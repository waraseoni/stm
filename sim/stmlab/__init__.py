"""stmlab - a small STM32 instruction simulator plus a chip read/write CLI.

Typical use::

    python -m stmlab demo
    python -m stmlab run build/firmware.elf --ms 200
    python -m stmlab session build/firmware.elf
    python -m stmlab ic read 0x40023800
    python -m stmlab ic write 0x40020014 0x20
"""

from .boards import BOARDS, get_board
from .machine import Machine, MachineError

__all__ = ["BOARDS", "get_board", "Machine", "MachineError"]
__version__ = "0.1.0"
