#pragma once
#include <d3d11.h>

namespace outrun::vr::dx11::live_game_stereo {
// D3D9-authored menu/car/race Draws may be issued with incomplete primitive
// batches (e.g. a one-index TRIANGLELIST) while retaining valid API status.
// The GPU executes the command but cannot rasterize a color/depth primitive.
// Keep the authentic Draw ordinal and D3D9 fallback, yet never use that
// command as evidence to publish a new native OpenXR eye frame.
//
// The D3D9 game adapter has no hull/domain shader pipeline: patch topologies
// are not supported scene raster evidence, even if an inherited host state
// accidentally exposes one. Unknown/undefined topology is fail-closed.
[[nodiscard]] constexpr bool primitive_can_rasterize(
    D3D11_PRIMITIVE_TOPOLOGY topology, UINT vertexOrIndexCount) noexcept {
    switch (topology) {
    case D3D11_PRIMITIVE_TOPOLOGY_POINTLIST:
        return vertexOrIndexCount >= 1u;
    case D3D11_PRIMITIVE_TOPOLOGY_LINELIST:
    case D3D11_PRIMITIVE_TOPOLOGY_LINESTRIP:
        return vertexOrIndexCount >= 2u;
    case D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST:
    case D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP:
        return vertexOrIndexCount >= 3u;
    case D3D11_PRIMITIVE_TOPOLOGY_LINELIST_ADJ:
    case D3D11_PRIMITIVE_TOPOLOGY_LINESTRIP_ADJ:
        return vertexOrIndexCount >= 4u;
    case D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST_ADJ:
    case D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP_ADJ:
        return vertexOrIndexCount >= 6u;
    default:
        return false;
    }
}
static_assert(primitive_can_rasterize(D3D11_PRIMITIVE_TOPOLOGY_POINTLIST, 1u));
static_assert(!primitive_can_rasterize(D3D11_PRIMITIVE_TOPOLOGY_LINELIST, 1u));
static_assert(primitive_can_rasterize(D3D11_PRIMITIVE_TOPOLOGY_LINELIST, 2u));
static_assert(!primitive_can_rasterize(D3D11_PRIMITIVE_TOPOLOGY_LINESTRIP, 1u));
static_assert(!primitive_can_rasterize(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST, 1u));
static_assert(!primitive_can_rasterize(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST, 2u));
static_assert(primitive_can_rasterize(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST, 3u));
static_assert(!primitive_can_rasterize(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP, 2u));
static_assert(primitive_can_rasterize(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP, 3u));
static_assert(!primitive_can_rasterize(D3D11_PRIMITIVE_TOPOLOGY_LINELIST_ADJ, 3u));
static_assert(primitive_can_rasterize(D3D11_PRIMITIVE_TOPOLOGY_LINESTRIP_ADJ, 4u));
static_assert(!primitive_can_rasterize(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST_ADJ, 5u));
static_assert(primitive_can_rasterize(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP_ADJ, 6u));
static_assert(!primitive_can_rasterize(D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED, 3u));
static_assert(!primitive_can_rasterize(D3D11_PRIMITIVE_TOPOLOGY_3_CONTROL_POINT_PATCHLIST, 3u));
} // namespace outrun::vr::dx11::live_game_stereo
