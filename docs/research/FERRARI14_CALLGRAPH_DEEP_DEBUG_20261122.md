# Ferrari14 v0.03 — source-by-source callgraph debug (2026-11-22 KST)

**Task:** Continue real code-path debugging from the latest glass-order candidate without modifying the approved normal VR release. Latest functional candidate source SHA `f166b31f0637f91f0e5f65ac57a04f26d33ee89b` (report commit may be newer). Compare against known-working v0.03 release `2446269aa33bc3c90a2a57f36a650cdd4d4fd5d7`, and predecessor glass-source `816ed1d3524c3841806e50f7cf9f80d37857fbb0`.

## Causal call path, one subsystem at a time

| Step | Source entry | What was checked | Source outcome |
|---|---|---|---|
| 01 | `QuestCockpitV2NativeFrameProbe::OnFrameEnter` | Detect menu/race transition and release sidecar GPU/pose history | Existing reset-on-race-exit path; not changed |
| 02 | `OnPlayerCallback` | Native callback hooks, original game mode, original-camera/F0 scoping | Original callback is preserved on non-admitted paths; native camera code unchanged |
| 03 | `ProbeCockpitCarMotion` | Probe guards run before player validation | Probe checks null player and opt-in probe flag before dereference; source path SAFE |
| 04 | `CallOriginalPlayerWithGlassScope` | Invalid ticket / Model OFF still invokes original callback | `if(f50.valid && DrawPreparedF50External(f50))` protects early runtime path |
| 05 | `PrepareF50External` / `Eligible` | Player identity, race, cockpit mode 1, stereo, stateblock recording | Fail-closed; 2D/menu/no device/non-owned car fallback to original |
| 06 | `MatchesFerrariSelection` / `BuildSidecarPath` | Canonical IDs 5 and 20 map to same 575 OVC | Bounded static filenames and aliases; other user cars excluded by 575 ON launcher |
| 07 | `SafeFloorLift` -> `ComputeExternalFloorLift` | OVC parser/CRC validated; static wheel-ground correction | **CONFIRMED mismatch:** producer accepted lift up to 1.25m but pose consumer silently zeroed above 1.0m. Fixed shared policy |
| 08 | `F50VisualPoseFilter::Apply` | World B0 basis, local-up translation, same native frame stereo key | **FIX:** use `SanitizeExternalFloorLift` from placement header; validated 1.0–1.25m survives pose; F50 smoothing remains F50-only |
| 09 | `DashboardFrameLatch` | One native epoch/player dashboard capture, no uncontrolled eye-to-eye drift | Existing source latch; actual gauge calibration remains not hardware-verified |
| 10 | `EnsureLoaded` / `Parse` | OVC1–OVC4 CRC/group bounds/DDS/ground QA; one-time read | Existing strict limits, fail closed. Actual privately-owned 575 asset contents not visually certified |
| 11 | `EnsureGpu` / `GpuRetryPolicy` | Device ownership, GPU upload, failed allocation and reset | Failed device quarantined until Reset; PBR shader excluded from generic 575 experiment |
| 12 | `DrawNativeScene` | Full D3D9 stateblock restore, explicit viewport-relevant render states | **Hardening:** clear inherited depth/slope bias and sRGB write; set ADD alpha blend op before sidecar draw |
| 13 | `MeshInDrawPass` | Opaque depth write before tagged glass alpha pass | Retained prior verified glass order; stable per-class mesh order, no per-frame sort/allocation |
| 14 | `ChooseOriginalCarRoute` | No-submit=full native fallback, complete=replace, partial=quarantine | Existing route tests cover no duplicate full-car drawing after partial GPU submission |
| 15 | `OnDeviceReset` / `NotifyGameReset` | Sidecar resources released before D3D Reset and frame reinitialization | Existing game reset callback and GPU retry reset still in place |
| 16 | Exact v0.03 protected tree | `vrhost`, core D3D9Ex, native cockpit frame, game `Start-OutRun.cmd` | Protected paths unchanged and checked by CI |

## Material new correction A — accepted floor lift was lost

- Previous `external_car_ground.hpp::ComputeExternalFloorLift` output bound = `1.25f`; `f50_external_pose_filter.hpp::Apply` incorrectly accepted only `localUp<=1.0f`. For `modelMinY=-1.2f`, requested lift 0, the valid computed output is **1.235m**, then `Apply` previously threw it away and translated by 0.
- The new pure helper `SanitizeExternalFloorLift` centralizes the **same** upper bound as floor computation. Tests enumerate all 1451 model-min-Y millimetre steps from -1.2m to 0.25m against four requested lifts, check all admitted outputs survive normalization and reject NaN/infinity/out-of-range.
- The mismatch was real and could cause submerged external geometry on certain imported models. **Not proven** as the user's 575 OVC symptom without its exact private vertex envelope.

## Material new correction B — inherited GPU state

- Original sidecar set alpha blend factors and Z testing but left `D3DRS_BLENDOP`, `D3DRS_DEPTHBIAS`, `D3DRS_SLOPESCALEDEPTHBIAS` to previous game draws. Fixed-function also relied on inherited `D3DRS_SRGBWRITEENABLE`; PBR explicitly set it.
- After capturing `D3DSBT_ALL`, clear both depth-bias states (DWORD-encoded float 0), set `D3DBLENDOP_ADD`, and disable sRGB output in the *sidecar* before drawing. `saved->Apply()` still restores the actual prior native game states, so normal sky/HUD/present drawing is unaffected by construction.
- This removes nondeterministic inherited-state dependence. It is **not** evidence that the previously captured HMD frame actually inherited any bad state.

## Established prior run; not a measurement of current test DLL

User Ferrari13 run on 2026-11-20 reported DLL SHA `313d9925...` and host SHA `9ecc80a9...`, `PreferD3D9Ex=false`, `DirectGpuOnly=false`, cadence 0, `FollowGameResolution=true`. Official v0.03 published host is `8c7e5742...`, and its game transport flags differ. Old 25–31 FPS must not be extrapolated to this candidate.

## CI gates and hard safety limitations

- Portable C++ source contract including height consistency, all existing sidecar tests, original callback route, mesh draw ordering and code-token linkage: dedicated `Ferrari14 Source Trace and Floor Pose Safety` workflow. Exact new-source run and result to be recorded on completion.
- Exact Win32 binary build is mandatory before any updated DLL ZIP is called testable. Do not reuse the previous `816ed1d` DLL or manifest for the new source.
- **STOP / NOT SOLVED:** Successful sidecar drawing replaces the entire original native player callback; original sub-draw effects, passengers, glass and 575 pose equivalence are unproven in hardware. The generic PBR VS uses `c0/c4/c8`, not the verified game stereo `c64` path, and remains disabled in 575 ON fixed-function A/B. Per-call stateblock capture and 78+ mesh submissions are potential CPU/GPU overhead, not a proven FPS root cause. Original model's black paint, gray gauges and missing 13-car full compatibility cannot be corrected by C++ guard tests.
- Required Quest3 A/B: official v0.03 original -> exact patched model OFF -> 575 ON fixed-function -> short TRACE on failure, comparing left/right depth, native player visibility, FPS, frame cadence and release host identity. Normal release is not to be overwritten or promoted without physical PASS.
- Score: a new task achievement is **not** confirmed until the exact-source Windows build and regression gates both pass. A single source-debug repair earns at most +1, not one per changed file, workflow, test or rerun.

## Stereo ownership expansion: actual default compiled path, no speculative core change

- `CMakeLists.txt` sets `OUTRUN_VR_R26_HUD_DEFAULT ON`; fresh normal Win32 builds compile `stereo_renderer_r30_r26_safe.cpp`. R30's `DrawIndexedPrimitiveDestR30` is the higher hook and checks ImGui/finite HUD/XYZRHW owners before falling back through `R30GuardScreenSpace` to `DrawIndexedPrimitiveDestR26`. R26 then delegates to the existing R23/R7 base when no occlusion veto applies. Therefore auditing `stereo_renderer_r7.inc` alone does **not** describe all draws.
- The base fixed-function world classifier explicitly requires live VS=null, a native XYZ-family FVF, perspective projection, gameplay, and a Z-enabled non-screen semantic. The experimental body sets VS=null, XYZ|NORMAL|TEX1, perspective game transforms and depth enabled. Those source eligibility conditions are necessary but **not** proof that the physical HMD issued independent L+R eye draws.
- R30 calls `GameSemantic::ConsumeForDraw()` for each submitted DIP. A pending game-authored screen one-shot/queue semantic could in principle change the classification of an externally injected mesh. There is **no physical evidence** of this happening with the user's 575; do not override or fake global game semantics until a bounded exact-producer diagnostic captures the actual draw, screen-scope, left/right RT/depth, and HRESULT.
- Unverified generic PBR vertex constants `c0/c4/c8` remain disabled; do not reinterpret fixed-function source eligibility as a completed PBR stereo repair. Existing full-native-callback replacement remains a separately acknowledged opt-in hazard.
