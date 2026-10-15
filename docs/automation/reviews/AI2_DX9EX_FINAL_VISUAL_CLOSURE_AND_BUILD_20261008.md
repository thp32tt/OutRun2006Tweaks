# DX9Ex P0 전체 화면 결함 최종 소스 정리 및 1회 테스트 빌드

- DATE: 2026-10-08 KST
- REQUEST: 두 차례 30분 원본/EXE/VR 화면 심층검토의 남은 사항을 모두 재점검해 증거 있는 것만 수정, 단일 테스트 ZIP으로 전달.
- SOURCE_AUTHORITY: authenticated GitHub thp32tt/OutRun2006Tweaks branch `vr-d3d9ex-focus`, `AGENTS.md`; original emoose mod, historical R59/R70/R71/R73/R74, pinned canonical EXE SHA `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`.
- PROTECTED: R50 road/vehicle world stereo and startup white-screen recovery, native game input, scene car-ground shadow, R23 pose/frame ACK/Reset, DX11 development isolated, DXVK frozen.
- User policy: no repeated HUD 1000/5000 static loops; use exact material SHA P0/Inspector + Active + source impact + domain gates; HMD remains `RUNTIME_VALIDATION=UNTESTED` pending user's actual Quest3 report.

## 1. Before this last integration — source fixes already packaged in 5f50ddc4
- Result-progress original E8 CALLs 0x97BE4/0x97DEC -> 0x2D200: bounded sibling ScreenHud ownership.
- GOAL TIME E8 0xBEA5A->0xBE020 and 0xBEA5F->0xBE150: direct helper originals and all appended sibling ScreenHud ownership.
- DispRank 6th/6 first kind1 sprani 0xB9DA6->0x29530, disjoint from eight following kind0 clip CALLs.
- SkyGlow final composite: horizontal blur target `reduced[eye]` on one-step; vertical blur target `temp[eye]` on two-step; retain pre-HUD scene capture failclose and configurable gain.
- XMT loader corrupt pointer bounds overflow-safe and five-hook partial-install atomic rollback.
- Pinned 108 original EXE contracts, direct 71 canonical HUD calls, 5 supplemental exact original producers, 10/10 known source windows, deterministic negative mutations; 4/4 source-SHA CI passed on earlier `5f50ddc478137ceaebb4c027737b8857ff4947d9`.

## 2. Final integration — P0-F11 GameState convergence
- Confirmed source difference: original Game::is_in_game() included TRYAGAIN and OUTRUNMILES (Theater) and excluded WARP/RESTART/GIVEUP/LINK_TIMEUP (actual race presentation). Exact CurrentPresentationMode() in R23 client used different state set; F11 external ImGui was scoped with the broad predicate instead of actual presentation.
- **Actual source fix:** `src/game_addrs.hpp::is_vr_gameplay_presentation()` now holds the nine exact Gameplay states from R45; both `src/vr/game/outrun_renderer.cpp::CurrentPresentationMode()` and `src/overlay/hooks_overlay.cpp::D3DEndScene` consume this shared function. Source is null-failclosed; front-end/select/ranking/TRYAGAIN remain Theater; normal STATE_GAME remains Gameplay; F11 true stereo guard remains inside RAII before `ImGui_ImplDX9_RenderDrawData()`.
- **Exact test protection:** `tools/verify_vr_visual_composition_p0.py` requires exact nine-state list, renderer call, F11 guard vs broad old helper, and three independent negative mutations (TRYAGAIN incorrectly gameplay, renderer drift, overlay drift). Inspector watches new header on push/PR (both lists), plus existing renderer/overlay; DX9Ex Active watches all src/**.
- MATERIAL_SHA candidate: `5868f8760e939e58212e9bc4fe5d15954a384f9c`. Resolve actual exact CI status/artifact before declaring release.

## 3. Remaining symptom families re-evaluated: source changes vs HMD proof
| Symptom | Current owner and decision | Runtime status |
|---|---|---|
| White HUD, 6th/6, +TIME, checkpoint, GOAL time/result percentage | Restored distinct original helper/glyph/first sprani sibling ownership and exact contracts; no blanket world-to-HUD promotion. | Source/CI prior PASS; current candidate HMD UNTESTED |
| F11 double/head-follow | Exact actual Gameplay/Theater classification unified in this integration. Retains active R30 FVF XYZ/orthographic bilateral projection/scissor with stock menu fallback. | SOURCE_FIXED / HMD_UNTESTED |
| Lens flare double | R30 exact SceneEffect shader WVP/XYZRHW eye handling and original Clr_SceneEffect near-plane restore already applied; historical R73 `0xCF53` projected-anchor + fixed 0.20 disparity had **unproven same-light relation** to earlier `0xCABE` DrawObjectAlpha. Direct cherry-pick risks stereo ownership/camera regression. Need same light ID/pose per-eye evidence before any additional parallax transform. | Existing source safeguards; OPTICAL_OPEN |
| Rank 4th/5th and rival marker | Existing all siblings + per-car rank invocation, finite Calc3D2D recovered view data, clipW behind-eye failclose remain. No proven new game carID/queue mismap; do not flatten real world marker into HUD. | OPTICAL_OPEN |
| Menu/selector DDS white | Previous original/native DDS+R14/R15 lifetime/partial UpdateSurface safe code, current XMT correction installed. Missing pixels require log/texture ID; not safe to force all textures white or bypass native. | SOURCE_SAFETY_FIXED / OPTICAL_OPEN |
| Start/selector shadow | Original three exact CalcPeraShadow calls are real world depth/stencil; `WorldParticle` scoped only. Duplicated shadow hypothesis needs one per-eye depth/stencil draw trace; no generic world-alpha swap. | OPTICAL_OPEN |
| SkyGlow | Proven compositing source input fixed, bilateral pre-HUD capture and failclose retained; sky brightness/headset factor requires one HMD observation. | SOURCE_FIXED / HMD_UNTESTED |
| Recenter and headlocked UI | Current frame poseSequence/recener yaw, finite HUD plane and host cached/recovery theater lifecycle coherent by source; no proven mis-composition without pose epoch/finalLayerKind. | OPTICAL_OPEN |
| 72/90 Hz performance | R23 capture/commit/render/endFrame P95, queue ACK + 60Hz sim pacing measurable; without runtime bottleneck numbers no safe arbitrary tuning. | PERF_UNMEASURED |
| Historical R70 nested BA9D0/R71 Sumo parent scope | Current specific result/GOAL and glyph/clip routes cover exact proven canonical edges; no further unhandled direct E8 bytes established. Avoid double-tagging unknown original sprite groups. | SOURCE_COVERAGE_REVIEWED / HMD_UNTESTED |

## 4. Full-build gate and final test protocol
- Required exact material-SHA GitHub Actions: DX9Ex Active Validation policy/game Win32/host x64/full-chain/package, OutRun EXE HUD Inspector static original disassembly + Win32 build, DX9Ex Full Source Impact Review game/host MSVC static analysis, Domain Isolation Guard.
- From one single **new** tested package, Quest3/VDXR test in natural order: menu/car DDS; 6th/6/arrow/YES-NO; normal GAME F11 and transition/theater; +TIME/checkpoint; GOAL/result percentage; 4th/5th/rival relative to car; lens head movement with SkyGlow off/on; start shadow; recenter; crowded sand section FPS. Logs sourceSHA, client GameState, finalLayerKind, frameId, poseSequence, SkyGlow capture, per-eye rank ownership, 72/90Hz P95.
- `RUNTIME_VALIDATION=UNTESTED`. No new actual headset test, even if every CI job succeeds. Do not mark Issue #13/00519 resolved based on build.

## 5. Exact CI result and package
### RELEASED EXACT TEST PACKAGE — authentic GitHub Actions artifact
- **FINAL 4/4 EXACT-SHA CI SUITES SUCCESS at 2026-10-08 22:20 KST.** The four GitHub runs all show `status=completed, conclusion=success` and `head_sha=5868f8760e939e58212e9bc4fe5d15954a384f9c`. The branch HEAD may contain later documents, but no newer game material than this source. No Quest 3 runtime optical PASS claimed.
- SOURCE_MATERIAL_SHA: `5868f8760e939e58212e9bc4fe5d15954a384f9c` (not later docs-only branch HEAD).
- DX9Ex Active Validation https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/37782451574: **SUCCESS all five**: `policy`, `game` Win32 DLL, `host` x64 OpenXR, `full-chain-compile` Win32 R33, `package`.
- EXE HUD Inspector https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/37782451549: static original x86 + all P0 F11 shared-state negatives SUCCESS, Win32 inspector build SUCCESS.
- Domain Isolation https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/37782451505: SUCCESS.
- DX9Ex Full Source Impact https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/37782451606: **SUCCESS all three**: source-cross-domain, x64 OpenXR host MSVC /analyze, Win32 game MSVC /analyze.
- **ONE DEPLOYABLE PACKAGE:** https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/37782451574/artifacts/11553510211, artifact ID `11553510211`, name `OutRun2-VR-DX9EX-ACTIVE-5868f8760e939e58212e9bc4fe5d15954a384f9c`, size `2,752,926` bytes; uploaded digest SHA-256 `247469d6e237f00e615a9a2f1cc11082ed1a8893f9d75309daedd931051b4c3e`.
- Package job `113330641488` downloaded exact game and host artifacts by digest, staged `dinput8.dll`, `outrun-vr-host.exe`, `SOURCE_SHA.txt`, verified each listed file and created nested `OutRun2_VR_DX9EX_ACTIVE_5868f8760e93.zip`, completed artifact upload successfully.
- This source includes the previous full P0 GOAL/RESULT/rank/SkyGlow/XMT fixes + new F11 shared theater-state fix. **No running HMD test has been performed**, so historical issue 00519 remains open with `RUNTIME_VALIDATION=UNTESTED`.
- Delivery policy: do not ask for repeated static checks or new pre-HMD build unless exact code changes, and do not merge speculative R73 lens 20%-disparity or turn real world car markers into flat HUD.

## 6. Canonical single-launcher repackaging — 2026-10-09 KST

- **The newest user-facing ZIP supersedes prior batch-heavy artifact #11553510211.** It is a package/runner-UX cleanup, not a new stereo/HUD GPU implementation. The game/host compilation and package contents were freshly validated in GitHub Actions.
- **NEW PREFERRED ZIP:** https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/37797477954/artifacts/11559811904 ; GitHub Actions artifact `11559811904`, name `OutRun2-VR-DX9EX-ACTIVE-3ffb1238223d858edfd4300ce89443a485ff81f4`, size `2,749,982` bytes, SHA256 `a97334fad0c73ea1e3e43f5d3491f00dab0ba06c1f11b51cc523e6ea1259d2be`.
- Exact package/code-source SHA `3ffb1238223d858edfd4300ce89443a485ff81f4` and newer documentation HEAD separate. DX9Ex Active `37797477954`: policy, game Win32, host x64, full-chain R33, ZIP package + extraction/hygiene test all SUCCESS. Original EXE HUD Inspector `37797477957`: static-exe-analysis and Win32 build SUCCESS. Domain Isolation `37797478103`: SUCCESS.
- **ONLY launch shortcut inside new package:** `OutRunVR-Slot-Selector.cmd`, opens `OutRunVR-Slot-Selector.ps1`. Extract ZIP contents to the folder already containing original `OR2006C2C.EXE`; double-click the `.cmd`, choose CURRENT FOCUS / CORRECTNESS first row, click `설정 + 바로 실행`. The slot GUI directly starts `Run-OutRunVRTest.ps1` which executes `OR2006C2C.EXE`. `outrun-vr-host.exe` is auxiliary and is not the user-started entrypoint.
- Package omits `Run-OutRunVRTest.cmd`, `OutRunVR-Backend-Selector.cmd`, `Collect-OutRunVRLogs.cmd`, and the unused alternate backend GUI. Preserve required `.ps1` runtime helpers; updated `Run-OutRunVRTest.ps1` displays an explicit PowerShell collector command for the exceptional host-not-exited recovery case.
- Release-specific `START_HERE_실행방법.txt` included. The packaging job enforces exactly ONE `.cmd` and NO `.bat` at any ZIP depth; exact expected slot launcher target and slot UI markers are also tested. Earlier overlaid ZIPs might leave unused `.cmd` in an existing user's folder; package does NOT delete user files.
- **Every future ZIP handoff** must print the launcher filename, click path, original game EXE dependency, download link, source SHA and verified package integrity. This rule is captured in `docs/VR_TEST_STRATEGY.md`.
- `RUNTIME_VALIDATION=UNTESTED` until actual Quest 3/VDXR test; prior 00519 visual regression OPEN. Nothing here claims lens/rank/GOAL runtime optical resolution.
