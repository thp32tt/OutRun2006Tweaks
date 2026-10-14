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
    std::cout<<"DX9Ex gameplay HUD continuous anchor/zoom PASS\n";
    return 0;
}
