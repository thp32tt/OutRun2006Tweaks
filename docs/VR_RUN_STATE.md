# VR Run State

Updated: 2026-09-20 23:10 KST

## Current checkpoint
- C0 RECOVER: complete — analyzed user logs from matrix `VRM-20260920-803144005c0e`
- C1 REVIEW: complete — delivered D3D9 SAFE path was an R26/R23 regression-isolation build, not the intended completed DX9Ex renderer
- C2 IMPLEMENT: complete — created `vr-d3d9ex-focus`, removed DXVK/DX12 from its dedicated workflow, added four DX9Ex-only comparison candidates and automatic per-variant log collection
- C3 VALIDATE: in progress — DX9Ex-only workflow run `35515548121`
- C4 COMMIT: complete for workflow/test-harness changes
- C5 PACKAGE: pending successful P1-P4 builds
- C6 STATE: current document

## Strategy change
DX9Ex is now the only active renderer target. DXVK, multiview and DX12 are frozen until the user accepts a correct and smooth DX9Ex reference. The generic Build workflow is disabled on `vr-d3d9ex-focus`; only the dedicated DX9Ex four-variant matrix should compile runtime candidates.

## Why the previous package regressed
The last D3D9 SAFE build explicitly compiled the R26/R23/R22/R13/R9 chain and excluded R29-R34 plus renderer R29. Runtime did reach TRUE STEREO SBS compose, so the new corruption was not a simple stereo-transport failure. In heavy gameplay samples the log rose to roughly 1,800-2,000 draws per Present and more than 568k semantic rejects, matching the expensive conservative replay path. The recovery launcher also forced 60 FPS, interpolation OFF and cadence OFF while the OpenXR host reported 90 Hz, adding a separate source of visible judder.

## DX9Ex four-build set
1. `P1_C1_FAST_WORLD`: R29 fast L+R + restored R27/R28 perspective-world classifier.
2. `P2_C2_FAST_HUD`: P1 + R30 HUD/XYZRHW/SkyGlow.
3. `P3_FULL_R34`: full R29-R34 chain.
4. `P4_R26_HUD_SAFE`: R26 world + R30 HUD/effect overlay, conservative comparison.

All use `PreferD3D9Ex=true`, allow fallback when DirectGPU sharing is not ready, enable dynamic OpenXR PhaseLock, remove the forced 60-FPS test cap after XR cadence becomes active, enable interpolation, and keep `SkyGlowFactor=1`.

## Next runtime test
Test P1 -> P2 -> P3 in that order. Use P4 only if the fast-path candidates remain badly corrupted or as a conservative comparison. Use the same short gameplay segment each time and upload the automatically generated `DX9EX_LOG_<variant>_<time>.zip`.


## Checkpoint 2026-09-21 02:06 KST
- C0 RECOVER: restored source head `2827f20d456d5fb266cfbefbd4435df0f9952569`, state and run `35516112968`.
- C1 REVIEW: no renderer review repeated because binary inputs were unchanged. Failure isolation found all P1-P4 Win32 DLL jobs and the common x64 host succeeded; only package assembly failed at PowerShell `$variant:` parsing.
- C2 IMPLEMENT: preserved packager delimiter fix `2827f20`; added missing declared runtime keys for experimental unlock, Desktop Duplication fallback and dynamic XR cadence in `ee94dc8051b6de8c0b6ce67d9bdd8b613b98363c`.
- C3 VALIDATE: reused artifacts from run `35516112968`. Four distinct x86 DLL hashes and one shared x64 host were confirmed. Follow-up workflow `35524755335` is running against the corrected INI.
- C4 COMMIT: config fix committed through GitHub CAS; `vr-openxr` and paused backends were untouched.
- C5 PACKAGE: local deterministic package `OutRun2_VR_DX9EX_4PACK_f46024f7005c.zip`; SHA256 `ba1757865c445e5f63d37041a1f10dbed8a3137ae049960ec752fc5c9b0fb44b`.
- C6 STATE: complete. Each inner ZIP contains 11 files, passes its own SHA256SUMS, has PE32 x86 `dinput8.dll` and PE32+ x64 `outrun-vr-host.exe`, and excludes DXVK, multiview and DX12 payloads.

## Next action
Quest 3/VDXR runtime evidence is now the gate: test P1 first, then P2 and P3 in the same scene; use P4 only as the conservative fallback. Upload the four auto-collected `DX9EX_LOG` archives. Do not resume other backends.


## Final CI seal
- Workflow `35524755335` completed successfully at source `ee94dc8051b6de8c0b6ce67d9bdd8b613b98363c`: host, P1-P4 games, package assembly and package validation all passed.
- Final artifact ID: `10609329194`; artifact/SHA256: `a21825389f0731ffc62dc23314a1415261bf05fcdf07f4accd4d92a0aa46e630`.
- Frozen test matrix: `DX9EX-20260920-ee94dc8051b6`. Runtime validation is the only remaining acceptance gate.
