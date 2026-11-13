/*
 * 06-tim-pwm -- TIM2 CH1 hardware PWM, onboard LED (PA5) fade.
 *
 * Board : Nucleo-F411RE / F446RE
 * Pin   : PA5 = TIM2_CH1, AF1
 * Clock : HSI 16 MHz (TIM2 APB1 par, APB1 prescaler /1)
 *
 * Frequency: 16 MHz / (PSC+1) / (ARR+1) = 16e6 / 16 / 1000 = 1 kHz
 * Duty     : CCR1 / (ARR+1) * 100 %
 *
 * LED brightness = duty, CPU ka koi kaam nahi -- hardware chalata hai.
 * (Software PWM se compare karo: wahan CPU cycles jaate hain.)
 */

#include "stm32f4xx.h"

#define PWM_TOP  1000U   /* ARR+1 = 1000 steps = 0.1% resolution */

volatile uint32_t g_ms_ticks;

void SysTick_Handler(void)
{
    g_ms_ticks++;
}

static void pwm_init(void)
{
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN;
    RCC->APB1ENR |= RCC_APB1ENR_TIM2EN;
    (void)RCC->APB1ENR;

    /* PA5 -> alternate function mode, AF1 = TIM2_CH1 */
    GPIOA->MODER &= ~GPIO_MODER_MODER5;
    GPIOA->MODER |=  GPIO_MODER_MODER5_1;
    GPIOA->OTYPER &= ~GPIO_OTYPER_OT5;
    GPIOA->OSPEEDR = (GPIOA->OSPEEDR & ~GPIO_OSPEEDR_OSPEED5)
                   | GPIO_OSPEEDR_OSPEED5_0;
    GPIOA->AFR[0] &= ~GPIO_AFRL_AFSEL5;
    GPIOA->AFR[0] |= (1U << GPIO_AFRL_AFSEL5_Pos);

    TIM2->PSC  = 15U;                    /* 16 MHz -> 1 MHz counter */
    TIM2->ARR  = PWM_TOP - 1U;           /* 1 MHz / 1000 -> 1 kHz */
    TIM2->CCR1 = 0U;

    /* PWM mode 1: counter < CCR1 -> output active */
    TIM2->CCMR1 = TIM_CCMR1_OC1M_2 | TIM_CCMR1_OC1M_1 | TIM_CCMR1_OC1PE;
    TIM2->CCER |= TIM_CCER_CC1E;

    TIM2->EGR = TIM_EGR_UG;              /* preload values ko latch karo */
    TIM2->CR1 = TIM_CR1_ARPE | TIM_CR1_CEN;
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
    pwm_init();
    systick_1ms();

    uint32_t duty = 0U;
    int32_t  step = 10;      /* 0.1% * 10 = 1% per 10 ms -> ~2 s fade */
    uint32_t next = 0U;

    for (;;) {
        if ((g_ms_ticks - next) >= 10U) {
            next += 10U;

            /* Triangle wave: 0 -> 1000 -> 0 */
            if (step > 0 && duty + (uint32_t)step >= PWM_TOP) {
                duty = PWM_TOP;
                step = -step;
            } else if (step < 0 && duty < (uint32_t)(-step)) {
                duty = 0U;
                step = -step;
            } else {
                duty = (uint32_t)((int32_t)duty + step);
            }

            TIM2->CCR1 = duty;
        }
    }
}
