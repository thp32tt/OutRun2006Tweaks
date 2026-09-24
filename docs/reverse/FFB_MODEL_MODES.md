# Selectable Wheel FFB Models

The standalone FFB branch exposes several force models through one DirectInput COM output owner. Device selection, focus-loss safety, actuator shutdown, response correction, slew limiting, soft saturation, reconnect handling and the hard DirectInput cap are shared by every model.

## Model 0 — Modern DD Physics

The existing DD-oriented model:

- front-slip/yaw Physics SAT with Natural SAT fallback;
- pneumatic + mechanical/caster trail;
- dynamic damping and grip-loss release;
- stage-aware four-wheel road texture;
- modern collision, gear and optional engine haptics.

This remains the default.

## Model 1 — Arcade Original (Lindbergh-derived)

This is a reconstruction of the **observed drive-board semantics** from the public `Boomslangnz/FFBArcadePlugin` `OutRun2Real.cpp` path. It must not be described as an official Sega protocol specification.

The reference path intercepts the Lindbergh routine at `0x08105A48`. Observed effect-code handling:

| code | observed plugin interpretation | PC reconstruction |
| ---: | --- | --- |
| `0x0B` | hard right-wall impact | directional ConstantForce |
| `0x1B` | hard left-wall impact | opposite directional ConstantForce |
| `0x02` | grass/sand | rough-surface vibration |
| `0x10` | side-rail / one directional group | one-sided rough-surface ConstantForce |
| `0x04` | rough surface -> road, one side | ~100 ms directional transition |
| `0x14` | opposite rough -> road transition | ~100 ms opposite transition |
| `0x00` | grass/sand/rough state, opposite group | one-sided rough-surface ConstantForce |

The public plugin also applies a spring for non-`0x7B` drive-board requests and a short 0.10 sine-like gear pulse.

C2C does not expose the Lindbergh drive-board packet stream, so this branch reconstructs the event semantics from C2C-native signals:

- four per-wheel surface masks and the original `sub_1149C0` roughness LUT;
- left/right non-water rough-surface grouping;
- rough -> road transitions;
- C2C collision state and speed-loss detection for wall events;
- C2C gear changes.

Modern inferred Physics SAT and inferred tire-slip chatter are disabled in this mode. The centering backbone is the shared DirectInput condition/spring path.

The Lindbergh plugin's speed-strength staircase is retained as a comparative shape. Its thresholds were defined in a different speed scale, so C2C uses the same ten-step structure normalized to C2C `speedNorm`; this is a porting approximation, not a claim that the raw speed units are identical.

## Model 2 — Arcade + Modern Hybrid

Keeps the Modern DD structural steering model but swaps surface/wall/gear event behavior to the Lindbergh-derived arcade reconstruction.

This is intended for modern DD hardware when the user wants current SAT quality with arcade-style transient timing.

## Model 3 — PS2 Original topology (Experimental)

The PS2 reverse map verifies distinct:

- condition-force download/update;
- constant-force download/update;
- periodic-force download/update;
- start/stop/destroy;
- overall force gain;
- Logitech enumerate/open/device-property flow.

What is **not** fully decoded yet is the exact force payload field layout, units and game-event mapping used by the retail build. Therefore this mode deliberately implements only the verified effect topology:

- condition/spring backbone;
- ConstantForce collision/event transport;
- periodic road transport;
- shared modern DD output safety.

It does not claim unverified magnitudes to be original PS2 values. Once the remaining PS2 force payload is decoded, the model can be tightened without changing the UI or output-owner architecture.

## Why Xbox is not a selectable wheel model

The reconstructed Xbox `CalcVibrationValues()` path is controller-rumble logic rather than a verified steering-wheel FFB implementation. Its two motor envelopes remain available only as diagnostic witnesses and are not offered as a wheel FFB model.

## F11 selection

`F11 -> Force Feedback -> FFB Model`:

1. Modern DD Physics
2. Arcade Original (Lindbergh-derived)
3. Arcade + Modern Hybrid
4. PS2 Original topology (Experimental)

Named FFB profiles include the selected model. Device identity, wheel response correction and diagnostics remain global/wheel-specific as before.
