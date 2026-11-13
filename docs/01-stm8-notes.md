# STM8 notes (STM8S103F3P6 base)

## Core / chip facts
- 8-bit STM8 core, max 16 MHz, Harvard, 3-stage pipeline.
- STM8S103F3P6: 8 KB flash, 1 KB RAM, 640 B EEPROM, 20 pin.
- Peripheral registers ~ `0x5000` block, core/debug ~ `0x7F00`.
- RAM `0x0000` se shuru, stack upar se neeche grow karta hai (linker top set karta hai).
- Koi cache nahi, koi clock tree nahi — isliye registers seekhne ke liye perfect.

## Reset default clock
- HSI = 16 MHz, reset par **/8 = 2 MHz**. `CLK_CKDIVR = 0x00` -> full 16 MHz.
- Delay loops/baud rate isi par depend karte hain. Clock pehle set karo.

## GPIO (STM8 ka pattern yaad rakho: DDR -> CR1 -> ODR)
Port B example (`PB` = port B, pin mask `0x20` = PB5):

| Register | Addr | Kaam |
|---|---|---|
| `PB_ODR` | 0x5005 | output data / input read bhi yahin se |
| `PB_IDR` | 0x5006 | input data |
| `PB_DDR` | 0x5007 | 1 = output, 0 = input |
| `PB_CR1` | 0x5008 | output: 1 = push-pull, 0 = open drain; input: 1 = pull-up |
| `PB_CR2` | 0x5009 | output: 1 = fast/slow slew; input: 1 = interrupt enable |

Port A: ODR 0x5000, IDR 0x5001, DDR 0x5002, CR1 0x5003, CR2 0x5004.
Port C: ODR 0x500A se shuru. Port D: 0x500F se. (RM0016 GPIO chapter se confirm karo.)

Sequence: `DDR |= mask` -> `CR1 |= mask` -> `ODR ^= mask`.

## SDCC specifics (STM8)
```c
__at(0x5005) volatile unsigned char PB_ODR;   // absolute register
void tim4_isr(void) __interrupt(23) { ... }   // TIM4: datasheet 25 - 2
__critical { ... }                            // interrupts band (short only)
```
- Build: `sdcc -mstm8 --std-c99 --opt-code-speed main.c` -> `.ihx`
- Vector numbers har part me alag ho sakte hain — datasheet ka "interrupt vector
  table" hi source of truth hai.
- **SDCC offset:** `__interrupt(n)` me datasheet ka number **2 kam** hota hai
  (SDCC TLI ko `int0` ginta hai; reset/trap alag). Examples: TIM4 25 -> 23,
  UART1 RX 19 -> 17, EXTI PORTB 6 -> 4, ADC1 24 -> 22.
- TIM4 ke registers STM8S103/003 par shift hain (CR1 ke baad 2 reserved bytes):
  `CR1 0x5340, IER 0x5343, SR1 0x5344, EGR 0x5345, CNTR 0x5346, PSCR 0x5347, ARR 0x5348`.
- `int` 16-bit hai. 32-bit/float avoid karo jab tak zaroori na ho (code size).
- `volatile` bhoolna = optimizer register write hata dega. Silent bug.

## Peripherals — study order
1. GPIO + clock (blink, no library)
2. TIM4 (basic timer, overflow interrupt) -> TIM2 (PWM, input capture)
3. UART1 (baud from 16 MHz, polling -> interrupt + ring buffer)
4. EXTI (pin interrupt), `__interrupt` + `rim/sim`
5. I2C (bit-bang pehle, phir hardware) — sensor ke saath test
6. ADC1 (single channel -> scan)
7. EEPROM (flash programming unlock sequence, `FLASH_CR1/CR2`, `NCR2`)
8. Watchdog (IWDG) + low power (WFI, `halt`)

## Gotchas jo baar baar milte hain
- Flash write ke liye standard block programming sequence chahiye; `NCR2` (complement)
  bharna padta hai.
- Option bytes galat set kiye to chip boot hi nahi karega (STVP se recover hota hai).
- SWIM: sirf 3 wires (SWIM, RESET, GND) + 3.3V. Reset line zaroori hai.
- UART TX pin ko output banana mat bhoolo (DDR/CR1).
- 8 KB flash: `printf` float ke saath ~2-3 KB kha jata hai. Integer printf use karo.

## References
- RM0016 (STM8S reference manual) — ADC, TIM, UART, GPIO, flash chapters.
- PM0044 (STM8 CPU programming manual) — instruction set, stack, stack pointer.
- STM8S103F3 datasheet — pinout, alternate functions, absolute max ratings.
- STM8S SPL (standard peripheral library) — `vendor/` me rakho, sirf padhne/compare ke liye.
