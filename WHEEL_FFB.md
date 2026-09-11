# Wheel / FFB architecture — v0.1

This document describes the `wheel-ffb` branch used for **OutRun2006Tweaks Wheel FFB v0.1**.

## Scope

v0.1 was created primarily for a personal **MOZA R3** setup and has only been personally hardware-tested on that wheel. It is shared as an experimental community build for anyone who may find it useful.

## Architecture

Input and force feedback deliberately use separate owners:

- **Input owner:** SDL3 raw joystick multi-device path.
- **FFB owner:** custom Windows DirectInput COM engine.
- Wheels, pedals, shifters, button boxes and gamepads can be bound independently.
- FFB is pinned to the selected DirectInput device GUID rather than whichever similarly named interface appears first.
- Legacy original-game DirectInput input remains an explicit compatibility fallback; it is not the v0.1 default.
- Application-level SDL Haptic is not used as the wheel FFB backend.

This separation avoids having an input poller and an FFB backend fight over the same exclusive DirectInput handle.

## Input setup

With the default `UseNewInput=true` path, **Input Bindings** is the single owner of steering, pedals, shifter/buttons and menu controls. Open it from the game's Controller Configuration screen, from **Settings → Controls → Configure Input Bindings**, or directly from **F11 → Force Feedback → Open Input Bindings**.

Quick Setup currently walks through Steering, Accelerator, Brake, Shift Up/Down, Start, Confirm, Back and Menu Up/Right/Down/Left. Each captured raw-device source replaces bindings only from the same currently resolved physical SDL device, so a wheel pass does not erase separate pedals, a shifter/button box or the default gamepad bindings. A step can be skipped when the wheel has no matching control. After the wizard, **Keep & Fine-tune** retains all captures and returns to the editor for per-axis Min / Rest / Max calibration.

Bindings are live immediately but are not durable until saved. Manual edits expose **Save & Return to game** so it is explicit whether the current mapping has been persisted. The **Profiles** tab can save the complete multi-device binding set as `OutRun2006Tweaks.profiles/Input/<name>.ini`; steering deadzone, sensitivity bypass, input backend and the exact selected DirectInput FFB output identity travel with that wheel profile. Loading a profile also updates the normal `OutRun2006Tweaks.input.ini` and user settings, so the selected setup survives the next restart. The separately named FFB feel profiles remain device-independent.

The Controllers page provides live raw axis/button/hat diagnostics and hotplugged devices appear automatically. Binding identity prefers VID/PID plus serial when available; USB path is only a duplicate-device fallback rather than a hard requirement.

## Force model

The FFB owner is the custom DirectInput COM engine and remains separate from SDL input ownership. The main steering model now has two SAT paths:

1. **Physics SAT** — estimates front slip from steering angle, body slip and yaw, then shapes it with a pneumatic-trail-like curve. It requires a current valid motion sample.
2. **Natural SAT** — steering-angle based progressive restoring torque. It is also the full-strength fallback while Physics SAT is calibrating or temporarily lacks valid motion telemetry.
3. **Centering Spring** — low-speed stabilizer, preferably DirectInput `GUID_Spring` when supported.
4. **Dynamic Damping** — resists steering velocity and releases with real front scrub/body slide.
5. **Weight Transfer** — filtered longitudinal acceleration/braking modulation of steering load.
6. **Collision / Gear Shift** — short event impulses kept separate from sustained steering slew.
7. **Road Detail / Tire Slip** — hardware sine effects where available, with a ConstantForce fallback that only uses remaining steering headroom.

`field_264/268` are used as lateral-load magnitude only; grip/slip decisions come from the vehicle-dynamics estimator. GlobalStrength is software model gain, while DirectInput device/effect gain stays at `DI_FFNOMINALMAX`. Sustained force passes through the production soft-knee limiter and DD-safe slew path.

The dedicated Force Feedback page exposes common controls directly and keeps lower-level but still supported values under **Advanced FFB tuning** (Spring Saturation, Weight Transfer, Lateral Signal Deadzone, Gear Shift, Engine Idle and Force Slew Rate). Named feel profiles are stored separately under `OutRun2006Tweaks.profiles/FFB/<name>.ini`. They intentionally exclude the DirectInput output-device GUID/name and diagnostic logging, so switching a force profile cannot silently redirect torque to another wheel. Loading a profile zeroes the current effects and restarts the normal DD-safe warm-up ramp before the new values take over.

## MOZA R3 recommended profiles

The current UI provides two saved starting points rather than the obsolete single `v0.1 default` button.

```text
Load MOZA R3 Physics SAT
Overall Strength       0.70
Centering Spring       0.65
Spring Saturation      0.95
Dynamic Damping        0.28
Self-aligning Torque   1.45
Grip-loss Response     0.65
Weight Transfer        0.15
Force Slew Rate        0.040
Road Detail            0.30
Tire Slip              0.20
Collision              0.38
Hardware Spring        ON
Hardware Damper        ON
Hardware sine effects  ON
Reverse SAT/CF         ON
Reverse Spring         OFF
```

`Load MOZA R3 Natural SAT` keeps the same overall/effect baseline but disables Physics SAT and uses Steering Weight 1.75, Dynamic Damping 0.30, Weight Transfer 0.20 and Slew 0.045. Treat both as starting points: verify ConstantForce and Spring direction with the 20% safe tests before increasing hardware torque.

For the R3, MOZA specifies a 3.9 Nm peak-torque direct-drive base with a 1000 Hz USB refresh capability. That USB figure does **not** create new OutRun physics samples: the game logic remains 60 Hz, so this fork deliberately does not synthesize a separate 1000/2000 Hz ConstantForce thread. While validating the game's SAT model, keep the Pit House **Base FFB Curve linear** and remember that Pit House mechanical centering, damping, inertia and friction are independent base-side forces that can stack with the game's Spring/Damper/SAT. Response correction remains off unless a measured wheel-response curve justifies it.

## Safety and lifecycle

The DirectInput engine includes:

- startup/reconnect force ramping;
- foreground/gameplay checks before torque updates;
- force zeroing and transient-event reset on focus loss;
- watchdog behavior when the FFB update path stalls;
- device-loss reacquire/reinitialize handling;
- panic-stop handling on game/window shutdown;
- safe left/right direction tests fixed at 20%, rejected outside gameplay;
- periodic road/tire/collision/shift signals silenced during manual direction tests.

Direct-drive wheels can still produce significant force. Keep a conservative hardware torque limit while testing a new wheel or driver.

## Compatibility notes

### MOZA R3

Personally tested in v0.1. In the tested setup:

- 270° steering range was used;
- Spring direction works with normal/positive coefficients;
- Reverse Spring is OFF;
- steering, pedals, menu directions/buttons and FFB operate through the multi-device + DirectInput split architecture.

### Other hardware

Other DirectInput-compatible wheels may work, including devices that expose separate input and FFB interfaces. v0.1 should still be treated as **untested** on hardware other than the MOZA R3 until community reports are available.

For a report, include:

- wheel base / rim / pedals / shifter models;
- driver and firmware versions;
- whether input appears in F11 Controllers;
- whether the selected FFB device passes direction tests;
- `OutRun2006Tweaks.log` from a complete launch → race → exit session.

## Credits

The implementation and design work builds on community references from:

- [emoose/OutRun2006Tweaks](https://github.com/emoose/OutRun2006Tweaks)
- [hyp36rmax/multi-device-input](https://github.com/hyp36rmax/multi-device-input/tree/multi-device-input)
- [d-b-c-e/OutRun2006Tweaks-FFB](https://github.com/d-b-c-e/OutRun2006Tweaks-FFB)

Thank you to those authors and community testers for making their work and hardware observations available. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for license/attribution details.

## Research-informed SAT and wheel-response model

Physics SAT separates a **pneumatic-trail** component from a bounded **mechanical/caster-trail** component. The combined proxy follows the standard aligning-moment structure `Fy * (pneumatic trail + mechanical trail)`: mechanical trail therefore acts whenever front lateral force exists instead of behaving like a fallback that only appears after pneumatic trail collapses. The total is normalized so `SteeringWeight` remains the primary gain, and mechanical trail is still not a centre spring.

The vehicle estimator keeps the existing bicycle-model-inspired `roadWheelAngle - bodySlip - yawRate * yawLeadSeconds` relation, but its body-slip/yaw/front-slip filters are speed-adaptive. This is a relaxation-length-inspired approximation: at higher vehicle speed the same fixed time low-pass created too much countersteer/SAT lag. Aligning moment has different transient behaviour from lateral force, so **Pneumatic Trail Response Lead** lets only the pneumatic lever arm move part-way toward raw front slip while lateral force and torque direction remain on the filtered signal. The default 0.25 is deliberately conservative and telemetry records `trailResponseSlip` / `trailResponseLead` for hardware validation.

`Force Feedback -> FFB Headroom / Clipping` measures sustained structural demand only. Crash/gear events, startup/recreate ramps and near-stop frames are excluded. P95/P99, soft-knee occupancy and hard-cap demand are reported, with a non-automatic Overall Strength suggestion targeting roughly 90% P99 demand.

Wheel-specific response correction is optional and **off by default**. A wheel profile can store `ResponseCorrection`, an 11-point monotonic `ResponseLUT` (desired torque 0..100% in 10% steps -> DirectInput command), and optional `MaxTorqueNm` for diagnostics. These hardware properties are deliberately excluded from named FFB feel profiles. Leave correction linear/off on a DD wheel unless a measured response curve justifies it.
