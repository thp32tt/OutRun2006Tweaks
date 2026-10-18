#pragma once
#include "native_game_postpass_replay.hpp"
#include <d3d11.h>

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
} // namespace outrun::vr::dx11
