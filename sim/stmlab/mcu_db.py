"""MCU database: STM32/STM8 parts plus pin/code-compatible equivalents.

Used by the GUI/CLI to auto-fill OpenOCD target/interface and to show
which parts from other vendors can replace an STM part.

Equivalence notes are "typical drop-in" hints only - always verify the
datasheet, pinout and errata before swapping parts.
"""

# Each entry:
#  vendor, family, part, core, flash_kb, ram_kb, package, target (OpenOCD),
#  interface, sim_board (or None), equiv: list of (vendor, part, note)
MCUS = [
    # ---------- STM32F1 (Cortex-M3) ----------
    {"vendor": "ST", "family": "STM32F1", "part": "STM32F103C8T6", "core": "Cortex-M3",
     "flash_kb": 64, "ram_kb": 20, "package": "LQFP48",
     "target": "target/stm32f1x.cfg", "sim_board": "f103c8",
     "equiv": [("GigaDevice", "GD32F103C8T6", "pin/code compatible"),
               ("MindMotion", "MM32F103C8T6", "similar"),
               ("Geehy", "APM32F103CBT6", "similar"),
               ("WCH", "CH32F103C8T6", "similar")]},
    {"vendor": "ST", "family": "STM32F1", "part": "STM32F103CBT6", "core": "Cortex-M3",
     "flash_kb": 128, "ram_kb": 20, "package": "LQFP48",
     "target": "target/stm32f1x.cfg", "sim_board": None,
     "equiv": [("GigaDevice", "GD32F103CBT6", "pin/code compatible")]},
    {"vendor": "ST", "family": "STM32F1", "part": "STM32F103RBT6", "core": "Cortex-M3",
     "flash_kb": 128, "ram_kb": 20, "package": "LQFP64",
     "target": "target/stm32f1x.cfg", "sim_board": None,
     "equiv": [("GigaDevice", "GD32F103RBT6", "pin/code compatible")]},
    {"vendor": "ST", "family": "STM32F1", "part": "STM32F103VET6", "core": "Cortex-M3",
     "flash_kb": 512, "ram_kb": 64, "package": "LQFP100",
     "target": "target/stm32f1x.cfg", "sim_board": None,
     "equiv": [("GigaDevice", "GD32F103VET6", "pin/code compatible")]},
    {"vendor": "ST", "family": "STM32F1", "part": "STM32F103ZET6", "core": "Cortex-M3",
     "flash_kb": 512, "ram_kb": 64, "package": "LQFP144",
     "target": "target/stm32f1x.cfg", "sim_board": None,
     "equiv": [("GigaDevice", "GD32F103ZET6", "pin/code compatible")]},

    # ---------- STM32F4 (Cortex-M4) ----------
    {"vendor": "ST", "family": "STM32F4", "part": "STM32F401CCU6", "core": "Cortex-M4",
     "flash_kb": 256, "ram_kb": 64, "package": "UFQFPN48",
     "target": "target/stm32f4x.cfg", "sim_board": None,
     "equiv": [("GigaDevice", "GD32F405CG", "similar")]},
    {"vendor": "ST", "family": "STM32F4", "part": "STM32F407VGT6", "core": "Cortex-M4",
     "flash_kb": 1024, "ram_kb": 192, "package": "LQFP100",
     "target": "target/stm32f4x.cfg", "sim_board": None,
     "equiv": [("GigaDevice", "GD32F407VGT6", "pin/code compatible")]},
    {"vendor": "ST", "family": "STM32F4", "part": "STM32F411CEU6", "core": "Cortex-M4",
     "flash_kb": 512, "ram_kb": 128, "package": "UFQFPN48",
     "target": "target/stm32f4x.cfg", "sim_board": None,
     "equiv": [("GigaDevice", "GD32F450? no", "no direct; check GD32F405")]},
    {"vendor": "ST", "family": "STM32F4", "part": "STM32F411RE", "core": "Cortex-M4",
     "flash_kb": 512, "ram_kb": 128, "package": "LQFP64",
     "target": "target/stm32f4x.cfg", "sim_board": "f411re",
     "equiv": [("GigaDevice", "GD32F405RG", "similar core/peripherals")]},
    {"vendor": "ST", "family": "STM32F4", "part": "STM32F446RE", "core": "Cortex-M4",
     "flash_kb": 512, "ram_kb": 128, "package": "LQFP64",
     "target": "target/stm32f4x.cfg", "sim_board": "f446re",
     "equiv": [("GigaDevice", "GD32F450RE", "similar")]},
    {"vendor": "ST", "family": "STM32F4", "part": "STM32F429ZIT6", "core": "Cortex-M4",
     "flash_kb": 2048, "ram_kb": 256, "package": "LQFP144",
     "target": "target/stm32f4x.cfg", "sim_board": None,
     "equiv": [("GigaDevice", "GD32F450ZI", "similar")]},

    # ---------- STM32F0 / F3 / F7 / H7 / L4 / G0 / G4 / U5 ----------
    {"vendor": "ST", "family": "STM32F0", "part": "STM32F030F4P6", "core": "Cortex-M0",
     "flash_kb": 16, "ram_kb": 4, "package": "TSSOP20",
     "target": "target/stm32f0x.cfg", "sim_board": None,
     "equiv": [("GigaDevice", "GD32F130F4", "similar low-end")]},
    {"vendor": "ST", "family": "STM32F0", "part": "STM32F072RB", "core": "Cortex-M0",
     "flash_kb": 128, "ram_kb": 16, "package": "LQFP64",
     "target": "target/stm32f0x.cfg", "sim_board": None, "equiv": []},
    {"vendor": "ST", "family": "STM32F3", "part": "STM32F303K8", "core": "Cortex-M4",
     "flash_kb": 64, "ram_kb": 12, "package": "LQFP32",
     "target": "target/stm32f3x.cfg", "sim_board": None,
     "equiv": [("GigaDevice", "GD32F303K8", "similar")]},
    {"vendor": "ST", "family": "STM32F7", "part": "STM32F767ZI", "core": "Cortex-M7",
     "flash_kb": 2048, "ram_kb": 512, "package": "LQFP144",
     "target": "target/stm32f7x.cfg", "sim_board": None, "equiv": []},
    {"vendor": "ST", "family": "STM32H7", "part": "STM32H743ZI", "core": "Cortex-M7",
     "flash_kb": 2048, "ram_kb": 1024, "package": "LQFP144",
     "target": "target/stm32h7x.cfg", "sim_board": None, "equiv": []},
    {"vendor": "ST", "family": "STM32L4", "part": "STM32L432KC", "core": "Cortex-M4",
     "flash_kb": 256, "ram_kb": 64, "package": "UFQFPN32",
     "target": "target/stm32l4x.cfg", "sim_board": None, "equiv": []},
    {"vendor": "ST", "family": "STM32L4", "part": "STM32L476RG", "core": "Cortex-M4",
     "flash_kb": 1024, "ram_kb": 128, "package": "LQFP64",
     "target": "target/stm32l4x.cfg", "sim_board": None, "equiv": []},
    {"vendor": "ST", "family": "STM32G0", "part": "STM32G030F6P6", "core": "Cortex-M0+",
     "flash_kb": 32, "ram_kb": 8, "package": "TSSOP20",
     "target": "target/stm32g0x.cfg", "sim_board": None, "equiv": []},
    {"vendor": "ST", "family": "STM32G4", "part": "STM32G431CB", "core": "Cortex-M4",
     "flash_kb": 128, "ram_kb": 32, "package": "UFQFPN48",
     "target": "target/stm32g4x.cfg", "sim_board": None, "equiv": []},
    {"vendor": "ST", "family": "STM32U5", "part": "STM32U575ZI", "core": "Cortex-M33",
     "flash_kb": 2048, "ram_kb": 768, "package": "LQFP144",
     "target": "target/stm32u5x.cfg", "sim_board": None, "equiv": []},
    {"vendor": "ST", "family": "STM32WB", "part": "STM32WB55CE", "core": "Cortex-M4+M0+",
     "flash_kb": 512, "ram_kb": 256, "package": "UFQFPN48",
     "target": "target/stm32wbx.cfg", "sim_board": None, "equiv": []},
    {"vendor": "ST", "family": "STM32WL", "part": "STM32WL55CC", "core": "Cortex-M4",
     "flash_kb": 256, "ram_kb": 64, "package": "UFQFPN48",
     "target": "target/stm32wlx.cfg", "sim_board": None, "equiv": []},

    # ---------- STM8 ----------
    {"vendor": "ST", "family": "STM8S", "part": "STM8S003F3P6", "core": "STM8",
     "flash_kb": 8, "ram_kb": 1, "package": "TSSOP20",
     "target": None, "sim_board": None,
     "equiv": [("STC", "STC15W204S", "different core, not drop-in"),
               ("Nuvoton", "NUVOTON MS51", "different core")]},
    {"vendor": "ST", "family": "STM8S", "part": "STM8S103F3P6", "core": "STM8",
     "flash_kb": 8, "ram_kb": 1, "package": "TSSOP20",
     "target": None, "sim_board": None, "equiv": []},
    {"vendor": "ST", "family": "STM8S", "part": "STM8S105K4T6", "core": "STM8",
     "flash_kb": 16, "ram_kb": 2, "package": "LQFP32",
     "target": None, "sim_board": None, "equiv": []},
    {"vendor": "ST", "family": "STM8L", "part": "STM8L151G4U6", "core": "STM8",
     "flash_kb": 16, "ram_kb": 2, "package": "UFQFPN28",
     "target": None, "sim_board": None, "equiv": []},
    {"vendor": "ST", "family": "STM8L", "part": "STM8L152R8T6", "core": "STM8",
     "flash_kb": 64, "ram_kb": 4, "package": "LQFP64",
     "target": None, "sim_board": None, "equiv": []},
    {"vendor": "ST", "family": "STM8AF", "part": "STM8AF5288T", "core": "STM8",
     "flash_kb": 64, "ram_kb": 4, "package": "LQFP64",
     "target": None, "sim_board": None, "equiv": []},
]


def find(part):
    part = part.strip().upper()
    for m in MCUS:
        if m["part"].upper() == part:
            return m
    return None


def search(text):
    text = text.strip().lower()
    out = []
    for m in MCUS:
        if (text in m["part"].lower() or text in m["family"].lower()
                or text in m["vendor"].lower()):
            out.append(m)
    return out


def equivalents(part):
    m = find(part)
    if not m:
        return []
    return m.get("equiv", [])


def families():
    return sorted({m["family"] for m in MCUS})


def vendors():
    return sorted({m["vendor"] for m in MCUS})