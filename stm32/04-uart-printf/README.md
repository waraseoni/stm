# 04-uart-printf

USART2 par `printf` — aage ke har exercise ka debugging tool.

## Kya hota hai
- USART2 (PA2 TX / PA3 RX, AF7), 115200 8N1, HSI 16 MHz.
- `printf` ka output ST-Link ke **virtual COM port** par aata hai — alag USB-UART
  converter ki zaroorat nahi.
- 1 second par `tick N s` print hota hai.

## Chalane ka tarika

```powershell
cd stm32\04-uart-printf
cmake --preset f446re        # ya f411re
cmake --build build
cmake --build build --target flash
```

Serial monitor (115200, 8N1):
- VS Code: `Serial Monitor` extension -> port select (STMicroelectronics STLink Virtual COM Port)
- Ya PuTTY / Tera Term.

## Code ke 3 important points

1. **`_write` retarget** — newlib ka `printf` seedha UART nahi janta; wo `_write()`
   call karta hai. `--specs=nosys.specs` weak stub deta hai, hum apna strong
   version dete hain, isliye linker hamara chunta hai.
2. **`setvbuf(stdout, NULL, _IONBF, 0)`** — iske bina stdout fully buffered hota
   hai (1024 B) aur chhota output kabhi nahi dikhta. Ye classic "printf kaam
   nahi kar raha" bug hai.
3. **BRR = round(PCLK/baud)** — `OVER8=0` par 16x oversampling. `PCLK1_HZ` galat
   hui to garbage aata hai (baud mismatch).

## Verify / khud try karo

- [ ] `BAUD` 9600 karo — terminal bhi 9600 par set karo. Kya farq dikha?
- [ ] `setvbuf` line comment karo — output kahan gaya? (buffer!)
- [ ] `PCLK1_HZ` 16000000 se 8000000 kar do — kya hota hai? kyun?
- [ ] `printf("%f", 3.14f)` try karo — size kitna badha? (`arm-none-eabi-size`)
      Float printf ~10 KB kha jata hai. Embedded me avoid.
- [ ] `03-clock-pll` ka `clock_init()` copy karke 84 MHz par chalao, `PCLK1_HZ`
      42000000 karo — ab bhi 115200 par sahi aata hai?

## Common problems

| Symptom | Reason |
|---|---|
| Kuch bhi print nahi | `setvbuf` missing, ya galat COM port |
| Garbage characters | baud mismatch (PCLK1_HZ / terminal setting) |
| `undefined reference to _write` | function signature galat (`int, char*, int`) |
| Sirf pehla line aata hai | TXE wait missing / UE bit set nahi |
