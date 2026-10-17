# Quest 3 / VDXR 2026-10-17 — R84 optical field regression and category-specific restore

## Exact user-tested input (NOT an automatic HMD PASS)
- Source SHA: `b476be3929e4a62f0462df70a1a79684f8fa305c`; all five uploaded DX9Ex sessions use R84 `dinput8.dll` installed SHA256 `cb0c906349d195e1aec95284902162485c35bcd6011eaff8db693b52af33e3ef`, provider `NATIVE_D3D9EX`.
- Logs: CURRENT_FOCUS/CORRECTNESS (13:27:17Z), R84_TEST/CORRECTNESS (13:30:23Z), B_HUD/HUD_SCREEN (13:32:36Z), D_PERF/PERFORMANCE (13:34:18Z), G_COCKPIT/COCKPIT_PARTICLES (13:23:47Z), all 2026-10-17 UTC.
- User optical report: MAIN R84/R29-R33 main menu appears approximately correct geometry except ~75% size. Other labels yield squashed centered wide menu with side margins despite shared DLL. Gameplay scene corrupted in all five. 4th/5th above-car ranks, `6th/6`, F11 and final results/time appear **left-eye only** and head-following. ESC appears in both eyes but shifts like wrongly classified 3D. Sky duplicates/head-follows. Cockpit repeatedly alternates apparent third-person/first-person zoom.
- `AUTO_ANALYSIS_SUMMARY.json` / `DX9EX_LAUNCH_HEALTH.txt` statuses do not override user Quest3 optical FAIL; `RUNTIME_VALIDATION` remains FAIL_ON_TESTED_OLD_SHA / UNTESTED_ON_NEW_SHA.
- This is not a successful validation of rank, GOAL, HUD or cockpit. R84 and R26 comparisons must keep separate compiled variant identities; CURRENT_FOCUS and R84_TEST are same R84 payload.

## Historic source-level category evidence (read before changing)
- `docs/VR_HUD_KNOWN_GOOD_RESTORE_RUNBOOK.md`: R64 `10c73daa037b5cc521b42ce7fb3a7cc1820b1921` user HMD-proven 6th/6 and menu fonts, not final result/+TIME. R62 `945e4471d6463f757f38b4b39d3eb8e492b2254f` proved 4th/5th car-attached ranks.
- `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp::R62TryFixedFunctionSpriteIndexed`: exact null VS, FVF `0x142`, D3DXSprite indexed; **both** `CorroboratesHud` native HUD plane and `CorroboratesProjectedWorldMarker` Calc3D2D plane, each with independent eye projections and projection restore.
- R84 `stereo_renderer_r30.cpp::R30TryFixedFunctionProjectedRankIndexed` previously admitted only projected marker, so source-owned *native indexed* 6th/6/Sumo/other HUD could reach physical draw with no stereo owner. New R84 material ports the source-scoped HUD branch and uses R84's existing `R30BuildStageExtensionXyzrhwEyePlane` head-inverse and eye-pair map, not a global colour/alpha/FVF promotion. Keep original shader, source WVP and F11 ImGui paths untouched.
- `src/hooks_graphics.cpp` + `driver_seat_car_space.hpp`: previously default `DriverSeatCarSpaceBasis=true`, which can choose car basis on one frame and native camera basis after invalid/stale `matrix_B0` on next. Pinned **NATIVE** in normal A/B/C runner and switched global default false; CAR remains opt-in for diagnosis. This is a plausible oscillation mechanism, not an already-optically proven cure.

## Next acceptance on NEW exact build (no repeating same unchanged ZIP)
1. Correct both-eye/full-scene gameplay before checking overlays.
2. `MAIN R84`, `R84_TEST`, `B_HUD` menu optical geometry and 75% scale separately. Original 4:3 source vs VDXR per-eye 2496x2688 must not be conflated with DX9Ex 3440x1440 desktop viewport; compare actual host menu quad and per-eye source fields.
3. Fixedfn native `6th/6`, text/GOAL/result and `F11` both-eye and head-stable; confirm debug `VR R84 R62 FVF142 stereo: owner=SCREEN_HUD` appears when actual screen HUD fixedfn submitted. Do not assume shader/XYZRHW draws are fixed by this indexed route.
4. Projected ranks 1st–5th stay attached to vehicles in 3D under yaw; independent `CAR_RANK` counter. R26's known-good game-FVF route must never suppress external F11 ImGui.
5. ESC/pause arrows and shell must be binocular, same optical plane, stable; sky/world must be rendered per-eye in **world** pass, not flattened into HUD. +TIME/GOAL moving-progress phase remains separately unresolved.
6. A/B/C cockpit must be steady in native basis; independently review native camera mode/time transitions and view rebuild only if oscillation remains. No original game EXE/PMT edits.
7. Runtime `UNTESTED` on new material until Quest3/VDXR optical verdict; Windows CI SUCCESS alone cannot approve optics.
