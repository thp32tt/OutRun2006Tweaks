// R187 isolated WARP indexed Draw: target geometry, viewport, scissor, pixels.
#include "vr/d3d11/native_indexed_target_viewport.hpp"
#include <cstdlib>
#include <iostream>
#include <cstdint>
#include <d3dcompiler.h>
#include <wrl/client.h>
using Microsoft::WRL::ComPtr;
using namespace outrun::vr::dx11;
static void require(bool b, const char* reason) {
    if (!b) { std::cerr << "R187 WARP failed: " << reason << '\n'; std::exit(1); }
}
int main() {
    ComPtr<ID3D11Device> dev;
    ComPtr<ID3D11DeviceContext> ctx;
    require(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,
        nullptr,0,nullptr,0,D3D11_SDK_VERSION,
        dev.GetAddressOf(),nullptr,ctx.GetAddressOf())), "create WARP");
    struct V {float x,y;};
    const V vertices[]={{-.8f,-.8f},{0.f,.8f},{.8f,-.8f}};
    const std::uint16_t indices[]={0,1,2};
    NativeLinearBufferMirror vb,ib;
    constexpr std::uint64_t gen=187, vv=31, iv=32;
    require(vb.initialize(dev.Get(),ResourceRole::Vertex,D3DPOOL_DEFAULT,
        D3DUSAGE_WRITEONLY,D3DFMT_UNKNOWN,vertices,sizeof(vertices),
        sizeof(V),gen,vv), "init VB");
    require(ib.initialize(dev.Get(),ResourceRole::Index,D3DPOOL_DEFAULT,
        D3DUSAGE_WRITEONLY,D3DFMT_INDEX16,indices,sizeof(indices),
        0,gen,iv), "init IB");
    require(vb.bind(ctx.Get(),gen,vv) && ib.bind(ctx.Get(),gen,iv), "bind VB/IB");
    constexpr char shader[] =
        "float4 vs(float2 p:POSITION):SV_Position{return float4(p,0,1);}"
        "float4 ps():SV_Target{return float4(0,1,0,1);}";
    ComPtr<ID3DBlob> vcode,pcode;
    require(SUCCEEDED(D3DCompile(shader,sizeof(shader)-1,nullptr,nullptr,
        nullptr,"vs","vs_4_0",0,0,vcode.GetAddressOf(),nullptr)), "VS compile");
    require(SUCCEEDED(D3DCompile(shader,sizeof(shader)-1,nullptr,nullptr,
        nullptr,"ps","ps_4_0",0,0,pcode.GetAddressOf(),nullptr)), "PS compile");
    ComPtr<ID3D11VertexShader> vs;
    ComPtr<ID3D11PixelShader> ps;
    require(SUCCEEDED(dev->CreateVertexShader(vcode->GetBufferPointer(),
        vcode->GetBufferSize(),nullptr,vs.GetAddressOf())), "VS create");
    require(SUCCEEDED(dev->CreatePixelShader(pcode->GetBufferPointer(),
        pcode->GetBufferSize(),nullptr,ps.GetAddressOf())), "PS create");
    const D3D11_INPUT_ELEMENT_DESC e={
        "POSITION",0,DXGI_FORMAT_R32G32_FLOAT,0,0,D3D11_INPUT_PER_VERTEX_DATA,0};
    ComPtr<ID3D11InputLayout> layout;
    require(SUCCEEDED(dev->CreateInputLayout(&e,1,vcode->GetBufferPointer(),
        vcode->GetBufferSize(),layout.GetAddressOf())), "layout");
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
    require(SUCCEEDED(dev->CreateTexture2D(&td,nullptr,color.GetAddressOf())), "color");
    require(SUCCEEDED(dev->CreateRenderTargetView(color.Get(),nullptr,rtv.GetAddressOf())), "RTV");
    ID3D11RenderTargetView* raw=rtv.Get();
    ctx->OMSetRenderTargets(1,&raw,nullptr);
    // Deliberately allocate a second fully valid same-size/format target.
    // The old geometry-only guard accepted this stale/wrong-eye binding.
    ComPtr<ID3D11Texture2D> wrongColor;
    ComPtr<ID3D11RenderTargetView> wrongRtv;
    require(SUCCEEDED(dev->CreateTexture2D(&td,nullptr,wrongColor.GetAddressOf())),
        "wrong-eye color");
    require(SUCCEEDED(dev->CreateRenderTargetView(wrongColor.Get(),nullptr,
        wrongRtv.GetAddressOf())), "wrong-eye RTV");
    td.Usage=D3D11_USAGE_STAGING; td.BindFlags=0; td.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
    ComPtr<ID3D11Texture2D> staging;
    require(SUCCEEDED(dev->CreateTexture2D(&td,nullptr,staging.GetAddressOf())), "staging");
    const D3D11_VIEWPORT full{0,0,40,40,0,1};
    ctx->RSSetViewports(1,&full);
    D3D11_RASTERIZER_DESC raster{};
    raster.FillMode=D3D11_FILL_SOLID; raster.CullMode=D3D11_CULL_NONE;
    raster.DepthClipEnable=TRUE;
    ComPtr<ID3D11RasterizerState> safe, clipped;
    require(SUCCEEDED(dev->CreateRasterizerState(&raster,safe.GetAddressOf())), "raster");
    raster.ScissorEnable=TRUE;
    require(SUCCEEDED(dev->CreateRasterizerState(&raster,clipped.GetAddressOf())), "scissor raster");
    ctx->RSSetState(safe.Get());
    const auto ready=[&](UINT w=40,UINT h=40,
                         DXGI_FORMAT f=DXGI_FORMAT_R8G8B8A8_UNORM) {
        return verified_indexed_full_target_draw_ready(
            vb,ib,ctx.Get(),0,3,0,gen,vv,iv,w,h,f,rtv.Get());
    };
    require(ready(), "baseline native indexed viewport ready");
    require(!verified_indexed_full_target_draw_ready(
        vb,ib,ctx.Get(),0,3,0,gen,vv,iv,40,40,
        DXGI_FORMAT_R8G8B8A8_UNORM,nullptr), "reject null expected RTV");
    ID3D11RenderTargetView* wrongRaw=wrongRtv.Get();
    ctx->OMSetRenderTargets(1,&wrongRaw,nullptr);
    require(!ready(), "reject same-sized different RTV");
    ctx->OMSetRenderTargets(1,&raw,nullptr);
    require(ready(), "restore original owned RTV");
    require(!ready(41,40), "reject wrong target width");
    require(!ready(40,40,DXGI_FORMAT_R8G8B8A8_UNORM_SRGB), "reject wrong view format");
    ctx->RSSetViewports(0,nullptr);
    require(!ready(), "reject missing viewport");
    const D3D11_VIEWPORT two[]={full,full};
    ctx->RSSetViewports(2,two);
    require(!ready(), "reject extra viewport");
    D3D11_VIEWPORT half=full; half.Width=20;
    ctx->RSSetViewports(1,&half);
    require(!ready(), "reject half viewport");
    ctx->RSSetViewports(1,&full);
    ctx->RSSetState(clipped.Get());
    require(!ready(), "reject scissor enabled");
    ctx->RSSetState(safe.Get());
    ctx->OMSetRenderTargets(0,nullptr,nullptr);
    require(!ready(), "reject missing bound RTV");
    ctx->OMSetRenderTargets(1,&raw,nullptr);
    require(ready(), "restored exact target/viewport");
    const float black[]={0,0,0,1};
    ctx->ClearRenderTargetView(rtv.Get(),black);
    // Real GPU draw is restricted to this isolated probe.
    ctx->DrawIndexed(3,0,0);
    ctx->CopyResource(staging.Get(),color.Get());
    D3D11_MAPPED_SUBRESOURCE map{};
    require(SUCCEEDED(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,&map)) &&
        map.pData, "map WARP pixels");
    const auto* px=static_cast<const unsigned char*>(map.pData);
    const auto* center=px+20*map.RowPitch+20*4;
    const auto* corner=px+1*map.RowPitch+1*4;
    const bool pixels=center[0]==0 && center[1]==255 &&
        center[2]==0 && center[3]==255 && corner[0]==0 &&
        corner[1]==0 && corner[2]==0 && corner[3]==255;
    ctx->Unmap(staging.Get(),0);
    require(pixels, "actual DrawIndexed green center / black corner pixels");
    ib.shutdown();
    require(!ready(), "reject retired IB");
    std::cout << "R187 exact viewport/RTV indexed WARP pixels: PASS\n";
}
