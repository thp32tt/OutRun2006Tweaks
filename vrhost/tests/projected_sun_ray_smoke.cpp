#include "vr/d3d9/projected_sun_ray.hpp"
#include <cmath>
#include <cstdio>
#include <limits>

struct Matrix { float m[4][4]{}; };
Matrix identity() { Matrix a{}; for (int i=0;i<4;++i) a.m[i][i]=1; return a; }
Matrix projection(float offsetX, float offsetY) {
    Matrix a{}; a.m[0][0]=1; a.m[1][1]=1;
    a.m[2][0]=offsetX; a.m[2][1]=offsetY;
    a.m[2][2]=-1.01f; a.m[2][3]=-1; a.m[3][2]=-0.101f;
    return a;
}
Matrix inverseProjection() {
    Matrix a{}; a.m[0][0]=a.m[1][1]=1;
    a.m[2][3]=-1.0f/0.101f; a.m[3][2]=-1;
    a.m[3][3]=1.01f/0.101f; return a;
}
bool near(float a,float b) { return std::fabs(a-b)<0.0001f; }
bool ray(const Matrix& a, float projectionX, float projectionY,
         float wantX, float wantY) {
    // Independent observation: inverse of the runtime eye's asymmetric
    // projection at a hand-selected model point (0.25, -0.125, -1, 1).
    const float p[4]{0.25f,-0.125f,-1,1}; float clip[4]{};
    for(int j=0;j<4;++j) for(int k=0;k<4;++k) clip[j]+=p[k]*a.m[k][j];
    return near(clip[0]/clip[3]+projectionX,wantX) &&
           near(clip[1]/clip[3]+projectionY,wantY);
}
int main() {
    const Matrix stock=projection(0,0), inverse=inverseProjection();
    Matrix head=identity(), eye=identity(), result{};
    for (int side=0;side<2;++side) {
        const float x=side ? -0.18f : 0.12f;
        const float y=side ? -0.04f : 0.07f;
        if (!OutRunVR::LensCentre::BuildProjectedSunRay(
                stock,inverse,head,eye,projection(x,y),result) ||
            !ray(result,x,y,0.25f,-0.125f)) {
            std::puts("FAIL: asymmetric eye projections do not recover the same sun ray"); return 1;
        }
    }
    // 90-degree roll of the head inverse: (x,y) -> (-y,x).
    head.m[0][0]=head.m[1][1]=0; head.m[0][1]=1; head.m[1][0]=-1;
    // Translation/IPD must not turn the artificial z=-1 sun plane into
    // a nearby stereoscopic object, regardless of its fake scene depth.
    head.m[3][0]=7; head.m[3][1]=-9; head.m[3][2]=4;
    eye.m[3][0]=0.032f; eye.m[3][2]=-0.02f;
    if(!OutRunVR::LensCentre::BuildProjectedSunRay(stock,inverse,head,eye,
            projection(0.12f,0.07f),result) ||
       !ray(result,0.12f,0.07f,0.125f,0.25f)) {
        std::puts("FAIL: sun is head locked or fake-plane translation is applied"); return 2;
    }
    // Eye cant is independent of common head rotation: inverse roll cancels.
    eye.m[0][0]=eye.m[1][1]=0; eye.m[0][1]=-1; eye.m[1][0]=1;
    if(!OutRunVR::LensCentre::BuildProjectedSunRay(stock,inverse,head,eye,
            projection(-0.18f,-0.04f),result) ||
       !ray(result,-0.18f,-0.04f,0.25f,-0.125f)) {
        std::puts("FAIL: eye-local rotation was lost"); return 3;
    }
    // A source already computed with the synchronized camera must not rotate
    // again. With no eye cant it retains its original source ray.
    eye=identity();
    if(!OutRunVR::LensCentre::BuildProjectedSunRay(stock,inverse,head,eye,
            projection(0.12f,0.07f),result,true) ||
       !ray(result,0.12f,0.07f,0.25f,-0.125f)) {
        std::puts("FAIL: synchronized camera receives a second head rotation"); return 6;
    }
    // HMD visual tuning: 0.5 scale halves local flare geometry around
    // its authored origin without moving the centre ray.
    {
        Matrix half{};
        const Matrix id = identity();
        if (!OutRunVR::LensCentre::BuildProjectedSunRay(
                projection(0,0), inverseProjection(), id, id,
                projection(0,0), half, false, 0.5f, 0.0f) ||
            !ray(half,0,0,0.125f,-0.0625f)) {
            std::puts("FAIL: 0.5 flare scale did not preserve centre and halve local size");
            return 7;
        }
    }
    // A tiny eye translation fraction is allowed for finite depth; it must
    // remain bounded and finite rather than reproducing full fake-plane IPD.
    {
        Matrix depthEye=identity(), shallow{};
        depthEye.m[3][0]=-0.032f;
        if (!OutRunVR::LensCentre::BuildProjectedSunRay(
                stock,inverse,identity(),depthEye,projection(0,0),
                shallow,false,1.0f,0.025f)) {
            std::puts("FAIL: shallow finite flare depth rejected");
            return 8;
        }
        for(int i=0;i<4;++i) for(int j=0;j<4;++j)
            if(!std::isfinite(shallow.m[i][j])) {
                std::puts("FAIL: shallow flare depth produced non-finite matrix");
                return 9;
            }
    }
    Matrix saved=result;
    head.m[0][0]=std::numeric_limits<float>::quiet_NaN();
    if(OutRunVR::LensCentre::BuildProjectedSunRay(stock,inverse,head,eye,
            projection(0,0),result)) {
        std::puts("FAIL: malformed pose accepted"); return 4;
    }
    for(int i=0;i<4;++i) for(int j=0;j<4;++j)
        if(result.m[i][j]!=saved.m[i][j]) { std::puts("FAIL: partial result published"); return 5; }
    std::puts("PASS projected sun: asymmetric FOV, head rotation, 0.5 local scale, shallow finite eye depth, atomic rejection");
}
