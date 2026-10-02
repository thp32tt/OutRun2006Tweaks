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
struct NativeTriangleFanIndexBufferReadiness;
struct VertexInputLayoutTranslation;
struct FixedFunctionStageState;
struct PipelineTranslation;

struct NativeBackendConfig {
    std::uint32_t width = 0;
    std::uint32_t height = 0;
    DXGI_FORMAT color_format = DXGI_FORMAT_B8G8R8A8_UNORM;
    bool request_debug_layer = false;
    bool adapter_luid_valid = false;
    bool require_adapter_luid = false;
    LUID adapter_luid{};
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
    [[nodiscard]] bool mirror_descriptor_exact(
        ID3D11Device* expectedDevice) const noexcept;
    [[nodiscard]] NativeManagedBufferMirrorReadiness mirror_readiness(
        ID3D11Device* expectedDevice) const noexcept;
    [[nodiscard]] bool validate_mirror_readiness_snapshot(
        ID3D11Device* expectedDevice,
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
// Its token is tied to the exact R112 translation snapshot and same-device COM
// identities. This is observation evidence only and never issues Draw*.
struct NativeFixedFunctionPipelineBindingReadiness {
    bool inputValid{};
    bool bundleReady{};
    bool contextMatches{};
    bool translationSnapshotValid{};
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

class NativeBackend final {
public:
    NativeBackend() = default;
    ~NativeBackend() = default;
    NativeBackend(const NativeBackend&) = delete;
    NativeBackend& operator=(const NativeBackend&) = delete;

    bool initialize(const NativeBackendConfig& config) noexcept;
    bool resize(std::uint32_t width, std::uint32_t height) noexcept;
    void begin_frame(const std::array<float, 4>& clear_color) noexcept;
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
    Microsoft::WRL::ComPtr<ID3D11Device> device_;
    Microsoft::WRL::ComPtr<ID3D11DeviceContext> context_;
    Microsoft::WRL::ComPtr<ID3D11Texture2D> color_texture_;
    Microsoft::WRL::ComPtr<ID3D11RenderTargetView> color_rtv_;
    Microsoft::WRL::ComPtr<ID3D11ShaderResourceView> color_srv_;
};

} // namespace outrun::vr::dx11