/*
 * 02-tim4-interrupt -- TIM4 se 1 ms tick, hardware interrupt ke saath.
 *
 * Board : STM8S103F3P6 minimum system board (LED = PB5, active high)
 * Clock : HSI 16 MHz
 *
 * TIM4 = basic 8-bit timer: sirf counter + prescaler + auto-reload.
 * PWM channels nahi hote -- uske liye TIM2 use karo.
 *
 * TIM4 UPD/OVF: datasheet vector 25, par SDCC me __interrupt(23).
 *
 * GOTCHA: SDCC ka number datasheet ke vector number se 2 kam hai (SDCC TLI ko
 * int0 maanta hai; reset aur trap alag handle hote hain). Isliye:
 *   datasheet 25 TIM4 -> SDCC 23, UART1 RX 19 -> 17, UART1 TX 20 -> 18,
 *   EXTI PORTB 6 -> 4, ADC1 24 -> 22, EEPROM 26 -> 24.
 * Verify karne ka tareeka: build ke baad .rst/.map me `;intN` comment dekho.
 * Agar board alag hai (STM8S003/S105...) to datasheet se number confirm karo.
 */

typedef unsigned char  u8;
typedef unsigned int   u16;

/* ---- CLK ---------------------------------------------------------------- */
__at(0x50C6) volatile u8 CLK_CKDIVR;
__at(0x50C7) volatile u8 CLK_PCKENR1;

/* ---- GPIOB -------------------------------------------------------------- */
__at(0x5005) volatile u8 PB_ODR;
__at(0x5007) volatile u8 PB_DDR;
__at(0x5008) volatile u8 PB_CR1;

/* ---- TIM4 --------------------------------------------------------------- */
/* Note: STM8S103/003 par CR1 ke baad 2 reserved bytes hain, isliye IER +3 par
 * hai (0x5340 + 3). Ye SPL ke TIM4_TypeDef se verify kiya gaya hai. */
__at(0x5340) volatile u8 TIM4_CR1;
__at(0x5343) volatile u8 TIM4_IER;
__at(0x5344) volatile u8 TIM4_SR1;
__at(0x5345) volatile u8 TIM4_EGR;
__at(0x5346) volatile u8 TIM4_CNTR;
__at(0x5347) volatile u8 TIM4_PSCR;
__at(0x5348) volatile u8 TIM4_ARR;

#define TIM4_CR1_CEN  0x01u
#define TIM4_IER_UIE  0x01u
#define TIM4_SR1_UIF  0x01u
#define TIM4_EGR_UG   0x01u

#define LED_MASK      0x20u          /* PB5 */

#define TIM4_VECTOR_UPD  23          /* datasheet 25 - 2 (SDCC numbering) */

static volatile u16 g_ms;

void tim4_isr(void) __interrupt(TIM4_VECTOR_UPD)
{
    TIM4_SR1 &= (u8)~TIM4_SR1_UIF;   /* flag clear -- warna re-entry loop */
    g_ms++;
}

void main(void)
{
    /* 1. 16 MHz */
    CLK_CKDIVR = 0x00u;

    /* 2. TIM4 clock gate (PCKENR1 bit4) */
    CLK_PCKENR1 |= 0x10u;

    /* 3. LED pin */
    PB_DDR |= LED_MASK;
    PB_CR1 |= LED_MASK;

    /* 4. 16 MHz / 2^6 = 250 kHz -> 250 counts = 1 ms
     *    (PSCR aur ARR buffered hain: EGR.UG se turant latch karo) */
    TIM4_PSCR = 6u;
    TIM4_ARR  = 250u - 1u;
    TIM4_CNTR = 0u;
    TIM4_EGR  = TIM4_EGR_UG;

    TIM4_SR1 = 0u;                   /* purana UIF saaf */
    TIM4_IER |= TIM4_IER_UIE;        /* update interrupt enable */
    TIM4_CR1 |= TIM4_CR1_CEN;        /* counter start */

    __asm__("rim");                  /* interrupts globally enable */

    u16 next = 0u;

    for (;;) {
        /* Non-blocking: ISR tick badhata hai, main loop compare karta hai.
         * unsigned subtraction wrap-around (65 s) handle karta hai. */
        if ((u16)(g_ms - next) >= 500u) {
            next += 500u;
            PB_ODR ^= LED_MASK;
        }
    }
}
