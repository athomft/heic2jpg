$ErrorActionPreference = 'Stop'

$Repo = "athomft/HEIC2JPG"
$AppName = "heic2jpg"
$InstallDir = "$HOME\.heic2jpg"
$ExeName = "$AppName.exe"
$ExePath = Join-Path $InstallDir $ExeName

# 1. Create install directory
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir | Out-Null
}

# 2. Get latest release version and download URL
Write-Host "Fetching latest version from GitHub..." -ForegroundColor Cyan
try {
    $Release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest"
    $Asset = $Release.assets | Where-Object { $_.name -like "*windows*.exe" -or ($_.name -eq "$AppName.exe") } | Select-Object -First 1
    
    if (-not $Asset) {
        throw "Could not find a Windows executable in the latest release."
    }
    
    $DownloadUrl = $Asset.browser_download_url
    Write-Host "Downloading $AppName v$($Release.tag_name)..." -ForegroundColor Green
    
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $ExePath
} catch {
    Write-Error "Failed to download ${AppName}: $($_.Exception.Message)"
    exit 1
}

# 3. Add to PATH if not already there
$CurrentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($CurrentPath -notlike "*$InstallDir*") {
    Write-Host "Adding $InstallDir to user PATH..." -ForegroundColor Cyan
    $NewPath = "$CurrentPath;$InstallDir"
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
    $env:Path = "$env:Path;$InstallDir"
    Write-Host "Success! You may need to restart your terminal for changes to take effect." -ForegroundColor Green
}

Write-Host "`n$AppName has been installed to $InstallDir" -ForegroundColor Green
Write-Host "Try running: $AppName --help" -ForegroundColor Yellow
