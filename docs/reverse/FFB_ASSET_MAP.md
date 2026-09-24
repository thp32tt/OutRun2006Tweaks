# OutRun 2006 FFB / physics asset reverse map

This document separates original-game evidence from the modern DD-wheel force model.

## 1. Existing native signal chain — SOURCE-CONFIRMED

Current `src/hooks_wheel_ffb.cpp` obtains surface state from each of four wheel/contact slots:

- `EVWORK_CAR::water_flag_24C[0..3]` (car offsets `0x24C..0x258`)
- `EVWORK_CAR::OnRoadPlace_5C.loadColiType_0`

It passes these to the Xbox-derived `sub_1149C0(surfaceMask, loadColiType, waterFlag)` and takes the largest returned roughness. Current DD-wheel code then removes the ordinary asphalt baseline and maps rough surfaces into the RoadTexture effect.

This means the most useful asset-level FFB research path is not a new arbitrary force table. It is:

`COLI0200 stage material -> runtime contact/material flags -> sub_1149C0 original roughness -> DD-wheel effect policy`.

## 2. Original Xbox-derived roughness mapping — SOURCE-CONFIRMED

The current fork contains an almost direct reconstruction of the Xbox game's surface mapping:

| surfaceMask | roughness / behavior |
|---:|---|
| `0x000001` | `0.00` |
| `0x000002` | normally `0.25`; stage-specific water cases below |
| `0x000004` | `0.70` |
| `0x000008` | `0.85` |
| `0x000010` | `0.90` |
| `0x000080` | `0.85` |
| `0x000100` | `0.45` |
| `0x000200` | `0.35` |
| `0x000400` | `0.30` |
| `0x000800` | `0.35` |
| `0x001000` | `0.35` |
| `0x002000` | `0.35` |
| `0x008000` | `0.40` |
| `0x100000` | `0.71` |
| `0x200000` | `0.80` |
| `0x400000` | `0.25` when `loadColiType != 0`; otherwise normally `0.90`, except Casino Town / reverse -> `0.25` |
| `0x800000` | `0.50` |
| other recognized high masks | fallback around `0.31` |

For mask `0x2`, these unique stages set the water flag and use higher roughness:

- 11 / 41: Metropolis / reverse -> `0.73`
- 13 / 43: Cape Way / reverse -> `0.79`
- 14 / 44: Imperial Avenue / reverse -> `0.76`

This table should be kept as an **original-game semantic witness**, not assumed to be ideal torque magnitude for a modern DD wheel.

## 3. Current modern-wheel signals — SOURCE-CONFIRMED

The current fork additionally derives:

- body slip and local longitudinal/lateral motion;
- yaw rate;
- front-slip proxy / tire scrub;
- native speed-vector correlation;
- longitudinal weight transfer;
- collision impulses from game state (`stateFlags & 0x1000` plus speed-drop logic);
- gear-change event;
- road texture and tire-slip periodic effects.

These should be correlated against native material/contact state before adding new synthetic cues.

## 4. Collision assets — CONFIRMED / OPEN semantics

Nineteen uploaded collision files inflate to a container with magic `COLI0200`. They represent 7 unique payload hashes in this subset; many BK files are byte-identical placeholder/common payloads.

The full installation manifest lists **72 `Stage/.../coli_*` files**, including stage-specific `coli_CS_*` data that was not included in the current uploaded asset archives.

Observed COLI files have a stable header family beginning with:

- total/payload-size field;
- ASCII `COLI0200`;
- counts and multiple in-file offsets;
- ASCII marker equivalent to `NEW COLLFMT` in the early header area.

Exact material/triangle field meanings are still **OPEN**. No field should be labeled `surfaceMask` merely because values resemble the runtime flag.

## 5. FFB research plan enabled by the shared KB

1. Obtain representative `Stage/.../coli_CS_*_bin.sz` files for asphalt, grass, snow/ice, water-edge and wall scenes.
2. Parse COLI sections and cluster per-face/per-region attribute words.
3. Add read-only runtime tracing at the point that populates `OnRoadPlace_5C` and `water_flag_24C[]`.
4. Correlate static COLI attributes with runtime `surfaceMask/loadColiType` and `sub_1149C0` output.
5. Replace stage-name special cases only when a native material/contact semantic is proven.

This can improve road texture, snow/ice behavior, curb/grass distinction and water/splash cues while retaining a modern DD-wheel force model.
