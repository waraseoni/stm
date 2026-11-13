"""Tkinter GUI for stmlab - click-and-run, no command line needed."""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Make sure the package is importable when launched directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stmlab import mini
from stmlab.boards import BOARDS, get_board
from stmlab.ic import IcError, Stm8FlashBackend, make_backend
from stmlab.machine import Machine, MachineError


class BusyMixin:
    def run_busy(self, fn, on_done=None):
        """Run fn() in a worker thread; disable/enable self.busy_widgets."""
        for w in getattr(self, "busy_widgets", []):
            w.config(state="disabled")
        self.status_var.set("Busy...")

        def worker():
            try:
                result = fn()
                self.root.after(0, lambda: self._done(result, on_done))
            except Exception as exc:  # noqa: BLE001
                self.root.after(0, lambda: self._fail(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _done(self, result, on_done):
        for w in getattr(self, "busy_widgets", []):
            w.config(state="normal")
        self.status_var.set("Ready")
        if on_done is not None:
            on_done(result)

    def _fail(self, exc):
        for w in getattr(self, "busy_widgets", []):
            w.config(state="normal")
        self.status_var.set("Error: %s" % exc)
        messagebox.showerror("stmlab", str(exc))


class SimTab(BusyMixin):
    def __init__(self, root, notebook, status_var):
        self.root = root
        self.status_var = status_var
        self.frame = ttk.Frame(notebook, padding=10)
        notebook.add(self.frame, text="Simulator")

        self.machine = None
        self.board_name = tk.StringVar(value="f411re")
        self.elf_path = tk.StringVar()
        self.run_ms = tk.StringVar(value="200")
        self.step_n = tk.StringVar(value="1000")
        self.peek_addr = tk.StringVar(value="0x40023800")
        self.peek_size = tk.StringVar(value="4")
        self.poke_addr = tk.StringVar(value="0x40020014")
        self.poke_value = tk.StringVar(value="0x20")
        self.poke_size = tk.StringVar(value="4")

        self.busy_widgets = []

        # ---- board + ELF ----
        row = ttk.Frame(self.frame)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Board:").pack(side="left")
        cb = ttk.Combobox(row, textvariable=self.board_name, values=sorted(BOARDS),
                          state="readonly", width=10)
        cb.pack(side="left", padx=4)
        ttk.Label(row, text="ELF:").pack(side="left", padx=(12, 0))
        ent = ttk.Entry(row, textvariable=self.elf_path, width=46)
        ent.pack(side="left", padx=4, fill="x", expand=True)
        br = ttk.Button(row, text="Browse...", command=self.browse_elf)
        br.pack(side="left")
        self.busy_widgets += [cb, ent, br]

        row2 = ttk.Frame(self.frame)
        row2.pack(fill="x", pady=4)
        load = ttk.Button(row2, text="Load ELF", command=self.load_elf)
        load.pack(side="left")
        demo = ttk.Button(row2, text="Load Demo (no toolchain)", command=self.load_demo)
        demo.pack(side="left", padx=4)
        reset = ttk.Button(row2, text="Reset", command=self.reset_machine)
        reset.pack(side="left", padx=4)
        self.busy_widgets += [load, demo, reset]

        # ---- run controls ----
        row3 = ttk.Frame(self.frame)
        row3.pack(fill="x", pady=4)
        ttk.Label(row3, text="Run (ms):").pack(side="left")
        e = ttk.Entry(row3, textvariable=self.run_ms, width=8)
        e.pack(side="left", padx=4)
        runb = ttk.Button(row3, text="Run", command=self.run_ms)
        runb.pack(side="left")
        ttk.Label(row3, text="Step (instr):").pack(side="left", padx=(12, 0))
        e2 = ttk.Entry(row3, textvariable=self.step_n, width=10)
        e2.pack(side="left", padx=4)
        stepb = ttk.Button(row3, text="Step", command=self.step)
        stepb.pack(side="left")
        self.busy_widgets += [e, e2, runb, stepb]

        # ---- status ----
        status = ttk.LabelFrame(self.frame, text="Status", padding=6)
        status.pack(fill="x", pady=6)
        self.status_text = tk.StringVar(value="No firmware loaded.")
        ttk.Label(status, textvariable=self.status_text, justify="left").pack(anchor="w")

        # ---- UART output ----
        uart = ttk.LabelFrame(self.frame, text="UART output", padding=6)
        uart.pack(fill="both", expand=True, pady=6)
        self.uart_box = tk.Text(uart, height=8, state="disabled", wrap="char")
        self.uart_box.pack(fill="both", expand=True)

        # ---- peek / poke ----
        pp = ttk.LabelFrame(self.frame, text="Memory / registers (peek & poke)", padding=6)
        pp.pack(fill="x", pady=6)
        r = ttk.Frame(pp); r.pack(fill="x", pady=2)
        ttk.Label(r, text="Peek addr:").pack(side="left")
        ttk.Entry(r, textvariable=self.peek_addr, width=12).pack(side="left", padx=4)
        ttk.Label(r, text="size:").pack(side="left")
        ttk.Entry(r, textvariable=self.peek_size, width=4).pack(side="left", padx=4)
        ttk.Button(r, text="Read", command=self.peek).pack(side="left", padx=4)
        self.peek_result = tk.StringVar(value="")
        ttk.Label(r, textvariable=self.peek_result).pack(side="left", padx=8)

        r2 = ttk.Frame(pp); r2.pack(fill="x", pady=2)
        ttk.Label(r2, text="Poke addr:").pack(side="left")
        ttk.Entry(r2, textvariable=self.poke_addr, width=12).pack(side="left", padx=4)
        ttk.Label(r2, text="value:").pack(side="left")
        ttk.Entry(r2, textvariable=self.poke_value, width=12).pack(side="left", padx=4)
        ttk.Label(r2, text="size:").pack(side="left")
        ttk.Entry(r2, textvariable=self.poke_size, width=4).pack(side="left", padx=4)
        ttk.Button(r2, text="Write", command=self.poke).pack(side="left", padx=4)

        # ---- RX inject ----
        r3 = ttk.Frame(pp); r3.pack(fill="x", pady=2)
        self.rx_text = tk.StringVar()
        ttk.Label(r3, text="Inject RX:").pack(side="left")
        ttk.Entry(r3, textvariable=self.rx_text, width=24).pack(side="left", padx=4)
        ttk.Button(r3, text="Send (text)", command=lambda: self.inject_rx(False)).pack(side="left", padx=4)
        ttk.Button(r3, text="Send (hex:)", command=lambda: self.inject_rx(True)).pack(side="left", padx=4)

    # ---- actions ----
    def browse_elf(self):
        path = filedialog.askopenfilename(
            title="Select firmware ELF",
            filetypes=[("ELF files", "*.elf *.axf"), ("All files", "*.*")],
        )
        if path:
            self.elf_path.set(path)

    def _need_machine(self):
        if self.machine is None:
            messagebox.showinfo("stmlab", "Pehle 'Load ELF' ya 'Load Demo' dabao.")
            return False
        return True

    def load_elf(self):
        path = self.elf_path.get().strip()
        if not path or not os.path.isfile(path):
            messagebox.showerror("stmlab", "Valid ELF file select karo.")
            return
        board = self.board_name.get()

        def work():
            m = Machine(board, trace=False)
            m.load_elf(path)
            return m

        self.run_busy(work, on_done=self._set_machine)

    def load_demo(self):
        board = get_board(self.board_name.get())
        segments, entry, symbols = mini.build_demo(board)

        def work():
            m = Machine(board.name, trace=False)
            m.load_raw(segments, entry, sp=board.ram_end, symbols=symbols)
            return m

        self.run_busy(work, on_done=self._set_machine)

    def _set_machine(self, m):
        self.machine = m
        self.refresh_status()
        self.refresh_uart()

    def reset_machine(self):
        if not self._need_machine():
            return
        self.machine.reset()
        self.refresh_status()
        self.refresh_uart()

    def run_ms(self):
        if not self._need_machine():
            return
        try:
            ms = float(self.run_ms.get())
        except ValueError:
            messagebox.showerror("stmlab", "Run (ms) number hona chahiye.")
            return

        def work():
            self.machine.run_ms(ms)
            return None

        self.run_busy(work, on_done=lambda _: self._after_run())

    def step(self):
        if not self._need_machine():
            return
        try:
            n = int(self.step_n.get())
        except ValueError:
            messagebox.showerror("stmlab", "Step count number hona chahiye.")
            return

        def work():
            self.machine.run_instructions(n)
            return None

        self.run_busy(work, on_done=lambda _: self._after_run())

    def _after_run(self):
        self.refresh_status()
        self.refresh_uart()

    def refresh_status(self):
        if self.machine is None:
            self.status_text.set("No firmware loaded.")
            return
        s = self.machine.summary()
        text = (
            "board=%s  icount=%d  pc=0x%08x  clock=%.1f MHz\n"
            "led %s%d = %s   (toggles=%d)   pending_irq=%s\n"
            "halted=%s  %s"
            % (s["board"], s["icount"], s["pc"], s["core_hz"] / 1e6,
               s["led_pin"], "on" if s["led_state"] else "off",
               s["led_toggles"], s["pending_irq"],
               s["halted"], s["stop_reason"])
        )
        self.status_text.set(text)

    def refresh_uart(self):
        self.uart_box.config(state="normal")
        self.uart_box.delete("1.0", "end")
        if self.machine is not None:
            self.uart_box.insert("end", self.machine.uart_text)
        self.uart_box.config(state="disabled")

    def peek(self):
        if not self._need_machine():
            return
        try:
            addr = int(self.peek_addr.get(), 0)
            size = int(self.peek_size.get())
        except ValueError:
            messagebox.showerror("stmlab", "Address/size invalid.")
            return
        try:
            val = self.machine.peek(addr, size)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("stmlab", str(exc))
            return
        self.peek_result.set("0x%0*x" % (size * 2, val))

    def poke(self):
        if not self._need_machine():
            return
        try:
            addr = int(self.poke_addr.get(), 0)
            value = int(self.poke_value.get(), 0)
            size = int(self.poke_size.get())
        except ValueError:
            messagebox.showerror("stmlab", "Address/value/size invalid.")
            return
        try:
            self.machine.poke(addr, size, value)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("stmlab", str(exc))
            return
        self.refresh_status()
        self.refresh_uart()
        messagebox.showinfo("stmlab", "Write done.")

    def inject_rx(self, as_hex):
        if not self._need_machine():
            return
        text = self.rx_text.get()
        if as_hex:
            try:
                data = bytes.fromhex(text.replace(" ", "").replace("0x", ""))
            except ValueError:
                messagebox.showerror("stmlab", "Hex string invalid (e.g. 41 42).")
                return
        else:
            data = text.encode()
        for b in data:
            self.machine.inject_uart_rx(b)
        self.refresh_status()
        self.refresh_uart()


class IcTab(BusyMixin):
    def __init__(self, root, notebook, status_var):
        self.root = root
        self.status_var = status_var
        self.frame = ttk.Frame(notebook, padding=10)
        notebook.add(self.frame, text="IC Read/Write")

        self.backend_name = tk.StringVar(value="sim")
        self.board_name = tk.StringVar(value="f411re")
        self.interface = tk.StringVar(value="interface/stlink.cfg")
        self.target = tk.StringVar(value="target/stm32f4x.cfg")
        self.part = tk.StringVar(value="stm8s103f3")
        self.programmer = tk.StringVar(value="stlinkv2")
        self.exe_path = tk.StringVar()
        self.address = tk.StringVar(value="0x40023800")
        self.count = tk.StringVar(value="1")
        self.size = tk.StringVar(value="4")
        self.value = tk.StringVar(value="0x20")
        self.length = tk.StringVar(value="256")
        self.file_path = tk.StringVar()
        self.elf_path = tk.StringVar()

        self.busy_widgets = []

        # ---- backend ----
        r = ttk.Frame(self.frame); r.pack(fill="x", pady=4)
        ttk.Label(r, text="Backend:").pack(side="left")
        cb = ttk.Combobox(r, textvariable=self.backend_name,
                          values=["sim", "openocd", "stm8flash"], state="readonly", width=12)
        cb.pack(side="left", padx=4)
        ttk.Label(r, text="Board (sim):").pack(side="left", padx=(12, 0))
        cb2 = ttk.Combobox(r, textvariable=self.board_name, values=sorted(BOARDS),
                           state="readonly", width=10)
        cb2.pack(side="left", padx=4)
        ttk.Label(r, text="ELF (sim):").pack(side="left", padx=(12, 0))
        ent = ttk.Entry(r, textvariable=self.elf_path, width=30)
        ent.pack(side="left", padx=4, fill="x", expand=True)
        br = ttk.Button(r, text="Browse", command=self.browse_elf)
        br.pack(side="left")
        self.busy_widgets += [cb, cb2, ent, br]

        # openocd options
        r2 = ttk.LabelFrame(self.frame, text="OpenOCD options (real STM32)", padding=6)
        r2.pack(fill="x", pady=4)
        for label, var in (("Interface:", self.interface), ("Target:", self.target)):
            rr = ttk.Frame(r2); rr.pack(fill="x", pady=2)
            ttk.Label(rr, text=label, width=11).pack(side="left")
            ttk.Entry(rr, textvariable=var, width=40).pack(side="left", padx=4, fill="x", expand=True)
        rr = ttk.Frame(r2); rr.pack(fill="x", pady=2)
        ttk.Label(rr, text="exe path:", width=11).pack(side="left")
        ttk.Entry(rr, textvariable=self.exe_path, width=40).pack(side="left", padx=4, fill="x", expand=True)
        ttk.Button(rr, text="Browse", command=self.browse_exe).pack(side="left")

        # stm8 options
        r3 = ttk.LabelFrame(self.frame, text="STM8 options (real STM8)", padding=6)
        r3.pack(fill="x", pady=4)
        rr = ttk.Frame(r3); rr.pack(fill="x", pady=2)
        ttk.Label(rr, text="Part:", width=11).pack(side="left")
        ttk.Entry(rr, textvariable=self.part, width=16).pack(side="left", padx=4)
        ttk.Label(rr, text="Programmer:").pack(side="left", padx=(12, 0))
        ttk.Entry(rr, textvariable=self.programmer, width=12).pack(side="left", padx=4)

        # address / params
        r4 = ttk.Frame(self.frame); r4.pack(fill="x", pady=4)
        ttk.Label(r4, text="Address:").pack(side="left")
        ttk.Entry(r4, textvariable=self.address, width=12).pack(side="left", padx=4)
        ttk.Label(r4, text="Count:").pack(side="left")
        ttk.Entry(r4, textvariable=self.count, width=6).pack(side="left", padx=4)
        ttk.Label(r4, text="Size:").pack(side="left")
        ttk.Combobox(r4, textvariable=self.size, values=["1", "2", "4"], width=4).pack(side="left", padx=4)
        ttk.Label(r4, text="Value:").pack(side="left", padx=(12, 0))
        ttk.Entry(r4, textvariable=self.value, width=12).pack(side="left", padx=4)
        ttk.Label(r4, text="Length:").pack(side="left", padx=(12, 0))
        ttk.Entry(r4, textvariable=self.length, width=8).pack(side="left", padx=4)

        r5 = ttk.Frame(self.frame); r5.pack(fill="x", pady=4)
        ttk.Label(r5, text="File:").pack(side="left")
        ttk.Entry(r5, textvariable=self.file_path, width=40).pack(side="left", padx=4, fill="x", expand=True)
        ttk.Button(r5, text="Browse", command=self.browse_file).pack(side="left")

        # buttons
        r6 = ttk.Frame(self.frame); r6.pack(fill="x", pady=6)
        for text, cmd in (("Read", self.do_read), ("Write", self.do_write),
                          ("Dump", self.do_dump), ("Load", self.do_load),
                          ("Info", self.do_info), ("Reset", self.do_reset)):
            b = ttk.Button(r6, text=text, command=cmd)
            b.pack(side="left", padx=3)
            self.busy_widgets.append(b)

        # output
        out = ttk.LabelFrame(self.frame, text="Output", padding=6)
        out.pack(fill="both", expand=True, pady=6)
        self.out_box = tk.Text(out, height=14, state="disabled", wrap="char")
        self.out_box.pack(fill="both", expand=True)

    def _args(self):
        import argparse
        ns = argparse.Namespace()
        ns.backend = self.backend_name.get()
        ns.board = self.board_name.get()
        ns.elf = self.elf_path.get().strip() or None
        ns.interface = self.interface.get().strip() or None
        ns.target = self.target.get().strip() or None
        ns.part = self.part.get().strip()
        ns.programmer = self.programmer.get().strip()
        ns.exe = self.exe_path.get().strip() or None
        ns.speed = None
        return ns

    def _backend(self):
        return make_backend(self._args())

    def _log(self, text):
        self.out_box.config(state="normal")
        self.out_box.insert("end", text + "\n")
        self.out_box.see("end")
        self.out_box.config(state="disabled")

    def browse_elf(self):
        p = filedialog.askopenfilename(title="Select ELF", filetypes=[("ELF", "*.elf *.axf"), ("All", "*.*")])
        if p:
            self.elf_path.set(p)

    def browse_exe(self):
        p = filedialog.askopenfilename(title="Select probe tool", filetypes=[("Executable", "*.exe"), ("All", "*.*")])
        if p:
            self.exe_path.set(p)

    def browse_file(self):
        p = filedialog.askopenfilename(title="Select file", filetypes=[("All", "*.*")])
        if p:
            self.file_path.set(p)

    def _int(self, text, default=0):
        text = text.strip()
        if not text:
            return default
        return int(text, 0)

    def do_read(self):
        def work():
            backend = self._backend()
            addr = self._int(self.address.get())
            count = self._int(self.count.get(), 1)
            size = self._int(self.size.get(), 4)
            vals = backend.read(addr, count, size)
            lines = ["0x%08x = 0x%0*x" % (addr + i * size, size * 2, v) for i, v in enumerate(vals)]
            return "\n".join(lines)

        self.run_busy(work, on_done=self._log)

    def do_write(self):
        def work():
            backend = self._backend()
            addr = self._int(self.address.get())
            value = self._int(self.value.get())
            size = self._int(self.size.get(), 4)
            backend.write(addr, value, size)
            return "0x%08x <- 0x%0*x" % (addr, size * 2, value)

        self.run_busy(work, on_done=self._log)

    def do_dump(self):
        def work():
            backend = self._backend()
            addr = self._int(self.address.get())
            length = self._int(self.length.get(), 256)
            path = self.file_path.get().strip()
            if not path:
                raise IcError("File path required for dump.")
            out = backend.dump(addr, length, path)
            return "dumped %d bytes from 0x%08x to %s" % (length, addr, out)

        self.run_busy(work, on_done=self._log)

    def do_load(self):
        def work():
            backend = self._backend()
            path = self.file_path.get().strip()
            if not path or not os.path.isfile(path):
                raise IcError("Valid file required for load.")
            addr = None
            if self.address.get().strip():
                addr = self._int(self.address.get())
            backend.load(path, addr)
            return "loaded %s" % path

        self.run_busy(work, on_done=self._log)

    def do_info(self):
        def work():
            return self._backend().info()

        self.run_busy(work, on_done=self._log)

    def do_reset(self):
        def work():
            backend = self._backend()
            if not hasattr(backend, "reset"):
                raise IcError("%s reset support nahi karta" % backend.name)
            backend.reset()
            return "reset done"

        self.run_busy(work, on_done=self._log)


class StmlabGui:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("stmlab - STM32 Simulator & IC Read/Write")
        self.root.geometry("920x720")
        self.status_var = tk.StringVar(value="Ready")

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=6, pady=6)

        self.sim_tab = SimTab(self.root, notebook, self.status_var)
        self.ic_tab = IcTab(self.root, notebook, self.status_var)

        bar = ttk.Frame(self.root, padding=(6, 2))
        bar.pack(fill="x")
        ttk.Label(bar, textvariable=self.status_var).pack(side="left")

    def run(self):
        self.root.mainloop()


def main():
    app = StmlabGui()
    app.run()


if __name__ == "__main__":
    main()
