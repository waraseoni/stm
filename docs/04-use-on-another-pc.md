# How to use this project on another PC

This guide explains how to clone and run `stm-dev` on a fresh Windows machine.
No commands are required for the GUI path.

---

## 1. Minimum requirements

### Simulator + GUI only
- Windows 10/11
- Python 3.10+ (https://www.python.org/downloads/) - check "Add python.exe to PATH"
- Internet connection (for pip install)
- ~50 MB disk space

### Firmware build + real chip (optional)
- ST-Link V2 (or V3 for STM32 only; V2 needed for STM8 SWIM)
- STM32 board (Blue Pill F103C8T6 / Nucleo-F411RE / F446RE)
- STM8 board (STM8S103F3P6 minimum system) - optional
- Toolchains (see section 6)

---

## 2. Clone the repository

```powershell
cd C:\next-vtech          # or any folder you like
git clone https://github.com/waraseoni/stm.git stm-dev
cd stm-dev
```

---

## 3. Install simulator dependencies

```powershell
cd sim
python -m pip install -r requirements.txt
cd ..
```

This installs `unicorn`, `pyelftools`, `keystone-engine`. No C/C++ compiler is needed for the simulator demo or tests.

Optional (for nicer GUI / plots / serial):
```powershell
python -m pip install pyserial matplotlib sv_ttk ttkbootstrap
```

---

## 4. Run the GUI (click-and-run, no commands)

### Option A - double-click launcher
1. Open File Explorer.
2. Go to `C:\next-vtech\stm-dev\sim`.
3. Double-click `stmlab-gui.cmd`.
4. A window opens with three tabs: **Hardware**, **Simulator**, **IC Read/Write**.

### Option B - desktop shortcut (recommended)
**Automatic (easiest):**
```powershell
cd C:\next-vtech\stm-dev
powershell -ExecutionPolicy Bypass -File sim\create-shortcut.ps1
```
This creates "stmlab GUI" on your Desktop.

**Manual (if the script fails):**
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

---

## 5. Run from the command line (optional)

```powershell
$env:PYTHONPATH = "C:\next-vtech\stm-dev\sim"

# Demo (no ARM toolchain needed)
python -m stmlab demo --board f411re --trace

# List boards
python -m stmlab boards

# Run a real firmware ELF
python -m stmlab run path\to\firmware.elf --board f411re --ms 200

# Interactive session
python -m stmlab session path\to\firmware.elf --board f411re

# IC read/write on simulated chip
python -m stmlab ic read 0x40023800 --backend sim --board f411re
python -m stmlab ic read RCC_CR --backend sim --board f411re

# Tests
python -m unittest discover -s sim/tests -t sim -v

# GDB stub
python -m stmlab gdb path\to\firmware.elf --board f411re --port 1234
```

---

## 6. Install toolchains (for firmware build + real chip)

### Quick (winget)
```powershell
winget install Kitware.CMake
winget install Ninja-build.Ninja
winget install ezwinports.make
winget install SDCC.SDCC
winget install xpack-dev-tools.openocd-xpack
winget install Arm.GnuArmEmbeddedToolchain
```

### Versions verified on the dev machine
```
sdcc:              4.5.0
arm-none-eabi-gcc: 14.2.1
cmake:             4.4.4
ninja:             1.13.2
openocd:           0.12.0-7
make:              4.4.1
```

### Paths (add to PATH if not auto-added)
```
C:\Program Files\SDCC\bin
C:\Program Files (x86)\Arm GNU Toolchain arm-none-eabi\14.2 rel1\bin
C:\Users\<you>\AppData\Local\Microsoft\WinGet\Packages\Kitware.CMake_Microsoft.Winget.Source_8wekyb3d8bbwe\cmake-4.4.4-windows-x86_64\bin
C:\Users\<you>\AppData\Local\Microsoft\WinGet\Packages\Ninja-build.Ninja_Microsoft.Winget.Source_8wekyb3d8bbwe
C:\Users\<you>\AppData\Local\Microsoft\WinGet\Packages\xpack-dev-tools.openocd-xpack_Microsoft.Winget.Source_8wekyb3d8bbwe\xpack-openocd-0.12.0-7\bin
C:\Users\<you>\AppData\Local\Microsoft\WinGet\Packages\ezwinports.make_Microsoft.Winget.Source_8wekyb3d8bbwe\bin
```

### Vendor headers
```powershell
cd C:\next-vtech\stm-dev
.\setup-vendor.ps1
```

### Build + flash
```powershell
# STM32
cd stm32\01-f103-blink
cmake --preset debug
cmake --build build
cmake --build build --target flash   # needs OpenOCD + ST-Link

# STM8
cd ..\..\stm8\01-blink-pb5
make
make flash                            # needs stm8flash (or STVP/OpenOCD)
```

### Notes
- `stm8flash` has no Windows binary via winget. Use STVP or OpenOCD (stm8 target) for STM8 flashing, or build stm8flash from source (needs a host C compiler).
- ST-Link V3 does **not** support STM8 SWIM. Use ST-Link V2 for STM8.
- OpenOCD and CubeProgrammer cannot share the same ST-Link at the same time.

---

## 7. Real chip read/write (optional, needs hardware + tools)

- OpenOCD + ST-Link driver (STM32)
- stm8flash (STM8) - or STVP/OpenOCD

Examples:
```powershell
# STM32 via OpenOCD
python -m stmlab ic read 0x40023800 -n 4 --backend openocd --target target/stm32f4x.cfg
python -m stmlab ic read RCC_CR --backend openocd --target target/stm32f4x.cfg
python -m stmlab ic write 0x40020014 0x20 --backend openocd --target target/stm32f4x.cfg
python -m stmlab ic load build\firmware.elf --backend openocd --target target/stm32f4x.cfg

# STM8
python -m stmlab stm8-dump flash.bin --part stm8s103f3
python -m stmlab stm8-flash blink.ihx --part stm8s103f3
```

If the tool is not on PATH, pass `--exe "C:\path\to\tool.exe"`.

---

## 8. GUI tips

- **Hardware tab**: pick MCU from the dropdown (88 parts) to auto-fill target/interface and see equivalent parts from GigaDevice/MindMotion/Geehy/WCH/Artery/etc.
- **ST-Link is NOT a COM port**: it uses USB (WinUSB/libusb). Install ST-Link driver (or Zadig WinUSB) if "Test connection" fails. Serial ports in the GUI are for UART (printf), not SWD.
- **Dark/light theme**: View menu -> Toggle dark mode (proper ttk theming, not just borders).
- **Settings** are saved to `~/.stmlab.json` (board, paths, baudrate, theme, port).
- **Guided exercises**: Help menu -> Guided exercises (opens exercise folders).

---

## 9. Troubleshooting

- `ModuleNotFoundError: No module named 'stmlab'` -> set `$env:PYTHONPATH = "C:\next-vtech\stm-dev\sim"`.
- `python` not recognized -> reinstall Python with "Add to PATH", or use `py`.
- OpenOCD/stm8flash not found -> install or pass `--exe`.
- GUI does not open -> run `python -m stmlab.gui` in PowerShell to see the error.
- Firmware ELF fails to load -> build with soft-float ABI (`-mfloat-abi=soft`); hard-float VFP is not supported by the simulator.
- CMake "Could not find toolchain file" -> use `cmake --preset` (presets set the toolchain file).
- STM8 "could not open usb device" -> WinUSB driver missing (Zadig) or V3 used (no SWIM).

---

## 10. What works without toolchains

- Simulator demo (`stmlab demo`)
- Simulator tests (`unittest`, 19 tests)
- IC read/write on the simulated chip (`--backend sim`)
- GUI for all of the above
- MCU database + equivalents browser

---

## 11. Notes

- `vendor/` and `tools/` are gitignored. Run `.\setup-vendor.ps1` if you want to build firmware.
- The simulator is approximate (timing, peripherals). Real silicon may differ.
- STM8 cannot be simulated by this core; use SDCC `ucsim`/`sstm8` for STM8 firmware testing.
- All exercise code is **unverified** until built on real hardware.
