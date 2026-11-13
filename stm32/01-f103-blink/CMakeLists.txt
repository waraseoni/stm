cmake_minimum_required(VERSION 3.20)

# ---------------------------------------------------------------------------
# 01-f103-blink  |  Blue Pill (STM32F103C8T6)  |  bare-metal, CMSIS only
# Build setup common/cmake/stm32_project.cmake me hai.
# ---------------------------------------------------------------------------
project(f103_blink C ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

include(../../common/cmake/stm32_project.cmake)

stm32_add_project(
  NAME   app
  BOARD  f103c8
  SOURCES src/main.c
)
