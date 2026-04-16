import argparse
import os
import sys
import subprocess
import json
import shutil
import tempfile
import urllib.request
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

try:
    from PIL import Image
    from pillow_heif import register_heif_opener
    import piexif
    from tqdm import tqdm
except ImportError:
    print("Missing dependencies. Please run: pip install Pillow pillow-heif piexif tqdm")
    sys.exit(1)

# Register HEIF opener for Pillow
register_heif_opener()

VERSION = '1.5.2'
APP_NAME = 'heic2jpg'
GITHUB_REPO = 'athomft/HEIC2JPG'
DESCRIPTION = 'Advanced CLI tool to convert .HEIC images to .JPG'

BANNER = r"""
  _    _ ______ _____ _____ ___      _ _____   _____ 
 | |  | |  ____|_   _/ ____|__ \    | |  __ \ / ____|
 | |__| | |__    | || |       ) |   | | |__) | |  __ 
 |  __  |  __|   | || |      / /_   | |  ___/| | |_ |
 | |  | | |____ _| || |____ / /| |__| | |    | |__| |
 |_|  |_|______|____\_____|____\____/|_|     \_____|
"""

def check_update():
    print("Checking for updates...")
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        headers = {'User-Agent': 'heic2jpg-cli'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            latest_version = data['tag_name'].replace('v', '')
            
            if latest_version != VERSION:
                print(f"\nA new version is available: v{latest_version} (current: v{VERSION})")
                print("Updating now...")
                
                if sys.platform == 'win32':
                    cmd = 'powershell -c "irm https://raw.githubusercontent.com/{0}/main/scripts/install.ps1 | iex"'.format(GITHUB_REPO)
                    subprocess.run(cmd, shell=True)
                else:
                    cmd = 'curl -fsSL https://raw.githubusercontent.com/{0}/main/scripts/install.sh | sh'.format(GITHUB_REPO)
                    subprocess.run(cmd, shell=True)
                
                print("\nUpdate complete! Please restart your terminal.")
            else:
                print("You are already using the latest version.")
    except Exception as e:
        print(f"Could not check for updates: {e}")

def uninstall():
    print("\nUninstalling heic2jpg...")
    if sys.platform == 'win32':
        install_dir = Path.home() / '.heic2jpg'
        if install_dir.exists():
            print(f"Removing directory: {install_dir}")
            try:
                # Create a batch file to delete the directory after we exit
                with tempfile.NamedTemporaryFile(suffix='.bat', delete=False) as f:
                    batch_path = f.name
                    script = f'@echo off\ntimeout /t 2 /nobreak > nul\nrmdir /s /q "{install_dir}"\ndel "%~f0"'
                    f.write(script.encode())
                
                subprocess.Popen(['cmd.exe', '/c', batch_path], detached=True)
                print("\nSuccess! The application files will be removed in a few seconds.")
                print("Note: You may still need to manually remove the folder from your PATH environment variable.")
                sys.exit(0)
            except Exception as e:
                print(f"Failed to trigger uninstallation: {e}")
    else:
        print("To uninstall on macOS/Linux, please run: sudo rm /usr/local/bin/heic2jpg")
    sys.exit(0)

def process_file(input_path, output_path, quality, strip, keep_date, delete_original, force):
    try:
        if os.path.exists(output_path) and not force:
            return {'status': 'skipped', 'input_path': input_path}

        img = Image.open(input_path)
        
        exif_dict = None
        if not strip:
            try:
                exif_data = img.info.get('exif')
                if exif_data:
                    exif_dict = piexif.load(exif_data)
            except Exception:
                pass

        # Convert to RGB if needed (JPEG doesn't support RGBA or P)
        if img.mode not in ('RGB', 'RGBA', 'L'):
            img = img.convert('RGB')
        
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
            
        exif_bytes = b''
        if exif_dict and not strip:
            try:
                exif_bytes = piexif.dump(exif_dict)
            except Exception:
                pass

        save_kwargs = {'quality': quality}
        if exif_bytes:
            save_kwargs['exif'] = exif_bytes

        img.save(output_path, 'JPEG', **save_kwargs)
        
        if keep_date:
            stat = os.stat(input_path)
            os.utime(output_path, (stat.st_atime, stat.st_mtime))

        if delete_original:
            os.remove(input_path)
            
        return {'status': 'success', 'input_path': input_path}
    except Exception as e:
        return {'status': 'error', 'input_path': input_path, 'message': str(e)}

def main():
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description=f"{BANNER}\n{DESCRIPTION}\nheic2jpg version {VERSION}",
        formatter_class=argparse.RawTextHelpFormatter,
        usage='%(prog)s [options] [inputs...]'
    )
    
    parser.add_argument('inputs', nargs='*', help='Path to the input .HEIC file(s) or directories')
    parser.add_argument('-o', '--output', help='Path to the output .JPG file or output directory')
    parser.add_argument('-q', '--quality', type=int, default=100, help='JPG quality (0 to 100)')
    parser.add_argument('-r', '--recursive', action='store_true', help='Recursively search for .HEIC files in directories')
    parser.add_argument('-d', '--delete', action='store_true', help='Delete the original .HEIC file after successful conversion')
    parser.add_argument('-f', '--force', action='store_true', help='Force overwrite if output file already exists')
    parser.add_argument('-p', '--parallel', type=int, default=os.cpu_count(), help='Number of parallel threads to use')
    parser.add_argument('--strip', action='store_true', help='Strip all metadata (EXIF) from the image')
    parser.add_argument('--keep-date', action='store_true', help='Preserve original file modification date')
    parser.add_argument('-v', '--version', action='version', version=f'{APP_NAME} {VERSION}')
    
    args = parser.parse_args()
    
    if not args.inputs:
        parser.print_help()
        sys.exit(0)
        
    files_to_process = []
    
    for input_path in args.inputs:
        p = Path(input_path)
        if not p.exists():
            print(f"Error: File or directory not found: {input_path}")
            continue
            
        if p.is_dir():
            if args.recursive:
                for heic_file in p.rglob('*.[hH][eE][iI][cC]'):
                    if heic_file.is_file():
                        files_to_process.append(heic_file)
            else:
                for heic_file in p.glob('*.[hH][eE][iI][cC]'):
                    if heic_file.is_file():
                        files_to_process.append(heic_file)
        elif p.is_file() and p.suffix.lower() == '.heic':
            files_to_process.append(p)
            
    if not files_to_process:
        print("No .HEIC files found to process.")
        sys.exit(0)
        
    output_base = Path(args.output) if args.output else None
    is_multi_file = len(files_to_process) > 1
    treat_as_directory = is_multi_file or (
        output_base and (
            args.output.endswith('/') or 
            args.output.endswith('\\') or 
            (output_base.exists() and output_base.is_dir())
        )
    )
    
    if treat_as_directory and output_base and not output_base.exists():
        output_base.mkdir(parents=True, exist_ok=True)
        
    print(f"Processing {len(files_to_process)} file(s) using {args.parallel} thread(s)...")
    
    converted_count = 0
    skipped_count = 0
    error_count = 0
    
    with ProcessPoolExecutor(max_workers=args.parallel) as executor:
        futures = {}
        for input_path in files_to_process:
            if treat_as_directory:
                if output_base:
                    output_path = output_base / f"{input_path.stem}.jpg"
                else:
                    output_path = input_path.parent / f"{input_path.stem}.jpg"
            else:
                output_path = output_base if output_base else input_path.parent / f"{input_path.stem}.jpg"
                
            future = executor.submit(
                process_file,
                str(input_path),
                str(output_path),
                args.quality,
                args.strip,
                args.keep_date,
                args.delete,
                args.force
            )
            futures[future] = input_path
            
        with tqdm(total=len(files_to_process), unit='file', desc='Progress', bar_format='{desc} |{bar}| {percentage:3.0f}% | {n_fmt}/{total_fmt} Files | {postfix}') as pbar:
            for future in as_completed(futures):
                result = future.result()
                if result['status'] == 'success':
                    converted_count += 1
                elif result['status'] == 'skipped':
                    skipped_count += 1
                else:
                    error_count += 1
                    
                input_path = futures[future]
                pbar.set_postfix_str(input_path.name)
                pbar.update(1)
                
    print('\n--- Summary ---')
    print(f"Converted: {converted_count}")
    print(f"Skipped:   {skipped_count} (Use -f to overwrite)")
    print(f"Errors:    {error_count}")

if __name__ == '__main__':
    main()