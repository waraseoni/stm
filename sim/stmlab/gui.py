"""Tkinter GUI for stmlab - click-and-run, no command line needed.

Beginner-friendly: Hardware tab (wiring + port detection), Simulator tab,
IC Read/Write tab. Optional features (serial, modern theme) are feature-gated.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stmlab import mini
from stmlab.boards import BOARDS, get_board
from stmlab.ic import IcError, make_backend
from stmlab.machine import Machine, MachineError

# Optional deps (feature-gated)
try:
    import serial  # noqa: F401
    import serial.tools.list_ports
    HAS_SERIAL = True
except Exception:  # noqa: BLE001
    HAS_SERIAL = False

try:
    import sv_ttk
    HAS_SVTTK = True
except Exception:  # noqa: BLE001
    HAS_SVTTK = False


WIRING = {
    "f411re": """Nucleo-F411RE / F446RE  (onboard ST-Link, no extra wiring for SWD)

SWD: done onboard via USB (CN1 / ST-Link)
printf UART: USART2 on PA2 (TX) / PA3 (RX) @ 115200 8N1
LED: PA5 (LD2, active high)
User button: PC13 (B1, active low)

USB cable: PC <-> Nucleo CN1 (ST-Link)  [debug + power]
Optional: PC <-> Nucleo virtual COM (USART2) for printf
""",
    "f446re": """Nucleo-F446RE  (onboard ST-Link)

SWD: onboard via USB
printf UART: USART2 on PA2 (TX) / PA3 (RX) @ 115200 8N1
LED: PA5 (LD2)
User button: PC13 (B1)
""",
    "f103c8": """Blue Pill (F103C8T6) + ST-Link V2  (external wiring)

ST-Link V2  ->  Blue Pill
  3.3V  --->  3V3
  GND   --->  GND
  SWDIO --->  PA13 (DIO)
  SWCLK --->  PA14 (CLK)
  RST   --->  NRST (optional)

Boot: BOOT0=0 for flash, BOOT0=1 for system bootloader (UART PA9/PA10 @ 115200)
LED: PC13 (active low)
User button: usually PA0 (add your own)
""",
}


class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _event=None):
        if self.tip is not None:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry("+%d+%d" % (x, y))
        lbl = tk.Label(self.tip, text=self.text, background="#ffffe0",
                       relief="solid", borderwidth=1, font=("Segoe UI", 9),
                       justify="left", wraplength=320)
        lbl.pack()

    def hide(self, _event=None):
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


def toast(root, message, kind="info", duration=3000):
    colors = {"info": "#333333", "success": "#1e7e34",
              "warning": "#b7791f", "error": "#c0392b"}
    top = tk.Toplevel(root)
    top.overrideredirect(True)
    top.attributes("-topmost", True)
    lbl = tk.Label(top, text=message, bg=colors.get(kind, "#333333"),
                   fg="white", font=("Segoe UI", 10, "bold"), padx=14, pady=8)
    lbl.pack()
    root.update_idletasks()
    x = root.winfo_rootx() + root.winfo_width() - top.winfo_reqwidth() - 20
    y = root.winfo_rooty() + root.winfo_height() - top.winfo_reqheight() - 40
    top.geometry("+%d+%d" % (x, y))
    top.after(duration, top.destroy)


class BusyMixin:
    def __init__(self):
        self.app = None

    def run_busy(self, fn, on_done=None):
        for w in getattr(self, "busy_widgets", []):
            try:
                w.config(state="disabled")
            except Exception:  # noqa: BLE001
                pass
        self._set_status("Busy...")
        if self.app is not None and getattr(self.app, "progress", None) is not None:
            self.app.progress.start(12)

        def worker():
            try:
                result = fn()
                self.root.after(0, lambda: self._done(result, on_done))
            except Exception as exc:  # noqa: BLE001
                self.root.after(0, lambda: self._fail(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _done(self, result, on_done):
        for w in getattr(self, "busy_widgets", []):
            try:
                w.config(state="normal")
            except Exception:  # noqa: BLE001
                pass
        self._set_status("Ready")
        if self.app is not None and getattr(self.app, "progress", None) is not None:
            self.app.progress.stop()
        if on_done is not None:
            on_done(result)

    def _fail(self, exc):
        for w in getattr(self, "busy_widgets", []):
            try:
                w.config(state="disabled" if False else "normal")
            except Exception:  # noqa: BLE001
                pass
        self._set_status("Error: %s" % exc)
        if self.app is not None and getattr(self.app, "progress", None) is not None:
            self.app.progress.stop()
        messagebox.showerror("stmlab", str(exc))

    def _set_status(self, text):
        if self.app is not None:
            self.app.status_var.set(text)


class SimTab(BusyMixin):
    def __init__(self, root, notebook, app):
        super().__init__()
        self.root = root
        self.app = app
        self.status_var = app.status_var
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
        self.rx_text = tk.StringVar()
        self.bp_text = tk.StringVar()
        self.until_text = tk.StringVar()
        self.trace_var = tk.BooleanVar(value=False)
        self.watches = []

        self.busy_widgets = []

        row = ttk.Frame(self.frame); row.pack(fill="x", pady=4)
        ttk.Label(row, text="Board:").pack(side="left")
        cb = ttk.Combobox(row, textvariable=self.board_name, values=sorted(BOARDS),
                          state="readonly", width=10)
        cb.pack(side="left", padx=4)
        Tooltip(cb, "Target board for the simulator.")
        ttk.Label(row, text="ELF:").pack(side="left", padx=(12, 0))
        ent = ttk.Entry(row, textvariable=self.elf_path, width=46)
        ent.pack(side="left", padx=4, fill="x", expand=True)
        br = ttk.Button(row, text="Browse...", command=self.browse_elf)
        br.pack(side="left")
        self.busy_widgets += [cb, ent, br]

        row2 = ttk.Frame(self.frame); row2.pack(fill="x", pady=4)
        load = ttk.Button(row2, text="Load ELF", command=self.load_elf)
        load.pack(side="left")
        Tooltip(load, "Load a GCC-built firmware ELF into the simulator.")
        demo = ttk.Button(row2, text="Load Demo (no toolchain)", command=self.load_demo)
        demo.pack(side="left", padx=4)
        Tooltip(demo, "Load a hand-assembled demo program (no compiler needed).")
        reset = ttk.Button(row2, text="Reset", command=self.reset_machine)
        reset.pack(side="left", padx=4)
        Tooltip(reset, "Reset CPU + reload the loaded image.")
        self.busy_widgets += [load, demo, reset]

        row3 = ttk.Frame(self.frame); row3.pack(fill="x", pady=4)
        ttk.Label(row3, text="Run (ms):").pack(side="left")
        e = ttk.Entry(row3, textvariable=self.run_ms, width=8)
        e.pack(side="left", padx=4)
        Tooltip(e, "Simulated milliseconds (approx 1 instr = 1 cycle).")
        runb = ttk.Button(row3, text="Run", command=self.run_ms)
        runb.pack(side="left")
        ttk.Label(row3, text="Step (instr):").pack(side="left", padx=(12, 0))
        e2 = ttk.Entry(row3, textvariable=self.step_n, width=10)
        e2.pack(side="left", padx=4)
        stepb = ttk.Button(row3, text="Step", command=self.step)
        stepb.pack(side="left")
        ttk.Checkbutton(row3, text="Trace", variable=self.trace_var,
                        command=self._toggle_trace).pack(side="left", padx=(12, 0))
        ttk.Button(row3, text="Save trace", command=self.save_trace).pack(side="left", padx=4)
        self.busy_widgets += [e, e2, runb, stepb]

        status = ttk.LabelFrame(self.frame, text="Status", padding=6)
        status.pack(fill="x", pady=6)
        self.status_text = tk.StringVar(value="No firmware loaded.")
        ttk.Label(status, textvariable=self.status_text, justify="left").pack(anchor="w")

        uart = ttk.LabelFrame(self.frame, text="UART output", padding=6)
        uart.pack(fill="both", expand=True, pady=6)
        self.uart_box = tk.Text(uart, height=8, state="disabled", wrap="char")
        self.uart_box.pack(fill="both", expand=True)

        regs = ttk.LabelFrame(self.frame, text="Register explorer (double-click to edit)", padding=6)
        regs.pack(fill="x", pady=6)
        cols = ("name", "address", "value")
        self.reg_tree = ttk.Treeview(regs, columns=cols, show="headings", height=7)
        for c, w in zip(cols, (150, 110, 110)):
            self.reg_tree.heading(c, text=c.capitalize())
            self.reg_tree.column(c, width=w, anchor="w")
        self.reg_tree.pack(fill="x", side="left", expand=True)
        sb = ttk.Scrollbar(regs, orient="vertical", command=self.reg_tree.yview)
        sb.pack(side="right", fill="y")
        self.reg_tree.config(yscrollcommand=sb.set)
        self.reg_tree.bind("<Double-1>", lambda _e: self.edit_register())
        rrb = ttk.Frame(regs); rrb.pack(fill="x", pady=2)
        ttk.Button(rrb, text="Refresh registers", command=self.refresh_registers).pack(side="left")
        ttk.Button(rrb, text="Edit selected", command=self.edit_register).pack(side="left", padx=4)

        watch = ttk.LabelFrame(self.frame, text="Watch expressions", padding=6)
        watch.pack(fill="x", pady=6)
        wr = ttk.Frame(watch); wr.pack(fill="x", pady=2)
        self.watch_entry = tk.StringVar()
        ttk.Entry(wr, textvariable=self.watch_entry, width=24).pack(side="left", padx=4)
        ttk.Button(wr, text="Add (name or addr)", command=self.add_watch).pack(side="left", padx=4)
        ttk.Button(wr, text="Remove", command=self.remove_watch).pack(side="left", padx=4)
        ttk.Button(wr, text="Refresh", command=self.refresh_watches).pack(side="left", padx=4)
        self.watch_tree = ttk.Treeview(watch, columns=("name", "address", "value"), show="headings", height=4)
        for c, w in zip(("name", "address", "value"), (150, 110, 110)):
            self.watch_tree.heading(c, text=c.capitalize())
            self.watch_tree.column(c, width=w, anchor="w")
        self.watch_tree.pack(fill="x")

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
        ttk.Button(r, text="Dump 64B", command=self.dump_range).pack(side="left", padx=4)
        ttk.Button(r, text="Plot LED", command=self.plot_led).pack(side="left", padx=4)
        ttk.Button(r, text="Memory Editor", command=self.memory_editor).pack(side="left", padx=4)

        r2 = ttk.Frame(pp); r2.pack(fill="x", pady=2)
        ttk.Label(r2, text="Poke addr:").pack(side="left")
        ttk.Entry(r2, textvariable=self.poke_addr, width=12).pack(side="left", padx=4)
        ttk.Label(r2, text="value:").pack(side="left")
        ttk.Entry(r2, textvariable=self.poke_value, width=12).pack(side="left", padx=4)
        ttk.Label(r2, text="size:").pack(side="left")
        ttk.Entry(r2, textvariable=self.poke_size, width=4).pack(side="left", padx=4)
        ttk.Button(r2, text="Write", command=self.poke).pack(side="left", padx=4)

        r3 = ttk.Frame(pp); r3.pack(fill="x", pady=2)
        ttk.Label(r3, text="Inject RX:").pack(side="left")
        ttk.Entry(r3, textvariable=self.rx_text, width=24).pack(side="left", padx=4)
        ttk.Button(r3, text="Send (text)", command=lambda: self.inject_rx(False)).pack(side="left", padx=4)
        ttk.Button(r3, text="Send (hex:)", command=lambda: self.inject_rx(True)).pack(side="left", padx=4)

        r4 = ttk.Frame(pp); r4.pack(fill="x", pady=2)
        ttk.Label(r4, text="Breakpoint (addr or symbol):").pack(side="left")
        ttk.Entry(r4, textvariable=self.bp_text, width=24).pack(side="left", padx=4)
        ttk.Button(r4, text="Run to BP", command=self.run_to_bp).pack(side="left", padx=4)

        r5 = ttk.Frame(pp); r5.pack(fill="x", pady=2)
        ttk.Label(r5, text="Run until UART contains:").pack(side="left")
        ttk.Entry(r5, textvariable=self.until_text, width=24).pack(side="left", padx=4)
        ttk.Button(r5, text="Run until text", command=self.run_until_text).pack(side="left", padx=4)

    def run_to_bp(self):
        if not self._need_machine():
            return
        text = self.bp_text.get().strip()
        if not text:
            messagebox.showinfo("stmlab", "Breakpoint address/symbol enter karo.")
            return
        try:
            if text in self.machine.symbols:
                addr = self.machine.symbols[text]
            else:
                addr = int(text, 0)
        except ValueError:
            messagebox.showerror("stmlab", "Invalid breakpoint.")
            return
        target = addr & ~1

        def work():
            steps = 0
            max_instr = 20_000_000
            while not self.machine.halted and steps < max_instr:
                self.machine.run_instructions(1000)
                steps += 1000
                if (self.machine.pc() & ~1) == target:
                    break
            return steps

        def done(steps):
            self._after_run()
            if (self.machine.pc() & ~1) == target:
                toast(self.root, "Breakpoint hit at 0x%08x" % target, "success")
            elif self.machine.halted:
                toast(self.root, "Halted: %s" % self.machine.stop_reason, "warning")
            else:
                toast(self.root, "BP not hit (ran %d instr)" % steps, "warning")

        self.run_busy(work, on_done=done)

    def run_until_text(self):
        if not self._need_machine():
            return
        target = self.until_text.get()
        if not target:
            messagebox.showinfo("stmlab", "Target text enter karo.")
            return

        def work():
            steps = 0
            max_instr = 50_000_000
            while not self.machine.halted and target not in self.machine.uart_text and steps < max_instr:
                self.machine.run_instructions(2000)
                steps += 2000
            return steps

        def done(steps):
            self._after_run()
            if target in self.machine.uart_text:
                toast(self.root, "Text found: %r" % target, "success")
            elif self.machine.halted:
                toast(self.root, "Halted: %s" % self.machine.stop_reason, "warning")
            else:
                toast(self.root, "Text not found (ran %d instr)" % steps, "warning")

        self.run_busy(work, on_done=done)

    def memory_editor(self):
        if not self._need_machine():
            return
        try:
            base = self._resolve_addr(self.peek_addr.get())
        except ValueError:
            base = 0x20000000
        top = tk.Toplevel(self.root)
        top.title("Memory editor @ 0x%08x" % base)
        frame = ttk.Frame(top, padding=8)
        frame.pack(fill="both", expand=True)
        addr_var = tk.StringVar(value="0x%08x" % base)
        ttk.Label(frame, text="Base address:").pack(side="left")
        ttk.Entry(frame, textvariable=addr_var, width=12).pack(side="left", padx=4)
        entries = []

        def load():
            for e in entries:
                e.destroy()
            entries.clear()
            try:
                b = int(addr_var.get(), 0)
            except ValueError:
                messagebox.showerror("stmlab", "Invalid address.")
                return
            for row in range(8):
                a = b + row * 16
                ttk.Label(frame, text="0x%08x" % a, font=("Consolas", 9)).pack(anchor="w")
                erow = ttk.Frame(frame)
                erow.pack(anchor="w")
                for i in range(16):
                    try:
                        v = self.machine.peek(a + i, 1)
                    except Exception:  # noqa: BLE001
                        v = 0
                    e = ttk.Entry(erow, width=3)
                    e.insert(0, "%02x" % v)
                    e.pack(side="left")
                    entries.append((a + i, e))

        def save():
            for addr, e in entries:
                try:
                    v = int(e.get(), 16)
                except ValueError:
                    messagebox.showerror("stmlab", "Bad byte at 0x%08x" % addr)
                    return
                self.machine.poke(addr, 1, v)
            toast(self.root, "Memory written.", "success")
            self.refresh_registers()

        ttk.Button(frame, text="Load", command=load).pack(side="left", padx=4)
        ttk.Button(frame, text="Save", command=save).pack(side="left", padx=4)
        load()

    def _toggle_trace(self):
        if self.machine is not None:
            self.machine.trace_enabled = bool(self.trace_var.get())
            if not self.machine.trace_enabled:
                self.machine.clear_trace()

    def save_trace(self):
        if self.machine is None or not self.machine.trace_log:
            messagebox.showinfo("stmlab", "No trace captured. Enable Trace and run first.")
            return
        path = filedialog.asksaveasfilename(title="Save trace", defaultextension=".txt",
                                           filetypes=[("Text", "*.txt"), ("All", "*.*")])
        if not path:
            return
        n = self.machine.dump_trace(path)
        toast(self.root, "Saved %d PCs to %s" % (n, path), "success")

    def add_watch(self):
        if not self._need_machine():
            return
        text = self.watch_entry.get().strip()
        if not text:
            return
        try:
            if text in self.machine.symbols:
                addr = self.machine.symbols[text]
                label = text
            else:
                addr = int(text, 0)
                label = "0x%08x" % addr
        except ValueError:
            messagebox.showerror("stmlab", "Invalid watch expression.")
            return
        self.watches.append((label, addr))
        self.refresh_watches()

    def remove_watch(self):
        sel = self.watch_tree.selection()
        if not sel:
            return
        idx = self.watch_tree.index(sel[0])
        if 0 <= idx < len(self.watches):
            del self.watches[idx]
        self.refresh_watches()

    def refresh_watches(self):
        for item in self.watch_tree.get_children():
            self.watch_tree.delete(item)
        if self.machine is None:
            return
        for label, addr in self.watches:
            try:
                val = self.machine.peek(addr, 4)
            except Exception:  # noqa: BLE001
                val = 0
            self.watch_tree.insert("", "end", values=(label, "0x%08x" % addr, "0x%08x" % val))

    def _resolve_addr(self, text):
        text = text.strip()
        try:
            return int(text, 0)
        except ValueError:
            from stmlab.regmap import resolve
            val = resolve(text, self.board_name.get())
            if val is None:
                raise ValueError("unknown register name: %s" % text)
            return val

    def _register_list(self):
        try:
            from stmlab.regmap import register_map
            return register_map(self.board_name.get())
        except Exception:  # noqa: BLE001
            return []

    def refresh_registers(self):
        for item in self.reg_tree.get_children():
            self.reg_tree.delete(item)
        if self.machine is None:
            return
        for name, addr in self._register_list():
            try:
                val = self.machine.peek(addr, 4)
            except Exception:  # noqa: BLE001
                val = 0
            self.reg_tree.insert("", "end", values=(name, "0x%08x" % addr, "0x%08x" % val))

    def edit_register(self):
        if not self._need_machine():
            return
        sel = self.reg_tree.selection()
        if not sel:
            messagebox.showinfo("stmlab", "Pehle ek register select karo.")
            return
        vals = self.reg_tree.item(sel[0])["values"]
        name, addr_s, cur = vals
        addr = int(addr_s, 0)
        new = simpledialog.askstring("Edit register", "%s @ 0x%08x" % (name, addr),
                                    initialvalue=cur)
        if new is None:
            return
        try:
            value = int(new, 0)
        except ValueError:
            messagebox.showerror("stmlab", "Value invalid (use 0x..).")
            return
        try:
            self.machine.poke(addr, 4, value)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("stmlab", str(exc))
            return
        self.refresh_registers()
        toast(self.root, "%s updated." % name, "success")

    def browse_elf(self):
        path = filedialog.askopenfilename(title="Select firmware ELF",
                                         filetypes=[("ELF files", "*.elf *.axf"), ("All files", "*.*")])
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
        if self.machine is not None:
            self.machine.trace_enabled = bool(self.trace_var.get())
            self.machine.clear_trace()
        self.refresh_status()
        self.refresh_uart()
        self.refresh_registers()
        self.refresh_watches()
        toast(self.root, "Firmware loaded.", "success")

    def reset_machine(self):
        if not self._need_machine():
            return
        self.machine.reset()
        self.refresh_status()
        self.refresh_uart()
        toast(self.root, "Reset done.", "info")

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
        self.refresh_registers()
        self.refresh_watches()

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
            addr = self._resolve_addr(self.peek_addr.get())
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
            addr = self._resolve_addr(self.poke_addr.get())
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
        toast(self.root, "Write done.", "success")

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


    def dump_range(self):
        if not self._need_machine():
            return
        try:
            addr = self._resolve_addr(self.peek_addr.get())
        except ValueError:
            messagebox.showerror("stmlab", "Address invalid.")
            return
        lines = []
        for row in range(4):
            base = addr + row * 16
            try:
                vals = [self.machine.peek(base + i, 1) for i in range(16)]
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("stmlab", str(exc))
                return
            hexpart = " ".join("%02x" % v for v in vals)
            asciipart = "".join(chr(v) if 32 <= v < 127 else "." for v in vals)
            lines.append("0x%08x  %s  %s" % (base, hexpart, asciipart))
        self.uart_box.config(state="normal")
        self.uart_box.insert("end", "\n".join(lines) + "\n")
        self.uart_box.see("end")
        self.uart_box.config(state="disabled")

    def plot_led(self):
        if not self._need_machine():
            return
        events = list(self.machine.led_events)
        if not events:
            messagebox.showinfo("stmlab", "No LED events yet. Run the firmware first.")
            return
        top = tk.Toplevel(self.root)
        top.title("LED state over time")
        canvas = tk.Canvas(top, width=720, height=220, bg="white")
        canvas.pack(padx=8, pady=8)
        # axes
        canvas.create_line(40, 10, 40, 200, fill="#333")
        canvas.create_line(40, 200, 700, 200, fill="#333")
        canvas.create_text(20, 10, text="1", anchor="w", font=("Segoe UI", 9))
        canvas.create_text(20, 190, text="0", anchor="w", font=("Segoe UI", 9))
        xs = [e[0] for e in events]
        xmin, xmax = min(xs), max(xs)
        if xmax == xmin:
            xmax = xmin + 1
        prev_x, prev_y = None, None
        for icount, level in events:
            x = 40 + (icount - xmin) / (xmax - xmin) * 660
            y = 20 if level else 190
            canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill="#1e7e34" if level else "#c0392b")
            if prev_x is not None:
                canvas.create_line(prev_x, prev_y, x, prev_y, fill="#888")
                canvas.create_line(x, prev_y, x, y, fill="#888")
            prev_x, prev_y = x, y
        canvas.create_text(370, 210, text="icount (%d .. %d)" % (xmin, xmax), font=("Segoe UI", 9))

class IcTab(BusyMixin):
    def __init__(self, root, notebook, app):
        super().__init__()
        self.root = root
        self.app = app
        self.status_var = app.status_var
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

        r = ttk.Frame(self.frame); r.pack(fill="x", pady=4)
        ttk.Label(r, text="Backend:").pack(side="left")
        cb = ttk.Combobox(r, textvariable=self.backend_name,
                          values=["sim", "openocd", "stm8flash"], state="readonly", width=12)
        cb.pack(side="left", padx=4)
        Tooltip(cb, "sim = simulated chip, openocd = real STM32, stm8flash = real STM8.")
        cb.bind("<<ComboboxSelected>>", lambda _e: self._update_backend_buttons())
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

        r3 = ttk.LabelFrame(self.frame, text="STM8 options (real STM8)", padding=6)
        r3.pack(fill="x", pady=4)
        rr = ttk.Frame(r3); rr.pack(fill="x", pady=2)
        ttk.Label(rr, text="Part:", width=11).pack(side="left")
        ttk.Entry(rr, textvariable=self.part, width=16).pack(side="left", padx=4)
        ttk.Label(rr, text="Programmer:").pack(side="left", padx=(12, 0))
        ttk.Entry(rr, textvariable=self.programmer, width=12).pack(side="left", padx=4)

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

        r6 = ttk.Frame(self.frame); r6.pack(fill="x", pady=6)
        self.btn_read = ttk.Button(r6, text="Read", command=self.do_read)
        self.btn_write = ttk.Button(r6, text="Write", command=self.do_write)
        self.btn_dump = ttk.Button(r6, text="Dump", command=self.do_dump)
        self.btn_load = ttk.Button(r6, text="Load", command=self.do_load)
        self.btn_verify = ttk.Button(r6, text="Verify", command=self.do_verify)
        self.btn_erase = ttk.Button(r6, text="Mass Erase", command=self.do_mass_erase)
        self.btn_info = ttk.Button(r6, text="Info", command=self.do_info)
        self.btn_reset = ttk.Button(r6, text="Reset", command=self.do_reset)
        for b in (self.btn_read, self.btn_write, self.btn_dump, self.btn_load,
                  self.btn_verify, self.btn_erase, self.btn_info, self.btn_reset):
            b.pack(side="left", padx=3)
            self.busy_widgets.append(b)

        out = ttk.LabelFrame(self.frame, text="Output", padding=6)
        out.pack(fill="both", expand=True, pady=6)
        self.out_box = tk.Text(out, height=14, state="disabled", wrap="char")
        self.out_box.pack(fill="both", expand=True)

        self._update_backend_buttons()

    def _update_backend_buttons(self):
        backend = self.backend_name.get()
        # stm8flash does not support word writes
        if backend == "stm8flash":
            self.btn_write.config(state="disabled")
        else:
            self.btn_write.config(state="normal")

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

    def _addr(self, text):
        text = text.strip()
        if not text:
            raise ValueError("address required")
        try:
            return int(text, 0)
        except ValueError:
            from stmlab.regmap import resolve
            val = resolve(text, self.board_name.get())
            if val is None:
                raise ValueError("unknown register name: %s" % text)
            return val

    def do_read(self):
        def work():
            backend = self._backend()
            addr = self._addr(self.address.get())
            count = self._int(self.count.get(), 1)
            size = self._int(self.size.get(), 4)
            vals = backend.read(addr, count, size)
            lines = ["0x%08x = 0x%0*x" % (addr + i * size, size * 2, v) for i, v in enumerate(vals)]
            return "\n".join(lines)

        self.run_busy(work, on_done=self._log)

    def do_write(self):
        def work():
            backend = self._backend()
            addr = self._addr(self.address.get())
            value = self._int(self.value.get())
            size = self._int(self.size.get(), 4)
            backend.write(addr, value, size)
            return "0x%08x <- 0x%0*x" % (addr, size * 2, value)

        self.run_busy(work, on_done=self._log)

    def do_dump(self):
        def work():
            backend = self._backend()
            addr = self._addr(self.address.get())
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
                addr = self._addr(self.address.get())
            backend.load(path, addr)
            return "loaded %s" % path

        self.run_busy(work, on_done=self._log)

    def do_verify(self):
        if not messagebox.askyesno("stmlab", "Verify file against chip memory?"):
            return
        def work():
            backend = self._backend()
            path = self.file_path.get().strip()
            if not path or not os.path.isfile(path):
                raise IcError("Valid file required for verify.")
            addr = None
            if self.address.get().strip():
                addr = self._addr(self.address.get())
            return backend.verify(path, addr)

        self.run_busy(work, on_done=self._log)

    def do_mass_erase(self):
        if not messagebox.askyesno("stmlab", "Mass erase ALL flash? This cannot be undone."):
            return
        def work():
            return self._backend().mass_erase()

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


class HardwareTab(BusyMixin):
    def __init__(self, root, notebook, app):
        super().__init__()
        self.root = root
        self.app = app
        self.status_var = app.status_var
        self.frame = ttk.Frame(notebook, padding=10)
        notebook.add(self.frame, text="Hardware")

        self.board_name = tk.StringVar(value="f411re")
        self.port_name = tk.StringVar()
        self.baudrate = tk.StringVar(value="115200")
        self.backend_name = tk.StringVar(value="openocd")
        self.interface = tk.StringVar(value="interface/stlink.cfg")
        self.target = tk.StringVar(value="target/stm32f4x.cfg")
        self.part = tk.StringVar(value="stm8s103f3")
        self.programmer = tk.StringVar(value="stlinkv2")
        self.exe_path = tk.StringVar()

        self.busy_widgets = []

        # ---- board + port ----
        r = ttk.Frame(self.frame); r.pack(fill="x", pady=4)
        ttk.Label(r, text="Board:").pack(side="left")
        cb = ttk.Combobox(r, textvariable=self.board_name, values=sorted(BOARDS),
                          state="readonly", width=10)
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda _e: self.refresh_wiring())
        ttk.Label(r, text="Serial port:").pack(side="left", padx=(12, 0))
        self.port_cb = ttk.Combobox(r, textvariable=self.port_name, values=[], width=26)
        self.port_cb.pack(side="left", padx=4)
        ttk.Button(r, text="Refresh ports", command=self.refresh_ports).pack(side="left", padx=4)
        ttk.Label(r, text="Baudrate:").pack(side="left", padx=(12, 0))
        ttk.Combobox(r, textvariable=self.baudrate,
                     values=["9600", "19200", "38400", "57600", "115200",
                             "230400", "460800", "921600"], width=10).pack(side="left", padx=4)

        if not HAS_SERIAL:
            ttk.Label(self.frame, text="pyserial not installed -> port auto-detect disabled. "
                                       "Install: pip install pyserial",
                      foreground="#b7791f").pack(anchor="w", pady=2)

        # ---- wiring diagram ----
        wd = ttk.LabelFrame(self.frame, text="Wiring diagram", padding=6)
        wd.pack(fill="both", expand=True, pady=6)
        self.wiring_box = tk.Text(wd, height=14, state="disabled", wrap="none",
                                  font=("Consolas", 10))
        self.wiring_box.pack(fill="both", expand=True)
        self.refresh_wiring()

        # ---- serial monitor ----
        sm = ttk.LabelFrame(self.frame, text="Serial monitor (UART printf)", padding=6)
        sm.pack(fill="both", expand=True, pady=6)
        sr = ttk.Frame(sm); sr.pack(fill="x", pady=2)
        self.serial_status = tk.StringVar(value="Disconnected")
        ttk.Label(sr, textvariable=self.serial_status).pack(side="left")
        self.btn_serial_connect = ttk.Button(sr, text="Connect", command=self.serial_connect)
        self.btn_serial_connect.pack(side="left", padx=6)
        self.btn_serial_disconnect = ttk.Button(sr, text="Disconnect", command=self.serial_disconnect, state="disabled")
        self.btn_serial_disconnect.pack(side="left", padx=2)
        ttk.Button(sr, text="Clear", command=self.serial_clear).pack(side="left", padx=2)
        self.serial_send_text = tk.StringVar()
        ss = ttk.Frame(sm); ss.pack(fill="x", pady=2)
        ttk.Entry(ss, textvariable=self.serial_send_text, width=40).pack(side="left", padx=4, fill="x", expand=True)
        ttk.Button(ss, text="Send", command=self.serial_send).pack(side="left", padx=4)
        ttk.Label(ss, text="(append \\\\n automatically)").pack(side="left")
        self.serial_box = tk.Text(sm, height=8, state="disabled", wrap="char", font=("Consolas", 10))
        self.serial_box.pack(fill="both", expand=True, pady=4)

        # ---- connection test ----
        r2 = ttk.Frame(self.frame); r2.pack(fill="x", pady=4)
        ttk.Label(r2, text="Backend:").pack(side="left")
        ttk.Combobox(r2, textvariable=self.backend_name,
                     values=["openocd", "stm8flash"], state="readonly", width=12).pack(side="left", padx=4)
        ttk.Label(r2, text="Interface:").pack(side="left", padx=(12, 0))
        ttk.Entry(r2, textvariable=self.interface, width=24).pack(side="left", padx=4)
        ttk.Label(r2, text="Target:").pack(side="left", padx=(12, 0))
        ttk.Entry(r2, textvariable=self.target, width=24).pack(side="left", padx=4)
        ttk.Label(r2, text="exe:").pack(side="left", padx=(12, 0))
        ttk.Entry(r2, textvariable=self.exe_path, width=24).pack(side="left", padx=4)

        r3 = ttk.Frame(self.frame); r3.pack(fill="x", pady=4)
        ttk.Label(r3, text="Part (STM8):").pack(side="left")
        ttk.Entry(r3, textvariable=self.part, width=14).pack(side="left", padx=4)
        ttk.Label(r3, text="Programmer:").pack(side="left", padx=(12, 0))
        ttk.Entry(r3, textvariable=self.programmer, width=12).pack(side="left", padx=4)
        test = ttk.Button(r3, text="Test connection", command=self.test_connection)
        test.pack(side="left", padx=12)
        self.busy_widgets.append(test)
        self.conn_status = tk.StringVar(value="Not tested yet.")
        ttk.Label(r3, textvariable=self.conn_status).pack(side="left", padx=8)

        self.serial_conn = None
        self.serial_thread = None
        self.serial_stop = threading.Event()
        self.refresh_ports()

    def refresh_wiring(self):
        board = self.board_name.get()
        text = WIRING.get(board, "No wiring info.")
        self.wiring_box.config(state="normal")
        self.wiring_box.delete("1.0", "end")
        self.wiring_box.insert("end", text)
        self.wiring_box.config(state="disabled")

    def refresh_ports(self):
        if not HAS_SERIAL:
            return
        ports = []
        for p in serial.tools.list_ports.comports():
            ports.append("%s - %s" % (p.device, p.description))
        self.port_cb["values"] = ports
        if ports and not self.port_name.get():
            self.port_name.set(ports[0].split(" - ")[0])

    def _args(self):
        import argparse
        ns = argparse.Namespace()
        ns.backend = self.backend_name.get()
        ns.board = self.board_name.get()
        ns.elf = None
        ns.interface = self.interface.get().strip() or None
        ns.target = self.target.get().strip() or None
        ns.part = self.part.get().strip()
        ns.programmer = self.programmer.get().strip()
        ns.exe = self.exe_path.get().strip() or None
        ns.speed = None
        return ns

    def test_connection(self):
        def work():
            from stmlab.ic import make_backend
            backend = make_backend(self._args())
            return backend.info()

        def done(text):
            self.conn_status.set("OK: %s" % text.replace("\n", " ")[:80])
            toast(self.root, "Connection OK", "success")

        def fail(exc):
            self.conn_status.set("FAIL: %s" % str(exc)[:80])
            toast(self.root, "Connection failed", "error")

        # run_busy only calls on_done on success; handle failure via toast in _fail already
        self.run_busy(work, on_done=done)

    # ---- serial monitor ----
    def _serial_port_name(self):
        name = self.port_name.get().strip()
        if " - " in name:
            name = name.split(" - ")[0]
        return name.strip()

    def serial_connect(self):
        if not HAS_SERIAL:
            messagebox.showerror("stmlab", "pyserial not installed. pip install pyserial")
            return
        port = self._serial_port_name()
        if not port:
            messagebox.showerror("stmlab", "Serial port select karo (Refresh ports).")
            return
        try:
            baud = int(self.baudrate.get())
        except ValueError:
            messagebox.showerror("stmlab", "Baudrate invalid.")
            return
        try:
            import serial as _serial
            self.serial_conn = _serial.Serial(port, baud, timeout=0.1)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("stmlab", "Connect failed: %s" % exc)
            self.serial_conn = None
            return
        self.serial_stop.clear()
        self.serial_thread = threading.Thread(target=self._serial_reader, daemon=True)
        self.serial_thread.start()
        self.btn_serial_connect.config(state="disabled")
        self.btn_serial_disconnect.config(state="normal")
        self.serial_status.set("Connected %s @ %d" % (port, baud))
        toast(self.root, "Serial connected.", "success")

    def _serial_reader(self):
        while not self.serial_stop.is_set() and self.serial_conn is not None:
            try:
                data = self.serial_conn.read(256)
            except Exception:  # noqa: BLE001
                break
            if data:
                text = data.decode("utf-8", errors="replace")
                self.root.after(0, lambda t=text: self._serial_append(t))

    def _serial_append(self, text):
        self.serial_box.config(state="normal")
        self.serial_box.insert("end", text)
        self.serial_box.see("end")
        self.serial_box.config(state="disabled")

    def serial_disconnect(self):
        self.serial_stop.set()
        if self.serial_conn is not None:
            try:
                self.serial_conn.close()
            except Exception:  # noqa: BLE001
                pass
        self.serial_conn = None
        self.btn_serial_connect.config(state="normal")
        self.btn_serial_disconnect.config(state="disabled")
        self.serial_status.set("Disconnected")
        toast(self.root, "Serial disconnected.", "info")

    def serial_send(self):
        if self.serial_conn is None:
            messagebox.showinfo("stmlab", "Pehle Connect dabao.")
            return
        text = self.serial_send_text.get()
        if not text:
            return
        try:
            self.serial_conn.write((text + "\\n").encode())
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("stmlab", "Send failed: %s" % exc)
            return
        self._serial_append(">> " + text + "\\n")

    def serial_clear(self):
        self.serial_box.config(state="normal")
        self.serial_box.delete("1.0", "end")
        self.serial_box.config(state="disabled")


class StmlabGui:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("stmlab - STM32 Simulator & IC Read/Write")
        self.root.geometry("980x760")
        self.root.minsize(820, 600)
        self.status_var = tk.StringVar(value="Ready")

        # Optional modern theme
        if HAS_SVTTK:
            try:
                sv_ttk.set_theme("light")
            except Exception:  # noqa: BLE001
                pass

        # Menu bar
        menubar = tk.Menu(self.root)
        view = tk.Menu(menubar, tearoff=0)
        view.add_command(label="Toggle dark mode", command=self.toggle_theme)
        menubar.add_cascade(label="View", menu=view)
        helpm = tk.Menu(menubar, tearoff=0)
        helpm.add_command(label="About stmlab", command=self.about)
        helpm.add_command(label="Open README", command=self.open_readme)
        helpm.add_command(label="Open docs folder", command=self.open_docs)
        helpm.add_command(label="Guided exercises", command=self.show_exercises)
        menubar.add_cascade(label="Help", menu=helpm)
        self.root.config(menu=menubar)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=6, pady=6)

        self.hw_tab = HardwareTab(self.root, notebook, self)
        self.sim_tab = SimTab(self.root, notebook, self)
        self.ic_tab = IcTab(self.root, notebook, self)

        # status bar with progress
        bar = ttk.Frame(self.root, padding=(6, 2))
        bar.pack(fill="x")
        ttk.Label(bar, textvariable=self.status_var).pack(side="left")
        self.progress = ttk.Progressbar(bar, mode="indeterminate", length=160)
        self.progress.pack(side="right", padx=6)

        self._dark = False
        self.settings_path = os.path.join(os.path.expanduser("~"), ".stmlab.json")
        self.load_settings()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_settings(self):
        import json
        try:
            with open(self.settings_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:  # noqa: BLE001
            data = {}
        try:
            if "sim" in data:
                d = data["sim"]
                if "board" in d: self.sim_tab.board_name.set(d["board"])
                if "elf" in d: self.sim_tab.elf_path.set(d["elf"])
                if "run_ms" in d: self.sim_tab.run_ms.set(d["run_ms"])
                if "step_n" in d: self.sim_tab.step_n.set(d["step_n"])
            if "ic" in data:
                d = data["ic"]
                for k, v in d.items():
                    attr = k
                    if hasattr(self.ic_tab, attr + "_name") is False and hasattr(self.ic_tab, attr):
                        pass
                if "backend" in d: self.ic_tab.backend_name.set(d["backend"])
                if "board" in d: self.ic_tab.board_name.set(d["board"])
                if "interface" in d: self.ic_tab.interface.set(d["interface"])
                if "target" in d: self.ic_tab.target.set(d["target"])
                if "part" in d: self.ic_tab.part.set(d["part"])
                if "programmer" in d: self.ic_tab.programmer.set(d["programmer"])
                if "exe" in d: self.ic_tab.exe_path.set(d["exe"])
                if "address" in d: self.ic_tab.address.set(d["address"])
                if "size" in d: self.ic_tab.size.set(d["size"])
                if "length" in d: self.ic_tab.length.set(d["length"])
            if "hw" in data:
                d = data["hw"]
                if "board" in d: self.hw_tab.board_name.set(d["board"])
                if "port" in d: self.hw_tab.port_name.set(d["port"])
                if "baudrate" in d: self.hw_tab.baudrate.set(d["baudrate"])
                if "backend" in d: self.hw_tab.backend_name.set(d["backend"])
                if "interface" in d: self.hw_tab.interface.set(d["interface"])
                if "target" in d: self.hw_tab.target.set(d["target"])
                if "part" in d: self.hw_tab.part.set(d["part"])
                if "programmer" in d: self.hw_tab.programmer.set(d["programmer"])
                if "exe" in d: self.hw_tab.exe_path.set(d["exe"])
            if data.get("dark"):
                self._dark = True
                self.toggle_theme()
        except Exception:  # noqa: BLE001
            pass

    def save_settings(self):
        import json
        data = {
            "sim": {
                "board": self.sim_tab.board_name.get(),
                "elf": self.sim_tab.elf_path.get(),
                "run_ms": self.sim_tab.run_ms.get(),
                "step_n": self.sim_tab.step_n.get(),
            },
            "ic": {
                "backend": self.ic_tab.backend_name.get(),
                "board": self.ic_tab.board_name.get(),
                "interface": self.ic_tab.interface.get(),
                "target": self.ic_tab.target.get(),
                "part": self.ic_tab.part.get(),
                "programmer": self.ic_tab.programmer.get(),
                "exe": self.ic_tab.exe_path.get(),
                "address": self.ic_tab.address.get(),
                "size": self.ic_tab.size.get(),
                "length": self.ic_tab.length.get(),
            },
            "hw": {
                "board": self.hw_tab.board_name.get(),
                "port": self.hw_tab.port_name.get(),
                "baudrate": self.hw_tab.baudrate.get(),
                "backend": self.hw_tab.backend_name.get(),
                "interface": self.hw_tab.interface.get(),
                "target": self.hw_tab.target.get(),
                "part": self.hw_tab.part.get(),
                "programmer": self.hw_tab.programmer.get(),
                "exe": self.hw_tab.exe_path.get(),
            },
            "dark": self._dark,
        }
        try:
            with open(self.settings_path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
        except Exception:  # noqa: BLE001
            pass

    def on_close(self):
        self.save_settings()
        # stop serial if connected
        try:
            self.hw_tab.serial_disconnect()
        except Exception:  # noqa: BLE001
            pass
        self.root.destroy()

    def toggle_theme(self):
        self._dark = not self._dark
        if HAS_SVTTK:
            try:
                sv_ttk.set_theme("dark" if self._dark else "light")
                return
            except Exception:  # noqa: BLE001
                pass
        # Fallback: basic color swap
        bg = "#1e1e1e" if self._dark else "#f0f0f0"
        fg = "#e0e0e0" if self._dark else "#000000"
        self.root.config(bg=bg)
        toast(self.root, "Theme toggled (limited without sv_ttk).", "info")

    def about(self):
        messagebox.showinfo(
            "stmlab",
            "stmlab - STM32 simulator + IC read/write GUI\n\n"
            "Unicorn-based Cortex-M simulator, OpenOCD/stm8flash backends,\n"
            "Tkinter front-end. Beginner friendly.\n\n"
            "Repo: https://github.com/waraseoni/stm",
        )

    def open_readme(self):
        import webbrowser
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), "sim", "README.md")
        webbrowser.open("file://" + path.replace("\\", "/"))

    def open_docs(self):
        import webbrowser
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        webbrowser.open("file://" + os.path.join(root, "docs").replace("\\", "/"))

    def show_exercises(self):
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        top = tk.Toplevel(self.root)
        top.title("Guided exercises")
        frame = ttk.Frame(top, padding=8)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Select an exercise folder:").pack(anchor="w")
        lb = tk.Listbox(frame, height=14, width=40)
        lb.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(frame, orient="vertical", command=lb.yview)
        sb.pack(side="right", fill="y")
        lb.config(yscrollcommand=sb.set)
        items = []
        for base in ("stm8", "stm32"):
            d = os.path.join(root, base)
            if not os.path.isdir(d):
                continue
            for name in sorted(os.listdir(d)):
                if os.path.isdir(os.path.join(d, name)):
                    items.append("%s/%s" % (base, name))
        for it in items:
            lb.insert("end", it)

        def open_folder():
            sel = lb.curselection()
            if not sel:
                return
            path = os.path.join(root, lb.get(sel[0]).replace("/", os.sep))
            os.startfile(path)

        def open_readme_ex():
            sel = lb.curselection()
            if not sel:
                return
            path = os.path.join(root, lb.get(sel[0]).replace("/", os.sep), "README.md")
            if os.path.isfile(path):
                import webbrowser
                webbrowser.open("file://" + path.replace("\\", "/"))
            else:
                messagebox.showinfo("stmlab", "No README.md in this folder.")

        btns = ttk.Frame(frame)
        btns.pack(fill="x", pady=4)
        ttk.Button(btns, text="Open folder", command=open_folder).pack(side="left", padx=4)
        ttk.Button(btns, text="Open README", command=open_readme_ex).pack(side="left", padx=4)

    def run(self):
        self.root.mainloop()


def main():
    app = StmlabGui()
    app.run()


if __name__ == "__main__":
    main()
