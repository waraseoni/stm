"""Register name -> address helpers for the simulator and IC tabs."""

from .boards import get_board


def register_map(board_name):
    """Return a list of (name, address) for a board's key registers."""
    board = get_board(board_name)
    items = []
    items.append(("RCC_CR", board.rcc_base + 0x00))
    cfgr = 0x08 if board.rcc_kind == "f4" else 0x04
    items.append(("RCC_CFGR", board.rcc_base + cfgr))
    if board.rcc_kind == "f4":
        items.append(("RCC_AHB1ENR", board.rcc_base + 0x30))
        items.append(("RCC_APB1ENR", board.rcc_base + 0x40))
        items.append(("RCC_APB2ENR", board.rcc_base + 0x44))
    else:
        items.append(("RCC_APB2ENR", board.rcc_base + 0x18))
        items.append(("RCC_APB1ENR", board.rcc_base + 0x1C))
    odr_off = 0x14 if board.rcc_kind == "f4" else 0x0C
    idr_off = 0x10 if board.rcc_kind == "f4" else 0x08
    for name, base in board.gpio_ports.items():
        items.append(("GPIO%s_ODR" % name, base + odr_off))
        items.append(("GPIO%s_IDR" % name, base + idr_off))
        items.append(("GPIO%s_BSRR" % name, base + (0x18 if board.rcc_kind == "f4" else 0x10)))
    items.append(("USART_SR", board.usart_base + 0x00))
    items.append(("USART_DR", board.usart_base + 0x04))
    items.append(("USART_BRR", board.usart_base + 0x08))
    items.append(("USART_CR1", board.usart_base + 0x0C))
    items.append(("TIM_ARR", board.tim_base + 0x2C))
    items.append(("TIM_CCR1", board.tim_base + 0x34))
    items.append(("TIM_CNT", board.tim_base + 0x24))
    items.append(("SYSTICK_CTRL", 0xE000E010))
    items.append(("SYSTICK_LOAD", 0xE000E014))
    items.append(("SYSTICK_VAL", 0xE000E018))
    items.append(("NVIC_ISER0", 0xE000E100))
    items.append(("NVIC_ISER1", 0xE000E104))
    items.append(("SCB_VTOR", 0xE000ED08))
    # EXTI / SYSCFG (F4)
    if board.rcc_kind == "f4":
        items.append(("SYSCFG_EXTICR1", 0x40013808))
        items.append(("EXTI_IMR", 0x40013C00))
        items.append(("EXTI_FTSR", 0x40013C0C))
        items.append(("EXTI_PR", 0x40013C14))
    # DMA
    if board.rcc_kind == "f4":
        items.append(("DMA1_LISR", 0x40026000))
        items.append(("DMA1_HISR", 0x40026004))
    # SPI / I2C / ADC
    items.append(("SPI1_SR", 0x40013008))
    items.append(("SPI1_DR", 0x4001300C))
    items.append(("I2C1_SR1", 0x40005414))
    items.append(("I2C1_DR", 0x40005410))
    items.append(("ADC1_SR", 0x40012000))
    items.append(("ADC1_DR", 0x4001204C))
    return items


def resolve(name, board_name):
    name = name.strip().upper()
    for n, addr in register_map(board_name):
        if n == name:
            return addr
    return None


def names(board_name):
    return [n for n, _ in register_map(board_name)]