# Exercise templates (unverified, copy when toolchain is ready)

These are **starting-point snippets** for the remaining Phase 1/2 exercises.
They are register-level (CMSIS, no HAL) and follow the style of
`stm32/01..06` and `stm8/01..04`. They have **not** been compiled on this
machine (no ARM GCC / SDCC). Treat them as templates: read, understand,
then rewrite by hand (study method).

---

## STM32

### 09-tim-input-capture (TIM2 CH1, PA0)
```c
/* Enable TIM2 clock, configure PA0 as AF1 (TIM2_CH1), set CCMR1 CC1S=01,
   CCER CC1E=1, PSC/ARR, DIER CC1IE, NVIC TIM2_IRQn. In ISR read CCR1. */
RCC->APB1ENR |= RCC_APB1ENR_TIM2EN;
RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN;
GPIOA->MODER  &= ~(3u << 0);
GPIOA->MODER  |=  (2u << 0);          /* AF */
GPIOA->AFR[0] &= ~(0xFu << 0);
GPIOA->AFR[0] |=  (1u  << 0);        /* AF1 = TIM2 */
TIM2->PSC = 84 - 1;                  /* 1 MHz tick @84 MHz */
TIM2->ARR = 0xFFFFFFFFu;
TIM2->CCMR1 = (1u << 0);             /* CC1S = 01 (input, TI1) */
TIM2->CCER  = (1u << 0);             /* CC1E */
TIM2->DIER  = (1u << 1);             /* CC1IE */
TIM2->CR1   = (1u << 0);             /* CEN */
NVIC_EnableIRQ(TIM2_IRQn);
/* ISR: freq = 1e6 / (CCR1 - prev_ccr1) */
```

### 10-spi-flash (SPI1, W25Qxx read ID)
```c
RCC->APB2ENR |= RCC_APB2ENR_SPI1EN;
RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN;
/* PA5=SCK, PA6=MISO, PA7=MOSI, PA4=CS (manual) */
GPIOA->MODER &= ~((3u<<(5*2))|(3u<<(6*2))|(3u<<(7*2))|(3u<<(4*2)));
GPIOA->MODER |=  ((2u<<(5*2))|(2u<<(6*2))|(2u<<(7*2))|(1u<<(4*2)));
GPIOA->AFR[0] |= (5u<<(5*4))|(5u<<(6*4))|(5u<<(7*4));
SPI1->CR1 = (1u<<2) /* MSTR */ | (3u<<3) /* BR=1/16 */ | (1u<<6) /* SPE */;
/* CS low, send 0x9F, read 3 bytes, CS high */
```

### 11-i2c-sensor (I2C1, master)
```c
RCC->APB1ENR |= RCC_APB1ENR_I2C1EN;
RCC->AHB1ENR |= RCC_AHB1ENR_GPIOBEN;
/* PB6=SCL, PB7=SDA, AF4 */
GPIOB->MODER &= ~((3u<<(6*2))|(3u<<(7*2)));
GPIOB->MODER |=  ((2u<<(6*2))|(2u<<(7*2)));
GPIOB->AFR[0] |= (4u<<(6*4))|(4u<<(7*4));
GPIOB->OTYPER |= (1u<<6)|(1u<<7);   /* open-drain */
I2C1->CR2 = 16;                      /* 16 MHz APB1 */
I2C1->CCR = 80;                      /* 100 kHz */
I2C1->TRISE = 17;
I2C1->CR1 |= (1u << 0);             /* PE */
/* START, address, data, STOP ... poll SR1/SR2 */
```

### 12-adc-dma (ADC1 + DMA2 stream0)
```c
RCC->APB2ENR |= RCC_APB2ENR_ADC1EN;
RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_DMA2EN;
/* PA0 analog */
GPIOA->MODER |= (3u << 0);
ADC1->SQR3 = 0;                      /* channel 0 */
ADC1->SQR1 = 0;                      /* 1 conversion */
ADC1->CR2  = (1u << 0) | (1u << 8) | (1u << 1);  /* ADON, DMA, DDS */
DMA2_Stream0->PAR  = (uint32_t)&ADC1->DR;
DMA2_Stream0->M0AR = (uint32_t)adc_buf;
DMA2_Stream0->NDTR = N;
DMA2_Stream0->CR   = (0u<<6) /* P->M */ | (2u<<11) /* PSIZE word */ |
                     (2u<<13) /* MSIZE word */ | (1u<<4) /* TCIE */ | (1u<<0) /* EN */;
ADC1->CR2 |= (1u << 30);            /* SWSTART */
```

### 13-dac (F446, DAC1 CH1 on PA4)
```c
RCC->APB1ENR |= RCC_APB1ENR_DACEN;
RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN;
GPIOA->MODER |= (3u << (4 * 2));     /* analog */
DAC->CR = (1u << 0);                 /* EN1 */
DAC->DHR12R1 = value;                /* 0..4095 */
```

### 14-usb-cdc (optional, CubeMX recommended)
Use CubeMX to generate a CDC device project, then compare with bare-metal register code.

---

## STM8

### 06-tim2-pwm (PB? TIM2 CH1)
```c
/* CLK 16 MHz; TIM2 prescaler + ARR + CCR1; output compare mode PWM1 */
CLK_CKDIVR = 0x00;
/* configure PB? as AF push-pull (TIM2_CH1) */
TIM2_PSCR = 0x00;   /* /1 */
TIM2_ARRH = 0x03; TIM2_ARRL = 0xE7;   /* ~1 kHz */
TIM2_CCR1H = 0x01; TIM2_CCR1L = 0xF3; /* ~50% */
TIM2_CCMR1 = 0x60;  /* PWM mode 1 */
TIM2_CCER1 = 0x01;  /* CC1E */
TIM2_CR1   = 0x01;  /* CEN */
```

### 07-exti-button
```c
/* EXTI on PA3 (port A, line 3); ISR toggles PB5 */
PA_DDR &= ~0x08; PA_CR1 |= 0x08; PA_CR2 |= 0x08;   /* pull-up + interrupt */
EXTI_CR1 |= 0x08;   /* PA3 falling edge (port A, CR1 bits 6:7? check RM) */
/* enable global interrupts: rim() */
```

### 08-i2c-eeprom
```c
I2C_CR1 = 0x01;     /* PE */
I2C_CR2 = 0x08;     /* 8 MHz? adjust */
I2C_CCRH = 0x00; I2C_CCRL = 0x50;
/* START, address, data, STOP */
```

### 09-adc1
```c
ADC1_CR1 = 0x01;    /* ADON */
ADC1_CR2 = 0x00;
ADC1_CSR = 0x00;    /* channel 0 */
/* start conversion, poll EOC, read ADC1_DRL/DRH */
```

### 10-eeprom
```c
/* FLASH_DUKR unlock, write byte to 0x4000, lock */
FLASH_DUKR = 0xAE; FLASH_DUKR = 0x56;
*(volatile u8 *)0x4000 = 0x42;
FLASH_IAPSR &= ~0x02;   /* clear DUL */
```

### 11-low-power
```c
/* halt / wait-for-interrupt */
__asm__("halt");
```

### 12-watchdog
```c
IWDG_KR = 0xCC;     /* start */
IWDG_KR = 0x55;     /* unlock PR/RLR */
IWDG_PR = 0x06;     /* /256 */
IWDG_RLR = 0xFF;
IWDG_KR = 0xAA;     /* reload */
```

---

## Notes
- All snippets are **unverified** (no toolchain on this machine).
- Register names/addresses may need adjustment; always check the RM.
- Each exercise should get its own folder under `stm32/` or `stm8/` with `README.md` + build files, following `01-blink-pb5` / `01-f103-blink` style.
- Add a `docs/` gotcha line per exercise.
