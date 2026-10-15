#include "../../src/vr/d3d9/hud_edge_transition.hpp"
#include <cmath>
#include <iostream>
#include <limits>
#include <initializer_list>

static bool Near(float a, float b, float tol=0.0001f) { return std::fabs(a-b)<=tol; }
int main()
{
    using namespace OutRunVrHudEdge;
    for (float aspect : {4.0f/3.0f, 16.0f/9.0f, 21.0f/9.0f})
    {
        float previous=PeripheralAnchor(0.20f,0.82f), previousBoost=1.0f;
        for(int i=201;i<=700;++i)
        {
            const float ndc=i/1000.0f;
            const float anchor=PeripheralAnchor(ndc,0.82f);
            const float boost=BlendBoost(1.0f,0.90f/0.55f,PeripheralWeight(ndc));
            if(anchor<previous || anchor-previous>0.004f ||
                boost<previousBoost || boost-previousBoost>0.007f) return 1;
            previous=anchor; previousBoost=boost;
        }
        // Both eyes share source geometry; per-eye FOV is still applied later.
        if(!Near(PeripheralAnchor(.72f,.82f)*aspect,
                 PeripheralAnchor(.72f,.82f)*aspect)) return 2;
    }
    // A HUD glyph returning past the 1.0 NDC source edge must ease back to
    // its neutral anchor and size, not snap at the historical 1.20 cutoff.
    for (int side : {-1, 1})
    {
        float lastWeight = 1.0f;
        float lastAnchor = .82f;
        for (int i = 1000; i <= 1200; ++i)
        {
            const float ndc = side * (i / 1000.0f);
            const float weight = PeripheralWeight(ndc);
            const float anchor = std::fabs(PeripheralAnchor(ndc, .82f));
            if (weight > lastWeight + 0.00001f || weight < 0.0f ||
                lastWeight - weight > 0.008f || anchor > lastAnchor + 0.00001f ||
                lastAnchor - anchor > 0.007f)
                return 11;
            lastWeight = weight;
            lastAnchor = anchor;
        }
        if (!Near(lastWeight, 0.f) || !Near(lastAnchor, 0.f))
            return 12;
    }
    if(!Near(PeripheralWeight(1.0f),1.f) ||
       !Near(PeripheralWeight(1.10f),.5f) ||
       !Near(PeripheralWeight(1.20f),0.f) ||
       !Near(PeripheralWeight(1.201f),0.f) ||
       !Near(PeripheralWeight(-1.10f),.5f)) return 13;
    if(!Near(PeripheralAnchor(-.70f,.82f),-PeripheralAnchor(.70f,.82f))) return 3;
    if(!Near(PeripheralWeight(.35f),0.f) || !Near(PeripheralWeight(.60f),1.f) ||
       !Near(PeripheralWeight(.475f),.5f)) return 4;
    if(!Near(PeripheralAnchor(.70f,.78f),.70f) ||
       !Near(PeripheralAnchor(.95f,.82f),.82f)) return 5;
    const float nan=std::numeric_limits<float>::quiet_NaN();
    if(!Near(PeripheralAnchor(.1f,.82f),0.f) ||
       !Near(PeripheralAnchor(nan,.82f),0.f) ||
       !Near(PeripheralAnchor(.7f,nan),0.f) ||
       !Near(PeripheralWeight(1.25f),0.f) ||
       !Near(BlendBoost(1.f,2.f,nan),1.f)) return 6;
    if(!Near(BlendBoost(1.f,2.f,0.f),1.f) ||
       !Near(BlendBoost(1.f,2.f,1.f),2.f) ||
       !Near(BlendBoost(1.f,2.f,.5f),1.5f)) return 7;
    // The same source envelope drives both eyes. Incoming and outgoing
    // glyph groups cannot jump between baseline and peripheral transforms.
    for (float aspect : {4.0f/3.0f, 16.0f/9.0f, 21.0f/9.0f})
    {
        const float w=480.0f*aspect, h=480.0f, margin=.015f*w;
        float previous=0.f;
        for(int step=0;step<=100;++step)
        {
            const float inset=margin*step/100.f;
            const float weight=FullyVisibleWeight(inset,.10f*w,.10f*h,.10f*h,w,h);
            const float positioned=PeripheralAnchor(.80f,.82f)*weight;
            const float enlarged=BlendBoost(1.f,1.65f,PeripheralWeight(.80f)*weight);
            if(weight<previous || weight-previous>.016f ||
               positioned<0.f || positioned>.81f ||
               enlarged<1.f || enlarged>1.65f) return 8;
            previous=weight;
        }
        if(!Near(FullyVisibleWeight(-.01f*w,.1f*w,.1f*h,.1f*h,w,h),0.f) ||
           !Near(FullyVisibleWeight(0.f,.1f*w,.1f*h,.1f*h,w,h),0.f) ||
           !Near(FullyVisibleWeight(margin,.1f*w,.1f*h,.1f*h,w,h),1.f) ||
           !Near(FullyVisibleWeight(margin*.5f,.1f*w,.1f*h,.1f*h,w,h),.5f))
            return 9;
    }
    if(!Near(FullyVisibleWeight(nan,10.f,10.f,10.f,640.f,480.f),0.f) ||
       !Near(FullyVisibleWeight(10.f,10.f,10.f,10.f,-1.f,480.f),0.f) ||
       !Near(FullyVisibleWeight(10.f,10.f,10.f,10.f,640.f,0.f),0.f))
        return 10;
    std::cout<<"DX9Ex gameplay HUD continuous anchor/zoom PASS\n";
    return 0;
}
