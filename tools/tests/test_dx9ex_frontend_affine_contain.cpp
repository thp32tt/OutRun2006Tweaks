// Portable C++17 changed-area regression; not DX9/HMD runtime evidence.
#include "../../src/vr/ui/frontend_affine_contain.hpp"
#include "../../src/vr/ui/menu_matrix_provenance.hpp"
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
 // D3DX-contained native 4:3 menu -> physical 16:9 custom sprite:
 // an exact matrix copy is already in pixels and must not re-letterbox.
 OutRunVrMenuQuad::ContainedMatrixLedger ledger;
 std::array<float,16> contained{}; contained[0]=0.75f;
 contained[5]=1.f; contained[12]=240.f; contained[15]=1.f;
 assert(ledger.Remember(contained,1,3.f,2.25f,1920,1080));
 assert(ledger.Contains(contained,1,3.f,2.25f,1920,1080));
 assert(Near(contained[12]+640*contained[0],720.f));
 assert(!Near(240.f+(contained[12]+640*contained[0])*2.25f,720.f));
 // An unrelated quad, second mode, reset viewport, stale source scale,
 // non-finite matrix and overwritten bounded-ring entry all fail closed.
 auto raw=contained; raw[12]=0; raw[0]=1.f;
 assert(!ledger.Contains(raw,1,3.f,2.25f,1920,1080));
 assert(!ledger.Contains(contained,2,3.f,2.25f,1920,1080));
 assert(!ledger.Contains(contained,1,3.f,2.25f,1600,900));
 assert(!ledger.Contains(contained,1,2.f,1.5f,1920,1080));
 assert(!ledger.Contains(contained,0,3.f,2.25f,1920,1080));
 auto corrupt=contained;corrupt[6]=std::numeric_limits<float>::quiet_NaN();
 assert(!ledger.Remember(corrupt,1,3.f,2.25f,1920,1080));
 assert(!ledger.Contains(corrupt,1,3.f,2.25f,1920,1080));
 for(int i=0;i<16;++i){auto other=contained;other[12]=300.f+i;
     assert(ledger.Remember(other,1,3.f,2.25f,1920,1080));}
 assert(!ledger.Contains(contained,1,3.f,2.25f,1920,1080));

}
