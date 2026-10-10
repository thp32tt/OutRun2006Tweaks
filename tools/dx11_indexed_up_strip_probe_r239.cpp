// R239: D3D9 indexed-UP strip, winding expansion, owned IA -> real WARP pixels.
// Only this standalone diagnostic issues a D3D11 DrawIndexed.
#include "vr/d3d11/native_d3d9_indexed_up_strip_batch.hpp"
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <d3dcompiler.h>
#include <wrl/client.h>

using Microsoft::WRL::ComPtr;
using outrun::vr::dx11::NativeD3D9IndexedUPStripBatch;
static void require(bool pass, const char* message) {
    if (!pass) { std::cerr << "R239 WARP: " << message << '\n'; std::exit(1); }
}
struct Vertex { float x, y; };
int main() {
    ComPtr<ID3D11Device> device;
    ComPtr<ID3D11DeviceContext> context;
    require(SUCCEEDED(D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_WARP,
        nullptr, 0, nullptr, 0, D3D11_SDK_VERSION,
        device.GetAddressOf(), nullptr, context.GetAddressOf())), "WARP device");
    const char shader[] =
        "float4 vs(float2 p:POSITION):SV_Position{return float4(p,0,1);}"
        "float4 ps():SV_Target{return float4(1,0,0,1);}";
    ComPtr<ID3DBlob> vsBytes, psBytes;
    require(SUCCEEDED(D3DCompile(shader,sizeof(shader)-1,nullptr,nullptr,
        nullptr,"vs","vs_4_0",0,0,vsBytes.GetAddressOf(),nullptr)), "VS compile");
    require(SUCCEEDED(D3DCompile(shader,sizeof(shader)-1,nullptr,nullptr,
        nullptr,"ps","ps_4_0",0,0,psBytes.GetAddressOf(),nullptr)), "PS compile");
    ComPtr<ID3D11VertexShader> vs;
    ComPtr<ID3D11PixelShader> ps;
    require(SUCCEEDED(device->CreateVertexShader(vsBytes->GetBufferPointer(),
        vsBytes->GetBufferSize(),nullptr,vs.GetAddressOf())), "VS create");
    require(SUCCEEDED(device->CreatePixelShader(psBytes->GetBufferPointer(),
        psBytes->GetBufferSize(),nullptr,ps.GetAddressOf())), "PS create");
    const D3D11_INPUT_ELEMENT_DESC element = {
        "POSITION",0,DXGI_FORMAT_R32G32_FLOAT,0,0,D3D11_INPUT_PER_VERTEX_DATA,0};
    ComPtr<ID3D11InputLayout> layout;
    require(SUCCEEDED(device->CreateInputLayout(&element,1,vsBytes->GetBufferPointer(),
        vsBytes->GetBufferSize(),layout.GetAddressOf())), "input layout");
    D3D11_TEXTURE2D_DESC texture{};
    texture.Width=texture.Height=32; texture.MipLevels=texture.ArraySize=1;
    texture.Format=DXGI_FORMAT_R8G8B8A8_UNORM; texture.SampleDesc.Count=1;
    texture.Usage=D3D11_USAGE_DEFAULT; texture.BindFlags=D3D11_BIND_RENDER_TARGET;
    ComPtr<ID3D11Texture2D> color, readback;
    ComPtr<ID3D11RenderTargetView> rtv;
    require(SUCCEEDED(device->CreateTexture2D(&texture,nullptr,color.GetAddressOf())),
            "RT");
    require(SUCCEEDED(device->CreateRenderTargetView(
        color.Get(),nullptr,rtv.GetAddressOf())), "RTV");
    texture.Usage=D3D11_USAGE_STAGING; texture.BindFlags=0;
    texture.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
    require(SUCCEEDED(device->CreateTexture2D(&texture,nullptr,readback.GetAddressOf())),
            "readback");
    D3D11_RASTERIZER_DESC rsDesc{};
    rsDesc.FillMode=D3D11_FILL_SOLID; rsDesc.CullMode=D3D11_CULL_NONE;
    rsDesc.DepthClipEnable=TRUE;
    ComPtr<ID3D11RasterizerState> rs;
    require(SUCCEEDED(device->CreateRasterizerState(&rsDesc,rs.GetAddressOf())),
            "raster");
    const D3D11_VIEWPORT viewport{0,0,32,32,0,1};
    context->RSSetState(rs.Get());
    context->RSSetViewports(1,&viewport);
    context->IASetInputLayout(layout.Get());
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context->VSSetShader(vs.Get(),nullptr,0);
    context->PSSetShader(ps.Get(),nullptr,0);
    ID3D11RenderTargetView* target = rtv.Get();
    context->OMSetRenderTargets(1,&target,nullptr);
    constexpr std::uint64_t generation=239, vbVersion=9, ibVersion=10;
    Vertex verts[]={{-.8f,-.8f},{-.8f,.8f},{.8f,-.8f},{.8f,.8f}};
    std::uint16_t strip16[]={0,1,2,3};
    NativeD3D9IndexedUPStripBatch batch;
    const auto capture16=[&](const void* i, UINT readable, D3DPRIMITIVETYPE type,
                             UINT triangles, UINT minVertex=0) {
        return batch.capture(device.Get(),verts,sizeof(verts),i,readable,
            type,minVertex,4,triangles,D3DFMT_INDEX16,sizeof(Vertex),
            generation,vbVersion,ibVersion);
    };
    require(!capture16(nullptr,sizeof(strip16),D3DPT_TRIANGLESTRIP,2),
            "reject null transient indices");
    require(!capture16(strip16,sizeof(strip16)-1,D3DPT_TRIANGLESTRIP,2),
            "reject short strip index span");
    require(!capture16(strip16,sizeof(strip16),D3DPT_TRIANGLELIST,2),
            "reject unsupported list topology");
    require(!capture16(strip16,sizeof(strip16),D3DPT_TRIANGLESTRIP,2,1),
            "reject nonzero MinVertexIndex");
    require(!capture16(strip16,sizeof(strip16),D3DPT_TRIANGLESTRIP,
                       0xffffffffu), "reject count overflow");
    std::uint16_t invalid[]={0,1,2,9};
    require(!capture16(invalid,sizeof(invalid),D3DPT_TRIANGLESTRIP,2),
            "reject out of range index");
    require(capture16(strip16,sizeof(strip16),D3DPT_TRIANGLESTRIP,2),
            "capture strip INDEX16");
    require(batch.index_count()==6, "two triangles expanded into six indices");
    for (auto& v:verts) v={3.f,3.f};
    for (auto& i:strip16) i=9;
    const auto ready=[&](std::uint64_t gen,std::uint64_t vv,std::uint64_t iv,
                         ID3D11PixelShader* px) {
        return batch.bind_and_verify(context.Get(),gen,vv,iv,32,32,
            DXGI_FORMAT_R8G8B8A8_UNORM,layout.Get(),vs.Get(),px,rtv.Get());
    };
    require(!ready(generation+1,vbVersion,ibVersion,ps.Get()),
            "reject stale generation");
    require(!ready(generation,vbVersion+1,ibVersion,ps.Get()),
            "reject stale vertex version");
    require(!ready(generation,vbVersion,ibVersion+1,ps.Get()),
            "reject stale index version");
    require(!ready(generation,vbVersion,ibVersion,nullptr),
            "reject missing PS");
    require(ready(generation,vbVersion,ibVersion,ps.Get()),
            "verify owned IA and one eye");
    const float black[]={0,0,0,1};
    const auto drawAndCheck=[&](const char* label) {
        context->ClearRenderTargetView(rtv.Get(),black);
        context->DrawIndexed(batch.index_count(),0,0); // WARP diagnostic only.
        context->CopyResource(readback.Get(),color.Get());
        D3D11_MAPPED_SUBRESOURCE mapped{};
        require(SUCCEEDED(context->Map(readback.Get(),0,D3D11_MAP_READ,0,
                                        &mapped)) && mapped.pData, "readback map");
        const auto* px=static_cast<const std::uint8_t*>(mapped.pData);
        const auto red=[&](UINT x,UINT y) {
            const auto* c=px+y*mapped.RowPitch+x*4u;
            return c[0]==255 && c[1]==0 && c[2]==0 && c[3]==255;
        };
        const auto clear=[&](UINT x,UINT y) {
            const auto* c=px+y*mapped.RowPitch+x*4u;
            return c[0]==0 && c[1]==0 && c[2]==0 && c[3]==255;
        };
        const bool good=red(10,10)&&red(22,22)&&clear(0,0);
        context->Unmap(readback.Get(),0);
        require(good,label);
    };
    drawAndCheck("INDEX16 both strip triangles -> GPU red, corner black");
    batch.reset();
    require(!ready(generation,vbVersion,ibVersion,ps.Get()), "retired batch");
    Vertex fresh[]={{-.8f,-.8f},{-.8f,.8f},{.8f,-.8f},{.8f,.8f}};
    std::uint32_t strip32[]={0,1,2,3};
    require(batch.capture(device.Get(),fresh,sizeof(fresh),strip32,sizeof(strip32),
        D3DPT_TRIANGLESTRIP,0,4,2,D3DFMT_INDEX32,sizeof(Vertex),
        generation,vbVersion+2,ibVersion+2), "INDEX32 capture");
    for (auto& i:strip32) i=9;
    require(batch.bind_and_verify(context.Get(),generation,vbVersion+2,
        ibVersion+2,32,32,DXGI_FORMAT_R8G8B8A8_UNORM,
        layout.Get(),vs.Get(),ps.Get(),rtv.Get()), "INDEX32 IA");
    drawAndCheck("INDEX32 both strip triangles -> GPU red, corner black");
    std::cout << "R239 D3D9 strip -> native immutable IA -> WARP pixel PASS\n";
    return 0;
}
