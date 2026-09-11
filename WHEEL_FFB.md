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

Quick Setup currently walks through Steering, Accelerator, Brake, Shift Up/Down, Start, Confirm, Back and Menu Up/Right/Down/Left. Each captured raw-device source replaces only the same broad source family, so configuring a wheel does not erase existing gamepad bindings. A step can be skipped when the wheel has no matching control. After the wizard, **Keep & Fine-tune** retains all captures and returns to the editor for per-axis Min / Rest / Max calibration.

Bindings are live immediately but are not durable until saved. Manual edits expose **Save & Return to game** so it is explicit whether the current mapping has been persisted.

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

The dedicated Force Feedback page exposes common controls directly and keeps lower-level but still supported values under **Advanced FFB tuning** (Spring Saturation, Weight Transfer, Lateral Signal Deadzone, Gear Shift, Engine Idle and Force Slew Rate).

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
