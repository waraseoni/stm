# CubeMX / CubeIDE workflow (HAL wala rasta)

Bare-metal templates se concepts clear hone ke baad HAL par switch karna easy
hota hai — ulta nahi. Par HAL ko "magic" ki tarah use karne se debugging mushkil
ho jati hai, isliye har generated file ko padho.

## Naya project

1. CubeIDE -> `File > New > STM32 Project`
2. Part number se select karo (`STM32F103C8` ya `STM32F446RETx`) — board select
   karne se pin conflicts kam hote hain.
3. `Project > Generate Code` se pehle:
   - **Project Manager > Code Generator**: "Generate peripheral initialization as
     a pair of .c/.h files per peripheral" ✅ (padhna aasan hota hai)
   - "Keep User Code when re-generating" ✅ (default)
4. Clock config: `Clock Configuration` tab — yahin PLL/prescaler set hote hain.
   Ye tab asal me `SystemClock_Config()` generator hai.
5. Pinout me LED pin ko `GPIO_Output` karo, label `LED` do (`LED_Pin` ban jayega).

## Generated code ka map (yahi padhna hai)

| File | Kya dekhte hain |
|---|---|
| `Core/Src/main.c` | `SystemClock_Config()`, `MX_GPIO_Init()` — HAL ke andar jaane ka entry point |
| `Core/Src/stm32f4xx_hal_msp.c` | `HAL_GPIO_Init` se pehle clock enable + NVIC (MSP = MCU Support Package) |
| `Core/Src/stm32f4xx_it.c` | ISR -> `HAL_xxx_IRQHandler()` call |
| `Core/Src/system_stm32f4xx.c` | `SystemInit()`, `SystemCoreClockUpdate()` |
| `startup_stm32f4xx.s` | vector table + `Reset_Handler` (humara same kaam karta hai) |
| `*.ioc` | project ka "source of truth" — git me commit karo |

**Rule:** `.ioc` badalne ke baad regenerate karo; generated file me sirf
`USER CODE BEGIN/END` blocks ke andar likho.

## Bare-metal se comparison (best exercise)

1. Apna `01-f103-blink/src/main.c` kholo, sath me CubeMX ka `SystemClock_Config()`.
2. Har line par likho: "ye mere code ki kaunsi line hai?".
3. Differences note karo `docs/02-stm32-notes.md` me — jaise HAL `HAL_RCC_OscConfig`
   PLL ready flag ka timeout handle karta hai, humne `while()` lagaya tha.
4. WAIT: HAL ka `HAL_Delay` SysTick par chalta hai; `SysTick_Handler` me
   `HAL_IncTick()` dikhega.

## CubeIDE + git

```
*.ioc              -> commit
Core/, Drivers/    -> commit (project self-contained rakhna hai)
Debug/, Release/   -> ignore
.settings/, .project, .cproject -> commit (team same IDE use kare to)
```

Ye workspace CMake wale projects ko IDE me import karta hai
(`File > Import > CMake Project`), dono side-by-side chal sakte hain.
