# R51 Virtual Fourth Driver View

Base SHA: `17ad376bfdf7939f0851c0c629e4fa094a84f28a`

## View cycle

- View 1: native raw mode 2, untouched.
- View 2: native raw mode 1, untouched.
- View 3: native raw mode 0, untouched.
- View 4: virtual flag + raw mode 1. It uses the exact native view-2 camera controller, but enables the driver-seat additions.
- Next Change View exits V4 to native view 1.

No raw camera mode 3 is ever written.

## Virtual view 4 only

- camera offset: Forward/Right/Up
- full player-car render state
- draw-local player-car scale
- passenger-only ROB02 draw
- ROB01 driver is never forced

The passenger path uses the original game `CalcCharMatrix(car, ROB02, 1)`.
The passenger draw is injected only after the player-car `DispCarModel_Common`
returns and the caller executes `mxPopMatrix` at RVA `0x6BF91`; the hook is
at RVA `0x6BF96`. This avoids inheriting the car-body matrix/render state that
caused the previous passenger mesh corruption.

Passenger injection is skipped for reflection/effect semantic subpasses to
avoid duplicate character draws.

Defaults:
- Forward=-0.451
- Right=-0.037
- Up=0.015
- CarScale=1.12

R51 validated render graph is preserved:
`SAFE_DRAW_COMPARE=OFF`, `R26_HUD_COMPARE=ON`.
