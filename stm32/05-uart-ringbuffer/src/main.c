/*
 * 05-uart-ringbuffer -- interrupt driven RX + ring buffer + echo.
 *
 * Board : Nucleo-F411RE / F446RE
 * UART  : USART2, PA2 TX / PA3 RX, AF7, 115200 8N1
 *
 * Kyun ring buffer?
 *   - ISR kabhi block nahi karta: bas byte daal ke wapas.
 *   - main loop apni speed par uthata hai -> data loss nahi (jab tak buffer
 *     bhara na ho).
 *   - ISR aur main ke beech sirf head/tail share hote hain, isliye lock ki
 *     zaroorat nahi (single producer / single consumer).
 *
 * Type karo: har character echo hoga, Enter par `[N bytes]` wapas aayega.
 */

#include <stdio.h>
#include <stdbool.h>
#include "stm32f4xx.h"

#define PCLK1_HZ  16000000U
#define BAUD      115200U

/* Power of 2 rakho -> modulo ki jagah mask (fast + safe ISR me) */
#define RB_SIZE   64U
#define RB_MASK   (RB_SIZE - 1U)

static volatile uint8_t  rb[RB_SIZE];
static volatile uint16_t rb_head;   /* ISR likhta hai */
static volatile uint16_t rb_tail;   /* main padhta hai */

static inline bool rb_put(uint8_t b)
{
    uint16_t next = (uint16_t)((rb_head + 1U) & RB_MASK);
    if (next == rb_tail) {
        return false;               /* buffer full -> byte drop */
    }
    rb[rb_head] = b;
    rb_head = next;
    return true;
}

static inline bool rb_get(uint8_t *b)
{
    if (rb_head == rb_tail) {
        return false;
    }
    *b = rb[rb_tail];
    rb_tail = (uint16_t)((rb_tail + 1U) & RB_MASK);
    return true;
}

static void uart2_init(uint32_t baud)
{
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN;
    RCC->APB1ENR |= RCC_APB1ENR_USART2EN;
    (void)RCC->APB1ENR;

    GPIOA->MODER &= ~(GPIO_MODER_MODER2 | GPIO_MODER_MODER3);
    GPIOA->MODER |=  (GPIO_MODER_MODER2_1 | GPIO_MODER_MODER3_1);

    GPIOA->OTYPER &= ~(GPIO_OTYPER_OT2 | GPIO_OTYPER_OT3);
    GPIOA->PUPDR &= ~(GPIO_PUPDR_PUPD2 | GPIO_PUPDR_PUPD3);
    GPIOA->PUPDR |=  (GPIO_PUPDR_PUPD2_0 | GPIO_PUPDR_PUPD3_0);

    GPIOA->AFR[0] &= ~(GPIO_AFRL_AFSEL2 | GPIO_AFRL_AFSEL3);
    GPIOA->AFR[0] |= (7U << GPIO_AFRL_AFSEL2_Pos)
                  |  (7U << GPIO_AFRL_AFSEL3_Pos);

    USART2->BRR = (PCLK1_HZ + (baud / 2U)) / baud;

    /* RXNE interrupt ON karo, phir USART enable */
    USART2->CR1 = USART_CR1_TE | USART_CR1_RE
                | USART_CR1_RXNEIE | USART_CR1_UE;

    NVIC_SetPriority(USART2_IRQn, 2);
    NVIC_EnableIRQ(USART2_IRQn);
}

static void uart2_putc(char c)
{
    while (!(USART2->SR & USART_SR_TXE)) {
    }
    USART2->DR = (uint8_t)c;
}

int _write(int fd, char *ptr, int len)
{
    (void)fd;
    for (int i = 0; i < len; i++) {
        uart2_putc(ptr[i]);
    }
    return len;
}

/* Hardware ISR -- chhota aur fast rakhna hai */
void USART2_IRQHandler(void)
{
    uint32_t sr = USART2->SR;                 /* flags ka snapshot */

    if (sr & (USART_SR_RXNE | USART_SR_ORE | USART_SR_FE | USART_SR_NE)) {
        uint8_t data = (uint8_t)USART2->DR;   /* SR+DR read = flags clear */
        if (sr & USART_SR_RXNE) {
            (void)rb_put(data);               /* full ho to drop */
        }
        /* ORE matlab main loop late tha -- yahan counter rakh sakte ho */
    }
}

int main(void)
{
    uart2_init(BAUD);
    setvbuf(stdout, NULL, _IONBF, 0);

    printf("\r\nRX ring buffer ready. Type something.\r\n");

    uint32_t line_bytes = 0U;

    for (;;) {
        uint8_t c;

        while (rb_get(&c)) {
            uart2_putc((char)c);
            line_bytes++;

            if (c == '\r' || c == '\n') {
                printf("\r\n[%lu bytes]\r\n", (unsigned long)line_bytes);
                line_bytes = 0U;
            }
        }

        /* Buffer khali hai -> interrupt ka wait (blocking delay se better) */
        if (rb_head == rb_tail) {
            __WFI();
        }
    }
}
