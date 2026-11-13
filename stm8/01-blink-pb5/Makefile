# STM8S103F3P6 blink on PB5 -- SDCC
MCU     ?= stm8s103f3
TARGET  ?= blink
SRC     ?= main.c

CC      ?= sdcc
CFLAGS  ?= -mstm8 --std-c99 --opt-code-speed
FLASHER ?= stm8flash
STLINK  ?= stlinkv2

all: $(TARGET).ihx

$(TARGET).ihx: $(SRC)
	$(CC) $(CFLAGS) -o $@ $(SRC)

flash: $(TARGET).ihx
	$(FLASHER) -c $(STLINK) -p $(MCU) -w $<

# flash + verify + reset
flashv: $(TARGET).ihx
	$(FLASHER) -c $(STLINK) -p $(MCU) -w $< -v

clean:
	rm -f *.ihx *.map *.lst *.rel *.rst *.sym *.asm *.lk *.cdb *.adb *.o

.PHONY: all flash flashv clean
