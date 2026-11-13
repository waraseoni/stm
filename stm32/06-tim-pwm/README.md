# 06-tim-pwm

Pehla **output compare / PWM**: TIM2 CH1 se onboard LED fade.

## Kya hota hai
- PA5 (LD2) = TIM2_CH1, AF1.
- 1 kHz PWM, 1000 steps (0.1% resolution).
- Duty triangle wave se 0 -> 100% -> 0 (approx 2 s). CPU sirf har 10 ms par
  `CCR1` update karta hai — brightness hardware se aati hai.

## Chalane ka tarika

```powershell
cd stm32\06-tim-pwm
cmake --preset f446re
cmake --build build
cmake --build build --target flash
```
LED dheere-dheere bright/dim hogi. (Logic analyzer ho to PA5 par 1 kHz, duty
badalte hue dekh sakte ho.)

## Formula (yaad rakho)

```
f_pwm = f_tim / (PSC + 1) / (ARR + 1)
duty  = CCR1 / (ARR + 1)
```

`16 MHz / 16 / 1000 = 1 kHz`, `CCR1 = 500` -> 50%.

## Khud try karo

- [ ] `PSC` 15 -> 159 karo: frequency 100 Hz. LED flicker karti hai? (1 kHz se
      upar flicker aankh ko nahi dikhta)
- [ ] `PWM_TOP` 100 karo: resolution 1% — fade me steps dikhte hain?
- [ ] `TIM_CCMR1_OC1PE` hatao: `CCR1` update par glitch aata hai? kyun?
- [ ] `TIM_CCER_CC1P` set karo (active-low polarity) — LED ulta chalti hai.
- [ ] PWM ko TIM3 CH1 (PB4, AF2) par shift karo — pin/AF table dekho.
- [ ] Software PWM likho (SysTick + GPIO toggle) aur compare karo: CPU load,
      jitter, code size.
- [ ] Break/Fault input (TIM1) padho — motor control me kyun zaroori hai?

## Common problems

| Symptom | Reason |
|---|---|
| LED off rehti hai | AF number galat (PA5 par AF1), ya `CC1E` missing |
| LED full bright, fade nahi | `CCR1` update nahi ho raha (loop condition) |
| LED 50 Hz par flicker | PSC bahut bada, ya ARR bahut chhota |
| Kuch nahi hota | `RCC_APB1ENR_TIM2EN` / `CEN` missing |
