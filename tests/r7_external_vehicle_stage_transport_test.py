"""Compile the actual R7 A1/A2/A3 stage, attachment and transport functions.
D3D9 and GpuOwner are fault-injected mocks; Windows CI compiles the real GPU mesh owner.
"""
from pathlib import Path
import subprocess
import tempfile

root=Path(__file__).resolve().parent.parent
r7=(root/"src/vr/d3d9/stereo_renderer_r7.inc").read_text()
gpu=(root/"src/vr/game/dino_external_d3d9.hpp").read_text()
precommit=(root/"src/vr/game/external_car_atomic_precommit.hpp").read_text()
assert "return false;" in precommit[precommit.index("RuntimeExternalCarAtomicStageReady()"):]
a=r7.index("enum class R7CandidateSeedResult")
seed=r7[a:r7.index("// A successful seed is ONLY",a)]
a=r7.index("struct R7StagedTransfer")
transfer=r7[a:r7.index("bool ResolveDirectTransport(",a)]
a=r7.index("OutRunVR::DinoSidecar::IsolatedStageResult StageExternalVehiclePair(")
stage=r7[a:r7.index("const char* NativeVehicleReplacementBlockReason()",a)]
a=r7.index("const char* NativeVehicleReplacementBlockReason()",a)
native_api=r7[a:r7.index("void R7SetDirectResetRasterOwner(",a)]
a=r7.index("bool R7NativeStockOnlyDraw()")
native_omit=r7[a:r7.index("template<class DrawCall>",a)]
a=gpu.index("enum class IsolatedMeshPass")
types=gpu[a:gpu.index("class GpuOwner",a)]
stub=r'''
#include <cassert>
#include <atomic>
#include <cstdint>
#include <cstring>
#include <iostream>
#include "src/vr/game/external_car_native_stock_replay.hpp"
#include "src/vr/game/external_car_eye_transform_proof.hpp"
using HRESULT=int;using UINT=unsigned;using DWORD=unsigned;
constexpr HRESULT S_OK=0,E_FAIL=-1,D3DERR_NOTFOUND=-2;
constexpr int D3DPT_TRIANGLELIST=4,D3DISSUE_END=1;
bool SUCCEEDED(HRESULT hr){return hr>=0;} bool FAILED(HRESULT hr){return hr<0;}
enum D3DTEXTUREFILTERTYPE {D3DTEXF_NONE,D3DTEXF_LINEAR};
struct RECT {int left=0,top=0,right=800,bottom=600;};
struct D3DVIEWPORT9 {UINT X=0,Y=0,Width=800,Height=600;};
struct D3DMATRIX {float m[4][4]{};};
bool MatrixFinite(const D3DMATRIX& m){for(auto& row:m.m)for(float f:row)if(!std::isfinite(f))return false;return true;}
D3DMATRIX MultiplyMatrix(const D3DMATRIX& a,const D3DMATRIX& b){
    D3DMATRIX m{};for(unsigned i=0;i<4;++i)for(unsigned j=0;j<4;++j)for(unsigned k=0;k<4;++k)m.m[i][j]+=a.m[i][k]*b.m[k][j];return m;
}
D3DMATRIX ProjectionFromFov(const D3DMATRIX& base,int fov){auto m=base;m.m[2][0]=float(fov);return m;}
struct IDirect3DSurface9 {unsigned refs=0,draws=0,pixels=0;void Release(){assert(refs);--refs;}};
template<class T>void ReleaseCom(T*& p){if(p){p->Release();p=nullptr;}}
struct IDirect3DDevice9 {
    IDirect3DSurface9 *rt=nullptr,*depth=nullptr;
    D3DVIEWPORT9 vp{};RECT scissor{};
    HRESULT GetRenderTarget(UINT slot,IDirect3DSurface9** p){*p=slot?nullptr:rt;if(*p)++(*p)->refs;return *p?S_OK:D3DERR_NOTFOUND;}
    HRESULT GetDepthStencilSurface(IDirect3DSurface9** p){*p=depth;if(*p)++(*p)->refs;return *p?S_OK:D3DERR_NOTFOUND;}
    HRESULT GetViewport(D3DVIEWPORT9* out){*out=vp;return S_OK;}
    HRESULT GetScissorRect(RECT* out){*out=scissor;return S_OK;}
    HRESULT SetViewport(const D3DVIEWPORT9* v){vp=*v;return S_OK;}
    HRESULT SetScissorRect(const RECT* r){scissor=*r;return S_OK;}
};
struct R7AtomicCandidatePair {
    struct Eye {IDirect3DSurface9 *color=nullptr,*depth=nullptr;} eyes[2]{};
    IDirect3DSurface9* provenLiveColor[2]{};
    IDirect3DSurface9* provenLiveDepth[2]{};
    IDirect3DDevice9* device=nullptr;
    struct {UINT Width=800,Height=600;} colorDesc;
    UINT simultaneousTargets=1;std::uint64_t generation=1;
} ExternalAtomicCandidates;
std::uint64_t PresentEpoch=9,ExternalAtomicReplayEpoch=9,R7CandidateBoundarySerial=0,FrameStereoPoseSequence=7,DirectTransportGeneration=4;
bool FrameStereoIncomplete=false,FrameRightDrawFailed=false,R7CandidateResetInFlight=false,InternalStereoPass=false,R7VehicleStageInFlight=false,DirectTransportResourcesReady=true;
struct {bool valid=true;std::uint32_t poseSequence=7;int eyeFov[2]{-1,1};} FrameStereoMetadata;
using NativeEyeMatrices=float[2][16];
NativeEyeMatrices nativeEyes{};
bool nativeEyesAvailable=true;
const NativeEyeMatrices* GetQuestNativeEyePairForPresent(std::uint32_t pose){
    return nativeEyesAvailable&&pose==FrameStereoPoseSequence?&nativeEyes:nullptr;
}
std::atomic<bool> OcclusionQueryTrackingUnavailable{false},StereoBaseCallbacksArmed{true};std::atomic<unsigned> ActiveOcclusionQueries{0};
bool R7CandidatePresentBoundaryCovered=true,R7CandidateResetBoundaryCovered=true;
namespace Settings {bool VRExternalFerrariTest=true,VRF50ExternalModel=false,VRDirectGpuOnly=true;}
bool HostDirectTransportReady(){return true;}
IDirect3DSurface9 *BackBuffer=nullptr,*TrackedRenderTarget=nullptr,*TrackedDepthStencil=nullptr,*RightEyeSurface=nullptr,*RightEyeDepth=nullptr;
struct Stamp {unsigned invalidated=0;void Invalidate(){++invalidated;}} LastMainDepthClearStamp;
bool RightDepthSynchronized=true,RightStencilSynchronized=true;
unsigned restoreErrors=0,rawCalls=0,rawFail=0,rawReset=0,rawPresent=0,copyCalls=0,copyFail=0,fenceCalls=0,fenceRevoke=0;
bool nativeValid=true,allowPublication=true,overlayDirty=false,overlayGlass=false,publishValid=true;
unsigned stageTags[16]{},stageTagCount=0;
bool IsGameDevice(IDirect3DDevice9* d){return d&&d==ExternalAtomicCandidates.device;}
bool GameplayActive(){return true;}
bool AnyAuxRenderTargetActive(){return false;}
bool TargetIsBackBuffer(){return BackBuffer&&TrackedRenderTarget==BackBuffer;}
void NoteRestoreFailure(const char*){++restoreErrors;}
struct InternalPassScope {bool old=InternalStereoPass;InternalPassScope(){InternalStereoPass=true;}~InternalPassScope(){InternalStereoPass=old;}};
struct RtHook {
    explicit operator bool()const{return true;}
    template<class H>H stdcall(IDirect3DDevice9* d,UINT,IDirect3DSurface9* s){assert(InternalStereoPass);d->rt=s;return S_OK;}
} SetRenderTargetHook;
struct DepthHook {
    explicit operator bool()const{return true;}
    template<class H>H stdcall(IDirect3DDevice9* d,IDirect3DSurface9* s){assert(InternalStereoPass);d->depth=s;return S_OK;}
} SetDepthStencilSurfaceHook;
struct DrawHook {
    explicit operator bool()const{return true;}
    template<class H>H stdcall(IDirect3DDevice9* d,int,int,UINT,UINT,UINT,UINT){
        assert(InternalStereoPass);
        auto& p=ExternalAtomicCandidates;
        assert((d->rt==p.eyes[0].color&&d->depth==p.eyes[0].depth)||
               (d->rt==p.eyes[1].color&&d->depth==p.eyes[1].depth));
        ++rawCalls;
        if(rawCalls==rawReset){++p.generation;p.device=nullptr;return E_FAIL;}
        if(rawCalls==rawPresent){++R7CandidateBoundarySerial;return E_FAIL;}
        if(rawCalls==rawFail)return E_FAIL;
        ++d->rt->draws;++d->depth->draws;return S_OK;
    }
} DrawIndexedPrimitiveHook;
struct StretchHook {
    template<class H>H stdcall(IDirect3DDevice9*,IDirect3DSurface9* s,const RECT*,IDirect3DSurface9* dst,const RECT*,D3DTEXTUREFILTERTYPE){
        assert(s&&dst);++copyCalls;if(copyCalls==copyFail)return E_FAIL;dst->pixels=s->pixels;return S_OK;
    }
} StretchRectHook;
struct Event {HRESULT Issue(DWORD){++fenceCalls;if(fenceRevoke)ExternalAtomicReplayEpoch=0;return S_OK;}};
struct DirectTransportSlot {IDirect3DSurface9 *leftSurface=nullptr,*rightSurface=nullptr;Event* fence=nullptr;bool published=false,producerPending=false;OutRunVR::DinoSidecar::IsolatedVehicleKey nativeVehicle{};};
void R7ReportNativePair(const OutRunVR::DinoSidecar::IsolatedVehicleKey&,const char*,HRESULT){}
namespace OutRunVR::State::StateBlockTracker {bool Recording(){return false;}}
namespace OutRunVR::DinoSidecar {
    enum class FerrariModelSlot : unsigned char {F50,GenericId};
    struct DashboardTelemetry {};
    struct MeshDrawReceipt {bool stateMayBeDirty=false;};
    bool RuntimeExternalCarAtomicStageReady(){return allowPublication;}
'''
gpu_stub=r'''
    struct MockGpu {
        unsigned count=3;bool dashboard=false;
        bool HasGlassMeshes(){return dashboard?overlayGlass:true;}
        bool SelectionMatches(FerrariModelSlot,unsigned char){return true;}
        bool ReadyForCandidateSeed(IDirect3DDevice9*,FerrariModelSlot,unsigned char) const {return true;}
        unsigned HasEmbeddedSpeedAndRpm(){return 0;}unsigned EmbeddedGearMask(){return 0;}
        GpuDrawResult DrawNativeScene(IDirect3DDevice9* d,const D3DMATRIX&,const D3DMATRIX& view,const D3DMATRIX& projection,const DashboardTelemetry&,unsigned,std::uint64_t,std::uint64_t,unsigned,const IsolatedEyeRaster* raster,IsolatedMeshPass phase=IsolatedMeshPass::All){
            GpuDrawResult r{};
            const bool right=d->rt==ExternalAtomicCandidates.eyes[1].color;
            assert(view.m[3][0]==(right?0.06f:0.f));
            assert(projection.m[2][0]==(right?1.f:-1.f));
            const unsigned draws=phase==IsolatedMeshPass::All?count:
                phase==IsolatedMeshPass::OpaqueOnly?count-1:1;
            for(unsigned i=0;i<draws;++i){
                assert(stageTagCount<16);
                stageTags[stageTagCount++]=dashboard?1u:phase==IsolatedMeshPass::GlassOnly?2u:0u;
                if(!raster->Current()||FAILED(raster->draw(raster->context,3,1))) {
                    r.receipt.stateMayBeDirty=!raster->Restorable();return r;
                }
            }
            r.receipt.stateMayBeDirty=(dashboard&&overlayDirty)||!raster->Restorable();
            r.isolatedEyeComplete=!r.receipt.stateMayBeDirty&&raster->Current();
            return r;
        }
    };
    MockGpu& GlobalGpu(){static MockGpu g{3,false};return g;}
    MockGpu& GlobalDashboardGpu(){static MockGpu g{2,true};return g;}
}
OutRunVR::DinoSidecar::IsolatedVehicleKey R7StagedVehicle{},R7NativeCompletedVehicle{};
OutRunVR::DinoSidecar::ExternalVehicleStageInput R7NativePublicationInput{};
'''
cases=r'''
using namespace OutRunVR::DinoSidecar;
struct Fixture {
    IDirect3DDevice9 d;IDirect3DSurface9 stock[2],stockZ[2],priv[2],privZ[2],output[2];Event event;
    DirectTransportSlot slot{&output[0],&output[1],&event,false,false};
    ExternalVehicleStageInput input{};
    Fixture(){
        ExternalAtomicCandidates={};ExternalAtomicCandidates.device=&d;
        for(unsigned i=0;i<2;++i){
            ExternalAtomicCandidates.eyes[i]={&priv[i],&privZ[i]};
            ExternalAtomicCandidates.provenLiveColor[i]=&stock[i];
            ExternalAtomicCandidates.provenLiveDepth[i]=&stockZ[i];
            stock[i].pixels=1;priv[i].pixels=2;
            for(unsigned j=0;j<16;++j)nativeEyes[i][j]=0.f;
            for(unsigned j=0;j<4;++j)nativeEyes[i][j*5]=1.f;
        }
        for(unsigned j=0;j<4;++j){input.world.m[j][j]=1;input.centerView.m[j][j]=1;input.centerProjection.m[j][j]=1;}
        nativeEyes[1][12]=0.06f;nativeEyesAvailable=true;
        BackBuffer=TrackedRenderTarget=d.rt=&stock[0];TrackedDepthStencil=d.depth=&stockZ[0];
        RightEyeSurface=&stock[1];RightEyeDepth=&stockZ[1];
        PresentEpoch=ExternalAtomicReplayEpoch=9;R7CandidateBoundarySerial=0;FrameStereoPoseSequence=7;R7StagedVehicle={};
        FrameStereoIncomplete=FrameRightDrawFailed=R7CandidateResetInFlight=InternalStereoPass=R7VehicleStageInFlight=false;
        FrameStereoMetadata.valid=true;FrameStereoMetadata.poseSequence=7;DirectTransportResourcesReady=true;
        rawCalls=rawFail=rawReset=rawPresent=copyCalls=copyFail=fenceCalls=fenceRevoke=restoreErrors=0;
        nativeValid=allowPublication=publishValid=true;overlayDirty=overlayGlass=false;stageTagCount=0;R7NativePublicationInput={};
        NativeVehicleModelEdgesReady=true;NativeVehiclePmtConsumerReady=true;R7NativeCompletedVehicle={};
        input.nativeFrame=12;input.pose=7;input.player=55;input.includeDashboard=true;
        input.nativeCurrent=[](const ExternalVehicleStageInput&) noexcept {return nativeValid;};
        input.publishCurrent=[](const ExternalVehicleStageInput&) noexcept {return publishValid;};
    }
    IsolatedStageResult Stage(){
        const auto r=StageExternalVehiclePair(&d,input);
        R7NativeCompletedVehicle=(r==IsolatedStageResult::Complete&&allowPublication)?R7StagedVehicle:IsolatedVehicleKey{};
        R7NativePublicationInput=input;
        return r;
    }
    IsolatedStageResult NativeStage(unsigned fault=0){
        NativeVehicleStockReplay receipt{};
        if(!BeginNativeVehicleReplacement(&d,input,receipt))return IsolatedStageResult::Unavailable;
        receipt.model=2;
        {
            ScopedNativeVehicleStockReplay owner(receipt);
            for(unsigned group=1;group<=3;++group){
                receipt.Open(true);
                {
                    ScopedNativeVehiclePhysical p(receipt.OwnsObject(0x30000u|(group==1?0x11u:group==2?0u:1u))&&!(fault==1&&group==2));
                    for(unsigned eye=0;eye<2;++eye){
                        if(R7NativeStockOnlyDraw()&&!(fault==2&&group==2&&eye==1))
                            R7RecordNativeStockOmission(eye,R7CandidateSeedResult::Seeded);
                        ++stock[eye].draws;++stockZ[eye].draws;
                    }
                }
                receipt.Close(true);
            }
        }
        if(fault==3)++R7CandidateBoundarySerial;
        return FinishNativeVehicleReplacement(&d,input,receipt);
    }
    R7StagedTransfer Transfer(){return R7TransferStagedVehicle(&d,slot,&stock[0],&stock[1],D3DTEXF_NONE);}
    void LiveUnchanged(){assert(!stock[0].draws&&!stock[1].draws&&!stockZ[0].draws&&!stockZ[1].draws);}
    void Restored(){assert(d.rt==&stock[0]&&d.depth==&stockZ[0]&&!InternalStereoPass&&!R7VehicleStageInFlight);}
    ~Fixture(){for(unsigned i=0;i<2;++i)assert(!stock[i].refs&&!stockZ[i].refs&&!priv[i].refs&&!privZ[i].refs);}
};
int main(){
    unsigned cases=0;
    {Fixture f;assert(f.Stage()==IsolatedStageResult::Complete&&rawCalls==10);
     assert(f.priv[0].draws==5&&f.priv[1].draws==5&&f.privZ[0].draws==5&&f.privZ[1].draws==5);
     const unsigned order[]{0,0,1,1,2,0,0,1,1,2};
     assert(stageTagCount==10&&std::memcmp(stageTags,order,sizeof(order))==0);
     f.LiveUnchanged();f.Restored();auto t=f.Transfer();assert(t.handled&&SUCCEEDED(t.hr)&&!t.copyFailed&&f.output[0].pixels==2&&f.output[1].pixels==2&&fenceCalls==1&&f.slot.nativeVehicle.Same(R7NativeCompletedVehicle));++cases;}
    for(unsigned failure=1;failure<=10;++failure)for(unsigned mode=0;mode<3;++mode){
        Fixture f;if(mode==0)rawFail=failure;if(mode==1)rawReset=failure;if(mode==2)rawPresent=failure;
        const auto r=f.Stage();assert(r!=IsolatedStageResult::Complete&&rawCalls==failure&&!ExternalAtomicReplayEpoch);
        if(mode!=1)f.Restored();
        if(mode==1)assert(r==IsolatedStageResult::DirtyRestore&&restoreErrors==1);
        f.LiveUnchanged();assert(!f.Transfer().handled&&!fenceCalls);++cases;
    }
    {Fixture f;overlayDirty=true;assert(f.Stage()==IsolatedStageResult::DirtyRestore&&rawCalls==4&&restoreErrors==1);f.Restored();++cases;}
    {Fixture f;assert(f.Stage()==IsolatedStageResult::Complete);assert(f.Stage()==IsolatedStageResult::Unavailable&&rawCalls==10&&!f.Transfer().handled);++cases;}
    {Fixture f;assert(f.Stage()==IsolatedStageResult::Complete);allowPublication=false;R7NativeCompletedVehicle={};assert(!f.Transfer().handled&&!copyCalls);++cases;}
    for(unsigned fault=1;fault<=2;++fault){
        Fixture f;assert(f.Stage()==IsolatedStageResult::Complete);copyFail=fault;
        auto t=f.Transfer();assert(t.handled&&SUCCEEDED(t.hr)&&f.output[0].pixels==1&&f.output[1].pixels==1&&fenceCalls==1&&!f.slot.nativeVehicle.Same(f.slot.nativeVehicle));
        f.LiveUnchanged();++cases;
    }
    {Fixture f;assert(f.Stage()==IsolatedStageResult::Complete);fenceRevoke=1;auto t=f.Transfer();assert(t.handled&&FAILED(t.hr)&&!t.copyFailed&&fenceCalls==1);++cases;}
    {Fixture f;overlayGlass=true;assert(f.Stage()==IsolatedStageResult::Unavailable&&!rawCalls);++cases;}
    {Fixture f;f.input.includeDashboard=false;assert(f.Stage()==IsolatedStageResult::Complete&&rawCalls==6);++cases;}
    {Fixture f;assert(f.NativeStage()==IsolatedStageResult::Complete);publishValid=false;
     assert(!f.Transfer().handled&&!copyCalls);++cases;}
    {Fixture f;assert(f.NativeStage()==IsolatedStageResult::Complete);R7NativePublicationInput.nativeFrame++;
     assert(!f.Transfer().handled&&!copyCalls);++cases;}
    {Fixture f;assert(f.NativeStage()==IsolatedStageResult::Complete);FrameStereoMetadata.valid=false;
     assert(!f.Transfer().handled&&!copyCalls);++cases;}
    {Fixture f;nativeEyes[1][12]=0.f;assert(f.Stage()==IsolatedStageResult::Unavailable&&!rawCalls);++cases;}
    {Fixture f;nativeEyesAvailable=false;assert(f.Stage()==IsolatedStageResult::Unavailable&&!rawCalls);++cases;}
    {Fixture f;FrameStereoMetadata.poseSequence=8;assert(f.Stage()==IsolatedStageResult::Unavailable&&!rawCalls);++cases;}
    // Actual A4 begin/finish and stock-only decision with A2/A3.
    for(unsigned fault=0;fault<=3;++fault){
        Fixture f;const auto r=f.NativeStage(fault);
        assert(f.stock[0].draws==3&&f.stock[1].draws==3);
        if(fault==0){
            assert(r==IsolatedStageResult::Complete&&rawCalls==10);
            auto t=f.Transfer();assert(t.handled&&SUCCEEDED(t.hr)&&f.output[0].pixels==2&&f.output[1].pixels==2);
            RetireRepeatedNativeVehicle(f.input.player);
            assert(!f.Transfer().handled&&!ExternalAtomicReplayEpoch);
        }else{
            assert(r==IsolatedStageResult::Unavailable&&!rawCalls&&!f.Transfer().handled);
        }
        ++cases;
    }
    {Fixture f;NativeVehiclePmtConsumerReady=false;assert(std::strcmp(NativeVehicleReplacementBlockReason(),"NATIVE_PMT_CONSUMER_MISSING")==0);assert(f.NativeStage()==IsolatedStageResult::Unavailable&&!rawCalls);++cases;}
    {Fixture f;assert(NativeVehicleReplacementBlockReason()==nullptr);ExternalAtomicReplayEpoch=0;
     assert(std::strcmp(NativeVehicleReplacementBlockReason(),"PRIVATE_SCENE_NOT_SEEDED_OR_REVOKED")==0);
     assert(f.NativeStage()==IsolatedStageResult::Unavailable&&!rawCalls);++cases;}
    {Fixture f;assert(f.NativeStage()==IsolatedStageResult::Complete);assert(f.Transfer().handled&&f.slot.nativeVehicle.Same(R7NativeCompletedVehicle));
     ExternalAtomicReplayEpoch=0;assert(!f.Transfer().handled&&!f.slot.nativeVehicle.Same(f.slot.nativeVehicle));++cases;}
    std::cout<<"R7_ACTUAL_ISOLATED_STAGE_TRANSPORT_PASS "<<cases<<"\n";
}
'''
with tempfile.TemporaryDirectory() as temp:
    cpp=Path(temp)/"stage.cpp";exe=Path(temp)/"stage"
    cpp.write_text(stub+types+gpu_stub+seed+native_omit+transfer+stage+native_api+cases)
    subprocess.run(["g++","-std=c++17","-O2","-Wall","-Wextra","-Werror","-pedantic","-I",str(root),str(cpp),"-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
