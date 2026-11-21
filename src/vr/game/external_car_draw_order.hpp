#pragma once
// Pure pass selection for the optional Ferrari sidecar only.
// Opaque meshes must establish depth before transparent glass is blended.
// Avoid sorting/copying GPU objects and allocating memory on each eye draw.
namespace OutRunVR::DinoSidecar {
constexpr bool MeshInDrawPass(bool isGlass, unsigned pass) noexcept {
    return pass < 2u && isGlass == (pass == 1u);
}
static_assert(MeshInDrawPass(false,0u));
static_assert(!MeshInDrawPass(true,0u));
static_assert(MeshInDrawPass(true,1u));
static_assert(!MeshInDrawPass(false,1u));
static_assert(!MeshInDrawPass(false,2u));
} // namespace OutRunVR::DinoSidecar
