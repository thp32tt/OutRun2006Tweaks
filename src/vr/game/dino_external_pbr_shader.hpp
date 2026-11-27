#pragma once
// Optional D3D9 SM3.0 metal/roughness cockpit shading. No D3DX link dependency.
// All shader resources are per-device and are released before Reset/ResetEx.
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <d3d9.h>
#include <d3dcompiler.h>
#include <cstring>
#include <cstdint>
#include <future>
#include <chrono>
#include <vector>
#include "external_car_pbr_eye_math.hpp"
#include "external_car_pbr_normal_math.hpp"

namespace OutRunVR::DinoSidecar {
class PbrShaders final {
    IDirect3DVertexShader9* vs_=nullptr;
    IDirect3DPixelShader9* ps_=nullptr;
    bool attempted_=false;
    std::uint64_t generation_=1;
    static constexpr const char* VertexSource() noexcept {
        return R"HLSL(
row_major float4x4 world : register(c0);
row_major float4x4 view : register(c4);
row_major float4x4 projection : register(c8);
row_major float3x3 worldNormalMatrix : register(c12);
struct VertexIn {
    float3 position : POSITION0;
    float3 normal : NORMAL0;
    float2 uv : TEXCOORD0;
};
struct VertexOut {
    float4 position : POSITION0;
    float3 worldPosition : TEXCOORD0;
    float3 worldNormal : TEXCOORD1;
    float2 uv : TEXCOORD2;
};
VertexOut mainVS(VertexIn input) {
    VertexOut o;
    float4 w = mul(float4(input.position,1), world);
    o.worldPosition = w.xyz;
    // normalize(0) is undefined in HLSL. Preserve a zero normal so the
    // pixel shader can derive a geometric normal rather than interpolate NaN.
    float3 transformedNormal = mul(input.normal, worldNormalMatrix);
    float normalSq = dot(transformedNormal,transformedNormal);
    o.worldNormal = normalSq > 1.e-30 ?
        transformedNormal * rsqrt(max(normalSq,1.e-30)) : float3(0,0,0);
    o.uv = input.uv;
    o.position = mul(mul(w,view),projection);
    return o;
}
)HLSL";
    }
    static constexpr const char* PixelSource() noexcept {
        return R"HLSL(
sampler2D albedoMap : register(s0);
sampler2D normalMap : register(s1);
sampler2D ormMap : register(s2);
// (roughness, metallic, normal strength, has normal map)
float4 factors : register(c0);
// (eye position xyz, has packed ORM map)
float4 eyeAndOrm : register(c1);
struct PixelIn {
    float3 worldPosition : TEXCOORD0;
    float3 worldNormal : TEXCOORD1;
    float2 uv : TEXCOORD2;
};
float4 mainPS(PixelIn input) : COLOR0 {
    const float pi = 3.14159265;
    float4 base = tex2D(albedoMap,input.uv);
    float3 albedo = pow(saturate(base.rgb),2.2);
    float roughness = clamp(factors.x,0.045,1.0);
    float metallic = saturate(factors.y);
    float ao = 1.0;
    if (eyeAndOrm.w > 0.5) {
        float3 orm = tex2D(ormMap,input.uv).rgb;
        ao = orm.r;
        roughness = clamp(orm.g * factors.x,0.045,1.0);
        metallic = saturate(orm.b * factors.y);
    }
    // Some imported models have zero-length normals (including genuinely
    // degenerate topology which the CPU cannot repair). Derive a geometric
    // face normal before normal-map TBN rather than normalizing float3(0,0,0).
    float3 dpdx = ddx(input.worldPosition);
    float3 dpdy = ddy(input.worldPosition);
    float3 faceN = cross(dpdx,dpdy);
    float3 rawN = input.worldNormal;
    float normalSq = dot(rawN,rawN);
    float faceSq = dot(faceN,faceN);
    float3 N = normalSq > 1.e-12 ? normalize(rawN) :
               (faceSq > 1.e-12 ? normalize(faceN) : float3(0,1,0));
    // Derivative TBN handles source FVF XYZ/NORMAL/UV without altered vertex stride.
    // Handedness is preserved for mirrored texture islands (negative UV determinant).
    float2 dtdx = ddx(input.uv);
    float2 dtdy = ddy(input.uv);
    float det = dtdx.x*dtdy.y-dtdx.y*dtdy.x;
    // A fixed absolute determinant threshold depends on projected area:
    // even a valid UV basis can lose its normal map on a very large
    // cockpit triangle. Compare the squared UV area to the gradient energies
    // to keep the decision invariant under screen resolution/scale.
    float gradientArea2 = dot(dtdx,dtdx)*dot(dtdy,dtdy);
    // Zero normal strength disables perturbation even for a bound map
    // with negative or zero Z; preserve the unperturbed normal.
    if (factors.w > 0.5 && factors.z > 0.0 && gradientArea2 > 1.e-30 &&
        det*det > gradientArea2*1.e-8) {
        // Mirrored UV islands retain their signed tangent handedness.
        // Never normalize a tangent parallel to a malformed source normal.
        float3 T = (dpdx*dtdy.y-dpdy*dtdx.y)/det;
        T = T-N*dot(N,T);
        float tangentSq = dot(T,T);
        float3 derivativeB = (dpdy*dtdx.x-dpdx*dtdy.x)/det;
        // A nonzero B derivative alone does not establish handedness:
        // it may lie in the N/T plane when imported normals are tangential.
        // Reject an ambiguous orientation instead of inventing a positive sign.
        float bitangentSq = dot(derivativeB,derivativeB);
        float orientation = dot(cross(N,T),derivativeB);
        if (tangentSq > 1.e-12 && bitangentSq > 1.e-12 &&
            orientation*orientation > tangentSq*bitangentSq*1.e-8) {
            T *= rsqrt(tangentSq);
            float handedness = orientation < 0 ? -1.0 : 1.0;
            float3 B = normalize(cross(N,T))*handedness;
            // The TBN branch varies across neighboring pixels. Implicit
            // texture derivatives here can select undefined mip levels.
            // Use the gradients already evaluated before divergent flow.
            float3 mapN = tex2Dgrad(normalMap,input.uv,dtdx,dtdy).xyz*2.0-1.0;
            mapN.xy *= factors.z;
            float3 mappedN = mapN.x*T+mapN.y*B+mapN.z*N;
            float mappedSq = dot(mappedN,mappedN);
            if (mappedSq > 1.e-12) N = mappedN * rsqrt(mappedSq);
        }
    }
    float3 L = normalize(float3(-0.45,0.85,-0.28));
    // An eye coincident with a surface vertex or a view direction
    // antiparallel to L has no defined unit vector / half vector.
    float3 eyeDelta = eyeAndOrm.xyz-input.worldPosition;
    float eyeSq = dot(eyeDelta,eyeDelta);
    float3 V = eyeSq > 1.e-12 ?
        eyeDelta * rsqrt(max(eyeSq,1.e-12)) : float3(0,0,0);
    float3 halfVector = L+V;
    float halfSq = dot(halfVector,halfVector);
    float3 H = halfSq > 1.e-12 ?
        halfVector * rsqrt(max(halfSq,1.e-12)) : float3(0,0,0);
    float NL = saturate(dot(N,L));
    float NV = max(saturate(dot(N,V)),0.001);
    float NH = saturate(dot(N,H));
    float VH = saturate(dot(V,H));
    float a = roughness*roughness;
    float a2 = a*a;
    float q = NH*NH*(a2-1)+1;
    float distribution = a2/(pi*q*q+0.0001);
    float k = (roughness+1)*(roughness+1)/8;
    float geometry = (NL/(NL*(1-k)+k))*(NV/(NV*(1-k)+k));
    float3 F0 = lerp(float3(0.04,0.04,0.04),albedo,metallic);
    float3 fresnel = F0+(1-F0)*pow(1-VH,5);
    // No valid eye/half vector means no directional specular highlight.
    float3 specular = eyeSq > 1.e-12 && halfSq > 1.e-12 ?
        distribution*geometry*fresnel/(4*NL*NV+0.001) : float3(0,0,0);
    float3 diffuse = (1-fresnel)*(1-metallic)*albedo/pi;
    float3 radiance = (diffuse+specular)*NL*2.0;
    float3 ambient = ao*(albedo*(1-metallic)*0.16+F0*0.045);
    // Identical BRDF for mapped and scalar-only materials. A neutral
    // (1,1,1) ORM must not change lighting; AO affects indirect light only.
    if (eyeSq > 1.e-12) {
        float edge = 1.0-roughness;
        float3 ambientF = F0+(max(float3(edge,edge,edge),F0)-F0)*pow(1-NV,5);
        ambient = ao*((1-ambientF)*albedo*(1-metallic)*0.16+
                      ambientF*lerp(0.045,0.02,roughness));
    }
    float3 linearColor = saturate(radiance+ambient);
    return float4(pow(linearColor,1.0/2.2),base.a);
}
)HLSL";
    }
    struct Bytecode {
        std::vector<DWORD> vs,ps;
        bool valid() const noexcept {return !vs.empty()&&!ps.empty();}
    };
    // D3DCompile is CPU-only. Share immutable bytecode across body/dashboard
    // and every Reset; never move device/COM shader creation off render thread.
    static Bytecode CompileBytecode() {
        struct Resources {
            HMODULE dll=nullptr;
            ID3DBlob *vs=nullptr,*ps=nullptr,*errors=nullptr;
            ~Resources(){
                if(errors)errors->Release();
                if(vs)vs->Release();
                if(ps)ps->Release();
                if(dll)FreeLibrary(dll);
            }
        } r;
        r.dll=LoadLibraryW(L"d3dcompiler_47.dll");
        if(!r.dll)return {};
        using Compile=HRESULT (WINAPI *)(LPCVOID,SIZE_T,LPCSTR,
            const D3D_SHADER_MACRO*,ID3DInclude*,LPCSTR,LPCSTR,
            UINT,UINT,ID3DBlob**,ID3DBlob**);
        const auto compile=reinterpret_cast<Compile>(GetProcAddress(r.dll,"D3DCompile"));
        if(!compile)return {};
        constexpr UINT flags=D3DCOMPILE_PACK_MATRIX_ROW_MAJOR|D3DCOMPILE_OPTIMIZATION_LEVEL3;
        HRESULT hr=compile(VertexSource(),std::strlen(VertexSource()),"DinoPbrVS",
            nullptr,nullptr,"mainVS","vs_3_0",flags,0,&r.vs,&r.errors);
        if(r.errors){r.errors->Release();r.errors=nullptr;}
        if(FAILED(hr)||!r.vs)return {};
        hr=compile(PixelSource(),std::strlen(PixelSource()),"DinoPbrPS",
            nullptr,nullptr,"mainPS","ps_3_0",flags,0,&r.ps,&r.errors);
        if(FAILED(hr)||!r.ps)return {};
        Bytecode code{};
        auto copy=[](ID3DBlob* blob,std::vector<DWORD>& out){
            const auto bytes=blob->GetBufferSize();
            if(!bytes||bytes%sizeof(DWORD)||!blob->GetBufferPointer())return false;
            out.resize(bytes/sizeof(DWORD));
            std::memcpy(out.data(),blob->GetBufferPointer(),bytes);
            return true;
        };
        if(!copy(r.vs,code.vs)||!copy(r.ps,code.ps))return {};
        return code;
    }
    static const std::shared_future<Bytecode>& SharedBytecode() {
        static const auto task=std::async(std::launch::async,[]{
            try{return CompileBytecode();}catch(...){return Bytecode{};}
        }).share();
        return task;
    }
public:
    enum class Preparation { Pending, Ready, Failed };
    static void Prewarm() noexcept {
        try{(void)SharedBytecode();}catch(...){}
    }
    // Exposed for the Windows compiler regression without requiring a GPU.
    static Preparation BytecodePreparation() noexcept {
        try{
            const auto& task=SharedBytecode();
            if(task.wait_for(std::chrono::seconds(0))!=std::future_status::ready)
                return Preparation::Pending;
            return task.get().valid()?Preparation::Ready:Preparation::Failed;
        }catch(...){return Preparation::Failed;}
    }
    static constexpr const char* VertexHlsl() noexcept {return VertexSource();}
    static constexpr const char* PixelHlsl() noexcept {return PixelSource();}
    IDirect3DVertexShader9* VertexShader() const noexcept {return vs_;}
    IDirect3DPixelShader9* PixelShader() const noexcept {return ps_;}
    PbrShaders()=default;
    ~PbrShaders(){Release();}
    PbrShaders(const PbrShaders&)=delete;
    PbrShaders& operator=(const PbrShaders&)=delete;
    void Release() noexcept {
        auto* vs=vs_;auto* ps=ps_;
        vs_=nullptr;ps_=nullptr;attempted_=false;
        if(++generation_==0)++generation_;
        if(vs)vs->Release();
        if(ps)ps->Release();
    }
    Preparation Ensure(IDirect3DDevice9* device) noexcept {
        if(!device)return Preparation::Failed;
        if(attempted_)return vs_&&ps_?Preparation::Ready:Preparation::Failed;
        const auto status=BytecodePreparation();
        if(status==Preparation::Pending)return status;
        attempted_=true;
        if(status!=Preparation::Ready)return Preparation::Failed;
        const auto generation=generation_;
        const auto current=[&](){return generation_==generation;};
        D3DCAPS9 caps{};
        if(FAILED(device->GetDeviceCaps(&caps))||!current()||
            caps.VertexShaderVersion<D3DVS_VERSION(3,0)||
            caps.PixelShaderVersion<D3DPS_VERSION(3,0))return Preparation::Failed;
        const auto& code=SharedBytecode().get();
        IDirect3DVertexShader9* pendingVs=nullptr;
        IDirect3DPixelShader9* pendingPs=nullptr;
        HRESULT hr=device->CreateVertexShader(code.vs.data(),&pendingVs);
        if(SUCCEEDED(hr)&&pendingVs&&current())
            hr=device->CreatePixelShader(code.ps.data(),&pendingPs);
        if(FAILED(hr)||!pendingVs||!pendingPs||!current()){
            if(pendingVs)pendingVs->Release();
            if(pendingPs)pendingPs->Release();
            return Preparation::Failed;
        }
        vs_=pendingVs;ps_=pendingPs;
        return Preparation::Ready;
    }
    template<class Current>
    HRESULT SetWorldGuarded(IDirect3DDevice9* device,const D3DMATRIX& world,Current current) noexcept {
        if(!device||!vs_)return E_FAIL;
        float normalRows[12]{};
        if(!ExternalCarPbrNormalMatrix(&world.m[0][0],normalRows))
            return E_FAIL;
        if(!current()||FAILED(device->SetVertexShaderConstantF(
                    0,&world.m[0][0],4)) ||
           !current()||FAILED(device->SetVertexShaderConstantF(12,normalRows,3))||!current())
            return E_FAIL;
        return S_OK;
    }
    HRESULT SetWorld(IDirect3DDevice9* device,const D3DMATRIX& world) noexcept {
        return SetWorldGuarded(device,world,[](){return true;});
    }
    template<class Current>
    HRESULT BindGuarded(IDirect3DDevice9* device,const D3DMATRIX& world,
                 const D3DMATRIX& view,const D3DMATRIX& projection,Current current) noexcept {
        if(!device||!vs_||!ps_)return E_FAIL;
        float eye[4]{};
        if(!ExternalPbrEyeConstants(&view.m[0][0],0.f,eye))
            return E_FAIL;
        if(!current()||FAILED(device->SetVertexShader(vs_)) ||
           !current()||FAILED(device->SetPixelShader(ps_)) ||
           !current()||FAILED(device->SetVertexShaderConstantF(4,&view.m[0][0],4)) ||
           !current()||FAILED(device->SetVertexShaderConstantF(8,&projection.m[0][0],4)) ||
           !current()||FAILED(device->SetPixelShaderConstantF(1,eye,1))||!current())
            return E_FAIL;
        return SetWorldGuarded(device,world,current);
    }
    HRESULT Bind(IDirect3DDevice9* device,const D3DMATRIX& world,
                 const D3DMATRIX& view,const D3DMATRIX& projection) noexcept {
        return BindGuarded(device,world,view,projection,[](){return true;});
    }
};
} // namespace OutRunVR::DinoSidecar