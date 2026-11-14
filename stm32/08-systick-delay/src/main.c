/* 08-systick-delay : 1 ms SysTick + blocking delay. UNVERIFIED. */
#include "stm32f4xx.h"

static volatile uint32_t ms_ticks = 0;

void SysTick_Handler(void) { ms_ticks++; }

static void systick_init(void) {
    SysTick->LOAD = (16000000u / 1000u) - 1u;   /* 16 MHz, 1 ms */
    SysTick->VAL = 0;
    SysTick->CTRL = SysTick_CTRL_CLKSOURCE_Msk | SysTick_CTRL_TICKINT_Msk | SysTick_CTRL_ENABLE_Msk;
}

void delay_ms(uint32_t ms) {
    uint32_t start = ms_ticks;
    while ((ms_ticks - start) < ms) { __WFI(); }
}

int main(void) {
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN;
    GPIOA->MODER &= ~(3u << 10);
    GPIOA->MODER |=  (1u << 10);   /* PA5 output */
    systick_init();
    for (;;) {
        GPIOA->ODR ^= (1u << 5);
        delay_ms(500);
    }
}
