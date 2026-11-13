# study/ — vendor code padhne ki jagah

Yahan SDK examples ko **copy** karke annotate karo. Original `vendor/` me
untouched rehta hai, isliye upgrade/diff kabhi nahi tootega.

Pattern:

```
study/
├─ stm8/
│  └─ tim4-pwm/
│     ├─ README.md      <- kya seekha, kaunse page, kya confuse hua
│     └─ main.c         <- copied example + apne // NOTE: comments
└─ stm32/
   └─ f4-uart-dma/
      ├─ README.md
      └─ main.c
```

Har study folder ke `README.md` me 3 lines minimum:

```
Source: STM32CubeF4/Projects/.../UART_TwoBoards_ComDMA
Seekha: DMA circular mode me TC flag clear karna zaroori hai warna ...
Diff from my code: HAL ne NVIC priority 0 set kiya, maine 5 -- kyun matter karta hai?
```
