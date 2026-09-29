// R23 renderer eligibility overlay. The R13 semantic classifier remains the
// normal path; this wrapper prevents head-tracked WVP injection and render-time
// culling-camera override until the common game-side baseline gate is eligible.
//
// R27 narrows R13's old alpha-state heuristic: a c64 upload that is already
// proven to be the main-backbuffer perspective world path is allowed to reach
// the authoritative WVP verifier regardless of alpha/cull state. Confirmed
// orthographic UI and auxiliary passes still stay stock. R27 also publishes F10
// to the host from every game BeginScene, including menus/theater mode.
//
// R28 keeps a stock-game shadow of c64..c67 so partial constant uploads cannot
// strand the device with a mixture of old head-patched rows and new stock rows.
// Perspective-world partial writes are rebuilt as one verified full WVP upload;
// non-world partial writes restore one coherent stock c64..c67 block.
//
// Recovery uses a separate pose-warmup phase. During that phase BeginScene may
// latch a fresh host pose for the upcoming authoritative clear, but the stock
// camera and stock c64 values remain on screen. The x86 recovery coordinator can
// then open stereo at a safe full clear without reusing the previous frame pose.

#include "../runtime_eligibility.hpp"
#include "../ipc/recenter_request.hpp"
#include "vr/d3d9/r13_bridge.hpp"
#include "outrun_renderer.cpp"
#include "outrun_renderer_r13_overlay.inc"
#include "outrun_renderer_r23_overlay.inc"
