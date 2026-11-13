/*
 * stm8/01-blink-pb5 - bare-register blink, no library.
 * Board: STM8S103F3P6 "minimum system" board (LED on PB5, active high).
 * Clock: HSI 16 MHz (reset default 2 MHz se change kiya).
 *
 * Registers yahan khud define kiye hain (SDCC device headers par depend nahi)
 * taaki address/bit meanings saaf dikhein. RM0016 GPIO + CLK chapters dekho.
 */

typedef unsigned char  u8;
typedef unsigned int   u16;

/* Clock */
__at(0x50C6) volatile u8 CLK_CKDIVR;   /* bit3 HSIDIV, bit2:0 CPUDIV */

/* Port B */
__at(0x5005) volatile u8 PB_ODR;
__at(0x5006) volatile u8 PB_IDR;
__at(0x5007) volatile u8 PB_DDR;
__at(0x5008) volatile u8 PB_CR1;
__at(0x5009) volatile u8 PB_CR2;

#define LED_MASK 0x20u                 /* PB5 */

static void delay_loop(u16 count)
{
    /* Rough delay: har iteration ~ kuch cycles. Exact timing ke liye TIM4 use karo. */
    volatile u16 i;
    for (i = 0; i < count; i++) {
    }
}

void main(void)
{
    /* 1. Clock: HSI 16 MHz with prescaler 1 (default reset value = 2 MHz) */
    CLK_CKDIVR = 0x00;

    /* 2. GPIO direction: PB5 = output */
    PB_DDR |= LED_MASK;

    /* 3. Output type: push-pull (0 = open drain). Speed: default slow is fine. */
    PB_CR1 |= LED_MASK;

    /* 4. Blink forever */
    for (;;) {
        PB_ODR ^= LED_MASK;
        delay_loop(30000);
    }
}
