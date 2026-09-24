# Stage COLI0200 / road-surface map for wheel FFB — v3

Evidence date: 2026-09-24 KST  
Input: user-supplied `Stage.zip` (290,113,621 bytes)  
ZIP SHA-256: `385a5be540d87139c065bb5d62899767ca57c9a26950f7c2819235aa1448e6f6`  
Canonical EXE SHA-256: `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`

This revision directly parses the Stage archive and cross-references the canonical PC executable. It supersedes v2 where the last four geometry bytes were described as one u32 flag field and sections 0/1/8 remained only partially understood.

## 1. Corpus

- collision archives: **72**
- current `COLI0200` course files: **66**
- legacy `COLI0105` background files: **6**
- material IDs observed: `01,02,03,04,05,07,08,09,0A,0B,0C,0E,10,11,12,13,14,16,17,18,19`
- primary-road material IDs: **01, 14, 16, 17**

## 2. Header / section model

Offsets in the nine-entry section table are relative to `file + 4`.

| File offset | Meaning |
|---:|---|
| `0x00` | payload size |
| `0x04` | `COLI0200` |
| `0x0C` | total collision count |
| `0x10` | descriptive `primaryRoadCollisionCount`; original symbol unknown |
| `0x14..` | nine section-relative offsets |

The early header also carries the developer marker `NEW COLL FMT`.

### Section 0 — 256×256 spatial grid

Exactly 131,072 bytes = 65,536 × u16.

Canonical helper RVA `0x0003BB40` / VA `0x0043CB40` converts two **collision-set-local** coordinates to a grid key:

```text
cell = clamp(int((coord + 3072.0) / 6.0), 0, 255)
key  = cellB * 256 + cellA
```

Important: collision query RVA `0x3DB60` first transforms the input contact/world point into collision-set-local coordinates. Do not feed raw `EVWORK_CAR::position_14` directly into this grid.

### Section 1 — candidate collision lists

Section-0 u16 values index section 1 in u16 units. A list is:

```text
u16 count
u16 collisionIndex[count]
```

All unique referenced lists across all 66 current files were bounds-checked. No candidate index exceeded the file's collision count. Per-file unique valid list counts range roughly 541..853; maximum observed candidate-list length is 113.

### Section 2 — material IDs: CONFIRMED

`u8 materialId[collisionCount]`.

Canonical PC code at VA `0x0043ECB8..0x0043ECC7` proves:

```text
materialId = materialArray[collisionIndex]
surfaceMask = 1u << materialId
```

### Section 3 — collision quad record: corrected exact 64-byte layout

```text
0x00 vec3 corner0
0x0C vec3 corner1
0x18 vec3 corner2
0x24 vec3 corner3
0x30 vec3 center
0x3C u16 collisionFlags
0x3E s16 localHeadingAngle
```

This corrects the older v2 `u32 flags` description.

Evidence:

- RVA `0x3C440` returns the u16 at record +`0x3C`; body-collision code writes it to `EVWORK_CAR+0x25C`.
- downstream gameplay code tests flag bits including `0x10`, `0x80`, `0x100` and combined `0x110`.
- RVA `0x3C340` reads signed word +`0x3E`, combines it with stage heading using constant `10430.3779296875 = 65536/(2π)`. It is therefore a local collision/road heading in the game's 16-bit binary-angle domain.

Flag-bit human names are still OPEN.

### Section 4 — four corner normals

48 bytes/record:

```text
vec3 normal0
vec3 normal1
vec3 normal2
vec3 normal3
```

Consumed by the canonical collision solver. Most material families are overwhelmingly upward-facing, so normal direction alone does **not** justify assigning names such as grass/curb/wall.

### Section 5 — collision topology/response selector

One byte per collision record.

At VA `0x0050422D`, the game uses the low nibble to index the 16-byte table at VA `0x005E0DE0`:

```text
00 01 01 C2 00 01 01 C2 01 42 02 03 01 42 02 03
```

The surrounding routine uses the low/high nibbles to reselect/reorder quad edge/corner vectors. Therefore section 5 is a **collision topology/response selector**, not surface material.

All records in the primary-road families `01/14/16/17` use subtype 0.

### Section 6 — road-section index

`u16[collisionCount]`.

The body-collision path reads `0x780228[collisionSet][collisionIndex]` and writes it to:

```text
EVWORK_CAR + 0x64
= OnRoadPlace_5C.roadSectionNum_8
```

This gives a deterministic bridge between a static polygon and runtime `roadSectionNum`.

### Section 7

Nested-offset data relocated by the loader. Semantic role remains **OPEN**.

### Section 8 — per-corner lighting/intensity values

Approximately four bytes per collision record, padded to alignment.

RVA `0x3C130` reads four bytes and converts each to float using `1/255`. Caller `0x4A45F0` combines these values with the collision quad and vehicle position, then smooths the result into `EVWORK_CAR::lightRate_58`.

Therefore these are best described as **four per-corner lighting/intensity coefficients**. They are not FFB material IDs and must not be mixed into surface-feel classification.

## 3. Native material -> surfaceMask -> FFB contract

Collision surface query:

```text
RVA 0x0003DB60 / VA 0x0043EB60
```

Exact material conversion:

```asm
0043ECB8  load per-stage material array
0043ECBF  materialId = material[collisionIndex]
0043ECC2  eax = 1
0043ECC7  eax <<= materialId
```

Four contact calls store returned masks at:

```text
EVWORK_CAR +0x24C
EVWORK_CAR +0x250
EVWORK_CAR +0x254
EVWORK_CAR +0x258
```

Thus:

```text
COLI polygon
 -> collisionIndex
 -> materialId
 -> 1 << materialId
 -> contact surfaceMask
 -> sub_1149C0
 -> original roughness
 -> modern DD-wheel policy
```

## 4. Per-contact exact polygon identity

The four-contact collision loop at VA `0x00475720` iterates `i=0..3`.

For each contact it uses:

- `EVWORK_CAR::vector_130[i]`
- wheel-work pointer `0x82EA38[i]`
- collision query RVA `0x3DB60`
- output collision-index pointer = `wheelWork[i] + 0x10`

The query writes the selected **exact collisionIndex** to that output pointer. This is stronger telemetry than reconstructing the polygon from vehicle position.

Recommended runtime correlation:

```text
contact i
 -> wheelWork[i]+0x10 collisionIndex
 -> static materialId / flags / heading / subtype / roadSection
 -> runtime surfaceMask
 -> FFB output
```

## 5. Body/general collision state

The separate body/general collision path around VA `0x0047BA30` reveals additional currently unnamed `EVWORK_CAR` fields:

| Car offset | Proven role |
|---:|---|
| `+0x230` | body/general collisionIndex |
| `+0x248` | body/general surfaceMask |
| `+0x25C` | collisionFlags from record +0x3C |
| `+0x5C` | `OnRoadPlace.loadColiType` / collision-set context |
| `+0x64` | `OnRoadPlace.roadSectionNum` |

These are useful semantic aliases for reverse diagnostics. Production struct renaming should remain a separate reviewed change.

## 6. Four-contact geometry/order — partially closed

Function VA `0x0046BBF0` returns per-car local wheel/contact geometry from:

```text
car-kind table + 0x98 + contactIndex*0x20
```

VA `0x004A58EC` copies the first vec3 from those four records directly into `EVWORK_CAR::vector_130[0..3]`.

Across inspected car types the order is consistently:

```text
index 0 = (-X, Y, -Z side)
index 1 = (+X, Y, -Z side)
index 2 = (-X, Y, +Z side)
index 3 = (+X, Y, +Z side)
```

Example car 0:

```text
0 (-0.810, 0.323, -1.200)
1 (+0.810, 0.323, -1.200)
2 (-0.801, 0.339, +1.380)
3 (+0.801, 0.339, +1.380)
```

The game also contains matching direction vectors:
`(-x,-z), (+x,-z), (-x,+z), (+x,+z)`.

This **proves the lateral/longitudinal pairing topology**, but the final human labels FL/FR/RL/RR remain OPEN until the game's forward-axis convention is independently proven. Do not guess it from generic D3D convention.

## 7. Primary-road material map

| ID | mask | native roughness | proven/observed role |
|---:|---:|---:|---|
| `01` | `0x00000002` | 0.25 normally | default primary road; wet-stage overrides |
| `14` | `0x00100000` | 0.71 | special rough primary-road strips; physical name open |
| `16` | `0x00400000` | 0.90 normally / 0.25 Casino | Casino Town primary family |
| `17` | `0x00800000` | 0.50 | Snowy Mountain / Ice Scape snow-ice road |

All other material IDs are non-primary in this corpus. Their numeric IDs/masks/native roughness are known, but physical labels remain OPEN.

## 8. High-value stage/roadSection regression ranges

These ranges let a Level1 FFB log validate material transitions using `roadSectionNum` without visually identifying the polygon.

### Snowy Mountain (stage 4)

Material `17` / mask `0x00800000`:
`0-31,33-84,86-97,99-131,204-248,250-270,272-328,330-373,375-401,403-419,421-502,504-534,536-569,571-572,574-600,602-610,612-645,647-680`

Ordinary material `01` / mask `0x2`:
`32,85,98,132-203,249,271,329,374,402,420,503,535,570,573,601,611,646`

The large ordinary-road block `132-203` is especially useful for proving that stage-wide snow attenuation is too broad.

### Snowy Mountain reverse (34)

Ordinary material `01`:
`34,69,79,107,110,145,177,260,278,306,351,409,431,477-548,582,595,648`

Other primary sections are material `17`.

### Ice Scape (19 / 49)

All primary road sections `0-620` are material `17`.

### Deep Lake

Forward ID14 rough strip: `419-458`.  
Reverse ID14 rough strip: `218-257`.

### Tulip Garden

Forward ID14: `54-70`.  
Reverse ID14: `571-587`.

### Floral Village

Forward ID14: `510-533`.  
Reverse ID14: `136-159`.

### Casino Town

Forward material `16`:
`7-18,56-86,88-255,257-380,511-656`

Forward material `01`:
`0-6,19-55,87,256,381-510,657-661`

Reverse material `16`:
`5-150,281-404,406-573,575-605,643-654`

Reverse material `01`:
`0-4,151-280,405,574,606-642,655-661`

### Wet-road stage exceptions

Metropolis primary material is ID01 over road sections `0-659`.  
Cape Way primary material is ID01 over `0-580`.  
Imperial Avenue primary material is ID01 over `0-653`.

Their different native roughness/water behavior therefore comes from the explicit stage logic in `sub_1149C0`, not a different COLI material byte.

## 9. FFB implementation implications

### Snow/Ice

Current runtime applies `SnowIceRoadTextureScale` to whole stages 4/19/34/49.

Direct data proves a better policy candidate:

```text
materialId 0x17
<=> surfaceMask 0x00800000
<=> snow/ice primary-road material
```

Snowy Mountain is mixed: 88.8% ID17 and 11.2% ordinary ID01. Ice Scape is 100% ID17. Therefore per-contact mask gating can preserve real ordinary-road patches.

Tracked implementation candidate: `FFB-SURFACE-MASK-POLICY-001`.

### Preserve exact contact identity before reducing

Keep:

```text
collisionIndex[0..3]
surfaceMask[0..3]
materialId[0..3]
nativeRoughness[0..3]
```

before any max/mean reduction. This supports asymmetric edge/curb/shoulder feel once physical material names are confirmed.

## 10. Next reverse target: human material names

Other game systems OR the four surface masks and test aggregate bit sets around several functions, including masks such as `0x02003B00` and `0x02F03F82`. These are promising particle/sound/surface-effect consumers.

They are **not yet named**. The next safe path is:

```text
materialId
 -> surfaceMask
 -> effect/sound branch
 -> particle / sound asset identity
 -> human surface name
```

Tracked research key: `SURFACE-MASK-EFFECT-CONSUMERS-001`.

## 11. Evidence boundary

**CONFIRMED**
- grid and candidate-list structure;
- materialId -> surfaceMask;
- exact 64-byte geometry split including u16 flags + s16 heading;
- four 48-byte corner normals;
- subtype/topology role;
- roadSection u16 path;
- section8 lighting/intensity role;
- exact per-contact collisionIndex storage;
- contact local-position topology.

**OPEN**
- section7 meaning;
- individual collision flag-bit names;
- final FL/FR/RL/RR labels;
- physical labels for non-primary material IDs;
- exact particle/sound semantics of aggregate surface-mask consumers.

Machine-readable summary: `reverse/game_assets/stage_coli_ffb_map.json`  
Reproducer: `tools/reverse/analyze_stage_coli.py`.
