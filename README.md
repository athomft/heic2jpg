# HEIC to JPG Converter

Web tool to convert `.HEIC` images to `.JPG` format through your browser. Supports drag-and-drop upload, quality adjustment, metadata stripping, single and batch conversion.

## Quick Start

```bash
pip install .
uvicorn web:app --reload
```

Open **http://localhost:8000**.

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
- Rate limiting (10 req/min per IP)
- File size limit (50 MB)
- Conversion timeout (120s)
- Health check endpoint (`/health`)

## API Endpoints

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Health check |
| `GET` | `/` | Web interface |
| `POST` | `/convert` | Convert a single HEIC file |
| `POST` | `/convert/batch` | Convert multiple HEIC files (returns ZIP) |
| `GET` | `/docs` | Swagger API documentation |

## Deployment

### Railway (recommended)

1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app) and create a new project
3. Select **Deploy from GitHub repo**
4. Railway auto-detects the Python project and runs `uvicorn web:app`
5. Set the start command if needed:
   ```
   uvicorn web:app --host 0.0.0.0 --port $PORT --workers 4
   ```

### Fly.io

```bash
fly launch
fly deploy
```

### Docker

```bash
docker build -t heic2jpg .
docker run -p 8000:8000 heic2jpg
```

### Cloudflare Tunnel (for personal use)

```bash
uvicorn web:app --host 0.0.0.0 --port 8000
cloudflared tunnel --url http://localhost:8000
```

## Troubleshooting

- **"input buffer is not a HEIC image"**: The file isn't a valid `.heic` photo. Check that it's actually a HEIC image (usually from an iPhone).
- **"File too large"**: Maximum file size is 50 MB. Resize or split your file.
- **"Conversion timed out"**: The conversion took longer than 120 seconds. Try a smaller file.

## License

MIT
