# stm-dev — STM8 + STM32 development & code study

Ek hi workspace me dono families. Har exercise apna folder, git me track,
vendor SDK git me nahi (bahut bada hai) — `vendor/` me download karke rakhenge.

## Folder map

```
stm-dev/
├─ README.md              <- ye file: plan + progress
├─ setup-vendor.ps1       <- CMSIS headers laata hai (ek baar chalana hai)
├─ docs/                  <- setup, register notes, resources (padhne ke liye)
│  ├─ 00-setup-windows.md
│  ├─ 01-stm8-notes.md
│  ├─ 02-stm32-notes.md
│  └─ resources.md
├─ stm8/                  <- STM8 projects (SDCC + stm8flash)
│  └─ 01-blink-pb5/
├─ stm32/                 <- STM32 bare-metal projects (CMake + GCC + OpenOCD)
│  ├─ cmake/              <- ARM toolchain file (dono boards ke liye)
│  ├─ vscode/             <- launch.json / tasks.json templates
│  ├─ docs/cubeide-workflow.md
│  ├─ 01-f103-blink/      <- Blue Pill, 72 MHz, CMSIS only
│  └─ 02-f4-blink/        <- Nucleo-F411RE / F446RE
├─ study/                 <- vendor examples ko copy karke annotate karne ke liye
├─ tools/   (gitignored)  <- portable toolchains, flashers, drivers
└─ vendor/  (gitignored)  <- CMSIS headers, Cube packages, datasheets
```

## Do tracks, ek workflow

| | STM8 | STM32 |
|---|---|---|
| Compiler | SDCC (`sdcc -mstm8`) | arm-none-eabi-gcc |
| Build | Makefile | CMake + Ninja (presets) |
| Flash/debug | ST-Link **V2** + stm8flash / STVP | ST-Link V2/V3 + OpenOCD / CubeProgrammer |
| SDK | STM8S SPL (sirf padhne ke liye) | CMSIS (HAL/LL baad me) |
| Role | registers samajhne ki lab | asli product / career |

**Rule:** naya peripheral pehle STM8 par bare-register likho (chhota, simple),
phir STM32 par bare-register, phir HAL wala version dekho. Isi diff se
register-level samajh aati hai.

## Quickstart (is machine par abhi tak install nahi hai)

```powershell
# 1) toolchains -- docs/00-setup-windows.md follow karo
#    STM8 : sdcc + stm8flash + make
#    STM32: arm-none-eabi-gcc + cmake + ninja + openocd

# 2) STM8 blink
cd stm8\01-blink-pb5
make ; make flash

# 3) STM32 blink (pehle headers)
cd ..\..
.\setup-vendor.ps1
cd stm32\01-f103-blink
cmake --preset debug ; cmake --build build ; cmake --build build --target flash
```

## Learning path

- [ ] **Phase 0 — toolchain (1-2 din).** Dono toolchains install, blink, UART par
      `printf` working. Yahan 80% log atakte hain; isse pehle aage na badhein.
- [ ] **Phase 1 — STM8 registers.** GPIO, clock, timers (TIM4), UART1,
      interrupts, I2C, ADC1, EEPROM. Har topic: RM chapter padho -> khud likho ->
      SPL se compare.
- [ ] **Phase 2 — STM32 bare-metal (CMSIS only).** RCC/GPIO, SysTick,
      NVIC/EXTI, USART, TIM PWM + input capture, SPI, I2C, ADC + DMA.
- [ ] **Phase 3 — HAL/LL + CubeMX.** CubeMX se project banao, generated code
      ko Phase 2 ke apne code se map karo. SWD debug, breakpoints, watch, ITM/SWO.
- [ ] **Phase 4 — system level.** FreeRTOS, bootloader (UART/CAN), low-power,
      flash wear-leveling, watchdog strategy.

## Study method (sabse important)

Har peripheral ke liye yahi loop repeat karo:

1. Datasheet/RM ka wo chapter padho (sirf relevant section).
2. Register table se bit meanings notebook me likho (`docs/` me).
3. Bare-metal code khud likho — copy-paste nahi.
4. Wahi cheez SPL/HAL me kholo aur line-by-line diff karo: "ye bit yahan
   kyun set kiya?".
5. Ek chhoti "gotcha" line `docs/` notes me add karo. 6 mahine baad yahi
   notes aapki asli asset hongi.

`study/` me vendor example ka folder copy karo, phir usi file me apne comments
(`// Q:`, `// NOTE:`) add karo. Original ko chhedna nahi.

## Roz ka workflow

```powershell
git checkout -b ex/tim4-pwm        # ek exercise = ek branch (optional)
# code likho, build, board par flash, test
git add -A ; git commit -m "stm8: TIM4 PWM on PC3, prescaler table noted"
```

Commit message me `stm8:` / `stm32:` prefix rakho — history me filter karna easy.

## Board / hardware (minimum kit)

- ST-Link **V2** clone (STM32 SWD + STM8 SWIM dono). **ST-Link V3 STM8 support
  nahi karta** — V3 ho to bhi ek V2 rakho.
- STM32: Blue Pill (F103C8T6) + Nucleo-F411RE/F446RE (onboard debugger).
- STM8: STM8S103F3P6 minimum system board (LED PB5 par).
- USB-UART (CH340/CP2102) — `printf` ke liye (Nucleo par ye onboard hai).
- Logic analyzer (8ch clone chalega) — I2C/SPI debug me time bachega.

## Progress

- [x] Workspace scaffold + docs
- [x] STM8 blink template (`stm8/01-blink-pb5`)
- [x] STM32 blink template: F103 + F4 (Nucleo)
- [ ] Toolchains installed + versions doc me likhe
- [ ] STM8 blink board par chalaya
- [ ] STM32 blink board par chalaya
- [ ] UART printf dono par
- [ ] pehla interrupt (EXTI / TIM)

> Status: STM8/STM32 ke source aur linker scripts likhe gaye hain; ARM GCC
> install hone ke baad build verify hoga. STM8 template SDCC se verify hua hai.
