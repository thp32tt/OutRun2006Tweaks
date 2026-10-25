// Research-only, typed bridge for OutRun PCVR cockpit recovery.
// NOT a runtime game hook. No modification of EVWORK_CAR or EvWorkCamera.
// Prov: Quest APK 2026-10-25 original AArch64 render_frame @ 0x10CBE9C.
// Source binary SHA-256 fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6
//
// Strongly cross-corroborated original memory owners:
//   vtable+0x30(provider, &vehicleGuest, &cameraGuest)
//   cameraGuest[0x34A] == 1 gates cockpit
//   vehicleGuest[0xB0] = EVWORK_CAR::matrix_B0
//   vehicleGuest[0xF0] = EVWORK_CAR::matrix_F0
// The concrete Quest provider vtable implementation still needs type proof.
//
// Include path is only for optional research compilation in the original repo.
// No game production source depends on this file.
#pragma once
#include "../../src/game.hpp"
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <type_traits>

namespace quest_cockpit_research {
static_assert(sizeof(D3DMATRIX) == 64u, "Expected D3D9 16xfloat matrix");
static_assert(std::is_standard_layout_v<EVWORK_CAR>,
              "Cannot validate car offsets with offsetof");
static_assert(offsetof(EVWORK_CAR, matrix_B0) == 0xB0u,
              "Quest +0xB0 maps to the vehicle, not camera");
static_assert(offsetof(EVWORK_CAR, matrix_F0) == 0xF0u,
              "Quest +0xF0 maps to the vehicle, not camera");
static_assert(offsetof(EvWorkCamera, cam_mode_34A) == 0x34Au,
              "Mode selection is from the separate camera record");

struct VehicleFrameMatrices final {
    std::uintptr_t playerIdentity = 0;
    std::array<float, 16> matrix_B0{};
    std::array<float, 16> matrix_F0{};
};

// Capture unmodified player-vehicle input for one render frame.
// Caller MUST establish that the player pointer is authoritative, its lifetime
// spans capture, and it has not been replaced/reused between frame boundaries.
inline bool CaptureVehicleMatrices(const EVWORK_CAR* player,
                                   const EvWorkCamera* camera,
                                   VehicleFrameMatrices& out) noexcept {
    if (!player || !camera || camera->cam_mode_34A != 1) return false;
    VehicleFrameMatrices value{};
    value.playerIdentity = reinterpret_cast<std::uintptr_t>(player);
    std::memcpy(value.matrix_B0.data(), &player->matrix_B0, sizeof(D3DMATRIX));
    std::memcpy(value.matrix_F0.data(), &player->matrix_F0, sizeof(D3DMATRIX));
    for (const float x : value.matrix_B0)
        if (!std::isfinite(x)) return false;
    for (const float x : value.matrix_F0)
        if (!std::isfinite(x)) return false;
    out = value;
    return true;
}

// Implemented in research file quest_cockpit_body_correction_reconstructed_20261025.cpp.
// This is an arithmetic experiment, NOT a proven complete eye/world-view pose.
std::array<float,16> NativeCorrectionReference(
    const std::array<float,16>& vehicle_B0,
    const std::array<float,16>& vehicle_F0);

// Actual native arithmetic symbol (not linked into the game by this header):
namespace implementation {
    // quest_research::body_correction_from_guest_matrices(...) is the
    // separately generated research implementation under docs/research.
}

// Implementation contract for subsequent production patch:
//   1) capture car B0/F0 from the SAME frame as cam mode-1 admission;
//   2) compute body correction from captured B0/F0 (not camera vectors);
//   3) stage renderer-local matrix_F0 = identity ONLY during player model draw;
//   4) consume correction in the scoped occupant pass;
//   5) restore any borrowed original car matrix on normal AND exceptional exit;
//   6) apply latched OpenXR eye transforms once; menu/effects untouched;
//   7) glass state changes only after player PMT draw owner is proven.
// DO NOT copy/paste a direct persistent EVWORK_CAR::matrix_F0 write here.
} // namespace quest_cockpit_research
