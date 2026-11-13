/*
 * 02-f4-blink -- bare-metal, sirf CMSIS. Koi HAL nahi.
 *
 * Board: Nucleo-F411RE / Nucleo-F446RE
 * LED  : PA5 (LD2 green), ACTIVE HIGH
 * Clock: HSI 16 MHz (koi PLL nahi) -- board-independent aur safe.
 *
 * 84 MHz / 180 MHz PLL exercise `03-clock-pll` ka kaam hai, kyunki wahan
 * FLASH latency + voltage scaling (VOS/overdrive) sahi set karne padte hain
 * aur galti par board hang ho jata hai. Pehle basic cheezein chalao.
 *
 * F1 se difference (dhyan do):
 *   - GPIO F4 me per-pin registers: MODER/OTYPER/PUPDR/OSPEEDR
 *   - Clock enable AHB1ENR me (F1 me APB2ENR me tha)
 */

#include "stm32f4xx.h"

volatile uint32_t g_ms_ticks;

void SysTick_Handler(void)
{
    g_ms_ticks++;
}

static void led_init(void)
{
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN;
    (void)RCC->AHB1ENR;

    /* PA5: MODER = 01 (general purpose output) */
    GPIOA->MODER &= ~GPIO_MODER_MODER5;
    GPIOA->MODER |=  GPIO_MODER_MODER5_0;

    GPIOA->OTYPER  &= ~GPIO_OTYPER_OT5;      /* 0 = push-pull */
    GPIOA->PUPDR   &= ~GPIO_PUPDR_PUPD5;     /* 00 = no pull */
    GPIOA->OSPEEDR |=  GPIO_OSPEEDR_OSPEED5_0; /* 01 = medium speed */

    GPIOA->ODR &= ~GPIO_ODR_OD5;             /* active high -> 0 = off */
}

static void systick_1ms(void)
{
    SysTick->LOAD = (SystemCoreClock / 1000U) - 1U;
    SysTick->VAL  = 0U;
    SysTick->CTRL = SysTick_CTRL_CLKSOURCE_Msk
                  | SysTick_CTRL_TICKINT_Msk
                  | SysTick_CTRL_ENABLE_Msk;
}

int main(void)
{
    led_init();
    systick_1ms();

    uint32_t next = 0U;

    for (;;) {
        if ((g_ms_ticks - next) >= 200U) {
            next += 200U;
            GPIOA->ODR ^= GPIO_ODR_OD5;
        }
    }
}
