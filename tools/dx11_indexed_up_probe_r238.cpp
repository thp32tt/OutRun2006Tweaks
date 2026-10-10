// R238: D3D9 DrawIndexedPrimitiveUP immutable CPU spans to WARP GPU pixels.
// No native gameplay Draw activation; only the probe calls DrawIndexed.
#include "vr/d3d11/native_d3d9_indexed_up_batch.hpp"
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <d3dcompiler.h>
#include <wrl/client.h>

using Microsoft::WRL::ComPtr;
using outrun::vr::dx11::NativeD3D9IndexedUPBatch;

static void require(bool yes, const char* reason) {
    if (!yes) { std::cerr << "R238 WARP: " << reason << '\n'; std::exit(1); }
}
struct Vertex { float x, y; };
int main() {
    ComPtr<ID3D11Device> device;
    ComPtr<ID3D11DeviceContext> ctx;
    require(SUCCEEDED(D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_WARP,
        nullptr, 0, nullptr, 0, D3D11_SDK_VERSION,
        device.GetAddressOf(), nullptr, ctx.GetAddressOf())), "create WARP");
    const char shader[] =
        "float4 vs(float2 p:POSITION):SV_Position{return float4(p,0,1);}"
        "float4 ps():SV_Target{return float4(1,0,0,1);}";
    ComPtr<ID3DBlob> vCode,pCode;
    require(SUCCEEDED(D3DCompile(shader,sizeof(shader)-1,nullptr,nullptr,
        nullptr,"vs","vs_4_0",0,0,vCode.GetAddressOf(),nullptr)), "VS");
    require(SUCCEEDED(D3DCompile(shader,sizeof(shader)-1,nullptr,nullptr,
        nullptr,"ps","ps_4_0",0,0,pCode.GetAddressOf(),nullptr)), "PS");
    ComPtr<ID3D11VertexShader> vs;
    ComPtr<ID3D11PixelShader> ps;
    require(SUCCEEDED(device->CreateVertexShader(vCode->GetBufferPointer(),
        vCode->GetBufferSize(),nullptr,vs.GetAddressOf())), "VS object");
    require(SUCCEEDED(device->CreatePixelShader(pCode->GetBufferPointer(),
        pCode->GetBufferSize(),nullptr,ps.GetAddressOf())), "PS object");
    const D3D11_INPUT_ELEMENT_DESC elem = {
        "POSITION",0,DXGI_FORMAT_R32G32_FLOAT,0,0,D3D11_INPUT_PER_VERTEX_DATA,0};
    ComPtr<ID3D11InputLayout> layout;
    require(SUCCEEDED(device->CreateInputLayout(&elem,1,vCode->GetBufferPointer(),
        vCode->GetBufferSize(),layout.GetAddressOf())), "IA layout");
    D3D11_TEXTURE2D_DESC td{};
    td.Width=td.Height=32; td.MipLevels=td.ArraySize=1;
    td.Format=DXGI_FORMAT_R8G8B8A8_UNORM; td.SampleDesc.Count=1;
    td.Usage=D3D11_USAGE_DEFAULT; td.BindFlags=D3D11_BIND_RENDER_TARGET;
    ComPtr<ID3D11Texture2D> color, staging, secondColor;
    ComPtr<ID3D11RenderTargetView> rtv, secondRtv;
    require(SUCCEEDED(device->CreateTexture2D(&td,nullptr,color.GetAddressOf())),
        "color");
    require(SUCCEEDED(device->CreateRenderTargetView(
        color.Get(),nullptr,rtv.GetAddressOf())), "RTV");
    require(SUCCEEDED(device->CreateTexture2D(&td,nullptr,secondColor.GetAddressOf())),
        "foreign eye");
    require(SUCCEEDED(device->CreateRenderTargetView(
        secondColor.Get(),nullptr,secondRtv.GetAddressOf())), "foreign RTV");
    td.BindFlags=0; td.Usage=D3D11_USAGE_STAGING;
    td.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
    require(SUCCEEDED(device->CreateTexture2D(&td,nullptr,staging.GetAddressOf())),
        "readback");
    D3D11_RASTERIZER_DESC rd{};
    rd.FillMode=D3D11_FILL_SOLID; rd.CullMode=D3D11_CULL_NONE;
    rd.DepthClipEnable=TRUE;
    ComPtr<ID3D11RasterizerState> rs;
    require(SUCCEEDED(device->CreateRasterizerState(&rd,rs.GetAddressOf())),
        "raster state");
    const D3D11_VIEWPORT vp{0,0,32,32,0,1};
    ctx->RSSetState(rs.Get());
    ctx->RSSetViewports(1,&vp);
    ctx->IASetInputLayout(layout.Get());
    ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    ctx->VSSetShader(vs.Get(),nullptr,0);
    ctx->PSSetShader(ps.Get(),nullptr,0);
    ID3D11RenderTargetView* onlyRtv=rtv.Get();
    ctx->OMSetRenderTargets(1,&onlyRtv,nullptr);

    Vertex points[]={{-.8f,-.8f},{0.f,.8f},{.8f,-.8f}};
    std::uint16_t order[]={0,1,2};
    constexpr std::uint64_t generation=238, vbVer=54, ibVer=55;
    NativeD3D9IndexedUPBatch up;
    const auto capture=[&](const void* v,UINT vb,const void* i,UINT ib,
                           D3DPRIMITIVETYPE type,UINT min,UINT count,
                           UINT triangles,D3DFORMAT fmt,UINT stride) {
        return up.capture(device.Get(),v,vb,i,ib,type,min,count,triangles,fmt,
                          stride,generation,vbVer,ibVer);
    };
    require(!capture(nullptr,sizeof(points),order,sizeof(order),
                     D3DPT_TRIANGLELIST,0,3,1,D3DFMT_INDEX16,sizeof(Vertex)),
            "reject null UP vertices");
    require(!capture(points,sizeof(points),nullptr,sizeof(order),
                     D3DPT_TRIANGLELIST,0,3,1,D3DFMT_INDEX16,sizeof(Vertex)),
            "reject null UP indices");
    require(!capture(points,sizeof(points)-1,order,sizeof(order),
                     D3DPT_TRIANGLELIST,0,3,1,D3DFMT_INDEX16,sizeof(Vertex)),
            "reject short vertex span");
    require(!capture(points,sizeof(points),order,sizeof(order)-1,
                     D3DPT_TRIANGLELIST,0,3,1,D3DFMT_INDEX16,sizeof(Vertex)),
            "reject short index span");
    require(!capture(points,sizeof(points),order,sizeof(order),
                     D3DPT_TRIANGLESTRIP,0,3,1,D3DFMT_INDEX16,sizeof(Vertex)),
            "reject unsupported topology");
    require(!capture(points,sizeof(points),order,sizeof(order),
                     D3DPT_TRIANGLELIST,1,3,1,D3DFMT_INDEX16,sizeof(Vertex)),
            "reject unproven nonzero MinVertexIndex");
    require(!capture(points,sizeof(points),order,sizeof(order),
                     D3DPT_TRIANGLELIST,0,3,0,D3DFMT_INDEX16,sizeof(Vertex)),
            "reject empty primitives");
    require(!capture(points,sizeof(points),order,sizeof(order),
                     D3DPT_TRIANGLELIST,0,3,1,D3DFMT_INDEX16,0),
            "reject zero stride");
    require(!capture(points,sizeof(points),order,sizeof(order),
                     D3DPT_TRIANGLELIST,0,3,0xffffffffu,D3DFMT_INDEX16,
                     sizeof(Vertex)), "reject primitive arithmetic overflow");
    std::uint16_t invalid[]={0,1,9};
    require(!capture(points,sizeof(points),invalid,sizeof(invalid),
                     D3DPT_TRIANGLELIST,0,3,1,D3DFMT_INDEX16,sizeof(Vertex)),
            "reject out-of-range index");
    require(capture(points,sizeof(points),order,sizeof(order),
                    D3DPT_TRIANGLELIST,0,3,1,D3DFMT_INDEX16,sizeof(Vertex)),
            "copy immutable D3D9 indexed UP spans");
    // Transient D3D9 pointers can disappear after capture.
    for (auto& v:points) v={3.f,3.f};
    for (auto& i:order) i=9;
    const auto ready=[&](std::uint64_t g,std::uint64_t v,std::uint64_t i,
                         ID3D11PixelShader* expected) {
        return up.bind_and_verify(ctx.Get(),g,v,i,32,32,
            DXGI_FORMAT_R8G8B8A8_UNORM,layout.Get(),vs.Get(),expected,rtv.Get());
    };
    require(!ready(generation+1,vbVer,ibVer,ps.Get()), "reject stale generation");
    require(!ready(generation,vbVer+1,ibVer,ps.Get()), "reject stale VB");
    require(!ready(generation,vbVer,ibVer+1,ps.Get()), "reject stale IB");
    require(!ready(generation,vbVer,ibVer,nullptr), "reject missing PS");
    ID3D11RenderTargetView* twoEyes[]={rtv.Get(),secondRtv.Get()};
    ctx->OMSetRenderTargets(2,twoEyes,nullptr);
    require(!ready(generation,vbVer,ibVer,ps.Get()), "reject foreign second eye");
    ctx->OMSetRenderTargets(1,&onlyRtv,nullptr);
    require(ready(generation,vbVer,ibVer,ps.Get()), "owned IA and sole eye");
    const float black[]={0,0,0,1};
    ctx->ClearRenderTargetView(rtv.Get(),black);
    ctx->DrawIndexed(up.index_count(),0u,0); // R238 isolated WARP only.
    ctx->CopyResource(staging.Get(),color.Get());
    D3D11_MAPPED_SUBRESOURCE map{};
    require(SUCCEEDED(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,&map)) &&
            map.pData, "map WARP");
    const auto* bytes=static_cast<const std::uint8_t*>(map.pData);
    const auto* center=bytes+16*map.RowPitch+16*4;
    const auto* corner=bytes;
    const bool red=center[0]==255 && center[1]==0 &&
                   center[2]==0 && center[3]==255;
    const bool unpainted=corner[0]==0 && corner[1]==0 &&
                         corner[2]==0 && corner[3]==255;
    ctx->Unmap(staging.Get(),0);
    require(red && unpainted,
            "R238 D3D9 indexed UP -> owned VB/IB -> native WARP red pixel");
    up.reset();
    require(!ready(generation,vbVer,ibVer,ps.Get()), "reject retired UP batch");
    // INDEX32 follows the same byte-span and immutable D3D11 IB path.
    Vertex fresh[]={{-.8f,-.8f},{0.f,.8f},{.8f,-.8f}};
    std::uint32_t wide[]={0,1,2};
    require(up.capture(device.Get(),fresh,sizeof(fresh),wide,sizeof(wide),
        D3DPT_TRIANGLELIST,0,3,1,D3DFMT_INDEX32,sizeof(Vertex),
        generation,vbVer+2,ibVer+2), "capture INDEX32");
    require(up.bind_and_verify(ctx.Get(),generation,vbVer+2,ibVer+2,32,32,
        DXGI_FORMAT_R8G8B8A8_UNORM,layout.Get(),vs.Get(),ps.Get(),rtv.Get()),
        "INDEX32 owned IA and sole eye");
    ctx->ClearRenderTargetView(rtv.Get(),black);
    ctx->DrawIndexed(up.index_count(),0,0);
    ctx->CopyResource(staging.Get(),color.Get());
    require(SUCCEEDED(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,&map)) &&
            map.pData, "map INDEX32 WARP");
    bytes=static_cast<const std::uint8_t*>(map.pData);
    center=bytes+16*map.RowPitch+16*4;
    const bool wideRed=center[0]==255 && center[1]==0 &&
                       center[2]==0 && center[3]==255;
    ctx->Unmap(staging.Get(),0);
    require(wideRed, "INDEX32 indexed UP native GPU pixel");
    std::cout<<"R238 D3D9 indexed UP immutable VB/IB -> WARP pixels: PASS\n";
    return 0;
}
