// Runs extracted production code; fake D3D calls record output and failures.
#include <algorithm>
#include <atomic>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <vector>
using HRESULT=int; using DWORD=unsigned; using LONG=long;
constexpr int E_NOTIMPL=-1,E_FAIL=-2,D3D_OK=0;
constexpr int D3DTS_WORLD=1,D3DTS_VIEW=2,D3DTS_PROJECTION=3;
constexpr int D3DRS_ZENABLE=1,D3DRS_SCISSORTESTENABLE=2;
constexpr int D3DZB_TRUE=1,D3DZB_FALSE=0,FALSE=0;
constexpr unsigned D3DFVF_POSITION_MASK=14,D3DFVF_XYZ=2,D3DFVF_DIFFUSE=64,D3DFVF_TEXCOUNT_MASK=3840,D3DFVF_TEX1=256;
bool SUCCEEDED(int h){return h>=0;} bool FAILED(int h){return h<0;}
struct D3DVIEWPORT9 {DWORD X=0,Y=0,Width=1337,Height=1440;float MinZ=0.2f,MaxZ=0.9f;};
struct RECT {LONG left=0,top=0,right=1337,bottom=1440;};
struct D3DMATRIX {union {float m[4][4];struct {float _11,_12,_13,_14,_21,_22,_23,_24,_31,_32,_33,_34,_41,_42,_43,_44;};};};
D3DMATRIX Identity(){D3DMATRIX x{};for(int i=0;i<4;i++)x.m[i][i]=1;return x;}
bool MatrixFinite(const D3DMATRIX& x){for(auto&r:x.m)for(float v:r)if(!std::isfinite(v))return false;return true;}
D3DMATRIX MultiplyMatrix(const D3DMATRIX&a,const D3DMATRIX&b){D3DMATRIX c{};for(int i=0;i<4;i++)for(int j=0;j<4;j++)for(int k=0;k<4;k++)c.m[i][j]+=a.m[i][k]*b.m[k][j];return c;}
bool R30ExternalImGuiIdentity(const D3DMATRIX& x){auto id=Identity();return std::memcmp(&id,&x,sizeof x)==0;}
struct IDirect3DVertexShader9 {void Release(){}};
struct IDirect3DSurface9 {};
IDirect3DSurface9 leftSurface,rightSurface,depthSurface,rightDepth;
IDirect3DSurface9*TrackedRenderTarget=&leftSurface,*TrackedDepthStencil=&depthSurface,*RightEyeSurface=&rightSurface,*RightEyeDepth=&rightDepth;
struct {unsigned Width=2496,Height=2688;} BackBufferDesc;
struct IDirect3DDevice9 {
 D3DVIEWPORT9 viewport; RECT scissor; D3DMATRIX projection=Identity();
 IDirect3DSurface9*target=&leftSurface,*depth=&depthSurface;
 unsigned failViewport=0,viewportCalls=0,failTransform=0,transformCalls=0;
 IDirect3DDevice9(){projection._11=2.f/1337;projection._22=-2.f/1440;projection._41=-1;projection._42=1;}
 HRESULT GetVertexShader(IDirect3DVertexShader9**s){*s=nullptr;return 0;}
 HRESULT GetFVF(DWORD*f){*f=0x142;return 0;}
 HRESULT GetTransform(int t,D3DMATRIX*p){*p=t==D3DTS_PROJECTION?projection:Identity();return 0;}
 HRESULT GetRenderState(int t,DWORD*p){*p=t==D3DRS_ZENABLE?0:1;return 0;}
 HRESULT GetScissorRect(RECT*p){*p=scissor;return 0;}
 HRESULT GetViewport(D3DVIEWPORT9*p){*p=viewport;return 0;}
 HRESULT SetViewport(const D3DVIEWPORT9*p){if(++viewportCalls==failViewport)return E_FAIL;viewport=*p;return 0;}
 HRESULT SetTransform(int,const D3DMATRIX*p){if(++transformCalls==failTransform)return E_FAIL;projection=*p;return 0;}
 HRESULT SetScissorRect(const RECT*p){scissor=*p;return 0;}
};
namespace OutRunVR::GameSemantic {enum class RenderScope {ScreenOverlay2D,None};unsigned ExternalOverlaySemanticDepth=1;RenderScope EffectiveScope(){return RenderScope::ScreenOverlay2D;}}
namespace OutRunVR {enum StereoFailureReason{StereoFailureLeftDrawFailed,StereoFailureRightStateFailed,StereoFailureRightDrawFailed};}
namespace Settings {bool VRTelemetry=true;}
namespace spdlog {template<class...T>void info(T&&...){}}
namespace OutRunVRRenderer {struct Fov{float angleLeft=-.7f,angleRight=.7f,angleDown=-.7f,angleUp=.7f;};struct Stereo{unsigned poseSequence=7;Fov eyeFov[2];};bool GetLatchedStereoFrame(Stereo&s){s.poseSequence=7;return true;}}
namespace OutRunVRF11Screen2D {struct EyeAffine{float scaleX=1,scaleY=1,offsetX=0,offsetY=0;};struct TangentBounds{float l,r,d,u;};bool Build(const TangentBounds*,EyeAffine*){return true;}}
struct R30XyzrhwState {D3DVIEWPORT9 viewport;OutRunVRRenderer::Stereo stereo;bool hudWorldLockValid=false;D3DMATRIX baseProjection=Identity();float hudClipX[2][3]{},hudClipY[2][3]{},hudClipW[2][3]{};};
bool FrameHadWorldStereo=true,FrameHadDuplicatedDraw=true,FrameRightDrawFailed=false;
unsigned FrameStereoPoseSequence=7,DuplicatedDraws=0,NonWorldDuplicatedDraws=0,R30SafeTwoEyeDraws=0,R30ExternalImGuiStereoDraws=0,R30ExternalImGuiEyeAttempts=0;
std::atomic<unsigned>CurrentVertexShaderIdentity{0};
bool safeBase=true;bool R30SafeStereoBase(IDirect3DDevice9*){return safeBase;}
bool R30ConfigureXyzrhwWorldEffect(IDirect3DDevice9*,const void*,unsigned,unsigned,R30XyzrhwState&,void*){return false;}
float R30HudPlaneViewZ(bool){return 1;}
struct InternalPassScope{};
void R30CaptureSkyGlowSceneBeforeHud(IDirect3DDevice9*){}
void R9NoteStereoDrawWithoutMonoBackup(){}
int poisons=0,restoreFailures=0,fallbacks=0;
void R9Poison(OutRunVR::StereoFailureReason,const char*,int){++poisons;}
void R30ArmSafeFallback(){++fallbacks;}
void NoteRestoreFailure(const char*){++restoreFailures;}
void InvalidateRightDepthStencilIfLeftMayWrite(IDirect3DDevice9*){}
struct RtHook{template<class T>T stdcall(IDirect3DDevice9*d,unsigned,IDirect3DSurface9*s){d->target=s;d->viewport={0,0,2496,2688,0,1};return 0;}}SetRenderTargetHook;
struct DsHook{template<class T>T stdcall(IDirect3DDevice9*d,IDirect3DSurface9*s){d->depth=s;return 0;}}SetDepthStencilSurfaceHook;
bool RestoreRightPassState(IDirect3DDevice9*d,IDirect3DSurface9*r,IDirect3DSurface9*z,const D3DVIEWPORT9&v,void*,bool){d->target=r;d->depth=z;return SUCCEEDED(d->SetViewport(&v));}
// @ACTUAL_F11_SOURCE@
void require(bool ok,const char*msg){if(!ok){std::fprintf(stderr,"FAIL %s\n",msg);std::exit(1);}}
void restored(const IDirect3DDevice9&d,const IDirect3DDevice9&before){require(std::memcmp(&d.viewport,&before.viewport,sizeof d.viewport)==0,"restore original client viewport and depth range");require(std::memcmp(&d.projection,&before.projection,sizeof d.projection)==0,"restore projection");require(std::memcmp(&d.scissor,&before.scissor,sizeof d.scissor)==0,"restore scissor");require(d.target==before.target&&d.depth==before.depth,"restore targets");}
int main(){
 for(int failure=0;failure<5;failure++){
  IDirect3DDevice9 d;auto before=d;int draws=0;
  FrameHadDuplicatedDraw=false;FrameRightDrawFailed=false;
  DuplicatedDraws=NonWorldDuplicatedDraws=R30SafeTwoEyeDraws=R30ExternalImGuiStereoDraws=R30ExternalImGuiEyeAttempts=0;
  poisons=restoreFailures=fallbacks=0;
  if(failure==1)d.failViewport=1;
  if(failure==4)d.failViewport=2;
  auto hr=R30TryExternalImGuiIndexed(&d,[&](){
   ++draws;
   require(d.viewport.X==0&&d.viewport.Y==0&&d.viewport.Width==2496&&d.viewport.Height==2688,"both F11 eyes must rasterize to XR extent, not 1337x1440 desktop viewport");
   require(d.scissor.left==0&&d.scissor.top==0&&d.scissor.right==2496&&d.scissor.bottom==2688,"scissor follows full eye mapping");
   require(d.target==(draws==1?&leftSurface:&rightSurface),"distinct left and right targets");
   return ((failure==2&&draws==1)||(failure==3&&draws==2))?E_FAIL:0;
  });
  if(failure==0)require(hr==0&&draws==2,"successful stereo submits exactly twice");
  if(failure==1)require(hr==E_NOTIMPL&&draws==0,"left viewport setup failure allows native fallback only before draws");
  if(failure==2)require(hr==E_FAIL&&draws==1,"left draw failure must not duplicate");
  if(failure==3)require(hr!=E_NOTIMPL&&draws==2&&FrameRightDrawFailed,"right draw failure poisons without native replay");
  if(failure==4)require(hr!=E_NOTIMPL&&draws==1,"right viewport failure cannot replay completed left");
  if(failure==0)require(DuplicatedDraws==1&&NonWorldDuplicatedDraws==1&&R30SafeTwoEyeDraws==1&&R30ExternalImGuiStereoDraws==1&&FrameHadDuplicatedDraw,"only successful F11 eye pair increments all stereo counters");
  if(failure>=1)require(DuplicatedDraws==0&&NonWorldDuplicatedDraws==0&&R30SafeTwoEyeDraws==0&&R30ExternalImGuiStereoDraws==0&&!FrameHadDuplicatedDraw,"failed F11 attempt cannot count a binocular success");
  if(failure==3||failure==4)require(R30ExternalImGuiEyeAttempts==1&&poisons==1&&fallbacks==1,"right failure preserves poison and one attempted pair");
  restored(d,before);
 }
 safeBase=false;IDirect3DDevice9 d;int draws=0;require(R30TryExternalImGuiIndexed(&d,[&](){++draws;return 0;})==E_NOTIMPL&&draws==0,"non-stereo path untouched");
 std::puts("PASS actual F11 eye viewport/scissor transaction, L/R failures, restore, native isolation (no HMD claim)");
}
