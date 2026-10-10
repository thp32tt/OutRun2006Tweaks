#include "live_game_frame_bridge.hpp"
#include "native_backend.hpp"

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
constexpr std::array<float, 4> kBackground{0.035f, 0.035f, 0.08f, 1.0f};
constexpr char kShader[] = R"(
struct VIn { float4 clip : POSITION; float4 diffuse : COLOR0; };
struct VOut { float4 clip : SV_Position; float4 diffuse : COLOR0; };
VOut VS(VIn v) { VOut o; o.clip = v.clip; o.diffuse = v.diffuse; return o; }
float4 PS(VOut v) : SV_Target { return v.diffuse; }
)";
struct NativeVertex {
    float clip[4];
    float diffuse[4];
};

struct State {
    std::mutex mutex;
    NativeBackend backend;
    ComPtr<ID3D11VertexShader> vs;
    ComPtr<ID3D11PixelShader> ps;
    ComPtr<ID3D11InputLayout> layout;
    ComPtr<ID3D11RasterizerState> raster;
    ComPtr<ID3D11Texture2D> staging;
    bool pending = false;
    bool attempted = false;
    bool logged = false;
    UINT observed = 0;
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
    if (s.backend.ready() && s.vs && s.ps && s.layout && s.raster && s.staging)
        return true;
    s.backend.shutdown();
    s.vs.Reset(); s.ps.Reset(); s.layout.Reset(); s.raster.Reset(); s.staging.Reset();
    NativeBackendConfig cfg{};
    cfg.width = kWidth;
    cfg.height = kHeight;
    cfg.color_format = DXGI_FORMAT_B8G8R8A8_UNORM;
    if (!s.backend.initialize(cfg)) return false;
    auto* dev = s.backend.device();
    ComPtr<ID3DBlob> vcode, pcode;
    if (!compile("VS", "vs_4_0", vcode) ||
        !compile("PS", "ps_4_0", pcode) ||
        FAILED(dev->CreateVertexShader(vcode->GetBufferPointer(), vcode->GetBufferSize(),
                                      nullptr, s.vs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(pcode->GetBufferPointer(), pcode->GetBufferSize(),
                                     nullptr, s.ps.GetAddressOf())))
        return false;
    const D3D11_INPUT_ELEMENT_DESC elements[] = {
        {"POSITION", 0, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 0,
         D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"COLOR", 0, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 16,
         D3D11_INPUT_PER_VERTEX_DATA, 0}
    };
    if (FAILED(dev->CreateInputLayout(elements, 2,
        vcode->GetBufferPointer(), vcode->GetBufferSize(), s.layout.GetAddressOf())))
        return false;
    D3D11_RASTERIZER_DESC raster{};
    raster.FillMode = D3D11_FILL_SOLID;
    raster.CullMode = D3D11_CULL_NONE;
    raster.DepthClipEnable = TRUE;
    if (FAILED(dev->CreateRasterizerState(&raster, s.raster.GetAddressOf())))
        return false;
    D3D11_TEXTURE2D_DESC desc{};
    s.backend.color_texture()->GetDesc(&desc);
    desc.Usage = D3D11_USAGE_STAGING;
    desc.BindFlags = 0;
    desc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    desc.MiscFlags = 0;
    return SUCCEEDED(dev->CreateTexture2D(&desc, nullptr, s.staging.GetAddressOf()));
}

// Read the current game device, not a WARP fixture's manufactured state.
// COM getters AddRef; local ComPtrs always release before reset/return.
bool supported_game_state(IDirect3DDevice9* game, D3DVIEWPORT9& viewport) noexcept {
    if (!game || FAILED(game->GetViewport(&viewport)) ||
        viewport.Width == 0 || viewport.Height == 0)
        return false;
    DWORD fvf = 0;
    if (FAILED(game->GetFVF(&fvf)) ||
        fvf != (D3DFVF_XYZRHW | D3DFVF_DIFFUSE))
        return false;
    ComPtr<IDirect3DVertexShader9> vs;
    ComPtr<IDirect3DPixelShader9> ps;
    ComPtr<IDirect3DBaseTexture9> tex;
    if (FAILED(game->GetVertexShader(vs.GetAddressOf())) || vs ||
        FAILED(game->GetPixelShader(ps.GetAddressOf())) || ps ||
        FAILED(game->GetTexture(0, tex.GetAddressOf())) || tex)
        return false;

    // This very first vertical slice covers only untextured, unblended,
    // no-depth pretransformed diffuse triangles. Every other real game draw
    // proceeds exclusively through DX9Ex. No visual parity claim for others.
    DWORD blend=TRUE, alpha=TRUE, stencil=TRUE, depth=TRUE, clip=TRUE;
    if (FAILED(game->GetRenderState(D3DRS_ALPHABLENDENABLE, &blend)) ||
        FAILED(game->GetRenderState(D3DRS_ALPHATESTENABLE, &alpha)) ||
        FAILED(game->GetRenderState(D3DRS_STENCILENABLE, &stencil)) ||
        FAILED(game->GetRenderState(D3DRS_ZENABLE, &depth)) ||
        FAILED(game->GetRenderState(D3DRS_CLIPPING, &clip)) ||
        blend || alpha || stencil || depth || !clip)
        return false;
    DWORD op=0, arg=0;
    if (FAILED(game->GetTextureStageState(0, D3DTSS_COLOROP, &op)) ||
        FAILED(game->GetTextureStageState(0, D3DTSS_COLORARG1, &arg)) ||
        op != D3DTOP_SELECTARG1 || (arg & D3DTA_SELECTMASK) != D3DTA_DIFFUSE)
        return false;
    return true;
}

bool translate_vertices(const void* input, UINT count, UINT stride,
                        const D3DVIEWPORT9& vp,
                        std::vector<NativeVertex>& output) {
    if (!input || stride < 20 || stride > 512 || count == 0 || count > kMaxVertices)
        return false;
    output.resize(count);
    const auto* src = static_cast<const std::uint8_t*>(input);
    for (UINT i = 0; i < count; ++i) {
        float xyzw[4]{};
        DWORD diffuse = 0;
        std::memcpy(xyzw, src + static_cast<std::size_t>(i) * stride, sizeof(xyzw));
        std::memcpy(&diffuse, src + static_cast<std::size_t>(i) * stride + 16, 4);
        if (!std::isfinite(xyzw[0]) || !std::isfinite(xyzw[1]) ||
            !std::isfinite(xyzw[2]) || !std::isfinite(xyzw[3]) ||
            xyzw[3] <= 0.0f)
            return false;
        NativeVertex& v = output[i];
        v.clip[0] = 2.0f * (xyzw[0] - static_cast<float>(vp.X)) /
                    static_cast<float>(vp.Width) - 1.0f;
        v.clip[1] = 1.0f - 2.0f * (xyzw[1] - static_cast<float>(vp.Y)) /
                    static_cast<float>(vp.Height);
        v.clip[2] = xyzw[2];
        v.clip[3] = 1.0f;
        v.diffuse[0] = static_cast<float>((diffuse >> 16) & 255) / 255.0f;
        v.diffuse[1] = static_cast<float>((diffuse >> 8) & 255) / 255.0f;
        v.diffuse[2] = static_cast<float>(diffuse & 255) / 255.0f;
        v.diffuse[3] = static_cast<float>((diffuse >> 24) & 255) / 255.0f;
    }
    return true;
}

bool submit(State& s, const std::vector<NativeVertex>& vertices,
            const std::uint32_t* indices, UINT indexCount) noexcept {
    if (!ensure_pipeline(s)) return false;
    auto* dev = s.backend.device();
    auto* ctx = s.backend.context();
    if (!dev || !ctx) return false;
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

    s.backend.begin_frame(kBackground);
    const UINT stride = sizeof(NativeVertex), offset = 0;
    ID3D11Buffer* boundVB = vb.Get();
    ctx->IASetInputLayout(s.layout.Get());
    ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    ctx->IASetVertexBuffers(0, 1, &boundVB, &stride, &offset);
    if (ib) ctx->IASetIndexBuffer(ib.Get(), DXGI_FORMAT_R32_UINT, 0);
    ctx->RSSetState(s.raster.Get());
    ctx->VSSetShader(s.vs.Get(), nullptr, 0);
    ctx->PSSetShader(s.ps.Get(), nullptr, 0);
    if (ib) ctx->DrawIndexed(indexCount, 0, 0);
    else ctx->Draw(static_cast<UINT>(vertices.size()), 0);
    ctx->Flush();
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
        if (s.attempted) return;
        D3DVIEWPORT9 vp{};
        if (!supported_game_state(game, vp)) return;
        if (indexCount && (!indices || indexCount != primitives * 3 ||
                           vertexCount > kMaxVertices))
            return;
        if (!indexCount && vertexCount != primitives * 3) return;
        std::vector<NativeVertex> vertices;
        if (!translate_vertices(bytes, vertexCount, stride, vp, vertices))
            return;
        if (indices) {
            for (UINT i=0; i<indexCount; ++i)
                if (indices[i] >= vertexCount) return;
        }
        s.attempted = true;
        if (!submit(s, vertices, indices, indexCount)) ++s.failed;
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
        if (s.pending && s.backend.ready() && s.staging) {
            auto* ctx = s.backend.context();
            ctx->CopyResource(s.staging.Get(), s.backend.color_texture());
            D3D11_MAPPED_SUBRESOURCE mapped{};
            if (SUCCEEDED(ctx->Map(s.staging.Get(), 0, D3D11_MAP_READ, 0, &mapped))) {
                UINT changedPixels = 0;
                for (UINT y=0; y<kHeight; ++y) {
                    const auto* row = static_cast<const std::uint8_t*>(mapped.pData) +
                                      static_cast<std::size_t>(y) * mapped.RowPitch;
                    for (UINT x=0; x<kWidth; ++x) {
                        const auto* p = row + 4*x;
                        // Background is BGRA=(~20,~9,~9,255). A generated
                        // test clear alone must never count as a drawn frame.
                        if (std::abs(int(p[0])-20) > 3 ||
                            std::abs(int(p[1])-9) > 3 ||
                            std::abs(int(p[2])-9) > 3) ++changedPixels;
                    }
                }
                if (changedPixels) {
                    ComPtr<IDirect3DSurface9> sys, back;
                    D3DSURFACE_DESC bb{};
                    if (SUCCEEDED(game->GetBackBuffer(0,0,D3DBACKBUFFER_TYPE_MONO,
                                                    back.GetAddressOf())) && back &&
                        SUCCEEDED(back->GetDesc(&bb)) &&
                        bb.Width >= kWidth && bb.Height >= kHeight &&
                        SUCCEEDED(game->CreateOffscreenPlainSurface(
                            kWidth, kHeight, D3DFMT_A8R8G8B8, D3DPOOL_SYSTEMMEM,
                            sys.GetAddressOf(), nullptr)) && sys) {
                        D3DLOCKED_RECT lockRect{};
                        if (SUCCEEDED(sys->LockRect(&lockRect, nullptr, 0))) {
                            for (UINT y=0; y<kHeight; ++y)
                                std::memcpy(static_cast<std::uint8_t*>(lockRect.pBits) +
                                            static_cast<std::size_t>(y)*lockRect.Pitch,
                                            static_cast<const std::uint8_t*>(mapped.pData) +
                                            static_cast<std::size_t>(y)*mapped.RowPitch,
                                            kWidth*4);
                            sys->UnlockRect();
                            POINT destination{static_cast<LONG>(bb.Width-kWidth-8), 8};
                            if (SUCCEEDED(game->UpdateSurface(
                                sys.Get(), nullptr, back.Get(), &destination))) {
                                ++s.visible;
                                if (!s.logged) {
                                    spdlog::info("DX11 FIRST_GAME_DRAW_FRAME diagnostic: game-origin FVF draw issued on native D3D11 and {} pixels changed; {}x{} desktop inset; source game Draw and input untouched; Quest3 UNTESTED",
                                        changedPixels, kWidth, kHeight);
                                    s.logged = true;
                                }
                            } else ++s.failed;
                        } else ++s.failed;
                    } else ++s.failed;
                }
                ctx->Unmap(s.staging.Get(), 0);
            } else ++s.failed;
        }
        s.pending = false;
        s.attempted = false;
    } catch (...) {
        // Preserve DX9Ex Present and recover on the next game frame.
        state().pending = false;
        state().attempted = false;
    }
}

void before_game_reset() noexcept {
    if (!diagnostic_enabled()) return;
    State& s = state();
    std::lock_guard<std::mutex> lock(s.mutex);
    s.pending = false;
    s.attempted = false;
    s.staging.Reset(); s.raster.Reset(); s.layout.Reset();
    s.ps.Reset(); s.vs.Reset();
    s.backend.shutdown();
}
} // namespace outrun::vr::dx11::live_game_frame
