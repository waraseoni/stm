# Makefile na ho to ye chalao (PowerShell, project folder ke andar)
#   .\build.ps1            -> build only
#   .\build.ps1 -Flash     -> build + flash
param([switch]$Flash)

$ErrorActionPreference = 'Stop'

$sdcc = 'sdcc'
if (-not (Get-Command $sdcc -ErrorAction SilentlyContinue)) {
    throw "sdcc PATH me nahi hai. docs/00-setup-windows.md dekho."
}

& $sdcc -mstm8 --std-c99 --opt-code-speed -o blink.ihx main.c
if ($LASTEXITCODE -ne 0) { throw "build fail (exit $LASTEXITCODE)" }
Write-Host "OK -> blink.ihx" -ForegroundColor Green

if ($Flash) {
    & stm8flash -c stlinkv2 -p stm8s103f3 -w blink.ihx
    if ($LASTEXITCODE -ne 0) { throw "flash fail (exit $LASTEXITCODE)" }
    Write-Host "Flashed." -ForegroundColor Green
}
