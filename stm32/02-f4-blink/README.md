# 02-f4-blink

Nucleo-F411RE / Nucleo-F446RE par bare-metal blink. Ek hi project, board
CMake preset se choose hota hai.

| Board | Chip | LED | Clock (ye template) |
|---|---|---|---|
| Nucleo-F411RE | STM32F411RET6 | PA5 (LD2, active high) | HSI 16 MHz |
| Nucleo-F446RE | STM32F446RET6 | PA5 (LD2, active high) | HSI 16 MHz |

**PLL jaan-boojh kar nahi lagaya.** 84/100/180 MHz par FLASH latency + voltage
scaling (VOS, overdrive on F446) set karna padta hai; galat value par board
randomly hang karta hai. Wo `03-clock-pll` exercise hai — pehle blink chalao.

## Build

```powershell
cd stm32\02-f4-blink
cmake --preset f411re        # ya: f446re
cmake --build build
cmake --build build --target flash
```

Nucleo par onboard ST-Link hai, alag flasher nahi chahiye. `flash` target OpenOCD
use karta hai (`build/openocd.cfg`, configure par auto-generate hota hai).

## F1 se F4 ka difference (yahi is project ka point hai)

| Cheez | F103 (F1) | F411/F446 (F4) |
|---|---|---|
| GPIO clock | `RCC->APB2ENR` IOPxEN | `RCC->AHB1ENR` GPIOxEN |
| Pin mode | `CRL/CRH` me 4-bit nibble | `MODER` me 2 bit per pin |
| Output type | `CNF` bits | `OTYPER` |
| Pull | `CNF` + `ODR` | `PUPDR` |
| Speed | `MODE` bits | `OSPEEDR` |
| Alternate function | AFIO remap | `AFR[0/1]` me AF number |

## Nucleo par extra

- LD2 (PA5) user LED, active high.
- B1 user button = PC13 (active low, pull-up) — `07-exti-button` me use karenge.
- Virtual COM port: USART2 (PA2 TX / PA3 RX) ST-Link ke through — `04-uart-printf`.
- Onboard ST-Link ke bina bhi flash kar sakte ho (SWD pins CN4 par).

## Khud se try karo

- [ ] PA5 ki jagah PB7 (blue LED) par blink karo.
- [ ] `system_stm32f4xx.c` ka `SCB->CPACR` line hatao, `float` variable use karo
      — kya hota hai? (FPU fault / `HardFault`)
- [ ] SysTick 1 ms ki jagah 10 ms karo — `LOAD` kaise badla?
- [ ] F411 par PLL 84 MHz khud set karo: HSI/16 * 336 / 4. Kya FLASH latency
      chahiye? (RM0090 FLASH table dekho — 84 MHz = 2 WS)
- [ ] Dono boards par same `main.c` chalta hai — kya sirf linker script aur
      `BOARD` / device define badalne se kaam ho jata hai? (haan, aur yahi CMSIS
      ka fayda hai)

## Common problems

| Symptom | Reason |
|---|---|
| `cmake --preset` fail | Ninja/CMake missing, ya `vendor/` setup nahi hua |
| Target not found | DO NOT power both USB and external 3V3 incorrectly; SWD GND common |
| Board baar baar disconnect | `adapter speed` kam karo (1000) |
| Preset badalne par purana board build hota hai | `build/` delete karo, cache board-specific hai |
