# Critical Quest cockpit source-recovery erratum: first guest buffer is the PLAYER VEHICLE (2026-10-25)

**New independent source-corroborated finding** — corrects mistaken earlier labels that called guest `+0xB0 / +0xF0` “camera matrices”. The exact Quest machine-code and native Windows game structures show these belong to a distinct vehicle buffer, while the `+0x34A` mode gate belongs to a second camera buffer. This correction is crucial before writing a PCVR patch.

## 1. Exact two-buffer provenance in original Quest Ghidra and ARM64
Source (user's owned ELF) `PcSceneRenderer::render_frame` ELF **0x10CBE9C**, SHA256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`, corrected Ghidra base +0x100000:

```cpp
// Ghidra-normalized read-only semantic excerpt; C++ names below recovered independently.
renderer->vehicleAndCameraProvider->vtable[0x30](
    provider, &firstGuestView, &secondGuestView);
if (secondGuestView.size > 0x34A &&
    secondGuestView.data[0x34A] == 1) {
    // read firstGuestView.data[0xB0..+0xEC] and
    // firstGuestView.data[0xF0..+0x12C];
    // calculate 16-float thread-local cockpit_body_correction;
    // temporarily write identity into firstGuestView +0xF0..+0x12C;
    // render frame with firstGuestView matrix_F0 neutralized;
    // normal and unwind: restore all 16 elements; deactivate TLS.
}
```

Source-independent verification of the two distinct buffer origins:
- Quest decompiler `apk/_analysis_focus/correctbase_20261025/cockpit_render_frame.c.txt`, ~lines 133–170: `(*plVar3+0x30)(plVar3,&lStack_230,&lStack_240)`; camera selector `*(char*)(lStack_240+0x34a) == 1` (the **second** buffer); first buffer `lStack_230` is the source of `+0xB0` and `+0xF0` 16-float arrays and destination of identity writes. A Ghidra pseudocode label alone does not prove object types.
- Independently built Windows original-game `src/game.hpp` defines **`EVWORK_CAR::matrix_70`, `EVWORK_CAR::matrix_B0`, `EVWORK_CAR::matrix_F0`** sequential 4×4 `D3DMATRIX` fields, at exactly offsets **0x70, 0xB0, 0xF0**. `EvWorkCamera::cam_mode_34A` resides in an entirely separate structure.
- Public independent PC code `r4dius/outrun2-decomp/src/platform/pc_scene_renderer.cpp` and `pc_scene_renderer.hpp` explicitly identify **`vehicle_camera(vehicle, camera)`** as a paired guest-data getter. This strongly corroborates the Quest first/second buffer interpretation; the concrete Quest provider vtable target has not yet been fully type-proved by its native producer.
- Therefore guest `old_matrix` in the previous **211-operation** reconstructed C++ is very likely **vehicle `matrix_B0`** and guest `new_matrix` is **vehicle `matrix_F0`**. Do NOT try to apply the reference function to `EvWorkCamera::cam_pos_F8/look_pos_104` or camera matrix offsets.

## 2. Model-local transform independently confirmed
Public, reconstructed PC original vehicle renderer `src/platform/vehicle_model_draw.cpp` contains repeated model paths whose render-state bits `vm = (vehicle.flags_4 >> 14)&3` choose `vm==1`. Under this route it does:
- copy **64 bytes from `vehicle + 0xF0`** into a local 4×4 matrix;
- otherwise substitute identity;
- `pc_matrix_push` then **`pc_matrix_multiply_current`** with the local matrix;
- draw car-model pieces, steering wheel, roof, shadows etc.
- `src/platform/pc_vehicle_display.cpp` separately pushes the car's `+0xB0` matrix for body/world basis.
- This establishes a concrete physical reason for Quest's scoped identity of `matrix_F0`: the same car rendering state 1 normally introduces an extra **vehicle-local** matrix. Quest's body-correction TLS compensates occupant geometry while vehicle-local transform is neutralized.
- IMPORTANT: The user PCVR `VRDriverSeatRenderTest` only forces vehicle display state 1 (`src/hooks_graphics.cpp`, `EXE+0x69764`); it does **not** reproduce Quest's local matrix_F0 neutralization/occupant correction. Current PC model scale 1.15 is experimental, not a stand-in for either matrix.

## 3. Correct per-frame integration blueprint (do not patch production yet)
```cpp
// Typed pseudocode. Exact hook timing / pointer ownership still to prove.
// The two car matrices must come from ONE legitimate, stable player-car
// presentation snapshot, not a borrowed HMD/culling camera.
if (rendererCockpitFrame && nativeCameraMode1 &&
    samePlayer && hasValidMatrices && xrStereoFrameValid) {
    const auto B0 = snapshot(player->matrix_B0);
    const auto F0 = snapshot(player->matrix_F0);
    const auto correction = body_correction_from_guest_matrices(B0, F0);
    // Quest specifically scopes vehicle matrix_F0 = identity during its
    // native frame renderer; Windows cannot freely mutate simulation data.
    // Prefer render-only local matrix override within the EXACT car draw path,
    // with RAII restoration if staging borrowed mutable memory is unavoidable.
    // In the same committed frame, occupant draw consumes correction.
    // Single present/pose sequence owner; same decision camera, near, car,
    // driver and passenger; independent head/eye transforms applied once.
}
```
- **Driver/camera:** Do not rebrand `matrix_F0` as a camera render matrix. Camera mode `+0x34A` remains the **separate** selector gate. Current PC camera offsets are still built from mutable `cam_pos_F8/look_pos_104`, which may also be overwritten by `ApplyCullingCameraSync`; another separately evidenced risk.
- **Ownership:** record `(presentEpoch, vehicleIdentity, mode1, B0Hash, F0Hash, poseId, scenePass, originalCameraHash)` and verify matrix_F0 restoration/last-good invalidation on every path.
- **Scope:** only modify verified player draw/local matrix, **not original persistent `EVWORK_CAR::matrix_F0` from an arbitrary graphics callback**, nor unrelated NPCs. Reconstructed C++ arithmetic is not bitwise tested against real game frames; dynamic order/layout and hand rig still require trace.
- **Glass/driver:** the known 0.25 draw-scoped alpha and occupancy TLS are independent aspects; do not enable glass alpha globally.

## 4. End-to-end implementation readiness
Verified or strongly corroborated: camera mode1 gate, paired car/camera getter, distinct B0/F0 matrices, scoped local F0 identity and 16/16 normal/exception restores, correction producer → occupant consumer, player draw state1 → matrix_F0 multiplication, XR two-eye validity, PMT player event selection from PC comparison.

Still missing: exact Quest provider vtable implementation identity; how Quest rendering phases coordinate player car draw versus occupant; signed matrix convention and measured vehicle-specific eye anchor; exact glass geometry draw flag bit1 writer; controller-hand-to-driver bones; actual Quest3 vs PC runtime comparison. No claim original authored C++ recovered.

**STATUS: RESEARCH_ONLY / GAME_SOURCE_UNMODIFIED / CI_NOT_RUN / HMD_UNTESTED.** Prior research reports using term “guest camera +0xF0” should be read **only with this erratum**.
