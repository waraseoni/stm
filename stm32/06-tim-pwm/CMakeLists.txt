cmake_minimum_required(VERSION 3.20)

# ---------------------------------------------------------------------------
# 06-tim-pwm  |  TIM2 CH1 (PA5) hardware PWM -- onboard LED fade
#
#   cmake --preset f411re      (ya f446re)
# ---------------------------------------------------------------------------
project(f4_tim_pwm C ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

include(../../common/cmake/stm32_project.cmake)

set(BOARD "f411re" CACHE STRING "Target board: f411re | f446re")

stm32_add_project(
  NAME   app
  BOARD  ${BOARD}
  SOURCES src/main.c
)
