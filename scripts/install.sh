#!/bin/bash
# installer for heic2jpg (macOS & Linux)
# Usage: curl -fsSL https://raw.githubusercontent.com/athomft/HEIC2JPG/main/scripts/install.sh | sh

set -e

REPO="athomft/HEIC2JPG"
INSTALL_DIR="/usr/local/bin"
APP_NAME="heic2jpg"

# 1. Detect OS & Arch
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

BINARY_NAME=""

if [ "$OS" == "darwin" ]; then
    if [ "$ARCH" == "arm64" ]; then
        BINARY_NAME="heic2jpg-macos-arm64"
    else
        BINARY_NAME="heic2jpg-macos-x64"
    fi
elif [ "$OS" == "linux" ]; then
    BINARY_NAME="heic2jpg-linux-x64"
else
    echo "❌ Unsupported OS: $OS"
    exit 1
fi

URL="https://github.com/$REPO/releases/latest/download/$BINARY_NAME"

# 2. Download
echo "📥 Downloading heic2jpg for $OS ($ARCH)..."
curl -L "$URL" -o "$INSTALL_DIR/$APP_NAME"

# 3. Permissions
echo "🔐 Setting permissions..."
chmod +x "$INSTALL_DIR/$APP_NAME"

echo -e "\n✨ heic2jpg has been installed successfully to $INSTALL_DIR!"
echo "🚀 Type 'heic2jpg' to start using it."
