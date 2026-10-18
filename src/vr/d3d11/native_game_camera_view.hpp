#pragma once
#include "native_game_postpass_replay.hpp"
#include <d3d11.h>
#include <algorithm>
#include <cmath>
#include <limits>

namespace outrun::vr::dx11 {

// A game's camera RTV/DSV can address mip 1+ of a larger texture or one
// slice of a camera array. Clear/Draw must use the PHYSICAL view extent,
// never the allocation's base dimensions (which belong to a different mip).
// Refuse multi-slice views: the native offscreen replay draws one camera at
// a time and must not implicitly stamp the other stereo camera.
struct NativeGameCameraViewExtent {
    UINT width{}, height{}, mip{}, arraySlice{};
    bool valid{};
};

[[nodiscard]] inline NativeGameCameraViewExtent
native_game_camera_rtv_extent(
    const D3D11_TEXTURE2D_DESC& texture,
    const D3D11_RENDER_TARGET_VIEW_DESC& view) noexcept {
    UINT mip = 0u, slice = 0u;
    switch (view.ViewDimension) {
    case D3D11_RTV_DIMENSION_TEXTURE2D:
        mip = view.Texture2D.MipSlice;
        if (texture.ArraySize != 1u || texture.SampleDesc.Count != 1u) return {};
        break;
    case D3D11_RTV_DIMENSION_TEXTURE2DARRAY:
        mip = view.Texture2DArray.MipSlice;
        slice = view.Texture2DArray.FirstArraySlice;
        if (view.Texture2DArray.ArraySize != 1u ||
            texture.SampleDesc.Count != 1u) return {};
        break;
    case D3D11_RTV_DIMENSION_TEXTURE2DMS:
        if (texture.ArraySize != 1u || texture.SampleDesc.Count <= 1u) return {};
        break;
    case D3D11_RTV_DIMENSION_TEXTURE2DMSARRAY:
        slice = view.Texture2DMSArray.FirstArraySlice;
        if (view.Texture2DMSArray.ArraySize != 1u ||
            texture.SampleDesc.Count <= 1u) return {};
        break;
    default:
        return {};
    }
    const auto extent = native_game_postpass_mip_extent(
        texture.Width, texture.Height, texture.MipLevels, mip,
        texture.ArraySize, slice, texture.SampleDesc.Count);
    return {extent.width, extent.height, mip, slice, extent.valid};
}

[[nodiscard]] inline NativeGameCameraViewExtent
native_game_camera_dsv_extent(
    const D3D11_TEXTURE2D_DESC& texture,
    const D3D11_DEPTH_STENCIL_VIEW_DESC& view) noexcept {
    UINT mip = 0u, slice = 0u;
    switch (view.ViewDimension) {
    case D3D11_DSV_DIMENSION_TEXTURE2D:
        mip = view.Texture2D.MipSlice;
        if (texture.ArraySize != 1u || texture.SampleDesc.Count != 1u) return {};
        break;
    case D3D11_DSV_DIMENSION_TEXTURE2DARRAY:
        mip = view.Texture2DArray.MipSlice;
        slice = view.Texture2DArray.FirstArraySlice;
        if (view.Texture2DArray.ArraySize != 1u ||
            texture.SampleDesc.Count != 1u) return {};
        break;
    case D3D11_DSV_DIMENSION_TEXTURE2DMS:
        if (texture.ArraySize != 1u || texture.SampleDesc.Count <= 1u) return {};
        break;
    case D3D11_DSV_DIMENSION_TEXTURE2DMSARRAY:
        slice = view.Texture2DMSArray.FirstArraySlice;
        if (view.Texture2DMSArray.ArraySize != 1u ||
            texture.SampleDesc.Count <= 1u) return {};
        break;
    default:
        return {};
    }
    const auto extent = native_game_postpass_mip_extent(
        texture.Width, texture.Height, texture.MipLevels, mip,
        texture.ArraySize, slice, texture.SampleDesc.Count);
    return {extent.width, extent.height, mip, slice, extent.valid};
}
// The same physical camera view admission applies to BOTH live auxiliary
// Draw/DrawIndexed and Clear. A DSV pointing at another mip/array extent or
// MSAA configuration is not a compatible camera depth attachment, even when
// D3D11 accepted the texture allocation or an alternate view of the eye.
// A color-only camera may use no DSV; callers enforce this when one is bound.
[[nodiscard]] constexpr bool native_game_camera_depth_compatible(
    const NativeGameCameraViewExtent& color,
    const NativeGameCameraViewExtent& depth,
    UINT colorSamples, UINT depthSamples,
    UINT colorSampleQuality, UINT depthSampleQuality) noexcept {
    return color.valid && depth.valid &&
        color.width == depth.width && color.height == depth.height &&
        colorSamples != 0u && colorSamples == depthSamples &&
        colorSampleQuality == depthSampleQuality;
}

// Unlike a Clear, a native camera Draw with zero raster intersection must
// not advance the authentic geometry chronology: copying the untouched
// offscreen camera later could otherwise advertise a stale menu/car eye.
// Use the selected RTV mip/array PHYSICAL extent, not the allocation extent.
// Fractional viewports are valid for D3D11; compute intersections in double
// so a finite but very large float cannot overflow when adding its size.
[[nodiscard]] inline bool native_game_camera_draw_coverage(
    UINT width, UINT height, const D3D11_VIEWPORT& viewport,
    bool scissorEnabled, const D3D11_RECT* scissor) noexcept {
    if (!width || !height ||
        !std::isfinite(viewport.TopLeftX) ||
        !std::isfinite(viewport.TopLeftY) ||
        !std::isfinite(viewport.Width) ||
        !std::isfinite(viewport.Height) ||
        viewport.Width <= 0.f || viewport.Height <= 0.f)
        return false;
    const double left = (std::max)(0.0, double(viewport.TopLeftX));
    const double top = (std::max)(0.0, double(viewport.TopLeftY));
    const double right = (std::min)(double(width),
        double(viewport.TopLeftX) + double(viewport.Width));
    const double bottom = (std::min)(double(height),
        double(viewport.TopLeftY) + double(viewport.Height));
    if (right <= left || bottom <= top) return false;
    if (!scissorEnabled) return true;
    return scissor && double(scissor->right) > left &&
        double(scissor->bottom) > top &&
        double(scissor->left) < right &&
        double(scissor->top) < bottom;
}

// D3D9 Clear is clipped to the current game viewport and (when enabled)
// scissor as well as to explicit pRects. D3D11 ClearRTV/DSV and ClearView
// ignore RS clipping. Compute the exact single-camera GPU clear rectangle
// before choosing full RTV, D3D11.1 ClearView or the D3D11.0 raster route.
struct NativeGameCameraClearRegion {
    D3D11_RECT rect{};
    bool valid{}, empty{}, full{};
};

[[nodiscard]] inline NativeGameCameraClearRegion native_game_camera_clear_region(
    UINT width, UINT height, const D3D11_VIEWPORT& viewport,
    bool scissorEnabled, const D3D11_RECT* scissor,
    const D3D11_RECT* sourceRegion) noexcept {
    if (!width || !height ||
        width > static_cast<UINT>((std::numeric_limits<LONG>::max)()) ||
        height > static_cast<UINT>((std::numeric_limits<LONG>::max)()))
        return {};
    const auto wholePixel = [](float n) noexcept {
        return std::isfinite(n) && n >= 0.0f &&
            n < static_cast<float>((std::numeric_limits<LONG>::max)()) &&
            std::trunc(n) == n;
    };
    const float right = viewport.TopLeftX + viewport.Width;
    const float bottom = viewport.TopLeftY + viewport.Height;
    if (!wholePixel(viewport.TopLeftX) || !wholePixel(viewport.TopLeftY) ||
        !wholePixel(viewport.Width) || !wholePixel(viewport.Height) ||
        !wholePixel(right) || !wholePixel(bottom) ||
        viewport.Width <= 0.f || viewport.Height <= 0.f ||
        (scissorEnabled && (!scissor ||
            scissor->left >= scissor->right ||
            scissor->top >= scissor->bottom)))
        return {};
    const LONG w = static_cast<LONG>(width), h = static_cast<LONG>(height);
    const D3D11_RECT source = sourceRegion
        ? *sourceRegion : D3D11_RECT{0, 0, w, h};
    // A malformed D3D9 source rectangle is NOT silently repaired.
    if (source.left < 0 || source.top < 0 || source.right > w ||
        source.bottom > h || source.left >= source.right ||
        source.top >= source.bottom)
        return {};
    D3D11_RECT out{
        (std::max)(source.left, static_cast<LONG>(viewport.TopLeftX)),
        (std::max)(source.top, static_cast<LONG>(viewport.TopLeftY)),
        (std::min)(source.right, static_cast<LONG>(right)),
        (std::min)(source.bottom, static_cast<LONG>(bottom))};
    if (scissorEnabled) {
        out.left = (std::max)(out.left, scissor->left);
        out.top = (std::max)(out.top, scissor->top);
        out.right = (std::min)(out.right, scissor->right);
        out.bottom = (std::min)(out.bottom, scissor->bottom);
    }
    NativeGameCameraClearRegion result{};
    result.valid = true;
    result.empty = out.left >= out.right || out.top >= out.bottom;
    if (!result.empty) {
        result.rect = out;
        result.full = out.left == 0 && out.top == 0 &&
            out.right == w && out.bottom == h;
    }
    return result;
}
} // namespace outrun::vr::dx11
