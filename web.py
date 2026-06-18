"""
heic2jpg Web API - Convert HEIC images to JPG via a web interface.

Production entry point. Run with:
    uvicorn web:app --host 0.0.0.0 --port 8000 --workers 4
    # or
    python web.py
"""

import asyncio
import base64
import io
import json
import logging
import os
import tempfile
import zipfile
from pathlib import Path
from typing import List

import uvicorn
from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.background import BackgroundTask

from converter import process_file

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(50 * 1024 * 1024)))
CONVERSION_TIMEOUT = int(os.getenv("CONVERSION_TIMEOUT", "120"))
HERE = Path(__file__).parent

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("heic2jpg")

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="HEIC to JPG Converter",
    description="Convert .HEIC images to .JPG format via a web interface",
    version="1.0.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _save_upload(file: UploadFile) -> str:
    """Stream upload to a temp file, enforcing a size limit.

    Returns the path to the temp file. Caller is responsible for cleanup.
    """
    if not file.filename:
        raise HTTPException(400, "No file provided")
    if not file.filename.lower().endswith(".heic"):
        raise HTTPException(400, f"Unsupported file type: {file.filename}")

    tmp = tempfile.NamedTemporaryFile(suffix=".heic", delete=False)
    total = 0
    try:
        while True:
            chunk = await file.read(64 * 1024)  # 64 KB chunks
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_FILE_SIZE:
                raise HTTPException(
                    413, f"File too large (max {MAX_FILE_SIZE // (1024 * 1024)} MB)"
                )
            tmp.write(chunk)
    except Exception:
        tmp.close()
        os.unlink(tmp.name)
        raise
    tmp.close()
    return tmp.name


def _convert(input_path: str, output_path: str, quality: int, strip: bool) -> None:
    """Run the converter synchronously. Raises HTTPException on failure."""
    result = process_file(
        input_path,
        output_path,
        quality,
        strip,
        keep_date=False,
        delete_original=False,
        force=True,
    )
    if result["status"] == "error":
        raise HTTPException(
            status_code=500, detail=result.get("message", "Conversion failed")
        )
    if not os.path.exists(output_path):
        raise HTTPException(status_code=500, detail="Output file was not created")


def _cleanup(*paths: str) -> None:
    """Remove files, ignoring errors."""
    for p in paths:
        try:
            if os.path.exists(p):
                os.unlink(p)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    """Health check for load balancers and monitoring."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = HERE / "index.html"
    if not html_path.exists():
        return HTMLResponse("<h1>Frontend not found</h1>", status_code=500)
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.post("/convert")
@limiter.limit("10/minute")
async def convert_single(
    request: Request,
    file: UploadFile = File(...),
    quality: int = Form(100),
    strip: bool = Form(False),
):
    """Convert a single HEIC file to JPG and stream it as a download."""
    if not (0 <= quality <= 100):
        raise HTTPException(400, "Quality must be between 0 and 100")

    tmp_in = await _save_upload(file)
    tmp_out = tmp_in.replace(".heic", ".jpg")

    try:
        loop = asyncio.get_running_loop()
        await asyncio.wait_for(
            loop.run_in_executor(None, _convert, tmp_in, tmp_out, quality, strip),
            timeout=CONVERSION_TIMEOUT,
        )

        out_name = (file.filename or "image").rsplit(".", 1)[0] + ".jpg"
        return FileResponse(
            tmp_out,
            media_type="image/jpeg",
            headers={"Content-Disposition": f'attachment; filename="{out_name}"'},
            background=BackgroundTask(_cleanup, tmp_in, tmp_out),
        )
    except asyncio.TimeoutError:
        _cleanup(tmp_in, tmp_out)
        logger.warning("Conversion timed out for %s", file.filename)
        raise HTTPException(504, "Conversion timed out")


async def _batch_event_stream(files, quality, strip):
    """Async generator yielding SSE events during batch conversion.

    Events: progress, summary, download, error
    """
    loop = asyncio.get_running_loop()
    total = len(files)
    queue = asyncio.Queue()
    lock = asyncio.Lock()
    converted = 0
    skipped = 0
    converted_data = []
    semaphore = asyncio.Semaphore(min(4, total))

    async def _convert_one(file):
        nonlocal converted, skipped

        async with semaphore:
            try:
                if not file.filename or not file.filename.lower().endswith(".heic"):
                    await queue.put(
                        {
                            "type": "progress",
                            "file": file.filename or "unknown",
                            "status": "skipped",
                            "reason": "not a HEIC file",
                        }
                    )
                    async with lock:
                        skipped += 1
                    return

                await queue.put(
                    {
                        "type": "progress",
                        "file": file.filename,
                        "status": "converting",
                    }
                )

                tmp_in = await _save_upload(file)
                tmp_out = tmp_in.replace(".heic", ".jpg")

                try:
                    await asyncio.wait_for(
                        loop.run_in_executor(
                            None, _convert, tmp_in, tmp_out, quality, strip
                        ),
                        timeout=CONVERSION_TIMEOUT,
                    )

                    async with lock:
                        with open(tmp_out, "rb") as f:
                            converted_data.append((os.path.basename(tmp_out), f.read()))
                        converted += 1

                    await queue.put(
                        {
                            "type": "progress",
                            "file": file.filename,
                            "status": "done",
                        }
                    )
                except asyncio.TimeoutError:
                    logger.warning("Batch conversion timed out for %s", file.filename)
                    await queue.put(
                        {
                            "type": "progress",
                            "file": file.filename,
                            "status": "error",
                            "message": "timed out",
                        }
                    )
                    async with lock:
                        skipped += 1
                except HTTPException:
                    logger.warning("Skipping file %s", file.filename)
                    await queue.put(
                        {
                            "type": "progress",
                            "file": file.filename,
                            "status": "error",
                            "message": "conversion failed",
                        }
                    )
                    async with lock:
                        skipped += 1
                finally:
                    _cleanup(tmp_in, tmp_out)
            except Exception as e:
                await queue.put(
                    {
                        "type": "progress",
                        "file": getattr(file, "filename", "unknown"),
                        "status": "error",
                        "message": str(e),
                    }
                )
                async with lock:
                    skipped += 1

    # Start all conversions concurrently
    tasks = [asyncio.create_task(_convert_one(f)) for f in files]

    # Yield events from the queue as they arrive
    done_count = 0
    while done_count < total:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=0.5)
            yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
            if event.get("type") == "progress" and event.get("status") in (
                "done",
                "skipped",
                "error",
            ):
                done_count += 1
        except asyncio.TimeoutError:
            if all(t.done() for t in tasks):
                break

    await asyncio.gather(*tasks, return_exceptions=True)

    # Send summary
    yield f"event: summary\ndata: {json.dumps({'converted': converted, 'skipped': skipped, 'total': total})}\n\n"

    if converted == 0:
        yield f"event: error\ndata: {json.dumps({'message': 'No valid HEIC files were converted'})}\n\n"
        return

    # Build ZIP from converted data and send as base64 download event
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in converted_data:
            zf.writestr(name, data)

    zip_b64 = base64.b64encode(zip_buffer.getvalue()).decode()
    yield f"event: download\ndata: {zip_b64}\n\n"


@app.post("/convert/batch")
@limiter.limit("5/minute")
async def convert_batch(
    request: Request,
    files: List[UploadFile] = File(...),
    quality: int = Form(100),
    strip: bool = Form(False),
):
    """Convert multiple HEIC files with real-time progress via SSE, then return a ZIP."""
    if not files:
        raise HTTPException(400, "No files provided")
    if not (0 <= quality <= 100):
        raise HTTPException(400, "Quality must be between 0 and 100")

    return StreamingResponse(
        _batch_event_stream(files, quality, strip),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(
        "web:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
        access_log=True,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
