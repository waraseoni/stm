"""Unicorn-based Cortex-M machine with just enough STM32 peripherals."""

import struct
from collections import deque

from unicorn import (
    Uc,
    UcError,
    UC_ARCH_ARM,
    UC_HOOK_CODE,
    UC_HOOK_INTR,
    UC_HOOK_MEM_READ,
    UC_HOOK_MEM_WRITE,
    UC_MODE_MCLASS,
    UC_MODE_THUMB,
)
from unicorn.arm_const import (
    UC_ARM_REG_CONTROL,
    UC_ARM_REG_LR,
    UC_ARM_REG_PC,
    UC_ARM_REG_PRIMASK,
    UC_ARM_REG_R0,
    UC_ARM_REG_R1,
    UC_ARM_REG_R2,
    UC_ARM_REG_R3,
    UC_ARM_REG_R12,
    UC_ARM_REG_SP,
    UC_ARM_REG_XPSR,
)

from .boards import get_board
from .elf import ElfImage
from .registers import (ADC, DMA, EXTI, FlashReg, GPIO, I2C, PWR, RCC_F1, RCC_F4,
                        SPI, SYSCFG, TIM, USART, SysTick)

PERIPH_BASE = 0x40000000
PERIPH_SIZE = 0x00030000
PPB_BASE = 0xE0000000
PPB_SIZE = 0x00010000

SYSTICK_BASE = 0xE000E010
NVIC_ISER = 0xE000E100
NVIC_ICER = 0xE000E180
NVIC_ISPR = 0xE000E200
NVIC_ICPR = 0xE000E280
NVIC_IPR = 0xE000E400
SCB_BASE = 0xE000ED00
VTOR_OFF = 0x08

SYSTICK_IRQ = 15


class MachineError(RuntimeError):
    pass


class Machine:
    def __init__(self, board="f411re", trace=True):
        self.board = get_board(board)
        self.trace_enabled = trace
        self.trace_log = []

        self.uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        self._map_regions()

        self.icount = 0
        self.halted = False
        self.stop_reason = ""
        self.in_exception = False
        self.exc_sp = 0
        self._inject = False
        self._ret = False
        self.pending = set()
        self.nvic_enabled = 0
        self.nvic_priorities = {}
        self.vtor = self.board.flash_base

        self.uart = bytearray()
        self.led_events = deque(maxlen=20000)
        self.led_state = 0
        self.pwm_events = deque(maxlen=4096)
        self.pin_events = deque(maxlen=20000)
        self.stop_events = deque(maxlen=64)

        self._make_peripherals()
        self.systick_enabled = False
        self.systick_tickint = False
        self.tick_period = 0
        self.next_tick = 0

        self.tramp = (self.board.flash_end - 4) & ~1
        self.uc.mem_write(self.tramp, b"\xfe\xe7")     # b .

        self._hooks()

        self._image = []
        self._entry = 0
        self._sp = 0
        self.symbols = {}

    # -- setup ---------------------------------------------------------
    def _map_regions(self):
        b = self.board
        self.uc.mem_map(b.flash_base, b.flash_size)
        self.uc.mem_map(b.ram_base, b.ram_size)
        self.uc.mem_map(PERIPH_BASE, PERIPH_SIZE)
        self.uc.mem_map(PPB_BASE, PPB_SIZE)

    def _make_peripherals(self):
        b = self.board
        self.rcc = (RCC_F4 if b.rcc_kind == "f4" else RCC_F1)(self, b.rcc_base)
        self.pwr = PWR(self, b.pwr_base) if b.rcc_kind == "f4" else None
        self.flashreg = FlashReg(self, "FLASH", b.flash_reg_base)
        self.gpio = {
            name: GPIO(self, "GPIO" + name, base, b.rcc_kind)
            for name, base in b.gpio_ports.items()
        }
        self.usart = USART(self, b.usart_name, b.usart_base, b.usart_irq)
        self.tim = TIM(self, "TIM2", b.tim_base)
        self.tim2 = self.tim
        self.tim3 = TIM(self, "TIM3", b.tim_base + 0x0400)
        self.tim4 = TIM(self, "TIM4", b.tim_base + 0x0800)
        self.tim5 = TIM(self, "TIM5", b.tim_base + 0x0C00)
        self.systick = SysTick()
        if b.rcc_kind == "f4":
            self.syscfg = SYSCFG(self, "SYSCFG", 0x40013800)
            self.exti = EXTI(self, "EXTI", 0x40013C00, self.syscfg)
            self.dma1 = DMA(self, "DMA1", 0x40026000)
            self.dma2 = DMA(self, "DMA2", 0x40026400)
        else:
            self.syscfg = None
            self.exti = None
            self.dma1 = None
            self.dma2 = None
        self.spi = SPI(self, "SPI1", 0x40013000)
        self.i2c = I2C(self, "I2C1", 0x40005400)
        self.adc = ADC(self, "ADC1", 0x40012000)
        self.reset_button_state()

    def _hooks(self):
        self.uc.hook_add(
            UC_HOOK_MEM_READ, self._hook_read,
            begin=PERIPH_BASE, end=PERIPH_BASE + PERIPH_SIZE,
        )
        self.uc.hook_add(
            UC_HOOK_MEM_WRITE, self._hook_write,
            begin=PERIPH_BASE, end=PERIPH_BASE + PERIPH_SIZE,
        )
        self.uc.hook_add(
            UC_HOOK_MEM_READ, self._hook_read,
            begin=PPB_BASE, end=PPB_BASE + PPB_SIZE,
        )
        self.uc.hook_add(
            UC_HOOK_MEM_WRITE, self._hook_write,
            begin=PPB_BASE, end=PPB_BASE + PPB_SIZE,
        )
        self.uc.hook_add(UC_HOOK_CODE, self._hook_code, begin=self.tramp, end=self.tramp + 2)
        self.uc.hook_add(UC_HOOK_INTR, self._hook_intr)

    # -- loading -------------------------------------------------------
    def load_elf(self, path):
        image = ElfImage(path)
        self._image = list(image.segments)
        self._entry = image.entry & ~1
        self.symbols = dict(image.symbols)
        self._load_segments()
        sp = self.read_u32(self.board.flash_base)
        if sp == 0 or sp == 0xFFFFFFFF:
            sp = self.board.ram_end
        self._sp = sp
        self._reset_cpu()
        return image

    def load_raw(self, segments, entry, sp=None, symbols=None):
        """segments: list of (address, bytes); used by the self-test."""
        self._image = [(a, bytes(d)) for a, d in segments]
        self._entry = entry & ~1
        self.symbols = dict(symbols or {})
        self._load_segments()
        self._sp = sp if sp is not None else self.board.ram_end
        self._reset_cpu()

    def _load_segments(self):
        b = self.board
        for addr, data in self._image:
            end = addr + len(data)
            inside = (
                (b.flash_base <= addr and end <= b.flash_end)
                or (b.ram_base <= addr and end <= b.ram_end)
            )
            if not inside:
                raise MachineError(
                    "ELF segment 0x%08x..0x%08x board memory ke bahar hai" % (addr, end)
                )
            self.uc.mem_write(addr, data)

    def _reset_cpu(self):
        self.uc.reg_write(UC_ARM_REG_SP, self._sp)
        self.uc.reg_write(UC_ARM_REG_PC, self._entry | 1)
        self.uc.reg_write(UC_ARM_REG_XPSR, 0x01000000)
        self.uc.reg_write(UC_ARM_REG_LR, 0xFFFFFFFF)
        self.uc.reg_write(UC_ARM_REG_CONTROL, 0)
        self.uc.reg_write(UC_ARM_REG_PRIMASK, 0)
        self.vtor = self.board.flash_base

    def reset(self):
        """Reload the ELF image and put the CPU back at reset state."""
        self.icount = 0
        self.halted = False
        self.stop_reason = ""
        self.in_exception = False
        self.exc_sp = 0
        self._inject = False
        self._ret = False
        self.pending.clear()
        self.nvic_enabled = 0
        self.nvic_priorities.clear()
        self.uart.clear()
        self.led_events.clear()
        self.led_state = 0
        self.pwm_events.clear()
        self.pin_events.clear()
        self.stop_events.clear()
        self._make_peripherals()
        self.systick_enabled = False
        self.systick_tickint = False
        self.tick_period = 0
        self.next_tick = 0
        # clear RAM then re-apply the loaded image (flash is overwritten by it)
        self.uc.mem_write(self.board.ram_base, b"\x00" * self.board.ram_size)
        self._load_segments()
        self.uc.mem_write(self.tramp, b"\xfe\xe7")     # b .
        self._reset_cpu()

    # -- memory / registers -------------------------------------------
    def read(self, addr, size):
        return int.from_bytes(self.uc.mem_read(addr, size), "little")

    read_u32 = lambda self, addr: self.read(addr, 4)

    def write(self, addr, size, value):
        self.uc.mem_write(addr, int(value).to_bytes(size, "little", signed=False))

    def write_u32(self, addr, value):
        self.write(addr, 4, value)

    def peek(self, addr, size=4):
        """Read through the peripheral model (session/CLI use this)."""
        v = self._read_peripheral(addr, size)
        if v is None:
            v = self.read(addr, size)
        return v

    def poke(self, addr, size, value):
        """Write through the peripheral model + backing memory."""
        value &= (1 << (8 * size)) - 1
        self._write_peripheral(addr, size, value)
        self.write(addr, size, value)

    def reg_read(self, reg):
        return self.uc.reg_read(reg)

    def reg_write(self, reg, value):
        self.uc.reg_write(reg, value)

    def symbol(self, name):
        return self.symbols.get(name)

    @property
    def core_hz(self):
        addr = self.symbols.get("SystemCoreClock")
        if addr:
            try:
                v = self.read_u32(addr)
            except UcError:
                return self.board.default_cpu_hz
            if 1_000_000 <= v <= 1_000_000_000:
                return v
        return self.board.default_cpu_hz

    # -- peripheral dispatch ------------------------------------------
    def _find_peripheral(self, addr):
        for dev in (self.rcc, self.pwr, self.flashreg, self.usart, self.tim,
                    self.tim2, self.tim3, self.tim4, self.tim5, self.syscfg,
                    self.exti, self.dma1, self.dma2, self.spi, self.i2c,
                    self.adc, *self.gpio.values()):
            if dev is not None and dev.base <= addr < dev.base + 0x400:
                return dev
        return None

    def _read_peripheral(self, addr, size):
        if PPB_BASE <= addr < PPB_BASE + PPB_SIZE:
            return self._read_ppb(addr, size)
        dev = self._find_peripheral(addr)
        if dev is None:
            return None
        return dev.read(addr - dev.base, size)

    def _write_peripheral(self, addr, size, value):
        if PPB_BASE <= addr < PPB_BASE + PPB_SIZE:
            self._write_ppb(addr, size, value)
            return
        dev = self._find_peripheral(addr)
        if dev is not None:
            dev.write(addr - dev.base, size, value)

    def _read_ppb(self, addr, size):
        if SYSTICK_BASE <= addr < SYSTICK_BASE + 0x10:
            return self.systick.read(addr - SYSTICK_BASE, size)
        if NVIC_ISER <= addr < NVIC_ISER + 0x80:
            idx = (addr - NVIC_ISER) // 4
            return (self.nvic_enabled >> (32 * idx)) & 0xFFFFFFFF
        if NVIC_ICER <= addr < NVIC_ICER + 0x80:
            return 0
        if NVIC_ISPR <= addr < NVIC_ISPR + 0x80:
            idx = (addr - NVIC_ISPR) // 4
            bits = 0
            for irq in self.pending:
                if irq // 32 == idx:
                    bits |= 1 << (irq % 32)
            return bits
        if NVIC_ICPR <= addr < NVIC_ICPR + 0x80:
            return 0
        if NVIC_IPR <= addr < NVIC_IPR + 0x400:
            return 0
        if SCB_BASE <= addr < SCB_BASE + 0x100:
            off = addr - SCB_BASE
            if off == VTOR_OFF:
                return self.vtor
            if off == 0x00:
                return 0x410FC241 if self.board.core == "cortex-m4" else 0x410FC231
            return 0
        return None

    def _write_ppb(self, addr, size, value):
        if SYSTICK_BASE <= addr < SYSTICK_BASE + 0x10:
            off = addr - SYSTICK_BASE
            self.systick.write(off, size, value)
            if off == SysTick.CTRL:
                self._update_systick()
            elif off == SysTick.VAL:
                self.next_tick = self.icount + max(1, self.tick_period)
            return
        if NVIC_ISER <= addr < NVIC_ICER:
            idx = (addr - NVIC_ISER) // 4
            self.nvic_enabled |= (value & 0xFFFFFFFF) << (32 * idx)
            return
        if NVIC_ICER <= addr < NVIC_ISPR:
            idx = (addr - NVIC_ICER) // 4
            self.nvic_enabled &= ~((value & 0xFFFFFFFF) << (32 * idx))
            return
        if NVIC_ISPR <= addr < NVIC_ICPR:
            idx = (addr - NVIC_ISPR) // 4
            for bit in range(32):
                if value & (1 << bit):
                    irq = idx * 32 + bit
                    if irq != SYSTICK_IRQ:
                        self.pending.add(irq)
            return
        if NVIC_ICPR <= addr < NVIC_IPR:
            idx = (addr - NVIC_ICPR) // 4
            for bit in range(32):
                if value & (1 << bit):
                    self.pending.discard(idx * 32 + bit)
            return
        if NVIC_IPR <= addr < NVIC_IPR + 0x400:
            self.nvic_priorities[addr - NVIC_IPR] = value & 0xFF
            return
        if SCB_BASE <= addr < SCB_BASE + 0x100:
            if addr - SCB_BASE == VTOR_OFF:
                self.vtor = value & 0xFFFFFF80
            return

    # -- hooks ---------------------------------------------------------
    def _hook_read(self, uc, access, address, size, value, user):
        v = self._read_peripheral(address, size)
        if v is not None:
            uc.mem_write(address, int(v).to_bytes(size, "little"))

    def _hook_write(self, uc, access, address, size, value, user):
        self._write_peripheral(address, size, value)

    def _hook_code(self, uc, address, size, user):
        if address == self.tramp:
            self._ret = True
            uc.emu_stop()

    def _hook_intr(self, uc, intno, user):
        self.stop_events.append(("cpu-exception", intno, self.icount))
        self.stop_reason = "CPU exception/IRQ %d (icount=%d)" % (intno, self.icount)
        self.halted = True
        uc.emu_stop()

    # -- external events ----------------------------------------------
    def on_pins_changed(self, port, changed, odr):
        self.pin_events.append((self.icount, port, changed, odr))
        b = self.board
        if port in (b.led_port, "GPIO" + b.led_port) and (changed & (1 << b.led_pin)):
            raw = (odr >> b.led_pin) & 1
            logical = (0 if raw else 1) if b.led_active_low else raw
            self.led_state = logical
            self.led_events.append((self.icount, logical))

    def on_uart_tx(self, byte):
        self.uart.append(byte & 0xFF)
        if len(self.uart) > 1_000_000:
            del self.uart[:-500_000]

    def on_pwm_ccr(self, value):
        self.pwm_events.append((self.icount, value))

    def on_spi_tx(self, name, byte):
        # placeholder hook for future tracing
        pass

    def raise_irq(self, irq):
        self.pending.add(irq)

    def inject_uart_rx(self, byte):
        self.usart.inject_rx(byte)

    def set_button(self, pressed):
        b = self.board
        g = self.gpio.get(b.button_port)
        if g is None:
            return
        old = (g.idr >> b.button_pin) & 1
        level = (0 if pressed else 1) if b.button_active_low else int(bool(pressed))
        if level:
            g.idr |= 1 << b.button_pin
        else:
            g.idr &= ~(1 << b.button_pin)
        new = (g.idr >> b.button_pin) & 1
        if new != old:
            self.on_gpio_input_changed(b.button_port, b.button_pin, new == 1)

    def on_gpio_input_changed(self, port, pin, rising):
        if getattr(self, "exti", None) is None:
            return
        port_index = ord(port) - ord("A")
        self.exti.trigger_from_gpio(port_index, pin, rising)

    def raise_exti(self, line):
        if getattr(self, "exti", None) is None:
            return
        self.pending.add(self.exti.irq_for_line(line))

    def reset_button_state(self):
        b = self.board
        g = self.gpio.get(b.button_port) if hasattr(self, "gpio") else None
        if g is not None:
            if not b.button_active_low:
                g.idr &= ~(1 << b.button_pin)
            else:
                g.idr |= 1 << b.button_pin

    # -- run loop ------------------------------------------------------
    def _update_systick(self):
        ctrl = self.systick.get(SysTick.CTRL)
        load = self.systick.get(SysTick.LOAD)
        self.systick_enabled = bool(ctrl & SysTick.CTRL_ENABLE)
        self.systick_tickint = bool(ctrl & SysTick.CTRL_TICKINT)
        self.tick_period = (load + 1) & 0xFFFFFFFF
        if self.tick_period <= 0:
            self.tick_period = 1
        self.next_tick = self.icount + self.tick_period

    def _check_tick(self):
        if not self.systick_enabled:
            return
        while self.icount >= self.next_tick:
            self.systick.countflag = True
            if self.systick_tickint:
                self.pending.add(SYSTICK_IRQ)
            self.next_tick += self.tick_period
            if self.next_tick <= self.icount:
                self.next_tick = self.icount + self.tick_period

    def _irq_allowed(self, irq):
        if irq == SYSTICK_IRQ:
            return True
        return bool(self.nvic_enabled & (1 << irq))

    def _inject_irq(self):
        candidates = [i for i in self.pending if self._irq_allowed(i)]
        if not candidates:
            # IRQs stay pending in the NVIC until the firmware enables them.
            return
        # Lower numeric priority = higher urgency (Cortex-M convention).
        # Ties broken by IRQ number.
        irq = min(candidates, key=lambda i: (self.nvic_priorities.get(i, 0), i))
        self.pending.discard(irq)
        vector = self.read_u32(self.vtor + 4 * irq)
        if vector in (0, 0xFFFFFFFF):
            raise MachineError(
                "IRQ %d ka vector 0x%08x par 0 hai (VTOR=0x%08x)"
                % (irq, self.vtor + 4 * irq, self.vtor)
            )
        frame = [
            self.uc.reg_read(UC_ARM_REG_R0),
            self.uc.reg_read(UC_ARM_REG_R1),
            self.uc.reg_read(UC_ARM_REG_R2),
            self.uc.reg_read(UC_ARM_REG_R3),
            self.uc.reg_read(UC_ARM_REG_R12),
            self.uc.reg_read(UC_ARM_REG_LR),
            self.uc.reg_read(UC_ARM_REG_PC) & ~1,
            self.uc.reg_read(UC_ARM_REG_XPSR),
        ]
        sp = (self.uc.reg_read(UC_ARM_REG_SP) - 32) & 0xFFFFFFFF
        self.uc.mem_write(sp, struct.pack("<8I", *frame))
        self.uc.reg_write(UC_ARM_REG_SP, sp)
        self.uc.reg_write(UC_ARM_REG_LR, self.tramp | 1)
        self.uc.reg_write(UC_ARM_REG_PC, (vector | 1) & 0xFFFFFFFF)
        self.uc.reg_write(UC_ARM_REG_XPSR, 0x01000000 | (16 + irq))
        self.in_exception = True
        self.exc_sp = sp

    def _exception_return(self):
        frame = struct.unpack("<8I", self.uc.mem_read(self.exc_sp, 32))
        (
            r0, r1, r2, r3, r12, lr, pc, xpsr,
        ) = frame
        self.uc.reg_write(UC_ARM_REG_R0, r0)
        self.uc.reg_write(UC_ARM_REG_R1, r1)
        self.uc.reg_write(UC_ARM_REG_R2, r2)
        self.uc.reg_write(UC_ARM_REG_R3, r3)
        self.uc.reg_write(UC_ARM_REG_R12, r12)
        self.uc.reg_write(UC_ARM_REG_LR, lr)
        self.uc.reg_write(UC_ARM_REG_XPSR, xpsr)
        self.uc.reg_write(UC_ARM_REG_SP, (self.exc_sp + 32) & 0xFFFFFFFF)
        self.uc.reg_write(UC_ARM_REG_PC, pc | 1)
        self.in_exception = False
        self.exc_sp = 0
        self._ret = False

    def run_instructions(self, count):
        target = self.icount + max(0, int(count))
        self._pump(target)

    def run_ms(self, ms):
        # Time model: one instruction ~ one core clock cycle at core_hz.
        per_ms = max(1, int(self.core_hz // 1000))
        self._pump(self.icount + int(ms * per_ms))

    def run_seconds(self, seconds):
        self.run_ms(seconds * 1000.0)

    def _pump(self, target):
        while self.icount < target and not self.halted:
            if self._ret:
                self._exception_return()
            if self._inject:
                self._inject = False
                self._inject_irq()
            self._check_tick()
            if (
                self.pending
                and not self.in_exception
                and not (self.uc.reg_read(UC_ARM_REG_PRIMASK) & 1)
                and any(self._irq_allowed(i) for i in self.pending)
            ):
                self._inject = True
                continue

            chunk = min(256, target - self.icount)
            if self.systick_enabled:
                gap = self.next_tick - self.icount
                if 0 < gap < chunk:
                    chunk = gap
            if chunk <= 0:
                break
            pc = self.uc.reg_read(UC_ARM_REG_PC)
            if self.trace_enabled:
                self.trace_log.append(pc & ~1)
                if len(self.trace_log) > 200000:
                    del self.trace_log[:100000]
            try:
                self.uc.emu_start((pc & ~1) | 1, 0, count=chunk)
            except UcError as exc:
                self.halted = True
                self.stop_reason = "CPU error: %s (pc=0x%08x, icount=%d)" % (
                    exc, pc, self.icount,
                )
                return
            self.icount += chunk

    # -- reporting -----------------------------------------------------
    @property
    def uart_text(self):
        return bytes(self.uart).decode("utf-8", errors="replace")

    def pc(self):
        return self.uc.reg_read(UC_ARM_REG_PC)

    def dump_trace(self, path):
        with open(path, "w", encoding="utf-8") as fh:
            for pc in self.trace_log:
                fh.write("0x%08x\\n" % pc)
        return len(self.trace_log)

    def clear_trace(self):
        self.trace_log.clear()

    # ---- snapshot / restore ----
    def save_snapshot(self, path):
        import base64, pickle
        regmap = {
            "r0": UC_ARM_REG_R0, "r1": UC_ARM_REG_R1, "r2": UC_ARM_REG_R2,
            "r3": UC_ARM_REG_R3, "r12": UC_ARM_REG_R12, "sp": UC_ARM_REG_SP,
            "lr": UC_ARM_REG_LR, "pc": UC_ARM_REG_PC, "xpsr": UC_ARM_REG_XPSR,
            "primask": UC_ARM_REG_PRIMASK, "control": UC_ARM_REG_CONTROL,
        }
        regs = {name: self.uc.reg_read(reg) for name, reg in regmap.items()}

        def dev_state(dev):
            if dev is None:
                return None
            st = {"words": dict(getattr(dev, "_words", {}))}
            for attr in ("odr", "prev_odr", "idr", "rx_byte", "rx_pending",
                         "tx_bytes", "ccr1_history", "dr_value", "converted",
                         "countflag"):
                if hasattr(dev, attr):
                    v = getattr(dev, attr)
                    if isinstance(v, (bytearray, bytes)):
                        v = list(v)
                    if isinstance(v, deque):
                        v = list(v)
                    st[attr] = v
            return st

        gpio_state = {name: dev_state(dev) for name, dev in self.gpio.items()}
        periph_state = {}
        for attr in ("rcc", "pwr", "flashreg", "usart", "tim", "tim2", "tim3",
                     "tim4", "tim5", "syscfg", "exti", "dma1", "dma2", "spi",
                     "i2c", "adc"):
            dev = getattr(self, attr, None)
            if dev is not None:
                periph_state[attr] = dev_state(dev)
        # systick is a RegFile, not a Peripheral
        periph_state["systick"] = {"words": dict(self.systick._words)}

        data = {
            "board": self.board.name,
            "trace_enabled": self.trace_enabled,
            "icount": self.icount,
            "entry": self._entry,
            "sp": self._sp,
            "symbols": dict(self.symbols),
            "image": [(a, base64.b64encode(d).decode()) for a, d in self._image],
            "ram": base64.b64encode(self.uc.mem_read(self.board.ram_base, self.board.ram_size)).decode(),
            "regs": regs,
            "pending": sorted(self.pending),
            "nvic_enabled": self.nvic_enabled,
            "nvic_priorities": dict(self.nvic_priorities),
            "vtor": self.vtor,
            "uart": base64.b64encode(bytes(self.uart)).decode(),
            "led_state": self.led_state,
            "led_events": list(self.led_events),
            "pwm_events": list(self.pwm_events),
            "pin_events": list(self.pin_events),
            "next_tick": self.next_tick,
            "tick_period": self.tick_period,
            "systick_enabled": self.systick_enabled,
            "systick_tickint": self.systick_tickint,
            "trace_log": list(self.trace_log),
            "periph_state": periph_state,
            "gpio_state": gpio_state,
        }
        with open(path, "wb") as fh:
            pickle.dump(data, fh)
        return path

    def load_snapshot(self, path):
        import base64, pickle
        with open(path, "rb") as fh:
            data = pickle.load(fh)

        # rebuild machine from scratch
        self.__init__(data["board"], data.get("trace_enabled", self.trace_enabled))
        self._image = [(a, base64.b64decode(d)) for a, d in data["image"]]
        self._entry = data["entry"]
        self.symbols = dict(data["symbols"])
        self._sp = data["sp"]
        self._load_segments()
        if "ram" in data:
            self.uc.mem_write(self.board.ram_base, base64.b64decode(data["ram"]))

        regmap = {
            "r0": UC_ARM_REG_R0, "r1": UC_ARM_REG_R1, "r2": UC_ARM_REG_R2,
            "r3": UC_ARM_REG_R3, "r12": UC_ARM_REG_R12, "sp": UC_ARM_REG_SP,
            "lr": UC_ARM_REG_LR, "pc": UC_ARM_REG_PC, "xpsr": UC_ARM_REG_XPSR,
            "primask": UC_ARM_REG_PRIMASK, "control": UC_ARM_REG_CONTROL,
        }
        for name, val in data["regs"].items():
            if name in regmap:
                self.uc.reg_write(regmap[name], val)

        self.icount = data["icount"]
        self.pending = set(data["pending"])
        self.nvic_enabled = data["nvic_enabled"]
        self.nvic_priorities = dict(data["nvic_priorities"])
        self.vtor = data["vtor"]
        self.uart = bytearray(base64.b64decode(data["uart"]))
        self.led_state = data["led_state"]
        from collections import deque
        self.led_events = deque(data["led_events"], maxlen=20000)
        self.pwm_events = deque(data["pwm_events"], maxlen=4096)
        self.pin_events = deque(data["pin_events"], maxlen=20000)
        self.next_tick = data["next_tick"]
        self.tick_period = data["tick_period"]
        self.systick_enabled = data["systick_enabled"]
        self.systick_tickint = data["systick_tickint"]
        self.trace_log = list(data.get("trace_log", []))
        self.trace_enabled = data.get("trace_enabled", self.trace_enabled)

        # restore peripherals
        ps = data.get("periph_state", {})
        for attr, st in ps.items():
            dev = getattr(self, attr, None)
            if dev is None or st is None:
                continue
            if hasattr(dev, "_words"):
                dev._words.clear()
                dev._words.update(st.get("words", {}))
            for a in ("odr", "prev_odr", "idr", "rx_byte", "rx_pending",
                      "dr_value", "converted", "countflag"):
                if a in st and hasattr(dev, a):
                    v = st[a]
                    if a == "tx_bytes" and isinstance(v, list):
                        v = bytearray(v)
                    if a == "ccr1_history" and isinstance(v, list):
                        v = list(v)
                    setattr(dev, a, v)
            if attr == "usart" and "tx_bytes" in st:
                dev.tx_bytes = bytearray(st["tx_bytes"])
            if attr == "tim" or attr.startswith("tim"):
                if "ccr1_history" in st:
                    dev.ccr1_history = list(st["ccr1_history"])
        # gpio
        for port, st in data.get("gpio_state", {}).items():
            dev = self.gpio.get(port)
            if dev is None or st is None:
                continue
            dev._words.clear()
            dev._words.update(st.get("words", {}))
            for a in ("odr", "prev_odr", "idr"):
                if a in st:
                    setattr(dev, a, st[a])
        return path

    def registers(self):
        names = {
            "r0": UC_ARM_REG_R0, "r1": UC_ARM_REG_R1, "r2": UC_ARM_REG_R2,
            "r3": UC_ARM_REG_R3, "r12": UC_ARM_REG_R12, "sp": UC_ARM_REG_SP,
            "lr": UC_ARM_REG_LR, "pc": UC_ARM_REG_PC, "xpsr": UC_ARM_REG_XPSR,
            "primask": UC_ARM_REG_PRIMASK, "control": UC_ARM_REG_CONTROL,
        }
        return {name: self.uc.reg_read(reg) for name, reg in names.items()}

    def summary(self):
        b = self.board
        return {
            "board": b.name,
            "icount": self.icount,
            "pc": self.pc(),
            "halted": self.halted,
            "stop_reason": self.stop_reason,
            "core_hz": self.core_hz,
            "uart": self.uart_text,
            "led_pin": "%s%d" % (b.led_port, b.led_pin),
            "led_state": self.led_state,
            "led_toggles": len(self.led_events),
            "pwm_updates": len(self.pwm_events),
            "pwm_duty": round(self.tim.duty(), 4),
            "pending_irq": sorted(self.pending),
        }
