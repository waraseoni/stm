# STM-DEV: master plan (future work)

This file is the single source of truth for "what to do next" in this workspace.
It covers three parallel tracks:

1. **Firmware learning** (STM8 + STM32 bare-metal, the original goal).
2. **Simulator** (`sim/stmlab`): Unicorn-based Cortex-M core + peripheral models.
3. **IC interface** (`stmlab ic`): read/write/dump/load for real and simulated chips.

Cross-reference: `README.md` (progress), `docs/00-setup-windows.md` (toolchains),
`docs/01-stm8-notes.md`, `docs/02-stm32-notes.md`, `sim/README.md`.

---

## 0. Guiding principles

- **Register-first learning.** Every new peripheral: RM chapter -> bare-metal code -> compare with SPL/HAL/LL. Keep a "gotcha" line in `docs/`.
- **One exercise = one commit.** Prefix `stm8:` / `stm32:` / `sim:`. Branch per exercise optional.
- **Simulator is a helper, not the oracle.** It must never replace silicon verification for timing/DMA/peripheral edge cases. When sim and silicon disagree, silicon wins and sim gets a note/fix.
- **No new peripheral model without a test.** Add a mini-program or unit test in `sim/tests/`.
- **Keep `vendor/` and `tools/` gitignored.** Only source, docs, build files tracked.
- **Hinglish chat OK; code/docs/commits in English.**

---

## 1. Phase 0 - toolchains (BLOCKING, do first)

Nothing below can be *verified* until this is done. Estimated 1-2 days.

- [ ] Install **SDCC** + **stm8flash** + **make** (STM8 track).
- [ ] Install **arm-none-eabi-gcc** + **cmake** + **ninja** + **openocd** (STM32 track).
- [ ] Run `.\setup-vendor.ps1` to fetch CMSIS headers.
- [ ] Verify `stm8/01-blink-pb5`: `make` + `make flash`.
- [ ] Verify `stm32/01-f103-blink`: `cmake --preset debug && cmake --build build && cmake --build build --target flash`.
- [ ] Record exact versions in `docs/00-setup-windows.md` (winget/choco commands + paths).
- [ ] (Optional) Install **ST-Link V2** (V3 does not do STM8 SWIM).

Exit criteria: one successful flash + UART `printf` on each board.

---

## 2. Phase 1 - STM8 registers (bare-metal, SDCC)

Order (each = folder `stm8/0N-...` + README + notes):

1. `05-gpio-input-button` - PA3/PC? input, pull-up, debouncing.
2. `06-tim2-pwm` - PWM on PB? (TIM2 CH1), compare with TIM4.
3. `07-exti-button` - EXTI on button -> LED toggle.
4. `08-i2c-eeprom` - I2C master read/write 24Cxx.
5. `09-adc1` - ADC1 single conversion + interrupt.
6. `10-eeprom` - internal EEPROM read/write.
7. `11-low-power` - wait-for-interrupt / halt.
8. `12-watchdog` - IWDG.

Deliverables per exercise: `src/main.c`, `Makefile` (reuse `common.mk`), `README.md` (what/why/how to test), gotcha in `docs/01-stm8-notes.md`.

---

## 3. Phase 2 - STM32 bare-metal (CMSIS only, no HAL)

Order (folders `stm32/0N-...`):

1. `07-exti-button` - EXTI + debounce (F4 Nucleo user button PC13).
2. `08-systick-delay` - SysTick 1 ms + blocking delay.
3. `09-tim-input-capture` - TIM2 CH1 input capture (frequency measure).
4. `10-spi-flash` - SPI1 talk to W25Qxx (read ID).
5. `11-i2c-lcd` or `i2c-sensor` - I2C1 master.
6. `12-adc-dma` - ADC1 + DMA circular, UART print.
7. `13-dac` (F446) - DAC output + triangle.
8. `14-usb-cdc` (optional) - USB device CDC echo (LL/Cube).

Deliverables: CMake build (reuse presets), `main.c`, notes in `docs/02-stm32-notes.md`.

---

## 4. Phase 3 - HAL/LL + CubeMX

- Generate one project per peripheral with CubeMX; map generated code to Phase 2 bare-metal.
- SWD debug: breakpoints, watch, ITM/SWO trace.
- FreeRTOS one demo (LED blink tasks + UART mutex).
- Bootloader sketch (UART firmware update) - optional.

---

## 5. Simulator roadmap (`sim/stmlab`)

Current state: Cortex-M core + RCC/GPIO/USART/TIM2/SysTick/NVIC minimal. Tests green.

### 5.1 Near-term (high value, low effort)

- [ ] **EXTI** model (EXTI_IMR/RTSR/FTSR/PR, SYSCFG EXTICR) + IRQ injection for lines 0-15.
- [ ] **DMA** minimal: channel enable, transfer-complete IRQ, memory<->peripheral.
- [ ] **SPI** (SPI1/2): TX/RX FIFO stub + TXE/RXNE flags + interrupt.
- [ ] **I2C** (I2C1): basic master write/read state machine.
- [ ] **ADC** (ADC1): conversion on trigger, EOC flag, DR read.
- [ ] **TIM** generalise: TIM3/TIM4/TIM5 models (not just TIM2), capture/compare.
- [ ] **FPU/VFP** decision: either disable (document) or enable Unicorn VFP (UC_MODE_VFP). Recommend: document soft-float; revisit if needed.
- [ ] **Nested interrupts / priority**: basic priority ordering in `_inject_irq` (currently min()).
- [ ] **Better timing**: clamp chunks at SysTick/IRQ injection (done for SysTick); add per-peripheral tick.
- [ ] **Trace mode**: optional instruction-level trace to file for debugging.

### 5.2 Mid-term

- [ ] **GDB remote stub** (`gdbserver` over TCP) so VS Code can attach to the sim.
- [ ] **Snapshot/save-state**: dump/restore machine state for long tests.
- [ ] **Coverage**: which instructions/peripherals exercised.
- [ ] **Firmware build integration**: `cmake --target sim` that runs `stmlab run` after build.
- [ ] **CI**: GitHub Actions running `python -m unittest` on push.

### 5.3 Deferred

- Full system simulators (Renode/QEMU) for cycle-accurate timing, cache, DMA arbitration. Out of scope for this workspace; document how to add later.

---

## 6. IC interface roadmap (`stmlab ic`)

- [ ] **OpenOCD improvements**: flash write/verify helpers, mass erase, option bytes read.
- [ ] **STM8**: partial read via dump (done); add `--offset/--length` slicing (done via read()).
- [ ] **Multi-probe**: select by serial number (`--serial`).
- [ ] **Config file**: `~/.stmlab.toml` for default interface/target/part.
- [ ] **Session persistence**: keep OpenOCD alive across commands (gdbserver mode) for speed.
- [ ] **Hex/ELF/S19 loaders** for `ic load` (currently binary + ELF).
- [ ] **Register name lookup**: `ic read RCC_CR` via SVD/CMSIS headers (optional, parse `.svd`).

---

## 7. Verification & quality

- [ ] Keep `sim/tests/` green on every commit (`python -m unittest discover -s sim/tests -t sim`).
- [ ] Add tests for each new peripheral model (mini-program + assertions).
- [ ] Add a "silicon vs sim" checklist per exercise (what to compare: UART output, LED timing, PWM duty, IRQ count).
- [ ] Lint/format: `ruff` or `black` for `sim/` (optional).
- [ ] Document known sim-vs-silicon differences in `sim/README.md`.

---

## 8. Immediate next actions (pick one)

1. **Install toolchains** (Phase 0) - unblocks all firmware verification. Highest priority.
2. **Run first real build** on `stm32/01-f103-blink` and `stm8/01-blink-pb5`, flash, capture UART.
3. **Simulator: add EXTI model + test** (needed for `07-exti-button` exercises).
4. **Push** future commits regularly to `origin/master`.

---

## 9. Risks / notes

- This machine has **no compiler** (no SDCC/ARM GCC/cmake/ninja/openocd/stm8flash). All firmware builds are unverified; simulator tests only cover hand-assembled mini programs.
- Keystones's `Ks.asm` hangs on `;` comments (treated as statement separator) - use `//` or `@`. Documented in `sim/stmlab/mini.py`.
- Unicorn `WFI` is a NOP; `EXC_RETURN` handled via flash trampoline (manual unstack). Nested exceptions not supported.
- `run_ms` assumes 1 instr ≈ 1 cycle; real cores have multi-cycle instructions and wait states. Use `--instr` for precise control.
- STM8 cannot be simulated by this core; use SDCC `ucsim`/`sstm8`.

---

## 10. Definition of done (per exercise)

- [ ] Code builds (when toolchain available).
- [ ] Flashed on real board, behaviour observed (LED/UART/scope).
- [ ] Gotcha + register notes added to `docs/`.
- [ ] (If applicable) sim test added/updated and green.
- [ ] Commit with `stm8:`/`stm32:`/`sim:` prefix, pushed.
