#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "runtime_census.hpp"
#include "fixed_function_pipeline.hpp"
#include "native_backend.hpp"
#include "resource_translation.hpp"
#include "startup_census.hpp"

#include <array>
#include <atomic>
#include <cstdint>
#include <cstring>
#include <limits>
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
        // R166 binds the census array directly to the enum-owned one-past-last
        // sentinel. R165 keeps dithering on its established bit while future
        // blockers may extend the contiguous range without silent census loss.
        constexpr std::size_t UnsupportedBitCount =
            static_cast<std::size_t>(PipelineUnsupportedBitCount);
        static_assert(
            static_cast<std::uint32_t>(PipelineUnsupportedDither) ==
                (1u << 17),
            "DX11 R165 unsupported dither bit drift");
        static_assert(
            UnsupportedBitCount > 0u &&
                UnsupportedBitCount <= sizeof(std::uint32_t) * 8u,
            "DX11 R166 unsupported census sentinel out of range");
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
        // R211: topology mapping alone is not enough for D3D9 point/line
        // raster equivalence. The dormant dispatch already fails these
        // primitives closed until point-size/sprite and LASTPIXEL semantics
        // are implemented; census exactness must preserve the same boundary.
        std::atomic<std::uint64_t> PointRasterUnsupportedSamples{0};
        std::atomic<std::uint64_t> LineRasterUnsupportedSamples{0};
        std::atomic<std::uint64_t> UnsupportedIndexFormatSamples{0};
        std::atomic<std::uint64_t> UnsupportedTextureFormatSamples{0};
        std::atomic<std::uint64_t> UnsupportedColorFormatSamples{0};
        std::atomic<std::uint64_t> UnsupportedDepthFormatSamples{0};
        std::atomic<std::uint64_t> UnsupportedAuxiliaryRenderTargetSamples{0};
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
        // R215 counts the narrow fixed-function subset whose already-dormant
        // VS/PS source generators and transform contract are all exact.
        std::atomic<std::uint64_t> ShaderTranslationExactSamples{0};
        std::atomic<std::uint64_t> ShaderFixedFunctionPendingSamples{0};
        std::atomic<std::uint64_t> ShaderProgrammablePendingSamples{0};
        // R277 observes the R276->R275 programmable semantic evidence chain
        // without promoting translation or draw authority.
        std::atomic<std::uint64_t> ShaderSemanticPlanExactSamples{0};
        std::atomic<std::uint64_t> ShaderSemanticPlanPendingSamples{0};
        std::atomic<std::uint64_t> ShaderSemanticReceiptExactSamples{0};
        std::atomic<std::uint64_t> ShaderSemanticReceiptPendingSamples{0};
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
        // Exact demand evidence for the still fail-closed D3D9 SRC1 blend
        // factors. Sampled zero is not absence proof; only exhaustive
        // stride=1 coverage may establish that no observed draw requested it.
        std::atomic<std::uint64_t> DualSourceBlendSamples{0};
        std::atomic<std::uint64_t> DualSourceRgbSourceSamples{0};
        std::atomic<std::uint64_t> DualSourceRgbDestSamples{0};
        std::atomic<std::uint64_t> DualSourceAlphaSourceSamples{0};
        std::atomic<std::uint64_t> DualSourceAlphaDestSamples{0};
        std::array<std::atomic<std::uint64_t>, UnsupportedBitCount>
            UnsupportedCounts{};
        std::atomic<ULONGLONG> LastLogMs{0};
        std::mutex SignatureMutex;
        std::unordered_set<std::uint64_t> SignatureHashes;
        // R223: cache only fixed-function signatures whose generated vertex
        // and pixel shader sources both compiled successfully. ExactSamples
        // must not promote source-generation readiness into compiler readiness.
        std::unordered_set<std::uint64_t> FixedFunctionShaderCompileExactHashes;

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

        // R287 owns one dormant native backend for sampled production-census
        // observations. It exists only while DX11 census is enabled, never
        // receives an ID3D11DeviceContext from the D3D9 draw path, and is
        // invalidated on every successful D3D9 Reset.
        std::mutex NativeProgrammableObservationMutex;
        NativeBackend NativeProgrammableObservationBackend;
        IDirect3DDevice9* NativeProgrammableObservationSourceDevice = nullptr;

        NativeProgrammableShaderProductionObservationEvidence
        observe_programmable_production_chain(
            IDirect3DDevice9* sourceDevice,
            const ProgrammableShaderPairCacheIdentity& sourceIdentity,
            const NativeProgrammableShaderTranslationObjectPrerequisiteEvidence&
                objectPrerequisite,
            std::uint64_t objectPrerequisiteSnapshotToken,
            const NativeProgrammableShaderObjectCreationHandoffEvidence&
                creationHandoff,
            std::uint64_t creationHandoffSnapshotToken,
            const NativeProgrammableShaderTargetBytecodeMaterializationEvidence&
                targetBytecodeMaterialization,
            std::uint64_t targetBytecodeMaterializationSnapshotToken,
            const NativeProgrammableShaderSourceMappingHandoff&
                sourceMappingHandoff,
            std::uint64_t sourceMappingHandoffSnapshotToken,
            const NativeProgrammableShaderSemanticTranslationPlanEvidence&
                translationPlan,
            std::uint64_t translationPlanSnapshotToken) noexcept
        {
            NativeProgrammableShaderProductionObservationEvidence out{};
            if (!sourceDevice ||
                !sourceIdentity.exact_identity() ||
                sourceIdentity.translationImplemented ||
                objectPrerequisiteSnapshotToken == 0 ||
                creationHandoffSnapshotToken == 0 ||
                targetBytecodeMaterializationSnapshotToken == 0 ||
                sourceMappingHandoffSnapshotToken == 0 ||
                translationPlanSnapshotToken == 0)
                return out;

            std::lock_guard<std::mutex> lock(
                NativeProgrammableObservationMutex);

            if (NativeProgrammableObservationSourceDevice != sourceDevice ||
                !NativeProgrammableObservationBackend.ready())
            {
                NativeProgrammableObservationBackend.shutdown();
                NativeProgrammableObservationSourceDevice = nullptr;

                const auto source = inspect_source_device(sourceDevice);
                if (!source.native_bootstrap_compatible ||
                    !source.adapter_luid_valid)
                    return out;

                NativeBackendConfig config{};
                config.width = source.width;
                config.height = source.height;
                config.color_format = source.native_format;
                config.adapter_luid_valid = true;
                config.require_adapter_luid = true;
                config.adapter_luid = source.adapter_luid;
                if (!NativeProgrammableObservationBackend.initialize(config))
                    return out;

                NativeProgrammableObservationSourceDevice = sourceDevice;
                spdlog::info(
                    "VR DX11 R287 production observer backend: ready=1 size={}x{} format={} ownerGeneration={}",
                    source.width,
                    source.height,
                    static_cast<int>(source.native_format),
                    NativeProgrammableObservationBackend.
                        programmable_shader_ownership().owner_generation());
            }

            return NativeProgrammableObservationBackend.
                observe_programmable_shader_source_evidence_chain(
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

        // R291 carries the exact R288 admission and R289 semantic review into
        // the sampled production census. The helper is serialized with the
        // R287 observation owner so Reset/device-generation changes cannot
        // race a semantic review. It creates/owns only the R289 input-layout
        // object and never binds IA/VS/PS or authorizes Draw*.
        struct ProgrammableProductionSemanticReviewCensusEvidence
        {
            NativeProgrammableShaderTranslationAdmissionEvidence admission{};
            NativeProgrammableShaderProductionSemanticReviewEvidence review{};
            bool admissionValidated{};
            bool reviewValidated{};
        };

        ProgrammableProductionSemanticReviewCensusEvidence
        review_programmable_production_semantics(
            IDirect3DDevice9* sourceDevice,
            const ProgrammableShaderPairCacheIdentity& sourceIdentity,
            const NativeProgrammableShaderProductionObservationEvidence&
                observation,
            const NativeProgrammableShaderTargetBytecodeMaterializationEvidence&
                targetBytecodeMaterialization,
            const VertexInputLayoutTranslation& layout,
            const ProgrammableShaderInterfaceLinkageEvidence&
                sourceInterfaceLinkage) noexcept
        {
            ProgrammableProductionSemanticReviewCensusEvidence out{};
            if (!sourceDevice ||
                !sourceIdentity.exact_identity() ||
                sourceIdentity.translationImplemented ||
                !observation.reviewReady ||
                observation.reviewSnapshotToken == 0 ||
                !targetBytecodeMaterialization.reviewReady ||
                !layout.exact ||
                !sourceInterfaceLinkage.exact())
                return out;

            std::lock_guard<std::mutex> lock(
                NativeProgrammableObservationMutex);
            if (NativeProgrammableObservationSourceDevice != sourceDevice ||
                !NativeProgrammableObservationBackend.ready())
                return out;

            out.admission =
                seal_programmable_shader_translation_admission(
                    sourceIdentity,
                    observation,
                    observation.reviewSnapshotToken);
            out.admissionValidated =
                validate_programmable_shader_translation_admission_snapshot(
                    sourceIdentity,
                    observation,
                    observation.reviewSnapshotToken,
                    out.admission,
                    out.admission.reviewSnapshotToken);
            if (!out.admissionValidated)
                return out;

            auto& ownership =
                NativeProgrammableObservationBackend.
                    programmable_shader_ownership();
            out.review =
                ownership.materialize_semantic_translation_review_for_observation(
                    sourceIdentity,
                    observation,
                    observation.reviewSnapshotToken,
                    out.admission,
                    out.admission.reviewSnapshotToken,
                    targetBytecodeMaterialization,
                    layout,
                    sourceInterfaceLinkage);
            out.reviewValidated =
                ownership.validate_semantic_translation_review_snapshot(
                    sourceIdentity,
                    observation,
                    observation.reviewSnapshotToken,
                    out.admission,
                    out.admission.reviewSnapshotToken,
                    targetBytecodeMaterialization,
                    layout,
                    sourceInterfaceLinkage,
                    out.review,
                    out.review.reviewSnapshotToken);
            return out;
        }

        // R293 exposes the R292 production activation-prerequisite boundary to
        // sampled census identity without fabricating the exact R258/R262
        // receipts that production does not own yet. Callers must provide both
        // receipts explicitly; missing inputs are recorded and fail closed.
        struct ProgrammableProductionActivationPrerequisiteCensusEvidence
        {
            NativeProgrammableShaderProductionActivationPrerequisiteEvidence
                observation{};
            bool productionSemanticReviewReady{};
            bool sourceRevalidationReceiptPresent{};
            bool resourceBehaviorReceiptPresent{};
            bool observationValidated{};
            bool staticPrerequisitesSatisfied{};
            bool boundaryPreserved{};
            std::uint32_t missingReceiptMask{};
        };

        ProgrammableProductionActivationPrerequisiteCensusEvidence
        review_programmable_production_activation_prerequisites(
            const NativeProgrammableShaderProductionSemanticReviewEvidence&
                productionSemanticReview,
            const NativeProgrammableShaderDormantSourceRevalidationReadiness*
                sourceRevalidation,
            const NativeProgrammableShaderOutputResourceBehaviorReadiness*
                resourceBehavior) noexcept
        {
            ProgrammableProductionActivationPrerequisiteCensusEvidence out{};
            constexpr std::uint32_t kSourceRevalidationReceiptMissing =
                1u << 0;
            constexpr std::uint32_t kResourceBehaviorReceiptMissing =
                1u << 1;

            out.productionSemanticReviewReady =
                productionSemanticReview.reviewReady &&
                productionSemanticReview.reviewSnapshotToken != 0 &&
                productionSemanticReview.diagnosticOnly &&
                productionSemanticReview.boundaryPreserved &&
                !productionSemanticReview.objectBindingAuthorized &&
                !productionSemanticReview.nativeDrawPathActivationAllowed &&
                !productionSemanticReview.drawDispatchAuthorized;
            out.sourceRevalidationReceiptPresent =
                sourceRevalidation != nullptr;
            out.resourceBehaviorReceiptPresent =
                resourceBehavior != nullptr;

            if (!out.sourceRevalidationReceiptPresent)
                out.missingReceiptMask |=
                    kSourceRevalidationReceiptMissing;
            if (!out.resourceBehaviorReceiptPresent)
                out.missingReceiptMask |=
                    kResourceBehaviorReceiptMissing;

            // Missing production receipts are a valid diagnostic state but
            // never an R292 success or activation signal.
            out.boundaryPreserved =
                out.productionSemanticReviewReady &&
                out.missingReceiptMask != 0;
            if (!out.productionSemanticReviewReady ||
                out.missingReceiptMask != 0)
                return out;

            out.observation =
                observe_programmable_shader_production_activation_prerequisites(
                    productionSemanticReview,
                    productionSemanticReview.reviewSnapshotToken,
                    *sourceRevalidation,
                    sourceRevalidation->snapshotToken,
                    *resourceBehavior,
                    resourceBehavior->reviewSnapshotToken);
            out.observationValidated =
                validate_programmable_shader_production_activation_prerequisite_snapshot(
                    productionSemanticReview,
                    productionSemanticReview.reviewSnapshotToken,
                    *sourceRevalidation,
                    sourceRevalidation->snapshotToken,
                    *resourceBehavior,
                    resourceBehavior->reviewSnapshotToken,
                    out.observation,
                    out.observation.reviewSnapshotToken);
            out.staticPrerequisitesSatisfied =
                out.observationValidated &&
                out.observation.staticPrerequisitesSatisfied &&
                out.observation.missingPrerequisiteMask == 0;
            out.boundaryPreserved =
                out.observationValidated &&
                out.staticPrerequisitesSatisfied &&
                out.observation.boundaryPreserved &&
                out.observation.prerequisites.activationSnapshotToken == 0 &&
                !out.observation.objectBindingAuthorized &&
                !out.observation.nativeDrawPathActivationAllowed &&
                !out.observation.drawDispatchAuthorized;
            return out;
        }

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
            bool sourceEvidenceExact{};
            bool instructionDecodeExact{};
            bool registerSemanticsExact{};
            UINT byteSize{};
            DWORD versionToken{};
            std::uint64_t hash{};
            UINT decodedInstructionCount{};
            UINT decodedOperandTokenCount{};
            std::uint64_t decodedStreamHash{};
            std::uint64_t decoderRevisionHash{};
            std::uint64_t semanticContractHash{};
            UINT registerSemanticInstructionCount{};
            UINT destinationOperandCount{};
            UINT sourceOperandCount{};
            UINT relativeAddressOperandCount{};
            UINT floatConstantReferenceCount{};
            UINT intConstantReferenceCount{};
            UINT boolConstantReferenceCount{};
            UINT samplerReferenceCount{};
            UINT constantDefinitionCount{};
            std::uint64_t registerSemanticsHash{};
            std::uint64_t registerDecoderRevisionHash{};
            std::uint64_t registerSemanticContractHash{};
            bool interfaceSemanticsExact{};
            UINT interfaceDeclarationInstructionCount{};
            UINT interfaceSemanticDeclarationCount{};
            UINT interfaceInputSemanticCount{};
            UINT interfaceOutputSemanticCount{};
            UINT interfaceSamplerDeclarationCount{};
            std::uint64_t interfaceSemanticsHash{};
            std::uint64_t interfaceDecoderRevisionHash{};
            std::uint64_t interfaceSemanticContractHash{};
        };

        struct SourceSignature
        {
            // R294 seals the exact D3D9 draw-call parameters needed by a
            // future production R258 source-revalidation producer. This does
            // not imply that native buffer mirrors or R258 itself exist yet.
            SourceDrawObservation sourceDraw{};
            bool sourceDrawIdentityExact{};
            bool sourceDrawNativeBufferEligible{};
            std::uint64_t sourceDrawIdentitySnapshotToken{};
            DWORD fvf{};
            std::uint64_t vertexDeclHash{};
            UINT vertexDeclElements{};
            std::array<D3DVERTEXELEMENT9, MAXD3DDECLLENGTH + 1> vertexDeclElementsData{};
            UINT streamOffset{};
            UINT stride{};
            // R175: D3D9 stream frequency controls indexed/instanced vertex
            // reuse. The dormant DX11 input layout is strictly per-vertex, so
            // only the D3D9 default frequency of one is currently exact.
            UINT stream0Frequency = 1u;
            DWORD vertexUsage{};
            D3DPOOL vertexPool = D3DPOOL_FORCE_DWORD;
            DWORD indexUsage{};
            D3DPOOL indexPool = D3DPOOL_FORCE_DWORD;
            D3DFORMAT indexFormat = D3DFMT_UNKNOWN;
            DWORD renderTargetUsage{};
            D3DPOOL renderTargetPool = D3DPOOL_FORCE_DWORD;
            D3DFORMAT renderTargetFormat = D3DFMT_UNKNOWN;
            // R177: the dormant surface mirror is exact only for non-MSAA
            // D3D9 surfaces. Preserve source sample type/quality in census
            // identity so an MSAA target cannot alias a single-sample target.
            D3DMULTISAMPLE_TYPE renderTargetMultiSampleType =
                D3DMULTISAMPLE_NONE;
            DWORD renderTargetMultiSampleQuality = 0;
            // R174: RT0 alone is insufficient source-output provenance.
            // Preserve D3D9 auxiliary MRT slots 1..3 in sampled identity so
            // multi-target draws cannot alias the one-color-target path.
            bool auxiliaryRenderTargetObservationComplete = true;
            std::uint8_t auxiliaryRenderTargetMask{};
            DWORD depthUsage{};
            D3DPOOL depthPool = D3DPOOL_FORCE_DWORD;
            D3DFORMAT depthFormat = D3DFMT_UNKNOWN;
            D3DMULTISAMPLE_TYPE depthMultiSampleType =
                D3DMULTISAMPLE_NONE;
            DWORD depthMultiSampleQuality = 0;
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
            // R269 seals pair-level R268 linkage into production census
            // identity without widening programmable translation readiness.
            bool shaderInterfaceLinkExact{};
            UINT shaderInterfaceMatchedSemanticCount{};
            std::uint64_t shaderInterfaceLinkHash{};
            std::uint64_t shaderInterfaceLinkerRevisionHash{};
            std::uint64_t shaderInterfaceSemanticContractHash{};
            // R271 binds both source-attested R266 stage semantics plus R268
            // linkage to the exact R239 programmable pair identity.
            bool shaderSourceSemanticPairExact{};
            std::uint64_t shaderSourceSemanticPairCacheKey{};
            std::uint64_t shaderSourceSemanticPairHash{};
            std::uint64_t shaderSourceSemanticReceiptRevisionHash{};
            std::uint64_t shaderSourceSemanticContractHash{};
            std::uint64_t shaderSourceVertexRegisterHash{};
            std::uint64_t shaderSourcePixelRegisterHash{};
            // R272 materializes a deterministic logical register/sampler map
            // from the exact R271/R266 source receipts without activating it.
            bool shaderRegisterMappingPlanExact{};
            UINT shaderConstantRegisterMappingCount{};
            UINT shaderSamplerMappingCount{};
            std::uint64_t shaderConstantRegisterMappingHash{};
            std::uint64_t shaderSamplerMappingHash{};
            std::uint64_t shaderRegisterMappingPlanRevisionHash{};
            std::uint64_t shaderRegisterMappingSemanticContractHash{};
            // R273 binds the R272 mapping plan to the exact R239/R271 source
            // identity as a production diagnostic handoff for later R263 use.
            bool shaderSourceMappingHandoffExact{};
            std::uint64_t shaderSourceMappingHandoffSnapshotToken{};
            // R277 seals source-derived R276 plan identity into the sampled
            // programmable signature and observes the R275 receipt boundary.
            // R279 separately seals the exact R240/R241/R242 ownership/lifetime
            // prerequisites without creating or binding programmable objects.
            bool shaderSemanticTranslationPlanExact{};
            std::uint64_t shaderSemanticTranslationPlanSnapshotToken{};
            std::uint64_t shaderTranslatedVertexSemanticHash{};
            std::uint64_t shaderTranslatedPixelSemanticHash{};
            std::uint64_t shaderTranslatorRevisionHash{};
            std::uint64_t shaderTranslationSemanticContractHash{};
            bool shaderTranslationObjectPrerequisiteExact{};
            bool shaderTranslationObjectCacheOwnerGenerationRequired{};
            bool shaderTranslationObjectSlotGenerationRequired{};
            bool shaderTranslationObjectReceiptGenerationRequired{};
            bool shaderTranslationObjectSameDevicePairRequired{};
            bool shaderTranslationObjectCacheSnapshotRequired{};
            bool shaderTranslationObjectSlotSnapshotRequired{};
            std::uint64_t shaderTranslationObjectPrerequisiteSnapshotToken{};
            bool shaderObjectCreationHandoffExact{};
            bool shaderObjectCreationHandoffVertexSourceExact{};
            bool shaderObjectCreationHandoffPixelSourceExact{};
            bool shaderObjectCreationHandoffOwnershipPrerequisiteMatches{};
            bool shaderObjectCreationAuthorized{};
            std::uint64_t shaderObjectCreationHandoffSnapshotToken{};
            bool shaderTranslatedArtifactReceiptExact{};
            bool shaderTranslatedArtifactReceiptTargetBytecodeRequired{};
            bool shaderTranslatedArtifactReceiptMaterialized{};
            bool shaderTranslatedArtifactCreationAuthorized{};
            std::uint64_t shaderTranslatedVertexArtifactIdentity{};
            std::uint64_t shaderTranslatedPixelArtifactIdentity{};
            std::uint64_t shaderTranslatedArtifactReceiptSnapshotToken{};
            bool shaderTargetMaterializationContractExact{};
            bool shaderTargetBytecodeMaterializationRequired{};
            bool shaderTargetBytecodeMaterialized{};
            bool shaderTargetCompilationAuthorized{};
            bool shaderTargetObjectCreationAuthorized{};
            std::uint64_t shaderTargetVertexCompileContractIdentity{};
            std::uint64_t shaderTargetPixelCompileContractIdentity{};
            std::uint64_t shaderTargetEntryPointHash{};
            std::uint64_t shaderTargetVertexProfileHash{};
            std::uint64_t shaderTargetPixelProfileHash{};
            std::uint32_t shaderTargetCompileFlags{};
            std::uint64_t shaderTargetMaterializationContractSnapshotToken{};
            // R283: bounded SM3 DCL+MOV translated source/DXBC evidence.
            // These fields are diagnostic only; object creation and Draw*
            // activation remain fail-closed.
            bool shaderTargetBytecodeMaterializationExact{};
            bool shaderTargetVertexSubsetSupported{};
            bool shaderTargetPixelSubsetSupported{};
            bool shaderTargetVertexCompiled{};
            bool shaderTargetPixelCompiled{};
            bool shaderTargetR283BytecodeMaterialized{};
            bool shaderTargetR283ObjectCreationAuthorized{};
            UINT shaderTargetVertexTranslatedSourceBytes{};
            UINT shaderTargetPixelTranslatedSourceBytes{};
            std::uint64_t shaderTargetVertexTranslatedSourceHash{};
            std::uint64_t shaderTargetPixelTranslatedSourceHash{};
            UINT shaderTargetVertexBytecodeBytes{};
            UINT shaderTargetPixelBytecodeBytes{};
            std::uint64_t shaderTargetVertexBytecodeHash{};
            std::uint64_t shaderTargetPixelBytecodeHash{};
            std::uint64_t shaderTargetVertexMaterializedArtifactIdentity{};
            std::uint64_t shaderTargetPixelMaterializedArtifactIdentity{};
            std::uint64_t shaderTargetBytecodeMaterializationSnapshotToken{};
            // R287 carries the exact sampled production chain through R286
            // into the persistent native-device R285 owner. This remains
            // diagnostic-only and cannot authorize binding or Draw*.
            bool shaderProductionObservationExact{};
            bool shaderProductionObservationMaterializationReused{};
            bool shaderProductionObservationObjectReady{};
            bool shaderProductionObservationBoundaryPreserved{};
            std::uint64_t shaderProductionObservationOwnerGeneration{};
            std::uint64_t shaderProductionSemanticHandoffSnapshotToken{};
            std::uint64_t shaderProductionObservationSnapshotToken{};
            // R291 observes the exact production R288/R289 admission/review
            // chain in census identity without promoting programmable draws.
            bool shaderTranslationAdmissionExact{};
            bool shaderTranslationAdmissionBoundaryPreserved{};
            std::uint64_t shaderTranslationAdmissionSnapshotToken{};
            bool shaderProductionSemanticReviewExact{};
            bool shaderProductionSemanticReviewInputLayoutReady{};
            bool shaderProductionSemanticReviewInputLayoutReused{};
            bool shaderProductionSemanticReviewTranslationReady{};
            bool shaderProductionSemanticReviewBoundaryPreserved{};
            std::uint64_t shaderProductionSemanticReviewInputLayoutSnapshotToken{};
            std::uint64_t shaderProductionSemanticReviewTranslationSnapshotToken{};
            std::uint64_t shaderProductionSemanticReviewSnapshotToken{};
            // R295 joins the exact R294 source draw identity to an optional
            // production R258 receipt. Current census does not own that receipt,
            // so the join remains explicit, diagnostic, and fail closed.
            bool shaderProductionSourceDrawIdentityExact{};
            bool shaderProductionSourceNativeBufferEligible{};
            bool shaderProductionSourceReceiptPresent{};
            bool shaderProductionSourceReceiptContractReady{};
            bool shaderProductionSourceKindMatches{};
            bool shaderProductionSourceStartMatches{};
            bool shaderProductionSourceElementCountDerivable{};
            bool shaderProductionSourceElementCountMatches{};
            UINT shaderProductionSourceElementCount{};
            bool shaderProductionSourceIndexFormatKnown{};
            bool shaderProductionSourceIndexFormatMatches{};
            bool shaderProductionSourceIndexOffsetMatches{};
            DXGI_FORMAT shaderProductionSourceIndexFormat = DXGI_FORMAT_UNKNOWN;
            bool shaderProductionSourceBaseVertexMatches{};
            bool shaderProductionSourceMinVertexMatches{};
            bool shaderProductionSourceNumVerticesMatches{};
            bool shaderProductionSourceRangeMatches{};
            bool shaderProductionSourceCacheKeyMatches{};
            bool shaderProductionSourceJoinExact{};
            bool shaderProductionSourceBoundaryPreserved{};
            std::uint32_t shaderProductionSourceMissingEvidenceMask{};
            std::uint64_t shaderProductionSourceReceiptSnapshotToken{};
            std::uint64_t shaderProductionSourceJoinSnapshotToken{};
            // R293 makes the production R292 blocker explicit in census
            // identity. Current production has no exact R258/R262 receipts, so
            // these samples remain prerequisite-pending and fail closed.
            bool shaderProductionActivationSourceReceiptPresent{};
            bool shaderProductionActivationResourceReceiptPresent{};
            bool shaderProductionActivationPrerequisiteExact{};
            bool shaderProductionActivationStaticPrerequisitesSatisfied{};
            bool shaderProductionActivationBoundaryPreserved{};
            std::uint32_t shaderProductionActivationMissingReceiptMask{};
            std::uint64_t shaderProductionActivationPrerequisiteSnapshotToken{};
            bool shaderTranslatedSemanticReceiptExact{};
            bool shaderTranslatedSemanticReceiptObjectReady{};
            std::uint64_t shaderTranslatedSemanticReceiptSnapshotToken{};
            // R317: capture the actual R275 producer-owned scalar tuple at
            // observation time; never reconstruct it from later mutable state.
            NativeProgrammableShaderTranslatedSemanticReceipt
                shaderTranslatedSemanticReceiptEvidence{};
            bool shaderTranslationExact{};
            // R220: keep the shader activation-readiness boundary distinct
            // from translation implementation state. Programmable D3D9 shader
            // pairs remain fail-closed until a dedicated translator is proven.
            bool shaderReadinessExact{};
            bool fixedFunctionStateCoverageExact{};
            // R162: preserve interpolation provenance in the sampled draw
            // identity so non-Gouraud state cannot alias an exact signature.
            bool shadeModeObservationComplete{};
            DWORD shadeMode = D3DSHADE_GOURAUD;
            // R163 seals matrix-blend provenance into draw identity so an
            // unsupported weighted/indexed draw cannot alias the default.
            bool vertexBlendObservationComplete{};
            DWORD vertexBlend = D3DVBF_DISABLE;
            DWORD indexedVertexBlendEnable = FALSE;
            // R164: preserve the raw D3D9 raster depth-bias states in the
            // census identity. Native readiness remains fail-closed for any
            // non-zero value, but distinct bias patterns must not alias.
            bool depthBiasObservationComplete{};
            DWORD depthBiasBits{};
            DWORD slopeScaleDepthBiasBits{};
            // R167: D3D9 dithering is fail-closed in the native pipeline, but
            // it must also participate in sampled draw identity so enabled
            // dithering cannot alias the exact disabled-default signature.
            bool ditherObservationComplete{};
            DWORD ditherEnable = FALSE;
            // R172: R171 translates D3DRS_MULTISAMPLEANTIALIAS into the
            // D3D11 rasterizer descriptor. Preserve the observed value in
            // census identity so per-draw raster variants cannot alias.
            bool multisampleRasterObservationComplete{};
            DWORD multiSampleAntialias = TRUE;
            // R205: R168 captures D3D9 LASTPIXEL and line-AA provenance, while
            // direct line dispatch remains fail-closed. Seal both values into
            // sampled identity so distinct line-raster states cannot alias.
            bool lineRasterObservationComplete{};
            DWORD lastPixel = TRUE;
            DWORD antialiasedLineEnable = FALSE;
            // R179: R124 already carries the dynamic output state consumed by
            // native DX11 binding. Seal it into census identity so draws that
            // differ only by blend factor, sample mask, viewport or scissor
            // cannot alias the same sampled signature.
            bool outputStateObservationComplete{};
            DWORD outputBlendFactor = 0xFFFFFFFFu;
            DWORD outputMultiSampleMask = 0xFFFFFFFFu;
            D3DVIEWPORT9 outputViewport{};
            RECT outputScissorRect{};
            DWORD outputScissorTestEnable = FALSE;
            // R191: D3DRS_TEXTUREFACTOR participates in fixed-function
            // D3DTA_TFACTOR/BLENDFACTORALPHA semantics. Keep observation
            // completeness and raw ARGB value in draw identity before those
            // shader operations are promoted.
            bool textureFactorObservationComplete{};
            DWORD textureFactor = 0xFFFFFFFFu;
            // R169: D3D9 POINTLIST size/sprite/scale state affects raster and
            // texture-coordinate semantics. Preserve the complete family in
            // census identity while native direct points remain fail-closed.
            bool pointRasterObservationComplete{};
            DWORD pointSizeBits = 0x3F800000u;
            DWORD pointSizeMinBits = 0x3F800000u;
            DWORD pointSizeMaxBits = 0x42800000u;
            DWORD pointSpriteEnable = FALSE;
            DWORD pointScaleEnable = FALSE;
            DWORD pointScaleABits = 0x3F800000u;
            DWORD pointScaleBBits = 0u;
            DWORD pointScaleCBits = 0u;
            // R170: preserve all eight D3DRS_WRAP stage masks in draw identity.
            bool textureCoordinateWrapObservationComplete{};
            std::array<DWORD, 8> textureCoordinateWrap{};
            // R212: RT0 COLORWRITEENABLE is translated exactly into the D3D11
            // blend descriptor. Preserve it in sampled draw identity so draws
            // that differ only by destination channel writes cannot alias.
            bool rt0ColorWriteObservationComplete{};
            DWORD colorWriteEnable =
                D3DCOLORWRITEENABLE_RED |
                D3DCOLORWRITEENABLE_GREEN |
                D3DCOLORWRITEENABLE_BLUE |
                D3DCOLORWRITEENABLE_ALPHA;
            bool mrtColorWriteObservationComplete{};
            std::array<DWORD, 3> additionalColorWriteEnable{
                0x0000000Fu, 0x0000000Fu, 0x0000000Fu
            };
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
            // R223 retains the already-generated per-signature vertex source
            // only long enough for the bounded unique-signature compiler probe.
            std::string fixedFunctionVertexShaderPrototypeSource;
            bool fixedFunctionTransformExact{};
            std::uint32_t fixedFunctionTransformUnsupported{};
            std::uint64_t fixedFunctionTransformHash{};
            bool vertexBufferPresent{};
            bool renderTargetPresent{};
            bool indexed{};
            bool textured{};
            bool depthPresent{};
            bool resourceIntrospectionComplete{true};
            // R219: keep F18 resource-behavior readiness as explicit sampled
            // identity and final ExactSamples state instead of hiding it only
            // inside the aggregate resourcesExact local.
            bool resourceBehaviorDescriptorExact{};
            bool resourceMutationTelemetryRequired{};
            bool resourceManagedShadowRequired{};
            bool resourceBehaviorExact{};
            bool fixedFunction{};
        };

        bool is_src1_blend_factor(DWORD value) noexcept
        {
            const auto blend = static_cast<D3DBLEND>(value);
            return blend == D3DBLEND_SRCCOLOR2 ||
                   blend == D3DBLEND_INVSRCCOLOR2;
        }

        std::uint64_t hash_mix(std::uint64_t hash, std::uint64_t value) noexcept
        {
            hash ^= value + 0x9e3779b97f4a7c15ull + (hash << 6) + (hash >> 2);
            return hash;
        }

        bool source_draw_identity_exact(
            const SourceDrawObservation& draw) noexcept
        {
            if (draw.primitive == D3DPT_FORCE_DWORD)
                return false;
            switch (draw.kind)
            {
            case SourceDrawKind::NonIndexed:
                return draw.baseVertexIndex == 0 &&
                    draw.minVertexIndex == 0 && draw.numVertices == 0 &&
                    draw.startIndex == 0 && draw.indexFormat == D3DFMT_UNKNOWN &&
                    draw.vertexStride == 0;
            case SourceDrawKind::Indexed:
                return draw.startVertex == 0 &&
                    (draw.indexFormat == D3DFMT_INDEX16 ||
                     draw.indexFormat == D3DFMT_INDEX32) &&
                    draw.vertexStride == 0;
            case SourceDrawKind::NonIndexedUserMemory:
                return draw.startVertex == 0 && draw.baseVertexIndex == 0 &&
                    draw.minVertexIndex == 0 && draw.numVertices == 0 &&
                    draw.startIndex == 0 && draw.indexFormat == D3DFMT_UNKNOWN &&
                    draw.vertexStride != 0;
            case SourceDrawKind::IndexedUserMemory:
                return draw.startVertex == 0 && draw.baseVertexIndex == 0 &&
                    draw.startIndex == 0 &&
                    (draw.indexFormat == D3DFMT_INDEX16 ||
                     draw.indexFormat == D3DFMT_INDEX32) &&
                    draw.vertexStride != 0;
            case SourceDrawKind::Unknown:
            default:
                return false;
            }
        }

        std::uint64_t source_draw_identity_snapshot_token(
            const SourceDrawObservation& draw) noexcept
        {
            if (!source_draw_identity_exact(draw))
                return 0;
            std::uint64_t token = 0xcbf29ce484222325ull;
            token = hash_mix(token, static_cast<std::uint32_t>(draw.kind));
            token = hash_mix(token, static_cast<std::uint32_t>(draw.primitive));
            token = hash_mix(token, draw.primitiveCount);
            token = hash_mix(token, draw.startVertex);
            token = hash_mix(
                token,
                static_cast<std::uint64_t>(
                    static_cast<std::int64_t>(draw.baseVertexIndex)));
            token = hash_mix(token, draw.minVertexIndex);
            token = hash_mix(token, draw.numVertices);
            token = hash_mix(token, draw.startIndex);
            token = hash_mix(token, static_cast<std::uint32_t>(draw.indexFormat));
            token = hash_mix(token, draw.vertexStride);
            token = hash_mix(token, 0x294u);
            return token == 0 ? 1 : token;
        }

        // R297 extends the R296 production handoff by retaining the indexed
        // base/min/count source-vertex range through R255-R258 and requiring
        // the future production receipt to match the exact R294 range. It does
        // not manufacture R258: an absent receipt is recorded as a bounded
        // fail-closed state, while a supplied receipt must match source kind,
        // start location, element count, cache identity, and the dormant R258
        // boundary.
        struct ProgrammableProductionSourceRevalidationCensusEvidence
        {
            bool sourceDrawIdentityExact{};
            bool sourceDrawNativeBufferEligible{};
            bool sourceRevalidationReceiptPresent{};
            bool sourceRevalidationReceiptContractReady{};
            bool sourceKindMatches{};
            bool sourceStartMatches{};
            bool sourceElementCountDerivable{};
            bool sourceElementCountMatches{};
            UINT sourceElementCount{};
            bool sourceIndexFormatKnown{};
            bool sourceIndexFormatMatches{};
            bool sourceIndexOffsetMatches{};
            DXGI_FORMAT sourceIndexFormat = DXGI_FORMAT_UNKNOWN;
            bool sourceBaseVertexMatches{};
            bool sourceMinVertexMatches{};
            bool sourceNumVerticesMatches{};
            bool sourceRangeMatches{};
            bool cacheIdentityMatches{};
            bool joinValidated{};
            bool boundaryPreserved{};
            std::uint32_t missingEvidenceMask{};
            std::uint64_t sourceDrawIdentitySnapshotToken{};
            std::uint64_t sourceRevalidationSnapshotToken{};
            std::uint64_t reviewSnapshotToken{};
        };

        bool source_draw_element_count(
            D3DPRIMITIVETYPE primitive,
            UINT primitiveCount,
            UINT& elementCount) noexcept
        {
            elementCount = 0;
            const UINT maxValue = (std::numeric_limits<UINT>::max)();
            switch (primitive)
            {
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
                // The direct R251/R255 source receipts reject triangle fans;
                // generated-index fan readiness remains a separate lineage.
                return false;
            }
        }

        ProgrammableProductionSourceRevalidationCensusEvidence
        review_programmable_production_source_revalidation(
            const SourceDrawObservation& sourceDraw,
            std::uint64_t sourceDrawIdentitySnapshotToken,
            std::uint64_t expectedCacheKey,
            const NativeProgrammableShaderDormantSourceRevalidationReadiness*
                sourceRevalidation) noexcept
        {
            ProgrammableProductionSourceRevalidationCensusEvidence out{};
            constexpr std::uint32_t kSourceDrawIdentityMissing = 1u << 0;
            constexpr std::uint32_t kNativeBufferEligibilityMissing = 1u << 1;
            constexpr std::uint32_t kSourceRevalidationReceiptMissing = 1u << 2;
            constexpr std::uint32_t kCacheIdentityMissing = 1u << 3;
            constexpr std::uint32_t kSourceElementCountMissing = 1u << 4;
            constexpr std::uint32_t kSourceIndexFormatMissing = 1u << 5;

            out.sourceDrawIdentitySnapshotToken =
                sourceDrawIdentitySnapshotToken;
            out.sourceDrawIdentityExact =
                sourceDrawIdentitySnapshotToken != 0 &&
                source_draw_identity_exact(sourceDraw) &&
                source_draw_identity_snapshot_token(sourceDraw) ==
                    sourceDrawIdentitySnapshotToken;
            out.sourceDrawNativeBufferEligible =
                out.sourceDrawIdentityExact &&
                sourceDraw.native_buffer_eligible();
            out.sourceElementCountDerivable =
                out.sourceDrawNativeBufferEligible &&
                source_draw_element_count(
                    sourceDraw.primitive,
                    sourceDraw.primitiveCount,
                    out.sourceElementCount);
            const bool sourceIndexed =
                sourceDraw.kind == SourceDrawKind::Indexed;
            out.sourceIndexFormat =
                !sourceIndexed
                    ? DXGI_FORMAT_UNKNOWN
                    : sourceDraw.indexFormat == D3DFMT_INDEX16
                        ? DXGI_FORMAT_R16_UINT
                        : sourceDraw.indexFormat == D3DFMT_INDEX32
                            ? DXGI_FORMAT_R32_UINT
                            : DXGI_FORMAT_UNKNOWN;
            out.sourceIndexFormatKnown =
                !sourceIndexed ||
                out.sourceIndexFormat != DXGI_FORMAT_UNKNOWN;
            out.sourceRevalidationReceiptPresent =
                sourceRevalidation != nullptr;

            if (!out.sourceDrawIdentityExact)
                out.missingEvidenceMask |= kSourceDrawIdentityMissing;
            if (!out.sourceDrawNativeBufferEligible)
                out.missingEvidenceMask |= kNativeBufferEligibilityMissing;
            if (!out.sourceRevalidationReceiptPresent)
                out.missingEvidenceMask |= kSourceRevalidationReceiptMissing;
            if (expectedCacheKey == 0)
                out.missingEvidenceMask |= kCacheIdentityMissing;
            if (!out.sourceElementCountDerivable)
                out.missingEvidenceMask |= kSourceElementCountMissing;
            if (!out.sourceIndexFormatKnown)
                out.missingEvidenceMask |= kSourceIndexFormatMissing;

            if (sourceRevalidation != nullptr)
            {
                out.sourceRevalidationSnapshotToken =
                    sourceRevalidation->snapshotToken;
                out.sourceRevalidationReceiptContractReady =
                    sourceRevalidation->ready &&
                    sourceRevalidation->boundaryPreserved &&
                    sourceRevalidation->snapshotToken != 0;
                const auto expectedKind = sourceIndexed
                    ? NativeProgrammableShaderDrawCandidateKind::Indexed
                    : NativeProgrammableShaderDrawCandidateKind::NonIndexed;
                out.sourceKindMatches =
                    out.sourceDrawNativeBufferEligible &&
                    sourceRevalidation->kind == expectedKind &&
                    sourceRevalidation->indexed == sourceIndexed;
                out.sourceStartMatches =
                    out.sourceDrawNativeBufferEligible &&
                    sourceRevalidation->startLocation ==
                        (sourceIndexed
                            ? sourceDraw.startIndex
                            : sourceDraw.startVertex);
                out.sourceElementCountMatches =
                    out.sourceElementCountDerivable &&
                    sourceRevalidation->elementCount == out.sourceElementCount;
                out.sourceIndexFormatMatches =
                    out.sourceIndexFormatKnown &&
                    sourceRevalidation->indexFormat == out.sourceIndexFormat;
                out.sourceIndexOffsetMatches =
                    out.sourceIndexFormatKnown &&
                    sourceRevalidation->indexOffset == 0u;
                out.sourceBaseVertexMatches =
                    !sourceIndexed ||
                    sourceRevalidation->baseVertexIndex ==
                        sourceDraw.baseVertexIndex;
                out.sourceMinVertexMatches =
                    !sourceIndexed ||
                    sourceRevalidation->minVertexIndex ==
                        sourceDraw.minVertexIndex;
                out.sourceNumVerticesMatches =
                    !sourceIndexed ||
                    sourceRevalidation->numVertices ==
                        sourceDraw.numVertices;
                out.sourceRangeMatches =
                    out.sourceBaseVertexMatches &&
                    out.sourceMinVertexMatches &&
                    out.sourceNumVerticesMatches;
                out.cacheIdentityMatches =
                    expectedCacheKey != 0 &&
                    sourceRevalidation->cacheKey == expectedCacheKey;
                out.joinValidated =
                    out.missingEvidenceMask == 0 &&
                    out.sourceRevalidationReceiptContractReady &&
                    out.sourceKindMatches &&
                    out.sourceStartMatches &&
                    out.sourceElementCountMatches &&
                    out.sourceIndexFormatMatches &&
                    out.sourceIndexOffsetMatches &&
                    out.sourceRangeMatches &&
                    out.cacheIdentityMatches;
                out.boundaryPreserved =
                    out.joinValidated &&
                    sourceRevalidation->boundaryPreserved;
            }
            else
            {
                // Current production state: the exact R294 source identity is
                // present, but no R258 producer owns the D3D11 context/buffer
                // evidence yet. Preserve this as a non-promoting boundary.
                out.boundaryPreserved =
                    out.sourceDrawIdentityExact &&
                    out.sourceDrawNativeBufferEligible &&
                    out.sourceElementCountDerivable &&
                    out.sourceIndexFormatKnown &&
                    expectedCacheKey != 0;
            }

            if (out.sourceDrawIdentityExact && expectedCacheKey != 0)
            {
                std::uint64_t token = 0xcbf29ce484222325ull;
                token = hash_mix(token, out.sourceDrawIdentitySnapshotToken);
                token = hash_mix(token, expectedCacheKey);
                token = hash_mix(
                    token, out.sourceRevalidationReceiptPresent ? 1u : 0u);
                token = hash_mix(
                    token, out.sourceRevalidationReceiptContractReady ? 1u : 0u);
                token = hash_mix(token, out.sourceKindMatches ? 1u : 0u);
                token = hash_mix(token, out.sourceStartMatches ? 1u : 0u);
                token = hash_mix(token, out.sourceElementCountDerivable ? 1u : 0u);
                token = hash_mix(token, out.sourceElementCountMatches ? 1u : 0u);
                token = hash_mix(token, out.sourceElementCount);
                token = hash_mix(token, out.sourceIndexFormatKnown ? 1u : 0u);
                token = hash_mix(token, out.sourceIndexFormatMatches ? 1u : 0u);
                token = hash_mix(token, out.sourceIndexOffsetMatches ? 1u : 0u);
                token = hash_mix(
                    token, static_cast<std::uint32_t>(out.sourceIndexFormat));
                token = hash_mix(token, out.sourceBaseVertexMatches ? 1u : 0u);
                token = hash_mix(token, out.sourceMinVertexMatches ? 1u : 0u);
                token = hash_mix(token, out.sourceNumVerticesMatches ? 1u : 0u);
                token = hash_mix(token, out.sourceRangeMatches ? 1u : 0u);
                token = hash_mix(token, out.cacheIdentityMatches ? 1u : 0u);
                token = hash_mix(token, out.joinValidated ? 1u : 0u);
                token = hash_mix(token, out.boundaryPreserved ? 1u : 0u);
                token = hash_mix(token, out.missingEvidenceMask);
                token = hash_mix(token, out.sourceRevalidationSnapshotToken);
                token = hash_mix(token, 0x295u);
                out.reviewSnapshotToken = token == 0 ? 1 : token;
            }
            return out;
        }

        std::uint32_t float_bits(float value) noexcept
        {
            static_assert(sizeof(std::uint32_t) == sizeof(float));
            std::uint32_t bits = 0;
            std::memcpy(&bits, &value, sizeof(bits));
            return bits;
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
            if (sig.sourceDrawIdentityExact)
            {
                hash = hash_mix(
                    hash, static_cast<std::uint32_t>(sig.sourceDraw.kind));
                hash = hash_mix(hash, sig.sourceDraw.primitiveCount);
                hash = hash_mix(hash, sig.sourceDraw.startVertex);
                hash = hash_mix(
                    hash,
                    static_cast<std::uint64_t>(
                        static_cast<std::int64_t>(sig.sourceDraw.baseVertexIndex)));
                hash = hash_mix(hash, sig.sourceDraw.minVertexIndex);
                hash = hash_mix(hash, sig.sourceDraw.numVertices);
                hash = hash_mix(hash, sig.sourceDraw.startIndex);
                hash = hash_mix(
                    hash, static_cast<std::uint32_t>(sig.sourceDraw.indexFormat));
                hash = hash_mix(hash, sig.sourceDraw.vertexStride);
                hash = hash_mix(
                    hash, sig.sourceDrawNativeBufferEligible ? 1u : 0u);
                hash = hash_mix(hash, sig.sourceDrawIdentitySnapshotToken);
            }
            hash = hash_mix(hash, sig.fvf);
            hash = hash_mix(hash, sig.vertexDeclHash);
            hash = hash_mix(hash, sig.vertexDeclElements);
            hash = hash_mix(hash, sig.streamOffset);
            hash = hash_mix(hash, sig.stride);
            hash = hash_mix(hash, sig.stream0Frequency);
            hash = hash_mix(hash, sig.vertexUsage);
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.vertexPool));
            hash = hash_mix(hash, sig.indexUsage);
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.indexPool));
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.indexFormat));
            hash = hash_mix(hash, sig.renderTargetUsage);
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.renderTargetPool));
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.renderTargetFormat));
            hash = hash_mix(
                hash, static_cast<std::uint32_t>(sig.renderTargetMultiSampleType));
            hash = hash_mix(hash, sig.renderTargetMultiSampleQuality);
            hash = hash_mix(
                hash, sig.auxiliaryRenderTargetObservationComplete ? 1u : 0u);
            hash = hash_mix(hash, sig.auxiliaryRenderTargetMask);
            hash = hash_mix(hash, sig.depthUsage);
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.depthPool));
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.depthFormat));
            hash = hash_mix(
                hash, static_cast<std::uint32_t>(sig.depthMultiSampleType));
            hash = hash_mix(hash, sig.depthMultiSampleQuality);
            // R217: resource observation completeness is part of sampled
            // signature identity. Failed descriptor/introspection paths must
            // not alias a fully observed draw whose descriptor fields happen
            // to retain the same default values.
            hash = hash_mix(
                hash, sig.resourceIntrospectionComplete ? 1u : 0u);
            // R219: derived resource-behavior readiness participates in
            // sampled identity. A future change to aggregate resource
            // accounting must not let mutation/lifetime blockers alias an
            // otherwise identical resource-ready draw.
            hash = hash_mix(
                hash, sig.resourceBehaviorDescriptorExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.resourceMutationTelemetryRequired ? 1u : 0u);
            hash = hash_mix(
                hash, sig.resourceManagedShadowRequired ? 1u : 0u);
            hash = hash_mix(
                hash, sig.resourceBehaviorExact ? 1u : 0u);
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
                hash = hash_mix(hash, stage.colorArg0);
                hash = hash_mix(hash, stage.alphaOp);
                hash = hash_mix(hash, stage.alphaArg1);
                hash = hash_mix(hash, stage.alphaArg2);
                hash = hash_mix(hash, stage.alphaArg0);
                hash = hash_mix(hash, stage.stageConstant);
                hash = hash_mix(hash, stage.resultArg);
                hash = hash_mix(hash, stage.texCoordIndex);
                hash = hash_mix(hash, stage.textureTransformFlags);
                hash = hash_mix(hash, stage.minFilter);
                hash = hash_mix(hash, stage.magFilter);
                hash = hash_mix(hash, stage.mipFilter);
                hash = hash_mix(hash, stage.mipLodBiasBits);
                hash = hash_mix(hash, stage.maxMipLevel);
                hash = hash_mix(hash, stage.addressU);
                hash = hash_mix(hash, stage.addressV);
                hash = hash_mix(hash, stage.borderColor);
                hash = hash_mix(hash, stage.srgbTexture);
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
            hash = hash_mix(
                hash, sig.vertexShader.sourceEvidenceExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.vertexShader.instructionDecodeExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.vertexShader.decodedInstructionCount);
            hash = hash_mix(
                hash, sig.vertexShader.decodedOperandTokenCount);
            hash = hash_mix(hash, sig.vertexShader.decodedStreamHash);
            hash = hash_mix(hash, sig.vertexShader.decoderRevisionHash);
            hash = hash_mix(hash, sig.vertexShader.semanticContractHash);
            hash = hash_mix(
                hash, sig.vertexShader.registerSemanticsExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.vertexShader.registerSemanticInstructionCount);
            hash = hash_mix(
                hash, sig.vertexShader.destinationOperandCount);
            hash = hash_mix(hash, sig.vertexShader.sourceOperandCount);
            hash = hash_mix(
                hash, sig.vertexShader.relativeAddressOperandCount);
            hash = hash_mix(
                hash, sig.vertexShader.floatConstantReferenceCount);
            hash = hash_mix(
                hash, sig.vertexShader.intConstantReferenceCount);
            hash = hash_mix(
                hash, sig.vertexShader.boolConstantReferenceCount);
            hash = hash_mix(hash, sig.vertexShader.samplerReferenceCount);
            hash = hash_mix(hash, sig.vertexShader.constantDefinitionCount);
            hash = hash_mix(hash, sig.vertexShader.registerSemanticsHash);
            hash = hash_mix(
                hash, sig.vertexShader.registerDecoderRevisionHash);
            hash = hash_mix(
                hash, sig.vertexShader.registerSemanticContractHash);
            hash = hash_mix(
                hash, sig.vertexShader.interfaceSemanticsExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.vertexShader.interfaceDeclarationInstructionCount);
            hash = hash_mix(
                hash, sig.vertexShader.interfaceSemanticDeclarationCount);
            hash = hash_mix(
                hash, sig.vertexShader.interfaceInputSemanticCount);
            hash = hash_mix(
                hash, sig.vertexShader.interfaceOutputSemanticCount);
            hash = hash_mix(
                hash, sig.vertexShader.interfaceSamplerDeclarationCount);
            hash = hash_mix(
                hash, sig.vertexShader.interfaceSemanticsHash);
            hash = hash_mix(
                hash, sig.vertexShader.interfaceDecoderRevisionHash);
            hash = hash_mix(
                hash, sig.vertexShader.interfaceSemanticContractHash);
            hash = hash_mix(hash, sig.pixelShader.present ? 1u : 0u);
            hash = hash_mix(hash, sig.pixelShader.observed ? 1u : 0u);
            hash = hash_mix(hash, sig.pixelShader.byteSize);
            hash = hash_mix(hash, sig.pixelShader.versionToken);
            hash = hash_mix(hash, sig.pixelShader.hash);
            hash = hash_mix(
                hash, sig.pixelShader.sourceEvidenceExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.pixelShader.instructionDecodeExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.pixelShader.decodedInstructionCount);
            hash = hash_mix(
                hash, sig.pixelShader.decodedOperandTokenCount);
            hash = hash_mix(hash, sig.pixelShader.decodedStreamHash);
            hash = hash_mix(hash, sig.pixelShader.decoderRevisionHash);
            hash = hash_mix(hash, sig.pixelShader.semanticContractHash);
            hash = hash_mix(
                hash, sig.pixelShader.registerSemanticsExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.pixelShader.registerSemanticInstructionCount);
            hash = hash_mix(
                hash, sig.pixelShader.destinationOperandCount);
            hash = hash_mix(hash, sig.pixelShader.sourceOperandCount);
            hash = hash_mix(
                hash, sig.pixelShader.relativeAddressOperandCount);
            hash = hash_mix(
                hash, sig.pixelShader.floatConstantReferenceCount);
            hash = hash_mix(
                hash, sig.pixelShader.intConstantReferenceCount);
            hash = hash_mix(
                hash, sig.pixelShader.boolConstantReferenceCount);
            hash = hash_mix(hash, sig.pixelShader.samplerReferenceCount);
            hash = hash_mix(hash, sig.pixelShader.constantDefinitionCount);
            hash = hash_mix(hash, sig.pixelShader.registerSemanticsHash);
            hash = hash_mix(
                hash, sig.pixelShader.registerDecoderRevisionHash);
            hash = hash_mix(
                hash, sig.pixelShader.registerSemanticContractHash);
            hash = hash_mix(
                hash, sig.pixelShader.interfaceSemanticsExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.pixelShader.interfaceDeclarationInstructionCount);
            hash = hash_mix(
                hash, sig.pixelShader.interfaceSemanticDeclarationCount);
            hash = hash_mix(
                hash, sig.pixelShader.interfaceInputSemanticCount);
            hash = hash_mix(
                hash, sig.pixelShader.interfaceOutputSemanticCount);
            hash = hash_mix(
                hash, sig.pixelShader.interfaceSamplerDeclarationCount);
            hash = hash_mix(
                hash, sig.pixelShader.interfaceSemanticsHash);
            hash = hash_mix(
                hash, sig.pixelShader.interfaceDecoderRevisionHash);
            hash = hash_mix(
                hash, sig.pixelShader.interfaceSemanticContractHash);
            hash = hash_mix(
                hash, sig.shaderInterfaceLinkExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderInterfaceMatchedSemanticCount);
            hash = hash_mix(hash, sig.shaderInterfaceLinkHash);
            hash = hash_mix(
                hash, sig.shaderInterfaceLinkerRevisionHash);
            hash = hash_mix(
                hash, sig.shaderInterfaceSemanticContractHash);
            hash = hash_mix(
                hash, sig.shaderSourceSemanticPairExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderSourceSemanticPairCacheKey);
            hash = hash_mix(
                hash, sig.shaderSourceSemanticPairHash);
            hash = hash_mix(
                hash, sig.shaderSourceSemanticReceiptRevisionHash);
            hash = hash_mix(
                hash, sig.shaderSourceSemanticContractHash);
            hash = hash_mix(
                hash, sig.shaderSourceVertexRegisterHash);
            hash = hash_mix(
                hash, sig.shaderSourcePixelRegisterHash);
            hash = hash_mix(
                hash, sig.shaderRegisterMappingPlanExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderConstantRegisterMappingCount);
            hash = hash_mix(
                hash, sig.shaderSamplerMappingCount);
            hash = hash_mix(
                hash, sig.shaderConstantRegisterMappingHash);
            hash = hash_mix(
                hash, sig.shaderSamplerMappingHash);
            hash = hash_mix(
                hash, sig.shaderRegisterMappingPlanRevisionHash);
            hash = hash_mix(
                hash, sig.shaderRegisterMappingSemanticContractHash);
            hash = hash_mix(
                hash, sig.shaderSourceMappingHandoffExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderSourceMappingHandoffSnapshotToken);
            hash = hash_mix(
                hash, sig.shaderSemanticTranslationPlanExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderSemanticTranslationPlanSnapshotToken);
            hash = hash_mix(
                hash, sig.shaderTranslatedVertexSemanticHash);
            hash = hash_mix(
                hash, sig.shaderTranslatedPixelSemanticHash);
            hash = hash_mix(hash, sig.shaderTranslatorRevisionHash);
            hash = hash_mix(
                hash, sig.shaderTranslationSemanticContractHash);
            hash = hash_mix(
                hash, sig.shaderTranslationObjectPrerequisiteExact ? 1u : 0u);
            hash = hash_mix(
                hash,
                sig.shaderTranslationObjectCacheOwnerGenerationRequired ? 1u : 0u);
            hash = hash_mix(
                hash,
                sig.shaderTranslationObjectSlotGenerationRequired ? 1u : 0u);
            hash = hash_mix(
                hash,
                sig.shaderTranslationObjectReceiptGenerationRequired ? 1u : 0u);
            hash = hash_mix(
                hash,
                sig.shaderTranslationObjectSameDevicePairRequired ? 1u : 0u);
            hash = hash_mix(
                hash,
                sig.shaderTranslationObjectCacheSnapshotRequired ? 1u : 0u);
            hash = hash_mix(
                hash,
                sig.shaderTranslationObjectSlotSnapshotRequired ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderTranslationObjectPrerequisiteSnapshotToken);
            hash = hash_mix(
                hash, sig.shaderObjectCreationHandoffExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderObjectCreationHandoffVertexSourceExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderObjectCreationHandoffPixelSourceExact ? 1u : 0u);
            hash = hash_mix(
                hash,
                sig.shaderObjectCreationHandoffOwnershipPrerequisiteMatches ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderObjectCreationAuthorized ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderObjectCreationHandoffSnapshotToken);
            hash = hash_mix(
                hash, sig.shaderTranslatedArtifactReceiptExact ? 1u : 0u);
            hash = hash_mix(
                hash,
                sig.shaderTranslatedArtifactReceiptTargetBytecodeRequired ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderTranslatedArtifactReceiptMaterialized ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderTranslatedArtifactCreationAuthorized ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderTranslatedVertexArtifactIdentity);
            hash = hash_mix(
                hash, sig.shaderTranslatedPixelArtifactIdentity);
            hash = hash_mix(
                hash, sig.shaderTranslatedArtifactReceiptSnapshotToken);
            hash = hash_mix(
                hash, sig.shaderTargetMaterializationContractExact ? 1u : 0u);
            hash = hash_mix(
                hash,
                sig.shaderTargetBytecodeMaterializationRequired ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderTargetBytecodeMaterialized ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderTargetCompilationAuthorized ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderTargetObjectCreationAuthorized ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderTargetVertexCompileContractIdentity);
            hash = hash_mix(
                hash, sig.shaderTargetPixelCompileContractIdentity);
            hash = hash_mix(hash, sig.shaderTargetEntryPointHash);
            hash = hash_mix(hash, sig.shaderTargetVertexProfileHash);
            hash = hash_mix(hash, sig.shaderTargetPixelProfileHash);
            hash = hash_mix(hash, sig.shaderTargetCompileFlags);
            hash = hash_mix(
                hash, sig.shaderTargetMaterializationContractSnapshotToken);
            hash = hash_mix(
                hash, sig.shaderTargetBytecodeMaterializationExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderTargetVertexSubsetSupported ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderTargetPixelSubsetSupported ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderTargetVertexCompiled ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderTargetPixelCompiled ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderTargetR283BytecodeMaterialized ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderTargetR283ObjectCreationAuthorized ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderTargetVertexTranslatedSourceBytes);
            hash = hash_mix(
                hash, sig.shaderTargetPixelTranslatedSourceBytes);
            hash = hash_mix(
                hash, sig.shaderTargetVertexTranslatedSourceHash);
            hash = hash_mix(
                hash, sig.shaderTargetPixelTranslatedSourceHash);
            hash = hash_mix(
                hash, sig.shaderTargetVertexBytecodeBytes);
            hash = hash_mix(
                hash, sig.shaderTargetPixelBytecodeBytes);
            hash = hash_mix(
                hash, sig.shaderTargetVertexBytecodeHash);
            hash = hash_mix(
                hash, sig.shaderTargetPixelBytecodeHash);
            hash = hash_mix(
                hash, sig.shaderTargetVertexMaterializedArtifactIdentity);
            hash = hash_mix(
                hash, sig.shaderTargetPixelMaterializedArtifactIdentity);
            hash = hash_mix(
                hash, sig.shaderTargetBytecodeMaterializationSnapshotToken);
            hash = hash_mix(
                hash, sig.shaderProductionObservationExact ? 1u : 0u);
            hash = hash_mix(
                hash,
                sig.shaderProductionObservationMaterializationReused ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderProductionObservationObjectReady ? 1u : 0u);
            hash = hash_mix(
                hash,
                sig.shaderProductionObservationBoundaryPreserved ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderProductionObservationOwnerGeneration);
            hash = hash_mix(
                hash, sig.shaderProductionSemanticHandoffSnapshotToken);
            hash = hash_mix(
                hash, sig.shaderProductionObservationSnapshotToken);
            hash = hash_mix(
                hash, sig.shaderTranslationAdmissionExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderTranslationAdmissionBoundaryPreserved ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderTranslationAdmissionSnapshotToken);
            hash = hash_mix(
                hash, sig.shaderProductionSemanticReviewExact ? 1u : 0u);
            hash = hash_mix(
                hash,
                sig.shaderProductionSemanticReviewInputLayoutReady ? 1u : 0u);
            hash = hash_mix(
                hash,
                sig.shaderProductionSemanticReviewInputLayoutReused ? 1u : 0u);
            hash = hash_mix(
                hash,
                sig.shaderProductionSemanticReviewTranslationReady ? 1u : 0u);
            hash = hash_mix(
                hash,
                sig.shaderProductionSemanticReviewBoundaryPreserved ? 1u : 0u);
            hash = hash_mix(
                hash,
                sig.shaderProductionSemanticReviewInputLayoutSnapshotToken);
            hash = hash_mix(
                hash,
                sig.shaderProductionSemanticReviewTranslationSnapshotToken);
            hash = hash_mix(
                hash, sig.shaderProductionSemanticReviewSnapshotToken);
            hash = hash_mix(
                hash, sig.shaderProductionSourceDrawIdentityExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderProductionSourceNativeBufferEligible ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderProductionSourceReceiptPresent ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderProductionSourceReceiptContractReady ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderProductionSourceKindMatches ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderProductionSourceStartMatches ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderProductionSourceElementCountDerivable ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderProductionSourceElementCountMatches ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderProductionSourceElementCount);
            hash = hash_mix(
                hash, sig.shaderProductionSourceIndexFormatKnown ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderProductionSourceIndexFormatMatches ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderProductionSourceIndexOffsetMatches ? 1u : 0u);
            hash = hash_mix(
                hash,
                static_cast<std::uint32_t>(
                    sig.shaderProductionSourceIndexFormat));
            hash = hash_mix(
                hash, sig.shaderProductionSourceBaseVertexMatches ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderProductionSourceMinVertexMatches ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderProductionSourceNumVerticesMatches ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderProductionSourceRangeMatches ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderProductionSourceCacheKeyMatches ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderProductionSourceJoinExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderProductionSourceBoundaryPreserved ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderProductionSourceMissingEvidenceMask);
            hash = hash_mix(
                hash, sig.shaderProductionSourceReceiptSnapshotToken);
            hash = hash_mix(
                hash, sig.shaderProductionSourceJoinSnapshotToken);
            hash = hash_mix(
                hash,
                sig.shaderProductionActivationSourceReceiptPresent ? 1u : 0u);
            hash = hash_mix(
                hash,
                sig.shaderProductionActivationResourceReceiptPresent ? 1u : 0u);
            hash = hash_mix(
                hash,
                sig.shaderProductionActivationPrerequisiteExact ? 1u : 0u);
            hash = hash_mix(
                hash,
                sig.shaderProductionActivationStaticPrerequisitesSatisfied
                    ? 1u : 0u);
            hash = hash_mix(
                hash,
                sig.shaderProductionActivationBoundaryPreserved ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderProductionActivationMissingReceiptMask);
            hash = hash_mix(
                hash,
                sig.shaderProductionActivationPrerequisiteSnapshotToken);
            hash = hash_mix(
                hash, sig.shaderTranslatedSemanticReceiptExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderTranslatedSemanticReceiptObjectReady ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shaderTranslatedSemanticReceiptSnapshotToken);
            hash = hash_mix(hash, sig.shaderIntrospectionComplete ? 1u : 0u);
            hash = hash_mix(hash, sig.shaderMixedPair ? 1u : 0u);
            hash = hash_mix(hash, sig.shaderTranslationExact ? 1u : 0u);
            hash = hash_mix(hash, sig.shaderReadinessExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.fixedFunctionStateCoverageExact ? 1u : 0u);
            hash = hash_mix(
                hash, sig.shadeModeObservationComplete ? 1u : 0u);
            hash = hash_mix(hash, sig.shadeMode);
            hash = hash_mix(
                hash, sig.vertexBlendObservationComplete ? 1u : 0u);
            hash = hash_mix(hash, sig.vertexBlend);
            hash = hash_mix(hash, sig.indexedVertexBlendEnable);
            hash = hash_mix(
                hash, sig.depthBiasObservationComplete ? 1u : 0u);
            hash = hash_mix(hash, sig.depthBiasBits);
            hash = hash_mix(hash, sig.slopeScaleDepthBiasBits);
            hash = hash_mix(
                hash, sig.ditherObservationComplete ? 1u : 0u);
            hash = hash_mix(hash, sig.ditherEnable);
            hash = hash_mix(
                hash, sig.multisampleRasterObservationComplete ? 1u : 0u);
            hash = hash_mix(hash, sig.multiSampleAntialias);
            hash = hash_mix(
                hash, sig.lineRasterObservationComplete ? 1u : 0u);
            hash = hash_mix(hash, sig.lastPixel);
            hash = hash_mix(hash, sig.antialiasedLineEnable);
            hash = hash_mix(
                hash, sig.outputStateObservationComplete ? 1u : 0u);
            hash = hash_mix(hash, sig.outputBlendFactor);
            hash = hash_mix(hash, sig.outputMultiSampleMask);
            hash = hash_mix(
                hash, sig.textureFactorObservationComplete ? 1u : 0u);
            hash = hash_mix(hash, sig.textureFactor);
            hash = hash_mix(hash, sig.outputViewport.X);
            hash = hash_mix(hash, sig.outputViewport.Y);
            hash = hash_mix(hash, sig.outputViewport.Width);
            hash = hash_mix(hash, sig.outputViewport.Height);
            hash = hash_mix(hash, float_bits(sig.outputViewport.MinZ));
            hash = hash_mix(hash, float_bits(sig.outputViewport.MaxZ));
            hash = hash_mix(
                hash, static_cast<std::uint32_t>(sig.outputScissorRect.left));
            hash = hash_mix(
                hash, static_cast<std::uint32_t>(sig.outputScissorRect.top));
            hash = hash_mix(
                hash, static_cast<std::uint32_t>(sig.outputScissorRect.right));
            hash = hash_mix(
                hash, static_cast<std::uint32_t>(sig.outputScissorRect.bottom));
            hash = hash_mix(hash, sig.outputScissorTestEnable);
            hash = hash_mix(
                hash, sig.pointRasterObservationComplete ? 1u : 0u);
            hash = hash_mix(hash, sig.pointSizeBits);
            hash = hash_mix(hash, sig.pointSizeMinBits);
            hash = hash_mix(hash, sig.pointSizeMaxBits);
            hash = hash_mix(hash, sig.pointSpriteEnable);
            hash = hash_mix(hash, sig.pointScaleEnable);
            hash = hash_mix(hash, sig.pointScaleABits);
            hash = hash_mix(hash, sig.pointScaleBBits);
            hash = hash_mix(hash, sig.pointScaleCBits);
            hash = hash_mix(
                hash, sig.textureCoordinateWrapObservationComplete ? 1u : 0u);
            for (const auto wrap : sig.textureCoordinateWrap)
                hash = hash_mix(hash, wrap);
            hash = hash_mix(
                hash, sig.rt0ColorWriteObservationComplete ? 1u : 0u);
            hash = hash_mix(hash, sig.colorWriteEnable);
            hash = hash_mix(
                hash, sig.mrtColorWriteObservationComplete ? 1u : 0u);
            for (const auto mask : sig.additionalColorWriteEnable)
                hash = hash_mix(hash, mask);
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
            TShader* shader,
            bool vertexStage,
            ProgrammableShaderInterfaceSemantics*
                interfaceSemanticsOut = nullptr,
            ProgrammableShaderRegisterSemantics*
                registerSemanticsOut = nullptr,
            ProgrammableShaderFunctionSourceEvidence*
                sourceEvidenceOut = nullptr) noexcept
        {
            if (interfaceSemanticsOut)
                *interfaceSemanticsOut = {};
            if (registerSemanticsOut)
                *registerSemanticsOut = {};
            if (sourceEvidenceOut)
                *sourceEvidenceOut = {};
            ShaderFunctionSignature out{};
            out.present = shader != nullptr;
            if (!shader)
            {
                out.observed = true;
                out.sourceEvidenceExact = true;
                return out;
            }

            UINT byteSize = 0;
            if (FAILED(shader->GetFunction(nullptr, &byteSize)) ||
                byteSize < 2u * sizeof(DWORD) ||
                byteSize > (1024u * 1024u) ||
                (byteSize % sizeof(DWORD)) != 0)
                return out;

            std::vector<std::uint8_t> bytecode(byteSize);
            UINT actual = byteSize;
            if (FAILED(shader->GetFunction(bytecode.data(), &actual)) ||
                actual != byteSize)
                return out;

            const auto evidence =
                capture_programmable_shader_function_source_evidence(
                    bytecode.data(), actual, vertexStage);
            if (sourceEvidenceOut)
                *sourceEvidenceOut = evidence;
            out.observed = evidence.observed;
            out.sourceEvidenceExact = evidence.exact();
            out.byteSize = evidence.byteSize;
            out.versionToken = evidence.versionToken;
            out.hash = evidence.bytecodeHash;

            const auto decode =
                decode_programmable_shader_instruction_stream(evidence);
            out.instructionDecodeExact = decode.exact();
            out.decodedInstructionCount = decode.instructionCount;
            out.decodedOperandTokenCount = decode.operandTokenCount;
            out.decodedStreamHash = decode.instructionStreamHash;
            out.decoderRevisionHash = decode.decoderRevisionHash;
            out.semanticContractHash = decode.semanticContractHash;

            const auto registerSemantics =
                decode_programmable_shader_register_semantics(decode);
            out.registerSemanticsExact =
                validate_programmable_shader_register_semantics(
                    registerSemantics, decode);
            out.registerSemanticInstructionCount =
                registerSemantics.semanticInstructionCount;
            out.destinationOperandCount =
                registerSemantics.destinationOperandCount;
            out.sourceOperandCount =
                registerSemantics.sourceOperandCount;
            out.relativeAddressOperandCount =
                registerSemantics.relativeAddressOperandCount;
            out.floatConstantReferenceCount =
                registerSemantics.floatConstantReferenceCount;
            out.intConstantReferenceCount =
                registerSemantics.intConstantReferenceCount;
            out.boolConstantReferenceCount =
                registerSemantics.boolConstantReferenceCount;
            out.samplerReferenceCount =
                registerSemantics.samplerReferenceCount;
            out.constantDefinitionCount =
                registerSemantics.constantDefinitionCount;
            out.registerSemanticsHash =
                registerSemantics.registerSemanticsHash;
            out.registerDecoderRevisionHash =
                registerSemantics.decoderRevisionHash;
            out.registerSemanticContractHash =
                registerSemantics.semanticContractHash;
            if (registerSemanticsOut)
                *registerSemanticsOut = registerSemantics;

            const auto interfaceSemantics =
                decode_programmable_shader_interface_semantics(
                    decode, registerSemantics);
            out.interfaceSemanticsExact = interfaceSemantics.exact();
            out.interfaceDeclarationInstructionCount =
                interfaceSemantics.declarationInstructionCount;
            out.interfaceSemanticDeclarationCount =
                interfaceSemantics.semanticDeclarationCount;
            out.interfaceInputSemanticCount =
                interfaceSemantics.inputSemanticCount;
            out.interfaceOutputSemanticCount =
                interfaceSemantics.outputSemanticCount;
            out.interfaceSamplerDeclarationCount =
                interfaceSemantics.samplerDeclarationCount;
            out.interfaceSemanticsHash =
                interfaceSemantics.interfaceSemanticsHash;
            out.interfaceDecoderRevisionHash =
                interfaceSemantics.decoderRevisionHash;
            out.interfaceSemanticContractHash =
                interfaceSemantics.semanticContractHash;
            if (interfaceSemanticsOut)
                *interfaceSemanticsOut = interfaceSemantics;
            return out;
        }

        SourceSignature inspect_source_signature(
            IDirect3DDevice9* device,
            bool fixedFunction,
            IDirect3DVertexShader9* vertexShader,
            IDirect3DPixelShader9* pixelShader,
            bool shaderQueryComplete,
            FixedFunctionLightingState fixedFunctionLighting) noexcept
        {
            SourceSignature sig{};
            sig.fixedFunction = fixedFunction;
            ProgrammableShaderInterfaceSemantics vertexInterfaceSemantics{};
            ProgrammableShaderInterfaceSemantics pixelInterfaceSemantics{};
            ProgrammableShaderRegisterSemantics vertexRegisterSemantics{};
            ProgrammableShaderRegisterSemantics pixelRegisterSemantics{};
            ProgrammableShaderFunctionSourceEvidence vertexSourceEvidence{};
            ProgrammableShaderFunctionSourceEvidence pixelSourceEvidence{};
            sig.vertexShader =
                inspect_shader_function(
                    vertexShader, true, &vertexInterfaceSemantics,
                    &vertexRegisterSemantics, &vertexSourceEvidence);
            sig.pixelShader =
                inspect_shader_function(
                    pixelShader, false, &pixelInterfaceSemantics,
                    &pixelRegisterSemantics, &pixelSourceEvidence);
            const auto shaderInterfaceLinkage =
                derive_programmable_shader_interface_linkage_evidence(
                    vertexInterfaceSemantics, pixelInterfaceSemantics);
            sig.shaderInterfaceLinkExact = shaderInterfaceLinkage.exact();
            sig.shaderInterfaceMatchedSemanticCount =
                shaderInterfaceLinkage.matchedSemanticCount;
            sig.shaderInterfaceLinkHash =
                shaderInterfaceLinkage.interfaceLinkHash;
            sig.shaderInterfaceLinkerRevisionHash =
                shaderInterfaceLinkage.linkerRevisionHash;
            sig.shaderInterfaceSemanticContractHash =
                shaderInterfaceLinkage.semanticContractHash;
            sig.shaderIntrospectionComplete =
                shaderQueryComplete &&
                sig.vertexShader.observed &&
                sig.pixelShader.observed &&
                sig.vertexShader.sourceEvidenceExact &&
                sig.pixelShader.sourceEvidenceExact;
            sig.shaderMixedPair =
                shaderQueryComplete &&
                ((vertexShader != nullptr) != (pixelShader != nullptr));

            const ProgrammableShaderFunctionIdentity vertexIdentity{
                sig.vertexShader.present,
                sig.vertexShader.observed,
                sig.vertexShader.byteSize,
                sig.vertexShader.versionToken,
                sig.vertexShader.hash,
            };
            const ProgrammableShaderFunctionIdentity pixelIdentity{
                sig.pixelShader.present,
                sig.pixelShader.observed,
                sig.pixelShader.byteSize,
                sig.pixelShader.versionToken,
                sig.pixelShader.hash,
            };
            const auto programmablePairIdentity =
                seal_programmable_shader_pair_cache_identity(
                    shaderQueryComplete,
                    sig.shaderMixedPair,
                    vertexIdentity,
                    pixelIdentity);
            const auto sourceSemanticPair =
                derive_programmable_shader_pair_source_semantic_evidence(
                    programmablePairIdentity,
                    vertexRegisterSemantics,
                    pixelRegisterSemantics,
                    shaderInterfaceLinkage);
            sig.shaderSourceSemanticPairExact =
                sourceSemanticPair.exact();
            sig.shaderSourceSemanticPairCacheKey =
                sourceSemanticPair.cacheKey;
            sig.shaderSourceSemanticPairHash =
                sourceSemanticPair.pairSemanticHash;
            sig.shaderSourceSemanticReceiptRevisionHash =
                sourceSemanticPair.receiptRevisionHash;
            sig.shaderSourceSemanticContractHash =
                sourceSemanticPair.semanticContractHash;
            sig.shaderSourceVertexRegisterHash =
                sourceSemanticPair.vertexRegisterSemanticsHash;
            sig.shaderSourcePixelRegisterHash =
                sourceSemanticPair.pixelRegisterSemanticsHash;
            const auto registerMappingPlan =
                derive_programmable_shader_register_mapping_plan(
                    sourceSemanticPair,
                    vertexRegisterSemantics,
                    pixelRegisterSemantics);
            sig.shaderRegisterMappingPlanExact =
                registerMappingPlan.exact();
            sig.shaderConstantRegisterMappingCount =
                registerMappingPlan.constantMappingCount;
            sig.shaderSamplerMappingCount =
                registerMappingPlan.samplerMappingCount;
            sig.shaderConstantRegisterMappingHash =
                registerMappingPlan.constantMappingHash;
            sig.shaderSamplerMappingHash =
                registerMappingPlan.samplerMappingHash;
            sig.shaderRegisterMappingPlanRevisionHash =
                registerMappingPlan.planRevisionHash;
            sig.shaderRegisterMappingSemanticContractHash =
                registerMappingPlan.semanticContractHash;
            const auto sourceMappingHandoff =
                compose_programmable_shader_source_mapping_handoff(
                    programmablePairIdentity,
                    sourceSemanticPair,
                    registerMappingPlan);
            sig.shaderSourceMappingHandoffExact =
                sourceMappingHandoff.reviewReady;
            sig.shaderSourceMappingHandoffSnapshotToken =
                sourceMappingHandoff.reviewSnapshotToken;

            const auto semanticTranslationPlan =
                derive_programmable_shader_semantic_translation_plan(
                    sourceSemanticPair,
                    shaderInterfaceLinkage,
                    sourceMappingHandoff,
                    sourceMappingHandoff.reviewSnapshotToken);
            sig.shaderSemanticTranslationPlanExact =
                semanticTranslationPlan.reviewReady;
            sig.shaderSemanticTranslationPlanSnapshotToken =
                semanticTranslationPlan.reviewSnapshotToken;
            sig.shaderTranslatedVertexSemanticHash =
                semanticTranslationPlan.targetVertexSemanticHash;
            sig.shaderTranslatedPixelSemanticHash =
                semanticTranslationPlan.targetPixelSemanticHash;
            sig.shaderTranslatorRevisionHash =
                semanticTranslationPlan.translatorRevisionHash;
            sig.shaderTranslationSemanticContractHash =
                semanticTranslationPlan.semanticContractHash;

            const auto translationObjectPrerequisite =
                derive_programmable_shader_translation_object_prerequisite(
                    programmablePairIdentity,
                    semanticTranslationPlan,
                    semanticTranslationPlan.reviewSnapshotToken);
            sig.shaderTranslationObjectPrerequisiteExact =
                translationObjectPrerequisite.reviewReady;
            sig.shaderTranslationObjectCacheOwnerGenerationRequired =
                translationObjectPrerequisite.cacheOwnerGenerationRequired;
            sig.shaderTranslationObjectSlotGenerationRequired =
                translationObjectPrerequisite.translationSlotGenerationRequired;
            sig.shaderTranslationObjectReceiptGenerationRequired =
                translationObjectPrerequisite.
                    translationObjectReceiptGenerationRequired;
            sig.shaderTranslationObjectSameDevicePairRequired =
                translationObjectPrerequisite.sameDeviceObjectPairRequired;
            sig.shaderTranslationObjectCacheSnapshotRequired =
                translationObjectPrerequisite.cacheSnapshotRequired;
            sig.shaderTranslationObjectSlotSnapshotRequired =
                translationObjectPrerequisite.slotSnapshotRequired;
            sig.shaderTranslationObjectPrerequisiteSnapshotToken =
                translationObjectPrerequisite.reviewSnapshotToken;

            const auto objectCreationHandoff =
                compose_programmable_shader_object_creation_handoff(
                    programmablePairIdentity,
                    vertexSourceEvidence,
                    pixelSourceEvidence,
                    semanticTranslationPlan,
                    semanticTranslationPlan.reviewSnapshotToken,
                    translationObjectPrerequisite,
                    translationObjectPrerequisite.reviewSnapshotToken);
            sig.shaderObjectCreationHandoffExact =
                objectCreationHandoff.reviewReady;
            sig.shaderObjectCreationHandoffVertexSourceExact =
                objectCreationHandoff.vertexSourceExact;
            sig.shaderObjectCreationHandoffPixelSourceExact =
                objectCreationHandoff.pixelSourceExact;
            sig.shaderObjectCreationHandoffOwnershipPrerequisiteMatches =
                objectCreationHandoff.objectPrerequisiteSnapshotMatches;
            sig.shaderObjectCreationAuthorized =
                objectCreationHandoff.objectCreationAuthorized;
            sig.shaderObjectCreationHandoffSnapshotToken =
                objectCreationHandoff.reviewSnapshotToken;

            const auto translatedArtifactReceipt =
                derive_programmable_shader_translated_artifact_receipt(
                    programmablePairIdentity,
                    objectCreationHandoff,
                    objectCreationHandoff.reviewSnapshotToken,
                    semanticTranslationPlan,
                    semanticTranslationPlan.reviewSnapshotToken);
            sig.shaderTranslatedArtifactReceiptExact =
                translatedArtifactReceipt.reviewReady;
            sig.shaderTranslatedArtifactReceiptTargetBytecodeRequired =
                translatedArtifactReceipt.targetBytecodeReceiptRequired;
            sig.shaderTranslatedArtifactReceiptMaterialized =
                translatedArtifactReceipt.targetBytecodeMaterialized;
            sig.shaderTranslatedArtifactCreationAuthorized =
                translatedArtifactReceipt.objectCreationAuthorized;
            sig.shaderTranslatedVertexArtifactIdentity =
                translatedArtifactReceipt.targetVertexBytecodeReceiptIdentity;
            sig.shaderTranslatedPixelArtifactIdentity =
                translatedArtifactReceipt.targetPixelBytecodeReceiptIdentity;
            sig.shaderTranslatedArtifactReceiptSnapshotToken =
                translatedArtifactReceipt.reviewSnapshotToken;

            const auto targetMaterializationContract =
                derive_programmable_shader_target_materialization_contract(
                    programmablePairIdentity,
                    translatedArtifactReceipt,
                    translatedArtifactReceipt.reviewSnapshotToken,
                    semanticTranslationPlan,
                    semanticTranslationPlan.reviewSnapshotToken);
            sig.shaderTargetMaterializationContractExact =
                targetMaterializationContract.reviewReady;
            sig.shaderTargetBytecodeMaterializationRequired =
                targetMaterializationContract.targetBytecodeMaterializationRequired;
            sig.shaderTargetBytecodeMaterialized =
                targetMaterializationContract.targetBytecodeMaterialized;
            sig.shaderTargetCompilationAuthorized =
                targetMaterializationContract.compilationAuthorized;
            sig.shaderTargetObjectCreationAuthorized =
                targetMaterializationContract.objectCreationAuthorized;
            sig.shaderTargetVertexCompileContractIdentity =
                targetMaterializationContract.vertexCompileContractIdentity;
            sig.shaderTargetPixelCompileContractIdentity =
                targetMaterializationContract.pixelCompileContractIdentity;
            sig.shaderTargetEntryPointHash =
                targetMaterializationContract.entryPointHash;
            sig.shaderTargetVertexProfileHash =
                targetMaterializationContract.vertexTargetProfileHash;
            sig.shaderTargetPixelProfileHash =
                targetMaterializationContract.pixelTargetProfileHash;
            sig.shaderTargetCompileFlags =
                targetMaterializationContract.compileFlags;
            sig.shaderTargetMaterializationContractSnapshotToken =
                targetMaterializationContract.reviewSnapshotToken;

            const auto targetBytecodeMaterialization =
                materialize_programmable_shader_target_bytecode(
                    programmablePairIdentity,
                    vertexSourceEvidence,
                    pixelSourceEvidence,
                    translatedArtifactReceipt,
                    translatedArtifactReceipt.reviewSnapshotToken,
                    targetMaterializationContract,
                    targetMaterializationContract.reviewSnapshotToken,
                    semanticTranslationPlan,
                    semanticTranslationPlan.reviewSnapshotToken);
            sig.shaderTargetBytecodeMaterializationExact =
                validate_programmable_shader_target_bytecode_materialization_snapshot(
                    programmablePairIdentity,
                    vertexSourceEvidence,
                    pixelSourceEvidence,
                    translatedArtifactReceipt,
                    translatedArtifactReceipt.reviewSnapshotToken,
                    targetMaterializationContract,
                    targetMaterializationContract.reviewSnapshotToken,
                    semanticTranslationPlan,
                    semanticTranslationPlan.reviewSnapshotToken,
                    targetBytecodeMaterialization,
                    targetBytecodeMaterialization.reviewSnapshotToken);
            sig.shaderTargetVertexSubsetSupported =
                targetBytecodeMaterialization.vertexSubsetSupported;
            sig.shaderTargetPixelSubsetSupported =
                targetBytecodeMaterialization.pixelSubsetSupported;
            sig.shaderTargetVertexCompiled =
                targetBytecodeMaterialization.vertexCompilationSucceeded;
            sig.shaderTargetPixelCompiled =
                targetBytecodeMaterialization.pixelCompilationSucceeded;
            sig.shaderTargetR283BytecodeMaterialized =
                targetBytecodeMaterialization.targetBytecodeMaterialized;
            sig.shaderTargetR283ObjectCreationAuthorized =
                targetBytecodeMaterialization.objectCreationAuthorized;
            sig.shaderTargetVertexTranslatedSourceBytes =
                targetBytecodeMaterialization.vertexTranslatedSourceBytes;
            sig.shaderTargetPixelTranslatedSourceBytes =
                targetBytecodeMaterialization.pixelTranslatedSourceBytes;
            sig.shaderTargetVertexTranslatedSourceHash =
                targetBytecodeMaterialization.vertexTranslatedSourceHash;
            sig.shaderTargetPixelTranslatedSourceHash =
                targetBytecodeMaterialization.pixelTranslatedSourceHash;
            sig.shaderTargetVertexBytecodeBytes =
                targetBytecodeMaterialization.vertexTargetBytecodeBytes;
            sig.shaderTargetPixelBytecodeBytes =
                targetBytecodeMaterialization.pixelTargetBytecodeBytes;
            sig.shaderTargetVertexBytecodeHash =
                targetBytecodeMaterialization.vertexTargetBytecodeHash;
            sig.shaderTargetPixelBytecodeHash =
                targetBytecodeMaterialization.pixelTargetBytecodeHash;
            sig.shaderTargetVertexMaterializedArtifactIdentity =
                targetBytecodeMaterialization.vertexMaterializedArtifactIdentity;
            sig.shaderTargetPixelMaterializedArtifactIdentity =
                targetBytecodeMaterialization.pixelMaterializedArtifactIdentity;
            sig.shaderTargetBytecodeMaterializationSnapshotToken =
                targetBytecodeMaterialization.reviewSnapshotToken;

            const auto productionObservation =
                observe_programmable_production_chain(
                    device,
                    programmablePairIdentity,
                    translationObjectPrerequisite,
                    translationObjectPrerequisite.reviewSnapshotToken,
                    objectCreationHandoff,
                    objectCreationHandoff.reviewSnapshotToken,
                    targetBytecodeMaterialization,
                    targetBytecodeMaterialization.reviewSnapshotToken,
                    sourceMappingHandoff,
                    sourceMappingHandoff.reviewSnapshotToken,
                    semanticTranslationPlan,
                    semanticTranslationPlan.reviewSnapshotToken);
            sig.shaderProductionObservationExact =
                productionObservation.reviewReady;
            sig.shaderProductionObservationMaterializationReused =
                productionObservation.semanticHandoff.materializationReused;
            sig.shaderProductionObservationObjectReady =
                productionObservation.semanticHandoff.translationObjectReady;
            sig.shaderProductionObservationBoundaryPreserved =
                productionObservation.boundaryPreserved;
            sig.shaderProductionObservationOwnerGeneration =
                productionObservation.backendOwnerGeneration;
            sig.shaderProductionSemanticHandoffSnapshotToken =
                productionObservation.semanticHandoffSnapshotToken;
            sig.shaderProductionObservationSnapshotToken =
                productionObservation.reviewSnapshotToken;

            NativeProgrammableShaderTranslatedSemanticReceipt
                translatedSemanticReceipt{};
            if (productionObservation.reviewReady &&
                productionObservation.semanticHandoffReady &&
                productionObservation.semanticHandoffSnapshotMatches)
            {
                translatedSemanticReceipt =
                    productionObservation.semanticHandoff.translatedSemanticReceipt;
            }
            else
            {
                const NativeProgrammableShaderTranslationObjectReadiness
                    unavailableTranslationObject{};
                translatedSemanticReceipt =
                    compose_programmable_shader_translated_semantic_receipt(
                        programmablePairIdentity,
                        unavailableTranslationObject,
                        0,
                        sourceMappingHandoff,
                        sourceMappingHandoff.reviewSnapshotToken,
                        semanticTranslationPlan,
                        semanticTranslationPlan.reviewSnapshotToken);
            }
            sig.shaderTranslatedSemanticReceiptExact =
                translatedSemanticReceipt.reviewReady;
            sig.shaderTranslatedSemanticReceiptObjectReady =
                translatedSemanticReceipt.translationObjectReady;
            sig.shaderTranslatedSemanticReceiptSnapshotToken =
                translatedSemanticReceipt.reviewSnapshotToken;
            sig.shaderTranslatedSemanticReceiptEvidence =
                translatedSemanticReceipt;

            // R80 starts fail-closed. R215 may promote only the later
            // fixed-function branch after its resource-dependent pixel
            // prototype, vertex prototype and WVP transform are all exact.
            // Programmable D3D9 shaders remain unsupported.
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

            // R175: GetStreamSource does not expose D3D9 instancing
            // frequency. Observe it independently so INDEXEDDATA/
            // INSTANCEDATA semantics cannot alias an ordinary vertex stream.
            if (FAILED(device->GetStreamSourceFreq(
                    0, &sig.stream0Frequency)))
                sig.resourceIntrospectionComplete = false;

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
                    sig.renderTargetMultiSampleType = desc.MultiSampleType;
                    sig.renderTargetMultiSampleQuality =
                        desc.MultiSampleQuality;
                }
                else
                    sig.resourceIntrospectionComplete = false;
                rt0->Release();
            }

            // R174: native DX11 output readiness owns exactly one color target.
            // Query only source-supported MRT slots; any bound auxiliary target
            // remains explicit fail-closed census evidence.
            D3DCAPS9 caps{};
            if (FAILED(device->GetDeviceCaps(&caps)))
            {
                sig.auxiliaryRenderTargetObservationComplete = false;
                sig.resourceIntrospectionComplete = false;
            }
            else
            {
                for (DWORD index = 1; index <= 3; ++index)
                {
                    if (index >= caps.NumSimultaneousRTs)
                        break;
                    IDirect3DSurface9* auxiliary = nullptr;
                    const HRESULT auxiliaryHr = device->GetRenderTarget(index, &auxiliary);
                    if (FAILED(auxiliaryHr) && auxiliaryHr != D3DERR_NOTFOUND)
                    {
                        sig.auxiliaryRenderTargetObservationComplete = false;
                        sig.resourceIntrospectionComplete = false;
                    }
                    else if (auxiliary)
                    {
                        sig.auxiliaryRenderTargetMask |=
                            static_cast<std::uint8_t>(1u << (index - 1u));
                    }
                    if (auxiliary)
                        auxiliary->Release();
                }
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
                    sig.depthMultiSampleType = desc.MultiSampleType;
                    sig.depthMultiSampleQuality = desc.MultiSampleQuality;
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
                    observeTextureStageState(D3DTSS_COLORARG0, out.colorArg0);
                    observeTextureStageState(D3DTSS_ALPHAOP, out.alphaOp);
                    observeTextureStageState(D3DTSS_ALPHAARG1, out.alphaArg1);
                    observeTextureStageState(D3DTSS_ALPHAARG2, out.alphaArg2);
                    observeTextureStageState(D3DTSS_ALPHAARG0, out.alphaArg0);
                    observeTextureStageState(D3DTSS_CONSTANT, out.stageConstant);
                    // R173: RESULTARG affects supported SELECTARG/MODULATE
                    // chains even when all argument/op enums are otherwise exact.
                    observeTextureStageState(D3DTSS_RESULTARG, out.resultArg);
                    observeTextureStageState(
                        D3DTSS_TEXCOORDINDEX, out.texCoordIndex);
                    observeTextureStageState(
                        D3DTSS_TEXTURETRANSFORMFLAGS,
                        out.textureTransformFlags);

                    observeSamplerState(D3DSAMP_MINFILTER, out.minFilter);
                    observeSamplerState(D3DSAMP_MAGFILTER, out.magFilter);
                    observeSamplerState(D3DSAMP_MIPFILTER, out.mipFilter);
                    observeSamplerState(
                        D3DSAMP_MIPMAPLODBIAS, out.mipLodBiasBits);
                    observeSamplerState(
                        D3DSAMP_MAXMIPLEVEL, out.maxMipLevel);
                    observeSamplerState(D3DSAMP_ADDRESSU, out.addressU);
                    observeSamplerState(D3DSAMP_ADDRESSV, out.addressV);
                    observeSamplerState(D3DSAMP_BORDERCOLOR, out.borderColor);
                    observeSamplerState(D3DSAMP_SRGBTEXTURE, out.srgbTexture);
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
                        sig.fvf, sig.stride, fixedFunctionLighting);
                sig.fixedFunctionVertexShaderPrototypeGenerated =
                    vertexPrototype.generated();
                sig.fixedFunctionVertexShaderPrototypeUnsupported =
                    vertexPrototype.unsupported;
                sig.fixedFunctionVertexShaderPrototypeHash =
                    vertexPrototype.sourceHash;
                sig.fixedFunctionVertexShaderPrototypeBytes =
                    static_cast<UINT>(vertexPrototype.source.size());
                sig.fixedFunctionVertexShaderPrototypeSource =
                    vertexPrototype.source;

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

            const auto productionSemanticReview =
                review_programmable_production_semantics(
                    device,
                    programmablePairIdentity,
                    productionObservation,
                    targetBytecodeMaterialization,
                    inputLayout,
                    shaderInterfaceLinkage);
            sig.shaderTranslationAdmissionExact =
                productionSemanticReview.admissionValidated;
            sig.shaderTranslationAdmissionBoundaryPreserved =
                productionSemanticReview.admissionValidated &&
                productionSemanticReview.admission.boundaryPreserved;
            sig.shaderTranslationAdmissionSnapshotToken =
                productionSemanticReview.admissionValidated
                    ? productionSemanticReview.admission.reviewSnapshotToken
                    : 0;
            sig.shaderProductionSemanticReviewExact =
                productionSemanticReview.reviewValidated;
            sig.shaderProductionSemanticReviewInputLayoutReady =
                productionSemanticReview.reviewValidated &&
                productionSemanticReview.review.inputLayoutReceiptReady &&
                productionSemanticReview.review.inputLayoutSnapshotMatches;
            sig.shaderProductionSemanticReviewInputLayoutReused =
                productionSemanticReview.reviewValidated &&
                productionSemanticReview.review.inputLayoutReused;
            sig.shaderProductionSemanticReviewTranslationReady =
                productionSemanticReview.reviewValidated &&
                productionSemanticReview.review.semanticTranslationReady &&
                productionSemanticReview.review.semanticTranslationSnapshotMatches;
            sig.shaderProductionSemanticReviewBoundaryPreserved =
                productionSemanticReview.reviewValidated &&
                productionSemanticReview.review.boundaryPreserved &&
                !productionSemanticReview.review.objectBindingAuthorized &&
                !productionSemanticReview.review.nativeDrawPathActivationAllowed &&
                !productionSemanticReview.review.drawDispatchAuthorized;
            sig.shaderProductionSemanticReviewInputLayoutSnapshotToken =
                productionSemanticReview.reviewValidated
                    ? productionSemanticReview.review.inputLayoutSnapshotToken
                    : 0;
            sig.shaderProductionSemanticReviewTranslationSnapshotToken =
                productionSemanticReview.reviewValidated
                    ? productionSemanticReview.review.semanticTranslationSnapshotToken
                    : 0;
            sig.shaderProductionSemanticReviewSnapshotToken =
                productionSemanticReview.reviewValidated
                    ? productionSemanticReview.review.reviewSnapshotToken
                    : 0;

            // R293 does not manufacture production R258/R262 receipts from
            // descriptor-level census data. R294 now preserves the exact
            // source draw-call identity needed by the future R258 producer,
            // but native buffer mirrors/binding receipts are still not owned
            // here; keep explicit absence until that full producer exists.
            const NativeProgrammableShaderDormantSourceRevalidationReadiness*
                productionSourceRevalidation = nullptr;
            const NativeProgrammableShaderOutputResourceBehaviorReadiness*
                productionResourceBehavior = nullptr;
            const auto productionActivationPrerequisites =
                review_programmable_production_activation_prerequisites(
                    productionSemanticReview.review,
                    productionSourceRevalidation,
                    productionResourceBehavior);
            sig.shaderProductionActivationSourceReceiptPresent =
                productionActivationPrerequisites.
                    sourceRevalidationReceiptPresent;
            sig.shaderProductionActivationResourceReceiptPresent =
                productionActivationPrerequisites.
                    resourceBehaviorReceiptPresent;
            sig.shaderProductionActivationPrerequisiteExact =
                productionActivationPrerequisites.observationValidated;
            sig.shaderProductionActivationStaticPrerequisitesSatisfied =
                productionActivationPrerequisites.staticPrerequisitesSatisfied;
            sig.shaderProductionActivationBoundaryPreserved =
                productionActivationPrerequisites.boundaryPreserved;
            sig.shaderProductionActivationMissingReceiptMask =
                productionActivationPrerequisites.missingReceiptMask;
            sig.shaderProductionActivationPrerequisiteSnapshotToken =
                productionActivationPrerequisites.observationValidated
                    ? productionActivationPrerequisites.
                        observation.reviewSnapshotToken
                    : 0;
            return sig;
        }

        bool note_signature(
            const SourceSignature& sig,
            D3DPRIMITIVETYPE primitive) noexcept
        {
            const auto hash = hash_signature(sig, primitive);
            bool inserted = false;
            bool signatureHashCapHit = false;
            bool shaderCompileReadinessExact = false;
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
                else if (sig.fixedFunction &&
                    sig.fixedFunctionShaderPrototypeGenerated)
                {
                    shaderCompileReadinessExact =
                        FixedFunctionShaderCompileExactHashes.find(hash) !=
                        FixedFunctionShaderCompileExactHashes.end();
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

            FixedFunctionPixelShaderCompileProbe pixelCompileProbe{};
            FixedFunctionVertexShaderCompileProbe vertexCompileProbe{};
            // R221: detailed signature logging is intentionally bounded at 64,
            // but compile-readiness evidence must not inherit that presentation
            // cap. R223 strengthens the bounded probe to require both generated
            // fixed-function pipeline shaders for each tracked signature.
            if (inserted && sig.fixedFunction &&
                sig.fixedFunctionShaderPrototypeGenerated &&
                sig.fixedFunctionVertexShaderPrototypeGenerated)
            {
                std::array<D3DRESOURCETYPE, 8> textureTypes{};
                for (std::size_t stageIndex = 0;
                     stageIndex < sig.textureStages.size();
                     ++stageIndex)
                    textureTypes[stageIndex] =
                        sig.textureStages[stageIndex].type;

                const auto pixelPrototype =
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
                        },
                        sig.textureFactor);
                pixelCompileProbe =
                    compile_fixed_function_pixel_shader_prototype(
                        pixelPrototype);

                FixedFunctionVertexShaderPrototype vertexPrototype{};
                vertexPrototype.unsupported =
                    sig.fixedFunctionVertexShaderPrototypeUnsupported;
                vertexPrototype.sourceHash =
                    sig.fixedFunctionVertexShaderPrototypeHash;
                vertexPrototype.source =
                    sig.fixedFunctionVertexShaderPrototypeSource;
                vertexCompileProbe =
                    compile_fixed_function_vertex_shader_prototype(
                        vertexPrototype);

                const bool pipelineCompileSucceeded =
                    pixelCompileProbe.succeeded &&
                    vertexCompileProbe.succeeded;
                (pipelineCompileSucceeded
                    ? FixedFunctionShaderCompileSucceededSignatures
                    : FixedFunctionShaderCompileFailedSignatures).fetch_add(
                        1, std::memory_order_relaxed);
                if (pipelineCompileSucceeded)
                {
                    std::lock_guard<std::mutex> lock(SignatureMutex);
                    FixedFunctionShaderCompileExactHashes.insert(hash);
                    shaderCompileReadinessExact = true;
                }
            }
            else if (signatureHashCapHit && sig.fixedFunction &&
                sig.fixedFunctionShaderPrototypeGenerated &&
                sig.fixedFunctionVertexShaderPrototypeGenerated)
            {
                FixedFunctionShaderCompileSkippedSignatureCap.fetch_add(
                    1, std::memory_order_relaxed);
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
            else if (sig.shaderTranslationExact)
                ShaderTranslationExactSamples.fetch_add(
                    1, std::memory_order_relaxed);
            else if (sig.fixedFunction)
                ShaderFixedFunctionPendingSamples.fetch_add(
                    1, std::memory_order_relaxed);
            else
                ShaderProgrammablePendingSamples.fetch_add(
                    1, std::memory_order_relaxed);

            if (!sig.fixedFunction &&
                sig.vertexShader.present &&
                sig.pixelShader.present)
            {
                (sig.shaderSemanticTranslationPlanExact
                    ? ShaderSemanticPlanExactSamples
                    : ShaderSemanticPlanPendingSamples).fetch_add(
                        1, std::memory_order_relaxed);
                (sig.shaderTranslatedSemanticReceiptExact
                    ? ShaderSemanticReceiptExactSamples
                    : ShaderSemanticReceiptPendingSamples).fetch_add(
                        1, std::memory_order_relaxed);
            }

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
                if (!sig.fixedFunction &&
                    sig.vertexShader.present &&
                    sig.pixelShader.present)
                {
                    spdlog::info(
                        "VR DX11 R271 sourceSemanticPair: exact={} cacheKey=0x{:016X} pairHash=0x{:016X} vsRegisterHash=0x{:016X} psRegisterHash=0x{:016X} linkHash=0x{:016X} receiptRevision=0x{:016X} contract=0x{:016X}",
                        sig.shaderSourceSemanticPairExact ? 1 : 0,
                        sig.shaderSourceSemanticPairCacheKey,
                        sig.shaderSourceSemanticPairHash,
                        sig.shaderSourceVertexRegisterHash,
                        sig.shaderSourcePixelRegisterHash,
                        sig.shaderInterfaceLinkHash,
                        sig.shaderSourceSemanticReceiptRevisionHash,
                        sig.shaderSourceSemanticContractHash);
                    spdlog::info(
                        "VR DX11 R272 registerMappingPlan: exact={} constants={} samplers={} constantHash=0x{:016X} samplerHash=0x{:016X} planRevision=0x{:016X} contract=0x{:016X}",
                        sig.shaderRegisterMappingPlanExact ? 1 : 0,
                        sig.shaderConstantRegisterMappingCount,
                        sig.shaderSamplerMappingCount,
                        sig.shaderConstantRegisterMappingHash,
                        sig.shaderSamplerMappingHash,
                        sig.shaderRegisterMappingPlanRevisionHash,
                        sig.shaderRegisterMappingSemanticContractHash);
                    spdlog::info(
                        "VR DX11 R273 sourceMappingHandoff: exact={} snapshot=0x{:016X}",
                        sig.shaderSourceMappingHandoffExact ? 1 : 0,
                        sig.shaderSourceMappingHandoffSnapshotToken);
                    spdlog::info(
                        "VR DX11 R276 semanticTranslationPlan signature#{}: exact={} snapshot=0x{:016X} targetVS=0x{:016X} targetPS=0x{:016X} revision=0x{:016X} contract=0x{:016X}",
                        unique,
                        sig.shaderSemanticTranslationPlanExact ? 1 : 0,
                        sig.shaderSemanticTranslationPlanSnapshotToken,
                        sig.shaderTranslatedVertexSemanticHash,
                        sig.shaderTranslatedPixelSemanticHash,
                        sig.shaderTranslatorRevisionHash,
                        sig.shaderTranslationSemanticContractHash);
                    spdlog::info(
                        "VR DX11 R279 translationObjectPrerequisite signature#{}: exact={} cacheOwnerGen={} slotGen={} receiptGen={} sameDevicePair={} cacheSnapshot={} slotSnapshot={} cacheKey=0x{:016X} planSnapshot=0x{:016X} snapshot=0x{:016X}",
                        unique,
                        sig.shaderTranslationObjectPrerequisiteExact ? 1 : 0,
                        sig.shaderTranslationObjectCacheOwnerGenerationRequired ? 1 : 0,
                        sig.shaderTranslationObjectSlotGenerationRequired ? 1 : 0,
                        sig.shaderTranslationObjectReceiptGenerationRequired ? 1 : 0,
                        sig.shaderTranslationObjectSameDevicePairRequired ? 1 : 0,
                        sig.shaderTranslationObjectCacheSnapshotRequired ? 1 : 0,
                        sig.shaderTranslationObjectSlotSnapshotRequired ? 1 : 0,
                        sig.shaderSourceSemanticPairCacheKey,
                        sig.shaderSemanticTranslationPlanSnapshotToken,
                        sig.shaderTranslationObjectPrerequisiteSnapshotToken);
                    spdlog::info(
                        "VR DX11 R280 objectCreationHandoff signature#{}: exact={} vertexSource={} pixelSource={} ownershipPrerequisite={} createAuthorized={} cacheKey=0x{:016X} planSnapshot=0x{:016X} ownershipSnapshot=0x{:016X} snapshot=0x{:016X}",
                        unique,
                        sig.shaderObjectCreationHandoffExact ? 1 : 0,
                        sig.shaderObjectCreationHandoffVertexSourceExact ? 1 : 0,
                        sig.shaderObjectCreationHandoffPixelSourceExact ? 1 : 0,
                        sig.shaderObjectCreationHandoffOwnershipPrerequisiteMatches ? 1 : 0,
                        sig.shaderObjectCreationAuthorized ? 1 : 0,
                        sig.shaderSourceSemanticPairCacheKey,
                        sig.shaderSemanticTranslationPlanSnapshotToken,
                        sig.shaderTranslationObjectPrerequisiteSnapshotToken,
                        sig.shaderObjectCreationHandoffSnapshotToken);
                    spdlog::info(
                        "VR DX11 R281 translatedArtifactReceipt signature#{}: exact={} targetBytecodeRequired={} materialized={} createAuthorized={} cacheKey=0x{:016X} vertexIdentity=0x{:016X} pixelIdentity=0x{:016X} handoffSnapshot=0x{:016X} planSnapshot=0x{:016X} snapshot=0x{:016X}",
                        unique,
                        sig.shaderTranslatedArtifactReceiptExact ? 1 : 0,
                        sig.shaderTranslatedArtifactReceiptTargetBytecodeRequired ? 1 : 0,
                        sig.shaderTranslatedArtifactReceiptMaterialized ? 1 : 0,
                        sig.shaderTranslatedArtifactCreationAuthorized ? 1 : 0,
                        sig.shaderSourceSemanticPairCacheKey,
                        sig.shaderTranslatedVertexArtifactIdentity,
                        sig.shaderTranslatedPixelArtifactIdentity,
                        sig.shaderObjectCreationHandoffSnapshotToken,
                        sig.shaderSemanticTranslationPlanSnapshotToken,
                        sig.shaderTranslatedArtifactReceiptSnapshotToken);
                    spdlog::info(
                        "VR DX11 R282 targetMaterializationContract signature#{}: exact={} targetRequired={} materialized={} compileAuthorized={} createAuthorized={} cacheKey=0x{:016X} vertexContract=0x{:016X} pixelContract=0x{:016X} entry=0x{:016X} vsProfile=0x{:016X} psProfile=0x{:016X} flags=0x{:08X} artifactSnapshot=0x{:016X} planSnapshot=0x{:016X} snapshot=0x{:016X}",
                        unique,
                        sig.shaderTargetMaterializationContractExact ? 1 : 0,
                        sig.shaderTargetBytecodeMaterializationRequired ? 1 : 0,
                        sig.shaderTargetBytecodeMaterialized ? 1 : 0,
                        sig.shaderTargetCompilationAuthorized ? 1 : 0,
                        sig.shaderTargetObjectCreationAuthorized ? 1 : 0,
                        sig.shaderSourceSemanticPairCacheKey,
                        sig.shaderTargetVertexCompileContractIdentity,
                        sig.shaderTargetPixelCompileContractIdentity,
                        sig.shaderTargetEntryPointHash,
                        sig.shaderTargetVertexProfileHash,
                        sig.shaderTargetPixelProfileHash,
                        sig.shaderTargetCompileFlags,
                        sig.shaderTranslatedArtifactReceiptSnapshotToken,
                        sig.shaderSemanticTranslationPlanSnapshotToken,
                        sig.shaderTargetMaterializationContractSnapshotToken);
                    spdlog::info(
                        "VR DX11 R283 targetBytecodeMaterialization signature#{}: exact={} vertexSubset={} pixelSubset={} vertexCompiled={} pixelCompiled={} materialized={} createAuthorized={} cacheKey=0x{:016X} vertexSourceBytes={} pixelSourceBytes={} vertexSource=0x{:016X} pixelSource=0x{:016X} vertexBytes={} pixelBytes={} vertexBytecode=0x{:016X} pixelBytecode=0x{:016X} vertexArtifact=0x{:016X} pixelArtifact=0x{:016X} contractSnapshot=0x{:016X} artifactSnapshot=0x{:016X} planSnapshot=0x{:016X} snapshot=0x{:016X}",
                        unique,
                        sig.shaderTargetBytecodeMaterializationExact ? 1 : 0,
                        sig.shaderTargetVertexSubsetSupported ? 1 : 0,
                        sig.shaderTargetPixelSubsetSupported ? 1 : 0,
                        sig.shaderTargetVertexCompiled ? 1 : 0,
                        sig.shaderTargetPixelCompiled ? 1 : 0,
                        sig.shaderTargetR283BytecodeMaterialized ? 1 : 0,
                        sig.shaderTargetR283ObjectCreationAuthorized ? 1 : 0,
                        sig.shaderSourceSemanticPairCacheKey,
                        sig.shaderTargetVertexTranslatedSourceBytes,
                        sig.shaderTargetPixelTranslatedSourceBytes,
                        sig.shaderTargetVertexTranslatedSourceHash,
                        sig.shaderTargetPixelTranslatedSourceHash,
                        sig.shaderTargetVertexBytecodeBytes,
                        sig.shaderTargetPixelBytecodeBytes,
                        sig.shaderTargetVertexBytecodeHash,
                        sig.shaderTargetPixelBytecodeHash,
                        sig.shaderTargetVertexMaterializedArtifactIdentity,
                        sig.shaderTargetPixelMaterializedArtifactIdentity,
                        sig.shaderTargetMaterializationContractSnapshotToken,
                        sig.shaderTranslatedArtifactReceiptSnapshotToken,
                        sig.shaderSemanticTranslationPlanSnapshotToken,
                        sig.shaderTargetBytecodeMaterializationSnapshotToken);
                    spdlog::info(
                        "VR DX11 R287 productionObservation signature#{}: exact={} ownerGeneration={} materializationReused={} objectReady={} boundaryPreserved={} handoffSnapshot=0x{:016X} snapshot=0x{:016X}",
                        unique,
                        sig.shaderProductionObservationExact ? 1 : 0,
                        sig.shaderProductionObservationOwnerGeneration,
                        sig.shaderProductionObservationMaterializationReused ? 1 : 0,
                        sig.shaderProductionObservationObjectReady ? 1 : 0,
                        sig.shaderProductionObservationBoundaryPreserved ? 1 : 0,
                        sig.shaderProductionSemanticHandoffSnapshotToken,
                        sig.shaderProductionObservationSnapshotToken);
                    spdlog::info(
                        "VR DX11 R291 productionSemanticReview signature#{}: admissionExact={} reviewExact={} inputLayoutReady={} inputLayoutReused={} semanticReady={} boundaryPreserved={} admissionSnapshot=0x{:016X} inputLayoutSnapshot=0x{:016X} semanticSnapshot=0x{:016X} reviewSnapshot=0x{:016X}",
                        unique,
                        sig.shaderTranslationAdmissionExact ? 1 : 0,
                        sig.shaderProductionSemanticReviewExact ? 1 : 0,
                        sig.shaderProductionSemanticReviewInputLayoutReady ? 1 : 0,
                        sig.shaderProductionSemanticReviewInputLayoutReused ? 1 : 0,
                        sig.shaderProductionSemanticReviewTranslationReady ? 1 : 0,
                        sig.shaderProductionSemanticReviewBoundaryPreserved ? 1 : 0,
                        sig.shaderTranslationAdmissionSnapshotToken,
                        sig.shaderProductionSemanticReviewInputLayoutSnapshotToken,
                        sig.shaderProductionSemanticReviewTranslationSnapshotToken,
                        sig.shaderProductionSemanticReviewSnapshotToken);
                    spdlog::info(
                        "VR DX11 R297 productionSourceRevalidation signature#{}: drawExact={} nativeBufferEligible={} r258Present={} r258Contract={} kindMatch={} startMatch={} countDerivable={} countMatch={} elementCount={} indexFormatKnown={} indexFormatMatch={} indexOffsetMatch={} indexFormat={} baseMatch={} minMatch={} numMatch={} rangeMatch={} cacheMatch={} joinExact={} boundaryPreserved={} missingEvidenceMask=0x{:08X} r258Snapshot=0x{:016X} joinSnapshot=0x{:016X}",
                        unique,
                        sig.shaderProductionSourceDrawIdentityExact ? 1 : 0,
                        sig.shaderProductionSourceNativeBufferEligible ? 1 : 0,
                        sig.shaderProductionSourceReceiptPresent ? 1 : 0,
                        sig.shaderProductionSourceReceiptContractReady ? 1 : 0,
                        sig.shaderProductionSourceKindMatches ? 1 : 0,
                        sig.shaderProductionSourceStartMatches ? 1 : 0,
                        sig.shaderProductionSourceElementCountDerivable ? 1 : 0,
                        sig.shaderProductionSourceElementCountMatches ? 1 : 0,
                        sig.shaderProductionSourceElementCount,
                        sig.shaderProductionSourceIndexFormatKnown ? 1 : 0,
                        sig.shaderProductionSourceIndexFormatMatches ? 1 : 0,
                        sig.shaderProductionSourceIndexOffsetMatches ? 1 : 0,
                        static_cast<unsigned>(
                            sig.shaderProductionSourceIndexFormat),
                        sig.shaderProductionSourceBaseVertexMatches ? 1 : 0,
                        sig.shaderProductionSourceMinVertexMatches ? 1 : 0,
                        sig.shaderProductionSourceNumVerticesMatches ? 1 : 0,
                        sig.shaderProductionSourceRangeMatches ? 1 : 0,
                        sig.shaderProductionSourceCacheKeyMatches ? 1 : 0,
                        sig.shaderProductionSourceJoinExact ? 1 : 0,
                        sig.shaderProductionSourceBoundaryPreserved ? 1 : 0,
                        sig.shaderProductionSourceMissingEvidenceMask,
                        sig.shaderProductionSourceReceiptSnapshotToken,
                        sig.shaderProductionSourceJoinSnapshotToken);
                    spdlog::info(
                        "VR DX11 R293 productionPrerequisiteCensus signature#{}: sourceReceipt={} resourceReceipt={} r292Exact={} staticSatisfied={} boundaryPreserved={} missingReceiptMask=0x{:08X} snapshot=0x{:016X}",
                        unique,
                        sig.shaderProductionActivationSourceReceiptPresent ? 1 : 0,
                        sig.shaderProductionActivationResourceReceiptPresent ? 1 : 0,
                        sig.shaderProductionActivationPrerequisiteExact ? 1 : 0,
                        sig.shaderProductionActivationStaticPrerequisitesSatisfied ? 1 : 0,
                        sig.shaderProductionActivationBoundaryPreserved ? 1 : 0,
                        sig.shaderProductionActivationMissingReceiptMask,
                        sig.shaderProductionActivationPrerequisiteSnapshotToken);
                    spdlog::info(
                        "VR DX11 R275 translatedSemanticReceipt signature#{}: exact={} objectReady={} snapshot=0x{:016X}",
                        unique,
                        sig.shaderTranslatedSemanticReceiptExact ? 1 : 0,
                        sig.shaderTranslatedSemanticReceiptObjectReady ? 1 : 0,
                        sig.shaderTranslatedSemanticReceiptSnapshotToken);

                    // R317: independent scalar-hash reconstruction only.
                    // These diagnostic values do not certify object ownership
                    // and never grant programmable native Draw* authority.
                    const auto& receipt =
                        sig.shaderTranslatedSemanticReceiptEvidence;
                    spdlog::info(
                        "VR DX11 R317 receiptInputs signature#{}: cacheKey=0x{:016X} vertexVersionToken=0x{:016X} pixelVersionToken=0x{:016X} vertexBytecodeHash=0x{:016X} pixelBytecodeHash=0x{:016X} translatedVertexSemanticHash=0x{:016X} translatedPixelSemanticHash=0x{:016X} translatorRevisionHash=0x{:016X} semanticContractHash=0x{:016X} sourcePairSemanticHash=0x{:016X} sourceConstantMappingHash=0x{:016X} sourceSamplerMappingHash=0x{:016X} sourceMappingPlanRevisionHash=0x{:016X} sourceMappingSemanticContractHash=0x{:016X} translationObjectSnapshotToken=0x{:016X} sourceMappingHandoffSnapshotToken=0x{:016X} translationPlanSnapshotToken=0x{:016X} vertexSemanticExact={} pixelSemanticExact={} constantRegisterMappingExact={} samplerMappingExact={}",
                        unique,
                        receipt.cacheKey,
                        receipt.vertexVersionToken,
                        receipt.pixelVersionToken,
                        receipt.vertexBytecodeHash,
                        receipt.pixelBytecodeHash,
                        receipt.translatedVertexSemanticHash,
                        receipt.translatedPixelSemanticHash,
                        receipt.translatorRevisionHash,
                        receipt.semanticContractHash,
                        receipt.sourcePairSemanticHash,
                        receipt.sourceConstantMappingHash,
                        receipt.sourceSamplerMappingHash,
                        receipt.sourceMappingPlanRevisionHash,
                        receipt.sourceMappingSemanticContractHash,
                        receipt.translationObjectSnapshotToken,
                        receipt.sourceMappingHandoffSnapshotToken,
                        receipt.translationPlanSnapshotToken,
                        receipt.vertexSemanticExact ? 1 : 0,
                        receipt.pixelSemanticExact ? 1 : 0,
                        receipt.constantRegisterMappingExact ? 1 : 0,
                        receipt.samplerMappingExact ? 1 : 0);
                }
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

                spdlog::info(
                    "VR DX11 R167 dither state#{}: observed={} enable={}",
                    unique,
                    sig.ditherObservationComplete ? 1 : 0,
                    sig.ditherEnable != FALSE ? 1 : 0);
                spdlog::info(
                    "VR DX11 R172 multisample-raster state#{}: observed={} enable={}",
                    unique,
                    sig.multisampleRasterObservationComplete ? 1 : 0,
                    sig.multiSampleAntialias != FALSE ? 1 : 0);
                spdlog::info(
                    "VR DX11 R205 line-raster state#{}: observed={} lastPixel={} antialiased={}",
                    unique,
                    sig.lineRasterObservationComplete ? 1 : 0,
                    sig.lastPixel != FALSE ? 1 : 0,
                    sig.antialiasedLineEnable != FALSE ? 1 : 0);
                spdlog::info(
                    "VR DX11 R179 output state#{}: observed={} scissorEnable={} blendFactor=0x{:08X} sampleMask=0x{:08X} viewport=[{},{},{},{},minZBits=0x{:08X},maxZBits=0x{:08X}] scissor=[{},{},{},{}]",
                    unique,
                    sig.outputStateObservationComplete ? 1 : 0,
                    sig.outputScissorTestEnable != FALSE ? 1 : 0,
                    sig.outputBlendFactor,
                    sig.outputMultiSampleMask,
                    sig.outputViewport.X,
                    sig.outputViewport.Y,
                    sig.outputViewport.Width,
                    sig.outputViewport.Height,
                    float_bits(sig.outputViewport.MinZ),
                    float_bits(sig.outputViewport.MaxZ),
                    sig.outputScissorRect.left,
                    sig.outputScissorRect.top,
                    sig.outputScissorRect.right,
                    sig.outputScissorRect.bottom);
                spdlog::info(
                    "VR DX11 R170 texture-coordinate wrap state#{}: observed={} wrap=[{},{},{},{},{},{},{},{}]",
                    unique,
                    sig.textureCoordinateWrapObservationComplete ? 1 : 0,
                    sig.textureCoordinateWrap[0], sig.textureCoordinateWrap[1],
                    sig.textureCoordinateWrap[2], sig.textureCoordinateWrap[3],
                    sig.textureCoordinateWrap[4], sig.textureCoordinateWrap[5],
                    sig.textureCoordinateWrap[6], sig.textureCoordinateWrap[7]);

                spdlog::info(
                    "VR DX11 R175 stream0-frequency state#{}: frequency=0x{:08X}",
                    unique,
                    sig.stream0Frequency);
                spdlog::info(
                    "VR DX11 R212 RT0 color-write state#{}: observed={} mask=0x{:08X}",
                    unique,
                    sig.rt0ColorWriteObservationComplete ? 1 : 0,
                    sig.colorWriteEnable);
                spdlog::info(
                    "VR DX11 MRT color-write state#{}: observed={} masks=[0x{:08X},0x{:08X},0x{:08X}]",
                    unique,
                    sig.mrtColorWriteObservationComplete ? 1 : 0,
                    sig.additionalColorWriteEnable[0],
                    sig.additionalColorWriteEnable[1],
                    sig.additionalColorWriteEnable[2]);

                spdlog::info(
                    "VR DX11 R174 source MRT state#{}: observed={} mask=0x{:02X}",
                    unique,
                    sig.auxiliaryRenderTargetObservationComplete ? 1 : 0,
                    sig.auxiliaryRenderTargetMask);
                spdlog::info(
                    "VR DX11 R177 surface MSAA state#{}: rt[present={},type={},quality={}] depth[present={},type={},quality={}] unsupported={}",
                    unique,
                    sig.renderTargetPresent ? 1 : 0,
                    static_cast<int>(sig.renderTargetMultiSampleType),
                    sig.renderTargetMultiSampleQuality,
                    sig.depthPresent ? 1 : 0,
                    static_cast<int>(sig.depthMultiSampleType),
                    sig.depthMultiSampleQuality,
                    ((sig.renderTargetPresent &&
                      (sig.renderTargetMultiSampleType != D3DMULTISAMPLE_NONE ||
                       sig.renderTargetMultiSampleQuality != 0)) ||
                     (sig.depthPresent &&
                      (sig.depthMultiSampleType != D3DMULTISAMPLE_NONE ||
                       sig.depthMultiSampleQuality != 0))) ? 1 : 0);

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
                        "VR DX11 R191 ffp texture-factor state#{}: observed={} argb=0x{:08X}",
                        unique,
                        sig.textureFactorObservationComplete ? 1 : 0,
                        sig.textureFactor);

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

                    spdlog::info(
                        "VR DX11 R164 depth-bias state#{}: observed={} constantBits=0x{:08X} slopeBits=0x{:08X}",
                        unique,
                        sig.depthBiasObservationComplete ? 1 : 0,
                        sig.depthBiasBits,
                        sig.slopeScaleDepthBiasBits);

                    spdlog::info(
                        "VR DX11 R169 point-raster state#{}: observed={} sizeBits=0x{:08X} minBits=0x{:08X} maxBits=0x{:08X} sprite={} scale={} scaleBits[A=0x{:08X},B=0x{:08X},C=0x{:08X}]",
                        unique,
                        sig.pointRasterObservationComplete ? 1 : 0,
                        sig.pointSizeBits,
                        sig.pointSizeMinBits,
                        sig.pointSizeMaxBits,
                        sig.pointSpriteEnable != FALSE ? 1 : 0,
                        sig.pointScaleEnable != FALSE ? 1 : 0,
                        sig.pointScaleABits,
                        sig.pointScaleBBits,
                        sig.pointScaleCBits);

                    if (sig.fixedFunctionShaderPrototypeGenerated)
                    {
                        spdlog::info(
                            "VR DX11 R85 ffp shader compile#{}: attempted={} succeeded={} hr=0x{:08X} bytecodeHash=0x{:016X} bytecodeBytes={} diagnosticsHash=0x{:016X} diagnosticsBytes={} profile=ps_4_0",
                            unique,
                            pixelCompileProbe.attempted ? 1 : 0,
                            pixelCompileProbe.succeeded ? 1 : 0,
                            static_cast<std::uint32_t>(
                                pixelCompileProbe.result),
                            pixelCompileProbe.bytecodeHash,
                            pixelCompileProbe.bytecodeBytes,
                            pixelCompileProbe.diagnosticsHash,
                            pixelCompileProbe.diagnosticsBytes);
                    }
                    if (sig.fixedFunctionVertexShaderPrototypeGenerated)
                    {
                        spdlog::info(
                            "VR DX11 R223 ffp vertex shader compile#{}: attempted={} succeeded={} hr=0x{:08X} bytecodeHash=0x{:016X} bytecodeBytes={} diagnosticsHash=0x{:016X} diagnosticsBytes={} profile=vs_4_0",
                            unique,
                            vertexCompileProbe.attempted ? 1 : 0,
                            vertexCompileProbe.succeeded ? 1 : 0,
                            static_cast<std::uint32_t>(
                                vertexCompileProbe.result),
                            vertexCompileProbe.bytecodeHash,
                            vertexCompileProbe.bytecodeBytes,
                            vertexCompileProbe.diagnosticsHash,
                            vertexCompileProbe.diagnosticsBytes);
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
                            "VR DX11 R197 ffp signature#{} stage#{}: color[op={},arg0=0x{:08X},arg1=0x{:08X},arg2=0x{:08X}] alpha[op={},arg0=0x{:08X},arg1=0x{:08X},arg2=0x{:08X}] constant=0x{:08X} resultArg=0x{:08X} texCoord=0x{:08X} texTransform=0x{:08X} sampler[min={},mag={},mip={},u={},v={},border=0x{:08X},srgb={}]",
                            unique,
                            stageIndex,
                            stage.colorOp,
                            stage.colorArg0,
                            stage.colorArg1,
                            stage.colorArg2,
                            stage.alphaOp,
                            stage.alphaArg0,
                            stage.alphaArg1,
                            stage.alphaArg2,
                            stage.stageConstant,
                            stage.resultArg,
                            stage.texCoordIndex,
                            stage.textureTransformFlags,
                            stage.minFilter,
                            stage.magFilter,
                            stage.mipFilter,
                            stage.addressU,
                            stage.addressV,
                            stage.borderColor,
                            stage.srgbTexture);
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

            // R222 fail-closed concurrency rule: an existing signature observed
            // before another thread finishes its first compile probe remains
            // non-exact for that sample. A later sample may reuse the cached
            // successful result; failed or hash-cap-skipped signatures never do.
            return shaderCompileReadinessExact;
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
                "VR DX11 R120 census: samples={} exact={} fixedFn={} programmable={} topologyUnsupported={} rasterSemantics[pointUnsupported={},lineUnsupported={}] signatures={} sampling[drawsSeen={},stride={},scheme={}] signatureCaps[hashCap={},hashCapHitSamples={},detailCap={},detailSkipped={}] declSamples={} indexedSamples={} texturedSamples={} resourceExact[introspectionFailure={},behaviorUnsupported={},mutationTelemetryRequired={},managedShadowRequired={},indexUnsupported={},textureUnsupported={},colorUnsupported={},depthUnsupported={},auxRenderTargetUnsupported={}] mutation[writeUnlocks={},readOnlyUnlocks={},discardWriteUnlocks={},noOverwriteWriteUnlocks={}] mutationPlan[exact={},unsupported={},managedShadow={},mapWrite={},mapDiscard={},mapNoOverwrite={},updateSubresource={}] textureMutation[writeUnlocks={},readOnlyUnlocks={},descriptorFailures={},updateTextureSuccesses={},updateTextureFailures={},updateSurfaceSuccesses={},updateSurfaceFailures={}] managedLifetime[shadowWrites={},shadowReads={},resetSuccesses={},shadowPreserved={},deviceGeneration={},shadowVersion={},mirrorGeneration={},mirrorVersion={},mirrorReady={}] managedTextureShadow[requiredSamples={},readySamples={},pendingSamples={}] managedTextureMutationSource[updateTextureInvalidations={},updateSurfaceInvalidations={}] inputLayout[exact={},unsupported={},fvfExact={},fvfPending={}] shaderReadiness[introspectionFailure={},mixedPair={},translationExact={},fixedFunctionPending={},programmablePending={}] programmableSemantic[planExact={},planPending={},receiptExact={},receiptPending={}] ffpCoverage[exact={},queryFailure={}] ffpReadiness[ready={},pending={}] ffpPipelineShader[exact={},pending={},alphaTestOwned={}] ffpShaderPrototype[generated={},pending={}] ffpShaderCompile[succeeded={},failed={},skippedCap={}] textureStageResource[bound={},exact={},pending={}] textureStageManagedShadow[required={},ready={},pending={}] dualSourceBlend[any={},rgbSrc={},rgbDst={},alphaSrc={},alphaDst={}] unsupported[incomplete={},wbuffer={},sepAlpha={},alphaTest={},stencil={},fog={},lighting={},srgb={},fill={},blend={},depthCmp={},cull={},dualSource={},shadeMode={},clipping={},depthBias={},vertexBlend={},dither={},texCoordWrap={},mrtColorWrite={},specular={}]",
                Samples.load(std::memory_order_relaxed),
                ExactSamples.load(std::memory_order_relaxed),
                FixedFunctionSamples.load(std::memory_order_relaxed),
                ProgrammableSamples.load(std::memory_order_relaxed),
                UnsupportedTopologySamples.load(std::memory_order_relaxed),
                PointRasterUnsupportedSamples.load(std::memory_order_relaxed),
                LineRasterUnsupportedSamples.load(std::memory_order_relaxed),
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
                UnsupportedAuxiliaryRenderTargetSamples.load(
                    std::memory_order_relaxed),
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
                ShaderTranslationExactSamples.load(std::memory_order_relaxed),
                ShaderFixedFunctionPendingSamples.load(std::memory_order_relaxed),
                ShaderProgrammablePendingSamples.load(std::memory_order_relaxed),
                ShaderSemanticPlanExactSamples.load(std::memory_order_relaxed),
                ShaderSemanticPlanPendingSamples.load(std::memory_order_relaxed),
                ShaderSemanticReceiptExactSamples.load(std::memory_order_relaxed),
                ShaderSemanticReceiptPendingSamples.load(std::memory_order_relaxed),
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
                DualSourceBlendSamples.load(std::memory_order_relaxed),
                DualSourceRgbSourceSamples.load(std::memory_order_relaxed),
                DualSourceRgbDestSamples.load(std::memory_order_relaxed),
                DualSourceAlphaSourceSamples.load(std::memory_order_relaxed),
                DualSourceAlphaDestSamples.load(std::memory_order_relaxed),
                unsupported[0], unsupported[1], unsupported[2], unsupported[3],
                unsupported[4], unsupported[5], unsupported[6], unsupported[7],
                unsupported[8], unsupported[9], unsupported[10], unsupported[11],
                unsupported[12], unsupported[13], unsupported[14], unsupported[15],
                unsupported[16], unsupported[17], unsupported[18],
                unsupported[19], unsupported[20]);
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
        {
            std::lock_guard<std::mutex> lock(
                NativeProgrammableObservationMutex);
            NativeProgrammableObservationBackend.shutdown();
            NativeProgrammableObservationSourceDevice = nullptr;
        }
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
        const SourceDrawObservation& draw) noexcept
    {
        if (!device || !census_enabled())
            return;

        auto sampledDraw = draw;
        const auto primitive = sampledDraw.primitive;

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

        if (sampledDraw.kind == SourceDrawKind::Indexed)
        {
            IDirect3DIndexBuffer9* indexBuffer = nullptr;
            if (SUCCEEDED(device->GetIndices(&indexBuffer)) && indexBuffer)
            {
                D3DINDEXBUFFER_DESC indexDesc{};
                if (SUCCEEDED(indexBuffer->GetDesc(&indexDesc)) &&
                    (indexDesc.Format == D3DFMT_INDEX16 ||
                     indexDesc.Format == D3DFMT_INDEX32))
                    sampledDraw.indexFormat = indexDesc.Format;
                indexBuffer->Release();
            }
        }

        OutRunVR::DrawState::RenderStateSnapshot source{};
        const bool captured =
            OutRunVRStereo::CaptureTrackedRenderStateSnapshot(device, source);

        const bool blendStateObserved =
            captured && source.complete && source.alphaBlendEnable != FALSE;
        const bool dualSourceRgbSource =
            blendStateObserved && is_src1_blend_factor(source.srcBlend);
        const bool dualSourceRgbDest =
            blendStateObserved && is_src1_blend_factor(source.destBlend);
        const bool separateAlphaObserved =
            blendStateObserved && source.separateAlphaBlendEnable != FALSE;
        const bool dualSourceAlphaSource =
            separateAlphaObserved &&
            is_src1_blend_factor(source.srcBlendAlpha);
        const bool dualSourceAlphaDest =
            separateAlphaObserved &&
            is_src1_blend_factor(source.destBlendAlpha);
        const bool dualSourceBlend =
            dualSourceRgbSource || dualSourceRgbDest ||
            dualSourceAlphaSource || dualSourceAlphaDest;

        if (dualSourceBlend)
            DualSourceBlendSamples.fetch_add(1, std::memory_order_relaxed);
        if (dualSourceRgbSource)
            DualSourceRgbSourceSamples.fetch_add(1, std::memory_order_relaxed);
        if (dualSourceRgbDest)
            DualSourceRgbDestSamples.fetch_add(1, std::memory_order_relaxed);
        if (dualSourceAlphaSource)
            DualSourceAlphaSourceSamples.fetch_add(1, std::memory_order_relaxed);
        if (dualSourceAlphaDest)
            DualSourceAlphaDestSamples.fetch_add(1, std::memory_order_relaxed);

        const auto translated = translate_pipeline(source);
        const auto topology = translate_primitive(primitive);

        Samples.fetch_add(1, std::memory_order_relaxed);
        std::uint32_t unsupported = translated.unsupported;
        if (!captured)
            unsupported |= PipelineUnsupportedIncompleteSnapshot;
        note_unsupported(unsupported);

        if (!topology.exact)
            UnsupportedTopologySamples.fetch_add(1, std::memory_order_relaxed);

        // R211 mirrors the existing dormant direct-dispatch semantic gates.
        // D3D11 POINTLIST does not reproduce D3D9 fixed-function point size /
        // sprite behavior, and D3D10+ has no D3DRS_LASTPIXEL equivalent for
        // line endpoint coverage. Keep these samples out of ExactSamples even
        // though their IA topology enum itself has a direct D3D11 mapping.
        const bool pointRasterSemanticsExact =
            primitive != D3DPT_POINTLIST;
        const bool lineRasterSemanticsExact =
            primitive != D3DPT_LINELIST && primitive != D3DPT_LINESTRIP;
        if (!pointRasterSemanticsExact)
            PointRasterUnsupportedSamples.fetch_add(
                1, std::memory_order_relaxed);
        if (!lineRasterSemanticsExact)
            LineRasterUnsupportedSamples.fetch_add(
                1, std::memory_order_relaxed);

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

        const FixedFunctionLightingState fixedFunctionLighting{
            captured && source.complete,
            source.lighting,
        };
        auto signature = inspect_source_signature(
            device,
            fixedFunction,
            vs,
            ps,
            shaderQueryComplete,
            fixedFunctionLighting);
        if (vs) vs->Release();
        if (ps) ps->Release();

        // R294 captures call-site geometry identity only for programmable
        // pairs. Fixed-function signature cardinality and its compile cache are
        // intentionally unchanged. UP draws retain exact call identity but are
        // never eligible to stand in for native managed-buffer evidence.
        if (programmablePair)
        {
            signature.sourceDraw = sampledDraw;
            signature.sourceDrawIdentityExact =
                source_draw_identity_exact(sampledDraw);
            signature.sourceDrawNativeBufferEligible =
                signature.sourceDrawIdentityExact &&
                sampledDraw.native_buffer_eligible();
            signature.sourceDrawIdentitySnapshotToken =
                signature.sourceDrawIdentityExact
                    ? source_draw_identity_snapshot_token(sampledDraw)
                    : 0;

            // R295 deliberately receives no R258 receipt until a production
            // owner can provide the exact D3D11 context/buffer lineage. The
            // bridge still seals the expected R294 -> R258 join contract now,
            // preventing a later producer from substituting a receipt from a
            // different draw kind/start location or shader-pair cache identity.
            const NativeProgrammableShaderDormantSourceRevalidationReadiness*
                productionSourceRevalidation = nullptr;
            const auto productionSourceJoin =
                review_programmable_production_source_revalidation(
                    signature.sourceDraw,
                    signature.sourceDrawIdentitySnapshotToken,
                    signature.shaderSourceSemanticPairCacheKey,
                    productionSourceRevalidation);
            signature.shaderProductionSourceDrawIdentityExact =
                productionSourceJoin.sourceDrawIdentityExact;
            signature.shaderProductionSourceNativeBufferEligible =
                productionSourceJoin.sourceDrawNativeBufferEligible;
            signature.shaderProductionSourceReceiptPresent =
                productionSourceJoin.sourceRevalidationReceiptPresent;
            signature.shaderProductionSourceReceiptContractReady =
                productionSourceJoin.sourceRevalidationReceiptContractReady;
            signature.shaderProductionSourceKindMatches =
                productionSourceJoin.sourceKindMatches;
            signature.shaderProductionSourceStartMatches =
                productionSourceJoin.sourceStartMatches;
            signature.shaderProductionSourceElementCountDerivable =
                productionSourceJoin.sourceElementCountDerivable;
            signature.shaderProductionSourceElementCountMatches =
                productionSourceJoin.sourceElementCountMatches;
            signature.shaderProductionSourceElementCount =
                productionSourceJoin.sourceElementCount;
            signature.shaderProductionSourceIndexFormatKnown =
                productionSourceJoin.sourceIndexFormatKnown;
            signature.shaderProductionSourceIndexFormatMatches =
                productionSourceJoin.sourceIndexFormatMatches;
            signature.shaderProductionSourceIndexOffsetMatches =
                productionSourceJoin.sourceIndexOffsetMatches;
            signature.shaderProductionSourceIndexFormat =
                productionSourceJoin.sourceIndexFormat;
            signature.shaderProductionSourceBaseVertexMatches =
                productionSourceJoin.sourceBaseVertexMatches;
            signature.shaderProductionSourceMinVertexMatches =
                productionSourceJoin.sourceMinVertexMatches;
            signature.shaderProductionSourceNumVerticesMatches =
                productionSourceJoin.sourceNumVerticesMatches;
            signature.shaderProductionSourceRangeMatches =
                productionSourceJoin.sourceRangeMatches;
            signature.shaderProductionSourceCacheKeyMatches =
                productionSourceJoin.cacheIdentityMatches;
            signature.shaderProductionSourceJoinExact =
                productionSourceJoin.joinValidated;
            signature.shaderProductionSourceBoundaryPreserved =
                productionSourceJoin.boundaryPreserved;
            signature.shaderProductionSourceMissingEvidenceMask =
                productionSourceJoin.missingEvidenceMask;
            signature.shaderProductionSourceReceiptSnapshotToken =
                productionSourceJoin.sourceRevalidationSnapshotToken;
            signature.shaderProductionSourceJoinSnapshotToken =
                productionSourceJoin.reviewSnapshotToken;
        }

        signature.shadeModeObservationComplete =
            captured && source.complete;
        signature.shadeMode = source.shadeMode;
        signature.vertexBlendObservationComplete =
            captured && source.complete;
        signature.vertexBlend = source.vertexBlend;
        signature.indexedVertexBlendEnable = source.indexedVertexBlendEnable;
        signature.depthBiasObservationComplete =
            captured && source.complete;
        signature.depthBiasBits = source.depthBiasBits;
        signature.slopeScaleDepthBiasBits = source.slopeScaleDepthBiasBits;
        signature.ditherObservationComplete =
            captured && source.complete;
        signature.ditherEnable = source.ditherEnable;
        signature.multisampleRasterObservationComplete =
            captured && source.complete;
        signature.multiSampleAntialias = source.multiSampleAntialias;
        signature.lineRasterObservationComplete =
            captured && source.complete;
        signature.lastPixel = source.lastPixel;
        signature.antialiasedLineEnable = source.antialiasedLineEnable;
        signature.outputStateObservationComplete =
            captured && source.complete && source.outputStateComplete;
        signature.outputBlendFactor = source.blendFactor;
        signature.outputMultiSampleMask = source.multiSampleMask;
        signature.outputViewport = source.viewport;
        signature.outputScissorRect = source.scissorRect;
        signature.outputScissorTestEnable = source.scissorTestEnable;
        signature.textureFactorObservationComplete =
            captured && source.complete;
        signature.textureFactor = source.textureFactor;
        signature.pointRasterObservationComplete =
            captured && source.complete;
        signature.pointSizeBits = source.pointSizeBits;
        signature.pointSizeMinBits = source.pointSizeMinBits;
        signature.pointSizeMaxBits = source.pointSizeMaxBits;
        signature.pointSpriteEnable = source.pointSpriteEnable;
        signature.pointScaleEnable = source.pointScaleEnable;
        signature.pointScaleABits = source.pointScaleABits;
        signature.pointScaleBBits = source.pointScaleBBits;
        signature.pointScaleCBits = source.pointScaleCBits;
        signature.textureCoordinateWrapObservationComplete =
            captured && source.complete;
        signature.textureCoordinateWrap = source.textureCoordinateWrap;
        signature.rt0ColorWriteObservationComplete =
            captured && source.complete;
        signature.colorWriteEnable = source.colorWriteEnable;
        signature.mrtColorWriteObservationComplete =
            captured && source.complete;
        signature.additionalColorWriteEnable =
            source.additionalColorWriteEnable;
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

        bool resourcesExact = signature.resourceIntrospectionComplete;
        if (!signature.resourceIntrospectionComplete)
            ResourceIntrospectionFailureSamples.fetch_add(
                1, std::memory_order_relaxed);

        if (signature.auxiliaryRenderTargetMask != 0)
        {
            UnsupportedAuxiliaryRenderTargetSamples.fetch_add(
                1, std::memory_order_relaxed);
            resourcesExact = false;
        }

        const bool streamSourceFrequencyUnsupported =
            signature.stream0Frequency != 1u;
        // R177 mirrors NativeSurfaceMirror::source_descriptor_exact(): D3D9
        // multisample type/quality are not assumed to map exactly to DXGI.
        const bool surfaceMultisampleUnsupported =
            (signature.renderTargetPresent &&
             (signature.renderTargetMultiSampleType != D3DMULTISAMPLE_NONE ||
              signature.renderTargetMultiSampleQuality != 0)) ||
            (signature.depthPresent &&
             (signature.depthMultiSampleType != D3DMULTISAMPLE_NONE ||
              signature.depthMultiSampleQuality != 0));

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

        if (!behaviorDescriptorExact || streamSourceFrequencyUnsupported ||
            surfaceMultisampleUnsupported)
            ResourceBehaviorUnsupportedSamples.fetch_add(
                1, std::memory_order_relaxed);
        if (mutationTelemetryRequired)
            ResourceMutationTelemetryRequiredSamples.fetch_add(
                1, std::memory_order_relaxed);
        if (managedShadowRequired)
            ResourceManagedShadowRequiredSamples.fetch_add(
                1, std::memory_order_relaxed);

        // R219 keeps the F18 descriptor/mutation/lifetime boundary explicit
        // on each sampled signature. This does not promote mutation telemetry
        // or managed shadows to exact; those remain independent blockers.
        signature.resourceBehaviorDescriptorExact = behaviorDescriptorExact;
        signature.resourceMutationTelemetryRequired =
            mutationTelemetryRequired;
        signature.resourceManagedShadowRequired = managedShadowRequired;
        signature.resourceBehaviorExact =
            behaviorDescriptorExact &&
            !mutationTelemetryRequired &&
            !managedShadowRequired &&
            !streamSourceFrequencyUnsupported &&
            !surfaceMultisampleUnsupported;

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
        if (!signature.resourceBehaviorExact)
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

            // R215 closes the original R80 fixed-function census gap without
            // promoting programmable D3D9 shaders or activating native draw.
            // The dormant native pipeline consumes these same generated VS/PS
            // and transform contracts, while input/resource/output readiness
            // remain independent ExactSamples gates below.
            signature.shaderTranslationExact =
                signature.shaderIntrospectionComplete &&
                !signature.shaderMixedPair &&
                signature.fixedFunctionPipelineShaderExact &&
                signature.fixedFunctionVertexShaderPrototypeGenerated &&
                signature.fixedFunctionTransformExact;
        }

        // R220 closes the remaining F21 scope hazard: the sampled readiness
        // identity must explicitly prove the currently supported fixed-function
        // shader path. A future programmable translator cannot silently inherit
        // ExactSamples by widening shaderTranslationExact alone.
        signature.shaderReadinessExact =
            signature.shaderIntrospectionComplete &&
            !signature.shaderMixedPair &&
            signature.fixedFunction &&
            signature.shaderTranslationExact;

        const bool shaderCompileReadinessExact =
            note_signature(signature, primitive);

        // R218 keeps the final ExactSamples boundary explicitly tied to the
        // complete fixed-function stage/sampler readiness contract. R215's
        // shaderTranslationExact currently depends on the same readiness, but
        // retaining the observation/readiness gates here prevents a later
        // shader-translation widening from silently promoting incomplete FFP
        // samples. Programmable D3D9 shaders and native draw remain dormant.
        if (unsupported == PipelineUnsupportedNone && topology.exact &&
            pointRasterSemanticsExact && lineRasterSemanticsExact &&
            signature.fixedFunction &&
            signature.fixedFunctionStateCoverageExact &&
            signature.fixedFunctionTranslationReady &&
            signature.resourceBehaviorExact &&
            resourcesExact && inputLayoutExact &&
            signature.outputStateObservationComplete &&
            signature.shaderReadinessExact &&
            shaderCompileReadinessExact &&
            signature.shaderTranslationExact)
            ExactSamples.fetch_add(1, std::memory_order_relaxed);

        maybe_log();
    }
}