#pragma once
// OutRun 2006 Dino sidecar D3D9 resources. Independent of native PMT/XPR.
// Caller supplies separately verified stereo eye world/view/projection and targets.
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <d3d9.h>
#include <algorithm>
#include <cstring>
#include <cwchar>
#include <cmath>
#include <iterator>
#include <future>
#include <chrono>
#include <string>
#include <vector>
#include "dino_external_sidecar.hpp"
#include "external_car_ground.hpp"
#include "external_car_draw_order.hpp"
#include "external_car_selection.hpp"
#include "external_car_runtime_policy.hpp"
#include "dino_external_original_car_gate.hpp"
#include "dino_external_pbr_shader.hpp"
#include "external_car_stereo_receipt.hpp"
#include "render_semantics.hpp"

namespace OutRunVR::DinoSidecar {
// Fixed-function test must be explicitly enabled by the launch process;
// generic PBR's c0/c4/c8 matrices are not compatible with verified c64 stereo.
inline bool FixedFunctionExternalStereoProbeActive() noexcept {
    wchar_t flag[4]{};
    return GetEnvironmentVariableW(
        L"OUTRUN_VR_EXTERNAL_FIXED_FUNCTION_TEST",flag,4)==1 &&
        flag[0]==L'1' && flag[1]==L'\0';
}
enum class FerrariModelSlot : unsigned char { F50, Gto288, F40, GenericId };
enum class SidecarRole : unsigned char { Vehicle, DashboardOverlay };
struct GpuDrawResult final {
    HRESULT hr=E_FAIL;
    MeshDrawReceipt receipt{};
};
class GpuOwner final {
    struct GpuMesh {
        IDirect3DVertexBuffer9* vb=nullptr;
        IDirect3DIndexBuffer9* ib=nullptr;
        UINT vertexCount=0,indexCount=0;
        unsigned material=0;
        int dashboardBinding=-1;
        bool glass=false; // sorted transparent sidecar group; never occludes road depth
    };
    Model cpu_{};
    std::vector<GpuMesh> meshes_{};
    std::vector<IDirect3DTexture9*> textures_{};
    std::vector<IDirect3DTexture9*> normals_{},orms_{};
    PbrShaders pbrShaders_{};
    bool pbrReady_=false;
    IDirect3DDevice9* owner_=nullptr; // borrowed, never AddRef
    bool loaded_=false,loadAttempted_=false;
    struct CpuLoad {
        Model model{};
        float lowest=0.f;
        bool parsed=false;
    };
    std::future<CpuLoad> cpuLoad_{};
    enum class Preparation : unsigned char {
        Cold, Reading, CpuReady, Uploading, Ready, Failed
    };
    Preparation preparation_=Preparation::Cold;
    std::size_t nextTexture_=0, nextMesh_=0;
    bool pbrPrepared_=false;
    SidecarRole role_=SidecarRole::Vehicle;
    FerrariModelSlot selectedSlot_=FerrariModelSlot::F50;
    unsigned char selectedCarId_=255u;
    float modelMinLocalY_=0.f;
    bool modelBoundsReady_=false;
    // If D3D9Ex rejects an HQ allocation, do not retry multi-megabyte
    // textures on every eye Draw. Retry only after Reset/device change.
    GpuRetryPolicy gpuRetry_{};
    static bool ReadFile(const wchar_t* path,std::vector<std::uint8_t>& out) {
        HANDLE f=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,
                            FILE_ATTRIBUTE_NORMAL,nullptr);
        if(f==INVALID_HANDLE_VALUE)return false;
        struct FileHandleGuard final {
            HANDLE handle;
            ~FileHandleGuard() noexcept {CloseHandle(handle);}
        } guard{f};
        LARGE_INTEGER size{};
        const bool ok=GetFileSizeEx(f,&size)!=FALSE &&
                      size.QuadPart>=36 &&
                      size.QuadPart<=static_cast<LONGLONG>(MaxSidecarBytes);
        if(!ok)return false;
        std::vector<std::uint8_t> b(static_cast<std::size_t>(size.QuadPart));
        DWORD got=0;
        const bool read=::ReadFile(f,b.data(),static_cast<DWORD>(b.size()),&got,nullptr)!=FALSE &&
                        got==b.size();
        if(!read)return false;
        out=std::move(b);
        return true;
    }
    static bool UploadDDS(IDirect3DDevice9* dev,const Texture& texture,
                          IDirect3DTexture9** out) noexcept {
        if(!dev || !out || texture.dds.size()<128 || !texture.width ||
           !texture.height || !texture.mips)return false;
        *out=nullptr;
        const D3DFORMAT format=texture.format==TextureFormat::DXT1?D3DFMT_DXT1:
            texture.format==TextureFormat::DXT5?D3DFMT_DXT5:D3DFMT_A8R8G8B8;
        const unsigned blockBytes=texture.format==TextureFormat::DXT1?8u:
            texture.format==TextureFormat::DXT5?16u:0u;
        IDirect3DTexture9* staging=nullptr;
        if(FAILED(dev->CreateTexture(texture.width,texture.height,texture.mips,0,
                                     format,D3DPOOL_SYSTEMMEM,&staging,nullptr))||!staging)
            return false;
        std::size_t pos=128;
        for(UINT mip=0;mip<texture.mips;++mip) {
            const unsigned width=(texture.width>>mip)?(texture.width>>mip):1u;
            const unsigned height=(texture.height>>mip)?(texture.height>>mip):1u;
            const unsigned rows=blockBytes?(((height+3u)/4u)?(height+3u)/4u:1u):height;
            const unsigned row=blockBytes?
                (((width+3u)/4u)?(width+3u)/4u:1u)*blockBytes:width*4u;
            if(!Bounds(pos,std::size_t(rows)*row,texture.dds.size())) {
                staging->Release();return false;
            }
            D3DLOCKED_RECT locked{};
            if(FAILED(staging->LockRect(mip,&locked,nullptr,0))) {
                staging->Release();return false;
            }
            if(!locked.pBits || locked.Pitch<static_cast<INT>(row)) {
                staging->UnlockRect(mip);staging->Release();return false;
            }
            for(unsigned y=0;y<rows;++y)
                std::memcpy(static_cast<std::uint8_t*>(locked.pBits)+
                            std::size_t(locked.Pitch)*y,
                            texture.dds.data()+pos+std::size_t(row)*y,row);
            staging->UnlockRect(mip);
            pos+=std::size_t(rows)*row;
        }
        HRESULT hr=dev->CreateTexture(texture.width,texture.height,texture.mips,0,
            format,D3DPOOL_DEFAULT,out,nullptr);
        if(SUCCEEDED(hr) && *out)hr=dev->UpdateTexture(staging,*out);
        staging->Release();
        if(FAILED(hr) || !*out) {
            if(*out) {(*out)->Release();*out=nullptr;}
            return false;
        }
        return true;
    }
    void ReleaseGpu() noexcept {
        for(auto& m:meshes_) {
            if(m.vb)m.vb->Release();
            if(m.ib)m.ib->Release();
        }
        meshes_.clear();
        for(auto& texture:textures_) {if(texture)texture->Release();texture=nullptr;}
        textures_.clear();
        for(auto& t:normals_)if(t)t->Release();
        for(auto& t:orms_)if(t)t->Release();
        normals_.clear();orms_.clear();
        pbrShaders_.Release();
        pbrReady_=false;
        pbrPrepared_=false;
        nextTexture_=nextMesh_=0;
        if(preparation_==Preparation::Uploading ||
           preparation_==Preparation::Ready)
            preparation_=loaded_?Preparation::CpuReady:Preparation::Cold;
        owner_=nullptr;
    }
    bool RejectGpu(IDirect3DDevice9* device) noexcept {
        ReleaseGpu();
        gpuRetry_.NoteFailure(device);
        return false;
    }
    // Diagnostic A/B only: reproduce the known-working single-F50
    // fixed-function stereo route while keeping the exact same V4 OVC body,
    // transforms and normal VR runner. This deliberately ignores normal/ORM
    // maps for the current process; default production behavior stays PBR.
    static bool ForceFixedFunctionStereoProbe() noexcept {
        return FixedFunctionExternalStereoProbeActive();
    }
    // A partial draw is not recoverable by issuing the original vehicle draw
    // in the same eye: those external pixels are already on the target.
    // Stop retries until the real D3D9 Reset, preventing another partial
    // submission in subsequent frames.
    void QuarantineFailedSubmission(IDirect3DDevice9* device) noexcept {
        ReleaseGpu();
        gpuRetry_.NoteFailure(device);
    }
    bool BuildSidecarPath(wchar_t (&path)[MAX_PATH]) const noexcept {
        const DWORD n=GetModuleFileNameW(nullptr,path,MAX_PATH);
        if(n==0 || n>=MAX_PATH)return false;
        wchar_t* last=wcsrchr(path,L'\\');
        if(!last)return false;
        *++last=L'\0';
        // Explicit fixed filename allowlist. No config-controlled arbitrary
        // path, no directory scan, and no unvalidated 'install' marker.
        wchar_t genericSuffix[96]{};
        const wchar_t* suffix=nullptr;
        if(role_==SidecarRole::DashboardOverlay) {
            if(selectedCarId_>=30u)return false;
            const auto canonicalId=CanonicalFerrariExternalCarId(selectedCarId_);
            if(swprintf_s(genericSuffix,_countof(genericSuffix),
                          L"ExternalCars\\Dashboard\\car_id_%02u.ovc",
                          static_cast<unsigned>(canonicalId))<=0)
                return false;
            suffix=genericSuffix;
        } else {
            wchar_t pbrFlag[4]{};
            const bool usePbr=GetEnvironmentVariableW(
                L"OUTRUN_VR_F50_PBR_TEST",pbrFlag,4)==1 &&
                pbrFlag[0]==L'1' && pbrFlag[1]==L'\0';
            constexpr wchar_t stableSuffix[]=L"F50_External_Test.ovc";
            constexpr wchar_t pbrSuffix[]=L"F50_External_Test_PBR.ovc";
            if(selectedSlot_==FerrariModelSlot::Gto288)
            suffix=L"ExternalCars\\288gto.ovc";
        else if(selectedSlot_==FerrariModelSlot::F40)
            suffix=L"ExternalCars\\f40.ovc";
            else if(selectedSlot_==FerrariModelSlot::GenericId) {
                if(selectedCarId_>=30u)return false;
                const auto canonicalId=CanonicalFerrariExternalCarId(selectedCarId_);
                if(swprintf_s(genericSuffix,_countof(genericSuffix),
                              L"ExternalCars\\car_id_%02u.ovc",
                              static_cast<unsigned>(canonicalId))<=0)
                    return false;
                suffix=genericSuffix;
                // Prefer the exact canonical per-car asset for all 16 models.
                // Legacy 288gto.ovc/f40.ovc remains a fallback only if that
                // canonical filename is genuinely absent (not malformed).
                // This path is resolved at cold load, never scanned on GPU.
                if(const wchar_t* legacy=LegacyFerrariCarSuffix(canonicalId)) {
                    wchar_t candidate[MAX_PATH]{};
                    if(std::wcslen(path)+std::wcslen(genericSuffix)+1>MAX_PATH ||
                       wcscpy_s(candidate,MAX_PATH,path)!=0 ||
                       wcscat_s(candidate,MAX_PATH,genericSuffix)!=0)
                        return false;
                    const DWORD attr=GetFileAttributesW(candidate);
                    if(attr==INVALID_FILE_ATTRIBUTES ||
                       (attr&FILE_ATTRIBUTE_DIRECTORY)!=0)
                        suffix=legacy;
                }
            } else
                suffix=usePbr?pbrSuffix:stableSuffix;
        }
        if(std::wcslen(path)+std::wcslen(suffix)+1>MAX_PATH)return false;
        return wcscat_s(path,MAX_PATH,suffix)==0;
    }
    bool EnsureLoaded() {
        if(loaded_)return true;
        if(!loadAttempted_) {
            loadAttempted_=true;
            wchar_t path[MAX_PATH]{};
            if(!BuildSidecarPath(path)) {
                preparation_=Preparation::Failed;
                return false;
            }
            // Run file IO, CRC and parsing away from the native player Draw.
            // Worker accesses only local path/model values, never live game
            // state or D3D9 device resources.
            const std::wstring pathCopy(path);
            cpuLoad_=std::async(std::launch::async,[pathCopy]() -> CpuLoad {
                CpuLoad result{};
                try {
                    std::vector<std::uint8_t> bytes;
                    if(!ReadFile(pathCopy.c_str(),bytes))return result;
                    std::string error;
                    if(!Parse(bytes.data(),bytes.size(),result.model,error))
                        return result;
                    float lowest=10000.f;
                    for(const auto& mesh:result.model.meshes)
                        for(const auto& vertex:mesh.vertices)
                            lowest=(std::min)(lowest,vertex.y);
                    result.lowest=lowest;
                    result.parsed=true;
                } catch(...) {
                    result.parsed=false;
                }
                return result;
            });
            preparation_=Preparation::Reading;
            return false;
        }
        if(!cpuLoad_.valid())return false;
        if(cpuLoad_.wait_for(std::chrono::seconds(0)) !=
           std::future_status::ready)
            return false;
        CpuLoad result=cpuLoad_.get();
        if(!result.parsed) {
            preparation_=Preparation::Failed;
            return false;
        }
        if(role_==SidecarRole::Vehicle) {
            float validatedLift=0.f;
            if(!ComputeExternalFloorLift(0.22f,result.lowest,validatedLift)) {
                preparation_=Preparation::Failed;
                return false;
            }
        } else if(!std::isfinite(result.lowest) ||
                  result.lowest < -10.f || result.lowest > 10.f) {
            preparation_=Preparation::Failed;
            return false;
        }
        modelMinLocalY_=result.lowest;
        modelBoundsReady_=true;
        cpu_=std::move(result.model);
        loaded_=true;
        preparation_=Preparation::CpuReady;
        return true;
    }
    bool EnsureGpu(IDirect3DDevice9* dev) {
        if(!dev || !EnsureLoaded())return false;
        if(!gpuRetry_.CanAttempt(dev))return false;
        if(owner_==dev && preparation_==Preparation::Ready)return true;
        if(owner_!=dev) {
            ReleaseGpu();
            owner_=dev;
            // Preallocate before any COM allocation: no failure may strand a
            // GPU mesh outside the owned vector.
            meshes_.reserve(cpu_.meshes.size());
            textures_.resize(cpu_.textures.size(),nullptr);
            preparation_=Preparation::Uploading;
        }
        // The original car stays active until the LAST upload succeeds.
        // Keep each frame's preparation to one DDS or one mesh allocation.
        if(nextTexture_<cpu_.textures.size()) {
            const auto material=nextTexture_++;
            if(!UploadDDS(dev,cpu_.textures[material],&textures_[material]))
                return RejectGpu(dev);
            return false;
        }
        // Optional PBR allocations must never prevent a working legacy draw.
        // On any map/shader failure fall back to textured fixed-function once
        // per device generation, not once per eye/frame.
        const bool fixedFunctionStereoProbe=
            ForceFixedFunctionStereoProbe();
        if(!pbrPrepared_ && cpu_.pbrEnabled && !fixedFunctionStereoProbe) {
            normals_.resize(cpu_.pbrMaterials.size(),nullptr);
            orms_.resize(cpu_.pbrMaterials.size(),nullptr);
            bool mapsReady=true;
            for(std::size_t i=0;i<cpu_.pbrMaterials.size();++i) {
                const auto& p=cpu_.pbrMaterials[i];
                if((!p.normal.dds.empty() &&
                    !UploadDDS(dev,p.normal,&normals_[i])) ||
                   (!p.orm.dds.empty() &&
                    !UploadDDS(dev,p.orm,&orms_[i]))) {
                    mapsReady=false;break;
                }
            }
            if(mapsReady)pbrReady_=pbrShaders_.Ensure(dev);
            // Normal/ORM maps are material input, never decorative.
            // If the shader or required source map fails, do not silently
            // render an unlit/flat "textured" external car: original native
            // car remains the only safe fallback for this device generation.
            if(!pbrReady_)return RejectGpu(dev);
        }
        pbrPrepared_=true;
        if(nextMesh_<cpu_.meshes.size()) {
            const auto meshIndex=nextMesh_;
            const auto& m=cpu_.meshes[meshIndex];
            GpuMesh next{};
            next.material=m.material;
            for(std::size_t binding=0;binding<cpu_.dashboardBindings.size();++binding)
                if(cpu_.dashboardBindings[binding].meshIndex==meshIndex) {
                    next.dashboardBinding=static_cast<int>(binding);
                    break;
                }
            next.glass=m.name.compare(0,10,"F50_GLASS_")==0 ||
                m.name.compare(0,10,"EXT_GLASS_")==0;
            next.vertexCount=static_cast<UINT>(m.vertices.size());
            next.indexCount=static_cast<UINT>(m.indices.size());
            const UINT vertexBytes=next.vertexCount*sizeof(Vertex);
            const UINT indexBytes=next.indexCount*(m.index32?4u:2u);
            if(FAILED(dev->CreateVertexBuffer(vertexBytes,D3DUSAGE_WRITEONLY,
                    D3DFVF_XYZ|D3DFVF_NORMAL|D3DFVF_TEX1,D3DPOOL_DEFAULT,&next.vb,nullptr)) ||
               FAILED(dev->CreateIndexBuffer(indexBytes,D3DUSAGE_WRITEONLY,
                    m.index32?D3DFMT_INDEX32:D3DFMT_INDEX16,
                    D3DPOOL_DEFAULT,&next.ib,nullptr))) {
                if(next.vb)next.vb->Release();
                if(next.ib)next.ib->Release();
                return RejectGpu(dev);
            }
            void* vData=nullptr;
            void* iData=nullptr;
            if(FAILED(next.vb->Lock(0,vertexBytes,&vData,0)) || !vData) {
                next.vb->Release();next.ib->Release();return RejectGpu(dev);
            }
            std::memcpy(vData,m.vertices.data(),vertexBytes);
            next.vb->Unlock();
            if(FAILED(next.ib->Lock(0,indexBytes,&iData,0)) || !iData) {
                next.vb->Release();next.ib->Release();return RejectGpu(dev);
            }
            if(m.index32)
                std::memcpy(iData,m.indices.data(),indexBytes);
            else {
                // OVC1/16-bit OVC2 are converted explicitly: a uint32 vector
                // must not be copied byte-for-byte into an INDEX16 buffer.
                auto* indexOut=static_cast<std::uint16_t*>(iData);
                for(UINT i=0;i<next.indexCount;++i)
                    indexOut[i]=static_cast<std::uint16_t>(m.indices[i]);
            }
            next.ib->Unlock();
            meshes_.push_back(next);
            ++nextMesh_;
            return false;
        }
        preparation_=Preparation::Ready;
        return true;
    }
    const DashboardBinding* DashboardFor(const GpuMesh& mesh) const noexcept {
        if(mesh.dashboardBinding<0 ||
           static_cast<std::size_t>(mesh.dashboardBinding)>=cpu_.dashboardBindings.size())
            return nullptr;
        return &cpu_.dashboardBindings[static_cast<std::size_t>(mesh.dashboardBinding)];
    }
    static D3DMATRIX AnimatedWorld(const D3DMATRIX& base,
                                   const DashboardBinding* binding,
                                   const DashboardTelemetry& telemetry) noexcept {
        DashboardMatrix input{};
        std::memcpy(input.data(),&base.m[0][0],sizeof(D3DMATRIX));
        const DashboardMatrix animated=
            DashboardWorldMatrix(input,binding,telemetry);
        D3DMATRIX out{};
        std::memcpy(&out.m[0][0],animated.data(),sizeof(D3DMATRIX));
        return out;
    }
public:
    explicit GpuOwner(SidecarRole role=SidecarRole::Vehicle) noexcept:role_(role){}
    ~GpuOwner(){ReleaseGpu();}
    GpuOwner(const GpuOwner&)=delete;
    GpuOwner& operator=(const GpuOwner&)=delete;
    // Called only from the validated native player callback. One fixed slot
    // is loaded per race; never accept paths from settings or user input.
    // GenericId resolves only to ExternalCars/car_id_00..29.ovc.
    bool SelectSidecar(FerrariModelSlot next,
                       unsigned char carId=255u) noexcept {
        const unsigned char nextCarId=
            next==FerrariModelSlot::GenericId && carId<30u ?
                CanonicalFerrariExternalCarId(carId):carId;
        // A tuned/non-tuned transition must share one validated CPU and GPU
        // resource identity, avoiding repeated large DDS uploads per slot.
        if(next==FerrariModelSlot::GenericId && nextCarId>=30u)
            return false;
        if(next==selectedSlot_ && nextCarId==selectedCarId_)return false;
        // Worker's code lives in this DLL: join before destroying its future.
        // Selection changes are rare; no game-state/D3D access occurs in worker.
        if(cpuLoad_.valid())cpuLoad_.wait();
        cpuLoad_=std::future<CpuLoad>{};
        ReleaseGpu();
        cpu_=Model{};
        loaded_=false;
        preparation_=Preparation::Cold;
        loadAttempted_=false;
        gpuRetry_.OnReset();
        selectedSlot_=next;
        selectedCarId_=nextCarId;
        modelBoundsReady_=false;
        modelMinLocalY_=0.f;
        return true;
    }
    void OnDeviceReset() noexcept {
        ReleaseGpu();
        gpuRetry_.OnReset();
        // A missing/corrupt sidecar is not retried on every eye draw.
        // Re-arm only after a real device reset or race->menu boundary so a
        // corrected OVC can be picked up next race without restarting the EXE.
        // Preserve a successfully parsed CPU model across device-loss resets
        // to avoid re-reading 100+ MiB of DDS from disk during gameplay.
        if(!loaded_ && !cpuLoad_.valid()) {
            loadAttempted_=false;
            preparation_=Preparation::Cold;
        }
    }
    bool Loaded() const noexcept {return loaded_;}
    // A V4 full-car sidecar may already carry its real speed and RPM needles.
    // The separate dashboard overlay then provides gear only, avoiding two
    // competing needles overlaid on the same original instrument cluster.
    bool HasEmbeddedSpeedAndRpm() const noexcept {
        if(role_!=SidecarRole::Vehicle || !loaded_)return false;
        bool speed=false,rpm=false;
        for(const auto& b:cpu_.dashboardBindings) {
            if(b.kind==DashboardKind::SpeedNeedle)speed=true;
            if(b.kind==DashboardKind::RpmNeedle)rpm=true;
        }
        return speed && rpm;
    }
    // Only a real installed sidecar with a resolvable fixed filename may
    // become a render candidate. Parse/CRC/PBR/ground QA still guard draw.
    bool Installed() const noexcept {
        wchar_t path[MAX_PATH]{};
        if(!BuildSidecarPath(path))return false;
        const DWORD flags=GetFileAttributesW(path);
        return flags!=INVALID_FILE_ATTRIBUTES &&
            (flags&FILE_ATTRIBUTE_DIRECTORY)==0;
    }
    bool SafeFloorLift(float requested,float& effective) noexcept {
        try {
            // EnsureLoaded already opens, bounds-checks and CRC-verifies the
            // fixed path exactly once per selected canonical car. Repeating
            // GetFileAttributesW per-eye/per-frame is unnecessary disk work.
            if(role_!=SidecarRole::Vehicle ||
               !EnsureLoaded() || !modelBoundsReady_)
                return false;
            return ComputeExternalFloorLift(
                requested,modelMinLocalY_,effective);
        } catch(...) {
            return false; // never crash native player callback
        }
    }
    bool EnsureResources(IDirect3DDevice9* device) noexcept {
        try{return EnsureGpu(device);}catch(...){return RejectGpu(device);}
    }
    // Call exactly once from the verified original player world-render scope.
    // The existing Quest/R26 D3D9 renderer remains the sole stereo owner and
    // duplicates these fixed-function DrawIndexedPrimitive calls per eye.
    GpuDrawResult DrawNativeScene(IDirect3DDevice9* device,
                    const D3DMATRIX& world,const D3DMATRIX& view,
                    const D3DMATRIX& projection,
                    const DashboardTelemetry& dashboard,
                     bool gearOnly=false,
                     std::uint64_t expectedNativeFrame=0,
                     std::uint64_t expectedPose=0) noexcept {
        GpuDrawResult result{};
        if(!EnsureResources(device) || expectedNativeFrame==0 || expectedPose==0)
            return result;
        OutRunVR::GameSemantic::ScopedExternalVehicleSemantic externalScope;
        for(const auto& mesh:meshes_) {
            const auto* binding=DashboardFor(mesh);
            if(gearOnly && (!binding || binding->kind!=DashboardKind::GearVisible))
                continue;
            if(DashboardMeshVisible(binding,dashboard))
                ++result.receipt.expectedMeshes;
        }
        IDirect3DStateBlock9* saved=nullptr;
        if(FAILED(device->CreateStateBlock(D3DSBT_ALL,&saved))||!saved)
            return result;
        if(FAILED(saved->Capture())){saved->Release();return result;}
        HRESULT hr=S_OK;
        const DWORD fvf=D3DFVF_XYZ|D3DFVF_NORMAL|D3DFVF_TEX1;
        if(FAILED(device->SetVertexShader(nullptr)) ||
           FAILED(device->SetPixelShader(nullptr)) ||
           FAILED(device->SetFVF(fvf)) ||
           FAILED(device->SetTransform(D3DTS_WORLD,&world)) ||
           FAILED(device->SetTransform(D3DTS_VIEW,&view)) ||
           FAILED(device->SetTransform(D3DTS_PROJECTION,&projection)) ||
           FAILED(device->SetRenderState(D3DRS_ZENABLE,D3DZB_TRUE)) ||
           FAILED(device->SetRenderState(D3DRS_ZWRITEENABLE,TRUE)) ||
           FAILED(device->SetRenderState(D3DRS_ZFUNC,D3DCMP_LESSEQUAL)) ||
           // Native shadow/sky passes may leave a nonzero depth bias.
           // External car must use actual game depth; D3D9 FLOAT-as-DWORD zero.
           FAILED(device->SetRenderState(D3DRS_DEPTHBIAS,0u)) ||
           FAILED(device->SetRenderState(D3DRS_SLOPESCALEDEPTHBIAS,0u)) ||
           FAILED(device->SetRenderState(D3DRS_ALPHABLENDENABLE,FALSE)) ||
           // Transparent glass uses source-over ADD, independent of the
           // preceding flare/sky pass blend equation.
           FAILED(device->SetRenderState(D3DRS_BLENDOP,D3DBLENDOP_ADD)) ||
           FAILED(device->SetRenderState(D3DRS_SRGBWRITEENABLE,FALSE)) ||
           FAILED(device->SetRenderState(D3DRS_ALPHATESTENABLE,FALSE)) ||
           FAILED(device->SetRenderState(D3DRS_STENCILENABLE,FALSE)) ||
           FAILED(device->SetRenderState(D3DRS_FOGENABLE,FALSE)) ||
           // The original fixed-function scene may leave a HUD/sky clipping
           // or matrix-blend state active. Our XYZ|NORMAL|TEX1 sidecar has
           // neither blend weights nor indices, and must clip at the stereo
           // frustum rather than rasterize behind-eye geometry.
           // These states are restored by the D3DSBT_ALL block below.
           FAILED(device->SetRenderState(D3DRS_CLIPPING,TRUE)) ||
           FAILED(device->SetRenderState(D3DRS_CLIPPLANEENABLE,0u)) ||
           FAILED(device->SetRenderState(D3DRS_VERTEXBLEND,D3DVBF_DISABLE)) ||
           FAILED(device->SetRenderState(D3DRS_INDEXEDVERTEXBLENDENABLE,FALSE)) ||
           FAILED(device->SetRenderState(D3DRS_SCISSORTESTENABLE,FALSE)) ||
           FAILED(device->SetRenderState(D3DRS_CULLMODE,D3DCULL_NONE)) ||
           FAILED(device->SetRenderState(D3DRS_LIGHTING,FALSE)) ||
           FAILED(device->SetRenderState(D3DRS_COLORWRITEENABLE,
                  D3DCOLORWRITEENABLE_RED | D3DCOLORWRITEENABLE_GREEN |
                  D3DCOLORWRITEENABLE_BLUE | D3DCOLORWRITEENABLE_ALPHA)) ||
           FAILED(device->SetTextureStageState(0,D3DTSS_COLOROP,D3DTOP_SELECTARG1)) ||
           FAILED(device->SetTextureStageState(0,D3DTSS_COLORARG1,D3DTA_TEXTURE)) ||
           FAILED(device->SetTextureStageState(0,D3DTSS_ALPHAOP,D3DTOP_SELECTARG1)) ||
           FAILED(device->SetTextureStageState(0,D3DTSS_ALPHAARG1,D3DTA_TEXTURE)) ||
           FAILED(device->SetTextureStageState(0,D3DTSS_TEXCOORDINDEX,0)) ||
           FAILED(device->SetTextureStageState(0,D3DTSS_TEXTURETRANSFORMFLAGS,D3DTTFF_DISABLE)) ||
           // A native car or sky shader may have enabled stages 1..7.
           // Stop the cascade explicitly after our textured stage 0.
           FAILED(device->SetTextureStageState(1,D3DTSS_COLOROP,D3DTOP_DISABLE)) ||
           FAILED(device->SetSamplerState(0,D3DSAMP_ADDRESSU,D3DTADDRESS_WRAP)) ||
           FAILED(device->SetSamplerState(0,D3DSAMP_ADDRESSV,D3DTADDRESS_WRAP)) ||
           FAILED(device->SetSamplerState(0,D3DSAMP_MINFILTER,D3DTEXF_LINEAR)) ||
           FAILED(device->SetSamplerState(0,D3DSAMP_MAGFILTER,D3DTEXF_LINEAR)) ||
           FAILED(device->SetSamplerState(0,D3DSAMP_MIPFILTER,D3DTEXF_LINEAR)) ||
           // Game HUD/sky draws may leave a nonzero minimum mip-level.
           // A 1024px HQ albedo would otherwise be sampled as low-resolution.
           FAILED(device->SetSamplerState(0,D3DSAMP_MAXMIPLEVEL,0u)) ||
           FAILED(device->SetSamplerState(0,D3DSAMP_MIPMAPLODBIAS,0u)) ||
           FAILED(device->SetSamplerState(0,D3DSAMP_SRGBTEXTURE,FALSE)))
            hr=E_FAIL;
        if(SUCCEEDED(hr) && pbrReady_) {
            if(FAILED(device->SetRenderState(D3DRS_SRGBWRITEENABLE,FALSE)) ||
               FAILED(device->SetSamplerState(1,D3DSAMP_ADDRESSU,D3DTADDRESS_WRAP)) ||
               FAILED(device->SetSamplerState(1,D3DSAMP_ADDRESSV,D3DTADDRESS_WRAP)) ||
               FAILED(device->SetSamplerState(2,D3DSAMP_ADDRESSU,D3DTADDRESS_WRAP)) ||
               FAILED(device->SetSamplerState(2,D3DSAMP_ADDRESSV,D3DTADDRESS_WRAP)) ||
               FAILED(device->SetSamplerState(1,D3DSAMP_MINFILTER,D3DTEXF_LINEAR)) ||
               FAILED(device->SetSamplerState(1,D3DSAMP_MAGFILTER,D3DTEXF_LINEAR)) ||
               FAILED(device->SetSamplerState(1,D3DSAMP_MIPFILTER,D3DTEXF_LINEAR)) ||
               FAILED(device->SetSamplerState(2,D3DSAMP_MINFILTER,D3DTEXF_LINEAR)) ||
               FAILED(device->SetSamplerState(2,D3DSAMP_MAGFILTER,D3DTEXF_LINEAR)) ||
               FAILED(device->SetSamplerState(2,D3DSAMP_MIPFILTER,D3DTEXF_LINEAR)) ||
               // Original sky/HUD shaders may have changed the inherited
               // min-mip/LOD bias on samplers 1 and 2. Explicitly reset
               // both normal and packed ORM samplers for crisp PBR details.
               FAILED(device->SetSamplerState(1,D3DSAMP_MAXMIPLEVEL,0u)) ||
               FAILED(device->SetSamplerState(2,D3DSAMP_MAXMIPLEVEL,0u)) ||
               FAILED(device->SetSamplerState(1,D3DSAMP_MIPMAPLODBIAS,0u)) ||
               FAILED(device->SetSamplerState(2,D3DSAMP_MIPMAPLODBIAS,0u)) ||
               FAILED(device->SetSamplerState(1,D3DSAMP_SRGBTEXTURE,FALSE)) ||
               FAILED(device->SetSamplerState(2,D3DSAMP_SRGBTEXTURE,FALSE)) ||
               FAILED(pbrShaders_.Bind(device,world,view,projection))) {
                // Never draw a broken normal map or silently switch a
                // PBR asset to a different, unlit material path.
                hr=E_FAIL;
            }
        }
        const float eye[3]{
            -(view._41*view._11+view._42*view._12+view._43*view._13),
            -(view._41*view._21+view._42*view._22+view._43*view._23),
            -(view._41*view._31+view._42*view._32+view._43*view._33)};
        // Preserve input order within each class, but render opaque geometry
        // before glass even when OVC mesh groups are interleaved. Depth writes
        // remain disabled only for the transparent pass. No allocation/sort.
        if(SUCCEEDED(hr))for(unsigned pass=0;pass<2u && SUCCEEDED(hr);++pass)
          for(const auto& m:meshes_) {
            if(!MeshInDrawPass(m.glass,pass))continue;
            const DashboardBinding* binding=DashboardFor(m);
            if(gearOnly && (!binding || binding->kind!=DashboardKind::GearVisible))
                continue;
            if(!DashboardMeshVisible(binding,dashboard))continue;
            const D3DMATRIX meshWorld=AnimatedWorld(world,binding,dashboard);
            // Opaque first, then tagged translucent glass. Transparent glass
            // must not write the depth buffer or hide the track from cockpit.
            if(FAILED(device->SetTransform(D3DTS_WORLD,&meshWorld)) ||
               (pbrReady_ && FAILED(pbrShaders_.SetWorld(device,meshWorld))) ||
               FAILED(device->SetRenderState(D3DRS_ZWRITEENABLE,m.glass?FALSE:TRUE)) ||
               FAILED(device->SetRenderState(D3DRS_ALPHABLENDENABLE,m.glass?TRUE:FALSE)) ||
               FAILED(device->SetRenderState(D3DRS_SRCBLEND,D3DBLEND_SRCALPHA)) ||
               FAILED(device->SetRenderState(D3DRS_DESTBLEND,D3DBLEND_INVSRCALPHA)) ||
               FAILED(device->SetRenderState(D3DRS_SEPARATEALPHABLENDENABLE,FALSE))) {
                hr=E_FAIL;break;
            }
            if(FAILED(device->SetStreamSource(0,m.vb,0,sizeof(Vertex))) ||
               FAILED(device->SetIndices(m.ib)) ||
               FAILED(device->SetTexture(0,textures_[m.material]))) {hr=E_FAIL;break;}
            if(pbrReady_) {
                const auto& p=cpu_.pbrMaterials[m.material];
                const float factors[4]{p.roughness,p.metallic,p.normalScale,
                                       normals_[m.material]?1.f:0.f};
                const float eyeOrm[4]{eye[0],eye[1],eye[2],
                                      orms_[m.material]?1.f:0.f};
                if(FAILED(device->SetTexture(1,normals_[m.material])) ||
                   FAILED(device->SetTexture(2,orms_[m.material])) ||
                   FAILED(device->SetPixelShaderConstantF(0,factors,1)) ||
                   FAILED(device->SetPixelShaderConstantF(1,eyeOrm,1))) {
                    hr=E_FAIL;break;
                }
            }
            ExternalStereoMeshReceipt physical{};
            physical.expectedPose=expectedPose;
            ScopedExternalStereoMeshReceipt eyeScope(physical);
            result.receipt.possiblySubmitted=true;
            ++result.receipt.attemptedMeshes;
            hr=device->DrawIndexedPrimitive(D3DPT_TRIANGLELIST,0,0,m.vertexCount,
                                             0,m.indexCount/3);
            if(SUCCEEDED(hr))++result.receipt.submittedMeshes;
            if(physical.Complete())++result.receipt.verifiedStereoMeshes;
            else hr=E_FAIL; // LEFT success alone never proves RIGHT
            if(FAILED(hr))break;
        }
        const HRESULT restore=saved->Apply();
        saved->Release();
        result.receipt.drawSucceeded=SUCCEEDED(hr) &&
            result.receipt.expectedMeshes!=0 &&
            result.receipt.submittedMeshes==result.receipt.expectedMeshes &&
            result.receipt.verifiedStereoMeshes==result.receipt.expectedMeshes;
        result.receipt.stateRestored=SUCCEEDED(restore);
        result.hr=FAILED(hr)?hr:(result.receipt.drawSucceeded?restore:E_FAIL);
        if(FAILED(result.hr))
            QuarantineFailedSubmission(device);
        return result;
    }
};
inline GpuOwner& GlobalGpu() noexcept {static GpuOwner owner{SidecarRole::Vehicle};return owner;}
inline GpuOwner& GlobalDashboardGpu() noexcept {
    static GpuOwner owner{SidecarRole::DashboardOverlay};return owner;
}
} // OutRunVR::DinoSidecar