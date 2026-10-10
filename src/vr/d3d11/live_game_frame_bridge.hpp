#pragma once

#include <d3d9.h>
#include <cstdint>

namespace outrun::vr::dx11::live_game_frame {

// Production behavior remains DX9Ex. An explicit process environment opt-in
// enables a separate diagnostic native draw of the *actual game vertex data*.
// Never intercept, skip or replace the game's original D3D9 return value.
bool diagnostic_enabled() noexcept;

// Pointer lifetime is limited to this call: data is copied before returning.
// The caller must attest that data came from the current game Draw call or
// from a generation-current D3D9 Lock/Unlock CPU shadow.
void observe_linear(IDirect3DDevice9* gameDevice, D3DPRIMITIVETYPE topology,
                    UINT primitiveCount, const void* vertices, UINT stride) noexcept;
void observe_indexed(IDirect3DDevice9* gameDevice, D3DPRIMITIVETYPE topology,
                     UINT primitiveCount, const void* vertices, UINT stride,
                     UINT vertexCount, const std::uint32_t* rebasedIndices,
                     UINT indexCount) noexcept;

// Present draws an isolated inset only if native GPU pixels were produced.
// Failure never propagates to the original game Present.
void before_game_present(IDirect3DDevice9* gameDevice) noexcept;
void before_game_reset() noexcept;
} // namespace outrun::vr::dx11::live_game_frame
