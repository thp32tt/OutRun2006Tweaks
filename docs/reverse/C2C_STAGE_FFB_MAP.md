# C2C Stage / Surface FFB Map

This map records stage and road-surface evidence that is safe to use in the standalone wheel-FFB branch. It is deliberately separate from all VR work.

## Evidence sources

- the original-mod game stage table in `src/game_addrs.hpp`;
- the reconstructed Xbox `CalcVibrationValues()` and `sub_1149C0()` in `src/hooks_forcefeedback.cpp`;
- the supplied full game-file manifest, which shows a `coli_CS_*_bin.sz` collision file for each stage variant and a smaller set of `coli_BK_*_bin.sz` background-collision assets;
- hardware FFB logs that expose four-wheel roughness transitions.

The historical member name `EVWORK_CAR::water_flag_24C[4]` is misleading for FFB analysis. The Xbox routine passes those four values directly to `sub_1149C0()` as **per-wheel surface masks** (FL/FR/RL/RR). Water is instead reported by the output flag supplied to `sub_1149C0()`.

`OnRoadPlace_5C.loadColiType_0` is a collision-context input. It must not be treated as a surface/material ID.

## Stage IDs

The game's unique-stage table contains 66 entries:

| IDs | stages |
| --- | --- |
| 0-14 | Palm Beach; Deep Lake; Industrial Complex; Alpine; Snowy Mountain; Cloudy Highland; Castle Wall; Ghost Forest; Coniferous Forest; Desert; Tulip Garden; Metropolis; Ancient Ruins; Cape Way; Imperial Avenue |
| 15-29 | Sunny Beach; Big Forest; Waterfalls; Casino Town; Ice Scape; Canyon; Bay Area; Jungle; Lost City; National Park; Legend; Skyscrapers; Floral Village; Milky Way; Giant Statues |
| 30-44 | reverse variants of IDs 0-14 |
| 45-59 | reverse variants of IDs 15-29 |
| 60-65 | (T) Palm Beach; (T) Sunny Beach; (Night) Palm Beach; (Night) Sunny Beach; (R-Night) Palm Beach; (R-Night) Sunny Beach |

FFB stage groups currently backed by code evidence:

- snow/ice attenuation: unique IDs `4, 19, 34, 49`;
- surface-mask `0x2` can report water only on IDs `11, 13, 14, 41, 43, 44` when collision context is zero;
- surface-mask `0x400000` resolves to the low `0.25` value on IDs `18, 48` when collision context is zero; on most other zero-context stages it resolves to `0.90`.

Do not infer extra stage-specific force tuning from scenery names alone. Stage identity is used only where the original surface/vibration code proves a semantic difference.

## Reconstructed surface roughness LUT

`sub_1149C0(surfaceMask, collisionContext, waterFlag)` maps the mask approximately as follows:

| Surface mask | roughness | notes |
| ---: | ---: | --- |
| `0x1` | 0.00 | exact |
| `0x2` | 0.25 / 0.73 / 0.79 / 0.76 | stage/context dependent; the three high values also set the water output flag |
| `0x4` | 0.70 | exact |
| `0x8` | 0.85 | exact |
| `0x10` | 0.90 | exact |
| `0x80` | 0.85 | exact |
| `0x100` | 0.45 | exact |
| `0x200` | 0.35 | exact |
| `0x400` | 0.30 | exact |
| `0x800` | 0.35 | exact |
| `0x1000` | 0.35 | exact |
| `0x2000` | 0.35 | exact |
| `0x8000` | 0.40 | exact |
| `0x100000` | 0.71 | exact |
| `0x200000` | 0.80 | exact |
| `0x400000` | 0.25 / 0.90 | collision/stage dependent |
| `0x800000` | 0.50 | exact |
| other/unmatched | 0.31 | fallback |

For `0x2`, non-zero collision context forces `0.25`. With zero context the water cases are:

- Metropolis / reverse (11 / 41): `0.73`;
- Cape Way / reverse (13 / 43): `0.79`;
- Imperial Avenue / reverse (14 / 44): `0.76`.

For `0x400000`, non-zero collision context forces `0.25`. With zero context, Casino Town / reverse (18 / 48) also return `0.25`; other stages return `0.90`.

## FFB integration rule

The standalone DD-wheel layer now preserves, per wheel:

- raw surface mask;
- resolved roughness;
- validity;
- water classification from the original LUT;
- non-water min/max roughness;
- collision context;
- current unique stage identity.

This allows the compatibility wrapper to distinguish a true rough curb/shoulder from stage-specific water. **Water is not promoted into the fixed curb-strength/SAT-unload path.** It remains visible to the core, which already owns water/splash behavior. A rough non-water wheel can still trigger the curb compatibility envelope even if another wheel is simultaneously in water.

Snow/ice keeps the existing mixed-contact material latch and 450 ms bounded hold. This map does not weaken that tested behavior.

## Runtime diagnostics

On stage change:

`WheelFFB STAGE: ... unique=... name=... snowIce=... mask2CanMarkWater=... mask400000Low=...`

During significant road/water contact:

`WheelFFB ROAD: ... nonWaterMin=... nonWaterMax=... waterWheels=... masks=... rough=... collisionCtx=...`

These fields are intended to turn future hardware logs into evidence for additional bounded FFB changes instead of guessing material meanings from stage appearance.
