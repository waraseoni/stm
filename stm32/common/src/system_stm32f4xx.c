/*
 * Minimal system_stm32f4xx.c -- shared by all F4 projects in this workspace.
 *
 * ST ka original reset par PLL config karta hai (HSE 8 MHz par depend karta hai).
 * Yahan sirf wo cheezein hain jo Cortex-M4 ko chahiye:
 *   1. FPU enable (CP10/CP11)  -- warna float instructions fault karte hain
 *   2. VTOR flash par
 *
 * Clock setup project ke main.c me hota hai (03-clock-pll me PLL).
 */

#include "stm32f4xx.h"

uint32_t SystemCoreClock = 16000000U; /* HSI 16 MHz */

void SystemInit(void)
{
    /* CPACR bits [23:20] = CP10/CP11 full access (FPU) */
    SCB->CPACR |= (0xFUL << 20U);

    /* Vector table flash ke start par */
    SCB->VTOR = FLASH_BASE;
}

void SystemCoreClockUpdate(void)
{
    SystemCoreClock = 16000000U;
}
