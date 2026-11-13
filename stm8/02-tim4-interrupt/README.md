# 02-tim4-interrupt

Pehla interrupt. TIM4 har 1 ms interrupt deta hai, main loop 500 ticks par LED
toggle karta hai. `01` ka delay loop yahan khatam ho jata hai.

## Chalane ka tarika

```powershell
cd stm8\02-tim4-interrupt
make
make flash
```

## TIM4 ka setup (math yaad rakho)

```
TIM4 clock  = f_master / 2^PSCR     = 16 MHz / 64 = 250 kHz
update rate = TIM4 clock / (ARR+1)  = 250 kHz / 250 = 1 kHz  -> 1 ms
```

`PSCR` aur `ARR` **buffered** hain — likhne ke baad `EGR.UG` se latch karna
padta hai, warna pehla period galat aata hai.

## Interrupt vector (asli gotcha)

STM8 me vector number **datasheet** me hai, header me nahi. Aur SDCC ka
`__interrupt(n)` number datasheet se **2 kam** hota hai (SDCC TLI ko `int0`
maanta hai; reset/trap alag). STM8S103F3 ke liye:

| Datasheet | SDCC `__interrupt()` | Source |
|---|---|---|
| 6 | 4 | EXTI PORTB |
| 13 | 11 | TIM1 UPD/OVF/TRG/BRK |
| 15 | 13 | TIM2 UPD/OVF |
| 19 | 17 | UART1 RX |
| 20 | 18 | UART1 TX |
| 21 | 19 | I2C |
| 24 | 22 | ADC1 |
| **25** | **23** | **TIM4 UPD/OVF** |
| 26 | 24 | EEPROM/EEC |

Agar vector galat hua to ISR kabhi nahi chalta (ya galat jagah se chalta hai)
aur LED nahi blinkegi. Build ke baad `.rst`/`.map` me `;int23` comment se
confirm kar sakte ho — SDCC wahan apna number likhta hai.

## Khud try karo

- [ ] `TIM4_ARR` 250 -> 125 karo: blink kitna fast hua? (2x)
- [ ] ISR me `TIM4_SR1` clear line hatao: kya hota hai? (infinite ISR -> hang)
- [ ] `g_ms` se `volatile` hatao, `--opt-code-speed` ke saath: LED rukti hai?
- [ ] ISR ke andar LED toggle karo (main loop hatao) — kya farq? kya ye achha
      design hai? (nahi: ISR chhota rakho)
- [ ] TIM2 (16-bit) se 1 s exact tick banao: `TIM2` base `0x5300`.
- [ ] `__critical { }` block me `g_ms` padho — kyun zaroori ho sakta hai?

## Common problems

| Symptom | Reason |
|---|---|
| LED nahi blinkti | galat vector, ya `IER.UIE` missing, ya `rim()` missing |
| LED bahut fast | `PSCR`/`ARR` galat, ya 16 MHz set nahi hua |
| Board hang | ISR me UIF clear nahi hua |
| Compile error on `__interrupt` | SDCC me sirf constant expression chalta hai — macro use karo |
