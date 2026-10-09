// R188 isolated WARP textured native DrawIndexed; game activation stays dormant.
#include "vr/d3d11/native_indexed_texture_binding.hpp"
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
    const std::uint16_t indices[]={0,1,2};
    constexpr std::uint64_t gen=188, vv=41, iv=42;
    NativeLinearBufferMirror vb,ib;
    require(vb.initialize(dev.Get(),ResourceRole::Vertex,D3DPOOL_DEFAULT,
        D3DUSAGE_WRITEONLY,D3DFMT_UNKNOWN,vertices,sizeof(vertices),
        sizeof(V),gen,vv), "init VB");
    require(ib.initialize(dev.Get(),ResourceRole::Index,D3DPOOL_DEFAULT,
        D3DUSAGE_WRITEONLY,D3DFMT_INDEX16,indices,sizeof(indices),
        0,gen,iv), "init IB");
    require(vb.bind(ctx.Get(),gen,vv) && ib.bind(ctx.Get(),gen,iv), "bind VB/IB");
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
        return verified_indexed_textured_draw_ready(
            vb,ib,ctx.Get(),0,3,0,gen,vv,iv,40,40,
            DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get(),slot,expected,expectedState,fmt);
    };
    require(ready(srv.Get(),sampler.Get()), "baseline bound texture ownership");
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
    const float clear[]={0,0,0,1};
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    ctx->DrawIndexed(3,0,0); // Isolated WARP proof, NEVER game draw activation.
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
    require(valid, "actual DrawIndexed sampled red center / black corner pixels");
    ib.shutdown();
    require(!ready(srv.Get(),sampler.Get()), "reject retired IB after texture binding");
    std::cout << "R188 exact PS texture/sampler DrawIndexed WARP GPU pixels PASS\n";
}
