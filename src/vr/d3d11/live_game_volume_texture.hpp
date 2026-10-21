#pragma once
// Real D3D9 SM3 volume image: read all slices/mips from a CPU-readable
// game-created source and upload a bounded immutable native D3D11 Texture3D.
// No guessed pixels, and no GPU-only DEFAULT-pool readback.
#include "live_game_volume_budget.hpp"
#include "live_game_volume_pixels.hpp"
#include <d3d9.h>
#include <d3d11.h>
#include <wrl/client.h>
#include <cstdint>
#include <cstddef>
#include <vector>
namespace outrun::vr::dx11::live_game_frame::live_volume {
inline bool mirror_image(ID3D11Device* device, IDirect3DVolumeTexture9* source,
 bool srgb, bool chain, DWORD maxMip,
 Microsoft::WRL::ComPtr<ID3D11ShaderResourceView>& view, UINT& uploaded) noexcept {
    if (!device || !source) return false;
    const UINT sourceLevels = source->GetLevelCount();
    D3DVOLUME_DESC base{};
    if (!sourceLevels || sourceLevels > 10u ||
        FAILED(source->GetLevelDesc(0u, &base)) ||
        !((base.Pool == D3DPOOL_MANAGED || base.Pool == D3DPOOL_SYSTEMMEM) ||
          (base.Pool == D3DPOOL_DEFAULT && (base.Usage & D3DUSAGE_DYNAMIC))) ||
        (base.Usage & (D3DUSAGE_RENDERTARGET | D3DUSAGE_DEPTHSTENCIL |
                       D3DUSAGE_AUTOGENMIPMAP)) != 0u ||
        (chain && (source->GetLOD() != 0u || maxMip >= sourceLevels)) ||
        (!chain && maxMip != 0u)) return false;
    // Preserve actual game sample channels across 8-bit swizzles, dynamic
    // volume writes and half-float scalar/RGBA 3D shader sources.
    const PixelLayout layout =
        base.Format == D3DFMT_A8R8G8B8 ? PixelLayout::bgra8 :
        base.Format == D3DFMT_X8R8G8B8 ? PixelLayout::bgrx8 :
        base.Format == D3DFMT_A8B8G8R8 ? PixelLayout::rgba8 :
        base.Format == D3DFMT_X8B8G8R8 ? PixelLayout::rgbx8 :
        base.Format == D3DFMT_R16F ? PixelLayout::r16f :
        base.Format == D3DFMT_A16B16G16R16F ? PixelLayout::rgba16f :
                                           PixelLayout::unsupported;
    const UINT bpp = bytes_per_texel(layout);
    if (!bpp || (srgb && (layout == PixelLayout::r16f ||
                         layout == PixelLayout::rgba16f))) return false;
    const DXGI_FORMAT format = layout == PixelLayout::r16f ?
        DXGI_FORMAT_R16_FLOAT : layout == PixelLayout::rgba16f ?
        DXGI_FORMAT_R16G16B16A16_FLOAT : srgb ?
        DXGI_FORMAT_R8G8B8A8_UNORM_SRGB : DXGI_FORMAT_R8G8B8A8_UNORM;
    const UINT levels = chain ? sourceLevels : 1u;
    if (!bounded_chain_bytes(base.Width, base.Height, base.Depth, levels, bpp))
        return false;
    std::vector<std::vector<std::uint8_t>> copies(levels);
    std::vector<D3D11_SUBRESOURCE_DATA> subs(levels);
    for (UINT mip = 0u; mip < levels; ++mip) {
        D3DVOLUME_DESC desc{};
        if (FAILED(source->GetLevelDesc(mip, &desc)) ||
            desc.Format != base.Format || desc.Pool != base.Pool ||
            !matching_mip(base.Width, base.Height, base.Depth, mip,
                          desc.Width, desc.Height, desc.Depth)) return false;
        const UINT rowBytes = desc.Width * bpp;
        const UINT sliceBytes = rowBytes * desc.Height;
        D3DLOCKED_BOX locked{};
        if (FAILED(source->LockBox(mip, &locked, nullptr, D3DLOCK_READONLY)))
            return false;
        const bool readable = locked.pBits && locked.RowPitch > 0 &&
            locked.SlicePitch > 0 &&
            static_cast<std::uint64_t>(locked.RowPitch) >= rowBytes &&
            static_cast<std::uint64_t>(locked.SlicePitch) >=
                static_cast<std::uint64_t>(locked.RowPitch) * desc.Height;
        if (readable) {
            auto& pixels = copies[mip];
            pixels.resize(static_cast<std::size_t>(sliceBytes) * desc.Depth);
            for (UINT z = 0u; z < desc.Depth; ++z)
                for (UINT y = 0u; y < desc.Height; ++y) {
                    const auto* in = static_cast<const std::uint8_t*>(locked.pBits) +
                        static_cast<std::size_t>(locked.SlicePitch) * z +
                        static_cast<std::size_t>(locked.RowPitch) * y;
                    auto* out = pixels.data() + static_cast<std::size_t>(sliceBytes) * z +
                        static_cast<std::size_t>(rowBytes) * y;
                    (void)convert_row(in, out, desc.Width, layout);
                }
        }
        const HRESULT unlocked = source->UnlockBox(mip);
        if (!readable || FAILED(unlocked)) return false;
        subs[mip].pSysMem = copies[mip].data();
        subs[mip].SysMemPitch = rowBytes;
        subs[mip].SysMemSlicePitch = sliceBytes;
    }
    D3D11_TEXTURE3D_DESC desc{};
    desc.Width = base.Width;
    desc.Height = base.Height;
    desc.Depth = base.Depth;
    desc.MipLevels = levels;
    desc.Format = format;
    desc.Usage = D3D11_USAGE_IMMUTABLE;
    desc.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    Microsoft::WRL::ComPtr<ID3D11Texture3D> native;
    D3D11_SHADER_RESOURCE_VIEW_DESC srv{};
    srv.Format = desc.Format;
    srv.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE3D;
    srv.Texture3D.MostDetailedMip = 0u;
    srv.Texture3D.MipLevels = levels;
    if (FAILED(device->CreateTexture3D(&desc, subs.data(), native.GetAddressOf())) ||
        FAILED(device->CreateShaderResourceView(
            native.Get(), &srv, view.GetAddressOf()))) return false;
    uploaded = levels;
    return true;
}
} // namespace outrun::vr::dx11::live_game_frame::live_volume
