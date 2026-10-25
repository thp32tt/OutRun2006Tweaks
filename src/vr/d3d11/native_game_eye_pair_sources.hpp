#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

namespace outrun::vr::dx11 {
// Accept only locally allocated native game color targets. A shared resource
// opened via a new transport view may alias a ring-owned output allocation
// even when the local COM identity no longer matches the original object.
[[nodiscard]] constexpr bool native_game_eye_local_render_target_admitted(
    std::uint32_t bindFlags, std::uint32_t miscFlags,
    std::uint32_t renderTargetFlag, std::uint32_t sharedFlags) noexcept {
    return renderTargetFlag != 0u &&
        (bindFlags & renderTargetFlag) == renderTargetFlag &&
        (miscFlags & sharedFlags) == 0u;
}
// Source eyes are local game-rendered RTs; the ring publishes single-sample
// shared textures. A multisampled stereo pair needs an explicit DX11 GPU
// resolve, never a CopyResource into a single-sample allocation. Reject
// mismatched eye sample modes and missing format resolve support before any
// GPU commands, leaving the acquired slot and original D3D9 frame intact.
// D3D9 camera postpasses may copy into a local GPU-only DEFAULT texture
// (BindFlags=0). Single-sample D3D11 CopyResource/CopySubresourceRegion
// accepts it as a source, unlike RTV-bound multisample ResolveSubresource.
// Shared, UAV-only and multisampled bindless sources must remain rejected.
// This is GPU source admission, never proof of a rendered stereo camera.
[[nodiscard]] constexpr bool native_game_eye_gpu_copy_only_source_admitted(
    std::uint32_t bindFlags, std::uint32_t miscFlags,
    std::uint32_t sampleCount, std::uint32_t sharedFlags) noexcept {
    return bindFlags == 0u && sampleCount == 1u &&
           (miscFlags & sharedFlags) == 0u;
}

 // Shader-readable, game-owned postpass camera images are commonly produced
 // by a GPU Copy/Resolve after the last real Draw, then sampled by a menu or
 // race compositor. They need not have RTV/UAV bind flags themselves. Accept
 // only a local, single-sample DEFAULT color source with the SRV flag alone:
 // the ring still requires exact eye extent/format, independent L/R slices,
 // producer device ownership, unique physical resource and a completed fence.
 [[nodiscard]] constexpr bool native_game_eye_gpu_shader_postpass_source_admitted(
     std::uint32_t bindFlags, std::uint32_t miscFlags,
     std::uint32_t sampleCount, std::uint32_t shaderResourceFlag,
     std::uint32_t sharedFlags) noexcept {
     return shaderResourceFlag != 0u && bindFlags == shaderResourceFlag &&
         sampleCount == 1u && (miscFlags & sharedFlags) == 0u;
 }
 static_assert(native_game_eye_gpu_shader_postpass_source_admitted(
     8u, 0u, 1u, 8u, 0x700u));
 static_assert(!native_game_eye_gpu_shader_postpass_source_admitted(
     8u, 0x200u, 1u, 8u, 0x700u));
 static_assert(!native_game_eye_gpu_shader_postpass_source_admitted(
     8u, 0u, 4u, 8u, 0x700u));
 static_assert(!native_game_eye_gpu_shader_postpass_source_admitted(
     8u | 0x80u, 0u, 1u, 8u, 0x700u));

// A compute-generated camera eye may never be RTV-bound: postprocessing
// writes an independent UAV-only texture (or UAV + SRV) and the native OpenXR
// handoff must still copy its complete mip-zero pixels on GPU. Admit only a
// single-sample, locally owned color source; depth/RTV combinations use their
// own established paths and shared allocations can alias published eyes.
[[nodiscard]] constexpr bool native_game_eye_gpu_compute_source_admitted(
    std::uint32_t bindFlags, std::uint32_t miscFlags,
    std::uint32_t sampleCount, std::uint32_t uavFlag,
    std::uint32_t renderTargetFlag, std::uint32_t depthFlag,
    std::uint32_t sharedFlags) noexcept {
    return uavFlag != 0u && (bindFlags & uavFlag) == uavFlag &&
        (bindFlags & (renderTargetFlag | depthFlag)) == 0u &&
        sampleCount == 1u && (miscFlags & sharedFlags) == 0u;
}
// Real native game color targets may use TYPELESS BGRA8 storage with a
// specific typed RTV. Permit GPU-only transfer to the matching typed XR ring
// when the currently bound game RTV proves BOTH the exact mip/array selection
// and color-space interpretation. An unbound/foreign view or SRGB -> UNORM
// reinterpretation must never silently alter game-camera gamma. MSAA typed
// resolves remain restricted to their exact original format.
[[nodiscard]] constexpr bool native_game_eye_format_transfer_admitted(
    std::uint32_t sourceStorage, std::uint32_t typedView,
    std::uint32_t ringFormat, std::uint32_t sampleCount,
    std::uint32_t bgraUnorm, std::uint32_t bgraSrgb,
    std::uint32_t bgraTypeless) noexcept {
    if (sourceStorage == ringFormat) return true;
    return sampleCount == 1u &&
        sourceStorage == bgraTypeless &&
        (ringFormat == bgraUnorm || ringFormat == bgraSrgb) &&
        typedView == ringFormat;
}
// Only a view containing the *selected* physical color subresource can
// attest to typeless storage. A different mip or array slice is not proof
// of the game-authored left/right camera's pixel interpretation.
[[nodiscard]] constexpr bool native_game_eye_rtv_subresource_matches(
    std::uint32_t selectedMip, std::uint32_t selectedSlice,
    std::uint32_t viewMip, std::uint32_t firstSlice,
    std::uint32_t sliceCount) noexcept {
    return sliceCount != 0u && selectedMip == viewMip &&
        selectedSlice >= firstSlice &&
        selectedSlice - firstSlice < sliceCount;
}
// A sequential L/R native camera can change OM output between real Draws.
// Only one EXACT game-bound typed RTV can attest to each physical eye's color
// interpretation, so retain that RTV until both GPU transfers are fenced.
[[nodiscard]] constexpr bool native_game_eye_captured_rtv_admitted(
    std::uint32_t storage, std::uint32_t observedFormat,
    std::uint32_t ringFormat, std::uint32_t sampleCount,
    bool sameAllocation, bool boundAtCapture,
    std::uint32_t selectedMip, std::uint32_t selectedSlice,
    std::uint32_t viewMip, std::uint32_t firstSlice,
    std::uint32_t viewSliceCount,
    std::uint32_t bgraUnorm, std::uint32_t bgraSrgb,
    std::uint32_t bgraTypeless) noexcept {
    return sameAllocation && boundAtCapture &&
        observedFormat == ringFormat && viewSliceCount == 1u &&
        native_game_eye_rtv_subresource_matches(
            selectedMip, selectedSlice, viewMip, firstSlice, viewSliceCount) &&
        native_game_eye_format_transfer_admitted(
            storage, observedFormat, ringFormat, sampleCount,
            bgraUnorm, bgraSrgb, bgraTypeless);
}
enum class NativeGameEyeTransfer : std::uint8_t { Reject, Copy, Resolve };
// Same-generation cumulative ACKs may retire frames with lower frame IDs.
// Disallow frame-ID reuse or a new ID already covered by a supplied ACK:
// otherwise a delayed ACK could retire newly published OpenXR eyes.
[[nodiscard]] constexpr bool native_game_eye_frame_id_admitted(
    std::uint64_t next, std::uint64_t highWatermark,
    std::uint64_t sameLifetimeAck) noexcept {
    return next != 0u && next > highWatermark && next > sameLifetimeAck;
}
[[nodiscard]] constexpr std::uint64_t native_game_eye_frame_high_watermark(
    std::uint64_t previous, std::uint64_t observed) noexcept {
    return previous < observed ? observed : previous;
}
// A slot with either eye GPU write already enqueued is not safely cancelable.
// This preserves original DX9Ex rendering and avoids aliasing late OpenXR eyes.
[[nodiscard]] constexpr bool native_game_eye_copy_cancelable(bool copyQueued) noexcept {
    return !copyQueued;
}
[[nodiscard]] constexpr NativeGameEyeTransfer native_game_eye_transfer(
    std::uint32_t leftSamples, std::uint32_t leftQuality,
    std::uint32_t rightSamples, std::uint32_t rightQuality,
    bool formatSupportsResolve) noexcept {
    if (leftSamples == 0u || leftSamples > 32u ||
        leftSamples != rightSamples ||
        leftQuality != rightQuality)
        return NativeGameEyeTransfer::Reject;
    if (leftSamples == 1u)
        return leftQuality == 0u
            ? NativeGameEyeTransfer::Copy
            : NativeGameEyeTransfer::Reject;
    return formatSupportsResolve
        ? NativeGameEyeTransfer::Resolve
        : NativeGameEyeTransfer::Reject;
}
// Compare canonical IUnknown identities, not interface pointers: two views of
// one eye or an in-flight ring output must never enter CopyResource as a source.
// Reject partially initialized rings rather than trust incomplete provenance.
template <std::size_t N>
[[nodiscard]] constexpr bool native_game_eye_pair_sources_admitted(
    std::uintptr_t left, std::uintptr_t right,
    const std::array<std::uintptr_t, N>& ringOwned) noexcept {
    if (!left || !right || left == right) return false;
    for (const auto identity : ringOwned)
        if (!identity || identity == left || identity == right) return false;
    return true;
}
} // namespace outrun::vr::dx11
