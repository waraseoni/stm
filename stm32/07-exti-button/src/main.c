/* 07-exti-button : Nucleo user button (PC13) toggles LED (PA5) via EXTI15_10.
 * Bare-metal, CMSIS only. UNVERIFIED (no ARM GCC on this machine). */
#include "stm32f4xx.h"

static void led_init(void) {
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN;
    GPIOA->MODER &= ~(3u << (5 * 2));
    GPIOA->MODER |=  (1u << (5 * 2));   /* PA5 output */
}

static void button_exti_init(void) {
    /* GPIOC clock + PC13 input (reset state is input, but enable clock) */
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOCEN;
    /* SYSCFG clock for EXTI mux */
    RCC->APB2ENR |= RCC_APB2ENR_SYSCFGEN;
    /* PC13 -> EXTI13 (port C = 2) */
    SYSCFG->EXTICR[3] &= ~(0xFu << ((13 % 4) * 4));
    SYSCFG->EXTICR[3] |=  (2u     << ((13 % 4) * 4));
    /* EXTI13: unmask + falling edge */
    EXTI->IMR  |= (1u << 13);
    EXTI->FTSR |= (1u << 13);
    /* NVIC: EXTI15_10 = IRQ 40 */
    NVIC_SetPriority(EXTI15_10_IRQn, 5);
    NVIC_EnableIRQ(EXTI15_10_IRQn);
}

void EXTI15_10_IRQHandler(void) {
    if (EXTI->PR & (1u << 13)) {
        EXTI->PR = (1u << 13);          /* clear pending */
        GPIOA->ODR ^= (1u << 5);       /* toggle LED */
    }
}

int main(void) {
    led_init();
    button_exti_init();
    for (;;) {
        __WFI();
    }
}
