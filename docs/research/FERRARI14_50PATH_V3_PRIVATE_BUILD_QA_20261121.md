# Ferrari14 50-path execution and private v3 runtime ZIP — 2026-11-21 KST

## Exact compiled source & CI
- Fix commit: `27531c2137ef776960745e84772f42eeb86e53ff`, derived from the pinned normal Quest 3 v0.03 core, no native stereo host/renderer change.
- Real Windows 32-bit Release Build: [GitHub Actions run 44873835207](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/44873835207) **SUCCESS**.
- Real Ferrari normal-stereo/sidecar CI: [run 44873835187](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/44873835187) **SUCCESS**, executes **50 distinct cases** in `tests/ferrari14_trace_50_test.cpp` in addition to pre-existing parser/selection/floor/dashboard/device-reset tests.
- Independently compiled and executed 50 scenarios as one suite on a resource-limited isolated machine. **50 separate whole-suite repetitions × 50 cases = 2,500/2,500 PASS**. Source SHA256 `f979b2fe37717e2cc325ada9d50a3f050da4665ee3df530f150dab2d679e4a6f`.
- GitHub per-case line-linked report: [50-path actual debug evidence](FERRARI14_50_PATH_CODE_DEBUG_20261121.md).

## Actual changed bug
`ChooseOriginalCarRoute` previously returned `OriginalFallback` on impossible mesh-receipt overrun (`submittedMeshes > expectedMeshes`) **even when triangles already rasterized**. It could then redraw the stock car, violating never-overdraw policy. Now nonzero submitted triangles with unexpected counts yield `ExternalPartial`, so original car is suppressed for that frame; the complete/partial/zero-submit cases are explicitly tested (#31–40). This is a concrete defensive error-path fix, NOT evidence that the user's earlier black-car frame followed that branch.

## v3 optional test patch (local user artifact; not publicly redistributed)
- Name: `Ferrari14_575_Only_Stereo_Diagnostic_v3_50Trace_20261121.zip`.
- Full ZIP SHA256: `016d5e95750afa7d405a0ec3cfff213fc0f9cf2e76850d080fe4bdec85e5e52b`.
- Size **2,970,939 bytes**, 11 files, ZIP CRC **PASS**.
- New `dinput8.dll` (Windows x86) SHA256 `4105326e624d624477d2d03736f2efd22d7f9aeb76bc4c0785afcb5f81acc065`, exact same bytes as run 44873835207 Win32 artifact; normal v0.03 x64 host SHA256 `bbeb46ea441513f2eeb89dc60291b75854df0b55a75155e9ffef5027ff886fb8`, unchanged.
- Reused three launchers for **model OFF / 575 model ON fixed-function / bounded 575 TRACE** with the **normal** direct-GPU/D3D9Ex/2496×2688 and cadence policy. F50 sidecar remains disabled, other cars stock.
- Opt-in PowerShell installer extends allowed previous DLL SHA list to include exact v2 `1bf14c87...`; it still validates original retail game path, expected **previous private hybrid 575 OVC SHA `16c15b9b...`**, source and host hashes, game not running, backup before replacement, restored hashes on failure. Separate rollback guards manifest and installed/new SHA.
- An independent local verification re-opened v3 and official GitHub artifact ZIP and validated **54/54 separate package, installer, architecture and launcher contract assertions**.
- Original commercial OutRun game EXE and cross-game model bytes are **not included**. Source PBR shading/culling/seat-relative occlusion still require actual VR physical A/B tests; do not call a released working 14-car build.
- `Get-Process` and install/rollback PowerShell were **not actually run under Windows in this source-only audit**. The 575 private model, original-gauges red-paint variant, cockpit screenshot and GPU frame timing need physical user validation.

## Source risks not claimed fixed
- The prior user's 25FPS/eye mismatch screenshot used the OLD Ferrari13 forced plain D3D9/SBS Desktop Duplication launcher. DirectReady for v3 remains untested on user's hardware.
- The 575 exterior paint DDS is opaque RGB(0,0,0) in both original exact and hybrid; model scale is ~2.09×1.2×4.54m, but still may cover the camera due to native B0/seat alignment.
- External fixed-function 575 uses `D3DCULL_NONE` (two-sided); geometry-normal winding audit showed 56,461 triangles with normal-consistent sign, 27 opposite and 1,298 near-zero dot. This does not alone determine correct game-space cull direction; enabling culling without headset A/B might make faces vanish.
- Fixed-function probe deliberately bypasses PBR normal/ORM lighting; this patch validates admission and stereo ownership only, not final graphic quality.
