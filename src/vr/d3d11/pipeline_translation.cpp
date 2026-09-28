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

        bool fixed_function_argument_supported(DWORD value) noexcept
        {
            if ((value & ~static_cast<DWORD>(D3DTA_SELECTMASK)) != 0)
                return false;

            switch (value & D3DTA_SELECTMASK)
            {
            case D3DTA_DIFFUSE:
            case D3DTA_CURRENT:
            case D3DTA_TEXTURE:
                return true;
            default:
                return false;
            }
        }

        bool fixed_function_filter_supported(
            DWORD value, bool mip) noexcept
        {
            if (mip && value == D3DTEXF_NONE)
                return true;
            return value == D3DTEXF_POINT || value == D3DTEXF_LINEAR;
        }

        bool fixed_function_address_supported(DWORD value) noexcept
        {
            return value == D3DTADDRESS_WRAP ||
                   value == D3DTADDRESS_CLAMP;
        }

        void validate_fixed_function_op(
            DWORD op,
            DWORD arg1,
            DWORD arg2,
            std::uint32_t opBit,
            FixedFunctionTranslationReadiness& out) noexcept
        {
            bool useArg1 = false;
            bool useArg2 = false;
            switch (op)
            {
            case D3DTOP_SELECTARG1:
                useArg1 = true;
                break;
            case D3DTOP_SELECTARG2:
                useArg2 = true;
                break;
            case D3DTOP_MODULATE:
                useArg1 = true;
                useArg2 = true;
                break;
            default:
                out.unsupported |= opBit;
                return;
            }

            if ((useArg1 && !fixed_function_argument_supported(arg1)) ||
                (useArg2 && !fixed_function_argument_supported(arg2)))
                out.unsupported |= FixedFunctionUnsupportedArgument;
        }

        bool append_fvf_element(
            VertexInputLayoutTranslation& out,
            const char* semantic,
            UINT semanticIndex,
            DXGI_FORMAT format,
            UINT byteSize,
            UINT& offset,
            UINT stream0Stride) noexcept
        {
            if (!semantic || stream0Stride == 0 ||
                out.elementCount >= out.elements.size() ||
                byteSize > stream0Stride ||
                offset > stream0Stride - byteSize)
                return false;

            auto& desc = out.elements[out.elementCount++];
            desc.SemanticName = semantic;
            desc.SemanticIndex = semanticIndex;
            desc.Format = format;
            desc.InputSlot = 0;
            desc.AlignedByteOffset = offset;
            desc.InputSlotClass = D3D11_INPUT_PER_VERTEX_DATA;
            desc.InstanceDataStepRate = 0;
            offset += byteSize;
            return true;
        }

        bool translate_fvf_layout(
            DWORD fvf,
            UINT stream0Stride,
            VertexInputLayoutTranslation& out) noexcept
        {
            if (fvf == 0 || stream0Stride == 0)
                return false;

            // Deliberately exclude reserved/LASTBETA encodings. Position blend
            // weights/indices stay pending until their exact D3D9 semantics are
            // paired with the future shader-signature F21 gate.
            constexpr DWORD supportedFlags =
                D3DFVF_POSITION_MASK |
                D3DFVF_NORMAL |
                D3DFVF_PSIZE |
                D3DFVF_DIFFUSE |
                D3DFVF_SPECULAR |
                D3DFVF_TEXCOUNT_MASK |
                0xFFFF0000u;
            if ((fvf & ~supportedFlags) != 0)
                return false;

            UINT offset = 0;
            const DWORD position = fvf & D3DFVF_POSITION_MASK;
            switch (position)
            {
            case D3DFVF_XYZ:
                if (!append_fvf_element(
                        out, "POSITION", 0,
                        DXGI_FORMAT_R32G32B32_FLOAT, 12,
                        offset, stream0Stride))
                    return false;
                break;
            case D3DFVF_XYZRHW:
                if ((fvf & D3DFVF_NORMAL) != 0 ||
                    !append_fvf_element(
                        out, "POSITIONT", 0,
                        DXGI_FORMAT_R32G32B32A32_FLOAT, 16,
                        offset, stream0Stride))
                    return false;
                break;
            case D3DFVF_XYZW:
                if (!append_fvf_element(
                        out, "POSITION", 0,
                        DXGI_FORMAT_R32G32B32A32_FLOAT, 16,
                        offset, stream0Stride))
                    return false;
                break;
            default:
                // XYZB1..XYZB5 and any unknown position encoding remain
                // fail-closed until blend-weight/index semantics are modeled.
                return false;
            }

            if ((fvf & D3DFVF_NORMAL) != 0)
            {
                if (position != D3DFVF_XYZ ||
                    !append_fvf_element(
                        out, "NORMAL", 0,
                        DXGI_FORMAT_R32G32B32_FLOAT, 12,
                        offset, stream0Stride))
                    return false;
            }

            if ((fvf & D3DFVF_PSIZE) != 0 &&
                !append_fvf_element(
                    out, "PSIZE", 0,
                    DXGI_FORMAT_R32_FLOAT, 4,
                    offset, stream0Stride))
                return false;

            if ((fvf & D3DFVF_DIFFUSE) != 0 &&
                !append_fvf_element(
                    out, "COLOR", 0,
                    DXGI_FORMAT_B8G8R8A8_UNORM, 4,
                    offset, stream0Stride))
                return false;

            if ((fvf & D3DFVF_SPECULAR) != 0 &&
                !append_fvf_element(
                    out, "COLOR", 1,
                    DXGI_FORMAT_B8G8R8A8_UNORM, 4,
                    offset, stream0Stride))
                return false;

            const UINT texCount = static_cast<UINT>(
                (fvf & D3DFVF_TEXCOUNT_MASK) >> D3DFVF_TEXCOUNT_SHIFT);
            if (texCount > 8)
                return false;

            for (UINT index = 0; index < 8; ++index)
            {
                const DWORD mask = 0x3u << (16u + index * 2u);
                const DWORD sizeBits = fvf & mask;
                if (index >= texCount)
                {
                    if (sizeBits != 0)
                        return false;
                    continue;
                }

                DXGI_FORMAT format = DXGI_FORMAT_UNKNOWN;
                UINT byteSize = 0;
                if (sizeBits == D3DFVF_TEXCOORDSIZE1(index))
                {
                    format = DXGI_FORMAT_R32_FLOAT;
                    byteSize = 4;
                }
                else if (sizeBits == D3DFVF_TEXCOORDSIZE2(index))
                {
                    format = DXGI_FORMAT_R32G32_FLOAT;
                    byteSize = 8;
                }
                else if (sizeBits == D3DFVF_TEXCOORDSIZE3(index))
                {
                    format = DXGI_FORMAT_R32G32B32_FLOAT;
                    byteSize = 12;
                }
                else if (sizeBits == D3DFVF_TEXCOORDSIZE4(index))
                {
                    format = DXGI_FORMAT_R32G32B32A32_FLOAT;
                    byteSize = 16;
                }
                else
                    return false;

                if (!append_fvf_element(
                        out, "TEXCOORD", index, format, byteSize,
                        offset, stream0Stride))
                    return false;
            }

            return out.elementCount > 0;
        }
    }

    FixedFunctionTranslationReadiness translate_fixed_function_readiness(
        const std::array<FixedFunctionStageState, 8>& source,
        bool observationComplete) noexcept
    {
        FixedFunctionTranslationReadiness out{};
        if (!observationComplete)
            out.unsupported |=
                FixedFunctionUnsupportedIncompleteObservation;

        bool colorChainDisabled = false;
        for (std::size_t stageIndex = 0;
             stageIndex < source.size(); ++stageIndex)
        {
            const auto& stage = source[stageIndex];

            if (stage.colorOp == D3DTOP_DISABLE)
            {
                colorChainDisabled = true;
                if (stage.alphaOp != D3DTOP_DISABLE)
                    out.unsupported |= FixedFunctionUnsupportedStageChain;
                continue;
            }

            if (colorChainDisabled)
                out.unsupported |= FixedFunctionUnsupportedStageChain;

            ++out.activeStages;

            // Resource exactness currently observes source textures only on
            // stages 0 and 1. Higher active stages therefore remain
            // deliberately fail-closed even though R81 records their state.
            if (stageIndex >= 2)
                out.unsupported |=
                    FixedFunctionUnsupportedResourceStageCoverage;

            validate_fixed_function_op(
                stage.colorOp, stage.colorArg1, stage.colorArg2,
                FixedFunctionUnsupportedColorOp, out);
            validate_fixed_function_op(
                stage.alphaOp, stage.alphaArg1, stage.alphaArg2,
                FixedFunctionUnsupportedAlphaOp, out);

            const DWORD coord = stage.texCoordIndex & 0xFFFFu;
            const DWORD coordFlags = stage.texCoordIndex & 0xFFFF0000u;
            if (coordFlags != 0 || coord >= 8)
                out.unsupported |= FixedFunctionUnsupportedTexCoord;

            if (stage.textureTransformFlags != D3DTTFF_DISABLE)
                out.unsupported |=
                    FixedFunctionUnsupportedTextureTransform;

            if (!fixed_function_filter_supported(stage.minFilter, false) ||
                !fixed_function_filter_supported(stage.magFilter, false) ||
                !fixed_function_filter_supported(stage.mipFilter, true))
                out.unsupported |= FixedFunctionUnsupportedSamplerFilter;

            if (!fixed_function_address_supported(stage.addressU) ||
                !fixed_function_address_supported(stage.addressV))
                out.unsupported |= FixedFunctionUnsupportedSamplerAddress;
        }

        return out;
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
            out.fvfPath = fvf != 0;
            if (!out.fvfPath)
                return out;
            if (translate_fvf_layout(fvf, stream0Stride, out))
            {
                out.exact = true;
                return out;
            }
            out.fvfPending = true;
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
