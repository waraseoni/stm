/* stm8/05-gpio-input-button - poll PA3 (input, pull-up) toggle PB5 LED.
 * UNVERIFIED (no SDCC on this machine). */
typedef unsigned char u8;
typedef unsigned int  u16;

__at(0x5000) volatile u8 PA_ODR;
__at(0x5001) volatile u8 PA_IDR;
__at(0x5002) volatile u8 PA_DDR;
__at(0x5003) volatile u8 PA_CR1;
__at(0x5004) volatile u8 PA_CR2;

__at(0x5005) volatile u8 PB_ODR;
__at(0x5006) volatile u8 PB_IDR;
__at(0x5007) volatile u8 PB_DDR;
__at(0x5008) volatile u8 PB_CR1;

__at(0x50C6) volatile u8 CLK_CKDIVR;

#define LED_MASK 0x20u     /* PB5 */
#define BTN_MASK 0x08u     /* PA3 */

static void delay(u16 n){ volatile u16 i; for(i=0;i<n;i++){} }

void main(void)
{
    CLK_CKDIVR = 0x00;          /* 16 MHz */

    /* LED output */
    PB_DDR |= LED_MASK;
    PB_CR1 |= LED_MASK;

    /* Button input with pull-up */
    PA_DDR &= ~BTN_MASK;
    PA_CR1 |= BTN_MASK;         /* input with pull-up */
    PA_CR2 &= ~BTN_MASK;        /* no interrupt */

    while (1) {
        if (!(PA_IDR & BTN_MASK)) {   /* pressed (active low) */
            PB_ODR ^= LED_MASK;
            delay(20000);
            while (!(PA_IDR & BTN_MASK)) {}  /* wait release */
            delay(20000);
        }
    }
}
