#!/bin/bash

REPO="athomft/HEIC2JPG"
APP_NAME="heic2jpg"
INSTALL_PATH="/usr/local/bin"

# Determine OS
OS=$(uname -s | tr '[:upper:]' '[:lower:]')

# Fetch latest release info
echo "Fetching latest version from GitHub..."
RELEASE_JSON=$(curl -s "https://api.github.com/repos/$REPO/releases/latest")
TAG=$(echo "$RELEASE_JSON" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')

if [ -z "$TAG" ]; then
    echo "Error: Could not find latest version on GitHub."
    exit 1
fi

echo "Downloading $APP_NAME $TAG for $OS..."

# Filter asset based on OS
if [[ "$OS" == "darwin" ]]; then
    ASSET_URL=$(echo "$RELEASE_JSON" | grep '"browser_download_url":' | grep 'macos' | sed -E 's/.*"([^"]+)".*/\1/')
elif [[ "$OS" == "linux" ]]; then
    ASSET_URL=$(echo "$RELEASE_JSON" | grep '"browser_download_url":' | grep 'linux' | sed -E 's/.*"([^"]+)".*/\1/')
fi

if [ -z "$ASSET_URL" ]; then
    # Fallback to searching by name if not found by platform
    ASSET_URL=$(echo "$RELEASE_JSON" | grep '"browser_download_url":' | grep "$OS" | sed -E 's/.*"([^"]+)".*/\1/')
fi

if [ -z "$ASSET_URL" ]; then
    echo "Error: Could not find a suitable binary for $OS."
    exit 1
fi

# Download to temporary location
TMP_FILE="/tmp/$APP_NAME"
curl -L "$ASSET_URL" -o "$TMP_FILE"
chmod +x "$TMP_FILE"

# Move to install path (may require sudo)
if [ -w "$INSTALL_PATH" ]; then
    mv "$TMP_FILE" "$INSTALL_PATH/$APP_NAME"
else
    echo "Requires sudo permissions to move binary to $INSTALL_PATH"
    sudo mv "$TMP_FILE" "$INSTALL_PATH/$APP_NAME"
fi

echo -e "\n$APP_NAME has been installed successfully!"
echo "Try running: $APP_NAME --help"
