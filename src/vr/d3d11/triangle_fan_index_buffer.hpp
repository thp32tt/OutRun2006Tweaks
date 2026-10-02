#pragma once

#include <cstdint>
#include <d3d9.h>
#include <d3d11.h>
#include <wrl/client.h>

namespace outrun::vr::dx11 {

// R126 dormant ownership/readiness identity for one generated triangle-fan
// D3D11 R32_UINT index stream. The owner may bind only an explicitly supplied
// D3D11 context; no D3D9 Draw* hook routes through this class.
struct NativeTriangleFanIndexBufferReadiness {
    bool resourcesOwned{};
    bool deviceMatches{};
    bool descriptorExact{};
    bool ready{};
    UINT indexCount{};
    std::uint64_t generation{};
    std::uint64_t contentHash{};
    std::uint64_t snapshotToken{};
};

class NativeTriangleFanIndexBuffer final {
public:
    NativeTriangleFanIndexBuffer() = default;
    ~NativeTriangleFanIndexBuffer() = default;
    NativeTriangleFanIndexBuffer(const NativeTriangleFanIndexBuffer&) = delete;
    NativeTriangleFanIndexBuffer& operator=(const NativeTriangleFanIndexBuffer&) = delete;

    // Materializes DrawPrimitive(D3DPT_TRIANGLEFAN) vertex ordinals into an
    // immutable R32_UINT triangle-list index buffer.
    bool initialize_nonindexed(
        ID3D11Device* device,
        UINT primitiveCount,
        UINT baseVertex) noexcept;

    // Materializes DrawIndexedPrimitive(D3DPT_TRIANGLEFAN) source indices into
    // an immutable R32_UINT triangle-list index buffer. BaseVertexIndex is
    // deliberately not folded into the generated values; a future DrawIndexed
    // caller must preserve it as D3D11 BaseVertexLocation.
    bool initialize_indexed(
        ID3D11Device* device,
        UINT primitiveCount,
        D3DFORMAT sourceIndexFormat,
        UINT startIndex,
        const void* sourceIndices,
        UINT sourceIndexCount) noexcept;

    // Dormant binding primitive for hosted validation/future native callers.
    // It rejects foreign-device contexts and always binds R32_UINT offset 0
    // plus TRIANGLELIST topology.
    bool bind(ID3D11DeviceContext* context) const noexcept;

    [[nodiscard]] NativeTriangleFanIndexBufferReadiness readiness(
        ID3D11Device* expectedDevice) const noexcept;
    [[nodiscard]] bool validate_readiness_snapshot(
        ID3D11Device* expectedDevice,
        std::uint64_t snapshotToken) const noexcept;

    void shutdown() noexcept;

    [[nodiscard]] bool ready() const noexcept {
        return device_ && buffer_ && index_count_ != 0 && content_hash_ != 0;
    }
    [[nodiscard]] ID3D11Buffer* buffer() const noexcept {
        return buffer_.Get();
    }
    [[nodiscard]] UINT index_count() const noexcept {
        return index_count_;
    }
    [[nodiscard]] std::uint64_t generation() const noexcept {
        return generation_;
    }

private:
    bool initialize_materialized(
        ID3D11Device* device,
        const UINT* indices,
        UINT indexCount) noexcept;
    [[nodiscard]] bool descriptor_exact(
        ID3D11Device* expectedDevice) const noexcept;

    Microsoft::WRL::ComPtr<ID3D11Device> device_;
    Microsoft::WRL::ComPtr<ID3D11Buffer> buffer_;
    UINT index_count_ = 0;
    std::uint64_t generation_ = 0;
    std::uint64_t content_hash_ = 0;
};

} // namespace outrun::vr::dx11
