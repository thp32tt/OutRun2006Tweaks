# 2026-10-09 23:48 UTC / 23:58 KST onward — one-session Quest 3 / VDXR DX9Ex visual feedback

## Exact user-tested source and evidence

- Authenticated user-uploaded log session: `20261009T144836475Z-e86396b3`, backend `NATIVE_D3D9EX`, profile `CURRENT_FOCUS/CORRECTNESS`, game DLL identity matched, material `a6f8497c2fbe83959984275c30fbf43aa6a72d55`.
- Optical PASS (user directly confirmed): all 1st–5th rank numbers are single, **not head-following**; 6th/6 correct; menu `< >`, YES/NO correct; car-selection textures normal; both original GOAL stage/course label and time normal; OutRun rival marker follows the rival vehicle. Do not break/revert any of these by blanket semantic switches.
- Optical FAIL (user directly confirmed): the **1st–5th ordinal indicators do not remain above their respective opponents** despite mono/stereo convergence, resembling 2D projected placement. The rival marker *does* attach correctly. Only transient **+TIME** on OutRun stage extension appears twice and head-following; normal GOAL stage/time is not broken.
- Performance: user sees frame drops; internal game render source resolution currently tracks PC desktop `3440x1440` rather than a headset-specific eye extent. These are independent issues. **Do not increase all VR render resolution by default while GPU/frame budget is already failing**.
- User wanted one HMD session tonight. Do not request another repeat test against the same SHA or unproven candidate.

## Confirmed from the uploaded log (not optical inference)

- `AUTO_ANALYSIS_SUMMARY.txt` reported `status=OK`, `projectedMarkerSemanticCount=9197`, `approxAverageXrFrameMs=12.368`, `approxAverageXrHz=80.9`, `perfSpikeCount=0`.
- XR host reports `actualXrHz=90` and 11.111ms frame period. **80.9 observed average Hz vs 90 requested does not establish precise lost-frame fraction**; host telemetry samples/reuse policies differ.
- `OutRun2006Tweaks.log` contains **88** `VR R28 PERF: lower-Present` windows, **63** windows whose maximum exceeds the 90Hz 11.111ms period; highest per-window maximum **29.917ms** (23:49:38 KST), another **28.557ms** (23:55:38). These are diagnostic stalls, not guaranteed full GPU frame durations. Legacy analyzer only parsed absent `R32 FRAME SPIKE` rows and gave false `0`.
- The `VR R62 FIXEDFN KIND0` first rank clip reports `owner=SCREEN_HUD producer=RANK_MARKER_CLIP marker=0`; other many `DISPRANK_KIND0_CLIP` are intentionally ScreenHud. **Do not globally promote every SCREEN_HUD rank clip**: this destroys the verified 6th/6 normal HUD.
- Cumulative projected `semantic=9197,buildAttempts=9152,buildOk=9107,buildFail=45` is **rank+rival aggregate**, NOT proof ordinal 1–5 car attachment works. Source `Calc3D2D_dest` would log `VR R57 rank Calc3D2D: ordinal capture` once on exact callsite `0xBAEE7`; no matching line appears in this runtime log even though rank producers are present. Investigate original 0xBAEE7 callback vs `RankMarkerSub` before proposing an optical fix. Do not infer zero ranking drawing merely because the exact callback log is absent.
- `GameDefaultConfigOverride` initializes `Game::screen_resolution` from `SM_CXSCREEN/SM_CYSCREEN`. `skyGlow[..buffer=3440x1440]` confirms internal resource size matches the screen-sized default for this session. VR host carries `SharedState->recommendedWidth/Height[eye]` later, but those dimensions are not valid at the early game-config hook; do not pretend the manual option implements dynamic XR recommended-dimension synchronization.

## Implemented source improvements (runtime UNTESTED)

1. `tools/Analyze-OutRunVRSession.ps1` now summarizes R28 Present maxima and compares them to the reported XR refresh budget, with `D3D9EX_PRESENT_LATENCY_OVER_XR_BUDGET` warning; no more false all-green from zero R32 spike rows. Separate `HUD_RANK_CALC_CAPTURE_UNOBSERVED` flag when rank producer present and rival/ordinal aggregate projected >0 but exact ordinal producer log missing. Both have bounded independent fixtures in `Test-OutRunVRAnalysisContract.ps1`.
2. Opt-in `[VR] RenderWidth` / `RenderHeight` in `src/vr/settings.cpp` (both 0 = legacy desktop; both valid >=640x480 and <=16,777,216 pixels required) and `src/hooks_misc.cpp` allow independent *manual* game eye-source backbuffer sizes, while `src/hooks_graphics.cpp` auto-fits the PC mirror window to monitor if explicitly overridden. This is not automatic OpenXR recommended eye resolution and not enabled on the user-tested package. Do **not** raise render load by default.
3. Package rebuild, MSVC validation, and runtime user HMD testing must be reported separately; source presence is not an optical success.

## Remaining engineering work

1. Rank indicators: identify why `0xBAEE7` Calc3D2D exact ordinal producer log is missing while rank clip producers exist; separate ordinal/rival owner and verify *world car relative tracking* rather than just stereo fusion. Preserve existing R62 4th/5th owner and R64 6th/6.
2. OutRun transient `+TIME`: follow original stage/sumo glyph owner plus no-tick sprite replay and both fixedfn/shader routes; separately retain **both** GOAL/time original helpers and mono restart. Never globally force white/semitransparent glyphs or delete a second GOAL helper.
3. Performance: correlate scene-specific R28 Present spikes, frame pacing, draw/primitives/particle-like, and host submitted-versus-cached frames. Do not claim all 29.917ms was GPU render cost or optimize reflections/sky blindly.
4. Auto XR resolution: game initialization is earlier than XR host published recommended extents. A production solution requires negotiated XR extent at a safe device creation/reset boundary, resource lifetime handling, and GPU budget before enabling by default.
5. Existing known-good semantics: world/road/vehicle stereo, rival attachment, 6th/6, menus, car DDS, GOAL text/time, F11 previously accepted, recenter.

**RUNTIME_VALIDATION:** previous exact user package `a6f8497c...` partially PASS/FAIL as above; all new code `UNTESTED` on HMD pending a later intentional test. No repeated 1000/5000 static loops.
