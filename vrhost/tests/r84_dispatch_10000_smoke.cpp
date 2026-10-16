// Actual shared DX9Ex C++ source policy, not a hand-translated Python model.
// 10,000 deterministic, distinct configurations covering producer->physical
// draw, original c64 split writes, OpenXR eye sizing and menu clipping.
// No D3D device, game process, VR driver or HMD required.
#include "../../src/vr/game/render_semantics.hpp"
#include "../../src/vr/game/queued_hud_partial_wvp.hpp"
#include "../../src/vr/ipc/xr_eye_extent.hpp"
#include "../src/runtime/menu_capture_snapshot.hpp"
#include "../src/runtime/menu_content_aspect.hpp"
#include "../../src/vr/d3d9/stage_extension_eye_plane.hpp"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
using OutRunVR::GameSemantic::PhysicalDrawCommand;
using OutRunVR::GameSemantic::RenderScope;
using OutRunVR::GameSemantic::ProducerToken;

static bool Near(float a, float b, float eps=0.0005f) {
    return std::isfinite(a) && std::isfinite(b) && std::fabs(a-b) <= eps;
}
int main() {
    constexpr int required = 10000;
    int checked=0, screen=0, world=0, hudSplit=0, hudRejected=0;
    int clipVisible=0, menuValid=0, badEye=0;
    int queueA=1, queueB=2;
    constexpr float wvpFirst[8]{1,2,3,4,5,6,7,8};
    constexpr float wvpLast[8]{9,10,11,12,13,14,15,16};
    const float identicalLeft[16]{
        1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};
    float shiftedLeft[16]{}, shiftedRight[16]{};
    for (int k=0;k<16;++k) shiftedLeft[k]=shiftedRight[k]=identicalLeft[k];
    shiftedLeft[12]=-0.07f;
    shiftedRight[12]=0.07f;
    auto fail=[&](int caseNum, const char* reason) {
        std::cerr << "FAIL case=" << caseNum << " " << reason << "\n";
        return 1;
    };
    for (int i=0;i<required;++i) {
        // Interleave all exact original scopes/producers, queue state and
        // call epochs. No state-class may inherit a screen draw's world WVP.
        const auto scope=static_cast<RenderScope>(
            (i*7+i/17) % (static_cast<int>(RenderScope::ScreenHud)+1));
        const auto producer=static_cast<ProducerToken>(
            (i*13+i/29) % (static_cast<int>(ProducerToken::PauseOptionArrow)+1));
        const bool queued=(i&1)!=0;
        const std::uint64_t lensEpoch=(i%5==0)?0u:static_cast<std::uint64_t>(i+1);
        const PhysicalDrawCommand draw{
            scope,producer,queued?static_cast<const void*>(&queueA):nullptr,
            queued?static_cast<std::uint64_t>(i+1):0u,queued,lensEpoch};
        const bool expectScreen=scope==RenderScope::ScreenHud ||
            scope==RenderScope::ScreenOverlay2D ||
            scope==RenderScope::ProjectedWorldMarker2D ||
            scope==RenderScope::ProjectedScreenEffect2D ||
            scope==RenderScope::SkyGlow;
        if(draw.DeniesGenericWorldFallback()!=expectScreen)
            return fail(i,"R33 screen WVP fallback owner");
        if(expectScreen) ++screen; else ++world;
        const bool exactFlare=!queued && scope==RenderScope::WorldBillboard &&
            producer==ProducerToken::LensFlareCentre && lensEpoch!=0u;
        const bool shadow=!queued && scope==RenderScope::WorldParticle &&
            producer==ProducerToken::CarBaseShadow;
        if(draw.IsDirectWorldLensCentre()!=exactFlare ||
            draw.IsDirectCarBaseShadow()!=shadow ||
            draw.CanUseGenericXyzrhwStereo()==(exactFlare||shadow))
            return fail(i,"XYZRHW flare/shadow producer exclusion");
        const bool provenHud=scope==RenderScope::ScreenHud &&
            producer!=ProducerToken::None;
        const bool needsStereo=provenHud || (queued &&
            producer!=ProducerToken::None &&
            scope==RenderScope::ProjectedWorldMarker2D);
        if(draw.IsSourceProvenHud()!=provenHud ||
            draw.NeedsScreenStereoOrOriginal()!=needsStereo)
            return fail(i,"R33 exact HUD owner fallback");
        const bool finiteResult=scope==RenderScope::ScreenHud &&
            (producer==ProducerToken::StageExtensionTime ||
             producer==ProducerToken::GoalTime020 ||
             producer==ProducerToken::GoalTime150 ||
             producer==ProducerToken::ResultProgress ||
             producer==ProducerToken::OutRunStagePrintf ||
             producer==ProducerToken::ResultTextB9200);
        if(draw.IsExactFiniteResultHud()!=finiteResult)
            return fail(i,"result +TIME/GOAL producer classification");
        if(OutRunVR::GameSemantic::QueueOverlayNeedsFiniteHudPlane(
            scope,queued,(i%3==0)) !=
            (scope==RenderScope::ScreenOverlay2D && queued && i%3!=0))
            return fail(i,"generic queue/overlay external UI isolation");

        // Native split uploads are allowed ONLY for a complete matching
        // original SpriteNode/shader/pose/device/draw lease.
        const std::uint64_t epoch=1u+(i%137);
        OutRunVR::HudQueuedWvp::Upload original{};
        const bool first=original.Append(64,2,wvpFirst,true,
            RenderScope::ScreenHud,ProducerToken::OutRunHudText,
            &queueA,epoch,4,0x100,3,0x200,i+1);
        if(first) return fail(i,"partial c64 acknowledged as complete");
        const int mutation=i%8;
        const void* node=(mutation==1)?static_cast<const void*>(&queueB):
            static_cast<const void*>(&queueA);
        const auto owner=(mutation==2)?ProducerToken::ResultProgress:
            ProducerToken::OutRunHudText;
        const auto drawSerial=static_cast<std::uint64_t>(i+1+(mutation==3));
        const auto pose=static_cast<std::uint64_t>(4+(mutation==4));
        const auto shaderEpoch=static_cast<std::uint64_t>(3+(mutation==5));
        const bool queueActive=mutation!=6;
        const auto secondScope=(mutation==7)?
            RenderScope::WorldParticle:RenderScope::ScreenHud;
        const bool complete=original.Append(66,2,wvpLast,queueActive,
            secondScope,owner,node,epoch,pose,0x100,shaderEpoch,
            0x200,drawSerial);
        if(complete!=(mutation==0))
            return fail(i,"split c64 stale producer/epoch/draw authorization");
        if(complete) ++hudSplit; else ++hudRejected;

        // Actual host->D3D9Ex published eye geometry, never 3440x1440
        // desktop mirror substitution or different left/right array sizes.
        using namespace OutRunVR::EyeExtent;
        const ViewLimits left{{static_cast<std::uint32_t>(700+i%1800),
            static_cast<std::uint32_t>(700+i%900)},{2800,3000}};
        const ViewLimits right{{static_cast<std::uint32_t>(800+(i*3)%1700),
            static_cast<std::uint32_t>(800+(i*7)%1200)},{2650,2900}};
        const float scales[]{0.0f,0.5f,0.78f,1.0f,1.4f,2.0f};
        const float scale=scales[i%6];
        const Size expected=ResolveHost(left,right,scale);
        if(scale==0.0f) {
            if(Valid(expected)) return fail(i,"invalid XR scale accepted");
            ++badEye;
        } else {
            const std::uint32_t capW=2650,capH=2900;
            // ResolveHost publishes the *allocated* XR size. D3D9Ex's
            // startup contract intentionally refuses below 640x480; it
            // must NOT resize the two eyes or impersonate desktop pixels.
            const bool startupEligible =
                expected.width>=640u && expected.height>=480u &&
                static_cast<std::uint64_t>(expected.width)*expected.height
                    <=16777216ull;
            if(!Valid(expected) || expected.width>capW ||
                expected.height>capH ||
                Valid(ResolveStartup(expected,expected))!=startupEligible ||
                !Equal(ResolveGame(expected,{capW,capH}),expected))
                return fail(i,"XR eye extent/host publication");
            if(Valid(ResolveStartup(expected,{expected.width+1,expected.height})))
                return fail(i,"unequal eye texture extent accepted");
            if(Valid(ResolveGame(expected,{expected.width-1,expected.height})))
                return fail(i,"game silently resized below host RT");
        }

        // Desktop Dup sampled menu UV clipping is orthogonal to OpenXR
        // eye extent and cannot silently reproject an offscreen client.
        const std::int64_t l=(i*17)%3200-640;
        const std::int64_t t=(i*11)%1900-420;
        const std::int64_t rr=l+640+i%1200;
        const std::int64_t bb=t+480+i%500;
        const auto clip=OutRunVrMenuCapture::ClipClient(l,t,rr,bb,1920,1080);
        if(clip.fullyVisible && !clip.visible)
            return fail(i,"partial menu classified complete");
        if(clip.visible) {
            ++clipVisible;
            if(clip.x<0.0f || clip.y<0.0f ||
               clip.width<=0.01f || clip.height<=0.01f ||
               clip.x+clip.width>1.0001f ||
               clip.y+clip.height>1.0001f ||
               clip.fullyVisible!=(l>=0 && t>=0 && rr<=1920 && bb<=1080))
                return fail(i,"capture UV/visible region invalid");
        }

        // Canted/asymmetric shared menu plane with unchanged physical
        // authored aspect at default, optional and full optical coverage.
        const float aspect=0.60f+(i%240)*0.01f;
        const float coverage=(i%3==0)?0.78f:(i%3==1?0.90f:1.0f);
        const auto fov=OutRunVrMenuAspect::PlanCommonFovTangents(
            -.78f,.86f,-.69f,.74f, -.88f,.80f,-.78f,.67f);
        const auto plane=OutRunVrMenuAspect::PlanOpticallyCenteredClip(
            fov,aspect,coverage);
        if(!fov.valid || !plane.valid)
            return fail(i,"common canted eye menu rejected");
        const float physical=plane.halfWidth/plane.halfHeight *
            (fov.right-fov.left)/(fov.up-fov.down);
        if(!Near(physical,aspect,0.001f) ||
            std::fabs(plane.centerX)+plane.halfWidth>1.0001f ||
            std::fabs(plane.centerY)+plane.halfHeight>1.0001f)
            return fail(i,"menu distortion or clipped stereo eye");
        ++menuValid;

        // Paired XYZRHW HUD geometry: both eye maps consume identical
        // source pixels, with a controlled relative optical IPD shift.
        float lx=0,ly=0,rx=0,ry=0;
        const float x=static_cast<float>((i*37)%640);
        const float y=static_cast<float>((i*19)%480);
        const float size=0.3f+(i%80)*0.01f;
        if(!OutRunVR::StageExtensionPlane::ProjectPixelPair(
            shiftedLeft,shiftedRight,x,y,0,0,640,480,size,
            lx,ly,rx,ry) ||
            !Near(rx-lx,44.8f,0.005f) || !Near(ly,ry,0.0005f))
            return fail(i,"HUD left/right projection mismatch");
        ++checked;
    }
    if(checked!=required || screen==0 || world==0 ||
       hudSplit==0 || hudRejected==0 || clipVisible==0 ||
       menuValid!=required || badEye==0)
        return fail(required,"incomplete combination coverage");
    std::cout << "PASS 10000 C++ DX9Ex multi-angle cases"
              << " screen="<<screen<<" world="<<world
              << " c64_complete="<<hudSplit
              << " c64_rejected="<<hudRejected
              << " menu_visible="<<clipVisible
              << " menu_both_eye="<<menuValid
              << " bad_eye_refused="<<badEye<<"\n";
    return 0;
}
