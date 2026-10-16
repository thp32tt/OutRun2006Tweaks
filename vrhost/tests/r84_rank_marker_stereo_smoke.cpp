// c++ -std=c++17 vrhost/tests/r84_rank_marker_stereo_smoke.cpp -o rank_smoke && ./rank_smoke
#include "../../src/vr/game/projected_rank_stereo.hpp"
#include <cassert>
#include <cmath>
#include <limits>
using OutRunVR::RankMarker::StereoNdcShift;
using OutRunVR::RankMarker::RemapScreenPoint;
static bool eq(float a,float b) { return std::fabs(a-b)<0.001f; }

#include "../../src/vr/game/rank_marker_sparse.hpp"
#include "../../src/vr/game/rank_marker_raw_wvp.hpp"
#include <vector>
// A sparse VB/IB list must produce the same referenced rank sprite positions
// as a dense scan. Invalid masks, reset/unknown decoders and nonindexed
// sprite batches must retain the original two-full-copy fallback.
static void CheckSparseRankCopyPlan()
{
    using OutRunVR::RankMarker::PlanSparseRankVertices;
    std::vector<std::uint8_t> mask(1024u);
    std::vector<std::uint32_t> touched{900u, 8u, 640u, 20u, 310u};
    for (auto index : touched) mask[index] = 1u;
    auto p = PlanSparseRankVertices(1024, &mask, &touched, touched.size());
    assert(p.enabled && p.referenced == touched.size());

    StereoNdcShift shift{};
    shift.baseX = -0.4f;
    shift.baseY = 0.5f;
    shift.deltaX[0] = -0.05f;
    shift.deltaX[1] = 0.05f;
    shift.deltaY[0] = 0.01f;
    shift.deltaY[1] = -0.01f;
    std::vector<float> x(1024u, 100.0f), y(1024u, 200.0f);
    float denseX[2][5]{}, denseY[2][5]{}, sparseX[2][5]{}, sparseY[2][5]{};
    for (int eye = 0; eye < 2; ++eye)
    {
        for (std::size_t k = 0; k < touched.size(); ++k)
        {
            const auto i = touched[k];
            assert(RemapScreenPoint(x[i], y[i], 0, 0, 640, 480, 0.55f,
                shift, eye, denseX[eye][k], denseY[eye][k]));
        }
        for (std::size_t k = 0; k < p.referenced; ++k)
        {
            const auto i = touched[k];
            assert(RemapScreenPoint(x[i], y[i], 0, 0, 640, 480, 0.55f,
                shift, eye, sparseX[eye][k], sparseY[eye][k]));
            assert(eq(denseX[eye][k], sparseX[eye][k]));
            assert(eq(denseY[eye][k], sparseY[eye][k]));
        }
    }
    assert(!PlanSparseRankVertices(1024, &mask, &touched, 4).enabled);
    assert(!PlanSparseRankVertices(1024, &mask, nullptr, 5).enabled);
    assert(!PlanSparseRankVertices(1024, nullptr, &touched, 5).enabled);
    assert(!PlanSparseRankVertices(32, &mask, &touched, 5).enabled);
    auto corrupt = touched;
    corrupt[1] = 1024;
    assert(!PlanSparseRankVertices(1024, &mask, &corrupt, 5).enabled);
    corrupt[1] = 42;
    assert(!PlanSparseRankVertices(1024, &mask, &corrupt, 5).enabled);
    std::vector<std::uint32_t> dense(300);
    for (std::uint32_t i = 0; i < dense.size(); ++i) dense[i] = i;
    std::vector<std::uint8_t> denseMask(1024, 1);
    assert(!PlanSparseRankVertices(
        1024, &denseMask, &dense, dense.size()).enabled);
}

int main()
{
    CheckSparseRankCopyPlan();
    using OutRunVR::RankMarker::OwnsRawGameWvp;
    using OutRunVR::RankMarker::RawWvpEvidence;
    const RawWvpEvidence owned{13,13,180,178,0x1234,0x1234,9,9,true,true,true};
    assert(OwnsRawGameWvp(owned));
    auto rejected = owned;
    rejected.sameQueueOwner = false; assert(!OwnsRawGameWvp(rejected));
    rejected = owned; rejected.exactUploadedRank = false; assert(!OwnsRawGameWvp(rejected));
    rejected = owned; rejected.writtenPose = 12; assert(!OwnsRawGameWvp(rejected));
    rejected = owned; rejected.writtenShaderEpoch = 8; assert(!OwnsRawGameWvp(rejected));
    rejected = owned; rejected.writtenDraw = 180; assert(!OwnsRawGameWvp(rejected));
    rejected = owned; rejected.nextDraw = 193; assert(!OwnsRawGameWvp(rejected));
    StereoNdcShift s{};
    s.baseX=0.25f; s.baseY=-0.2f;
    s.deltaX[0]=-0.06f; s.deltaX[1]=0.06f;
    s.deltaY[0]=0.03f; s.deltaY[1]=-0.03f;
    float lx=0,ly=0,rx=0,ry=0;
    assert(RemapScreenPoint(400,200,0,0,640,480,1,s,0,lx,ly));
    assert(RemapScreenPoint(400,200,0,0,640,480,1,s,1,rx,ry));
    assert(eq(lx,380.8f) && eq(rx,419.2f));
    assert(eq(ly,192.8f) && eq(ry,207.2f));
    float cx=0,cy=0;
    assert(RemapScreenPoint(418,208,0,0,640,480,1,s,0,cx,cy));
    assert(eq(cx-lx,18) && eq(cy-ly,8));
    assert(RemapScreenPoint(400,200,0,0,640,480,0.5f,s,0,cx,cy));
    assert(eq(cx,380.8f));
    assert(!RemapScreenPoint(400,200,0,0,640,480,1,s,2,lx,ly));
    assert(!RemapScreenPoint(400,200,0,0,0,480,1,s,0,lx,ly));
    assert(!RemapScreenPoint(std::numeric_limits<float>::quiet_NaN(),
        200,0,0,640,480,1,s,0,lx,ly));
    s.deltaY[1]=std::numeric_limits<float>::quiet_NaN();
    assert(!RemapScreenPoint(400,200,0,0,640,480,1,s,1,rx,ry));
    assert(RemapScreenPoint(400,200,0,0,640,480,1,s,0,lx,ly));
}
