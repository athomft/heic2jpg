"""
heic2jpg Web API - Convert HEIC images to JPG via a web interface.

Usage:
    uvicorn web:app --reload
    # or
    python web.py
"""
import os
import sys
import tempfile
import zipfile
import io
from pathlib import Path
from typing import List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response, HTMLResponse
import uvicorn

# Import the existing CLI conversion function
sys.path.insert(0, str(Path(__file__).parent))
from heic2jpg import register_heif_opener, process_file

register_heif_opener()

app = FastAPI(
    title="HEIC to JPG Converter",
    description="Convert .HEIC images to .JPG format via a web interface",
    version="1.0.0",
)

HERE = Path(__file__).parent


def _convert_to_bytes(input_path, output_path, quality, strip):
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


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = HERE / "index.html"
    if not html_path.exists():
        return HTMLResponse("<h1>HEIC to JPG Converter</h1><p>Frontend not found.</p>", status_code=500)
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.post("/convert")
async def convert_single(
    file: UploadFile = File(...),
    quality: int = Form(100),
    strip: bool = Form(False),
):
    if not file.filename:
        raise HTTPException(400, "No file provided")
    if not file.filename.lower().endswith(".heic"):
        raise HTTPException(400, f"Unsupported file type: {file.filename}. Only .HEIC files are supported.")
    if not (0 <= quality <= 100):
        raise HTTPException(400, "Quality must be between 0 and 100")

    tmp_in = tempfile.NamedTemporaryFile(suffix=".heic", delete=False).name
    tmp_out = tmp_in.replace(".heic", ".jpg")

    try:
        content = await file.read()
        with open(tmp_in, "wb") as f:
            f.write(content)
        jpg_bytes = _convert_to_bytes(tmp_in, tmp_out, quality, strip)
        out_name = file.filename.rsplit(".", 1)[0] + ".jpg"
        return Response(
            content=jpg_bytes,
            media_type="image/jpeg",
            headers={"Content-Disposition": f'attachment; filename="{out_name}"'},
        )
    finally:
        for p in (tmp_in, tmp_out):
            if os.path.exists(p):
                os.unlink(p)


@app.post("/convert/batch")
async def convert_batch(
    files: List[UploadFile] = File(...),
    quality: int = Form(100),
    strip: bool = Form(False),
):
    if not files:
        raise HTTPException(400, "No files provided")
    if not (0 <= quality <= 100):
        raise HTTPException(400, "Quality must be between 0 and 100")

    with tempfile.TemporaryDirectory() as tmp_dir:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in files:
                if not file.filename or not file.filename.lower().endswith(".heic"):
                    continue
                tmp_in = os.path.join(tmp_dir, file.filename)
                tmp_out = os.path.join(tmp_dir, file.filename.rsplit(".", 1)[0] + ".jpg")
                content = await file.read()
                with open(tmp_in, "wb") as f:
                    f.write(content)
                result = process_file(
                    tmp_in, tmp_out, quality, strip,
                    keep_date=False, delete_original=False, force=True,
                )
                if result["status"] == "success" and os.path.exists(tmp_out):
                    zf.write(tmp_out, os.path.basename(tmp_out))
        zip_buffer.seek(0)
        zip_bytes = zip_buffer.getvalue()

    if len(zip_bytes) == 0:
        raise HTTPException(400, "No valid HEIC files were converted")

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="converted-images.zip"'},
    )


if __name__ == "__main__":
    uvicorn.run("web:app", host="0.0.0.0", port=8000, reload=True)
