// Portable execution harness for the ACTUAL R26 R62 core and four dispatchers.
// D3D9 device calls are fakes; this is not a GPU or headset optical test.
#include <atomic>
#include <array>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>
#include <type_traits>
#include <utility>
#include <cstdio>
#define __stdcall
using HRESULT=int; using UINT=unsigned; using INT=int; using DWORD=unsigned;
using D3DPRIMITIVETYPE=int; using D3DFORMAT=int;
constexpr int D3DPT_TRIANGLELIST=4, D3DFMT_UNKNOWN=0,
    D3DFMT_INDEX16=101, D3DFMT_INDEX32=102;
constexpr int D3DRTYPE_TEXTURE=3;
constexpr HRESULT E_NOTIMPL=-1, E_FAIL=-2, E_PENDING=-3, D3D_OK=0;
constexpr int D3DZB_FALSE=0,D3DRS_ZENABLE=7,D3DTS_PROJECTION=3;
constexpr int D3DRS_ALPHABLENDENABLE=27,D3DRS_SRCBLEND=19,D3DRS_DESTBLEND=20;
constexpr int D3DRS_ZWRITEENABLE=14,D3DRS_ALPHATESTENABLE=15,
    D3DRS_COLORWRITEENABLE=168;
constexpr DWORD D3DBLEND_SRCALPHA=5,D3DBLEND_INVSRCALPHA=6;
enum class GameState { STATE_GAME=0, STATE_GOAL=20 };
namespace Game { inline GameState goalState=GameState::STATE_GAME; inline GameState* current_mode=&goalState; }
bool FAILED(HRESULT h){return h<0;} bool SUCCEEDED(HRESULT h){return h>=0;}
struct D3DMATRIX { union {float m[4][4]; struct {float _11,_12,_13,_14,_21,_22,_23,_24,_31,_32,_33,_34,_41,_42,_43,_44;};};};
D3DMATRIX IdentityMatrix(){D3DMATRIX x{};for(int i=0;i<4;++i)x.m[i][i]=1;return x;}
D3DMATRIX MultiplyMatrix(const D3DMATRIX&a,const D3DMATRIX&b){D3DMATRIX c{};for(int i=0;i<4;++i)for(int j=0;j<4;++j)for(int k=0;k<4;++k)c.m[i][j]+=a.m[i][k]*b.m[k][j];return c;}
bool MatrixFinite(const D3DMATRIX&m){for(auto&r:m.m)for(float v:r)if(!std::isfinite(v))return false;return true;}
struct Viewport {DWORD X=0,Y=0,Width=1920,Height=1080;};
namespace OutRunVR::GameSemantic {
enum class RenderScope {None,ScreenHud,World,Projected,ProjectedWorldMarker2D,ScreenOverlay2D};
enum class ProducerToken {None,StageExtensionTime,ResultProgress,Goal,Rank,Lens,RivalMarkerSprani};
struct Command {RenderScope scope=RenderScope::ScreenHud;ProducerToken producer=ProducerToken::StageExtensionTime;bool queued=false;void*queueNode=nullptr;unsigned queueEpoch=0;
bool IsExactFiniteResultHud()const{return scope==RenderScope::ScreenHud&&(producer==ProducerToken::StageExtensionTime||producer==ProducerToken::ResultProgress||producer==ProducerToken::Goal);}};
Command command; unsigned ExternalOverlaySemanticDepth=0;
Command CapturePhysicalDrawCommand(){return command;}
RenderScope EffectiveScope(){return command.scope;}
RenderScope ConsumeForDraw(){return command.scope;}
bool CorroboratesHud(RenderScope s){return s==RenderScope::ScreenHud;}
bool CorroboratesProjectedWorldMarker(RenderScope s){return s==RenderScope::Projected;}
struct ScopedRenderSemantic {explicit ScopedRenderSemantic(RenderScope){}};
ProducerToken CurrentQueueProducerToken(){return command.producer;}
ProducerToken CurrentRenderProducerToken(){return command.producer;}
void*CurrentProjectedMarker(){return nullptr;}
const char*Name(ProducerToken){return "test";}
const char*Name(RenderScope){return "test-scope";}
}
namespace Settings {bool VRTelemetry=true;}
namespace spdlog {template<class...T>void info(T&&...){}}
namespace OutRunVRRenderer {struct LatchedStereoFrame{unsigned poseSequence=7;};bool poseValid=true;bool GetLatchedStereoFrame(LatchedStereoFrame&f){f.poseSequence=7;return poseValid;}}
struct D3DSURFACE_DESC {UINT Width=0,Height=0;D3DFORMAT Format=D3DFMT_UNKNOWN;};
struct IDirect3DBaseTexture9 {int released=0;int GetType(){return D3DRTYPE_TEXTURE;}void Release(){++released;}};
struct IDirect3DTexture9 : IDirect3DBaseTexture9 {HRESULT GetLevelDesc(UINT,D3DSURFACE_DESC*d){*d={64,64,21};return D3D_OK;}};
struct IDirect3DVertexBuffer9 {int released=0;void Release(){++released;}};
struct IDirect3DIndexBuffer9 {int released=0;void Release(){++released;}};
struct IDirect3DSurface9 {int released=0;void Release(){++released;}HRESULT GetDesc(D3DSURFACE_DESC*d){*d={1920,1080,21};return D3D_OK;}};
struct IDirect3DVertexShader9 {int released=0;void Release(){++released;}};
struct IDirect3DDevice9 {
 DWORD fvf=0x142; IDirect3DVertexShader9*vs=nullptr; D3DMATRIX projection=IdentityMatrix();
 int sets=0,failSet=0;bool failVs=false,failFvf=false;std::vector<D3DMATRIX>setMatrices;
 HRESULT GetVertexShader(IDirect3DVertexShader9**s){*s=vs;return failVs?E_FAIL:D3D_OK;}
 HRESULT GetFVF(DWORD*f){*f=fvf;return failFvf?E_FAIL:D3D_OK;}
 HRESULT GetTexture(DWORD,IDirect3DBaseTexture9**t){*t=nullptr;return D3D_OK;}
 HRESULT GetStreamSource(UINT,IDirect3DVertexBuffer9**v,UINT*o,UINT*s){*v=nullptr;*o=0;*s=24;return D3D_OK;}
 HRESULT GetIndices(IDirect3DIndexBuffer9**i){*i=nullptr;return D3D_OK;}
 HRESULT GetRenderTarget(DWORD,IDirect3DSurface9**s){*s=nullptr;return D3D_OK;}
 HRESULT GetRenderState(int state,DWORD*v){if(state==D3DRS_ALPHABLENDENABLE)*v=1;else if(state==D3DRS_SRCBLEND)*v=D3DBLEND_SRCALPHA;else if(state==D3DRS_DESTBLEND)*v=D3DBLEND_INVSRCALPHA;else if(state==D3DRS_COLORWRITEENABLE)*v=0xF;else *v=0;return D3D_OK;}
 HRESULT GetViewport(Viewport*v){*v={};return D3D_OK;}
 HRESULT GetTransform(int,D3DMATRIX*m){*m=projection;return D3D_OK;}
 HRESULT SetTransform(int,const D3DMATRIX*m){++sets;setMatrices.push_back(*m);if(sets==failSet)return E_FAIL;projection=*m;return D3D_OK;}
};
IDirect3DDevice9*gameDevice=nullptr;
IDirect3DSurface9*RightEyeSurface=nullptr;
bool InternalStereoPass=false,backbuffer=true,safeBase=true,R9StereoSeeded=true,FrameStereoIncomplete=false;
unsigned FrameStereoPoseSequence=7; std::atomic<std::uintptr_t>CurrentVertexShaderIdentity{0};
struct {unsigned Width=1920,Height=1080;}BackBufferDesc;
bool IsGameDevice(IDirect3DDevice9*d){return d==gameDevice;}
bool TargetIsBackBuffer(){return backbuffer;}
bool R30SafeStereoBase(IDirect3DDevice9*d){return d==gameDevice&&!InternalStereoPass&&safeBase&&!FrameStereoIncomplete;}
bool EnsureStereoResources(IDirect3DDevice9*){return true;}
struct InternalPassScope {bool old=InternalStereoPass;InternalPassScope(){InternalStereoPass=true;}~InternalPassScope(){InternalStereoPass=old;}};
struct R30XyzrhwState {Viewport viewport;OutRunVRRenderer::LatchedStereoFrame stereo;float eyeScale[2]{},eyeOffset[2]{},projectedDeltaX[2]{},projectedDeltaY[2]{},projectedBaseX=0,projectedBaseY=0;bool depthTestEnabled=false,hudWorldLockValid=true;D3DMATRIX baseProjection=IdentityMatrix();float hudClipX[2][3]{},hudClipY[2][3]{},hudClipW[2][3]{};};
bool configureValid=true;
bool R30BuildEyeAffine(const OutRunVRRenderer::LatchedStereoFrame&,float*,float*){return true;}
bool ReadTrackedRenderState(IDirect3DDevice9*,int,DWORD&v){v=0;return true;}
bool R30ConfigureXyzrhwWorldEffect(IDirect3DDevice9*,const void*,UINT,UINT,R30XyzrhwState&s){for(int e=0;e<2;++e){s.hudClipX[e][0]=0.55f;s.hudClipX[e][2]=e?0.03f:-0.03f;s.hudClipY[e][1]=0.55f;s.hudClipW[e][2]=1;}return configureValid;}
void R30TracePreRestartHudDrawForm(IDirect3DDevice9*,UINT){}
void R30TracePreRestartHudEligibility(IDirect3DDevice9*,UINT){}
void R30BeforeScreenDrawForSkyGlow(IDirect3DDevice9*,OutRunVR::GameSemantic::RenderScope){}
float R30HudScaleValue(){return 0.55f;}float R30HudPlaneViewZ(bool){return -2.5f;}
int currentEye=0,stereoTransactions=0,restoreFailures=0;
void NoteRestoreFailure(const char*){++restoreFailures;FrameStereoIncomplete=true;}
void R30ArmSafeFallback(){FrameStereoIncomplete=true;}
struct R30StereoPassTrace {HRESULT rightTargetHr=0,rightDepthHr=0,rightViewportHr=0;bool restoreOk=true;};
// The unchanged outer transaction has its own GPU integration tests. Emulate
// its left HRESULT/right failure poisoning contract, never replay a failed eye.
template<class L,class R>HRESULT R30ExecuteXyzrhwStereo(IDirect3DDevice9*,const R30XyzrhwState&,L l,R r,const char*,R30StereoPassTrace*,const bool* = nullptr){++stereoTransactions;currentEye=0;auto h=l();if(FAILED(h)){FrameStereoIncomplete=true;return h;}currentEye=1;if(FAILED(r()))FrameStereoIncomplete=true;currentEye=0;return h;}
struct Receipt{int api,eye;std::vector<std::uintptr_t>args;};std::vector<Receipt>receipts;int failEye=-1;
template<class T>std::uintptr_t arg(T v){if constexpr(std::is_pointer_v<T>)return reinterpret_cast<std::uintptr_t>(v);else return static_cast<std::uintptr_t>(v);}
struct Hook{int api;template<class R,class...A>R stdcall(A...a){receipts.push_back({api,currentEye,{arg(a)...}});return currentEye==failEye?E_FAIL:D3D_OK;}};
Hook DrawPrimitiveHook{0},DrawIndexedPrimitiveHook{1},DrawPrimitiveUPHook{2},DrawIndexedPrimitiveUPHook{3};
Hook R30DrawPrimitiveR29Hook{10},R30DrawIndexedPrimitiveR29Hook{11},R30DrawPrimitiveUPR29Hook{12},R30DrawIndexedPrimitiveUPR29Hook{13};
template<class...T>HRESULT R30TryXyzrhwPrimitiveVB(T...){return E_NOTIMPL;}
template<class...T>HRESULT R30TryXyzrhwIndexedPrimitiveVB(T...){return E_NOTIMPL;}
template<class...T>HRESULT R30TryXyzrhwPrimitiveUP(T...){return E_NOTIMPL;}
template<class...T>HRESULT R30TryXyzrhwIndexedPrimitiveUP(T...){return E_NOTIMPL;}
template<class...T>HRESULT R30TryExternalImGuiIndexed(T...){return E_NOTIMPL;}
template<class A,class B>HRESULT R30GuardScreenSpace(IDirect3DDevice9*,A,B b,const char*){return b();}
unsigned TopLevelDrawSerial(){return 1;}
bool R30IsExactResultHudDraw(){return OutRunVR::GameSemantic::command.IsExactFiniteResultHud();}
// @ACTUAL_R26_SOURCE@
void reset(IDirect3DDevice9&d){d={};gameDevice=&d;receipts.clear();stereoTransactions=0;restoreFailures=0;currentEye=0;failEye=-1;FrameStereoIncomplete=false;InternalStereoPass=false;backbuffer=true;safeBase=true;configureValid=true;FrameStereoPoseSequence=7;OutRunVRRenderer::poseValid=true;CurrentVertexShaderIdentity=0;OutRunVR::GameSemantic::command={};OutRunVR::GameSemantic::ExternalOverlaySemanticDepth=0;Game::goalState=GameState::STATE_GAME;}
float vertices[24]{};std::uint16_t indices[6]{};
HRESULT call(int api,IDirect3DDevice9&d,UINT stride=24,D3DFORMAT fmt=D3DFMT_INDEX16){switch(api){case 0:return DrawPrimitiveDestR30(&d,4,11,2);case 1:return DrawIndexedPrimitiveDestR30(&d,4,9,3,8,7,2);case 2:return DrawPrimitiveUPDestR30(&d,4,2,vertices,stride);default:return DrawIndexedPrimitiveUPDestR30(&d,4,3,8,2,indices,fmt,vertices,stride);}}
int main(){using namespace OutRunVR::GameSemantic;IDirect3DDevice9 d;int node=1;
for(int api=0;api<4;++api)for(bool queued:{false,true}){
 reset(d);command.queued=queued;command.queueNode=queued?&node:nullptr;command.queueEpoch=queued?19:0;
 CurrentVertexShaderIdentity=123; // live-null shader wins for exact +TIME
 assert(call(api,d)==D3D_OK);assert(stereoTransactions==1);assert(receipts.size()==2);
 assert(receipts[0].api==api&&receipts[1].api==api);assert(receipts[0].eye==0&&receipts[1].eye==1);
 assert(receipts[0].args==receipts[1].args);assert(d.sets==3);
 assert(d.setMatrices[0]._41!=d.setMatrices[1]._41);auto id=IdentityMatrix();assert(std::memcmp(&d.projection,&id,sizeof(id))==0);
 // Exact original arguments must survive, including base/min/start indices.
 std::vector<std::uintptr_t> expected;
 if(api==0)expected={arg(&d),4,11,2};
 if(api==1)expected={arg(&d),4,9,3,8,7,2};
 if(api==2)expected={arg(&d),4,2,arg(vertices),24};
 if(api==3)expected={arg(&d),4,3,8,2,arg(indices),101,arg(vertices),24};
 assert(receipts[0].args==expected);
}
for(int api:{0,2,3}){
 // Foreign producers and malformed queued owners must retain original route.
 for(auto p:{ProducerToken::None,ProducerToken::Goal,ProducerToken::Rank,ProducerToken::Lens}){reset(d);command.producer=p;call(api,d);assert(stereoTransactions==0&&receipts.size()==1&&receipts[0].api==api+10);}
 for(int bad=0;bad<10;++bad){reset(d);IDirect3DVertexShader9 shader;
 switch(bad){case 0:command.queued=true;command.queueEpoch=1;break;case 1:command.queued=true;command.queueNode=&node;break;case 2:ExternalOverlaySemanticDepth=1;break;case 3:command.scope=RenderScope::World;break;case 4:d.vs=&shader;break;case 5:d.fvf=0x144;break;case 6:backbuffer=false;break;case 7:OutRunVRRenderer::poseValid=false;break;case 8:FrameStereoPoseSequence=8;break;case 9:configureValid=false;break;}
 call(api,d);assert(stereoTransactions==0&&receipts.size()==1&&d.sets==0);if(bad==4)assert(shader.released==1);
 }
 for(int eye:{0,1}){reset(d);failEye=eye;auto hr=call(api,d);assert(FrameStereoIncomplete);assert(receipts.size()==unsigned(eye+1));assert(stereoTransactions==1);assert(hr==(eye?D3D_OK:E_FAIL));assert(d.sets==eye+2);}
 for(int set:{1,2,3}){reset(d);d.failSet=set;auto hr=call(api,d);assert(FrameStereoIncomplete);assert(stereoTransactions==1);const unsigned expectedReceipts=set==1?1u:unsigned(set-1);assert(receipts.size()==expectedReceipts);if(set==1)assert(receipts[0].api==api+10);if(set==3)assert(hr==E_FAIL&&restoreFailures==1);}
}
for(int api:{2,3}){reset(d);call(api,d,23);assert(stereoTransactions==0&&receipts.size()==1);}
reset(d);call(3,d,24,999);assert(stereoTransactions==0&&receipts.size()==1);
reset(d);call(3,d,24,D3DFMT_INDEX32);assert(stereoTransactions==1&&receipts[0].args[6]==102);
// Existing indexed GOAL and projected rank admission remains intact.
for(auto p:{ProducerToken::Goal,ProducerToken::Rank}){reset(d);command.producer=p;if(p==ProducerToken::Rank)command.scope=RenderScope::Projected;call(1,d);assert(stereoTransactions==1&&receipts.size()==2);}
std::puts("R26 +TIME actual-source four-API dispatch, provenance and failure tests PASS");}
