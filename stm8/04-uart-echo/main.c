/*
 * 04-uart-echo -- UART1 RX interrupt + ring buffer + echo.
 *
 * Board : STM8S103F3P6, PD5 = TX, PD4 = RX, 115200 8N1, HSI 16 MHz
 *
 * UART1 RX: datasheet vector 19, SDCC me __interrupt(17).
 * SDCC ka number datasheet se 2 kam hai (TIM4 25 -> 23, TX 20 -> 18).
 *
 * Jo type karo wahi echo hota hai; Enter par byte count print hota hai.
 * Ye `02` (interrupt) + `03` (UART) ka combination hai.
 */

typedef unsigned char  u8;
typedef unsigned int   u16;

/* ---- CLK ---------------------------------------------------------------- */
__at(0x50C6) volatile u8 CLK_CKDIVR;
__at(0x50C7) volatile u8 CLK_PCKENR1;

/* ---- GPIOD -------------------------------------------------------------- */
__at(0x500F) volatile u8 PD_ODR;
__at(0x5011) volatile u8 PD_DDR;
__at(0x5012) volatile u8 PD_CR1;

/* ---- UART1 -------------------------------------------------------------- */
__at(0x5230) volatile u8 UART1_SR;
__at(0x5231) volatile u8 UART1_DR;
__at(0x5232) volatile u8 UART1_BRR1;
__at(0x5233) volatile u8 UART1_BRR2;
__at(0x5235) volatile u8 UART1_CR2;

#define UART1_SR_TXE   0x80u
#define UART1_SR_RXNE  0x20u
#define UART1_CR2_RIEN 0x20u
#define UART1_CR2_TEN  0x08u
#define UART1_CR2_REN  0x04u

#define F_CPU  16000000UL
#define BAUD   115200UL

#define PD_TX  0x20u
#define PD_RX  0x10u

#define UART1_VECTOR_RX  17          /* datasheet 19 - 2 (SDCC numbering) */

/* ---- ring buffer -------------------------------------------------------- */
#define RB_SIZE 32u                 /* 2 ki power */
#define RB_MASK (RB_SIZE - 1u)

static volatile u8 rx_buf[RB_SIZE];
static volatile u8 rx_head;         /* ISR likhta hai */
static volatile u8 rx_tail;         /* main padhta hai */
static volatile u16 rx_dropped;

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

/* ISR: chhota rakhna hai -- sirf byte uthao aur buffer me daalo */
void uart_rx_isr(void) __interrupt(UART1_VECTOR_RX)
{
    u8 sr = UART1_SR;             /* SR padho ... */
    u8 d  = UART1_DR;             /* ... phir DR: isse RXNE clear hota hai */
    u8 next;

    (void)sr;

    next = (u8)((rx_head + 1u) & RB_MASK);
    if (next == rx_tail) {
        rx_dropped++;             /* buffer full */
        return;
    }
    rx_buf[rx_head] = d;
    rx_head = next;
}

static void uart_init(void)
{
    u16 div;

    CLK_PCKENR1 |= 0x04u;

    div = (u16)((F_CPU + (BAUD / 2UL)) / BAUD);
    UART1_BRR2 = (u8)(div & 0x0Fu);
    UART1_BRR1 = (u8)(div >> 4);

    /* RX interrupt enable + TX/RX enable */
    UART1_CR2 = UART1_CR2_TEN | UART1_CR2_REN | UART1_CR2_RIEN;
}

void main(void)
{
    u16 line_bytes = 0u;

    CLK_CKDIVR = 0x00u;

    /* Ring buffer state explicit reset -- startup zero-init par depend mat raho */
    rx_head = 0u;
    rx_tail = 0u;
    rx_dropped = 0u;

    /* PD5 output (TX), PD4 input + pull-up (RX) */
    PD_DDR |= PD_TX;
    PD_CR1 |= (PD_TX | PD_RX);

    uart_init();
    __asm__("rim");

    uart_puts("\r\nSTM8 echo ready. Type something.\r\n");

    for (;;) {
        u8 c;

        while (rx_tail != rx_head) {
            c = rx_buf[rx_tail];
            rx_tail = (u8)((rx_tail + 1u) & RB_MASK);

            uart_putc((char)c);
            line_bytes++;

            if (c == '\r' || c == '\n') {
                uart_puts("\r\n[");
                uart_putu(line_bytes);
                uart_puts(" bytes");
                if (rx_dropped) {
                    uart_puts(", dropped ");
                    uart_putu(rx_dropped);
                }
                uart_puts("]\r\n");
                line_bytes = 0u;
            }
        }

        __asm__("wfi");           /* koi kaam nahi -> sone jao, ISR jagayega */
    }
}
