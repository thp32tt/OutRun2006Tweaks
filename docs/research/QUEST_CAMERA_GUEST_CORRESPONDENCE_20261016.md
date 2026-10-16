# Quest APK ↔ original PC camera/body: focused native translation mapping

Date: 2026-10-16 KST. APK source: user's local `outrun2.apk`, native ARM64 `liboutrun_quest_core.so` SHA-256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`. Static inspection only; no original APK code/assets copied.

## Proven PC-address matches
- PC original `CalcCameraMatrix` at EXE offset `0x84BD0` → VA `0x484BD0`: native `camera_project_484bd0` ELF VA `0x118ed40` and translated `or2x86::tr_network::F_484bd0` ELF VA `0x579bb0`.
- Original `RobotDisplay` at offset `0x114C10` → VA `0x514C10`: translated `or2x86::tr_bulk::F_514c10` ELF VA `0xc1aa6c`.
- Native camera mode switch `race_camera_view_switch_484a40` ELF VA `0x119240c`, 536 bytes. AArch64 direct memory accesses cover `0x340`, `0x344`, `0x34A`, `0x34B`, `0x360` (and transition byte `0x342`). The function decrements transition counters and writes selected view IDs; it does **not** prove an additional game camera enum.
- Native `race_robot_driver_display_4879b0` ELF VA `0x39fd04`, 108 bytes: uses original-car render bits `(flags & 0xc000)==0x4000` then dispatches native robot display. This agrees with the PC hook forcing state 1 in `DispCarModel_Common`.
- Native `race_robot_driver_chara_487ee0`, `race_robot_driver_matrix_488af0`, `race_camera_eye_look_485590` and `camera_control_485fe0` exist, preserving original PC guest VAs in names.
- Separate ELF TLS `cockpit_body_correction` (64 bytes), `cockpit_glass_opacity` (4), `cockpit_glass_premultiplied` (1), vehicle/occupant scopes exist. **Only state existence and relocation are proven**, not windshield draw IDs or glass shader blending.

## Implemented PCVR code in this change
- New opt-in `[VR] DriverSeatCarSpaceBasis=false` preserves existing native camera-mode-1 interpolation and the legacy camera-based translation unless enabled.
- With opt-in, the seat translation uses the original player's `matrix_B0` local-to-world orientation (D3D row-vector forward/up axes) instead of the possibly smoothed camera yaw. Forward-axis sign is aligned with the native bumper view; near-parallel and invalid states are rejected.
- Camera, car-model enable, driver hiding and near plane all share the same validation path. Preserves original simulation camera after building the view matrix. Applies only inside the established world/cockpit pass; does not alter SceneEffect, HUD, DX11, DXVK or controller/FFB.
- Added an **executed Release test** for same-basis parity, yaw-follow, reverse local axis, zero/parallel/sideways/NaN/overflow and recovery.

## Limits and acceptance
- This is a clean-room **hypothesis-driven adaptation**, not proof that `matrix_B0` duplicates Quest's `cockpit_body_correction`; AArch64 TLS write/read traces and each vehicle asset rig are not yet mapped.
- Car-space feature stays opt-in until HMD verifies seated offset across 360SP/other cars, car pitch/yaw and transitions. Windshield transparency remains unchanged pending positive glass/material ID and per-eye blend-state ownership; do not broadly reduce alpha.
- Follow mandatory exact SHA Win32 R84 / R26_SAFE / x64 host / Domain / HUD / package validation. HMD `RUNTIME_VALIDATION=UNTESTED` until physical Quest3/VDXR evidence.
- N100 local analysis files `apk/_analysis_focus/camera_guest_match_20261016.json`, `disasm/camera_view_switch_20261016.asm`, `driver_display_20261016.asm` remain local and are not redistributed.

## Subsequent APK TLS data-flow verification (bounded AArch64 xrefs)

A bounded AArch64 ADRP + TLSDESC relocation resolver was run against the same ARM64 SHA, then each hit was checked against the native disassembly. This upgrades the following findings from mere symbol presence to observed **read/write site linkage** (not yet a complete shader/material trace):

| TLS state | Native producer / consumer | Evidence |
|---|---|---|
| `cockpit_render_active` | `PcSceneRenderer::render_frame`, `display_race_car`, `Draw::disp_514c30` | TLS access sites at `0x10cbf58`, `0x10cc7d4`, `0x10c9288`, `0xd610cc` |
| `cockpit_vehicle_draw` | `display_race_car`, `render_object_405360` / morph / palette | `0x10c929c`, `0x10abd44`, `0x10ac268`, `0x10ac4dc` |
| `cockpit_occupant_draw` | `Draw::disp_514c30`, node visibility | `0xd610e8`, `0x10aa3f8` |
| `cockpit_body_correction` | `PcSceneRenderer::render_frame` writes a 64-byte 16-float matrix; `Draw::disp_514c30` reads it | `0x10cc2ac` → `0x10cc2e0–0x10cc2fc` 16 stores, `0xd61124` → matrix FMADD |
| `cockpit_glass_opacity` | `Flush::draw_404700(pmt_records::DrawEntry, PcPmtResources)`, `GlD3D9Device::flush` | `0x10b99bc`, `0x2fd140` |
| `cockpit_glass_premultiplied` | Same native `Flush::draw_404700` ↔ `GlD3D9Device::flush` | `0x10b99a8`, `0x2fd15c` |

This establishes a particularly useful pipeline: **original guest draw producer `0x404700` → native `DrawEntry`/PMT resource handling → per-draw opacity/premultiplication state → GLES flush**. The `0x10b99d4` draw loop also materializes 1.0 and 0.25 float constants, but this alone does not establish which texture or windshield draw uses 0.25. It is not safe to apply a global D3D9 alpha multiplier.

**Next exact-code gate for glass:** compare the PC original `Flush::draw_404700` and associated PMT `DrawEntry` / render-state write with the native `0x10b99a8/0x10b99bc` call sites. Recover the specific material/texture/producer identity and blend equation before routing to the R84 R33/R29 per-eye source. Both eyes must use the same identified material identity but independent depth and color targets; restore blend states afterward.

**Scope distinction:** APK matrix correction has an actual 16-float writer/consumer. The opt-in PC `DriverSeatCarSpaceBasis` added earlier uses original `matrix_B0` orientation as an independently implemented *approximation*; it is **not** the exact native matrix writer. Do not claim bitwise parity or full cockpit completion. Raw private disassembly is retained only on N100 under `apk/_analysis_focus/disasm/*_20261016.asm`.
