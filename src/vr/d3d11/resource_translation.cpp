#include "resource_translation.hpp"

namespace outrun::vr::dx11
{
    FormatTranslation translate_resource_format(
        D3DFORMAT source,
        ResourceRole role) noexcept
    {
        if (role == ResourceRole::Index)
        {
            switch (source)
            {
            case D3DFMT_INDEX16:
                return { DXGI_FORMAT_R16_UINT, true };
            case D3DFMT_INDEX32:
                return { DXGI_FORMAT_R32_UINT, true };
            default:
                return {};
            }
        }

        if (role == ResourceRole::DepthStencil)
        {
            switch (source)
            {
            case D3DFMT_D16:
                return { DXGI_FORMAT_D16_UNORM, true };
            case D3DFMT_D24S8:
                return { DXGI_FORMAT_D24_UNORM_S8_UINT, true };
            case D3DFMT_D32F_LOCKABLE:
                return { DXGI_FORMAT_D32_FLOAT, true };
            default:
                return {};
            }
        }

        switch (source)
        {
        case D3DFMT_A8R8G8B8:
            return { DXGI_FORMAT_B8G8R8A8_UNORM, true };
        case D3DFMT_X8R8G8B8:
            return { DXGI_FORMAT_B8G8R8X8_UNORM, true };
        case D3DFMT_A8B8G8R8:
            return { DXGI_FORMAT_R8G8B8A8_UNORM, true };
        case D3DFMT_R5G6B5:
            return { DXGI_FORMAT_B5G6R5_UNORM, true };
        case D3DFMT_A1R5G5B5:
            return { DXGI_FORMAT_B5G5R5A1_UNORM, true };
        case D3DFMT_A8:
            return { DXGI_FORMAT_A8_UNORM, true };
        case D3DFMT_DXT1:
            return { DXGI_FORMAT_BC1_UNORM, true };
        case D3DFMT_DXT3:
            return { DXGI_FORMAT_BC2_UNORM, true };
        case D3DFMT_DXT5:
            return { DXGI_FORMAT_BC3_UNORM, true };
        default:
            // Luminance/palettized/bump/floating formats deliberately remain
            // inexact until the matching shader/resource semantics are proven.
            return {};
        }
    }
}