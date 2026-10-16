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
