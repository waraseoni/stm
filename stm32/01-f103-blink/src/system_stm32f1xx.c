/*
 * Minimal system_stm32f1xx.c -- apna version, taaki clock ka control hamare paas rahe.
 *
 * ST ka original system file reset par khud hi HSE+PLL 72 MHz set karta hai;
 * agar board par crystal na ho to wahi hang kar jata hai. Bare-metal seekhne ke
 * liye explicit better hai: yahan kuch nahi hota, clock main() me set hoti hai.
 *
 * CubeMX/HAL project me ST ka hi system file use karenge (wahan HAL_RCC_OscConfig
 * isi par depend karta hai).
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
    /* Is template me clock main() set karta hai aur SystemCoreClock khud update
     * karta hai. HAL ke saath aane wale projects me ye function registers
     * padhkar value nikalta hai. */
    SystemCoreClock = 8000000U;
}
