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

The ROMDIR image was parsed into the standard runtime modules: SYSMEM, LOADCORE, SIFCMD, SIFMAN, THREADMAN, IOMAN, MODLOAD, FILEIO, CDVDMAN, CDVDFSV, LOADFILE, TIMEMANI, ROMDRV, EESYNC, SYSCLIB and STDIO.

`LGDEV.IRX` is **not** inside this IOPRP image. The EE binary explicitly references that filename, so the disc's `LGDEV.IRX` is the next required binary for the IOP-side Logitech USB/force protocol map. A disc-local `USBD.IRX` is also useful if present.

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

This proves a directional constant-force cap of `220/255`, but the semantic meaning of those two retail source variables is not yet sufficiently mapped to call the path specifically collision, rail, or steering force. The PC event mapping therefore remains explicitly provisional.

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

- semantic identity of the signed constant-force source variables at `0x00349528 / 0x0034952C`;
- semantic identity of the periodic magnitude source around `0x00349538`;
- full mapping of effect-manager slots/types around `0x00134478..0x001351FC`;
- event-to-effect mapping for collision, rail, surface transition, drift/slip, and gear;
- `LGDEV.IRX` internal transport/units if the disc module becomes available.

