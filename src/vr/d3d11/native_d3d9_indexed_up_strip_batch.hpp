#pragma once
// R239: D3D9 indexed-UP triangle strip -> winding-correct, immutable D3D11
// triangle-list VB/IB ownership. Dormant adapter: no intercepted gameplay Draw.
#include "native_d3d9_indexed_up_batch.hpp"
#include <cstdint>
#include <cstring>
#include <limits>
#include <memory>
#include <new>
#include <utility>

namespace outrun::vr::dx11 {
class NativeD3D9IndexedUPStripBatch final {
public:
    [[nodiscard]] bool capture(
        ID3D11Device* device, const void* vertices, UINT readableVertexBytes,
        const void* indices, UINT readableIndexBytes, D3DPRIMITIVETYPE type,
        UINT minVertexIndex, UINT numVertices, UINT primitiveCount,
        D3DFORMAT indexFormat, UINT vertexStride, std::uint64_t generation,
        std::uint64_t vertexVersion, std::uint64_t indexVersion) noexcept {
        reset(); // Failed recapture must revoke old IA bindings.
        if (type != D3DPT_TRIANGLESTRIP || !device || !vertices || !indices ||
            minVertexIndex != 0 || !numVertices || !primitiveCount ||
            !vertexStride || !generation || !vertexVersion || !indexVersion ||
            (indexFormat != D3DFMT_INDEX16 && indexFormat != D3DFMT_INDEX32) ||
            primitiveCount > (std::numeric_limits<UINT>::max)() / 3u)
            return false;
        const UINT width = indexFormat == D3DFMT_INDEX16 ? 2u : 4u;
        const UINT inputCount = primitiveCount + 2u;
        const UINT triangleIndices = primitiveCount * 3u;
        if (inputCount > (std::numeric_limits<UINT>::max)() / width ||
            triangleIndices > (std::numeric_limits<UINT>::max)() / width ||
            readableIndexBytes < inputCount * width)
            return false;
        // D3D9 UP callers attest readability; no attempt is made to probe
        // arbitrary pointers or to retain transient CPU memory after capture.
        const auto* source = static_cast<const std::uint8_t*>(indices);
        const UINT expandedBytes = triangleIndices * width;
        std::unique_ptr<std::uint8_t[]> expanded(
            new (std::nothrow) std::uint8_t[expandedBytes]);
        if (!expanded) return false;
        for (UINT i = 0; i < primitiveCount; ++i) {
            UINT a = 0, b = 0, c = 0;
            std::memcpy(&a, source + static_cast<std::size_t>(i) * width, width);
            std::memcpy(&b, source + static_cast<std::size_t>(i + 1u) * width, width);
            std::memcpy(&c, source + static_cast<std::size_t>(i + 2u) * width, width);
            if (i & 1u) std::swap(a, b); // D3D9 strip alternating winding.
            if (a >= numVertices || b >= numVertices || c >= numVertices)
                return false;
            auto* dest = expanded.get() + static_cast<std::size_t>(i) * 3u * width;
            std::memcpy(dest, &a, width);
            std::memcpy(dest + width, &b, width);
            std::memcpy(dest + 2u * width, &c, width);
        }
        // R238 owns immutable DEFAULT D3D11 buffers, versions and exact
        // single-eye pipeline preflight. Expanded UP bytes die after upload.
        return owned_.capture(
            device, vertices, readableVertexBytes, expanded.get(), expandedBytes,
            D3DPT_TRIANGLELIST, 0, numVertices, primitiveCount, indexFormat,
            vertexStride, generation, vertexVersion, indexVersion);
    }

    [[nodiscard]] bool bind_and_verify(
        ID3D11DeviceContext* context, std::uint64_t generation,
        std::uint64_t vertexVersion, std::uint64_t indexVersion,
        UINT width, UINT height, DXGI_FORMAT format,
        ID3D11InputLayout* layout, ID3D11VertexShader* vs,
        ID3D11PixelShader* ps, ID3D11RenderTargetView* rtv) const noexcept {
        return owned_.bind_and_verify(context, generation, vertexVersion,
                                     indexVersion, width, height, format,
                                     layout, vs, ps, rtv);
    }
    [[nodiscard]] UINT index_count() const noexcept { return owned_.index_count(); }
    void reset() noexcept { owned_.reset(); }
private:
    NativeD3D9IndexedUPBatch owned_;
};
} // namespace outrun::vr::dx11
