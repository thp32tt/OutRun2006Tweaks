#pragma once

#include "resource_translation.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <vector>
#include <d3d9.h>
#include <d3d11.h>
#include <wrl/client.h>

namespace outrun::vr::dx11 {

struct FixedFunctionTransformConstants;
struct FixedFunctionVertexShaderPrototype;
struct FixedFunctionPixelShaderPrototype;
struct VertexInputLayoutTranslation;
struct FixedFunctionStageState;

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

// R98 dormant owner for one translated fixed-function sampler state. It
// creates a D3D11 sampler object but never binds it to a game context.
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
// DEFAULT+DYNAMIC source semantics. The object still never binds its SRV to a
// game context and has no production caller.
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

// R102 dormant CPU shadow for a single-mip uncompressed D3D9 MANAGED
// Texture2D. Shadow bytes survive device-generation changes while mirror
// readiness is invalidated until a future GPU reupload is acknowledged.
// This class owns no D3D11 resource and has no production caller.
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
    void note_mirror_uploaded() noexcept;
    void observe_device_reset() noexcept;
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
        return managed_mirror_ready(lifetime_);
    }
    [[nodiscard]] std::uint64_t shadow_version() const noexcept {
        return lifetime_.cpuShadowVersion;
    }
    [[nodiscard]] std::uint64_t device_generation() const noexcept {
        return lifetime_.deviceGeneration;
    }
    [[nodiscard]] const ManagedMirrorLifetimeState&
    lifetime_state() const noexcept {
        return lifetime_;
    }

private:
    D3DFORMAT source_format_ = D3DFMT_UNKNOWN;
    UINT width_ = 0;
    UINT height_ = 0;
    UINT row_bytes_ = 0;
    std::vector<std::uint8_t> shadow_;
    ManagedMirrorLifetimeState lifetime_{};
};

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
};

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