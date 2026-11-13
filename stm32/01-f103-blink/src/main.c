/*
 * 01-f103-blink -- bare-metal, sirf CMSIS. Koi HAL nahi.
 *
 * Board: Blue Pill / STM32F103C8T6
 * LED  : PC13, ACTIVE LOW (pin 0 = LED ON)
 * Clock: HSE 8 MHz -> PLL x9 -> 72 MHz
 *
 * Padhne ka order: RM0008 -> RCC (ch.7), FLASH (ch.3), GPIO (ch.9)
 */

#include "stm32f1xx.h"

/* 1 kHz SysTick ISR se badhne wala counter. volatile zaroori hai! */
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

/* 8 MHz HSE -> 72 MHz SYSCLK, AHB 72, APB1 36, APB2 72 */
static void clock_72mhz(void)
{
    /* 1) HSE on karo aur ready hone tak ruko (timeout ke saath) */
    RCC->CR |= RCC_CR_HSEON;
    for (uint32_t i = 0; i < 100000U; i++) {
        if (RCC->CR & RCC_CR_HSERDY) {
            break;
        }
    }
    if (!(RCC->CR & RCC_CR_HSERDY)) {
        fatal(); /* crystal nahi hai -> yahin ruk jayenge (debug me pata chalega) */
    }

    /* 2) 72 MHz par flash 2 wait state maangta hai. Prefetch bhi on. */
    FLASH->ACR = FLASH_ACR_PRFTBE | FLASH_ACR_LATENCY_2;

    /* 3) Bus prescalers: APB1 max 36 MHz hai, isliye /2. */
    RCC->CFGR &= ~(RCC_CFGR_HPRE | RCC_CFGR_PPRE1 | RCC_CFGR_PPRE2);
    RCC->CFGR |=  (RCC_CFGR_HPRE_DIV1 | RCC_CFGR_PPRE1_DIV2 | RCC_CFGR_PPRE2_DIV1);

    /* 4) PLL: HSE source, x9 = 72 MHz */
    RCC->CFGR &= ~(RCC_CFGR_PLLSRC | RCC_CFGR_PLLMULL);
    RCC->CFGR |=  (RCC_CFGR_PLLSRC | RCC_CFGR_PLLMULL9);

    RCC->CR |= RCC_CR_PLLON;
    while (!(RCC->CR & RCC_CR_PLLRDY)) {
    }

    /* 5) SYSCLK = PLL, phir switch confirm karo */
    RCC->CFGR = (RCC->CFGR & ~RCC_CFGR_SW) | RCC_CFGR_SW_PLL;
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_PLL) {
    }

    SystemCoreClock = 72000000U; /* SysTick/baud calculations isi par depend karte hain */
}

static void led_init(void)
{
    RCC->APB2ENR |= RCC_APB2ENR_IOPCEN;
    (void)RCC->APB2ENR; /* read-back: clock enable apply hone ka wait */

    /* PC13: CNF=00 (push-pull), MODE=10 (output 2 MHz)  -> CRH bits [23:20] */
    GPIOC->CRH &= ~(GPIO_CRH_CNF13 | GPIO_CRH_MODE13);
    GPIOC->CRH |=  GPIO_CRH_MODE13_1;

    GPIOC->ODR |= GPIO_ODR_ODR13; /* active low -> 1 = LED off */
}

static void systick_1ms(void)
{
    SysTick->LOAD = (SystemCoreClock / 1000U) - 1U;
    SysTick->VAL  = 0U;
    SysTick->CTRL = SysTick_CTRL_CLKSOURCE_Msk  /* HCLK, HCLK/8 nahi */
                  | SysTick_CTRL_TICKINT_Msk
                  | SysTick_CTRL_ENABLE_Msk;
}

int main(void)
{
    clock_72mhz();
    led_init();
    systick_1ms();

    uint32_t next = 0U;

    for (;;) {
        /* Non-blocking blink: koi delay loop nahi, CPU free rehta hai.
         * Unsigned subtraction wrap-around ko handle karta hai. */
        if ((g_ms_ticks - next) >= 500U) {
            next += 500U;
            GPIOC->ODR ^= GPIO_ODR_ODR13;
        }
    }
}
