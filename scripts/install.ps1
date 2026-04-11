# installer for heic2jpg (Windows)
# Usage: powershell -c "irm https://raw.githubusercontent.com/athomft/HEIC2JPG/main/scripts/install.ps1 | iex"

$installDir = "$HOME\.heic2jpg\bin"
$exeName = "heic2jpg.exe"
$exePath = "$installDir\$exeName"
$githubUrl = "https://github.com/athomft/HEIC2JPG/releases/latest/download/heic2jpg-win-x64.exe"

# 1. Create directory
if (!(Test-Path $installDir)) {
    Write-Host "📁 Creating installation directory: $installDir" -ForegroundColor Cyan
    New-Item -ItemType Directory -Force -Path $installDir | Out-Null
}

# 2. Download binary
Write-Host "📥 Downloading heic2jpg..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri $githubUrl -OutFile $exePath
} catch {
    Write-Error "❌ Failed to download binary. Please check the URL or your internet connection."
    exit 1
}

# 3. Add to PATH (User level)
Write-Host "⚙️ Adding to system PATH..." -ForegroundColor Cyan
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($currentPath -notlike "*$installDir*") {
    $newPath = "$currentPath;$installDir"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "✅ Successfully added to PATH." -ForegroundColor Green
} else {
    Write-Host "ℹ️ Already in PATH." -ForegroundColor Yellow
}

Write-Host "`n✨ heic2jpg has been installed successfully!" -ForegroundColor Green
Write-Host "🚀 Restart your terminal and type 'heic2jpg' to start using it." -ForegroundColor Cyan
