# Ferrari14 575 — 50 distinct code-path debugging cases

**Date:** 2026-11-21 KST  
**Branch:** `vr-ferrari14-stereo-recovery-normal-20261121`  
**Source correction:** `27531c2137ef776960745e84772f42eeb86e53ff`  
**Test file:** `tests/ferrari14_trace_50_test.cpp`  
**Executed:** actual g++ `-std=c++17 -O0 -g -Wall -Wextra -Werror -pedantic` compiled and executed against current source headers; **50/50 PASS**, test SHA256 `f979b2fe37717e2cc325ada9d50a3f050da4665ee3df530f150dab2d679e4a6f`. These are **50 independent input/branch scenarios**, not 50 full Windows/HMD runtime launches.

## Actual entry-to-draw code path

`RUN-FERRARI14-575-ONLY-VR.cmd` → `VR.ExternalFerrariTestCarId=5` → original player callback `OnPlayerCallback` → `PrepareF50External` → `MatchesFerrariSelection` → `Eligible` → `GlobalGpu().SelectSidecar` → `SafeFloorLift` → source B0 + native View/Projection + latched XR frame → `DrawPreparedF50External` → `CanReplaceOriginalCar` → `GpuOwner::DrawNativeScene` → GPU draw receipt → `ChooseOriginalCarRoute` → suppress original only when external has been rasterized; otherwise invoke original callback.

## 50 individual executed cases

| # | Actual branch/case traced | Result | Source implementation |
|---:|---|:---:|---|
| 01 | selected base 5 | PASS | [external_car_selection.hpp:11](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/external_car_selection.hpp#L11) |
| 02 | selected tuned 20 | PASS | [external_car_selection.hpp:11](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/external_car_selection.hpp#L11) |
| 03 | reverse tuned selector to base | PASS | [external_car_selection.hpp:11](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/external_car_selection.hpp#L11) |
| 04 | f50 excluded from 575 | PASS | [external_car_selection.hpp:11](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/external_car_selection.hpp#L11) |
| 05 | f430sp excluded | PASS | [external_car_selection.hpp:11](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/external_car_selection.hpp#L11) |
| 06 | f40 tuned excluded | PASS | [external_car_selection.hpp:11](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/external_car_selection.hpp#L11) |
| 07 | invalid requested -2 fails | PASS | [external_car_selection.hpp:11](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/external_car_selection.hpp#L11) |
| 08 | requested 30 out of bounds | PASS | [external_car_selection.hpp:11](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/external_car_selection.hpp#L11) |
| 09 | player ID 30 out of bounds | PASS | [external_car_selection.hpp:11](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/external_car_selection.hpp#L11) |
| 10 | legacy all-cars request -1 | PASS | [external_car_selection.hpp:11](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/external_car_selection.hpp#L11) |
| 11 | 575 owned player eligible | PASS | [dino_external_sidecar.hpp:296](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_sidecar.hpp#L296) |
| 12 | no opt-in rejected | PASS | [dino_external_sidecar.hpp:296](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_sidecar.hpp#L296) |
| 13 | 2D path rejected | PASS | [dino_external_sidecar.hpp:296](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_sidecar.hpp#L296) |
| 14 | outside cockpit rejected | PASS | [dino_external_sidecar.hpp:296](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_sidecar.hpp#L296) |
| 15 | menu state rejected | PASS | [dino_external_sidecar.hpp:296](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_sidecar.hpp#L296) |
| 16 | invalid XR stereo rejected | PASS | [dino_external_sidecar.hpp:296](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_sidecar.hpp#L296) |
| 17 | not player draw rejected | PASS | [dino_external_sidecar.hpp:296](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_sidecar.hpp#L296) |
| 18 | no D3D device rejected | PASS | [dino_external_sidecar.hpp:296](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_sidecar.hpp#L296) |
| 19 | D3D recording rejected | PASS | [dino_external_sidecar.hpp:296](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_sidecar.hpp#L296) |
| 20 | wrong ticket car identity rejected | PASS | [dino_external_sidecar.hpp:296](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_sidecar.hpp#L296) |
| 21 | valid epoch and pose can replace | PASS | [dino_external_original_car_gate.hpp:13](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_original_car_gate.hpp#L13) |
| 22 | opt-out not replace | PASS | [dino_external_original_car_gate.hpp:13](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_original_car_gate.hpp#L13) |
| 23 | rival player not replace | PASS | [dino_external_original_car_gate.hpp:13](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_original_car_gate.hpp#L13) |
| 24 | menu draw not replace | PASS | [dino_external_original_car_gate.hpp:13](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_original_car_gate.hpp#L13) |
| 25 | external camera not replace | PASS | [dino_external_original_car_gate.hpp:13](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_original_car_gate.hpp#L13) |
| 26 | eye pose invalid not replace | PASS | [dino_external_original_car_gate.hpp:13](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_original_car_gate.hpp#L13) |
| 27 | inactive frame not replace | PASS | [dino_external_original_car_gate.hpp:13](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_original_car_gate.hpp#L13) |
| 28 | device null not replace | PASS | [dino_external_original_car_gate.hpp:13](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_original_car_gate.hpp#L13) |
| 29 | stale native epoch not replace | PASS | [dino_external_original_car_gate.hpp:13](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_original_car_gate.hpp#L13) |
| 30 | different XR pose not replace | PASS | [dino_external_original_car_gate.hpp:13](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_original_car_gate.hpp#L13) |
| 31 | all mesh submitted complete | PASS | [dino_external_original_car_gate.hpp:33](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_original_car_gate.hpp#L33) |
| 32 | zero expected fallback | PASS | [dino_external_original_car_gate.hpp:33](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_original_car_gate.hpp#L33) |
| 33 | no triangle draw fallback | PASS | [dino_external_original_car_gate.hpp:33](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_original_car_gate.hpp#L33) |
| 34 | partial GPU draw quarantined | PASS | [dino_external_original_car_gate.hpp:33](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_original_car_gate.hpp#L33) |
| 35 | all submitted but D3D failure partial | PASS | [dino_external_original_car_gate.hpp:33](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_original_car_gate.hpp#L33) |
| 36 | state restore failure partial | PASS | [dino_external_original_car_gate.hpp:33](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_original_car_gate.hpp#L33) |
| 37 | over-submitted receipt avoids stock-car double draw | PASS | [dino_external_original_car_gate.hpp:33](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_original_car_gate.hpp#L33) |
| 38 | one of many partial | PASS | [dino_external_original_car_gate.hpp:33](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_original_car_gate.hpp#L33) |
| 39 | draw gate false overrides mesh success | PASS | [dino_external_original_car_gate.hpp:33](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_original_car_gate.hpp#L33) |
| 40 | single drawable mesh complete | PASS | [dino_external_original_car_gate.hpp:33](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_original_car_gate.hpp#L33) |
| 41 | native floor minimum 3.5cm | PASS | [external_car_ground.hpp:15](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/external_car_ground.hpp#L15) |
| 42 | native model floor lift | PASS | [external_car_ground.hpp:15](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/external_car_ground.hpp#L15) |
| 43 | negative bound exact edge | PASS | [external_car_ground.hpp:15](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/external_car_ground.hpp#L15) |
| 44 | out of envelope floor fail | PASS | [external_car_ground.hpp:15](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/external_car_ground.hpp#L15) |
| 45 | sunk model with min>0.25 reject | PASS | [external_car_ground.hpp:15](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/external_car_ground.hpp#L15) |
| 46 | nan floor reject | PASS | [external_car_ground.hpp:15](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/external_car_ground.hpp#L15) |
| 47 | speed RPM and gear valid | PASS | [external_car_dashboard.hpp:24](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/external_car_dashboard.hpp#L24) |
| 48 | two eyes same frame dashboard latch | PASS | [external_car_dashboard.hpp:24](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/external_car_dashboard.hpp#L24) |
| 49 | GPU failed device is quarantined | PASS | [dino_external_sidecar.hpp:270](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_sidecar.hpp#L270) |
| 50 | real device reset re-enables one retry | PASS | [dino_external_sidecar.hpp:270](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-ferrari14-stereo-recovery-normal-20261121/src/vr/game/dino_external_sidecar.hpp#L270) |

## New code defect discovered and corrected

Prior `ChooseOriginalCarRoute` returned `OriginalFallback` when an anomalous receipt reported `submittedMeshes > expectedMeshes`, even if at least one external triangle had already been rendered. Rendering the original stock car again in that case can overlay both bodies. New code prioritizes nonzero submission: `submittedMeshes == 0` → original fallback; `submitted > expected` or impossible `expected==0 && submitted>0` → partial/quarantine route; successful full count and restored state → complete external route. **Test #37** exercises the correction. It is a defensive error-path correction, not proof that the user's particular screenshot hit this condition. The normal Quest VR renderer source was not changed.

## Additional grounded audit

- **Prior broken physical session:** `FERRARI13_RUN_20261120T161837806Z.log` explicitly launched with `PreferD3D9Ex=false`, `DirectGpuOnly=false`, `FollowGameResolution=true`, `FrameCadenceMode=0` and older Ferrari13 DLL/host. That establishes a performance regression **for the old session only**, not an empirical measurement of the new patch.
- **Current v2 ZIP:** `Ferrari14_575_Only_Stereo_Diagnostic_v2_20261121.zip` was re-opened locally: CRC PASS; x86 DLL SHA256 `1bf14c87fb8307442acc1df15d71010b67f47f7edc5c14a77f91ebdfc3858b52`, x64 host SHA256 `bbeb46ea441513f2eeb89dc60291b75854df0b55a75155e9ffef5027ff886fb8`. Its original binaries predate the new #37 fix, so **do not describe v2 as incorporating the new correction**.
- **Limitations:** no Windows PowerShell execution, D3D9 driver stereo draw, Quest 3 eye-pair display, FPS benchmark, or seat-relative occlusion execution was part of these 50 pure-C++ test scenarios. Verified caller paths rely on native hooks, GPU runtime, and physical HMD testing. No evidence that corrected branch fixes user's camera obstruction or original 25FPS regression until hardware A/B confirmation.
- **Independent model issue:** previous exact 575 and hybrid material DDS have a fully opaque black car paint asset; the hybrid replaces the proper original 256×256 gauge texture with a gray donor gauge surface. These are separate from #37 route logic.

## Follow-up validation gates

Source build exact SHA → GitHub Ferrrari 50-path CI and Win32 Release → verify new DLL binary SHA against that exact build → private optional game-copy test model OFF vs 575 ON with matching normal host → headset left/right, FPS and bounded `VR FERRARI INPUT TRANSFORM` log → promote only on user's acceptance.

**AI2 scoring:** Do not score the previous 50/50 test result as an independent model/VR runtime success; a distinct code fix may qualify only after accepted CI and scoreboard SSOT audit.
