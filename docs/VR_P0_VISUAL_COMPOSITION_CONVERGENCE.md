# DX9Ex P0 Visual Composition Convergence

Status: ACTIVE / NO HMD CANDIDATE

## Trigger
DX9Ex 00519 (9a3e08cc62b6a36a8196936eacead8cc08fcc756) is USER_RUNTIME_FAIL: menu/car-selection textures missing; HUD/rank/rival/+TIME/menu arrows/YES-NO/lens flare doubled or head-following; performance not accepted.

## Evidence order
1. Original emoose/OutRun2006Tweaks hooks_uiscaling/hooks_graphics/interpolation/game_addrs.
2. Fork R65-R74/R73-era HMD history and regression ledgers.
3. Canonical OR2006C2C.EXE identity + disassembly/XREF/byte contracts.
4. Current producer -> SpriteNode -> replay -> queue -> fixed-function/VS draw ownership.
5. Deterministic static verifier.
6. Quest 3/VDXR only after 1-5 are green.

## Closure matrix
- Menu/car-selection textures: MANAGED LockRect must remain compatible; translated DYNAMIC textures must not waste bounded CPU-shadow memory.
- Screen HUD: exact ownership for rank/position, gear/rev, time/goal/results/+TIME/checkpoint, hearts/rival/ghost/C2C, menu arrows, YES/NO, 6th/6 and glyph paths.
- Vehicle markers: rank 1st-3rd, 4th+ clip digits and rival marker preserve Calc3D2D payload; fixed-function XYZRHW and shader/c64 paths both support ProjectedWorldMarker2D.
- Lens flare/SceneEffect: reconcile original camera/z-near/interpolation path with current R29/R30 ownership; no broad alpha heuristic.
- F11 overlay stays external and cannot consume game semantic tokens.
- World stereo remains protected; no blanket queue-to-ScreenHud.
- Launcher proves canonical EXE semantic identity before launch and packages analyze_outrun_assets.py.

## Exit gate
tools/verify_vr_visual_composition_p0.py plus canonical binary/HUD cadence/producer provenance/cross-thread registry/projected marker/Sumo replay/recenter/reset-transport/Domain Isolation gates must all be green before another HMD candidate is requested.

## Cross-domain source review (2026-10-08, AI 2)
- Before attempting another HUD-only correction, read [the 150-file game/host source screen and targeted ownership/error-path review](automation/reviews/AI2_QUEST3_CROSS_DOMAIN_SOURCE_REVIEW_20261008.md). It distinguishes the **packaged R26+HUD/R23 owner** from CI-only R33, exact HUD c64 upload-vs-node-draw timing, generic-overlay live-c64 use, R30 lazy VB/IB shadow fallback, off-path world semantic tokens, F11 presentation-state predicate divergence, and UI DDS replacement vs original fallback / R15/legacy-XMT resource failures.
- New assertions should be **one targeted negative contract per proven defect**, never unchanged-source 1000/5000 repetitions. A static pass is never Quest 3 visual proof; `RUNTIME_VALIDATION=UNTESTED` until the exact candidate is headset-tested.
