cmake_minimum_required(VERSION 3.20)

# ---------------------------------------------------------------------------
# 01-f103-blink  |  Blue Pill (STM32F103C8T6)  |  bare-metal, CMSIS only
# ---------------------------------------------------------------------------
project(f103_blink C ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# vendor/ workspace root par hai: stm32/01-f103-blink -> ../../vendor
set(VENDOR_DIR  "${CMAKE_CURRENT_LIST_DIR}/../../vendor")
set(CMSIS_CORE  "${VENDOR_DIR}/cmsis-core/Include")
set(DEVICE_DIR  "${VENDOR_DIR}/cmsis-device-f1")

if(NOT EXISTS "${DEVICE_DIR}/Include/stm32f103xb.h")
  message(FATAL_ERROR
    "CMSIS device headers nahi mile: ${DEVICE_DIR}\n"
    "Workspace root se chalayein:  .\\setup-vendor.ps1")
endif()

add_executable(app
  src/main.c
  src/system_stm32f1xx.c
  ${DEVICE_DIR}/Source/Templates/gcc/startup_stm32f103xb.s
)

target_include_directories(app PRIVATE
  src
  ${CMSIS_CORE}
  ${DEVICE_DIR}/Include
)

target_compile_definitions(app PRIVATE STM32F103xB)

target_compile_options(app PRIVATE
  -Wall -Wextra
  -Wno-unused-parameter
)

target_link_options(app PRIVATE
  -T${CMAKE_CURRENT_LIST_DIR}/ld/STM32F103C8Tx.ld
  --specs=nano.specs
  --specs=nosys.specs
  -Wl,--gc-sections
  -Wl,-Map=${CMAKE_BINARY_DIR}/app.map
  -Wl,--print-memory-usage
)

# .elf ke saath .bin aur .hex bhi banao (ST-Link Utility / DFU ke liye)
add_custom_command(TARGET app POST_BUILD
  COMMAND ${CMAKE_OBJCOPY} -O binary  $<TARGET_FILE:app> ${CMAKE_BINARY_DIR}/app.bin
  COMMAND ${CMAKE_OBJCOPY} -O ihex    $<TARGET_FILE:app> ${CMAKE_BINARY_DIR}/app.hex
  COMMAND ${CMAKE_SIZE}    $<TARGET_FILE:app>
  COMMENT "objcopy -> app.bin / app.hex"
)

# --- flash via OpenOCD (ST-Link) -------------------------------------------
find_program(OPENOCD_EXE openocd)
if(OPENOCD_EXE)
  file(TO_CMAKE_PATH "${CMAKE_BINARY_DIR}/app.elf" _elf)
  add_custom_target(flash
    COMMAND ${OPENOCD_EXE}
            -f ${CMAKE_CURRENT_LIST_DIR}/openocd.cfg
            -c "program ${_elf} verify reset exit"
    DEPENDS app
    COMMENT "OpenOCD: flashing app.elf"
    VERBATIM)

  add_custom_target(reset
    COMMAND ${OPENOCD_EXE} -f ${CMAKE_CURRENT_LIST_DIR}/openocd.cfg
            -c "init; reset run; shutdown"
    COMMENT "OpenOCD: reset target"
    VERBATIM)
else()
  message(STATUS "openocd nahi mila -- 'flash' target available nahi hoga")
endif()
