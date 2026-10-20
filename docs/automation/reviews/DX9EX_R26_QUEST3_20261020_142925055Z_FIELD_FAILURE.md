# Quest 3 R26+HUD field regression — 2026-10-20 23:29 KST

Status: **FAILED HMD ACCEPTANCE / SOURCE REVIEW / NO GAME SOURCE MUTATION**  
Lane: DX9Ex, baseline branch `vr-d3d9ex-focus`, source SHA `3b0204bc3b694231576cead79ed9fcd238a610ca`  
Session: `20261020T142925055Z-7e8d625e`, profile `CURRENT_FOCUS/CORRECTNESS`  
Input archive: `OutRun2_VR_ANALYZE_DX9EX-ACTIVE-20261020-3b0204bc3b69_CURRENT_FOCUS_CORRECTNESS_20261020T142925055Z-7e8d625e.zip` (supplied by user; not committed)  
Visuals: three user-supplied screen captures and first-person HMD assessment. Monitor mirror screenshots do **not** establish single-eye separation.

## User-observed failures (authoritative optical evidence)

1. OutRun extension-time digits still split between eyes / perceived head-lock.
2. End/result stage progress chart and figures still visibly split.
3. Car-attached ordinal/rival markers appear depthless / detached.
4. Central lens flare point duplicated and particularly distracting.
5. Main menu appears approximately 4:3 but too small; vehicle-selection geometry extends outside menu frame.
6. End/TRY AGAIN menu appears abnormally tall.

**Reject any claim that R26+HUD solved these visual symptoms merely because CI or draw HRESULT succeeds.**

## Build and runtime identity (verified in supplied package logs)

- `BUILD_INPUTS.json`: `ACTIVE_R26_R43_R44`, `R26_HUD_DEFAULT_CMAKE_OPTIONS`; `CURRENT_VR_SESSION.json`: `RendererCmakeFlags=-DOUTRUN_VR_SAFE_DRAW_COMPARE=OFF -DOUTRUN_VR_R26_HUD_COMPARE=ON -DOUTRUN_VR_C1_COMPARE=OFF -DOUTRUN_VR_C2_COMPARE=OFF`.
- `GAME_DLL_IDENTITY.txt`: selected and installed DLL SHA256 both `93e136ee75a7069bb5e4311a3bb4228bff4260036c4a8e1cf22da8bb38eb8b6c`; **loaded module hash NOT_ATTESTED**, so do not overclaim memory attestation.
- `EXE_IDENTITY.txt`: canonical replacement EXE SHA256 `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`.
- `DX9EX_LAUNCH_HEALTH.txt`: game exit 0; OpenXR host process observed; **HMD optical success not verified**.
- `AUTO_ANALYSIS_SUMMARY.txt`: D3D9EX_NATIVE, DirectGPU frames 31315, fallbacks 2, fence timeouts 0; estimate XR mean 11.065 ms, 90.4 Hz. There were frame spikes; this is not a 90fps guarantee.
- Game desktop resolution `3440x1440`; published per-eye XR texture `2496x2688`. Menu source UV, sampled aspect, capture clipping, and actual physical theater aspect were **not logged together**.
- `RUNTIME_VALIDATION=FAILED_USER_VISUAL` for the observed symptoms, not `PASSED`; any independent untested code changes remain `UNTESTED`.

## P0. Result progress — left/right Draw success does NOT prove optical convergence

`OutRun2006Tweaks.log` at ~23:38:02–03 includes bounded `VR R26 RESULT_HUD_EYES` records:
`route=FiniteHud api=DIP producer=OUTRUN_RESULT_PROGRESS queued=true viewport=0,0,2496,2688 fvf=0x142 VS=0 left=0x00000000 right=0x00000000 projectionRestored=true frameIncomplete=false`.

This proves selected source reached an indexed fixed-function stereo pair with successful HRESULT. It does **not** prove correct projection depth, in-eye pixel positions, composited head-space appearance, all result glyph producers, or lack of additional overlays. The same log has `VR P0 GOAL EARLY_GATE` state 20 with **multiple owners** (`OUTRUN_RESULT_PROGRESS`, `EXACT_SCREEN_HUD_CLIP`, `NONE/SCREEN_OVERLAY_2D`). `HUD_TRACE_SUMMARY.txt` identifies result/stage text at RVAs `0x97da7` and `0x97bb7`, which require distinct physical API evidence. Extra-time text is not proven resolved by one result-progress pair.

Next: exact producer fingerprint per glyph/number/progress fragment, capture output per eye + clip W + source pixel extent + original D3DX projection + R62 clipMap, and compare native/finite HUD/zero-disparity via opt-in optical route probe. Do not globally change HUD projection or report success from S_OK.

## P0. Rank and rival — projection path absent from this session, but class scope matters

`AUTO_ANALYSIS_SUMMARY.txt`: `RankProducerObserved=True`, `projectedMarkerSemanticCount=0`, `RankExactCalcObserved=False`. `OutRun2006Tweaks.log`: `VR R57 ORDINAL EDGE PROBE` was actually executed, `rawFinite=true`, `projectionValid=0`, `navipubDepth=1` (multiple samples, e.g. sourceZ -109.46208, screenZ -109.46208). The reporter field `RankExactCalcObserved` therefore needs review: edge telemetry exists but no valid projection event. `R64 D3DX ISOLATE RESTORED` says `markerValid=0`.

**Important:** `navipubDepth=1` is an exact ScreenHud callsite scope, and `src/hooks_uiscaling.cpp::Calc3D2D_dest` deliberately skips ordinal capture while that scope is active. The observed zero projected counts may include only NaviPub HUD draws, not necessarily the physical car-attached class. Do **not** change `RankMarkerSubScreenHudDepth == 0` globally or relabel NaviPub as world. Scope-sensitive telemetry for `RankMarkerSubSemanticDest`, `RankMarkerSub_dest`, `RankMarker_sprani`, `RankMarker_putClipSprite`, rival callsite and actual DIP/DPUP is required to distinguish failure from correct HUD suppression. Independently test car ordinal and rival.

## P0. Lens center — existing suppression has not removed the user's visible double point

Log startup: `LensFlareCentreEnabled: false`, `FixLensFlarePath: true`, `VRLensFlareProjected2D: apply successful`; hook install describes original `0xD3A5` parent and `0xC993` center draw; outer `0xCABE` untouched. `src/hooks_graphics.cpp::DrawObjectAlphaCentre` suppresses **only if** VR enabled, owner depth matches, not queue-active, object ID `0x570002`, and setting false.

Since the user still sees a double central dot, one of these is unresolved: (a) center scope predicate does not match runtime physical dot, (b) a separate CABE projected halo/object draws the point, (c) other duplicate effect. `VR P0 FLARE OBJECT` sampled object IDs 5701646/5701635–46 for CABE (decimal values), but the available logs do not contain per-eye GPU fingerprint of the actual disturbing spot. Do not simply turn off the whole sky/SkyGlow or remove CABE producers.

Next: add **non-invasive bounded counters** for C993 invoked/owner matched/suppressed/forwarded and for CABE object identities, with true draw fingerprints; opt-in hide-one-object A/B only after confirming the exact source. Preserve desktop and outer rings.

## P1. Menus — size/aspect/state handling not solved by R26 HUD

User sees title/main 4:3 but reduced; car-select car crosses menu, exit/TRY AGAIN vertically elongated. Host logs show `menu-local-fixed-projection-*` for pre/post-race and `projection-direct-r32-fast` for race. Actual `vrhost/src/runtime/menu_content_aspect.hpp` has state-dependent source crop/UV/aspect/optical contain rules including wide vehicle selectors 0x0A/0x0B/0x0C; a desktop 3440x1440 and XR eye 2496x2688 **must not be exchanged as identical source aspect**.

Next: exact game state, window client/source capture rectangle, sampled UV, menu crop plan, projected physical aspect, optical coverage and presentation path per title / main / select / exit, all in one matched log. Use an A/B configuration or isolated host patch; do not fix by globally coercing game render resolution to 4:3 or by independent X/Y scaling.

## P1. Performance, separately

98 active pacing windows; below-60 FPS frames 2439; below-50 frames 316; 164 source frames >25ms. CPU and non-CPU mixed spikes, max source frame 302.57ms; no fence timeout. Avoid attributing this to sand particles alone without correlated scene/draw timing.

## Acceptance and constraints

- Preserve known-good original user baseline `0cff83cf509c2acd6f3391b3a46c4dec1403a0d9` for comparison; never overwrite.
- Branch mainline: R26+HUD only. R84 is explicit diagnostic control, not fallback promotion.
- No speculative full-scene alpha, all-HUD, all-rank or aspect transforms. Use `docs/DX9EX_OPTICAL_ROUTE_PROBE_POLICY_20261020.md`.
- **This record changes documentation only; game/runtime source, settings, artifacts and automatic DX9Ex REVIEW_ONLY policy unchanged.**
- No score for duplicated task/status reporting (+0); no visual fixes are claimed.
