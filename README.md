# HEIC to JPG Converter

Web tool to convert `.HEIC` images to `.JPG` format through your browser. Supports drag-and-drop upload, quality adjustment, metadata stripping, single and batch conversion.

## Setup

```bash
git clone https://github.com/athomft/HEIC2JPG.git
cd heic2jpg
pip install .
```

## Usage

```bash
uvicorn web:app --reload
```

Then open **http://localhost:8000** in your browser.

Or simply:
```bash
python web.py
```

## Features

- Drag-and-drop file upload
- Quality adjustment slider
- Strip metadata option
- Single file → direct JPG download
- Multiple files → ZIP download
- Automatic Swagger API docs at `/docs`

## API Endpoints

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Web interface |
| `POST` | `/convert` | Convert a single HEIC file |
| `POST` | `/convert/batch` | Convert multiple HEIC files (returns ZIP) |
| `GET` | `/docs` | Swagger API documentation |

## Troubleshooting

- **"input buffer is not a HEIC image"**: The file isn't a valid `.heic` photo. Check that the file isn't corrupted and that it's actually a HEIC image (usually from an iPhone).

## License

MIT
