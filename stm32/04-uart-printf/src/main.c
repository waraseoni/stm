/*
 * 04-uart-printf -- USART2 + newlib printf retarget.
 *
 * Board : Nucleo-F411RE / Nucleo-F446RE (dono par same pins)
 * UART  : USART2, PA2 = TX, PA3 = RX, AF7
 * Speed : 115200 8N1, PCLK1 = 16 MHz (HSI, koi PLL nahi)
 * Cable : Nucleo ka onboard ST-Link VCP -> USB, koi extra wire nahi
 *
 * printf ke liye do cheezein zaroori hain:
 *   1. _write() ka apna implementation (newlib ka syscall hook)
 *   2. stdout unbuffered (warna output buffer bharte tak gayab rehta hai)
 */

#include <stdio.h>
#include "stm32f4xx.h"

#define PCLK1_HZ  16000000U   /* APB1 clock; PLL lagao to ye badalna hoga */
#define BAUD      115200U

volatile uint32_t g_ms_ticks;

void SysTick_Handler(void)
{
    g_ms_ticks++;
}

static void uart2_init(uint32_t baud)
{
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN;
    RCC->APB1ENR |= RCC_APB1ENR_USART2EN;
    (void)RCC->APB1ENR;

    /* PA2/PA3 -> alternate function mode (MODER = 10) */
    GPIOA->MODER &= ~(GPIO_MODER_MODER2 | GPIO_MODER_MODER3);
    GPIOA->MODER |=  (GPIO_MODER_MODER2_1 | GPIO_MODER_MODER3_1);

    /* push-pull, no pull-up on TX; RX par pull-up safe rehta hai */
    GPIOA->OTYPER &= ~(GPIO_OTYPER_OT2 | GPIO_OTYPER_OT3);
    GPIOA->PUPDR &= ~(GPIO_PUPDR_PUPD2 | GPIO_PUPDR_PUPD3);
    GPIOA->PUPDR |=  (GPIO_PUPDR_PUPD2_0 | GPIO_PUPDR_PUPD3_0);

    /* AF7 = USART2 (F411 aur F446 dono par same) */
    GPIOA->AFR[0] &= ~(GPIO_AFRL_AFSEL2 | GPIO_AFRL_AFSEL3);
    GPIOA->AFR[0] |= (7U << GPIO_AFRL_AFSEL2_Pos)
                  |  (7U << GPIO_AFRL_AFSEL3_Pos);

    /* OVER8 = 0 -> BRR = round(PCLK / baud) */
    USART2->BRR = (PCLK1_HZ + (baud / 2U)) / baud;

    USART2->CR1 = USART_CR1_TE | USART_CR1_RE | USART_CR1_UE;
}

static void uart2_putc(char c)
{
    while (!(USART2->SR & USART_SR_TXE)) {
    }
    USART2->DR = (uint8_t)c;
}

/* newlib yahi call karta hai jab printf output likhta hai */
int _write(int fd, char *ptr, int len)
{
    (void)fd;
    for (int i = 0; i < len; i++) {
        uart2_putc(ptr[i]);
    }
    return len;
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
    uart2_init(BAUD);
    systick_1ms();

    /* Bahut important: warna printf ka output buffer me pada rehta hai */
    setvbuf(stdout, NULL, _IONBF, 0);

    printf("\r\nSTM32 UART OK -- %lu Hz, %lu baud\r\n",
           (unsigned long)SystemCoreClock, (unsigned long)BAUD);

    uint32_t next = 0U;
    uint32_t count = 0U;

    for (;;) {
        if ((g_ms_ticks - next) >= 1000U) {
            next += 1000U;
            printf("tick %lu s\r\n", (unsigned long)++count);
        }
    }
}
