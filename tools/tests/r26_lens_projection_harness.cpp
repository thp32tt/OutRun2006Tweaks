// The C993 production branch is inserted verbatim by the verifier.
// D3D/XR boundary adapters use row-vector matrices. Expected rays below
// are reconstructed independently from the submitted FOV and eye rotation.
#include "vr/d3d9/projected_sun_ray.hpp"
#include "vr/d3d9/lens_centre_relative_eye_pose.hpp"
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <limits>

struct D3DMATRIX { float m[4][4]{}; };
struct Fov { float angleLeft, angleRight, angleUp, angleDown; };
struct Stereo {
    std::uint32_t poseSequence = 7;
    float eyeOffset[2][3]{};
    float eyeOrientation[2][4]{{0,0,0,1},{0,0,0,1}};
    Fov eyeFov[2]{};
};
D3DMATRIX IdentityMatrix() {
    D3DMATRIX m{}; for(int i=0;i<4;++i) m.m[i][i]=1; return m;
}
D3DMATRIX TransposeMatrix(const D3DMATRIX& a) {
    D3DMATRIX m{}; for(int i=0;i<4;++i) for(int j=0;j<4;++j) m.m[i][j]=a.m[j][i]; return m;
}
D3DMATRIX MatrixFromQuaternionTranslation(const float* q,const float* t,float scale) {
    const float x=q[0],y=q[1],z=q[2],w=q[3];
    D3DMATRIX m=IdentityMatrix();
    m.m[0][0]=1-2*y*y-2*z*z; m.m[0][1]=2*x*y+2*z*w; m.m[0][2]=2*x*z-2*y*w;
    m.m[1][0]=2*x*y-2*z*w; m.m[1][1]=1-2*x*x-2*z*z; m.m[1][2]=2*y*z+2*x*w;
    m.m[2][0]=2*x*z+2*y*w; m.m[2][1]=2*y*z-2*x*w; m.m[2][2]=1-2*x*x-2*y*y;
    for(int i=0;i<3;++i) m.m[3][i]=t[i]*scale;
    return m;
}
D3DMATRIX InverseRigid(const D3DMATRIX& a) {
    D3DMATRIX m=IdentityMatrix();
    for(int i=0;i<3;++i) for(int j=0;j<3;++j) m.m[i][j]=a.m[j][i];
    for(int j=0;j<3;++j) for(int k=0;k<3;++k) m.m[3][j]-=a.m[3][k]*m.m[k][j];
    return m;
}
D3DMATRIX ProjectionFromFov(const D3DMATRIX& base,const Fov& f) {
    D3DMATRIX m=base;
    const float l=std::tan(f.angleLeft),r=std::tan(f.angleRight);
    const float d=std::tan(f.angleDown),u=std::tan(f.angleUp);
    m.m[0][0]=2/(r-l); m.m[1][1]=2/(u-d);
    m.m[2][0]=(r+l)/(r-l); m.m[2][1]=(u+d)/(u-d);
    return m;
}
namespace OutRunVR::GameSemantic {
enum class ProducerToken { None, LensFlareCentre };
bool queued=false;
ProducerToken producer=ProducerToken::LensFlareCentre;
bool QueueRenderActive(){ return queued; }
ProducerToken CurrentRenderProducerToken(){ return producer; }
}
namespace OutRunVRRenderer {
D3DMATRIX head=IdentityMatrix();
std::uint32_t sequence=7;
bool haveHead=true,synced=false;
bool GetLatchedHeadInverse(float* out,std::uint32_t& seq) {
    std::memcpy(out,&head,sizeof(head)); seq=sequence; return haveHead;
}
bool GetLastRawGameWvpCameraSynced(){ return synced; }
}
bool actual(const Stereo& stereo,const D3DMATRIX& stockWvp,
            const D3DMATRIX& baseProjection,const D3DMATRIX& inverseBaseProjection,
            float (&eyeConstants)[2][16]) {
    // @ACTUAL_C993_BRANCH@
    return false;
}
bool same(float x,float y){ return std::fabs(x-y)<0.0001f; }
bool rays(const Stereo& s,const float (&constants)[2][16],float wantX,float wantY) {
    for(int e=0;e<2;++e) {
        D3DMATRIX t{}; std::memcpy(&t,constants[e],sizeof(t));
        const auto m=TransposeMatrix(t);
        const float point[4]{.25f,-.125f,-1,1}; float clip[4]{};
        for(int j=0;j<4;++j) for(int k=0;k<4;++k) clip[j]+=point[k]*m.m[k][j];
        const auto& f=s.eyeFov[e];
        const float l=std::tan(f.angleLeft),r=std::tan(f.angleRight);
        const float d=std::tan(f.angleDown),u=std::tan(f.angleUp);
        const float eyeX=(clip[0]/clip[3]*(r-l)+r+l)*.5f;
        const float eyeY=(clip[1]/clip[3]*(u-d)+u+d)*.5f;
        // Independently undo eye-local roll used by the fixtures.
        const float angle=2*std::atan2(s.eyeOrientation[e][2],s.eyeOrientation[e][3]);
        const float x=eyeX*std::cos(angle)-eyeY*std::sin(angle);
        const float y=eyeX*std::sin(angle)+eyeY*std::cos(angle);
        if(!same(x,wantX)||!same(y,wantY)) return false;
    }
    return true;
}
int main() {
    Stereo s{};
    s.eyeFov[0]={-.9f,.7f,.8f,-.6f};
    s.eyeFov[1]={-.65f,.85f,.7f,-.9f};
    D3DMATRIX base{}; base.m[0][0]=base.m[1][1]=1;
    base.m[2][2]=-1.01f; base.m[2][3]=-1; base.m[3][2]=-.101f;
    D3DMATRIX inv{}; inv.m[0][0]=inv.m[1][1]=1;
    inv.m[2][3]=-1/.101f; inv.m[3][2]=-1; inv.m[3][3]=1.01f/.101f;
    float output[2][16]{};
    if(!actual(s,base,base,inv,output)||!rays(s,output,.25f,-.125f)) {
        std::puts("FAIL actual C993: asymmetric submitted FOVs recover different sun rays"); return 1;
    }
    for(int e=0;e<2;++e) {
        const float angle=e?-.23f:.17f;
        s.eyeOrientation[e][2]=std::sin(angle/2); s.eyeOrientation[e][3]=std::cos(angle/2);
        s.eyeOffset[e][0]=e?.032f:-.032f;
    }
    if(!actual(s,base,base,inv,output)||!rays(s,output,.25f,-.125f)) return 2;
    auto& h=OutRunVRRenderer::head;
    h.m[0][0]=h.m[1][1]=0; h.m[0][1]=1; h.m[1][0]=-1;
    h.m[3][0]=10; h.m[3][1]=-8; h.m[3][2]=4;
    if(!actual(s,base,base,inv,output)||!rays(s,output,.125f,.25f)) return 3;
    OutRunVRRenderer::synced=true;
    if(!actual(s,base,base,inv,output)||!rays(s,output,.25f,-.125f)) return 4;
    float saved[2][16]{}; std::memcpy(saved,output,sizeof(saved));
    const auto unchanged=[&](){return std::memcmp(saved,output,sizeof(saved))==0;};
    s.eyeOrientation[1][0]=std::numeric_limits<float>::quiet_NaN();
    if(actual(s,base,base,inv,output)||!unchanged()) return 5;
    s.eyeOrientation[1][0]=0;
    OutRunVRRenderer::sequence=8;
    if(actual(s,base,base,inv,output)||!unchanged()) return 6;
    OutRunVRRenderer::sequence=7;
    OutRunVR::GameSemantic::queued=true;
    if(actual(s,base,base,inv,output)||!unchanged()) return 7;
    OutRunVR::GameSemantic::queued=false;
    OutRunVR::GameSemantic::producer=OutRunVR::GameSemantic::ProducerToken::None;
    if(actual(s,base,base,inv,output)||!unchanged()) return 8;
    std::puts("PASS actual C993: asymmetric XY FOV, eye cant, head rotation, translation exclusion, camera sync, atomic rejection and exact scope");
}
