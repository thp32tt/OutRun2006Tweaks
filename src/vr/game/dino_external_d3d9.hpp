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
#include "external_car_dds_upload.hpp"
#include "external_car_mesh_upload.hpp"
#include "external_car_normal_repair.hpp"
#include "external_car_ground.hpp"
#include "external_car_draw_order.hpp"
#include "external_car_selection.hpp"
#include "external_car_legacy_fallback.hpp"
#include "external_car_runtime_policy.hpp"
#include "dino_external_original_car_gate.hpp"
#include "dino_external_pbr_shader.hpp"
#include "external_car_pbr_stereo_scope.hpp"
#include "external_car_stereo_receipt.hpp"
#include "external_car_atomic_precommit.hpp"
#include "external_car_stereo_retry.hpp"
#include "render_semantics.hpp"

namespace OutRunVR::DinoSidecar {
// Independent of an optional R29 linked renderer TU: release builds can
// include the R26-safe owner instead. Check actual COM surface identities
// before any external car CPU/GPU preparation. Fail closed on any D3D error.
inline bool MainBackbufferActive(IDirect3DDevice9* device) noexcept {
    if(!device)return false;
    IDirect3DSurface9* active=nullptr;
    IDirect3DSurface9* main=nullptr;
    const HRESULT boundHr=device->GetRenderTarget(0,&active);
    const HRESULT mainHr=device->GetBackBuffer(
        0,0,D3DBACKBUFFER_TYPE_MONO,&main);
    const bool same=SUCCEEDED(boundHr) && SUCCEEDED(mainHr) &&
        active!=nullptr && main!=nullptr && active==main;
    if(active)active->Release();
    if(main)main->Release();
    if(!same)return false;
    // R7 rejects stereo duplication when MRT1..3 is still bound even
    // with RT0 pointing at the primary backbuffer. Fail before drawing
    // any sidecar pixels rather than entering an unrecoverable mono pass.
    for(DWORD slot=1u;slot<=3u;++slot) {
        IDirect3DSurface9* auxiliary=nullptr;
        const HRESULT result=device->GetRenderTarget(slot,&auxiliary);
        const bool bound=SUCCEEDED(result) && auxiliary!=nullptr;
        if(auxiliary)auxiliary->Release();
        if(bound)return false;
        // Unsupported MRT slots or empty attachments are normal; an
        // unexpected COM failure must not certify the stereo main pass.
        if(FAILED(result) && result!=D3DERR_NOTFOUND &&
           result!=D3DERR_INVALIDCALL)
            return false;
    }
    return true;
}
// Fixed-function test must be explicitly enabled by the launch process;
// generic PBR's c0/c4/c8 matrices are not compatible with verified c64 stereo.
inline bool FixedFunctionExternalStereoProbeActive() noexcept {
    wchar_t flag[4]{};
    return GetEnvironmentVariableW(
        L"OUTRUN_VR_EXTERNAL_FIXED_FUNCTION_TEST",flag,4)==1 &&
        flag[0]==L'1' && flag[1]==L'\0';
}
// Off by default. Only the PBR diagnostic runner enables this independent
// admission route; final acceptance still requires R7's per-mesh dual-eye
// physical receipt plus its exact shader identity and restore proof.
inline bool PbrExternalStereoProbeActive() noexcept {
    wchar_t flag[4]{};
    return GetEnvironmentVariableW(
        L"OUTRUN_VR_EXTERNAL_PBR_STEREO_TEST",flag,4)==1 &&
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
        float glassCenter[3]{0.f,0.f,0.f}; // local bbox centre, calculated on upload
    };
    Model cpu_{};
    NormalRepairStats normalRepairStats_{};
    std::string cpuLoadFailure_{};
    const char* gpuFailure_="NONE";
    std::vector<GpuMesh> meshes_{};
    std::vector<IDirect3DTexture9*> textures_{};
    std::vector<IDirect3DTexture9*> normals_{},orms_{};
    PbrShaders pbrShaders_{};
    bool pbrReady_=false;
    IDirect3DDevice9* owner_=nullptr; // borrowed, never AddRef
    bool loaded_=false,loadAttempted_=false;
    struct CpuLoad {
        Model model{};
        NormalRepairStats normalStats{};
        std::string error{};
        float lowest=0.f;
        bool parsed=false;
    };
    std::future<CpuLoad> cpuLoad_{};
    enum class Preparation : unsigned char {
        Cold, Reading, CpuReady, Uploading, Ready, Failed
    };
    Preparation preparation_=Preparation::Cold;
    std::size_t nextTexture_=0, nextMesh_=0, nextPbrMap_=0;
    bool pbrPrepared_=false;
    SidecarRole role_=SidecarRole::Vehicle;
    FerrariModelSlot selectedSlot_=FerrariModelSlot::F50;
    unsigned char selectedCarId_=255u;
    float modelMinLocalY_=0.f;
    bool modelBoundsReady_=false;
    // If D3D9Ex rejects an HQ allocation, do not retry multi-megabyte
    // textures on every eye Draw. Retry only after Reset/device change.
    GpuRetryPolicy gpuRetry_{};
    ExternalStereoRetryPolicy stereoRetry_{};
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
                                     format,D3DPOOL_SYSTEMMEM,&staging,nullptr))||!staging) {
            if(staging)staging->Release();
            return false;
        }
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
            // A successful LockRect must be paired with exactly one unlock.
            // Failed unlock means this mip was not safely committed: never
            // allocate/publish the default-pool texture from this staging data.
            if(!CopyAndUnlockDdsMip(locked.pBits,locked.Pitch,
                    texture.dds.data()+pos,rows,row,[&]() noexcept {
                        return SUCCEEDED(staging->UnlockRect(mip));
                    })) {
                staging->Release();return false;
            }
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
        nextTexture_=nextMesh_=nextPbrMap_=0;
        if(preparation_==Preparation::Uploading ||
           preparation_==Preparation::Ready)
            preparation_=loaded_?Preparation::CpuReady:Preparation::Cold;
        owner_=nullptr;
    }
    bool RejectGpu(IDirect3DDevice9* device,
                   const char* reason="GPU_RESOURCE_FAILURE") noexcept {
        ReleaseGpu();
        gpuFailure_=reason;
        gpuRetry_.NoteFailure(device);
        preparation_=Preparation::Failed;
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
        gpuFailure_="GPU_PARTIAL_SUBMISSION";
        preparation_=Preparation::Failed;
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
                    // Do not silently replace a canonical model on access
                    // denied, network/media errors or an existing directory.
                    const DWORD error=attr==INVALID_FILE_ATTRIBUTES ?
                        GetLastError():ERROR_SUCCESS;
                    if(LegacyFallbackForMissingCanonical(
                        attr!=INVALID_FILE_ATTRIBUTES,error))
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
                    if(!ReadFile(pathCopy.c_str(),bytes)) {
                        result.error="OVC_MISSING_OR_READ_FAILED";
                        return result;
                    }
                    if(!Parse(bytes.data(),bytes.size(),result.model,result.error))
                        return result;
                    result.normalStats=RepairExternalModelNormals(result.model);
                    float lowest=10000.f;
                    for(const auto& mesh:result.model.meshes) {
                        IndexedMeshBounds bounds{};
                        if(!ComputeIndexedMeshBounds(mesh,bounds)) {
                            result.error="OVC_INVALID_INDEXED_BOUNDS";
                            return result;
                        }
                        lowest=(std::min)(lowest,bounds.low[1]);
                    }
                    result.lowest=lowest;
                    result.parsed=true;
                } catch(...) {
                    result.parsed=false;
                    result.error="OVC_PARSE_EXCEPTION";
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
            cpuLoadFailure_=std::move(result.error);
            if(cpuLoadFailure_.empty())cpuLoadFailure_="OVC_PARSE_UNKNOWN";
            preparation_=Preparation::Failed;
            return false;
        }
        if(role_==SidecarRole::Vehicle) {
            float validatedLift=0.f;
            if(!ComputeExternalFloorLift(0.22f,result.lowest,validatedLift)) {
                cpuLoadFailure_="OVC_INVALID_FLOOR_ENVELOPE";
                preparation_=Preparation::Failed;
                return false;
            }
        } else if(!std::isfinite(result.lowest) ||
                  result.lowest < -10.f || result.lowest > 10.f) {
            cpuLoadFailure_="OVC_INVALID_DASHBOARD_ENVELOPE";
            preparation_=Preparation::Failed;
            return false;
        }
        modelMinLocalY_=result.lowest;
        modelBoundsReady_=true;
        cpu_=std::move(result.model);
        cpuLoadFailure_.clear();
        normalRepairStats_=result.normalStats;
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
                return RejectGpu(dev,"ALBEDO_DDS_UPLOAD_FAILED");
            return false;
        }
        // Optional PBR allocations must never prevent a working legacy draw.
        // On any map/shader failure fall back to textured fixed-function once
        // per device generation, not once per eye/frame.
        const bool fixedFunctionStereoProbe=
            ForceFixedFunctionStereoProbe();
        if(!pbrPrepared_ && cpu_.pbrEnabled && !fixedFunctionStereoProbe) {
            const auto count=cpu_.pbrMaterials.size();
            if(normals_.size()!=count)normals_.resize(count,nullptr);
            if(orms_.size()!=count)orms_.resize(count,nullptr);
            // Only one actual PBR map upload per player callback.
            while(nextPbrMap_<count*2u) {
                const std::size_t index=nextPbrMap_++;
                const auto material=index/2u;
                const bool normal=(index%2u)==0u;
                const auto& src=normal ? cpu_.pbrMaterials[material].normal
                                       : cpu_.pbrMaterials[material].orm;
                if(src.dds.empty())continue;
                IDirect3DTexture9** dst=normal ? &normals_[material]
                                              : &orms_[material];
                if(!UploadDDS(dev,src,dst))
                    return RejectGpu(dev,normal ? "NORMAL_DDS_UPLOAD_FAILED"
                                                : "ORM_DDS_UPLOAD_FAILED");
                return false;
            }
            // Bind only after every normal/ORM allocation succeeded.
            pbrReady_=pbrShaders_.Ensure(dev);
            if(!pbrReady_)return RejectGpu(dev,"PBR_SHADER_UNAVAILABLE");
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
            if(next.glass) {
                IndexedMeshBounds bounds{};
                if(!ComputeIndexedMeshBounds(m,bounds))
                    return RejectGpu(dev,"GLASS_INDEXED_BOUNDS_INVALID");
                for(unsigned k=0;k<3;++k)
                    next.glassCenter[k]=bounds.low[k]*0.5f+bounds.high[k]*0.5f;
            }
            next.vertexCount=static_cast<UINT>(m.vertices.size());
            next.indexCount=static_cast<UINT>(m.indices.size());
            const UINT vertexBytes=next.vertexCount*sizeof(Vertex);
            const UINT indexBytes=next.indexCount*(m.index32?4u:2u);
            if(FAILED(dev->CreateVertexBuffer(vertexBytes,D3DUSAGE_WRITEONLY,
                    D3DFVF_XYZ|D3DFVF_NORMAL|D3DFVF_TEX1,D3DPOOL_DEFAULT,&next.vb,nullptr)) || !next.vb ||
               FAILED(dev->CreateIndexBuffer(indexBytes,D3DUSAGE_WRITEONLY,
                    m.index32?D3DFMT_INDEX32:D3DFMT_INDEX16,
                    D3DPOOL_DEFAULT,&next.ib,nullptr)) || !next.ib) {
                if(next.vb)next.vb->Release();
                if(next.ib)next.ib->Release();
                return RejectGpu(dev);
            }
            if(!UploadExternalMeshBuffer(
                    [&](void** data) noexcept {
                        return SUCCEEDED(next.vb->Lock(0,vertexBytes,data,0));
                    },
                    [&](void* data) noexcept {
                        std::memcpy(data,m.vertices.data(),vertexBytes);
                    },
                    [&]() noexcept {return SUCCEEDED(next.vb->Unlock());})) {
                next.vb->Release();next.ib->Release();
                return RejectGpu(dev,"VERTEX_BUFFER_UPLOAD_FAILED");
            }
            if(!UploadExternalMeshBuffer(
                    [&](void** data) noexcept {
                        return SUCCEEDED(next.ib->Lock(0,indexBytes,data,0));
                    },
                    [&](void* data) noexcept {
                        if(m.index32)
                            std::memcpy(data,m.indices.data(),indexBytes);
                        else {
                            // OVC1/16-bit OVC2 require explicit narrowing.
                            auto* indexOut=static_cast<std::uint16_t*>(data);
                            for(UINT i=0;i<next.indexCount;++i)
                                indexOut[i]=static_cast<std::uint16_t>(m.indices[i]);
                        }
                    },
                    [&]() noexcept {return SUCCEEDED(next.ib->Unlock());})) {
                next.vb->Release();next.ib->Release();
                return RejectGpu(dev,"INDEX_BUFFER_UPLOAD_FAILED");
            }
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
        // No blocking wait on the player callback: a large old OVC parse
        // must finish asynchronously while native PMT is still displayed.
        // Re-attempt the pending selection on the next native callback.
        if(cpuLoad_.valid() &&
           cpuLoad_.wait_for(std::chrono::seconds(0)) !=
               std::future_status::ready)
            return false;
        // A ready future is safe to destroy without waiting; do not let a
        // stale old-car payload migrate to the new selection.
        cpuLoad_=std::future<CpuLoad>{};
        ReleaseGpu();
        cpu_=Model{};
        normalRepairStats_={};
        cpuLoadFailure_.clear();
        gpuFailure_="NONE";
        loaded_=false;
        preparation_=Preparation::Cold;
        loadAttempted_=false;
        gpuRetry_.OnReset();
        stereoRetry_.OnSelectionOrDeviceReset();
        selectedSlot_=next;
        selectedCarId_=nextCarId;
        modelBoundsReady_=false;
        modelMinLocalY_=0.f;
        return true;
    }
    bool SelectionMatches(FerrariModelSlot requested,
                          unsigned char carId=255u) const noexcept {
        const unsigned char canonical =
            requested==FerrariModelSlot::GenericId && carId<30u
            ? CanonicalFerrariExternalCarId(carId):carId;
        return selectedSlot_==requested && selectedCarId_==canonical;
    }
    void OnDeviceReset() noexcept {
        ReleaseGpu();
        gpuRetry_.OnReset();
        stereoRetry_.OnSelectionOrDeviceReset();
        // A missing/corrupt sidecar is not retried on every eye draw.
        // Re-arm only after a real device reset or race->menu boundary so a
        // corrected OVC can be picked up next race without restarting the EXE.
        // Preserve a successfully parsed CPU model across device-loss resets
        // to avoid re-reading 100+ MiB of DDS from disk during gameplay.
        if(loaded_)preparation_=Preparation::CpuReady;
        if(!loaded_ && !cpuLoad_.valid()) {
            loadAttempted_=false;
            preparation_=Preparation::Cold;
        }
    }
    // A verified-epoch mismatch after GPU submissions is not recoverable
    // by drawing the stock body over the already modified eye. Keep the
    // current frame partial and use original PMT from the next frame.
    void QuarantineUnsafeFrame(IDirect3DDevice9* device) noexcept {
        QuarantineFailedSubmission(device);
    }
    const char* LastLoadFailureName() const noexcept {
        if(gpuFailure_ && std::strcmp(gpuFailure_,"NONE")!=0)return gpuFailure_;
        return cpuLoadFailure_.empty() ? "NONE" : cpuLoadFailure_.c_str();
    }
    const char* PreparationName() const noexcept {
        switch(preparation_) {
        case Preparation::Cold:return "COLD";
        case Preparation::Reading:return "CPU_READING";
        case Preparation::CpuReady:return "CPU_READY";
        case Preparation::Uploading:return "GPU_UPLOADING";
        case Preparation::Ready:return "GPU_READY";
        default:return "FAILED";
        }
    }
    // A validated PBR-format OVC does not imply PBR is actually drawn:
    // strict native per-eye fixed-function testing deliberately bypasses
    // normal/ORM uploads and the unverified c0/c4/c8 vertex shader.
    const char* MaterialModeName() const noexcept {
        if(preparation_!=Preparation::Ready)return "NOT_READY";
        if(pbrReady_)return "PBR_SHADER";
        return cpu_.pbrEnabled ?
            "FIXED_FN_ALBEDO_ONLY_PBR_MAPS_BYPASSED" :
            "FIXED_FN_ALBEDO_ONLY";
    }
    NormalRepairStats NormalRecovery() const noexcept {return normalRepairStats_;}
    unsigned NormalMapsInAsset() const noexcept {
        unsigned count=0;
        for(const auto& p:cpu_.pbrMaterials)
            if(!p.normal.dds.empty())++count;
        return count;
    }
    unsigned OrmMapsInAsset() const noexcept {
        unsigned count=0;
        for(const auto& p:cpu_.pbrMaterials)
            if(!p.orm.dds.empty())++count;
        return count;
    }
    unsigned NormalMapsOnGpu() const noexcept {
        if(!pbrReady_)return 0;
        unsigned count=0;
        for(const auto* p:normals_)if(p)++count;
        return count;
    }
    unsigned OrmMapsOnGpu() const noexcept {
        if(!pbrReady_)return 0;
        unsigned count=0;
        for(const auto* p:orms_)if(p)++count;
        return count;
    }
    bool Loaded() const noexcept {return loaded_;}
    // API name retained for the existing large game-hook call site: return
    // individual bit coverage (1=speed, 2=RPM), NOT a boolean pair flag.
    unsigned HasEmbeddedSpeedAndRpm() const noexcept {
        return role_==SidecarRole::Vehicle && loaded_ ?
            DashboardNeedleMask(cpu_.dashboardBindings.data(),
                                cpu_.dashboardBindings.size()) : 0u;
    }
    // Only body-owned gear bindings can suppress a matching overlay gear.
    unsigned EmbeddedGearMask() const noexcept {
        return role_==SidecarRole::Vehicle && loaded_ ?
            DashboardGearMask(cpu_.dashboardBindings.data(),
                              cpu_.dashboardBindings.size()) : 0u;
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
                     unsigned embeddedNeedleMask=0u,
                     std::uint64_t expectedNativeFrame=0,
                     std::uint64_t expectedPose=0,
                     unsigned embeddedGearMask=0u) noexcept {
        GpuDrawResult result{};
        // First-party safety gate, independent of whether R7/R30/R33
        // vtable hooks installed successfully. No whole-vehicle isolated
        // L/R color+depth stage and pair-atomic publication exists yet.
        // Return BEFORE D3D state setup, resource creation or any DIP so
        // the original 49F3E0 player callback remains the sole raster owner.
        if(!RuntimeExternalCarAtomicStageReady())return result;
        // A stale/invalid ticket must not consume retry budget or start
        // any expensive DDS/mesh preparation.
        if(!device || expectedNativeFrame==0 || expectedPose==0)return result;
        if(!stereoRetry_.AllowNativeAttempt())return result;
        if(!EnsureResources(device))return result;
        for(const auto& mesh:meshes_) {
            const auto* binding=DashboardFor(mesh);
            if(DashboardOverlayMeshVisible(binding,dashboard,embeddedNeedleMask,embeddedGearMask))
                ++result.receipt.expectedMeshes;
        }
        // Nothing drawable: do not mutate render state or quarantine GPU.
        if(result.receipt.expectedMeshes==0)return result;
        IDirect3DStateBlock9* saved=nullptr;
        if(!CaptureExternalDrawState(saved,stereoRetry_,
            [&](IDirect3DStateBlock9** out) noexcept {
                return SUCCEEDED(device->CreateStateBlock(D3DSBT_ALL,out));
            },
            [&]() noexcept {return SUCCEEDED(saved->Capture());},
            [&]() noexcept {saved->Release();}))
            return result;
        HRESULT hr=S_OK;
        bool eyeProofOnlyFailure=false;
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
           !ConfigureExternalRasterCoverage(
               [&]() { return SUCCEEDED(device->SetRenderState(
                   D3DRS_FILLMODE,D3DFILL_SOLID)); },
               [&]() { return SUCCEEDED(device->SetRenderState(
                   D3DRS_MULTISAMPLEMASK,0xffffffffu)); }) ||
           FAILED(device->SetRenderState(D3DRS_CULLMODE,D3DCULL_NONE)) ||
           FAILED(device->SetRenderState(D3DRS_LIGHTING,FALSE)) ||
           FAILED(device->SetRenderState(D3DRS_COLORWRITEENABLE,
                  D3DCOLORWRITEENABLE_RED | D3DCOLORWRITEENABLE_GREEN |
                  D3DCOLORWRITEENABLE_BLUE | D3DCOLORWRITEENABLE_ALPHA)) ||
           !ConfigureExternalTextureRouting(
               [&]() { return SUCCEEDED(device->SetTextureStageState(
                   0,D3DTSS_RESULTARG,D3DTA_CURRENT)); },
               [&](unsigned coordinate) {
                   constexpr D3DRENDERSTATETYPE states[]{
                       D3DRS_WRAP0,D3DRS_WRAP1,D3DRS_WRAP2};
                   return SUCCEEDED(device->SetRenderState(states[coordinate],0u));
               }) ||
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
        // Imported OVC mesh order is not depth order. Keep opaque input
        // order; sort only transparent meshes far-to-near in the latched
        // center camera. This stack buffer is bounded by the parser's 512
        // mesh limit, with no per-eye allocations or texture replacement.
        std::array<GlassDepthItem,MaxGroups> glassOrder{};
        unsigned glassCount=0u;
        if(SUCCEEDED(hr))for(unsigned i=0;i<meshes_.size();++i) {
            const auto& m=meshes_[i];
            if(m.glass && glassCount<glassOrder.size()) {
                const auto* binding=DashboardFor(m);
                if(!DashboardOverlayMeshVisible(binding,dashboard,
                        embeddedNeedleMask,embeddedGearMask))continue;
                // Sort using the same animated transform as the DIP.
                const D3DMATRIX meshWorld=AnimatedWorld(world,binding,dashboard);
                glassOrder[glassCount++]={i,ExternalGlassViewDepth(
                    m.glassCenter,&meshWorld.m[0][0],&view.m[0][0],
                    projection._34)};
            }
        }
        SortGlassBackToFront(glassOrder.data(),glassCount);
        if(SUCCEEDED(hr))for(unsigned pass=0;pass<2u && SUCCEEDED(hr);++pass)
          for(unsigned order=0;order<(pass?glassCount:meshes_.size());++order) {
            const auto& m=meshes_[pass?glassOrder[order].index:order];
            if(!MeshInDrawPass(m.glass,pass))continue;
            const DashboardBinding* binding=DashboardFor(m);
            if(!DashboardOverlayMeshVisible(binding,dashboard,embeddedNeedleMask,embeddedGearMask))
                continue;
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
            // The R7 renderer may re-upload this exact shader's c4/c8 and
            // pixel c1 for each eye. The identity scope never tags game draws.
            ScopedExternalPbrStereo pbrEyeScope(
                pbrReady_?pbrShaders_.VertexShader():nullptr,
                pbrReady_?pbrShaders_.PixelShader():nullptr);
            // Scope only the physical DIP, never shader/RT/StateBlock setup.
            // A native draw re-entering during preparation retains its owner.
            OutRunVR::GameSemantic::ScopedExternalVehicleSemantic externalScope;
            const unsigned priorAttempts=result.receipt.attemptedMeshes;
            const unsigned priorSubmissions=result.receipt.submittedMeshes;
            result.receipt.possiblySubmitted=true;
            ++result.receipt.attemptedMeshes;
            const HRESULT dipHr=device->DrawIndexedPrimitive(
                D3DPT_TRIANGLELIST,0,0,m.vertexCount,0,m.indexCount/3);
            if(SUCCEEDED(dipHr))++result.receipt.submittedMeshes;
            const bool provenNoDraw=FAILED(dipHr) &&
                CanFallbackAfterNoExternalRaster(physical,priorAttempts,
                                                  priorSubmissions);
            if(provenNoDraw)result.receipt.possiblySubmitted=false;
            const bool stereoComplete=physical.Complete();
            result.receipt.lastEyeFailure=ClassifyExternalEyeFailure(physical);
            result.receipt.lastEyeReports=physical.reports;
            if(stereoComplete)++result.receipt.verifiedStereoMeshes;
            if((SUCCEEDED(dipHr) && !stereoComplete) || provenNoDraw)
                eyeProofOnlyFailure=!physical.rightDrawFailed &&
                    !physical.deviceRestoreFailed;
            hr=stereoComplete?dipHr:E_FAIL;
            if(FAILED(hr))break;
        }
        const HRESULT restore=saved->Apply();
        saved->Release();
        result.receipt.drawSucceeded=SUCCEEDED(hr) &&
            result.receipt.expectedMeshes!=0 &&
            result.receipt.submittedMeshes==result.receipt.expectedMeshes &&
            result.receipt.verifiedStereoMeshes==result.receipt.expectedMeshes;
        result.receipt.stateRestored=SUCCEEDED(restore);
        // A failed StateBlock Apply can leave the next original callback
        // using external-car shaders/textures/depth settings. Keep the current
        // native callback suppressed even when no DIP was submitted.
        result.receipt.stateMayBeDirty=FAILED(restore);
        result.hr=FAILED(hr)?hr:(result.receipt.drawSucceeded?restore:E_FAIL);
        if(FAILED(result.hr)) {
            if(eyeProofOnlyFailure && result.receipt.stateRestored) {
                // Stereo loss is a frame issue, not proof that the OVC
                // textures/VBs are corrupt. Keep stock visible during
                // cooldown and retry a bounded interval later.
                stereoRetry_.OnSoftStereoFailure();
            } else {
                QuarantineFailedSubmission(device);
            }
        }
        return result;
    }
};
inline GpuOwner& GlobalGpu() noexcept {static GpuOwner owner{SidecarRole::Vehicle};return owner;}
inline GpuOwner& GlobalDashboardGpu() noexcept {
    static GpuOwner owner{SidecarRole::DashboardOverlay};return owner;
}
} // OutRunVR::DinoSidecar