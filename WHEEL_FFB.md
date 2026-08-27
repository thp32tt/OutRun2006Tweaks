# Wheel FFB experimental branch

This branch adds native steering-wheel force feedback to current OutRun2006Tweaks, initially targeting a MOZA R3.

## Current architecture

- **FFB output:** Windows DirectInput 8 COM (`IDirectInputEffect`).
- **Steering source:** the game's real `GetVolume(Steering)` path, not the unverified `EVWORK_CAR::field_1D0` value.
- **Update cadence:** one update per `CalcVibrationValues()` / car-physics tick (normally 60 Hz).
- **Main steering output:** `GUID_ConstantForce` updated with `DIEP_TYPESPECIFICPARAMS | DIEP_START`.
- **Road/tire texture:** hardware `GUID_Sine` periodic effects when the driver supports them; constant-force sine fallback otherwise.
- **Device handling:** dedicated `EXCLUSIVE | BACKGROUND` DirectInput handle; default device-name filter is `MOZA`; common virtual devices such as vJoy/ViGEm/XOutput are skipped.

The DirectInput output design is based on the hardware-tested lessons in `d-b-c-e/OutRun2006Tweaks-FFB` (MIT), while this branch keeps the current emoose Tweaks codebase and fixes the steering-source problem recorded in that project by reading the actual game steering input.

## Force model

The experimental model is intentionally arcade-oriented:

1. **Center spring** — actual steering position × speed curve.
2. **Damper** — derived from frame-to-frame change in the actual steering input.
3. **Cornering load** — OutRun's `field_264 + field_268` lateral signal.
4. **Grip loss** — cornering load gets lighter as the lateral signal enters a deep drift.
5. **Weight transfer** — braking/acceleration modulates structural steering load.
6. **Wall impact** — short directional collision impulse with cooldown.
7. **Gear shift** — symmetric +/− double pulse so it feels like a thunk instead of a sideways yank.
8. **Road texture** — OutRun's own Xbox surface roughness LUT (`sub_1149C0`) drives a hardware sine effect.
9. **Tire slip** — 40→28 Hz sine chatter as drift depth increases.

Output conditioning includes a warm-up ramp, `tanh()` soft saturation, per-frame slew limiting and a ramp-in when a DirectInput effect has to be recreated.

## Safety / lifecycle

Direct-drive safety is treated separately from the feel model:

- conservative default master gain: **25%**;
- 30-frame startup ramp;
- 6%/frame structural slew limit by default;
- watchdog timer zeros forces if the game FFB tick stops for more than 250 ms;
- Alt-Tab zeros forces;
- `WM_CLOSE`, `WM_DESTROY`, `WM_QUERYENDSESSION` and `ExitProcess` paths call `PanicStop`;
- `PanicStop` sends constant-force zero, stops periodic effects, `STOPALL`, `SETACTUATORSOFF`, `RESET`, then unacquires the device;
- driver autocenter is restored **after** `Unacquire`, matching the ordering validated on a MOZA R12 in the reference project.

## Settings

Settings can be overridden in `OutRun2006Tweaks.user.ini`:

```ini
[WheelFFB]
Enable = true
DeviceName = MOZA

# R3 first-test values
GlobalStrength = 0.25
SpringStrength = 0.45
DamperStrength = 0.10
SteeringWeight = 0.45
GripLoss = 0.60
LateralDeadzone = 1.5
WeightTransfer = 0.60

WallImpact = 0.35
GearShift = 0.18
RoadTexture = 0.20
TireSlip = 0.18
EngineIdle = 0.04

SlewRate = 0.06
UsePeriodicEffects = true
InvertForce = false
DebugLog = true
```

If the wheel pulls further into a corner instead of returning toward center, change:

```ini
InvertForce = true
```

If periodic vibration behaves strangely on a particular driver, test:

```ini
UsePeriodicEffects = false
```

This keeps steering FFB and synthesizes limited-frequency texture through ConstantForce instead.

## First MOZA R3 test

The first drive is still a smoke test. Verify these before judging fine feel:

1. OutRun still sees steering and pedals normally.
2. Log contains `WheelFFB: ready on 'MOZA ...'`.
3. Left steering produces a restoring force toward the right and vice versa.
4. Straight-line force does not violently oscillate.
5. Alt-Tab and game exit remove torque cleanly.
6. Only after the above, judge drift unloading, road texture, crash and gear effects.

Useful log lines start with `WheelFFB:` or `WheelFFB DIAG:`.

## CI

Every push to `wheel-ffb` runs the existing Windows Server 2022 / Visual Studio 2022 **Win32 Release** GitHub Actions workflow. The workflow injects `src/hooks_wheel_ffb_build.cpp` into the generated CMake source list and uploads the normal Tweaks build as an Artifact.
