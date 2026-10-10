// R186: isolated WARP GPU DrawIndexed proves production-owned VB/IB +
// pipeline readiness and actual framebuffer pixels. No gameplay activation.
#include "vr/d3d11/native_indexed_uav_eye_guard.hpp"
#include <cstdint>
#include <cstdlib>
#include <d3dcompiler.h>
#include <iostream>
#include <wrl/client.h>

using Microsoft::WRL::ComPtr;
using outrun::vr::dx11::NativeLinearBufferMirror;
using outrun::vr::dx11::ResourceRole;
using outrun::vr::dx11::verified_indexed_linear_draw_ready;

static void require(bool valid, const char* label) {
    if (!valid) { std::cerr << "R186 WARP failed: " << label << '\n'; std::exit(1); }
}
int main() {
    ComPtr<ID3D11Device> device, otherDevice;
    ComPtr<ID3D11DeviceContext> context, otherContext;
    require(SUCCEEDED(D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_WARP,
        nullptr, 0, nullptr, 0, D3D11_SDK_VERSION,
        device.GetAddressOf(), nullptr, context.GetAddressOf())), "create WARP");
    require(SUCCEEDED(D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_WARP,
        nullptr, 0, nullptr, 0, D3D11_SDK_VERSION,
        otherDevice.GetAddressOf(), nullptr, otherContext.GetAddressOf())), "create other WARP");

    struct Vertex { float x, y; };
    const Vertex vertices[] = {{-.8f,-.8f},{0.f,.8f},{.8f,-.8f}};
    const std::uint16_t indices[] = {0,1,2};
    constexpr std::uint64_t generation=186, vbVersion=72, ibVersion=73;
    NativeLinearBufferMirror vb, ib;
    require(vb.initialize(device.Get(), ResourceRole::Vertex,
        D3DPOOL_DEFAULT, D3DUSAGE_WRITEONLY, D3DFMT_UNKNOWN,
        vertices, sizeof(vertices), sizeof(Vertex), generation, vbVersion), "own VB");
    require(ib.initialize(device.Get(), ResourceRole::Index,
        D3DPOOL_DEFAULT, D3DUSAGE_WRITEONLY, D3DFMT_INDEX16,
        indices, sizeof(indices), 0, generation, ibVersion), "own IB");
    require(vb.bind(context.Get(),generation,vbVersion) &&
            ib.bind(context.Get(),generation,ibVersion), "bind owned IA");

    constexpr char shader[] =
        "float4 vs(float2 p:POSITION):SV_Position{return float4(p,0,1);}"
        "float4 ps():SV_Target{return float4(0,1,0,1);}";
    ComPtr<ID3DBlob> vsCode, psCode;
    require(SUCCEEDED(D3DCompile(shader,sizeof(shader)-1,nullptr,
        nullptr,nullptr,"vs","vs_4_0",0,0,vsCode.GetAddressOf(),nullptr)), "compile VS");
    require(SUCCEEDED(D3DCompile(shader,sizeof(shader)-1,nullptr,
        nullptr,nullptr,"ps","ps_4_0",0,0,psCode.GetAddressOf(),nullptr)), "compile PS");
    ComPtr<ID3D11VertexShader> vs;
    ComPtr<ID3D11PixelShader> ps;
    require(SUCCEEDED(device->CreateVertexShader(vsCode->GetBufferPointer(),
        vsCode->GetBufferSize(),nullptr,vs.GetAddressOf())), "create VS");
    require(SUCCEEDED(device->CreatePixelShader(psCode->GetBufferPointer(),
        psCode->GetBufferSize(),nullptr,ps.GetAddressOf())), "create PS");
    const D3D11_INPUT_ELEMENT_DESC element = {
        "POSITION",0,DXGI_FORMAT_R32G32_FLOAT,0,0,D3D11_INPUT_PER_VERTEX_DATA,0};
    ComPtr<ID3D11InputLayout> layout;
    require(SUCCEEDED(device->CreateInputLayout(&element,1,vsCode->GetBufferPointer(),
        vsCode->GetBufferSize(),layout.GetAddressOf())), "create layout");

    D3D11_TEXTURE2D_DESC td{};
    td.Width=td.Height=32; td.MipLevels=td.ArraySize=1;
    td.Format=DXGI_FORMAT_R8G8B8A8_UNORM; td.SampleDesc.Count=1;
    td.Usage=D3D11_USAGE_DEFAULT; td.BindFlags=D3D11_BIND_RENDER_TARGET;
    ComPtr<ID3D11Texture2D> color;
    ComPtr<ID3D11RenderTargetView> rtv;
    require(SUCCEEDED(device->CreateTexture2D(&td,nullptr,color.GetAddressOf())), "color");
    require(SUCCEEDED(device->CreateRenderTargetView(color.Get(),nullptr,rtv.GetAddressOf())), "RTV");
    td.Usage=D3D11_USAGE_STAGING; td.BindFlags=0;
    td.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
    ComPtr<ID3D11Texture2D> readback;
    require(SUCCEEDED(device->CreateTexture2D(&td,nullptr,readback.GetAddressOf())), "staging");

    D3D11_RASTERIZER_DESC raster{};
    raster.FillMode=D3D11_FILL_SOLID; raster.CullMode=D3D11_CULL_NONE;
    raster.DepthClipEnable=TRUE;
    ComPtr<ID3D11RasterizerState> rs;
    require(SUCCEEDED(device->CreateRasterizerState(&raster,rs.GetAddressOf())), "rasterizer");
    const D3D11_VIEWPORT vp{0,0,32,32,0,1};
    context->RSSetViewports(1,&vp);
    context->RSSetState(rs.Get());
    context->IASetInputLayout(layout.Get());
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context->VSSetShader(vs.Get(),nullptr,0);
    context->PSSetShader(ps.Get(),nullptr,0);
    ID3D11RenderTargetView* rawTarget=rtv.Get();
    context->OMSetRenderTargets(1,&rawTarget,nullptr);

    const auto ready=[&](ID3D11DeviceContext* c, UINT start, UINT count,
                         INT base, std::uint64_t gen,
                         std::uint64_t vVersion, std::uint64_t iVersion) {
        return verified_indexed_linear_draw_ready(
            vb,ib,c,start,count,base,gen,vVersion,iVersion);
    };
    // R207: the old same-device preflight admits a replacement PS, which
    // actually paints a different WARP pixel. Exact expected identity must fail.
    const auto exactReady=[&]() {
        return outrun::vr::dx11::verified_indexed_pipeline_identity_ready(
            vb, ib, context.Get(), 0, 3, 0, generation, vbVersion,
            ibVersion, layout.Get(), vs.Get(), ps.Get(), rtv.Get());
    };
    require(exactReady(), "R207 exact indexed pipeline initial objects");
    constexpr char alienShader[] =
        "float4 ps():SV_Target{return float4(1,0,0,1);}";
    ComPtr<ID3DBlob> alienCode;
    require(SUCCEEDED(D3DCompile(alienShader,sizeof(alienShader)-1,nullptr,
        nullptr,nullptr,"ps","ps_4_0",0,0,alienCode.GetAddressOf(),nullptr)),
        "R207 compile same-device alien PS");
    ComPtr<ID3D11PixelShader> alienPS;
    require(SUCCEEDED(device->CreatePixelShader(alienCode->GetBufferPointer(),
        alienCode->GetBufferSize(),nullptr,alienPS.GetAddressOf())),
        "R207 create same-device alien PS");
    context->PSSetShader(alienPS.Get(),nullptr,0);
    require(ready(context.Get(),0,3,0,generation,vbVersion,ibVersion),
        "R207 same-device base guard cannot identify alien PS");
    require(!exactReady(), "R207 reject same-device alien PS identity");
    const float r207clear[] = {0,0,0,1};
    context->ClearRenderTargetView(rtv.Get(),r207clear);
    context->DrawIndexed(3,0,0);
    context->CopyResource(readback.Get(),color.Get());
    D3D11_MAPPED_SUBRESOURCE alienMap{};
    require(SUCCEEDED(context->Map(readback.Get(),0,D3D11_MAP_READ,0,&alienMap))
        && alienMap.pData, "R207 map alien PS GPU pixel");
    const auto* alienPixel=static_cast<const unsigned char*>(alienMap.pData)
        +16*alienMap.RowPitch+16*4;
    const bool alienRed=alienPixel[0]==255 && alienPixel[1]==0 &&
        alienPixel[2]==0 && alienPixel[3]==255;
    context->Unmap(readback.Get(),0);
    require(alienRed, "R207 alien PS changes real WARP indexed pixel to red");
    context->PSSetShader(ps.Get(),nullptr,0);
    require(exactReady(), "R207 restore exact expected PS");

    // R212 real WARP DrawIndexed: valid slot0 still leaks SV_Target1.
    constexpr char dualShader[] =
        "struct O{float4 a:SV_Target0;float4 b:SV_Target1;};"
        "O ps(){O o;o.a=float4(0,1,0,1);o.b=float4(1,0,0,1);return o;}";
    ComPtr<ID3DBlob> dualCode;
    require(SUCCEEDED(D3DCompile(dualShader,sizeof(dualShader)-1,
        nullptr,nullptr,nullptr,"ps","ps_4_0",0,0,
        dualCode.GetAddressOf(),nullptr)), "R212 compile dual PS");
    ComPtr<ID3D11PixelShader> dualPs;
    require(SUCCEEDED(device->CreatePixelShader(dualCode->GetBufferPointer(),
        dualCode->GetBufferSize(),nullptr,dualPs.GetAddressOf())),
        "R212 native dual-output shader");
    D3D11_TEXTURE2D_DESC foreignDesc{};
    color->GetDesc(&foreignDesc);
    ComPtr<ID3D11Texture2D> foreignColor;
    ComPtr<ID3D11RenderTargetView> foreignRtv;
    require(SUCCEEDED(device->CreateTexture2D(&foreignDesc,nullptr,
        foreignColor.GetAddressOf())), "R212 same-device foreign eye texture");
    require(SUCCEEDED(device->CreateRenderTargetView(foreignColor.Get(),
        nullptr,foreignRtv.GetAddressOf())), "R212 second eye RTV");
    context->PSSetShader(dualPs.Get(),nullptr,0);
    ID3D11RenderTargetView* twoEyes[]={rtv.Get(),foreignRtv.Get()};
    context->OMSetRenderTargets(2,twoEyes,nullptr);
    const auto oldMrtReady=[&] {
        return outrun::vr::dx11::verified_indexed_pipeline_identity_ready(
            vb,ib,context.Get(),0,3,0,generation,vbVersion,ibVersion,
            layout.Get(),vs.Get(),dualPs.Get(),rtv.Get());
    };
    const auto newMrtReady=[&] {
        return outrun::vr::dx11::verified_indexed_single_eye_output_ready(
            vb,ib,context.Get(),0,3,0,generation,vbVersion,ibVersion,
            layout.Get(),vs.Get(),dualPs.Get(),rtv.Get());
    };
    require(oldMrtReady(), "R212 R207 accepts second eye");
    require(!newMrtReady(), "R212 rejects second eye");
    const float eyeClear[]={0,0,0,1};
    context->ClearRenderTargetView(foreignRtv.Get(),eyeClear);
    context->DrawIndexed(3,0,0);
    context->CopyResource(readback.Get(),foreignColor.Get());
    D3D11_MAPPED_SUBRESOURCE eyeMap{};
    require(SUCCEEDED(context->Map(readback.Get(),0,D3D11_MAP_READ,0,
        &eyeMap)) && eyeMap.pData, "R212 map foreign eye");
    const auto* eye=static_cast<const unsigned char*>(eyeMap.pData)
        +16*eyeMap.RowPitch+16*4;
    const bool leakedRed=eye[0]==255 && eye[1]==0 &&
        eye[2]==0 && eye[3]==255;
    context->Unmap(readback.Get(),0);
    require(leakedRed, "R212 real indexed eye leak red pixel");
    context->OMSetRenderTargets(1,&rawTarget,nullptr);
    require(newMrtReady(), "R212 recovered single eye");
    context->PSSetShader(ps.Get(),nullptr,0);
    require(exactReady(), "R212 recovered original shader");

    // R217: opt-in exact indexed opaque depth-eye proof. Keep this WARP-only:
    // the game-native DrawIndexed activation boundary remains unchanged.
    D3D11_TEXTURE2D_DESC r217DepthDesc{};
    r217DepthDesc.Width=32; r217DepthDesc.Height=32;
    r217DepthDesc.MipLevels=1; r217DepthDesc.ArraySize=1;
    r217DepthDesc.Format=DXGI_FORMAT_D32_FLOAT;
    r217DepthDesc.SampleDesc.Count=1;
    r217DepthDesc.Usage=D3D11_USAGE_DEFAULT;
    r217DepthDesc.BindFlags=D3D11_BIND_DEPTH_STENCIL;
    ComPtr<ID3D11Texture2D> r217DepthTex;
    ComPtr<ID3D11DepthStencilView> r217Dsv, r217ForeignDsv;
    require(SUCCEEDED(device->CreateTexture2D(&r217DepthDesc,nullptr,
        r217DepthTex.GetAddressOf())), "R217 owned D32 eye depth surface");
    require(SUCCEEDED(device->CreateDepthStencilView(r217DepthTex.Get(),
        nullptr,r217Dsv.GetAddressOf())), "R217 owned D32 eye DSV");
    require(SUCCEEDED(device->CreateDepthStencilView(r217DepthTex.Get(),
        nullptr,r217ForeignDsv.GetAddressOf())) &&
        r217ForeignDsv.Get()!=r217Dsv.Get(),
        "R217 independent same-device DSV identity");

    D3D11_DEPTH_STENCIL_DESC r217StateDesc{};
    r217StateDesc.DepthEnable=TRUE;
    r217StateDesc.DepthWriteMask=D3D11_DEPTH_WRITE_MASK_ALL;
    r217StateDesc.DepthFunc=D3D11_COMPARISON_LESS;
    r217StateDesc.StencilEnable=FALSE;
    ComPtr<ID3D11DepthStencilState> r217State, r217NoDepth;
    require(SUCCEEDED(device->CreateDepthStencilState(&r217StateDesc,
        r217State.GetAddressOf())), "R217 opaque LESS/write-all state");
    D3D11_DEPTH_STENCIL_DESC r217InvalidDesc=r217StateDesc;
    r217InvalidDesc.DepthEnable=FALSE;
    require(SUCCEEDED(device->CreateDepthStencilState(&r217InvalidDesc,
        r217NoDepth.GetAddressOf())), "R217 disabled depth negative state");

    context->OMSetRenderTargets(1,&rawTarget,r217Dsv.Get());
    context->OMSetDepthStencilState(r217State.Get(),0u);
    const auto r217Ready=[&] {
        return outrun::vr::dx11::verified_indexed_opaque_depth_single_eye_ready(
            vb,ib,context.Get(),0u,3u,0,
            generation,vbVersion,ibVersion,layout.Get(),vs.Get(),ps.Get(),
            rtv.Get(),r217Dsv.Get(),r217State.Get());
    };
    require(r217Ready(),"R217 owned opaque depth-eye initial ready");

    context->OMSetRenderTargets(1,&rawTarget,r217ForeignDsv.Get());
    require(!r217Ready(),"R217 same-device foreign DSV rejected");
    context->OMSetRenderTargets(1,&rawTarget,r217Dsv.Get());
    context->OMSetDepthStencilState(r217NoDepth.Get(),0u);
    require(!r217Ready(),"R217 disabled depth state rejected");
    context->OMSetDepthStencilState(r217State.Get(),0u);
    context->OMSetRenderTargets(1,&rawTarget,nullptr);
    require(!r217Ready(),"R217 missing DSV rejected");
    context->OMSetRenderTargets(1,&rawTarget,r217Dsv.Get());

    D3D11_BLEND_DESC r217BlendDesc{};
    r217BlendDesc.RenderTarget[0].RenderTargetWriteMask=
        D3D11_COLOR_WRITE_ENABLE_ALL;
    ComPtr<ID3D11BlendState> r217ForeignBlend;
    require(SUCCEEDED(device->CreateBlendState(
        &r217BlendDesc,r217ForeignBlend.GetAddressOf())),
        "R217 foreign blend object");
    context->OMSetBlendState(r217ForeignBlend.Get(),nullptr,
                             D3D11_DEFAULT_SAMPLE_MASK);
    require(!r217Ready(),"R217 retained blend object rejected");
    context->OMSetBlendState(nullptr,nullptr,0u);
    require(!r217Ready(),"R217 zero OM coverage rejected");
    context->OMSetBlendState(nullptr,nullptr,D3D11_DEFAULT_SAMPLE_MASK);
    require(r217Ready(),"R217 opaque OM restored");

    // Three real indexed GPU submissions establish a depth-negative and
    // restored positive pixel, not just a descriptor / pointer assertion.
    const float r217Clear[]={0,0,0,1};
    const auto r217ReadCenter=[&](bool green){
        context->CopyResource(readback.Get(),color.Get());
        D3D11_MAPPED_SUBRESOURCE m{};
        require(SUCCEEDED(context->Map(readback.Get(),0,D3D11_MAP_READ,
            0,&m)) && m.pData,"R217 GPU indexed depth staging map");
        const auto* px=static_cast<const unsigned char*>(m.pData)
            +16*m.RowPitch+16*4;
        const bool ok=green
            ? px[0]==0u && px[1]==255u && px[2]==0u && px[3]==255u
            : px[0]==0u && px[1]==0u && px[2]==0u && px[3]==255u;
        context->Unmap(readback.Get(),0);
        return ok;
    };
    context->ClearRenderTargetView(rtv.Get(),r217Clear);
    context->ClearDepthStencilView(r217Dsv.Get(),D3D11_CLEAR_DEPTH,1.0f,0u);
    require(r217Ready(),"R217 ready prior to GPU positive");
    context->DrawIndexed(3u,0u,0);
    require(r217ReadCenter(true),"R217 WARP depth=1 draws green");
    context->ClearRenderTargetView(rtv.Get(),r217Clear);
    context->ClearDepthStencilView(r217Dsv.Get(),D3D11_CLEAR_DEPTH,0.0f,0u);
    context->DrawIndexed(3u,0u,0);
    require(r217ReadCenter(false),"R217 WARP depth=0 rejects indexed pixels");
    context->ClearDepthStencilView(r217Dsv.Get(),D3D11_CLEAR_DEPTH,1.0f,0u);
    context->DrawIndexed(3u,0u,0);
    require(r217ReadCenter(true),"R217 restored WARP indexed green pixel");

    // R218: old R217 permits a half viewport, alien raster, or a mip-one
    // DSV whose 32x32 view aliases a larger resource.
    const auto r217With = [&](ID3D11DepthStencilView* dsv) {
        return outrun::vr::dx11::verified_indexed_opaque_depth_single_eye_ready(
            vb,ib,context.Get(),0u,3u,0,generation,vbVersion,ibVersion,
            layout.Get(),vs.Get(),ps.Get(),rtv.Get(),dsv,r217State.Get());
    };
    const auto r218Ready = [&](ID3D11DepthStencilView* dsv) {
        return outrun::vr::dx11::verified_indexed_sealed_opaque_eye_draw_ready(
            vb,ib,context.Get(),0u,3u,0,generation,vbVersion,ibVersion,
            32u,32u,DXGI_FORMAT_R8G8B8A8_UNORM,
            layout.Get(),vs.Get(),ps.Get(),rtv.Get(),dsv,r217State.Get(),
            rs.Get());
    };
    require(r218Ready(r217Dsv.Get()),"R218 initial exact indexed eye");
    D3D11_VIEWPORT r218Cropped=vp;
    r218Cropped.Width=16.f;
    context->RSSetViewports(1,&r218Cropped);
    require(r217Ready(),"R218 old guard accepts half viewport");
    require(!r218Ready(r217Dsv.Get()),"R218 reject cropped viewport");
    context->RSSetViewports(1,&vp);
    require(r218Ready(r217Dsv.Get()),"R218 viewport restored");
    D3D11_RASTERIZER_DESC r218AlienRasterDesc=raster;
    r218AlienRasterDesc.CullMode=D3D11_CULL_BACK;
    ComPtr<ID3D11RasterizerState> r218AlienRaster;
    require(SUCCEEDED(device->CreateRasterizerState(&r218AlienRasterDesc,
        r218AlienRaster.GetAddressOf())),"R218 create foreign raster");
    context->RSSetState(r218AlienRaster.Get());
    require(r217Ready(),"R218 old guard accepts foreign raster");
    require(!r218Ready(r217Dsv.Get()),"R218 reject alien raster");
    context->RSSetState(rs.Get());
    require(r218Ready(r217Dsv.Get()),"R218 raster restored");

    D3D11_TEXTURE2D_DESC r218MipDesc=r217DepthDesc;
    r218MipDesc.Width=64u;
    r218MipDesc.Height=64u;
    r218MipDesc.MipLevels=2u;
    ComPtr<ID3D11Texture2D> r218MipTexture;
    ComPtr<ID3D11DepthStencilView> r218MipDsv;
    D3D11_DEPTH_STENCIL_VIEW_DESC r218MipView{};
    r218MipView.Format=DXGI_FORMAT_D32_FLOAT;
    r218MipView.ViewDimension=D3D11_DSV_DIMENSION_TEXTURE2D;
    r218MipView.Texture2D.MipSlice=1u;
    require(SUCCEEDED(device->CreateTexture2D(&r218MipDesc,nullptr,
        r218MipTexture.GetAddressOf())),"R218 create mip-aliased depth");
    require(SUCCEEDED(device->CreateDepthStencilView(r218MipTexture.Get(),
        &r218MipView,r218MipDsv.GetAddressOf())),"R218 create nonbase DSV");
    context->OMSetRenderTargets(1,&rawTarget,r218MipDsv.Get());
    require(r217With(r218MipDsv.Get()),
        "R218 old guard accepts exact live mip-one DSV");
    require(!r218Ready(r218MipDsv.Get()),"R218 reject mip-aliased DSV");
    context->OMSetRenderTargets(1,&rawTarget,r217Dsv.Get());
    require(r218Ready(r217Dsv.Get()),"R218 dedicated depth restored");
    context->ClearRenderTargetView(rtv.Get(),r217Clear);
    context->ClearDepthStencilView(r217Dsv.Get(),D3D11_CLEAR_DEPTH,1.f,0u);
    require(r218Ready(r217Dsv.Get()),"R218 ready before restored WARP DrawIndexed");
    context->DrawIndexed(3u,0u,0);
    require(r217ReadCenter(true),"R218 restored WARP green indexed pixel");
    // R226: actual indexed WARP GPU draw under the new dedicated depth
    // resource preflight; no game-native DrawIndexed activation.
    D3D11_TEXTURE2D_DESC r226Backing{};
    r217DepthTex->GetDesc(&r226Backing);
    require(r226Backing.BindFlags == D3D11_BIND_DEPTH_STENCIL &&
            r226Backing.MiscFlags == 0u,
            "R226 WARP D32 dedicated backing descriptor");
    require(r218Ready(r217Dsv.Get()), "R226 dedicated D32 ready");
    context->ClearRenderTargetView(rtv.Get(),r217Clear);
    context->ClearDepthStencilView(r217Dsv.Get(),D3D11_CLEAR_DEPTH,1.f,0u);
    context->DrawIndexed(3u,0u,0);
    require(r217ReadCenter(true),
            "R226 dedicated D32 indexed DrawIndexed green pixel");


    // R219: an OM UAV does not occupy a second RTV slot. The old composed
    // full-eye guard accepts it even though a real indexed PS can write it.
    D3D11_TEXTURE2D_DESC r219UavDesc{};
    r219UavDesc.Width=r219UavDesc.Height=4u;
    r219UavDesc.MipLevels=r219UavDesc.ArraySize=1u;
    r219UavDesc.Format=DXGI_FORMAT_R32_UINT;
    r219UavDesc.SampleDesc.Count=1u;
    r219UavDesc.Usage=D3D11_USAGE_DEFAULT;
    r219UavDesc.BindFlags=D3D11_BIND_UNORDERED_ACCESS;
    ComPtr<ID3D11Texture2D> r219ForeignTexture;
    ComPtr<ID3D11UnorderedAccessView> r219ForeignUav;
    require(SUCCEEDED(device->CreateTexture2D(&r219UavDesc,nullptr,
        r219ForeignTexture.GetAddressOf())), "R219 create foreign UAV texture");
    require(SUCCEEDED(device->CreateUnorderedAccessView(
        r219ForeignTexture.Get(),nullptr,r219ForeignUav.GetAddressOf())),
        "R219 create foreign UAV");
    D3D11_TEXTURE2D_DESC r219ReadDesc=r219UavDesc;
    r219ReadDesc.Usage=D3D11_USAGE_STAGING;
    r219ReadDesc.BindFlags=0u;
    r219ReadDesc.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
    ComPtr<ID3D11Texture2D> r219Readback;
    require(SUCCEEDED(device->CreateTexture2D(&r219ReadDesc,nullptr,
        r219Readback.GetAddressOf())), "R219 foreign UAV readback");
    constexpr char r219Shader[] =
        "RWTexture2D<uint> foreignEye:register(u1);"
        "float4 ps():SV_Target{foreignEye[uint2(0,0)]=0x1234u;"
        "return float4(0,1,0,1);}";
    ComPtr<ID3DBlob> r219Code;
    require(SUCCEEDED(D3DCompile(r219Shader,sizeof(r219Shader)-1,nullptr,
        nullptr,nullptr,"ps","ps_5_0",0u,0u,
        r219Code.GetAddressOf(),nullptr)), "R219 compile PS with hidden UAV");
    ComPtr<ID3D11PixelShader> r219Ps;
    require(SUCCEEDED(device->CreatePixelShader(r219Code->GetBufferPointer(),
        r219Code->GetBufferSize(),nullptr,r219Ps.GetAddressOf())),
        "R219 create PS with hidden UAV");
    const auto r219OldReady = [&] {
        return outrun::vr::dx11::verified_indexed_sealed_opaque_eye_draw_ready(
            vb,ib,context.Get(),0u,3u,0,generation,vbVersion,ibVersion,
            32u,32u,DXGI_FORMAT_R8G8B8A8_UNORM,layout.Get(),vs.Get(),
            r219Ps.Get(),rtv.Get(),r217Dsv.Get(),r217State.Get(),rs.Get());
    };
    const auto r219NewReady = [&](ID3D11PixelShader* expectedPs) {
        return outrun::vr::dx11::verified_indexed_uav_isolated_eye_ready(
            vb,ib,context.Get(),0u,3u,0,generation,vbVersion,ibVersion,
            32u,32u,DXGI_FORMAT_R8G8B8A8_UNORM,layout.Get(),vs.Get(),
            expectedPs,rtv.Get(),r217Dsv.Get(),r217State.Get(),rs.Get());
    };
    context->PSSetShader(r219Ps.Get(),nullptr,0u);
    ID3D11UnorderedAccessView* r219BoundUav=r219ForeignUav.Get();
    context->OMSetRenderTargetsAndUnorderedAccessViews(
        1u,&rawTarget,r217Dsv.Get(),1u,1u,&r219BoundUav,nullptr);
    require(r219OldReady(),"R219 old guard accepts extra OM UAV");
    require(!r219NewReady(r219Ps.Get()),"R219 new guard rejects extra OM UAV");
    const UINT r219ClearUav[4]={0u,0u,0u,0u};
    context->ClearUnorderedAccessViewUint(r219ForeignUav.Get(),r219ClearUav);
    context->ClearRenderTargetView(rtv.Get(),r217Clear);
    context->ClearDepthStencilView(r217Dsv.Get(),D3D11_CLEAR_DEPTH,1.f,0u);
    context->DrawIndexed(3u,0u,0);
    context->CopyResource(r219Readback.Get(),r219ForeignTexture.Get());
    D3D11_MAPPED_SUBRESOURCE r219Mapped{};
    require(SUCCEEDED(context->Map(r219Readback.Get(),0u,D3D11_MAP_READ,
        0u,&r219Mapped)) && r219Mapped.pData,
        "R219 map foreign UAV GPU output");
    const auto r219Written=*static_cast<const UINT*>(r219Mapped.pData);
    context->Unmap(r219Readback.Get(),0u);
    require(r219Written==0x1234u,
        "R219 WARP hidden UAV writes real second texture");
    require(r217ReadCenter(true),"R219 WARP indexed RTV remains green");
    ID3D11UnorderedAccessView* r219NullUav=nullptr;
    context->OMSetRenderTargetsAndUnorderedAccessViews(
        1u,&rawTarget,r217Dsv.Get(),1u,1u,&r219NullUav,nullptr);
    context->PSSetShader(ps.Get(),nullptr,0u);
    require(r219NewReady(ps.Get()),"R219 UAV unbound restores isolated eye");
    context->ClearRenderTargetView(rtv.Get(),r217Clear);
    context->ClearDepthStencilView(r217Dsv.Get(),D3D11_CLEAR_DEPTH,1.f,0u);
    context->DrawIndexed(3u,0u,0);
    require(r217ReadCenter(true),"R219 restored WARP indexed green pixel");

    context->OMSetRenderTargets(1,&rawTarget,nullptr);
    context->OMSetDepthStencilState(nullptr,0u);



    require(!ready(context.Get(),0,0,0,generation,vbVersion,ibVersion), "reject zero indices");
    require(!ready(context.Get(),0,2,0,generation,vbVersion,ibVersion), "reject partial triangle");
    require(!ready(context.Get(),1,3,0,generation,vbVersion,ibVersion), "reject IB overrun");
    require(!ready(context.Get(),0,3,1,generation,vbVersion,ibVersion), "reject VB overrun");
    require(!ready(context.Get(),0,3,-1,generation,vbVersion,ibVersion), "reject negative VB");
    require(!ready(context.Get(),0,3,0,generation+1,vbVersion,ibVersion), "reject generation");
    require(!ready(context.Get(),0,3,0,generation,vbVersion+1,ibVersion), "reject stale VB");
    require(!ready(context.Get(),0,3,0,generation,vbVersion,ibVersion+1), "reject stale IB");
    require(!ready(otherContext.Get(),0,3,0,generation,vbVersion,ibVersion), "reject other device");
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_LINELIST);
    require(!ready(context.Get(),0,3,0,generation,vbVersion,ibVersion), "reject wrong topology");
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context->IASetInputLayout(nullptr);
    require(!ready(context.Get(),0,3,0,generation,vbVersion,ibVersion), "reject missing layout");
    context->IASetInputLayout(layout.Get());
    context->PSSetShader(nullptr,nullptr,0);
    require(!ready(context.Get(),0,3,0,generation,vbVersion,ibVersion), "reject missing PS");
    context->PSSetShader(ps.Get(),nullptr,0);
    context->OMSetRenderTargets(0,nullptr,nullptr);
    require(!ready(context.Get(),0,3,0,generation,vbVersion,ibVersion), "reject missing RTV");
    context->OMSetRenderTargets(1,&rawTarget,nullptr);

    require(ready(context.Get(),0,3,0,generation,vbVersion,ibVersion),
            "owned indexed IA + pipeline readiness");
    // R196: a retained geometry shader can silently move all original
    // vertices beyond the clip volume, despite valid owned IA/VS/PS/RTV.
    constexpr char geometry[] =
        "struct V {float4 p:SV_Position;};"
        "[maxvertexcount(3)]"
        "void gs(triangle V tri[3],inout TriangleStream<V> stream){"
        "for(uint i=0;i<3;++i){V v=tri[i];v.p.xy=float2(2,2);stream.Append(v);}}";
    ComPtr<ID3DBlob> gsCode;
    require(SUCCEEDED(D3DCompile(geometry,sizeof(geometry)-1,nullptr,
        nullptr,nullptr,"gs","gs_4_0",0,0,gsCode.GetAddressOf(),nullptr)),
        "compile interfering GS");
    ComPtr<ID3D11GeometryShader> gs;
    require(SUCCEEDED(device->CreateGeometryShader(gsCode->GetBufferPointer(),
        gsCode->GetBufferSize(),nullptr,gs.GetAddressOf())), "create interfering GS");
    const float clear[] = {0,0,0,1};
    context->GSSetShader(gs.Get(),nullptr,0);
    require(!ready(context.Get(),0,3,0,generation,vbVersion,ibVersion),
            "reject unexpected live GS");
    context->ClearRenderTargetView(rtv.Get(),clear);
    context->DrawIndexed(3,0,0);
    context->CopyResource(readback.Get(),color.Get());
    D3D11_MAPPED_SUBRESOURCE hiddenMap{};
    require(SUCCEEDED(context->Map(readback.Get(),0,D3D11_MAP_READ,0,&hiddenMap))
        && hiddenMap.pData, "map GS-suppressed indexed pixel");
    const auto* hidden=static_cast<const unsigned char*>(hiddenMap.pData)
        +16*hiddenMap.RowPitch+16*4;
    const bool suppressed=hidden[0]==0 && hidden[1]==0 &&
        hidden[2]==0 && hidden[3]==255;
    context->Unmap(readback.Get(),0);
    require(suppressed, "R196 GS must change actual WARP DrawIndexed pixels");
    context->GSSetShader(nullptr,nullptr,0);
    require(ready(context.Get(),0,3,0,generation,vbVersion,ibVersion),
            "restore pure VS/PS indexed pipeline");
    context->ClearRenderTargetView(rtv.Get(),clear);
    // Only tools/ owns actual DrawIndexed dispatch; production helper has none.
    context->DrawIndexed(3,0,0);
    context->CopyResource(readback.Get(),color.Get());
    D3D11_MAPPED_SUBRESOURCE mapped{};
    require(SUCCEEDED(context->Map(readback.Get(),0,D3D11_MAP_READ,0,&mapped)) &&
            mapped.pData, "GPU readback map");
    const auto* pixels=static_cast<const unsigned char*>(mapped.pData);
    const auto* center=pixels+16*mapped.RowPitch+16*4;
    const auto* corner=pixels+1*mapped.RowPitch+1*4;
    const bool correct=center[0]==0 && center[1]==255 && center[2]==0 &&
        center[3]==255 && corner[0]==0 && corner[1]==0 && corner[2]==0;
    context->Unmap(readback.Get(),0);
    require(correct, "R186 actual DrawIndexed green center / black corner pixels");
    ib.shutdown();
    require(!ready(context.Get(),0,3,0,generation,vbVersion,ibVersion),
            "reject retired IB owner");
    std::cout << "R186 owned indexed DrawIndexed WARP pixels and fail-closed states: PASS\n";
}
