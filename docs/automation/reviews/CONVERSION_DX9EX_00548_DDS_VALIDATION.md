# DX9Ex 00548 — reject invalid replacement DDS descriptors before mutating original UI metadata

## Scope and evidence
- Exact branch: `vr-d3d9ex-focus`; task: `CONVERSION-DX9EX-00548`; selected from P0 menu/car-selection texture failures after confirming that the recorded 0–1100 structure refactor chain is **COMPLETE**.
- Baseline source: `src/hooks_textures.cpp`, `HandleTexture` accepted DDS replacement on magic/dimensions/format/first mip size alone, then wrote `memcpy(*ppSrcData, file, sizeof(DDS_FILE))` into the game's original source header and published `sprite_scales`. DDS descriptor size fields were not checked.
- For malformed external replacement DDS, a correct magic and sufficient payload could pass that structural check while containing an inconsistent `DDSURFACEDESC2.dwSize` or `DDPIXELFORMAT.dwSize`. This violates layout preconditions before destructive metadata publication.
- Original input with zero width/height would divide by zero when constructing a UI sprite scale from replacement/original dimensions.

## Material source repair
- Guard the original width/height before computing any scale.
- Require replacement descriptor sizes to match `sizeof(DDSURFACEDESC2)` and `sizeof(DDPIXELFORMAT)`, and require valid DDS magic, before parsing replacement format, replacing the original header, updating pointers and assigning HUD sprite scales.
- Keep valid DDS decoding, cache/transient source lifetime, texture allocator choice, existing first-mip bounds and D3DX fallback unchanged. No changes to DX11/DXVK/localization branches.
- Extend `verify_vr_hud_dds_loader.py --self-test` to 20 source contracts and 14 deliberate defect mutations, enforcing descriptor checks and validation-before-header-overwrite ordering.

## GitHub Actions
- Validation-bearing material SHA: `f96b661fdededb2f61e72e4a14ad402abd76b183`.
- [HUD Inspector](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/37714119384): static job 113106557754 PASS (20 DDS guards, 14/14 mutation rejects, 71 HUD CALLs, 10/10 HUD mutation rejects, P0 static composition PASS); Windows build pending at record creation.
- [DX9Ex Active Validation](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/37714119420): exact SHA run; other jobs pending at record creation.
- [Domain Isolation](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/37714119310): success, independently verified.
- [Full Source Impact Review](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/37714119321): cross-domain inventory PASS, hosted MSVC analysis pending.
- **No Quest3/VDXR or local game runtime test**. `RUNTIME_VALIDATION=UNTESTED`. In particular, no proof that historical 00519 HMD menu/HUD defects are resolved.

The follow-up run-record commit is bookkeeping and never replaces the original material result SHA or triggers a new required game-build Gate.

## Exact-SHA gate closure

- `37714119420` DX9Ex Active Validation: **completed/success**, policy `113106559145`, game `113106667780`, full-chain `113106667797`, host `113106667807`, package `113108017607` all success.
- `37714119384` HUD Inspector: **completed/success**, static and Windows build success; confirmed `20` DDS source obligations, `14/14` negative mutations, `71` canonical HUD CALLs, `10/10` HUD mutation rejects, P0 visual composition static PASS.
- `37714119310` Domain Isolation: **completed/success**.
- HUD 1000/5000 static reviews: `37714119449` and `37714119350` success.
- Exact material package ID `11523475635`, SHA-256 `a78168037a77d8e4ac23db69d156340b4ac2c8eb016affbbf6443d8341308be3`.
- Separate full-source impact MSVC analysis `37714119321` was still running at record closure; this supplemental suite is not counted as passed until it finishes.
- `AUTOMATION_VALIDATION=PASS`; `RUNTIME_VALIDATION=UNTESTED`. No headset claims. This result record update is **bookkeeping-only** and is not a validation-bearing SHA.

## Supplemental source impact closure

- The independent `DX9Ex Full Source Impact Review` [37714119321](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/37714119321) also **completed/success** on the exact material SHA. Both source-cross-domain and MSVC analyze jobs passed.
- This is supplemental to, and does not alter, the already completed mandatory build and HUD gates; the tested material SHA remains `f96b661fdededb2f61e72e4a14ad402abd76b183`.
