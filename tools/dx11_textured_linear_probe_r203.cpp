// R203 isolated WARP textured native non-indexed Draw; game activation stays dormant.
#include "vr/d3d11/native_linear_texture_binding.hpp"
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <d3dcompiler.h>
#include <wrl/client.h>
using Microsoft::WRL::ComPtr;
using namespace outrun::vr::dx11;
static void require(bool valid, const char* reason) {
    if (!valid) { std::cerr << "R188 WARP failed: " << reason << '\n'; std::exit(1); }
}
int main() {
    ComPtr<ID3D11Device> dev;
    ComPtr<ID3D11DeviceContext> ctx;
    require(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,
        nullptr,0,nullptr,0,D3D11_SDK_VERSION,
        dev.GetAddressOf(),nullptr,ctx.GetAddressOf())), "create WARP");
    struct V {float x,y,u,v;};
    const V vertices[]={{-.8f,-.8f,.5f,.5f},{0.f,.8f,.5f,.5f},{.8f,-.8f,.5f,.5f}};
    constexpr std::uint64_t gen=203, vv=74;
    NativeLinearBufferMirror vb;
    require(vb.initialize(dev.Get(),ResourceRole::Vertex,D3DPOOL_DEFAULT,
        D3DUSAGE_WRITEONLY,D3DFMT_UNKNOWN,vertices,sizeof(vertices),
        sizeof(V),gen,vv), "init VB");
    require(vb.bind(ctx.Get(),gen,vv), "bind owned non-indexed VB");
    constexpr char hlsl[] =
        "struct O{float4 pos:SV_Position; float2 uv:TEXCOORD0;};"
        "O vs(float2 p:POSITION,float2 uv:TEXCOORD0){O o;o.pos=float4(p,0,1);o.uv=uv;return o;}"
        "Texture2D t0:register(t0);SamplerState s0:register(s0);"
        "float4 ps(O i):SV_Target{return t0.Sample(s0,i.uv);}";
    ComPtr<ID3DBlob> vcode,pcode;
    require(SUCCEEDED(D3DCompile(hlsl,sizeof(hlsl)-1,nullptr,nullptr,
        nullptr,"vs","vs_4_0",0,0,vcode.GetAddressOf(),nullptr)), "VS compile");
    require(SUCCEEDED(D3DCompile(hlsl,sizeof(hlsl)-1,nullptr,nullptr,
        nullptr,"ps","ps_4_0",0,0,pcode.GetAddressOf(),nullptr)), "PS compile");
    ComPtr<ID3D11VertexShader> vs;
    ComPtr<ID3D11PixelShader> ps;
    require(SUCCEEDED(dev->CreateVertexShader(vcode->GetBufferPointer(),
        vcode->GetBufferSize(),nullptr,vs.GetAddressOf())), "VS create");
    require(SUCCEEDED(dev->CreatePixelShader(pcode->GetBufferPointer(),
        pcode->GetBufferSize(),nullptr,ps.GetAddressOf())), "PS create");
    const D3D11_INPUT_ELEMENT_DESC elements[]={
        {"POSITION",0,DXGI_FORMAT_R32G32_FLOAT,0,0,D3D11_INPUT_PER_VERTEX_DATA,0},
        {"TEXCOORD",0,DXGI_FORMAT_R32G32_FLOAT,0,8,D3D11_INPUT_PER_VERTEX_DATA,0}};
    ComPtr<ID3D11InputLayout> layout;
    require(SUCCEEDED(dev->CreateInputLayout(elements,2,vcode->GetBufferPointer(),
        vcode->GetBufferSize(),layout.GetAddressOf())), "layout");
    ctx->IASetInputLayout(layout.Get());
    ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    ctx->VSSetShader(vs.Get(),nullptr,0); ctx->PSSetShader(ps.Get(),nullptr,0);

    D3D11_TEXTURE2D_DESC td{};
    td.Width=40;td.Height=40;td.MipLevels=1;td.ArraySize=1;
    td.Format=DXGI_FORMAT_R8G8B8A8_UNORM;td.SampleDesc.Count=1;
    td.Usage=D3D11_USAGE_DEFAULT;td.BindFlags=D3D11_BIND_RENDER_TARGET;
    ComPtr<ID3D11Texture2D> color;
    ComPtr<ID3D11RenderTargetView> rtv;
    require(SUCCEEDED(dev->CreateTexture2D(&td,nullptr,color.GetAddressOf())), "color");
    require(SUCCEEDED(dev->CreateRenderTargetView(color.Get(),nullptr,rtv.GetAddressOf())), "RTV");
    td.Usage=D3D11_USAGE_STAGING;td.BindFlags=0;td.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
    ComPtr<ID3D11Texture2D> staging;
    require(SUCCEEDED(dev->CreateTexture2D(&td,nullptr,staging.GetAddressOf())), "staging");
    ID3D11RenderTargetView* target=rtv.Get();
    ctx->OMSetRenderTargets(1,&target,nullptr);
    const D3D11_VIEWPORT vp{0,0,40,40,0,1};
    ctx->RSSetViewports(1,&vp);
    D3D11_RASTERIZER_DESC raster{};
    raster.FillMode=D3D11_FILL_SOLID;raster.CullMode=D3D11_CULL_NONE;
    raster.DepthClipEnable=TRUE;
    ComPtr<ID3D11RasterizerState> rs;
    require(SUCCEEDED(dev->CreateRasterizerState(&raster,rs.GetAddressOf())), "RS");
    ctx->RSSetState(rs.Get());

    td.Width=1;td.Height=1;td.Usage=D3D11_USAGE_IMMUTABLE;
    td.CPUAccessFlags=0;td.BindFlags=D3D11_BIND_SHADER_RESOURCE;
    const std::uint8_t red[]={255,0,0,255};
    const std::uint8_t blue[]={0,0,255,255};
    const D3D11_SUBRESOURCE_DATA redData{red,4,0}, blueData{blue,4,0};
    ComPtr<ID3D11Texture2D> source, other;
    require(SUCCEEDED(dev->CreateTexture2D(&td,&redData,source.GetAddressOf())), "source");
    require(SUCCEEDED(dev->CreateTexture2D(&td,&blueData,other.GetAddressOf())), "other");
    ComPtr<ID3D11ShaderResourceView> srv, otherSrv;
    require(SUCCEEDED(dev->CreateShaderResourceView(source.Get(),nullptr,srv.GetAddressOf())), "SRV");
    require(SUCCEEDED(dev->CreateShaderResourceView(other.Get(),nullptr,otherSrv.GetAddressOf())), "other SRV");
    D3D11_SAMPLER_DESC sd{};
    sd.Filter=D3D11_FILTER_MIN_MAG_MIP_POINT;
    sd.AddressU=sd.AddressV=sd.AddressW=D3D11_TEXTURE_ADDRESS_CLAMP;
    sd.MaxAnisotropy=1;sd.ComparisonFunc=D3D11_COMPARISON_ALWAYS;
    sd.MinLOD=0;sd.MaxLOD=D3D11_FLOAT32_MAX;
    ComPtr<ID3D11SamplerState> sampler, alternate;
    require(SUCCEEDED(dev->CreateSamplerState(&sd,sampler.GetAddressOf())), "sampler");
    sd.Filter=D3D11_FILTER_MIN_MAG_MIP_LINEAR;
    require(SUCCEEDED(dev->CreateSamplerState(&sd,alternate.GetAddressOf())), "alternate sampler");
    ID3D11ShaderResourceView* rawSrv=srv.Get();
    ID3D11SamplerState* rawSampler=sampler.Get();
    ctx->PSSetShaderResources(0,1,&rawSrv);
    ctx->PSSetSamplers(0,1,&rawSampler);
    const auto ready=[&](ID3D11ShaderResourceView* expected,
                         ID3D11SamplerState* expectedState,UINT slot=0,
                         DXGI_FORMAT fmt=DXGI_FORMAT_R8G8B8A8_UNORM){
        return verified_linear_textured_draw_ready(
            vb,ctx.Get(),0,3,gen,vv,40,40,
            DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get(),slot,expected,expectedState,fmt);
    };
    require(ready(srv.Get(),sampler.Get()), "baseline bound texture ownership");
    // R222: depth is intentionally unowned by this opt-in textured preflight.
    // A same-device DSV is still an inter-eye rejection, not a free pass.
    D3D11_TEXTURE2D_DESC depthDesc{};
    depthDesc.Width=40;depthDesc.Height=40;
    depthDesc.MipLevels=1;depthDesc.ArraySize=1;
    depthDesc.Format=DXGI_FORMAT_D32_FLOAT;
    depthDesc.SampleDesc.Count=1;
    depthDesc.Usage=D3D11_USAGE_DEFAULT;
    depthDesc.BindFlags=D3D11_BIND_DEPTH_STENCIL;
    ComPtr<ID3D11Texture2D> retainedDepth;
    ComPtr<ID3D11DepthStencilView> retainedDsv;
    require(SUCCEEDED(dev->CreateTexture2D(&depthDesc,nullptr,
        retainedDepth.GetAddressOf())) && retainedDepth, "create retained depth");
    require(SUCCEEDED(dev->CreateDepthStencilView(retainedDepth.Get(),
        nullptr,retainedDsv.GetAddressOf())) && retainedDsv,
        "create retained DSV");
    ctx->OMSetRenderTargets(1,&target,retainedDsv.Get());
    require(!ready(srv.Get(),sampler.Get()), "reject unowned retained depth view");
    ctx->OMSetRenderTargets(1,&target,nullptr);
    require(ready(srv.Get(),sampler.Get()), "restore depth-free textured eye");
    require(!ready(otherSrv.Get(),sampler.Get()), "reject wrong expected SRV");
    require(!ready(srv.Get(),alternate.Get()), "reject wrong expected sampler");
    require(!ready(srv.Get(),sampler.Get(),1), "reject wrong PS slot");
    require(!ready(srv.Get(),sampler.Get(),16), "reject sampler out-of-range");
    require(!ready(srv.Get(),sampler.Get(),0,DXGI_FORMAT_R8G8B8A8_UNORM_SRGB),
        "reject wrong source format");
    ID3D11ShaderResourceView* wrong=otherSrv.Get();
    ctx->PSSetShaderResources(0,1,&wrong);
    require(!ready(srv.Get(),sampler.Get()), "reject rebound SRV");
    ctx->PSSetShaderResources(0,1,&rawSrv);
    ID3D11SamplerState* alternatePtr=alternate.Get();
    ctx->PSSetSamplers(0,1,&alternatePtr);
    require(!ready(srv.Get(),sampler.Get()), "reject rebound sampler");
    ctx->PSSetSamplers(0,1,&rawSampler);
    require(ready(srv.Get(),sampler.Get()), "restored exact PS texture binding");
    // R203 retry: a stale second-eye RTV would silently receive the same
    // non-indexed Draw even though slot 0 retains the correct expected target.
    D3D11_TEXTURE2D_DESC strayDesc{};
    strayDesc.Width=40;strayDesc.Height=40;strayDesc.MipLevels=1;
    strayDesc.ArraySize=1;strayDesc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;
    strayDesc.SampleDesc.Count=1;strayDesc.BindFlags=D3D11_BIND_RENDER_TARGET;
    ComPtr<ID3D11Texture2D> staleEye;
    ComPtr<ID3D11RenderTargetView> staleEyeRtv;
    require(SUCCEEDED(dev->CreateTexture2D(&strayDesc,nullptr,staleEye.GetAddressOf())),
        "create stale eye target");
    require(SUCCEEDED(dev->CreateRenderTargetView(staleEye.Get(),nullptr,
        staleEyeRtv.GetAddressOf())), "create stale eye RTV");
    ID3D11RenderTargetView* twoEyes[]={rtv.Get(),staleEyeRtv.Get()};
    ctx->OMSetRenderTargets(2,twoEyes,nullptr);
    require(!ready(srv.Get(),sampler.Get()), "reject stray second-eye RTV slot 1");
    ctx->OMSetRenderTargets(1,&target,nullptr);
    require(ready(srv.Get(),sampler.Get()), "restore sole eye render target");
    const float clear[]={0,0,0,1};
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    require(ready(srv.Get(),sampler.Get()), "owned red SRV immediately before Draw");
    ctx->Draw(3,0); // Isolated WARP proof, NEVER game draw activation.
    ctx->CopyResource(staging.Get(),color.Get());
    D3D11_MAPPED_SUBRESOURCE map{};
    require(SUCCEEDED(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,&map)) &&
        map.pData, "map GPU readback");
    const auto* pixels=static_cast<const std::uint8_t*>(map.pData);
    const auto* center=pixels+20*map.RowPitch+20*4;
    const auto* corner=pixels+1*map.RowPitch+1*4;
    const bool valid=center[0]==255 && center[1]==0 && center[2]==0 &&
        center[3]==255 && corner[0]==0 && corner[1]==0 &&
        corner[2]==0 && corner[3]==255;
    ctx->Unmap(staging.Get(),0);
    require(valid, "actual non-indexed Draw sampled red center / black corner pixels");
    // A foreign live PS SRV changes genuine GPU pixels, not merely a hash.
    wrong=otherSrv.Get();
    ctx->PSSetShaderResources(0,1,&wrong);
    require(!ready(srv.Get(),sampler.Get()),
        "reject rebound blue SRV before GPU Draw");
    require(ready(otherSrv.Get(),sampler.Get()),
        "explicit blue SRV owner accepted only when requested");
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    ctx->Draw(3,0);
    ctx->CopyResource(staging.Get(),color.Get());
    require(SUCCEEDED(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,&map)) &&
        map.pData, "map blue WARP readback");
    pixels=static_cast<const std::uint8_t*>(map.pData);
    center=pixels+20*map.RowPitch+20*4;
    const bool gotBlue=center[0]==0 && center[1]==0 &&
        center[2]==255 && center[3]==255;
    ctx->Unmap(staging.Get(),0);
    require(gotBlue, "actual rebound blue texture changes Draw center pixel");

    ctx->PSSetShaderResources(0,1,&rawSrv);
    require(ready(srv.Get(),sampler.Get()), "restored exact red texture binding");
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    ctx->Draw(3,0);
    ctx->CopyResource(staging.Get(),color.Get());
    require(SUCCEEDED(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,&map)) &&
        map.pData, "map restored red WARP readback");
    pixels=static_cast<const std::uint8_t*>(map.pData);
    center=pixels+20*map.RowPitch+20*4;
    const bool restoredRed=center[0]==255 && center[1]==0 &&
        center[2]==0 && center[3]==255;
    ctx->Unmap(staging.Get(),0);
    require(restoredRed, "actual restored red SRV recovers Draw pixel");
    vb.shutdown();
    require(!ready(srv.Get(),sampler.Get()), "reject retired VB after texture binding");
    std::cout << "R203 exact PS SRV/sampler non-indexed WARP red/blue/red GPU pixels PASS\\n";
}
