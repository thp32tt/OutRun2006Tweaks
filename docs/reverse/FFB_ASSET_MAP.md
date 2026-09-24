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


## Confirmed Stage COLI0200 material contract

Direct analysis of the user-supplied Stage.zip plus the canonical PC executable closes the previous static-asset gap.

- 72 collision assets: 66 `COLI0200` course files + 6 legacy `COLI0105` background files.
- `COLI0200` section 2 is the per-collision **materialId byte array**.
- Canonical PC VA `0x0043ECB8..0x0043ECC7` reads `materialId[collisionIndex]` and returns `surfaceMask = 1u << materialId`.
- The four contact calls write masks to `EVWORK_CAR+0x24C/+0x250/+0x254/+0x258`.
- Section 3 is a 64-byte collision geometry record (`vec3 corner[4] + vec3 center + u16 collisionFlags + s16 localHeadingAngle`).
- Section 4 is a 48-byte per-corner-normal record.
- Section 5 is a one-byte collision subtype/class family; names remain open.
- Section 6 is a u16 road-section-index family compared against `OnRoadPlace::roadSectionNum`.

Primary-road material IDs are only `0x01, 0x14, 0x16, 0x17` in the supplied 66-stage corpus. In particular:
- `0x17 -> mask 0x00800000 -> native roughness 0.50` is the snow/ice primary-road family.
- Snowy Mountain primary road is 88.8% ID 0x17 and 11.2% ordinary ID 0x01.
- Ice Scape primary road is 100% ID 0x17.
- `0x16 -> mask 0x00400000` dominates Casino Town and hits the game's explicit Casino roughness exception.
- `0x14 -> mask 0x00100000 -> roughness 0.71` appears in short primary-road runs at Deep Lake, Tulip Garden and Floral Village.

FFB should therefore prefer the **runtime per-contact raw masks** over stage-name-wide material assumptions. The current snow/ice stage-wide attenuation can be refined to the proven `0x00800000` contact mask after normal FFB branch review/validation.

See `docs/reverse/STAGE_SURFACE_FFB_MAP.md`, `reverse/game_assets/stage_coli_ffb_map.json` and `tools/reverse/analyze_stage_coli.py`.


## Exact per-contact polygon identity

The canonical PC four-contact collision loop now exposes a stronger FFB correlation key than position alone.

- loop VA: `0x00475720`
- contact position input: `EVWORK_CAR::vector_130[i]`
- wheel-work pointer: `0x82EA38[i]`
- collision query: RVA `0x0003DB60`
- exact selected polygon output: `*(wheelWork[i] + 0x10) = collisionIndex`
- returned material mask: stored to `EVWORK_CAR+0x24C+4*i`

This allows deterministic joining of a runtime contact to the static Stage record:

```text
contact i
 -> collisionIndex
 -> materialId
 -> collisionFlags / localHeadingAngle
 -> subtype / roadSection
 -> surfaceMask
 -> native roughness
 -> DD-wheel output
```

The same reverse pass closes several other COLI fields:

- section0: 256×256 u16 spatial grid in collision-set-local coordinates.
- section1: `u16 count + u16 collisionIndex[count]` candidate lists.
- geometry tail: u16 collisionFlags + s16 localHeadingAngle.
- section5: collision topology/response selector, not material.
- section6: u16 road-section index.
- section8: four per-corner lighting/intensity bytes contributing to `EVWORK_CAR::lightRate_58`, not FFB surface identity.
- section7: still open.

### Contact ordering boundary

Per-car static contact positions are copied from the `0x46BBF0` table into `vector_130[0..3]` in this exact local topology:

```text
0 = -X / -Z side
1 = +X / -Z side
2 = -X / +Z side
3 = +X / +Z side
```

This proves pair topology, not final FL/FR/RL/RR names. The vehicle-local forward-axis sign still needs independent proof.

### Level1 validation anchors

Useful deterministic roadSection transitions:

- Snowy Mountain stage 4: sections `132..203` are ordinary ID01/mask `0x2`, inside an otherwise snow-dominant course.
- Ice Scape 19/49: primary `0..620` is ID17/mask `0x800000`.
- Deep Lake 1: `419..458` is ID14/mask `0x100000`.
- Tulip Garden 10: `54..70` is ID14.
- Floral Village 27: `510..533` is ID14.

Future telemetry should capture the exact contact collision indices; raw world position is secondary because the 256×256 grid is addressed only after the game's collision-set-local coordinate transform.
