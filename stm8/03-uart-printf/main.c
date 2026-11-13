/*
 * 03-uart-printf -- UART1 TX (polling), 115200 8N1, PD5.
 *
 * Board : STM8S103F3P6 minimum system board
 * Clock : HSI 16 MHz
 * Wiring: PD5 (TX) -> USB-UART RX, GND common. (RX = PD4, abhi use nahi)
 *
 * 8 KB flash wale chip par printf mehnga hai (~2-4 KB). Isliye yahan apne
 * chhote helpers hain: uart_puts / uart_putu. `04` me RX bhi add hoga.
 */

typedef unsigned char  u8;
typedef unsigned int   u16;
typedef unsigned long  u32;

/* ---- CLK ---------------------------------------------------------------- */
__at(0x50C6) volatile u8 CLK_CKDIVR;
__at(0x50C7) volatile u8 CLK_PCKENR1;

/* ---- GPIOD (PD4 = RX, PD5 = TX) ---------------------------------------- */
__at(0x500F) volatile u8 PD_ODR;
__at(0x5011) volatile u8 PD_DDR;
__at(0x5012) volatile u8 PD_CR1;

/* ---- UART1 -------------------------------------------------------------- */
__at(0x5230) volatile u8 UART1_SR;
__at(0x5231) volatile u8 UART1_DR;
__at(0x5232) volatile u8 UART1_BRR1;
__at(0x5233) volatile u8 UART1_BRR2;
__at(0x5234) volatile u8 UART1_CR1;
__at(0x5235) volatile u8 UART1_CR2;

#define UART1_SR_TXE   0x80u
#define UART1_CR2_TEN  0x08u
#define UART1_CR2_REN  0x04u

#define F_CPU  16000000UL
#define BAUD   115200UL

#define PD_TX  0x20u
#define PD_RX  0x10u

static void uart_init(void)
{
    /* UART1 clock gate (PCKENR1 bit2) */
    CLK_PCKENR1 |= 0x04u;

    /* BRR = f_master / baud. BRR2 me fraction (low nibble) hai aur
     * BRR2 ko BRR1 se PEHLE likhna padta hai (RM0016). */
    u16 div = (u16)((F_CPU + (BAUD / 2UL)) / BAUD);

    UART1_BRR2 = (u8)(div & 0x0Fu);
    UART1_BRR1 = (u8)(div >> 4);

    UART1_CR2 = UART1_CR2_TEN | UART1_CR2_REN;
}

static void uart_putc(char c)
{
    while (!(UART1_SR & UART1_SR_TXE)) {
    }
    UART1_DR = (u8)c;
}

static void uart_puts(const char *s)
{
    while (*s) {
        uart_putc(*s++);
    }
}

/* 0..65535 ke liye chhota integer printer */
static void uart_putu(u16 v)
{
    char buf[6];
    u8   n = 0;

    if (v == 0u) {
        uart_putc('0');
        return;
    }
    while (v > 0u) {
        buf[n++] = (char)('0' + (v % 10u));
        v /= 10u;
    }
    while (n > 0u) {
        uart_putc(buf[--n]);
    }
}

static void delay_ms(u16 ms)
{
    /* Calibrated nahi hai -- sirf demo. Exact timing ke liye TIM4 (02) use karo. */
    volatile u16 i;
    while (ms--) {
        for (i = 0; i < 2000u; i++) {
        }
    }
}

void main(void)
{
    CLK_CKDIVR = 0x00u;               /* 16 MHz */

    /* PD5 = output (push-pull), PD4 = input with pull-up */
    PD_DDR |= PD_TX;
    PD_CR1 |= (PD_TX | PD_RX);

    uart_init();

    uart_puts("\r\nSTM8 UART1 OK @115200\r\n");

    u16 count = 0u;
    for (;;) {
        uart_puts("count = ");
        uart_putu(count++);
        uart_puts("\r\n");
        delay_ms(1000u);
    }
}
