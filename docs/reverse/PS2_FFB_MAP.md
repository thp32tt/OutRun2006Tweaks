# OutRun 2 SP (Japan) PS2 FFB map

Source binaries analyzed:

- `SLPM_666.28` SHA-256 `bc5dd6d836bf34546ef9f047ad2bcb99c5ef5a713767a161d0c342af33f38c34`
- `IOPRP310.IMG` SHA-256 `1cf5475f533f04d161bbb4b08179df156afeb7b400f207c88dcf1e39466679b6`
- ELF entry `0x00100008`
- GP `0x0043BC70`

The retail ELF is stripped. Names in `reverse/ps2/semantics.json` are semantic names derived from literal diagnostic strings plus direct MIPS call edges; they are not claimed to be original Sega symbols.

## Verified EE-side FFB path

| Address | Semantic | Low-level target |
| --- | --- | --- |
| `0x00132488` | wheel/module initialization | literal `LGDEV.IRX`; wrapper init `0x001333D8` |
| `0x001354B0` | download condition force | `0x00167720 lgDevDownloadForceEffect` |
| `0x00135640` | update condition force | `0x00167AB8 lgDevAUpdateForceEffect` |
| `0x001357B8` | download constant force | `0x00167720 lgDevDownloadForceEffect` |
| `0x00135910` | update constant force | `0x00167AB8 lgDevAUpdateForceEffect` |
| `0x00135AA8` | start force effect | `0x00167C08 lgDevAStartForceEffect` |
| `0x00135B60` | stop force effect | `0x00167CA0 lgDevAStopForceEffect` |
| `0x00135C18` | destroy force effect | `0x00167888 lgDevDestroyForceEffect` |
| `0x00135CD8` | set overall force gain | `0x00167670 lgDevSetDeviceProperty` |
| `0x00135D40` | download periodic force | `0x00167720 lgDevDownloadForceEffect` |
| `0x00135EB0` | update periodic force | `0x00167AB8 lgDevAUpdateForceEffect` |
| `0x001362A0` | Logitech enumerate/open | `lgDevEnumerate/Open/SetDeviceProperty/Close` |

The supplied executable contains `EZ Wheel Wrapper v4.01`, Logitech wheel diagnostics and the EE-side `liblgdev` RPC implementation. Condition, constant and periodic effects have separate wrapper paths but converge on the same low-level force-effect payload API. This makes the effect structure passed into `lgDevDownloadForceEffect` / `lgDevAUpdateForceEffect` the next high-value target when comparing PS2 behavior with the PC DirectInput FFB implementation.

Update/start/stop use asynchronous `lgDevA*` calls in this build. Function `0x00167910` is repeatedly called immediately before those requests and is treated only as an unnamed synchronization/RPC helper until stronger evidence exists.

Ramp-force diagnostic strings are present, but no direct code XREF is verified yet. Do not assign a ramp wrapper address from adjacency alone.

## IOPRP310

The ROMDIR image was parsed directly. Its module list is: RESET, ROMDIR, EXTINFO, SYSMEM, LOADCORE, SIFCMD, SIFMAN, THREADMAN, IOMAN, MODLOAD, FILEIO, CDVDMAN, CDVDFSV, LOADFILE, TIMEMANI, ROMDRV, EESYNC, SYSCLIB and STDIO.

`LGDEV.IRX` is **not** inside this IOPRP image. The EE binary explicitly references that filename, so the disc's `LGDEV.IRX` is the next required binary for the IOP-side Logitech USB/force protocol map. A disc-local `USBD.IRX` is also useful if present.

The supplied `DRIVER.PS2` was also checked as a possible module container. It is 458,752 bytes with SHA-256 `d5cd14efec2378d96497fdc8d9dc2f0b31ae799d42fdb1a7e798adf066a3cea9`; it has no ELF, ROMDIR, IRX, LGDEV, USBD, Logitech or wheel-module signature/string, and its high-entropy payload is consistent with a packed game asset rather than an IOPRP/IRX container. It is therefore not used as evidence for Logitech transport semantics.

## Map-generation result

The local full map generated during this analysis indexed:

- 561,460 EE instructions
- 38,738 direct JAL calls
- 49,884 code references
- 22,169 data references
- 10,101 strings
- 2,490 exact string XREFs
- 8,537 inferred function anchors
- SQLite `integrity_check = ok`

Production PC FFB changes should use this PS2 map as comparative evidence, not blindly copy numeric values until the force-structure fields and units are confirmed.


## 2026-09-25 retail parameter recovery

A deeper pass over `SLPM_666.28` resolves enough of the retail condition/periodic path to replace several provisional PC values.

### Retail drive factor

At `0x00132CB0`, the game reads the car value corresponding to C2C `EVWORK_CAR::field_1C4`, divides it by `2.5`, and clamps it to 1. The FFB update at `0x00133070` then divides that stored value by `0.35` and clamps again.

Equivalent expression:

```
driveFactor = clamp(field_1C4 / 0.875, 0, 1)
```

This is intentionally separate from the Modern DD model's `field_1C4 / 2.0` normalization.

### Spring — Type 7

The initial setup at `0x00133044..0x00133058` requests symmetric spring values of 70/70.

During the normal update at `0x001330F0..0x00133128`, static retail data resolves to:

- base saturation = `15`
- saturation speed span = `45`
- coefficient = `200`
- offset = `0`
- deadband = `0`

The runtime condition is therefore:

```
saturationNeg = saturationPos = 15 + round(45 * driveFactor)
coefficientNeg = coefficientPos = 200
```

All values are on the Logitech 0..255 condition scale.

The standalone PC translation maps these to normalized DirectInput `GUID_Spring` parameters. Existing F11 Spring Strength / Spring Saturation remain available only as explicit user scaling around the recovered retail baseline; the PS2 shortcut restores the 1.00x scaler values.

### Damper — Type 8

The main update around `0x00133138..0x00133158` uses the retail static value `10` and computes:

```
coefficient = round(10 * (1 - driveFactor))
```

The Type-8 condition builder around `0x001342F0` confirms:

- saturationNeg = saturationPos = `255`
- offset = `0`
- deadband = `0`
- symmetric coefficient.

The PC PS2 model now follows this speed-fading coefficient. F11 Dynamic Damping `0.30` is defined as the 1.00x retail scaler for this mode.

### Constant force

The main path at `0x001330A0..0x001330EC` combines two signed force sources, selects:

- direction `90` for one sign;
- direction `270` for the other;

and computes a magnitude scaled by `220`, capped to `220` on the 0..255 Logitech scale.

This proves a directional constant-force cap of `220/255`, but a deeper static call-graph pass finds no verified non-zero retail caller for the two source floats in this build. Their direct setter at `0x00132A28` is called at initialization (`0x00132AF4`) and from the per-car update (`0x00132DB4`); both verified direct calls pass `0.0 / 0.0`. No additional direct call or static function-pointer reference to that setter was recovered.

That does **not** prove that a computed/indirect caller is impossible, but it removes the evidentiary basis for mapping C2C collision detection to the retail ConstantForce transport. PS2 Original therefore keeps the transport/cap documented for future recovery while emitting no collision ConstantForce until a non-zero retail event caller is verified. Modern DD collision and Lindbergh Arcade wall-event behavior are unaffected.

### Periodic — Type 4 / Triangle

The main path at `0x00133328..0x00133384` requests effect Type `4`. Contemporary Logitech `liblgdev` ABI material identifies Type 4 as **Triangle**.

The retail period field is:

```
period = 100 + round(60 * driveFactor)
```

The manager passes:

- direction `90`;
- phase `0`;
- offset `0`;
- no envelope;
- infinite/continuous-style duration through the wrapper path.

The retail binary proves the numeric period field `100..160`; it does **not** itself label that field as Hertz or milliseconds. For the DirectInput host translation, the standalone branch interprets the common liblgdev period convention as milliseconds, yielding about 10 Hz at the low end and 6.25 Hz at the high end. This is marked as a host translation assumption.

The PS2 PC mode now creates `GUID_Triangle` for its road periodic instead of reusing the Modern/Arcade `GUID_Sine` object.

### Periodic magnitude / surface source — retail chain recovered

A deeper retail-SLPM pass resolves the steady-state Type-4 magnitude source:

1. `0x001D7C88` maps a wheel's surface mask plus collision context to a roughness envelope. The caller at `0x001D8098..0x001D810C` evaluates the four car values at offsets `0x24C/0x250/0x254/0x258` and keeps the maximum.
2. The LUT values and the stage/context special cases for masks `0x2` and `0x400000` match the already reconstructed C2C/Xbox `sub_1149C0` map. This makes the current C2C four-wheel roughness result a retail-backed baseline source for PS2 translation.
3. `0x001D811C` stores the maximum surface envelope to `0x0035F280`. The same producer contains additional vehicle-state shaping after that store; those later semantic branches remain under analysis.
4. `0x00132E94..0x00132EA0` consumes that envelope and multiplies it by `min(field_1C4, 1.0)` before storing the Type-4 source.
5. `0x00133328..0x0013334C` computes the integer periodic magnitude from:
   `surfaceSource * driveFactor * 50 * activationScale`.
   Static retail data at `0x0034950C` is `50`.
6. After round-to-integer, raw magnitudes below `27` are suppressed/stopped (`slti ..., 0x1B` at `0x0013334C`).

The standalone PS2 mode therefore no longer reuses Modern DD's `(roughness - 0.30) / 0.55` texture shaping. Its steady-state translation uses the recovered raw surface envelope, `min(field_1C4,1)`, the independent PS2 `driveFactor`, the retail scale `50`, and the raw start threshold `27`.

The multiplier previously described as an unknown activation/ramp is now identified more precisely. The retail options path creates a 0..10 control and, when the wheel-device path is active, stores its selected integer in game-state byte `+0xFC` at `0x0024E8DC`. The surface producer at `0x001D7FBC..` reads the same byte, rejects values >=11, and disables the surface-feedback producer when it is zero. For non-zero levels it also forms a base strength:

```
surfaceFeedbackBase = 0.20 + 0.08 * level
```

The Type-4 manager at `0x001332BC..0x00133340` independently applies:

```
wheelLevelScale = (level + 1) / 11
```

with the same invalid-value reset. This is strong evidence for a **wheel-specific 0..10 feedback-strength level**, not a transient activation/recreate ramp. The exact localized menu label is still unresolved, so the documentation intentionally avoids claiming a literal retail setting name.

Two boundaries remain explicit:

- later vehicle-state shaping inside the surface-feedback producer is still under analysis;
- F11 **Road Detail = 1.00** is a host/user one-to-one scaler corresponding to the retail maximum level multiplier of 1.0 before Overall Strength and the common DD output/safety layer. Lower F11 values remain continuous host scaling; no retail default level is invented.

### Effect-manager category ownership

The retail manager uses a 0..11 category dispatcher. The FFB-relevant categories needed by the OutRun wheel update are now tied to concrete wrapper families:

| manager category | retail owner | evidence |
| ---: | --- | --- |
| `1` | ConstantForce | queried by `0x00134048`; create/update converges on `0x001357B8 / 0x00135910` |
| `2` | Type-8 condition / Damper | queried by `0x00134268`; condition update carries effect type `8` |
| `7` | Type-7 condition / Spring | queried by `0x00133DB0`; initial 70/70 setup and runtime condition update carry type `7` |
| `8` | periodic | queried by `0x00134EB0`; the main update supplies periodic type `4` |

`0x00133B20` is the presence/query dispatcher and `0x00133700` is the matching stop/release dispatcher. Their jump tables also contain categories 0, 3, 4, 5, 6, 9 and 11; those are not assigned force-effect names without stronger caller evidence. Category 10 falls through the query dispatcher. Category 9 is exercised by the manager control path but remains deliberately unnamed.

This confirms that Spring, Damper, ConstantForce and periodic ownership are distinct in the retail manager and supports keeping those DirectInput objects separate in the PC PS2 model.

### Model-transition ownership

Periodic COM objects are waveform-specific. On FFB model/profile transitions the PC backend now releases the old periodic objects and recreates the required set:

- Modern DD: road Sine + tire-slip Sine;
- Arcade Original: road Sine only;
- Arcade Hybrid: road Sine + tire-slip Sine;
- PS2 Original Experimental: road Triangle only.

This prevents a Modern/Arcade Sine from surviving into PS2 and removes the false requirement that original modes support the unused Modern tire-slip effect.

### Reproducible compact semantic map

The compact reverse-map builder now imports the curated retail evidence records from `reverse/ps2/semantics.json` into its SQLite `semantics` table. This includes the recovered runtime construction sites at `0x00132CB0`, `0x001330A0`, `0x001330F0`, `0x00133138`, and `0x00133328`. These records persist already-established instruction/dataflow evidence; they do not upgrade unresolved gameplay-event semantics.

`ps2query.py` is schema-aware: a compact regenerated map works without the richer one-off `string_xrefs` table, while enriched maps can expose those XREFs when present. CI executes a minimal SQLite regression test for this contract.

### Remaining PS2 reverse targets

Still unresolved and therefore **not** represented as retail-original tuning:

- any non-zero/indirect retail caller and semantic identity for the ConstantForce source variables at `0x00349528 / 0x0034952C`;
- semantic identity of the additional vehicle-state shaping that can modify the surface envelope after `0x001D811C`;
- semantic naming for the remaining non-core effect-manager categories (0, 3, 4, 5, 6, 9, 11);
- event-to-effect mapping for collision, rail, surface transition, drift/slip, and gear;
- `LGDEV.IRX` internal transport/units if the disc module becomes available.

