#pragma once
// Exact original +TIME stage owner ONLY. Alpha/FVF/texture never give ownership.
#include "render_semantics.hpp"
namespace OutRunVR::StageOpticalProbe {
enum class Mode : int { Off=0, Native=1, FiniteHud=2, ZeroDisparity=3, Hidden=4 };
constexpr Mode Parse(int n) noexcept { return n>=0 && n<=4 ? static_cast<Mode>(n) : Mode::Off; }
constexpr bool Selected(const OutRunVR::GameSemantic::PhysicalDrawCommand& c, int target) noexcept {
 using namespace OutRunVR::GameSemantic;
 return c.IsExactFiniteResultHud() && c.producer==ProducerToken::StageExtensionTime &&
  (!c.queued || (c.queueNode!=nullptr && c.queueEpoch!=0)) &&
  (target==0 || (target==1 && !c.queued) || (target==2 && c.queued));
}
static_assert(Parse(-1)==Mode::Off && Parse(5)==Mode::Off);
static_assert(Selected({OutRunVR::GameSemantic::RenderScope::ScreenHud,
 OutRunVR::GameSemantic::ProducerToken::StageExtensionTime,nullptr,0,false,0},0));
static_assert(!Selected({OutRunVR::GameSemantic::RenderScope::ScreenHud,
 OutRunVR::GameSemantic::ProducerToken::ResultProgress,nullptr,0,false,0},0));
static_assert(!Selected({OutRunVR::GameSemantic::RenderScope::ProjectedWorldMarker2D,
 OutRunVR::GameSemantic::ProducerToken::RankMarkerClipSprite,nullptr,0,false,0},0));
static_assert(!Selected({OutRunVR::GameSemantic::RenderScope::ScreenOverlay2D,
 OutRunVR::GameSemantic::ProducerToken::StageExtensionTime,nullptr,0,false,0},0));
static_assert(!Selected({OutRunVR::GameSemantic::RenderScope::ScreenHud,
 OutRunVR::GameSemantic::ProducerToken::StageExtensionTime,nullptr,1,true,0},0));
static_assert(!Selected({OutRunVR::GameSemantic::RenderScope::ScreenHud,
 OutRunVR::GameSemantic::ProducerToken::StageExtensionTime,nullptr,0,false,0},2));
}
