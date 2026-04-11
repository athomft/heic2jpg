# HEIC to JPG Converter CLI

A powerful Node.js command-line tool to convert `.HEIC` images to `.JPG` format. Supports batch conversion, recursion, quality control, and more.

## Prerequisites

- [Node.js](https://nodejs.org/) (v14 or higher recommended)

## Installation

1. Clone or download this project.
2. Open your terminal in the project directory.
3. Install the dependencies:
   ```bash
   npm install
   ```
4. Build the project:
   ```bash
   npm run build
   ```

## Development

To run the TypeScript code directly during development:
```bash
npm run dev -- [options] <inputs...>
```

## Global Command (Recommended)

To use `heic2jpg` from **any folder**, link it globally:

1. In the project directory, build and link:
   ```bash
   npm run build
   npm link
   ```
2. Now, you can run:
   ```bash
   heic2jpg [options] <inputs...>
   ```

---

## Usage & Options

You can run the tool using `node dist/app.js` or the global `heic2jpg` command. Since it uses absolute paths, you can point to files anywhere on your computer.
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

### Examples

**Convert an entire folder and its subfolders:**
```bash
heic2jpg ./TravelPhotos -r
```

**Convert with 80% quality and delete originals:**
```bash
heic2jpg photo.heic -q 80 -d
```

**Convert multiple files into a specific directory:**
```bash
heic2jpg photo1.heic photo2.heic -o ./output_folder/
```

## Troubleshooting

- **"input buffer is not a HEIC image"**: The file is corrupted or not a real HEIC image.
- **Skipped files**: By default, the tool won't overwrite existing files. Use `-f` to force overwrite.

## License
MIT
