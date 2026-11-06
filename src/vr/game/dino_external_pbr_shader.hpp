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

namespace OutRunVR::DinoSidecar {
class PbrShaders final {
    IDirect3DVertexShader9* vs_=nullptr;
    IDirect3DPixelShader9* ps_=nullptr;
    bool attempted_=false;
    static constexpr const char* VertexSource() noexcept {
        return R"HLSL(
row_major float4x4 world : register(c0);
row_major float4x4 view : register(c4);
row_major float4x4 projection : register(c8);
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
    o.worldNormal = normalize(mul(input.normal, (float3x3)world));
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
    float3 N = normalize(input.worldNormal);
    // Derivative TBN handles source FVF XYZ/NORMAL/UV without altered vertex stride.
    // Handedness is preserved for mirrored texture islands (negative UV determinant).
    float3 dpdx = ddx(input.worldPosition);
    float3 dpdy = ddy(input.worldPosition);
    float2 dtdx = ddx(input.uv);
    float2 dtdy = ddy(input.uv);
    float det = dtdx.x*dtdy.y-dtdx.y*dtdy.x;
    if (factors.w > 0.5 && abs(det) > 0.0000001) {
        float3 T = normalize(dpdx*dtdy.y-dpdy*dtdx.y);
        T = normalize(T-N*dot(N,T));
        float3 B = normalize(cross(N,T))*(det < 0 ? -1 : 1);
        float3 mapN = tex2D(normalMap,input.uv).xyz*2.0-1.0;
        mapN.xy *= factors.z;
        N = normalize(mapN.x*T+mapN.y*B+mapN.z*N);
    }
    float3 L = normalize(float3(-0.45,0.85,-0.28));
    float3 V = normalize(eyeAndOrm.xyz-input.worldPosition);
    float3 H = normalize(L+V);
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
    float3 specular = distribution*geometry*fresnel/(4*NL*NV+0.001);
    float3 diffuse = (1-fresnel)*(1-metallic)*albedo/pi;
    float3 radiance = (diffuse+specular)*NL*2.0;
    float3 ambient = ao*(albedo*(1-metallic)*0.16+F0*0.045);
    float3 linearColor = saturate(radiance+ambient);
    return float4(pow(linearColor,1.0/2.2),base.a);
}
)HLSL";
    }
public:
    static constexpr const char* VertexHlsl() noexcept {return VertexSource();}
    static constexpr const char* PixelHlsl() noexcept {return PixelSource();}
    PbrShaders()=default;
    ~PbrShaders(){Release();}
    PbrShaders(const PbrShaders&)=delete;
    PbrShaders& operator=(const PbrShaders&)=delete;
    void Release() noexcept {
        if(vs_){vs_->Release();vs_=nullptr;}
        if(ps_){ps_->Release();ps_=nullptr;}
        attempted_=false;
    }
    bool Ensure(IDirect3DDevice9* device) noexcept {
        if(!device)return false;
        if(attempted_)return vs_ && ps_;
        attempted_=true; // never retry shader compilation every stereo eye
        D3DCAPS9 caps{};
        if(FAILED(device->GetDeviceCaps(&caps)) ||
           caps.VertexShaderVersion<D3DVS_VERSION(3,0) ||
           caps.PixelShaderVersion<D3DPS_VERSION(3,0))return false;
        HMODULE dll=LoadLibraryW(L"d3dcompiler_47.dll");
        if(!dll)return false; // clean fixed-function fallback
        using Compile=HRESULT (WINAPI *)(LPCVOID,SIZE_T,LPCSTR,
            const D3D_SHADER_MACRO*,ID3DInclude*,LPCSTR,LPCSTR,
            UINT,UINT,ID3DBlob**,ID3DBlob**);
        const auto compile=reinterpret_cast<Compile>(GetProcAddress(dll,"D3DCompile"));
        if(!compile){FreeLibrary(dll);return false;}
        ID3DBlob *vsCode=nullptr,*psCode=nullptr,*errors=nullptr;
        constexpr UINT flags=D3DCOMPILE_PACK_MATRIX_ROW_MAJOR|D3DCOMPILE_OPTIMIZATION_LEVEL3;
        HRESULT hr=compile(VertexSource(),std::strlen(VertexSource()),
                           "DinoPbrVS",nullptr,nullptr,"mainVS","vs_3_0",
                           flags,0,&vsCode,&errors);
        if(errors){errors->Release();errors=nullptr;}
        if(SUCCEEDED(hr))
            hr=compile(PixelSource(),std::strlen(PixelSource()),
                       "DinoPbrPS",nullptr,nullptr,"mainPS","ps_3_0",
                       flags,0,&psCode,&errors);
        if(errors)errors->Release();
        if(SUCCEEDED(hr) && vsCode && psCode)
            hr=device->CreateVertexShader(
                static_cast<const DWORD*>(vsCode->GetBufferPointer()),&vs_);
        if(SUCCEEDED(hr) && vs_ && psCode)
            hr=device->CreatePixelShader(
                static_cast<const DWORD*>(psCode->GetBufferPointer()),&ps_);
        if(vsCode)vsCode->Release();
        if(psCode)psCode->Release();
        FreeLibrary(dll);
        if(FAILED(hr)||!vs_||!ps_) {
            if(vs_){vs_->Release();vs_=nullptr;}
            if(ps_){ps_->Release();ps_=nullptr;}
            return false;
        }
        return true;
    }
    HRESULT Bind(IDirect3DDevice9* device,const D3DMATRIX& world,
                 const D3DMATRIX& view,const D3DMATRIX& projection) noexcept {
        if(!device||!vs_||!ps_)return E_FAIL;
        float eye[4]{
            -(view._41*view._11+view._42*view._12+view._43*view._13),
            -(view._41*view._21+view._42*view._22+view._43*view._23),
            -(view._41*view._31+view._42*view._32+view._43*view._33),0.f};
        return FAILED(device->SetVertexShader(vs_)) ||
               FAILED(device->SetPixelShader(ps_)) ||
               FAILED(device->SetVertexShaderConstantF(0,&world.m[0][0],4)) ||
               FAILED(device->SetVertexShaderConstantF(4,&view.m[0][0],4)) ||
               FAILED(device->SetVertexShaderConstantF(8,&projection.m[0][0],4)) ||
               FAILED(device->SetPixelShaderConstantF(1,eye,1)) ? E_FAIL:S_OK;
    }
};
} // namespace OutRunVR::DinoSidecar
