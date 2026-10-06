#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <vector>
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
        // R163: D3D9 fixed-function matrix blending requires multiple world
        // transforms and optional packed matrix indices that the dormant
        // native vertex shader does not model.
        PipelineUnsupportedVertexBlend = 1u << 16,
        // R165: D3D9 can explicitly enable output dithering, while D3D11
        // exposes no equivalent raster/OM toggle. Keep enabled dithering
        // fail-closed until exact output-format behavior is proven.
        PipelineUnsupportedDither = 1u << 17,
        // R170: any non-zero D3DRS_WRAP0..7 mask needs fixed-function
        // vertex-coordinate semantics the dormant native VS does not model.
        PipelineUnsupportedTextureCoordinateWrap = 1u << 18,
        // D3D9 COLORWRITEENABLE1..3 configure secondary MRT write masks.
        // Native fixed-function output currently owns RT0 only.
        PipelineUnsupportedMrtColorWrite = 1u << 19,
        // R204: keep the post-texture D3DRS_SPECULARENABLE semantic distinct
        // from fixed-function lighting. Both remain fail-closed, but exact
        // census evidence must be able to identify which blocker was observed.
        PipelineUnsupportedSpecular = 1u << 20,
        // R166: one-past-last bit count consumed by the runtime census. Keep
        // this sentinel synchronized with concrete PipelineUnsupported bits;
        // the source-graph gate verifies max(bit)+1 == this value.
        PipelineUnsupportedBitCount = 21u,
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
        // D3D9 D3DSAMP_SRGBTEXTURE changes texture decode semantics. The
        // current native Texture2D SRV path is not yet format-promoted to an
        // sRGB view, so nonzero state must remain fail-closed.
        FixedFunctionUnsupportedSamplerSrgb = 1u << 11,
        // R201: D3DTSS_RESULTARG may target CURRENT or TEMP. TEMP is readable
        // from its D3D9 default transparent-black value even before a write;
        // this bit therefore guards only invalid result destinations.
        FixedFunctionUnsupportedResultArg = 1u << 12,
    };

    struct FixedFunctionStageState
    {
        DWORD colorOp = D3DTOP_DISABLE;
        DWORD colorArg1 = D3DTA_TEXTURE;
        DWORD colorArg2 = D3DTA_CURRENT;
        // R194: D3D9 ternary operations use COLORARG0/ALPHAARG0 as their
        // third source operand. Both states default to CURRENT.
        DWORD colorArg0 = D3DTA_CURRENT;
        DWORD alphaOp = D3DTOP_DISABLE;
        DWORD alphaArg1 = D3DTA_TEXTURE;
        DWORD alphaArg2 = D3DTA_CURRENT;
        DWORD alphaArg0 = D3DTA_CURRENT;
        // R197: D3DTSS_CONSTANT is an ARGB per-stage color selected by
        // D3DTA_CONSTANT. Direct3D 9 defines an opaque-white default.
        DWORD stageConstant = 0xFFFFFFFFu;
        // D3D9 defaults stage output to CURRENT. TEMP is a separate
        // cross-stage register initialized to transparent black; redirecting a
        // result to TEMP preserves CURRENT.
        DWORD resultArg = D3DTA_CURRENT;
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
        // Preserve raw D3D9 sampler sRGB-decode intent. FALSE is exact with
        // the current linear SRV path; enabled sRGB decode is gated until an
        // exact sRGB SRV/format translation is implemented.
        DWORD srgbTexture = FALSE;
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
        FixedFunctionAlphaTestState alphaTest = {},
        DWORD textureFactor = 0xFFFFFFFFu);

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

    // R239 seals the census-observed D3D9 programmable VS/PS identity into a
    // deterministic stage-typed cache key for a future translator/object
    // cache. This is identity readiness only: it neither translates bytecode
    // nor creates/binds D3D11 shaders, and translationImplemented stays false.
    enum ProgrammableShaderPairIdentityUnsupported : std::uint32_t
    {
        ProgrammableShaderPairIdentityUnsupportedNone = 0,
        ProgrammableShaderPairIdentityUnsupportedIncompleteObservation = 1u << 0,
        ProgrammableShaderPairIdentityUnsupportedMixedPair = 1u << 1,
        ProgrammableShaderPairIdentityUnsupportedMissingVertexShader = 1u << 2,
        ProgrammableShaderPairIdentityUnsupportedMissingPixelShader = 1u << 3,
        ProgrammableShaderPairIdentityUnsupportedInvalidVertexBytecode = 1u << 4,
        ProgrammableShaderPairIdentityUnsupportedInvalidPixelBytecode = 1u << 5,
        ProgrammableShaderPairIdentityUnsupportedInvalidVertexVersion = 1u << 6,
        ProgrammableShaderPairIdentityUnsupportedInvalidPixelVersion = 1u << 7,
        ProgrammableShaderPairIdentityUnsupportedMissingVertexHash = 1u << 8,
        ProgrammableShaderPairIdentityUnsupportedMissingPixelHash = 1u << 9,
    };

    struct ProgrammableShaderFunctionIdentity
    {
        bool present = false;
        bool observed = false;
        UINT byteSize = 0;
        DWORD versionToken = 0;
        std::uint64_t bytecodeHash = 0;
    };

    struct ProgrammableShaderPairCacheIdentity
    {
        std::uint32_t unsupported =
            ProgrammableShaderPairIdentityUnsupportedNone;
        ProgrammableShaderFunctionIdentity vertexShader{};
        ProgrammableShaderFunctionIdentity pixelShader{};
        std::uint64_t cacheKey = 0;
        bool translationImplemented = false;

        [[nodiscard]] bool exact_identity() const noexcept
        {
            return unsupported ==
                       ProgrammableShaderPairIdentityUnsupportedNone &&
                   cacheKey != 0;
        }
    };

    // R264 preserves the exact D3D9 programmable-shader function bytes that
    // produced an R239 identity. This is source evidence for a future
    // translator only: no D3D11 object is created or bound here.
    struct ProgrammableShaderFunctionSourceEvidence
    {
        bool vertexStage = false;
        bool observed = false;
        bool versionSupported = false;
        UINT byteSize = 0;
        DWORD versionToken = 0;
        std::uint64_t bytecodeHash = 0;
        std::vector<DWORD> tokens;

        [[nodiscard]] bool exact() const noexcept
        {
            return observed &&
                   versionSupported &&
                   byteSize >= 2u * sizeof(DWORD) &&
                   byteSize <= 1024u * 1024u &&
                   (byteSize % sizeof(DWORD)) == 0 &&
                   tokens.size() == byteSize / sizeof(DWORD) &&
                   bytecodeHash != 0;
        }
    };

    [[nodiscard]] ProgrammableShaderFunctionSourceEvidence
    capture_programmable_shader_function_source_evidence(
        const void* bytecode,
        UINT byteSize,
        bool vertexStage) noexcept;

    [[nodiscard]] bool
    validate_programmable_shader_function_source_evidence(
        const ProgrammableShaderFunctionSourceEvidence& evidence,
        const ProgrammableShaderFunctionIdentity& identity,
        bool vertexStage) noexcept;

    // R265 decodes the bounded R264 DWORD stream into instruction tokens plus
    // their raw operand-token ranges for shader model 2.x/3.x only. This is a
    // fail-closed structural decoder: it does not yet claim register, constant,
    // sampler, linkage, or HLSL translation semantics.
    struct ProgrammableShaderDecodedInstruction
    {
        DWORD instructionToken = 0;
        DWORD opcode = 0;
        UINT tokenOffset = 0;
        UINT operandCount = 0;
        std::vector<DWORD> operandTokens;
    };

    struct ProgrammableShaderInstructionDecode
    {
        bool vertexStage = false;
        DWORD versionToken = 0;
        bool sourceExact = false;
        bool versionSupported = false;
        bool endSeen = false;
        bool complete = false;
        UINT instructionCount = 0;
        UINT operandTokenCount = 0;
        UINT commentDwordCount = 0;
        std::uint64_t sourceBytecodeHash = 0;
        std::uint64_t instructionStreamHash = 0;
        std::uint64_t decoderRevisionHash = 0;
        std::uint64_t semanticContractHash = 0;
        std::vector<ProgrammableShaderDecodedInstruction> instructions;

        [[nodiscard]] bool exact() const noexcept
        {
            return sourceExact &&
                   versionSupported &&
                   endSeen &&
                   complete &&
                   instructionCount != 0 &&
                   instructions.size() == instructionCount &&
                   sourceBytecodeHash != 0 &&
                   instructionStreamHash != 0 &&
                   decoderRevisionHash != 0 &&
                   semanticContractHash != 0;
        }
    };

    [[nodiscard]] ProgrammableShaderInstructionDecode
    decode_programmable_shader_instruction_stream(
        const ProgrammableShaderFunctionSourceEvidence& evidence) noexcept;

    // R266 derives fail-closed register-level semantics from the exact R265
    // instruction stream. It classifies opcode-specific destination/source
    // parameter roles, register file/index/modifier/addressing fields, and
    // constant/sampler provenance without translating or binding shaders.
    enum class ProgrammableShaderRegisterOperandRole : std::uint8_t
    {
        Destination = 0,
        Source = 1,
        RelativeAddress = 2,
        Declaration = 3,
    };

    struct ProgrammableShaderRegisterOperand
    {
        ProgrammableShaderRegisterOperandRole role =
            ProgrammableShaderRegisterOperandRole::Source;
        DWORD token = 0;
        D3DSHADER_PARAM_REGISTER_TYPE registerType = D3DSPR_FORCE_DWORD;
        UINT registerIndex = 0;
        DWORD writeMask = 0;
        DWORD destinationModifier = 0;
        DWORD destinationShift = 0;
        DWORD sourceSwizzle = 0;
        DWORD sourceModifier = 0;
        bool relativeAddressing = false;
        bool constantReference = false;
        bool samplerReference = false;
        UINT normalizedConstantIndex = 0;
    };

    struct ProgrammableShaderRegisterSemantics
    {
        bool vertexStage = false;
        bool instructionDecodeExact = false;
        bool complete = false;
        // R270 binds register/constant/sampler semantics back to the exact
        // R265 source stream so later F21 evidence cannot accept a detached
        // but otherwise well-formed semantic receipt.
        DWORD versionToken = 0;
        std::uint64_t sourceBytecodeHash = 0;
        UINT instructionCount = 0;
        UINT semanticInstructionCount = 0;
        UINT destinationOperandCount = 0;
        UINT sourceOperandCount = 0;
        UINT relativeAddressOperandCount = 0;
        UINT declarationOperandCount = 0;
        UINT literalDwordCount = 0;
        UINT floatConstantReferenceCount = 0;
        UINT intConstantReferenceCount = 0;
        UINT boolConstantReferenceCount = 0;
        UINT samplerReferenceCount = 0;
        UINT constantDefinitionCount = 0;
        std::uint64_t registerSemanticsHash = 0;
        std::uint64_t decoderRevisionHash = 0;
        std::uint64_t semanticContractHash = 0;
        std::vector<ProgrammableShaderRegisterOperand> operands;

        [[nodiscard]] bool exact() const noexcept
        {
            return instructionDecodeExact &&
                   complete &&
                   versionToken != 0 &&
                   sourceBytecodeHash != 0 &&
                   semanticInstructionCount == instructionCount &&
                   registerSemanticsHash != 0 &&
                   decoderRevisionHash != 0 &&
                   semanticContractHash != 0;
        }
    };

    [[nodiscard]] ProgrammableShaderRegisterSemantics
    decode_programmable_shader_register_semantics(
        const ProgrammableShaderInstructionDecode& decode) noexcept;

    // R270 validates that one exact R266 semantic receipt still belongs to
    // the exact R265 instruction stream from which it was derived.
    [[nodiscard]] bool
    validate_programmable_shader_register_semantics(
        const ProgrammableShaderRegisterSemantics& semantics,
        const ProgrammableShaderInstructionDecode& decode) noexcept;

    // R267 derives explicit shader-model-3 interface declaration semantics
    // from the exact R265/R266 stream. It records DCL usage/index/register
    // and write-mask provenance for vertex inputs/outputs and pixel inputs.
    // Sampler declarations are counted but are not treated as inter-stage
    // semantics. Shader-model-2 and ambiguous declaration layouts stay
    // fail-closed; this is evidence only and does not emit/bind shaders.
    struct ProgrammableShaderInterfaceSemantic
    {
        bool input = false;
        bool output = false;
        D3DDECLUSAGE usage = D3DDECLUSAGE_POSITION;
        UINT usageIndex = 0;
        D3DSHADER_PARAM_REGISTER_TYPE registerType = D3DSPR_FORCE_DWORD;
        UINT registerIndex = 0;
        DWORD writeMask = 0;
    };

    struct ProgrammableShaderInterfaceSemantics
    {
        bool vertexStage = false;
        bool instructionDecodeExact = false;
        bool registerSemanticsExact = false;
        bool shaderModel3 = false;
        bool complete = false;
        // R269: carry the exact R264/R265 source identity through R267 so
        // pair-level R268 linkage can be checked against the census-sealed
        // shader pair instead of accepting a detached semantic hash.
        DWORD versionToken = 0;
        std::uint64_t sourceBytecodeHash = 0;
        UINT declarationInstructionCount = 0;
        UINT semanticDeclarationCount = 0;
        UINT inputSemanticCount = 0;
        UINT outputSemanticCount = 0;
        UINT samplerDeclarationCount = 0;
        std::uint64_t interfaceSemanticsHash = 0;
        std::uint64_t decoderRevisionHash = 0;
        std::uint64_t semanticContractHash = 0;
        std::vector<ProgrammableShaderInterfaceSemantic> semantics;

        [[nodiscard]] bool exact() const noexcept
        {
            return instructionDecodeExact &&
                   registerSemanticsExact &&
                   shaderModel3 &&
                   complete &&
                   versionToken != 0 &&
                   sourceBytecodeHash != 0 &&
                   interfaceSemanticsHash != 0 &&
                   decoderRevisionHash != 0 &&
                   semanticContractHash != 0;
        }
    };

    [[nodiscard]] ProgrammableShaderInterfaceSemantics
    decode_programmable_shader_interface_semantics(
        const ProgrammableShaderInstructionDecode& decode,
        const ProgrammableShaderRegisterSemantics& registerSemantics) noexcept;

    // R268 consumes two exact R267 shader-model-3 interface receipts and
    // proves only the inter-stage VS-output -> PS-input contract. Every pixel
    // input semantic must have one same-usage/index vertex output whose
    // declared component mask covers the pixel declaration. Extra VS outputs
    // are permitted. Missing/mismatched semantics, insufficient masks, stage
    // inversion, or inconsistent R267 counts fail closed. This remains
    // diagnostic evidence only and does not authorize native Draw* dispatch.
    struct ProgrammableShaderInterfaceLinkageEvidence
    {
        bool vertexInterfaceExact = false;
        bool pixelInterfaceExact = false;
        bool complete = false;
        // R269: retain source identities for the pair-level receipt consumed
        // by R263 semantic-translation readiness.
        DWORD vertexVersionToken = 0;
        DWORD pixelVersionToken = 0;
        std::uint64_t vertexSourceBytecodeHash = 0;
        std::uint64_t pixelSourceBytecodeHash = 0;
        UINT vertexOutputSemanticCount = 0;
        UINT pixelInputSemanticCount = 0;
        UINT matchedSemanticCount = 0;
        std::uint64_t interfaceLinkHash = 0;
        std::uint64_t linkerRevisionHash = 0;
        std::uint64_t semanticContractHash = 0;

        [[nodiscard]] bool exact() const noexcept
        {
            return vertexInterfaceExact &&
                   pixelInterfaceExact &&
                   complete &&
                   vertexVersionToken != 0 &&
                   pixelVersionToken != 0 &&
                   vertexSourceBytecodeHash != 0 &&
                   pixelSourceBytecodeHash != 0 &&
                   matchedSemanticCount == pixelInputSemanticCount &&
                   interfaceLinkHash != 0 &&
                   linkerRevisionHash != 0 &&
                   semanticContractHash != 0;
        }
    };

    [[nodiscard]] ProgrammableShaderInterfaceLinkageEvidence
    derive_programmable_shader_interface_linkage_evidence(
        const ProgrammableShaderInterfaceSemantics& vertexSemantics,
        const ProgrammableShaderInterfaceSemantics& pixelSemantics) noexcept;

    // R271 composes one pair-level source-semantic receipt from the exact R239
    // programmable pair identity, source-attested R266 VS/PS register semantics
    // and the exact R268 stage-linkage receipt. This is production census
    // evidence only; it does not claim translation or authorize native Draw*.
    struct ProgrammableShaderPairSourceSemanticEvidence
    {
        bool sourceIdentityExact = false;
        bool vertexRegisterSemanticsExact = false;
        bool pixelRegisterSemanticsExact = false;
        bool interfaceLinkageExact = false;
        bool complete = false;
        std::uint64_t cacheKey = 0;
        DWORD vertexVersionToken = 0;
        DWORD pixelVersionToken = 0;
        std::uint64_t vertexSourceBytecodeHash = 0;
        std::uint64_t pixelSourceBytecodeHash = 0;
        std::uint64_t vertexRegisterSemanticsHash = 0;
        std::uint64_t pixelRegisterSemanticsHash = 0;
        std::uint64_t interfaceLinkHash = 0;
        UINT vertexConstantReferenceCount = 0;
        UINT pixelConstantReferenceCount = 0;
        UINT vertexSamplerReferenceCount = 0;
        UINT pixelSamplerReferenceCount = 0;
        std::uint64_t pairSemanticHash = 0;
        std::uint64_t receiptRevisionHash = 0;
        std::uint64_t semanticContractHash = 0;

        [[nodiscard]] bool exact() const noexcept
        {
            return sourceIdentityExact &&
                   vertexRegisterSemanticsExact &&
                   pixelRegisterSemanticsExact &&
                   interfaceLinkageExact &&
                   complete &&
                   cacheKey != 0 &&
                   vertexVersionToken != 0 &&
                   pixelVersionToken != 0 &&
                   vertexSourceBytecodeHash != 0 &&
                   pixelSourceBytecodeHash != 0 &&
                   vertexRegisterSemanticsHash != 0 &&
                   pixelRegisterSemanticsHash != 0 &&
                   interfaceLinkHash != 0 &&
                   pairSemanticHash != 0 &&
                   receiptRevisionHash != 0 &&
                   semanticContractHash != 0;
        }
    };

    [[nodiscard]] ProgrammableShaderPairSourceSemanticEvidence
    derive_programmable_shader_pair_source_semantic_evidence(
        const ProgrammableShaderPairCacheIdentity& sourceIdentity,
        const ProgrammableShaderRegisterSemantics& vertexSemantics,
        const ProgrammableShaderRegisterSemantics& pixelSemantics,
        const ProgrammableShaderInterfaceLinkageEvidence& interfaceLinkage) noexcept;

    // R272 turns the exact R271 pair receipt plus R266 operand provenance into
    // a deterministic, fail-closed logical constant/sampler mapping plan.
    // The target indices are translation-plan identities only: no D3D11
    // constant buffer, sampler object or shader is created/bound here.
    enum class ProgrammableShaderConstantRegisterClass : std::uint8_t
    {
        Float = 0,
        Int = 1,
        Bool = 2,
    };

    struct ProgrammableShaderConstantRegisterMapping
    {
        bool vertexStage = false;
        ProgrammableShaderConstantRegisterClass registerClass =
            ProgrammableShaderConstantRegisterClass::Float;
        D3DSHADER_PARAM_REGISTER_TYPE sourceRegisterType = D3DSPR_FORCE_DWORD;
        UINT sourceRegisterIndex = 0;
        UINT normalizedConstantIndex = 0;
        UINT logicalTargetIndex = 0;
    };

    struct ProgrammableShaderSamplerRegisterMapping
    {
        bool vertexStage = false;
        UINT sourceRegisterIndex = 0;
        UINT targetSamplerSlot = 0;
    };

    struct ProgrammableShaderRegisterMappingPlanEvidence
    {
        bool sourceSemanticReceiptExact = false;
        bool vertexRegisterSemanticsExact = false;
        bool pixelRegisterSemanticsExact = false;
        bool constantRegisterMappingExact = false;
        bool samplerMappingExact = false;
        bool complete = false;
        std::uint64_t cacheKey = 0;
        std::uint64_t pairSemanticHash = 0;
        std::uint64_t vertexRegisterSemanticsHash = 0;
        std::uint64_t pixelRegisterSemanticsHash = 0;
        UINT constantMappingCount = 0;
        UINT samplerMappingCount = 0;
        std::uint64_t constantMappingHash = 0;
        std::uint64_t samplerMappingHash = 0;
        std::uint64_t planRevisionHash = 0;
        std::uint64_t semanticContractHash = 0;
        std::vector<ProgrammableShaderConstantRegisterMapping> constantMappings;
        std::vector<ProgrammableShaderSamplerRegisterMapping> samplerMappings;

        [[nodiscard]] bool exact() const noexcept
        {
            return sourceSemanticReceiptExact &&
                   vertexRegisterSemanticsExact &&
                   pixelRegisterSemanticsExact &&
                   constantRegisterMappingExact &&
                   samplerMappingExact &&
                   complete &&
                   cacheKey != 0 &&
                   pairSemanticHash != 0 &&
                   vertexRegisterSemanticsHash != 0 &&
                   pixelRegisterSemanticsHash != 0 &&
                   constantMappingCount == constantMappings.size() &&
                   samplerMappingCount == samplerMappings.size() &&
                   constantMappingHash != 0 &&
                   samplerMappingHash != 0 &&
                   planRevisionHash != 0 &&
                   semanticContractHash != 0;
        }
    };

    [[nodiscard]] ProgrammableShaderRegisterMappingPlanEvidence
    derive_programmable_shader_register_mapping_plan(
        const ProgrammableShaderPairSourceSemanticEvidence& sourceReceipt,
        const ProgrammableShaderRegisterSemantics& vertexSemantics,
        const ProgrammableShaderRegisterSemantics& pixelSemantics) noexcept;

    [[nodiscard]] ProgrammableShaderPairCacheIdentity
    seal_programmable_shader_pair_cache_identity(
        bool observationComplete,
        bool mixedPair,
        const ProgrammableShaderFunctionIdentity& vertexShader,
        const ProgrammableShaderFunctionIdentity& pixelShader) noexcept;

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
        bool hasSpecular = false;
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

    // R223 mirrors the R85 pixel compiler probe for the generated R93 vertex
    // source. The bytecode remains diagnostic-only and is never bound.
    struct FixedFunctionVertexShaderCompileProbe
    {
        bool attempted = false;
        bool succeeded = false;
        HRESULT result = E_FAIL;
        UINT bytecodeBytes = 0;
        std::uint64_t bytecodeHash = 0;
        UINT diagnosticsBytes = 0;
        std::uint64_t diagnosticsHash = 0;
    };

    [[nodiscard]] FixedFunctionVertexShaderCompileProbe
    compile_fixed_function_vertex_shader_prototype(
        const FixedFunctionVertexShaderPrototype& prototype) noexcept;

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
