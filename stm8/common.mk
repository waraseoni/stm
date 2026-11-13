# ---------------------------------------------------------------------------
# stm8/common.mk -- saare STM8 projects ka shared SDCC build.
#
# Project Makefile:
#   TARGET = blink
#   MCU    = stm8s103f3
#   include ../common.mk
# ---------------------------------------------------------------------------

MCU     ?= stm8s103f3
TARGET  ?= blink
SRC     ?= main.c

# GNU make ka built-in CC=cc hota hai, isliye `CC ?= sdcc` kaam nahi karta.
# Sirf tab override karo jab CC ne kuch custom set na kiya ho.
ifeq ($(origin CC),default)
CC = sdcc
endif
CFLAGS  ?= -mstm8 --std-c99 --opt-code-speed --out-fmt-ihx
FLASHER ?= stm8flash
STLINK  ?= stlinkv2

all: $(TARGET).ihx

$(TARGET).ihx: $(SRC)
	$(CC) $(CFLAGS) -o $@ $(SRC)

# Flash + verify + reset
flash: $(TARGET).ihx
	$(FLASHER) -c $(STLINK) -p $(MCU) -w $< -v

# Sirf flash (verify nahi)
flash-fast: $(TARGET).ihx
	$(FLASHER) -c $(STLINK) -p $(MCU) -w $<

clean:
	-$(RM) $(TARGET).ihx *.map *.lst *.rel *.rst *.sym *.asm *.lk *.cdb *.adb *.o

.PHONY: all flash flash-fast clean
