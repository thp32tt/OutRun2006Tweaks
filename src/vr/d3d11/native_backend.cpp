#include "native_backend.hpp"

#include "pipeline_translation.hpp"
#include "triangle_fan_index_buffer.hpp"
#include "resource_translation.hpp"
#include "state_translation.hpp"
#include "surface_mirror.hpp"

#include <array>
#include <cstddef>
#include <cstring>
#include <d3dcompiler.h>
#include <dxgi1_2.h>
#include <limits>
#include <string>
#include <utility>

namespace outrun::vr::dx11 {
namespace {

bool same_luid(const LUID& a, const LUID& b) noexcept {
    return a.LowPart == b.LowPart && a.HighPart == b.HighPart;
}

std::uint64_t mix_readiness_snapshot_token(
    std::uint64_t token,
    std::uint64_t value) noexcept {
    token ^= value + 0x9e3779b97f4a7c15ull + (token << 6) + (token >> 2);
    return token;
}

std::uint64_t hash_observation_payload_bytes(
    const void* payload,
    UINT payloadBytes) noexcept {
    if (!payload || payloadBytes == 0)
        return 0;
    std::uint64_t hash = 1469598103934665603ull;
    const auto* bytes = static_cast<const unsigned char*>(payload);
    for (UINT index = 0; index < payloadBytes; ++index) {
        hash ^= static_cast<std::uint64_t>(bytes[index]);
        hash *= 1099511628211ull;
    }
    return hash == 0 ? 1 : hash;
}

std::uint64_t hash_transform_payload_bytes(
    const FixedFunctionTransformConstants& constants) noexcept {
    if (!constants.exact() || constants.payloadHash == 0)
        return 0;
    std::uint64_t hash = 1469598103934665603ull;
    const auto* bytes = reinterpret_cast<const unsigned char*>(
        constants.worldViewProjection.data());
    constexpr std::size_t kPayloadBytes = 16u * sizeof(float);
    for (std::size_t index = 0; index < kPayloadBytes; ++index) {
        hash ^= static_cast<std::uint64_t>(bytes[index]);
        hash *= 1099511628211ull;
    }
    return hash == constants.payloadHash ? hash : 0;
}

std::uint64_t hash_pipeline_input_layout_identity(
    const VertexInputLayoutTranslation& layout) noexcept {
    if (!layout.exact || layout.elementCount == 0 ||
        layout.elementCount > layout.elements.size() ||
        layout.stream0Stride == 0)
        return 0;

    std::uint64_t hash = 0xcbf29ce484222325ull;
    hash = mix_readiness_snapshot_token(hash, layout.elementCount);
    hash = mix_readiness_snapshot_token(hash, layout.stream0Stride);
    hash = mix_readiness_snapshot_token(hash, layout.declarationPath ? 1u : 0u);
    hash = mix_readiness_snapshot_token(hash, layout.fvfPath ? 1u : 0u);
    hash = mix_readiness_snapshot_token(hash, layout.fvfPending ? 1u : 0u);
    for (UINT index = 0; index < layout.elementCount; ++index) {
        const auto& element = layout.elements[index];
        if (!element.SemanticName || element.SemanticName[0] == '\0')
            return 0;
        for (const unsigned char* ch =
                 reinterpret_cast<const unsigned char*>(element.SemanticName);
             *ch != 0; ++ch)
            hash = mix_readiness_snapshot_token(hash, *ch);
        hash = mix_readiness_snapshot_token(hash, 0xffu);
        hash = mix_readiness_snapshot_token(hash, element.SemanticIndex);
        hash = mix_readiness_snapshot_token(
            hash, static_cast<std::uint32_t>(element.Format));
        hash = mix_readiness_snapshot_token(hash, element.InputSlot);
        hash = mix_readiness_snapshot_token(hash, element.AlignedByteOffset);
        hash = mix_readiness_snapshot_token(
            hash, static_cast<std::uint32_t>(element.InputSlotClass));
        hash = mix_readiness_snapshot_token(
            hash, element.InstanceDataStepRate);
    }
    return hash == 0 ? 1 : hash;
}

std::uint64_t hash_pipeline_render_state_identity(
    const PipelineTranslation& pipeline) noexcept {
    if (!pipeline.exact())
        return 0;

    std::uint64_t hash = 0xcbf29ce484222325ull;
    const auto mix = [&hash](std::uint64_t value) noexcept {
        hash = mix_readiness_snapshot_token(hash, value);
    };
    const auto mix_float = [&mix](float value) noexcept {
        std::uint32_t bits = 0;
        std::memcpy(&bits, &value, sizeof(bits));
        mix(bits);
    };
    const auto mix_stencil_face =
        [&mix](const D3D11_DEPTH_STENCILOP_DESC& face) noexcept {
            mix(static_cast<std::uint32_t>(face.StencilFailOp));
            mix(static_cast<std::uint32_t>(face.StencilDepthFailOp));
            mix(static_cast<std::uint32_t>(face.StencilPassOp));
            mix(static_cast<std::uint32_t>(face.StencilFunc));
        };

    mix(pipeline.blend.AlphaToCoverageEnable != FALSE ? 1u : 0u);
    mix(pipeline.blend.IndependentBlendEnable != FALSE ? 1u : 0u);
    for (const auto& rt : pipeline.blend.RenderTarget) {
        mix(rt.BlendEnable != FALSE ? 1u : 0u);
        mix(static_cast<std::uint32_t>(rt.SrcBlend));
        mix(static_cast<std::uint32_t>(rt.DestBlend));
        mix(static_cast<std::uint32_t>(rt.BlendOp));
        mix(static_cast<std::uint32_t>(rt.SrcBlendAlpha));
        mix(static_cast<std::uint32_t>(rt.DestBlendAlpha));
        mix(static_cast<std::uint32_t>(rt.BlendOpAlpha));
        mix(rt.RenderTargetWriteMask);
    }

    const auto& depth = pipeline.depth_stencil;
    mix(depth.DepthEnable != FALSE ? 1u : 0u);
    mix(static_cast<std::uint32_t>(depth.DepthWriteMask));
    mix(static_cast<std::uint32_t>(depth.DepthFunc));
    mix(depth.StencilEnable != FALSE ? 1u : 0u);
    mix(depth.StencilReadMask);
    mix(depth.StencilWriteMask);
    mix_stencil_face(depth.FrontFace);
    mix_stencil_face(depth.BackFace);

    const auto& raster = pipeline.rasterizer;
    mix(static_cast<std::uint32_t>(raster.FillMode));
    mix(static_cast<std::uint32_t>(raster.CullMode));
    mix(raster.FrontCounterClockwise != FALSE ? 1u : 0u);
    mix(static_cast<std::uint32_t>(raster.DepthBias));
    mix_float(raster.DepthBiasClamp);
    mix_float(raster.SlopeScaledDepthBias);
    mix(raster.DepthClipEnable != FALSE ? 1u : 0u);
    mix(raster.ScissorEnable != FALSE ? 1u : 0u);
    mix(raster.MultisampleEnable != FALSE ? 1u : 0u);
    mix(raster.AntialiasedLineEnable != FALSE ? 1u : 0u);
    mix(pipeline.stencil_ref);

    return hash == 0 ? 1 : hash;
}

bool texture_uncompressed_row_bytes(
    D3DFORMAT format,
    UINT width,
    UINT& rowBytes) noexcept {

    if (width == 0)
        return false;

    UINT bytesPerPixel = 0;
    switch (format) {
    case D3DFMT_A8R8G8B8:
    case D3DFMT_X8R8G8B8:
    case D3DFMT_A8B8G8R8:
        bytesPerPixel = 4;
        break;
    case D3DFMT_R5G6B5:
    case D3DFMT_A1R5G5B5:
        bytesPerPixel = 2;
        break;
    case D3DFMT_A8:
        bytesPerPixel = 1;
        break;
    default:
        return false;
    }

    if (width > (std::numeric_limits<UINT>::max)() / bytesPerPixel)
        return false;
    rowBytes = width * bytesPerPixel;
    return true;
}

bool find_adapter(
    const LUID& wanted,
    Microsoft::WRL::ComPtr<IDXGIAdapter1>& adapter) noexcept {

    Microsoft::WRL::ComPtr<IDXGIFactory1> factory;
    if (FAILED(CreateDXGIFactory1(
            __uuidof(IDXGIFactory1),
            reinterpret_cast<void**>(factory.ReleaseAndGetAddressOf()))))
        return false;

    for (UINT index = 0;; ++index) {
        Microsoft::WRL::ComPtr<IDXGIAdapter1> candidate;
        const HRESULT hr = factory->EnumAdapters1(
            index, candidate.ReleaseAndGetAddressOf());
        if (hr == DXGI_ERROR_NOT_FOUND) break;
        if (FAILED(hr)) return false;

        DXGI_ADAPTER_DESC1 desc{};
        if (SUCCEEDED(candidate->GetDesc1(&desc)) &&
            same_luid(desc.AdapterLuid, wanted)) {
            adapter = std::move(candidate);
            return true;
        }
    }
    return false;
}

bool read_device_luid(
    ID3D11Device* device,
    LUID& luid) noexcept {

    if (!device) return false;
    Microsoft::WRL::ComPtr<IDXGIDevice> dxgiDevice;
    if (FAILED(device->QueryInterface(
            __uuidof(IDXGIDevice),
            reinterpret_cast<void**>(dxgiDevice.ReleaseAndGetAddressOf()))))
        return false;

    Microsoft::WRL::ComPtr<IDXGIAdapter> adapter;
    if (FAILED(dxgiDevice->GetAdapter(adapter.ReleaseAndGetAddressOf())) ||
        !adapter)
        return false;

    DXGI_ADAPTER_DESC desc{};
    if (FAILED(adapter->GetDesc(&desc)))
        return false;

    luid = desc.AdapterLuid;
    return true;
}

bool compile_shader_source(
    const std::string& source,
    const char* source_name,
    const char* target,
    Microsoft::WRL::ComPtr<ID3DBlob>& bytecode) noexcept {

    bytecode.Reset();
    if (source.empty() || !source_name || !target)
        return false;

    Microsoft::WRL::ComPtr<ID3DBlob> diagnostics;
    const HRESULT hr = D3DCompile(
        source.data(), source.size(), source_name,
        nullptr, nullptr, "main", target,
        D3DCOMPILE_ENABLE_STRICTNESS | D3DCOMPILE_OPTIMIZATION_LEVEL3,
        0, bytecode.ReleaseAndGetAddressOf(),
        diagnostics.ReleaseAndGetAddressOf());
    return SUCCEEDED(hr) && bytecode;
}

std::uint64_t r283_materializer_revision_hash() noexcept {
    static constexpr char kRevision[] =
        "R283_D3D9_SM3_DCL_MOV_HLSL_MATERIALIZER_V1";
    return hash_observation_payload_bytes(
        kRevision, static_cast<UINT>(sizeof(kRevision) - 1u));
}

std::uint64_t r283_semantic_subset_contract_hash() noexcept {
    static constexpr char kContract[] =
        "R283_R281_R282_R276_SM3_DCL_MOV_DXBC_PROVENANCE_V1";
    return hash_observation_payload_bytes(
        kContract, static_cast<UINT>(sizeof(kContract) - 1u));
}

D3DSHADER_PARAM_REGISTER_TYPE r283_decode_register_type(DWORD token) noexcept {
    const DWORD rawType =
        ((token & D3DSP_REGTYPE_MASK) >> D3DSP_REGTYPE_SHIFT) |
        ((token & D3DSP_REGTYPE_MASK2) >> D3DSP_REGTYPE_SHIFT2);
    if (rawType > static_cast<DWORD>(D3DSPR_PREDICATE))
        return D3DSPR_FORCE_DWORD;
    return static_cast<D3DSHADER_PARAM_REGISTER_TYPE>(rawType);
}

bool r283_hlsl_semantic(
    const ProgrammableShaderInterfaceSemantic& semantic,
    bool vertexStage,
    bool output,
    std::string& label) {
    label.clear();
    switch (semantic.usage) {
    case D3DDECLUSAGE_POSITION:
        if (output && vertexStage) {
            if (semantic.usageIndex != 0u)
                return false;
            label = "SV_Position";
            return true;
        }
        if (!vertexStage)
            return false;
        label = "POSITION" + std::to_string(semantic.usageIndex);
        return true;
    case D3DDECLUSAGE_TEXCOORD:
        label = "TEXCOORD" + std::to_string(semantic.usageIndex);
        return true;
    case D3DDECLUSAGE_COLOR:
        label = "COLOR" + std::to_string(semantic.usageIndex);
        return true;
    case D3DDECLUSAGE_NORMAL:
        if (!vertexStage || output)
            return false;
        label = "NORMAL" + std::to_string(semantic.usageIndex);
        return true;
    default:
        return false;
    }
}

bool build_r283_sm3_mov_shader_source(
    const ProgrammableShaderFunctionSourceEvidence& evidence,
    bool vertexStage,
    std::string& translated) noexcept {
    translated.clear();
    try {
        if (!evidence.exact() ||
            evidence.vertexStage != vertexStage ||
            evidence.versionToken !=
                (vertexStage ? D3DVS_VERSION(3, 0) : D3DPS_VERSION(3, 0)))
            return false;

        const auto decode =
            decode_programmable_shader_instruction_stream(evidence);
        const auto registers =
            decode_programmable_shader_register_semantics(decode);
        const auto interfaceSemantics =
            decode_programmable_shader_interface_semantics(
                decode, registers);
        if (!decode.exact() ||
            !registers.exact() ||
            !interfaceSemantics.exact())
            return false;

        std::vector<ProgrammableShaderInterfaceSemantic> inputs;
        std::vector<ProgrammableShaderInterfaceSemantic> outputs;
        for (const auto& semantic : interfaceSemantics.semantics) {
            if (semantic.writeMask != D3DSP_WRITEMASK_ALL)
                return false;
            if (semantic.input)
                inputs.push_back(semantic);
            else if (semantic.output)
                outputs.push_back(semantic);
            else
                return false;
        }

        if (inputs.empty() || inputs.size() > 8u)
            return false;
        if (vertexStage) {
            if (outputs.empty() || outputs.size() > 8u)
                return false;
        } else if (!outputs.empty() || inputs.size() != 1u) {
            return false;
        }

        struct MovBinding {
            UINT destinationRegister{};
            UINT sourceRegister{};
        };
        std::vector<MovBinding> moves;
        for (const auto& instruction : decode.instructions) {
            if (instruction.opcode == static_cast<DWORD>(D3DSIO_DCL))
                continue;
            if (instruction.opcode != static_cast<DWORD>(D3DSIO_MOV) ||
                instruction.operandTokens.size() != 2u)
                return false;

            const DWORD destination = instruction.operandTokens[0];
            const DWORD source = instruction.operandTokens[1];
            if ((destination & 0x80000000u) == 0u ||
                (source & 0x80000000u) == 0u ||
                (destination & D3DSP_WRITEMASK_ALL) != D3DSP_WRITEMASK_ALL ||
                (destination & D3DSP_DSTMOD_MASK) != 0u ||
                (destination & D3DSP_DSTSHIFT_MASK) != 0u ||
                (destination & D3DSHADER_ADDRESSMODE_MASK) != 0u ||
                (source & D3DSP_SWIZZLE_MASK) != D3DSP_NOSWIZZLE ||
                (source & D3DSP_SRCMOD_MASK) != 0u ||
                (source & D3DSHADER_ADDRESSMODE_MASK) != 0u)
                return false;

            const auto destinationType =
                r283_decode_register_type(destination);
            const auto sourceType = r283_decode_register_type(source);
            const UINT destinationRegister =
                static_cast<UINT>(destination & D3DSP_REGNUM_MASK);
            const UINT sourceRegister =
                static_cast<UINT>(source & D3DSP_REGNUM_MASK);
            if (sourceType != D3DSPR_INPUT)
                return false;

            bool sourceDeclared = false;
            for (const auto& semantic : inputs) {
                if (semantic.registerType == D3DSPR_INPUT &&
                    semantic.registerIndex == sourceRegister) {
                    sourceDeclared = true;
                    break;
                }
            }
            if (!sourceDeclared)
                return false;

            if (vertexStage) {
                if (destinationType != D3DSPR_OUTPUT)
                    return false;
                bool destinationDeclared = false;
                for (const auto& semantic : outputs) {
                    if (semantic.registerType == D3DSPR_OUTPUT &&
                        semantic.registerIndex == destinationRegister) {
                        destinationDeclared = true;
                        break;
                    }
                }
                if (!destinationDeclared)
                    return false;
                for (const auto& existing : moves) {
                    if (existing.destinationRegister == destinationRegister)
                        return false;
                }
            } else {
                if (destinationType != D3DSPR_COLOROUT ||
                    destinationRegister != 0u ||
                    !moves.empty())
                    return false;
            }
            moves.push_back({ destinationRegister, sourceRegister });
        }

        if (vertexStage) {
            if (moves.size() != outputs.size())
                return false;
            for (const auto& semantic : outputs) {
                bool assigned = false;
                for (const auto& move : moves) {
                    if (move.destinationRegister == semantic.registerIndex) {
                        assigned = true;
                        break;
                    }
                }
                if (!assigned)
                    return false;
            }
        } else if (moves.size() != 1u) {
            return false;
        }

        translated = "struct R283Input {\n";
        for (const auto& semantic : inputs) {
            std::string label;
            if (!r283_hlsl_semantic(
                    semantic, vertexStage, false, label))
                return false;
            translated += "    float4 r" +
                std::to_string(semantic.registerIndex) +
                " : " + label + ";\n";
        }
        translated += "};\n";

        if (vertexStage) {
            translated += "struct R283Output {\n";
            for (const auto& semantic : outputs) {
                std::string label;
                if (!r283_hlsl_semantic(
                        semantic, true, true, label))
                    return false;
                translated += "    float4 r" +
                    std::to_string(semantic.registerIndex) +
                    " : " + label + ";\n";
            }
            translated += "};\n";
            translated += "R283Output main(R283Input input) {\n";
            translated += "    R283Output output = (R283Output)0;\n";
            for (const auto& move : moves) {
                translated += "    output.r" +
                    std::to_string(move.destinationRegister) +
                    " = input.r" + std::to_string(move.sourceRegister) +
                    ";\n";
            }
            translated += "    return output;\n}\n";
        } else {
            translated += "float4 main(R283Input input) : SV_Target0 {\n";
            translated += "    return input.r" +
                std::to_string(moves.front().sourceRegister) + ";\n}\n";
        }
        return !translated.empty();
    } catch (...) {
        translated.clear();
        return false;
    }
}

bool r283_dxbc_payload(const std::vector<std::uint8_t>& bytes) noexcept {
    return bytes.size() >= 4u &&
        bytes[0] == static_cast<std::uint8_t>('D') &&
        bytes[1] == static_cast<std::uint8_t>('X') &&
        bytes[2] == static_cast<std::uint8_t>('B') &&
        bytes[3] == static_cast<std::uint8_t>('C');
}

std::uint64_t r283_materialized_artifact_identity(
    std::uint64_t receiptIdentity,
    std::uint64_t compileContractIdentity,
    std::uint64_t translatedSourceHash,
    std::uint64_t targetBytecodeHash,
    UINT targetBytecodeBytes,
    std::uint64_t stageTag) noexcept {
    if (receiptIdentity == 0 ||
        compileContractIdentity == 0 ||
        translatedSourceHash == 0 ||
        targetBytecodeHash == 0 ||
        targetBytecodeBytes == 0)
        return 0;
    std::uint64_t identity = 0xcbf29ce484222325ull;
    identity = mix_readiness_snapshot_token(identity, receiptIdentity);
    identity = mix_readiness_snapshot_token(
        identity, compileContractIdentity);
    identity = mix_readiness_snapshot_token(
        identity, translatedSourceHash);
    identity = mix_readiness_snapshot_token(
        identity, targetBytecodeHash);
    identity = mix_readiness_snapshot_token(
        identity, targetBytecodeBytes);
    identity = mix_readiness_snapshot_token(identity, stageTag);
    return identity == 0 ? 1 : identity;
}

std::uint64_t r283_materialization_snapshot_token(
    const NativeProgrammableShaderTargetBytecodeMaterializationEvidence&
        materialization) noexcept {
    if (!materialization.reviewReady)
        return 0;
    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(token, materialization.cacheKey);
    token = mix_readiness_snapshot_token(
        token, materialization.targetVertexBytecodeReceiptIdentity);
    token = mix_readiness_snapshot_token(
        token, materialization.targetPixelBytecodeReceiptIdentity);
    token = mix_readiness_snapshot_token(
        token, materialization.vertexCompileContractIdentity);
    token = mix_readiness_snapshot_token(
        token, materialization.pixelCompileContractIdentity);
    token = mix_readiness_snapshot_token(
        token, materialization.vertexTranslatedSourceHash);
    token = mix_readiness_snapshot_token(
        token, materialization.pixelTranslatedSourceHash);
    token = mix_readiness_snapshot_token(
        token, materialization.vertexTargetBytecodeHash);
    token = mix_readiness_snapshot_token(
        token, materialization.pixelTargetBytecodeHash);
    token = mix_readiness_snapshot_token(
        token, materialization.vertexMaterializedArtifactIdentity);
    token = mix_readiness_snapshot_token(
        token, materialization.pixelMaterializedArtifactIdentity);
    token = mix_readiness_snapshot_token(
        token, materialization.materializerRevisionHash);
    token = mix_readiness_snapshot_token(
        token, materialization.semanticSubsetContractHash);
    token = mix_readiness_snapshot_token(
        token, materialization.translatedArtifactReceiptSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, materialization.targetMaterializationContractSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, materialization.translationPlanSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, materialization.targetBytecodeMaterialized ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, materialization.objectCreationAuthorized ? 1u : 0u);
    token = mix_readiness_snapshot_token(token, 0x283u);
    return token == 0 ? 1 : token;
}

std::uint64_t r284_object_materializer_revision_hash() noexcept {
    static constexpr char kRevision[] =
        "R284_R283_DXBC_R240_R241_R242_OBJECT_MATERIALIZER_V1";
    return hash_observation_payload_bytes(
        kRevision, static_cast<UINT>(sizeof(kRevision) - 1u));
}

std::uint64_t r284_object_materialization_snapshot_token(
    const NativeProgrammableShaderObjectMaterializationEvidence&
        materialization) noexcept {
    if (!materialization.reviewReady)
        return 0;
    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(token, materialization.cacheKey);
    token = mix_readiness_snapshot_token(
        token, materialization.targetVertexBytecodeHash);
    token = mix_readiness_snapshot_token(
        token, materialization.targetPixelBytecodeHash);
    token = mix_readiness_snapshot_token(
        token, materialization.vertexMaterializedArtifactIdentity);
    token = mix_readiness_snapshot_token(
        token, materialization.pixelMaterializedArtifactIdentity);
    token = mix_readiness_snapshot_token(
        token, materialization.ownerGeneration);
    token = mix_readiness_snapshot_token(
        token, materialization.slotGeneration);
    token = mix_readiness_snapshot_token(
        token, materialization.translationObjectReceiptGeneration);
    token = mix_readiness_snapshot_token(
        token, materialization.objectMaterializerRevisionHash);
    token = mix_readiness_snapshot_token(
        token, materialization.objectPrerequisiteSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, materialization.creationHandoffSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, materialization.targetBytecodeMaterializationSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, materialization.cacheSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, materialization.slotSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, materialization.translationObjectSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, materialization.translationObjectReceiptReady ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, materialization.objectBindingAuthorized ? 1u : 0u);
    token = mix_readiness_snapshot_token(token, 0x284u);
    return token == 0 ? 1 : token;
}

std::uint64_t r285_backend_semantic_handoff_snapshot_token(
    const NativeProgrammableShaderBackendSemanticHandoffEvidence&
        handoff) noexcept {
    if (!handoff.reviewReady)
        return 0;
    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(token, handoff.cacheKey);
    token = mix_readiness_snapshot_token(
        token, handoff.backendOwnerGeneration);
    token = mix_readiness_snapshot_token(
        token, handoff.cacheOwnerGeneration);
    token = mix_readiness_snapshot_token(
        token, handoff.objectMaterializationSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, handoff.cacheSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, handoff.slotSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, handoff.translationObjectSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, handoff.translatedSemanticReceiptSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, handoff.translationObjectReady ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, handoff.translatedSemanticReceiptReady ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, handoff.objectBindingAuthorized ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, handoff.nativeDrawPathActivationAllowed ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, handoff.drawDispatchAuthorized ? 1u : 0u);
    token = mix_readiness_snapshot_token(token, 0x285u);
    return token == 0 ? 1 : token;
}


std::uint64_t r286_production_observation_snapshot_token(
    const NativeProgrammableShaderProductionObservationEvidence&
        observation) noexcept {
    if (!observation.reviewReady)
        return 0;
    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(token, observation.cacheKey);
    token = mix_readiness_snapshot_token(
        token, observation.backendOwnerGeneration);
    token = mix_readiness_snapshot_token(
        token, observation.objectPrerequisiteSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, observation.creationHandoffSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, observation.targetBytecodeMaterializationSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, observation.sourceMappingHandoffSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, observation.translationPlanSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, observation.semanticHandoffSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, observation.semanticHandoffReady ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.semanticHandoffSnapshotMatches ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.objectBindingAuthorized ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.nativeDrawPathActivationAllowed ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.drawDispatchAuthorized ? 1u : 0u);
    token = mix_readiness_snapshot_token(token, 0x286u);
    return token == 0 ? 1 : token;
}

std::uint64_t r288_programmable_translation_admission_snapshot_token(
    const NativeProgrammableShaderTranslationAdmissionEvidence&
        admission) noexcept {
    if (!admission.reviewReady)
        return 0;
    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(token, admission.cacheKey);
    token = mix_readiness_snapshot_token(
        token, admission.backendOwnerGeneration);
    token = mix_readiness_snapshot_token(
        token, admission.productionObservationSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, admission.translatedSemanticReceiptSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, admission.productionObservationReady ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, admission.productionObservationSnapshotMatches ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, admission.translatedSemanticReceiptReady ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, admission.translatedSemanticReceiptSnapshotMatches ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, admission.cacheIdentityMatches ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, admission.translationObjectReady ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, admission.objectBindingAuthorized ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, admission.nativeDrawPathActivationAllowed ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, admission.drawDispatchAuthorized ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, admission.boundaryPreserved ? 1u : 0u);
    token = mix_readiness_snapshot_token(token, 0x288u);
    return token == 0 ? 1 : token;
}

std::uint64_t r289_programmable_production_semantic_review_snapshot_token(
    const NativeProgrammableShaderProductionSemanticReviewEvidence&
        review) noexcept {
    if (!review.reviewReady)
        return 0;
    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(token, review.cacheKey);
    token = mix_readiness_snapshot_token(
        token, review.backendOwnerGeneration);
    token = mix_readiness_snapshot_token(
        token, review.admissionSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, review.targetBytecodeMaterializationSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, review.cacheSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, review.slotSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, review.translationObjectSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, review.inputLayoutSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, review.semanticTranslationSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, review.inputLayoutReused ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, review.semanticTranslationReady ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, review.semanticTranslationSnapshotMatches ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, review.objectBindingAuthorized ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, review.nativeDrawPathActivationAllowed ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, review.drawDispatchAuthorized ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, review.boundaryPreserved ? 1u : 0u);
    token = mix_readiness_snapshot_token(token, 0x289u);
    return token == 0 ? 1 : token;
}

// R303 reconstructs the exact R262 full-resource review payload before the
// production R292 activation-prerequisite boundary may trust its stored token.
std::uint64_t recompute_programmable_output_resource_behavior_payload_snapshot(
    const NativeProgrammableShaderOutputResourceBehaviorReadiness&
        resourceBehavior) noexcept {
    if (resourceBehavior.kind ==
        NativeProgrammableShaderDrawCandidateKind::None)
        return 0;

    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(
        token, static_cast<std::uint32_t>(resourceBehavior.kind));
    token = mix_readiness_snapshot_token(
        token, resourceBehavior.indexed ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, resourceBehavior.sourceRevalidationSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, resourceBehavior.textureBehaviorSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, resourceBehavior.texturePayloadSnapshotMatches ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, resourceBehavior.surfacePairSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, resourceBehavior.surfaceBindingSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, resourceBehavior.missingResourceScopeMask);
    token = mix_readiness_snapshot_token(token, 0x262u);
    return token == 0 ? 1 : token;
}

// R305 seals the complete copied R259/R292 observation payload at the
// validation boundary used by production census. The stored R259/R292 review
// tokens intentionally remain their original domains; this independent payload
// identity detects mutation of fields that those historical tokens did not hash.
std::uint64_t r305_programmable_activation_prerequisite_payload_snapshot_token(
    const NativeProgrammableShaderActivationPrerequisiteHandoff&
        prerequisites) noexcept {
    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(token, prerequisites.inputValid ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.sourceRevalidationReady ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.sourceRevalidationSnapshotMatches ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.sourceRevalidationPayloadSnapshotMatches ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.sourceIdentityMatches ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.resourceBehaviorReviewReady ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.resourceBehaviorSnapshotMatches ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.resourceBehaviorPayloadSnapshotMatches ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.resourceBehaviorGeometryProofPresent ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.resourceBehaviorTextureProofPresent ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.resourceBehaviorOutputProofPresent ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.resourceBehaviorCoverageComplete ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.inputLayoutOwnershipReady ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.inputLayoutSnapshotMatches ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.shaderTranslationReviewReady ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.shaderTranslationSnapshotMatches ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.resourceBehaviorProofPresent ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.inputLayoutProofPresent ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.shaderTranslationProofPresent ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.sourceIdentityProofPresent ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.activationPrerequisitesSatisfied ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.diagnosticOnly ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.nativeDrawPathActivationAllowed ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.drawDispatchAuthorized ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.boundaryPreserved ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.reviewReady ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, static_cast<std::uint64_t>(prerequisites.kind));
    token = mix_readiness_snapshot_token(token, prerequisites.indexed ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, prerequisites.missingPrerequisiteMask);
    token = mix_readiness_snapshot_token(token, prerequisites.cacheKey);
    token = mix_readiness_snapshot_token(
        token, prerequisites.sourceRevalidationSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, prerequisites.resourceBehaviorSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, prerequisites.inputLayoutSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, prerequisites.shaderTranslationSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, prerequisites.reviewSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, prerequisites.activationSnapshotToken);
    token = mix_readiness_snapshot_token(token, 0x305259u);
    return token == 0 ? 1 : token;
}

std::uint64_t r305_programmable_production_activation_payload_snapshot_token(
    const NativeProgrammableShaderProductionActivationPrerequisiteEvidence&
        observation) noexcept {
    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(token, observation.inputValid ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.productionSemanticReviewReady ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.productionSemanticReviewSnapshotMatches ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.sourceRevalidationReady ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.sourceRevalidationSnapshotMatches ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.resourceBehaviorReady ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.resourceBehaviorSnapshotMatches ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.resourceBehaviorPayloadSnapshotMatches ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.prerequisiteHandoffReady ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.prerequisiteHandoffSnapshotMatches ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.staticPrerequisitesSatisfied ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.objectBindingAuthorized ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.nativeDrawPathActivationAllowed ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.drawDispatchAuthorized ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.diagnosticOnly ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.boundaryPreserved ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.reviewReady ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.missingPrerequisiteMask);
    token = mix_readiness_snapshot_token(token, observation.cacheKey);
    token = mix_readiness_snapshot_token(
        token, observation.productionSemanticReviewSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, observation.sourceRevalidationSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, observation.resourceBehaviorSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, observation.prerequisiteHandoffSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, observation.reviewSnapshotToken);
    token = mix_readiness_snapshot_token(
        token,
        r305_programmable_activation_prerequisite_payload_snapshot_token(
            observation.prerequisites));
    token = mix_readiness_snapshot_token(token, 0x305292u);
    return token == 0 ? 1 : token;
}

std::uint64_t r292_programmable_production_activation_prerequisite_snapshot_token(
    const NativeProgrammableShaderProductionActivationPrerequisiteEvidence&
        observation) noexcept {
    if (!observation.reviewReady)
        return 0;
    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(token, observation.cacheKey);
    token = mix_readiness_snapshot_token(
        token, observation.productionSemanticReviewSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, observation.sourceRevalidationSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, observation.resourceBehaviorSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, observation.resourceBehaviorPayloadSnapshotMatches ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.prerequisiteHandoffSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, observation.missingPrerequisiteMask);
    token = mix_readiness_snapshot_token(
        token, observation.staticPrerequisitesSatisfied ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.objectBindingAuthorized ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.nativeDrawPathActivationAllowed ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.drawDispatchAuthorized ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, observation.boundaryPreserved ? 1u : 0u);
    token = mix_readiness_snapshot_token(token, 0x292u);
    return token == 0 ? 1 : token;
}

HRESULT create_device(
    IDXGIAdapter* adapter,
    UINT flags,
    Microsoft::WRL::ComPtr<ID3D11Device>& device,
    Microsoft::WRL::ComPtr<ID3D11DeviceContext>& context,
    D3D_FEATURE_LEVEL& feature_level) noexcept {

    constexpr std::array<D3D_FEATURE_LEVEL, 4> kFeatureLevels = {
        D3D_FEATURE_LEVEL_11_1,
        D3D_FEATURE_LEVEL_11_0,
        D3D_FEATURE_LEVEL_10_1,
        D3D_FEATURE_LEVEL_10_0,
    };

    const D3D_DRIVER_TYPE driverType =
        adapter ? D3D_DRIVER_TYPE_UNKNOWN : D3D_DRIVER_TYPE_HARDWARE;

    HRESULT hr = D3D11CreateDevice(
        adapter, driverType, nullptr, flags,
        kFeatureLevels.data(), static_cast<UINT>(kFeatureLevels.size()),
        D3D11_SDK_VERSION, device.ReleaseAndGetAddressOf(),
        &feature_level, context.ReleaseAndGetAddressOf());

    if (hr == E_INVALIDARG) {
        constexpr std::array<D3D_FEATURE_LEVEL, 3> kFallbackLevels = {
            D3D_FEATURE_LEVEL_11_0,
            D3D_FEATURE_LEVEL_10_1,
            D3D_FEATURE_LEVEL_10_0,
        };
        hr = D3D11CreateDevice(
            adapter, driverType, nullptr, flags,
            kFallbackLevels.data(), static_cast<UINT>(kFallbackLevels.size()),
            D3D11_SDK_VERSION, device.ReleaseAndGetAddressOf(),
            &feature_level, context.ReleaseAndGetAddressOf());
    }

    return hr;
}

} // namespace

bool NativeFixedFunctionTransformBuffer::initialize(
    ID3D11Device* device) noexcept {

    shutdown();
    if (!device) return false;

    D3D11_BUFFER_DESC desc{};
    desc.ByteWidth = static_cast<UINT>(16u * sizeof(float));
    desc.Usage = D3D11_USAGE_DYNAMIC;
    desc.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
    desc.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;

    Microsoft::WRL::ComPtr<ID3D11Buffer> buffer;
    if (FAILED(device->CreateBuffer(
            &desc, nullptr, buffer.ReleaseAndGetAddressOf())) ||
        !buffer)
        return false;

    device_ = device;
    buffer_ = std::move(buffer);
    upload_generation_ = 0;
    return true;
}

bool NativeFixedFunctionTransformBuffer::upload_and_bind(
    ID3D11DeviceContext* context,
    const FixedFunctionTransformConstants& constants) noexcept {

    // R151: deferred contexts record b0 updates; they cannot establish a
    // live immediate-context WVP upload/binding receipt.
    if (!ready() || !context || !constants.exact() ||
        context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE)
        return false;

    const auto payloadHash = hash_transform_payload_bytes(constants);
    if (payloadHash == 0)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    if (!contextDevice || contextDevice.Get() != device_.Get())
        return false;

    D3D11_MAPPED_SUBRESOURCE mapped{};
    if (FAILED(context->Map(
            buffer_.Get(), 0, D3D11_MAP_WRITE_DISCARD, 0, &mapped)) ||
        !mapped.pData)
        return false;

    constexpr std::size_t kTransformBytes = 16u * sizeof(float);
    static_assert(kTransformBytes == 64u);
    std::memcpy(
        mapped.pData,
        constants.worldViewProjection.data(),
        kTransformBytes);
    context->Unmap(buffer_.Get(), 0);

    ID3D11Buffer* buffer = buffer_.Get();
    context->VSSetConstantBuffers(0, 1, &buffer);
    Microsoft::WRL::ComPtr<ID3D11Buffer> observedBuffer;
    context->VSGetConstantBuffers(0, 1, observedBuffer.ReleaseAndGetAddressOf());
    if (observedBuffer.Get() != buffer_.Get())
        return false;
    payload_hash_ = payloadHash;
    ++upload_generation_;
    if (upload_generation_ == 0)
        ++upload_generation_;
    return true;
}

NativeFixedFunctionTransformBindingReadiness
NativeFixedFunctionTransformBuffer::binding_readiness(
    ID3D11DeviceContext* context,
    const FixedFunctionTransformConstants& constants) const noexcept {
    NativeFixedFunctionTransformBindingReadiness out{};
    const auto payloadHash = hash_transform_payload_bytes(constants);
    out.payloadHash = payloadHash;
    out.uploadGeneration = upload_generation_;
    out.inputValid =
        context != nullptr &&
        context->GetType() == D3D11_DEVICE_CONTEXT_IMMEDIATE &&
        payloadHash != 0;
    out.ownerReady = ready();
    out.payloadMatches = payloadHash != 0 && payload_hash_ == payloadHash;
    out.uploadPresent = upload_generation_ != 0 && payload_hash_ != 0;
    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    if (context)
        context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    out.contextMatches =
        contextDevice && device_ && contextDevice.Get() == device_.Get();
    if (out.inputValid && out.ownerReady && out.contextMatches) {
        Microsoft::WRL::ComPtr<ID3D11Buffer> observedBuffer;
        context->VSGetConstantBuffers(
            0, 1, observedBuffer.ReleaseAndGetAddressOf());
        out.boundExact = observedBuffer.Get() == buffer_.Get();
    }
    out.ready =
        out.inputValid && out.ownerReady && out.contextMatches &&
        out.payloadMatches && out.boundExact && out.uploadPresent;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(this)));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(device_.Get())));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(buffer_.Get())));
        token = mix_readiness_snapshot_token(token, out.uploadGeneration);
        token = mix_readiness_snapshot_token(token, out.payloadHash);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeFixedFunctionTransformBuffer::validate_binding_snapshot(
    ID3D11DeviceContext* context,
    const FixedFunctionTransformConstants& constants,
    std::uint64_t snapshotToken) const noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = binding_readiness(context, constants);
    return current.ready && current.snapshotToken == snapshotToken;
}

void NativeFixedFunctionTransformBuffer::shutdown() noexcept {
    buffer_.Reset();
    device_.Reset();
    upload_generation_ = 0;
    payload_hash_ = 0;
}

bool NativeFixedFunctionSamplerState::initialize(
    ID3D11Device* device,
    const FixedFunctionStageState& stage) noexcept {

    shutdown();
    if (!device)
        return false;

    const auto translation = translate_fixed_function_sampler(stage);
    if (!translation.exact)
        return false;

    Microsoft::WRL::ComPtr<ID3D11SamplerState> sampler;
    if (FAILED(device->CreateSamplerState(
            &translation.desc, sampler.ReleaseAndGetAddressOf())) ||
        !sampler)
        return false;

    device_ = device;
    sampler_ = std::move(sampler);
    return true;
}

void NativeFixedFunctionSamplerState::shutdown() noexcept {
    sampler_.Reset();
    device_.Reset();
}

bool NativeFixedFunctionTextureView::initialize(
    ID3D11Device* device,
    ID3D11Texture2D* texture,
    D3DFORMAT sourceFormat,
    D3DPOOL sourcePool,
    DWORD sourceUsage) noexcept {

    shutdown();
    if (!device || !texture)
        return false;

    const auto format = translate_resource_format(
        sourceFormat, ResourceRole::Texture);
    const auto behavior = translate_resource_behavior(
        ResourceRole::Texture, sourcePool, sourceUsage);
    if (!format.exact || !behavior.descriptorExact ||
        behavior.requiresCpuShadow ||
        (behavior.bindFlags & D3D11_BIND_SHADER_RESOURCE) == 0)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> textureDevice;
    texture->GetDevice(textureDevice.ReleaseAndGetAddressOf());
    if (!textureDevice || textureDevice.Get() != device)
        return false;

    D3D11_TEXTURE2D_DESC desc{};
    texture->GetDesc(&desc);
    if (desc.Width == 0 || desc.Height == 0 || desc.MipLevels == 0 ||
        desc.ArraySize != 1 || desc.SampleDesc.Count != 1 ||
        desc.Format != format.format || desc.Usage != behavior.usage ||
        (desc.BindFlags & behavior.bindFlags) != behavior.bindFlags ||
        desc.CPUAccessFlags != behavior.cpuAccessFlags ||
        (desc.MiscFlags & D3D11_RESOURCE_MISC_TEXTURECUBE) != 0)
        return false;

    D3D11_SHADER_RESOURCE_VIEW_DESC srvDesc{};
    srvDesc.Format = desc.Format;
    srvDesc.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D;
    srvDesc.Texture2D.MostDetailedMip = 0;
    srvDesc.Texture2D.MipLevels = desc.MipLevels;

    Microsoft::WRL::ComPtr<ID3D11ShaderResourceView> srv;
    if (FAILED(device->CreateShaderResourceView(
            texture, &srvDesc, srv.ReleaseAndGetAddressOf())) ||
        !srv)
        return false;

    device_ = device;
    texture_ = texture;
    srv_ = std::move(srv);
    source_format_ = sourceFormat;
    source_pool_ = sourcePool;
    source_usage_ = sourceUsage;
    source_metadata_valid_ = true;
    upload_generation_ = 0;
    return true;
}

bool NativeFixedFunctionTextureView::upload_full_discard(
    ID3D11DeviceContext* context,
    const void* source,
    UINT sourceRowPitch,
    UINT sourceRows) noexcept {

    // R153: deferred Map/Unmap records a command list, not a live
    // immediate-context texture upload. Never advance content generation
    // on a deferred context even when it belongs to the same device.
    if (!ready() || !context || !source ||
        context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE ||
        sourceRowPitch == 0 || sourceRows == 0)
        return false;

    const auto mutation = translate_texture_mutation(
        source_pool_, source_usage_, D3DLOCK_DISCARD, true);
    if (!mutation.planExact ||
        mutation.kind != TextureMutationUpdateKind::DynamicMapWriteDiscard ||
        mutation.mapType != D3D11_MAP_WRITE_DISCARD)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    if (!contextDevice || contextDevice.Get() != device_.Get())
        return false;

    D3D11_TEXTURE2D_DESC desc{};
    texture_->GetDesc(&desc);
    if (desc.MipLevels != 1 || desc.ArraySize != 1 ||
        desc.SampleDesc.Count != 1 ||
        desc.Usage != D3D11_USAGE_DYNAMIC ||
        desc.CPUAccessFlags != D3D11_CPU_ACCESS_WRITE)
        return false;

    UINT rowBytes = 0;
    if (!texture_uncompressed_row_bytes(source_format_, desc.Width, rowBytes) ||
        sourceRows != desc.Height ||
        sourceRowPitch < rowBytes)
        return false;

    D3D11_MAPPED_SUBRESOURCE mapped{};
    if (FAILED(context->Map(
            texture_.Get(), 0, mutation.mapType, 0, &mapped)) ||
        !mapped.pData)
        return false;

    if (mapped.RowPitch < rowBytes) {
        context->Unmap(texture_.Get(), 0);
        return false;
    }

    const auto* sourceBytes = static_cast<const std::uint8_t*>(source);
    auto* destinationBytes = static_cast<std::uint8_t*>(mapped.pData);
    for (UINT row = 0; row < sourceRows; ++row) {
        std::memcpy(
            destinationBytes + static_cast<std::size_t>(row) * mapped.RowPitch,
            sourceBytes + static_cast<std::size_t>(row) * sourceRowPitch,
            rowBytes);
    }
    context->Unmap(texture_.Get(), 0);
    ++upload_generation_;
    return true;
}

bool bind_fixed_function_texture_stage_for_observation(
    ID3D11DeviceContext* context,
    UINT slot,
    const NativeFixedFunctionSamplerState& sampler,
    const NativeFixedFunctionTextureView& texture) noexcept {

    // R152: a deferred context can record matching PS sampler/SRV state,
    // but cannot prove the immediate draw context has those live bindings.
    if (!context ||
        context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE ||
        !sampler.ready() || !texture.ready() ||
        slot >= D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT ||
        slot >= D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT)
        return false;

    ID3D11Device* samplerDevice = sampler.device();
    ID3D11Device* textureDevice = texture.device();
    if (!samplerDevice || !textureDevice || samplerDevice != textureDevice)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    if (!contextDevice || contextDevice.Get() != samplerDevice)
        return false;

    ID3D11SamplerState* samplerState = sampler.sampler();
    ID3D11ShaderResourceView* shaderResource = texture.srv();
    if (!samplerState || !shaderResource)
        return false;

    context->PSSetSamplers(slot, 1, &samplerState);
    context->PSSetShaderResources(slot, 1, &shaderResource);

    // D3D11 silently NULLs an SRV when it conflicts with a resource that is
    // already bound for output. Treat that hazard resolution as a failed
    // observation bind instead of reporting a false-positive readiness state.
    Microsoft::WRL::ComPtr<ID3D11SamplerState> boundSampler;
    Microsoft::WRL::ComPtr<ID3D11ShaderResourceView> boundResource;
    context->PSGetSamplers(
        slot, 1, boundSampler.ReleaseAndGetAddressOf());
    context->PSGetShaderResources(
        slot, 1, boundResource.ReleaseAndGetAddressOf());
    if (boundSampler.Get() != samplerState ||
        boundResource.Get() != shaderResource) {
        ID3D11SamplerState* nullSampler = nullptr;
        ID3D11ShaderResourceView* nullResource = nullptr;
        context->PSSetSamplers(slot, 1, &nullSampler);
        context->PSSetShaderResources(slot, 1, &nullResource);
        return false;
    }

    return true;
}

NativeFixedFunctionTextureStageBindingReadiness
observe_fixed_function_texture_stage_binding(
    ID3D11DeviceContext* context,
    UINT slot,
    const NativeFixedFunctionSamplerState& sampler,
    const NativeFixedFunctionTextureView& texture) noexcept {
    NativeFixedFunctionTextureStageBindingReadiness out{};
    out.slot = slot;
    out.textureUploadGeneration = texture.upload_generation();
    // R152: recording state on a deferred context is not a live PS receipt.
    out.inputValid =
        context != nullptr &&
        context->GetType() == D3D11_DEVICE_CONTEXT_IMMEDIATE;
    out.slotValid =
        slot < D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT &&
        slot < D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT;
    out.ownersReady = sampler.ready() && texture.ready();

    ID3D11Device* samplerDevice = sampler.device();
    ID3D11Device* textureDevice = texture.device();
    out.devicesMatch =
        samplerDevice != nullptr &&
        textureDevice != nullptr &&
        samplerDevice == textureDevice;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    if (context)
        context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    out.contextMatches =
        out.devicesMatch &&
        contextDevice &&
        contextDevice.Get() == samplerDevice;

    if (out.inputValid && out.slotValid && out.ownersReady &&
        out.devicesMatch && out.contextMatches) {
        Microsoft::WRL::ComPtr<ID3D11SamplerState> boundSampler;
        Microsoft::WRL::ComPtr<ID3D11ShaderResourceView> boundResource;
        context->PSGetSamplers(
            slot, 1, boundSampler.ReleaseAndGetAddressOf());
        context->PSGetShaderResources(
            slot, 1, boundResource.ReleaseAndGetAddressOf());
        out.boundExact =
            boundSampler.Get() == sampler.sampler() &&
            boundResource.Get() == texture.srv();
    }

    out.ready =
        out.inputValid &&
        out.slotValid &&
        out.ownersReady &&
        out.devicesMatch &&
        out.contextMatches &&
        out.boundExact;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(token, out.slot);
        token = mix_readiness_snapshot_token(
            token, out.textureUploadGeneration);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(samplerDevice)));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(sampler.sampler())));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(texture.srv())));
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_texture_stage_binding_snapshot(
    ID3D11DeviceContext* context,
    UINT slot,
    const NativeFixedFunctionSamplerState& sampler,
    const NativeFixedFunctionTextureView& texture,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = observe_fixed_function_texture_stage_binding(
        context, slot, sampler, texture);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionTextureBindingSetReadiness
observe_fixed_function_texture_binding_set(
    ID3D11DeviceContext* context,
    std::uint32_t requiredTextureMask,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures) noexcept {
    NativeFixedFunctionTextureBindingSetReadiness out{};
    constexpr std::uint32_t kFixedFunctionStageMask = 0xffu;
    out.requiredTextureMask = requiredTextureMask;
    out.requiredMaskValid =
        requiredTextureMask != 0 &&
        (requiredTextureMask & ~kFixedFunctionStageMask) == 0;
    out.inputValid = context != nullptr && out.requiredMaskValid;
    if (!out.inputValid)
        return out;

    for (UINT slot = 0; slot < 8; ++slot) {
        const std::uint32_t stageBit = 1u << slot;
        if ((requiredTextureMask & stageBit) == 0)
            continue;

        const auto* sampler = samplers[slot];
        const auto* texture = textures[slot];
        if (!sampler || !texture)
            continue;

        const auto stage = observe_fixed_function_texture_stage_binding(
            context, slot, *sampler, *texture);
        if (!stage.ready || stage.snapshotToken == 0)
            continue;

        out.observedTextureMask |= stageBit;
        out.stageSnapshotTokens[slot] = stage.snapshotToken;
    }

    out.allRequiredBoundExact =
        out.observedTextureMask == out.requiredTextureMask;
    out.ready = out.inputValid && out.allRequiredBoundExact;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(token, out.requiredTextureMask);
        token = mix_readiness_snapshot_token(token, out.observedTextureMask);
        for (UINT slot = 0; slot < 8; ++slot) {
            const std::uint32_t stageBit = 1u << slot;
            if ((requiredTextureMask & stageBit) == 0)
                continue;
            token = mix_readiness_snapshot_token(token, stageBit);
            token = mix_readiness_snapshot_token(
                token, out.stageSnapshotTokens[slot]);
        }
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_texture_binding_set_snapshot(
    ID3D11DeviceContext* context,
    std::uint32_t requiredTextureMask,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = observe_fixed_function_texture_binding_set(
        context, requiredTextureMask, samplers, textures);
    return current.ready && current.snapshotToken == snapshotToken;
}

bool validate_fixed_function_texture_binding_set_readiness_integrity(
    const NativeFixedFunctionTextureBindingSetReadiness& textureBindings) noexcept {
    constexpr std::uint32_t kFixedFunctionStageMask = 0xffu;
    if (!textureBindings.inputValid ||
        !textureBindings.requiredMaskValid ||
        !textureBindings.allRequiredBoundExact ||
        !textureBindings.ready ||
        textureBindings.snapshotToken == 0 ||
        textureBindings.requiredTextureMask == 0 ||
        (textureBindings.requiredTextureMask & ~kFixedFunctionStageMask) != 0 ||
        textureBindings.observedTextureMask !=
            textureBindings.requiredTextureMask)
        return false;

    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(
        token, textureBindings.requiredTextureMask);
    token = mix_readiness_snapshot_token(
        token, textureBindings.observedTextureMask);
    for (UINT slot = 0; slot < 8; ++slot) {
        const std::uint32_t stageBit = 1u << slot;
        const bool required =
            (textureBindings.requiredTextureMask & stageBit) != 0;
        if (!required) {
            if (textureBindings.stageSnapshotTokens[slot] != 0)
                return false;
            continue;
        }
        if (textureBindings.stageSnapshotTokens[slot] == 0)
            return false;
        token = mix_readiness_snapshot_token(token, stageBit);
        token = mix_readiness_snapshot_token(
            token, textureBindings.stageSnapshotTokens[slot]);
    }
    token = token == 0 ? 1 : token;
    return token == textureBindings.snapshotToken;
}

void NativeFixedFunctionTextureView::shutdown() noexcept {
    srv_.Reset();
    texture_.Reset();
    device_.Reset();
    source_format_ = D3DFMT_UNKNOWN;
    source_pool_ = D3DPOOL_DEFAULT;
    source_usage_ = 0;
    source_metadata_valid_ = false;
    upload_generation_ = 0;
}

bool NativeManagedBufferShadow::initialize(
    ResourceRole role,
    UINT byteWidth,
    DWORD sourceUsage) noexcept {

    shutdown();
    if ((role != ResourceRole::Vertex && role != ResourceRole::Index) ||
        byteWidth == 0)
        return false;

    const auto behavior = translate_resource_behavior(
        role, D3DPOOL_MANAGED, sourceUsage);
    const UINT expectedBind =
        role == ResourceRole::Vertex
            ? D3D11_BIND_VERTEX_BUFFER
            : D3D11_BIND_INDEX_BUFFER;
    if (!behavior.descriptorExact ||
        behavior.lifetime != ResourceMirrorLifetime::ManagedCpuShadow ||
        !behavior.requiresCpuShadow ||
        behavior.usage != D3D11_USAGE_DEFAULT ||
        behavior.cpuAccessFlags != 0 ||
        behavior.bindFlags != expectedBind)
        return false;

    try {
        shadow_.assign(static_cast<std::size_t>(byteWidth), 0);
    } catch (...) {
        shutdown();
        return false;
    }

    role_ = role;
    source_usage_ = sourceUsage;
    byte_width_ = byteWidth;
    metadata_valid_ = true;
    lifetime_ = {};
    return true;
}

bool NativeManagedBufferShadow::write_range(
    UINT offset,
    const void* source,
    UINT sourceBytes) noexcept {

    if (!ready() || !source || sourceBytes == 0 ||
        offset > byte_width_ || sourceBytes > byte_width_ - offset)
        return false;

    const auto mutation = translate_buffer_mutation(
        role_, D3DPOOL_MANAGED, source_usage_, 0);
    // R125: R121 made ordinary MANAGED buffer mutation plans exact. The
    // dormant R113 CPU shadow must consume that exact plan rather than reject
    // it; R119 mirror readiness still independently rejects stale snapshots.
    if (mutation.kind != BufferMutationUpdateKind::ManagedCpuShadowWrite ||
        !mutation.requiresCpuShadow || !mutation.planExact)
        return false;

    // Until a complete initial image exists, a partial Lock cannot establish
    // deterministic contents for the untouched bytes.
    if (!shadow_valid() &&
        (offset != 0 || sourceBytes != byte_width_))
        return false;

    std::memcpy(
        shadow_.data() + static_cast<std::size_t>(offset),
        source,
        static_cast<std::size_t>(sourceBytes));
    release_mirror();
    lifetime_ = note_managed_shadow_write(lifetime_);
    return true;
}

bool NativeManagedBufferShadow::recreate_and_upload_mirror(
    ID3D11Device* device) noexcept {

    if (!ready() || !shadow_valid() || !device)
        return false;

    const auto behavior = translate_resource_behavior(
        role_, D3DPOOL_MANAGED, source_usage_);
    const UINT expectedBind =
        role_ == ResourceRole::Vertex
            ? D3D11_BIND_VERTEX_BUFFER
            : D3D11_BIND_INDEX_BUFFER;
    if (!behavior.descriptorExact ||
        behavior.lifetime != ResourceMirrorLifetime::ManagedCpuShadow ||
        !behavior.requiresCpuShadow ||
        behavior.usage != D3D11_USAGE_DEFAULT ||
        behavior.cpuAccessFlags != 0 ||
        behavior.bindFlags != expectedBind)
        return false;

    release_mirror();

    D3D11_BUFFER_DESC desc{};
    desc.ByteWidth = byte_width_;
    desc.Usage = D3D11_USAGE_DEFAULT;
    desc.BindFlags = expectedBind;

    D3D11_SUBRESOURCE_DATA initialData{};
    initialData.pSysMem = shadow_.data();

    Microsoft::WRL::ComPtr<ID3D11Buffer> buffer;
    if (FAILED(device->CreateBuffer(
            &desc, &initialData, buffer.ReleaseAndGetAddressOf())) ||
        !buffer)
        return false;

    mirror_device_ = device;
    mirror_buffer_ = std::move(buffer);
    lifetime_ = note_managed_mirror_upload(lifetime_);
    if (!mirror_ready()) {
        release_mirror();
        return false;
    }
    ++mirror_instance_generation_;
    if (mirror_instance_generation_ == 0)
        ++mirror_instance_generation_;
    return true;
}

bool NativeManagedBufferShadow::mirror_descriptor_exact(
    ID3D11Device* expectedDevice) const noexcept {

    if (!expectedDevice ||
        mirror_device_.Get() != expectedDevice ||
        !mirror_buffer_)
        return false;

    const auto behavior = translate_resource_behavior(
        role_, D3DPOOL_MANAGED, source_usage_);
    const UINT expectedBind =
        role_ == ResourceRole::Vertex
            ? D3D11_BIND_VERTEX_BUFFER
            : D3D11_BIND_INDEX_BUFFER;
    if (!behavior.descriptorExact ||
        behavior.lifetime != ResourceMirrorLifetime::ManagedCpuShadow ||
        !behavior.requiresCpuShadow ||
        behavior.usage != D3D11_USAGE_DEFAULT ||
        behavior.cpuAccessFlags != 0 ||
        behavior.bindFlags != expectedBind)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> bufferDevice;
    mirror_buffer_->GetDevice(bufferDevice.ReleaseAndGetAddressOf());
    if (!bufferDevice || bufferDevice.Get() != expectedDevice)
        return false;

    D3D11_BUFFER_DESC desc{};
    mirror_buffer_->GetDesc(&desc);
    return desc.ByteWidth == byte_width_ &&
        desc.Usage == behavior.usage &&
        desc.BindFlags == behavior.bindFlags &&
        desc.CPUAccessFlags == behavior.cpuAccessFlags &&
        desc.MiscFlags == 0 &&
        desc.StructureByteStride == 0;
}

NativeManagedBufferMirrorReadiness
NativeManagedBufferShadow::mirror_readiness(
    ID3D11Device* expectedDevice) const noexcept {

    NativeManagedBufferMirrorReadiness out{};
    out.role = role_;
    out.deviceGeneration = lifetime_.deviceGeneration;
    out.shadowVersion = lifetime_.cpuShadowVersion;
    out.mirrorGeneration = lifetime_.mirrorGeneration;
    out.mirrorShadowVersion = lifetime_.mirrorShadowVersion;
    out.mirrorInstanceGeneration = mirror_instance_generation_;

    out.inputValid = ready() && expectedDevice != nullptr;
    if (!out.inputValid)
        return out;

    out.shadowValid = lifetime_.cpuShadowValid;
    out.resourcesOwned = mirror_device_ && mirror_buffer_;
    out.lifetimeCurrent = managed_mirror_ready(lifetime_);
    out.deviceMatches =
        out.resourcesOwned && mirror_device_.Get() == expectedDevice;
    if (out.deviceMatches) {
        Microsoft::WRL::ComPtr<ID3D11Device> bufferDevice;
        mirror_buffer_->GetDevice(bufferDevice.ReleaseAndGetAddressOf());
        out.deviceMatches =
            bufferDevice && bufferDevice.Get() == expectedDevice;
    }
    out.descriptorExact =
        out.deviceMatches && mirror_descriptor_exact(expectedDevice);
    const auto mutationPlan = translate_buffer_mutation(
        role_, D3DPOOL_MANAGED, source_usage_, 0);
    out.mutationPlanExact =
        mutationPlan.planExact &&
        mutationPlan.requiresCpuShadow &&
        mutationPlan.kind == BufferMutationUpdateKind::ManagedCpuShadowWrite;
    out.ready =
        out.shadowValid &&
        out.resourcesOwned &&
        out.lifetimeCurrent &&
        out.deviceMatches &&
        out.descriptorExact &&
        out.mutationPlanExact &&
        out.mirrorInstanceGeneration != 0;

    if (out.ready) {
        std::uint64_t snapshotToken = 0xcbf29ce484222325ull;
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken,
            static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(this)));
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken,
            static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(expectedDevice)));
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken,
            static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(mirror_buffer_.Get())));
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, static_cast<std::uint32_t>(role_));
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, source_usage_);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, byte_width_);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, out.mutationPlanExact ? 1u : 0u);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, out.deviceGeneration);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, out.shadowVersion);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, out.mirrorGeneration);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, out.mirrorShadowVersion);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, out.mirrorInstanceGeneration);
        out.snapshotToken = snapshotToken == 0 ? 1 : snapshotToken;
    }
    return out;
}

bool NativeManagedBufferShadow::validate_mirror_readiness_snapshot(
    ID3D11Device* expectedDevice,
    std::uint64_t snapshotToken) const noexcept {

    if (snapshotToken == 0)
        return false;
    const auto current = mirror_readiness(expectedDevice);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeManagedIndexRangeReadiness
NativeManagedBufferShadow::index_range_readiness(
    const NativeManagedBufferMirrorReadiness& mirror,
    D3DFORMAT sourceIndexFormat,
    UINT startIndex,
    UINT indexCount,
    UINT minVertexIndex,
    UINT maxVertexIndex) const noexcept {

    NativeManagedIndexRangeReadiness out{};
    out.sourceIndexFormat = sourceIndexFormat;
    out.startIndex = startIndex;
    out.indexCount = indexCount;
    out.minVertexIndex = minVertexIndex;
    out.maxVertexIndex = maxVertexIndex;
    out.shadowVersion = lifetime_.cpuShadowVersion;
    out.mirrorSnapshotToken = mirror.snapshotToken;

    out.inputValid =
        ready() &&
        role_ == ResourceRole::Index &&
        mirror.inputValid &&
        mirror.role == ResourceRole::Index &&
        mirror.snapshotToken != 0;
    if (!out.inputValid)
        return out;

    out.shadowValid = shadow_valid() && mirror.shadowValid;
    const auto currentMirror = mirror_readiness(mirror_device_.Get());
    out.mirrorSnapshotExact =
        currentMirror.ready &&
        currentMirror.snapshotToken == mirror.snapshotToken &&
        currentMirror.shadowVersion == lifetime_.cpuShadowVersion;
    out.indexFormatExact =
        sourceIndexFormat == D3DFMT_INDEX16 ||
        sourceIndexFormat == D3DFMT_INDEX32;

    const std::uint64_t elementBytes =
        sourceIndexFormat == D3DFMT_INDEX16 ? 2ull :
        sourceIndexFormat == D3DFMT_INDEX32 ? 4ull : 0ull;
    if (elementBytes != 0) {
        const std::uint64_t startByte =
            static_cast<std::uint64_t>(startIndex) * elementBytes;
        const std::uint64_t scanBytes =
            static_cast<std::uint64_t>(indexCount) * elementBytes;
        out.byteRangeExact =
            startByte <= static_cast<std::uint64_t>(byte_width_) &&
            scanBytes <=
                static_cast<std::uint64_t>(byte_width_) - startByte;
    }

    if (!out.shadowValid ||
        !out.mirrorSnapshotExact ||
        !out.indexFormatExact ||
        !out.byteRangeExact)
        return out;

    if (indexCount != 0 && minVertexIndex > maxVertexIndex)
        return out;

    std::uint64_t contentHash = 0xcbf29ce484222325ull;
    out.valuesWithinDeclaredRange = true;
    if (indexCount != 0)
        out.observedMinIndex = (std::numeric_limits<UINT>::max)();

    const std::size_t elementSize = static_cast<std::size_t>(elementBytes);
    const std::size_t firstByte =
        static_cast<std::size_t>(startIndex) * elementSize;
    for (UINT i = 0; i < indexCount; ++i) {
        UINT value = 0;
        const auto* source =
            shadow_.data() + firstByte +
            static_cast<std::size_t>(i) * elementSize;
        if (sourceIndexFormat == D3DFMT_INDEX16) {
            std::uint16_t value16 = 0;
            std::memcpy(&value16, source, sizeof(value16));
            value = value16;
        } else {
            std::uint32_t value32 = 0;
            std::memcpy(&value32, source, sizeof(value32));
            value = value32;
        }
        if (value < out.observedMinIndex)
            out.observedMinIndex = value;
        if (value > out.observedMaxIndex)
            out.observedMaxIndex = value;
        contentHash = mix_readiness_snapshot_token(contentHash, value);
        if (value < minVertexIndex || value > maxVertexIndex)
            out.valuesWithinDeclaredRange = false;
    }
    out.contentHash = contentHash == 0 ? 1 : contentHash;
    out.ready =
        out.valuesWithinDeclaredRange &&
        out.mirrorSnapshotExact &&
        out.mirrorSnapshotToken != 0;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(token, out.mirrorSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.shadowVersion);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.sourceIndexFormat));
        token = mix_readiness_snapshot_token(token, out.startIndex);
        token = mix_readiness_snapshot_token(token, out.indexCount);
        token = mix_readiness_snapshot_token(token, out.minVertexIndex);
        token = mix_readiness_snapshot_token(token, out.maxVertexIndex);
        token = mix_readiness_snapshot_token(token, out.observedMinIndex);
        token = mix_readiness_snapshot_token(token, out.observedMaxIndex);
        token = mix_readiness_snapshot_token(token, out.contentHash);
        token = mix_readiness_snapshot_token(token, 0x152u);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeManagedBufferShadow::hash_indexed_triangle_fan_window(
    D3DFORMAT sourceIndexFormat,
    UINT startIndex,
    UINT sourceIndexCount,
    UINT primitiveCount,
    std::uint64_t expectedShadowVersion,
    std::uint64_t& expandedContentHash) const noexcept {

    expandedContentHash = 0;
    if (!ready() ||
        role_ != ResourceRole::Index ||
        !shadow_valid() ||
        expectedShadowVersion == 0 ||
        lifetime_.cpuShadowVersion != expectedShadowVersion)
        return false;

    const auto expansion = translate_triangle_fan_expansion(primitiveCount);
    if (!expansion.exact ||
        expansion.sourceElementCount == 0 ||
        expansion.expandedIndexCount == 0)
        return false;

    const std::uint64_t elementBytes =
        sourceIndexFormat == D3DFMT_INDEX16 ? 2ull :
        sourceIndexFormat == D3DFMT_INDEX32 ? 4ull : 0ull;
    if (elementBytes == 0 ||
        startIndex > sourceIndexCount ||
        expansion.sourceElementCount > sourceIndexCount - startIndex)
        return false;

    const std::uint64_t declaredBytes =
        static_cast<std::uint64_t>(sourceIndexCount) * elementBytes;
    const std::uint64_t firstByte =
        static_cast<std::uint64_t>(startIndex) * elementBytes;
    const std::uint64_t requiredBytes =
        static_cast<std::uint64_t>(expansion.sourceElementCount) * elementBytes;
    if (declaredBytes > static_cast<std::uint64_t>(byte_width_) ||
        firstByte > static_cast<std::uint64_t>(byte_width_) ||
        requiredBytes > static_cast<std::uint64_t>(byte_width_) - firstByte)
        return false;

    std::uint64_t hash = 0xcbf29ce484222325ull;
    for (UINT expandedIndex = 0;
         expandedIndex < expansion.expandedIndexCount;
         ++expandedIndex) {
        UINT sourceElement = 0;
        if (!triangle_fan_source_element(
                primitiveCount, expandedIndex, sourceElement))
            return false;

        const std::size_t byteOffset =
            static_cast<std::size_t>(
                static_cast<std::uint64_t>(startIndex + sourceElement) *
                elementBytes);
        UINT value = 0;
        if (sourceIndexFormat == D3DFMT_INDEX16) {
            std::uint16_t value16 = 0;
            std::memcpy(
                &value16, shadow_.data() + byteOffset, sizeof(value16));
            value = value16;
        } else {
            std::uint32_t value32 = 0;
            std::memcpy(
                &value32, shadow_.data() + byteOffset, sizeof(value32));
            value = value32;
        }
        hash = mix_readiness_snapshot_token(hash, value);
    }

    expandedContentHash = hash == 0 ? 1 : hash;
    return true;
}

bool NativeManagedBufferShadow::validate_index_range_readiness_snapshot(
    const NativeManagedBufferMirrorReadiness& mirror,
    D3DFORMAT sourceIndexFormat,
    UINT startIndex,
    UINT indexCount,
    UINT minVertexIndex,
    UINT maxVertexIndex,
    std::uint64_t snapshotToken) const noexcept {

    if (snapshotToken == 0)
        return false;
    const auto current = index_range_readiness(
        mirror, sourceIndexFormat, startIndex, indexCount,
        minVertexIndex, maxVertexIndex);
    return current.ready && current.snapshotToken == snapshotToken;
}

void NativeManagedBufferShadow::observe_device_reset() noexcept {
    release_mirror();
    lifetime_ = advance_managed_device_generation(lifetime_);
}

void NativeManagedBufferShadow::release_mirror() noexcept {
    mirror_buffer_.Reset();
    mirror_device_.Reset();
    lifetime_.mirrorValid = false;
}

void NativeManagedBufferShadow::shutdown() noexcept {
    release_mirror();
    role_ = ResourceRole::Vertex;
    source_usage_ = 0;
    byte_width_ = 0;
    metadata_valid_ = false;
    shadow_.clear();
    lifetime_ = {};
    mirror_instance_generation_ = 0;
}

bool NativeManagedTextureShadow::initialize(
    D3DFORMAT sourceFormat,
    UINT width,
    UINT height) noexcept {

    shutdown();
    if (width == 0 || height == 0)
        return false;

    const auto format = translate_resource_format(
        sourceFormat, ResourceRole::Texture);
    const auto behavior = translate_resource_behavior(
        ResourceRole::Texture, D3DPOOL_MANAGED, 0);
    if (!format.exact || !behavior.descriptorExact ||
        behavior.lifetime != ResourceMirrorLifetime::ManagedCpuShadow ||
        !behavior.requiresCpuShadow)
        return false;

    UINT rowBytes = 0;
    if (!texture_uncompressed_row_bytes(sourceFormat, width, rowBytes))
        return false;

    if (static_cast<std::size_t>(height) >
        (std::numeric_limits<std::size_t>::max)() / rowBytes)
        return false;
    const std::size_t shadowBytes =
        static_cast<std::size_t>(rowBytes) * height;

    try {
        shadow_.assign(shadowBytes, 0);
    } catch (...) {
        shutdown();
        return false;
    }

    source_format_ = sourceFormat;
    width_ = width;
    height_ = height;
    row_bytes_ = rowBytes;
    lifetime_ = {};
    return true;
}

bool NativeManagedTextureShadow::write_full(
    const void* source,
    UINT sourceRowPitch,
    UINT sourceRows) noexcept {

    if (!ready() || source_lock_active_ || source_unlock_staged_ || !source ||
        sourceRows != height_ || sourceRowPitch < row_bytes_)
        return false;

    const auto mutation = translate_texture_mutation(
        D3DPOOL_MANAGED, 0, 0, true);
    if (mutation.kind != TextureMutationUpdateKind::ManagedCpuShadowWrite ||
        !mutation.requiresCpuShadow || mutation.planExact)
        return false;

    const auto* sourceBytes = static_cast<const std::uint8_t*>(source);
    for (UINT row = 0; row < height_; ++row) {
        std::memcpy(
            shadow_.data() + static_cast<std::size_t>(row) * row_bytes_,
            sourceBytes + static_cast<std::size_t>(row) * sourceRowPitch,
            row_bytes_);
    }

    release_mirror();
    lifetime_ = note_managed_shadow_write(lifetime_);
    return true;
}

bool NativeManagedTextureShadow::read_full(
    void* destination,
    UINT destinationRowPitch,
    UINT destinationRows) const noexcept {

    if (!ready() || source_lock_active_ || source_unlock_staged_ ||
        !shadow_valid() || !destination ||
        destinationRows != height_ || destinationRowPitch < row_bytes_)
        return false;

    const auto mutation = translate_texture_mutation(
        D3DPOOL_MANAGED, 0, D3DLOCK_READONLY, true);
    if (mutation.kind != TextureMutationUpdateKind::ManagedCpuShadowRead ||
        !mutation.requiresCpuShadow || mutation.planExact)
        return false;

    auto* destinationBytes = static_cast<std::uint8_t*>(destination);
    for (UINT row = 0; row < height_; ++row) {
        std::memcpy(
            destinationBytes + static_cast<std::size_t>(row) * destinationRowPitch,
            shadow_.data() + static_cast<std::size_t>(row) * row_bytes_,
            row_bytes_);
    }
    return true;
}

bool NativeManagedTextureShadow::recreate_and_upload_mirror(
    ID3D11Device* device) noexcept {

    if (!ready() || source_lock_active_ || source_unlock_staged_ ||
        !shadow_valid() || !device)
        return false;

    const auto format = translate_resource_format(
        source_format_, ResourceRole::Texture);
    const auto behavior = translate_resource_behavior(
        ResourceRole::Texture, D3DPOOL_MANAGED, 0);
    if (!format.exact || !behavior.descriptorExact ||
        behavior.lifetime != ResourceMirrorLifetime::ManagedCpuShadow ||
        !behavior.requiresCpuShadow ||
        behavior.usage != D3D11_USAGE_DEFAULT ||
        behavior.cpuAccessFlags != 0 ||
        (behavior.bindFlags & D3D11_BIND_SHADER_RESOURCE) == 0)
        return false;

    release_mirror();

    D3D11_TEXTURE2D_DESC desc{};
    desc.Width = width_;
    desc.Height = height_;
    desc.MipLevels = 1;
    desc.ArraySize = 1;
    desc.Format = format.format;
    desc.SampleDesc.Count = 1;
    desc.Usage = D3D11_USAGE_DEFAULT;
    desc.BindFlags = D3D11_BIND_SHADER_RESOURCE;

    D3D11_SUBRESOURCE_DATA initialData{};
    initialData.pSysMem = shadow_.data();
    initialData.SysMemPitch = row_bytes_;

    Microsoft::WRL::ComPtr<ID3D11Texture2D> texture;
    if (FAILED(device->CreateTexture2D(
            &desc, &initialData, texture.ReleaseAndGetAddressOf())) ||
        !texture)
        return false;

    D3D11_SHADER_RESOURCE_VIEW_DESC srvDesc{};
    srvDesc.Format = desc.Format;
    srvDesc.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D;
    srvDesc.Texture2D.MostDetailedMip = 0;
    srvDesc.Texture2D.MipLevels = 1;

    Microsoft::WRL::ComPtr<ID3D11ShaderResourceView> srv;
    if (FAILED(device->CreateShaderResourceView(
            texture.Get(), &srvDesc, srv.ReleaseAndGetAddressOf())) ||
        !srv)
        return false;

    mirror_device_ = device;
    mirror_texture_ = std::move(texture);
    mirror_srv_ = std::move(srv);
    note_mirror_uploaded();
    if (!mirror_ready()) {
        release_mirror();
        return false;
    }
    ++mirror_instance_generation_;
    if (mirror_instance_generation_ == 0)
        ++mirror_instance_generation_;
    return true;
}

bool NativeManagedTextureShadow::mirror_descriptor_exact(
    ID3D11Device* expectedDevice) const noexcept {
    if (!expectedDevice ||
        mirror_device_.Get() != expectedDevice ||
        !mirror_texture_ || !mirror_srv_)
        return false;

    const auto format = translate_resource_format(
        source_format_, ResourceRole::Texture);
    const auto behavior = translate_resource_behavior(
        ResourceRole::Texture, D3DPOOL_MANAGED, 0);
    if (!format.exact || !behavior.descriptorExact ||
        behavior.lifetime != ResourceMirrorLifetime::ManagedCpuShadow ||
        !behavior.requiresCpuShadow ||
        behavior.usage != D3D11_USAGE_DEFAULT ||
        behavior.cpuAccessFlags != 0 ||
        behavior.bindFlags != D3D11_BIND_SHADER_RESOURCE)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> textureDevice;
    mirror_texture_->GetDevice(textureDevice.ReleaseAndGetAddressOf());
    if (!textureDevice || textureDevice.Get() != expectedDevice)
        return false;

    D3D11_TEXTURE2D_DESC textureDesc{};
    mirror_texture_->GetDesc(&textureDesc);
    if (textureDesc.Width != width_ ||
        textureDesc.Height != height_ ||
        textureDesc.MipLevels != 1 ||
        textureDesc.ArraySize != 1 ||
        textureDesc.Format != format.format ||
        textureDesc.SampleDesc.Count != 1 ||
        textureDesc.SampleDesc.Quality != 0 ||
        textureDesc.Usage != behavior.usage ||
        textureDesc.BindFlags != behavior.bindFlags ||
        textureDesc.CPUAccessFlags != behavior.cpuAccessFlags ||
        textureDesc.MiscFlags != 0)
        return false;

    D3D11_SHADER_RESOURCE_VIEW_DESC srvDesc{};
    mirror_srv_->GetDesc(&srvDesc);
    if (srvDesc.Format != textureDesc.Format ||
        srvDesc.ViewDimension != D3D11_SRV_DIMENSION_TEXTURE2D ||
        srvDesc.Texture2D.MostDetailedMip != 0 ||
        srvDesc.Texture2D.MipLevels != 1)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Resource> viewResource;
    mirror_srv_->GetResource(viewResource.ReleaseAndGetAddressOf());
    if (!viewResource)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Texture2D> viewTexture;
    if (FAILED(viewResource.As(&viewTexture)) ||
        !viewTexture || viewTexture.Get() != mirror_texture_.Get())
        return false;

    return true;
}

bool NativeManagedTextureShadow::begin_source_lock(
    UINT level,
    const RECT* sourceRect,
    DWORD lockFlags,
    const D3DLOCKED_RECT& lockedRect) noexcept {

    if (!ready() || source_lock_active_ || source_unlock_staged_ ||
        level != 0 || sourceRect != nullptr ||
        !lockedRect.pBits || lockedRect.Pitch <= 0)
        return false;

    const auto mutation = translate_texture_mutation(
        D3DPOOL_MANAGED, 0, lockFlags, true);
    if (mutation.kind != TextureMutationUpdateKind::ManagedCpuShadowWrite ||
        !mutation.requiresCpuShadow || mutation.planExact)
        return false;

    const UINT pitch = static_cast<UINT>(lockedRect.Pitch);
    if (pitch < row_bytes_)
        return false;

    // A successful writable LockRect means the source can diverge before the
    // matching UnlockRect. Do not expose a previously uploaded mirror while
    // that source memory is mutable.
    release_mirror();
    source_lock_bits_ = lockedRect.pBits;
    source_lock_pitch_ = pitch;
    source_lock_level_ = level;
    source_lock_active_ = true;
    return true;
}

bool NativeManagedTextureShadow::stage_source_unlock(UINT level) noexcept {
    if (!source_lock_active_ || source_unlock_staged_ ||
        level != source_lock_level_ || !source_lock_bits_ ||
        source_lock_pitch_ < row_bytes_)
        return false;

    try {
        pending_unlock_.resize(shadow_.size());
    } catch (...) {
        invalidate_shadow();
        clear_source_lock();
        clear_unlock_stage();
        return false;
    }

    const auto* sourceBytes =
        static_cast<const std::uint8_t*>(source_lock_bits_);
    for (UINT row = 0; row < height_; ++row) {
        std::memcpy(
            pending_unlock_.data() +
                static_cast<std::size_t>(row) * row_bytes_,
            sourceBytes +
                static_cast<std::size_t>(row) * source_lock_pitch_,
            row_bytes_);
    }

    clear_source_lock();
    source_unlock_level_ = level;
    source_unlock_staged_ = true;
    return true;
}

bool NativeManagedTextureShadow::finish_source_unlock(
    UINT level,
    HRESULT unlockResult) noexcept {

    if (!source_unlock_staged_ || level != source_unlock_level_)
        return false;

    if (FAILED(unlockResult) || !ready() ||
        pending_unlock_.size() != shadow_.size()) {
        clear_unlock_stage();
        invalidate_shadow();
        return false;
    }

    std::memcpy(
        shadow_.data(), pending_unlock_.data(), pending_unlock_.size());
    clear_unlock_stage();
    release_mirror();
    lifetime_ = note_managed_shadow_write(lifetime_);
    return true;
}

bool NativeManagedTextureShadow::commit_source_unlock(UINT level) noexcept {
    return stage_source_unlock(level) &&
        finish_source_unlock(level, S_OK);
}

void NativeManagedTextureShadow::cancel_source_lock() noexcept {
    clear_source_lock();
    clear_unlock_stage();
}

void NativeManagedTextureShadow::note_mirror_uploaded() noexcept {
    if (!mirror_device_ || !mirror_texture_ || !mirror_srv_)
        return;
    lifetime_ = note_managed_mirror_upload(lifetime_);
}

void NativeManagedTextureShadow::observe_device_reset() noexcept {
    clear_source_lock();
    clear_unlock_stage();
    release_mirror();
    lifetime_ = advance_managed_device_generation(lifetime_);
}

bool NativeManagedTextureShadow::invalidate_external_mutation() noexcept {
    const bool wasValid = lifetime_.cpuShadowValid;
    clear_source_lock();
    clear_unlock_stage();
    invalidate_shadow();
    return wasValid;
}

void NativeManagedTextureShadow::release_mirror() noexcept {
    mirror_srv_.Reset();
    mirror_texture_.Reset();
    mirror_device_.Reset();
    lifetime_.mirrorValid = false;
}

void NativeManagedTextureShadow::invalidate_shadow() noexcept {
    release_mirror();
    lifetime_.cpuShadowValid = false;
    lifetime_.mirrorValid = false;
}

void NativeManagedTextureShadow::clear_source_lock() noexcept {
    source_lock_bits_ = nullptr;
    source_lock_pitch_ = 0;
    source_lock_level_ = 0;
    source_lock_active_ = false;
}

void NativeManagedTextureShadow::clear_unlock_stage() noexcept {
    pending_unlock_.clear();
    source_unlock_level_ = 0;
    source_unlock_staged_ = false;
}

void NativeManagedTextureShadow::shutdown() noexcept {
    clear_source_lock();
    clear_unlock_stage();
    release_mirror();
    source_format_ = D3DFMT_UNKNOWN;
    width_ = 0;
    height_ = 0;
    row_bytes_ = 0;
    shadow_.clear();
    lifetime_ = {};
    mirror_instance_generation_ = 0;
}

bool NativeManagedTextureRegistry::register_texture(
    const void* textureKey,
    D3DFORMAT sourceFormat,
    UINT width,
    UINT height,
    UINT levels,
    DWORD usage,
    D3DPOOL pool) noexcept {

    if (!textureKey || levels != 1)
        return false;

    const auto behavior = translate_resource_behavior(
        ResourceRole::Texture, pool, usage);
    if (!behavior.descriptorExact ||
        behavior.lifetime != ResourceMirrorLifetime::ManagedCpuShadow ||
        !behavior.requiresCpuShadow ||
        pool != D3DPOOL_MANAGED || usage != 0)
        return false;

    try {
        auto shadow = std::make_unique<NativeManagedTextureShadow>();
        if (!shadow->initialize(sourceFormat, width, height))
            return false;

        std::lock_guard<std::mutex> lock(mutex_);
        shadows_[textureKey] = std::move(shadow);
        advance_membership_generation_locked();
        return true;
    } catch (...) {
        return false;
    }
}

NativeManagedTextureShadow* NativeManagedTextureRegistry::find_locked(
    const void* textureKey) noexcept {
    const auto it = shadows_.find(textureKey);
    return it == shadows_.end() ? nullptr : it->second.get();
}

const NativeManagedTextureShadow* NativeManagedTextureRegistry::find_locked(
    const void* textureKey) const noexcept {
    const auto it = shadows_.find(textureKey);
    return it == shadows_.end() ? nullptr : it->second.get();
}

void NativeManagedTextureRegistry::advance_membership_generation_locked() noexcept {
    ++membership_generation_;
    if (membership_generation_ == 0)
        ++membership_generation_;
}

bool NativeManagedTextureRegistry::begin_source_lock(
    const void* textureKey,
    UINT level,
    const RECT* sourceRect,
    DWORD lockFlags,
    const D3DLOCKED_RECT& lockedRect) noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    auto* shadow = find_locked(textureKey);
    return shadow &&
        shadow->begin_source_lock(level, sourceRect, lockFlags, lockedRect);
}

bool NativeManagedTextureRegistry::stage_source_unlock(
    const void* textureKey,
    UINT level) noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    auto* shadow = find_locked(textureKey);
    return shadow && shadow->stage_source_unlock(level);
}

bool NativeManagedTextureRegistry::finish_source_unlock(
    const void* textureKey,
    UINT level,
    HRESULT unlockResult) noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    auto* shadow = find_locked(textureKey);
    return shadow &&
        shadow->finish_source_unlock(level, unlockResult);
}

bool NativeManagedTextureRegistry::invalidate_external_mutation(
    const void* textureKey) noexcept {
    if (!textureKey)
        return false;
    std::lock_guard<std::mutex> lock(mutex_);
    auto* shadow = find_locked(textureKey);
    return shadow && shadow->invalidate_external_mutation();
}

bool NativeManagedTextureRegistry::recreate_and_upload_mirror_for_observation(
    const void* textureKey,
    ID3D11Device* device) noexcept {
    if (!textureKey || !device)
        return false;
    std::lock_guard<std::mutex> lock(mutex_);
    auto* shadow = find_locked(textureKey);
    return shadow && shadow->recreate_and_upload_mirror(device);
}

NativeManagedTextureMirrorReadiness
NativeManagedTextureRegistry::mirror_readiness(
    const void* textureKey,
    ID3D11Device* expectedDevice) const noexcept {
    NativeManagedTextureMirrorReadiness out{};
    if (!textureKey)
        return out;

    std::lock_guard<std::mutex> lock(mutex_);
    const auto* shadow = find_locked(textureKey);
    if (!shadow)
        return out;

    out.registered = true;
    out.shadowValid = shadow->shadow_valid();
    const auto& lifetime = shadow->lifetime_state();
    out.deviceGeneration = lifetime.deviceGeneration;
    out.shadowVersion = lifetime.cpuShadowVersion;
    out.mirrorGeneration = lifetime.mirrorGeneration;
    out.mirrorShadowVersion = lifetime.mirrorShadowVersion;
    out.resourcesOwned =
        shadow->mirror_device() != nullptr &&
        shadow->mirror_texture() != nullptr &&
        shadow->mirror_srv() != nullptr;
    out.lifetimeCurrent = managed_mirror_ready(lifetime);
    out.deviceMatches =
        expectedDevice != nullptr &&
        shadow->mirror_device() == expectedDevice;
    out.descriptorExact =
        shadow->mirror_descriptor_exact(expectedDevice);
    out.ready =
        shadow->mirror_ready() &&
        out.resourcesOwned &&
        out.lifetimeCurrent &&
        out.deviceMatches &&
        out.descriptorExact;
    return out;
}

NativeManagedTextureStageReadiness
NativeManagedTextureRegistry::mirror_readiness_for_stages(
    const void* const* textureKeys,
    std::size_t textureCount,
    std::uint32_t requiredMask,
    ID3D11Device* expectedDevice) const noexcept {
    NativeManagedTextureStageReadiness out{};
    out.requiredMask = requiredMask;
    out.pendingMask = requiredMask;

    if (textureCount > 32 ||
        (textureCount != 0 && textureKeys == nullptr))
        return out;

    const std::uint32_t validMask =
        textureCount == 32
        ? 0xffffffffu
        : (textureCount == 0
            ? 0u
            : ((1u << static_cast<std::uint32_t>(textureCount)) - 1u));
    if ((requiredMask & ~validMask) != 0 ||
        (requiredMask != 0 && expectedDevice == nullptr))
        return out;

    out.inputValid = true;
    std::uint64_t snapshotToken = 0xcbf29ce484222325ull;
    snapshotToken = mix_readiness_snapshot_token(
        snapshotToken, static_cast<std::uint64_t>(requiredMask));
    snapshotToken = mix_readiness_snapshot_token(
        snapshotToken,
        static_cast<std::uint64_t>(
            reinterpret_cast<std::uintptr_t>(expectedDevice)));

    std::lock_guard<std::mutex> lock(mutex_);
    snapshotToken = mix_readiness_snapshot_token(
        snapshotToken,
        static_cast<std::uint64_t>(
            reinterpret_cast<std::uintptr_t>(this)));
    snapshotToken = mix_readiness_snapshot_token(
        snapshotToken, membership_generation_);
    for (std::size_t stage = 0; stage < textureCount; ++stage) {
        const auto bit = static_cast<std::uint32_t>(1u << stage);
        if ((requiredMask & bit) == 0)
            continue;

        const auto* shadow = find_locked(textureKeys[stage]);
        if (!shadow)
            continue;

        out.registeredMask |= bit;
        if (shadow->shadow_valid())
            out.shadowValidMask |= bit;

        const auto& lifetime = shadow->lifetime_state();
        const bool resourcesOwned =
            shadow->mirror_device() != nullptr &&
            shadow->mirror_texture() != nullptr &&
            shadow->mirror_srv() != nullptr;
        const bool lifetimeCurrent = managed_mirror_ready(lifetime);
        const bool deviceMatches =
            shadow->mirror_device() == expectedDevice;
        const bool descriptorExact =
            shadow->mirror_descriptor_exact(expectedDevice);

        if (resourcesOwned)
            out.resourcesOwnedMask |= bit;
        if (lifetimeCurrent)
            out.lifetimeCurrentMask |= bit;
        if (deviceMatches)
            out.deviceMatchesMask |= bit;
        if (descriptorExact)
            out.descriptorExactMask |= bit;
        if (shadow->mirror_ready() &&
            resourcesOwned &&
            lifetimeCurrent &&
            deviceMatches &&
            descriptorExact)
            out.readyMask |= bit;

        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, static_cast<std::uint64_t>(stage));
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken,
            static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(textureKeys[stage])));
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, lifetime.deviceGeneration);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, lifetime.cpuShadowVersion);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, lifetime.mirrorGeneration);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, lifetime.mirrorShadowVersion);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, shadow->mirror_instance_generation());
    }

    out.pendingMask = out.requiredMask & ~out.readyMask;
    out.allRequiredReady = out.pendingMask == 0;
    if (out.allRequiredReady && out.requiredMask != 0) {
        out.snapshotToken = snapshotToken == 0 ? 1 : snapshotToken;
    }
    return out;
}

bool NativeManagedTextureRegistry::validate_mirror_readiness_snapshot_for_stages(
    const void* const* textureKeys,
    std::size_t textureCount,
    std::uint32_t requiredMask,
    ID3D11Device* expectedDevice,
    std::uint64_t snapshotToken) const noexcept {
    if (snapshotToken == 0 || requiredMask == 0)
        return false;

    const auto current = mirror_readiness_for_stages(
        textureKeys, textureCount, requiredMask, expectedDevice);
    return current.inputValid &&
        current.allRequiredReady &&
        current.snapshotToken == snapshotToken;
}

void NativeManagedTextureRegistry::observe_device_reset() noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    for (auto& entry : shadows_) {
        if (entry.second)
            entry.second->observe_device_reset();
    }
}

void NativeManagedTextureRegistry::forget_texture(
    const void* textureKey) noexcept {
    if (!textureKey)
        return;
    std::lock_guard<std::mutex> lock(mutex_);
    const auto it = shadows_.find(textureKey);
    if (it == shadows_.end())
        return;
    if (it->second)
        it->second->shutdown();
    shadows_.erase(it);
    advance_membership_generation_locked();
}

void NativeManagedTextureRegistry::clear() noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    if (shadows_.empty())
        return;
    for (auto& entry : shadows_) {
        if (entry.second)
            entry.second->shutdown();
    }
    shadows_.clear();
    advance_membership_generation_locked();
}

std::size_t NativeManagedTextureRegistry::size() const noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    return shadows_.size();
}

bool NativeManagedTextureRegistry::contains(
    const void* textureKey) const noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    return find_locked(textureKey) != nullptr;
}

bool NativeManagedTextureRegistry::shadow_valid(
    const void* textureKey) const noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    const auto* shadow = find_locked(textureKey);
    return shadow && shadow->shadow_valid();
}

std::uint64_t NativeManagedTextureRegistry::shadow_version(
    const void* textureKey) const noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    const auto* shadow = find_locked(textureKey);
    return shadow ? shadow->shadow_version() : 0;
}

std::uint64_t NativeManagedTextureRegistry::device_generation(
    const void* textureKey) const noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    const auto* shadow = find_locked(textureKey);
    return shadow ? shadow->device_generation() : 0;
}

bool NativeManagedTextureRegistry::source_lock_active(
    const void* textureKey) const noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    const auto* shadow = find_locked(textureKey);
    return shadow && shadow->source_lock_active();
}

bool NativeManagedTextureRegistry::source_unlock_staged(
    const void* textureKey) const noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    const auto* shadow = find_locked(textureKey);
    return shadow && shadow->source_unlock_staged();
}

bool NativeManagedTextureRegistry::read_shadow(
    const void* textureKey,
    void* destination,
    UINT destinationRowPitch,
    UINT destinationRows) const noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    const auto* shadow = find_locked(textureKey);
    return shadow && shadow->read_full(
        destination, destinationRowPitch, destinationRows);
}

bool NativeFixedFunctionRenderStateBundle::initialize(
    ID3D11Device* device,
    const PipelineTranslation& translation) noexcept {

    shutdown();
    const auto translationIdentity =
        hash_pipeline_render_state_identity(translation);
    if (!device || translationIdentity == 0)
        return false;

    Microsoft::WRL::ComPtr<ID3D11BlendState> blendState;
    Microsoft::WRL::ComPtr<ID3D11DepthStencilState> depthStencilState;
    Microsoft::WRL::ComPtr<ID3D11RasterizerState> rasterizerState;
    if (FAILED(device->CreateBlendState(
            &translation.blend,
            blendState.ReleaseAndGetAddressOf())) ||
        !blendState ||
        FAILED(device->CreateDepthStencilState(
            &translation.depth_stencil,
            depthStencilState.ReleaseAndGetAddressOf())) ||
        !depthStencilState ||
        FAILED(device->CreateRasterizerState(
            &translation.rasterizer,
            rasterizerState.ReleaseAndGetAddressOf())) ||
        !rasterizerState)
        return false;

    device_ = device;
    blend_state_ = std::move(blendState);
    depth_stencil_state_ = std::move(depthStencilState);
    rasterizer_state_ = std::move(rasterizerState);
    stencil_ref_ = translation.stencil_ref;
    translation_identity_ = translationIdentity;
    ++bundle_generation_;
    if (bundle_generation_ == 0)
        ++bundle_generation_;
    return true;
}

NativeFixedFunctionRenderStateReadiness
NativeFixedFunctionRenderStateBundle::translation_readiness(
    ID3D11Device* expectedDevice,
    const PipelineTranslation& translation) const noexcept {
    NativeFixedFunctionRenderStateReadiness out{};
    const auto translationIdentity =
        hash_pipeline_render_state_identity(translation);
    if (!expectedDevice || translationIdentity == 0)
        return out;

    out.inputValid = true;
    out.bundleReady = ready();
    out.bundleGeneration = bundle_generation_;
    out.translationIdentity = translationIdentity;
    out.translationMatches =
        translation_identity_ != 0 &&
        translation_identity_ == translationIdentity &&
        stencil_ref_ == translation.stencil_ref;

    if (out.bundleReady) {
        Microsoft::WRL::ComPtr<ID3D11Device> blendDevice;
        Microsoft::WRL::ComPtr<ID3D11Device> depthDevice;
        Microsoft::WRL::ComPtr<ID3D11Device> rasterDevice;
        blend_state_->GetDevice(blendDevice.ReleaseAndGetAddressOf());
        depth_stencil_state_->GetDevice(depthDevice.ReleaseAndGetAddressOf());
        rasterizer_state_->GetDevice(rasterDevice.ReleaseAndGetAddressOf());
        out.deviceMatches =
            device_.Get() == expectedDevice &&
            blendDevice.Get() == expectedDevice &&
            depthDevice.Get() == expectedDevice &&
            rasterDevice.Get() == expectedDevice;
    }

    out.ready =
        out.bundleReady &&
        out.deviceMatches &&
        out.translationMatches;
    if (out.ready) {
        std::uint64_t snapshotToken = 0xcbf29ce484222325ull;
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken,
            reinterpret_cast<std::uintptr_t>(expectedDevice));
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, translationIdentity);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, bundle_generation_);
        out.snapshotToken = snapshotToken == 0 ? 1 : snapshotToken;
    }
    return out;
}

bool NativeFixedFunctionRenderStateBundle::validate_translation_snapshot(
    ID3D11Device* expectedDevice,
    const PipelineTranslation& translation,
    std::uint64_t snapshotToken) const noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current =
        translation_readiness(expectedDevice, translation);
    return current.ready && current.snapshotToken == snapshotToken;
}

bool NativeFixedFunctionRenderStateBundle::validate_readiness_snapshot(
    ID3D11Device* expectedDevice,
    const NativeFixedFunctionRenderStateReadiness& readiness) const noexcept {
    if (!expectedDevice ||
        !readiness.inputValid ||
        !readiness.bundleReady ||
        !readiness.deviceMatches ||
        !readiness.translationMatches ||
        !readiness.ready ||
        readiness.bundleGeneration == 0 ||
        readiness.translationIdentity == 0 ||
        readiness.snapshotToken == 0 ||
        !ready() ||
        device_.Get() != expectedDevice ||
        readiness.bundleGeneration != bundle_generation_ ||
        readiness.translationIdentity != translation_identity_)
        return false;

    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(
        token, reinterpret_cast<std::uintptr_t>(expectedDevice));
    token = mix_readiness_snapshot_token(token, translation_identity_);
    token = mix_readiness_snapshot_token(token, bundle_generation_);
    token = token == 0 ? 1 : token;
    return token == readiness.snapshotToken;
}

void NativeFixedFunctionRenderStateBundle::shutdown() noexcept {
    rasterizer_state_.Reset();
    depth_stencil_state_.Reset();
    blend_state_.Reset();
    device_.Reset();
    stencil_ref_ = 0;
    translation_identity_ = 0;
}

bool NativeProgrammableShaderPairCache::initialize(
    ID3D11Device* device) noexcept {
    shutdown();
    if (!device)
        return false;

    device_ = device;
    ++owner_generation_;
    if (owner_generation_ == 0)
        ++owner_generation_;
    return true;
}

bool NativeProgrammableShaderPairCache::cache_for_observation(
    const ProgrammableShaderPairCacheIdentity& identity) noexcept {
    if (!ready() ||
        !identity.exact_identity() ||
        identity.translationImplemented)
        return false;

    const Entry candidate{
        identity.vertexShader.byteSize,
        identity.vertexShader.versionToken,
        identity.vertexShader.bytecodeHash,
        identity.pixelShader.byteSize,
        identity.pixelShader.versionToken,
        identity.pixelShader.bytecodeHash,
    };
    const auto same_entry = [](const Entry& a, const Entry& b) noexcept {
        return a.vertexByteSize == b.vertexByteSize &&
               a.vertexVersionToken == b.vertexVersionToken &&
               a.vertexBytecodeHash == b.vertexBytecodeHash &&
               a.pixelByteSize == b.pixelByteSize &&
               a.pixelVersionToken == b.pixelVersionToken &&
               a.pixelBytecodeHash == b.pixelBytecodeHash;
    };

    const auto found = entries_.find(identity.cacheKey);
    if (found != entries_.end())
        return same_entry(found->second, candidate);

    try {
        entries_.emplace(identity.cacheKey, candidate);
    } catch (...) {
        return false;
    }
    return true;
}

NativeProgrammableShaderPairCacheReadiness
NativeProgrammableShaderPairCache::readiness(
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity) const noexcept {
    NativeProgrammableShaderPairCacheReadiness out{};
    out.ownerReady = ready();
    out.ownerGeneration = owner_generation_;
    out.entryCount = entries_.size();
    out.cacheKey = identity.cacheKey;
    out.identityExact =
        identity.exact_identity() && !identity.translationImplemented;
    out.inputValid = expectedDevice != nullptr && out.identityExact;
    out.deviceMatches =
        out.ownerReady && expectedDevice != nullptr &&
        device_.Get() == expectedDevice;

    if (out.inputValid && out.ownerReady) {
        const auto found = entries_.find(identity.cacheKey);
        if (found != entries_.end()) {
            const Entry candidate{
                identity.vertexShader.byteSize,
                identity.vertexShader.versionToken,
                identity.vertexShader.bytecodeHash,
                identity.pixelShader.byteSize,
                identity.pixelShader.versionToken,
                identity.pixelShader.bytecodeHash,
            };
            const auto& cached = found->second;
            out.collisionFree =
                cached.vertexByteSize == candidate.vertexByteSize &&
                cached.vertexVersionToken == candidate.vertexVersionToken &&
                cached.vertexBytecodeHash == candidate.vertexBytecodeHash &&
                cached.pixelByteSize == candidate.pixelByteSize &&
                cached.pixelVersionToken == candidate.pixelVersionToken &&
                cached.pixelBytecodeHash == candidate.pixelBytecodeHash;
            out.cached = out.collisionFree;
        }
    }

    out.ready =
        out.inputValid &&
        out.ownerReady &&
        out.deviceMatches &&
        out.identityExact &&
        out.collisionFree &&
        out.cached &&
        out.ownerGeneration != 0 &&
        out.cacheKey != 0;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token,
            static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(this)));
        token = mix_readiness_snapshot_token(
            token,
            static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(expectedDevice)));
        token = mix_readiness_snapshot_token(token, out.ownerGeneration);
        token = mix_readiness_snapshot_token(token, out.cacheKey);
        token = mix_readiness_snapshot_token(
            token, identity.vertexShader.byteSize);
        token = mix_readiness_snapshot_token(
            token, identity.vertexShader.versionToken);
        token = mix_readiness_snapshot_token(
            token, identity.vertexShader.bytecodeHash);
        token = mix_readiness_snapshot_token(
            token, identity.pixelShader.byteSize);
        token = mix_readiness_snapshot_token(
            token, identity.pixelShader.versionToken);
        token = mix_readiness_snapshot_token(
            token, identity.pixelShader.bytecodeHash);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeProgrammableShaderPairCache::validate_snapshot(
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t snapshotToken) const noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = readiness(expectedDevice, identity);
    return current.ready && current.snapshotToken == snapshotToken;
}

bool NativeProgrammableShaderPairCache::reserve_translation_slot_for_observation(
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken) noexcept {
    if (!expectedDevice ||
        cacheSnapshotToken == 0 ||
        !validate_snapshot(expectedDevice, identity, cacheSnapshotToken))
        return false;

    const auto found = entries_.find(identity.cacheKey);
    if (found == entries_.end())
        return false;

    auto& entry = found->second;
    if (entry.translationSlotGeneration != 0)
        return true;

    ++translation_slot_generation_counter_;
    if (translation_slot_generation_counter_ == 0)
        ++translation_slot_generation_counter_;
    entry.translationSlotGeneration = translation_slot_generation_counter_;
    return true;
}

NativeProgrammableShaderTranslationSlotReadiness
NativeProgrammableShaderPairCache::translation_slot_ownership_readiness(
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken) const noexcept {
    NativeProgrammableShaderTranslationSlotReadiness out{};
    out.ownerGeneration = owner_generation_;
    out.cacheKey = identity.cacheKey;
    out.cacheSnapshotToken = cacheSnapshotToken;
    out.translationObjectsPresent = false;
    out.inputValid =
        expectedDevice != nullptr &&
        cacheSnapshotToken != 0 &&
        identity.exact_identity() &&
        !identity.translationImplemented;

    const auto cache = readiness(expectedDevice, identity);
    out.cacheReady = cache.ready;
    out.deviceMatches =
        cache.ownerReady &&
        expectedDevice != nullptr &&
        device_.Get() == expectedDevice;
    out.cacheSnapshotMatches =
        cache.ready && cache.snapshotToken == cacheSnapshotToken;

    if (out.inputValid &&
        out.cacheReady &&
        out.deviceMatches &&
        out.cacheSnapshotMatches) {
        const auto found = entries_.find(identity.cacheKey);
        if (found != entries_.end()) {
            out.slotGeneration = found->second.translationSlotGeneration;
            out.slotReserved = out.slotGeneration != 0;
        }
    }

    out.ownershipReady =
        out.inputValid &&
        out.cacheReady &&
        out.deviceMatches &&
        out.cacheSnapshotMatches &&
        out.slotReserved &&
        !out.translationObjectsPresent &&
        out.ownerGeneration != 0 &&
        out.slotGeneration != 0 &&
        out.cacheKey != 0;

    if (out.ownershipReady) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token,
            static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(this)));
        token = mix_readiness_snapshot_token(
            token,
            static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(expectedDevice)));
        token = mix_readiness_snapshot_token(token, out.ownerGeneration);
        token = mix_readiness_snapshot_token(token, out.slotGeneration);
        token = mix_readiness_snapshot_token(token, out.cacheKey);
        token = mix_readiness_snapshot_token(token, out.cacheSnapshotToken);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeProgrammableShaderPairCache::validate_translation_slot_snapshot(
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken) const noexcept {
    if (slotSnapshotToken == 0)
        return false;
    const auto current = translation_slot_ownership_readiness(
        expectedDevice, identity, cacheSnapshotToken);
    return current.ownershipReady &&
           current.snapshotToken == slotSnapshotToken;
}

bool NativeProgrammableShaderPairCache::attach_translation_objects_for_observation(
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    ID3D11VertexShader* vertexShader,
    ID3D11PixelShader* pixelShader) noexcept {
    if (!expectedDevice || !vertexShader || !pixelShader ||
        !validate_translation_slot_snapshot(
            expectedDevice, identity, cacheSnapshotToken, slotSnapshotToken))
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> vertexDevice;
    Microsoft::WRL::ComPtr<ID3D11Device> pixelDevice;
    vertexShader->GetDevice(vertexDevice.GetAddressOf());
    pixelShader->GetDevice(pixelDevice.GetAddressOf());
    if (vertexDevice.Get() != expectedDevice ||
        pixelDevice.Get() != expectedDevice)
        return false;

    const auto found = entries_.find(identity.cacheKey);
    if (found == entries_.end())
        return false;

    auto& entry = found->second;
    if (entry.translationSlotGeneration == 0)
        return false;

    const bool attachmentStarted =
        entry.translatedVertexShader ||
        entry.translatedPixelShader ||
        entry.translationObjectReceiptGeneration != 0;
    if (attachmentStarted) {
        return entry.translatedVertexShader.Get() == vertexShader &&
               entry.translatedPixelShader.Get() == pixelShader &&
               entry.translationObjectReceiptGeneration != 0;
    }

    entry.translatedVertexShader = vertexShader;
    entry.translatedPixelShader = pixelShader;
    ++translation_object_receipt_generation_counter_;
    if (translation_object_receipt_generation_counter_ == 0)
        ++translation_object_receipt_generation_counter_;
    entry.translationObjectReceiptGeneration =
        translation_object_receipt_generation_counter_;
    return true;
}

NativeProgrammableShaderTranslationObjectReadiness
NativeProgrammableShaderPairCache::translation_object_readiness(
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken) const noexcept {
    NativeProgrammableShaderTranslationObjectReadiness out{};
    out.ownerGeneration = owner_generation_;
    out.cacheKey = identity.cacheKey;
    out.cacheSnapshotToken = cacheSnapshotToken;
    out.slotSnapshotToken = slotSnapshotToken;
    out.inputValid =
        expectedDevice != nullptr &&
        cacheSnapshotToken != 0 &&
        slotSnapshotToken != 0 &&
        identity.exact_identity() &&
        !identity.translationImplemented;

    const auto slot = translation_slot_ownership_readiness(
        expectedDevice, identity, cacheSnapshotToken);
    out.slotReady = slot.ownershipReady;
    out.deviceMatches = slot.deviceMatches;
    out.cacheSnapshotMatches = slot.cacheSnapshotMatches;
    out.slotSnapshotMatches =
        slot.ownershipReady &&
        slot.snapshotToken == slotSnapshotToken;
    out.slotGeneration = slot.slotGeneration;

    if (out.inputValid &&
        out.slotReady &&
        out.deviceMatches &&
        out.cacheSnapshotMatches &&
        out.slotSnapshotMatches) {
        const auto found = entries_.find(identity.cacheKey);
        if (found != entries_.end()) {
            const auto& entry = found->second;
            out.translationObjectReceiptGeneration =
                entry.translationObjectReceiptGeneration;
            out.objectsAttached =
                entry.translatedVertexShader &&
                entry.translatedPixelShader &&
                out.translationObjectReceiptGeneration != 0;
            if (out.objectsAttached) {
                Microsoft::WRL::ComPtr<ID3D11Device> vertexDevice;
                Microsoft::WRL::ComPtr<ID3D11Device> pixelDevice;
                entry.translatedVertexShader->GetDevice(
                    vertexDevice.GetAddressOf());
                entry.translatedPixelShader->GetDevice(
                    pixelDevice.GetAddressOf());
                out.objectDevicesMatch =
                    vertexDevice.Get() == expectedDevice &&
                    pixelDevice.Get() == expectedDevice;
            }
        }
    }

    out.attachmentReady =
        out.inputValid &&
        out.slotReady &&
        out.deviceMatches &&
        out.cacheSnapshotMatches &&
        out.slotSnapshotMatches &&
        out.objectsAttached &&
        out.objectDevicesMatch &&
        out.ownerGeneration != 0 &&
        out.slotGeneration != 0 &&
        out.translationObjectReceiptGeneration != 0 &&
        out.cacheKey != 0;

    if (out.attachmentReady) {
        const auto found = entries_.find(identity.cacheKey);
        if (found == entries_.end())
            return {};
        const auto& entry = found->second;
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token,
            static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(this)));
        token = mix_readiness_snapshot_token(
            token,
            static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(expectedDevice)));
        token = mix_readiness_snapshot_token(token, out.ownerGeneration);
        token = mix_readiness_snapshot_token(token, out.slotGeneration);
        token = mix_readiness_snapshot_token(
            token, out.translationObjectReceiptGeneration);
        token = mix_readiness_snapshot_token(token, out.cacheKey);
        token = mix_readiness_snapshot_token(token, out.cacheSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.slotSnapshotToken);
        token = mix_readiness_snapshot_token(
            token,
            static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(
                    entry.translatedVertexShader.Get())));
        token = mix_readiness_snapshot_token(
            token,
            static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(
                    entry.translatedPixelShader.Get())));
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeProgrammableShaderPairCache::validate_translation_object_snapshot(
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken) const noexcept {
    if (objectSnapshotToken == 0)
        return false;
    const auto current = translation_object_readiness(
        expectedDevice, identity, cacheSnapshotToken, slotSnapshotToken);
    return current.attachmentReady &&
           current.snapshotToken == objectSnapshotToken;
}

bool NativeProgrammableShaderPairCache::attach_input_layout_for_observation(
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    ID3D11InputLayout* inputLayout) noexcept {
    const auto inputLayoutIdentity =
        hash_pipeline_input_layout_identity(layout);
    if (!expectedDevice ||
        !inputLayout ||
        inputLayoutIdentity == 0 ||
        !validate_translation_object_snapshot(
            expectedDevice,
            identity,
            cacheSnapshotToken,
            slotSnapshotToken,
            objectSnapshotToken))
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> inputLayoutDevice;
    inputLayout->GetDevice(inputLayoutDevice.GetAddressOf());
    if (inputLayoutDevice.Get() != expectedDevice)
        return false;

    const auto found = entries_.find(identity.cacheKey);
    if (found == entries_.end())
        return false;

    auto& entry = found->second;
    if (!entry.translatedVertexShader ||
        !entry.translatedPixelShader ||
        entry.translationObjectReceiptGeneration == 0)
        return false;

    const bool attachmentStarted =
        entry.translatedInputLayout ||
        entry.inputLayoutIdentity != 0 ||
        entry.inputLayoutReceiptGeneration != 0;
    if (attachmentStarted) {
        return entry.translatedInputLayout.Get() == inputLayout &&
               entry.inputLayoutIdentity == inputLayoutIdentity &&
               entry.inputLayoutReceiptGeneration != 0;
    }

    entry.translatedInputLayout = inputLayout;
    entry.inputLayoutIdentity = inputLayoutIdentity;
    ++input_layout_receipt_generation_counter_;
    if (input_layout_receipt_generation_counter_ == 0)
        ++input_layout_receipt_generation_counter_;
    entry.inputLayoutReceiptGeneration =
        input_layout_receipt_generation_counter_;
    return true;
}

NativeProgrammableShaderInputLayoutReadiness
NativeProgrammableShaderPairCache::input_layout_readiness(
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout) const noexcept {
    NativeProgrammableShaderInputLayoutReadiness out{};
    out.ownerGeneration = owner_generation_;
    out.cacheKey = identity.cacheKey;
    out.cacheSnapshotToken = cacheSnapshotToken;
    out.slotSnapshotToken = slotSnapshotToken;
    out.objectSnapshotToken = objectSnapshotToken;
    out.inputLayoutIdentity =
        hash_pipeline_input_layout_identity(layout);
    out.layoutIdentityExact = out.inputLayoutIdentity != 0;
    out.inputValid =
        expectedDevice != nullptr &&
        cacheSnapshotToken != 0 &&
        slotSnapshotToken != 0 &&
        objectSnapshotToken != 0 &&
        out.layoutIdentityExact &&
        identity.exact_identity() &&
        !identity.translationImplemented;

    const auto objects = translation_object_readiness(
        expectedDevice, identity, cacheSnapshotToken, slotSnapshotToken);
    out.objectReceiptReady = objects.attachmentReady;
    out.deviceMatches =
        objects.deviceMatches && objects.objectDevicesMatch;
    out.objectSnapshotMatches =
        objects.attachmentReady &&
        objects.snapshotToken == objectSnapshotToken;
    out.slotGeneration = objects.slotGeneration;
    out.translationObjectReceiptGeneration =
        objects.translationObjectReceiptGeneration;

    if (out.inputValid &&
        out.objectReceiptReady &&
        out.deviceMatches &&
        out.objectSnapshotMatches) {
        const auto found = entries_.find(identity.cacheKey);
        if (found != entries_.end()) {
            const auto& entry = found->second;
            out.inputLayoutReceiptGeneration =
                entry.inputLayoutReceiptGeneration;
            out.inputLayoutAttached =
                entry.translatedInputLayout &&
                entry.inputLayoutIdentity == out.inputLayoutIdentity &&
                out.inputLayoutReceiptGeneration != 0;
            if (out.inputLayoutAttached) {
                Microsoft::WRL::ComPtr<ID3D11Device> inputLayoutDevice;
                entry.translatedInputLayout->GetDevice(
                    inputLayoutDevice.GetAddressOf());
                out.inputLayoutDeviceMatches =
                    inputLayoutDevice.Get() == expectedDevice;
            }
        }
    }

    out.attachmentReady =
        out.inputValid &&
        out.objectReceiptReady &&
        out.deviceMatches &&
        out.objectSnapshotMatches &&
        out.layoutIdentityExact &&
        out.inputLayoutAttached &&
        out.inputLayoutDeviceMatches &&
        out.ownerGeneration != 0 &&
        out.slotGeneration != 0 &&
        out.translationObjectReceiptGeneration != 0 &&
        out.inputLayoutReceiptGeneration != 0 &&
        out.cacheKey != 0 &&
        out.inputLayoutIdentity != 0;

    if (out.attachmentReady) {
        const auto found = entries_.find(identity.cacheKey);
        if (found == entries_.end())
            return {};
        const auto& entry = found->second;

        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token,
            static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(this)));
        token = mix_readiness_snapshot_token(
            token,
            static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(expectedDevice)));
        token = mix_readiness_snapshot_token(token, out.ownerGeneration);
        token = mix_readiness_snapshot_token(token, out.slotGeneration);
        token = mix_readiness_snapshot_token(
            token, out.translationObjectReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.inputLayoutReceiptGeneration);
        token = mix_readiness_snapshot_token(token, out.cacheKey);
        token = mix_readiness_snapshot_token(token, out.inputLayoutIdentity);
        token = mix_readiness_snapshot_token(token, out.cacheSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.slotSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.objectSnapshotToken);
        token = mix_readiness_snapshot_token(
            token,
            static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(
                    entry.translatedInputLayout.Get())));
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeProgrammableShaderPairCache::validate_input_layout_snapshot(
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken) const noexcept {
    if (inputLayoutSnapshotToken == 0)
        return false;
    const auto current = input_layout_readiness(
        expectedDevice,
        identity,
        cacheSnapshotToken,
        slotSnapshotToken,
        objectSnapshotToken,
        layout);
    return current.attachmentReady &&
           current.snapshotToken == inputLayoutSnapshotToken;
}


bool NativeProgrammableShaderPairCache::attach_constant_state_for_observation(
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    ID3D11Buffer* vertexConstantBuffer,
    UINT vertexConstantBytes,
    ID3D11Buffer* pixelConstantBuffer,
    UINT pixelConstantBytes) noexcept {
    if (!expectedDevice || !vertexConstantBuffer || !pixelConstantBuffer ||
        vertexConstantBytes == 0 || pixelConstantBytes == 0 ||
        (vertexConstantBytes & 15u) != 0 ||
        (pixelConstantBytes & 15u) != 0 ||
        !validate_input_layout_snapshot(
            expectedDevice, identity, cacheSnapshotToken, slotSnapshotToken,
            objectSnapshotToken, layout, inputLayoutSnapshotToken))
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> vertexConstantDevice;
    Microsoft::WRL::ComPtr<ID3D11Device> pixelConstantDevice;
    vertexConstantBuffer->GetDevice(vertexConstantDevice.GetAddressOf());
    pixelConstantBuffer->GetDevice(pixelConstantDevice.GetAddressOf());
    if (vertexConstantDevice.Get() != expectedDevice ||
        pixelConstantDevice.Get() != expectedDevice)
        return false;

    D3D11_BUFFER_DESC vertexDesc{};
    D3D11_BUFFER_DESC pixelDesc{};
    vertexConstantBuffer->GetDesc(&vertexDesc);
    pixelConstantBuffer->GetDesc(&pixelDesc);
    const auto descriptor_exact = [](const D3D11_BUFFER_DESC& desc,
                                     UINT expectedBytes) noexcept {
        return desc.ByteWidth == expectedBytes &&
               desc.Usage == D3D11_USAGE_DEFAULT &&
               desc.BindFlags == D3D11_BIND_CONSTANT_BUFFER &&
               desc.CPUAccessFlags == 0 &&
               desc.MiscFlags == 0 &&
               desc.StructureByteStride == 0;
    };
    if (!descriptor_exact(vertexDesc, vertexConstantBytes) ||
        !descriptor_exact(pixelDesc, pixelConstantBytes))
        return false;

    const auto found = entries_.find(identity.cacheKey);
    if (found == entries_.end())
        return false;
    auto& entry = found->second;
    if (!entry.translatedInputLayout ||
        entry.inputLayoutIdentity == 0 ||
        entry.inputLayoutReceiptGeneration == 0)
        return false;

    const bool attachmentStarted =
        entry.translatedVertexConstantBuffer ||
        entry.translatedPixelConstantBuffer ||
        entry.vertexConstantBytes != 0 ||
        entry.pixelConstantBytes != 0 ||
        entry.constantStateReceiptGeneration != 0;
    if (attachmentStarted) {
        return entry.translatedVertexConstantBuffer.Get() == vertexConstantBuffer &&
               entry.translatedPixelConstantBuffer.Get() == pixelConstantBuffer &&
               entry.vertexConstantBytes == vertexConstantBytes &&
               entry.pixelConstantBytes == pixelConstantBytes &&
               entry.constantStateReceiptGeneration != 0;
    }

    entry.translatedVertexConstantBuffer = vertexConstantBuffer;
    entry.translatedPixelConstantBuffer = pixelConstantBuffer;
    entry.vertexConstantBytes = vertexConstantBytes;
    entry.pixelConstantBytes = pixelConstantBytes;
    ++constant_state_receipt_generation_counter_;
    if (constant_state_receipt_generation_counter_ == 0)
        ++constant_state_receipt_generation_counter_;
    entry.constantStateReceiptGeneration =
        constant_state_receipt_generation_counter_;
    return true;
}

NativeProgrammableShaderConstantStateReadiness
NativeProgrammableShaderPairCache::constant_state_readiness(
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken) const noexcept {
    NativeProgrammableShaderConstantStateReadiness out{};
    out.ownerGeneration = owner_generation_;
    out.cacheKey = identity.cacheKey;
    out.cacheSnapshotToken = cacheSnapshotToken;
    out.slotSnapshotToken = slotSnapshotToken;
    out.objectSnapshotToken = objectSnapshotToken;
    out.inputLayoutSnapshotToken = inputLayoutSnapshotToken;
    out.inputLayoutIdentity = hash_pipeline_input_layout_identity(layout);
    out.inputValid =
        expectedDevice != nullptr && cacheSnapshotToken != 0 &&
        slotSnapshotToken != 0 && objectSnapshotToken != 0 &&
        inputLayoutSnapshotToken != 0 && out.inputLayoutIdentity != 0 &&
        identity.exact_identity() && !identity.translationImplemented;

    const auto inputLayout = input_layout_readiness(
        expectedDevice, identity, cacheSnapshotToken, slotSnapshotToken,
        objectSnapshotToken, layout);
    out.inputLayoutReceiptReady = inputLayout.attachmentReady;
    out.deviceMatches =
        inputLayout.deviceMatches && inputLayout.inputLayoutDeviceMatches;
    out.inputLayoutSnapshotMatches =
        inputLayout.attachmentReady &&
        inputLayout.snapshotToken == inputLayoutSnapshotToken;
    out.slotGeneration = inputLayout.slotGeneration;
    out.translationObjectReceiptGeneration =
        inputLayout.translationObjectReceiptGeneration;
    out.inputLayoutReceiptGeneration =
        inputLayout.inputLayoutReceiptGeneration;

    if (out.inputValid && out.inputLayoutReceiptReady &&
        out.deviceMatches && out.inputLayoutSnapshotMatches) {
        const auto found = entries_.find(identity.cacheKey);
        if (found != entries_.end()) {
            const auto& entry = found->second;
            out.constantStateReceiptGeneration =
                entry.constantStateReceiptGeneration;
            out.vertexConstantBytes = entry.vertexConstantBytes;
            out.pixelConstantBytes = entry.pixelConstantBytes;
            out.constantBuffersAttached =
                entry.translatedVertexConstantBuffer &&
                entry.translatedPixelConstantBuffer &&
                out.vertexConstantBytes != 0 &&
                out.pixelConstantBytes != 0 &&
                out.constantStateReceiptGeneration != 0;
            if (out.constantBuffersAttached) {
                Microsoft::WRL::ComPtr<ID3D11Device> vertexConstantDevice;
                Microsoft::WRL::ComPtr<ID3D11Device> pixelConstantDevice;
                entry.translatedVertexConstantBuffer->GetDevice(
                    vertexConstantDevice.GetAddressOf());
                entry.translatedPixelConstantBuffer->GetDevice(
                    pixelConstantDevice.GetAddressOf());
                out.constantBufferDevicesMatch =
                    vertexConstantDevice.Get() == expectedDevice &&
                    pixelConstantDevice.Get() == expectedDevice;
                D3D11_BUFFER_DESC vertexDesc{};
                D3D11_BUFFER_DESC pixelDesc{};
                entry.translatedVertexConstantBuffer->GetDesc(&vertexDesc);
                entry.translatedPixelConstantBuffer->GetDesc(&pixelDesc);
                const auto descriptor_exact =
                    [](const D3D11_BUFFER_DESC& desc,
                       UINT expectedBytes) noexcept {
                        return desc.ByteWidth == expectedBytes &&
                               desc.Usage == D3D11_USAGE_DEFAULT &&
                               desc.BindFlags == D3D11_BIND_CONSTANT_BUFFER &&
                               desc.CPUAccessFlags == 0 &&
                               desc.MiscFlags == 0 &&
                               desc.StructureByteStride == 0;
                    };
                out.constantBufferDescriptorsExact =
                    descriptor_exact(vertexDesc, out.vertexConstantBytes) &&
                    descriptor_exact(pixelDesc, out.pixelConstantBytes);
            }
        }
    }

    out.attachmentReady =
        out.inputValid && out.inputLayoutReceiptReady &&
        out.deviceMatches && out.inputLayoutSnapshotMatches &&
        out.constantBuffersAttached && out.constantBufferDevicesMatch &&
        out.constantBufferDescriptorsExact &&
        out.ownerGeneration != 0 && out.slotGeneration != 0 &&
        out.translationObjectReceiptGeneration != 0 &&
        out.inputLayoutReceiptGeneration != 0 &&
        out.constantStateReceiptGeneration != 0 &&
        out.cacheKey != 0 && out.inputLayoutIdentity != 0 &&
        out.vertexConstantBytes != 0 && out.pixelConstantBytes != 0;

    if (out.attachmentReady) {
        const auto found = entries_.find(identity.cacheKey);
        if (found == entries_.end())
            return {};
        const auto& entry = found->second;
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(this)));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(expectedDevice)));
        token = mix_readiness_snapshot_token(token, out.ownerGeneration);
        token = mix_readiness_snapshot_token(token, out.slotGeneration);
        token = mix_readiness_snapshot_token(
            token, out.translationObjectReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.inputLayoutReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.constantStateReceiptGeneration);
        token = mix_readiness_snapshot_token(token, out.cacheKey);
        token = mix_readiness_snapshot_token(token, out.inputLayoutIdentity);
        token = mix_readiness_snapshot_token(token, out.vertexConstantBytes);
        token = mix_readiness_snapshot_token(token, out.pixelConstantBytes);
        token = mix_readiness_snapshot_token(token, out.cacheSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.slotSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.objectSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.inputLayoutSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(
                    entry.translatedVertexConstantBuffer.Get())));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(
                    entry.translatedPixelConstantBuffer.Get())));
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeProgrammableShaderPairCache::validate_constant_state_snapshot(
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken) const noexcept {
    if (constantStateSnapshotToken == 0)
        return false;
    const auto current = constant_state_readiness(
        expectedDevice, identity, cacheSnapshotToken, slotSnapshotToken,
        objectSnapshotToken, layout, inputLayoutSnapshotToken);
    return current.attachmentReady &&
           current.snapshotToken == constantStateSnapshotToken;
}

bool NativeProgrammableShaderPairCache::upload_constant_payload_for_observation(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    const void* vertexPayload,
    UINT vertexPayloadBytes,
    const void* pixelPayload,
    UINT pixelPayloadBytes) noexcept {
    if (!expectedContext || !expectedDevice ||
        !vertexPayload || !pixelPayload ||
        vertexPayloadBytes == 0 || pixelPayloadBytes == 0 ||
        !validate_constant_state_snapshot(
            expectedDevice, identity, cacheSnapshotToken, slotSnapshotToken,
            objectSnapshotToken, layout, inputLayoutSnapshotToken,
            constantStateSnapshotToken))
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    expectedContext->GetDevice(contextDevice.GetAddressOf());
    Microsoft::WRL::ComPtr<ID3D11DeviceContext> immediateContext;
    expectedDevice->GetImmediateContext(immediateContext.GetAddressOf());
    if (contextDevice.Get() != expectedDevice ||
        immediateContext.Get() != expectedContext)
        return false;

    const auto found = entries_.find(identity.cacheKey);
    if (found == entries_.end())
        return false;
    auto& entry = found->second;
    if (!entry.translatedVertexConstantBuffer ||
        !entry.translatedPixelConstantBuffer ||
        entry.vertexConstantBytes == 0 || entry.pixelConstantBytes == 0 ||
        entry.constantStateReceiptGeneration == 0 ||
        vertexPayloadBytes != entry.vertexConstantBytes ||
        pixelPayloadBytes != entry.pixelConstantBytes)
        return false;

    const auto vertexPayloadHash =
        hash_observation_payload_bytes(vertexPayload, vertexPayloadBytes);
    const auto pixelPayloadHash =
        hash_observation_payload_bytes(pixelPayload, pixelPayloadBytes);
    if (vertexPayloadHash == 0 || pixelPayloadHash == 0)
        return false;

    const bool uploadStarted =
        entry.constantUploadContext ||
        entry.vertexConstantPayloadHash != 0 ||
        entry.pixelConstantPayloadHash != 0 ||
        entry.constantPayloadReceiptGeneration != 0;
    if (uploadStarted) {
        return entry.constantUploadContext.Get() == expectedContext &&
               entry.vertexConstantPayloadHash == vertexPayloadHash &&
               entry.pixelConstantPayloadHash == pixelPayloadHash &&
               entry.constantPayloadReceiptGeneration != 0;
    }

    expectedContext->UpdateSubresource(
        entry.translatedVertexConstantBuffer.Get(), 0, nullptr,
        vertexPayload, 0, 0);
    expectedContext->UpdateSubresource(
        entry.translatedPixelConstantBuffer.Get(), 0, nullptr,
        pixelPayload, 0, 0);
    entry.constantUploadContext = expectedContext;
    entry.vertexConstantPayloadHash = vertexPayloadHash;
    entry.pixelConstantPayloadHash = pixelPayloadHash;
    ++constant_payload_receipt_generation_counter_;
    if (constant_payload_receipt_generation_counter_ == 0)
        ++constant_payload_receipt_generation_counter_;
    entry.constantPayloadReceiptGeneration =
        constant_payload_receipt_generation_counter_;
    return true;
}

NativeProgrammableShaderConstantPayloadReadiness
NativeProgrammableShaderPairCache::constant_payload_readiness(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken) const noexcept {
    NativeProgrammableShaderConstantPayloadReadiness out{};
    out.ownerGeneration = owner_generation_;
    out.cacheKey = identity.cacheKey;
    out.cacheSnapshotToken = cacheSnapshotToken;
    out.slotSnapshotToken = slotSnapshotToken;
    out.objectSnapshotToken = objectSnapshotToken;
    out.inputLayoutSnapshotToken = inputLayoutSnapshotToken;
    out.constantStateSnapshotToken = constantStateSnapshotToken;
    out.inputLayoutIdentity = hash_pipeline_input_layout_identity(layout);
    out.inputValid =
        expectedContext != nullptr && expectedDevice != nullptr &&
        constantStateSnapshotToken != 0 && out.inputLayoutIdentity != 0 &&
        identity.exact_identity() && !identity.translationImplemented;

    const auto constantState = constant_state_readiness(
        expectedDevice, identity, cacheSnapshotToken, slotSnapshotToken,
        objectSnapshotToken, layout, inputLayoutSnapshotToken);
    out.constantStateReceiptReady = constantState.attachmentReady;
    out.deviceMatches = constantState.deviceMatches &&
                        constantState.constantBufferDevicesMatch;
    out.constantStateSnapshotMatches =
        constantState.attachmentReady &&
        constantState.snapshotToken == constantStateSnapshotToken;
    out.slotGeneration = constantState.slotGeneration;
    out.translationObjectReceiptGeneration =
        constantState.translationObjectReceiptGeneration;
    out.inputLayoutReceiptGeneration =
        constantState.inputLayoutReceiptGeneration;
    out.constantStateReceiptGeneration =
        constantState.constantStateReceiptGeneration;
    out.vertexConstantBytes = constantState.vertexConstantBytes;
    out.pixelConstantBytes = constantState.pixelConstantBytes;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    Microsoft::WRL::ComPtr<ID3D11DeviceContext> immediateContext;
    if (expectedContext)
        expectedContext->GetDevice(contextDevice.GetAddressOf());
    if (expectedDevice)
        expectedDevice->GetImmediateContext(immediateContext.GetAddressOf());
    out.contextDeviceMatches =
        expectedDevice != nullptr &&
        contextDevice.Get() == expectedDevice &&
        immediateContext.Get() == expectedContext;

    if (out.inputValid && out.constantStateReceiptReady &&
        out.deviceMatches && out.contextDeviceMatches &&
        out.constantStateSnapshotMatches) {
        const auto found = entries_.find(identity.cacheKey);
        if (found != entries_.end()) {
            const auto& entry = found->second;
            out.constantPayloadReceiptGeneration =
                entry.constantPayloadReceiptGeneration;
            out.vertexPayloadHash = entry.vertexConstantPayloadHash;
            out.pixelPayloadHash = entry.pixelConstantPayloadHash;
            out.payloadReceiptPresent =
                entry.constantUploadContext &&
                entry.constantUploadContext.Get() == expectedContext &&
                out.constantPayloadReceiptGeneration != 0 &&
                out.vertexPayloadHash != 0 && out.pixelPayloadHash != 0;
            out.payloadBytesExact =
                entry.vertexConstantBytes == out.vertexConstantBytes &&
                entry.pixelConstantBytes == out.pixelConstantBytes &&
                out.vertexConstantBytes != 0 && out.pixelConstantBytes != 0;
        }
    }

    out.uploadReady =
        out.inputValid && out.constantStateReceiptReady &&
        out.deviceMatches && out.contextDeviceMatches &&
        out.constantStateSnapshotMatches &&
        out.payloadReceiptPresent && out.payloadBytesExact &&
        out.ownerGeneration != 0 && out.slotGeneration != 0 &&
        out.translationObjectReceiptGeneration != 0 &&
        out.inputLayoutReceiptGeneration != 0 &&
        out.constantStateReceiptGeneration != 0 &&
        out.constantPayloadReceiptGeneration != 0 &&
        out.cacheKey != 0 && out.inputLayoutIdentity != 0 &&
        out.vertexPayloadHash != 0 && out.pixelPayloadHash != 0;

    if (out.uploadReady) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(this)));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(expectedContext)));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(expectedDevice)));
        token = mix_readiness_snapshot_token(token, out.ownerGeneration);
        token = mix_readiness_snapshot_token(token, out.slotGeneration);
        token = mix_readiness_snapshot_token(
            token, out.translationObjectReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.inputLayoutReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.constantStateReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.constantPayloadReceiptGeneration);
        token = mix_readiness_snapshot_token(token, out.cacheKey);
        token = mix_readiness_snapshot_token(token, out.inputLayoutIdentity);
        token = mix_readiness_snapshot_token(token, out.vertexConstantBytes);
        token = mix_readiness_snapshot_token(token, out.pixelConstantBytes);
        token = mix_readiness_snapshot_token(token, out.vertexPayloadHash);
        token = mix_readiness_snapshot_token(token, out.pixelPayloadHash);
        token = mix_readiness_snapshot_token(token, out.cacheSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.slotSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.objectSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.inputLayoutSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.constantStateSnapshotToken);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeProgrammableShaderPairCache::validate_constant_payload_snapshot(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken) const noexcept {
    if (constantPayloadSnapshotToken == 0)
        return false;
    const auto current = constant_payload_readiness(
        expectedContext, expectedDevice, identity, cacheSnapshotToken,
        slotSnapshotToken, objectSnapshotToken, layout,
        inputLayoutSnapshotToken, constantStateSnapshotToken);
    return current.uploadReady &&
           current.snapshotToken == constantPayloadSnapshotToken;
}

bool NativeProgrammableShaderPairCache::bind_constant_slots_for_observation(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken) noexcept {
    if (!expectedContext || !expectedDevice ||
        !validate_constant_payload_snapshot(
            expectedContext, expectedDevice, identity, cacheSnapshotToken,
            slotSnapshotToken, objectSnapshotToken, layout,
            inputLayoutSnapshotToken, constantStateSnapshotToken,
            constantPayloadSnapshotToken))
        return false;

    const auto found = entries_.find(identity.cacheKey);
    if (found == entries_.end())
        return false;
    auto& entry = found->second;
    if (!entry.translatedVertexConstantBuffer ||
        !entry.translatedPixelConstantBuffer ||
        !entry.constantUploadContext ||
        entry.constantUploadContext.Get() != expectedContext ||
        entry.constantPayloadReceiptGeneration == 0)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    Microsoft::WRL::ComPtr<ID3D11DeviceContext> immediateContext;
    expectedContext->GetDevice(contextDevice.GetAddressOf());
    expectedDevice->GetImmediateContext(immediateContext.GetAddressOf());
    if (contextDevice.Get() != expectedDevice ||
        immediateContext.Get() != expectedContext)
        return false;

    const bool bindingStarted =
        entry.constantBindingContext ||
        entry.constantBindingReceiptGeneration != 0;
    if (bindingStarted) {
        if (entry.constantBindingContext.Get() != expectedContext ||
            entry.constantBindingReceiptGeneration == 0)
            return false;
        Microsoft::WRL::ComPtr<ID3D11Buffer> currentVertex;
        Microsoft::WRL::ComPtr<ID3D11Buffer> currentPixel;
        expectedContext->VSGetConstantBuffers(
            0, 1, currentVertex.GetAddressOf());
        expectedContext->PSGetConstantBuffers(
            0, 1, currentPixel.GetAddressOf());
        return currentVertex.Get() ==
                   entry.translatedVertexConstantBuffer.Get() &&
               currentPixel.Get() ==
                   entry.translatedPixelConstantBuffer.Get();
    }

    ID3D11Buffer* vertexBuffer =
        entry.translatedVertexConstantBuffer.Get();
    ID3D11Buffer* pixelBuffer =
        entry.translatedPixelConstantBuffer.Get();
    expectedContext->VSSetConstantBuffers(0, 1, &vertexBuffer);
    expectedContext->PSSetConstantBuffers(0, 1, &pixelBuffer);

    Microsoft::WRL::ComPtr<ID3D11Buffer> currentVertex;
    Microsoft::WRL::ComPtr<ID3D11Buffer> currentPixel;
    expectedContext->VSGetConstantBuffers(
        0, 1, currentVertex.GetAddressOf());
    expectedContext->PSGetConstantBuffers(
        0, 1, currentPixel.GetAddressOf());
    if (currentVertex.Get() != entry.translatedVertexConstantBuffer.Get() ||
        currentPixel.Get() != entry.translatedPixelConstantBuffer.Get())
        return false;

    entry.constantBindingContext = expectedContext;
    ++constant_binding_receipt_generation_counter_;
    if (constant_binding_receipt_generation_counter_ == 0)
        ++constant_binding_receipt_generation_counter_;
    entry.constantBindingReceiptGeneration =
        constant_binding_receipt_generation_counter_;
    return true;
}

NativeProgrammableShaderConstantBindingReadiness
NativeProgrammableShaderPairCache::constant_binding_readiness(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken) const noexcept {
    NativeProgrammableShaderConstantBindingReadiness out{};
    out.ownerGeneration = owner_generation_;
    out.cacheKey = identity.cacheKey;
    out.cacheSnapshotToken = cacheSnapshotToken;
    out.slotSnapshotToken = slotSnapshotToken;
    out.objectSnapshotToken = objectSnapshotToken;
    out.inputLayoutSnapshotToken = inputLayoutSnapshotToken;
    out.constantStateSnapshotToken = constantStateSnapshotToken;
    out.constantPayloadSnapshotToken = constantPayloadSnapshotToken;
    out.inputLayoutIdentity = hash_pipeline_input_layout_identity(layout);
    out.inputValid =
        expectedContext != nullptr && expectedDevice != nullptr &&
        constantPayloadSnapshotToken != 0 &&
        out.inputLayoutIdentity != 0 &&
        identity.exact_identity() && !identity.translationImplemented;

    const auto payload = constant_payload_readiness(
        expectedContext, expectedDevice, identity, cacheSnapshotToken,
        slotSnapshotToken, objectSnapshotToken, layout,
        inputLayoutSnapshotToken, constantStateSnapshotToken);
    out.constantPayloadReceiptReady = payload.uploadReady;
    out.deviceMatches = payload.deviceMatches;
    out.contextDeviceMatches = payload.contextDeviceMatches;
    out.constantPayloadSnapshotMatches =
        payload.uploadReady &&
        payload.snapshotToken == constantPayloadSnapshotToken;
    out.slotGeneration = payload.slotGeneration;
    out.translationObjectReceiptGeneration =
        payload.translationObjectReceiptGeneration;
    out.inputLayoutReceiptGeneration =
        payload.inputLayoutReceiptGeneration;
    out.constantStateReceiptGeneration =
        payload.constantStateReceiptGeneration;
    out.constantPayloadReceiptGeneration =
        payload.constantPayloadReceiptGeneration;
    out.vertexConstantBytes = payload.vertexConstantBytes;
    out.pixelConstantBytes = payload.pixelConstantBytes;
    out.vertexPayloadHash = payload.vertexPayloadHash;
    out.pixelPayloadHash = payload.pixelPayloadHash;

    if (out.inputValid && out.constantPayloadReceiptReady &&
        out.deviceMatches && out.contextDeviceMatches &&
        out.constantPayloadSnapshotMatches) {
        const auto found = entries_.find(identity.cacheKey);
        if (found != entries_.end()) {
            const auto& entry = found->second;
            out.constantBindingReceiptGeneration =
                entry.constantBindingReceiptGeneration;
            out.bindingReceiptPresent =
                entry.constantBindingContext &&
                entry.constantBindingContext.Get() == expectedContext &&
                out.constantBindingReceiptGeneration != 0;
            Microsoft::WRL::ComPtr<ID3D11Buffer> currentVertex;
            Microsoft::WRL::ComPtr<ID3D11Buffer> currentPixel;
            expectedContext->VSGetConstantBuffers(
                0, 1, currentVertex.GetAddressOf());
            expectedContext->PSGetConstantBuffers(
                0, 1, currentPixel.GetAddressOf());
            out.vertexSlotMatches =
                currentVertex.Get() ==
                entry.translatedVertexConstantBuffer.Get();
            out.pixelSlotMatches =
                currentPixel.Get() ==
                entry.translatedPixelConstantBuffer.Get();
        }
    }

    out.bindingReady =
        out.inputValid && out.constantPayloadReceiptReady &&
        out.deviceMatches && out.contextDeviceMatches &&
        out.constantPayloadSnapshotMatches &&
        out.bindingReceiptPresent &&
        out.vertexSlotMatches && out.pixelSlotMatches &&
        out.ownerGeneration != 0 && out.slotGeneration != 0 &&
        out.translationObjectReceiptGeneration != 0 &&
        out.inputLayoutReceiptGeneration != 0 &&
        out.constantStateReceiptGeneration != 0 &&
        out.constantPayloadReceiptGeneration != 0 &&
        out.constantBindingReceiptGeneration != 0 &&
        out.cacheKey != 0 && out.inputLayoutIdentity != 0 &&
        out.vertexPayloadHash != 0 && out.pixelPayloadHash != 0;

    if (out.bindingReady) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(this)));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(expectedContext)));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(expectedDevice)));
        token = mix_readiness_snapshot_token(token, out.ownerGeneration);
        token = mix_readiness_snapshot_token(token, out.slotGeneration);
        token = mix_readiness_snapshot_token(
            token, out.translationObjectReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.inputLayoutReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.constantStateReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.constantPayloadReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.constantBindingReceiptGeneration);
        token = mix_readiness_snapshot_token(token, out.cacheKey);
        token = mix_readiness_snapshot_token(
            token, out.inputLayoutIdentity);
        token = mix_readiness_snapshot_token(
            token, out.vertexConstantBytes);
        token = mix_readiness_snapshot_token(
            token, out.pixelConstantBytes);
        token = mix_readiness_snapshot_token(
            token, out.vertexPayloadHash);
        token = mix_readiness_snapshot_token(
            token, out.pixelPayloadHash);
        token = mix_readiness_snapshot_token(
            token, out.cacheSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.slotSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.objectSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.inputLayoutSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.constantStateSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.constantPayloadSnapshotToken);
        const auto found = entries_.find(identity.cacheKey);
        if (found != entries_.end()) {
            token = mix_readiness_snapshot_token(
                token, static_cast<std::uint64_t>(
                    reinterpret_cast<std::uintptr_t>(
                        found->second.translatedVertexConstantBuffer.Get())));
            token = mix_readiness_snapshot_token(
                token, static_cast<std::uint64_t>(
                    reinterpret_cast<std::uintptr_t>(
                        found->second.translatedPixelConstantBuffer.Get())));
        }
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeProgrammableShaderPairCache::validate_constant_binding_snapshot(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken,
    std::uint64_t constantBindingSnapshotToken) const noexcept {
    if (constantBindingSnapshotToken == 0)
        return false;
    const auto current = constant_binding_readiness(
        expectedContext, expectedDevice, identity, cacheSnapshotToken,
        slotSnapshotToken, objectSnapshotToken, layout,
        inputLayoutSnapshotToken, constantStateSnapshotToken,
        constantPayloadSnapshotToken);
    return current.bindingReady &&
           current.snapshotToken == constantBindingSnapshotToken;
}

bool NativeProgrammableShaderPairCache::bind_pipeline_objects_for_observation(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken,
    std::uint64_t constantBindingSnapshotToken) noexcept {
    if (!expectedContext || !expectedDevice ||
        !validate_constant_binding_snapshot(
            expectedContext, expectedDevice, identity, cacheSnapshotToken,
            slotSnapshotToken, objectSnapshotToken, layout,
            inputLayoutSnapshotToken, constantStateSnapshotToken,
            constantPayloadSnapshotToken, constantBindingSnapshotToken))
        return false;

    const auto found = entries_.find(identity.cacheKey);
    if (found == entries_.end())
        return false;
    auto& entry = found->second;
    if (!entry.translatedVertexShader || !entry.translatedPixelShader ||
        !entry.translatedInputLayout ||
        entry.translationObjectReceiptGeneration == 0 ||
        entry.inputLayoutReceiptGeneration == 0 ||
        !entry.constantBindingContext ||
        entry.constantBindingContext.Get() != expectedContext ||
        entry.constantBindingReceiptGeneration == 0)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    Microsoft::WRL::ComPtr<ID3D11DeviceContext> immediateContext;
    expectedContext->GetDevice(contextDevice.GetAddressOf());
    expectedDevice->GetImmediateContext(immediateContext.GetAddressOf());
    if (contextDevice.Get() != expectedDevice ||
        immediateContext.Get() != expectedContext)
        return false;

    const bool bindingStarted =
        entry.programmableBindingContext ||
        entry.programmableBindingReceiptGeneration != 0;
    if (bindingStarted) {
        if (entry.programmableBindingContext.Get() != expectedContext ||
            entry.programmableBindingReceiptGeneration == 0)
            return false;
        Microsoft::WRL::ComPtr<ID3D11VertexShader> currentVertexShader;
        Microsoft::WRL::ComPtr<ID3D11PixelShader> currentPixelShader;
        Microsoft::WRL::ComPtr<ID3D11InputLayout> currentInputLayout;
        expectedContext->VSGetShader(
            currentVertexShader.GetAddressOf(), nullptr, nullptr);
        expectedContext->PSGetShader(
            currentPixelShader.GetAddressOf(), nullptr, nullptr);
        expectedContext->IAGetInputLayout(
            currentInputLayout.GetAddressOf());
        return currentVertexShader.Get() == entry.translatedVertexShader.Get() &&
               currentPixelShader.Get() == entry.translatedPixelShader.Get() &&
               currentInputLayout.Get() == entry.translatedInputLayout.Get();
    }

    expectedContext->VSSetShader(
        entry.translatedVertexShader.Get(), nullptr, 0);
    expectedContext->PSSetShader(
        entry.translatedPixelShader.Get(), nullptr, 0);
    expectedContext->IASetInputLayout(entry.translatedInputLayout.Get());

    Microsoft::WRL::ComPtr<ID3D11VertexShader> currentVertexShader;
    Microsoft::WRL::ComPtr<ID3D11PixelShader> currentPixelShader;
    Microsoft::WRL::ComPtr<ID3D11InputLayout> currentInputLayout;
    expectedContext->VSGetShader(
        currentVertexShader.GetAddressOf(), nullptr, nullptr);
    expectedContext->PSGetShader(
        currentPixelShader.GetAddressOf(), nullptr, nullptr);
    expectedContext->IAGetInputLayout(currentInputLayout.GetAddressOf());
    if (currentVertexShader.Get() != entry.translatedVertexShader.Get() ||
        currentPixelShader.Get() != entry.translatedPixelShader.Get() ||
        currentInputLayout.Get() != entry.translatedInputLayout.Get())
        return false;

    entry.programmableBindingContext = expectedContext;
    ++programmable_binding_receipt_generation_counter_;
    if (programmable_binding_receipt_generation_counter_ == 0)
        ++programmable_binding_receipt_generation_counter_;
    entry.programmableBindingReceiptGeneration =
        programmable_binding_receipt_generation_counter_;
    return true;
}

NativeProgrammableShaderPipelineBindingReadiness
NativeProgrammableShaderPairCache::pipeline_binding_readiness(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken,
    std::uint64_t constantBindingSnapshotToken) const noexcept {
    NativeProgrammableShaderPipelineBindingReadiness out{};
    out.ownerGeneration = owner_generation_;
    out.cacheKey = identity.cacheKey;
    out.cacheSnapshotToken = cacheSnapshotToken;
    out.slotSnapshotToken = slotSnapshotToken;
    out.objectSnapshotToken = objectSnapshotToken;
    out.inputLayoutSnapshotToken = inputLayoutSnapshotToken;
    out.constantStateSnapshotToken = constantStateSnapshotToken;
    out.constantPayloadSnapshotToken = constantPayloadSnapshotToken;
    out.constantBindingSnapshotToken = constantBindingSnapshotToken;
    out.inputLayoutIdentity = hash_pipeline_input_layout_identity(layout);
    out.inputValid =
        expectedContext != nullptr && expectedDevice != nullptr &&
        constantBindingSnapshotToken != 0 &&
        out.inputLayoutIdentity != 0 &&
        identity.exact_identity() && !identity.translationImplemented;

    const auto constantBinding = constant_binding_readiness(
        expectedContext, expectedDevice, identity, cacheSnapshotToken,
        slotSnapshotToken, objectSnapshotToken, layout,
        inputLayoutSnapshotToken, constantStateSnapshotToken,
        constantPayloadSnapshotToken);
    out.constantBindingReceiptReady = constantBinding.bindingReady;
    out.deviceMatches = constantBinding.deviceMatches;
    out.contextDeviceMatches = constantBinding.contextDeviceMatches;
    out.constantBindingSnapshotMatches =
        constantBinding.bindingReady &&
        constantBinding.snapshotToken == constantBindingSnapshotToken;
    out.slotGeneration = constantBinding.slotGeneration;
    out.translationObjectReceiptGeneration =
        constantBinding.translationObjectReceiptGeneration;
    out.inputLayoutReceiptGeneration =
        constantBinding.inputLayoutReceiptGeneration;
    out.constantStateReceiptGeneration =
        constantBinding.constantStateReceiptGeneration;
    out.constantPayloadReceiptGeneration =
        constantBinding.constantPayloadReceiptGeneration;
    out.constantBindingReceiptGeneration =
        constantBinding.constantBindingReceiptGeneration;

    if (out.inputValid && out.constantBindingReceiptReady &&
        out.deviceMatches && out.contextDeviceMatches &&
        out.constantBindingSnapshotMatches) {
        const auto found = entries_.find(identity.cacheKey);
        if (found != entries_.end()) {
            const auto& entry = found->second;
            out.pipelineBindingReceiptGeneration =
                entry.programmableBindingReceiptGeneration;
            out.bindingReceiptPresent =
                entry.programmableBindingContext &&
                entry.programmableBindingContext.Get() == expectedContext &&
                out.pipelineBindingReceiptGeneration != 0;
            Microsoft::WRL::ComPtr<ID3D11VertexShader> currentVertexShader;
            Microsoft::WRL::ComPtr<ID3D11PixelShader> currentPixelShader;
            Microsoft::WRL::ComPtr<ID3D11InputLayout> currentInputLayout;
            expectedContext->VSGetShader(
                currentVertexShader.GetAddressOf(), nullptr, nullptr);
            expectedContext->PSGetShader(
                currentPixelShader.GetAddressOf(), nullptr, nullptr);
            expectedContext->IAGetInputLayout(
                currentInputLayout.GetAddressOf());
            out.vertexShaderMatches =
                currentVertexShader.Get() == entry.translatedVertexShader.Get();
            out.pixelShaderMatches =
                currentPixelShader.Get() == entry.translatedPixelShader.Get();
            out.inputLayoutMatches =
                currentInputLayout.Get() == entry.translatedInputLayout.Get();
        }
    }

    out.bindingReady =
        out.inputValid && out.constantBindingReceiptReady &&
        out.deviceMatches && out.contextDeviceMatches &&
        out.constantBindingSnapshotMatches &&
        out.bindingReceiptPresent &&
        out.vertexShaderMatches && out.pixelShaderMatches &&
        out.inputLayoutMatches &&
        out.ownerGeneration != 0 && out.slotGeneration != 0 &&
        out.translationObjectReceiptGeneration != 0 &&
        out.inputLayoutReceiptGeneration != 0 &&
        out.constantStateReceiptGeneration != 0 &&
        out.constantPayloadReceiptGeneration != 0 &&
        out.constantBindingReceiptGeneration != 0 &&
        out.pipelineBindingReceiptGeneration != 0 &&
        out.cacheKey != 0 && out.inputLayoutIdentity != 0;

    if (out.bindingReady) {
        const auto found = entries_.find(identity.cacheKey);
        if (found == entries_.end())
            return {};
        const auto& entry = found->second;
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(this)));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(expectedContext)));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(expectedDevice)));
        token = mix_readiness_snapshot_token(token, out.ownerGeneration);
        token = mix_readiness_snapshot_token(token, out.slotGeneration);
        token = mix_readiness_snapshot_token(
            token, out.translationObjectReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.inputLayoutReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.constantStateReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.constantPayloadReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.constantBindingReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.pipelineBindingReceiptGeneration);
        token = mix_readiness_snapshot_token(token, out.cacheKey);
        token = mix_readiness_snapshot_token(token, out.inputLayoutIdentity);
        token = mix_readiness_snapshot_token(token, out.cacheSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.slotSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.objectSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.inputLayoutSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.constantStateSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.constantPayloadSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.constantBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(
                    entry.translatedVertexShader.Get())));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(
                    entry.translatedPixelShader.Get())));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(
                    entry.translatedInputLayout.Get())));
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeProgrammableShaderPairCache::validate_pipeline_binding_snapshot(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken,
    std::uint64_t constantBindingSnapshotToken,
    std::uint64_t pipelineBindingSnapshotToken) const noexcept {
    if (pipelineBindingSnapshotToken == 0)
        return false;
    const auto current = pipeline_binding_readiness(
        expectedContext, expectedDevice, identity, cacheSnapshotToken,
        slotSnapshotToken, objectSnapshotToken, layout,
        inputLayoutSnapshotToken, constantStateSnapshotToken,
        constantPayloadSnapshotToken, constantBindingSnapshotToken);
    return current.bindingReady &&
           current.snapshotToken == pipelineBindingSnapshotToken;
}

bool NativeProgrammableShaderPairCache::bind_primitive_topology_for_observation(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken,
    std::uint64_t constantBindingSnapshotToken,
    std::uint64_t pipelineBindingSnapshotToken,
    D3DPRIMITIVETYPE primitiveType) noexcept {
    const auto topology = translate_primitive(primitiveType);
    if (!expectedContext || !expectedDevice || !topology.exact ||
        topology.value == D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED ||
        !validate_pipeline_binding_snapshot(
            expectedContext, expectedDevice, identity, cacheSnapshotToken,
            slotSnapshotToken, objectSnapshotToken, layout,
            inputLayoutSnapshotToken, constantStateSnapshotToken,
            constantPayloadSnapshotToken, constantBindingSnapshotToken,
            pipelineBindingSnapshotToken))
        return false;

    const auto found = entries_.find(identity.cacheKey);
    if (found == entries_.end())
        return false;
    auto& entry = found->second;
    if (!entry.programmableBindingContext ||
        entry.programmableBindingContext.Get() != expectedContext ||
        entry.programmableBindingReceiptGeneration == 0)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    Microsoft::WRL::ComPtr<ID3D11DeviceContext> immediateContext;
    expectedContext->GetDevice(contextDevice.GetAddressOf());
    expectedDevice->GetImmediateContext(immediateContext.GetAddressOf());
    if (contextDevice.Get() != expectedDevice ||
        immediateContext.Get() != expectedContext)
        return false;

    const bool bindingStarted =
        entry.topologyBindingContext ||
        entry.boundPrimitiveTopology != D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED ||
        entry.topologyBindingReceiptGeneration != 0;
    if (bindingStarted) {
        if (entry.topologyBindingContext.Get() != expectedContext ||
            entry.boundPrimitiveTopology != topology.value ||
            entry.topologyBindingReceiptGeneration == 0)
            return false;
        D3D11_PRIMITIVE_TOPOLOGY current =
            D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
        expectedContext->IAGetPrimitiveTopology(&current);
        return current == entry.boundPrimitiveTopology;
    }

    expectedContext->IASetPrimitiveTopology(topology.value);
    D3D11_PRIMITIVE_TOPOLOGY current =
        D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    expectedContext->IAGetPrimitiveTopology(&current);
    if (current != topology.value)
        return false;

    entry.topologyBindingContext = expectedContext;
    entry.boundPrimitiveTopology = topology.value;
    ++topology_binding_receipt_generation_counter_;
    if (topology_binding_receipt_generation_counter_ == 0)
        ++topology_binding_receipt_generation_counter_;
    entry.topologyBindingReceiptGeneration =
        topology_binding_receipt_generation_counter_;
    return true;
}

NativeProgrammableShaderTopologyBindingReadiness
NativeProgrammableShaderPairCache::primitive_topology_binding_readiness(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken,
    std::uint64_t constantBindingSnapshotToken,
    std::uint64_t pipelineBindingSnapshotToken,
    D3DPRIMITIVETYPE primitiveType) const noexcept {
    NativeProgrammableShaderTopologyBindingReadiness out{};
    out.ownerGeneration = owner_generation_;
    out.cacheKey = identity.cacheKey;
    out.cacheSnapshotToken = cacheSnapshotToken;
    out.slotSnapshotToken = slotSnapshotToken;
    out.objectSnapshotToken = objectSnapshotToken;
    out.inputLayoutSnapshotToken = inputLayoutSnapshotToken;
    out.constantStateSnapshotToken = constantStateSnapshotToken;
    out.constantPayloadSnapshotToken = constantPayloadSnapshotToken;
    out.constantBindingSnapshotToken = constantBindingSnapshotToken;
    out.pipelineBindingSnapshotToken = pipelineBindingSnapshotToken;
    out.inputLayoutIdentity = hash_pipeline_input_layout_identity(layout);
    const auto topology = translate_primitive(primitiveType);
    out.topologyExact =
        topology.exact &&
        topology.value != D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    out.translatedTopology = topology.value;
    out.inputValid =
        expectedContext != nullptr && expectedDevice != nullptr &&
        pipelineBindingSnapshotToken != 0 &&
        out.inputLayoutIdentity != 0 &&
        identity.exact_identity() && !identity.translationImplemented;

    const auto pipeline = pipeline_binding_readiness(
        expectedContext, expectedDevice, identity, cacheSnapshotToken,
        slotSnapshotToken, objectSnapshotToken, layout,
        inputLayoutSnapshotToken, constantStateSnapshotToken,
        constantPayloadSnapshotToken, constantBindingSnapshotToken);
    out.pipelineBindingReceiptReady = pipeline.bindingReady;
    out.deviceMatches = pipeline.deviceMatches;
    out.contextDeviceMatches = pipeline.contextDeviceMatches;
    out.pipelineBindingSnapshotMatches =
        pipeline.bindingReady &&
        pipeline.snapshotToken == pipelineBindingSnapshotToken;
    out.slotGeneration = pipeline.slotGeneration;
    out.translationObjectReceiptGeneration =
        pipeline.translationObjectReceiptGeneration;
    out.inputLayoutReceiptGeneration =
        pipeline.inputLayoutReceiptGeneration;
    out.constantStateReceiptGeneration =
        pipeline.constantStateReceiptGeneration;
    out.constantPayloadReceiptGeneration =
        pipeline.constantPayloadReceiptGeneration;
    out.constantBindingReceiptGeneration =
        pipeline.constantBindingReceiptGeneration;
    out.pipelineBindingReceiptGeneration =
        pipeline.pipelineBindingReceiptGeneration;

    if (out.inputValid && out.pipelineBindingReceiptReady &&
        out.deviceMatches && out.contextDeviceMatches &&
        out.pipelineBindingSnapshotMatches && out.topologyExact) {
        const auto found = entries_.find(identity.cacheKey);
        if (found != entries_.end()) {
            const auto& entry = found->second;
            out.topologyBindingReceiptGeneration =
                entry.topologyBindingReceiptGeneration;
            out.topologyReceiptPresent =
                entry.topologyBindingContext &&
                entry.topologyBindingContext.Get() == expectedContext &&
                entry.boundPrimitiveTopology == out.translatedTopology &&
                out.topologyBindingReceiptGeneration != 0;
            D3D11_PRIMITIVE_TOPOLOGY current =
                D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
            expectedContext->IAGetPrimitiveTopology(&current);
            out.topologyMatches =
                current == out.translatedTopology &&
                current == entry.boundPrimitiveTopology;
        }
    }

    out.bindingReady =
        out.inputValid && out.pipelineBindingReceiptReady &&
        out.deviceMatches && out.contextDeviceMatches &&
        out.pipelineBindingSnapshotMatches && out.topologyExact &&
        out.topologyReceiptPresent && out.topologyMatches &&
        out.ownerGeneration != 0 && out.slotGeneration != 0 &&
        out.translationObjectReceiptGeneration != 0 &&
        out.inputLayoutReceiptGeneration != 0 &&
        out.constantStateReceiptGeneration != 0 &&
        out.constantPayloadReceiptGeneration != 0 &&
        out.constantBindingReceiptGeneration != 0 &&
        out.pipelineBindingReceiptGeneration != 0 &&
        out.topologyBindingReceiptGeneration != 0 &&
        out.cacheKey != 0 && out.inputLayoutIdentity != 0;

    if (out.bindingReady) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(this)));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(expectedContext)));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(expectedDevice)));
        token = mix_readiness_snapshot_token(token, out.ownerGeneration);
        token = mix_readiness_snapshot_token(token, out.slotGeneration);
        token = mix_readiness_snapshot_token(
            token, out.translationObjectReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.inputLayoutReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.constantStateReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.constantPayloadReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.constantBindingReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.pipelineBindingReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.topologyBindingReceiptGeneration);
        token = mix_readiness_snapshot_token(token, out.cacheKey);
        token = mix_readiness_snapshot_token(token, out.inputLayoutIdentity);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(out.translatedTopology));
        token = mix_readiness_snapshot_token(token, out.cacheSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.slotSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.objectSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.inputLayoutSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.constantStateSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.constantPayloadSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.constantBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.pipelineBindingSnapshotToken);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeProgrammableShaderPairCache::
validate_primitive_topology_binding_snapshot(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken,
    std::uint64_t constantBindingSnapshotToken,
    std::uint64_t pipelineBindingSnapshotToken,
    D3DPRIMITIVETYPE primitiveType,
    std::uint64_t topologyBindingSnapshotToken) const noexcept {
    if (topologyBindingSnapshotToken == 0)
        return false;
    const auto current = primitive_topology_binding_readiness(
        expectedContext, expectedDevice, identity, cacheSnapshotToken,
        slotSnapshotToken, objectSnapshotToken, layout,
        inputLayoutSnapshotToken, constantStateSnapshotToken,
        constantPayloadSnapshotToken, constantBindingSnapshotToken,
        pipelineBindingSnapshotToken, primitiveType);
    return current.bindingReady &&
           current.snapshotToken == topologyBindingSnapshotToken;
}

bool NativeProgrammableShaderPairCache::bind_indexed_geometry_for_observation(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken,
    std::uint64_t constantBindingSnapshotToken,
    std::uint64_t pipelineBindingSnapshotToken,
    D3DPRIMITIVETYPE primitiveType,
    std::uint64_t topologyBindingSnapshotToken,
    const NativeManagedBufferShadow& vertexBuffer,
    std::uint64_t vertexBufferSnapshotToken,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeManagedBufferShadow& indexBuffer,
    std::uint64_t indexBufferSnapshotToken,
    DXGI_FORMAT indexFormat,
    UINT indexOffset) noexcept {
    const UINT indexElementBytes =
        indexFormat == DXGI_FORMAT_R16_UINT ? 2u :
        indexFormat == DXGI_FORMAT_R32_UINT ? 4u : 0u;
    if (!expectedContext || !expectedDevice ||
        vertexStride == 0 || indexElementBytes == 0 ||
        (indexOffset % indexElementBytes) != 0 ||
        vertexBufferSnapshotToken == 0 || indexBufferSnapshotToken == 0 ||
        !validate_primitive_topology_binding_snapshot(
            expectedContext, expectedDevice, identity, cacheSnapshotToken,
            slotSnapshotToken, objectSnapshotToken, layout,
            inputLayoutSnapshotToken, constantStateSnapshotToken,
            constantPayloadSnapshotToken, constantBindingSnapshotToken,
            pipelineBindingSnapshotToken, primitiveType,
            topologyBindingSnapshotToken))
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    Microsoft::WRL::ComPtr<ID3D11DeviceContext> immediateContext;
    expectedContext->GetDevice(contextDevice.GetAddressOf());
    expectedDevice->GetImmediateContext(immediateContext.GetAddressOf());
    if (contextDevice.Get() != expectedDevice ||
        immediateContext.Get() != expectedContext ||
        vertexBuffer.mirror_device() != expectedDevice ||
        indexBuffer.mirror_device() != expectedDevice)
        return false;

    const auto currentVertex = vertexBuffer.mirror_readiness(expectedDevice);
    const auto currentIndex = indexBuffer.mirror_readiness(expectedDevice);
    if (!currentVertex.ready ||
        currentVertex.role != ResourceRole::Vertex ||
        currentVertex.snapshotToken != vertexBufferSnapshotToken ||
        !currentIndex.ready ||
        currentIndex.role != ResourceRole::Index ||
        currentIndex.snapshotToken != indexBufferSnapshotToken)
        return false;

    const auto found = entries_.find(identity.cacheKey);
    if (found == entries_.end())
        return false;
    auto& entry = found->second;
    if (!entry.topologyBindingContext ||
        entry.topologyBindingContext.Get() != expectedContext ||
        entry.topologyBindingReceiptGeneration == 0)
        return false;

    const bool bindingStarted =
        entry.indexedGeometryBindingContext ||
        entry.indexedGeometryVertexBuffer ||
        entry.indexedGeometryIndexBuffer ||
        entry.indexedGeometryBindingReceiptGeneration != 0;
    if (bindingStarted) {
        return indexed_geometry_binding_readiness(
            expectedContext, expectedDevice, identity, cacheSnapshotToken,
            slotSnapshotToken, objectSnapshotToken, layout,
            inputLayoutSnapshotToken, constantStateSnapshotToken,
            constantPayloadSnapshotToken, constantBindingSnapshotToken,
            pipelineBindingSnapshotToken, primitiveType,
            topologyBindingSnapshotToken, vertexBuffer,
            vertexBufferSnapshotToken, vertexStride, vertexOffset,
            indexBuffer, indexBufferSnapshotToken, indexFormat,
            indexOffset).bindingReady;
    }

    ID3D11Buffer* vertex = vertexBuffer.mirror_buffer();
    expectedContext->IASetVertexBuffers(
        0, 1, &vertex, &vertexStride, &vertexOffset);
    expectedContext->IASetIndexBuffer(
        indexBuffer.mirror_buffer(), indexFormat, indexOffset);

    Microsoft::WRL::ComPtr<ID3D11Buffer> observedVertex;
    UINT observedStride = 0;
    UINT observedVertexOffset = 0;
    expectedContext->IAGetVertexBuffers(
        0, 1, observedVertex.ReleaseAndGetAddressOf(),
        &observedStride, &observedVertexOffset);
    Microsoft::WRL::ComPtr<ID3D11Buffer> observedIndex;
    DXGI_FORMAT observedIndexFormat = DXGI_FORMAT_UNKNOWN;
    UINT observedIndexOffset = 0;
    expectedContext->IAGetIndexBuffer(
        observedIndex.ReleaseAndGetAddressOf(),
        &observedIndexFormat, &observedIndexOffset);
    D3D11_PRIMITIVE_TOPOLOGY observedTopology =
        D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    expectedContext->IAGetPrimitiveTopology(&observedTopology);
    const auto translatedTopology = translate_primitive(primitiveType);
    if (observedVertex.Get() != vertexBuffer.mirror_buffer() ||
        observedStride != vertexStride ||
        observedVertexOffset != vertexOffset ||
        observedIndex.Get() != indexBuffer.mirror_buffer() ||
        observedIndexFormat != indexFormat ||
        observedIndexOffset != indexOffset ||
        !translatedTopology.exact ||
        observedTopology != translatedTopology.value)
        return false;

    entry.indexedGeometryBindingContext = expectedContext;
    entry.indexedGeometryVertexBuffer = vertexBuffer.mirror_buffer();
    entry.indexedGeometryIndexBuffer = indexBuffer.mirror_buffer();
    entry.indexedGeometryVertexBufferSnapshotToken = vertexBufferSnapshotToken;
    entry.indexedGeometryIndexBufferSnapshotToken = indexBufferSnapshotToken;
    entry.indexedGeometryVertexStride = vertexStride;
    entry.indexedGeometryVertexOffset = vertexOffset;
    entry.indexedGeometryIndexFormat = indexFormat;
    entry.indexedGeometryIndexOffset = indexOffset;
    ++indexed_geometry_binding_receipt_generation_counter_;
    if (indexed_geometry_binding_receipt_generation_counter_ == 0)
        ++indexed_geometry_binding_receipt_generation_counter_;
    entry.indexedGeometryBindingReceiptGeneration =
        indexed_geometry_binding_receipt_generation_counter_;
    return true;
}

NativeProgrammableShaderIndexedGeometryBindingReadiness
NativeProgrammableShaderPairCache::indexed_geometry_binding_readiness(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken,
    std::uint64_t constantBindingSnapshotToken,
    std::uint64_t pipelineBindingSnapshotToken,
    D3DPRIMITIVETYPE primitiveType,
    std::uint64_t topologyBindingSnapshotToken,
    const NativeManagedBufferShadow& vertexBuffer,
    std::uint64_t vertexBufferSnapshotToken,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeManagedBufferShadow& indexBuffer,
    std::uint64_t indexBufferSnapshotToken,
    DXGI_FORMAT indexFormat,
    UINT indexOffset) const noexcept {
    NativeProgrammableShaderIndexedGeometryBindingReadiness out{};
    out.cacheKey = identity.cacheKey;
    out.inputLayoutIdentity = hash_pipeline_input_layout_identity(layout);
    out.vertexStride = vertexStride;
    out.vertexOffset = vertexOffset;
    out.indexFormat = indexFormat;
    out.indexOffset = indexOffset;
    out.cacheSnapshotToken = cacheSnapshotToken;
    out.slotSnapshotToken = slotSnapshotToken;
    out.objectSnapshotToken = objectSnapshotToken;
    out.inputLayoutSnapshotToken = inputLayoutSnapshotToken;
    out.constantStateSnapshotToken = constantStateSnapshotToken;
    out.constantPayloadSnapshotToken = constantPayloadSnapshotToken;
    out.constantBindingSnapshotToken = constantBindingSnapshotToken;
    out.pipelineBindingSnapshotToken = pipelineBindingSnapshotToken;
    out.topologyBindingSnapshotToken = topologyBindingSnapshotToken;
    out.vertexBufferSnapshotToken = vertexBufferSnapshotToken;
    out.indexBufferSnapshotToken = indexBufferSnapshotToken;

    const UINT indexElementBytes =
        indexFormat == DXGI_FORMAT_R16_UINT ? 2u :
        indexFormat == DXGI_FORMAT_R32_UINT ? 4u : 0u;
    out.inputValid =
        expectedContext != nullptr && expectedDevice != nullptr &&
        topologyBindingSnapshotToken != 0 &&
        vertexBufferSnapshotToken != 0 &&
        indexBufferSnapshotToken != 0 &&
        vertexStride != 0 &&
        indexElementBytes != 0 &&
        (indexOffset % indexElementBytes) == 0 &&
        out.inputLayoutIdentity != 0 &&
        identity.exact_identity() && !identity.translationImplemented;

    const auto topology = primitive_topology_binding_readiness(
        expectedContext, expectedDevice, identity, cacheSnapshotToken,
        slotSnapshotToken, objectSnapshotToken, layout,
        inputLayoutSnapshotToken, constantStateSnapshotToken,
        constantPayloadSnapshotToken, constantBindingSnapshotToken,
        pipelineBindingSnapshotToken, primitiveType);
    out.topologyBindingReceiptReady = topology.bindingReady;
    out.topologyBindingSnapshotMatches =
        topology.bindingReady &&
        topology.snapshotToken == topologyBindingSnapshotToken;
    out.ownerGeneration = topology.ownerGeneration;
    out.slotGeneration = topology.slotGeneration;
    out.translationObjectReceiptGeneration =
        topology.translationObjectReceiptGeneration;
    out.inputLayoutReceiptGeneration =
        topology.inputLayoutReceiptGeneration;
    out.constantStateReceiptGeneration =
        topology.constantStateReceiptGeneration;
    out.constantPayloadReceiptGeneration =
        topology.constantPayloadReceiptGeneration;
    out.constantBindingReceiptGeneration =
        topology.constantBindingReceiptGeneration;
    out.pipelineBindingReceiptGeneration =
        topology.pipelineBindingReceiptGeneration;
    out.topologyBindingReceiptGeneration =
        topology.topologyBindingReceiptGeneration;
    out.translatedTopology = topology.translatedTopology;
    out.contextDeviceMatches = topology.contextDeviceMatches;

    const auto currentVertex = vertexBuffer.mirror_readiness(expectedDevice);
    const auto currentIndex = indexBuffer.mirror_readiness(expectedDevice);
    out.vertexBufferCurrent =
        currentVertex.ready &&
        currentVertex.role == ResourceRole::Vertex &&
        currentVertex.snapshotToken == vertexBufferSnapshotToken;
    out.indexBufferCurrent =
        currentIndex.ready &&
        currentIndex.role == ResourceRole::Index &&
        currentIndex.snapshotToken == indexBufferSnapshotToken;
    out.deviceMatches =
        topology.deviceMatches &&
        vertexBuffer.mirror_device() == expectedDevice &&
        indexBuffer.mirror_device() == expectedDevice;

    if (out.inputValid && out.topologyBindingReceiptReady &&
        out.topologyBindingSnapshotMatches && out.deviceMatches &&
        out.contextDeviceMatches && out.vertexBufferCurrent &&
        out.indexBufferCurrent) {
        const auto found = entries_.find(identity.cacheKey);
        if (found != entries_.end()) {
            const auto& entry = found->second;
            out.indexedGeometryBindingReceiptGeneration =
                entry.indexedGeometryBindingReceiptGeneration;
            out.geometryReceiptPresent =
                entry.indexedGeometryBindingContext &&
                entry.indexedGeometryBindingContext.Get() == expectedContext &&
                out.indexedGeometryBindingReceiptGeneration != 0;

            Microsoft::WRL::ComPtr<ID3D11Buffer> observedVertex;
            UINT observedStride = 0;
            UINT observedVertexOffset = 0;
            expectedContext->IAGetVertexBuffers(
                0, 1, observedVertex.ReleaseAndGetAddressOf(),
                &observedStride, &observedVertexOffset);
            Microsoft::WRL::ComPtr<ID3D11Buffer> observedIndex;
            DXGI_FORMAT observedIndexFormat = DXGI_FORMAT_UNKNOWN;
            UINT observedIndexOffset = 0;
            expectedContext->IAGetIndexBuffer(
                observedIndex.ReleaseAndGetAddressOf(),
                &observedIndexFormat, &observedIndexOffset);

            out.vertexBufferMatches =
                entry.indexedGeometryVertexBuffer.Get() ==
                    vertexBuffer.mirror_buffer() &&
                entry.indexedGeometryVertexBufferSnapshotToken ==
                    vertexBufferSnapshotToken &&
                entry.indexedGeometryVertexStride == vertexStride &&
                entry.indexedGeometryVertexOffset == vertexOffset &&
                observedVertex.Get() == vertexBuffer.mirror_buffer() &&
                observedStride == vertexStride &&
                observedVertexOffset == vertexOffset;
            out.indexBufferMatches =
                entry.indexedGeometryIndexBuffer.Get() ==
                    indexBuffer.mirror_buffer() &&
                entry.indexedGeometryIndexBufferSnapshotToken ==
                    indexBufferSnapshotToken &&
                entry.indexedGeometryIndexFormat == indexFormat &&
                entry.indexedGeometryIndexOffset == indexOffset &&
                observedIndex.Get() == indexBuffer.mirror_buffer() &&
                observedIndexFormat == indexFormat &&
                observedIndexOffset == indexOffset;
        }
    }

    out.bindingReady =
        out.inputValid && out.topologyBindingReceiptReady &&
        out.topologyBindingSnapshotMatches &&
        out.deviceMatches && out.contextDeviceMatches &&
        out.vertexBufferCurrent && out.indexBufferCurrent &&
        out.geometryReceiptPresent &&
        out.vertexBufferMatches && out.indexBufferMatches &&
        out.ownerGeneration != 0 && out.slotGeneration != 0 &&
        out.translationObjectReceiptGeneration != 0 &&
        out.inputLayoutReceiptGeneration != 0 &&
        out.constantStateReceiptGeneration != 0 &&
        out.constantPayloadReceiptGeneration != 0 &&
        out.constantBindingReceiptGeneration != 0 &&
        out.pipelineBindingReceiptGeneration != 0 &&
        out.topologyBindingReceiptGeneration != 0 &&
        out.indexedGeometryBindingReceiptGeneration != 0 &&
        out.cacheKey != 0 && out.inputLayoutIdentity != 0;

    if (out.bindingReady) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(this)));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(expectedContext)));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(expectedDevice)));
        token = mix_readiness_snapshot_token(token, out.ownerGeneration);
        token = mix_readiness_snapshot_token(token, out.slotGeneration);
        token = mix_readiness_snapshot_token(
            token, out.translationObjectReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.inputLayoutReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.constantStateReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.constantPayloadReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.constantBindingReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.pipelineBindingReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.topologyBindingReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.indexedGeometryBindingReceiptGeneration);
        token = mix_readiness_snapshot_token(token, out.cacheKey);
        token = mix_readiness_snapshot_token(token, out.inputLayoutIdentity);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.translatedTopology));
        token = mix_readiness_snapshot_token(token, out.cacheSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.slotSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.objectSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.inputLayoutSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.constantStateSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.constantPayloadSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.constantBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.pipelineBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.topologyBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.vertexBufferSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.indexBufferSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.vertexStride);
        token = mix_readiness_snapshot_token(token, out.vertexOffset);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.indexFormat));
        token = mix_readiness_snapshot_token(token, out.indexOffset);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeProgrammableShaderPairCache::validate_indexed_geometry_binding_snapshot(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken,
    std::uint64_t constantBindingSnapshotToken,
    std::uint64_t pipelineBindingSnapshotToken,
    D3DPRIMITIVETYPE primitiveType,
    std::uint64_t topologyBindingSnapshotToken,
    const NativeManagedBufferShadow& vertexBuffer,
    std::uint64_t vertexBufferSnapshotToken,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeManagedBufferShadow& indexBuffer,
    std::uint64_t indexBufferSnapshotToken,
    DXGI_FORMAT indexFormat,
    UINT indexOffset,
    std::uint64_t indexedGeometryBindingSnapshotToken) const noexcept {
    if (indexedGeometryBindingSnapshotToken == 0)
        return false;
    const auto current = indexed_geometry_binding_readiness(
        expectedContext, expectedDevice, identity, cacheSnapshotToken,
        slotSnapshotToken, objectSnapshotToken, layout,
        inputLayoutSnapshotToken, constantStateSnapshotToken,
        constantPayloadSnapshotToken, constantBindingSnapshotToken,
        pipelineBindingSnapshotToken, primitiveType,
        topologyBindingSnapshotToken, vertexBuffer,
        vertexBufferSnapshotToken, vertexStride, vertexOffset,
        indexBuffer, indexBufferSnapshotToken, indexFormat, indexOffset);
    return current.bindingReady &&
           current.snapshotToken == indexedGeometryBindingSnapshotToken;
}

bool NativeProgrammableShaderPairCache::bind_nonindexed_geometry_for_observation(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken,
    std::uint64_t constantBindingSnapshotToken,
    std::uint64_t pipelineBindingSnapshotToken,
    D3DPRIMITIVETYPE primitiveType,
    std::uint64_t topologyBindingSnapshotToken,
    const NativeManagedBufferShadow& vertexBuffer,
    std::uint64_t vertexBufferSnapshotToken,
    UINT vertexStride,
    UINT vertexOffset) noexcept {
    if (!expectedContext || !expectedDevice ||
        vertexStride == 0 || vertexBufferSnapshotToken == 0 ||
        !validate_primitive_topology_binding_snapshot(
            expectedContext, expectedDevice, identity, cacheSnapshotToken,
            slotSnapshotToken, objectSnapshotToken, layout,
            inputLayoutSnapshotToken, constantStateSnapshotToken,
            constantPayloadSnapshotToken, constantBindingSnapshotToken,
            pipelineBindingSnapshotToken, primitiveType,
            topologyBindingSnapshotToken))
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    Microsoft::WRL::ComPtr<ID3D11DeviceContext> immediateContext;
    expectedContext->GetDevice(contextDevice.GetAddressOf());
    expectedDevice->GetImmediateContext(immediateContext.GetAddressOf());
    if (contextDevice.Get() != expectedDevice ||
        immediateContext.Get() != expectedContext ||
        vertexBuffer.mirror_device() != expectedDevice)
        return false;

    const auto currentVertex = vertexBuffer.mirror_readiness(expectedDevice);
    if (!currentVertex.ready ||
        currentVertex.role != ResourceRole::Vertex ||
        currentVertex.snapshotToken != vertexBufferSnapshotToken)
        return false;

    const auto found = entries_.find(identity.cacheKey);
    if (found == entries_.end())
        return false;
    auto& entry = found->second;
    if (!entry.topologyBindingContext ||
        entry.topologyBindingContext.Get() != expectedContext ||
        entry.topologyBindingReceiptGeneration == 0)
        return false;

    const bool bindingStarted =
        entry.nonIndexedGeometryBindingContext ||
        entry.nonIndexedGeometryVertexBuffer ||
        entry.nonIndexedGeometryBindingReceiptGeneration != 0;
    if (bindingStarted) {
        return nonindexed_geometry_binding_readiness(
            expectedContext, expectedDevice, identity, cacheSnapshotToken,
            slotSnapshotToken, objectSnapshotToken, layout,
            inputLayoutSnapshotToken, constantStateSnapshotToken,
            constantPayloadSnapshotToken, constantBindingSnapshotToken,
            pipelineBindingSnapshotToken, primitiveType,
            topologyBindingSnapshotToken, vertexBuffer,
            vertexBufferSnapshotToken, vertexStride, vertexOffset).bindingReady;
    }

    ID3D11Buffer* vertex = vertexBuffer.mirror_buffer();
    expectedContext->IASetVertexBuffers(
        0, 1, &vertex, &vertexStride, &vertexOffset);
    expectedContext->IASetIndexBuffer(nullptr, DXGI_FORMAT_UNKNOWN, 0);

    Microsoft::WRL::ComPtr<ID3D11Buffer> observedVertex;
    UINT observedStride = 0;
    UINT observedVertexOffset = 0;
    expectedContext->IAGetVertexBuffers(
        0, 1, observedVertex.ReleaseAndGetAddressOf(),
        &observedStride, &observedVertexOffset);
    Microsoft::WRL::ComPtr<ID3D11Buffer> observedIndex;
    DXGI_FORMAT observedIndexFormat = DXGI_FORMAT_UNKNOWN;
    UINT observedIndexOffset = 0;
    expectedContext->IAGetIndexBuffer(
        observedIndex.ReleaseAndGetAddressOf(),
        &observedIndexFormat, &observedIndexOffset);
    D3D11_PRIMITIVE_TOPOLOGY observedTopology =
        D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    expectedContext->IAGetPrimitiveTopology(&observedTopology);
    const auto translatedTopology = translate_primitive(primitiveType);
    if (observedVertex.Get() != vertexBuffer.mirror_buffer() ||
        observedStride != vertexStride ||
        observedVertexOffset != vertexOffset ||
        observedIndex.Get() != nullptr ||
        observedIndexFormat != DXGI_FORMAT_UNKNOWN ||
        observedIndexOffset != 0 ||
        !translatedTopology.exact ||
        observedTopology != translatedTopology.value)
        return false;

    entry.nonIndexedGeometryBindingContext = expectedContext;
    entry.nonIndexedGeometryVertexBuffer = vertexBuffer.mirror_buffer();
    entry.nonIndexedGeometryVertexBufferSnapshotToken = vertexBufferSnapshotToken;
    entry.nonIndexedGeometryVertexStride = vertexStride;
    entry.nonIndexedGeometryVertexOffset = vertexOffset;
    ++nonindexed_geometry_binding_receipt_generation_counter_;
    if (nonindexed_geometry_binding_receipt_generation_counter_ == 0)
        ++nonindexed_geometry_binding_receipt_generation_counter_;
    entry.nonIndexedGeometryBindingReceiptGeneration =
        nonindexed_geometry_binding_receipt_generation_counter_;
    return true;
}

NativeProgrammableShaderNonIndexedGeometryBindingReadiness
NativeProgrammableShaderPairCache::nonindexed_geometry_binding_readiness(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken,
    std::uint64_t constantBindingSnapshotToken,
    std::uint64_t pipelineBindingSnapshotToken,
    D3DPRIMITIVETYPE primitiveType,
    std::uint64_t topologyBindingSnapshotToken,
    const NativeManagedBufferShadow& vertexBuffer,
    std::uint64_t vertexBufferSnapshotToken,
    UINT vertexStride,
    UINT vertexOffset) const noexcept {
    NativeProgrammableShaderNonIndexedGeometryBindingReadiness out{};
    out.cacheKey = identity.cacheKey;
    out.inputLayoutIdentity = hash_pipeline_input_layout_identity(layout);
    out.vertexStride = vertexStride;
    out.vertexOffset = vertexOffset;
    out.cacheSnapshotToken = cacheSnapshotToken;
    out.slotSnapshotToken = slotSnapshotToken;
    out.objectSnapshotToken = objectSnapshotToken;
    out.inputLayoutSnapshotToken = inputLayoutSnapshotToken;
    out.constantStateSnapshotToken = constantStateSnapshotToken;
    out.constantPayloadSnapshotToken = constantPayloadSnapshotToken;
    out.constantBindingSnapshotToken = constantBindingSnapshotToken;
    out.pipelineBindingSnapshotToken = pipelineBindingSnapshotToken;
    out.topologyBindingSnapshotToken = topologyBindingSnapshotToken;
    out.vertexBufferSnapshotToken = vertexBufferSnapshotToken;
    out.inputValid =
        expectedContext != nullptr && expectedDevice != nullptr &&
        topologyBindingSnapshotToken != 0 &&
        vertexBufferSnapshotToken != 0 &&
        vertexStride != 0 &&
        out.inputLayoutIdentity != 0 &&
        identity.exact_identity() && !identity.translationImplemented;

    const auto topology = primitive_topology_binding_readiness(
        expectedContext, expectedDevice, identity, cacheSnapshotToken,
        slotSnapshotToken, objectSnapshotToken, layout,
        inputLayoutSnapshotToken, constantStateSnapshotToken,
        constantPayloadSnapshotToken, constantBindingSnapshotToken,
        pipelineBindingSnapshotToken, primitiveType);
    out.topologyBindingReceiptReady = topology.bindingReady;
    out.topologyBindingSnapshotMatches =
        topology.bindingReady &&
        topology.snapshotToken == topologyBindingSnapshotToken;
    out.ownerGeneration = topology.ownerGeneration;
    out.slotGeneration = topology.slotGeneration;
    out.translationObjectReceiptGeneration =
        topology.translationObjectReceiptGeneration;
    out.inputLayoutReceiptGeneration =
        topology.inputLayoutReceiptGeneration;
    out.constantStateReceiptGeneration =
        topology.constantStateReceiptGeneration;
    out.constantPayloadReceiptGeneration =
        topology.constantPayloadReceiptGeneration;
    out.constantBindingReceiptGeneration =
        topology.constantBindingReceiptGeneration;
    out.pipelineBindingReceiptGeneration =
        topology.pipelineBindingReceiptGeneration;
    out.topologyBindingReceiptGeneration =
        topology.topologyBindingReceiptGeneration;
    out.translatedTopology = topology.translatedTopology;
    out.contextDeviceMatches = topology.contextDeviceMatches;

    const auto currentVertex = vertexBuffer.mirror_readiness(expectedDevice);
    out.vertexBufferCurrent =
        currentVertex.ready &&
        currentVertex.role == ResourceRole::Vertex &&
        currentVertex.snapshotToken == vertexBufferSnapshotToken;
    out.deviceMatches =
        topology.deviceMatches &&
        vertexBuffer.mirror_device() == expectedDevice;

    if (out.inputValid && out.topologyBindingReceiptReady &&
        out.topologyBindingSnapshotMatches && out.deviceMatches &&
        out.contextDeviceMatches && out.vertexBufferCurrent) {
        const auto found = entries_.find(identity.cacheKey);
        if (found != entries_.end()) {
            const auto& entry = found->second;
            out.nonIndexedGeometryBindingReceiptGeneration =
                entry.nonIndexedGeometryBindingReceiptGeneration;
            out.geometryReceiptPresent =
                entry.nonIndexedGeometryBindingContext &&
                entry.nonIndexedGeometryBindingContext.Get() == expectedContext &&
                out.nonIndexedGeometryBindingReceiptGeneration != 0;

            Microsoft::WRL::ComPtr<ID3D11Buffer> observedVertex;
            UINT observedStride = 0;
            UINT observedVertexOffset = 0;
            expectedContext->IAGetVertexBuffers(
                0, 1, observedVertex.ReleaseAndGetAddressOf(),
                &observedStride, &observedVertexOffset);
            Microsoft::WRL::ComPtr<ID3D11Buffer> observedIndex;
            DXGI_FORMAT observedIndexFormat = DXGI_FORMAT_UNKNOWN;
            UINT observedIndexOffset = 0;
            expectedContext->IAGetIndexBuffer(
                observedIndex.ReleaseAndGetAddressOf(),
                &observedIndexFormat, &observedIndexOffset);

            out.vertexBufferMatches =
                entry.nonIndexedGeometryVertexBuffer.Get() ==
                    vertexBuffer.mirror_buffer() &&
                entry.nonIndexedGeometryVertexBufferSnapshotToken ==
                    vertexBufferSnapshotToken &&
                entry.nonIndexedGeometryVertexStride == vertexStride &&
                entry.nonIndexedGeometryVertexOffset == vertexOffset &&
                observedVertex.Get() == vertexBuffer.mirror_buffer() &&
                observedStride == vertexStride &&
                observedVertexOffset == vertexOffset;
            out.indexBufferClear =
                observedIndex.Get() == nullptr &&
                observedIndexFormat == DXGI_FORMAT_UNKNOWN &&
                observedIndexOffset == 0;
        }
    }

    out.bindingReady =
        out.inputValid && out.topologyBindingReceiptReady &&
        out.topologyBindingSnapshotMatches &&
        out.deviceMatches && out.contextDeviceMatches &&
        out.vertexBufferCurrent && out.geometryReceiptPresent &&
        out.vertexBufferMatches && out.indexBufferClear &&
        out.ownerGeneration != 0 && out.slotGeneration != 0 &&
        out.translationObjectReceiptGeneration != 0 &&
        out.inputLayoutReceiptGeneration != 0 &&
        out.constantStateReceiptGeneration != 0 &&
        out.constantPayloadReceiptGeneration != 0 &&
        out.constantBindingReceiptGeneration != 0 &&
        out.pipelineBindingReceiptGeneration != 0 &&
        out.topologyBindingReceiptGeneration != 0 &&
        out.nonIndexedGeometryBindingReceiptGeneration != 0 &&
        out.cacheKey != 0 && out.inputLayoutIdentity != 0;

    if (out.bindingReady) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(this)));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(expectedContext)));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(expectedDevice)));
        token = mix_readiness_snapshot_token(token, out.ownerGeneration);
        token = mix_readiness_snapshot_token(token, out.slotGeneration);
        token = mix_readiness_snapshot_token(
            token, out.translationObjectReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.inputLayoutReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.constantStateReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.constantPayloadReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.constantBindingReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.pipelineBindingReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.topologyBindingReceiptGeneration);
        token = mix_readiness_snapshot_token(
            token, out.nonIndexedGeometryBindingReceiptGeneration);
        token = mix_readiness_snapshot_token(token, out.cacheKey);
        token = mix_readiness_snapshot_token(token, out.inputLayoutIdentity);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.translatedTopology));
        token = mix_readiness_snapshot_token(token, out.cacheSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.slotSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.objectSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.inputLayoutSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.constantStateSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.constantPayloadSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.constantBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.pipelineBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.topologyBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.vertexBufferSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.vertexStride);
        token = mix_readiness_snapshot_token(token, out.vertexOffset);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeProgrammableShaderPairCache::
validate_nonindexed_geometry_binding_snapshot(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken,
    std::uint64_t constantBindingSnapshotToken,
    std::uint64_t pipelineBindingSnapshotToken,
    D3DPRIMITIVETYPE primitiveType,
    std::uint64_t topologyBindingSnapshotToken,
    const NativeManagedBufferShadow& vertexBuffer,
    std::uint64_t vertexBufferSnapshotToken,
    UINT vertexStride,
    UINT vertexOffset,
    std::uint64_t nonIndexedGeometryBindingSnapshotToken) const noexcept {
    if (nonIndexedGeometryBindingSnapshotToken == 0)
        return false;
    const auto current = nonindexed_geometry_binding_readiness(
        expectedContext, expectedDevice, identity, cacheSnapshotToken,
        slotSnapshotToken, objectSnapshotToken, layout,
        inputLayoutSnapshotToken, constantStateSnapshotToken,
        constantPayloadSnapshotToken, constantBindingSnapshotToken,
        pipelineBindingSnapshotToken, primitiveType,
        topologyBindingSnapshotToken, vertexBuffer,
        vertexBufferSnapshotToken, vertexStride, vertexOffset);
    return current.bindingReady &&
           current.snapshotToken == nonIndexedGeometryBindingSnapshotToken;
}

void NativeProgrammableShaderPairCache::shutdown() noexcept {
    entries_.clear();
    device_.Reset();
}

bool NativeProgrammableShaderBackendOwnership::initialize(
    ID3D11Device* device) noexcept {
    shutdown();
    if (!device || !cache_.initialize(device))
        return false;
    device_ = device;
    ++owner_generation_;
    if (owner_generation_ == 0)
        ++owner_generation_;
    return true;
}

void NativeProgrammableShaderBackendOwnership::shutdown() noexcept {
    semantic_input_layouts_.clear();
    materializations_.clear();
    cache_.shutdown();
    device_.Reset();
}

NativeProgrammableShaderBackendSemanticHandoffEvidence
NativeProgrammableShaderBackendOwnership::
materialize_semantic_handoff_for_observation(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderTranslationObjectPrerequisiteEvidence&
        objectPrerequisite,
    std::uint64_t objectPrerequisiteSnapshotToken,
    const NativeProgrammableShaderObjectCreationHandoffEvidence& creationHandoff,
    std::uint64_t creationHandoffSnapshotToken,
    const NativeProgrammableShaderTargetBytecodeMaterializationEvidence&
        targetBytecodeMaterialization,
    std::uint64_t targetBytecodeMaterializationSnapshotToken,
    const NativeProgrammableShaderSourceMappingHandoff& sourceMappingHandoff,
    std::uint64_t sourceMappingHandoffSnapshotToken,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence&
        translationPlan,
    std::uint64_t translationPlanSnapshotToken) noexcept {
    NativeProgrammableShaderBackendSemanticHandoffEvidence out{};
    out.diagnosticOnly = true;
    out.objectBindingAuthorized = false;
    out.nativeDrawPathActivationAllowed = false;
    out.drawDispatchAuthorized = false;
    out.cacheKey = sourceIdentity.cacheKey;
    out.backendOwnerGeneration = owner_generation_;
    out.inputValid =
        sourceIdentity.exact_identity() &&
        !sourceIdentity.translationImplemented &&
        objectPrerequisiteSnapshotToken != 0 &&
        creationHandoffSnapshotToken != 0 &&
        targetBytecodeMaterializationSnapshotToken != 0 &&
        sourceMappingHandoffSnapshotToken != 0 &&
        translationPlanSnapshotToken != 0;
    out.ownerReady = ready();
    out.deviceMatches =
        out.ownerReady &&
        device_.Get() != nullptr &&
        cache_.device() == device_.Get();
    if (!out.inputValid || !out.ownerReady || !out.deviceMatches)
        return out;

    const NativeProgrammableShaderObjectMaterializationEvidence*
        materialization = nullptr;
    const auto existing = materializations_.find(sourceIdentity.cacheKey);
    if (existing != materializations_.end()) {
        if (!validate_programmable_shader_object_materialization_snapshot(
                device_.Get(),
                cache_,
                sourceIdentity,
                objectPrerequisite,
                objectPrerequisiteSnapshotToken,
                creationHandoff,
                creationHandoffSnapshotToken,
                targetBytecodeMaterialization,
                targetBytecodeMaterializationSnapshotToken,
                existing->second,
                existing->second.reviewSnapshotToken))
            return out;
        materialization = &existing->second;
        out.materializationReused = true;
    } else {
        const auto created =
            materialize_programmable_shader_translation_objects(
                device_.Get(),
                cache_,
                sourceIdentity,
                objectPrerequisite,
                objectPrerequisiteSnapshotToken,
                creationHandoff,
                creationHandoffSnapshotToken,
                targetBytecodeMaterialization,
                targetBytecodeMaterializationSnapshotToken);
        if (!created.reviewReady ||
            !validate_programmable_shader_object_materialization_snapshot(
                device_.Get(),
                cache_,
                sourceIdentity,
                objectPrerequisite,
                objectPrerequisiteSnapshotToken,
                creationHandoff,
                creationHandoffSnapshotToken,
                targetBytecodeMaterialization,
                targetBytecodeMaterializationSnapshotToken,
                created,
                created.reviewSnapshotToken))
            return out;
        try {
            const auto inserted =
                materializations_.emplace(sourceIdentity.cacheKey, created);
            if (!inserted.second)
                return out;
            materialization = &inserted.first->second;
        } catch (...) {
            return out;
        }
    }

    if (!materialization)
        return out;

    out.materializationReady =
        materialization->reviewReady &&
        materialization->translationObjectReceiptReady &&
        !materialization->objectBindingAuthorized;
    out.materializationSnapshotMatches =
        out.materializationReady &&
        materialization->reviewSnapshotToken != 0 &&
        validate_programmable_shader_object_materialization_snapshot(
            device_.Get(),
            cache_,
            sourceIdentity,
            objectPrerequisite,
            objectPrerequisiteSnapshotToken,
            creationHandoff,
            creationHandoffSnapshotToken,
            targetBytecodeMaterialization,
            targetBytecodeMaterializationSnapshotToken,
            *materialization,
            materialization->reviewSnapshotToken);
    out.objectMaterializationSnapshotToken =
        materialization->reviewSnapshotToken;
    out.cacheSnapshotToken = materialization->cacheSnapshotToken;
    out.slotSnapshotToken = materialization->slotSnapshotToken;
    out.cacheOwnerGeneration = materialization->ownerGeneration;
    if (!out.materializationSnapshotMatches)
        return out;

    const auto translationObject =
        cache_.translation_object_readiness(
            device_.Get(),
            sourceIdentity,
            out.cacheSnapshotToken,
            out.slotSnapshotToken);
    out.translationObjectReady =
        translationObject.attachmentReady &&
        translationObject.objectsAttached &&
        translationObject.objectDevicesMatch &&
        translationObject.cacheKey == sourceIdentity.cacheKey;
    out.translationObjectSnapshotToken = translationObject.snapshotToken;
    out.translationObjectSnapshotMatches =
        out.translationObjectReady &&
        out.translationObjectSnapshotToken != 0 &&
        out.translationObjectSnapshotToken ==
            materialization->translationObjectSnapshotToken &&
        cache_.validate_translation_object_snapshot(
            device_.Get(),
            sourceIdentity,
            out.cacheSnapshotToken,
            out.slotSnapshotToken,
            out.translationObjectSnapshotToken);
    if (!out.translationObjectSnapshotMatches)
        return out;

    out.translatedSemanticReceipt =
        compose_programmable_shader_translated_semantic_receipt(
            sourceIdentity,
            translationObject,
            out.translationObjectSnapshotToken,
            sourceMappingHandoff,
            sourceMappingHandoffSnapshotToken,
            translationPlan,
            translationPlanSnapshotToken);
    out.translatedSemanticReceiptSnapshotToken =
        out.translatedSemanticReceipt.reviewSnapshotToken;
    out.translatedSemanticReceiptReady =
        out.translatedSemanticReceipt.reviewReady &&
        validate_programmable_shader_translated_semantic_receipt_snapshot(
            out.translatedSemanticReceipt,
            out.translatedSemanticReceiptSnapshotToken);
    out.translatedSemanticReceiptSnapshotMatches =
        out.translatedSemanticReceiptReady &&
        out.translatedSemanticReceipt.translationObjectSnapshotToken ==
            out.translationObjectSnapshotToken &&
        out.translatedSemanticReceipt.sourceMappingHandoffSnapshotToken ==
            sourceMappingHandoffSnapshotToken &&
        out.translatedSemanticReceipt.translationPlanSnapshotToken ==
            translationPlanSnapshotToken &&
        out.translatedSemanticReceipt.cacheKey == sourceIdentity.cacheKey;

    out.boundaryPreserved =
        out.materializationSnapshotMatches &&
        out.translationObjectSnapshotMatches &&
        out.translatedSemanticReceiptSnapshotMatches &&
        !out.objectBindingAuthorized &&
        !out.nativeDrawPathActivationAllowed &&
        !out.drawDispatchAuthorized &&
        out.diagnosticOnly;
    out.reviewReady =
        out.inputValid &&
        out.ownerReady &&
        out.deviceMatches &&
        out.boundaryPreserved;
    if (out.reviewReady)
        out.reviewSnapshotToken =
            r285_backend_semantic_handoff_snapshot_token(out);
    return out;
}

bool NativeProgrammableShaderBackendOwnership::
validate_semantic_handoff_snapshot(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderTranslationObjectPrerequisiteEvidence&
        objectPrerequisite,
    std::uint64_t objectPrerequisiteSnapshotToken,
    const NativeProgrammableShaderObjectCreationHandoffEvidence& creationHandoff,
    std::uint64_t creationHandoffSnapshotToken,
    const NativeProgrammableShaderTargetBytecodeMaterializationEvidence&
        targetBytecodeMaterialization,
    std::uint64_t targetBytecodeMaterializationSnapshotToken,
    const NativeProgrammableShaderSourceMappingHandoff& sourceMappingHandoff,
    std::uint64_t sourceMappingHandoffSnapshotToken,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence&
        translationPlan,
    std::uint64_t translationPlanSnapshotToken,
    const NativeProgrammableShaderBackendSemanticHandoffEvidence& handoff,
    std::uint64_t reviewSnapshotToken) const noexcept {
    if (reviewSnapshotToken == 0 ||
        !handoff.reviewReady ||
        !handoff.boundaryPreserved ||
        !handoff.diagnosticOnly ||
        handoff.objectBindingAuthorized ||
        handoff.nativeDrawPathActivationAllowed ||
        handoff.drawDispatchAuthorized ||
        handoff.reviewSnapshotToken != reviewSnapshotToken ||
        !ready() ||
        handoff.backendOwnerGeneration != owner_generation_ ||
        handoff.cacheKey != sourceIdentity.cacheKey)
        return false;

    const auto found = materializations_.find(sourceIdentity.cacheKey);
    if (found == materializations_.end())
        return false;
    const auto& materialization = found->second;
    if (materialization.reviewSnapshotToken !=
            handoff.objectMaterializationSnapshotToken ||
        materialization.cacheSnapshotToken != handoff.cacheSnapshotToken ||
        materialization.slotSnapshotToken != handoff.slotSnapshotToken ||
        materialization.ownerGeneration != handoff.cacheOwnerGeneration ||
        !validate_programmable_shader_object_materialization_snapshot(
            device_.Get(),
            cache_,
            sourceIdentity,
            objectPrerequisite,
            objectPrerequisiteSnapshotToken,
            creationHandoff,
            creationHandoffSnapshotToken,
            targetBytecodeMaterialization,
            targetBytecodeMaterializationSnapshotToken,
            materialization,
            handoff.objectMaterializationSnapshotToken))
        return false;

    const auto translationObject =
        cache_.translation_object_readiness(
            device_.Get(),
            sourceIdentity,
            handoff.cacheSnapshotToken,
            handoff.slotSnapshotToken);
    if (!translationObject.attachmentReady ||
        !translationObject.objectsAttached ||
        !translationObject.objectDevicesMatch ||
        translationObject.snapshotToken !=
            handoff.translationObjectSnapshotToken ||
        !cache_.validate_translation_object_snapshot(
            device_.Get(),
            sourceIdentity,
            handoff.cacheSnapshotToken,
            handoff.slotSnapshotToken,
            handoff.translationObjectSnapshotToken))
        return false;

    const auto currentReceipt =
        compose_programmable_shader_translated_semantic_receipt(
            sourceIdentity,
            translationObject,
            handoff.translationObjectSnapshotToken,
            sourceMappingHandoff,
            sourceMappingHandoffSnapshotToken,
            translationPlan,
            translationPlanSnapshotToken);
    if (!currentReceipt.reviewReady ||
        !validate_programmable_shader_translated_semantic_receipt_snapshot(
            currentReceipt,
            currentReceipt.reviewSnapshotToken) ||
        currentReceipt.reviewSnapshotToken !=
            handoff.translatedSemanticReceiptSnapshotToken ||
        currentReceipt.reviewSnapshotToken !=
            handoff.translatedSemanticReceipt.reviewSnapshotToken ||
        currentReceipt.cacheKey != handoff.translatedSemanticReceipt.cacheKey ||
        currentReceipt.translationObjectSnapshotToken !=
            handoff.translatedSemanticReceipt.translationObjectSnapshotToken ||
        currentReceipt.sourceMappingHandoffSnapshotToken !=
            handoff.translatedSemanticReceipt.sourceMappingHandoffSnapshotToken ||
        currentReceipt.translationPlanSnapshotToken !=
            handoff.translatedSemanticReceipt.translationPlanSnapshotToken ||
        !validate_programmable_shader_translated_semantic_receipt_snapshot(
            handoff.translatedSemanticReceipt,
            handoff.translatedSemanticReceiptSnapshotToken))
        return false;

    return r285_backend_semantic_handoff_snapshot_token(handoff) ==
        reviewSnapshotToken;
}


NativeProgrammableShaderProductionObservationEvidence
observe_programmable_shader_production_source_evidence_chain(
    NativeProgrammableShaderBackendOwnership& ownership,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderTranslationObjectPrerequisiteEvidence&
        objectPrerequisite,
    std::uint64_t objectPrerequisiteSnapshotToken,
    const NativeProgrammableShaderObjectCreationHandoffEvidence& creationHandoff,
    std::uint64_t creationHandoffSnapshotToken,
    const NativeProgrammableShaderTargetBytecodeMaterializationEvidence&
        targetBytecodeMaterialization,
    std::uint64_t targetBytecodeMaterializationSnapshotToken,
    const NativeProgrammableShaderSourceMappingHandoff& sourceMappingHandoff,
    std::uint64_t sourceMappingHandoffSnapshotToken,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence&
        translationPlan,
    std::uint64_t translationPlanSnapshotToken) noexcept {
    NativeProgrammableShaderProductionObservationEvidence out{};
    out.diagnosticOnly = true;
    out.objectBindingAuthorized = false;
    out.nativeDrawPathActivationAllowed = false;
    out.drawDispatchAuthorized = false;
    out.cacheKey = sourceIdentity.cacheKey;
    out.backendOwnerGeneration = ownership.owner_generation();
    out.objectPrerequisiteSnapshotToken = objectPrerequisiteSnapshotToken;
    out.creationHandoffSnapshotToken = creationHandoffSnapshotToken;
    out.targetBytecodeMaterializationSnapshotToken =
        targetBytecodeMaterializationSnapshotToken;
    out.sourceMappingHandoffSnapshotToken = sourceMappingHandoffSnapshotToken;
    out.translationPlanSnapshotToken = translationPlanSnapshotToken;

    out.inputValid =
        expectedDevice != nullptr &&
        sourceIdentity.exact_identity() &&
        !sourceIdentity.translationImplemented &&
        objectPrerequisiteSnapshotToken != 0 &&
        creationHandoffSnapshotToken != 0 &&
        targetBytecodeMaterializationSnapshotToken != 0 &&
        sourceMappingHandoffSnapshotToken != 0 &&
        translationPlanSnapshotToken != 0;
    out.ownerReady = ownership.ready();
    out.deviceMatches =
        out.ownerReady && ownership.device() == expectedDevice;
    out.objectPrerequisiteReady =
        objectPrerequisite.reviewReady &&
        objectPrerequisite.boundaryPreserved &&
        objectPrerequisite.diagnosticOnly &&
        objectPrerequisite.reviewSnapshotToken ==
            objectPrerequisiteSnapshotToken;
    out.creationHandoffReady =
        creationHandoff.reviewReady &&
        creationHandoff.boundaryPreserved &&
        creationHandoff.diagnosticOnly &&
        !creationHandoff.objectCreationAuthorized &&
        creationHandoff.reviewSnapshotToken == creationHandoffSnapshotToken;
    out.targetBytecodeMaterializationReady =
        targetBytecodeMaterialization.reviewReady &&
        targetBytecodeMaterialization.boundaryPreserved &&
        targetBytecodeMaterialization.diagnosticOnly &&
        targetBytecodeMaterialization.targetBytecodeMaterialized &&
        !targetBytecodeMaterialization.objectCreationAuthorized &&
        targetBytecodeMaterialization.reviewSnapshotToken ==
            targetBytecodeMaterializationSnapshotToken;
    out.sourceMappingHandoffReady =
        sourceMappingHandoff.reviewReady &&
        sourceMappingHandoff.boundaryPreserved &&
        sourceMappingHandoff.diagnosticOnly &&
        sourceMappingHandoff.reviewSnapshotToken ==
            sourceMappingHandoffSnapshotToken;
    out.translationPlanReady =
        translationPlan.reviewReady &&
        translationPlan.boundaryPreserved &&
        translationPlan.diagnosticOnly &&
        translationPlan.reviewSnapshotToken == translationPlanSnapshotToken;

    if (!out.inputValid ||
        !out.ownerReady ||
        !out.deviceMatches ||
        !out.objectPrerequisiteReady ||
        !out.creationHandoffReady ||
        !out.targetBytecodeMaterializationReady ||
        !out.sourceMappingHandoffReady ||
        !out.translationPlanReady)
        return out;

    out.semanticHandoff =
        ownership.materialize_semantic_handoff_for_observation(
            sourceIdentity,
            objectPrerequisite,
            objectPrerequisiteSnapshotToken,
            creationHandoff,
            creationHandoffSnapshotToken,
            targetBytecodeMaterialization,
            targetBytecodeMaterializationSnapshotToken,
            sourceMappingHandoff,
            sourceMappingHandoffSnapshotToken,
            translationPlan,
            translationPlanSnapshotToken);
    out.semanticHandoffSnapshotToken =
        out.semanticHandoff.reviewSnapshotToken;
    out.semanticHandoffReady =
        out.semanticHandoff.reviewReady &&
        out.semanticHandoff.boundaryPreserved &&
        out.semanticHandoff.diagnosticOnly;
    out.semanticHandoffSnapshotMatches =
        out.semanticHandoffReady &&
        out.semanticHandoffSnapshotToken != 0 &&
        ownership.validate_semantic_handoff_snapshot(
            sourceIdentity,
            objectPrerequisite,
            objectPrerequisiteSnapshotToken,
            creationHandoff,
            creationHandoffSnapshotToken,
            targetBytecodeMaterialization,
            targetBytecodeMaterializationSnapshotToken,
            sourceMappingHandoff,
            sourceMappingHandoffSnapshotToken,
            translationPlan,
            translationPlanSnapshotToken,
            out.semanticHandoff,
            out.semanticHandoffSnapshotToken);
    out.objectBindingAuthorized =
        out.semanticHandoff.objectBindingAuthorized;
    out.nativeDrawPathActivationAllowed =
        out.semanticHandoff.nativeDrawPathActivationAllowed;
    out.drawDispatchAuthorized =
        out.semanticHandoff.drawDispatchAuthorized;
    out.boundaryPreserved =
        out.semanticHandoffSnapshotMatches &&
        !out.objectBindingAuthorized &&
        !out.nativeDrawPathActivationAllowed &&
        !out.drawDispatchAuthorized &&
        out.diagnosticOnly;
    out.reviewReady =
        out.inputValid &&
        out.ownerReady &&
        out.deviceMatches &&
        out.objectPrerequisiteReady &&
        out.creationHandoffReady &&
        out.targetBytecodeMaterializationReady &&
        out.sourceMappingHandoffReady &&
        out.translationPlanReady &&
        out.boundaryPreserved;
    if (out.reviewReady)
        out.reviewSnapshotToken =
            r286_production_observation_snapshot_token(out);
    return out;
}

bool validate_programmable_shader_production_observation_snapshot(
    const NativeProgrammableShaderProductionObservationEvidence& observation,
    std::uint64_t reviewSnapshotToken) noexcept {
    if (!observation.reviewReady ||
        !observation.boundaryPreserved ||
        !observation.diagnosticOnly ||
        observation.objectBindingAuthorized ||
        observation.nativeDrawPathActivationAllowed ||
        observation.drawDispatchAuthorized ||
        reviewSnapshotToken == 0 ||
        observation.reviewSnapshotToken != reviewSnapshotToken ||
        !observation.semanticHandoffReady ||
        !observation.semanticHandoffSnapshotMatches ||
        !observation.semanticHandoff.reviewReady ||
        observation.semanticHandoff.reviewSnapshotToken !=
            observation.semanticHandoffSnapshotToken ||
        !observation.semanticHandoff.translatedSemanticReceiptReady ||
        !observation.semanticHandoff.translatedSemanticReceiptSnapshotMatches)
        return false;

    const auto& receipt =
        observation.semanticHandoff.translatedSemanticReceipt;
    if (!receipt.reviewReady ||
        receipt.reviewSnapshotToken !=
            observation.semanticHandoff.translatedSemanticReceiptSnapshotToken ||
        !validate_programmable_shader_translated_semantic_receipt_snapshot(
            receipt, receipt.reviewSnapshotToken))
        return false;

    return r286_production_observation_snapshot_token(observation) ==
        reviewSnapshotToken;
}

NativeProgrammableShaderTranslationAdmissionEvidence
seal_programmable_shader_translation_admission(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderProductionObservationEvidence& observation,
    std::uint64_t productionObservationSnapshotToken) noexcept {
    NativeProgrammableShaderTranslationAdmissionEvidence out{};
    out.diagnosticOnly = true;
    out.cacheKey = sourceIdentity.cacheKey;
    out.backendOwnerGeneration = observation.backendOwnerGeneration;
    out.productionObservationSnapshotToken =
        productionObservationSnapshotToken;
    out.translatedSemanticReceiptSnapshotToken =
        observation.semanticHandoff.translatedSemanticReceipt.reviewSnapshotToken;

    out.inputValid =
        sourceIdentity.exact_identity() &&
        !sourceIdentity.translationImplemented &&
        productionObservationSnapshotToken != 0;
    out.sourceIdentityExact =
        sourceIdentity.exact_identity() &&
        !sourceIdentity.translationImplemented;
    out.productionObservationReady =
        observation.reviewReady &&
        observation.boundaryPreserved &&
        observation.diagnosticOnly;
    out.productionObservationSnapshotMatches =
        out.productionObservationReady &&
        validate_programmable_shader_production_observation_snapshot(
            observation, productionObservationSnapshotToken);

    const auto& receipt =
        observation.semanticHandoff.translatedSemanticReceipt;
    out.translatedSemanticReceiptReady =
        observation.semanticHandoff.translatedSemanticReceiptReady &&
        receipt.reviewReady &&
        receipt.boundaryPreserved &&
        receipt.diagnosticOnly;
    out.translatedSemanticReceiptSnapshotMatches =
        out.translatedSemanticReceiptReady &&
        out.translatedSemanticReceiptSnapshotToken != 0 &&
        validate_programmable_shader_translated_semantic_receipt_snapshot(
            receipt, out.translatedSemanticReceiptSnapshotToken);
    out.cacheIdentityMatches =
        observation.cacheKey == sourceIdentity.cacheKey &&
        observation.semanticHandoff.cacheKey == sourceIdentity.cacheKey &&
        receipt.cacheKey == sourceIdentity.cacheKey;
    out.translationObjectReady =
        observation.semanticHandoff.translationObjectReady &&
        observation.semanticHandoff.translationObjectSnapshotMatches &&
        receipt.translationObjectReady &&
        receipt.translationObjectSnapshotMatches;

    out.objectBindingAuthorized =
        observation.objectBindingAuthorized ||
        observation.semanticHandoff.objectBindingAuthorized;
    out.nativeDrawPathActivationAllowed =
        observation.nativeDrawPathActivationAllowed ||
        observation.semanticHandoff.nativeDrawPathActivationAllowed;
    out.drawDispatchAuthorized =
        observation.drawDispatchAuthorized ||
        observation.semanticHandoff.drawDispatchAuthorized;

    out.boundaryPreserved =
        out.inputValid &&
        out.sourceIdentityExact &&
        out.productionObservationSnapshotMatches &&
        out.translatedSemanticReceiptSnapshotMatches &&
        out.cacheIdentityMatches &&
        out.translationObjectReady &&
        !out.objectBindingAuthorized &&
        !out.nativeDrawPathActivationAllowed &&
        !out.drawDispatchAuthorized &&
        out.diagnosticOnly;
    out.reviewReady =
        out.productionObservationReady &&
        out.translatedSemanticReceiptReady &&
        out.boundaryPreserved;
    if (out.reviewReady)
        out.reviewSnapshotToken =
            r288_programmable_translation_admission_snapshot_token(out);
    return out;
}

bool validate_programmable_shader_translation_admission_snapshot(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderProductionObservationEvidence& observation,
    std::uint64_t productionObservationSnapshotToken,
    const NativeProgrammableShaderTranslationAdmissionEvidence& admission,
    std::uint64_t reviewSnapshotToken) noexcept {
    if (!admission.reviewReady ||
        !admission.boundaryPreserved ||
        !admission.diagnosticOnly ||
        admission.objectBindingAuthorized ||
        admission.nativeDrawPathActivationAllowed ||
        admission.drawDispatchAuthorized ||
        reviewSnapshotToken == 0 ||
        admission.reviewSnapshotToken != reviewSnapshotToken)
        return false;

    const auto current =
        seal_programmable_shader_translation_admission(
            sourceIdentity,
            observation,
            productionObservationSnapshotToken);
    if (!current.reviewReady ||
        current.cacheKey != admission.cacheKey ||
        current.backendOwnerGeneration != admission.backendOwnerGeneration ||
        current.productionObservationSnapshotToken !=
            admission.productionObservationSnapshotToken ||
        current.translatedSemanticReceiptSnapshotToken !=
            admission.translatedSemanticReceiptSnapshotToken ||
        current.reviewSnapshotToken != reviewSnapshotToken)
        return false;

    return r288_programmable_translation_admission_snapshot_token(admission) ==
        reviewSnapshotToken;
}

NativeProgrammableShaderProductionSemanticReviewEvidence
NativeProgrammableShaderBackendOwnership::
materialize_semantic_translation_review_for_observation(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderProductionObservationEvidence& observation,
    std::uint64_t productionObservationSnapshotToken,
    const NativeProgrammableShaderTranslationAdmissionEvidence& admission,
    std::uint64_t admissionSnapshotToken,
    const NativeProgrammableShaderTargetBytecodeMaterializationEvidence&
        targetBytecodeMaterialization,
    const VertexInputLayoutTranslation& layout,
    const ProgrammableShaderInterfaceLinkageEvidence&
        sourceInterfaceLinkage) noexcept {
    NativeProgrammableShaderProductionSemanticReviewEvidence out{};
    out.diagnosticOnly = true;
    out.cacheKey = sourceIdentity.cacheKey;
    out.backendOwnerGeneration = owner_generation_;
    out.admissionSnapshotToken = admissionSnapshotToken;
    out.targetBytecodeMaterializationSnapshotToken =
        targetBytecodeMaterialization.reviewSnapshotToken;
    out.cacheSnapshotToken = observation.semanticHandoff.cacheSnapshotToken;
    out.slotSnapshotToken = observation.semanticHandoff.slotSnapshotToken;
    out.translationObjectSnapshotToken =
        observation.semanticHandoff.translationObjectSnapshotToken;

    out.inputValid =
        sourceIdentity.exact_identity() &&
        !sourceIdentity.translationImplemented &&
        productionObservationSnapshotToken != 0 &&
        admissionSnapshotToken != 0 &&
        sourceInterfaceLinkage.exact();
    out.ownerReady =
        ready() &&
        observation.backendOwnerGeneration == owner_generation_ &&
        observation.semanticHandoff.backendOwnerGeneration == owner_generation_;
    out.admissionReady =
        admission.reviewReady &&
        admission.boundaryPreserved &&
        admission.diagnosticOnly &&
        !admission.objectBindingAuthorized &&
        !admission.nativeDrawPathActivationAllowed &&
        !admission.drawDispatchAuthorized;
    out.admissionSnapshotMatches =
        out.admissionReady &&
        validate_programmable_shader_translation_admission_snapshot(
            sourceIdentity,
            observation,
            productionObservationSnapshotToken,
            admission,
            admissionSnapshotToken);

    const auto vertexBytecodeBytes =
        targetBytecodeMaterialization.vertexTargetBytecode.size();
    out.targetVertexBytecodeReady =
        targetBytecodeMaterialization.reviewReady &&
        targetBytecodeMaterialization.boundaryPreserved &&
        targetBytecodeMaterialization.diagnosticOnly &&
        targetBytecodeMaterialization.targetBytecodeMaterialized &&
        !targetBytecodeMaterialization.objectCreationAuthorized &&
        targetBytecodeMaterialization.reviewSnapshotToken ==
            observation.targetBytecodeMaterializationSnapshotToken &&
        targetBytecodeMaterialization.vertexTargetBytecodeBytes != 0 &&
        vertexBytecodeBytes ==
            targetBytecodeMaterialization.vertexTargetBytecodeBytes &&
        vertexBytecodeBytes <=
            static_cast<std::size_t>((std::numeric_limits<UINT>::max)()) &&
        hash_observation_payload_bytes(
            targetBytecodeMaterialization.vertexTargetBytecode.data(),
            static_cast<UINT>(vertexBytecodeBytes)) ==
            targetBytecodeMaterialization.vertexTargetBytecodeHash;
    out.inputLayoutDescriptorExact =
        hash_pipeline_input_layout_identity(layout) != 0;

    if (!out.inputValid ||
        !out.ownerReady ||
        !out.admissionSnapshotMatches ||
        !out.targetVertexBytecodeReady ||
        !out.inputLayoutDescriptorExact)
        return out;

    const auto translationObject =
        cache_.translation_object_readiness(
            device_.Get(),
            sourceIdentity,
            out.cacheSnapshotToken,
            out.slotSnapshotToken);
    out.translationObjectReady =
        translationObject.attachmentReady &&
        translationObject.objectsAttached &&
        translationObject.objectDevicesMatch &&
        translationObject.cacheKey == sourceIdentity.cacheKey;
    out.translationObjectSnapshotMatches =
        out.translationObjectReady &&
        translationObject.snapshotToken != 0 &&
        translationObject.snapshotToken ==
            out.translationObjectSnapshotToken &&
        cache_.validate_translation_object_snapshot(
            device_.Get(),
            sourceIdentity,
            out.cacheSnapshotToken,
            out.slotSnapshotToken,
            out.translationObjectSnapshotToken);
    if (!out.translationObjectSnapshotMatches)
        return out;

    ID3D11InputLayout* inputLayoutObject = nullptr;
    const auto existingLayout =
        semantic_input_layouts_.find(sourceIdentity.cacheKey);
    if (existingLayout != semantic_input_layouts_.end()) {
        inputLayoutObject = existingLayout->second.Get();
        out.inputLayoutReused = inputLayoutObject != nullptr;
    } else {
        Microsoft::WRL::ComPtr<ID3D11InputLayout> createdLayout;
        if (FAILED(device_->CreateInputLayout(
                layout.elements.data(),
                layout.elementCount,
                targetBytecodeMaterialization.vertexTargetBytecode.data(),
                vertexBytecodeBytes,
                createdLayout.ReleaseAndGetAddressOf())) ||
            !createdLayout)
            return out;
        try {
            const auto inserted = semantic_input_layouts_.emplace(
                sourceIdentity.cacheKey, createdLayout);
            if (!inserted.second)
                return out;
            inputLayoutObject = inserted.first->second.Get();
        } catch (...) {
            return out;
        }
    }
    out.inputLayoutObjectReady = inputLayoutObject != nullptr;
    if (!out.inputLayoutObjectReady ||
        !cache_.attach_input_layout_for_observation(
            device_.Get(),
            sourceIdentity,
            out.cacheSnapshotToken,
            out.slotSnapshotToken,
            out.translationObjectSnapshotToken,
            layout,
            inputLayoutObject))
        return out;

    out.inputLayout =
        cache_.input_layout_readiness(
            device_.Get(),
            sourceIdentity,
            out.cacheSnapshotToken,
            out.slotSnapshotToken,
            out.translationObjectSnapshotToken,
            layout);
    out.inputLayoutSnapshotToken = out.inputLayout.snapshotToken;
    out.inputLayoutReceiptReady =
        out.inputLayout.attachmentReady &&
        out.inputLayout.inputLayoutAttached &&
        out.inputLayout.inputLayoutDeviceMatches &&
        out.inputLayout.layoutIdentityExact &&
        out.inputLayout.cacheKey == sourceIdentity.cacheKey;
    out.inputLayoutSnapshotMatches =
        out.inputLayoutReceiptReady &&
        out.inputLayoutSnapshotToken != 0 &&
        cache_.validate_input_layout_snapshot(
            device_.Get(),
            sourceIdentity,
            out.cacheSnapshotToken,
            out.slotSnapshotToken,
            out.translationObjectSnapshotToken,
            layout,
            out.inputLayoutSnapshotToken);
    if (!out.inputLayoutSnapshotMatches)
        return out;

    const auto& translatedSemanticReceipt =
        observation.semanticHandoff.translatedSemanticReceipt;
    out.semanticTranslation =
        compose_programmable_shader_semantic_translation_readiness(
            sourceIdentity,
            translationObject,
            out.translationObjectSnapshotToken,
            out.inputLayout,
            out.inputLayoutSnapshotToken,
            translatedSemanticReceipt,
            observation.semanticHandoff.
                translatedSemanticReceiptSnapshotToken,
            sourceInterfaceLinkage);
    out.semanticTranslationSnapshotToken =
        out.semanticTranslation.reviewSnapshotToken;
    out.semanticTranslationReady =
        out.semanticTranslation.reviewReady &&
        out.semanticTranslation.boundaryPreserved &&
        out.semanticTranslation.diagnosticOnly &&
        out.semanticTranslation.semanticProofPresent;
    out.semanticTranslationSnapshotMatches =
        out.semanticTranslationReady &&
        out.semanticTranslationSnapshotToken != 0 &&
        validate_programmable_shader_semantic_translation_readiness_snapshot(
            sourceIdentity,
            translationObject,
            out.translationObjectSnapshotToken,
            out.inputLayout,
            out.inputLayoutSnapshotToken,
            translatedSemanticReceipt,
            observation.semanticHandoff.
                translatedSemanticReceiptSnapshotToken,
            sourceInterfaceLinkage,
            out.semanticTranslationSnapshotToken);

    out.objectBindingAuthorized =
        admission.objectBindingAuthorized ||
        observation.objectBindingAuthorized ||
        observation.semanticHandoff.objectBindingAuthorized;
    out.nativeDrawPathActivationAllowed =
        admission.nativeDrawPathActivationAllowed ||
        observation.nativeDrawPathActivationAllowed ||
        observation.semanticHandoff.nativeDrawPathActivationAllowed;
    out.drawDispatchAuthorized =
        admission.drawDispatchAuthorized ||
        observation.drawDispatchAuthorized ||
        observation.semanticHandoff.drawDispatchAuthorized;

    out.boundaryPreserved =
        out.admissionSnapshotMatches &&
        out.translationObjectSnapshotMatches &&
        out.inputLayoutSnapshotMatches &&
        out.semanticTranslationSnapshotMatches &&
        !out.objectBindingAuthorized &&
        !out.nativeDrawPathActivationAllowed &&
        !out.drawDispatchAuthorized &&
        out.diagnosticOnly;
    out.reviewReady =
        out.inputValid &&
        out.ownerReady &&
        out.targetVertexBytecodeReady &&
        out.inputLayoutDescriptorExact &&
        out.inputLayoutObjectReady &&
        out.inputLayoutReceiptReady &&
        out.semanticTranslationReady &&
        out.boundaryPreserved;
    if (out.reviewReady)
        out.reviewSnapshotToken =
            r289_programmable_production_semantic_review_snapshot_token(out);
    return out;
}

bool NativeProgrammableShaderBackendOwnership::
validate_semantic_translation_review_snapshot(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderProductionObservationEvidence& observation,
    std::uint64_t productionObservationSnapshotToken,
    const NativeProgrammableShaderTranslationAdmissionEvidence& admission,
    std::uint64_t admissionSnapshotToken,
    const NativeProgrammableShaderTargetBytecodeMaterializationEvidence&
        targetBytecodeMaterialization,
    const VertexInputLayoutTranslation& layout,
    const ProgrammableShaderInterfaceLinkageEvidence&
        sourceInterfaceLinkage,
    const NativeProgrammableShaderProductionSemanticReviewEvidence& review,
    std::uint64_t reviewSnapshotToken) const noexcept {
    if (!review.reviewReady ||
        !review.boundaryPreserved ||
        !review.diagnosticOnly ||
        review.objectBindingAuthorized ||
        review.nativeDrawPathActivationAllowed ||
        review.drawDispatchAuthorized ||
        reviewSnapshotToken == 0 ||
        review.reviewSnapshotToken != reviewSnapshotToken ||
        !ready() ||
        review.backendOwnerGeneration != owner_generation_ ||
        review.cacheKey != sourceIdentity.cacheKey ||
        review.admissionSnapshotToken != admissionSnapshotToken ||
        review.targetBytecodeMaterializationSnapshotToken !=
            targetBytecodeMaterialization.reviewSnapshotToken ||
        !validate_programmable_shader_translation_admission_snapshot(
            sourceIdentity,
            observation,
            productionObservationSnapshotToken,
            admission,
            admissionSnapshotToken))
        return false;

    const auto vertexBytecodeBytes =
        targetBytecodeMaterialization.vertexTargetBytecode.size();
    if (!targetBytecodeMaterialization.reviewReady ||
        targetBytecodeMaterialization.reviewSnapshotToken !=
            observation.targetBytecodeMaterializationSnapshotToken ||
        vertexBytecodeBytes == 0 ||
        vertexBytecodeBytes !=
            targetBytecodeMaterialization.vertexTargetBytecodeBytes ||
        vertexBytecodeBytes >
            static_cast<std::size_t>((std::numeric_limits<UINT>::max)()) ||
        hash_observation_payload_bytes(
            targetBytecodeMaterialization.vertexTargetBytecode.data(),
            static_cast<UINT>(vertexBytecodeBytes)) !=
            targetBytecodeMaterialization.vertexTargetBytecodeHash)
        return false;

    const auto translationObject =
        cache_.translation_object_readiness(
            device_.Get(),
            sourceIdentity,
            review.cacheSnapshotToken,
            review.slotSnapshotToken);
    if (!translationObject.attachmentReady ||
        !cache_.validate_translation_object_snapshot(
            device_.Get(),
            sourceIdentity,
            review.cacheSnapshotToken,
            review.slotSnapshotToken,
            review.translationObjectSnapshotToken))
        return false;

    if (!cache_.validate_input_layout_snapshot(
            device_.Get(),
            sourceIdentity,
            review.cacheSnapshotToken,
            review.slotSnapshotToken,
            review.translationObjectSnapshotToken,
            layout,
            review.inputLayoutSnapshotToken))
        return false;

    const auto& translatedSemanticReceipt =
        observation.semanticHandoff.translatedSemanticReceipt;
    if (!validate_programmable_shader_semantic_translation_readiness_snapshot(
            sourceIdentity,
            translationObject,
            review.translationObjectSnapshotToken,
            review.inputLayout,
            review.inputLayoutSnapshotToken,
            translatedSemanticReceipt,
            observation.semanticHandoff.
                translatedSemanticReceiptSnapshotToken,
            sourceInterfaceLinkage,
            review.semanticTranslationSnapshotToken))
        return false;

    return r289_programmable_production_semantic_review_snapshot_token(review) ==
        reviewSnapshotToken;
}

NativeProgrammableShaderProductionActivationPrerequisiteEvidence
observe_programmable_shader_production_activation_prerequisites(
    const NativeProgrammableShaderProductionSemanticReviewEvidence&
        productionSemanticReview,
    std::uint64_t productionSemanticReviewSnapshotToken,
    const NativeProgrammableShaderDormantSourceRevalidationReadiness&
        sourceRevalidation,
    std::uint64_t sourceRevalidationSnapshotToken,
    const NativeProgrammableShaderOutputResourceBehaviorReadiness&
        resourceBehavior,
    std::uint64_t resourceBehaviorSnapshotToken) noexcept {
    NativeProgrammableShaderProductionActivationPrerequisiteEvidence out{};
    out.diagnosticOnly = true;
    out.cacheKey = productionSemanticReview.cacheKey;
    out.productionSemanticReviewSnapshotToken =
        productionSemanticReviewSnapshotToken;
    out.sourceRevalidationSnapshotToken = sourceRevalidationSnapshotToken;
    out.resourceBehaviorSnapshotToken = resourceBehaviorSnapshotToken;

    out.inputValid =
        productionSemanticReviewSnapshotToken != 0 &&
        sourceRevalidationSnapshotToken != 0 &&
        resourceBehaviorSnapshotToken != 0 &&
        out.cacheKey != 0;
    out.productionSemanticReviewReady =
        productionSemanticReview.reviewReady &&
        productionSemanticReview.diagnosticOnly &&
        productionSemanticReview.boundaryPreserved &&
        !productionSemanticReview.objectBindingAuthorized &&
        !productionSemanticReview.nativeDrawPathActivationAllowed &&
        !productionSemanticReview.drawDispatchAuthorized;
    out.productionSemanticReviewSnapshotMatches =
        out.productionSemanticReviewReady &&
        productionSemanticReview.reviewSnapshotToken ==
            productionSemanticReviewSnapshotToken &&
        r289_programmable_production_semantic_review_snapshot_token(
            productionSemanticReview) ==
            productionSemanticReviewSnapshotToken;

    out.sourceRevalidationReady =
        sourceRevalidation.ready &&
        sourceRevalidation.boundaryPreserved &&
        sourceRevalidation.cacheKey != 0;
    out.sourceRevalidationSnapshotMatches =
        out.sourceRevalidationReady &&
        sourceRevalidation.snapshotToken ==
            sourceRevalidationSnapshotToken;
    out.resourceBehaviorReady =
        resourceBehavior.reviewReady &&
        resourceBehavior.boundaryPreserved &&
        resourceBehavior.fullResourceBehaviorProofPresent &&
        resourceBehavior.missingResourceScopeMask == 0;
    out.resourceBehaviorSnapshotMatches =
        out.resourceBehaviorReady &&
        resourceBehavior.reviewSnapshotToken ==
            resourceBehaviorSnapshotToken;
    out.resourceBehaviorPayloadSnapshotMatches =
        out.resourceBehaviorReady &&
        resourceBehavior.reviewSnapshotToken ==
            recompute_programmable_output_resource_behavior_payload_snapshot(
                resourceBehavior);

    if (out.inputValid &&
        out.productionSemanticReviewSnapshotMatches &&
        out.sourceRevalidationSnapshotMatches &&
        out.resourceBehaviorSnapshotMatches &&
        out.resourceBehaviorPayloadSnapshotMatches) {
        out.prerequisites =
            compose_programmable_activation_prerequisite_handoff(
                sourceRevalidation,
                sourceRevalidationSnapshotToken,
                resourceBehavior,
                resourceBehaviorSnapshotToken,
                productionSemanticReview.inputLayout,
                productionSemanticReview.inputLayoutSnapshotToken,
                productionSemanticReview.semanticTranslation,
                productionSemanticReview.semanticTranslationSnapshotToken);
        out.prerequisiteHandoffReady =
            out.prerequisites.reviewReady &&
            out.prerequisites.diagnosticOnly;
        out.prerequisiteHandoffSnapshotToken =
            out.prerequisites.reviewSnapshotToken;
        out.prerequisiteHandoffSnapshotMatches =
            out.prerequisiteHandoffReady &&
            validate_programmable_activation_prerequisite_handoff_snapshot(
                sourceRevalidation,
                sourceRevalidationSnapshotToken,
                resourceBehavior,
                resourceBehaviorSnapshotToken,
                productionSemanticReview.inputLayout,
                productionSemanticReview.inputLayoutSnapshotToken,
                productionSemanticReview.semanticTranslation,
                productionSemanticReview.semanticTranslationSnapshotToken,
                out.prerequisiteHandoffSnapshotToken);
    }

    out.missingPrerequisiteMask =
        out.prerequisites.missingPrerequisiteMask;
    out.staticPrerequisitesSatisfied =
        out.prerequisiteHandoffSnapshotMatches &&
        out.prerequisites.activationPrerequisitesSatisfied &&
        out.missingPrerequisiteMask == 0;
    out.objectBindingAuthorized =
        productionSemanticReview.objectBindingAuthorized;
    out.nativeDrawPathActivationAllowed =
        productionSemanticReview.nativeDrawPathActivationAllowed ||
        out.prerequisites.nativeDrawPathActivationAllowed;
    out.drawDispatchAuthorized =
        productionSemanticReview.drawDispatchAuthorized ||
        out.prerequisites.drawDispatchAuthorized;
    out.boundaryPreserved =
        out.productionSemanticReviewSnapshotMatches &&
        out.sourceRevalidationSnapshotMatches &&
        out.resourceBehaviorSnapshotMatches &&
        out.resourceBehaviorPayloadSnapshotMatches &&
        out.staticPrerequisitesSatisfied &&
        out.prerequisites.boundaryPreserved &&
        out.prerequisites.activationSnapshotToken == 0 &&
        out.diagnosticOnly &&
        !out.objectBindingAuthorized &&
        !out.nativeDrawPathActivationAllowed &&
        !out.drawDispatchAuthorized;
    out.reviewReady =
        out.inputValid &&
        out.prerequisiteHandoffSnapshotMatches &&
        out.boundaryPreserved;
    if (out.reviewReady)
        out.reviewSnapshotToken =
            r292_programmable_production_activation_prerequisite_snapshot_token(
                out);
    return out;
}

bool validate_programmable_shader_production_activation_prerequisite_snapshot(
    const NativeProgrammableShaderProductionSemanticReviewEvidence&
        productionSemanticReview,
    std::uint64_t productionSemanticReviewSnapshotToken,
    const NativeProgrammableShaderDormantSourceRevalidationReadiness&
        sourceRevalidation,
    std::uint64_t sourceRevalidationSnapshotToken,
    const NativeProgrammableShaderOutputResourceBehaviorReadiness&
        resourceBehavior,
    std::uint64_t resourceBehaviorSnapshotToken,
    const NativeProgrammableShaderProductionActivationPrerequisiteEvidence&
        observation,
    std::uint64_t reviewSnapshotToken) noexcept {
    if (!observation.reviewReady ||
        !observation.boundaryPreserved ||
        !observation.diagnosticOnly ||
        observation.objectBindingAuthorized ||
        observation.nativeDrawPathActivationAllowed ||
        observation.drawDispatchAuthorized ||
        !observation.staticPrerequisitesSatisfied ||
        observation.missingPrerequisiteMask != 0 ||
        observation.prerequisites.activationSnapshotToken != 0 ||
        reviewSnapshotToken == 0 ||
        observation.reviewSnapshotToken != reviewSnapshotToken)
        return false;

    const auto current =
        observe_programmable_shader_production_activation_prerequisites(
            productionSemanticReview,
            productionSemanticReviewSnapshotToken,
            sourceRevalidation,
            sourceRevalidationSnapshotToken,
            resourceBehavior,
            resourceBehaviorSnapshotToken);
    const auto currentPayloadSnapshotToken =
        r305_programmable_production_activation_payload_snapshot_token(current);
    const auto observedPayloadSnapshotToken =
        r305_programmable_production_activation_payload_snapshot_token(
            observation);
    if (currentPayloadSnapshotToken == 0 ||
        currentPayloadSnapshotToken != observedPayloadSnapshotToken ||
        !current.reviewReady ||
        current.cacheKey != observation.cacheKey ||
        current.productionSemanticReviewSnapshotToken !=
            observation.productionSemanticReviewSnapshotToken ||
        current.sourceRevalidationSnapshotToken !=
            observation.sourceRevalidationSnapshotToken ||
        current.resourceBehaviorSnapshotToken !=
            observation.resourceBehaviorSnapshotToken ||
        current.prerequisiteHandoffSnapshotToken !=
            observation.prerequisiteHandoffSnapshotToken ||
        current.reviewSnapshotToken != reviewSnapshotToken)
        return false;

    return r292_programmable_production_activation_prerequisite_snapshot_token(
        observation) == reviewSnapshotToken;
}

bool NativeFixedFunctionPipelineBundle::initialize(
    ID3D11Device* device,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype) noexcept {

    shutdown();
    const auto inputLayoutIdentity =
        hash_pipeline_input_layout_identity(layout);
    if (!device || inputLayoutIdentity == 0 ||
        !vertexPrototype.generated() || !pixelPrototype.generated() ||
        vertexPrototype.sourceHash == 0 || pixelPrototype.sourceHash == 0)
        return false;

    Microsoft::WRL::ComPtr<ID3DBlob> vertexBytecode;
    Microsoft::WRL::ComPtr<ID3DBlob> pixelBytecode;
    if (!compile_shader_source(
            vertexPrototype.source,
            "OutRunR97FixedFunctionVertexShader",
            "vs_4_0", vertexBytecode) ||
        !compile_shader_source(
            pixelPrototype.source,
            "OutRunR97FixedFunctionPixelShader",
            "ps_4_0", pixelBytecode))
        return false;

    Microsoft::WRL::ComPtr<ID3D11VertexShader> vertexShader;
    if (FAILED(device->CreateVertexShader(
            vertexBytecode->GetBufferPointer(),
            vertexBytecode->GetBufferSize(), nullptr,
            vertexShader.ReleaseAndGetAddressOf())) ||
        !vertexShader)
        return false;

    Microsoft::WRL::ComPtr<ID3D11InputLayout> inputLayout;
    if (FAILED(device->CreateInputLayout(
            layout.elements.data(), layout.elementCount,
            vertexBytecode->GetBufferPointer(),
            vertexBytecode->GetBufferSize(),
            inputLayout.ReleaseAndGetAddressOf())) ||
        !inputLayout)
        return false;

    Microsoft::WRL::ComPtr<ID3D11PixelShader> pixelShader;
    if (FAILED(device->CreatePixelShader(
            pixelBytecode->GetBufferPointer(),
            pixelBytecode->GetBufferSize(), nullptr,
            pixelShader.ReleaseAndGetAddressOf())) ||
        !pixelShader)
        return false;

    if (!transform_buffer_.initialize(device)) {
        shutdown();
        return false;
    }

    device_ = device;
    vertex_shader_ = std::move(vertexShader);
    pixel_shader_ = std::move(pixelShader);
    input_layout_ = std::move(inputLayout);
    input_layout_identity_ = inputLayoutIdentity;
    vertex_shader_source_hash_ = vertexPrototype.sourceHash;
    pixel_shader_source_hash_ = pixelPrototype.sourceHash;
    ++bundle_generation_;
    if (bundle_generation_ == 0)
        ++bundle_generation_;
    return true;
}

NativeFixedFunctionPipelineReadiness
NativeFixedFunctionPipelineBundle::translation_readiness(
    ID3D11Device* expectedDevice,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype) const noexcept {
    NativeFixedFunctionPipelineReadiness out{};
    const auto inputLayoutIdentity =
        hash_pipeline_input_layout_identity(layout);
    if (!expectedDevice || inputLayoutIdentity == 0 ||
        !vertexPrototype.generated() || !pixelPrototype.generated() ||
        vertexPrototype.sourceHash == 0 || pixelPrototype.sourceHash == 0)
        return out;

    out.inputValid = true;
    out.bundleReady = ready();
    out.bundleGeneration = bundle_generation_;
    out.inputLayoutMatches =
        input_layout_identity_ != 0 &&
        input_layout_identity_ == inputLayoutIdentity;
    out.vertexShaderMatches =
        vertex_shader_source_hash_ != 0 &&
        vertex_shader_source_hash_ == vertexPrototype.sourceHash;
    out.pixelShaderMatches =
        pixel_shader_source_hash_ != 0 &&
        pixel_shader_source_hash_ == pixelPrototype.sourceHash;

    if (out.bundleReady) {
        Microsoft::WRL::ComPtr<ID3D11Device> vertexDevice;
        Microsoft::WRL::ComPtr<ID3D11Device> pixelDevice;
        Microsoft::WRL::ComPtr<ID3D11Device> layoutDevice;
        Microsoft::WRL::ComPtr<ID3D11Device> transformDevice;
        vertex_shader_->GetDevice(vertexDevice.ReleaseAndGetAddressOf());
        pixel_shader_->GetDevice(pixelDevice.ReleaseAndGetAddressOf());
        input_layout_->GetDevice(layoutDevice.ReleaseAndGetAddressOf());
        transform_buffer_.buffer()->GetDevice(
            transformDevice.ReleaseAndGetAddressOf());
        out.deviceMatches =
            device_.Get() == expectedDevice &&
            vertexDevice.Get() == expectedDevice &&
            pixelDevice.Get() == expectedDevice &&
            layoutDevice.Get() == expectedDevice &&
            transformDevice.Get() == expectedDevice;
    }

    out.ready =
        out.bundleReady &&
        out.deviceMatches &&
        out.inputLayoutMatches &&
        out.vertexShaderMatches &&
        out.pixelShaderMatches &&
        out.bundleGeneration != 0;
    if (out.ready) {
        std::uint64_t snapshotToken = 0xcbf29ce484222325ull;
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken,
            static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(this)));
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken,
            static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(expectedDevice)));
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, out.bundleGeneration);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, input_layout_identity_);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, vertex_shader_source_hash_);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, pixel_shader_source_hash_);
        out.snapshotToken = snapshotToken == 0 ? 1 : snapshotToken;
    }
    return out;
}

bool NativeFixedFunctionPipelineBundle::validate_translation_snapshot(
    ID3D11Device* expectedDevice,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    std::uint64_t snapshotToken) const noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = translation_readiness(
        expectedDevice, layout, vertexPrototype, pixelPrototype);
    return current.ready && current.snapshotToken == snapshotToken;
}

bool NativeFixedFunctionPipelineBundle::upload_transform_for_observation(
    ID3D11DeviceContext* context,
    const FixedFunctionTransformConstants& constants) noexcept {
    if (!ready() || !context)
        return false;
    return transform_buffer_.upload_and_bind(context, constants);
}

bool NativeFixedFunctionPipelineBundle::bind_for_observation(
    ID3D11DeviceContext* context,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    std::uint64_t snapshotToken) const noexcept {

    // R154: a deferred context records commands but does not own the live
    // immediate IA/VS/PS pipeline consumed by native Draw.
    if (!context ||
        context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE ||
        !ready() || snapshotToken == 0 ||
        !validate_translation_snapshot(
            device_.Get(), layout, vertexPrototype, pixelPrototype,
            snapshotToken))
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    if (!contextDevice || contextDevice.Get() != device_.Get())
        return false;

    context->IASetInputLayout(input_layout_.Get());
    context->VSSetShader(vertex_shader_.Get(), nullptr, 0);
    context->PSSetShader(pixel_shader_.Get(), nullptr, 0);
    // R147 fixed-function draws must not inherit programmable stages that do
    // not exist in the D3D9 fixed-function contract. Clear them at the same
    // dormant observation boundary as IA/VS/PS before issuing any readiness.
    context->GSSetShader(nullptr, nullptr, 0);
    context->HSSetShader(nullptr, nullptr, 0);
    context->DSSetShader(nullptr, nullptr, 0);
    ID3D11Buffer* nullStreamOutputTargets[D3D11_SO_BUFFER_SLOT_COUNT]{};
    UINT nullStreamOutputOffsets[D3D11_SO_BUFFER_SLOT_COUNT]{};
    context->SOSetTargets(
        D3D11_SO_BUFFER_SLOT_COUNT,
        nullStreamOutputTargets,
        nullStreamOutputOffsets);
    context->SetPredication(nullptr, FALSE);

    Microsoft::WRL::ComPtr<ID3D11InputLayout> boundInputLayout;
    Microsoft::WRL::ComPtr<ID3D11VertexShader> boundVertexShader;
    Microsoft::WRL::ComPtr<ID3D11PixelShader> boundPixelShader;
    Microsoft::WRL::ComPtr<ID3D11GeometryShader> boundGeometryShader;
    Microsoft::WRL::ComPtr<ID3D11HullShader> boundHullShader;
    Microsoft::WRL::ComPtr<ID3D11DomainShader> boundDomainShader;
    ID3D11Buffer* boundStreamOutputTargets[D3D11_SO_BUFFER_SLOT_COUNT]{};
    Microsoft::WRL::ComPtr<ID3D11Predicate> boundPredicate;
    BOOL boundPredicateValue = FALSE;
    context->IAGetInputLayout(boundInputLayout.ReleaseAndGetAddressOf());
    context->VSGetShader(
        boundVertexShader.ReleaseAndGetAddressOf(), nullptr, nullptr);
    context->PSGetShader(
        boundPixelShader.ReleaseAndGetAddressOf(), nullptr, nullptr);
    context->GSGetShader(
        boundGeometryShader.ReleaseAndGetAddressOf(), nullptr, nullptr);
    context->HSGetShader(
        boundHullShader.ReleaseAndGetAddressOf(), nullptr, nullptr);
    context->DSGetShader(
        boundDomainShader.ReleaseAndGetAddressOf(), nullptr, nullptr);
    context->SOGetTargets(
        D3D11_SO_BUFFER_SLOT_COUNT, boundStreamOutputTargets);
    context->GetPredication(
        boundPredicate.ReleaseAndGetAddressOf(), &boundPredicateValue);
    bool streamOutputTargetsClear = true;
    for (UINT slot = 0; slot < D3D11_SO_BUFFER_SLOT_COUNT; ++slot) {
        if (boundStreamOutputTargets[slot]) {
            streamOutputTargetsClear = false;
            boundStreamOutputTargets[slot]->Release();
            boundStreamOutputTargets[slot] = nullptr;
        }
    }
    const bool predicationClear = boundPredicate.Get() == nullptr;

    if (boundInputLayout.Get() != input_layout_.Get() ||
        boundVertexShader.Get() != vertex_shader_.Get() ||
        boundPixelShader.Get() != pixel_shader_.Get() ||
        boundGeometryShader.Get() != nullptr ||
        boundHullShader.Get() != nullptr ||
        boundDomainShader.Get() != nullptr ||
        !streamOutputTargetsClear ||
        !predicationClear) {
        context->IASetInputLayout(nullptr);
        context->VSSetShader(nullptr, nullptr, 0);
        context->PSSetShader(nullptr, nullptr, 0);
        context->GSSetShader(nullptr, nullptr, 0);
        context->HSSetShader(nullptr, nullptr, 0);
        context->DSSetShader(nullptr, nullptr, 0);
        context->SOSetTargets(
            D3D11_SO_BUFFER_SLOT_COUNT,
            nullStreamOutputTargets,
            nullStreamOutputOffsets);
        context->SetPredication(nullptr, FALSE);
        return false;
    }
    return true;
}

NativeFixedFunctionPipelineBindingReadiness
NativeFixedFunctionPipelineBundle::binding_readiness(
    ID3D11DeviceContext* context,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    std::uint64_t pipelineSnapshotToken) const noexcept {
    NativeFixedFunctionPipelineBindingReadiness out{};
    out.pipelineSnapshotToken = pipelineSnapshotToken;
    // R154: same-device deferred context state is not a live draw receipt.
    out.inputValid = context != nullptr &&
        context->GetType() == D3D11_DEVICE_CONTEXT_IMMEDIATE &&
        pipelineSnapshotToken != 0;
    out.bundleReady = ready();
    out.translationSnapshotValid =
        out.inputValid && out.bundleReady &&
        validate_translation_snapshot(
            device_.Get(), layout, vertexPrototype, pixelPrototype,
            pipelineSnapshotToken);

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    if (context)
        context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    out.contextMatches =
        contextDevice && device_ && contextDevice.Get() == device_.Get();

    if (out.translationSnapshotValid && out.contextMatches) {
        Microsoft::WRL::ComPtr<ID3D11InputLayout> boundInputLayout;
        Microsoft::WRL::ComPtr<ID3D11VertexShader> boundVertexShader;
        Microsoft::WRL::ComPtr<ID3D11PixelShader> boundPixelShader;
        Microsoft::WRL::ComPtr<ID3D11GeometryShader> boundGeometryShader;
        Microsoft::WRL::ComPtr<ID3D11HullShader> boundHullShader;
        Microsoft::WRL::ComPtr<ID3D11DomainShader> boundDomainShader;
        ID3D11Buffer* boundStreamOutputTargets[D3D11_SO_BUFFER_SLOT_COUNT]{};
        Microsoft::WRL::ComPtr<ID3D11Predicate> boundPredicate;
        BOOL boundPredicateValue = FALSE;
        context->IAGetInputLayout(boundInputLayout.ReleaseAndGetAddressOf());
        context->VSGetShader(
            boundVertexShader.ReleaseAndGetAddressOf(), nullptr, nullptr);
        context->PSGetShader(
            boundPixelShader.ReleaseAndGetAddressOf(), nullptr, nullptr);
        context->GSGetShader(
            boundGeometryShader.ReleaseAndGetAddressOf(), nullptr, nullptr);
        context->HSGetShader(
            boundHullShader.ReleaseAndGetAddressOf(), nullptr, nullptr);
        context->DSGetShader(
            boundDomainShader.ReleaseAndGetAddressOf(), nullptr, nullptr);
        context->SOGetTargets(
            D3D11_SO_BUFFER_SLOT_COUNT, boundStreamOutputTargets);
        context->GetPredication(
            boundPredicate.ReleaseAndGetAddressOf(), &boundPredicateValue);
        out.geometryShaderClear = boundGeometryShader.Get() == nullptr;
        out.hullShaderClear = boundHullShader.Get() == nullptr;
        out.domainShaderClear = boundDomainShader.Get() == nullptr;
        out.graphicsStageIsolationReady =
            out.geometryShaderClear &&
            out.hullShaderClear &&
            out.domainShaderClear;
        out.streamOutputTargetsClear = true;
        for (UINT slot = 0; slot < D3D11_SO_BUFFER_SLOT_COUNT; ++slot) {
            if (boundStreamOutputTargets[slot]) {
                out.streamOutputTargetsClear = false;
                boundStreamOutputTargets[slot]->Release();
                boundStreamOutputTargets[slot] = nullptr;
            }
        }
        out.predicationClear = boundPredicate.Get() == nullptr;
        out.drawSideEffectIsolationReady =
            out.streamOutputTargetsClear && out.predicationClear;
        out.boundExact =
            boundInputLayout.Get() == input_layout_.Get() &&
            boundVertexShader.Get() == vertex_shader_.Get() &&
            boundPixelShader.Get() == pixel_shader_.Get() &&
            out.graphicsStageIsolationReady &&
            out.drawSideEffectIsolationReady;
    }

    out.ready =
        out.inputValid && out.bundleReady && out.contextMatches &&
        out.translationSnapshotValid && out.boundExact;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(token, pipelineSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(device_.Get())));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(input_layout_.Get())));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(vertex_shader_.Get())));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(pixel_shader_.Get())));
        // Version the live binding identity with both R147 shader-stage and
        // R148 SO/predication isolation so older snapshots cannot alias this
        // stronger dormant draw proof.
        token = mix_readiness_snapshot_token(
            token, out.graphicsStageIsolationReady ? 0x147u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.drawSideEffectIsolationReady ? 0x148u : 0u);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeFixedFunctionPipelineBundle::validate_binding_snapshot(
    ID3D11DeviceContext* context,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    std::uint64_t pipelineSnapshotToken,
    std::uint64_t bindingSnapshotToken) const noexcept {
    if (bindingSnapshotToken == 0)
        return false;
    const auto current = binding_readiness(
        context, layout, vertexPrototype, pixelPrototype,
        pipelineSnapshotToken);
    return current.ready && current.snapshotToken == bindingSnapshotToken;
}

NativeFixedFunctionActivationReadiness
compose_fixed_function_activation_readiness(
    const NativeFixedFunctionPipelineReadiness& pipeline,
    const NativeManagedTextureStageReadiness& textureStages) noexcept {
    NativeFixedFunctionActivationReadiness out{};
    out.requiredTextureMask = textureStages.requiredMask;
    out.pipelineSnapshotToken = pipeline.snapshotToken;
    out.textureSnapshotToken = textureStages.snapshotToken;

    const bool texturesRequired = textureStages.requiredMask != 0;
    const bool textureMaskReady =
        textureStages.readyMask == textureStages.requiredMask &&
        textureStages.pendingMask == 0;

    out.inputValid = pipeline.inputValid && textureStages.inputValid;
    out.pipelineReady = pipeline.ready && pipeline.snapshotToken != 0;
    out.textureStagesReady =
        textureStages.allRequiredReady &&
        textureMaskReady &&
        (!texturesRequired || textureStages.snapshotToken != 0);
    out.componentSnapshotsPresent =
        pipeline.snapshotToken != 0 &&
        (!texturesRequired || textureStages.snapshotToken != 0);
    out.ready =
        out.inputValid &&
        out.pipelineReady &&
        out.textureStagesReady &&
        out.componentSnapshotsPresent;

    if (out.ready) {
        std::uint64_t activationToken = 0xcbf29ce484222325ull;
        activationToken = mix_readiness_snapshot_token(
            activationToken, out.pipelineSnapshotToken);
        activationToken = mix_readiness_snapshot_token(
            activationToken, out.textureSnapshotToken);
        activationToken = mix_readiness_snapshot_token(
            activationToken,
            static_cast<std::uint64_t>(out.requiredTextureMask));
        out.snapshotToken = activationToken == 0 ? 1 : activationToken;
    }
    return out;
}

bool validate_fixed_function_activation_snapshot(
    const NativeFixedFunctionPipelineReadiness& pipeline,
    const NativeManagedTextureStageReadiness& textureStages,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = compose_fixed_function_activation_readiness(
        pipeline, textureStages);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionGeometryReadiness
compose_fixed_function_geometry_readiness(
    const NativeManagedBufferMirrorReadiness& vertexBuffer,
    bool indexed,
    const NativeManagedBufferMirrorReadiness& indexBuffer,
    D3DPRIMITIVETYPE primitive) noexcept {
    NativeFixedFunctionGeometryReadiness out{};
    const auto topology = translate_primitive(primitive);
    out.indexBufferRequired = indexed;
    out.topology = topology.value;
    out.vertexBufferSnapshotToken = vertexBuffer.snapshotToken;
    out.indexBufferSnapshotToken = indexed ? indexBuffer.snapshotToken : 0;
    out.inputValid =
        vertexBuffer.inputValid &&
        vertexBuffer.role == ResourceRole::Vertex &&
        (!indexed ||
         (indexBuffer.inputValid &&
          indexBuffer.role == ResourceRole::Index));
    out.vertexBufferReady =
        vertexBuffer.ready && vertexBuffer.snapshotToken != 0;
    out.indexBufferReady =
        !indexed || (indexBuffer.ready && indexBuffer.snapshotToken != 0);
    out.topologyReady =
        topology.exact &&
        topology.value != D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    out.componentSnapshotsPresent =
        vertexBuffer.snapshotToken != 0 &&
        (!indexed || indexBuffer.snapshotToken != 0);
    out.ready =
        out.inputValid &&
        out.vertexBufferReady &&
        out.indexBufferReady &&
        out.topologyReady &&
        out.componentSnapshotsPresent;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.vertexBufferSnapshotToken);
        token = mix_readiness_snapshot_token(token, indexed ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.indexBufferSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.topology));
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_geometry_snapshot(
    const NativeManagedBufferMirrorReadiness& vertexBuffer,
    bool indexed,
    const NativeManagedBufferMirrorReadiness& indexBuffer,
    D3DPRIMITIVETYPE primitive,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = compose_fixed_function_geometry_readiness(
        vertexBuffer, indexed, indexBuffer, primitive);
    return current.ready && current.snapshotToken == snapshotToken;
}

bool validate_fixed_function_direct_geometry_readiness_integrity(
    const NativeFixedFunctionGeometryReadiness& geometry) noexcept {
    if (!geometry.inputValid ||
        !geometry.vertexBufferReady ||
        !geometry.indexBufferReady ||
        !geometry.topologyReady ||
        !geometry.componentSnapshotsPresent ||
        !geometry.ready ||
        geometry.generatedIndexBufferRequired ||
        geometry.generatedIndexBufferReady ||
        geometry.generatedIndexBufferMatchesDraw ||
        geometry.generatedIndexBufferSnapshotToken != 0 ||
        geometry.vertexBufferSnapshotToken == 0 ||
        geometry.topology == D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED ||
        geometry.snapshotToken == 0)
        return false;

    if (geometry.indexBufferRequired) {
        if (geometry.indexBufferSnapshotToken == 0)
            return false;
    } else if (geometry.indexBufferSnapshotToken != 0) {
        return false;
    }

    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(
        token, geometry.vertexBufferSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, geometry.indexBufferRequired ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, geometry.indexBufferSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, static_cast<std::uint32_t>(geometry.topology));
    token = token == 0 ? 1 : token;
    return token == geometry.snapshotToken;
}

NativeFixedFunctionGeometryBindingReadiness
observe_fixed_function_geometry_binding(
    ID3D11DeviceContext* context,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeManagedBufferShadow* indexBuffer,
    DXGI_FORMAT indexFormat,
    UINT indexOffset) noexcept {
    NativeFixedFunctionGeometryBindingReadiness out{};
    out.indexed = geometry.indexBufferRequired;
    out.vertexStride = vertexStride;
    out.vertexOffset = vertexOffset;
    out.indexFormat = indexFormat;
    out.indexOffset = indexOffset;
    out.topology = geometry.topology;
    out.geometrySnapshotToken = geometry.snapshotToken;
    out.vertexBufferSnapshotToken = geometry.vertexBufferSnapshotToken;
    out.indexBufferSnapshotToken = geometry.indexBufferSnapshotToken;

    const bool indexFormatExact =
        indexFormat == DXGI_FORMAT_R16_UINT ||
        indexFormat == DXGI_FORMAT_R32_UINT;
    const UINT indexElementBytes =
        indexFormat == DXGI_FORMAT_R16_UINT ? 2u :
        indexFormat == DXGI_FORMAT_R32_UINT ? 4u : 0u;
    const bool indexShapeValid =
        out.indexed
            ? indexBuffer != nullptr &&
              indexFormatExact &&
              indexElementBytes != 0 &&
              (indexOffset % indexElementBytes) == 0
            : indexBuffer == nullptr &&
              indexFormat == DXGI_FORMAT_UNKNOWN &&
              indexOffset == 0;

    out.inputValid =
        context != nullptr &&
        vertexStride != 0 &&
        indexShapeValid &&
        validate_fixed_function_direct_geometry_readiness_integrity(geometry);
    if (!out.inputValid)
        return out;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    out.contextMatches =
        contextDevice &&
        vertexBuffer.mirror_device() == contextDevice.Get() &&
        (!out.indexed ||
         (indexBuffer &&
          indexBuffer->mirror_device() == contextDevice.Get()));
    if (!out.contextMatches)
        return out;

    const auto currentVertex =
        vertexBuffer.mirror_readiness(contextDevice.Get());
    out.vertexBufferCurrent =
        currentVertex.ready &&
        currentVertex.role == ResourceRole::Vertex &&
        currentVertex.snapshotToken == geometry.vertexBufferSnapshotToken;

    out.indexBufferCurrent = !out.indexed;
    if (out.indexed && indexBuffer) {
        const auto currentIndex =
            indexBuffer->mirror_readiness(contextDevice.Get());
        out.indexBufferCurrent =
            currentIndex.ready &&
            currentIndex.role == ResourceRole::Index &&
            currentIndex.snapshotToken == geometry.indexBufferSnapshotToken;
    }

    out.geometryReady =
        out.vertexBufferCurrent &&
        out.indexBufferCurrent;
    if (!out.geometryReady)
        return out;

    Microsoft::WRL::ComPtr<ID3D11Buffer> observedVertexBuffer;
    UINT observedStride = 0;
    UINT observedVertexOffset = 0;
    context->IAGetVertexBuffers(
        0, 1, observedVertexBuffer.ReleaseAndGetAddressOf(),
        &observedStride, &observedVertexOffset);

    Microsoft::WRL::ComPtr<ID3D11Buffer> observedIndexBuffer;
    DXGI_FORMAT observedIndexFormat = DXGI_FORMAT_UNKNOWN;
    UINT observedIndexOffset = 0;
    context->IAGetIndexBuffer(
        observedIndexBuffer.ReleaseAndGetAddressOf(),
        &observedIndexFormat, &observedIndexOffset);

    D3D11_PRIMITIVE_TOPOLOGY observedTopology =
        D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    context->IAGetPrimitiveTopology(&observedTopology);

    out.vertexBufferBoundExact =
        observedVertexBuffer.Get() == vertexBuffer.mirror_buffer() &&
        observedStride == vertexStride &&
        observedVertexOffset == vertexOffset;
    out.indexBufferBoundExact =
        out.indexed
            ? observedIndexBuffer.Get() == indexBuffer->mirror_buffer() &&
              observedIndexFormat == indexFormat &&
              observedIndexOffset == indexOffset
            : observedIndexBuffer.Get() == nullptr &&
              observedIndexFormat == DXGI_FORMAT_UNKNOWN &&
              observedIndexOffset == 0;
    out.topologyBoundExact = observedTopology == geometry.topology;
    out.ready =
        out.geometryReady &&
        out.contextMatches &&
        out.vertexBufferBoundExact &&
        out.indexBufferBoundExact &&
        out.topologyBoundExact;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.geometrySnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.vertexBufferSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.indexBufferSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(context)));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(
                    observedVertexBuffer.Get())));
        token = mix_readiness_snapshot_token(token, observedStride);
        token = mix_readiness_snapshot_token(token, observedVertexOffset);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(
                    observedIndexBuffer.Get())));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(observedIndexFormat));
        token = mix_readiness_snapshot_token(token, observedIndexOffset);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(observedTopology));
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool bind_fixed_function_geometry_for_observation(
    ID3D11DeviceContext* context,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeManagedBufferShadow* indexBuffer,
    DXGI_FORMAT indexFormat,
    UINT indexOffset) noexcept {
    if (!context ||
        vertexStride == 0 ||
        !validate_fixed_function_direct_geometry_readiness_integrity(geometry))
        return false;

    const bool indexed = geometry.indexBufferRequired;
    const UINT indexElementBytes =
        indexFormat == DXGI_FORMAT_R16_UINT ? 2u :
        indexFormat == DXGI_FORMAT_R32_UINT ? 4u : 0u;
    if (indexed) {
        if (!indexBuffer ||
            indexElementBytes == 0 ||
            (indexOffset % indexElementBytes) != 0)
            return false;
    } else if (indexBuffer ||
               indexFormat != DXGI_FORMAT_UNKNOWN ||
               indexOffset != 0) {
        return false;
    }

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    if (!contextDevice ||
        vertexBuffer.mirror_device() != contextDevice.Get())
        return false;

    const auto currentVertex =
        vertexBuffer.mirror_readiness(contextDevice.Get());
    if (!currentVertex.ready ||
        currentVertex.role != ResourceRole::Vertex ||
        currentVertex.snapshotToken != geometry.vertexBufferSnapshotToken)
        return false;

    if (indexed) {
        if (indexBuffer->mirror_device() != contextDevice.Get())
            return false;
        const auto currentIndex =
            indexBuffer->mirror_readiness(contextDevice.Get());
        if (!currentIndex.ready ||
            currentIndex.role != ResourceRole::Index ||
            currentIndex.snapshotToken != geometry.indexBufferSnapshotToken)
            return false;
    }

    ID3D11Buffer* vertex = vertexBuffer.mirror_buffer();
    context->IASetVertexBuffers(
        0, 1, &vertex, &vertexStride, &vertexOffset);
    if (indexed) {
        context->IASetIndexBuffer(
            indexBuffer->mirror_buffer(), indexFormat, indexOffset);
    } else {
        context->IASetIndexBuffer(nullptr, DXGI_FORMAT_UNKNOWN, 0);
    }
    context->IASetPrimitiveTopology(geometry.topology);

    return observe_fixed_function_geometry_binding(
        context, geometry, vertexBuffer, vertexStride, vertexOffset,
        indexBuffer, indexFormat, indexOffset).ready;
}

bool validate_fixed_function_geometry_binding_snapshot(
    ID3D11DeviceContext* context,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeManagedBufferShadow* indexBuffer,
    DXGI_FORMAT indexFormat,
    UINT indexOffset,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = observe_fixed_function_geometry_binding(
        context, geometry, vertexBuffer, vertexStride, vertexOffset,
        indexBuffer, indexFormat, indexOffset);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionGeometryReadiness
compose_fixed_function_nonindexed_triangle_fan_geometry_readiness(
    const NativeManagedBufferMirrorReadiness& vertexBuffer,
    const NativeTriangleFanIndexBufferReadiness& generatedIndexBuffer,
    UINT primitiveCount,
    UINT baseVertex) noexcept {
    NativeFixedFunctionGeometryReadiness out{};
    const auto expansion = translate_triangle_fan_expansion(primitiveCount);
    out.indexBufferRequired = false;
    out.indexBufferReady = true;
    out.generatedIndexBufferRequired = true;
    out.topology = expansion.topology;
    out.vertexBufferSnapshotToken = vertexBuffer.snapshotToken;
    out.generatedIndexBufferSnapshotToken =
        generatedIndexBuffer.snapshotToken;

    std::uint64_t expectedContentHash = 0;
    if (expansion.exact &&
        expansion.expandedIndexCount != 0 &&
        expansion.topology == D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST) {
        std::uint64_t hash = 0xcbf29ce484222325ull;
        bool exactIndices = true;
        for (UINT expandedIndex = 0;
             expandedIndex < expansion.expandedIndexCount;
             ++expandedIndex) {
            UINT sourceElement = 0;
            if (!triangle_fan_source_element(
                    primitiveCount, expandedIndex, sourceElement) ||
                baseVertex >
                    (std::numeric_limits<UINT>::max)() - sourceElement) {
                exactIndices = false;
                break;
            }
            hash = mix_readiness_snapshot_token(
                hash, baseVertex + sourceElement);
        }
        if (exactIndices)
            expectedContentHash = hash == 0 ? 1 : hash;
    }

    out.inputValid =
        vertexBuffer.inputValid &&
        vertexBuffer.role == ResourceRole::Vertex &&
        expansion.exact &&
        expectedContentHash != 0;
    out.vertexBufferReady =
        vertexBuffer.ready && vertexBuffer.snapshotToken != 0;
    out.generatedIndexBufferReady =
        generatedIndexBuffer.ready &&
        generatedIndexBuffer.snapshotToken != 0;
    out.generatedIndexBufferMatchesDraw =
        out.generatedIndexBufferReady &&
        !generatedIndexBuffer.indexedSource &&
        generatedIndexBuffer.primitiveCount == primitiveCount &&
        generatedIndexBuffer.baseVertex == baseVertex &&
        generatedIndexBuffer.indexCount == expansion.expandedIndexCount &&
        generatedIndexBuffer.contentHash == expectedContentHash;
    out.topologyReady =
        expansion.exact &&
        expansion.topology == D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST;
    out.componentSnapshotsPresent =
        vertexBuffer.snapshotToken != 0 &&
        generatedIndexBuffer.snapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.vertexBufferReady &&
        out.indexBufferReady &&
        out.generatedIndexBufferReady &&
        out.generatedIndexBufferMatchesDraw &&
        out.topologyReady &&
        out.componentSnapshotsPresent;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.vertexBufferSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.generatedIndexBufferSnapshotToken);
        token = mix_readiness_snapshot_token(token, primitiveCount);
        token = mix_readiness_snapshot_token(token, baseVertex);
        token = mix_readiness_snapshot_token(token, expectedContentHash);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.topology));
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_nonindexed_triangle_fan_geometry_snapshot(
    const NativeManagedBufferMirrorReadiness& vertexBuffer,
    const NativeTriangleFanIndexBufferReadiness& generatedIndexBuffer,
    UINT primitiveCount,
    UINT baseVertex,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current =
        compose_fixed_function_nonindexed_triangle_fan_geometry_readiness(
            vertexBuffer, generatedIndexBuffer, primitiveCount, baseVertex);
    return current.ready && current.snapshotToken == snapshotToken;
}

// R143 composes the current managed source-index identity with the generated
// indexed triangle-fan owner. It proves provenance only; no IA binding or Draw*
// is performed here.
NativeFixedFunctionGeometryReadiness
compose_fixed_function_indexed_triangle_fan_geometry_readiness(
    const NativeManagedBufferMirrorReadiness& vertexBuffer,
    const NativeManagedBufferMirrorReadiness& sourceIndexBuffer,
    const NativeTriangleFanIndexBufferReadiness& generatedIndexBuffer,
    UINT primitiveCount,
    D3DFORMAT sourceIndexFormat,
    UINT startIndex,
    UINT sourceIndexCount) noexcept {
    NativeFixedFunctionGeometryReadiness out{};
    const auto expansion = translate_triangle_fan_expansion(primitiveCount);
    const bool sourceFormatExact =
        sourceIndexFormat == D3DFMT_INDEX16 ||
        sourceIndexFormat == D3DFMT_INDEX32;
    const bool sourceRangeExact =
        expansion.exact &&
        startIndex <= sourceIndexCount &&
        expansion.sourceElementCount <= sourceIndexCount - startIndex;

    out.indexBufferRequired = true;
    out.generatedIndexBufferRequired = true;
    out.topology = expansion.topology;
    out.vertexBufferSnapshotToken = vertexBuffer.snapshotToken;
    out.indexBufferSnapshotToken = sourceIndexBuffer.snapshotToken;
    out.generatedIndexBufferSnapshotToken =
        generatedIndexBuffer.snapshotToken;

    out.inputValid =
        vertexBuffer.inputValid &&
        vertexBuffer.role == ResourceRole::Vertex &&
        sourceIndexBuffer.inputValid &&
        sourceIndexBuffer.role == ResourceRole::Index &&
        expansion.exact &&
        expansion.expandedIndexCount != 0 &&
        sourceFormatExact &&
        sourceRangeExact;
    out.vertexBufferReady =
        vertexBuffer.ready && vertexBuffer.snapshotToken != 0;
    out.indexBufferReady =
        sourceIndexBuffer.ready && sourceIndexBuffer.snapshotToken != 0;
    out.generatedIndexBufferReady =
        generatedIndexBuffer.ready &&
        generatedIndexBuffer.sourceProvenanceExact &&
        generatedIndexBuffer.indexedSource &&
        generatedIndexBuffer.snapshotToken != 0;
    out.generatedIndexBufferMatchesDraw =
        out.generatedIndexBufferReady &&
        generatedIndexBuffer.indexCount == expansion.expandedIndexCount &&
        generatedIndexBuffer.primitiveCount == primitiveCount &&
        generatedIndexBuffer.sourceIndexFormat == sourceIndexFormat &&
        generatedIndexBuffer.sourceStartIndex == startIndex &&
        generatedIndexBuffer.sourceIndexCount == sourceIndexCount &&
        generatedIndexBuffer.sourceIndexSnapshotToken ==
            sourceIndexBuffer.snapshotToken &&
        generatedIndexBuffer.contentHash != 0;
    out.topologyReady =
        expansion.exact &&
        expansion.topology == D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST;
    out.componentSnapshotsPresent =
        vertexBuffer.snapshotToken != 0 &&
        sourceIndexBuffer.snapshotToken != 0 &&
        generatedIndexBuffer.snapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.vertexBufferReady &&
        out.indexBufferReady &&
        out.generatedIndexBufferReady &&
        out.generatedIndexBufferMatchesDraw &&
        out.topologyReady &&
        out.componentSnapshotsPresent;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.vertexBufferSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.indexBufferSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.generatedIndexBufferSnapshotToken);
        token = mix_readiness_snapshot_token(token, primitiveCount);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(sourceIndexFormat));
        token = mix_readiness_snapshot_token(token, startIndex);
        token = mix_readiness_snapshot_token(token, sourceIndexCount);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.topology));
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_indexed_triangle_fan_geometry_snapshot(
    const NativeManagedBufferMirrorReadiness& vertexBuffer,
    const NativeManagedBufferMirrorReadiness& sourceIndexBuffer,
    const NativeTriangleFanIndexBufferReadiness& generatedIndexBuffer,
    UINT primitiveCount,
    D3DFORMAT sourceIndexFormat,
    UINT startIndex,
    UINT sourceIndexCount,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current =
        compose_fixed_function_indexed_triangle_fan_geometry_readiness(
            vertexBuffer, sourceIndexBuffer, generatedIndexBuffer,
            primitiveCount, sourceIndexFormat, startIndex, sourceIndexCount);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionOutputStateReadiness
compose_fixed_function_output_state_readiness(
    const OutRunVR::DrawState::RenderStateSnapshot& source,
    const NativeSurfacePairReadiness& surfacePair) noexcept {
    NativeFixedFunctionOutputStateReadiness out{};
    out.sampleMask = source.multiSampleMask;

    if (!source.outputStateComplete ||
        !surfacePair.inputValid ||
        !surfacePair.ready ||
        surfacePair.snapshotToken == 0 ||
        surfacePair.width == 0 ||
        surfacePair.height == 0)
        return out;

    out.inputValid = true;

    const std::uint64_t viewportRight =
        static_cast<std::uint64_t>(source.viewport.X) +
        static_cast<std::uint64_t>(source.viewport.Width);
    const std::uint64_t viewportBottom =
        static_cast<std::uint64_t>(source.viewport.Y) +
        static_cast<std::uint64_t>(source.viewport.Height);
    out.viewportExact =
        source.viewport.Width != 0 &&
        source.viewport.Height != 0 &&
        viewportRight <= surfacePair.width &&
        viewportBottom <= surfacePair.height &&
        source.viewport.MinZ >= 0.0f &&
        source.viewport.MinZ <= source.viewport.MaxZ &&
        source.viewport.MaxZ <= 1.0f;

    out.viewport.TopLeftX = static_cast<float>(source.viewport.X);
    out.viewport.TopLeftY = static_cast<float>(source.viewport.Y);
    out.viewport.Width = static_cast<float>(source.viewport.Width);
    out.viewport.Height = static_cast<float>(source.viewport.Height);
    out.viewport.MinDepth = source.viewport.MinZ;
    out.viewport.MaxDepth = source.viewport.MaxZ;

    out.scissorRect.left = source.scissorRect.left;
    out.scissorRect.top = source.scissorRect.top;
    out.scissorRect.right = source.scissorRect.right;
    out.scissorRect.bottom = source.scissorRect.bottom;
    const bool scissorBoundsExact =
        source.scissorRect.left >= 0 &&
        source.scissorRect.top >= 0 &&
        source.scissorRect.right >= source.scissorRect.left &&
        source.scissorRect.bottom >= source.scissorRect.top &&
        static_cast<std::uint64_t>(source.scissorRect.right) <=
            surfacePair.width &&
        static_cast<std::uint64_t>(source.scissorRect.bottom) <=
            surfacePair.height;
    out.scissorExact =
        source.scissorTestEnable == FALSE || scissorBoundsExact;

    constexpr float channelScale = 1.0f / 255.0f;
    out.blendFactor[0] =
        static_cast<float>((source.blendFactor >> 16) & 0xffu) *
        channelScale;
    out.blendFactor[1] =
        static_cast<float>((source.blendFactor >> 8) & 0xffu) *
        channelScale;
    out.blendFactor[2] =
        static_cast<float>(source.blendFactor & 0xffu) *
        channelScale;
    out.blendFactor[3] =
        static_cast<float>((source.blendFactor >> 24) & 0xffu) *
        channelScale;
    out.omDynamicExact = true;

    out.ready =
        out.inputValid &&
        out.viewportExact &&
        out.scissorExact &&
        out.omDynamicExact;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, surfacePair.snapshotToken);
        token = mix_readiness_snapshot_token(token, source.viewport.X);
        token = mix_readiness_snapshot_token(token, source.viewport.Y);
        token = mix_readiness_snapshot_token(token, source.viewport.Width);
        token = mix_readiness_snapshot_token(token, source.viewport.Height);
        std::uint32_t minDepthBits = 0;
        std::uint32_t maxDepthBits = 0;
        std::memcpy(
            &minDepthBits, &source.viewport.MinZ, sizeof(minDepthBits));
        std::memcpy(
            &maxDepthBits, &source.viewport.MaxZ, sizeof(maxDepthBits));
        token = mix_readiness_snapshot_token(token, minDepthBits);
        token = mix_readiness_snapshot_token(token, maxDepthBits);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(source.scissorRect.left));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(source.scissorRect.top));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(source.scissorRect.right));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(source.scissorRect.bottom));
        token = mix_readiness_snapshot_token(
            token, source.scissorTestEnable != FALSE ? 1u : 0u);
        token = mix_readiness_snapshot_token(token, source.blendFactor);
        token = mix_readiness_snapshot_token(token, source.multiSampleMask);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_output_state_snapshot(
    const OutRunVR::DrawState::RenderStateSnapshot& source,
    const NativeSurfacePairReadiness& surfacePair,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current =
        compose_fixed_function_output_state_readiness(source, surfacePair);
    return current.ready && current.snapshotToken == snapshotToken;
}

bool NativeFixedFunctionOutputStateBinding::initialize(
    ID3D11Device* device,
    const NativeFixedFunctionRenderStateBundle& renderStateBundle,
    const PipelineTranslation& translation,
    std::uint64_t renderStateSnapshotToken,
    const OutRunVR::DrawState::RenderStateSnapshot& source,
    const NativeSurfacePairReadiness& surfacePair,
    std::uint64_t outputStateSnapshotToken) noexcept {

    shutdown();
    if (!device ||
        renderStateSnapshotToken == 0 ||
        outputStateSnapshotToken == 0 ||
        !renderStateBundle.validate_translation_snapshot(
            device, translation, renderStateSnapshotToken) ||
        !validate_fixed_function_output_state_snapshot(
            source, surfacePair, outputStateSnapshotToken) ||
        !renderStateBundle.ready() ||
        renderStateBundle.device() != device ||
        !renderStateBundle.blend_state() ||
        !renderStateBundle.depth_stencil_state() ||
        !renderStateBundle.rasterizer_state())
        return false;

    const bool sourceScissorEnabled = source.scissorTestEnable != FALSE;
    if (translation.rasterizer.ScissorEnable != sourceScissorEnabled)
        return false;

    const auto renderState =
        renderStateBundle.translation_readiness(device, translation);
    const auto outputState =
        compose_fixed_function_output_state_readiness(source, surfacePair);
    if (!renderState.ready ||
        renderState.snapshotToken != renderStateSnapshotToken ||
        !outputState.ready ||
        outputState.snapshotToken != outputStateSnapshotToken)
        return false;

    D3D11_RECT sealedScissor = outputState.scissorRect;
    if (!sourceScissorEnabled) {
        if (surfacePair.width >
                static_cast<UINT>((std::numeric_limits<LONG>::max)()) ||
            surfacePair.height >
                static_cast<UINT>((std::numeric_limits<LONG>::max)()))
            return false;
        sealedScissor.left = 0;
        sealedScissor.top = 0;
        sealedScissor.right = static_cast<LONG>(surfacePair.width);
        sealedScissor.bottom = static_cast<LONG>(surfacePair.height);
    }

    device_ = device;
    blend_state_ = renderStateBundle.blend_state();
    depth_stencil_state_ = renderStateBundle.depth_stencil_state();
    rasterizer_state_ = renderStateBundle.rasterizer_state();
    viewport_ = outputState.viewport;
    scissor_rect_ = sealedScissor;
    blend_factor_ = outputState.blendFactor;
    sample_mask_ = outputState.sampleMask;
    stencil_ref_ = renderStateBundle.stencil_ref();
    render_state_snapshot_token_ = renderStateSnapshotToken;
    surface_pair_snapshot_token_ = surfacePair.snapshotToken;
    output_state_snapshot_token_ = outputStateSnapshotToken;

    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(
        token, render_state_snapshot_token_);
    token = mix_readiness_snapshot_token(
        token, surface_pair_snapshot_token_);
    token = mix_readiness_snapshot_token(
        token, output_state_snapshot_token_);
    token = mix_readiness_snapshot_token(
        token, static_cast<std::uint64_t>(
            reinterpret_cast<std::uintptr_t>(device_.Get())));
    token = mix_readiness_snapshot_token(
        token, static_cast<std::uint64_t>(
            reinterpret_cast<std::uintptr_t>(blend_state_.Get())));
    token = mix_readiness_snapshot_token(
        token, static_cast<std::uint64_t>(
            reinterpret_cast<std::uintptr_t>(depth_stencil_state_.Get())));
    token = mix_readiness_snapshot_token(
        token, static_cast<std::uint64_t>(
            reinterpret_cast<std::uintptr_t>(rasterizer_state_.Get())));
    snapshot_token_ = token == 0 ? 1 : token;
    return ready();
}

void NativeFixedFunctionOutputStateBinding::shutdown() noexcept {
    rasterizer_state_.Reset();
    depth_stencil_state_.Reset();
    blend_state_.Reset();
    device_.Reset();
    viewport_ = {};
    scissor_rect_ = {};
    blend_factor_ = {1.0f, 1.0f, 1.0f, 1.0f};
    sample_mask_ = 0xFFFFFFFFu;
    stencil_ref_ = 0;
    render_state_snapshot_token_ = 0;
    surface_pair_snapshot_token_ = 0;
    output_state_snapshot_token_ = 0;
    snapshot_token_ = 0;
}

bool NativeFixedFunctionOutputStateBinding::apply(
    ID3D11DeviceContext* context) const noexcept {

    // R155: only the live immediate context may own a draw-state receipt.
    // Deferred command recording on the same device is not live RS/OM state.
    if (!ready() || !context ||
        context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    if (!contextDevice || contextDevice.Get() != device_.Get())
        return false;

    context->RSSetState(rasterizer_state_.Get());
    context->RSSetViewports(1, &viewport_);
    context->RSSetScissorRects(1, &scissor_rect_);
    context->OMSetBlendState(
        blend_state_.Get(), blend_factor_.data(), sample_mask_);
    context->OMSetDepthStencilState(
        depth_stencil_state_.Get(), stencil_ref_);
    return true;
}

NativeFixedFunctionOutputBindingReadiness
NativeFixedFunctionOutputStateBinding::binding_readiness(
    ID3D11DeviceContext* context) const noexcept {
    NativeFixedFunctionOutputBindingReadiness out{};
    out.outputBindingSnapshotToken = snapshot_token_;
    // R155: recorded RS/OM commands on a deferred context are not live.
    out.inputValid = context != nullptr &&
        context->GetType() == D3D11_DEVICE_CONTEXT_IMMEDIATE &&
        snapshot_token_ != 0;
    out.ownerReady = ready();
    if (!out.inputValid || !out.ownerReady)
        return out;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    out.contextMatches =
        contextDevice && contextDevice.Get() == device_.Get();
    if (!out.contextMatches)
        return out;

    Microsoft::WRL::ComPtr<ID3D11RasterizerState> observedRasterizer;
    Microsoft::WRL::ComPtr<ID3D11BlendState> observedBlend;
    Microsoft::WRL::ComPtr<ID3D11DepthStencilState> observedDepthStencil;
    D3D11_VIEWPORT observedViewport{};
    D3D11_RECT observedScissor{};
    FLOAT observedBlendFactor[4]{};
    UINT observedSampleMask = 0;
    UINT observedStencilRef = 0;
    UINT viewportCount = 1;
    UINT scissorCount = 1;

    context->RSGetState(observedRasterizer.ReleaseAndGetAddressOf());
    context->RSGetViewports(&viewportCount, &observedViewport);
    context->RSGetScissorRects(&scissorCount, &observedScissor);
    context->OMGetBlendState(
        observedBlend.ReleaseAndGetAddressOf(),
        observedBlendFactor, &observedSampleMask);
    context->OMGetDepthStencilState(
        observedDepthStencil.ReleaseAndGetAddressOf(),
        &observedStencilRef);

    out.rasterizerMatches =
        observedRasterizer.Get() == rasterizer_state_.Get();
    out.viewportMatches =
        viewportCount == 1 &&
        observedViewport.TopLeftX == viewport_.TopLeftX &&
        observedViewport.TopLeftY == viewport_.TopLeftY &&
        observedViewport.Width == viewport_.Width &&
        observedViewport.Height == viewport_.Height &&
        observedViewport.MinDepth == viewport_.MinDepth &&
        observedViewport.MaxDepth == viewport_.MaxDepth;
    out.scissorMatches =
        scissorCount == 1 &&
        observedScissor.left == scissor_rect_.left &&
        observedScissor.top == scissor_rect_.top &&
        observedScissor.right == scissor_rect_.right &&
        observedScissor.bottom == scissor_rect_.bottom;
    out.blendStateMatches =
        observedBlend.Get() == blend_state_.Get();
    out.blendFactorMatches =
        observedBlendFactor[0] == blend_factor_[0] &&
        observedBlendFactor[1] == blend_factor_[1] &&
        observedBlendFactor[2] == blend_factor_[2] &&
        observedBlendFactor[3] == blend_factor_[3];
    out.sampleMaskMatches = observedSampleMask == sample_mask_;
    out.depthStencilMatches =
        observedDepthStencil.Get() == depth_stencil_state_.Get();
    out.stencilRefMatches = observedStencilRef == stencil_ref_;
    out.ready =
        out.rasterizerMatches &&
        out.viewportMatches &&
        out.scissorMatches &&
        out.blendStateMatches &&
        out.blendFactorMatches &&
        out.sampleMaskMatches &&
        out.depthStencilMatches &&
        out.stencilRefMatches;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.outputBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(context)));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(observedRasterizer.Get())));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(observedBlend.Get())));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(observedDepthStencil.Get())));
        token = mix_readiness_snapshot_token(token, observedSampleMask);
        token = mix_readiness_snapshot_token(token, observedStencilRef);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeFixedFunctionOutputStateBinding::validate_binding_snapshot(
    ID3D11DeviceContext* context,
    std::uint64_t bindingSnapshotToken) const noexcept {
    if (bindingSnapshotToken == 0)
        return false;
    const auto current = binding_readiness(context);
    return current.ready && current.snapshotToken == bindingSnapshotToken;
}

NativeFixedFunctionDrawReadiness
compose_fixed_function_draw_readiness(
    const NativeFixedFunctionActivationReadiness& activation,
    const NativeFixedFunctionRenderStateReadiness& renderState,
    const NativeSurfacePairReadiness& surfacePair,
    const NativeFixedFunctionOutputStateReadiness& outputState,
    const NativeFixedFunctionOutputStateBinding& outputBinding,
    const NativeFixedFunctionGeometryReadiness& geometry) noexcept {
    NativeFixedFunctionDrawReadiness out{};
    out.activationSnapshotToken = activation.snapshotToken;
    out.pipelineSnapshotToken = activation.pipelineSnapshotToken;
    out.renderStateSnapshotToken = renderState.snapshotToken;
    out.surfacePairSnapshotToken = surfacePair.snapshotToken;
    out.outputStateSnapshotToken = outputState.snapshotToken;
    out.outputBindingSnapshotToken = outputBinding.snapshot_token();
    out.geometrySnapshotToken = geometry.snapshotToken;
    out.requiredTextureMask = activation.requiredTextureMask;
    out.inputValid =
        activation.inputValid &&
        renderState.inputValid &&
        surfacePair.inputValid &&
        outputState.inputValid &&
        geometry.inputValid;
    out.activationReady =
        activation.ready && activation.snapshotToken != 0;
    out.renderStateReady =
        renderState.ready && renderState.snapshotToken != 0;
    out.surfacePairReady =
        surfacePair.ready && surfacePair.snapshotToken != 0;
    out.outputStateReady =
        outputState.ready && outputState.snapshotToken != 0;
    out.outputBindingReady =
        outputBinding.ready() &&
        outputBinding.render_state_snapshot_token() == renderState.snapshotToken &&
        outputBinding.surface_pair_snapshot_token() == surfacePair.snapshotToken &&
        outputBinding.output_state_snapshot_token() == outputState.snapshotToken &&
        outputBinding.snapshot_token() != 0;
    out.geometryReady =
        geometry.ready && geometry.snapshotToken != 0;
    out.componentSnapshotsPresent =
        activation.snapshotToken != 0 &&
        renderState.snapshotToken != 0 &&
        surfacePair.snapshotToken != 0 &&
        outputState.snapshotToken != 0 &&
        outputBinding.snapshot_token() != 0 &&
        geometry.snapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.activationReady &&
        out.renderStateReady &&
        out.surfacePairReady &&
        out.outputStateReady &&
        out.outputBindingReady &&
        out.geometryReady &&
        out.componentSnapshotsPresent;
    if (out.ready) {
        std::uint64_t drawToken = 0xcbf29ce484222325ull;
        drawToken = mix_readiness_snapshot_token(
            drawToken, out.activationSnapshotToken);
        drawToken = mix_readiness_snapshot_token(
            drawToken, out.pipelineSnapshotToken);
        drawToken = mix_readiness_snapshot_token(
            drawToken, out.renderStateSnapshotToken);
        drawToken = mix_readiness_snapshot_token(
            drawToken, out.surfacePairSnapshotToken);
        drawToken = mix_readiness_snapshot_token(
            drawToken, out.outputStateSnapshotToken);
        drawToken = mix_readiness_snapshot_token(
            drawToken, out.outputBindingSnapshotToken);
        drawToken = mix_readiness_snapshot_token(
            drawToken, out.geometrySnapshotToken);
        drawToken = mix_readiness_snapshot_token(
            drawToken, out.requiredTextureMask);
        out.snapshotToken = drawToken == 0 ? 1 : drawToken;
    }
    return out;
}

bool validate_fixed_function_draw_readiness_integrity(
    const NativeFixedFunctionDrawReadiness& draw) noexcept {
    if (!draw.inputValid ||
        !draw.activationReady ||
        !draw.renderStateReady ||
        !draw.surfacePairReady ||
        !draw.outputStateReady ||
        !draw.outputBindingReady ||
        !draw.geometryReady ||
        !draw.componentSnapshotsPresent ||
        !draw.ready ||
        draw.activationSnapshotToken == 0 ||
        draw.pipelineSnapshotToken == 0 ||
        draw.renderStateSnapshotToken == 0 ||
        draw.surfacePairSnapshotToken == 0 ||
        draw.outputStateSnapshotToken == 0 ||
        draw.outputBindingSnapshotToken == 0 ||
        draw.geometrySnapshotToken == 0 ||
        draw.snapshotToken == 0)
        return false;

    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(token, draw.activationSnapshotToken);
    token = mix_readiness_snapshot_token(token, draw.pipelineSnapshotToken);
    token = mix_readiness_snapshot_token(token, draw.renderStateSnapshotToken);
    token = mix_readiness_snapshot_token(token, draw.surfacePairSnapshotToken);
    token = mix_readiness_snapshot_token(token, draw.outputStateSnapshotToken);
    token = mix_readiness_snapshot_token(token, draw.outputBindingSnapshotToken);
    token = mix_readiness_snapshot_token(token, draw.geometrySnapshotToken);
    token = mix_readiness_snapshot_token(token, draw.requiredTextureMask);
    token = token == 0 ? 1 : token;
    return token == draw.snapshotToken;
}

bool validate_fixed_function_draw_snapshot(
    const NativeFixedFunctionActivationReadiness& activation,
    const NativeFixedFunctionRenderStateReadiness& renderState,
    const NativeSurfacePairReadiness& surfacePair,
    const NativeFixedFunctionOutputStateReadiness& outputState,
    const NativeFixedFunctionOutputStateBinding& outputBinding,
    const NativeFixedFunctionGeometryReadiness& geometry,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = compose_fixed_function_draw_readiness(
        activation, renderState, surfacePair, outputState, outputBinding, geometry);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionTexturedDrawReadiness
compose_fixed_function_textured_draw_readiness(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    UINT slot,
    const NativeFixedFunctionSamplerState& sampler,
    const NativeFixedFunctionTextureView& texture) noexcept {
    NativeFixedFunctionTexturedDrawReadiness out{};
    const auto textureStage = observe_fixed_function_texture_stage_binding(
        context, slot, sampler, texture);
    out.drawSnapshotToken = draw.snapshotToken;
    out.textureStageSnapshotToken = textureStage.snapshotToken;
    out.requiredTextureMask = draw.requiredTextureMask;
    out.observedTextureMask =
        textureStage.slot < 32u ? (1u << textureStage.slot) : 0u;
    // R133 is deliberately single-stage: one observed PS binding cannot prove
    // a multi-stage activation mask. Require the exact activation stage bit so
    // a valid sampler/SRV bound to the wrong slot cannot make the draw ready.
    out.textureMaskMatches =
        textureStage.slotValid &&
        out.requiredTextureMask != 0 &&
        out.requiredTextureMask == out.observedTextureMask;
    out.inputValid =
        draw.inputValid && textureStage.inputValid && out.textureMaskMatches;
    out.drawReady =
        validate_fixed_function_draw_readiness_integrity(draw);
    out.textureStageReady =
        textureStage.ready && textureStage.snapshotToken != 0;
    out.componentSnapshotsPresent =
        draw.snapshotToken != 0 && textureStage.snapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.drawReady &&
        out.textureStageReady &&
        out.textureMaskMatches &&
        out.componentSnapshotsPresent;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(token, out.drawSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.textureStageSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.requiredTextureMask);
        token = mix_readiness_snapshot_token(
            token, out.observedTextureMask);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_textured_draw_snapshot(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    UINT slot,
    const NativeFixedFunctionSamplerState& sampler,
    const NativeFixedFunctionTextureView& texture,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = compose_fixed_function_textured_draw_readiness(
        draw, context, slot, sampler, texture);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionTexturedDrawReadiness
compose_fixed_function_multistage_textured_draw_readiness(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures) noexcept {
    NativeFixedFunctionTexturedDrawReadiness out{};
    // Reobserve every required PS stage at composition time. A previously
    // captured aggregate is useful diagnostic evidence, but cannot authorize a
    // later draw candidate after the live context has changed.
    const auto textureBindings = observe_fixed_function_texture_binding_set(
        context, draw.requiredTextureMask, samplers, textures);
    out.drawSnapshotToken = draw.snapshotToken;
    out.textureStageSnapshotToken = textureBindings.snapshotToken;
    out.requiredTextureMask = draw.requiredTextureMask;
    out.observedTextureMask = textureBindings.observedTextureMask;
    out.textureMaskMatches =
        textureBindings.requiredMaskValid &&
        out.requiredTextureMask != 0 &&
        textureBindings.requiredTextureMask == out.requiredTextureMask &&
        out.observedTextureMask == out.requiredTextureMask;
    const bool drawSnapshotValid =
        validate_fixed_function_draw_readiness_integrity(draw);
    const bool textureBindingSnapshotValid =
        validate_fixed_function_texture_binding_set_readiness_integrity(
            textureBindings);
    out.inputValid =
        drawSnapshotValid &&
        textureBindingSnapshotValid &&
        out.textureMaskMatches;
    out.drawReady = drawSnapshotValid;
    out.textureStageReady = textureBindingSnapshotValid;
    out.componentSnapshotsPresent =
        draw.snapshotToken != 0 && textureBindings.snapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.drawReady &&
        out.textureStageReady &&
        out.textureMaskMatches &&
        out.componentSnapshotsPresent;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(token, out.drawSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.textureStageSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.requiredTextureMask);
        token = mix_readiness_snapshot_token(
            token, out.observedTextureMask);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_multistage_textured_draw_snapshot(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current =
        compose_fixed_function_multistage_textured_draw_readiness(
            draw, context, samplers, textures);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionBoundDrawReadiness
compose_fixed_function_bound_draw_readiness(
    const NativeFixedFunctionDrawReadiness& draw,
    const NativeFixedFunctionTexturedDrawReadiness& texturedDraw,
    const NativeFixedFunctionPipelineBindingReadiness& pipelineBinding,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding) noexcept {
    NativeFixedFunctionBoundDrawReadiness out{};
    out.texturedDrawSnapshotToken = texturedDraw.snapshotToken;
    out.pipelineBindingSnapshotToken = pipelineBinding.snapshotToken;
    const auto outputBinding =
        outputStateBinding.binding_readiness(context);
    out.outputBindingSnapshotToken = outputBinding.snapshotToken;
    const bool drawSnapshotValid =
        validate_fixed_function_draw_readiness_integrity(draw);
    out.inputValid =
        drawSnapshotValid &&
        texturedDraw.inputValid &&
        pipelineBinding.inputValid &&
        outputBinding.inputValid;
    out.texturedDrawReady =
        texturedDraw.ready && texturedDraw.snapshotToken != 0 &&
        texturedDraw.drawSnapshotToken == draw.snapshotToken;
    out.pipelineBindingReady =
        pipelineBinding.ready && pipelineBinding.snapshotToken != 0;
    out.pipelineBindingMatchesDraw =
        draw.pipelineSnapshotToken != 0 &&
        pipelineBinding.pipelineSnapshotToken == draw.pipelineSnapshotToken;
    out.outputBindingReady =
        outputBinding.ready && outputBinding.snapshotToken != 0;
    out.outputBindingMatchesDraw =
        draw.outputBindingSnapshotToken != 0 &&
        outputBinding.outputBindingSnapshotToken ==
            draw.outputBindingSnapshotToken;
    out.componentSnapshotsPresent =
        draw.snapshotToken != 0 &&
        texturedDraw.snapshotToken != 0 &&
        pipelineBinding.snapshotToken != 0 &&
        outputBinding.snapshotToken != 0;
    out.ready =
        draw.ready &&
        out.inputValid &&
        out.texturedDrawReady &&
        out.pipelineBindingReady &&
        out.pipelineBindingMatchesDraw &&
        out.outputBindingReady &&
        out.outputBindingMatchesDraw &&
        out.componentSnapshotsPresent;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.texturedDrawSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.pipelineBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.outputBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, draw.pipelineSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, draw.outputBindingSnapshotToken);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_bound_draw_snapshot(
    const NativeFixedFunctionDrawReadiness& draw,
    const NativeFixedFunctionTexturedDrawReadiness& texturedDraw,
    const NativeFixedFunctionPipelineBindingReadiness& pipelineBinding,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = compose_fixed_function_bound_draw_readiness(
        draw, texturedDraw, pipelineBinding, context, outputStateBinding);
    return current.ready && current.snapshotToken == snapshotToken;
}


NativeFixedFunctionBoundDrawReadiness
compose_fixed_function_same_context_bound_draw_readiness(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    const NativeFixedFunctionPipelineBundle& pipelineBundle,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures) noexcept {
    if (!context || !validate_fixed_function_draw_readiness_integrity(draw))
        return {};

    // All three live observations are derived here from the same context.
    // Callers cannot splice a textured/pipeline snapshot captured elsewhere.
    const auto texturedDraw =
        compose_fixed_function_multistage_textured_draw_readiness(
            draw, context, samplers, textures);
    const auto pipelineBinding = pipelineBundle.binding_readiness(
        context, layout, vertexPrototype, pixelPrototype,
        draw.pipelineSnapshotToken);
    return compose_fixed_function_bound_draw_readiness(
        draw, texturedDraw, pipelineBinding, context, outputStateBinding);
}

bool validate_fixed_function_same_context_bound_draw_snapshot(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    const NativeFixedFunctionPipelineBundle& pipelineBundle,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = compose_fixed_function_same_context_bound_draw_readiness(
        draw, context, outputStateBinding, pipelineBundle,
        layout, vertexPrototype, pixelPrototype, samplers, textures);
    return current.ready && current.snapshotToken == snapshotToken;
}


NativeFixedFunctionCompleteBoundDrawReadiness
compose_fixed_function_complete_bound_draw_readiness(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    const NativeFixedFunctionPipelineBundle& pipelineBundle,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeManagedBufferShadow* indexBuffer,
    DXGI_FORMAT indexFormat,
    UINT indexOffset) noexcept {
    NativeFixedFunctionCompleteBoundDrawReadiness out{};
    const auto boundDraw =
        compose_fixed_function_same_context_bound_draw_readiness(
            draw, context, outputStateBinding, pipelineBundle,
            layout, vertexPrototype, pixelPrototype, samplers, textures);
    const auto geometryBinding = observe_fixed_function_geometry_binding(
        context, geometry, vertexBuffer, vertexStride, vertexOffset,
        indexBuffer, indexFormat, indexOffset);

    out.sameContextBoundDrawSnapshotToken = boundDraw.snapshotToken;
    out.geometryBindingSnapshotToken = geometryBinding.snapshotToken;
    out.inputValid =
        boundDraw.inputValid &&
        geometryBinding.inputValid &&
        validate_fixed_function_draw_readiness_integrity(draw);
    out.sameContextBoundDrawReady =
        boundDraw.ready && boundDraw.snapshotToken != 0;
    out.geometryBindingReady =
        geometryBinding.ready && geometryBinding.snapshotToken != 0;
    out.geometryBindingMatchesDraw =
        draw.geometrySnapshotToken != 0 &&
        geometry.snapshotToken == draw.geometrySnapshotToken &&
        geometryBinding.geometrySnapshotToken == draw.geometrySnapshotToken;
    out.componentSnapshotsPresent =
        boundDraw.snapshotToken != 0 &&
        geometryBinding.snapshotToken != 0 &&
        draw.geometrySnapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.sameContextBoundDrawReady &&
        out.geometryBindingReady &&
        out.geometryBindingMatchesDraw &&
        out.componentSnapshotsPresent;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.sameContextBoundDrawSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.geometryBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, draw.geometrySnapshotToken);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_complete_bound_draw_snapshot(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    const NativeFixedFunctionPipelineBundle& pipelineBundle,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeManagedBufferShadow* indexBuffer,
    DXGI_FORMAT indexFormat,
    UINT indexOffset,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = compose_fixed_function_complete_bound_draw_readiness(
        draw, context, outputStateBinding, pipelineBundle,
        layout, vertexPrototype, pixelPrototype, samplers, textures,
        geometry, vertexBuffer, vertexStride, vertexOffset,
        indexBuffer, indexFormat, indexOffset);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionCompleteFanBoundDrawReadiness
compose_fixed_function_complete_nonindexed_triangle_fan_bound_draw_readiness(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    const NativeFixedFunctionPipelineBundle& pipelineBundle,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeTriangleFanIndexBuffer& generatedIndexBuffer,
    UINT primitiveCount,
    UINT baseVertex) noexcept {
    NativeFixedFunctionCompleteFanBoundDrawReadiness out{};
    const auto boundDraw =
        compose_fixed_function_same_context_bound_draw_readiness(
            draw, context, outputStateBinding, pipelineBundle,
            layout, vertexPrototype, pixelPrototype, samplers, textures);
    out.sameContextBoundDrawSnapshotToken = boundDraw.snapshotToken;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    if (context)
        context->GetDevice(contextDevice.ReleaseAndGetAddressOf());

    const auto currentVertex =
        vertexBuffer.mirror_readiness(contextDevice.Get());
    const auto currentFan =
        generatedIndexBuffer.readiness(contextDevice.Get());
    const auto currentGeometry =
        compose_fixed_function_nonindexed_triangle_fan_geometry_readiness(
            currentVertex, currentFan, primitiveCount, baseVertex);
    const auto fanBinding =
        generatedIndexBuffer.binding_readiness(context);

    out.geometrySnapshotToken = currentGeometry.snapshotToken;
    out.vertexBufferSnapshotToken = currentVertex.snapshotToken;
    out.generatedIndexBindingSnapshotToken = fanBinding.snapshotToken;
    out.inputValid =
        context != nullptr &&
        contextDevice.Get() != nullptr &&
        vertexStride != 0 &&
        boundDraw.inputValid &&
        currentGeometry.inputValid &&
        fanBinding.inputValid;
    out.sameContextBoundDrawReady =
        boundDraw.ready && boundDraw.snapshotToken != 0;
    out.geometryReady =
        currentGeometry.ready && currentGeometry.snapshotToken != 0;
    out.geometryMatchesDraw =
        draw.geometrySnapshotToken != 0 &&
        currentGeometry.snapshotToken == draw.geometrySnapshotToken;

    Microsoft::WRL::ComPtr<ID3D11Buffer> observedVertexBuffer;
    UINT observedStride = 0;
    UINT observedVertexOffset = 0;
    if (context) {
        context->IAGetVertexBuffers(
            0, 1, observedVertexBuffer.ReleaseAndGetAddressOf(),
            &observedStride, &observedVertexOffset);
    }
    out.vertexBufferBoundExact =
        contextDevice.Get() != nullptr &&
        vertexBuffer.mirror_device() == contextDevice.Get() &&
        currentVertex.ready &&
        currentVertex.snapshotToken ==
            currentGeometry.vertexBufferSnapshotToken &&
        observedVertexBuffer.Get() == vertexBuffer.mirror_buffer() &&
        observedStride == vertexStride &&
        observedVertexOffset == vertexOffset;
    out.generatedIndexBindingReady =
        fanBinding.ready && fanBinding.snapshotToken != 0;
    out.generatedIndexMatchesGeometry =
        currentFan.ready &&
        currentFan.snapshotToken != 0 &&
        currentGeometry.generatedIndexBufferRequired &&
        currentGeometry.generatedIndexBufferSnapshotToken ==
            currentFan.snapshotToken &&
        fanBinding.ownerSnapshotToken == currentFan.snapshotToken;
    out.componentSnapshotsPresent =
        boundDraw.snapshotToken != 0 &&
        currentGeometry.snapshotToken != 0 &&
        currentVertex.snapshotToken != 0 &&
        fanBinding.snapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.sameContextBoundDrawReady &&
        out.geometryReady &&
        out.geometryMatchesDraw &&
        out.vertexBufferBoundExact &&
        out.generatedIndexBindingReady &&
        out.generatedIndexMatchesGeometry &&
        out.componentSnapshotsPresent;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.sameContextBoundDrawSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.geometrySnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.vertexBufferSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.generatedIndexBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(
                    observedVertexBuffer.Get())));
        token = mix_readiness_snapshot_token(token, observedStride);
        token = mix_readiness_snapshot_token(token, observedVertexOffset);
        token = mix_readiness_snapshot_token(token, primitiveCount);
        token = mix_readiness_snapshot_token(token, baseVertex);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool
validate_fixed_function_complete_nonindexed_triangle_fan_bound_draw_snapshot(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    const NativeFixedFunctionPipelineBundle& pipelineBundle,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeTriangleFanIndexBuffer& generatedIndexBuffer,
    UINT primitiveCount,
    UINT baseVertex,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current =
        compose_fixed_function_complete_nonindexed_triangle_fan_bound_draw_readiness(
            draw, context, outputStateBinding, pipelineBundle,
            layout, vertexPrototype, pixelPrototype, samplers, textures,
            vertexBuffer, vertexStride, vertexOffset,
            generatedIndexBuffer, primitiveCount, baseVertex);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionCompleteIndexedFanBoundDrawReadiness
compose_fixed_function_complete_indexed_triangle_fan_bound_draw_readiness(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    const NativeFixedFunctionPipelineBundle& pipelineBundle,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeManagedBufferShadow& sourceIndexBuffer,
    const NativeTriangleFanIndexBuffer& generatedIndexBuffer,
    UINT primitiveCount,
    D3DFORMAT sourceIndexFormat,
    UINT startIndex,
    UINT sourceIndexCount,
    INT baseVertexLocation) noexcept {
    NativeFixedFunctionCompleteIndexedFanBoundDrawReadiness out{};
    const auto boundDraw =
        compose_fixed_function_same_context_bound_draw_readiness(
            draw, context, outputStateBinding, pipelineBundle,
            layout, vertexPrototype, pixelPrototype, samplers, textures);
    out.sameContextBoundDrawSnapshotToken = boundDraw.snapshotToken;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    if (context)
        context->GetDevice(contextDevice.ReleaseAndGetAddressOf());

    const auto currentVertex =
        vertexBuffer.mirror_readiness(contextDevice.Get());
    const auto currentSourceIndex =
        sourceIndexBuffer.mirror_readiness(contextDevice.Get());
    const auto currentFan =
        generatedIndexBuffer.readiness(contextDevice.Get());
    const auto currentGeometry =
        compose_fixed_function_indexed_triangle_fan_geometry_readiness(
            currentVertex, currentSourceIndex, currentFan,
            primitiveCount, sourceIndexFormat, startIndex, sourceIndexCount);
    const auto fanBinding =
        generatedIndexBuffer.binding_readiness(context);

    out.geometrySnapshotToken = currentGeometry.snapshotToken;
    out.vertexBufferSnapshotToken = currentVertex.snapshotToken;
    out.sourceIndexBufferSnapshotToken = currentSourceIndex.snapshotToken;
    out.generatedIndexBindingSnapshotToken = fanBinding.snapshotToken;
    out.inputValid =
        context != nullptr &&
        contextDevice.Get() != nullptr &&
        vertexStride != 0 &&
        boundDraw.inputValid &&
        currentGeometry.inputValid &&
        fanBinding.inputValid &&
        validate_fixed_function_draw_readiness_integrity(draw);
    out.sameContextBoundDrawReady =
        boundDraw.ready && boundDraw.snapshotToken != 0;
    out.geometryReady =
        currentGeometry.ready && currentGeometry.snapshotToken != 0;
    out.geometryMatchesDraw =
        draw.geometrySnapshotToken != 0 &&
        currentGeometry.snapshotToken == draw.geometrySnapshotToken;
    out.sourceIndexBufferCurrent =
        sourceIndexBuffer.mirror_device() == contextDevice.Get() &&
        currentSourceIndex.ready &&
        currentSourceIndex.role == ResourceRole::Index &&
        currentSourceIndex.snapshotToken != 0 &&
        currentSourceIndex.snapshotToken ==
            currentGeometry.indexBufferSnapshotToken;

    Microsoft::WRL::ComPtr<ID3D11Buffer> observedVertexBuffer;
    UINT observedStride = 0;
    UINT observedVertexOffset = 0;
    if (context) {
        context->IAGetVertexBuffers(
            0, 1, observedVertexBuffer.ReleaseAndGetAddressOf(),
            &observedStride, &observedVertexOffset);
    }
    out.vertexBufferBoundExact =
        contextDevice.Get() != nullptr &&
        vertexBuffer.mirror_device() == contextDevice.Get() &&
        currentVertex.ready &&
        currentVertex.snapshotToken ==
            currentGeometry.vertexBufferSnapshotToken &&
        observedVertexBuffer.Get() == vertexBuffer.mirror_buffer() &&
        observedStride == vertexStride &&
        observedVertexOffset == vertexOffset;
    out.generatedIndexBindingReady =
        fanBinding.ready && fanBinding.snapshotToken != 0;
    out.generatedIndexMatchesGeometry =
        currentFan.ready &&
        currentFan.indexedSource &&
        currentFan.baseVertex == 0 &&
        currentFan.snapshotToken != 0 &&
        currentGeometry.generatedIndexBufferRequired &&
        currentGeometry.generatedIndexBufferSnapshotToken ==
            currentFan.snapshotToken &&
        fanBinding.ownerSnapshotToken == currentFan.snapshotToken;
    out.componentSnapshotsPresent =
        boundDraw.snapshotToken != 0 &&
        currentGeometry.snapshotToken != 0 &&
        currentVertex.snapshotToken != 0 &&
        currentSourceIndex.snapshotToken != 0 &&
        fanBinding.snapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.sameContextBoundDrawReady &&
        out.geometryReady &&
        out.geometryMatchesDraw &&
        out.sourceIndexBufferCurrent &&
        out.vertexBufferBoundExact &&
        out.generatedIndexBindingReady &&
        out.generatedIndexMatchesGeometry &&
        out.componentSnapshotsPresent;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.sameContextBoundDrawSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.geometrySnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.vertexBufferSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.sourceIndexBufferSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.generatedIndexBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(
                    observedVertexBuffer.Get())));
        token = mix_readiness_snapshot_token(token, observedStride);
        token = mix_readiness_snapshot_token(token, observedVertexOffset);
        token = mix_readiness_snapshot_token(token, primitiveCount);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(sourceIndexFormat));
        token = mix_readiness_snapshot_token(token, startIndex);
        token = mix_readiness_snapshot_token(token, sourceIndexCount);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(baseVertexLocation));
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool
validate_fixed_function_complete_indexed_triangle_fan_bound_draw_snapshot(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    const NativeFixedFunctionPipelineBundle& pipelineBundle,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeManagedBufferShadow& sourceIndexBuffer,
    const NativeTriangleFanIndexBuffer& generatedIndexBuffer,
    UINT primitiveCount,
    D3DFORMAT sourceIndexFormat,
    UINT startIndex,
    UINT sourceIndexCount,
    INT baseVertexLocation,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current =
        compose_fixed_function_complete_indexed_triangle_fan_bound_draw_readiness(
            draw, context, outputStateBinding, pipelineBundle,
            layout, vertexPrototype, pixelPrototype, samplers, textures,
            vertexBuffer, vertexStride, vertexOffset, sourceIndexBuffer,
            generatedIndexBuffer, primitiveCount, sourceIndexFormat,
            startIndex, sourceIndexCount, baseVertexLocation);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionFullyBoundDrawReadiness
compose_fixed_function_fully_bound_draw_readiness(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    const NativeFixedFunctionPipelineBundle& pipelineBundle,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride, UINT vertexOffset,
    const NativeManagedBufferShadow* indexBuffer,
    DXGI_FORMAT indexFormat, UINT indexOffset,
    const FixedFunctionTransformConstants& transform) noexcept {
    NativeFixedFunctionFullyBoundDrawReadiness out{};
    const auto complete = compose_fixed_function_complete_bound_draw_readiness(
        draw, context, outputStateBinding, pipelineBundle,
        layout, vertexPrototype, pixelPrototype, samplers, textures,
        geometry, vertexBuffer, vertexStride, vertexOffset,
        indexBuffer, indexFormat, indexOffset);
    const auto transformBinding =
        pipelineBundle.transform_buffer().binding_readiness(context, transform);
    out.completeBoundDrawSnapshotToken = complete.snapshotToken;
    out.transformBindingSnapshotToken = transformBinding.snapshotToken;
    out.transformPayloadHash = transformBinding.payloadHash;
    out.inputValid = complete.inputValid && transformBinding.inputValid;
    out.completeBoundDrawReady = complete.ready && complete.snapshotToken != 0;
    out.transformBindingReady =
        transformBinding.ready && transformBinding.snapshotToken != 0;
    out.componentSnapshotsPresent =
        complete.snapshotToken != 0 &&
        transformBinding.snapshotToken != 0 &&
        transformBinding.payloadHash != 0;
    out.ready =
        out.inputValid && out.completeBoundDrawReady &&
        out.transformBindingReady && out.componentSnapshotsPresent;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.completeBoundDrawSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.transformBindingSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.transformPayloadHash);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_fully_bound_draw_snapshot(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    const NativeFixedFunctionPipelineBundle& pipelineBundle,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride, UINT vertexOffset,
    const NativeManagedBufferShadow* indexBuffer,
    DXGI_FORMAT indexFormat, UINT indexOffset,
    const FixedFunctionTransformConstants& transform,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = compose_fixed_function_fully_bound_draw_readiness(
        draw, context, outputStateBinding, pipelineBundle,
        layout, vertexPrototype, pixelPrototype, samplers, textures,
        geometry, vertexBuffer, vertexStride, vertexOffset,
        indexBuffer, indexFormat, indexOffset, transform);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionRenderTargetBoundDrawReadiness
compose_fixed_function_render_target_bound_draw_readiness(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    const NativeFixedFunctionPipelineBundle& pipelineBundle,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride, UINT vertexOffset,
    const NativeManagedBufferShadow* indexBuffer,
    DXGI_FORMAT indexFormat, UINT indexOffset,
    const FixedFunctionTransformConstants& transform,
    const NativeSurfacePairBinding& surfaceBinding,
    const NativeSurfaceMirror& colorSurface,
    const NativeSurfaceMirror& depthSurface) noexcept {
    NativeFixedFunctionRenderTargetBoundDrawReadiness out{};
    out.vertexStride = vertexStride;
    out.inputLayoutStream0Stride = layout.stream0Stride;
    out.vertexOffset = vertexOffset;
    out.vertexBufferByteWidth = vertexBuffer.byte_width();
    out.indexFormat = indexFormat;
    out.indexOffset = indexOffset;
    out.indexBufferByteWidth = indexBuffer ? indexBuffer->byte_width() : 0u;
    const UINT indexElementBytes =
        indexFormat == DXGI_FORMAT_R16_UINT ? 2u :
        indexFormat == DXGI_FORMAT_R32_UINT ? 4u : 0u;
    out.vertexStrideMatchesInputLayout =
        layout.exact &&
        layout.stream0Stride != 0 &&
        vertexStride == layout.stream0Stride;
    out.geometryRangeMetadataExact =
        vertexStride != 0 &&
        out.vertexBufferByteWidth != 0 &&
        vertexOffset <= out.vertexBufferByteWidth &&
        (geometry.indexBufferRequired
            ? indexBuffer != nullptr &&
              indexElementBytes != 0 &&
              (indexOffset % indexElementBytes) == 0 &&
              out.indexBufferByteWidth != 0 &&
              indexOffset <= out.indexBufferByteWidth
            : indexBuffer == nullptr &&
              indexFormat == DXGI_FORMAT_UNKNOWN &&
              indexOffset == 0 &&
              out.indexBufferByteWidth == 0);

    const auto fullyBound =
        compose_fixed_function_fully_bound_draw_readiness(
            draw, context, outputStateBinding, pipelineBundle,
            layout, vertexPrototype, pixelPrototype, samplers, textures,
            geometry, vertexBuffer, vertexStride, vertexOffset,
            indexBuffer, indexFormat, indexOffset, transform);
    const auto targetBinding =
        surfaceBinding.binding_readiness(
            context, colorSurface, depthSurface);

    out.fullyBoundDrawSnapshotToken = fullyBound.snapshotToken;
    out.surfaceTargetBindingSnapshotToken = targetBinding.snapshotToken;
    out.surfacePairSnapshotToken = targetBinding.surfacePairSnapshotToken;
    out.inputValid = fullyBound.inputValid && targetBinding.inputValid;
    out.fullyBoundDrawReady =
        fullyBound.ready && fullyBound.snapshotToken != 0;
    out.surfaceTargetBindingReady =
        targetBinding.ready && targetBinding.snapshotToken != 0;
    out.surfacePairMatchesDraw =
        draw.surfacePairSnapshotToken != 0 &&
        targetBinding.surfacePairSnapshotToken ==
            draw.surfacePairSnapshotToken &&
        outputStateBinding.surface_pair_snapshot_token() ==
            draw.surfacePairSnapshotToken;
    out.componentSnapshotsPresent =
        fullyBound.snapshotToken != 0 &&
        targetBinding.snapshotToken != 0 &&
        targetBinding.surfacePairSnapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.fullyBoundDrawReady &&
        out.surfaceTargetBindingReady &&
        out.surfacePairMatchesDraw &&
        out.geometryRangeMetadataExact &&
        out.vertexStrideMatchesInputLayout &&
        out.componentSnapshotsPresent;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.fullyBoundDrawSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.surfaceTargetBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.surfacePairSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.vertexStride);
        token = mix_readiness_snapshot_token(
            token, out.inputLayoutStream0Stride);
        token = mix_readiness_snapshot_token(token, out.vertexOffset);
        token = mix_readiness_snapshot_token(token, out.vertexBufferByteWidth);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.indexFormat));
        token = mix_readiness_snapshot_token(token, out.indexOffset);
        token = mix_readiness_snapshot_token(token, out.indexBufferByteWidth);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_render_target_bound_draw_snapshot(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    const NativeFixedFunctionPipelineBundle& pipelineBundle,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride, UINT vertexOffset,
    const NativeManagedBufferShadow* indexBuffer,
    DXGI_FORMAT indexFormat, UINT indexOffset,
    const FixedFunctionTransformConstants& transform,
    const NativeSurfacePairBinding& surfaceBinding,
    const NativeSurfaceMirror& colorSurface,
    const NativeSurfaceMirror& depthSurface,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current =
        compose_fixed_function_render_target_bound_draw_readiness(
            draw, context, outputStateBinding, pipelineBundle,
            layout, vertexPrototype, pixelPrototype, samplers, textures,
            geometry, vertexBuffer, vertexStride, vertexOffset,
            indexBuffer, indexFormat, indexOffset, transform,
            surfaceBinding, colorSurface, depthSurface);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionFinalFanBoundDrawReadiness
compose_fixed_function_final_nonindexed_triangle_fan_bound_draw_readiness(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    const NativeFixedFunctionPipelineBundle& pipelineBundle,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeTriangleFanIndexBuffer& generatedIndexBuffer,
    UINT primitiveCount,
    UINT baseVertex,
    const FixedFunctionTransformConstants& transform,
    const NativeSurfacePairBinding& surfaceBinding,
    const NativeSurfaceMirror& colorSurface,
    const NativeSurfaceMirror& depthSurface) noexcept {
    NativeFixedFunctionFinalFanBoundDrawReadiness out{};
    const auto complete =
        compose_fixed_function_complete_nonindexed_triangle_fan_bound_draw_readiness(
            draw, context, outputStateBinding, pipelineBundle,
            layout, vertexPrototype, pixelPrototype, samplers, textures,
            vertexBuffer, vertexStride, vertexOffset,
            generatedIndexBuffer, primitiveCount, baseVertex);
    const auto transformBinding =
        pipelineBundle.transform_buffer().binding_readiness(context, transform);
    const auto targetBinding =
        surfaceBinding.binding_readiness(context, colorSurface, depthSurface);

    out.completeFanBoundDrawSnapshotToken = complete.snapshotToken;
    out.transformBindingSnapshotToken = transformBinding.snapshotToken;
    out.transformPayloadHash = transformBinding.payloadHash;
    out.surfaceTargetBindingSnapshotToken = targetBinding.snapshotToken;
    out.surfacePairSnapshotToken = targetBinding.surfacePairSnapshotToken;
    out.inputValid =
        complete.inputValid && transformBinding.inputValid &&
        targetBinding.inputValid;
    out.completeFanBoundDrawReady =
        complete.ready && complete.snapshotToken != 0;
    out.transformBindingReady =
        transformBinding.ready && transformBinding.snapshotToken != 0;
    out.surfaceTargetBindingReady =
        targetBinding.ready && targetBinding.snapshotToken != 0;
    out.surfacePairMatchesDraw =
        draw.surfacePairSnapshotToken != 0 &&
        targetBinding.surfacePairSnapshotToken ==
            draw.surfacePairSnapshotToken &&
        outputStateBinding.surface_pair_snapshot_token() ==
            draw.surfacePairSnapshotToken;
    out.componentSnapshotsPresent =
        complete.snapshotToken != 0 &&
        transformBinding.snapshotToken != 0 &&
        transformBinding.payloadHash != 0 &&
        targetBinding.snapshotToken != 0 &&
        targetBinding.surfacePairSnapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.completeFanBoundDrawReady &&
        out.transformBindingReady &&
        out.surfaceTargetBindingReady &&
        out.surfacePairMatchesDraw &&
        out.componentSnapshotsPresent;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.completeFanBoundDrawSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.transformBindingSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.transformPayloadHash);
        token = mix_readiness_snapshot_token(
            token, out.surfaceTargetBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.surfacePairSnapshotToken);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool
validate_fixed_function_final_nonindexed_triangle_fan_bound_draw_snapshot(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    const NativeFixedFunctionPipelineBundle& pipelineBundle,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeTriangleFanIndexBuffer& generatedIndexBuffer,
    UINT primitiveCount,
    UINT baseVertex,
    const FixedFunctionTransformConstants& transform,
    const NativeSurfacePairBinding& surfaceBinding,
    const NativeSurfaceMirror& colorSurface,
    const NativeSurfaceMirror& depthSurface,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current =
        compose_fixed_function_final_nonindexed_triangle_fan_bound_draw_readiness(
            draw, context, outputStateBinding, pipelineBundle,
            layout, vertexPrototype, pixelPrototype, samplers, textures,
            vertexBuffer, vertexStride, vertexOffset,
            generatedIndexBuffer, primitiveCount, baseVertex, transform,
            surfaceBinding, colorSurface, depthSurface);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionFinalFanBoundDrawReadiness
compose_fixed_function_final_indexed_triangle_fan_bound_draw_readiness(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    const NativeFixedFunctionPipelineBundle& pipelineBundle,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeManagedBufferShadow& sourceIndexBuffer,
    const NativeTriangleFanIndexBuffer& generatedIndexBuffer,
    UINT primitiveCount,
    D3DFORMAT sourceIndexFormat,
    UINT startIndex,
    UINT sourceIndexCount,
    INT baseVertexLocation,
    const FixedFunctionTransformConstants& transform,
    const NativeSurfacePairBinding& surfaceBinding,
    const NativeSurfaceMirror& colorSurface,
    const NativeSurfaceMirror& depthSurface) noexcept {
    NativeFixedFunctionFinalFanBoundDrawReadiness out{};
    const auto complete =
        compose_fixed_function_complete_indexed_triangle_fan_bound_draw_readiness(
            draw, context, outputStateBinding, pipelineBundle,
            layout, vertexPrototype, pixelPrototype, samplers, textures,
            vertexBuffer, vertexStride, vertexOffset, sourceIndexBuffer,
            generatedIndexBuffer, primitiveCount, sourceIndexFormat,
            startIndex, sourceIndexCount, baseVertexLocation);
    const auto transformBinding =
        pipelineBundle.transform_buffer().binding_readiness(context, transform);
    const auto targetBinding =
        surfaceBinding.binding_readiness(context, colorSurface, depthSurface);

    out.completeFanBoundDrawSnapshotToken = complete.snapshotToken;
    out.transformBindingSnapshotToken = transformBinding.snapshotToken;
    out.transformPayloadHash = transformBinding.payloadHash;
    out.surfaceTargetBindingSnapshotToken = targetBinding.snapshotToken;
    out.surfacePairSnapshotToken = targetBinding.surfacePairSnapshotToken;
    out.inputValid =
        complete.inputValid && transformBinding.inputValid &&
        targetBinding.inputValid;
    out.completeFanBoundDrawReady =
        complete.ready && complete.snapshotToken != 0;
    out.transformBindingReady =
        transformBinding.ready && transformBinding.snapshotToken != 0;
    out.surfaceTargetBindingReady =
        targetBinding.ready && targetBinding.snapshotToken != 0;
    out.surfacePairMatchesDraw =
        draw.surfacePairSnapshotToken != 0 &&
        targetBinding.surfacePairSnapshotToken ==
            draw.surfacePairSnapshotToken &&
        outputStateBinding.surface_pair_snapshot_token() ==
            draw.surfacePairSnapshotToken;
    out.componentSnapshotsPresent =
        complete.snapshotToken != 0 &&
        transformBinding.snapshotToken != 0 &&
        transformBinding.payloadHash != 0 &&
        targetBinding.snapshotToken != 0 &&
        targetBinding.surfacePairSnapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.completeFanBoundDrawReady &&
        out.transformBindingReady &&
        out.surfaceTargetBindingReady &&
        out.surfacePairMatchesDraw &&
        out.componentSnapshotsPresent;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.completeFanBoundDrawSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.transformBindingSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.transformPayloadHash);
        token = mix_readiness_snapshot_token(
            token, out.surfaceTargetBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.surfacePairSnapshotToken);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool
validate_fixed_function_final_indexed_triangle_fan_bound_draw_snapshot(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    const NativeFixedFunctionPipelineBundle& pipelineBundle,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeManagedBufferShadow& sourceIndexBuffer,
    const NativeTriangleFanIndexBuffer& generatedIndexBuffer,
    UINT primitiveCount,
    D3DFORMAT sourceIndexFormat,
    UINT startIndex,
    UINT sourceIndexCount,
    INT baseVertexLocation,
    const FixedFunctionTransformConstants& transform,
    const NativeSurfacePairBinding& surfaceBinding,
    const NativeSurfaceMirror& colorSurface,
    const NativeSurfaceMirror& depthSurface,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current =
        compose_fixed_function_final_indexed_triangle_fan_bound_draw_readiness(
            draw, context, outputStateBinding, pipelineBundle,
            layout, vertexPrototype, pixelPrototype, samplers, textures,
            vertexBuffer, vertexStride, vertexOffset, sourceIndexBuffer,
            generatedIndexBuffer, primitiveCount, sourceIndexFormat,
            startIndex, sourceIndexCount, baseVertexLocation, transform,
            surfaceBinding, colorSurface, depthSurface);
    return current.ready && current.snapshotToken == snapshotToken;
}


static bool direct_draw_element_count(
    D3DPRIMITIVETYPE primitive,
    UINT primitiveCount,
    UINT& elementCount) noexcept {
    elementCount = 0;
    if (primitiveCount == 0)
        return primitive != D3DPT_TRIANGLEFAN &&
            translate_primitive(primitive).exact;

    const UINT maxValue = (std::numeric_limits<UINT>::max)();
    switch (primitive) {
    case D3DPT_POINTLIST:
        elementCount = primitiveCount;
        return true;
    case D3DPT_LINELIST:
        if (primitiveCount > maxValue / 2u)
            return false;
        elementCount = primitiveCount * 2u;
        return true;
    case D3DPT_LINESTRIP:
        if (primitiveCount == maxValue)
            return false;
        elementCount = primitiveCount + 1u;
        return true;
    case D3DPT_TRIANGLELIST:
        if (primitiveCount > maxValue / 3u)
            return false;
        elementCount = primitiveCount * 3u;
        return true;
    case D3DPT_TRIANGLESTRIP:
        if (primitiveCount > maxValue - 2u)
            return false;
        elementCount = primitiveCount + 2u;
        return true;
    case D3DPT_TRIANGLEFAN:
    default:
        return false;
    }
}

NativeProgrammableShaderNonIndexedDirectDispatchReadiness
NativeProgrammableShaderPairCache::nonindexed_direct_dispatch_readiness(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken,
    std::uint64_t constantBindingSnapshotToken,
    std::uint64_t pipelineBindingSnapshotToken,
    D3DPRIMITIVETYPE primitiveType,
    std::uint64_t topologyBindingSnapshotToken,
    const NativeManagedBufferShadow& vertexBuffer,
    std::uint64_t vertexBufferSnapshotToken,
    UINT vertexStride,
    UINT vertexOffset,
    std::uint64_t nonIndexedGeometryBindingSnapshotToken,
    UINT primitiveCount,
    UINT startVertexLocation) const noexcept {
    NativeProgrammableShaderNonIndexedDirectDispatchReadiness out{};
    out.primitiveCount = primitiveCount;
    out.startVertexLocation = startVertexLocation;
    out.vertexStride = vertexStride;
    out.vertexOffset = vertexOffset;
    out.vertexBufferByteWidth = vertexBuffer.byte_width();
    out.geometryBindingSnapshotToken =
        nonIndexedGeometryBindingSnapshotToken;
    out.vertexBufferSnapshotToken = vertexBufferSnapshotToken;

    const auto geometry = nonindexed_geometry_binding_readiness(
        expectedContext, expectedDevice, identity, cacheSnapshotToken,
        slotSnapshotToken, objectSnapshotToken, layout,
        inputLayoutSnapshotToken, constantStateSnapshotToken,
        constantPayloadSnapshotToken, constantBindingSnapshotToken,
        pipelineBindingSnapshotToken, primitiveType,
        topologyBindingSnapshotToken, vertexBuffer,
        vertexBufferSnapshotToken, vertexStride, vertexOffset);
    out.inputValid =
        expectedContext != nullptr && expectedDevice != nullptr &&
        nonIndexedGeometryBindingSnapshotToken != 0 &&
        vertexBufferSnapshotToken != 0 &&
        vertexStride != 0 &&
        out.vertexBufferByteWidth != 0;
    out.geometryBindingReady = geometry.bindingReady;
    out.geometryBindingSnapshotMatches =
        geometry.bindingReady &&
        geometry.snapshotToken == nonIndexedGeometryBindingSnapshotToken;

    const auto topology = translate_primitive(primitiveType);
    out.topology = topology.value;
    out.primitiveExact =
        topology.exact &&
        primitiveType != D3DPT_TRIANGLEFAN &&
        topology.value != D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    out.topologyMatchesGeometry =
        out.primitiveExact &&
        geometry.translatedTopology == topology.value;

    UINT vertexCount = 0;
    out.countExact =
        direct_draw_element_count(primitiveType, primitiveCount, vertexCount);
    out.vertexCount = out.countExact ? vertexCount : 0u;

    out.vertexRangeExact = false;
    if (out.countExact && vertexStride != 0) {
        const UINT maxValue = (std::numeric_limits<UINT>::max)();
        const bool elementRangeExact =
            startVertexLocation <= maxValue - out.vertexCount;
        if (elementRangeExact) {
            const std::uint64_t firstByte =
                static_cast<std::uint64_t>(vertexOffset) +
                static_cast<std::uint64_t>(startVertexLocation) *
                    static_cast<std::uint64_t>(vertexStride);
            const std::uint64_t endByte =
                firstByte +
                static_cast<std::uint64_t>(out.vertexCount) *
                    static_cast<std::uint64_t>(vertexStride);
            out.vertexRangeExact =
                firstByte <= out.vertexBufferByteWidth &&
                endByte <= out.vertexBufferByteWidth;
        }
    }

    out.dispatchArgumentsExact =
        out.countExact && out.vertexRangeExact;
    out.componentSnapshotsPresent =
        geometry.snapshotToken != 0 &&
        geometry.vertexBufferSnapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.geometryBindingReady &&
        out.geometryBindingSnapshotMatches &&
        out.primitiveExact &&
        out.topologyMatchesGeometry &&
        out.dispatchArgumentsExact &&
        out.componentSnapshotsPresent;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.geometryBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.vertexBufferSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(primitiveType));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.topology));
        token = mix_readiness_snapshot_token(token, out.primitiveCount);
        token = mix_readiness_snapshot_token(token, out.vertexCount);
        token = mix_readiness_snapshot_token(token, out.startVertexLocation);
        token = mix_readiness_snapshot_token(token, out.vertexStride);
        token = mix_readiness_snapshot_token(token, out.vertexOffset);
        token = mix_readiness_snapshot_token(
            token, out.vertexBufferByteWidth);
        token = mix_readiness_snapshot_token(
            token, out.vertexRangeExact ? 0x251u : 0u);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeProgrammableShaderPairCache::
validate_nonindexed_direct_dispatch_snapshot(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken,
    std::uint64_t constantBindingSnapshotToken,
    std::uint64_t pipelineBindingSnapshotToken,
    D3DPRIMITIVETYPE primitiveType,
    std::uint64_t topologyBindingSnapshotToken,
    const NativeManagedBufferShadow& vertexBuffer,
    std::uint64_t vertexBufferSnapshotToken,
    UINT vertexStride,
    UINT vertexOffset,
    std::uint64_t nonIndexedGeometryBindingSnapshotToken,
    UINT primitiveCount,
    UINT startVertexLocation,
    std::uint64_t directDispatchSnapshotToken) const noexcept {
    if (directDispatchSnapshotToken == 0)
        return false;
    const auto current = nonindexed_direct_dispatch_readiness(
        expectedContext, expectedDevice, identity, cacheSnapshotToken,
        slotSnapshotToken, objectSnapshotToken, layout,
        inputLayoutSnapshotToken, constantStateSnapshotToken,
        constantPayloadSnapshotToken, constantBindingSnapshotToken,
        pipelineBindingSnapshotToken, primitiveType,
        topologyBindingSnapshotToken, vertexBuffer,
        vertexBufferSnapshotToken, vertexStride, vertexOffset,
        nonIndexedGeometryBindingSnapshotToken,
        primitiveCount, startVertexLocation);
    return current.ready &&
           current.snapshotToken == directDispatchSnapshotToken;
}

NativeProgrammableShaderIndexedDirectDispatchReadiness
NativeProgrammableShaderPairCache::indexed_direct_dispatch_readiness(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken,
    std::uint64_t constantBindingSnapshotToken,
    std::uint64_t pipelineBindingSnapshotToken,
    D3DPRIMITIVETYPE primitiveType,
    std::uint64_t topologyBindingSnapshotToken,
    const NativeManagedBufferShadow& vertexBuffer,
    std::uint64_t vertexBufferSnapshotToken,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeManagedBufferShadow& indexBuffer,
    std::uint64_t indexBufferSnapshotToken,
    DXGI_FORMAT indexFormat,
    UINT indexOffset,
    std::uint64_t indexedGeometryBindingSnapshotToken,
    UINT primitiveCount,
    INT baseVertexIndex,
    UINT minVertexIndex,
    UINT numVertices,
    UINT startIndex) const noexcept {
    NativeProgrammableShaderIndexedDirectDispatchReadiness out{};
    out.primitiveCount = primitiveCount;
    out.baseVertexLocation = baseVertexIndex;
    out.minVertexIndex = minVertexIndex;
    out.numVertices = numVertices;
    out.startIndexLocation = startIndex;
    out.vertexStride = vertexStride;
    out.vertexOffset = vertexOffset;
    out.vertexBufferByteWidth = vertexBuffer.byte_width();
    out.indexFormat = indexFormat;
    out.indexOffset = indexOffset;
    out.indexBufferByteWidth = indexBuffer.byte_width();
    out.indexElementBytes =
        indexFormat == DXGI_FORMAT_R16_UINT ? 2u :
        indexFormat == DXGI_FORMAT_R32_UINT ? 4u : 0u;
    out.geometryBindingSnapshotToken = indexedGeometryBindingSnapshotToken;
    out.vertexBufferSnapshotToken = vertexBufferSnapshotToken;
    out.indexBufferSnapshotToken = indexBufferSnapshotToken;

    const auto geometry = indexed_geometry_binding_readiness(
        expectedContext, expectedDevice, identity, cacheSnapshotToken,
        slotSnapshotToken, objectSnapshotToken, layout,
        inputLayoutSnapshotToken, constantStateSnapshotToken,
        constantPayloadSnapshotToken, constantBindingSnapshotToken,
        pipelineBindingSnapshotToken, primitiveType,
        topologyBindingSnapshotToken, vertexBuffer,
        vertexBufferSnapshotToken, vertexStride, vertexOffset,
        indexBuffer, indexBufferSnapshotToken, indexFormat, indexOffset);

    out.inputValid =
        expectedContext != nullptr && expectedDevice != nullptr &&
        indexedGeometryBindingSnapshotToken != 0 &&
        vertexBufferSnapshotToken != 0 &&
        indexBufferSnapshotToken != 0 &&
        vertexStride != 0 &&
        out.vertexBufferByteWidth != 0 &&
        out.indexBufferByteWidth != 0 &&
        out.indexElementBytes != 0 &&
        (indexOffset % out.indexElementBytes) == 0;
    out.geometryBindingReady = geometry.bindingReady;
    out.geometryBindingSnapshotMatches =
        geometry.bindingReady &&
        geometry.snapshotToken == indexedGeometryBindingSnapshotToken;

    const auto topology = translate_primitive(primitiveType);
    out.topology = topology.value;
    out.primitiveExact =
        topology.exact &&
        primitiveType != D3DPT_TRIANGLEFAN &&
        topology.value != D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    out.topologyMatchesGeometry =
        out.primitiveExact &&
        geometry.translatedTopology == topology.value;

    UINT indexCount = 0;
    out.countExact =
        direct_draw_element_count(primitiveType, primitiveCount, indexCount);
    out.indexCount = out.countExact ? indexCount : 0u;

    const UINT maxValue = (std::numeric_limits<UINT>::max)();
    const bool vertexCountCompatible =
        primitiveCount == 0u || numVertices != 0u;
    bool declaredRangeFits = primitiveCount == 0u;
    bool effectiveRangeFits = primitiveCount == 0u;
    if (numVertices != 0u) {
        const UINT spanMinusOne = numVertices - 1u;
        declaredRangeFits = minVertexIndex <= maxValue - spanMinusOne;
        if (declaredRangeFits) {
            out.maxVertexIndex = minVertexIndex + spanMinusOne;
            const std::int64_t effectiveMin =
                static_cast<std::int64_t>(baseVertexIndex) +
                static_cast<std::int64_t>(minVertexIndex);
            const std::int64_t effectiveMax =
                static_cast<std::int64_t>(baseVertexIndex) +
                static_cast<std::int64_t>(out.maxVertexIndex);
            effectiveRangeFits =
                effectiveMin >= 0 &&
                effectiveMax >= effectiveMin &&
                effectiveMax <= static_cast<std::int64_t>(maxValue);
        } else {
            effectiveRangeFits = false;
        }
    }
    out.sourceVertexRangeExact =
        vertexCountCompatible && declaredRangeFits;
    out.effectiveVertexRangeExact =
        out.sourceVertexRangeExact && effectiveRangeFits;

    out.indexBufferRangeExact = false;
    if (out.countExact && out.indexElementBytes != 0) {
        const bool indexElementRangeExact =
            startIndex <= maxValue - out.indexCount;
        if (indexElementRangeExact) {
            const std::uint64_t firstByte =
                static_cast<std::uint64_t>(indexOffset) +
                static_cast<std::uint64_t>(startIndex) *
                    static_cast<std::uint64_t>(out.indexElementBytes);
            const std::uint64_t endByte =
                firstByte +
                static_cast<std::uint64_t>(out.indexCount) *
                    static_cast<std::uint64_t>(out.indexElementBytes);
            out.indexBufferRangeExact =
                firstByte <= out.indexBufferByteWidth &&
                endByte <= out.indexBufferByteWidth;
        }
    }

    out.vertexBufferRangeExact = false;
    if (out.effectiveVertexRangeExact && vertexStride != 0) {
        if (out.indexCount == 0u) {
            out.vertexBufferRangeExact =
                vertexOffset <= out.vertexBufferByteWidth;
        } else {
            const std::int64_t effectiveMax =
                static_cast<std::int64_t>(baseVertexIndex) +
                static_cast<std::int64_t>(out.maxVertexIndex);
            if (effectiveMax >= 0) {
                const std::uint64_t endByte =
                    static_cast<std::uint64_t>(vertexOffset) +
                    (static_cast<std::uint64_t>(effectiveMax) + 1ull) *
                        static_cast<std::uint64_t>(vertexStride);
                out.vertexBufferRangeExact =
                    endByte <= out.vertexBufferByteWidth;
            }
        }
    }

    out.dispatchArgumentsExact =
        out.countExact &&
        out.sourceVertexRangeExact &&
        out.effectiveVertexRangeExact &&
        out.indexBufferRangeExact &&
        out.vertexBufferRangeExact;
    out.componentSnapshotsPresent =
        geometry.snapshotToken != 0 &&
        geometry.vertexBufferSnapshotToken != 0 &&
        geometry.indexBufferSnapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.geometryBindingReady &&
        out.geometryBindingSnapshotMatches &&
        out.primitiveExact &&
        out.topologyMatchesGeometry &&
        out.dispatchArgumentsExact &&
        out.componentSnapshotsPresent;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.geometryBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.vertexBufferSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.indexBufferSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(primitiveType));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.topology));
        token = mix_readiness_snapshot_token(token, out.primitiveCount);
        token = mix_readiness_snapshot_token(token, out.indexCount);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.baseVertexLocation));
        token = mix_readiness_snapshot_token(token, out.minVertexIndex);
        token = mix_readiness_snapshot_token(token, out.numVertices);
        token = mix_readiness_snapshot_token(token, out.maxVertexIndex);
        token = mix_readiness_snapshot_token(token, out.startIndexLocation);
        token = mix_readiness_snapshot_token(token, out.vertexStride);
        token = mix_readiness_snapshot_token(token, out.vertexOffset);
        token = mix_readiness_snapshot_token(
            token, out.vertexBufferByteWidth);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.indexFormat));
        token = mix_readiness_snapshot_token(token, out.indexOffset);
        token = mix_readiness_snapshot_token(token, out.indexElementBytes);
        token = mix_readiness_snapshot_token(
            token, out.indexBufferByteWidth);
        token = mix_readiness_snapshot_token(
            token, out.dispatchArgumentsExact ? 0x252u : 0u);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeProgrammableShaderPairCache::validate_indexed_direct_dispatch_snapshot(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken,
    std::uint64_t constantBindingSnapshotToken,
    std::uint64_t pipelineBindingSnapshotToken,
    D3DPRIMITIVETYPE primitiveType,
    std::uint64_t topologyBindingSnapshotToken,
    const NativeManagedBufferShadow& vertexBuffer,
    std::uint64_t vertexBufferSnapshotToken,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeManagedBufferShadow& indexBuffer,
    std::uint64_t indexBufferSnapshotToken,
    DXGI_FORMAT indexFormat,
    UINT indexOffset,
    std::uint64_t indexedGeometryBindingSnapshotToken,
    UINT primitiveCount,
    INT baseVertexIndex,
    UINT minVertexIndex,
    UINT numVertices,
    UINT startIndex,
    std::uint64_t directDispatchSnapshotToken) const noexcept {
    if (directDispatchSnapshotToken == 0)
        return false;
    const auto current = indexed_direct_dispatch_readiness(
        expectedContext, expectedDevice, identity, cacheSnapshotToken,
        slotSnapshotToken, objectSnapshotToken, layout,
        inputLayoutSnapshotToken, constantStateSnapshotToken,
        constantPayloadSnapshotToken, constantBindingSnapshotToken,
        pipelineBindingSnapshotToken, primitiveType,
        topologyBindingSnapshotToken, vertexBuffer,
        vertexBufferSnapshotToken, vertexStride, vertexOffset,
        indexBuffer, indexBufferSnapshotToken, indexFormat, indexOffset,
        indexedGeometryBindingSnapshotToken, primitiveCount,
        baseVertexIndex, minVertexIndex, numVertices, startIndex);
    return current.ready &&
           current.snapshotToken == directDispatchSnapshotToken;
}

NativeProgrammableShaderIndexedSourceValueReadiness
NativeProgrammableShaderPairCache::indexed_source_value_readiness(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken,
    std::uint64_t constantBindingSnapshotToken,
    std::uint64_t pipelineBindingSnapshotToken,
    D3DPRIMITIVETYPE primitiveType,
    std::uint64_t topologyBindingSnapshotToken,
    const NativeManagedBufferShadow& vertexBuffer,
    std::uint64_t vertexBufferSnapshotToken,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeManagedBufferShadow& indexBuffer,
    std::uint64_t indexBufferSnapshotToken,
    DXGI_FORMAT indexFormat,
    UINT indexOffset,
    std::uint64_t indexedGeometryBindingSnapshotToken,
    UINT primitiveCount,
    INT baseVertexIndex,
    UINT minVertexIndex,
    UINT numVertices,
    UINT startIndex,
    std::uint64_t directDispatchSnapshotToken) const noexcept {

    NativeProgrammableShaderIndexedSourceValueReadiness out{};
    out.directDispatchSnapshotToken = directDispatchSnapshotToken;
    out.indexMirrorSnapshotToken = indexBufferSnapshotToken;

    const auto dispatch = indexed_direct_dispatch_readiness(
        expectedContext, expectedDevice, identity, cacheSnapshotToken,
        slotSnapshotToken, objectSnapshotToken, layout,
        inputLayoutSnapshotToken, constantStateSnapshotToken,
        constantPayloadSnapshotToken, constantBindingSnapshotToken,
        pipelineBindingSnapshotToken, primitiveType,
        topologyBindingSnapshotToken, vertexBuffer,
        vertexBufferSnapshotToken, vertexStride, vertexOffset,
        indexBuffer, indexBufferSnapshotToken, indexFormat, indexOffset,
        indexedGeometryBindingSnapshotToken, primitiveCount,
        baseVertexIndex, minVertexIndex, numVertices, startIndex);

    out.inputValid =
        expectedContext != nullptr && expectedDevice != nullptr &&
        directDispatchSnapshotToken != 0 && indexBufferSnapshotToken != 0;
    out.directDispatchReady = dispatch.ready;
    out.directDispatchSnapshotMatches =
        dispatch.ready && dispatch.snapshotToken == directDispatchSnapshotToken;
    out.indexCount = dispatch.indexCount;
    out.minVertexIndex = dispatch.minVertexIndex;
    out.maxVertexIndex = dispatch.maxVertexIndex;

    const auto mirror = indexBuffer.mirror_readiness(expectedDevice);
    out.indexMirrorReady = mirror.ready;
    out.indexMirrorSnapshotMatches =
        mirror.ready && mirror.snapshotToken == indexBufferSnapshotToken;

    out.sourceIndexFormat =
        indexFormat == DXGI_FORMAT_R16_UINT ? D3DFMT_INDEX16 :
        indexFormat == DXGI_FORMAT_R32_UINT ? D3DFMT_INDEX32 :
        D3DFMT_UNKNOWN;
    out.indexFormatExact = out.sourceIndexFormat != D3DFMT_UNKNOWN;

    bool scanStartExact = false;
    if (out.indexFormatExact && dispatch.indexElementBytes != 0 &&
        (indexOffset % dispatch.indexElementBytes) == 0) {
        const UINT offsetElements = indexOffset / dispatch.indexElementBytes;
        const UINT maxValue = (std::numeric_limits<UINT>::max)();
        scanStartExact = startIndex <= maxValue - offsetElements;
        if (scanStartExact)
            out.scanStartIndex = offsetElements + startIndex;
    }

    NativeManagedIndexRangeReadiness sourceValues{};
    if (scanStartExact && out.indexMirrorSnapshotMatches &&
        out.directDispatchSnapshotMatches) {
        sourceValues = indexBuffer.index_range_readiness(
            mirror, out.sourceIndexFormat, out.scanStartIndex,
            dispatch.indexCount, dispatch.minVertexIndex, dispatch.maxVertexIndex);
    }
    out.sourceValuesReady = sourceValues.ready;
    out.sourceValuesMatchDispatchWindow =
        sourceValues.startIndex == out.scanStartIndex &&
        sourceValues.indexCount == dispatch.indexCount;
    out.sourceValuesMatchDispatchRange =
        sourceValues.minVertexIndex == dispatch.minVertexIndex &&
        sourceValues.maxVertexIndex == dispatch.maxVertexIndex;
    out.observedMinIndex = sourceValues.observedMinIndex;
    out.observedMaxIndex = sourceValues.observedMaxIndex;
    out.sourceValueSnapshotToken = sourceValues.snapshotToken;
    out.sourceContentHash = sourceValues.contentHash;
    out.componentSnapshotsPresent =
        dispatch.snapshotToken != 0 &&
        mirror.snapshotToken != 0 &&
        sourceValues.snapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.directDispatchReady &&
        out.directDispatchSnapshotMatches &&
        out.indexMirrorReady &&
        out.indexMirrorSnapshotMatches &&
        out.indexFormatExact &&
        out.sourceValuesReady &&
        out.sourceValuesMatchDispatchWindow &&
        out.sourceValuesMatchDispatchRange &&
        out.componentSnapshotsPresent;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.directDispatchSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.indexMirrorSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.sourceValueSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.sourceIndexFormat));
        token = mix_readiness_snapshot_token(token, out.scanStartIndex);
        token = mix_readiness_snapshot_token(token, out.indexCount);
        token = mix_readiness_snapshot_token(token, out.minVertexIndex);
        token = mix_readiness_snapshot_token(token, out.maxVertexIndex);
        token = mix_readiness_snapshot_token(token, out.observedMinIndex);
        token = mix_readiness_snapshot_token(token, out.observedMaxIndex);
        token = mix_readiness_snapshot_token(token, out.sourceContentHash);
        token = mix_readiness_snapshot_token(token, 0x253u);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeProgrammableShaderPairCache::validate_indexed_source_value_snapshot(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken,
    std::uint64_t constantBindingSnapshotToken,
    std::uint64_t pipelineBindingSnapshotToken,
    D3DPRIMITIVETYPE primitiveType,
    std::uint64_t topologyBindingSnapshotToken,
    const NativeManagedBufferShadow& vertexBuffer,
    std::uint64_t vertexBufferSnapshotToken,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeManagedBufferShadow& indexBuffer,
    std::uint64_t indexBufferSnapshotToken,
    DXGI_FORMAT indexFormat,
    UINT indexOffset,
    std::uint64_t indexedGeometryBindingSnapshotToken,
    UINT primitiveCount,
    INT baseVertexIndex,
    UINT minVertexIndex,
    UINT numVertices,
    UINT startIndex,
    std::uint64_t directDispatchSnapshotToken,
    std::uint64_t sourceValueSnapshotToken) const noexcept {
    if (sourceValueSnapshotToken == 0)
        return false;
    const auto current = indexed_source_value_readiness(
        expectedContext, expectedDevice, identity, cacheSnapshotToken,
        slotSnapshotToken, objectSnapshotToken, layout,
        inputLayoutSnapshotToken, constantStateSnapshotToken,
        constantPayloadSnapshotToken, constantBindingSnapshotToken,
        pipelineBindingSnapshotToken, primitiveType,
        topologyBindingSnapshotToken, vertexBuffer,
        vertexBufferSnapshotToken, vertexStride, vertexOffset,
        indexBuffer, indexBufferSnapshotToken, indexFormat, indexOffset,
        indexedGeometryBindingSnapshotToken, primitiveCount,
        baseVertexIndex, minVertexIndex, numVertices, startIndex,
        directDispatchSnapshotToken);
    return current.ready && current.snapshotToken == sourceValueSnapshotToken;
}

NativeProgrammableShaderIndexedLiveIndexBindingReadiness
NativeProgrammableShaderPairCache::indexed_live_index_binding_readiness(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const NativeManagedBufferShadow& indexBuffer,
    std::uint64_t indexBufferSnapshotToken,
    DXGI_FORMAT indexFormat,
    UINT indexOffset,
    const NativeProgrammableShaderIndexedSourceValueReadiness& sourceValues,
    std::uint64_t sourceValueSnapshotToken) const noexcept {

    NativeProgrammableShaderIndexedLiveIndexBindingReadiness out{};
    out.expectedIndexFormat = indexFormat;
    out.expectedIndexOffset = indexOffset;
    out.sourceValueSnapshotToken = sourceValueSnapshotToken;
    out.indexMirrorSnapshotToken = indexBufferSnapshotToken;
    out.expectedIndexBufferIdentity = static_cast<std::uint64_t>(
        reinterpret_cast<std::uintptr_t>(indexBuffer.mirror_buffer()));

    const UINT indexElementBytes =
        indexFormat == DXGI_FORMAT_R16_UINT ? 2u :
        indexFormat == DXGI_FORMAT_R32_UINT ? 4u : 0u;
    const D3DFORMAT sourceIndexFormat =
        indexFormat == DXGI_FORMAT_R16_UINT ? D3DFMT_INDEX16 :
        indexFormat == DXGI_FORMAT_R32_UINT ? D3DFMT_INDEX32 :
        D3DFMT_UNKNOWN;
    out.inputValid =
        expectedContext != nullptr && expectedDevice != nullptr &&
        indexBufferSnapshotToken != 0 && sourceValueSnapshotToken != 0 &&
        indexElementBytes != 0 &&
        (indexOffset % indexElementBytes) == 0 &&
        out.expectedIndexBufferIdentity != 0;

    out.sourceValueReady = sourceValues.ready;
    std::uint64_t sealedSourceValueToken = 0;
    if (sourceValues.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, sourceValues.directDispatchSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, sourceValues.indexMirrorSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, sourceValues.sourceValueSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(sourceValues.sourceIndexFormat));
        token = mix_readiness_snapshot_token(token, sourceValues.scanStartIndex);
        token = mix_readiness_snapshot_token(token, sourceValues.indexCount);
        token = mix_readiness_snapshot_token(token, sourceValues.minVertexIndex);
        token = mix_readiness_snapshot_token(token, sourceValues.maxVertexIndex);
        token = mix_readiness_snapshot_token(token, sourceValues.observedMinIndex);
        token = mix_readiness_snapshot_token(token, sourceValues.observedMaxIndex);
        token = mix_readiness_snapshot_token(token, sourceValues.sourceContentHash);
        token = mix_readiness_snapshot_token(token, 0x253u);
        sealedSourceValueToken = token == 0 ? 1 : token;
    }
    out.sourceValueSnapshotMatches =
        sourceValues.ready &&
        sourceValues.snapshotToken == sourceValueSnapshotToken &&
        sealedSourceValueToken == sourceValueSnapshotToken;
    out.sourceValueFormatMatches =
        sourceIndexFormat != D3DFMT_UNKNOWN &&
        sourceValues.sourceIndexFormat == sourceIndexFormat;

    const auto mirror = indexBuffer.mirror_readiness(expectedDevice);
    out.indexMirrorReady = mirror.ready && mirror.role == ResourceRole::Index;
    out.indexMirrorSnapshotMatches =
        out.indexMirrorReady &&
        mirror.snapshotToken == indexBufferSnapshotToken &&
        sourceValues.indexMirrorSnapshotToken == indexBufferSnapshotToken;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    if (expectedContext)
        expectedContext->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    out.contextDeviceMatches =
        contextDevice.Get() != nullptr &&
        contextDevice.Get() == expectedDevice;

    Microsoft::WRL::ComPtr<ID3D11Buffer> observedIndex;
    DXGI_FORMAT observedIndexFormat = DXGI_FORMAT_UNKNOWN;
    UINT observedIndexOffset = 0;
    if (expectedContext) {
        expectedContext->IAGetIndexBuffer(
            observedIndex.ReleaseAndGetAddressOf(),
            &observedIndexFormat, &observedIndexOffset);
    }
    out.observedIndexFormat = observedIndexFormat;
    out.observedIndexOffset = observedIndexOffset;
    out.observedIndexBufferIdentity = static_cast<std::uint64_t>(
        reinterpret_cast<std::uintptr_t>(observedIndex.Get()));
    out.liveIndexBufferMatches =
        observedIndex.Get() != nullptr &&
        observedIndex.Get() == indexBuffer.mirror_buffer();
    out.liveIndexFormatMatches = observedIndexFormat == indexFormat;
    out.liveIndexOffsetMatches = observedIndexOffset == indexOffset;
    out.componentSnapshotsPresent =
        sourceValueSnapshotToken != 0 &&
        mirror.snapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.sourceValueReady &&
        out.sourceValueSnapshotMatches &&
        out.sourceValueFormatMatches &&
        out.indexMirrorReady &&
        out.indexMirrorSnapshotMatches &&
        out.contextDeviceMatches &&
        out.liveIndexBufferMatches &&
        out.liveIndexFormatMatches &&
        out.liveIndexOffsetMatches &&
        out.componentSnapshotsPresent;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.sourceValueSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.indexMirrorSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.expectedIndexBufferIdentity);
        token = mix_readiness_snapshot_token(
            token, out.observedIndexBufferIdentity);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.expectedIndexFormat));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.observedIndexFormat));
        token = mix_readiness_snapshot_token(token, out.expectedIndexOffset);
        token = mix_readiness_snapshot_token(token, out.observedIndexOffset);
        token = mix_readiness_snapshot_token(token, 0x254u);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeProgrammableShaderPairCache::
validate_indexed_live_index_binding_snapshot(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const NativeManagedBufferShadow& indexBuffer,
    std::uint64_t indexBufferSnapshotToken,
    DXGI_FORMAT indexFormat,
    UINT indexOffset,
    const NativeProgrammableShaderIndexedSourceValueReadiness& sourceValues,
    std::uint64_t sourceValueSnapshotToken,
    std::uint64_t liveIndexBindingSnapshotToken) const noexcept {
    if (liveIndexBindingSnapshotToken == 0)
        return false;
    const auto current = indexed_live_index_binding_readiness(
        expectedContext, expectedDevice, indexBuffer,
        indexBufferSnapshotToken, indexFormat, indexOffset,
        sourceValues, sourceValueSnapshotToken);
    return current.ready &&
           current.snapshotToken == liveIndexBindingSnapshotToken;
}

// R255 recomputes and joins the current R252/R253/R254 indexed receipts.
NativeProgrammableShaderIndexedPreDrawReadiness
NativeProgrammableShaderPairCache::indexed_pre_draw_readiness(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken,
    std::uint64_t constantBindingSnapshotToken,
    std::uint64_t pipelineBindingSnapshotToken,
    D3DPRIMITIVETYPE primitiveType,
    std::uint64_t topologyBindingSnapshotToken,
    const NativeManagedBufferShadow& vertexBuffer,
    std::uint64_t vertexBufferSnapshotToken,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeManagedBufferShadow& indexBuffer,
    std::uint64_t indexBufferSnapshotToken,
    DXGI_FORMAT indexFormat,
    UINT indexOffset,
    std::uint64_t indexedGeometryBindingSnapshotToken,
    UINT primitiveCount,
    INT baseVertexIndex,
    UINT minVertexIndex,
    UINT numVertices,
    UINT startIndex,
    std::uint64_t directDispatchSnapshotToken,
    std::uint64_t sourceValueSnapshotToken,
    std::uint64_t liveIndexBindingSnapshotToken) const noexcept {

    NativeProgrammableShaderIndexedPreDrawReadiness out{};
    out.directDispatchSnapshotToken = directDispatchSnapshotToken;
    out.sourceValueSnapshotToken = sourceValueSnapshotToken;
    out.liveIndexBindingSnapshotToken = liveIndexBindingSnapshotToken;

    const auto dispatch = indexed_direct_dispatch_readiness(
        expectedContext, expectedDevice, identity, cacheSnapshotToken,
        slotSnapshotToken, objectSnapshotToken, layout,
        inputLayoutSnapshotToken, constantStateSnapshotToken,
        constantPayloadSnapshotToken, constantBindingSnapshotToken,
        pipelineBindingSnapshotToken, primitiveType,
        topologyBindingSnapshotToken, vertexBuffer,
        vertexBufferSnapshotToken, vertexStride, vertexOffset,
        indexBuffer, indexBufferSnapshotToken, indexFormat, indexOffset,
        indexedGeometryBindingSnapshotToken, primitiveCount,
        baseVertexIndex, minVertexIndex, numVertices, startIndex);
    const auto sourceValues = indexed_source_value_readiness(
        expectedContext, expectedDevice, identity, cacheSnapshotToken,
        slotSnapshotToken, objectSnapshotToken, layout,
        inputLayoutSnapshotToken, constantStateSnapshotToken,
        constantPayloadSnapshotToken, constantBindingSnapshotToken,
        pipelineBindingSnapshotToken, primitiveType,
        topologyBindingSnapshotToken, vertexBuffer,
        vertexBufferSnapshotToken, vertexStride, vertexOffset,
        indexBuffer, indexBufferSnapshotToken, indexFormat, indexOffset,
        indexedGeometryBindingSnapshotToken, primitiveCount,
        baseVertexIndex, minVertexIndex, numVertices, startIndex,
        directDispatchSnapshotToken);
    const auto liveBinding = indexed_live_index_binding_readiness(
        expectedContext, expectedDevice, indexBuffer,
        indexBufferSnapshotToken, indexFormat, indexOffset,
        sourceValues, sourceValueSnapshotToken);

    out.indexCount = dispatch.indexCount;
    out.startIndexLocation = dispatch.startIndexLocation;
    out.baseVertexIndex = dispatch.baseVertexLocation;
    out.minVertexIndex = dispatch.minVertexIndex;
    out.numVertices = dispatch.numVertices;
    out.indexFormat = dispatch.indexFormat;
    out.indexOffset = dispatch.indexOffset;
    out.inputValid =
        expectedContext != nullptr && expectedDevice != nullptr &&
        directDispatchSnapshotToken != 0 &&
        sourceValueSnapshotToken != 0 &&
        liveIndexBindingSnapshotToken != 0;
    out.directDispatchReady = dispatch.ready;
    out.directDispatchSnapshotMatches =
        dispatch.ready && dispatch.snapshotToken == directDispatchSnapshotToken;
    out.sourceValueReady = sourceValues.ready;
    out.sourceValueSnapshotMatches =
        sourceValues.ready && sourceValues.snapshotToken == sourceValueSnapshotToken;
    out.liveIndexBindingReady = liveBinding.ready;
    out.liveIndexBindingSnapshotMatches =
        liveBinding.ready &&
        liveBinding.snapshotToken == liveIndexBindingSnapshotToken;
    out.dispatchSourceLineageMatches =
        out.directDispatchSnapshotMatches &&
        out.sourceValueSnapshotMatches &&
        sourceValues.directDispatchSnapshotToken == dispatch.snapshotToken &&
        sourceValues.indexMirrorSnapshotToken == dispatch.indexBufferSnapshotToken &&
        sourceValues.indexCount == dispatch.indexCount &&
        sourceValues.minVertexIndex == dispatch.minVertexIndex &&
        sourceValues.maxVertexIndex == dispatch.maxVertexIndex;
    out.sourceLiveLineageMatches =
        out.sourceValueSnapshotMatches &&
        out.liveIndexBindingSnapshotMatches &&
        liveBinding.sourceValueSnapshotToken == sourceValues.snapshotToken &&
        liveBinding.indexMirrorSnapshotToken ==
            sourceValues.indexMirrorSnapshotToken &&
        liveBinding.expectedIndexFormat == dispatch.indexFormat &&
        liveBinding.observedIndexFormat == dispatch.indexFormat &&
        liveBinding.expectedIndexOffset == dispatch.indexOffset &&
        liveBinding.observedIndexOffset == dispatch.indexOffset &&
        liveBinding.expectedIndexBufferIdentity != 0 &&
        liveBinding.expectedIndexBufferIdentity ==
            liveBinding.observedIndexBufferIdentity;
    out.componentSnapshotsPresent =
        dispatch.snapshotToken != 0 &&
        sourceValues.snapshotToken != 0 &&
        liveBinding.snapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.directDispatchReady &&
        out.directDispatchSnapshotMatches &&
        out.sourceValueReady &&
        out.sourceValueSnapshotMatches &&
        out.liveIndexBindingReady &&
        out.liveIndexBindingSnapshotMatches &&
        out.dispatchSourceLineageMatches &&
        out.sourceLiveLineageMatches &&
        out.componentSnapshotsPresent;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.directDispatchSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.sourceValueSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.liveIndexBindingSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.indexCount);
        token = mix_readiness_snapshot_token(token, out.startIndexLocation);
        token = mix_readiness_snapshot_token(
            token,
            static_cast<std::uint64_t>(
                static_cast<std::int64_t>(out.baseVertexIndex)));
        token = mix_readiness_snapshot_token(token, out.minVertexIndex);
        token = mix_readiness_snapshot_token(token, out.numVertices);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.indexFormat));
        token = mix_readiness_snapshot_token(token, out.indexOffset);
        token = mix_readiness_snapshot_token(token, 0x255u);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeProgrammableShaderPairCache::validate_indexed_pre_draw_snapshot(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken,
    std::uint64_t constantBindingSnapshotToken,
    std::uint64_t pipelineBindingSnapshotToken,
    D3DPRIMITIVETYPE primitiveType,
    std::uint64_t topologyBindingSnapshotToken,
    const NativeManagedBufferShadow& vertexBuffer,
    std::uint64_t vertexBufferSnapshotToken,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeManagedBufferShadow& indexBuffer,
    std::uint64_t indexBufferSnapshotToken,
    DXGI_FORMAT indexFormat,
    UINT indexOffset,
    std::uint64_t indexedGeometryBindingSnapshotToken,
    UINT primitiveCount,
    INT baseVertexIndex,
    UINT minVertexIndex,
    UINT numVertices,
    UINT startIndex,
    std::uint64_t directDispatchSnapshotToken,
    std::uint64_t sourceValueSnapshotToken,
    std::uint64_t liveIndexBindingSnapshotToken,
    std::uint64_t preDrawSnapshotToken) const noexcept {
    if (preDrawSnapshotToken == 0)
        return false;
    const auto current = indexed_pre_draw_readiness(
        expectedContext, expectedDevice, identity, cacheSnapshotToken,
        slotSnapshotToken, objectSnapshotToken, layout,
        inputLayoutSnapshotToken, constantStateSnapshotToken,
        constantPayloadSnapshotToken, constantBindingSnapshotToken,
        pipelineBindingSnapshotToken, primitiveType,
        topologyBindingSnapshotToken, vertexBuffer,
        vertexBufferSnapshotToken, vertexStride, vertexOffset,
        indexBuffer, indexBufferSnapshotToken, indexFormat, indexOffset,
        indexedGeometryBindingSnapshotToken, primitiveCount,
        baseVertexIndex, minVertexIndex, numVertices, startIndex,
        directDispatchSnapshotToken, sourceValueSnapshotToken,
        liveIndexBindingSnapshotToken);
    return current.ready && current.snapshotToken == preDrawSnapshotToken;
}

// R256 creates a common dormant draw-candidate receipt from exactly one
// already-sealed programmable branch. It does not re-route or issue a draw.
NativeProgrammableShaderDrawCandidateReadiness
compose_programmable_draw_candidate_readiness(
    const NativeProgrammableShaderNonIndexedDirectDispatchReadiness& dispatch,
    std::uint64_t dispatchSnapshotToken) noexcept {
    NativeProgrammableShaderDrawCandidateReadiness out{};
    out.kind = NativeProgrammableShaderDrawCandidateKind::NonIndexed;
    out.indexed = false;
    out.elementCount = dispatch.vertexCount;
    out.startLocation = dispatch.startVertexLocation;
    out.sourceReceiptSnapshotToken = dispatchSnapshotToken;
    out.inputValid = dispatchSnapshotToken != 0;
    out.selectedReceiptReady = dispatch.ready;
    out.selectedReceiptSnapshotMatches =
        dispatch.ready && dispatch.snapshotToken == dispatchSnapshotToken;
    out.componentSnapshotsPresent = dispatch.componentSnapshotsPresent;
    out.ready =
        out.inputValid &&
        out.selectedReceiptReady &&
        out.selectedReceiptSnapshotMatches &&
        out.componentSnapshotsPresent;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.kind));
        token = mix_readiness_snapshot_token(
            token, out.sourceReceiptSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.elementCount);
        token = mix_readiness_snapshot_token(token, out.startLocation);
        token = mix_readiness_snapshot_token(token, 0x256u);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

NativeProgrammableShaderDrawCandidateReadiness
compose_programmable_draw_candidate_readiness(
    const NativeProgrammableShaderIndexedPreDrawReadiness& preDraw,
    std::uint64_t preDrawSnapshotToken) noexcept {
    NativeProgrammableShaderDrawCandidateReadiness out{};
    out.kind = NativeProgrammableShaderDrawCandidateKind::Indexed;
    out.indexed = true;
    out.elementCount = preDraw.indexCount;
    out.startLocation = preDraw.startIndexLocation;
    out.baseVertexIndex = preDraw.baseVertexIndex;
    out.minVertexIndex = preDraw.minVertexIndex;
    out.numVertices = preDraw.numVertices;
    out.indexFormat = preDraw.indexFormat;
    out.indexOffset = preDraw.indexOffset;
    out.sourceReceiptSnapshotToken = preDrawSnapshotToken;
    out.inputValid = preDrawSnapshotToken != 0;
    out.selectedReceiptReady = preDraw.ready;
    out.selectedReceiptSnapshotMatches =
        preDraw.ready && preDraw.snapshotToken == preDrawSnapshotToken;
    out.componentSnapshotsPresent = preDraw.componentSnapshotsPresent;
    out.ready =
        out.inputValid &&
        out.selectedReceiptReady &&
        out.selectedReceiptSnapshotMatches &&
        out.componentSnapshotsPresent;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.kind));
        token = mix_readiness_snapshot_token(
            token, out.sourceReceiptSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.elementCount);
        token = mix_readiness_snapshot_token(token, out.startLocation);
        token = mix_readiness_snapshot_token(
            token,
            static_cast<std::uint64_t>(
                static_cast<std::int64_t>(out.baseVertexIndex)));
        token = mix_readiness_snapshot_token(token, out.minVertexIndex);
        token = mix_readiness_snapshot_token(token, out.numVertices);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.indexFormat));
        token = mix_readiness_snapshot_token(token, out.indexOffset);
        token = mix_readiness_snapshot_token(token, 0x256u);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_programmable_draw_candidate_snapshot(
    const NativeProgrammableShaderNonIndexedDirectDispatchReadiness& dispatch,
    std::uint64_t dispatchSnapshotToken,
    std::uint64_t candidateSnapshotToken) noexcept {
    if (candidateSnapshotToken == 0)
        return false;
    const auto current = compose_programmable_draw_candidate_readiness(
        dispatch, dispatchSnapshotToken);
    return current.ready && current.snapshotToken == candidateSnapshotToken;
}

bool validate_programmable_draw_candidate_snapshot(
    const NativeProgrammableShaderIndexedPreDrawReadiness& preDraw,
    std::uint64_t preDrawSnapshotToken,
    std::uint64_t candidateSnapshotToken) noexcept {
    if (candidateSnapshotToken == 0)
        return false;
    const auto current = compose_programmable_draw_candidate_readiness(
        preDraw, preDrawSnapshotToken);
    return current.ready && current.snapshotToken == candidateSnapshotToken;
}

namespace {

std::uint64_t recompute_programmable_draw_candidate_payload_snapshot(
    const NativeProgrammableShaderDrawCandidateReadiness& candidate) noexcept {
    if (candidate.kind == NativeProgrammableShaderDrawCandidateKind::None)
        return 0;

    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(
        token, static_cast<std::uint32_t>(candidate.kind));
    token = mix_readiness_snapshot_token(
        token, candidate.sourceReceiptSnapshotToken);
    token = mix_readiness_snapshot_token(token, candidate.elementCount);
    token = mix_readiness_snapshot_token(token, candidate.startLocation);
    if (candidate.kind == NativeProgrammableShaderDrawCandidateKind::Indexed) {
        token = mix_readiness_snapshot_token(
            token,
            static_cast<std::uint64_t>(
                static_cast<std::int64_t>(candidate.baseVertexIndex)));
        token = mix_readiness_snapshot_token(token, candidate.minVertexIndex);
        token = mix_readiness_snapshot_token(token, candidate.numVertices);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(candidate.indexFormat));
        token = mix_readiness_snapshot_token(token, candidate.indexOffset);
    }
    token = mix_readiness_snapshot_token(token, 0x256u);
    return token == 0 ? 1 : token;
}

} // namespace

NativeProgrammableShaderDormantPreActivationReadiness
compose_programmable_dormant_pre_activation_readiness(
    const NativeProgrammableShaderDrawCandidateReadiness& candidate,
    std::uint64_t candidateSnapshotToken) noexcept {
    NativeProgrammableShaderDormantPreActivationReadiness out{};
    out.kind = candidate.kind;
    out.indexed = candidate.indexed;
    out.elementCount = candidate.elementCount;
    out.startLocation = candidate.startLocation;
    out.baseVertexIndex = candidate.baseVertexIndex;
    out.minVertexIndex = candidate.minVertexIndex;
    out.numVertices = candidate.numVertices;
    out.indexFormat = candidate.indexFormat;
    out.indexOffset = candidate.indexOffset;
    out.sourceReceiptSnapshotToken = candidate.sourceReceiptSnapshotToken;
    out.candidateSnapshotToken = candidateSnapshotToken;

    out.inputValid = candidateSnapshotToken != 0;
    out.candidateReady = candidate.ready;
    out.candidateSnapshotMatches =
        candidate.ready && candidate.snapshotToken == candidateSnapshotToken;
    out.candidatePayloadSnapshotMatches =
        candidate.ready &&
        candidate.snapshotToken != 0 &&
        candidate.snapshotToken ==
            recompute_programmable_draw_candidate_payload_snapshot(candidate);
    out.candidateKindValid =
        (candidate.kind ==
             NativeProgrammableShaderDrawCandidateKind::NonIndexed &&
         !candidate.indexed &&
         candidate.baseVertexIndex == 0 &&
         candidate.minVertexIndex == 0u &&
         candidate.numVertices == 0u &&
         candidate.indexFormat == DXGI_FORMAT_UNKNOWN &&
         candidate.indexOffset == 0u) ||
        (candidate.kind ==
             NativeProgrammableShaderDrawCandidateKind::Indexed &&
         candidate.indexed &&
         candidate.indexFormat != DXGI_FORMAT_UNKNOWN);

    // R257 is a one-way dormant handoff. These flags are intentionally fixed
    // rather than caller-provided so a readiness receipt cannot be mistaken
    // for activation proof or execution authorization.
    out.diagnosticOnly = true;
    out.activationProofPresent = false;
    out.nativeDrawPathActivationAllowed = false;
    out.drawDispatchAuthorized = false;
    out.boundaryPreserved =
        out.diagnosticOnly &&
        !out.activationProofPresent &&
        !out.nativeDrawPathActivationAllowed &&
        !out.drawDispatchAuthorized;

    out.ready =
        out.inputValid &&
        out.candidateReady &&
        out.candidateSnapshotMatches &&
        out.candidatePayloadSnapshotMatches &&
        out.candidateKindValid &&
        out.boundaryPreserved;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.kind));
        token = mix_readiness_snapshot_token(token, out.indexed ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.sourceReceiptSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.candidateSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.elementCount);
        token = mix_readiness_snapshot_token(token, out.startLocation);
        token = mix_readiness_snapshot_token(
            token,
            static_cast<std::uint64_t>(
                static_cast<std::int64_t>(out.baseVertexIndex)));
        token = mix_readiness_snapshot_token(token, out.minVertexIndex);
        token = mix_readiness_snapshot_token(token, out.numVertices);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.indexFormat));
        token = mix_readiness_snapshot_token(token, out.indexOffset);
        token = mix_readiness_snapshot_token(token, 1u); // diagnosticOnly
        token = mix_readiness_snapshot_token(token, 0u); // activation proof
        token = mix_readiness_snapshot_token(token, 0u); // activation allowed
        token = mix_readiness_snapshot_token(token, 0u); // dispatch authorized
        token = mix_readiness_snapshot_token(token, 0x257u);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_programmable_dormant_pre_activation_snapshot(
    const NativeProgrammableShaderDrawCandidateReadiness& candidate,
    std::uint64_t candidateSnapshotToken,
    std::uint64_t preActivationSnapshotToken) noexcept {
    if (preActivationSnapshotToken == 0)
        return false;
    const auto current = compose_programmable_dormant_pre_activation_readiness(
        candidate, candidateSnapshotToken);
    return current.ready && current.snapshotToken == preActivationSnapshotToken;
}

namespace {

template <typename SourceReceipt>
NativeProgrammableShaderDormantSourceRevalidationReadiness
compose_programmable_dormant_source_revalidation_readiness(
    const SourceReceipt& sourceReceipt,
    std::uint64_t cacheKey,
    std::uint64_t candidateSnapshotToken,
    std::uint64_t preActivationSnapshotToken) noexcept {
    NativeProgrammableShaderDormantSourceRevalidationReadiness out{};
    out.cacheKey = cacheKey;
    out.inputValid =
        cacheKey != 0 &&
        candidateSnapshotToken != 0 && preActivationSnapshotToken != 0;
    out.sourceReceiptReady = sourceReceipt.ready;
    out.sourceReceiptSnapshotPresent = sourceReceipt.snapshotToken != 0;
    out.currentSourceReceiptSnapshotToken = sourceReceipt.snapshotToken;
    out.candidateSnapshotToken = candidateSnapshotToken;
    out.preActivationSnapshotToken = preActivationSnapshotToken;

    const auto candidate = compose_programmable_draw_candidate_readiness(
        sourceReceipt, sourceReceipt.snapshotToken);
    out.kind = candidate.kind;
    out.indexed = candidate.indexed;
    out.elementCount = candidate.elementCount;
    out.startLocation = candidate.startLocation;
    out.baseVertexIndex = candidate.baseVertexIndex;
    out.minVertexIndex = candidate.minVertexIndex;
    out.numVertices = candidate.numVertices;
    out.indexFormat = candidate.indexFormat;
    out.indexOffset = candidate.indexOffset;
    out.candidateReady = candidate.ready;
    out.candidateSnapshotMatches =
        candidate.ready && candidate.snapshotToken == candidateSnapshotToken;
    out.sourceLineageMatches =
        candidate.ready &&
        candidate.sourceReceiptSnapshotToken == sourceReceipt.snapshotToken;

    const auto preActivation =
        compose_programmable_dormant_pre_activation_readiness(
            candidate, candidate.snapshotToken);
    out.preActivationReady = preActivation.ready;
    out.preActivationSnapshotMatches =
        preActivation.ready &&
        preActivation.snapshotToken == preActivationSnapshotToken;
    out.candidateLineageMatches =
        preActivation.ready &&
        preActivation.candidateSnapshotToken == candidate.snapshotToken;
    out.boundaryPreserved =
        preActivation.boundaryPreserved &&
        preActivation.diagnosticOnly &&
        !preActivation.activationProofPresent &&
        !preActivation.nativeDrawPathActivationAllowed &&
        !preActivation.drawDispatchAuthorized;
    out.ready =
        out.inputValid &&
        out.sourceReceiptReady &&
        out.sourceReceiptSnapshotPresent &&
        out.candidateReady &&
        out.candidateSnapshotMatches &&
        out.preActivationReady &&
        out.preActivationSnapshotMatches &&
        out.sourceLineageMatches &&
        out.candidateLineageMatches &&
        out.boundaryPreserved;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.kind));
        token = mix_readiness_snapshot_token(token, out.indexed ? 1u : 0u);
        token = mix_readiness_snapshot_token(token, out.cacheKey);
        token = mix_readiness_snapshot_token(
            token, out.currentSourceReceiptSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.candidateSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.preActivationSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.elementCount);
        token = mix_readiness_snapshot_token(token, out.startLocation);
        token = mix_readiness_snapshot_token(
            token,
            static_cast<std::uint64_t>(
                static_cast<std::int64_t>(out.baseVertexIndex)));
        token = mix_readiness_snapshot_token(token, out.minVertexIndex);
        token = mix_readiness_snapshot_token(token, out.numVertices);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.indexFormat));
        token = mix_readiness_snapshot_token(token, out.indexOffset);
        token = mix_readiness_snapshot_token(token, 0x258u);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

std::uint64_t recompute_programmable_dormant_source_revalidation_payload_snapshot(
    const NativeProgrammableShaderDormantSourceRevalidationReadiness&
        sourceRevalidation) noexcept {
    if (sourceRevalidation.kind ==
        NativeProgrammableShaderDrawCandidateKind::None)
        return 0;

    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(
        token, static_cast<std::uint32_t>(sourceRevalidation.kind));
    token = mix_readiness_snapshot_token(
        token, sourceRevalidation.indexed ? 1u : 0u);
    token = mix_readiness_snapshot_token(token, sourceRevalidation.cacheKey);
    token = mix_readiness_snapshot_token(
        token, sourceRevalidation.currentSourceReceiptSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, sourceRevalidation.candidateSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, sourceRevalidation.preActivationSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, sourceRevalidation.elementCount);
    token = mix_readiness_snapshot_token(
        token, sourceRevalidation.startLocation);
    token = mix_readiness_snapshot_token(
        token,
        static_cast<std::uint64_t>(
            static_cast<std::int64_t>(
                sourceRevalidation.baseVertexIndex)));
    token = mix_readiness_snapshot_token(
        token, sourceRevalidation.minVertexIndex);
    token = mix_readiness_snapshot_token(
        token, sourceRevalidation.numVertices);
    token = mix_readiness_snapshot_token(
        token, static_cast<std::uint32_t>(sourceRevalidation.indexFormat));
    token = mix_readiness_snapshot_token(
        token, sourceRevalidation.indexOffset);
    token = mix_readiness_snapshot_token(token, 0x258u);
    return token == 0 ? 1 : token;
}

std::uint64_t recompute_programmable_resource_behavior_payload_snapshot(
    const NativeProgrammableShaderResourceBehaviorReadiness&
        geometryBehavior) noexcept {
    if (geometryBehavior.kind ==
        NativeProgrammableShaderDrawCandidateKind::None)
        return 0;

    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(
        token, static_cast<std::uint32_t>(geometryBehavior.kind));
    token = mix_readiness_snapshot_token(
        token, geometryBehavior.indexed ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, geometryBehavior.sourceRevalidationSnapshotToken);
    token = mix_readiness_snapshot_token(
        token,
        geometryBehavior.sourceRevalidationPayloadSnapshotMatches ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, geometryBehavior.vertexMirrorSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, geometryBehavior.indexMirrorSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, geometryBehavior.missingResourceScopeMask);
    token = mix_readiness_snapshot_token(token, 0x260u);
    return token == 0 ? 1 : token;
}

// R302 reconstructs the complete R261 review payload before R262 may consume
// its stored snapshot token. This keeps derived texture receipts fail-closed
// against in-memory payload drift without granting any activation authority.
std::uint64_t recompute_programmable_texture_resource_behavior_payload_snapshot(
    const NativeProgrammableShaderTextureResourceBehaviorReadiness&
        textureBehavior) noexcept {
    if (textureBehavior.kind ==
        NativeProgrammableShaderDrawCandidateKind::None)
        return 0;

    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(
        token, static_cast<std::uint32_t>(textureBehavior.kind));
    token = mix_readiness_snapshot_token(
        token, textureBehavior.indexed ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, textureBehavior.sourceRevalidationSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, textureBehavior.geometrySnapshotToken);
    token = mix_readiness_snapshot_token(
        token, textureBehavior.geometryPayloadSnapshotMatches ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, textureBehavior.requiredTextureMask);
    token = mix_readiness_snapshot_token(
        token, textureBehavior.textureStageSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, textureBehavior.missingResourceScopeMask);
    token = mix_readiness_snapshot_token(token, 0x261u);
    return token == 0 ? 1 : token;
}

} // namespace

NativeProgrammableShaderResourceBehaviorReadiness
compose_programmable_resource_behavior_readiness(
    const NativeProgrammableShaderDormantSourceRevalidationReadiness&
        sourceRevalidation,
    std::uint64_t sourceRevalidationSnapshotToken,
    ID3D11Device* expectedDevice,
    const NativeManagedBufferShadow& vertexMirror,
    std::uint64_t vertexMirrorSnapshotToken,
    const NativeManagedBufferShadow* indexMirror,
    std::uint64_t indexMirrorSnapshotToken) noexcept {
    NativeProgrammableShaderResourceBehaviorReadiness out{};
    constexpr std::uint32_t kGeometryScopeMissing = 1u << 0;
    constexpr std::uint32_t kTextureScopeMissing = 1u << 1;
    constexpr std::uint32_t kOutputScopeMissing = 1u << 2;

    out.kind = sourceRevalidation.kind;
    out.indexed = sourceRevalidation.indexed;
    out.indexMirrorRequired = out.indexed;
    out.sourceRevalidationSnapshotToken = sourceRevalidationSnapshotToken;
    out.vertexMirrorSnapshotToken = vertexMirrorSnapshotToken;
    out.indexMirrorSnapshotToken = indexMirrorSnapshotToken;

    const bool kindValid =
        (out.kind == NativeProgrammableShaderDrawCandidateKind::NonIndexed &&
         !out.indexed) ||
        (out.kind == NativeProgrammableShaderDrawCandidateKind::Indexed &&
         out.indexed);
    const bool indexInputsValid =
        out.indexMirrorRequired
            ? indexMirror != nullptr && indexMirrorSnapshotToken != 0
            : indexMirror == nullptr && indexMirrorSnapshotToken == 0;
    out.inputValid =
        kindValid &&
        expectedDevice != nullptr &&
        sourceRevalidationSnapshotToken != 0 &&
        vertexMirrorSnapshotToken != 0 &&
        indexInputsValid;

    out.sourceRevalidationReady =
        sourceRevalidation.ready &&
        sourceRevalidation.boundaryPreserved &&
        sourceRevalidation.snapshotToken != 0;
    out.sourceRevalidationSnapshotMatches =
        out.sourceRevalidationReady &&
        sourceRevalidation.snapshotToken ==
            sourceRevalidationSnapshotToken;
    out.sourceRevalidationPayloadSnapshotMatches =
        out.sourceRevalidationReady &&
        sourceRevalidation.snapshotToken ==
            recompute_programmable_dormant_source_revalidation_payload_snapshot(
                sourceRevalidation);

    const auto vertex = vertexMirror.mirror_readiness(expectedDevice);
    out.vertexMirrorReady =
        vertex.ready &&
        vertex.role == ResourceRole::Vertex &&
        vertex.shadowValid &&
        vertex.lifetimeCurrent &&
        vertex.descriptorExact &&
        vertex.mutationPlanExact;
    out.vertexMirrorSnapshotMatches =
        out.vertexMirrorReady &&
        vertex.snapshotToken == vertexMirrorSnapshotToken &&
        vertexMirror.validate_mirror_readiness_snapshot(
            expectedDevice, vertexMirrorSnapshotToken);

    if (out.indexMirrorRequired && indexMirror) {
        const auto index = indexMirror->mirror_readiness(expectedDevice);
        out.indexMirrorReady =
            index.ready &&
            index.role == ResourceRole::Index &&
            index.shadowValid &&
            index.lifetimeCurrent &&
            index.descriptorExact &&
            index.mutationPlanExact;
        out.indexMirrorSnapshotMatches =
            out.indexMirrorReady &&
            index.snapshotToken == indexMirrorSnapshotToken &&
            indexMirror->validate_mirror_readiness_snapshot(
                expectedDevice, indexMirrorSnapshotToken);
    } else if (!out.indexMirrorRequired) {
        out.indexMirrorReady = true;
        out.indexMirrorSnapshotMatches = true;
    }

    out.geometryResourceBehaviorExact =
        out.sourceRevalidationPayloadSnapshotMatches &&
        out.vertexMirrorReady &&
        out.vertexMirrorSnapshotMatches &&
        out.indexMirrorReady &&
        out.indexMirrorSnapshotMatches;

    // R260 deliberately closes only the geometry portion of F18. The current
    // dormant programmable candidate does not yet carry equivalent exact
    // texture/output behavior receipts, so those scopes remain fail-closed.
    out.textureResourceBehaviorProofPresent = false;
    out.outputResourceBehaviorProofPresent = false;
    out.missingResourceScopeMask = 0;
    if (!out.geometryResourceBehaviorExact)
        out.missingResourceScopeMask |= kGeometryScopeMissing;
    if (!out.textureResourceBehaviorProofPresent)
        out.missingResourceScopeMask |= kTextureScopeMissing;
    if (!out.outputResourceBehaviorProofPresent)
        out.missingResourceScopeMask |= kOutputScopeMissing;
    out.fullResourceBehaviorProofPresent =
        out.missingResourceScopeMask == 0;

    out.diagnosticOnly = true;
    out.boundaryPreserved =
        sourceRevalidation.boundaryPreserved &&
        out.sourceRevalidationPayloadSnapshotMatches &&
        out.diagnosticOnly &&
        !out.fullResourceBehaviorProofPresent &&
        out.missingResourceScopeMask != 0;
    out.reviewReady =
        out.inputValid &&
        out.sourceRevalidationReady &&
        out.sourceRevalidationSnapshotMatches &&
        out.geometryResourceBehaviorExact &&
        out.boundaryPreserved;

    if (out.reviewReady) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.kind));
        token = mix_readiness_snapshot_token(token, out.indexed ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.sourceRevalidationSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.sourceRevalidationPayloadSnapshotMatches ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.vertexMirrorSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.indexMirrorSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.missingResourceScopeMask);
        token = mix_readiness_snapshot_token(token, 0x260u);
        out.reviewSnapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_programmable_resource_behavior_readiness_snapshot(
    const NativeProgrammableShaderDormantSourceRevalidationReadiness&
        sourceRevalidation,
    std::uint64_t sourceRevalidationSnapshotToken,
    ID3D11Device* expectedDevice,
    const NativeManagedBufferShadow& vertexMirror,
    std::uint64_t vertexMirrorSnapshotToken,
    const NativeManagedBufferShadow* indexMirror,
    std::uint64_t indexMirrorSnapshotToken,
    std::uint64_t reviewSnapshotToken) noexcept {
    if (reviewSnapshotToken == 0)
        return false;
    const auto current = compose_programmable_resource_behavior_readiness(
        sourceRevalidation, sourceRevalidationSnapshotToken,
        expectedDevice, vertexMirror, vertexMirrorSnapshotToken,
        indexMirror, indexMirrorSnapshotToken);
    return current.reviewReady &&
        current.reviewSnapshotToken == reviewSnapshotToken &&
        current.geometryResourceBehaviorExact &&
        !current.fullResourceBehaviorProofPresent &&
        current.missingResourceScopeMask != 0;
}

NativeProgrammableShaderTextureResourceBehaviorReadiness
compose_programmable_texture_resource_behavior_readiness(
    const NativeProgrammableShaderResourceBehaviorReadiness& geometryBehavior,
    std::uint64_t geometrySnapshotToken,
    const NativeManagedTextureRegistry& textureRegistry,
    const void* const* textureKeys,
    std::size_t textureCount,
    ID3D11Device* expectedDevice,
    const NativeManagedTextureStageReadiness& textureStages,
    std::uint64_t textureStageSnapshotToken) noexcept {
    NativeProgrammableShaderTextureResourceBehaviorReadiness out{};
    constexpr std::uint32_t kGeometryScopeMissing = 1u << 0;
    constexpr std::uint32_t kTextureScopeMissing = 1u << 1;
    constexpr std::uint32_t kOutputScopeMissing = 1u << 2;

    out.kind = geometryBehavior.kind;
    out.indexed = geometryBehavior.indexed;
    out.requiredTextureMask = textureStages.requiredMask;
    out.readyTextureMask = textureStages.readyMask;
    out.pendingTextureMask = textureStages.pendingMask;
    out.sourceRevalidationSnapshotToken =
        geometryBehavior.sourceRevalidationSnapshotToken;
    out.geometrySnapshotToken = geometrySnapshotToken;
    out.textureStageSnapshotToken = textureStageSnapshotToken;

    out.inputValid =
        geometrySnapshotToken != 0 &&
        textureStageSnapshotToken != 0 &&
        expectedDevice != nullptr;
    out.geometryReviewReady =
        geometryBehavior.reviewReady &&
        geometryBehavior.boundaryPreserved &&
        geometryBehavior.geometryResourceBehaviorExact &&
        geometryBehavior.reviewSnapshotToken != 0;
    out.geometrySnapshotMatches =
        out.geometryReviewReady &&
        geometryBehavior.reviewSnapshotToken == geometrySnapshotToken;
    out.geometryPayloadSnapshotMatches =
        out.geometryReviewReady &&
        geometryBehavior.reviewSnapshotToken ==
            recompute_programmable_resource_behavior_payload_snapshot(
                geometryBehavior);

    out.requiredTextureScopePresent = textureStages.requiredMask != 0;
    out.textureStagesInputValid = textureStages.inputValid;
    const bool allMasksExact =
        textureStages.registeredMask == textureStages.requiredMask &&
        textureStages.shadowValidMask == textureStages.requiredMask &&
        textureStages.resourcesOwnedMask == textureStages.requiredMask &&
        textureStages.lifetimeCurrentMask == textureStages.requiredMask &&
        textureStages.deviceMatchesMask == textureStages.requiredMask &&
        textureStages.descriptorExactMask == textureStages.requiredMask &&
        textureStages.readyMask == textureStages.requiredMask &&
        textureStages.pendingMask == 0;
    out.textureStageSnapshotMatches =
        out.requiredTextureScopePresent &&
        out.textureStagesInputValid &&
        textureStages.allRequiredReady &&
        allMasksExact &&
        textureStages.snapshotToken != 0 &&
        textureStages.snapshotToken == textureStageSnapshotToken &&
        textureRegistry.validate_mirror_readiness_snapshot_for_stages(
            textureKeys, textureCount, textureStages.requiredMask,
            expectedDevice, textureStageSnapshotToken);

    out.geometryResourceBehaviorExact =
        out.geometryReviewReady &&
        out.geometrySnapshotMatches &&
        out.geometryPayloadSnapshotMatches;
    out.textureResourceBehaviorExact =
        out.textureStageSnapshotMatches;

    // R261 deliberately leaves output-resource behavior unproven. It also
    // treats the required texture mask as an explicit caller-supplied scope;
    // F21 remains responsible for shader semantic translation/readiness.
    out.outputResourceBehaviorProofPresent = false;
    out.missingResourceScopeMask = 0;
    if (!out.geometryResourceBehaviorExact)
        out.missingResourceScopeMask |= kGeometryScopeMissing;
    if (!out.textureResourceBehaviorExact)
        out.missingResourceScopeMask |= kTextureScopeMissing;
    if (!out.outputResourceBehaviorProofPresent)
        out.missingResourceScopeMask |= kOutputScopeMissing;
    out.fullResourceBehaviorProofPresent =
        out.missingResourceScopeMask == 0;

    out.diagnosticOnly = true;
    out.boundaryPreserved =
        geometryBehavior.boundaryPreserved &&
        out.geometryPayloadSnapshotMatches &&
        out.diagnosticOnly &&
        !out.fullResourceBehaviorProofPresent &&
        out.missingResourceScopeMask != 0;
    out.reviewReady =
        out.inputValid &&
        out.geometryReviewReady &&
        out.geometrySnapshotMatches &&
        out.geometryPayloadSnapshotMatches &&
        out.textureResourceBehaviorExact &&
        out.boundaryPreserved;

    if (out.reviewReady) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.kind));
        token = mix_readiness_snapshot_token(token, out.indexed ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.sourceRevalidationSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.geometrySnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.geometryPayloadSnapshotMatches ? 1u : 0u);
        token = mix_readiness_snapshot_token(token, out.requiredTextureMask);
        token = mix_readiness_snapshot_token(
            token, out.textureStageSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.missingResourceScopeMask);
        token = mix_readiness_snapshot_token(token, 0x261u);
        out.reviewSnapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_programmable_texture_resource_behavior_readiness_snapshot(
    const NativeProgrammableShaderResourceBehaviorReadiness& geometryBehavior,
    std::uint64_t geometrySnapshotToken,
    const NativeManagedTextureRegistry& textureRegistry,
    const void* const* textureKeys,
    std::size_t textureCount,
    ID3D11Device* expectedDevice,
    const NativeManagedTextureStageReadiness& textureStages,
    std::uint64_t textureStageSnapshotToken,
    std::uint64_t reviewSnapshotToken) noexcept {
    if (reviewSnapshotToken == 0)
        return false;
    const auto current =
        compose_programmable_texture_resource_behavior_readiness(
            geometryBehavior, geometrySnapshotToken,
            textureRegistry, textureKeys, textureCount, expectedDevice,
            textureStages, textureStageSnapshotToken);
    return current.reviewReady &&
        current.reviewSnapshotToken == reviewSnapshotToken &&
        current.geometryResourceBehaviorExact &&
        current.textureResourceBehaviorExact &&
        !current.outputResourceBehaviorProofPresent &&
        !current.fullResourceBehaviorProofPresent &&
        current.missingResourceScopeMask == (1u << 2);
}

NativeProgrammableShaderOutputResourceBehaviorReadiness
compose_programmable_output_resource_behavior_readiness(
    const NativeProgrammableShaderTextureResourceBehaviorReadiness& textureBehavior,
    std::uint64_t textureBehaviorSnapshotToken,
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const NativeSurfacePairReadiness& surfacePair,
    std::uint64_t surfacePairSnapshotToken,
    const NativeSurfacePairBinding& surfaceBinding,
    const NativeSurfaceMirror& colorSurface,
    const NativeSurfaceMirror& depthSurface,
    std::uint64_t surfaceBindingSnapshotToken) noexcept {
    NativeProgrammableShaderOutputResourceBehaviorReadiness out{};
    constexpr std::uint32_t kGeometryScopeMissing = 1u << 0;
    constexpr std::uint32_t kTextureScopeMissing = 1u << 1;
    constexpr std::uint32_t kOutputScopeMissing = 1u << 2;

    out.kind = textureBehavior.kind;
    out.indexed = textureBehavior.indexed;
    out.sourceRevalidationSnapshotToken =
        textureBehavior.sourceRevalidationSnapshotToken;
    out.textureBehaviorSnapshotToken = textureBehaviorSnapshotToken;
    out.surfacePairSnapshotToken = surfacePairSnapshotToken;
    out.surfaceBindingSnapshotToken = surfaceBindingSnapshotToken;

    out.inputValid =
        textureBehaviorSnapshotToken != 0 &&
        expectedContext != nullptr &&
        expectedDevice != nullptr &&
        surfacePairSnapshotToken != 0 &&
        surfaceBindingSnapshotToken != 0;
    out.textureReviewReady =
        textureBehavior.reviewReady &&
        textureBehavior.boundaryPreserved &&
        textureBehavior.geometryResourceBehaviorExact &&
        textureBehavior.textureResourceBehaviorExact &&
        !textureBehavior.outputResourceBehaviorProofPresent &&
        !textureBehavior.fullResourceBehaviorProofPresent &&
        textureBehavior.missingResourceScopeMask == kOutputScopeMissing &&
        textureBehavior.reviewSnapshotToken != 0;
    out.textureSnapshotMatches =
        out.textureReviewReady &&
        textureBehavior.reviewSnapshotToken ==
            textureBehaviorSnapshotToken;
    out.texturePayloadSnapshotMatches =
        out.textureReviewReady &&
        textureBehavior.reviewSnapshotToken ==
            recompute_programmable_texture_resource_behavior_payload_snapshot(
                textureBehavior);

    out.surfacePairReady =
        surfacePair.ready &&
        surfacePair.snapshotToken != 0 &&
        validate_surface_pair_snapshot(
            expectedDevice, colorSurface, depthSurface,
            surfacePair.snapshotToken);
    out.surfacePairSnapshotMatches =
        out.surfacePairReady &&
        surfacePair.snapshotToken == surfacePairSnapshotToken;

    const auto liveBinding = surfaceBinding.binding_readiness(
        expectedContext, colorSurface, depthSurface);
    out.surfaceBindingReady =
        liveBinding.ready &&
        liveBinding.surfacePairSnapshotToken == surfacePair.snapshotToken &&
        surfaceBinding.surface_pair_snapshot_token() ==
            surfacePair.snapshotToken;
    out.surfaceBindingSnapshotMatches =
        out.surfaceBindingReady &&
        liveBinding.snapshotToken == surfaceBindingSnapshotToken &&
        surfaceBinding.validate_binding_snapshot(
            expectedContext, colorSurface, depthSurface,
            surfaceBindingSnapshotToken);

    out.geometryResourceBehaviorExact =
        out.textureReviewReady &&
        out.textureSnapshotMatches &&
        out.texturePayloadSnapshotMatches &&
        textureBehavior.geometryResourceBehaviorExact;
    out.textureResourceBehaviorExact =
        out.textureReviewReady &&
        out.textureSnapshotMatches &&
        out.texturePayloadSnapshotMatches &&
        textureBehavior.textureResourceBehaviorExact;
    out.outputResourceBehaviorExact =
        out.surfacePairReady &&
        out.surfacePairSnapshotMatches &&
        out.surfaceBindingReady &&
        out.surfaceBindingSnapshotMatches;

    out.missingResourceScopeMask = 0;
    if (!out.geometryResourceBehaviorExact)
        out.missingResourceScopeMask |= kGeometryScopeMissing;
    if (!out.textureResourceBehaviorExact)
        out.missingResourceScopeMask |= kTextureScopeMissing;
    if (!out.outputResourceBehaviorExact)
        out.missingResourceScopeMask |= kOutputScopeMissing;
    out.fullResourceBehaviorProofPresent =
        out.missingResourceScopeMask == 0;

    out.diagnosticOnly = true;
    out.boundaryPreserved =
        textureBehavior.boundaryPreserved &&
        out.texturePayloadSnapshotMatches &&
        out.diagnosticOnly &&
        out.fullResourceBehaviorProofPresent;
    out.reviewReady =
        out.inputValid &&
        out.textureReviewReady &&
        out.textureSnapshotMatches &&
        out.texturePayloadSnapshotMatches &&
        out.fullResourceBehaviorProofPresent &&
        out.boundaryPreserved;

    if (out.reviewReady) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.kind));
        token = mix_readiness_snapshot_token(token, out.indexed ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.sourceRevalidationSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.textureBehaviorSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.texturePayloadSnapshotMatches ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.surfacePairSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.surfaceBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.missingResourceScopeMask);
        token = mix_readiness_snapshot_token(token, 0x262u);
        out.reviewSnapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_programmable_output_resource_behavior_readiness_snapshot(
    const NativeProgrammableShaderTextureResourceBehaviorReadiness& textureBehavior,
    std::uint64_t textureBehaviorSnapshotToken,
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const NativeSurfacePairReadiness& surfacePair,
    std::uint64_t surfacePairSnapshotToken,
    const NativeSurfacePairBinding& surfaceBinding,
    const NativeSurfaceMirror& colorSurface,
    const NativeSurfaceMirror& depthSurface,
    std::uint64_t surfaceBindingSnapshotToken,
    std::uint64_t reviewSnapshotToken) noexcept {
    if (reviewSnapshotToken == 0)
        return false;
    const auto current =
        compose_programmable_output_resource_behavior_readiness(
            textureBehavior, textureBehaviorSnapshotToken,
            expectedContext, expectedDevice,
            surfacePair, surfacePairSnapshotToken,
            surfaceBinding, colorSurface, depthSurface,
            surfaceBindingSnapshotToken);
    return current.reviewReady &&
        current.reviewSnapshotToken == reviewSnapshotToken &&
        current.geometryResourceBehaviorExact &&
        current.textureResourceBehaviorExact &&
        current.outputResourceBehaviorExact &&
        current.fullResourceBehaviorProofPresent &&
        current.missingResourceScopeMask == 0;
}

NativeProgrammableShaderSourceMappingHandoff
compose_programmable_shader_source_mapping_handoff(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const ProgrammableShaderPairSourceSemanticEvidence& sourceReceipt,
    const ProgrammableShaderRegisterMappingPlanEvidence& mappingPlan) noexcept {
    NativeProgrammableShaderSourceMappingHandoff out{};

    out.cacheKey = mappingPlan.cacheKey;
    out.pairSemanticHash = mappingPlan.pairSemanticHash;
    out.vertexRegisterSemanticsHash =
        mappingPlan.vertexRegisterSemanticsHash;
    out.pixelRegisterSemanticsHash =
        mappingPlan.pixelRegisterSemanticsHash;
    out.constantMappingHash = mappingPlan.constantMappingHash;
    out.samplerMappingHash = mappingPlan.samplerMappingHash;
    out.mappingPlanRevisionHash = mappingPlan.planRevisionHash;
    out.mappingSemanticContractHash = mappingPlan.semanticContractHash;

    out.inputValid =
        sourceReceipt.exact() &&
        mappingPlan.exact();
    out.sourceIdentityExact =
        sourceIdentity.exact_identity() &&
        !sourceIdentity.translationImplemented;
    out.sourceSemanticReceiptExact = sourceReceipt.exact();
    out.mappingPlanExact = mappingPlan.exact();

    out.sourceReceiptIdentityMatches =
        out.sourceIdentityExact &&
        sourceReceipt.cacheKey == sourceIdentity.cacheKey &&
        sourceReceipt.vertexVersionToken ==
            sourceIdentity.vertexShader.versionToken &&
        sourceReceipt.pixelVersionToken ==
            sourceIdentity.pixelShader.versionToken &&
        sourceReceipt.vertexSourceBytecodeHash ==
            sourceIdentity.vertexShader.bytecodeHash &&
        sourceReceipt.pixelSourceBytecodeHash ==
            sourceIdentity.pixelShader.bytecodeHash;

    out.mappingPlanIdentityMatches =
        out.sourceSemanticReceiptExact &&
        out.mappingPlanExact &&
        mappingPlan.cacheKey == sourceReceipt.cacheKey &&
        mappingPlan.pairSemanticHash == sourceReceipt.pairSemanticHash &&
        mappingPlan.vertexRegisterSemanticsHash ==
            sourceReceipt.vertexRegisterSemanticsHash &&
        mappingPlan.pixelRegisterSemanticsHash ==
            sourceReceipt.pixelRegisterSemanticsHash;

    out.constantRegisterMappingExact =
        out.mappingPlanIdentityMatches &&
        mappingPlan.constantRegisterMappingExact &&
        mappingPlan.constantMappingHash != 0;
    out.samplerMappingExact =
        out.mappingPlanIdentityMatches &&
        mappingPlan.samplerMappingExact &&
        mappingPlan.samplerMappingHash != 0;

    out.diagnosticOnly = true;
    out.boundaryPreserved =
        out.sourceReceiptIdentityMatches &&
        out.mappingPlanIdentityMatches &&
        out.constantRegisterMappingExact &&
        out.samplerMappingExact &&
        out.diagnosticOnly;
    out.reviewReady =
        out.inputValid &&
        out.boundaryPreserved;

    if (out.reviewReady) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(token, out.cacheKey);
        token = mix_readiness_snapshot_token(token, out.pairSemanticHash);
        token = mix_readiness_snapshot_token(
            token, out.vertexRegisterSemanticsHash);
        token = mix_readiness_snapshot_token(
            token, out.pixelRegisterSemanticsHash);
        token = mix_readiness_snapshot_token(token, out.constantMappingHash);
        token = mix_readiness_snapshot_token(token, out.samplerMappingHash);
        token = mix_readiness_snapshot_token(
            token, out.mappingPlanRevisionHash);
        token = mix_readiness_snapshot_token(
            token, out.mappingSemanticContractHash);
        token = mix_readiness_snapshot_token(token, 0x273u);
        out.reviewSnapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_programmable_shader_source_mapping_handoff_snapshot(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const ProgrammableShaderPairSourceSemanticEvidence& sourceReceipt,
    const ProgrammableShaderRegisterMappingPlanEvidence& mappingPlan,
    std::uint64_t reviewSnapshotToken) noexcept {
    if (reviewSnapshotToken == 0)
        return false;
    const auto current =
        compose_programmable_shader_source_mapping_handoff(
            sourceIdentity, sourceReceipt, mappingPlan);
    return current.reviewReady &&
        current.reviewSnapshotToken == reviewSnapshotToken &&
        current.sourceReceiptIdentityMatches &&
        current.mappingPlanIdentityMatches &&
        current.constantRegisterMappingExact &&
        current.samplerMappingExact;
}

NativeProgrammableShaderSemanticTranslationPlanEvidence
derive_programmable_shader_semantic_translation_plan(
    const ProgrammableShaderPairSourceSemanticEvidence& sourceReceipt,
    const ProgrammableShaderInterfaceLinkageEvidence& sourceInterfaceLinkage,
    const NativeProgrammableShaderSourceMappingHandoff& sourceMappingHandoff,
    std::uint64_t sourceMappingHandoffSnapshotToken) noexcept {
    NativeProgrammableShaderSemanticTranslationPlanEvidence out{};

    out.cacheKey = sourceReceipt.cacheKey;
    out.sourcePairSemanticHash = sourceReceipt.pairSemanticHash;
    out.interfaceLinkHash = sourceInterfaceLinkage.interfaceLinkHash;
    out.sourceConstantMappingHash = sourceMappingHandoff.constantMappingHash;
    out.sourceSamplerMappingHash = sourceMappingHandoff.samplerMappingHash;
    out.sourceMappingHandoffSnapshotToken = sourceMappingHandoffSnapshotToken;

    out.inputValid = sourceMappingHandoffSnapshotToken != 0;
    out.sourceSemanticReceiptExact = sourceReceipt.exact();
    out.interfaceLinkageExact = sourceInterfaceLinkage.exact();
    out.sourceMappingHandoffReady =
        sourceMappingHandoff.reviewReady &&
        sourceMappingHandoff.boundaryPreserved &&
        sourceMappingHandoff.diagnosticOnly &&
        sourceMappingHandoff.sourceReceiptIdentityMatches &&
        sourceMappingHandoff.mappingPlanIdentityMatches &&
        sourceMappingHandoff.constantRegisterMappingExact &&
        sourceMappingHandoff.samplerMappingExact &&
        sourceMappingHandoff.reviewSnapshotToken != 0;
    out.sourceMappingHandoffSnapshotMatches =
        out.sourceMappingHandoffReady &&
        sourceMappingHandoff.reviewSnapshotToken ==
            sourceMappingHandoffSnapshotToken;

    out.provenanceMatches =
        out.sourceSemanticReceiptExact &&
        out.interfaceLinkageExact &&
        out.sourceMappingHandoffSnapshotMatches &&
        sourceReceipt.cacheKey != 0 &&
        sourceReceipt.cacheKey == sourceMappingHandoff.cacheKey &&
        sourceReceipt.pairSemanticHash != 0 &&
        sourceReceipt.pairSemanticHash ==
            sourceMappingHandoff.pairSemanticHash &&
        sourceReceipt.vertexRegisterSemanticsHash ==
            sourceMappingHandoff.vertexRegisterSemanticsHash &&
        sourceReceipt.pixelRegisterSemanticsHash ==
            sourceMappingHandoff.pixelRegisterSemanticsHash &&
        sourceReceipt.interfaceLinkHash != 0 &&
        sourceReceipt.interfaceLinkHash ==
            sourceInterfaceLinkage.interfaceLinkHash &&
        sourceReceipt.vertexVersionToken ==
            sourceInterfaceLinkage.vertexVersionToken &&
        sourceReceipt.pixelVersionToken ==
            sourceInterfaceLinkage.pixelVersionToken &&
        sourceReceipt.vertexSourceBytecodeHash ==
            sourceInterfaceLinkage.vertexSourceBytecodeHash &&
        sourceReceipt.pixelSourceBytecodeHash ==
            sourceInterfaceLinkage.pixelSourceBytecodeHash;

    static constexpr char kTranslatorRevision[] =
        "R276_D3D9_SOURCE_DERIVED_SEMANTIC_TRANSLATION_PLAN_V1";
    static constexpr char kSemanticContract[] =
        "R276_R271_R268_R273_TARGET_SEMANTIC_IDENTITY_V1";
    const auto hash_literal =
        [](const char* bytes, std::size_t size) noexcept -> std::uint64_t
    {
        std::uint64_t hash = 1469598103934665603ull;
        for (std::size_t i = 0; i < size; ++i)
        {
            hash ^= static_cast<std::uint8_t>(bytes[i]);
            hash *= 1099511628211ull;
        }
        return hash == 0 ? 1 : hash;
    };
    out.translatorRevisionHash =
        hash_literal(kTranslatorRevision, sizeof(kTranslatorRevision) - 1u);
    out.semanticContractHash =
        hash_literal(kSemanticContract, sizeof(kSemanticContract) - 1u);

    if (out.provenanceMatches) {
        std::uint64_t vertexHash = 0xcbf29ce484222325ull;
        vertexHash = mix_readiness_snapshot_token(
            vertexHash, out.sourcePairSemanticHash);
        vertexHash = mix_readiness_snapshot_token(
            vertexHash, sourceReceipt.vertexRegisterSemanticsHash);
        vertexHash = mix_readiness_snapshot_token(
            vertexHash, out.interfaceLinkHash);
        vertexHash = mix_readiness_snapshot_token(
            vertexHash, out.sourceConstantMappingHash);
        vertexHash = mix_readiness_snapshot_token(
            vertexHash, out.sourceSamplerMappingHash);
        vertexHash = mix_readiness_snapshot_token(
            vertexHash, out.translatorRevisionHash);
        vertexHash = mix_readiness_snapshot_token(
            vertexHash, out.semanticContractHash);
        vertexHash = mix_readiness_snapshot_token(vertexHash, 0x5653u);
        out.targetVertexSemanticHash =
            vertexHash == 0 ? 1 : vertexHash;

        std::uint64_t pixelHash = 0xcbf29ce484222325ull;
        pixelHash = mix_readiness_snapshot_token(
            pixelHash, out.sourcePairSemanticHash);
        pixelHash = mix_readiness_snapshot_token(
            pixelHash, sourceReceipt.pixelRegisterSemanticsHash);
        pixelHash = mix_readiness_snapshot_token(
            pixelHash, out.interfaceLinkHash);
        pixelHash = mix_readiness_snapshot_token(
            pixelHash, out.sourceConstantMappingHash);
        pixelHash = mix_readiness_snapshot_token(
            pixelHash, out.sourceSamplerMappingHash);
        pixelHash = mix_readiness_snapshot_token(
            pixelHash, out.translatorRevisionHash);
        pixelHash = mix_readiness_snapshot_token(
            pixelHash, out.semanticContractHash);
        pixelHash = mix_readiness_snapshot_token(pixelHash, 0x5053u);
        out.targetPixelSemanticHash =
            pixelHash == 0 ? 1 : pixelHash;
    }

    out.vertexSemanticExact =
        out.provenanceMatches && out.targetVertexSemanticHash != 0;
    out.pixelSemanticExact =
        out.provenanceMatches && out.targetPixelSemanticHash != 0;
    out.diagnosticOnly = true;
    out.boundaryPreserved =
        out.provenanceMatches &&
        out.vertexSemanticExact &&
        out.pixelSemanticExact &&
        out.translatorRevisionHash != 0 &&
        out.semanticContractHash != 0 &&
        out.diagnosticOnly;
    out.reviewReady = out.inputValid && out.boundaryPreserved;

    if (out.reviewReady) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(token, out.cacheKey);
        token = mix_readiness_snapshot_token(
            token, out.sourcePairSemanticHash);
        token = mix_readiness_snapshot_token(token, out.interfaceLinkHash);
        token = mix_readiness_snapshot_token(
            token, out.sourceConstantMappingHash);
        token = mix_readiness_snapshot_token(
            token, out.sourceSamplerMappingHash);
        token = mix_readiness_snapshot_token(
            token, out.targetVertexSemanticHash);
        token = mix_readiness_snapshot_token(
            token, out.targetPixelSemanticHash);
        token = mix_readiness_snapshot_token(
            token, out.translatorRevisionHash);
        token = mix_readiness_snapshot_token(token, out.semanticContractHash);
        token = mix_readiness_snapshot_token(
            token, out.sourceMappingHandoffSnapshotToken);
        token = mix_readiness_snapshot_token(token, 0x276u);
        out.reviewSnapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_programmable_shader_semantic_translation_plan_snapshot(
    const NativeProgrammableShaderSemanticTranslationPlanEvidence& plan,
    std::uint64_t reviewSnapshotToken) noexcept {
    if (reviewSnapshotToken == 0 ||
        !plan.reviewReady ||
        !plan.boundaryPreserved ||
        !plan.provenanceMatches ||
        !plan.vertexSemanticExact ||
        !plan.pixelSemanticExact)
        return false;

    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(token, plan.cacheKey);
    token = mix_readiness_snapshot_token(
        token, plan.sourcePairSemanticHash);
    token = mix_readiness_snapshot_token(token, plan.interfaceLinkHash);
    token = mix_readiness_snapshot_token(
        token, plan.sourceConstantMappingHash);
    token = mix_readiness_snapshot_token(
        token, plan.sourceSamplerMappingHash);
    token = mix_readiness_snapshot_token(
        token, plan.targetVertexSemanticHash);
    token = mix_readiness_snapshot_token(
        token, plan.targetPixelSemanticHash);
    token = mix_readiness_snapshot_token(
        token, plan.translatorRevisionHash);
    token = mix_readiness_snapshot_token(token, plan.semanticContractHash);
    token = mix_readiness_snapshot_token(
        token, plan.sourceMappingHandoffSnapshotToken);
    token = mix_readiness_snapshot_token(token, 0x276u);
    const auto expected = token == 0 ? 1 : token;
    return plan.reviewSnapshotToken == reviewSnapshotToken &&
        expected == reviewSnapshotToken;
}

NativeProgrammableShaderTranslationObjectPrerequisiteEvidence
derive_programmable_shader_translation_object_prerequisite(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence& translationPlan,
    std::uint64_t translationPlanSnapshotToken) noexcept {
    NativeProgrammableShaderTranslationObjectPrerequisiteEvidence out{};

    out.cacheKey = sourceIdentity.cacheKey;
    out.targetVertexSemanticHash =
        translationPlan.targetVertexSemanticHash;
    out.targetPixelSemanticHash =
        translationPlan.targetPixelSemanticHash;
    out.translationPlanSnapshotToken = translationPlanSnapshotToken;

    out.inputValid = translationPlanSnapshotToken != 0;
    out.sourceIdentityExact =
        sourceIdentity.exact_identity() &&
        !sourceIdentity.translationImplemented;
    out.translationPlanReady =
        translationPlan.reviewReady &&
        translationPlan.boundaryPreserved &&
        translationPlan.diagnosticOnly &&
        translationPlan.provenanceMatches &&
        translationPlan.vertexSemanticExact &&
        translationPlan.pixelSemanticExact &&
        translationPlan.reviewSnapshotToken != 0;
    out.translationPlanSnapshotMatches =
        out.translationPlanReady &&
        translationPlan.reviewSnapshotToken ==
            translationPlanSnapshotToken;
    out.cacheIdentityMatches =
        out.sourceIdentityExact &&
        out.translationPlanSnapshotMatches &&
        sourceIdentity.cacheKey != 0 &&
        sourceIdentity.cacheKey == translationPlan.cacheKey &&
        translationPlan.targetVertexSemanticHash != 0 &&
        translationPlan.targetPixelSemanticHash != 0;

    // These booleans describe mandatory R240/R241/R242 lifetime evidence.
    // They are requirements, not claims that those generations/objects exist.
    out.cacheOwnerGenerationRequired = out.cacheIdentityMatches;
    out.translationSlotGenerationRequired = out.cacheIdentityMatches;
    out.translationObjectReceiptGenerationRequired =
        out.cacheIdentityMatches;
    out.sameDeviceObjectPairRequired = out.cacheIdentityMatches;
    out.cacheSnapshotRequired = out.cacheIdentityMatches;
    out.slotSnapshotRequired = out.cacheIdentityMatches;
    out.diagnosticOnly = true;
    out.boundaryPreserved =
        out.cacheIdentityMatches &&
        out.cacheOwnerGenerationRequired &&
        out.translationSlotGenerationRequired &&
        out.translationObjectReceiptGenerationRequired &&
        out.sameDeviceObjectPairRequired &&
        out.cacheSnapshotRequired &&
        out.slotSnapshotRequired &&
        out.diagnosticOnly;
    out.reviewReady =
        out.inputValid &&
        out.boundaryPreserved;

    if (out.reviewReady) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(token, out.cacheKey);
        token = mix_readiness_snapshot_token(
            token, out.targetVertexSemanticHash);
        token = mix_readiness_snapshot_token(
            token, out.targetPixelSemanticHash);
        token = mix_readiness_snapshot_token(
            token, out.translationPlanSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.cacheOwnerGenerationRequired ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.translationSlotGenerationRequired ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.translationObjectReceiptGenerationRequired ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.sameDeviceObjectPairRequired ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.cacheSnapshotRequired ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.slotSnapshotRequired ? 1u : 0u);
        token = mix_readiness_snapshot_token(token, 0x279u);
        out.reviewSnapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_programmable_shader_translation_object_prerequisite_snapshot(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence& translationPlan,
    std::uint64_t translationPlanSnapshotToken,
    std::uint64_t reviewSnapshotToken) noexcept {
    if (reviewSnapshotToken == 0)
        return false;
    const auto current =
        derive_programmable_shader_translation_object_prerequisite(
            sourceIdentity,
            translationPlan,
            translationPlanSnapshotToken);
    return current.reviewReady &&
        current.boundaryPreserved &&
        current.cacheOwnerGenerationRequired &&
        current.translationSlotGenerationRequired &&
        current.translationObjectReceiptGenerationRequired &&
        current.sameDeviceObjectPairRequired &&
        current.cacheSnapshotRequired &&
        current.slotSnapshotRequired &&
        current.reviewSnapshotToken == reviewSnapshotToken;
}

NativeProgrammableShaderObjectCreationHandoffEvidence
compose_programmable_shader_object_creation_handoff(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const ProgrammableShaderFunctionSourceEvidence& vertexSource,
    const ProgrammableShaderFunctionSourceEvidence& pixelSource,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence& translationPlan,
    std::uint64_t translationPlanSnapshotToken,
    const NativeProgrammableShaderTranslationObjectPrerequisiteEvidence&
        objectPrerequisite,
    std::uint64_t objectPrerequisiteSnapshotToken) noexcept {
    NativeProgrammableShaderObjectCreationHandoffEvidence out{};

    out.cacheKey = sourceIdentity.cacheKey;
    out.vertexVersionToken = sourceIdentity.vertexShader.versionToken;
    out.pixelVersionToken = sourceIdentity.pixelShader.versionToken;
    out.vertexByteSize = sourceIdentity.vertexShader.byteSize;
    out.pixelByteSize = sourceIdentity.pixelShader.byteSize;
    out.vertexBytecodeHash = sourceIdentity.vertexShader.bytecodeHash;
    out.pixelBytecodeHash = sourceIdentity.pixelShader.bytecodeHash;
    out.targetVertexSemanticHash =
        translationPlan.targetVertexSemanticHash;
    out.targetPixelSemanticHash =
        translationPlan.targetPixelSemanticHash;
    out.translationPlanSnapshotToken = translationPlanSnapshotToken;
    out.objectPrerequisiteSnapshotToken =
        objectPrerequisiteSnapshotToken;

    out.inputValid =
        translationPlanSnapshotToken != 0 &&
        objectPrerequisiteSnapshotToken != 0;
    out.sourceIdentityExact =
        sourceIdentity.exact_identity() &&
        !sourceIdentity.translationImplemented;
    out.vertexSourceExact =
        out.sourceIdentityExact &&
        validate_programmable_shader_function_source_evidence(
            vertexSource, sourceIdentity.vertexShader, true);
    out.pixelSourceExact =
        out.sourceIdentityExact &&
        validate_programmable_shader_function_source_evidence(
            pixelSource, sourceIdentity.pixelShader, false);
    out.sourcePairMatches =
        out.vertexSourceExact &&
        out.pixelSourceExact &&
        vertexSource.byteSize == sourceIdentity.vertexShader.byteSize &&
        pixelSource.byteSize == sourceIdentity.pixelShader.byteSize &&
        vertexSource.versionToken == sourceIdentity.vertexShader.versionToken &&
        pixelSource.versionToken == sourceIdentity.pixelShader.versionToken &&
        vertexSource.bytecodeHash == sourceIdentity.vertexShader.bytecodeHash &&
        pixelSource.bytecodeHash == sourceIdentity.pixelShader.bytecodeHash;
    out.translationPlanReady =
        translationPlan.reviewReady &&
        translationPlan.boundaryPreserved &&
        translationPlan.diagnosticOnly &&
        translationPlan.provenanceMatches &&
        translationPlan.vertexSemanticExact &&
        translationPlan.pixelSemanticExact &&
        translationPlan.reviewSnapshotToken != 0;
    out.translationPlanSnapshotMatches =
        out.translationPlanReady &&
        translationPlan.reviewSnapshotToken ==
            translationPlanSnapshotToken;
    out.objectPrerequisiteReady =
        objectPrerequisite.reviewReady &&
        objectPrerequisite.boundaryPreserved &&
        objectPrerequisite.diagnosticOnly &&
        objectPrerequisite.cacheOwnerGenerationRequired &&
        objectPrerequisite.translationSlotGenerationRequired &&
        objectPrerequisite.translationObjectReceiptGenerationRequired &&
        objectPrerequisite.sameDeviceObjectPairRequired &&
        objectPrerequisite.cacheSnapshotRequired &&
        objectPrerequisite.slotSnapshotRequired &&
        objectPrerequisite.reviewSnapshotToken != 0;
    out.objectPrerequisiteSnapshotMatches =
        out.objectPrerequisiteReady &&
        objectPrerequisite.reviewSnapshotToken ==
            objectPrerequisiteSnapshotToken;
    out.cacheIdentityMatches =
        out.sourcePairMatches &&
        out.translationPlanSnapshotMatches &&
        out.objectPrerequisiteSnapshotMatches &&
        sourceIdentity.cacheKey != 0 &&
        sourceIdentity.cacheKey == translationPlan.cacheKey &&
        sourceIdentity.cacheKey == objectPrerequisite.cacheKey &&
        translationPlan.targetVertexSemanticHash != 0 &&
        translationPlan.targetVertexSemanticHash ==
            objectPrerequisite.targetVertexSemanticHash &&
        translationPlan.targetPixelSemanticHash != 0 &&
        translationPlan.targetPixelSemanticHash ==
            objectPrerequisite.targetPixelSemanticHash;

    // R280 is intentionally evidence-only. A future implementation must add
    // a separate creation authority before any D3D11 programmable object call.
    out.objectCreationAuthorized = false;
    out.diagnosticOnly = true;
    out.boundaryPreserved =
        out.cacheIdentityMatches &&
        !out.objectCreationAuthorized &&
        out.diagnosticOnly;
    out.reviewReady =
        out.inputValid &&
        out.boundaryPreserved;

    if (out.reviewReady) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(token, out.cacheKey);
        token = mix_readiness_snapshot_token(token, out.vertexVersionToken);
        token = mix_readiness_snapshot_token(token, out.pixelVersionToken);
        token = mix_readiness_snapshot_token(token, out.vertexByteSize);
        token = mix_readiness_snapshot_token(token, out.pixelByteSize);
        token = mix_readiness_snapshot_token(token, out.vertexBytecodeHash);
        token = mix_readiness_snapshot_token(token, out.pixelBytecodeHash);
        token = mix_readiness_snapshot_token(
            token, out.targetVertexSemanticHash);
        token = mix_readiness_snapshot_token(
            token, out.targetPixelSemanticHash);
        token = mix_readiness_snapshot_token(
            token, out.translationPlanSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.objectPrerequisiteSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.objectCreationAuthorized ? 1u : 0u);
        token = mix_readiness_snapshot_token(token, 0x280u);
        out.reviewSnapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_programmable_shader_object_creation_handoff_snapshot(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const ProgrammableShaderFunctionSourceEvidence& vertexSource,
    const ProgrammableShaderFunctionSourceEvidence& pixelSource,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence& translationPlan,
    std::uint64_t translationPlanSnapshotToken,
    const NativeProgrammableShaderTranslationObjectPrerequisiteEvidence&
        objectPrerequisite,
    std::uint64_t objectPrerequisiteSnapshotToken,
    std::uint64_t reviewSnapshotToken) noexcept {
    if (reviewSnapshotToken == 0)
        return false;
    const auto current =
        compose_programmable_shader_object_creation_handoff(
            sourceIdentity,
            vertexSource,
            pixelSource,
            translationPlan,
            translationPlanSnapshotToken,
            objectPrerequisite,
            objectPrerequisiteSnapshotToken);
    return current.reviewReady &&
        current.boundaryPreserved &&
        current.vertexSourceExact &&
        current.pixelSourceExact &&
        current.sourcePairMatches &&
        current.translationPlanSnapshotMatches &&
        current.objectPrerequisiteSnapshotMatches &&
        current.cacheIdentityMatches &&
        !current.objectCreationAuthorized &&
        current.reviewSnapshotToken == reviewSnapshotToken;
}

NativeProgrammableShaderTranslatedArtifactReceiptEvidence
derive_programmable_shader_translated_artifact_receipt(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderObjectCreationHandoffEvidence& creationHandoff,
    std::uint64_t creationHandoffSnapshotToken,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence& translationPlan,
    std::uint64_t translationPlanSnapshotToken) noexcept {
    NativeProgrammableShaderTranslatedArtifactReceiptEvidence out{};

    out.cacheKey = sourceIdentity.cacheKey;
    out.vertexVersionToken = sourceIdentity.vertexShader.versionToken;
    out.pixelVersionToken = sourceIdentity.pixelShader.versionToken;
    out.sourceVertexBytecodeHash = sourceIdentity.vertexShader.bytecodeHash;
    out.sourcePixelBytecodeHash = sourceIdentity.pixelShader.bytecodeHash;
    out.targetVertexSemanticHash = translationPlan.targetVertexSemanticHash;
    out.targetPixelSemanticHash = translationPlan.targetPixelSemanticHash;
    out.translatorRevisionHash = translationPlan.translatorRevisionHash;
    out.semanticContractHash = translationPlan.semanticContractHash;
    out.objectCreationHandoffSnapshotToken = creationHandoffSnapshotToken;
    out.translationPlanSnapshotToken = translationPlanSnapshotToken;

    out.inputValid =
        creationHandoffSnapshotToken != 0 &&
        translationPlanSnapshotToken != 0;
    out.sourceIdentityExact =
        sourceIdentity.exact_identity() &&
        !sourceIdentity.translationImplemented;
    out.objectCreationHandoffReady =
        creationHandoff.reviewReady &&
        creationHandoff.boundaryPreserved &&
        creationHandoff.diagnosticOnly &&
        creationHandoff.cacheIdentityMatches &&
        creationHandoff.vertexSourceExact &&
        creationHandoff.pixelSourceExact &&
        !creationHandoff.objectCreationAuthorized &&
        creationHandoff.reviewSnapshotToken != 0;
    out.objectCreationHandoffSnapshotMatches =
        out.objectCreationHandoffReady &&
        creationHandoff.reviewSnapshotToken == creationHandoffSnapshotToken;
    out.translationPlanReady =
        translationPlan.reviewReady &&
        translationPlan.boundaryPreserved &&
        translationPlan.diagnosticOnly &&
        translationPlan.provenanceMatches &&
        translationPlan.vertexSemanticExact &&
        translationPlan.pixelSemanticExact &&
        translationPlan.translatorRevisionHash != 0 &&
        translationPlan.semanticContractHash != 0 &&
        translationPlan.reviewSnapshotToken != 0;
    out.translationPlanSnapshotMatches =
        out.translationPlanReady &&
        translationPlan.reviewSnapshotToken == translationPlanSnapshotToken;
    out.cacheIdentityMatches =
        out.sourceIdentityExact &&
        out.objectCreationHandoffSnapshotMatches &&
        out.translationPlanSnapshotMatches &&
        sourceIdentity.cacheKey != 0 &&
        sourceIdentity.cacheKey == creationHandoff.cacheKey &&
        sourceIdentity.cacheKey == translationPlan.cacheKey &&
        sourceIdentity.vertexShader.bytecodeHash ==
            creationHandoff.vertexBytecodeHash &&
        sourceIdentity.pixelShader.bytecodeHash ==
            creationHandoff.pixelBytecodeHash &&
        translationPlan.targetVertexSemanticHash ==
            creationHandoff.targetVertexSemanticHash &&
        translationPlan.targetPixelSemanticHash ==
            creationHandoff.targetPixelSemanticHash;

    if (out.cacheIdentityMatches) {
        std::uint64_t vertexIdentity = 0xcbf29ce484222325ull;
        vertexIdentity = mix_readiness_snapshot_token(vertexIdentity, out.cacheKey);
        vertexIdentity = mix_readiness_snapshot_token(
            vertexIdentity, out.vertexVersionToken);
        vertexIdentity = mix_readiness_snapshot_token(
            vertexIdentity, out.sourceVertexBytecodeHash);
        vertexIdentity = mix_readiness_snapshot_token(
            vertexIdentity, out.targetVertexSemanticHash);
        vertexIdentity = mix_readiness_snapshot_token(
            vertexIdentity, out.translatorRevisionHash);
        vertexIdentity = mix_readiness_snapshot_token(
            vertexIdentity, out.semanticContractHash);
        vertexIdentity = mix_readiness_snapshot_token(vertexIdentity, 0x28101u);
        out.targetVertexBytecodeReceiptIdentity =
            vertexIdentity == 0 ? 1 : vertexIdentity;

        std::uint64_t pixelIdentity = 0xcbf29ce484222325ull;
        pixelIdentity = mix_readiness_snapshot_token(pixelIdentity, out.cacheKey);
        pixelIdentity = mix_readiness_snapshot_token(
            pixelIdentity, out.pixelVersionToken);
        pixelIdentity = mix_readiness_snapshot_token(
            pixelIdentity, out.sourcePixelBytecodeHash);
        pixelIdentity = mix_readiness_snapshot_token(
            pixelIdentity, out.targetPixelSemanticHash);
        pixelIdentity = mix_readiness_snapshot_token(
            pixelIdentity, out.translatorRevisionHash);
        pixelIdentity = mix_readiness_snapshot_token(
            pixelIdentity, out.semanticContractHash);
        pixelIdentity = mix_readiness_snapshot_token(pixelIdentity, 0x28102u);
        out.targetPixelBytecodeReceiptIdentity =
            pixelIdentity == 0 ? 1 : pixelIdentity;
    }

    out.targetVertexIdentityDefined =
        out.targetVertexBytecodeReceiptIdentity != 0;
    out.targetPixelIdentityDefined =
        out.targetPixelBytecodeReceiptIdentity != 0;
    out.targetBytecodeReceiptRequired =
        out.targetVertexIdentityDefined && out.targetPixelIdentityDefined;

    // R281 is a requirement/receipt identity only. No target bytecode exists
    // yet, therefore shader creation must remain impossible at this boundary.
    out.targetBytecodeMaterialized = false;
    out.objectCreationAuthorized = false;
    out.diagnosticOnly = true;
    out.boundaryPreserved =
        out.cacheIdentityMatches &&
        out.targetBytecodeReceiptRequired &&
        !out.targetBytecodeMaterialized &&
        !out.objectCreationAuthorized &&
        out.diagnosticOnly;
    out.reviewReady = out.inputValid && out.boundaryPreserved;

    if (out.reviewReady) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(token, out.cacheKey);
        token = mix_readiness_snapshot_token(
            token, out.targetVertexBytecodeReceiptIdentity);
        token = mix_readiness_snapshot_token(
            token, out.targetPixelBytecodeReceiptIdentity);
        token = mix_readiness_snapshot_token(
            token, out.objectCreationHandoffSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.translationPlanSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.targetBytecodeReceiptRequired ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.targetBytecodeMaterialized ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.objectCreationAuthorized ? 1u : 0u);
        token = mix_readiness_snapshot_token(token, 0x281u);
        out.reviewSnapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_programmable_shader_translated_artifact_receipt_snapshot(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderObjectCreationHandoffEvidence& creationHandoff,
    std::uint64_t creationHandoffSnapshotToken,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence& translationPlan,
    std::uint64_t translationPlanSnapshotToken,
    std::uint64_t reviewSnapshotToken) noexcept {
    if (reviewSnapshotToken == 0)
        return false;
    const auto current = derive_programmable_shader_translated_artifact_receipt(
        sourceIdentity,
        creationHandoff,
        creationHandoffSnapshotToken,
        translationPlan,
        translationPlanSnapshotToken);
    return current.reviewReady &&
        current.boundaryPreserved &&
        current.objectCreationHandoffSnapshotMatches &&
        current.translationPlanSnapshotMatches &&
        current.cacheIdentityMatches &&
        current.targetVertexIdentityDefined &&
        current.targetPixelIdentityDefined &&
        current.targetBytecodeReceiptRequired &&
        !current.targetBytecodeMaterialized &&
        !current.objectCreationAuthorized &&
        current.reviewSnapshotToken == reviewSnapshotToken;
}

NativeProgrammableShaderTargetMaterializationContractEvidence
derive_programmable_shader_target_materialization_contract(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderTranslatedArtifactReceiptEvidence&
        translatedArtifactReceipt,
    std::uint64_t translatedArtifactReceiptSnapshotToken,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence& translationPlan,
    std::uint64_t translationPlanSnapshotToken) noexcept {
    NativeProgrammableShaderTargetMaterializationContractEvidence out{};

    constexpr char kEntryPoint[] = "main";
    constexpr char kVertexTargetProfile[] = "vs_4_0";
    constexpr char kPixelTargetProfile[] = "ps_4_0";
    constexpr std::uint32_t kCompileFlags =
        D3DCOMPILE_ENABLE_STRICTNESS | D3DCOMPILE_OPTIMIZATION_LEVEL3;

    out.cacheKey = sourceIdentity.cacheKey;
    out.targetVertexBytecodeReceiptIdentity =
        translatedArtifactReceipt.targetVertexBytecodeReceiptIdentity;
    out.targetPixelBytecodeReceiptIdentity =
        translatedArtifactReceipt.targetPixelBytecodeReceiptIdentity;
    out.entryPointHash = hash_observation_payload_bytes(
        kEntryPoint, static_cast<UINT>(sizeof(kEntryPoint) - 1));
    out.vertexTargetProfileHash = hash_observation_payload_bytes(
        kVertexTargetProfile,
        static_cast<UINT>(sizeof(kVertexTargetProfile) - 1));
    out.pixelTargetProfileHash = hash_observation_payload_bytes(
        kPixelTargetProfile,
        static_cast<UINT>(sizeof(kPixelTargetProfile) - 1));
    out.compileFlags = kCompileFlags;
    out.translatorRevisionHash = translationPlan.translatorRevisionHash;
    out.semanticContractHash = translationPlan.semanticContractHash;
    out.translatedArtifactReceiptSnapshotToken =
        translatedArtifactReceiptSnapshotToken;
    out.translationPlanSnapshotToken = translationPlanSnapshotToken;

    out.inputValid =
        translatedArtifactReceiptSnapshotToken != 0 &&
        translationPlanSnapshotToken != 0;
    out.sourceIdentityExact =
        sourceIdentity.exact_identity() &&
        !sourceIdentity.translationImplemented;
    out.translatedArtifactReceiptReady =
        translatedArtifactReceipt.reviewReady &&
        translatedArtifactReceipt.boundaryPreserved &&
        translatedArtifactReceipt.diagnosticOnly &&
        translatedArtifactReceipt.cacheIdentityMatches &&
        translatedArtifactReceipt.targetVertexIdentityDefined &&
        translatedArtifactReceipt.targetPixelIdentityDefined &&
        translatedArtifactReceipt.targetBytecodeReceiptRequired &&
        !translatedArtifactReceipt.targetBytecodeMaterialized &&
        !translatedArtifactReceipt.objectCreationAuthorized &&
        translatedArtifactReceipt.reviewSnapshotToken != 0;
    out.translatedArtifactReceiptSnapshotMatches =
        out.translatedArtifactReceiptReady &&
        translatedArtifactReceipt.reviewSnapshotToken ==
            translatedArtifactReceiptSnapshotToken;
    out.translationPlanReady =
        translationPlan.reviewReady &&
        translationPlan.boundaryPreserved &&
        translationPlan.diagnosticOnly &&
        translationPlan.provenanceMatches &&
        translationPlan.vertexSemanticExact &&
        translationPlan.pixelSemanticExact &&
        translationPlan.translatorRevisionHash != 0 &&
        translationPlan.semanticContractHash != 0 &&
        translationPlan.reviewSnapshotToken != 0;
    out.translationPlanSnapshotMatches =
        out.translationPlanReady &&
        translationPlan.reviewSnapshotToken == translationPlanSnapshotToken;
    out.cacheIdentityMatches =
        out.sourceIdentityExact &&
        out.translatedArtifactReceiptSnapshotMatches &&
        out.translationPlanSnapshotMatches &&
        sourceIdentity.cacheKey != 0 &&
        sourceIdentity.cacheKey == translatedArtifactReceipt.cacheKey &&
        sourceIdentity.cacheKey == translationPlan.cacheKey;
    out.targetArtifactIdentityMatches =
        out.cacheIdentityMatches &&
        translatedArtifactReceipt.targetVertexBytecodeReceiptIdentity != 0 &&
        translatedArtifactReceipt.targetPixelBytecodeReceiptIdentity != 0 &&
        translatedArtifactReceipt.targetVertexBytecodeReceiptIdentity !=
            translatedArtifactReceipt.targetPixelBytecodeReceiptIdentity &&
        translatedArtifactReceipt.translatorRevisionHash ==
            translationPlan.translatorRevisionHash &&
        translatedArtifactReceipt.semanticContractHash ==
            translationPlan.semanticContractHash;

    out.entryPointExact = out.entryPointHash != 0;
    out.vertexTargetProfileExact = out.vertexTargetProfileHash != 0;
    out.pixelTargetProfileExact = out.pixelTargetProfileHash != 0;
    out.compileFlagsExact =
        out.compileFlags ==
            (D3DCOMPILE_ENABLE_STRICTNESS | D3DCOMPILE_OPTIMIZATION_LEVEL3);

    if (out.targetArtifactIdentityMatches &&
        out.entryPointExact &&
        out.vertexTargetProfileExact &&
        out.pixelTargetProfileExact &&
        out.compileFlagsExact) {
        std::uint64_t vertexContract = 0xcbf29ce484222325ull;
        vertexContract = mix_readiness_snapshot_token(
            vertexContract, out.targetVertexBytecodeReceiptIdentity);
        vertexContract = mix_readiness_snapshot_token(
            vertexContract, out.entryPointHash);
        vertexContract = mix_readiness_snapshot_token(
            vertexContract, out.vertexTargetProfileHash);
        vertexContract = mix_readiness_snapshot_token(
            vertexContract, out.compileFlags);
        vertexContract = mix_readiness_snapshot_token(
            vertexContract, out.translatorRevisionHash);
        vertexContract = mix_readiness_snapshot_token(
            vertexContract, out.semanticContractHash);
        vertexContract = mix_readiness_snapshot_token(vertexContract, 0x28201u);
        out.vertexCompileContractIdentity =
            vertexContract == 0 ? 1 : vertexContract;

        std::uint64_t pixelContract = 0xcbf29ce484222325ull;
        pixelContract = mix_readiness_snapshot_token(
            pixelContract, out.targetPixelBytecodeReceiptIdentity);
        pixelContract = mix_readiness_snapshot_token(
            pixelContract, out.entryPointHash);
        pixelContract = mix_readiness_snapshot_token(
            pixelContract, out.pixelTargetProfileHash);
        pixelContract = mix_readiness_snapshot_token(
            pixelContract, out.compileFlags);
        pixelContract = mix_readiness_snapshot_token(
            pixelContract, out.translatorRevisionHash);
        pixelContract = mix_readiness_snapshot_token(
            pixelContract, out.semanticContractHash);
        pixelContract = mix_readiness_snapshot_token(pixelContract, 0x28202u);
        out.pixelCompileContractIdentity =
            pixelContract == 0 ? 1 : pixelContract;
    }

    out.targetBytecodeMaterializationRequired =
        out.vertexCompileContractIdentity != 0 &&
        out.pixelCompileContractIdentity != 0 &&
        out.vertexCompileContractIdentity != out.pixelCompileContractIdentity;

    // R282 defines only the exact compiler/materialization identity. Actual
    // translated source/bytecode production is a later boundary.
    out.targetBytecodeMaterialized = false;
    out.compilationAuthorized = false;
    out.objectCreationAuthorized = false;
    out.diagnosticOnly = true;
    out.boundaryPreserved =
        out.targetArtifactIdentityMatches &&
        out.targetBytecodeMaterializationRequired &&
        !out.targetBytecodeMaterialized &&
        !out.compilationAuthorized &&
        !out.objectCreationAuthorized &&
        out.diagnosticOnly;
    out.reviewReady = out.inputValid && out.boundaryPreserved;

    if (out.reviewReady) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(token, out.cacheKey);
        token = mix_readiness_snapshot_token(
            token, out.vertexCompileContractIdentity);
        token = mix_readiness_snapshot_token(
            token, out.pixelCompileContractIdentity);
        token = mix_readiness_snapshot_token(
            token, out.translatedArtifactReceiptSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.translationPlanSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.targetBytecodeMaterializationRequired ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.targetBytecodeMaterialized ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.compilationAuthorized ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.objectCreationAuthorized ? 1u : 0u);
        token = mix_readiness_snapshot_token(token, 0x282u);
        out.reviewSnapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_programmable_shader_target_materialization_contract_snapshot(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderTranslatedArtifactReceiptEvidence&
        translatedArtifactReceipt,
    std::uint64_t translatedArtifactReceiptSnapshotToken,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence& translationPlan,
    std::uint64_t translationPlanSnapshotToken,
    std::uint64_t reviewSnapshotToken) noexcept {
    if (reviewSnapshotToken == 0)
        return false;
    const auto current =
        derive_programmable_shader_target_materialization_contract(
            sourceIdentity,
            translatedArtifactReceipt,
            translatedArtifactReceiptSnapshotToken,
            translationPlan,
            translationPlanSnapshotToken);
    return current.reviewReady &&
        current.boundaryPreserved &&
        current.translatedArtifactReceiptSnapshotMatches &&
        current.translationPlanSnapshotMatches &&
        current.cacheIdentityMatches &&
        current.targetArtifactIdentityMatches &&
        current.entryPointExact &&
        current.vertexTargetProfileExact &&
        current.pixelTargetProfileExact &&
        current.compileFlagsExact &&
        current.targetBytecodeMaterializationRequired &&
        !current.targetBytecodeMaterialized &&
        !current.compilationAuthorized &&
        !current.objectCreationAuthorized &&
        current.reviewSnapshotToken == reviewSnapshotToken;
}

NativeProgrammableShaderTargetBytecodeMaterializationEvidence
materialize_programmable_shader_target_bytecode(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const ProgrammableShaderFunctionSourceEvidence& vertexSource,
    const ProgrammableShaderFunctionSourceEvidence& pixelSource,
    const NativeProgrammableShaderTranslatedArtifactReceiptEvidence&
        translatedArtifactReceipt,
    std::uint64_t translatedArtifactReceiptSnapshotToken,
    const NativeProgrammableShaderTargetMaterializationContractEvidence&
        targetMaterializationContract,
    std::uint64_t targetMaterializationContractSnapshotToken,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence& translationPlan,
    std::uint64_t translationPlanSnapshotToken) noexcept {
    NativeProgrammableShaderTargetBytecodeMaterializationEvidence out{};
    out.diagnosticOnly = true;
    out.cacheKey = sourceIdentity.cacheKey;
    out.vertexVersionToken = sourceIdentity.vertexShader.versionToken;
    out.pixelVersionToken = sourceIdentity.pixelShader.versionToken;
    out.sourceVertexBytecodeHash = sourceIdentity.vertexShader.bytecodeHash;
    out.sourcePixelBytecodeHash = sourceIdentity.pixelShader.bytecodeHash;
    out.targetVertexBytecodeReceiptIdentity =
        translatedArtifactReceipt.targetVertexBytecodeReceiptIdentity;
    out.targetPixelBytecodeReceiptIdentity =
        translatedArtifactReceipt.targetPixelBytecodeReceiptIdentity;
    out.vertexCompileContractIdentity =
        targetMaterializationContract.vertexCompileContractIdentity;
    out.pixelCompileContractIdentity =
        targetMaterializationContract.pixelCompileContractIdentity;
    out.targetVertexSemanticHash = translationPlan.targetVertexSemanticHash;
    out.targetPixelSemanticHash = translationPlan.targetPixelSemanticHash;
    out.materializerRevisionHash = r283_materializer_revision_hash();
    out.semanticSubsetContractHash =
        r283_semantic_subset_contract_hash();
    out.translatedArtifactReceiptSnapshotToken =
        translatedArtifactReceiptSnapshotToken;
    out.targetMaterializationContractSnapshotToken =
        targetMaterializationContractSnapshotToken;
    out.translationPlanSnapshotToken = translationPlanSnapshotToken;

    out.inputValid =
        translatedArtifactReceiptSnapshotToken != 0 &&
        targetMaterializationContractSnapshotToken != 0 &&
        translationPlanSnapshotToken != 0;
    out.sourceIdentityExact =
        sourceIdentity.exact_identity() &&
        !sourceIdentity.translationImplemented;
    out.vertexSourceExact =
        validate_programmable_shader_function_source_evidence(
            vertexSource, sourceIdentity.vertexShader, true);
    out.pixelSourceExact =
        validate_programmable_shader_function_source_evidence(
            pixelSource, sourceIdentity.pixelShader, false);
    out.translatedArtifactReceiptReady =
        translatedArtifactReceipt.reviewReady &&
        translatedArtifactReceipt.boundaryPreserved &&
        translatedArtifactReceipt.diagnosticOnly &&
        translatedArtifactReceipt.targetBytecodeReceiptRequired &&
        !translatedArtifactReceipt.targetBytecodeMaterialized &&
        !translatedArtifactReceipt.objectCreationAuthorized;
    out.translatedArtifactReceiptSnapshotMatches =
        out.translatedArtifactReceiptReady &&
        translatedArtifactReceipt.reviewSnapshotToken ==
            translatedArtifactReceiptSnapshotToken;
    out.targetMaterializationContractReady =
        targetMaterializationContract.reviewReady &&
        targetMaterializationContract.boundaryPreserved &&
        targetMaterializationContract.diagnosticOnly &&
        targetMaterializationContract.targetBytecodeMaterializationRequired &&
        !targetMaterializationContract.targetBytecodeMaterialized &&
        !targetMaterializationContract.compilationAuthorized &&
        !targetMaterializationContract.objectCreationAuthorized;
    out.targetMaterializationContractSnapshotMatches =
        out.targetMaterializationContractReady &&
        targetMaterializationContract.reviewSnapshotToken ==
            targetMaterializationContractSnapshotToken;
    out.translationPlanReady =
        translationPlan.reviewReady &&
        translationPlan.boundaryPreserved &&
        translationPlan.diagnosticOnly &&
        translationPlan.provenanceMatches &&
        translationPlan.vertexSemanticExact &&
        translationPlan.pixelSemanticExact;
    out.translationPlanSnapshotMatches =
        out.translationPlanReady &&
        translationPlan.reviewSnapshotToken == translationPlanSnapshotToken;
    out.provenanceMatches =
        out.inputValid &&
        out.sourceIdentityExact &&
        out.vertexSourceExact &&
        out.pixelSourceExact &&
        out.translatedArtifactReceiptSnapshotMatches &&
        out.targetMaterializationContractSnapshotMatches &&
        out.translationPlanSnapshotMatches &&
        sourceIdentity.cacheKey != 0 &&
        sourceIdentity.cacheKey == translatedArtifactReceipt.cacheKey &&
        sourceIdentity.cacheKey == targetMaterializationContract.cacheKey &&
        sourceIdentity.cacheKey == translationPlan.cacheKey &&
        translatedArtifactReceipt.targetVertexBytecodeReceiptIdentity ==
            targetMaterializationContract.targetVertexBytecodeReceiptIdentity &&
        translatedArtifactReceipt.targetPixelBytecodeReceiptIdentity ==
            targetMaterializationContract.targetPixelBytecodeReceiptIdentity &&
        translatedArtifactReceipt.translatorRevisionHash ==
            translationPlan.translatorRevisionHash &&
        translatedArtifactReceipt.semanticContractHash ==
            translationPlan.semanticContractHash &&
        targetMaterializationContract.translatorRevisionHash ==
            translationPlan.translatorRevisionHash &&
        targetMaterializationContract.semanticContractHash ==
            translationPlan.semanticContractHash &&
        targetMaterializationContract.vertexCompileContractIdentity != 0 &&
        targetMaterializationContract.pixelCompileContractIdentity != 0 &&
        translationPlan.targetVertexSemanticHash != 0 &&
        translationPlan.targetPixelSemanticHash != 0 &&
        out.materializerRevisionHash != 0 &&
        out.semanticSubsetContractHash != 0;
    if (!out.provenanceMatches)
        return out;

    try {
        std::string vertexTranslatedSource;
        std::string pixelTranslatedSource;
        out.vertexSubsetSupported =
            build_r283_sm3_mov_shader_source(
                vertexSource, true, vertexTranslatedSource);
        out.pixelSubsetSupported =
            build_r283_sm3_mov_shader_source(
                pixelSource, false, pixelTranslatedSource);
        if (!out.vertexSubsetSupported || !out.pixelSubsetSupported)
            return out;
        if (vertexTranslatedSource.size() >
                (std::numeric_limits<UINT>::max)() ||
            pixelTranslatedSource.size() >
                (std::numeric_limits<UINT>::max)())
            return out;

        out.vertexTranslatedSourceBytes =
            static_cast<UINT>(vertexTranslatedSource.size());
        out.pixelTranslatedSourceBytes =
            static_cast<UINT>(pixelTranslatedSource.size());
        out.vertexTranslatedSourceHash =
            hash_observation_payload_bytes(
                vertexTranslatedSource.data(),
                out.vertexTranslatedSourceBytes);
        out.pixelTranslatedSourceHash =
            hash_observation_payload_bytes(
                pixelTranslatedSource.data(),
                out.pixelTranslatedSourceBytes);
        out.vertexSourceMaterialized =
            out.vertexTranslatedSourceBytes != 0 &&
            out.vertexTranslatedSourceHash != 0;
        out.pixelSourceMaterialized =
            out.pixelTranslatedSourceBytes != 0 &&
            out.pixelTranslatedSourceHash != 0;
        if (!out.vertexSourceMaterialized ||
            !out.pixelSourceMaterialized)
            return out;

        Microsoft::WRL::ComPtr<ID3DBlob> vertexBytecode;
        Microsoft::WRL::ComPtr<ID3DBlob> pixelBytecode;
        out.vertexCompilationSucceeded =
            compile_shader_source(
                vertexTranslatedSource,
                "r283_programmable_vs",
                "vs_4_0",
                vertexBytecode);
        out.pixelCompilationSucceeded =
            compile_shader_source(
                pixelTranslatedSource,
                "r283_programmable_ps",
                "ps_4_0",
                pixelBytecode);
        if (!out.vertexCompilationSucceeded ||
            !out.pixelCompilationSucceeded ||
            !vertexBytecode ||
            !pixelBytecode ||
            vertexBytecode->GetBufferSize() >
                (std::numeric_limits<UINT>::max)() ||
            pixelBytecode->GetBufferSize() >
                (std::numeric_limits<UINT>::max)())
            return out;

        out.vertexTargetBytecodeBytes =
            static_cast<UINT>(vertexBytecode->GetBufferSize());
        out.pixelTargetBytecodeBytes =
            static_cast<UINT>(pixelBytecode->GetBufferSize());
        const auto* vertexBegin = static_cast<const std::uint8_t*>(
            vertexBytecode->GetBufferPointer());
        const auto* pixelBegin = static_cast<const std::uint8_t*>(
            pixelBytecode->GetBufferPointer());
        if (!vertexBegin || !pixelBegin ||
            out.vertexTargetBytecodeBytes == 0 ||
            out.pixelTargetBytecodeBytes == 0)
            return out;
        out.vertexTargetBytecode.assign(
            vertexBegin,
            vertexBegin + out.vertexTargetBytecodeBytes);
        out.pixelTargetBytecode.assign(
            pixelBegin,
            pixelBegin + out.pixelTargetBytecodeBytes);
        if (!r283_dxbc_payload(out.vertexTargetBytecode) ||
            !r283_dxbc_payload(out.pixelTargetBytecode))
            return out;

        out.vertexTargetBytecodeHash =
            hash_observation_payload_bytes(
                out.vertexTargetBytecode.data(),
                out.vertexTargetBytecodeBytes);
        out.pixelTargetBytecodeHash =
            hash_observation_payload_bytes(
                out.pixelTargetBytecode.data(),
                out.pixelTargetBytecodeBytes);
        out.vertexMaterializedArtifactIdentity =
            r283_materialized_artifact_identity(
                out.targetVertexBytecodeReceiptIdentity,
                out.vertexCompileContractIdentity,
                out.vertexTranslatedSourceHash,
                out.vertexTargetBytecodeHash,
                out.vertexTargetBytecodeBytes,
                0x28301u);
        out.pixelMaterializedArtifactIdentity =
            r283_materialized_artifact_identity(
                out.targetPixelBytecodeReceiptIdentity,
                out.pixelCompileContractIdentity,
                out.pixelTranslatedSourceHash,
                out.pixelTargetBytecodeHash,
                out.pixelTargetBytecodeBytes,
                0x28302u);
        out.targetBytecodeMaterialized =
            out.vertexTargetBytecodeHash != 0 &&
            out.pixelTargetBytecodeHash != 0 &&
            out.vertexMaterializedArtifactIdentity != 0 &&
            out.pixelMaterializedArtifactIdentity != 0 &&
            out.vertexMaterializedArtifactIdentity !=
                out.pixelMaterializedArtifactIdentity;
        out.objectCreationAuthorized = false;
        out.boundaryPreserved =
            out.provenanceMatches &&
            out.vertexSubsetSupported &&
            out.pixelSubsetSupported &&
            out.vertexSourceMaterialized &&
            out.pixelSourceMaterialized &&
            out.vertexCompilationSucceeded &&
            out.pixelCompilationSucceeded &&
            out.targetBytecodeMaterialized &&
            !out.objectCreationAuthorized &&
            out.diagnosticOnly;
        out.reviewReady = out.boundaryPreserved;
        if (out.reviewReady)
            out.reviewSnapshotToken =
                r283_materialization_snapshot_token(out);
        return out;
    } catch (...) {
        return {};
    }
}

bool validate_programmable_shader_target_bytecode_materialization_snapshot(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const ProgrammableShaderFunctionSourceEvidence& vertexSource,
    const ProgrammableShaderFunctionSourceEvidence& pixelSource,
    const NativeProgrammableShaderTranslatedArtifactReceiptEvidence&
        translatedArtifactReceipt,
    std::uint64_t translatedArtifactReceiptSnapshotToken,
    const NativeProgrammableShaderTargetMaterializationContractEvidence&
        targetMaterializationContract,
    std::uint64_t targetMaterializationContractSnapshotToken,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence& translationPlan,
    std::uint64_t translationPlanSnapshotToken,
    const NativeProgrammableShaderTargetBytecodeMaterializationEvidence&
        materialization,
    std::uint64_t reviewSnapshotToken) noexcept {
    if (reviewSnapshotToken == 0 ||
        !materialization.reviewReady ||
        !materialization.boundaryPreserved ||
        !materialization.diagnosticOnly ||
        materialization.objectCreationAuthorized ||
        !materialization.targetBytecodeMaterialized ||
        materialization.reviewSnapshotToken != reviewSnapshotToken)
        return false;

    if (!sourceIdentity.exact_identity() ||
        sourceIdentity.translationImplemented ||
        !validate_programmable_shader_function_source_evidence(
            vertexSource, sourceIdentity.vertexShader, true) ||
        !validate_programmable_shader_function_source_evidence(
            pixelSource, sourceIdentity.pixelShader, false) ||
        !translatedArtifactReceipt.reviewReady ||
        translatedArtifactReceipt.reviewSnapshotToken !=
            translatedArtifactReceiptSnapshotToken ||
        !targetMaterializationContract.reviewReady ||
        targetMaterializationContract.reviewSnapshotToken !=
            targetMaterializationContractSnapshotToken ||
        !translationPlan.reviewReady ||
        translationPlan.reviewSnapshotToken != translationPlanSnapshotToken)
        return false;

    if (materialization.cacheKey != sourceIdentity.cacheKey ||
        materialization.sourceVertexBytecodeHash !=
            sourceIdentity.vertexShader.bytecodeHash ||
        materialization.sourcePixelBytecodeHash !=
            sourceIdentity.pixelShader.bytecodeHash ||
        materialization.targetVertexBytecodeReceiptIdentity !=
            translatedArtifactReceipt.targetVertexBytecodeReceiptIdentity ||
        materialization.targetPixelBytecodeReceiptIdentity !=
            translatedArtifactReceipt.targetPixelBytecodeReceiptIdentity ||
        materialization.vertexCompileContractIdentity !=
            targetMaterializationContract.vertexCompileContractIdentity ||
        materialization.pixelCompileContractIdentity !=
            targetMaterializationContract.pixelCompileContractIdentity ||
        materialization.targetVertexSemanticHash !=
            translationPlan.targetVertexSemanticHash ||
        materialization.targetPixelSemanticHash !=
            translationPlan.targetPixelSemanticHash ||
        materialization.materializerRevisionHash !=
            r283_materializer_revision_hash() ||
        materialization.semanticSubsetContractHash !=
            r283_semantic_subset_contract_hash() ||
        materialization.translatedArtifactReceiptSnapshotToken !=
            translatedArtifactReceiptSnapshotToken ||
        materialization.targetMaterializationContractSnapshotToken !=
            targetMaterializationContractSnapshotToken ||
        materialization.translationPlanSnapshotToken !=
            translationPlanSnapshotToken)
        return false;

    try {
        std::string vertexTranslatedSource;
        std::string pixelTranslatedSource;
        if (!build_r283_sm3_mov_shader_source(
                vertexSource, true, vertexTranslatedSource) ||
            !build_r283_sm3_mov_shader_source(
                pixelSource, false, pixelTranslatedSource) ||
            vertexTranslatedSource.size() !=
                materialization.vertexTranslatedSourceBytes ||
            pixelTranslatedSource.size() !=
                materialization.pixelTranslatedSourceBytes ||
            hash_observation_payload_bytes(
                vertexTranslatedSource.data(),
                materialization.vertexTranslatedSourceBytes) !=
                materialization.vertexTranslatedSourceHash ||
            hash_observation_payload_bytes(
                pixelTranslatedSource.data(),
                materialization.pixelTranslatedSourceBytes) !=
                materialization.pixelTranslatedSourceHash)
            return false;
    } catch (...) {
        return false;
    }

    if (materialization.vertexTargetBytecode.size() !=
            materialization.vertexTargetBytecodeBytes ||
        materialization.pixelTargetBytecode.size() !=
            materialization.pixelTargetBytecodeBytes ||
        !r283_dxbc_payload(materialization.vertexTargetBytecode) ||
        !r283_dxbc_payload(materialization.pixelTargetBytecode) ||
        hash_observation_payload_bytes(
            materialization.vertexTargetBytecode.data(),
            materialization.vertexTargetBytecodeBytes) !=
            materialization.vertexTargetBytecodeHash ||
        hash_observation_payload_bytes(
            materialization.pixelTargetBytecode.data(),
            materialization.pixelTargetBytecodeBytes) !=
            materialization.pixelTargetBytecodeHash)
        return false;

    if (r283_materialized_artifact_identity(
            materialization.targetVertexBytecodeReceiptIdentity,
            materialization.vertexCompileContractIdentity,
            materialization.vertexTranslatedSourceHash,
            materialization.vertexTargetBytecodeHash,
            materialization.vertexTargetBytecodeBytes,
            0x28301u) !=
            materialization.vertexMaterializedArtifactIdentity ||
        r283_materialized_artifact_identity(
            materialization.targetPixelBytecodeReceiptIdentity,
            materialization.pixelCompileContractIdentity,
            materialization.pixelTranslatedSourceHash,
            materialization.pixelTargetBytecodeHash,
            materialization.pixelTargetBytecodeBytes,
            0x28302u) !=
            materialization.pixelMaterializedArtifactIdentity)
        return false;

    return r283_materialization_snapshot_token(materialization) ==
        reviewSnapshotToken;
}

NativeProgrammableShaderObjectMaterializationEvidence
materialize_programmable_shader_translation_objects(
    ID3D11Device* expectedDevice,
    NativeProgrammableShaderPairCache& cache,
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderTranslationObjectPrerequisiteEvidence&
        objectPrerequisite,
    std::uint64_t objectPrerequisiteSnapshotToken,
    const NativeProgrammableShaderObjectCreationHandoffEvidence& creationHandoff,
    std::uint64_t creationHandoffSnapshotToken,
    const NativeProgrammableShaderTargetBytecodeMaterializationEvidence&
        targetBytecodeMaterialization,
    std::uint64_t targetBytecodeMaterializationSnapshotToken) noexcept {
    NativeProgrammableShaderObjectMaterializationEvidence out{};
    out.diagnosticOnly = true;
    out.objectBindingAuthorized = false;
    out.cacheKey = sourceIdentity.cacheKey;
    out.targetVertexBytecodeHash =
        targetBytecodeMaterialization.vertexTargetBytecodeHash;
    out.targetPixelBytecodeHash =
        targetBytecodeMaterialization.pixelTargetBytecodeHash;
    out.vertexMaterializedArtifactIdentity =
        targetBytecodeMaterialization.vertexMaterializedArtifactIdentity;
    out.pixelMaterializedArtifactIdentity =
        targetBytecodeMaterialization.pixelMaterializedArtifactIdentity;
    out.objectMaterializerRevisionHash =
        r284_object_materializer_revision_hash();
    out.objectPrerequisiteSnapshotToken = objectPrerequisiteSnapshotToken;
    out.creationHandoffSnapshotToken = creationHandoffSnapshotToken;
    out.targetBytecodeMaterializationSnapshotToken =
        targetBytecodeMaterializationSnapshotToken;

    out.inputValid =
        expectedDevice != nullptr &&
        objectPrerequisiteSnapshotToken != 0 &&
        creationHandoffSnapshotToken != 0 &&
        targetBytecodeMaterializationSnapshotToken != 0;
    out.sourceIdentityExact =
        sourceIdentity.exact_identity() &&
        !sourceIdentity.translationImplemented;
    out.objectPrerequisiteReady =
        objectPrerequisite.reviewReady &&
        objectPrerequisite.boundaryPreserved &&
        objectPrerequisite.diagnosticOnly &&
        objectPrerequisite.cacheOwnerGenerationRequired &&
        objectPrerequisite.translationSlotGenerationRequired &&
        objectPrerequisite.translationObjectReceiptGenerationRequired &&
        objectPrerequisite.sameDeviceObjectPairRequired &&
        objectPrerequisite.cacheSnapshotRequired &&
        objectPrerequisite.slotSnapshotRequired;
    out.objectPrerequisiteSnapshotMatches =
        out.objectPrerequisiteReady &&
        objectPrerequisite.reviewSnapshotToken ==
            objectPrerequisiteSnapshotToken;
    out.creationHandoffReady =
        creationHandoff.reviewReady &&
        creationHandoff.boundaryPreserved &&
        creationHandoff.diagnosticOnly &&
        creationHandoff.sourcePairMatches &&
        creationHandoff.objectPrerequisiteReady &&
        creationHandoff.objectPrerequisiteSnapshotMatches &&
        !creationHandoff.objectCreationAuthorized;
    out.creationHandoffSnapshotMatches =
        out.creationHandoffReady &&
        creationHandoff.reviewSnapshotToken ==
            creationHandoffSnapshotToken;
    out.targetBytecodeMaterializationReady =
        targetBytecodeMaterialization.reviewReady &&
        targetBytecodeMaterialization.boundaryPreserved &&
        targetBytecodeMaterialization.diagnosticOnly &&
        targetBytecodeMaterialization.provenanceMatches &&
        targetBytecodeMaterialization.vertexSubsetSupported &&
        targetBytecodeMaterialization.pixelSubsetSupported &&
        targetBytecodeMaterialization.vertexCompilationSucceeded &&
        targetBytecodeMaterialization.pixelCompilationSucceeded &&
        targetBytecodeMaterialization.targetBytecodeMaterialized &&
        !targetBytecodeMaterialization.objectCreationAuthorized &&
        targetBytecodeMaterialization.vertexTargetBytecodeBytes != 0 &&
        targetBytecodeMaterialization.pixelTargetBytecodeBytes != 0 &&
        targetBytecodeMaterialization.vertexTargetBytecode.size() ==
            targetBytecodeMaterialization.vertexTargetBytecodeBytes &&
        targetBytecodeMaterialization.pixelTargetBytecode.size() ==
            targetBytecodeMaterialization.pixelTargetBytecodeBytes &&
        targetBytecodeMaterialization.vertexTargetBytecodeHash != 0 &&
        targetBytecodeMaterialization.pixelTargetBytecodeHash != 0 &&
        targetBytecodeMaterialization.vertexMaterializedArtifactIdentity != 0 &&
        targetBytecodeMaterialization.pixelMaterializedArtifactIdentity != 0;
    out.targetBytecodeMaterializationSnapshotMatches =
        out.targetBytecodeMaterializationReady &&
        targetBytecodeMaterialization.reviewSnapshotToken ==
            targetBytecodeMaterializationSnapshotToken &&
        r283_materialization_snapshot_token(targetBytecodeMaterialization) ==
            targetBytecodeMaterializationSnapshotToken;
    out.provenanceMatches =
        out.inputValid &&
        out.sourceIdentityExact &&
        out.objectPrerequisiteSnapshotMatches &&
        out.creationHandoffSnapshotMatches &&
        out.targetBytecodeMaterializationSnapshotMatches &&
        sourceIdentity.cacheKey != 0 &&
        objectPrerequisite.cacheKey == sourceIdentity.cacheKey &&
        creationHandoff.cacheKey == sourceIdentity.cacheKey &&
        targetBytecodeMaterialization.cacheKey == sourceIdentity.cacheKey &&
        creationHandoff.objectPrerequisiteSnapshotToken ==
            objectPrerequisiteSnapshotToken &&
        creationHandoff.vertexBytecodeHash ==
            sourceIdentity.vertexShader.bytecodeHash &&
        creationHandoff.pixelBytecodeHash ==
            sourceIdentity.pixelShader.bytecodeHash &&
        targetBytecodeMaterialization.sourceVertexBytecodeHash ==
            sourceIdentity.vertexShader.bytecodeHash &&
        targetBytecodeMaterialization.sourcePixelBytecodeHash ==
            sourceIdentity.pixelShader.bytecodeHash &&
        out.objectMaterializerRevisionHash != 0;
    if (!out.provenanceMatches)
        return out;

    if (!cache.ready()) {
        out.cacheInitialized = cache.initialize(expectedDevice);
    } else {
        out.cacheInitialized = cache.device() == expectedDevice;
    }
    if (!out.cacheInitialized ||
        cache.device() != expectedDevice ||
        !cache.cache_for_observation(sourceIdentity))
        return out;

    const auto cacheReady = cache.readiness(expectedDevice, sourceIdentity);
    out.cacheEntryReady = cacheReady.ready;
    out.cacheSnapshotToken = cacheReady.snapshotToken;
    out.cacheSnapshotMatches =
        cacheReady.ready &&
        cache.validate_snapshot(
            expectedDevice, sourceIdentity, cacheReady.snapshotToken);
    out.ownerGeneration = cacheReady.ownerGeneration;
    if (!out.cacheEntryReady ||
        !out.cacheSnapshotMatches ||
        out.cacheSnapshotToken == 0 ||
        out.ownerGeneration == 0)
        return out;

    out.translationSlotReserved =
        cache.reserve_translation_slot_for_observation(
            expectedDevice, sourceIdentity, out.cacheSnapshotToken);
    const auto slotReady =
        cache.translation_slot_ownership_readiness(
            expectedDevice, sourceIdentity, out.cacheSnapshotToken);
    out.translationSlotReady = slotReady.ownershipReady;
    out.slotSnapshotToken = slotReady.snapshotToken;
    out.slotSnapshotMatches =
        slotReady.ownershipReady &&
        slotReady.snapshotToken != 0 &&
        cache.validate_translation_slot_snapshot(
            expectedDevice,
            sourceIdentity,
            out.cacheSnapshotToken,
            slotReady.snapshotToken);
    out.slotGeneration = slotReady.slotGeneration;
    if (!out.translationSlotReserved ||
        !out.translationSlotReady ||
        !out.slotSnapshotMatches ||
        out.slotGeneration == 0)
        return out;

    const auto beforeObjects =
        cache.translation_object_readiness(
            expectedDevice,
            sourceIdentity,
            out.cacheSnapshotToken,
            out.slotSnapshotToken);
    out.objectsAbsentBeforeMaterialization =
        !beforeObjects.objectsAttached &&
        !beforeObjects.attachmentReady &&
        beforeObjects.translationObjectReceiptGeneration == 0 &&
        beforeObjects.snapshotToken == 0;
    if (!out.objectsAbsentBeforeMaterialization)
        return out;

    Microsoft::WRL::ComPtr<ID3D11VertexShader> vertexShader;
    Microsoft::WRL::ComPtr<ID3D11PixelShader> pixelShader;
    out.vertexObjectCreated =
        SUCCEEDED(expectedDevice->CreateVertexShader(
            targetBytecodeMaterialization.vertexTargetBytecode.data(),
            targetBytecodeMaterialization.vertexTargetBytecodeBytes,
            nullptr,
            vertexShader.ReleaseAndGetAddressOf())) &&
        vertexShader;
    out.pixelObjectCreated =
        SUCCEEDED(expectedDevice->CreatePixelShader(
            targetBytecodeMaterialization.pixelTargetBytecode.data(),
            targetBytecodeMaterialization.pixelTargetBytecodeBytes,
            nullptr,
            pixelShader.ReleaseAndGetAddressOf())) &&
        pixelShader;
    if (!out.vertexObjectCreated || !out.pixelObjectCreated)
        return out;

    Microsoft::WRL::ComPtr<ID3D11Device> vertexDevice;
    Microsoft::WRL::ComPtr<ID3D11Device> pixelDevice;
    vertexShader->GetDevice(vertexDevice.ReleaseAndGetAddressOf());
    pixelShader->GetDevice(pixelDevice.ReleaseAndGetAddressOf());
    out.objectDevicesMatch =
        vertexDevice.Get() == expectedDevice &&
        pixelDevice.Get() == expectedDevice;
    if (!out.objectDevicesMatch)
        return out;

    out.objectsAttached =
        cache.attach_translation_objects_for_observation(
            expectedDevice,
            sourceIdentity,
            out.cacheSnapshotToken,
            out.slotSnapshotToken,
            vertexShader.Get(),
            pixelShader.Get());
    if (!out.objectsAttached)
        return out;

    const auto objectReady =
        cache.translation_object_readiness(
            expectedDevice,
            sourceIdentity,
            out.cacheSnapshotToken,
            out.slotSnapshotToken);
    out.translationObjectReceiptReady =
        objectReady.attachmentReady &&
        objectReady.objectsAttached &&
        objectReady.objectDevicesMatch &&
        objectReady.cacheKey == sourceIdentity.cacheKey &&
        objectReady.ownerGeneration == out.ownerGeneration &&
        objectReady.slotGeneration == out.slotGeneration &&
        objectReady.translationObjectReceiptGeneration != 0 &&
        objectReady.snapshotToken != 0 &&
        cache.validate_translation_object_snapshot(
            expectedDevice,
            sourceIdentity,
            out.cacheSnapshotToken,
            out.slotSnapshotToken,
            objectReady.snapshotToken);
    out.translationObjectReceiptGeneration =
        objectReady.translationObjectReceiptGeneration;
    out.translationObjectSnapshotToken = objectReady.snapshotToken;

    out.boundaryPreserved =
        out.provenanceMatches &&
        out.cacheSnapshotMatches &&
        out.slotSnapshotMatches &&
        out.objectsAbsentBeforeMaterialization &&
        out.vertexObjectCreated &&
        out.pixelObjectCreated &&
        out.objectsAttached &&
        out.objectDevicesMatch &&
        out.translationObjectReceiptReady &&
        !out.objectBindingAuthorized &&
        out.diagnosticOnly;
    out.reviewReady = out.boundaryPreserved;
    if (out.reviewReady)
        out.reviewSnapshotToken =
            r284_object_materialization_snapshot_token(out);
    return out;
}

bool validate_programmable_shader_object_materialization_snapshot(
    ID3D11Device* expectedDevice,
    const NativeProgrammableShaderPairCache& cache,
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderTranslationObjectPrerequisiteEvidence&
        objectPrerequisite,
    std::uint64_t objectPrerequisiteSnapshotToken,
    const NativeProgrammableShaderObjectCreationHandoffEvidence& creationHandoff,
    std::uint64_t creationHandoffSnapshotToken,
    const NativeProgrammableShaderTargetBytecodeMaterializationEvidence&
        targetBytecodeMaterialization,
    std::uint64_t targetBytecodeMaterializationSnapshotToken,
    const NativeProgrammableShaderObjectMaterializationEvidence& materialization,
    std::uint64_t reviewSnapshotToken) noexcept {
    if (!expectedDevice ||
        reviewSnapshotToken == 0 ||
        materialization.reviewSnapshotToken != reviewSnapshotToken ||
        !materialization.reviewReady ||
        !materialization.boundaryPreserved ||
        !materialization.diagnosticOnly ||
        materialization.objectBindingAuthorized ||
        !materialization.translationObjectReceiptReady)
        return false;

    if (!sourceIdentity.exact_identity() ||
        sourceIdentity.translationImplemented ||
        !objectPrerequisite.reviewReady ||
        objectPrerequisite.reviewSnapshotToken !=
            objectPrerequisiteSnapshotToken ||
        !creationHandoff.reviewReady ||
        creationHandoff.reviewSnapshotToken !=
            creationHandoffSnapshotToken ||
        creationHandoff.objectCreationAuthorized ||
        !targetBytecodeMaterialization.reviewReady ||
        !targetBytecodeMaterialization.targetBytecodeMaterialized ||
        targetBytecodeMaterialization.objectCreationAuthorized ||
        targetBytecodeMaterialization.reviewSnapshotToken !=
            targetBytecodeMaterializationSnapshotToken ||
        r283_materialization_snapshot_token(targetBytecodeMaterialization) !=
            targetBytecodeMaterializationSnapshotToken)
        return false;

    if (!cache.ready() ||
        cache.device() != expectedDevice ||
        materialization.cacheKey != sourceIdentity.cacheKey ||
        materialization.cacheKey != objectPrerequisite.cacheKey ||
        materialization.cacheKey != creationHandoff.cacheKey ||
        materialization.cacheKey != targetBytecodeMaterialization.cacheKey ||
        materialization.targetVertexBytecodeHash !=
            targetBytecodeMaterialization.vertexTargetBytecodeHash ||
        materialization.targetPixelBytecodeHash !=
            targetBytecodeMaterialization.pixelTargetBytecodeHash ||
        materialization.vertexMaterializedArtifactIdentity !=
            targetBytecodeMaterialization.vertexMaterializedArtifactIdentity ||
        materialization.pixelMaterializedArtifactIdentity !=
            targetBytecodeMaterialization.pixelMaterializedArtifactIdentity ||
        materialization.objectMaterializerRevisionHash !=
            r284_object_materializer_revision_hash() ||
        materialization.objectPrerequisiteSnapshotToken !=
            objectPrerequisiteSnapshotToken ||
        materialization.creationHandoffSnapshotToken !=
            creationHandoffSnapshotToken ||
        materialization.targetBytecodeMaterializationSnapshotToken !=
            targetBytecodeMaterializationSnapshotToken)
        return false;

    const auto cacheReady = cache.readiness(expectedDevice, sourceIdentity);
    if (!cacheReady.ready ||
        cacheReady.ownerGeneration != materialization.ownerGeneration ||
        cacheReady.snapshotToken != materialization.cacheSnapshotToken ||
        !cache.validate_snapshot(
            expectedDevice,
            sourceIdentity,
            materialization.cacheSnapshotToken))
        return false;

    const auto slotReady =
        cache.translation_slot_ownership_readiness(
            expectedDevice,
            sourceIdentity,
            materialization.cacheSnapshotToken);
    if (!slotReady.ownershipReady ||
        slotReady.slotGeneration != materialization.slotGeneration ||
        slotReady.snapshotToken != materialization.slotSnapshotToken ||
        !cache.validate_translation_slot_snapshot(
            expectedDevice,
            sourceIdentity,
            materialization.cacheSnapshotToken,
            materialization.slotSnapshotToken))
        return false;

    const auto objectReady =
        cache.translation_object_readiness(
            expectedDevice,
            sourceIdentity,
            materialization.cacheSnapshotToken,
            materialization.slotSnapshotToken);
    if (!objectReady.attachmentReady ||
        !objectReady.objectsAttached ||
        !objectReady.objectDevicesMatch ||
        objectReady.translationObjectReceiptGeneration !=
            materialization.translationObjectReceiptGeneration ||
        objectReady.snapshotToken !=
            materialization.translationObjectSnapshotToken ||
        !cache.validate_translation_object_snapshot(
            expectedDevice,
            sourceIdentity,
            materialization.cacheSnapshotToken,
            materialization.slotSnapshotToken,
            materialization.translationObjectSnapshotToken))
        return false;

    return r284_object_materialization_snapshot_token(materialization) ==
        reviewSnapshotToken;
}

NativeProgrammableShaderTranslatedSemanticReceipt
compose_programmable_shader_translated_semantic_receipt(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderTranslationObjectReadiness& translationObject,
    std::uint64_t translationObjectSnapshotToken,
    const NativeProgrammableShaderSourceMappingHandoff& sourceMappingHandoff,
    std::uint64_t sourceMappingHandoffSnapshotToken,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence& translationPlan,
    std::uint64_t translationPlanSnapshotToken) noexcept {
    NativeProgrammableShaderTranslatedSemanticReceipt out{};

    out.cacheKey = sourceIdentity.cacheKey;
    out.vertexVersionToken = sourceIdentity.vertexShader.versionToken;
    out.pixelVersionToken = sourceIdentity.pixelShader.versionToken;
    out.vertexBytecodeHash = sourceIdentity.vertexShader.bytecodeHash;
    out.pixelBytecodeHash = sourceIdentity.pixelShader.bytecodeHash;
    out.translatedVertexSemanticHash =
        translationPlan.targetVertexSemanticHash;
    out.translatedPixelSemanticHash =
        translationPlan.targetPixelSemanticHash;
    out.translatorRevisionHash = translationPlan.translatorRevisionHash;
    out.semanticContractHash = translationPlan.semanticContractHash;
    out.sourcePairSemanticHash = translationPlan.sourcePairSemanticHash;
    out.sourceConstantMappingHash =
        translationPlan.sourceConstantMappingHash;
    out.sourceSamplerMappingHash =
        translationPlan.sourceSamplerMappingHash;
    out.sourceMappingPlanRevisionHash =
        sourceMappingHandoff.mappingPlanRevisionHash;
    out.sourceMappingSemanticContractHash =
        sourceMappingHandoff.mappingSemanticContractHash;
    out.translationObjectSnapshotToken = translationObjectSnapshotToken;
    out.sourceMappingHandoffSnapshotToken =
        sourceMappingHandoffSnapshotToken;
    out.translationPlanSnapshotToken = translationPlanSnapshotToken;

    out.inputValid =
        translationObjectSnapshotToken != 0 &&
        sourceMappingHandoffSnapshotToken != 0 &&
        translationPlanSnapshotToken != 0;
    out.sourceIdentityExact =
        sourceIdentity.exact_identity() &&
        !sourceIdentity.translationImplemented;
    out.translationObjectReady =
        translationObject.attachmentReady &&
        translationObject.objectsAttached &&
        translationObject.objectDevicesMatch &&
        translationObject.cacheKey != 0 &&
        translationObject.snapshotToken != 0;
    out.translationObjectSnapshotMatches =
        out.translationObjectReady &&
        translationObject.snapshotToken == translationObjectSnapshotToken;
    out.sourceMappingHandoffReady =
        sourceMappingHandoff.reviewReady &&
        sourceMappingHandoff.boundaryPreserved &&
        sourceMappingHandoff.diagnosticOnly &&
        sourceMappingHandoff.sourceReceiptIdentityMatches &&
        sourceMappingHandoff.mappingPlanIdentityMatches &&
        sourceMappingHandoff.constantRegisterMappingExact &&
        sourceMappingHandoff.samplerMappingExact &&
        sourceMappingHandoff.cacheKey != 0 &&
        sourceMappingHandoff.reviewSnapshotToken != 0;
    out.sourceMappingHandoffSnapshotMatches =
        out.sourceMappingHandoffReady &&
        sourceMappingHandoff.reviewSnapshotToken ==
            sourceMappingHandoffSnapshotToken;
    out.translationPlanReady =
        translationPlan.reviewReady &&
        translationPlan.boundaryPreserved &&
        translationPlan.diagnosticOnly &&
        translationPlan.provenanceMatches &&
        translationPlan.vertexSemanticExact &&
        translationPlan.pixelSemanticExact &&
        translationPlan.reviewSnapshotToken != 0;
    out.translationPlanSnapshotMatches =
        out.translationPlanReady &&
        translationPlan.reviewSnapshotToken ==
            translationPlanSnapshotToken;
    out.cacheIdentityMatches =
        out.sourceIdentityExact &&
        out.translationObjectSnapshotMatches &&
        out.sourceMappingHandoffSnapshotMatches &&
        out.translationPlanSnapshotMatches &&
        translationObject.cacheKey == sourceIdentity.cacheKey &&
        sourceMappingHandoff.cacheKey == sourceIdentity.cacheKey &&
        translationPlan.cacheKey == sourceIdentity.cacheKey &&
        translationPlan.sourcePairSemanticHash ==
            sourceMappingHandoff.pairSemanticHash &&
        translationPlan.sourceConstantMappingHash ==
            sourceMappingHandoff.constantMappingHash &&
        translationPlan.sourceSamplerMappingHash ==
            sourceMappingHandoff.samplerMappingHash;
    out.vertexSemanticExact =
        out.cacheIdentityMatches &&
        translationPlan.vertexSemanticExact &&
        translationPlan.targetVertexSemanticHash != 0;
    out.pixelSemanticExact =
        out.cacheIdentityMatches &&
        translationPlan.pixelSemanticExact &&
        translationPlan.targetPixelSemanticHash != 0;
    out.constantRegisterMappingExact =
        out.cacheIdentityMatches &&
        sourceMappingHandoff.constantRegisterMappingExact &&
        sourceMappingHandoff.constantMappingHash != 0;
    out.samplerMappingExact =
        out.cacheIdentityMatches &&
        sourceMappingHandoff.samplerMappingExact &&
        sourceMappingHandoff.samplerMappingHash != 0;

    out.diagnosticOnly = true;
    out.boundaryPreserved =
        out.cacheIdentityMatches &&
        out.vertexSemanticExact &&
        out.pixelSemanticExact &&
        out.constantRegisterMappingExact &&
        out.samplerMappingExact &&
        out.diagnosticOnly;
    out.reviewReady =
        out.inputValid &&
        out.boundaryPreserved;

    if (out.reviewReady) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(token, out.cacheKey);
        token = mix_readiness_snapshot_token(token, out.vertexVersionToken);
        token = mix_readiness_snapshot_token(token, out.pixelVersionToken);
        token = mix_readiness_snapshot_token(token, out.vertexBytecodeHash);
        token = mix_readiness_snapshot_token(token, out.pixelBytecodeHash);
        token = mix_readiness_snapshot_token(
            token, out.translatedVertexSemanticHash);
        token = mix_readiness_snapshot_token(
            token, out.translatedPixelSemanticHash);
        token = mix_readiness_snapshot_token(token, out.translatorRevisionHash);
        token = mix_readiness_snapshot_token(token, out.semanticContractHash);
        token = mix_readiness_snapshot_token(
            token, out.sourcePairSemanticHash);
        token = mix_readiness_snapshot_token(
            token, out.sourceConstantMappingHash);
        token = mix_readiness_snapshot_token(
            token, out.sourceSamplerMappingHash);
        token = mix_readiness_snapshot_token(
            token, out.sourceMappingPlanRevisionHash);
        token = mix_readiness_snapshot_token(
            token, out.sourceMappingSemanticContractHash);
        token = mix_readiness_snapshot_token(
            token, out.translationObjectSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.sourceMappingHandoffSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.translationPlanSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.vertexSemanticExact ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.pixelSemanticExact ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.constantRegisterMappingExact ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.samplerMappingExact ? 1u : 0u);
        token = mix_readiness_snapshot_token(token, 0x275276u);
        out.reviewSnapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_programmable_shader_translated_semantic_receipt_snapshot(
    const NativeProgrammableShaderTranslatedSemanticReceipt& receipt,
    std::uint64_t reviewSnapshotToken) noexcept {
    if (reviewSnapshotToken == 0 ||
        !receipt.reviewReady ||
        !receipt.boundaryPreserved ||
        !receipt.translationPlanReady ||
        !receipt.translationPlanSnapshotMatches ||
        !receipt.cacheIdentityMatches ||
        !receipt.vertexSemanticExact ||
        !receipt.pixelSemanticExact ||
        !receipt.constantRegisterMappingExact ||
        !receipt.samplerMappingExact)
        return false;

    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(token, receipt.cacheKey);
    token = mix_readiness_snapshot_token(token, receipt.vertexVersionToken);
    token = mix_readiness_snapshot_token(token, receipt.pixelVersionToken);
    token = mix_readiness_snapshot_token(token, receipt.vertexBytecodeHash);
    token = mix_readiness_snapshot_token(token, receipt.pixelBytecodeHash);
    token = mix_readiness_snapshot_token(
        token, receipt.translatedVertexSemanticHash);
    token = mix_readiness_snapshot_token(
        token, receipt.translatedPixelSemanticHash);
    token = mix_readiness_snapshot_token(token, receipt.translatorRevisionHash);
    token = mix_readiness_snapshot_token(token, receipt.semanticContractHash);
    token = mix_readiness_snapshot_token(
        token, receipt.sourcePairSemanticHash);
    token = mix_readiness_snapshot_token(
        token, receipt.sourceConstantMappingHash);
    token = mix_readiness_snapshot_token(
        token, receipt.sourceSamplerMappingHash);
    token = mix_readiness_snapshot_token(
        token, receipt.sourceMappingPlanRevisionHash);
    token = mix_readiness_snapshot_token(
        token, receipt.sourceMappingSemanticContractHash);
    token = mix_readiness_snapshot_token(
        token, receipt.translationObjectSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, receipt.sourceMappingHandoffSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, receipt.translationPlanSnapshotToken);
    token = mix_readiness_snapshot_token(
        token, receipt.vertexSemanticExact ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, receipt.pixelSemanticExact ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, receipt.constantRegisterMappingExact ? 1u : 0u);
    token = mix_readiness_snapshot_token(
        token, receipt.samplerMappingExact ? 1u : 0u);
    token = mix_readiness_snapshot_token(token, 0x275276u);
    const auto expected = token == 0 ? 1 : token;
    return receipt.reviewSnapshotToken == reviewSnapshotToken &&
        expected == reviewSnapshotToken;
}

NativeProgrammableShaderSemanticTranslationReadiness
compose_programmable_shader_semantic_translation_readiness(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderTranslationObjectReadiness& translationObject,
    std::uint64_t translationObjectSnapshotToken,
    const NativeProgrammableShaderInputLayoutReadiness& inputLayout,
    std::uint64_t inputLayoutSnapshotToken,
    const NativeProgrammableShaderTranslatedSemanticReceipt&
        translatedSemanticReceipt,
    std::uint64_t translatedSemanticReceiptSnapshotToken,
    const ProgrammableShaderInterfaceLinkageEvidence& sourceInterfaceLinkage) noexcept {
    NativeProgrammableShaderSemanticTranslationReadiness out{};

    out.cacheKey = sourceIdentity.cacheKey;
    out.vertexVersionToken = sourceIdentity.vertexShader.versionToken;
    out.pixelVersionToken = sourceIdentity.pixelShader.versionToken;
    out.vertexBytecodeHash = sourceIdentity.vertexShader.bytecodeHash;
    out.pixelBytecodeHash = sourceIdentity.pixelShader.bytecodeHash;
    out.translatedVertexSemanticHash =
        translatedSemanticReceipt.translatedVertexSemanticHash;
    out.translatedPixelSemanticHash =
        translatedSemanticReceipt.translatedPixelSemanticHash;
    out.interfaceLinkHash = sourceInterfaceLinkage.interfaceLinkHash;
    out.translatorRevisionHash =
        translatedSemanticReceipt.translatorRevisionHash;
    out.semanticContractHash =
        translatedSemanticReceipt.semanticContractHash;
    out.sourcePairSemanticHash =
        translatedSemanticReceipt.sourcePairSemanticHash;
    out.sourceConstantMappingHash =
        translatedSemanticReceipt.sourceConstantMappingHash;
    out.sourceSamplerMappingHash =
        translatedSemanticReceipt.sourceSamplerMappingHash;
    out.sourceMappingPlanRevisionHash =
        translatedSemanticReceipt.sourceMappingPlanRevisionHash;
    out.sourceMappingSemanticContractHash =
        translatedSemanticReceipt.sourceMappingSemanticContractHash;
    out.translationObjectSnapshotToken = translationObjectSnapshotToken;
    out.inputLayoutSnapshotToken = inputLayoutSnapshotToken;
    out.translatedSemanticReceiptSnapshotToken =
        translatedSemanticReceiptSnapshotToken;
    out.sourceMappingHandoffSnapshotToken =
        translatedSemanticReceipt.sourceMappingHandoffSnapshotToken;

    out.inputValid =
        translationObjectSnapshotToken != 0 &&
        inputLayoutSnapshotToken != 0 &&
        translatedSemanticReceiptSnapshotToken != 0 &&
        sourceInterfaceLinkage.exact();
    out.sourceIdentityExact =
        sourceIdentity.exact_identity() &&
        !sourceIdentity.translationImplemented;

    out.translationObjectReady =
        translationObject.attachmentReady &&
        translationObject.objectsAttached &&
        translationObject.objectDevicesMatch &&
        translationObject.cacheKey != 0 &&
        translationObject.snapshotToken != 0;
    out.translationObjectSnapshotMatches =
        out.translationObjectReady &&
        translationObject.snapshotToken == translationObjectSnapshotToken;

    out.inputLayoutReady =
        inputLayout.attachmentReady &&
        inputLayout.layoutIdentityExact &&
        inputLayout.inputLayoutAttached &&
        inputLayout.inputLayoutDeviceMatches &&
        inputLayout.cacheKey != 0 &&
        inputLayout.objectSnapshotToken != 0 &&
        inputLayout.snapshotToken != 0;
    out.inputLayoutSnapshotMatches =
        out.inputLayoutReady &&
        inputLayout.snapshotToken == inputLayoutSnapshotToken;

    out.cacheIdentityMatches =
        out.sourceIdentityExact &&
        translationObject.cacheKey == sourceIdentity.cacheKey &&
        inputLayout.cacheKey == sourceIdentity.cacheKey &&
        inputLayout.objectSnapshotToken == translationObjectSnapshotToken;

    out.translatedSemanticReceiptReady =
        validate_programmable_shader_translated_semantic_receipt_snapshot(
            translatedSemanticReceipt,
            translatedSemanticReceiptSnapshotToken);
    out.translatedSemanticReceiptSnapshotMatches =
        out.translatedSemanticReceiptReady &&
        translatedSemanticReceipt.reviewSnapshotToken ==
            translatedSemanticReceiptSnapshotToken;
    out.translatedSemanticIdentityMatches =
        out.translatedSemanticReceiptSnapshotMatches &&
        translatedSemanticReceipt.cacheKey == sourceIdentity.cacheKey &&
        translatedSemanticReceipt.vertexVersionToken ==
            sourceIdentity.vertexShader.versionToken &&
        translatedSemanticReceipt.pixelVersionToken ==
            sourceIdentity.pixelShader.versionToken &&
        translatedSemanticReceipt.vertexBytecodeHash ==
            sourceIdentity.vertexShader.bytecodeHash &&
        translatedSemanticReceipt.pixelBytecodeHash ==
            sourceIdentity.pixelShader.bytecodeHash &&
        translatedSemanticReceipt.translationObjectSnapshotToken ==
            translationObjectSnapshotToken;

    out.sourceMappingHandoffReady =
        out.translatedSemanticReceiptReady &&
        translatedSemanticReceipt.sourceMappingHandoffReady;
    out.sourceMappingHandoffSnapshotMatches =
        out.translatedSemanticIdentityMatches &&
        translatedSemanticReceipt.sourceMappingHandoffSnapshotMatches &&
        translatedSemanticReceipt.sourceMappingHandoffSnapshotToken != 0;
    out.sourceMappingIdentityMatches =
        out.translatedSemanticIdentityMatches &&
        out.sourceMappingHandoffSnapshotMatches;
    out.vertexSemanticExact =
        out.translatedSemanticIdentityMatches &&
        translatedSemanticReceipt.vertexSemanticExact;
    out.pixelSemanticExact =
        out.translatedSemanticIdentityMatches &&
        translatedSemanticReceipt.pixelSemanticExact;
    out.constantRegisterMappingExact =
        out.sourceMappingIdentityMatches &&
        translatedSemanticReceipt.constantRegisterMappingExact;
    out.samplerMappingExact =
        out.sourceMappingIdentityMatches &&
        translatedSemanticReceipt.samplerMappingExact;

    out.interfaceSourceIdentityMatches =
        sourceInterfaceLinkage.exact() &&
        sourceInterfaceLinkage.vertexVersionToken ==
            sourceIdentity.vertexShader.versionToken &&
        sourceInterfaceLinkage.pixelVersionToken ==
            sourceIdentity.pixelShader.versionToken &&
        sourceInterfaceLinkage.vertexSourceBytecodeHash ==
            sourceIdentity.vertexShader.bytecodeHash &&
        sourceInterfaceLinkage.pixelSourceBytecodeHash ==
            sourceIdentity.pixelShader.bytecodeHash;
    out.interfaceLinkExact =
        out.interfaceSourceIdentityMatches &&
        sourceInterfaceLinkage.interfaceLinkHash != 0 &&
        inputLayout.inputLayoutIdentity != 0;

    out.semanticProofPresent =
        out.sourceIdentityExact &&
        out.translationObjectSnapshotMatches &&
        out.inputLayoutSnapshotMatches &&
        out.cacheIdentityMatches &&
        out.translatedSemanticIdentityMatches &&
        out.sourceMappingIdentityMatches &&
        out.vertexSemanticExact &&
        out.pixelSemanticExact &&
        out.constantRegisterMappingExact &&
        out.samplerMappingExact &&
        out.interfaceLinkExact;

    out.diagnosticOnly = true;
    out.boundaryPreserved =
        out.semanticProofPresent &&
        out.diagnosticOnly;
    out.reviewReady =
        out.inputValid &&
        out.semanticProofPresent &&
        out.boundaryPreserved;

    if (out.reviewReady) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(token, out.cacheKey);
        token = mix_readiness_snapshot_token(token, out.vertexVersionToken);
        token = mix_readiness_snapshot_token(token, out.pixelVersionToken);
        token = mix_readiness_snapshot_token(token, out.vertexBytecodeHash);
        token = mix_readiness_snapshot_token(token, out.pixelBytecodeHash);
        token = mix_readiness_snapshot_token(
            token, out.translatedVertexSemanticHash);
        token = mix_readiness_snapshot_token(
            token, out.translatedPixelSemanticHash);
        token = mix_readiness_snapshot_token(token, out.interfaceLinkHash);
        token = mix_readiness_snapshot_token(token, out.translatorRevisionHash);
        token = mix_readiness_snapshot_token(token, out.semanticContractHash);
        token = mix_readiness_snapshot_token(
            token, out.sourcePairSemanticHash);
        token = mix_readiness_snapshot_token(
            token, out.sourceConstantMappingHash);
        token = mix_readiness_snapshot_token(
            token, out.sourceSamplerMappingHash);
        token = mix_readiness_snapshot_token(
            token, out.sourceMappingPlanRevisionHash);
        token = mix_readiness_snapshot_token(
            token, out.sourceMappingSemanticContractHash);
        token = mix_readiness_snapshot_token(
            token, out.translatedSemanticReceiptSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.sourceMappingHandoffSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.constantRegisterMappingExact ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.samplerMappingExact ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.translationObjectSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.inputLayoutSnapshotToken);
        token = mix_readiness_snapshot_token(token, 0x263275u);
        out.reviewSnapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_programmable_shader_semantic_translation_readiness_snapshot(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderTranslationObjectReadiness& translationObject,
    std::uint64_t translationObjectSnapshotToken,
    const NativeProgrammableShaderInputLayoutReadiness& inputLayout,
    std::uint64_t inputLayoutSnapshotToken,
    const NativeProgrammableShaderTranslatedSemanticReceipt&
        translatedSemanticReceipt,
    std::uint64_t translatedSemanticReceiptSnapshotToken,
    const ProgrammableShaderInterfaceLinkageEvidence& sourceInterfaceLinkage,
    std::uint64_t reviewSnapshotToken) noexcept {
    if (reviewSnapshotToken == 0)
        return false;
    const auto current =
        compose_programmable_shader_semantic_translation_readiness(
            sourceIdentity,
            translationObject, translationObjectSnapshotToken,
            inputLayout, inputLayoutSnapshotToken,
            translatedSemanticReceipt,
            translatedSemanticReceiptSnapshotToken,
            sourceInterfaceLinkage);
    return current.reviewReady &&
        current.reviewSnapshotToken == reviewSnapshotToken &&
        current.semanticProofPresent &&
        current.translatedSemanticReceiptReady &&
        current.translatedSemanticReceiptSnapshotMatches &&
        current.translatedSemanticIdentityMatches &&
        current.sourceMappingHandoffReady &&
        current.sourceMappingHandoffSnapshotMatches &&
        current.sourceMappingIdentityMatches &&
        current.vertexSemanticExact &&
        current.pixelSemanticExact &&
        current.constantRegisterMappingExact &&
        current.samplerMappingExact &&
        current.interfaceLinkExact;
}

NativeProgrammableShaderActivationPrerequisiteHandoff
compose_programmable_activation_prerequisite_handoff(
    const NativeProgrammableShaderDormantSourceRevalidationReadiness&
        sourceRevalidation,
    std::uint64_t sourceRevalidationSnapshotToken,
    const NativeProgrammableShaderOutputResourceBehaviorReadiness& resourceBehavior,
    std::uint64_t resourceBehaviorSnapshotToken,
    const NativeProgrammableShaderInputLayoutReadiness& inputLayout,
    std::uint64_t inputLayoutSnapshotToken,
    const NativeProgrammableShaderSemanticTranslationReadiness& shaderTranslation,
    std::uint64_t shaderTranslationSnapshotToken) noexcept {
    NativeProgrammableShaderActivationPrerequisiteHandoff out{};
    constexpr std::uint32_t kResourceBehaviorMissing = 1u << 0;
    constexpr std::uint32_t kInputLayoutMissing = 1u << 1;
    constexpr std::uint32_t kShaderTranslationMissing = 1u << 2;
    constexpr std::uint32_t kSourceIdentityMissing = 1u << 3;

    out.kind = sourceRevalidation.kind;
    out.indexed = sourceRevalidation.indexed;
    out.cacheKey = sourceRevalidation.cacheKey;
    out.sourceRevalidationSnapshotToken = sourceRevalidationSnapshotToken;
    out.resourceBehaviorSnapshotToken = resourceBehaviorSnapshotToken;
    out.inputLayoutSnapshotToken = inputLayoutSnapshotToken;
    out.shaderTranslationSnapshotToken = shaderTranslationSnapshotToken;
    out.inputValid =
        out.cacheKey != 0 &&
        sourceRevalidationSnapshotToken != 0 &&
        resourceBehaviorSnapshotToken != 0 &&
        inputLayoutSnapshotToken != 0 &&
        shaderTranslationSnapshotToken != 0;

    out.sourceRevalidationReady =
        sourceRevalidation.ready &&
        sourceRevalidation.boundaryPreserved &&
        sourceRevalidation.snapshotToken != 0;
    out.sourceRevalidationSnapshotMatches =
        out.sourceRevalidationReady &&
        sourceRevalidation.snapshotToken ==
            sourceRevalidationSnapshotToken;
    out.sourceRevalidationPayloadSnapshotMatches =
        out.sourceRevalidationReady &&
        sourceRevalidation.snapshotToken ==
            recompute_programmable_dormant_source_revalidation_payload_snapshot(
                sourceRevalidation);
    out.sourceIdentityMatches =
        out.sourceRevalidationSnapshotMatches &&
        out.sourceRevalidationPayloadSnapshotMatches &&
        out.cacheKey != 0 &&
        inputLayout.cacheKey == out.cacheKey &&
        shaderTranslation.cacheKey == out.cacheKey;

    out.resourceBehaviorReviewReady =
        resourceBehavior.reviewReady &&
        resourceBehavior.boundaryPreserved &&
        resourceBehavior.geometryResourceBehaviorExact &&
        resourceBehavior.textureResourceBehaviorExact &&
        resourceBehavior.outputResourceBehaviorExact &&
        resourceBehavior.fullResourceBehaviorProofPresent &&
        resourceBehavior.missingResourceScopeMask == 0 &&
        resourceBehavior.reviewSnapshotToken != 0 &&
        resourceBehavior.kind == out.kind &&
        resourceBehavior.indexed == out.indexed &&
        resourceBehavior.sourceRevalidationSnapshotToken ==
            sourceRevalidationSnapshotToken;
    out.resourceBehaviorSnapshotMatches =
        out.resourceBehaviorReviewReady &&
        resourceBehavior.reviewSnapshotToken ==
            resourceBehaviorSnapshotToken;
    // R304: the public R259 handoff must not trust stored/caller R262 token
    // equality alone. Reconstruct the complete R262 payload before any F18
    // proof bit may contribute to an activation prerequisite.
    out.resourceBehaviorPayloadSnapshotMatches =
        out.resourceBehaviorReviewReady &&
        resourceBehavior.reviewSnapshotToken ==
            recompute_programmable_output_resource_behavior_payload_snapshot(
                resourceBehavior);
    out.resourceBehaviorGeometryProofPresent =
        out.resourceBehaviorReviewReady &&
        out.resourceBehaviorSnapshotMatches &&
        out.resourceBehaviorPayloadSnapshotMatches &&
        resourceBehavior.geometryResourceBehaviorExact;
    out.resourceBehaviorTextureProofPresent =
        out.resourceBehaviorReviewReady &&
        out.resourceBehaviorSnapshotMatches &&
        out.resourceBehaviorPayloadSnapshotMatches &&
        resourceBehavior.textureResourceBehaviorExact;
    out.resourceBehaviorOutputProofPresent =
        out.resourceBehaviorReviewReady &&
        out.resourceBehaviorSnapshotMatches &&
        out.resourceBehaviorPayloadSnapshotMatches &&
        resourceBehavior.outputResourceBehaviorExact;
    out.resourceBehaviorCoverageComplete =
        out.resourceBehaviorGeometryProofPresent &&
        out.resourceBehaviorTextureProofPresent &&
        out.resourceBehaviorOutputProofPresent &&
        resourceBehavior.fullResourceBehaviorProofPresent &&
        resourceBehavior.missingResourceScopeMask == 0;

    out.inputLayoutOwnershipReady =
        inputLayout.attachmentReady &&
        inputLayout.layoutIdentityExact &&
        inputLayout.inputLayoutAttached &&
        inputLayout.inputLayoutDeviceMatches &&
        inputLayout.snapshotToken != 0;
    out.inputLayoutSnapshotMatches =
        out.inputLayoutOwnershipReady &&
        inputLayout.snapshotToken == inputLayoutSnapshotToken;

    out.shaderTranslationReviewReady =
        shaderTranslation.reviewReady &&
        shaderTranslation.boundaryPreserved &&
        shaderTranslation.semanticProofPresent &&
        shaderTranslation.cacheKey == inputLayout.cacheKey &&
        shaderTranslation.inputLayoutSnapshotToken == inputLayoutSnapshotToken &&
        shaderTranslation.reviewSnapshotToken != 0;
    out.shaderTranslationSnapshotMatches =
        out.shaderTranslationReviewReady &&
        shaderTranslation.reviewSnapshotToken ==
            shaderTranslationSnapshotToken;

    // R260+R261+R262 provide complete F18 resource behavior. R263 now binds
    // the exact R239 source identity to the R242/R243 translated-object and
    // input-layout receipts, closing the static F21 semantic-translation proof.
    // This still does not authorize NativeDrawPath or any Draw* dispatch.
    out.resourceBehaviorProofPresent =
        out.resourceBehaviorCoverageComplete;
    out.inputLayoutProofPresent =
        out.inputLayoutOwnershipReady &&
        out.inputLayoutSnapshotMatches;
    out.shaderTranslationProofPresent =
        out.shaderTranslationReviewReady &&
        out.shaderTranslationSnapshotMatches;
    // R290 prevents a valid R258/R262 draw/resource chain from being combined
    // with equally valid R243/R263 receipts belonging to another R239 pair.
    out.sourceIdentityProofPresent =
        out.sourceIdentityMatches;

    out.missingPrerequisiteMask = 0;
    if (!out.resourceBehaviorProofPresent)
        out.missingPrerequisiteMask |= kResourceBehaviorMissing;
    if (!out.inputLayoutProofPresent)
        out.missingPrerequisiteMask |= kInputLayoutMissing;
    if (!out.shaderTranslationProofPresent)
        out.missingPrerequisiteMask |= kShaderTranslationMissing;
    if (!out.sourceIdentityProofPresent)
        out.missingPrerequisiteMask |= kSourceIdentityMissing;

    out.activationPrerequisitesSatisfied =
        out.resourceBehaviorProofPresent &&
        out.inputLayoutProofPresent &&
        out.shaderTranslationProofPresent &&
        out.sourceIdentityProofPresent &&
        out.missingPrerequisiteMask == 0;

    out.diagnosticOnly = true;
    out.nativeDrawPathActivationAllowed = false;
    out.drawDispatchAuthorized = false;
    out.boundaryPreserved =
        sourceRevalidation.boundaryPreserved &&
        out.resourceBehaviorProofPresent &&
        out.inputLayoutProofPresent &&
        out.shaderTranslationProofPresent &&
        out.sourceIdentityProofPresent &&
        out.diagnosticOnly &&
        !out.nativeDrawPathActivationAllowed &&
        !out.drawDispatchAuthorized;

    out.reviewReady =
        out.inputValid &&
        out.sourceRevalidationReady &&
        out.sourceRevalidationSnapshotMatches &&
        out.resourceBehaviorProofPresent &&
        out.inputLayoutProofPresent &&
        out.shaderTranslationProofPresent &&
        out.sourceIdentityProofPresent &&
        out.boundaryPreserved;

    if (out.reviewReady) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.kind));
        token = mix_readiness_snapshot_token(token, out.indexed ? 1u : 0u);
        token = mix_readiness_snapshot_token(token, out.cacheKey);
        token = mix_readiness_snapshot_token(
            token, out.sourceRevalidationSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.sourceRevalidationPayloadSnapshotMatches ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.resourceBehaviorSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.resourceBehaviorPayloadSnapshotMatches ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.inputLayoutSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.shaderTranslationSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.missingPrerequisiteMask);
        token = mix_readiness_snapshot_token(
            token, out.resourceBehaviorGeometryProofPresent ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.resourceBehaviorTextureProofPresent ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.resourceBehaviorOutputProofPresent ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.resourceBehaviorCoverageComplete ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.inputLayoutProofPresent ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.shaderTranslationProofPresent ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.sourceIdentityProofPresent ? 1u : 0u);
        token = mix_readiness_snapshot_token(token, 0x259u);
        token = mix_readiness_snapshot_token(token, 0x290u);
        out.reviewSnapshotToken = token == 0 ? 1 : token;
    }

    out.activationSnapshotToken = 0;
    return out;
}

bool validate_programmable_activation_prerequisite_handoff_snapshot(
    const NativeProgrammableShaderDormantSourceRevalidationReadiness&
        sourceRevalidation,
    std::uint64_t sourceRevalidationSnapshotToken,
    const NativeProgrammableShaderOutputResourceBehaviorReadiness& resourceBehavior,
    std::uint64_t resourceBehaviorSnapshotToken,
    const NativeProgrammableShaderInputLayoutReadiness& inputLayout,
    std::uint64_t inputLayoutSnapshotToken,
    const NativeProgrammableShaderSemanticTranslationReadiness& shaderTranslation,
    std::uint64_t shaderTranslationSnapshotToken,
    std::uint64_t reviewSnapshotToken) noexcept {
    if (reviewSnapshotToken == 0)
        return false;
    const auto current = compose_programmable_activation_prerequisite_handoff(
        sourceRevalidation, sourceRevalidationSnapshotToken,
        resourceBehavior, resourceBehaviorSnapshotToken,
        inputLayout, inputLayoutSnapshotToken,
        shaderTranslation, shaderTranslationSnapshotToken);
    return current.reviewReady &&
        current.reviewSnapshotToken == reviewSnapshotToken &&
        current.resourceBehaviorGeometryProofPresent &&
        current.resourceBehaviorTextureProofPresent &&
        current.resourceBehaviorOutputProofPresent &&
        current.resourceBehaviorCoverageComplete &&
        current.resourceBehaviorProofPresent &&
        current.inputLayoutProofPresent &&
        current.shaderTranslationProofPresent &&
        current.sourceIdentityProofPresent &&
        current.missingPrerequisiteMask == 0 &&
        current.activationPrerequisitesSatisfied &&
        !current.nativeDrawPathActivationAllowed &&
        !current.drawDispatchAuthorized &&
        current.activationSnapshotToken == 0;
}
NativeProgrammableShaderDormantSourceRevalidationReadiness
NativeProgrammableShaderPairCache::
nonindexed_dormant_source_revalidation_readiness(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken,
    std::uint64_t constantBindingSnapshotToken,
    std::uint64_t pipelineBindingSnapshotToken,
    D3DPRIMITIVETYPE primitiveType,
    std::uint64_t topologyBindingSnapshotToken,
    const NativeManagedBufferShadow& vertexBuffer,
    std::uint64_t vertexBufferSnapshotToken,
    UINT vertexStride,
    UINT vertexOffset,
    std::uint64_t nonIndexedGeometryBindingSnapshotToken,
    UINT primitiveCount,
    UINT startVertexLocation,
    std::uint64_t candidateSnapshotToken,
    std::uint64_t preActivationSnapshotToken) const noexcept {
    const auto currentSource = nonindexed_direct_dispatch_readiness(
        expectedContext, expectedDevice, identity, cacheSnapshotToken,
        slotSnapshotToken, objectSnapshotToken, layout,
        inputLayoutSnapshotToken, constantStateSnapshotToken,
        constantPayloadSnapshotToken, constantBindingSnapshotToken,
        pipelineBindingSnapshotToken, primitiveType,
        topologyBindingSnapshotToken, vertexBuffer,
        vertexBufferSnapshotToken, vertexStride, vertexOffset,
        nonIndexedGeometryBindingSnapshotToken, primitiveCount,
        startVertexLocation);
    return compose_programmable_dormant_source_revalidation_readiness(
        currentSource, identity.cacheKey,
        candidateSnapshotToken, preActivationSnapshotToken);
}

NativeProgrammableShaderDormantSourceRevalidationReadiness
NativeProgrammableShaderPairCache::
indexed_dormant_source_revalidation_readiness(
    ID3D11DeviceContext* expectedContext,
    ID3D11Device* expectedDevice,
    const ProgrammableShaderPairCacheIdentity& identity,
    std::uint64_t cacheSnapshotToken,
    std::uint64_t slotSnapshotToken,
    std::uint64_t objectSnapshotToken,
    const VertexInputLayoutTranslation& layout,
    std::uint64_t inputLayoutSnapshotToken,
    std::uint64_t constantStateSnapshotToken,
    std::uint64_t constantPayloadSnapshotToken,
    std::uint64_t constantBindingSnapshotToken,
    std::uint64_t pipelineBindingSnapshotToken,
    D3DPRIMITIVETYPE primitiveType,
    std::uint64_t topologyBindingSnapshotToken,
    const NativeManagedBufferShadow& vertexBuffer,
    std::uint64_t vertexBufferSnapshotToken,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeManagedBufferShadow& indexBuffer,
    std::uint64_t indexBufferSnapshotToken,
    DXGI_FORMAT indexFormat,
    UINT indexOffset,
    std::uint64_t indexedGeometryBindingSnapshotToken,
    UINT primitiveCount,
    INT baseVertexIndex,
    UINT minVertexIndex,
    UINT numVertices,
    UINT startIndex,
    std::uint64_t directDispatchSnapshotToken,
    std::uint64_t sourceValueSnapshotToken,
    std::uint64_t liveIndexBindingSnapshotToken,
    std::uint64_t candidateSnapshotToken,
    std::uint64_t preActivationSnapshotToken) const noexcept {
    const auto currentSource = indexed_pre_draw_readiness(
        expectedContext, expectedDevice, identity, cacheSnapshotToken,
        slotSnapshotToken, objectSnapshotToken, layout,
        inputLayoutSnapshotToken, constantStateSnapshotToken,
        constantPayloadSnapshotToken, constantBindingSnapshotToken,
        pipelineBindingSnapshotToken, primitiveType,
        topologyBindingSnapshotToken, vertexBuffer,
        vertexBufferSnapshotToken, vertexStride, vertexOffset,
        indexBuffer, indexBufferSnapshotToken, indexFormat, indexOffset,
        indexedGeometryBindingSnapshotToken, primitiveCount,
        baseVertexIndex, minVertexIndex, numVertices, startIndex,
        directDispatchSnapshotToken, sourceValueSnapshotToken,
        liveIndexBindingSnapshotToken);
    return compose_programmable_dormant_source_revalidation_readiness(
        currentSource, identity.cacheKey,
        candidateSnapshotToken, preActivationSnapshotToken);
}

NativeFixedFunctionIndexedSourceRangeReadiness
compose_fixed_function_indexed_source_range_readiness(
    D3DPRIMITIVETYPE primitive,
    UINT primitiveCount,
    INT baseVertexIndex,
    UINT minVertexIndex,
    UINT numVertices,
    UINT startIndex) noexcept {
    NativeFixedFunctionIndexedSourceRangeReadiness out{};
    out.primitiveCount = primitiveCount;
    out.baseVertexIndex = baseVertexIndex;
    out.minVertexIndex = minVertexIndex;
    out.numVertices = numVertices;
    out.startIndex = startIndex;

    const auto topology = translate_primitive(primitive);
    out.topology = topology.value;

    UINT elementCount = 0;
    const bool countExact =
        direct_draw_element_count(primitive, primitiveCount, elementCount);
    out.elementCount = countExact ? elementCount : 0u;
    out.primitiveExact =
        topology.exact &&
        topology.value != D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED &&
        primitive != D3DPT_POINTLIST &&
        primitive != D3DPT_TRIANGLEFAN;

    const UINT maxValue = (std::numeric_limits<UINT>::max)();
    const bool vertexCountCompatible =
        primitiveCount == 0u || numVertices != 0u;
    bool vertexRangeFits = primitiveCount == 0u;
    bool effectiveVertexRangeFits = primitiveCount == 0u;
    if (numVertices != 0u) {
        const UINT spanMinusOne = numVertices - 1u;
        vertexRangeFits = minVertexIndex <= maxValue - spanMinusOne;
        if (vertexRangeFits) {
            out.maxVertexIndex = minVertexIndex + spanMinusOne;
            const std::int64_t effectiveMinVertex =
                static_cast<std::int64_t>(baseVertexIndex) +
                static_cast<std::int64_t>(minVertexIndex);
            const std::int64_t effectiveMaxVertex =
                static_cast<std::int64_t>(baseVertexIndex) +
                static_cast<std::int64_t>(out.maxVertexIndex);
            effectiveVertexRangeFits =
                effectiveMinVertex >= 0 &&
                effectiveMaxVertex >= effectiveMinVertex &&
                effectiveMaxVertex <=
                    static_cast<std::int64_t>(maxValue);
        } else {
            effectiveVertexRangeFits = false;
        }
    }
    out.vertexRangeExact =
        vertexCountCompatible && vertexRangeFits && effectiveVertexRangeFits;
    out.indexRangeExact =
        countExact && startIndex <= maxValue - elementCount;
    out.inputValid = out.primitiveExact && countExact;
    out.ready =
        out.inputValid &&
        out.vertexRangeExact &&
        out.indexRangeExact;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(primitive));
        token = mix_readiness_snapshot_token(token, primitiveCount);
        token = mix_readiness_snapshot_token(token, elementCount);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(baseVertexIndex));
        token = mix_readiness_snapshot_token(token, minVertexIndex);
        token = mix_readiness_snapshot_token(token, numVertices);
        token = mix_readiness_snapshot_token(token, out.maxVertexIndex);
        token = mix_readiness_snapshot_token(token, startIndex);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_indexed_source_range_snapshot(
    D3DPRIMITIVETYPE primitive,
    UINT primitiveCount,
    INT baseVertexIndex,
    UINT minVertexIndex,
    UINT numVertices,
    UINT startIndex,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = compose_fixed_function_indexed_source_range_readiness(
        primitive, primitiveCount, baseVertexIndex, minVertexIndex,
        numVertices, startIndex);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionIndexedDirectDispatchReadiness
compose_fixed_function_indexed_direct_dispatch_readiness(
    const NativeFixedFunctionDirectDrawDispatchReadiness& dispatch,
    const NativeFixedFunctionIndexedSourceRangeReadiness& sourceRange,
    const NativeFixedFunctionRenderTargetBoundDrawReadiness& boundDraw) noexcept {
    NativeFixedFunctionIndexedDirectDispatchReadiness out{};
    out.directDispatchSnapshotToken = dispatch.snapshotToken;
    out.sourceRangeSnapshotToken = sourceRange.snapshotToken;
    out.boundDrawSnapshotToken = boundDraw.snapshotToken;

    const bool boundDrawIntegrity =
        validate_fixed_function_render_target_bound_draw_readiness_integrity(
            boundDraw);
    out.inputValid =
        dispatch.ready &&
        sourceRange.ready &&
        dispatch.indexed &&
        dispatch.snapshotToken != 0 &&
        sourceRange.snapshotToken != 0 &&
        boundDrawIntegrity;
    out.directDispatchReady = dispatch.ready && dispatch.indexed;
    out.sourceRangeReady = sourceRange.ready;
    out.boundDrawReady = boundDrawIntegrity;
    out.dispatchMatchesSourceRange =
        out.inputValid &&
        dispatch.topology == sourceRange.topology &&
        dispatch.primitiveCount == sourceRange.primitiveCount &&
        dispatch.elementCount == sourceRange.elementCount &&
        dispatch.startIndexLocation == sourceRange.startIndex &&
        dispatch.baseVertexLocation == sourceRange.baseVertexIndex;
    out.boundDrawMatchesDispatch =
        boundDraw.snapshotToken != 0 &&
        boundDraw.snapshotToken == dispatch.renderTargetBoundDrawSnapshotToken;

    out.vertexBufferRangeExact = false;
    if (out.inputValid &&
        boundDraw.geometryRangeMetadataExact &&
        boundDraw.vertexStride != 0 &&
        boundDraw.vertexBufferByteWidth != 0) {
        if (sourceRange.elementCount == 0) {
            out.vertexBufferRangeExact = true;
        } else {
            const std::int64_t effectiveMaxVertex =
                static_cast<std::int64_t>(sourceRange.baseVertexIndex) +
                static_cast<std::int64_t>(sourceRange.maxVertexIndex);
            if (effectiveMaxVertex >= 0) {
                const std::uint64_t endByte =
                    static_cast<std::uint64_t>(boundDraw.vertexOffset) +
                    (static_cast<std::uint64_t>(effectiveMaxVertex) + 1ull) *
                        boundDraw.vertexStride;
                out.vertexBufferRangeExact =
                    endByte <= boundDraw.vertexBufferByteWidth;
            }
        }
    }

    out.componentSnapshotsPresent =
        dispatch.snapshotToken != 0 &&
        sourceRange.snapshotToken != 0 &&
        boundDraw.snapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.directDispatchReady &&
        out.sourceRangeReady &&
        out.boundDrawReady &&
        out.dispatchMatchesSourceRange &&
        out.boundDrawMatchesDispatch &&
        out.vertexBufferRangeExact &&
        out.componentSnapshotsPresent;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(token, out.directDispatchSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.sourceRangeSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.boundDrawSnapshotToken);
        token = mix_readiness_snapshot_token(token, 0x150u);
        token = mix_readiness_snapshot_token(
            token, out.vertexBufferRangeExact ? 0x151u : 0u);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}
bool validate_fixed_function_indexed_direct_dispatch_snapshot(
    const NativeFixedFunctionDirectDrawDispatchReadiness& dispatch,
    const NativeFixedFunctionIndexedSourceRangeReadiness& sourceRange,
    const NativeFixedFunctionRenderTargetBoundDrawReadiness& boundDraw,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current =
        compose_fixed_function_indexed_direct_dispatch_readiness(
            dispatch, sourceRange, boundDraw);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionIndexedSourceValueReadiness
compose_fixed_function_indexed_source_value_readiness(
    const NativeFixedFunctionDirectDrawDispatchReadiness& dispatch,
    const NativeFixedFunctionIndexedDirectDispatchReadiness& indexedLineage,
    const NativeFixedFunctionIndexedSourceRangeReadiness& sourceRange,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeManagedIndexRangeReadiness& sourceValues) noexcept {

    NativeFixedFunctionIndexedSourceValueReadiness out{};
    out.directDispatchSnapshotToken = dispatch.snapshotToken;
    out.indexedLineageSnapshotToken = indexedLineage.snapshotToken;
    out.sourceRangeSnapshotToken = sourceRange.snapshotToken;
    out.geometrySnapshotToken = geometry.snapshotToken;
    out.sourceValuesSnapshotToken = sourceValues.snapshotToken;

    out.inputValid =
        dispatch.ready &&
        dispatch.indexed &&
        indexedLineage.ready &&
        sourceRange.ready &&
        geometry.ready &&
        sourceValues.ready;
    out.directDispatchReady = dispatch.ready && dispatch.indexed;
    out.indexedLineageReady = indexedLineage.ready;
    out.sourceRangeReady = sourceRange.ready;
    out.geometryReady =
        geometry.ready &&
        geometry.indexBufferRequired &&
        geometry.indexBufferReady;
    out.sourceValuesReady = sourceValues.ready;
    out.dispatchMatchesLineage =
        indexedLineage.directDispatchSnapshotToken == dispatch.snapshotToken &&
        indexedLineage.sourceRangeSnapshotToken == sourceRange.snapshotToken;
    out.geometryMatchesSourceValues =
        dispatch.geometrySnapshotToken == geometry.snapshotToken &&
        geometry.indexBufferSnapshotToken == sourceValues.mirrorSnapshotToken;
    out.sourceValuesMatchRange =
        sourceValues.startIndex == sourceRange.startIndex &&
        sourceValues.indexCount == sourceRange.elementCount &&
        sourceValues.minVertexIndex == sourceRange.minVertexIndex &&
        sourceValues.maxVertexIndex == sourceRange.maxVertexIndex;
    out.componentSnapshotsPresent =
        dispatch.snapshotToken != 0 &&
        indexedLineage.snapshotToken != 0 &&
        sourceRange.snapshotToken != 0 &&
        geometry.snapshotToken != 0 &&
        sourceValues.snapshotToken != 0 &&
        sourceValues.mirrorSnapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.directDispatchReady &&
        out.indexedLineageReady &&
        out.sourceRangeReady &&
        out.geometryReady &&
        out.sourceValuesReady &&
        out.dispatchMatchesLineage &&
        out.geometryMatchesSourceValues &&
        out.sourceValuesMatchRange &&
        out.componentSnapshotsPresent;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.directDispatchSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.indexedLineageSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.sourceRangeSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.geometrySnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.sourceValuesSnapshotToken);
        token = mix_readiness_snapshot_token(token, 0x152u);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_indexed_source_value_snapshot(
    const NativeFixedFunctionDirectDrawDispatchReadiness& dispatch,
    const NativeFixedFunctionIndexedDirectDispatchReadiness& indexedLineage,
    const NativeFixedFunctionIndexedSourceRangeReadiness& sourceRange,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeManagedIndexRangeReadiness& sourceValues,
    std::uint64_t snapshotToken) noexcept {

    if (snapshotToken == 0)
        return false;
    const auto current =
        compose_fixed_function_indexed_source_value_readiness(
            dispatch, indexedLineage, sourceRange, geometry, sourceValues);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionIndexedSourceBindingReadiness
compose_fixed_function_indexed_source_binding_readiness(
    const NativeFixedFunctionIndexedSourceValueReadiness& sourceValueLineage,
    const NativeFixedFunctionDirectDrawDispatchReadiness& dispatch,
    const NativeFixedFunctionIndexedDirectDispatchReadiness& indexedLineage,
    const NativeFixedFunctionIndexedSourceRangeReadiness& sourceRange,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeManagedIndexRangeReadiness& sourceValues,
    const NativeFixedFunctionRenderTargetBoundDrawReadiness& boundDraw) noexcept {

    NativeFixedFunctionIndexedSourceBindingReadiness out{};
    out.sourceIndexFormat = sourceValues.sourceIndexFormat;
    out.boundIndexFormat = boundDraw.indexFormat;
    out.boundIndexOffset = boundDraw.indexOffset;
    out.sourceValueLineageSnapshotToken = sourceValueLineage.snapshotToken;
    out.indexedLineageSnapshotToken = indexedLineage.snapshotToken;
    out.boundDrawSnapshotToken = boundDraw.snapshotToken;

    out.sourceValueLineageReady =
        validate_fixed_function_indexed_source_value_snapshot(
            dispatch, indexedLineage, sourceRange, geometry, sourceValues,
            sourceValueLineage.snapshotToken);
    out.boundDrawReady =
        validate_fixed_function_render_target_bound_draw_readiness_integrity(
            boundDraw);
    out.boundDrawMatchesLineage =
        indexedLineage.boundDrawSnapshotToken != 0 &&
        indexedLineage.boundDrawSnapshotToken == boundDraw.snapshotToken &&
        dispatch.renderTargetBoundDrawSnapshotToken != 0 &&
        dispatch.renderTargetBoundDrawSnapshotToken == boundDraw.snapshotToken;

    const DXGI_FORMAT expectedIndexFormat =
        sourceValues.sourceIndexFormat == D3DFMT_INDEX16
            ? DXGI_FORMAT_R16_UINT
            : sourceValues.sourceIndexFormat == D3DFMT_INDEX32
                ? DXGI_FORMAT_R32_UINT
                : DXGI_FORMAT_UNKNOWN;
    out.indexFormatMatchesSourceValues =
        expectedIndexFormat != DXGI_FORMAT_UNKNOWN &&
        boundDraw.indexFormat == expectedIndexFormat;
    out.indexOffsetExact = boundDraw.indexOffset == 0u;
    out.componentSnapshotsPresent =
        sourceValueLineage.snapshotToken != 0 &&
        indexedLineage.snapshotToken != 0 &&
        boundDraw.snapshotToken != 0;
    out.inputValid =
        sourceValueLineage.ready &&
        indexedLineage.ready &&
        dispatch.ready &&
        dispatch.indexed &&
        sourceRange.ready &&
        geometry.ready &&
        sourceValues.ready;
    out.ready =
        out.inputValid &&
        out.sourceValueLineageReady &&
        out.boundDrawReady &&
        out.boundDrawMatchesLineage &&
        out.indexFormatMatchesSourceValues &&
        out.indexOffsetExact &&
        out.componentSnapshotsPresent;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.sourceValueLineageSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.indexedLineageSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.boundDrawSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.sourceIndexFormat));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.boundIndexFormat));
        token = mix_readiness_snapshot_token(token, out.boundIndexOffset);
        token = mix_readiness_snapshot_token(token, 0x153u);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_indexed_source_binding_snapshot(
    const NativeFixedFunctionIndexedSourceValueReadiness& sourceValueLineage,
    const NativeFixedFunctionDirectDrawDispatchReadiness& dispatch,
    const NativeFixedFunctionIndexedDirectDispatchReadiness& indexedLineage,
    const NativeFixedFunctionIndexedSourceRangeReadiness& sourceRange,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeManagedIndexRangeReadiness& sourceValues,
    const NativeFixedFunctionRenderTargetBoundDrawReadiness& boundDraw,
    std::uint64_t snapshotToken) noexcept {

    if (snapshotToken == 0)
        return false;
    const auto current =
        compose_fixed_function_indexed_source_binding_readiness(
            sourceValueLineage, dispatch, indexedLineage, sourceRange,
            geometry, sourceValues, boundDraw);
    return current.ready && current.snapshotToken == snapshotToken;
}


NativeFixedFunctionIndexedSourceLiveBindingReadiness
compose_fixed_function_indexed_source_live_binding_readiness(
    const NativeFixedFunctionIndexedSourceBindingReadiness& sourceBinding,
    const NativeFixedFunctionIndexedSourceValueReadiness& sourceValueLineage,
    const NativeFixedFunctionDirectDrawDispatchReadiness& dispatch,
    const NativeFixedFunctionIndexedDirectDispatchReadiness& indexedLineage,
    const NativeFixedFunctionIndexedSourceRangeReadiness& sourceRange,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeManagedIndexRangeReadiness& sourceValues,
    const NativeFixedFunctionRenderTargetBoundDrawReadiness& boundDraw,
    ID3D11DeviceContext* context,
    const NativeManagedBufferShadow& indexBuffer) noexcept {

    NativeFixedFunctionIndexedSourceLiveBindingReadiness out{};
    out.sourceBindingSnapshotToken = sourceBinding.snapshotToken;
    out.indexMirrorSnapshotToken = sourceValues.mirrorSnapshotToken;
    out.inputValid =
        context != nullptr &&
        sourceBinding.ready &&
        sourceValues.ready;
    if (!out.inputValid)
        return out;

    out.sourceBindingReady =
        validate_fixed_function_indexed_source_binding_snapshot(
            sourceValueLineage, dispatch, indexedLineage, sourceRange,
            geometry, sourceValues, boundDraw, sourceBinding.snapshotToken);

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    out.contextMatchesMirror =
        contextDevice &&
        indexBuffer.mirror_device() == contextDevice.Get();

    if (out.contextMatchesMirror) {
        const auto currentMirror =
            indexBuffer.mirror_readiness(contextDevice.Get());
        out.indexMirrorCurrent =
            currentMirror.ready &&
            currentMirror.role == ResourceRole::Index &&
            currentMirror.snapshotToken == sourceValues.mirrorSnapshotToken;
    }

    Microsoft::WRL::ComPtr<ID3D11Buffer> observedIndexBuffer;
    context->IAGetIndexBuffer(
        observedIndexBuffer.ReleaseAndGetAddressOf(),
        &out.observedIndexFormat, &out.observedIndexOffset);
    out.liveIndexBufferExact =
        observedIndexBuffer.Get() == indexBuffer.mirror_buffer();
    out.liveIndexFormatExact =
        out.observedIndexFormat == sourceBinding.boundIndexFormat;
    out.liveIndexOffsetExact =
        out.observedIndexOffset == sourceBinding.boundIndexOffset;
    out.componentSnapshotsPresent =
        sourceBinding.snapshotToken != 0 &&
        sourceValues.mirrorSnapshotToken != 0;
    out.ready =
        out.sourceBindingReady &&
        out.contextMatchesMirror &&
        out.indexMirrorCurrent &&
        out.liveIndexBufferExact &&
        out.liveIndexFormatExact &&
        out.liveIndexOffsetExact &&
        out.componentSnapshotsPresent;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.sourceBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.indexMirrorSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(context)));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(
                    observedIndexBuffer.Get())));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.observedIndexFormat));
        token = mix_readiness_snapshot_token(token, out.observedIndexOffset);
        token = mix_readiness_snapshot_token(token, 0x1531u);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_indexed_source_live_binding_snapshot(
    const NativeFixedFunctionIndexedSourceBindingReadiness& sourceBinding,
    const NativeFixedFunctionIndexedSourceValueReadiness& sourceValueLineage,
    const NativeFixedFunctionDirectDrawDispatchReadiness& dispatch,
    const NativeFixedFunctionIndexedDirectDispatchReadiness& indexedLineage,
    const NativeFixedFunctionIndexedSourceRangeReadiness& sourceRange,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeManagedIndexRangeReadiness& sourceValues,
    const NativeFixedFunctionRenderTargetBoundDrawReadiness& boundDraw,
    ID3D11DeviceContext* context,
    const NativeManagedBufferShadow& indexBuffer,
    std::uint64_t snapshotToken) noexcept {

    if (snapshotToken == 0)
        return false;
    const auto current =
        compose_fixed_function_indexed_source_live_binding_readiness(
            sourceBinding, sourceValueLineage, dispatch, indexedLineage,
            sourceRange, geometry, sourceValues, boundDraw, context,
            indexBuffer);
    return current.ready && current.snapshotToken == snapshotToken;
}

bool validate_fixed_function_render_target_bound_draw_readiness_integrity(
    const NativeFixedFunctionRenderTargetBoundDrawReadiness& boundDraw) noexcept {
    if (!boundDraw.inputValid ||
        !boundDraw.fullyBoundDrawReady ||
        !boundDraw.surfaceTargetBindingReady ||
        !boundDraw.surfacePairMatchesDraw ||
        !boundDraw.geometryRangeMetadataExact ||
        !boundDraw.vertexStrideMatchesInputLayout ||
        !boundDraw.componentSnapshotsPresent ||
        !boundDraw.ready ||
        boundDraw.vertexStride == 0 ||
        boundDraw.inputLayoutStream0Stride == 0 ||
        boundDraw.vertexStride != boundDraw.inputLayoutStream0Stride ||
        boundDraw.vertexBufferByteWidth == 0 ||
        boundDraw.vertexOffset > boundDraw.vertexBufferByteWidth ||
        boundDraw.fullyBoundDrawSnapshotToken == 0 ||
        boundDraw.surfaceTargetBindingSnapshotToken == 0 ||
        boundDraw.surfacePairSnapshotToken == 0 ||
        boundDraw.snapshotToken == 0)
        return false;

    const UINT indexElementBytes =
        boundDraw.indexFormat == DXGI_FORMAT_R16_UINT ? 2u :
        boundDraw.indexFormat == DXGI_FORMAT_R32_UINT ? 4u : 0u;
    if (boundDraw.indexFormat == DXGI_FORMAT_UNKNOWN) {
        if (boundDraw.indexOffset != 0 || boundDraw.indexBufferByteWidth != 0)
            return false;
    } else if (indexElementBytes == 0 ||
               boundDraw.indexBufferByteWidth == 0 ||
               (boundDraw.indexOffset % indexElementBytes) != 0 ||
               boundDraw.indexOffset > boundDraw.indexBufferByteWidth) {
        return false;
    }

    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(token, boundDraw.fullyBoundDrawSnapshotToken);
    token = mix_readiness_snapshot_token(token, boundDraw.surfaceTargetBindingSnapshotToken);
    token = mix_readiness_snapshot_token(token, boundDraw.surfacePairSnapshotToken);
    token = mix_readiness_snapshot_token(token, boundDraw.vertexStride);
    // R158/R203: keep copied-readiness integrity hashing byte-for-byte
    // symmetric with compose_fixed_function_render_target_bound_draw_readiness.
    // Omitting the translated stream-0 stride makes a valid R145 snapshot
    // fail its own integrity check and incorrectly blocks R147 dispatch.
    token = mix_readiness_snapshot_token(
        token, boundDraw.inputLayoutStream0Stride);
    token = mix_readiness_snapshot_token(token, boundDraw.vertexOffset);
    token = mix_readiness_snapshot_token(token, boundDraw.vertexBufferByteWidth);
    token = mix_readiness_snapshot_token(
        token, static_cast<std::uint32_t>(boundDraw.indexFormat));
    token = mix_readiness_snapshot_token(token, boundDraw.indexOffset);
    token = mix_readiness_snapshot_token(token, boundDraw.indexBufferByteWidth);
    if (token == 0)
        token = 1;
    return token == boundDraw.snapshotToken;
}

NativeFixedFunctionDirectDrawDispatchReadiness
compose_fixed_function_direct_draw_dispatch_readiness(
    const NativeFixedFunctionRenderTargetBoundDrawReadiness& boundDraw,
    const NativeFixedFunctionDrawReadiness& draw,
    const NativeFixedFunctionGeometryReadiness& geometry,
    D3DPRIMITIVETYPE primitive,
    UINT primitiveCount,
    bool indexed,
    UINT startVertexLocation,
    UINT startIndexLocation,
    INT baseVertexLocation) noexcept {
    NativeFixedFunctionDirectDrawDispatchReadiness out{};
    out.indexed = indexed;
    out.primitiveCount = primitiveCount;
    out.startVertexLocation = startVertexLocation;
    out.startIndexLocation = startIndexLocation;
    out.baseVertexLocation = baseVertexLocation;
    out.renderTargetBoundDrawSnapshotToken = boundDraw.snapshotToken;
    out.drawSnapshotToken = draw.snapshotToken;
    out.geometrySnapshotToken = geometry.snapshotToken;

    const auto topology = translate_primitive(primitive);
    out.topology = topology.value;

    UINT elementCount = 0;
    const bool countExact =
        direct_draw_element_count(primitive, primitiveCount, elementCount);
    out.elementCount = countExact ? elementCount : 0u;

    const bool argumentsCanonical =
        indexed
            ? startVertexLocation == 0u
            : (startIndexLocation == 0u && baseVertexLocation == 0);
    const UINT maxValue = (std::numeric_limits<UINT>::max)();
    const bool rangeExact =
        countExact &&
        (indexed
            ? startIndexLocation <= maxValue - elementCount
            : startVertexLocation <= maxValue - elementCount);

    // R151 validates direct fetches against the byte capacity sealed by R145.
    // The widened arithmetic keeps this proof safe from UINT wraparound.
    out.bufferRangeExact = false;
    if (countExact && rangeExact && boundDraw.geometryRangeMetadataExact) {
        if (indexed) {
            const std::uint64_t indexElementBytes =
                boundDraw.indexFormat == DXGI_FORMAT_R16_UINT ? 2ull :
                boundDraw.indexFormat == DXGI_FORMAT_R32_UINT ? 4ull : 0ull;
            if (indexElementBytes != 0) {
                const std::uint64_t firstByte =
                    static_cast<std::uint64_t>(boundDraw.indexOffset) +
                    static_cast<std::uint64_t>(startIndexLocation) * indexElementBytes;
                const std::uint64_t endByte =
                    firstByte +
                    static_cast<std::uint64_t>(elementCount) * indexElementBytes;
                out.bufferRangeExact =
                    firstByte <= boundDraw.indexBufferByteWidth &&
                    endByte <= boundDraw.indexBufferByteWidth;
            }
        } else {
            const std::uint64_t firstByte =
                static_cast<std::uint64_t>(boundDraw.vertexOffset) +
                static_cast<std::uint64_t>(startVertexLocation) *
                    boundDraw.vertexStride;
            const std::uint64_t endByte =
                firstByte +
                static_cast<std::uint64_t>(elementCount) * boundDraw.vertexStride;
            out.bufferRangeExact =
                firstByte <= boundDraw.vertexBufferByteWidth &&
                endByte <= boundDraw.vertexBufferByteWidth;
        }
    }

    const bool drawIntegrity =
        validate_fixed_function_draw_readiness_integrity(draw);
    out.inputValid =
        drawIntegrity &&
        geometry.inputValid &&
        boundDraw.inputValid;
    out.renderTargetBoundDrawReady =
        validate_fixed_function_render_target_bound_draw_readiness_integrity(
            boundDraw);
    out.geometryReady =
        validate_fixed_function_direct_geometry_readiness_integrity(geometry);
    out.geometryMatchesDraw =
        draw.geometrySnapshotToken != 0 &&
        geometry.snapshotToken == draw.geometrySnapshotToken &&
        geometry.indexBufferRequired == indexed;
    out.surfacePairMatchesDraw =
        boundDraw.surfacePairSnapshotToken != 0 &&
        boundDraw.surfacePairSnapshotToken == draw.surfacePairSnapshotToken;
    out.topologyMatchesGeometry =
        topology.exact &&
        topology.value != D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED &&
        topology.value == geometry.topology;
    // R155 keeps direct POINTLIST fail-closed until D3D9 point-size and
    // point-sprite raster state is captured and translated. Topology alone
    // is not sufficient evidence of fixed-function raster equivalence.
    out.pointRasterSemanticsExact = primitive != D3DPT_POINTLIST;
    // R168 captures/translates ANTIALIASEDLINEENABLE, but D3D10+ removed
    // D3D9 LASTPIXEL control. Exact topology/arguments plus AA state still
    // cannot prove endpoint coverage, so direct line draws remain fail-closed
    // until LASTPIXEL is explicitly emulated.
    out.lineRasterSemanticsExact =
        primitive != D3DPT_LINELIST && primitive != D3DPT_LINESTRIP;
    out.dispatchArgumentsExact =
        argumentsCanonical && rangeExact && out.bufferRangeExact;
    out.componentSnapshotsPresent =
        boundDraw.snapshotToken != 0 &&
        draw.snapshotToken != 0 &&
        geometry.snapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.renderTargetBoundDrawReady &&
        draw.ready &&
        out.geometryReady &&
        out.geometryMatchesDraw &&
        out.surfacePairMatchesDraw &&
        out.topologyMatchesGeometry &&
        out.pointRasterSemanticsExact &&
        out.lineRasterSemanticsExact &&
        out.dispatchArgumentsExact &&
        out.componentSnapshotsPresent;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.renderTargetBoundDrawSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.drawSnapshotToken);
        token = mix_readiness_snapshot_token(token, out.geometrySnapshotToken);
        token = mix_readiness_snapshot_token(token, indexed ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(primitive));
        token = mix_readiness_snapshot_token(token, primitiveCount);
        token = mix_readiness_snapshot_token(token, elementCount);
        token = mix_readiness_snapshot_token(token, startVertexLocation);
        token = mix_readiness_snapshot_token(token, startIndexLocation);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(baseVertexLocation));
        token = mix_readiness_snapshot_token(
            token, out.bufferRangeExact ? 0x151u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.pointRasterSemanticsExact ? 0x155u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.lineRasterSemanticsExact ? 0x157u : 0u);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_direct_draw_dispatch_snapshot(
    const NativeFixedFunctionRenderTargetBoundDrawReadiness& boundDraw,
    const NativeFixedFunctionDrawReadiness& draw,
    const NativeFixedFunctionGeometryReadiness& geometry,
    D3DPRIMITIVETYPE primitive,
    UINT primitiveCount,
    bool indexed,
    UINT startVertexLocation,
    UINT startIndexLocation,
    INT baseVertexLocation,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = compose_fixed_function_direct_draw_dispatch_readiness(
        boundDraw, draw, geometry, primitive, primitiveCount, indexed,
        startVertexLocation, startIndexLocation, baseVertexLocation);
    return current.ready && current.snapshotToken == snapshotToken;
}

// R156: offscreen WARP-only native Draw preflight; no gameplay draw dispatch.
// The actual D3D11 Draw resides exclusively in tools/dx11_constant_buffer_probe.cpp.
// This rechecks current device/context and live OM/IA/VS/PS attachments.
bool prepare_fixed_function_nonindexed_direct_draw_probe(
    ID3D11DeviceContext* context,
    ID3D11RenderTargetView* expectedProbeTarget,
    const NativeFixedFunctionRenderTargetBoundDrawReadiness& boundDraw,
    const NativeFixedFunctionDrawReadiness& draw,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeFixedFunctionDirectDrawDispatchReadiness& dispatch,
    D3DPRIMITIVETYPE primitive,
    UINT primitiveCount,
    UINT startVertexLocation) noexcept {
    if (!context || !expectedProbeTarget ||
        context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE ||
        dispatch.indexed || !dispatch.ready || dispatch.snapshotToken == 0 ||
        dispatch.elementCount == 0 ||
        !validate_fixed_function_direct_draw_dispatch_snapshot(
            boundDraw, draw, geometry, primitive, primitiveCount, false,
            startVertexLocation, 0u, 0, dispatch.snapshotToken))
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    Microsoft::WRL::ComPtr<ID3D11Device> targetDevice;
    context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    expectedProbeTarget->GetDevice(targetDevice.ReleaseAndGetAddressOf());
    if (!contextDevice || contextDevice.Get() != targetDevice.Get())
        return false;

    Microsoft::WRL::ComPtr<ID3D11RenderTargetView> liveTarget;
    context->OMGetRenderTargets(1, liveTarget.ReleaseAndGetAddressOf(), nullptr);
    if (liveTarget.Get() != expectedProbeTarget)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Buffer> liveVertexBuffer;
    UINT liveStride = 0;
    UINT liveOffset = 0;
    context->IAGetVertexBuffers(
        0, 1, liveVertexBuffer.ReleaseAndGetAddressOf(),
        &liveStride, &liveOffset);
    D3D11_PRIMITIVE_TOPOLOGY liveTopology =
        D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    context->IAGetPrimitiveTopology(&liveTopology);
    Microsoft::WRL::ComPtr<ID3D11VertexShader> liveVS;
    Microsoft::WRL::ComPtr<ID3D11PixelShader> livePS;
    context->VSGetShader(liveVS.ReleaseAndGetAddressOf(), nullptr, nullptr);
    context->PSGetShader(livePS.ReleaseAndGetAddressOf(), nullptr, nullptr);
    if (!liveVertexBuffer || !liveVS || !livePS ||
        liveStride != boundDraw.vertexStride ||
        liveOffset != boundDraw.vertexOffset ||
        liveTopology != dispatch.topology)
        return false;

    // No native Draw* dispatch in production: preserve the activation boundary.
    return true;
}

NativeFixedFunctionFanDrawDispatchReadiness
compose_fixed_function_nonindexed_triangle_fan_draw_dispatch_readiness(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    const NativeFixedFunctionPipelineBundle& pipelineBundle,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride, UINT vertexOffset,
    const NativeTriangleFanIndexBuffer& generatedIndexBuffer,
    UINT primitiveCount, UINT baseVertex,
    const FixedFunctionTransformConstants& transform,
    const NativeSurfacePairBinding& surfaceBinding,
    const NativeSurfaceMirror& colorSurface,
    const NativeSurfaceMirror& depthSurface) noexcept {
    NativeFixedFunctionFanDrawDispatchReadiness out{};
    const auto finalBound =
        compose_fixed_function_final_nonindexed_triangle_fan_bound_draw_readiness(
            draw, context, outputStateBinding, pipelineBundle,
            layout, vertexPrototype, pixelPrototype, samplers, textures,
            vertexBuffer, vertexStride, vertexOffset, generatedIndexBuffer,
            primitiveCount, baseVertex, transform, surfaceBinding,
            colorSurface, depthSurface);

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    if (context)
        context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    const auto generated = generatedIndexBuffer.readiness(contextDevice.Get());

    out.primitiveCount = primitiveCount;
    out.indexCount = generated.indexCount;
    out.startIndexLocation = 0u;
    out.baseVertexLocation = 0;
    out.finalFanBoundDrawSnapshotToken = finalBound.snapshotToken;
    out.generatedIndexSnapshotToken = generated.snapshotToken;
    out.inputValid =
        context != nullptr && contextDevice.Get() != nullptr &&
        finalBound.inputValid && generated.deviceMatches;
    out.finalFanBoundDrawReady =
        finalBound.ready && finalBound.snapshotToken != 0;
    out.generatedIndexReady =
        generated.ready && generated.snapshotToken != 0;

    const UINT maxValue = (std::numeric_limits<UINT>::max)();
    const bool countExact =
        primitiveCount <= maxValue / 3u &&
        generated.indexCount == primitiveCount * 3u;
    out.generatedIndexMatchesDispatch =
        generated.ready &&
        !generated.indexedSource &&
        generated.primitiveCount == primitiveCount &&
        generated.baseVertex == baseVertex &&
        generated.sourceIndexSnapshotToken == 0 &&
        countExact;

    // R154: a generated nonindexed fan encodes source vertices
    // [baseVertex, baseVertex + primitiveCount + 1] directly into its immutable
    // R32 index stream. Seal that deterministic span against the same managed
    // VB owner/stride/offset used by the final live IA proof before allowing
    // the eventual DrawIndexed tuple to become ready.
    out.vertexBufferRangeExact = false;
    const auto expansion = translate_triangle_fan_expansion(primitiveCount);
    if (out.generatedIndexMatchesDispatch &&
        expansion.exact &&
        expansion.sourceElementCount != 0u &&
        vertexStride != 0u &&
        vertexBuffer.byte_width() != 0u &&
        vertexOffset <= vertexBuffer.byte_width()) {
        const std::uint64_t maxVertex =
            static_cast<std::uint64_t>(baseVertex) +
            static_cast<std::uint64_t>(expansion.sourceElementCount - 1u);
        const std::uint64_t endByte =
            static_cast<std::uint64_t>(vertexOffset) +
            (maxVertex + 1ull) * static_cast<std::uint64_t>(vertexStride);
        out.vertexBufferRangeExact =
            maxVertex <= (std::numeric_limits<UINT>::max)() &&
            endByte <= static_cast<std::uint64_t>(vertexBuffer.byte_width());
    }

    out.dispatchArgumentsExact =
        out.generatedIndexMatchesDispatch &&
        out.vertexBufferRangeExact &&
        out.startIndexLocation == 0u &&
        out.baseVertexLocation == 0;
    out.componentSnapshotsPresent =
        finalBound.snapshotToken != 0 && generated.snapshotToken != 0;
    out.ready =
        out.inputValid && out.finalFanBoundDrawReady &&
        out.generatedIndexReady && out.generatedIndexMatchesDispatch &&
        out.dispatchArgumentsExact && out.componentSnapshotsPresent;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.finalFanBoundDrawSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.generatedIndexSnapshotToken);
        token = mix_readiness_snapshot_token(token, primitiveCount);
        token = mix_readiness_snapshot_token(token, baseVertex);
        token = mix_readiness_snapshot_token(token, out.indexCount);
        token = mix_readiness_snapshot_token(token, out.startIndexLocation);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.baseVertexLocation));
        token = mix_readiness_snapshot_token(
            token, out.vertexBufferRangeExact ? 0x154u : 0u);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool
validate_fixed_function_nonindexed_triangle_fan_draw_dispatch_snapshot(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    const NativeFixedFunctionPipelineBundle& pipelineBundle,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride, UINT vertexOffset,
    const NativeTriangleFanIndexBuffer& generatedIndexBuffer,
    UINT primitiveCount, UINT baseVertex,
    const FixedFunctionTransformConstants& transform,
    const NativeSurfacePairBinding& surfaceBinding,
    const NativeSurfaceMirror& colorSurface,
    const NativeSurfaceMirror& depthSurface,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current =
        compose_fixed_function_nonindexed_triangle_fan_draw_dispatch_readiness(
            draw, context, outputStateBinding, pipelineBundle,
            layout, vertexPrototype, pixelPrototype, samplers, textures,
            vertexBuffer, vertexStride, vertexOffset, generatedIndexBuffer,
            primitiveCount, baseVertex, transform, surfaceBinding,
            colorSurface, depthSurface);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionIndexedFanSourceContentReadiness
compose_fixed_function_indexed_fan_source_content_readiness(
    const NativeManagedBufferShadow& sourceIndexBuffer,
    const NativeTriangleFanIndexBuffer& generatedIndexBuffer,
    ID3D11Device* expectedDevice) noexcept {

    NativeFixedFunctionIndexedFanSourceContentReadiness out{};
    const auto generated = generatedIndexBuffer.readiness(expectedDevice);
    const auto source = sourceIndexBuffer.mirror_readiness(expectedDevice);
    out.generatedIndexSnapshotToken = generated.snapshotToken;
    out.sourceIndexSnapshotToken = source.snapshotToken;
    out.generatedContentHash = generated.contentHash;

    out.inputValid =
        expectedDevice != nullptr &&
        generated.ready &&
        generated.indexedSource &&
        source.ready &&
        source.role == ResourceRole::Index;
    out.generatedIndexReady =
        generated.ready && generated.snapshotToken != 0;
    out.sourceIndexReady =
        source.ready && source.snapshotToken != 0;
    out.sourceProvenanceMatches =
        out.inputValid &&
        generated.sourceIndexSnapshotToken == source.snapshotToken &&
        generated.sourceIndexFormat != D3DFMT_UNKNOWN;

    std::uint64_t expectedExpandedContentHash = 0;
    const bool contentHashReady =
        out.sourceProvenanceMatches &&
        sourceIndexBuffer.hash_indexed_triangle_fan_window(
            generated.sourceIndexFormat,
            generated.sourceStartIndex,
            generated.sourceIndexCount,
            generated.primitiveCount,
            source.shadowVersion,
            expectedExpandedContentHash);
    out.expectedExpandedContentHash = expectedExpandedContentHash;
    out.expandedContentExact =
        contentHashReady &&
        expectedExpandedContentHash != 0 &&
        generated.contentHash == expectedExpandedContentHash;
    out.componentSnapshotsPresent =
        generated.snapshotToken != 0 &&
        source.snapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.generatedIndexReady &&
        out.sourceIndexReady &&
        out.sourceProvenanceMatches &&
        out.expandedContentExact &&
        out.componentSnapshotsPresent;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.generatedIndexSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.sourceIndexSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.expectedExpandedContentHash);
        token = mix_readiness_snapshot_token(
            token, out.generatedContentHash);
        token = mix_readiness_snapshot_token(token, 0x155u);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_indexed_fan_source_content_snapshot(
    const NativeManagedBufferShadow& sourceIndexBuffer,
    const NativeTriangleFanIndexBuffer& generatedIndexBuffer,
    ID3D11Device* expectedDevice,
    std::uint64_t snapshotToken) noexcept {

    if (snapshotToken == 0)
        return false;
    const auto current =
        compose_fixed_function_indexed_fan_source_content_readiness(
            sourceIndexBuffer, generatedIndexBuffer, expectedDevice);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionFanDrawDispatchReadiness
compose_fixed_function_indexed_triangle_fan_draw_dispatch_readiness(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    const NativeFixedFunctionPipelineBundle& pipelineBundle,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride, UINT vertexOffset,
    const NativeManagedBufferShadow& sourceIndexBuffer,
    const NativeTriangleFanIndexBuffer& generatedIndexBuffer,
    UINT primitiveCount, D3DFORMAT sourceIndexFormat,
    UINT startIndex, UINT sourceIndexCount, INT baseVertexLocation,
    UINT minVertexIndex, UINT numVertices,
    const FixedFunctionTransformConstants& transform,
    const NativeSurfacePairBinding& surfaceBinding,
    const NativeSurfaceMirror& colorSurface,
    const NativeSurfaceMirror& depthSurface) noexcept {
    NativeFixedFunctionFanDrawDispatchReadiness out{};
    out.indexedSource = true;
    const auto finalBound =
        compose_fixed_function_final_indexed_triangle_fan_bound_draw_readiness(
            draw, context, outputStateBinding, pipelineBundle,
            layout, vertexPrototype, pixelPrototype, samplers, textures,
            vertexBuffer, vertexStride, vertexOffset, sourceIndexBuffer,
            generatedIndexBuffer, primitiveCount, sourceIndexFormat,
            startIndex, sourceIndexCount, baseVertexLocation, transform,
            surfaceBinding, colorSurface, depthSurface);

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    if (context)
        context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    const auto generated = generatedIndexBuffer.readiness(contextDevice.Get());
    const auto currentSource =
        sourceIndexBuffer.mirror_readiness(contextDevice.Get());
    const auto sourceContent =
        compose_fixed_function_indexed_fan_source_content_readiness(
            sourceIndexBuffer, generatedIndexBuffer, contextDevice.Get());

    out.primitiveCount = primitiveCount;
    out.indexCount = generated.indexCount;
    out.startIndexLocation = 0u;
    out.baseVertexLocation = baseVertexLocation;
    out.sourceMinVertexIndex = minVertexIndex;
    out.sourceNumVertices = numVertices;
    out.finalFanBoundDrawSnapshotToken = finalBound.snapshotToken;
    out.generatedIndexSnapshotToken = generated.snapshotToken;
    out.sourceIndexSnapshotToken = currentSource.snapshotToken;
    out.sourceContentSnapshotToken = sourceContent.snapshotToken;
    out.inputValid =
        context != nullptr && contextDevice.Get() != nullptr &&
        finalBound.inputValid && generated.deviceMatches &&
        currentSource.inputValid && sourceContent.inputValid;
    out.finalFanBoundDrawReady =
        finalBound.ready && finalBound.snapshotToken != 0;
    out.generatedIndexReady =
        generated.ready && generated.snapshotToken != 0 &&
        currentSource.ready && currentSource.snapshotToken != 0 &&
        sourceContent.ready && sourceContent.snapshotToken != 0;

    const UINT maxValue = (std::numeric_limits<UINT>::max)();
    const bool countExact =
        primitiveCount <= maxValue / 3u &&
        generated.indexCount == primitiveCount * 3u;

    // DX11-FAN-DECLARED-RANGE: preserve D3D9 indexed-fan declared vertex range. D3D11
    // DrawIndexed has no MinVertexIndex/NumVertices arguments, so the dormant
    // readiness chain must retain them and prove the exact source index values
    // stay within that caller-declared interval before activation.
    const bool sourceVertexCountCompatible =
        primitiveCount == 0u || numVertices != 0u;
    bool sourceDeclaredRangeFits = primitiveCount == 0u;
    if (numVertices != 0u) {
        const UINT spanMinusOne = numVertices - 1u;
        sourceDeclaredRangeFits =
            minVertexIndex <= maxValue - spanMinusOne;
        if (sourceDeclaredRangeFits)
            out.sourceMaxVertexIndex = minVertexIndex + spanMinusOne;
    }
    out.sourceDeclaredVertexRangeExact =
        sourceVertexCountCompatible && sourceDeclaredRangeFits;

    out.generatedIndexMatchesDispatch =
        generated.ready && generated.indexedSource &&
        generated.baseVertex == 0u &&
        generated.primitiveCount == primitiveCount &&
        generated.sourceIndexFormat == sourceIndexFormat &&
        generated.sourceStartIndex == startIndex &&
        generated.sourceIndexCount == sourceIndexCount &&
        generated.sourceIndexSnapshotToken != 0 &&
        generated.sourceIndexSnapshotToken == currentSource.snapshotToken &&
        sourceContent.generatedIndexSnapshotToken == generated.snapshotToken &&
        sourceContent.sourceIndexSnapshotToken == currentSource.snapshotToken &&
        sourceContent.expandedContentExact &&
        countExact;
    // R156: indexed fan capacity follows the exact source indices that R155
    // proved were used to materialize the generated immutable fan stream.
    // D3D11 applies BaseVertexLocation after fetching those generated indices,
    // so both the signed effective vertex interval and the resulting VB byte
    // interval must remain representable and inside the same live IA owner.
    out.vertexBufferRangeExact = false;
    const auto expansion = translate_triangle_fan_expansion(primitiveCount);
    NativeManagedIndexRangeReadiness sourceVertexWindow{};
    if (currentSource.ready && expansion.exact &&
        expansion.sourceElementCount != 0u &&
        out.sourceDeclaredVertexRangeExact) {
        sourceVertexWindow = sourceIndexBuffer.index_range_readiness(
            currentSource, sourceIndexFormat, startIndex,
            expansion.sourceElementCount, out.sourceMinVertexIndex,
            out.sourceMaxVertexIndex);
    }
    out.sourceObservedMinIndex = sourceVertexWindow.observedMinIndex;
    out.sourceObservedMaxIndex = sourceVertexWindow.observedMaxIndex;
    out.sourceValuesWithinDeclaredRange =
        sourceVertexWindow.ready &&
        sourceVertexWindow.valuesWithinDeclaredRange;
    out.sourceValueSnapshotToken = sourceVertexWindow.snapshotToken;
    if (out.generatedIndexMatchesDispatch &&
        sourceVertexWindow.ready &&
        sourceVertexWindow.snapshotToken != 0 &&
        sourceVertexWindow.mirrorSnapshotToken == currentSource.snapshotToken &&
        vertexStride != 0u &&
        vertexBuffer.byte_width() != 0u &&
        vertexOffset <= vertexBuffer.byte_width()) {
        const std::int64_t effectiveMinVertex =
            static_cast<std::int64_t>(baseVertexLocation) +
            static_cast<std::int64_t>(sourceVertexWindow.observedMinIndex);
        const std::int64_t effectiveMaxVertex =
            static_cast<std::int64_t>(baseVertexLocation) +
            static_cast<std::int64_t>(sourceVertexWindow.observedMaxIndex);
        if (effectiveMinVertex >= 0 &&
            effectiveMaxVertex >= effectiveMinVertex &&
            effectiveMaxVertex <= static_cast<std::int64_t>(maxValue)) {
            const std::uint64_t endByte =
                static_cast<std::uint64_t>(vertexOffset) +
                (static_cast<std::uint64_t>(effectiveMaxVertex) + 1ull) *
                    static_cast<std::uint64_t>(vertexStride);
            out.vertexBufferRangeExact =
                endByte <= static_cast<std::uint64_t>(vertexBuffer.byte_width());
        }
    }
    // R160: MinVertexIndex/NumVertices describe the complete D3D9 source
    // vertex window, not only the indices observed in this draw. Preserve the
    // existing R156 observed-fetch proof, but also require the full declared
    // window after BaseVertexLocation to fit the exact managed VB capacity.
    out.sourceDeclaredVertexBufferRangeExact = false;
    if (out.sourceDeclaredVertexRangeExact &&
        out.sourceValuesWithinDeclaredRange &&
        vertexStride != 0u &&
        vertexBuffer.byte_width() != 0u &&
        vertexOffset <= vertexBuffer.byte_width()) {
        const std::int64_t effectiveDeclaredMinVertex =
            static_cast<std::int64_t>(baseVertexLocation) +
            static_cast<std::int64_t>(out.sourceMinVertexIndex);
        const std::int64_t effectiveDeclaredMaxVertex =
            static_cast<std::int64_t>(baseVertexLocation) +
            static_cast<std::int64_t>(out.sourceMaxVertexIndex);
        if (effectiveDeclaredMinVertex >= 0 &&
            effectiveDeclaredMaxVertex >= effectiveDeclaredMinVertex &&
            effectiveDeclaredMaxVertex <= static_cast<std::int64_t>(maxValue)) {
            const std::uint64_t declaredEndByte =
                static_cast<std::uint64_t>(vertexOffset) +
                (static_cast<std::uint64_t>(effectiveDeclaredMaxVertex) + 1ull) *
                    static_cast<std::uint64_t>(vertexStride);
            out.sourceDeclaredVertexBufferRangeExact =
                declaredEndByte <=
                static_cast<std::uint64_t>(vertexBuffer.byte_width());
        }
    }

    out.dispatchArgumentsExact =
        out.generatedIndexMatchesDispatch &&
        out.sourceDeclaredVertexRangeExact &&
        out.sourceValuesWithinDeclaredRange &&
        out.vertexBufferRangeExact &&
        out.sourceDeclaredVertexBufferRangeExact &&
        out.startIndexLocation == 0u;
    out.componentSnapshotsPresent =
        finalBound.snapshotToken != 0 &&
        generated.snapshotToken != 0 &&
        currentSource.snapshotToken != 0 &&
        sourceContent.snapshotToken != 0 &&
        sourceVertexWindow.snapshotToken != 0;
    out.ready =
        out.inputValid && out.finalFanBoundDrawReady &&
        out.generatedIndexReady && out.generatedIndexMatchesDispatch &&
        out.dispatchArgumentsExact && out.componentSnapshotsPresent;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.finalFanBoundDrawSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.generatedIndexSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.sourceIndexSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.sourceContentSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.sourceValueSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.sourceObservedMinIndex);
        token = mix_readiness_snapshot_token(
            token, out.sourceObservedMaxIndex);
        token = mix_readiness_snapshot_token(
            token, out.sourceMinVertexIndex);
        token = mix_readiness_snapshot_token(
            token, out.sourceNumVertices);
        token = mix_readiness_snapshot_token(
            token, out.sourceMaxVertexIndex);
        token = mix_readiness_snapshot_token(
            token, out.sourceDeclaredVertexRangeExact ? 0x46414e52u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.sourceValuesWithinDeclaredRange ? 0x46414e53u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.sourceDeclaredVertexBufferRangeExact ? 0x160u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.vertexBufferRangeExact ? 0x156u : 0u);
        token = mix_readiness_snapshot_token(token, primitiveCount);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(sourceIndexFormat));
        token = mix_readiness_snapshot_token(token, startIndex);
        token = mix_readiness_snapshot_token(token, sourceIndexCount);
        token = mix_readiness_snapshot_token(token, out.indexCount);
        token = mix_readiness_snapshot_token(token, out.startIndexLocation);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(baseVertexLocation));
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool
validate_fixed_function_indexed_triangle_fan_draw_dispatch_snapshot(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    const NativeFixedFunctionPipelineBundle& pipelineBundle,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride, UINT vertexOffset,
    const NativeManagedBufferShadow& sourceIndexBuffer,
    const NativeTriangleFanIndexBuffer& generatedIndexBuffer,
    UINT primitiveCount, D3DFORMAT sourceIndexFormat,
    UINT startIndex, UINT sourceIndexCount, INT baseVertexLocation,
    UINT minVertexIndex, UINT numVertices,
    const FixedFunctionTransformConstants& transform,
    const NativeSurfacePairBinding& surfaceBinding,
    const NativeSurfaceMirror& colorSurface,
    const NativeSurfaceMirror& depthSurface,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current =
        compose_fixed_function_indexed_triangle_fan_draw_dispatch_readiness(
            draw, context, outputStateBinding, pipelineBundle,
            layout, vertexPrototype, pixelPrototype, samplers, textures,
            vertexBuffer, vertexStride, vertexOffset, sourceIndexBuffer,
            generatedIndexBuffer, primitiveCount, sourceIndexFormat,
            startIndex, sourceIndexCount, baseVertexLocation,
            minVertexIndex, numVertices, transform,
            surfaceBinding, colorSurface, depthSurface);
    return current.ready && current.snapshotToken == snapshotToken;
}


void NativeFixedFunctionPipelineBundle::shutdown() noexcept {
    transform_buffer_.shutdown();
    input_layout_.Reset();
    pixel_shader_.Reset();
    vertex_shader_.Reset();
    device_.Reset();
    input_layout_identity_ = 0;
    vertex_shader_source_hash_ = 0;
    pixel_shader_source_hash_ = 0;
}

bool NativeBackend::initialize(const NativeBackendConfig& config) noexcept {
    shutdown();
    if (config.width == 0 || config.height == 0) return false;

    if (config.require_adapter_luid && !config.adapter_luid_valid)
        return false;

    Microsoft::WRL::ComPtr<IDXGIAdapter1> requestedAdapter;
    if (config.adapter_luid_valid &&
        !find_adapter(config.adapter_luid, requestedAdapter) &&
        config.require_adapter_luid)
        return false;

    UINT flags = D3D11_CREATE_DEVICE_BGRA_SUPPORT;
    if (config.request_debug_layer) flags |= D3D11_CREATE_DEVICE_DEBUG;

    HRESULT hr = create_device(
        requestedAdapter.Get(), flags, device_, context_, feature_level_);
    if (FAILED(hr) && (flags & D3D11_CREATE_DEVICE_DEBUG) != 0) {
        device_.Reset();
        context_.Reset();
        flags &= ~D3D11_CREATE_DEVICE_DEBUG;
        hr = create_device(
            requestedAdapter.Get(), flags, device_, context_, feature_level_);
    }
    if (FAILED(hr)) {
        shutdown();
        return false;
    }

    selected_adapter_luid_valid_ =
        read_device_luid(device_.Get(), selected_adapter_luid_);
    if (config.adapter_luid_valid &&
        config.require_adapter_luid &&
        (!selected_adapter_luid_valid_ ||
         !same_luid(selected_adapter_luid_, config.adapter_luid))) {
        shutdown();
        return false;
    }

    config_ = config;
    if (!programmable_shader_ownership_.initialize(device_.Get())) {
        shutdown();
        return false;
    }
    if (!create_color_target(config.width, config.height, config.color_format)) {
        shutdown();
        return false;
    }
    return true;
}


NativeProgrammableShaderProductionObservationEvidence
NativeBackend::observe_programmable_shader_source_evidence_chain(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderTranslationObjectPrerequisiteEvidence&
        objectPrerequisite,
    std::uint64_t objectPrerequisiteSnapshotToken,
    const NativeProgrammableShaderObjectCreationHandoffEvidence& creationHandoff,
    std::uint64_t creationHandoffSnapshotToken,
    const NativeProgrammableShaderTargetBytecodeMaterializationEvidence&
        targetBytecodeMaterialization,
    std::uint64_t targetBytecodeMaterializationSnapshotToken,
    const NativeProgrammableShaderSourceMappingHandoff& sourceMappingHandoff,
    std::uint64_t sourceMappingHandoffSnapshotToken,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence&
        translationPlan,
    std::uint64_t translationPlanSnapshotToken) noexcept {
    if (!ready())
        return {};
    return observe_programmable_shader_production_source_evidence_chain(
        programmable_shader_ownership(),
        device_.Get(),
        sourceIdentity,
        objectPrerequisite,
        objectPrerequisiteSnapshotToken,
        creationHandoff,
        creationHandoffSnapshotToken,
        targetBytecodeMaterialization,
        targetBytecodeMaterializationSnapshotToken,
        sourceMappingHandoff,
        sourceMappingHandoffSnapshotToken,
        translationPlan,
        translationPlanSnapshotToken);
}

bool NativeBackend::resize(std::uint32_t width, std::uint32_t height) noexcept {
    if (!device_ || width == 0 || height == 0) return false;

    color_srv_.Reset();
    color_rtv_.Reset();
    color_texture_.Reset();

    if (!create_color_target(width, height, config_.color_format)) return false;
    config_.width = width;
    config_.height = height;
    return true;
}

void NativeBackend::begin_frame(const std::array<float, 4>& clear_color) noexcept {
    if (!ready()) return;

    ID3D11RenderTargetView* rtv = color_rtv_.Get();
    context_->OMSetRenderTargets(1, &rtv, nullptr);

    D3D11_VIEWPORT viewport{};
    viewport.Width = static_cast<float>(config_.width);
    viewport.Height = static_cast<float>(config_.height);
    viewport.MinDepth = 0.0f;
    viewport.MaxDepth = 1.0f;
    context_->RSSetViewports(1, &viewport);
    context_->ClearRenderTargetView(color_rtv_.Get(), clear_color.data());
}

void NativeBackend::shutdown() noexcept {
    programmable_shader_ownership_.shutdown();
    color_srv_.Reset();
    color_rtv_.Reset();
    color_texture_.Reset();
    context_.Reset();
    device_.Reset();
    config_ = {};
    feature_level_ = D3D_FEATURE_LEVEL_9_1;
    selected_adapter_luid_ = {};
    selected_adapter_luid_valid_ = false;
}

bool NativeBackend::create_color_target(
    std::uint32_t width, std::uint32_t height, DXGI_FORMAT format) noexcept {
    if (!device_ || width == 0 || height == 0) return false;

    D3D11_TEXTURE2D_DESC desc{};
    desc.Width = width;
    desc.Height = height;
    desc.MipLevels = 1;
    desc.ArraySize = 1;
    desc.Format = format;
    desc.SampleDesc.Count = 1;
    desc.Usage = D3D11_USAGE_DEFAULT;
    desc.BindFlags = D3D11_BIND_RENDER_TARGET | D3D11_BIND_SHADER_RESOURCE;

    if (FAILED(device_->CreateTexture2D(&desc, nullptr, color_texture_.ReleaseAndGetAddressOf())))
        return false;
    if (FAILED(device_->CreateRenderTargetView(color_texture_.Get(), nullptr, color_rtv_.ReleaseAndGetAddressOf()))) {
        color_texture_.Reset();
        return false;
    }
    if (FAILED(device_->CreateShaderResourceView(color_texture_.Get(), nullptr, color_srv_.ReleaseAndGetAddressOf()))) {
        color_rtv_.Reset();
        color_texture_.Reset();
        return false;
    }
    return true;
}

} // namespace outrun::vr::dx11