# PS2 Logitech FFB structure and RPC map

## Verified OutRun path

`OutRun gameplay -> EZ Wheel Wrapper -> EE liblgdev -> SIF RPC 0x046D046D -> SYSTEM.PS2/LGDEV -> USBD -> Logitech wheel`

The supplied `SYSTEM.PS2` contains an IOP module whose exported library name is `lgdev`. Its embedded version string is `1.12.003 ( Wheel Joystick )`. Another module exports `USB_driver` / `usbd`.

The LGDEV IOP module registers RPC server ID `0x046D046D`. Its dispatcher begins at `0x000008A8` and uses a command jump table at `0x0000B618`.

## Force-effect object

OutRun's condition, constant, and periodic wrapper functions clear exactly `0x3C` bytes before filling an effect and passing it to `lgDevDownloadForceEffect` or `lgDevAUpdateForceEffect`.

This matches the PS2 Logitech `lgDevForceEffect` layout recovered from DWARF-backed public PS2 decompilation material:

```text
lgDevForceEffect size 0x3C
+0x00 u8  Type
+0x01     padding[3]
+0x04 u32 Duration
+0x08 u32 StartDelay
+0x0C union params[0x30]
```

Condition occupies two 0x18-byte axis records:

```text
lgDevConditionForceParams size 0x18
+0x00 s32 Offset
+0x04 u32 Deadband
+0x08 u32 SaturationNeg
+0x0C u32 SaturationPos
+0x10 s32 CoefficientNeg
+0x14 s32 CoefficientPos

effect.params.condition[2] == 0x30 bytes
```

The OutRun condition download wrapper at `0x001354B0` independently confirms this shape: it builds the first 0x18-byte condition block at effect+0x0C and copies that block into the second-axis area at effect+0x24.

Other union members are:

```text
lgDevEnvelopeParams size 0x10
+0x00 u32 AttackTime
+0x04 u32 AttackLevel
+0x08 u32 FadeTime
+0x0C u32 FadeLevel

lgDevConstantForceParams size 0x18
+0x00 s32 Magnitude
+0x04 u32 Direction
+0x08 lgDevEnvelopeParams envelope

lgDevPeriodicForceParams size 0x24
+0x00 u32 Magnitude
+0x04 u32 Direction
+0x08 u32 Period
+0x0C u32 Phase
+0x10 s32 Offset
+0x14 lgDevEnvelopeParams envelope

lgDevRampForceParams size 0x0C
+0x00 s32 MagnitudeStart
+0x04 s32 MagnitudeEnd
+0x08 u32 Direction
```

## EE <-> IOP RPC commands

| Command | EE function | IOP handler | Meaning |
| ---: | --- | --- | --- |
| 1 | lgDev Enumerate path | `0x00000BC0` | Enumerate |
| 2 | lgDev Open path | `0x00000DE4` | Open |
| 3 | lgDev Close path | `0x00000F88` | Close |
| 4 | GetDeviceProperty | `0x00001070` | Get property |
| 5 | `0x00167670` | `0x00001258` | SetDeviceProperty |
| 6 | Read path | `0x0000143C` | Read |
| 7 | `0x00167720` | `0x00001820` | Download/SetForceEffect |
| 8 | `0x00167C08` | `0x00001A38` | StartForceEffect |
| 9 | `0x00167CA0` | `0x00001BB4` | StopForceEffect |
| 10 | `0x00167888` | `0x00001D30` | DestroyForceEffect |
| 13 | `0x00167AB8` | `0x00001924` | UpdateForceEffect |

The EE-side functions visibly load these command IDs before the SIF RPC call. The IOP dispatch jump table independently maps the same IDs to the handlers above.

## OutRun wrapper anchors

- `0x001354B0` — DownloadConditionForce
- `0x00135640` — UpdateConditionForce
- `0x001357B8` — DownloadConstantForce
- `0x00135910` — UpdateConstantForce
- `0x00135AA8` — StartForceEffect
- `0x00135B60` — StopForceEffect
- `0x00135C18` — DestroyForceEffect
- `0x00135CD8` — SetOverallForceGain
- `0x00135D40` — DownloadPeriodicForce
- `0x00135EB0` — UpdatePeriodicForce

## PC FFB comparison rule

Use this map to recover the *gameplay meaning and scale* of forces before changing PC DirectInput behavior. Do not copy numeric constants across platforms until the caller-side units and ranges have been verified. Device-protocol details in LGDEV/USBD are secondary to the values OutRun puts into `Offset/Deadband/Saturation/Coefficient`, `Magnitude/Direction`, and `Period/Phase`.
