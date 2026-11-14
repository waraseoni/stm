"""Chip back-ends: talk to real STM32/STM8 parts (OpenOCD, stm8flash) or to
the simulated chip.

Every back-end exposes the same small surface:

    read(addr, count=1, size=4) -> list[int]
    write(addr, value, size=4)
    dump(addr, length, path)
    load(path, addr=None)
    info() -> str

so the CLI (and scripts) can use them interchangeably.
"""

import glob
import os
import re
import shutil
import subprocess
import tempfile

from .boards import get_board
from .machine import Machine


class IcError(RuntimeError):
    """Raised when the probe/tool is missing or reports a failure."""


def find_tool(name, patterns=()):
    """Locate an executable on PATH or in a known install directory."""
    found = shutil.which(name)
    if found:
        return found
    for pattern in patterns:
        hits = glob.glob(pattern)
        if hits:
            return hits[0]
    return None


def _run(cmd, timeout=120):
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
    except FileNotFoundError:
        raise IcError("tool not found: %s" % cmd[0])
    except subprocess.TimeoutExpired:
        raise IcError("timeout after %ss: %s" % (timeout, " ".join(cmd)))
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise IcError(
            "%s failed (exit %d)%s"
            % (cmd[0], proc.returncode, (": " + detail) if detail else "")
        )
    return proc.stdout


_MD_TOKENS = re.compile(r"\b([0-9a-fA-F]{2,8})\b")


def _parse_md(text):
    """Parse OpenOCD `mdw/mdh/mdb` output into a list of integers."""
    values = []
    for line in text.splitlines():
        if ":" not in line:
            continue
        _, rest = line.split(":", 1)
        for token in rest.split():
            token = token.strip().rstrip(",")
            if _MD_TOKENS.fullmatch(token):
                values.append(int(token, 16))
    return values


class OpenOCDBackend:
    """STM32 access through a ST-Link/CMSIS-DAP probe and OpenOCD."""

    name = "openocd"

    OPENOCD_PATTERNS = (
        r"C:\ST\*openocd*\bin\openocd.exe",
        r"C:\ST\*openocd*.exe",
        r"C:\Program Files\STMicroelectronics\*\openocd*\bin\openocd.exe",
        r"C:\Program Files (x86)\STMicroelectronics\*\openocd*\bin\openocd.exe",
        "/usr/bin/openocd",
        "/usr/local/bin/openocd",
    )

    def __init__(self, interface="interface/stlink.cfg", target="target/stm32f4x.cfg",
                 exe=None, speed=None):
        self.exe = exe or find_tool("openocd", self.OPENOCD_PATTERNS)
        if not self.exe:
            raise IcError(
                "openocd nahi mila. STM32CubeIDE ke saath aata hai "
                "(C:\\ST\\...\\openocd\\bin\\openocd.exe) ya `winget install OpenOCD` "
                "se install karo, ya --exe se path do."
            )
        self.interface = interface
        self.target = target
        self.speed = speed

    # -- plumbing ------------------------------------------------------
    def _cmd(self, *commands, timeout=120):
        args = [self.exe]
        if self.interface:
            args += ["-f", self.interface]
        if self.target:
            args += ["-f", self.target]
        if self.speed:
            args += ["-c", "adapter speed %s" % self.speed]
        for command in commands:
            args += ["-c", command]
        return _run(args, timeout=timeout)

    def _session(self, command, timeout=120):
        return self._cmd("init", "halt", command, "shutdown", timeout=timeout)

    # -- API -----------------------------------------------------------
    def read(self, addr, count=1, size=4):
        cmd = {1: "mdb", 2: "mdh", 4: "mdw"}[size]
        out = self._session("%s 0x%08x %d" % (cmd, addr, count))
        values = _parse_md(out)
        if len(values) < count:
            raise IcError(
                "read failed (0x%08x, %d x %d bytes): %s"
                % (addr, count, size, out.strip()[-400:])
            )
        return values[:count]

    def write(self, addr, value, size=4):
        cmd = {1: "mwb", 2: "mwh", 4: "mww"}[size]
        self._session("%s 0x%08x 0x%08x" % (cmd, addr, value & 0xFFFFFFFF))

    def dump(self, addr, length, path):
        path = os.path.abspath(path)
        self._session('dump_image "%s" 0x%08x %d' % (path, addr, length))
        return path

    def load(self, path, addr=None):
        path = os.path.abspath(path)
        if path.lower().endswith((".elf", ".axf")):
            self._cmd("init", "halt", 'program "%s" verify reset exit' % path,
                      timeout=300)
            return
        if addr is None:
            raise IcError("binary image ke liye address chahiye (--addr)")
        self._cmd("init", "halt",
                  'load_image "%s" 0x%08x' % (path, addr),
                  "reset", "shutdown", timeout=300)

    def reset(self):
        self._cmd("init", "reset", "shutdown")

    def verify(self, path, addr=None):
        path = os.path.abspath(path)
        if path.lower().endswith((".elf", ".axf")):
            self._cmd("init", "halt", 'verify_image "%s"' % path, "shutdown",
                      timeout=300)
            return "verified %s" % path
        if addr is None:
            raise IcError("binary verify ke liye address chahiye (--addr)")
        self._cmd("init", "halt", 'verify_image "%s" 0x%08x' % (path, addr),
                  "shutdown", timeout=300)
        return "verified %s @ 0x%08x" % (path, addr)

    def mass_erase(self):
        self._cmd("init", "halt", "flash erase_sector 0 0 last", "reset",
                  "shutdown", timeout=300)
        return "mass erase done"

    def info(self):
        return self._cmd("init", "targets", "shutdown").strip()


class Stm8FlashBackend:
    """STM8 access through stm8flash (ST-Link) - dump/flash only."""

    name = "stm8flash"
    STM8FLASH_PATTERNS = (
        r"C:\stm8flash\stm8flash.exe",
        r"C:\tools\stm8flash\stm8flash.exe",
        "/usr/bin/stm8flash",
        "/usr/local/bin/stm8flash",
    )

    #: STM8S103F3 flash window used when `read()` has to slice a dump.
    FLASH_START = 0x8000
    FLASH_SIZE = 8 * 1024

    def __init__(self, part="stm8s103f3", programmer="stlinkv2", exe=None):
        self.exe = exe or find_tool("stm8flash", self.STM8FLASH_PATTERNS)
        if not self.exe:
            raise IcError(
                "stm8flash nahi mila. https://github.com/vdudouyt/stm8flash se "
                "build karke PATH me daalo, ya --exe se path do."
            )
        self.part = part
        self.programmer = programmer

    def _cmd(self, *args):
        return [self.exe, "-c", self.programmer, "-p", self.part, *args]

    def dump(self, addr, length, path):
        path = os.path.abspath(path)
        _run(self._cmd("-r", path))
        return path

    def load(self, path, addr=None):
        _run(self._cmd("-w", os.path.abspath(path)))

    def verify(self, path, addr=None):
        path = os.path.abspath(path)
        with open(path, "rb") as fh:
            blob = fh.read()
        flash = bytes(self.read(self.FLASH_START, len(blob), 1))
        if flash != blob:
            raise IcError("verify failed: %d bytes differ"
                         % sum(a != b for a, b in zip(flash, blob)))
        return "verified %s (%d bytes)" % (path, len(blob))

    def mass_erase(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "erased.bin")
            with open(path, "wb") as fh:
                fh.write(b"\xff" * self.FLASH_SIZE)
            _run(self._cmd("-w", path))
        return "mass erase done (0xFF fill)"

    def read(self, addr, count=1, size=4):
        if not (self.FLASH_START <= addr and
                addr + count * size <= self.FLASH_START + self.FLASH_SIZE):
            raise IcError(
                "stm8flash sirf flash dump kar sakta hai (0x%04x..0x%04x)"
                % (self.FLASH_START, self.FLASH_START + self.FLASH_SIZE)
            )
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "flash.bin")
            _run(self._cmd("-r", path))
            with open(path, "rb") as fh:
                blob = fh.read()
        start = addr - self.FLASH_START
        chunk = blob[start:start + count * size]
        values = []
        for i in range(0, len(chunk), size):
            values.append(int.from_bytes(chunk[i:i + size], "little"))
        return values

    def write(self, addr, value, size=4):
        raise IcError(
            "stm8flash word writes support nahi karta. `dump` se file nikalo, "
            "usko edit karo, phir `load`/`flash` se wapas likho."
        )

    def info(self):
        return "stm8flash: part=%s programmer=%s" % (self.part, self.programmer)


class SimBackend:
    """The simulated chip - same API, no hardware needed."""

    name = "sim"

    def __init__(self, board="f411re", elf=None):
        self.board = get_board(board)
        self.machine = Machine(self.board.name, trace=False)
        if elf:
            self.machine.load_elf(elf)

    def read(self, addr, count=1, size=4):
        return [self.machine.peek(addr + i * size, size) for i in range(count)]

    def write(self, addr, value, size=4):
        self.machine.poke(addr, size, value)

    def dump(self, addr, length, path):
        blob = bytes(self.machine.uc.mem_read(addr, length))
        with open(os.path.abspath(path), "wb") as fh:
            fh.write(blob)
        return os.path.abspath(path)

    def load(self, path, addr=None):
        with open(path, "rb") as fh:
            blob = fh.read()
        if addr is None:
            addr = self.board.flash_base
        self.machine.uc.mem_write(addr, blob)

    def reset(self):
        self.machine.reset()

    def verify(self, path, addr=None):
        with open(os.path.abspath(path), "rb") as fh:
            blob = fh.read()
        if addr is None:
            addr = self.board.flash_base
        flash = bytes(self.machine.uc.mem_read(addr, len(blob)))
        if flash != blob:
            raise IcError("verify failed: %d bytes differ" % sum(a != b for a, b in zip(flash, blob)))
        return "verified %s (%d bytes)" % (path, len(blob))

    def mass_erase(self):
        size = self.board.flash_size
        self.machine.uc.mem_write(self.board.flash_base, b"\xff" * size)
        return "mass erase done (simulated)"

    def info(self):
        return "sim: board=%s (Unicorn Cortex-M)" % self.board.name


def make_backend(args):
    """Build the back-end requested on the command line."""
    backend = getattr(args, "backend", "openocd")
    if backend == "sim":
        return SimBackend(getattr(args, "board", "f411re"), getattr(args, "elf", None))
    if backend == "stm8flash":
        return Stm8FlashBackend(
            getattr(args, "part", "stm8s103f3"),
            getattr(args, "programmer", "stlinkv2"),
            getattr(args, "exe", None),
        )
    return OpenOCDBackend(
        getattr(args, "interface", "interface/stlink.cfg"),
        getattr(args, "target", "target/stm32f4x.cfg"),
        getattr(args, "exe", None),
        getattr(args, "speed", None),
    )
