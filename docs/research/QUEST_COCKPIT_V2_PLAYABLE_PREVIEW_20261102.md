# QuestCockpitV2 first playable-preview integration (2026-11-02 KST)

**Branch:** `vr-quest-cockpit-v2` ONLY. Published `vr-v0.01-beta` and `vr-d3d9ex-focus` unchanged. This is a Quest3 experimental build, not a stable release or proof of APK parity.

## Position equality question resolved
- Original Quest ARM64 `race_camera_eye_look_485590` mode 1 uses the original game's 30×36-byte model-camera anchor table at retail PC VA `0x5BA4E0`, with optional Quest-specific 16-byte override input **whose runtime enable is not proven**.
- Canonical original PC ROM: 30 entries; all first three floats of models `i` and `i+15` equal (15 pairs). **15 DISTINCT XYZ anchors**, not one universal XYZ. Other model-specific fields are not all identical.
- New `OriginalModeOneAnchor()` reads the live original EXE's *ROM* table (RVA `0x1BA4E0`), rejects unknown model/invalid matrix, transforms a local XYZ through `EVWORK_CAR::matrix_B0` row-vector basis. No manual per-car INI calibration. HMD eye tracking is applied independently once by the existing OpenXR path.
- Original mode 1 is the only admitted test mode; modes 0 and 2 remain normal. No extra offset `-1.35/-0.32/+0.65`, no 1.15 car scale and no duplicated old cockpit hooks.

## Wired runtime behavior, opt-in only
- `-VR.QuestCockpitV2Enabled=true` is an **experimental game camera** placement into the player's original car body-space anchor for native mode 1. In the original `FixZBufferPrecision::CalcCameraMatrix` callback it temporarily borrows position/look only across the original matrix calculation; RAII restores game camera work. The existing XR pose/eye renderer remains unchanged.
- Player callback `0x69764` forces full original player-car model (state1) only under the same opt-in mode-1 gate; robot callback preserves heroine/ambiguous characters, optionally omits only qualified player driver, scope strictly player-only. FFB, SDL/XInput, game physics, HUD, ESC/F11, screen effects and original car shadow remain independently owned.
- Three original PC frame/callback signatures must match to arm the trial owner. `CockpitFrameProbe=true` installs the fail-closed native correlation hooks. Logging is bounded and available through the experimental launcher. The original `FrameOwner` contract and B0/F0 occupant correction remain tested and compiled, **but actual correction is NOT globally injected into the original game**: precise PC draw owner/parent-child model traversal remains unverified.
- Original car origin may be a render/interpolation epoch different from the camera update frame; thus this EXPERIMENTAL build can still visibly jitter, clip, or render a player body incorrectly. No hard claim of successful Quest3 VR without the user's runtime log.

## User test instructions
Copy the GitHub Windows Actions test ZIP **entirely** into a separate copy of the original game containing `OR2006C2C.EXE`. Run `RUN-QUEST-COCKPIT-V2.cmd` (selects D3D9 and enables the V2 test only for that process); select in-car native camera mode1; use F12 recenter; compare camera modes0/1/2, standing/accelerating/turning, driver/passenger, menu/goal and MOZA R3. For original VR route run `Run-OutRunVRTest.cmd`; the shipped INI has `QuestCockpitV2Enabled=false` and `CockpitFrameProbe=false`. Send bounded local logs on mismatch, not proprietary binaries.

## Acceptance / outstanding
1. Windows x86 game DLL and x64 host exact-SHA GitHub Actions (verify after commit).
2. C++17 executable seat-table/row-vector tests plus native-correlation and correction tests.
3. Quest 3 runtime still **UNTESTED**; validate original native frame->BeginScene/Present/pose map using newly added read-only probes, then restore exact full Quest occupant `W × C` inside verified draw scope, optional glass only after PMT ownership proof, and safe all-screen regression before v0.02 promotion.
