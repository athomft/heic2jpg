"""
Core HEIC to JPG conversion logic.
"""

import argparse
import os
import sys
from pathlib import Path

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

# Register HEIF opener so Pillow can read .heic files
register_heif_opener()


def process_file(
    input_path: str,
    output_path: str,
    quality: int = 100,
    strip: bool = False,
    keep_date: bool = False,
    delete_original: bool = False,
    force: bool = True,
) -> dict:
    """
    Convert a single HEIC file to JPG.

    Returns a dict with 'status' ('success', 'skipped', or 'error'),
    'input_path', and optionally 'message' on error.
    """
    try:
        if os.path.exists(output_path) and not force:
            return {"status": "skipped", "input_path": input_path}

        with Image.open(input_path) as img:
            # Preserve raw EXIF bytes before transformations
            exif_bytes = img.info.get("exif") if not strip else None

            # Auto-orient pixels based on EXIF tag to prevent sideways images
            img = ImageOps.exif_transpose(img)

            # Handle alpha channel & transparency compositing on white background
            if img.mode in ("RGBA", "LA") or (
                img.mode == "P" and "transparency" in img.info
            ):
                img = img.convert("RGBA")
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            save_kwargs = {"quality": quality}
            if exif_bytes and not strip:
                save_kwargs["exif"] = exif_bytes

            img.save(output_path, "JPEG", **save_kwargs)

        if keep_date and os.path.exists(input_path):
            stat = os.stat(input_path)
            os.utime(output_path, (stat.st_atime, stat.st_mtime))

        if delete_original and os.path.exists(input_path):
            os.remove(input_path)

        return {"status": "success", "input_path": input_path}
    except Exception as e:
        return {"status": "error", "input_path": input_path, "message": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Convert HEIC images to JPG.")
    parser.add_argument("input", help="Input HEIC file or directory")
    parser.add_argument(
        "-o", "--output", help="Output JPG file or directory", default=None
    )
    parser.add_argument(
        "-q",
        "--quality",
        type=int,
        default=100,
        help="JPEG quality (1-100, default: 100)",
    )
    parser.add_argument(
        "--strip", action="store_true", help="Strip EXIF metadata"
    )
    parser.add_argument(
        "--keep-date",
        action="store_true",
        help="Preserve file modification time",
    )
    parser.add_argument(
        "--delete-original",
        action="store_true",
        help="Delete original HEIC file after conversion",
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="Overwrite existing files"
    )

    args = parser.parse_args()
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Error: {input_path} does not exist", file=sys.stderr)
        sys.exit(1)

    files_to_process = []
    if input_path.is_dir():
        for p in input_path.glob("**/*"):
            if p.suffix.lower() == ".heic":
                out_dir = Path(args.output) if args.output else p.parent
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / (p.stem + ".jpg")
                files_to_process.append((str(p), str(out_path)))
    else:
        out_path = (
            args.output if args.output else str(input_path.with_suffix(".jpg"))
        )
        files_to_process.append((str(input_path), out_path))

    success = 0
    for inp, outp in files_to_process:
        res = process_file(
            inp,
            outp,
            quality=args.quality,
            strip=args.strip,
            keep_date=args.keep_date,
            delete_original=args.delete_original,
            force=args.force,
        )
        if res["status"] == "success":
            print(f"Converted: {inp} -> {outp}")
            success += 1
        elif res["status"] == "skipped":
            print(f"Skipped (already exists): {outp}")
        else:
            print(f"Error on {inp}: {res.get('message')}", file=sys.stderr)

    print(
        f"Finished. Successfully converted {success}/{len(files_to_process)} file(s)."
    )


if __name__ == "__main__":
    main()
