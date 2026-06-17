"""
Core HEIC to JPG conversion logic.
"""

import os

import piexif
from PIL import Image
from pillow_heif import register_heif_opener

# Register HEIF opener so Pillow can read .heic files
register_heif_opener()


def process_file(
    input_path, output_path, quality, strip, keep_date, delete_original, force
):
    """
    Convert a single HEIC file to JPG.

    Returns a dict with 'status' ('success', 'skipped', or 'error'),
    'input_path', and optionally 'message' on error.
    """
    try:
        if os.path.exists(output_path) and not force:
            return {"status": "skipped", "input_path": input_path}

        img = Image.open(input_path)

        exif_dict = None
        if not strip:
            try:
                exif_data = img.info.get("exif")
                if exif_data:
                    exif_dict = piexif.load(exif_data)
            except Exception:
                pass

        # Convert to RGB if needed (JPEG doesn't support RGBA or P)
        if img.mode not in ("RGB", "RGBA", "L"):
            img = img.convert("RGB")

        if img.mode == "RGBA":
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background

        exif_bytes = b""
        if exif_dict and not strip:
            try:
                exif_bytes = piexif.dump(exif_dict)
            except Exception:
                pass

        save_kwargs = {"quality": quality}
        if exif_bytes:
            save_kwargs["exif"] = exif_bytes

        img.save(output_path, "JPEG", **save_kwargs)

        if keep_date:
            stat = os.stat(input_path)
            os.utime(output_path, (stat.st_atime, stat.st_mtime))

        if delete_original:
            os.remove(input_path)

        return {"status": "success", "input_path": input_path}
    except Exception as e:
        return {"status": "error", "input_path": input_path, "message": str(e)}
