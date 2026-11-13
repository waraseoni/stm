# 01-f103-blink

Blue Pill (STM32F103C8T6) par pehla bare-metal program. Koi HAL, koi library —
sirf CMSIS headers + apna linker script + ST ka startup file.

## Behaviour
PC13 LED (active **low**) har 500 ms toggle hoti hai. Delay loop nahi — SysTick
interrupt 1 ms tick deta hai, `main` loop usi ko count karta hai.

## Build + flash

```powershell
# workspace root se ek baar:
.\setup-vendor.ps1

cd stm32\01-f103-blink
cmake --preset debug
cmake --build build
cmake --build build --target flash
```

Xvfb/serial nahi chahiye — LED dekh ke verify karo.

## Wiring (ST-Link V2 -> Blue Pill)

| ST-Link | Blue Pill |
|---|---|
| SWDIO | DIO |
| SWCLK | CLK |
| GND   | GND |
| 3.3V  | 3V3 |
| RST (optional) | R |

BOOT0 jumper **0** par ho (flash se boot).

## Memory map (linker script)

```
FLASH 0x08000000  64 KB
RAM   0x20000000  20 KB   (stack top = 0x20005000)
```

## Code me kya-kya hai

1. `clock_72mhz()` — HSE 8 MHz -> PLL x9 -> 72 MHz, APB1 /2 (36 MHz limit),
   flash 2 wait states. **Order matter karta hai**: flash latency pehle, phir
   PLL switch.
2. `led_init()` — `RCC->APB2ENR` me IOPCEN, phir CRH me MODE13=10, CNF13=00.
3. `systick_1ms()` — `LOAD = 72 000 - 1`, `CLKSOURCE = HCLK`.
4. `main()` — `(g_ms_ticks - next) >= 500` wala non-blocking pattern
   (unsigned wrap-around safe hai).

## Khud se ye try karo (README me answer likho)

- [ ] `g_ms_ticks` se `volatile` hatao, `-O2` se build karo — kya hota hai? kyun?
- [ ] `clock_72mhz()` hata do — blink slow ho jayega? kitna? (HSI 8 MHz)
- [ ] APB1 prescaler `/2` ko `/1` kar do — kya tootega? (36 MHz limit)
- [ ] `-O2` aur `-Os` ke size compare karo (`arm-none-eabi-size build/app.elf`).
- [ ] Blink ko TIM3 se karo (SysTick hata kar) — `04` se pehle khud try karo.
- [ ] Blue Pill ka HSE 8 MHz hai; agar aapke board par crystal nahi hai to
      `clock_72mhz()` jaan-boojh kar `fatal()` par rukega — debugger me PC dekho.

## Common problems

| Symptom | Reason |
|---|---|
| LED kabhi on/off nahi hoti | PC13 active low hai — `ODR` bit 13 = 0 par ON |
| Flash nahi hota | SWD wiring / BOOT0 / ST-Link driver |
| Program chal ke ruk gaya | HSE ready nahi hua -> `fatal()`; crystal check karo |
| `undefined reference to _estack` | galat linker script ya `-T` path |
| LED slow blink | PLL switch fail -> HSI 8 MHz par chal raha hai |
