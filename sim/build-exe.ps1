# Build a standalone stmlab GUI executable (optional).
# Requires: pip install pyinstaller
# Run from the sim\ folder: .\build-exe.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "pyinstaller not found. Install with: python -m pip install pyinstaller" -ForegroundColor Yellow
    exit 1
}

pyinstaller --noconfirm --windowed --name stmlab-gui `
    --add-data "stmlab;stmlab" `
    --paths "." `
    stmlab\gui.py

Write-Host ""
Write-Host "Built: dist\stmlab-gui\stmlab-gui.exe" -ForegroundColor Green
Write-Host "Zip the dist\stmlab-gui folder and share it; no Python install needed on the target PC."