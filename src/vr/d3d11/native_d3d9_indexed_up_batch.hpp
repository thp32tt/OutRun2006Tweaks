#pragma once
// R238: isolated D3D9 DrawIndexedPrimitiveUP caller-attested CPU span ->
// generation-owned D3D11 VB/IB -> single-eye WARP DrawIndexed readiness.
// This owner never installs a gameplay hook or dispatches a gameplay Draw.
#include "native_indexed_target_viewport.hpp"
#include <cstdint>
#include <cstring>
#include <limits>

namespace outrun::vr::dx11 {
class NativeD3D9IndexedUPBatch final {
public:
    [[nodiscard]] bool capture(
        ID3D11Device* device,
        const void* vertices, UINT readableVertexBytes,
        const void* indices, UINT readableIndexBytes,
        D3DPRIMITIVETYPE primitiveType, UINT minVertexIndex,
        UINT numVertices, UINT primitiveCount, D3DFORMAT indexFormat,
        UINT vertexStride, std::uint64_t generation,
        std::uint64_t vertexVersion, std::uint64_t indexVersion) noexcept {
        reset(); // Failed replacement cannot leave an old batch draw-ready.
        // The first implementation only admits zero-based UP index windows;
        // nonzero MinVertexIndex needs separately proven D3D9 pointer semantics.
        if (!device || !vertices || !indices ||
            primitiveType != D3DPT_TRIANGLELIST || minVertexIndex != 0 ||
            !numVertices || !primitiveCount || !vertexStride ||
            !generation || !vertexVersion || !indexVersion ||
            (indexFormat != D3DFMT_INDEX16 && indexFormat != D3DFMT_INDEX32) ||
            primitiveCount > (std::numeric_limits<UINT>::max)() / 3u)
            return false;
        const UINT indexCount = primitiveCount * 3u;
        const UINT indexStride = indexFormat == D3DFMT_INDEX16 ? 2u : 4u;
        if (numVertices > (std::numeric_limits<UINT>::max)() / vertexStride ||
            indexCount > (std::numeric_limits<UINT>::max)() / indexStride)
            return false;
        const UINT vertexBytes = numVertices * vertexStride;
        const UINT indexBytes = indexCount * indexStride;
        if (readableVertexBytes < vertexBytes || readableIndexBytes < indexBytes)
            return false;
        // D3D9 UP pointers are transient. Validate every index before handing
        // the exact source span to immutable native DEFAULT buffers.
        const auto* source = static_cast<const std::uint8_t*>(indices);
        for (UINT n = 0; n < indexCount; ++n) {
            UINT value = 0;
            std::memcpy(&value, source + static_cast<std::size_t>(n) * indexStride,
                        indexStride);
            if (value >= numVertices) return false;
        }
        if (!vertex_.initialize(device, ResourceRole::Vertex,
                                D3DPOOL_DEFAULT, D3DUSAGE_WRITEONLY,
                                D3DFMT_UNKNOWN, vertices, vertexBytes,
                                vertexStride, generation, vertexVersion))
            return false;
        if (!index_.initialize(device, ResourceRole::Index,
                               D3DPOOL_DEFAULT, D3DUSAGE_WRITEONLY,
                               indexFormat, indices, indexBytes, 0u,
                               generation, indexVersion)) {
            reset();
            return false;
        }
        index_count_ = indexCount;
        generation_ = generation;
        vertex_version_ = vertexVersion;
        index_version_ = indexVersion;
        return true;
    }

    [[nodiscard]] bool bind_and_verify(
        ID3D11DeviceContext* context, std::uint64_t generation,
        std::uint64_t vertexVersion, std::uint64_t indexVersion,
        UINT width, UINT height, DXGI_FORMAT format,
        ID3D11InputLayout* layout, ID3D11VertexShader* vs,
        ID3D11PixelShader* ps, ID3D11RenderTargetView* rtv) const noexcept {
        if (!context || !index_count_ || generation != generation_ ||
            vertexVersion != vertex_version_ || indexVersion != index_version_ ||
            !vertex_.bind(context, generation, vertexVersion) ||
            !index_.bind(context, generation, indexVersion))
            return false;
        return verified_indexed_single_eye_output_ready(
                   vertex_, index_, context, 0u, index_count_, 0,
                   generation, vertexVersion, indexVersion,
                   layout, vs, ps, rtv) &&
               verified_indexed_full_target_draw_ready(
                   vertex_, index_, context, 0u, index_count_, 0,
                   generation, vertexVersion, indexVersion,
                   width, height, format, rtv);
    }

    [[nodiscard]] UINT index_count() const noexcept { return index_count_; }
    void reset() noexcept {
        vertex_.shutdown();
        index_.shutdown();
        index_count_ = 0u;
        generation_ = vertex_version_ = index_version_ = 0;
    }
private:
    NativeLinearBufferMirror vertex_, index_;
    UINT index_count_ = 0u;
    std::uint64_t generation_ = 0, vertex_version_ = 0, index_version_ = 0;
};
} // namespace outrun::vr::dx11
