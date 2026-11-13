"""Hand-written Cortex-M programs, assembled with keystone.

These exist so `stmlab demo` and the self tests can exercise the simulator on
machines that do not have an ARM toolchain installed.  Real firmware is run
from a GCC-produced ELF (`stmlab run firmware.elf`).
"""

import struct

from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB

# Where the demo places its code inside flash.
CODE_OFFSET = 0x100
HANDLER_OFFSET = 0x200
VECTOR_WORDS = 40          # covers IRQs up to 38 (USART2)


class Asm:
    """Small keystone wrapper that assembles at a fixed link address."""

    def __init__(self):
        self._ks = Ks(KS_ARCH_ARM, KS_MODE_THUMB)

    def __call__(self, source, addr):
        # Keystone's encoder can spin forever on lone-LF input coming from
        # Python strings; its native parser expects CRLF line endings.
        source = source.replace("\r\n", "\n").replace("\n", "\r\n")
        encoding, _ = self._ks.asm(source, addr)
        return bytes(encoding)


_asm = Asm()


def _load(reg, addr):
    """Thumb instructions that put a 32-bit constant in a register."""
    return "movw %s, #0x%04x\nmovt %s, #0x%04x" % (
        reg, addr & 0xFFFF, reg, (addr >> 16) & 0xFFFF
    )


def _gpio_layout(board):
    """Register offsets for the GPIO flavour of this board."""
    if board.rcc_kind == "f1":
        return {
            "config_off": 0x00 if board.led_pin < 8 else 0x04,   # CRL / CRH
            "config_val": 0x3 << (4 * (board.led_pin % 8)),       # output 50 MHz
            "odr": 0x0C,
            "bsrr": 0x10,
        }
    return {
        "config_off": 0x00,                                       # MODER
        "config_val": 0x1 << (2 * board.led_pin),                 # output
        "odr": 0x14,
        "bsrr": 0x18,
    }


def _gpio_clock(board):
    port = board.led_port
    if board.rcc_kind == "f1":
        return 0x18, 1 << (ord(port) - ord("A"))                  # APB2ENR
    return 0x30, 1 << (ord(port) - ord("A"))                      # AHB1ENR


def _usart_clock(board):
    if board.rcc_kind == "f1":
        return 0x18, 1 << 14                                      # USART1EN
    bit = 17 if board.usart_name == "USART2" else 16
    return 0x40, 1 << bit                                         # APB1ENR


def _vector_table(board, entry, handlers):
    """handlers: {irq_number: address}"""
    size = VECTOR_WORDS * 4
    for irq in handlers:
        size = max(size, (irq + 1) * 4)
    table = bytearray(size)
    struct.pack_into("<I", table, 0, board.ram_end)
    struct.pack_into("<I", table, 4, entry | 1)
    for irq, addr in handlers.items():
        struct.pack_into("<I", table, 4 * irq, addr | 1)
    return bytes(table)


def build_demo(board):
    """Enable the LED, print over USART, then blink from the SysTick handler."""
    gpio_base = board.gpio_ports[board.led_port]
    g = _gpio_layout(board)
    rcc_off, gpio_bit = _gpio_clock(board)
    usart_off, usart_bit = _usart_clock(board)
    handler_addr = board.flash_base + HANDLER_OFFSET
    msg_addr = board.flash_base + 0x300
    counter = board.ram_base + 0x100

    body = """
    // --- GPIO clock + LED pin as output ---
    {ld_rcc}
    ldr r0, [r1, #{rcc_off:#04x}]
    orr r0, r0, #{gpio_bit:#x}
    str r0, [r1, #{rcc_off:#04x}]
    {ld_gpio}
    movw r0, #{cfg_lo:#06x}
    movt r0, #{cfg_hi:#06x}
    str r0, [r1, #{cfg_off:#04x}]
    movs r0, #0
    str r0, [r1, #{odr:#04x}]

    // --- USART: 115200 8N1 at 16 MHz ---
    {ld_rcc2}
    ldr r0, [r1, #{usart_off:#04x}]
    orr r0, r0, #{usart_bit:#x}
    str r0, [r1, #{usart_off:#04x}]
    {ld_usart}
    movw r0, #139
    str r0, [r2, #0x08]
    movw r0, #0x2008
    str r0, [r2, #0x0c]

    {ld_msg}
print_loop:
    ldrb r4, [r5], #1
    cmp r4, #0
    beq print_done
print_wait:
    ldr r0, [r2, #0x00]
    tst r0, #0x80
    beq print_wait
    str r4, [r2, #0x04]
    b print_loop
print_done:

    // --- SysTick: 1 ms tick, interrupt enabled ---
    {ld_systick}
    movw r0, #999
    str r0, [r1, #0x04]
    movs r0, #0
    str r0, [r1, #0x08]
    movs r0, #7
    str r0, [r1, #0x00]

forever:
    wfi
    b forever
""".format(
        ld_rcc=_load("r1", board.rcc_base),
        ld_rcc2=_load("r1", board.rcc_base),
        ld_gpio=_load("r1", gpio_base),
        ld_usart=_load("r2", board.usart_base),
        ld_systick=_load("r1", 0xE000E010),
        ld_msg=_load("r5", msg_addr),
        rcc_off=rcc_off,
        gpio_bit=gpio_bit,
        usart_off=usart_off,
        usart_bit=usart_bit,
        cfg_off=g["config_off"],
        cfg_lo=g["config_val"] & 0xFFFF,
        cfg_hi=(g["config_val"] >> 16) & 0xFFFF,
        odr=g["odr"],
    )

    handler = """
    {ld_ctr}
    ldr r1, [r0]
    adds r1, #1
    str r1, [r0]
    tst r1, #8
    bne led_reset
    {ld_set}
    b led_write
led_reset:
    {ld_reset}
led_write:
    {ld_gpio}
    str r2, [r3, #{bsrr:#04x}]
    bx lr
""".format(
        ld_ctr=_load("r0", counter),
        ld_set=_load("r2", 1 << board.led_pin),
        ld_reset=_load("r2", 1 << (board.led_pin + 16)),
        ld_gpio=_load("r3", gpio_base),
        bsrr=g["bsrr"],
    )

    code_addr = board.flash_base + CODE_OFFSET
    segments = [
        (board.flash_base,
         _vector_table(board, code_addr, {15: handler_addr})),
        (code_addr, _asm(body, code_addr)),
        (handler_addr, _asm(handler, handler_addr)),
        (msg_addr, b"Hi from stmlab\n\x00"),
    ]
    return segments, code_addr, {"tick_counter": counter}


def build_uart_echo(board):
    """USART RX interrupt echoes bytes and stores them in a RAM buffer."""
    buf = board.ram_base + 0x100
    handler_addr = board.flash_base + HANDLER_OFFSET
    usart_off, usart_bit = _usart_clock(board)

    body = """
    {ld_rcc}
    ldr r0, [r1, #{off:#04x}]
    orr r0, r0, #{bit:#x}
    str r0, [r1, #{off:#04x}]
    {ld_usart}
    movs r0, #139
    str r0, [r2, #0x08]
    movw r0, #0x2024
    str r0, [r2, #0x0c]
    movw r1, #0xe104
    movt r1, #0xe000
    movs r0, #0x{iser_bit:x}
    str r0, [r1]

forever:
    b forever
""".format(
        ld_rcc=_load("r1", board.rcc_base),
        ld_usart=_load("r2", board.usart_base),
        off=usart_off, bit=usart_bit,
        iser_bit=1 << (board.usart_irq % 32),
    )

    handler = """
    {ld_usart}
    ldr r3, [r2, #0x04]             // received byte, clears RXNE
    {ld_buf}
    ldrb r0, [r1]
    adds r0, #1
    strb r0, [r1]
    strb r3, [r1, r0]
echo_wait:
    ldr r0, [r2, #0x00]
    tst r0, #0x80
    beq echo_wait
    str r3, [r2, #0x04]
    bx lr
""".format(
        ld_usart=_load("r2", board.usart_base),
        ld_buf=_load("r1", buf),
    )

    code_addr = board.flash_base + CODE_OFFSET
    segments = [
        (board.flash_base,
         _vector_table(board, code_addr, {board.usart_irq: handler_addr})),
        (code_addr, _asm(body, code_addr)),
        (handler_addr, _asm(handler, handler_addr)),
    ]
    return segments, code_addr, {"rx_buffer": buf}
