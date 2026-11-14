# 05-gpio-input-button

Poll PA3 (input, pull-up) and toggle PB5 LED.

- Board: STM8S103F3P6 minimum system.
- Build: `make` (uses `../common.mk`)
- Flash: `make flash`
- Expected: press button -> LED toggles.

Status: **unverified** (no SDCC on this machine). Verify on hardware.