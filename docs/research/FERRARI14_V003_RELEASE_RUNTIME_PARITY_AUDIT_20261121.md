# Ferrari14 vs current official v0.03 release — startup/runtime parity audit (2026-11-21 KST)

## Exact comparison anchors

- **Official current release branch:** `vr-quest-cockpit-v2-v0.03-release` at `2446269aa33bc3c90a2a57f36a650cdd4d4fd5d7`, exact public GitHub release tag `v0.03` (published 2026-11-20 15:34Z).
- **Ferrari diagnostic branch:** `vr-ferrari14-stereo-recovery-normal-20261121` at source fix `27531c2137ef776960745e84772f42eeb86e53ff` (later commits merely add research documents).
- **Merge base:** `5eb417782179c0c944ac2c28fc04a223b0b130fa` = approved normal v0.03 functional code. Release branch's 2 extra commits modify **only** `.github/workflows/vr-github-general-build.yml` and `README_VR_v0.03.txt`. Ferrari branch adds `src/hooks_graphics.cpp` (+311 lines), `src/vr/game/outrun_renderer.cpp` (+2 lines), Ferrari-only headers/tests and opt-in launchers; `Start-OutRun.cmd`, native Quest camera/seat and D3D9 stereo core are byte-identical in GitHub.
- **Verified real packaged official release artifact:** downloaded exact `normal-v003-final-5eb41778-artifact.zip` and extracted inner `OutRun2_VR_v0.03_Beta_Cockpit.zip`. Local package `Ferrari14_575_Only_Stereo_Diagnostic_v3_50Trace_20261121.zip` was reopened and compared, ZIP CRC PASS. This is actual binary/package comparison, not just source assumptions.
- **Package SHA256** official `OR2006C2C.EXE` `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`, official `OutRun2006Tweaks.ini` `630fc782a7b99666bc6f62ee0c791f160bddb6b1a879ef97f39f38763ac77358`, official `dinput8.dll` `b4fc8d100c8716c12829f1defe76a959fc9953119ba792a8e72ca56ccec5cbe1`, official x64 `outrun-vr-host.exe` `bbeb46ea441513f2eeb89dc60291b75854df0b55a75155e9ffef5027ff886fb8`. Ferrari v3 DLL `4105326e624d624477d2d03736f2efd22d7f9aeb76bc4c0785afcb5f81acc065`, host **same exact bytes** as official release. No user hardware invocation in this audit.

## Findings prioritized by risk

### P0 — v3 installer is **not actually installable on a clean official v0.03 release copy**
- Official v0.03 DLL hash `b4fc8d10...` is not in `APPLY-FERRARI14-575-V2.ps1` accepted prior DLL hashes. Allowed: older Ferrari13 `313d9925...`, previous A/B `9f80db33...`, previous v2 `1bf14c87...` or already installed new `4105326e...`. Thus v3 is a **legacy-Ferrari-test-folder updater**, not a clean official-release-delta installer, regardless of the release-like launcher.
- Installer requires a pre-existing **exact 575 hybrid OVC hash `16c15b9b...`** and checks only existence of `OR2006C2C.EXE`; it does **not** pin official release EXE SHA, does **not** inspect/replace/validate the official release INI and includes neither EXE nor INI. User's old Ferrari13 test folder may retain a different EXE and saved graphics/VR options. No observation can attribute a new failure solely to Ferrari changes until baseline binary/INI parity is demonstrated.
- Fix gate: **separate clean release copy** + official EXE/INI exact hash audit + explicit test-copy marker + new opt-in release-base installer that never modifies the working v0.03 folder; preserve rollback of prior DLL and host. The existing v3 installer must remain isolated and must **not** be relaxed to accept any arbitrary DLL.

### P0 — native player car callback is bypassed on successful external draw
- Official `src/hooks_graphics.cpp` `CallOriginalPlayerWithGlassScope` always wraps `QuestCockpitGlassLive::PlayerCallback` and invokes `PlayerCallbackHook.ccall<void>(player)` (original player-car render callback). Ferrari `src/hooks_graphics.cpp` around lines 1201–1210 instead calls `PrepareF50External` and `DrawPreparedF50External`, and **returns early** on complete/partial external submission. This skips the whole original player callback, not merely the original paint/body mesh.
- Native effects, state changes or scoped subdraws owned by that original callback are therefore not guaranteed parity. **Do not claim ROB02 passenger disappearance is confirmed**: its separate native event hook may draw elsewhere. Verify exactly which original subdraws are inside `PlayerCallbackHook.ccall` before replacing or suppressing individually.
- The earlier 50-path portable tests model admission and route receipt, **not** actual nested native callback side effects.

### P1 — separate world/pose basis and F50-specific vertical filter leak into 575
- Official v0.03 `OnPlayerCallback` computes `C=ComputeBodyCorrection(B0,F0)`, snapshots original `B0/F0/C` and temporarily stages identity `F0` for the original player render scope. The added sidecar instead uses `ticket.world=player->matrix_B0`, then `GlobalF50PoseFilter().Apply(..., Settings::VRF50ExternalStabilize.get())`. The setting defaults **true** and is **not restricted to F50**: the **generic 575** receives F50's vertical low-pass filter too.
- Original Quest-native camera and passenger stabilization run their independent paths. Relative offsets/phase and external-car near-eye visibility are therefore **not proven equivalent**. This may explain car-body shaking/occlusion despite preserving the original camera code. Instrument B0/F0/C/VR view vs mesh bounds in the same native frame before changing seat calibration.
- Avoid globally retuning seat F11 height, world scale or 575 geometry on this evidence alone. A controlled 575-only no-filter A/B is the next safe experiment.

### P1 — external shader/render route differs from normal game's verified stereo route
- Ferrari sidecar PBR VS uses matrices `c0/c4/c8` and is **not** the verified game's `c64..c67` WVP lineage. The V3 575 ON launcher explicitly sets `OUTRUN_VR_EXTERNAL_FIXED_FUNCTION_TEST=1` to bypass that unverified PBR path. This is a **diagnostic downgrade**, not a production-quality PBR fix.
- The unchanged v0.03 R7 renderer does support per-eye fixed-function transform duplication conditionally when bound vertex shader=null, FVF XYZ, perspective projection, gameplay world semantics and Z enabled. Actual driver state and eye draws of this new OVC have not been physically proven.
- Fixed-function draw explicitly disables lighting, sets two-sided `D3DCULL_NONE`, uses texture-only shading and creates+catches `D3DSBT_ALL` stateblock each `DrawNativeScene`. The 575 hybrid has 78 mesh groups, so 78 `DrawIndexedPrimitive` calls **per accepted native sidecar draw** (plus optional dashboard). This is extra CPU/GPU cost versus release; no current-binary FPS number is known.
- R22/R31 **already hook StateBlock::Apply and perform state-cache invalidation and lazy resynchronization** (`stereo_renderer_r22.cpp`, `stereo_renderer_r31.cpp`). Do not incorrectly report StateBlock apply itself as an unhandled new bug; extra stateblock cost and live capture correctness remain measurement questions.

### P1 — known model asset quality independent of normal engine
- Exact 575 original and hybrid sources both contain fully opaque black RGB(0,0,0) Ferrari paint DDS. The experimental hybrid replaces the original 256×256 gauge atlas with a low-information 16×16 gray material on 6,074 gauge triangles; geometry overall remains ~2.09m wide ×1.20m tall ×4.54m long. A black near-eye vehicle panel can therefore be a **material plus local pose/occlusion issue**, not evidence that the normal world sky/road renderer itself is bad.
- The private diagnostic original-gauge red-paint OVC is a **controlled material A/B only**, not a Quest3-approved vehicle.

## Demonstrated release parity / ruled-out major core regressions

| Layer | Evidence | Verdict |
|---|---|---|
| Current release launch flags | Official packaged Start-OutRun vs V3 baseline: 48 common CLI options have identical values; V3 baseline adds only ExternalFerrariTest=false and F50ExternalModel=false | **Basic flag parity PASS** |
| Transport/cadence | Both normal VR command paths use PreferD3D9Ex=true, DirectGpuOnly=true, 2496×2688, FollowGameResolution=false, FrameCadenceMode=1 | **Flags match**, actual GPU directReady not measured |
| OpenXR x64 host | Both binary SHA256 `bbeb46ea...` | **Exact same host** |
| OpenXR core, native stereo and camera | GitHub diff contains no source changes in host/stereo/camera/Quest native files | **Normal engine core unchanged** |
| 2D/FFB original release flow | `Start-OutRun.cmd` source identical; Ferrari separate launcher preserves same two-mode menu | No code-level 2D launcher regression detected |
| Actual 575 draw/sidecar path | Extra hook, B0 pose filter, state blocks, sidecar material and PBR/fixed-function pipeline | **Major unproven runtime differences** |
| Old 25fps log | Logged former Ferrari13 DLL/host, forced D3D9Ex=false/DirectGpuOnly=false, SBS/Desktop Dup | **Cannot project old 25FPS result onto new v3 binary** |

## Recommended acceptance sequence

1. Save official v0.03 working installation unchanged. Create a fresh licensed v0.03 game test copy, checking all four official EXE/INI/DLL/host hashes before any modification.
2. Verify **baseline with original release DLL and release launch** on same Quest3/OpenXR settings. Then install a separately gated **release-copy** Ferrari DLL only and run model OFF with exact same launch options. If model OFF fails, diagnose hook/resets/EXE/INI integration, not 575.
3. Run 575 ON with fixed-function, compare native vs external frame/eye mesh submissions, screen-space pose/depth overlap, directReady, fresh/cached frame count, GPU/CPU frame times. Short TRACE only after reproducing.
4. A/B 575 pose filter OFF and isolate original callback subdraws. Only after acceptable stereo and seat-relative geometry add verified PBR stereo matrices and model lighting.
5. Do not call Ferrari14 physically fixed/ready based on ZIP CRC, CI or 50×50 pure helper tests.

This is comparison and static inference with exact user artifact/package and current GitHub evidence, **not** a physical Quest3 test. No user normal release files modified. Score: audit only (new independent result not scored).
