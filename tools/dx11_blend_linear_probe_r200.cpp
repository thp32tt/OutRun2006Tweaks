// R200: actual non-indexed WARP Draw alpha state: purple/opaque-red/recovery.
#include "vr/d3d11/native_linear_blend_binding.hpp"
#include <array>
#include <cstdlib>
#include <iostream>
#include <cstdint>
#include <d3dcompiler.h>
#include <wrl/client.h>
using Microsoft::WRL::ComPtr;
using namespace outrun::vr::dx11;
static void require(bool ok, const char* why) {
    if (!ok) { std::cerr << "R200 WARP failure: " << why << '\n'; std::exit(1); }
}
int main() {
    ComPtr<ID3D11Device> dev;
    ComPtr<ID3D11DeviceContext> ctx;
    require(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,
        nullptr,0,D3D11_SDK_VERSION,dev.GetAddressOf(),nullptr,
        ctx.GetAddressOf())), "WARP device");
    struct V {float x,y;};
    constexpr V verts[]={{-.8f,-.8f},{0.f,.8f},{.8f,-.8f}};
    NativeLinearBufferMirror vb;
    constexpr std::uint64_t gen=200,ver=71;
    require(vb.initialize(dev.Get(),ResourceRole::Vertex,D3DPOOL_DEFAULT,
        D3DUSAGE_WRITEONLY,D3DFMT_UNKNOWN,verts,sizeof(verts),
        sizeof(V),gen,ver), "live VB object upload");
    require(vb.bind(ctx.Get(),gen,ver),"bind native VB");
    constexpr char hlsl[]=
        "float4 vs(float2 p:POSITION):SV_Position{return float4(p,0,1);}"
        "float4 ps():SV_Target{return float4(1,0,0,0.5);}";
    ComPtr<ID3DBlob> vsCode,psCode;
    require(SUCCEEDED(D3DCompile(hlsl,sizeof(hlsl)-1,nullptr,nullptr,nullptr,
        "vs","vs_4_0",0,0,vsCode.GetAddressOf(),nullptr)),"VS compile");
    require(SUCCEEDED(D3DCompile(hlsl,sizeof(hlsl)-1,nullptr,nullptr,nullptr,
        "ps","ps_4_0",0,0,psCode.GetAddressOf(),nullptr)),"PS compile");
    ComPtr<ID3D11VertexShader> vs;
    ComPtr<ID3D11PixelShader> ps;
    require(SUCCEEDED(dev->CreateVertexShader(vsCode->GetBufferPointer(),
        vsCode->GetBufferSize(),nullptr,vs.GetAddressOf())),"VS object");
    require(SUCCEEDED(dev->CreatePixelShader(psCode->GetBufferPointer(),
        psCode->GetBufferSize(),nullptr,ps.GetAddressOf())),"PS object");
    constexpr D3D11_INPUT_ELEMENT_DESC elem={"POSITION",0,
        DXGI_FORMAT_R32G32_FLOAT,0,0,D3D11_INPUT_PER_VERTEX_DATA,0};
    ComPtr<ID3D11InputLayout> layout;
    require(SUCCEEDED(dev->CreateInputLayout(&elem,1,vsCode->GetBufferPointer(),
        vsCode->GetBufferSize(),layout.GetAddressOf())),"input layout");
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
        "color RTV texture");
    require(SUCCEEDED(dev->CreateRenderTargetView(color.Get(),nullptr,
        rtv.GetAddressOf())),"RTV view");
    ID3D11RenderTargetView* raw=rtv.Get();
    ctx->OMSetRenderTargets(1,&raw,nullptr);
    const D3D11_VIEWPORT viewport{0,0,40,40,0,1};
    ctx->RSSetViewports(1,&viewport);
    D3D11_RASTERIZER_DESC rasterDesc{};
    rasterDesc.FillMode=D3D11_FILL_SOLID;
    rasterDesc.CullMode=D3D11_CULL_NONE;
    rasterDesc.DepthClipEnable=TRUE;
    ComPtr<ID3D11RasterizerState> raster;
    require(SUCCEEDED(dev->CreateRasterizerState(
        &rasterDesc,raster.GetAddressOf())),"raster");
    ctx->RSSetState(raster.Get());

    D3D11_BLEND_DESC desc{};
    auto& rt=desc.RenderTarget[0];
    rt.BlendEnable=TRUE;
    rt.SrcBlend=D3D11_BLEND_SRC_ALPHA;
    rt.DestBlend=D3D11_BLEND_INV_SRC_ALPHA;
    rt.BlendOp=D3D11_BLEND_OP_ADD;
    rt.SrcBlendAlpha=D3D11_BLEND_ONE;
    rt.DestBlendAlpha=D3D11_BLEND_ZERO;
    rt.BlendOpAlpha=D3D11_BLEND_OP_ADD;
    rt.RenderTargetWriteMask=D3D11_COLOR_WRITE_ENABLE_ALL;
    ComPtr<ID3D11BlendState> alpha,opaque,zeroWrite;
    require(SUCCEEDED(dev->CreateBlendState(&desc,alpha.GetAddressOf())),
        "owned alpha state");
    rt.BlendEnable=FALSE;
    require(SUCCEEDED(dev->CreateBlendState(&desc,opaque.GetAddressOf())),
        "opaque state");
    rt.BlendEnable=TRUE;rt.RenderTargetWriteMask=0;
    require(SUCCEEDED(dev->CreateBlendState(&desc,zeroWrite.GetAddressOf())),
        "zero color state");
    constexpr FLOAT ones[4]={1,1,1,1};
    constexpr FLOAT stale[4]={0,1,1,1};
    ctx->OMSetBlendState(alpha.Get(),ones,D3D11_DEFAULT_SAMPLE_MASK);
    const auto ready=[&]() {
        return verified_linear_blend_draw_ready(vb,ctx.Get(),0,3,gen,ver,
            40,40,DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get(),alpha.Get());
    };
    require(ready(),"owned non-indexed live alpha blend baseline");
    require(!verified_linear_blend_draw_ready(vb,ctx.Get(),0,3,gen,ver,
        40,40,DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get(),nullptr),
        "reject missing expected alpha state");
    ctx->OMSetBlendState(opaque.Get(),ones,D3D11_DEFAULT_SAMPLE_MASK);
    require(!ready(),"reject rebound opaque state");
    ctx->OMSetBlendState(zeroWrite.Get(),ones,D3D11_DEFAULT_SAMPLE_MASK);
    require(!verified_linear_blend_draw_ready(vb,ctx.Get(),0,3,gen,ver,
        40,40,DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get(),zeroWrite.Get()),
        "reject disabled write mask");
    ctx->OMSetBlendState(alpha.Get(),stale,D3D11_DEFAULT_SAMPLE_MASK);
    require(!ready(),"reject stale blend factors");
    ctx->OMSetBlendState(alpha.Get(),ones,0u);
    require(!ready(),"reject zero sample mask");
    ctx->OMSetBlendState(alpha.Get(),ones,D3D11_DEFAULT_SAMPLE_MASK);
    require(ready(),"restore correct live alpha state");

    td.Usage=D3D11_USAGE_STAGING;
    td.BindFlags=0;td.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
    ComPtr<ID3D11Texture2D> stage;
    require(SUCCEEDED(dev->CreateTexture2D(&td,nullptr,stage.GetAddressOf())),
        "GPU readback staging");
    constexpr FLOAT blue[]={0,0,1,1};
    const auto centerPixel=[&]() {
        ctx->CopyResource(stage.Get(),color.Get());
        D3D11_MAPPED_SUBRESOURCE map{};
        require(SUCCEEDED(ctx->Map(stage.Get(),0,D3D11_MAP_READ,0,&map)) &&
            map.pData,"WARP Map");
        const auto* pixel=static_cast<const unsigned char*>(map.pData)
            +20*map.RowPitch+20*4;
        const std::array<unsigned char,4> rgba{
            pixel[0],pixel[1],pixel[2],pixel[3]};
        ctx->Unmap(stage.Get(),0);
        return rgba;
    };
    require(ready(),"alpha preflight immediately before GPU Draw");
    ctx->ClearRenderTargetView(rtv.Get(),blue);
    ctx->Draw(3,0);
    const auto purple=centerPixel();
    require(purple[0]>=127 && purple[0]<=129 && purple[1]==0 &&
        purple[2]>=126 && purple[2]<=129 &&
        purple[3]>=127 && purple[3]<=129,
        "actual alpha blended Draw purple center");
    // A live unexpected OM state silently alters the same real Draw pixels.
    ctx->OMSetBlendState(opaque.Get(),ones,D3D11_DEFAULT_SAMPLE_MASK);
    require(!ready(),"reject unexpected opaque blend before raw GPU Draw");
    ctx->ClearRenderTargetView(rtv.Get(),blue);
    ctx->Draw(3,0);
    const auto red=centerPixel();
    require(red[0]==255 && red[1]==0 && red[2]==0 &&
        red[3]>=127 && red[3]<=129,
        "actual wrong live blend changes purple to red");
    ctx->OMSetBlendState(alpha.Get(),ones,D3D11_DEFAULT_SAMPLE_MASK);
    require(ready(),"recover exact OM alpha state");
    ctx->ClearRenderTargetView(rtv.Get(),blue);
    ctx->Draw(3,0);
    const auto restored=centerPixel();
    require(restored[0]>=127 && restored[0]<=129 &&
        restored[1]==0 && restored[2]>=126 && restored[2]<=129,
        "actual restored blend recovers purple");
    vb.shutdown();
    require(!ready(),"reject retired linear VB owner");
    std::cout<<"R200 live linear OM alpha blended WARP Draw: PASS\n";
}
