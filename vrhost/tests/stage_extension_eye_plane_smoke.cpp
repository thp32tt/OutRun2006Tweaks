#include "../../src/vr/d3d9/stage_extension_eye_plane.hpp"
#include "../../src/vr/game/stage_extension_physical_source.hpp"
#include <cmath>
#include <limits>
#include <initializer_list>
namespace {
bool Near(float a,float b,float eps=1e-4f) {
    return std::isfinite(a)&&std::isfinite(b)&&std::fabs(a-b)<eps;
}
}
int main() {
    using OutRunVR::StageExtensionPlane::ProjectPixel;
    using OutRunVR::StageExtensionPlane::BuildStageEyePoses;
    // Two independent original +TIME SpriteNodes can share the same
    // ScreenHud/StageExtensionTime token. They must not share one delayed
    // GPU submission: R33 binds each left/right pair to a queue node/epoch.
    // Keep one native batch per node, never one Flush per D3DX Draw.
    {
        using namespace OutRunVR::GameSemantic;
        const int firstNode=1, secondNode=2;
        const auto check = [&](bool active, const void* outgoing,
                               const void* incoming, RenderScope outScope,
                               ProducerToken outToken, RenderScope inScope,
                               ProducerToken inToken) {
            return CanIsolateD3DXStageQueueNodeTransition(
                active, outgoing, incoming,
                outScope, outToken, inScope, inToken);
        };
        // Each SelectSpriteQueueNode call advances the physical epoch.
        // This includes native priority-slot reuse with the SAME pointer:
        // drain the previous homogeneous D3DX batch before the new epoch.
        // The helper is called on selection, not per D3DX Draw.
        if (!check(true, &firstNode, &secondNode,
                   RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
                   RenderScope::ScreenHud, ProducerToken::StageExtensionTime) ||
            !check(true, &firstNode, &firstNode,
                   RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
                   RenderScope::ScreenHud, ProducerToken::StageExtensionTime))
            return 60;
        // Inactive queues, missing node identity and foreign owners never
        // acquire stage +TIME batch authority or alter native fallback.
        if (check(false, &firstNode, &secondNode,
                  RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
                  RenderScope::ScreenHud, ProducerToken::StageExtensionTime) ||
            check(true, nullptr, &secondNode,
                  RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
                  RenderScope::ScreenHud, ProducerToken::StageExtensionTime) ||
            check(true, &firstNode, nullptr,
                  RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
                  RenderScope::ScreenHud, ProducerToken::StageExtensionTime))
            return 61;
        // Direct numeric +TIME registration must drain BEFORE the first
        // queued +TIME sprite even if both bear the same semantic token.
        // An old queued batch lacking an exit Flush is never reclassified
        // as a new direct owner, including with a different queue epoch.
        if (!CanDrainDirectResultBeforeFirstQueueNode(
                false, true, true, 2, true,
                RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
                RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
                true) ||
            CanDrainDirectResultBeforeFirstQueueNode(
                false, true, true, 2, true,
                RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
                RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
                false))
            return 68;
        // GOAL, F11, generic HUD and projected/world effects have their
        // own original boundaries and cannot acquire +TIME's GPU owner.
        if (check(true, &firstNode, &secondNode,
                  RenderScope::ScreenHud, ProducerToken::GoalTime020,
                  RenderScope::ScreenHud, ProducerToken::GoalTime020) ||
            check(true, &firstNode, &secondNode,
                  RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
                  RenderScope::ScreenHud, ProducerToken::GoalTime150) ||
            check(true, &firstNode, &secondNode,
                  RenderScope::WorldBillboard, ProducerToken::StageExtensionTime,
                  RenderScope::ScreenHud, ProducerToken::StageExtensionTime) ||
            check(true, &firstNode, &secondNode,
                  RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
                  RenderScope::ScreenOverlay2D, ProducerToken::StageExtensionTime))
            return 62;
        // A verified old homogeneous GPU batch must still pass the existing
        // pre-queue fence; mixed/foreign batches cannot be relabelled.
        if (!CanFlushD3DXPreQueueStageBatch(
                true, false, true,
                RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
                RenderScope::ScreenHud, ProducerToken::StageExtensionTime) ||
            CanFlushD3DXPreQueueStageBatch(
                true, false, false,
                RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
                RenderScope::ScreenHud, ProducerToken::StageExtensionTime) ||
            CanFlushD3DXPreQueueStageBatch(
                true, false, true,
                RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
                RenderScope::ScreenHud, ProducerToken::ResultProgress))
            return 63;
    }

    // GOAL 0-99%, elapsed time and stage-result text share exact screen
    // semantics across several SpriteNodes. R33 binds each queued physical
    // Draw to its own node/epoch, so same-token transitions must submit the
    // previous proven D3DX buffer before changing selection.
    {
        using namespace OutRunVR::GameSemantic;
        const int firstNode=11, secondNode=12;
        for (const auto producer : {
                ProducerToken::GoalTime020, ProducerToken::GoalTime150,
                ProducerToken::ResultProgress, ProducerToken::OutRunStagePrintf,
                ProducerToken::ResultTextB9200}) {
            const auto isolated = [&](bool active, const void* prior,
                                      const void* next, RenderScope scope,
                                      ProducerToken incoming) {
                return CanIsolateD3DXGoalQueueNodeTransition(
                    active, prior, next, scope, producer,
                    RenderScope::ScreenHud, incoming);
            };
            if (!isolated(true, &firstNode, &secondNode,
                          RenderScope::ScreenHud, producer))
                return 64;
            // A recycled pointer is a NEW queue selection/epoch, even
            // when its address and source token equal the old node.
            // Fail-before fixture: old code incorrectly returned false.
            if (!isolated(true, &firstNode, &firstNode,
                          RenderScope::ScreenHud, producer))
                return 65;
            // Queue inactive/null or a foreign screen/world source still
            // retains the original End path, with no GOAL eye ownership.
            if (isolated(false, &firstNode, &secondNode,
                         RenderScope::ScreenHud, producer) ||
                isolated(true, nullptr, &secondNode,
                         RenderScope::ScreenHud, producer) ||
                isolated(true, &firstNode, nullptr,
                         RenderScope::ScreenHud, producer) ||
                isolated(true, &firstNode, &secondNode,
                         RenderScope::ScreenOverlay2D, producer) ||
                isolated(true, &firstNode, &secondNode,
                         RenderScope::WorldBillboard, producer) ||
                isolated(true, &firstNode, &secondNode,
                         RenderScope::ScreenHud, ProducerToken::None))
                return 65;
        }
        // Only a previously tagged GOAL owner may request this boundary;
        // never expand to stage +TIME, pause UI, DispRank, F11 or SkyGlow.
        for (const auto foreign : {
                ProducerToken::StageExtensionTime,
                ProducerToken::PauseOptionArrow,
                ProducerToken::DispRankClipSprite,
                ProducerToken::None}) {
            if (CanIsolateD3DXGoalQueueNodeTransition(
                    true, &firstNode, &secondNode,
                    RenderScope::ScreenHud, foreign,
                    RenderScope::ScreenHud, foreign))
                return 66;
        }
        if (CanIsolateD3DXGoalQueueNodeTransition(
                true, &firstNode, &secondNode,
                RenderScope::ScreenHud, ProducerToken::GoalTime020,
                RenderScope::ScreenHud, ProducerToken::GoalTime150))
            return 67;
    }

    const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    float x=0,y=0;
    if(!ProjectPixel(identity,320,240,0,0,640,480,1,x,y) ||
       !Near(x,320)||!Near(y,240))return 1;
    const float left[16]={1,0,0,0,0,1,0,0,0,0,1,0,-0.04f,0,0,1};
    const float right[16]={1,0,0,0,0,1,0,0,0,0,1,0,0.04f,0,0,1};
    float lx=0,ly=0,rx=0,ry=0;
    if(!ProjectPixel(left,320,240,0,0,640,480,1,lx,ly)||
       !ProjectPixel(right,320,240,0,0,640,480,1,rx,ry)||
       !(lx<320&&rx>320&&Near(ly,ry)))return 2;
    float offsets[2][3]{{100.f-0.032f,2,5},{100.f+0.032f,2,5}};
    const float cant=0.12f;
    const float canted[2][4]{{0,-std::sin(cant),0,std::cos(cant)},
                             {0, std::sin(cant),0,std::cos(cant)}};
    float ipd[2][3]{},quats[2][4]{};
    if(!BuildStageEyePoses(offsets,canted,1.f,ipd,quats))return 3;
    if(!Near(ipd[0][0],-0.032f,1e-3f)||
       !Near(ipd[1][0],0.032f,1e-3f)||
       !Near(quats[0][1],-std::sin(cant))||
       !Near(quats[1][1], std::sin(cant)))return 4;
    const float parallel[2][4]{{0,0,0,1},{0,0,0,1}};
    if(!BuildStageEyePoses(offsets,parallel,1.f,ipd,quats)||
       !Near(quats[0][3],1)||!Near(quats[1][3],1))return 5;
    for(auto& eye:ipd)for(float& v:eye)v=17;
    for(auto& eye:quats)for(float& v:eye)v=19;
    const float invalid[2][4]{{0,0,0,1},{0,0,0,0}};
    if(BuildStageEyePoses(offsets,invalid,1.f,ipd,quats)||
       BuildStageEyePoses(offsets,canted,0.f,ipd,quats)||
       BuildStageEyePoses(offsets,canted,
           std::numeric_limits<float>::infinity(),ipd,quats))return 6;
    for(const auto& eye:ipd)for(float v:eye)if(v!=17)return 7;
    for(const auto& eye:quats)for(float v:eye)if(v!=19)return 8;
    offsets[0][0]=std::numeric_limits<float>::quiet_NaN();
    if(BuildStageEyePoses(offsets,canted,1.f,ipd,quats))return 9;
    if(ProjectPixel(identity,0,0,0,0,0,480,1,x,y))return 10;
    const float zero[16]{};
    if(ProjectPixel(zero,320,240,0,0,640,480,1,x,y)||
       ProjectPixel(identity,
          std::numeric_limits<float>::quiet_NaN(),240,
          0,0,640,480,1,x,y)||
       ProjectPixel(identity,320,240,0,0,640,480,-1,x,y))return 11;

    // The original independent-eye GPU route is the reference for full
    // +TIME sprites, numeric glyphs and GOAL 0-99/result quads. The fused
    // source-NDC route must agree at the centre and all viewport edges,
    // including changing desktop size, HUD scale and per-eye cant/skew.
    using OutRunVR::StageExtensionPlane::ProjectPixelPair;
    float matrixL[16]{1,0,0,0.045f, 0,1,0,-0.02f,
                      0,0,1,0, -0.035f,0.01f,0,1};
    float matrixR[16]{1,0,0,-0.03f, 0,1,0,0.015f,
                      0,0,1,0, 0.04f,-0.015f,0,1};
    const float viewports[][2]{{640.f,480.f},{1920.f,1080.f},
                               {3440.f,1440.f},{720.f,1280.f}};
    for (float scale : {0.30f, 0.55f, 1.0f, 1.20f}) {
        for (const auto& dims : viewports) {
            for (float fx : {0.f,0.25f,0.5f,0.75f,1.f}) {
                for (float fy : {0.f,0.3f,0.5f,1.f}) {
                    const float sx=73.f+fx*dims[0], sy=41.f+fy*dims[1];
                    float lrx=0,lry=0,rrx=0,rry=0;
                    float flx=0,fly=0,frx=0,fry=0;
                    if (!ProjectPixel(matrixL,sx,sy,73,41,dims[0],dims[1],
                                      scale,lrx,lry) ||
                        !ProjectPixel(matrixR,sx,sy,73,41,dims[0],dims[1],
                                      scale,rrx,rry) ||
                        !ProjectPixelPair(matrixL,matrixR,sx,sy,73,41,
                                          dims[0],dims[1],scale,
                                          flx,fly,frx,fry) ||
                        !Near(flx,lrx,0.002f) || !Near(fly,lry,0.002f) ||
                        !Near(frx,rrx,0.002f) || !Near(fry,rry,0.002f))
                        return 12;
                }
            }
        }
    }
    // Reject malformed RIGHT-only projection without changing either
    // earlier published eye; also reject invalid screen inputs and scale.
    float badRight[16]{};
    float oldLx=17,oldLy=19,oldRx=23,oldRy=29;
    if (ProjectPixelPair(matrixL,badRight,320,240,0,0,640,480,
                         0.55f,oldLx,oldLy,oldRx,oldRy) ||
        ProjectPixelPair(matrixL,nullptr,320,240,0,0,640,480,
                         0.55f,oldLx,oldLy,oldRx,oldRy) ||
        ProjectPixelPair(matrixL,matrixR,320,240,0,0,0,480,
                         0.55f,oldLx,oldLy,oldRx,oldRy) ||
        ProjectPixelPair(matrixL,matrixR,320,240,0,0,640,480,
                         -1.f,oldLx,oldLy,oldRx,oldRy) ||
        oldLx!=17 || oldLy!=19 || oldRx!=23 || oldRy!=29)
        return 13;
    // Original 2D +TIME sprite and numeric glyphs retain the SAME
    // source ray when game output is 3440x1440 but R84 RT is 2496x2688.
    using OutRunVR::StageExtensionPlane::ProjectPixelPairAcrossViewports;
    {
        const float eL[16]{1,0,0,0,0,1,0,0,0,0,1,0,-0.04f,0,0,1};
        const float eR[16]{1,0,0,0,0,1,0,0,0,0,1,0,0.04f,0,0,1};
        float a=0,b=0,c=0,d=0;
        if (!ProjectPixelPairAcrossViewports(eL,eR,1720,720,
                0,0,3440,1440,0,0,2496,2688,1,a,b,c,d) ||
            !Near(a,1198.08f,.01f) || !Near(c,1297.92f,.01f) ||
            !Near(b,1344.f) || !Near(d,1344.f))
            return 46;
        if (!ProjectPixelPairAcrossViewports(eL,eR,1720,720,
                0,0,3440,1440,73,41,2496,2688,.55f,a,b,c,d) ||
            !Near(a,73.f+1198.08f,.01f) ||
            !Near(c,73.f+1297.92f,.01f) ||
            !Near(b,1385.f) || !Near(d,1385.f))
            return 47;
        const float oldA=a,oldB=b,oldC=c,oldD=d;
        const float bad[16]{};
        if (ProjectPixelPairAcrossViewports(eL,bad,1720,720,
                0,0,3440,1440,0,0,2496,2688,1,a,b,c,d) ||
            ProjectPixelPairAcrossViewports(eL,eR,1720,720,
                0,0,0,1440,0,0,2496,2688,1,a,b,c,d) ||
            ProjectPixelPairAcrossViewports(eL,eR,1720,720,
                0,0,3440,1440,0,0,0,2688,1,a,b,c,d) ||
            !Near(a,oldA) || !Near(b,oldB) ||
            !Near(c,oldC) || !Near(d,oldD))
            return 48;
        float la=0,lb=0,ra=0,rb=0;
        if (!ProjectPixelPair(eL,eR,320,240,0,0,640,480,.55f,
                la,lb,ra,rb) ||
            !ProjectPixelPairAcrossViewports(eL,eR,320,240,
                0,0,640,480,0,0,640,480,.55f,a,b,c,d) ||
            !Near(a,la) || !Near(b,lb) || !Near(c,ra) || !Near(d,rb))
            return 49;
    }
    // Physical eye size MUST NOT become the coordinate source for the
    // original gameplay speed/time/position and rank HUD. The +TIME/GOAL
    // path already uses this adapter: source-proven ordinary HUD now shares
    // it. Preserve both eye offsets, game centre, edge and source aspect.
    {
        const float eyeIdentity[16]{
            1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};
        float a=0,b=0,c=0,d=0;
        float wrongX=0,wrongY=0,wrongRx=0,wrongRy=0;
        if (!ProjectPixelPairAcrossViewports(
                eyeIdentity,eyeIdentity,320,240,
                0,0,640,480,0,0,2496,2688,1,a,b,c,d) ||
            !Near(a,1248.f)||!Near(b,1344.f)||
            !Near(c,1248.f)||!Near(d,1344.f) ||
            !ProjectPixelPair(eyeIdentity,eyeIdentity,320,240,
                0,0,2496,2688,1,wrongX,wrongY,wrongRx,wrongRy) ||
            !(wrongX<600.f&&wrongY<600.f))
            return 50;
        if (!ProjectPixelPairAcrossViewports(
                eyeIdentity,eyeIdentity,80,120,
                0,0,640,480,0,0,2496,2688,1,a,b,c,d) ||
            !Near(a,312.f)||!Near(b,672.f)||
            !Near(c,312.f)||!Near(d,672.f))
            return 51;
        // With a matching game/RT extent there is no extra adjustment.
        float oldLx=0,oldLy=0,oldRx=0,oldRy=0;
        if (!ProjectPixelPair(eyeIdentity,eyeIdentity,80,120,
                0,0,640,480,.55f,oldLx,oldLy,oldRx,oldRy) ||
            !ProjectPixelPairAcrossViewports(
                eyeIdentity,eyeIdentity,80,120,
                0,0,640,480,0,0,640,480,.55f,a,b,c,d) ||
            !Near(a,oldLx)||!Near(b,oldLy)||
            !Near(c,oldRx)||!Near(d,oldRy))
            return 52;
    }
    // R84 paused ESC shell (queued ScreenOverlay2D) and exact option
    // arrows (ScreenHud) share one optical plane but use the independent
    // pause slider/offset. The +TIME/GOAL path supplies zero shift.
    using OutRunVR::StageExtensionPlane::ApplyPostEyeVerticalShiftPair;
    float pauseLeftY=240.f, pauseRightY=250.f;
    if(!ApplyPostEyeVerticalShiftPair(48.f,pauseLeftY,pauseRightY)||
       !Near(pauseLeftY,288.f)||!Near(pauseRightY,298.f))
        return 14;
    // Negative pause offset and independent optical scale also preserve
    // pre-projection bilateral geometry (only post-eye Y is translated).
    if(!ApplyPostEyeVerticalShiftPair(-24.f,pauseLeftY,pauseRightY)||
       !Near(pauseLeftY,264.f)||!Near(pauseRightY,274.f))
        return 15;
    if(!ApplyPostEyeVerticalShiftPair(0.f,pauseLeftY,pauseRightY)||
       !Near(pauseLeftY,264.f)||!Near(pauseRightY,274.f))
        return 16;
    float invalidShiftLeft=11.f, invalidShiftRight=13.f;
    if(ApplyPostEyeVerticalShiftPair(
           std::numeric_limits<float>::infinity(),
           invalidShiftLeft,invalidShiftRight) ||
       invalidShiftLeft!=11.f || invalidShiftRight!=13.f)
        return 17;
    invalidShiftLeft=std::numeric_limits<float>::max();
    invalidShiftRight=13.f;
    if(ApplyPostEyeVerticalShiftPair(
           std::numeric_limits<float>::max(),
           invalidShiftLeft,invalidShiftRight) ||
       invalidShiftLeft!=std::numeric_limits<float>::max() ||
       invalidShiftRight!=13.f)
        return 18;
    // Distinct eye projections retain parallax; pause translation affects
    // only post-eye pixel Y by the same signed viewport fraction.
    float pauseLx=0.f,pauseLy=0.f,pauseRx=0.f,pauseRy=0.f;
    if(!ProjectPixelPair(matrixL,matrixR,320,240,0,0,640,480,
                         0.85f,pauseLx,pauseLy,pauseRx,pauseRy))
        return 19;
    const float originalPauseLy=pauseLy, originalPauseRy=pauseRy;
    if(!ApplyPostEyeVerticalShiftPair(48.f,pauseLy,pauseRy) ||
       !(pauseLx<pauseRx) ||
       !Near(pauseLy,originalPauseLy+48.f,0.002f) ||
       !Near(pauseRy,originalPauseRy+48.f,0.002f))
        return 19;

    // GPU SUBMISSION rather than CPU D3DX Draw registration is the real
    // +TIME ownership boundary. Both direct numeric and queued sprite
    // paths must keep the same source through a reentrant native left Draw.
    using namespace OutRunVR::StageExtensionPhysical;
    using OutRunVR::GameSemantic::RenderScope;
    using OutRunVR::GameSemantic::ProducerToken;
    const int stageNode = 1, foreignNode = 2;
    Source queuedStage{RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime, true, &stageNode, 41,
        23, 9, 0, 0}; // FVF 0x142 fixed-function: null VS is legitimate.
    Source directStage{RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime, false, nullptr, 0,
        23, 9, 0x1234, 11}; // Original numeric shader glyphs.
    if (!SameAfterNativeLeft(queuedStage, queuedStage) ||
        !SameAfterNativeLeft(directStage, directStage))
        return 20;
    auto reject = [](const Source& original, const Source& changed) {
        return !SameAfterNativeLeft(original, changed);
    };
    auto altered = queuedStage;
    altered.node = &foreignNode; if (!reject(queuedStage,altered)) return 21;
    altered = queuedStage; ++altered.queueEpoch;
    if (!reject(queuedStage,altered)) return 22;
    altered = queuedStage; altered.queued = false;
    if (!reject(queuedStage,altered)) return 23;
    altered = queuedStage; altered.producer = ProducerToken::GoalTime020;
    if (!reject(queuedStage,altered)) return 24;
    altered = queuedStage; altered.scope = RenderScope::ScreenOverlay2D;
    if (!reject(queuedStage,altered)) return 25;
    altered = queuedStage; altered.poseEpoch = 0;
    if (!reject(queuedStage,altered)) return 26;
    altered = queuedStage; ++altered.topLevelDrawSerial;
    if (!reject(queuedStage,altered)) return 27;
    altered = queuedStage; altered.shader = 0x2345;
    if (!reject(queuedStage,altered)) return 28;
    altered = directStage; ++altered.shaderEpoch;
    if (!reject(directStage,altered)) return 29;
    altered = directStage; altered.shaderEpoch = 0;
    if (!reject(directStage,altered)) return 30;
    altered = directStage; altered.node = &stageNode;
    if (!reject(directStage,altered)) return 31;
    altered = directStage; altered.queueEpoch = 1;
    if (!reject(directStage,altered)) return 32;
    altered = directStage; altered.queued = true;
    if (!reject(directStage,altered)) return 33;
    altered = directStage; altered.scope = RenderScope::WorldBillboard;
    if (!reject(directStage,altered)) return 34;
    altered = directStage; altered.producer = ProducerToken::None;
    if (!reject(directStage,altered)) return 35;
    altered = queuedStage; altered.poseEpoch = 24;
    if (!reject(queuedStage,altered)) return 36;
    // R84 shader/c64 +TIME has a separate physical owner from GOAL,
    // even when a native callback reenters a second numeric glyph or
    // queued sprite with the same ScreenHud classification.
    Source shaderStage{RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime, false, nullptr, 0,
        127, 991, 0x1234, 14};
    if (!SameAfterNativeLeft(shaderStage, shaderStage))
        return 38;
    auto duringLeft = shaderStage;
    ++duringLeft.topLevelDrawSerial;
    if (SameAfterNativeLeft(shaderStage, duringLeft))
        return 39;
    duringLeft = shaderStage;
    ++duringLeft.shaderEpoch;
    if (SameAfterNativeLeft(shaderStage, duringLeft))
        return 40;
    duringLeft = shaderStage;
    duringLeft.producer = ProducerToken::ResultProgress;
    if (SameAfterNativeLeft(shaderStage, duringLeft))
        return 41;
    duringLeft = shaderStage;
    duringLeft.queued = true;
    duringLeft.node = &stageNode;
    duringLeft.queueEpoch = 42;
    if (SameAfterNativeLeft(shaderStage, duringLeft))
        return 42;
    duringLeft = shaderStage;
    ++duringLeft.poseEpoch;
    if (SameAfterNativeLeft(shaderStage, duringLeft))
        return 43;
    // Fixedfn/null-VS queued sprites remain eligible but a newly selected
    // R84 shader or queue node may never borrow their prepared right eye.
    if (!SameAfterNativeLeft(queuedStage, queuedStage))
        return 44;
    duringLeft = queuedStage;
    duringLeft.shader = 0x1234;
    duringLeft.shaderEpoch = 14;
    if (SameAfterNativeLeft(queuedStage, duringLeft))
        return 45;
    // Native LEFT +TIME can reenter another original game c64 writer
    // without changing shader, queue, producer or frame-pose identity.
    // Both queued stage sprites and direct numeric D3DX glyphs must
    // reject that GPU source change before submitting RIGHT.
    auto stampedQueued = queuedStage;
    stampedQueued.rawWvpWriteSerial = 711;
    stampedQueued.rawWvpDrawSerial = 99;
    auto stampedDirect = directStage;
    stampedDirect.rawWvpWriteSerial = 712;
    stampedDirect.rawWvpDrawSerial = 100;
    if (!SameAfterNativeLeft(stampedQueued, stampedQueued) ||
        !SameAfterNativeLeft(stampedDirect, stampedDirect))
        return 69;
    altered = stampedQueued; ++altered.rawWvpWriteSerial;
    if (SameAfterNativeLeft(stampedQueued, altered)) return 70;
    altered = stampedDirect; ++altered.rawWvpDrawSerial;
    if (SameAfterNativeLeft(stampedDirect, altered)) return 71;
    altered = stampedQueued; altered.rawWvpWriteSerial = 0;
    if (SameAfterNativeLeft(stampedQueued, altered)) return 72;
    altered = stampedDirect; altered.rawWvpDrawSerial = 0;
    if (SameAfterNativeLeft(stampedDirect, altered)) return 73;
    // Missing raw-WVP telemetry must retain the legacy stage eligibility;
    // a partly present pair is invalid (not evidence for physical stereo).
    if (!IsValid(queuedStage) || !IsValid(directStage))
        return 74;
    auto unpaired = stampedQueued;
    unpaired.rawWvpDrawSerial = 0;
    if (IsValid(unpaired)) return 75;
    // Test the LAST owner fence too. A right-eye RT/viewport/c64 setter
    // can reenter another game call after an already valid left submission.
    for (const Source& before : {stampedQueued, stampedDirect}) {
        Source afterLeft = before;
        Source beforeRight = before;
        if (!SameAfterNativeLeft(before, afterLeft) ||
            !SameAfterNativeLeft(before, beforeRight))
            return 76;
        ++beforeRight.rawWvpWriteSerial;
        if (SameAfterNativeLeft(before, beforeRight))
            return 77; // original game c64 changed during right setters
        beforeRight = before;
        ++beforeRight.poseEpoch;
        if (SameAfterNativeLeft(before, beforeRight))
            return 78; // recenter after left
        beforeRight = before;
        ++beforeRight.topLevelDrawSerial;
        if (SameAfterNativeLeft(before, beforeRight))
            return 79; // foreign nested draw
        beforeRight = before;
        beforeRight.producer = ProducerToken::ResultProgress;
        if (SameAfterNativeLeft(before, beforeRight))
            return 80; // GOAL cannot become stage
        if (before.queued) {
            beforeRight = before;
            ++beforeRight.queueEpoch;
            if (SameAfterNativeLeft(before, beforeRight))
                return 81; // recycled SpriteNode in a new queue epoch
        }
    }

    // Original HUD/GOAL/rival/SkyGlow and untagged native draws are
    // never admitted by this exact stage-only transaction.
    if (IsValid(Source{}) ||
        IsValid(Source{RenderScope::ScreenHud,
            ProducerToken::ResultProgress, false, nullptr, 0, 23, 9, 0, 0}))
        return 37;
    return 0;
}
