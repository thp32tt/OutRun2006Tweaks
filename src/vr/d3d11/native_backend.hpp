#pragma once

#include "resource_translation.hpp"
#include "vr/core/d3d9_draw_state.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <mutex>
#include <unordered_map>
#include <vector>
#include <d3d9.h>
#include <d3d11.h>
#include <wrl/client.h>

namespace outrun::vr::dx11 {

struct FixedFunctionTransformConstants;
struct FixedFunctionVertexShaderPrototype;
struct FixedFunctionPixelShaderPrototype;
struct NativeSurfacePairReadiness;
class NativeSurfaceMirror;
class NativeSurfacePairBinding;
struct NativeTriangleFanIndexBufferReadiness;
class NativeTriangleFanIndexBuffer;
struct VertexInputLayoutTranslation;
struct FixedFunctionStageState;
struct PipelineTranslation;
struct ProgrammableShaderPairCacheIdentity;
struct ProgrammableShaderFunctionSourceEvidence;
struct ProgrammableShaderInterfaceLinkageEvidence;
struct ProgrammableShaderPairSourceSemanticEvidence;
struct ProgrammableShaderRegisterMappingPlanEvidence;

struct NativeBackendConfig {
    std::uint32_t width = 0;
    std::uint32_t height = 0;
    DXGI_FORMAT color_format = DXGI_FORMAT_B8G8R8A8_UNORM;
    bool request_debug_layer = false;
    bool adapter_luid_valid = false;
    bool require_adapter_luid = false;
    LUID adapter_luid{};
};

// Live binding proof for the R96 transform owner. A snapshot is valid only
// when the exact translated WVP payload previously uploaded by this owner is
// still bound at VS b0 on the caller-supplied same-device context. This is
// dormant observation evidence only and never issues Draw*.
struct NativeFixedFunctionTransformBindingReadiness {
    bool inputValid{};
    bool ownerReady{};
    bool contextMatches{};
    bool payloadMatches{};
    bool boundExact{};
    bool uploadPresent{};
    bool ready{};
    std::uint64_t uploadGeneration{};
    std::uint64_t payloadHash{};
    std::uint64_t snapshotToken{};
};

// R96 dormant owner for the R94/R95 fixed-function transform constant
// payload. No game draw path constructs this owner yet.
class NativeFixedFunctionTransformBuffer final {
public:
    NativeFixedFunctionTransformBuffer() = default;
    ~NativeFixedFunctionTransformBuffer() = default;
    NativeFixedFunctionTransformBuffer(
        const NativeFixedFunctionTransformBuffer&) = delete;
    NativeFixedFunctionTransformBuffer& operator=(
        const NativeFixedFunctionTransformBuffer&) = delete;

    bool initialize(ID3D11Device* device) noexcept;
    bool upload_and_bind(
        ID3D11DeviceContext* context,
        const FixedFunctionTransformConstants& constants) noexcept;
    [[nodiscard]] NativeFixedFunctionTransformBindingReadiness
    binding_readiness(
        ID3D11DeviceContext* context,
        const FixedFunctionTransformConstants& constants) const noexcept;
    [[nodiscard]] bool validate_binding_snapshot(
        ID3D11DeviceContext* context,
        const FixedFunctionTransformConstants& constants,
        std::uint64_t snapshotToken) const noexcept;
    void shutdown() noexcept;

    [[nodiscard]] bool ready() const noexcept {
        return device_ && buffer_;
    }
    [[nodiscard]] ID3D11Buffer* buffer() const noexcept {
        return buffer_.Get();
    }
    [[nodiscard]] std::uint64_t upload_generation() const noexcept {
        return upload_generation_;
    }

private:
    Microsoft::WRL::ComPtr<ID3D11Device> device_;
    Microsoft::WRL::ComPtr<ID3D11Buffer> buffer_;
    std::uint64_t upload_generation_ = 0;
    std::uint64_t payload_hash_ = 0;
};

// R98 dormant owner for one translated fixed-function sampler state.
// The CONV-DX11 texture-stage binding primitive may bind this immutable object
// only to an explicitly supplied same-device context; no game Draw* path calls it.
class NativeFixedFunctionSamplerState final {
public:
    NativeFixedFunctionSamplerState() = default;
    ~NativeFixedFunctionSamplerState() = default;
    NativeFixedFunctionSamplerState(
        const NativeFixedFunctionSamplerState&) = delete;
    NativeFixedFunctionSamplerState& operator=(
        const NativeFixedFunctionSamplerState&) = delete;

    bool initialize(
        ID3D11Device* device,
        const FixedFunctionStageState& stage) noexcept;
    void shutdown() noexcept;

    [[nodiscard]] bool ready() const noexcept {
        return device_ && sampler_;
    }
    [[nodiscard]] ID3D11Device* device() const noexcept {
        return device_.Get();
    }
    [[nodiscard]] ID3D11SamplerState* sampler() const noexcept {
        return sampler_.Get();
    }

private:
    Microsoft::WRL::ComPtr<ID3D11Device> device_;
    Microsoft::WRL::ComPtr<ID3D11SamplerState> sampler_;
};

// R99 dormant owner for a translated D3D11 Texture2D mirror and its SRV.
// R101 adds a bounded full-subresource WRITE_DISCARD upload for exact
// DEFAULT+DYNAMIC source semantics. The CONV-DX11 texture-stage binding
// primitive may bind the SRV only with a same-device R98 sampler; no production
// caller or native game Draw* routing is introduced here.
class NativeFixedFunctionTextureView final {
public:
    NativeFixedFunctionTextureView() = default;
    ~NativeFixedFunctionTextureView() = default;
    NativeFixedFunctionTextureView(
        const NativeFixedFunctionTextureView&) = delete;
    NativeFixedFunctionTextureView& operator=(
        const NativeFixedFunctionTextureView&) = delete;

    bool initialize(
        ID3D11Device* device,
        ID3D11Texture2D* texture,
        D3DFORMAT sourceFormat,
        D3DPOOL sourcePool,
        DWORD sourceUsage) noexcept;
    bool upload_full_discard(
        ID3D11DeviceContext* context,
        const void* source,
        UINT sourceRowPitch,
        UINT sourceRows) noexcept;
    void shutdown() noexcept;

    [[nodiscard]] bool ready() const noexcept {
        return device_ && texture_ && srv_ && source_metadata_valid_;
    }
    [[nodiscard]] bool content_ready() const noexcept {
        return upload_generation_ != 0;
    }
    [[nodiscard]] std::uint64_t upload_generation() const noexcept {
        return upload_generation_;
    }
    [[nodiscard]] ID3D11Device* device() const noexcept {
        return device_.Get();
    }
    [[nodiscard]] ID3D11Texture2D* texture() const noexcept {
        return texture_.Get();
    }
    [[nodiscard]] ID3D11ShaderResourceView* srv() const noexcept {
        return srv_.Get();
    }

private:
    Microsoft::WRL::ComPtr<ID3D11Device> device_;
    Microsoft::WRL::ComPtr<ID3D11Texture2D> texture_;
    Microsoft::WRL::ComPtr<ID3D11ShaderResourceView> srv_;
    D3DFORMAT source_format_ = D3DFMT_UNKNOWN;
    D3DPOOL source_pool_ = D3DPOOL_DEFAULT;
    DWORD source_usage_ = 0;
    bool source_metadata_valid_ = false;
    std::uint64_t upload_generation_ = 0;
};

// Dormant fixed-function texture-stage binding primitive. Both immutable
// owners and the supplied context must belong to the same D3D11 device, and
// the slot must be legal for both PS sampler and SRV namespaces. This helper
// never dispatches a D3D11 Draw* call and has no production caller.
[[nodiscard]] bool bind_fixed_function_texture_stage_for_observation(
    ID3D11DeviceContext* context,
    UINT slot,
    const NativeFixedFunctionSamplerState& sampler,
    const NativeFixedFunctionTextureView& texture) noexcept;

// R132 observes the exact PS sampler/SRV identity after a dormant binding.
// The snapshot includes the slot, owner COM identities and texture upload
// generation so a later mutation/rebind cannot reuse stale readiness.
struct NativeFixedFunctionTextureStageBindingReadiness {
    bool inputValid{};
    bool slotValid{};
    bool ownersReady{};
    bool devicesMatch{};
    bool contextMatches{};
    bool boundExact{};
    bool ready{};
    UINT slot{};
    std::uint64_t textureUploadGeneration{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] NativeFixedFunctionTextureStageBindingReadiness
observe_fixed_function_texture_stage_binding(
    ID3D11DeviceContext* context,
    UINT slot,
    const NativeFixedFunctionSamplerState& sampler,
    const NativeFixedFunctionTextureView& texture) noexcept;

[[nodiscard]] bool validate_fixed_function_texture_stage_binding_snapshot(
    ID3D11DeviceContext* context,
    UINT slot,
    const NativeFixedFunctionSamplerState& sampler,
    const NativeFixedFunctionTextureView& texture,
    std::uint64_t snapshotToken) noexcept;

// R136 aggregates the exact live PS sampler/SRV identity for every fixed-
// function texture stage required by the sealed draw mask. D3D9 fixed-function
// texture stages are limited to 0..7. Missing owners, unsupported mask bits, or
// any stale live binding keep the aggregate fail-closed.
struct NativeFixedFunctionTextureBindingSetReadiness {
    bool inputValid{};
    bool requiredMaskValid{};
    bool allRequiredBoundExact{};
    bool ready{};
    std::uint32_t requiredTextureMask{};
    std::uint32_t observedTextureMask{};
    std::array<std::uint64_t, 8> stageSnapshotTokens{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] NativeFixedFunctionTextureBindingSetReadiness
observe_fixed_function_texture_binding_set(
    ID3D11DeviceContext* context,
    std::uint32_t requiredTextureMask,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures) noexcept;

[[nodiscard]] bool validate_fixed_function_texture_binding_set_snapshot(
    ID3D11DeviceContext* context,
    std::uint32_t requiredTextureMask,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    std::uint64_t snapshotToken) noexcept;

// R136 also makes the aggregate value self-authenticating against accidental
// copied-struct drift before it can be composed with an R135 sealed draw.
[[nodiscard]] bool
validate_fixed_function_texture_binding_set_readiness_integrity(
    const NativeFixedFunctionTextureBindingSetReadiness& textureBindings) noexcept;

// R119 seals one R113 MANAGED vertex/index buffer mirror into a fail-closed
// readiness snapshot. The token binds CPU-shadow version, device generation,
// mirror instance, descriptor and expected-device identity. This is dormant
// evidence only; it does not route a game Lock/Unlock or Draw* call to D3D11.
struct NativeManagedBufferMirrorReadiness
{
    bool inputValid{};
    bool shadowValid{};
    bool resourcesOwned{};
    bool lifetimeCurrent{};
    bool deviceMatches{};
    bool descriptorExact{};
    bool mutationPlanExact{};
    bool ready{};
    ResourceRole role = ResourceRole::Vertex;
    std::uint64_t deviceGeneration{};
    std::uint64_t shadowVersion{};
    std::uint64_t mirrorGeneration{};
    std::uint64_t mirrorShadowVersion{};
    std::uint64_t mirrorInstanceGeneration{};
    std::uint64_t snapshotToken{};
};

// R152 seals the actual managed source-index values covered by a D3D9
// DrawIndexedPrimitive source range. Unlike R149's numeric range proof, this
// snapshot scans the exact current CPU shadow and is tied to the same R119
// mirror identity used by dormant geometry readiness.
struct NativeManagedIndexRangeReadiness {
    bool inputValid{};
    bool shadowValid{};
    bool indexFormatExact{};
    bool mirrorSnapshotExact{};
    bool byteRangeExact{};
    bool valuesWithinDeclaredRange{};
    bool ready{};
    D3DFORMAT sourceIndexFormat = D3DFMT_UNKNOWN;
    UINT startIndex{};
    UINT indexCount{};
    UINT minVertexIndex{};
    UINT maxVertexIndex{};
    UINT observedMinIndex{};
    UINT observedMaxIndex{};
    std::uint64_t shadowVersion{};
    std::uint64_t mirrorSnapshotToken{};
    std::uint64_t contentHash{};
    std::uint64_t snapshotToken{};
};

// R113 dormant CPU shadow plus generation-bound D3D11 mirror for D3D9
// MANAGED vertex/index buffers. This is readiness infrastructure only: no
// game Lock/Unlock hook or native draw path routes through it yet.
class NativeManagedBufferShadow final {
public:
    NativeManagedBufferShadow() = default;
    ~NativeManagedBufferShadow() = default;
    NativeManagedBufferShadow(const NativeManagedBufferShadow&) = delete;
    NativeManagedBufferShadow& operator=(const NativeManagedBufferShadow&) = delete;

    bool initialize(
        ResourceRole role,
        UINT byteWidth,
        DWORD sourceUsage) noexcept;
    bool write_range(
        UINT offset,
        const void* source,
        UINT sourceBytes) noexcept;
    bool recreate_and_upload_mirror(ID3D11Device* device) noexcept;
    void observe_device_reset() noexcept;
    void shutdown() noexcept;

    [[nodiscard]] bool ready() const noexcept {
        return metadata_valid_ && byte_width_ != 0 &&
            shadow_.size() == byte_width_;
    }
    [[nodiscard]] bool shadow_valid() const noexcept {
        return lifetime_.cpuShadowValid;
    }
    [[nodiscard]] bool mirror_ready() const noexcept {
        return managed_mirror_ready(lifetime_) &&
            mirror_device_ && mirror_buffer_;
    }
    [[nodiscard]] std::uint64_t shadow_version() const noexcept {
        return lifetime_.cpuShadowVersion;
    }
    [[nodiscard]] std::uint64_t device_generation() const noexcept {
        return lifetime_.deviceGeneration;
    }
    [[nodiscard]] ID3D11Device* mirror_device() const noexcept {
        return mirror_device_.Get();
    }
    [[nodiscard]] ID3D11Buffer* mirror_buffer() const noexcept {
        return mirror_buffer_.Get();
    }
    [[nodiscard]] UINT byte_width() const noexcept {
        return byte_width_;
    }

    // R155 hashes the exact indexed triangle-fan expansion implied by the
    // current MANAGED index CPU shadow. No raw shadow pointer escapes.
    [[nodiscard]] bool hash_indexed_triangle_fan_window(
        D3DFORMAT sourceIndexFormat,
        UINT startIndex,
        UINT sourceIndexCount,
        UINT primitiveCount,
        std::uint64_t expectedShadowVersion,
        std::uint64_t& expandedContentHash) const noexcept;

    [[nodiscard]] bool mirror_descriptor_exact(
        ID3D11Device* expectedDevice) const noexcept;
    [[nodiscard]] NativeManagedBufferMirrorReadiness mirror_readiness(
        ID3D11Device* expectedDevice) const noexcept;
    [[nodiscard]] bool validate_mirror_readiness_snapshot(
        ID3D11Device* expectedDevice,
        std::uint64_t snapshotToken) const noexcept;
    [[nodiscard]] NativeManagedIndexRangeReadiness index_range_readiness(
        const NativeManagedBufferMirrorReadiness& mirror,
        D3DFORMAT sourceIndexFormat,
        UINT startIndex,
        UINT indexCount,
        UINT minVertexIndex,
        UINT maxVertexIndex) const noexcept;
    [[nodiscard]] bool validate_index_range_readiness_snapshot(
        const NativeManagedBufferMirrorReadiness& mirror,
        D3DFORMAT sourceIndexFormat,
        UINT startIndex,
        UINT indexCount,
        UINT minVertexIndex,
        UINT maxVertexIndex,
        std::uint64_t snapshotToken) const noexcept;
    [[nodiscard]] std::uint64_t mirror_instance_generation() const noexcept {
        return mirror_instance_generation_;
    }

private:
    void release_mirror() noexcept;

    ResourceRole role_ = ResourceRole::Vertex;
    DWORD source_usage_ = 0;
    UINT byte_width_ = 0;
    bool metadata_valid_ = false;
    std::vector<std::uint8_t> shadow_;
    ManagedMirrorLifetimeState lifetime_{};
    Microsoft::WRL::ComPtr<ID3D11Device> mirror_device_;
    Microsoft::WRL::ComPtr<ID3D11Buffer> mirror_buffer_;
    std::uint64_t mirror_instance_generation_ = 0;
};

// R102 dormant CPU shadow for a single-mip uncompressed D3D9 MANAGED
// Texture2D. R103 adds concrete generation-bound D3D11 DEFAULT mirror/SRV
// recreation from the shadow. R104 adds the LockRect source transaction.
// R105 stages bytes before the real D3D9 UnlockRect and commits them only after
// that UnlockRect succeeds, so no source pointer survives across the COM call.
// R108 adds registry-level, non-routing mirror ownership/readiness observation.
// R109 adds fail-closed per-stage aggregation over those readiness snapshots.
// R110 adds a stale-snapshot token that changes on every successful mirror
// recreation and on every generation/shadow-version transition represented by
// the aggregate. R111 additionally verifies the concrete D3D11 Texture2D/SRV
// descriptor and view identity before readiness can become true.
// Native draw/SRV binding remains disabled.
struct NativeManagedTextureMirrorReadiness {
    bool registered{};
    bool shadowValid{};
    bool resourcesOwned{};
    bool lifetimeCurrent{};
    bool deviceMatches{};
    bool descriptorExact{};
    bool ready{};
    std::uint64_t deviceGeneration{};
    std::uint64_t shadowVersion{};
    std::uint64_t mirrorGeneration{};
    std::uint64_t mirrorShadowVersion{};
};

struct NativeManagedTextureStageReadiness {
    bool inputValid{};
    bool allRequiredReady{};
    std::uint32_t requiredMask{};
    std::uint32_t registeredMask{};
    std::uint32_t shadowValidMask{};
    std::uint32_t resourcesOwnedMask{};
    std::uint32_t lifetimeCurrentMask{};
    std::uint32_t deviceMatchesMask{};
    std::uint32_t descriptorExactMask{};
    std::uint32_t readyMask{};
    std::uint32_t pendingMask{};
    std::uint64_t snapshotToken{};
};

class NativeManagedTextureShadow final {
public:
    NativeManagedTextureShadow() = default;
    ~NativeManagedTextureShadow() = default;
    NativeManagedTextureShadow(const NativeManagedTextureShadow&) = delete;
    NativeManagedTextureShadow& operator=(const NativeManagedTextureShadow&) = delete;

    bool initialize(
        D3DFORMAT sourceFormat,
        UINT width,
        UINT height) noexcept;
    bool write_full(
        const void* source,
        UINT sourceRowPitch,
        UINT sourceRows) noexcept;
    bool read_full(
        void* destination,
        UINT destinationRowPitch,
        UINT destinationRows) const noexcept;
    bool recreate_and_upload_mirror(ID3D11Device* device) noexcept;
    bool begin_source_lock(
        UINT level,
        const RECT* sourceRect,
        DWORD lockFlags,
        const D3DLOCKED_RECT& lockedRect) noexcept;
    bool stage_source_unlock(UINT level) noexcept;
    bool finish_source_unlock(UINT level, HRESULT unlockResult) noexcept;
    bool commit_source_unlock(UINT level) noexcept;
    void cancel_source_lock() noexcept;
    void note_mirror_uploaded() noexcept;
    void observe_device_reset() noexcept;
    bool invalidate_external_mutation() noexcept;
    void shutdown() noexcept;

    [[nodiscard]] bool ready() const noexcept {
        return source_format_ != D3DFMT_UNKNOWN &&
            width_ != 0 && height_ != 0 && row_bytes_ != 0 &&
            !shadow_.empty();
    }
    [[nodiscard]] bool shadow_valid() const noexcept {
        return lifetime_.cpuShadowValid;
    }
    [[nodiscard]] bool mirror_ready() const noexcept {
        return managed_mirror_ready(lifetime_) &&
            mirror_device_ && mirror_texture_ && mirror_srv_;
    }
    [[nodiscard]] std::uint64_t shadow_version() const noexcept {
        return lifetime_.cpuShadowVersion;
    }
    [[nodiscard]] std::uint64_t device_generation() const noexcept {
        return lifetime_.deviceGeneration;
    }
    [[nodiscard]] bool source_lock_active() const noexcept {
        return source_lock_active_;
    }
    [[nodiscard]] bool source_unlock_staged() const noexcept {
        return source_unlock_staged_;
    }
    [[nodiscard]] ID3D11Device* mirror_device() const noexcept {
        return mirror_device_.Get();
    }
    [[nodiscard]] ID3D11Texture2D* mirror_texture() const noexcept {
        return mirror_texture_.Get();
    }
    [[nodiscard]] ID3D11ShaderResourceView* mirror_srv() const noexcept {
        return mirror_srv_.Get();
    }
    [[nodiscard]] std::uint64_t mirror_instance_generation() const noexcept {
        return mirror_instance_generation_;
    }
    [[nodiscard]] bool mirror_descriptor_exact(
        ID3D11Device* expectedDevice) const noexcept;
    [[nodiscard]] const ManagedMirrorLifetimeState&
    lifetime_state() const noexcept {
        return lifetime_;
    }

private:
    void release_mirror() noexcept;
    void invalidate_shadow() noexcept;
    void clear_source_lock() noexcept;
    void clear_unlock_stage() noexcept;

    D3DFORMAT source_format_ = D3DFMT_UNKNOWN;
    UINT width_ = 0;
    UINT height_ = 0;
    UINT row_bytes_ = 0;
    std::vector<std::uint8_t> shadow_;
    ManagedMirrorLifetimeState lifetime_{};
    const void* source_lock_bits_ = nullptr;
    UINT source_lock_pitch_ = 0;
    UINT source_lock_level_ = 0;
    bool source_lock_active_ = false;
    std::vector<std::uint8_t> pending_unlock_;
    UINT source_unlock_level_ = 0;
    bool source_unlock_staged_ = false;
    Microsoft::WRL::ComPtr<ID3D11Device> mirror_device_;
    Microsoft::WRL::ComPtr<ID3D11Texture2D> mirror_texture_;
    Microsoft::WRL::ComPtr<ID3D11ShaderResourceView> mirror_srv_;
    std::uint64_t mirror_instance_generation_ = 0;
};

// R105 census-only per-texture owner. Keys are observed D3D9 texture identities;
// the registry never AddRefs them, so the R30 Release hook must forget an entry
// when the real COM refcount reaches zero. It owns CPU shadows and transaction
// staging only and does not bind D3D11 resources to a game draw.
class NativeManagedTextureRegistry final {
public:
    NativeManagedTextureRegistry() = default;
    ~NativeManagedTextureRegistry() = default;
    NativeManagedTextureRegistry(const NativeManagedTextureRegistry&) = delete;
    NativeManagedTextureRegistry& operator=(const NativeManagedTextureRegistry&) = delete;

    bool register_texture(
        const void* textureKey,
        D3DFORMAT sourceFormat,
        UINT width,
        UINT height,
        UINT levels,
        DWORD usage,
        D3DPOOL pool) noexcept;
    bool begin_source_lock(
        const void* textureKey,
        UINT level,
        const RECT* sourceRect,
        DWORD lockFlags,
        const D3DLOCKED_RECT& lockedRect) noexcept;
    bool stage_source_unlock(const void* textureKey, UINT level) noexcept;
    bool finish_source_unlock(
        const void* textureKey,
        UINT level,
        HRESULT unlockResult) noexcept;
    bool invalidate_external_mutation(const void* textureKey) noexcept;
    bool recreate_and_upload_mirror_for_observation(
        const void* textureKey,
        ID3D11Device* device) noexcept;
    [[nodiscard]] NativeManagedTextureMirrorReadiness mirror_readiness(
        const void* textureKey,
        ID3D11Device* expectedDevice) const noexcept;
    [[nodiscard]] NativeManagedTextureStageReadiness
    mirror_readiness_for_stages(
        const void* const* textureKeys,
        std::size_t textureCount,
        std::uint32_t requiredMask,
        ID3D11Device* expectedDevice) const noexcept;
    [[nodiscard]] bool validate_mirror_readiness_snapshot_for_stages(
        const void* const* textureKeys,
        std::size_t textureCount,
        std::uint32_t requiredMask,
        ID3D11Device* expectedDevice,
        std::uint64_t snapshotToken) const noexcept;
    void observe_device_reset() noexcept;
    void forget_texture(const void* textureKey) noexcept;
    void clear() noexcept;

    [[nodiscard]] std::size_t size() const noexcept;
    [[nodiscard]] bool contains(const void* textureKey) const noexcept;
    [[nodiscard]] bool shadow_valid(const void* textureKey) const noexcept;
    [[nodiscard]] std::uint64_t shadow_version(
        const void* textureKey) const noexcept;
    [[nodiscard]] std::uint64_t device_generation(
        const void* textureKey) const noexcept;
    [[nodiscard]] bool source_lock_active(
        const void* textureKey) const noexcept;
    [[nodiscard]] bool source_unlock_staged(
        const void* textureKey) const noexcept;
    bool read_shadow(
        const void* textureKey,
        void* destination,
        UINT destinationRowPitch,
        UINT destinationRows) const noexcept;

private:
    NativeManagedTextureShadow* find_locked(const void* textureKey) noexcept;
    const NativeManagedTextureShadow* find_locked(
        const void* textureKey) const noexcept;
    void advance_membership_generation_locked() noexcept;

    mutable std::mutex mutex_;
    std::unordered_map<
        const void*,
        std::unique_ptr<NativeManagedTextureShadow>> shadows_;
    std::uint64_t membership_generation_ = 1;
};

// R116 owns concrete D3D11 blend/depth-stencil/rasterizer objects for one
// exact PipelineTranslation and seals their immutable translation identity.
// This remains dormant activation-readiness evidence: it does not bind state
// or route a game draw.
struct NativeFixedFunctionRenderStateReadiness {
    bool inputValid{};
    bool bundleReady{};
    bool deviceMatches{};
    bool translationMatches{};
    bool ready{};
    std::uint64_t bundleGeneration{};
    std::uint64_t translationIdentity{};
    std::uint64_t snapshotToken{};
};

class NativeFixedFunctionRenderStateBundle final {
public:
    NativeFixedFunctionRenderStateBundle() = default;
    ~NativeFixedFunctionRenderStateBundle() = default;
    NativeFixedFunctionRenderStateBundle(
        const NativeFixedFunctionRenderStateBundle&) = delete;
    NativeFixedFunctionRenderStateBundle& operator=(
        const NativeFixedFunctionRenderStateBundle&) = delete;

    bool initialize(
        ID3D11Device* device,
        const PipelineTranslation& translation) noexcept;
    void shutdown() noexcept;
    [[nodiscard]] NativeFixedFunctionRenderStateReadiness
    translation_readiness(
        ID3D11Device* expectedDevice,
        const PipelineTranslation& translation) const noexcept;
    [[nodiscard]] bool validate_translation_snapshot(
        ID3D11Device* expectedDevice,
        const PipelineTranslation& translation,
        std::uint64_t snapshotToken) const noexcept;
    [[nodiscard]] bool validate_readiness_snapshot(
        ID3D11Device* expectedDevice,
        const NativeFixedFunctionRenderStateReadiness& readiness) const noexcept;

    [[nodiscard]] bool ready() const noexcept {
        return device_ && blend_state_ && depth_stencil_state_ &&
            rasterizer_state_;
    }
    [[nodiscard]] ID3D11Device* device() const noexcept {
        return device_.Get();
    }
    [[nodiscard]] ID3D11BlendState* blend_state() const noexcept {
        return blend_state_.Get();
    }
    [[nodiscard]] ID3D11DepthStencilState* depth_stencil_state() const noexcept {
        return depth_stencil_state_.Get();
    }
    [[nodiscard]] ID3D11RasterizerState* rasterizer_state() const noexcept {
        return rasterizer_state_.Get();
    }
    [[nodiscard]] UINT stencil_ref() const noexcept {
        return stencil_ref_;
    }

private:
    Microsoft::WRL::ComPtr<ID3D11Device> device_;
    Microsoft::WRL::ComPtr<ID3D11BlendState> blend_state_;
    Microsoft::WRL::ComPtr<ID3D11DepthStencilState> depth_stencil_state_;
    Microsoft::WRL::ComPtr<ID3D11RasterizerState> rasterizer_state_;
    UINT stencil_ref_ = 0;
    std::uint64_t translation_identity_ = 0;
    std::uint64_t bundle_generation_ = 0;
};

// R112 seals the exact translation identity of an R97 bundle without routing
// it into a game draw. A nonzero snapshot is issued only when the live bundle
// still belongs to the expected D3D11 device and matches the exact input-layout
// plus R93/R84 shader prototypes used for the activation candidate.
struct NativeFixedFunctionPipelineReadiness {
    bool inputValid{};
    bool bundleReady{};
    bool deviceMatches{};
    bool inputLayoutMatches{};
    bool vertexShaderMatches{};
    bool pixelShaderMatches{};
    bool ready{};
    std::uint64_t bundleGeneration{};
    std::uint64_t snapshotToken{};
};

// R134 observes the concrete IA/VS/PS objects after the dormant R132 binder.
// R147 adds GS/HS/DS isolation, and R148 additionally requires stream-output
// targets plus draw predication to be clear. Its token is tied to the exact
// R112 translation snapshot and same-device COM identities. This is
// observation evidence only and never issues Draw*.
struct NativeFixedFunctionPipelineBindingReadiness {
    bool inputValid{};
    bool bundleReady{};
    bool contextMatches{};
    bool translationSnapshotValid{};
    bool geometryShaderClear{};
    bool hullShaderClear{};
    bool domainShaderClear{};
    bool graphicsStageIsolationReady{};
    bool streamOutputTargetsClear{};
    bool predicationClear{};
    bool drawSideEffectIsolationReady{};
    bool boundExact{};
    bool ready{};
    std::uint64_t pipelineSnapshotToken{};
    std::uint64_t snapshotToken{};
};

// R115 composes the independently proven R112 pipeline snapshot and R110/R111
// managed-texture stage snapshot into one fail-closed activation-candidate
// identity. This is evidence only: it does not bind state or route a game draw.
struct NativeFixedFunctionActivationReadiness {
    bool inputValid{};
    bool pipelineReady{};
    bool textureStagesReady{};
    bool componentSnapshotsPresent{};
    bool ready{};
    std::uint32_t requiredTextureMask{};
    std::uint64_t pipelineSnapshotToken{};
    std::uint64_t textureSnapshotToken{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] NativeFixedFunctionActivationReadiness
compose_fixed_function_activation_readiness(
    const NativeFixedFunctionPipelineReadiness& pipeline,
    const NativeManagedTextureStageReadiness& textureStages) noexcept;

[[nodiscard]] bool validate_fixed_function_activation_snapshot(
    const NativeFixedFunctionPipelineReadiness& pipeline,
    const NativeManagedTextureStageReadiness& textureStages,
    std::uint64_t snapshotToken) noexcept;

// R122 composes exact R119 managed VB/optional IB snapshots with exact
// primitive topology. The R121 fan materializer still needs an owned/uploaded
// generated IB, so triangle fans remain fail-closed at this readiness layer.
struct NativeFixedFunctionGeometryReadiness {
    bool inputValid{};
    bool vertexBufferReady{};
    bool indexBufferRequired{};
    bool indexBufferReady{};
    bool generatedIndexBufferRequired{};
    bool generatedIndexBufferReady{};
    bool generatedIndexBufferMatchesDraw{};
    bool topologyReady{};
    bool componentSnapshotsPresent{};
    bool ready{};
    D3D11_PRIMITIVE_TOPOLOGY topology =
        D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    std::uint64_t vertexBufferSnapshotToken{};
    std::uint64_t indexBufferSnapshotToken{};
    std::uint64_t generatedIndexBufferSnapshotToken{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] NativeFixedFunctionGeometryReadiness
compose_fixed_function_geometry_readiness(
    const NativeManagedBufferMirrorReadiness& vertexBuffer,
    bool indexed,
    const NativeManagedBufferMirrorReadiness& indexBuffer,
    D3DPRIMITIVETYPE primitive) noexcept;

[[nodiscard]] bool validate_fixed_function_geometry_snapshot(
    const NativeManagedBufferMirrorReadiness& vertexBuffer,
    bool indexed,
    const NativeManagedBufferMirrorReadiness& indexBuffer,
    D3DPRIMITIVETYPE primitive,
    std::uint64_t snapshotToken) noexcept;

// R139 seals the direct R122 managed-buffer geometry snapshot against copied
// struct drift, then observes the effective live IA slot-0 VB/optional IB and
// primitive topology. Generated triangle-fan IBs remain fail-closed here until
// their owning buffer is wired through the same live-binding contract.
[[nodiscard]] bool validate_fixed_function_direct_geometry_readiness_integrity(
    const NativeFixedFunctionGeometryReadiness& geometry) noexcept;

struct NativeFixedFunctionGeometryBindingReadiness {
    bool inputValid{};
    bool geometryReady{};
    bool contextMatches{};
    bool vertexBufferCurrent{};
    bool indexBufferCurrent{};
    bool vertexBufferBoundExact{};
    bool indexBufferBoundExact{};
    bool topologyBoundExact{};
    bool ready{};
    bool indexed{};
    UINT vertexStride{};
    UINT vertexOffset{};
    DXGI_FORMAT indexFormat = DXGI_FORMAT_UNKNOWN;
    UINT indexOffset{};
    D3D11_PRIMITIVE_TOPOLOGY topology =
        D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    std::uint64_t geometrySnapshotToken{};
    std::uint64_t vertexBufferSnapshotToken{};
    std::uint64_t indexBufferSnapshotToken{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] bool bind_fixed_function_geometry_for_observation(
    ID3D11DeviceContext* context,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeManagedBufferShadow* indexBuffer,
    DXGI_FORMAT indexFormat,
    UINT indexOffset) noexcept;

[[nodiscard]] NativeFixedFunctionGeometryBindingReadiness
observe_fixed_function_geometry_binding(
    ID3D11DeviceContext* context,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeManagedBufferShadow* indexBuffer,
    DXGI_FORMAT indexFormat,
    UINT indexOffset) noexcept;

[[nodiscard]] bool validate_fixed_function_geometry_binding_snapshot(
    ID3D11DeviceContext* context,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeManagedBufferShadow& vertexBuffer,
    UINT vertexStride,
    UINT vertexOffset,
    const NativeManagedBufferShadow* indexBuffer,
    DXGI_FORMAT indexFormat,
    UINT indexOffset,
    std::uint64_t snapshotToken) noexcept;

// R128 consumes an R126 generated IB only for non-indexed D3D9 triangle fans.
// Indexed fans deliberately remain on the direct R122 fail-closed path until
// source-index provenance is sealed separately.
[[nodiscard]] NativeFixedFunctionGeometryReadiness
compose_fixed_function_nonindexed_triangle_fan_geometry_readiness(
    const NativeManagedBufferMirrorReadiness& vertexBuffer,
    const NativeTriangleFanIndexBufferReadiness& generatedIndexBuffer,
    UINT primitiveCount,
    UINT baseVertex) noexcept;

[[nodiscard]] bool
validate_fixed_function_nonindexed_triangle_fan_geometry_snapshot(
    const NativeManagedBufferMirrorReadiness& vertexBuffer,
    const NativeTriangleFanIndexBufferReadiness& generatedIndexBuffer,
    UINT primitiveCount,
    UINT baseVertex,
    std::uint64_t snapshotToken) noexcept;

// R143 closes the indexed triangle-fan geometry lineage gap without activating
// Draw*. The generated R126/R129 owner is accepted only when it was built from
// the exact current source-index mirror snapshot and the same primitive count,
// index format, StartIndex and source-index extent supplied to this compositor.
// The source index buffer remains provenance evidence; the generated R32_UINT
// triangle-list owner is the eventual IA index stream.
[[nodiscard]] NativeFixedFunctionGeometryReadiness
compose_fixed_function_indexed_triangle_fan_geometry_readiness(
    const NativeManagedBufferMirrorReadiness& vertexBuffer,
    const NativeManagedBufferMirrorReadiness& sourceIndexBuffer,
    const NativeTriangleFanIndexBufferReadiness& generatedIndexBuffer,
    UINT primitiveCount,
    D3DFORMAT sourceIndexFormat,
    UINT startIndex,
    UINT sourceIndexCount) noexcept;

[[nodiscard]] bool
validate_fixed_function_indexed_triangle_fan_geometry_snapshot(
    const NativeManagedBufferMirrorReadiness& vertexBuffer,
    const NativeManagedBufferMirrorReadiness& sourceIndexBuffer,
    const NativeTriangleFanIndexBufferReadiness& generatedIndexBuffer,
    UINT primitiveCount,
    D3DFORMAT sourceIndexFormat,
    UINT startIndex,
    UINT sourceIndexCount,
    std::uint64_t snapshotToken) noexcept;

// R124 seals D3D9 dynamic output state into a dormant D3D11-ready snapshot.
// It proves viewport/scissor geometry plus the OM blend factor/sample mask
// against the current output-surface extent. Nothing here binds RS/OM state.
struct NativeFixedFunctionOutputStateReadiness {
    bool inputValid{};
    bool viewportExact{};
    bool scissorExact{};
    bool omDynamicExact{};
    bool ready{};
    D3D11_VIEWPORT viewport{};
    D3D11_RECT scissorRect{};
    std::array<float, 4> blendFactor{1.0f, 1.0f, 1.0f, 1.0f};
    UINT sampleMask = 0xFFFFFFFFu;
    std::uint64_t snapshotToken{};
};

[[nodiscard]] NativeFixedFunctionOutputStateReadiness
compose_fixed_function_output_state_readiness(
    const OutRunVR::DrawState::RenderStateSnapshot& source,
    const NativeSurfacePairReadiness& surfacePair) noexcept;

[[nodiscard]] bool validate_fixed_function_output_state_snapshot(
    const OutRunVR::DrawState::RenderStateSnapshot& source,
    const NativeSurfacePairReadiness& surfacePair,
    std::uint64_t snapshotToken) noexcept;

// R137 observes the effective live RS/OM state after the dormant R126 owner
// has been applied. A token is issued only when every sealed object and
// dynamic value is still exact on the same D3D11 context device.
struct NativeFixedFunctionOutputBindingReadiness {
    bool inputValid{};
    bool ownerReady{};
    bool contextMatches{};
    bool rasterizerMatches{};
    bool viewportMatches{};
    bool scissorMatches{};
    bool blendStateMatches{};
    bool blendFactorMatches{};
    bool sampleMaskMatches{};
    bool depthStencilMatches{};
    bool stencilRefMatches{};
    bool ready{};
    std::uint64_t outputBindingSnapshotToken{};
    std::uint64_t snapshotToken{};
};

// R126 consumes an exact live R116 translation snapshot plus a freshly
// recomputed R124 source/surface snapshot into one dormant binding owner.
// initialize() cross-checks immutable rasterizer scissor enable against the
// dynamic source state before sealing RS/OM bindings. apply() never Draw*s.
class NativeFixedFunctionOutputStateBinding final {
public:
    NativeFixedFunctionOutputStateBinding() = default;
    ~NativeFixedFunctionOutputStateBinding() = default;
    NativeFixedFunctionOutputStateBinding(
        const NativeFixedFunctionOutputStateBinding&) = delete;
    NativeFixedFunctionOutputStateBinding& operator=(
        const NativeFixedFunctionOutputStateBinding&) = delete;

    bool initialize(
        ID3D11Device* device,
        const NativeFixedFunctionRenderStateBundle& renderStateBundle,
        const PipelineTranslation& translation,
        std::uint64_t renderStateSnapshotToken,
        const OutRunVR::DrawState::RenderStateSnapshot& source,
        const NativeSurfacePairReadiness& surfacePair,
        std::uint64_t outputStateSnapshotToken) noexcept;
    void shutdown() noexcept;
    [[nodiscard]] bool apply(ID3D11DeviceContext* context) const noexcept;
    [[nodiscard]] NativeFixedFunctionOutputBindingReadiness binding_readiness(
        ID3D11DeviceContext* context) const noexcept;
    [[nodiscard]] bool validate_binding_snapshot(
        ID3D11DeviceContext* context,
        std::uint64_t bindingSnapshotToken) const noexcept;

    [[nodiscard]] bool ready() const noexcept {
        return device_ && blend_state_ && depth_stencil_state_ &&
            rasterizer_state_ && render_state_snapshot_token_ != 0 &&
            surface_pair_snapshot_token_ != 0 &&
            output_state_snapshot_token_ != 0 && snapshot_token_ != 0;
    }
    [[nodiscard]] std::uint64_t render_state_snapshot_token() const noexcept {
        return render_state_snapshot_token_;
    }
    [[nodiscard]] std::uint64_t surface_pair_snapshot_token() const noexcept {
        return surface_pair_snapshot_token_;
    }
    [[nodiscard]] std::uint64_t output_state_snapshot_token() const noexcept {
        return output_state_snapshot_token_;
    }
    [[nodiscard]] std::uint64_t snapshot_token() const noexcept {
        return snapshot_token_;
    }

private:
    Microsoft::WRL::ComPtr<ID3D11Device> device_;
    Microsoft::WRL::ComPtr<ID3D11BlendState> blend_state_;
    Microsoft::WRL::ComPtr<ID3D11DepthStencilState> depth_stencil_state_;
    Microsoft::WRL::ComPtr<ID3D11RasterizerState> rasterizer_state_;
    D3D11_VIEWPORT viewport_{};
    D3D11_RECT scissor_rect_{};
    std::array<float, 4> blend_factor_{1.0f, 1.0f, 1.0f, 1.0f};
    UINT sample_mask_ = 0xFFFFFFFFu;
    UINT stencil_ref_ = 0;
    std::uint64_t render_state_snapshot_token_ = 0;
    std::uint64_t surface_pair_snapshot_token_ = 0;
    std::uint64_t output_state_snapshot_token_ = 0;
    std::uint64_t snapshot_token_ = 0;
};

// R131 extends the dormant draw-readiness snapshot through the concrete R126
// RS/OM binding identity. A candidate is not ready unless the binding was built
// from the same render-state, surface-pair and dynamic-output snapshots carried
// by the draw candidate. This remains dormant evidence only; no Draw* routing.
struct NativeFixedFunctionDrawReadiness {
    bool inputValid{};
    bool activationReady{};
    bool renderStateReady{};
    bool surfacePairReady{};
    bool outputStateReady{};
    bool outputBindingReady{};
    bool geometryReady{};
    bool componentSnapshotsPresent{};
    bool ready{};
    std::uint32_t requiredTextureMask{};
    std::uint64_t activationSnapshotToken{};
    std::uint64_t pipelineSnapshotToken{};
    std::uint64_t renderStateSnapshotToken{};
    std::uint64_t surfacePairSnapshotToken{};
    std::uint64_t outputStateSnapshotToken{};
    std::uint64_t outputBindingSnapshotToken{};
    std::uint64_t geometrySnapshotToken{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] NativeFixedFunctionDrawReadiness
compose_fixed_function_draw_readiness(
    const NativeFixedFunctionActivationReadiness& activation,
    const NativeFixedFunctionRenderStateReadiness& renderState,
    const NativeSurfacePairReadiness& surfacePair,
    const NativeFixedFunctionOutputStateReadiness& outputState,
    const NativeFixedFunctionOutputStateBinding& outputBinding,
    const NativeFixedFunctionGeometryReadiness& geometry) noexcept;

// R135 validates the self-contained identity carried by a composed draw
// readiness value. This prevents downstream bind-readiness code from accepting
// a copied snapshot whose required texture-stage mask was changed afterward.
[[nodiscard]] bool validate_fixed_function_draw_readiness_integrity(
    const NativeFixedFunctionDrawReadiness& draw) noexcept;

[[nodiscard]] bool validate_fixed_function_draw_snapshot(
    const NativeFixedFunctionActivationReadiness& activation,
    const NativeFixedFunctionRenderStateReadiness& renderState,
    const NativeSurfacePairReadiness& surfacePair,
    const NativeFixedFunctionOutputStateReadiness& outputState,
    const NativeFixedFunctionOutputStateBinding& outputBinding,
    const NativeFixedFunctionGeometryReadiness& geometry,
    std::uint64_t snapshotToken) noexcept;

// R132 composes the R131 RS/OM-gated draw candidate with the currently
// observed PS sampler/SRV binding identity. This is readiness evidence only;
// it does not issue a D3D11 Draw* call.
struct NativeFixedFunctionTexturedDrawReadiness {
    bool inputValid{};
    bool drawReady{};
    bool textureStageReady{};
    bool textureMaskMatches{};
    bool componentSnapshotsPresent{};
    bool ready{};
    std::uint32_t requiredTextureMask{};
    std::uint32_t observedTextureMask{};
    std::uint64_t drawSnapshotToken{};
    std::uint64_t textureStageSnapshotToken{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] NativeFixedFunctionTexturedDrawReadiness
compose_fixed_function_textured_draw_readiness(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    UINT slot,
    const NativeFixedFunctionSamplerState& sampler,
    const NativeFixedFunctionTextureView& texture) noexcept;

[[nodiscard]] bool validate_fixed_function_textured_draw_snapshot(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    UINT slot,
    const NativeFixedFunctionSamplerState& sampler,
    const NativeFixedFunctionTextureView& texture,
    std::uint64_t snapshotToken) noexcept;

// R136 composes a sealed draw with an aggregate of all required live PS
// sampler/SRV stage identities. The legacy single-stage R133 entrypoint remains
// fail-closed for multi-stage masks.
[[nodiscard]] NativeFixedFunctionTexturedDrawReadiness
compose_fixed_function_multistage_textured_draw_readiness(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures) noexcept;

[[nodiscard]] bool validate_fixed_function_multistage_textured_draw_snapshot(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    std::uint64_t snapshotToken) noexcept;

// R138 composes the existing output/surface/PS/geometry evidence with live
// exact R97 IA/VS/PS and R137 RS/OM binding observations on the same context.
// Both live binding identities must still match the snapshots sealed by draw.
struct NativeFixedFunctionBoundDrawReadiness {
    bool inputValid{};
    bool texturedDrawReady{};
    bool pipelineBindingReady{};
    bool pipelineBindingMatchesDraw{};
    bool outputBindingReady{};
    bool outputBindingMatchesDraw{};
    bool componentSnapshotsPresent{};
    bool ready{};
    std::uint64_t texturedDrawSnapshotToken{};
    std::uint64_t pipelineBindingSnapshotToken{};
    std::uint64_t outputBindingSnapshotToken{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] NativeFixedFunctionBoundDrawReadiness
compose_fixed_function_bound_draw_readiness(
    const NativeFixedFunctionDrawReadiness& draw,
    const NativeFixedFunctionTexturedDrawReadiness& texturedDraw,
    const NativeFixedFunctionPipelineBindingReadiness& pipelineBinding,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding) noexcept;

[[nodiscard]] bool validate_fixed_function_bound_draw_snapshot(
    const NativeFixedFunctionDrawReadiness& draw,
    const NativeFixedFunctionTexturedDrawReadiness& texturedDraw,
    const NativeFixedFunctionPipelineBindingReadiness& pipelineBinding,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    std::uint64_t snapshotToken) noexcept;

// R240 dormant per-device inventory/cache owner for the R239 programmable
// VS/PS pair identity. This deliberately caches only authenticated identity
// metadata; it does not translate D3D9 bytecode, create/bind D3D11 shader
// objects, or participate in NativeDrawPath routing.
struct NativeProgrammableShaderPairCacheReadiness {
    bool inputValid{};
    bool ownerReady{};
    bool deviceMatches{};
    bool identityExact{};
    bool collisionFree{};
    bool cached{};
    bool ready{};
    std::size_t entryCount{};
    std::uint64_t ownerGeneration{};
    std::uint64_t cacheKey{};
    std::uint64_t snapshotToken{};
};

// R241 reserves a device/generation-owned slot for a future programmable
// translation result. Ownership readiness is intentionally distinct from
// shader-object readiness: R241 never creates or binds D3D11 shader objects.
struct NativeProgrammableShaderTranslationSlotReadiness {
    bool inputValid{};
    bool cacheReady{};
    bool deviceMatches{};
    bool cacheSnapshotMatches{};
    bool slotReserved{};
    bool translationObjectsPresent{};
    bool ownershipReady{};
    std::uint64_t ownerGeneration{};
    std::uint64_t slotGeneration{};
    std::uint64_t cacheKey{};
    std::uint64_t cacheSnapshotToken{};
    std::uint64_t snapshotToken{};
};

// R242 attaches an already-created programmable VS/PS object pair to one
// exact R241 slot and issues an ownership receipt. It does not translate
// D3D9 bytecode, create shaders, bind shaders, or participate in draw routing.
struct NativeProgrammableShaderTranslationObjectReadiness {
    bool inputValid{};
    bool slotReady{};
    bool deviceMatches{};
    bool cacheSnapshotMatches{};
    bool slotSnapshotMatches{};
    bool objectsAttached{};
    bool objectDevicesMatch{};
    bool attachmentReady{};
    std::uint64_t ownerGeneration{};
    std::uint64_t slotGeneration{};
    std::uint64_t translationObjectReceiptGeneration{};
    std::uint64_t cacheKey{};
    std::uint64_t cacheSnapshotToken{};
    std::uint64_t slotSnapshotToken{};
    std::uint64_t snapshotToken{};
};

// R243 attaches one exact translated D3D11 input-layout object to a validated
// R242 shader-object receipt. It seals ownership of the already-created layout
// plus exact descriptor metadata; it does not bind IA state or claim that
// programmable shader translation/constants are complete.
struct NativeProgrammableShaderInputLayoutReadiness {
    bool inputValid{};
    bool objectReceiptReady{};
    bool deviceMatches{};
    bool objectSnapshotMatches{};
    bool layoutIdentityExact{};
    bool inputLayoutAttached{};
    bool inputLayoutDeviceMatches{};
    bool attachmentReady{};
    std::uint64_t ownerGeneration{};
    std::uint64_t slotGeneration{};
    std::uint64_t translationObjectReceiptGeneration{};
    std::uint64_t inputLayoutReceiptGeneration{};
    std::uint64_t cacheKey{};
    std::uint64_t inputLayoutIdentity{};
    std::uint64_t cacheSnapshotToken{};
    std::uint64_t slotSnapshotToken{};
    std::uint64_t objectSnapshotToken{};
    std::uint64_t snapshotToken{};
};

    
// R244 attaches an exact same-device VS/PS constant-buffer pair to a validated
// R243 input-layout receipt. It seals ownership and exact constant-buffer
// descriptors only; it does not upload constants, bind VS/PS slots, or route
// programmable draws.
struct NativeProgrammableShaderConstantStateReadiness {
    bool inputValid{};
    bool inputLayoutReceiptReady{};
    bool deviceMatches{};
    bool inputLayoutSnapshotMatches{};
    bool constantBuffersAttached{};
    bool constantBufferDevicesMatch{};
    bool constantBufferDescriptorsExact{};
    bool attachmentReady{};
    std::uint64_t ownerGeneration{};
    std::uint64_t slotGeneration{};
    std::uint64_t translationObjectReceiptGeneration{};
    std::uint64_t inputLayoutReceiptGeneration{};
    std::uint64_t constantStateReceiptGeneration{};
    std::uint64_t cacheKey{};
    std::uint64_t inputLayoutIdentity{};
    UINT vertexConstantBytes{};
    UINT pixelConstantBytes{};
    std::uint64_t cacheSnapshotToken{};
    std::uint64_t slotSnapshotToken{};
    std::uint64_t objectSnapshotToken{};
    std::uint64_t inputLayoutSnapshotToken{};
    std::uint64_t snapshotToken{};
};

// R245 uploads one exact VS/PS payload pair into the dormant R244-owned
// constant buffers and seals the source payload/context receipt. It does not
// bind constant-buffer slots, route Draw*, or activate programmable rendering.
struct NativeProgrammableShaderConstantPayloadReadiness {
    bool inputValid{};
    bool constantStateReceiptReady{};
    bool deviceMatches{};
    bool contextDeviceMatches{};
    bool constantStateSnapshotMatches{};
    bool payloadReceiptPresent{};
    bool payloadBytesExact{};
    bool uploadReady{};
    std::uint64_t ownerGeneration{};
    std::uint64_t slotGeneration{};
    std::uint64_t translationObjectReceiptGeneration{};
    std::uint64_t inputLayoutReceiptGeneration{};
    std::uint64_t constantStateReceiptGeneration{};
    std::uint64_t constantPayloadReceiptGeneration{};
    std::uint64_t cacheKey{};
    std::uint64_t inputLayoutIdentity{};
    UINT vertexConstantBytes{};
    UINT pixelConstantBytes{};
    std::uint64_t vertexPayloadHash{};
    std::uint64_t pixelPayloadHash{};
    std::uint64_t cacheSnapshotToken{};
    std::uint64_t slotSnapshotToken{};
    std::uint64_t objectSnapshotToken{};
    std::uint64_t inputLayoutSnapshotToken{};
    std::uint64_t constantStateSnapshotToken{};
    std::uint64_t snapshotToken{};
};

// R246 binds the validated R245 VS/PS constant buffers to slot b0 on the
// exact immediate context and seals the observed binding state. It remains
// dormant: no translated shaders are bound, no Draw* call is routed, and
// NativeDrawPath is not activated.
struct NativeProgrammableShaderConstantBindingReadiness {
    bool inputValid{};
    bool constantPayloadReceiptReady{};
    bool deviceMatches{};
    bool contextDeviceMatches{};
    bool constantPayloadSnapshotMatches{};
    bool bindingReceiptPresent{};
    bool vertexSlotMatches{};
    bool pixelSlotMatches{};
    bool bindingReady{};
    std::uint64_t ownerGeneration{};
    std::uint64_t slotGeneration{};
    std::uint64_t translationObjectReceiptGeneration{};
    std::uint64_t inputLayoutReceiptGeneration{};
    std::uint64_t constantStateReceiptGeneration{};
    std::uint64_t constantPayloadReceiptGeneration{};
    std::uint64_t constantBindingReceiptGeneration{};
    std::uint64_t cacheKey{};
    std::uint64_t inputLayoutIdentity{};
    UINT vertexConstantBytes{};
    UINT pixelConstantBytes{};
    std::uint64_t vertexPayloadHash{};
    std::uint64_t pixelPayloadHash{};
    std::uint64_t cacheSnapshotToken{};
    std::uint64_t slotSnapshotToken{};
    std::uint64_t objectSnapshotToken{};
    std::uint64_t inputLayoutSnapshotToken{};
    std::uint64_t constantStateSnapshotToken{};
    std::uint64_t constantPayloadSnapshotToken{};
    std::uint64_t snapshotToken{};
};

// R247 binds the already-owned translated VS/PS objects and validated input
// layout on the exact immediate context after the R246 constant-slot receipt.
// It only seals/readbacks programmable object binding state; topology, Draw*
// routing and NativeDrawPath activation remain outside this boundary.
struct NativeProgrammableShaderPipelineBindingReadiness {
    bool inputValid{};
    bool constantBindingReceiptReady{};
    bool deviceMatches{};
    bool contextDeviceMatches{};
    bool constantBindingSnapshotMatches{};
    bool bindingReceiptPresent{};
    bool vertexShaderMatches{};
    bool pixelShaderMatches{};
    bool inputLayoutMatches{};
    bool bindingReady{};
    std::uint64_t ownerGeneration{};
    std::uint64_t slotGeneration{};
    std::uint64_t translationObjectReceiptGeneration{};
    std::uint64_t inputLayoutReceiptGeneration{};
    std::uint64_t constantStateReceiptGeneration{};
    std::uint64_t constantPayloadReceiptGeneration{};
    std::uint64_t constantBindingReceiptGeneration{};
    std::uint64_t pipelineBindingReceiptGeneration{};
    std::uint64_t cacheKey{};
    std::uint64_t inputLayoutIdentity{};
    std::uint64_t cacheSnapshotToken{};
    std::uint64_t slotSnapshotToken{};
    std::uint64_t objectSnapshotToken{};
    std::uint64_t inputLayoutSnapshotToken{};
    std::uint64_t constantStateSnapshotToken{};
    std::uint64_t constantPayloadSnapshotToken{};
    std::uint64_t constantBindingSnapshotToken{};
    std::uint64_t snapshotToken{};
};

// R248 binds one exact directly-translatable D3D9 primitive topology after the
// validated R247 programmable pipeline-object receipt. D3DPT_TRIANGLEFAN stays
// fail-closed here because it requires the separate exact expansion/index path.
// This receipt still does not issue Draw* or activate NativeDrawPath.
struct NativeProgrammableShaderTopologyBindingReadiness {
    bool inputValid{};
    bool pipelineBindingReceiptReady{};
    bool deviceMatches{};
    bool contextDeviceMatches{};
    bool pipelineBindingSnapshotMatches{};
    bool topologyExact{};
    bool topologyReceiptPresent{};
    bool topologyMatches{};
    bool bindingReady{};
    std::uint64_t ownerGeneration{};
    std::uint64_t slotGeneration{};
    std::uint64_t translationObjectReceiptGeneration{};
    std::uint64_t inputLayoutReceiptGeneration{};
    std::uint64_t constantStateReceiptGeneration{};
    std::uint64_t constantPayloadReceiptGeneration{};
    std::uint64_t constantBindingReceiptGeneration{};
    std::uint64_t pipelineBindingReceiptGeneration{};
    std::uint64_t topologyBindingReceiptGeneration{};
    std::uint64_t cacheKey{};
    std::uint64_t inputLayoutIdentity{};
    D3D11_PRIMITIVE_TOPOLOGY translatedTopology =
        D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    std::uint64_t cacheSnapshotToken{};
    std::uint64_t slotSnapshotToken{};
    std::uint64_t objectSnapshotToken{};
    std::uint64_t inputLayoutSnapshotToken{};
    std::uint64_t constantStateSnapshotToken{};
    std::uint64_t constantPayloadSnapshotToken{};
    std::uint64_t constantBindingSnapshotToken{};
    std::uint64_t pipelineBindingSnapshotToken{};
    std::uint64_t snapshotToken{};
};

// R249 binds exact managed slot-0 vertex and index mirrors after the validated
// R248 topology receipt. The receipt seals mirror generations plus stride,
// offsets and index format on the same immediate context. It does not change
// topology, issue Draw*, or activate NativeDrawPath.
struct NativeProgrammableShaderIndexedGeometryBindingReadiness {
    bool inputValid{};
    bool topologyBindingReceiptReady{};
    bool deviceMatches{};
    bool contextDeviceMatches{};
    bool topologyBindingSnapshotMatches{};
    bool vertexBufferCurrent{};
    bool indexBufferCurrent{};
    bool geometryReceiptPresent{};
    bool vertexBufferMatches{};
    bool indexBufferMatches{};
    bool bindingReady{};
    std::uint64_t ownerGeneration{};
    std::uint64_t slotGeneration{};
    std::uint64_t translationObjectReceiptGeneration{};
    std::uint64_t inputLayoutReceiptGeneration{};
    std::uint64_t constantStateReceiptGeneration{};
    std::uint64_t constantPayloadReceiptGeneration{};
    std::uint64_t constantBindingReceiptGeneration{};
    std::uint64_t pipelineBindingReceiptGeneration{};
    std::uint64_t topologyBindingReceiptGeneration{};
    std::uint64_t indexedGeometryBindingReceiptGeneration{};
    std::uint64_t cacheKey{};
    std::uint64_t inputLayoutIdentity{};
    D3D11_PRIMITIVE_TOPOLOGY translatedTopology =
        D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    UINT vertexStride{};
    UINT vertexOffset{};
    DXGI_FORMAT indexFormat = DXGI_FORMAT_UNKNOWN;
    UINT indexOffset{};
    std::uint64_t cacheSnapshotToken{};
    std::uint64_t slotSnapshotToken{};
    std::uint64_t objectSnapshotToken{};
    std::uint64_t inputLayoutSnapshotToken{};
    std::uint64_t constantStateSnapshotToken{};
    std::uint64_t constantPayloadSnapshotToken{};
    std::uint64_t constantBindingSnapshotToken{};
    std::uint64_t pipelineBindingSnapshotToken{};
    std::uint64_t topologyBindingSnapshotToken{};
    std::uint64_t vertexBufferSnapshotToken{};
    std::uint64_t indexBufferSnapshotToken{};
    std::uint64_t snapshotToken{};
};

// R250 binds the exact managed slot-0 vertex mirror for a non-indexed draw
// after the validated R248 topology receipt. The receipt also seals an
// explicitly clear IA index-buffer state on the same immediate context.
// It does not issue Draw* or activate NativeDrawPath.
struct NativeProgrammableShaderNonIndexedGeometryBindingReadiness {
    bool inputValid{};
    bool topologyBindingReceiptReady{};
    bool deviceMatches{};
    bool contextDeviceMatches{};
    bool topologyBindingSnapshotMatches{};
    bool vertexBufferCurrent{};
    bool geometryReceiptPresent{};
    bool vertexBufferMatches{};
    bool indexBufferClear{};
    bool bindingReady{};
    std::uint64_t ownerGeneration{};
    std::uint64_t slotGeneration{};
    std::uint64_t translationObjectReceiptGeneration{};
    std::uint64_t inputLayoutReceiptGeneration{};
    std::uint64_t constantStateReceiptGeneration{};
    std::uint64_t constantPayloadReceiptGeneration{};
    std::uint64_t constantBindingReceiptGeneration{};
    std::uint64_t pipelineBindingReceiptGeneration{};
    std::uint64_t topologyBindingReceiptGeneration{};
    std::uint64_t nonIndexedGeometryBindingReceiptGeneration{};
    std::uint64_t cacheKey{};
    std::uint64_t inputLayoutIdentity{};
    D3D11_PRIMITIVE_TOPOLOGY translatedTopology =
        D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    UINT vertexStride{};
    UINT vertexOffset{};
    std::uint64_t cacheSnapshotToken{};
    std::uint64_t slotSnapshotToken{};
    std::uint64_t objectSnapshotToken{};
    std::uint64_t inputLayoutSnapshotToken{};
    std::uint64_t constantStateSnapshotToken{};
    std::uint64_t constantPayloadSnapshotToken{};
    std::uint64_t constantBindingSnapshotToken{};
    std::uint64_t pipelineBindingSnapshotToken{};
    std::uint64_t topologyBindingSnapshotToken{};
    std::uint64_t vertexBufferSnapshotToken{};
    std::uint64_t snapshotToken{};
};

// R251 seals the exact non-indexed D3D11 Draw argument tuple after a current
// R250 geometry-binding receipt. It revalidates the live IA binding through
// NativeProgrammableShaderPairCache, proves primitive-count translation and
// vertex-buffer byte range, and remains dormant: no Draw* call is issued and
// NativeDrawPath is not activated.
struct NativeProgrammableShaderNonIndexedDirectDispatchReadiness {
    bool inputValid{};
    bool geometryBindingReady{};
    bool geometryBindingSnapshotMatches{};
    bool primitiveExact{};
    bool topologyMatchesGeometry{};
    bool countExact{};
    bool vertexRangeExact{};
    bool dispatchArgumentsExact{};
    bool componentSnapshotsPresent{};
    bool ready{};
    D3D11_PRIMITIVE_TOPOLOGY topology =
        D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    UINT primitiveCount{};
    UINT vertexCount{};
    UINT startVertexLocation{};
    UINT vertexStride{};
    UINT vertexOffset{};
    UINT vertexBufferByteWidth{};
    std::uint64_t geometryBindingSnapshotToken{};
    std::uint64_t vertexBufferSnapshotToken{};
    std::uint64_t snapshotToken{};
};

// R252 seals the indexed D3D9 DrawIndexedPrimitive source-range arguments and
// the exact D3D11 DrawIndexed tuple after a current R249 indexed IA receipt.
// It proves the declared source-vertex interval plus concrete vertex/index
// byte windows against the same MANAGED mirrors. This remains dormant:
// no DrawIndexed call is issued and NativeDrawPath is not activated.
struct NativeProgrammableShaderIndexedDirectDispatchReadiness {
    bool inputValid{};
    bool geometryBindingReady{};
    bool geometryBindingSnapshotMatches{};
    bool primitiveExact{};
    bool topologyMatchesGeometry{};
    bool countExact{};
    bool sourceVertexRangeExact{};
    bool effectiveVertexRangeExact{};
    bool indexBufferRangeExact{};
    bool vertexBufferRangeExact{};
    bool dispatchArgumentsExact{};
    bool componentSnapshotsPresent{};
    bool ready{};
    D3D11_PRIMITIVE_TOPOLOGY topology =
        D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    UINT primitiveCount{};
    UINT indexCount{};
    INT baseVertexLocation{};
    UINT minVertexIndex{};
    UINT numVertices{};
    UINT maxVertexIndex{};
    UINT startIndexLocation{};
    UINT vertexStride{};
    UINT vertexOffset{};
    UINT vertexBufferByteWidth{};
    DXGI_FORMAT indexFormat = DXGI_FORMAT_UNKNOWN;
    UINT indexOffset{};
    UINT indexElementBytes{};
    UINT indexBufferByteWidth{};
    std::uint64_t geometryBindingSnapshotToken{};
    std::uint64_t vertexBufferSnapshotToken{};
    std::uint64_t indexBufferSnapshotToken{};
    std::uint64_t snapshotToken{};
};

// R253 seals the actual MANAGED source-index values consumed by the R252
// indexed direct-dispatch tuple. It reuses the R152 CPU-shadow scanner, binds
// that content proof to the exact R252 receipt and current R119 mirror identity,
// and remains dormant: no DrawIndexed call is issued and NativeDrawPath stays off.
struct NativeProgrammableShaderIndexedSourceValueReadiness {
    bool inputValid{};
    bool directDispatchReady{};
    bool directDispatchSnapshotMatches{};
    bool indexMirrorReady{};
    bool indexMirrorSnapshotMatches{};
    bool indexFormatExact{};
    bool sourceValuesReady{};
    bool sourceValuesMatchDispatchWindow{};
    bool sourceValuesMatchDispatchRange{};
    bool componentSnapshotsPresent{};
    bool ready{};
    D3DFORMAT sourceIndexFormat = D3DFMT_UNKNOWN;
    UINT scanStartIndex{};
    UINT indexCount{};
    UINT minVertexIndex{};
    UINT maxVertexIndex{};
    UINT observedMinIndex{};
    UINT observedMaxIndex{};
    std::uint64_t directDispatchSnapshotToken{};
    std::uint64_t indexMirrorSnapshotToken{};
    std::uint64_t sourceValueSnapshotToken{};
    std::uint64_t sourceContentHash{};
    std::uint64_t snapshotToken{};
};

// R254 reobserves the live IA index-buffer binding after the sealed R253
// source-value receipt. This creates an explicit pre-Draw freshness proof for
// buffer identity, DXGI index format and byte offset without issuing DrawIndexed
// or activating NativeDrawPath.
struct NativeProgrammableShaderIndexedLiveIndexBindingReadiness {
    bool inputValid{};
    bool sourceValueReady{};
    bool sourceValueSnapshotMatches{};
    bool sourceValueFormatMatches{};
    bool indexMirrorReady{};
    bool indexMirrorSnapshotMatches{};
    bool contextDeviceMatches{};
    bool liveIndexBufferMatches{};
    bool liveIndexFormatMatches{};
    bool liveIndexOffsetMatches{};
    bool componentSnapshotsPresent{};
    bool ready{};
    DXGI_FORMAT expectedIndexFormat = DXGI_FORMAT_UNKNOWN;
    DXGI_FORMAT observedIndexFormat = DXGI_FORMAT_UNKNOWN;
    UINT expectedIndexOffset{};
    UINT observedIndexOffset{};
    std::uint64_t expectedIndexBufferIdentity{};
    std::uint64_t observedIndexBufferIdentity{};
    std::uint64_t sourceValueSnapshotToken{};
    std::uint64_t indexMirrorSnapshotToken{};
    std::uint64_t snapshotToken{};
};

// R255 composes the current R252 indexed dispatch tuple, R253 source-value
// proof and R254 fresh live IA binding into one final dormant pre-Draw receipt.
// Every component is recomputed from the current device/context state; this does
// not issue DrawIndexed or activate NativeDrawPath.
struct NativeProgrammableShaderIndexedPreDrawReadiness {
    bool inputValid{};
    bool directDispatchReady{};
    bool directDispatchSnapshotMatches{};
    bool sourceValueReady{};
    bool sourceValueSnapshotMatches{};
    bool liveIndexBindingReady{};
    bool liveIndexBindingSnapshotMatches{};
    bool dispatchSourceLineageMatches{};
    bool sourceLiveLineageMatches{};
    bool componentSnapshotsPresent{};
    bool ready{};
    UINT indexCount{};
    UINT startIndexLocation{};
    INT baseVertexIndex{};
    UINT minVertexIndex{};
    UINT numVertices{};
    DXGI_FORMAT indexFormat = DXGI_FORMAT_UNKNOWN;
    UINT indexOffset{};
    std::uint64_t directDispatchSnapshotToken{};
    std::uint64_t sourceValueSnapshotToken{};
    std::uint64_t liveIndexBindingSnapshotToken{};
    std::uint64_t snapshotToken{};
};

enum class NativeProgrammableShaderDrawCandidateKind : std::uint8_t {
    None = 0,
    NonIndexed = 1,
    Indexed = 2,
};

// R256 normalizes either a validated R251 non-indexed dispatch receipt or a
// validated R255 indexed pre-Draw receipt into one branch-tagged dormant
// candidate. This is deliberately not an activation structure: it owns no
// device context, issues no Draw/DrawIndexed call and does not change
// NativeDrawPath state.
struct NativeProgrammableShaderDrawCandidateReadiness {
    bool inputValid{};
    bool selectedReceiptReady{};
    bool selectedReceiptSnapshotMatches{};
    bool componentSnapshotsPresent{};
    bool ready{};
    NativeProgrammableShaderDrawCandidateKind kind =
        NativeProgrammableShaderDrawCandidateKind::None;
    bool indexed{};
    UINT elementCount{};
    UINT startLocation{};
    INT baseVertexIndex{};
    UINT minVertexIndex{};
    UINT numVertices{};
    DXGI_FORMAT indexFormat = DXGI_FORMAT_UNKNOWN;
    UINT indexOffset{};
    std::uint64_t sourceReceiptSnapshotToken{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] NativeProgrammableShaderDrawCandidateReadiness
compose_programmable_draw_candidate_readiness(
    const NativeProgrammableShaderNonIndexedDirectDispatchReadiness& dispatch,
    std::uint64_t dispatchSnapshotToken) noexcept;

[[nodiscard]] NativeProgrammableShaderDrawCandidateReadiness
compose_programmable_draw_candidate_readiness(
    const NativeProgrammableShaderIndexedPreDrawReadiness& preDraw,
    std::uint64_t preDrawSnapshotToken) noexcept;

[[nodiscard]] bool validate_programmable_draw_candidate_snapshot(
    const NativeProgrammableShaderNonIndexedDirectDispatchReadiness& dispatch,
    std::uint64_t dispatchSnapshotToken,
    std::uint64_t candidateSnapshotToken) noexcept;

[[nodiscard]] bool validate_programmable_draw_candidate_snapshot(
    const NativeProgrammableShaderIndexedPreDrawReadiness& preDraw,
    std::uint64_t preDrawSnapshotToken,
    std::uint64_t candidateSnapshotToken) noexcept;

// R257 creates a dormant pre-activation review receipt from one current R256
// candidate. "ready" means the candidate is internally coherent and safe to
// carry to a later activation review; it explicitly does NOT authorize a
// D3D11 Draw* call or NativeDrawPath activation. This keeps F23's diagnostic
// evidence separate from any future activation proof.
struct NativeProgrammableShaderDormantPreActivationReadiness {
    bool inputValid{};
    bool candidateReady{};
    bool candidateSnapshotMatches{};
    bool candidatePayloadSnapshotMatches{};
    bool candidateKindValid{};
    bool diagnosticOnly{};
    bool activationProofPresent{};
    bool nativeDrawPathActivationAllowed{};
    bool drawDispatchAuthorized{};
    bool boundaryPreserved{};
    bool ready{};
    NativeProgrammableShaderDrawCandidateKind kind =
        NativeProgrammableShaderDrawCandidateKind::None;
    bool indexed{};
    UINT elementCount{};
    UINT startLocation{};
    INT baseVertexIndex{};
    UINT minVertexIndex{};
    UINT numVertices{};
    DXGI_FORMAT indexFormat = DXGI_FORMAT_UNKNOWN;
    UINT indexOffset{};
    std::uint64_t sourceReceiptSnapshotToken{};
    std::uint64_t candidateSnapshotToken{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] NativeProgrammableShaderDormantPreActivationReadiness
compose_programmable_dormant_pre_activation_readiness(
    const NativeProgrammableShaderDrawCandidateReadiness& candidate,
    std::uint64_t candidateSnapshotToken) noexcept;

[[nodiscard]] bool validate_programmable_dormant_pre_activation_snapshot(
    const NativeProgrammableShaderDrawCandidateReadiness& candidate,
    std::uint64_t candidateSnapshotToken,
    std::uint64_t preActivationSnapshotToken) noexcept;

// R258 revalidates the selected R256 source branch against current device /
// context / resource state before carrying the dormant R257 handoff any
// further. The current R251 or R255 receipt is recomputed by the pair cache;
// success only means that the old R256/R257 identities are still fresh. It
// remains diagnostic-only and cannot authorize Draw* or NativeDrawPath.
// R290 additionally seals the exact R239 cache key into this receipt so the
// later R259 handoff can reject evidence assembled from different shader pairs.
struct NativeProgrammableShaderDormantSourceRevalidationReadiness {
    bool inputValid{};
    bool sourceReceiptReady{};
    bool sourceReceiptSnapshotPresent{};
    bool candidateReady{};
    bool candidateSnapshotMatches{};
    bool preActivationReady{};
    bool preActivationSnapshotMatches{};
    bool sourceLineageMatches{};
    bool candidateLineageMatches{};
    bool boundaryPreserved{};
    bool ready{};
    NativeProgrammableShaderDrawCandidateKind kind =
        NativeProgrammableShaderDrawCandidateKind::None;
    bool indexed{};
    UINT elementCount{};
    UINT startLocation{};
    INT baseVertexIndex{};
    UINT minVertexIndex{};
    UINT numVertices{};
    DXGI_FORMAT indexFormat = DXGI_FORMAT_UNKNOWN;
    UINT indexOffset{};
    std::uint64_t cacheKey{};
    std::uint64_t currentSourceReceiptSnapshotToken{};
    std::uint64_t candidateSnapshotToken{};
    std::uint64_t preActivationSnapshotToken{};
    std::uint64_t snapshotToken{};
};

// R260 turns the current R258 source receipt plus the exact MANAGED geometry
// mirrors into an explicit F18 resource-behavior review receipt. The receipt
// revalidates descriptor, mutation-plan and Reset-lifetime state on the actual
// vertex/index mirrors. Texture and output-resource behavior are deliberately
// still unproven, so this is geometry evidence only and cannot close F18 or
// authorize Draw*, NativeDrawPath, or any runtime-visible route.
struct NativeProgrammableShaderResourceBehaviorReadiness {
    bool inputValid{};
    bool sourceRevalidationReady{};
    bool sourceRevalidationSnapshotMatches{};
    bool sourceRevalidationPayloadSnapshotMatches{};
    bool vertexMirrorReady{};
    bool vertexMirrorSnapshotMatches{};
    bool indexMirrorRequired{};
    bool indexMirrorReady{};
    bool indexMirrorSnapshotMatches{};
    bool geometryResourceBehaviorExact{};
    bool textureResourceBehaviorProofPresent{};
    bool outputResourceBehaviorProofPresent{};
    bool fullResourceBehaviorProofPresent{};
    bool diagnosticOnly{};
    bool boundaryPreserved{};
    bool reviewReady{};
    NativeProgrammableShaderDrawCandidateKind kind =
        NativeProgrammableShaderDrawCandidateKind::None;
    bool indexed{};
    std::uint32_t missingResourceScopeMask{};
    std::uint64_t sourceRevalidationSnapshotToken{};
    std::uint64_t vertexMirrorSnapshotToken{};
    std::uint64_t indexMirrorSnapshotToken{};
    std::uint64_t reviewSnapshotToken{};
};

[[nodiscard]] NativeProgrammableShaderResourceBehaviorReadiness
compose_programmable_resource_behavior_readiness(
    const NativeProgrammableShaderDormantSourceRevalidationReadiness&
        sourceRevalidation,
    std::uint64_t sourceRevalidationSnapshotToken,
    ID3D11Device* expectedDevice,
    const NativeManagedBufferShadow& vertexMirror,
    std::uint64_t vertexMirrorSnapshotToken,
    const NativeManagedBufferShadow* indexMirror,
    std::uint64_t indexMirrorSnapshotToken) noexcept;

[[nodiscard]] bool
validate_programmable_resource_behavior_readiness_snapshot(
    const NativeProgrammableShaderDormantSourceRevalidationReadiness&
        sourceRevalidation,
    std::uint64_t sourceRevalidationSnapshotToken,
    ID3D11Device* expectedDevice,
    const NativeManagedBufferShadow& vertexMirror,
    std::uint64_t vertexMirrorSnapshotToken,
    const NativeManagedBufferShadow* indexMirror,
    std::uint64_t indexMirrorSnapshotToken,
    std::uint64_t reviewSnapshotToken) noexcept;

// R261 binds the current R260 geometry receipt to one exact MANAGED texture
// stage readiness snapshot. The required mask is explicit and every required
// stage must have current shadow, mirror lifetime, device and descriptor
// evidence. This proves texture resource behavior only for that supplied stage
// set; output-resource behavior stays absent and no shader semantic claim is
// inferred from the mask.
struct NativeProgrammableShaderTextureResourceBehaviorReadiness {
    bool inputValid{};
    bool geometryReviewReady{};
    bool geometrySnapshotMatches{};
    bool geometryPayloadSnapshotMatches{};
    bool requiredTextureScopePresent{};
    bool textureStagesInputValid{};
    bool textureStageSnapshotMatches{};
    bool geometryResourceBehaviorExact{};
    bool textureResourceBehaviorExact{};
    bool outputResourceBehaviorProofPresent{};
    bool fullResourceBehaviorProofPresent{};
    bool diagnosticOnly{};
    bool boundaryPreserved{};
    bool reviewReady{};
    NativeProgrammableShaderDrawCandidateKind kind =
        NativeProgrammableShaderDrawCandidateKind::None;
    bool indexed{};
    std::uint32_t requiredTextureMask{};
    std::uint32_t readyTextureMask{};
    std::uint32_t pendingTextureMask{};
    std::uint32_t missingResourceScopeMask{};
    std::uint64_t sourceRevalidationSnapshotToken{};
    std::uint64_t geometrySnapshotToken{};
    std::uint64_t textureStageSnapshotToken{};
    std::uint64_t reviewSnapshotToken{};
};

[[nodiscard]] NativeProgrammableShaderTextureResourceBehaviorReadiness
compose_programmable_texture_resource_behavior_readiness(
    const NativeProgrammableShaderResourceBehaviorReadiness& geometryBehavior,
    std::uint64_t geometrySnapshotToken,
    const NativeManagedTextureRegistry& textureRegistry,
    const void* const* textureKeys,
    std::size_t textureCount,
    ID3D11Device* expectedDevice,
    const NativeManagedTextureStageReadiness& textureStages,
    std::uint64_t textureStageSnapshotToken) noexcept;

[[nodiscard]] bool
validate_programmable_texture_resource_behavior_readiness_snapshot(
    const NativeProgrammableShaderResourceBehaviorReadiness& geometryBehavior,
    std::uint64_t geometrySnapshotToken,
    const NativeManagedTextureRegistry& textureRegistry,
    const void* const* textureKeys,
    std::size_t textureCount,
    ID3D11Device* expectedDevice,
    const NativeManagedTextureStageReadiness& textureStages,
    std::uint64_t textureStageSnapshotToken,
    std::uint64_t reviewSnapshotToken) noexcept;

// R262 binds the current R261 geometry+texture receipt to the exact live
// output surface pair and OM target binding. R119 descriptor/generation identity
// plus R145 RTV/DSV/UAV-clear observation close the remaining F18 output-resource
// scope. This is still diagnostic-only: F21 remains absent and no Draw* or
// NativeDrawPath activation authority is created.
struct NativeProgrammableShaderOutputResourceBehaviorReadiness {
    bool inputValid{};
    bool textureReviewReady{};
    bool textureSnapshotMatches{};
    // R302 requires the stored R261 token to match its reconstructed payload.
    bool texturePayloadSnapshotMatches{};
    bool surfacePairReady{};
    bool surfacePairSnapshotMatches{};
    bool surfaceBindingReady{};
    bool surfaceBindingSnapshotMatches{};
    bool geometryResourceBehaviorExact{};
    bool textureResourceBehaviorExact{};
    bool outputResourceBehaviorExact{};
    bool fullResourceBehaviorProofPresent{};
    bool diagnosticOnly{};
    bool boundaryPreserved{};
    bool reviewReady{};
    NativeProgrammableShaderDrawCandidateKind kind =
        NativeProgrammableShaderDrawCandidateKind::None;
    bool indexed{};
    std::uint32_t missingResourceScopeMask{};
    std::uint64_t sourceRevalidationSnapshotToken{};
    std::uint64_t textureBehaviorSnapshotToken{};
    std::uint64_t surfacePairSnapshotToken{};
    std::uint64_t surfaceBindingSnapshotToken{};
    std::uint64_t reviewSnapshotToken{};
};

[[nodiscard]] NativeProgrammableShaderOutputResourceBehaviorReadiness
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
    std::uint64_t surfaceBindingSnapshotToken) noexcept;

[[nodiscard]] bool
validate_programmable_output_resource_behavior_readiness_snapshot(
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
    std::uint64_t reviewSnapshotToken) noexcept;

// R273 seals the source-derived R272 constant/sampler mapping plan to the
// same exact R239/R271 programmable pair identity that a later R263
// semantic-translation review will consume. This is a diagnostic handoff only;
// it does not create/bind D3D11 shaders or authorize NativeDrawPath/Draw*.
struct NativeProgrammableShaderSourceMappingHandoff {
    bool inputValid{};
    bool sourceIdentityExact{};
    bool sourceSemanticReceiptExact{};
    bool mappingPlanExact{};
    bool sourceReceiptIdentityMatches{};
    bool mappingPlanIdentityMatches{};
    bool constantRegisterMappingExact{};
    bool samplerMappingExact{};
    bool diagnosticOnly{};
    bool boundaryPreserved{};
    bool reviewReady{};
    std::uint64_t cacheKey{};
    std::uint64_t pairSemanticHash{};
    std::uint64_t vertexRegisterSemanticsHash{};
    std::uint64_t pixelRegisterSemanticsHash{};
    std::uint64_t constantMappingHash{};
    std::uint64_t samplerMappingHash{};
    std::uint64_t mappingPlanRevisionHash{};
    std::uint64_t mappingSemanticContractHash{};
    std::uint64_t reviewSnapshotToken{};
};

[[nodiscard]] NativeProgrammableShaderSourceMappingHandoff
compose_programmable_shader_source_mapping_handoff(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const ProgrammableShaderPairSourceSemanticEvidence& sourceReceipt,
    const ProgrammableShaderRegisterMappingPlanEvidence& mappingPlan) noexcept;

[[nodiscard]] bool
validate_programmable_shader_source_mapping_handoff_snapshot(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const ProgrammableShaderPairSourceSemanticEvidence& sourceReceipt,
    const ProgrammableShaderRegisterMappingPlanEvidence& mappingPlan,
    std::uint64_t reviewSnapshotToken) noexcept;

// R276 derives a deterministic, diagnostic-only target-semantic plan from
// exact R271 source semantics, R268 stage linkage and the sealed R273 mapping
// handoff. It describes provenance-bound target semantic identities only; it
// does not emit shader bytecode, create/bind D3D11 shaders or authorize Draw*.
struct NativeProgrammableShaderSemanticTranslationPlanEvidence {
    bool inputValid{};
    bool sourceSemanticReceiptExact{};
    bool interfaceLinkageExact{};
    bool sourceMappingHandoffReady{};
    bool sourceMappingHandoffSnapshotMatches{};
    bool provenanceMatches{};
    bool vertexSemanticExact{};
    bool pixelSemanticExact{};
    bool diagnosticOnly{};
    bool boundaryPreserved{};
    bool reviewReady{};
    std::uint64_t cacheKey{};
    std::uint64_t sourcePairSemanticHash{};
    std::uint64_t interfaceLinkHash{};
    std::uint64_t sourceConstantMappingHash{};
    std::uint64_t sourceSamplerMappingHash{};
    std::uint64_t targetVertexSemanticHash{};
    std::uint64_t targetPixelSemanticHash{};
    std::uint64_t translatorRevisionHash{};
    std::uint64_t semanticContractHash{};
    std::uint64_t sourceMappingHandoffSnapshotToken{};
    std::uint64_t reviewSnapshotToken{};
};

[[nodiscard]] NativeProgrammableShaderSemanticTranslationPlanEvidence
derive_programmable_shader_semantic_translation_plan(
    const ProgrammableShaderPairSourceSemanticEvidence& sourceReceipt,
    const ProgrammableShaderInterfaceLinkageEvidence& sourceInterfaceLinkage,
    const NativeProgrammableShaderSourceMappingHandoff& sourceMappingHandoff,
    std::uint64_t sourceMappingHandoffSnapshotToken) noexcept;

[[nodiscard]] bool
validate_programmable_shader_semantic_translation_plan_snapshot(
    const NativeProgrammableShaderSemanticTranslationPlanEvidence& plan,
    std::uint64_t reviewSnapshotToken) noexcept;

// R279 seals the exact ownership/lifetime prerequisites that a future R242
// translated programmable VS/PS object receipt must prove. It binds the R239
// pair identity to the R276 target-semantic plan and records the required
// owner/slot/object generations and same-device attachment boundary without
// creating or binding any D3D11 object.
struct NativeProgrammableShaderTranslationObjectPrerequisiteEvidence {
    bool inputValid{};
    bool sourceIdentityExact{};
    bool translationPlanReady{};
    bool translationPlanSnapshotMatches{};
    bool cacheIdentityMatches{};
    bool cacheOwnerGenerationRequired{};
    bool translationSlotGenerationRequired{};
    bool translationObjectReceiptGenerationRequired{};
    bool sameDeviceObjectPairRequired{};
    bool cacheSnapshotRequired{};
    bool slotSnapshotRequired{};
    bool diagnosticOnly{};
    bool boundaryPreserved{};
    bool reviewReady{};
    std::uint64_t cacheKey{};
    std::uint64_t targetVertexSemanticHash{};
    std::uint64_t targetPixelSemanticHash{};
    std::uint64_t translationPlanSnapshotToken{};
    std::uint64_t reviewSnapshotToken{};
};

[[nodiscard]] NativeProgrammableShaderTranslationObjectPrerequisiteEvidence
derive_programmable_shader_translation_object_prerequisite(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence& translationPlan,
    std::uint64_t translationPlanSnapshotToken) noexcept;

[[nodiscard]] bool
validate_programmable_shader_translation_object_prerequisite_snapshot(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence& translationPlan,
    std::uint64_t translationPlanSnapshotToken,
    std::uint64_t reviewSnapshotToken) noexcept;

// R280 seals the exact source-to-object creation handoff that must precede
// any future R242 programmable VS/PS object creation. It binds exact R264
// source bytes to the R276 target-semantic plan and R279 ownership/lifetime
// prerequisite. This remains diagnostic-only: it never compiles/creates/binds
// D3D11 shaders and never authorizes NativeDrawPath/Draw*.
struct NativeProgrammableShaderObjectCreationHandoffEvidence {
    bool inputValid{};
    bool sourceIdentityExact{};
    bool vertexSourceExact{};
    bool pixelSourceExact{};
    bool sourcePairMatches{};
    bool translationPlanReady{};
    bool translationPlanSnapshotMatches{};
    bool objectPrerequisiteReady{};
    bool objectPrerequisiteSnapshotMatches{};
    bool cacheIdentityMatches{};
    bool objectCreationAuthorized{};
    bool diagnosticOnly{};
    bool boundaryPreserved{};
    bool reviewReady{};
    std::uint64_t cacheKey{};
    DWORD vertexVersionToken{};
    DWORD pixelVersionToken{};
    UINT vertexByteSize{};
    UINT pixelByteSize{};
    std::uint64_t vertexBytecodeHash{};
    std::uint64_t pixelBytecodeHash{};
    std::uint64_t targetVertexSemanticHash{};
    std::uint64_t targetPixelSemanticHash{};
    std::uint64_t translationPlanSnapshotToken{};
    std::uint64_t objectPrerequisiteSnapshotToken{};
    std::uint64_t reviewSnapshotToken{};
};

[[nodiscard]] NativeProgrammableShaderObjectCreationHandoffEvidence
compose_programmable_shader_object_creation_handoff(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const ProgrammableShaderFunctionSourceEvidence& vertexSource,
    const ProgrammableShaderFunctionSourceEvidence& pixelSource,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence& translationPlan,
    std::uint64_t translationPlanSnapshotToken,
    const NativeProgrammableShaderTranslationObjectPrerequisiteEvidence&
        objectPrerequisite,
    std::uint64_t objectPrerequisiteSnapshotToken) noexcept;

[[nodiscard]] bool
validate_programmable_shader_object_creation_handoff_snapshot(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const ProgrammableShaderFunctionSourceEvidence& vertexSource,
    const ProgrammableShaderFunctionSourceEvidence& pixelSource,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence& translationPlan,
    std::uint64_t translationPlanSnapshotToken,
    const NativeProgrammableShaderTranslationObjectPrerequisiteEvidence&
        objectPrerequisite,
    std::uint64_t objectPrerequisiteSnapshotToken,
    std::uint64_t reviewSnapshotToken) noexcept;

// R281 defines the provenance identity that a future translated VS/PS
// bytecode artifact receipt must carry before R242 object creation can be
// considered. It intentionally does not materialize target bytecode, compile
// shaders, create/bind D3D11 objects or authorize NativeDrawPath/Draw*.
struct NativeProgrammableShaderTranslatedArtifactReceiptEvidence {
    bool inputValid{};
    bool sourceIdentityExact{};
    bool objectCreationHandoffReady{};
    bool objectCreationHandoffSnapshotMatches{};
    bool translationPlanReady{};
    bool translationPlanSnapshotMatches{};
    bool cacheIdentityMatches{};
    bool targetVertexIdentityDefined{};
    bool targetPixelIdentityDefined{};
    bool targetBytecodeReceiptRequired{};
    bool targetBytecodeMaterialized{};
    bool objectCreationAuthorized{};
    bool diagnosticOnly{};
    bool boundaryPreserved{};
    bool reviewReady{};
    std::uint64_t cacheKey{};
    DWORD vertexVersionToken{};
    DWORD pixelVersionToken{};
    std::uint64_t sourceVertexBytecodeHash{};
    std::uint64_t sourcePixelBytecodeHash{};
    std::uint64_t targetVertexSemanticHash{};
    std::uint64_t targetPixelSemanticHash{};
    std::uint64_t translatorRevisionHash{};
    std::uint64_t semanticContractHash{};
    std::uint64_t targetVertexBytecodeReceiptIdentity{};
    std::uint64_t targetPixelBytecodeReceiptIdentity{};
    std::uint64_t objectCreationHandoffSnapshotToken{};
    std::uint64_t translationPlanSnapshotToken{};
    std::uint64_t reviewSnapshotToken{};
};

[[nodiscard]] NativeProgrammableShaderTranslatedArtifactReceiptEvidence
derive_programmable_shader_translated_artifact_receipt(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderObjectCreationHandoffEvidence& creationHandoff,
    std::uint64_t creationHandoffSnapshotToken,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence& translationPlan,
    std::uint64_t translationPlanSnapshotToken) noexcept;

[[nodiscard]] bool
validate_programmable_shader_translated_artifact_receipt_snapshot(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderObjectCreationHandoffEvidence& creationHandoff,
    std::uint64_t creationHandoffSnapshotToken,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence& translationPlan,
    std::uint64_t translationPlanSnapshotToken,
    std::uint64_t reviewSnapshotToken) noexcept;

// R282 seals the deterministic compile/materialization contract that must
// produce target bytes matching the R281 translated artifact identities.
// It binds the existing native DX11 compiler policy (main, vs_4_0/ps_4_0,
// strictness + O3) to the exact R281/R276 provenance, but deliberately does
// not invoke D3DCompile, materialize bytecode, create shaders or authorize Draw*.
struct NativeProgrammableShaderTargetMaterializationContractEvidence {
    bool inputValid{};
    bool sourceIdentityExact{};
    bool translatedArtifactReceiptReady{};
    bool translatedArtifactReceiptSnapshotMatches{};
    bool translationPlanReady{};
    bool translationPlanSnapshotMatches{};
    bool cacheIdentityMatches{};
    bool targetArtifactIdentityMatches{};
    bool entryPointExact{};
    bool vertexTargetProfileExact{};
    bool pixelTargetProfileExact{};
    bool compileFlagsExact{};
    bool targetBytecodeMaterializationRequired{};
    bool targetBytecodeMaterialized{};
    bool compilationAuthorized{};
    bool objectCreationAuthorized{};
    bool diagnosticOnly{};
    bool boundaryPreserved{};
    bool reviewReady{};
    std::uint64_t cacheKey{};
    std::uint64_t targetVertexBytecodeReceiptIdentity{};
    std::uint64_t targetPixelBytecodeReceiptIdentity{};
    std::uint64_t entryPointHash{};
    std::uint64_t vertexTargetProfileHash{};
    std::uint64_t pixelTargetProfileHash{};
    std::uint32_t compileFlags{};
    std::uint64_t translatorRevisionHash{};
    std::uint64_t semanticContractHash{};
    std::uint64_t vertexCompileContractIdentity{};
    std::uint64_t pixelCompileContractIdentity{};
    std::uint64_t translatedArtifactReceiptSnapshotToken{};
    std::uint64_t translationPlanSnapshotToken{};
    std::uint64_t reviewSnapshotToken{};
};

[[nodiscard]] NativeProgrammableShaderTargetMaterializationContractEvidence
derive_programmable_shader_target_materialization_contract(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderTranslatedArtifactReceiptEvidence&
        translatedArtifactReceipt,
    std::uint64_t translatedArtifactReceiptSnapshotToken,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence& translationPlan,
    std::uint64_t translationPlanSnapshotToken) noexcept;

[[nodiscard]] bool
validate_programmable_shader_target_materialization_contract_snapshot(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderTranslatedArtifactReceiptEvidence&
        translatedArtifactReceipt,
    std::uint64_t translatedArtifactReceiptSnapshotToken,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence& translationPlan,
    std::uint64_t translationPlanSnapshotToken,
    std::uint64_t reviewSnapshotToken) noexcept;

// R283 materializes target HLSL/DXBC only for the bounded SM3 DCL+MOV subset
// proven by the current source evidence. The resulting bytes are carried in
// this diagnostic receipt and are sealed to the exact R281/R282/R276
// provenance. Shader object creation/binding and NativeDrawPath/Draw* remain
// explicitly unauthorized.
struct NativeProgrammableShaderTargetBytecodeMaterializationEvidence {
    bool inputValid{};
    bool sourceIdentityExact{};
    bool vertexSourceExact{};
    bool pixelSourceExact{};
    bool translatedArtifactReceiptReady{};
    bool translatedArtifactReceiptSnapshotMatches{};
    bool targetMaterializationContractReady{};
    bool targetMaterializationContractSnapshotMatches{};
    bool translationPlanReady{};
    bool translationPlanSnapshotMatches{};
    bool provenanceMatches{};
    bool vertexSubsetSupported{};
    bool pixelSubsetSupported{};
    bool vertexSourceMaterialized{};
    bool pixelSourceMaterialized{};
    bool vertexCompilationSucceeded{};
    bool pixelCompilationSucceeded{};
    bool targetBytecodeMaterialized{};
    bool objectCreationAuthorized{};
    bool diagnosticOnly{};
    bool boundaryPreserved{};
    bool reviewReady{};
    std::uint64_t cacheKey{};
    DWORD vertexVersionToken{};
    DWORD pixelVersionToken{};
    std::uint64_t sourceVertexBytecodeHash{};
    std::uint64_t sourcePixelBytecodeHash{};
    std::uint64_t targetVertexBytecodeReceiptIdentity{};
    std::uint64_t targetPixelBytecodeReceiptIdentity{};
    std::uint64_t vertexCompileContractIdentity{};
    std::uint64_t pixelCompileContractIdentity{};
    std::uint64_t targetVertexSemanticHash{};
    std::uint64_t targetPixelSemanticHash{};
    UINT vertexTranslatedSourceBytes{};
    UINT pixelTranslatedSourceBytes{};
    std::uint64_t vertexTranslatedSourceHash{};
    std::uint64_t pixelTranslatedSourceHash{};
    UINT vertexTargetBytecodeBytes{};
    UINT pixelTargetBytecodeBytes{};
    std::uint64_t vertexTargetBytecodeHash{};
    std::uint64_t pixelTargetBytecodeHash{};
    std::uint64_t vertexMaterializedArtifactIdentity{};
    std::uint64_t pixelMaterializedArtifactIdentity{};
    std::uint64_t materializerRevisionHash{};
    std::uint64_t semanticSubsetContractHash{};
    std::uint64_t translatedArtifactReceiptSnapshotToken{};
    std::uint64_t targetMaterializationContractSnapshotToken{};
    std::uint64_t translationPlanSnapshotToken{};
    std::uint64_t reviewSnapshotToken{};
    std::vector<std::uint8_t> vertexTargetBytecode;
    std::vector<std::uint8_t> pixelTargetBytecode;
};

[[nodiscard]] NativeProgrammableShaderTargetBytecodeMaterializationEvidence
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
    std::uint64_t translationPlanSnapshotToken) noexcept;

[[nodiscard]] bool
validate_programmable_shader_target_bytecode_materialization_snapshot(
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
    std::uint64_t reviewSnapshotToken) noexcept;

// R284 consumes exact R283 DXBC into a real same-device D3D11 VS/PS pair and
// attaches it to the existing R240/R241 cache ownership boundary, yielding the
// concrete R242 translation-object receipt. It creates/owns shader objects only:
// no shader/context binding, shaderTranslationExact promotion, NativeDrawPath,
// Draw or DrawIndexed authority is granted here.
class NativeProgrammableShaderPairCache;

struct NativeProgrammableShaderObjectMaterializationEvidence {
    bool inputValid{};
    bool sourceIdentityExact{};
    bool objectPrerequisiteReady{};
    bool objectPrerequisiteSnapshotMatches{};
    bool creationHandoffReady{};
    bool creationHandoffSnapshotMatches{};
    bool targetBytecodeMaterializationReady{};
    bool targetBytecodeMaterializationSnapshotMatches{};
    bool provenanceMatches{};
    bool cacheInitialized{};
    bool cacheEntryReady{};
    bool cacheSnapshotMatches{};
    bool translationSlotReserved{};
    bool translationSlotReady{};
    bool slotSnapshotMatches{};
    bool objectsAbsentBeforeMaterialization{};
    bool vertexObjectCreated{};
    bool pixelObjectCreated{};
    bool objectsAttached{};
    bool objectDevicesMatch{};
    bool translationObjectReceiptReady{};
    bool objectBindingAuthorized{};
    bool diagnosticOnly{};
    bool boundaryPreserved{};
    bool reviewReady{};
    std::uint64_t cacheKey{};
    std::uint64_t targetVertexBytecodeHash{};
    std::uint64_t targetPixelBytecodeHash{};
    std::uint64_t vertexMaterializedArtifactIdentity{};
    std::uint64_t pixelMaterializedArtifactIdentity{};
    std::uint64_t ownerGeneration{};
    std::uint64_t slotGeneration{};
    std::uint64_t translationObjectReceiptGeneration{};
    std::uint64_t objectMaterializerRevisionHash{};
    std::uint64_t objectPrerequisiteSnapshotToken{};
    std::uint64_t creationHandoffSnapshotToken{};
    std::uint64_t targetBytecodeMaterializationSnapshotToken{};
    std::uint64_t cacheSnapshotToken{};
    std::uint64_t slotSnapshotToken{};
    std::uint64_t translationObjectSnapshotToken{};
    std::uint64_t reviewSnapshotToken{};
};

[[nodiscard]] NativeProgrammableShaderObjectMaterializationEvidence
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
    std::uint64_t targetBytecodeMaterializationSnapshotToken) noexcept;

[[nodiscard]] bool
validate_programmable_shader_object_materialization_snapshot(
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
    std::uint64_t reviewSnapshotToken) noexcept;

// R275 seals one dormant translated-semantic observation into a tamper-evident
// receipt bound to the exact R239 pair, R242 translated-object ownership, R273
// source-mapping handoff and R276 source-derived semantic translation plan.
// This receipt remains diagnostic evidence only and never creates/binds shaders
// or authorizes NativeDrawPath/Draw*.
struct NativeProgrammableShaderTranslatedSemanticReceipt {
    bool inputValid{};
    bool sourceIdentityExact{};
    bool translationObjectReady{};
    bool translationObjectSnapshotMatches{};
    bool sourceMappingHandoffReady{};
    bool sourceMappingHandoffSnapshotMatches{};
    bool translationPlanReady{};
    bool translationPlanSnapshotMatches{};
    bool cacheIdentityMatches{};
    bool vertexSemanticExact{};
    bool pixelSemanticExact{};
    bool constantRegisterMappingExact{};
    bool samplerMappingExact{};
    bool diagnosticOnly{};
    bool boundaryPreserved{};
    bool reviewReady{};
    std::uint64_t cacheKey{};
    DWORD vertexVersionToken{};
    DWORD pixelVersionToken{};
    std::uint64_t vertexBytecodeHash{};
    std::uint64_t pixelBytecodeHash{};
    std::uint64_t translatedVertexSemanticHash{};
    std::uint64_t translatedPixelSemanticHash{};
    std::uint64_t translatorRevisionHash{};
    std::uint64_t semanticContractHash{};
    std::uint64_t sourcePairSemanticHash{};
    std::uint64_t sourceConstantMappingHash{};
    std::uint64_t sourceSamplerMappingHash{};
    std::uint64_t sourceMappingPlanRevisionHash{};
    std::uint64_t sourceMappingSemanticContractHash{};
    std::uint64_t translationObjectSnapshotToken{};
    std::uint64_t sourceMappingHandoffSnapshotToken{};
    std::uint64_t translationPlanSnapshotToken{};
    std::uint64_t reviewSnapshotToken{};
};

[[nodiscard]] NativeProgrammableShaderTranslatedSemanticReceipt
compose_programmable_shader_translated_semantic_receipt(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderTranslationObjectReadiness& translationObject,
    std::uint64_t translationObjectSnapshotToken,
    const NativeProgrammableShaderSourceMappingHandoff& sourceMappingHandoff,
    std::uint64_t sourceMappingHandoffSnapshotToken,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence& translationPlan,
    std::uint64_t translationPlanSnapshotToken) noexcept;

[[nodiscard]] bool
validate_programmable_shader_translated_semantic_receipt_snapshot(
    const NativeProgrammableShaderTranslatedSemanticReceipt& receipt,
    std::uint64_t reviewSnapshotToken) noexcept;

// R263 seals one exact F21 programmable-shader semantic-translation proof.
// R275 now carries the translated-semantic scalar bundle as one snapshot-sealed
// receipt. R263 consumes that receipt plus exact R243 input-layout and R268
// linkage evidence. This review path never routes Draw* or activates
// NativeDrawPath.
struct NativeProgrammableShaderSemanticTranslationReadiness {
    bool inputValid{};
    bool sourceIdentityExact{};
    bool translationObjectReady{};
    bool translationObjectSnapshotMatches{};
    bool inputLayoutReady{};
    bool inputLayoutSnapshotMatches{};
    bool cacheIdentityMatches{};
    bool translatedSemanticReceiptReady{};
    bool translatedSemanticReceiptSnapshotMatches{};
    bool translatedSemanticIdentityMatches{};
    bool sourceMappingHandoffReady{};
    bool sourceMappingHandoffSnapshotMatches{};
    bool sourceMappingIdentityMatches{};
    bool vertexSemanticExact{};
    bool pixelSemanticExact{};
    bool interfaceSourceIdentityMatches{};
    bool interfaceLinkExact{};
    bool semanticProofPresent{};
    bool diagnosticOnly{};
    bool boundaryPreserved{};
    bool reviewReady{};
    std::uint64_t cacheKey{};
    DWORD vertexVersionToken{};
    DWORD pixelVersionToken{};
    std::uint64_t vertexBytecodeHash{};
    std::uint64_t pixelBytecodeHash{};
    std::uint64_t translatedVertexSemanticHash{};
    std::uint64_t translatedPixelSemanticHash{};
    std::uint64_t interfaceLinkHash{};
    std::uint64_t translatorRevisionHash{};
    std::uint64_t semanticContractHash{};
    std::uint64_t sourcePairSemanticHash{};
    std::uint64_t sourceConstantMappingHash{};
    std::uint64_t sourceSamplerMappingHash{};
    std::uint64_t sourceMappingPlanRevisionHash{};
    std::uint64_t sourceMappingSemanticContractHash{};
    bool constantRegisterMappingExact{};
    bool samplerMappingExact{};
    std::uint64_t translationObjectSnapshotToken{};
    std::uint64_t inputLayoutSnapshotToken{};
    std::uint64_t translatedSemanticReceiptSnapshotToken{};
    std::uint64_t sourceMappingHandoffSnapshotToken{};
    std::uint64_t reviewSnapshotToken{};
};

[[nodiscard]] NativeProgrammableShaderSemanticTranslationReadiness
compose_programmable_shader_semantic_translation_readiness(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderTranslationObjectReadiness& translationObject,
    std::uint64_t translationObjectSnapshotToken,
    const NativeProgrammableShaderInputLayoutReadiness& inputLayout,
    std::uint64_t inputLayoutSnapshotToken,
    const NativeProgrammableShaderTranslatedSemanticReceipt&
        translatedSemanticReceipt,
    std::uint64_t translatedSemanticReceiptSnapshotToken,
    const ProgrammableShaderInterfaceLinkageEvidence& sourceInterfaceLinkage) noexcept;

[[nodiscard]] bool
validate_programmable_shader_semantic_translation_readiness_snapshot(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderTranslationObjectReadiness& translationObject,
    std::uint64_t translationObjectSnapshotToken,
    const NativeProgrammableShaderInputLayoutReadiness& inputLayout,
    std::uint64_t inputLayoutSnapshotToken,
    const NativeProgrammableShaderTranslatedSemanticReceipt&
        translatedSemanticReceipt,
    std::uint64_t translatedSemanticReceiptSnapshotToken,
    const ProgrammableShaderInterfaceLinkageEvidence& sourceInterfaceLinkage,
    std::uint64_t reviewSnapshotToken) noexcept;

// R259 consumes the current R258 source receipt, R262 full F18 resource-behavior
// review, R243 input-layout ownership and the exact R263 F21 semantic proof into
// one activation-prerequisite handoff. R290 requires all shader-side receipts
// to carry the same R239 cache key before this handoff can become review-ready.
// Static prerequisites may become complete, but activation authority stays off
// until the separate activation/runtime gate.
struct NativeProgrammableShaderActivationPrerequisiteHandoff {
    bool inputValid{};
    bool sourceRevalidationReady{};
    bool sourceRevalidationSnapshotMatches{};
    bool sourceRevalidationPayloadSnapshotMatches{};
    bool sourceIdentityMatches{};
    bool resourceBehaviorReviewReady{};
    bool resourceBehaviorSnapshotMatches{};
    // R304 requires exact R262 payload reconstruction at the shared R259 gate.
    bool resourceBehaviorPayloadSnapshotMatches{};
    bool resourceBehaviorGeometryProofPresent{};
    bool resourceBehaviorTextureProofPresent{};
    bool resourceBehaviorOutputProofPresent{};
    bool resourceBehaviorCoverageComplete{};
    bool inputLayoutOwnershipReady{};
    bool inputLayoutSnapshotMatches{};
    bool shaderTranslationReviewReady{};
    bool shaderTranslationSnapshotMatches{};
    bool resourceBehaviorProofPresent{};
    bool inputLayoutProofPresent{};
    bool shaderTranslationProofPresent{};
    bool sourceIdentityProofPresent{};
    bool activationPrerequisitesSatisfied{};
    bool diagnosticOnly{};
    bool nativeDrawPathActivationAllowed{};
    bool drawDispatchAuthorized{};
    bool boundaryPreserved{};
    bool reviewReady{};
    NativeProgrammableShaderDrawCandidateKind kind =
        NativeProgrammableShaderDrawCandidateKind::None;
    bool indexed{};
    std::uint32_t missingPrerequisiteMask{};
    std::uint64_t cacheKey{};
    std::uint64_t sourceRevalidationSnapshotToken{};
    std::uint64_t resourceBehaviorSnapshotToken{};
    std::uint64_t inputLayoutSnapshotToken{};
    std::uint64_t shaderTranslationSnapshotToken{};
    std::uint64_t reviewSnapshotToken{};
    std::uint64_t activationSnapshotToken{};
};

[[nodiscard]] NativeProgrammableShaderActivationPrerequisiteHandoff
compose_programmable_activation_prerequisite_handoff(
    const NativeProgrammableShaderDormantSourceRevalidationReadiness&
        sourceRevalidation,
    std::uint64_t sourceRevalidationSnapshotToken,
    const NativeProgrammableShaderOutputResourceBehaviorReadiness& resourceBehavior,
    std::uint64_t resourceBehaviorSnapshotToken,
    const NativeProgrammableShaderInputLayoutReadiness& inputLayout,
    std::uint64_t inputLayoutSnapshotToken,
    const NativeProgrammableShaderSemanticTranslationReadiness& shaderTranslation,
    std::uint64_t shaderTranslationSnapshotToken) noexcept;

[[nodiscard]] bool
validate_programmable_activation_prerequisite_handoff_snapshot(
    const NativeProgrammableShaderDormantSourceRevalidationReadiness&
        sourceRevalidation,
    std::uint64_t sourceRevalidationSnapshotToken,
    const NativeProgrammableShaderOutputResourceBehaviorReadiness& resourceBehavior,
    std::uint64_t resourceBehaviorSnapshotToken,
    const NativeProgrammableShaderInputLayoutReadiness& inputLayout,
    std::uint64_t inputLayoutSnapshotToken,
    const NativeProgrammableShaderSemanticTranslationReadiness& shaderTranslation,
    std::uint64_t shaderTranslationSnapshotToken,
    std::uint64_t reviewSnapshotToken) noexcept;

class NativeProgrammableShaderPairCache final {
public:
    NativeProgrammableShaderPairCache() = default;
    ~NativeProgrammableShaderPairCache() = default;
    NativeProgrammableShaderPairCache(
        const NativeProgrammableShaderPairCache&) = delete;
    NativeProgrammableShaderPairCache& operator=(
        const NativeProgrammableShaderPairCache&) = delete;

    bool initialize(ID3D11Device* device) noexcept;
    bool cache_for_observation(
        const ProgrammableShaderPairCacheIdentity& identity) noexcept;
    [[nodiscard]] NativeProgrammableShaderPairCacheReadiness readiness(
        ID3D11Device* expectedDevice,
        const ProgrammableShaderPairCacheIdentity& identity) const noexcept;
    [[nodiscard]] bool validate_snapshot(
        ID3D11Device* expectedDevice,
        const ProgrammableShaderPairCacheIdentity& identity,
        std::uint64_t snapshotToken) const noexcept;
    bool reserve_translation_slot_for_observation(
        ID3D11Device* expectedDevice,
        const ProgrammableShaderPairCacheIdentity& identity,
        std::uint64_t cacheSnapshotToken) noexcept;
    [[nodiscard]] NativeProgrammableShaderTranslationSlotReadiness
    translation_slot_ownership_readiness(
        ID3D11Device* expectedDevice,
        const ProgrammableShaderPairCacheIdentity& identity,
        std::uint64_t cacheSnapshotToken) const noexcept;
    [[nodiscard]] bool validate_translation_slot_snapshot(
        ID3D11Device* expectedDevice,
        const ProgrammableShaderPairCacheIdentity& identity,
        std::uint64_t cacheSnapshotToken,
        std::uint64_t slotSnapshotToken) const noexcept;
    bool attach_translation_objects_for_observation(
        ID3D11Device* expectedDevice,
        const ProgrammableShaderPairCacheIdentity& identity,
        std::uint64_t cacheSnapshotToken,
        std::uint64_t slotSnapshotToken,
        ID3D11VertexShader* vertexShader,
        ID3D11PixelShader* pixelShader) noexcept;
    [[nodiscard]] NativeProgrammableShaderTranslationObjectReadiness
    translation_object_readiness(
        ID3D11Device* expectedDevice,
        const ProgrammableShaderPairCacheIdentity& identity,
        std::uint64_t cacheSnapshotToken,
        std::uint64_t slotSnapshotToken) const noexcept;
    [[nodiscard]] bool validate_translation_object_snapshot(
        ID3D11Device* expectedDevice,
        const ProgrammableShaderPairCacheIdentity& identity,
        std::uint64_t cacheSnapshotToken,
        std::uint64_t slotSnapshotToken,
        std::uint64_t objectSnapshotToken) const noexcept;
    bool attach_input_layout_for_observation(
        ID3D11Device* expectedDevice,
        const ProgrammableShaderPairCacheIdentity& identity,
        std::uint64_t cacheSnapshotToken,
        std::uint64_t slotSnapshotToken,
        std::uint64_t objectSnapshotToken,
        const VertexInputLayoutTranslation& layout,
        ID3D11InputLayout* inputLayout) noexcept;
    [[nodiscard]] NativeProgrammableShaderInputLayoutReadiness
    input_layout_readiness(
        ID3D11Device* expectedDevice,
        const ProgrammableShaderPairCacheIdentity& identity,
        std::uint64_t cacheSnapshotToken,
        std::uint64_t slotSnapshotToken,
        std::uint64_t objectSnapshotToken,
        const VertexInputLayoutTranslation& layout) const noexcept;
    [[nodiscard]] bool validate_input_layout_snapshot(
        ID3D11Device* expectedDevice,
        const ProgrammableShaderPairCacheIdentity& identity,
        std::uint64_t cacheSnapshotToken,
        std::uint64_t slotSnapshotToken,
        std::uint64_t objectSnapshotToken,
        const VertexInputLayoutTranslation& layout,
        std::uint64_t inputLayoutSnapshotToken) const noexcept;
    bool attach_constant_state_for_observation(
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
        UINT pixelConstantBytes) noexcept;
    [[nodiscard]] NativeProgrammableShaderConstantStateReadiness
    constant_state_readiness(
        ID3D11Device* expectedDevice,
        const ProgrammableShaderPairCacheIdentity& identity,
        std::uint64_t cacheSnapshotToken,
        std::uint64_t slotSnapshotToken,
        std::uint64_t objectSnapshotToken,
        const VertexInputLayoutTranslation& layout,
        std::uint64_t inputLayoutSnapshotToken) const noexcept;
    [[nodiscard]] bool validate_constant_state_snapshot(
        ID3D11Device* expectedDevice,
        const ProgrammableShaderPairCacheIdentity& identity,
        std::uint64_t cacheSnapshotToken,
        std::uint64_t slotSnapshotToken,
        std::uint64_t objectSnapshotToken,
        const VertexInputLayoutTranslation& layout,
        std::uint64_t inputLayoutSnapshotToken,
        std::uint64_t constantStateSnapshotToken) const noexcept;
    bool upload_constant_payload_for_observation(
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
        UINT pixelPayloadBytes) noexcept;
    [[nodiscard]] NativeProgrammableShaderConstantPayloadReadiness
    constant_payload_readiness(
        ID3D11DeviceContext* expectedContext,
        ID3D11Device* expectedDevice,
        const ProgrammableShaderPairCacheIdentity& identity,
        std::uint64_t cacheSnapshotToken,
        std::uint64_t slotSnapshotToken,
        std::uint64_t objectSnapshotToken,
        const VertexInputLayoutTranslation& layout,
        std::uint64_t inputLayoutSnapshotToken,
        std::uint64_t constantStateSnapshotToken) const noexcept;
    [[nodiscard]] bool validate_constant_payload_snapshot(
        ID3D11DeviceContext* expectedContext,
        ID3D11Device* expectedDevice,
        const ProgrammableShaderPairCacheIdentity& identity,
        std::uint64_t cacheSnapshotToken,
        std::uint64_t slotSnapshotToken,
        std::uint64_t objectSnapshotToken,
        const VertexInputLayoutTranslation& layout,
        std::uint64_t inputLayoutSnapshotToken,
        std::uint64_t constantStateSnapshotToken,
        std::uint64_t constantPayloadSnapshotToken) const noexcept;
    bool bind_constant_slots_for_observation(
        ID3D11DeviceContext* expectedContext,
        ID3D11Device* expectedDevice,
        const ProgrammableShaderPairCacheIdentity& identity,
        std::uint64_t cacheSnapshotToken,
        std::uint64_t slotSnapshotToken,
        std::uint64_t objectSnapshotToken,
        const VertexInputLayoutTranslation& layout,
        std::uint64_t inputLayoutSnapshotToken,
        std::uint64_t constantStateSnapshotToken,
        std::uint64_t constantPayloadSnapshotToken) noexcept;
    [[nodiscard]] NativeProgrammableShaderConstantBindingReadiness
    constant_binding_readiness(
        ID3D11DeviceContext* expectedContext,
        ID3D11Device* expectedDevice,
        const ProgrammableShaderPairCacheIdentity& identity,
        std::uint64_t cacheSnapshotToken,
        std::uint64_t slotSnapshotToken,
        std::uint64_t objectSnapshotToken,
        const VertexInputLayoutTranslation& layout,
        std::uint64_t inputLayoutSnapshotToken,
        std::uint64_t constantStateSnapshotToken,
        std::uint64_t constantPayloadSnapshotToken) const noexcept;
    [[nodiscard]] bool validate_constant_binding_snapshot(
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
        std::uint64_t constantBindingSnapshotToken) const noexcept;
    bool bind_pipeline_objects_for_observation(
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
        std::uint64_t constantBindingSnapshotToken) noexcept;
    [[nodiscard]] NativeProgrammableShaderPipelineBindingReadiness
    pipeline_binding_readiness(
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
        std::uint64_t constantBindingSnapshotToken) const noexcept;
    [[nodiscard]] bool validate_pipeline_binding_snapshot(
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
        std::uint64_t pipelineBindingSnapshotToken) const noexcept;
    bool bind_primitive_topology_for_observation(
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
        D3DPRIMITIVETYPE primitiveType) noexcept;
    [[nodiscard]] NativeProgrammableShaderTopologyBindingReadiness
    primitive_topology_binding_readiness(
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
        D3DPRIMITIVETYPE primitiveType) const noexcept;
    [[nodiscard]] bool validate_primitive_topology_binding_snapshot(
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
        std::uint64_t topologyBindingSnapshotToken) const noexcept;
    bool bind_indexed_geometry_for_observation(
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
        UINT indexOffset) noexcept;
    [[nodiscard]] NativeProgrammableShaderIndexedGeometryBindingReadiness
    indexed_geometry_binding_readiness(
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
        UINT indexOffset) const noexcept;
    [[nodiscard]] bool validate_indexed_geometry_binding_snapshot(
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
        std::uint64_t indexedGeometryBindingSnapshotToken) const noexcept;
    bool bind_nonindexed_geometry_for_observation(
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
        UINT vertexOffset) noexcept;
    [[nodiscard]] NativeProgrammableShaderNonIndexedGeometryBindingReadiness
    nonindexed_geometry_binding_readiness(
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
        UINT vertexOffset) const noexcept;
    [[nodiscard]] bool validate_nonindexed_geometry_binding_snapshot(
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
        std::uint64_t nonIndexedGeometryBindingSnapshotToken) const noexcept;
    [[nodiscard]] NativeProgrammableShaderNonIndexedDirectDispatchReadiness
    nonindexed_direct_dispatch_readiness(
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
        UINT startVertexLocation) const noexcept;
    [[nodiscard]] bool validate_nonindexed_direct_dispatch_snapshot(
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
        std::uint64_t directDispatchSnapshotToken) const noexcept;
    [[nodiscard]] NativeProgrammableShaderIndexedDirectDispatchReadiness
    indexed_direct_dispatch_readiness(
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
        UINT startIndex) const noexcept;
    [[nodiscard]] bool validate_indexed_direct_dispatch_snapshot(
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
        std::uint64_t directDispatchSnapshotToken) const noexcept;
    [[nodiscard]] NativeProgrammableShaderIndexedSourceValueReadiness
    indexed_source_value_readiness(
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
        std::uint64_t directDispatchSnapshotToken) const noexcept;
    [[nodiscard]] bool validate_indexed_source_value_snapshot(
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
        std::uint64_t sourceValueSnapshotToken) const noexcept;
    [[nodiscard]] NativeProgrammableShaderIndexedLiveIndexBindingReadiness
    indexed_live_index_binding_readiness(
        ID3D11DeviceContext* expectedContext,
        ID3D11Device* expectedDevice,
        const NativeManagedBufferShadow& indexBuffer,
        std::uint64_t indexBufferSnapshotToken,
        DXGI_FORMAT indexFormat,
        UINT indexOffset,
        const NativeProgrammableShaderIndexedSourceValueReadiness& sourceValues,
        std::uint64_t sourceValueSnapshotToken) const noexcept;
    [[nodiscard]] bool validate_indexed_live_index_binding_snapshot(
        ID3D11DeviceContext* expectedContext,
        ID3D11Device* expectedDevice,
        const NativeManagedBufferShadow& indexBuffer,
        std::uint64_t indexBufferSnapshotToken,
        DXGI_FORMAT indexFormat,
        UINT indexOffset,
        const NativeProgrammableShaderIndexedSourceValueReadiness& sourceValues,
        std::uint64_t sourceValueSnapshotToken,
        std::uint64_t liveIndexBindingSnapshotToken) const noexcept;
    [[nodiscard]] NativeProgrammableShaderIndexedPreDrawReadiness
    indexed_pre_draw_readiness(
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
        std::uint64_t liveIndexBindingSnapshotToken) const noexcept;
    [[nodiscard]] bool validate_indexed_pre_draw_snapshot(
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
        std::uint64_t preDrawSnapshotToken) const noexcept;
    [[nodiscard]] NativeProgrammableShaderDormantSourceRevalidationReadiness
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
        std::uint64_t preActivationSnapshotToken) const noexcept;
    [[nodiscard]] NativeProgrammableShaderDormantSourceRevalidationReadiness
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
        std::uint64_t preActivationSnapshotToken) const noexcept;
    void shutdown() noexcept;

    [[nodiscard]] bool ready() const noexcept {
        return device_ != nullptr && owner_generation_ != 0;
    }
    [[nodiscard]] ID3D11Device* device() const noexcept {
        return device_.Get();
    }
    [[nodiscard]] std::size_t entry_count() const noexcept {
        return entries_.size();
    }
    [[nodiscard]] std::uint64_t owner_generation() const noexcept {
        return owner_generation_;
    }

private:
    struct Entry {
        UINT vertexByteSize{};
        DWORD vertexVersionToken{};
        std::uint64_t vertexBytecodeHash{};
        UINT pixelByteSize{};
        DWORD pixelVersionToken{};
        std::uint64_t pixelBytecodeHash{};
        std::uint64_t translationSlotGeneration{};
        Microsoft::WRL::ComPtr<ID3D11VertexShader> translatedVertexShader;
        Microsoft::WRL::ComPtr<ID3D11PixelShader> translatedPixelShader;
        std::uint64_t translationObjectReceiptGeneration{};
        Microsoft::WRL::ComPtr<ID3D11InputLayout> translatedInputLayout;
        std::uint64_t inputLayoutIdentity{};
        std::uint64_t inputLayoutReceiptGeneration{};
        Microsoft::WRL::ComPtr<ID3D11Buffer> translatedVertexConstantBuffer;
        Microsoft::WRL::ComPtr<ID3D11Buffer> translatedPixelConstantBuffer;
        UINT vertexConstantBytes{};
        UINT pixelConstantBytes{};
        std::uint64_t constantStateReceiptGeneration{};
        Microsoft::WRL::ComPtr<ID3D11DeviceContext> constantUploadContext;
        std::uint64_t vertexConstantPayloadHash{};
        std::uint64_t pixelConstantPayloadHash{};
        std::uint64_t constantPayloadReceiptGeneration{};
        Microsoft::WRL::ComPtr<ID3D11DeviceContext> constantBindingContext;
        std::uint64_t constantBindingReceiptGeneration{};
        Microsoft::WRL::ComPtr<ID3D11DeviceContext> programmableBindingContext;
        std::uint64_t programmableBindingReceiptGeneration{};
        Microsoft::WRL::ComPtr<ID3D11DeviceContext> topologyBindingContext;
        D3D11_PRIMITIVE_TOPOLOGY boundPrimitiveTopology =
            D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
        std::uint64_t topologyBindingReceiptGeneration{};
        Microsoft::WRL::ComPtr<ID3D11DeviceContext> indexedGeometryBindingContext;
        Microsoft::WRL::ComPtr<ID3D11Buffer> indexedGeometryVertexBuffer;
        Microsoft::WRL::ComPtr<ID3D11Buffer> indexedGeometryIndexBuffer;
        std::uint64_t indexedGeometryVertexBufferSnapshotToken{};
        std::uint64_t indexedGeometryIndexBufferSnapshotToken{};
        UINT indexedGeometryVertexStride{};
        UINT indexedGeometryVertexOffset{};
        DXGI_FORMAT indexedGeometryIndexFormat = DXGI_FORMAT_UNKNOWN;
        UINT indexedGeometryIndexOffset{};
        std::uint64_t indexedGeometryBindingReceiptGeneration{};
        Microsoft::WRL::ComPtr<ID3D11DeviceContext> nonIndexedGeometryBindingContext;
        Microsoft::WRL::ComPtr<ID3D11Buffer> nonIndexedGeometryVertexBuffer;
        std::uint64_t nonIndexedGeometryVertexBufferSnapshotToken{};
        UINT nonIndexedGeometryVertexStride{};
        UINT nonIndexedGeometryVertexOffset{};
        std::uint64_t nonIndexedGeometryBindingReceiptGeneration{};
    };

    Microsoft::WRL::ComPtr<ID3D11Device> device_;
    std::unordered_map<std::uint64_t, Entry> entries_;
    std::uint64_t owner_generation_ = 0;
    std::uint64_t translation_slot_generation_counter_ = 0;
    std::uint64_t translation_object_receipt_generation_counter_ = 0;
    std::uint64_t input_layout_receipt_generation_counter_ = 0;
    std::uint64_t constant_state_receipt_generation_counter_ = 0;
    std::uint64_t constant_payload_receipt_generation_counter_ = 0;
    std::uint64_t constant_binding_receipt_generation_counter_ = 0;
    std::uint64_t programmable_binding_receipt_generation_counter_ = 0;
    std::uint64_t topology_binding_receipt_generation_counter_ = 0;
    std::uint64_t indexed_geometry_binding_receipt_generation_counter_ = 0;
    std::uint64_t nonindexed_geometry_binding_receipt_generation_counter_ = 0;
};

// R285 turns the one-shot R284 materializer into a persistent native-device
// ownership boundary. The owner reuses an exact validated R284 receipt for a
// repeatedly observed programmable pair and immediately feeds the current R242
// object receipt into R275. No ID3D11DeviceContext is accepted here, so shader
// binding, NativeDrawPath and Draw/DrawIndexed remain structurally unavailable.
struct NativeProgrammableShaderBackendSemanticHandoffEvidence {
    bool inputValid{};
    bool ownerReady{};
    bool deviceMatches{};
    bool materializationReady{};
    bool materializationSnapshotMatches{};
    bool materializationReused{};
    bool translationObjectReady{};
    bool translationObjectSnapshotMatches{};
    bool translatedSemanticReceiptReady{};
    bool translatedSemanticReceiptSnapshotMatches{};
    bool objectBindingAuthorized{};
    bool nativeDrawPathActivationAllowed{};
    bool drawDispatchAuthorized{};
    bool diagnosticOnly{};
    bool boundaryPreserved{};
    bool reviewReady{};
    std::uint64_t cacheKey{};
    std::uint64_t backendOwnerGeneration{};
    std::uint64_t cacheOwnerGeneration{};
    std::uint64_t objectMaterializationSnapshotToken{};
    std::uint64_t cacheSnapshotToken{};
    std::uint64_t slotSnapshotToken{};
    std::uint64_t translationObjectSnapshotToken{};
    std::uint64_t translatedSemanticReceiptSnapshotToken{};
    std::uint64_t reviewSnapshotToken{};
    NativeProgrammableShaderTranslatedSemanticReceipt translatedSemanticReceipt{};
};

struct NativeProgrammableShaderProductionObservationEvidence;
struct NativeProgrammableShaderTranslationAdmissionEvidence;
struct NativeProgrammableShaderProductionSemanticReviewEvidence;

class NativeProgrammableShaderBackendOwnership final {
public:
    NativeProgrammableShaderBackendOwnership() = default;
    ~NativeProgrammableShaderBackendOwnership() = default;
    NativeProgrammableShaderBackendOwnership(
        const NativeProgrammableShaderBackendOwnership&) = delete;
    NativeProgrammableShaderBackendOwnership& operator=(
        const NativeProgrammableShaderBackendOwnership&) = delete;

    bool initialize(ID3D11Device* device) noexcept;
    void shutdown() noexcept;

    [[nodiscard]] NativeProgrammableShaderBackendSemanticHandoffEvidence
    materialize_semantic_handoff_for_observation(
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
        const NativeProgrammableShaderSourceMappingHandoff& sourceMappingHandoff,
        std::uint64_t sourceMappingHandoffSnapshotToken,
        const NativeProgrammableShaderSemanticTranslationPlanEvidence&
            translationPlan,
        std::uint64_t translationPlanSnapshotToken) noexcept;

    [[nodiscard]] bool validate_semantic_handoff_snapshot(
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
        const NativeProgrammableShaderSourceMappingHandoff& sourceMappingHandoff,
        std::uint64_t sourceMappingHandoffSnapshotToken,
        const NativeProgrammableShaderSemanticTranslationPlanEvidence&
            translationPlan,
        std::uint64_t translationPlanSnapshotToken,
        const NativeProgrammableShaderBackendSemanticHandoffEvidence& handoff,
        std::uint64_t reviewSnapshotToken) const noexcept;

    [[nodiscard]] NativeProgrammableShaderProductionSemanticReviewEvidence
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
            sourceInterfaceLinkage) noexcept;

    [[nodiscard]] bool validate_semantic_translation_review_snapshot(
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
        std::uint64_t reviewSnapshotToken) const noexcept;

    [[nodiscard]] bool ready() const noexcept {
        return device_ && cache_.ready() && cache_.device() == device_.Get() &&
            owner_generation_ != 0;
    }
    [[nodiscard]] ID3D11Device* device() const noexcept {
        return device_.Get();
    }
    [[nodiscard]] std::uint64_t owner_generation() const noexcept {
        return owner_generation_;
    }
    [[nodiscard]] const NativeProgrammableShaderPairCache& cache() const noexcept {
        return cache_;
    }

private:
    Microsoft::WRL::ComPtr<ID3D11Device> device_;
    NativeProgrammableShaderPairCache cache_;
    std::unordered_map<
        std::uint64_t,
        NativeProgrammableShaderObjectMaterializationEvidence> materializations_;
    std::unordered_map<
        std::uint64_t,
        Microsoft::WRL::ComPtr<ID3D11InputLayout>> semantic_input_layouts_;
    std::uint64_t owner_generation_ = 0;
};


struct NativeProgrammableShaderProductionObservationEvidence {
    bool inputValid{};
    bool ownerReady{};
    bool deviceMatches{};
    bool objectPrerequisiteReady{};
    bool creationHandoffReady{};
    bool targetBytecodeMaterializationReady{};
    bool sourceMappingHandoffReady{};
    bool translationPlanReady{};
    bool semanticHandoffReady{};
    bool semanticHandoffSnapshotMatches{};
    bool objectBindingAuthorized{};
    bool nativeDrawPathActivationAllowed{};
    bool drawDispatchAuthorized{};
    bool diagnosticOnly{};
    bool boundaryPreserved{};
    bool reviewReady{};
    std::uint64_t cacheKey{};
    std::uint64_t backendOwnerGeneration{};
    std::uint64_t objectPrerequisiteSnapshotToken{};
    std::uint64_t creationHandoffSnapshotToken{};
    std::uint64_t targetBytecodeMaterializationSnapshotToken{};
    std::uint64_t sourceMappingHandoffSnapshotToken{};
    std::uint64_t translationPlanSnapshotToken{};
    std::uint64_t semanticHandoffSnapshotToken{};
    std::uint64_t reviewSnapshotToken{};
    NativeProgrammableShaderBackendSemanticHandoffEvidence semanticHandoff{};
};

// R286 is the bounded production-side observation bridge from the exact
// R279/R280/R283/R274/R276 evidence chain into the persistent R285 owner.
// It intentionally accepts no ID3D11DeviceContext and cannot bind shaders,
// enable NativeDrawPath, or issue Draw/DrawIndexed.
[[nodiscard]] NativeProgrammableShaderProductionObservationEvidence
observe_programmable_shader_production_source_evidence_chain(
    NativeProgrammableShaderBackendOwnership& ownership,
    ID3D11Device* expectedDevice,
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
    const NativeProgrammableShaderSourceMappingHandoff& sourceMappingHandoff,
    std::uint64_t sourceMappingHandoffSnapshotToken,
    const NativeProgrammableShaderSemanticTranslationPlanEvidence&
        translationPlan,
    std::uint64_t translationPlanSnapshotToken) noexcept;

// R288 seals an exact R286 production observation plus its nested R275
// translated-semantic receipt into one promotion-review admission receipt.
// This is still diagnostic evidence only: it accepts no device context and
// cannot bind shaders, enable NativeDrawPath, or authorize Draw/DrawIndexed.
struct NativeProgrammableShaderTranslationAdmissionEvidence {
    bool inputValid{};
    bool sourceIdentityExact{};
    bool productionObservationReady{};
    bool productionObservationSnapshotMatches{};
    bool translatedSemanticReceiptReady{};
    bool translatedSemanticReceiptSnapshotMatches{};
    bool cacheIdentityMatches{};
    bool translationObjectReady{};
    bool objectBindingAuthorized{};
    bool nativeDrawPathActivationAllowed{};
    bool drawDispatchAuthorized{};
    bool diagnosticOnly{};
    bool boundaryPreserved{};
    bool reviewReady{};
    std::uint64_t cacheKey{};
    std::uint64_t backendOwnerGeneration{};
    std::uint64_t productionObservationSnapshotToken{};
    std::uint64_t translatedSemanticReceiptSnapshotToken{};
    std::uint64_t reviewSnapshotToken{};
};

[[nodiscard]] bool
validate_programmable_shader_production_observation_snapshot(
    const NativeProgrammableShaderProductionObservationEvidence& observation,
    std::uint64_t reviewSnapshotToken) noexcept;

[[nodiscard]] NativeProgrammableShaderTranslationAdmissionEvidence
seal_programmable_shader_translation_admission(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderProductionObservationEvidence& observation,
    std::uint64_t productionObservationSnapshotToken) noexcept;

[[nodiscard]] bool
validate_programmable_shader_translation_admission_snapshot(
    const ProgrammableShaderPairCacheIdentity& sourceIdentity,
    const NativeProgrammableShaderProductionObservationEvidence& observation,
    std::uint64_t productionObservationSnapshotToken,
    const NativeProgrammableShaderTranslationAdmissionEvidence& admission,
    std::uint64_t reviewSnapshotToken) noexcept;

// R289 materializes only the D3D11 input-layout object required to review the
// exact R288 production admission through the existing R263 semantic gate.
// It reuses the persistent R285/R242 ownership, never accepts a device context,
// never binds IA/VS/PS state, and cannot authorize NativeDrawPath/Draw*.

struct NativeProgrammableShaderProductionSemanticReviewEvidence {
    bool inputValid{};
    bool ownerReady{};
    bool admissionReady{};
    bool admissionSnapshotMatches{};
    bool targetVertexBytecodeReady{};
    bool inputLayoutDescriptorExact{};
    bool inputLayoutObjectReady{};
    bool inputLayoutReused{};
    bool translationObjectReady{};
    bool translationObjectSnapshotMatches{};
    bool inputLayoutReceiptReady{};
    bool inputLayoutSnapshotMatches{};
    bool semanticTranslationReady{};
    bool semanticTranslationSnapshotMatches{};
    bool objectBindingAuthorized{};
    bool nativeDrawPathActivationAllowed{};
    bool drawDispatchAuthorized{};
    bool diagnosticOnly{};
    bool boundaryPreserved{};
    bool reviewReady{};
    std::uint64_t cacheKey{};
    std::uint64_t backendOwnerGeneration{};
    std::uint64_t admissionSnapshotToken{};
    std::uint64_t targetBytecodeMaterializationSnapshotToken{};
    std::uint64_t cacheSnapshotToken{};
    std::uint64_t slotSnapshotToken{};
    std::uint64_t translationObjectSnapshotToken{};
    std::uint64_t inputLayoutSnapshotToken{};
    std::uint64_t semanticTranslationSnapshotToken{};
    std::uint64_t reviewSnapshotToken{};
    NativeProgrammableShaderInputLayoutReadiness inputLayout{};
    NativeProgrammableShaderSemanticTranslationReadiness semanticTranslation{};
};

// R292 combines the current R289 production semantic review with the exact
// dormant R258 source and R262 full-F18 resource receipts, then reuses the
// R259/R290 prerequisite gate. Static prerequisites may be observed complete,
// but this evidence is diagnostic-only and never creates binding/draw authority.
struct NativeProgrammableShaderProductionActivationPrerequisiteEvidence {
    bool inputValid{};
    bool productionSemanticReviewReady{};
    bool productionSemanticReviewSnapshotMatches{};
    bool sourceRevalidationReady{};
    bool sourceRevalidationSnapshotMatches{};
    bool resourceBehaviorReady{};
    bool resourceBehaviorSnapshotMatches{};
    // R303 requires exact R262 payload reconstruction at the production gate.
    bool resourceBehaviorPayloadSnapshotMatches{};
    bool prerequisiteHandoffReady{};
    bool prerequisiteHandoffSnapshotMatches{};
    bool staticPrerequisitesSatisfied{};
    bool objectBindingAuthorized{};
    bool nativeDrawPathActivationAllowed{};
    bool drawDispatchAuthorized{};
    bool diagnosticOnly{};
    bool boundaryPreserved{};
    bool reviewReady{};
    std::uint32_t missingPrerequisiteMask{};
    std::uint64_t cacheKey{};
    std::uint64_t productionSemanticReviewSnapshotToken{};
    std::uint64_t sourceRevalidationSnapshotToken{};
    std::uint64_t resourceBehaviorSnapshotToken{};
    std::uint64_t prerequisiteHandoffSnapshotToken{};
    std::uint64_t reviewSnapshotToken{};
    NativeProgrammableShaderActivationPrerequisiteHandoff prerequisites{};
};

[[nodiscard]] NativeProgrammableShaderProductionActivationPrerequisiteEvidence
observe_programmable_shader_production_activation_prerequisites(
    const NativeProgrammableShaderProductionSemanticReviewEvidence&
        productionSemanticReview,
    std::uint64_t productionSemanticReviewSnapshotToken,
    const NativeProgrammableShaderDormantSourceRevalidationReadiness&
        sourceRevalidation,
    std::uint64_t sourceRevalidationSnapshotToken,
    const NativeProgrammableShaderOutputResourceBehaviorReadiness&
        resourceBehavior,
    std::uint64_t resourceBehaviorSnapshotToken) noexcept;

[[nodiscard]] bool
validate_programmable_shader_production_activation_prerequisite_snapshot(
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
    std::uint64_t reviewSnapshotToken) noexcept;

// R97 dormant per-device owner for the R93/R84 shader pair, R78/R88
// input layout, and R96 transform buffer. No game draw path constructs or
// binds this bundle yet.
class NativeFixedFunctionPipelineBundle final {
public:
    NativeFixedFunctionPipelineBundle() = default;
    ~NativeFixedFunctionPipelineBundle() = default;
    NativeFixedFunctionPipelineBundle(
        const NativeFixedFunctionPipelineBundle&) = delete;
    NativeFixedFunctionPipelineBundle& operator=(
        const NativeFixedFunctionPipelineBundle&) = delete;

    bool initialize(
        ID3D11Device* device,
        const VertexInputLayoutTranslation& layout,
        const FixedFunctionVertexShaderPrototype& vertexPrototype,
        const FixedFunctionPixelShaderPrototype& pixelPrototype) noexcept;
    void shutdown() noexcept;
    [[nodiscard]] NativeFixedFunctionPipelineReadiness translation_readiness(
        ID3D11Device* expectedDevice,
        const VertexInputLayoutTranslation& layout,
        const FixedFunctionVertexShaderPrototype& vertexPrototype,
        const FixedFunctionPixelShaderPrototype& pixelPrototype) const noexcept;
    [[nodiscard]] bool validate_translation_snapshot(
        ID3D11Device* expectedDevice,
        const VertexInputLayoutTranslation& layout,
        const FixedFunctionVertexShaderPrototype& vertexPrototype,
        const FixedFunctionPixelShaderPrototype& pixelPrototype,
        std::uint64_t snapshotToken) const noexcept;

    // Upload and bind the exact translated WVP through the R96 owner without
    // routing a game draw. The final VS-b0 gate reobserves this binding.
    bool upload_transform_for_observation(
        ID3D11DeviceContext* context,
        const FixedFunctionTransformConstants& constants) noexcept;

    // Dormant exact-device binding primitive for the already-sealed R97
    // pipeline identity. This binds only IA/VS/PS objects for observation;
    // it does not upload per-draw constants or issue a Draw* call.
    [[nodiscard]] bool bind_for_observation(
        ID3D11DeviceContext* context,
        const VertexInputLayoutTranslation& layout,
        const FixedFunctionVertexShaderPrototype& vertexPrototype,
        const FixedFunctionPixelShaderPrototype& pixelPrototype,
        std::uint64_t snapshotToken) const noexcept;
    [[nodiscard]] NativeFixedFunctionPipelineBindingReadiness binding_readiness(
        ID3D11DeviceContext* context,
        const VertexInputLayoutTranslation& layout,
        const FixedFunctionVertexShaderPrototype& vertexPrototype,
        const FixedFunctionPixelShaderPrototype& pixelPrototype,
        std::uint64_t pipelineSnapshotToken) const noexcept;
    [[nodiscard]] bool validate_binding_snapshot(
        ID3D11DeviceContext* context,
        const VertexInputLayoutTranslation& layout,
        const FixedFunctionVertexShaderPrototype& vertexPrototype,
        const FixedFunctionPixelShaderPrototype& pixelPrototype,
        std::uint64_t pipelineSnapshotToken,
        std::uint64_t bindingSnapshotToken) const noexcept;

    [[nodiscard]] bool ready() const noexcept {
        return device_ && vertex_shader_ && pixel_shader_ && input_layout_ &&
            transform_buffer_.ready();
    }
    [[nodiscard]] ID3D11Device* device() const noexcept {
        return device_.Get();
    }
    [[nodiscard]] ID3D11VertexShader* vertex_shader() const noexcept {
        return vertex_shader_.Get();
    }
    [[nodiscard]] ID3D11PixelShader* pixel_shader() const noexcept {
        return pixel_shader_.Get();
    }
    [[nodiscard]] ID3D11InputLayout* input_layout() const noexcept {
        return input_layout_.Get();
    }
    [[nodiscard]] const NativeFixedFunctionTransformBuffer&
    transform_buffer() const noexcept {
        return transform_buffer_;
    }

private:
    Microsoft::WRL::ComPtr<ID3D11Device> device_;
    Microsoft::WRL::ComPtr<ID3D11VertexShader> vertex_shader_;
    Microsoft::WRL::ComPtr<ID3D11PixelShader> pixel_shader_;
    Microsoft::WRL::ComPtr<ID3D11InputLayout> input_layout_;
    NativeFixedFunctionTransformBuffer transform_buffer_;
    std::uint64_t input_layout_identity_ = 0;
    std::uint64_t vertex_shader_source_hash_ = 0;
    std::uint64_t pixel_shader_source_hash_ = 0;
    std::uint64_t bundle_generation_ = 0;
};


// R139 is the stronger final dormant proof: it reobserves aggregate PS,
// IA/VS/PS and RS/OM bindings from one caller-supplied D3D11 context before
// composing R138. Precomputed readiness from another context cannot be
// injected because this entrypoint owns all live observations. It never Draw*s.
[[nodiscard]] NativeFixedFunctionBoundDrawReadiness
compose_fixed_function_same_context_bound_draw_readiness(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    const NativeFixedFunctionPipelineBundle& pipelineBundle,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures) noexcept;

[[nodiscard]] bool validate_fixed_function_same_context_bound_draw_snapshot(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    const NativeFixedFunctionPipelineBundle& pipelineBundle,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    std::uint64_t snapshotToken) noexcept;

// R140 closes the remaining direct-geometry observation gap in the final
// dormant pre-draw proof. R139 reobserves aggregate PS, IA/VS/PS and RS/OM
// state from one context; R140 additionally requires the exact live slot-0
// VB/optional IB/stride/offset/topology snapshot sealed by the draw geometry.
// This remains observation evidence only and never issues Draw*.
struct NativeFixedFunctionCompleteBoundDrawReadiness {
    bool inputValid{};
    bool sameContextBoundDrawReady{};
    bool geometryBindingReady{};
    bool geometryBindingMatchesDraw{};
    bool componentSnapshotsPresent{};
    bool ready{};
    std::uint64_t sameContextBoundDrawSnapshotToken{};
    std::uint64_t geometryBindingSnapshotToken{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] NativeFixedFunctionCompleteBoundDrawReadiness
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
    UINT indexOffset) noexcept;

[[nodiscard]] bool validate_fixed_function_complete_bound_draw_snapshot(
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
    std::uint64_t snapshotToken) noexcept;

// R142 extends the complete dormant pre-draw proof to non-indexed D3D9
// triangle fans. It reconstructs the fan geometry from the current managed
// vertex mirror plus the generated-index owner, then observes exact slot-0 VB
// and generated R32_UINT IB/topology state on the same context. No Draw* call
// is issued and NativeDrawPathActive remains unchanged.
struct NativeFixedFunctionCompleteFanBoundDrawReadiness {
    bool inputValid{};
    bool sameContextBoundDrawReady{};
    bool geometryReady{};
    bool geometryMatchesDraw{};
    bool vertexBufferBoundExact{};
    bool generatedIndexBindingReady{};
    bool generatedIndexMatchesGeometry{};
    bool componentSnapshotsPresent{};
    bool ready{};
    std::uint64_t sameContextBoundDrawSnapshotToken{};
    std::uint64_t geometrySnapshotToken{};
    std::uint64_t vertexBufferSnapshotToken{};
    std::uint64_t generatedIndexBindingSnapshotToken{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] NativeFixedFunctionCompleteFanBoundDrawReadiness
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
    UINT baseVertex) noexcept;

[[nodiscard]] bool
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
    std::uint64_t snapshotToken) noexcept;

// R144 closes the indexed triangle-fan final dormant pre-draw gap. It
// reconstructs R143 geometry from the current VB/source-IB mirrors, reobserves
// the generated R32_UINT triangle-list binding on the same context, and seals
// the future DrawIndexed BaseVertexLocation without issuing Draw*.
struct NativeFixedFunctionCompleteIndexedFanBoundDrawReadiness {
    bool inputValid{};
    bool sameContextBoundDrawReady{};
    bool geometryReady{};
    bool geometryMatchesDraw{};
    bool sourceIndexBufferCurrent{};
    bool vertexBufferBoundExact{};
    bool generatedIndexBindingReady{};
    bool generatedIndexMatchesGeometry{};
    bool componentSnapshotsPresent{};
    bool ready{};
    std::uint64_t sameContextBoundDrawSnapshotToken{};
    std::uint64_t geometrySnapshotToken{};
    std::uint64_t vertexBufferSnapshotToken{};
    std::uint64_t sourceIndexBufferSnapshotToken{};
    std::uint64_t generatedIndexBindingSnapshotToken{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] NativeFixedFunctionCompleteIndexedFanBoundDrawReadiness
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
    INT baseVertexLocation) noexcept;

[[nodiscard]] bool
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
    std::uint64_t snapshotToken) noexcept;

// Final transform-aware dormant pre-draw proof. R140 already reobserves live
// pipeline/PS/RS/OM/direct-IA state; this layer additionally requires the
// exact R96 WVP payload to remain bound at VS b0 on that same context.
struct NativeFixedFunctionFullyBoundDrawReadiness {
    bool inputValid{};
    bool completeBoundDrawReady{};
    bool transformBindingReady{};
    bool componentSnapshotsPresent{};
    bool ready{};
    std::uint64_t completeBoundDrawSnapshotToken{};
    std::uint64_t transformBindingSnapshotToken{};
    std::uint64_t transformPayloadHash{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] NativeFixedFunctionFullyBoundDrawReadiness
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
    const FixedFunctionTransformConstants& transform) noexcept;

[[nodiscard]] bool validate_fixed_function_fully_bound_draw_snapshot(
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
    std::uint64_t snapshotToken) noexcept;

// R145 closes the live OM target gap in the direct-geometry dormant pre-draw
// proof. The existing fully-bound gate is recomputed from the same context and
// then paired with an exact R130 surface owner live RTV/DSV snapshot. No Draw*
// call or NativeDrawPathActive promotion occurs here.
struct NativeFixedFunctionRenderTargetBoundDrawReadiness {
    bool inputValid{};
    bool fullyBoundDrawReady{};
    bool surfaceTargetBindingReady{};
    bool surfacePairMatchesDraw{};
    // R151 seals the exact byte-range metadata behind the live IA binding.
    bool geometryRangeMetadataExact{};
    // R158 binds live IA stride to the stride used to validate the translated
    // D3D9 input layout.
    bool vertexStrideMatchesInputLayout{};
    bool componentSnapshotsPresent{};
    bool ready{};
    UINT vertexStride{};
    UINT inputLayoutStream0Stride{};
    UINT vertexOffset{};
    UINT vertexBufferByteWidth{};
    DXGI_FORMAT indexFormat = DXGI_FORMAT_UNKNOWN;
    UINT indexOffset{};
    UINT indexBufferByteWidth{};
    std::uint64_t fullyBoundDrawSnapshotToken{};
    std::uint64_t surfaceTargetBindingSnapshotToken{};
    std::uint64_t surfacePairSnapshotToken{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] NativeFixedFunctionRenderTargetBoundDrawReadiness
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
    const NativeSurfaceMirror& depthSurface) noexcept;

[[nodiscard]] bool validate_fixed_function_render_target_bound_draw_snapshot(
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
    std::uint64_t snapshotToken) noexcept;

// R146 extends the dormant final pre-draw proof to generated triangle fans.
// R142/R144 already seal current generated-fan IA state; this layer additionally
// requires the exact live VS-b0/WVP binding and the exact live OM RTV/DSV pair.
// It remains observation-only and never issues Draw* or enables NativeDrawPathActive.
struct NativeFixedFunctionFinalFanBoundDrawReadiness {
    bool inputValid{};
    bool completeFanBoundDrawReady{};
    bool transformBindingReady{};
    bool surfaceTargetBindingReady{};
    bool surfacePairMatchesDraw{};
    bool componentSnapshotsPresent{};
    bool ready{};
    std::uint64_t completeFanBoundDrawSnapshotToken{};
    std::uint64_t transformBindingSnapshotToken{};
    std::uint64_t transformPayloadHash{};
    std::uint64_t surfaceTargetBindingSnapshotToken{};
    std::uint64_t surfacePairSnapshotToken{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] NativeFixedFunctionFinalFanBoundDrawReadiness
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
    const NativeSurfaceMirror& depthSurface) noexcept;

[[nodiscard]] bool
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
    std::uint64_t snapshotToken) noexcept;

[[nodiscard]] NativeFixedFunctionFinalFanBoundDrawReadiness
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
    const NativeSurfaceMirror& depthSurface) noexcept;

[[nodiscard]] bool
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
    std::uint64_t snapshotToken) noexcept;


// R147 seals the exact Draw/DrawIndexed argument tuple for direct non-fan
// geometry after the R145 live-state proof. This is dormant dispatch evidence
// only: it neither calls Draw* nor changes NativeDrawPathActive.
struct NativeFixedFunctionDirectDrawDispatchReadiness {
    bool inputValid{};
    bool renderTargetBoundDrawReady{};
    bool geometryReady{};
    bool geometryMatchesDraw{};
    bool surfacePairMatchesDraw{};
    bool topologyMatchesGeometry{};
    // R155: D3D9 POINTLIST raster behavior depends on point-size/point-sprite
    // state that is not yet sealed by the dormant DX11 draw snapshot.
    bool pointRasterSemanticsExact{};
    // R168: ANTIALIASEDLINEENABLE is captured and translated, but D3D10+
    // removed D3D9 LASTPIXEL control. Keep direct lines fail-closed until
    // endpoint coverage is explicitly emulated and sealed.
    bool lineRasterSemanticsExact{};
    bool bufferRangeExact{};
    bool dispatchArgumentsExact{};
    bool componentSnapshotsPresent{};
    bool ready{};
    bool indexed{};
    D3D11_PRIMITIVE_TOPOLOGY topology =
        D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    UINT primitiveCount{};
    UINT elementCount{};
    UINT startVertexLocation{};
    UINT startIndexLocation{};
    INT baseVertexLocation{};
    std::uint64_t renderTargetBoundDrawSnapshotToken{};
    std::uint64_t drawSnapshotToken{};
    std::uint64_t geometrySnapshotToken{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] bool
validate_fixed_function_render_target_bound_draw_readiness_integrity(
    const NativeFixedFunctionRenderTargetBoundDrawReadiness& boundDraw) noexcept;

[[nodiscard]] NativeFixedFunctionDirectDrawDispatchReadiness
compose_fixed_function_direct_draw_dispatch_readiness(
    const NativeFixedFunctionRenderTargetBoundDrawReadiness& boundDraw,
    const NativeFixedFunctionDrawReadiness& draw,
    const NativeFixedFunctionGeometryReadiness& geometry,
    D3DPRIMITIVETYPE primitive,
    UINT primitiveCount,
    bool indexed,
    UINT startVertexLocation,
    UINT startIndexLocation,
    INT baseVertexLocation) noexcept;

[[nodiscard]] bool validate_fixed_function_direct_draw_dispatch_snapshot(
    const NativeFixedFunctionRenderTargetBoundDrawReadiness& boundDraw,
    const NativeFixedFunctionDrawReadiness& draw,
    const NativeFixedFunctionGeometryReadiness& geometry,
    D3DPRIMITIVETYPE primitive,
    UINT primitiveCount,
    bool indexed,
    UINT startVertexLocation,
    UINT startIndexLocation,
    INT baseVertexLocation,
    std::uint64_t snapshotToken) noexcept;

// R156: diagnostic preflight for a sealed offscreen nonindexed Draw in the
// dedicated WARP test harness. Gameplay/native draw activation remains dormant.
// This function never calls Draw; only tools/dx11_constant_buffer_probe.cpp
// issues the separately reviewed offscreen WARP test Draw.
// Caller supplies the exact expected RTV, input layout and VS/PS objects;
// live immediate OM/IA/shader substitutions fail closed before Draw.
[[nodiscard]] bool prepare_fixed_function_nonindexed_direct_draw_probe(
    ID3D11DeviceContext* context,
    ID3D11RenderTargetView* expectedProbeTarget,
    ID3D11InputLayout* expectedProbeLayout,
    ID3D11VertexShader* expectedProbeVS,
    ID3D11PixelShader* expectedProbePS,
    const NativeFixedFunctionRenderTargetBoundDrawReadiness& boundDraw,
    const NativeFixedFunctionDrawReadiness& draw,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeFixedFunctionDirectDrawDispatchReadiness& dispatch,
    D3DPRIMITIVETYPE primitive,
    UINT primitiveCount,
    UINT startVertexLocation) noexcept;

// R149 preserves the D3D9 DrawIndexedPrimitive source-range arguments before
// any native DrawIndexed activation. D3D11 drops MinVertexIndex/NumVertices
// from the dispatch API, so this dormant token keeps BaseVertexIndex,
// MinVertexIndex, NumVertices, StartIndex and PrimitiveCount stale-resistant.
// It proves only numeric/range identity; it does not claim source index values
// have been scanned against the declared vertex range.
struct NativeFixedFunctionIndexedSourceRangeReadiness {
    bool inputValid{};
    bool primitiveExact{};
    bool vertexRangeExact{};
    bool indexRangeExact{};
    bool ready{};
    D3D11_PRIMITIVE_TOPOLOGY topology =
        D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    UINT primitiveCount{};
    UINT elementCount{};
    INT baseVertexIndex{};
    UINT minVertexIndex{};
    UINT numVertices{};
    UINT maxVertexIndex{};
    UINT startIndex{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] NativeFixedFunctionIndexedSourceRangeReadiness
compose_fixed_function_indexed_source_range_readiness(
    D3DPRIMITIVETYPE primitive,
    UINT primitiveCount,
    INT baseVertexIndex,
    UINT minVertexIndex,
    UINT numVertices,
    UINT startIndex) noexcept;

[[nodiscard]] bool validate_fixed_function_indexed_source_range_snapshot(
    D3DPRIMITIVETYPE primitive,
    UINT primitiveCount,
    INT baseVertexIndex,
    UINT minVertexIndex,
    UINT numVertices,
    UINT startIndex,
    std::uint64_t snapshotToken) noexcept;

// R150 joins the exact R147 native DrawIndexed tuple with the R149 D3D9
// source-range identity. D3D11 drops MinVertexIndex/NumVertices at dispatch,
// so activation must carry both snapshots and prove their shared arguments
// still describe the same draw before any native DrawIndexed call.
struct NativeFixedFunctionIndexedDirectDispatchReadiness {
    bool inputValid{};
    bool directDispatchReady{};
    bool sourceRangeReady{};
    bool boundDrawReady{};
    bool dispatchMatchesSourceRange{};
    bool boundDrawMatchesDispatch{};
    bool vertexBufferRangeExact{};
    bool componentSnapshotsPresent{};
    bool ready{};
    std::uint64_t directDispatchSnapshotToken{};
    std::uint64_t sourceRangeSnapshotToken{};
    std::uint64_t boundDrawSnapshotToken{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] NativeFixedFunctionIndexedDirectDispatchReadiness
compose_fixed_function_indexed_direct_dispatch_readiness(
    const NativeFixedFunctionDirectDrawDispatchReadiness& dispatch,
    const NativeFixedFunctionIndexedSourceRangeReadiness& sourceRange,
    const NativeFixedFunctionRenderTargetBoundDrawReadiness& boundDraw) noexcept;

[[nodiscard]] bool validate_fixed_function_indexed_direct_dispatch_snapshot(
    const NativeFixedFunctionDirectDrawDispatchReadiness& dispatch,
    const NativeFixedFunctionIndexedSourceRangeReadiness& sourceRange,
    const NativeFixedFunctionRenderTargetBoundDrawReadiness& boundDraw,
    std::uint64_t snapshotToken) noexcept;

// R152 closes the remaining direct indexed source-range gap by joining the
// R150 dispatch/source-range lineage to the exact managed IB CPU-shadow values
// and the R122 geometry snapshot that owns that same IB mirror. This remains
// dormant readiness evidence only and never issues DrawIndexed.
struct NativeFixedFunctionIndexedSourceValueReadiness {
    bool inputValid{};
    bool directDispatchReady{};
    bool indexedLineageReady{};
    bool sourceRangeReady{};
    bool geometryReady{};
    bool sourceValuesReady{};
    bool dispatchMatchesLineage{};
    bool geometryMatchesSourceValues{};
    bool sourceValuesMatchRange{};
    bool componentSnapshotsPresent{};
    bool ready{};
    std::uint64_t directDispatchSnapshotToken{};
    std::uint64_t indexedLineageSnapshotToken{};
    std::uint64_t sourceRangeSnapshotToken{};
    std::uint64_t geometrySnapshotToken{};
    std::uint64_t sourceValuesSnapshotToken{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] NativeFixedFunctionIndexedSourceValueReadiness
compose_fixed_function_indexed_source_value_readiness(
    const NativeFixedFunctionDirectDrawDispatchReadiness& dispatch,
    const NativeFixedFunctionIndexedDirectDispatchReadiness& indexedLineage,
    const NativeFixedFunctionIndexedSourceRangeReadiness& sourceRange,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeManagedIndexRangeReadiness& sourceValues) noexcept;

[[nodiscard]] bool validate_fixed_function_indexed_source_value_snapshot(
    const NativeFixedFunctionDirectDrawDispatchReadiness& dispatch,
    const NativeFixedFunctionIndexedDirectDispatchReadiness& indexedLineage,
    const NativeFixedFunctionIndexedSourceRangeReadiness& sourceRange,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeManagedIndexRangeReadiness& sourceValues,
    std::uint64_t snapshotToken) noexcept;

// R153 seals R152's exact source-index values to the live IA index binding.
// The managed shadow mirrors the complete D3D9 index buffer, so an exact
// direct-DIP path must bind that mirror from byte offset zero and use the
// DXGI index format corresponding to the scanned D3D9 format. This remains
// dormant evidence only and never issues DrawIndexed.
struct NativeFixedFunctionIndexedSourceBindingReadiness {
    bool inputValid{};
    bool sourceValueLineageReady{};
    bool boundDrawReady{};
    bool boundDrawMatchesLineage{};
    bool indexFormatMatchesSourceValues{};
    bool indexOffsetExact{};
    bool componentSnapshotsPresent{};
    bool ready{};
    D3DFORMAT sourceIndexFormat = D3DFMT_UNKNOWN;
    DXGI_FORMAT boundIndexFormat = DXGI_FORMAT_UNKNOWN;
    UINT boundIndexOffset{};
    std::uint64_t sourceValueLineageSnapshotToken{};
    std::uint64_t indexedLineageSnapshotToken{};
    std::uint64_t boundDrawSnapshotToken{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] NativeFixedFunctionIndexedSourceBindingReadiness
compose_fixed_function_indexed_source_binding_readiness(
    const NativeFixedFunctionIndexedSourceValueReadiness& sourceValueLineage,
    const NativeFixedFunctionDirectDrawDispatchReadiness& dispatch,
    const NativeFixedFunctionIndexedDirectDispatchReadiness& indexedLineage,
    const NativeFixedFunctionIndexedSourceRangeReadiness& sourceRange,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeManagedIndexRangeReadiness& sourceValues,
    const NativeFixedFunctionRenderTargetBoundDrawReadiness& boundDraw) noexcept;

[[nodiscard]] bool validate_fixed_function_indexed_source_binding_snapshot(
    const NativeFixedFunctionIndexedSourceValueReadiness& sourceValueLineage,
    const NativeFixedFunctionDirectDrawDispatchReadiness& dispatch,
    const NativeFixedFunctionIndexedDirectDispatchReadiness& indexedLineage,
    const NativeFixedFunctionIndexedSourceRangeReadiness& sourceRange,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeManagedIndexRangeReadiness& sourceValues,
    const NativeFixedFunctionRenderTargetBoundDrawReadiness& boundDraw,
    std::uint64_t snapshotToken) noexcept;

// R155 proves that an indexed triangle-fan's generated immutable IB was
// materialized from the exact current MANAGED source-IB CPU shadow, rather than
// from an unrelated pointer carrying a borrowed mirror snapshot token. This is
// dormant provenance evidence only and never issues DrawIndexed.
struct NativeFixedFunctionIndexedFanSourceContentReadiness {
    bool inputValid{};
    bool generatedIndexReady{};
    bool sourceIndexReady{};
    bool sourceProvenanceMatches{};
    bool expandedContentExact{};
    bool componentSnapshotsPresent{};
    bool ready{};
    std::uint64_t generatedIndexSnapshotToken{};
    std::uint64_t sourceIndexSnapshotToken{};
    std::uint64_t expectedExpandedContentHash{};
    std::uint64_t generatedContentHash{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] NativeFixedFunctionIndexedFanSourceContentReadiness
compose_fixed_function_indexed_fan_source_content_readiness(
    const NativeManagedBufferShadow& sourceIndexBuffer,
    const NativeTriangleFanIndexBuffer& generatedIndexBuffer,
    ID3D11Device* expectedDevice) noexcept;

[[nodiscard]] bool validate_fixed_function_indexed_fan_source_content_snapshot(
    const NativeManagedBufferShadow& sourceIndexBuffer,
    const NativeTriangleFanIndexBuffer& generatedIndexBuffer,
    ID3D11Device* expectedDevice,
    std::uint64_t snapshotToken) noexcept;


// R153 live-revalidation hardening closes the stale-snapshot gap after the
// source-value/IA-format seal. It reobserves the current IA index buffer on the
// caller's D3D11 context and requires the exact current R119 managed mirror,
// format and offset before any future DrawIndexed activation. No Draw* is issued.
struct NativeFixedFunctionIndexedSourceLiveBindingReadiness {
    bool inputValid{};
    bool sourceBindingReady{};
    bool contextMatchesMirror{};
    bool indexMirrorCurrent{};
    bool liveIndexBufferExact{};
    bool liveIndexFormatExact{};
    bool liveIndexOffsetExact{};
    bool componentSnapshotsPresent{};
    bool ready{};
    DXGI_FORMAT observedIndexFormat = DXGI_FORMAT_UNKNOWN;
    UINT observedIndexOffset{};
    std::uint64_t sourceBindingSnapshotToken{};
    std::uint64_t indexMirrorSnapshotToken{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] NativeFixedFunctionIndexedSourceLiveBindingReadiness
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
    const NativeManagedBufferShadow& indexBuffer) noexcept;

[[nodiscard]] bool validate_fixed_function_indexed_source_live_binding_snapshot(
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
    std::uint64_t snapshotToken) noexcept;

// R157/R161/R162/R163/R164 offscreen WARP-only indexed DrawIndexed preflight.
// Revalidates indexed source lineage, live IA/VS/PS/GS/HS/DS, exact RS/OM
// output state, and R164 OM RTV+DSV identity. No gameplay Draw activation.
[[nodiscard]] bool prepare_fixed_function_indexed_direct_draw_probe(
    ID3D11DeviceContext* context,
    ID3D11RenderTargetView* expectedProbeTarget,
    ID3D11DepthStencilView* expectedProbeDepth,
    ID3D11InputLayout* expectedProbeLayout,
    ID3D11VertexShader* expectedProbeVS,
    ID3D11PixelShader* expectedProbePS,
    const NativeFixedFunctionOutputStateBinding& expectedOutputBinding,
    const NativeFixedFunctionRenderTargetBoundDrawReadiness& boundDraw,
    const NativeFixedFunctionDrawReadiness& draw,
    const NativeFixedFunctionGeometryReadiness& geometry,
    const NativeFixedFunctionDirectDrawDispatchReadiness& dispatch,
    const NativeFixedFunctionIndexedDirectDispatchReadiness& indexedLineage,
    const NativeFixedFunctionIndexedSourceRangeReadiness& sourceRange,
    const NativeManagedIndexRangeReadiness& sourceValues,
    const NativeFixedFunctionIndexedSourceValueReadiness& sourceValueLineage,
    const NativeFixedFunctionIndexedSourceBindingReadiness& sourceBinding,
    const NativeManagedBufferShadow& vertexBuffer,
    const NativeManagedBufferShadow& indexBuffer,
    D3DPRIMITIVETYPE primitive, UINT primitiveCount,
    UINT startIndexLocation, INT baseVertexLocation) noexcept;

// R148 seals the eventual DrawIndexed tuple for generated triangle fans after
// the R146 live IA/VS-b0/OM proof. This remains dormant evidence only and does
// not issue DrawIndexed or enable NativeDrawPathActive.
struct NativeFixedFunctionFanDrawDispatchReadiness {
    bool inputValid{};
    bool finalFanBoundDrawReady{};
    bool generatedIndexReady{};
    bool generatedIndexMatchesDispatch{};
    // R154 seals the deterministic nonindexed fan source-vertex span against
    // the exact managed vertex-buffer byte capacity. R156 applies the same
    // fail-closed capacity proof to indexed fans using exact R155 source
    // content plus an R152 MANAGED source-index window snapshot.
    bool vertexBufferRangeExact{};
    // DX11-FAN-DECLARED-RANGE preserves D3D9 DrawIndexedPrimitive MinVertexIndex/NumVertices for
    // indexed triangle fans and proves the exact MANAGED source values stay
    // inside that declared source-vertex interval before D3D11 DrawIndexed.
    bool sourceDeclaredVertexRangeExact{};
    bool sourceValuesWithinDeclaredRange{};
    // R160 separately seals the complete D3D9 declared source-vertex window
    // against the managed VB capacity. R156 continues to represent the exact
    // observed source-index fetch capacity.
    bool sourceDeclaredVertexBufferRangeExact{};
    bool dispatchArgumentsExact{};
    bool componentSnapshotsPresent{};
    bool ready{};
    bool indexedSource{};
    UINT primitiveCount{};
    UINT indexCount{};
    UINT startIndexLocation{};
    INT baseVertexLocation{};
    std::uint64_t finalFanBoundDrawSnapshotToken{};
    std::uint64_t generatedIndexSnapshotToken{};
    std::uint64_t sourceIndexSnapshotToken{};
    std::uint64_t sourceContentSnapshotToken{};
    // R156 seals the exact source-index values used to derive indexed fan
    // vertex capacity. Zero for nonindexed fans.
    UINT sourceObservedMinIndex{};
    UINT sourceObservedMaxIndex{};
    UINT sourceMinVertexIndex{};
    UINT sourceNumVertices{};
    UINT sourceMaxVertexIndex{};
    std::uint64_t sourceValueSnapshotToken{};
    std::uint64_t snapshotToken{};
};

[[nodiscard]] NativeFixedFunctionFanDrawDispatchReadiness
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
    const NativeSurfaceMirror& depthSurface) noexcept;

[[nodiscard]] bool
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
    std::uint64_t snapshotToken) noexcept;

[[nodiscard]] NativeFixedFunctionFanDrawDispatchReadiness
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
    const NativeSurfaceMirror& depthSurface) noexcept;

[[nodiscard]] bool
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
    std::uint64_t snapshotToken) noexcept;


class NativeBackend final {
    // White-box WARP fixture validates transactional COM ownership without
    // enabling a native gameplay Draw or an extra production initialization API.
    friend struct NativeBackendResizeProbeAccess;
public:
    NativeBackend() = default;
    ~NativeBackend() = default;
    NativeBackend(const NativeBackend&) = delete;
    NativeBackend& operator=(const NativeBackend&) = delete;

    bool initialize(const NativeBackendConfig& config) noexcept;
    bool resize(std::uint32_t width, std::uint32_t height) noexcept;
    void begin_frame(const std::array<float, 4>& clear_color) noexcept;

    [[nodiscard]] NativeProgrammableShaderProductionObservationEvidence
    observe_programmable_shader_source_evidence_chain(
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
        const NativeProgrammableShaderSourceMappingHandoff& sourceMappingHandoff,
        std::uint64_t sourceMappingHandoffSnapshotToken,
        const NativeProgrammableShaderSemanticTranslationPlanEvidence&
            translationPlan,
        std::uint64_t translationPlanSnapshotToken) noexcept;
    void shutdown() noexcept;

    [[nodiscard]] bool ready() const noexcept {
        return device_ && context_ && color_texture_ && color_rtv_ && color_srv_;
    }
    [[nodiscard]] D3D_FEATURE_LEVEL feature_level() const noexcept { return feature_level_; }
    [[nodiscard]] const NativeBackendConfig& config() const noexcept { return config_; }
    [[nodiscard]] ID3D11Device* device() const noexcept { return device_.Get(); }
    [[nodiscard]] ID3D11DeviceContext* context() const noexcept { return context_.Get(); }
    [[nodiscard]] ID3D11Texture2D* color_texture() const noexcept { return color_texture_.Get(); }
    [[nodiscard]] ID3D11RenderTargetView* color_rtv() const noexcept { return color_rtv_.Get(); }
    [[nodiscard]] ID3D11ShaderResourceView* color_srv() const noexcept { return color_srv_.Get(); }
    [[nodiscard]] NativeProgrammableShaderBackendOwnership&
    programmable_shader_ownership() noexcept {
        return programmable_shader_ownership_;
    }
    [[nodiscard]] const NativeProgrammableShaderBackendOwnership&
    programmable_shader_ownership() const noexcept {
        return programmable_shader_ownership_;
    }
    [[nodiscard]] bool selected_adapter_luid_valid() const noexcept {
        return selected_adapter_luid_valid_;
    }
    [[nodiscard]] LUID selected_adapter_luid() const noexcept {
        return selected_adapter_luid_;
    }

private:
    bool create_color_target(std::uint32_t width, std::uint32_t height, DXGI_FORMAT format) noexcept;

    NativeBackendConfig config_{};
    D3D_FEATURE_LEVEL feature_level_ = D3D_FEATURE_LEVEL_9_1;
    LUID selected_adapter_luid_{};
    bool selected_adapter_luid_valid_ = false;
    NativeProgrammableShaderBackendOwnership programmable_shader_ownership_;
    Microsoft::WRL::ComPtr<ID3D11Device> device_;
    Microsoft::WRL::ComPtr<ID3D11DeviceContext> context_;
    Microsoft::WRL::ComPtr<ID3D11Texture2D> color_texture_;
    Microsoft::WRL::ComPtr<ID3D11RenderTargetView> color_rtv_;
    Microsoft::WRL::ComPtr<ID3D11ShaderResourceView> color_srv_;
};

} // namespace outrun::vr::dx11
