# AI 2 — Quest 3 DX9Ex rank/rival and shared HUD original-address reconciliation (2026-10-08)

## User issue and source of authority

Prior review deferred car-attached rank/rival marker anchoring despite the user stating these worked before. This report compares the **pinned original emoose/OutRun2006Tweaks UIScaling producer** (including `50d94534ec2b` on the fork's pre-VR ancestry), the present `vr-d3d9ex-focus` hooks and the canonical `OR2006C2C.EXE` direct-CALL manifest. No speculation about absent EXE locations; `tools/verify_vr_hud_exact_callsite_contract.py --self-test` enforces the **71 exact disjoint x86 CALL producers, original destinations, source addresses and installed wrappers**.

**Code-bearing final candidate SHA:** `79a0dcb7495d7a8af9eb0d410d716bf72f024444`. Previous independent F11/memory/world-readiness material was `f2e290417fe9e4f6f822f0009feca7410103adf7` (all 4 exact-SHA CI SUCCESS). Historical HMD failure 00519 `9a3e08cc62b6a36a8196936eacead8cc08fcc756` is still OPEN.

## Original vs regressed fork architecture

| Original/canonical x86 evidence | Original intent / persistent behavior | Fork gap proven from source | Fix in current source |
| --- | --- | --- | --- |
| `sub_4BAD20` entry `0xBAD20`, `Calc3D2D` at `0x49940`, rank producer's Calc return `0xBAEE7` | Per-call car projection precedes digit/animated rank sprite production. Old emoose code restores subpixel fractions discarded by `cvttss2si` | Fork held the **last valid `RankMarkerProjectedInfo` as a thread-local sticky variable**; later sprite producers could reuse a preceding car's point, or NaviPub same-function screen-HUD calls could poison the car anchor | Hook only exact function entry `RankMarkerSub_hk` → `RankMarkerSub_dest`, zero rank projected payload and rank float fractions *for this invocation*, then restore parent values at exit. `Calc3D2D_dest` populates world-car anchor only within active `sub_4BAD20` and outside NaviPub `ScreenHud` scope. Both original subpixel semantics and nested subcalls preserved |
| `RankMarker_Truncate = 0xBB046`; rank sprani `0xBB0FB/0xBB133/0xBB16C/0xBB1A5` | 1st–3rd ranks use `sprani_play_ae_auth_alpha`, one producer can create animated/masked sibling sprites | Earlier separate fix already expanded rank sprani tagging to **all** new nodes; do not roll it back | Preserve exactly existing `TagAppendedNodes` and new per-car projected payload scope |
| Rank clip digits `0xBB21F/0xBB241/0xBB271/0xBB2BC/0xBB2D0` | 4th+ ranking letters/digits use `put_clip_sprite`, restore `RankMarkerFracX/Y` in sprite position | Old fork registered only **priority tail** for projected/world/screen semantics and updated that one SPRARGS node. If the call creates multiple nodes, earlier siblings fall back to generic ScreenOverlay and can be binocularly displaced | Snapshot tails for all **21 priority roots** before the original producer; retain bounded traversal to `SpriteNodeMax=0x230`; apply original fractional fix to every new `kind_C==0` / `SPRARGS` node (never corrupt `kind_C==1` /`SPRARGS2`); `TagAppendedNodes` attaches the **same world projected anchor and producer** to *all* new children |
| NaviPub → rank sub `0xBEB98/0xBED83/0xBED9E/0xBEDAE` | These calls reuse rank drawing for **screen HUD**, not world rank marks | Subroutine's prior `Calc3D2D` sample was previously allowed to overwrite world projected cache even during screen-HUD provenance | Guard Calc capture with `RankMarkerSubScreenHudDepth==0`; ScreenHud ownership still wins for the entire rank subroutine and all exact callsite children |
| Rival Calc return `0xBB6F5`, rival animation call `0xBB796` | Vehicle-relative rival projected point must be attached to **this car's** draw | Fork kept last rival point set beyond producer lifetime; each new sprani could inherit prior payload if Calc had not produced its own point | Move captured rival anchor to local `projectedAnchor`, immediately clear `RivalMarkerProjectedInfo`, tag all appended nodes with one copied payload, preserve strict WorldBillboard fallback when missing |
| Menu arrows `0xE358B~0xED7A3`, result `0x97BB7/0x97DA7`, relevant TimeAttack/ghost/rank/REV clip addresses in manifest | Exact 2D calls should map to `ScreenHud`, preserving left/right original spacing | Generic `ExactScreenHud_putClipSprite` tagged only **last** new node; animated/masked sibling could render as head-following generic ScreenOverlay2D | Change exact ScreenHud clip producer to priority-tail snapshot + all-child tagging through common `TagAppendedNodes`; **do not change any EXE CALL destination or left/right spacing** |

The existing `render_semantics.hpp` synchronized SpriteNode tag registry, `hooks_framerate.cpp::SumoUISpriteReplay` no-tick replay of projected payload, and active R30 fixed-function `R57BuildProjectedMarkerDelta` per-eye reprojection are preserved. New per-producer expiration occurs **after** nodes have copied the projected point, so 1st–3rd/4th+ siblings and no-tick replay keep the right car point without keeping a global last-car cache.

The world/ScreenHud split is explicit. World car markers retain original positional data plus R30 per-eye world projected correction; **generic text/menus are not promoted into car-attached world geometry**. The original upstream game function destinations and all 71 canonical CALL bytes are unmodified.

## Targeted deterministic regression tests

- `tools/verify_vr_hud_exact_callsite_contract.py --self-test`: all 71 original CALL signatures plus exactly 10 diverse existing fault injections, updated for full sibling tagging, exact NaviPub/Rank marker owner and rival one-shot sample. Retains original source hook targets.
- `tools/verify_vr_projected_marker_anchor.py`: rank function lifetime, exact projected Calc capture gate, rival consume-once, all 4th+ rank siblings, all menu/result siblings, and no-tick replay behavior.
- `tools/verify_vr_visual_composition_p0.py`: original EXE contract, scene/DDS and viewport + F11 safeguards, **four new distinct single-fault mutations** targeting rank stale sample, 4th+ sibling, menu child, rival stale sample; no 1000/5000 passes.
- `tools/verify_vr_hud_cadence_restore.py`: updated from old tail-only assumptions to the actual all-sibling source order while preserving 0xBB796, bounded scoping and exact screen HUD semantics.
- Active DX9Ex CI, EXE HUD Inspector Win32 build, Domain Isolation, Full Source Impact MSVC host/game analysis run on the **same material SHA** before any Quest 3 candidate is considered.

## What static proof cannot establish

- **Quest 3/VDXR runtime=UNTESTED.** The formerly working original mod ran a flat D3D9 game and is structural evidence for original call destinations/positioning, not evidence that a new stereo build visually converges. Prior 00519 HMD FAILURE remains valid until a **single** exact-build targeted session.
- Exact callsites prove **who owns a queued sprite**, not that `Calc3D2D` reconstructed view-space math is numerically perfect at every depth. Preserve source producer values and include rank 1–3, 4–5 plus rival in one user session.
- The new all-child tagging closes a **conditional** sibling ownership gap. It does **not** claim that the original EXE always emits multiple children for every clip CALL.
- Related P0 visual open items (lens flare, +TIME/goal record, c64-before-node WVP ownership, runtime shadows, HMD recenter, frame pacing) need separate exact-owner evidence. The earlier independent F11 fixed-XYZ owner and DDS fallback remain in the active candidate and are **not** counted again as this fix.

## Outcome

- Material source changed: `src/hooks_uiscaling.cpp`, strict producer and P0 regression scripts. No changes to EXE binary or canonical RVA manifest.
- Validation source SHA `79a0dcb7495d7a8af9eb0d410d716bf72f024444`.
- **CI status, same exact SHA:** DX9Ex Active Validation `37741691863` **SUCCESS** (policy, Win32 game, x64 OpenXR host, R33 full-chain, package); EXE HUD Inspector `37741691867` **SUCCESS** (canonical EXE contracts + new P0 fault injections + game Win32 Inspector build); Domain Isolation Guard `37741692068` **SUCCESS**. DX9Ex Full Source Impact Review `37741692064` currently source inventory/host MSVC analyzer SUCCESS with game /analyze still in progress; do not infer its final result until finished.
- **Packaged GitHub Actions artifact:** ID `11533599078`, `OutRun2-VR-DX9EX-ACTIVE-79a0dcb7495d7a8af9eb0d410d716bf72f024444`, digest `sha256:c7909cb0511373bc27bb56bc679069ba0326d83257f8d1d48b3b61f512797ef7`; size 2,749,477 bytes. No hardware execution occurred.
- **Quest 3 headset:** `RUNTIME_VALIDATION=UNTESTED`.
