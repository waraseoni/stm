/*
 * Minimal system_stm32f1xx.c -- shared by all F1 projects in this workspace.
 *
 * ST ka original system file reset par khud hi HSE+PLL 72 MHz set karta hai;
 * agar board par crystal na ho to wahi hang kar jata hai. Bare-metal seekhne ke
 * liye explicit better hai: yahan kuch nahi hota, clock main() me set hoti hai.
 *
 * CubeMX/HAL project me ST ka hi system file use karenge.
 */

#include "stm32f1xx.h"

uint32_t SystemCoreClock = 8000000U; /* reset default: HSI 8 MHz */

void SystemInit(void)
{
    /* Vector table flash ke start par hai (default). Aur kuch nahi. */
    SCB->VTOR = FLASH_BASE;
}

void SystemCoreClockUpdate(void)
{
    /* Clock main() set karta hai aur SystemCoreClock khud update karta hai.
     * HAL wale projects me ye function registers padhkar value nikalta hai. */
    SystemCoreClock = 8000000U;
}
