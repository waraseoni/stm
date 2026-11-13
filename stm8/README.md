# stm8/ — projects (SDCC + stm8flash)

Naming: `NN-topic`. Har project self-contained: `main.c` + `Makefile` + `README.md`.
Build rules ek hi jagah: `common.mk` (project `Makefile` sirf `TARGET`/`MCU` set karta hai).

| # | Project | Topic | Status |
|---|---|---|---|
| 01 | `01-blink-pb5` | GPIO, clock (HSI 16 MHz), toolchain verify | done |
| 02 | `02-tim4-interrupt` | TIM4 overflow ISR, `__interrupt`, vector 25 | done |
| 03 | `03-uart-printf` | UART1 TX polling, baud calc (BRR2 pehle) | done |
| 04 | `04-uart-echo` | UART1 RX interrupt + ring buffer + echo | done |
| 05 | `05-i2c-ssd1306` | I2C (bit-bang -> hardware) | planned |
| 06 | `06-adc-scan` | ADC1 single + scan mode | planned |
| 07 | `07-eeprom` | flash/EEPROM write unlock sequence | planned |
| 08 | `08-pwm-motor` | TIM2 PWM, duty table | planned |

```powershell
cd stm8\02-tim4-interrupt
make            # -> blink_tim4.ihx
make flash      # stm8flash -c stlinkv2 -p stm8s103f3 -w ... -v
```

Register addresses har project me khud define karenge (device header dependency
nahi) — isse address aur bit meanings dono yaad rehte hain. Verified addresses:
`GPIOA 0x5000`, `GPIOB 0x5005`, `GPIOC 0x500A`, `GPIOD 0x500F`,
`UART1 0x5230`, `TIM2 0x5300`, `TIM4 0x5340`, `CLK 0x50C0`.

Interrupt vectors STM8S103F3 datasheet se (header me nahi milte): TIM1 = 13,
TIM2 = 15, UART1 RX = 19, UART1 TX = 20, I2C = 21, ADC1 = 24, TIM4 = 25,
EEPROM = 26, EXTI PORTD = 8.

> **SDCC numbering:** `__interrupt(n)` me datasheet ka number **2 kam** hota hai
> (SDCC TLI ko `int0` maanta hai). Yaani TIM4 `__interrupt(23)`, UART1 RX
> `__interrupt(17)`, EXTI PORTB `__interrupt(4)`. Build ke `.rst` me `;int23`
> comment se cross-check karo.
