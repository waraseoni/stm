# Resources (priority order me padho)

## STM8
- **RM0016** — STM8S reference manual (GPIO, CLK, TIM, UART, I2C, ADC, FLASH).
- **PM0044** — STM8 CPU programming manual (instruction set, stack, addressing).
- STM8S103F3 datasheet — pinout, alternate functions, electrical limits.
- STM8S SPL (`STM8S_StdPeriph_Lib`) — examples + library, sirf reference ke liye.
- `github.com/vdudouyt/stm8flash` — flasher source/README (chip list yahin).

## STM32
- **RM0008** (F1) / **RM0090** (F4) — har peripheral ka truth.
- **PM0056 / PM0214** — Cortex-M3/M4 core, NVIC, SysTick, faults.
- CMSIS device header — register names/bitfields ka final source.
- STM32CubeF1 / STM32CubeF4 packages — `Projects/*/Examples/` me **per-peripheral
  bare-metal examples** (HAL ke bina bhi bahut kuch milta hai, `Examples_LL` dekho).
- AN2606 — built-in bootloader (UART/DFU se flash, brick recovery).

## Books
- *Mastering STM32* — Carmine Noviello (Cube/HAL + FreeRTOS, practical).
- *Making Embedded Systems* — Elecia White (design thinking, architecture).
- *The Definitive Guide to ARM Cortex-M3/M4* — Joseph Yiu (core deep dive).

## Practice / community
- controllerstech.com, deepbluembedded.com — HAL examples (verify against RM).
- Fastbit Embedded Brain Academy (Udemy) — bare-metal register course, structured.
- ST community forum: ST-Link/SDCC driver issues ke liye sabse fast answer.

## Datasheet rakhne ka tarika
`vendor/datasheets/` me PDF rakho (gitignored) aur `docs/` me sirf page numbers
likho: jaise `RM0016 p.142 TIM4`. Search me 30 second bachte hain.
