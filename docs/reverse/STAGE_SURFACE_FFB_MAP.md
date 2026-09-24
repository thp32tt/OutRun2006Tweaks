# Stage COLI0200 / road-surface map for wheel FFB — v2

Evidence date: 2026-09-24 KST  
Input: user-supplied `Stage.zip` (290,113,621 bytes)  
ZIP SHA-256: `385a5be540d87139c065bb5d62899767ca57c9a26950f7c2819235aa1448e6f6`  
Canonical EXE SHA-256: `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`

This revision directly parses the uploaded Stage archive and cross-references the canonical PC executable. It supersedes the previous inventory-only analysis.

## 1. Corpus

- collision archives: **72**
- `COLI0200` current course files (`coli_CS_*`): **66**
- legacy `COLI0105` background files (`coli_BK_*`): **6**
- current material IDs observed: `01,02,03,04,05,07,08,09,0A,0B,0C,0E,10,11,12,13,14,16,17,18,19`
- material IDs observed in the primary road region: **01, 14, 16, 17 only**

## 2. COLI0200 layout now decoded enough for FFB

Offsets stored in the file are relative to `file + 4` (the payload-size prefix is outside the collision object proper).

| section | record/layout | status / use |
|---|---|---|
| section 0 | 131,072 bytes = 65,536 × u16 | spatial lookup/bucket map; collision-query acceleration |
| section 1 | variable | candidate-list data used by the collision query |
| section 2 | `u8 materialId[collisionCount]` | **CONFIRMED** material array |
| section 3 | 64 B/record | **CONFIRMED**: `vec3 corner[4] + vec3 center + u32 flags` |
| section 4 | 48 B/record | **CONFIRMED**: `vec3 normal[4]` |
| section 5 | `u8[collisionCount]` | collision subtype/class; low nibble is consumed through canonical table VA `0x5E0DE0`; names open |
| section 6 | `u16[collisionCount]` | road-section index family; compared with `OnRoadPlace::roadSectionNum` |
| section 7 | variable | open |
| section 8 | variable | open |

The 64-byte geometry relationship and 48-byte normal relationship hold across all **66/66 COLI0200 files**.

The second header count at file offset `0x10` behaves as the **primary/main-road collision record count**. For all 66 files, the first `primaryCount` subtype/class entries are zero, and their material distribution maps cleanly to the course's main-road surface families. The exact original symbol name is unknown, so tooling preserves the descriptive name `primaryRoadCollisionCount`.

## 3. PC executable proves materialId -> surfaceMask

The canonical PC executable makes the link directly.

Collision surface query at VA `0x0043EB60` / RVA `0x0003DB60` reaches:

```asm
0043ECB8  mov  0x780100(,stage,4), ecx   ; material array base
0043ECBF  mov  byte ptr [edi+ecx], cl    ; materialId = material[collisionIndex]
0043ECC2  mov  1, eax
0043ECC7  shl  eax, cl                    ; surfaceMask = 1u << materialId
```

The per-wheel caller then stores the returned masks at:

```text
004757FA -> EVWORK_CAR + 0x24C
00475807 -> EVWORK_CAR + 0x250
00475814 -> EVWORK_CAR + 0x254
00475821 -> EVWORK_CAR + 0x258
```

These are the existing `water_flag_24C[4]` fields. The historical name is misleading: they are four contact **surface masks**.

The same collision query uses:

- `0x780110[stage]` at 64-byte stride for collision geometry;
- `0x780120[stage]` at 48-byte stride for per-corner normals;
- `0x780100[stage]` for the material byte array.

Therefore the end-to-end relation is now **CONFIRMED**, not inferred:

```text
COLI0200 collision polygon
  -> materialId byte
  -> surfaceMask = 1 << materialId
  -> EVWORK_CAR surfaceMask[0..3]
  -> sub_1149C0(surfaceMask, loadColiType, waterFlag)
  -> original roughness
  -> modern wheel FFB policy
```

## 4. Material ID / mask / original roughness map

| material ID | surfaceMask | original roughness | observed role |
|---:|---:|---:|---|
| `01` | `0x00000002` | 0.25 normally | **default primary road**; stage overrides below |
| `02` | `0x00000004` | 0.70 | non-primary; semantic name open |
| `03` | `0x00000008` | 0.85 | non-primary; name open |
| `04` | `0x00000010` | 0.90 | non-primary; name open |
| `05` | `0x00000020` | ~0.31 fallback | non-primary; name open |
| `07` | `0x00000080` | 0.85 | non-primary; name open |
| `08` | `0x00000100` | 0.45 | non-primary; name open |
| `09` | `0x00000200` | 0.35 | non-primary; name open |
| `0A` | `0x00000400` | 0.30 | non-primary; name open |
| `0B` | `0x00000800` | 0.35 | non-primary; name open |
| `0C` | `0x00001000` | 0.35 | non-primary; name open |
| `0E` | `0x00004000` | ~0.31 fallback | non-primary; name open |
| `10` | `0x00010000` | ~0.31 fallback | non-primary; name open |
| `11` | `0x00020000` | ~0.31 fallback | non-primary; name open |
| `12` | `0x00040000` | ~0.31 fallback | non-primary; name open |
| `13` | `0x00080000` | ~0.31 fallback | non-primary; name open |
| `14` | `0x00100000` | **0.71** | **special rough primary-road strip** in Deep Lake, Tulip Garden, Floral Village; exact physical name open |
| `16` | `0x00400000` | 0.90 normally; **0.25 Casino Town** | **Casino Town primary-road family** |
| `17` | `0x00800000` | **0.50** | **Snowy Mountain / Ice Scape snow-ice primary road** |
| `18` | `0x01000000` | ~0.31 fallback | non-primary; name open |
| `19` | `0x02000000` | ~0.31 fallback | non-primary; name open |

Do not invent labels such as grass/curb/wall for the non-primary IDs yet. The static files prove the ID and native roughness path; physical names still need driven runtime correlation.

## 5. Main-road surface inventory — forward stages

| ID | Stage | primary records | material distribution / effective native roughness |
|---:|---|---:|---|
| 0 | Palm Beach | 1283 | `01` 100% -> 0.25 |
| 1 | Deep Lake | 1325 | `01` 95.3% -> 0.25; `14` 4.7% -> **0.71** |
| 2 | Industrial Complex | 635 | `01` 100% -> 0.25 |
| 3 | Alpine | 1638 | `01` 100% -> 0.25 |
| 4 | Snowy Mountain | 1549 | `17` **88.8% -> 0.50**; `01` 11.2% -> 0.25 |
| 5 | Cloudy Highland | 1378 | `01` 100% -> 0.25 |
| 6 | Castle Wall | 1515 | `01` 100% -> 0.25 |
| 7 | Ghost Forest | 1489 | `01` 100% -> 0.25 |
| 8 | Coniferous Forest | 1453 | `01` 100% -> 0.25 |
| 9 | Desert | 1472 | `01` 100% -> 0.25 |
| 10 | Tulip Garden | 1372 | `01` 97.2%; `14` 2.8% -> **0.71** |
| 11 | Metropolis | 1378 | `01` 100%; stage override -> **0.73 + water flag** |
| 12 | Ancient Ruins | 1551 | `01` 100% -> 0.25 |
| 13 | Cape Way | 1413 | `01` 100%; stage override -> **0.79 + water flag** |
| 14 | Imperial Avenue | 1448 | `01` 100%; stage override -> **0.76 + water flag** |
| 15 | Sunny Beach | 1113 | `01` 100% -> 0.25 |
| 16 | Big Forest | 1424 | `01` 100% -> 0.25 |
| 17 | Waterfalls | 1388 | `01` 100% -> 0.25 |
| 18 | Casino Town | 830 | `16` **78.2% -> 0.25 Casino exception**; `01` 21.8% -> 0.25 |
| 19 | Ice Scape | 1439 | `17` **100% -> 0.50** |
| 20 | Canyon | 1332 | `01` 100% -> 0.25 |
| 21 | Bay Area | 1134 | `01` 100% -> 0.25 |
| 22 | Jungle | 1406 | `01` 100% -> 0.25 |
| 23 | Lost City | 1325 | `01` 100% -> 0.25 |
| 24 | National Park | 1466 | `01` 100% -> 0.25 |
| 25 | Legend | 1607 | `01` 100% -> 0.25 |
| 26 | Skyscrapers | 855 | `01` 100% -> 0.25 |
| 27 | Floral Village | 1504 | `01` 96.5%; `14` 3.5% -> **0.71** |
| 28 | Milky Way | 1769 | `01` 100% -> 0.25 |
| 29 | Giant Statues | 1511 | `01` 100% -> 0.25 |

Reverse stages use stage IDs +30. Their primary material counts match the corresponding forward surface families; some files differ in non-primary collision geometry/material ordering, so runtime masks remain authoritative.

Special Palm/Sunny Beach variants (IDs 60..65) use material `01` for their primary road region.

## 6. Immediate FFB implications

### 6.1 Replace the snow/ice stage-name heuristic with the proven material mask

Current DD FFB applies `SnowIceRoadTextureScale` to the whole stage for stage IDs 4/19/34/49. Static collision data proves a better discriminator:

```text
materialId 0x17
<=> surfaceMask 0x00800000
<=> actual snow/ice primary-road material
```

This matters on **Snowy Mountain**: 174 of 1549 primary road polygons (11.2%) are ordinary material `01`, while 1375 are snow/ice `17`. A stage-wide multiplier suppresses both; a mask-based multiplier can affect only real snow/ice contact. Ice Scape is 100% material `17` in the primary-road range.

Recommended implementation key: `FFB-SURFACE-MASK-POLICY-001`.

### 6.2 Keep four contacts instead of reducing immediately to max roughness

Because each contact receives its own mask, retain:

```text
surfaceMask[0..3]
materialId[0..3] = countr_zero(surfaceMask[i]) for one-hot nonzero masks
roughness[0..3]
```

Then derive max/mean/spread, mask counts and transition events. Do **not** label the indices FL/FR/RL/RR until wheel ordering is separately proven.

### 6.3 Static map is a regression oracle, not the runtime decision source

Runtime masks are authoritative. Useful static expectations:

- Ice Scape primary road: `0x00800000`.
- Snowy Mountain: mostly `0x00800000`, with real `0x00000002` road patches.
- Casino Town: substantial `0x00400000` roadway, but original roughness is 0.25 there by explicit stage exception.
- Deep Lake / Tulip Garden / Floral Village: short `0x00100000` rough-road runs -> 0.71.
- Metropolis / Cape Way / Imperial Avenue: material `01`, but original routine intentionally applies stage wet-road overrides.

## 7. Telemetry for the next FFB validation run

Log on mask changes plus a low-rate heartbeat:

```text
stageId
roadSectionNum
curStageIdx
loadColiType
for contact[0..3]:
    surfaceMask
    derivedMaterialId
    nativeRoughness
waterFlagAggregate
speedNorm
roadAmp
roadFreq
```

The exact contact-index-to-wheel-name order remains OPEN.

## 8. Evidence boundaries

**CONFIRMED**
- 72 collision files are directly readable from the uploaded ZIP: 66 COLI0200 + 6 COLI0105.
- material array and `surfaceMask = 1 << materialId` are linked by canonical PC EXE code.
- 64-byte geometry and 48-byte per-corner normal arrays are consumed by the canonical collision query.
- four returned masks are written to `EVWORK_CAR +0x24C..+0x258`.

**STRONG descriptive naming**
- file `0x10` count is called `primaryRoadCollisionCount` from its behavior; original symbol name is unknown.
- section 6 is called road-section-index family because it is directly compared with `OnRoadPlace::roadSectionNum`.

**OPEN**
- human physical names for non-primary material IDs (curb/grass/gravel/wall/etc.).
- contact index -> FL/FR/RL/RR order.
- section 7/8 semantics.

Machine-readable map: `reverse/game_assets/stage_coli_ffb_map.json`.  
Reproducer: `tools/reverse/analyze_stage_coli.py`.
