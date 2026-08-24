# HEIC to JPG Converter 📸

A modern, fast, **100% private, client-side WebAssembly** web app designed with a native mobile-app interface to convert `.HEIC` / `.HEIF` images to `.JPG` format directly in your browser.

> 🔒 **100% Private:** Photos are processed locally on your device via WebAssembly. Images never leave your phone or computer.

---

## 🚀 Deploy to Vercel (Instant 1-Click)

This project is built for zero-maintenance, static edge deployment on **Vercel**:

1. Push this repository to GitHub.
2. Go to [vercel.com](https://vercel.com) and click **"Add New Project"**.
3. Import this repository and click **Deploy**.
4. That's it! Zero backend servers, zero database, zero hosting bills.

Or with the Vercel CLI:
```bash
npx vercel
```

---

## ✨ Features

- **📱 Native Mobile-App UI:** Fixed-width smartphone canvas with iOS dynamic island, segmented quality controls, and thumb-friendly touch zones.
- **⚡ Client-Side WebAssembly:** Uses `heic2any` to decode HEIC and encode JPEG directly on device with near-native performance.
- **📦 Instant ZIP Downloads:** Generates multi-image `.zip` archives client-side via `JSZip` without server round-trips.
- **🔒 Zero-Knowledge Privacy:** 100% offline-capable and on-device. No data or photos are ever uploaded to any server.
- **⚙️ Custom Quality & EXIF Options:** Segmented presets (`75%`, `90%`, `100%`), fine-tune sliders, and EXIF strip toggle.
- **💻 CLI Utility:** Includes Python CLI script (`converter.py`) for batch processing files on desktop machines.

---

## 🛠️ Local Development

Simply open `index.html` in any modern web browser or serve locally:

```bash
# Using Python
python -m http.server 8000

# Using Node / npx
npx serve .
```

Open **http://localhost:8000** in your browser or mobile phone.

---

## 🖥️ Command Line Interface (CLI)

You can also convert images locally via Python CLI:

```bash
# Convert a single file
python converter.py photo.heic -o photo.jpg

# Convert a directory of HEIC files
python converter.py ./photos/ -o ./converted/ --quality 90

# Strip metadata and keep original timestamps
python converter.py ./photos/ --strip --keep-date
```

---

## 📄 License

MIT

