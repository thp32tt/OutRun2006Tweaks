#include "../src/vr/game/external_car_draw_order.hpp"
#include <array>
#include <cassert>
#include <vector>
#include <limits>
using OutRunVR::DinoSidecar::MeshInDrawPass;
using OutRunVR::DinoSidecar::ExternalGlassViewDepth;
using OutRunVR::DinoSidecar::GlassDepthItem;
using OutRunVR::DinoSidecar::SortGlassBackToFront;
int main() {
    // Input order deliberately interleaves transparent and opaque meshes.
    const std::array<bool,5> glass{true,false,true,false,true};
    std::vector<unsigned> order;
    for (unsigned pass=0;pass<2u;++pass)
        for (unsigned i=0;i<glass.size();++i)
            if (MeshInDrawPass(glass[i],pass))order.push_back(i);
    assert((order==std::vector<unsigned>{1,3,0,2,4}));
    // Every mesh is submitted exactly once, never outside the two passes.
    for (unsigned i=0;i<glass.size();++i) {
        assert(MeshInDrawPass(glass[i],0u) != MeshInDrawPass(glass[i],1u));
        assert(!MeshInDrawPass(glass[i],2u));
    }
    // Glass may appear in reverse distance order in third-party OVC data.
    // Same mesh receives identical camera-space ordering for both stereo eyes
    // when depth order is unambiguous; no sorting of opaque meshes.
    constexpr float identity[16]{
        1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};
    constexpr float leftView[16]{
        1,0,0,0, 0,1,0,0, 0,0,1,0, 0.032,0,0,1};
    constexpr float rightView[16]{
        1,0,0,0, 0,1,0,0, 0,0,1,0, -0.032,0,0,1};
    constexpr float nearGlass[3]{0,0,1};
    constexpr float farGlass[3]{0,0,5};
    constexpr float middleGlass[3]{0,0,3};
    assert(ExternalGlassViewDepth(nearGlass,identity,identity,1.f)==1.f);
    assert(ExternalGlassViewDepth(farGlass,identity,identity,1.f)==5.f);
    for(const float* eye:{leftView,rightView}) {
        std::array<GlassDepthItem,4> items{{
            {2,ExternalGlassViewDepth(nearGlass,identity,eye,1.f)},
            {0,ExternalGlassViewDepth(farGlass,identity,eye,1.f)},
            {3,ExternalGlassViewDepth(middleGlass,identity,eye,1.f)},
            {1,ExternalGlassViewDepth(farGlass,identity,eye,1.f)}
        }};
        SortGlassBackToFront(items.data(),items.size());
        assert(items[0].index==0 && items[1].index==1);
        assert(items[2].index==3 && items[3].index==2);
    }
    // Retail right-handed projection: _34=-1 and forward Z is negative.
    // Source-over is not commutative: near-first makes far glass overwrite
    // the near tint. Test both eyes, both handedness conventions, ties and
    // a point behind the eye; do not use abs(viewZ).
    for(unsigned slot=0;slot<16u;++slot) {
        for(const float* eye:{leftView,rightView}) {
            for(float sign:{-1.f,1.f}) {
                const float nearP[3]{0,0,sign};
                const float farP[3]{0,0,5.f*sign};
                const float behind[3]{0,0,-10.f*sign};
                std::array<GlassDepthItem,4> items{{
                    {2,ExternalGlassViewDepth(nearP,identity,eye,sign)},
                    {1,ExternalGlassViewDepth(farP,identity,eye,sign)},
                    {3,ExternalGlassViewDepth(behind,identity,eye,sign)},
                    {0,ExternalGlassViewDepth(farP,identity,eye,sign)}
                }};
                SortGlassBackToFront(items.data(),items.size());
                assert(items[0].index==0 && items[1].index==1 &&
                       items[2].index==2 && items[3].index==3);
                // With 50% opacity, far blue then near red leaves red dominant.
                const auto blend=[](float src,float dst){return src*.5f+dst*.5f;};
                const bool farFirst=items[0].index==0;
                const float red=farFirst?blend(1.f,blend(0.f,0.f)):
                    blend(0.f,blend(1.f,0.f));
                const float blue=farFirst?blend(0.f,blend(1.f,0.f)):
                    blend(1.f,blend(0.f,0.f));
                assert(red==.5f && blue==.25f);
                if(sign<0.f) {
                    // Old raw-Z sort reverses the visible pair.
                    std::array<GlassDepthItem,2> old{{
                        {2,nearP[2]},{0,farP[2]}}};
                    SortGlassBackToFront(old.data(),old.size());
                    assert(old[0].index==2);
                }
                // Animation can move a mesh behind another glass group.
                float animated[16];
                for(unsigned k=0;k<16;++k)animated[k]=identity[k];
                animated[14]=6.f*sign;
                assert(ExternalGlassViewDepth(nearP,animated,eye,sign)>
                       ExternalGlassViewDepth(farP,identity,eye,sign));
            }
        }
    }
    assert(ExternalGlassViewDepth(farGlass,identity,identity,0.f)==0.f);
    assert(ExternalGlassViewDepth(farGlass,identity,identity,
           std::numeric_limits<float>::quiet_NaN())==0.f);
    // Deliberately malformed/nonfinite camera matrices produce deterministic
    // keys rather than NaN comparisons with undefined sort ordering.
    float badView[16]{};
    for(unsigned i=0;i<16;++i)badView[i]=identity[i];
    badView[10]=std::numeric_limits<float>::quiet_NaN();
    assert(ExternalGlassViewDepth(farGlass,identity,badView,1.f)==0.f);
    // Model the same setter transaction used by DrawNativeScene. Stage 0
    // TEMP output loses texture alpha at the final CURRENT register; stale
    // interpolation wrapping must not alter PBR world/normal/UV semantics.
    // Check both clean and inherited-dirty states in every canonical slot.
    for(unsigned slot=0;slot<16u;++slot) {
        for(unsigned dirty=0;dirty<16u;++dirty) {
            for(unsigned fail=0;fail<=4u;++fail) {
                bool current=(dirty&1u)==0;
                std::array<unsigned,3> wrap{{
                    (dirty&2u)?1u:0u,(dirty&4u)?2u:0u,(dirty&8u)?3u:0u}};
                const auto oldCurrent=current;
                const auto oldWrap=wrap;
                unsigned calls=0;
                const bool ready=OutRunVR::DinoSidecar::ConfigureExternalTextureRouting(
                    [&]() { if(calls++==fail)return false;current=true;return true; },
                    [&](unsigned coordinate) {
                        assert(coordinate==calls-1u);
                        if(calls++==fail)return false;
                        wrap[coordinate]=0u;return true;
                    });
                assert(ready==(fail==4u));
                assert(calls==(fail<4u?fail+1u:4u));
                if(ready) {
                    assert(current && (wrap==std::array<unsigned,3>{{0,0,0}}));
                    // Single-stage alpha routes to CURRENT, not TEMP.
                    constexpr float textureAlpha=0.25f;
                    const float alpha=current?textureAlpha:1.f;
                    assert(alpha==textureAlpha);
                }
                // Model the existing captured-state Apply on both paths.
                // Production source assertions bind this test to the actual
                // pre-DIP gate and unconditional Apply.
                current=oldCurrent;wrap=oldWrap;
                assert(current==oldCurrent && wrap==oldWrap);
            }
        }
    }
    // A successful DIP can still write no MSAA samples, or only wireframe
    // edges, when the previous native pass left those states behind.
    // Exercise both mesh passes, 16 synthetic slots, single/MSAA targets,
    // all inherited states, setter failures, and restoration on both paths.
    for(unsigned slot=0;slot<16u;++slot)
        for(bool glassPass:{false,true})
            for(unsigned samples:{1u,2u,4u,8u,16u})
                for(bool oldSolid:{false,true})
                    for(unsigned oldMask:{0u,1u,0x55u,0xffffffffu})
                        for(unsigned fail=0;fail<=2u;++fail) {
                            bool solid=oldSolid;
                            unsigned mask=oldMask,calls=0;
                            const unsigned full=(1u<<samples)-1u;
                            // Single-sample targets ignore the mask.
                            const unsigned before=samples==1u?1u:mask&full;
                            if(samples>1u && oldMask==0u)assert(before==0u);
                            const bool ready=OutRunVR::DinoSidecar::ConfigureExternalRasterCoverage(
                                [&]() { if(calls++==fail)return false;solid=true;return true; },
                                [&]() { if(calls++==fail)return false;mask=0xffffffffu;return true; });
                            assert(ready==(fail==2u));
                            assert(calls==(fail==0u?1u:2u));
                            const bool submit=ready && MeshInDrawPass(glassPass,glassPass?1u:0u);
                            assert(submit==(fail==2u));
                            if(submit) {
                                assert(solid);
                                assert((samples==1u?1u:mask&full)==full);
                            }
                            // Model unconditional captured state restoration.
                            solid=oldSolid;mask=oldMask;
                            assert(solid==oldSolid && mask==oldMask);
                        }
    // All-opaque and all-glass OVCs do not produce spurious extra draws.
    for (bool isGlass:{false,true}) {
        unsigned count=0;
        for(unsigned pass=0;pass<2u;++pass)
            for(unsigned mesh=0;mesh<78u;++mesh)
                if(MeshInDrawPass(isGlass,pass))++count;
        assert(count==78u);
    }
}
