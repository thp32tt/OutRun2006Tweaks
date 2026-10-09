// R190 isolated Win32 WARP: owned alpha blending with real indexed GPU pixels.
#include "vr/d3d11/native_indexed_blend_binding.hpp"
#include <cstdlib>
#include <iostream>
#include <cstdint>
#include <d3dcompiler.h>
#include <wrl/client.h>
using Microsoft::WRL::ComPtr;
using namespace outrun::vr::dx11;
static void require(bool ok, const char* reason) {
    if (!ok) { std::cerr << "R190 WARP failed: " << reason << '\n'; std::exit(1); }
}
int main() {
    ComPtr<ID3D11Device> dev;
    ComPtr<ID3D11DeviceContext> ctx;
    require(SUCCEEDED(D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_WARP, nullptr, 0,
        nullptr, 0, D3D11_SDK_VERSION, dev.GetAddressOf(), nullptr,
        ctx.GetAddressOf())), "WARP device");
    struct Vertex { float x, y; };
    const Vertex vertices[]={{-.8f,-.8f},{0.f,.8f},{.8f,-.8f}};
    const std::uint16_t indices[]={0,1,2};
    NativeLinearBufferMirror vb,ib;
    constexpr std::uint64_t gen=190, vv=61, iv=62;
    require(vb.initialize(dev.Get(),ResourceRole::Vertex,D3DPOOL_DEFAULT,
        D3DUSAGE_WRITEONLY,D3DFMT_UNKNOWN,vertices,sizeof(vertices),
        sizeof(Vertex),gen,vv), "vertex owner");
    require(ib.initialize(dev.Get(),ResourceRole::Index,D3DPOOL_DEFAULT,
        D3DUSAGE_WRITEONLY,D3DFMT_INDEX16,indices,sizeof(indices),
        0,gen,iv), "index owner");
    require(vb.bind(ctx.Get(),gen,vv) && ib.bind(ctx.Get(),gen,iv), "bind owned IA");
    constexpr char shader[]=
        "float4 vs(float2 p:POSITION):SV_Position{return float4(p,0,1);}"
        "float4 ps():SV_Target{return float4(1,0,0,0.5);}";
    ComPtr<ID3DBlob> vsCode,psCode;
    require(SUCCEEDED(D3DCompile(shader,sizeof(shader)-1,nullptr,nullptr,nullptr,
        "vs","vs_4_0",0,0,vsCode.GetAddressOf(),nullptr)), "VS compile");
    require(SUCCEEDED(D3DCompile(shader,sizeof(shader)-1,nullptr,nullptr,nullptr,
        "ps","ps_4_0",0,0,psCode.GetAddressOf(),nullptr)), "PS compile");
    ComPtr<ID3D11VertexShader> vs;
    ComPtr<ID3D11PixelShader> ps;
    require(SUCCEEDED(dev->CreateVertexShader(vsCode->GetBufferPointer(),
        vsCode->GetBufferSize(),nullptr,vs.GetAddressOf())), "VS");
    require(SUCCEEDED(dev->CreatePixelShader(psCode->GetBufferPointer(),
        psCode->GetBufferSize(),nullptr,ps.GetAddressOf())), "PS");
    const D3D11_INPUT_ELEMENT_DESC element={"POSITION",0,DXGI_FORMAT_R32G32_FLOAT,
        0,0,D3D11_INPUT_PER_VERTEX_DATA,0};
    ComPtr<ID3D11InputLayout> layout;
    require(SUCCEEDED(dev->CreateInputLayout(&element,1,vsCode->GetBufferPointer(),
        vsCode->GetBufferSize(),layout.GetAddressOf())), "input layout");
    ctx->IASetInputLayout(layout.Get());
    ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    ctx->VSSetShader(vs.Get(),nullptr,0);
    ctx->PSSetShader(ps.Get(),nullptr,0);
    D3D11_TEXTURE2D_DESC td{};
    td.Width=40; td.Height=40; td.MipLevels=1; td.ArraySize=1;
    td.Format=DXGI_FORMAT_R8G8B8A8_UNORM; td.SampleDesc.Count=1;
    td.Usage=D3D11_USAGE_DEFAULT; td.BindFlags=D3D11_BIND_RENDER_TARGET;
    ComPtr<ID3D11Texture2D> color;
    ComPtr<ID3D11RenderTargetView> rtv;
    require(SUCCEEDED(dev->CreateTexture2D(&td,nullptr,color.GetAddressOf())),
        "color texture");
    require(SUCCEEDED(dev->CreateRenderTargetView(color.Get(),nullptr,
        rtv.GetAddressOf())), "RTV");
    ID3D11RenderTargetView* raw=rtv.Get();
    ctx->OMSetRenderTargets(1,&raw,nullptr);
    const D3D11_VIEWPORT vp{0,0,40,40,0,1};
    ctx->RSSetViewports(1,&vp);
    D3D11_RASTERIZER_DESC rd{};
    rd.FillMode=D3D11_FILL_SOLID; rd.CullMode=D3D11_CULL_NONE;
    rd.DepthClipEnable=TRUE;
    ComPtr<ID3D11RasterizerState> raster;
    require(SUCCEEDED(dev->CreateRasterizerState(&rd,raster.GetAddressOf())),
        "rasterizer");
    ctx->RSSetState(raster.Get());

    D3D11_BLEND_DESC bd{};
    auto& rt=bd.RenderTarget[0];
    rt.BlendEnable=TRUE;
    rt.SrcBlend=D3D11_BLEND_SRC_ALPHA;
    rt.DestBlend=D3D11_BLEND_INV_SRC_ALPHA;
    rt.BlendOp=D3D11_BLEND_OP_ADD;
    rt.SrcBlendAlpha=D3D11_BLEND_ONE;
    rt.DestBlendAlpha=D3D11_BLEND_ZERO;
    rt.BlendOpAlpha=D3D11_BLEND_OP_ADD;
    rt.RenderTargetWriteMask=D3D11_COLOR_WRITE_ENABLE_ALL;
    ComPtr<ID3D11BlendState> alphaBlend, opaqueBlend, zeroWriteBlend;
    require(SUCCEEDED(dev->CreateBlendState(&bd,alphaBlend.GetAddressOf())),
        "alpha blend state");
    rt.BlendEnable=FALSE;
    require(SUCCEEDED(dev->CreateBlendState(&bd,opaqueBlend.GetAddressOf())),
        "opaque state");
    rt.BlendEnable=TRUE; rt.RenderTargetWriteMask=0;
    require(SUCCEEDED(dev->CreateBlendState(&bd,zeroWriteBlend.GetAddressOf())),
        "zero-write state");
    constexpr FLOAT ones[4]={1.f,1.f,1.f,1.f};
    const FLOAT staleFactor[4]={0.f,1.f,1.f,1.f};
    ctx->OMSetBlendState(alphaBlend.Get(),ones,D3D11_DEFAULT_SAMPLE_MASK);
    const auto ready=[&]() {
        return verified_indexed_blend_draw_ready(vb,ib,ctx.Get(),0,3,0,gen,
            vv,iv,40,40,DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get(),alphaBlend.Get());
    };
    require(ready(),"baseline exact owned blend state");
    require(!verified_indexed_blend_draw_ready(vb,ib,ctx.Get(),0,3,0,gen,
        vv,iv,40,40,DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get(),nullptr),
        "reject missing expected blend state");
    ctx->OMSetBlendState(opaqueBlend.Get(),ones,D3D11_DEFAULT_SAMPLE_MASK);
    require(!ready(),"reject rebound opaque blend");
    ctx->OMSetBlendState(zeroWriteBlend.Get(),ones,D3D11_DEFAULT_SAMPLE_MASK);
    require(!verified_indexed_blend_draw_ready(vb,ib,ctx.Get(),0,3,0,gen,
        vv,iv,40,40,DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get(),zeroWriteBlend.Get()),
        "reject disabled color write mask");
    ctx->OMSetBlendState(alphaBlend.Get(),staleFactor,D3D11_DEFAULT_SAMPLE_MASK);
    require(!ready(),"reject stale blend factors");
    ctx->OMSetBlendState(alphaBlend.Get(),ones,0u);
    require(!ready(),"reject zero sample mask");
    ctx->OMSetBlendState(alphaBlend.Get(),ones,D3D11_DEFAULT_SAMPLE_MASK);
    require(ready(),"restored blend");
    const FLOAT blue[]={0.f,0.f,1.f,1.f};
    ctx->ClearRenderTargetView(rtv.Get(),blue);
    require(ready(),"preflight indexed GPU blend");
    ctx->DrawIndexed(3,0,0);
    td.Usage=D3D11_USAGE_STAGING; td.BindFlags=0;
    td.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
    ComPtr<ID3D11Texture2D> staging;
    require(SUCCEEDED(dev->CreateTexture2D(&td,nullptr,staging.GetAddressOf())),
        "staging");
    ctx->CopyResource(staging.Get(),color.Get());
    D3D11_MAPPED_SUBRESOURCE mapped{};
    require(SUCCEEDED(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,&mapped)) &&
        mapped.pData,"map actual WARP pixels");
    const auto* pixels=static_cast<const unsigned char*>(mapped.pData);
    const auto* center=pixels+20*mapped.RowPitch+20*4;
    const auto* corner=pixels+1*mapped.RowPitch+1*4;
    const bool rgba=(center[0]>=127 && center[0]<=129 &&
        center[1]==0 && center[2]>=126 && center[2]<=129 &&
        center[3]>=127 && center[3]<=129 &&
        corner[0]==0 && corner[1]==0 &&
        corner[2]==255 && corner[3]==255);
    ctx->Unmap(staging.Get(),0);
    require(rgba,"actual alpha blended DrawIndexed purple center / blue corner");
    ib.shutdown();
    require(!ready(),"reject retired IB owner");
    std::cout<<"R190 native indexed alpha OM WARP GPU pixels: PASS\n";
}
