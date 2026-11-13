# stm32/ — projects

Naming: `NN-topic`, jaise `01-baremetal-blink`, `02-uart-printf`, `03-tim-pwm`.

Do flavours rakhenge, isi order me:

1. **baremetal/** — sirf CMSIS, apna startup + linker script, register writes.
   Yahi asli learning hai.
2. **hal/** — CubeMX generated + HAL. Yahan comparison karenge: "HAL ne mera
   bare-metal code kaise likha?".

Board select hone ke baad templates yahan add honge:
- F103C8T6 (Blue Pill) -> `stm32/f103/`
- Nucleo-F411/F446    -> `stm32/f4/`

## Common build (plan)

```
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Debug
cmake --build build
openocd -f interface/stlink.cfg -f target/stm32f1x.cfg \
        -c "program build/app.elf verify reset exit"
```
