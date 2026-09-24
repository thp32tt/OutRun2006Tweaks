# Stage collision / road-surface map for wheel FFB

This document turns the Stage asset inventory and current game/FFB source into a reusable road-surface evidence model.

> Evidence boundary: the uploaded `Stage.zip` (290,113,621 bytes) was successfully received/materialized, but raw ZIP extraction was blocked by the execution backend during this run. Exact per-triangle/region fields inside the newly uploaded Stage payload are therefore **not claimed as decoded here**. The inventory below is independently grounded by the previously supplied full game manifest and current source/runtime evidence.

## 1. Stage corpus — CONFIRMED inventory

The full game manifest contains:

- **847** files below `Stage/`
- **66** stage directories/variants
- **296,418,999 bytes** total for those Stage files as stored in the installation
- **72** `coli_*` collision assets
- **19,481,268 bytes** total compressed collision payload
- 456 `*_bin.sz`, 273 `*_pmt.sz`, 114 other `.sz` files, plus 4 other entries

There are 66 game stage IDs: 30 forward, 30 reverse and six Palm Beach/Sunny Beach time/night variants. The machine-readable mapping is in `reverse/game_assets/stage_collision_inventory.json`.

Six forward folders also carry a `coli_BK_*` file (CAPE, EAST, FLOR, MAYA, NEWY, PRIN). All six manifest sizes are exactly 11,706 bytes. They are tracked separately from the main course-surface `coli_CS_*` file and must not be assumed to contain road material until their consumer is proven.

## 2. Runtime contact fields — SOURCE-CONFIRMED

Current `EVWORK_CAR` contains:

```cpp
OnRoadPlace OnRoadPlace_5C;

uint32_t water_flag_24C[4];

struct OnRoadPlace {
    uint32_t loadColiType_0;
    uint32_t field_4;
    int16_t  roadSectionNum_8;
    uint8_t  field_A;
    uint8_t  unk_B;
    uint32_t curStageIdx_C;
};
```

Two semantic corrections matter for FFB.

### `water_flag_24C[4]` is effectively a per-wheel surface mask

The historical field name is misleading. The wheel code passes every element as the first argument of:

`sub_1149C0(surfaceMask, loadColiType, waterFlag)`

and the Xbox-derived routine branches over values from `0x1` through `0x800000`. Most of these cases have nothing specifically water-only about them.

For reverse-engineering and FFB documentation, use the semantic alias:

```text
surfaceMask[4] := EVWORK_CAR::water_flag_24C[4]
```

Do not rename the binary structure field in production merely for readability unless all call sites are audited.

### `loadColiType_0` is branch/junction context, not a proven material ID

Current source defines:

```cpp
bool is_in_bunki() {
    return OnRoadPlace_5C.loadColiType_0 != 0;
}
```

(`bunki` = branch/junction in the existing game terminology.)

Therefore `loadColiType` must be carried separately from material identity. It affects some original roughness decisions, but it should **not** be used as a surface enum.

## 3. Original surfaceMask -> roughness table — SOURCE-CONFIRMED

The Xbox-derived `sub_1149C0` provides the strongest currently known native material witness.

| surfaceMask | original roughness | notes |
|---:|---:|---|
| `0x000001` | 0.00 | semantic name open |
| `0x000002` | 0.25 normally | stage-dependent water behavior |
| `0x000004` | 0.70 | name open |
| `0x000008` | 0.85 | name open |
| `0x000010` | 0.90 | name open |
| `0x000080` | 0.85 | name open |
| `0x000100` | 0.45 | name open |
| `0x000200` | 0.35 | name open |
| `0x000400` | 0.30 | name open |
| `0x000800` | 0.35 | name open |
| `0x001000` | 0.35 | name open |
| `0x002000` | 0.35 | name open |
| `0x008000` | 0.40 | name open |
| `0x100000` | 0.71 | name open |
| `0x200000` | 0.80 | name open |
| `0x400000` | 0.90 normally | 0.25 in junction context; also 0.25 on Casino Town |
| `0x800000` | 0.50 | name open |
| unrecognized/fallback | about 0.31 | depends on branch |

### Proven stage-dependent `0x2` behavior

When `loadColiType == 0`, mask `0x2` sets the routine's water output for:

- stage 11 / 41 — Metropolis / reverse: **0.73**
- stage 13 / 43 — Cape Way / reverse: **0.79**
- stage 14 / 44 — Imperial Avenue / reverse: **0.76**

This proves that the same surface mask can have stage context. A future material database therefore needs the tuple:

`{stageId, surfaceMask, loadColiType}`

rather than a global one-dimensional “surface ID”.

## 4. Runtime road evidence already captured — CONFIRMED

Existing FFB logs contain real four-wheel transitions including:

- `0.35 -> 0.76` mixed contact, followed by all-wheel `0.76`
- `0.35 -> 0.85` mixed contact, followed by all-wheel `0.85`
- `0.25 -> 0.71` mixed contact, followed by all-wheel `0.71`
- snow/ice runs showing wheel sets around `0.25/0.35 .. 0.50`
- all-wheel `0.70` runs

This is useful validation of the Xbox-derived table, but roughness alone does not uniquely identify a mask:

- 0.35 has four known mask candidates;
- 0.85 has two;
- 0.25 has multiple context-sensitive paths.

Raw masks must therefore be logged before assigning names such as curb, grass or snow.

## 5. What FFB can safely use now

The recommended data pipeline is:

```text
COLI0200 static region/face attribute
        ↓  (still needs exact correlation)
runtime per-wheel surfaceMask[4]
        ↓
stageId + loadColiType/junction context
        ↓
original sub_1149C0 roughness
        ↓
semantic material profile
        ↓
modern DD-wheel effect
```

For a modern DD wheel, keep two layers separate:

**Game semantics**
- raw surface mask;
- stage/junction context;
- original roughness;
- water behavior;
- contact wheel.

**Wheel feel**
- RoadTexture amplitude/frequency;
- curb/edge pulse;
- grass/gravel-like texture once proven;
- snow/ice attenuation;
- splash event;
- SAT/grip/damper policy.

Do not directly turn Xbox rumble amplitude into wheel torque.

## 6. Improvement over current max-roughness reduction

The core FFB path currently takes the maximum roughness across four wheels. That is useful for a single road-texture intensity but loses information needed for good curb/shoulder feel.

For future FFB material logic, retain:

```text
surfaceMaskFL / FR / RL / RR
roughnessFL   / FR / RL / RR
```

and derive:

- `roughnessMin`
- `roughnessMax`
- `roughnessSpread`
- number of wheels on each raw mask
- front-versus-rear transition
- left-versus-right transition

This can distinguish “one side touching a curb” from “all four wheels on the same rough road” without guessing from stage name.

## 7. Required telemetry before changing behavior

A read-only diagnostic line should capture at low rate or on contact changes:

```text
stageId
roadSectionNum
curStageIdx
loadColiType
surfaceMask[4]
roughness[4]
waterFlag
speed
FFB road output
```

This is sufficient to correlate a driven location with the static Stage collision asset once the COLI face/region field is decoded.

## 8. Stage-file parsing next step

The shared analyzer already verifies `COLI0200` identity/header bounds and zlib SZ. It should additionally emit for every `Stage/*/coli_*.sz`:

- stage folder / stage ID / variant;
- compressed and inflated sizes;
- full collision SHA-256;
- header/count/offset fields;
- per-region/per-record candidate field histograms;
- cross-stage repeated values;
- forward/reverse similarities.

Candidate fields should remain anonymous (for example `record_u32_0C`) until a runtime mask correlation proves their meaning.

The goal is not merely a list of road types; it is a reproducible mapping that can eventually remove stage-name heuristics from FFB.


## 9. Independent Xbox cross-check — RetroReverse

An independent public reverse-engineering project, `StupidCoder/RetroReverse` at commit `e9d892e19825c518407e41144fb8050f9d3e6c50`, provides a useful cross-check against the Xbox C2C assets.

Its current OutRun 2006 Xbox notes independently report:

- `coli_CS_*_bin` self-describes as `{size, "COLI0200", counts, section offsets}`;
- 66 main COLI0200 course files are present;
- six old-format `COLI0105` leftovers also exist on the Xbox disc;
- the COLI sections/material meanings remain unopened in that project as well.

The same work later proves that the **visible road mesh** (asphalt, lane markings and kerbs) is ordinary rendered batch geometry inside decompressed `cs_CS_*_pmt.sz`. This is an important boundary for FFB:

```text
cs_CS_*_pmt.sz   -> visible/render road geometry + textures
coli_CS_*_bin.sz -> collision/contact geometry/data used for physics lookup
```

Visual texture identity must therefore not be substituted for collision material identity. It can be used only as a spatial cross-check after the runtime collision mask is correlated.


### Cross-platform contact-pipeline anchor

The same independent Xbox reverse project later corrected an earlier misidentification of `car+0x5C`: a write watch showed its only writer at Xbox `0x16902E`, described as contact write-back inside the `0x1692A0` per-car pipeline and fed by collision routine `0x168880`.

The PC fork independently places `OnRoadPlace_5C` at **exactly car offset +0x5C**. Function addresses are platform-specific and must not be copied to PC, but the structure/role agreement is valuable.

**PC next anchor:** find every canonical-EXE writer to `EVWORK_CAR + 0x5C`, then walk backward to the collision query and forward to the writes of per-wheel `surfaceMask` at `+0x24C..+0x258`. This is a stronger route to the COLI material field than guessing from static values.
