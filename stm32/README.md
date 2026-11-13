# stm32/ — bare-metal projects (VS Code + CMake + GCC + OpenOCD)

Do boards support hain, dono ek hi toolchain file se:

| Folder | Board | Chip | LED | Clock (template) |
|---|---|---|---|---|
| `01-f103-blink` | Blue Pill | STM32F103C8T6 | PC13 (active low) | HSE 8 MHz -> PLL 72 MHz |
| `02-f4-blink`   | Nucleo-F411RE | STM32F411RET6 | PA5 (active high) | HSI 16 MHz (PLL `03` me) |
| `02-f4-blink`   | Nucleo-F446RE | STM32F446RET6 | PA5 (active high) | HSI 16 MHz (PLL `03` me) |

Nucleo wale exercises (dono boards par same code, sirf preset badalta hai):

| Folder | Topic | Peripherals / pins |
|---|---|---|
| `03-clock-pll` | F4 clock tree: VOS, overdrive, flash latency, APB limits | 84 MHz (F411) / 180 MHz (F446), SysTick |
| `04-uart-printf` | `printf` retarget to ST-Link VCP | USART2 PA2/PA3 AF7, 115200 |
| `05-uart-ringbuffer` | RX interrupt + ring buffer + echo | USART2 RXNE IRQ, `__WFI` |
| `06-tim-pwm` | Hardware PWM, LED fade | TIM2_CH1 PA5 AF1, 1 kHz |

Saare projects **CMSIS only** hain — koi HAL nahi, apna startup + linker script.
Yahi register-level seekhne ka rasta hai.

## Pehle ek baar (workspace root se)

```powershell
.\setup-vendor.ps1
```

Ye `vendor/` me CMSIS core + device headers + startup files laata hai (~35 MB).
`vendor/` gitignored hai, isliye naye machine par sirf ye script dobara chalana hai.

## Build

```powershell
cd stm32\01-f103-blink
cmake --preset debug          # configure
cmake --build build           # build -> build/app.elf, .bin, .hex
cmake --build build --target flash
```

Nucleo par board choose karo:

```powershell
cd stm32\04-uart-printf
cmake --preset f411re         # ya f446re
cmake --build build
cmake --build build --target flash
```

Board badalna ho to preset badalne ke baad `build/` delete karna padega
(CMake cache board-specific hai): `Remove-Item -Recurse build`.

`cmake --build build --target size` section-wise RAM/flash dikhata hai.

## Debug (VS Code)

1. `stm32/vscode/` ki files apne project ke `.vscode/` me copy karo.
2. `launch.json` me `device` aur `configFiles` apne board ke hisaab se badlo.
3. F5 -> Cortex-Debug OpenOCD server raise karega, `main` par rukega.

`openocd.cfg` ab har project ke `build/` me **auto-generate** hota hai
(`stm32_project.cmake` likhta hai). CLI debug:

```powershell
openocd -f build/openocd.cfg
# doosre terminal me:
arm-none-eabi-gdb build/app.elf -ex "target extended-remote :3333"
```

## Shared build layer

Har project ki `CMakeLists.txt` sirf 3 cheezein batati hai: naam, board, sources.
Baaki sab `common/` me hai — ek jagah fix karo, sab projects ko milega:

```
stm32/
├─ common/
│  ├─ cmake/stm32_project.cmake   <- BOARD -> defines, startup, ld, openocd, targets
│  ├─ src/system_stm32f1xx.c
│  ├─ src/system_stm32f4xx.c      <- FPU enable + VTOR (ST ka HSE wala nahi)
│  └─ ld/STM32F103C8Tx.ld, STM32F411RE.ld, STM32F446RE.ld
├─ cmake/arm-none-eabi-gcc.cmake  <- toolchain file (-DCPU=cortex-m3|m4)
└─ NN-topic/
   ├─ CMakeLists.txt
   ├─ CMakePresets.json
   ├─ src/main.c
   └─ README.md                   <- kya seekha, kya atka
```

Naya project banane ka fastest rasta: `06-tim-pwm` copy karo, `CMakeLists.txt`
me project naam aur `SOURCES` badlo, phir `main.c` likho.

> Float: presets default **soft-float** use karte hain. F4 ka FPU chahiye to
> preset me `"FPU": "fpv4-sp-d16"` add karo (hard-float, `system_stm32f4xx.c`
> pehle se CPACR enable karta hai).

## Planned sequence

- [x] `01-f103-blink` — RCC/GPIO, SysTick, non-blocking blink
- [x] `02-f4-blink` — F4 GPIO (MODER/OTYPER/PUPDR), board choice
- [x] `03-clock-pll` — F4 84/180 MHz: FLASH latency, VOS/overdrive, APB1 limit
- [x] `04-uart-printf` — USART2 TX + `_write` retarget, 115200
- [x] `05-uart-ringbuffer` — RX interrupt + ring buffer
- [x] `06-tim-pwm` — TIM2 CH1 PWM, duty update
- [ ] `07-exti-button` — EXTI + debounce (state machine)
- [ ] `08-i2c-oled` — I2C hardware + SSD1306
- [ ] `09-spi-flash` — SPI + W25Q flash ID
- [ ] `10-adc-dma` — ADC + DMA circular, moving average
- [ ] `11-freertos` — FreeRTOS, 2 tasks + queue

## CubeMX / CubeIDE wala rasta

`docs/cubeide-workflow.md` — jab HAL/CubeMX se project banana ho. Wahan
generated code ko *padhne* ka tarika likha hai (usko blindly edit nahi karte).
