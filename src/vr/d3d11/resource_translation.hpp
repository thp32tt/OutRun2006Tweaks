#pragma once

#include <d3d9.h>
#include <dxgiformat.h>

namespace outrun::vr::dx11
{
    enum class ResourceRole
    {
        Color,
        Texture,
        DepthStencil,
        Index,
    };

    struct FormatTranslation
    {
        DXGI_FORMAT format = DXGI_FORMAT_UNKNOWN;
        bool exact = false;
    };

    // Conservative translation contract used by the passive R72/R73 census.
    // "exact" means the source format can be represented without inventing
    // channel/depth semantics. Unknown/inexact formats remain on the D3D9 path.
    [[nodiscard]] FormatTranslation translate_resource_format(
        D3DFORMAT source,
        ResourceRole role) noexcept;
}
