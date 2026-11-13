# Setup on Windows (ST-Link + SDCC + ARM GCC)

Sab kuch `tools/` me portable rakho, PATH me sirf zaroori cheezein add karo.
Install hone ke baad versions yahin neeche likh do — debugging me kaam aata hai.

## 0. ST-Link driver (dono tracks ke liye)

- Original ST-Link: ST website se "ST-Link USB driver" install karo.
- Clone V2: Windows 10/11 aksar khud le leta hai. Agar flasher "no device" bole:
  - **Zadig** chalao -> ST-Link ko **WinUSB** driver do (stm8flash / st-flash /
    OpenOCD isi se baat karte hain).
  - Ye driver change CubeProgrammer/CubeIDE ko tod sakta hai — dono set use karne
    ho to ek machine par ek hi driver family rakho, ya STVP use karo.
- **ST-Link V3 par STM8 SWIM nahi hai.** STM8 ke liye V2 zaroori.

## 1. STM8 track

1. **SDCC** (compiler): sdcc.sourceforge.net -> Windows installer (4.4+).
   - Check: `sdcc -v` aur `sdcc -mstm8 --help | Select-String stm8`
2. **stm8flash** (flasher, open source): github.com/vdudouyt/stm8flash
   - Windows binary release lo, `tools\stm8flash\` me rakho.
   - Check: `stm8flash -h`
3. **GNU make** (Makefile ke liye): `winget install ezwinports.make`
   ya MSYS2/mingw32-make. Check: `make -v`
4. Optional: **STVP** (ST Visual Programmer) — driver jhanjhat ke bina flash karne
   ka easiest rasta. **STVD** legacy IDE hai, sirf debug fallback ke liye.

Flash command (template me bhi hai):
```powershell
stm8flash -c stlinkv2 -p stm8s103f3 -w blink.ihx
```

## 2. STM32 track

### Option A — STM32CubeIDE (beginner friendly, sab included)
ST website se download (login free). Isme GCC, debugger, CubeMX, programmer sab hai.
Sirf `docs` + experiments ke liye best. Build system CubeIDE ka apna hota hai,
git me `.cproject`/`.project` aayenge.

### Option B — VS Code + CMake (recommended for code study)
- **arm-none-eabi-gcc**: developer.arm.com (GNU Toolchain for Embedded) ya
  `winget install Arm.GnuArmEmbeddedToolchain` (package name badal sakta hai,
  `winget search arm-none-eabi` se confirm karo).
- **CMake** + **Ninja**: `winget install Kitware.CMake Ninja-build.Ninja`
- **STM32CubeCLT** (ST ki official GCC+programmer+OpenOCD CLI bundle) — ST site par
  "STM32CubeCLT" search karo. Isse `STM32_Programmer_CLI.exe` milta hai.
- **OpenOCD**: `winget install xpack-dev-tools.openocd-xpack` (ya CubeCLT wala use karo)
- VS Code extensions: `C/C++` (ms-vscode.cpptools), `CMake Tools`,
  `Cortex-Debug` (marus25), `Serial Monitor` (ms-vscode.vscode-serial-monitor).

Check:
```powershell
arm-none-eabi-gcc --version
cmake --version ; ninja --version ; openocd --version
```

Flash + debug (SWD, ST-Link):
```powershell
openocd -f interface/stlink.cfg -f target/stm32f1x.cfg -c "program build/app.elf verify reset exit"
```

## 3. Sanity checklist (ye 5 cheezein chal jayein tabhi aage badho)

- [ ] `sdcc -mstm8 --version` -> 4.x
- [ ] `stm8flash -h` -> help print ho
- [ ] `arm-none-eabi-gcc --version`
- [ ] `openocd -f interface/stlink.cfg -f target/stm32f1x.cfg -c "init;exit"` -> no error
- [ ] board par blink + UART par `printf` output

## Installed versions (bharke rakhna)

```
sdcc:
stm8flash:
arm-none-eabi-gcc:
cmake / ninja:
openocd:
STM32CubeProgrammer:
ST-Link firmware:
```

## Common problems

| Symptom | Cause / fix |
|---|---|
| `stm8flash: could not open usb device` | WinUSB driver missing (Zadig) ya V3 use ho raha hai |
| STM32 "target not found" | SWD wiring (SWDIO/SWCLK/GND/3V3), board ko power, BOOT0 low |
| `arm-none-eabi-gcc: command not found` | PATH me toolchain `bin` add karo, naya terminal kholo |
| CubeProgrammer chal raha hai par OpenOCD nahi | Dono ek hi ST-Link ko grab karte hain — ek time par ek hi chalao |
| `make: command not found` | `winget install ezwinports.make` |
