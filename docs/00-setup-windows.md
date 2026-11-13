# Setup on Windows (ST-Link + SDCC + ARM GCC + bare-metal)

Sab kuch `tools/` me portable rakho, PATH me sirf zaroori cheezein add karo.
Install hone ke baad versions yahin neeche likh do — debugging me kaam aata hai.

## 0. ST-Link driver (dono tracks ke liye)

- Original ST-Link: ST website se "ST-Link USB driver" install karo.
- Clone V2: Windows 10/11 aksar khud le leta hai. Agar flasher "no device" bole:
  - **Zadig** chalao -> ST-Link ko **WinUSB** driver do (stm8flash / OpenOCD isi
    se baat karte hain).
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
   Check: `make -v`
4. Optional: **STVP** (ST Visual Programmer) — driver jhanjhat ke bina flash karne
   ka easiest rasta. **STVD** legacy IDE hai, sirf debug fallback ke liye.

```powershell
cd stm8\01-blink-pb5
make            # ya: .\build.ps1
make flash      # ya: .\build.ps1 -Flash
```

## 2. STM32 track (bare-metal, recommended)

```powershell
winget install Arm.GnuArmEmbeddedToolchain     # arm-none-eabi-gcc
winget install Kitware.CMake
winget install Ninja-build.Ninja
winget install xpack-dev-tools.openocd-xpack   # ya CubeCLT ka OpenOCD
```

Check:
```powershell
arm-none-eabi-gcc --version
cmake --version ; ninja --version ; openocd --version
```

Phir workspace root se ek baar vendor headers laao:

```powershell
.\setup-vendor.ps1
```

Aur build + flash:

```powershell
cd stm32\01-f103-blink
cmake --preset debug
cmake --build build
cmake --build build --target flash
```

> Note: `winget install Arm.GnuArmEmbeddedToolchain` ek MSI installer chalata hai
> jo admin/UAC maang sakta hai. Na chale to ARM ka official `.zip` download karke
> `tools\arm-gnu-toolchain\` me extract karo aur uska `bin\` PATH me add karo.

### Optional: STM32CubeIDE (HAL/CubeMX ke liye)
ST website se download (login free). Isme GCC, debugger, CubeMX sab hai.
Ye CMake wale projects ko replace nahi karta — HAL seekhne/quick test ke liye
side-by-side rakho. Workflow: `stm32/docs/cubeide-workflow.md`.

### Optional: STM32CubeProgrammer (CLI)
CubeIDE ke bina flash/option-bytes ke liye. `STM32_Programmer_CLI.exe -c port=SWD -w app.bin 0x08000000 -v -rst`.

## 3. Sanity checklist (ye 5 cheezein chal jayein tabhi aage badho)

- [ ] `sdcc -mstm8 --version` -> 4.x
- [ ] `stm8flash -h` -> help print ho
- [ ] `arm-none-eabi-gcc --version`
- [ ] `openocd -f interface/stlink.cfg -f target/stm32f1x.cfg -c "init;exit"` -> no error
- [ ] board par blink + UART par `printf` output

## 4. VS Code (optional, par recommended)

Extensions: `ms-vscode.cpptools`, `ms-vscode.cmake-tools`, `marus25.cortex-debug`,
`ms-vscode.vscode-serial-monitor`, `dan-c-underwood.arm`.

`stm32/vscode/` ki files project ke `.vscode/` me copy karo -> F5 se debug.

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
| `Could not find toolchain file` | `cmake --preset` use karo, ya `-DCMAKE_TOOLCHAIN_FILE` sahi path do |
| `No CMAKE_C_COMPILER could be found` | ARM GCC PATH me nahi hai |
| CubeProgrammer chal raha hai par OpenOCD nahi | Dono ek hi ST-Link ko grab karte hain — ek time par ek hi chalao |
| `make: command not found` | `winget install ezwinports.make` |
