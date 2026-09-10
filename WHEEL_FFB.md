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

F11 provides:

- startup device enumeration and hotplug handling;
- per-device button / axis / hat bindings;
- VID/PID plus serial/path identity where available;
- Steering / Accelerator / Brake calibration with Min / Rest / Max;
- axis inversion / positive-side selection;
- guided Quick Setup;
- live input display and binding persistence.

Quick Setup waits for the captured control to be released before moving to the next step, including raw pedal axes. This prevents a held accelerator from being mistaken for the following brake step.

## Force model

The FFB model uses the real game steering input and game-physics signals rather than the previously unverified `field_1D0` steering assumption.

Main channels:

1. **Aligning / Spring** — speed-dependent centering based on actual steering position.
2. **Dynamic Damping** — resists steering velocity without being another centering spring.
3. **Cornering Load** — adds load from OutRun lateral physics.
4. **Grip-loss Unload** — reduces cornering/spring load in a deep drift.
5. **Weight Transfer** — acceleration/braking modulation.
6. **Collision** — short directional impact impulse.
7. **Gear Shift** — short symmetric shift thunk.
8. **Road Detail** — periodic texture derived from the game's surface roughness information.
9. **Tire Slip** — periodic chatter that increases with drift depth.

Signal conditioning applies master gain before soft saturation/slew. DirectInput effect `dwGain` remains at `DI_FFNOMINALMAX`; the 0-150% master control is software model gain, not an out-of-range driver gain.

## MOZA R3 v0.1 default profile

The release default intentionally adds steering resistance without making collision feedback too strong.

```text
Overall Strength       0.70
Aligning / Spring      0.60
Dynamic Damping        0.42
Cornering Load         0.38
Grip-loss Unload       0.65
Collision              0.38
Road Detail            0.30
Tire Slip              0.20
Low-speed Aligning     0.08
Corner-load Boost      0.35
Hardware Spring        ON
Hardware Damper        ON
Reverse Spring         OFF (MOZA R3 tested direction)
```

F11 exposes this as **MOZA R3 v0.1 (default)**. The older Simulation Balanced / Arcade Light / Arcade Strong presets remain available as comparison references.

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
