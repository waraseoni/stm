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


# --------------------------------------------------------------------------
# SYSCFG + EXTI (F4; minimal)
# --------------------------------------------------------------------------

class SYSCFG(Peripheral):
    MEMRMP = 0x00
    PMC = 0x04
    EXTICR = (0x08, 0x0C, 0x10, 0x14)

    def exti_port(self, line):
        idx = line // 4
        off = self.EXTICR[idx]
        field = (line % 4) * 4
        return (self.get(off) >> field) & 0xF


class EXTI(Peripheral):
    IMR = 0x00
    EMR = 0x04
    RTSR = 0x08
    FTSR = 0x0C
    SWIER = 0x10
    PR = 0x14

    def __init__(self, machine, name, base, syscfg):
        super().__init__(machine, name, base)
        self.syscfg = syscfg

    def write_word(self, off, val):
        if off == self.SWIER:
            # software interrupt: trigger lines where bit set
            for line in range(16):
                if val & (1 << line):
                    self._trigger(line, rising=True, software=True)
            self.put(self.SWIER, 0)
            return
        if off == self.PR:
            # write 1 to clear
            cur = self.get(self.PR)
            self.put(self.PR, cur & ~val)
            return
        self.put(off, val)

    def _trigger(self, line, rising, software=False):
        if line < 0 or line > 15:
            return
        # SYSCFG selects which GPIO port feeds this EXTI line.
        port_sel = self.syscfg.exti_port(line) if self.syscfg is not None else 0
        # port_sel 0=A,1=B,...; we do not filter by port here because the
        # caller already knows the port; filtering happens in Machine.
        imr = self.get(self.IMR)
        if not (imr & (1 << line)):
            return
        if not software:
            rtsr = self.get(self.RTSR)
            ftsr = self.get(self.FTSR)
            if rising and not (rtsr & (1 << line)):
                return
            if (not rising) and not (ftsr & (1 << line)):
                return
        pr = self.get(self.PR)
        self.put(self.PR, pr | (1 << line))
        self.machine.raise_exti(line)

    def trigger_from_gpio(self, port_index, line, rising):
        # port_index: 0=A,1=B,...; only fire if SYSCFG selects this port
        if self.syscfg is not None:
            if self.syscfg.exti_port(line) != port_index:
                return
        self._trigger(line, rising, software=False)

    def irq_for_line(self, line):
        if line <= 4:
            return 6 + line
        if line <= 9:
            return 23
        return 40


# --------------------------------------------------------------------------
# DMA (F4, minimal, synchronous transfer on EN)
# --------------------------------------------------------------------------

class DMA(Peripheral):
    # Stream i registers: base + 0x10 + i*0x18
    LISR = 0x00
    HISR = 0x04
    LIFCR = 0x08
    HIFCR = 0x0C
    STREAM_STRIDE = 0x18
    STREAM_BASE = 0x10

    TCIF_BITS = (5, 11, 17, 23)   # within LISR/HISR for streams 0-3 / 4-7
    CR_EN = 1 << 0
    CR_TCIE = 1 << 4
    CR_DIR_SHIFT = 6
    CR_PSIZE_SHIFT = 11
    CR_MSIZE_SHIFT = 13

    def __init__(self, machine, name, base):
        super().__init__(machine, name, base)
        self.stream_irq_base = 11 if "DMA1" in name else 56

    def _stream_off(self, stream):
        return self.STREAM_BASE + stream * self.STREAM_STRIDE

    def _size_bytes(self, code):
        return (1, 2, 4)[code & 3] if code in (0, 1, 2) else 1

    def write_word(self, off, val):
        # flag clear registers
        if off == self.LIFCR or off == self.HIFCR:
            lisr = self.get(self.LISR)
            hisr = self.get(self.HISR)
            if off == self.LIFCR:
                self.put(self.LISR, lisr & ~val)
            else:
                self.put(self.HISR, hisr & ~val)
            return
        # stream CR write
        for stream in range(8):
            cr_off = self._stream_off(stream)
            if off == cr_off:
                self.put(cr_off, val)
                if val & self.CR_EN:
                    self._transfer(stream, val)
                return
        # other stream regs / default
        self.put(off, val)

    def _transfer(self, stream, cr):
        ndtr_off = self._stream_off(stream) + 0x04
        par_off = self._stream_off(stream) + 0x08
        m0ar_off = self._stream_off(stream) + 0x0C
        ndtr = self.get(ndtr_off)
        par = self.get(par_off)
        m0ar = self.get(m0ar_off)
        direction = (cr >> self.CR_DIR_SHIFT) & 3
        psize = self._size_bytes((cr >> self.CR_PSIZE_SHIFT) & 3)
        msize = self._size_bytes((cr >> self.CR_MSIZE_SHIFT) & 3)
        size = msize if direction != 0 else psize

        if direction == 0:          # peripheral -> memory
            for i in range(ndtr):
                v = self.machine.peek(par, size)
                self.machine.poke(m0ar + i * size, size, v)
        elif direction == 1:        # memory -> peripheral
            for i in range(ndtr):
                v = self.machine.peek(m0ar + i * size, size)
                self.machine.poke(par, size, v)
        else:                       # memory -> memory
            for i in range(ndtr):
                v = self.machine.peek(m0ar + i * size, size)
                self.machine.poke(par + i * size, size, v)

        # clear EN, NDTR
        cr_off = self._stream_off(stream)
        self.put(cr_off, self.get(cr_off) & ~self.CR_EN)
        self.put(ndtr_off, 0)

        # set TCIF flag
        tcie = bool(cr & self.CR_TCIE)
        bit = self.TCIF_BITS[stream % 4]
        if stream < 4:
            self.put(self.LISR, self.get(self.LISR) | (1 << bit))
        else:
            self.put(self.HISR, self.get(self.HISR) | (1 << bit))

        if tcie:
            irq = self.stream_irq_base + stream
            self.machine.pending.add(irq)

    def read_word(self, off):
        if off == self.LISR:
            return self.get(self.LISR)
        if off == self.HISR:
            return self.get(self.HISR)
        return self.get(off)


# --------------------------------------------------------------------------
# SPI / I2C / ADC (minimal flag models)
# --------------------------------------------------------------------------

class SPI(Peripheral):
    CR1 = 0x00
    CR2 = 0x04
    SR = 0x08
    DR = 0x0C

    SR_RXNE = 1 << 0
    SR_TXE = 1 << 1
    SR_BSY = 1 << 7

    def __init__(self, machine, name, base):
        super().__init__(machine, name, base)
        self.tx_log = bytearray()
        self.rx_byte = 0

    def read_word(self, off):
        if off == self.SR:
            return self.SR_RXNE | self.SR_TXE
        if off == self.DR:
            return self.rx_byte
        return self.get(off)

    def write(self, off, size, value):
        base = off & ~3
        if base == self.DR:
            self.tx_log.append(value & 0xFF)
            self.machine.on_spi_tx(self.name, value & 0xFF)
            return
        super().write(off, size, value)


class I2C(Peripheral):
    CR1 = 0x00
    CR2 = 0x04
    OAR1 = 0x08
    OAR2 = 0x0C
    DR = 0x10
    SR1 = 0x14
    SR2 = 0x18
    CCR = 0x1C
    TRISE = 0x20

    SR1_SB = 1 << 0
    SR1_ADDR = 1 << 1
    SR1_BTF = 1 << 2
    SR1_TXE = 1 << 7
    SR1_RXNE = 1 << 6

    def __init__(self, machine, name, base):
        super().__init__(machine, name, base)
        self.rx_byte = 0
        self.started = False
        self.addressed = False

    def read_word(self, off):
        if off == self.SR1:
            v = self.SR1_TXE | self.SR1_BTF
            if self.started and not self.addressed:
                v |= self.SR1_SB
            if self.addressed:
                v |= self.SR1_ADDR | self.SR1_RXNE
            return v
        if off == self.SR2:
            self.addressed = False
            self.started = False
            return 0
        if off == self.DR:
            return self.rx_byte
        return self.get(off)

    def write_word(self, off, val):
        if off == self.CR1:
            if val & (1 << 8):          # START
                self.started = True
                self.addressed = False
            if val & (1 << 9):          # STOP
                self.started = False
                self.addressed = False
            self.put(off, val)
            return
        if off == self.DR:
            # writing an address byte -> become addressed
            if self.started and not self.addressed:
                self.addressed = True
            return
        self.put(off, val)


class ADC(Peripheral):
    SR = 0x00
    CR1 = 0x04
    CR2 = 0x08
    SMPR1 = 0x0C
    SMPR2 = 0x10
    SQR1 = 0x2C
    SQR2 = 0x30
    SQR3 = 0x34
    DR = 0x4C

    SR_EOC = 1 << 1
    CR2_ADON = 1 << 0
    CR2_SWSTART = 1 << 30

    def __init__(self, machine, name, base):
        super().__init__(machine, name, base)
        self.dr_value = 0x0800
        self.converted = False

    def read_word(self, off):
        if off == self.SR:
            return self.SR_EOC if self.converted else 0
        if off == self.DR:
            self.converted = False
            return self.dr_value
        return self.get(off)

    def write_word(self, off, val):
        if off == self.CR2:
            self.put(off, val)
            if (val & self.CR2_ADON) and (val & self.CR2_SWSTART):
                self.converted = True
            return
        if off == self.SQR3:
            # channel select -> fake a value dependent on channel
            ch = val & 0x1F
            self.dr_value = 0x0800 + ch
        self.put(off, val)
