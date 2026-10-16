// Portable C++17 changed-area regression; not DX9/HMD runtime evidence.
#include "../../src/vr/ui/frontend_affine_contain.hpp"
#include <cassert>
#include <cmath>
#include <limits>
static bool Near(float a,float b){return std::fabs(a-b)<0.002f;}
int main(){
 using OutRunVrUiAspect::BuildFrontEndAffineContain;
 auto m=BuildFrontEndAffineContain(1,1,640,480,640,480);
 assert(m.valid&&Near(m.MapX(640),640)&&Near(m.MapY(480),480));
 m=BuildFrontEndAffineContain(3,2.25f,1920,1080,640,480);
 assert(m.valid&&Near(m.MapX(0),240)&&Near(m.MapX(1920),1680)&&Near(m.MapY(1080),1080));
 assert(Near(m.ScaleX(120),90));
 m=BuildFrontEndAffineContain(5.375f,3,3440,1440,640,480);
 assert(m.valid&&Near(m.MapX(0),760)&&Near(m.MapX(3440),2680));
 // Reset to 1280x720 while original game screen_scale still says 1920x1080.
 // The old 2.25 scale would overflow both axes of the current backbuffer.
 m=BuildFrontEndAffineContain(3,2.25f,1280,720,640,480);
 assert(m.valid&&Near(m.MapX(0),160)&&Near(m.MapX(1920),1120));
 assert(Near(m.MapY(0),0)&&Near(m.MapY(1080),720));
 // The full/partial/pivoted D3DX paths share one physical affine basis.
 assert(Near(m.ScaleX(120),60)&&Near(m.ScaleY(90),60));
 assert(Near(m.MapX(960),640)&&Near(m.MapY(540),360));
 m=BuildFrontEndAffineContain(2.5f,3.3333333f,1200,1600,640,480);
 assert(m.valid&&Near(m.MapX(0),0)&&Near(m.MapY(0),350)&&Near(m.MapY(1600),1250));
 m=BuildFrontEndAffineContain(1,1,1920,1080,640,480);
 assert(m.valid&&Near(m.MapX(0),640)&&Near(m.MapY(0),300));
 const float nan=std::numeric_limits<float>::quiet_NaN();
 assert(!BuildFrontEndAffineContain(0,2,1280,720,640,480).valid);
 assert(!BuildFrontEndAffineContain(3,2.25f,0,720,640,480).valid);
 assert(!BuildFrontEndAffineContain(nan,2,1280,720,640,480).valid);
 assert(!BuildFrontEndAffineContain(3,2.25f,1280,720,0,480).valid);
}
