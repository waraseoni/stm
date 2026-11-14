cmake_minimum_required(VERSION 3.20)

# ---------------------------------------------------------------------------
# 07-exti-button  |  Nucleo-F411RE / Nucleo-F446RE  |  bare-metal, CMSIS only
#
#   cmake --preset f411re      (ya f446re)
# NOTE: unverified on this machine (no ARM GCC installed). See docs/03-plan.md.
# ---------------------------------------------------------------------------
project(exti_button C ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

include(../../common/cmake/stm32_project.cmake)

set(BOARD "f411re" CACHE STRING "Target board: f411re | f446re")

stm32_add_project(
  NAME   app
  BOARD  ${BOARD}
  SOURCES src/main.c
)
