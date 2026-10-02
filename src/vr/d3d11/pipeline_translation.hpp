#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <d3d9.h>
#include <d3d11.h>

#include "vr/core/d3d9_draw_state.hpp"

namespace outrun::vr::dx11
{
    enum PipelineUnsupported : std::uint32_t
    {
        PipelineUnsupportedNone = 0,
        PipelineUnsupportedIncompleteSnapshot = 1u << 0,
        PipelineUnsupportedWBuffer = 1u << 1,
        PipelineUnsupportedSeparateAlphaBlend = 1u << 2,
        PipelineUnsupportedAlphaTest = 1u << 3,
        PipelineUnsupportedStencil = 1u << 4,
        PipelineUnsupportedFog = 1u << 5,
        PipelineUnsupportedLighting = 1u << 6,
        PipelineUnsupportedSrgbWrite = 1u << 7,
        PipelineUnsupportedFillMode = 1u << 8,
        PipelineUnsupportedBlend = 1u << 9,
        PipelineUnsupportedDepthCompare = 1u << 10,
        PipelineUnsupportedCull = 1u << 11,
        // D3D9Ex SRC*COLOR2 needs a second pixel-shader color output. Keep
        // this distinct from generic blend translation failures so fixed-
        // function readiness cannot accidentally treat a D3D11 SRC1 enum
        // mapping as proof that SV_Target1 semantics exist.
        PipelineUnsupportedDualSourceBlend = 1u << 12,
        // R162: the generated fixed-function shaders use ordinary smooth
        // interpolation. D3D9 FLAT/PHONG shade modes require separate
        // semantics and therefore remain fail-closed.
        PipelineUnsupportedShadeMode = 1u << 13,
        // R161: native fixed-function readiness currently models the normal
        // D3D9 clipping path only. Disabled clipping or enabled user clip
        // planes require shader/raster semantics that are not implemented.
        PipelineUnsupportedClipping = 1u << 14,
        // D3D9 DEPTHBIAS uses API/format-specific constant-bias semantics.
        // Until an exact cross-API mapping is proven, any non-zero constant
        // or slope-scale bias must block dormant native readiness.
        PipelineUnsupportedDepthBias = 1u << 15,
    };

    struct PipelineTranslation
    {
        D3D11_BLEND_DESC blend{};
        D3D11_DEPTH_STENCIL_DESC depth_stencil{};
        UINT stencil_ref = 0;
        D3D11_RASTERIZER_DESC rasterizer{};
        std::uint32_t unsupported = PipelineUnsupportedNone;

        [[nodiscard]] bool exact() const noexcept
        {
            return unsupported == PipelineUnsupportedNone;
        }
    };

    [[nodiscard]] PipelineTranslation translate_pipeline(
        const OutRunVR::DrawState::RenderStateSnapshot& source) noexcept;

    // R82 models a deliberately conservative subset of D3D9 fixed-function
    // texture/sampler state that a future native shader generator may consume.
    // This is readiness classification only; it does not emit shaders and must
    // not be treated as native-draw activation proof.
    enum FixedFunctionUnsupported : std::uint32_t
    {
        FixedFunctionUnsupportedNone = 0,
        FixedFunctionUnsupportedIncompleteObservation = 1u << 0,
        FixedFunctionUnsupportedStageChain = 1u << 1,
        FixedFunctionUnsupportedResourceStageCoverage = 1u << 2,
        FixedFunctionUnsupportedColorOp = 1u << 3,
        FixedFunctionUnsupportedAlphaOp = 1u << 4,
        FixedFunctionUnsupportedArgument = 1u << 5,
        FixedFunctionUnsupportedTexCoord = 1u << 6,
        FixedFunctionUnsupportedTextureTransform = 1u << 7,
        FixedFunctionUnsupportedSamplerFilter = 1u << 8,
        FixedFunctionUnsupportedSamplerAddress = 1u << 9,
        FixedFunctionUnsupportedSamplerLod = 1u << 10,
    };

    struct FixedFunctionStageState
    {
        DWORD colorOp = D3DTOP_DISABLE;
        DWORD colorArg1 = D3DTA_TEXTURE;
        DWORD colorArg2 = D3DTA_CURRENT;
        DWORD alphaOp = D3DTOP_DISABLE;
        DWORD alphaArg1 = D3DTA_TEXTURE;
        DWORD alphaArg2 = D3DTA_CURRENT;
        DWORD texCoordIndex = 0;
        DWORD textureTransformFlags = D3DTTFF_DISABLE;
        DWORD minFilter = D3DTEXF_NONE;
        DWORD magFilter = D3DTEXF_NONE;
        DWORD mipFilter = D3DTEXF_NONE;
        // R125 preserves raw D3D9 sampler LOD provenance. The current native
        // sampler contract proves only the legacy defaults, so non-default
        // bias/most-detailed-mip state remains fail-closed.
        DWORD mipLodBiasBits = 0;
        DWORD maxMipLevel = 0;
        // R159 maps the address modes with identical D3D9/D3D11 coordinate
        // semantics directly. R160 captures D3DSAMP_BORDERCOLOR so BORDER can
        // preserve the exact D3D9 ARGB sampler color in D3D11 RGBA form.
        DWORD addressU = D3DTADDRESS_WRAP;
        DWORD addressV = D3DTADDRESS_WRAP;
        DWORD borderColor = 0;
    };

    // R98 translates the conservative R82 sampler subset into a concrete
    // D3D11 sampler descriptor for the R84 Texture2D path. This remains a
    // readiness contract only; no game draw path binds the resulting state.
    struct FixedFunctionSamplerTranslation
    {
        D3D11_SAMPLER_DESC desc{};
        bool exact = false;
    };

    [[nodiscard]] FixedFunctionSamplerTranslation
    translate_fixed_function_sampler(
        const FixedFunctionStageState& source) noexcept;

    struct FixedFunctionTranslationReadiness
    {
        std::uint32_t unsupported = FixedFunctionUnsupportedNone;
        UINT activeStages = 0;

        [[nodiscard]] bool exact() const noexcept
        {
            return unsupported == FixedFunctionUnsupportedNone;
        }
    };

    [[nodiscard]] FixedFunctionTranslationReadiness
    translate_fixed_function_readiness(
        const std::array<FixedFunctionStageState, 8>& source,
        bool observationComplete,
        std::uint8_t textureResourcePresentMask,
        std::uint8_t textureResourceExactMask) noexcept;

    // R84 is a diagnostic-only pixel-shader source prototype. It consumes
    // only R82/R83-ready fixed-function states, emits no D3D11 shader object,
    // and must never be interpreted as native-draw activation proof.
    enum FixedFunctionShaderPrototypeUnsupported : std::uint32_t
    {
        FixedFunctionShaderPrototypeUnsupportedNone = 0,
        FixedFunctionShaderPrototypeUnsupportedNotReady = 1u << 0,
        FixedFunctionShaderPrototypeUnsupportedResourceType = 1u << 1,
        FixedFunctionShaderPrototypeUnsupportedAlphaTestState = 1u << 2,
    };

    // D3D9 alpha testing is pixel-shader behavior in the native DX11 path.
    // Keep the state explicit in the diagnostic prototype so readiness
    // evidence cannot silently drop ALPHAREF/ALPHAFUNC semantics.
    struct FixedFunctionAlphaTestState
    {
        bool observationComplete = true;
        DWORD enabled = FALSE;
        DWORD reference = 0;
        DWORD function = D3DCMP_ALWAYS;
    };

    struct FixedFunctionPixelShaderPrototype
    {
        std::uint32_t unsupported =
            FixedFunctionShaderPrototypeUnsupportedNone;
        UINT activeStages = 0;
        std::uint64_t sourceHash = 0;
        std::string source;

        [[nodiscard]] bool generated() const noexcept
        {
            return unsupported ==
                       FixedFunctionShaderPrototypeUnsupportedNone &&
                   !source.empty();
        }
    };

    [[nodiscard]] FixedFunctionPixelShaderPrototype
    generate_fixed_function_pixel_shader_prototype(
        const std::array<FixedFunctionStageState, 8>& source,
        bool observationComplete,
        std::uint8_t textureResourcePresentMask,
        std::uint8_t textureResourceExactMask,
        const std::array<D3DRESOURCETYPE, 8>& textureResourceTypes,
        FixedFunctionAlphaTestState alphaTest = {});

    // R85 compiles the generated R84 source only as an offline diagnostic
    // probe. The bytecode is immediately discarded and never bound to a
    // D3D11 device; success therefore proves compiler acceptance only.
    struct FixedFunctionPixelShaderCompileProbe
    {
        bool attempted = false;
        bool succeeded = false;
        HRESULT result = E_FAIL;
        UINT bytecodeBytes = 0;
        std::uint64_t bytecodeHash = 0;
        UINT diagnosticsBytes = 0;
        std::uint64_t diagnosticsHash = 0;
    };

    [[nodiscard]] FixedFunctionPixelShaderCompileProbe
    compile_fixed_function_pixel_shader_prototype(
        const FixedFunctionPixelShaderPrototype& prototype) noexcept;

    // R93 emits a diagnostic-only vertex-shader source for the narrow
    // untransformed fixed-function FVF subset that can feed the R84 pixel
    // prototype. It models a future b0 WVP constant-buffer contract but never
    // binds a shader or changes native-draw activation.
    enum FixedFunctionVertexShaderPrototypeUnsupported : std::uint32_t
    {
        FixedFunctionVertexShaderPrototypeUnsupportedNone = 0,
        FixedFunctionVertexShaderPrototypeUnsupportedInputLayout = 1u << 0,
        FixedFunctionVertexShaderPrototypeUnsupportedPosition = 1u << 1,
        FixedFunctionVertexShaderPrototypeUnsupportedBlend = 1u << 2,
        FixedFunctionVertexShaderPrototypeUnsupportedNormal = 1u << 3,
        FixedFunctionVertexShaderPrototypeUnsupportedPointSize = 1u << 4,
        FixedFunctionVertexShaderPrototypeUnsupportedSpecular = 1u << 5,
        FixedFunctionVertexShaderPrototypeUnsupportedTexCoord = 1u << 6,
    };

    struct FixedFunctionLightingState
    {
        // A normal-bearing FVF is exact for this diagnostic prototype only
        // when the D3D9 lighting render state is known disabled. If lighting
        // is enabled, material/light semantics remain a separate fail-closed
        // conversion item.
        bool observationComplete = false;
        DWORD enabled = FALSE;
    };

    struct FixedFunctionVertexShaderPrototype
    {
        std::uint32_t unsupported =
            FixedFunctionVertexShaderPrototypeUnsupportedNone;
        UINT inputElements = 0;
        UINT texCoordCount = 0;
        bool hasDiffuse = false;
        bool hasNormal = false;
        std::uint64_t sourceHash = 0;
        std::string source;

        [[nodiscard]] bool generated() const noexcept
        {
            return unsupported ==
                       FixedFunctionVertexShaderPrototypeUnsupportedNone &&
                   !source.empty();
        }
    };

    [[nodiscard]] FixedFunctionVertexShaderPrototype
    generate_fixed_function_vertex_shader_prototype(
        DWORD fvf,
        UINT stream0Stride,
        FixedFunctionLightingState lighting = {});

    // R94 translates passively observed D3D9 WORLD/VIEW/PROJECTION state
    // into the row-major b0 payload consumed by the R93 diagnostic vertex
    // prototype. This is binding-readiness evidence only; no runtime D3D11
    // constant buffer is allocated or bound here.
    enum FixedFunctionTransformUnsupported : std::uint32_t
    {
        FixedFunctionTransformUnsupportedNone = 0,
        FixedFunctionTransformUnsupportedIncompleteObservation = 1u << 0,
        FixedFunctionTransformUnsupportedNonFinite = 1u << 1,
    };

    struct FixedFunctionTransformConstants
    {
        std::uint32_t unsupported = FixedFunctionTransformUnsupportedNone;
        std::array<float, 16> worldViewProjection{};
        std::uint64_t payloadHash = 0;

        [[nodiscard]] bool exact() const noexcept
        {
            return unsupported == FixedFunctionTransformUnsupportedNone;
        }
    };

    [[nodiscard]] FixedFunctionTransformConstants
    generate_fixed_function_transform_constants(
        const D3DMATRIX& world,
        const D3DMATRIX& view,
        const D3DMATRIX& projection,
        bool observationComplete) noexcept;

    // R79/R88 translates either an explicit D3D9 declaration or a
    // conservative FVF subset into canonical D3D11 input-layout descriptors.
    // R88 models XYZB1..XYZB5 blend weights plus LASTBETA_UBYTE4 and
    // LASTBETA_D3DCOLOR index encodings. Unmodelled/reserved combinations
    // remain fail-closed. Programmable shader-signature compatibility remains
    // an independent F21 gate; exact means descriptor-level readiness only.
    struct VertexInputLayoutTranslation
    {
        std::array<D3D11_INPUT_ELEMENT_DESC, MAXD3DDECLLENGTH> elements{};
        UINT elementCount = 0;
        // R158 preserves the exact D3D9 stream-0 stride used when descriptor
        // offsets were validated. D3D11 input-layout objects do not encode
        // vertex-buffer stride, so final IA readiness must carry it separately.
        UINT stream0Stride = 0;
        bool exact = false;
        bool declarationPath = false;
        bool fvfPath = false;
        bool fvfPending = false;
    };

    [[nodiscard]] VertexInputLayoutTranslation translate_vertex_input_layout(
        const D3DVERTEXELEMENT9* source,
        UINT count,
        DWORD fvf,
        UINT stream0Stride) noexcept;
}
