# stm-dev — STM8 + STM32 development & code study

Ek hi workspace me dono families. Har exercise apna folder, git me track,
vendor SDK git me nahi (bahut bada hai) — `vendor/` me download karke rakhenge.

## Folder map

```
stm-dev/
├─ README.md              <- ye file: plan + progress
├─ docs/                  <- setup, register notes, resources (padhne ke liye)
│  ├─ 00-setup-windows.md
│  ├─ 01-stm8-notes.md
│  ├─ 02-stm32-notes.md
│  └─ resources.md
├─ stm8/                  <- STM8 projects (SDCC + stm8flash)
│  └─ 01-blink-pb5/
├─ stm32/                 <- STM32 projects (baseline + HAL)
├─ study/                 <- vendor examples ko copy karke annotate karne ke liye
├─ tools/   (gitignored)  <- portable toolchains, flashers, drivers
└─ vendor/  (gitignored)  <- ST SPL / Cube packages / reference code
```

## Do tracks, ek workflow

| | STM8 | STM32 |
|---|---|---|
| Compiler | SDCC (`sdcc -mstm8`) | arm-none-eabi-gcc |
| Build | Makefile / CMake | CMake (ya CubeIDE generated) |
| Flash/debug | ST-Link **V2** + stm8flash / STVP | ST-Link V2/V3 + CubeProgrammer / OpenOCD |
| SDK | STM8S SPL (sirf padhne ke liye) | CMSIS + HAL/LL |
| Role | registers samajhne ki lab | asli product / career |

**Rule:** naya peripheral pehle STM8 par bare-register likho (chhota, simple),
phir STM32 par bare-register, phir HAL wala version dekho. Isi diff se
register-level samajh aati hai.

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
- STM32 board: Blue Pill (F103C8T6, sasta) ya Nucleo-F411/F446 (debugger onboard).
- STM8 board: STM8S103F3P6 minimum system board (LED PB5 par).
- USB-UART (CH340/CP2102) — dono par `printf` ke liye.
- Logic analyzer (8ch clone chalega) — I2C/SPI debug me time bachega.

## Progress

- [ ] Toolchains installed + versions doc me likhe
- [ ] `stm8/01-blink-pb5` board par chalaya
- [ ] STM32 blink (apne board par)
- [ ] UART printf dono par
- [ ] pehla interrupt (EXTI / TIM)
