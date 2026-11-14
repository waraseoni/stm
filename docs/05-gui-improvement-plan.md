# stmlab GUI - improvement plan (hardware connect + UX redesign)

Goal: make the GUI a true "click-and-run" tool for beginners, including
hardware connection guidance (which port, baudrate, wiring) and a modern,
beginner-friendly UX. This is a plan only; implementation is tracked as
checkboxes.

Status: current GUI is a functional Tkinter tool with Simulator + IC tabs.
See `sim/stmlab/gui.py`.

---

## 1. Hardware connection wizard (new tab or first-run dialog)

Beginners do not know which COM port / baudrate / wiring to use. Add a
"Connect Hardware" wizard that detects and guides.

### 1.1 Auto-detect serial ports
- Use `pyserial` (optional dep) to list COM ports with descriptions.
- Show a dropdown: "ST-Link (COM5)", "CH340 (COM3)", etc.
- Detect ST-Link by VID/PID (0483:3748/374b/374e/374f/3752/3753).
- Button: "Refresh ports".

### 1.2 Wiring diagram panel
ASCII + (later) image diagrams per board:

**Nucleo-F411RE / F446RE (onboard ST-Link, no extra wiring needed for SWD)**
```
PC  --USB-->  Nucleo (CN1 ST-Link)   SWD done onboard
PC  --USB-->  Nucleo (CN? USART)      for printf @ 115200 8N1 (USART2 on PA2/PA3)
```
Pins:
- LED: PA5 (LD2)
- User button: PC13 (B1)
- UART TX: PA2, RX: PA3 (115200 8N1)

**Blue Pill (F103C8) + ST-Link V2**
```
ST-Link V2          Blue Pill
  3.3V  ---------->  3V3
  GND   ---------->  GND
  SWDIO ---------->  PA13 (DIO)
  SWCLK ---------->  PA14 (CLK)
  RST   ---------->  NRST (optional)
```
Boot: BOOT0=0 for flash, BOOT0=1 for system bootloader (UART PA9/PA10 @ 115200).
LED: PC13 (active low). Button: usually PA0 (user adds).

**STM8S103F3 minimum board + ST-Link V2 (SWIM)**
```
ST-Link V2          STM8 board
  3.3V  ---------->  3V3
  GND   ---------->  GND
  SWIM  ---------->  PD1 (SWIM)
  RST   ---------->  NRST (optional)
```
UART: PD5 (TX), PD6 (RX) @ 115200 8N1 (if used).

### 1.3 Baudrate selector
- Common values: 9600, 19200, 38400, 57600, 115200 (default), 230400, 460800, 921600.
- Hint: "Firmware default is 115200 (see USART BRR). Match this."

### 1.4 Connection test button
- "Test connection" runs `ic info` / `ic read 0xE000ED00` (CPUID) and shows PASS/FAIL with readable message.
- Green/red status indicator.

---

## 2. UX redesign (modern look)

### 2.1 Visual
- Use a cleaner theme: `ttk` with a modern style (clam + custom colors) or optional `sv_ttk`/`ttkbootstrap` (optional dep).
- Dark/light toggle.
- Larger fonts for beginners (11pt), generous padding, icons on buttons.
- Status bar with colored indicators (green=ready, orange=busy, red=error).
- Responsive layout (min window 900x640, resizable panes with `PanedWindow`).

### 2.2 Navigation
- Left sidebar with big buttons: Simulator, IC Tool, Hardware Setup, Logs, Settings, Help.
- Or keep tabs but add icons and tooltips.
- Breadcrumbs: "Simulator > f411re > firmware.elf".

### 2.3 Beginner-friendly
- First-run wizard: pick board, show wiring, test connection, then open main window.
- Tooltips on every control ("Peek reads a 1/2/4-byte value from an address").
- "What is this?" help button per tab opening `sim/README.md` section.
- Disable buttons that do not apply (e.g. Write on stm8flash backend) with tooltip explaining why.
- Confirm dialogs for destructive actions (flash, erase, reset).

### 2.4 Feedback
- Progress bar for long runs (flash, dump, run_ms with many instructions).
- Toast notifications for success (auto-dismiss 3s).
- Color-coded log: info (black), success (green), warning (orange), error (red).

---

## 3. New features (expert suggestions)

### 3.1 Simulator
- **Register explorer**: tree view of RCC/GPIO/USART/TIM/SysTick/NVIC with live values, click to edit.
- **Memory viewer**: hex dump view with ASCII column, navigate address, edit bytes.
- **Breakpoints**: set BP at address/symbol; run until hit; show source line if ELF has DWARF (optional `pyelftools` DWARF).
- **Watch expressions**: variable name -> address -> value, auto-refresh.
- **Oscilloscope/plot**: plot LED state, PWM duty, UART bytes over time (matplotlib optional; fallback to simple canvas).
- **Speed control**: slider for run speed (instructions per tick) + "run until UART contains text".
- **Snapshot/restore**: save machine state to file, reload later.
- **Multi-instance**: two simulators side by side (e.g. STM32 + virtual sensor).
- **Script console**: small Python REPL that can drive the machine (`m.poke(...)`, loops).

### 3.2 IC tool
- **Register name resolution**: type `RCC_CR` instead of `0x40023800` (parse CMSIS headers / SVD).
- **Live polling**: "watch" an address at N Hz, show value + change highlight.
- **Compare**: diff two dumps (before/after).
- **Flash verify**: after `load`, read back and compare.
- **Mass erase** button (with confirmation).
- **Option bytes** viewer (STM32).
- **Multi-probe selector** by serial number.
- **Session reuse**: keep OpenOCD alive between commands (gdbserver mode) for 10x speed.
- **Export**: CSV/JSON of reads.

### 3.3 Hardware integration
- **Serial monitor**: built-in UART terminal (pyserial) with baudrate selector, TX input, RX log, hex/ascii toggle, timestamps, save log.
- **SWD flash progress**: parse OpenOCD output, show % progress bar.
- **Board auto-detect**: identify connected board by CPUID + flash size.
- **Firmware drag-and-drop**: drop an ELF/bin onto the window to load/flash.

### 3.4 Learning aids
- **Guided exercises**: step-by-step panels for `01-blink`, `04-uart-printf`, etc., with "expected output" check.
- **Gotcha notes**: show `docs/*.md` snippets in a side panel.
- **Register bitfield tooltips**: hover on a bit shows its name and effect (from RM).
- **Diff viewer**: compare your bare-metal code with SPL/HAL equivalent.

---

## 4. Implementation phases

### Phase A (quick wins, 1-2 days)
- [ ] Connection wizard tab with port detection (pyserial optional) + wiring diagrams (ASCII).
- [ ] Baudrate selector + connection test button.
- [ ] Disable inapplicable buttons + tooltips.
- [ ] Dark/light theme toggle.
- [ ] Progress bar for run/dump/flash.
- [ ] Toast notifications + color-coded log.

### Phase B (medium, 3-5 days)
- [ ] Register explorer + memory viewer.
- [ ] Breakpoints + watch (address-based).
- [ ] Serial monitor tab (pyserial).
- [ ] Flash verify + mass erase.
- [ ] Register name resolution (CMSIS header parser).
- [ ] Guided exercise panel (load from `docs/` + `stm32/`/`stm8/`).

### Phase C (advanced, 1-2 weeks)
- [ ] Plotting (matplotlib optional) for LED/PWM/UART.
- [ ] DWARF source-level debug (pyelftools).
- [ ] Snapshot/restore.
- [ ] GDB remote stub integration.
- [ ] Multi-instance + scripting console.
- [ ] Packaging: PyInstaller `.exe` so end users need no Python install.

---

## 5. Dependencies (keep optional)

Core (already required): `unicorn`, `pyelftools`, `keystone-engine`, `tkinter` (built-in).

Optional (feature-gated, import with try/except):
- `pyserial` - serial monitor + port detection.
- `matplotlib` - plots.
- `sv_ttk` or `ttkbootstrap` - modern theme.
- `pyinstaller` - packaging (dev only).

Rule: the GUI must still work with only the core deps; optional features show
"install X to enable" instead of crashing.

---

## 6. Design notes for beginners

- Never show raw hex without context; always label (e.g. "RCC_CR = 0x... (HSIRDY set)").
- Default to safe actions; destructive actions (erase/flash) require confirmation + show what will happen.
- All long operations in background threads; UI never freezes.
- Errors in plain language + "what to try next".
- Remember last-used board/port/baudrate/paths (save to `~/.stmlab.json`).
- Provide a "Reset to defaults" button.

---

## 7. Success criteria

- A beginner with no CLI experience can: open GUI, pick board, see wiring, connect hardware, flash firmware, view UART, read a register, dump flash - all by clicking.
- GUI remains usable with only core deps installed.
- No UI freeze during any operation.
- Hardware connection errors produce actionable messages (not stack traces).

---

## 8. Out of scope (for now)

- Cycle-accurate simulation (use Renode/QEMU separately).
- IDE integration (VS Code extension) - later.
- Cloud/remote debugging.
- Mobile app.

---

## 9. Suggested first implementation

Start with **Phase A** items in this order:
1. Connection wizard + wiring diagrams + port detection.
2. Tooltips + disable inapplicable buttons.
3. Progress bar + toast notifications.
4. Dark/light theme.

Then move to Phase B (register explorer, serial monitor).

---

## 10. Pending work merged from `docs/03-plan.md` (master plan)

The GUI plan must not lose sight of the broader workspace goals. These pending
items are tracked in `docs/03-plan.md`; GUI features should support them.

### 10.1 Firmware learning (STM8 + STM32)
- **Phase 0 (blocking):** install SDCC + stm8flash + make; arm-none-eabi-gcc + cmake + ninja + openocd; run `setup-vendor.ps1`; verify first flash + UART on both boards.
- **Phase 1 STM8 (05-12):** GPIO input button, TIM2 PWM, EXTI, I2C EEPROM, ADC1, internal EEPROM, low-power, watchdog.
- **Phase 2 STM32 (07-14):** EXTI button, SysTick delay, TIM input capture, SPI flash, I2C, ADC+DMA, DAC (F446), USB CDC.
- **Phase 3:** HAL/LL + CubeMX mapping, SWD debug, FreeRTOS demo, bootloader sketch.
- GUI support needed: guided exercise panels, expected-output checks, serial monitor, register tooltips.

### 10.2 Simulator roadmap (`sim/stmlab`)
- **Near-term:** EXTI model, DMA minimal, SPI, I2C, ADC, TIM generalise (3/4/5), FPU decision, nested interrupts/priority, per-peripheral tick, instruction trace.
- **Mid-term:** GDB remote stub, snapshot/restore, coverage, `cmake --target sim`, CI (GitHub Actions).
- **Deferred:** Renode/QEMU for cycle-accurate sim.
- GUI support needed: breakpoint/watch UI, memory viewer, plot, snapshot buttons.

### 10.3 IC interface roadmap (`stmlab ic`)
- OpenOCD: flash write/verify, mass erase, option bytes.
- STM8: offset/length slicing (done), multi-probe by serial, config file.
- Session reuse (gdbserver mode), hex/ELF/S19 loaders, register name lookup via SVD/CMSIS.
- GUI support needed: flash verify button, mass erase (confirm), option bytes viewer, multi-probe dropdown, live polling.

### 10.4 Verification & quality
- Keep `sim/tests/` green on every commit.
- Add tests for each new peripheral model.
- "Silicon vs sim" checklist per exercise.
- Optional lint/format (`ruff`/`black`) for `sim/`.
- Document sim-vs-silicon differences in `sim/README.md`.

### 10.5 Immediate next actions (from master plan)
1. Install toolchains (Phase 0) - unblocks firmware verification.
2. Run first real build on `stm32/01-f103-blink` and `stm8/01-blink-pb5`, flash, capture UART.
3. Simulator: add EXTI model + test (needed for `07-exti-button`).
4. Push commits regularly.

### 10.6 Risks / notes (carried over)
- No compiler on this machine; firmware builds unverified.
- Keystone hangs on `;` comments (use `//` or `@`).
- Unicorn `WFI` is NOP; EXC_RETURN via trampoline; nested exceptions not supported.
- `run_ms` assumes 1 instr ≈ 1 cycle; use `--instr` for precise control.
- STM8 cannot be simulated by this core; use SDCC `ucsim`/`sstm8`.

### 10.7 Definition of done (per exercise, carried over)
- Code builds (when toolchain available).
- Flashed on real board, behaviour observed.
- Gotcha + register notes in `docs/`.
- Sim test added/updated and green (if applicable).
- Commit with `stm8:`/`stm32:`/`sim:` prefix, pushed.

---

## 11. Combined priority order (GUI + firmware + sim)

1. **Phase 0 toolchains** (blocks everything) - do first.
2. **GUI Phase A** (connection wizard, tooltips, progress, theme) - improves usability now.
3. **Simulator EXTI model + test** - unblocks `07-exti-button` exercises.
4. **First real build + flash** on both boards.
5. **GUI Phase B** (register explorer, serial monitor, flash verify).
6. **Phase 1/2 firmware exercises** with sim tests.
7. **GUI Phase C** (plotting, DWARF, packaging).