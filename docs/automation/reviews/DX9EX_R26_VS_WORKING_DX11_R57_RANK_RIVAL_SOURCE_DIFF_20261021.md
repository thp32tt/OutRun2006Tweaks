# 2026-10-21 — Working DX11 test build vs DX9Ex R26: rank & rival marker source comparison

**User headset verdict:** current DX11 test build shows both vehicle rank and rival markers correct. Treat as physical optical evidence for their tested ZIP, **not** automatic validation of every source on latest branch head. Comparison read at 2026-10-21 07:47 KST.

**Read-only compared heads**
- DX11 `vr-dx11-native-r71`: `e3f8acd154c49e3455a1f427dbfa32614fd6f9ed` (C6 record, native full-game runtime `UNTESTED`)
- DX9Ex `vr-d3d9ex-focus`: `de9d1c71a619232dec1b2190b214760b74198b4f` (R26+HUD configured default; later review-only documents may advance HEAD)

## Critical identity warning: "DX11 build" != proven native DX11 raster

DX11 branch `src/vr/d3d11/live_game_frame_bridge.cpp::env_opt_in()` requires literal `OUTRUN_DX11_FIRST_GAME_FRAME=1`; full native frame additionally requires `OUTRUN_DX11_FULL_GAME_FRAME=1`. Without these, fallback remains the D3D9Ex game path. `AGENTS.md` on the DX11 branch records 2026-10-18 live evidence `native_draws=0`; `docs/automation/runs/CONVERSION-DX11-00959.json` marks native full-frame, game and HMD validation `UNTESTED`, despite 5/5 exact-SHA CI success. Thus the optical-accepted build plausibly exercises **DX11 branch's legacy R57/R62 D3D9 VR code** rather than the unfinished native D3D11 raster. Determine tested ZIP source, live loaded x86 DLL hash, effective `OUTRUN_DX11_* ` flags, and native drawn/published counters before attributing correctness to native backend.

## Direct source deltas

| Boundary | DX11 branch — working-user build lineage | DX9Ex R26 — affected | Why it matters |
|---|---|---|---|
| Original vehicle `Calc3D2D` | `src/hooks_uiscaling.cpp:317+`: call original; on `_ReturnAddress()==0xBAEE7` recover `viewZ=out.z, viewX=out.x*(-out.z)/a1, viewY=out.y*(-out.z)/a2` | `src/hooks_uiscaling.cpp:898+`: raw input round-trip, `RankMarkerSubActiveDepth`, `RankMarkerExactCalcEdge`, `RankMarkerSubScreenHudDepth`, strict source provenance | An extra false gate drops all car anchors; field SHA `3f9ccd3` reported `projectionValid=0` while original sourceZ looked like moving vehicles. |
| 1–3 direct marker sprites | DX11 `VRR57Mode()` defaults **6**; `ScopedProducerSemantic(ProjectedWorldMarker2D, &RankMarkerProjectedInfo)` spans actual `sprani` call | DX9Ex `ScopedExactProducerSemantic`, projected only after validated anchor; multiple root/tail/generation and NaviPub rules | DX11 attaches semantic in physical creation; DX9Ex may fail before owner or lose it before GPU Draw. |
| 4–6 clip rank sprites | DX11 `ScopedProducerSemantic` during original `put_clip_sprite`, then `RegisterSpriteNodeScope(node,r57Scope,r57Marker)` on actual last new node | DX9Ex replaces with multi-node exact-queue tagging, root/reuse checks, `RankMarkerSubScreenHudDepth` branch | May misclassify as ScreenHud or lose anchor in deferred queue. Do not revert all-sibling guard without proof. |
| Desktop marker vertical offset | DX11 uses original `y+RankMarkerFracY` and `y` for 4+ clip | DX9Ex introduced `VehicleAnchorDesktopLiftPixels(...)=+32` on valid projected car marker in `b0d6f977` (2026-10-19) | When projected class works, marker Y is intentionally changed. It is an independent potential *visual attachment offset* even if stereo projection is correct. Does not affect rival. |
| Rival | DX11 `src/hooks_uiscaling.cpp` has **no** `RivalMarker_sprani`, no `RivalMarkerProjectedInfo`, no `0xBB6F0` E8 hook | DX9Ex adds consumed rival payload + `RivalMarker_sprani` at `0xBB796`, and an additional exact `0xBB6F0` call wrapper in `0d254808` | A working DX11 rival **does not use** DX9Ex's extra rival-hook machinery. Preserving/restoring original rival route is higher-priority A/B than changing eye pose globally. |
| R57 stereo math | DX11 `stereo_renderer_r30_r26_safe.cpp:1560+`: mode6 uses `HeadInverse * eyeInverse(relative IPD, identity q) * eye FOV`; optional explicit marker branch is different | DX9Ex `...r26_safe.cpp:1570+`: always applies HeadInverse; default `RankDx11ReferenceEyePose=true` selects identity eye q but another mode remains | With correct anchor, default angular math is substantially similar. Changing eye cant alone cannot repair missing source. |
| Clip-W validity | DX11 `R57ProjectViewPoint` uses `fabs(clipW)>1e-6`; DX9Ex requires `clipW>1e-6` | Conservative DX9 gate could reject a sample that DX11 permits; **not proof positive-W points are failing** | Diagnose actual per-eye clipW first; do not globally admit behind-eye markers. |
| Fixedfn R62 | Both branches have `R62TryFixedFunctionSpriteIndexed` for FVF0x142 NULL VS, indexed triangles | DX9Ex adds extra gates and result-HUD logic, but function exists and dispatches after F11 | Historic R84 loss was already fixed; do not claim present function is missing. |
| R64 Draw→Flush split | Present in DX9Ex `VRProjectedD3DXSpriteIsolationR64`, restored in `87a275de` | DX11 legacy producer path differs and does not prove R64 split's physical activation in DX9Ex | Check Draw+Flush telemetry and queue owner for each exact car producer. |
| HUD 0.55 | Both branches source and packaged INI use `HudScale=0.55` | DX9Ex also has `Hud1080pReference=true` 1080p contain-fit (effective 0.409 at 3440x1440 for screen HUD) | Do not conflate 0.55 setting with identical final UI raster size. Rank marker depth is separate from generic HUD scale. |

## Strongest failure candidates to verify

1. **HIGH: rank source admissibility/owner mismatch.** Compare DX11's `RankMarkerProjectedInfo.valid` under exact 0xBAEE7 with DX9 `RankMarkerSubScreenHudDepth`, `RankMarkerExactCalcEdge`, `projectedAnchor.valid` under matching car-distance/yaw. Preserve actual 2D NaviPub exceptions; an exact inner `0xBAEE2` alone does not distinguish NaviPub's four legitimate parents because they reuse `sub_4BAD20`.
2. **HIGH: rival path over-customization.** Compare native direct screen output from unchanged DX11 rival vs DX9 `0xBB796` after the extra `0xBB6F0` capture. No claim that deleting a hook automatically fixes it; need a reversible A/B on SAME DX9 compiled code/path.
3. **MEDIUM: extra 32 original-pixel lift**, only for valid rank 3D owner. Can cause residual car detachment when 3D marker depth is already fixed. Do NOT globally shift all HUD.
4. **MEDIUM: clipW sign and D3DXSprite queue batching**, check actual accepted per-eye draw and projection restore. Existing R62/R64 presence is code-only.

## Controlled next step

Obtain/verify actual user-good DX11 tested package `SOURCE_SHA.txt`, `GAME_DLL_IDENTITY.txt` if available, logs plus DX11 opt-in env and `native_draws/native_published_frames`. This determines if original D3D9Ex R57 mode6 is the *physical* gold reference. For an explicitly authorized patch, isolate DX9 rank/rival only behind reversible A/B flags: (A) direct original DX11-style rank producer ownership with exact NaviPub protections; (B) bypass added rival E8+sprani custom owner while preserving original coordinates; (C) optional +32 lift disabled. Fix only the gate that matching runtime/source evidence shows fails. Preserve default R26+HUD, good menu/selector, F11, +TIME isolation, HUD setting 0.55, input/FFB and world/sky. Follow with exact-SHA Win32 CI then one Quest3 optical run. No game/runtime code was changed during this source comparison.

**Validation:** STATIC_SOURCE_DIFF_COMPLETE; user-reported DX11 HMD PASS without test asset SHA; DX9 runtime effects of proposed changes UNTESTED. No score for docs review.
