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

// A supported zero-count Draw has no CPU VB/IB/UP shadow. Observe its source
// ordinal; after the real D3D9 call, failed HRESULT still aborts native output.
void observe_empty_game_draw(IDirect3DDevice9* gameDevice,
                             D3DPRIMITIVETYPE topology) noexcept;

// An existing game VB/IB/UP Draw whose CPU snapshot cannot be mirrored still
// advances the raw source stream. Multi-Draw inset publication fails closed;
// this never alters the original D3D9 HRESULT or input path.
void observe_unavailable_game_draw(IDirect3DDevice9* gameDevice) noexcept;

// Called after each intercepted original D3D9 Draw/DrawIndexed returns.
// If it failed, invalidate its speculative native Draw and the entire
// same-Present batch without modifying the original D3D9 HRESULT/input.
void observe_failed_game_draw(IDirect3DDevice9* gameDevice) noexcept;

// Return true only for a successful D3D9 TARGET-only Clear of an auxiliary
// RT0, with a still-verified same-device main-backbuffer color seed. This
// color-only operation must not abort menu/car/race native Draw continuity.
// Unknown surface, depth or stencil state continues to fail closed.
bool preserve_offscreen_color_only_clear(IDirect3DDevice9* gameDevice,
                                         DWORD flags) noexcept;

// A game-authored Clear or successful RT0 switch after a native Draw divides
// a frame into incompatible surfaces. Discard the diagnostic batch; keep the
// original D3D9 Clear, Draw, Present and gamepad dispatch untouched.
void observe_scene_boundary(IDirect3DDevice9* gameDevice) noexcept;
// Preserve a complete live native game color batch across a verified depth-only
// Clear; return false to use unchanged D3D9 scene-boundary fallback.
bool observe_game_depth_clear(IDirect3DDevice9* gameDevice, DWORD count,
                              const D3DRECT* rects, DWORD flags, float z) noexcept;
// Called only after a successful original game Clear; preserve its full-RT
// background color for a same-device/backbuffer native Draw/DrawIndexed.
void observe_game_clear(IDirect3DDevice9* gameDevice, DWORD count,
                        const D3DRECT* rects, DWORD flags, D3DCOLOR color, float z) noexcept;

// Present draws an isolated inset only if native GPU pixels were produced.
// Failure never propagates to the original game Present.
void before_game_present(IDirect3DDevice9* gameDevice,
                         const RECT* sourceRect, const RGNDATA* dirtyRegion) noexcept;
// Called before the original D3D9 Reset; only its owning game device may
// retire the native frame and associated D3D11 resources.
void before_game_reset(IDirect3DDevice9* gameDevice) noexcept;
} // namespace outrun::vr::dx11::live_game_frame
