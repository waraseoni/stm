"""Register-level models for the STM32 peripherals used by the exercises.

The models are deliberately simple: they implement the bits the firmware
polls (ready flags, TXE, RXNE, COUNTFLAG) and record writes that tests can
inspect (ODR, CCR1, UART data).  They are not cycle accurate.
"""

MASKS = {1: 0xFF, 2: 0xFFFF, 4: 0xFFFFFFFF}


class RegFile:
    def __init__(self):
        self._words = {}

    def get(self, off):
        return self._words.get(off & ~3, 0)

    def put(self, off, val):
        self._words[off & ~3] = val & 0xFFFFFFFF


class Peripheral(RegFile):
    def __init__(self, machine, name, base):
        super().__init__()
        self.machine = machine
        self.name = name
        self.base = base

    def read(self, off, size):
        word = self.read_word(off)
        shift = (off & 3) * 8
        return (word >> shift) & MASKS[size]

    def write(self, off, size, value):
        base = off & ~3
        shift = (off & 3) * 8
        cur = self.read_word(base)
        mask = MASKS[size] << shift
        word = (cur & ~mask) | ((value & MASKS[size]) << shift)
        self.write_word(base, word)

    def read_word(self, off):
        return self.get(off)

    def write_word(self, off, val):
        self.put(off, val)


# --------------------------------------------------------------------------
# RCC
# --------------------------------------------------------------------------

class RCC_F4(Peripheral):
    CR = 0x00
    PLLCFGR = 0x04
    CFGR = 0x08
    AHB1ENR = 0x30
    APB1ENR = 0x40
    APB2ENR = 0x44

    def __init__(self, machine, base):
        super().__init__(machine, "RCC", base)
        self.put(self.CR, (1 << 0) | (1 << 1))   # HSION | HSIRDY

    def write_word(self, off, val):
        if off == self.CR:
            if val & (1 << 24):
                val |= 1 << 25                    # PLLON -> PLLRDY
            if val & (1 << 16):
                val |= 1 << 17                    # HSEON -> HSERDY
            self.put(self.CR, val)
            return
        if off == self.CFGR:
            # SW -> SWS so the "wait for switch" loops finish.
            sw = val & 0x3
            self.put(self.CFGR, (val & ~0xC) | (sw << 2))
            return
        self.put(off, val)


class RCC_F1(Peripheral):
    CR = 0x00
    CFGR = 0x04
    APB2ENR = 0x18
    APB1ENR = 0x1C

    def __init__(self, machine, base):
        super().__init__(machine, "RCC", base)
        self.put(self.CR, (1 << 0) | (1 << 1))   # HSION | HSIRDY

    def write_word(self, off, val):
        if off == self.CR:
            if val & (1 << 24):
                val |= 1 << 25                    # PLLON -> PLLRDY
            if val & (1 << 16):
                val |= 1 << 17                    # HSEON -> HSERDY
            self.put(self.CR, val)
            return
        if off == self.CFGR:
            sw = val & 0x3
            self.put(self.CFGR, (val & ~0xC) | (sw << 2))
            return
        self.put(off, val)


# --------------------------------------------------------------------------
# PWR / FLASH
# --------------------------------------------------------------------------

class PWR(Peripheral):
    CR = 0x00
    CSR = 0x04

    def __init__(self, machine, base):
        super().__init__(machine, "PWR", base)
        self.put(self.CSR, 1 << 15)               # VOSRDY

    def write_word(self, off, val):
        if off == self.CR:
            csr = self.get(self.CSR)
            if val & (1 << 16):                   # ODEN
                csr |= 1 << 16                    # ODRDY
            if val & (1 << 17):                   # ODSWEN
                csr |= 1 << 17                    # ODSWRDY
            self.put(self.CSR, csr)
        self.put(off, val)


class FlashReg(Peripheral):
    ACR = 0x00


# --------------------------------------------------------------------------
# GPIO
# --------------------------------------------------------------------------

class GPIO(Peripheral):
    # F4 offsets (default).  F1 boards remap them in __init__.
    MODER = 0x00
    OTYPER = 0x04
    OSPEEDR = 0x08
    PUPDR = 0x0C
    IDR = 0x10
    ODR = 0x14
    BSRR = 0x18
    LCKR = 0x1C
    AFR = 0x20
    BRR = 0x28

    def __init__(self, machine, name, base, kind="f4"):
        super().__init__(machine, name, base)
        if kind == "f1":
            self.CRL = 0x00
            self.CRH = 0x04
            self.IDR = 0x08
            self.ODR = 0x0C
            self.BSRR = 0x10
            self.BRR = 0x14
            self.LCKR = 0x18
        self.odr = 0
        self.prev_odr = 0
        self.idr = 0

    def read_word(self, off):
        if off == self.ODR:
            return self.odr
        if off == self.IDR:
            return self.idr
        return self.get(off)

    def write(self, off, size, value):
        base = off & ~3
        if base == self.ODR:
            self._set_odr(value & MASKS[size])
            return
        if base == self.BSRR and size == 4:
            set_bits = value & 0xFFFF
            reset_bits = (value >> 16) & 0xFFFF
            self._set_odr((self.odr | set_bits) & ~reset_bits)
            return
        if base == self.BRR and size == 4:
            self._set_odr(self.odr & ~(value & 0xFFFF))
            return
        super().write(off, size, value)

    def _set_odr(self, value):
        self.odr = value & 0xFFFF
        changed = self.odr ^ self.prev_odr
        self.prev_odr = self.odr
        if changed:
            self.machine.on_pins_changed(self.name, changed, self.odr)


# --------------------------------------------------------------------------
# USART
# --------------------------------------------------------------------------

class USART(Peripheral):
    SR = 0x00
    DR = 0x04
    BRR = 0x08
    CR1 = 0x0C
    CR2 = 0x10
    CR3 = 0x14
    GTPR = 0x18

    SR_TXE = 1 << 7
    SR_TC = 1 << 6
    SR_RXNE = 1 << 5

    CR1_RE = 1 << 2
    CR1_TE = 1 << 3
    CR1_RXNEIE = 1 << 5
    CR1_TXEIE = 1 << 7
    CR1_UE = 1 << 13

    def __init__(self, machine, name, base, irq=38):
        super().__init__(machine, name, base)
        self.irq = irq
        self.rx_byte = 0
        self.rx_pending = False
        self.tx_bytes = bytearray()

    # ---- read --------------------------------------------------------
    def read_word(self, off):
        if off == self.SR:
            sr = self.SR_TXE | self.SR_TC
            if self.rx_pending:
                sr |= self.SR_RXNE
            return sr
        if off == self.DR:
            data = self.rx_byte if self.rx_pending else 0
            self.rx_pending = False           # reading DR clears RXNE
            return data
        return self.get(off)

    # ---- write -------------------------------------------------------
    def write(self, off, size, value):
        base = off & ~3
        if base == self.DR:
            byte = value & 0xFF
            self.tx_bytes.append(byte)
            self.machine.on_uart_tx(byte)
            return
        super().write(off, size, value)

    def cr1(self):
        return self.get(self.CR1)

    def inject_rx(self, byte):
        self.rx_byte = byte & 0xFF
        self.rx_pending = True
        cr1 = self.cr1()
        if (cr1 & self.CR1_UE) and (cr1 & self.CR1_RE) and (cr1 & self.CR1_RXNEIE):
            self.machine.raise_irq(self.irq)

    def tx_enabled(self):
        cr1 = self.cr1()
        return bool(cr1 & self.CR1_UE) and bool(cr1 & self.CR1_TE)


# --------------------------------------------------------------------------
# Timers (TIM2 is enough for the PWM exercise)
# --------------------------------------------------------------------------

class TIM(Peripheral):
    CR1 = 0x00
    DIER = 0x0C
    SR = 0x10
    EGR = 0x14
    CCMR1 = 0x18
    CCER = 0x20
    CNT = 0x24
    PSC = 0x28
    ARR = 0x2C
    CCR1 = 0x34

    def __init__(self, machine, name, base):
        super().__init__(machine, name, base)
        self.ccr1_history = []

    def write_word(self, off, val):
        self.put(off, val)
        if off == self.CCR1:
            self.ccr1_history.append(val)
            if len(self.ccr1_history) > 4096:
                self.ccr1_history.pop(0)
            self.machine.on_pwm_ccr(val)

    def duty(self):
        arr = self.get(self.ARR)
        top = arr + 1
        if top <= 0:
            return 0.0
        return min(1.0, self.get(self.CCR1) / top)


# --------------------------------------------------------------------------
# SysTick (part of the PPB, handled by the machine)
# --------------------------------------------------------------------------

class SysTick(RegFile):
    CTRL = 0x00
    LOAD = 0x04
    VAL = 0x08
    CALIB = 0x0C

    CTRL_ENABLE = 1 << 0
    CTRL_TICKINT = 1 << 1
    CTRL_CLKSOURCE = 1 << 2
    CTRL_COUNTFLAG = 1 << 16

    def __init__(self):
        super().__init__()
        self.countflag = False

    def read(self, off, size):
        if off == self.CTRL:
            v = self.get(self.CTRL)
            if self.countflag:
                v |= self.CTRL_COUNTFLAG
            self.countflag = False             # read clears COUNTFLAG
            return v
        return self.get(off)

    def write(self, off, size, value):
        off &= ~3
        if off == self.VAL:
            self.countflag = False
        self.put(off, value & 0xFFFFFFFF)
