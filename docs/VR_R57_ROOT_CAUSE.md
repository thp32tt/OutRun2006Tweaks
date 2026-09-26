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

## Deeper R57 findings — 2026-09-26

### The 1st-3rd vs 4th+ HMD split is an original-engine renderer split

Static disassembly now proves two SpriteNode forms:

- `put_sprite_ex` at RVA `0x2CFE0` allocates `kind_C=0` and copies `SPRARGS`.
- `put_sprite_ex2` at RVA `0x2D0C0` allocates `kind_C=1` and copies `SPRARGS2`.
- rank 1st/2nd/3rd reaches `sprani` and then `put_sprite_ex2` / kind1.
- rank 4th+ digit construction reaches `put_clip_sprite` and then `put_sprite_ex` / kind0.

Despite this split, both paths converge before D3D9 presentation. The kind1 custom-matrix renderer and kind0 renderer both disable the vertex shader, select FVF `0x144 = XYZRHW | DIFFUSE | TEX1`, use 28-byte vertices, and issue `DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, ...)`.

Therefore production VR correction does not need two unrelated stereo renderers. Exact node metadata can be consumed once at the common R30 XYZRHW boundary.

### Exact cause of vehicle-marker head lock

All five currently identified rival-marker projections load the stock camera matrix `EvWorkCamera::d3dmatrix140` immediately before `Calc3D2D`:

- `0xBAEE2`
- `0xBB3D6`
- `0xBB6F0`
- `0xBBB85`
- `0xBBDC5`

The active VR `ApplyCullingCameraSync()` intentionally updates only `cam_pos_F8` and `look_pos_104`; it does not rebuild `d3dmatrix140`. World geometry later receives `LatchedHeadInverse` at the renderer/c64 boundary, but the rival marker has already been flattened to a 2D sprite using the stock camera matrix.

This is a direct structural explanation for the user-observed result: a marker can become binocularly single yet still follow the headset rather than remain over the car.

### Existing Calc3D2D hook is the safest anchor capture point

The original UIScaling implementation already owns one stable inline hook for `Calc3D2D`. No new queue-entry hook and no vehicle-structure hook is required.

At the five exact rank return RVAs, capture before/after the original call:

- input `*in`: the caller has already transformed the local marker offset by the vehicle matrix; this is the world-space marker anchor,
- raw `out.x/out.y/out.z`,
- `a1/a2`,
- producer callsite / generation.

The canonical formula is:

`out.x = a1 * view.x / -view.z`
`out.y = a2 * view.y / -view.z`
`out.z = view.z`

so the exact stock-view anchor can also be reconstructed without dereferencing the vehicle again:

`view.x = out.x * (-out.z) / a1`
`view.y = out.y * (-out.z) / a2`
`view.z = out.z`

Capture both world and view anchors for diagnostics; the view anchor is sufficient for the first implementation.

### Preferred rendering shortcut: move the game's finished quad, do not rebuild it

The game already owns texture choice, animation, ordinal/digit composition, scale and distance-dependent alpha. Preserve all of that.

For each exact projected-rank SpriteNode attach the captured stock-view anchor. At R30:

1. project the stored anchor through the stock/base projection to obtain the source anchor ray,
2. project the same anchor through `LatchedHeadInverse * relativeEyeInverse * eyeProjection` for each eye,
3. convert the difference to viewport pixels,
4. add the same per-eye delta X/Y to every XYZRHW vertex generated by that node.

This keeps the final quad camera-facing, preserves the original game's sprite size/layout and makes every digit belonging to the same vehicle move with one common world anchor.

A second candidate may reuse R30's existing full XYZRHW reprojection by overriding the missing depth from the exact anchor. That is useful as a falsification path, but rigidly reprojecting all four corners can rotate/skew a billboard under head rotation. The anchor-delta method better matches the original camera-facing marker semantics.

### Why the current generic R30 world reprojection cannot solve rank by itself

The existing R30 full reprojection recovers view Z primarily from `RHW = 1/clipW`. Rank sprite renderers emit ordinary screen-space XYZRHW data rather than the vehicle's true perspective depth. As a result the final D3D draw no longer contains the information required to reconstruct the vehicle anchor correctly.

This is why exact `WORLD_BILLBOARD` scope alone was insufficient. Semantic ownership says what the draw is, but the original 3D depth/anchor has already been discarded.

### Producer-to-node propagation should use the common node creation hooks

R56 often snapshots a queue tail before a producer and tags a tail afterward. Deeper sprani disassembly shows an internal `SPRARGS2` staging/deferred buffer at `0x986B34` controlled by `0x986B28/0x986B30`. This makes "one producer call == one immediate tail" an unsafe long-term assumption.

The code already hooks both common node creation paths:

- `put_sprite_ex_dest` for kind0,
- `put_sprite_ex2_dest` for kind1.

Use an exact producer context/epoch around the known rival-marker calls, then let these common hooks attach scope + anchor metadata to every node actually created. This naturally covers multi-node sprani output and digit nodes without guessing the final tail.

If the deferred staging ever crosses the producer scope boundary, preserve the producer epoch alongside the staged SPRARGS2 record or use the bounded node walk as a fail-safe. Runtime counters must prove registered/consumed metadata counts before integration.

### Do not globally replace the camera matrix stack

Full-EXE xrefs show:

- `mxLoadCurrentMatrix(0xA170)`: 73 direct call sites,
- `mxPushLoadMatrix(0x9F90)`: 124,
- `mxCalcPoint(0xA7D0)`: 137.

Changing the shared matrix stack or `d3dmatrix140` globally can affect many unrelated effects and objects. The five exact rank `Calc3D2D` sites provide the same information with a much smaller regression surface.

### Screen POSITION / 6th/6 is simpler than vehicle rank

The eight DispRank calls are all direct `put_clip_sprite` producers, therefore kind0/fixed-function XYZRHW. Treat the complete DispRank node group as exact `SCREEN_HUD` at node creation. Do not apply vehicle depth or WORLD_BILLBOARD handling.

This also means c64 timing is not the primary explanation for the visible `6th/6` sprite group itself. c64 provenance still matters for other shader-backed white text, but the DispRank group should first be fixed through exact kind0 node ownership and the finite HUD plane.

### High-information next HMD matrix

Replace redundant visual-coordinate variants with these orthogonal probes:

| Probe | Purpose |
|---|---|
| CONTROL | protected R51/R55 world baseline |
| POSITION_NODE_SUPPRESS | prove the visible 6th/6 group is exactly the eight DispRank nodes |
| POSITION_EXACT_HUD | direct kind0 ScreenHud ownership |
| POSITION_HUD_PLANE | production-style finite HUD plane + normal scale |
| RANK_CAPTURE_ONLY | log the five Calc3D2D anchors and node propagation, no visual change |
| RANK_HEAD_ANCHOR | common-head correction only; proves the head-lock cause |
| RANK_EYE_DELTA_BAD20 | anchor-delta stereo for BAD20 family only |
| RANK_EYE_DELTA_SIBLINGS | anchor-delta stereo for sibling families only |
| RANK_EYE_DELTA_ALL | unified candidate for 1st-6th+ |
| RANK_DEPTH_REPROJECT | alternate exact-depth full-reprojection falsification |
| RANK_KIND0_TO_KIND1 | diagnostic only: force 4th+ into kind1-style path to confirm renderer-path parity; never production policy |
| ALL_EXACT | POSITION exact HUD + unified vehicle rank anchor candidate |

Only candidates that answer a different ownership/geometry question remain.

## Integration rule

R56 remains diagnostic evidence only. R57 is not merged into `vr-d3d9ex-focus` until:
- POSITION is proven to use exact DispRank nodes,
- all live vehicle rank producer families are identified,
- anchor metadata remains attached through queue selection,
- per-eye reprojection keeps the marker over the correct vehicle while the head moves,
- protected road/background/vehicle stereo and frame pacing do not regress.


## Deeper R57 finding: depth survives Calc3D2D but is discarded by SpriteNode draw data

The canonical EXE constants prove `0x0062806C = 1.0f`, `0x006281C8 = 320.0f`, `0x006281CC = 240.0f`, and the BAD20 glyph vertical offset is `32.0f`.

Calc3D2D therefore has the exact form:

```
view = mxCalcPoint(currentMatrix, input)
out.x = a1 * view.x / (-view.z)
out.y = a2 * view.y / (-view.z)
out.z = view.z
```

and can be inverted without the original vehicle point:

```
view.x = out.x * (-out.z) / a1
view.y = out.y * (-out.z) / a2
view.z = out.z
```

This is the strongest shortcut found so far. The original rank-marker code keeps the true camera/current-matrix depth in `out.z` long enough to perform visibility/size/alpha decisions, then loses that depth when it creates a 2D sprite.

For BAD20 specifically, the already-installed safe hook at RVA `0xBB046` reads the unrounded projected X/Y from stack offsets `+0x40/+0x44`; the adjacent `+0x48` value is the preserved Calc3D2D Z for that same projected vector. This means a BAD20 proof candidate can capture real marker depth without adding another risky mid-hook.

### Why exact WORLD_BILLBOARD tags still fail

The queue has two concrete sprite representations:
- 1st-3rd use `sprani_play_ae_auth_alpha -> put_sprite_ex2`, yielding `SpriteNode.kind_C = 1` / `SPRARGS2`.
- 4th+ use `put_clip_sprite -> put_sprite_ex`, yielding `SpriteNode.kind_C = 0` / `SPRARGS`.

The custom-matrix renderer for `SPRARGS2` expands the quad and explicitly writes RHW = `1.0f` for every vertex before `DrawPrimitiveUP`. The plain `SPRARGS` representation also has no vehicle/view-depth field. Both paths therefore reach R30 after the real Calc3D2D depth has been discarded.

R30's existing full XYZRHW world reprojection expects RHW/clip-W or screen-Z to carry depth. That assumption is valid for projected particles/decals but is false for rival-marker sprites. Consequently an exact WORLD_BILLBOARD tag can still reconstruct the marker at an artificial near/flat depth.

### Lower-risk fix: depth-aware anchor translation

Do not replace the game's sprite renderer and do not rebuild every rank glyph in 3D.

Store a small projected-anchor record next to the existing per-SpriteNode semantic tag:
- Calc3D2D caller/family,
- `out.x/out.y/out.z`,
- `a1/a2`,
- original screen anchor after the game's 320/240/32 offsets,
- node/glyph offset from that anchor,
- generation/serial.

At R30 stereo replay:
1. reconstruct the center/game-view anchor from `out.x/out.y/out.z/a1/a2`;
2. apply the existing R30 relative-eye transform and eye projection (no second common head rotation);
3. compute left/right projected anchor positions;
4. translate the already-generated sprite quad by `eyeAnchor - originalAnchor`;
5. leave texture, animation, scale, alpha, color, rank digits and layout unchanged.

This one transform can handle both `SPRARGS2` 1st-3rd and `SPRARGS` 4th+ because both ultimately reach D3D9 `DrawPrimitiveUP`.

The existing `SpriteNodeSemanticTag` side table already has the correct lifetime/concurrency model and capacity equal to the 0x230-node sprite pool, so projected-anchor metadata can use a parallel bounded table rather than introducing a new allocation-heavy map.

### Alternative central capture point under investigation

`dispMarkerCheck(0xBA0E0)` takes the candidate object pointer and directly reads a 3D vector at `object+0x14` while comparing it with the player-side world position. If global xrefs prove all relevant rival-rank families pass through it, this may provide an even simpler common vehicle identity/world-anchor source. It is not yet assumed to cover every visible rank producer.
