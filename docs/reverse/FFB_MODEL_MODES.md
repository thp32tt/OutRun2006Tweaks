# Selectable Wheel FFB Models

The standalone FFB branch exposes several force models through one DirectInput COM output owner. Device selection, focus-loss safety, actuator shutdown, response correction, slew limiting, soft saturation, reconnect handling and the hard DirectInput cap are shared by every model. Hardware periodic transport remains a live model/user choice: Arcade Original/Hybrid can request Sine, PS2 Original can request Triangle, and the core falls back to ConstantForce when a required periodic effect is unavailable. The shared compatibility wrapper does not overwrite that choice.

## Model 0 — Modern DD Physics

The existing DD-oriented model:

- front-slip/yaw Physics SAT with Natural SAT fallback;
- pneumatic + mechanical/caster trail, with a smooth deep-slip-only mechanical/caster reinforcement that is zero in normal corners and reaches +25% by about 0.32 rad front slip;
- dynamic damping and grip-loss release;
- stage-aware four-wheel road texture;
- modern collision, gear and optional engine haptics.

This remains the default. The two **MOZA R3** Modern presets intentionally default hardware periodic effects **off**, using the ConstantForce road/slip fallback because the R3 compatibility work found that reported Sine support can be physically weak. This is a preset default, not a global lock: the F11 periodic switch remains live.

## Model 1 — Arcade Original (Lindbergh-derived)

This is a reconstruction of the **observed drive-board semantics** from the public `Boomslangnz/FFBArcadePlugin` `OutRun2Real.cpp` path. It must not be described as an official Sega protocol specification.

The reference path intercepts the Lindbergh routine at `0x08105A48`. Observed effect-code handling:

| code | observed plugin interpretation | PC reconstruction |
| ---: | --- | --- |
| `0x0B` | hard right-wall impact | directional ConstantForce |
| `0x1B` | hard left-wall impact | opposite directional ConstantForce |
| `0x02` | grass/sand | rough-surface vibration |
| `0x10` | side-rail / one directional group | one-sided rough-surface ConstantForce |
| `0x04` | rough surface -> road, one side | ~80 ms directional transition (5 C2C ticks) |
| `0x14` | opposite rough -> road transition | ~80 ms opposite transition (5 C2C ticks) |
| `0x00` | grass/sand/rough state, opposite group | one-sided rough-surface ConstantForce |

The public plugin also applies a spring for non-`0x7B` drive-board requests. Its rough-surface call is `Sine(70, 80, strength)`; the plugin API names the first argument `period` and copies it to SDL's periodic period field, so the PC host translates 70 ms to about 14.286 Hz rather than treating 70 as Hz. Gear changes while moving call `Sine(240, 320, 0.10)`: the PC reconstruction synthesizes one ~240 ms (~4.167 Hz) cycle and treats F11 Gear Shift as a host scaler, with 1.00 preserving the observed 0.10 source amplitude.

C2C does not expose the Lindbergh drive-board packet stream, so this branch reconstructs the event semantics from C2C-native signals:

- four per-wheel surface masks and the original `sub_1149C0` roughness LUT;
- left/right non-water rough-surface grouping;
- rough -> road transitions; the OutRun2Real profile's `FeedbackLength=80` maps to five C2C 60 Hz ticks (~83.3 ms), and while the 0x04/0x14 transition is active it owns the directional surface output instead of summing/cancelling against a simultaneous sustained 0x10/0x00 reconstruction;
- a dedicated C2C course-collision witness: the course solver reloads EVWORK_CAR field_283 to 30 and field_coli_281/field_282 carry side/intensity-related state. A rising high timer edge now owns wall/course impacts; the broader field_8 bit 0x1000 remains available for vehicle/other impacts, with severe speed-drop only as emergency fallback;
- C2C gear changes.

Modern inferred Physics SAT and inferred tire-slip chatter are disabled in this mode. The centering backbone is the shared DirectInput condition/spring path. Road Detail and Collision are explicit PC host scalers around the reconstructed `SpeedStrength` source; both Arcade shortcuts set them to 1.00 for one-to-one source amplitude before common Overall Strength. The **Use Arcade Original** shortcut restores the public OutRun2Real profile baseline: `SpringStrength=50` maps to a 0.50 condition coefficient with 1.00 saturation, while `EnableDamper=0` maps to zero Dynamic Damping. F11 can still override those values explicitly after loading the shortcut; Arcade Hybrid does not inherit this Original-only condition baseline.

The Lindbergh plugin's speed-strength staircase is retained as a comparative shape. Its thresholds were defined in a different speed scale, so C2C uses the same ten-step structure after scaling `speedRaw / 2`; this is a porting approximation, not a claim that the raw speed units are identical. Modern DD still clamps its own `speedNorm` to 0..1, while Arcade preserves 0..1.25 headroom so the reference final >500 / 100% strength band remains reachable. Captured C2C telemetry reaches `speedRaw ~= 2.239`, i.e. Arcade normalized speed ~=1.12.

## Model 2 — Arcade + Modern Hybrid

Keeps the Modern DD structural steering model but swaps surface/wall/gear event behavior to the Lindbergh-derived arcade reconstruction.

This is intended for modern DD hardware when the user wants current SAT quality with arcade-style transient timing. Collision debounce remains shared, but Hybrid only unloads its Modern structural torque during the active Arcade directional event window (~80 ms); the rest of the debounce interval no longer leaves SAT artificially blank.

The **Use Arcade Hybrid** shortcut is a complete reference preset rather than a delta from the previously selected model. It explicitly restores the Modern DD spring/damper, mechanical/caster, tire-slip, slew and reversal-release baseline before enabling the arcade event layer. This prevents Arcade Original's 0.50/no-damper condition profile or PS2 condition settings from leaking into Hybrid during live F11 switching. All Original/Hybrid/PS2 reference shortcuts also restore both ConstantForce and Spring reversal to OFF so stale direction settings cannot contaminate model comparisons.

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
- PS2 Host Gain is a separate PC/DD transport multiplier: 1.00x is the recovered retail-reference translation, while the F11 PS2 shortcut starts at 2.00x for modern DD hardware (adjustable through 2.50x). It scales Spring/Damper/Triangle/ConstantForce-fallback transport together without changing the recovered retail formulas; normal DirectInput caps still apply;
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


### Cabinet steering-hardware scope

Do not generalize one OutRun 2 cabinet steering mechanism to every cabinet variant. The SEGA motorized SPG-2500 handle assembly used by motor-FFB Twin/Deluxe-family documentation lists a 500 W servo motor, pulleys/gears, timing belt and steering VR, while DRIVE BOARD TEST actively rolls the wheel left/right and exposes MOTOR POWER steering-resistance levels with 80% as the default. A separate UK HAPP Upright service path explicitly documents mechanical spring replacement. The latter is a different handle/cabinet variant and must not be used as evidence that the motorized OutRun2Real/Lindbergh target had a passive centering spring.

For Arcade Original, the target remains the motorized drive-board feel represented by OutRun2Real: a continuously available condition/centering backbone plus drive-board event codes. The 0.50 condition coefficient is therefore a host translation of the motorized cabinet's active steering resistance, not a claim about a physical coil spring in the SPG-2500 mechanism.
