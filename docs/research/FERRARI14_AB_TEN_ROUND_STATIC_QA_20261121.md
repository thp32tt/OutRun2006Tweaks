# Ferrari14 normal-stereo A/B recovery patch — 10-round repeat static QA (2026-11-21 KST)

## Reviewed exact artifact and source
- Archive: `Ferrari14_Quest3_NormalStereo_AB_PRIVATE_20261121.zip`
- ZIP SHA256: `275108bf77c5c1d0023145a803f1a09c3cff4541dfd8238c1d61f973e4db25ad`, 11 files. No original game EXE or third-party OVC files in this patch.
- Compiled DLL SHA256: `9f80db33031fd15289e1bc74081066cd8a57bb0e688b187152596e005e672707`, native Windows PE x86 machine 0x014C, exact byte match to GitHub Windows Release Build artifact run **44775223482**.
- Normal VR host SHA256: `bbeb46ea441513f2eeb89dc60291b75854df0b55a75155e9ffef5027ff886fb8`, PE x64 machine 0x8664, exact byte match to official Quest cockpit v0.03 release inner archive pinned to `5eb417782179c0c944ac2c28fc04a223b0b130fa`.
- Previous broken runtime DLL/host SHA checks explicitly pinned to user session log: `313d9925b48fab98dbe2445201cfc54a1e2a05ab34fb940b6bc3761c94e97a4e` and `9ecc80a902985506a66b93446f38d724190d622eba09a0f2683891714579460c`.

## Ten repeated archive, launcher and installer checks
Performed **10 independent repeated scans**, **102 actual checks per scan**, **1020/1020 PASS**:
1. ZIP CRC, 11 entry count, duplicate/path traversal, no zero-byte entries
2. Game DLL x86 and VR host x64 PE structure / correct size
3. Actual payload and QA JSON hash bindings, source commit and no false HMD success
4. PowerShell verify-only default, explicit install, model SHA, old-runtime rejection, source/target checks, both file backups and post-copy verification
5. Rollback guards (manifest schema, original backup hashes, unexpected installed file changes, game must not be running)
6. Three launcher profiles preserve direct transport, D3D9Ex preference, 2496×2688 eyes, fixed render resolution, cadence=1, no disabled stereo
7. Windows CMD static continuation syntax and host-hidden prewarm, correct executable
8. Baseline model OFF vs fixed-function A/B model ON vs optional car trace ON; flag differences restricted to model/trace toggles
9. README warns old Ferrari13/Ferrari575 launcher reverts runtime, physical test not done and non-PBR normal-map lighting in A/B
10. Exact DLL comparison with GitHub build; host comparison with original v0.03 release; no original commercial game EXE or licensed third-party model binary in patch.

**Test-harness finding:** First runs raised 3 failures per cycle only because checker incorrectly required an ending newline after a valid `exit /b 0`; actual Windows batch syntax does not require it. Corrected tester to `rstrip().endswith('exit /b 0')` and repeated all 10 full scans with 0 failures. A previously vacuous QA assertion was separately replaced with a real normal-release-untouched assertion and all 10 scans passed again. No actual patch defect was identified by these runs.

## Ten repeated native C++ tests (isolated N100, 1 compiler thread)
Cloned current branch `8c85de96f2ebe7e7652eb67a5542eeed8bd7eb07` and independently verified GitHub comparison with pinned compiled source `9b749fadfa7c4af2664c8fc23a944cc5dc592d96`: only a documentation markdown changed, so **same C++ source**. Compiled 5 portable tests with `g++ -std=c++17 -O0 -Wall -Wextra -Werror -pedantic` (**5/5 compile PASS**). Re-executed all five tests 10 times (**50/50 PASS**):
- `external_car_ground_test` (ground alignment/floor)
- `external_car_gate_test` (original-car fallback/replacement admission)
- `external_car_dashboard_test` (dynamic speed/RPM binding)
- `external_car_sidecar_v4_test` (V4/DDS/PBR-sidecar contracts)
- `game_reset_events_test` (release GPU objects before device reset)

GitHub CI on exact compiled source: Windows Release Build `44775223482` SUCCESS; Ferrari14 Normal-Core Stereo Recovery Gate `44775223637` SUCCESS; EXE HUD Inspector `44775223436` SUCCESS.

## Ten repeated 575 model OVC4 independent verification
Re-ran separate, previously independently authored V4 OVC parser on actual preserved 575 hybrid model `575superamerica_External_Test.ovc` (SHA256 `16c15b9bd05bc69b581fa1fddda73bb7c6461ab59ff121109ae29ff30fa87e71`): **10/10 PASS**, checking V4 header, CRC32, complete DDS/PBR material stream, 57,786 triangles, 78 groups, two unique speed/RPM binding records and 0 trailing payload bytes.

## Explicit remaining limitations
- **NO Windows PowerShell installer execution was performed in this test** (PowerShell interpreter unavailable locally; script static policy was inspected, not Windows runtime exercised).
- **NO actual Quest3 HMD stereo, runtime performance, model placement or horizon/road occlusion verified**. A C++ test/ZIP hash cannot prove draw transforms, eye-specific camera, scene visibility, real 120Hz frame pacing or the original displayed 25fps issue resolved.
- The A/B path deliberately sets `OUTRUN_VR_EXTERNAL_FIXED_FUNCTION_TEST=1`, thus bypassing the current PBR normal/ORM shader path while investigating VR eye mismatch. Not a full PBR-quality build.
- Old `START-FERRARI575-VR.cmd` / `START-FERRARI13-VR.cmd` in the test game folder must **not** be launched; they may reinstall the earlier broken runtime. Do not install patch into known-good v0.03 production directory; use only the copied test directory and the SHA-gated installer.
- An actual Windows PowerShell execution/sandboxed mock installation, physical Quest3 baseline vs external ON screenshot/metrics and per-car placement inspection remain outstanding.

## Score
This is the re-verification of already-scored `FERRARI14-NORMAL-CORE-STEREO-AB-CI-20261121-9B749FAD` and existing 575 model artifacts. **+0**; do not duplicate that source integration achievement. Latest AI2 scoreboard before this report: **2881**.
