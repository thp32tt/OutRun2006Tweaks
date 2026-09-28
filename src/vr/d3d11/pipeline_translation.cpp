#include "pipeline_translation.hpp"

#include "state_translation.hpp"

namespace outrun::vr::dx11
{
    namespace
    {
        UINT8 translate_color_write_mask(DWORD value) noexcept
        {
            UINT8 mask = 0;
            if ((value & D3DCOLORWRITEENABLE_RED) != 0)
                mask |= D3D11_COLOR_WRITE_ENABLE_RED;
            if ((value & D3DCOLORWRITEENABLE_GREEN) != 0)
                mask |= D3D11_COLOR_WRITE_ENABLE_GREEN;
            if ((value & D3DCOLORWRITEENABLE_BLUE) != 0)
                mask |= D3D11_COLOR_WRITE_ENABLE_BLUE;
            if ((value & D3DCOLORWRITEENABLE_ALPHA) != 0)
                mask |= D3D11_COLOR_WRITE_ENABLE_ALPHA;
            return mask;
        }

        struct DeclTypeTranslation
        {
            DXGI_FORMAT format = DXGI_FORMAT_UNKNOWN;
            UINT byteSize = 0;
            bool exact = false;
        };

        DeclTypeTranslation translate_decl_type(BYTE type) noexcept
        {
            switch (static_cast<D3DDECLTYPE>(type))
            {
            case D3DDECLTYPE_FLOAT1:
                return { DXGI_FORMAT_R32_FLOAT, 4, true };
            case D3DDECLTYPE_FLOAT2:
                return { DXGI_FORMAT_R32G32_FLOAT, 8, true };
            case D3DDECLTYPE_FLOAT3:
                return { DXGI_FORMAT_R32G32B32_FLOAT, 12, true };
            case D3DDECLTYPE_FLOAT4:
                return { DXGI_FORMAT_R32G32B32A32_FLOAT, 16, true };
            case D3DDECLTYPE_D3DCOLOR:
                return { DXGI_FORMAT_B8G8R8A8_UNORM, 4, true };
            case D3DDECLTYPE_UBYTE4:
                return { DXGI_FORMAT_R8G8B8A8_UINT, 4, true };
            case D3DDECLTYPE_SHORT2:
                return { DXGI_FORMAT_R16G16_SINT, 4, true };
            case D3DDECLTYPE_SHORT4:
                return { DXGI_FORMAT_R16G16B16A16_SINT, 8, true };
            case D3DDECLTYPE_UBYTE4N:
                return { DXGI_FORMAT_R8G8B8A8_UNORM, 4, true };
            case D3DDECLTYPE_SHORT2N:
                return { DXGI_FORMAT_R16G16_SNORM, 4, true };
            case D3DDECLTYPE_SHORT4N:
                return { DXGI_FORMAT_R16G16B16A16_SNORM, 8, true };
            case D3DDECLTYPE_USHORT2N:
                return { DXGI_FORMAT_R16G16_UNORM, 4, true };
            case D3DDECLTYPE_USHORT4N:
                return { DXGI_FORMAT_R16G16B16A16_UNORM, 8, true };
            case D3DDECLTYPE_FLOAT16_2:
                return { DXGI_FORMAT_R16G16_FLOAT, 4, true };
            case D3DDECLTYPE_FLOAT16_4:
                return { DXGI_FORMAT_R16G16B16A16_FLOAT, 8, true };
            default:
                return {};
            }
        }

        const char* translate_decl_semantic(BYTE usage) noexcept
        {
            switch (static_cast<D3DDECLUSAGE>(usage))
            {
            case D3DDECLUSAGE_POSITION:     return "POSITION";
            case D3DDECLUSAGE_BLENDWEIGHT:  return "BLENDWEIGHT";
            case D3DDECLUSAGE_BLENDINDICES: return "BLENDINDICES";
            case D3DDECLUSAGE_NORMAL:       return "NORMAL";
            case D3DDECLUSAGE_PSIZE:        return "PSIZE";
            case D3DDECLUSAGE_TEXCOORD:     return "TEXCOORD";
            case D3DDECLUSAGE_TANGENT:      return "TANGENT";
            case D3DDECLUSAGE_BINORMAL:     return "BINORMAL";
            case D3DDECLUSAGE_POSITIONT:    return "POSITIONT";
            case D3DDECLUSAGE_COLOR:        return "COLOR";
            case D3DDECLUSAGE_FOG:          return "FOG";
            case D3DDECLUSAGE_DEPTH:        return "DEPTH";
            case D3DDECLUSAGE_SAMPLE:       return "SAMPLE";
            default:                        return nullptr;
            }
        }
    }

    PipelineTranslation translate_pipeline(
        const OutRunVR::DrawState::RenderStateSnapshot& source) noexcept
    {
        PipelineTranslation out{};

        out.blend.AlphaToCoverageEnable = FALSE;
        out.blend.IndependentBlendEnable = FALSE;
        auto& rt = out.blend.RenderTarget[0];
        rt.BlendEnable = source.alphaBlendEnable != FALSE;
        rt.RenderTargetWriteMask = translate_color_write_mask(
            source.colorWriteEnable);

        const auto srcBlend = translate_blend(
            static_cast<D3DBLEND>(source.srcBlend));
        const auto dstBlend = translate_blend(
            static_cast<D3DBLEND>(source.destBlend));
        const auto blendOp = translate_blend_op(
            static_cast<D3DBLENDOP>(source.blendOp));

        rt.SrcBlend = srcBlend.value;
        rt.DestBlend = dstBlend.value;
        rt.BlendOp = blendOp.value;
        rt.SrcBlendAlpha = srcBlend.value;
        rt.DestBlendAlpha = dstBlend.value;
        rt.BlendOpAlpha = blendOp.value;

        if (rt.BlendEnable &&
            (!srcBlend.exact || !dstBlend.exact || !blendOp.exact))
            out.unsupported |= PipelineUnsupportedBlend;

        if (source.separateAlphaBlendEnable != FALSE)
            out.unsupported |= PipelineUnsupportedSeparateAlphaBlend;

        if (source.zEnable == D3DZB_USEW)
            out.unsupported |= PipelineUnsupportedWBuffer;

        out.depth_stencil.DepthEnable =
            source.zEnable != D3DZB_FALSE;
        out.depth_stencil.DepthWriteMask =
            source.zWriteEnable != FALSE
            ? D3D11_DEPTH_WRITE_MASK_ALL
            : D3D11_DEPTH_WRITE_MASK_ZERO;

        const auto depthFunc = translate_compare(
            static_cast<D3DCMPFUNC>(source.zFunc));
        out.depth_stencil.DepthFunc = depthFunc.value;
        if (out.depth_stencil.DepthEnable && !depthFunc.exact)
            out.unsupported |= PipelineUnsupportedDepthCompare;

        // D3D9 stencil state is intentionally fail-closed until all front/back
        // op/function semantics are captured in the shared snapshot.
        out.depth_stencil.StencilEnable = source.stencilEnable != FALSE;
        out.depth_stencil.StencilReadMask = D3D11_DEFAULT_STENCIL_READ_MASK;
        out.depth_stencil.StencilWriteMask =
            static_cast<UINT8>(source.stencilWriteMask & 0xFFu);
        if (out.depth_stencil.StencilEnable)
            out.unsupported |= PipelineUnsupportedStencil;

        out.rasterizer.FillMode = D3D11_FILL_SOLID;
        switch (static_cast<D3DFILLMODE>(source.fillMode))
        {
        case D3DFILL_SOLID:
            out.rasterizer.FillMode = D3D11_FILL_SOLID;
            break;
        case D3DFILL_WIREFRAME:
            out.rasterizer.FillMode = D3D11_FILL_WIREFRAME;
            break;
        default:
            out.unsupported |= PipelineUnsupportedFillMode;
            break;
        }

        const auto cull = translate_cull(
            static_cast<D3DCULL>(source.cullMode));
        out.rasterizer.CullMode = cull.value;
        if (!cull.exact)
            out.unsupported |= PipelineUnsupportedCull;

        out.rasterizer.FrontCounterClockwise = FALSE;
        out.rasterizer.DepthClipEnable = TRUE;
        out.rasterizer.ScissorEnable =
            source.scissorTestEnable != FALSE;
        out.rasterizer.MultisampleEnable = FALSE;
        out.rasterizer.AntialiasedLineEnable = FALSE;

        if (source.alphaTestEnable != FALSE)
            out.unsupported |= PipelineUnsupportedAlphaTest;
        if (source.fogEnable != FALSE)
            out.unsupported |= PipelineUnsupportedFog;
        if (source.lighting != FALSE)
            out.unsupported |= PipelineUnsupportedLighting;
        if (source.sRGBWriteEnable != FALSE)
            out.unsupported |= PipelineUnsupportedSrgbWrite;
        if (!source.complete)
            out.unsupported |= PipelineUnsupportedIncompleteSnapshot;

        return out;
    }

    VertexInputLayoutTranslation translate_vertex_input_layout(
        const D3DVERTEXELEMENT9* source,
        UINT count,
        DWORD fvf,
        UINT stream0Stride) noexcept
    {
        VertexInputLayoutTranslation out{};
        if (!source || count == 0)
        {
            out.fvfPending = fvf != 0;
            return out;
        }

        out.declarationPath = true;
        bool terminatorSeen = false;
        for (UINT i = 0; i < count; ++i)
        {
            const auto& element = source[i];
            if (element.Stream == 0xFF &&
                element.Type == D3DDECLTYPE_UNUSED)
            {
                terminatorSeen = true;
                break;
            }

            if (out.elementCount >= out.elements.size() ||
                element.Stream != 0 ||
                element.Method != D3DDECLMETHOD_DEFAULT)
                return out;

            const auto type = translate_decl_type(element.Type);
            const char* semantic = translate_decl_semantic(element.Usage);
            if (!type.exact || !semantic || stream0Stride == 0 ||
                type.byteSize > stream0Stride ||
                element.Offset > stream0Stride - type.byteSize)
                return out;

            auto& desc = out.elements[out.elementCount++];
            desc.SemanticName = semantic;
            desc.SemanticIndex = element.UsageIndex;
            desc.Format = type.format;
            desc.InputSlot = 0;
            desc.AlignedByteOffset = element.Offset;
            desc.InputSlotClass = D3D11_INPUT_PER_VERTEX_DATA;
            desc.InstanceDataStepRate = 0;
        }

        out.exact = terminatorSeen && out.elementCount > 0;
        return out;
    }
}
