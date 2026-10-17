// R194: actual WARP triangle winding/cull polarity pixel readback. No gameplay path.
#include "vr/d3d11/native_indexed_cull_binding.hpp"
#include <cstdlib>
#include <cstdint>
#include <iostream>
#include <d3dcompiler.h>
#include <wrl/client.h>

using Microsoft::WRL::ComPtr;
using namespace outrun::vr::dx11;
static void require(bool ok, const char* reason) {
    if (!ok) { std::cerr << "R194 WARP failure: " << reason << '\n'; std::exit(1); }
}
int main() {
    ComPtr<ID3D11Device> device;
    ComPtr<ID3D11DeviceContext> ctx;
    require(SUCCEEDED(D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_WARP,
        nullptr, 0, nullptr, 0, D3D11_SDK_VERSION, device.GetAddressOf(),
        nullptr, ctx.GetAddressOf())), "create WARP device");
    struct Vertex { float x,y; };
    constexpr Vertex vertices[] = {{-1.f,-1.f},{0.f,1.f},{1.f,-1.f}};
    constexpr std::uint16_t indices[] = {0,1,2};
    constexpr std::uint64_t gen=194, vv=11, iv=12;
    NativeLinearBufferMirror vb, ib;
    require(vb.initialize(device.Get(),ResourceRole::Vertex,D3DPOOL_DEFAULT,
        D3DUSAGE_WRITEONLY,D3DFMT_UNKNOWN,vertices,sizeof(vertices),
        sizeof(Vertex),gen,vv), "vertex snapshot");
    require(ib.initialize(device.Get(),ResourceRole::Index,D3DPOOL_DEFAULT,
        D3DUSAGE_WRITEONLY,D3DFMT_INDEX16,indices,sizeof(indices),
        0,gen,iv), "index snapshot");
    require(vb.bind(ctx.Get(),gen,vv) && ib.bind(ctx.Get(),gen,iv), "owned IA");
    constexpr char code[]=
        "float4 vs(float2 p:POSITION):SV_Position{return float4(p,0,1);}"
        "float4 ps():SV_Target{return float4(1,0,0,1);}";
    ComPtr<ID3DBlob> vsBytecode, psBytecode;
    require(SUCCEEDED(D3DCompile(code,sizeof(code)-1,nullptr,nullptr,nullptr,
        "vs","vs_4_0",0,0,vsBytecode.GetAddressOf(),nullptr)), "VS compile");
    require(SUCCEEDED(D3DCompile(code,sizeof(code)-1,nullptr,nullptr,nullptr,
        "ps","ps_4_0",0,0,psBytecode.GetAddressOf(),nullptr)), "PS compile");
    ComPtr<ID3D11VertexShader> vs;
    ComPtr<ID3D11PixelShader> ps;
    require(SUCCEEDED(device->CreateVertexShader(vsBytecode->GetBufferPointer(),
        vsBytecode->GetBufferSize(),nullptr,vs.GetAddressOf())), "VS object");
    require(SUCCEEDED(device->CreatePixelShader(psBytecode->GetBufferPointer(),
        psBytecode->GetBufferSize(),nullptr,ps.GetAddressOf())), "PS object");
    const D3D11_INPUT_ELEMENT_DESC el = {"POSITION",0,DXGI_FORMAT_R32G32_FLOAT,
        0,0,D3D11_INPUT_PER_VERTEX_DATA,0};
    ComPtr<ID3D11InputLayout> layout;
    require(SUCCEEDED(device->CreateInputLayout(&el,1,
        vsBytecode->GetBufferPointer(),vsBytecode->GetBufferSize(),
        layout.GetAddressOf())), "IA layout");
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
    require(SUCCEEDED(device->CreateTexture2D(&td,nullptr,
        color.GetAddressOf())), "color target");
    require(SUCCEEDED(device->CreateRenderTargetView(color.Get(),nullptr,
        rtv.GetAddressOf())), "owned RTV");
    ID3D11RenderTargetView* rawRtv=rtv.Get();
    ctx->OMSetRenderTargets(1,&rawRtv,nullptr);
    const D3D11_VIEWPORT vp={0,0,40,40,0,1};
    ctx->RSSetViewports(1,&vp);

    D3D11_RASTERIZER_DESC rd{};
    rd.FillMode=D3D11_FILL_SOLID; rd.CullMode=D3D11_CULL_BACK;
    rd.DepthClipEnable=TRUE; rd.FrontCounterClockwise=FALSE;
    ComPtr<ID3D11RasterizerState> winding0,winding1,noCull;
    require(SUCCEEDED(device->CreateRasterizerState(&rd,
        winding0.GetAddressOf())), "clockwise front-state");
    rd.FrontCounterClockwise=TRUE;
    require(SUCCEEDED(device->CreateRasterizerState(&rd,
        winding1.GetAddressOf())), "counterclockwise front-state");
    rd.CullMode=D3D11_CULL_NONE;
    require(SUCCEEDED(device->CreateRasterizerState(&rd,
        noCull.GetAddressOf())), "culling disabled state");
    const auto ready=[&](ID3D11RasterizerState* rs,bool ccw) {
        return verified_indexed_cull_draw_ready(vb,ib,ctx.Get(),0,3,0,
            gen,vv,iv,40,40,DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get(),
            rs,D3D11_CULL_BACK,ccw);
    };
    ctx->RSSetState(winding0.Get());
    require(ready(winding0.Get(),false), "owned clockwise cull");
    require(!ready(winding0.Get(),true), "reject stale winding intent");
    require(!ready(winding1.Get(),true), "reject stale bound raster owner");
    require(!verified_indexed_cull_draw_ready(vb,ib,ctx.Get(),0,3,0,
        gen,vv,iv,40,40,DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get(),
        winding0.Get(),D3D11_CULL_FRONT,false), "reject stale cull intent");
    require(!verified_indexed_cull_draw_ready(vb,ib,ctx.Get(),0,3,0,
        gen,vv,iv,40,40,DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get(),
        winding0.Get(),D3D11_CULL_NONE,false), "reject cull-none intent");
    require(!verified_indexed_cull_draw_ready(vb,ib,ctx.Get(),0,3,0,
        gen+1,vv,iv,40,40,DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get(),
        winding0.Get(),D3D11_CULL_BACK,false), "reject stale generation");
    ctx->RSSetState(noCull.Get());
    require(!ready(noCull.Get(),true), "reject disabled raster cull");
    ctx->RSSetState(winding0.Get());
    td.Usage=D3D11_USAGE_STAGING; td.BindFlags=0;
    td.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
    ComPtr<ID3D11Texture2D> staging;
    require(SUCCEEDED(device->CreateTexture2D(&td,nullptr,
        staging.GetAddressOf())), "staging readback");
    const FLOAT blue[]={0,0,1,1};
    const auto renderedRed=[&](ID3D11RasterizerState* rs,bool ccw) {
        ctx->RSSetState(rs);
        require(ready(rs,ccw), "live raster cull preflight");
        ctx->ClearRenderTargetView(rtv.Get(),blue);
        ctx->DrawIndexed(3,0,0);
        ctx->CopyResource(staging.Get(),color.Get());
        D3D11_MAPPED_SUBRESOURCE mapped{};
        require(SUCCEEDED(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,&mapped))
            && mapped.pData, "actual WARP map");
        const auto* b=static_cast<const std::uint8_t*>(mapped.pData)
            +24*mapped.RowPitch+20*4;
        const bool red=b[0]==255 && b[1]==0 && b[2]==0 && b[3]==255;
        const bool bluePixel=b[0]==0 && b[1]==0 && b[2]==255 && b[3]==255;
        ctx->Unmap(staging.Get(),0);
        require(red || bluePixel, "unexpected raster GPU pixel");
        return red;
    };
    const bool clockwise=renderedRed(winding0.Get(),false);
    const bool counterclockwise=renderedRed(winding1.Get(),true);
    require(clockwise != counterclockwise,
        "WARP winding polarity must flip DrawIndexed pixel visibility");
    ib.shutdown();
    require(!ready(winding1.Get(),true), "reject retired index snapshot");
    std::cout << "R194 real WARP CullBack winding-polarity DrawIndexed pixels: PASS\n";
}
