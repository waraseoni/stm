# Implementation Plan — All Audit Findings (2026-11)

This plan converts every finding from the project audit (see chat history / `docs/03-plan.md`)
into concrete, trackable work. It supersedes the stale checkbox lists in `docs/03-plan.md` and
`docs/05-gui-improvement-plan.md` where they conflict.

**Branch strategy:** one branch per phase (`fix/ic-backend`, `fix/mcu-db`, `docs/sync`, ...).
Each phase ends with `python -m unittest discover -s sim/tests -t sim` green and a push.

**Status legend:** `[ ]` not started, `[~]` in progress, `[x]` done.

---

## Phase 0 — Setup reproducibility (blocks everything else)

- [ ] `sim/set-toolchain-env.ps1` (new): detect/install-on-PATH for
  - ARM GCC: `C:\Program Files (x86)\Arm GNU Toolchain arm-none-eabi\14.2 rel1\bin`
  - SDCC: `C:\Program Files\SDCC\bin`
  - OpenOCD (winget xpack) latest under `...\WinGet\Packages\xpack-dev-tools.openocd-xpack*\...\bin`
  - CMake/Ninja/make (winget packages)
  - Idempotent: only add paths that exist and are missing from `$env:PATH`; persist to user env via `[Environment]::SetEnvironmentVariable`.
- [ ] `sim/setup-toolchain-env.cmd` (new): calls the ps1, for double-click users.
- [ ] `sim/stmlab-gui.cmd` + `sim/create-shortcut.ps1`: resolve `pythonw` to absolute path (`(Get-Command pythonw -ErrorAction SilentlyContinue).Source`); fall back to `pyw`.
- [ ] `docs/00-setup-windows.md`: add “run `sim/set-toolchain-env.ps1` once” step before build; note ARM GCC is not auto-added to PATH by its installer.
- [ ] GUI: at startup, detect missing toolchains and show a non-blocking banner with a “Fix PATH” button that runs the ps1 (or opens it).
- [ ] Add `tools/README.md` (whitelisted by `.gitignore`) documenting portable-tool layout and the env script.

**Done when:** a fresh PowerShell (no manual PATH) can run
`cd stm32\01-f103-blink; cmake --preset debug; cmake --build build` successfully.

---

## Phase 1 — IC backend correctness (HIGH)

### 1.1 SimBackend ELF handling
- [ ] `ic.py:SimBackend.load`: if `path` ends with `.elf`/`.axf`, call `self.machine.load_elf(path)` instead of raw `mem_write`; otherwise keep raw binary behaviour.
- [ ] CLI `cmd_ic` `load`: pass `--elf` through to `SimBackend` constructor only when the positional file is not an ELF; document that `--elf` is for pre-loading before a binary write.
- [ ] GUI `do_load`: auto-detect extension and, for sim backend + ELF, call the ELF path (no addr needed); disable addr field in that case.
- [ ] Test: `test_sim_load_elf` — load `stm32/01-f103-blink/build/app`, assert first word == vector table (`0x20005000`-ish), not `0x464c457f`.

### 1.2 stm8flash verify for `.ihx`
- [ ] Add `Stm8FlashBackend._ihx_to_bin(path)`: parse Intel HEX into a flat binary at `FLASH_START`.
- [ ] `verify`: if path ends with `.ihx`, convert then compare; otherwise compare raw bytes.
- [ ] Test with a known-good `blink.ihx` round-trip on sim (mock backend).

### 1.3 stm8 dump slicing
- [ ] `Stm8FlashBackend.dump(addr, length, path)`: dump full flash to a temp file, then write only `blob[start:start+length]` to `path`; honour `addr`/`length` (current signature).
- [ ] Return actual byte count; CLI message already prints `args.length` — keep consistent.

### 1.4 stm8 mass_erase
- [ ] Read flash size from a part table (`STM8_FLASH_SIZE` map) instead of hardcoded 8 KB.
- [ ] Use `stm8flash -e` if supported, else keep 0xFF-fill as documented fallback; print which method was used.

### 1.5 CLI mass-erase confirmation
- [ ] `cmd_ic` mass-erase branch: prompt `Mass erase ALL flash? [y/N]`, abort on anything other than `y`/`yes`. Keep `--yes` flag to skip for scripting.
- [ ] GUI already confirms — no change.

### 1.6 Register-name resolution target-aware
- [ ] CLI: add `--family {f1,f4}` (or derive from `--target` filename: `stm32f1x.cfg`→f1) and pass to `resolve(name, board_or_family)`.
- [ ] `regmap.resolve`/`register_map`: accept either a sim board name or a family string (`"f1"`/`"f4"`); build a synthetic board-like object for address calculation.
- [ ] GUI IC tab: derive family from `target` string (`f1x`/`f0x`/...) and use it for register resolution instead of `board_name`.
- [ ] Test: `resolve('RCC_CR', 'f1') == 0x40021000`, `resolve('RCC_CR','f4') == 0x40023800`.

### 1.7 Sim IC persistence
- [ ] Option A (chosen): make `SimBackend` stateful within a single CLI invocation by adding `read`/`write`/`dump`/`load` already operate on one `Machine`; document that each `stmlab ic ...` call is a fresh chip (existing behaviour) — but add `stmlab ic session` (interactive) for multi-op workflows, OR
- [ ] Option B: cache the sim machine to `~/.stmlab-sim-state.json` between calls (complex). **Decision: Option A** — add `stmlab ic session` subcommand reusing the session loop, and document the limitation.

### 1.8 OpenOCD `.bin` load
- [ ] `OpenOCDBackend.load`: for non-ELF use `flash write_image erase "<path>" 0x...` instead of `load_image`.
- [ ] Keep `load_image` fallback only if `flash write_image` fails; log a warning.

### 1.9 OpenOCD winget path
- [ ] Add winget xpack patterns to `OPENOCD_PATTERNS` (glob `C:\Users\*\AppData\Local\Microsoft\WinGet\Packages\xpack-dev-tools.openocd-xpack*\...\bin\openocd.exe`).

**Done when:** all new tests pass; `ic load app.elf --backend sim` then `ic read 0x08000000` (same process via session) returns the vector table; F1 register name resolves to F1 address.

---

## Phase 2 — MCU database cleanup

- [ ] Remove 7 exact duplicate entries from `mcu_db.MCUS`.
- [ ] Add `equiv` coverage honestly: keep the 37 that have real drop-in equivalents; for the rest set `equiv=[]` (already) and ensure GUI shows “(no common drop-in equivalent listed)” (already does) — no change needed beyond dedup.
- [ ] Add a `sim_board` note: only `f103c8`, `f411re`, `f446re` are simulatable; document this in the DB header comment.
- [ ] GUI `on_mcu_selected`:
  - Set `backend_name` to `stm8flash` when `core == "STM8"`, else `openocd`.
  - Set `part` (STM8) from the selected part.
  - Replace dead `if m.get("interface"): pass` with real interface selection (`interface/stlink.cfg` default; `interface/wlink.cfg` for WCH).
  - If no `sim_board`, show a yellow note “not simulatable by stmlab (use real hardware)”.
- [ ] GUI: propagate MCU selection to Simulator and IC tabs (shared `mcu_name` or a callback `on_mcu_selected` → `sim_tab.board_name`/`ic_tab.target`/`ic_tab.backend_name`).
- [ ] `find()` dedup safety: `find` returns first match (fine after dedup).
- [ ] Tests: `test_mcu_db` — unique parts, required keys present, `target` not None for non-STM8/non-RISC-V, sim_board in `BOARDS` or None, no duplicate parts.

**Done when:** dropdown has 81 entries, no duplicates; selecting STM8S103 sets backend=stm8flash & part=stm8s103f3; selecting STM32F407 shows “not simulatable” note.

---

## Phase 3 — F1 peripheral model parity

- [ ] `machine.py:_make_peripherals`: for `rcc_kind == "f1"` instantiate
  - `SYSCFG`/`EXTI` at AFIO base `0x40010000`/`0x40010400` (F1 layout),
  - `DMA1` at `0x40020000`,
  - `ADC1` at `0x40012400`.
- [ ] `registers.py`: F1-aware EXTI/AFCIO/DMA/ADC base addresses; gate by `rcc_kind`.
- [ ] `regmap.py`: add F1 entries (EXTI_IMR/RTSR/FTSR/PR, AFIO_EXTICR, DMA1_ISR/IFCR, ADC1_SR/DR).
- [ ] `SPI`/`I2C` already at F1-correct bases (0x40013000 / 0x40005400) — verify.
- [ ] Test: F1 EXTI falling-edge IRQ end-to-end (port to `stm32/07` F1 variant or a mini-program).

**Done when:** an F1 EXTI mini-program toggles the LED in the simulator.

---

## Phase 4 — GUI state sync + one-click build

- [ ] Shared state: `StmlabGui` holds `current_mcu`, `current_board`; tabs subscribe via callbacks (not three independent StringVars for the same concept).
- [ ] “Build & Flash” button on Simulator tab: run `cmake --preset <board> && cmake --build build` in the chosen project folder (configurable project path), stream output to a log pane, then optionally `--target flash` via OpenOCD.
- [ ] Detect missing toolchains → disable button with tooltip.
- [ ] Settings: persist `project_path` (default `stm32/04-uart-printf`).
- [ ] `apply_theme`: also theme `Text`/`Listbox`/`Canvas` consistently (already mostly; audit `sv_ttk` fallback).

**Done when:** user can build+flash `04-uart-printf` from the GUI without a terminal.

---

## Phase 5 — Documentation sync

- [ ] `README.md`: remove stale “not installed” note; fix exercise counts (5 STM8 / 8 STM32 + 07/08); update folder map; tick Phase 0; add `docs/07` link.
- [ ] `sim/README.md`: fix limitations (DMA/SPI/I2C/ADC exist, F4-focused); fix tabs list; fix `stm8-dump` → `ic stm8-dump`; add “F1 vs F4 model parity” note.
- [ ] `docs/00-setup-windows.md`: add env script step; correct “stm8flash: NOT installed” → “no binary via winget; use STVP/OpenOCD/ucsim”.
- [ ] `docs/03-plan.md`: mark completed items `[x]` (toolchains, peripherals, GDB, snapshot, CI); keep genuinely pending ones.
- [ ] `docs/04-use-on-another-pc.md`: fix preset (`debug` only for 01; `f411re`/`f446re` otherwise); fix stm8 subcommands; update GUI feature list; add ucsim note.
- [ ] `docs/05-gui-improvement-plan.md`: mark completed items `[x]`; leave only genuinely pending (multi-instance, scripting console, full DWARF).
- [ ] `docs/06-exercise-templates.md`: remove “no ARM GCC” line; mark 07/08/05 as implemented.
- [ ] `stm32/README.md`: add 07/08 rows; add `03` README.
- [ ] `stm8/README.md`: fix 05 row (`05-gpio-input-button`); add ucsim usage.
- [ ] `stm32/03-clock-pll/README.md` (new): build/run notes.
- [ ] `stm32/07`, `08` source comments: remove stale “no ARM GCC” line (change to “verified build, unverified on hardware”).
- [ ] `docs/07` (this file) kept in sync as phases complete.

---

## Phase 6 — Tests + CI

- [ ] `sim/tests/test_mcu_db.py`: dedup, keys, target validity, sim_board validity.
- [ ] `sim/tests/test_regmap.py`: F1/F4 address expectations.
- [ ] `sim/tests/test_ic_sim.py`: ELF load, read/write roundtrip within one backend instance, dump slicing.
- [ ] `sim/tests/test_cli_smoke.py`: `--help`, `boards`, `ic read ... --backend sim`.
- [ ] GDB stub: minimal RSP test (attach, `g`, `m`, breakpoint, continue) — reuse existing raw client if present.
- [ ] CI: add `firmware` job — `apt install gcc-arm-none-eabi sdcc cmake ninja-build`, run `setup-vendor.ps1` (pwsh), build all 8 STM32 + 5 STM8, upload artifacts on failure.
- [ ] Optional: `ruff` check in CI (non-blocking initially).

**Done when:** `python -m unittest discover` shows ≥ 30 tests, all green; CI green on a clean clone.

---

## Phase 7 — Packaging & legal

- [ ] Add `LICENSE` (recommend MIT for the project code; note dependency licenses separately).
- [ ] Add `pyproject.toml`: project metadata, `requires-python = ">=3.10"`, optional extras `[serial]`, `[plot]`, `[theme]`, console script `stmlab = stmlab.cli:main`, gui entrypoint.
- [ ] `requirements.txt`: keep core; add `requirements-optional.txt` for pyserial/matplotlib/sv_ttk/ttkbootstrap.
- [ ] Verify PyInstaller build end-to-end on a machine without Python (test in a VM or clean user account); document any missing data files (unicorn/keystone DLLs).
- [ ] Add dependency-license notice file (`THIRD_PARTY_LICENSES.md`) listing unicorn/keystone/pyelftools.

**Done when:** `pip install -e .` works; `stmlab` runs without `PYTHONPATH`; exe launches on a clean Windows user account.

---

## Phase 8 — STM8 simulation + remaining exercises (stretch)

- [ ] `stmlab stm8-sim <file.ihx>` wrapper around `ucsim_stm8` with `-t <mcu>` and a timeout; document in `sim/README.md`.
- [ ] Implement remaining templates from `docs/06` as actual folders: `09-tim-input-capture`, `10-spi-flash`, etc. (STM32) and `05-i2c-ssd1306`, `06-adc-scan`, `07-eeprom`, `08-pwm-motor` (STM8).
- [ ] STM8 OpenOCD backend (optional, for users without stm8flash) reusing `target/stm8s103.cfg`.

---

## Cross-cutting acceptance (final sign-off)

- [ ] `python -m unittest discover -s sim/tests -t sim` → all green.
- [ ] Fresh shell: `set-toolchain-env.ps1` then build all 13 firmware projects → 0 errors.
- [ ] GUI launches via desktop shortcut on a clean account; MCU selector has 81 unique entries; selecting STM8 sets stm8flash backend.
- [ ] `stmlab ic read RCC_CR --backend sim --board f103c8` → `0x40021000`.
- [ ] `stmlab ic load <elf> --backend sim` then read vector table → correct.
- [ ] All docs reflect installed toolchain versions and verified builds.
- [ ] CI green on `master`.

---

## Tracking

Update checkboxes in this file as work lands. Each completed phase → commit with prefix
`sim:` / `stm32:` / `stm8:` / `docs:` and push to `https://github.com/waraseoni/stm.git`.
