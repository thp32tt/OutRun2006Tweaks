// Compile-only native Windows-independent OutRun HUD/FFP reference contract.
#include "vr/game/disasm_render_contract.hpp"
#include <cstdint>
#include <cstdio>
using namespace OutRunVR::DisasmContract;
static_assert(RankMarkerCallRvas.size() == 9, "Decomp verified 4 + 5 rank callsites");
static_assert(RankMarkerCallRvas[0]==0xBB0FB && RankMarkerCallRvas[3]==0xBB1A5,"SPRANI callsite drift");
static_assert(RankMarkerCallRvas[4]==0xBB21F && RankMarkerCallRvas[8]==0xBB2D0,"clip callsite drift");
static_assert(IsRankMarkerCall(0xBB133) && IsRankMarkerCall(0xBB271),"rank hook coverage");
static_assert(!IsRankMarkerCall(0xBAD20) && !IsRankMarkerCall(0xB9DA6),"producer/DispRank isolation");
static_assert(ClassifyCriticalProducer(0xBAD20)==SpacePolicy::WorldBillboard,"protected runtime classification");
// Diagnostic-only example: disabled D3D9 state must not alter a Vulkan pipeline key.
// This is NOT linked into OutRun's DXVK provider.
struct Key {
  bool depth, depthWrite, blend;
  std::uint32_t depthFunc, src, dst;
  constexpr bool operator==(const Key& r) const noexcept {
    return depth==r.depth && depthWrite==r.depthWrite && blend==r.blend &&
           depthFunc==r.depthFunc && src==r.src && dst==r.dst;
  }
};
constexpr Key diagnosticNormalize(Key k) noexcept {
  if(!k.depth){ k.depthWrite=false; k.depthFunc=0; }
  if(!k.blend){ k.src=0; k.dst=0; }
  return k;
}
static_assert(diagnosticNormalize({false,true,false,2,6,5})==
              diagnosticNormalize({false,false,false,7,1,2}),
              "inactive depth/blend bits should not generate distinct example keys");
static_assert(!(diagnosticNormalize({true,true,true,2,6,5})==
                diagnosticNormalize({true,true,true,2,1,2})),
              "active blending must preserve distinct state");
int main(){ std::puts("outrun2-decomp-reference C++ contracts OK"); }
