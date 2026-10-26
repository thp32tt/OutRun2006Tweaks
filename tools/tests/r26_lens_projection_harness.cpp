// The C993 production branch is inserted verbatim by the verifier.
// R7 projection/quaternion/transpose functions are inserted verbatim too.
// Expected rays use independent scalar quaternion algebra and shader-layout
// decoding. D3D/XR boundaries are fakes, not physical GPU/HMD acceptance.
#include "vr/d3d9/projected_sun_ray.hpp"
#include "vr/d3d9/lens_centre_relative_eye_pose.hpp"
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <limits>
#include <initializer_list>

struct D3DMATRIX { union { float m[4][4]; struct {
    float _11,_12,_13,_14,_21,_22,_23,_24,
          _31,_32,_33,_34,_41,_42,_43,_44;
}; }; };
struct Fov { float angleLeft, angleRight, angleUp, angleDown; };
namespace OutRunVR { using SharedFov = Fov; }
struct Stereo {
    std::uint32_t poseSequence = 7;
    float eyeOffset[2][3]{};
    float eyeOrientation[2][4]{{0,0,0,1},{0,0,0,1}};
    Fov eyeFov[2]{};
};
// @ACTUAL_RENDER_MATH@
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
struct V { double x,y,z; };
struct Q { double x,y,z,w; };
V cross(V a,V b){return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}
V rotate(Q q,V v) {
    const double n=std::sqrt(q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w);
    q={q.x/n,q.y/n,q.z/n,q.w/n};
    const V t=cross({q.x,q.y,q.z},v),u=cross({q.x,q.y,q.z},t);
    return {v.x+2*(q.w*t.x+u.x),v.y+2*(q.w*t.y+u.y),v.z+2*(q.w*t.z+u.z)};
}
Q product(Q a,Q b) {
    return {a.w*b.x+a.x*b.w+a.y*b.z-a.z*b.y,
            a.w*b.y-a.x*b.z+a.y*b.w+a.z*b.x,
            a.w*b.z+a.x*b.y-a.y*b.x+a.z*b.w,
            a.w*b.w-a.x*b.x-a.y*b.y-a.z*b.z};
}
Q euler(double yaw,double pitch,double roll) {
    return product(product({0,std::sin(yaw/2),0,std::cos(yaw/2)},
                           {std::sin(pitch/2),0,0,std::cos(pitch/2)}),
                           {0,0,std::sin(roll/2),std::cos(roll/2)});
}
bool sameDirection(V a,V b) {
    const double na=std::sqrt(a.x*a.x+a.y*a.y+a.z*a.z);
    const double nb=std::sqrt(b.x*b.x+b.y*b.y+b.z*b.z);
    return std::fabs(a.x/na-b.x/nb)<0.00002 &&
           std::fabs(a.y/na-b.y/nb)<0.00002 &&
           std::fabs(a.z/na-b.z/nb)<0.00002;
}
bool rays3d(const Stereo& s,const float (&constants)[2][16],Q head) {
    const V points[]={{.25,-.125,-1},{-.03,.018,-.2},{12,-5,-100}};
    for(const auto p:points) for(int e=0;e<2;++e) {
        D3DMATRIX t{}; std::memcpy(&t,constants[e],sizeof(t));
        D3DMATRIX m{};
        for(int r=0;r<4;++r) for(int c=0;c<4;++c) m.m[r][c]=t.m[c][r];
        const double point[4]{p.x,p.y,p.z,1}; double clip[4]{};
        for(int j=0;j<4;++j) for(int k=0;k<4;++k) clip[j]+=point[k]*m.m[k][j];
        if(!std::isfinite(clip[3]) || clip[3]<=0) return false;
        const auto& f=s.eyeFov[e];
        const double l=std::tan(f.angleLeft),r=std::tan(f.angleRight);
        const double d=std::tan(f.angleDown),u=std::tan(f.angleUp);
        const V eyeRay{(clip[0]/clip[3]*(r-l)+r+l)*.5,
                       (clip[1]/clip[3]*(u-d)+u+d)*.5,-1};
        const auto* q=s.eyeOrientation[e];
        const V recovered=rotate({q[0],q[1],q[2],q[3]},eyeRay);
        const V expected=OutRunVRRenderer::synced?p:rotate(head,p);
        if(!sameDirection(recovered,expected)) return false;
    }
    return true;
}
void setEye(Stereo& s,int e,Q q) {
    const float scale=e?1.3f:.7f;
    s.eyeOrientation[e][0]=static_cast<float>(q.x)*scale;
    s.eyeOrientation[e][1]=static_cast<float>(q.y)*scale;
    s.eyeOrientation[e][2]=static_cast<float>(q.z)*scale;
    s.eyeOrientation[e][3]=static_cast<float>(q.w)*scale;
}
bool rays(const Stereo& s,const float (&constants)[2][16],float wantX,float wantY) {
    for(int e=0;e<2;++e) {
        D3DMATRIX t{}; std::memcpy(&t,constants[e],sizeof(t));
        D3DMATRIX m{};
        for(int r=0;r<4;++r) for(int c=0;c<4;++c) m.m[r][c]=t.m[c][r];
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
    OutRunVR::GameSemantic::producer=OutRunVR::GameSemantic::ProducerToken::LensFlareCentre;
    const Q rotations[]={{0,0,0,1},euler(.18,0,0),euler(0,-.16,0),
                         euler(0,0,.23),euler(.15,-.12,.21)};
    unsigned cases=0;
    for(const auto head:rotations) for(const auto eye:rotations) {
        setEye(s,0,eye);
        setEye(s,1,product(euler(-.04,.03,-.02),eye));
        const float q[]{static_cast<float>(head.x),static_cast<float>(head.y),
                        static_cast<float>(head.z),static_cast<float>(head.w)};
        const float translation[]{10,-8,4};
        OutRunVRRenderer::head=MatrixFromQuaternionTranslation(q,translation,1);
        for(bool sync:{false,true}) {
            OutRunVRRenderer::synced=sync;
            if(!actual(s,base,base,inv,output)||!rays3d(s,output,head)) {
                std::puts("FAIL production C993/R7: recovered 3D eye rays disagree"); return 9;
            }
            ++cases;
        }
    }
    std::printf("PASS production C993 + R7 math: %u yaw/pitch/roll/combined/camera-sync pairs, 3 depths, normalized eye cant, translation exclusion, atomic rejection\n",cases);
}

