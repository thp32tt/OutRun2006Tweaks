// R183: actual WARP DrawIndexed consumes production-owned VB and IB objects.
// No game draw hook, backend activation or Quest 3 runtime claim.
#include "vr/d3d11/native_linear_buffer_mirror.hpp"
#include "vr/d3d11/native_linear_target_viewport.hpp"
#include "vr/d3d11/native_linear_uav_eye_guard.hpp"
#include <cstdint>
#include <cstdlib>
#include <d3dcompiler.h>
#include <iostream>
#include <wrl/client.h>

using Microsoft::WRL::ComPtr;
using outrun::vr::dx11::NativeLinearBufferMirror;
using outrun::vr::dx11::ResourceRole;

void require(bool ok, const char* why) {
    if (!ok) { std::cerr << "R183 WARP failure: " << why << '\n'; std::exit(1); }
}
int main() {
    ComPtr<ID3D11Device> dev, other;
    ComPtr<ID3D11DeviceContext> ctx, otherCtx;
    require(SUCCEEDED(D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_WARP,
        nullptr, 0, nullptr, 0, D3D11_SDK_VERSION,
        dev.GetAddressOf(), nullptr, ctx.GetAddressOf())), "WARP device");
    require(SUCCEEDED(D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_WARP,
        nullptr, 0, nullptr, 0, D3D11_SDK_VERSION,
        other.GetAddressOf(), nullptr, otherCtx.GetAddressOf())), "other device");
    struct Vertex { float x, y; };
    const Vertex vertices[] = {{-.9f,-.9f},{0.f,.9f},{.9f,-.9f}};
    const std::uint16_t indices[] = {0,1,2,99,100,101};
    NativeLinearBufferMirror vb, ib;
    constexpr std::uint64_t generation = 71, version = 183;
    require(!vb.initialize(dev.Get(), ResourceRole::Vertex,
        D3DPOOL_DEFAULT, D3DUSAGE_WRITEONLY, D3DFMT_UNKNOWN,
        vertices, sizeof(vertices), 0, generation, version),
        "zero stride rejected");
    require(!ib.initialize(dev.Get(), ResourceRole::Index,
        D3DPOOL_DEFAULT, D3DUSAGE_WRITEONLY, D3DFMT_INDEX16,
        indices, 3, 0, generation, version),
        "misaligned index bytes rejected");
    require(!vb.initialize(dev.Get(), ResourceRole::Vertex,
        D3DPOOL_DEFAULT, D3DUSAGE_DYNAMIC | D3DUSAGE_WRITEONLY,
        D3DFMT_UNKNOWN, vertices, sizeof(vertices), sizeof(Vertex),
        generation, version), "dynamic without mutation owner rejected");
    require(vb.initialize(dev.Get(), ResourceRole::Vertex,
        D3DPOOL_DEFAULT, D3DUSAGE_WRITEONLY, D3DFMT_UNKNOWN,
        vertices, sizeof(vertices), sizeof(Vertex), generation, version),
        "real vertex buffer upload");
    require(ib.initialize(dev.Get(), ResourceRole::Index,
        D3DPOOL_DEFAULT, D3DUSAGE_WRITEONLY, D3DFMT_INDEX16,
        indices, sizeof(indices), 0, generation, version),
        "real index buffer upload");
    require(vb.descriptor_exact() && ib.descriptor_exact(),
        "owner descriptor and GetDevice");
    require(!vb.bind(ctx.Get(), generation+1, version),
        "device generation mismatch rejected");
    require(!ib.bind(ctx.Get(), generation, version+1),
        "stale snapshot rejected");
    require(!vb.bind(otherCtx.Get(), generation, version),
        "cross-device VB bind rejected");
    require(!ib.bind(otherCtx.Get(), generation, version),
        "cross-device IB bind rejected");
    ComPtr<ID3D11DeviceContext> deferred;
    require(SUCCEEDED(dev->CreateDeferredContext(0, deferred.GetAddressOf())),
        "deferred context creation");
    require(!vb.bind(deferred.Get(), generation, version),
        "deferred VB context rejected");
    require(vb.bind(ctx.Get(), generation, version) &&
            ib.bind(ctx.Get(), generation, version),
        "immediate IA VB/IB object binding");
    require(vb.binding_exact(ctx.Get(), generation, version) &&
            ib.binding_exact(ctx.Get(), generation, version),
        "GetVertexBuffers/GetIndexBuffer object identity");

    // R184: dormant DrawIndexed range attestations run before live GPU proof.
    require(vb.indexed_draw_bounds_exact(ib,ctx.Get(),0,3,0,
            generation,version,version), "valid complete index slice");
    // R195: the selected subset is valid though an unrelated trailing
    // index slice addresses vertices absent from the currently bound VB.
    require(!vb.indexed_draw_bounds_exact(ib,ctx.Get(),0,6,0,
            generation,version,version), "R195 reject whole IB invalid tail");
    require(!vb.indexed_draw_bounds_exact(ib,ctx.Get(),3,3,0,
            generation,version,version), "R195 reject bad tail slice");
    require(!vb.indexed_draw_bounds_exact(ib,ctx.Get(),0,0,0,
            generation,version,version), "empty indexed draw rejected");
    require(!vb.indexed_draw_bounds_exact(ib,ctx.Get(),1,3,0,
            generation,version,version), "index window overrun rejected");
    require(!vb.indexed_draw_bounds_exact(ib,ctx.Get(),0,3,1,
            generation,version,version), "positive base vertex overrun rejected");
    require(!vb.indexed_draw_bounds_exact(ib,ctx.Get(),0,3,-1,
            generation,version,version), "negative base vertex underrun rejected");
    require(!vb.indexed_draw_bounds_exact(ib,otherCtx.Get(),0,3,0,
            generation,version,version), "foreign IA state rejected");
    require(!vb.indexed_draw_bounds_exact(ib,ctx.Get(),0,3,0,
            generation,version+1,version), "stale VB snapshot rejected");
    require(!vb.indexed_draw_bounds_exact(ib,ctx.Get(),0,3,0,
            generation,version,version+1), "stale IB snapshot rejected");
    require(!ib.indexed_draw_bounds_exact(vb,ctx.Get(),0,3,0,
            generation,version,version), "swapped buffer roles rejected");

    const char hlsl[] =
        "float4 vs(float2 p:POSITION):SV_Position{return float4(p,0,1);}"
        "float4 ps():SV_Target{return float4(1,0,0,1);}";
    ComPtr<ID3DBlob> vsCode, psCode;
    require(SUCCEEDED(D3DCompile(hlsl, sizeof(hlsl)-1, nullptr,
        nullptr, nullptr, "vs", "vs_4_0", 0, 0,
        vsCode.GetAddressOf(), nullptr)), "vertex shader compile");
    require(SUCCEEDED(D3DCompile(hlsl, sizeof(hlsl)-1, nullptr,
        nullptr, nullptr, "ps", "ps_4_0", 0, 0,
        psCode.GetAddressOf(), nullptr)), "pixel shader compile");
    ComPtr<ID3D11VertexShader> vs;
    ComPtr<ID3D11PixelShader> ps;
    require(SUCCEEDED(dev->CreateVertexShader(
        vsCode->GetBufferPointer(), vsCode->GetBufferSize(), nullptr,
        vs.GetAddressOf())), "vertex shader object");
    require(SUCCEEDED(dev->CreatePixelShader(
        psCode->GetBufferPointer(), psCode->GetBufferSize(), nullptr,
        ps.GetAddressOf())), "pixel shader object");
    const D3D11_INPUT_ELEMENT_DESC input = {
        "POSITION",0,DXGI_FORMAT_R32G32_FLOAT,0,0,
        D3D11_INPUT_PER_VERTEX_DATA,0};
    ComPtr<ID3D11InputLayout> layout;
    require(SUCCEEDED(dev->CreateInputLayout(&input, 1,
        vsCode->GetBufferPointer(), vsCode->GetBufferSize(),
        layout.GetAddressOf())), "input layout");
    D3D11_TEXTURE2D_DESC td{};
    td.Width=td.Height=32; td.MipLevels=td.ArraySize=1;
    td.Format=DXGI_FORMAT_R8G8B8A8_UNORM;
    td.SampleDesc.Count=1; td.Usage=D3D11_USAGE_DEFAULT;
    td.BindFlags=D3D11_BIND_RENDER_TARGET;
    ComPtr<ID3D11Texture2D> color;
    ComPtr<ID3D11RenderTargetView> rtv;
    require(SUCCEEDED(dev->CreateTexture2D(&td,nullptr,color.GetAddressOf())),
            "GPU RT");
    require(SUCCEEDED(dev->CreateRenderTargetView(color.Get(),nullptr,
            rtv.GetAddressOf())), "GPU RTV");
    td.Usage=D3D11_USAGE_STAGING; td.BindFlags=0;
    td.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
    ComPtr<ID3D11Texture2D> staging;
    require(SUCCEEDED(dev->CreateTexture2D(&td,nullptr,staging.GetAddressOf())),
            "GPU staging");
    D3D11_RASTERIZER_DESC raster{};
    raster.FillMode=D3D11_FILL_SOLID;
    raster.CullMode=D3D11_CULL_NONE;
    raster.DepthClipEnable=TRUE;
    ComPtr<ID3D11RasterizerState> rs;
    require(SUCCEEDED(dev->CreateRasterizerState(&raster,rs.GetAddressOf())),
            "rasterizer state");
    const D3D11_VIEWPORT vp{0,0,32,32,0,1};
    ctx->RSSetViewports(1,&vp);
    ctx->RSSetState(rs.Get());
    ctx->IASetInputLayout(layout.Get());
    ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    ctx->VSSetShader(vs.Get(),nullptr,0);
    ctx->PSSetShader(ps.Get(),nullptr,0);
    ID3D11RenderTargetView* rawRTV=rtv.Get();
    ctx->OMSetRenderTargets(1,&rawRTV,nullptr);
    const float clear[]{0,0,0,1};
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    require(vb.binding_exact(ctx.Get(),generation,version) &&
            ib.binding_exact(ctx.Get(),generation,version),
            "VB and IB ready immediately before GPU DrawIndexed");
    require(vb.indexed_draw_bounds_exact(ib,ctx.Get(),0,3,0,
            generation,version,version), "R184 range and live IA ready before GPU");
    ctx->DrawIndexed(3,0,0);
    ctx->CopyResource(staging.Get(),color.Get());
    D3D11_MAPPED_SUBRESOURCE mapped{};
    require(SUCCEEDED(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,&mapped)) &&
            mapped.pData, "GPU staging readback");
    const auto* bytes=static_cast<const unsigned char*>(mapped.pData);
    const auto* center=bytes+16*mapped.RowPitch+16*4;
    const auto* corner=bytes+1*mapped.RowPitch+1*4;
    const bool pixels=center[0]==255 && center[1]==0 &&
        center[2]==0 && center[3]==255 &&
        corner[0]==0 && corner[1]==0 && corner[2]==0;
    ctx->Unmap(staging.Get(),0);
    require(pixels,"real VB/IB DrawIndexed GPU pixel readback");

    // R185: production exposes readiness-only, while this isolated WARP tool
    // submits the actual non-indexed GPU Draw. Game activation stays blocked.
    using outrun::vr::dx11::verified_linear_draw_ready;
    require(!verified_linear_draw_ready(vb,ctx.Get(),0,0,generation,version),
            "linear Draw zero count rejected");
    require(!verified_linear_draw_ready(vb,ctx.Get(),0,4,generation,version),
            "linear Draw vertex extent rejected");
    require(!verified_linear_draw_ready(vb,ctx.Get(),1,3,generation,version),
            "linear Draw start offset overrun rejected");
    require(!verified_linear_draw_ready(vb,otherCtx.Get(),0,3,generation,version),
            "linear Draw foreign device rejected");
    require(!verified_linear_draw_ready(vb,ctx.Get(),0,3,generation,version+1),
            "linear Draw stale snapshot rejected");
    ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_LINELIST);
    require(!verified_linear_draw_ready(vb,ctx.Get(),0,3,generation,version),
            "linear Draw foreign topology rejected");
    ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    ctx->PSSetShader(nullptr,nullptr,0);
    require(!verified_linear_draw_ready(vb,ctx.Get(),0,3,generation,version),
            "linear Draw missing PS rejected");
    ctx->PSSetShader(ps.Get(),nullptr,0);
    ctx->OMSetRenderTargets(0,nullptr,nullptr);
    require(!verified_linear_draw_ready(vb,ctx.Get(),0,3,generation,version),
            "linear Draw missing RT rejected");
    ctx->OMSetRenderTargets(1,&rawRTV,nullptr);
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    require(verified_linear_draw_ready(vb,ctx.Get(),0,3,generation,version),
            "R185 dormant native linear Draw IA/pipeline ready");
    // R209: R185 passes a same-device alien PS, but exact pipeline identity
    // must reject it. Real WARP non-indexed GPU Draw changes red to green.
    const auto exactLinearReady = [&] {
        return outrun::vr::dx11::verified_linear_pipeline_identity_ready(
            vb,ctx.Get(),0,3,generation,version,
            layout.Get(),vs.Get(),ps.Get(),rtv.Get());
    };
    require(exactLinearReady(), "R209 exact linear pipeline initial objects");
    require(!outrun::vr::dx11::verified_linear_pipeline_identity_ready(
            vb,ctx.Get(),0,3,generation,version,
            layout.Get(),vs.Get(),nullptr,rtv.Get()),
            "R209 reject absent expected PS");
    constexpr char alienLinearShader[] =
        "float4 ps():SV_Target{return float4(0,1,0,1);}";
    ComPtr<ID3DBlob> alienLinearCode;
    require(SUCCEEDED(D3DCompile(alienLinearShader,
        sizeof(alienLinearShader)-1,nullptr,nullptr,nullptr,
        "ps","ps_4_0",0,0,alienLinearCode.GetAddressOf(),nullptr)),
        "R209 compile alternate same-device PS");
    ComPtr<ID3D11PixelShader> alienLinearPs;
    require(SUCCEEDED(dev->CreatePixelShader(
        alienLinearCode->GetBufferPointer(),alienLinearCode->GetBufferSize(),
        nullptr,alienLinearPs.GetAddressOf())),
        "R209 create alternate same-device PS");
    ctx->PSSetShader(alienLinearPs.Get(),nullptr,0);
    require(verified_linear_draw_ready(vb,ctx.Get(),0,3,generation,version),
            "R209 base readiness admits alien same-device PS");
    require(!exactLinearReady(), "R209 reject alternate same-device PS");
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    ctx->Draw(3,0);
    ctx->CopyResource(staging.Get(),color.Get());
    D3D11_MAPPED_SUBRESOURCE alienLinearMap{};
    require(SUCCEEDED(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,
            &alienLinearMap)) && alienLinearMap.pData,
            "R209 map changed real WARP nonindexed pixel");
    const auto* alienLinearPixel =
        static_cast<const unsigned char*>(alienLinearMap.pData)
        +16*alienLinearMap.RowPitch+16*4;
    const bool alienGreen=alienLinearPixel[0]==0 &&
        alienLinearPixel[1]==255 && alienLinearPixel[2]==0 &&
        alienLinearPixel[3]==255;
    ctx->Unmap(staging.Get(),0);
    require(alienGreen, "R209 alien PS changes real WARP linear pixel green");
    ctx->PSSetShader(ps.Get(),nullptr,0);
    require(exactLinearReady(), "R209 restore exact linear pipeline PS");


    // R210: same-device foreign OM DSV defeats an otherwise exact R209
    // pipeline: depth LESS against 0 discards the actual WARP red pixel.
    D3D11_TEXTURE2D_DESC depthDesc{};
    depthDesc.Width=depthDesc.Height=32;
    depthDesc.MipLevels=depthDesc.ArraySize=1;
    depthDesc.Format=DXGI_FORMAT_D32_FLOAT;
    depthDesc.SampleDesc.Count=1;
    depthDesc.Usage=D3D11_USAGE_DEFAULT;
    depthDesc.BindFlags=D3D11_BIND_DEPTH_STENCIL;
    ComPtr<ID3D11Texture2D> ownDepth, foreignDepth;
    ComPtr<ID3D11DepthStencilView> ownDsv, foreignDsv;
    require(SUCCEEDED(dev->CreateTexture2D(&depthDesc,nullptr,
            ownDepth.GetAddressOf())), "R210 owned depth texture");
    require(SUCCEEDED(dev->CreateTexture2D(&depthDesc,nullptr,
            foreignDepth.GetAddressOf())), "R210 alien depth texture");
    require(SUCCEEDED(dev->CreateDepthStencilView(ownDepth.Get(),nullptr,
            ownDsv.GetAddressOf())), "R210 owned depth view");
    require(SUCCEEDED(dev->CreateDepthStencilView(foreignDepth.Get(),nullptr,
            foreignDsv.GetAddressOf())), "R210 alien same-device depth view");
    D3D11_DEPTH_STENCIL_DESC depthStateDesc{};
    depthStateDesc.DepthEnable=TRUE;
    depthStateDesc.DepthWriteMask=D3D11_DEPTH_WRITE_MASK_ALL;
    depthStateDesc.DepthFunc=D3D11_COMPARISON_LESS;
    depthStateDesc.StencilEnable=FALSE;
    ComPtr<ID3D11DepthStencilState> depthState, alienDepthState;
    require(SUCCEEDED(dev->CreateDepthStencilState(&depthStateDesc,
            depthState.GetAddressOf())), "R210 owned depth state");
    ctx->OMSetDepthStencilState(depthState.Get(),0);
    ctx->OMSetRenderTargets(1,&rawRTV,ownDsv.Get());
    const auto exactDepthReady = [&] {
        return outrun::vr::dx11::verified_linear_depth_om_identity_ready(
            vb,ctx.Get(),0,3,generation,version,
            layout.Get(),vs.Get(),ps.Get(),rtv.Get(),
            ownDsv.Get(),depthState.Get());
    };
    require(exactDepthReady(), "R210 exact owned OM DSV and depth state");

    // R211: old R210 verifies OM slot 0 only; a second same-device eye
    // attachment must not be accepted as an isolated non-indexed eye.
    const auto singleEyeDepthReady = [&] {
        return outrun::vr::dx11::verified_linear_single_eye_depth_draw_ready(
            vb,ctx.Get(),0,3,generation,version,
            layout.Get(),vs.Get(),ps.Get(),rtv.Get(),
            ownDsv.Get(),depthState.Get());
    };
    require(singleEyeDepthReady(), "R211 isolated single-eye depth ready");
    D3D11_TEXTURE2D_DESC secondEyeDesc{};
    color->GetDesc(&secondEyeDesc);
    ComPtr<ID3D11Texture2D> secondEyeTexture;
    ComPtr<ID3D11RenderTargetView> secondEyeView;
    require(SUCCEEDED(dev->CreateTexture2D(&secondEyeDesc,nullptr,
            secondEyeTexture.GetAddressOf())), "R211 create second-eye texture");
    require(SUCCEEDED(dev->CreateRenderTargetView(secondEyeTexture.Get(),nullptr,
            secondEyeView.GetAddressOf())), "R211 create second-eye RTV");
    ID3D11RenderTargetView* twoEyes[] = {rawRTV,secondEyeView.Get()};
    ctx->OMSetRenderTargets(2,twoEyes,ownDsv.Get());
    require(exactDepthReady(), "R211 R210 slot-zero guard admits extra eye MRT");
    require(!singleEyeDepthReady(), "R211 reject same-device secondary eye RTV");
    ctx->OMSetRenderTargets(1,&rawRTV,ownDsv.Get());
    require(singleEyeDepthReady(), "R211 restore one eye before real WARP Draw");

    // R214: even with exact depth/shaders and only one OM eye, a retained
    // non-opaque blend or zero sample mask must refuse native Draw readiness.
    // Prove the rejected states actually suppress the isolated WARP Draw.
    const auto exactOpaqueEyeReady = [&] {
        return outrun::vr::dx11::verified_linear_opaque_single_eye_draw_ready(
            vb,ctx.Get(),0,3,generation,version,
            layout.Get(),vs.Get(),ps.Get(),rtv.Get(),
            ownDsv.Get(),depthState.Get());
    };
    ctx->OMSetBlendState(nullptr,nullptr,D3D11_DEFAULT_SAMPLE_MASK);
    require(exactOpaqueEyeReady(), "R214 opaque linear single-eye OM ready");
    D3D11_BLEND_DESC keepColorDesc{};
    auto& keep = keepColorDesc.RenderTarget[0];
    keep.BlendEnable = TRUE;
    keep.SrcBlend = D3D11_BLEND_ZERO;
    keep.DestBlend = D3D11_BLEND_ONE;
    keep.BlendOp = D3D11_BLEND_OP_ADD;
    keep.SrcBlendAlpha = D3D11_BLEND_ZERO;
    keep.DestBlendAlpha = D3D11_BLEND_ONE;
    keep.BlendOpAlpha = D3D11_BLEND_OP_ADD;
    keep.RenderTargetWriteMask = D3D11_COLOR_WRITE_ENABLE_ALL;
    ComPtr<ID3D11BlendState> keepColorBlend;
    require(SUCCEEDED(dev->CreateBlendState(
            &keepColorDesc,keepColorBlend.GetAddressOf())),
            "R214 create actual WARP color-preserving blend");
    const auto samplePixelEquals = [&](unsigned char r, unsigned char g,
                                       unsigned char b) {
        ctx->CopyResource(staging.Get(),color.Get());
        D3D11_MAPPED_SUBRESOURCE pixelMap{};
        if (FAILED(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,&pixelMap)) ||
            !pixelMap.pData) return false;
        const auto* p = static_cast<const unsigned char*>(pixelMap.pData)
            +16*pixelMap.RowPitch+16*4;
        const bool matches = p[0]==r && p[1]==g && p[2]==b && p[3]==255;
        ctx->Unmap(staging.Get(),0);
        return matches;
    };
    ctx->OMSetBlendState(keepColorBlend.Get(),nullptr,
                         D3D11_DEFAULT_SAMPLE_MASK);
    require(singleEyeDepthReady(), "R214 R211 still accepts foreign OM blend");
    require(!exactOpaqueEyeReady(), "R214 reject stale nonopaque OM blend");
    ctx->ClearDepthStencilView(ownDsv.Get(),D3D11_CLEAR_DEPTH,1.f,0);
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    ctx->Draw(3,0);
    require(samplePixelEquals(0,0,0),
            "R214 real WARP Draw suppressed by retained blend");
    ctx->OMSetBlendState(nullptr,nullptr,D3D11_DEFAULT_SAMPLE_MASK);
    require(exactOpaqueEyeReady(), "R214 recover exact default OM blend");
    ctx->OMSetBlendState(nullptr,nullptr,0u);
    require(singleEyeDepthReady(), "R214 R211 still accepts zero sample mask");
    require(!exactOpaqueEyeReady(), "R214 reject zero live sample mask");
    ctx->ClearDepthStencilView(ownDsv.Get(),D3D11_CLEAR_DEPTH,1.f,0);
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    ctx->Draw(3,0);
    require(samplePixelEquals(0,0,0),
            "R214 real WARP Draw suppressed by zero mask");
    ctx->OMSetBlendState(nullptr,nullptr,D3D11_DEFAULT_SAMPLE_MASK);
    require(exactOpaqueEyeReady(), "R214 restore fully owned opaque OM state");
    ctx->ClearDepthStencilView(ownDsv.Get(),D3D11_CLEAR_DEPTH,1.f,0);
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    ctx->Draw(3,0);
    require(samplePixelEquals(255,0,0),
            "R214 real WARP Draw restored red pixel after OM repair");

    // R215: R214 alone accepts a half eye viewport or a foreign raster
    // state, even though both can invalidate an otherwise exact OM Draw.
    const auto sealedEyeReady = [&] {
        return outrun::vr::dx11::verified_linear_sealed_opaque_eye_draw_ready(
            vb,ctx.Get(),0,3,generation,version,32,32,
            DXGI_FORMAT_R8G8B8A8_UNORM,
            layout.Get(),vs.Get(),ps.Get(),rtv.Get(),
            ownDsv.Get(),depthState.Get(),rs.Get());
    };
    require(sealedEyeReady(), "R215 sealed opaque eye initial readiness");
    D3D11_VIEWPORT r215Half=vp;
    r215Half.Width=16.f;
    ctx->RSSetViewports(1,&r215Half);
    require(exactOpaqueEyeReady(), "R215 R214 admits retained half viewport");
    require(!sealedEyeReady(), "R215 reject half-eye viewport");
    ctx->ClearDepthStencilView(ownDsv.Get(),D3D11_CLEAR_DEPTH,1.f,0);
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    ctx->Draw(3,0);
    require(samplePixelEquals(0,0,0),
            "R215 real WARP half-viewport suppresses center pixel");
    ctx->RSSetViewports(1,&vp);
    require(sealedEyeReady(), "R215 full-eye viewport restored");
    D3D11_RASTERIZER_DESC foreignRasterDesc=raster;
    foreignRasterDesc.CullMode=D3D11_CULL_BACK;
    ComPtr<ID3D11RasterizerState> foreignRaster;
    require(SUCCEEDED(dev->CreateRasterizerState(
            &foreignRasterDesc,foreignRaster.GetAddressOf())),
            "R215 alternate same-device raster");
    ctx->RSSetState(foreignRaster.Get());
    require(exactOpaqueEyeReady(), "R215 R214 admits foreign raster");
    require(!sealedEyeReady(), "R215 reject foreign raster owner");
    ctx->RSSetState(rs.Get());
    require(sealedEyeReady(), "R215 exact raster object restored");
    ctx->ClearDepthStencilView(ownDsv.Get(),D3D11_CLEAR_DEPTH,1.f,0);
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    ctx->Draw(3,0);
    require(samplePixelEquals(255,0,0),
            "R215 real WARP restores full-eye red pixel");

    // R215: same-size depth view over mip 1 of a 64x64 resource is a
    // legitimate D3D11 OM attachment but not a dedicated 32x32 eye owner.
    // R214 sees an exact DSV *object* and admits this aliased resource.
    D3D11_TEXTURE2D_DESC mipDepthDesc=depthDesc;
    mipDepthDesc.Width=64;
    mipDepthDesc.Height=64;
    mipDepthDesc.MipLevels=2;
    ComPtr<ID3D11Texture2D> mipDepth;
    require(SUCCEEDED(dev->CreateTexture2D(
                &mipDepthDesc,nullptr,mipDepth.GetAddressOf())),
            "R215 create nonbase mip depth texture");
    D3D11_DEPTH_STENCIL_VIEW_DESC mipViewDesc{};
    mipViewDesc.Format=DXGI_FORMAT_D32_FLOAT;
    mipViewDesc.ViewDimension=D3D11_DSV_DIMENSION_TEXTURE2D;
    mipViewDesc.Texture2D.MipSlice=1;
    ComPtr<ID3D11DepthStencilView> mipDsv;
    require(SUCCEEDED(dev->CreateDepthStencilView(
                mipDepth.Get(),&mipViewDesc,mipDsv.GetAddressOf())),
            "R215 create nonbase mip depth view");
    ctx->OMSetRenderTargets(1,&rawRTV,mipDsv.Get());
    require(outrun::vr::dx11::verified_linear_opaque_single_eye_draw_ready(
                vb,ctx.Get(),0,3,generation,version,
                layout.Get(),vs.Get(),ps.Get(),rtv.Get(),
                mipDsv.Get(),depthState.Get()),
            "R215 R214 admits nonbase depth mip view");
    require(!outrun::vr::dx11::verified_linear_sealed_opaque_eye_draw_ready(
                vb,ctx.Get(),0,3,generation,version,32,32,
                DXGI_FORMAT_R8G8B8A8_UNORM,
                layout.Get(),vs.Get(),ps.Get(),rtv.Get(),
                mipDsv.Get(),depthState.Get(),rs.Get()),
            "R215 reject nonbase depth mip view");
    ctx->ClearDepthStencilView(mipDsv.Get(),D3D11_CLEAR_DEPTH,1.f,0);
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    ctx->Draw(3,0);
    require(samplePixelEquals(255,0,0),
            "R215 real WARP nonbase depth mip renders red");
    ctx->OMSetRenderTargets(1,&rawRTV,ownDsv.Get());
    require(sealedEyeReady(), "R215 original depth eye recovered");

    // R216: R215's DSV identity admits a dedicated same-size D16 depth
    // texture. A float32 precision contract must reject that legitimate
    // but lower-precision WARP OM attachment, then restore the owned D32 eye.
    const auto floatDepthEyeReady = [&](ID3D11DepthStencilView* candidate) {
        return outrun::vr::dx11::verified_linear_float_depth_eye_draw_ready(
            vb,ctx.Get(),0,3,generation,version,32,32,
            DXGI_FORMAT_R8G8B8A8_UNORM,
            layout.Get(),vs.Get(),ps.Get(),rtv.Get(),
            candidate,depthState.Get(),rs.Get());
    };
    require(floatDepthEyeReady(ownDsv.Get()),
            "R216 dedicated D32_FLOAT eye initially ready");
    D3D11_TEXTURE2D_DESC d16DepthDesc=depthDesc;
    d16DepthDesc.Format=DXGI_FORMAT_D16_UNORM;
    ComPtr<ID3D11Texture2D> d16Depth;
    ComPtr<ID3D11DepthStencilView> d16Dsv;
    require(SUCCEEDED(dev->CreateTexture2D(
                &d16DepthDesc,nullptr,d16Depth.GetAddressOf())),
            "R216 create dedicated D16 depth texture");
    require(SUCCEEDED(dev->CreateDepthStencilView(
                d16Depth.Get(),nullptr,d16Dsv.GetAddressOf())),
            "R216 create same-size D16 depth view");
    ctx->OMSetRenderTargets(1,&rawRTV,d16Dsv.Get());
    require(outrun::vr::dx11::verified_linear_sealed_opaque_eye_draw_ready(
                vb,ctx.Get(),0,3,generation,version,32,32,
                DXGI_FORMAT_R8G8B8A8_UNORM,
                layout.Get(),vs.Get(),ps.Get(),rtv.Get(),
                d16Dsv.Get(),depthState.Get(),rs.Get()),
            "R216 R215 admits valid lower-precision D16 eye");
    require(!floatDepthEyeReady(d16Dsv.Get()),
            "R216 reject D16 eye masquerading as float depth");
    ctx->ClearDepthStencilView(d16Dsv.Get(),D3D11_CLEAR_DEPTH,1.f,0);
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    ctx->Draw(3,0);
    require(samplePixelEquals(255,0,0),
            "R216 real WARP D16 Draw succeeds but is not D32 precision");
    ctx->OMSetRenderTargets(1,&rawRTV,ownDsv.Get());
    require(floatDepthEyeReady(ownDsv.Get()),
            "R216 exact original D32_FLOAT eye restored");
    ctx->ClearDepthStencilView(ownDsv.Get(),D3D11_CLEAR_DEPTH,1.f,0);
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    ctx->Draw(3,0);
    require(samplePixelEquals(255,0,0),
            "R216 real WARP restored D32 eye draws red");
    // R221: an exact linear D32 eye can still write a retained second-eye UAV.
    const auto isolatedLinearReady = [&] {
        return outrun::vr::dx11::verified_linear_uav_isolated_eye_ready(
            vb,ctx.Get(),0,3,generation,version,32,32,
            DXGI_FORMAT_R8G8B8A8_UNORM,
            layout.Get(),vs.Get(),ps.Get(),rtv.Get(),
            ownDsv.Get(),depthState.Get(),rs.Get());
    };
    require(isolatedLinearReady(), "R221 isolated linear eye initial");
    require(!outrun::vr::dx11::verified_linear_uav_isolated_eye_ready(
            vb,ctx.Get(),0,3,generation,version,32,32,
            DXGI_FORMAT_R8G8B8A8_UNORM,
            layout.Get(),vs.Get(),ps.Get(),rtv.Get(),
            nullptr,depthState.Get(),rs.Get()),
            "R221 rejects missing DSV owner");
    D3D11_TEXTURE2D_DESC eyeDesc{};
    eyeDesc.Width=32; eyeDesc.Height=32; eyeDesc.MipLevels=1;
    eyeDesc.ArraySize=1; eyeDesc.SampleDesc.Count=1;
    eyeDesc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;
    eyeDesc.Usage=D3D11_USAGE_DEFAULT;
    eyeDesc.BindFlags=D3D11_BIND_UNORDERED_ACCESS;
    ComPtr<ID3D11Texture2D> sideEye, sideRead;
    ComPtr<ID3D11UnorderedAccessView> sideUav;
    require(SUCCEEDED(dev->CreateTexture2D(
        &eyeDesc,nullptr,sideEye.GetAddressOf())), "R221 UAV texture");
    require(SUCCEEDED(dev->CreateUnorderedAccessView(
        sideEye.Get(),nullptr,sideUav.GetAddressOf())), "R221 UAV view");
    eyeDesc.Usage=D3D11_USAGE_STAGING; eyeDesc.BindFlags=0;
    eyeDesc.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
    require(SUCCEEDED(dev->CreateTexture2D(
        &eyeDesc,nullptr,sideRead.GetAddressOf())), "R221 UAV readback");
    ID3D11UnorderedAccessView* rawSide=sideUav.Get();
    ctx->OMSetRenderTargetsAndUnorderedAccessViews(
        1,&rawRTV,ownDsv.Get(),1,1,&rawSide,nullptr);
    require(floatDepthEyeReady(ownDsv.Get()),
        "R221 old R216 admits hidden OM UAV");
    require(!isolatedLinearReady(), "R221 rejects hidden OM UAV");

    // WARP negative proof: a real pixel shader writes GREEN into side eye.
    constexpr char sideShader[] =
        "RWTexture2D<float4> eye:register(u1);"
        "float4 psSide(float4 p:SV_Position):SV_Target{"
        "eye[uint2(p.xy)]=float4(0,1,0,1);return float4(1,0,0,1);}";
    ComPtr<ID3DBlob> sideCode;
    require(SUCCEEDED(D3DCompile(sideShader,sizeof(sideShader)-1,
        nullptr,nullptr,nullptr,"psSide","ps_5_0",0,0,
        sideCode.GetAddressOf(),nullptr)), "R221 compile UAV pixel shader");
    ComPtr<ID3D11PixelShader> sidePs;
    require(SUCCEEDED(dev->CreatePixelShader(
        sideCode->GetBufferPointer(),sideCode->GetBufferSize(),
        nullptr,sidePs.GetAddressOf())), "R221 create UAV pixel shader");
    const float zeroSide[]={0,0,0,1};
    ctx->ClearUnorderedAccessViewFloat(sideUav.Get(),zeroSide);
    ctx->ClearDepthStencilView(ownDsv.Get(),D3D11_CLEAR_DEPTH,1.f,0);
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    ctx->PSSetShader(sidePs.Get(),nullptr,0);
    ctx->Draw(3,0);
    ctx->CopyResource(sideRead.Get(),sideEye.Get());
    D3D11_MAPPED_SUBRESOURCE sideMap{};
    require(SUCCEEDED(ctx->Map(
        sideRead.Get(),0,D3D11_MAP_READ,0,&sideMap)) && sideMap.pData,
        "R221 map WARP second eye");
    const auto* green=static_cast<const unsigned char*>(sideMap.pData)
        +16*sideMap.RowPitch+16*4;
    const bool leak=green[0]==0 && green[1]==255 &&
        green[2]==0 && green[3]==255;
    ctx->Unmap(sideRead.Get(),0);
    require(leak, "R221 WARP second-eye UAV pixel write");
    ctx->PSSetShader(ps.Get(),nullptr,0);
    ctx->OMSetRenderTargets(1,&rawRTV,ownDsv.Get());
    require(isolatedLinearReady(), "R221 isolation recovered");
    ctx->ClearDepthStencilView(ownDsv.Get(),D3D11_CLEAR_DEPTH,1.f,0);
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    ctx->Draw(3,0);
    require(samplePixelEquals(255,0,0), "R221 WARP red eye recovered");

    // R230: isolate non-indexed Draw from any live GPU predication. The
    // unpredicated recovery performs a real WARP pixel write/readback.
    const auto r230Ready = [&] {
        return outrun::vr::dx11::verified_linear_unpredicated_eye_ready(
            vb, ctx.Get(), 0u, 3u, generation, version,
            32u, 32u, DXGI_FORMAT_R8G8B8A8_UNORM,
            layout.Get(), vs.Get(), ps.Get(), rtv.Get(),
            ownDsv.Get(), depthState.Get(), rs.Get());
    };
    require(r230Ready(), "R230 initial unpredicated linear eye");
    D3D11_QUERY_DESC r230Query{};
    r230Query.Query = D3D11_QUERY_OCCLUSION_PREDICATE;
    ComPtr<ID3D11Predicate> r230Predicate;
    require(SUCCEEDED(dev->CreatePredicate(&r230Query,
        r230Predicate.GetAddressOf())), "R230 same-device predicate object");
    ctx->SetPredication(r230Predicate.Get(), FALSE);
    require(isolatedLinearReady(), "R230 predecessor accepts active predicate");
    require(!r230Ready(), "R230 reject false-polarity predication");
    ctx->SetPredication(r230Predicate.Get(), TRUE);
    require(!r230Ready(), "R230 reject true-polarity predication");
    ctx->SetPredication(nullptr, FALSE);
    require(r230Ready(), "R230 restore unpredicated linear eye");
    ctx->ClearDepthStencilView(ownDsv.Get(), D3D11_CLEAR_DEPTH, 1.f, 0);
    ctx->ClearRenderTargetView(rtv.Get(), clear);
    ctx->Draw(3u, 0u);
    require(samplePixelEquals(255,0,0),
        "R230 restored WARP Draw paints red eye pixel");

    // R232: all four Stream Output slots are potential GPU write sinks
    // outside the owned eye. Compare predecessor, negative SO slots and
    // restored real WARP Draw, without enabling the game native path.
    const auto r232Ready = [&] {
        return outrun::vr::dx11::verified_linear_no_stream_output_eye_ready(
            vb, ctx.Get(), 0u, 3u, generation, version,
            32u, 32u, DXGI_FORMAT_R8G8B8A8_UNORM,
            layout.Get(), vs.Get(), ps.Get(), rtv.Get(),
            ownDsv.Get(), depthState.Get(), rs.Get());
    };
    require(r232Ready(), "R232 initial clean linear eye");
    D3D11_BUFFER_DESC r232BufferDesc{};
    r232BufferDesc.ByteWidth = 64u;
    r232BufferDesc.Usage = D3D11_USAGE_DEFAULT;
    r232BufferDesc.BindFlags = D3D11_BIND_STREAM_OUTPUT;
    ComPtr<ID3D11Buffer> r232SoBuffer;
    require(SUCCEEDED(dev->CreateBuffer(
        &r232BufferDesc, nullptr, r232SoBuffer.GetAddressOf())) && r232SoBuffer,
        "R232 same-device stream-output buffer");
    ID3D11Buffer* r232Slot0 = r232SoBuffer.Get();
    UINT r232Offsets[D3D11_SO_BUFFER_SLOT_COUNT]{};
    ctx->SOSetTargets(1u, &r232Slot0, r232Offsets);
    require(r230Ready(), "R232 predecessor ignores SO target");
    require(!r232Ready(), "R232 reject slot-zero stream-output");
    ID3D11Buffer* r232Slot3[D3D11_SO_BUFFER_SLOT_COUNT]{
        nullptr, nullptr, nullptr, r232SoBuffer.Get()};
    ctx->SOSetTargets(D3D11_SO_BUFFER_SLOT_COUNT, r232Slot3, r232Offsets);
    require(!r232Ready(), "R232 reject highest stream-output slot");
    ctx->SOSetTargets(0u, nullptr, nullptr);
    require(r232Ready(), "R232 restore after SO unbind");
    ctx->ClearDepthStencilView(ownDsv.Get(), D3D11_CLEAR_DEPTH, 1.f, 0);
    ctx->ClearRenderTargetView(rtv.Get(), clear);
    ctx->Draw(3u, 0u);
    require(samplePixelEquals(255,0,0),
        "R232 restored WARP Draw paints red eye pixel");






    require(!outrun::vr::dx11::verified_linear_depth_om_identity_ready(
            vb,ctx.Get(),0,3,generation,version,
            layout.Get(),vs.Get(),ps.Get(),rtv.Get(),
            nullptr,depthState.Get()), "R210 reject absent DSV owner");
    ctx->ClearDepthStencilView(ownDsv.Get(),D3D11_CLEAR_DEPTH,1.f,0);
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    ctx->Draw(3,0);
    ctx->CopyResource(staging.Get(),color.Get());
    D3D11_MAPPED_SUBRESOURCE ownedDepthMap{};
    require(SUCCEEDED(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,
            &ownedDepthMap)) && ownedDepthMap.pData,
            "R210 map owned-depth WARP pixels");
    const auto* ownedDepthPixel =
        static_cast<const unsigned char*>(ownedDepthMap.pData)
        +16*ownedDepthMap.RowPitch+16*4;
    const bool ownedDepthRed=ownedDepthPixel[0]==255 &&
        ownedDepthPixel[1]==0 && ownedDepthPixel[2]==0 &&
        ownedDepthPixel[3]==255;
    ctx->Unmap(staging.Get(),0);
    require(ownedDepthRed, "R210 owned depth passes real WARP red pixel");

    ctx->OMSetRenderTargets(1,&rawRTV,foreignDsv.Get());
    ctx->ClearDepthStencilView(foreignDsv.Get(),D3D11_CLEAR_DEPTH,0.f,0);
    require(exactLinearReady(), "R210 R209 accepts foreign same-device DSV");
    require(!exactDepthReady(), "R210 reject foreign live OM DSV");
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    ctx->Draw(3,0);
    ctx->CopyResource(staging.Get(),color.Get());
    D3D11_MAPPED_SUBRESOURCE foreignDepthMap{};
    require(SUCCEEDED(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,
            &foreignDepthMap)) && foreignDepthMap.pData,
            "R210 map alien-depth WARP pixels");
    const auto* foreignDepthPixel =
        static_cast<const unsigned char*>(foreignDepthMap.pData)
        +16*foreignDepthMap.RowPitch+16*4;
    const bool foreignDepthBlack=foreignDepthPixel[0]==0 &&
        foreignDepthPixel[1]==0 && foreignDepthPixel[2]==0 &&
        foreignDepthPixel[3]==255;
    ctx->Unmap(staging.Get(),0);
    require(foreignDepthBlack, "R210 alien DSV suppresses real WARP pixel");

    ctx->OMSetRenderTargets(1,&rawRTV,ownDsv.Get());
    ctx->OMSetDepthStencilState(nullptr,0);
    require(!exactDepthReady(), "R210 reject unowned depth state");
    ctx->OMSetDepthStencilState(depthState.Get(),1);
    require(!exactDepthReady(), "R210 reject different stencil reference");
    ctx->OMSetDepthStencilState(depthState.Get(),0);
    depthStateDesc.DepthFunc=D3D11_COMPARISON_ALWAYS;
    require(SUCCEEDED(dev->CreateDepthStencilState(&depthStateDesc,
            alienDepthState.GetAddressOf())), "R210 alien depth state");
    ctx->OMSetDepthStencilState(alienDepthState.Get(),0);
    require(!exactDepthReady(), "R210 reject different depth state object");
    ctx->OMSetDepthStencilState(depthState.Get(),0);
    require(exactDepthReady(), "R210 restore exact depth-state identity");
    ctx->ClearDepthStencilView(ownDsv.Get(),D3D11_CLEAR_DEPTH,1.f,0);
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    ctx->Draw(3,0);
    ctx->CopyResource(staging.Get(),color.Get());
    D3D11_MAPPED_SUBRESOURCE restoreDepthMap{};
    require(SUCCEEDED(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,
            &restoreDepthMap)) && restoreDepthMap.pData,
            "R210 map restored-depth WARP pixels");
    const auto* restoreDepthPixel =
        static_cast<const unsigned char*>(restoreDepthMap.pData)
        +16*restoreDepthMap.RowPitch+16*4;
    const bool restoredDepthRed=restoreDepthPixel[0]==255 &&
        restoreDepthPixel[1]==0 && restoreDepthPixel[2]==0 &&
        restoreDepthPixel[3]==255;
    ctx->Unmap(staging.Get(),0);
    require(restoredDepthRed, "R210 recovered owned DSV WARP red pixel");
    ctx->OMSetRenderTargets(1,&rawRTV,nullptr);
    ctx->OMSetDepthStencilState(nullptr,0);

    // R199 independent non-indexed RTV/viewport ownership contract.
    const auto fullTargetReady = [&] {
        return outrun::vr::dx11::verified_linear_full_target_draw_ready(
            vb,ctx.Get(),0,3,generation,version,32,32,
            DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get());
    };
    require(fullTargetReady(), "R199 owned full linear target ready");
    require(!outrun::vr::dx11::verified_linear_full_target_draw_ready(
            vb,ctx.Get(),0,3,generation,version,32,32,
            DXGI_FORMAT_R8G8B8A8_UNORM,nullptr),
            "R199 reject null expected target");
    require(!outrun::vr::dx11::verified_linear_full_target_draw_ready(
            vb,ctx.Get(),0,3,generation,version,33,32,
            DXGI_FORMAT_R8G8B8A8_UNORM,rtv.Get()),
            "R199 reject wrong target width");
    require(!outrun::vr::dx11::verified_linear_full_target_draw_ready(
            vb,ctx.Get(),0,3,generation,version,32,32,
            DXGI_FORMAT_R8G8B8A8_UNORM_SRGB,rtv.Get()),
            "R199 reject wrong target format");

    // Same device, same dimensions and format: only RTV identity differs.
    D3D11_TEXTURE2D_DESC wrongDesc{};
    color->GetDesc(&wrongDesc);
    ComPtr<ID3D11Texture2D> wrongEyeColor;
    ComPtr<ID3D11RenderTargetView> wrongEyeRtv;
    require(SUCCEEDED(dev->CreateTexture2D(&wrongDesc,nullptr,
            wrongEyeColor.GetAddressOf())), "R199 create alternate-eye target");
    require(SUCCEEDED(dev->CreateRenderTargetView(wrongEyeColor.Get(),nullptr,
            wrongEyeRtv.GetAddressOf())), "R199 create alternate-eye RTV");
    ID3D11RenderTargetView* wrongEyeRaw=wrongEyeRtv.Get();
    ctx->OMSetRenderTargets(1,&wrongEyeRaw,nullptr);
    require(!fullTargetReady(), "R199 reject different-eye RTV");
    require(verified_linear_draw_ready(vb,ctx.Get(),0,3,generation,version),
            "R209 base readiness admits alien same-device eye RTV");
    require(!exactLinearReady(), "R209 reject alien same-device RTV");
    ctx->OMSetRenderTargets(1,&rawRTV,nullptr);
    require(fullTargetReady(), "R199 recover original eye RTV");
    require(exactLinearReady(), "R209 restore original eye RTV identity");

    // R224: typed RTV view over a same-device TYPELESS color allocation
    // previously satisfied format/identity checks despite an alias-capable
    // backing resource. The actual WARP OM binding exercises this state.
    D3D11_TEXTURE2D_DESC r224Backing{};
    color->GetDesc(&r224Backing);
    r224Backing.Format = DXGI_FORMAT_R8G8B8A8_TYPELESS;
    ComPtr<ID3D11Texture2D> r224Typeless;
    require(SUCCEEDED(dev->CreateTexture2D(&r224Backing,nullptr,
            r224Typeless.GetAddressOf())) && r224Typeless,
            "R224 create same-device typeless color resource");
    D3D11_RENDER_TARGET_VIEW_DESC r224TypedView{};
    rtv->GetDesc(&r224TypedView);
    ComPtr<ID3D11RenderTargetView> r224TypedRtv;
    require(SUCCEEDED(dev->CreateRenderTargetView(
            r224Typeless.Get(), &r224TypedView,
            r224TypedRtv.GetAddressOf())) && r224TypedRtv,
            "R224 typed RTV over typeless color resource");
    ID3D11RenderTargetView* r224Raw = r224TypedRtv.Get();
    ctx->OMSetRenderTargets(1,&r224Raw,nullptr);
    require(verified_linear_draw_ready(vb,ctx.Get(),0,3,generation,version),
            "R224 IA baseline admits typed view of typeless resource");
    require(!outrun::vr::dx11::verified_linear_full_target_draw_ready(
            vb,ctx.Get(),0,3,generation,version,32,32,
            DXGI_FORMAT_R8G8B8A8_UNORM,r224TypedRtv.Get()),
            "R224 reject typeless backing resource despite typed exact RTV");
    ctx->OMSetRenderTargets(1,&rawRTV,nullptr);
    require(fullTargetReady(), "R224 restore exact typed single-eye color resource");

    ctx->RSSetViewports(0,nullptr);
    require(!fullTargetReady(), "R199 reject missing viewport");
    const D3D11_VIEWPORT doubleViewports[]={vp,vp};
    ctx->RSSetViewports(2,doubleViewports);
    require(!fullTargetReady(), "R199 reject extra viewport");

    // The raw Draw incorrectly passed R185 readiness with a half viewport.
    // Real WARP output must now be black at the full eye's center.
    D3D11_VIEWPORT halfVp=vp;
    halfVp.Width=16.f;
    ctx->RSSetViewports(1,&halfVp);
    require(verified_linear_draw_ready(vb,ctx.Get(),0,3,generation,version),
            "R199 negative: old IA/pipeline alone accepts half viewport");
    require(!fullTargetReady(), "R199 reject half viewport");
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    ctx->Draw(3,0);
    ctx->CopyResource(staging.Get(),color.Get());
    D3D11_MAPPED_SUBRESOURCE halfMap{};
    require(SUCCEEDED(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,&halfMap))
            && halfMap.pData, "R199 map half-viewport WARP pixels");
    const auto* halfCenter=static_cast<const unsigned char*>(halfMap.pData)
        +16*halfMap.RowPitch+16*4;
    const bool halfCenterBlack=halfCenter[0]==0 && halfCenter[1]==0 &&
        halfCenter[2]==0 && halfCenter[3]==255;
    ctx->Unmap(staging.Get(),0);
    require(halfCenterBlack, "R199 half viewport suppresses WARP center pixel");
    ctx->RSSetViewports(1,&vp);
    require(fullTargetReady(), "R199 restore full viewport");

    D3D11_RASTERIZER_DESC scissorDesc{};
    rs->GetDesc(&scissorDesc);
    scissorDesc.ScissorEnable=TRUE;
    ComPtr<ID3D11RasterizerState> scissorState;
    require(SUCCEEDED(dev->CreateRasterizerState(
            &scissorDesc,scissorState.GetAddressOf())),
            "R199 create scissor rasterizer");
    ctx->RSSetState(scissorState.Get());
    require(!fullTargetReady(), "R199 reject scissor-enabled rasterizer");
    ctx->RSSetState(rs.Get());
    require(fullTargetReady(), "R199 restore full RTV/viewport/scissor");
    ctx->ClearRenderTargetView(rtv.Get(),clear);

    // R197: a retained Geometry Shader moves the actual non-indexed
    // triangle outside clip space while IA/VS/PS/RTV stay unchanged.
    constexpr char interferingGeometry[] =
        "struct V {float4 p:SV_Position;};"
        "[maxvertexcount(3)]"
        "void gs(triangle V tri[3],inout TriangleStream<V> stream){"
        "for(uint i=0;i<3;++i){V v=tri[i];v.p.xy=float2(2,2);stream.Append(v);}}";
    ComPtr<ID3DBlob> gsCode;
    require(SUCCEEDED(D3DCompile(interferingGeometry,
            sizeof(interferingGeometry)-1, nullptr, nullptr, nullptr,
            "gs", "gs_4_0", 0, 0, gsCode.GetAddressOf(), nullptr)),
            "R197 compile interfering GS");
    ComPtr<ID3D11GeometryShader> interferingGs;
    require(SUCCEEDED(dev->CreateGeometryShader(gsCode->GetBufferPointer(),
            gsCode->GetBufferSize(), nullptr, interferingGs.GetAddressOf())),
            "R197 create interfering GS");
    ctx->GSSetShader(interferingGs.Get(),nullptr,0);
    require(!verified_linear_draw_ready(vb,ctx.Get(),0,3,generation,version),
            "R197 reject unexpected non-indexed GS");
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    // Isolated negative proof: the same raw GPU Draw now outputs black.
    ctx->Draw(3,0);
    ctx->CopyResource(staging.Get(),color.Get());
    D3D11_MAPPED_SUBRESOURCE gsMapped{};
    require(SUCCEEDED(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,&gsMapped))
            && gsMapped.pData, "R197 read GS-suppressed WARP pixels");
    const auto* gsPixels = static_cast<const unsigned char*>(gsMapped.pData)
        +16*gsMapped.RowPitch+16*4;
    const bool gsBlack=gsPixels[0]==0 && gsPixels[1]==0 &&
        gsPixels[2]==0 && gsPixels[3]==255;
    ctx->Unmap(staging.Get(),0);
    require(gsBlack, "R197 GS changes actual WARP Draw pixels");
    ctx->GSSetShader(nullptr,nullptr,0);
    require(verified_linear_draw_ready(vb,ctx.Get(),0,3,generation,version),
            "R197 restore pure VS/PS native Draw");
    require(fullTargetReady(), "R199 final owned linear full target ready");
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    // The one actual native Draw remains isolated outside production DX11.
    ctx->Draw(3,0);
    ctx->CopyResource(staging.Get(),color.Get());
    D3D11_MAPPED_SUBRESOURCE linearMapped{};
    require(SUCCEEDED(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,&linearMapped)) &&
            linearMapped.pData, "R185 linear GPU staging readback");
    const auto* linearPixels=static_cast<const unsigned char*>(linearMapped.pData);
    const auto* linearCenter=linearPixels+16*linearMapped.RowPitch+16*4;
    const auto* linearCorner=linearPixels+1*linearMapped.RowPitch+1*4;
    const bool linearOk=linearCenter[0]==255 && linearCenter[1]==0 &&
        linearCenter[2]==0 && linearCenter[3]==255 &&
        linearCorner[0]==0 && linearCorner[1]==0 && linearCorner[2]==0;
    ctx->Unmap(staging.Get(),0);
    require(linearOk,"linear Draw GPU pixel readback");

    // R236: nonzero D3D9 DrawPrimitive start vertex -> owned mono WARP
    // Draw(3,3) pixel. The first triangle is off-screen intentionally.
    const Vertex r236Vertices[] = {
        {3.f,3.f},{3.f,4.f},{4.f,3.f},
        {-.9f,-.9f},{0.f,.9f},{.9f,-.9f}
    };
    constexpr std::uint64_t r236Version = 236;
    NativeLinearBufferMirror r236VB;
    require(r236VB.initialize(dev.Get(), outrun::vr::dx11::ResourceRole::Vertex,
            D3DPOOL_DEFAULT, D3DUSAGE_WRITEONLY, D3DFMT_UNKNOWN,
            r236Vertices, sizeof(r236Vertices), sizeof(Vertex),
            generation, r236Version), "R236 D3D9 source owns six vertices");
    require(r236VB.bind(ctx.Get(),generation,r236Version),
            "R236 D3D9 source VB native IA binding");
    ctx->IASetInputLayout(layout.Get());
    ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    ctx->VSSetShader(vs.Get(),nullptr,0);
    ctx->PSSetShader(ps.Get(),nullptr,0);
    ctx->RSSetState(rs.Get());
    ctx->RSSetViewports(1,&vp);
    ctx->OMSetRenderTargets(1,&rawRTV,nullptr);
    ctx->OMSetBlendState(nullptr,nullptr,D3D11_DEFAULT_SAMPLE_MASK);
    const auto r236Ready = [&](D3DPRIMITIVETYPE primitive, UINT first,
                               UINT count, std::uint64_t sourceVersion) {
        return outrun::vr::dx11::verified_d3d9_nonindexed_triangles_ready(
            r236VB, ctx.Get(), primitive, first, count, generation,
            sourceVersion, 32u, 32u, DXGI_FORMAT_R8G8B8A8_UNORM,
            layout.Get(), vs.Get(), ps.Get(), rtv.Get());
    };
    require(r236Ready(D3DPT_TRIANGLELIST,3u,1u,r236Version),
            "R236 valid nonzero D3D9 DrawPrimitive source command");
    require(!r236Ready(D3DPT_TRIANGLESTRIP,3u,1u,r236Version),
            "R236 reject non-triangle-list source topology");
    require(!r236Ready(D3DPT_TRIANGLELIST,3u,0u,r236Version),
            "R236 reject empty D3D9 primitive command");
    require(!r236Ready(D3DPT_TRIANGLELIST,4u,1u,r236Version),
            "R236 reject D3D9 source VB overrun");
    require(!r236Ready(D3DPT_TRIANGLELIST,3u,0xffffffffu,r236Version),
            "R236 reject D3D9 primitive overflow");
    require(!r236Ready(D3DPT_TRIANGLELIST,3u,1u,r236Version+1u),
            "R236 reject stale source version");
    ctx->PSSetShader(nullptr,nullptr,0);
    require(!r236Ready(D3DPT_TRIANGLELIST,3u,1u,r236Version),
            "R236 reject missing native PS");
    ctx->PSSetShader(ps.Get(),nullptr,0);
    ID3D11RenderTargetView* r236TwoEyes[] = {rtv.Get(), secondEyeView.Get()};
    ctx->OMSetRenderTargets(2,r236TwoEyes,nullptr);
    require(!r236Ready(D3DPT_TRIANGLELIST,3u,1u,r236Version),
            "R236 reject foreign second eye");
    ctx->OMSetRenderTargets(1,&rawRTV,nullptr);
    require(r236Ready(D3DPT_TRIANGLELIST,3u,1u,r236Version),
            "R236 restore exact mono native pipeline");
    ctx->ClearRenderTargetView(rtv.Get(),clear);
    ctx->Draw(3u,0u);
    ctx->CopyResource(staging.Get(),color.Get());
    D3D11_MAPPED_SUBRESOURCE r236Offscreen{};
    require(SUCCEEDED(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,
            &r236Offscreen)) && r236Offscreen.pData,
            "R236 map offscreen source GPU pixel");
    const auto* r236Miss = static_cast<const unsigned char*>(
            r236Offscreen.pData)+16*r236Offscreen.RowPitch+16*4;
    const bool r236Black = r236Miss[0]==0 && r236Miss[1]==0 &&
                          r236Miss[2]==0 && r236Miss[3]==255;
    ctx->Unmap(staging.Get(),0);
    require(r236Black,"R236 first source triangle misses WARP eye");
    ctx->Draw(3u,3u);
    ctx->CopyResource(staging.Get(),color.Get());
    D3D11_MAPPED_SUBRESOURCE r236Mapped{};
    require(SUCCEEDED(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,
            &r236Mapped)) && r236Mapped.pData,
            "R236 map native DrawPrimitive WARP pixels");
    const auto* r236Pixels = static_cast<const unsigned char*>(r236Mapped.pData);
    const auto* r236Center = r236Pixels+16*r236Mapped.RowPitch+16*4;
    const auto* r236Corner = r236Pixels+1*r236Mapped.RowPitch+1*4;
    const bool r236Red = r236Center[0]==255 && r236Center[1]==0 &&
                         r236Center[2]==0 && r236Center[3]==255 &&
                         r236Corner[0]==0 && r236Corner[1]==0 &&
                         r236Corner[2]==0 && r236Corner[3]==255;
    ctx->Unmap(staging.Get(),0);
    require(r236Red,"R236 D3D9 DrawPrimitive -> WARP Draw(3,3) red pixel");
    r236VB.shutdown();
    require(!r236Ready(D3DPT_TRIANGLELIST,3u,1u,r236Version),
            "R236 reject released source VB ownership");

    ib.shutdown();
    require(!ib.binding_exact(ctx.Get(),generation,version),
            "retired index owner cannot validate stale IA object");
    vb.shutdown();
    require(!vb.bind(ctx.Get(),generation,version),
            "retired vertex owner cannot bind stale object");
    std::cout << "R183 live D3D11 VB/IB owner IA + GPU DrawIndexed WARP: PASS\n";
}
