#include "vr/ui/menu_quad_transform.hpp"
#include <cmath>
#include <limits>

// Native, Release-executed game-header regression. The authored custom quad
// must fit the real backbuffer even if cached screen_scale is stale after a
// size transition. The regular Vanilla/desktop route must stay unchanged.
namespace {
bool Near(float a, float b, float epsilon=0.001f) noexcept
{
    return std::isfinite(a) && std::isfinite(b) &&
        std::fabs(a-b) < epsilon;
}
bool UniformQuad(const OutRunVrMenuQuad::PixelMap& m,
    float sourceWidth, float sourceHeight,
    float screenWidth, float screenHeight) noexcept
{
    if (!m.valid || !Near(m.scaleX,m.scaleY) || m.scaleX <= 0.0f)
        return false;
    const float l=OutRunVrMenuQuad::ProjectX(m,0)-0.5f;
    const float t=OutRunVrMenuQuad::ProjectY(m,0)-0.5f;
    const float r=OutRunVrMenuQuad::ProjectX(m,sourceWidth)-0.5f;
    const float b=OutRunVrMenuQuad::ProjectY(m,sourceHeight)-0.5f;
    return l >= -0.001f && t >= -0.001f &&
        r <= screenWidth+0.001f && b <= screenHeight+0.001f &&
        Near(l,screenWidth-r) && Near(t,screenHeight-b) &&
        Near(r-l,sourceWidth*m.scaleX) &&
        Near(b-t,sourceHeight*m.scaleY);
}
}
int main()
{
    using namespace OutRunVrMenuQuad;
    const auto native=BuildPixelMap(true,true,1,1,640,480,640,480);
    if(!UniformQuad(native,640,480,640,480) ||
       !Near(native.scaleX,1)) return 1;

    const auto wide=BuildPixelMap(true,true,3,2.25f,1920,1080,640,480);
    if(!UniformQuad(wide,640,480,1920,1080) ||
       !Near(wide.scaleX,2.25f) ||
       !Near(wide.offsetX,240)) return 2;

    const auto ultra=BuildPixelMap(true,true,5.375f,3,3440,1440,640,480);
    if(!UniformQuad(ultra,640,480,3440,1440) ||
       !Near(ultra.scaleX,3) || !Near(ultra.offsetX,760)) return 3;

    const auto portrait=BuildPixelMap(true,true,1.875f,3.333333f,
        1200,1600,640,480);
    if(!UniformQuad(portrait,640,480,1200,1600) ||
       !Near(portrait.scaleX,1.875f) ||
       !Near(portrait.offsetY,350)) return 4;

    // A screen-scale value from a previous 1920x1080 output must NOT crop
    // 1600x900's selector to 1920 pixels during the Reset transition.
    const auto stale=BuildPixelMap(true,true,3,2.25f,1600,900,640,480);
    if(!UniformQuad(stale,640,480,1600,900) ||
       !Near(stale.scaleX,1.875f) || !Near(stale.offsetX,200)) return 5;

    // User-authored deliberately smaller scale remains unchanged.
    const auto small=BuildPixelMap(true,true,1,1,1920,1080,640,480);
    if(!UniformQuad(small,640,480,1920,1080) ||
       !Near(small.scaleX,1)) return 6;

    // Preserve the original uncontained Vanilla anisotropic X path and Y
    // mapping independently of any transient absent screen dimensions.
    const auto vanilla=BuildPixelMap(false,true,3,2.25f,0,0,0,0);
    const auto other=BuildPixelMap(false,false,3,2.25f,0,0,0,0);
    if(!vanilla.valid || !other.valid ||
       !Near(vanilla.scaleX,3) || !Near(vanilla.scaleY,2.25f) ||
       !Near(other.scaleX,2.25f) || !Near(other.scaleY,2.25f))
        return 7;

    if(BuildPixelMap(true,true,3,2,1600,900,0,480).valid ||
       BuildPixelMap(true,true,3,2,1600,0,640,480).valid ||
       BuildPixelMap(true,true,3,2,1600,900,
           std::numeric_limits<float>::quiet_NaN(),480).valid ||
       BuildPixelMap(true,true,3,2,1600,900,
           std::numeric_limits<float>::min(),480).valid)
        return 8;

    // Each of four arbitrary source-space corners receives one identical
    // affine: corner order and 90-degree rotated art cannot skew or crop
    // one axis while the other is physical-viewport bounded.
    const float sx=25,sy=70;
    if(!Near(ProjectX(stale,sx)-ProjectX(stale,0),sx*stale.scaleX) ||
       !Near(ProjectY(stale,sy)-ProjectY(stale,0),sy*stale.scaleY))
        return 9;
    return 0;
}
