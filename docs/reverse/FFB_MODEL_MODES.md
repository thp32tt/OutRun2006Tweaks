# Selectable Wheel FFB Models

The standalone FFB branch exposes several force models through one DirectInput COM output owner. Device selection, focus-loss safety, actuator shutdown, response correction, slew limiting, soft saturation, reconnect handling and the hard DirectInput cap are shared by every model. Hardware periodic transport remains a live model/user choice: Arcade Original/Hybrid can request Sine, PS2 Original can request Triangle, and the core falls back to ConstantForce when a required periodic effect is unavailable. The shared compatibility wrapper does not overwrite that choice.

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

The public plugin also applies a spring for non-`0x7B` drive-board requests. Its rough-surface call is `Sine(70, 80, strength)`; the plugin API names the first argument `period` and copies it to SDL's periodic period field, so the PC host translates 70 ms to about 14.286 Hz rather than treating 70 as Hz. Gear changes while moving call `Sine(240, 320, 0.10)`: the PC reconstruction synthesizes one ~240 ms (~4.167 Hz) cycle and treats F11 Gear Shift as a host scaler, with 1.00 preserving the observed 0.10 source amplitude.

C2C does not expose the Lindbergh drive-board packet stream, so this branch reconstructs the event semantics from C2C-native signals:

- four per-wheel surface masks and the original `sub_1149C0` roughness LUT;
- left/right non-water rough-surface grouping;
- rough -> road transitions; while the short 0x04/0x14 transition is active it owns the directional surface output, matching the single-code callback semantics instead of summing/cancelling against a simultaneous sustained 0x10/0x00 reconstruction;
- C2C collision state for wall events, with a conservative host-only severe speed-drop fallback when no collision-state edge is available; the explicit game-state edge has priority;
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

The retail path is now decoded beyond topology for several fields: the Type-7 Spring coefficient/dynamic saturation, Type-8 Damper coefficient/saturation, the directional ConstantForce output cap, and the Type-4 periodic raw period/direction/phase/offset are backed by direct SLPM evidence. The PC translation uses those verified envelopes where possible.

Still unresolved are the gameplay meanings of the retail ConstantForce source globals, additional vehicle-state/activation shaping around the periodic envelope, some effect-manager slot semantics, and the raw period field's physical unit. Therefore:

- Condition/Spring and Damper parameters use recovered retail values with explicit user scaling;
- the PS2 road periodic uses the recovered Type-4/Triangle shape, raw period curve, four-wheel surface-envelope family, verified 1.25 vehicle-state envelope boost, `min(field_1C4,1)` factor, magnitude scale `50`, and raw start threshold `27`; the car-field labels behind the boost remain intentionally unnamed;
- F11 Road Detail `1.00` is the one-to-one host scaler around that recovered periodic envelope before Overall Strength and DD safety;
- the recovered directional ConstantForce transport/cap remains documented, but PS2 Original emits no C2C collision force because no verified non-zero retail caller has been recovered;
- no PS2 gear-shift pulse is synthesized without a verified retail caller;
- all output still passes through the shared modern DD safety layer.

The mode remains **Experimental** until those event/source mappings and remaining units are recovered and hardware-tested.

## Why Xbox is not a selectable wheel model

The reconstructed Xbox `CalcVibrationValues()` path is controller-rumble logic rather than a verified steering-wheel FFB implementation. Its two motor envelopes remain available only as diagnostic witnesses and are not offered as a wheel FFB model.

## F11 selection

`F11 -> Force Feedback -> FFB Model`:

1. Modern DD Physics
2. Arcade Original (Lindbergh-derived)
3. Arcade + Modern Hybrid
4. PS2 Original topology (Experimental)

Named FFB profiles include the selected model. Device identity, wheel response correction and diagnostics remain global/wheel-specific as before.
