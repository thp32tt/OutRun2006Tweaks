# DX9Ex R84 Mainline — Development, Test and Rollback Contract

**Scope:** `thp32tt/OutRun2006Tweaks` / `vr-d3d9ex-focus`. Effective 2026-10-15. Supersedes old instructions describing R26+HUD as the *default* renderer. DX11 Native and DXVK lanes are out of scope.

## One renderer owner for all new DX9Ex development and test

- **Main:** R84 independently compiled `stereo_renderer_r33.cpp` (sole physical draw dispatcher), `r32.cpp` (DirectGPU, Reset/Present support), `r31.cpp` (StateBlock/safe caches), `r30.cpp` (HUD/XYZRHW/SkyGlow), `r29.cpp` (stereo base); shared OutRun game WVP/camera and R23 lower source path.
- **Build:** `cmake -S . -B build -G "Visual Studio 17 2022" -A Win32` **with no `-DOUTRUN_VR` flags** selects `SAFE_DRAW_COMPARE=OFF`, `R26_HUD_COMPARE=OFF`, `C1/C2=OFF` and all four `REFACTOR_SPLIT` flags `ON`. CMake and cmkr TOML default flags must agree.
- **Test and package:** `DX9Ex Active Validation` must build its normal game DLL using that same option-free CMake configuration; only `dx9ex-r84-independent-full-chain-game` supplies `backends/d3d9/dinput8.dll` in the `OutRun2-VR-DX9EX-ACTIVE-<SHA>` ZIP. `START_DX9EX_TEST.cmd` and `CURRENT_FOCUS/CORRECTNESS` load the actual R84 DLL and exact-SHA x64 OpenXR host.
- **Recover:** `R26_SAFE` is separately compiled with `-DOUTRUN_VR_R26_HUD_COMPARE=ON`, other compare flags off. The CMake split defaults then select OFF automatically for this *explicit* comparison. This DLL is **only** `slots/R26_SAFE/dinput8.dll`, never the main `backends/d3d9/dinput8.dll`.
- **Legacy test-only:** `R84_TEST` remains an exact-SHA alias for R84, not a competing development owner. Historical R26/C1/C2 builds are not the default. Fail closed if CMake cache, ZIP variant, host hash or selected game DLL do not match the requested slot.
- **CI:** Exact SHA `policy`, default R84 game `full-chain-compile`, R26 fallback `game`, x64 host `host`, production ZIP `package`, Domain Isolation, and affected HUD/Full Source gates; test launcher, rollback hash equality and package BUILD_INPUTS/MAINLINE_BUILD_MODE.
- **Source scope:** New DX9Ex performance, lens, +TIME/GOAL, F11/ESC/HUD fixes belong in actual R84 owner/shared game/host code. A fix confined to `stereo_renderer_r30_r26_safe.cpp` is a fallback-only change and **does not** complete the R84 feature. Preserve previous optimizations and the intentional conservative flicker rollback; do not raw-merge old donor code.
- **Configuration cache:** CMake `option()` values are cached. For a developer switching from a previously configured R26/C1/C2 tree, use a **fresh build directory** or explicitly reset the previous `CMakeCache.txt` before checking R84 mainline defaults. Reusing the stale cache can select a different path.
- **Validation:** Build-verified CI is not headset approval. `RUNTIME_VALIDATION=UNTESTED` until Quest 3/VDXR independently checks both eyes, HUD/lens/source WVP, menus, +TIME/GOAL, reset/recenter, DirectGPU producer/host lifecycle, dense buildings/sand/spray FPS/frame time. Do not assert target 72/90/120Hz or quality equivalence from source checks.
- **Separate architecture v3:** The R84 independent render graph is structurally integrated, but the v3 `IGameAdapter/IStereoBackend/IPC v3` primary live authority remains blocked by `ARCH-V3-GATE-001`. Keep v2 live until an exact Quest3/VDXR baseline is accepted.
- **Automation:** GitHub is source of truth. Controller reads this policy and the branch at the next dispatch while honoring active owner/TASK_ID; a GitHub commit does **not** redeploy the external Docker/Portainer worker. Don't award any duplicate R84 structural score.

## Quick operator proof

1. Run the default `cmake` configure and confirm the eight R84 owner/compare cache entries in `build/CMakeCache.txt`.
2. In GitHub Actions, use the **ACTIVE** ZIP (not the standalone R84 game artifact).
3. Double-click `START_DX9EX_TEST.cmd`, confirm `CURRENT_VR_SESSION.json`: `VariantId=CURRENT_FOCUS`, `RendererBuildVariant=R84_SPLIT_R33_R32_R31_R30_R29` and matching SOURCE_SHA.
4. For rollback, select `R26_SAFE` and verify its exact `ACTIVE_R26_R43_R44` identifier, DLL SHA; restore `CURRENT_FOCUS` to return to R84.
5. Review Quest3/VDXR logs separately before claiming `RUNTIME_VALIDATION` beyond `UNTESTED`.
