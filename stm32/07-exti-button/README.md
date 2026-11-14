# 07-exti-button

Nucleo user button (PC13) toggles LED (PA5) via EXTI15_10 interrupt.

- MCU: STM32F411RE / F446RE
- Bare-metal, CMSIS only (no HAL).
- Build: `cmake --preset f411re && cmake --build build`
- Flash: `cmake --build build --target flash`
- Expected: press B1 -> LD2 toggles.

Status: **unverified** (no ARM GCC on this machine). Verify on hardware.