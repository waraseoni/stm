# How to use this project on another PC

This guide explains how to clone and run `stm-dev` on a fresh Windows machine.
No commands are required for the GUI path.

---

## 1. Minimum requirements (simulator + GUI only)

- Windows 10/11
- Python 3.10+ (https://www.python.org/downloads/) - check "Add python.exe to PATH"
- Internet connection (for pip install)
- ~50 MB disk space

## 2. Clone the repository

```powershell
cd C:\next-vtech          # or any folder you like
git clone https://github.com/waraseoni/stm.git stm-dev
cd stm-dev
```

## 3. Install simulator dependencies

```powershell
cd sim
python -m pip install -r requirements.txt
cd ..
```

This installs `unicorn`, `pyelftools`, `keystone-engine`. No C/C++ compiler is needed for the simulator demo or tests.

## 4. Run the GUI (click-and-run, no commands)

### Option A - double-click launcher
1. Open File Explorer.
2. Go to `C:\next-vtech\stm-dev\sim`.
3. Double-click `stmlab-gui.cmd`.
4. A window opens with two tabs: **Simulator** and **IC Read/Write**.

### Option B - desktop shortcut (recommended)
1. Right-click on Desktop -> New -> Shortcut.
2. Location: `pythonw.exe -m stmlab.gui`
3. Name: `stmlab GUI`
4. Right-click the shortcut -> Properties -> "Start in": `C:\next-vtech\stm-dev\sim`
5. OK. Now double-click the shortcut anytime.

### Option C - manual (if the above fail)
```powershell
$env:PYTHONPATH = "C:\next-vtech\stm-dev\sim"
python -m stmlab.gui
```

## 5. Run from the command line (optional)

```powershell
$env:PYTHONPATH = "C:\next-vtech\stm-dev\sim"

# Demo (no ARM toolchain needed)
python -m stmlab demo --board f411re --trace

# List boards
python -m stmlab boards

# Run a real firmware ELF (needs ARM GCC build)
python -m stmlab run path\to\firmware.elf --board f411re --ms 200

# Interactive session
python -m stmlab session path\to\firmware.elf --board f411re

# IC read/write on simulated chip
python -m stmlab ic read 0x40023800 --backend sim --board f411re
python -m stmlab ic write 0x40020014 0x20 --backend sim --board f411re

# Tests
python -m unittest discover -s sim/tests -t sim -v
```

## 6. Firmware build + simulate (optional, needs toolchains)

Follow `docs/00-setup-windows.md` to install:
- STM8: SDCC + stm8flash + make
- STM32: arm-none-eabi-gcc + cmake + ninja + openocd

Then:
```powershell
cd C:\next-vtech\stm-dev
.\setup-vendor.ps1            # fetch CMSIS headers (once)
cd stm32\04-uart-printf
cmake --preset debug
cmake --build build
cd ..\..\..
$env:PYTHONPATH = "C:\next-vtech\stm-dev\sim"
python -m stmlab run stm32\04-uart-printf\build\firmware.elf --board f411re --ms 200
```

## 7. Real chip read/write (optional, needs hardware + tools)

- OpenOCD + ST-Link driver (STM32)
- stm8flash (STM8)

Examples:
```powershell
# STM32 via OpenOCD
python -m stmlab ic read 0x40023800 -n 4 --backend openocd --target target/stm32f4x.cfg
python -m stmlab ic write 0x40020014 0x20 --backend openocd --target target/stm32f4x.cfg
python -m stmlab ic load build\firmware.elf --backend openocd --target target/stm32f4x.cfg

# STM8 via stm8flash
python -m stmlab stm8-dump flash.bin --part stm8s103f3
python -m stmlab stm8-flash blink.ihx --part stm8s103f3
```

If the tool is not on PATH, pass `--exe "C:\path\to\tool.exe"`.

## 8. Troubleshooting

- `ModuleNotFoundError: No module named 'stmlab'` -> set `$env:PYTHONPATH = "C:\next-vtech\stm-dev\sim"`.
- `python` not recognized -> reinstall Python with "Add to PATH", or use `py` instead of `python`.
- OpenOCD/stm8flash not found -> install or pass `--exe`.
- GUI does not open -> run `python -m stmlab.gui` in PowerShell to see the error.
- Firmware ELF fails to load -> build with soft-float ABI (`-mfloat-abi=soft`); hard-float VFP is not supported by the simulator.

## 9. What works without toolchains

- Simulator demo (`stmlab demo`)
- Simulator tests (`unittest`)
- IC read/write on the simulated chip (`--backend sim`)
- GUI for all of the above

## 10. Notes

- `vendor/` and `tools/` are gitignored. Run `.\setup-vendor.ps1` if you want to build firmware.
- The simulator is approximate (timing, peripherals). Real silicon may differ.
- STM8 cannot be simulated by this core; use SDCC `ucsim`/`sstm8` for STM8 firmware testing.
