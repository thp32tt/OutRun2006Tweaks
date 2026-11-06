# Dino OVC3 PBR vs original OutRun 2006: compatibility audit

Date: 2026-11-06 KST
Scope: only `feature/dino-external-pbr-runtime-v1-20261106`, originally based on `feature/dino-original-preserving-ai-rework-20261106`. No merge into baseline release or main.

## Verified source properties

1. Original game `OR2006C2C.EXE`, `Cars/*.sz`, PMT, XPR: no source or asset edits. Feature is in the mod DLL and a standalone OVC3 file.
2. The stable `[VR] DinoExternalCockpit = false` setting remains the default in `OutRun2006Tweaks.ini` and in `src/hooks_graphics.cpp`. The original player callback executes whether or not the external sidecar loads; PBR cannot make the base game dependent on the optional model file.
3. Eligibility is restricted to VR, stereo, QuestCockpitV2, playable race/mode-1, original player-car Dino `car_kind_11 == 1`, active native frame, valid XR pose and non-recording D3D9 state. This is not a general 2D, DX11 or DXVK PBR hook.
4. OVC1/OVC2 readers keep their existing signatures, vertex stride, index layout and albedo DDS upload. New OVC3 uses `OVRCABH3` plus bounded PBR material extension, with strict CRC/budgets and no silent format downgrade.
5. Default model path remains `Dino246_Cockpit_LHD_v15.ovc`. Only explicit `OUTRUN_VR_DINO_PBR_TEST=1` selects `Dino246_Cockpit_LHD_v15_PBR.ovc`. The new launcher sets this flag only for the child game session and restores the previous environment afterwards.
6. D3D9 `D3DSBT_ALL` save/restore spans new shader/texture stages; GPU sidecar default-pool resources and SM3 shaders are released on Reset and race->menu transition. This is a *source-path* check, not proof that a user's exit/menu crash is fixed.
7. `QuestCockpit-CopyRun.ps1` inherited a seriously malformed host identity check and repeated tail sections (PowerShell syntax invalid) in the ancestor branch. The PBR branch rebuilds one valid flow; the original legacy `-Mode DINO` model hash remains fixed, while `-Mode PBR` requires an independent manifest SHA and separate PBR model. Preflight rejects different existing sidecars before any backend installation changes. The restore manifest includes both stable and PBR paths.
8. Identically built x86 mod DLL and x64 OpenXR host are paired in the PBR CI artifact using both `SOURCE_SHA.txt` and `HOST_BUILD_SOURCE_SHA.txt`.

## Reproducible automated tests

- Linux: OVC1/OVC2/OVC3 strict parse, CRC, malformed DDS, NaN material factors, OVC2-to-OVC3 packer.
- Windows: actual `D3DCompile` for `vs_3_0` / `ps_3_0`.
- Windows: x86 R26 mod DLL build plus x64 OpenXR host build from the same SHA.
- Windows: parse actual PowerShell copy-run/restore, synthetic 32-bit DLL and 64-bit host machine checks, `-Mode PBR -VerifyOnly`, negative host source marker and model hash, simulated full install using a fake game exe, preservation of an existing OVC2 sentinel file, pre-write conflict rejection, opt-in environment during simulated launch, environment restoration, removal of new PBR model on restore and recovery of original user DLL/host.

## Real game compatibility **not yet established**

- No original-game process/gameplay/HMD test executed in CI. Windows compilation is not native game runtime proof.
- The original `PlayerCallbackHook.ccall<void>(player)` still draws before the external sidecar overlay in `src/hooks_graphics.cpp`. Therefore the previously observed **duplicate steering wheel and overlapping interior** are **not fixed** by the PBR material extension.
- No successful race-end -> loading -> main-menu -> exit/relaunch loop on the user's actual Quest 3 + PC has been established. Existing sky flicker, camera shake and menu crash are outside this PBR compatibility claim.
- No frame-time or stereoscopic image validation. GGX shader uses approximate directional/ambient light, not original game's true dynamic lighting/environment reflections.
- No turn-key ZIP with an actual proprietary Dino OVC3 model was produced. The standalone build artifact contains matching backend binaries; the copy-run script additionally requires a complete verified `QUEST_APK_COPYRUN_PAYLOAD` with an operator-created OVC3 sidecar and `DinoPbrModelSha256` in the package identity. Do **not** copy the new binary over an active old release and press the old launcher.

## Safe next physical test

1. Keep the presently working game directory intact and test in a **copy**.
2. Use the exact-source matched PBR Win32 DLL + x64 host; place a tested OVC3 file at the **separate PBR filename** and use only the dedicated PBR launcher with its full matching manifest. Verify package first.
3. Before claiming parity, capture original OVC2 vs OVC3 race/menu flows, per-eye screenshots, driver wheel duplication, original sky/HUD, seat camera, GPU frame times and crash dump if any.
4. Restore with `RESTORE-QUEST-APK-COCKPIT.cmd` if any compatibility fault is reproduced.

Status: **SOURCE/CI COMPATIBILITY PARTIALLY VERIFIED; ORIGINAL GAME VR RUNTIME UNTESTED.**
