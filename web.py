"""
heic2jpg Web API - Convert HEIC images to JPG via a web interface.

Production entry point. Run with:
    uvicorn web:app --host 0.0.0.0 --port 8000 --workers 4
    # or
    python web.py
"""
import os
import tempfile
import zipfile
import io
import asyncio
import logging
from pathlib import Path
from typing import List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import Response, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn

from converter import process_file

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MAX_FILE_SIZE = 50 * 1024 * 1024      # 50 MB per file
CONVERSION_TIMEOUT = 120               # seconds per file
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
                raise HTTPException(413, "File too large (max 50 MB)")
            tmp.write(chunk)
    except Exception:
        tmp.close()
        os.unlink(tmp.name)
        raise
    tmp.close()
    return tmp.name


def _convert_to_bytes(input_path: str, output_path: str, quality: int, strip: bool) -> bytes:
    """Run the converter synchronously and return output bytes."""
    result = process_file(
        input_path, output_path, quality, strip,
        keep_date=False, delete_original=False, force=True,
    )
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "Conversion failed"))
    if not os.path.exists(output_path):
        raise HTTPException(status_code=500, detail="Output file was not created")
    with open(output_path, "rb") as f:
        return f.read()


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
    """Convert a single HEIC file to JPG and return it as a download."""
    if not (0 <= quality <= 100):
        raise HTTPException(400, "Quality must be between 0 and 100")

    tmp_in = await _save_upload(file)
    tmp_out = tmp_in.replace(".heic", ".jpg")

    try:
        loop = asyncio.get_running_loop()
        jpg_bytes = await asyncio.wait_for(
            loop.run_in_executor(None, _convert_to_bytes, tmp_in, tmp_out, quality, strip),
            timeout=CONVERSION_TIMEOUT,
        )

        out_name = file.filename.rsplit(".", 1)[0] + ".jpg"
        return Response(
            content=jpg_bytes,
            media_type="image/jpeg",
            headers={"Content-Disposition": f'attachment; filename="{out_name}"'},
        )
    except asyncio.TimeoutError:
        logger.warning("Conversion timed out for %s", file.filename)
        raise HTTPException(504, "Conversion timed out")
    finally:
        for p in (tmp_in, tmp_out):
            if os.path.exists(p):
                os.unlink(p)


@app.post("/convert/batch")
@limiter.limit("5/minute")
async def convert_batch(
    request: Request,
    files: List[UploadFile] = File(...),
    quality: int = Form(100),
    strip: bool = Form(False),
):
    """Convert multiple HEIC files and return a ZIP archive of JPGs."""
    if not files:
        raise HTTPException(400, "No files provided")
    if not (0 <= quality <= 100):
        raise HTTPException(400, "Quality must be between 0 and 100")

    loop = asyncio.get_running_loop()
    converted = 0

    with tempfile.TemporaryDirectory() as tmp_dir:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in files:
                if not file.filename or not file.filename.lower().endswith(".heic"):
                    continue

                tmp_in = await _save_upload(file)
                tmp_out = tmp_in.replace(".heic", ".jpg")

                try:
                    await asyncio.wait_for(
                        loop.run_in_executor(None, _convert_to_bytes, tmp_in, tmp_out, quality, strip),
                        timeout=CONVERSION_TIMEOUT,
                    )
                    zf.write(tmp_out, os.path.basename(tmp_out))
                    converted += 1
                except asyncio.TimeoutError:
                    logger.warning("Batch conversion timed out for %s", file.filename)
                except HTTPException:
                    logger.warning("Skipping file %s", file.filename)
                finally:
                    for p in (tmp_in, tmp_out):
                        if os.path.exists(p):
                            os.unlink(p)

        zip_buffer.seek(0)
        zip_bytes = zip_buffer.getvalue()

    if converted == 0:
        raise HTTPException(400, "No valid HEIC files were converted")

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="converted-images.zip"'},
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
    )
