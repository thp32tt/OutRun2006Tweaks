# OutRun 2 Special Tours Deluxe / Lindbergh FFB comparative map

## Source identity

Public reference repository: `Boomslangnz/FFBArcadePlugin`

Files inspected:

- `Game Files/OutRun2Real.cpp` — blob `a66474889813405dd79cbf6bce50164c0b21fc0e`
- `Game Files/OutRun2Fake.cpp` — blob `0eb002d06c6b37bc3083508251b7eea027d1f4f5`

This document records comparative reverse-engineering evidence. It does not claim the plugin's comments are official Sega protocol documentation.

## Real drive-board path

`OutRun2Real.cpp` replaces the Lindbergh routine at absolute address `0x08105A48` and observes four byte-sized arguments. When the first argument is `0x7B`, the plugin treats the third argument as an FFB effect code. The source comments/handling associate these values with:

| effect code | plugin observation |
| --- | --- |
| `0x0B` | hard right-wall impact / constant-force event |
| `0x1B` | hard left-wall impact / constant-force event |
| `0x02` | grass/sand driving / sine effect |
| `0x10` | side-rail scrape |
| `0x04` | rough surface to road transition, one side |
| `0x14` | rough surface to road transition, opposite side |
| `0x00` | grass/sand/rough-surface state |

The plugin applies a spring for non-`0x7B` commands; `0x7D` is explicitly noted as unused in that implementation.

The Real path also samples:

- gear `0x0827A160`
- race state `0x08304ADC`
- speed `0x08273DF0`

Its speed-dependent strength is quantized in ten-percent steps. That curve is useful as evidence that the arcade path scales transient effects with speed, but it is not appropriate to copy literally into the modern DD-wheel backend because the C2C implementation already has continuous normalization, soft saturation and slew limiting.

## Fake/memory-observer path

`OutRun2Fake.cpp` reconstructs effects by observing memory rather than intercepting the drive-board request. Relevant addresses in that Lindbergh environment are:

| address | plugin use |
| --- | --- |
| `0x0827A1A0` | effect/state value |
| `0x08273FAC` | wall-related value read into `ffwall`; the current Fake source does not use it to generate FFB |
| `0x0827A1DA` | changing event value |
| `0x0827A35D` | changing event value / sine trigger |
| `0x0827A1D4` | side selector |
| `0x08670DC8` | steering byte, centered around 0x7F |
| `0x08273AD4` | observed float |
| `0x08304ADC` | race state |
| `0x086749CA` | menu state |
| `0x0827A160` | gear |
| `0x08273DF0` | speed |

The Fake path converts the steering byte directly into directional ConstantForce. This is a compatibility approximation, not a model to transplant into the current Physics SAT path. In particular, although the source reads `ffwall = 0x08273FAC`, it does not use that value to generate FFB; it remains only a discovery hint, not a validated wall-impact signal.

## C2C integration rule

Do **not** reuse the absolute Lindbergh addresses in `OR2006C2C.EXE`. Any production C2C hook must be independently recovered from the canonical EXE map and promoted through the binary-contract/signature process.

The current C2C tree already reconstructs the Xbox `CalcVibrationValues()` routine in `src/hooks_forcefeedback.cpp`. The wheel backend now logs its two normalized XInput motor envelopes as `origXboxL/origXboxR` in compact diagnostics and `xboxLeft/xboxRight` in opt-in 10 Hz telemetry.

These XInput channels are low/high-frequency rumble motors; they are **not left/right steering-force directions**. They are intentionally read-only witnesses and must not be added to DirectInput ConstantForce direction without stronger evidence.

Recommended correlation for hardware logs:

1. compare Xbox witness channel changes with current `roadAmp`, `slipAmp`, `event`, collision state and gear changes;
2. reproduce grass/sand, shoulder/rail contact, hard wall impacts and surface-to-road transitions;
3. only after a repeatable correspondence is established, promote a specific missing transient into the DD-wheel event layer;
4. preserve Physics SAT/mechanical trail/damper as the steering backbone instead of copying the Fake steering-centering approximation.


### Gear Sine trigger semantics

The plugin interface declares `Sine(UINT16 period, UINT16 fadePeriod, double strength)`, and `TriggerSineEffect` writes the first argument to SDL's periodic period and length. OutRun2Real's gear-change call `Sine(240, 320, 0.10)` therefore represents a 240 ms-period, 240 ms-length Sine at source amplitude 0.10; the second value is the attack/fade parameter. The PC reconstruction uses the 240 ms period as ~4.167 Hz and F11 Gear Shift only as an explicit host scaler.


### OutRun2Real ConstantForce lifetime

The shipped plugin profile `[Outrun 2 Special Tours Deluxe Real]` sets `FeedbackLength=80`. `TriggerConstantEffect` assigns that value to SDL's constant-effect length. The local `percentLength=100` in `SendForceFeedback` is used only by the companion rumble call, not by ConstantForce. The C2C reconstruction therefore represents the directional 0x10/0x00/0x0B/0x1B/0x04/0x14 ConstantForce lifetime as five 60 Hz ticks (~83.3 ms), the nearest whole-frame representation of 80 ms.


### OutRun2Real condition baseline

The shipped plugin profile sets `SpringStrength=50` and `EnableDamper=0`. Non-0x7B drive-board requests call `Springi(SpringStrength/100)`. With the plugin defaults MinForce=0 / MaxForce=100, `TriggerSpringEffectInfinite(0.50)` yields coefficient 0.50 and saturation 1.00 (`coeff*2`). The standalone **Arcade Original** shortcut restores that profile before the common PC Overall Strength/safety scaler. Arcade Hybrid deliberately retains the Modern DD structural backbone instead.


### Cabinet steering-hardware scope

Do not generalize one OutRun 2 cabinet steering mechanism to every cabinet variant. The SEGA motorized SPG-2500 handle assembly used by motor-FFB Twin/Deluxe-family documentation lists a 500 W servo motor, pulleys/gears, timing belt and steering VR, while DRIVE BOARD TEST actively rolls the wheel left/right and exposes MOTOR POWER steering-resistance levels with 80% as the default. A separate UK HAPP Upright service path explicitly documents mechanical spring replacement. The latter is a different handle/cabinet variant and must not be used as evidence that the motorized OutRun2Real/Lindbergh target had a passive centering spring.

For Arcade Original, the target remains the motorized drive-board feel represented by OutRun2Real: a continuously available condition/centering backbone plus drive-board event codes. The 0.50 condition coefficient is therefore a host translation of the motorized cabinet's active steering resistance, not a claim about a physical coil spring in the SPG-2500 mechanism.
