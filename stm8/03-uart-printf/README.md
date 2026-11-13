# 03-uart-printf

UART1 transmission (polling) + apne chhote print helpers. Ye aage ke har
exercise ka debugging channel hai.

## Wiring

| Board | USB-UART |
|---|---|
| PD5 (TX) | RX |
| GND | GND |

(PD4 = RX, `04` me use hoga. USB-UART ko 3.3V logic par rakho.)

`stm8flash` wala ST-Link alag rehta hai — UART ke liye koi driver nahi chahiye.

## Chalane ka tarika

```powershell
cd stm8\03-uart-printf
make
make flash
```
Serial monitor: **115200 8N1**. Output:

```
STM8 UART1 OK @115200
count = 0
count = 1
...
```

## Baud rate ka math (RM0016 UART1)

```
UART_DIV = f_master / baud = 16 000 000 / 115 200 = 138.9 -> 139 (0x8B)
BRR1 = UART_DIV >> 4   = 0x08
BRR2 = UART_DIV & 0x0F = 0x0B
```

- **BRR2 pehle, BRR1 baad me** — ulta karne par divider latch nahi hota.
- `div` rounding ke saath liya hai. Truncation se 9600 par bhi chalega, par
  115200 par error zyada ho jata hai.
- Actual baud 16e6/139 = 115 108 (-0.08%) — UART ke liye theek.

## Kyun `printf` nahi?

SDCC ka `printf` (integer only) ~2-3 KB leta hai, `%f` ke saath 4+ KB. 8 KB
flash par ye 50% budget hai. Isliye `uart_putc` / `uart_puts` / `uart_putu`.
Zaroorat pade to `--opt-code-size` ke saath `printf` add karke size compare karo:

```powershell
arm-none-eabi-size   # nahi, ye ARM ka hai
```
SDCC ka size `.map`/`.ihx` se dekho — ya `sdobjcopy`/`makebin` se binary banao.

## Khud try karo

- [ ] `BAUD` 9600 karo, terminal bhi 9600 — farq note karo.
- [ ] BRR2/BRR1 ka order ulta karo — kya hota hai? (garbage / no output)
- [ ] `uart_putu` ko `%04u` jaisa zero-padded banao.
- [ ] `delay_ms` ko TIM4 tick (02) se replace karo — ab exact 1 s.
- [ ] `printf` version banao aur flash usage compare karo (`.map` file).
- [ ] UART1 TX interrupt (vector 20) se non-blocking TX banao.

## Common problems

| Symptom | Reason |
|---|---|
| Kuch nahi aata | TX pin (PD5) output nahi banaya, ya GND common nahi |
| Garbage | baud mismatch, ya BRR1/BRR2 order ulta |
| Sirf pehla char | `TXE` wait missing |
| Terminal par kuch nahi, board par sab theek | USB-UART ka RX/TX cross-check karo |
