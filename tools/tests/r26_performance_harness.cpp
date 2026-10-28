#include <array>
#include <vector>
#include <algorithm>
#include <atomic>
#include <cstdint>
#include <cstring>
#include <cmath>
#include <cstdio>
#include <limits>
#include <mutex>
#include <memory>
#include <random>
#include "vr/d3d9/r30_shadow_scratch.hpp"
using UINT=unsigned;using HRESULT=std::int32_t;
constexpr HRESULT D3DERR_INVALIDCALL=-1, E_FAIL=-2;
bool SUCCEEDED(HRESULT h){return h>=0;}
bool FAILED(HRESULT h){return h<0;}
struct D3DMATRIX { union {float m[4][4];struct{float _11,_12,_13,_14,_21,_22,_23,_24,_31,_32,_33,_34,_41,_42,_43,_44;};}; };
struct D3DVIEWPORT9 {UINT X,Y,Width,Height;float MinZ,MaxZ;};
namespace OutRunVR {struct SharedFov {float angleLeft,angleRight,angleUp,angleDown;};}
namespace OutRunVRRenderer {struct LatchedStereoFrame{float eyeOrientation[2][4]{};float eyeOffset[2][3]{};OutRunVR::SharedFov eyeFov[2]{};};}
namespace Settings {bool VRTelemetry=false;float VRWorldScale=1,VRStereoDepth=1;}
namespace spdlog {template<class...T> void info(T...) {}}
namespace OutRunVR::GameSemantic {
int ExternalOverlaySemanticDepth=0;
struct Command{int producer=0;bool queued=false;void* queueNode=nullptr;std::uint64_t queueEpoch=0;bool IsExactFiniteResultHud()const{return false;}};
Command CapturePhysicalDrawCommand(){return {};}
const char* Name(int){return "test";}
}
struct Desc{UINT Width=1920,Height=1080;}BackBufferDesc;
float R30HudScaleValue(){return .55f;}
unsigned R30XyzrhwDepthPreserveFallbacks=0,R30XyzrhwAtomicFallbacks=0,R30XyzrhwBilateralFallbacks=0;
bool R30FirstXyzrhwAtomicFallbackLogged=false,R30FirstXyzrhwBilateralFallbackLogged=false;
unsigned actualRestores=0,referenceRestores=0,cacheBuilds=0;
// @STATE@
// @MATH@
// @CACHE@
// @REFERENCE@
// @ACTUAL@
struct IDirect3DSurface9{};
constexpr int D3DTEXF_NONE=0,D3DTEXF_LINEAR=2;
unsigned DirectTransportGeneration=1,DirectTransportWidth=1920,DirectTransportHeight=1080;
struct IDirect3DDevice9{
 unsigned calls=0,linear=0,none=0;HRESULT linearResult=0,noneResult=0;
 HRESULT StretchRect(IDirect3DSurface9*,void*,IDirect3DSurface9*,void*,int filter){++calls;if(filter==D3DTEXF_LINEAR){++linear;return linearResult;}++none;return noneResult;}
};
// @COPY@
struct IDirect3DVertexBuffer9{};
struct Shadow{std::mutex mutex;UINT size=0;std::vector<std::uint8_t> bytes;std::vector<std::pair<UINT,UINT>> valid;};
std::shared_ptr<Shadow> shadow;
auto R30FindVertexShadow(IDirect3DVertexBuffer9*){return shadow;}
unsigned R30ShadowReadHits=0;
bool R30RangeValid(const std::vector<std::pair<UINT,UINT>>& ranges,UINT a,UINT b){for(auto r:ranges)if(a>=r.first&&b<=r.second)return true;return false;}
// @SPARSE@
#define CHECK(c) do{if(!(c)){std::printf("FAIL line %d: %s\n",__LINE__,#c);return 1;}}while(0)
struct Vertex {float x,y,z,rhw;std::uint32_t color;float u,v;};
int main(){
 using Bytes=OutRunVR::R30ScratchBytes::WriteOnlyByteScratch;
 Bytes al,ar,bl,br;std::vector<std::array<float,4>> shared;
 std::mt19937 rng(1029);unsigned mismatches=0,success=0;
 for(unsigned test=0;test<4000;++test){
  R30XyzrhwState st{};st.viewport={3,7,1920,1080,0,1};st.worldEffect=true;st.fullWorldReprojection=true;
  st.baseProjection=IdentityMatrix();st.baseProjection._34=1;st.baseProjection._44=0;
  st.inverseBaseProjection=IdentityMatrix();
  for(int e=0;e<2;++e){st.eyeInverse[e]=IdentityMatrix();st.eyeInverse[e]._41=e?.03f:-.03f;st.eyeProjection[e]=st.baseProjection;st.eyeProjection[e]._31=e?.1f:-.07f;st.worldScaleX[e]=st.worldScaleY[e]=1;st.worldOffsetX[e]=e?.02f:-.01f;}
  const unsigned n=1+rng()%130;std::vector<Vertex> v(n);std::vector<std::uint8_t> used(n);
  for(unsigned i=0;i<n;++i){v[i]={float(rng()%2400)-200,float(rng()%1400)-100,float(rng()%150)/100, .001f+float(rng()%100)/50, static_cast<std::uint32_t>(rng()),float(i)/n,.7f};used[i]=rng()%3!=0;}
  switch(test%12){
   case 1:st.eyeProjection[1]._34=-1;break; // one-eye fallback
   case 2:st.eyeProjection[0]._34=-1;break;
   case 3:v[n/2].rhw=0;break;
   case 4:v[n/2].x=std::numeric_limits<float>::quiet_NaN();break;
   case 5:st.viewport.Width=0;break;
   case 6:st.worldEffect=false;st.hudWorldLockValid=true;for(int e=0;e<2;++e){st.hudClipX[e][0]=1;st.hudClipY[e][1]=1;st.hudClipW[e][2]=1;}break;
   case 7:st.projectedWorldMarker=true;st.fullWorldReprojection=false;break;
   case 8:st.baseProjection._14=.1f;break; // inverse-projection path
   case 9:st.viewport.MaxZ=st.viewport.MinZ;break;
   case 10:std::fill(used.begin(),used.end(),0);break;
  }
  const auto* mask=test%2?&used:nullptr;
  bool a=R30TransformXyzrhwStereo(v.data(),n,sizeof(Vertex),st,al,ar,shared,mask);
  bool b=ReferenceTransformXyzrhwStereo(v.data(),n,sizeof(Vertex),st,bl,br,mask);
  CHECK(a==b);
  if(a){++success;CHECK(al.size()==bl.size()&&ar.size()==br.size());if(std::memcmp(al.data(),bl.data(),al.size())||std::memcmp(ar.data(),br.data(),ar.size()))++mismatches;}
 }
 CHECK(mismatches==0);CHECK(actualRestores<referenceRestores);
 std::printf("PASS 4000 production transform cases (%u successful), byte-identical; restores %u -> %u\n",success,referenceRestores,actualRestores);
 OutRunVRRenderer::LatchedStereoFrame stereo{};for(int e=0;e<2;++e){stereo.eyeOrientation[e][3]=1;stereo.eyeOffset[e][0]=e?.03f:-.03f;stereo.eyeFov[e]={-.9f,.8f,.85f,-.75f};}
 D3DMATRIX projection=IdentityMatrix();
 for(unsigned i=0;i<100;++i){
  auto pair=R26CachedEyeMath(projection,stereo);CHECK(pair);
  for(int e=0;e<2;++e){auto pose=MatrixFromQuaternionTranslation(stereo.eyeOrientation[e],stereo.eyeOffset[e],Settings::VRWorldScale*Settings::VRStereoDepth);auto inv=InverseRigid(pose);auto proj=ProjectionFromFov(projection,stereo.eyeFov[e]);CHECK(!std::memcmp(&inv,&pair->inverse[e],sizeof(inv)));CHECK(!std::memcmp(&proj,&pair->projection[e],sizeof(proj)));}
 }
 CHECK(cacheBuilds==1);
 for(int field=0;field<5;++field){switch(field){case 0:projection._11+=.1f;break;case 1:stereo.eyeOrientation[1][1]=.1f;break;case 2:stereo.eyeOffset[0][2]=.1f;break;case 3:stereo.eyeFov[1].angleRight+=.1f;break;case 4:Settings::VRWorldScale+=.1f;break;}CHECK(R26CachedEyeMath(projection,stereo));CHECK(cacheBuilds==unsigned(field+2));}
 std::puts("PASS actual eye cache: identical results, repeat hit, projection/quaternion/offset/FOV/scale invalidation");
 IDirect3DDevice9 dev;IDirect3DSurface9 source,target;
 CHECK(StretchDirectEye(&dev,&source,&target)==0&&dev.linear==0&&dev.none==1);
 DirectTransportWidth=1500;++DirectTransportGeneration;dev.linearResult=D3DERR_INVALIDCALL;
 CHECK(StretchDirectEye(&dev,&source,&target)==0&&dev.linear==1);
 CHECK(StretchDirectEye(&dev,&source,&target)==0&&dev.linear==1);
 ++DirectTransportGeneration;CHECK(StretchDirectEye(&dev,&source,&target)==0&&dev.linear==2);
 ++DirectTransportGeneration;dev.linearResult=E_FAIL;
 CHECK(StretchDirectEye(&dev,&source,&target)==0);CHECK(StretchDirectEye(&dev,&source,&target)==0&&dev.linear==4);
 dev.noneResult=E_FAIL;CHECK(StretchDirectEye(&dev,&source,&target)==E_FAIL);
 CHECK(StretchDirectEye(nullptr,&source,&target)==D3DERR_INVALIDCALL);
 std::puts("PASS actual transfer policy: exact size, unsupported filter memo, generation reset, transient failure, HRESULT");
 shadow=std::make_shared<Shadow>();shadow->size=10000;shadow->bytes.resize(10000);for(unsigned i=0;i<10000;++i)shadow->bytes[i]=i%251;shadow->valid={{0,10000}};
 std::vector<std::uint32_t> physical{1,100,300,100,1,300};auto original=physical;auto unique=physical;std::sort(unique.begin(),unique.end());unique.erase(std::unique(unique.begin(),unique.end()),unique.end());
 IDirect3DVertexBuffer9 vb;Bytes sparse;CHECK(R30CopySparseVertexShadow(&vb,16,28,unique,sparse));
 for(auto& v:physical)v=std::lower_bound(unique.begin(),unique.end(),v)-unique.begin();
 for(unsigned i=0;i<physical.size();++i)CHECK(!std::memcmp(sparse.data()+physical[i]*28,shadow->bytes.data()+16+original[i]*28,28));
 shadow->valid={{0,200}};CHECK(!R30CopySparseVertexShadow(&vb,16,28,unique,sparse));
 shadow->valid={{0,10000}};CHECK(!R30CopySparseVertexShadow(&vb,0,28,{UINT(-1)},sparse));
 std::puts("PASS actual sparse shadow copy: primitive order/attributes, missing provenance, overflow bounds");
}
