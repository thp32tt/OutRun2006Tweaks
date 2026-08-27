# Wheel FFB experimental branch

This branch adds an experimental SDL3 haptic output path for steering wheels, initially targeting a MOZA R3.

## Design

- Keeps the existing OutRun2006Tweaks game hook intact.
- Hooks the Tweaks-side `CalcVibrationValues()` routine, calls the original first, then reads the restored Xbox vibration values.
- Reads steering through the game's own `GetVolume(Steering)` function, so both Tweaks SDL input and legacy DirectInput paths are supported.
- Uses SDL3 haptic device enumeration and selects a device whose name contains `MOZA` by default.
- Creates a constant-force steering effect and an optional 30 Hz sine texture effect.
- Uses conservative defaults, dual-rate EMA smoothing, tanh soft clipping, and a slew-rate limiter.
- Haptic effects use a 100 ms finite duration that is refreshed on game ticks, so force should expire if updates unexpectedly stop.

## Settings

The settings are registered by the mod and can be overridden in `OutRun2006Tweaks.user.ini`:

```ini
[WheelFFB]
Enable = true
DeviceName = MOZA
GlobalStrength = 0.35
SteeringStrength = 0.50
TextureStrength = 0.08
SlewRate = 0.08
InvertForce = false
DebugLog = true
```

Start with these conservative values on a DD wheel.

If the wheel pulls further into a turn instead of resisting it, change:

```ini
InvertForce = true
```

## Current status

This is a first hardware smoke-test build. It is intended to verify:

1. SDL3 detects the MOZA haptic device.
2. Constant force can be created and updated while OutRun still receives wheel input.
3. Force direction is correct.
4. The restored Xbox vibration signal can drive a sine texture effect.

True SAT, slip-based unloading, wall impact shaping, gear-shift pulses and separate road/kerb effects come after the output path is verified on real hardware.
