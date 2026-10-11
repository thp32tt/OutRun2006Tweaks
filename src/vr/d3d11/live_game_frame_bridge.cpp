#include "live_game_frame_bridge.hpp"
#include "native_backend.hpp"
#include "packed_texture_16bit.hpp"

#include <Windows.h>
#include <d3dcompiler.h>
#include <wrl/client.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <mutex>
#include <vector>
#include <spdlog/spdlog.h>

namespace outrun::vr::dx11::live_game_frame {
namespace {
using Microsoft::WRL::ComPtr;
constexpr UINT kWidth = 256;
constexpr UINT kHeight = 144;
constexpr UINT kMaxVertices = 1536;
constexpr UINT kMaxIndices = 1536;
// Rotate among eligible game Draws so an off-screen first Draw cannot starve
// later visible candidates. Exactly one native submission is allowed per Present.
constexpr UINT kProbeSlots = 64;
constexpr UINT kReadbackSlots = 3; // GPU event-fenced frame copies

constexpr std::array<float, 4> kBackground{0.035f, 0.035f, 0.08f, 1.0f};
constexpr char kShader[] = R"(
struct VIn { float4 clip : POSITION; float4 diffuse : COLOR0; float2 uv : TEXCOORD0; };
struct VOut { float4 clip : SV_Position; float4 diffuse : COLOR0; float2 uv : TEXCOORD0; };
Texture2D gameTexture : register(t0);
SamplerState gameSampler : register(s0);
cbuffer AlphaParams : register(b0) { float4 alphaParams; };
// D3D9 alpha reference compares 8-bit post-texture alpha, not a raw
// floating-point value. Only the explicitly admitted compare funcs are used.
void AlphaGate(float alpha) {
    if (alphaParams.x > 0.5f) {
        float value = floor(saturate(alpha) * 255.0f + 0.5f);
        bool pass = (alphaParams.z == 5.0f && value > alphaParams.y) ||
                    (alphaParams.z == 7.0f && value >= alphaParams.y);
        clip(pass ? 1.0f : -1.0f);
    }
}
VOut VS(VIn v) { VOut o; o.clip = v.clip; o.diffuse = v.diffuse; o.uv = v.uv; return o; }
float4 PS(VOut v) : SV_Target { float4 c = v.diffuse; AlphaGate(c.a); return c; }
float4 PSTextured(VOut v) : SV_Target { float4 c = gameTexture.Sample(gameSampler, v.uv) * v.diffuse; AlphaGate(c.a); return c; }
float4 PSTextureOnly(VOut v) : SV_Target { float4 c = gameTexture.Sample(gameSampler, v.uv); AlphaGate(c.a); return c; }
)";
struct NativeVertex {
    float clip[4];
    float diffuse[4];
    float uv[2];
};

// Narrow fixed-function stage-0 textured subset for real game menu/vehicle/race
// draws. Any unmirrored texture, sampler, alpha or stage state fails closed.
struct TextureCapture {
    bool enabled = false;
    bool selectTexture = false;
    Microsoft::WRL::ComPtr<IDirect3DTexture9> texture;
    D3DTEXTUREADDRESS addressU = D3DTADDRESS_CLAMP;
    D3DTEXTUREADDRESS addressV = D3DTADDRESS_CLAMP;
    D3DTEXTUREFILTERTYPE filter = D3DTEXF_POINT;
};

struct OutputCapture {
    bool alphaBlend = false;
    bool alphaTest = false;
    DWORD alphaRef = 0;
    D3DCMPFUNC alphaFunc = D3DCMP_ALWAYS;
    bool scissor = false;
    D3D11_RECT nativeScissor{};
    // Only source RGB-visible masks are eligible for the diagnostic inset.
    std::uint8_t colorWriteMask = D3D11_COLOR_WRITE_ENABLE_ALL;
};

struct ReadbackSlot {
    ComPtr<ID3D11Texture2D> staging;
    ComPtr<ID3D11Query> fence;
    bool busy = false;
};
struct State {
    std::mutex mutex;
    NativeBackend backend;
    ComPtr<ID3D11VertexShader> vs;
    ComPtr<ID3D11PixelShader> ps;
    ComPtr<ID3D11PixelShader> sampledPs;
    ComPtr<ID3D11PixelShader> textureOnlyPs;
    ComPtr<ID3D11InputLayout> layout;
    ComPtr<ID3D11RasterizerState> raster;
    ComPtr<ID3D11RasterizerState> scissorRaster;
    ComPtr<ID3D11BlendState> alphaBlend;
    // Cached by source mask and alpha-blend mode; no per-frame state churn.
    std::array<ComPtr<ID3D11BlendState>, 32> maskedBlends{};
    ComPtr<ID3D11Buffer> alphaConstants;
    std::array<ReadbackSlot, kReadbackSlots> readbacks{};
    UINT readSlot = 0;
    UINT writeSlot = 0;
    UINT droppedCopies = 0;
    ComPtr<IDirect3DSurface9> insetSurface;
    D3DFORMAT insetFormat = D3DFMT_UNKNOWN;
    bool pending = false;
    bool attempted = false;
    bool logged = false;
    UINT observed = 0;
    std::uint64_t presents = 0;
    std::uint64_t eligible = 0;
    UINT eligibleThisFrame = 0;
    UINT probeSlot = 0;
    UINT issued = 0;
    UINT visible = 0;
    UINT failed = 0;
};
State& state() noexcept { static State s; return s; }

bool env_opt_in() noexcept {
    wchar_t value[8]{};
    // Exact opt-in only. No ini, default flag or runtime backend promotion.
    return GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME", value, 8) == 1
        && value[0] == L'1';
}

bool compile(const char* entry, const char* profile, ComPtr<ID3DBlob>& blob) noexcept {
    ComPtr<ID3DBlob> errors;
    return SUCCEEDED(D3DCompile(kShader, sizeof(kShader) - 1, "live_game_frame",
        nullptr, nullptr, entry, profile, D3DCOMPILE_ENABLE_STRICTNESS,
        0, blob.GetAddressOf(), errors.GetAddressOf())) && blob;
}

bool ensure_pipeline(State& s) noexcept {
    const bool readbackReady = std::all_of(s.readbacks.begin(), s.readbacks.end(),
        [](const ReadbackSlot& item) { return item.staging && item.fence; });
    if (s.backend.ready() && s.vs && s.ps && s.sampledPs && s.textureOnlyPs &&
        s.layout && s.raster && s.scissorRaster && s.alphaBlend &&
        s.alphaConstants && readbackReady)
        return true;
    s.backend.shutdown();
    s.vs.Reset(); s.ps.Reset(); s.sampledPs.Reset(); s.textureOnlyPs.Reset();
    s.layout.Reset(); s.raster.Reset(); s.scissorRaster.Reset();
    s.alphaBlend.Reset(); s.alphaConstants.Reset();
    for (auto& item : s.readbacks) {
        item.staging.Reset(); item.fence.Reset(); item.busy = false;
    }
    s.readSlot = s.writeSlot = 0;
    s.insetSurface.Reset(); s.insetFormat = D3DFMT_UNKNOWN;
    for (auto& masked : s.maskedBlends) masked.Reset();
    NativeBackendConfig cfg{};
    cfg.width = kWidth;
    cfg.height = kHeight;
    cfg.color_format = DXGI_FORMAT_B8G8R8A8_UNORM;
    if (!s.backend.initialize(cfg)) return false;
    auto* dev = s.backend.device();
    ComPtr<ID3DBlob> vcode, pcode, sampledCode, textureOnlyCode;
    if (!compile("VS", "vs_4_0", vcode) ||
        !compile("PS", "ps_4_0", pcode) ||
        !compile("PSTextured", "ps_4_0", sampledCode) ||
        !compile("PSTextureOnly", "ps_4_0", textureOnlyCode) ||
        FAILED(dev->CreateVertexShader(vcode->GetBufferPointer(), vcode->GetBufferSize(),
                                      nullptr, s.vs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(pcode->GetBufferPointer(), pcode->GetBufferSize(),
                                     nullptr, s.ps.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(sampledCode->GetBufferPointer(), sampledCode->GetBufferSize(),
                                     nullptr, s.sampledPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(textureOnlyCode->GetBufferPointer(), textureOnlyCode->GetBufferSize(),
                                     nullptr, s.textureOnlyPs.GetAddressOf())))
        return false;
    const D3D11_INPUT_ELEMENT_DESC elements[] = {
        {"POSITION", 0, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 0,
         D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"COLOR", 0, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 16,
         D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 0, DXGI_FORMAT_R32G32_FLOAT, 0, 32,
         D3D11_INPUT_PER_VERTEX_DATA, 0}
    };
    if (FAILED(dev->CreateInputLayout(elements, 3,
        vcode->GetBufferPointer(), vcode->GetBufferSize(), s.layout.GetAddressOf())))
        return false;
    D3D11_RASTERIZER_DESC raster{};
    raster.FillMode = D3D11_FILL_SOLID;
    raster.CullMode = D3D11_CULL_NONE;
    raster.DepthClipEnable = TRUE;
    if (FAILED(dev->CreateRasterizerState(&raster, s.raster.GetAddressOf())))
        return false;
    // Source D3D9 SCISSORTESTENABLE is a rasterization operation, not a
    // texture-stage effect. A separate RS state preserves the uncut path.
    raster.ScissorEnable = TRUE;
    if (FAILED(dev->CreateRasterizerState(&raster, s.scissorRaster.GetAddressOf())))
        return false;
    // Narrow D3D9 SRCALPHA/INVSRCALPHA/ADD, with the same factors
    // for destination alpha. This is a diagnostic target, not the game RT.
    D3D11_BLEND_DESC blend{};
    auto& target = blend.RenderTarget[0];
    target.BlendEnable = TRUE;
    target.SrcBlend = D3D11_BLEND_SRC_ALPHA;
    target.DestBlend = D3D11_BLEND_INV_SRC_ALPHA;
    target.BlendOp = D3D11_BLEND_OP_ADD;
    target.SrcBlendAlpha = D3D11_BLEND_SRC_ALPHA;
    target.DestBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;
    target.BlendOpAlpha = D3D11_BLEND_OP_ADD;
    target.RenderTargetWriteMask = D3D11_COLOR_WRITE_ENABLE_ALL;
    if (FAILED(dev->CreateBlendState(&blend, s.alphaBlend.GetAddressOf())))
        return false;
    D3D11_BUFFER_DESC constants{};
    constants.ByteWidth = sizeof(float) * 4u;
    constants.Usage = D3D11_USAGE_DEFAULT;
    constants.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
    if (FAILED(dev->CreateBuffer(&constants, nullptr, s.alphaConstants.GetAddressOf())))
        return false;
    D3D11_TEXTURE2D_DESC desc{};
    s.backend.color_texture()->GetDesc(&desc);
    desc.Usage = D3D11_USAGE_STAGING;
    desc.BindFlags = 0;
    desc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    desc.MiscFlags = 0;
    D3D11_QUERY_DESC query{};
    query.Query = D3D11_QUERY_EVENT;
    for (auto& item : s.readbacks) {
        if (FAILED(dev->CreateTexture2D(&desc, nullptr, item.staging.GetAddressOf())) ||
            FAILED(dev->CreateQuery(&query, item.fence.GetAddressOf())))
            return false;
    }
    return true;
}

// Read the current game device, not a WARP fixture's manufactured state.
// COM getters AddRef; local ComPtrs always release before reset/return.
bool supported_game_state(IDirect3DDevice9* game, D3DVIEWPORT9& viewport,
                          bool& pretransformed,
                          std::array<D3DMATRIX, 3>& transforms,
                          TextureCapture& capture, OutputCapture& output) noexcept {
    if (!game || FAILED(game->GetViewport(&viewport)) ||
        viewport.Width == 0 || viewport.Height == 0)
        return false;
    DWORD fvf = 0;
    if (FAILED(game->GetFVF(&fvf))) return false;
    // Real game fixed-function geometry: admit both pretransformed HUD/sprite
    // vertices and unlit object-space diffuse vertices. Other FVF layouts
    // (textures, normals, weights, shader declarations) remain DX9Ex-owned.
    const DWORD rhw = D3DFVF_XYZRHW | D3DFVF_DIFFUSE;
    const DWORD xyz = D3DFVF_XYZ | D3DFVF_DIFFUSE;
    pretransformed = (fvf == rhw || fvf == (rhw | D3DFVF_TEX1));
    capture.enabled = fvf == (rhw | D3DFVF_TEX1) ||
                      fvf == (xyz | D3DFVF_TEX1);
    if (!pretransformed && fvf != xyz && fvf != (xyz | D3DFVF_TEX1))
        return false;
    ComPtr<IDirect3DVertexShader9> vs;
    ComPtr<IDirect3DPixelShader9> ps;
    ComPtr<IDirect3DBaseTexture9> tex;
    if (FAILED(game->GetVertexShader(vs.GetAddressOf())) || vs ||
        FAILED(game->GetPixelShader(ps.GetAddressOf())) || ps ||
        FAILED(game->GetTexture(0, tex.GetAddressOf())))
        return false;

    // Only unblended, no-depth FVF diffuse or TEX1/modulate fixed-function
    // triangles are mirrored. The original D3D9 call always executes.
    if (capture.enabled) {
        if (!tex || tex->GetType() != D3DRTYPE_TEXTURE ||
            FAILED(tex.As(&capture.texture))) return false;
    } else if (tex) {
        // No texture source is consumed by the diffuse-only shader.
        return false;
    }
    DWORD blend=TRUE, alpha=TRUE, stencil=TRUE, depth=TRUE, clip=TRUE;
    DWORD fog=TRUE, scissor=TRUE;
    DWORD colorMask=0, cullMode=0, fillMode=0;
    // Keep the diagnostic raster conservative: no cull/fill/fog translation.
    // The source color-write channels are mirrored into the D3D11 OM blend
    // descriptor, never converted to an all-channel write by accident.
    // Scissoring is mirrored via RSSetScissorRects.
    if (FAILED(game->GetRenderState(D3DRS_ALPHABLENDENABLE, &blend)) ||
        FAILED(game->GetRenderState(D3DRS_ALPHATESTENABLE, &alpha)) ||
        FAILED(game->GetRenderState(D3DRS_STENCILENABLE, &stencil)) ||
        FAILED(game->GetRenderState(D3DRS_ZENABLE, &depth)) ||
        FAILED(game->GetRenderState(D3DRS_CLIPPING, &clip)) ||
        FAILED(game->GetRenderState(D3DRS_FOGENABLE, &fog)) ||
        FAILED(game->GetRenderState(D3DRS_SCISSORTESTENABLE, &scissor)) ||
        FAILED(game->GetRenderState(D3DRS_COLORWRITEENABLE, &colorMask)) ||
        FAILED(game->GetRenderState(D3DRS_CULLMODE, &cullMode)) ||
        FAILED(game->GetRenderState(D3DRS_FILLMODE, &fillMode)) ||
        stencil || depth || !clip || fog ||
        cullMode != D3DCULL_NONE || fillMode != D3DFILL_SOLID)
        return false;
    const DWORD legalMask = D3DCOLORWRITEENABLE_RED | D3DCOLORWRITEENABLE_GREEN |
                            D3DCOLORWRITEENABLE_BLUE | D3DCOLORWRITEENABLE_ALPHA;
    const DWORD visibleMask = D3DCOLORWRITEENABLE_RED | D3DCOLORWRITEENABLE_GREEN |
                              D3DCOLORWRITEENABLE_BLUE;
    // Zero, alpha-only and unknown bits cannot produce trustworthy RGB inset
    // evidence. D3D9 still draws those game primitives without interception.
    if ((colorMask & ~legalMask) || !(colorMask & visibleMask)) return false;
    output.colorWriteMask = static_cast<std::uint8_t>(
        ((colorMask & D3DCOLORWRITEENABLE_RED) ? D3D11_COLOR_WRITE_ENABLE_RED : 0u) |
        ((colorMask & D3DCOLORWRITEENABLE_GREEN) ? D3D11_COLOR_WRITE_ENABLE_GREEN : 0u) |
        ((colorMask & D3DCOLORWRITEENABLE_BLUE) ? D3D11_COLOR_WRITE_ENABLE_BLUE : 0u) |
        ((colorMask & D3DCOLORWRITEENABLE_ALPHA) ? D3D11_COLOR_WRITE_ENABLE_ALPHA : 0u));
    if (scissor) {
        RECT gameScissor{};
        if (FAILED(game->GetScissorRect(&gameScissor)) ||
            gameScissor.right <= gameScissor.left ||
            gameScissor.bottom <= gameScissor.top)
            return false;
        // D3D9 scissor is in source render-target pixel coordinates; native
        // vertices are remapped from source viewport to the 256x144 inset.
        // Intersect in signed 64-bit space so viewport X+Width cannot wrap.
        const std::int64_t left = (std::max)(
            static_cast<std::int64_t>(gameScissor.left),
            static_cast<std::int64_t>(viewport.X));
        const std::int64_t top = (std::max)(
            static_cast<std::int64_t>(gameScissor.top),
            static_cast<std::int64_t>(viewport.Y));
        const std::int64_t right = (std::min)(
            static_cast<std::int64_t>(gameScissor.right),
            static_cast<std::int64_t>(viewport.X) + viewport.Width);
        const std::int64_t bottom = (std::min)(
            static_cast<std::int64_t>(gameScissor.bottom),
            static_cast<std::int64_t>(viewport.Y) + viewport.Height);
        if (right <= left || bottom <= top) return false;
        // Clip inwards during diagnostic downsampling. A larger native
        // rectangle would draw pixels the original source scissor excluded.
        // This is conservative pixel sampling, not D3D9 screen parity proof.
        const LONG nativeLeft = static_cast<LONG>(std::ceil(
            static_cast<double>(left - viewport.X) * kWidth / viewport.Width));
        const LONG nativeTop = static_cast<LONG>(std::ceil(
            static_cast<double>(top - viewport.Y) * kHeight / viewport.Height));
        const LONG nativeRight = static_cast<LONG>(std::floor(
            static_cast<double>(right - viewport.X) * kWidth / viewport.Width));
        const LONG nativeBottom = static_cast<LONG>(std::floor(
            static_cast<double>(bottom - viewport.Y) * kHeight / viewport.Height));
        if (nativeRight <= nativeLeft || nativeBottom <= nativeTop)
            return false;
        output.scissor = true;
        output.nativeScissor = {nativeLeft, nativeTop, nativeRight, nativeBottom};
    }
    // D3D9 sprite/menu draw states. Reject alternate blend factors,
    // separate alpha, or alpha compare functions before any native draw.
    if (blend) {
        DWORD src = 0, dst = 0, blendOp = 0, separate = TRUE;
        if (FAILED(game->GetRenderState(D3DRS_SRCBLEND, &src)) ||
            FAILED(game->GetRenderState(D3DRS_DESTBLEND, &dst)) ||
            FAILED(game->GetRenderState(D3DRS_BLENDOP, &blendOp)) ||
            FAILED(game->GetRenderState(D3DRS_SEPARATEALPHABLENDENABLE, &separate)) ||
            src != D3DBLEND_SRCALPHA || dst != D3DBLEND_INVSRCALPHA ||
            blendOp != D3DBLENDOP_ADD || separate)
            return false;
        output.alphaBlend = true;
    }
    if (alpha) {
        DWORD func = 0, reference = ~0u;
        if (FAILED(game->GetRenderState(D3DRS_ALPHAFUNC, &func)) ||
            FAILED(game->GetRenderState(D3DRS_ALPHAREF, &reference)) ||
            (func != D3DCMP_GREATER && func != D3DCMP_GREATEREQUAL) ||
            reference > 255u)
            return false;
        output.alphaTest = true;
        output.alphaFunc = static_cast<D3DCMPFUNC>(func);
        output.alphaRef = reference;
    }
    DWORD op=0, arg=0, nextColorOp=0;
    // A later fixed-function texture stage can still change the result even
    // when stage 0 selects DIFFUSE. Reject it rather than mislabel an altered
    // game draw as native color parity; the original DX9Ex draw still runs.
    if (FAILED(game->GetTextureStageState(0, D3DTSS_COLOROP, &op)) ||
        FAILED(game->GetTextureStageState(0, D3DTSS_COLORARG1, &arg)) ||
        FAILED(game->GetTextureStageState(1, D3DTSS_COLOROP, &nextColorOp)) ||
        nextColorOp != D3DTOP_DISABLE)
        return false;
    if (!capture.enabled && (op != D3DTOP_SELECTARG1 || arg != D3DTA_DIFFUSE))
        return false;
    if (capture.enabled) {
        DWORD arg2=0, alphaOp=0, alphaArg1=0, alphaArg2=0;
        DWORD coordIndex=~0u, transformFlags=~0u;
        DWORD addressU=0, addressV=0, mag=0, min=0, mip=0, srgb=1;
        if (FAILED(game->GetTextureStageState(0, D3DTSS_COLORARG2, &arg2)) ||
            FAILED(game->GetTextureStageState(0, D3DTSS_ALPHAOP, &alphaOp)) ||
            FAILED(game->GetTextureStageState(0, D3DTSS_ALPHAARG1, &alphaArg1)) ||
            FAILED(game->GetTextureStageState(0, D3DTSS_ALPHAARG2, &alphaArg2)) ||
            FAILED(game->GetTextureStageState(0, D3DTSS_TEXCOORDINDEX, &coordIndex)) ||
            FAILED(game->GetTextureStageState(0, D3DTSS_TEXTURETRANSFORMFLAGS, &transformFlags)) ||
            FAILED(game->GetSamplerState(0, D3DSAMP_ADDRESSU, &addressU)) ||
            FAILED(game->GetSamplerState(0, D3DSAMP_ADDRESSV, &addressV)) ||
            FAILED(game->GetSamplerState(0, D3DSAMP_MAGFILTER, &mag)) ||
            FAILED(game->GetSamplerState(0, D3DSAMP_MINFILTER, &min)) ||
            FAILED(game->GetSamplerState(0, D3DSAMP_MIPFILTER, &mip)) ||
            FAILED(game->GetSamplerState(0, D3DSAMP_SRGBTEXTURE, &srgb)))
            return false;
        // Reject complement/alpha-replicate modifiers, projected or displaced
        // coordinates, gamma reads and mip/anisotropic paths we do not emulate.
        const bool modulate = op == D3DTOP_MODULATE && alphaOp == D3DTOP_MODULATE;
        const bool selectTexture = op == D3DTOP_SELECTARG1 && alphaOp == D3DTOP_SELECTARG1;
        // Preserve exact RGB/alpha semantics. Mixed operations are not yet
        // mirrored; inactive ARG2 is irrelevant for SELECTARG1.
        if ((!modulate && !selectTexture) || arg != D3DTA_TEXTURE ||
            alphaArg1 != D3DTA_TEXTURE ||
            (modulate && (arg2 != D3DTA_DIFFUSE || alphaArg2 != D3DTA_DIFFUSE)) ||
            coordIndex != 0 || transformFlags != D3DTTFF_DISABLE || srgb ||
            (addressU != D3DTADDRESS_WRAP && addressU != D3DTADDRESS_CLAMP) ||
            (addressV != D3DTADDRESS_WRAP && addressV != D3DTADDRESS_CLAMP) ||
            (mag != D3DTEXF_POINT && mag != D3DTEXF_LINEAR) ||
            min != mag || mip != D3DTEXF_NONE)
            return false;
        capture.addressU = static_cast<D3DTEXTUREADDRESS>(addressU);
        capture.addressV = static_cast<D3DTEXTUREADDRESS>(addressV);
        capture.filter = static_cast<D3DTEXTUREFILTERTYPE>(mag);
        capture.selectTexture = selectTexture;
    }
    // Custom clip planes are not implemented by the native shader. The
    // object-space path must also reject D3D9 lighting and vertex blending.
    DWORD clipPlanes = ~0u;
    if (FAILED(game->GetRenderState(D3DRS_CLIPPLANEENABLE, &clipPlanes)) ||
        clipPlanes != 0u)
        return false;
    if (!pretransformed) {
        DWORD lighting = TRUE, vertexBlend = ~0u;
        if (FAILED(game->GetRenderState(D3DRS_LIGHTING, &lighting)) ||
            FAILED(game->GetRenderState(D3DRS_VERTEXBLEND, &vertexBlend)) ||
            lighting || vertexBlend != D3DVBF_DISABLE ||
            FAILED(game->GetTransform(D3DTS_WORLD, &transforms[0])) ||
            FAILED(game->GetTransform(D3DTS_VIEW, &transforms[1])) ||
            FAILED(game->GetTransform(D3DTS_PROJECTION, &transforms[2])))
            return false;
    }
    return true;
}

bool translate_vertices(const void* input, UINT count, UINT stride,
                        const D3DVIEWPORT9& vp, bool pretransformed,
                        const std::array<D3DMATRIX, 3>& transforms,
                        const TextureCapture& capture,
                        std::vector<NativeVertex>& output) {
    const UINT diffuseOffset = pretransformed ? 16u : 12u;
    if (!input || stride < diffuseOffset + (capture.enabled ? 12u : 4u) || stride > 512u ||
        count == 0 || count > kMaxVertices)
        return false;
    output.resize(count);
    const auto* src = static_cast<const std::uint8_t*>(input);
    for (UINT i = 0; i < count; ++i) {
        float xyz[4]{0.0f, 0.0f, 0.0f, 1.0f};
        DWORD diffuse = 0;
        const auto* data = src + static_cast<std::size_t>(i) * stride;
        std::memcpy(xyz, data, diffuseOffset);
        std::memcpy(&diffuse, data + diffuseOffset, sizeof(diffuse));
        if (capture.enabled) {
            std::memcpy(output[i].uv, data + diffuseOffset + 4u,
                        sizeof(output[i].uv));
            if (!std::isfinite(output[i].uv[0]) ||
                !std::isfinite(output[i].uv[1])) return false;
        } else {
            output[i].uv[0] = output[i].uv[1] = 0.0f;
        }
        if (!std::isfinite(xyz[0]) || !std::isfinite(xyz[1]) ||
            !std::isfinite(xyz[2]) ||
            (pretransformed && (!std::isfinite(xyz[3]) || xyz[3] <= 0.0f)))
            return false;
        NativeVertex& v = output[i];
        if (pretransformed) {
            // D3D9 XYZRHW stores reciprocal homogeneous W. Preserve it for
            // perspective-correct UV interpolation instead of treating a menu
            // sprite with non-uniform RHW as an affine D3D11 triangle.
            const float w = 1.0f / xyz[3];
            if (!std::isfinite(w) || w <= 0.0f) return false;
            v.clip[0] = (2.0f * (xyz[0] - static_cast<float>(vp.X)) /
                        static_cast<float>(vp.Width) - 1.0f) * w;
            v.clip[1] = (1.0f - 2.0f * (xyz[1] - static_cast<float>(vp.Y)) /
                        static_cast<float>(vp.Height)) * w;
            v.clip[2] = xyz[2] * w;
            v.clip[3] = w;
        } else {
            // D3D9 fixed-function uses row vectors: position * World * View *
            // Projection. The result is D3D11 clip space as well (z in [0,w]).
            // Reject nonfinite/behind-camera vertices instead of fabricating
            // a positive GPU pixel while the real game draw is clipped.
            std::array<float, 4> clip{xyz[0], xyz[1], xyz[2], 1.0f};
            for (const auto& matrix : transforms) {
                std::array<float, 4> next{};
                for (UINT col = 0; col < 4; ++col)
                    for (UINT row = 0; row < 4; ++row)
                        next[col] += clip[row] * matrix.m[row][col];
                clip = next;
            }
            if (!std::isfinite(clip[0]) || !std::isfinite(clip[1]) ||
                !std::isfinite(clip[2]) || !std::isfinite(clip[3]) ||
                clip[3] <= 0.0f)
                return false;
            std::copy(clip.begin(), clip.end(), v.clip);
        }
        if (!std::isfinite(v.clip[0]) || !std::isfinite(v.clip[1]) ||
            !std::isfinite(v.clip[2]))
            return false;
        v.diffuse[0] = static_cast<float>((diffuse >> 16) & 255) / 255.0f;
        v.diffuse[1] = static_cast<float>((diffuse >> 8) & 255) / 255.0f;
        v.diffuse[2] = static_cast<float>(diffuse & 255) / 255.0f;
        v.diffuse[3] = static_cast<float>((diffuse >> 24) & 255) / 255.0f;
    }
    return true;
}

// Snapshot a live game texture's level 0 into a D3D11 sampleable resource.
// Managed/system-memory DXT1/3/5 are copied as BC1/2/3 blocks, not decoded
// or reinterpreted as BGRA pixels. Unsupported or GPU-only sources remain DX9Ex.
bool mirror_texture(ID3D11Device* dev, const TextureCapture& capture,
                    ComPtr<ID3D11ShaderResourceView>& view,
                    ComPtr<ID3D11SamplerState>& sampler) noexcept {
    if (!dev || !capture.enabled || !capture.texture ||
        capture.texture->GetLevelCount() == 0) return false;
    D3DSURFACE_DESC info{};
    if (FAILED(capture.texture->GetLevelDesc(0, &info)) ||
        info.Width == 0 || info.Height == 0 ||
        info.Width > 1024 || info.Height > 1024 ||
        info.Pool == D3DPOOL_DEFAULT)
        return false;

    // Both the producer's LockRect rows and D3D11's immutable subresource
    // pitch are in *compressed block bytes* for DXT. A BGRA pitch for BCn
    // silently corrupts the sampled menu/vehicle artwork.
    const bool compressed = info.Format == D3DFMT_DXT1 ||
                            info.Format == D3DFMT_DXT3 ||
                            info.Format == D3DFMT_DXT5;
    // Expand game-authored 16-bit packed texels into an immutable BGRA8
    // diagnostic SRV. D3D9 owns the source and continues its own Draw.
    const bool packed16 = info.Format == D3DFMT_R5G6B5 ||
                          info.Format == D3DFMT_A1R5G5B5 ||
                          info.Format == D3DFMT_A4R4G4B4;
    DXGI_FORMAT nativeFormat = DXGI_FORMAT_UNKNOWN;
    UINT rowBytes = 0, rows = 0;
    if (compressed) {
        // Level-0 BC resources must have full 4x4 blocks. Reject tiny or
        // partial blocks rather than relying on device-specific acceptance.
        if ((info.Width & 3u) || (info.Height & 3u)) return false;
        const UINT bytesPerBlock = info.Format == D3DFMT_DXT1 ? 8u : 16u;
        rowBytes = (info.Width / 4u) * bytesPerBlock;
        rows = info.Height / 4u;
        nativeFormat = info.Format == D3DFMT_DXT1 ? DXGI_FORMAT_BC1_UNORM :
                       info.Format == D3DFMT_DXT3 ? DXGI_FORMAT_BC2_UNORM :
                                                    DXGI_FORMAT_BC3_UNORM;
    } else if (info.Format == D3DFMT_A8R8G8B8 ||
               info.Format == D3DFMT_X8R8G8B8) {
        rowBytes = info.Width * 4u;
        rows = info.Height;
        nativeFormat = DXGI_FORMAT_B8G8R8A8_UNORM;
    } else if (packed16) {
        // D3D9 LockRect is 2 bytes/pixel, whereas DX11 BGRA8 upload is 4.
        rowBytes = info.Width * 2u;
        rows = info.Height;
        nativeFormat = DXGI_FORMAT_B8G8R8A8_UNORM;
    } else {
        return false;
    }

    D3DLOCKED_RECT locked{};
    if (FAILED(capture.texture->LockRect(0, &locked, nullptr, D3DLOCK_READONLY)))
        return false;
    bool ok = false;
    if (locked.pBits && locked.Pitch > 0 &&
        static_cast<UINT>(locked.Pitch) >= rowBytes) {
        const UINT uploadRowBytes = packed16 ? info.Width * 4u : rowBytes;
        const std::size_t sourceByteCount = static_cast<std::size_t>(rowBytes) * rows;
        std::vector<std::uint8_t> pixels(
            packed16 ? static_cast<std::size_t>(uploadRowBytes) * rows : sourceByteCount);
        const auto layout = info.Format == D3DFMT_R5G6B5 ?
            packed_texture16::Layout::rgb565 : info.Format == D3DFMT_A1R5G5B5 ?
            packed_texture16::Layout::argb1555 : packed_texture16::Layout::argb4444;
        for (UINT y = 0; y < rows; ++y) {
            const auto* source = static_cast<const std::uint8_t*>(locked.pBits) +
                                 static_cast<std::size_t>(y) * locked.Pitch;
            if (packed16) {
                packed_texture16::unpack_row(
                    source, pixels.data() + static_cast<std::size_t>(y) * uploadRowBytes,
                    info.Width, layout);
            } else {
                std::memcpy(pixels.data() + static_cast<std::size_t>(y) * rowBytes,
                            source, rowBytes);
            }
        }
        // D3DFMT_X8R8G8B8 alpha is undefined in D3D9; the native
        // texture-only and modulate pixel shaders must sample opaque alpha.
        if (info.Format == D3DFMT_X8R8G8B8)
            for (std::size_t x = 3; x < pixels.size(); x += 4)
                pixels[x] = 0xffu;
        D3D11_TEXTURE2D_DESC desc{};
        desc.Width = info.Width; desc.Height = info.Height;
        desc.MipLevels = 1; desc.ArraySize = 1;
        desc.Format = nativeFormat;
        desc.SampleDesc.Count = 1;
        desc.Usage = D3D11_USAGE_IMMUTABLE;
        desc.BindFlags = D3D11_BIND_SHADER_RESOURCE;
        D3D11_SUBRESOURCE_DATA initial{};
        initial.pSysMem = pixels.data();
        initial.SysMemPitch = rowBytes;
        if (packed16) initial.SysMemPitch = uploadRowBytes;
        ComPtr<ID3D11Texture2D> texture;
        if (SUCCEEDED(dev->CreateTexture2D(&desc, &initial, texture.GetAddressOf())) &&
            SUCCEEDED(dev->CreateShaderResourceView(texture.Get(), nullptr,
                                                   view.GetAddressOf()))) {
            D3D11_SAMPLER_DESC state{};
            state.Filter = capture.filter == D3DTEXF_LINEAR ?
                D3D11_FILTER_MIN_MAG_MIP_LINEAR : D3D11_FILTER_MIN_MAG_MIP_POINT;
            state.AddressU = capture.addressU == D3DTADDRESS_WRAP ?
                D3D11_TEXTURE_ADDRESS_WRAP : D3D11_TEXTURE_ADDRESS_CLAMP;
            state.AddressV = capture.addressV == D3DTADDRESS_WRAP ?
                D3D11_TEXTURE_ADDRESS_WRAP : D3D11_TEXTURE_ADDRESS_CLAMP;
            state.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
            // D3DSAMP_MIPFILTER=NONE always reads mip 0 even when the
            // source texture contains more mips; never sample unmirrored levels.
            state.MinLOD = 0.0f;
            state.MaxLOD = 0.0f;
            state.MaxAnisotropy = 1;
            state.ComparisonFunc = D3D11_COMPARISON_NEVER;
            ok = SUCCEEDED(dev->CreateSamplerState(&state, sampler.GetAddressOf()));
        }
    }
    capture.texture->UnlockRect(0);
    return ok;
}

bool submit(State& s, const std::vector<NativeVertex>& vertices,
            const std::uint32_t* indices, UINT indexCount,
            const TextureCapture& capture, const OutputCapture& output) noexcept {
    if (!ensure_pipeline(s)) return false;
    auto* dev = s.backend.device();
    auto* ctx = s.backend.context();
    if (!dev || !ctx) return false;
    ComPtr<ID3D11ShaderResourceView> sampledView;
    ComPtr<ID3D11SamplerState> sampledSampler;
    if (capture.enabled &&
        !mirror_texture(dev, capture, sampledView, sampledSampler)) return false;
    D3D11_BUFFER_DESC bd{};
    bd.ByteWidth = static_cast<UINT>(vertices.size() * sizeof(NativeVertex));
    bd.BindFlags = D3D11_BIND_VERTEX_BUFFER;
    bd.Usage = D3D11_USAGE_IMMUTABLE;
    D3D11_SUBRESOURCE_DATA initial{};
    initial.pSysMem = vertices.data();
    ComPtr<ID3D11Buffer> vb;
    if (FAILED(dev->CreateBuffer(&bd, &initial, vb.GetAddressOf()))) return false;
    ComPtr<ID3D11Buffer> ib;
    if (indices && indexCount) {
        bd.ByteWidth = indexCount * sizeof(std::uint32_t);
        bd.BindFlags = D3D11_BIND_INDEX_BUFFER;
        initial.pSysMem = indices;
        if (FAILED(dev->CreateBuffer(&bd, &initial, ib.GetAddressOf()))) return false;
    }

    // Pixel shader alpha test and OM alpha blend are bound to this same
    // source draw; unsupported D3D9 combinations were rejected above.
    const float alphaParams[4] = {
        output.alphaTest ? 1.0f : 0.0f,
        static_cast<float>(output.alphaRef),
        static_cast<float>(output.alphaFunc), 0.0f
    };
    // D3D11 default OM state writes all channels. Even when blending is off,
    // a partial D3D9 COLORWRITEENABLE requires a real blend-state object.
    // Copy the validated alpha blend descriptor rather than approximating
    // its RGB/alpha factors in a second path.
    ComPtr<ID3D11BlendState>* maskedBlend = nullptr;
    if (output.colorWriteMask != D3D11_COLOR_WRITE_ENABLE_ALL) {
        const UINT slot = (output.alphaBlend ? 16u : 0u) + output.colorWriteMask;
        if (slot >= s.maskedBlends.size()) return false;
        auto& cached = s.maskedBlends[slot];
        if (!cached) {
            D3D11_BLEND_DESC maskDesc{};
            // Copy known-valid D3D11 blend factors even for opaque masks.
            // A zero-initialized BLEND_DESC has invalid factor/op enumerants
            // on devices that validate disabled-blend fields as well.
            s.alphaBlend->GetDesc(&maskDesc);
            maskDesc.RenderTarget[0].BlendEnable = output.alphaBlend ? TRUE : FALSE;
            maskDesc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;
            if (FAILED(dev->CreateBlendState(&maskDesc, cached.GetAddressOf())))
                return false;
        }
        maskedBlend = &cached;
    }
    ctx->UpdateSubresource(s.alphaConstants.Get(), 0, nullptr, alphaParams, 0, 0);
    s.backend.begin_frame(kBackground);
    if (maskedBlend)
        ctx->OMSetBlendState(maskedBlend->Get(), nullptr, 0xffffffffu);
    else
        ctx->OMSetBlendState(output.alphaBlend ? s.alphaBlend.Get() : nullptr, nullptr, 0xffffffffu);
    ID3D11Buffer* alphaBuffer = s.alphaConstants.Get();
    ctx->PSSetConstantBuffers(0, 1, &alphaBuffer);
    const UINT stride = sizeof(NativeVertex), offset = 0;
    ID3D11Buffer* boundVB = vb.Get();
    ctx->IASetInputLayout(s.layout.Get());
    ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    ctx->IASetVertexBuffers(0, 1, &boundVB, &stride, &offset);
    if (ib) ctx->IASetIndexBuffer(ib.Get(), DXGI_FORMAT_R32_UINT, 0);
    const D3D11_RECT fullScissor{0, 0, static_cast<LONG>(kWidth),
                                  static_cast<LONG>(kHeight)};
    const D3D11_RECT& rect = output.scissor ? output.nativeScissor : fullScissor;
    ctx->RSSetScissorRects(1, &rect);
    ctx->RSSetState(output.scissor ? s.scissorRaster.Get() : s.raster.Get());
    ctx->VSSetShader(s.vs.Get(), nullptr, 0);
    ctx->PSSetShader(!capture.enabled ? s.ps.Get() :
                     (capture.selectTexture ? s.textureOnlyPs.Get() : s.sampledPs.Get()), nullptr, 0);
    ID3D11ShaderResourceView* boundView = sampledView.Get();
    ID3D11SamplerState* boundSampler = sampledSampler.Get();
    ctx->PSSetShaderResources(0, 1, &boundView);
    ctx->PSSetSamplers(0, 1, &boundSampler);
    if (ib) ctx->DrawIndexed(indexCount, 0, 0);
    else ctx->Draw(static_cast<UINT>(vertices.size()), 0);
    // GPU submission is paired with the queued readback at Present.
    s.pending = true;
    ++s.issued;
    return true;
}

void observe(IDirect3DDevice9* game, D3DPRIMITIVETYPE type, UINT primitives,
             const void* bytes, UINT stride, UINT vertexCount,
             const std::uint32_t* indices, UINT indexCount) noexcept {
    if (!diagnostic_enabled() || !game || type != D3DPT_TRIANGLELIST ||
        primitives == 0 || primitives > kMaxVertices / 3)
        return;
    try {
        State& s = state();
        std::lock_guard<std::mutex> lock(s.mutex);
        ++s.observed;
        D3DVIEWPORT9 vp{};
        bool pretransformed = true;
        std::array<D3DMATRIX, 3> transforms{};
        TextureCapture capture{};
        OutputCapture output{};
        if (!supported_game_state(game, vp, pretransformed, transforms, capture, output)) return;
        // Count every admitted state, including calls after this frame's one
        // native draw. Use that bounded population to rotate the next frame's
        // probe rather than sampling its same first triangle indefinitely.
        const UINT candidateOrdinal = s.eligibleThisFrame++;
        ++s.eligible;
        if (s.attempted || candidateOrdinal != s.probeSlot) return;
        if (indexCount && (!indices || indexCount != primitives * 3 ||
                           vertexCount > kMaxVertices))
            return;
        if (!indexCount && vertexCount != primitives * 3) return;
        std::vector<NativeVertex> vertices;
        if (!translate_vertices(bytes, vertexCount, stride, vp,
                                pretransformed, transforms, capture, vertices))
            return;
        if (indices) {
            for (UINT i=0; i<indexCount; ++i)
                if (indices[i] >= vertexCount) return;
        }
        s.attempted = true;
        if (!submit(s, vertices, indices, indexCount, capture, output)) ++s.failed;
    } catch (...) {
        // Never interrupt the game's real draw or input on diagnostic failure.
    }
}
} // namespace

bool diagnostic_enabled() noexcept {
    static const bool optedIn = env_opt_in();
    return optedIn;
}

void observe_linear(IDirect3DDevice9* game, D3DPRIMITIVETYPE type,
                    UINT primitives, const void* vertices, UINT stride) noexcept {
    if (!primitives || primitives > kMaxVertices / 3) return;
    observe(game, type, primitives, vertices, stride, primitives * 3, nullptr, 0);
}

void observe_indexed(IDirect3DDevice9* game, D3DPRIMITIVETYPE type,
                     UINT primitives, const void* vertices, UINT stride,
                     UINT vertexCount, const std::uint32_t* indices,
                     UINT indexCount) noexcept {
    observe(game, type, primitives, vertices, stride, vertexCount, indices, indexCount);
}

void before_game_present(IDirect3DDevice9* game) noexcept {
    if (!diagnostic_enabled() || !game) return;
    try {
        State& s = state();
        std::lock_guard<std::mutex> lock(s.mutex);
        if (s.backend.ready() && s.backend.context()) {
            auto* ctx = s.backend.context();
            // Poll the oldest GPU fence without implicit flushing or CPU waits.
            auto& oldest = s.readbacks[s.readSlot];
            if (oldest.busy) {
                const HRESULT ready = ctx->GetData(
                    oldest.fence.Get(), nullptr, 0, D3D11_ASYNC_GETDATA_DONOTFLUSH);
                if (ready == S_OK) {
                    D3D11_MAPPED_SUBRESOURCE mapped{};
                    const HRESULT mapStatus = ctx->Map(oldest.staging.Get(), 0,
                        D3D11_MAP_READ, D3D11_MAP_FLAG_DO_NOT_WAIT, &mapped);
                    if (SUCCEEDED(mapStatus)) {
                        UINT changedPixels = 0;
                        for (UINT y = 0; y < kHeight; ++y) {
                            const auto* row = static_cast<const std::uint8_t*>(mapped.pData) +
                                static_cast<std::size_t>(y) * mapped.RowPitch;
                            for (UINT x = 0; x < kWidth; ++x) {
                                const auto* p = row + 4 * x;
                                if (std::abs(int(p[0])-20) > 3 ||
                                    std::abs(int(p[1])-9) > 3 ||
                                    std::abs(int(p[2])-9) > 3) ++changedPixels;
                            }
                        }
                        if (changedPixels) {
                            ComPtr<IDirect3DSurface9> back;
                            D3DSURFACE_DESC bb{};
                            if (SUCCEEDED(game->GetBackBuffer(0, 0, D3DBACKBUFFER_TYPE_MONO,
                                                             back.GetAddressOf())) && back &&
                                SUCCEEDED(back->GetDesc(&bb)) &&
                                bb.Width >= kWidth + 8u && bb.Height >= kHeight + 8u &&
                                bb.MultiSampleType == D3DMULTISAMPLE_NONE &&
                                (bb.Format == D3DFMT_A8R8G8B8 ||
                                 bb.Format == D3DFMT_X8R8G8B8)) {
                                // Cache CPU upload memory; invalidate on format/Reset.
                                if (!s.insetSurface || s.insetFormat != bb.Format) {
                                    s.insetSurface.Reset();
                                    s.insetFormat = D3DFMT_UNKNOWN;
                                    if (SUCCEEDED(game->CreateOffscreenPlainSurface(
                                            kWidth, kHeight, bb.Format, D3DPOOL_SYSTEMMEM,
                                            s.insetSurface.GetAddressOf(), nullptr)))
                                        s.insetFormat = bb.Format;
                                }
                                D3DLOCKED_RECT lockRect{};
                                if (s.insetSurface && s.insetFormat == bb.Format &&
                                    SUCCEEDED(s.insetSurface->LockRect(&lockRect, nullptr, 0))) {
                                    for (UINT y = 0; y < kHeight; ++y)
                                        std::memcpy(
                                            static_cast<std::uint8_t*>(lockRect.pBits) +
                                                static_cast<std::size_t>(y)*lockRect.Pitch,
                                            static_cast<const std::uint8_t*>(mapped.pData) +
                                                static_cast<std::size_t>(y)*mapped.RowPitch,
                                            kWidth*4);
                                    s.insetSurface->UnlockRect();
                                    POINT destination{static_cast<LONG>(bb.Width-kWidth-8), 8};
                                    if (SUCCEEDED(game->UpdateSurface(
                                            s.insetSurface.Get(), nullptr, back.Get(), &destination))) {
                                        ++s.visible;
                                        if (!s.logged) {
                                            spdlog::info("DX11 FIRST_GAME_DRAW_FRAME async game-origin FVF native Draw: {} changed pixels, {}x{} desktop inset; original D3D9 draw/input untouched; Quest3 UNTESTED",
                                                changedPixels, kWidth, kHeight);
                                            s.logged = true;
                                        }
                                    } else ++s.failed;
                                } else ++s.failed;
                            } else ++s.failed;
                        }
                        ctx->Unmap(oldest.staging.Get(), 0);
                        oldest.busy = false;
                        s.readSlot = (s.readSlot + 1u) % kReadbackSlots;
                    } else if (mapStatus != DXGI_ERROR_WAS_STILL_DRAWING) {
                        ++s.failed;
                        oldest.busy = false;
                        s.readSlot = (s.readSlot + 1u) % kReadbackSlots;
                    }
                } else if (FAILED(ready)) {
                    ++s.failed;
                    oldest.busy = false;
                    s.readSlot = (s.readSlot + 1u) % kReadbackSlots;
                }
            }
            if (s.pending) {
                auto& next = s.readbacks[s.writeSlot];
                if (!next.busy) {
                    ctx->CopyResource(next.staging.Get(), s.backend.color_texture());
                    ctx->End(next.fence.Get());
                    // A single GPU submit per diagnostic frame; never a blocking Map.
                    ctx->Flush();
                    next.busy = true;
                    s.writeSlot = (s.writeSlot + 1u) % kReadbackSlots;
                } else {
                    // Ring saturation is diagnostic-only: drop instead of stalling D3D9.
                    ++s.droppedCopies;
                }
            }
        } else if (s.pending) ++s.failed;
        s.pending = false;
        s.attempted = false;
        const UINT window = (std::min)(s.eligibleThisFrame, kProbeSlots);
        s.probeSlot = window ? (s.probeSlot + 1u) % window : 0u;
        s.eligibleThisFrame = 0;
        // Opt-in-only evidence: a hooked game Draw is not proof that the
        // restricted FVF subset was admitted, nor that GPU pixels became
        // visible in the game's backbuffer. Log both missing links explicitly.
        ++s.presents;
        if (s.presents == 300 ||
            (s.presents % 1800u == 0u && s.visible == 0u)) {
            spdlog::info(
                "DX11 FIRST_GAME_DRAW_FRAME progress: game_tri_draws={} native_draws={} desktop_insets={} failed={} presents={} eligible_state_draws={} next_probe_slot={}; unsupported draws stay DX9Ex; HMD UNTESTED",
                s.observed, s.issued, s.visible, s.failed, s.presents,
                s.eligible, s.probeSlot);
        }
    } catch (...) {
        // Preserve DX9Ex Present and recover on the next game frame.
        // The diagnostic is best-effort even when logging/readback fails;
        // leave all original D3D9 Present and input behavior untouched.
        State& s = state();
        s.pending = false;
        s.attempted = false;
        s.eligibleThisFrame = 0;
        s.probeSlot = 0;
    }
}

void before_game_reset() noexcept {
    if (!diagnostic_enabled()) return;
    State& s = state();
    std::lock_guard<std::mutex> lock(s.mutex);
    s.pending = false;
    s.attempted = false;
    s.eligibleThisFrame = 0;
    s.probeSlot = 0;
    for (auto& item : s.readbacks) {
        item.staging.Reset(); item.fence.Reset(); item.busy = false;
    }
    s.readSlot = s.writeSlot = 0;
    s.insetSurface.Reset(); s.insetFormat = D3DFMT_UNKNOWN;
    s.raster.Reset(); s.scissorRaster.Reset(); s.layout.Reset();
    s.alphaBlend.Reset(); s.alphaConstants.Reset();
    for (auto& masked : s.maskedBlends) masked.Reset();
    s.ps.Reset(); s.sampledPs.Reset(); s.textureOnlyPs.Reset(); s.vs.Reset();
    s.backend.shutdown();
}
} // namespace outrun::vr::dx11::live_game_frame
