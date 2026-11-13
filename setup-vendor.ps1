#Requires -Version 5.1
<#
.SYNOPSIS
  vendor/ setup -- sirf CMSIS headers (bare-metal projects ke liye kaafi hai).

.DESCRIPTION
  ST ne CMSIS device headers alag repos me rakhe hain. Yahan hum sirf wo files
  laate hain jo bare-metal build ke liye chahiye:

    vendor/cmsis-core/Include/          core_cm3.h, core_cm4.h ...
    vendor/cmsis-device-f1/Include/     stm32f103xb.h ...
    vendor/cmsis-device-f1/Source/...   startup_stm32f103xb.s
    vendor/cmsis-device-f4/Include/     stm32f411xe.h, stm32f446xx.h ...
    vendor/cmsis-device-f4/Source/...   startup_*.s

  HAL/SPL chahiye ho to alag se full Cube package download karo (README dekho).

.EXAMPLE
  .\setup-vendor.ps1
#>
[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$vendor = Join-Path $PSScriptRoot 'vendor'
New-Item -ItemType Directory -Force -Path $vendor | Out-Null

function Ensure-SparseRepo {
    param([string]$Url, [string]$Dir, [string[]]$Paths, [switch]$Reuse)

    if ((Test-Path (Join-Path $Dir '.git')) -and -not $Force) {
        Write-Host "  skip (already present) $Dir"
    } else {
        if (Test-Path $Dir) { Remove-Item -Recurse -Force $Dir }
        Write-Host "  clone $Url"
        git clone --depth 1 --filter=blob:none --sparse -q $Url $Dir
        if ($LASTEXITCODE -ne 0) { throw "git clone failed: $Url" }
    }

    git -C $Dir sparse-checkout set --cone @Paths | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "sparse-checkout failed: $Dir" }
}

Write-Host "== vendor setup ==" -ForegroundColor Cyan

Ensure-SparseRepo -Url 'https://github.com/STMicroelectronics/cmsis-device-f1' `
                  -Dir (Join-Path $vendor 'cmsis-device-f1') `
                  -Paths @('Include', 'Source/Templates')

Ensure-SparseRepo -Url 'https://github.com/STMicroelectronics/cmsis-device-f4' `
                  -Dir (Join-Path $vendor 'cmsis-device-f4') `
                  -Paths @('Include', 'Source/Templates/gcc')

# CMSIS core headers STM32CubeF1 ke andar hain; sirf Core/Include copy karte hain.
$cube = Join-Path $vendor 'STM32CubeF1'
Ensure-SparseRepo -Url 'https://github.com/STMicroelectronics/STM32CubeF1' `
                  -Dir $cube -Paths @('Drivers/CMSIS/Core/Include')

$coreSrc = Join-Path $cube 'Drivers/CMSIS/Core/Include'
$coreDst = Join-Path $vendor 'cmsis-core/Include'
if (Test-Path $coreDst) { Remove-Item -Recurse -Force $coreDst }
New-Item -ItemType Directory -Force -Path (Split-Path $coreDst) | Out-Null
Copy-Item -Recurse $coreSrc $coreDst

# --- verify -----------------------------------------------------------------
$checks = @(
    'cmsis-core/Include/core_cm3.h',
    'cmsis-core/Include/core_cm4.h',
    'cmsis-device-f1/Include/stm32f103xb.h',
    'cmsis-device-f1/Source/Templates/gcc/startup_stm32f103xb.s',
    'cmsis-device-f4/Include/stm32f411xe.h',
    'cmsis-device-f4/Include/stm32f446xx.h',
    'cmsis-device-f4/Source/Templates/gcc/startup_stm32f411xe.s',
    'cmsis-device-f4/Source/Templates/gcc/startup_stm32f446xx.s'
)

$missing = @()
foreach ($c in $checks) {
    if (-not (Test-Path (Join-Path $vendor $c))) { $missing += $c }
}

if ($missing.Count -gt 0) {
    Write-Host "`nFAILED -- ye files nahi mili:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  $_" }
    exit 1
}

Write-Host "`nOK -- CMSIS headers ready." -ForegroundColor Green
Write-Host @"

Next steps:
  1. STM32 bare-metal build:
       cd stm32\01-f103-blink
       cmake --preset debug
       cmake --build build
       cmake --build build --target flash

  2. Full Cube package (HAL + examples) chahiye to:
       git clone --depth 1 https://github.com/STMicroelectronics/STM32CubeF1 vendor\STM32CubeF1-full
"@
