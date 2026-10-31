#include "../src/vr/d3d11/native_game_inert_stencil_mrt.hpp"
using namespace outrun::vr::dx11::live_game_frame;
constexpr GameNativeStencilEvidence inert(bool twoSided, unsigned mask) {
    GameNativeStencilEvidence e{};
    e.enabled = e.known = true;
    e.twoSided = twoSided;
    e.frontCompare = 8u;
    e.backCompare = 8u;
    e.writeMask = mask;
    e.operationsKnown = true;
    e.frontOps = {1u, 1u, 1u};
    e.backOps = {1u, 1u, 1u};
    return e;
}
constexpr auto oneFace = inert(false, 0xffffffffu);
constexpr auto twoFaces = inert(true, 0xffffffffu);
static_assert(GameNativeInertStencilMrt::draw_inert({}));
static_assert(GameNativeInertStencilMrt::draw_inert(inert(false, 0u)));
static_assert(GameNativeInertStencilMrt::draw_inert(inert(true, 0u)));
static_assert(GameNativeInertStencilMrt::draw_inert(oneFace));
static_assert(GameNativeInertStencilMrt::draw_inert(twoFaces));
static_assert(!GameNativeInertStencilMrt::draw_inert(
    [] { auto e=oneFace; e.known=false; return e; }()));
static_assert(!GameNativeInertStencilMrt::draw_inert(
    [] { auto e=oneFace; e.frontCompare=5u; return e; }()));
static_assert(!GameNativeInertStencilMrt::draw_inert(
    [] { auto e=twoFaces; e.backCompare=4u; return e; }()));
static_assert(!GameNativeInertStencilMrt::draw_inert(
    [] { auto e=oneFace; e.frontOps[1]=3u; return e; }()));
static_assert(!GameNativeInertStencilMrt::draw_inert(
    [] { auto e=twoFaces; e.backOps[2]=2u; return e; }()));
static_assert(!GameNativeInertStencilMrt::draw_inert(
    [] { auto e=oneFace; e.operationsKnown=false; return e; }()));
static_assert(GameNativeInertStencilMrt::draw_inert(
    [] { auto e=oneFace; e.writeMask=0u; e.operationsKnown=false; return e; }()));
static_assert(GameNativeInertStencilMrt::stencil_equivalent_to_disabled(
    true, true, 8u, 0u, false));
static_assert(!GameNativeInertStencilMrt::stencil_equivalent_to_disabled(
    true, true, 8u, 1u, false));
int main() { return 0; }
