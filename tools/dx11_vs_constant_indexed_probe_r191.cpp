// R191 isolated actual WARP DrawIndexed: vertex translation comes from owned VS b0.
// No D3D9 gameplay Draw or backend activation.
#include "vr/d3d11/native_indexed_vs_constant.hpp"
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <d3dcompiler.h>
#include <wrl/client.h>
using Microsoft::WRL::ComPtr;
using namespace outrun::vr::dx11;
static void require(bool ok, const char* why) {
    if (!ok) { std::cerr << "R191 WARP failed: " << why << '\n'; std::exit(1); }
}
int main() {
    ComPtr<ID3D11Device> dev;
    ComPtr<ID3D11DeviceContext> ctx;
    require(SUCCEEDED(D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_WARP, nullptr, 0,
        nullptr, 0, D3D11_SDK_VERSION, dev.GetAddressOf(), nullptr,
        ctx.GetAddressOf())), "create WARP device");
    struct V { float x, y; };
    const V vertices[]={{-.8f,-.8f},{0.f,.8f},{.8f,-.8f}};
    const std::uint16_t indices[]={0,1,2};
    NativeLinearBufferMirror vb, ib;
    constexpr std::uint64_t gen=191, vv=71, iv=72;
    require(vb.initialize(dev.Get(),ResourceRole::Vertex,D3DPOOL_DEFAULT,
        D3DUSAGE_WRITEONLY,D3DFMT_UNKNOWN,vertices,sizeof(vertices),
        sizeof(V),gen,vv), "VB resource");
    require(ib.initialize(dev.Get(),ResourceRole::Index,D3DPOOL_DEFAULT,
        D3DUSAGE_WRITEONLY,D3DFMT_INDEX16,indices,sizeof(indices),
        0,gen,iv), "IB resource");
    require(vb.bind(ctx.Get(),gen,vv) && ib.bind(ctx.Get(),gen,iv),
        "bind owned VB/IB");
    constexpr char shader[]=
        "cbuffer Transform : register(b0) {float4 tx;};"
        "float4 vs(float2 p:POSITION):SV_Position{"
        "return float4(p*tx.zw+tx.xy,0,1);}"
        "float4 ps():SV_Target{return float4(0,1,0,1);}";
    ComPtr<ID3DBlob> vsCode,psCode;
    require(SUCCEEDED(D3DCompile(shader,sizeof(shader)-1,nullptr,nullptr,nullptr,
        "vs","vs_4_0",0,0,vsCode.GetAddressOf(),nullptr)), "VS compilation");
    require(SUCCEEDED(D3DCompile(shader,sizeof(shader)-1,nullptr,nullptr,nullptr,
        "ps","ps_4_0",0,0,psCode.GetAddressOf(),nullptr)), "PS compilation");
    ComPtr<ID3D11VertexShader> vs;
    ComPtr<ID3D11PixelShader> ps;
    require(SUCCEEDED(dev->CreateVertexShader(vsCode->GetBufferPointer(),
        vsCode->GetBufferSize(),nullptr,vs.GetAddressOf())), "VS object");
    require(SUCCEEDED(dev->CreatePixelShader(psCode->GetBufferPointer(),
        psCode->GetBufferSize(),nullptr,ps.GetAddressOf())), "PS object");
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
    ID3D11RenderTargetView* rawRtv=rtv.Get();
    ctx->OMSetRenderTargets(1,&rawRtv,nullptr);
    const D3D11_VIEWPORT viewport{0,0,40,40,0,1};
    ctx->RSSetViewports(1,&viewport);
    D3D11_RASTERIZER_DESC rasterDesc{};
    rasterDesc.FillMode=D3D11_FILL_SOLID;
    rasterDesc.CullMode=D3D11_CULL_NONE;
    rasterDesc.DepthClipEnable=TRUE;
    ComPtr<ID3D11RasterizerState> raster;
    require(SUCCEEDED(dev->CreateRasterizerState(&rasterDesc,
        raster.GetAddressOf())), "rasterizer");
    ctx->RSSetState(raster.Get());
    td.Usage=D3D11_USAGE_STAGING; td.BindFlags=0;
    td.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
    ComPtr<ID3D11Texture2D> staging;
    require(SUCCEEDED(dev->CreateTexture2D(&td,nullptr,staging.GetAddressOf())),
        "staging");

    NativeVsConstantSnapshotR191 snapshot, wrong;
    require(!snapshot.initialize(dev.Get(),{0,0,0,1},gen,1),
        "reject zero transform scale");
    require(snapshot.initialize(dev.Get(),{0,0,1,1},gen,73),
        "initial immutable VS transform");
    require(!snapshot.bind_vs_b0(ctx.Get(),gen,74),
        "reject wrong source snapshot version");
    require(snapshot.bind_vs_b0(ctx.Get(),gen,73), "bind VS b0");
    const auto ready=[&](std::uint64_t version) {
        return verified_indexed_vs_transform_draw_ready(
            vb,ib,snapshot,ctx.Get(),0,3,0,gen,vv,iv,version,40,40,
            DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get());
    };
    require(ready(73), "initial VS b0 exact draw readiness");
    require(!ready(74), "reject stale VS snapshot receipt");
    require(!ready(73+1000), "reject future VS snapshot receipt");
    require(wrong.initialize(dev.Get(),{0,0,1,1},gen,73),
        "same-size wrong-owner constant buffer");
    require(wrong.bind_vs_b0(ctx.Get(),gen,73), "bind wrong owner");
    require(!ready(73), "reject equal-bytes different VS buffer identity");
    require(snapshot.bind_vs_b0(ctx.Get(),gen,73), "restore owned VS b0");
    ID3D11Buffer* nullBuffer=nullptr;
    ctx->VSSetConstantBuffers(0,1,&nullBuffer);
    require(!ready(73), "reject unbound VS b0");
    require(snapshot.bind_vs_b0(ctx.Get(),gen,73), "restore VS b0 again");

    const float black[]={0,0,0,1};
    ctx->ClearRenderTargetView(rtv.Get(),black);
    require(ready(73), "preflight first actual GPU DrawIndexed");
    ctx->DrawIndexed(3,0,0);
    ctx->CopyResource(staging.Get(),color.Get());
    const auto pixel=[&](UINT x,UINT y,bool green) {
        D3D11_MAPPED_SUBRESOURCE map{};
        require(SUCCEEDED(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,&map)) &&
            map.pData,"map WARP GPU pixel");
        const auto* p=static_cast<const unsigned char*>(map.pData)+
            y*map.RowPitch+x*4;
        const bool match=green
            ? p[0]==0 && p[1]==255 && p[2]==0 && p[3]==255
            : p[0]==0 && p[1]==0 && p[2]==0 && p[3]==255;
        ctx->Unmap(staging.Get(),0);
        return match;
    };
    require(pixel(20,20,true) && pixel(1,1,false),
        "baseline VS transform produces centered green indexed pixels");

    // Recreate the immutable snapshot instead of pretending stale GPU bytes
    // changed when only a generation/version scalar advanced.
    require(snapshot.initialize(dev.Get(),{.65f,0.f,.4f,.4f},gen,74),
        "replacement immutable VS transform");
    require(!ready(74), "reject old bound GPU transform object");
    require(snapshot.bind_vs_b0(ctx.Get(),gen,74), "bind fresh b0");
    require(!ready(73) && ready(74), "reject retired version accept replacement");
    ctx->ClearRenderTargetView(rtv.Get(),black);
    require(ready(74), "preflight translated DrawIndexed");
    ctx->DrawIndexed(3,0,0);
    ctx->CopyResource(staging.Get(),color.Get());
    require(pixel(20,20,false) && pixel(33,20,true) && pixel(1,1,false),
        "actual VS b0 shifted DrawIndexed from center to right-side pixels");

    snapshot.shutdown();
    require(!ready(74),"reject retired VS constant owner");
    ib.shutdown();
    std::cout << "R191 owned immutable VS b0 index DrawIndexed WARP pixels: PASS\n";
}
