# STM32 notes (F1 = Blue Pill, F4 = Nucleo)

## Bare-metal ka mental model
1. **Clock on karo** (RCC) — bina iske peripheral ke registers dead hain.
2. **Pin mode set karo** (GPIO) — F1: CRL/CRH, F4: MODER/OTYPER/PUPDR/AFR.
3. **Peripheral configure karo**.
4. **NVIC** me interrupt enable karo (agar chahiye).
5. **Enable bit** set karo — tabhi hardware chalta hai.
6. Debug: SWD + `printf`/ITM + logic analyzer.

## RCC / bus mapping (common galti)
- Har peripheral kisi bus par hota hai: AHB, APB1, APB2 (F4 me AHB1/AHB2).
- Enable bit usi bus ke `RCC->xxxENR` me hota hai:
  - F1: `RCC->APB2ENR` me `IOPAEN..IOPEEN`, `USART1EN`, `AFIOEN`;
    `RCC->APB1ENR` me `USART2EN`, `TIM2EN`, `I2C1EN`.
  - F4: `RCC->AHB1ENR` me `GPIOAEN...`, `RCC->APB2ENR` me `USART1EN`, `APB1ENR` me `TIM2EN`.
- `AFIOEN` (F1) bhoolne se EXTI/remap kaam nahi karta.
- Peripheral clock band = register writes ignore, koi error nahi. Bas "kaam nahi kar raha".

## GPIO: F1 vs F4 (sabse bada confusion point)
| | F1 (CRL/CRH, 4 bit per pin) | F4 (per-pin registers) |
|---|---|---|
| mode | `MODE[1:0]`: 00 in, 01/10/11 out 10/2/50 MHz | `MODER`: 00 in, 01 out, 10 AF, 11 analog |
| type | `CNF[1:0]`: out 00 push-pull, 01 open-drain; in 00 float, 01 pull, 10 analog | `OTYPER` 0 PP / 1 OD |
| pull | input + CNF=10 -> pull-up/down via ODR bit | `PUPDR` |
| alt func | fixed alternate (remap via AFIO) | `AFR[0/1]` me AF number |

- F1 par pin 0-7 = `CRL`, pin 8-15 = `CRH`.
- Output speed kam rakho (EMI), unless zaroori ho.

## Clock tree
- F1: HSI 8 MHz, HSE 8 MHz -> PLL x9 = 72 MHz. Flash latency set karna padta hai
  (`FLASH->ACR` me `LATENCY`) — bina iske 72 MHz par crash/instability.
- F4: HSE 8 MHz -> PLL -> 84/168/180 MHz. `PWR->CR` me VOS, `FLASH->ACR` latency,
  APB prescalers (APB1 max 42 MHz on F4, 45 MHz on F446 at VOS1!). F446 par
  168 MHz se upar **overdrive** (`PWR->CR` ODEN/ODSWRDY) chahiye.
- Baud rate TIM/peripheral clocks se calculate hota hai — clock badla to baud
  dobara check karo.

### Ready-made recipes (khud verify karo, RM table se)

| Target | Board | PLL | Flash latency | Extra |
|---|---|---|---|---|
| 72 MHz | F103 | HSE 8 x9 | 2 WS + prefetch | APB1 /2 (36 MHz) |
| 84 MHz | F411 | HSI 16 /16 x336 /4 | 2 WS | VOS1 default |
| 100 MHz | F411 | HSI 16 /16 x400 /4 | 3 WS | VOS1, APB1 /2 |
| 168 MHz | F446 | HSI 16 /16 x336 /2 | 5 WS | VOS1, APB1 /4 |
| 180 MHz | F446 | HSI 16 /16 x360 /2 | 5 WS | **VOS0 + overdrive**, APB1 /4 |

**Order har jagah same**: voltage scale / VOS -> flash latency -> prescalers ->
PLL on -> wait PLLRDY -> switch SYSCLK -> `SystemCoreClock` update.
Ye order galat kiya to board hang/random-fault karta hai, aur reason samajhna
mushkil hota hai.

> Hamare bare-metal templates me apna minimal `system_stm32f*.c` hai (reset par
> kuch nahi karta). CubeMX/HAL project me ST ka system file use hota hai jo khud
> PLL set karta hai — dono ko mix mat karo.

## Interrupts / NVIC
- Vector table `startup_*.s` me; naam CMSIS headers me (`TIM2_IRQHandler`).
- Enable: `NVIC_EnableIRQ(TIM2_IRQn)` + peripheral ka interrupt bit.
- Handler me `SR` flag clear karna **zaroori** — warna infinite re-entry.
- Keep ISR chhota: flag set karo, kaam `main` loop me.

## UART / ST-Link VCP (printf ka rasta)

| Board | UART | TX | RX | AF | Note |
|---|---|---|---|---|---|
| Nucleo-F411RE / F446RE | USART2 | PA2 | PA3 | AF7 | onboard ST-Link VCP, koi wire nahi |
| Blue Pill | USART1 | PA9 | PA10 | fixed | `printf` ke liye USB-UART converter |
| Blue Pill (alt) | USART2 | PA2 | PA3 | fixed | `AFIO_MAPR` remap nahi chahiye |

- F4 par `GPIOA->AFR[0]` me AF number 7 likhna padta hai; F1 par AF fixed hota hai
  (sirf `CRH` me `MODE=10, CNF=10` = AF push-pull).
- `BRR = PCLK / baud` (OVER8=0). PLL on karne ke baad `PCLK1` badalta hai —
  baud dobara calculate karo, warna garbage.
- Nucleo par VCP ka RX/TX ST-Link ke through aata hai; board ko USB se hi power
  do, alag USB-UART ki zaroorat nahi.

## SysTick / timing
- `SysTick_Config(SystemCoreClock/1000)` -> 1 ms tick. Delay/`millis()` isi par.
- `volatile uint32_t ticks;` handler me badhao, warna optimizer cache kar lega.

## Debug
- SWD: SWDIO, SWCLK, GND (+ optionally RESET). 3V3 se power ya alag supply.
- BOOT0 = 0 -> flash se boot. BOOT0 = 1 -> system memory (UART bootloader).
- F1 par SWD pins PB3/PB4 share hote hain (JTAG se) — `AFIO_MAPR` se SWJ config.
- ITM/SWO: F1 par PB3 = SWO — single wire `printf` (SWD ke saath), pins bachte hain.

## HAL vs LL vs CMSIS — kab kya
- **CMSIS (bare-metal)**: seekhne ke liye, register clarity. Product me bhi chhote
  projects par theek.
- **LL**: HAL ka patla version, register ke kareeb, fast, achha compromise.
- **HAL**: portability + jaldi deliver. Code study me HAL ko "reference
  implementation" maano, truth nahi.
- CubeMX generated code ko kabhi blindly edit mat karo — `USER CODE BEGIN/END`
  blocks ke bahar ka code regenerate hone par ud jata hai.

## Gotchas
- `HAL_Delay` SysTick par chalta hai; ISR me `HAL_Delay` = deadlock.
- `HAL_Init()` se pehle clock config karne ki koshish = undefined behaviour.
- F1 Blue Pill par PC13 LED **active-low** hai.
- Blue Pill clone ke USB pull-up (R10) galat value ke hote hain — USB enumerate nahi karta.
- Read-out protection (RDP) enable ho gaya to SWD lock ho jayega; unlock se full chip erase hota hai.
- F4 me `__HAL_RCC_..._CLK_ENABLE()` ke baad thoda settle time (kuch peripherals) — HAL handles it.

## References
- RM0008 (F1), RM0090 (F4) — RCC/GPIO/USART/TIM chapters.
- PM0056 (Cortex-M3), PM0214 (Cortex-M4) — NVIC, SysTick, SCB.
- CMSIS device header (`stm32f103xb.h`) — register struct ka asli sach.
- Nucleo/Blue Pill schematic — pin mapping ke liye.
