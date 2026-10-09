// R193: isolated actual WARP DrawIndexed scissor coverage, never game activation.
#include "vr/d3d11/native_indexed_scissor_binding.hpp"
#include <cstdlib>
#include <cstdint>
#include <iostream>
#include <d3dcompiler.h>
#include <wrl/client.h>
using Microsoft::WRL::ComPtr;
using namespace outrun::vr::dx11;
static void require(bool ok, const char* why) {
    if (!ok) { std::cerr << "R193 WARP failed: " << why << '\n'; std::exit(1); }
}
int main() {
    ComPtr<ID3D11Device> dev;
    ComPtr<ID3D11DeviceContext> ctx;
    require(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,
        nullptr,0,D3D11_SDK_VERSION,dev.GetAddressOf(),nullptr,
        ctx.GetAddressOf())), "WARP device");
    struct Vertex { float x,y; };
    const Vertex vertices[]={{-1.f,-1.f},{0.f,1.f},{1.f,-1.f}};
    const std::uint16_t indices[]={0,1,2};
    NativeLinearBufferMirror vb,ib;
    constexpr std::uint64_t gen=193, vv=101, iv=102;
    require(vb.initialize(dev.Get(),ResourceRole::Vertex,D3DPOOL_DEFAULT,
        D3DUSAGE_WRITEONLY,D3DFMT_UNKNOWN,vertices,sizeof(vertices),
        sizeof(Vertex),gen,vv),"vertex owner");
    require(ib.initialize(dev.Get(),ResourceRole::Index,D3DPOOL_DEFAULT,
        D3DUSAGE_WRITEONLY,D3DFMT_INDEX16,indices,sizeof(indices),
        0,gen,iv),"index owner");
    require(vb.bind(ctx.Get(),gen,vv) && ib.bind(ctx.Get(),gen,iv),"owned IA");
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
        vsCode->GetBufferSize(),nullptr,vs.GetAddressOf())),"VS");
    require(SUCCEEDED(dev->CreatePixelShader(psCode->GetBufferPointer(),
        psCode->GetBufferSize(),nullptr,ps.GetAddressOf())),"PS");
    const D3D11_INPUT_ELEMENT_DESC position={"POSITION",0,
        DXGI_FORMAT_R32G32_FLOAT,0,0,D3D11_INPUT_PER_VERTEX_DATA,0};
    ComPtr<ID3D11InputLayout> layout;
    require(SUCCEEDED(dev->CreateInputLayout(&position,1,
        vsCode->GetBufferPointer(),vsCode->GetBufferSize(),
        layout.GetAddressOf())),"layout");
    ctx->IASetInputLayout(layout.Get());
    ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    ctx->VSSetShader(vs.Get(),nullptr,0);
    ctx->PSSetShader(ps.Get(),nullptr,0);
    D3D11_TEXTURE2D_DESC td{};
    td.Width=40;td.Height=40;td.MipLevels=1;td.ArraySize=1;
    td.Format=DXGI_FORMAT_R8G8B8A8_UNORM;td.SampleDesc.Count=1;
    td.Usage=D3D11_USAGE_DEFAULT;td.BindFlags=D3D11_BIND_RENDER_TARGET;
    ComPtr<ID3D11Texture2D> color;
    ComPtr<ID3D11RenderTargetView> rtv;
    require(SUCCEEDED(dev->CreateTexture2D(&td,nullptr,color.GetAddressOf())),
        "color target");
    require(SUCCEEDED(dev->CreateRenderTargetView(color.Get(),nullptr,
        rtv.GetAddressOf())),"RTV");
    ID3D11RenderTargetView* raw=rtv.Get();
    ctx->OMSetRenderTargets(1,&raw,nullptr);
    const D3D11_VIEWPORT vp={0,0,40,40,0,1};
    ctx->RSSetViewports(1,&vp);
    D3D11_RASTERIZER_DESC rd{};
    rd.FillMode=D3D11_FILL_SOLID;
    rd.CullMode=D3D11_CULL_NONE;
    rd.DepthClipEnable=TRUE;
    rd.ScissorEnable=TRUE;
    ComPtr<ID3D11RasterizerState> clipped,unclipped;
    require(SUCCEEDED(dev->CreateRasterizerState(&rd,clipped.GetAddressOf())),
        "owned scissor raster");
    rd.ScissorEnable=FALSE;
    require(SUCCEEDED(dev->CreateRasterizerState(&rd,unclipped.GetAddressOf())),
        "disabled scissor raster");
    const D3D11_RECT rect={0,0,20,40};
    const D3D11_RECT stale={0,0,40,40};
    ctx->RSSetState(clipped.Get());
    ctx->RSSetScissorRects(1,&rect);
    const auto ready=[&]() {
        return verified_indexed_scissor_draw_ready(vb,ib,ctx.Get(),0,3,0,
            gen,vv,iv,40,40,DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get(),
            clipped.Get(),rect);
    };
    require(ready(),"live exact owner and clip");
    require(!verified_indexed_scissor_draw_ready(vb,ib,ctx.Get(),0,3,0,
        gen,vv,iv,40,40,DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get(),
        clipped.Get(),stale),"reject caller stale scissor");
    ctx->RSSetScissorRects(1,&stale);
    require(!ready(),"reject rebound scissor");
    ctx->RSSetScissorRects(1,&rect);
    ctx->RSSetState(unclipped.Get());
    require(!ready(),"reject wrong raster state owner");
    require(!verified_indexed_scissor_draw_ready(vb,ib,ctx.Get(),0,3,0,
        gen,vv,iv,40,40,DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get(),
        unclipped.Get(),rect),"reject scissor-disabled state");
    ctx->RSSetState(clipped.Get());
    require(!verified_indexed_scissor_draw_ready(vb,ib,ctx.Get(),0,3,0,
        gen+1,vv,iv,40,40,DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get(),
        clipped.Get(),rect),"reject wrong generation");
    require(ready(),"restored exact scissor");
    const FLOAT blue[]={0,0,1,1};
    ctx->ClearRenderTargetView(rtv.Get(),blue);
    require(ready(),"before live WARP indexed draw");
    ctx->DrawIndexed(3,0,0);
    td.Usage=D3D11_USAGE_STAGING;td.BindFlags=0;
    td.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
    ComPtr<ID3D11Texture2D> staging;
    require(SUCCEEDED(dev->CreateTexture2D(&td,nullptr,
        staging.GetAddressOf())),"readback texture");
    ctx->CopyResource(staging.Get(),color.Get());
    D3D11_MAPPED_SUBRESOURCE map{};
    require(SUCCEEDED(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,&map)) &&
        map.pData,"map actual WARP pixels");
    const auto* bytes=static_cast<const std::uint8_t*>(map.pData);
    const auto* inside=bytes+24*map.RowPitch+12*4;
    const auto* outside=bytes+24*map.RowPitch+28*4;
    const bool correct=inside[0]==255 && inside[1]==0 &&
        inside[2]==0 && inside[3]==255 &&
        outside[0]==0 && outside[1]==0 &&
        outside[2]==255 && outside[3]==255;
    ctx->Unmap(staging.Get(),0);
    require(correct,"GPU red inside owned left clip and blue outside");
    ib.shutdown();
    require(!ready(),"reject retired IB owner");
    std::cout << "R193 live WARP scissored indexed pixels: PASS\n";
}
