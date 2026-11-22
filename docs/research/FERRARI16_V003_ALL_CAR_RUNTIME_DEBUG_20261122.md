# Ferrari16 v0.03: 16-car native external runtime debug (2026-11-22 KST)

## Scope / immutable baseline
- User request: continue the broken external Ferrari Quest 3 model debugging across **all sixteen distinct cars**, not only the 575 Superamerica.
- Known-good, **untouched** normal VR release: `vr-quest-cockpit-v2-v0.03-release` @ `2446269aa33bc3c90a2a57f36a650cdd4d4fd5d7`.
- Debugging starts from `vr-ferrari14-v003-source-trace-fixes-20261122` @ `d45c9d8a5f0e127aa5362ceded7202d7e8ab9a77`; all new modifications confined to `vr-ferrari16-v003-multicar-debug-20261122`.
- **Do not merge into or overwrite the working v0.03 release until real Quest 3 A/B, per-eye pose, driver-eye cockpit clearance and stable FPS PASS.**
- Opt-in experimental replacement still suppresses the entire original player-draw callback on a submitted model, so native subdraw/passenger/lighting parity is NOT proven. PBR c0/c4/c8 stereo path still disabled; only fixed-function per-eye diagnostic candidate.

## Verified full 16-car retail mapping
These represent 16 models, exposed through 30 retail base/tuned game IDs. Original first-party PMT is always used when optional sidecar is missing, malformed or ineligible.

| Canonical ID | Car | Preferred private asset | Tuned retail alias |
| ---: | --- | --- | ---: |
| 00 | Dino 246 GTS | ExternalCars/car_id_00.ovc | 15 |
| 01 | 365 GTS/4 Daytona | ExternalCars/car_id_01.ovc | 16 |
| 02 | F50 | ExternalCars/car_id_02.ovc | 17 |
| 03 | 360 Spider | ExternalCars/car_id_03.ovc | 18 |
| 04 | F355 Spider | ExternalCars/car_id_04.ovc | 19 |
| 05 | 575 Superamerica | ExternalCars/car_id_05.ovc | 20 |
| 06 | Testarossa (roof variant still to verify) | ExternalCars/car_id_06.ovc | 21 |
| 07 | 288 GTO | ExternalCars/car_id_07.ovc | 22 |
| 08 | 328 GTS | ExternalCars/car_id_08.ovc | 23 |
| 09 | 250 GTO | ExternalCars/car_id_09.ovc | 24 |
| 10 | 512 BB | ExternalCars/car_id_10.ovc | 25 |
| 11 | F40 | ExternalCars/car_id_11.ovc | 26 |
| 12 | 550 Barchetta | ExternalCars/car_id_12.ovc | 27 |
| 13 | F430 Coupe | ExternalCars/car_id_13.ovc | no tuned ID in retail table |
| 14 | Enzo / FX | ExternalCars/car_id_14.ovc | 29 |
| 28 | F430 Spider | ExternalCars/car_id_28.ovc | the tuned-only retail entry |

Do not mistake the default high-quality **13/16 exact variants** for 16/16 real playable models. Three extra exact candidates (328 GTS, 575 Superamerica, F430 Spider) are owner-private optional/lower-detail sources and not promoted. No current user 16-car OVC package was opened or live-tested in this run.

## Corrected common-source defects

1. **GTO/F40 wrong identity on the 16-car launcher:** the previous `PrepareF50External` forced ID 7/22 into legacy `288gto.ovc` and ID 11/26 into legacy `f40.ovc`, preventing their normal canonical `car_id_07/11.ovc` high-quality assets from being selected. All `VR.ExternalFerrariTest` IDs now route through `GenericId`, with fixed-name fallback **only if canonical path is absent**, not when its contents are malformed. Separate opt-in F50 experimental `F50_External_Test.ovc` remains intact.
2. **Unnecessary reloading for tuned aliases:** `GpuOwner::SelectSidecar` previously used raw retail ID as resource identity, rebuilding the same model GPU buffers and textures when switching from a base to its tuned alias. Now it keys cached resources by canonical car ID, preserving the same validated OVC and preventing redundant per-alias model loads.
3. **Per-frame file stat / extra path resolution:** `SafeFloorLift` previously called `Installed()` on every eligible player callback before `EnsureLoaded()`. The latter already performs actual file open and CRC parsing once per selected car; removed redundant per-frame `GetFileAttributesW` while preserving fail-closed missing/malformed handling and reset semantics.
4. **575-only debug receipt exhaustion:** four diagnostic counters previously had global eight/four/six sample caps; first selected Ferrari consumed them and subsequent cars had silent traces. New bounded `std::array<...,30>` counters are indexed by canonical car ID for per-car first-error, route, gate and transform visibility. No unlimited frame-by-frame spam. Normal A/B logging remains off.
5. **Prior universal GPU state isolation retained:** zero depth/slope bias, ADD blending, sRGB reset, explicit clipping, clip-plane disable, vertex-blend disable, opaque-before-glass ordering; all confined to sidecar stateblock.

## Real checks performed, not inferred hardware results

- Exact full-car routing tests: all 30 IDs, **16 unique canonical models**, pair aliases, selected-car gate, full-callback fallback, partial-GPU quarantine, native epoch/pose consistency, 16-car floor math, same-frame speed/RPM latch and GPU reset retry.
- Previous ten portable sidecar regression test programs run again (including 50 distinct old diagnostic checks) from the latest branch.
- New `tools/ferrari16/verify_all_car_ovc.py` read-only native file preflight: all sixteen canonical paths, GTO/F40 missing-file-only fallback, optional dashboard overlays; validates OVC header/CRC, group and index bounds, finite vertices and UVs, DDS mip size, PBR map/factors, animated needle bindings, GPU budget and *role-specific* road versus dashboard model envelopes. Self-test constructs a synthetic valid V4 model and rejects a deliberate CRC mutation. **The actual private user OVC files were NOT available to this GitHub CI and have NOT been certified by this self-test.**
- GitHub Actions **PASS** at source/runner/testing commit `572d920eb54400b0330268874944183e3c31ae99`, workflow `Ferrari16 All-Car Sidecar Regression` run `44980004029`: all eleven C++ portable programs, synthetic OVC validator, exact production file-path/token assertions and protected normal-release source parity.
- Windows Win32 Release binary build started for exact source, but **not declared PASS until CI completes**. No new game DLL/patch installer or public release produced in this task as of writing. Previous 575-only compiled DLL MUST NOT be relabeled as all-car build.

## How to run privately, after exact Windows DLL becomes available

1. Retain the installed working official v0.03 game. Create a **separate** verified copy using existing test-copy installer, never the existing v0.03 live folder.
2. Stage a **matching compiled x86 dinput8.dll** from this exact branch into that test copy only; do not use the original 575 patch installer without updating its manifest and verifying the exact produced DLL SHA. Preserve official v0.03 EXE, INI and x64 host.
3. In the separate game root, place `tools/ferrari16/RUN-FERRARI16-V003-MODEL-OFF.cmd`, `RUN-FERRARI16-V003-ALL-CARS.cmd` and `RUN-FERRARI16-V003-ALL-CARS-TRACE.cmd`. They run from their own directory, so they need the EXE alongside them.
4. Run the offline preflight on the separate game directory (Python 3 required):
   `python tools/ferrari16/verify_all_car_ovc.py --game-root "C:\OutRun-Ferrari16-Test" --json-out "C:\OutRun-Ferrari16-Test\ferrari16_preflight.json"`.
   A MISSING model is not a crash; the native original remains. A FAIL is a bad OVC candidate; do not enable replacement for that car until corrected.
5. In Quest 3, test unchanged original v0.03, then same game copy with `MODEL-OFF.cmd vr`, then `ALL-CARS.cmd vr`. Change through all sixteen base/car IDs and tuned aliases; compare binocular stereo and world depth, driver-eye visibility, native passenger, 2D/menu/focus, first-stage sky, sidecar transparency, speed/RPM/gear needles and FPS. The all-car launcher uses `ExternalFerrariTestCarId=-1`, F50 special OFF, fixed-function stereo and explicit callback-replacement opt-in.
6. On first reproduction, run `ALL-CARS-TRACE.cmd vr` briefly and gather both game and VR-host/watchdog logs with the selected retail car ID, exact DLL/host SHA, device type, DirectGpuReady and measured eye frame timing. Restore the prior matching DLL from a verified backup on ANY new model-OFF regression.
7. Do not conflate all-car **source coverage** with all-car **asset or headset PASS**. Neither model color/PBR parity nor full callback effects can be accepted without a live HMD test.

## Scoring
Single multi-car source correction/test outcome; do not count each slot/CI retry/source commit as separate work. Latest account-wide AI 2 SSOT at task start: 2887 points (2026-11-22 08:53 KST). Score decision deferred until exact Windows build and distinct-source achievement evidence are confirmed; no speculative addition.
