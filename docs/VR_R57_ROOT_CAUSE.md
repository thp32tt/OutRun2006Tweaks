# R57 HUD / Rank Root-Cause Analysis

## Why R56 is not enough

R55 already proved that the generic HUD coordinate path is live: zero-disparity, obvious 35% scale, and finite HUD-plane variants visibly change ordinary HUD. Repeating those same equations as R56 01-04 adds little new information.

The remaining defects are ownership/provenance defects, not primarily another choice of HUD coordinate equation.

## Confirmed canonical-EXE facts

Canonical OR2006C2C.EXE:
- SHA-256 `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`
- PE32/x86, image base `0x00400000`

### Screen POSITION / rank HUD

`DispRank` is an explicit screen-space producer. The following callsites all call `put_clip_sprite` directly:

- `0xB9F3A`
- `0xB9F5E`
- `0xB9F81`
- `0xB9FD0`
- `0xB9FFC`
- `0xBA01E`
- `0xBA035`
- `0xBA052`

The calls use fixed screen coordinates and priority 2.0. Therefore `6th/6 POSITION` should not be fixed by guessing world depth. It needs exact SCREEN_HUD ownership carried from these producer calls into the render node / final draw.

Current generic semantic propagation is weaker than these exact callsites: `put_clip_sprite` builds a local SPRARGS and calls `put_sprite_ex` internally, and the global `put_sprite_ex` hook recovers semantics by `_ReturnAddress()` plus stack walking. At that point the immediate caller is the helper inside `put_clip_sprite`, not DispRank itself. A direct DispRank callsite wrapper can tag the exact newly-created SpriteNode without depending on optimized x86 stack recovery.

### Vehicle-attached rank markers

`Calc3D2D` at RVA `0x49940` is a real 3D-to-2D projection:
1. calls `mxCalcPoint`,
2. rejects near-zero depth,
3. divides transformed X/Y by -Z,
4. writes projected X/Y and preserves transformed Z.

`sub_4BAD20` calls `Calc3D2D` at `0xBAEE2`.
It then splits rendering by rank:
- 1st/2nd/3rd: `sprani_play_ae_auth_alpha` at `0xBB133`, `0xBB16C`, `0xBB1A5` plus special `0xBB0FB`.
- 4th+: digit construction through `put_clip_sprite` at `0xBB21F`, `0xBB241`, `0xBB271`, `0xBB2BC`, `0xBB2D0`.

This directly explains the different HMD behavior of 1-3 vs 4-6.

### BAD20 is not the whole producer set

Additional projected-marker families exist:

Calc3D2D callers:
- `0xBB3D6`
- `0xBB6F0`
- `0xBBB85`
- `0xBBDC5`

Related sprite producers include:
- `0xBB550`
- `0xBB796`
- `0xBBC5A`
- `0xBC2E5`
- `0xBC346`

Additional nearby generic number/sprite helpers also use:
- `put_clip_sprite` at `0xBAAA0`, `0xBABA4`
- `sprani_play_ae_auth_alpha` at `0xBAAEA`

R56 only probes the BAD20 subset, so an unchanged visible marker does not prove that the final renderer ignored the probe; a sibling producer may own it.

## Structural mismatch in the current VR classifier

The game converts a vehicle/world anchor to 2D with `Calc3D2D` and then queues an ordinary sprite.

Current R30 shader classification only accepts exact `WORLD_BILLBOARD` as a shader world-billboard when the base projection is `Perspective3D`. An exact rank marker that arrives through a final orthographic/2D sprite path can therefore be rejected even though its semantic owner is world-attached.

That matches the runtime evidence:
- rank semantic producers execute,
- queue semantics are registered/consumed,
- final `worldBillboard` counter can remain zero.

A vehicle marker therefore needs a dedicated concept such as `ProjectedWorldBillboard2D`: world-owned metadata with a 2D final draw, not generic WORLD_BILLBOARD and not SCREEN_HUD.

There is a second timing hazard on shader HUD: the game can upload/reuse c64 before the queue node semantic becomes current. The renderer stores both the uploaded WVP and the original raw game WVP, but the R44 raw-overlay lookup currently uses a 12-draw age window. Exact node provenance should be allowed to select the latest raw WVP for the same shader epoch without relying on that heuristic window; otherwise an already head-injected live c64 can be transformed again at R30.

## Metadata required for the real vehicle-rank fix

At each exact projected-rank `Calc3D2D` callsite capture:
- producer family / callsite ID,
- pre-projection input point,
- projected X/Y/Z,
- the two projection scale parameters passed to Calc3D2D,
- frame/queue generation.

When a related sprite is queued, attach to each SpriteNode:
- the captured projected-world anchor,
- glyph/sprite offset relative to that anchor,
- producer family,
- exact semantic = PROJECTED_WORLD_BILLBOARD_2D.

At render:
1. fail closed if the node metadata is absent or stale;
2. reconstruct or reuse the pre-projection 3D/view point;
3. project the anchor separately for left and right eyes;
4. add the original glyph offset after per-eye anchor projection;
5. use the same owner for 1-3 and every 4+ digit node.

This preserves the vehicle anchor instead of trying to manufacture stereo from the already-flattened final sprite coordinates.

## 6th/6 fix

Use direct wrappers at the eight DispRank `put_clip_sprite` callsites.

The wrapper should:
1. record the exact priority-list tail before the call,
2. call original `put_clip_sprite`,
3. identify the newly queued node,
4. attach exact `SCREEN_HUD/HUD_RANK` provenance before queue traversal,
5. log node pointer, kind, xstnum, position and priority,
6. allow R30 to consume this exact ownership at the earliest safe boundary.

Do not infer `6th/6` from generic white color, alpha, primitive count or shader shape.

## Revised HMD probe set

The next matrix should contain orthogonal probes rather than 20 visual variations:

| # | Probe | Question answered |
|---|---|---|
| 01 | Control only | protected world / current defect baseline |
| 02 | DispRank exact provenance logging | do all visible POSITION glyphs come from the 8 proven callsites? |
| 03 | DispRank exact-node suppress | does removing these nodes remove the visible 6th/6? |
| 04 | DispRank exact SCREEN_HUD | does direct node ownership fix convergence/head-follow? |
| 05 | DispRank exact finite HUD plane + scale | actual POSITION fix candidate |
| 06 | All projected-rank Calc3D2D capture only | which BAD20/sibling family is live in the tested race? |
| 07 | Suppress BAD20 family only | is current 1-6 display BAD20-owned? |
| 08 | Suppress sibling projected families only | does another producer own the visible marker? |
| 09 | Tag all projected families as PROJECTED_WORLD_2D, no movement | metadata/lifetime proof without visual formula change |
| 10 | BAD20 anchor per-eye reprojection | direct world-anchor fix for classic rank path |
| 11 | sibling anchor per-eye reprojection | same fix for alternate producer families |
| 12 | unified projected-rank reprojection | production candidate for all vehicle rank markers |
| 13 | unified reprojection, eye/IPD only | test whether Calc3D2D source already includes head-synced camera |
| 14 | unified reprojection, head inverse + eye/IPD | opposite head-space hypothesis |

Only 13 vs 14 intentionally form one A/B pair. The other probes attack different pipeline boundaries.

## Integration rule

R56 remains diagnostic evidence only. R57 is not merged into `vr-d3d9ex-focus` until:
- POSITION is proven to use exact DispRank nodes,
- all live vehicle rank producer families are identified,
- anchor metadata remains attached through queue selection,
- per-eye reprojection keeps the marker over the correct vehicle while the head moves,
- protected road/background/vehicle stereo and frame pacing do not regress.
