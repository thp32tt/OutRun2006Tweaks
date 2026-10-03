#include "pipeline_translation.hpp"

#include <d3dcompiler.h>
#include <cmath>
#include <cstring>

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

        bool is_dual_source_blend_factor(D3DBLEND value) noexcept
        {
            return value == D3DBLEND_SRCCOLOR2 ||
                   value == D3DBLEND_INVSRCCOLOR2;
        }

        TranslationResult<D3D11_BLEND> translate_separate_alpha_blend_factor(
            D3DBLEND value) noexcept
        {
            // D3D9 blend factors are RGBA vectors. For the independent alpha
            // equation only the alpha component matters, while D3D11 forbids
            // *_COLOR enums in SrcBlendAlpha/DestBlendAlpha. Canonicalize
            // those vector-equivalent factors instead of rejecting an exact
            // D3D9 state. Legacy BOTH* shortcuts are valid only for
            // D3DRS_SRCBLEND, and SRC*COLOR2 has no defined alpha component,
            // so translate_blend() deliberately keeps those fail-closed.
            switch (value)
            {
            case D3DBLEND_SRCCOLOR:
            case D3DBLEND_SRCALPHA:
                return { D3D11_BLEND_SRC_ALPHA, true };
            case D3DBLEND_INVSRCCOLOR:
            case D3DBLEND_INVSRCALPHA:
                return { D3D11_BLEND_INV_SRC_ALPHA, true };
            case D3DBLEND_DESTCOLOR:
            case D3DBLEND_DESTALPHA:
                return { D3D11_BLEND_DEST_ALPHA, true };
            case D3DBLEND_INVDESTCOLOR:
            case D3DBLEND_INVDESTALPHA:
                return { D3D11_BLEND_INV_DEST_ALPHA, true };
            case D3DBLEND_SRCALPHASAT:
                // Its D3D9 alpha component is exactly 1, matching the D3D11
                // SRC_ALPHA_SAT alpha factor.
                return { D3D11_BLEND_SRC_ALPHA_SAT, true };
            default:
                return translate_blend(value);
            }
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
            // R178: D3DTA_COMPLEMENT and D3DTA_ALPHAREPLICATE are modifiers
            // on an otherwise supported argument selector. Preserve those
            // fixed-function semantics in generated HLSL while keeping every
            // unknown modifier bit fail-closed.
            constexpr DWORD supportedModifiers =
                static_cast<DWORD>(D3DTA_COMPLEMENT) |
                static_cast<DWORD>(D3DTA_ALPHAREPLICATE);
            const DWORD supportedBits =
                static_cast<DWORD>(D3DTA_SELECTMASK) | supportedModifiers;
            if ((value & ~supportedBits) != 0)
                return false;

            switch (value & D3DTA_SELECTMASK)
            {
            case D3DTA_DIFFUSE:
            case D3DTA_CURRENT:
            case D3DTA_TEXTURE:
            case D3DTA_TFACTOR:
            case D3DTA_CONSTANT:
            case D3DTA_TEMP:
            case D3DTA_SPECULAR:
                return true;
            default:
                return false;
            }
        }

        bool fixed_function_argument_uses_texture(DWORD value) noexcept
        {
            return (value & D3DTA_SELECTMASK) == D3DTA_TEXTURE;
        }

        bool fixed_function_op_uses_texture(
            DWORD op, DWORD arg0, DWORD arg1, DWORD arg2) noexcept
        {
            switch (op)
            {
            case D3DTOP_SELECTARG1:
            case D3DTOP_PREMODULATE:
                return fixed_function_argument_uses_texture(arg1);
            case D3DTOP_SELECTARG2:
                return fixed_function_argument_uses_texture(arg2);
            case D3DTOP_BLENDTEXTUREALPHA:
                // R186: the blend factor itself is this stage's sampled
                // texture alpha, even when neither argument selects texture.
                return true;
            case D3DTOP_BLENDTEXTUREALPHAPM:
                // R187: premultiplied texture-alpha blending still depends on
                // this stage's sampled alpha even when neither argument does.
                return true;
            case D3DTOP_MODULATE:
            case D3DTOP_MODULATE2X:
            case D3DTOP_MODULATE4X:
            case D3DTOP_ADD:
            case D3DTOP_ADDSIGNED:
            case D3DTOP_ADDSIGNED2X:
            case D3DTOP_ADDSMOOTH:
            case D3DTOP_BLENDDIFFUSEALPHA:
            case D3DTOP_BLENDCURRENTALPHA:
            case D3DTOP_BLENDFACTORALPHA:
            case D3DTOP_MODULATEALPHA_ADDCOLOR:
            case D3DTOP_MODULATECOLOR_ADDALPHA:
            case D3DTOP_MODULATEINVALPHA_ADDCOLOR:
            case D3DTOP_MODULATEINVCOLOR_ADDALPHA:
            case D3DTOP_DOTPRODUCT3:
            case D3DTOP_SUBTRACT:
                return fixed_function_argument_uses_texture(arg1) ||
                       fixed_function_argument_uses_texture(arg2);
            case D3DTOP_MULTIPLYADD:
            case D3DTOP_LERP:
                // R194/R196: ternary operations consume COLORARG0/ALPHAARG0
                // as the third source operand.
                return fixed_function_argument_uses_texture(arg0) ||
                       fixed_function_argument_uses_texture(arg1) ||
                       fixed_function_argument_uses_texture(arg2);
            default:
                return false;
            }
        }

        bool fixed_function_argument_uses_current(DWORD value) noexcept
        {
            return (value & D3DTA_SELECTMASK) == D3DTA_CURRENT;
        }

        bool fixed_function_op_uses_current_argument(
            DWORD op, DWORD arg0, DWORD arg1, DWORD arg2) noexcept
        {
            switch (op)
            {
            case D3DTOP_SELECTARG1:
            case D3DTOP_PREMODULATE:
                return fixed_function_argument_uses_current(arg1);
            case D3DTOP_SELECTARG2:
                return fixed_function_argument_uses_current(arg2);
            case D3DTOP_MODULATE:
            case D3DTOP_MODULATE2X:
            case D3DTOP_MODULATE4X:
            case D3DTOP_ADD:
            case D3DTOP_ADDSIGNED:
            case D3DTOP_ADDSIGNED2X:
            case D3DTOP_ADDSMOOTH:
            case D3DTOP_BLENDDIFFUSEALPHA:
            case D3DTOP_BLENDCURRENTALPHA:
            case D3DTOP_BLENDFACTORALPHA:
            case D3DTOP_BLENDTEXTUREALPHA:
            case D3DTOP_BLENDTEXTUREALPHAPM:
            case D3DTOP_MODULATEALPHA_ADDCOLOR:
            case D3DTOP_MODULATECOLOR_ADDALPHA:
            case D3DTOP_MODULATEINVALPHA_ADDCOLOR:
            case D3DTOP_MODULATEINVCOLOR_ADDALPHA:
            case D3DTOP_DOTPRODUCT3:
            case D3DTOP_SUBTRACT:
                return fixed_function_argument_uses_current(arg1) ||
                       fixed_function_argument_uses_current(arg2);
            case D3DTOP_MULTIPLYADD:
            case D3DTOP_LERP:
                return fixed_function_argument_uses_current(arg0) ||
                       fixed_function_argument_uses_current(arg1) ||
                       fixed_function_argument_uses_current(arg2);
            default:
                return false;
            }
        }

        bool fixed_function_stage_uses_texture(
            const FixedFunctionStageState& stage,
            bool premodulateColor,
            bool premodulateAlpha,
            bool texturePresent) noexcept
        {
            if (fixed_function_op_uses_texture(
                    stage.colorOp, stage.colorArg0,
                    stage.colorArg1, stage.colorArg2) ||
                fixed_function_op_uses_texture(
                    stage.alphaOp, stage.alphaArg0,
                    stage.alphaArg1, stage.alphaArg2))
                return true;

            // R195: PREMODULATE only changes CURRENT in the following stage
            // when that following stage actually has a texture bound.
            if (!texturePresent)
                return false;

            return
                (premodulateColor &&
                 fixed_function_op_uses_current_argument(
                     stage.colorOp, stage.colorArg0,
                     stage.colorArg1, stage.colorArg2)) ||
                (premodulateAlpha &&
                 fixed_function_op_uses_current_argument(
                     stage.alphaOp, stage.alphaArg0,
                     stage.alphaArg1, stage.alphaArg2));
        }

        std::string fixed_function_argument_expression(
            DWORD value,
            std::size_t stageIndex,
            const char* swizzle,
            DWORD textureFactor,
            DWORD stageConstant,
            bool premodulateCurrent = false)
        {
            const auto normalizedByte = [](DWORD color, unsigned shift)
            {
                return std::to_string((color >> shift) & 0xFFu) +
                       ".0f / 255.0f";
            };
            std::string base;
            switch (value & D3DTA_SELECTMASK)
            {
            case D3DTA_DIFFUSE:
                base = "input.diffuse";
                break;
            case D3DTA_CURRENT:
                base = premodulateCurrent
                    ? "(current * sampled" + std::to_string(stageIndex) + ")"
                    : "current";
                break;
            case D3DTA_TEMP:
                base = "temp";
                break;
            case D3DTA_TEXTURE:
                base = "sampled" + std::to_string(stageIndex);
                break;
            case D3DTA_TFACTOR:
                // D3DCOLOR is 0xAARRGGBB; materialize a normalized RGBA
                // constant so existing COMPLEMENT/ALPHAREPLICATE handling
                // remains identical to other fixed-function arguments.
                base = "float4(" + normalizedByte(textureFactor, 16) + ", " +
                       normalizedByte(textureFactor, 8) + ", " +
                       normalizedByte(textureFactor, 0) + ", " +
                       normalizedByte(textureFactor, 24) + ")";
                break;
            case D3DTA_CONSTANT:
                // R197: D3DTSS_CONSTANT is a per-stage 0xAARRGGBB color.
                // Materialize normalized RGBA so the existing argument
                // modifiers retain identical behavior.
                base = "float4(" + normalizedByte(stageConstant, 16) + ", " +
                       normalizedByte(stageConstant, 8) + ", " +
                       normalizedByte(stageConstant, 0) + ", " +
                       normalizedByte(stageConstant, 24) + ")";
                break;
            case D3DTA_SPECULAR:
                // R198: D3DTA_SPECULAR consumes interpolated vertex COLOR1.
                // The fixed-function VS prototype emits opaque white when the
                // FVF omits SPECULAR, matching the documented D3D9 default.
                base = "input.specular";
                break;
            default:
                return {};
            }
            // R178: ALPHAREPLICATE substitutes the source alpha for the
            // RGB argument. It is a no-op for the scalar alpha path. Apply
            // COMPLEMENT after selecting/replicating the source argument.
            if ((value & static_cast<DWORD>(D3DTA_ALPHAREPLICATE)) != 0 &&
                std::string(swizzle) == ".rgb")
                base += ".aaa";
            else
                base += swizzle;

            if ((value & static_cast<DWORD>(D3DTA_COMPLEMENT)) != 0)
                return "(1.0 - " + base + ")";
            return base;
        }

        std::string fixed_function_op_expression(
            DWORD op,
            DWORD arg0,
            DWORD arg1,
            DWORD arg2,
            std::size_t stageIndex,
            const char* swizzle,
            DWORD textureFactor,
            DWORD stageConstant,
            bool premodulateCurrent = false)
        {
            const auto first = fixed_function_argument_expression(
                arg1, stageIndex, swizzle, textureFactor, stageConstant,
                premodulateCurrent);
            const auto second = fixed_function_argument_expression(
                arg2, stageIndex, swizzle, textureFactor, stageConstant,
                premodulateCurrent);
            switch (op)
            {
            case D3DTOP_SELECTARG1:
            case D3DTOP_PREMODULATE:
                return first;
            case D3DTOP_SELECTARG2:
                return second;
            case D3DTOP_MODULATE:
                return first + " * " + second;
            case D3DTOP_MODULATE2X:
                // D3D9 MODULATE2X multiplies Arg1 and Arg2, then doubles
                // the component-wise result for brightening.
                return "(" + first + " * " + second + ") * 2.0";
            case D3DTOP_MODULATE4X:
                // D3D9 MODULATE4X multiplies Arg1 and Arg2, then scales
                // the component-wise result by four.
                return "(" + first + " * " + second + ") * 4.0";
            case D3DTOP_ADD:
                // D3D9 D3DTOP_ADD is component-wise Arg1 + Arg2.
                return first + " + " + second;
            case D3DTOP_ADDSIGNED:
                // R182: D3D9 ADDSIGNED applies a -0.5 bias after adding
                // Arg1 and Arg2 component-wise.
                return first + " + " + second + " - 0.5";
            case D3DTOP_ADDSIGNED2X:
                // R183: D3D9 ADDSIGNED2X applies the ADDSIGNED -0.5 bias,
                // then doubles the component-wise result.
                return "(" + first + " + " + second + " - 0.5) * 2.0";
            case D3DTOP_ADDSMOOTH:
                // R184: D3D9 ADDSMOOTH computes Arg1 + Arg2 * (1 - Arg1)
                // component-wise.
                return first + " + " + second + " * (1.0 - " + first + ")";
            case D3DTOP_BLENDDIFFUSEALPHA:
                // R185: D3D9 BLENDDIFFUSEALPHA linearly blends Arg1/Arg2
                // using the interpolated vertex diffuse alpha for both RGB
                // and alpha outputs.
                return first + " * input.diffuse.a + " + second +
                       " * (1.0 - input.diffuse.a)";
            case D3DTOP_BLENDCURRENTALPHA:
                // D3D9 BLENDCURRENTALPHA uses the previous texture-stage
                // result alpha as the interpolation factor.
                return first + " * current.a + " + second +
                       " * (1.0 - current.a)";
            case D3DTOP_BLENDTEXTUREALPHA:
            {
                // R186: D3D9 BLENDTEXTUREALPHA uses this stage's sampled
                // texture alpha as the scalar interpolation factor.
                const auto textureAlpha =
                    "sampled" + std::to_string(stageIndex) + ".a";
                return first + " * " + textureAlpha + " + " + second +
                       " * (1.0 - " + textureAlpha + ")";
            }
            case D3DTOP_BLENDFACTORALPHA:
            {
                // D3D9 BLENDFACTORALPHA linearly blends Arg1/Arg2 using
                // D3DRS_TEXTUREFACTOR's alpha byte as one global scalar.
                const auto factorAlpha = std::to_string(
                    (textureFactor >> 24) & 0xFFu) + ".0f / 255.0f";
                return first + " * (" + factorAlpha + ") + " + second +
                       " * (1.0 - (" + factorAlpha + "))";
            }
            case D3DTOP_BLENDTEXTUREALPHAPM:
            {
                // R187: D3D9 BLENDTEXTUREALPHAPM assumes Arg1 is already
                // premultiplied by this stage's texture alpha.
                const auto textureAlpha =
                    "sampled" + std::to_string(stageIndex) + ".a";
                return first + " + " + second +
                       " * (1.0 - " + textureAlpha + ")";
            }
            case D3DTOP_MODULATEALPHA_ADDCOLOR:
            {
                // Direct3D 9 defines this COLOROP-only operation as
                // Arg1.rgb + Arg1.a * Arg2.rgb.
                const auto firstAlpha = fixed_function_argument_expression(
                    arg1, stageIndex, ".a", textureFactor, stageConstant,
                    premodulateCurrent);
                return first + " + " + firstAlpha + " * " + second;
            }
            case D3DTOP_MODULATECOLOR_ADDALPHA:
            {
                // R188: D3D9 defines this COLOROP-only operation as
                // Arg1.rgb * Arg2.rgb + Arg1.a, with Arg1.a replicated
                // across the RGB result.
                const auto firstAlpha = fixed_function_argument_expression(
                    arg1, stageIndex, ".a", textureFactor, stageConstant,
                    premodulateCurrent);
                return first + " * " + second + " + " + firstAlpha;
            }
            case D3DTOP_MODULATEINVALPHA_ADDCOLOR:
            {
                // R189: D3D9 defines this COLOROP-only operation as
                // Arg1.rgb + (1 - Arg1.a) * Arg2.rgb.
                const auto firstAlpha = fixed_function_argument_expression(
                    arg1, stageIndex, ".a", textureFactor, stageConstant,
                    premodulateCurrent);
                return first + " + (1.0 - " + firstAlpha + ") * " + second;
            }
            case D3DTOP_MODULATEINVCOLOR_ADDALPHA:
            {
                // R190: D3D9 defines this COLOROP-only operation as
                // (1 - Arg1.rgb) * Arg2.rgb + Arg1.a.
                const auto firstAlpha = fixed_function_argument_expression(
                    arg1, stageIndex, ".a", textureFactor, stageConstant,
                    premodulateCurrent);
                return "(1.0 - " + first + ") * " + second + " + " +
                       firstAlpha;
            }
            case D3DTOP_SUBTRACT:
                // R177: D3D9 defines SUBTRACT as component-wise Arg1 - Arg2.
                return first + " - " + second;
            case D3DTOP_DOTPRODUCT3:
            {
                // R193: D3D9 DOTPRODUCT3 interprets both RGB arguments as
                // signed values (2*x-1), computes their three-component dot
                // product, and replicates the scalar through the destination.
                const auto dotFirst = fixed_function_argument_expression(
                    arg1, stageIndex, ".rgb", textureFactor, stageConstant,
                    premodulateCurrent);
                const auto dotSecond = fixed_function_argument_expression(
                    arg2, stageIndex, ".rgb", textureFactor, stageConstant,
                    premodulateCurrent);
                return "dot((" + dotFirst + " * 2.0 - 1.0), (" +
                       dotSecond + " * 2.0 - 1.0))";
            }
            case D3DTOP_MULTIPLYADD:
            {
                // R194: Direct3D 9 defines MULTIPLYADD as
                // Arg1 + Arg2 * Arg0, where ARG0 is the third stage source.
                const auto third = fixed_function_argument_expression(
                    arg0, stageIndex, swizzle, textureFactor, stageConstant,
                    premodulateCurrent);
                return first + " + " + second + " * " + third;
            }
            case D3DTOP_LERP:
            {
                // R196: Direct3D 9 linearly interpolates Arg1 toward Arg2
                // using ARG0 as the per-component proportion.
                const auto proportion = fixed_function_argument_expression(
                    arg0, stageIndex, swizzle, textureFactor, stageConstant,
                    premodulateCurrent);
                return first + " * " + proportion + " + " + second +
                       " * (1.0 - " + proportion + ")";
            }
            default:
                return {};
            }
        }

        bool fixed_function_alpha_test_supported(
            DWORD value) noexcept
        {
            switch (static_cast<D3DCMPFUNC>(value))
            {
            case D3DCMP_NEVER:
            case D3DCMP_LESS:
            case D3DCMP_EQUAL:
            case D3DCMP_LESSEQUAL:
            case D3DCMP_GREATER:
            case D3DCMP_NOTEQUAL:
            case D3DCMP_GREATEREQUAL:
            case D3DCMP_ALWAYS:
                return true;
            default:
                return false;
            }
        }

        const char* fixed_function_alpha_compare_operator(
            DWORD value) noexcept
        {
            switch (static_cast<D3DCMPFUNC>(value))
            {
            case D3DCMP_LESS:         return "<";
            case D3DCMP_EQUAL:        return "==";
            case D3DCMP_LESSEQUAL:    return "<=";
            case D3DCMP_GREATER:      return ">";
            case D3DCMP_NOTEQUAL:     return "!=";
            case D3DCMP_GREATEREQUAL: return ">=";
            default:                  return nullptr;
            }
        }

        std::uint64_t hash_bytes(
            const void* data, std::size_t size) noexcept
        {
            std::uint64_t hash = 1469598103934665603ull;
            const auto* bytes = static_cast<const unsigned char*>(data);
            for (std::size_t index = 0; index < size; ++index)
            {
                hash ^= static_cast<std::uint64_t>(bytes[index]);
                hash *= 1099511628211ull;
            }
            return hash;
        }

        std::uint64_t hash_shader_source(const std::string& source) noexcept
        {
            return hash_bytes(source.data(), source.size());
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
            // R159/R160: these D3D9 modes have direct D3D11 coordinate
            // semantics. BORDER is exact only because R160 now captures the
            // corresponding D3DSAMP_BORDERCOLOR in FixedFunctionStageState.
            return value == D3DTADDRESS_WRAP ||
                   value == D3DTADDRESS_MIRROR ||
                   value == D3DTADDRESS_CLAMP ||
                   value == D3DTADDRESS_BORDER ||
                   value == D3DTADDRESS_MIRRORONCE;
        }

        bool translate_fixed_function_sampler_lod(
            const FixedFunctionStageState& source,
            D3D11_SAMPLER_DESC& desc) noexcept
        {
            float mipLodBias = 0.0f;
            static_assert(
                sizeof(mipLodBias) == sizeof(source.mipLodBiasBits));
            std::memcpy(
                &mipLodBias, &source.mipLodBiasBits, sizeof(mipLodBias));

            // D3D9 stores MIPMAPLODBIAS as raw float bits and MAXMIPLEVEL as
            // the index of the most-detailed mip allowed. D3D11 expresses
            // those same semantics as MipLODBias and the MinLOD clamp.
            if (!std::isfinite(mipLodBias) ||
                mipLodBias < D3D11_MIP_LOD_BIAS_MIN ||
                mipLodBias > D3D11_MIP_LOD_BIAS_MAX ||
                source.maxMipLevel >= D3D11_REQ_MIP_LEVELS)
                return false;

            // D3DTEXF_NONE disables mipmapping. Keep the prior exact
            // single-level contract and fail closed if non-default D3D9 LOD
            // state is present in that mode rather than guessing how a driver
            // would combine an ignored bias/MAXMIPLEVEL with no mip selection.
            if (source.mipFilter == D3DTEXF_NONE)
            {
                if (source.mipLodBiasBits != 0u ||
                    source.maxMipLevel != 0u)
                    return false;
                desc.MipLODBias = 0.0f;
                desc.MinLOD = 0.0f;
                desc.MaxLOD = 0.0f;
                return true;
            }

            desc.MipLODBias = mipLodBias;
            desc.MinLOD = static_cast<float>(source.maxMipLevel);
            desc.MaxLOD = D3D11_FLOAT32_MAX;
            return true;
        }

        D3D11_FILTER translate_fixed_function_filter(
            DWORD minFilter,
            DWORD magFilter,
            DWORD mipFilter) noexcept
        {
            const unsigned key =
                (minFilter == D3DTEXF_LINEAR ? 4u : 0u) |
                (magFilter == D3DTEXF_LINEAR ? 2u : 0u) |
                (mipFilter == D3DTEXF_LINEAR ? 1u : 0u);
            switch (key)
            {
            case 0u: return D3D11_FILTER_MIN_MAG_MIP_POINT;
            case 1u: return D3D11_FILTER_MIN_MAG_POINT_MIP_LINEAR;
            case 2u: return D3D11_FILTER_MIN_POINT_MAG_LINEAR_MIP_POINT;
            case 3u: return D3D11_FILTER_MIN_POINT_MAG_MIP_LINEAR;
            case 4u: return D3D11_FILTER_MIN_LINEAR_MAG_MIP_POINT;
            case 5u: return D3D11_FILTER_MIN_LINEAR_MAG_POINT_MIP_LINEAR;
            case 6u: return D3D11_FILTER_MIN_MAG_LINEAR_MIP_POINT;
            case 7u: return D3D11_FILTER_MIN_MAG_MIP_LINEAR;
            default: return D3D11_FILTER_MIN_MAG_MIP_POINT;
            }
        }

        D3D11_TEXTURE_ADDRESS_MODE translate_fixed_function_address(
            DWORD value) noexcept
        {
            switch (value)
            {
            case D3DTADDRESS_MIRROR:
                return D3D11_TEXTURE_ADDRESS_MIRROR;
            case D3DTADDRESS_CLAMP:
                return D3D11_TEXTURE_ADDRESS_CLAMP;
            case D3DTADDRESS_BORDER:
                return D3D11_TEXTURE_ADDRESS_BORDER;
            case D3DTADDRESS_MIRRORONCE:
                return D3D11_TEXTURE_ADDRESS_MIRROR_ONCE;
            case D3DTADDRESS_WRAP:
            default:
                return D3D11_TEXTURE_ADDRESS_WRAP;
            }
        }

        void validate_fixed_function_op(
            DWORD op,
            DWORD arg0,
            DWORD arg1,
            DWORD arg2,
            std::uint32_t opBit,
            bool alphaOperation,
            FixedFunctionTranslationReadiness& out) noexcept
        {
            bool useArg0 = false;
            bool useArg1 = false;
            bool useArg2 = false;
            switch (op)
            {
            case D3DTOP_SELECTARG1:
            case D3DTOP_PREMODULATE:
                useArg1 = true;
                break;
            case D3DTOP_SELECTARG2:
                useArg2 = true;
                break;
            case D3DTOP_MODULATE:
            case D3DTOP_MODULATE2X:
            case D3DTOP_MODULATE4X:
            case D3DTOP_ADD:
            case D3DTOP_ADDSIGNED:
            case D3DTOP_ADDSIGNED2X:
            case D3DTOP_ADDSMOOTH:
            case D3DTOP_BLENDDIFFUSEALPHA:
            case D3DTOP_BLENDCURRENTALPHA:
            case D3DTOP_BLENDFACTORALPHA:
            case D3DTOP_BLENDTEXTUREALPHA:
            case D3DTOP_BLENDTEXTUREALPHAPM:
            case D3DTOP_DOTPRODUCT3:
            case D3DTOP_SUBTRACT:
                useArg1 = true;
                useArg2 = true;
                break;
            case D3DTOP_MULTIPLYADD:
            case D3DTOP_LERP:
                useArg0 = true;
                useArg1 = true;
                useArg2 = true;
                break;
            case D3DTOP_MODULATEALPHA_ADDCOLOR:
            case D3DTOP_MODULATECOLOR_ADDALPHA:
            case D3DTOP_MODULATEINVALPHA_ADDCOLOR:
            case D3DTOP_MODULATEINVCOLOR_ADDALPHA:
                // These Direct3D 9 operations are valid only for COLOROP.
                if (alphaOperation)
                {
                    out.unsupported |= opBit;
                    return;
                }
                useArg1 = true;
                useArg2 = true;
                break;
            default:
                out.unsupported |= opBit;
                return;
            }

            if ((useArg0 && !fixed_function_argument_supported(arg0)) ||
                (useArg1 && !fixed_function_argument_supported(arg1)) ||
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

        bool append_fvf_blend_weights(
            VertexInputLayoutTranslation& out,
            UINT count,
            UINT& offset,
            UINT stream0Stride) noexcept
        {
            switch (count)
            {
            case 0:
                return true;
            case 1:
                return append_fvf_element(
                    out, "BLENDWEIGHT", 0,
                    DXGI_FORMAT_R32_FLOAT, 4,
                    offset, stream0Stride);
            case 2:
                return append_fvf_element(
                    out, "BLENDWEIGHT", 0,
                    DXGI_FORMAT_R32G32_FLOAT, 8,
                    offset, stream0Stride);
            case 3:
                return append_fvf_element(
                    out, "BLENDWEIGHT", 0,
                    DXGI_FORMAT_R32G32B32_FLOAT, 12,
                    offset, stream0Stride);
            case 4:
                return append_fvf_element(
                    out, "BLENDWEIGHT", 0,
                    DXGI_FORMAT_R32G32B32A32_FLOAT, 16,
                    offset, stream0Stride);
            case 5:
                return append_fvf_element(
                           out, "BLENDWEIGHT", 0,
                           DXGI_FORMAT_R32G32B32A32_FLOAT, 16,
                           offset, stream0Stride) &&
                       append_fvf_element(
                           out, "BLENDWEIGHT", 1,
                           DXGI_FORMAT_R32_FLOAT, 4,
                           offset, stream0Stride);
            default:
                return false;
            }
        }

        bool translate_fvf_layout(
            DWORD fvf,
            UINT stream0Stride,
            VertexInputLayoutTranslation& out) noexcept
        {
            if (fvf == 0 || stream0Stride == 0)
                return false;

            // R88 treats FVF blend weights/indices as descriptor-level input
            // layout semantics only. Shader use remains an independent F21
            // gate, so this does not activate native DX11 drawing.
            constexpr DWORD supportedFlags =
                D3DFVF_POSITION_MASK |
                D3DFVF_NORMAL |
                D3DFVF_PSIZE |
                D3DFVF_DIFFUSE |
                D3DFVF_SPECULAR |
                D3DFVF_TEXCOUNT_MASK |
                D3DFVF_LASTBETA_UBYTE4 |
                D3DFVF_LASTBETA_D3DCOLOR |
                0xFFFF0000u;
            if ((fvf & ~supportedFlags) != 0)
                return false;

            UINT offset = 0;
            UINT betaCount = 0;
            bool blendPosition = false;
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
            case D3DFVF_XYZB1:
                betaCount = 1;
                blendPosition = true;
                break;
            case D3DFVF_XYZB2:
                betaCount = 2;
                blendPosition = true;
                break;
            case D3DFVF_XYZB3:
                betaCount = 3;
                blendPosition = true;
                break;
            case D3DFVF_XYZB4:
                betaCount = 4;
                blendPosition = true;
                break;
            case D3DFVF_XYZB5:
                betaCount = 5;
                blendPosition = true;
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
                return false;
            }

            const bool lastBetaUbyte4 =
                (fvf & D3DFVF_LASTBETA_UBYTE4) != 0;
            const bool lastBetaD3DColor =
                (fvf & D3DFVF_LASTBETA_D3DCOLOR) != 0;
            if (lastBetaUbyte4 && lastBetaD3DColor)
                return false;

            if (blendPosition)
            {
                if (!append_fvf_element(
                        out, "POSITION", 0,
                        DXGI_FORMAT_R32G32B32_FLOAT, 12,
                        offset, stream0Stride))
                    return false;

                const bool hasBlendIndices =
                    lastBetaUbyte4 || lastBetaD3DColor;
                const UINT blendWeightCount =
                    betaCount - (hasBlendIndices ? 1u : 0u);
                if (!append_fvf_blend_weights(
                        out, blendWeightCount, offset, stream0Stride))
                    return false;

                if (hasBlendIndices)
                {
                    const DXGI_FORMAT indexFormat =
                        lastBetaUbyte4
                        ? DXGI_FORMAT_R8G8B8A8_UINT
                        : DXGI_FORMAT_B8G8R8A8_UNORM;
                    if (!append_fvf_element(
                            out, "BLENDINDICES", 0,
                            indexFormat, 4,
                            offset, stream0Stride))
                        return false;
                }
            }
            else if (lastBetaUbyte4 || lastBetaD3DColor)
            {
                return false;
            }

            if ((fvf & D3DFVF_NORMAL) != 0)
            {
                if ((position != D3DFVF_XYZ && !blendPosition) ||
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

    FixedFunctionSamplerTranslation translate_fixed_function_sampler(
        const FixedFunctionStageState& source) noexcept
    {
        FixedFunctionSamplerTranslation out{};
        if (!fixed_function_filter_supported(source.minFilter, false) ||
            !fixed_function_filter_supported(source.magFilter, false) ||
            !fixed_function_filter_supported(source.mipFilter, true) ||
            !translate_fixed_function_sampler_lod(source, out.desc) ||
            source.srgbTexture != FALSE ||
            !fixed_function_address_supported(source.addressU) ||
            !fixed_function_address_supported(source.addressV))
            return out;

        out.desc.Filter = translate_fixed_function_filter(
            source.minFilter, source.magFilter, source.mipFilter);
        out.desc.AddressU = translate_fixed_function_address(source.addressU);
        out.desc.AddressV = translate_fixed_function_address(source.addressV);
        // R84 currently accepts Texture2D only, so W is not sampled. Keep a
        // deterministic WRAP value rather than inventing uncaptured D3D9 state.
        out.desc.AddressW = D3D11_TEXTURE_ADDRESS_WRAP;
        out.desc.MaxAnisotropy = 1;
        out.desc.ComparisonFunc = D3D11_COMPARISON_NEVER;
        // D3D9 D3DCOLOR is AARRGGBB; D3D11 expects RGBA float channels.
        constexpr float kInv255 = 1.0f / 255.0f;
        out.desc.BorderColor[0] =
            static_cast<float>((source.borderColor >> 16) & 0xFFu) * kInv255;
        out.desc.BorderColor[1] =
            static_cast<float>((source.borderColor >> 8) & 0xFFu) * kInv255;
        out.desc.BorderColor[2] =
            static_cast<float>(source.borderColor & 0xFFu) * kInv255;
        out.desc.BorderColor[3] =
            static_cast<float>((source.borderColor >> 24) & 0xFFu) * kInv255;
        out.exact = true;
        return out;
    }

    FixedFunctionTranslationReadiness translate_fixed_function_readiness(
        const std::array<FixedFunctionStageState, 8>& source,
        bool observationComplete,
        std::uint8_t textureResourcePresentMask,
        std::uint8_t textureResourceExactMask) noexcept
    {
        FixedFunctionTranslationReadiness out{};
        if (!observationComplete)
            out.unsupported |=
                FixedFunctionUnsupportedIncompleteObservation;

        bool colorChainDisabled = false;
        bool premodulateColor = false;
        bool premodulateAlpha = false;
        for (std::size_t stageIndex = 0;
             stageIndex < source.size(); ++stageIndex)
        {
            const auto& stage = source[stageIndex];

            if (stage.colorOp == D3DTOP_DISABLE)
            {
                colorChainDisabled = true;
                premodulateColor = false;
                premodulateAlpha = false;
                if (stage.alphaOp != D3DTOP_DISABLE)
                    out.unsupported |= FixedFunctionUnsupportedStageChain;
                continue;
            }

            if (colorChainDisabled)
                out.unsupported |= FixedFunctionUnsupportedStageChain;

            ++out.activeStages;

            validate_fixed_function_op(
                stage.colorOp, stage.colorArg0, stage.colorArg1, stage.colorArg2,
                FixedFunctionUnsupportedColorOp, false, out);
            validate_fixed_function_op(
                stage.alphaOp, stage.alphaArg0, stage.alphaArg1, stage.alphaArg2,
                FixedFunctionUnsupportedAlphaOp, true, out);

            // R201: D3D9 defines the TEMP register's device default as
            // transparent black, so TEMP is readable before any stage writes
            // it. RESULTARG itself remains exact only for CURRENT or TEMP.
            if (stage.resultArg != D3DTA_CURRENT &&
                stage.resultArg != D3DTA_TEMP)
                out.unsupported |= FixedFunctionUnsupportedResultArg;

            const auto stageBit = static_cast<std::uint8_t>(
                1u << static_cast<unsigned>(stageIndex));
            const bool texturePresent =
                (textureResourcePresentMask & stageBit) != 0;
            const bool usesTexture = fixed_function_stage_uses_texture(
                stage, premodulateColor, premodulateAlpha, texturePresent);
            if (usesTexture &&
                (((textureResourcePresentMask & stageBit) == 0) ||
                 ((textureResourceExactMask & stageBit) == 0)))
                out.unsupported |=
                    FixedFunctionUnsupportedResourceStageCoverage;

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

            D3D11_SAMPLER_DESC lodDesc{};
            if (!translate_fixed_function_sampler_lod(stage, lodDesc))
                out.unsupported |= FixedFunctionUnsupportedSamplerLod;

            if (stage.srgbTexture != FALSE)
                out.unsupported |= FixedFunctionUnsupportedSamplerSrgb;

            premodulateColor = stage.colorOp == D3DTOP_PREMODULATE;
            premodulateAlpha = stage.alphaOp == D3DTOP_PREMODULATE;
        }

        return out;
    }

    FixedFunctionPixelShaderPrototype
    generate_fixed_function_pixel_shader_prototype(
        const std::array<FixedFunctionStageState, 8>& source,
        bool observationComplete,
        std::uint8_t textureResourcePresentMask,
        std::uint8_t textureResourceExactMask,
        const std::array<D3DRESOURCETYPE, 8>& textureResourceTypes,
        FixedFunctionAlphaTestState alphaTest,
        DWORD textureFactor)
    {
        FixedFunctionPixelShaderPrototype out{};
        const auto readiness = translate_fixed_function_readiness(
            source,
            observationComplete,
            textureResourcePresentMask,
            textureResourceExactMask);
        out.activeStages = readiness.activeStages;
        if (!readiness.exact())
        {
            out.unsupported |=
                FixedFunctionShaderPrototypeUnsupportedNotReady;
            return out;
        }

        if (!alphaTest.observationComplete ||
            (alphaTest.enabled != FALSE &&
             !fixed_function_alpha_test_supported(alphaTest.function)))
        {
            out.unsupported |=
                FixedFunctionShaderPrototypeUnsupportedAlphaTestState;
            return out;
        }

        bool premodulateColor = false;
        bool premodulateAlpha = false;
        for (std::size_t stageIndex = 0;
             stageIndex < source.size(); ++stageIndex)
        {
            const auto& stage = source[stageIndex];
            if (stage.colorOp == D3DTOP_DISABLE)
                break;

            const auto stageBit = static_cast<std::uint8_t>(
                1u << static_cast<unsigned>(stageIndex));
            const bool texturePresent =
                (textureResourcePresentMask & stageBit) != 0;
            const bool usesTexture = fixed_function_stage_uses_texture(
                stage, premodulateColor, premodulateAlpha, texturePresent);
            if (usesTexture &&
                textureResourceTypes[stageIndex] != D3DRTYPE_TEXTURE)
            {
                out.unsupported |=
                    FixedFunctionShaderPrototypeUnsupportedResourceType;
                return out;
            }

            premodulateColor = stage.colorOp == D3DTOP_PREMODULATE;
            premodulateAlpha = stage.alphaOp == D3DTOP_PREMODULATE;
        }

        auto& shader = out.source;
        shader.reserve(4096);
        shader +=
            "// R84 diagnostic-only fixed-function pixel-shader prototype\n"
            "struct PSInput\n"
            "{\n"
            "    float4 diffuse : COLOR0;\n"
            "    float4 specular : COLOR1;\n";
        for (std::size_t index = 0; index < source.size(); ++index)
        {
            shader += "    float4 tex";
            shader += std::to_string(index);
            shader += " : TEXCOORD";
            shader += std::to_string(index);
            shader += ";\n";
        }
        shader += "};\n";

        premodulateColor = false;
        premodulateAlpha = false;
        for (std::size_t stageIndex = 0;
             stageIndex < source.size(); ++stageIndex)
        {
            const auto& stage = source[stageIndex];
            if (stage.colorOp == D3DTOP_DISABLE)
                break;
            const auto stageBit = static_cast<std::uint8_t>(
                1u << static_cast<unsigned>(stageIndex));
            const bool texturePresent =
                (textureResourcePresentMask & stageBit) != 0;
            const bool usesTexture = fixed_function_stage_uses_texture(
                stage, premodulateColor, premodulateAlpha, texturePresent);

            premodulateColor = stage.colorOp == D3DTOP_PREMODULATE;
            premodulateAlpha = stage.alphaOp == D3DTOP_PREMODULATE;
            if (!usesTexture)
                continue;

            shader += "Texture2D texture";
            shader += std::to_string(stageIndex);
            shader += " : register(t";
            shader += std::to_string(stageIndex);
            shader += ");\nSamplerState sampler";
            shader += std::to_string(stageIndex);
            shader += " : register(s";
            shader += std::to_string(stageIndex);
            shader += ");\n";
        }

        shader +=
            "float4 main(PSInput input) : SV_Target\n"
            "{\n"
            "    float4 current = input.diffuse;\n"
            "    float4 temp = 0.0f;\n";

        premodulateColor = false;
        premodulateAlpha = false;
        for (std::size_t stageIndex = 0;
             stageIndex < source.size(); ++stageIndex)
        {
            const auto& stage = source[stageIndex];
            if (stage.colorOp == D3DTOP_DISABLE)
                break;

            shader += "    { // stage ";
            shader += std::to_string(stageIndex);
            shader += "\n";

            const auto stageBit = static_cast<std::uint8_t>(
                1u << static_cast<unsigned>(stageIndex));
            const bool texturePresent =
                (textureResourcePresentMask & stageBit) != 0;
            const bool usesTexture = fixed_function_stage_uses_texture(
                stage, premodulateColor, premodulateAlpha, texturePresent);
            const bool premodulateCurrentColor =
                premodulateColor && texturePresent;
            const bool premodulateCurrentAlpha =
                premodulateAlpha && texturePresent;
            if (usesTexture)
            {
                const auto coord = static_cast<unsigned>(
                    stage.texCoordIndex & 0xFFFFu);
                shader += "        float4 sampled";
                shader += std::to_string(stageIndex);
                shader += " = texture";
                shader += std::to_string(stageIndex);
                shader += ".Sample(sampler";
                shader += std::to_string(stageIndex);
                shader += ", input.tex";
                shader += std::to_string(coord);
                shader += ".xy);\n";
            }

            shader += "        float3 nextColor = ";
            shader += fixed_function_op_expression(
                stage.colorOp, stage.colorArg0, stage.colorArg1, stage.colorArg2,
                stageIndex, ".rgb", textureFactor, stage.stageConstant,
                premodulateCurrentColor);
            shader += ";\n        float nextAlpha = ";
            shader += fixed_function_op_expression(
                stage.alphaOp, stage.alphaArg0, stage.alphaArg1, stage.alphaArg2,
                stageIndex, ".a", textureFactor, stage.stageConstant,
                premodulateCurrentAlpha);
            shader += ";\n";
            if (stage.resultArg == D3DTA_TEMP)
            {
                shader +=
                    "        temp = float4(nextColor, nextAlpha);\n"
                    "    }\n";
            }
            else
            {
                shader +=
                    "        current = float4(nextColor, nextAlpha);\n"
                    "    }\n";
            }

            premodulateColor = stage.colorOp == D3DTOP_PREMODULATE;
            premodulateAlpha = stage.alphaOp == D3DTOP_PREMODULATE;
        }

        if (alphaTest.enabled != FALSE)
        {
            const auto alphaFunction =
                static_cast<D3DCMPFUNC>(alphaTest.function);
            if (alphaFunction == D3DCMP_NEVER)
            {
                shader +=
                    "    discard; // D3D9 alpha test NEVER\n";
            }
            else if (alphaFunction != D3DCMP_ALWAYS)
            {
                shader += "    const float alphaRef = (";
                shader += std::to_string(alphaTest.reference & 0xFFu);
                shader += ".0f / 255.0f);\n";
                shader += "    if (!(current.a ";
                shader += fixed_function_alpha_compare_operator(
                    alphaTest.function);
                shader += " alphaRef)) discard;\n";
            }
        }

        shader += "    return current;\n}\n";
        out.sourceHash = hash_shader_source(shader);
        return out;
    }

    FixedFunctionPixelShaderCompileProbe
    compile_fixed_function_pixel_shader_prototype(
        const FixedFunctionPixelShaderPrototype& prototype) noexcept
    {
        FixedFunctionPixelShaderCompileProbe out{};
        if (!prototype.generated())
            return out;

        out.attempted = true;
        ID3DBlob* bytecode = nullptr;
        ID3DBlob* diagnostics = nullptr;
        out.result = D3DCompile(
            prototype.source.data(),
            prototype.source.size(),
            "OutRunR84FixedFunctionPrototype",
            nullptr,
            nullptr,
            "main",
            "ps_4_0",
            D3DCOMPILE_ENABLE_STRICTNESS | D3DCOMPILE_OPTIMIZATION_LEVEL3,
            0,
            &bytecode,
            &diagnostics);

        if (diagnostics)
        {
            out.diagnosticsBytes =
                static_cast<UINT>(diagnostics->GetBufferSize());
            out.diagnosticsHash = hash_bytes(
                diagnostics->GetBufferPointer(),
                diagnostics->GetBufferSize());
        }

        if (SUCCEEDED(out.result) && bytecode)
        {
            out.succeeded = true;
            out.bytecodeBytes =
                static_cast<UINT>(bytecode->GetBufferSize());
            out.bytecodeHash = hash_bytes(
                bytecode->GetBufferPointer(),
                bytecode->GetBufferSize());
        }

        if (diagnostics)
            diagnostics->Release();
        if (bytecode)
            bytecode->Release();
        return out;
    }

    FixedFunctionTransformConstants
    generate_fixed_function_transform_constants(
        const D3DMATRIX& world,
        const D3DMATRIX& view,
        const D3DMATRIX& projection,
        bool observationComplete) noexcept
    {
        FixedFunctionTransformConstants out{};
        if (!observationComplete)
        {
            out.unsupported |=
                FixedFunctionTransformUnsupportedIncompleteObservation;
            return out;
        }

        const auto matrix_finite = [](const D3DMATRIX& matrix) noexcept
        {
            for (UINT row = 0; row < 4; ++row)
            {
                for (UINT column = 0; column < 4; ++column)
                {
                    if (!std::isfinite(matrix.m[row][column]))
                        return false;
                }
            }
            return true;
        };

        if (!matrix_finite(world) ||
            !matrix_finite(view) ||
            !matrix_finite(projection))
        {
            out.unsupported |= FixedFunctionTransformUnsupportedNonFinite;
            return out;
        }

        const auto multiply = [](const D3DMATRIX& a,
                                 const D3DMATRIX& b) noexcept
        {
            D3DMATRIX result{};
            for (UINT row = 0; row < 4; ++row)
            {
                for (UINT column = 0; column < 4; ++column)
                {
                    float value = 0.0f;
                    for (UINT inner = 0; inner < 4; ++inner)
                        value += a.m[row][inner] * b.m[inner][column];
                    result.m[row][column] = value;
                }
            }
            return result;
        };

        const D3DMATRIX worldView = multiply(world, view);
        const D3DMATRIX worldViewProjection =
            multiply(worldView, projection);
        if (!matrix_finite(worldViewProjection))
        {
            out.unsupported |= FixedFunctionTransformUnsupportedNonFinite;
            return out;
        }

        for (UINT row = 0; row < 4; ++row)
        {
            for (UINT column = 0; column < 4; ++column)
            {
                out.worldViewProjection[row * 4u + column] =
                    worldViewProjection.m[row][column];
            }
        }
        out.payloadHash = hash_bytes(
            out.worldViewProjection.data(),
            sizeof(float) * out.worldViewProjection.size());
        return out;
    }

    FixedFunctionVertexShaderPrototype
    generate_fixed_function_vertex_shader_prototype(
        DWORD fvf,
        UINT stream0Stride,
        FixedFunctionLightingState lighting)
    {
        FixedFunctionVertexShaderPrototype out{};

        const auto layout = translate_vertex_input_layout(
            nullptr, 0, fvf, stream0Stride);
        if (!layout.exact || !layout.fvfPath)
        {
            out.unsupported |=
                FixedFunctionVertexShaderPrototypeUnsupportedInputLayout;
            return out;
        }
        out.inputElements = layout.elementCount;

        const DWORD position = fvf & D3DFVF_POSITION_MASK;
        switch (position)
        {
        case D3DFVF_XYZ:
            break;
        case D3DFVF_XYZB1:
        case D3DFVF_XYZB2:
        case D3DFVF_XYZB3:
        case D3DFVF_XYZB4:
        case D3DFVF_XYZB5:
            out.unsupported |=
                FixedFunctionVertexShaderPrototypeUnsupportedBlend;
            break;
        default:
            out.unsupported |=
                FixedFunctionVertexShaderPrototypeUnsupportedPosition;
            break;
        }

        if ((fvf & (D3DFVF_LASTBETA_UBYTE4 |
                    D3DFVF_LASTBETA_D3DCOLOR)) != 0)
            out.unsupported |=
                FixedFunctionVertexShaderPrototypeUnsupportedBlend;

        out.hasNormal = (fvf & D3DFVF_NORMAL) != 0;
        if (out.hasNormal &&
            (!lighting.observationComplete || lighting.enabled != FALSE))
        {
            out.unsupported |=
                FixedFunctionVertexShaderPrototypeUnsupportedNormal;
        }
        if ((fvf & D3DFVF_PSIZE) != 0)
            out.unsupported |=
                FixedFunctionVertexShaderPrototypeUnsupportedPointSize;

        out.hasDiffuse = (fvf & D3DFVF_DIFFUSE) != 0;
        out.hasSpecular = (fvf & D3DFVF_SPECULAR) != 0;
        out.texCoordCount = static_cast<UINT>(
            (fvf & D3DFVF_TEXCOUNT_MASK) >> D3DFVF_TEXCOUNT_SHIFT);
        if (out.texCoordCount > 8)
            out.unsupported |=
                FixedFunctionVertexShaderPrototypeUnsupportedTexCoord;

        if (out.unsupported !=
            FixedFunctionVertexShaderPrototypeUnsupportedNone)
            return out;

        const auto tex_coord_type = [&](UINT index) -> const char*
        {
            const DWORD mask = 0x3u << (16u + index * 2u);
            const DWORD sizeBits = fvf & mask;
            if (sizeBits == D3DFVF_TEXCOORDSIZE1(index))
                return "float";
            if (sizeBits == D3DFVF_TEXCOORDSIZE2(index))
                return "float2";
            if (sizeBits == D3DFVF_TEXCOORDSIZE3(index))
                return "float3";
            if (sizeBits == D3DFVF_TEXCOORDSIZE4(index))
                return "float4";
            return nullptr;
        };

        auto& shader = out.source;
        shader.reserve(4096);
        shader +=
            "// R93 diagnostic-only fixed-function vertex-shader prototype\n"
            "cbuffer FixedFunctionTransform : register(b0)\n"
            "{\n"
            "    row_major float4x4 worldViewProjection;\n"
            "};\n"
            "struct VSInput\n"
            "{\n"
            "    float3 position : POSITION0;\n";
        if (out.hasNormal)
            shader += "    float3 normal : NORMAL0;\n";
        if (out.hasDiffuse)
            shader += "    float4 diffuse : COLOR0;\n";
        if (out.hasSpecular)
            shader += "    float4 specular : COLOR1;\n";

        for (UINT index = 0; index < out.texCoordCount; ++index)
        {
            const char* type = tex_coord_type(index);
            if (!type)
            {
                out.unsupported |=
                    FixedFunctionVertexShaderPrototypeUnsupportedTexCoord;
                out.source.clear();
                out.sourceHash = 0;
                return out;
            }
            shader += "    ";
            shader += type;
            shader += " tex";
            shader += std::to_string(index);
            shader += " : TEXCOORD";
            shader += std::to_string(index);
            shader += ";\n";
        }

        shader +=
            "};\n"
            "struct VSOutput\n"
            "{\n"
            "    float4 position : SV_Position;\n";
        if (out.hasNormal)
            shader += "    float3 normal : NORMAL0;\n";
        shader +=
            "    float4 diffuse : COLOR0;\n"
            "    float4 specular : COLOR1;\n";
        for (UINT index = 0; index < 8; ++index)
        {
            shader += "    float4 tex";
            shader += std::to_string(index);
            shader += " : TEXCOORD";
            shader += std::to_string(index);
            shader += ";\n";
        }
        shader +=
            "};\n"
            "VSOutput main(VSInput input)\n"
            "{\n"
            "    VSOutput output;\n"
            "    output.position = mul(float4(input.position, 1.0f), "
            "worldViewProjection);\n";
        if (out.hasNormal)
            shader += "    output.normal = input.normal;\n";
        shader += out.hasDiffuse
            ? "    output.diffuse = input.diffuse;\n"
            : "    output.diffuse = float4(1.0f, 1.0f, 1.0f, 1.0f);\n";
        shader += out.hasSpecular
            ? "    output.specular = input.specular;\n"
            : "    output.specular = float4(1.0f, 1.0f, 1.0f, 1.0f);\n";

        for (UINT index = 0; index < 8; ++index)
        {
            shader += "    output.tex";
            shader += std::to_string(index);
            shader += " = ";
            if (index >= out.texCoordCount)
            {
                shader += "0.0f;\n";
                continue;
            }

            const DWORD mask = 0x3u << (16u + index * 2u);
            const DWORD sizeBits = fvf & mask;
            if (sizeBits == D3DFVF_TEXCOORDSIZE1(index))
            {
                shader += "float4(input.tex";
                shader += std::to_string(index);
                shader += ", 0.0f, 0.0f, 0.0f);\n";
            }
            else if (sizeBits == D3DFVF_TEXCOORDSIZE2(index))
            {
                shader += "float4(input.tex";
                shader += std::to_string(index);
                shader += ", 0.0f, 0.0f);\n";
            }
            else if (sizeBits == D3DFVF_TEXCOORDSIZE3(index))
            {
                shader += "float4(input.tex";
                shader += std::to_string(index);
                shader += ", 0.0f);\n";
            }
            else if (sizeBits == D3DFVF_TEXCOORDSIZE4(index))
            {
                shader += "input.tex";
                shader += std::to_string(index);
                shader += ";\n";
            }
            else
            {
                out.unsupported |=
                    FixedFunctionVertexShaderPrototypeUnsupportedTexCoord;
                out.source.clear();
                out.sourceHash = 0;
                return out;
            }
        }

        shader += "    return output;\n}\n";
        out.sourceHash = hash_shader_source(shader);
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

        const auto sourceBlendValue =
            static_cast<D3DBLEND>(source.srcBlend);
        const auto destinationBlendValue =
            static_cast<D3DBLEND>(source.destBlend);
        auto srcBlend = translate_blend(sourceBlendValue);
        auto dstBlend = translate_blend(destinationBlendValue);
        const auto blendOp = translate_blend_op(
            static_cast<D3DBLENDOP>(source.blendOp));
        const bool dualSourceBlendRequested =
            is_dual_source_blend_factor(sourceBlendValue) ||
            is_dual_source_blend_factor(destinationBlendValue);

        // D3DBLEND_BOTHSRCALPHA/BOTHINVSRCALPHA are legacy source-state
        // shortcuts: when used as D3DRS_SRCBLEND they override DESTBLEND.
        // Keep translate_blend() role-agnostic/fail-closed so the same enum
        // values remain unsupported if they are observed in a destination
        // blend render state.
        if (sourceBlendValue == D3DBLEND_BOTHSRCALPHA)
        {
            srcBlend = { D3D11_BLEND_SRC_ALPHA, true };
            dstBlend = { D3D11_BLEND_INV_SRC_ALPHA, true };
        }
        else if (sourceBlendValue == D3DBLEND_BOTHINVSRCALPHA)
        {
            srcBlend = { D3D11_BLEND_INV_SRC_ALPHA, true };
            dstBlend = { D3D11_BLEND_SRC_ALPHA, true };
        }

        rt.SrcBlend = srcBlend.value;
        rt.DestBlend = dstBlend.value;
        rt.BlendOp = blendOp.value;
        rt.SrcBlendAlpha = srcBlend.value;
        rt.DestBlendAlpha = dstBlend.value;
        rt.BlendOpAlpha = blendOp.value;

        if (rt.BlendEnable && dualSourceBlendRequested)
            out.unsupported |= PipelineUnsupportedDualSourceBlend;

        if (rt.BlendEnable &&
            (!srcBlend.exact || !dstBlend.exact || !blendOp.exact))
            out.unsupported |= PipelineUnsupportedBlend;

        if (rt.BlendEnable && source.separateAlphaBlendEnable != FALSE)
        {
            const auto srcBlendAlpha = translate_separate_alpha_blend_factor(
                static_cast<D3DBLEND>(source.srcBlendAlpha));
            const auto dstBlendAlpha = translate_separate_alpha_blend_factor(
                static_cast<D3DBLEND>(source.destBlendAlpha));
            const auto blendOpAlpha = translate_blend_op(
                static_cast<D3DBLENDOP>(source.blendOpAlpha));

            rt.SrcBlendAlpha = srcBlendAlpha.value;
            rt.DestBlendAlpha = dstBlendAlpha.value;
            rt.BlendOpAlpha = blendOpAlpha.value;
            if (!srcBlendAlpha.exact || !dstBlendAlpha.exact ||
                !blendOpAlpha.exact)
            {
                out.unsupported |= PipelineUnsupportedSeparateAlphaBlend;
            }
        }

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

        out.depth_stencil.StencilEnable = source.stencilEnable != FALSE;
        out.depth_stencil.StencilReadMask =
            static_cast<UINT8>(source.stencilReadMask & 0xFFu);
        out.depth_stencil.StencilWriteMask =
            static_cast<UINT8>(source.stencilWriteMask & 0xFFu);
        out.stencil_ref = source.stencilRef & 0xFFu;

        const auto set_default_stencil_face =
            [](D3D11_DEPTH_STENCILOP_DESC& face) noexcept
        {
            face.StencilFailOp = D3D11_STENCIL_OP_KEEP;
            face.StencilDepthFailOp = D3D11_STENCIL_OP_KEEP;
            face.StencilPassOp = D3D11_STENCIL_OP_KEEP;
            face.StencilFunc = D3D11_COMPARISON_ALWAYS;
        };
        set_default_stencil_face(out.depth_stencil.FrontFace);
        set_default_stencil_face(out.depth_stencil.BackFace);

        const auto translate_stencil_face =
            [](D3D11_DEPTH_STENCILOP_DESC& face,
               DWORD failValue,
               DWORD depthFailValue,
               DWORD passValue,
               DWORD funcValue) noexcept
        {
            const auto fail =
                translate_stencil_op(static_cast<D3DSTENCILOP>(failValue));
            const auto depthFail =
                translate_stencil_op(static_cast<D3DSTENCILOP>(depthFailValue));
            const auto pass =
                translate_stencil_op(static_cast<D3DSTENCILOP>(passValue));
            const auto func =
                translate_compare(static_cast<D3DCMPFUNC>(funcValue));

            face.StencilFailOp = fail.value;
            face.StencilDepthFailOp = depthFail.value;
            face.StencilPassOp = pass.value;
            face.StencilFunc = func.value;
            return fail.exact && depthFail.exact && pass.exact && func.exact;
        };

        if (out.depth_stencil.StencilEnable)
        {
            // R71 keeps FrontCounterClockwise=FALSE, matching D3D9's clockwise
            // front-face convention. D3DRS_STENCIL* therefore maps to
            // D3D11 FrontFace; CCW_STENCIL* maps to BackFace in two-sided mode.
            const bool frontExact = translate_stencil_face(
                out.depth_stencil.FrontFace,
                source.stencilFail,
                source.stencilZFail,
                source.stencilPass,
                source.stencilFunc);
            if (!frontExact)
                out.unsupported |= PipelineUnsupportedStencil;

            if (source.twoSidedStencilMode != FALSE)
            {
                // D3D9 requires two-sided stencil with culling disabled.
                // Keep invalid/driver-dependent combinations fail-closed.
                if (source.cullMode != D3DCULL_NONE)
                {
                    out.unsupported |= PipelineUnsupportedStencil;
                }
                else if (!translate_stencil_face(
                             out.depth_stencil.BackFace,
                             source.ccwStencilFail,
                             source.ccwStencilZFail,
                             source.ccwStencilPass,
                             source.ccwStencilFunc))
                {
                    out.unsupported |= PipelineUnsupportedStencil;
                }
            }
            else
            {
                out.depth_stencil.BackFace = out.depth_stencil.FrontFace;
            }
        }

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
        // R171: D3DRS_MULTISAMPLEANTIALIAS is the D3D9 per-draw
        // multisample-raster switch. Preserve it in the D3D11 rasterizer
        // descriptor rather than silently forcing the native path off.
        out.rasterizer.MultisampleEnable =
            source.multiSampleAntialias != FALSE;
        // R168: D3D11 retains an explicit antialiased-line switch, so carry
        // the captured D3D9 intent instead of silently forcing it off.
        // LASTPIXEL has no D3D11 rasterizer equivalent and remains guarded at
        // direct-line dispatch readiness rather than being misrepresented here.
        out.rasterizer.AntialiasedLineEnable =
            source.antialiasedLineEnable != FALSE;

        // R161: the native path currently assumes normal D3D9 frustum
        // clipping and does not emit SV_ClipDistance for user clip planes.
        // Keep those unmodeled semantics fail-closed instead of silently
        // accepting the unconditional D3D11 DepthClipEnable descriptor.
        if (source.clipping == FALSE || source.clipPlaneEnable != 0u)
            out.unsupported |= PipelineUnsupportedClipping;

        // D3D9 constant depth-bias units are not assumed equivalent to
        // D3D11's integer DepthBias. Preserve both raw float-bit states and
        // reject any non-default bias until an exact mapping is proven.
        if (source.depthBiasBits != 0u ||
            source.slopeScaleDepthBiasBits != 0u)
            out.unsupported |= PipelineUnsupportedDepthBias;

        // R162: the current native fixed-function HLSL follows D3D9's
        // default Gouraud interpolation only. Do not let FLAT/PHONG state be
        // erased by an otherwise exact D3D11 pipeline descriptor.
        if (source.shadeMode != D3DSHADE_GOURAUD)
            out.unsupported |= PipelineUnsupportedShadeMode;

        // R163: exact native fixed-function translation currently assumes one
        // world matrix and no packed matrix-index stream. Keep every D3D9
        // geometry-blend mode fail-closed until that VS path is implemented.
        if (source.vertexBlend != D3DVBF_DISABLE ||
            source.indexedVertexBlendEnable != FALSE)
            out.unsupported |= PipelineUnsupportedVertexBlend;

        // R165: D3D11 has no D3D9 DITHERENABLE state. Do not erase an
        // explicitly enabled legacy output-dithering request.
        if (source.ditherEnable != FALSE)
            out.unsupported |= PipelineUnsupportedDither;

        // R170: WRAP0..7 is a fixed-function coordinate operation, not
        // sampler addressing. Keep every non-default mask fail-closed.
        for (const auto wrap : source.textureCoordinateWrap)
        {
            if (wrap != 0u)
            {
                out.unsupported |= PipelineUnsupportedTextureCoordinateWrap;
                break;
            }
        }

        // D3D9 COLORWRITEENABLE1..3 default to 0x0000000F. Until native
        // MRT output binding exists, any secondary-target write-mask override
        // cannot be represented by the RT0-only D3D11 path.
        constexpr DWORD DefaultMrtColorWriteMask = 0x0000000Fu;
        for (const auto mask : source.additionalColorWriteEnable)
        {
            if (mask != DefaultMrtColorWriteMask)
            {
                out.unsupported |= PipelineUnsupportedMrtColorWrite;
                break;
            }
        }

        if (source.alphaTestEnable != FALSE)
            out.unsupported |= PipelineUnsupportedAlphaTest;
        if (source.fogEnable != FALSE)
            out.unsupported |= PipelineUnsupportedFog;
        // R202: D3DRS_SPECULARENABLE performs a fixed-function
        // specular add after the texture cascade. The dormant native shader
        // path does not model that operation, so share the existing lighting
        // blocker until explicit post-texture specular semantics exist.
        if (source.lighting != FALSE || source.specularEnable != FALSE)
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
        out.stream0Stride = stream0Stride;
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
