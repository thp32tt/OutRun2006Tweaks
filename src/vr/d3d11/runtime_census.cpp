#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "runtime_census.hpp"
#include "fixed_function_pipeline.hpp"
#include "native_backend.hpp"
#include "resource_translation.hpp"

#include <array>
#include <atomic>
#include <cstdint>
#include <cstring>
#include <mutex>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include <spdlog/spdlog.h>

#include "pipeline_translation.hpp"
#include "state_translation.hpp"
#include "vr/core/d3d9_draw_state.hpp"

namespace outrun::vr::dx11
{
    namespace
    {
        constexpr std::uint32_t SampleStride = 64u;
        constexpr std::size_t SignatureHashCap = 512u;
        constexpr std::size_t DetailedSignatureLogCap = 64u;
        constexpr std::size_t UnsupportedBitCount = 12;
        static_assert(
            SampleStride != 0u && (SampleStride & (SampleStride - 1u)) == 0u,
            "DX11 census sample stride must remain a power of two");

        std::atomic<int> EnabledCache{-1};
        std::atomic<int> ExhaustiveCache{-1};
        std::atomic<std::uint64_t> DrawCallsSeen{0};
        std::atomic<std::uint64_t> Samples{0};
        std::atomic<std::uint64_t> ExactSamples{0};
        std::atomic<std::uint64_t> FixedFunctionSamples{0};
        std::atomic<std::uint64_t> ProgrammableSamples{0};
        std::atomic<std::uint64_t> UnsupportedTopologySamples{0};
        std::atomic<std::uint64_t> UnsupportedIndexFormatSamples{0};
        std::atomic<std::uint64_t> UnsupportedTextureFormatSamples{0};
        std::atomic<std::uint64_t> UnsupportedColorFormatSamples{0};
        std::atomic<std::uint64_t> UnsupportedDepthFormatSamples{0};
        std::atomic<std::uint64_t> ResourceIntrospectionFailureSamples{0};
        std::atomic<std::uint64_t> ResourceBehaviorUnsupportedSamples{0};
        std::atomic<std::uint64_t> ResourceMutationTelemetryRequiredSamples{0};
        std::atomic<std::uint64_t> ResourceMutationWriteUnlocks{0};
        std::atomic<std::uint64_t> ResourceMutationReadOnlyUnlocks{0};
        std::atomic<std::uint64_t> ResourceMutationDiscardWriteUnlocks{0};
        std::atomic<std::uint64_t> ResourceMutationNoOverwriteWriteUnlocks{0};
        std::atomic<std::uint64_t> ResourceMutationPlanExactUnlocks{0};
        std::atomic<std::uint64_t> ResourceMutationPlanUnsupportedUnlocks{0};
        std::atomic<std::uint64_t> ResourceMutationManagedShadowUnlocks{0};
        std::atomic<std::uint64_t> ResourceMutationMapWriteUnlocks{0};
        std::atomic<std::uint64_t> ResourceMutationMapDiscardUnlocks{0};
        std::atomic<std::uint64_t> ResourceMutationMapNoOverwriteUnlocks{0};
        std::atomic<std::uint64_t> ResourceMutationUpdateSubresourceUnlocks{0};
        std::atomic<std::uint64_t> ResourceTextureMutationWriteUnlocks{0};
        std::atomic<std::uint64_t> ResourceTextureMutationReadOnlyUnlocks{0};
        std::atomic<std::uint64_t> ResourceTextureMutationDescriptorFailures{0};
        std::atomic<std::uint64_t> ResourceUpdateTextureSuccesses{0};
        std::atomic<std::uint64_t> ResourceUpdateTextureFailures{0};
        std::atomic<std::uint64_t> ResourceUpdateSurfaceSuccesses{0};
        std::atomic<std::uint64_t> ResourceUpdateSurfaceFailures{0};
        std::atomic<std::uint64_t> ManagedTextureUpdateTextureInvalidations{0};
        std::atomic<std::uint64_t> ManagedTextureUpdateSurfaceInvalidations{0};
        std::atomic<std::uint64_t> ResourceManagedShadowWrites{0};
        std::atomic<std::uint64_t> ResourceManagedShadowReads{0};
        std::atomic<std::uint64_t> ResourceManagedResetSuccesses{0};
        std::atomic<std::uint64_t> ResourceManagedResetShadowPreserved{0};
        std::atomic<std::uint64_t> ResourceManagedShadowRequiredSamples{0};
        std::atomic<std::uint64_t> ManagedTextureShadowRequiredSamples{0};
        std::atomic<std::uint64_t> ManagedTextureShadowReadySamples{0};
        std::atomic<std::uint64_t> ManagedTextureShadowPendingSamples{0};
        std::atomic<std::uint64_t> TextureStageManagedShadowRequiredResources{0};
        std::atomic<std::uint64_t> TextureStageManagedShadowReadyResources{0};
        std::atomic<std::uint64_t> TextureStageManagedShadowPendingResources{0};
        std::atomic<std::uint64_t> UniqueDrawSignatures{0};
        std::atomic<std::uint64_t> SignatureHashCapHitSamples{0};
        std::atomic<std::uint64_t> DetailedSignatureLogSkippedSignatures{0};
        std::atomic<std::uint64_t> VertexDeclarationSamples{0};
        std::atomic<std::uint64_t> InputLayoutExactSamples{0};
        std::atomic<std::uint64_t> InputLayoutUnsupportedSamples{0};
        std::atomic<std::uint64_t> InputLayoutFvfExactSamples{0};
        std::atomic<std::uint64_t> InputLayoutFvfPendingSamples{0};
        std::atomic<std::uint64_t> ShaderIntrospectionFailureSamples{0};
        std::atomic<std::uint64_t> ShaderMixedPairSamples{0};
        std::atomic<std::uint64_t> ShaderFixedFunctionPendingSamples{0};
        std::atomic<std::uint64_t> ShaderProgrammablePendingSamples{0};
        std::atomic<std::uint64_t> FixedFunctionStateCoverageExactSamples{0};
        std::atomic<std::uint64_t> FixedFunctionStateCoverageFailureSamples{0};
        std::atomic<std::uint64_t> FixedFunctionTranslationReadySamples{0};
        std::atomic<std::uint64_t> FixedFunctionTranslationPendingSamples{0};
        std::atomic<std::uint64_t> FixedFunctionPipelineShaderExactSamples{0};
        std::atomic<std::uint64_t> FixedFunctionPipelineShaderPendingSamples{0};
        std::atomic<std::uint64_t> FixedFunctionAlphaTestShaderOwnedSamples{0};
        std::atomic<std::uint64_t> FixedFunctionShaderPrototypeGeneratedSamples{0};
        std::atomic<std::uint64_t> FixedFunctionShaderPrototypePendingSamples{0};
        std::atomic<std::uint64_t> FixedFunctionShaderCompileSucceededSignatures{0};
        std::atomic<std::uint64_t> FixedFunctionShaderCompileFailedSignatures{0};
        std::atomic<std::uint64_t> FixedFunctionShaderCompileSkippedSignatureCap{0};
        std::atomic<std::uint64_t> TextureStageBoundResources{0};
        std::atomic<std::uint64_t> TextureStageExactResources{0};
        std::atomic<std::uint64_t> TextureStagePendingResources{0};
        std::atomic<std::uint64_t> IndexedSamples{0};
        std::atomic<std::uint64_t> TexturedSamples{0};
        std::array<std::atomic<std::uint64_t>, UnsupportedBitCount>
            UnsupportedCounts{};
        std::atomic<ULONGLONG> LastLogMs{0};
        std::mutex SignatureMutex;
        std::unordered_set<std::uint64_t> SignatureHashes;

        struct BufferMutationEvidence
        {
            bool lockPending{};
            bool descriptorObserved{};
            ResourceRole role = ResourceRole::Vertex;
            D3DPOOL pool = D3DPOOL_FORCE_DWORD;
            DWORD usage{};
            UINT offset{};
            UINT size{};
            DWORD flags{};
        };

        using BufferMutationRegistry =
            std::unordered_map<const void*, BufferMutationEvidence>;
        std::mutex MutationEvidenceMutex;
        BufferMutationRegistry VertexMutationEvidence;
        BufferMutationRegistry IndexMutationEvidence;
        ManagedMirrorLifetimeState ManagedLifetimeEvidence{};
        NativeManagedTextureRegistry ManagedTextureShadowRegistry{};

        struct TextureMutationEvidence
        {
            bool descriptorObserved{};
            D3DPOOL pool = D3DPOOL_FORCE_DWORD;
            DWORD usage{};
            DWORD flags{};
        };

        using TextureMutationRegistry =
            std::unordered_map<const void*,
                std::unordered_map<UINT, TextureMutationEvidence>>;
        TextureMutationRegistry TextureMutationEvidenceRegistry;

        struct TextureStageResourceState
        {
            D3DRESOURCETYPE type = D3DRTYPE_FORCE_DWORD;
            DWORD usage{};
            D3DPOOL pool = D3DPOOL_FORCE_DWORD;
            D3DFORMAT format = D3DFMT_UNKNOWN;
            bool present{};
            bool observed{};
            bool managedShadowRequired{};
            bool managedShadowReady{};
        };

        struct ShaderFunctionSignature
        {
            bool present{};
            bool observed{};
            UINT byteSize{};
            DWORD versionToken{};
            std::uint64_t hash{};
        };

        struct SourceSignature
        {
            DWORD fvf{};
            std::uint64_t vertexDeclHash{};
            UINT vertexDeclElements{};
            std::array<D3DVERTEXELEMENT9, MAXD3DDECLLENGTH + 1> vertexDeclElementsData{};
            UINT streamOffset{};
            UINT stride{};
            DWORD vertexUsage{};
            D3DPOOL vertexPool = D3DPOOL_FORCE_DWORD;
            DWORD indexUsage{};
            D3DPOOL indexPool = D3DPOOL_FORCE_DWORD;
            D3DFORMAT indexFormat = D3DFMT_UNKNOWN;
            DWORD renderTargetUsage{};
            D3DPOOL renderTargetPool = D3DPOOL_FORCE_DWORD;
            D3DFORMAT renderTargetFormat = D3DFMT_UNKNOWN;
            DWORD depthUsage{};
            D3DPOOL depthPool = D3DPOOL_FORCE_DWORD;
            D3DFORMAT depthFormat = D3DFMT_UNKNOWN;
            std::array<TextureStageResourceState, 8> textureStages{};
            std::uint8_t textureResourcePresentMask{};
            std::uint8_t textureResourceExactMask{};
            std::uint8_t textureManagedShadowRequiredMask{};
            std::uint8_t textureManagedShadowReadyMask{};
            // D3D9 fixed-function texture blending exposes stages 0..7.
            // R81 observes all eight stages and the currently modeled sampler
            // fields for each stage; this remains evidence, not emulation.
            std::array<FixedFunctionStageState, 8> fixedFunctionStages{};
            DWORD colorOp0 = D3DTOP_DISABLE;
            DWORD alphaOp0 = D3DTOP_DISABLE;
            DWORD colorOp1 = D3DTOP_DISABLE;
            DWORD alphaOp1 = D3DTOP_DISABLE;
            DWORD minFilter = D3DTEXF_NONE;
            DWORD magFilter = D3DTEXF_NONE;
            DWORD mipFilter = D3DTEXF_NONE;
            DWORD addressU = D3DTADDRESS_WRAP;
            DWORD addressV = D3DTADDRESS_WRAP;
            bool vertexDeclaration{};
            bool inputLayoutExact{};
            bool inputLayoutFvfExact{};
            bool inputLayoutFvfPending{};
            UINT inputLayoutElements{};
            ShaderFunctionSignature vertexShader{};
            ShaderFunctionSignature pixelShader{};
            bool shaderIntrospectionComplete{};
            bool shaderMixedPair{};
            bool shaderTranslationExact{};
            bool fixedFunctionStateCoverageExact{};
            bool alphaTestObservationComplete{};
            DWORD alphaTestEnable = FALSE;
            DWORD alphaTestRef{};
            DWORD alphaTestFunc = D3DCMP_ALWAYS;
            bool fogObservationComplete{};
            DWORD fogEnable = FALSE;
            DWORD fogColor{};
            DWORD fogTableMode = D3DFOG_NONE;
            DWORD fogStartBits{};
            DWORD fogEndBits = 0x3F800000u;
            DWORD fogDensityBits = 0x3F800000u;
            DWORD rangeFogEnable = FALSE;
            DWORD fogVertexMode = D3DFOG_NONE;
            bool fixedFunctionTranslationReady{};
            std::uint32_t fixedFunctionTranslationUnsupported{};
            UINT fixedFunctionActiveStages{};
            bool fixedFunctionPipelineShaderExact{};
            std::uint32_t fixedFunctionPipelineShaderUnsupported{};
            bool fixedFunctionAlphaTestOwnedByPixelShader{};
            bool fixedFunctionShaderPrototypeGenerated{};
            std::uint32_t fixedFunctionShaderPrototypeUnsupported{};
            std::uint64_t fixedFunctionShaderPrototypeHash{};
            UINT fixedFunctionShaderPrototypeBytes{};
            bool fixedFunctionVertexShaderPrototypeGenerated{};
            std::uint32_t fixedFunctionVertexShaderPrototypeUnsupported{};
            std::uint64_t fixedFunctionVertexShaderPrototypeHash{};
            UINT fixedFunctionVertexShaderPrototypeBytes{};
            bool fixedFunctionTransformExact{};
            std::uint32_t fixedFunctionTransformUnsupported{};
            std::uint64_t fixedFunctionTransformHash{};
            bool vertexBufferPresent{};
            bool renderTargetPresent{};
            bool indexed{};
            bool textured{};
            bool depthPresent{};
            bool resourceIntrospectionComplete{true};
            bool fixedFunction{};
        };

        std::uint64_t hash_mix(std::uint64_t hash, std::uint64_t value) noexcept
        {
            hash ^= value + 0x9e3779b97f4a7c15ull + (hash << 6) + (hash >> 2);
            return hash;
        }

        // R114/F22: hash the per-thread draw ordinal before applying the 1/64
        // census stride. This preserves bounded diagnostic cost while avoiding
        // the permanent fixed-phase alias of (++ordinal % 64) against periodic
        // draw ordering. It is still sampled evidence, never exhaustive proof.
        std::uint64_t mix_sample_ordinal(std::uint64_t value) noexcept
        {
            value += 0x9e3779b97f4a7c15ull;
            value = (value ^ (value >> 30)) * 0xbf58476d1ce4e5b9ull;
            value = (value ^ (value >> 27)) * 0x94d049bb133111ebull;
            return value ^ (value >> 31);
        }

        std::uint64_t hash_signature(
            const SourceSignature& sig,
            D3DPRIMITIVETYPE primitive) noexcept
        {
            std::uint64_t hash = 0xcbf29ce484222325ull;
            hash = hash_mix(hash, static_cast<std::uint32_t>(primitive));
            hash = hash_mix(hash, sig.fvf);
            hash = hash_mix(hash, sig.vertexDeclHash);
            hash = hash_mix(hash, sig.vertexDeclElements);
            hash = hash_mix(hash, sig.streamOffset);
            hash = hash_mix(hash, sig.stride);
            hash = hash_mix(hash, sig.vertexUsage);
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.vertexPool));
            hash = hash_mix(hash, sig.indexUsage);
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.indexPool));
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.indexFormat));
            hash = hash_mix(hash, sig.renderTargetUsage);
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.renderTargetPool));
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.renderTargetFormat));
            hash = hash_mix(hash, sig.depthUsage);
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.depthPool));
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.depthFormat));
            for (const auto& texture : sig.textureStages)
            {
                hash = hash_mix(hash, texture.present ? 1u : 0u);
                hash = hash_mix(hash, texture.observed ? 1u : 0u);
                hash = hash_mix(hash, static_cast<std::uint32_t>(texture.type));
                hash = hash_mix(hash, texture.usage);
                hash = hash_mix(hash, static_cast<std::uint32_t>(texture.pool));
                hash = hash_mix(hash, static_cast<std::uint32_t>(texture.format));
                hash = hash_mix(hash, texture.managedShadowRequired ? 1u : 0u);
                hash = hash_mix(hash, texture.managedShadowReady ? 1u : 0u);
            }
            hash = hash_mix(hash, sig.textureResourcePresentMask);
            hash = hash_mix(hash, sig.textureResourceExactMask);
            hash = hash_mix(hash, sig.textureManagedShadowRequiredMask);
            hash = hash_mix(hash, sig.textureManagedShadowReadyMask);
            hash = hash_mix(hash, sig.colorOp0);
            hash = hash_mix(hash, sig.alphaOp0);
            hash = hash_mix(hash, sig.colorOp1);
            hash = hash_mix(hash, sig.alphaOp1);
            for (const auto& stage : sig.fixedFunctionStages)
            {
                hash = hash_mix(hash, stage.colorOp);
                hash = hash_mix(hash, stage.colorArg1);
                hash = hash_mix(hash, stage.colorArg2);
                hash = hash_mix(hash, stage.alphaOp);
                hash = hash_mix(hash, stage.alphaArg1);
                hash = hash_mix(hash, stage.alphaArg2);
                hash = hash_mix(hash, stage.texCoordIndex);
                hash = hash_mix(hash, stage.textureTransformFlags);
                hash = hash_mix(hash, stage.minFilter);
                hash = hash_mix(hash, stage.magFilter);
                hash = hash_mix(hash, stage.mipFilter);
                hash = hash_mix(hash, stage.addressU);
                hash = hash_mix(hash, stage.addressV);
            }
            hash = hash_mix(
                hash, sig.alphaTestObservationComplete ? 1u : 0u);
            hash = hash_mix(hash, sig.alphaTestEnable);
            hash = hash_mix(hash, sig.alphaTestRef & 0xFFu);
            hash = hash_mix(hash, sig.alphaTestFunc);
            hash = hash_mix(
                hash, sig.fogObservationComplete ? 1u : 0u);
            hash = hash_mix(hash, sig.fogEnable);
            if (sig.fogEnable != FALSE)
            {
                // D3D9 ignores fog-color alpha. Hash only RGB plus every
                // remaining mode/parameter state that can affect fog output.
                hash = hash_mix(hash, sig.fogColor & 0x00FFFFFFu);
                hash = hash_mix(hash, sig.fogTableMode);
                hash = hash_mix(hash, sig.fogStartBits);
                hash = hash_mix(hash, sig.fogEndBits);
                hash = hash_mix(hash, sig.fogDensityBits);
                hash = hash_mix(hash, sig.rangeFogEnable);
                hash = hash_mix(hash, sig.fogVertexMode);
            }
            hash = hash_mix(hash, sig.minFilter);
            hash = hash_mix(hash, sig.magFilter);
            hash = hash_mix(hash, sig.mipFilter);
            hash = hash_mix(hash, sig.addressU);
            hash = hash_mix(hash, sig.addressV);
            hash = hash_mix(hash, sig.vertexDeclaration ? 1u : 0u);
            hash = hash_mix(hash, sig.inputLayoutExact ? 1u : 0u);
            hash = hash_mix(hash, sig.inputLayoutFvfExact ? 1u : 0u);
            hash = hash_mix(hash, sig.inputLayoutFvfPending ? 1u : 0u);
            hash = hash_mix(hash, sig.inputLayoutElements);
            hash = hash_mix(hash, sig.vertexShader.present ? 1u : 0u);
            hash = hash_mix(hash, sig.vertexShader.observed ? 1u : 0u);
            hash = hash_mix(hash, sig.vertexShader.byteSize);
            hash = hash_mix(hash, sig.vertexShader.versionToken);
            hash = hash_mix(hash, sig.vertexShader.hash);
            hash = hash_mix(hash, sig.pixelShader.present ? 1u : 0u);
            hash = hash_mix(hash, sig.pixelShader.observed ? 1u : 0u);
            hash = hash_mix(hash, sig.pixelShader.byteSize);
            hash = hash_mix(hash, sig.pixelShader.versionToken);
            hash = hash_mix(hash, sig.pixelShader.hash);
            hash = hash_mix(hash, sig.shaderIntrospectionComplete ? 1u : 0u);
            hash = hash_mix(hash, sig.shaderMixedPair ? 1u : 0u);
            hash = hash_mix(hash, sig.shaderTranslationExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.fixedFunctionStateCoverageExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.fixedFunctionTranslationReady ? 1u : 0u);
            hash = hash_mix(
                hash, sig.fixedFunctionTranslationUnsupported);
            hash = hash_mix(hash, sig.fixedFunctionActiveStages);
            hash = hash_mix(
                hash, sig.fixedFunctionPipelineShaderExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.fixedFunctionPipelineShaderUnsupported);
            hash = hash_mix(
                hash, sig.fixedFunctionAlphaTestOwnedByPixelShader ? 1u : 0u);
            hash = hash_mix(
                hash, sig.fixedFunctionShaderPrototypeGenerated ? 1u : 0u);
            hash = hash_mix(
                hash, sig.fixedFunctionShaderPrototypeUnsupported);
            hash = hash_mix(
                hash, sig.fixedFunctionShaderPrototypeHash);
            hash = hash_mix(
                hash, sig.fixedFunctionShaderPrototypeBytes);
            hash = hash_mix(
                hash,
                sig.fixedFunctionVertexShaderPrototypeGenerated ? 1u : 0u);
            hash = hash_mix(
                hash, sig.fixedFunctionVertexShaderPrototypeUnsupported);
            hash = hash_mix(
                hash, sig.fixedFunctionVertexShaderPrototypeHash);
            hash = hash_mix(
                hash, sig.fixedFunctionVertexShaderPrototypeBytes);
            hash = hash_mix(
                hash, sig.fixedFunctionTransformExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.fixedFunctionTransformUnsupported);
            hash = hash_mix(hash, sig.vertexBufferPresent ? 1u : 0u);
            hash = hash_mix(hash, sig.renderTargetPresent ? 1u : 0u);
            hash = hash_mix(hash, sig.indexed ? 1u : 0u);
            hash = hash_mix(hash, sig.textured ? 1u : 0u);
            hash = hash_mix(hash, sig.fixedFunction ? 1u : 0u);
            return hash;
        }

        void begin_observed_buffer_lock(
            BufferMutationRegistry& registry,
            const void* resource,
            ResourceRole role,
            D3DPOOL pool,
            DWORD usage,
            bool descriptorObserved,
            UINT offset,
            UINT size,
            DWORD flags) noexcept
        {
            if (!resource)
                return;
            std::lock_guard<std::mutex> lock(MutationEvidenceMutex);
            auto& evidence = registry[resource];
            evidence.lockPending = true;
            evidence.descriptorObserved = descriptorObserved;
            evidence.role = role;
            evidence.pool = pool;
            evidence.usage = usage;
            evidence.offset = offset;
            evidence.size = size;
            evidence.flags = flags;
        }

        void note_managed_lifetime_access(bool write) noexcept
        {
            if (write)
                ResourceManagedShadowWrites.fetch_add(
                    1, std::memory_order_relaxed);
            else
                ResourceManagedShadowReads.fetch_add(
                    1, std::memory_order_relaxed);

            if (!write)
                return;
            std::lock_guard<std::mutex> lock(MutationEvidenceMutex);
            ManagedLifetimeEvidence =
                note_managed_shadow_write(ManagedLifetimeEvidence);
        }

        ManagedMirrorLifetimeState managed_lifetime_snapshot() noexcept
        {
            std::lock_guard<std::mutex> lock(MutationEvidenceMutex);
            return ManagedLifetimeEvidence;
        }

        void finish_observed_buffer_unlock(
            BufferMutationRegistry& registry,
            const void* resource,
            HRESULT result) noexcept
        {
            if (!resource)
                return;

            BufferMutationEvidence evidence{};
            bool pending = false;
            {
                std::lock_guard<std::mutex> lock(MutationEvidenceMutex);
                const auto it = registry.find(resource);
                if (it == registry.end())
                    return;
                pending = it->second.lockPending;
                evidence = it->second;
                it->second.lockPending = false;
            }

            if (!pending || FAILED(result))
                return;

            if ((evidence.flags & D3DLOCK_READONLY) != 0)
            {
                ResourceMutationReadOnlyUnlocks.fetch_add(
                    1, std::memory_order_relaxed);
            }
            else
            {
                ResourceMutationWriteUnlocks.fetch_add(
                    1, std::memory_order_relaxed);
                if ((evidence.flags & D3DLOCK_DISCARD) != 0)
                    ResourceMutationDiscardWriteUnlocks.fetch_add(
                        1, std::memory_order_relaxed);
                if ((evidence.flags & D3DLOCK_NOOVERWRITE) != 0)
                    ResourceMutationNoOverwriteWriteUnlocks.fetch_add(
                        1, std::memory_order_relaxed);
            }

            if (!evidence.descriptorObserved)
            {
                ResourceMutationPlanUnsupportedUnlocks.fetch_add(
                    1, std::memory_order_relaxed);
                return;
            }

            const auto plan = translate_buffer_mutation(
                evidence.role, evidence.pool, evidence.usage, evidence.flags);
            switch (plan.kind)
            {
            case BufferMutationUpdateKind::DynamicMapWrite:
                ResourceMutationPlanExactUnlocks.fetch_add(
                    1, std::memory_order_relaxed);
                ResourceMutationMapWriteUnlocks.fetch_add(
                    1, std::memory_order_relaxed);
                break;
            case BufferMutationUpdateKind::DynamicMapWriteDiscard:
                ResourceMutationPlanExactUnlocks.fetch_add(
                    1, std::memory_order_relaxed);
                ResourceMutationMapDiscardUnlocks.fetch_add(
                    1, std::memory_order_relaxed);
                break;
            case BufferMutationUpdateKind::DynamicMapWriteNoOverwrite:
                ResourceMutationPlanExactUnlocks.fetch_add(
                    1, std::memory_order_relaxed);
                ResourceMutationMapNoOverwriteUnlocks.fetch_add(
                    1, std::memory_order_relaxed);
                break;
            case BufferMutationUpdateKind::DefaultUpdateSubresource:
                ResourceMutationPlanExactUnlocks.fetch_add(
                    1, std::memory_order_relaxed);
                ResourceMutationUpdateSubresourceUnlocks.fetch_add(
                    1, std::memory_order_relaxed);
                break;
            case BufferMutationUpdateKind::ManagedCpuShadowRead:
                ResourceMutationManagedShadowUnlocks.fetch_add(
                    1, std::memory_order_relaxed);
                note_managed_lifetime_access(false);
                break;
            case BufferMutationUpdateKind::ManagedCpuShadowWrite:
                ResourceMutationManagedShadowUnlocks.fetch_add(
                    1, std::memory_order_relaxed);
                note_managed_lifetime_access(true);
                break;
            case BufferMutationUpdateKind::Unsupported:
            default:
                ResourceMutationPlanUnsupportedUnlocks.fetch_add(
                    1, std::memory_order_relaxed);
                break;
            }
        }

        void forget_observed_buffer(
            BufferMutationRegistry& registry,
            const void* resource) noexcept
        {
            if (!resource)
                return;
            std::lock_guard<std::mutex> lock(MutationEvidenceMutex);
            registry.erase(resource);
        }

        void begin_observed_texture_lock(
            const void* resource,
            UINT level,
            bool descriptorObserved,
            D3DPOOL pool,
            DWORD usage,
            DWORD flags) noexcept
        {
            if (!resource)
                return;
            std::lock_guard<std::mutex> lock(MutationEvidenceMutex);
            auto& evidence = TextureMutationEvidenceRegistry[resource][level];
            evidence.descriptorObserved = descriptorObserved;
            evidence.pool = pool;
            evidence.usage = usage;
            evidence.flags = flags;
            if (!descriptorObserved)
                ResourceTextureMutationDescriptorFailures.fetch_add(
                    1, std::memory_order_relaxed);
        }

        void finish_observed_texture_unlock(
            const void* resource,
            UINT level,
            HRESULT result) noexcept
        {
            if (!resource)
                return;

            TextureMutationEvidence evidence{};
            bool pending = false;
            {
                std::lock_guard<std::mutex> lock(MutationEvidenceMutex);
                const auto resourceIt =
                    TextureMutationEvidenceRegistry.find(resource);
                if (resourceIt == TextureMutationEvidenceRegistry.end())
                    return;
                const auto levelIt = resourceIt->second.find(level);
                if (levelIt == resourceIt->second.end())
                    return;
                evidence = levelIt->second;
                pending = true;
                resourceIt->second.erase(levelIt);
                if (resourceIt->second.empty())
                    TextureMutationEvidenceRegistry.erase(resourceIt);
            }

            if (!pending || FAILED(result))
                return;
            const bool readOnly =
                (evidence.flags & D3DLOCK_READONLY) != 0;
            if (readOnly)
                ResourceTextureMutationReadOnlyUnlocks.fetch_add(
                    1, std::memory_order_relaxed);
            else
                ResourceTextureMutationWriteUnlocks.fetch_add(
                    1, std::memory_order_relaxed);

            if (evidence.descriptorObserved &&
                evidence.pool == D3DPOOL_MANAGED)
                note_managed_lifetime_access(!readOnly);
        }

        bool invalidate_managed_texture_update_target(
            IDirect3DBaseTexture9* destination) noexcept
        {
            if (!destination || destination->GetType() != D3DRTYPE_TEXTURE)
                return false;

            IDirect3DTexture9* texture = nullptr;
            if (FAILED(destination->QueryInterface(
                    __uuidof(IDirect3DTexture9),
                    reinterpret_cast<void**>(&texture))) || !texture)
                return false;

            const bool invalidated =
                ManagedTextureShadowRegistry.invalidate_external_mutation(texture);
            texture->Release();
            return invalidated;
        }

        bool invalidate_managed_texture_update_target(
            IDirect3DSurface9* destination) noexcept
        {
            if (!destination)
                return false;

            IDirect3DTexture9* texture = nullptr;
            if (FAILED(destination->GetContainer(
                    __uuidof(IDirect3DTexture9),
                    reinterpret_cast<void**>(&texture))) || !texture)
                return false;

            const bool invalidated =
                ManagedTextureShadowRegistry.invalidate_external_mutation(texture);
            texture->Release();
            return invalidated;
        }

        bool inspect_texture(
            IDirect3DDevice9* device,
            DWORD stage,
            D3DRESOURCETYPE& type,
            DWORD& usage,
            D3DPOOL& pool,
            D3DFORMAT& format,
            bool& present,
            bool& managedShadowRequired,
            bool& managedShadowReady) noexcept
        {
            type = D3DRTYPE_FORCE_DWORD;
            usage = 0;
            pool = D3DPOOL_FORCE_DWORD;
            format = D3DFMT_UNKNOWN;
            present = false;
            managedShadowRequired = false;
            managedShadowReady = false;
            const void* textureIdentity = nullptr;

            IDirect3DBaseTexture9* base = nullptr;
            const HRESULT getHr = device->GetTexture(stage, &base);
            if (FAILED(getHr))
                return false;
            if (!base)
                return true;

            present = true;
            type = base->GetType();
            bool descriptorObserved = false;
            if (type == D3DRTYPE_TEXTURE)
            {
                IDirect3DTexture9* texture = nullptr;
                if (SUCCEEDED(base->QueryInterface(
                        __uuidof(IDirect3DTexture9),
                        reinterpret_cast<void**>(&texture))) && texture)
                {
                    D3DSURFACE_DESC desc{};
                    if (SUCCEEDED(texture->GetLevelDesc(0, &desc)))
                    {
                        usage = desc.Usage;
                        pool = desc.Pool;
                        format = desc.Format;
                        descriptorObserved = true;
                        textureIdentity = texture;
                    }
                    texture->Release();
                }
            }
            else if (type == D3DRTYPE_CUBETEXTURE)
            {
                IDirect3DCubeTexture9* texture = nullptr;
                if (SUCCEEDED(base->QueryInterface(
                        __uuidof(IDirect3DCubeTexture9),
                        reinterpret_cast<void**>(&texture))) && texture)
                {
                    D3DSURFACE_DESC desc{};
                    if (SUCCEEDED(texture->GetLevelDesc(0, &desc)))
                    {
                        usage = desc.Usage;
                        pool = desc.Pool;
                        format = desc.Format;
                        descriptorObserved = true;
                    }
                    texture->Release();
                }
            }
            else if (type == D3DRTYPE_VOLUMETEXTURE)
            {
                IDirect3DVolumeTexture9* texture = nullptr;
                if (SUCCEEDED(base->QueryInterface(
                        __uuidof(IDirect3DVolumeTexture9),
                        reinterpret_cast<void**>(&texture))) && texture)
                {
                    D3DVOLUME_DESC desc{};
                    if (SUCCEEDED(texture->GetLevelDesc(0, &desc)))
                    {
                        usage = desc.Usage;
                        pool = desc.Pool;
                        format = desc.Format;
                        descriptorObserved = true;
                    }
                    texture->Release();
                }
            }

            if (descriptorObserved)
            {
                const auto behavior = translate_resource_behavior(
                    ResourceRole::Texture, pool, usage);
                managedShadowRequired =
                    behavior.descriptorExact && behavior.requiresCpuShadow;
                managedShadowReady =
                    !managedShadowRequired ||
                    (type == D3DRTYPE_TEXTURE &&
                     textureIdentity != nullptr &&
                     ManagedTextureShadowRegistry.shadow_valid(textureIdentity));
            }

            base->Release();
            return descriptorObserved;
        }

        template <typename TShader>
        ShaderFunctionSignature inspect_shader_function(
            TShader* shader) noexcept
        {
            ShaderFunctionSignature out{};
            out.present = shader != nullptr;
            if (!shader)
            {
                out.observed = true;
                return out;
            }

            UINT byteSize = 0;
            if (FAILED(shader->GetFunction(nullptr, &byteSize)) ||
                byteSize < sizeof(DWORD) ||
                byteSize > (1024u * 1024u))
                return out;

            std::vector<std::uint8_t> bytecode(byteSize);
            UINT actual = byteSize;
            if (FAILED(shader->GetFunction(bytecode.data(), &actual)) ||
                actual != byteSize)
                return out;

            out.observed = true;
            out.byteSize = actual;
            std::memcpy(
                &out.versionToken, bytecode.data(), sizeof(out.versionToken));

            std::uint64_t hash = 1469598103934665603ull;
            for (const auto byte : bytecode)
            {
                hash ^= static_cast<std::uint64_t>(byte);
                hash *= 1099511628211ull;
            }
            out.hash = hash;
            return out;
        }

        SourceSignature inspect_source_signature(
            IDirect3DDevice9* device,
            bool fixedFunction,
            IDirect3DVertexShader9* vertexShader,
            IDirect3DPixelShader9* pixelShader,
            bool shaderQueryComplete) noexcept
        {
            SourceSignature sig{};
            sig.fixedFunction = fixedFunction;
            sig.vertexShader = inspect_shader_function(vertexShader);
            sig.pixelShader = inspect_shader_function(pixelShader);
            sig.shaderIntrospectionComplete =
                shaderQueryComplete &&
                sig.vertexShader.observed &&
                sig.pixelShader.observed;
            sig.shaderMixedPair =
                shaderQueryComplete &&
                ((vertexShader != nullptr) != (pixelShader != nullptr));

            // R80 is deliberately fail-closed: no native D3D11 shader
            // translator or complete fixed-function emulation exists yet.
            // Fingerprints are evidence for F21; they are not readiness.
            sig.shaderTranslationExact = false;

            device->GetFVF(&sig.fvf);

            IDirect3DVertexDeclaration9* declaration = nullptr;
            if (SUCCEEDED(device->GetVertexDeclaration(&declaration)) &&
                declaration)
            {
                sig.vertexDeclaration = true;

                UINT count = 0;
                if (SUCCEEDED(declaration->GetDeclaration(nullptr, &count)) &&
                    count > 0 && count <= (MAXD3DDECLLENGTH + 1))
                {
                    std::vector<D3DVERTEXELEMENT9> elements(count);
                    UINT actual = count;
                    if (SUCCEEDED(declaration->GetDeclaration(
                            elements.data(), &actual)) &&
                        actual > 0 && actual <= count)
                    {
                        std::uint64_t declHash = 0xcbf29ce484222325ull;
                        for (UINT i = 0; i < actual; ++i)
                        {
                            const auto& element = elements[i];
                            declHash = hash_mix(declHash, element.Stream);
                            declHash = hash_mix(declHash, element.Offset);
                            declHash = hash_mix(declHash, element.Type);
                            declHash = hash_mix(declHash, element.Method);
                            declHash = hash_mix(declHash, element.Usage);
                            declHash = hash_mix(declHash, element.UsageIndex);
                        }
                        sig.vertexDeclHash = declHash;
                        sig.vertexDeclElements = actual;
                        for (UINT i = 0; i < actual; ++i)
                            sig.vertexDeclElementsData[i] = elements[i];
                    }
                }
                declaration->Release();
            }

            IDirect3DVertexBuffer9* vb = nullptr;
            const HRESULT streamHr = device->GetStreamSource(
                0, &vb, &sig.streamOffset, &sig.stride);
            if (FAILED(streamHr))
            {
                sig.resourceIntrospectionComplete = false;
            }
            else if (vb)
            {
                sig.vertexBufferPresent = true;
                D3DVERTEXBUFFER_DESC desc{};
                if (SUCCEEDED(vb->GetDesc(&desc)))
                {
                    sig.vertexUsage = desc.Usage;
                    sig.vertexPool = desc.Pool;
                }
                else
                    sig.resourceIntrospectionComplete = false;
                vb->Release();
            }

            IDirect3DSurface9* rt0 = nullptr;
            const HRESULT rtHr = device->GetRenderTarget(0, &rt0);
            if (FAILED(rtHr) || !rt0)
            {
                sig.resourceIntrospectionComplete = false;
            }
            else
            {
                sig.renderTargetPresent = true;
                D3DSURFACE_DESC desc{};
                if (SUCCEEDED(rt0->GetDesc(&desc)))
                {
                    sig.renderTargetUsage = desc.Usage;
                    sig.renderTargetPool = desc.Pool;
                    sig.renderTargetFormat = desc.Format;
                }
                else
                    sig.resourceIntrospectionComplete = false;
                rt0->Release();
            }

            IDirect3DSurface9* depth = nullptr;
            const HRESULT depthHr = device->GetDepthStencilSurface(&depth);
            if (FAILED(depthHr) && depthHr != D3DERR_NOTFOUND)
            {
                sig.resourceIntrospectionComplete = false;
            }
            else if (depth)
            {
                sig.depthPresent = true;
                D3DSURFACE_DESC desc{};
                if (SUCCEEDED(depth->GetDesc(&desc)))
                {
                    sig.depthUsage = desc.Usage;
                    sig.depthPool = desc.Pool;
                    sig.depthFormat = desc.Format;
                }
                else
                    sig.resourceIntrospectionComplete = false;
                depth->Release();
            }

            IDirect3DIndexBuffer9* ib = nullptr;
            const HRESULT indexHr = device->GetIndices(&ib);
            if (FAILED(indexHr))
            {
                sig.resourceIntrospectionComplete = false;
            }
            else if (ib)
            {
                D3DINDEXBUFFER_DESC desc{};
                if (SUCCEEDED(ib->GetDesc(&desc)))
                {
                    sig.indexUsage = desc.Usage;
                    sig.indexPool = desc.Pool;
                    sig.indexFormat = desc.Format;
                }
                else
                    sig.resourceIntrospectionComplete = false;
                sig.indexed = true;
                ib->Release();
            }

            for (DWORD stage = 0;
                 stage < static_cast<DWORD>(sig.textureStages.size());
                 ++stage)
            {
                auto& texture = sig.textureStages[stage];
                texture.observed = inspect_texture(
                    device, stage, texture.type, texture.usage,
                    texture.pool, texture.format, texture.present,
                    texture.managedShadowRequired,
                    texture.managedShadowReady);
                if (!texture.observed)
                    sig.resourceIntrospectionComplete = false;
                if (texture.present)
                {
                    sig.textured = true;
                    const auto stageBit =
                        static_cast<std::uint8_t>(1u << stage);
                    sig.textureResourcePresentMask |= stageBit;
                    if (texture.managedShadowRequired)
                    {
                        sig.textureManagedShadowRequiredMask |= stageBit;
                        if (texture.managedShadowReady)
                            sig.textureManagedShadowReadyMask |= stageBit;
                    }
                }
            }

            if (fixedFunction)
            {
                sig.fixedFunctionStateCoverageExact = true;
                for (DWORD stage = 0;
                     stage < static_cast<DWORD>(sig.fixedFunctionStages.size());
                     ++stage)
                {
                    auto& out = sig.fixedFunctionStages[stage];
                    const auto observeTextureStageState =
                        [&](D3DTEXTURESTAGESTATETYPE type,
                            DWORD& value) noexcept
                    {
                        if (FAILED(device->GetTextureStageState(
                                stage, type, &value)))
                            sig.fixedFunctionStateCoverageExact = false;
                    };
                    const auto observeSamplerState =
                        [&](D3DSAMPLERSTATETYPE type,
                            DWORD& value) noexcept
                    {
                        if (FAILED(device->GetSamplerState(
                                stage, type, &value)))
                            sig.fixedFunctionStateCoverageExact = false;
                    };

                    observeTextureStageState(D3DTSS_COLOROP, out.colorOp);
                    observeTextureStageState(D3DTSS_COLORARG1, out.colorArg1);
                    observeTextureStageState(D3DTSS_COLORARG2, out.colorArg2);
                    observeTextureStageState(D3DTSS_ALPHAOP, out.alphaOp);
                    observeTextureStageState(D3DTSS_ALPHAARG1, out.alphaArg1);
                    observeTextureStageState(D3DTSS_ALPHAARG2, out.alphaArg2);
                    observeTextureStageState(
                        D3DTSS_TEXCOORDINDEX, out.texCoordIndex);
                    observeTextureStageState(
                        D3DTSS_TEXTURETRANSFORMFLAGS,
                        out.textureTransformFlags);

                    observeSamplerState(D3DSAMP_MINFILTER, out.minFilter);
                    observeSamplerState(D3DSAMP_MAGFILTER, out.magFilter);
                    observeSamplerState(D3DSAMP_MIPFILTER, out.mipFilter);
                    observeSamplerState(D3DSAMP_ADDRESSU, out.addressU);
                    observeSamplerState(D3DSAMP_ADDRESSV, out.addressV);
                }
                sig.colorOp0 = sig.fixedFunctionStages[0].colorOp;
                sig.alphaOp0 = sig.fixedFunctionStages[0].alphaOp;
                sig.colorOp1 = sig.fixedFunctionStages[1].colorOp;
                sig.alphaOp1 = sig.fixedFunctionStages[1].alphaOp;
                sig.minFilter = sig.fixedFunctionStages[0].minFilter;
                sig.magFilter = sig.fixedFunctionStages[0].magFilter;
                sig.mipFilter = sig.fixedFunctionStages[0].mipFilter;
                sig.addressU = sig.fixedFunctionStages[0].addressU;
                sig.addressV = sig.fixedFunctionStages[0].addressV;

                // R83 defers translation readiness until resource behavior
                // and format exactness have been evaluated for all 8 stages.

                const auto vertexPrototype =
                    generate_fixed_function_vertex_shader_prototype(
                        sig.fvf, sig.stride);
                sig.fixedFunctionVertexShaderPrototypeGenerated =
                    vertexPrototype.generated();
                sig.fixedFunctionVertexShaderPrototypeUnsupported =
                    vertexPrototype.unsupported;
                sig.fixedFunctionVertexShaderPrototypeHash =
                    vertexPrototype.sourceHash;
                sig.fixedFunctionVertexShaderPrototypeBytes =
                    static_cast<UINT>(vertexPrototype.source.size());

                // R94 observes WORLD/VIEW/PROJECTION only on the already
                // sampled diagnostic path. It does not hook SetTransform or
                // bind native D3D11 constants.
                D3DMATRIX world{};
                D3DMATRIX view{};
                D3DMATRIX projection{};
                const HRESULT worldHr =
                    device->GetTransform(D3DTS_WORLD, &world);
                const HRESULT viewHr =
                    device->GetTransform(D3DTS_VIEW, &view);
                const HRESULT projectionHr =
                    device->GetTransform(D3DTS_PROJECTION, &projection);
                const auto transform =
                    generate_fixed_function_transform_constants(
                        world,
                        view,
                        projection,
                        SUCCEEDED(worldHr) &&
                        SUCCEEDED(viewHr) &&
                        SUCCEEDED(projectionHr));
                sig.fixedFunctionTransformExact = transform.exact();
                sig.fixedFunctionTransformUnsupported =
                    transform.unsupported;
                sig.fixedFunctionTransformHash = transform.payloadHash;
            }

            const auto inputLayout = translate_vertex_input_layout(
                sig.vertexDeclaration ? sig.vertexDeclElementsData.data() : nullptr,
                sig.vertexDeclaration ? sig.vertexDeclElements : 0,
                sig.fvf,
                sig.stride);
            sig.inputLayoutExact = inputLayout.exact;
            sig.inputLayoutFvfExact = inputLayout.fvfPath && inputLayout.exact;
            sig.inputLayoutFvfPending = inputLayout.fvfPending;
            sig.inputLayoutElements = inputLayout.elementCount;
            return sig;
        }

        void note_signature(
            const SourceSignature& sig,
            D3DPRIMITIVETYPE primitive) noexcept
        {
            const auto hash = hash_signature(sig, primitive);
            bool inserted = false;
            bool signatureHashCapHit = false;
            std::uint64_t unique = 0;
            {
                std::lock_guard<std::mutex> lock(SignatureMutex);
                const auto existing = SignatureHashes.find(hash);
                if (existing == SignatureHashes.end())
                {
                    if (SignatureHashes.size() < SignatureHashCap)
                        inserted = SignatureHashes.insert(hash).second;
                    else
                        signatureHashCapHit = true;
                }
                unique = SignatureHashes.size();
            }
            UniqueDrawSignatures.store(unique, std::memory_order_relaxed);
            if (signatureHashCapHit)
                SignatureHashCapHitSamples.fetch_add(
                    1, std::memory_order_relaxed);
            if (inserted && unique > DetailedSignatureLogCap)
                DetailedSignatureLogSkippedSignatures.fetch_add(
                    1, std::memory_order_relaxed);

            FixedFunctionPixelShaderCompileProbe compileProbe{};
            if (inserted && sig.fixedFunction &&
                sig.fixedFunctionShaderPrototypeGenerated)
            {
                if (unique <= DetailedSignatureLogCap)
                {
                    std::array<D3DRESOURCETYPE, 8> textureTypes{};
                    for (std::size_t stageIndex = 0;
                         stageIndex < sig.textureStages.size();
                         ++stageIndex)
                        textureTypes[stageIndex] =
                            sig.textureStages[stageIndex].type;

                    const auto prototype =
                        generate_fixed_function_pixel_shader_prototype(
                            sig.fixedFunctionStages,
                            sig.fixedFunctionStateCoverageExact,
                            sig.textureResourcePresentMask,
                            sig.textureResourceExactMask,
                            textureTypes,
                            FixedFunctionAlphaTestState{
                                sig.alphaTestObservationComplete,
                                sig.alphaTestEnable,
                                sig.alphaTestRef,
                                sig.alphaTestFunc
                            });
                    compileProbe =
                        compile_fixed_function_pixel_shader_prototype(
                            prototype);
                    (compileProbe.succeeded
                        ? FixedFunctionShaderCompileSucceededSignatures
                        : FixedFunctionShaderCompileFailedSignatures).fetch_add(
                            1, std::memory_order_relaxed);
                }
                else
                {
                    FixedFunctionShaderCompileSkippedSignatureCap.fetch_add(
                        1, std::memory_order_relaxed);
                }
            }

            if (sig.vertexDeclaration)
                VertexDeclarationSamples.fetch_add(
                    1, std::memory_order_relaxed);
            if (sig.inputLayoutExact)
                InputLayoutExactSamples.fetch_add(
                    1, std::memory_order_relaxed);
            else
                InputLayoutUnsupportedSamples.fetch_add(
                    1, std::memory_order_relaxed);
            if (sig.inputLayoutFvfExact)
                InputLayoutFvfExactSamples.fetch_add(
                    1, std::memory_order_relaxed);
            if (sig.inputLayoutFvfPending)
                InputLayoutFvfPendingSamples.fetch_add(
                    1, std::memory_order_relaxed);

            if (!sig.shaderIntrospectionComplete)
                ShaderIntrospectionFailureSamples.fetch_add(
                    1, std::memory_order_relaxed);
            else if (sig.shaderMixedPair)
                ShaderMixedPairSamples.fetch_add(
                    1, std::memory_order_relaxed);
            else if (sig.fixedFunction)
                ShaderFixedFunctionPendingSamples.fetch_add(
                    1, std::memory_order_relaxed);
            else
                ShaderProgrammablePendingSamples.fetch_add(
                    1, std::memory_order_relaxed);

            if (sig.fixedFunction)
            {
                (sig.fixedFunctionStateCoverageExact
                    ? FixedFunctionStateCoverageExactSamples
                    : FixedFunctionStateCoverageFailureSamples).fetch_add(
                        1, std::memory_order_relaxed);
                (sig.fixedFunctionTranslationReady
                    ? FixedFunctionTranslationReadySamples
                    : FixedFunctionTranslationPendingSamples).fetch_add(
                        1, std::memory_order_relaxed);
                (sig.fixedFunctionPipelineShaderExact
                    ? FixedFunctionPipelineShaderExactSamples
                    : FixedFunctionPipelineShaderPendingSamples).fetch_add(
                        1, std::memory_order_relaxed);
                if (sig.fixedFunctionAlphaTestOwnedByPixelShader)
                    FixedFunctionAlphaTestShaderOwnedSamples.fetch_add(
                        1, std::memory_order_relaxed);
                (sig.fixedFunctionShaderPrototypeGenerated
                    ? FixedFunctionShaderPrototypeGeneratedSamples
                    : FixedFunctionShaderPrototypePendingSamples).fetch_add(
                        1, std::memory_order_relaxed);
            }

            if (sig.indexed)
                IndexedSamples.fetch_add(1, std::memory_order_relaxed);
            if (sig.textured)
                TexturedSamples.fetch_add(1, std::memory_order_relaxed);
            for (std::size_t stageIndex = 0;
                 stageIndex < sig.textureStages.size();
                 ++stageIndex)
            {
                const auto& texture = sig.textureStages[stageIndex];
                if (!texture.present)
                    continue;
                TextureStageBoundResources.fetch_add(
                    1, std::memory_order_relaxed);
                const auto stageBit = static_cast<std::uint8_t>(
                    1u << static_cast<unsigned>(stageIndex));
                ((sig.textureResourceExactMask & stageBit) != 0
                    ? TextureStageExactResources
                    : TextureStagePendingResources).fetch_add(
                        1, std::memory_order_relaxed);

                if ((sig.textureManagedShadowRequiredMask & stageBit) != 0)
                {
                    TextureStageManagedShadowRequiredResources.fetch_add(
                        1, std::memory_order_relaxed);
                    ((sig.textureManagedShadowReadyMask & stageBit) != 0
                        ? TextureStageManagedShadowReadyResources
                        : TextureStageManagedShadowPendingResources).fetch_add(
                            1, std::memory_order_relaxed);
                }
            }

            if (inserted && unique <= DetailedSignatureLogCap)
            {
                spdlog::info(
                    "VR DX11 R85 signature#{}: primitive={} fixedFn={} fvf=0x{:08X} decl={} declHash=0x{:016X} declElems={} inputLayout[exact={},elements={},fvfExact={},fvfPending={}] shader[introspection={},mixed={},exact={},vsPresent={},vsBytes={},vsVersion=0x{:08X},vsHash=0x{:016X},psPresent={},psBytes={},psVersion=0x{:08X},psHash=0x{:016X}] ffpCoverage[exact={}] ffpReadiness[ready={},mask=0x{:08X},activeStages={}] texMask[present=0x{:02X},exact=0x{:02X}] managedTexShadow[required=0x{:02X},ready=0x{:02X}] stream0[offset={},stride={},present={},pool={},usage=0x{:08X}] ib[present={},pool={},usage=0x{:08X},fmt={}] rt[present={},pool={},usage=0x{:08X},fmt={}] depth[present={},pool={},usage=0x{:08X},fmt={}] tex0[present={},type={},pool={},usage=0x{:08X},fmt={}] tex1[present={},type={},pool={},usage=0x{:08X},fmt={}] tss0[color={},alpha={}] tss1[color={},alpha={}] samp0[min={},mag={},mip={},u={},v={}]",
                    unique,
                    static_cast<int>(primitive),
                    sig.fixedFunction ? 1 : 0,
                    sig.fvf,
                    sig.vertexDeclaration ? 1 : 0,
                    sig.vertexDeclHash,
                    sig.vertexDeclElements,
                    sig.inputLayoutExact ? 1 : 0,
                    sig.inputLayoutElements,
                    sig.inputLayoutFvfExact ? 1 : 0,
                    sig.inputLayoutFvfPending ? 1 : 0,
                    sig.shaderIntrospectionComplete ? 1 : 0,
                    sig.shaderMixedPair ? 1 : 0,
                    sig.shaderTranslationExact ? 1 : 0,
                    sig.vertexShader.present ? 1 : 0,
                    sig.vertexShader.byteSize,
                    sig.vertexShader.versionToken,
                    sig.vertexShader.hash,
                    sig.pixelShader.present ? 1 : 0,
                    sig.pixelShader.byteSize,
                    sig.pixelShader.versionToken,
                    sig.pixelShader.hash,
                    sig.fixedFunctionStateCoverageExact ? 1 : 0,
                    sig.fixedFunctionTranslationReady ? 1 : 0,
                    sig.fixedFunctionTranslationUnsupported,
                    sig.fixedFunctionActiveStages,
                    sig.textureResourcePresentMask,
                    sig.textureResourceExactMask,
                    sig.textureManagedShadowRequiredMask,
                    sig.textureManagedShadowReadyMask,
                    sig.streamOffset,
                    sig.stride,
                    sig.vertexBufferPresent ? 1 : 0,
                    static_cast<int>(sig.vertexPool),
                    sig.vertexUsage,
                    sig.indexed ? 1 : 0,
                    static_cast<int>(sig.indexPool),
                    sig.indexUsage,
                    static_cast<int>(sig.indexFormat),
                    sig.renderTargetPresent ? 1 : 0,
                    static_cast<int>(sig.renderTargetPool),
                    sig.renderTargetUsage,
                    static_cast<int>(sig.renderTargetFormat),
                    sig.depthPresent ? 1 : 0,
                    static_cast<int>(sig.depthPool),
                    sig.depthUsage,
                    static_cast<int>(sig.depthFormat),
                    sig.textureStages[0].present ? 1 : 0,
                    static_cast<int>(sig.textureStages[0].type),
                    static_cast<int>(sig.textureStages[0].pool),
                    sig.textureStages[0].usage,
                    static_cast<int>(sig.textureStages[0].format),
                    sig.textureStages[1].present ? 1 : 0,
                    static_cast<int>(sig.textureStages[1].type),
                    static_cast<int>(sig.textureStages[1].pool),
                    sig.textureStages[1].usage,
                    static_cast<int>(sig.textureStages[1].format),
                    sig.colorOp0,
                    sig.alphaOp0,
                    sig.colorOp1,
                    sig.alphaOp1,
                    sig.minFilter,
                    sig.magFilter,
                    sig.mipFilter,
                    sig.addressU,
                    sig.addressV);

                for (std::size_t stageIndex = 0;
                     stageIndex < sig.textureStages.size();
                     ++stageIndex)
                {
                    const auto& texture = sig.textureStages[stageIndex];
                    if (!texture.present)
                        continue;
                    const auto stageBit = static_cast<std::uint8_t>(
                        1u << static_cast<unsigned>(stageIndex));
                    spdlog::info(
                        "VR DX11 R85 texture signature#{} stage#{}: observed={} type={} pool={} usage=0x{:08X} fmt={} exact={} managedShadowRequired={} managedShadowReady={}",
                        unique,
                        stageIndex,
                        texture.observed ? 1 : 0,
                        static_cast<int>(texture.type),
                        static_cast<int>(texture.pool),
                        texture.usage,
                        static_cast<int>(texture.format),
                        (sig.textureResourceExactMask & stageBit) != 0 ? 1 : 0,
                        texture.managedShadowRequired ? 1 : 0,
                        texture.managedShadowReady ? 1 : 0);
                }

                if (sig.fixedFunction)
                {
                    spdlog::info(
                        "VR DX11 R119 ffp fog state#{}: observed={} enable={} colorRgb=0x{:06X} tableMode={} vertexMode={} startBits=0x{:08X} endBits=0x{:08X} densityBits=0x{:08X} range={}",
                        unique,
                        sig.fogObservationComplete ? 1 : 0,
                        sig.fogEnable != FALSE ? 1 : 0,
                        sig.fogColor & 0x00FFFFFFu,
                        sig.fogTableMode,
                        sig.fogVertexMode,
                        sig.fogStartBits,
                        sig.fogEndBits,
                        sig.fogDensityBits,
                        sig.rangeFogEnable != FALSE ? 1 : 0);

                    spdlog::info(
                        "VR DX11 R94 ffp vertex readiness#{}: generated={} mask=0x{:08X} sourceHash=0x{:016X} sourceBytes={} transform[exact={},mask=0x{:08X},payloadHash=0x{:016X}]",
                        unique,
                        sig.fixedFunctionVertexShaderPrototypeGenerated ? 1 : 0,
                        sig.fixedFunctionVertexShaderPrototypeUnsupported,
                        sig.fixedFunctionVertexShaderPrototypeHash,
                        sig.fixedFunctionVertexShaderPrototypeBytes,
                        sig.fixedFunctionTransformExact ? 1 : 0,
                        sig.fixedFunctionTransformUnsupported,
                        sig.fixedFunctionTransformHash);

                    spdlog::info(
                        "VR DX11 R85 ffp shader prototype#{}: generated={} mask=0x{:08X} hash=0x{:016X} bytes={} activeStages={}",
                        unique,
                        sig.fixedFunctionShaderPrototypeGenerated ? 1 : 0,
                        sig.fixedFunctionShaderPrototypeUnsupported,
                        sig.fixedFunctionShaderPrototypeHash,
                        sig.fixedFunctionShaderPrototypeBytes,
                        sig.fixedFunctionActiveStages);

                    spdlog::info(
                        "VR DX11 R120 ffp pipeline/shader handoff#{}: exact={} renderMask=0x{:08X} alphaTestOwnedByPixelShader={}",
                        unique,
                        sig.fixedFunctionPipelineShaderExact ? 1 : 0,
                        sig.fixedFunctionPipelineShaderUnsupported,
                        sig.fixedFunctionAlphaTestOwnedByPixelShader ? 1 : 0);

                    if (sig.fixedFunctionShaderPrototypeGenerated)
                    {
                        spdlog::info(
                            "VR DX11 R85 ffp shader compile#{}: attempted={} succeeded={} hr=0x{:08X} bytecodeHash=0x{:016X} bytecodeBytes={} diagnosticsHash=0x{:016X} diagnosticsBytes={} profile=ps_4_0",
                            unique,
                            compileProbe.attempted ? 1 : 0,
                            compileProbe.succeeded ? 1 : 0,
                            static_cast<std::uint32_t>(
                                compileProbe.result),
                            compileProbe.bytecodeHash,
                            compileProbe.bytecodeBytes,
                            compileProbe.diagnosticsHash,
                            compileProbe.diagnosticsBytes);
                    }

                    for (std::size_t stageIndex = 0;
                         stageIndex < sig.fixedFunctionStages.size();
                         ++stageIndex)
                    {
                        const auto& stage = sig.fixedFunctionStages[stageIndex];
                        if (stage.colorOp == D3DTOP_DISABLE &&
                            stage.alphaOp == D3DTOP_DISABLE)
                            continue;

                        spdlog::info(
                            "VR DX11 R85 ffp signature#{} stage#{}: color[op={},arg1=0x{:08X},arg2=0x{:08X}] alpha[op={},arg1=0x{:08X},arg2=0x{:08X}] texCoord=0x{:08X} texTransform=0x{:08X} sampler[min={},mag={},mip={},u={},v={}]",
                            unique,
                            stageIndex,
                            stage.colorOp,
                            stage.colorArg1,
                            stage.colorArg2,
                            stage.alphaOp,
                            stage.alphaArg1,
                            stage.alphaArg2,
                            stage.texCoordIndex,
                            stage.textureTransformFlags,
                            stage.minFilter,
                            stage.magFilter,
                            stage.mipFilter,
                            stage.addressU,
                            stage.addressV);
                    }
                }

                if (sig.vertexDeclaration && sig.vertexDeclElements > 0)
                {
                    for (UINT i = 0; i < sig.vertexDeclElements; ++i)
                    {
                        const auto& element = sig.vertexDeclElementsData[i];
                        spdlog::info(
                            "VR DX11 R72 decl signature#{} elem#{}: stream={} offset={} type={} method={} usage={} usageIndex={}",
                            unique,
                            i,
                            element.Stream,
                            element.Offset,
                            element.Type,
                            element.Method,
                            element.Usage,
                            element.UsageIndex);
                    }
                }
            }
        }

        bool census_exhaustive() noexcept
        {
            int cached = ExhaustiveCache.load(std::memory_order_acquire);
            if (cached >= 0)
                return cached != 0;

            char value[8]{};
            const DWORD length = GetEnvironmentVariableA(
                "OUTRUN_VR_DX11_CENSUS_EXHAUSTIVE", value,
                static_cast<DWORD>(sizeof(value)));
            const bool exhaustive =
                length > 0 && length < sizeof(value) && value[0] == '1';
            ExhaustiveCache.store(
                exhaustive ? 1 : 0, std::memory_order_release);
            return exhaustive;
        }

        std::uint32_t census_sample_stride() noexcept
        {
            return census_exhaustive() ? 1u : SampleStride;
        }

        std::uint32_t census_sampling_scheme() noexcept
        {
            return census_exhaustive() ? 2u : 1u;
        }

        bool census_enabled() noexcept
        {
            int cached = EnabledCache.load(std::memory_order_acquire);
            if (cached >= 0)
                return cached != 0;

            char value[8]{};
            const DWORD length = GetEnvironmentVariableA(
                "OUTRUN_VR_DX11_CENSUS", value,
                static_cast<DWORD>(sizeof(value)));
            const bool enabled =
                length > 0 && length < sizeof(value) && value[0] == '1';
            EnabledCache.store(enabled ? 1 : 0, std::memory_order_release);
            if (enabled)
            {
                const auto sampleStride = census_sample_stride();
                const auto samplingScheme = census_sampling_scheme();
                spdlog::info(
                    "VR DX11 R114 census ACTIVE: {} draw census; stride={} scheme={}; signatureHashCap={} detailedSignatureLogCap={}; unique-signature-only non-routing D3DCompile probes remain diagnostic and native draw routing remains disabled",
                    samplingScheme == 2u
                        ? "exhaustive"
                        : "passive hashed-ordinal sampled",
                    sampleStride,
                    samplingScheme,
                    SignatureHashCap,
                    DetailedSignatureLogCap);
            }
            return enabled;
        }

        void maybe_log() noexcept
        {
            const ULONGLONG now = GetTickCount64();
            ULONGLONG last = LastLogMs.load(std::memory_order_acquire);
            if (now - last < 5000)
                return;
            if (!LastLogMs.compare_exchange_strong(
                    last, now, std::memory_order_acq_rel,
                    std::memory_order_acquire))
                return;

            std::array<std::uint64_t, UnsupportedBitCount> unsupported{};
            for (std::size_t i = 0; i < UnsupportedBitCount; ++i)
                unsupported[i] =
                    UnsupportedCounts[i].load(std::memory_order_relaxed);

            const auto managedLifetime = managed_lifetime_snapshot();
            const auto sampleStride = census_sample_stride();
            const auto samplingScheme = census_sampling_scheme();
            spdlog::info(
                "VR DX11 R120 census: samples={} exact={} fixedFn={} programmable={} topologyUnsupported={} signatures={} sampling[drawsSeen={},stride={},scheme={}] signatureCaps[hashCap={},hashCapHitSamples={},detailCap={},detailSkipped={}] declSamples={} indexedSamples={} texturedSamples={} resourceExact[introspectionFailure={},behaviorUnsupported={},mutationTelemetryRequired={},managedShadowRequired={},indexUnsupported={},textureUnsupported={},colorUnsupported={},depthUnsupported={}] mutation[writeUnlocks={},readOnlyUnlocks={},discardWriteUnlocks={},noOverwriteWriteUnlocks={}] mutationPlan[exact={},unsupported={},managedShadow={},mapWrite={},mapDiscard={},mapNoOverwrite={},updateSubresource={}] textureMutation[writeUnlocks={},readOnlyUnlocks={},descriptorFailures={},updateTextureSuccesses={},updateTextureFailures={},updateSurfaceSuccesses={},updateSurfaceFailures={}] managedLifetime[shadowWrites={},shadowReads={},resetSuccesses={},shadowPreserved={},deviceGeneration={},shadowVersion={},mirrorGeneration={},mirrorVersion={},mirrorReady={}] managedTextureShadow[requiredSamples={},readySamples={},pendingSamples={}] managedTextureMutationSource[updateTextureInvalidations={},updateSurfaceInvalidations={}] inputLayout[exact={},unsupported={},fvfExact={},fvfPending={}] shaderReadiness[introspectionFailure={},mixedPair={},fixedFunctionPending={},programmablePending={}] ffpCoverage[exact={},queryFailure={}] ffpReadiness[ready={},pending={}] ffpPipelineShader[exact={},pending={},alphaTestOwned={}] ffpShaderPrototype[generated={},pending={}] ffpShaderCompile[succeeded={},failed={},skippedCap={}] textureStageResource[bound={},exact={},pending={}] textureStageManagedShadow[required={},ready={},pending={}] unsupported[incomplete={},wbuffer={},sepAlpha={},alphaTest={},stencil={},fog={},lighting={},srgb={},fill={},blend={},depthCmp={},cull={}]",
                Samples.load(std::memory_order_relaxed),
                ExactSamples.load(std::memory_order_relaxed),
                FixedFunctionSamples.load(std::memory_order_relaxed),
                ProgrammableSamples.load(std::memory_order_relaxed),
                UnsupportedTopologySamples.load(std::memory_order_relaxed),
                UniqueDrawSignatures.load(std::memory_order_relaxed),
                DrawCallsSeen.load(std::memory_order_relaxed),
                sampleStride,
                samplingScheme,
                SignatureHashCap,
                SignatureHashCapHitSamples.load(std::memory_order_relaxed),
                DetailedSignatureLogCap,
                DetailedSignatureLogSkippedSignatures.load(
                    std::memory_order_relaxed),
                VertexDeclarationSamples.load(std::memory_order_relaxed),
                IndexedSamples.load(std::memory_order_relaxed),
                TexturedSamples.load(std::memory_order_relaxed),
                ResourceIntrospectionFailureSamples.load(std::memory_order_relaxed),
                ResourceBehaviorUnsupportedSamples.load(std::memory_order_relaxed),
                ResourceMutationTelemetryRequiredSamples.load(std::memory_order_relaxed),
                ResourceManagedShadowRequiredSamples.load(std::memory_order_relaxed),
                UnsupportedIndexFormatSamples.load(std::memory_order_relaxed),
                UnsupportedTextureFormatSamples.load(std::memory_order_relaxed),
                UnsupportedColorFormatSamples.load(std::memory_order_relaxed),
                UnsupportedDepthFormatSamples.load(std::memory_order_relaxed),
                ResourceMutationWriteUnlocks.load(std::memory_order_relaxed),
                ResourceMutationReadOnlyUnlocks.load(std::memory_order_relaxed),
                ResourceMutationDiscardWriteUnlocks.load(std::memory_order_relaxed),
                ResourceMutationNoOverwriteWriteUnlocks.load(std::memory_order_relaxed),
                ResourceMutationPlanExactUnlocks.load(std::memory_order_relaxed),
                ResourceMutationPlanUnsupportedUnlocks.load(std::memory_order_relaxed),
                ResourceMutationManagedShadowUnlocks.load(std::memory_order_relaxed),
                ResourceMutationMapWriteUnlocks.load(std::memory_order_relaxed),
                ResourceMutationMapDiscardUnlocks.load(std::memory_order_relaxed),
                ResourceMutationMapNoOverwriteUnlocks.load(std::memory_order_relaxed),
                ResourceMutationUpdateSubresourceUnlocks.load(std::memory_order_relaxed),
                ResourceTextureMutationWriteUnlocks.load(std::memory_order_relaxed),
                ResourceTextureMutationReadOnlyUnlocks.load(std::memory_order_relaxed),
                ResourceTextureMutationDescriptorFailures.load(std::memory_order_relaxed),
                ResourceUpdateTextureSuccesses.load(std::memory_order_relaxed),
                ResourceUpdateTextureFailures.load(std::memory_order_relaxed),
                ResourceUpdateSurfaceSuccesses.load(std::memory_order_relaxed),
                ResourceUpdateSurfaceFailures.load(std::memory_order_relaxed),
                ResourceManagedShadowWrites.load(std::memory_order_relaxed),
                ResourceManagedShadowReads.load(std::memory_order_relaxed),
                ResourceManagedResetSuccesses.load(std::memory_order_relaxed),
                ResourceManagedResetShadowPreserved.load(std::memory_order_relaxed),
                managedLifetime.deviceGeneration,
                managedLifetime.cpuShadowVersion,
                managedLifetime.mirrorGeneration,
                managedLifetime.mirrorShadowVersion,
                managed_mirror_ready(managedLifetime) ? 1 : 0,
                ManagedTextureShadowRequiredSamples.load(std::memory_order_relaxed),
                ManagedTextureShadowReadySamples.load(std::memory_order_relaxed),
                ManagedTextureShadowPendingSamples.load(std::memory_order_relaxed),
                ManagedTextureUpdateTextureInvalidations.load(
                    std::memory_order_relaxed),
                ManagedTextureUpdateSurfaceInvalidations.load(
                    std::memory_order_relaxed),
                InputLayoutExactSamples.load(std::memory_order_relaxed),
                InputLayoutUnsupportedSamples.load(std::memory_order_relaxed),
                InputLayoutFvfExactSamples.load(std::memory_order_relaxed),
                InputLayoutFvfPendingSamples.load(std::memory_order_relaxed),
                ShaderIntrospectionFailureSamples.load(std::memory_order_relaxed),
                ShaderMixedPairSamples.load(std::memory_order_relaxed),
                ShaderFixedFunctionPendingSamples.load(std::memory_order_relaxed),
                ShaderProgrammablePendingSamples.load(std::memory_order_relaxed),
                FixedFunctionStateCoverageExactSamples.load(
                    std::memory_order_relaxed),
                FixedFunctionStateCoverageFailureSamples.load(
                    std::memory_order_relaxed),
                FixedFunctionTranslationReadySamples.load(
                    std::memory_order_relaxed),
                FixedFunctionTranslationPendingSamples.load(
                    std::memory_order_relaxed),
                FixedFunctionPipelineShaderExactSamples.load(
                    std::memory_order_relaxed),
                FixedFunctionPipelineShaderPendingSamples.load(
                    std::memory_order_relaxed),
                FixedFunctionAlphaTestShaderOwnedSamples.load(
                    std::memory_order_relaxed),
                FixedFunctionShaderPrototypeGeneratedSamples.load(
                    std::memory_order_relaxed),
                FixedFunctionShaderPrototypePendingSamples.load(
                    std::memory_order_relaxed),
                FixedFunctionShaderCompileSucceededSignatures.load(
                    std::memory_order_relaxed),
                FixedFunctionShaderCompileFailedSignatures.load(
                    std::memory_order_relaxed),
                FixedFunctionShaderCompileSkippedSignatureCap.load(
                    std::memory_order_relaxed),
                TextureStageBoundResources.load(std::memory_order_relaxed),
                TextureStageExactResources.load(std::memory_order_relaxed),
                TextureStagePendingResources.load(std::memory_order_relaxed),
                TextureStageManagedShadowRequiredResources.load(
                    std::memory_order_relaxed),
                TextureStageManagedShadowReadyResources.load(
                    std::memory_order_relaxed),
                TextureStageManagedShadowPendingResources.load(
                    std::memory_order_relaxed),
                unsupported[0], unsupported[1], unsupported[2], unsupported[3],
                unsupported[4], unsupported[5], unsupported[6], unsupported[7],
                unsupported[8], unsupported[9], unsupported[10], unsupported[11]);
        }

        void note_unsupported(std::uint32_t mask) noexcept
        {
            for (std::size_t bit = 0; bit < UnsupportedBitCount; ++bit)
            {
                if ((mask & (1u << bit)) != 0)
                    UnsupportedCounts[bit].fetch_add(
                        1, std::memory_order_relaxed);
            }
        }
    }

    void observe_vertex_buffer_lock(
        IDirect3DVertexBuffer9* buffer,
        UINT offset,
        UINT size,
        DWORD flags) noexcept
    {
        if (!buffer || !census_enabled())
            return;
        D3DVERTEXBUFFER_DESC desc{};
        const bool descriptorObserved = SUCCEEDED(buffer->GetDesc(&desc));
        begin_observed_buffer_lock(
            VertexMutationEvidence, buffer, ResourceRole::Vertex,
            desc.Pool, desc.Usage, descriptorObserved, offset, size, flags);
    }

    void observe_vertex_buffer_unlock(
        IDirect3DVertexBuffer9* buffer,
        HRESULT result) noexcept
    {
        if (!buffer || !census_enabled())
            return;
        finish_observed_buffer_unlock(
            VertexMutationEvidence, buffer, result);
    }

    void forget_vertex_buffer_mutation(
        IDirect3DVertexBuffer9* buffer) noexcept
    {
        forget_observed_buffer(VertexMutationEvidence, buffer);
    }

    void observe_index_buffer_lock(
        IDirect3DIndexBuffer9* buffer,
        UINT offset,
        UINT size,
        DWORD flags) noexcept
    {
        if (!buffer || !census_enabled())
            return;
        D3DINDEXBUFFER_DESC desc{};
        const bool descriptorObserved = SUCCEEDED(buffer->GetDesc(&desc));
        begin_observed_buffer_lock(
            IndexMutationEvidence, buffer, ResourceRole::Index,
            desc.Pool, desc.Usage, descriptorObserved, offset, size, flags);
    }

    void observe_index_buffer_unlock(
        IDirect3DIndexBuffer9* buffer,
        HRESULT result) noexcept
    {
        if (!buffer || !census_enabled())
            return;
        finish_observed_buffer_unlock(
            IndexMutationEvidence, buffer, result);
    }

    void forget_index_buffer_mutation(
        IDirect3DIndexBuffer9* buffer) noexcept
    {
        forget_observed_buffer(IndexMutationEvidence, buffer);
    }

    void observe_texture_lock_rect(
        IDirect3DTexture9* texture,
        UINT level,
        DWORD flags) noexcept
    {
        if (!texture || !census_enabled())
            return;
        D3DSURFACE_DESC desc{};
        const bool descriptorObserved =
            SUCCEEDED(texture->GetLevelDesc(level, &desc));
        begin_observed_texture_lock(
            texture, level, descriptorObserved,
            desc.Pool, desc.Usage, flags);
    }

    void observe_texture_unlock_rect(
        IDirect3DTexture9* texture,
        UINT level,
        HRESULT result) noexcept
    {
        if (!texture || !census_enabled())
            return;
        finish_observed_texture_unlock(texture, level, result);
    }

    bool observe_managed_texture_lock_rect(
        IDirect3DTexture9* texture,
        UINT level,
        const D3DLOCKED_RECT& lockedRect,
        const RECT* rect,
        DWORD flags) noexcept
    {
        if (!texture || !census_enabled() || level != 0)
            return false;

        if (!ManagedTextureShadowRegistry.contains(texture))
        {
            D3DSURFACE_DESC desc{};
            const UINT levels = texture->GetLevelCount();
            if (levels != 1 || FAILED(texture->GetLevelDesc(0, &desc)) ||
                !ManagedTextureShadowRegistry.register_texture(
                    texture, desc.Format, desc.Width, desc.Height,
                    levels, desc.Usage, desc.Pool))
                return false;
        }

        return ManagedTextureShadowRegistry.begin_source_lock(
            texture, level, rect, flags, lockedRect);
    }

    bool stage_managed_texture_unlock_rect(
        IDirect3DTexture9* texture,
        UINT level) noexcept
    {
        if (!texture || !census_enabled())
            return false;
        return ManagedTextureShadowRegistry.stage_source_unlock(
            texture, level);
    }

    bool finish_managed_texture_unlock_rect(
        IDirect3DTexture9* texture,
        UINT level,
        HRESULT result) noexcept
    {
        if (!texture || !census_enabled())
            return false;
        return ManagedTextureShadowRegistry.finish_source_unlock(
            texture, level, result);
    }

    void forget_texture_mutation(
        IDirect3DTexture9* texture) noexcept
    {
        if (!texture)
            return;
        {
            std::lock_guard<std::mutex> lock(MutationEvidenceMutex);
            TextureMutationEvidenceRegistry.erase(texture);
        }
        ManagedTextureShadowRegistry.forget_texture(texture);
    }

    void clear_managed_texture_shadows() noexcept
    {
        {
            std::lock_guard<std::mutex> lock(MutationEvidenceMutex);
            TextureMutationEvidenceRegistry.clear();
        }
        ManagedTextureShadowRegistry.clear();
    }

    void observe_update_texture(
        IDirect3DBaseTexture9* source,
        IDirect3DBaseTexture9* destination,
        HRESULT result) noexcept
    {
        if (!source || !destination || !census_enabled())
            return;
        if (SUCCEEDED(result))
        {
            ResourceUpdateTextureSuccesses.fetch_add(
                1, std::memory_order_relaxed);
            if (invalidate_managed_texture_update_target(destination))
                ManagedTextureUpdateTextureInvalidations.fetch_add(
                    1, std::memory_order_relaxed);
        }
        else
        {
            ResourceUpdateTextureFailures.fetch_add(
                1, std::memory_order_relaxed);
        }
    }

    void observe_update_surface(
        IDirect3DSurface9* source,
        IDirect3DSurface9* destination,
        HRESULT result) noexcept
    {
        if (!source || !destination || !census_enabled())
            return;
        if (SUCCEEDED(result))
        {
            ResourceUpdateSurfaceSuccesses.fetch_add(
                1, std::memory_order_relaxed);
            if (invalidate_managed_texture_update_target(destination))
                ManagedTextureUpdateSurfaceInvalidations.fetch_add(
                    1, std::memory_order_relaxed);
        }
        else
        {
            ResourceUpdateSurfaceFailures.fetch_add(
                1, std::memory_order_relaxed);
        }
    }

    void observe_device_reset_generation(HRESULT result) noexcept
    {
        if (FAILED(result) || !census_enabled())
            return;

        ResourceManagedResetSuccesses.fetch_add(
            1, std::memory_order_relaxed);
        ManagedTextureShadowRegistry.observe_device_reset();
        bool shadowPreserved = false;
        {
            std::lock_guard<std::mutex> lock(MutationEvidenceMutex);
            const auto before = ManagedLifetimeEvidence;
            ManagedLifetimeEvidence =
                advance_managed_device_generation(ManagedLifetimeEvidence);
            shadowPreserved =
                before.cpuShadowValid &&
                ManagedLifetimeEvidence.cpuShadowValid &&
                before.cpuShadowVersion ==
                    ManagedLifetimeEvidence.cpuShadowVersion;
        }
        if (shadowPreserved)
            ResourceManagedResetShadowPreserved.fetch_add(
                1, std::memory_order_relaxed);
    }

    void observe_source_draw(
        IDirect3DDevice9* device,
        D3DPRIMITIVETYPE primitive) noexcept
    {
        if (!device || !census_enabled())
            return;

        thread_local std::uint64_t drawOrdinal = 0;
        DrawCallsSeen.fetch_add(1, std::memory_order_relaxed);
        const auto ordinal = ++drawOrdinal;
        const auto sampleStride = census_sample_stride();
        if (sampleStride > 1u)
        {
            const auto sampleKey = mix_sample_ordinal(
                ordinal ^
                (static_cast<std::uint64_t>(GetCurrentThreadId()) << 32));
            if ((sampleKey & (sampleStride - 1u)) != 0u)
                return;
        }

        OutRunVR::DrawState::RenderStateSnapshot source{};
        const bool captured =
            OutRunVRStereo::CaptureTrackedRenderStateSnapshot(device, source);
        const auto translated = translate_pipeline(source);
        const auto topology = translate_primitive(primitive);

        Samples.fetch_add(1, std::memory_order_relaxed);
        std::uint32_t unsupported = translated.unsupported;
        if (!captured)
            unsupported |= PipelineUnsupportedIncompleteSnapshot;
        note_unsupported(unsupported);

        if (!topology.exact)
            UnsupportedTopologySamples.fetch_add(1, std::memory_order_relaxed);

        IDirect3DVertexShader9* vs = nullptr;
        IDirect3DPixelShader9* ps = nullptr;
        const bool vsOk = SUCCEEDED(device->GetVertexShader(&vs));
        const bool psOk = SUCCEEDED(device->GetPixelShader(&ps));
        const bool shaderQueryComplete = vsOk && psOk;
        const bool fixedFunction =
            shaderQueryComplete && vs == nullptr && ps == nullptr;
        const bool programmablePair =
            shaderQueryComplete && vs != nullptr && ps != nullptr;

        if (fixedFunction)
            FixedFunctionSamples.fetch_add(1, std::memory_order_relaxed);
        else if (programmablePair)
            ProgrammableSamples.fetch_add(1, std::memory_order_relaxed);

        auto signature = inspect_source_signature(
            device, fixedFunction, vs, ps, shaderQueryComplete);
        if (vs) vs->Release();
        if (ps) ps->Release();

        signature.alphaTestObservationComplete =
            captured && source.complete;
        signature.alphaTestEnable = source.alphaTestEnable;
        signature.alphaTestRef = source.alphaRef;
        signature.alphaTestFunc = source.alphaFunc;
        signature.fogObservationComplete =
            captured && source.complete;
        signature.fogEnable = source.fogEnable;
        signature.fogColor = source.fogColor;
        signature.fogTableMode = source.fogTableMode;
        signature.fogStartBits = source.fogStartBits;
        signature.fogEndBits = source.fogEndBits;
        signature.fogDensityBits = source.fogDensityBits;
        signature.rangeFogEnable = source.rangeFogEnable;
        signature.fogVertexMode = source.fogVertexMode;

        const bool inputLayoutExact = signature.inputLayoutExact;
        const bool shaderTranslationExact =
            signature.shaderTranslationExact;

        bool resourcesExact = signature.resourceIntrospectionComplete;
        if (!signature.resourceIntrospectionComplete)
            ResourceIntrospectionFailureSamples.fetch_add(
                1, std::memory_order_relaxed);

        bool behaviorDescriptorExact = true;
        bool mutationTelemetryRequired = false;
        bool managedShadowRequired = false;
        const auto observeBehavior = [&](bool present, ResourceRole role,
                                         D3DPOOL pool, DWORD usage) noexcept
        {
            if (!present)
                return true;
            const auto behavior = translate_resource_behavior(role, pool, usage);
            behaviorDescriptorExact =
                behaviorDescriptorExact && behavior.descriptorExact;
            mutationTelemetryRequired =
                mutationTelemetryRequired || behavior.requiresMutationTelemetry;
            managedShadowRequired =
                managedShadowRequired || behavior.requiresCpuShadow;
            return behavior.descriptorExact &&
                   !behavior.requiresMutationTelemetry &&
                   !behavior.requiresCpuShadow;
        };

        observeBehavior(
            signature.vertexBufferPresent, ResourceRole::Vertex,
            signature.vertexPool, signature.vertexUsage);
        observeBehavior(
            signature.indexed, ResourceRole::Index,
            signature.indexPool, signature.indexUsage);
        std::array<bool, 8> textureBehaviorExact{};
        for (std::size_t stageIndex = 0;
             stageIndex < signature.textureStages.size();
             ++stageIndex)
        {
            const auto& texture = signature.textureStages[stageIndex];
            textureBehaviorExact[stageIndex] = observeBehavior(
                texture.present, ResourceRole::Texture,
                texture.pool, texture.usage);
        }
        observeBehavior(
            signature.renderTargetPresent, ResourceRole::Color,
            signature.renderTargetPool, signature.renderTargetUsage);
        observeBehavior(
            signature.depthPresent, ResourceRole::DepthStencil,
            signature.depthPool, signature.depthUsage);

        if (!behaviorDescriptorExact)
            ResourceBehaviorUnsupportedSamples.fetch_add(
                1, std::memory_order_relaxed);
        if (mutationTelemetryRequired)
            ResourceMutationTelemetryRequiredSamples.fetch_add(
                1, std::memory_order_relaxed);
        if (managedShadowRequired)
            ResourceManagedShadowRequiredSamples.fetch_add(
                1, std::memory_order_relaxed);

        const bool managedTextureShadowRequired =
            signature.textureManagedShadowRequiredMask != 0;
        const bool managedTextureShadowReady =
            managedTextureShadowRequired &&
            (signature.textureManagedShadowReadyMask &
             signature.textureManagedShadowRequiredMask) ==
                signature.textureManagedShadowRequiredMask;
        if (managedTextureShadowRequired)
        {
            ManagedTextureShadowRequiredSamples.fetch_add(
                1, std::memory_order_relaxed);
            (managedTextureShadowReady
                ? ManagedTextureShadowReadySamples
                : ManagedTextureShadowPendingSamples).fetch_add(
                    1, std::memory_order_relaxed);
        }

        // R106 exposes managed Texture2D shadow readiness as an independent
        // activation prerequisite. It deliberately does not clear the older
        // mutation-telemetry/resource-lifetime blocker or activate native draw.
        if (!behaviorDescriptorExact || mutationTelemetryRequired ||
            managedShadowRequired)
            resourcesExact = false;

        if (signature.indexed &&
            !translate_resource_format(
                signature.indexFormat, ResourceRole::Index).exact)
        {
            UnsupportedIndexFormatSamples.fetch_add(1, std::memory_order_relaxed);
            resourcesExact = false;
        }
        for (std::size_t stageIndex = 0;
             stageIndex < signature.textureStages.size();
             ++stageIndex)
        {
            const auto& texture = signature.textureStages[stageIndex];
            if (!texture.present)
                continue;

            const bool formatExact = translate_resource_format(
                texture.format, ResourceRole::Texture).exact;
            if (!formatExact)
            {
                UnsupportedTextureFormatSamples.fetch_add(
                    1, std::memory_order_relaxed);
                resourcesExact = false;
            }

            if (texture.observed &&
                textureBehaviorExact[stageIndex] &&
                formatExact)
            {
                signature.textureResourceExactMask |=
                    static_cast<std::uint8_t>(
                        1u << static_cast<unsigned>(stageIndex));
            }
        }

        // A bound texture whose descriptor could not be observed leaves
        // D3DFMT_UNKNOWN behind; both the introspection gate and the bound
        // stage format checks above fail closed.
        if (!translate_resource_format(
                signature.renderTargetFormat, ResourceRole::Color).exact)
        {
            UnsupportedColorFormatSamples.fetch_add(1, std::memory_order_relaxed);
            resourcesExact = false;
        }
        if (signature.depthPresent &&
            !translate_resource_format(
                signature.depthFormat, ResourceRole::DepthStencil).exact)
        {
            UnsupportedDepthFormatSamples.fetch_add(1, std::memory_order_relaxed);
            resourcesExact = false;
        }

        if (signature.fixedFunction)
        {
            const auto readiness = translate_fixed_function_readiness(
                signature.fixedFunctionStages,
                signature.fixedFunctionStateCoverageExact,
                signature.textureResourcePresentMask,
                signature.textureResourceExactMask);
            signature.fixedFunctionTranslationReady = readiness.exact();
            signature.fixedFunctionTranslationUnsupported =
                readiness.unsupported;
            signature.fixedFunctionActiveStages = readiness.activeStages;

            std::array<D3DRESOURCETYPE, 8> textureTypes{};
            for (std::size_t stageIndex = 0;
                 stageIndex < signature.textureStages.size();
                 ++stageIndex)
                textureTypes[stageIndex] =
                    signature.textureStages[stageIndex].type;

            // R120 consumes the R118 fixed-function-only alpha-test handoff
            // strictly as census/readiness evidence. The generic pipeline
            // unsupported mask above remains untouched, shaderTranslationExact
            // stays fail-closed, and no game draw is routed to D3D11.
            const auto pipelineShader =
                translate_fixed_function_pipeline_with_shader_semantics(
                    source,
                    fixedFunction,
                    signature.fixedFunctionStages,
                    signature.fixedFunctionStateCoverageExact,
                    signature.textureResourcePresentMask,
                    signature.textureResourceExactMask,
                    textureTypes);
            signature.fixedFunctionPipelineShaderExact =
                pipelineShader.exact();
            signature.fixedFunctionPipelineShaderUnsupported =
                pipelineShader.renderStates.unsupported;
            signature.fixedFunctionAlphaTestOwnedByPixelShader =
                pipelineShader.alphaTestOwnedByPixelShader;

            const auto& shaderPrototype = pipelineShader.pixelShader;
            signature.fixedFunctionShaderPrototypeGenerated =
                shaderPrototype.generated();
            signature.fixedFunctionShaderPrototypeUnsupported =
                shaderPrototype.unsupported;
            signature.fixedFunctionShaderPrototypeHash =
                shaderPrototype.sourceHash;
            signature.fixedFunctionShaderPrototypeBytes =
                static_cast<UINT>(shaderPrototype.source.size());
        }

        note_signature(signature, primitive);

        if (unsupported == PipelineUnsupportedNone && topology.exact &&
            resourcesExact && inputLayoutExact && shaderTranslationExact)
            ExactSamples.fetch_add(1, std::memory_order_relaxed);

        maybe_log();
    }
}