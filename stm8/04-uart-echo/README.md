# 04-uart-echo

UART1 **RX interrupt** + ring buffer + echo. `02` (interrupt) aur `03` (UART)
ka combination — yahi pattern real firmware me har jagah milta hai.

## Wiring

| Board | USB-UART |
|---|---|
| PD5 (TX) | RX |
| PD4 (RX) | TX |
| GND | GND |

## Chalane ka tarika

```powershell
cd stm8\04-uart-echo
make
make flash
```
115200 8N1 par type karo — echo aayega, Enter par `[N bytes]` (aur drop count).

## Design

- **Datasheet vector 19 = UART1 RX; SDCC me `__interrupt(17)`** (SDCC numbering
  datasheet se 2 kam). Galat number = ISR kabhi nahi chalta.
- **SR phir DR** padhna zaroori hai — isse `RXNE` clear hota hai. Sirf DR padho
  to flag atka rehta hai aur interrupt loop me phas jate ho.
- **Single producer / single consumer**: `rx_head` sirf ISR, `rx_tail` sirf main.
  Isliye `volatile` kaafi hai, `sim()` ki zaroorat nahi.
- Buffer full par byte **drop** hota hai (overwrite nahi), aur `rx_dropped`
  counter batata hai ki main loop kitna slow tha.
- `wfi` — koi kaam nahi to CPU halt, interrupt par jagta hai. Power bachta hai.

## Khud try karo

- [ ] `RB_SIZE` 8 karo aur 50 chars ek saath paste karo — kitne drop hue?
- [ ] ISR me `uart_putc(d)` daal do (echo ISR se) — kya risk hai? (blocking in ISR)
- [ ] `wfi` hatao — power/frequency farq note karo (current meter ho to).
- [ ] Echo ko uppercase banao (main loop me, ISR me nahi).
- [ ] Chhota command parser: `led on` / `led off` se PB5 control karo.
- [ ] TIM4 tick (02) ke saath: 1 s par uptime print karo jab koi input na ho.

## Common problems

| Symptom | Reason |
|---|---|
| Echo nahi | `RIEN` missing, `rim()` missing, ya galat vector |
| Pehla char repeat hota hai | RXNE flag init ke waqt stale tha — `(void)UART1_SR; (void)UART1_DR;` |
| Board hang | ISR me SR/DR dono nahi padhe (flag clear nahi hua) |
| Drop count badhta hai | main loop slow (`uart_putc` blocking) — TX interrupt banao |
