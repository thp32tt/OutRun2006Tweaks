#pragma once
// R237: D3D9 DrawPrimitiveUP immutable CPU source -> native IA VB -> mono
// WARP pixel. Isolated producer-to-consumer preflight only: never dispatches a
// gameplay Draw, intercepts a D3D9 hook, or claims dynamic Lock/Unlock parity.
#include "native_linear_target_viewport.hpp"
#include <limits>

namespace outrun::vr::dx11 {
class NativeD3D9UPTriangleBatch final {
public:
    // sourceByteLength is the caller-attested readable span, not an assumed
    // raw pointer allocation size. D3D9 UP memory may disappear after return;
    // NativeLinearBufferMirror copies exactly the admitted vertex bytes.
    [[nodiscard]] bool capture(
        ID3D11Device* device, const void* sourceBytes, UINT sourceByteLength,
        D3DPRIMITIVETYPE primitiveType, UINT primitiveCount, UINT vertexStride,
        std::uint64_t generation, std::uint64_t snapshotVersion) noexcept {
        reset(); // A failed re-capture retires any previously valid batch.
        if (!device || !sourceBytes || primitiveType != D3DPT_TRIANGLELIST ||
            !primitiveCount || !vertexStride || !generation || !snapshotVersion ||
            primitiveCount > (std::numeric_limits<UINT>::max)() / 3u)
            return false;
        const UINT vertexCount = primitiveCount * 3u;
        if (vertexStride > (std::numeric_limits<UINT>::max)() / vertexCount)
            return false;
        const UINT neededBytes = vertexCount * vertexStride;
        if (sourceByteLength < neededBytes)
            return false;
        if (!vertex_.initialize(device, ResourceRole::Vertex, D3DPOOL_DEFAULT,
                                D3DUSAGE_WRITEONLY, D3DFMT_UNKNOWN,
                                sourceBytes, neededBytes, vertexStride,
                                generation, snapshotVersion))
            return false;
        primitive_count_ = primitiveCount;
        generation_ = generation;
        snapshot_version_ = snapshotVersion;
        return true;
    }

    // Pipeline must be prepared by the test/caller. The exact native owned VB
    // is bound, and R236 seals the shader/RTV, single-eye and silent-output
    // hazards before a tool-only WARP Draw(3,0).
    [[nodiscard]] bool bind_and_verify(
        ID3D11DeviceContext* context,
        std::uint64_t generation, std::uint64_t snapshotVersion,
        UINT width, UINT height, DXGI_FORMAT format,
        ID3D11InputLayout* layout, ID3D11VertexShader* vs,
        ID3D11PixelShader* ps, ID3D11RenderTargetView* rtv) const noexcept {
        if (!context || !primitive_count_ ||
            generation != generation_ || snapshotVersion != snapshot_version_ ||
            !vertex_.bind(context, generation, snapshotVersion))
            return false;
        return verified_d3d9_nonindexed_triangles_ready(
            vertex_, context, D3DPT_TRIANGLELIST, 0u, primitive_count_,
            generation, snapshotVersion, width, height, format,
            layout, vs, ps, rtv);
    }

    void reset() noexcept {
        vertex_.shutdown();
        primitive_count_ = 0;
        generation_ = snapshot_version_ = 0;
    }
private:
    NativeLinearBufferMirror vertex_;
    UINT primitive_count_ = 0;
    std::uint64_t generation_ = 0;
    std::uint64_t snapshot_version_ = 0;
};
} // namespace outrun::vr::dx11
