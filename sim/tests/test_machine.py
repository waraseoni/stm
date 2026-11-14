"""Self tests for the Unicorn machine and the chip back-ends.

Run from the repository root:

    python -m unittest discover -s sim/tests -t sim -v
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stmlab import mini                                    # noqa: E402
from stmlab.boards import get_board                        # noqa: E402
from stmlab.ic import IcError, SimBackend                  # noqa: E402
from stmlab.machine import Machine                         # noqa: E402


def load(board_name, program):
    board = get_board(board_name)
    segments, entry, symbols = program(board)
    machine = Machine(board_name, trace=False)
    machine.load_raw(segments, entry, sp=board.ram_end, symbols=symbols)
    return machine, board, symbols


class DemoTest(unittest.TestCase):
    def _check_demo(self, board_name, ms=250):
        machine, board, symbols = load(board_name, mini.build_demo)
        machine.run_ms(ms)
        self.assertFalse(machine.halted, machine.stop_reason)
        self.assertIn("Hi from stmlab", machine.uart_text)
        ticks = machine.read(symbols["tick_counter"], 4)
        self.assertGreater(ticks, ms // 2, "SysTick handler nahi chala")
        self.assertGreater(len(machine.led_events), 5, "LED toggle nahi hua")
        # SysTick pending bit handler ke baad khatam hona chahiye
        self.assertNotIn(15, machine.pending)
        return machine

    def test_demo_f411re(self):
        machine = self._check_demo("f411re")
        self.assertIn(machine.registers()["sp"], (
            get_board("f411re").ram_end - 32,
            get_board("f411re").ram_end,
        ))

    def test_demo_f446re(self):
        self._check_demo("f446re")

    def test_demo_f103c8(self):
        self._check_demo("f103c8", ms=200)

    def test_reset_clears_run_state(self):
        machine, board, symbols = load("f411re", mini.build_demo)
        machine.run_ms(50)
        self.assertGreater(machine.icount, 0)
        machine.reset()
        self.assertEqual(machine.icount, 0)
        self.assertEqual(machine.uart_text, "")
        self.assertEqual(machine.read(symbols["tick_counter"], 4), 0)
        self.assertEqual(machine.pc(), board.flash_base + mini.CODE_OFFSET)


class UartRxTest(unittest.TestCase):
    def test_rx_interrupt_echo(self):
        machine, board, symbols = load("f411re", mini.build_uart_echo)
        buf = symbols["rx_buffer"]
        machine.run_ms(5)
        self.assertFalse(machine.halted, machine.stop_reason)

        machine.inject_uart_rx(ord("A"))
        machine.run_ms(5)
        machine.inject_uart_rx(ord("B"))
        machine.run_ms(5)

        self.assertEqual(machine.read(buf, 1), 2, "RX counter update nahi hua")
        self.assertEqual(machine.read(buf + 1, 1), ord("A"))
        self.assertEqual(machine.read(buf + 2, 1), ord("B"))
        self.assertEqual(machine.uart_text, "AB")
        self.assertFalse(machine.usart.rx_pending)

    def test_rx_pending_when_nvic_disabled(self):
        """IRQ pending rehta hai jab tak firmware NVIC me enable na kare."""
        machine, board, symbols = load("f411re", mini.build_uart_echo)
        machine.run_ms(2)
        machine.nvic_enabled = 0                    # firmware ne enable kar diya tha
        machine.inject_uart_rx(ord("Z"))
        self.assertIn(38, machine.pending)
        machine.run_ms(2)
        self.assertIn(38, machine.pending, "disabled IRQ execute ho gaya")
        self.assertEqual(machine.read(symbols["rx_buffer"], 1), 0)

        machine.nvic_enabled |= 1 << 38             # ab enable karo
        machine.run_ms(2)
        self.assertEqual(machine.read(symbols["rx_buffer"], 1), 1)
        self.assertEqual(machine.read(symbols["rx_buffer"] + 1, 1), ord("Z"))


class PeripheralModelTest(unittest.TestCase):
    def test_rcc_ready_flags(self):
        machine = Machine("f411re", trace=False)
        # HSE on -> HSERDY, PLL on -> PLLRDY (firmware ke wait loops ke liye)
        machine.poke(0x40023800, 4, 0x00010000)
        self.assertTrue(machine.peek(0x40023800, 4) & (1 << 17))
        machine.poke(0x40023800, 4, 0x01000000)
        self.assertTrue(machine.peek(0x40023800, 4) & (1 << 25))

    def test_gpio_odr_and_bsrr(self):
        machine = Machine("f411re", trace=False)
        machine.poke(0x40020014, 4, 0x20)             # ODR PA5
        self.assertEqual(machine.peek(0x40020018, 4), 0)  # BSRR reads as 0
        self.assertEqual(machine.led_state, 1)
        machine.poke(0x40020018, 4, 1 << 21)          # BSRR reset PA5
        self.assertEqual(machine.led_state, 0)

    def test_systick_countflag(self):
        machine = Machine("f411re", trace=False)
        # ek `b .` loop chahiye warna CPU 0x00000000 par fetch error deta hai
        machine.load_raw([(0x08000000, b"\xfe\xe7")], 0x08000000)
        machine.poke(0xE000E014, 4, 9)                 # LOAD
        machine.poke(0xE000E018, 4, 0)                 # VAL
        machine.poke(0xE000E010, 4, 5)                 # ENABLE | CLKSOURCE
        machine.run_instructions(100)
        self.assertTrue(machine.peek(0xE000E010, 4) & (1 << 16))
        # COUNTFLAG read par clear ho jata hai
        self.assertFalse(machine.peek(0xE000E010, 4) & (1 << 16))

    def test_pwm_ccr_tracking(self):
        machine = Machine("f411re", trace=False)
        machine.poke(0x4000002C, 4, 999)               # TIM2 ARR
        machine.poke(0x40000034, 4, 250)               # CCR1
        self.assertAlmostEqual(machine.tim.duty(), 0.25, places=3)
        self.assertEqual(machine.pwm_events[-1][1], 250)

    def test_spi_flags_and_tx(self):
        machine = Machine("f411re", trace=False)
        self.assertTrue(machine.peek(0x40013008, 4) & 0x03)   # TXE|RXNE
        machine.poke(0x4001300C, 1, 0x55)
        self.assertEqual(machine.spi.tx_log[-1], 0x55)

    def test_i2c_start_addressed(self):
        machine = Machine("f411re", trace=False)
        machine.poke(0x40005400, 4, 1 << 8)           # CR1 START
        self.assertTrue(machine.peek(0x40005414, 4) & 1)  # SB
        machine.poke(0x40005410, 1, 0x50)             # DR address
        self.assertTrue(machine.peek(0x40005414, 4) & 2)  # ADDR
        machine.peek(0x40005418, 4)                    # read SR2 clears
        self.assertFalse(machine.peek(0x40005414, 4) & 2)

    def test_adc_conversion(self):
        machine = Machine("f411re", trace=False)
        machine.poke(0x40012034, 4, 5)                 # SQR3 channel 5
        machine.poke(0x40012008, 4, (1 << 0) | (1 << 30))  # ADON + SWSTART
        self.assertTrue(machine.peek(0x40012000, 4) & (1 << 1))  # EOC
        self.assertEqual(machine.peek(0x4001204C, 4), 0x0805)

    def test_dma_m2m(self):
        machine = Machine("f411re", trace=False)
        src, dst = 0x20000100, 0x20000200
        for i, v in enumerate([0xA, 0xB, 0xC]):
            machine.poke(src + i * 4, 4, v)
        machine.poke(0x40026018, 4, dst)               # PAR (dest in M2M)
        machine.poke(0x4002601C, 4, src)               # M0AR (src)
        machine.poke(0x40026014, 4, 3)                 # NDTR
        cr = (2 << 6) | (2 << 11) | (2 << 13) | (1 << 4) | 1
        machine.poke(0x40026010, 4, cr)                # CR (EN)
        self.assertEqual([machine.peek(dst + i * 4, 4) for i in range(3)], [0xA, 0xB, 0xC])
        self.assertEqual(machine.peek(0x40026014, 4), 0)
        self.assertTrue(machine.peek(0x40026000, 4) & (1 << 5))

    def test_tim3_duty(self):
        machine = Machine("f411re", trace=False)
        machine.poke(0x4000042C, 4, 199)               # TIM3 ARR
        machine.poke(0x40000434, 4, 50)                # TIM3 CCR1
        self.assertAlmostEqual(machine.tim3.duty(), 0.25, places=2)

    def test_exti_falling_edge_irq(self):
        machine = Machine("f411re", trace=False)
        machine.poke(0x40013C00, 4, 1)                 # EXTI IMR line0
        machine.poke(0x40013C0C, 4, 1)                 # EXTI FTSR line0
        machine.nvic_enabled |= 1 << 6                 # EXTI0_IRQn
        machine.gpio["A"].idr |= 1                     # PA0 high initially
        machine.gpio["A"].idr &= ~1                    # PA0 goes low
        machine.on_gpio_input_changed("A", 0, False)    # falling edge
        self.assertIn(6, machine.pending)
        self.assertTrue(machine.peek(0x40013C14, 4) & 1)  # PR bit0 set


class SimBackendTest(unittest.TestCase):
    def test_read_write_dump_load(self):
        backend = SimBackend("f411re")
        backend.write(0x20000100, 0xDEADBEEF)
        self.assertEqual(backend.read(0x20000100, 2), [0xDEADBEEF, 0])
        backend.write(0x20000104, 0x1234, size=2)
        self.assertEqual(backend.read(0x20000104, 1, size=2), [0x1234])
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "dump.bin")
            backend.dump(0x20000100, 8, path)
            self.assertEqual(os.path.getsize(path), 8)
            backend.write(0x20000100, 0)
            backend.load(path, 0x20000100)
            self.assertEqual(backend.read(0x20000100, 1), [0xDEADBEEF])

    def test_stm8_write_is_rejected(self):
        from stmlab.ic import Stm8FlashBackend

        backend = Stm8FlashBackend.__new__(Stm8FlashBackend)
        with self.assertRaises(IcError):
            backend.write(0x8000, 0)


if __name__ == "__main__":
    unittest.main()
