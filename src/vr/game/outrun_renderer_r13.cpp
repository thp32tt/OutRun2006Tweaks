// R13 renderer-pose hardening compatibility wrapper.
// The reusable hardening body lives in outrun_renderer_r13_overlay.inc so later
// production owners do not need to include this historical .cpp translation unit.

#include "vr/d3d9/r13_bridge.hpp"
#include "outrun_renderer.cpp"
#include "outrun_renderer_r13_overlay.inc"
