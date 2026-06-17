# HEIC to JPG Converter

A powerful tool to convert `.HEIC` images to `.JPG` format. Comes as both a **CLI tool** and a **web interface**. Supports batch conversion, recursion, quality control, parallel processing, and metadata management.

## 🚀 Quick Install (Standalone - No Python required)

Install `heic2jpg` globally with a single command.

### **Windows (PowerShell)**
```powershell
powershell -c "irm https://raw.githubusercontent.com/athomft/HEIC2JPG/main/scripts/install.ps1 | iex"
```

### **macOS / Linux**
```bash
curl -fsSL https://raw.githubusercontent.com/athomft/HEIC2JPG/main/scripts/install.sh | sh
```

---

## 🛠️ Manual Installation (Requires Python)

If you have Python installed and want to install via `pip`:

1. Clone or download this project.
2. Install:
   ```bash
   pip install .
   ```

---

## 🌐 Web Interface

Run the web app to convert HEIC files through your browser.

### Setup

```bash
pip install .[web]
```

### Usage

```bash
uvicorn web:app --reload
```

Then open **http://localhost:8000** in your browser.

Or simply:
```bash
python web.py
```

### Features

- Drag-and-drop file upload
- Quality adjustment slider
- Strip metadata option
- Single file → direct JPG download
- Multiple files → ZIP download
- Automatic Swagger API docs at `/docs`

---

## CLI Usage & Options

You can run the tool using the global `heic2jpg` command. Since it uses absolute paths, you can point to files anywhere on your computer.

```bash
# Single file
heic2jpg photo.heic

# Multiple files
heic2jpg image1.heic image2.heic

# All HEIC files in a folder
heic2jpg ./MyPhotos/
```

### Advanced Options

| Option | Shorthand | Description |
| :--- | :--- | :--- |
| `--help` | `-h` | Display help and all available options |
| `--version` | `-v` | Display the current app version |
| `--quality <0-100>` | `-q` | Set JPG quality (Default is 100) |
| `--output <path>` | `-o` | Specify output file or directory |
| `--recursive` | `-r` | Search for .heic files in subfolders |
| `--delete` | `-d` | Delete the original .heic file after successful conversion |
| `--force` | `-f` | Overwrite existing .jpg files without asking |
| `--parallel <number>` | `-p` | Number of parallel threads to use (Default: CPU count) |
| `--strip` | | Strip all metadata (EXIF) from the image |
| `--keep-date` | | Preserve original file modification date |

### Examples

**Convert an entire folder using all CPU cores:**
```bash
heic2jpg ./TravelPhotos -r
```

**Convert with specific parallel threads and keep original date:**
```bash
heic2jpg ./Photos -r -p 4 --keep-date
```

**Convert with 80% quality and strip all metadata for privacy:**
```bash
heic2jpg photo.heic -q 80 --strip
```

## Troubleshooting

- **"input buffer is not a HEIC image"**: This means the file you're trying to convert isn't a valid `.heic` photo. Check that the file isn't corrupted and that it's actually a HEIC image (usually from an iPhone).
- **Skipped files**: To protect your data, the tool **will not** overwrite an existing `.jpg` file by default. If you want to replace an existing JPG, add the `-f` (force) flag to your command.

## License
MIT
