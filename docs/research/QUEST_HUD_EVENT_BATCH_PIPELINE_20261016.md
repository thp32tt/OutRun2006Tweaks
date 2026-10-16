# Quest OutRun 2006 HUD 이벤트·문자·스프라이트·GPU 배치 경로 정밀 분석
2026-10-16 KST. Source: user-provided `outrun2.apk` ARM64 `liboutrun_quest_core.so`, SHA-256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`. N100 is used for **read-only** ELF disassembly. This document is a call-site analysis, **not** fully recovered C++ source or proof of Quest3 in-HMD layout.

## 1. Core finding: event-driven HUD, not one flat overlay

ELF AArch64 direct `BL` and PLT symbol resolutions establish that `outrun::runtime::attach_pc_scene` registers separate callbacks:
- `native_sprite2d_display` via 0x002d2a88 → PLT `0x01220d50`;
- `native_race_hud_display` via 0x002d2aa8 → PLT `0x01220d60`;
- `native_sprite2d_leaf` via 0x002d2f3c → PLT `0x01220db0`.

These are **separate callbacks**, not evidence that one function directly synchronously invokes the other in that sequence. The conceptual lifecycle is:

```text
PC game-race state/event callbacks (attach_pc_scene)
  ├── native_race_hud_display
  │     ├── sprani_draw_428a10 (6 distinct static BL callsites)
  │     ├── run_navi_draws (4 callsites)
  │     ├── queue_unmarked_glyphs (2 callsites)
  │     ├── native_sprite2d_glyph_records (2 callsites)
  │     └── original sprite, GOAL/end-of-race and rebuild/note
  ├── native_sprite2d_display
  │     ├── ensure_bank (5 callsites)
  │     ├── pc_image_42d300 / pc_image_42d280
  │     └── pc_sprite_pool_display_428170 (exact BL at 0x1040dc4)
  │           └── pc_sprani_render_429460 / matrix push/pop
  └── native_sprite2d_leaf
        ├── native_sprite2d_glyph_records (exact BL at 0x10419a4)
        └── pc_2d_flush_42d710 (exact BL at 0x1041a14)
              ├── quads / blend / state restoration / matrix conversion
              └── native D3D9-compatibility draw submission

native_sprite2d_glyph_records
  ├── if glyph list empty, fast return
  ├── native_sprite2d → ensure_bank(...)
  └── for each FrontendGlyph record (44-byte stride):
        copy record fields to a 72-byte image command buffer
        call pc_image_record_42cfe0(sprite-state, record, depth/order)
```

All named addresses refer to this **exact** AArch64 ELF image, not PC EXE/VR DLL addresses.

## 2. Glyph and HUD producer treatment: why this matters

- `native_race_hud_display` at **0x1044820**, 5,964 bytes; direct calls cover original sprite/animation, `native_race_end_gad_display`, `native_race_end_arcade_display`, `native_race_attack_display_4b0490`, `run_navi_draws`, `queue_unmarked_glyphs`, `native_sprite2d_glyph_records`, `note`, `rebuild` and `drain_sounds`. Distinct callbacks for different race modes and scene conditions are evident. The N100 Ghidra text for this function has incorrect EH/landing-pad overlap, so rely on exact disassembled calls rather than claiming clean C++ decompilation.
- `run_navi_draws` at **0x1045f6c** (~4,672 bytes) calls `native_sprite2d_glyph_records` at **four** static sites, also `frontend_text_glyph_42c720`, `frontend_text_advance_42c5a0`, `FrontendSprites::bank_scene`, `pc_image_group_42d5f0` and `pc_image_42d200`. Navigation can emit BOTH texture records and font glyphs.
- `queue_unmarked_glyphs` at **0x10471ac**, 1,088 bytes, uses a `vector<bool>` marking array in a path accepting `RaceHudDraw` and `FrontendGlyph` vectors. Then calls `native_sprite2d_glyph_records` at **0x10474c8**. Strongly supports tracking *which glyph records have been consumed*, with a residual/unmarked fallback, **not** deduplicating equal character codes (e.g. '11' must render two glyphs). Precise source-index mapping needs more dataflow recovery.
- `native_sprite2d_glyph_records` at **0x10408bc**, 272 bytes: `ensure_bank` before loop, loads `FrontendGlyph` entries at a fixed **44-byte stride**, copies fields to a local **72-byte** image structure, then calls `pc_image_record_42cfe0` for each entry (exact AArch64 loop branch at 0x104099c).
- `native_sprite2d_display` at **0x1040bdc**, 2,160 bytes, calls `ensure_bank` at **five static sites**; those are distinct code paths, **not proof of five texture bank loads each HUD frame**. It also calls `pc_sprite_pool_display_428170` and sprite-image recording.
- `pc_2d_flush_42d710` at **0x10357dc**, **24,796 bytes** / 6,199 decoded 4-byte instructions; has 136 direct BL sites and calls blend/quad/latch/reset/matrix helper routines. The **exact runtime integration edge** is `native_sprite2d_leaf` → `pc_2d_flush` at 0x1041a14. Existence of independent flush means HUD command capture and physical sprite submission are not the same lifetime. Direct GPU `glDraw*` is in the GLES-compatible device stage; full per-batch linkage to eye swapchain submission is not yet reconstructed.
- These are AArch64 **static** call counts. A function containing several BL sites does not mean every site executes each frame. This is not an FPS benchmark.
- The binary proves ordinary sprite/text staging and flush **inside the game renderer**. It does **not** prove a separate `XrCompositionLayerQuad`, fixed distance in metres, HUD curvature, no head-lock or different HMD UI coordinate policy. Do not claim these without `xrEndFrame` layer/pixel transforms and real headset captures.

## 3. Crosswalk to current PCVR R84 (as of observed branch)

| Quest producer/step | Current PCVR owner | Proven current behavior | Targeted validation |
|---|---|---|---|
| `RaceHudDraw` + `FrontendGlyph` | `src/vr/hud_semantics.hpp` and `src/vr/game/render_semantics.hpp` | Caller RVA → `ScreenHud` vs `WorldBillboard`; source tokens for GOAL, +TIME, ranks and car heart | Compare original six +TIME E8 identities and numeric/sprite paths |
| `native_sprite2d_glyph_records` + `ensure_bank` | Original game texture bank/D3DX Sprite and R84 HUD Inspector | Semantic provenance exists, but no proven matched Quest-style per-item glyph/image/texture-bank consumption | For white/blank glyphs, capture texture bank ID, texture existence, Reset generation, blend, alpha and GPU submission |
| `queue_unmarked_glyphs` | `SpriteNode` selection, direct numeric glyph and exact queue producer handling | Separate direct/queue token, no generic dedup of repeated characters | Preserve per-**draw entry** identity; don't skip identical visible chars/markers |
| `pc_2d_flush` | `src/hooks_uiscaling.cpp::VRProjectedD3DXSpriteIsolationR64` | **Already implemented**: exact `ID3DXSprite::Begin/Draw/Flush/End` interception, same-live-sprite identity, homogeneous `PendingScope/PendingProducer`, flush on exact transition / source exit / queue end, lost/reset invalidation | Compare `PendingDraws` lifecycle with actual DrawIndexedPrimitive, *don't add a duplicate generic Flush hook* |
| Quest GL compat draw | `stereo_renderer_r33.cpp` → `r30.cpp` → `r29.cpp` | R33 routes exact ScreenHud; R30 per-eye XYZRHW/raw VS matrix, R29 fail-closed fallback | Check raw VS c64 provenance, FVF 0x142, POSITIONT, same eye-pose epoch, draw HRESULT |
| Separate GOAL/callback | 0xBE020/0xBE150 helpers, B9200 text and `StageExtensionTime` | Some original B9200 text **explicitly excluded** from deferred D3DX promotion because ownership is not proven; not necessarily a defect | Recover its producer→deferred batch proof instead of enabling by guess |

### Critical correction to earlier findings

Our PCVR **already has** the `VRProjectedD3DXSpriteIsolationR64` hook class and `CanDrainDirectResultBeforeFirstQueueNode` / `CanRestoreDeferredResultOwner` safety contracts. Describing deferred D3DX provenance as entirely unimplemented would be incorrect. Whether these hooks see the **actual** problematic device/texture/draw calls on a failing PC/HMD session remains unproven. The right next change is an exact **producer → batch → GPU sink** trace and a bounded failing implementation repair, not an additional unrelated HUD framework.

## 4. +TIME, GOAL, duplicate / head-locked sprites — concrete decision tree

**+TIME original E8 sites (from canonical PC EXE):** sprite 0x9898E/0x98A36/0x98AC6 → 0x29530; numeric 0x989AD/0x98A89 → 0x973C0, 0x98A10 → 0x974E0. Current source has StageExtensionEnter/Leave and D3DX source/batch tracking.

1. At original E8 and `SpriteNode`: capture `source callsite`, `producer token`, `queue node ID`, `sprite instance`, `batch Begin generation`, `draw ordinal`, `texture bank identity`, `device Reset epoch`, `frame ID`.
2. At `ID3DXSprite::Draw/Flush/End` record the **same batch key**, ordered producer segments and whether `PendingHomogeneous` remains true. A flush done inside a later texture switch belongs to the **previous** producer.
3. At R33/R30 real D3D9 GPU primitive: record the same batch/sink where possible, FVF/declaration/VS shader/c64, original WVP, per-eye pose epoch, target/depth and HRESULT. If a batch key cannot be tied to the sink, mark evidence **UNKNOWN**, not SCREEN_HUD by guess.
4. If source=StageExtensionTime but GPU owner=None/foreign, the existing live isolation failed at one boundary. Repair only that boundary with exact proof, preserving mixed-batch End fallback and all texture order; avoid unconditional Flush.
5. If source survives but image is doubled/headlocked, inspect R30/R33 eye projection/WVP and whether the original mono draw is also submitted. If image is white, verify shader texture bank binding/Reset generation/alpha before changing screen projection. A white texture is not automatically a source-tagging bug.
6. Verify all three sprite and three numeric sources, end-race 0–99% and final records, normal timer, 6th/6, GOAL, rival marker and menus in the same exact SHA. No Android HMD performance assumption.

## 5. Implementation limits and status

- No Quest SDK GLES code, original sprite art, ELF object code or Ghidra output copied to Windows sources.
- The report is **evidence only**, not a claimed end-to-end HUD fix or Quest-native overlay duplication.
- No new gameplay source commit for this HUD investigation: no observed PC/HMD GPU sink evidence identifying a safe edit yet; existing R84 semantics/deferred batch owner must be respected.
- Exact SHA source/CI and real Quest 3/VDXR imagery are necessary before calling white glyphs, +TIME, result, lens flare or screen-space mapping fixed. `RUNTIME_VALIDATION=UNTESTED`.
