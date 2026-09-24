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

## 4. Collision assets and Stage corpus — CONFIRMED inventory / OPEN field semantics

The earlier non-Stage sample established the `COLI0200` container family. The full installation manifest now gives a complete Stage inventory:

- 847 files under `Stage/`;
- 66 stage directories/variants;
- 72 collision assets = 66 main `coli_CS_*` files + 6 `coli_BK_*` files;
- 19,481,268 bytes of compressed collision data.

The supplied `Stage.zip` is 290,113,621 bytes and was received/materialized for analysis. During this run the execution backend failed on raw ZIP access, so the newly uploaded Stage payload has **not** yet been used to claim any per-triangle/material field semantics. The authoritative stage/file inventory is preserved in `reverse/game_assets/stage_collision_inventory.json`.

Observed COLI containers have a stable family beginning with:

- total/payload-size field;
- ASCII `COLI0200`;
- counts and multiple in-file offsets;
- early `NEW COLLFMT` marker.

Exact COLI record-field -> runtime `surfaceMask` mapping remains **OPEN**.

### Correct runtime semantics

For FFB/reverse-analysis purposes, the legacy `EVWORK_CAR::water_flag_24C[4]` field should be treated as a **per-wheel surfaceMask[4]**. The Xbox-derived roughness routine dispatches many non-water masks through it.

Conversely, `OnRoadPlace_5C.loadColiType_0` is not a proven material ID. Current source defines `is_in_bunki()` as `loadColiType_0 != 0`, so it is route/branch/junction collision context.

The detailed evidence, stage-specific exceptions and telemetry design are in `docs/reverse/STAGE_SURFACE_FFB_MAP.md`.

## 5. FFB research plan enabled by the shared KB

1. Run the shared analyzer over the supplied Stage tree when raw execution access is available; record inflated COLI hashes/header/offset metadata.
2. Cluster anonymous per-face/per-region candidate fields across SNOW/ALAS/PALM/METR/CAPE/IMPE/LASV and forward/reverse pairs.
3. Add read-only runtime telemetry for `stageId, roadSectionNum, curStageIdx, loadColiType, surfaceMask[4], roughness[4]`.
4. Correlate driven locations and mask transitions with static COLI candidate values.
5. Assign semantic material names only after that correlation.
6. Replace stage-name FFB special cases only when native material/contact identity is proven and regression-tested.

The FFB layer should preserve four-wheel material identity instead of reducing everything to one max-roughness value when implementing curb/shoulder transitions.
