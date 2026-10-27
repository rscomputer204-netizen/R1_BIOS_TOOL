# BIOS_TOOL Build Script
# This script automates the creation of a single-file executable using PyInstaller.

$VENV_PYTHON = ".\.venv\Scripts\python.exe"
$MAIN_SCRIPT = "bios_client.py"
$APP_NAME = "BIOS_TOOL_PREMIUM"

Write-Host "--- Starting BIOS_TOOL Premium Build Process ---" -ForegroundColor Cyan

# 1. Ensure PyInstaller is available
Write-Host "[1/4] Checking dependencies..."
& $VENV_PYTHON -m pip install pyinstaller | Out-Null

# 2. Clean previous builds
Write-Host "[2/4] Cleaning old build files..."
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }

# 3. Run PyInstaller (Lightweight Modular Build)
Write-Host "[3/4] Running PyInstaller (Onedir / Modular)..."
& $VENV_PYTHON -m PyInstaller `
    --onedir `
    --windowed `
    --name $APP_NAME `
    --add-data "assets;assets" `
    --noconfirm `
    $MAIN_SCRIPT

# 4. Copy External Dependencies to Subfolders
Write-Host "[4/4] Organizing Subfolders..."
$DIST_PATH = "dist\$APP_NAME"

$FOLDERS_TO_COPY = @(
    "assets",
    "ME Analyzer",
    "MCExtractor",
    "BGScriptTool",
    "MCS-Parser",
    "external",
    "BIOSUtilities"
)

foreach ($folder in $FOLDERS_TO_COPY) {
    if (Test-Path $folder) {
        Write-Host "   -> Copying $folder..."
        Copy-Item -Recurse $folder -Destination "$DIST_PATH\$folder"
    }
}

# 4. Finalize
if ($LASTEXITCODE -eq 0) {
    Write-Host "[4/4] Build SUCCESSFUL!" -ForegroundColor Green
    Write-Host "Executable is located at: dist\$APP_NAME.exe" -ForegroundColor Yellow
    Write-Host "Important: Keep the 'bios-Firmware Repository Pack' folder in the same directory as the .exe for full functionality." -ForegroundColor Gray
} else {
    Write-Host "[!] Build FAILED. Check the logs above." -ForegroundColor Red
}
