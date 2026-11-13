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
│  ├─ common.mk           <- shared build rules
│  ├─ 01-blink-pb5/       <- GPIO blink
│  ├─ 02-tim4-interrupt/  <- timer ISR + vector 25
│  ├─ 03-uart-printf/     <- UART1 TX
│  └─ 04-uart-echo/       <- UART1 RX interrupt + ring buffer
├─ stm32/                 <- STM32 bare-metal projects (CMake + GCC + OpenOCD)
│  ├─ common/             <- shared cmake function, system files, linker scripts
│  ├─ cmake/              <- ARM toolchain file (dono boards ke liye)
│  ├─ vscode/             <- launch.json / tasks.json templates
│  ├─ docs/cubeide-workflow.md
│  ├─ 01-f103-blink/      <- Blue Pill, 72 MHz, CMSIS only
│  ├─ 02-f4-blink/        <- Nucleo-F411RE / F446RE
│  ├─ 03-clock-pll/       <- F4 84 / 180 MHz, VOS + overdrive
│  ├─ 04-uart-printf/     <- USART2 + _write retarget
│  ├─ 05-uart-ringbuffer/ <- RX ISR + ring buffer
│  └─ 06-tim-pwm/         <- TIM2 CH1 PWM fade
├─ sim/                   <- stmlab: STM32 simulator + IC read/write CLI
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

# 4) Simulator (bina hardware/ARM GCC ke demo)
cd ..\..
python -m pip install -r sim\requirements.txt
$env:PYTHONPATH="$PWD\sim"; python -m stmlab demo --trace
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
- [x] STM8: blink, TIM4 interrupt, UART TX, UART RX echo (4 exercises)
- [x] STM32: F103 + F4 blink, PLL, UART printf, RX ring buffer, PWM (6 exercises)
- [x] Shared build layer (`stm32/common`, `stm8/common.mk`) + vendor script
- [x] `sim/stmlab`: Unicorn-based STM32 simulator (UART/GPIO/SysTick/NVIC basics) + IC read/write CLI (OpenOCD/stm8flash/sim)
- [ ] Toolchains installed + versions doc me likhe
- [ ] Board par pehla flash + UART output
- [ ] `07-exti-button` (STM32 EXTI + debounce)
- [ ] Simulator ko real ELF builds se verify (ARM GCC chahiye) + aur peripherals (EXTI/DMA/ADC...)

> Status: source, linker scripts aur build files likhe gaye hain. Is machine par
> SDCC / ARM GCC abhi install nahi hain, isliye **compile verify pending** hai.
> Jo verify hua: vendor headers ke asli naam/macros (`RCC_CFGR_PLLMULL9`,
> `GPIO_ODR_OD5`, `SysTick_CTRL_*`, `USART2_IRQn`, `TIM_CCMR1_OC1M_2`,
> `PWR_CR_ODEN`/`PWR_CSR_ODSWRDY`, `FLASH_ACR_LATENCY_5WS`), startup file names,
> include chain, STM8 base addresses/vector numbers (SPL source + datasheet),
> aur `setup-vendor.ps1` ka actual run. Pehla `cmake --build` / `make` chalane
> par agar koi error aaye to `docs/` me note karo — scaffolding ka point yahi hai.
