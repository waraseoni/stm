# stm8/ — projects (SDCC + stm8flash)

Naming: `NN-topic`. Har project self-contained: `main.c` + `Makefile` + `README.md`.

| # | Project | Topic |
|---|---|---|
| 01 | `01-blink-pb5` | GPIO, clock (HSI 16 MHz), toolchain verify |
| 02 | `02-tim4-interrupt` | timer overflow ISR, `__interrupt` |
| 03 | `03-uart-printf` | UART1, baud calc, blocking TX |
| 04 | `04-uart-ringbuffer` | interrupt RX + ring buffer |
| 05 | `05-i2c-ssd1306`  | I2C (bit-bang -> hardware) |
| 06 | `06-adc-scan`     | ADC1 single + scan mode |
| 07 | `07-eeprom`       | flash/EEPROM write unlock sequence |
| 08 | `08-pwm-motor`    | TIM2 PWM, duty table |

Register addresses har project me khud define karenge (device header dependency
nahi) — isse address aur bit meanings dono yaad rehte hain.
