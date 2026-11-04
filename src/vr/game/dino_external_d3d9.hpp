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
    IDirect3DTexture9* textures_[Materials]{};
    IDirect3DDevice9* owner_=nullptr; // borrowed, never AddRef
    bool loaded_=false,loadAttempted_=false;
    static bool ReadFile(const wchar_t* path,std::vector<std::uint8_t>& out) noexcept {
        HANDLE f=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,
                            FILE_ATTRIBUTE_NORMAL,nullptr);
        if(f==INVALID_HANDLE_VALUE)return false;
        LARGE_INTEGER size{};
        const bool ok=GetFileSizeEx(f,&size)!=FALSE &&
                      size.QuadPart>=36 && size.QuadPart<=8ll*1024*1024;
        if(!ok){CloseHandle(f);return false;}
        std::vector<std::uint8_t> b(static_cast<std::size_t>(size.QuadPart));
        DWORD got=0;
        const bool read=::ReadFile(f,b.data(),static_cast<DWORD>(b.size()),&got,nullptr)!=FALSE &&
                        got==b.size();
        CloseHandle(f);
        if(!read)return false;
        out=std::move(b);
        return true;
    }
    static bool UploadDDS(IDirect3DDevice9* dev,const std::uint8_t* dds,
                          IDirect3DTexture9** out) noexcept {
        if(!dev || !dds || !out)return false;
        *out=nullptr;
        IDirect3DTexture9* staging=nullptr;
        // D3D9Ex forbids MANAGED; use a lockable SYSTEMMEM staging texture.
        if(FAILED(dev->CreateTexture(128,128,8,0,D3DFMT_DXT1,D3DPOOL_SYSTEMMEM,&staging,nullptr))||
           !staging)return false;
        std::size_t pos=128;
        for(UINT mip=0;mip<8;++mip) {
            const unsigned dim=std::max(1u,128u>>mip);
            const unsigned blocks=std::max(1u,(dim+3u)/4u);
            const unsigned row=blocks*8u;
            D3DLOCKED_RECT lock{};
            if(FAILED(staging->LockRect(mip,&lock,nullptr,0))) {staging->Release();return false;}
            for(unsigned y=0;y<blocks;++y) {
                std::memcpy(static_cast<std::uint8_t*>(lock.pBits)+
                            std::size_t(lock.Pitch)*y,dds+pos+std::size_t(row)*y,row);
            }
            staging->UnlockRect(mip);
            pos+=std::size_t(blocks)*row;
        }
        if(pos!=128u+10936u) {staging->Release();return false;}
        HRESULT hr=dev->CreateTexture(128,128,8,0,D3DFMT_DXT1,D3DPOOL_DEFAULT,out,nullptr);
        if(SUCCEEDED(hr)&&*out)hr=dev->UpdateTexture(staging,*out);
        staging->Release();
        if(FAILED(hr)||!*out) {
            if(*out){(*out)->Release();*out=nullptr;}
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
        owner_=nullptr;
    }
    bool EnsureLoaded() noexcept {
        if(loadAttempted_)return loaded_;
        loadAttempted_=true;
        wchar_t path[MAX_PATH]{};
        const DWORD n=GetModuleFileNameW(nullptr,path,MAX_PATH);
        if(n==0 || n>=MAX_PATH)return false;
        wchar_t* last=wcsrchr(path,L'\\');
        if(!last)return false;
        *++last=L'\0';
        constexpr wchar_t suffix[]=L"Dino246_Cockpit_LHD_v15.ovc";
        if(std::wcslen(path)+(sizeof(suffix)/sizeof(suffix[0]))>MAX_PATH)return false;
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
    bool EnsureGpu(IDirect3DDevice9* dev) noexcept {
        if(!dev || !EnsureLoaded())return false;
        if(owner_==dev && meshes_.size()==Groups)return true;
        ReleaseGpu();
        owner_=dev;
        for(unsigned material=0;material<Materials;++material) {
            if(!UploadDDS(dev,cpu_.dds[material].data(),&textures_[material])) {
                ReleaseGpu();return false;
            }
        }
        for(const auto& m:cpu_.meshes) {
            GpuMesh next{};
            next.material=m.material;
            next.vertexCount=static_cast<UINT>(m.vertices.size());
            next.indexCount=static_cast<UINT>(m.indices.size());
            const UINT vertexBytes=next.vertexCount*sizeof(Vertex);
            const UINT indexBytes=next.indexCount*sizeof(std::uint16_t);
            if(FAILED(dev->CreateVertexBuffer(vertexBytes,D3DUSAGE_WRITEONLY,
                    D3DFVF_XYZ|D3DFVF_NORMAL|D3DFVF_TEX1,D3DPOOL_DEFAULT,&next.vb,nullptr)) ||
               FAILED(dev->CreateIndexBuffer(indexBytes,D3DUSAGE_WRITEONLY,
                    D3DFMT_INDEX16,D3DPOOL_DEFAULT,&next.ib,nullptr))) {
                if(next.vb)next.vb->Release();
                if(next.ib)next.ib->Release();
                ReleaseGpu();return false;
            }
            void* vData=nullptr;
            void* iData=nullptr;
            if(FAILED(next.vb->Lock(0,vertexBytes,&vData,0)) || !vData) {
                next.vb->Release();next.ib->Release();ReleaseGpu();return false;
            }
            std::memcpy(vData,m.vertices.data(),vertexBytes);
            next.vb->Unlock();
            if(FAILED(next.ib->Lock(0,indexBytes,&iData,0)) || !iData) {
                next.vb->Release();next.ib->Release();ReleaseGpu();return false;
            }
            std::memcpy(iData,m.indices.data(),indexBytes);
            next.ib->Unlock();
            meshes_.push_back(next);
        }
        return meshes_.size()==Groups;
    }
public:
    GpuOwner()=default;
    ~GpuOwner(){ReleaseGpu();}
    GpuOwner(const GpuOwner&)=delete;
    GpuOwner& operator=(const GpuOwner&)=delete;
    void OnDeviceReset() noexcept {ReleaseGpu();}
    bool Loaded() const noexcept {return loaded_;}
    bool EnsureResources(IDirect3DDevice9* device) noexcept {
        try{return EnsureGpu(device);}catch(...){ReleaseGpu();return false;}
    }
    // Only call during an active BeginScene with correct per-eye RT and depth
    // already bound by the owning VR renderer. No BeginScene/EndScene here.
    HRESULT DrawEye(IDirect3DDevice9* device,const D3DMATRIX& world,
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
           FAILED(device->SetRenderState(D3DRS_ALPHABLENDENABLE,FALSE)) ||
           FAILED(device->SetRenderState(D3DRS_LIGHTING,FALSE)) ||
           FAILED(device->SetTextureStageState(0,D3DTSS_COLOROP,D3DTOP_SELECTARG1)) ||
           FAILED(device->SetTextureStageState(0,D3DTSS_COLORARG1,D3DTA_TEXTURE)) ||
           FAILED(device->SetTextureStageState(0,D3DTSS_ALPHAOP,D3DTOP_SELECTARG1)) ||
           FAILED(device->SetTextureStageState(0,D3DTSS_ALPHAARG1,D3DTA_TEXTURE)) ||
           FAILED(device->SetSamplerState(0,D3DSAMP_MINFILTER,D3DTEXF_LINEAR)) ||
           FAILED(device->SetSamplerState(0,D3DSAMP_MAGFILTER,D3DTEXF_LINEAR)))
            hr=E_FAIL;
        if(SUCCEEDED(hr))for(const auto& m:meshes_) {
            if(FAILED(device->SetStreamSource(0,m.vb,0,sizeof(Vertex))) ||
               FAILED(device->SetIndices(m.ib)) ||
               FAILED(device->SetTexture(0,textures_[m.material]))) {hr=E_FAIL;break;}
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
