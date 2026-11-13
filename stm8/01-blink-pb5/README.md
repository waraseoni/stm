# 01-blink-pb5

Sabse pehla test: toolchain + board + flasher ek saath verify karna.
Koi library nahi, sirf 5 registers. Agar ye chal gaya to environment theek hai.

## Chalane ka tarika

```powershell
# 1) build
make                     # ya: .\build.ps1
# 2) flash
make flash               # ya: .\build.ps1 -Flash
```

`make` na ho to: `winget install ezwinports.make`

Chip alag hai to `MCU` badlo (stm8flash ke `-p` list se):
```powershell
make flash MCU=stm8s003f3
```

## Wiring (ST-Link V2 -> board)

| ST-Link | Board |
|---|---|
| SWIM | SWIM |
| RESET | RST |
| GND | GND |
| 3.3V | 3V3 |

## Jo seekhna hai (comment apne shabdon me add karo)

- Reset par clock 2 MHz kyun hota hai? `CLK_CKDIVR = 0` ka effect?
- `DDR` / `CR1` / `ODR` -- teeno ka role alag kyun hai? (STM8 ka classic pattern)
- `volatile` hata kar build karo -- kya hota hai? (optimizer register write hata deta hai)
- Delay loop ko TIM4 se replace karo -> Phase 1 ka pehla real exercise.

## Next
- `02-tim4-interrupt`: TIM4 overflow interrupt, exact 1 s tick.
- `03-uart-printf`: UART1 @ 9600, 16 MHz se BRR calculate karke.
