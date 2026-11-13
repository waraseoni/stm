"""Board definitions for the STM32 simulator.

Only the peripherals used by the exercises in this workspace are modelled.
Addresses are from RM0008 (F1) and RM0090 (F4).
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Board:
    name: str
    core: str                    # "cortex-m3" | "cortex-m4"
    flash_size: int
    ram_size: int
    default_cpu_hz: int
    rcc_base: int
    rcc_kind: str                # "f1" | "f4"
    gpio_ports: dict
    usart_base: int
    usart_name: str
    led_port: str
    led_pin: int
    usart_irq: int = 38          # USART2_IRQn on F4
    led_active_low: bool = False
    button_port: str = "C"
    button_pin: int = 13
    button_active_low: bool = True
    pwr_base: int = 0x40007000
    flash_reg_base: int = 0x40023C00
    tim_base: int = 0x40000000

    flash_base: int = 0x08000000
    ram_base: int = 0x20000000

    @property
    def flash_end(self):
        return self.flash_base + self.flash_size

    @property
    def ram_end(self):
        return self.ram_base + self.ram_size


F4_GPIO = {
    "A": 0x40020000,
    "B": 0x40020400,
    "C": 0x40020800,
    "D": 0x40020C00,
    "E": 0x40021000,
}

F1_GPIO = {
    "A": 0x40010800,
    "B": 0x40010C00,
    "C": 0x40011000,
    "D": 0x40011400,
}

BOARDS = {
    "f411re": Board(
        name="f411re",
        core="cortex-m4",
        flash_size=512 * 1024,
        ram_size=128 * 1024,
        default_cpu_hz=16_000_000,
        rcc_base=0x40023800,
        rcc_kind="f4",
        gpio_ports=F4_GPIO,
        usart_base=0x40004400,          # USART2
        usart_name="USART2",
        led_port="A",
        led_pin=5,
        button_port="C",
        button_pin=13,
    ),
    "f446re": Board(
        name="f446re",
        core="cortex-m4",
        flash_size=512 * 1024,
        ram_size=128 * 1024,
        default_cpu_hz=16_000_000,
        rcc_base=0x40023800,
        rcc_kind="f4",
        gpio_ports=F4_GPIO,
        usart_base=0x40004400,
        usart_name="USART2",
        led_port="A",
        led_pin=5,
        button_port="C",
        button_pin=13,
    ),
    "f103c8": Board(
        name="f103c8",
        core="cortex-m3",
        flash_size=64 * 1024,
        ram_size=20 * 1024,
        default_cpu_hz=8_000_000,
        rcc_base=0x40021000,
        rcc_kind="f1",
        gpio_ports=F1_GPIO,
        usart_base=0x40013800,          # USART1 (not modelled specially)
        usart_name="USART1",
        usart_irq=37,                   # USART1_IRQn
        led_port="C",
        led_pin=13,
        led_active_low=True,
        pwr_base=0x40007000,            # not present on F1; unused
        flash_reg_base=0x40022000,
        tim_base=0x40000000,
    ),
}


def get_board(name):
    key = name.lower()
    if key not in BOARDS:
        raise KeyError(
            "unknown board '%s' (choose: %s)" % (name, ", ".join(sorted(BOARDS)))
        )
    return BOARDS[key]
