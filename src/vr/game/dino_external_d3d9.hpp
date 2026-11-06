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
#include <iterator>
#include <string>
#include <vector>
#include "dino_external_sidecar.hpp"
#include "dino_external_pbr_shader.hpp"

namespace OutRunVR::DinoSidecar {
class GpuOwner final {
    struct GpuMesh {
        IDirect3DVertexBuffer9* vb=nullptr;
        IDirect3DIndexBuffer9* ib=nullptr;
        UINT vertexCount=0,indexCount=0;
        unsigned material=0;
    };
    Model cpu_{};
    std::vector<GpuMesh> meshes_{};
    std::vector<IDirect3DTexture9*> textures_{};
    std::vector<IDirect3DTexture9*> normals_{},orms_{};
    PbrShaders pbrShaders_{};
    bool pbrReady_=false;
    IDirect3DDevice9* owner_=nullptr; // borrowed, never AddRef
    bool loaded_=false,loadAttempted_=false;
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
        owner_=nullptr;
    }
    bool RejectGpu(IDirect3DDevice9* device) noexcept {
        ReleaseGpu();
        gpuRetry_.NoteFailure(device);
        return false;
    }
    bool EnsureLoaded() {
        if(loadAttempted_)return loaded_;
        loadAttempted_=true;
        wchar_t path[MAX_PATH]{};
        const DWORD n=GetModuleFileNameW(nullptr,path,MAX_PATH);
        if(n==0 || n>=MAX_PATH)return false;
        wchar_t* last=wcsrchr(path,L'\\');
        if(!last)return false;
        *++last=L'\0';
        // Never replace or auto-detect the stable OVC2 file. Only the
        // separate PBR launcher may explicitly opt in to the V3 filename.
        wchar_t pbrFlag[4]{};
        const bool usePbr=GetEnvironmentVariableW(
            L"OUTRUN_VR_DINO_PBR_TEST",pbrFlag,4)==1 &&
            pbrFlag[0]==L'1' && pbrFlag[1]==L'\\0';
        constexpr wchar_t stableSuffix[]=L"Dino246_Cockpit_LHD_v15.ovc";
        constexpr wchar_t pbrSuffix[]=L"Dino246_Cockpit_LHD_v15_PBR.ovc";
        const wchar_t* suffix=usePbr?pbrSuffix:stableSuffix;
        if(std::wcslen(path)+std::wcslen(suffix)+1>MAX_PATH)return false;
        if(wcscat_s(path,MAX_PATH,suffix)!=0)return false;
        std::vector<std::uint8_t> bytes;
        if(!ReadFile(path,bytes))return false;
        std::string error;
        Model next;
        if(!Parse(bytes.data(),bytes.size(),next,error))return false;
        cpu_=std::move(next);
        loaded_=true;
        return true;
    }
    bool EnsureGpu(IDirect3DDevice9* dev) {
        if(!dev || !EnsureLoaded())return false;
        if(!gpuRetry_.CanAttempt(dev))return false;
        if(owner_==dev && meshes_.size()==cpu_.meshes.size() &&
           textures_.size()==cpu_.textures.size())return true;
        ReleaseGpu();
        owner_=dev;
        // No vector reallocations after COM allocations begin: an allocation
        // failure must not leak the just-created VB/IB pair of a pending mesh.
        meshes_.reserve(cpu_.meshes.size());
        textures_.resize(cpu_.textures.size(),nullptr);
        for(std::size_t material=0;material<cpu_.textures.size();++material) {
            if(!UploadDDS(dev,cpu_.textures[material],&textures_[material])) {
                return RejectGpu(dev);
            }
        }
        // Optional PBR allocations must never prevent a working legacy draw.
        // On any map/shader failure fall back to textured fixed-function once
        // per device generation, not once per eye/frame.
        if(cpu_.pbrEnabled) {
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
            if(!pbrReady_) {
                for(auto& t:normals_){if(t)t->Release();t=nullptr;}
                for(auto& t:orms_){if(t)t->Release();t=nullptr;}
            }
        }
        for(const auto& m:cpu_.meshes) {
            GpuMesh next{};
            next.material=m.material;
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
        }
        return meshes_.size()==cpu_.meshes.size();
    }
public:
    GpuOwner()=default;
    ~GpuOwner(){ReleaseGpu();}
    GpuOwner(const GpuOwner&)=delete;
    GpuOwner& operator=(const GpuOwner&)=delete;
    void OnDeviceReset() noexcept {ReleaseGpu();gpuRetry_.OnReset();}
    bool Loaded() const noexcept {return loaded_;}
    bool EnsureResources(IDirect3DDevice9* device) noexcept {
        try{return EnsureGpu(device);}catch(...){return RejectGpu(device);}
    }
    // Call exactly once from the verified original player world-render scope.
    // The existing Quest/R26 D3D9 renderer remains the sole stereo owner and
    // duplicates these fixed-function DrawIndexedPrimitive calls per eye.
    HRESULT DrawNativeScene(IDirect3DDevice9* device,const D3DMATRIX& world,
                    const D3DMATRIX& view,const D3DMATRIX& projection) noexcept {
        if(!EnsureResources(device))return E_FAIL;
        IDirect3DStateBlock9* saved=nullptr;
        if(FAILED(device->CreateStateBlock(D3DSBT_ALL,&saved))||!saved)
            return E_FAIL;
        if(FAILED(saved->Capture())){saved->Release();return E_FAIL;}
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
           FAILED(device->SetRenderState(D3DRS_ALPHABLENDENABLE,FALSE)) ||
           FAILED(device->SetRenderState(D3DRS_ALPHATESTENABLE,FALSE)) ||
           FAILED(device->SetRenderState(D3DRS_STENCILENABLE,FALSE)) ||
           FAILED(device->SetRenderState(D3DRS_FOGENABLE,FALSE)) ||
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
               FAILED(device->SetSamplerState(1,D3DSAMP_SRGBTEXTURE,FALSE)) ||
               FAILED(device->SetSamplerState(2,D3DSAMP_SRGBTEXTURE,FALSE)) ||
               FAILED(pbrShaders_.Bind(device,world,view,projection))) {
                // Preserve the color-texture path even on a shader bind error.
                pbrReady_=false;
                if(FAILED(device->SetVertexShader(nullptr)) ||
                   FAILED(device->SetPixelShader(nullptr)))hr=E_FAIL;
            }
        }
        const float eye[3]{
            -(view._41*view._11+view._42*view._12+view._43*view._13),
            -(view._41*view._21+view._42*view._22+view._43*view._23),
            -(view._41*view._31+view._42*view._32+view._43*view._33)};
        if(SUCCEEDED(hr))for(const auto& m:meshes_) {
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
            hr=device->DrawIndexedPrimitive(D3DPT_TRIANGLELIST,0,0,m.vertexCount,
                                             0,m.indexCount/3);
            if(FAILED(hr))break;
        }
        const HRESULT restore=saved->Apply();
        saved->Release();
        return FAILED(hr)?hr:restore;
    }
};
inline GpuOwner& GlobalGpu() noexcept {static GpuOwner owner;return owner;}
} // OutRunVR::DinoSidecar
