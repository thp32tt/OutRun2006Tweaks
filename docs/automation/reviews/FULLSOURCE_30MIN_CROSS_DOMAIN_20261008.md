# 2026-10-08 DX9Ex full-source cross-domain review (30-minute checkpoint)

- Work window: 2026-10-08 **09:53–10:23 KST** (approximately 30 minutes).
- GitHub SSOT branch: `vr-d3d9ex-focus`; material source/CI graph SHA: `43b3021b9c6cc45f5ad305804bd886470f421bf6`.
- All `src/` C++/.h/.hpp/.inc inventory: **124 files, 2,525,945 source bytes** at SHA `620d5b4d`; actual MSVC `/analyze` compiled the active R26+HUD Win32 game variant separately (not just the inactive R33 comparison).
- This is a code review, static source/binary/compilation analysis and automated mutation review. It is **not** a Quest3/VDXR runtime validation. `RUNTIME_VALIDATION=UNTESTED`, 00519 user-observed HUD double/head-follow/missing menus remains open.
- No source duplication/large checkout/N100 activity.

## Verified code issues and precise changes

| Severity | Source evidence | Root cause and cross-domain risk | Material commit |
|---|---|---|---|
| HIGH | `src/hooks_textures.cpp`, `D3DXCreateTextureFromFileInMemoryEx_Custom_dest` | Shared fast DDS path supported only a subset of D3DX Ex semantics but scene loader had no native fallback. Unsupported ColorKey/explicit width/format/mips/filter, pSrcInfo or pPalette could silently lose scene textures. Native D3DX fallback now preserves arguments and transient source lifetime. | `259d3cac`, verifier fix `850c522d` |
| HIGH | `src/hooks_textures.cpp`, `D3DXCreateTextureFromFileInMemoryEx_Custom` | A loader changed device-wide sampler state during texture creation, affecting future draws unrelated to the texture (HUD, scene, stereo and lens). Removed sampler-state mutations. | `259d3cac` |
| HIGH | `src/hooks_textures.cpp`, `FileDataCache::getFileData/cacheFile` | Background LRU writer under mtx1 vs getFileData reader/mutator under mtx2: unsynchronized unordered_map/list and naked vector data pointer invalidation by eviction during D3DX. Unified cache mutex and shared buffer owner retained across fast/native decode. | `be085195`, verifier fix `a9f42ac8` |
| MEDIUM | `src/hooks_drawdistance.cpp:188` MSVC C6387 | GlobalLock could return NULL passed immediately to memcpy; clipboard memory leak or transferred memory misownership on failed API. Guarded lock/open/empty/set/free. | `68df1d4e` |
| MEDIUM | `src/hooks_framerate.cpp:117` MSVC C6387 | unchecked LoadLibrary/GetProcAddress and timer capability function pointers; guarded optional API and nonzero period fallback. | `68df1d4e` |
| MEDIUM | `src/hooks_bugfixes.cpp:723` MSVC C6031 | unconditional Sumo file-loading race fix could install EnterCriticalSection hooks after failed InitializeCriticalSectionAndSpinCount. Fail closed and log before hook installation. | `620d5b4d` |
| HIGH integration gap | `.github/workflows/vr-dx9ex-active.yml` push-path filter | hooks_bugfixes, hooks_drawdistance and hooks_input sources were not watched; source-only fixes could skip canonical DX9Ex game/host/full-chain CI. Added exact path triggers and Win32 source verifier. | `43b3021b` |

## Hosted evidence (distinguish exact SHA)

- `850c522d` — **HUD Inspector CI 37710686700 success**, **DX9Ex Active Validation 37710686730 success** (policy/game/host/full-chain/package) for corrected scene texture fallback.
- `57242f53` — **Full Source Impact Review 37710992744 success**, both 124-file cross-domain source scan and Win32 MSVC `/analyze`.
- Initial Win32 analyzer log at that SHA contained **13 first-party C6xxx findings**, including clipboard GlobalLock, timer winmm, loader critical-section init; the third-party dependency analysis produces many more warnings and must not be counted as 13 project bugs.
- `620d5b4d` — full source scan and explicit Win32 mutation verifier **12 obligations, 10/10 deliberate faults rejected**, run 37712219036 source-cross-domain success. Domain Isolation Guard 37712219069 success. Full MSVC and HUD Inspector at this SHA were still in progress when cross-domain CI trigger patch was written.
- `43b3021b` — subsequent DX9Ex Active Validation **37712610038** and Full Source Impact Review **37712609977** were started by the new watch graph. No success asserted until exact-SHA jobs finish.

## Eight cross-domain review flags, prioritized

1. `F01/F07` detached DInput polling thread: possible unload lifetime risk, **ControllerHotPlug defaults false**, not a plausible default-session 00519 HUD root cause; do not change input ownership without explicit lifetime evidence.
2. `F02` fast-load Reset: D3D9 Reset risk on FramerateFastLoad=2 when not XR paced; **all examined VR test profiles use -FramerateFastLoad=0** and INI default 3, so do not label default VR bug.
3. `F03` EXE lens-flare string strcpy: prior `common` → `media` rewrite likely shorter, but original binary capacity and VirtualProtect failure path need canonical byte verification before rewriting.
4. `F04` `memcpy(*ppSrcData, replacementDDSHeader,...)` changes original game bytes before D3DX resource successfully created; historical original-game cooperation needs binary contract before any change.
5. `F05` rank 1–3 producer tags only final priority tail; verify canonical sprani producer never creates >1 node.
6. `F06` fixed-function ScreenOverlay2D uses finite head-recentered HUD plane, shader/c64 path says FOV-only; may be intentional historical R51 protection. Resolve owner semantics before changing rendered pixels.
7. `F08` scene D3DX fast/native fallback is fixed at source and host CI level; real menu/car/scene DDS pixel and alpha correctness still not proven.
8. Additional MSVC warnings in `hooks_wheel_ffb.cpp`: five C6320 catch-all SEH filters intentional crash barriers unless regression evidence; remaining lower impact C6246 shadowing, C6340 signedness, C6031 optional WSAStartup, C6400 locale comparison are triaged separately and not represented as confirmed visual bugs.

## Review conclusion / next action

Source-level **confirmed root-cause fixes** are in GitHub, with P0 negative mutation and cross-domain source checker. Do not substitute compilation or mutation tests for actual VR visual verification. Preserve previous 00519 failure and do **not** ask the user for repetitive HMD trials; after remaining image/semantic binary gaps close, freeze ONE exact material build for integrated Quest3/VDXR proof. Review material can become BUILD_VERIFIED only when matching exact-SHA game/host/full-chain/domain/HUD CI concludes successfully; pending/cancelled runs are not success.
