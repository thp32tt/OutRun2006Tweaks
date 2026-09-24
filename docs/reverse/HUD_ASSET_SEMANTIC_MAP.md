# HUD / Sprite / Sprani reverse map

Evidence baseline: `vr-d3d9ex-focus@3aff39d2d964c1df7d9085af058cbe2cc97e45ec`  
Canonical EXE SHA-256: `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`

This map joins the user-owned Sprite/Sprani assets to the canonical executable and the current VR semantic system. It is intended for both VR HUD work and Korean-localization resource work.

## 1. Canonical 75-slot XST table — CONFIRMED

The canonical executable contains five language pointer tables:

| language | table VA |
|---|---:|
| E | `0x00639CB8` |
| F | `0x00639DE4` |
| G | `0x00639F10` |
| I | `0x0063A03C` |
| S | `0x0063A168` |

Each table is exactly 75 pointers. Table spacing is `0x12C = 75 * 4`.

The loader around VA `0x0042DF49..0x0042DF55` obtains the language index, multiplies it by `0x4B` (75), adds the XST-set index, fetches the path pointer from the E-table base and calls the sprite/XST loader.

The English table has 50 non-null slots. Sixteen slot families have E/F/G/I/S path variants and therefore form a static localization resource boundary.

## 2. Exact packed sprite identity — CONFIRMED

`SPRARGS::xstnum_0` is a 32-bit packed identity.

Canonical helper VA `0x0042DDF0` decodes it as:

```text
xstSet      = packedId >> 16
spriteIndex = packedId & 0xFFFF
```

It validates `xstSet < 0x4B`, indexes the loaded XST-set state and then selects the sprite entry by the low 16-bit index.

Therefore a queued SpriteNode already contains an exact static asset join key:

```text
SpriteNode.args.xstnum_0
  -> XST set slot
  -> canonical language-specific pack
  -> sprite index
  -> XST sprite record
  -> texture index / UV geometry
```

This is independent evidence from caller-RVA semantic classification.

## 3. Sprani packed identity — CONFIRMED

The Sprani path uses the same high/low split at the animation level.

The entry path around VA `0x00428A10` splits a passed ID into:

```text
spraniSet = id >> 16
animIndex = id & 0xFFFF
```

and accepts Sprani/XST-set IDs in the 32..74 range.

The animation renderer later reaches VA `0x00428C0F`, loads a packed sprite identity from the animation draw record and calls the XST sprite resolver at `0x0042DDF0`.

Reusable provenance chain:

```text
Sprani (set, animation)
  -> animation draw record
  -> packed XST (set, sprite)
  -> XST sprite record
  -> texture/resource
```

This gives the HUD and localization projects a deterministic path from animation identity to actual texture asset.

## 4. Representative canonical slots

The supplied assets parse as follows:

| slot | family | textures | sprites | Sprani animations | localized E/F/G/I/S |
|---:|---|---:|---:|---:|---|
| 0 | FONT | 10 | 10 | - | no |
| 3 | ETC | 13 | 117 | - | no |
| 18 | SELECT | 6 | 136 | - | no |
| 19 | WARNING | 2 | 2 | - | no |
| 20 | NAME_ENTRY | 3 | 93 | - | no |
| 21 | RANKING | 2 | 50 | - | no |
| 32 | SPRANI_LOGO | 2 | 5 | 1 | no |
| 33 | LOGO | 2 | 5 | 1 | yes |
| 34 | TITLE_CVT | 6 | 15 | 4 | no |
| 43 | GAME_CVT | 7 | 338 | 108 | yes |
| 44 | ETC_CVT | 11 | 698 | 319 | yes |
| 45 | FIGHT | 1 | 34 | 11 | yes |
| 46 | SELECTOR_CVT | 38 | 523 | 96 | yes |
| 47 | LOADING_CVT | 5 | 18 | 9 | yes |
| 50 | ADV_CVT | 12 | 197 | 30 | no |
| 51 | COMMON | 4 | 5 | 2 | no |
| 52 | ROUTE_CVT | 12 | 80 | 32 | yes |
| 53 | ENDING | 7 | 141 | 20 | no |
| 54 | NAME_CMN | 8 | 126 | 15 | no |
| 61 | RANKING_CVT | 3 | 108 | 41 | yes |
| 68 | SUMO_FE_CVT | 129 | 1,564 | 224 | yes |
| 70 | FRUITY_CVT | 2 | 195 | 103 | yes |
| 72 | SUMO_LOADING | 4 | 5 | 2 | yes |
| 73 | SUMO_VSLOAD | 4 | 278 | 32 | yes |
| 74 | TAEXTRA | 1 | 140 | 20 | no |

The vehicle meter slots are also small and regular: slots 35..42 and 48..49 each use two textures/two sprites with a one-animation Sprani bank.

The largest major UI pack in this set is `SUMO_FE_CVT`: 129 textures, 1,564 sprites and 224 top-level animations. Asset size alone must not be interpreted as runtime draw count.

## 5. Current VR semantic system and the new join

The current renderer intentionally uses exact producer/node semantics first and generic canonical SpriteNode queue membership only as a fallback.

Current generic fallback:
`canonical SpriteNode queue -> SCREEN_OVERLAY_2D`.

Exact producer scopes include `SCREEN_HUD` and `WORLD_BILLBOARD`.

The new static identity should therefore be used as **provenance**, not as a blind classifier:

```text
producer/caller semantic
+ exact SpriteNode identity (xstSet,spriteIndex)
+ optional Sprani (set,animation)
+ runtime node epoch/WVP evidence
= semantic decision / diagnostic evidence
```

Do not classify every GAME/RANKING sprite as screen HUD. Rival markers can use sprite resources while remaining world-attached.

## 6. B_HUD experiment scope

Current matrix B_HUD source:
`7e2095aa2156f6a9dd301d2899b0e62b4d92f4f1`.

Its behavior-changing commit `f6a91063...` fixes one specific semantic-lifetime problem: a c64 upload can be accepted as world before the canonical SpriteNode semantic becomes current. Once the exact draw is later proven `SCREEN_HUD`, that earlier timing artifact must not veto the HUD path.

This is a valid narrow fix, but it does not by itself solve every remaining HUD family.

### Fixed-function / no-VS HUD path is already implemented; remaining gap is semantic coverage

The R51 runtime capture observed genuine `vsPtr=0 / vsHash=0` states, but current source already has a dedicated fixed-function path:

- `R30PrepareXyzrhwState` explicitly requires no current vertex shader and `D3DFVF_XYZRHW`.
- `R30ConfigureXyzrhwWorldEffect` treats exact `SCREEN_HUD` and generic queue `SCREEN_OVERLAY_2D` as authoritative non-world semantics.
- it constructs the same finite recentered world-locked HUD plane and transforms XYZRHW vertices per eye.
- unknown XYZRHW draws still fail closed unless they have strong projected-depth world evidence.

Therefore a remaining white/fixed-function HUD draw is **not** evidence that R30 lacks a no-VS HUD owner. If it reaches no screen/XYZRHW semantic counters, the next question is whether the exact SpriteNode scope was active at that draw and whether the draw met the XYZRHW/FVF entry contract.

Next diagnostic should capture, only for the failing exact producer:
`semantic scope + packed xstnum + current node + FVF + primitive path + XYZ/RHW sample + fallback reason`.

Do not create a second broad fixed-function HUD classifier.

### Rival-marker world anchor remains a distinct boundary

The rank-marker producer first projects the rival-car position with `Calc3D2D`, then queues 2D sprite content. Tagging the resulting SpriteNode as `WORLD_BILLBOARD` does not restore the original 3D vehicle anchor. A correct world-attached marker needs that anchor preserved through the semantic metadata and projected separately per eye.

## 7. Rank-marker node-count correction

An earlier hypothesis suggested the 4th+ `put_clip_sprite` route might append multiple nodes while the hook tagged only the final one.

Canonical EXE falsifies that hypothesis for a single call:

- `put_clip_sprite`: RVA `0x0002D280` / VA `0x0042D280`
- it builds one SPRARGS and calls `put_sprite_ex` exactly once at VA `0x0042D2EC`

Therefore the existing tail-before/tail-after tag is sufficient for that one `put_clip_sprite` invocation.

The 1st/2nd/3rd route through `sprani_play_ae_auth_alpha` is different: Sprani can expand an animation into sprite draw records. The current wrapper records only one final tail per priority after the animation call. **Whether the concrete rank animations emit more than one node at a priority still needs exact animation-record verification.** Track this as an investigation, not as a proven bug.

## 8. Localization reuse

The same exact IDs are directly useful to the Korean project:

```text
menu/HUD producer
 -> packed sprite or Sprani ID
 -> exact XST slot
 -> language variant path
 -> sprite index / texture index
 -> translated texture payload
```

This avoids translating an entire large texture family blindly when only a subset of sprites is reachable from the target UI flow.

## 9. Next deterministic work

1. Extend HUD Inspector rows with packed `xstnum` decoding: set + sprite index + canonical pack name.
2. When a Sprani producer is known, log set + animation index and child sprite identities.
3. Verify the exact rank-marker Sprani animations for child-node cardinality.
4. Carry the original rival-car world anchor through `WORLD_BILLBOARD` metadata.
5. Add a fixed-function exact-HUD owner scoped only to proven producer/node semantics.
6. Keep the static XST family as supporting evidence, never as the sole screen/world classifier.

Machine-readable map: `reverse/game_assets/hud_xst_slot_map.json`.  
Reproducer: `tools/reverse/analyze_hud_assets.py`.
