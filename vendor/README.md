# vendor/ (gitignored)

Downloaded SDKs / headers / datasheets. Yahan **kuch edit nahi** karte.

Ye folder `setup-vendor.ps1` banata hai (workspace root se chalao).

```
vendor/
├─ cmsis-core/Include/          core_cm3.h, core_cm4.h  (~1.4 MB)
├─ cmsis-device-f1/             stm32f103xb.h + startup_stm32f103xb.s
├─ cmsis-device-f4/             stm32f411xe.h, stm32f446xx.h + startups
├─ STM32CubeF1/                 sirf Drivers/CMSIS/Core/Include (sparse)
└─ datasheets/                  <- aap yahan PDFs rakho (RM0016, RM0008, RM0090...)
```

Ye sab **bare-metal** build ke liye kaafi hai (koi HAL nahi).

## HAL / Cube / SPL chahiye ho to

```powershell
# full Cube package (HAL drivers + per-peripheral examples) -- bada hai (~500 MB)
git clone --depth 1 https://github.com/STMicroelectronics/STM32CubeF1 vendor\STM32CubeF1-full

# STM8 SPL (sirf padhne/compare karne ke liye, SDCC build nahi)
#   ST website se "STM8S standard peripheral library" zip download karke
#   vendor\STM8S_StdPeriph_Lib\ me extract karo
```

## Datasheets (manual download, ST login free)

| File | Kya |
|---|---|
| RM0016 | STM8S reference manual |
| PM0044 | STM8 CPU programming manual |
| RM0008 | STM32F1 reference manual |
| RM0090 | STM32F4 reference manual |
| PM0214 | Cortex-M4 programming manual |
| DS5319 | STM8S103F3 datasheet |
| DS10693 / DS10688 | STM32F411RE / F446RE datasheet |

Kaunsa version use kiya, `docs/00-setup-windows.md` ke "Installed versions" me likho.
