# Wheel / FFB architecture — v0.1

This document describes the release architecture of the `wheel-ffb` branch used for **OutRun2006Tweaks Wheel FFB v0.1**.

## Scope

v0.1 was developed primarily around a **MOZA R3** and the tested default path is:

- input: SDL3 raw multi-device input;
- force feedback: Windows DirectInput COM;
- build: Win32 x86;
- game update rate: OutRun's native 60 Hz gameplay loop.

Other DirectInput wheels may work, but the R3 is the main hardware validation target for this release.

## Input ownership

With `UseNewInput=true`, **Input Bindings is the only input-binding owner** for steering, pedals, buttons and menu controls. Wheel, separate pedals, shifter, button box and gamepad can all contribute to one player at the same time.

The older legacy DirectInput path remains available only as a compatibility fallback. The v0.1 release documentation no longer directs users through the old guided Quick Setup flow.

Bindings are live while editing, but manual changes should be persisted with **Save & Return to game**. Named input profiles remain available for complete multi-device layouts.

## FFB ownership

The wheel FFB backend is a single DirectInput COM owner. It pins output to the selected DirectInput device identity instead of whichever similarly named interface is enumerated first.

The main steering model contains:

1. **Physics SAT** — estimates front slip from vehicle motion, steering and yaw, then derives aligning torque from lateral force and total trail.
2. **Natural SAT fallback** — progressive steering-angle-based restoring torque when the physics sample is unavailable or Physics SAT is disabled.
3. **Mechanical / caster trail** — remains active with front lateral load instead of acting as an artificial center spring.
4. **Low-speed spring** — only a stabilizer near low speed; deliberately reduced on the tested R3 feel.
5. **Dynamic damping** — steering-velocity resistance that releases as the front end scrubs or the car slides.
6. **Grip-loss unloading** — reduces steering load as usable front grip falls away.
7. **Road / tire / gear / collision effects** — transient tactile effects layered on top of the structural steering signal.

## Force Feedback UI

The F11 **Force Feedback** page owns output-device selection and game-side tuning. `Load MOZA R3 Physics SAT` and `Load MOZA R3 Natural SAT` provide starting profiles, while **Save Force Feedback** persists live edits.

The **Advanced FFB tuning** section exposes supported lower-level values such as Spring Saturation, Weight Transfer, Force Build Slew Rate, Countersteer Release Rate, Pneumatic Trail Response Lead and optional wheel-response correction. These remain live tuning controls; wheel-specific response data is stored with the wheel profile rather than a generic named feel profile.

## MOZA R3 compatibility path

The R3 driver can accept creation/update of a DirectInput sine effect while the physical road texture remains effectively inaudible. v0.1 therefore forces road/slip vibration through the **ConstantForce fallback** on the R3 path.

Road contact is sampled across all four wheels. The compatibility layer distinguishes:

- **mixed surface** — meaningful roughness spread while only part of the car is on a curb/shoulder;
- **fully rough surface** — all sampled wheels are on a high-roughness surface;
- **ordinary surface** — no extra tactile override.

Mixed and fully rough curb states use the same strong tactile profile so vibration does not disappear when the remaining wheels cross fully onto the curb. During tactile contact the R3 path temporarily reduces structural SAT/damping enough for the road ripple to remain perceptible under corner load, then immediately restores the user's normal settings.

Snow stages have a much lower core road-texture scale. The R3 compatibility wrapper compensates that attenuation only when a real tactile surface is detected, so the normal snow road itself does not become a constant buzz.

## Device selection and safety

- Clean R3 setups auto-match the DirectInput product substring `R3 Racing Wheel`.
- Once a device is selected, the exact DirectInput GUID is persisted.
- Focus loss, state transitions and device loss clear active effects.
- Device reconnect schedules normal DirectInput reinitialization.
- Manual left/right direction tests are hard-capped at 20% and only run during active gameplay.
- A wheel-output owner suppresses duplicate gamepad rumble ownership where required.

## R3 release feel

The release retune intentionally moved away from a heavy artificial spring:

- low-speed spring reduced;
- spring saturation reduced;
- SAT remains the main cornering load;
- road texture is strengthened for the ConstantForce fallback;
- tire-slip buzz is kept low;
- gear-change feedback is made clearly perceptible;
- snow/curb tactile handling is R3-specific and does not globally weaken ordinary cornering.

These are starting values rather than a guarantee for every firmware/Pit House configuration.

## Diagnostics

`OutRun2006Tweaks.log` records:

- selected DirectInput FFB identity;
- effect creation/fallback status;
- SAT and final output diagnostics;
- R3 road-contact diagnostics including min/max roughness, spread, mixed/full-rough state and temporary tactile scaling.

For a useful hardware report, include the full launch → race → exit log plus wheel-base model, driver and firmware version.

## Build and release validation

CI runs:

- `tools/verify_wheel_ffb_current.py` against the consolidated production source;
- the production wheel FFB math test;
- Win32 Release compilation;
- PE32 payload checks and compiled marker verification;
- final artifact upload from the exact release commit.

The v0.1 release workflow waits for the matching successful Build workflow before publishing the ZIP.

## Credits / license

The implementation is based on `emoose/OutRun2006Tweaks` and incorporates design lessons from public OutRun wheel work including `hyp36rmax/multi-device-input` and `d-b-c-e/OutRun2006Tweaks-FFB`.

Repository license details are in `LICENSE.md` and `THIRD_PARTY_NOTICES.md`. The public binary ZIP receives one consolidated `LICENSES.txt` generated from the dependency source trees used for that build.
