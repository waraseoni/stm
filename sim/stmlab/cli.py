"""Command line front-end for stmlab."""

import argparse
import json
import shlex
import sys
import time

from . import mini
from .boards import BOARDS, get_board
from .ic import IcError, Stm8FlashBackend, make_backend
from .machine import Machine, MachineError


def parse_int(text):
    """Accept 0x.., 1234, 0b.., and 1_000 style numbers."""
    return int(str(text).replace("_", ""), 0)


def _print_summary(machine, heading=None):
    if heading:
        print(heading)
    info = machine.summary()
    uart = info["uart"]
    print("  board        : %s (%s)" % (info["board"], "Cortex-M"))
    print("  instructions : %d" % info["icount"])
    print("  core clock   : %.1f MHz (assumed)" % (info["core_hz"] / 1e6))
    print("  pc           : 0x%08x" % info["pc"])
    if uart:
        print("  uart output  : %r" % uart)
    print("  led %-3s      : %s (%d toggle%s)" % (
        info["led_pin"], "on" if info["led_state"] else "off",
        info["led_toggles"], "" if info["led_toggles"] == 1 else "s",
    ))
    if info["pwm_updates"]:
        print("  pwm updates  : %d (duty %.1f%%)" % (
            info["pwm_updates"], info["pwm_duty"] * 100,
        ))
    if info["pending_irq"]:
        print("  pending irq  : %s" % info["pending_irq"])
    if info["halted"]:
        print("  stopped      : %s" % info["stop_reason"])


def _print_events(machine, limit=40):
    events = []
    for icount, level in list(machine.led_events)[:limit]:
        events.append((icount, "led", "on" if level else "off"))
    for icount, value in list(machine.pwm_events)[:limit]:
        events.append((icount, "pwm", value))
    for icount, port, changed, odr in list(machine.pin_events)[:limit]:
        events.append((icount, "pins", "%s changed=0x%04x odr=0x%04x"
                       % (port, changed, odr)))
    events.sort()
    for icount, kind, text in events[:limit]:
        print("  [%8d] %-4s %s" % (icount, kind, text))


# --------------------------------------------------------------------------
# run / demo
# --------------------------------------------------------------------------

def cmd_boards(args):
    print("%-8s %-8s %9s %9s  %s" % ("board", "core", "flash", "ram", "led"))
    for board in BOARDS.values():
        print("%-8s %-8s %8dK %8dK  %s%d" % (
            board.name, board.core, board.flash_size // 1024,
            board.ram_size // 1024, board.led_port, board.led_pin,
        ))


def cmd_demo(args):
    board = get_board(args.board)
    segments, entry, symbols = mini.build_demo(board)
    machine = Machine(board.name, trace=args.trace)
    machine.load_raw(segments, entry, sp=board.ram_end, symbols=symbols)
    machine.run_ms(args.ms)
    _print_summary(machine, "stmlab demo on %s (hand-assembled, no toolchain)"
                   % board.name)
    counter = symbols.get("tick_counter")
    if counter:
        try:
            print("  systick ticks: %d" % machine.read(counter, 4))
        except Exception:
            pass
    if args.trace:
        _print_events(machine)


def cmd_run(args):
    board = get_board(args.board)
    machine = Machine(board.name, trace=args.trace)
    image = machine.load_elf(args.elf)
    if args.trace:
        print("loaded %s" % image.describe())
    if args.instr:
        machine.run_instructions(args.instr)
    else:
        machine.run_ms(args.ms)
    _print_summary(machine, "ran %s on %s" % (args.elf, board.name))
    if args.trace:
        _print_events(machine)
    if args.json:
        print(json.dumps(machine.summary(), indent=2))
    return 1 if machine.halted and "CPU error" in machine.stop_reason else 0


# --------------------------------------------------------------------------
# interactive session
# --------------------------------------------------------------------------

SESSION_HELP = """commands:
  run [ms]              simulated milliseconds chalao
  step [n]              n instructions chalao
  regs                  core registers dikhao
  peek ADDR [SIZE]      memory/peripheral padho (simulator ke through)
  poke ADDR VALUE [SZ]  memory/peripheral likho
  uart [clear]          UART output dikhao / clear karo
  led                   LED state
  rx TEXT | rx hex:4142 UART RX bytes inject karo (interrupt bhi trigger hota hai)
  button 0|1            user button dabao/chhodo
  irq N                 IRQ pending karo
  events                LED/PWM/pin events
  symbols [PATTERN]     ELF symbols
  reset                 board reset (ELF dobara load)
  info                  board + machine summary
  help / quit
"""


def cmd_session(args):
    board = get_board(args.board)
    if not args.elf:
        raise SystemExit("session ke liye ELF chahiye: stmlab session firmware.elf")
    machine = Machine(board.name, trace=args.trace)
    machine.load_elf(args.elf)
    print("stmlab session - %s, %s" % (board.name, args.elf))
    print("'help' se commands dekho, 'quit' se bahar.\n")
    while True:
        try:
            line = input("stmlab> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        try:
            parts = shlex.split(line)
        except ValueError as exc:
            print("parse error:", exc)
            continue
        cmd, rest = parts[0].lower(), parts[1:]
        try:
            if cmd in ("quit", "exit", "q"):
                break
            elif cmd in ("help", "h", "?"):
                print(SESSION_HELP)
            elif cmd == "run":
                machine.run_ms(float(rest[0]) if rest else 10.0)
                _print_summary(machine)
            elif cmd in ("step", "s"):
                machine.run_instructions(int(parse_int(rest[0])) if rest else 1)
                print("icount=%d pc=0x%08x" % (machine.icount, machine.pc()))
            elif cmd in ("regs", "r"):
                for name, value in machine.registers().items():
                    print("  %-8s 0x%08x" % (name, value))
            elif cmd == "peek":
                addr = parse_int(rest[0])
                size = parse_int(rest[1]) if len(rest) > 1 else 4
                print("0x%08x = 0x%0*x" % (addr, size * 2, machine.peek(addr, size)))
            elif cmd == "poke":
                addr, value = parse_int(rest[0]), parse_int(rest[1])
                size = parse_int(rest[2]) if len(rest) > 2 else 4
                machine.poke(addr, size, value)
                print("wrote 0x%08x = 0x%0*x" % (addr, size * 2, value))
            elif cmd == "uart":
                if rest and rest[0] == "clear":
                    machine.uart.clear()
                print(repr(machine.uart_text))
            elif cmd == "led":
                print("LED %s%d %s" % (
                    board.led_port, board.led_pin,
                    "on" if machine.led_state else "off"))
            elif cmd == "rx":
                if not rest:
                    raise ValueError("rx TEXT ya rx hex:4142")
                text = " ".join(rest)
                if text.startswith("hex:"):
                    data = bytes.fromhex(text[4:].replace(" ", ""))
                else:
                    data = text.encode()
                for byte in data:
                    machine.inject_uart_rx(byte)
                print("injected %d byte(s)" % len(data))
            elif cmd == "button":
                machine.set_button(bool(parse_int(rest[0])))
                print("button", "pressed" if parse_int(rest[0]) else "released")
            elif cmd == "irq":
                number = parse_int(rest[0])
                machine.raise_irq(number)
                print("IRQ %d pending" % number)
            elif cmd == "events":
                _print_events(machine)
            elif cmd == "symbols":
                pattern = rest[0] if rest else ""
                hits = [(n, a) for n, a in sorted(machine.symbols.items())
                        if pattern in n]
                for name, addr in hits[:200]:
                    print("  0x%08x  %s" % (addr, name))
                if not hits:
                    print("  (koi symbol nahi mila)")
            elif cmd == "reset":
                machine.reset()
                print("reset done")
            elif cmd == "info":
                _print_summary(machine)
            else:
                print("unknown command:", cmd, "(help dekho)")
        except (ValueError, IndexError, IcError) as exc:
            print("error:", exc)
    return 0


# --------------------------------------------------------------------------
# ic (real chip or simulated chip)
# --------------------------------------------------------------------------

def _add_backend_options(parser):
    parser.add_argument(
        "--backend", choices=("openocd", "stm8flash", "sim"),
        default="openocd",
        help="openocd = STM32 probe, stm8flash = STM8 probe, sim = simulated chip",
    )
    parser.add_argument("--board", default="f411re", help="sim board name")
    parser.add_argument("--elf", help="sim only: ELF image load karo")
    parser.add_argument("--interface", default="interface/stlink.cfg")
    parser.add_argument("--target", default="target/stm32f4x.cfg")
    parser.add_argument("--part", default="stm8s103f3")
    parser.add_argument("--programmer", default="stlinkv2")
    parser.add_argument("--exe", help="probe tool ka poora path")
    parser.add_argument("--speed", help="OpenOCD adapter speed (kHz)")


def _fmt_values(addr, values, size):
    for index, value in enumerate(values):
        print("0x%08x = 0x%0*x" % (addr + index * size, size * 2, value))


def _resolve_addr(args, text):
    text = str(text).strip()
    try:
        return parse_int(text)
    except ValueError:
        from stmlab.regmap import resolve
        board = getattr(args, "board", "f411re")
        val = resolve(text, board)
        if val is None:
            raise IcError("unknown register name: %s" % text)
        return val


def cmd_ic(args):
    backend = make_backend(args)
    action = args.action

    if action == "read":
        addr = _resolve_addr(args, args.address)
        values = backend.read(addr, args.count, args.size)
        _fmt_values(addr, values, args.size)
    elif action == "write":
        addr = _resolve_addr(args, args.address)
        backend.write(addr, args.value, args.size)
        print("0x%08x <- 0x%0*x" % (addr, args.size * 2, args.value))
    elif action == "dump":
        addr = _resolve_addr(args, args.address)
        path = backend.dump(addr, args.length, args.out)
        print("dumped %d bytes from 0x%08x to %s" % (args.length, addr, path))
    elif action == "load":
        addr = None
        if getattr(args, "addr", None):
            addr = _resolve_addr(args, args.addr)
        backend.load(args.file, addr)
        print("loaded %s" % args.file)
    elif action == "info":
        print(backend.info())
    elif action == "reset":
        if not hasattr(backend, "reset"):
            raise IcError("%s reset support nahi karta" % backend.name)
        backend.reset()
        print("reset done")
    elif action == "verify":
        msg = backend.verify(args.file, args.addr)
        print(msg)
    elif action == "mass-erase":
        print(backend.mass_erase())
    else:                                   # pragma: no cover - argparse guards
        raise IcError("unknown ic action: %s" % action)
    return 0


# --------------------------------------------------------------------------
# parser
# --------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="stmlab",
        description="STM32 instruction simulator + real chip read/write CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="hand-assembled demo (toolchain ki zaroorat nahi)")
    demo.add_argument("--board", default="f411re", choices=sorted(BOARDS))
    demo.add_argument("--ms", type=float, default=250.0)
    demo.add_argument("--trace", action="store_true")
    demo.set_defaults(func=cmd_demo)

    run = sub.add_parser("run", help="ELF firmware ko simulator me chalao")
    run.add_argument("elf")
    run.add_argument("--board", default="f411re", choices=sorted(BOARDS))
    run.add_argument("--ms", type=float, default=200.0)
    run.add_argument("--instr", type=int, default=0,
                     help="milliseconds ki jagah instruction count")
    run.add_argument("--trace", action="store_true")
    run.add_argument("--json", action="store_true")
    run.set_defaults(func=cmd_run)

    session = sub.add_parser("session", help="interactive simulator session")
    session.add_argument("elf", nargs="?")
    session.add_argument("--board", default="f411re", choices=sorted(BOARDS))
    session.add_argument("--trace", action="store_true")
    session.set_defaults(func=cmd_session)

    boards = sub.add_parser("boards", help="supported boards list karo")
    boards.set_defaults(func=cmd_boards)

    ic = sub.add_parser("ic", help="chip memory/registers padho-likho")
    ic_sub = ic.add_subparsers(dest="action", required=True)

    read = ic_sub.add_parser("read", help="memory words padho")
    read.add_argument("address", type=str)
    read.add_argument("-n", "--count", type=parse_int, default=1)
    read.add_argument("-s", "--size", type=parse_int, choices=(1, 2, 4), default=4)
    _add_backend_options(read)
    read.set_defaults(func=cmd_ic)

    write = ic_sub.add_parser("write", help="memory word likho")
    write.add_argument("address", type=str)
    write.add_argument("value", type=parse_int)
    write.add_argument("-s", "--size", type=parse_int, choices=(1, 2, 4), default=4)
    _add_backend_options(write)
    write.set_defaults(func=cmd_ic)

    dump = ic_sub.add_parser("dump", help="memory ko file me dump karo")
    dump.add_argument("address", type=str)
    dump.add_argument("--length", type=parse_int, required=True)
    dump.add_argument("--out", required=True)
    _add_backend_options(dump)
    dump.set_defaults(func=cmd_ic)

    load = ic_sub.add_parser("load", help="binary/ELF file chip par likho")
    load.add_argument("file")
    load.add_argument("--addr", type=str)
    _add_backend_options(load)
    load.set_defaults(func=cmd_ic)

    info = ic_sub.add_parser("info", help="probe/target info")
    _add_backend_options(info)
    info.set_defaults(func=cmd_ic)

    reset = ic_sub.add_parser("reset", help="target reset")
    _add_backend_options(reset)
    reset.set_defaults(func=cmd_ic)

    verify = ic_sub.add_parser("verify", help="verify a file against chip memory")
    verify.add_argument("file")
    verify.add_argument("--addr", type=parse_int)
    _add_backend_options(verify)
    verify.set_defaults(func=cmd_ic, action="verify")

    mass_erase = ic_sub.add_parser("mass-erase", help="erase all flash (with confirmation)")
    _add_backend_options(mass_erase)
    mass_erase.set_defaults(func=cmd_ic, action="mass-erase")

    # STM8 convenience wrappers (dump/flash are the only stm8flash operations).
    stm8_dump = ic_sub.add_parser("stm8-dump", help="STM8 flash ko file me dump karo")
    stm8_dump.add_argument("file")
    _add_backend_options(stm8_dump)
    stm8_dump.set_defaults(func=_cmd_stm8_dump)

    stm8_flash = ic_sub.add_parser("stm8-flash", help="STM8 flash file ko program karo")
    stm8_flash.add_argument("file")
    _add_backend_options(stm8_flash)
    stm8_flash.set_defaults(func=_cmd_stm8_flash)

    # Top-level GDB remote stub.
    gdb = sub.add_parser("gdb", help="start a minimal GDB remote stub")
    gdb.add_argument("elf", nargs="?")
    gdb.add_argument("--board", default="f411re", choices=sorted(BOARDS))
    gdb.add_argument("--port", type=int, default=1234)
    gdb.add_argument("--host", default="127.0.0.1")
    gdb.add_argument("--trace", action="store_true")
    gdb.set_defaults(func=cmd_gdb)

    return parser


def _cmd_stm8_dump(args):
    backend = Stm8FlashBackend(args.part, args.programmer, args.exe)
    backend.dump(0, 0, args.file)
    print("STM8 flash dumped to %s" % args.file)
    return 0


def _cmd_stm8_flash(args):
    backend = Stm8FlashBackend(args.part, args.programmer, args.exe)
    backend.load(args.file)
    print("STM8 flash written from %s" % args.file)
    return 0


def cmd_gdb(args):
    board = get_board(args.board)
    machine = Machine(board.name, trace=args.trace)
    if args.elf:
        machine.load_elf(args.elf)
    from stmlab.gdbstub import GdbStub
    stub = GdbStub(machine, host=args.host, port=args.port)
    stub.start()
    print("GDB stub listening on %s:%d" % (args.host, args.port))
    print("target remote %s:%d" % (args.host, args.port))
    print("Press Ctrl-C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    stub.stop()
    print("stopped")
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args) or 0
    except (IcError, MachineError, OSError) as exc:
        print("error:", exc, file=sys.stderr)
        return 2
