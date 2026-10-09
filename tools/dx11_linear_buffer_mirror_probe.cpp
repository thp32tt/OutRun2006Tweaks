// R183: actual WARP DrawIndexed consumes production-owned VB and IB objects.
// No game draw hook, backend activation or Quest 3 runtime claim.
#include "vr/d3d11/native_linear_buffer_mirror.hpp"
#include "vr/d3d11/native_linear_draw_submit.hpp"
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
    ib.shutdown();
    require(!ib.binding_exact(ctx.Get(),generation,version),
            "retired index owner cannot validate stale IA object");
    vb.shutdown();
    require(!vb.bind(ctx.Get(),generation,version),
            "retired vertex owner cannot bind stale object");
    std::cout << "R183 live D3D11 VB/IB owner IA + GPU DrawIndexed WARP: PASS\n";
}
