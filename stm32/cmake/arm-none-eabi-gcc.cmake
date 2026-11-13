# ARM GNU toolchain (bare-metal) -- ek hi file dono families ke liye.
#
# Use:
#   cmake -S . -B build -G Ninja \
#         -DCMAKE_TOOLCHAIN_FILE=../cmake/arm-none-eabi-gcc.cmake \
#         -DCPU=cortex-m3
#
# CPU: cortex-m0 | cortex-m0plus | cortex-m3 | cortex-m4 | cortex-m7
# FPU: khali chhodne par soft-float. F4 FPU chahiye to -DFPU=fpv4-sp-d16

set(CMAKE_SYSTEM_NAME      Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)

# Cross compiler ko test program link karne ki zaroorat nahi
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

set(CPU "cortex-m3" CACHE STRING "Target Cortex-M core")
set(FPU ""          CACHE STRING "FPU jaise fpv4-sp-d16 (khali = soft float)")

find_program(ARM_GCC arm-none-eabi-gcc REQUIRED
             DOC "arm-none-eabi-gcc (PATH me hona chahiye)")

set(CMAKE_C_COMPILER   "${ARM_GCC}")
set(CMAKE_ASM_COMPILER "${ARM_GCC}")

get_filename_component(_arm_bin "${ARM_GCC}" DIRECTORY)
file(TO_CMAKE_PATH "${_arm_bin}" _arm_bin)
set(CMAKE_OBJCOPY "${_arm_bin}/arm-none-eabi-objcopy" CACHE FILEPATH "")
set(CMAKE_SIZE    "${_arm_bin}/arm-none-eabi-size"    CACHE FILEPATH "")
set(CMAKE_GDB     "${_arm_bin}/arm-none-eabi-gdb"     CACHE FILEPATH "")

set(_arch "-mcpu=${CPU} -mthumb")
if(FPU)
  string(APPEND _arch " -mfpu=${FPU} -mfloat-abi=hard")
else()
  string(APPEND _arch " -mfloat-abi=soft")
endif()

# -ffunction-sections/-fdata-sections + --gc-sections = per-function dead code removal
set(CMAKE_C_FLAGS_INIT            "${_arch} -ffunction-sections -fdata-sections -fno-common")
set(CMAKE_ASM_FLAGS_INIT          "${_arch}")
set(CMAKE_CXX_FLAGS_INIT          "${CMAKE_C_FLAGS_INIT}")
set(CMAKE_EXE_LINKER_FLAGS_INIT   "${_arch}")

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
