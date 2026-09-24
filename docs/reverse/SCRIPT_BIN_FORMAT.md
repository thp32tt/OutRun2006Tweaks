# OutRun 2006 Scripts/bin container reverse map

## Generic container — CONFIRMED across supplied files

All 80 supplied `Scripts/bin/*.bin` files can be read as a common header form:

```text
u32 descriptor_count
u32 fixup_count
fixup[fixup_count]      = { u32 pointer_field_offset, u32 target_data_offset }
descriptor[descriptor_count] = { u32 type_id/hash, u32 count, u32 data_offset }
... serialized data ...
```

The fixup table is important: serialized pointer-shaped values are **not** native EXE function pointers. At load time, the fields listed by the fixups are expected to be rebound to locations within the loaded blob.

The supplied corpus exposes hundreds of repeated descriptor type IDs and common fixed record widths. These IDs are useful for cross-file type clustering even before the names are known.

## TracksideCameras.bin — CONFIRMED structure / STRONG semantic inference

File size: 1,900 bytes (`0x76C`).

Header:

- descriptors: 8
- pointer fixups: 6

Fixups:

| Pointer field | Target data |
|---:|---:|
| `0x740` | `0x098` |
| `0x748` | `0x674` |
| `0x750` | `0x3E0` |
| `0x758` | `0x46C` |
| `0x760` | `0x50C` |
| `0x768` | `0x598` |

Descriptors:

| Type ID | Count | Offset | Exact stride to next region |
|---|---:|---:|---:|
| `0xBEF37BA8` | 13 | `0x098` | 20 |
| `0x21D147BF` | 29 | `0x19C` | 20 |
| `0xF5DE036D` | 7 | `0x3E0` | 20 |
| `0x991B659E` | 8 | `0x46C` | 20 |
| `0x34849FD6` | 7 | `0x50C` | 20 |
| `0x000B8F82` | 11 | `0x598` | 20 |
| `0x534C3720` | 10 | `0x674` | 20 |
| `0xE4C25C1C` | 6 | `0x73C` | 8 |

The seven 20-byte arrays consistently contain two zero DWORDs followed by three finite floats. The trailing six 8-byte records contain first DWORDs `0, 26, 24, 21, 20, 18`; those are valid unique-stage IDs, and the second field of each record is one of the six relocated pointer fields.

**STRONG INFERENCE:** this is a stage -> trackside-camera point-list graph, and the three floats are position-like XYZ values. The exact meaning of the two zero fields and whether each point is a camera position, target, spline knot or trigger must still be confirmed in the runtime consumer.

## Cross-project value

- VR/camera: resolve Trackside/native camera data into `EvWorkCamera` and `CalcCameraMatrix` for camera semantics and driver-seat work.
- FFB: the generic typed-script parser may expose race/course rules useful for interpreting stage state but should not be mixed with physics until a consumer is proven.
- localization: script descriptors can be searched for string IDs/references once the Text ID map exists.

## Required next step

Locate the generic loader that applies these pointer fixups and identify descriptor dispatch/type registration. Then map type IDs to consumer functions using the canonical EXE map. Do not infer function pointers from stale serialized pointer residue.
