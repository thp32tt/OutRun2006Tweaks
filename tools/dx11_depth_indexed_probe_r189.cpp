// R189 isolated WARP indexed depth DrawIndexed: real depth-test pixel proof.
#include "vr/d3d11/native_indexed_depth_binding.hpp"
#include <cstdlib>
#include <iostream>
#include <cstdint>
#include <d3dcompiler.h>
#include <wrl/client.h>
using Microsoft::WRL::ComPtr;
using namespace outrun::vr::dx11;
static void require(bool b, const char* reason) {
    if (!b) { std::cerr << "R189 WARP failed: " << reason << '\n'; std::exit(1); }
}
int main() {
    ComPtr<ID3D11Device> dev;
    ComPtr<ID3D11DeviceContext> ctx;
    require(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,
        nullptr,0,nullptr,0,D3D11_SDK_VERSION,
        dev.GetAddressOf(),nullptr,ctx.GetAddressOf())), "create WARP");
    struct V {float x,y,z;};
    const V vertices[]={
        {-.8f,-.8f,.2f},{0.f,.8f,.2f},{.8f,-.8f,.2f},
        {-.8f,-.8f,.8f},{0.f,.8f,.8f},{.8f,-.8f,.8f}};
    const std::uint16_t indices[]={0,1,2,3,4,5};
    NativeLinearBufferMirror vb,ib;
    constexpr std::uint64_t gen=189, vv=51, iv=52;
    require(vb.initialize(dev.Get(),ResourceRole::Vertex,D3DPOOL_DEFAULT,
        D3DUSAGE_WRITEONLY,D3DFMT_UNKNOWN,vertices,sizeof(vertices),
        sizeof(V),gen,vv), "init VB");
    require(ib.initialize(dev.Get(),ResourceRole::Index,D3DPOOL_DEFAULT,
        D3DUSAGE_WRITEONLY,D3DFMT_INDEX16,indices,sizeof(indices),
        0,gen,iv), "init IB");
    require(vb.bind(ctx.Get(),gen,vv) && ib.bind(ctx.Get(),gen,iv), "bind VB/IB");
    constexpr char shader[] =
        "float4 vs(float3 p:POSITION):SV_Position{return float4(p,1);}"
        "float4 ps():SV_Target{return float4(0,1,0,1);}";
    ComPtr<ID3DBlob> vcode,pcode,redCode;
    require(SUCCEEDED(D3DCompile(shader,sizeof(shader)-1,nullptr,nullptr,
        nullptr,"vs","vs_4_0",0,0,vcode.GetAddressOf(),nullptr)), "VS compile");
    require(SUCCEEDED(D3DCompile(shader,sizeof(shader)-1,nullptr,nullptr,
        nullptr,"ps","ps_4_0",0,0,pcode.GetAddressOf(),nullptr)), "PS compile");
    constexpr char redShader[] = "float4 ps():SV_Target{return float4(1,0,0,1);}";
    require(SUCCEEDED(D3DCompile(redShader,sizeof(redShader)-1,nullptr,nullptr,
        nullptr,"ps","ps_4_0",0,0,redCode.GetAddressOf(),nullptr)), "red PS compile");
    ComPtr<ID3D11VertexShader> vs;
    ComPtr<ID3D11PixelShader> ps, redPs;
    require(SUCCEEDED(dev->CreateVertexShader(vcode->GetBufferPointer(),
        vcode->GetBufferSize(),nullptr,vs.GetAddressOf())), "VS create");
    require(SUCCEEDED(dev->CreatePixelShader(pcode->GetBufferPointer(),
        pcode->GetBufferSize(),nullptr,ps.GetAddressOf())), "PS create");
    require(SUCCEEDED(dev->CreatePixelShader(redCode->GetBufferPointer(),
        redCode->GetBufferSize(),nullptr,redPs.GetAddressOf())), "red PS create");
    const D3D11_INPUT_ELEMENT_DESC e={
        "POSITION",0,DXGI_FORMAT_R32G32B32_FLOAT,0,0,D3D11_INPUT_PER_VERTEX_DATA,0};
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
    // Create a separate real D24S8 depth surface and same-sized wrong-eye DSV.
    D3D11_TEXTURE2D_DESC depthDesc=td;
    depthDesc.Format=DXGI_FORMAT_D24_UNORM_S8_UINT;
    depthDesc.BindFlags=D3D11_BIND_DEPTH_STENCIL;
    ComPtr<ID3D11Texture2D> depth, otherDepth;
    ComPtr<ID3D11DepthStencilView> dsv, otherDsv;
    require(SUCCEEDED(dev->CreateTexture2D(&depthDesc,nullptr,depth.GetAddressOf())),
        "create depth");
    require(SUCCEEDED(dev->CreateDepthStencilView(depth.Get(),nullptr,
        dsv.GetAddressOf())), "create DSV");
    require(SUCCEEDED(dev->CreateTexture2D(&depthDesc,nullptr,
        otherDepth.GetAddressOf())), "create same-size other depth");
    require(SUCCEEDED(dev->CreateDepthStencilView(otherDepth.Get(),nullptr,
        otherDsv.GetAddressOf())), "create same-size other DSV");
    D3D11_DEPTH_STENCIL_DESC dsDesc{};
    dsDesc.DepthEnable=TRUE; dsDesc.DepthWriteMask=D3D11_DEPTH_WRITE_MASK_ALL;
    dsDesc.DepthFunc=D3D11_COMPARISON_LESS;
    ComPtr<ID3D11DepthStencilState> depthState, disabledDepth, reversedDepth, stencilDepth;
    require(SUCCEEDED(dev->CreateDepthStencilState(&dsDesc,
        depthState.GetAddressOf())), "depth state");
    dsDesc.DepthEnable=FALSE;
    require(SUCCEEDED(dev->CreateDepthStencilState(&dsDesc,
        disabledDepth.GetAddressOf())), "disabled depth state");
    dsDesc.DepthEnable=TRUE; dsDesc.DepthFunc=D3D11_COMPARISON_GREATER;
    require(SUCCEEDED(dev->CreateDepthStencilState(&dsDesc,
        reversedDepth.GetAddressOf())), "reversed depth state");
    dsDesc.DepthFunc=D3D11_COMPARISON_LESS; dsDesc.StencilEnable=TRUE;
    // Valid explicit stencil operations: zero is not a D3D11_STENCIL_OP.
    // The previous negative fixture itself failed CreateDepthStencilState.
    D3D11_DEPTH_STENCILOP_DESC keepAlways{};
    keepAlways.StencilFailOp=D3D11_STENCIL_OP_KEEP;
    keepAlways.StencilDepthFailOp=D3D11_STENCIL_OP_KEEP;
    keepAlways.StencilPassOp=D3D11_STENCIL_OP_KEEP;
    keepAlways.StencilFunc=D3D11_COMPARISON_ALWAYS;
    dsDesc.FrontFace=keepAlways; dsDesc.BackFace=keepAlways;
    require(SUCCEEDED(dev->CreateDepthStencilState(&dsDesc,
        stencilDepth.GetAddressOf())), "stencil state");
    ctx->OMSetRenderTargets(1,&raw,dsv.Get());
    ctx->OMSetDepthStencilState(depthState.Get(),0);
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
    const auto ready=[&](UINT start=0) {
        return verified_indexed_depth_draw_ready(vb,ib,ctx.Get(),
            start,3,0,gen,vv,iv,40,40,DXGI_FORMAT_R8G8B8A8_UNORM,
            rtv.Get(),dsv.Get(),depthState.Get());
    };
    require(ready(), "baseline exact DSV/depth state");
    // R213 same-device shader drift: R189 passes, joined exact guard must fail.
    const auto exactReady=[&](ID3D11PixelShader* expectedPs, UINT start=0) {
        return verified_indexed_exact_depth_pipeline_ready(
            vb,ib,ctx.Get(),start,3,0,gen,vv,iv,40,40,
            DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get(),dsv.Get(),depthState.Get(),
            layout.Get(),vs.Get(),expectedPs);
    };
    require(exactReady(ps.Get()), "R213 baseline exact indexed pipeline");
    // An otherwise exact indexed eye cannot render opaque proof pixels with
    // foreign OM blending or masked-out writes. R189 lacks this OM ownership.
    D3D11_BLEND_DESC blendDesc{};
    auto& rtBlend=blendDesc.RenderTarget[0];
    rtBlend.BlendEnable=TRUE;
    rtBlend.SrcBlend=D3D11_BLEND_ZERO;
    rtBlend.DestBlend=D3D11_BLEND_ONE;
    rtBlend.BlendOp=D3D11_BLEND_OP_ADD;
    rtBlend.SrcBlendAlpha=D3D11_BLEND_ZERO;
    rtBlend.DestBlendAlpha=D3D11_BLEND_ONE;
    rtBlend.BlendOpAlpha=D3D11_BLEND_OP_ADD;
    rtBlend.RenderTargetWriteMask=D3D11_COLOR_WRITE_ENABLE_ALL;
    ComPtr<ID3D11BlendState> foreignBlend;
    require(SUCCEEDED(dev->CreateBlendState(&blendDesc,
        foreignBlend.GetAddressOf())), "R213 foreign blend create");
    ctx->OMSetBlendState(foreignBlend.Get(),nullptr,D3D11_DEFAULT_SAMPLE_MASK);
    require(ready(), "R213 legacy depth guard ignores foreign blend");
    require(!exactReady(ps.Get()), "R213 rejects foreign OM blend");
    ctx->OMSetBlendState(nullptr,nullptr,0);
    require(!exactReady(ps.Get()), "R213 rejects zero sample mask");
    ctx->OMSetBlendState(nullptr,nullptr,D3D11_DEFAULT_SAMPLE_MASK);
    require(exactReady(ps.Get()), "R213 restores opaque blend sample mask");
    ctx->PSSetShader(redPs.Get(),nullptr,0);
    require(ready(), "R213 R189 accepts a foreign same-device PS");
    require(!exactReady(ps.Get()), "R213 rejects same-device PS drift");
    require(exactReady(redPs.Get()), "R213 exact alternate expected PS");
    ctx->PSSetShader(ps.Get(),nullptr,0);
    require(exactReady(ps.Get()), "R213 restores exact PS");

    require(!verified_indexed_depth_draw_ready(vb,ib,ctx.Get(),0,3,0,
        gen,vv,iv,40,40,DXGI_FORMAT_R8G8B8A8_UNORM,
        rtv.Get(),nullptr,depthState.Get()), "reject null expected DSV");
    ctx->OMSetRenderTargets(1,&raw,otherDsv.Get());
    require(!ready(), "reject same-sized wrong-eye DSV");
    require(!exactReady(ps.Get()), "R213 rejects wrong-eye DSV");
    ctx->OMSetRenderTargets(1,&raw,dsv.Get());
    ctx->OMSetDepthStencilState(disabledDepth.Get(),0);
    require(!ready(), "reject rebound depth state");
    require(!exactReady(ps.Get()), "R213 rejects rebound depth state");
    ctx->OMSetDepthStencilState(depthState.Get(),1);
    require(!ready(), "reject stencil reference drift");
    ctx->OMSetDepthStencilState(reversedDepth.Get(),0);
    require(!verified_indexed_depth_draw_ready(vb,ib,ctx.Get(),0,3,0,
        gen,vv,iv,40,40,DXGI_FORMAT_R8G8B8A8_UNORM,
        rtv.Get(),dsv.Get(),reversedDepth.Get()), "reject reversed depth compare");
    ctx->OMSetDepthStencilState(stencilDepth.Get(),0);
    require(!verified_indexed_depth_draw_ready(vb,ib,ctx.Get(),0,3,0,
        gen,vv,iv,40,40,DXGI_FORMAT_R8G8B8A8_UNORM,
        rtv.Get(),dsv.Get(),stencilDepth.Get()), "reject stencil-enabled depth");
    ctx->OMSetDepthStencilState(depthState.Get(),0);
    require(ready() && ready(3) && exactReady(ps.Get()) && exactReady(ps.Get(),3),
        "R213 restored combined depth/pipeline binding");
    const float black[]={0,0,0,1};
    ctx->ClearRenderTargetView(rtv.Get(),black);
    ctx->ClearDepthStencilView(dsv.Get(),D3D11_CLEAR_DEPTH|D3D11_CLEAR_STENCIL,1.f,0);
    // Near green writes .2 depth; far red at .8 must NOT overdraw it.
    require(exactReady(ps.Get(),0), "R213 exact preflight near draw");
    ctx->PSSetShader(ps.Get(),nullptr,0);
    ctx->DrawIndexed(3,0,0);
    ctx->PSSetShader(redPs.Get(),nullptr,0);
    require(exactReady(redPs.Get(),3), "R213 exact preflight far draw");
    ctx->DrawIndexed(3,3,0);
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
    require(pixels, "actual depth-tested DrawIndexed green center / black corner pixels");
    ib.shutdown();
    require(!ready() && !exactReady(redPs.Get()), "R213 rejects retired IB");
    std::cout << "R189 exact DSV depth-tested indexed WARP pixels: PASS\n";
}
