cmake_minimum_required(VERSION 3.20)

# ---------------------------------------------------------------------------
# 03-clock-pll  |  Nucleo-F411RE -> 84 MHz, Nucleo-F446RE -> 180 MHz
#
#   cmake --preset f411re      (ya f446re)
# ---------------------------------------------------------------------------
project(f4_clock_pll C ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

include(../../common/cmake/stm32_project.cmake)

set(BOARD "f411re" CACHE STRING "Target board: f411re | f446re")

stm32_add_project(
  NAME   app
  BOARD  ${BOARD}
  SOURCES src/main.c
)
