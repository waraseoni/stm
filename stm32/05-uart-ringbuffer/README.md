# 05-uart-ringbuffer

Pehla **interrupt-driven** peripheral: USART2 RX ISR + ring buffer + echo.

## Kya hota hai
- 115200 8N1, USART2 (ST-Link VCP).
- Jo type karo wahi echo hota hai; Enter par `[N bytes]` aata hai.
- Buffer khali ho to CPU `__WFI()` me so jata hai (interrupt par uthta hai).

## Chalane ka tarika

```powershell
cd stm32\05-uart-ringbuffer
cmake --preset f446re
cmake --build build
cmake --build build --target flash
```
Serial monitor me type karo (local echo off rakho, warna double dikhega).

## Design ke 4 points

1. **Single producer / single consumer** — `rb_head` sirf ISR badhata hai,
   `rb_tail` sirf main. Isliye `volatile` kaafi hai, `__disable_irq()` nahi chahiye.
   Do producers hote to race hoti.
2. **ISR chhota** — sirf byte uthao aur buffer me daalo. Echo main loop me hota hai.
   ISR me `printf`/blocking TX = system freeze.
3. **`SR` read + `DR` read** — STM32 me RXNE/ORE clear karne ka tareeka yahi hai.
   Sirf `DR` padhna ORE ke case me kaafi nahi hota.
4. **Buffer full** — byte drop hota hai, overwrite nahi. `rb_put` ka return value
   ignore kar rahe hain; production me drop counter rakho.

## Khud try karo (yahi asli seekhna hai)

- [ ] ISR me `printf("rx\n")` daal do, phir 100+ chars bhejo — kya hota hai? kyun?
- [ ] `RB_SIZE` 8 karo, 50 chars ek saath paste karo — kitne drop hue?
- [ ] `rb_put` fail hone par ek `g_dropped++` counter rakho aur 1 s par print karo.
- [ ] Baud 9600 karke 100 KB bhejo — drop hone lagta hai? `__WFI` hata ke dekho.
- [ ] Echo ko uppercase me badlo (ISR me nahi, main me).
- [ ] `line_bytes` ki jagah ek chhota command parser banao: `led on` / `led off`.

## Common problems

| Symptom | Reason |
|---|---|
| Echo nahi aata | `USART_CR1_RXNEIE` missing ya `NVIC_EnableIRQ` missing |
| Pehla char missing | RXNE flag stale tha — init me `(void)USART2->SR; (void)USART2->DR;` |
| Double characters | terminal ka local echo on hai |
| `__WFI` ke baad hang | interrupt enable nahi hua (PRIMASK) |
