import os
import sys
import tempfile
from pathlib import Path
import pytest
from PIL import Image, ImageOps
import piexif

sys.path.insert(0, str(Path(__file__).parent.parent))
from converter import process_file



@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def sample_heic(temp_dir):
    """Create a valid sample HEIC image for testing."""
    heic_path = temp_dir / "test_photo.heic"
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    img.save(str(heic_path), format="HEIF")
    return str(heic_path)


@pytest.fixture
def sample_heic_rgba(temp_dir):
    """Create a valid sample HEIC image with RGBA transparency for testing."""
    heic_path = temp_dir / "test_transparent.heic"
    img = Image.new("RGBA", (100, 100), color=(0, 255, 0, 128))
    img.save(str(heic_path), format="HEIF")
    return str(heic_path)


def test_process_file_success(sample_heic, temp_dir):
    output_path = str(temp_dir / "test_photo.jpg")
    res = process_file(sample_heic, output_path, quality=90, strip=False)
    assert res["status"] == "success"
    assert os.path.exists(output_path)

    # Verify output is a valid JPEG
    with Image.open(output_path) as out_img:
        assert out_img.format == "JPEG"
        assert out_img.size == (100, 100)


def test_process_file_rgba(sample_heic_rgba, temp_dir):
    output_path = str(temp_dir / "test_transparent.jpg")
    res = process_file(sample_heic_rgba, output_path, quality=85)
    assert res["status"] == "success"
    assert os.path.exists(output_path)

    with Image.open(output_path) as out_img:
        assert out_img.format == "JPEG"
        assert out_img.mode == "RGB"


def test_process_file_skip_existing(sample_heic, temp_dir):
    output_path = str(temp_dir / "test_photo.jpg")
    Path(output_path).write_bytes(b"existing")

    res = process_file(sample_heic, output_path, force=False)
    assert res["status"] == "skipped"


def test_process_file_non_existent():
    res = process_file("non_existent.heic", "out.jpg")
    assert res["status"] == "error"
    assert "message" in res


def test_process_file_exif_strip(temp_dir):
    heic_path = temp_dir / "exif_photo.heic"
    # Create an image with orientation EXIF tag
    zeroth_ifd = {piexif.ImageIFD.Orientation: 6}
    exif_bytes = piexif.dump({"0th": zeroth_ifd})
    img = Image.new("RGB", (200, 100), color=(10, 20, 30))
    img.save(str(heic_path), format="HEIF", exif=exif_bytes)

    # When strip=True, output should be transposed (100x200) and EXIF stripped
    out_stripped = str(temp_dir / "out_stripped.jpg")
    res1 = process_file(str(heic_path), out_stripped, strip=True)
    assert res1["status"] == "success"

    with Image.open(out_stripped) as out_img:
        # Since orientation 6 means rotate 270 / transpose, size is 100x200
        assert out_img.size == (100, 200)


def test_converter_cli(sample_heic, temp_dir):
    import subprocess
    import sys
    out_path = temp_dir / "cli_out.jpg"
    converter_script = Path(__file__).parent.parent / "converter.py"
    proc = subprocess.run(
        [sys.executable, str(converter_script), sample_heic, "-o", str(out_path), "-q", "75"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert out_path.exists()


