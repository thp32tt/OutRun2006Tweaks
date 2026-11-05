#include "src/vr/game/dino_external_stereo_bridge.hpp"
// Compile-only Windows D3D9/Ex ABI coverage; no game dependency or device needed.
static_assert(sizeof(OutRunVR::DinoSidecar::Vertex)==32,"Dino vertex ABI");
int main(){return 0;}
