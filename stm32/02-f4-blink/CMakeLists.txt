cmake_minimum_required(VERSION 3.20)

# ---------------------------------------------------------------------------
# 02-f4-blink  |  Nucleo-F411RE / Nucleo-F446RE  |  bare-metal, CMSIS only
#
#   cmake --preset f411re      (ya f446re)
# ---------------------------------------------------------------------------
project(f4_blink C ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

set(BOARD "f411re" CACHE STRING "Target board: f411re | f446re")

if(BOARD STREQUAL "f411re")
  set(DEVICE_DEF  STM32F411xE)
  set(STARTUP     startup_stm32f411xe.s)
  set(LD_SCRIPT   ${CMAKE_CURRENT_LIST_DIR}/ld/STM32F411RE.ld)
  set(OPENOCD_CFG ${CMAKE_CURRENT_LIST_DIR}/openocd-f4.cfg)
elseif(BOARD STREQUAL "f446re")
  set(DEVICE_DEF  STM32F446xx)
  set(STARTUP     startup_stm32f446xx.s)
  set(LD_SCRIPT   ${CMAKE_CURRENT_LIST_DIR}/ld/STM32F446RE.ld)
  set(OPENOCD_CFG ${CMAKE_CURRENT_LIST_DIR}/openocd-f4.cfg)
else()
  message(FATAL_ERROR "BOARD '${BOARD}' unknown -- f411re ya f446re use karein")
endif()

set(VENDOR_DIR "${CMAKE_CURRENT_LIST_DIR}/../../vendor")
set(CMSIS_CORE "${VENDOR_DIR}/cmsis-core/Include")
set(DEVICE_DIR "${VENDOR_DIR}/cmsis-device-f4")

if(NOT EXISTS "${DEVICE_DIR}/Include/stm32f411xe.h")
  message(FATAL_ERROR
    "CMSIS device headers nahi mile: ${DEVICE_DIR}\n"
    "Workspace root se chalayein:  .\\setup-vendor.ps1")
endif()

message(STATUS "Board: ${BOARD}  (${DEVICE_DEF})")

add_executable(app
  src/main.c
  src/system_stm32f4xx.c
  ${DEVICE_DIR}/Source/Templates/gcc/${STARTUP}
)

target_include_directories(app PRIVATE
  src
  ${CMSIS_CORE}
  ${DEVICE_DIR}/Include
)

target_compile_definitions(app PRIVATE ${DEVICE_DEF})

target_compile_options(app PRIVATE
  -Wall -Wextra
  -Wno-unused-parameter
)

target_link_options(app PRIVATE
  -T${LD_SCRIPT}
  --specs=nano.specs
  --specs=nosys.specs
  -Wl,--gc-sections
  -Wl,-Map=${CMAKE_BINARY_DIR}/app.map
  -Wl,--print-memory-usage
)

add_custom_command(TARGET app POST_BUILD
  COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:app> ${CMAKE_BINARY_DIR}/app.bin
  COMMAND ${CMAKE_OBJCOPY} -O ihex   $<TARGET_FILE:app> ${CMAKE_BINARY_DIR}/app.hex
  COMMAND ${CMAKE_SIZE}   $<TARGET_FILE:app>
  COMMENT "objcopy -> app.bin / app.hex"
)

find_program(OPENOCD_EXE openocd)
if(OPENOCD_EXE)
  file(TO_CMAKE_PATH "${CMAKE_BINARY_DIR}/app.elf" _elf)
  add_custom_target(flash
    COMMAND ${OPENOCD_EXE} -f ${OPENOCD_CFG}
            -c "program ${_elf} verify reset exit"
    DEPENDS app
    COMMENT "OpenOCD: flashing app.elf"
    VERBATIM)

  add_custom_target(reset
    COMMAND ${OPENOCD_EXE} -f ${OPENOCD_CFG}
            -c "init; reset run; shutdown"
    COMMENT "OpenOCD: reset target"
    VERBATIM)
else()
  message(STATUS "openocd nahi mila -- 'flash' target available nahi hoga")
endif()
