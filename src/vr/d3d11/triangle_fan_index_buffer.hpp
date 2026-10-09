#pragma once

#include <cstdint>
#include <d3d9.h>
#include <d3d11.h>
#include <wrl/client.h>

namespace outrun::vr::dx11 {

// R126 dormant ownership/readiness identity for one generated triangle-fan
// D3D11 R32_UINT index stream. The owner may bind only an explicitly supplied
// D3D11 context; no D3D9 Draw* hook routes through this class.
// R141 observes the exact live IA state for the generated fan owner after bind.
// This is dormant evidence only; it never issues a Draw* call.
struct NativeTriangleFanIndexBufferBindingReadiness {
    bool inputValid{};
    bool ownerReady{};
    bool contextMatches{};
    bool bufferBoundExact{};
    bool formatExact{};
    bool offsetExact{};
    bool topologyExact{};
    bool ready{};
    std::uint64_t ownerSnapshotToken{};
    std::uint64_t snapshotToken{};
};

struct NativeTriangleFanIndexBufferReadiness {
    bool resourcesOwned{};
    bool deviceMatches{};
    bool descriptorExact{};
    bool sourceProvenanceExact{};
    bool indexedSource{};
    bool ready{};
    UINT indexCount{};
    UINT primitiveCount{};
    UINT baseVertex{};
    D3DFORMAT sourceIndexFormat = D3DFMT_UNKNOWN;
    UINT sourceStartIndex{};
    UINT sourceIndexCount{};
    std::uint64_t sourceIndexSnapshotToken{};
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
    // R129 additionally seals the exact source-index mirror snapshot used to
    // materialize the fan. Indexed geometry may consume this owner only while
    // that source snapshot is still current.
    bool initialize_indexed(
        ID3D11Device* device,
        UINT primitiveCount,
        D3DFORMAT sourceIndexFormat,
        UINT startIndex,
        const void* sourceIndices,
        UINT sourceIndexCount,
        std::uint64_t sourceIndexSnapshotToken) noexcept;

    // R182: isolated guarded D3D11 DrawIndexed, never a gameplay D3D9 hook.
    // True means the D3D11 command was issued, not successful GPU/HMD output.
    [[nodiscard]] bool draw_indexed_dormant(
        ID3D11DeviceContext* context,
        std::uint64_t bindingSnapshotToken,
        ID3D11RenderTargetView* expectedColorTarget,
        INT baseVertexLocation = 0) const noexcept;

    // Dormant binding primitive for hosted validation/future native callers.
    // It rejects foreign-device contexts and always binds R32_UINT offset 0
    // plus TRIANGLELIST topology.
    bool bind(ID3D11DeviceContext* context) const noexcept;

    [[nodiscard]] NativeTriangleFanIndexBufferReadiness readiness(
        ID3D11Device* expectedDevice) const noexcept;
    [[nodiscard]] bool validate_readiness_snapshot(
        ID3D11Device* expectedDevice,
        std::uint64_t snapshotToken) const noexcept;

    [[nodiscard]] NativeTriangleFanIndexBufferBindingReadiness
    binding_readiness(ID3D11DeviceContext* context) const noexcept;
    [[nodiscard]] bool validate_binding_snapshot(
        ID3D11DeviceContext* context,
        std::uint64_t snapshotToken) const noexcept;

    void shutdown() noexcept;

    [[nodiscard]] bool ready() const noexcept {
        return device_ && buffer_ && index_count_ != 0 && content_hash_ != 0 &&
            source_provenance_exact_;
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
    bool source_provenance_exact_ = false;
    bool indexed_source_ = false;
    UINT primitive_count_ = 0;
    UINT base_vertex_ = 0;
    D3DFORMAT source_index_format_ = D3DFMT_UNKNOWN;
    UINT source_start_index_ = 0;
    UINT source_index_count_ = 0;
    std::uint64_t source_index_snapshot_token_ = 0;
    std::uint64_t generation_ = 0;
    std::uint64_t content_hash_ = 0;
};

} // namespace outrun::vr::dx11
