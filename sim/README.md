# stmlab - STM32 simulator + IC read/write CLI

`stmlab` is a small, Python-based tool for this workspace:

- **Simulator**: runs Cortex-M3/M4 Thumb firmware images (ELF) on a Unicorn CPU core with minimal peripheral models, so you can test basic firmware logic without hardware.
- **IC interface**: a single CLI that can read/write/dump memory on a real chip (via OpenOCD / stm8flash) or on the simulated chip.

It is intentionally lightweight (register-level models, approximate timing). It is **not** a full Renode/QEMU replacement.

## Setup

```powershell
cd sim
python -m pip install -r requirements.txt
```

Requires Python 3.10+ (tested on 3.14). On Windows you can run commands as:

```powershell
$env:PYTHONPATH="C:\next-vtech\stm-dev\sim"
python -m stmlab <command>
# or
.\sim\stmlab.cmd <command>
```

## GUI (click-and-run, no command line)

Beginners ke liye ek Tkinter GUI bhi hai - double-click karo, command nahi chahiye.

- Desktop par **"stmlab GUI"** shortcut (auto-created) ya `sim\stmlab-gui.cmd` double-click karo.
- Ya manually: `$env:PYTHONPATH="C:\next-vtech\stm-dev\sim"; python -m stmlab.gui`
- Tabs:
  - **Hardware**: board select, serial port auto-detect, baudrate, wiring diagram, connection test (openocd/stm8flash).
  - **Simulator**: board/ELF load, Run/Step/Reset, UART output, peek/poke, RX inject.
  - **IC Read/Write**: sim/openocd/stm8flash backend, read/write/dump/load/info/reset.
- Dark/light theme toggle (View menu), tooltips, progress bar, toast notifications.
- Sab heavy kaam background thread me hota hai, UI hang nahi hota.

## Simulator

### Quick demo (no ARM toolchain needed)

```powershell
python -m stmlab demo --board f411re --trace
python -m stmlab boards
```

The demo uses a hand-assembled program (keystone) that prints `Hi from stmlab` over the modelled USART and toggles the board LED from a SysTick interrupt.

### Run a real firmware ELF

```powershell
python -m stmlab run path\to\firmware.elf --board f411re --ms 200
python -m stmlab run path\to\firmware.elf --board f103c8 --instr 500000 --trace
```

- Build firmware with the workspace presets (ARM GCC, `-mcpu=cortex-m4 -mthumb` soft-float by default). Load the `.elf` from the build directory.
- Time model: ~1 instruction ≈ 1 core clock cycle at `SystemCoreClock` (falls back to the board default HSI clock). Timing is approximate.

### Interactive session

```powershell
python -m stmlab session path\to\firmware.elf --board f411re
```

Commands inside the session: `run [ms]`, `step [n]`, `regs`, `peek ADDR [SZ]`, `poke ADDR VAL [SZ]`, `uart`, `rx TEXT|hex:..`, `button 0|1`, `irq N`, `events`, `symbols [PATTERN]`, `reset`, `info`, `help`, `quit`.

### Modelled peripherals (current)

- RCC: ready/switch flags auto-complete (HSI/HSE/PLL/VOS/OD) so firmware wait loops finish.
- GPIO: MODER/ODR/IDR/BSRR/BRR (F4 and F1 register layouts), LED and pin-change events.
- USART (USART2 on F4, USART1 on F103): TX captured to UART log, RXNE/RXDR read, RXNEIE interrupt injection via `inject_uart_rx`.
- TIM2: basic registers + CCR1/ARR duty tracking.
- SysTick: CTRL/LOAD/VAL/COUNTFLAG, tick interrupt (exception 15).
- NVIC: ISER/ICER/ISPR/ICPR (minimal), VTOR.

Interrupts are injected at instruction-slice boundaries (not cycle-exact). `WFI` is treated as a NOP; EXC_RETURN is handled via a flash trampoline. **FPU/VFP instructions are not supported** (build with soft-float ABI). Decision: keep soft-float only; enabling VFP in Unicorn would require FPU register save/restore in the exception frame and is deferred (see `docs/03-plan.md` 5.1).

## IC read/write interface

The `ic` subcommands talk to a backend with a uniform API.

### Simulated chip

```powershell
python -m stmlab ic read 0x40023800 --backend sim --board f411re
python -m stmlab ic write 0x40020014 0x20 --backend sim --board f411re
python -m stmlab ic dump 0x08000000 --length 256 --out flash.bin --backend sim --board f411re
```

### Real STM32 (OpenOCD + ST-Link)

```powershell
python -m stmlab ic read 0x40023800 -n 4 --backend openocd --interface interface/stlink.cfg --target target/stm32f4x.cfg
python -m stmlab ic write 0x40020014 0x20 --backend openocd --target target/stm32f4x.cfg
python -m stmlab ic dump 0x08000000 --length 0x800 --out flash.bin --backend openocd --target target/stm32f4x.cfg
python -m stmlab ic load build\firmware.elf --backend openocd --target target/stm32f4x.cfg
python -m stmlab ic info --backend openocd --target target/stm32f4x.cfg
```

`--exe` can point to `openocd.exe` if it is not on PATH (CubeIDE bundles it under `C:\ST\...`).

### Real STM8 (stm8flash)

```powershell
python -m stmlab stm8-dump flash.bin --part stm8s103f3 --programmer stlinkv2
python -m stmlab stm8-flash blink.ihx --part stm8s103f3 --programmer stlinkv2
```

`stm8flash` operates on whole flash images; arbitrary register word-writes are not supported by that backend.

## STM8 simulation

A Python Cortex-M simulator cannot run STM8 code. For STM8 firmware testing without hardware, use SDCC's `ucsim`/`sstm8` (not bundled here):

```powershell
# build, then simulate (example - requires ucsim/sstm8 installed)
sstm8 build\firmware.ihx
```

You can still use `stmlab stm8-dump` / `stmlab stm8-flash` with a real ST-Link.

## Limitations

- Approximate timing and simplified peripherals; behaviour may differ from silicon.
- No FPU/VFP, no DMA, no I2C/SPI/ADC/CAN/USB models yet.
- Interrupt priorities/nesting are minimal.
- Flash/option-byte programming semantics are not modelled.
- Real-chip backends depend on external tools (`openocd`, `stm8flash`) and a debug probe.

## Tests

```powershell
$env:PYTHONPATH="C:\next-vtech\stm-dev\sim"
python -m unittest discover -s sim/tests -t sim -v
```

Tests use keystone-assembled mini programs and run without an ARM GCC toolchain.
