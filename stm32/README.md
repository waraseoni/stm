# stm32/ — bare-metal projects (VS Code + CMake + GCC + OpenOCD)

Do boards support hain, dono ek hi toolchain file se:

| Folder | Board | Chip | LED | Clock (template) |
|---|---|---|---|---|
| `01-f103-blink` | Blue Pill | STM32F103C8T6 | PC13 (active low) | HSE 8 MHz -> PLL 72 MHz |
| `02-f4-blink`   | Nucleo-F411RE | STM32F411RET6 | PA5 (active high) | HSI 16 MHz (PLL next exercise) |
| `02-f4-blink`   | Nucleo-F446RE | STM32F446RET6 | PA5 (active high) | HSI 16 MHz (PLL next exercise) |

Dono projects **CMSIS only** hain — koi HAL nahi, apna startup + linker script.
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
cd stm32\02-f4-blink
cmake --preset f411re         # ya f446re
cmake --build build
cmake --build build --target flash
```

Board badalna ho to preset badalne ke baad `build/` delete karna padega
(CMake cache board-specific hai): `Remove-Item -Recurse build`.

## Debug (VS Code)

1. `stm32/vscode/` ki files apne project ke `.vscode/` me copy karo.
2. `launch.json` me `device` aur `configFiles` apne board ke hisaab se badlo.
3. F5 -> Cortex-Debug OpenOCD server raise karega, `main` par rukega.

CLI debug (GUI ke bina):
```powershell
openocd -f openocd.cfg
# doosre terminal me:
arm-none-eabi-gdb build/app.elf -ex "target extended-remote :3333"
```

## Folder pattern (naye project ke liye)

```
stm32/NN-topic/
├─ CMakeLists.txt
├─ CMakePresets.json
├─ src/main.c
├─ src/system_stm32f1xx.c        (apna minimal version)
├─ ld/<chip>.ld
├─ openocd.cfg
└─ README.md                      <- kya seekha, kya atka
```

Naya project banane ka fastest rasta: purana folder copy karo, `CMakeLists.txt`
me `SRC`/`DEVICE_DEF`/`LD_SCRIPT` badlo.

## Planned sequence

- [x] `01-f103-blink` — RCC/GPIO, SysTick, non-blocking blink
- [x] `02-f4-blink` — F4 GPIO (MODER/OTYPER/PUPDR), board choice
- [ ] `03-clock-pll` — F4 84/180 MHz: FLASH latency, VOS/overdrive, APB1 limit
- [ ] `04-uart-printf` — USART2 TX + `_write` retarget, 115200
- [ ] `05-uart-ringbuffer` — RX interrupt + ring buffer
- [ ] `06-tim-pwm` — TIM3 PWM, duty update
- [ ] `07-exti-button` — EXTI + debounce (state machine)
- [ ] `08-i2c-oled` — I2C hardware + SSD1306
- [ ] `09-spi-flash` — SPI + W25Q flash ID
- [ ] `10-adc-dma` — ADC + DMA circular, moving average
- [ ] `11-freertos` — FreeRTOS, 2 tasks + queue

## CubeMX / CubeIDE wala rasta

`docs/cubeide-workflow.md` — jab HAL/CubeMX se project banana ho. Wahan
generated code ko *padhne* ka tarika likha hai (usko blindly edit nahi karte).
