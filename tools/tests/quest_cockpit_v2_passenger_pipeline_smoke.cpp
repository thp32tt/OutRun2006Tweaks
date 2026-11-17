// Executable model of native PC 43FB40 event scene mask and 4879B0 car
// presentation gate with QuestCockpitV2's narrowly scoped ROB02 restoration.
// This models documented native dispatch predicates; NOT an HMD pixel test.
#include "../../src/vr/game/quest_cockpit_v2_passenger_event.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <initializer_list>
using namespace OutRunVR::QuestCockpitV2;

struct Trial {
  bool vr=true, cockpit=true, follow=true, racing=true;
  bool cam1=true, frame=true, stereo=true, live=true;
  std::uint32_t driverScene=0x80u, guestScene=0x80u;
  std::uint32_t carFlags=0x4000u, mask=0x80u;
  std::int32_t first=0,last=409;
};
struct Result {unsigned wrapperCalls=0,robotDraws=0,sceneRestores=0;};
constexpr Result NativeLayerWithGuestFix(const Trial& t) {
  Result r{};
  // PC 43FB40: original event flag, scene mask and event range gate.
  // Driver's current scene is NOT part of this passenger callback gate.
  const bool native=t.live &&
    t.first<=static_cast<int>(OriginalPassengerEventId) &&
    t.last>=static_cast<int>(OriginalPassengerEventId) &&
    (t.guestScene&t.mask)!=0u;
  if(native) {
    ++r.wrapperCalls; // 4879B0
    // 487880 enters 514E60, but the cockpit-only Remove option then
    // suppresses the exact guest inside RobotDisplay. Count the native
    // submission only if the render-only Remove policy admits it.
    const bool suppressed=ShouldSuppressOriginalPassenger(
        t.vr,t.cockpit,t.follow,t.racing,t.cam1,t.live);
    if(!suppressed &&
       ((t.carFlags&0xc000u)==0x4000u ||
        ShouldBypassPassengerCarDisplayGate(t.vr,t.cockpit,t.follow,
              t.racing&&t.frame&&t.stereo,t.cam1,t.live,t.carFlags)))
      ++r.robotDraws; // 487880 -> 514E60
  }
  // Hooked event pass, after native scan. No second draw if wrapper called.
  const bool restore=ShouldRecoverOriginalPassengerScenePass(
    t.vr,t.cockpit,t.follow,t.racing,t.cam1,t.live,
    t.frame,t.stereo,t.mask,t.first,t.last,t.guestScene,
    r.wrapperCalls!=0u);
  if(restore) {
    ++r.sceneRestores;
    ++r.wrapperCalls;
    // The existing 4879B0 hook forwards to native 487880, skipping
    // the original car flag when needed. Never creates a new work.
    ++r.robotDraws;
  }
  return r;
}
constexpr bool VerifyNativePassengerPipeline() {
  constexpr std::array<std::uint32_t,5> scenes{{0u,0x80u,0x40u,0x100u,0x180u}};
  constexpr std::array<std::uint32_t,4> carMasks{{0u,0x4000u,0x8000u,0xc000u}};
  // 2 driver scene x 5 guest scene x 4 car gates x 2 cameras x 2 F11
  // modes = 160 native-dispatch cases. Both-hidden is the new regression.
  for(auto driver:{0u,0x80u}) for(auto guest:scenes)
  for(auto car:carMasks) for(int camera=0;camera<2;++camera)
  for(int follow=0;follow<2;++follow) {
    Trial t{};
    t.driverScene=driver;t.guestScene=guest;t.carFlags=car;
    t.cam1=camera!=0;t.follow=follow!=0;
    const auto r=NativeLayerWithGuestFix(t);
    if(r.robotDraws>1u||r.sceneRestores>1u)return false;
    if((!t.cam1||!t.follow)&&r.sceneRestores!=0u)return false;
    // Camera0: native game unchanged regardless of Follow/Remove.
    const unsigned orig=((guest&0x80u)!=0u && car==0x4000u)?1u:0u;
    if(!t.cam1&&r.robotDraws!=orig)return false;
    if(t.cam1&&!t.follow&&r.robotDraws!=0u)return false;
    if(t.cam1&&t.follow) {
      const unsigned want=(guest==0u||(guest&0x80u)!=0u)?1u:0u;
      if(r.robotDraws!=want)return false;
      if(guest==0u&&r.sceneRestores!=1u)return false;
      if(guest!=0u&&r.sceneRestores!=0u)return false;
    }
  }
  // 64 combinations of disabled safety gates. Only all six true
  // may recover the exact live original passenger from a fully hidden scene.
  for(unsigned bits=0;bits<64u;++bits) {
    Trial t{};
    t.driverScene=0u;t.guestScene=0u;t.carFlags=0u;
    t.vr=(bits&1u)!=0u;t.cockpit=(bits&2u)!=0u;
    t.follow=(bits&4u)!=0u;t.racing=(bits&8u)!=0u;
    t.frame=(bits&16u)!=0u;t.stereo=(bits&32u)!=0u;
    const auto r=NativeLayerWithGuestFix(t);
    if(r.sceneRestores!=(bits==63u?1u:0u))return false;
  }
  Trial dead{};dead.guestScene=0u;dead.live=false;
  if(NativeLayerWithGuestFix(dead).robotDraws!=0u)return false;
  Trial alt{};alt.guestScene=0x40u;alt.mask=0x40u;
  if(NativeLayerWithGuestFix(alt).sceneRestores!=0u)return false;
  Trial range{};range.guestScene=0u;range.last=362;
  if(NativeLayerWithGuestFix(range).sceneRestores!=0u)return false;
  Trial gate{};gate.guestScene=0x80u;gate.carFlags=0u;
  const auto existing=NativeLayerWithGuestFix(gate);
  if(existing.sceneRestores!=0u||existing.robotDraws!=1u)return false;
  return true;
}
static_assert(VerifyNativePassengerPipeline(),
  "original camera0 parity, both-hidden cockpit restore, no double draw");
int main() {
  assert(VerifyNativePassengerPipeline());
  std::puts("PASS modeled 43FB40 -> 4879B0 -> 487880 native ROB02 pipeline");
}
