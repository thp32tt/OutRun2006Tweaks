# OutRun 2006 native wheel/tyre physics map (FFB research)

Status: **research map, canonical OR2006C2C.EXE only**

Canonical executable identity is the one used by the whole-EXE map workflow. These
notes record only relationships that were observed in the disassembly/XREF graph.
Unknown physical units, left/right ordering and uncertain semantics are kept
explicit instead of being promoted into production FFB assumptions.

## 1. Invalidated v0.3 DBC "X-Force" hypothesis

`EVWORK_CAR+0xDBC` (`actionforce_DBC`) is adjacent to the already named race
handicap fields:

- `+0xDB0` commrace rank
- `+0xDB1` handicap state
- `+0xDB4/+0xDB8/+0xDBA` handicap fields
- `+0xDBC/+0xDC0` values written by the same catch-up/handicap calculation

The writer at RVA **0x00058E40** updates DBC/DC0 from rank/relative-speed
conditions. DBC therefore must not be treated as steering-rack/X-Force data.
v0.4 keeps the old settings only for profile compatibility and forces production
ownership to Modern DD.

## 2. Native longitudinal delta

`GamePlCar_Ctrl`, RVA **0x000A8330**, computes:

- `EVWORK_CAR+0x1D0 = field_1C4 - field_178`
- `EVWORK_CAR+0x1D4 = previous +0x1D0`

`field_1C4` is used as the vehicle speed scalar elsewhere. This makes 1D0/1D4
strong candidates for the game's own per-tick longitudinal speed delta/current
and previous acceleration-like state. Units/sign still require a capture before
they replace the existing FFB weight-transfer estimator.

## 3. Native heading

RVA **0x000A5650** converts `EVWORK_CAR+0x2E` through the game's 16-bit angle
helpers and trigonometric functions, multiplies by `field_1C4`, and writes the
result into `spd_mb_20.x/z`. This is strong evidence that +0x2E is a vehicle
heading/yaw angle.

A capture compares it with the current matrix-derived heading before any
production yaw-rate replacement.

## 4. Player physics workspace

The player car uses a fixed 0x900-byte workspace at original VA **0x0082E7F0**,
RVA **0x0042E7F0**.

Initializer RVA **0x000A69F0** sets the four wheel pointers:

| workspace field | inline object |
| --- | --- |
| +0x248 | +0x258 |
| +0x24C | +0x34C |
| +0x250 | +0x440 |
| +0x254 | +0x534 |

Each wheel object has stride **0xF4**.

RVA **0x00100700** applies the player steering angle to wheel 0 and wheel 1 but
not wheel 2/3. Therefore **wheel 0/1 are the front axle** and **wheel 2/3 are the
rear axle**. Left/right order is not yet proven.

## 5. Suspension / vertical-load channel

RVA **0x000A1B70** updates each wheel:

- `+0x18`: non-negative suspension/contact compression-like value
- `+0x1C`: previous +0x18
- `+0x20`: rate derived from the change in +0x18
- `+0x24`: nonlinear spring/damper reaction-like output
- `+0x28`: contact/rest reference used by the compression calculation

The later force pipeline uses:

- `+0x34`: actual normal-load/vertical-force candidate
- `+0x38`: reference/nominal load used to form a load ratio

RVA **0x00100C60** explicitly forms `(+0x34)/(+0x38)` and uses the ratio in a
load-sensitive tyre-capacity calculation.

## 6. Native tyre slip and lateral force

RVA **0x00100230** derives wheel `+0xEC` from the wheel/contact velocity
direction.

RVA **0x00100700** maintains wheel `+0x32` as wheel heading (front 0/1 include
steering input), then writes:

`+0xEE = +0xEC - +0x32`

RVA **0x001019C0** uses the opposite difference `+0x32 - +0xEC`, converts it
through the game's 16-bit angle scale, combines it with load/tyre parameters and
writes wheel **+0xAC**. This is strong evidence that:

- `+0xEE` is signed tyre slip-angle state (opposite sign to the angle used by
  the lateral-force calculation)
- `+0xAC` is the tyre-model lateral-force component before/through combined-slip
  processing

RVA **0x001026F0** applies the combined-slip/friction-circle limit to the force
pair and writes the adjusted `+0xAC/+0xB0` plus scale/angle state.

RVA **0x00101AD0** rotates `+0xAC/+0xB0` and writes `+0xB4/+0xB8`.
RVA **0x00102270** consumes `+0xB4/+0xB8` to build chassis forces/moments.

RVA **0x00100C60** writes `+0xC0`, a positive load-sensitive tyre force/grip
capacity used by the combined-slip limiter.

This provides a promising dimensionless research signal:

`front lateral-force ratio ~= (front0.AC + front1.AC) / (abs(front0.C0) + abs(front1.C0))`

It is not routed to FFB yet. Runtime capture must establish sign, scale, zero
behavior, airborne behavior and per-car consistency first.

## 7. Current capture contract

`NativePhysicsCapture60Hz=true` records, after the completed player-car physics
tick:

- speed, native speed delta/current+previous
- +0x2E heading candidate and +0xD34 angular candidate
- all four wheels' suspension/reaction/load fields
- tyre `AC/B0/B4/B8/BC/C0` force/capacity fields
- `E0/E4/EE/F0` combined-slip/angular fields
- front normal-load sum/difference and transformed-force sums

No field in this capture path can alter DirectInput output.


## 8. Opt-in native tyre SAT candidate

The v0.4 research branch exposes a **default-off** `NativeTireSAT` mode. It
uses only the front axle (wheel0/1):

- slip angle: `-EE * (2*pi/65536)`
- native lateral force: `AC0 + AC1`
- native load-sensitive capacity: `abs(C0_0) + abs(C0_1)`
- normalized force: lateral-force sum divided by capacity, clamped to [-1,1]

The native force magnitude is shaped only by the existing pneumatic/mechanical
trail model. The synthetic lateral-G load boost is intentionally not stacked on
top because AC/C0 already comes from the game's tyre/load/combined-slip path.

Safety/validation rules:

- ships OFF
- zero/invalid capacity cannot arm native SAT
- valid native ownership ramps in over ~200 ms at the fixed 60 Hz physics rate
- invalid native data fades back to Modern SAT over ~100 ms
- menu/focus/device/settings lifecycle resets native ownership to zero
- the existing output soft-cap, reversal release, DirectInput lease/watchdog and
  focus-loss zeroing remain downstream
- old/partial profiles that do not contain native-tyre keys explicitly restore
  `NativeTireSAT=false`, gain 1.00 and invert false

The sign/scale still requires a controlled low-strength hardware capture before
this mode can become a default. The separate invert switch exists only for that
validation and does not change global ConstantForce direction.


## 9. Native rear-slip counter-steer cue

The v0.4 research branch also exposes a **default-off**
`NativeOversteerCue` path inspired by the bounded rear-slip / oversteer ideas
used in AMS2 rFuktor-family custom FFB and modern Assetto Corsa FFB
post-processing tools.

It reads the canonical rear axle (wheel2/3):

- rear slip angle: capacity-weighted `-EE * (2*pi/65536)`
- rear lateral-force evidence: `AC2 + AC3`
- rear load-sensitive capacity: `abs(C0_2) + abs(C0_3)`

The additive cue is not a generic drift-force switch. Rear slip is normalized
against the configurable `NativeOversteerSlipThreshold` and passed through a
bounded catch window:

- below ~0.85x peak reference: zero
- 0.85x -> 1.15x: smooth rise
- 1.15x -> 1.45x: strongest catch cue
- 1.45x -> 2.25x: smooth release
- beyond ~2.25x: zero again

This prevents an extreme sustained slide from continually winding a DD wheel
harder. The cue is additionally protected by:

- front and rear native capacity must both be valid
- current vehicle-dynamics sample must be valid
- collision impulse handling must be inactive
- speed must be above the low-speed research gate
- protection ownership ramps in over ~200 ms but releases in ~50 ms when a
  collision/contact/telemetry guard fails
- lifecycle/settings transitions reset protection ownership to zero
- existing global soft clipping, stale-torque reversal release, output slew,
  DirectInput watchdog and focus/device-loss zeroing remain downstream

`NativeOversteerStrength` is capped at 0.35 before global output strength, and
`NativeOversteerInvert` reverses only this research channel for controlled
hardware sign validation.

Old or partial FFB profiles that do not contain the new rear-slip keys explicitly
restore `NativeOversteerCue=false`, strength 0.18, peak reference 0.12 rad and
invert false.

The capture analyzer now reports rear slip/capacity/AC distributions and
correlations plus P90/P95 rear-slip reference hints. Those percentile hints are
evidence for tuning only; they are never applied automatically.
