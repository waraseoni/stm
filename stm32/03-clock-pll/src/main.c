/*
 * 03-clock-pll -- F4 clock tree ko explicitly set karna.
 *
 *   Nucleo-F411RE : HSI 16 MHz -> PLL -> 84 MHz   (PLLP = /4, N = 336)
 *   Nucleo-F446RE : HSI 16 MHz -> PLL -> 180 MHz  (PLLP = /2, N = 360, +overdrive)
 *
 * LED: PA5 (LD2, active high). Blink 100 ms.
 *
 * Order (yahi asli lesson hai):
 *   1. PWR clock + voltage scale (VOS)
 *   2. 168 MHz se upar: overdrive enable + ready wait
 *   3. FLASH latency (speed se pehle!)
 *   4. APB prescalers (APB1 ki limit yaad rakho)
 *   5. PLL config + ON + PLLRDY wait
 *   6. SW = PLL + SWS confirm
 *   7. SystemCoreClock update
 *
 * Ulta order (PLL pehle, latency baad me) = random hard faults.
 */

#include "stm32f4xx.h"

#if defined(STM32F411xE)
  #define SYSCLK_HZ   84000000U
  #define PLL_N       336U
  #define PLL_P_CODE  1U        /* 01 = /4 */
  #define PLL_Q       7U        /* 48 MHz USB ke liye */
#elif defined(STM32F446xx)
  #define SYSCLK_HZ   180000000U
  #define PLL_N       360U
  #define PLL_P_CODE  0U        /* 00 = /2 */
  /* PLLQ yahan sirf valid range (2..15) me rakhne ke liye hai: 360/8 = 45 MHz.
   * USB 48 MHz chahiye to ye config kaam nahi karegi (360 ko 48 se divide
   * nahi kar sakte) -- alag PLL setup / HSE use karna padega. */
  #define PLL_Q       8U
#else
  #error "Board define missing (STM32F411xE / STM32F446xx)"
#endif

volatile uint32_t g_ms_ticks;

void SysTick_Handler(void)
{
    g_ms_ticks++;
}

static void fatal(void)
{
    for (;;) {
    }
}

static void clock_init(void)
{
    /* 1) PWR interface clock (VOS/overdrive registers isi ke through hain) */
    RCC->APB1ENR |= RCC_APB1ENR_PWREN;
    (void)RCC->APB1ENR;

#if SYSCLK_HZ > 168000000U
    /* VOLTAGE SCALE 1 (VOS = 11) -- 180 MHz ke liye zaroori */
    PWR->CR = (PWR->CR & ~PWR_CR_VOS) | PWR_CR_VOS;

    /* 2) Over-drive: pehle enable, ready ka wait, phir switch */
    PWR->CR |= PWR_CR_ODEN;
    while (!(PWR->CSR & PWR_CSR_ODRDY)) {
    }
    PWR->CR |= PWR_CR_ODSWEN;
    while (!(PWR->CSR & PWR_CSR_ODSWRDY)) {
    }
#endif

    /* 3) Flash latency + caches. 84 MHz = 2 WS, 180 MHz = 5 WS. */
#if SYSCLK_HZ > 168000000U
    FLASH->ACR = FLASH_ACR_PRFTEN | FLASH_ACR_ICEN | FLASH_ACR_DCEN | FLASH_ACR_LATENCY_5WS;
#elif SYSCLK_HZ > 84000000U
    FLASH->ACR = FLASH_ACR_PRFTEN | FLASH_ACR_ICEN | FLASH_ACR_DCEN | FLASH_ACR_LATENCY_3WS;
#else
    FLASH->ACR = FLASH_ACR_PRFTEN | FLASH_ACR_ICEN | FLASH_ACR_DCEN | FLASH_ACR_LATENCY_2WS;
#endif

    /* 4) Bus prescalers: AHB /1, APB1 apni limit par, APB2 /1 ya /2 */
    RCC->CFGR &= ~(RCC_CFGR_HPRE | RCC_CFGR_PPRE1 | RCC_CFGR_PPRE2);
    RCC->CFGR |= RCC_CFGR_HPRE_DIV1;

#if SYSCLK_HZ > 100000000U
    /* 180 MHz: APB1 max 45 MHz, APB2 max 90 MHz -> /4, /2 */
    RCC->CFGR |= (RCC_CFGR_PPRE1_DIV4 | RCC_CFGR_PPRE2_DIV2);
#else
    /* 84 MHz: APB1 max 50 MHz, APB2 100 MHz -> /2, /1 */
    RCC->CFGR |= (RCC_CFGR_PPRE1_DIV2 | RCC_CFGR_PPRE2_DIV1);
#endif

    /* 5) PLL: HSI 16 MHz / M * N / P
     *    VCO = 16 / 16 * N  -> 336 MHz (F411), 360 MHz (F446)
     *    SYSCLK = VCO / P  -> 84 MHz, 180 MHz                        */
    RCC->PLLCFGR = 0U;                                      /* PLLSRC = HSI */
    RCC->PLLCFGR |= (16U  << RCC_PLLCFGR_PLLM_Pos);          /* M = 16 -> 1 MHz */
    RCC->PLLCFGR |= (PLL_N << RCC_PLLCFGR_PLLN_Pos);
    RCC->PLLCFGR |= (PLL_P_CODE << RCC_PLLCFGR_PLLP_Pos);
    RCC->PLLCFGR |= (PLL_Q << RCC_PLLCFGR_PLLQ_Pos);

    RCC->CR |= RCC_CR_PLLON;
    while (!(RCC->CR & RCC_CR_PLLRDY)) {
    }

    /* 6) Switch SYSCLK to PLL, phir confirm */
    RCC->CFGR = (RCC->CFGR & ~RCC_CFGR_SW) | RCC_CFGR_SW_PLL;
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_PLL) {
    }

    /* 7) Baaki code (SysTick, baud) isi value par depend karta hai */
    SystemCoreClock = SYSCLK_HZ;
}

static void led_init(void)
{
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN;
    (void)RCC->AHB1ENR;

    GPIOA->MODER = (GPIOA->MODER & ~GPIO_MODER_MODER5) | GPIO_MODER_MODER5_0;
    GPIOA->OTYPER &= ~GPIO_OTYPER_OT5;
    GPIOA->OSPEEDR = (GPIOA->OSPEEDR & ~GPIO_OSPEEDR_OSPEED5) | GPIO_OSPEEDR_OSPEED5_0;
    GPIOA->ODR &= ~GPIO_ODR_OD5;
}

static void systick_1ms(void)
{
    SysTick->LOAD = (SystemCoreClock / 1000U) - 1U;   /* 84000 ya 180000 */
    SysTick->VAL  = 0U;
    SysTick->CTRL = SysTick_CTRL_CLKSOURCE_Msk
                  | SysTick_CTRL_TICKINT_Msk
                  | SysTick_CTRL_ENABLE_Msk;
}

int main(void)
{
    clock_init();
    led_init();
    systick_1ms();

    uint32_t next = 0U;

    for (;;) {
        if ((g_ms_ticks - next) >= 100U) {
            next += 100U;
            GPIOA->ODR ^= GPIO_ODR_OD5;
        }
    }
}
