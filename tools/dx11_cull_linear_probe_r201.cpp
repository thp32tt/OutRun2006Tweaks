// R201: isolated WARP native non-indexed Draw verifies front-face/cull pixels.
#include "vr/d3d11/native_linear_cull_binding.hpp"
#include <cstdlib>
#include <cstdint>
#include <iostream>
#include <d3dcompiler.h>
#include <wrl/client.h>

using Microsoft::WRL::ComPtr;
using namespace outrun::vr::dx11;
static void require(bool ok, const char* reason) {
    if (!ok) { std::cerr << "R201 WARP failure: " << reason << '\n'; std::exit(1); }
}
int main() {
    ComPtr<ID3D11Device> dev;
    ComPtr<ID3D11DeviceContext> ctx;
    require(SUCCEEDED(D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_WARP,
        nullptr, 0, nullptr, 0, D3D11_SDK_VERSION, dev.GetAddressOf(),
        nullptr, ctx.GetAddressOf())), "WARP device");

    struct Vertex { float x,y; };
    constexpr Vertex vertices[]={{-1.f,-1.f},{0.f,1.f},{1.f,-1.f}};
    NativeLinearBufferMirror vb;
    constexpr std::uint64_t gen=201, version=72;
    require(vb.initialize(dev.Get(),ResourceRole::Vertex,D3DPOOL_DEFAULT,
        D3DUSAGE_WRITEONLY,D3DFMT_UNKNOWN,vertices,sizeof(vertices),
        sizeof(Vertex),gen,version),"owned VB snapshot");
    require(vb.bind(ctx.Get(),gen,version),"owned non-indexed IA");

    constexpr char shader[]=
        "float4 vs(float2 p:POSITION):SV_Position{return float4(p,0,1);}"
        "float4 ps():SV_Target{return float4(1,0,0,1);}";
    ComPtr<ID3DBlob> vsCode,psCode;
    require(SUCCEEDED(D3DCompile(shader,sizeof(shader)-1,nullptr,nullptr,nullptr,
        "vs","vs_4_0",0,0,vsCode.GetAddressOf(),nullptr)),"VS compile");
    require(SUCCEEDED(D3DCompile(shader,sizeof(shader)-1,nullptr,nullptr,nullptr,
        "ps","ps_4_0",0,0,psCode.GetAddressOf(),nullptr)),"PS compile");
    ComPtr<ID3D11VertexShader> vs;
    ComPtr<ID3D11PixelShader> ps;
    require(SUCCEEDED(dev->CreateVertexShader(vsCode->GetBufferPointer(),
        vsCode->GetBufferSize(),nullptr,vs.GetAddressOf())),"VS object");
    require(SUCCEEDED(dev->CreatePixelShader(psCode->GetBufferPointer(),
        psCode->GetBufferSize(),nullptr,ps.GetAddressOf())),"PS object");
    constexpr D3D11_INPUT_ELEMENT_DESC element={"POSITION",0,
        DXGI_FORMAT_R32G32_FLOAT,0,0,D3D11_INPUT_PER_VERTEX_DATA,0};
    ComPtr<ID3D11InputLayout> layout;
    require(SUCCEEDED(dev->CreateInputLayout(&element,1,
        vsCode->GetBufferPointer(),vsCode->GetBufferSize(),
        layout.GetAddressOf())),"input layout");
    ctx->IASetInputLayout(layout.Get());
    ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    ctx->VSSetShader(vs.Get(),nullptr,0);
    ctx->PSSetShader(ps.Get(),nullptr,0);

    D3D11_TEXTURE2D_DESC tex{};
    tex.Width=40;tex.Height=40;tex.MipLevels=1;tex.ArraySize=1;
    tex.Format=DXGI_FORMAT_R8G8B8A8_UNORM;tex.SampleDesc.Count=1;
    tex.Usage=D3D11_USAGE_DEFAULT;tex.BindFlags=D3D11_BIND_RENDER_TARGET;
    ComPtr<ID3D11Texture2D> target;
    ComPtr<ID3D11RenderTargetView> rtv;
    require(SUCCEEDED(dev->CreateTexture2D(&tex,nullptr,target.GetAddressOf())),
        "color texture");
    require(SUCCEEDED(dev->CreateRenderTargetView(target.Get(),nullptr,
        rtv.GetAddressOf())),"owned RTV");
    ID3D11RenderTargetView* raw=rtv.Get();
    ctx->OMSetRenderTargets(1,&raw,nullptr);
    const D3D11_VIEWPORT vp={0,0,40,40,0,1};
    ctx->RSSetViewports(1,&vp);

    D3D11_RASTERIZER_DESC rd{};
    rd.FillMode=D3D11_FILL_SOLID;
    rd.CullMode=D3D11_CULL_BACK;
    rd.DepthClipEnable=TRUE;
    rd.FrontCounterClockwise=FALSE;
    ComPtr<ID3D11RasterizerState> cw,ccw,noCull;
    require(SUCCEEDED(dev->CreateRasterizerState(&rd,cw.GetAddressOf())),
        "clockwise front raster");
    rd.FrontCounterClockwise=TRUE;
    require(SUCCEEDED(dev->CreateRasterizerState(&rd,ccw.GetAddressOf())),
        "counterclockwise front raster");
    rd.CullMode=D3D11_CULL_NONE;
    require(SUCCEEDED(dev->CreateRasterizerState(&rd,noCull.GetAddressOf())),
        "no cull raster");
    const auto ready=[&](ID3D11RasterizerState* state,bool frontCCW) {
        return verified_linear_cull_draw_ready(vb,ctx.Get(),0,3,gen,version,
            40,40,DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get(),state,
            D3D11_CULL_BACK,frontCCW);
    };
    ctx->RSSetState(cw.Get());
    require(ready(cw.Get(),false),"owned CW front state");
    require(!ready(cw.Get(),true),"reject stale front winding intent");
    require(!ready(ccw.Get(),true),"reject foreign bound raster state");
    require(!verified_linear_cull_draw_ready(vb,ctx.Get(),0,3,gen,version,
        40,40,DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get(),cw.Get(),
        D3D11_CULL_FRONT,false),"reject stale cull mode intent");
    require(!verified_linear_cull_draw_ready(vb,ctx.Get(),0,3,gen,version,
        40,40,DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get(),cw.Get(),
        D3D11_CULL_NONE,false),"reject cull-none expected mode");
    require(!verified_linear_cull_draw_ready(vb,ctx.Get(),0,3,gen+1,version,
        40,40,DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get(),cw.Get(),
        D3D11_CULL_BACK,false),"reject stale VB generation");
    ctx->RSSetState(noCull.Get());
    require(!ready(noCull.Get(),true),"reject disabled raster culling");
    ctx->RSSetState(cw.Get());

    tex.Usage=D3D11_USAGE_STAGING;tex.BindFlags=0;
    tex.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
    ComPtr<ID3D11Texture2D> staging;
    require(SUCCEEDED(dev->CreateTexture2D(&tex,nullptr,staging.GetAddressOf())),
        "WARP staging");
    constexpr FLOAT blue[]={0,0,1,1};
    const auto isRed=[&](ID3D11RasterizerState* state,bool winding) {
        ctx->RSSetState(state);
        require(ready(state,winding),"live cull readiness before WARP Draw");
        ctx->ClearRenderTargetView(rtv.Get(),blue);
        ctx->Draw(3,0);
        ctx->CopyResource(staging.Get(),target.Get());
        D3D11_MAPPED_SUBRESOURCE map{};
        require(SUCCEEDED(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,&map)) &&
            map.pData,"map WARP pixel");
        const auto* pixel=static_cast<const std::uint8_t*>(map.pData)
            +24*map.RowPitch+20*4;
        const bool red=pixel[0]==255&&pixel[1]==0&&pixel[2]==0&&pixel[3]==255;
        const bool bluePixel=pixel[0]==0&&pixel[1]==0&&pixel[2]==255&&pixel[3]==255;
        ctx->Unmap(staging.Get(),0);
        require(red||bluePixel,"unexpected GPU winding pixel");
        return red;
    };
    const bool cwVisible=isRed(cw.Get(),false);
    const bool ccwVisible=isRed(ccw.Get(),true);
    require(cwVisible!=ccwVisible,
        "actual non-indexed WARP Draw cull winding must flip GPU pixel");
    vb.shutdown();
    require(!ready(ccw.Get(),true),"reject retired VB generation owner");
    std::cout<<"R201 native non-indexed CullBack winding WARP Draw pixels: PASS\n";
}
