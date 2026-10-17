#include "../../src/vr/game/dds_fast_loader_request.hpp"
using namespace OutRunVR::DdsFastLoad;
static_assert(kD3dxFromFile == 0xfffffffdu,
              "legacy D3DX file-format sentinel ABI changed");
static_assert(RequestedMipCountSupported(0xffffffffu, 1, 0xffffffffu));
static_assert(RequestedMipCountSupported(3, 3, 0xffffffffu));
static_assert(!RequestedMipCountSupported(0, 3, 0xffffffffu));
static_assert(!RequestedMipCountSupported(4, 3, 0xffffffffu));
static_assert(RequestedFormatSupported(0xffffffffu, 21, 0xffffffffu, 0xfffffffdu));
static_assert(RequestedFormatSupported(kD3dxFromFile, 21, 0xffffffffu, kD3dxFromFile));
static_assert(RequestedFormatSupported(21, 21, 0xffffffffu, 0xfffffffdu));
static_assert(!RequestedFormatSupported(22, 21, 0xffffffffu, kD3dxFromFile));
static_assert(!RequestedFormatSupported(0, 21, 0xffffffffu, kD3dxFromFile));
int main() { return 0; }
