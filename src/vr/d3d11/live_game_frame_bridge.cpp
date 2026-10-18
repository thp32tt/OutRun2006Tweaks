#include "live_game_frame_bridge.hpp"
#include "live_game_primitive_span.hpp"
#include "live_game_depth_state.hpp"
#include "live_game_cull_state.hpp"
#include "live_game_sm3_composite.hpp"
#include "live_game_sm3_vertex_unpack.hpp"
#include "live_game_fvf_layout.hpp"
#include "live_game_object_clip.hpp"
#include "live_game_pixel_center.hpp"
#include "native_game_dynamic_stream.hpp"
#include "live_game_viewport_depth.hpp"
#include "live_game_stage0_blend.hpp"
#include "live_game_stage1_factor.hpp"
#include "live_game_stage1_dual_texture.hpp"
#include "live_game_stage1_uv.hpp"
#include "live_game_stage1_mirror_reuse.hpp"
#include "live_game_blend_extrema.hpp"
#include "native_backend.hpp"
#include "pipeline_translation.hpp"
#include "packed_texture_16bit.hpp"
#include "live_game_luminance_texture.hpp"
#include "live_game_rgb24_texture.hpp"
#include "live_game_rgba_texture.hpp"
#include "live_game_render_target_readback.hpp"
#include "live_game_float_vector_texture.hpp"
#include "live_game_dynamic_texture.hpp"
#include "live_game_10bit_texture.hpp"
#include "live_game_extended_luminance_texture.hpp"
#include "live_game_rg16_texture.hpp"
#include "live_game_a8p8_texture.hpp"
#include "live_game_p8_texture.hpp"
#include "live_game_rgb332_texture.hpp"
#include "live_game_rgba16_texture.hpp"
#include "live_game_float_rgba_texture.hpp"
#include "native_game_frame_batch.hpp"
#include "native_game_cpu_surface_ticket.hpp"
#include "native_game_source_mutation.hpp"
#include "native_game_surface_copy_region.hpp"
#include "native_game_frame_publication.hpp"
#include "native_game_gpu_handoff.hpp"
#include "native_game_shared_desktop.hpp"
#include "native_game_cpu_upload_transaction.hpp"
#include "native_game_shared_desktop_admission.hpp"
#include "native_game_frame_upload.hpp"
#include "native_game_dirty_region.hpp"
#include "native_game_readback_provenance.hpp"
#include "native_game_present_region.hpp"
#include "native_game_partial_dirty_upload.hpp"
#include "native_game_multi_dirty_upload.hpp"
#include "native_game_clear_color.hpp"
#include "native_game_masked_draw.hpp"
#include "native_game_fragment_reject.hpp"
#include "native_game_scissor_clip.hpp"
#include "native_game_offscreen_pass.hpp"
#include "native_game_inert_stencil_mrt.hpp"
#include "native_game_clear_coverage.hpp"
#include "native_game_full_color_depth.hpp"
#include "native_game_main_stencil_clear.hpp"
#include "native_game_backbuffer_admission.hpp"
#include "native_game_texture_atlas_budget.hpp"

#include <Windows.h>
#include <d3dcompiler.h>
#include <d3d11_1.h>
#include <wrl/client.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>
#include <mutex>
#include <string>
#include <vector>
#include <unordered_map>
#include <spdlog/spdlog.h>

namespace outrun::vr::dx11::live_game_frame {
namespace {
using Microsoft::WRL::ComPtr;
// The game UpdateSurface detour is also reached when we upload native pixels
// into its D3D9 backbuffer. Never acquire State::mutex again from that hook.
thread_local std::uint32_t nativeOutputUploadDepth = 0u;
struct NativeOutputUploadScope final {
    NativeOutputUploadScope() noexcept { ++nativeOutputUploadDepth; }
    ~NativeOutputUploadScope() { --nativeOutputUploadDepth; }
    NativeOutputUploadScope(const NativeOutputUploadScope&) = delete;
    NativeOutputUploadScope& operator=(const NativeOutputUploadScope&) = delete;
};
static_assert(dynamic_texture::kDefaultPool == D3DPOOL_DEFAULT &&
              dynamic_texture::kDynamicUsage == D3DUSAGE_DYNAMIC,
              "D3D9 DEFAULT/DYNAMIC source texture constants changed");
static_assert(D3DPT_POINTLIST == 1 && D3DPT_LINELIST == 2 && D3DPT_LINESTRIP == 3 &&
              D3DPT_TRIANGLELIST == 4 && D3DPT_TRIANGLESTRIP == 5 &&
              D3DPT_TRIANGLEFAN == 6, "D3D9 primitive span enum changed");
static_assert(kGameStage0BlendDiffuseAlpha == D3DTOP_BLENDDIFFUSEALPHA &&
              kGameStage0BlendTextureAlphaPM == D3DTOP_BLENDTEXTUREALPHAPM &&
              kGameStage0BlendCurrentAlpha == D3DTOP_BLENDCURRENTALPHA &&
              3u == D3DTOP_SELECTARG2,
              "Portable stage0 blend op constants must match the D3D9 SDK");
static_assert(kGameFvfXyz == D3DFVF_XYZ && kGameFvfXyzRhw == D3DFVF_XYZRHW &&
              kGameFvfDiffuse == D3DFVF_DIFFUSE && kGameFvfTex1 == D3DFVF_TEX1 &&
              kGameFvfNormal == D3DFVF_NORMAL &&
              kGameFvfPsize == D3DFVF_PSIZE &&
              kGameFvfSpecular == D3DFVF_SPECULAR &&
              kGameFvfTex2 == D3DFVF_TEX2 && kGameFvfTex3 == D3DFVF_TEX3 &&
              kGameFvfTex4 == D3DFVF_TEX4 &&
              kGameFvfTex5 == D3DFVF_TEX5 && kGameFvfTex6 == D3DFVF_TEX6 &&
              kGameFvfTex7 == D3DFVF_TEX7 && kGameFvfTex8 == D3DFVF_TEX8 &&
              kGameFvfTexCountMask == D3DFVF_TEXCOUNT_MASK &&
              kGameFvfPositionMask == D3DFVF_POSITION_MASK &&
              kGameFvfTexcoordSize1_0 == D3DFVF_TEXCOORDSIZE1(0) &&
               kGameFvfTexcoordSize1_1 == D3DFVF_TEXCOORDSIZE1(1) &&
               kGameFvfTexcoordSize1_2 == D3DFVF_TEXCOORDSIZE1(2) &&
               kGameFvfTexcoordSize1_3 == D3DFVF_TEXCOORDSIZE1(3) &&
               kGameFvfTexcoordSize1_4 == D3DFVF_TEXCOORDSIZE1(4) &&
               kGameFvfTexcoordSize1_5 == D3DFVF_TEXCOORDSIZE1(5) &&
               kGameFvfTexcoordSize1_6 == D3DFVF_TEXCOORDSIZE1(6) &&
               kGameFvfTexcoordSize1_7 == D3DFVF_TEXCOORDSIZE1(7) &&
               kGameFvfTexcoordSize3_0 == D3DFVF_TEXCOORDSIZE3(0) &&
               kGameFvfTexcoordSize3_7 == D3DFVF_TEXCOORDSIZE3(7) &&
               kGameFvfTexcoordSize4_0 == D3DFVF_TEXCOORDSIZE4(0) &&
               kGameFvfTexcoordSize4_7 == D3DFVF_TEXCOORDSIZE4(7),
              "Portable FVF constants must match the D3D9 SDK");
static_assert(D3DBLEND_ONE == 2 && D3DBLEND_SRCALPHA == 5 &&
              D3DBLEND_INVSRCALPHA == 6 && D3DBLENDOP_ADD == 1,
              "Portable SM3 blend admission must match D3D9 SDK");
static_assert(kStage1Disable == D3DTOP_DISABLE &&
              kStage1SelectArg1 == D3DTOP_SELECTARG1 &&
              kStage1SelectArg2 == D3DTOP_SELECTARG2 &&
              kStage1Modulate == D3DTOP_MODULATE &&
              kStage1Modulate2X == D3DTOP_MODULATE2X &&
              kStage1Modulate4X == D3DTOP_MODULATE4X &&
              kStage1Add == D3DTOP_ADD &&
              kStage1AddSigned == D3DTOP_ADDSIGNED &&
              kStage1AddSigned2X == D3DTOP_ADDSIGNED2X &&
              kStage1Subtract == D3DTOP_SUBTRACT &&
              kStage1AddSmooth == D3DTOP_ADDSMOOTH &&
              kStage1BlendDiffuseAlpha == D3DTOP_BLENDDIFFUSEALPHA &&
              kStage1BlendTextureAlpha == D3DTOP_BLENDTEXTUREALPHA &&
              kStage1BlendTextureAlphaPM == D3DTOP_BLENDTEXTUREALPHAPM &&
              kStage1BlendFactorAlpha == D3DTOP_BLENDFACTORALPHA &&
              kStage1BlendCurrentAlpha == D3DTOP_BLENDCURRENTALPHA &&
              kStage1ModulateAlphaAddColor == D3DTOP_MODULATEALPHA_ADDCOLOR &&
              kStage1ModulateColorAddAlpha == D3DTOP_MODULATECOLOR_ADDALPHA &&
              kStage1ModulateInvAlphaAddColor == D3DTOP_MODULATEINVALPHA_ADDCOLOR &&
              kStage1ModulateInvColorAddAlpha == D3DTOP_MODULATEINVCOLOR_ADDALPHA &&
              kStage1DotProduct3 == D3DTOP_DOTPRODUCT3 &&
              kStage1MultiplyAdd == D3DTOP_MULTIPLYADD &&
              kStage1Lerp == D3DTOP_LERP &&
              kStage1Current == D3DTA_CURRENT &&
              kStage1Specular == D3DTA_SPECULAR &&
              kStage1Constant == D3DTA_CONSTANT &&
              kStage1Factor == D3DTA_TFACTOR &&
              kStage1Complement == D3DTA_COMPLEMENT &&
              kStage1AlphaReplicate == D3DTA_ALPHAREPLICATE);
static_assert(D3DDECLTYPE_FLOAT1 == 0 && D3DDECLTYPE_FLOAT4 == 3 &&
              D3DDECLTYPE_D3DCOLOR == 4 && D3DDECLTYPE_UBYTE4 == 5 &&
              D3DDECLTYPE_SHORT2 == 6 && D3DDECLTYPE_SHORT4 == 7 &&
              D3DDECLTYPE_UBYTE4N == 8 && D3DDECLTYPE_SHORT2N == 9 &&
              D3DDECLTYPE_SHORT4N == 10 && D3DDECLTYPE_USHORT2N == 11 &&
              D3DDECLTYPE_USHORT4N == 12 && D3DDECLTYPE_FLOAT16_2 == 15 &&
              D3DDECLTYPE_FLOAT16_4 == 16 && D3DDECLTYPE_UNUSED == 17,
              "Portable D3D9 SM3 declaration types changed");
constexpr UINT kWidth = 256;
constexpr UINT kHeight = 144;

// D3D9 menu/race fades can blend alpha independently of RGB. Only factors
// and operations supported by D3D11 output merger are admitted, otherwise
// the original D3D9 game draw and input remain authoritative.
constexpr bool native_game_alpha_factor(DWORD f, D3D11_BLEND& out) noexcept {
    switch (f) {
    case D3DBLEND_ZERO: out = D3D11_BLEND_ZERO; return true;
    case D3DBLEND_ONE: out = D3D11_BLEND_ONE; return true;
    case D3DBLEND_SRCALPHA: out = D3D11_BLEND_SRC_ALPHA; return true;
    case D3DBLEND_INVSRCALPHA: out = D3D11_BLEND_INV_SRC_ALPHA; return true;
    case D3DBLEND_DESTALPHA: out = D3D11_BLEND_DEST_ALPHA; return true;
    case D3DBLEND_INVDESTALPHA: out = D3D11_BLEND_INV_DEST_ALPHA; return true;
    default: return false;
    }
}
constexpr bool native_game_separate_alpha(
    DWORD source, DWORD destination, DWORD equation,
    D3D11_BLEND& src, D3D11_BLEND& dst, D3D11_BLEND_OP& op) noexcept {
    D3D11_BLEND s{}, d{};
    if (!native_game_alpha_factor(source, s) ||
        !native_game_alpha_factor(destination, d)) return false;
    D3D11_BLEND_OP operation{};
    switch (equation) {
    case D3DBLENDOP_ADD: operation = D3D11_BLEND_OP_ADD; break;
    case D3DBLENDOP_SUBTRACT: operation = D3D11_BLEND_OP_SUBTRACT; break;
    case D3DBLENDOP_REVSUBTRACT: operation = D3D11_BLEND_OP_REV_SUBTRACT; break;
    default: return false;
    }
    src = s; dst = d; op = operation;
    return true;
}
constexpr bool native_game_separate_alpha_contract() noexcept {
    D3D11_BLEND src = D3D11_BLEND_ZERO, dst = D3D11_BLEND_ZERO;
    D3D11_BLEND_OP op = D3D11_BLEND_OP_ADD;
    if (!native_game_separate_alpha(D3DBLEND_ONE, D3DBLEND_INVSRCALPHA,
            D3DBLENDOP_ADD, src, dst, op) ||
        src != D3D11_BLEND_ONE || dst != D3D11_BLEND_INV_SRC_ALPHA ||
        op != D3D11_BLEND_OP_ADD) return false;
    if (!native_game_separate_alpha(D3DBLEND_SRCALPHA, D3DBLEND_DESTALPHA,
            D3DBLENDOP_REVSUBTRACT, src, dst, op) ||
        src != D3D11_BLEND_SRC_ALPHA || dst != D3D11_BLEND_DEST_ALPHA ||
        op != D3D11_BLEND_OP_REV_SUBTRACT) return false;
    const auto oldSrc = src;
    const auto oldDst = dst;
    const auto oldOp = op;
    return !native_game_separate_alpha(D3DBLEND_SRCALPHASAT, D3DBLEND_ONE,
                D3DBLENDOP_ADD, src, dst, op) &&
           !native_game_separate_alpha(D3DBLEND_ONE, D3DBLEND_ONE,
                D3DBLENDOP_MIN, src, dst, op) &&
           !native_game_separate_alpha(D3DBLEND_BLENDFACTOR, D3DBLEND_ONE,
                D3DBLENDOP_ADD, src, dst, op) &&
           src == oldSrc && dst == oldDst && op == oldOp;
}
static_assert(native_game_separate_alpha_contract(),
              "Live D3D9 independent alpha OM/fallback regression");

// Live programmable D3D9 color and independent-alpha factors map to a
// per-game-Draw D3D11 output-merger state. No guessed blend constants or
// dual-source/factor modes: anything not representable falls back to D3D9.
constexpr bool sm3_live_factor(DWORD f, bool alpha, bool independent,
                              D3D11_BLEND& out) noexcept {
    if (independent && f != D3DBLEND_ZERO && f != D3DBLEND_ONE &&
        f != D3DBLEND_SRCALPHA && f != D3DBLEND_INVSRCALPHA &&
        f != D3DBLEND_DESTALPHA && f != D3DBLEND_INVDESTALPHA) return false;
    switch (f) {
    case D3DBLEND_ZERO: out = D3D11_BLEND_ZERO; break;
    case D3DBLEND_ONE: out = D3D11_BLEND_ONE; break;
    case D3DBLEND_SRCCOLOR: out = alpha ? D3D11_BLEND_SRC_ALPHA : D3D11_BLEND_SRC_COLOR; break;
    case D3DBLEND_INVSRCCOLOR: out = alpha ? D3D11_BLEND_INV_SRC_ALPHA : D3D11_BLEND_INV_SRC_COLOR; break;
    case D3DBLEND_SRCALPHA: out = D3D11_BLEND_SRC_ALPHA; break;
    case D3DBLEND_INVSRCALPHA: out = D3D11_BLEND_INV_SRC_ALPHA; break;
    case D3DBLEND_DESTALPHA: out = D3D11_BLEND_DEST_ALPHA; break;
    case D3DBLEND_INVDESTALPHA: out = D3D11_BLEND_INV_DEST_ALPHA; break;
    case D3DBLEND_DESTCOLOR: out = alpha ? D3D11_BLEND_DEST_ALPHA : D3D11_BLEND_DEST_COLOR; break;
    case D3DBLEND_INVDESTCOLOR: out = alpha ? D3D11_BLEND_INV_DEST_ALPHA : D3D11_BLEND_INV_DEST_COLOR; break;
    default: return false;
    }
    return true;
}
constexpr bool sm3_live_blend_op(DWORD f, D3D11_BLEND_OP& out) noexcept {
    switch (f) {
    case D3DBLENDOP_ADD: out = D3D11_BLEND_OP_ADD; return true;
    case D3DBLENDOP_SUBTRACT: out = D3D11_BLEND_OP_SUBTRACT; return true;
    case D3DBLENDOP_REVSUBTRACT: out = D3D11_BLEND_OP_REV_SUBTRACT; return true;
    default: return false;
    }
}
constexpr bool sm3_live_blend_desc(
    DWORD sc, DWORD dc, DWORD oc, bool separate,
    DWORD sa, DWORD da, DWORD oa, D3D11_RENDER_TARGET_BLEND_DESC& out) noexcept {
    D3D11_RENDER_TARGET_BLEND_DESC b{};
    b.BlendEnable = TRUE;
    b.RenderTargetWriteMask = D3D11_COLOR_WRITE_ENABLE_ALL;
    if (!sm3_live_factor(sc, false, false, b.SrcBlend) ||
        !sm3_live_factor(dc, false, false, b.DestBlend) ||
        !sm3_live_blend_op(oc, b.BlendOp) ||
        !sm3_live_factor(separate ? sa : sc, true, separate, b.SrcBlendAlpha) ||
        !sm3_live_factor(separate ? da : dc, true, separate, b.DestBlendAlpha) ||
        !sm3_live_blend_op(separate ? oa : oc, b.BlendOpAlpha))
        return false;
    out = b;
    return true;
}
constexpr std::uint64_t sm3_live_blend_key(
    const D3D11_RENDER_TARGET_BLEND_DESC& b) noexcept {
    return static_cast<std::uint64_t>(b.SrcBlend) |
        (static_cast<std::uint64_t>(b.DestBlend) << 8u) |
        (static_cast<std::uint64_t>(b.BlendOp) << 16u) |
        (static_cast<std::uint64_t>(b.SrcBlendAlpha) << 24u) |
        (static_cast<std::uint64_t>(b.DestBlendAlpha) << 32u) |
        (static_cast<std::uint64_t>(b.BlendOpAlpha) << 40u);
}
constexpr bool sm3_live_blend_regression() noexcept {
    D3D11_RENDER_TARGET_BLEND_DESC b{};
    if (!sm3_live_blend_desc(D3DBLEND_SRCCOLOR, D3DBLEND_INVDESTCOLOR,
        D3DBLENDOP_SUBTRACT, true, D3DBLEND_ONE, D3DBLEND_INVSRCALPHA,
        D3DBLENDOP_REVSUBTRACT, b) ||
        b.SrcBlend != D3D11_BLEND_SRC_COLOR ||
        b.DestBlend != D3D11_BLEND_INV_DEST_COLOR ||
        b.BlendOp != D3D11_BLEND_OP_SUBTRACT ||
        b.SrcBlendAlpha != D3D11_BLEND_ONE ||
        b.DestBlendAlpha != D3D11_BLEND_INV_SRC_ALPHA ||
        b.BlendOpAlpha != D3D11_BLEND_OP_REV_SUBTRACT) return false;
    if (!sm3_live_blend_desc(D3DBLEND_SRCCOLOR, D3DBLEND_INVDESTCOLOR,
        D3DBLENDOP_ADD, false, 0u, 0u, 0u, b) ||
        b.SrcBlendAlpha != D3D11_BLEND_SRC_ALPHA ||
        b.DestBlendAlpha != D3D11_BLEND_INV_DEST_ALPHA) return false;
    const auto saved = b;
    return !sm3_live_blend_desc(D3DBLEND_BLENDFACTOR, D3DBLEND_ONE,
                D3DBLENDOP_ADD, false, 0u, 0u, 0u, b) &&
           !sm3_live_blend_desc(D3DBLEND_ONE, D3DBLEND_ONE,
                D3DBLENDOP_MIN, false, 0u, 0u, 0u, b) &&
           !sm3_live_blend_desc(D3DBLEND_ONE, D3DBLEND_ONE,
                D3DBLENDOP_ADD, true, D3DBLEND_SRCCOLOR,
                D3DBLEND_ONE, D3DBLENDOP_ADD, b) &&
           saved.SrcBlend == b.SrcBlend &&
           saved.SrcBlendAlpha == b.SrcBlendAlpha;
}
static_assert(sm3_live_blend_regression(),
              "Game RGB/independent alpha OM translation must fail closed");



// Map a live D3D9 source viewport onto the diagnostic backbuffer inset.
// Using the complete game render-target dimensions (not viewport.Width alone)
// preserves split/partial menu, vehicle-selection and race views during both
// real game Draw and DrawIndexed. Always retain original D3D9 rendering.
struct GameNativeInsetRect {
    float left = 0.0f, top = 0.0f, right = 0.0f, bottom = 0.0f;
};
constexpr bool game_native_inset_viewport(
    std::uint32_t x, std::uint32_t y,
    std::uint32_t width, std::uint32_t height,
    std::uint32_t sourceWidth, std::uint32_t sourceHeight,
    GameNativeInsetRect& result,
    std::uint32_t destinationWidth = kWidth,
    std::uint32_t destinationHeight = kHeight) noexcept {
    if (!width || !height || !sourceWidth || !sourceHeight ||
        !destinationWidth || !destinationHeight ||
        static_cast<std::uint64_t>(x) + width > sourceWidth ||
        static_cast<std::uint64_t>(y) + height > sourceHeight)
        return false;
    const double dx = static_cast<double>(destinationWidth) / sourceWidth;
    const double dy = static_cast<double>(destinationHeight) / sourceHeight;
    const GameNativeInsetRect mapped{
        static_cast<float>(x * dx),
        static_cast<float>(y * dy),
        static_cast<float>((static_cast<std::uint64_t>(x) + width) * dx),
        static_cast<float>((static_cast<std::uint64_t>(y) + height) * dy)
    };
    if (!(mapped.right > mapped.left && mapped.bottom > mapped.top) ||
        mapped.right - mapped.left < 1.0f ||
        mapped.bottom - mapped.top < 1.0f ||
        mapped.left < 0.0f || mapped.top < 0.0f ||
        mapped.right > destinationWidth || mapped.bottom > destinationHeight)
        return false;
    result = mapped;
    return true;
}
// Compile-time positive/negative source-to-native raster geometry contracts.
constexpr bool game_native_inset_viewport_contract() noexcept {
    GameNativeInsetRect mapped{};
    if (!game_native_inset_viewport(0, 0, 1920, 1080, 1920, 1080, mapped) ||
        mapped.left != 0.0f || mapped.top != 0.0f ||
        mapped.right != 256.0f || mapped.bottom != 144.0f)
        return false;
    if (!game_native_inset_viewport(480, 270, 960, 540, 1920, 1080, mapped) ||
        mapped.left != 64.0f || mapped.top != 36.0f ||
        mapped.right != 192.0f || mapped.bottom != 108.0f)
        return false;
    return !game_native_inset_viewport(1919, 0, 2, 1080, 1920, 1080, mapped) &&
           !game_native_inset_viewport(0, 1080, 1920, 1, 1920, 1080, mapped) &&
           !game_native_inset_viewport(0, 0, 0, 1080, 1920, 1080, mapped) &&
           !game_native_inset_viewport(0, 0, 1, 1, 1920, 1080, mapped);
}
static_assert(game_native_inset_viewport_contract(),
              "DX11 live game partial-viewport native raster mapping regression");
constexpr UINT kMaxVertices = kMaxNativeGameVertices;
constexpr UINT kMaxIndices = kMaxNativeGameVertices;
// Rotate through the entire eligible game Draw population, not only the first
// 64. The per-Present native Draw budget remains 1 or an explicitly opted-in 8.
constexpr UINT kReadbackSlots = 3; // GPU event-fenced frame copies
// D3D11 sampler range: reject rather than clamp unsupported D3D9 LOD offsets.
constexpr float kMinMipLodBias = -16.0f;
constexpr float kMaxMipLodBias = 15.99f;

constexpr std::array<float, 4> kBackground{0.035f, 0.035f, 0.08f, 1.0f};
constexpr char kShader[] = R"(
struct VIn { float4 clip : POSITION; float4 diffuse : COLOR0; float2 uv : TEXCOORD0; float4 specular : COLOR1; float2 uvStage1 : TEXCOORD1; };
struct VOut { float4 clip : SV_Position; float4 diffuse : COLOR0; float2 uv : TEXCOORD0; float4 specular : COLOR1; float2 uvStage1 : TEXCOORD1; };
Texture2D gameTexture : register(t0);
SamplerState gameSampler : register(s0);
cbuffer AlphaParams : register(b0) { float4 alphaParams; };
void AlphaGate(float alpha) {
    if (alphaParams.x > 0.5f) {
        float value = floor(saturate(alpha) * 255.0f + 0.5f);
        bool pass = (alphaParams.z == 2.0f && value < alphaParams.y) ||
                    (alphaParams.z == 3.0f && value == alphaParams.y) ||
                    (alphaParams.z == 4.0f && value <= alphaParams.y) ||
                    (alphaParams.z == 5.0f && value > alphaParams.y) ||
                    (alphaParams.z == 6.0f && value != alphaParams.y) ||
                    (alphaParams.z == 7.0f && value >= alphaParams.y) ||
                    (alphaParams.z == 8.0f); // D3DCMP_ALWAYS
        clip(pass ? 1.0f : -1.0f);
    }
}
VOut VS(VIn v) { VOut o; o.clip = v.clip; o.diffuse = v.diffuse; o.uv = v.uv; o.specular = v.specular; o.uvStage1 = v.uvStage1; return o; }
float4 PS(VOut v) : SV_Target { float4 c = v.diffuse; AlphaGate(c.a); return c; }
float4 PSTextured(VOut v) : SV_Target { float4 c = gameTexture.Sample(gameSampler, v.uv) * v.diffuse; AlphaGate(c.a); return c; }
float4 PSTextureOnly(VOut v) : SV_Target { float4 c = gameTexture.Sample(gameSampler, v.uv); AlphaGate(c.a); return c; }
// Stage0 texture RGB can select an independent vertex fade alpha.
float4 PSTextureSelectTextureDiffuseAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(t.rgb, v.diffuse.a);
    AlphaGate(c.a); return c;
}
float4 PSTextureSelectTextureModulateAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(t.rgb, t.a * v.diffuse.a);
    AlphaGate(c.a); return c;
}
// Stage0 SELECTARG1 keeps texture RGB while alpha arithmetic uses both sources.
float4 PSTextureSelectTextureAddAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(t.rgb, saturate(t.a + v.diffuse.a));
    AlphaGate(c.a); return c;
}
float4 PSTextureSelectTextureSubtractAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(t.rgb, saturate(t.a - v.diffuse.a));
    AlphaGate(c.a); return c;
}
// Stage0 SELECTARG2 returns vertex RGB but computes an independent
// saturating D3D9 stage-0 alpha from TEXTURE and DIFFUSE/CURRENT.
float4 PSTextureSelectDiffuseAddAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(v.diffuse.rgb, saturate(t.a + v.diffuse.a));
    AlphaGate(c.a); return c;
}
float4 PSTextureSelectDiffuseSubtractAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(v.diffuse.rgb, saturate(t.a - v.diffuse.a));
    AlphaGate(c.a); return c;
}
// Stage0 SELECTARG2 RGB consumes DIFFUSE/CURRENT but alpha may use texture.
float4 PSTextureSelectDiffuseTextureAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(v.diffuse.rgb, t.a);
    AlphaGate(c.a); return c;
}
float4 PSTextureSelectDiffuseModulateAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(v.diffuse.rgb, t.a * v.diffuse.a);
    AlphaGate(c.a); return c;
}
// D3DTOP_ADD saturates both RGB and alpha before alpha comparison.
float4 PSTextureAdd(VOut v) : SV_Target { float4 c = saturate(gameTexture.Sample(gameSampler, v.uv) + v.diffuse); AlphaGate(c.a); return c; }
// D3DTOP_SUBTRACT saturates Arg1(TEXTURE) - Arg2(DIFFUSE/CURRENT) in RGBA.
float4 PSTextureSubtract(VOut v) : SV_Target { float4 c = saturate(gameTexture.Sample(gameSampler, v.uv) - v.diffuse); AlphaGate(c.a); return c; }
// Stage0 SUBTRACT RGB with selected texture/diffuse alpha (D3D9 stage 0).
float4 PSTextureSubtractTextureAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb - v.diffuse.rgb), t.a);
    AlphaGate(c.a); return c;
}
float4 PSTextureSubtractDiffuseAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb - v.diffuse.rgb), v.diffuse.a);
    AlphaGate(c.a); return c;
}
// D3D9 stage 0 permits MODULATE alpha with independent SUBTRACT RGB.
float4 PSTextureSubtractModulateAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb - v.diffuse.rgb), t.a * v.diffuse.a);
    AlphaGate(c.a); return c;
}
// Stage0 D3D9 MODULATE2X/4X: scale RGB and alpha, saturate before alpha test.
float4 PSTextureModulate2X(VOut v) : SV_Target { float4 c = saturate(2.0f * gameTexture.Sample(gameSampler, v.uv) * v.diffuse); AlphaGate(c.a); return c; }
float4 PSTextureModulate4X(VOut v) : SV_Target { float4 c = saturate(4.0f * gameTexture.Sample(gameSampler, v.uv) * v.diffuse); AlphaGate(c.a); return c; }
// D3D9 MODULATE2X/4X RGB with independently selected unscaled alpha.
float4 PSTextureModulate2XTextureAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(2.0f * t.rgb * v.diffuse.rgb), t.a);
    AlphaGate(c.a); return c;
}
float4 PSTextureModulate2XDiffuseAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(2.0f * t.rgb * v.diffuse.rgb), v.diffuse.a);
    AlphaGate(c.a); return c;
}
float4 PSTextureModulate4XTextureAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(4.0f * t.rgb * v.diffuse.rgb), t.a);
    AlphaGate(c.a); return c;
}
float4 PSTextureModulate4XDiffuseAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(4.0f * t.rgb * v.diffuse.rgb), v.diffuse.a);
    AlphaGate(c.a); return c;
}
// D3D9 fixed-function RGB MODULATE with independently selected texture/diffuse alpha.
float4 PSTextureModulateTextureAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(t.rgb * v.diffuse.rgb, t.a);
    AlphaGate(c.a); return c;
}
float4 PSTextureModulateDiffuseAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(t.rgb * v.diffuse.rgb, v.diffuse.a);
    AlphaGate(c.a); return c;
}
// Independently select D3D9 alpha after saturating stage0 ADD RGB.
float4 PSTextureAddTextureAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb), t.a);
    AlphaGate(c.a); return c;
}
float4 PSTextureAddDiffuseAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb), v.diffuse.a);
    AlphaGate(c.a); return c;
}
// D3D9 stage0 texture/diffuse alpha blending chooses the same factor for RGBA.
// Both variants feed the existing D3D9 alpha test and D3D11 blend/write state.
float4 PSTextureBlendTextureAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = lerp(v.diffuse, t, t.a);
    AlphaGate(c.a); return c;
}
float4 PSTextureBlendDiffuseAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = lerp(v.diffuse, t, v.diffuse.a);
    AlphaGate(c.a); return c;
}
// Game-authored D3D9 stage0 texture/diffuse-factor RGB, independent output alpha.
float4 PSTextureBlendTextureSelectedTextureAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float3 rgb = lerp(v.diffuse.rgb, t.rgb, t.a);
    float4 c = float4(rgb, t.a);
    AlphaGate(c.a); return c;
}
float4 PSTextureBlendTextureSelectedDiffuseAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float3 rgb = lerp(v.diffuse.rgb, t.rgb, t.a);
    float4 c = float4(rgb, v.diffuse.a);
    AlphaGate(c.a); return c;
}
float4 PSTextureBlendDiffuseSelectedTextureAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float3 rgb = lerp(v.diffuse.rgb, t.rgb, v.diffuse.a);
    float4 c = float4(rgb, t.a);
    AlphaGate(c.a); return c;
}
float4 PSTextureBlendDiffuseSelectedDiffuseAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float3 rgb = lerp(v.diffuse.rgb, t.rgb, v.diffuse.a);
    float4 c = float4(rgb, v.diffuse.a);
    AlphaGate(c.a); return c;
}
float4 PSTextureBlendTextureModulateAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(lerp(v.diffuse.rgb, t.rgb, t.a), t.a * v.diffuse.a);
    AlphaGate(c.a); return c;
}
float4 PSTextureBlendDiffuseModulateAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(lerp(v.diffuse.rgb, t.rgb, v.diffuse.a), t.a * v.diffuse.a);
    AlphaGate(c.a); return c;
}
// Game-stage RGB blend factors from texture/diffuse with independently scaled alpha.
// Preserve the alpha test AFTER saturating D3DTOP_MODULATE2X/4X.
float4 PSTextureBlendTextureModulate2XAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(lerp(v.diffuse.rgb, t.rgb, t.a),
                      saturate(2.0f * t.a * v.diffuse.a));
    AlphaGate(c.a); return c;
}
float4 PSTextureBlendTextureModulate4XAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(lerp(v.diffuse.rgb, t.rgb, t.a),
                      saturate(4.0f * t.a * v.diffuse.a));
    AlphaGate(c.a); return c;
}
float4 PSTextureBlendDiffuseModulate2XAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(lerp(v.diffuse.rgb, t.rgb, v.diffuse.a),
                      saturate(2.0f * t.a * v.diffuse.a));
    AlphaGate(c.a); return c;
}
float4 PSTextureBlendDiffuseModulate4XAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(lerp(v.diffuse.rgb, t.rgb, v.diffuse.a),
                      saturate(4.0f * t.a * v.diffuse.a));
    AlphaGate(c.a); return c;
}
// Game-authored BLENDTEXTUREALPHA/BLENDDIFFUSEALPHA RGB with independent
// D3DTOP_ADD alpha. D3D9 saturates the alpha sum before alpha test/blending.
float4 PSTextureBlendTextureAddAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(lerp(v.diffuse.rgb, t.rgb, t.a), saturate(t.a + v.diffuse.a));
    AlphaGate(c.a); return c;
}
float4 PSTextureBlendDiffuseAddAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(lerp(v.diffuse.rgb, t.rgb, v.diffuse.a), saturate(t.a + v.diffuse.a));
    AlphaGate(c.a); return c;
}
// Independent D3D9 stage0 SUBTRACT alpha: TEXTURE - DIFFUSE/CURRENT,
// saturating negative results before alpha test and output blending.
float4 PSTextureBlendTextureSubtractAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(lerp(v.diffuse.rgb, t.rgb, t.a), saturate(t.a - v.diffuse.a));
    AlphaGate(c.a); return c;
}
float4 PSTextureBlendDiffuseSubtractAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(lerp(v.diffuse.rgb, t.rgb, v.diffuse.a), saturate(t.a - v.diffuse.a));
    AlphaGate(c.a); return c;
}
// Game stage0 BLEND texture/diffuse factor RGB, independent ADDSMOOTH alpha.
float4 PSTextureBlendTextureAddSmoothAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(lerp(v.diffuse.rgb, t.rgb, t.a),
                      saturate(t.a + v.diffuse.a * (1.0f - t.a)));
    AlphaGate(c.a); return c;
}
float4 PSTextureBlendDiffuseAddSmoothAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(lerp(v.diffuse.rgb, t.rgb, v.diffuse.a),
                      saturate(t.a + v.diffuse.a * (1.0f - t.a)));
    AlphaGate(c.a); return c;
}
// D3D9 stage0 BLENDFACTORALPHA uses the alpha byte of D3DRS_TEXTUREFACTOR
// for both RGB and alpha; this diagnostic never reads the RGB factor bytes.
float4 PSTextureBlendFactorAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = lerp(v.diffuse, t, alphaParams.w);
    AlphaGate(c.a); return c;
}
// D3D9 stage0 factor-blended RGB with separately selected texture alpha.
float4 PSTextureBlendFactorTextureAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(lerp(v.diffuse.rgb, t.rgb, alphaParams.w), t.a);
    AlphaGate(c.a); return c;
}
// D3D9 stage0 factor-blended RGB with independent MODULATE alpha.
float4 PSTextureBlendFactorModulateAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(lerp(v.diffuse.rgb, t.rgb, alphaParams.w), t.a * v.diffuse.a);
    AlphaGate(c.a); return c;
}
// D3D9 BLENDFACTORALPHA RGB with independently selected DIFFUSE/CURRENT alpha.
float4 PSTextureBlendFactorDiffuseAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(lerp(v.diffuse.rgb, t.rgb, alphaParams.w), v.diffuse.a);
    AlphaGate(c.a); return c;
}
// D3D9 BLENDFACTORALPHA RGB and separate ADD(TEXTURE,DIFFUSE) alpha.
// The fixed-function ADD stage saturates before alpha test.
float4 PSTextureBlendFactorAddAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(lerp(v.diffuse.rgb, t.rgb, alphaParams.w), saturate(t.a + v.diffuse.a));
    AlphaGate(c.a); return c;
}
// D3D9 texture-factor RGB interpolation with independent SUBTRACT alpha.
float4 PSTextureBlendFactorSubtractAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(lerp(v.diffuse.rgb, t.rgb, alphaParams.w),
                      saturate(t.a - v.diffuse.a));
    AlphaGate(c.a); return c;
}
// D3D9 texture-factor RGB interpolation with independent ADDSMOOTH alpha.
float4 PSTextureBlendFactorAddSmoothAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(lerp(v.diffuse.rgb, t.rgb, alphaParams.w),
                      saturate(t.a + v.diffuse.a * (1.0f - t.a)));
    AlphaGate(c.a); return c;
}
// Independent D3D9 stage0 MODULATE2X alpha with BLENDFACTORALPHA RGB.
float4 PSTextureBlendFactorModulate2XAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(lerp(v.diffuse.rgb, t.rgb, alphaParams.w),
                      saturate(2.0f * t.a * v.diffuse.a));
    AlphaGate(c.a); return c;
}
// Independent D3D9 stage0 MODULATE4X alpha with BLENDFACTORALPHA RGB.
float4 PSTextureBlendFactorModulate4XAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(lerp(v.diffuse.rgb, t.rgb, alphaParams.w),
                      saturate(4.0f * t.a * v.diffuse.a));
    AlphaGate(c.a); return c;
}
// Exact ADDSMOOTH RGB with independently selected texture or diffuse alpha.
float4 PSTextureAddSmoothTextureAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.rgb)), t.a);
    AlphaGate(c.a); return c;
}
float4 PSTextureAddSmoothDiffuseAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.rgb)), v.diffuse.a);
    AlphaGate(c.a); return c;
}
// Exact D3D9 fixed-function ADDSMOOTH: Arg1 + Arg2*(1-Arg1) for RGBA.
float4 PSTextureAddSmooth(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = saturate(t + v.diffuse * (1.0f - t));
    AlphaGate(c.a); return c;
}
)";
// Keep both source literals below MSVC C2026 per-literal size limits.
// The native pixel shaders compile from their concatenation once per pipeline.
constexpr char kScaledAlphaShader[] = R"(
// D3D9 PM: ARG1 + ARG2*(1-texture alpha), including alpha.
float4 PSTextureBlendTextureAlphaPM(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = saturate(t + v.diffuse * (1.0f - t.a));
    AlphaGate(c.a); return c;
}
// Mixed PM RGB plus independently selected original texture alpha.
// Unlike a full PM alpha operation, ALPHAOP=SELECTARG1 must return t.a.
float4 PSTextureBlendTextureAlphaPMSelectTextureAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)), t.a);
    AlphaGate(c.a); return c;
}
// PM RGB must use texture alpha as its interpolation factor; SELECTARG2 alpha
// instead returns the vertex DIFFUSE/CURRENT alpha, never the full PM alpha.
// PM RGB plus independent stage0 MODULATE(TEXTURE, DIFFUSE/CURRENT) alpha.
// Alpha testing must consume the modulated value, not premultiplied RGB alpha.
float4 PSTextureBlendTextureAlphaPMModulateAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),
                      t.a * v.diffuse.a);
    AlphaGate(c.a); return c;
}
// PM RGB with independently added stage0 alpha; both source alpha values
// saturate BEFORE AlphaGate, without changing the texture-alpha RGB weight.
float4 PSTextureBlendTextureAlphaPMAddAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),
                      saturate(t.a + v.diffuse.a));
    AlphaGate(c.a); return c;
}
// PM RGB and independently SUBTRACTED stage0 alpha: TEXTURE - DIFFUSE/CURRENT.
// RGB uses the original texture alpha for premultiplication, while alpha
// testing/blending must see the saturated independent result.
float4 PSTextureBlendTextureAlphaPMSubtractAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),
                      saturate(t.a - v.diffuse.a));
    AlphaGate(c.a); return c;
}

// PM RGB uses the original texture-alpha weight while stage0 alpha varies.
// PM RGB uses the original texture alpha while independent D3D9
// BLENDTEXTUREALPHA alpha interpolates TEXTURE.a and DIFFUSE/CURRENT.a.
float4 PSTextureBlendTextureAlphaPMBlendTextureAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),
                      lerp(v.diffuse.a, t.a, t.a));
    AlphaGate(c.a); return c;
}
// Texture-alpha PM RGB with separately DIFFUSE/CURRENT-weighted alpha.
float4 PSTextureBlendTextureAlphaPMBlendDiffuseAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),
                      lerp(v.diffuse.a, t.a, v.diffuse.a));
    AlphaGate(c.a); return c;
}
// 00641: Stage0 CURRENT.a is vertex diffuse.a; PM RGB retains texture alpha.
float4 PSTextureBlendTextureAlphaPMBlendCurrentFactorAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),
                      lerp(alphaParams.w, t.a, v.diffuse.a));
    AlphaGate(c.a); return c;
}
// PM RGB uses texture alpha; stage0 BLENDFACTORALPHA interpolates alpha with
// the high-byte of live D3DRS_TEXTUREFACTOR, not with the texture A weight.
float4 PSTextureBlendTextureAlphaPMBlendFactorAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),
                      lerp(v.diffuse.a, t.a, alphaParams.w));
    AlphaGate(c.a); return c;
}
float4 PSTextureBlendTextureAlphaPMAddSmoothAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),
                      saturate(t.a + v.diffuse.a * (1.0f - t.a)));
    AlphaGate(c.a); return c;
}
float4 PSTextureBlendTextureAlphaPMModulate2XAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),
                      saturate(2.0f * t.a * v.diffuse.a));
    AlphaGate(c.a); return c;
}
// Texture-alpha PM RGB with a separate saturated MODULATE4X alpha.
float4 PSTextureBlendTextureAlphaPMModulate4XAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),
                      saturate(4.0f * t.a * v.diffuse.a));
    AlphaGate(c.a); return c;
}
// PM RGB and independently sourced stage0 TFACTOR alpha.// Texture-alpha PM RGB with independently signed-add stage0 alpha.
// D3DTOP_ADDSIGNED = saturate(ARG1 + ARG2 - 0.5); RGB still uses original t.a.
float4 PSTextureBlendTextureAlphaPMAddSignedAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),
                      saturate(t.a + v.diffuse.a - 0.5f));
    AlphaGate(c.a); return c;
}
// D3DTOP_ADDSIGNED2X doubles alpha's signed sum prior to saturation.
// Premultiplied RGB retains its original texture-alpha weight.
float4 PSTextureBlendTextureAlphaPMAddSigned2XAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),
                      saturate(2.0f * (t.a + v.diffuse.a - 0.5f)));
    AlphaGate(c.a); return c;
}

// PM RGB preserves the sampled alpha weighting while stage-0 MODULATE
// independently consumes TEXTURE and the live game's TFACTOR alpha byte.
float4 PSTextureBlendTextureAlphaPMModulateFactorAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),
                      saturate(t.a * alphaParams.w));
    AlphaGate(c.a); return c;
}
// Stage0 ADD and ADDSMOOTH consume game-authored TFACTOR alpha independently
// from the original sampled alpha that determines premultiplied RGB.
float4 PSTextureBlendTextureAlphaPMAddFactorAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),
                      saturate(t.a + alphaParams.w));
    AlphaGate(c.a); return c;
}
float4 PSTextureBlendTextureAlphaPMAddSmoothFactorAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),
                      saturate(t.a + alphaParams.w * (1.0f - t.a)));
    AlphaGate(c.a); return c;
}
// Preserve PM RGB texture-alpha weighting; signed alpha is game factor-sourced.
float4 PSTextureBlendTextureAlphaPMSignedFactorAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),
                      saturate(t.a + alphaParams.w - 0.5f));
    AlphaGate(c.a); return c;
}
float4 PSTextureBlendTextureAlphaPMSigned2XFactorAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),
                      saturate(2.0f * (t.a + alphaParams.w - 0.5f)));
    AlphaGate(c.a); return c;
}
float4 PSTextureBlendTextureAlphaPMSelectFactorAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)), alphaParams.w);
    AlphaGate(c.a); return c;
}
// SELECTARG1(TEXTURE|COMPLEMENT) inverts alpha but leaves PM RGB using original t.a.
float4 PSTextureBlendTextureAlphaPMSelectInverseTextureAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)), 1.0f - t.a);
    AlphaGate(c.a); return c;
}
// Only stage0 CURRENT aliases vertex DIFFUSE. Complement vertex alpha
// independently of the original texture-alpha-weighted premultiplied RGB.
float4 PSTextureBlendTextureAlphaPMSelectInverseDiffuseAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)), 1.0f - v.diffuse.a);
    AlphaGate(c.a); return c;
}
float4 PSTextureBlendTextureAlphaPMSelectDiffuseAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)), v.diffuse.a);
    AlphaGate(c.a); return c;
}
// Stage0 SELECTARG2 uses DIFFUSE/CURRENT RGB while alpha independently
// MODULATE2X/4X multiplies texture/vertex alpha, saturating before AlphaGate.
float4 PSTextureSelectDiffuseModulate2XAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(v.diffuse.rgb, saturate(2.0f * t.a * v.diffuse.a));
    AlphaGate(c.a); return c;
}
float4 PSTextureSelectDiffuseModulate4XAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(v.diffuse.rgb, saturate(4.0f * t.a * v.diffuse.a));
    AlphaGate(c.a); return c;
}

// Stage0 SELECTARG1 RGB stays texture; 2x/4x alpha is independent and saturated.
float4 PSTextureSelectTextureModulate2XAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(t.rgb, saturate(2.0f * t.a * v.diffuse.a));
    AlphaGate(c.a); return c;
}
float4 PSTextureSelectTextureModulate4XAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(t.rgb, saturate(4.0f * t.a * v.diffuse.a));
    AlphaGate(c.a); return c;
}
 // D3D9 ADDSMOOTH alpha: Arg1 + Arg2 * (1 - Arg1); RGB remains independent.
float4 PSTextureSelectTextureAddSmoothAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(t.rgb, saturate(t.a + v.diffuse.a * (1.0f - t.a)));
    AlphaGate(c.a); return c;
}
float4 PSTextureSelectDiffuseAddSmoothAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(v.diffuse.rgb, saturate(t.a + v.diffuse.a * (1.0f - t.a)));
    AlphaGate(c.a); return c;
}
// RGB SELECTARG1/2 is independent of stage0 BLENDFACTORALPHA alpha.
// BLENDFACTORALPHA uses the texture factor A byte, not the sampled A byte.
float4 PSTextureSelectTextureFactorAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(t.rgb, lerp(v.diffuse.a, t.a, alphaParams.w));
    AlphaGate(c.a); return c;
}
float4 PSTextureSelectDiffuseFactorAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(v.diffuse.rgb, lerp(v.diffuse.a, t.a, alphaParams.w));
    AlphaGate(c.a); return c;
}
// SELECTARG texture/diffuse RGB keeps independent D3D9 BLENDTEXTUREALPHA.
// Texture alpha is the interpolation weight even when alpha ARG1=TEXTURE.
float4 PSTextureSelectTextureBlendTextureAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(t.rgb, lerp(v.diffuse.a, t.a, t.a));
    AlphaGate(c.a); return c;
}
float4 PSTextureSelectDiffuseBlendTextureAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(v.diffuse.rgb, lerp(v.diffuse.a, t.a, t.a));
    AlphaGate(c.a); return c;
}
// Stage-0 SELECTARG RGB with independent alpha ARG1=TFACTOR, not texture alpha.
float4 PSTextureSelectTextureTfactorAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(t.rgb, alphaParams.w);
    AlphaGate(c.a); return c;
}
float4 PSTextureSelectDiffuseTfactorAlpha(VOut v) : SV_Target {
    float4 c = float4(v.diffuse.rgb, alphaParams.w);
    AlphaGate(c.a); return c;
}
// D3D9 SELECTARG RGB with independently diffuse-alpha-weighted output alpha.
float4 PSTextureSelectTextureBlendDiffuseAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(t.rgb, lerp(v.diffuse.a, t.a, v.diffuse.a));
    AlphaGate(c.a); return c;
}
float4 PSTextureSelectDiffuseBlendDiffuseAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(v.diffuse.rgb, lerp(v.diffuse.a, t.a, v.diffuse.a));
    AlphaGate(c.a); return c;
}
)";
struct NativeVertex {
    float clip[4];
    float diffuse[4];
    float uv[2];
    float specular[4]; // Packed D3D9 FVF SPECULAR, never aliased with DIFFUSE.
    float uvStage1[2]; // Independently selected and COUNT2-transformed game Stage1 UV.
};

// Narrow fixed-function stage-0 textured subset for real game menu/vehicle/race
// draws. Any unmirrored texture, sampler, alpha or stage state fails closed.
struct TextureCapture {
    bool enabled = false;
    // Source FVF contains UVs, but the verified stage-0 RGB/alpha shader
    // consumes DIFFUSE only and stage 1 is disabled. Never sample the stale
    // D3D9 texture; keep physical VB/IB byte offsets from the full FVF.
    bool inactiveStage0TextureBypass = false;
    bool stage1Enabled = false;
    bool stage1TextureOperands = false; // Stage1 D3DTA_TEXTURE in actual RGB/alpha operands.
    ComPtr<IDirect3DTexture9> stage1SeparateTexture; // Independent live D3D9 texture/sampler -> native t1/s1.
    // ADDRESSU/V/W, BORDER, MAG, MIN, MIP, LODBIAS, MAXMIP, ANISO, SRGB.
    std::array<DWORD, 11> stage1SamplerStates{};
    bool stage1IndependentSampler = false; // Same texture can still need a distinct native s1.
    UINT stage1CoordIndex = 0u; // D3DTSS_TEXCOORDINDEX(1), independent of Stage0.
    bool stage1TransformUv = false;
    D3DMATRIX stage1UvTransform{};
    bool stage0ResultTemp = false; // RESULTARG=TEMP, CURRENT remains vertex DIFFUSE.
    bool stage0FullModulate = false;
    DWORD stage1ColorOp = D3DTOP_DISABLE;
    DWORD stage1AlphaOp = D3DTOP_DISABLE;
    std::array<DWORD, 4> stage1Args{};
    std::array<DWORD, 2> stage1ArgZero{}; // COLORARG0, ALPHAARG0 for 25/26
    std::array<float, 4> stage1Factor{};
    std::array<float, 4> stage1Constant{};

    bool selectTexture = false;
    bool selectTextureDiffuseAlpha = false;
    bool selectTextureModulateAlpha = false;
    bool selectTextureModulate2XAlpha = false;
    bool selectTextureModulate4XAlpha = false;
    bool selectTextureAddAlpha = false;
    bool selectTextureSubtractAlpha = false;
    bool selectTextureAddSmoothAlpha = false;
    bool selectTextureFactorAlpha = false;
    bool selectTextureTfactorAlpha = false;
    bool selectTextureTfactorArg2Alpha = false;
    bool selectTextureBlendTextureAlpha = false;
    bool selectDiffuseTextureAlpha = false;
    bool selectDiffuseDiffuseAlpha = false;
    bool selectDiffuseModulateAlpha = false;
    bool selectDiffuseAddAlpha = false;
    bool selectDiffuseSubtractAlpha = false;
    bool selectDiffuseModulate2XAlpha = false;
    bool selectDiffuseModulate4XAlpha = false;
    bool selectDiffuseAddSmoothAlpha = false;
    bool selectDiffuseFactorAlpha = false;
    bool selectDiffuseTfactorAlpha = false;
    bool selectDiffuseTfactorArg2Alpha = false;
    bool selectDiffuseBlendTextureAlpha = false;
    bool selectTextureBlendDiffuseAlpha = false;
    bool selectDiffuseBlendDiffuseAlpha = false;
    bool additive = false;
    bool subtract = false;
    bool subtractTextureAlpha = false;
    bool subtractDiffuseAlpha = false;
    bool subtractModulateAlpha = false;
    bool addSmooth = false;
    bool addSmoothTextureAlpha = false;
    bool addSmoothDiffuseAlpha = false;
    bool modulate2x = false;
    bool modulate4x = false;
    bool modulate2xTextureAlpha = false;
    bool modulate2xDiffuseAlpha = false;
    bool modulate4xTextureAlpha = false;
    bool modulate4xDiffuseAlpha = false;
    bool mixedTextureAlpha = false;
    bool mixedDiffuseAlpha = false;
    bool mixedAddTextureAlpha = false;
    bool mixedAddDiffuseAlpha = false;
    bool blendTextureAlpha = false;
    bool blendTextureAlphaPM = false;
    bool blendTextureAlphaPMTextureAlpha = false;
    bool blendTextureAlphaPMInverseTextureAlpha = false;
    bool blendTextureAlphaPMInverseDiffuseAlpha = false;
    bool blendTextureAlphaPMDiffuseAlpha = false;
    bool blendTextureAlphaPMFactorAlpha = false;
    bool blendTextureAlphaPMModulateFactorAlpha = false;
    bool blendTextureAlphaPMSignedFactorAlpha = false;
    bool blendTextureAlphaPMAddFactorAlpha = false;
    bool blendTextureAlphaPMAddSmoothFactorAlpha = false;
    bool blendTextureAlphaPMSigned2XFactorAlpha = false;
    bool blendTextureAlphaPMModulateAlpha = false;
    bool blendTextureAlphaPMAddAlpha = false;
    bool blendTextureAlphaPMSubtractAlpha = false;
    bool blendTextureAlphaPMModulate2XAlpha = false;
    bool blendTextureAlphaPMModulate4XAlpha = false;
    bool blendTextureAlphaPMAddSignedAlpha = false;
    bool blendTextureAlphaPMAddSigned2XAlpha = false;
    bool blendTextureAlphaPMBlendTextureAlpha = false;
    bool blendTextureAlphaPMBlendDiffuseAlpha = false;
    bool blendTextureAlphaPMBlendCurrentFactorAlpha = false;
    bool blendTextureAlphaPMBlendFactorAlpha = false;
    bool blendTextureAlphaPMAddSmoothAlpha = false;
    bool blendDiffuseAlpha = false;
    bool blendTextureSelectedTextureAlpha = false;
    bool blendTextureSelectedDiffuseAlpha = false;
    bool blendDiffuseSelectedTextureAlpha = false;
    bool blendDiffuseSelectedDiffuseAlpha = false;
    bool blendTextureModulateAlpha = false;
    bool blendDiffuseModulateAlpha = false;
    bool blendTextureModulate2XAlpha = false;
    bool blendTextureModulate4XAlpha = false;
    bool blendDiffuseModulate2XAlpha = false;
    bool blendDiffuseModulate4XAlpha = false;
    bool blendTextureAddAlpha = false;
    bool blendDiffuseAddAlpha = false;
    bool blendTextureSubtractAlpha = false;
    bool blendDiffuseSubtractAlpha = false;
    bool blendTextureAddSmoothAlpha = false;
    bool blendDiffuseAddSmoothAlpha = false;
    bool blendFactorAlpha = false;
    bool blendFactorTextureAlpha = false;
    bool blendFactorModulateAlpha = false;
    bool blendFactorDiffuseAlpha = false;
    bool blendFactorAddAlpha = false;
    bool blendFactorSubtractAlpha = false;
    bool blendFactorAddSmoothAlpha = false;
    bool blendFactorModulate2XAlpha = false;
    bool blendFactorModulate4XAlpha = false;
    float blendFactorAlphaValue = 0.0f;
    UINT coordIndex = 0;
    bool transformUv = false; // Live D3D9 stage0 COUNT2 texture0 transform.
    D3DMATRIX uvTransform{};
    Microsoft::WRL::ComPtr<IDirect3DTexture9> texture;
    D3DTEXTUREADDRESS addressU = D3DTADDRESS_CLAMP;
    D3DTEXTUREADDRESS addressV = D3DTADDRESS_CLAMP;
    DWORD borderColor = 0u; // Live game D3D9 sampler ARGB.
    D3DTEXTUREFILTERTYPE minFilter = D3DTEXF_POINT;
    D3DTEXTUREFILTERTYPE magFilter = D3DTEXF_POINT;
    D3DTEXTUREFILTERTYPE mipFilter = D3DTEXF_NONE;
    DWORD maxAnisotropy = 1u; // Captured live game D3D9 anisotropy.
    bool srgbTexture = false; // Game D3DSAMP_SRGBTEXTURE: native SRGB SRV decode.
    DWORD maxMipLevel = 0u;  // D3D9's most detailed permitted mip for MIN sampling.
    float mipLodBias = 0.0f; // Signed game-authored MIPMAPLODBIAS (IEEE-754).
};

struct OutputCapture {
    bool alphaBlend = false;
    bool additiveBlend = false; // D3D9 ONE/ONE
    bool sourceAlphaAddBlend = false; // D3D9 SRCALPHA/ONE
    bool premultipliedAlphaBlend = false; // D3D9 ONE/INVSRCALPHA
    bool inverseSourceAlphaBlend = false; // Game D3D9 BOTHINVSRCALPHA
    bool sourceAlphaCopyBlend = false; // D3D9 SRCALPHA/ZERO: source attenuated, destination discarded
    bool inverseAlphaCopyBlend = false; // D3D9 INVSRCALPHA/ZERO
    bool inverseAlphaAddBlend = false; // D3D9 INVSRCALPHA/ONE
    bool sourceReplaceBlend = false; // D3D9 ONE/ZERO: exact RGB + alpha source overwrite
    bool multiplyBlend = false; // D3D9 DESTCOLOR/ZERO or ZERO/SRCCOLOR
    bool inverseDestMultiplyBlend = false; // D3D9 INVDESTCOLOR/ZERO
    bool inverseSourceMultiplyBlend = false; // D3D9 ZERO/INVSRCCOLOR
    bool destAlphaCrossfadeBlend = false; // DESTALPHA / INVDESTALPHA
    bool reverseDestAlphaCrossfadeBlend = false; // INVDESTALPHA / DESTALPHA
    bool sourceAlphaSaturateCopyBlend = false; // SRCALPHASAT/ZERO
    bool sourceAlphaSaturateAddBlend = false; // SRCALPHASAT/ONE
    D3D11_BLEND_OP blendOp = D3D11_BLEND_OP_ADD; // Captured D3D9 RGB operation.
    bool separateAlphaBlend = false;
    D3D11_BLEND nativeSrcAlpha = D3D11_BLEND_ONE;
    D3D11_BLEND nativeDstAlpha = D3D11_BLEND_ZERO;
    D3D11_BLEND_OP nativeAlphaOp = D3D11_BLEND_OP_ADD;
    bool alphaTest = false;
    bool nativeDepthTest = false;
    bool nativeDepthLessEqual = false;
    bool nativeDepthWrite = false;
    bool nativeDepthAlways = false;
    std::uint32_t nativeDepthEqualityMode = 0u;
    std::uint32_t nativeDepthOrderingMode = 0u;
    DWORD nativeCullMode = D3DCULL_NONE; // live game face exclusion
    DWORD alphaRef = 0;
    D3DCMPFUNC alphaFunc = D3DCMP_ALWAYS;
    bool scissor = false;
    D3D11_RECT nativeScissor{};
    D3D11_VIEWPORT nativeViewport{}; // Original game backbuffer-relative raster region.
    UINT nativeWidth = kWidth, nativeHeight = kHeight;
    std::uintptr_t targetIdentity = 0u; // Live source RT0 IUnknown.
    // Only source RGB-visible masks are eligible for the diagnostic inset.
    std::uint8_t colorWriteMask = D3D11_COLOR_WRITE_ENABLE_ALL;
};

// Native pixel-shader stage-1 combiner uses an 80-byte, 16-byte-aligned
// D3D11 b1 payload across live menu, vehicle-select and race draws.
struct Stage1Upload {
    float factor[4];
    std::int32_t operations[4];
    std::int32_t arguments[4];
    std::int32_t argZero[4];
    float stageConstant[4];
};
static_assert(sizeof(Stage1Upload) == 80u && sizeof(Stage1Upload) % 16u == 0u,
              "Native game stage-1 constant buffer ABI must match PS b1");

struct ReadbackSlot {
    ComPtr<ID3D11Texture2D> staging;
    ComPtr<ID3D11Query> fence;
    bool busy = false;
    // A failed GPU EVENT query cannot prove that the asynchronous CopyResource
    // stopped writing. Keep this staging allocation out of the free ring until
    // a real source-device Reset recreates the entire readback pipeline.
    bool quarantined = false;
    // A completed EVENT does not prove CPU Map(DO_NOT_WAIT) succeeded.
    // Keep this slot GPU/CPU-owned until its pending Map can be retired
    // on a later Present, without ever uploading that stale game image.
    bool mapPending = false;
    bool completeFullFrame = false;
    GameReadbackProvenance provenance{};
};
struct LiveSm3Pipeline {
    NativeLiveSm3Program program;
    ComPtr<ID3D11InputLayout> inputLayout;
    ComPtr<ID3D11Buffer> vertexConstants;
    ComPtr<ID3D11Buffer> pixelConstants;
    ComPtr<ID3D11Buffer> alphaReference;
    unsigned alphaCompare{};
    std::vector<DWORD> vertexTokens, pixelTokens;
    std::vector<D3DVERTEXELEMENT9> declaration;
};
struct State {
    std::mutex mutex;
    // Shader bytecode+declaration keyed cache is bound to this backend's
    // exact D3D11 device lifetime, and discarded on source Reset.
    std::unordered_map<std::uint64_t, LiveSm3Pipeline> liveSm3Pipelines;
    std::unordered_map<std::uint64_t, ComPtr<ID3D11BlendState>> liveSm3BlendStates;
    // Non-owning identity only: reset at every Present/Reset. Never retain a
    // game D3D9 COM object or mix different device Draw calls in one GPU batch.
    std::uintptr_t sourceGameDevice = 0u;
    GameOutputSignature previousOutput{};
    GameNativeClearColor clearColor{};
    GameNativePreDrawFills preDrawFills{};
    std::uint64_t outputGeneration = 0u;
    // Successful game StretchRect/UpdateSurface postpasses are replayed into
    // the real full-size native texture, never treated as geometry Draws.
    // This bounded diagnostic compatibility path reads the CURRENT original
    // D3D9 backbuffer, then GPU-copies only the affected region. It does not
    // falsely claim zero-copy D3D9->D3D11 or native offscreen Draw parity.
    ComPtr<IDirect3DSurface9> surfaceReplayReadback;
    std::uintptr_t surfaceReplayOwner = 0u;
    UINT surfaceReplayWidth = 0u, surfaceReplayHeight = 0u;
    D3DFORMAT surfaceReplayFormat = D3DFMT_UNKNOWN;
    ComPtr<ID3D11Texture2D> surfaceReplayScratch;
    ComPtr<ID3D11Device> surfaceReplayScratchDevice;
    UINT surfaceReplayScratchWidth = 0u, surfaceReplayScratchHeight = 0u;
    std::vector<std::uint8_t> surfaceReplayPixels;
    std::uint32_t surfaceReplayCount = 0u;
    GameNativeCpuSurfaceTicket cpuSurfaceReplay{};
    NativeBackend backend;
    // Persistent native D3D11 upload buffers for a whole real game frame.
    // Re-upload every Draw to preserve game-authored mutable VB/IB content.
    ComPtr<ID3D11Buffer> fullGameVertexUpload;
    ComPtr<ID3D11Buffer> fullGameIndexUpload;
    UINT fullGameVertexCapacity = 0u;
    UINT fullGameIndexCapacity = 0u;
    UINT nativeWidth = 0u, nativeHeight = 0u;
    // Diagnostic-only depth is never shared with the original D3D9 renderer.
    ComPtr<ID3D11Texture2D> diagnosticDepth;
    ComPtr<ID3D11DepthStencilView> diagnosticDepthView;
    std::array<ComPtr<ID3D11DepthStencilState>, 4> diagnosticDepthStates;
    // Independent ALWAYS depth-write OFF/ON states.
    std::array<ComPtr<ID3D11DepthStencilState>, 2> diagnosticDepthAlwaysStates;
    // EQUAL/NOTEQUAL each preserve both depth-write modes independently.
    std::array<ComPtr<ID3D11DepthStencilState>, 4> diagnosticDepthEqualityStates;
    // GREATER / GREATEREQUAL x Z-write, distinct from equality states.
    std::array<ComPtr<ID3D11DepthStencilState>, 4> diagnosticDepthOrderingStates;
    ComPtr<ID3D11VertexShader> vs;
    ComPtr<ID3D11PixelShader> ps;
    ComPtr<ID3D11PixelShader> sampledPs;
    ComPtr<ID3D11PixelShader> stage1DiffusePs;
    ComPtr<ID3D11PixelShader> stage1ModulatePs;
    ComPtr<ID3D11PixelShader> stage1TextureOnlyPs;
    ComPtr<ID3D11PixelShader> stage1AddPs;
    ComPtr<ID3D11PixelShader> textureOnlyPs;
    ComPtr<ID3D11PixelShader> selectTextureDiffuseAlphaPs;
    ComPtr<ID3D11PixelShader> selectTextureModulateAlphaPs;
    ComPtr<ID3D11PixelShader> selectTextureModulate2XAlphaPs;
    ComPtr<ID3D11PixelShader> selectTextureModulate4XAlphaPs;
    ComPtr<ID3D11PixelShader> selectTextureAddAlphaPs;
    ComPtr<ID3D11PixelShader> selectTextureSubtractAlphaPs;
    ComPtr<ID3D11PixelShader> selectTextureAddSmoothAlphaPs;
    ComPtr<ID3D11PixelShader> selectTextureFactorAlphaPs;
    ComPtr<ID3D11PixelShader> selectTextureTfactorAlphaPs;
    ComPtr<ID3D11PixelShader> selectTextureBlendTextureAlphaPs;
    ComPtr<ID3D11PixelShader> selectDiffuseTextureAlphaPs;
    ComPtr<ID3D11PixelShader> selectDiffuseModulateAlphaPs;
    ComPtr<ID3D11PixelShader> selectDiffuseAddAlphaPs;
    ComPtr<ID3D11PixelShader> selectDiffuseSubtractAlphaPs;
    ComPtr<ID3D11PixelShader> selectDiffuseModulate2XAlphaPs;
    ComPtr<ID3D11PixelShader> selectDiffuseModulate4XAlphaPs;
    ComPtr<ID3D11PixelShader> selectDiffuseAddSmoothAlphaPs;
    ComPtr<ID3D11PixelShader> selectDiffuseFactorAlphaPs;
    ComPtr<ID3D11PixelShader> selectDiffuseTfactorAlphaPs;
    ComPtr<ID3D11PixelShader> selectDiffuseBlendTextureAlphaPs;
    ComPtr<ID3D11PixelShader> selectTextureBlendDiffuseAlphaPs;
    ComPtr<ID3D11PixelShader> selectDiffuseBlendDiffuseAlphaPs;
    ComPtr<ID3D11PixelShader> additivePs;
    ComPtr<ID3D11PixelShader> subtractPs;
    ComPtr<ID3D11PixelShader> subtractTextureAlphaPs;
    ComPtr<ID3D11PixelShader> subtractDiffuseAlphaPs;
    ComPtr<ID3D11PixelShader> subtractModulateAlphaPs;
    ComPtr<ID3D11PixelShader> addSmoothPs;
    ComPtr<ID3D11PixelShader> addSmoothTextureAlphaPs;
    ComPtr<ID3D11PixelShader> addSmoothDiffuseAlphaPs;
    ComPtr<ID3D11PixelShader> modulate2xPs;
    ComPtr<ID3D11PixelShader> modulate4xPs;
    ComPtr<ID3D11PixelShader> modulate2xTextureAlphaPs;
    ComPtr<ID3D11PixelShader> modulate2xDiffuseAlphaPs;
    ComPtr<ID3D11PixelShader> modulate4xTextureAlphaPs;
    ComPtr<ID3D11PixelShader> modulate4xDiffuseAlphaPs;
    ComPtr<ID3D11PixelShader> mixedTextureAlphaPs;
    ComPtr<ID3D11PixelShader> mixedDiffuseAlphaPs;
    ComPtr<ID3D11PixelShader> mixedAddTextureAlphaPs;
    ComPtr<ID3D11PixelShader> mixedAddDiffuseAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPmPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPmTextureAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPmInverseTextureAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPmInverseDiffuseAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPmDiffuseAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPmFactorAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPmModulateFactorAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPmSignedFactorAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPmAddFactorAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPmAddSmoothFactorAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPmSigned2XFactorAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPmModulateAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPmAddAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPmSubtractAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPmModulate2XAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPmModulate4XAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPmAddSignedAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPmAddSigned2XAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPmBlendTextureAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPmBlendDiffuseAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPmBlendCurrentFactorAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPmBlendFactorAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAlphaPmAddSmoothAlphaPs;
    ComPtr<ID3D11PixelShader> blendDiffuseAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureSelectedTextureAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureSelectedDiffuseAlphaPs;
    ComPtr<ID3D11PixelShader> blendDiffuseSelectedTextureAlphaPs;
    ComPtr<ID3D11PixelShader> blendDiffuseSelectedDiffuseAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureModulateAlphaPs;
    ComPtr<ID3D11PixelShader> blendDiffuseModulateAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureModulate2XAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureModulate4XAlphaPs;
    ComPtr<ID3D11PixelShader> blendDiffuseModulate2XAlphaPs;
    ComPtr<ID3D11PixelShader> blendDiffuseModulate4XAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAddAlphaPs;
    ComPtr<ID3D11PixelShader> blendDiffuseAddAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureSubtractAlphaPs;
    ComPtr<ID3D11PixelShader> blendDiffuseSubtractAlphaPs;
    ComPtr<ID3D11PixelShader> blendTextureAddSmoothAlphaPs;
    ComPtr<ID3D11PixelShader> blendDiffuseAddSmoothAlphaPs;
    ComPtr<ID3D11PixelShader> blendFactorAlphaPs;
    ComPtr<ID3D11PixelShader> blendFactorTextureAlphaPs;
    ComPtr<ID3D11PixelShader> blendFactorModulateAlphaPs;
    ComPtr<ID3D11PixelShader> blendFactorDiffuseAlphaPs;
    ComPtr<ID3D11PixelShader> blendFactorAddAlphaPs;
    ComPtr<ID3D11PixelShader> blendFactorSubtractAlphaPs;
    ComPtr<ID3D11PixelShader> blendFactorAddSmoothAlphaPs;
    ComPtr<ID3D11PixelShader> blendFactorModulate2XAlphaPs;
    ComPtr<ID3D11PixelShader> blendFactorModulate4XAlphaPs;
    ComPtr<ID3D11InputLayout> layout;
    ComPtr<ID3D11RasterizerState> raster;
    ComPtr<ID3D11RasterizerState> scissorRaster;
    // CW/CCW triangle raster x diagnostic scissor OFF/ON.
    std::array<ComPtr<ID3D11RasterizerState>, 4> diagnosticCullRasters;
    ComPtr<ID3D11BlendState> alphaBlend;
    ComPtr<ID3D11BlendState> additiveBlend;
    ComPtr<ID3D11BlendState> sourceAlphaAddBlend;
    ComPtr<ID3D11BlendState> premultipliedAlphaBlend;
    ComPtr<ID3D11BlendState> inverseSourceAlphaBlend;
    ComPtr<ID3D11BlendState> sourceAlphaCopyBlend;
    ComPtr<ID3D11BlendState> inverseAlphaCopyBlend;
    ComPtr<ID3D11BlendState> inverseAlphaAddBlend;
    ComPtr<ID3D11BlendState> sourceReplaceBlend;
    ComPtr<ID3D11BlendState> multiplyBlend;
    ComPtr<ID3D11BlendState> inverseDestMultiplyBlend;
    ComPtr<ID3D11BlendState> inverseSourceMultiplyBlend;
    ComPtr<ID3D11BlendState> destAlphaCrossfadeBlend;
    ComPtr<ID3D11BlendState> reverseDestAlphaCrossfadeBlend;
    ComPtr<ID3D11BlendState> sourceAlphaSaturateCopyBlend;
    ComPtr<ID3D11BlendState> sourceAlphaSaturateAddBlend;
    // Opaque/over/additive/source-alpha-add/premultiplied, 16 masks each.
    std::array<ComPtr<ID3D11BlendState>, 80> maskedBlends{};
    // Distinct destination-dependent blend cache; do not alias older mask slots.
    std::array<ComPtr<ID3D11BlendState>, 16> multiplyMaskedBlends{};
    std::array<ComPtr<ID3D11BlendState>, 16> inverseDestMultiplyMaskedBlends{};
    std::array<ComPtr<ID3D11BlendState>, 16> inverseSourceMultiplyMaskedBlends{};
    std::array<ComPtr<ID3D11BlendState>, 16> destAlphaCrossfadeMaskedBlends{};
    std::array<ComPtr<ID3D11BlendState>, 16> reverseDestAlphaCrossfadeMaskedBlends{};
    std::array<ComPtr<ID3D11BlendState>, 16> sourceAlphaSaturateCopyMaskedBlends{};
    std::array<ComPtr<ID3D11BlendState>, 16> sourceAlphaSaturateAddMaskedBlends{};
    std::array<ComPtr<ID3D11BlendState>, 16> inverseSourceAlphaMaskedBlends{};
    std::array<ComPtr<ID3D11BlendState>, 16> sourceAlphaCopyMaskedBlends{};
    std::array<ComPtr<ID3D11BlendState>, 16> inverseAlphaCopyMaskedBlends{};
    std::array<ComPtr<ID3D11BlendState>, 16> inverseAlphaAddMaskedBlends{};
    std::array<ComPtr<ID3D11BlendState>, 16> sourceReplaceMaskedBlends{};
    // Four admitted factor pairs x subtract/reverse-subtract x 16 write masks.
    // Create on demand; never alias normal ADD or multiply blend descriptors.
    std::array<ComPtr<ID3D11BlendState>, 128> subtractiveMaskedBlends{};
    // D3D9 MIN/MAX game/menu blending has separate native OM cache slots:
    // never collide with SUBTRACT/REVSUBTRACT under changing color masks.
    std::array<ComPtr<ID3D11BlendState>, 128> extremumMaskedBlends{};
    ComPtr<ID3D11Buffer> alphaConstants;
    // Per-device mutable b1 state; changed game combiners update before
    // each Draw instead of creating thousands of immutable GPU objects.
    ComPtr<ID3D11Buffer> stage1Constants;
    std::array<ReadbackSlot, kReadbackSlots> readbacks{};
    UINT readSlot = 0;
    UINT writeSlot = 0;
    UINT droppedCopies = 0;
    std::uint64_t staleReadbacks = 0;
    ComPtr<IDirect3DSurface9> insetSurface;
    D3DFORMAT insetFormat = D3DFMT_UNKNOWN;
    std::uintptr_t insetSurfaceDevice = 0u;
    // D3D9 SYSTEMMEM uploads are dimension-owned independently of their format.
    UINT insetSurfaceWidth = 0u, insetSurfaceHeight = 0u;
    bool pending = false;
    NativeSharedDesktopBridge sharedDesktop;
    NativeGameCpuUploadTransaction cpuUploadRollback;
    NativeFullGameGpuSink gpuFrameSink = nullptr;
    void* gpuFrameSinkUser = nullptr;
    GameNativeFrameBatch frameBatch{}; // Opt-in native only, original D3D9/input preserved.
    bool logged = false;
    UINT observed = 0;
    std::uint64_t presents = 0;
    std::uint64_t eligible = 0;
    UINT eligibleThisFrame = 0;
    std::uint64_t sourceDrawsThisFrame = 0u;
    bool sourceModeKnown = false;
    bool sourceWasFullMode = false;
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

bool env_full_game_opt_in() noexcept {
    wchar_t value[8]{};
    return env_opt_in() &&
        GetEnvironmentVariableW(L"OUTRUN_DX11_FULL_GAME_FRAME", value, 8) == 1 &&
        value[0] == L'1';
}
bool env_shared_desktop_opt_in() noexcept {
    wchar_t value[8]{};
    return env_full_game_opt_in() &&
        GetEnvironmentVariableW(L"OUTRUN_DX11_GPU_SHARED_DESKTOP", value, 8) == 1 &&
        value[0] == L'1';
}
bool env_batch_opt_in() noexcept {
    wchar_t value[8]{};
    // Requires primary diagnostic opt-in in the outer capture path.
    return GetEnvironmentVariableW(L"OUTRUN_DX11_FRAME_BATCH", value, 8) == 1
        && value[0] == L'1';
}

constexpr char kStage1FactorShader[] = R"(
Texture2D stage1GameTexture : register(t1);
SamplerState stage1GameSampler : register(s1);
// Stage 1 accepts raw vertex DIFFUSE/SPECULAR, stage-0 CURRENT and TFACTOR with
// D3DTA_COMPLEMENT/ALPHAREPLICATE. Unsupported sources
// are CPU-rejected before either native Draw or DrawIndexed is submitted.
// Separate RGB and alpha instructions run before native alpha-test/OM blend.
cbuffer Stage1FactorParams : register(b1) {
    float4 stage1Factor;
    int4 stage1Ops;  // color op, alpha op, reserved, reserved
    int4 stage1Args; // color arg1/2, alpha arg1/2
    int4 stage1ArgZero; // color arg0, alpha arg0, reserved, reserved
float4 stage1Constant; // D3DTSS_CONSTANT, not texture factor
};
float4 Stage1Source(float4 current, float4 diffuse, float4 specular, int source) {
    // D3DTA_MASK=0x0f; DIFFUSE=0, CURRENT=1, TFACTOR=3. CPU admission owns the
    // strict selector/flag allowlist. Apply alpha replication before optional
    // complement, identically for RGB and independent stage-1 alpha.
    float4 value = (source & 15) == 3 ? stage1Factor : current;
    if ((source & 15) == 0) value = diffuse;
    if ((source & 15) == 4) value = specular;
    if ((source & 15) == 6) value = stage1Constant;
    // Stage0 TEMP producer keeps CURRENT at the incoming DIFFUSE.
    // Stage1 TEMP sees the separately produced stage0 result.
    if ((source & 15) == 1 && stage1Ops.z != 0) value = diffuse;
    if ((source & 15) == 5) value = current;
    if ((source & 32) != 0) value = value.aaaa;
    if ((source & 16) != 0) value = 1.0f - value;
    return value;
}
float Stage1BlendWeight(int op, float4 stage0, float4 diffuse) {
    // D3DTOP_BLEND*: ARG1 * weight + ARG2 * (1 - weight).
    if (op == 12) return diffuse.a;       // BLENDDIFFUSEALPHA
    if (op == 14) return stage1Factor.a;  // BLENDFACTORALPHA
    if (stage1Ops.z != 0) return diffuse.a; // CURRENT from vertex after TEMP write.
    return stage0.a;                      // 16: BLENDCURRENTALPHA; CPU-gated
}
float4 Stage1Combine(float4 a, float4 b, int op, float4 stage0, float4 diffuse) {
    if (op == 2) return a;
    if (op == 3) return b;
    if (op == 4) return saturate(a * b);
    if (op == 5) return saturate(2.0f * a * b);
    if (op == 6) return saturate(4.0f * a * b);
    if (op == 7) return saturate(a + b);
    if (op == 8) return saturate(a + b - 0.5f);     // ADDSIGNED
    if (op == 9) return saturate(2.0f * (a + b - 0.5f)); // ADDSIGNED2X
    if (op == 10) return saturate(a - b);
    // D3D9 COLOROP-only 18..21: ARG1 alpha and RGB are distinct inputs.
    // The CPU gate rejects these operators from independent ALPHAOP.
    if (op == 18) return saturate(a + a.aaaa * b);
    if (op == 19) return saturate(a * b + a.aaaa);
    if (op == 20) return saturate(a + (1.0f - a.aaaa) * b);
    if (op == 21) return saturate((1.0f - a) * b + a.aaaa);
    if (op == 24) {
        // D3D9 signed DOTPRODUCT3: remap two RGB operands from [0,1] to [-1,1].
        // Its saturated scalar is RGB only; ALPHAOP below stays independent.
        float3 signedA = a.rgb * 2.0f - 1.0f;
        float3 signedB = b.rgb * 2.0f - 1.0f;
        float signedDot = saturate(dot(signedA, signedB));
        return float4(signedDot, signedDot, signedDot, signedDot);
    }
    if (op == 12 || op == 14 || op == 16)
        return saturate(lerp(b, a, Stage1BlendWeight(op, stage0, diffuse)));
    return saturate(a + b * (1.0f - a)); // 11: ADDSMOOTH, CPU-gated
}
// D3DTOP_MULTIPLYADD = ARG1 + ARG2*ARG0;
 // D3DTOP_LERP = ARG0*ARG1 + (1-ARG0)*ARG2.
 // The source selector resolves vertex/current/factor and complement/alpha
 // replicate for all three inputs, with the original D3D9 path as fallback.
float4 Stage1ThreeSource(float4 stage0, float4 diffuse, float4 specular,
                         int op, int arg0, int arg1, int arg2) {
    float4 a0 = Stage1Source(stage0, diffuse, specular, arg0);
    float4 a1 = Stage1Source(stage0, diffuse, specular, arg1);
    float4 a2 = Stage1Source(stage0, diffuse, specular, arg2);
    if (op == 25) return saturate(a1 + a2 * a0);
    return saturate(lerp(a2, a1, a0)); // 26, CPU-gated
}
float4 Stage1AndAlpha(float4 stage0, float4 diffuse, float4 specular,
                      float stage1TextureAlpha) {
    float4 color = Stage1Combine(
        Stage1Source(stage0, diffuse, specular, stage1Args.x),
        Stage1Source(stage0, diffuse, specular, stage1Args.y), stage1Ops.x, stage0, diffuse);
    if (stage1Ops.x == 25 || stage1Ops.x == 26)
        color = Stage1ThreeSource(stage0, diffuse, specular, stage1Ops.x,
                                  stage1ArgZero.x, stage1Args.x, stage1Args.y);
    // Only admitted when D3D9 stage 1 samples exactly the mirrored stage-0
    // texture at identical coordinates with identical sampling parameters.
    if (stage1Ops.x == 13)
        color = saturate(lerp(
            Stage1Source(stage0, diffuse, specular, stage1Args.y),
            Stage1Source(stage0, diffuse, specular, stage1Args.x),
            stage1TextureAlpha));
    // D3D9 premultiplied ARG1 is already weighted, unlike ordinary lerp.
    if (stage1Ops.x == 15) {
        float4 pmColor1 = Stage1Source(stage0, diffuse, specular, stage1Args.x);
        float4 pmColor2 = Stage1Source(stage0, diffuse, specular, stage1Args.y);
        color = saturate(pmColor1 + pmColor2 * (1.0f - stage1TextureAlpha));
    }
    float alpha = stage1Ops.y == 1 ?
        (stage1Ops.z != 0 ? diffuse.a : stage0.a) : Stage1Combine(
        Stage1Source(stage0, diffuse, specular, stage1Args.z),
        Stage1Source(stage0, diffuse, specular, stage1Args.w), stage1Ops.y, stage0, diffuse).a;
    if (stage1Ops.y == 25 || stage1Ops.y == 26)
        alpha = Stage1ThreeSource(stage0, diffuse, specular, stage1Ops.y,
                                  stage1ArgZero.y, stage1Args.z, stage1Args.w).a;
    if (stage1Ops.y == 13)
        alpha = saturate(lerp(
            Stage1Source(stage0, diffuse, specular, stage1Args.w),
            Stage1Source(stage0, diffuse, specular, stage1Args.z),
            stage1TextureAlpha)).a;
    // ALPHAOP reads separate D3D9 operands, never the RGB PM output alpha.
    if (stage1Ops.y == 15) {
        float4 pmAlpha1 = Stage1Source(stage0, diffuse, specular, stage1Args.z);
        float4 pmAlpha2 = Stage1Source(stage0, diffuse, specular, stage1Args.w);
        alpha = saturate(pmAlpha1 + pmAlpha2 * (1.0f - stage1TextureAlpha)).a;
    }
    float4 result = float4(color.rgb, alpha);
    AlphaGate(result.a);
    return result;
}
// Stage-1 TEXTURE operand reads an exact matched sample, including D3DTA flags.
// Keep the legacy non-texture stage-1 shader unchanged for proven draws.
float4 Stage1SourceTextured(float4 current, float4 diffuse, float4 specular,
                            float4 stage1TextureColor, int source) {
    if ((source & 15) != 2) return Stage1Source(current, diffuse, specular, source);
    float4 value = stage1TextureColor;
    value = (source & 32) != 0 ? value.aaaa : value;
    value = (source & 16) != 0 ? 1.0f - value : value;
    return value;
}
float4 Stage1ThreeSourceTextured(float4 current, float4 diffuse, float4 specular,
    float4 stage1TextureColor, int op, int arg0, int arg1, int arg2) {
    float4 a0 = Stage1SourceTextured(current,diffuse,specular,stage1TextureColor,arg0);
    float4 a1 = Stage1SourceTextured(current,diffuse,specular,stage1TextureColor,arg1);
    float4 a2 = Stage1SourceTextured(current,diffuse,specular,stage1TextureColor,arg2);
    return op == 25 ? saturate(a1 + a2 * a0) : saturate(lerp(a2, a1, a0));
}
float4 Stage1AndAlphaTextured(float4 stage0, float4 diffuse, float4 specular,
                      float stage1TextureAlpha, float4 stage1TextureColor) {
    float4 color = Stage1Combine(
        Stage1SourceTextured(stage0, diffuse, specular, stage1TextureColor, (stage1Args.x)),
        Stage1SourceTextured(stage0, diffuse, specular, stage1TextureColor, (stage1Args.y)), (stage1Ops.x), stage0, diffuse);
    if ((stage1Ops.x) == 25 || (stage1Ops.x) == 26)
        color = Stage1ThreeSourceTextured(stage0, diffuse, specular, stage1TextureColor, (stage1Ops.x),
                                  (stage1ArgZero.x), (stage1Args.x), (stage1Args.y));
    // Only admitted when D3D9 stage 1 samples exactly the mirrored stage-0
    // texture at identical coordinates with identical sampling parameters.
    if (13 == (stage1Ops.x))
        color = saturate(lerp(
            Stage1SourceTextured(stage0, diffuse, specular, stage1TextureColor, (stage1Args.y)),
            Stage1SourceTextured(stage0, diffuse, specular, stage1TextureColor, (stage1Args.x)),
            stage1TextureAlpha * 1.0f));
    // D3D9 premultiplied ARG1 is already weighted, unlike ordinary lerp.
    if (15 == (stage1Ops.x)) {
        float4 texturePmColor1 = Stage1SourceTextured(stage0, diffuse, specular, stage1TextureColor, (stage1Args.x));
        float4 texturePmColor2 = Stage1SourceTextured(stage0, diffuse, specular, stage1TextureColor, (stage1Args.y));
        color = saturate(texturePmColor1 + texturePmColor2 * (1.0f - stage1TextureAlpha * 1.0f));
    }
    float alpha = (stage1Ops.y) == 1 ?
        ((stage1Ops.z) != 0 ? diffuse.a : stage0.a) : Stage1Combine(
        Stage1SourceTextured(stage0, diffuse, specular, stage1TextureColor, (stage1Args.z)),
        Stage1SourceTextured(stage0, diffuse, specular, stage1TextureColor, (stage1Args.w)), (stage1Ops.y), stage0, diffuse).w;
    if ((stage1Ops.y) == 25 || (stage1Ops.y) == 26)
        alpha = Stage1ThreeSourceTextured(stage0, diffuse, specular, stage1TextureColor, (stage1Ops.y),
                                  (stage1ArgZero.y), (stage1Args.z), (stage1Args.w)).a;
    if (13 == (stage1Ops.y))
        alpha = saturate(lerp(
            Stage1SourceTextured(stage0, diffuse, specular, stage1TextureColor, (stage1Args.w)),
            Stage1SourceTextured(stage0, diffuse, specular, stage1TextureColor, (stage1Args.z)),
            stage1TextureAlpha * 1.0f)).a;
    // ALPHAOP reads separate D3D9 operands, never the RGB PM output alpha.
    if (15 == (stage1Ops.y)) {
        float4 texturePmAlpha1 = Stage1SourceTextured(stage0, diffuse, specular, stage1TextureColor, (stage1Args.z));
        float4 texturePmAlpha2 = Stage1SourceTextured(stage0, diffuse, specular, stage1TextureColor, (stage1Args.w));
        alpha = saturate(texturePmAlpha1 + texturePmAlpha2 * (1.0f - stage1TextureAlpha * 1.0f)).a;
    }
    float4 result = float4(color.xyz, alpha);
    AlphaGate(result.w);
    return result;
}
float4 PSStage1Diffuse(VOut v) : SV_Target {
    return Stage1AndAlpha(v.diffuse, v.diffuse, v.specular, 0.0f);
}
float4 PSStage1Modulate(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    if (stage1Ops.w == 2) {
        float4 stage1Sample = stage1GameTexture.Sample(stage1GameSampler, v.uvStage1);
        return Stage1AndAlphaTextured(t * v.diffuse, v.diffuse, v.specular,
                                      stage1Sample.a, stage1Sample);
    }
    if (stage1Ops.w != 0) return Stage1AndAlphaTextured(t * v.diffuse, v.diffuse, v.specular, t.a, t);
    return Stage1AndAlpha(t * v.diffuse, v.diffuse, v.specular, t.a);
}
float4 PSStage1TextureOnly(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    if (stage1Ops.w == 2) {
        float4 stage1Sample = stage1GameTexture.Sample(stage1GameSampler, v.uvStage1);
        return Stage1AndAlphaTextured(t, v.diffuse, v.specular,
                                      stage1Sample.a, stage1Sample);
    }
    if (stage1Ops.w != 0) return Stage1AndAlphaTextured(t, v.diffuse, v.specular, t.a, t);
    return Stage1AndAlpha(t, v.diffuse, v.specular, t.a);
}
float4 PSStage1Add(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    if (stage1Ops.w == 2) {
        float4 stage1Sample = stage1GameTexture.Sample(stage1GameSampler, v.uvStage1);
        return Stage1AndAlphaTextured(saturate(t + v.diffuse), v.diffuse, v.specular,
                                      stage1Sample.a, stage1Sample);
    }
    if (stage1Ops.w != 0) return Stage1AndAlphaTextured(saturate(t + v.diffuse), v.diffuse, v.specular, t.a, t);
    return Stage1AndAlpha(saturate(t + v.diffuse), v.diffuse, v.specular, t.a);
}
)";

bool compile(const char* entry, const char* profile, ComPtr<ID3DBlob>& blob) noexcept {
    ComPtr<ID3DBlob> errors;
    static const std::string shaderSource = std::string(kShader) + kScaledAlphaShader;
    // Preserve the original stage-0 shader source while linking stage 1.
    static const std::string stage1ShaderSource = shaderSource + kStage1FactorShader;
    return SUCCEEDED(D3DCompile(stage1ShaderSource.data(), stage1ShaderSource.size(), "live_game_frame",
        nullptr, nullptr, entry, profile, D3DCOMPILE_ENABLE_STRICTNESS,
        0, blob.GetAddressOf(), errors.GetAddressOf())) && blob;
}

bool ensure_pipeline(State& s, UINT width, UINT height) noexcept {
    if (!width || !height || width > 4096u || height > 4096u ||
        static_cast<std::uint64_t>(width) * height > 8388608u) return false;
    const bool readbackReady = std::all_of(s.readbacks.begin(), s.readbacks.end(),
        [](const ReadbackSlot& item) { return item.staging && item.fence; });
    if (s.backend.ready() && s.nativeWidth == width &&
        s.nativeHeight == height && s.vs && s.ps && s.sampledPs && s.textureOnlyPs && s.selectDiffuseTextureAlphaPs && s.selectDiffuseModulateAlphaPs && s.selectDiffuseAddAlphaPs && s.selectDiffuseSubtractAlphaPs && s.selectDiffuseModulate2XAlphaPs && s.selectDiffuseModulate4XAlphaPs && s.additivePs && s.subtractPs &&
        s.stage1DiffusePs && s.stage1ModulatePs &&
        s.stage1TextureOnlyPs && s.stage1AddPs && s.selectTextureAddSmoothAlphaPs && s.selectDiffuseAddSmoothAlphaPs && s.selectTextureFactorAlphaPs && s.selectTextureTfactorAlphaPs && s.selectDiffuseFactorAlphaPs && s.selectDiffuseTfactorAlphaPs && s.selectTextureBlendTextureAlphaPs && s.selectDiffuseBlendTextureAlphaPs && s.selectTextureBlendDiffuseAlphaPs && s.selectDiffuseBlendDiffuseAlphaPs && s.selectTextureModulate2XAlphaPs && s.selectTextureModulate4XAlphaPs && s.selectTextureDiffuseAlphaPs && s.selectTextureModulateAlphaPs && s.selectTextureAddAlphaPs && s.selectTextureSubtractAlphaPs &&
        s.subtractTextureAlphaPs && s.subtractDiffuseAlphaPs && s.subtractModulateAlphaPs && s.addSmoothPs && s.modulate2xPs && s.modulate4xPs &&
        s.modulate2xTextureAlphaPs &&
        s.modulate2xDiffuseAlphaPs &&
        s.modulate4xTextureAlphaPs &&
        s.modulate4xDiffuseAlphaPs && s.mixedTextureAlphaPs && s.mixedDiffuseAlphaPs &&
        s.mixedAddTextureAlphaPs && s.mixedAddDiffuseAlphaPs &&
        s.blendTextureAlphaPs && s.blendTextureAlphaPmPs && s.blendTextureAlphaPmTextureAlphaPs && s.blendTextureAlphaPmInverseDiffuseAlphaPs && s.blendTextureAlphaPmDiffuseAlphaPs && s.blendDiffuseAlphaPs && s.blendTextureSelectedTextureAlphaPs && s.blendTextureSelectedDiffuseAlphaPs && s.blendDiffuseSelectedTextureAlphaPs && s.blendDiffuseSelectedDiffuseAlphaPs && s.blendTextureModulateAlphaPs && s.blendDiffuseModulateAlphaPs && s.blendTextureModulate2XAlphaPs && s.blendTextureModulate4XAlphaPs && s.blendDiffuseModulate2XAlphaPs && s.blendDiffuseModulate4XAlphaPs && s.blendTextureAddAlphaPs && s.blendDiffuseAddAlphaPs &&
        s.blendTextureSubtractAlphaPs && s.blendDiffuseSubtractAlphaPs &&
        s.blendTextureAddSmoothAlphaPs && s.blendDiffuseAddSmoothAlphaPs && s.blendFactorAlphaPs &&
        s.blendFactorTextureAlphaPs && s.blendFactorModulateAlphaPs &&
        s.blendFactorDiffuseAlphaPs && s.blendFactorAddAlphaPs &&
        s.blendFactorSubtractAlphaPs && s.blendFactorAddSmoothAlphaPs &&
        s.blendFactorModulate2XAlphaPs && s.blendFactorModulate4XAlphaPs &&
        s.addSmoothTextureAlphaPs && s.addSmoothDiffuseAlphaPs &&
        s.blendTextureAlphaPmAddAlphaPs &&
         s.blendTextureAlphaPmSubtractAlphaPs && s.blendTextureAlphaPmModulate2XAlphaPs && s.blendTextureAlphaPmModulate4XAlphaPs && s.blendTextureAlphaPmAddSignedAlphaPs && s.blendTextureAlphaPmAddSigned2XAlphaPs && s.blendTextureAlphaPmBlendTextureAlphaPs && s.blendTextureAlphaPmBlendDiffuseAlphaPs && s.blendTextureAlphaPmBlendCurrentFactorAlphaPs && s.blendTextureAlphaPmBlendFactorAlphaPs && s.blendTextureAlphaPmAddSmoothAlphaPs &&
        s.blendTextureAlphaPmAddFactorAlphaPs && s.blendTextureAlphaPmAddSmoothFactorAlphaPs && s.blendTextureAlphaPmSignedFactorAlphaPs && s.blendTextureAlphaPmSigned2XFactorAlphaPs && s.blendTextureAlphaPmModulateFactorAlphaPs && s.blendTextureAlphaPmModulateAlphaPs && s.blendTextureAlphaPmFactorAlphaPs && s.layout && s.raster && s.scissorRaster &&
        s.diagnosticCullRasters[0] && s.diagnosticCullRasters[1] &&
        s.diagnosticCullRasters[2] && s.diagnosticCullRasters[3] && s.alphaBlend &&
         s.additiveBlend && s.sourceAlphaAddBlend && s.premultipliedAlphaBlend &&
        s.inverseSourceAlphaBlend && s.multiplyBlend &&
         s.inverseDestMultiplyBlend && s.inverseSourceMultiplyBlend &&
         s.destAlphaCrossfadeBlend && s.reverseDestAlphaCrossfadeBlend &&
         s.sourceAlphaSaturateCopyBlend && s.sourceAlphaSaturateAddBlend &&
        s.sourceAlphaCopyBlend && s.inverseAlphaCopyBlend &&
        s.inverseAlphaAddBlend && s.sourceReplaceBlend &&
        s.alphaConstants && s.stage1Constants && readbackReady)
        return true;
    s.diagnosticDepthView.Reset();
    s.diagnosticDepth.Reset();
    for (auto& depthState : s.diagnosticDepthStates) depthState.Reset();
    for (auto& depthState : s.diagnosticDepthAlwaysStates) depthState.Reset();
    for (auto& depthState : s.diagnosticDepthEqualityStates) depthState.Reset();
    for (auto& depthState : s.diagnosticDepthOrderingStates) depthState.Reset();
    // These buffers are owned by the exact D3D11 device generation.
    s.fullGameVertexUpload.Reset();
    s.fullGameIndexUpload.Reset();
    s.fullGameVertexCapacity = s.fullGameIndexCapacity = 0u;
    s.liveSm3Pipelines.clear();
    s.liveSm3BlendStates.clear();
    s.backend.shutdown();
    s.nativeWidth = s.nativeHeight = 0u;
    s.vs.Reset(); s.ps.Reset(); s.sampledPs.Reset();
    s.stage1DiffusePs.Reset(); s.stage1ModulatePs.Reset();
    s.stage1TextureOnlyPs.Reset(); s.stage1AddPs.Reset(); s.textureOnlyPs.Reset(); s.selectTextureDiffuseAlphaPs.Reset(); s.selectTextureModulateAlphaPs.Reset(); s.selectTextureModulate2XAlphaPs.Reset(); s.selectTextureModulate4XAlphaPs.Reset(); s.selectTextureAddAlphaPs.Reset(); s.selectTextureSubtractAlphaPs.Reset(); s.selectDiffuseTextureAlphaPs.Reset(); s.selectDiffuseModulateAlphaPs.Reset(); s.selectDiffuseAddAlphaPs.Reset(); s.selectDiffuseSubtractAlphaPs.Reset(); s.selectDiffuseModulate2XAlphaPs.Reset(); s.selectDiffuseModulate4XAlphaPs.Reset(); s.selectTextureAddSmoothAlphaPs.Reset(); s.selectDiffuseAddSmoothAlphaPs.Reset(); s.selectTextureFactorAlphaPs.Reset(); s.selectTextureTfactorAlphaPs.Reset(); s.selectDiffuseFactorAlphaPs.Reset(); s.selectDiffuseTfactorAlphaPs.Reset(); s.selectTextureBlendTextureAlphaPs.Reset(); s.selectDiffuseBlendTextureAlphaPs.Reset(); s.selectTextureBlendDiffuseAlphaPs.Reset(); s.selectDiffuseBlendDiffuseAlphaPs.Reset(); s.additivePs.Reset(); s.subtractPs.Reset(); s.addSmoothPs.Reset();
    s.subtractTextureAlphaPs.Reset(); s.subtractDiffuseAlphaPs.Reset(); s.subtractModulateAlphaPs.Reset(); s.modulate2xPs.Reset(); s.modulate4xPs.Reset(); s.modulate2xTextureAlphaPs.Reset(); s.modulate2xDiffuseAlphaPs.Reset(); s.modulate4xTextureAlphaPs.Reset(); s.modulate4xDiffuseAlphaPs.Reset(); s.mixedTextureAlphaPs.Reset(); s.mixedDiffuseAlphaPs.Reset(); s.mixedAddTextureAlphaPs.Reset(); s.mixedAddDiffuseAlphaPs.Reset(); s.blendTextureAlphaPs.Reset(); s.blendTextureAlphaPmPs.Reset(); s.blendTextureAlphaPmTextureAlphaPs.Reset(); s.blendTextureAlphaPmInverseTextureAlphaPs.Reset(); s.blendTextureAlphaPmInverseDiffuseAlphaPs.Reset(); s.blendTextureAlphaPmDiffuseAlphaPs.Reset(); s.blendTextureAlphaPmFactorAlphaPs.Reset(); s.blendTextureAlphaPmSignedFactorAlphaPs.Reset(); s.blendTextureAlphaPmSigned2XFactorAlphaPs.Reset(); s.blendTextureAlphaPmAddFactorAlphaPs.Reset(); s.blendTextureAlphaPmAddSmoothFactorAlphaPs.Reset(); s.blendTextureAlphaPmModulateFactorAlphaPs.Reset(); s.blendTextureAlphaPmModulateAlphaPs.Reset(); s.blendTextureAlphaPmAddAlphaPs.Reset(); s.blendTextureAlphaPmSubtractAlphaPs.Reset(); s.blendTextureAlphaPmModulate2XAlphaPs.Reset(); s.blendTextureAlphaPmModulate4XAlphaPs.Reset(); s.blendTextureAlphaPmAddSignedAlphaPs.Reset(); s.blendTextureAlphaPmAddSigned2XAlphaPs.Reset(); s.blendTextureAlphaPmBlendTextureAlphaPs.Reset(); s.blendTextureAlphaPmBlendDiffuseAlphaPs.Reset(); s.blendTextureAlphaPmBlendCurrentFactorAlphaPs.Reset(); s.blendTextureAlphaPmBlendFactorAlphaPs.Reset(); s.blendTextureAlphaPmAddSmoothAlphaPs.Reset(); s.blendDiffuseAlphaPs.Reset(); s.blendTextureSelectedTextureAlphaPs.Reset(); s.blendTextureSelectedDiffuseAlphaPs.Reset(); s.blendDiffuseSelectedTextureAlphaPs.Reset(); s.blendDiffuseSelectedDiffuseAlphaPs.Reset(); s.blendTextureModulateAlphaPs.Reset(); s.blendDiffuseModulateAlphaPs.Reset(); s.blendTextureModulate2XAlphaPs.Reset(); s.blendTextureModulate4XAlphaPs.Reset(); s.blendDiffuseModulate2XAlphaPs.Reset(); s.blendDiffuseModulate4XAlphaPs.Reset(); s.blendTextureAddAlphaPs.Reset(); s.blendDiffuseAddAlphaPs.Reset(); s.blendTextureSubtractAlphaPs.Reset(); s.blendDiffuseSubtractAlphaPs.Reset(); s.blendTextureAddSmoothAlphaPs.Reset(); s.blendDiffuseAddSmoothAlphaPs.Reset(); s.blendFactorAlphaPs.Reset(); s.blendFactorTextureAlphaPs.Reset(); s.blendFactorModulateAlphaPs.Reset();
    s.blendFactorDiffuseAlphaPs.Reset(); s.blendFactorAddAlphaPs.Reset(); s.blendFactorSubtractAlphaPs.Reset(); s.blendFactorAddSmoothAlphaPs.Reset();
    s.blendFactorModulate2XAlphaPs.Reset(); s.blendFactorModulate4XAlphaPs.Reset();
    s.addSmoothTextureAlphaPs.Reset(); s.addSmoothDiffuseAlphaPs.Reset();
    s.layout.Reset(); s.raster.Reset(); s.scissorRaster.Reset();
    for (auto& item : s.diagnosticCullRasters) item.Reset();
    s.alphaBlend.Reset(); s.additiveBlend.Reset(); s.sourceAlphaAddBlend.Reset(); s.premultipliedAlphaBlend.Reset(); s.inverseSourceAlphaBlend.Reset(); s.sourceAlphaCopyBlend.Reset(); s.inverseAlphaCopyBlend.Reset(); s.inverseAlphaAddBlend.Reset(); s.sourceReplaceBlend.Reset(); s.multiplyBlend.Reset(); s.inverseDestMultiplyBlend.Reset(); s.inverseSourceMultiplyBlend.Reset(); s.destAlphaCrossfadeBlend.Reset(); s.reverseDestAlphaCrossfadeBlend.Reset(); s.sourceAlphaSaturateCopyBlend.Reset(); s.sourceAlphaSaturateAddBlend.Reset();
    s.alphaConstants.Reset();
    s.stage1Constants.Reset();
    for (auto& item : s.readbacks) {
        item.staging.Reset(); item.fence.Reset(); item.busy = false; item.quarantined = false;
        item.mapPending = false;
    }
    s.readSlot = s.writeSlot = 0;
    s.previousOutput = {};
    if (++s.outputGeneration == 0u) ++s.outputGeneration;
    s.insetSurface.Reset(); s.insetFormat = D3DFMT_UNKNOWN;
    s.insetSurfaceDevice = 0u;
    s.insetSurfaceWidth = s.insetSurfaceHeight = 0u;
    for (auto& masked : s.maskedBlends) masked.Reset();
    for (auto& masked : s.multiplyMaskedBlends) masked.Reset();
    for (auto& masked : s.inverseDestMultiplyMaskedBlends) masked.Reset();
    for (auto& masked : s.inverseSourceMultiplyMaskedBlends) masked.Reset();
    for (auto& masked : s.destAlphaCrossfadeMaskedBlends) masked.Reset();
    for (auto& masked : s.reverseDestAlphaCrossfadeMaskedBlends) masked.Reset();
    for (auto& masked : s.sourceAlphaSaturateCopyMaskedBlends) masked.Reset();
    for (auto& masked : s.sourceAlphaSaturateAddMaskedBlends) masked.Reset();
    for (auto& masked : s.inverseSourceAlphaMaskedBlends) masked.Reset();
    for (auto& masked : s.sourceAlphaCopyMaskedBlends) masked.Reset();
    for (auto& masked : s.inverseAlphaCopyMaskedBlends) masked.Reset();
    for (auto& masked : s.inverseAlphaAddMaskedBlends) masked.Reset();
    for (auto& masked : s.sourceReplaceMaskedBlends) masked.Reset();
    for (auto& masked : s.subtractiveMaskedBlends) masked.Reset();
    for (auto& masked : s.extremumMaskedBlends) masked.Reset();
    NativeBackendConfig cfg{};
    cfg.width = width;
    cfg.height = height;
    cfg.color_format = DXGI_FORMAT_B8G8R8A8_UNORM;
    if (!s.backend.initialize(cfg)) return false;
    s.nativeWidth = width; s.nativeHeight = height;
    auto* dev = s.backend.device();
    ComPtr<ID3DBlob> vcode, pcode, sampledCode, textureOnlyCode, additiveCode, subtractCode, addSmoothCode, modulate2xCode, modulate4xCode, modulate2xTextureCode, modulate2xDiffuseCode, modulate4xTextureCode, modulate4xDiffuseCode, subtractTextureCode, subtractDiffuseCode, subtractModulateCode, mixedTextureCode, mixedDiffuseCode, mixedAddTextureCode, mixedAddDiffuseCode, blendTextureCode, blendTexturePmCode, blendTexturePmTextureAlphaCode, blendTexturePmInverseTextureAlphaCode, blendTexturePmInverseDiffuseAlphaCode, blendTexturePmDiffuseAlphaCode, blendTexturePmModulateAlphaCode, blendTexturePmFactorAlphaCode, blendDiffuseCode, blendTexturePmAddAlphaCode, blendTexturePmSubtractAlphaCode, blendTexturePmModulate2XAlphaCode, blendTexturePmModulate4XAlphaCode, blendTexturePmAddSignedAlphaCode, blendTexturePmAddSigned2XAlphaCode, blendTexturePmBlendTextureAlphaCode, blendTexturePmBlendDiffuseAlphaCode, blendTexturePmBlendCurrentFactorAlphaCode, blendTexturePmBlendFactorAlphaCode, blendTexturePmAddSmoothAlphaCode, blendTextureSelectedTextureAlphaCode, blendTextureSelectedDiffuseAlphaCode, blendDiffuseSelectedTextureAlphaCode, blendDiffuseSelectedDiffuseAlphaCode, blendTextureModulate2XCode, blendTextureModulate4XCode, blendDiffuseModulate2XCode, blendDiffuseModulate4XCode, blendTextureModulateCode, blendDiffuseModulateCode, blendTextureAddCode, blendDiffuseAddCode, blendTextureSubtractCode, blendDiffuseSubtractCode, blendTextureAddSmoothCode, blendDiffuseAddSmoothCode, blendFactorCode, blendFactorTextureCode, blendFactorModulateCode, blendFactorDiffuseCode, blendFactorAddCode, blendFactorSubtractCode, blendFactorAddSmoothCode, blendFactorModulate2XCode, blendFactorModulate4XCode, smoothTextureCode, smoothDiffuseCode, selectDiffuseTextureCode, selectDiffuseModulateCode, selectTextureDiffuseCode, selectTextureModulateCode, selectTextureModulate2XCode, selectTextureModulate4XCode, selectTextureAddCode, selectTextureSubtractCode, selectDiffuseAddCode, selectDiffuseSubtractCode, selectDiffuseModulate2XCode, selectDiffuseModulate4XCode, selectTextureAddSmoothCode, selectDiffuseAddSmoothCode, selectTextureFactorCode, selectDiffuseFactorCode, selectTextureBlendTextureCode, selectDiffuseBlendTextureCode; ComPtr<ID3DBlob> selectTextureBlendDiffuseCode, selectDiffuseBlendDiffuseCode, selectTextureTfactorCode, selectDiffuseTfactorCode;
    ComPtr<ID3DBlob> stage1DiffuseCode, stage1ModulateCode;
    ComPtr<ID3DBlob> stage1TextureOnlyCode, stage1AddCode;
    ComPtr<ID3DBlob> blendTexturePmModulateFactorAlphaCode;
    ComPtr<ID3DBlob> blendTexturePmAddFactorCode, blendTexturePmAddSmoothFactorCode;
    ComPtr<ID3DBlob> blendTexturePmSignedFactorCode, blendTexturePmSigned2XFactorCode;
    if (!compile("VS", "vs_4_0", vcode) ||
        !compile("PS", "ps_4_0", pcode) ||
        !compile("PSStage1Diffuse", "ps_4_0", stage1DiffuseCode) ||
        !compile("PSStage1Modulate", "ps_4_0", stage1ModulateCode) ||
        !compile("PSStage1TextureOnly", "ps_4_0", stage1TextureOnlyCode) ||
        !compile("PSStage1Add", "ps_4_0", stage1AddCode) ||
        !compile("PSTextured", "ps_4_0", sampledCode) ||
        !compile("PSTextureOnly", "ps_4_0", textureOnlyCode) ||
        !compile("PSTextureSelectTextureDiffuseAlpha", "ps_4_0", selectTextureDiffuseCode) ||
        !compile("PSTextureSelectTextureModulateAlpha", "ps_4_0", selectTextureModulateCode) ||
        !compile("PSTextureSelectTextureModulate2XAlpha", "ps_4_0", selectTextureModulate2XCode) ||
        !compile("PSTextureSelectTextureModulate4XAlpha", "ps_4_0", selectTextureModulate4XCode) ||
        !compile("PSTextureSelectTextureAddAlpha", "ps_4_0", selectTextureAddCode) ||
        !compile("PSTextureSelectTextureSubtractAlpha", "ps_4_0", selectTextureSubtractCode) ||
        !compile("PSTextureSelectDiffuseTextureAlpha", "ps_4_0", selectDiffuseTextureCode) ||
        !compile("PSTextureSelectDiffuseModulateAlpha", "ps_4_0", selectDiffuseModulateCode) ||
        !compile("PSTextureSelectDiffuseAddAlpha", "ps_4_0", selectDiffuseAddCode) ||
        !compile("PSTextureSelectDiffuseSubtractAlpha", "ps_4_0", selectDiffuseSubtractCode) ||
        !compile("PSTextureSelectDiffuseModulate2XAlpha", "ps_4_0", selectDiffuseModulate2XCode) ||
        !compile("PSTextureSelectDiffuseModulate4XAlpha", "ps_4_0", selectDiffuseModulate4XCode) ||
        !compile("PSTextureSelectTextureAddSmoothAlpha", "ps_4_0", selectTextureAddSmoothCode) ||
        !compile("PSTextureSelectDiffuseAddSmoothAlpha", "ps_4_0", selectDiffuseAddSmoothCode) ||
        !compile("PSTextureSelectTextureFactorAlpha", "ps_4_0", selectTextureFactorCode) ||
        !compile("PSTextureSelectTextureTfactorAlpha", "ps_4_0", selectTextureTfactorCode) ||
        !compile("PSTextureSelectDiffuseFactorAlpha", "ps_4_0", selectDiffuseFactorCode) ||
        !compile("PSTextureSelectDiffuseTfactorAlpha", "ps_4_0", selectDiffuseTfactorCode) ||
        !compile("PSTextureSelectTextureBlendTextureAlpha", "ps_4_0", selectTextureBlendTextureCode) ||
        !compile("PSTextureSelectDiffuseBlendTextureAlpha", "ps_4_0", selectDiffuseBlendTextureCode) ||
        !compile("PSTextureSelectTextureBlendDiffuseAlpha", "ps_4_0", selectTextureBlendDiffuseCode) ||
        !compile("PSTextureSelectDiffuseBlendDiffuseAlpha", "ps_4_0", selectDiffuseBlendDiffuseCode) ||
        !compile("PSTextureAdd", "ps_4_0", additiveCode) ||
        !compile("PSTextureSubtract", "ps_4_0", subtractCode) ||
        !compile("PSTextureSubtractTextureAlpha", "ps_4_0", subtractTextureCode) ||
        !compile("PSTextureSubtractDiffuseAlpha", "ps_4_0", subtractDiffuseCode) ||
        !compile("PSTextureSubtractModulateAlpha", "ps_4_0", subtractModulateCode) ||
        !compile("PSTextureAddSmooth", "ps_4_0", addSmoothCode) ||
        !compile("PSTextureAddSmoothTextureAlpha", "ps_4_0", smoothTextureCode) ||
        !compile("PSTextureAddSmoothDiffuseAlpha", "ps_4_0", smoothDiffuseCode) ||
        !compile("PSTextureModulate2X", "ps_4_0", modulate2xCode) ||
        !compile("PSTextureModulate4X", "ps_4_0", modulate4xCode) ||
        !compile("PSTextureModulate2XTextureAlpha", "ps_4_0", modulate2xTextureCode) ||
        !compile("PSTextureModulate2XDiffuseAlpha", "ps_4_0", modulate2xDiffuseCode) ||
        !compile("PSTextureModulate4XTextureAlpha", "ps_4_0", modulate4xTextureCode) ||
        !compile("PSTextureModulate4XDiffuseAlpha", "ps_4_0", modulate4xDiffuseCode) ||
        !compile("PSTextureModulateTextureAlpha", "ps_4_0", mixedTextureCode) ||
        !compile("PSTextureModulateDiffuseAlpha", "ps_4_0", mixedDiffuseCode) ||
        !compile("PSTextureAddTextureAlpha", "ps_4_0", mixedAddTextureCode) ||
        !compile("PSTextureAddDiffuseAlpha", "ps_4_0", mixedAddDiffuseCode) ||
        !compile("PSTextureBlendTextureAlpha", "ps_4_0", blendTextureCode) ||
        !compile("PSTextureBlendTextureAlphaPM", "ps_4_0", blendTexturePmCode) ||
        !compile("PSTextureBlendTextureAlphaPMSelectTextureAlpha", "ps_4_0", blendTexturePmTextureAlphaCode) ||
        !compile("PSTextureBlendTextureAlphaPMSelectInverseTextureAlpha", "ps_4_0", blendTexturePmInverseTextureAlphaCode) ||
        !compile("PSTextureBlendTextureAlphaPMSelectInverseDiffuseAlpha", "ps_4_0", blendTexturePmInverseDiffuseAlphaCode) ||
        !compile("PSTextureBlendTextureAlphaPMSelectDiffuseAlpha", "ps_4_0", blendTexturePmDiffuseAlphaCode) ||
        !compile("PSTextureBlendTextureAlphaPMSelectFactorAlpha", "ps_4_0", blendTexturePmFactorAlphaCode) ||
         !compile("PSTextureBlendTextureAlphaPMModulateFactorAlpha", "ps_4_0", blendTexturePmModulateFactorAlphaCode) ||
        !compile("PSTextureBlendTextureAlphaPMAddFactorAlpha", "ps_4_0", blendTexturePmAddFactorCode) ||
        !compile("PSTextureBlendTextureAlphaPMAddSmoothFactorAlpha", "ps_4_0", blendTexturePmAddSmoothFactorCode) ||
        !compile("PSTextureBlendTextureAlphaPMSignedFactorAlpha", "ps_4_0", blendTexturePmSignedFactorCode) ||
        !compile("PSTextureBlendTextureAlphaPMSigned2XFactorAlpha", "ps_4_0", blendTexturePmSigned2XFactorCode) ||
        !compile("PSTextureBlendTextureAlphaPMModulateAlpha", "ps_4_0", blendTexturePmModulateAlphaCode) ||
         !compile("PSTextureBlendTextureAlphaPMAddAlpha", "ps_4_0", blendTexturePmAddAlphaCode) ||
         !compile("PSTextureBlendTextureAlphaPMSubtractAlpha", "ps_4_0", blendTexturePmSubtractAlphaCode) ||
         !compile("PSTextureBlendTextureAlphaPMModulate2XAlpha", "ps_4_0", blendTexturePmModulate2XAlphaCode) ||
         !compile("PSTextureBlendTextureAlphaPMModulate4XAlpha", "ps_4_0", blendTexturePmModulate4XAlphaCode) ||
         !compile("PSTextureBlendTextureAlphaPMAddSignedAlpha", "ps_4_0", blendTexturePmAddSignedAlphaCode) ||
         !compile("PSTextureBlendTextureAlphaPMAddSigned2XAlpha", "ps_4_0", blendTexturePmAddSigned2XAlphaCode) ||
         !compile("PSTextureBlendTextureAlphaPMBlendTextureAlpha", "ps_4_0", blendTexturePmBlendTextureAlphaCode) ||
         !compile("PSTextureBlendTextureAlphaPMBlendDiffuseAlpha", "ps_4_0", blendTexturePmBlendDiffuseAlphaCode) ||
         !compile("PSTextureBlendTextureAlphaPMBlendCurrentFactorAlpha", "ps_4_0", blendTexturePmBlendCurrentFactorAlphaCode) ||
          !compile("PSTextureBlendTextureAlphaPMBlendFactorAlpha", "ps_4_0", blendTexturePmBlendFactorAlphaCode) ||
         !compile("PSTextureBlendTextureAlphaPMAddSmoothAlpha", "ps_4_0", blendTexturePmAddSmoothAlphaCode) ||
        !compile("PSTextureBlendDiffuseAlpha", "ps_4_0", blendDiffuseCode) ||
        !compile("PSTextureBlendTextureSelectedTextureAlpha", "ps_4_0", blendTextureSelectedTextureAlphaCode) ||
        !compile("PSTextureBlendTextureSelectedDiffuseAlpha", "ps_4_0", blendTextureSelectedDiffuseAlphaCode) ||
        !compile("PSTextureBlendDiffuseSelectedTextureAlpha", "ps_4_0", blendDiffuseSelectedTextureAlphaCode) ||
        !compile("PSTextureBlendDiffuseSelectedDiffuseAlpha", "ps_4_0", blendDiffuseSelectedDiffuseAlphaCode) ||
        !compile("PSTextureBlendTextureModulateAlpha", "ps_4_0", blendTextureModulateCode) ||
        !compile("PSTextureBlendDiffuseModulateAlpha", "ps_4_0", blendDiffuseModulateCode) ||
        !compile("PSTextureBlendTextureModulate2XAlpha", "ps_4_0", blendTextureModulate2XCode) ||
        !compile("PSTextureBlendTextureModulate4XAlpha", "ps_4_0", blendTextureModulate4XCode) ||
        !compile("PSTextureBlendDiffuseModulate2XAlpha", "ps_4_0", blendDiffuseModulate2XCode) ||
        !compile("PSTextureBlendDiffuseModulate4XAlpha", "ps_4_0", blendDiffuseModulate4XCode) ||
        !compile("PSTextureBlendTextureAddAlpha", "ps_4_0", blendTextureAddCode) ||
        !compile("PSTextureBlendDiffuseAddAlpha", "ps_4_0", blendDiffuseAddCode) ||
        !compile("PSTextureBlendTextureSubtractAlpha", "ps_4_0", blendTextureSubtractCode) ||
        !compile("PSTextureBlendDiffuseSubtractAlpha", "ps_4_0", blendDiffuseSubtractCode) ||
        !compile("PSTextureBlendTextureAddSmoothAlpha", "ps_4_0", blendTextureAddSmoothCode) ||
        !compile("PSTextureBlendDiffuseAddSmoothAlpha", "ps_4_0", blendDiffuseAddSmoothCode) ||
        !compile("PSTextureBlendFactorAlpha", "ps_4_0", blendFactorCode) ||
        !compile("PSTextureBlendFactorTextureAlpha", "ps_4_0", blendFactorTextureCode) ||
        !compile("PSTextureBlendFactorModulateAlpha", "ps_4_0", blendFactorModulateCode) ||
        !compile("PSTextureBlendFactorDiffuseAlpha", "ps_4_0", blendFactorDiffuseCode) ||
        !compile("PSTextureBlendFactorAddAlpha", "ps_4_0", blendFactorAddCode) ||
        !compile("PSTextureBlendFactorSubtractAlpha", "ps_4_0", blendFactorSubtractCode) ||
        !compile("PSTextureBlendFactorAddSmoothAlpha", "ps_4_0", blendFactorAddSmoothCode) ||
        !compile("PSTextureBlendFactorModulate2XAlpha", "ps_4_0", blendFactorModulate2XCode) ||
        !compile("PSTextureBlendFactorModulate4XAlpha", "ps_4_0", blendFactorModulate4XCode) ||
        FAILED(dev->CreateVertexShader(vcode->GetBufferPointer(), vcode->GetBufferSize(),
                                      nullptr, s.vs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(pcode->GetBufferPointer(), pcode->GetBufferSize(),
                                     nullptr, s.ps.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(stage1DiffuseCode->GetBufferPointer(), stage1DiffuseCode->GetBufferSize(),
                                     nullptr, s.stage1DiffusePs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(stage1ModulateCode->GetBufferPointer(), stage1ModulateCode->GetBufferSize(),
                                     nullptr, s.stage1ModulatePs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(stage1TextureOnlyCode->GetBufferPointer(), stage1TextureOnlyCode->GetBufferSize(),
                                     nullptr, s.stage1TextureOnlyPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(stage1AddCode->GetBufferPointer(), stage1AddCode->GetBufferSize(),
                                     nullptr, s.stage1AddPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(sampledCode->GetBufferPointer(), sampledCode->GetBufferSize(),
                                     nullptr, s.sampledPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(textureOnlyCode->GetBufferPointer(), textureOnlyCode->GetBufferSize(),
                                     nullptr, s.textureOnlyPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(selectTextureDiffuseCode->GetBufferPointer(), selectTextureDiffuseCode->GetBufferSize(),
                                      nullptr, s.selectTextureDiffuseAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(selectTextureModulateCode->GetBufferPointer(), selectTextureModulateCode->GetBufferSize(),
                                      nullptr, s.selectTextureModulateAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(selectTextureModulate2XCode->GetBufferPointer(), selectTextureModulate2XCode->GetBufferSize(),
                                      nullptr, s.selectTextureModulate2XAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(selectTextureModulate4XCode->GetBufferPointer(), selectTextureModulate4XCode->GetBufferSize(),
                                      nullptr, s.selectTextureModulate4XAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(selectTextureAddCode->GetBufferPointer(), selectTextureAddCode->GetBufferSize(),
                                      nullptr, s.selectTextureAddAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(selectTextureSubtractCode->GetBufferPointer(), selectTextureSubtractCode->GetBufferSize(),
                                      nullptr, s.selectTextureSubtractAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(selectDiffuseTextureCode->GetBufferPointer(), selectDiffuseTextureCode->GetBufferSize(),
                                     nullptr, s.selectDiffuseTextureAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(selectDiffuseModulateCode->GetBufferPointer(), selectDiffuseModulateCode->GetBufferSize(),
                                     nullptr, s.selectDiffuseModulateAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(selectDiffuseAddCode->GetBufferPointer(), selectDiffuseAddCode->GetBufferSize(),
                                     nullptr, s.selectDiffuseAddAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(selectDiffuseSubtractCode->GetBufferPointer(), selectDiffuseSubtractCode->GetBufferSize(),
                                     nullptr, s.selectDiffuseSubtractAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(selectDiffuseModulate2XCode->GetBufferPointer(), selectDiffuseModulate2XCode->GetBufferSize(),
                                     nullptr, s.selectDiffuseModulate2XAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(selectDiffuseModulate4XCode->GetBufferPointer(), selectDiffuseModulate4XCode->GetBufferSize(),
                                     nullptr, s.selectDiffuseModulate4XAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(selectTextureAddSmoothCode->GetBufferPointer(), selectTextureAddSmoothCode->GetBufferSize(),
                                      nullptr, s.selectTextureAddSmoothAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(selectDiffuseAddSmoothCode->GetBufferPointer(), selectDiffuseAddSmoothCode->GetBufferSize(),
                                      nullptr, s.selectDiffuseAddSmoothAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(selectTextureFactorCode->GetBufferPointer(), selectTextureFactorCode->GetBufferSize(),
                                      nullptr, s.selectTextureFactorAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(selectTextureTfactorCode->GetBufferPointer(), selectTextureTfactorCode->GetBufferSize(),
                                      nullptr, s.selectTextureTfactorAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(selectDiffuseFactorCode->GetBufferPointer(), selectDiffuseFactorCode->GetBufferSize(),
                                      nullptr, s.selectDiffuseFactorAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(selectDiffuseTfactorCode->GetBufferPointer(), selectDiffuseTfactorCode->GetBufferSize(),
                                      nullptr, s.selectDiffuseTfactorAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(selectTextureBlendTextureCode->GetBufferPointer(), selectTextureBlendTextureCode->GetBufferSize(),
                                      nullptr, s.selectTextureBlendTextureAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(selectDiffuseBlendTextureCode->GetBufferPointer(), selectDiffuseBlendTextureCode->GetBufferSize(),
                                      nullptr, s.selectDiffuseBlendTextureAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(selectTextureBlendDiffuseCode->GetBufferPointer(), selectTextureBlendDiffuseCode->GetBufferSize(),
                                      nullptr, s.selectTextureBlendDiffuseAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(selectDiffuseBlendDiffuseCode->GetBufferPointer(), selectDiffuseBlendDiffuseCode->GetBufferSize(),
                                      nullptr, s.selectDiffuseBlendDiffuseAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(additiveCode->GetBufferPointer(), additiveCode->GetBufferSize(),
                                     nullptr, s.additivePs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(subtractCode->GetBufferPointer(), subtractCode->GetBufferSize(),
                                     nullptr, s.subtractPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(subtractTextureCode->GetBufferPointer(), subtractTextureCode->GetBufferSize(),
                                      nullptr, s.subtractTextureAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(subtractDiffuseCode->GetBufferPointer(), subtractDiffuseCode->GetBufferSize(),
                                      nullptr, s.subtractDiffuseAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(subtractModulateCode->GetBufferPointer(), subtractModulateCode->GetBufferSize(),
                                       nullptr, s.subtractModulateAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(addSmoothCode->GetBufferPointer(), addSmoothCode->GetBufferSize(),
                                     nullptr, s.addSmoothPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(smoothTextureCode->GetBufferPointer(), smoothTextureCode->GetBufferSize(),
                                     nullptr, s.addSmoothTextureAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(smoothDiffuseCode->GetBufferPointer(), smoothDiffuseCode->GetBufferSize(),
                                     nullptr, s.addSmoothDiffuseAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(modulate2xCode->GetBufferPointer(), modulate2xCode->GetBufferSize(),
                                     nullptr, s.modulate2xPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(modulate4xCode->GetBufferPointer(), modulate4xCode->GetBufferSize(),
                                     nullptr, s.modulate4xPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(modulate2xTextureCode->GetBufferPointer(), modulate2xTextureCode->GetBufferSize(),
                                     nullptr, s.modulate2xTextureAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(modulate2xDiffuseCode->GetBufferPointer(), modulate2xDiffuseCode->GetBufferSize(),
                                     nullptr, s.modulate2xDiffuseAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(modulate4xTextureCode->GetBufferPointer(), modulate4xTextureCode->GetBufferSize(),
                                     nullptr, s.modulate4xTextureAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(modulate4xDiffuseCode->GetBufferPointer(), modulate4xDiffuseCode->GetBufferSize(),
                                     nullptr, s.modulate4xDiffuseAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(mixedTextureCode->GetBufferPointer(), mixedTextureCode->GetBufferSize(),
                                     nullptr, s.mixedTextureAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(mixedDiffuseCode->GetBufferPointer(), mixedDiffuseCode->GetBufferSize(),
                                     nullptr, s.mixedDiffuseAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(mixedAddTextureCode->GetBufferPointer(), mixedAddTextureCode->GetBufferSize(),
                                     nullptr, s.mixedAddTextureAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(mixedAddDiffuseCode->GetBufferPointer(), mixedAddDiffuseCode->GetBufferSize(),
                                     nullptr, s.mixedAddDiffuseAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTextureCode->GetBufferPointer(), blendTextureCode->GetBufferSize(),
                                     nullptr, s.blendTextureAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTexturePmCode->GetBufferPointer(), blendTexturePmCode->GetBufferSize(),
                                      nullptr, s.blendTextureAlphaPmPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTexturePmTextureAlphaCode->GetBufferPointer(), blendTexturePmTextureAlphaCode->GetBufferSize(),
                                      nullptr, s.blendTextureAlphaPmTextureAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTexturePmInverseTextureAlphaCode->GetBufferPointer(), blendTexturePmInverseTextureAlphaCode->GetBufferSize(),
                                      nullptr, s.blendTextureAlphaPmInverseTextureAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTexturePmInverseDiffuseAlphaCode->GetBufferPointer(), blendTexturePmInverseDiffuseAlphaCode->GetBufferSize(),
                                       nullptr, s.blendTextureAlphaPmInverseDiffuseAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTexturePmDiffuseAlphaCode->GetBufferPointer(), blendTexturePmDiffuseAlphaCode->GetBufferSize(),
                                      nullptr, s.blendTextureAlphaPmDiffuseAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTexturePmFactorAlphaCode->GetBufferPointer(), blendTexturePmFactorAlphaCode->GetBufferSize(),
                                      nullptr, s.blendTextureAlphaPmFactorAlphaPs.GetAddressOf())) ||
         FAILED(dev->CreatePixelShader(blendTexturePmModulateFactorAlphaCode->GetBufferPointer(), blendTexturePmModulateFactorAlphaCode->GetBufferSize(),
                                       nullptr, s.blendTextureAlphaPmModulateFactorAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTexturePmAddFactorCode->GetBufferPointer(), blendTexturePmAddFactorCode->GetBufferSize(),
                                      nullptr, s.blendTextureAlphaPmAddFactorAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTexturePmAddSmoothFactorCode->GetBufferPointer(), blendTexturePmAddSmoothFactorCode->GetBufferSize(),
                                      nullptr, s.blendTextureAlphaPmAddSmoothFactorAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTexturePmSignedFactorCode->GetBufferPointer(), blendTexturePmSignedFactorCode->GetBufferSize(),
                                      nullptr, s.blendTextureAlphaPmSignedFactorAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTexturePmSigned2XFactorCode->GetBufferPointer(), blendTexturePmSigned2XFactorCode->GetBufferSize(),
                                      nullptr, s.blendTextureAlphaPmSigned2XFactorAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTexturePmModulateAlphaCode->GetBufferPointer(), blendTexturePmModulateAlphaCode->GetBufferSize(),
                                      nullptr, s.blendTextureAlphaPmModulateAlphaPs.GetAddressOf())) ||
         FAILED(dev->CreatePixelShader(blendTexturePmAddAlphaCode->GetBufferPointer(), blendTexturePmAddAlphaCode->GetBufferSize(),
                                       nullptr, s.blendTextureAlphaPmAddAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTexturePmSubtractAlphaCode->GetBufferPointer(), blendTexturePmSubtractAlphaCode->GetBufferSize(),
                                      nullptr, s.blendTextureAlphaPmSubtractAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTexturePmModulate2XAlphaCode->GetBufferPointer(), blendTexturePmModulate2XAlphaCode->GetBufferSize(),
                                      nullptr, s.blendTextureAlphaPmModulate2XAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTexturePmModulate4XAlphaCode->GetBufferPointer(), blendTexturePmModulate4XAlphaCode->GetBufferSize(),
                                       nullptr, s.blendTextureAlphaPmModulate4XAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTexturePmAddSignedAlphaCode->GetBufferPointer(), blendTexturePmAddSignedAlphaCode->GetBufferSize(),
                                       nullptr, s.blendTextureAlphaPmAddSignedAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTexturePmAddSigned2XAlphaCode->GetBufferPointer(), blendTexturePmAddSigned2XAlphaCode->GetBufferSize(),
                                       nullptr, s.blendTextureAlphaPmAddSigned2XAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTexturePmBlendTextureAlphaCode->GetBufferPointer(), blendTexturePmBlendTextureAlphaCode->GetBufferSize(),
                                       nullptr, s.blendTextureAlphaPmBlendTextureAlphaPs.GetAddressOf())) ||
         FAILED(dev->CreatePixelShader(blendTexturePmBlendDiffuseAlphaCode->GetBufferPointer(), blendTexturePmBlendDiffuseAlphaCode->GetBufferSize(),
                                        nullptr, s.blendTextureAlphaPmBlendDiffuseAlphaPs.GetAddressOf())) ||
         FAILED(dev->CreatePixelShader(blendTexturePmBlendCurrentFactorAlphaCode->GetBufferPointer(), blendTexturePmBlendCurrentFactorAlphaCode->GetBufferSize(),
                                       nullptr, s.blendTextureAlphaPmBlendCurrentFactorAlphaPs.GetAddressOf())) ||
         FAILED(dev->CreatePixelShader(blendTexturePmBlendFactorAlphaCode->GetBufferPointer(), blendTexturePmBlendFactorAlphaCode->GetBufferSize(),
                                      nullptr, s.blendTextureAlphaPmBlendFactorAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTexturePmAddSmoothAlphaCode->GetBufferPointer(), blendTexturePmAddSmoothAlphaCode->GetBufferSize(),
                                      nullptr, s.blendTextureAlphaPmAddSmoothAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendDiffuseCode->GetBufferPointer(), blendDiffuseCode->GetBufferSize(),
                                     nullptr, s.blendDiffuseAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTextureSelectedTextureAlphaCode->GetBufferPointer(), blendTextureSelectedTextureAlphaCode->GetBufferSize(),
                                     nullptr, s.blendTextureSelectedTextureAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTextureSelectedDiffuseAlphaCode->GetBufferPointer(), blendTextureSelectedDiffuseAlphaCode->GetBufferSize(),
                                     nullptr, s.blendTextureSelectedDiffuseAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendDiffuseSelectedTextureAlphaCode->GetBufferPointer(), blendDiffuseSelectedTextureAlphaCode->GetBufferSize(),
                                     nullptr, s.blendDiffuseSelectedTextureAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendDiffuseSelectedDiffuseAlphaCode->GetBufferPointer(), blendDiffuseSelectedDiffuseAlphaCode->GetBufferSize(),
                                     nullptr, s.blendDiffuseSelectedDiffuseAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTextureModulateCode->GetBufferPointer(), blendTextureModulateCode->GetBufferSize(),
                                      nullptr, s.blendTextureModulateAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendDiffuseModulateCode->GetBufferPointer(), blendDiffuseModulateCode->GetBufferSize(),
                                      nullptr, s.blendDiffuseModulateAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTextureModulate2XCode->GetBufferPointer(), blendTextureModulate2XCode->GetBufferSize(),
                                       nullptr, s.blendTextureModulate2XAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTextureModulate4XCode->GetBufferPointer(), blendTextureModulate4XCode->GetBufferSize(),
                                       nullptr, s.blendTextureModulate4XAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendDiffuseModulate2XCode->GetBufferPointer(), blendDiffuseModulate2XCode->GetBufferSize(),
                                       nullptr, s.blendDiffuseModulate2XAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendDiffuseModulate4XCode->GetBufferPointer(), blendDiffuseModulate4XCode->GetBufferSize(),
                                       nullptr, s.blendDiffuseModulate4XAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTextureAddCode->GetBufferPointer(), blendTextureAddCode->GetBufferSize(),
                                      nullptr, s.blendTextureAddAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendDiffuseAddCode->GetBufferPointer(), blendDiffuseAddCode->GetBufferSize(),
                                      nullptr, s.blendDiffuseAddAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTextureSubtractCode->GetBufferPointer(), blendTextureSubtractCode->GetBufferSize(),
                                      nullptr, s.blendTextureSubtractAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendDiffuseSubtractCode->GetBufferPointer(), blendDiffuseSubtractCode->GetBufferSize(),
                                      nullptr, s.blendDiffuseSubtractAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendTextureAddSmoothCode->GetBufferPointer(), blendTextureAddSmoothCode->GetBufferSize(),
                                      nullptr, s.blendTextureAddSmoothAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendDiffuseAddSmoothCode->GetBufferPointer(), blendDiffuseAddSmoothCode->GetBufferSize(),
                                      nullptr, s.blendDiffuseAddSmoothAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendFactorCode->GetBufferPointer(), blendFactorCode->GetBufferSize(),
                                     nullptr, s.blendFactorAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendFactorTextureCode->GetBufferPointer(), blendFactorTextureCode->GetBufferSize(),
                                     nullptr, s.blendFactorTextureAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendFactorModulateCode->GetBufferPointer(), blendFactorModulateCode->GetBufferSize(),
                                     nullptr, s.blendFactorModulateAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendFactorDiffuseCode->GetBufferPointer(), blendFactorDiffuseCode->GetBufferSize(),
                                      nullptr, s.blendFactorDiffuseAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendFactorAddCode->GetBufferPointer(), blendFactorAddCode->GetBufferSize(),
                                      nullptr, s.blendFactorAddAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendFactorSubtractCode->GetBufferPointer(), blendFactorSubtractCode->GetBufferSize(),
                                      nullptr, s.blendFactorSubtractAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendFactorAddSmoothCode->GetBufferPointer(), blendFactorAddSmoothCode->GetBufferSize(),
                                      nullptr, s.blendFactorAddSmoothAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendFactorModulate2XCode->GetBufferPointer(), blendFactorModulate2XCode->GetBufferSize(),
                                     nullptr, s.blendFactorModulate2XAlphaPs.GetAddressOf())) ||
        FAILED(dev->CreatePixelShader(blendFactorModulate4XCode->GetBufferPointer(), blendFactorModulate4XCode->GetBufferSize(),
                                     nullptr, s.blendFactorModulate4XAlphaPs.GetAddressOf())))
        return false;
    const D3D11_INPUT_ELEMENT_DESC elements[] = {
        {"POSITION", 0, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 0,
         D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"COLOR", 0, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 16,
         D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 0, DXGI_FORMAT_R32G32_FLOAT, 0, 32,
         D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"COLOR", 1, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 40,
         D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 1, DXGI_FORMAT_R32G32_FLOAT, 0, 56,
         D3D11_INPUT_PER_VERTEX_DATA, 0}
    };
    static_assert(sizeof(NativeVertex) == 64u, "Native vertex/IA Stage1 UV mismatch");
    if (FAILED(dev->CreateInputLayout(elements, 5,
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
    // D3D9 CullMode names the winding to remove, D3D11 BACK removes the
    // opposite face of FrontCounterClockwise. Keep menu no-cull unchanged.
    for (unsigned scissorEnabled = 0u; scissorEnabled < 2u; ++scissorEnabled) {
        for (unsigned direction = 0u; direction < 2u; ++direction) {
            raster.CullMode = D3D11_CULL_BACK;
            raster.FrontCounterClockwise = direction == 0u ? TRUE : FALSE;
            raster.ScissorEnable = scissorEnabled ? TRUE : FALSE;
            if (FAILED(dev->CreateRasterizerState(
                    &raster, s.diagnosticCullRasters[scissorEnabled * 2u + direction].GetAddressOf())))
                return false;
        }
    }
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
    // Game-supplied D3D9 SRCBLEND/DESTBLEND factors apply to RGB and alpha.
    target.SrcBlend = D3D11_BLEND_ONE;
    target.DestBlend = D3D11_BLEND_ONE;
    target.SrcBlendAlpha = D3D11_BLEND_ONE;
    target.DestBlendAlpha = D3D11_BLEND_ONE;
    if (FAILED(dev->CreateBlendState(&blend, s.additiveBlend.GetAddressOf())))
        return false;
    target.SrcBlend = D3D11_BLEND_SRC_ALPHA;
    target.SrcBlendAlpha = D3D11_BLEND_SRC_ALPHA;
    if (FAILED(dev->CreateBlendState(&blend, s.sourceAlphaAddBlend.GetAddressOf())))
        return false;
    // Premultiplied-alpha menu/UI surfaces: source RGB is already scaled.
    // Same ONE/INVSRCALPHA factors apply to output alpha, since separate
    // D3D9 alpha blending is rejected by the live state capture.
    target.SrcBlend = D3D11_BLEND_ONE;
    target.DestBlend = D3D11_BLEND_INV_SRC_ALPHA;
    target.SrcBlendAlpha = D3D11_BLEND_ONE;
    target.DestBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;
    if (FAILED(dev->CreateBlendState(&blend, s.premultipliedAlphaBlend.GetAddressOf())))
        return false;
    // D3D9 BOTHINVSRCALPHA overrides DESTBLEND: src*(1-src.a)+dst*src.a.
    // Translate both RGB and alpha factors; SEPARATEALPHABLEND is rejected.
    target.SrcBlend = D3D11_BLEND_INV_SRC_ALPHA;
    target.DestBlend = D3D11_BLEND_SRC_ALPHA;
    target.SrcBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;
    target.DestBlendAlpha = D3D11_BLEND_SRC_ALPHA;
    if (FAILED(dev->CreateBlendState(&blend, s.inverseSourceAlphaBlend.GetAddressOf())))
        return false;
    // Native D3D9 SRCALPHA/ZERO: attenuate source RGB by source alpha and
    // source alpha by itself, discarding destination. Do not use standard
    // SRCALPHA/INVSRCALPHA, which would leak prior diagnostic frame pixels.
    // Keep alpha factors as SRC_ALPHA/ZERO, not ONE/ZERO.
    target.SrcBlend = D3D11_BLEND_SRC_ALPHA;
    target.DestBlend = D3D11_BLEND_ZERO;
    target.SrcBlendAlpha = D3D11_BLEND_SRC_ALPHA;
    target.DestBlendAlpha = D3D11_BLEND_ZERO;
    if (FAILED(dev->CreateBlendState(&blend, s.sourceAlphaCopyBlend.GetAddressOf())))
        return false;
    // Exact live D3D9 inverse-source-alpha copy/add, including alpha equation.
    // No directional subtraction and no implicit production activation.
    target.SrcBlend = D3D11_BLEND_INV_SRC_ALPHA;
    target.DestBlend = D3D11_BLEND_ZERO;
    target.SrcBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;
    target.DestBlendAlpha = D3D11_BLEND_ZERO;
    if (FAILED(dev->CreateBlendState(&blend, s.inverseAlphaCopyBlend.GetAddressOf())))
        return false;
    target.DestBlend = D3D11_BLEND_ONE;
    target.DestBlendAlpha = D3D11_BLEND_ONE;
    if (FAILED(dev->CreateBlendState(&blend, s.inverseAlphaAddBlend.GetAddressOf())))
        return false;
    // D3D9 ONE/ZERO: source replacement in all four channels, even when
    // ALPHABLENDENABLE is true. Never borrow standard-over alpha factors.
    target.SrcBlend = D3D11_BLEND_ONE;
    target.DestBlend = D3D11_BLEND_ZERO;
    target.SrcBlendAlpha = D3D11_BLEND_ONE;
    target.DestBlendAlpha = D3D11_BLEND_ZERO;
    if (FAILED(dev->CreateBlendState(&blend, s.sourceReplaceBlend.GetAddressOf())))
        return false;
    // Multiplicative game overlays: both D3D9 DESTCOLOR/ZERO and
    // ZERO/SRCCOLOR evaluate src*dst. D3D11 alpha factors use DEST_ALPHA,
    // never DEST_COLOR in SrcBlendAlpha (invalid for the alpha slot).
    target.SrcBlend = D3D11_BLEND_DEST_COLOR;
    target.DestBlend = D3D11_BLEND_ZERO;
    target.SrcBlendAlpha = D3D11_BLEND_DEST_ALPHA;
    target.DestBlendAlpha = D3D11_BLEND_ZERO;
    if (FAILED(dev->CreateBlendState(&blend, s.multiplyBlend.GetAddressOf())))
        return false;
    // Menu/vehicle/race complement modulation. Distinct source/destination
    // equations: src*(1-dst) and dst*(1-src) must not share an OM descriptor.
    // D3D11 alpha slots require INV_DEST_ALPHA / INV_SRC_ALPHA respectively.
    target.SrcBlend = D3D11_BLEND_INV_DEST_COLOR;
    target.DestBlend = D3D11_BLEND_ZERO;
    target.SrcBlendAlpha = D3D11_BLEND_INV_DEST_ALPHA;
    target.DestBlendAlpha = D3D11_BLEND_ZERO;
    if (FAILED(dev->CreateBlendState(&blend, s.inverseDestMultiplyBlend.GetAddressOf())))
        return false;
    target.SrcBlend = D3D11_BLEND_ZERO;
    target.DestBlend = D3D11_BLEND_INV_SRC_COLOR;
    target.SrcBlendAlpha = D3D11_BLEND_ZERO;
    target.DestBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;
    if (FAILED(dev->CreateBlendState(&blend, s.inverseSourceMultiplyBlend.GetAddressOf())))
        return false;
    // Actual game Draw state may weight source and destination by the existing
    // render target alpha rather than source alpha. Distinct native descriptors
    // preserve each polarity on RGB and alpha, including masked sprite draws.
    target.SrcBlend = D3D11_BLEND_DEST_ALPHA;
    target.DestBlend = D3D11_BLEND_INV_DEST_ALPHA;
    target.SrcBlendAlpha = D3D11_BLEND_DEST_ALPHA;
    target.DestBlendAlpha = D3D11_BLEND_INV_DEST_ALPHA;
    if (FAILED(dev->CreateBlendState(&blend, s.destAlphaCrossfadeBlend.GetAddressOf())))
        return false;
    target.SrcBlend = D3D11_BLEND_INV_DEST_ALPHA;
    target.DestBlend = D3D11_BLEND_DEST_ALPHA;
    target.SrcBlendAlpha = D3D11_BLEND_INV_DEST_ALPHA;
    target.DestBlendAlpha = D3D11_BLEND_DEST_ALPHA;
    if (FAILED(dev->CreateBlendState(&blend, s.reverseDestAlphaCrossfadeBlend.GetAddressOf())))
        return false;
    // Game D3D9 SRCALPHASAT has RGB factor min(src.a,1-dst.a), while
    // source ALPHA factor is ONE. SRC_ALPHA_SAT is invalid in SrcBlendAlpha.
    // Pair-specific descriptors avoid mixing source replacement and additive.
    target.SrcBlend = D3D11_BLEND_SRC_ALPHA_SAT;
    target.DestBlend = D3D11_BLEND_ZERO;
    target.SrcBlendAlpha = D3D11_BLEND_ONE;
    target.DestBlendAlpha = D3D11_BLEND_ZERO;
    if (FAILED(dev->CreateBlendState(&blend, s.sourceAlphaSaturateCopyBlend.GetAddressOf())))
        return false;
    target.SrcBlend = D3D11_BLEND_SRC_ALPHA_SAT;
    target.DestBlend = D3D11_BLEND_ONE;
    target.SrcBlendAlpha = D3D11_BLEND_ONE;
    target.DestBlendAlpha = D3D11_BLEND_ONE;
    if (FAILED(dev->CreateBlendState(&blend, s.sourceAlphaSaturateAddBlend.GetAddressOf())))
        return false;
    D3D11_BUFFER_DESC constants{};
    constants.ByteWidth = sizeof(float) * 4u;
    constants.Usage = D3D11_USAGE_DEFAULT;
    constants.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
    if (FAILED(dev->CreateBuffer(&constants, nullptr, s.alphaConstants.GetAddressOf())))
        return false;
    // A single GPU buffer is owned by this D3D11 generation. Source game
    // stage-1 states (including TEMP, factors and texture operands) change
    // per Draw; Upload/PS b1 binding below must refresh on every use.
    constants.ByteWidth = sizeof(Stage1Upload);
    if (FAILED(dev->CreateBuffer(&constants, nullptr, s.stage1Constants.GetAddressOf())))
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

// A native diagnostic draw must originate in the same primary game backbuffer
// to which before_game_present() will upload its GPU-fenced inset. An auxiliary
// render-to-texture pass cannot be promoted solely by D3D9 device identity.
bool game_native_backbuffer_ready(IDirect3DDevice9* game,
                                  const D3DVIEWPORT9& viewport) noexcept {
    ComPtr<IDirect3DSurface9> target, backbuffer;
    D3DSURFACE_DESC targetDesc{}, bbDesc{};
    if (!game ||
        FAILED(game->GetRenderTarget(0, target.GetAddressOf())) || !target ||
        FAILED(game->GetBackBuffer(0, 0, D3DBACKBUFFER_TYPE_MONO,
                                   backbuffer.GetAddressOf())) || !backbuffer ||
        FAILED(target->GetDesc(&targetDesc)) ||
        FAILED(backbuffer->GetDesc(&bbDesc)))
        return false;
    // Canonical COM identity avoids false positives from interface aliases.
    ComPtr<IUnknown> targetIdentity, backbufferIdentity;
    if (FAILED(target.As(&targetIdentity)) ||
        FAILED(backbuffer.As(&backbufferIdentity)))
        return false;
    const GameNativeBackbufferAdmission admission{
        reinterpret_cast<std::uintptr_t>(targetIdentity.Get()),
        reinterpret_cast<std::uintptr_t>(backbufferIdentity.Get()),
        targetDesc.Width, targetDesc.Height, bbDesc.Width, bbDesc.Height,
        viewport.X, viewport.Y, viewport.Width, viewport.Height,
        targetDesc.Format == bbDesc.Format,
        bbDesc.Format == D3DFMT_A8R8G8B8 ||
            bbDesc.Format == D3DFMT_X8R8G8B8,
        targetDesc.MultiSampleType == D3DMULTISAMPLE_NONE &&
            bbDesc.MultiSampleType == D3DMULTISAMPLE_NONE
    };
    return env_full_game_opt_in()
        ? admission.accepts(bbDesc.Width, bbDesc.Height, 0u)
        : admission.accepts(kWidth, kHeight, 8u);
}

// Read the current game device, not a WARP fixture's manufactured state.
// COM getters AddRef; local ComPtrs always release before reset/return.
bool supported_game_state(IDirect3DDevice9* game, D3DPRIMITIVETYPE topology,
                          D3DVIEWPORT9& viewport,
                          GameFvfLayout& layout,
                          std::array<D3DMATRIX, 3>& transforms,
                          TextureCapture& capture, OutputCapture& output) noexcept {
    if (!game || FAILED(game->GetViewport(&viewport)) ||
        viewport.Width == 0 || viewport.Height == 0 ||
        !game_native_viewport_depth_valid(viewport.MinZ, viewport.MaxZ))
        return false;
    // Source viewport may be smaller than its target during menu/UI/race
    // transitions. A full-size D3D11 viewport distorted those actual game
    // Draws even though vertices were decoded correctly.
    ComPtr<IDirect3DSurface9> sourceTarget;
    D3DSURFACE_DESC sourceDesc{};
    if (FAILED(game->GetRenderTarget(0, sourceTarget.GetAddressOf())) ||
        !sourceTarget || FAILED(sourceTarget->GetDesc(&sourceDesc)))
        return false;
    ComPtr<IUnknown> sourceTargetIdentity;
    if (FAILED(sourceTarget.As(&sourceTargetIdentity)) || !sourceTargetIdentity)
        return false;
    output.targetIdentity = reinterpret_cast<std::uintptr_t>(sourceTargetIdentity.Get());
    GameNativeInsetRect nativeRect{};
    const bool fullFrame = env_full_game_opt_in();
    output.nativeWidth = fullFrame ? sourceDesc.Width : kWidth;
    output.nativeHeight = fullFrame ? sourceDesc.Height : kHeight;
    if (!game_native_inset_viewport(
            viewport.X, viewport.Y, viewport.Width, viewport.Height,
            sourceDesc.Width, sourceDesc.Height, nativeRect,
            output.nativeWidth, output.nativeHeight))
        return false;
    output.nativeViewport = {
        nativeRect.left, nativeRect.top,
        nativeRect.right - nativeRect.left,
        nativeRect.bottom - nativeRect.top, 0.0f, 1.0f
    };
    DWORD fvf = 0;
    if (FAILED(game->GetFVF(&fvf))) return false;
    // Use the live game's exact FVF byte layout; avoid reading UV as
    // diffuse when a menu/sprite TEX1 vertex omits D3DFVF_DIFFUSE.
    if (!game_fvf_layout(fvf, layout)) return false;
    // FVF PSIZE alters point rasterization, so point-specific admission below
    // rejects it. For lines/triangles the field only shifts COLOR/UV offsets.
    // Decide from the LIVE fixed-function combiner, not from TEXCOORD count.
    // Menus and vehicle previews may retain TEX1..8 UVs and an old bound
    // texture while COLOROP/ALPHAOP select only DIFFUSE. Such Draws require
    // the native untextured PS; genuinely sampled state still takes the
    // original texture mirror or safe D3D9 fallback.
    DWORD stage0Op = 0u, stage0Arg1 = 0u, stage0Arg2 = 0u;
    DWORD stage0AlphaOp = 0u, stage0Alpha1 = 0u, stage0Alpha2 = 0u;
    DWORD followingColorOp = 0u;
    if (FAILED(game->GetTextureStageState(0, D3DTSS_COLOROP, &stage0Op)) ||
        FAILED(game->GetTextureStageState(0, D3DTSS_COLORARG1, &stage0Arg1)) ||
        FAILED(game->GetTextureStageState(0, D3DTSS_COLORARG2, &stage0Arg2)) ||
        FAILED(game->GetTextureStageState(0, D3DTSS_ALPHAOP, &stage0AlphaOp)) ||
        FAILED(game->GetTextureStageState(0, D3DTSS_ALPHAARG1, &stage0Alpha1)) ||
        FAILED(game->GetTextureStageState(0, D3DTSS_ALPHAARG2, &stage0Alpha2)) ||
        FAILED(game->GetTextureStageState(1, D3DTSS_COLOROP, &followingColorOp)))
        return false;
    const bool diffuseOnly = game_fvf_diffuse_only_inactive_texture(
        stage0Op, stage0Arg1, stage0Arg2,
        stage0AlphaOp, stage0Alpha1, stage0Alpha2,
        followingColorOp, layout.hasDiffuse);
    capture.inactiveStage0TextureBypass = diffuseOnly && layout.textured;
    capture.enabled = layout.textured && !diffuseOnly;
    // Native VS has no additive specular interpolant. Object-space NORMAL
    // is valid only when D3DRS_LIGHTING is disabled below.
    if (layout.hasSpecular) {
        DWORD specularEnabled = TRUE;
        if (FAILED(game->GetRenderState(D3DRS_SPECULARENABLE, &specularEnabled)) ||
            specularEnabled)
            return false;
    }
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
    } else if (tex && !diffuseOnly) {
        // A game-authored texture binding is ignored only after proving the
        // complete live RGB/alpha/next-stage combiner reads vertex DIFFUSE.
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
        !clip || fog || fillMode != D3DFILL_SOLID)
        return false;
    // The live game's stencil-enabled Draw can still write real main color:
    // ALWAYS + a zero write mask + one-sided stencil is pixel-equivalent to
    // disabled stencil for every D3D11 fragment (no stencil dependency/write).
    // Do not merely drop stencil for an unproved comparison or CCW mode.
    DWORD stencilFunc = 0u, stencilWriteMask = 0xffffffffu, twoSided = TRUE;
    const bool stencilKnown = stencil == FALSE ||
        (SUCCEEDED(game->GetRenderState(D3DRS_STENCILFUNC, &stencilFunc)) &&
         SUCCEEDED(game->GetRenderState(D3DRS_STENCILWRITEMASK, &stencilWriteMask)) &&
         SUCCEEDED(game->GetRenderState(D3DRS_TWOSIDEDSTENCILMODE, &twoSided)));
    if (!GameNativeInertStencilMrt::stencil_equivalent_to_disabled(
            stencil != FALSE, stencilKnown, stencilFunc,
            stencilWriteMask, twoSided != FALSE))
        return false;
    if (fullFrame) {
        // Live menu/vehicle/race Draws can leave MRT1..3 bound with their
        // independent masks at zero. D3D11's one-RT native frame may mirror
        // RT0 in that case. A writable or unknown MRT would be lost, so cancel
        // the optional native frame and preserve actual D3D9 output instead.
        D3DCAPS9 caps{};
        if (FAILED(game->GetDeviceCaps(&caps)) ||
            !GameNativeOffscreenPass::valid_mrt_count(caps.NumSimultaneousRTs))
            return false;
        constexpr D3DRENDERSTATETYPE extraColorMasks[] = {
            D3DRS_COLORWRITEENABLE1, D3DRS_COLORWRITEENABLE2,
            D3DRS_COLORWRITEENABLE3
        };
        for (DWORD slot = 1u; slot < caps.NumSimultaneousRTs; ++slot) {
            ComPtr<IDirect3DSurface9> extra;
            const HRESULT hr = game->GetRenderTarget(slot, extra.GetAddressOf());
            if (hr == D3DERR_NOTFOUND) continue;
            DWORD extraMask = 0xffffffffu;
            if (FAILED(hr) || !extra ||
                FAILED(game->GetRenderState(extraColorMasks[slot - 1u],
                                            &extraMask)) ||
                !GameNativeInertStencilMrt::extra_target_inert(true, extraMask))
                return false;
        }
    }
    GameNativeCullAdmission admittedCull{};
    if (!game_native_cull_admission(
            cullMode, static_cast<std::uint32_t>(topology), admittedCull))
        return false;
    output.nativeCullMode = admittedCull.d3d9Mode;
    // Mirror only one isolated game-authored Z draw. The newly cleared DSV
    // omits earlier D3D9 occluders: this is diagnostic, NOT scene parity.
    // W-buffering, depth-bias and missing depth fail closed; depth-read-only
    // draws keep Z comparison but never update the native diagnostic DSV.
    if (depth != D3DZB_FALSE) {
        DWORD zWrite = 0, zFunc = 0, bias = ~0u, slopeBias = ~0u;
        ComPtr<IDirect3DSurface9> gameDepth;
        D3DSURFACE_DESC depthDesc{};
        if (FAILED(game->GetRenderState(D3DRS_ZWRITEENABLE, &zWrite)) ||
            FAILED(game->GetRenderState(D3DRS_ZFUNC, &zFunc)) ||
            FAILED(game->GetRenderState(D3DRS_DEPTHBIAS, &bias)) ||
            FAILED(game->GetRenderState(D3DRS_SLOPESCALEDEPTHBIAS, &slopeBias)) ||
            FAILED(game->GetDepthStencilSurface(gameDepth.GetAddressOf())) ||
            !gameDepth || FAILED(gameDepth->GetDesc(&depthDesc)))
            return false;
        GameNativeDepthAdmission admitted{};
        if (!game_native_depth_admission(
                depth, zWrite, zFunc, bias, slopeBias,
                depthDesc.MultiSampleType == D3DMULTISAMPLE_NONE, admitted))
            return false;
        output.nativeDepthTest = admitted.enabled;
        output.nativeDepthLessEqual = admitted.lessEqual;
        output.nativeDepthWrite = admitted.writeEnabled;
        output.nativeDepthAlways = admitted.always;
        output.nativeDepthEqualityMode = admitted.equalityMode;
        output.nativeDepthOrderingMode = admitted.orderingMode;
    }
    // Only native one-pixel points without sprites or per-vertex point sizes.
    // All larger/scaled point raster states continue to the original D3D9
    // Draw only; do not display a misleading native menu/effect inset.
    if (topology == D3DPT_POINTLIST) {
        DWORD size = 0u, minSize = 0u, maxSize = 0u;
        DWORD sprite = TRUE, scale = TRUE;
        if (FAILED(game->GetRenderState(D3DRS_POINTSIZE, &size)) ||
            FAILED(game->GetRenderState(D3DRS_POINTSIZE_MIN, &minSize)) ||
            FAILED(game->GetRenderState(D3DRS_POINTSIZE_MAX, &maxSize)) ||
            FAILED(game->GetRenderState(D3DRS_POINTSPRITEENABLE, &sprite)) ||
            FAILED(game->GetRenderState(D3DRS_POINTSCALEENABLE, &scale)) ||
            !game_native_unit_point_raster(size, minSize, maxSize,
                                           sprite, scale, layout.hasPointSize))
            return false;
    }
    // Lines with D3D9-specific AA/last-pixel behavior cannot be represented
    // exactly by this single-sample native diagnostic target: fail closed.
    if (topology == D3DPT_LINELIST || topology == D3DPT_LINESTRIP) {
        DWORD lineAA = TRUE, lastPixel = FALSE;
        if (FAILED(game->GetRenderState(D3DRS_ANTIALIASEDLINEENABLE, &lineAA)) ||
            FAILED(game->GetRenderState(D3DRS_LASTPIXEL, &lastPixel)) ||
            lineAA != FALSE || lastPixel != TRUE)
            return false;
    }
    const DWORD legalMask = D3DCOLORWRITEENABLE_RED | D3DCOLORWRITEENABLE_GREEN |
                            D3DCOLORWRITEENABLE_BLUE | D3DCOLORWRITEENABLE_ALPHA;
    const DWORD visibleMask = D3DCOLORWRITEENABLE_RED | D3DCOLORWRITEENABLE_GREEN |
                              D3DCOLORWRITEENABLE_BLUE;
    // The inset remains RGB-only. Full-size A8 destination alpha is sampled
    // by later game blend passes; a source depth-write-only game Draw updates
    // native DSV even when RGB is masked off. Reject unobservable or unknown
    // writes and retain original D3D9 gamepad/Draw/Present as fallback.
    if ((colorMask & ~legalMask) ||
        (!(colorMask & visibleMask) &&
         !GameNativeMaskedDraw::accepts_source_mask(
             colorMask, fullFrame, sourceDesc.Format == D3DFMT_A8R8G8B8,
             output.nativeDepthTest && output.nativeDepthWrite)))
        return false;
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
            static_cast<double>(left) * output.nativeWidth / sourceDesc.Width));
        const LONG nativeTop = static_cast<LONG>(std::ceil(
            static_cast<double>(top) * output.nativeHeight / sourceDesc.Height));
        const LONG nativeRight = static_cast<LONG>(std::floor(
            static_cast<double>(right) * output.nativeWidth / sourceDesc.Width));
        const LONG nativeBottom = static_cast<LONG>(std::floor(
            static_cast<double>(bottom) * output.nativeHeight / sourceDesc.Height));
        if (nativeRight <= nativeLeft || nativeBottom <= nativeTop)
            return false;
        output.scissor = true;
        output.nativeScissor = {nativeLeft, nativeTop, nativeRight, nativeBottom};
    }
    // D3D9 sprite/menu draw states. Mirror the complete 8-bit alpha compare
    // family, but continue to reject unsupported blend factors/separate alpha.
    if (blend) {
        DWORD src = 0, dst = 0, blendOp = 0, separate = TRUE;
        if (FAILED(game->GetRenderState(D3DRS_SRCBLEND, &src)) ||
            FAILED(game->GetRenderState(D3DRS_DESTBLEND, &dst)) ||
            FAILED(game->GetRenderState(D3DRS_BLENDOP, &blendOp)) ||
            FAILED(game->GetRenderState(D3DRS_SEPARATEALPHABLENDENABLE, &separate)))
            return false;
        // Capture the actual independent game alpha operation only when
        // enabled. Never use RGB factors as a surrogate for a menu fade.
        if (separate != FALSE) {
            DWORD srcAlpha = 0u, dstAlpha = 0u, opAlpha = 0u;
            if (FAILED(game->GetRenderState(D3DRS_SRCBLENDALPHA, &srcAlpha)) ||
                FAILED(game->GetRenderState(D3DRS_DESTBLENDALPHA, &dstAlpha)) ||
                FAILED(game->GetRenderState(D3DRS_BLENDOPALPHA, &opAlpha)) ||
                !native_game_separate_alpha(srcAlpha, dstAlpha, opAlpha,
                    output.nativeSrcAlpha, output.nativeDstAlpha,
                    output.nativeAlphaOp))
                return false;
            output.separateAlphaBlend = true;
        }
        // Real D3D9 menu/car overlay MIN/MAX ignores the blend factors;
        // D3D11 has the same RGB/alpha extrema operations. Admit only
        // separately tested common factor pairs with no independent alpha.
        const bool extrema = blendOp == D3DBLENDOP_MIN ||
                             blendOp == D3DBLENDOP_MAX;
        if (extrema && !game_native_extremum_admission(
                blendOp, src, dst, separate != FALSE, colorMask))
            return false;
        if (blendOp != D3DBLENDOP_ADD) {
            if (blendOp != D3DBLENDOP_SUBTRACT &&
                blendOp != D3DBLENDOP_REVSUBTRACT && !extrema) return false;
        }
        // Only exact known-good over/ONE+ONE/SRCALPHA+ONE game combinations.
        const bool additive = src == D3DBLEND_ONE && dst == D3DBLEND_ONE;
        const bool sourceAlphaAdd = src == D3DBLEND_SRCALPHA &&
                                    dst == D3DBLEND_ONE;
        const bool premultipliedAlpha = src == D3DBLEND_ONE &&
                                        dst == D3DBLEND_INVSRCALPHA;
        const bool multiply =
            (src == D3DBLEND_DESTCOLOR && dst == D3DBLEND_ZERO) ||
            (src == D3DBLEND_ZERO && dst == D3DBLEND_SRCCOLOR);
        const bool inverseDestMultiply =
            src == D3DBLEND_INVDESTCOLOR && dst == D3DBLEND_ZERO;
        const bool inverseSourceMultiply =
            src == D3DBLEND_ZERO && dst == D3DBLEND_INVSRCCOLOR;
        const bool destAlphaCrossfade =
            src == D3DBLEND_DESTALPHA && dst == D3DBLEND_INVDESTALPHA;
        const bool reverseDestAlphaCrossfade =
            src == D3DBLEND_INVDESTALPHA && dst == D3DBLEND_DESTALPHA;
        const bool sourceAlphaSaturateCopy =
            src == D3DBLEND_SRCALPHASAT && dst == D3DBLEND_ZERO;
        const bool sourceAlphaSaturateAdd =
            src == D3DBLEND_SRCALPHASAT && dst == D3DBLEND_ONE;
        // D3D9 BOTH* source blend enums set both source and destination
        // factors, ignoring D3DRS_DESTBLEND. BOTHSRCALPHA reuses native
        // SRCALPHA/INVSRCALPHA; BOTHINVSRCALPHA needs inverse-over OM.
        const bool bothSourceAlpha = src == D3DBLEND_BOTHSRCALPHA;
        const bool inverseSourceAlpha = src == D3DBLEND_BOTHINVSRCALPHA;
        const bool sourceAlphaCopy = src == D3DBLEND_SRCALPHA && dst == D3DBLEND_ZERO;
        const bool inverseAlphaCopy = src == D3DBLEND_INVSRCALPHA && dst == D3DBLEND_ZERO;
        const bool inverseAlphaAdd = src == D3DBLEND_INVSRCALPHA && dst == D3DBLEND_ONE;
        const bool sourceReplace = src == D3DBLEND_ONE && dst == D3DBLEND_ZERO;
        // Inverse-over is currently ADD-only. Preserve DX9Ex fallback for
        // directional subtracts until independently verified.
        if (inverseSourceAlpha && blendOp != D3DBLENDOP_ADD) return false;
        // Destination-free source attenuation is admitted only with ADD.
        // Other equations remain game-owned rather than borrowing OM slots.
        if (sourceAlphaCopy && blendOp != D3DBLENDOP_ADD) return false;
        if ((inverseAlphaCopy || inverseAlphaAdd) && blendOp != D3DBLENDOP_ADD)
            return false;
        // Reverse-subtract would invert source; preserve the original DX9Ex
        // path instead of reusing an ADD-only source-replacement descriptor.
        if (sourceReplace && blendOp != D3DBLENDOP_ADD) return false;
        // The two multiply factor orders are equivalent for ADD only:
        // subtractive operations are directional. Keep them on D3D9 rather
        // than incorrectly substituting the canonical DESTCOLOR/ZERO state.
        if (multiply && blendOp != D3DBLENDOP_ADD) return false;
        // Complement multiplication is defined only for ADD with non-separate
        // alpha. Directional subtract cannot borrow the source/dest OM slots.
        if ((inverseDestMultiply || inverseSourceMultiply) &&
            blendOp != D3DBLENDOP_ADD) return false;
        // Destination-alpha crossfade never borrows subtract/reverse-subtract
        // or separate alpha descriptors. Unsupported game draws stay on D3D9.
        if ((destAlphaCrossfade || reverseDestAlphaCrossfade) &&
            blendOp != D3DBLENDOP_ADD) return false;
        // Newly supported complement pairs use different but exact ADD-only
        // OM descriptors. Keep original legacy allowlist text intact so
        // older destructive mutations still exercise their own factors.
        if (inverseDestMultiply || inverseSourceMultiply) {
            // Original 00606 allowlist remains independent, preserving its
            // per-pair negative regression checks and original D3D9 fallback.
        } else if (destAlphaCrossfade || reverseDestAlphaCrossfade) {
            // Both dest-alpha crossfades were attested as ADD/non-separate
            // above and use their own forward/reverse native OM descriptors.
        } else if (sourceAlphaSaturateCopy || sourceAlphaSaturateAdd) {
            // Unsupported subtract/separate-alpha must remain on original D3D9.
            if (blendOp != D3DBLENDOP_ADD) return false;
        } else if (!premultipliedAlpha && !multiply &&
            !sourceAlphaCopy && !sourceReplace &&
            !inverseAlphaCopy && !inverseAlphaAdd &&
            (src != D3DBLEND_SRCALPHA || dst != D3DBLEND_INVSRCALPHA) &&
            !bothSourceAlpha && !inverseSourceAlpha &&
            !additive && !sourceAlphaAdd) return false;
        output.alphaBlend = true;
        output.additiveBlend = additive;
        output.sourceAlphaAddBlend = sourceAlphaAdd;
        output.premultipliedAlphaBlend = premultipliedAlpha;
        output.inverseSourceAlphaBlend = inverseSourceAlpha;
        output.sourceAlphaCopyBlend = sourceAlphaCopy;
        output.inverseAlphaCopyBlend = inverseAlphaCopy;
        output.inverseAlphaAddBlend = inverseAlphaAdd;
        output.sourceReplaceBlend = sourceReplace;
        output.multiplyBlend = multiply;
        output.inverseDestMultiplyBlend = inverseDestMultiply;
        output.inverseSourceMultiplyBlend = inverseSourceMultiply;
        output.destAlphaCrossfadeBlend = destAlphaCrossfade;
        output.reverseDestAlphaCrossfadeBlend = reverseDestAlphaCrossfade;
        output.sourceAlphaSaturateCopyBlend = sourceAlphaSaturateCopy;
        output.sourceAlphaSaturateAddBlend = sourceAlphaSaturateAdd;
        output.blendOp = blendOp == D3DBLENDOP_SUBTRACT ?
            D3D11_BLEND_OP_SUBTRACT :
            blendOp == D3DBLENDOP_REVSUBTRACT ?
            D3D11_BLEND_OP_REV_SUBTRACT : D3D11_BLEND_OP_ADD;
        // Preserve independent SUBTRACT/REVSUBTRACT mapping, then override
        // only the newly admitted extrema RGB/alpha operator.
        if (extrema) output.blendOp = blendOp == D3DBLENDOP_MIN ?
            D3D11_BLEND_OP_MIN : D3D11_BLEND_OP_MAX;
    }
    if (alpha) {
        DWORD func = 0, reference = ~0u;
        if (FAILED(game->GetRenderState(D3DRS_ALPHAFUNC, &func)) ||
            FAILED(game->GetRenderState(D3DRS_ALPHAREF, &reference)) ||
            ((func != D3DCMP_GREATER && func != D3DCMP_GREATEREQUAL) &&
             func != D3DCMP_NEVER && func != D3DCMP_LESS &&
             func != D3DCMP_EQUAL && func != D3DCMP_LESSEQUAL &&
             func != D3DCMP_NOTEQUAL && func != D3DCMP_ALWAYS) ||
            reference > 255u)
            return false;
        output.alphaTest = true;
        output.alphaFunc = static_cast<D3DCMPFUNC>(func);
        output.alphaRef = reference;
    }
    DWORD op=0, arg=0, nextColorOp=0, resultArg=0;
    // A later fixed-function texture stage can still change the result even
    // when stage 0 selects DIFFUSE. Reject it rather than mislabel an altered
    // game draw as native color parity; the original DX9Ex draw still runs.
    if (FAILED(game->GetTextureStageState(0, D3DTSS_COLOROP, &op)) ||
        FAILED(game->GetTextureStageState(0, D3DTSS_COLORARG1, &arg)) ||
        FAILED(game->GetTextureStageState(1, D3DTSS_COLOROP, &nextColorOp)) ||
        FAILED(game->GetTextureStageState(0, D3DTSS_RESULTARG, &resultArg)) ||
        (resultArg != D3DTA_CURRENT &&
         !(resultArg == D3DTA_TEMP && nextColorOp > D3DTOP_DISABLE && layout.hasDiffuse)))
        return false;
    // The native PS writes the stage-0 result directly to the frame.
    // D3DTA_TEMP would leave CURRENT unchanged, so this diagnostic must
    // preserve the original D3D9 Draw instead of mirroring a false color.
    if (!capture.enabled) {
        // D3D9 stage 0 CURRENT is the incoming vertex DIFFUSE. An untextured
        // menu/sprite Draw can select that color from ARG1 or ARG2, with its
        // alpha independently selected. The native PS reads only v.diffuse;
        // reject any other RGB/alpha source or modifier rather than display
        // a misleading inset (the original D3D9 Draw is never intercepted).
        DWORD arg2 = 0, alphaOp = 0, alphaArg1 = 0, alphaArg2 = 0;
        if (!layout.hasDiffuse ||
            FAILED(game->GetTextureStageState(0, D3DTSS_COLORARG2, &arg2)) ||
            FAILED(game->GetTextureStageState(0, D3DTSS_ALPHAOP, &alphaOp)) ||
            FAILED(game->GetTextureStageState(0, D3DTSS_ALPHAARG1, &alphaArg1)) ||
            FAILED(game->GetTextureStageState(0, D3DTSS_ALPHAARG2, &alphaArg2)))
            return false;
        // D3D9 stage-0 COLOROP DISABLE ends downstream texture stages
        // and implicitly disables alpha, leaving the vertex diffuse RGBA.
        // Connect real untextured menu/car-selection FVF to native Draw.
        if (!game_fvf_untextured_stage0(
                op, arg, arg2, alphaOp, alphaArg1, alphaArg2,
                nextColorOp, layout.hasDiffuse)) return false;
    }
    if (capture.enabled) {
        DWORD arg2=0, alphaOp=0, alphaArg1=0, alphaArg2=0;
        DWORD coordIndex=~0u, transformFlags=~0u;
        DWORD addressU=0, addressV=0, mag=0, min=0, mip=0, srgb=1;
        DWORD borderColor = 0u;
        DWORD maxMip=~0u, mipBias=~0u, maxAniso=0u, srgbWrite=TRUE;
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
            FAILED(game->GetSamplerState(0, D3DSAMP_MAXMIPLEVEL, &maxMip)) ||
            FAILED(game->GetSamplerState(0, D3DSAMP_MIPMAPLODBIAS, &mipBias)) ||
            FAILED(game->GetSamplerState(0, D3DSAMP_SRGBTEXTURE, &srgb)) ||
            FAILED(game->GetRenderState(D3DRS_SRGBWRITEENABLE, &srgbWrite)) ||
            srgbWrite != FALSE)
            return false;
        // Capture the live D3D9 anisotropy only when the game uses it.
        if (min == D3DTEXF_ANISOTROPIC &&
            FAILED(game->GetSamplerState(0, D3DSAMP_MAXANISOTROPY, &maxAniso)))
            return false;
        // Sampled BORDER U or V needs game-authored ARGB rather than D3D11 zero.
        // Failure stays on original D3D9 Draw, with no native submission.
        if ((addressU == D3DTADDRESS_BORDER || addressV == D3DTADDRESS_BORDER) &&
            FAILED(game->GetSamplerState(0, D3DSAMP_BORDERCOLOR, &borderColor)))
            return false;
        // D3D9 COUNT2 takes (u,v,1,0); projective and other counts fail closed.
        const bool transformUv = transformFlags == D3DTTFF_COUNT2;
        // COUNT2 transform semantics can depend on the source coordinate
        // width; do not reinterpret a packed TEXCOORDSIZE3 under COUNT2.
        if (transformUv && layout.texcoord3DMask != 0u) return false;
        if (transformUv && layout.texcoord4DMask != 0u) return false;
        D3DMATRIX uvTransform{};
        if (transformUv && FAILED(game->GetTransform(D3DTS_TEXTURE0, &uvTransform)))
            return false;
        // DWORD MIPMAPLODBIAS contains IEEE-754 bits; numeric conversion loses
        // the game's fractional/negative offset. Validate before native capture.
        float decodedMipBias = 0.0f;
        static_assert(sizeof(decodedMipBias) == sizeof(mipBias));
        std::memcpy(&decodedMipBias, &mipBias, sizeof(decodedMipBias));
        const bool validMipBias = std::isfinite(decodedMipBias) &&
                                 decodedMipBias >= kMinMipLodBias &&
                                 decodedMipBias <= kMaxMipLodBias;
        // D3D9 MIN_ANISOTROPIC with MAG_LINEAR or MAG_ANISOTROPIC
        // maps to D3D11 ANISOTROPIC with the full MIP_LINEAR chain.
        // Other MAG-aniso combinations remain on the original D3D9 Draw.
        const bool anisotropic = min == D3DTEXF_ANISOTROPIC &&
            (mag == D3DTEXF_LINEAR || mag == D3DTEXF_ANISOTROPIC) &&
            mip == D3DTEXF_LINEAR &&
            maxAniso >= 2u && maxAniso <= D3D11_REQ_MAXANISOTROPY;
        // Fixed-function stage 0 CURRENT is the incoming vertex DIFFUSE.
        // With stage 0 writing CURRENT, the stage-0 starting source is DIFFUSE.
        // BLENDCURRENTALPHA is pixel-identical to the already supported
        // BLENDDIFFUSEALPHA native shaders. Normalize color and alpha
        // independently before the existing operand/variant/fallback gate.
        // In other stages or without game-authored diffuse, fail closed.
        const bool stage0CurrentIsDiffuse =
            layout.hasDiffuse && resultArg == D3DTA_CURRENT;
        op = canonical_game_stage0_blend_alpha_op(op, stage0CurrentIsDiffuse);
        // Keep PM CURRENT alpha distinguishable for its exact native shaders.
        // Otherwise the 00641/00642 predicates are dead after canonicalization.
        alphaOp = canonical_game_stage0_pm_alpha_op(
            op, alphaOp, stage0CurrentIsDiffuse);
        capture.stage0FullModulate =
            op == D3DTOP_MODULATE && alphaOp == D3DTOP_MODULATE;
        // Full CPU-readable mip chain required; aniso and invalid inputs
        // retain the original D3D9 Draw path without native promotion.
        // Reject complement/alpha-replicate modifiers and projected coordinates.
        const bool blendTextureModulateAlpha = op == D3DTOP_BLENDTEXTUREALPHA &&
                                                alphaOp == D3DTOP_MODULATE;
        const bool blendDiffuseModulateAlpha = op == D3DTOP_BLENDDIFFUSEALPHA &&
                                                alphaOp == D3DTOP_MODULATE;
        const bool blendTextureModulate2XAlpha = op == D3DTOP_BLENDTEXTUREALPHA &&
                                         alphaOp == D3DTOP_MODULATE2X;
        const bool blendTextureModulate4XAlpha = op == D3DTOP_BLENDTEXTUREALPHA &&
                                         alphaOp == D3DTOP_MODULATE4X;
        const bool blendDiffuseModulate2XAlpha = op == D3DTOP_BLENDDIFFUSEALPHA &&
                                         alphaOp == D3DTOP_MODULATE2X;
        const bool blendDiffuseModulate4XAlpha = op == D3DTOP_BLENDDIFFUSEALPHA &&
                                         alphaOp == D3DTOP_MODULATE4X;
        const bool blendTextureAddAlpha = op == D3DTOP_BLENDTEXTUREALPHA &&
                                          alphaOp == D3DTOP_ADD;
        const bool blendDiffuseAddAlpha = op == D3DTOP_BLENDDIFFUSEALPHA &&
                                          alphaOp == D3DTOP_ADD;
        const bool blendTextureSubtractAlpha = op == D3DTOP_BLENDTEXTUREALPHA &&
                                               alphaOp == D3DTOP_SUBTRACT;
        const bool blendDiffuseSubtractAlpha = op == D3DTOP_BLENDDIFFUSEALPHA &&
                                               alphaOp == D3DTOP_SUBTRACT;
        const bool blendTextureAddSmoothAlpha = op == D3DTOP_BLENDTEXTUREALPHA &&
                                                alphaOp == D3DTOP_ADDSMOOTH;
        const bool blendDiffuseAddSmoothAlpha = op == D3DTOP_BLENDDIFFUSEALPHA &&
                                                alphaOp == D3DTOP_ADDSMOOTH;
        const bool blendFactorAlpha = op == D3DTOP_BLENDFACTORALPHA &&
                                      alphaOp == D3DTOP_BLENDFACTORALPHA;
        // Admit only the exact two mixed-alpha variants, never arbitrary ops.
        const bool blendFactorTextureAlpha = op == D3DTOP_BLENDFACTORALPHA &&
                                             alphaOp == D3DTOP_SELECTARG1;
        const bool blendFactorModulateAlpha = op == D3DTOP_BLENDFACTORALPHA &&
                                              alphaOp == D3DTOP_MODULATE;
        const bool blendFactorDiffuseAlpha = op == D3DTOP_BLENDFACTORALPHA &&
                                             alphaOp == D3DTOP_SELECTARG2;
        const bool blendFactorAddAlpha = op == D3DTOP_BLENDFACTORALPHA &&
                                         alphaOp == D3DTOP_ADD;
        const bool blendFactorSubtractAlpha = op == D3DTOP_BLENDFACTORALPHA &&
                                              alphaOp == D3DTOP_SUBTRACT;
        const bool blendFactorAddSmoothAlpha = op == D3DTOP_BLENDFACTORALPHA &&
                                               alphaOp == D3DTOP_ADDSMOOTH;
        const bool blendFactorModulate2XAlpha = op == D3DTOP_BLENDFACTORALPHA &&
                                                alphaOp == D3DTOP_MODULATE2X;
        const bool blendFactorModulate4XAlpha = op == D3DTOP_BLENDFACTORALPHA &&
                                                alphaOp == D3DTOP_MODULATE4X;
        const bool modulate = op == D3DTOP_MODULATE && alphaOp == D3DTOP_MODULATE;
        const bool selectTexture = op == D3DTOP_SELECTARG1 && alphaOp == D3DTOP_SELECTARG1;
        const bool selectTextureDiffuseAlpha = op == D3DTOP_SELECTARG1 &&
                                               alphaOp == D3DTOP_SELECTARG2;
        const bool selectTextureModulateAlpha = op == D3DTOP_SELECTARG1 &&
                                                alphaOp == D3DTOP_MODULATE;
        const bool selectTextureModulate2XAlpha = op == D3DTOP_SELECTARG1 &&
                                                  alphaOp == D3DTOP_MODULATE2X;
        const bool selectTextureModulate4XAlpha = op == D3DTOP_SELECTARG1 &&
                                                  alphaOp == D3DTOP_MODULATE4X;
        const bool selectTextureAddAlpha = op == D3DTOP_SELECTARG1 &&
                                           alphaOp == D3DTOP_ADD;
        const bool selectTextureSubtractAlpha = op == D3DTOP_SELECTARG1 &&
                                                alphaOp == D3DTOP_SUBTRACT;
        const bool selectTextureAddSmoothAlpha = op == D3DTOP_SELECTARG1 &&
                                                 alphaOp == D3DTOP_ADDSMOOTH;
        const bool selectTextureFactorAlpha = op == D3DTOP_SELECTARG1 &&
                                      alphaOp == D3DTOP_BLENDFACTORALPHA;
        // Stage0 CURRENT is vertex DIFFUSE. RGB selects ARG2 independently.
        const bool selectDiffuseTextureAlpha = op == D3DTOP_SELECTARG2 &&
                                               alphaOp == D3DTOP_SELECTARG1;
        const bool selectDiffuseDiffuseAlpha = op == D3DTOP_SELECTARG2 &&
                                               alphaOp == D3DTOP_SELECTARG2;
        const bool selectDiffuseModulateAlpha = op == D3DTOP_SELECTARG2 &&
                                                alphaOp == D3DTOP_MODULATE;
        const bool selectDiffuseAddAlpha = op == D3DTOP_SELECTARG2 &&
                                           alphaOp == D3DTOP_ADD;
        const bool selectDiffuseSubtractAlpha = op == D3DTOP_SELECTARG2 &&
                                                alphaOp == D3DTOP_SUBTRACT;
        const bool selectDiffuseModulate2XAlpha = op == D3DTOP_SELECTARG2 &&
                                                  alphaOp == D3DTOP_MODULATE2X;
        const bool selectDiffuseModulate4XAlpha = op == D3DTOP_SELECTARG2 &&
                                                  alphaOp == D3DTOP_MODULATE4X;
        const bool selectDiffuseAddSmoothAlpha = op == D3DTOP_SELECTARG2 &&
                                                 alphaOp == D3DTOP_ADDSMOOTH;
        const bool selectDiffuseFactorAlpha = op == D3DTOP_SELECTARG2 &&
                                      alphaOp == D3DTOP_BLENDFACTORALPHA;
        const bool selectTextureBlendTextureAlpha = op == D3DTOP_SELECTARG1 &&
            alphaOp == D3DTOP_BLENDTEXTUREALPHA;
        const bool selectDiffuseBlendTextureAlpha = op == D3DTOP_SELECTARG2 &&
            alphaOp == D3DTOP_BLENDTEXTUREALPHA;
        const bool selectTextureBlendDiffuseAlpha = op == D3DTOP_SELECTARG1 &&
            alphaOp == D3DTOP_BLENDDIFFUSEALPHA;
        const bool selectDiffuseBlendDiffuseAlpha = op == D3DTOP_SELECTARG2 &&
            alphaOp == D3DTOP_BLENDDIFFUSEALPHA;
        // D3D9 fixed-function stage 0 permits unmodified TFACTOR alpha
        // independently of the texture or DIFFUSE/CURRENT RGB selection.
        const bool selectTextureTfactorAlpha = op == D3DTOP_SELECTARG1 &&
            alphaOp == D3DTOP_SELECTARG1 && alphaArg1 == D3DTA_TFACTOR;
        const bool selectDiffuseTfactorAlpha = op == D3DTOP_SELECTARG2 &&
            alphaOp == D3DTOP_SELECTARG1 && alphaArg1 == D3DTA_TFACTOR;
        // SELECTARG2 alpha reads ALPHAARG2, not ALPHAARG1. Reuse the
        // verified texture-factor shader and its 8-bit high-byte constant.
        const bool selectTextureTfactorArg2Alpha = op == D3DTOP_SELECTARG1 &&
            alphaOp == D3DTOP_SELECTARG2 && alphaArg2 == D3DTA_TFACTOR;
        const bool selectDiffuseTfactorArg2Alpha = op == D3DTOP_SELECTARG2 &&
            alphaOp == D3DTOP_SELECTARG2 && alphaArg2 == D3DTA_TFACTOR;
        // Only this exact PM RGB / factor-alpha operation is admitted.
        const bool blendTextureAlphaPMFactorAlpha = op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_SELECTARG1 && alphaArg1 == D3DTA_TFACTOR;
        // SELECTARG2 reads only ALPHAARG2. Route an unmodified TFACTOR
        // high-byte to the already compiled native PM RGB/factor-alpha PS.
        // Never alias this to the earlier SELECTARG2 vertex-diffuse PS.
        const bool blendTextureAlphaPMFactorArg2Alpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_SELECTARG2 && alphaArg2 == D3DTA_TFACTOR;
        // Stage 0 PM RGB with independent MODULATE(TEXTURE, TFACTOR) alpha.
        // Other operand orders and modifiers retain the original D3D9 draw.
        const bool blendTextureAlphaPMModulateFactorAlpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_MODULATE &&
            alphaArg1 == D3DTA_TEXTURE && alphaArg2 == D3DTA_TFACTOR;
        // 00637: D3D9 alpha MODULATE(TEXTURE, 1 - TFACTOR) still uses
        // original TEXTURE alpha as the PM RGB interpolation weight.  Reuse
        // the same native PS only after reading and inverting the actual
        // game-authored factor; all other modified alpha operands fail closed.
        const bool blendTextureAlphaPMModulateInverseFactorAlpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_MODULATE &&
            alphaArg1 == D3DTA_TEXTURE &&
            alphaArg2 == (D3DTA_TFACTOR | D3DTA_COMPLEMENT);
        // Scaled D3D9 alpha factors: 2X/4X multiply TEXTURE alpha and live
        // TFACTOR alpha; saturation occurs before AlphaGate and OM blending.
        // RGB remains premultiplied by the original *unscaled* texture alpha.
        const bool blendTextureAlphaPMScaledFactorAlpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            (alphaOp == D3DTOP_MODULATE2X || alphaOp == D3DTOP_MODULATE4X) &&
            alphaArg1 == D3DTA_TEXTURE && alphaArg2 == D3DTA_TFACTOR;
        const bool blendTextureAlphaPMScaledInverseFactorAlpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            (alphaOp == D3DTOP_MODULATE2X || alphaOp == D3DTOP_MODULATE4X) &&
            alphaArg1 == D3DTA_TEXTURE &&
            alphaArg2 == (D3DTA_TFACTOR | D3DTA_COMPLEMENT);
        // D3D9 complement belongs to the active alpha operand, never to
        // the sampled texture-alpha used by premultiplied RGB blending.
        const bool blendTextureAlphaPMInverseFactorArg1Alpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_SELECTARG1 &&
            alphaArg1 == (D3DTA_TFACTOR | D3DTA_COMPLEMENT);
        const bool blendTextureAlphaPMInverseFactorArg2Alpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_SELECTARG2 &&
            alphaArg2 == (D3DTA_TFACTOR | D3DTA_COMPLEMENT);
        // Game SELECTARG1 reads ALPHAARG1 only; unmodified vertex DIFFUSE
        // and stage-0 CURRENT use the existing native PM/diffuse-alpha PS.
        // Inactive ALPHAARG2 must not affect this operation.
        const bool blendTextureAlphaPMDiffuseArg1Alpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_SELECTARG1 &&
            (alphaArg1 == D3DTA_DIFFUSE || alphaArg1 == D3DTA_CURRENT);
        // Live game PM RGB retains the original texture alpha for RGB weighting,
        // independently complementing only SELECTARG1 TEXTURE alpha.
        // Reject other sources, modifiers, and reverse SELECTARG2 combinations.
        const bool blendTextureAlphaPMInverseTextureAlpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_SELECTARG1 &&
            alphaArg1 == (D3DTA_TEXTURE | D3DTA_COMPLEMENT);
        // SELECTARG2 consumes ALPHAARG2, never the inactive ALPHAARG1.
        // Keep the unmodified sampled alpha for PM RGB weighting, but emit
        // complemented sampled alpha through the already compiled native PS.
        const bool blendTextureAlphaPMInverseTextureArg2Alpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_SELECTARG2 &&
            alphaArg2 == (D3DTA_TEXTURE | D3DTA_COMPLEMENT);
        // D3D9 stage0 CURRENT is vertex DIFFUSE; only an active alpha operand
        // may be complemented. No unrecognized flags reach the native draw.
        const bool blendTextureAlphaPMInverseDiffuseArg1Alpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_SELECTARG1 &&
            (alphaArg1 == (D3DTA_DIFFUSE | D3DTA_COMPLEMENT) ||
             alphaArg1 == (D3DTA_CURRENT | D3DTA_COMPLEMENT));
        const bool blendTextureAlphaPMInverseDiffuseArg2Alpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_SELECTARG2 &&
            (alphaArg2 == (D3DTA_DIFFUSE | D3DTA_COMPLEMENT) ||
             alphaArg2 == (D3DTA_CURRENT | D3DTA_COMPLEMENT));
        const bool blendTextureAlphaPMInverseDiffuseAlpha =
            blendTextureAlphaPMInverseDiffuseArg1Alpha ||
            blendTextureAlphaPMInverseDiffuseArg2Alpha;
        // Reject other alpha operand modifiers, TFACTOR and reverse ordering.
        const bool blendTextureAlphaPMModulateAlpha = op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_MODULATE && alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT);
        // D3D9 ADD alpha uses unmodified ARG1=TEXTURE and ARG2=DIFFUSE/CURRENT;
        // PM RGB remains texture-alpha weighted, not ADD RGB.
        const bool blendTextureAlphaPMAddAlpha = op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_ADD && alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT);
        // SUBTRACT alpha is a distinct saturating texture-minus-diffuse operation;
        // reject swapped or modified operands and preserve the D3D9 fallback.
        const bool blendTextureAlphaPMSubtractAlpha = op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_SUBTRACT && alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT);
        const bool blendTextureAlphaPMAddSmoothAlpha = op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_ADDSMOOTH && alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT);
        const bool blendTextureAlphaPMModulate2XAlpha = op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_MODULATE2X && alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT);
        // Exact unmodified alpha operands only; all other PM/4X states fall back.
        const bool blendTextureAlphaPMModulate4XAlpha = op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_MODULATE4X && alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT);
        // Signed-add alpha preserves PM RGB weighting; modified or reversed
        // operands retain DX9Ex instead of approximating game output.
        const bool blendTextureAlphaPMAddSignedAlpha = op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_ADDSIGNED && alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT);
        // Preserve DX9Ex for modified/swapped/non-diffuse signed2x operands.
        const bool blendTextureAlphaPMAddSigned2XAlpha = op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_ADDSIGNED2X && alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT);
        // Admit only unmodified texture/vertex operands. Any other source,
        // modifier or alpha operation leaves the original D3D9 draw untouched.
        const bool blendTextureAlphaPMBlendTextureAlpha = op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_BLENDTEXTUREALPHA && alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT);
        // Exact PM RGB with CURRENT-weighted TEXTURE/TFACTOR alpha;
        // any modified ARG1, swapped source or unsupported op fails closed.
        const bool blendTextureAlphaPMBlendCurrentFactorAlpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_BLENDCURRENTALPHA &&
            alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_TFACTOR ||
             alphaArg2 == (D3DTA_TFACTOR | D3DTA_COMPLEMENT));
        // Stage0 CURRENT-weighted alpha with DIFFUSE/CURRENT as ARG2:
        // CURRENT resolves to the vertex diffuse color at stage 0. Reuse
        // the numerically identical BLENDDIFFUSEALPHA native PS, but never
        // admit altered operands or silently fall through to TFACTOR.
        const bool blendTextureAlphaPMBlendCurrentDiffuseAlpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_BLENDCURRENTALPHA &&
            alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT);
        // Only unmodified texture and vertex operands are admitted.
        const bool blendTextureAlphaPMBlendDiffuseAlpha = op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_BLENDDIFFUSEALPHA && alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT);
        // Admit only unmodified texture and DIFFUSE/CURRENT operands.
        // Unsupported alpha operands preserve the original D3D9 draw.
        const bool blendTextureAlphaPMBlendFactorAlpha = op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_BLENDFACTORALPHA && alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT);
        // Live game factor alpha, only TEXTURE arg1 and TFACTOR arg2.
        // Unsupported modifiers or swapped operations keep D3D9 fallback.
        const bool blendTextureAlphaPMAddFactorAlpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM && alphaOp == D3DTOP_ADD &&
            alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_TFACTOR ||
             alphaArg2 == (D3DTA_TFACTOR | D3DTA_COMPLEMENT));
        const bool blendTextureAlphaPMAddSmoothFactorAlpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM && alphaOp == D3DTOP_ADDSMOOTH &&
            alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_TFACTOR ||
             alphaArg2 == (D3DTA_TFACTOR | D3DTA_COMPLEMENT));
        // Real game PM RGB with independent ADDSIGNED/ADDSIGNED2X alpha:
        // only TEXTURE and unmodified/complemented TFACTOR may participate.
        const bool blendTextureAlphaPMSignedFactorAlpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            (alphaOp == D3DTOP_ADDSIGNED || alphaOp == D3DTOP_ADDSIGNED2X) &&
            alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_TFACTOR ||
             alphaArg2 == (D3DTA_TFACTOR | D3DTA_COMPLEMENT));
        // Capture the factor only after the SELECTARG predicates exist;
        // unsupported D3D9 states keep the original DX9Ex draw/input.
        DWORD textureFactor = 0;
        if ((blendFactorAlpha || blendFactorTextureAlpha || blendFactorModulateAlpha ||
             selectTextureTfactorAlpha || selectDiffuseTfactorAlpha ||
             selectTextureTfactorArg2Alpha || selectDiffuseTfactorArg2Alpha ||
             blendTextureAlphaPMFactorAlpha || blendTextureAlphaPMBlendFactorAlpha || blendFactorDiffuseAlpha || blendFactorAddAlpha ||
             blendFactorSubtractAlpha || blendFactorAddSmoothAlpha ||
             blendFactorModulate2XAlpha || blendFactorModulate4XAlpha ||
              selectTextureFactorAlpha || selectDiffuseFactorAlpha ||
              blendTextureAlphaPMFactorArg2Alpha) &&
            FAILED(game->GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)))
            return false;
        // TFACTOR alpha MODULATE is a separate, disjoint game-state read.
        // Preserve legacy SELECTARG read and fallback predicates verbatim.
        if (blendTextureAlphaPMModulateFactorAlpha &&
            FAILED(game->GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)))
            return false;
        // 00637: an unreadable live TFACTOR must not produce a fabricated
        // native modulation or change the original game Draw/input.
        if (blendTextureAlphaPMModulateInverseFactorAlpha &&
            FAILED(game->GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)))
            return false;
        // The scaled factors are game state, not the default capture value.
        // No native Draw/DrawIndexed occurs if this read fails.
        if ((blendTextureAlphaPMScaledFactorAlpha ||
             blendTextureAlphaPMScaledInverseFactorAlpha) &&
            FAILED(game->GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)))
            return false;
        if ((blendTextureAlphaPMAddFactorAlpha ||
             blendTextureAlphaPMAddSmoothFactorAlpha) &&
            FAILED(game->GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)))
            return false;
        if (blendTextureAlphaPMSignedFactorAlpha &&
            FAILED(game->GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)))
            return false;
        if (blendTextureAlphaPMBlendCurrentFactorAlpha &&
            FAILED(game->GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)))
            return false;
        // These disjoint complemented-factor selectors must fetch the actual
        // game constant; failure leaves the draw on the D3D9 fallback path.
        if ((blendTextureAlphaPMInverseFactorArg1Alpha ||
             blendTextureAlphaPMInverseFactorArg2Alpha) &&
            FAILED(game->GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)))
            return false;
        // RGB and alpha must both use ADD(TEXTURE, DIFFUSE).
        const bool additive = op == D3DTOP_ADD && alphaOp == D3DTOP_ADD;
        // Mixed RGB/alpha operations remain DX9Ex; operand order stays exact.
        const bool subtract = op == D3DTOP_SUBTRACT && alphaOp == D3DTOP_SUBTRACT;
        const bool subtractTextureAlpha = op == D3DTOP_SUBTRACT && alphaOp == D3DTOP_SELECTARG1;
        const bool subtractDiffuseAlpha = op == D3DTOP_SUBTRACT && alphaOp == D3DTOP_SELECTARG2;
        const bool subtractModulateAlpha = op == D3DTOP_SUBTRACT && alphaOp == D3DTOP_MODULATE;
        const bool addSmooth = op == D3DTOP_ADDSMOOTH && alphaOp == D3DTOP_ADDSMOOTH;
        const bool addSmoothTextureAlpha = op == D3DTOP_ADDSMOOTH && alphaOp == D3DTOP_SELECTARG1;
        const bool addSmoothDiffuseAlpha = op == D3DTOP_ADDSMOOTH && alphaOp == D3DTOP_SELECTARG2;
        const bool modulate2x = op == D3DTOP_MODULATE2X && alphaOp == D3DTOP_MODULATE2X;
        const bool modulate4x = op == D3DTOP_MODULATE4X && alphaOp == D3DTOP_MODULATE4X;
        const bool modulate2xTextureAlpha = op == D3DTOP_MODULATE2X && alphaOp == D3DTOP_SELECTARG1;
        const bool modulate2xDiffuseAlpha = op == D3DTOP_MODULATE2X && alphaOp == D3DTOP_SELECTARG2;
        const bool modulate4xTextureAlpha = op == D3DTOP_MODULATE4X && alphaOp == D3DTOP_SELECTARG1;
        const bool modulate4xDiffuseAlpha = op == D3DTOP_MODULATE4X && alphaOp == D3DTOP_SELECTARG2;
        const bool mixedTextureAlpha = op == D3DTOP_MODULATE && alphaOp == D3DTOP_SELECTARG1;
        const bool mixedDiffuseAlpha = op == D3DTOP_MODULATE && alphaOp == D3DTOP_SELECTARG2;
        const bool mixedAddTextureAlpha = op == D3DTOP_ADD && alphaOp == D3DTOP_SELECTARG1;
        const bool mixedAddDiffuseAlpha = op == D3DTOP_ADD && alphaOp == D3DTOP_SELECTARG2;
        // Stage0 blend factors are texture alpha or interpolated vertex diffuse
        // alpha. These must be matched in both color and alpha operations.
        const bool blendTextureAlpha = op == D3DTOP_BLENDTEXTUREALPHA && alphaOp == D3DTOP_BLENDTEXTUREALPHA;
        // No mixed PM RGB/alpha admission without separate native shader parity.
        const bool blendTextureAlphaPM = game_stage0_premultiplied_pair(op, alphaOp);
        const bool blendTextureAlphaPMTextureAlpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM && alphaOp == D3DTOP_SELECTARG1 &&
            alphaArg1 == D3DTA_TEXTURE;
        const bool blendTextureAlphaPMDiffuseAlpha =
            game_stage0_premultiplied_diffuse_alpha_pair(op, alphaOp);
        const bool blendDiffuseAlpha = op == D3DTOP_BLENDDIFFUSEALPHA && alphaOp == D3DTOP_BLENDDIFFUSEALPHA;
        const bool blendTextureSelectedTextureAlpha = op == D3DTOP_BLENDTEXTUREALPHA && alphaOp == D3DTOP_SELECTARG1;
        const bool blendTextureSelectedDiffuseAlpha = op == D3DTOP_BLENDTEXTUREALPHA && alphaOp == D3DTOP_SELECTARG2;
        const bool blendDiffuseSelectedTextureAlpha = op == D3DTOP_BLENDDIFFUSEALPHA && alphaOp == D3DTOP_SELECTARG1;
        const bool blendDiffuseSelectedDiffuseAlpha = op == D3DTOP_BLENDDIFFUSEALPHA && alphaOp == D3DTOP_SELECTARG2;
        // On D3D9 fixed-function stage 0, CURRENT resolves to vertex DIFFUSE.
        // Reject operand modifiers; later stages are disabled by the gate.
        const bool arg2Diffuse = arg2 == D3DTA_DIFFUSE || arg2 == D3DTA_CURRENT;
        const bool alphaArg2Diffuse = alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT ||
            blendTextureAlphaPMInverseFactorArg2Alpha; // exact SELECTARG2 factor exception
        // SELECTARG1 reads ALPHAARG1 only. D3D9 ALPHAARG2 is inactive and
        // must not spuriously reject a valid PM RGB + texture-alpha Draw.
        const bool alphaArg2UnusedOnSelectArg1 = alphaOp == D3DTOP_SELECTARG1;
        // PM RGB still consumes the vertex DIFFUSE/CURRENT color input.
        // The new alpha operation's ARG2 is TFACTOR instead, so enforce RGB
        // source polarity separately without accepting other RGB modifiers.
        if (blendTextureAlphaPMModulateFactorAlpha && !arg2Diffuse) return false;
        if (blendTextureAlphaPMModulateInverseFactorAlpha && !arg2Diffuse) return false;
        if ((blendTextureAlphaPMScaledFactorAlpha ||
             blendTextureAlphaPMScaledInverseFactorAlpha) && !arg2Diffuse) return false;
        if ((blendTextureAlphaPMAddFactorAlpha ||
             blendTextureAlphaPMAddSmoothFactorAlpha) && !arg2Diffuse) return false;
        if (blendTextureAlphaPMSignedFactorAlpha && !arg2Diffuse) return false;
        if (blendTextureAlphaPMBlendCurrentFactorAlpha && !arg2Diffuse) return false;
        if (blendTextureAlphaPMBlendCurrentDiffuseAlpha && !arg2Diffuse) return false;
        // A missing DIFFUSE slot may supply a material color under MODULATE.
        // Only texture selection is provably independent of that color.
        if (!layout.hasDiffuse && !selectTexture) return false;
        // Validate the chosen alpha input independently from RGB. Inactive
        // alpha stage operands are ignored; active modifier bits remain denied.
        const bool rgbNeedsDiffuse = selectDiffuseTextureAlpha || selectDiffuseDiffuseAlpha || selectDiffuseTfactorAlpha || selectDiffuseTfactorArg2Alpha || selectDiffuseBlendTextureAlpha ||
                                     selectDiffuseBlendDiffuseAlpha ||
                                     selectDiffuseFactorAlpha ||
                                     selectDiffuseModulateAlpha || selectDiffuseAddAlpha || selectDiffuseSubtractAlpha || selectDiffuseAddSmoothAlpha || selectDiffuseModulate2XAlpha || selectDiffuseModulate4XAlpha ||
                                     blendFactorTextureAlpha || blendFactorModulateAlpha ||
                                     blendFactorDiffuseAlpha || blendFactorAddAlpha ||
                                     blendFactorSubtractAlpha || blendFactorAddSmoothAlpha ||
                                     blendFactorModulate2XAlpha || blendFactorModulate4XAlpha ||
                                     blendTextureModulateAlpha || blendDiffuseModulateAlpha ||
                                     blendTextureModulate2XAlpha || blendTextureModulate4XAlpha || blendDiffuseModulate2XAlpha || blendDiffuseModulate4XAlpha || blendTextureAddAlpha || blendDiffuseAddAlpha ||
                                     blendTextureSubtractAlpha || blendDiffuseSubtractAlpha ||
                                     blendTextureAddSmoothAlpha || blendDiffuseAddSmoothAlpha ||
                                     blendTextureSelectedTextureAlpha || blendTextureSelectedDiffuseAlpha ||
                                     blendDiffuseSelectedTextureAlpha || blendDiffuseSelectedDiffuseAlpha ||
                                     addSmoothTextureAlpha || addSmoothDiffuseAlpha ||
                                     modulate || additive || subtract || addSmooth || modulate2x || modulate4x ||
                                     modulate2xTextureAlpha || modulate2xDiffuseAlpha || modulate4xTextureAlpha || modulate4xDiffuseAlpha ||
                                     mixedTextureAlpha || mixedDiffuseAlpha ||
                                     mixedAddTextureAlpha || mixedAddDiffuseAlpha ||
                                     subtractTextureAlpha || subtractDiffuseAlpha || subtractModulateAlpha ||
                                     blendTextureAlphaPMFactorAlpha || blendTextureAlphaPMInverseFactorArg1Alpha || blendTextureAlphaPMInverseFactorArg2Alpha || blendTextureAlphaPMDiffuseArg1Alpha || blendTextureAlphaPMDiffuseAlpha || blendTextureAlphaPMModulateAlpha || blendTextureAlphaPMAddAlpha || blendTextureAlphaPMSubtractAlpha || blendTextureAlphaPMModulate2XAlpha || blendTextureAlphaPMModulate4XAlpha || blendTextureAlphaPMAddSignedAlpha || blendTextureAlphaPMAddSigned2XAlpha || blendTextureAlphaPMBlendTextureAlpha || blendTextureAlphaPMAddSmoothAlpha || blendTextureAlphaPMBlendDiffuseAlpha || blendTextureAlphaPMBlendCurrentDiffuseAlpha || blendTextureAlphaPMBlendCurrentFactorAlpha || blendTextureAlphaPMBlendFactorAlpha || blendTextureAlphaPMInverseTextureAlpha || blendTextureAlphaPMInverseDiffuseAlpha ||
                                     blendTextureAlpha || blendTextureAlphaPM || blendTextureAlphaPMTextureAlpha || blendDiffuseAlpha || blendFactorAlpha;
        const bool alphaNeedsDiffuse = selectDiffuseDiffuseAlpha || selectDiffuseModulateAlpha || selectTextureBlendTextureAlpha || selectDiffuseBlendTextureAlpha || selectTextureBlendDiffuseAlpha || selectDiffuseBlendDiffuseAlpha ||
                                           selectTextureFactorAlpha || selectDiffuseFactorAlpha ||
                                          selectDiffuseAddAlpha || selectDiffuseSubtractAlpha || selectDiffuseAddSmoothAlpha || selectDiffuseModulate2XAlpha || selectDiffuseModulate4XAlpha ||
                                         selectTextureDiffuseAlpha || selectTextureModulateAlpha ||
                                         selectTextureAddAlpha || selectTextureSubtractAlpha || selectTextureAddSmoothAlpha ||
                                          selectTextureModulate2XAlpha || selectTextureModulate4XAlpha ||
                                         blendFactorModulateAlpha ||
                                        blendFactorDiffuseAlpha || blendFactorAddAlpha ||
                                        blendFactorSubtractAlpha || blendFactorAddSmoothAlpha ||
                                        blendFactorModulate2XAlpha || blendFactorModulate4XAlpha ||
                                        blendTextureModulateAlpha || blendDiffuseModulateAlpha ||
                                     blendTextureModulate2XAlpha || blendTextureModulate4XAlpha || blendDiffuseModulate2XAlpha || blendDiffuseModulate4XAlpha || blendTextureAddAlpha || blendDiffuseAddAlpha ||
                                     blendTextureSubtractAlpha || blendDiffuseSubtractAlpha ||
                                     blendTextureAddSmoothAlpha || blendDiffuseAddSmoothAlpha ||
                                        blendTextureSelectedDiffuseAlpha || blendDiffuseSelectedDiffuseAlpha ||
                                        addSmoothDiffuseAlpha || subtractDiffuseAlpha || subtractModulateAlpha ||
                                       modulate || additive || subtract || addSmooth || modulate2x || modulate4x ||
                                       modulate2xDiffuseAlpha || modulate4xDiffuseAlpha ||
                                       mixedDiffuseAlpha || mixedAddDiffuseAlpha ||
                                       blendTextureAlphaPMDiffuseArg1Alpha || blendTextureAlphaPMDiffuseAlpha || blendTextureAlphaPMModulateAlpha || blendTextureAlphaPMAddAlpha || blendTextureAlphaPMSubtractAlpha || blendTextureAlphaPMModulate2XAlpha || blendTextureAlphaPMModulate4XAlpha || blendTextureAlphaPMAddSignedAlpha || blendTextureAlphaPMAddSigned2XAlpha || blendTextureAlphaPMBlendTextureAlpha || blendTextureAlphaPMAddSmoothAlpha || blendTextureAlphaPMBlendDiffuseAlpha || blendTextureAlphaPMBlendCurrentDiffuseAlpha || blendTextureAlphaPMBlendFactorAlpha || blendTextureAlphaPMInverseTextureAlpha || blendTextureAlphaPMInverseDiffuseAlpha ||
                                     blendTextureAlpha || blendTextureAlphaPM || blendTextureAlphaPMTextureAlpha || blendDiffuseAlpha || blendFactorAlpha;
        if ((!modulate && !selectTexture && !selectDiffuseTextureAlpha && !selectDiffuseDiffuseAlpha &&
               !selectTextureTfactorAlpha && !selectDiffuseTfactorAlpha &&
               !selectTextureTfactorArg2Alpha && !selectDiffuseTfactorArg2Alpha &&
              !selectDiffuseBlendTextureAlpha && !selectTextureBlendTextureAlpha && !selectTextureBlendDiffuseAlpha && !selectDiffuseBlendDiffuseAlpha && !selectDiffuseModulateAlpha && !selectDiffuseAddAlpha && !selectDiffuseSubtractAlpha &&
               !selectDiffuseModulate2XAlpha && !selectDiffuseModulate4XAlpha && !selectDiffuseAddSmoothAlpha && !selectDiffuseFactorAlpha && !selectTextureFactorAlpha && !selectTextureDiffuseAlpha && !selectTextureModulateAlpha &&
              !selectTextureAddAlpha && !selectTextureSubtractAlpha && !selectTextureAddSmoothAlpha &&
               !selectTextureModulate2XAlpha && !selectTextureModulate4XAlpha &&
              !additive && !subtract && !modulate2x && !modulate4x &&
             !modulate2xTextureAlpha && !modulate2xDiffuseAlpha && !modulate4xTextureAlpha && !modulate4xDiffuseAlpha &&
             !mixedTextureAlpha && !mixedDiffuseAlpha &&
             !mixedAddTextureAlpha && !mixedAddDiffuseAlpha && !addSmooth &&
             !addSmoothTextureAlpha && !addSmoothDiffuseAlpha &&
             !subtractTextureAlpha && !subtractDiffuseAlpha && !subtractModulateAlpha &&
             !blendFactorTextureAlpha && !blendFactorModulateAlpha &&
              !blendFactorDiffuseAlpha && !blendFactorAddAlpha &&
              !blendFactorSubtractAlpha && !blendFactorAddSmoothAlpha &&
              !blendFactorModulate2XAlpha && !blendFactorModulate4XAlpha &&
             !blendTextureSelectedTextureAlpha && !blendTextureSelectedDiffuseAlpha && !blendDiffuseSelectedTextureAlpha && !blendDiffuseSelectedDiffuseAlpha &&
             !blendTextureModulateAlpha && !blendDiffuseModulateAlpha &&
              !blendTextureModulate2XAlpha && !blendTextureModulate4XAlpha && !blendDiffuseModulate2XAlpha && !blendDiffuseModulate4XAlpha &&
              !blendTextureAddAlpha && !blendDiffuseAddAlpha &&
              !blendTextureSubtractAlpha && !blendDiffuseSubtractAlpha &&
               !blendTextureAddSmoothAlpha && !blendDiffuseAddSmoothAlpha &&
             !blendTextureAlphaPMInverseTextureAlpha && !blendTextureAlphaPMInverseDiffuseAlpha && !blendTextureAlphaPMFactorAlpha && !blendTextureAlphaPMInverseFactorArg1Alpha && !blendTextureAlphaPMInverseFactorArg2Alpha && !blendTextureAlphaPMDiffuseArg1Alpha && !blendTextureAlphaPMModulateAlpha && !blendTextureAlphaPMAddAlpha && !blendTextureAlphaPMSubtractAlpha && !blendTextureAlphaPMModulate2XAlpha && !blendTextureAlphaPMModulate4XAlpha && !blendTextureAlphaPMAddSignedAlpha && !blendTextureAlphaPMAddSigned2XAlpha && !blendTextureAlphaPMBlendTextureAlpha && !blendTextureAlphaPMAddSmoothAlpha && !blendTextureAlphaPMBlendDiffuseAlpha && !blendTextureAlphaPMBlendCurrentFactorAlpha && !blendTextureAlphaPMBlendCurrentDiffuseAlpha && !blendTextureAlphaPMBlendFactorAlpha &&
              !blendTextureAlphaPMAddFactorAlpha &&
              !blendTextureAlphaPMAddSmoothFactorAlpha &&
              !blendTextureAlphaPMSignedFactorAlpha &&
              !blendTextureAlphaPMScaledFactorAlpha &&
              !blendTextureAlphaPMScaledInverseFactorAlpha &&
              !blendTextureAlphaPMModulateInverseFactorAlpha &&
              !blendTextureAlphaPMModulateFactorAlpha &&
             !blendTextureAlphaPMDiffuseAlpha && !blendTextureAlpha && !blendTextureAlphaPM && !blendTextureAlphaPMTextureAlpha && !blendDiffuseAlpha && !blendFactorAlpha) || arg != D3DTA_TEXTURE ||
            (!selectTextureDiffuseAlpha && (!blendFactorDiffuseAlpha && !addSmoothDiffuseAlpha &&
              !subtractDiffuseAlpha &&
              !modulate2xDiffuseAlpha && !modulate4xDiffuseAlpha &&
              (!subtractDiffuseAlpha && !blendTextureSelectedDiffuseAlpha && !blendDiffuseSelectedDiffuseAlpha &&
               ((!selectDiffuseDiffuseAlpha && !mixedDiffuseAlpha && !mixedAddDiffuseAlpha && !blendTextureAlphaPMInverseFactorArg1Alpha && !blendTextureAlphaPMInverseFactorArg2Alpha && alphaArg1 != D3DTA_TEXTURE && !blendTextureAlphaPMDiffuseAlpha && !blendTextureAlphaPMDiffuseArg1Alpha && !blendTextureAlphaPMInverseTextureAlpha && !blendTextureAlphaPMInverseDiffuseArg1Alpha) && !selectTextureTfactorAlpha && !selectDiffuseTfactorAlpha &&
               !selectTextureTfactorArg2Alpha && !selectDiffuseTfactorArg2Alpha && !blendTextureAlphaPMFactorAlpha)))) ||
            (rgbNeedsDiffuse && !arg2Diffuse) ||
            ((((alphaNeedsDiffuse && !alphaArg2Diffuse) && !alphaArg2UnusedOnSelectArg1) && !selectTextureTfactorArg2Alpha && !selectDiffuseTfactorArg2Alpha &&
              !blendTextureAlphaPMFactorArg2Alpha &&
              !blendTextureAlphaPMInverseTextureArg2Alpha) && !blendTextureAlphaPMInverseDiffuseArg2Alpha) ||
            coordIndex >= layout.texcoordCount ||
            (transformFlags != D3DTTFF_DISABLE && transformFlags != D3DTTFF_COUNT2) || srgb > 1u ||
            ((addressU != D3DTADDRESS_WRAP && addressU != D3DTADDRESS_CLAMP &&
             addressU != D3DTADDRESS_MIRROR && addressU != D3DTADDRESS_MIRRORONCE) &&
             addressU != D3DTADDRESS_BORDER) ||
            ((addressV != D3DTADDRESS_WRAP && addressV != D3DTADDRESS_CLAMP &&
             addressV != D3DTADDRESS_MIRROR && addressV != D3DTADDRESS_MIRRORONCE) &&
             addressV != D3DTADDRESS_BORDER) ||
            ((mag != D3DTEXF_POINT && mag != D3DTEXF_LINEAR) && !anisotropic) ||
            ((min != D3DTEXF_POINT && min != D3DTEXF_LINEAR) && !anisotropic) ||
            ((mip != D3DTEXF_NONE && mip != D3DTEXF_POINT) && mip != D3DTEXF_LINEAR) ||
            (mip == D3DTEXF_NONE && (maxMip != 0u || decodedMipBias != 0.0f)) || !validMipBias)
            return false;
        // Preserve game sRGB reads only when the diagnostic UNORM target does
        // not require sRGB writes. Incompatible output remains D3D9-owned.
        capture.srgbTexture = srgb == TRUE;
        capture.mipFilter = static_cast<D3DTEXTUREFILTERTYPE>(mip);
        capture.maxMipLevel = maxMip;
        capture.mipLodBias = decodedMipBias;
        capture.addressU = static_cast<D3DTEXTUREADDRESS>(addressU);
        capture.addressV = static_cast<D3DTEXTUREADDRESS>(addressV);
        capture.borderColor = borderColor;
        capture.minFilter = static_cast<D3DTEXTUREFILTERTYPE>(min);
        capture.maxAnisotropy = anisotropic ? maxAniso : 1u;
        capture.magFilter = static_cast<D3DTEXTUREFILTERTYPE>(mag);
        capture.selectTexture = selectTexture;
        capture.selectTextureDiffuseAlpha = selectTextureDiffuseAlpha;
        capture.selectTextureModulateAlpha = selectTextureModulateAlpha;
        capture.selectTextureModulate2XAlpha = selectTextureModulate2XAlpha;
        capture.selectTextureModulate4XAlpha = selectTextureModulate4XAlpha;
        capture.selectTextureAddAlpha = selectTextureAddAlpha;
        capture.selectTextureSubtractAlpha = selectTextureSubtractAlpha;
        capture.selectTextureAddSmoothAlpha = selectTextureAddSmoothAlpha;
        capture.selectTextureFactorAlpha = selectTextureFactorAlpha;
        capture.selectTextureTfactorAlpha = selectTextureTfactorAlpha;
        capture.selectTextureTfactorArg2Alpha = selectTextureTfactorArg2Alpha;
        capture.selectTextureBlendTextureAlpha = selectTextureBlendTextureAlpha;
        capture.selectDiffuseTextureAlpha = selectDiffuseTextureAlpha;
        capture.selectDiffuseDiffuseAlpha = selectDiffuseDiffuseAlpha;
        capture.selectDiffuseModulateAlpha = selectDiffuseModulateAlpha;
        capture.selectDiffuseAddAlpha = selectDiffuseAddAlpha;
        capture.selectDiffuseSubtractAlpha = selectDiffuseSubtractAlpha;
        capture.selectDiffuseModulate2XAlpha = selectDiffuseModulate2XAlpha;
        capture.selectDiffuseModulate4XAlpha = selectDiffuseModulate4XAlpha;
        capture.selectDiffuseAddSmoothAlpha = selectDiffuseAddSmoothAlpha;
        capture.selectDiffuseFactorAlpha = selectDiffuseFactorAlpha;
        capture.selectDiffuseTfactorAlpha = selectDiffuseTfactorAlpha;
        capture.selectDiffuseTfactorArg2Alpha = selectDiffuseTfactorArg2Alpha;
        capture.selectDiffuseBlendTextureAlpha = selectDiffuseBlendTextureAlpha;
        capture.selectTextureBlendDiffuseAlpha = selectTextureBlendDiffuseAlpha;
        capture.selectDiffuseBlendDiffuseAlpha = selectDiffuseBlendDiffuseAlpha;
        capture.additive = additive;
        capture.subtract = subtract;
        capture.subtractTextureAlpha = subtractTextureAlpha;
        capture.subtractDiffuseAlpha = subtractDiffuseAlpha;
        capture.subtractModulateAlpha = subtractModulateAlpha;
        capture.addSmooth = addSmooth;
        capture.addSmoothTextureAlpha = addSmoothTextureAlpha;
        capture.addSmoothDiffuseAlpha = addSmoothDiffuseAlpha;
        capture.modulate2x = modulate2x;
        capture.modulate4x = modulate4x;
        capture.modulate2xTextureAlpha = modulate2xTextureAlpha;
        capture.modulate2xDiffuseAlpha = modulate2xDiffuseAlpha;
        capture.modulate4xTextureAlpha = modulate4xTextureAlpha;
        capture.modulate4xDiffuseAlpha = modulate4xDiffuseAlpha;
        capture.mixedTextureAlpha = mixedTextureAlpha;
        capture.mixedDiffuseAlpha = mixedDiffuseAlpha;
        capture.mixedAddTextureAlpha = mixedAddTextureAlpha;
        capture.mixedAddDiffuseAlpha = mixedAddDiffuseAlpha;
        capture.blendTextureAlpha = blendTextureAlpha;
        capture.blendTextureAlphaPM = blendTextureAlphaPM;
        capture.blendTextureAlphaPMTextureAlpha = blendTextureAlphaPMTextureAlpha;
        capture.blendTextureAlphaPMInverseTextureAlpha = blendTextureAlphaPMInverseTextureAlpha;
        capture.blendTextureAlphaPMInverseDiffuseAlpha = blendTextureAlphaPMInverseDiffuseArg1Alpha;
        capture.blendTextureAlphaPMDiffuseAlpha = blendTextureAlphaPMDiffuseAlpha;
        // Reuse the compiled vertex-alpha PM pixel shader, but keep the
        // original SELECTARG2 predicate and factor-alpha precedence intact.
        if (blendTextureAlphaPMDiffuseArg1Alpha)
            capture.blendTextureAlphaPMDiffuseAlpha = true;
        capture.blendTextureAlphaPMFactorAlpha = blendTextureAlphaPMFactorAlpha;
        capture.blendTextureAlphaPMModulateFactorAlpha = blendTextureAlphaPMModulateFactorAlpha;
        capture.blendTextureAlphaPMAddFactorAlpha = blendTextureAlphaPMAddFactorAlpha;
        capture.blendTextureAlphaPMAddSmoothFactorAlpha = blendTextureAlphaPMAddSmoothFactorAlpha;
        capture.blendTextureAlphaPMSignedFactorAlpha = blendTextureAlphaPMSignedFactorAlpha;
        capture.blendTextureAlphaPMSigned2XFactorAlpha =
            blendTextureAlphaPMSignedFactorAlpha && alphaOp == D3DTOP_ADDSIGNED2X;
        if (blendTextureAlphaPMModulateInverseFactorAlpha)
            capture.blendTextureAlphaPMModulateFactorAlpha = true;
        // Share the native PM RGB shader with a scaled saturating alpha
        // constant, keeping the original DX9Ex game Draw and input unmodified.
        if (blendTextureAlphaPMScaledFactorAlpha ||
            blendTextureAlphaPMScaledInverseFactorAlpha)
            capture.blendTextureAlphaPMModulateFactorAlpha = true;
        // SELECTARG1 complemented factor shares the compiled native PM/factor
        // shader, with alpha inversion applied to its constant below.
        if (blendTextureAlphaPMInverseFactorArg1Alpha)
            capture.blendTextureAlphaPMFactorAlpha = true;
        // The SELECTARG2 diffuse selector is structurally shared; override
        // it only for verified factor-alpha, before native shader selection.
        // Unknown/modified ALPHAARG2 still fails the original guard.
        if (blendTextureAlphaPMFactorArg2Alpha) {
            capture.blendTextureAlphaPMDiffuseAlpha = false;
            capture.blendTextureAlphaPMFactorAlpha = true;
        }
        // SELECTARG2 complemented factor is not vertex alpha. Override the
        // generic PM diffuse shader before the native Draw/DrawIndexed bind.
        if (blendTextureAlphaPMInverseFactorArg2Alpha) {
            capture.blendTextureAlphaPMDiffuseAlpha = false;
            capture.blendTextureAlphaPMFactorAlpha = true;
        }
        // SELECTARG2 with exact complemented TEXTURE alpha is not diffuse
        // alpha; override the default PM SELECTARG2 selector before PS bind.
        // Unsupported alpha modifiers still fail closed to the D3D9 Draw.
        if (blendTextureAlphaPMInverseTextureArg2Alpha) {
            capture.blendTextureAlphaPMDiffuseAlpha = false;
            capture.blendTextureAlphaPMInverseTextureAlpha = true;
        }
        // The generic SELECTARG2 PM diffuse branch is superseded here only
        // for the exactly selected complemented vertex-alpha source.
        if (blendTextureAlphaPMInverseDiffuseArg2Alpha) {
            capture.blendTextureAlphaPMDiffuseAlpha = false;
            capture.blendTextureAlphaPMInverseDiffuseAlpha = true;
        }
        capture.blendTextureAlphaPMModulateAlpha = blendTextureAlphaPMModulateAlpha;
        capture.blendTextureAlphaPMAddAlpha = blendTextureAlphaPMAddAlpha;
        capture.blendTextureAlphaPMSubtractAlpha = blendTextureAlphaPMSubtractAlpha;
        capture.blendTextureAlphaPMModulate2XAlpha = blendTextureAlphaPMModulate2XAlpha;
        capture.blendTextureAlphaPMModulate4XAlpha = blendTextureAlphaPMModulate4XAlpha;
        capture.blendTextureAlphaPMAddSignedAlpha = blendTextureAlphaPMAddSignedAlpha;
        capture.blendTextureAlphaPMAddSigned2XAlpha = blendTextureAlphaPMAddSigned2XAlpha;
        capture.blendTextureAlphaPMBlendTextureAlpha = blendTextureAlphaPMBlendTextureAlpha;
        // Preserve the 00628 base selector and its source regression graph.
        capture.blendTextureAlphaPMBlendDiffuseAlpha = blendTextureAlphaPMBlendDiffuseAlpha;
        // 00642: stage0 CURRENT weights are the same vertex diffuse alpha.
        // Alias only this new, exact predicate to the existing native shader.
        if (blendTextureAlphaPMBlendCurrentDiffuseAlpha)
            capture.blendTextureAlphaPMBlendDiffuseAlpha = true;
        capture.blendTextureAlphaPMBlendCurrentFactorAlpha = blendTextureAlphaPMBlendCurrentFactorAlpha;
        capture.blendTextureAlphaPMBlendFactorAlpha = blendTextureAlphaPMBlendFactorAlpha;
        capture.blendTextureAlphaPMAddSmoothAlpha = blendTextureAlphaPMAddSmoothAlpha;
        capture.blendDiffuseAlpha = blendDiffuseAlpha;
        capture.blendTextureSelectedTextureAlpha = blendTextureSelectedTextureAlpha;
        capture.blendTextureSelectedDiffuseAlpha = blendTextureSelectedDiffuseAlpha;
        capture.blendDiffuseSelectedTextureAlpha = blendDiffuseSelectedTextureAlpha;
        capture.blendDiffuseSelectedDiffuseAlpha = blendDiffuseSelectedDiffuseAlpha;
        capture.blendTextureModulateAlpha = blendTextureModulateAlpha;
        capture.blendDiffuseModulateAlpha = blendDiffuseModulateAlpha;
        capture.blendTextureModulate2XAlpha = blendTextureModulate2XAlpha;
        capture.blendTextureModulate4XAlpha = blendTextureModulate4XAlpha;
        capture.blendDiffuseModulate2XAlpha = blendDiffuseModulate2XAlpha;
        capture.blendDiffuseModulate4XAlpha = blendDiffuseModulate4XAlpha;
        capture.blendTextureAddAlpha = blendTextureAddAlpha;
        capture.blendDiffuseAddAlpha = blendDiffuseAddAlpha;
        capture.blendTextureSubtractAlpha = blendTextureSubtractAlpha;
        capture.blendDiffuseSubtractAlpha = blendDiffuseSubtractAlpha;
        capture.blendTextureAddSmoothAlpha = blendTextureAddSmoothAlpha;
        capture.blendDiffuseAddSmoothAlpha = blendDiffuseAddSmoothAlpha;
        capture.blendFactorAlpha = blendFactorAlpha;
        capture.blendFactorTextureAlpha = blendFactorTextureAlpha;
        capture.blendFactorModulateAlpha = blendFactorModulateAlpha;
        capture.blendFactorDiffuseAlpha = blendFactorDiffuseAlpha;
        capture.blendFactorAddAlpha = blendFactorAddAlpha;
        capture.blendFactorSubtractAlpha = blendFactorSubtractAlpha;
        capture.blendFactorAddSmoothAlpha = blendFactorAddSmoothAlpha;
        capture.blendFactorModulate2XAlpha = blendFactorModulate2XAlpha;
        capture.blendFactorModulate4XAlpha = blendFactorModulate4XAlpha;
        capture.blendFactorAlphaValue = static_cast<float>((textureFactor >> 24u) & 0xffu) / 255.0f;
        if (blendTextureAlphaPMInverseFactorArg1Alpha || blendTextureAlphaPMInverseFactorArg2Alpha)
            capture.blendFactorAlphaValue = 1.0f - capture.blendFactorAlphaValue;
        if (blendTextureAlphaPMModulateInverseFactorAlpha ||
            blendTextureAlphaPMScaledInverseFactorAlpha)
            capture.blendFactorAlphaValue = 1.0f - capture.blendFactorAlphaValue;
        // The exact accepted TFACTOR operands differ only by complement.
        // Keep signed-factor source-test anchors unambiguous.
        if ((blendTextureAlphaPMAddFactorAlpha ||
             blendTextureAlphaPMAddSmoothFactorAlpha) &&
            (alphaArg2 & D3DTA_COMPLEMENT) != 0u)
            capture.blendFactorAlphaValue = 1.0f - capture.blendFactorAlphaValue;
        if (blendTextureAlphaPMSignedFactorAlpha &&
            alphaArg2 == (D3DTA_TFACTOR | D3DTA_COMPLEMENT))
            capture.blendFactorAlphaValue = 1.0f - capture.blendFactorAlphaValue;
        if (blendTextureAlphaPMBlendCurrentFactorAlpha &&
            alphaArg2 == (D3DTA_TFACTOR | D3DTA_COMPLEMENT))
            capture.blendFactorAlphaValue = 1.0f - capture.blendFactorAlphaValue;
        // A D3D11 PS constant can exceed 1 here; the pixel shader must
        // saturate the final TEXTURE.a * scaled factor before alpha test.
        if (blendTextureAlphaPMScaledFactorAlpha ||
            blendTextureAlphaPMScaledInverseFactorAlpha)
            capture.blendFactorAlphaValue *=
                alphaOp == D3DTOP_MODULATE2X ? 2.0f : 4.0f;
        capture.coordIndex = coordIndex;
        capture.transformUv = transformUv;
        if (transformUv) capture.uvTransform = uvTransform;
    }
    // Real fixed-function stage 1 can combine the stage-0 CURRENT pixel
    // with D3DRS_TEXTUREFACTOR or live vertex DIFFUSE, including operand
    // modifiers, signed-add/cross-channel RGB transitions and diffuse/factor/current-alpha fades
    // for independent RGB/alpha operations. A missing required DIFFUSE remains DX9Ex-only. No stage-1 texture, TEMP,
    // unknown operand bits or stage-2 semantics are guessed; unsupported
    // stage-0 shaders never enter this path.
    if (nextColorOp != D3DTOP_DISABLE) {
        DWORD color1=~0u, color2=~0u, alphaOp=~0u, alpha1=~0u, alpha2=~0u;
        DWORD color0=~0u, alpha0=~0u;
        DWORD stage1Result=~0u, stage2Op=~0u, factor=0u;
        DWORD stageConstant=0u;
        const bool stage0WritesTemp = resultArg == D3DTA_TEMP;
        // Only a captured textured producer is allowed to supply TEMP.
        if (stage0WritesTemp && !capture.enabled) return false;
        // ARG0 is required only for the actual three-operand instructions.
        // A failed D3D9 state query must not turn into a guessed zero.
        if (stage1_three_source_operation(nextColorOp) &&
            FAILED(game->GetTextureStageState(1, D3DTSS_COLORARG0, &color0)))
            return false;
        // ALPHAOP can be independently three-source with two-source COLOROP.
        if (FAILED(game->GetTextureStageState(1, D3DTSS_ALPHAOP, &alphaOp)))
            return false;
        if (stage1_three_source_operation(alphaOp) &&
            FAILED(game->GetTextureStageState(1, D3DTSS_ALPHAARG0, &alpha0)))
            return false;
        if (FAILED(game->GetTextureStageState(1, D3DTSS_COLORARG1, &color1)) ||
            FAILED(game->GetTextureStageState(1, D3DTSS_COLORARG2, &color2)) ||
            FAILED(game->GetTextureStageState(1, D3DTSS_ALPHAARG1, &alpha1)) ||
            FAILED(game->GetTextureStageState(1, D3DTSS_ALPHAARG2, &alpha2)) ||
            FAILED(game->GetTextureStageState(1, D3DTSS_RESULTARG, &stage1Result)) ||
            FAILED(game->GetTextureStageState(2, D3DTSS_COLOROP, &stage2Op)) ||
            FAILED(game->GetRenderState(D3DRS_TEXTUREFACTOR, &factor)) ||
            stage1Result != D3DTA_CURRENT || stage2Op != D3DTOP_DISABLE ||
            (stage1_three_source_operation(nextColorOp)
                 ? (!stage1_three_source_supported(nextColorOp, color0, color1, color2) &&
                    !stage1_three_source_supported_with_temp(nextColorOp, color0, color1, color2, stage0WritesTemp) &&
                     !stage1_matched_texture_three_source_supported(nextColorOp,color0,color1,color2,true,stage0WritesTemp))
                 : (!stage1_combiner_supported(nextColorOp, color1, color2) &&
                    !stage1_combiner_supported_with_temp(nextColorOp, color1, color2, stage0WritesTemp) &&
                     !stage1_matched_texture_alpha_blend_supported(
                         nextColorOp, color1, color2, true, stage0WritesTemp) &&
                      !stage1_matched_texture_two_source_supported(nextColorOp,color1,color2,true,stage0WritesTemp,false))) ||
            (stage1_three_source_operation(alphaOp)
                 ? (!stage1_three_source_supported(alphaOp, alpha0, alpha1, alpha2) &&
                    !stage1_three_source_supported_with_temp(alphaOp, alpha0, alpha1, alpha2, stage0WritesTemp) &&
                     !stage1_matched_texture_three_source_supported(alphaOp,alpha0,alpha1,alpha2,true,stage0WritesTemp))
                 : (!stage1_alpha_supported(alphaOp, alpha1, alpha2) &&
                    !stage1_alpha_supported_with_temp(alphaOp, alpha1, alpha2, stage0WritesTemp) &&
                     !stage1_matched_texture_alpha_blend_supported(
                         alphaOp, alpha1, alpha2, true, stage0WritesTemp) &&
                      !stage1_matched_texture_two_source_supported(alphaOp,alpha1,alpha2,true,stage0WritesTemp,true))) ||
            (!layout.hasDiffuse &&
             (stage1_operation_reads_diffuse(nextColorOp, color1, color2) ||
              stage1_operation_reads_diffuse(alphaOp, alpha1, alpha2) ||
              stage1_three_source_reads_diffuse(nextColorOp, color0, color1, color2) ||
              stage1_three_source_reads_diffuse(alphaOp, alpha0, alpha1, alpha2))) ||
            (!layout.hasSpecular &&
             (stage1_operation_reads_specular(nextColorOp, color1, color2) ||
              stage1_operation_reads_specular(alphaOp, alpha1, alpha2) ||
              stage1_three_source_reads_specular(nextColorOp, color0, color1, color2) ||
              stage1_three_source_reads_specular(alphaOp, alpha0, alpha1, alpha2))) ||
            (capture.enabled && !capture.stage0FullModulate &&
             !capture.selectTexture && !capture.additive))
            return false;
        // Stage1 TEXTURE is a separate D3D9 operand for arbitrary RGB/alpha
        // and three-input combiners; never substitute stage0 CURRENT for it.
        const bool stage1UsesTextureOperand =
            stage1_operation_reads_texture(nextColorOp,color1,color2) ||
            stage1_operation_reads_texture(alphaOp,alpha1,alpha2) ||
            stage1_three_source_reads_texture(nextColorOp,color0,color1,color2) ||
            stage1_three_source_reads_texture(alphaOp,alpha0,alpha1,alpha2);
        const bool stage1NeedsMatchedTexture = stage1UsesTextureOperand ||
            nextColorOp == D3DTOP_BLENDTEXTUREALPHA ||
            nextColorOp == D3DTOP_BLENDTEXTUREALPHAPM ||
            alphaOp == D3DTOP_BLENDTEXTUREALPHA ||
            alphaOp == D3DTOP_BLENDTEXTUREALPHAPM;
        // D3D9 Stage1 BLENDTEXTUREALPHA and PM read sampler/texture 1. It may
        // reuse the native stage-0 sample only when resource, UV and all
        // relevant sampler state agree; otherwise preserve original D3D9.
        if (stage1NeedsMatchedTexture) {
            if (!capture.enabled || !tex) return false;
            ComPtr<IDirect3DBaseTexture9> tex1;
            DWORD uv1 = ~0u, transform1 = ~0u;
            if (FAILED(game->GetTexture(1, tex1.GetAddressOf())) ||
                !tex1 || tex1->GetType() != D3DRTYPE_TEXTURE ||
                FAILED(game->GetTextureStageState(1, D3DTSS_TEXCOORDINDEX, &uv1)) ||
                FAILED(game->GetTextureStageState(1, D3DTSS_TEXTURETRANSFORMFLAGS, &transform1)) ||
                !stage1_game_uv_supported(uv1, layout.texcoordCount, transform1))
                return false;
            D3DMATRIX matrix1{};
            bool stage1AlternateUv =
                uv1 != capture.coordIndex ||
                (transform1 == D3DTTFF_COUNT2) != capture.transformUv;
            if (transform1 == D3DTTFF_COUNT2) {
                if (FAILED(game->GetTransform(D3DTS_TEXTURE1, &matrix1)))
                    return false;
                if (capture.transformUv &&
                    std::memcmp(&capture.uvTransform, &matrix1, sizeof(matrix1)) != 0)
                    stage1AlternateUv = true;
            }
            capture.stage1CoordIndex = uv1;
            capture.stage1TransformUv = transform1 == D3DTTFF_COUNT2;
            if (capture.stage1TransformUv) capture.stage1UvTransform = matrix1;
            constexpr std::array<D3DSAMPLERSTATETYPE, 11> states{{
                D3DSAMP_ADDRESSU, D3DSAMP_ADDRESSV, D3DSAMP_ADDRESSW,
                D3DSAMP_BORDERCOLOR, D3DSAMP_MAGFILTER, D3DSAMP_MINFILTER,
                D3DSAMP_MIPFILTER, D3DSAMP_MIPMAPLODBIAS,
                D3DSAMP_MAXMIPLEVEL, D3DSAMP_MAXANISOTROPY,
                D3DSAMP_SRGBTEXTURE
            }};
            bool samplerDiff = false;
            for (std::size_t i = 0; i < states.size(); ++i) {
                DWORD s0 = ~0u, s1 = ~0u;
                if (FAILED(game->GetSamplerState(0, states[i], &s0)) ||
                    FAILED(game->GetSamplerState(1, states[i], &s1)))
                    return false;
                // ADDRESSW is not modeled for a 2D texture. Keep it equal
                // rather than silently discarding a game-authored difference.
                if (states[i] == D3DSAMP_ADDRESSW && s0 != s1) return false;
                samplerDiff |= s0 != s1;
                capture.stage1SamplerStates[i] = s1;
            }
            const auto& s1 = capture.stage1SamplerStates;
            float stage1MipBias = 0.0f;
            static_assert(sizeof(stage1MipBias) == sizeof(DWORD));
            std::memcpy(&stage1MipBias, &s1[7], sizeof(stage1MipBias));
            // Preserve independent game-authored addressing, filter, mip and
            // sRGB. Unrepresentable profiles retain the original D3D9 draw.
            const bool stage1SamplerSupported = stage1_game_sampler_supported(
                s1[0],s1[1],s1[5],s1[4],s1[6],s1[8],stage1MipBias,s1[9],s1[10]);
            if (!stage1_dual_texture_compatible(
                    capture.enabled, tex1 != nullptr, tex1->GetType() == D3DRTYPE_TEXTURE,
                    stage1_game_uv_supported(uv1, layout.texcoordCount, transform1),
                    transform1 == D3DTTFF_DISABLE || transform1 == D3DTTFF_COUNT2,
                    stage1SamplerSupported))
                return false;
            capture.stage1IndependentSampler = samplerDiff;
            // Even the same D3D9 texture must bind t1/s1 when sampler 1
            // differs, otherwise the stage-0 texture sample changes pixels.
            // Different game UV slots or COUNT2 matrices need a separate
            // t1/s1 sample even when texture object and sampler match Stage0.
            if ((tex1.Get() != tex.Get() || samplerDiff || stage1AlternateUv) &&
                FAILED(tex1.As(&capture.stage1SeparateTexture)))
                return false;
        }
        // Only read stage-local CONSTANT when active COLOR/ALPHA/ARG0 needs it.
        // A failed query preserves D3D9 Draw/Present and gamepad unchanged.
        const bool needsStageConstant =
            stage1_operation_reads_constant(nextColorOp,color1,color2) ||
            stage1_operation_reads_constant(alphaOp,alpha1,alpha2) ||
            stage1_three_source_reads_constant(nextColorOp,color0,color1,color2) ||
            stage1_three_source_reads_constant(alphaOp,alpha0,alpha1,alpha2);
        if (needsStageConstant &&
            FAILED(game->GetTextureStageState(1,D3DTSS_CONSTANT,&stageConstant)))
            return false;
        capture.stage1Enabled = true;
        capture.stage1TextureOperands = stage1UsesTextureOperand;
        capture.stage0ResultTemp = stage0WritesTemp;
        capture.stage1ColorOp = nextColorOp;
        capture.stage1AlphaOp = alphaOp;
        capture.stage1Args = {color1, color2, alpha1, alpha2};
        capture.stage1ArgZero = {color0, alpha0};
        constexpr float kByteScale = 1.0f / 255.0f;
        capture.stage1Factor = {
            static_cast<float>((factor >> 16) & 255u) * kByteScale,
            static_cast<float>((factor >> 8) & 255u) * kByteScale,
            static_cast<float>(factor & 255u) * kByteScale,
            static_cast<float>((factor >> 24) & 255u) * kByteScale
        };
        capture.stage1Constant = {
            static_cast<float>((stageConstant >> 16) & 255u) * kByteScale,
            static_cast<float>((stageConstant >> 8) & 255u) * kByteScale,
            static_cast<float>(stageConstant & 255u) * kByteScale,
            static_cast<float>((stageConstant >> 24) & 255u) * kByteScale
        };
    }
    // Custom clip planes are not implemented by the native shader. The
    // object-space path must also reject D3D9 lighting and vertex blending.
    DWORD clipPlanes = ~0u;
    if (FAILED(game->GetRenderState(D3DRS_CLIPPLANEENABLE, &clipPlanes)) ||
        clipPlanes != 0u)
        return false;
    if (!layout.pretransformed) {
        DWORD lighting = TRUE, vertexBlend = ~0u;
        if (FAILED(game->GetRenderState(D3DRS_LIGHTING, &lighting)) ||
            FAILED(game->GetRenderState(D3DRS_VERTEXBLEND, &vertexBlend)) ||
            lighting || vertexBlend != D3DVBF_DISABLE ||
            FAILED(game->GetTransform(D3DTS_WORLD, &transforms[0])) ||
            FAILED(game->GetTransform(D3DTS_VIEW, &transforms[1])) ||
            FAILED(game->GetTransform(D3DTS_PROJECTION, &transforms[2])))
            return false;
    }
    if (!game_native_backbuffer_ready(game, viewport)) return false;
    return true;
}

bool translate_vertices(const void* input, UINT count, UINT stride,
                        const D3DVIEWPORT9& vp, const GameFvfLayout& layout,
                        const std::array<D3DMATRIX, 3>& transforms,
                        const TextureCapture& capture,
                        std::vector<NativeVertex>& output) {
    if (!input || stride < layout.minStride || stride > 512u ||
        count == 0 || count > kMaxVertices ||
        (capture.enabled != layout.textured &&
         !(layout.textured && !capture.enabled &&
           capture.inactiveStage0TextureBypass)))
        return false;
    output.resize(count);
    const auto* src = static_cast<const std::uint8_t*>(input);
    for (UINT i = 0; i < count; ++i) {
        GameFvfSample decoded{};
        const auto* data = src + static_cast<std::size_t>(i) * stride;
        if (!game_fvf_decode_vertex(data, stride, layout, decoded))
            return false;
        const float* xyz = decoded.position;
        const DWORD diffuse = decoded.diffuse;
        const DWORD specular = decoded.specular;
        // TEXCOORDSIZE3/4 stores (u,v,extra...); native untransformed 2D UV consumes (u,v).
        // TEXCOORDSIZE1(0..7) U-only streams get V=0; later UV sets
        // retain packed game byte offsets through native Draw/DrawIndexed.
        // TEX2..8 select UV1..7 from game bytes; absent slots fail closed.
        // An inactive stage-0 texture still uses the full game FVF stride,
        // but does not consume any TEXn coordinates. The same vertex upload
        // storage is reused across Draw and DrawIndexed within a frame: zero
        // unused native UVs instead of inheriting stale values from a prior
        // textured game draw. Malformed or NaN unused UVs never become samples.
        if (!capture.enabled) {
            output[i].uv[0] = 0.0f;
            output[i].uv[1] = 0.0f;
        }
        if (capture.enabled &&
            !game_fvf_select_uv(decoded, layout, capture.coordIndex, output[i].uv))
            return false;
        if (capture.enabled && (!std::isfinite(output[i].uv[0]) ||
                                !std::isfinite(output[i].uv[1]))) return false;
        if (capture.enabled && capture.transformUv) {
            // D3D9 COUNT2: row-vector (u,v,1,0), transformed before
            // native perspective-correct texture coordinate interpolation.
            const float u = output[i].uv[0], v = output[i].uv[1];
            const auto& m = capture.uvTransform;
            const float texU = u * m._11 + v * m._21 + m._31;
            const float texV = u * m._12 + v * m._22 + m._32;
            if (!std::isfinite(texU) || !std::isfinite(texV)) return false;
            output[i].uv[0] = texU;
            output[i].uv[1] = texV;
        }
        // Native TEXCOORD1 is always initialized. Stage1 may read a distinct
        // FVF UV stream or an independently transformed D3DTS_TEXTURE1 matrix.
        // The per-vertex finite check prevents undefined native GPU samples;
        // original D3D9 Draw/input stays unmodified on failure.
        output[i].uvStage1[0] = output[i].uv[0];
        output[i].uvStage1[1] = output[i].uv[1];
        if (capture.stage1SeparateTexture) {
            if (!game_fvf_select_uv(decoded, layout, capture.stage1CoordIndex,
                                    output[i].uvStage1))
                return false;
            if (capture.stage1TransformUv) {
                const float u = output[i].uvStage1[0];
                const float v = output[i].uvStage1[1];
                const auto& m = capture.stage1UvTransform;
                output[i].uvStage1[0] = u * m._11 + v * m._21 + m._31;
                output[i].uvStage1[1] = u * m._12 + v * m._22 + m._32;
            }
            if (!std::isfinite(output[i].uvStage1[0]) ||
                !std::isfinite(output[i].uvStage1[1]))
                return false;
        }
        if (!std::isfinite(xyz[0]) || !std::isfinite(xyz[1]) ||
            !std::isfinite(xyz[2]) ||
            (layout.pretransformed && (!std::isfinite(xyz[3]) || xyz[3] <= 0.0f)))
            return false;
        NativeVertex& v = output[i];
        if (layout.pretransformed) {
            // D3D9 XYZRHW stores reciprocal homogeneous W. Preserve it for
            // perspective-correct UV interpolation instead of treating a menu
            // sprite with non-uniform RHW as an affine D3D11 triangle.
            const float w = 1.0f / xyz[3];
            if (!std::isfinite(w) || w <= 0.0f) return false;
            v.clip[0] = (2.0f * (xyz[0] - static_cast<float>(vp.X)) /
                        static_cast<float>(vp.Width) - 1.0f) * w;
            v.clip[1] = (1.0f - 2.0f * (xyz[1] - static_cast<float>(vp.Y)) /
                        static_cast<float>(vp.Height)) * w;
            // XYZRHW already contains post-viewport window depth: do not
            // reapply D3D9 MinZ/MaxZ during menu/HUD native Draw.
            if (!game_native_screen_depth_clip(
                    xyz[2], w, vp.MinZ, vp.MaxZ, v.clip[2])) return false;
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
            // World-space geometry may straddle the camera plane. D3D11
            // clips homogeneous triangles/lines before perspective division;
            // rejecting one negative-W vertex dropped the *entire* game Draw.
            // Preserve finite W==0 camera-plane vertices: homogeneous clipping
            // of a triangle/line occurs on D3D11 GPU, before perspective divide.
            // Invalid/fully zero homogeneous vertices retain D3D9 fallback.
            // The game-authored viewport Z range is not necessarily [0,1].
            // Mirror its depth map before D3D11 homogeneous clipping so
            // world/race Draw and DrawIndexed share D3D9 depth ordering.
            if (!game_native_world_depth_clip(clip, vp.MinZ, vp.MaxZ) ||
                !game_native_object_clip_position(clip))
                return false;
            std::copy(clip.begin(), clip.end(), v.clip);
        }
        // D3D9 uses integer pixel centers; D3D11 samples at pixel +0.5.
        // Convert BOTH menu XYZRHW and world WVP vertices without dividing
        // by homogeneous W. The same output reaches live Draw/DrawIndexed.
        // Failed correction keeps original game D3D9 Draw/Present/input.
        if (!game_native_d3d9_raster_center(
                v.clip, static_cast<float>(vp.Width),
                static_cast<float>(vp.Height))) return false;
        v.diffuse[0] = static_cast<float>((diffuse >> 16) & 255) / 255.0f;
        v.diffuse[1] = static_cast<float>((diffuse >> 8) & 255) / 255.0f;
        v.diffuse[2] = static_cast<float>(diffuse & 255) / 255.0f;
        v.diffuse[3] = static_cast<float>((diffuse >> 24) & 255) / 255.0f;
        v.specular[0] = static_cast<float>((specular >> 16) & 255) / 255.0f;
        v.specular[1] = static_cast<float>((specular >> 8) & 255) / 255.0f;
        v.specular[2] = static_cast<float>(specular & 255) / 255.0f;
        v.specular[3] = static_cast<float>((specular >> 24) & 255) / 255.0f;
    }
    return true;
}

// Snapshot a live game texture into a D3D11 sampleable resource. When the
// source asks for MIP_POINT or MIP_LINEAR, upload every readable mip rather than binding
// level 0 and silently changing the game's minification result. All error
// paths preserve the original D3D9 Draw/Present/gamepad behavior.
// Build sampler state independently from a mirrored D3D11 texture. Stage1 may
// use the same D3D9 pixels with different game-authored sampler state; doing
// so must not re-read or re-upload the live source texture.
bool create_game_sampler(ID3D11Device* dev, const TextureCapture& capture,
                         UINT levels, ComPtr<ID3D11SamplerState>& sampler) noexcept {
    if (!dev || levels == 0u) return false;
    if (capture.minFilter == D3DTEXF_ANISOTROPIC &&
        ((capture.magFilter != D3DTEXF_LINEAR &&
          capture.magFilter != D3DTEXF_ANISOTROPIC) ||
         capture.mipFilter != D3DTEXF_LINEAR ||
         capture.maxAnisotropy < 2u ||
         capture.maxAnisotropy > D3D11_REQ_MAXANISOTROPY)) return false;
    const bool usesMips = capture.mipFilter == D3DTEXF_POINT ||
                          capture.mipFilter == D3DTEXF_LINEAR;
    if (usesMips && capture.maxMipLevel >= levels) return false;
    D3D11_SAMPLER_DESC state{};
    // Independent D3D9 MIN/MAG filtering with point or linear mip selection. For
    // MIPFILTER=NONE force LOD 0 even if the source has additional mips.
    state.Filter = capture.minFilter == D3DTEXF_LINEAR ?
        (capture.magFilter == D3DTEXF_LINEAR ?
            D3D11_FILTER_MIN_MAG_LINEAR_MIP_POINT :
            D3D11_FILTER_MIN_LINEAR_MAG_MIP_POINT) :
        (capture.magFilter == D3DTEXF_LINEAR ?
            D3D11_FILTER_MIN_POINT_MAG_LINEAR_MIP_POINT :
            D3D11_FILTER_MIN_MAG_MIP_POINT);
    // Preserve trilinear and mixed MIN/MAG sampling for game textures:
    // DX9Ex uses two adjacent mip levels when MIPFILTER is LINEAR.
    if (capture.mipFilter == D3DTEXF_LINEAR) {
        state.Filter = capture.minFilter == D3DTEXF_LINEAR ?
            (capture.magFilter == D3DTEXF_LINEAR ?
                D3D11_FILTER_MIN_MAG_MIP_LINEAR :
                D3D11_FILTER_MIN_LINEAR_MAG_POINT_MIP_LINEAR) :
            (capture.magFilter == D3DTEXF_LINEAR ?
                D3D11_FILTER_MIN_POINT_MAG_MIP_LINEAR :
                D3D11_FILTER_MIN_MAG_POINT_MIP_LINEAR);
    }
    // Bind the full mip chain for both captured D3D9 MAG anisotropic profiles.
    if (capture.minFilter == D3DTEXF_ANISOTROPIC)
        state.Filter = D3D11_FILTER_ANISOTROPIC;
    // D3D9 game/menu UVs may reflect outside [0,1]. Preserve their
    // addressing semantics through the native pixel sampler; never silently
    // clamp an unknown D3D9 state, which would mislabel a diagnostic frame.
    const auto translateAddress = [](D3DTEXTUREADDRESS address) noexcept {
        switch (address) {
        case D3DTADDRESS_WRAP: return D3D11_TEXTURE_ADDRESS_WRAP;
        case D3DTADDRESS_CLAMP: return D3D11_TEXTURE_ADDRESS_CLAMP;
        case D3DTADDRESS_MIRROR: return D3D11_TEXTURE_ADDRESS_MIRROR;
        case D3DTADDRESS_MIRRORONCE: return D3D11_TEXTURE_ADDRESS_MIRROR_ONCE;
        case D3DTADDRESS_BORDER: return D3D11_TEXTURE_ADDRESS_BORDER;
        default: return static_cast<D3D11_TEXTURE_ADDRESS_MODE>(0);
        }
    };
    state.AddressU = translateAddress(capture.addressU);
    state.AddressV = translateAddress(capture.addressV);
    if (!state.AddressU || !state.AddressV) return false;
    state.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
    // D3D9 COLORREF-like D3DCOLOR is 0xAARRGGBB; native BorderColor is RGBA.
    state.BorderColor[0] = static_cast<float>((capture.borderColor >> 16) & 0xffu) / 255.0f;
    state.BorderColor[1] = static_cast<float>((capture.borderColor >> 8) & 0xffu) / 255.0f;
    state.BorderColor[2] = static_cast<float>(capture.borderColor & 0xffu) / 255.0f;
    state.BorderColor[3] = static_cast<float>((capture.borderColor >> 24) & 0xffu) / 255.0f;
    // Recheck captured source state before CreateSamplerState; no silent
    // D3D11 driver clamp or NaN/Inf propagation in the diagnostic image.
    if (!std::isfinite(capture.mipLodBias) ||
        capture.mipLodBias < kMinMipLodBias || capture.mipLodBias > kMaxMipLodBias ||
        (!usesMips && capture.mipLodBias != 0.0f)) return false;
    // D3D9 MAXMIPLEVEL discards finer (lower-indexed) mip levels.
    // D3D11 MinLOD clamps to that same source level; all levels are mirrored.
    state.MinLOD = usesMips ? static_cast<float>(capture.maxMipLevel) : 0.0f;
    state.MaxLOD = usesMips ? static_cast<float>(levels - 1u) : 0.0f;
    state.MipLODBias = usesMips ? capture.mipLodBias : 0.0f;
    state.MaxAnisotropy = capture.minFilter == D3DTEXF_ANISOTROPIC ?
        capture.maxAnisotropy : 1u;
    state.ComparisonFunc = D3D11_COMPARISON_NEVER;
    return SUCCEEDED(dev->CreateSamplerState(&state, sampler.GetAddressOf()));
}

bool mirror_texture(ID3D11Device* dev, const TextureCapture& capture,
                    ComPtr<ID3D11ShaderResourceView>& view,
                    ComPtr<ID3D11SamplerState>& sampler) noexcept {
    if (!dev || !capture.enabled || !capture.texture) return false;
    const UINT sourceLevels = capture.texture->GetLevelCount();
    // A 4K menu/vehicle atlas may use thirteen distinct mip levels;
    // actual source extents and converted-byte budget are checked below.
    if (sourceLevels == 0 || sourceLevels > kMaxNativeGameAtlasMipLevels) return false;
    D3DSURFACE_DESC base{};
    if (FAILED(capture.texture->GetLevelDesc(0, &base)) ||
        base.Width == 0 || base.Height == 0 ||
        base.Width > kMaxNativeGameAtlasDimension ||
        base.Height > kMaxNativeGameAtlasDimension) return false;
    // The game can render menu, car and race textures into more than one
    // color layout, including 16-bit game-authored render targets.
    // Snapshot the real D3D9 RT before converting to a native
    // BGRA8 SRV; never reinterpret RGBA or packed 10-bit pixels as BGRA.
    const native_rt_readback::Layout rtLayout =
        base.Format == D3DFMT_A8R8G8B8 ? native_rt_readback::Layout::argb8 :
        base.Format == D3DFMT_X8R8G8B8 ? native_rt_readback::Layout::xrgb8 :
        base.Format == D3DFMT_A8B8G8R8 ? native_rt_readback::Layout::a8b8g8r8 :
        base.Format == D3DFMT_X8B8G8R8 ? native_rt_readback::Layout::x8b8g8r8 :
        base.Format == D3DFMT_A2R10G10B10 ? native_rt_readback::Layout::a2r10g10b10 :
        base.Format == D3DFMT_A2B10G10R10 ? native_rt_readback::Layout::a2b10g10r10 :
        base.Format == D3DFMT_R5G6B5 ? native_rt_readback::Layout::rgb565 :
        base.Format == D3DFMT_A1R5G5B5 ? native_rt_readback::Layout::argb1555 :
        base.Format == D3DFMT_A4R4G4B4 ? native_rt_readback::Layout::argb4444 :
        base.Format == D3DFMT_X1R5G5B5 ? native_rt_readback::Layout::xrgb1555 :
        base.Format == D3DFMT_X4R4G4B4 ? native_rt_readback::Layout::xrgb4444 :
                                          native_rt_readback::Layout::unsupported;
    const bool gpuRenderTarget = base.Pool == D3DPOOL_DEFAULT &&
        (base.Usage & D3DUSAGE_RENDERTARGET) != 0u &&
        native_rt_readback::sampleable(rtLayout, capture.srgbTexture);
    // Large immutable atlases are byte-budgeted, but a live render target would
    // synchronously GetRenderTargetData in every game Draw: retain the prior
    // 1K GPU-source bound to protect menu/race input and frame pacing.
    if (gpuRenderTarget && (base.Width > 1024u || base.Height > 1024u))
        return false;
    // DEFAULT DYNAMIC textures are game-writable LockRect resources, unlike
    // ordinary DEFAULT textures. Re-snapshot their actual contents at every
    // observed game Draw/DrawIndexed; never reuse a stale frame or assume
    // the driver supports a read lock. Unsupported usage remains D3D9-owned.
    const auto sourceRoute = dynamic_texture::source_route(
        static_cast<unsigned>(base.Pool), static_cast<unsigned>(base.Usage),
        gpuRenderTarget);
    if (sourceRoute == dynamic_texture::SourceRoute::unsupported) return false;
    const bool usesMips = capture.mipFilter == D3DTEXF_POINT ||
                          capture.mipFilter == D3DTEXF_LINEAR;
    // AUTOGENMIPMAP exposes one level to LockRect even though the D3D9
    // sampler consumes generated levels. Never claim those mips were copied.
    if (usesMips && (base.Usage & D3DUSAGE_AUTOGENMIPMAP)) return false;
    if (usesMips && capture.texture->GetLOD() != 0u) return false;
    // Reject invalid game mip requests rather than silently clamping a native sampler.
    if (usesMips && capture.maxMipLevel >= sourceLevels) return false;
    const UINT levels = usesMips ? sourceLevels : 1u;
    // A game-created mipmapped render target needs one D3D9 GPU readback per
    // sampled mip. Each source level is independently validated and captured
    // before creating the immutable DX11 SRV; failure stays on DX9Ex.
    const bool compressed = base.Format == D3DFMT_DXT1 ||
                            base.Format == D3DFMT_DXT3 ||
                            base.Format == D3DFMT_DXT5;
    const bool packed16 = base.Format == D3DFMT_R5G6B5 ||
                          base.Format == D3DFMT_A1R5G5B5 ||
                          base.Format == D3DFMT_A4R4G4B4 ||
                          base.Format == D3DFMT_X1R5G5B5 ||
                          base.Format == D3DFMT_X4R4G4B4;
    // Live menu masks and lettering may use alpha/luminance-only D3D9 texels.
    const bool luminance = base.Format == D3DFMT_A8 ||
                           base.Format == D3DFMT_L8 ||
                           base.Format == D3DFMT_A8L8;
    // The game RGB24 B,G,R rows have no native 24-bit D3D11 SRV.
    const bool rgb24 = base.Format == D3DFMT_R8G8B8;
    // Little-endian RGBA memory cannot be memcpy-ed into a BGRA8 SRV.
    const bool rgbaSwizzle = base.Format == D3DFMT_A8B8G8R8 ||
                             base.Format == D3DFMT_X8B8G8R8;
    // Ten-bit game RGB/2-bit alpha has no BGRA8 byte-compatible memory layout.
    const bool tenBit = base.Format == D3DFMT_A2R10G10B10 ||
                        base.Format == D3DFMT_A2B10G10R10;
    // A4L4 and L16 are game-authored legacy luminance formats not sampleable as BGRA8.
    const bool extendedLuma = base.Format == D3DFMT_A4L4 ||
                              base.Format == D3DFMT_L16;
    // D3D9 G16R16 is a four-byte, two-channel texture, not BGRA8.
    const bool rg16 = base.Format == D3DFMT_G16R16;
    // Game-authored 64-bit RGBA UNORM mips are byte-compatible with DXGI RGBA16.
    const bool rgba16 = base.Format == D3DFMT_A16B16G16R16;
    // Preserve real game float component payloads without BGRA8 quantization.
    const bool floatRgba = base.Format == D3DFMT_A16B16G16R16F ||
                           base.Format == D3DFMT_A32B32G32R32F;
    // Actual game R/RG floating-point texture mip data has no BGRA8
    // representation: preserve the native scalar/vector IEEE754 channels
    // through the same immutable SRV used by Draw and DrawIndexed.
    const bool floatVector = base.Format == D3DFMT_R16F ||
                             base.Format == D3DFMT_G16R16F ||
                             base.Format == D3DFMT_R32F ||
                             base.Format == D3DFMT_G32R32F;
    const auto floatVectorLayout =
        base.Format == D3DFMT_R16F ? float_vector_texture::Layout::r16f :
        base.Format == D3DFMT_G16R16F ? float_vector_texture::Layout::rg16f :
        base.Format == D3DFMT_R32F ? float_vector_texture::Layout::r32f :
                                     float_vector_texture::Layout::rg32f;
    const auto floatLayout = base.Format == D3DFMT_A32B32G32R32F ?
        float_rgba_texture::Layout::rgba32f : float_rgba_texture::Layout::rgba16f;
    // Some legacy menu/text atlases encode palette index and per-texel alpha.
    // The native diagnostic must fetch the live game palette, not treat
    // A8P8's two bytes as a packed RGB color.
    const bool a8p8 = base.Format == D3DFMT_A8P8;
    // P8 uses one palette index per game texel; alpha may come from the
    // current palette only when the D3D9 device exposes ALPHAPALETTE.
    const bool p8 = base.Format == D3DFMT_P8;
    // Packed 3:3:2 game textures carry one color byte and optional alpha.
    const bool rgb332 = base.Format == D3DFMT_R3G3B2 ||
                        base.Format == D3DFMT_A8R3G3B2;
    const auto rgb332Layout = base.Format == D3DFMT_A8R3G3B2 ?
        rgb332_texture::Layout::a8rgb332 : rgb332_texture::Layout::rgb332;
    // D3D9 packed 16-bit texture formats have no equivalent sRGB D3D11 SRV.
    // Keep their live Draw on DX9Ex; never decode as linear by mistake.
    if (capture.srgbTexture && packed16) return false;
    // Legacy alpha/luminance sRGB parity has not been proven: DX9Ex owns it.
    if (capture.srgbTexture && luminance) return false;
    // Unproven 10-bit D3D9 sRGB transfer semantics remain on DX9Ex.
    if (capture.srgbTexture && tenBit) return false;
    // Legacy luminance sRGB transfer is not yet proven for this native path.
    if (capture.srgbTexture && extendedLuma) return false;
    // Do not assume D3D9 sRGB transfer for high precision RG; DX9Ex owns it.
    if (capture.srgbTexture && rg16) return false;
    // No sRGB view exists for 16-bit UNORM: never silently sample as linear.
    if (capture.srgbTexture && rgba16) return false;
    // FLOAT SRVs lack sRGB views. Unverified D3D9 modes stay with DX9Ex.
    if (capture.srgbTexture && floatRgba) return false;
    // FLOAT source textures have no DXGI sRGB view. Never reinterpret a
    // game-authored sRGB request as linear in the diagnostic output.
    if (capture.srgbTexture && floatVector) return false;
    // Palettized sRGB lookup/transfer parity is not proven on D3D9.
    if (capture.srgbTexture && a8p8) return false;
    if (capture.srgbTexture && p8) return false;
    // No verified legacy sRGB equivalence for 3:3:2 packed color.
    if (capture.srgbTexture && rgb332) return false;
    DXGI_FORMAT nativeFormat = DXGI_FORMAT_UNKNOWN;
    if (compressed) {
        // A full-sized BC base level is required, but its final mips may
        // legally be 2x2 or 1x1, each occupying one compressed 4x4 block.
        if ((base.Width & 3u) || (base.Height & 3u)) return false;
        nativeFormat = base.Format == D3DFMT_DXT1 ?
            (capture.srgbTexture ? DXGI_FORMAT_BC1_UNORM_SRGB : DXGI_FORMAT_BC1_UNORM) :
            base.Format == D3DFMT_DXT3 ?
            (capture.srgbTexture ? DXGI_FORMAT_BC2_UNORM_SRGB : DXGI_FORMAT_BC2_UNORM) :
            (capture.srgbTexture ? DXGI_FORMAT_BC3_UNORM_SRGB : DXGI_FORMAT_BC3_UNORM);
    } else if (base.Format == D3DFMT_A8R8G8B8 ||
               base.Format == D3DFMT_X8R8G8B8 || packed16 || luminance || rgb24 || rgbaSwizzle || tenBit || extendedLuma) {
        nativeFormat = capture.srgbTexture ?
            DXGI_FORMAT_B8G8R8A8_UNORM_SRGB : DXGI_FORMAT_B8G8R8A8_UNORM;
    } else if (floatVector) {
        // D3D9 R16F/G16R16F/R32F/G32R32F LockRect rows match the
        // little-endian DXGI R/RG FLOAT component ordering and precision.
        nativeFormat = base.Format == D3DFMT_R16F ? DXGI_FORMAT_R16_FLOAT :
            base.Format == D3DFMT_G16R16F ? DXGI_FORMAT_R16G16_FLOAT :
            base.Format == D3DFMT_R32F ? DXGI_FORMAT_R32_FLOAT :
                                         DXGI_FORMAT_R32G32_FLOAT;
    } else if (rgba16) {
        // Preserve all game R/G/B/A 16-bit channels in a native UNORM SRV.
        nativeFormat = DXGI_FORMAT_R16G16B16A16_UNORM;
    } else if (floatRgba) {
        // Game D3D9 FLOAT memory matches little-endian DXGI R/G/B/A layout.
        nativeFormat = floatLayout == float_rgba_texture::Layout::rgba16f ?
            DXGI_FORMAT_R16G16B16A16_FLOAT : DXGI_FORMAT_R32G32B32A32_FLOAT;
    } else if (rg16) {
        // RG16 is converted to BGRA8 per row; no native format reinterpretation.
        nativeFormat = DXGI_FORMAT_B8G8R8A8_UNORM;
    } else if (rgb332) {
        // One/two-byte source texels expand into four-byte BGRA8 pixels.
        nativeFormat = DXGI_FORMAT_B8G8R8A8_UNORM;
    } else if (p8) {
        // Decode the active D3D9 palette, including supported palette alpha.
        nativeFormat = DXGI_FORMAT_B8G8R8A8_UNORM;
    } else if (a8p8) {
        // Current D3D9 palette RGB and source alpha must be decoded per texel.
        nativeFormat = DXGI_FORMAT_B8G8R8A8_UNORM;
    } else return false;

    // Real D3D9 menu/car atlases can be 2048 square. Budget the complete
    // converted D3D11 SRV mip payload *before* palette lookup, D3D9 readback,
    // CPU copies or GPU allocation. Packed/palette/RGB24 formats expand to
    // BGRA8, while BC and native half/full floats retain their own pitches.
    // Use the actual destination DXGI pixel size. This keeps the existing
    // per-format D3D9 source-byte contracts unique for destructive regression
    // tests while correctly budgeting the converted *native* SRV payload.
    const UINT atlasTexelBytes =
        nativeFormat == DXGI_FORMAT_R32G32B32A32_FLOAT ? 16u :
        (nativeFormat == DXGI_FORMAT_R16G16B16A16_FLOAT ||
         nativeFormat == DXGI_FORMAT_R16G16B16A16_UNORM ||
         nativeFormat == DXGI_FORMAT_R32G32_FLOAT) ? 8u : 4u;
    const UINT atlasBlockBytes = compressed ?
        (base.Format == D3DFMT_DXT1 ? 8u : 16u) : 0u;
    if (!native_game_texture_upload_bytes(
            base.Width, base.Height, levels,
            compressed ? 0u : atlasTexelBytes, atlasBlockBytes))
        return false;

    ComPtr<IDirect3DSurface9> readbackSurface;
    ComPtr<IDirect3DDevice9> gameDevice;
    if (gpuRenderTarget &&
        (FAILED(capture.texture->GetDevice(gameDevice.GetAddressOf())) ||
         !gameDevice)) return false;

    std::array<a8p8_texture::Rgb, 256> activePalette{};
    std::array<p8_texture::Rgba, 256> p8Palette{};
    if (a8p8 || p8) {
        // Palette selection is device state and can change between game
        // Draw calls. Snapshot it alongside the texture before reading mips.
        ComPtr<IDirect3DDevice9> paletteDevice;
        UINT paletteNumber = 0;
        std::array<PALETTEENTRY, 256> entries{};
        if (FAILED(capture.texture->GetDevice(paletteDevice.GetAddressOf())) ||
            !paletteDevice ||
            FAILED(paletteDevice->GetCurrentTexturePalette(&paletteNumber)) ||
            FAILED(paletteDevice->GetPaletteEntries(paletteNumber, entries.data())))
            return false;
        // The palette alpha byte is not used by A8P8 (which has per-texel
        // alpha), but IS part of a P8 sample on ALPHAPALETTE-capable devices.
        // Query live caps rather than assuming an opaque or alpha palette.
        bool alphaPalette = false;
        if (p8) {
            D3DCAPS9 caps{};
            if (FAILED(paletteDevice->GetDeviceCaps(&caps))) return false;
            alphaPalette = (caps.TextureCaps & D3DPTEXTURECAPS_ALPHAPALETTE) != 0u;
        }
        for (std::size_t i = 0; i < entries.size(); ++i) {
            activePalette[i] = {entries[i].peRed, entries[i].peGreen,
                                entries[i].peBlue};
            p8Palette[i] = {entries[i].peRed, entries[i].peGreen,
                            entries[i].peBlue,
                            static_cast<std::uint8_t>(alphaPalette ? entries[i].peFlags : 0xffu)};
        }
    }

    const auto luminanceLayout = base.Format == D3DFMT_A8 ?
        luminance_texture::Layout::alpha8 :
        base.Format == D3DFMT_L8 ?
        luminance_texture::Layout::luminance8 :
        luminance_texture::Layout::alpha8_luminance8;
    const auto extendedLumaLayout = base.Format == D3DFMT_L16 ?
        extended_luminance_texture::Layout::luminance16 :
        extended_luminance_texture::Layout::alpha4_luminance4;
    const UINT sourceTexelBytes = packed16 ? 2u :
        floatRgba ? float_rgba_texture::source_bytes_per_texel(floatLayout) :
        floatVector ? float_vector_texture::source_bytes_per_texel(floatVectorLayout) :
        rgba16 ? rgba16_texture::source_bytes_per_texel() :
        luminance ? luminance_texture::source_bytes_per_texel(luminanceLayout) :
        extendedLuma ? extended_luminance_texture::source_bytes_per_texel(extendedLumaLayout) :
        a8p8 ? a8p8_texture::source_bytes_per_texel() :
        p8 ? p8_texture::source_bytes_per_texel() :
        rgb332 ? rgb332_texture::source_bytes_per_texel(rgb332Layout) :
        rgb24 ? rgb24_texture::source_bytes_per_texel() : 4u;
    std::vector<std::vector<std::uint8_t>> copied(levels);
    std::vector<UINT> pitches(levels);
    for (UINT level = 0; level < levels; ++level) {
        D3DSURFACE_DESC desc{};
        if (FAILED(capture.texture->GetLevelDesc(level, &desc)) ||
            desc.Format != base.Format || desc.Pool != base.Pool ||
            (sourceRoute == dynamic_texture::SourceRoute::dynamic_default &&
             desc.Usage != base.Usage) ||
            desc.Width != (std::max)(1u, base.Width >> level) ||
            desc.Height != (std::max)(1u, base.Height >> level))
            return false;
        if (gpuRenderTarget) {
            // Reading base mip 0 repeatedly into smaller upload pitches would
            // corrupt the vehicle/race sampler. Snapshot this exact D3D9
            // render-target mip into a same-size SYSTEMMEM surface instead.
            readbackSurface.Reset();
            ComPtr<IDirect3DSurface9> sourceSurface;
            D3DSURFACE_DESC sourceDesc{};
            if (FAILED(capture.texture->GetSurfaceLevel(level, sourceSurface.GetAddressOf())) ||
                !sourceSurface ||
                FAILED(sourceSurface->GetDesc(&sourceDesc)) ||
                sourceDesc.Format != desc.Format ||
                sourceDesc.Pool != desc.Pool ||
                !(sourceDesc.Usage & D3DUSAGE_RENDERTARGET) ||
                sourceDesc.MultiSampleType != D3DMULTISAMPLE_NONE ||
                !native_rt_readback::matching_mip_extent(
                    base.Width, base.Height, level, sourceDesc.Width, sourceDesc.Height) ||
                sourceDesc.Width != desc.Width || sourceDesc.Height != desc.Height ||
                FAILED(gameDevice->CreateOffscreenPlainSurface(
                    desc.Width, desc.Height, desc.Format, D3DPOOL_SYSTEMMEM,
                    readbackSurface.GetAddressOf(), nullptr)) ||
                FAILED(gameDevice->GetRenderTargetData(sourceSurface.Get(), readbackSurface.Get())))
                return false;
        }
        const UINT rows = compressed ? (std::max)(1u, (desc.Height + 3u) / 4u) : desc.Height;
        const UINT rowBytes = compressed ?
            (std::max)(1u, (desc.Width + 3u) / 4u) *
                (base.Format == D3DFMT_DXT1 ? 8u : 16u) :
            desc.Width * sourceTexelBytes;
        const UINT uploadPitch = ((packed16 || luminance) || rgb24 || rgbaSwizzle) || extendedLuma || rgb332 || p8 ?
            desc.Width * 4u : rowBytes;
        // Preserve existing format pitch contracts and only widen A8P8
        // (two source bytes per texel) to four-byte decoded native pixels.
        const UINT a8p8UploadPitch = a8p8 ? desc.Width * 4u : uploadPitch;
        D3DLOCKED_RECT lock{};
        const HRESULT lockResult = gpuRenderTarget ?
            readbackSurface->LockRect(&lock, nullptr, D3DLOCK_READONLY) :
            capture.texture->LockRect(level, &lock, nullptr, D3DLOCK_READONLY);
        if (FAILED(lockResult)) return false;
        const bool readable = lock.pBits &&
            dynamic_texture::readable_pitch(lock.Pitch, rowBytes);
        if (readable) {
            auto& pixels = copied[level];
            pixels.resize(static_cast<std::size_t>(uploadPitch) * rows);
            // Only palettized rows need widening beyond the source pitch.
            if (a8p8) pixels.resize(static_cast<std::size_t>(a8p8UploadPitch) * rows);
            const auto packing = base.Format == D3DFMT_R5G6B5 ?
                packed_texture16::Layout::rgb565 :
                base.Format == D3DFMT_A1R5G5B5 ?
                packed_texture16::Layout::argb1555 :
                base.Format == D3DFMT_A4R4G4B4 ?
                packed_texture16::Layout::argb4444 :
                base.Format == D3DFMT_X1R5G5B5 ?
                packed_texture16::Layout::xrgb1555 :
                packed_texture16::Layout::xrgb4444;
            for (UINT y = 0; y < rows; ++y) {
                const auto* source = static_cast<const std::uint8_t*>(lock.pBits) +
                                     static_cast<std::size_t>(y) * lock.Pitch;
                auto* destination = pixels.data() + static_cast<std::size_t>(y) * uploadPitch;
                if (a8p8)
                    destination = pixels.data() + static_cast<std::size_t>(y) * a8p8UploadPitch;
                if (gpuRenderTarget) {
                    // Decode the readback's exact D3D9 color layout before
                    // binding this real game-authored texture in native Draw.
                    if (!native_rt_readback::unpack_row(
                            source, destination, desc.Width, rtLayout)) {
                        readbackSurface->UnlockRect();
                        return false;
                    }
                } else if (packed16)
                    packed_texture16::unpack_row(source, destination, desc.Width, packing);
                else if (luminance)
                    luminance_texture::unpack_row(source, destination, desc.Width, luminanceLayout);
                else if (extendedLuma)
                    extended_luminance_texture::unpack_row(source, destination, desc.Width, extendedLumaLayout);
                else if (rgb24)
                    rgb24_texture::unpack_row(source, destination, desc.Width);
                else if (rg16)
                    rg16_texture::unpack_row(source, destination, desc.Width);
                else if (rgba16)
                    rgba16_texture::copy_row(source, destination, desc.Width);
                else if (floatRgba)
                    float_rgba_texture::copy_row(source, destination, desc.Width, floatLayout);
                else if (floatVector)
                    float_vector_texture::copy_row(source, destination, desc.Width, floatVectorLayout);
                else if (rgb332)
                    rgb332_texture::unpack_row(source, destination, desc.Width, rgb332Layout);
                else if (p8)
                    p8_texture::unpack_row(source, destination, desc.Width,
                                           p8Palette.data());
                else if (a8p8)
                    a8p8_texture::unpack_row(source, destination, desc.Width,
                                             activePalette.data());
                else if (rgbaSwizzle)
                    rgba_texture::unpack_row(source, destination, desc.Width,
                        base.Format == D3DFMT_X8B8G8R8 ?
                            rgba_texture::Layout::xrgb : rgba_texture::Layout::argb);
                else if (tenBit)
                    tenbit_texture::unpack_row(source, destination, desc.Width,
                        base.Format == D3DFMT_A2B10G10R10 ?
                            tenbit_texture::Layout::a2b10g10r10 :
                            tenbit_texture::Layout::a2r10g10b10);
                else
                    std::memcpy(destination, source, rowBytes);
            }
            // X8R8G8B8 has no usable alpha; every mip must sample opaque.
            if (base.Format == D3DFMT_X8R8G8B8)
                for (std::size_t p = 3; p < pixels.size(); p += 4)
                    pixels[p] = 0xffu;
            pitches[level] = a8p8UploadPitch;
        }
        const HRESULT unlockResult = gpuRenderTarget ?
            readbackSurface->UnlockRect() : capture.texture->UnlockRect(level);
        // A failed dynamic Unlock invalidates the diagnostic snapshot even
        // if LockRect yielded bytes. Original game Draw/input still proceed.
        if (FAILED(unlockResult)) return false;
        if (!readable) return false;
    }
    std::vector<D3D11_SUBRESOURCE_DATA> initial(levels);
    for (UINT level = 0; level < levels; ++level) {
        initial[level].pSysMem = copied[level].data();
        initial[level].SysMemPitch = pitches[level];
    }
    D3D11_TEXTURE2D_DESC desc{};
    desc.Width = base.Width; desc.Height = base.Height;
    desc.MipLevels = levels; desc.ArraySize = 1;
    desc.Format = nativeFormat;
    desc.SampleDesc.Count = 1;
    desc.Usage = D3D11_USAGE_IMMUTABLE;
    desc.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    ComPtr<ID3D11Texture2D> texture;
    if (FAILED(dev->CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())) ||
        FAILED(dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())))
        return false;
    return create_game_sampler(dev, capture, levels, sampler);
}


bool capture_live_sm3_sampler(IDirect3DDevice9* game, unsigned slot,
                              TextureCapture& out) noexcept {
    if (!game || slot >= 16u) return false;
    ComPtr<IDirect3DBaseTexture9> source;
    if (FAILED(game->GetTexture(slot, source.GetAddressOf())) ||
        !source || source->GetType() != D3DRTYPE_TEXTURE ||
        FAILED(source.As(&out.texture))) return false;
    DWORD u{}, v{}, mag{}, min{}, mip{}, maxMip{}, anisotropy{}, srgb{}, border{}, bias{};
    if (FAILED(game->GetSamplerState(slot, D3DSAMP_ADDRESSU, &u)) ||
        FAILED(game->GetSamplerState(slot, D3DSAMP_ADDRESSV, &v)) ||
        FAILED(game->GetSamplerState(slot, D3DSAMP_MAGFILTER, &mag)) ||
        FAILED(game->GetSamplerState(slot, D3DSAMP_MINFILTER, &min)) ||
        FAILED(game->GetSamplerState(slot, D3DSAMP_MIPFILTER, &mip)) ||
        FAILED(game->GetSamplerState(slot, D3DSAMP_MAXMIPLEVEL, &maxMip)) ||
        FAILED(game->GetSamplerState(slot, D3DSAMP_MAXANISOTROPY, &anisotropy)) ||
        FAILED(game->GetSamplerState(slot, D3DSAMP_SRGBTEXTURE, &srgb)) ||
        FAILED(game->GetSamplerState(slot, D3DSAMP_BORDERCOLOR, &border)) ||
        FAILED(game->GetSamplerState(slot, D3DSAMP_MIPMAPLODBIAS, &bias)))
        return false;
    DWORD addressW{};
    // 2D sampling ignores W, but an unsupported U/V profile never clamps.
    if (FAILED(game->GetSamplerState(slot, D3DSAMP_ADDRESSW, &addressW)))
        return false;
    out.enabled = true;
    out.addressU = static_cast<D3DTEXTUREADDRESS>(u);
    out.addressV = static_cast<D3DTEXTUREADDRESS>(v);
    out.magFilter = static_cast<D3DTEXTUREFILTERTYPE>(mag);
    out.minFilter = static_cast<D3DTEXTUREFILTERTYPE>(min);
    out.mipFilter = static_cast<D3DTEXTUREFILTERTYPE>(mip);
    out.maxMipLevel = maxMip;
    out.maxAnisotropy = anisotropy;
    out.srgbTexture = srgb != FALSE;
    out.borderColor = border;
    std::memcpy(&out.mipLodBias, &bias, sizeof(bias));
    return true;
}

std::uint64_t live_sm3_pipeline_identity(
    const ProgrammableShaderFunctionSourceEvidence& vertex,
    const ProgrammableShaderFunctionSourceEvidence& pixel,
    const std::vector<D3DVERTEXELEMENT9>& declaration,
    unsigned alphaCompare) noexcept {
    if (!vertex.exact() || !pixel.exact() || declaration.empty() ||
        alphaCompare > 8u) return 0u;
    std::uint64_t h = 1469598103934665603ull;
    const auto hashBytes = [&](const void* value, std::size_t bytes) {
        const auto* b = static_cast<const std::uint8_t*>(value);
        for (std::size_t i = 0; i < bytes; ++i) {
            h ^= b[i];
            h *= 1099511628211ull;
        }
    };
    hashBytes(vertex.tokens.data(), vertex.byteSize);
    hashBytes(pixel.tokens.data(), pixel.byteSize);
    hashBytes(declaration.data(), declaration.size() * sizeof(D3DVERTEXELEMENT9));
    // Distinct alpha comparisons compile distinct native pixel shaders.
    // Do not reuse a cached no-alpha shader for a menu alpha-tested Draw.
    hashBytes(&alphaCompare, sizeof(alphaCompare));
    return h != 0u ? h : 1u;
}

// A real live D3D9 declaration drives the native IA, never an FVF-shaped
// substitute. Source offsets and formats must fit the rebased game stream.
bool live_sm3_input_layout(
    const std::vector<D3DVERTEXELEMENT9>& declaration, UINT stride,
    std::vector<D3D11_INPUT_ELEMENT_DESC>& layout,
    bool& repack, UINT& nativeStride) noexcept {
    if (declaration.size() < 2u || stride == 0u) return false;
    static constexpr const char* kPosition = "POSITION";
    static constexpr const char* kTexcoord = "TEXCOORD";
    static constexpr const char* kNormal = "NORMAL";
    static constexpr const char* kColor = "COLOR";
    static constexpr const char* kBlendWeight = "BLENDWEIGHT";
    static constexpr const char* kBlendIndices = "BLENDINDICES";
    static constexpr const char* kTangent = "TANGENT";
    static constexpr const char* kBinormal = "BINORMAL";
    static constexpr const char* kPositionT = "POSITIONT";
    static constexpr const char* kPsize = "PSIZE";
    static constexpr const char* kFog = "FOG";
    static constexpr const char* kDepth = "DEPTH";
    static constexpr const char* kSample = "SAMPLE";
    repack = false;
    nativeStride = stride;
    for (std::size_t i = 0; i + 1u < declaration.size(); ++i) {
        const auto& in = declaration[i];
        if (in.Stream != 0u || in.Method != D3DDECLMETHOD_DEFAULT ||
            in.UsageIndex >= 16u) return false;
        DXGI_FORMAT format = DXGI_FORMAT_UNKNOWN;
        const UINT width = game_sm3_decl_width(in.Type);
        switch (in.Type) {
        case D3DDECLTYPE_FLOAT1: format = DXGI_FORMAT_R32_FLOAT; break;
        case D3DDECLTYPE_FLOAT2: format = DXGI_FORMAT_R32G32_FLOAT; break;
        case D3DDECLTYPE_FLOAT3: format = DXGI_FORMAT_R32G32B32_FLOAT; break;
        case D3DDECLTYPE_FLOAT4: format = DXGI_FORMAT_R32G32B32A32_FLOAT; break;
        default:
            if (width == 0u) return false;
            // Native IA cannot safely reinterpret D3D9 packed integer,
            // D3DCOLOR or half values as the float SM3 signature.
            repack = true;
            format = DXGI_FORMAT_R32G32B32A32_FLOAT;
            break;
        }
        if (static_cast<UINT>(in.Offset) + width > stride) return false;
        const char* name = nullptr;
        switch (in.Usage) {
        case D3DDECLUSAGE_POSITION: name = kPosition; break;
        case D3DDECLUSAGE_TEXCOORD: name = kTexcoord; break;
        case D3DDECLUSAGE_NORMAL: name = kNormal; break;
        case D3DDECLUSAGE_COLOR: name = kColor; break;
        case D3DDECLUSAGE_BLENDWEIGHT: name = kBlendWeight; break;
        case D3DDECLUSAGE_BLENDINDICES: name = kBlendIndices; break;
        case D3DDECLUSAGE_TANGENT: name = kTangent; break;
        case D3DDECLUSAGE_BINORMAL: name = kBinormal; break;
        case D3DDECLUSAGE_POSITIONT: name = kPositionT; break;
        case D3DDECLUSAGE_PSIZE: name = kPsize; break;
        case D3DDECLUSAGE_FOG: name = kFog; break;
        case D3DDECLUSAGE_DEPTH: name = kDepth; break;
        case D3DDECLUSAGE_SAMPLE: name = kSample; break;
        default: return false;
        }
        for (const auto& old : layout)
            if (std::strcmp(old.SemanticName, name) == 0 &&
                old.SemanticIndex == in.UsageIndex) return false;
        D3D11_INPUT_ELEMENT_DESC element{};
        element.SemanticName = name;
        element.SemanticIndex = in.UsageIndex;
        element.Format = format;
        element.InputSlot = 0u;
        element.AlignedByteOffset = in.Offset;
        element.InputSlotClass = D3D11_INPUT_PER_VERTEX_DATA;
        layout.push_back(element);
    }
    const auto& end = declaration.back();
    if (layout.empty() || end.Stream != 0xffu ||
        end.Type != D3DDECLTYPE_UNUSED) return false;
    if (repack) {
        // Full FLOAT4 packing also supplies D3D9's missing 0/0/0/1 defaults.
        // Bind only a validated source-owned stream; no D3D9 GPU references.
        if (layout.size() > (1u << 20u) / (4u * sizeof(float))) return false;
        nativeStride = static_cast<UINT>(layout.size() * 4u * sizeof(float));
        for (std::size_t i = 0; i < layout.size(); ++i) {
            layout[i].Format = DXGI_FORMAT_R32G32B32A32_FLOAT;
            layout[i].AlignedByteOffset = static_cast<UINT>(i * 16u);
        }
    }
    return true;
}

bool live_sm3_shader_bytes(IDirect3DVertexShader9* vertexShader,
                           IDirect3DPixelShader9* pixelShader,
                           ProgrammableShaderFunctionSourceEvidence& vertex,
                           ProgrammableShaderFunctionSourceEvidence& pixel) noexcept {
    if (!vertexShader || !pixelShader) return false;
    UINT vb = 0u, pb = 0u;
    if (FAILED(vertexShader->GetFunction(nullptr, &vb)) ||
        FAILED(pixelShader->GetFunction(nullptr, &pb)) ||
        vb < 8u || pb < 8u || vb > (1u << 20u) || pb > (1u << 20u) ||
        (vb % 4u) != 0u || (pb % 4u) != 0u) return false;
    std::vector<DWORD> v(vb / 4u), p(pb / 4u);
    if (FAILED(vertexShader->GetFunction(v.data(), &vb)) ||
        FAILED(pixelShader->GetFunction(p.data(), &pb))) return false;
    vertex = capture_programmable_shader_function_source_evidence(v.data(), vb, true);
    pixel = capture_programmable_shader_function_source_evidence(p.data(), pb, false);
    return vertex.exact() && pixel.exact();
}

// The real-game VB/IB upload routines are defined below this SM3 caller.
// Declare their exact signatures so both the programmable and fixed-function
// Draw/DrawIndexed paths share the same GPU allocation/Map transaction.
bool ensure_full_game_upload_buffer(ID3D11Device* dev,
                                    ComPtr<ID3D11Buffer>& resource,
                                    UINT& capacity, UINT required,
                                    UINT bindFlags) noexcept;
bool upload_full_game_stream(ID3D11DeviceContext* context,
                             ID3D11Buffer* buffer, UINT capacity,
                             const void* source, UINT bytes) noexcept;

// Real programmable D3D9 game source -> SM3 HLSL/DXBC -> native D3D11
// IA/VS/PS/tN/sN/b0/Draw. Preserve live game CW/CCW culling and the
// four exact D3D9 RGB+alpha blend equations already owned by the backend.
// Unknown stencil, alpha-test, fog and blend states still fail closed.
// Live programmable geometry can now share the native DSV and scissor path
// with full-frame fixed-function Draws without reusing D3D9 GPU resources.
bool submit_live_sm3_game_draw(State& s, IDirect3DDevice9* game,
                               D3DPRIMITIVETYPE type, UINT expected,
                               const void* bytes, UINT stride, UINT vertexCount,
                               const std::uint32_t* indices, UINT indexCount,
                               std::uint64_t sourceOrdinal) noexcept {
    if (!env_full_game_opt_in() || !game || !bytes || !stride ||
        vertexCount == 0u || vertexCount > kMaxVertices ||
        type != D3DPT_TRIANGLELIST && type != D3DPT_TRIANGLESTRIP &&
        type != D3DPT_TRIANGLEFAN)
        return false;
    // The shared R30 observer has already validated the exact source
    // primitive element count. Reuse it rather than decoding twice.
    if (!expected ||
        (indices && (indexCount != expected || indexCount > kMaxIndices)) ||
        (!indices && vertexCount != expected) ||
        (indices && indexCount == 0u))
        return false;
    if (static_cast<std::uint64_t>(stride) * vertexCount > (1ull << 25u))
        return false;
    // The game's SM3 menu/vehicle TRIANGLEFAN has no D3D11 topology.
    // Expand its authentic VB/IB/UP span to triangles BEFORE GPU mutation.
    // On invalid or oversized source input, keep the original D3D9 renderer.
    std::vector<std::uint32_t> nativeFanTriangles;
    const std::uint32_t* nativeIndices = indices;
    UINT nativeIndexCount = indexCount;
    if (type == D3DPT_TRIANGLEFAN) {
        if (expected < 3u ||
            !game_fan_to_triangle_list(expected - 2u, indices, indexCount,
                                       vertexCount, nativeFanTriangles) ||
            nativeFanTriangles.size() > kMaxIndices)
            return false;
        nativeIndices = nativeFanTriangles.data();
        nativeIndexCount = static_cast<UINT>(nativeFanTriangles.size());
    }
    DWORD blend = TRUE, alpha = TRUE, stencil = TRUE, depth = TRUE;
    DWORD fog = TRUE, scissor = TRUE, clipPlanes = 1u, fill = 0u;
    DWORD colorMask = 0u, cull = 0u, srgbWrite = TRUE;
    DWORD srcBlend = 0u, dstBlend = 0u, blendOp = 0u, separateAlpha = TRUE;
    DWORD srcBlendAlpha = 0u, dstBlendAlpha = 0u, blendOpAlpha = 0u;
    DWORD alphaFunc = 0u, alphaRef = 0u;
    D3DVIEWPORT9 viewport{};
    if (FAILED(game->GetViewport(&viewport)) ||
        FAILED(game->GetRenderState(D3DRS_ALPHABLENDENABLE, &blend)) ||
        FAILED(game->GetRenderState(D3DRS_ALPHATESTENABLE, &alpha)) ||
        FAILED(game->GetRenderState(D3DRS_STENCILENABLE, &stencil)) ||
        FAILED(game->GetRenderState(D3DRS_ZENABLE, &depth)) ||
        FAILED(game->GetRenderState(D3DRS_FOGENABLE, &fog)) ||
        FAILED(game->GetRenderState(D3DRS_SCISSORTESTENABLE, &scissor)) ||
        FAILED(game->GetRenderState(D3DRS_CLIPPLANEENABLE, &clipPlanes)) ||
        FAILED(game->GetRenderState(D3DRS_FILLMODE, &fill)) ||
        FAILED(game->GetRenderState(D3DRS_CULLMODE, &cull)) ||
        FAILED(game->GetRenderState(D3DRS_COLORWRITEENABLE, &colorMask)) ||
        FAILED(game->GetRenderState(D3DRS_SRGBWRITEENABLE, &srgbWrite)) ||
        stencil || fog || clipPlanes || fill != D3DFILL_SOLID ||
        colorMask != 0x0fu || srgbWrite != FALSE ||
        !game_native_backbuffer_ready(game, viewport))
        return false;
    // SM3 pixel alpha test is shader-side in D3D11, not a blend state.
    // Preserve the exact live game's compare and 8-bit reference per Draw.
    if (alpha != FALSE &&
        (FAILED(game->GetRenderState(D3DRS_ALPHAFUNC, &alphaFunc)) ||
         FAILED(game->GetRenderState(D3DRS_ALPHAREF, &alphaRef)) ||
         alphaFunc < D3DCMP_NEVER || alphaFunc > D3DCMP_ALWAYS ||
         alphaRef > 255u))
        return false;
    // Reject an unknown game raster winding before any D3D11 mutation.
    GameNativeCullAdmission nativeCull{};
    if (!game_native_cull_admission(
            cull, static_cast<std::uint32_t>(type), nativeCull))
        return false;
    if (blend != FALSE &&
        (FAILED(game->GetRenderState(D3DRS_SRCBLEND, &srcBlend)) ||
         FAILED(game->GetRenderState(D3DRS_DESTBLEND, &dstBlend)) ||
         FAILED(game->GetRenderState(D3DRS_BLENDOP, &blendOp)) ||
         FAILED(game->GetRenderState(
             D3DRS_SEPARATEALPHABLENDENABLE, &separateAlpha))))
        return false;
    if (blend != FALSE && separateAlpha != FALSE &&
        (FAILED(game->GetRenderState(D3DRS_SRCBLENDALPHA, &srcBlendAlpha)) ||
         FAILED(game->GetRenderState(D3DRS_DESTBLENDALPHA, &dstBlendAlpha)) ||
         FAILED(game->GetRenderState(D3DRS_BLENDOPALPHA, &blendOpAlpha))))
        return false;
    const auto nativeBlend = live_sm3_blend(
        blend != FALSE, srcBlend, dstBlend, blendOp, separateAlpha != FALSE);
    D3D11_RENDER_TARGET_BLEND_DESC extendedDesc{};
    if (nativeBlend == LiveSm3Blend::unsupported &&
        !sm3_live_blend_desc(srcBlend, dstBlend, blendOp,
            separateAlpha != FALSE, srcBlendAlpha, dstBlendAlpha,
            blendOpAlpha, extendedDesc)) return false;
    ComPtr<IDirect3DSurface9> target;
    ComPtr<IUnknown> targetIdentity;
    D3DSURFACE_DESC source{};
    auto& liveBatch = s.frameBatch;
    if (FAILED(game->GetRenderTarget(0, target.GetAddressOf())) ||
        !target || FAILED(target->GetDesc(&source)) ||
        FAILED(target.As(&targetIdentity)) || !targetIdentity ||
        !s.clearColor.matches(reinterpret_cast<std::uintptr_t>(game),
             reinterpret_cast<std::uintptr_t>(targetIdentity.Get())) ||
        !liveBatch.accepts_full_on_source_target(sourceOrdinal, true) ||
        !liveBatch.accepts_source_draw(sourceOrdinal, true) ||
        s.preDrawFills.count != 0u || viewport.Width == 0u ||
        viewport.Height == 0u) return false;
    // Intercept the REAL programmable game Draw's Z contract. Depth history
    // is owned by the isolated native DSV, never by the game's D3D9 surface.
    // A different/unknown main Z, W-buffering, bias or MSAA returns to D3D9.
    GameNativeDepthAdmission liveDepth{};
    if (depth != D3DZB_FALSE) {
        DWORD zWrite = TRUE, zFunc = 0u, bias = ~0u, slopeBias = ~0u;
        ComPtr<IDirect3DSurface9> gameDepth;
        ComPtr<IUnknown> gameDepthIdentity;
        D3DSURFACE_DESC depthDesc{};
        if (FAILED(game->GetRenderState(D3DRS_ZWRITEENABLE, &zWrite)) ||
            FAILED(game->GetRenderState(D3DRS_ZFUNC, &zFunc)) ||
            FAILED(game->GetRenderState(D3DRS_DEPTHBIAS, &bias)) ||
            FAILED(game->GetRenderState(D3DRS_SLOPESCALEDEPTHBIAS, &slopeBias)) ||
            FAILED(game->GetDepthStencilSurface(gameDepth.GetAddressOf())) ||
            !gameDepth || FAILED(gameDepth->GetDesc(&depthDesc)) ||
            FAILED(gameDepth.As(&gameDepthIdentity)) || !gameDepthIdentity ||
            depthDesc.Width != source.Width ||
            depthDesc.Height != source.Height ||
            !s.clearColor.main_depth_still_bound(
                reinterpret_cast<std::uintptr_t>(gameDepthIdentity.Get())) ||
            !game_native_depth_admission(
                depth, zWrite, zFunc, bias, slopeBias,
                depthDesc.MultiSampleType == D3DMULTISAMPLE_NONE, liveDepth))
            return false;
    }
    const bool reverseDepth = liveDepth.orderingMode != 0u;
    if (!liveBatch.accepts_depth(liveDepth.enabled, reverseDepth))
        return false;
    // Full-resolution source scissor coordinates are already D3D11 pixels.
    // Clip to viewport AND RT boundaries; never broaden a live D3D9 scissor.
    const auto sourceRight = static_cast<std::int64_t>(source.Width);
    const auto sourceBottom = static_cast<std::int64_t>(source.Height);
    D3D11_RECT liveScissor{0, 0, static_cast<LONG>(source.Width),
                                static_cast<LONG>(source.Height)};
    if (scissor != FALSE) {
        RECT gameRect{};
        if (FAILED(game->GetScissorRect(&gameRect)) ||
            gameRect.right <= gameRect.left ||
            gameRect.bottom <= gameRect.top)
            return false;
        const std::int64_t l = (std::max)(
            std::int64_t{0}, (std::max)(static_cast<std::int64_t>(gameRect.left),
                                       static_cast<std::int64_t>(viewport.X)));
        const std::int64_t t = (std::max)(
            std::int64_t{0}, (std::max)(static_cast<std::int64_t>(gameRect.top),
                                       static_cast<std::int64_t>(viewport.Y)));
        const std::int64_t r = (std::min)(
            sourceRight, (std::min)(static_cast<std::int64_t>(gameRect.right),
                 static_cast<std::int64_t>(viewport.X) + viewport.Width));
        const std::int64_t b = (std::min)(
            sourceBottom, (std::min)(static_cast<std::int64_t>(gameRect.bottom),
                 static_cast<std::int64_t>(viewport.Y) + viewport.Height));
        if (r <= l || b <= t) return false;
        liveScissor = {static_cast<LONG>(l), static_cast<LONG>(t),
                       static_cast<LONG>(r), static_cast<LONG>(b)};
    }
    ComPtr<IDirect3DVertexShader9> vertexShader;
    ComPtr<IDirect3DPixelShader9> pixelShader;
    ComPtr<IDirect3DVertexDeclaration9> sourceDecl;
    if (FAILED(game->GetVertexShader(vertexShader.GetAddressOf())) ||
        FAILED(game->GetPixelShader(pixelShader.GetAddressOf())) ||
        FAILED(game->GetVertexDeclaration(sourceDecl.GetAddressOf())) ||
        !vertexShader || !pixelShader || !sourceDecl) return false;
    UINT count = MAXD3DDECLLENGTH;
    std::vector<D3DVERTEXELEMENT9> declaration(count);
    if (FAILED(sourceDecl->GetDeclaration(declaration.data(), &count)) ||
        count < 2u || count > MAXD3DDECLLENGTH) return false;
    declaration.resize(count);
    std::vector<D3D11_INPUT_ELEMENT_DESC> input;
    bool repack = false;
    UINT nativeStride = stride;
    if (!live_sm3_input_layout(declaration, stride, input,
                               repack, nativeStride)) return false;
    // A mixed packed/float D3D9 stream must reach the actual game's native
    // Draw in shader-visible FLOAT4 register order (not format bitcasts).
    // Reject oversized, malformed or untranslatable data before any upload.
    std::vector<std::uint8_t> unpacked;
    const void* nativeBytes = bytes;
    if (repack) {
        const auto total = static_cast<std::uint64_t>(nativeStride) * vertexCount;
        if (total == 0u || total > (1ull << 25u)) return false;
        try {
            unpacked.resize(static_cast<std::size_t>(total));
            const auto* original = static_cast<const std::uint8_t*>(bytes);
            for (UINT v = 0u; v < vertexCount; ++v) {
                for (std::size_t i = 0; i < input.size(); ++i) {
                    std::array<float, 4> decoded{};
                    if (!game_sm3_unpack_attribute(
                            declaration[i].Type,
                            original + static_cast<std::size_t>(v) * stride +
                                declaration[i].Offset, decoded)) return false;
                    std::memcpy(unpacked.data() +
                            static_cast<std::size_t>(v) * nativeStride + i * 16u,
                            decoded.data(), sizeof(decoded));
                }
            }
        } catch (...) { return false; }
        nativeBytes = unpacked.data();
    }
    ProgrammableShaderFunctionSourceEvidence vertexEvidence, pixelEvidence;
    if (!live_sm3_shader_bytes(vertexShader.Get(), pixelShader.Get(),
                              vertexEvidence, pixelEvidence)) return false;
    if (!ensure_pipeline(s, source.Width, source.Height)) return false;
    auto* device = s.backend.device();
    auto* context = s.backend.context();
    if (!device || !context) return false;
    ID3D11BlendState* extendedBlend = nullptr;
    if (nativeBlend == LiveSm3Blend::unsupported) {
        const auto blendKey = sm3_live_blend_key(extendedDesc);
        auto found = s.liveSm3BlendStates.find(blendKey);
        if (found == s.liveSm3BlendStates.end()) {
            if (s.liveSm3BlendStates.size() >= 64u) return false;
            D3D11_BLEND_DESC desc{};
            desc.RenderTarget[0] = extendedDesc;
            ComPtr<ID3D11BlendState> created;
            if (FAILED(device->CreateBlendState(&desc, created.GetAddressOf())) ||
                !created) return false;
            found = s.liveSm3BlendStates.emplace(blendKey, std::move(created)).first;
        }
        extendedBlend = found->second.Get();
        if (!extendedBlend) return false;
    }
    const auto key = live_sm3_pipeline_identity(
        vertexEvidence, pixelEvidence, declaration, alphaFunc);
    if (!key) return false;
    auto it = s.liveSm3Pipelines.find(key);
    if (it == s.liveSm3Pipelines.end()) {
        // Bound the number of compiled game programs per device/Reset.
        if (s.liveSm3Pipelines.size() >= 64u) return false;
        LiveSm3Pipeline pipeline{};
        if (!compile_native_live_sm3_program(
                device, vertexEvidence, pixelEvidence, alphaFunc, pipeline.program))
            return false;
        if (FAILED(device->CreateInputLayout(
                input.data(), static_cast<UINT>(input.size()),
                pipeline.program.vertexBytecode.data(),
                pipeline.program.vertexBytecode.size(),
                pipeline.inputLayout.GetAddressOf()))) return false;
        D3D11_BUFFER_DESC cb{};
        cb.ByteWidth = 256u * 4u * sizeof(float);
        cb.Usage = D3D11_USAGE_DEFAULT;
        cb.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
        if ((pipeline.program.vertexConstants &&
             FAILED(device->CreateBuffer(&cb, nullptr,
                        pipeline.vertexConstants.GetAddressOf()))) ||
            (pipeline.program.pixelConstants &&
             FAILED(device->CreateBuffer(&cb, nullptr,
                        pipeline.pixelConstants.GetAddressOf())))) return false;
        if (alphaFunc != 0u) {
            D3D11_BUFFER_DESC alphaDesc{};
            alphaDesc.ByteWidth = 16u;
            alphaDesc.Usage = D3D11_USAGE_DEFAULT;
            alphaDesc.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
            if (FAILED(device->CreateBuffer(&alphaDesc, nullptr,
                           pipeline.alphaReference.GetAddressOf())))
                return false;
        }
        pipeline.alphaCompare = alphaFunc;
        pipeline.vertexTokens = vertexEvidence.tokens;
        pipeline.pixelTokens = pixelEvidence.tokens;
        pipeline.declaration = declaration;
        it = s.liveSm3Pipelines.emplace(key, std::move(pipeline)).first;
    }
    auto& pipeline = it->second;
    // A hash collision may never reuse shaders or a declaration from a
    // different live game draw.
    if (pipeline.alphaCompare != alphaFunc ||
        (alphaFunc != 0u && !pipeline.alphaReference) ||
        pipeline.vertexTokens != vertexEvidence.tokens ||
        pipeline.pixelTokens != pixelEvidence.tokens ||
        pipeline.declaration.size() != declaration.size() ||
        std::memcmp(pipeline.declaration.data(), declaration.data(),
                    declaration.size() * sizeof(D3DVERTEXELEMENT9)) != 0)
        return false;
    // Bind the same native depth family as fixed-function menu/race Draws,
    // including write-disabled comparison and reversed/equality modes.
    // All resources/states must exist before mutating the current GPU frame.
    ID3D11DepthStencilState* liveDepthState = nullptr;
    if (liveDepth.enabled) {
        if (!s.diagnosticDepthView) {
            D3D11_TEXTURE2D_DESC zDesc{};
            zDesc.Width = s.nativeWidth;
            zDesc.Height = s.nativeHeight;
            zDesc.MipLevels = 1u;
            zDesc.ArraySize = 1u;
            zDesc.Format = DXGI_FORMAT_D32_FLOAT;
            zDesc.SampleDesc.Count = 1u;
            zDesc.Usage = D3D11_USAGE_DEFAULT;
            zDesc.BindFlags = D3D11_BIND_DEPTH_STENCIL;
            ComPtr<ID3D11Texture2D> created;
            ComPtr<ID3D11DepthStencilView> view;
            if (FAILED(device->CreateTexture2D(
                    &zDesc, nullptr, created.GetAddressOf())) ||
                FAILED(device->CreateDepthStencilView(
                    created.Get(), nullptr, view.GetAddressOf())))
                return false;
            s.diagnosticDepth = std::move(created);
            s.diagnosticDepthView = std::move(view);
        }
        ComPtr<ID3D11DepthStencilState>* state = nullptr;
        D3D11_COMPARISON_FUNC compare = D3D11_COMPARISON_LESS;
        if (liveDepth.always) {
            state = &s.diagnosticDepthAlwaysStates[liveDepth.writeEnabled ? 1u : 0u];
            compare = D3D11_COMPARISON_ALWAYS;
        } else if (liveDepth.equalityMode != 0u) {
            state = &s.diagnosticDepthEqualityStates[game_native_depth_equality_slot(
                liveDepth.writeEnabled, liveDepth.equalityMode)];
            compare = liveDepth.equalityMode == D3DCMP_EQUAL
                ? D3D11_COMPARISON_EQUAL : D3D11_COMPARISON_NOT_EQUAL;
        } else if (liveDepth.orderingMode != 0u) {
            state = &s.diagnosticDepthOrderingStates[game_native_depth_ordering_slot(
                liveDepth.writeEnabled, liveDepth.orderingMode)];
            compare = liveDepth.orderingMode == D3DCMP_GREATER
                ? D3D11_COMPARISON_GREATER : D3D11_COMPARISON_GREATER_EQUAL;
        } else {
            state = &s.diagnosticDepthStates[game_native_depth_slot(
                liveDepth.writeEnabled, liveDepth.lessEqual)];
            compare = liveDepth.lessEqual ? D3D11_COMPARISON_LESS_EQUAL
                                           : D3D11_COMPARISON_LESS;
        }
        if (!*state) {
            D3D11_DEPTH_STENCIL_DESC ds{};
            ds.DepthEnable = TRUE;
            ds.DepthWriteMask = liveDepth.writeEnabled
                ? D3D11_DEPTH_WRITE_MASK_ALL : D3D11_DEPTH_WRITE_MASK_ZERO;
            ds.DepthFunc = compare;
            ds.StencilEnable = FALSE;
            if (FAILED(device->CreateDepthStencilState(
                    &ds, state->GetAddressOf())))
                return false;
        }
        liveDepthState = state->Get();
    }
    // Mirror only samplers used by the translated ps_3_0 TEXLD program.
    // Every live tN/sN is bound on THIS D3D11 immediate context for THIS draw.
    std::array<ComPtr<ID3D11ShaderResourceView>,16> views{};
    std::array<ComPtr<ID3D11SamplerState>,16> samplers{};
    std::array<ID3D11ShaderResourceView*,16> boundViews{};
    std::array<ID3D11SamplerState*,16> boundSamplers{};
    for (unsigned slot = 0; slot < 16u; ++slot) {
        if ((pipeline.program.pixelSamplerMask & (1u << slot)) == 0u)
            continue;
        TextureCapture capture{};
        if (!capture_live_sm3_sampler(game, slot, capture) ||
            !mirror_texture(device, capture, views[slot], samplers[slot]))
            return false;
        boundViews[slot] = views[slot].Get();
        boundSamplers[slot] = samplers[slot].Get();
    }
    std::array<float, 256u * 4u> vertexConstants{};
    std::array<float, 256u * 4u> pixelConstants{};
    if ((pipeline.program.vertexConstants &&
         FAILED(game->GetVertexShaderConstantF(0, vertexConstants.data(), 256u))) ||
        (pipeline.program.pixelConstants &&
         FAILED(game->GetPixelShaderConstantF(0, pixelConstants.data(), 224u))))
        return false;
    const auto nativeByteCount = static_cast<std::uint64_t>(nativeStride) * vertexCount;
    if (!nativeByteCount || nativeByteCount > (1ull << 25u)) return false;
    const UINT vertexBytes = static_cast<UINT>(nativeByteCount);
    if (!ensure_full_game_upload_buffer(device, s.fullGameVertexUpload,
                                        s.fullGameVertexCapacity, vertexBytes,
                                        D3D11_BIND_VERTEX_BUFFER) ||
        !upload_full_game_stream(context, s.fullGameVertexUpload.Get(),
                                 s.fullGameVertexCapacity, nativeBytes, vertexBytes))
        return false;
    if (nativeIndices) {
        for (UINT i = 0; i < nativeIndexCount; ++i)
            if (nativeIndices[i] >= vertexCount) return false;
        const UINT indexBytes = nativeIndexCount * sizeof(std::uint32_t);
        if (!ensure_full_game_upload_buffer(device, s.fullGameIndexUpload,
                                            s.fullGameIndexCapacity, indexBytes,
                                            D3D11_BIND_INDEX_BUFFER) ||
            !upload_full_game_stream(context, s.fullGameIndexUpload.Get(),
                                     s.fullGameIndexCapacity, nativeIndices, indexBytes))
            return false;
    }
    if (liveBatch.first_draw()) {
        s.backend.begin_frame(s.clearColor.native_color(
            reinterpret_cast<std::uintptr_t>(game),
            reinterpret_cast<std::uintptr_t>(targetIdentity.Get()), kBackground));
        s.preDrawFills.discard();
    }
    if (pipeline.program.vertexConstants)
        context->UpdateSubresource(pipeline.vertexConstants.Get(), 0, nullptr,
                                   vertexConstants.data(), 0, 0);
    if (pipeline.program.pixelConstants)
        context->UpdateSubresource(pipeline.pixelConstants.Get(), 0, nullptr,
                                   pixelConstants.data(), 0, 0);
    if (alphaFunc != 0u) {
        const std::array<std::uint32_t, 4> reference{{alphaRef, 0u, 0u, 0u}};
        context->UpdateSubresource(pipeline.alphaReference.Get(), 0u, nullptr,
                                   reference.data(), 0u, 0u);
    }
    ID3D11Buffer* alphaBuffer = pipeline.alphaReference.Get();
    context->PSSetConstantBuffers(1u, 1u, &alphaBuffer);
    ID3D11Buffer* vsConstants = pipeline.vertexConstants.Get();
    ID3D11Buffer* psConstants = pipeline.pixelConstants.Get();
    context->VSSetConstantBuffers(0u, 1u, &vsConstants);
    context->PSSetConstantBuffers(0u, 1u, &psConstants);
    const D3D11_VIEWPORT nativeViewport{
        static_cast<float>(viewport.X), static_cast<float>(viewport.Y),
        static_cast<float>(viewport.Width), static_cast<float>(viewport.Height),
        viewport.MinZ, viewport.MaxZ};
    context->RSSetViewports(1u, &nativeViewport);
    context->RSSetScissorRects(1u, &liveScissor);
    const unsigned scissorSlot = scissor != FALSE ? 2u : 0u;
    ID3D11RasterizerState* liveRaster =
        nativeCull.d3d9Mode == D3DCULL_CW
            ? s.diagnosticCullRasters[scissorSlot].Get()
            : nativeCull.d3d9Mode == D3DCULL_CCW
                ? s.diagnosticCullRasters[scissorSlot + 1u].Get()
                : (scissor != FALSE ? s.scissorRaster.Get() : s.raster.Get());
    // Raster selection mirrors the source winding on both Draw/DrawIndexed.
    context->RSSetState(liveRaster);
    ID3D11RenderTargetView* rtv = s.backend.color_rtv();
    context->OMSetRenderTargets(
        1u, &rtv, liveDepth.enabled ? s.diagnosticDepthView.Get() : nullptr);
    // A preceding successful full game Z Clear owns the native depth seed.
    // First native Z draw must initialize DSV even after color-only Draws.
    if (liveDepth.enabled && liveBatch.clear_depth()) {
        context->ClearDepthStencilView(
            s.diagnosticDepthView.Get(), D3D11_CLEAR_DEPTH,
            liveBatch.depth_clear_value(reverseDepth), 0u);
        liveBatch.consume_depth_clear();
    }
    context->OMSetDepthStencilState(liveDepthState, 0u);
    ID3D11BlendState* liveBlend = nullptr;
    switch (nativeBlend) {
    case LiveSm3Blend::disabled: break;
    case LiveSm3Blend::straight_alpha: liveBlend = s.alphaBlend.Get(); break;
    case LiveSm3Blend::additive: liveBlend = s.additiveBlend.Get(); break;
    case LiveSm3Blend::source_alpha_add:
        liveBlend = s.sourceAlphaAddBlend.Get(); break;
    case LiveSm3Blend::premultiplied_alpha:
        liveBlend = s.premultipliedAlphaBlend.Get(); break;
    case LiveSm3Blend::unsupported:
        liveBlend = extendedBlend;
        if (!liveBlend) return false;
        break;
    }
    context->OMSetBlendState(liveBlend, nullptr, 0xffffffffu);
    const UINT offset = 0u;
    ID3D11Buffer* stream = s.fullGameVertexUpload.Get();
    context->IASetInputLayout(pipeline.inputLayout.Get());
    context->IASetVertexBuffers(0u, 1u, &stream, &nativeStride, &offset);
    context->IASetPrimitiveTopology(type == D3DPT_TRIANGLESTRIP ?
        D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP :
        D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    if (nativeIndices)
        context->IASetIndexBuffer(s.fullGameIndexUpload.Get(),
                                  DXGI_FORMAT_R32_UINT, 0u);
    else
        context->IASetIndexBuffer(nullptr, DXGI_FORMAT_UNKNOWN, 0u);
    context->VSSetShader(pipeline.program.vertexShader.Get(), nullptr, 0u);
    context->PSSetShader(pipeline.program.pixelShader.Get(), nullptr, 0u);
    context->PSSetShaderResources(0u, 16u, boundViews.data());
    context->PSSetSamplers(0u, 16u, boundSamplers.data());
    if (nativeIndices) context->DrawIndexed(nativeIndexCount, 0u, 0);
    else context->Draw(vertexCount, 0u);
    s.pending = true;
    ++s.issued;
    ++s.eligible;
    if (s.eligibleThisFrame != (std::numeric_limits<UINT>::max)())
        ++s.eligibleThisFrame;
    liveBatch.succeeded(liveDepth.enabled, reverseDepth);
    liveBatch.record_source_draw(sourceOrdinal);
    return true;
}

// Reuse geometric growth buffers for the thousands of game-owned VB/IB
// Draws in native full-frame mode. Uploads are submitted on the SAME
// immediate context, preserving each Draw's source content and ordering.
// Never retain a D3D9 COM reference or assume that game vertices are static.
bool ensure_full_game_upload_buffer(ID3D11Device* dev,
                                    ComPtr<ID3D11Buffer>& resource,
                                    UINT& capacity, UINT required,
                                    UINT bindFlags) noexcept {
    if (!dev || required == 0u ||
        (bindFlags != D3D11_BIND_VERTEX_BUFFER &&
         bindFlags != D3D11_BIND_INDEX_BUFFER)) return false;
    if (resource && capacity >= required) return true;
    UINT allocation = 256u;
    while (allocation < required) {
        if (allocation > (std::numeric_limits<UINT>::max)() / 2u)
            return false;
        allocation *= 2u;
    }
    D3D11_BUFFER_DESC desc{};
    desc.ByteWidth = allocation;
    desc.BindFlags = bindFlags;
    // WRITE_DISCARD renames GPU storage when a previous menu/race Draw still
    // references the old contents. DEFAULT/UpdateSubresource may require
    // hidden staging and an extra dependent copy for every source Draw.
    desc.Usage = D3D11_USAGE_DYNAMIC;
    desc.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
    ComPtr<ID3D11Buffer> candidate;
    if (FAILED(dev->CreateBuffer(&desc, nullptr, candidate.GetAddressOf())) ||
        !candidate) return false;
    resource = std::move(candidate);
    capacity = allocation;
    return true;
}

// Upload both real-game streams before IA binding. Map/Unmap is a transaction:
// failed mapping/copy leaves native publication aborted; original D3D9
// Draw/DrawIndexed and gamepad never depend on this optional path.
bool upload_full_game_stream(ID3D11DeviceContext* context,
                             ID3D11Buffer* buffer, UINT capacity,
                             const void* source, UINT bytes) noexcept {
    if (!context || !buffer || !source || bytes == 0u || bytes > capacity)
        return false;
    D3D11_MAPPED_SUBRESOURCE mapped{};
    if (FAILED(context->Map(buffer, 0u, D3D11_MAP_WRITE_DISCARD, 0u, &mapped)))
        return false;
    const bool copied = game_native_copy_dynamic_stream(
        mapped.pData, capacity, source, bytes);
    context->Unmap(buffer, 0u);
    return copied;
}

bool submit(State& s, const std::vector<NativeVertex>& vertices,
            const std::uint32_t* indices, UINT indexCount,
            D3DPRIMITIVETYPE topology, const TextureCapture& capture,
            const OutputCapture& output) noexcept {
    if (!ensure_pipeline(s, output.nativeWidth, output.nativeHeight)) return false;
    auto* dev = s.backend.device();
    auto* ctx = s.backend.context();
    if (!dev || !ctx) return false;
    ComPtr<ID3D11ShaderResourceView> sampledView;
    ComPtr<ID3D11SamplerState> sampledSampler;
    if (capture.enabled &&
        !mirror_texture(dev, capture, sampledView, sampledSampler)) return false;
    ComPtr<ID3D11ShaderResourceView> stage1View;
    ComPtr<ID3D11SamplerState> stage1Sampler;
    if (capture.stage1SeparateTexture) {
        TextureCapture second = capture;
        second.texture = capture.stage1SeparateTexture;
        if (capture.stage1IndependentSampler) {
            const auto& ss = capture.stage1SamplerStates;
            second.addressU = static_cast<D3DTEXTUREADDRESS>(ss[0]);
            second.addressV = static_cast<D3DTEXTUREADDRESS>(ss[1]);
            second.borderColor = ss[3];
            second.magFilter = static_cast<D3DTEXTUREFILTERTYPE>(ss[4]);
            second.minFilter = static_cast<D3DTEXTUREFILTERTYPE>(ss[5]);
            second.mipFilter = static_cast<D3DTEXTUREFILTERTYPE>(ss[6]);
            std::memcpy(&second.mipLodBias, &ss[7], sizeof(second.mipLodBias));
            second.maxMipLevel = ss[8];
            second.maxAnisotropy = ss[9];
            second.srgbTexture = ss[10] != FALSE;
        }
        // An independently addressed/sampled Stage1 may still reference the
        // exact Stage0 game texture. Reuse the already captured native SRV and
        // create only a distinct sampler; this avoids a second D3D9 LockRect/
        // GetRenderTargetData and D3D11 upload on each real game Draw.
        // Changed mip-chain or sRGB views require the full separate mirror.
        if (stage1_game_mirror_reusable(
                capture.texture.Get() == second.texture.Get(),
                capture.srgbTexture == second.srgbTexture,
                capture.mipFilter != D3DTEXF_NONE,
                second.mipFilter != D3DTEXF_NONE,
                sampledView.Get() != nullptr && sampledSampler.Get() != nullptr)) {
            const UINT sourceLevels = capture.texture->GetLevelCount();
            const UINT mirroredLevels =
                capture.mipFilter != D3DTEXF_NONE ? sourceLevels : 1u;
            if (!create_game_sampler(dev, second, mirroredLevels, stage1Sampler))
                return false;
            stage1View = sampledView;
        } else if (!mirror_texture(dev, second, stage1View, stage1Sampler))
            return false;
    }
    // Real game Stage-1 PS b1 is updated in original Draw order, using
    // the same device-owned GPU allocation through menu, car and race.
    // No immutable buffer allocation per game-authored Draw.
    if (capture.stage1Enabled) {
        Stage1Upload payload{};
        std::copy(capture.stage1Factor.begin(), capture.stage1Factor.end(),
                  payload.factor);
        std::copy(capture.stage1Constant.begin(), capture.stage1Constant.end(),
                  payload.stageConstant);
        payload.operations[0] = static_cast<std::int32_t>(capture.stage1ColorOp);
        payload.operations[1] = static_cast<std::int32_t>(capture.stage1AlphaOp);
        payload.operations[2] = capture.stage0ResultTemp ? 1 : 0; // shader CURRENT/TEMP route.
        payload.operations[3] = capture.stage1SeparateTexture ? 2 :
            (capture.stage1TextureOperands ? 1 : 0); // 2=second live game sample, 1=matched stage0.
        for (std::size_t i = 0; i < 4; ++i)
            payload.arguments[i] = static_cast<std::int32_t>(capture.stage1Args[i]);
        for (std::size_t i = 0; i < 2; ++i)
            payload.argZero[i] = static_cast<std::int32_t>(capture.stage1ArgZero[i]);
        // D3D11_USAGE_DEFAULT UpdateSubresource is ordered ahead of this
        // game's native Draw on the same immediate context. The driver
        // preserves in-flight draw state even when a later draw overwrites b1.
        if (!s.stage1Constants) return false;
        ctx->UpdateSubresource(s.stage1Constants.Get(), 0u, nullptr,
                               &payload, 0u, 0u);
    }
    ComPtr<ID3D11Buffer> vb, ib;
    if (env_full_game_opt_in()) {
        // Full-scene Draws normally share a pair of D3D11 GPU allocations;
        // only their *contents* change. Preserve VB/IB ownership across
        // complete menus, vehicle selection and racing, not an inset sample.
        const std::size_t vertexBytes = vertices.size() * sizeof(NativeVertex);
        if (vertexBytes == 0u ||
            vertexBytes > (std::numeric_limits<UINT>::max)()) return false;
        const UINT vertexSize = static_cast<UINT>(vertexBytes);
        if (!ensure_full_game_upload_buffer(dev, s.fullGameVertexUpload,
                                            s.fullGameVertexCapacity, vertexSize,
                                            D3D11_BIND_VERTEX_BUFFER)) return false;
        if (!upload_full_game_stream(ctx, s.fullGameVertexUpload.Get(),
                                     s.fullGameVertexCapacity,
                                     vertices.data(), vertexSize)) return false;
        vb = s.fullGameVertexUpload;
        if (indices && indexCount) {
            if (indexCount > (std::numeric_limits<UINT>::max)() / sizeof(std::uint32_t))
                return false;
            const UINT indexSize = indexCount * sizeof(std::uint32_t);
            if (!ensure_full_game_upload_buffer(dev, s.fullGameIndexUpload,
                                                s.fullGameIndexCapacity, indexSize,
                                                D3D11_BIND_INDEX_BUFFER)) return false;
            if (!upload_full_game_stream(ctx, s.fullGameIndexUpload.Get(),
                                         s.fullGameIndexCapacity,
                                         indices, indexSize)) return false;
            ib = s.fullGameIndexUpload;
        }
        if (FAILED(dev->GetDeviceRemovedReason())) return false;
    } else {
        // Preserve the original bounded diagnostic path byte-for-byte.
    D3D11_BUFFER_DESC bd{};
    bd.ByteWidth = static_cast<UINT>(vertices.size() * sizeof(NativeVertex));
    bd.BindFlags = D3D11_BIND_VERTEX_BUFFER;
    bd.Usage = D3D11_USAGE_IMMUTABLE;
    D3D11_SUBRESOURCE_DATA initial{};
    initial.pSysMem = vertices.data();
    if (FAILED(dev->CreateBuffer(&bd, &initial, vb.GetAddressOf()))) return false;
    if (indices && indexCount) {
        bd.ByteWidth = indexCount * sizeof(std::uint32_t);
        bd.BindFlags = D3D11_BIND_INDEX_BUFFER;
        initial.pSysMem = indices;
        if (FAILED(dev->CreateBuffer(&bd, &initial, ib.GetAddressOf()))) return false;
    }
    }

    // Pixel shader alpha test and OM alpha blend are bound to this same
    // source draw; unsupported D3D9 combinations were rejected above.
    const float alphaParams[4] = {
        output.alphaTest ? 1.0f : 0.0f,
        static_cast<float>(output.alphaRef),
        static_cast<float>(output.alphaFunc), capture.blendFactorAlphaValue
    };
    // D3D11 default OM state writes all channels. Even when blending is off,
    // a partial D3D9 COLORWRITEENABLE requires a real blend-state object.
    // Copy the validated alpha blend descriptor rather than approximating
    // its RGB/alpha factors in a second path.
    ComPtr<ID3D11BlendState>* maskedBlend = nullptr;
    ComPtr<ID3D11BlendState> independentAlphaBlend;
    if (output.separateAlphaBlend) {
        // Clone the admitted RGB descriptor; bind exact game alpha factors,
        // independent alpha equation and the original color-write mask on
        // this real game Draw/DrawIndexed. Opt-in diagnostics are bounded to
        // eight submissions per Present and never replace D3D9 rendering.
        ID3D11BlendState* rgbBase =
            output.additiveBlend ? s.additiveBlend.Get() :
            output.sourceAlphaAddBlend ? s.sourceAlphaAddBlend.Get() :
            output.premultipliedAlphaBlend ? s.premultipliedAlphaBlend.Get() :
            output.inverseSourceAlphaBlend ? s.inverseSourceAlphaBlend.Get() :
            output.sourceAlphaCopyBlend ? s.sourceAlphaCopyBlend.Get() :
            output.inverseAlphaCopyBlend ? s.inverseAlphaCopyBlend.Get() :
            output.inverseAlphaAddBlend ? s.inverseAlphaAddBlend.Get() :
            output.sourceReplaceBlend ? s.sourceReplaceBlend.Get() :
            output.multiplyBlend ? s.multiplyBlend.Get() :
            output.inverseDestMultiplyBlend ? s.inverseDestMultiplyBlend.Get() :
            output.inverseSourceMultiplyBlend ? s.inverseSourceMultiplyBlend.Get() :
            output.destAlphaCrossfadeBlend ? s.destAlphaCrossfadeBlend.Get() :
            output.reverseDestAlphaCrossfadeBlend ? s.reverseDestAlphaCrossfadeBlend.Get() :
            output.sourceAlphaSaturateCopyBlend ? s.sourceAlphaSaturateCopyBlend.Get() :
            output.sourceAlphaSaturateAddBlend ? s.sourceAlphaSaturateAddBlend.Get() :
            s.alphaBlend.Get();
        if (!rgbBase) return false;
        D3D11_BLEND_DESC desc{};
        rgbBase->GetDesc(&desc);
        desc.RenderTarget[0].BlendOp = output.blendOp;
        desc.RenderTarget[0].SrcBlendAlpha = output.nativeSrcAlpha;
        desc.RenderTarget[0].DestBlendAlpha = output.nativeDstAlpha;
        desc.RenderTarget[0].BlendOpAlpha = output.nativeAlphaOp;
        desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;
        if (FAILED(dev->CreateBlendState(&desc,
                                        independentAlphaBlend.GetAddressOf())))
            return false;
        maskedBlend = &independentAlphaBlend;
    } else if (output.blendOp == D3D11_BLEND_OP_MIN ||
               output.blendOp == D3D11_BLEND_OP_MAX) {
        // Both RGBA extrema are separate non-directional D3D11 OM states.
        // Keep the game-authored color-write mask and known-good alpha
        // factor family, without aliasing either subtractive cache.
        const UINT variant = output.additiveBlend ? 1u :
                             output.sourceAlphaAddBlend ? 2u :
                             output.premultipliedAlphaBlend ? 3u : 0u;
        const UINT slot = game_native_extremum_slot(
            output.blendOp == D3D11_BLEND_OP_MAX, variant,
            output.colorWriteMask);
        if (slot >= s.extremumMaskedBlends.size()) return false;
        auto& cached = s.extremumMaskedBlends[slot];
        if (!cached) {
            ID3D11BlendState* base = output.additiveBlend ? s.additiveBlend.Get() :
                output.sourceAlphaAddBlend ? s.sourceAlphaAddBlend.Get() :
                output.premultipliedAlphaBlend ? s.premultipliedAlphaBlend.Get() :
                s.alphaBlend.Get();
            if (!base) return false;
            D3D11_BLEND_DESC desc{};
            base->GetDesc(&desc);
            desc.RenderTarget[0].BlendOp = output.blendOp;
            desc.RenderTarget[0].BlendOpAlpha = output.blendOp;
            desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;
            if (FAILED(dev->CreateBlendState(&desc, cached.GetAddressOf())))
                return false; // Original D3D9 Draw/input remain authoritative.
        }
        maskedBlend = &cached;
    } else if (output.blendOp != D3D11_BLEND_OP_ADD) {
        // The native game draw uses the original captured factor pair and
        // requested direction. Copy proven ADD factors; change BOTH RGB and
        // alpha operations and preserve D3D9 COLORWRITEENABLE per draw.
        // Multiplicative pairs are rejected above until their two different
        // factor orders have independent subtractive states.
        const UINT variant = output.additiveBlend ? 1u :
                             output.sourceAlphaAddBlend ? 2u :
                             output.premultipliedAlphaBlend ? 3u : 0u;
        const UINT direction = output.blendOp == D3D11_BLEND_OP_REV_SUBTRACT ?
                               1u : 0u;
        const UINT slot = (direction * 4u + variant) * 16u +
                          output.colorWriteMask;
        if (slot >= s.subtractiveMaskedBlends.size()) return false;
        auto& cached = s.subtractiveMaskedBlends[slot];
        if (!cached) {
            ID3D11BlendState* base = output.additiveBlend ? s.additiveBlend.Get() :
                output.sourceAlphaAddBlend ? s.sourceAlphaAddBlend.Get() :
                output.premultipliedAlphaBlend ? s.premultipliedAlphaBlend.Get() :
                s.alphaBlend.Get();
            if (!base) return false;
            D3D11_BLEND_DESC desc{};
            base->GetDesc(&desc);
            desc.RenderTarget[0].BlendOp = output.blendOp;
            desc.RenderTarget[0].BlendOpAlpha = output.blendOp;
            desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;
            if (FAILED(dev->CreateBlendState(&desc, cached.GetAddressOf())))
                return false;
        }
        maskedBlend = &cached;
    } else if (output.inverseSourceAlphaBlend &&
               output.colorWriteMask != D3D11_COLOR_WRITE_ENABLE_ALL) {
        // Dedicated inverse-over mask slots prevent reuse of standard-over OM.
        auto& cached = s.inverseSourceAlphaMaskedBlends[output.colorWriteMask];
        if (!cached) {
            D3D11_BLEND_DESC desc{};
            s.inverseSourceAlphaBlend->GetDesc(&desc);
            desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;
            if (FAILED(dev->CreateBlendState(&desc, cached.GetAddressOf())))
                return false;
        }
        maskedBlend = &cached;
    } else if (output.multiplyBlend && output.colorWriteMask != D3D11_COLOR_WRITE_ENABLE_ALL) {
        // Multiplicative overlays must not reuse over/additive masked states.
        auto& cached = s.multiplyMaskedBlends[output.colorWriteMask];
        if (!cached) {
            D3D11_BLEND_DESC desc{};
            s.multiplyBlend->GetDesc(&desc);
            desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;
            if (FAILED(dev->CreateBlendState(&desc, cached.GetAddressOf())))
                return false;
        }
        maskedBlend = &cached;
    } else if (output.inverseDestMultiplyBlend &&
               output.colorWriteMask != D3D11_COLOR_WRITE_ENABLE_ALL) {
        auto& cached = s.inverseDestMultiplyMaskedBlends[output.colorWriteMask];
        if (!cached) {
            D3D11_BLEND_DESC desc{};
            s.inverseDestMultiplyBlend->GetDesc(&desc);
            desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;
            if (FAILED(dev->CreateBlendState(&desc, cached.GetAddressOf())))
                return false;
        }
        maskedBlend = &cached;
    } else if (output.inverseSourceMultiplyBlend &&
               output.colorWriteMask != D3D11_COLOR_WRITE_ENABLE_ALL) {
        auto& cached = s.inverseSourceMultiplyMaskedBlends[output.colorWriteMask];
        if (!cached) {
            D3D11_BLEND_DESC desc{};
            s.inverseSourceMultiplyBlend->GetDesc(&desc);
            desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;
            if (FAILED(dev->CreateBlendState(&desc, cached.GetAddressOf())))
                return false;
        }
        maskedBlend = &cached;
    } else if (output.sourceAlphaSaturateCopyBlend &&
               output.colorWriteMask != D3D11_COLOR_WRITE_ENABLE_ALL) {
        auto& cached = s.sourceAlphaSaturateCopyMaskedBlends[output.colorWriteMask];
        if (!cached) {
            D3D11_BLEND_DESC desc{};
            s.sourceAlphaSaturateCopyBlend->GetDesc(&desc);
            desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;
            if (FAILED(dev->CreateBlendState(&desc, cached.GetAddressOf()))) return false;
        }
        maskedBlend = &cached;
    } else if (output.sourceAlphaSaturateAddBlend &&
               output.colorWriteMask != D3D11_COLOR_WRITE_ENABLE_ALL) {
        auto& cached = s.sourceAlphaSaturateAddMaskedBlends[output.colorWriteMask];
        if (!cached) {
            D3D11_BLEND_DESC desc{};
            s.sourceAlphaSaturateAddBlend->GetDesc(&desc);
            desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;
            if (FAILED(dev->CreateBlendState(&desc, cached.GetAddressOf()))) return false;
        }
        maskedBlend = &cached;
    } else if (output.destAlphaCrossfadeBlend &&
               output.colorWriteMask != D3D11_COLOR_WRITE_ENABLE_ALL) {
        auto& cached = s.destAlphaCrossfadeMaskedBlends[output.colorWriteMask];
        if (!cached) {
            D3D11_BLEND_DESC desc{};
            s.destAlphaCrossfadeBlend->GetDesc(&desc);
            desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;
            if (FAILED(dev->CreateBlendState(&desc, cached.GetAddressOf()))) return false;
        }
        maskedBlend = &cached;
    } else if (output.reverseDestAlphaCrossfadeBlend &&
               output.colorWriteMask != D3D11_COLOR_WRITE_ENABLE_ALL) {
        auto& cached = s.reverseDestAlphaCrossfadeMaskedBlends[output.colorWriteMask];
        if (!cached) {
            D3D11_BLEND_DESC desc{};
            s.reverseDestAlphaCrossfadeBlend->GetDesc(&desc);
            desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;
            if (FAILED(dev->CreateBlendState(&desc, cached.GetAddressOf()))) return false;
        }
        maskedBlend = &cached;
    } else if (output.sourceAlphaCopyBlend &&
               output.colorWriteMask != D3D11_COLOR_WRITE_ENABLE_ALL) {
        // Preserve source-owned per-channel color writes for SRCALPHA/ZERO.
        // Never alias the standard-over, inverse-over or multiply caches.
        auto& cached = s.sourceAlphaCopyMaskedBlends[output.colorWriteMask];
        if (!cached) {
            D3D11_BLEND_DESC desc{};
            s.sourceAlphaCopyBlend->GetDesc(&desc);
            desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;
            if (FAILED(dev->CreateBlendState(&desc, cached.GetAddressOf())))
                return false;
        }
        maskedBlend = &cached;
    } else if (output.inverseAlphaCopyBlend &&
               output.colorWriteMask != D3D11_COLOR_WRITE_ENABLE_ALL) {
        auto& cached = s.inverseAlphaCopyMaskedBlends[output.colorWriteMask];
        if (!cached) {
            D3D11_BLEND_DESC desc{};
            s.inverseAlphaCopyBlend->GetDesc(&desc);
            desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;
            if (FAILED(dev->CreateBlendState(&desc, cached.GetAddressOf()))) return false;
        }
        maskedBlend = &cached;
    } else if (output.inverseAlphaAddBlend &&
               output.colorWriteMask != D3D11_COLOR_WRITE_ENABLE_ALL) {
        auto& cached = s.inverseAlphaAddMaskedBlends[output.colorWriteMask];
        if (!cached) {
            D3D11_BLEND_DESC desc{};
            s.inverseAlphaAddBlend->GetDesc(&desc);
            desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;
            if (FAILED(dev->CreateBlendState(&desc, cached.GetAddressOf()))) return false;
        }
        maskedBlend = &cached;
    } else if (output.sourceReplaceBlend &&
               output.colorWriteMask != D3D11_COLOR_WRITE_ENABLE_ALL) {
        // The original D3D9 draw overwrites only enabled channels. Keep the
        // other diagnostic target components untouched, including alpha.
        auto& cached = s.sourceReplaceMaskedBlends[output.colorWriteMask];
        if (!cached) {
            D3D11_BLEND_DESC desc{};
            s.sourceReplaceBlend->GetDesc(&desc);
            desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;
            if (FAILED(dev->CreateBlendState(&desc, cached.GetAddressOf())))
                return false;
        }
        maskedBlend = &cached;
    } else if (output.colorWriteMask != D3D11_COLOR_WRITE_ENABLE_ALL) {
        const UINT baseSlot = (output.alphaBlend ? 16u : 0u) + output.colorWriteMask;
        const UINT slot = baseSlot + (output.additiveBlend ? 16u :
                                     output.sourceAlphaAddBlend ? 32u : 0u) +
                                     (output.premultipliedAlphaBlend ? 48u : 0u);
        if (slot >= s.maskedBlends.size()) return false;
        auto& cached = s.maskedBlends[slot];
        if (!cached) {
            D3D11_BLEND_DESC maskDesc{};
            // Copy known-valid D3D11 blend factors even for opaque masks.
            // A zero-initialized BLEND_DESC has invalid factor/op enumerants
            // on devices that validate disabled-blend fields as well.
            s.alphaBlend->GetDesc(&maskDesc);
            maskDesc.RenderTarget[0].BlendEnable = output.alphaBlend ? TRUE : FALSE;
            // The D3D9 write mask never changes source/destination factors.
            if (output.premultipliedAlphaBlend) {
                maskDesc.RenderTarget[0].SrcBlend = D3D11_BLEND_ONE;
                maskDesc.RenderTarget[0].DestBlend = D3D11_BLEND_INV_SRC_ALPHA;
                maskDesc.RenderTarget[0].SrcBlendAlpha = D3D11_BLEND_ONE;
                maskDesc.RenderTarget[0].DestBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;
            // Never use standard over factors for masked additive draw calls.
            } else if (output.additiveBlend || output.sourceAlphaAddBlend) {
                maskDesc.RenderTarget[0].SrcBlend =
                    output.additiveBlend ? D3D11_BLEND_ONE : D3D11_BLEND_SRC_ALPHA;
                maskDesc.RenderTarget[0].DestBlend = D3D11_BLEND_ONE;
                maskDesc.RenderTarget[0].SrcBlendAlpha =
                    output.additiveBlend ? D3D11_BLEND_ONE : D3D11_BLEND_SRC_ALPHA;
                maskDesc.RenderTarget[0].DestBlendAlpha = D3D11_BLEND_ONE;
            }
            maskDesc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;
            if (FAILED(dev->CreateBlendState(&maskDesc, cached.GetAddressOf())))
                return false;
        }
        maskedBlend = &cached;
    }
    // Allocate an optional isolated D32 target for exact supported Z draws.
    // Existing no-depth menu/UI draws never depend on this attachment.
    if (output.nativeDepthTest) {
        if (!s.diagnosticDepthView) {
            D3D11_TEXTURE2D_DESC depthDesc{};
            depthDesc.Width = s.nativeWidth;
            depthDesc.Height = s.nativeHeight;
            depthDesc.MipLevels = 1;
            depthDesc.ArraySize = 1;
            depthDesc.Format = DXGI_FORMAT_D32_FLOAT;
            depthDesc.SampleDesc.Count = 1;
            depthDesc.Usage = D3D11_USAGE_DEFAULT;
            depthDesc.BindFlags = D3D11_BIND_DEPTH_STENCIL;
            ComPtr<ID3D11Texture2D> createdDepth;
            ComPtr<ID3D11DepthStencilView> createdView;
            if (FAILED(dev->CreateTexture2D(&depthDesc, nullptr,
                                            createdDepth.GetAddressOf())) ||
                FAILED(dev->CreateDepthStencilView(createdDepth.Get(), nullptr,
                                                  createdView.GetAddressOf())))
                return false;
            s.diagnosticDepth = std::move(createdDepth);
            s.diagnosticDepthView = std::move(createdView);
        }
        // D3D9 ALWAYS passes every fragment but may still write Z.
        // Never collapse that mode into a depth-disabled diagnostic draw.
        if (output.nativeDepthAlways) {
            auto& alwaysDepthState =
                s.diagnosticDepthAlwaysStates[output.nativeDepthWrite ? 1u : 0u];
            if (!alwaysDepthState) {
                D3D11_DEPTH_STENCIL_DESC ds{};
                ds.DepthEnable = TRUE;
                ds.DepthWriteMask = output.nativeDepthWrite ?
                    D3D11_DEPTH_WRITE_MASK_ALL : D3D11_DEPTH_WRITE_MASK_ZERO;
                ds.DepthFunc = D3D11_COMPARISON_ALWAYS;
                ds.StencilEnable = FALSE;
                if (FAILED(dev->CreateDepthStencilState(&ds,
                                                        alwaysDepthState.GetAddressOf())))
                    return false;
            }
        } else if (output.nativeDepthEqualityMode != 0u) {
            // Real D3D9 menu/vehicle/race compare, not a depth-disabled draw.
            auto& equalityDepthState = s.diagnosticDepthEqualityStates[
                game_native_depth_equality_slot(output.nativeDepthWrite,
                                                output.nativeDepthEqualityMode)];
            if (!equalityDepthState) {
                D3D11_DEPTH_STENCIL_DESC ds{};
                ds.DepthEnable = TRUE;
                ds.DepthWriteMask = output.nativeDepthWrite ?
                    D3D11_DEPTH_WRITE_MASK_ALL : D3D11_DEPTH_WRITE_MASK_ZERO;
                ds.DepthFunc = output.nativeDepthEqualityMode == D3DCMP_EQUAL ?
                    D3D11_COMPARISON_EQUAL : D3D11_COMPARISON_NOT_EQUAL;
                ds.StencilEnable = FALSE;
                if (FAILED(dev->CreateDepthStencilState(&ds,
                                                        equalityDepthState.GetAddressOf())))
                    return false;
            }
        } else if (output.nativeDepthOrderingMode != 0u) {
            // One isolated game-authored Z comparison, not scene-depth parity.
            auto& orderingDepthState = s.diagnosticDepthOrderingStates[
                game_native_depth_ordering_slot(output.nativeDepthWrite,
                                                output.nativeDepthOrderingMode)];
            if (!orderingDepthState) {
                D3D11_DEPTH_STENCIL_DESC ds{};
                ds.DepthEnable = TRUE;
                ds.DepthWriteMask = output.nativeDepthWrite ?
                    D3D11_DEPTH_WRITE_MASK_ALL : D3D11_DEPTH_WRITE_MASK_ZERO;
                ds.DepthFunc = output.nativeDepthOrderingMode == D3DCMP_GREATER ?
                    D3D11_COMPARISON_GREATER : D3D11_COMPARISON_GREATER_EQUAL;
                ds.StencilEnable = FALSE;
                if (FAILED(dev->CreateDepthStencilState(&ds,
                                                        orderingDepthState.GetAddressOf())))
                    return false;
            }
        } else {
        auto& depthState =
            s.diagnosticDepthStates[game_native_depth_slot(
                output.nativeDepthWrite, output.nativeDepthLessEqual)];
        if (!depthState) {
            D3D11_DEPTH_STENCIL_DESC ds{};
            ds.DepthEnable = TRUE;
            ds.DepthWriteMask = output.nativeDepthWrite ?
                D3D11_DEPTH_WRITE_MASK_ALL : D3D11_DEPTH_WRITE_MASK_ZERO;
            ds.DepthFunc = output.nativeDepthLessEqual ?
                D3D11_COMPARISON_LESS_EQUAL : D3D11_COMPARISON_LESS;
            ds.StencilEnable = FALSE;
            if (FAILED(dev->CreateDepthStencilState(&ds,
                                                    depthState.GetAddressOf())))
                return false;
        }
        }
    }
    ctx->UpdateSubresource(s.alphaConstants.Get(), 0, nullptr, alphaParams, 0, 0);
    // The first real game Draw consumes a whole Clear and any intervening
    // game-authored partial ColorFills in their original order. Do not issue
    // native commands if the remembered fills cannot be replayed atomically.
    if (s.frameBatch.first_draw()) {
        ComPtr<ID3D11DeviceContext1> replayContext;
        if (s.preDrawFills.count != 0u &&
            (!env_full_game_opt_in() ||
             !s.clearColor.matches(s.sourceGameDevice, output.targetIdentity) ||
             !s.preDrawFills.belongs_to(s.sourceGameDevice, output.targetIdentity) ||
             !s.backend.color_rtv() ||
             FAILED(ctx->QueryInterface(IID_PPV_ARGS(replayContext.GetAddressOf()))) ||
             !replayContext)) {
            s.preDrawFills.discard();
            return false; // original D3D9 Draw/Present/input remain authoritative
        }
        s.backend.begin_frame(env_full_game_opt_in()
            ? s.clearColor.native_color(s.sourceGameDevice, output.targetIdentity, kBackground)
            : kBackground);
        if (replayContext) {
            constexpr float scale = 1.0f / 255.0f;
            for (std::uint32_t i = 0; i < s.preDrawFills.count; ++i) {
                const auto& fill = s.preDrawFills.entries[i];
                const float rgba[4]{
                    float((fill.argb >> 16) & 255u) * scale,
                    float((fill.argb >> 8) & 255u) * scale,
                    float(fill.argb & 255u) * scale,
                    s.clearColor.opaqueDestinationAlpha ? 1.0f :
                        float((fill.argb >> 24) & 255u) * scale};
                const D3D11_RECT area{
                    static_cast<LONG>(fill.left), static_cast<LONG>(fill.top),
                    static_cast<LONG>(fill.right), static_cast<LONG>(fill.bottom)};
                replayContext->ClearView(s.backend.color_rtv(), rgba, &area, 1u);
            }
        }
        s.preDrawFills.discard();
    }
    if (output.nativeDepthTest) {
        ID3D11RenderTargetView* rtv = s.backend.color_rtv();
        ctx->OMSetRenderTargets(1, &rtv, s.diagnosticDepthView.Get());
        // Independent diagnostic depth cannot reuse earlier D3D9 history.
        // Reversed ordering needs a zero baseline to show positive fragments.
        // Mirror first game Z and later verified Z-only Clears before next depth Draw.
        if (s.frameBatch.clear_depth()) {
            ctx->ClearDepthStencilView(s.diagnosticDepthView.Get(), D3D11_CLEAR_DEPTH,
                s.frameBatch.depth_clear_value(output.nativeDepthOrderingMode != 0u), 0);
            s.frameBatch.consume_depth_clear();
        }
        if (output.nativeDepthAlways)
            ctx->OMSetDepthStencilState(
                s.diagnosticDepthAlwaysStates[output.nativeDepthWrite ? 1u : 0u].Get(), 0);
        else if (output.nativeDepthEqualityMode != 0u)
            ctx->OMSetDepthStencilState(
                s.diagnosticDepthEqualityStates[game_native_depth_equality_slot(
                    output.nativeDepthWrite, output.nativeDepthEqualityMode)].Get(), 0);
        else if (output.nativeDepthOrderingMode != 0u)
            ctx->OMSetDepthStencilState(
                s.diagnosticDepthOrderingStates[game_native_depth_ordering_slot(
                    output.nativeDepthWrite, output.nativeDepthOrderingMode)].Get(), 0);
        else
        ctx->OMSetDepthStencilState(
            s.diagnosticDepthStates[game_native_depth_slot(
                output.nativeDepthWrite, output.nativeDepthLessEqual)].Get(), 0);
    } else {
        // Immediate-context state survives across draws; do not depth-test
        // later menu/vehicle/HUD draws using the previous race state.
        ctx->OMSetDepthStencilState(nullptr, 0);
    }
    if (maskedBlend)
        ctx->OMSetBlendState(maskedBlend->Get(), nullptr, 0xffffffffu);
    else if (output.additiveBlend)
        ctx->OMSetBlendState(s.additiveBlend.Get(), nullptr, 0xffffffffu);
    else if (output.sourceAlphaAddBlend)
        ctx->OMSetBlendState(s.sourceAlphaAddBlend.Get(), nullptr, 0xffffffffu);
    else if (output.premultipliedAlphaBlend)
        ctx->OMSetBlendState(s.premultipliedAlphaBlend.Get(), nullptr, 0xffffffffu);
    else if (output.inverseSourceAlphaBlend)
        ctx->OMSetBlendState(s.inverseSourceAlphaBlend.Get(), nullptr, 0xffffffffu);
    else if (output.multiplyBlend)
        ctx->OMSetBlendState(s.multiplyBlend.Get(), nullptr, 0xffffffffu);
    else if (output.inverseDestMultiplyBlend)
        ctx->OMSetBlendState(s.inverseDestMultiplyBlend.Get(), nullptr, 0xffffffffu);
    else if (output.inverseSourceMultiplyBlend)
        ctx->OMSetBlendState(s.inverseSourceMultiplyBlend.Get(), nullptr, 0xffffffffu);
    else if (output.sourceAlphaSaturateCopyBlend)
        ctx->OMSetBlendState(s.sourceAlphaSaturateCopyBlend.Get(), nullptr, 0xffffffffu);
    else if (output.sourceAlphaSaturateAddBlend)
        ctx->OMSetBlendState(s.sourceAlphaSaturateAddBlend.Get(), nullptr, 0xffffffffu);
    else if (output.destAlphaCrossfadeBlend)
        ctx->OMSetBlendState(s.destAlphaCrossfadeBlend.Get(), nullptr, 0xffffffffu);
    else if (output.reverseDestAlphaCrossfadeBlend)
        ctx->OMSetBlendState(s.reverseDestAlphaCrossfadeBlend.Get(), nullptr, 0xffffffffu);
    else if (output.sourceAlphaCopyBlend)
        ctx->OMSetBlendState(s.sourceAlphaCopyBlend.Get(), nullptr, 0xffffffffu);
    else if (output.inverseAlphaCopyBlend)
        ctx->OMSetBlendState(s.inverseAlphaCopyBlend.Get(), nullptr, 0xffffffffu);
    else if (output.inverseAlphaAddBlend)
        ctx->OMSetBlendState(s.inverseAlphaAddBlend.Get(), nullptr, 0xffffffffu);
    else if (output.sourceReplaceBlend)
        ctx->OMSetBlendState(s.sourceReplaceBlend.Get(), nullptr, 0xffffffffu);
    else
        ctx->OMSetBlendState(output.alphaBlend ? s.alphaBlend.Get() : nullptr, nullptr, 0xffffffffu);
    ID3D11Buffer* alphaBuffer = s.alphaConstants.Get();
    ctx->PSSetConstantBuffers(0, 1, &alphaBuffer);
    // Explicitly clear b1 for a following stage-0-only menu/HUD Draw.
    // Never let a previous stage-1 combiner leak into a new game draw.
    ID3D11Buffer* combiner = capture.stage1Enabled ? s.stage1Constants.Get() : nullptr;
    ctx->PSSetConstantBuffers(1, 1, &combiner);
    // Both source modes must bind the exact buffers populated above. In
    // particular, the bounded D3D9 diagnostic fallback must not shadow these
    // owners with short-lived local ComPtrs and submit with a null IA vertex
    // stream. A failed native binding never changes the original D3D9 Draw.
    if (!vb || (indices && indexCount && !ib)) return false;
    const UINT stride = sizeof(NativeVertex), offset = 0;
    ID3D11Buffer* boundVB = vb.Get();
    ctx->IASetInputLayout(s.layout.Get());
    ctx->IASetPrimitiveTopology(topology == D3DPT_POINTLIST ?
        D3D11_PRIMITIVE_TOPOLOGY_POINTLIST :
        topology == D3DPT_LINELIST ?
        D3D11_PRIMITIVE_TOPOLOGY_LINELIST :
        topology == D3DPT_LINESTRIP ?
        D3D11_PRIMITIVE_TOPOLOGY_LINESTRIP :
        topology == D3DPT_TRIANGLESTRIP ?
        D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP :
        D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    ctx->IASetVertexBuffers(0, 1, &boundVB, &stride, &offset);
    if (ib) ctx->IASetIndexBuffer(ib.Get(), DXGI_FORMAT_R32_UINT, 0);
    const D3D11_RECT fullScissor{0, 0, static_cast<LONG>(s.nativeWidth),
                                  static_cast<LONG>(s.nativeHeight)};
    // NativeBackend::begin_frame installs a full-inset viewport. Restore
    // the captured game viewport for EACH draw, including indexed draws,
    // so the diagnostic frame keeps original menu/race layout coordinates.
    ctx->RSSetViewports(1, &output.nativeViewport);
    const D3D11_RECT& rect = output.scissor ? output.nativeScissor : fullScissor;
    ctx->RSSetScissorRects(1, &rect);
    // The R30 game Draw always survives. The native diagnostic mirrors its
    // current face exclusion and chooses the matching scissor variant.
    ID3D11RasterizerState* nativeRaster =
        output.nativeCullMode == D3DCULL_CW
            ? s.diagnosticCullRasters[output.scissor ? 2u : 0u].Get()
            : output.nativeCullMode == D3DCULL_CCW
                ? s.diagnosticCullRasters[output.scissor ? 3u : 1u].Get()
                : (output.scissor ? s.scissorRaster.Get() : s.raster.Get());
    ctx->RSSetState(nativeRaster);
    ctx->VSSetShader(s.vs.Get(), nullptr, 0);
    ctx->PSSetShader(capture.stage1Enabled ?
                       (!capture.enabled ? s.stage1DiffusePs.Get() :
                        capture.selectTexture ? s.stage1TextureOnlyPs.Get() :
                        capture.additive ? s.stage1AddPs.Get() :
                        s.stage1ModulatePs.Get()) :
                       capture.selectDiffuseTextureAlpha ? s.selectDiffuseTextureAlphaPs.Get() :
                      capture.selectDiffuseTfactorArg2Alpha ? s.selectDiffuseTfactorAlphaPs.Get() :
                      capture.selectDiffuseDiffuseAlpha ? s.ps.Get() :
                      capture.selectDiffuseModulateAlpha ? s.selectDiffuseModulateAlphaPs.Get() :
                      capture.selectDiffuseAddAlpha ? s.selectDiffuseAddAlphaPs.Get() :
                      capture.selectDiffuseSubtractAlpha ? s.selectDiffuseSubtractAlphaPs.Get() :
                      capture.selectDiffuseModulate2XAlpha ? s.selectDiffuseModulate2XAlphaPs.Get() :
                      capture.selectDiffuseModulate4XAlpha ? s.selectDiffuseModulate4XAlphaPs.Get() :
                       capture.selectDiffuseAddSmoothAlpha ? s.selectDiffuseAddSmoothAlphaPs.Get() :
                        capture.selectDiffuseTfactorAlpha ? s.selectDiffuseTfactorAlphaPs.Get() :
                         capture.selectDiffuseFactorAlpha ? s.selectDiffuseFactorAlphaPs.Get() :
                        capture.selectDiffuseBlendTextureAlpha ? s.selectDiffuseBlendTextureAlphaPs.Get() :
                       capture.selectTextureTfactorArg2Alpha ? s.selectTextureTfactorAlphaPs.Get() :
                      capture.selectTextureDiffuseAlpha ? s.selectTextureDiffuseAlphaPs.Get() :
                       capture.selectTextureModulateAlpha ? s.selectTextureModulateAlphaPs.Get() :
                        capture.selectTextureModulate2XAlpha ? s.selectTextureModulate2XAlphaPs.Get() :
                        capture.selectTextureModulate4XAlpha ? s.selectTextureModulate4XAlphaPs.Get() :
                       capture.selectTextureAddAlpha ? s.selectTextureAddAlphaPs.Get() :
                       capture.selectTextureSubtractAlpha ? s.selectTextureSubtractAlphaPs.Get() :
                        capture.selectTextureAddSmoothAlpha ? s.selectTextureAddSmoothAlphaPs.Get() :
                        capture.selectTextureTfactorAlpha ? s.selectTextureTfactorAlphaPs.Get() :
                         capture.selectTextureFactorAlpha ? s.selectTextureFactorAlphaPs.Get() :
                        capture.selectTextureBlendTextureAlpha ? s.selectTextureBlendTextureAlphaPs.Get() :
                         capture.selectTextureBlendDiffuseAlpha ? s.selectTextureBlendDiffuseAlphaPs.Get() :
                         capture.selectDiffuseBlendDiffuseAlpha ? s.selectDiffuseBlendDiffuseAlphaPs.Get() :
                      capture.blendTextureAlpha ? s.blendTextureAlphaPs.Get() :
                      capture.blendTextureAlphaPM ? s.blendTextureAlphaPmPs.Get() :
                      capture.blendTextureAlphaPMTextureAlpha ? s.blendTextureAlphaPmTextureAlphaPs.Get() :
                      capture.blendTextureAlphaPMInverseTextureAlpha ? s.blendTextureAlphaPmInverseTextureAlphaPs.Get() :
                       capture.blendTextureAlphaPMInverseDiffuseAlpha ? s.blendTextureAlphaPmInverseDiffuseAlphaPs.Get() :
                      capture.blendTextureAlphaPMDiffuseAlpha ? s.blendTextureAlphaPmDiffuseAlphaPs.Get() :
                      capture.blendTextureAlphaPMFactorAlpha ? s.blendTextureAlphaPmFactorAlphaPs.Get() :
                       capture.blendTextureAlphaPMAddFactorAlpha ? s.blendTextureAlphaPmAddFactorAlphaPs.Get() :
                       capture.blendTextureAlphaPMAddSmoothFactorAlpha ? s.blendTextureAlphaPmAddSmoothFactorAlphaPs.Get() :
                       capture.blendTextureAlphaPMSigned2XFactorAlpha ? s.blendTextureAlphaPmSigned2XFactorAlphaPs.Get() :
                       capture.blendTextureAlphaPMSignedFactorAlpha ? s.blendTextureAlphaPmSignedFactorAlphaPs.Get() :
                       capture.blendTextureAlphaPMModulateFactorAlpha ? s.blendTextureAlphaPmModulateFactorAlphaPs.Get() :
                       capture.blendTextureAlphaPMModulateAlpha ? s.blendTextureAlphaPmModulateAlphaPs.Get() :
                        capture.blendTextureAlphaPMAddAlpha ? s.blendTextureAlphaPmAddAlphaPs.Get() :
                       capture.blendTextureAlphaPMSubtractAlpha ? s.blendTextureAlphaPmSubtractAlphaPs.Get() :
                       capture.blendTextureAlphaPMModulate2XAlpha ? s.blendTextureAlphaPmModulate2XAlphaPs.Get() :
                        capture.blendTextureAlphaPMModulate4XAlpha ? s.blendTextureAlphaPmModulate4XAlphaPs.Get() :
                        capture.blendTextureAlphaPMAddSignedAlpha ? s.blendTextureAlphaPmAddSignedAlphaPs.Get() :
                        capture.blendTextureAlphaPMAddSigned2XAlpha ? s.blendTextureAlphaPmAddSigned2XAlphaPs.Get() :
                         capture.blendTextureAlphaPMBlendTextureAlpha ? s.blendTextureAlphaPmBlendTextureAlphaPs.Get() :
                          capture.blendTextureAlphaPMBlendDiffuseAlpha ? s.blendTextureAlphaPmBlendDiffuseAlphaPs.Get() :
                          capture.blendTextureAlphaPMBlendCurrentFactorAlpha ? s.blendTextureAlphaPmBlendCurrentFactorAlphaPs.Get() :
                           capture.blendTextureAlphaPMBlendFactorAlpha ? s.blendTextureAlphaPmBlendFactorAlphaPs.Get() :
                       capture.blendTextureAlphaPMAddSmoothAlpha ? s.blendTextureAlphaPmAddSmoothAlphaPs.Get() :
                     capture.blendDiffuseAlpha ? s.blendDiffuseAlphaPs.Get() :
                     capture.blendTextureSelectedTextureAlpha ? s.blendTextureSelectedTextureAlphaPs.Get() :
                     capture.blendTextureSelectedDiffuseAlpha ? s.blendTextureSelectedDiffuseAlphaPs.Get() :
                     capture.blendDiffuseSelectedTextureAlpha ? s.blendDiffuseSelectedTextureAlphaPs.Get() :
                     capture.blendDiffuseSelectedDiffuseAlpha ? s.blendDiffuseSelectedDiffuseAlphaPs.Get() :
                     capture.blendTextureModulateAlpha ? s.blendTextureModulateAlphaPs.Get() :
                     capture.blendDiffuseModulateAlpha ? s.blendDiffuseModulateAlphaPs.Get() :
        capture.blendTextureModulate2XAlpha ? s.blendTextureModulate2XAlphaPs.Get() :
         capture.blendTextureModulate4XAlpha ? s.blendTextureModulate4XAlphaPs.Get() :
         capture.blendDiffuseModulate2XAlpha ? s.blendDiffuseModulate2XAlphaPs.Get() :
         capture.blendDiffuseModulate4XAlpha ? s.blendDiffuseModulate4XAlphaPs.Get() :
         capture.blendTextureAddAlpha ? s.blendTextureAddAlphaPs.Get() :
        capture.blendDiffuseAddAlpha ? s.blendDiffuseAddAlphaPs.Get() :
        capture.blendTextureSubtractAlpha ? s.blendTextureSubtractAlphaPs.Get() :
        capture.blendDiffuseSubtractAlpha ? s.blendDiffuseSubtractAlphaPs.Get() :
         capture.blendTextureAddSmoothAlpha ? s.blendTextureAddSmoothAlphaPs.Get() :
         capture.blendDiffuseAddSmoothAlpha ? s.blendDiffuseAddSmoothAlphaPs.Get() :
                     capture.blendFactorAlpha ? s.blendFactorAlphaPs.Get() :
                     capture.blendFactorTextureAlpha ? s.blendFactorTextureAlphaPs.Get() :
                     capture.blendFactorModulateAlpha ? s.blendFactorModulateAlphaPs.Get() :
                     capture.blendFactorDiffuseAlpha ? s.blendFactorDiffuseAlphaPs.Get() :
                     capture.blendFactorAddAlpha ? s.blendFactorAddAlphaPs.Get() :
                     capture.blendFactorSubtractAlpha ? s.blendFactorSubtractAlphaPs.Get() :
                     capture.blendFactorAddSmoothAlpha ? s.blendFactorAddSmoothAlphaPs.Get() :
                     capture.blendFactorModulate2XAlpha ? s.blendFactorModulate2XAlphaPs.Get() :
                     capture.blendFactorModulate4XAlpha ? s.blendFactorModulate4XAlphaPs.Get() :
                      capture.subtractTextureAlpha ? s.subtractTextureAlphaPs.Get() :
                      capture.subtractDiffuseAlpha ? s.subtractDiffuseAlphaPs.Get() :
                       capture.subtractModulateAlpha ? s.subtractModulateAlphaPs.Get() :
                      capture.modulate2xTextureAlpha ? s.modulate2xTextureAlphaPs.Get() :
                      capture.modulate2xDiffuseAlpha ? s.modulate2xDiffuseAlphaPs.Get() :
                      capture.modulate4xTextureAlpha ? s.modulate4xTextureAlphaPs.Get() :
                      capture.modulate4xDiffuseAlpha ? s.modulate4xDiffuseAlphaPs.Get() :
                     !capture.enabled ? s.ps.Get() :
                     (capture.addSmoothTextureAlpha ? s.addSmoothTextureAlphaPs.Get() :
                     (capture.addSmoothDiffuseAlpha ? s.addSmoothDiffuseAlphaPs.Get() :
                     (capture.addSmooth ? s.addSmoothPs.Get() :
                     (capture.subtract ? s.subtractPs.Get() :
                     (capture.modulate2x ? s.modulate2xPs.Get() :
                     (capture.modulate4x ? s.modulate4xPs.Get() :
                     (capture.mixedTextureAlpha ? s.mixedTextureAlphaPs.Get() :
                     (capture.mixedDiffuseAlpha ? s.mixedDiffuseAlphaPs.Get() :
                     (capture.mixedAddTextureAlpha ? s.mixedAddTextureAlphaPs.Get() :
                     (capture.mixedAddDiffuseAlpha ? s.mixedAddDiffuseAlphaPs.Get() :
                     (capture.selectTexture ? s.textureOnlyPs.Get() :
                      capture.additive ? s.additivePs.Get() : s.sampledPs.Get()))))))))))), nullptr, 0);
    ID3D11ShaderResourceView* boundView = sampledView.Get();
    ID3D11SamplerState* boundSampler = sampledSampler.Get();
    ctx->PSSetShaderResources(0, 1, &boundView);
    ctx->PSSetSamplers(0, 1, &boundSampler);
    ID3D11ShaderResourceView* boundStage1View = stage1View.Get();
    ID3D11SamplerState* boundStage1Sampler = stage1Sampler.Get();
    ctx->PSSetShaderResources(1, 1, &boundStage1View);
    ctx->PSSetSamplers(1, 1, &boundStage1Sampler);
    if (ib) ctx->DrawIndexed(indexCount, 0, 0);
    else ctx->Draw(static_cast<UINT>(vertices.size()), 0);
    // GPU submission is paired with the queued readback at Present.
    s.pending = true;
    ++s.issued;
    return true;
}

bool observe_source_device(State& s, IDirect3DDevice9* game) noexcept {
    const auto current = reinterpret_cast<std::uintptr_t>(game);
    const auto lastPresentDevice = s.previousOutput.valid()
        ? s.previousOutput.device : 0u;
    if (!GameNativeFrameBatch::admits_game_source(
            current, s.sourceGameDevice, lastPresentDevice)) {
        // Exclude an early auxiliary/menu device Draw without advancing
        // the real game's source ordinal or aborting its existing batch.
        // The original D3D9 Draw and gamepad input are unaffected.
        return false;
    }
    if (s.sourceGameDevice == 0u) s.sourceGameDevice = current;
    return true;
}

// A native full-size Draw and a diagnostic inset Draw cannot describe the
// same source frame. Mode flips are fail-closed until a new full TARGET Clear
// or Present, preserving every original D3D9 Draw and controller event.
bool observe_source_frame_mode(State& s, bool fullMode) noexcept {
    if (!s.sourceModeKnown) {
        s.sourceModeKnown = true;
        s.sourceWasFullMode = fullMode;
        return true;
    }
    if (s.sourceWasFullMode == fullMode) return true;
    s.frameBatch.abort();
    s.pending = false;
    return false;
}

// An offscreen D3D9 Draw must not be counted as a native backbuffer Draw.
// Check the current COM backbuffer identity, Z/stencil and all extra MRTs;
// a failed query, shared main RT or depth/stencil write aborts the native batch.
// Defined beside the full-frame no-write source observer below. Shared by
// native offscreen camera isolation and main RT0 no-output game Draws.
bool game_stencil_is_read_only(IDirect3DDevice9* game, DWORD enabled,
                               bool maskKnown, DWORD writeMask) noexcept;

bool isolated_offscreen_game_draw(IDirect3DDevice9* game, State& s) noexcept {
    if (!env_full_game_opt_in() || !game || s.frameBatch.stopped) return false;
    const auto owner = reinterpret_cast<std::uintptr_t>(game);
    DWORD zEnabled = D3DZB_TRUE, zWriteEnabled = TRUE, stencilEnabled = TRUE;
    if (FAILED(game->GetRenderState(D3DRS_ZENABLE, &zEnabled)) ||
        FAILED(game->GetRenderState(D3DRS_ZWRITEENABLE, &zWriteEnabled)) ||
        FAILED(game->GetRenderState(D3DRS_STENCILENABLE, &stencilEnabled)))
        return false;
    // Preserve game render-to-texture stencil TESTS with zero writable bits,
    // not just STENCILENABLE=FALSE. Unknown readback or a nonzero mask
    // still invalidates the optional native full-frame stream.
    DWORD stencilWriteMask = 0xffffffffu;
    const bool stencilMaskKnown = stencilEnabled == FALSE ||
        SUCCEEDED(game->GetRenderState(D3DRS_STENCILWRITEMASK, &stencilWriteMask));
    if (!stencilMaskKnown) return false;
    ComPtr<IDirect3DSurface9> target, backbuffer;
    ComPtr<IUnknown> targetIdentity, backbufferIdentity;
    if (FAILED(game->GetRenderTarget(0, target.GetAddressOf())) || !target ||
        FAILED(game->GetBackBuffer(0, 0, D3DBACKBUFFER_TYPE_MONO,
                                  backbuffer.GetAddressOf())) || !backbuffer ||
        FAILED(target.As(&targetIdentity)) ||
        FAILED(backbuffer.As(&backbufferIdentity)) ||
        !targetIdentity || !backbufferIdentity) return false;
    // Query only MRT slots the actual D3D9 adapter exposes. Asking for
    // nonexistent slots returns INVALIDCALL on one/two-target hardware,
    // previously aborting otherwise isolated menu and vehicle passes.
    // Unknown or out-of-range caps still fail closed before native admission.
    D3DCAPS9 caps{};
    if (FAILED(game->GetDeviceCaps(&caps)) ||
        !GameNativeOffscreenPass::valid_mrt_count(caps.NumSimultaneousRTs))
        return false;
    // Some real menu/vehicle previews leave extra MRT slots bound with every
    // channel disabled. Such Draw/DrawIndexed calls cannot write those RTs,
    // even when an extra slot aliases the seeded main backbuffer. Validate
    // the exact per-slot game write mask; an unknown binding/mask fails closed.
    // Offscreen Clears remain stricter because Clear ignores color masks.
    constexpr D3DRENDERSTATETYPE extraColorMasks[] = {
        D3DRS_COLORWRITEENABLE1, D3DRS_COLORWRITEENABLE2,
        D3DRS_COLORWRITEENABLE3
    };
    bool noExtraRenderTargets = true;
    for (DWORD i = 1u; i < caps.NumSimultaneousRTs; ++i) {
        ComPtr<IDirect3DSurface9> extra;
        const HRESULT hr = game->GetRenderTarget(i, extra.GetAddressOf());
        if (hr == D3DERR_NOTFOUND) continue;
        DWORD mask = 0xffffffffu;
        const bool maskKnown = SUCCEEDED(hr) && extra &&
            SUCCEEDED(game->GetRenderState(extraColorMasks[i - 1u], &mask));
        if (!GameNativeOffscreenPass::inactive_extra_mrt(maskKnown, mask)) {
            // A live, writable MRT can be part of the game's own auxiliary
            // menu/vehicle texture pass. Preserve main-frame source ordinals
            // only after proving that THIS surface cannot alias main RT0.
            ComPtr<IUnknown> extraIdentity;
            const bool distinctExtra = SUCCEEDED(hr) && extra &&
                SUCCEEDED(extra.As(&extraIdentity)) && extraIdentity &&
                GameNativeOffscreenPass::distinct_auxiliary_mrt(
                    reinterpret_cast<std::uintptr_t>(extraIdentity.Get()),
                    reinterpret_cast<std::uintptr_t>(backbufferIdentity.Get()));
            if (!distinctExtra) {
                noExtraRenderTargets = false;
                break;
            }
        }
    }
    // A real game menu/vehicle render-to-texture Draw can write its OWN Z
    // surface without changing the seeded main game's depth history. Prove
    // both COM identities before absorbing the original source ordinal:
    // matching/unknown main Z must still abort native full-frame output.
    const bool depthWrites = zEnabled != D3DZB_FALSE && zWriteEnabled != FALSE;
    const bool stencilReadOnly = game_stencil_is_read_only(
        game, stencilEnabled, stencilMaskKnown, stencilWriteMask);
    const bool stencilWrites = stencilEnabled != FALSE && !stencilReadOnly;
    bool isolatedDepthWrite = false;
    if ((depthWrites && s.clearColor.mainDepthIdentity != 0u) ||
        (stencilWrites && s.clearColor.mainDepthIdentity != 0u)) {
        ComPtr<IDirect3DSurface9> boundDepth;
        ComPtr<IUnknown> depthIdentity;
        if (SUCCEEDED(game->GetDepthStencilSurface(boundDepth.GetAddressOf())) &&
            boundDepth && SUCCEEDED(boundDepth.As(&depthIdentity)) && depthIdentity)
            isolatedDepthWrite = !s.clearColor.main_depth_still_bound(
                reinterpret_cast<std::uintptr_t>(depthIdentity.Get()));
    }
    const bool isolated = GameNativeOffscreenPass::source_has_no_main_writes(
        true, s.clearColor.matches(owner, reinterpret_cast<std::uintptr_t>(
            backbufferIdentity.Get())),
        targetIdentity.Get() != backbufferIdentity.Get(),
        GameNativeOffscreenPass::no_main_depth_write(
            zEnabled != D3DZB_FALSE, zWriteEnabled != FALSE, isolatedDepthWrite),
        (stencilReadOnly ||
         GameNativeOffscreenPass::isolated_auxiliary_stencil_write(
             stencilEnabled != FALSE, stencilMaskKnown, stencilWriteMask,
             isolatedDepthWrite)),
        noExtraRenderTargets, s.frameBatch.stopped);
    // The original D3D9 Draw has now changed the auxiliary Z surface. A
    // subsequent backbuffer depth Draw must rebind the seeded MAIN depth
    // identity, not reuse the auxiliary depth history as the native DSV.
    if (isolated && depthWrites && isolatedDepthWrite)
        s.clearColor.note_auxiliary_depth_write();
    if (isolated && stencilWrites && isolatedDepthWrite)
        s.clearColor.note_auxiliary_depth_write();
    return isolated;
}

// Read a real D3D9 stencil state, not a guessed draw-side flag. A nonzero
// write mask with all front/CCW KEEP operations is still a pure stencil TEST.
// This allows menu/vehicle/race no-output Draw ordinals to remain contiguous
// without submitting an artificial D3D11 Draw or mutating the main Z/S.
bool game_stencil_is_read_only(IDirect3DDevice9* game,
                               DWORD enabled, bool maskKnown,
                               DWORD writeMask) noexcept {
    if (enabled == FALSE) return true;
    if (!game || !maskKnown) return false;
    if (writeMask == 0u) return true;
    DWORD frontFail = 0u, frontZFail = 0u, frontPass = 0u;
    DWORD twoSided = TRUE;
    if (FAILED(game->GetRenderState(D3DRS_STENCILFAIL, &frontFail)) ||
        FAILED(game->GetRenderState(D3DRS_STENCILZFAIL, &frontZFail)) ||
        FAILED(game->GetRenderState(D3DRS_STENCILPASS, &frontPass)) ||
        FAILED(game->GetRenderState(D3DRS_TWOSIDEDSTENCILMODE, &twoSided)) ||
        (twoSided != FALSE && twoSided != TRUE))
        return false;
    DWORD backFail = 0u, backZFail = 0u, backPass = 0u;
    if (twoSided == TRUE &&
        (FAILED(game->GetRenderState(D3DRS_CCW_STENCILFAIL, &backFail)) ||
         FAILED(game->GetRenderState(D3DRS_CCW_STENCILZFAIL, &backZFail)) ||
         FAILED(game->GetRenderState(D3DRS_CCW_STENCILPASS, &backPass))))
        return false;
    return GameNativeOffscreenPass::all_stencil_ops_keep(
        frontFail, frontZFail, frontPass, twoSided == TRUE,
        backFail, backZFail, backPass);
}

// Preserve the complete game Draw/DrawIndexed source stream when a successful
// call has no possible output write. Menu/car-selection setup draws frequently
// disable color and Z writes; treating them as unsupported used to abort the
// subsequent full-resolution native game Present despite correct GPU pixels.
// Fail closed on unknown state, stencil writes or any bound extra MRT. The
// original D3D9 Draw (and gamepad/input) always executes independently.
bool proven_game_draw_no_target_writes(IDirect3DDevice9* game, const State& s) noexcept {
    if (!game || !env_full_game_opt_in() || s.frameBatch.stopped) return false;
    DWORD colorMask = 0xffffffffu;
    if (FAILED(game->GetRenderState(D3DRS_COLORWRITEENABLE, &colorMask)) ||
        (colorMask & ~0x0fu) != 0u) return false;
    DWORD zEnabled = D3DZB_TRUE, zWrite = TRUE, stencilEnabled = TRUE;
    if (FAILED(game->GetRenderState(D3DRS_ZENABLE, &zEnabled)) ||
        FAILED(game->GetRenderState(D3DRS_ZWRITEENABLE, &zWrite)) ||
        FAILED(game->GetRenderState(D3DRS_STENCILENABLE, &stencilEnabled)))
        return false;
    D3DCAPS9 caps{};
    if (FAILED(game->GetDeviceCaps(&caps)) ||
        !GameNativeOffscreenPass::valid_mrt_count(caps.NumSimultaneousRTs))
        return false;
    // Menu/car/race main-backbuffer draws may retain live RT1..RT3 bindings
    // while disabling every channel on those targets. Such draws are still
    // pixel-neutral if RT0, main Z and stencil are also non-writable. Check
    // each bound MRT's *own* D3D9 color mask; missing caps/state or any
    // writable channel keeps original D3D9 Draw/Present and aborts native.
    constexpr D3DRENDERSTATETYPE kExtraColorMasks[] = {
        D3DRS_COLORWRITEENABLE1, D3DRS_COLORWRITEENABLE2,
        D3DRS_COLORWRITEENABLE3
    };
    for (DWORD i = 1u; i < caps.NumSimultaneousRTs; ++i) {
        ComPtr<IDirect3DSurface9> extra;
        const HRESULT status = game->GetRenderTarget(i, extra.GetAddressOf());
        if (status == D3DERR_NOTFOUND) continue;
        DWORD extraMask = 0xffffffffu;
        if (status != D3DERR_NOTFOUND &&
            (FAILED(status) || !extra ||
             FAILED(game->GetRenderState(kExtraColorMasks[i - 1u], &extraMask)) ||
             !GameNativeOffscreenPass::inactive_extra_mrt(true, extraMask)))
            return false;
    }
    // Stencil test ENABLED does not mean stencil can mutate main Z/S.
    // A zero write mask is read-only; an unknown or nonzero mask must
    // never certify a no-write Draw, even if RT0 and MRT masks are zero.
    DWORD stencilWriteMask = 0xffffffffu;
    const bool stencilMaskKnown = stencilEnabled == FALSE ||
        SUCCEEDED(game->GetRenderState(D3DRS_STENCILWRITEMASK, &stencilWriteMask));
    // A nonzero write mask alone does not make a stencil TEST writable:
    // front and CCW KEEP operations preserve the main Z/S on both faces.
    // Unknown operations or any writable face still abort native output.
    const bool stencilReadOnly = game_stencil_is_read_only(
        game, stencilEnabled, stencilMaskKnown, stencilWriteMask);
    if (!stencilReadOnly) return false;
    const bool stencilWrites = stencilEnabled != FALSE && !stencilReadOnly;
    ComPtr<IDirect3DSurface9> target, backbuffer;
    ComPtr<IUnknown> targetIdentity, identity;
    D3DSURFACE_DESC targetDesc{}, backbufferDesc{};
    if (FAILED(game->GetRenderTarget(0, target.GetAddressOf())) || !target ||
        FAILED(game->GetBackBuffer(0, 0, D3DBACKBUFFER_TYPE_MONO,
                                   backbuffer.GetAddressOf())) || !backbuffer ||
        FAILED(target->GetDesc(&targetDesc)) ||
        FAILED(backbuffer->GetDesc(&backbufferDesc)) ||
        FAILED(target.As(&targetIdentity)) || !targetIdentity ||
        FAILED(backbuffer.As(&identity)) || !identity ||
        targetIdentity.Get() != identity.Get() ||
        targetDesc.Format != backbufferDesc.Format ||
        (backbufferDesc.Format != D3DFMT_A8R8G8B8 &&
         backbufferDesc.Format != D3DFMT_X8R8G8B8))
        return false;
    // On X8 the game's ALPHA-only mask cannot change RT0 color. On A8
    // it is a real destination-alpha update, including later DESTALPHA
    // blending, and must never be dropped. No speculative native Draw is
    // issued for the proved X8 no-write call; the original D3D9 draw and
    // gamepad path remain completely unchanged.
    const bool sameClearedGameBackbuffer = s.clearColor.matches(
        reinterpret_cast<std::uintptr_t>(game),
        reinterpret_cast<std::uintptr_t>(identity.Get()));
    // Preserve the existing COLORWRITEENABLE/ZWRITEENABLE no-op path without
    // adding GetRenderState costs or changing its admitted D3D9 behavior.
    if (GameNativeMaskedDraw::no_visible_target_write_source_draw(
            true, sameClearedGameBackbuffer,
            static_cast<std::uint32_t>(colorMask),
            backbufferDesc.Format == D3DFMT_A8R8G8B8,
            zEnabled != D3DZB_FALSE, zWrite != FALSE,
            stencilWrites, false)) return true;
    // Menu fades and race passes sometimes issue real Draw/DrawIndexed calls
    // with an unconditional D3D9 alpha or Z rejection. They write neither
    // RGB/alpha nor Z even with write masks ON; they must consume a precise
    // source ordinal instead of aborting later full-resolution native draws.
    // Stencil, MRT, foreign RT0, unknown state and missing clear fail closed.
    DWORD alphaTest = FALSE, alphaFunc = 0u, depthFunc = 0u;
    if (FAILED(game->GetRenderState(D3DRS_ALPHATESTENABLE, &alphaTest)) ||
        FAILED(game->GetRenderState(D3DRS_ALPHAFUNC, &alphaFunc)) ||
        FAILED(game->GetRenderState(D3DRS_ZFUNC, &depthFunc)))
        return false;
    return GameNativeFragmentReject::no_target_write(
        true, sameClearedGameBackbuffer, true, true,
        !stencilWrites, alphaTest == TRUE,
        static_cast<std::uint32_t>(alphaFunc),
        zEnabled != D3DZB_FALSE, static_cast<std::uint32_t>(depthFunc));
}
void observe(IDirect3DDevice9* game, D3DPRIMITIVETYPE type, UINT primitives,
             const void* bytes, UINT stride, UINT vertexCount,
             const std::uint32_t* indices, UINT indexCount) noexcept {
    if (!diagnostic_enabled() || !game) return;
    try {
        State& s = state();
        std::lock_guard<std::mutex> lock(s.mutex);
        ++s.observed;
        if (!observe_source_device(s, game)) return;
        if (s.cpuSurfaceReplay.active()) {
            s.frameBatch.abort();
            s.pending = false;
            return; // native Draw may not cross a writable surface acquisition
        }
        // Record every observed game Draw/DrawIndexed before native state
        // admission. Eligible-only ordinals are insufficient to establish
        // contiguous menu, vehicle-selection or race source calls.
        if (s.sourceDrawsThisFrame == (std::numeric_limits<std::uint64_t>::max)()) {
            s.frameBatch.abort();
            return;
        }
        const std::uint64_t sourceOrdinal = s.sourceDrawsThisFrame++;
        const bool fullMode = env_full_game_opt_in();
        if (!observe_source_frame_mode(s, fullMode)) return;
        const bool multiBatch = fullMode || env_batch_opt_in();
        // A successful zero-primitive game Draw changes no target pixels.
        // Before or after the first real native Draw, keep successful no-op
        // calls in the full-size menu/car/race source stream. A pre-Draw
        // empty call requires the real game's whole TARGET Clear and never
        // counts as a GPU Draw, so first-draw RTV/DSV initialization remains.
        // Never accept an unknown topology or rescue an unseeded scene.
        // observe_failed_game_draw() still aborts if D3D9 returned failure.
        if (fullMode && primitives == 0u &&
            type >= D3DPT_POINTLIST && type <= D3DPT_TRIANGLEFAN) {
            const bool sameSourceFullClear = s.clearColor.valid &&
                s.clearColor.sourceDevice ==
                    reinterpret_cast<std::uintptr_t>(game);
            if (!s.frameBatch.absorb_empty_source_draw(
                    sourceOrdinal, sameSourceFullClear))
                s.frameBatch.abort();
            return;
        }
        UINT expectedElements = 0;
        if (!game_native_primitive_element_count(
                static_cast<std::uint32_t>(type), primitives, expectedElements)) {
            // The hook saw a real game source call even when native topology
            // translation is impossible. It must break an active scene batch.
            if (s.frameBatch.must_abort_unsupported(fullMode, multiBatch))
                s.frameBatch.abort();
            return;
        }
        // A successful game Draw/DrawIndexed whose enabled scissor is wholly
        // outside the source viewport has no color/depth effect. Preserve its
        // precise source ordinal in the full native menu->car->race batch
        // without issuing a fabricated GPU draw or losing original D3D9/input.
        // Only proved empty rectangles qualify; intersecting, disabled or
        // failed state queries follow the normal native admission/fallback.
        if (fullMode) {
            DWORD scissorEnabled = FALSE;
            if (SUCCEEDED(game->GetRenderState(D3DRS_SCISSORTESTENABLE, &scissorEnabled)) &&
                scissorEnabled == TRUE) {
                D3DVIEWPORT9 sourceViewport{};
                RECT sourceScissor{};
                if (SUCCEEDED(game->GetViewport(&sourceViewport)) &&
                    SUCCEEDED(game->GetScissorRect(&sourceScissor)) &&
                    GameNativeScissorClip::excludes_viewport(
                        sourceViewport.X, sourceViewport.Y,
                        sourceViewport.Width, sourceViewport.Height,
                        sourceScissor.left, sourceScissor.top,
                        sourceScissor.right, sourceScissor.bottom)) {
                    const bool sameSourceFullClear = s.clearColor.valid &&
                        s.clearColor.sourceDevice ==
                            reinterpret_cast<std::uintptr_t>(game);
                    if (!s.frameBatch.absorb_empty_source_draw(
                            sourceOrdinal, sameSourceFullClear))
                        s.frameBatch.abort();
                    return;
                }
            }
        }
        // Menu/vehicle render-to-texture passes may run between genuine
        // backbuffer draws. Only a proved offscreen, depth/stencil-free,
        // single-RT draw consumes its original game ordinal without issuing
        // any D3D11 pixels. Unsupported main draws still cancel publication.
        if (fullMode && isolated_offscreen_game_draw(game, s)) {
            const bool sameSourceFullClear = s.clearColor.valid &&
                s.clearColor.sourceDevice == reinterpret_cast<std::uintptr_t>(game);
            if (!s.frameBatch.absorb_empty_source_draw(
                    sourceOrdinal, sameSourceFullClear))
                s.frameBatch.abort();
            return;
        }
        // A real Draw/DrawIndexed with RT0 color writes disabled, no Z
        // writes, no stencil writes and no bound MRT is pixel-neutral.
        // Consume its exact source ordinal without dropping the later native
        // menu/car/race frame. Any unproven state follows normal admission
        // and aborts the native copy while D3D9 Draw/input stay intact.
        if (fullMode && proven_game_draw_no_target_writes(game, s)) {
            const bool sameSourceFullClear = s.clearColor.valid &&
                s.clearColor.sourceDevice ==
                    reinterpret_cast<std::uintptr_t>(game);
            if (!s.frameBatch.absorb_empty_source_draw(
                    sourceOrdinal, sameSourceFullClear))
                s.frameBatch.abort();
            return;
        }
        // Actual game VS/PS must never be submitted as the diagnostic FVF
        // fixed-function shader. Attempt the real SM3->DX11 IA/VS/PS path
        // first, with original D3D9 rendering/input/FFB always authoritative.
        if (fullMode) {
            ComPtr<IDirect3DVertexShader9> liveVs;
            ComPtr<IDirect3DPixelShader9> livePs;
            if (SUCCEEDED(game->GetVertexShader(liveVs.GetAddressOf())) &&
                SUCCEEDED(game->GetPixelShader(livePs.GetAddressOf())) &&
                (liveVs || livePs)) {
                if (!submit_live_sm3_game_draw(
                        s, game, type, expectedElements, bytes, stride, vertexCount,
                        indices, indexCount, sourceOrdinal)) {
                    s.frameBatch.abort();
                    ++s.failed;
                }
                return;
            }
        }
        D3DVIEWPORT9 vp{};
        GameFvfLayout layout{};
        std::array<D3DMATRIX, 3> transforms{};
        TextureCapture capture{};
        OutputCapture output{};
        if (!supported_game_state(game, type, vp, layout, transforms, capture, output)) {
            // Once a multi-draw scene starts, an unsupported real game Draw
            // is not a transparent hole in the native compositor. Cancel
            // publication without affecting the original D3D9 rendering.
            if (s.frameBatch.must_abort_unsupported(fullMode, multiBatch))
                s.frameBatch.abort();
            return;
        }
        // Count every admitted state, including calls after this frame's one
        // native draw. Use that bounded population to rotate the next frame's
        // probe rather than sampling its same first triangle indefinitely.
        // Never let an overflowing draw ordinal wrap to zero and spoof a
        // previously sampled Draw; original D3D9 input/Draw still execute.
        if (s.eligibleThisFrame == (std::numeric_limits<UINT>::max)()) {
            if (fullMode) s.frameBatch.abort();
            return;
        }
        const UINT candidateOrdinal = s.eligibleThisFrame++;
        ++s.eligible;
        // A full-resolution menu/vehicle/race output needs the original
        // game's verified color baseline, not a synthetic inset background.
        // Verify same device and canonical D3D9 surface on the first Draw.
        // The first source target match is not enough. A later game Draw
        // can bind an offscreen/menu RT0 without changing D3D9 device or
        // vertex topology. Recheck the exact Clear-owned backbuffer for
        // every native Draw/DrawIndexed; otherwise preserve original D3D9.
        const bool sameClearedGameTarget = s.clearColor.matches(
            reinterpret_cast<std::uintptr_t>(game), output.targetIdentity);
        const bool admitted = fullMode
            ? s.frameBatch.accepts_full_on_source_target(
                  sourceOrdinal, sameClearedGameTarget)
            : s.frameBatch.accepts(candidateOrdinal, s.probeSlot,
                                  env_batch_opt_in());
        if (!admitted) {
            if (fullMode) s.frameBatch.abort();
            return;
        }
        if (!s.frameBatch.accepts_source_draw(sourceOrdinal, multiBatch)) {
            s.frameBatch.abort();
            return;
        }
        // A vehicle/menu pass can rebind a foreign Z surface without a
        // corresponding Clear. Even an accepted main-RT color Draw cannot
        // reuse that depth history as the native full-resolution DSV.
        // Require the same seeded main D3D9 Z identity on every depth Draw.
        if (fullMode && output.nativeDepthTest) {
            ComPtr<IDirect3DSurface9> boundDepth;
            ComPtr<IUnknown> boundDepthIdentity;
            if (FAILED(game->GetDepthStencilSurface(boundDepth.GetAddressOf())) ||
                !boundDepth || FAILED(boundDepth.As(&boundDepthIdentity)) ||
                !boundDepthIdentity ||
                !s.clearColor.main_depth_still_bound(
                    reinterpret_cast<std::uintptr_t>(boundDepthIdentity.Get()))) {
                s.frameBatch.abort();
                return;
            }
        }
        // A second depth draw with reversed Z direction cannot share the
        // previous native diagnostic DSV; fail closed, original D3D9 survives.
        if (!s.frameBatch.accepts_depth(output.nativeDepthTest,
                                        output.nativeDepthOrderingMode != 0u)) {
            s.frameBatch.abort();
            return;
        }
        // X8 has no writable destination alpha. Apply the native RGB-only
        // mask to the admitted real game Draw source, including fan/indexed
        // variants. Keep the existing validated OM state cache and A8 mask.
        if (fullMode) {
            // An earlier isolated auxiliary Z/stencil Clear cannot silently
            // become the native main DSV history when the game rebinds that
            // auxiliary surface for a later main Draw. Preserve fallback.
            if (s.clearColor.auxiliaryDepthCleared && output.nativeDepthTest) {
                ComPtr<IDirect3DSurface9> liveDepth;
                ComPtr<IUnknown> liveDepthIdentity;
                if (FAILED(game->GetDepthStencilSurface(liveDepth.GetAddressOf())) ||
                    !liveDepth || FAILED(liveDepth.As(&liveDepthIdentity)) ||
                    !liveDepthIdentity || !s.clearColor.main_depth_still_bound(
                        reinterpret_cast<std::uintptr_t>(liveDepthIdentity.Get()))) {
                    s.frameBatch.abort();
                    return;
                }
            }
            output.colorWriteMask = s.clearColor.native_write_mask(
                reinterpret_cast<std::uintptr_t>(game), output.targetIdentity,
                output.colorWriteMask);
            // X8 masks alpha to zero. Such a game draw is still meaningful
            // only if the accepted native DSV can record its depth prepass.
            // No-effect Draws must not certify a full game color frame.
            if (output.colorWriteMask == 0u && !output.nativeDepthWrite) {
                s.frameBatch.abort();
                return;
            }
        }
        if (indexCount && (!indices || indexCount != expectedElements ||
                           vertexCount > kMaxVertices)) {
            s.frameBatch.abort();
            return;
        }
        if (!indexCount && vertexCount != expectedElements) {
            s.frameBatch.abort();
            return;
        }
        std::vector<NativeVertex> vertices;
        if (!translate_vertices(bytes, vertexCount, stride, vp,
                                layout, transforms, capture, vertices)) {
            s.frameBatch.abort();
            return;
        }
        if (indices) {
            for (UINT i=0; i<indexCount; ++i) {
                if (indices[i] >= vertexCount) {
                    s.frameBatch.abort();
                    return;
                }
            }
        }
        if (type == D3DPT_TRIANGLEFAN) {
            // Real game VB/IB/UP data, rebased by R30. No fixture substitution.
            std::vector<std::uint32_t> fanTriangles;
            if (!game_fan_to_triangle_list(primitives, indices, indexCount,
                                           vertexCount, fanTriangles)) {
                s.frameBatch.abort();
                return;
            }
            if (!submit(s, vertices, fanTriangles.data(),
                        static_cast<UINT>(fanTriangles.size()),
                        D3DPT_TRIANGLELIST, capture, output)) {
                s.frameBatch.abort();
                ++s.failed;
            } else {
                s.frameBatch.succeeded(output.nativeDepthTest,
                                       output.nativeDepthOrderingMode != 0u);
                s.frameBatch.record_source_draw(sourceOrdinal);
            }
        } else {
            if (!submit(s, vertices, indices, indexCount, type, capture, output)) {
                s.frameBatch.abort();
                ++s.failed;
            } else {
                s.frameBatch.succeeded(output.nativeDepthTest,
                                       output.nativeDepthOrderingMode != 0u);
                s.frameBatch.record_source_draw(sourceOrdinal);
            }
        }
    } catch (...) {
        // If allocation or translation throws after one native Draw, do not
        // append subsequent game draws into a partially composed frame.
        // Catch any diagnostic cleanup failure: D3D9 Draw/input must survive.
        try {
            State& s = state();
            std::lock_guard<std::mutex> lock(s.mutex);
            s.frameBatch.abort();
            ++s.failed;
        } catch (...) {
            // Never interrupt the original D3D9 Draw/Present path.
        }
    }
}
} // namespace

// A successful R9 RT0 switch to/from a verified auxiliary game target
// changes no backbuffer pixels on its own. Preserve full-frame draw ownership;
// actual offscreen Draws must pass the independent no-Z/stencil/MRT proof below.
bool preserve_game_target_transition(IDirect3DDevice9* game) noexcept {
    if (!diagnostic_enabled() || !env_full_game_opt_in() || !game) return false;
    try {
        State& s = state();
        std::lock_guard<std::mutex> lock(s.mutex);
        const auto owner = reinterpret_cast<std::uintptr_t>(game);
        ComPtr<IDirect3DSurface9> target, backbuffer;
        ComPtr<IUnknown> targetIdentity, backbufferIdentity;
        if (FAILED(game->GetRenderTarget(0, target.GetAddressOf())) || !target ||
            FAILED(game->GetBackBuffer(0, 0, D3DBACKBUFFER_TYPE_MONO,
                                      backbuffer.GetAddressOf())) || !backbuffer ||
            FAILED(target.As(&targetIdentity)) ||
            FAILED(backbuffer.As(&backbufferIdentity))) return false;
        return GameNativeOffscreenPass::preserve_transition(
            true, s.clearColor.matches(owner, reinterpret_cast<std::uintptr_t>(
                backbufferIdentity.Get())),
            s.sourceGameDevice == 0u || s.sourceGameDevice == owner,
            s.frameBatch.stopped, targetIdentity != nullptr);
    } catch (...) {
        return false; // Unproved RT changes follow original fail-closed boundary.
    }
}

bool diagnostic_enabled() noexcept {
    static const bool optedIn = env_opt_in();
    return optedIn;
}

// One original game D3D9 Present may enter the native observer with stereo
// enabled. Never replace the real R9 left eye with a pre-stereo mono D3D11
// image, even when the diagnostic/native full-frame env opt-in is set.
thread_local bool monoNativePublicationAllowed = true;

ScopedMonoNativePublication::ScopedMonoNativePublication(bool allow) noexcept
    : previous_(monoNativePublicationAllowed) {
    monoNativePublicationAllowed = previous_ && allow;
}
ScopedMonoNativePublication::~ScopedMonoNativePublication() noexcept {
    monoNativePublicationAllowed = previous_;
}

void set_native_full_game_gpu_sink(NativeFullGameGpuSink sink, void* user) noexcept {
    State& s = state();
    std::lock_guard<std::mutex> lock(s.mutex);
    s.gpuFrameSink = sink;
    s.gpuFrameSinkUser = sink ? user : nullptr;
}

void observe_empty_game_draw(IDirect3DDevice9* game,
                             D3DPRIMITIVETYPE type) noexcept {
    // No fabricated GPU Draw: only an already seeded actual game frame
    // absorbs this source ordinal; original D3D9 Draw/input stay authoritative.
    if (!game_native_empty_primitive_type(static_cast<std::uint32_t>(type))) {
        observe_unavailable_game_draw(game);
        return;
    }
    observe(game, type, 0u, nullptr, 0u, 0u, nullptr, 0u);
}

void observe_linear(IDirect3DDevice9* game, D3DPRIMITIVETYPE type,
                    UINT primitives, const void* vertices, UINT stride) noexcept {
    // DrawPrimitiveUP with no vertices is a real source call, not a missing
    // shadow. Preserve its ordinal between full-size menu/car/race native Draws.
    if (primitives == 0u &&
        game_native_empty_primitive_type(static_cast<std::uint32_t>(type))) {
        observe_empty_game_draw(game, type);
        return;
    }
    UINT nativeElements = 0;
    if (!game_native_primitive_element_count(static_cast<std::uint32_t>(type),
                                             primitives, nativeElements)) {
        // Oversized/invalid DrawPrimitiveUP still belongs to the original
        // D3D9 game stream: never splice native batches across that call.
        observe_unavailable_game_draw(game);
        return;
    }
    observe(game, type, primitives, vertices, stride, nativeElements, nullptr, 0);
}

void observe_indexed(IDirect3DDevice9* game, D3DPRIMITIVETYPE type,
                     UINT primitives, const void* vertices, UINT stride,
                     UINT vertexCount, const std::uint32_t* indices,
                     UINT indexCount) noexcept {
    observe(game, type, primitives, vertices, stride, vertexCount, indices, indexCount);
}

bool preserve_offscreen_color_only_clear(IDirect3DDevice9* game,
                                         DWORD flags) noexcept {
    // Legacy hook name retained for callers. Auxiliary Z/STENCIL-only
    // Clears cannot change the main color even when the main RT0 stays
    // bound; exact independent Z/S identity is still mandatory.
    const DWORD clearBits = D3DCLEAR_TARGET | D3DCLEAR_ZBUFFER | D3DCLEAR_STENCIL;
    if (!diagnostic_enabled() || !env_full_game_opt_in() || !game ||
        (flags & clearBits) == 0u || (flags & ~clearBits) != 0u) return false;
    try {
        State& s = state();
        std::lock_guard<std::mutex> lock(s.mutex);
        const auto owner = reinterpret_cast<std::uintptr_t>(game);
        if ((s.sourceGameDevice != 0u && s.sourceGameDevice != owner) ||
            s.frameBatch.stopped || !s.clearColor.valid) return false;
        D3DCAPS9 caps{};
        if (FAILED(game->GetDeviceCaps(&caps)) ||
            !GameNativeOffscreenPass::valid_mrt_count(caps.NumSimultaneousRTs))
            return false;
        // D3DCLEAR_TARGET ignores COLORWRITEENABLEn: a bound MRT must be
        // proven independent of the seeded main backbuffer, even when its
        // color mask is zero. Z/stencil-only Clears do not touch color MRTs.
        if ((flags & D3DCLEAR_TARGET) != 0u) {
            for (DWORD slot = 1u; slot < caps.NumSimultaneousRTs; ++slot) {
                ComPtr<IDirect3DSurface9> extra;
                const HRESULT hr = game->GetRenderTarget(slot, extra.GetAddressOf());
                if (hr == D3DERR_NOTFOUND) continue;
                ComPtr<IUnknown> extraIdentity;
                if (FAILED(hr) || !extra ||
                    FAILED(extra.As(&extraIdentity)) || !extraIdentity ||
                    !GameNativeOffscreenPass::distinct_auxiliary_mrt(
                        reinterpret_cast<std::uintptr_t>(extraIdentity.Get()),
                        s.clearColor.backbufferIdentity))
                    return false;
            }
        }
        const bool clearsDepth = (flags & (D3DCLEAR_ZBUFFER | D3DCLEAR_STENCIL)) != 0u;
        if (clearsDepth) {
            ComPtr<IDirect3DSurface9> depth;
            ComPtr<IUnknown> depthIdentity;
            if (!s.clearColor.mainDepthIdentity ||
                FAILED(game->GetDepthStencilSurface(depth.GetAddressOf())) || !depth ||
                FAILED(depth.As(&depthIdentity)) || !depthIdentity ||
                s.clearColor.main_depth_still_bound(
                    reinterpret_cast<std::uintptr_t>(depthIdentity.Get())))
                return false;
        }
        ComPtr<IDirect3DSurface9> target, backbuffer;
        ComPtr<IUnknown> targetIdentity, backbufferIdentity;
        if (FAILED(game->GetRenderTarget(0, target.GetAddressOf())) || !target ||
            FAILED(game->GetBackBuffer(0, 0, D3DBACKBUFFER_TYPE_MONO,
                                      backbuffer.GetAddressOf())) || !backbuffer ||
            FAILED(target.As(&targetIdentity)) ||
            FAILED(backbuffer.As(&backbufferIdentity)) ||
            !targetIdentity || !backbufferIdentity) return false;
        const bool seeded = s.clearColor.matches(
            owner, reinterpret_cast<std::uintptr_t>(backbufferIdentity.Get()));
        const bool offscreen = targetIdentity.Get() != backbufferIdentity.Get();
        // Menu/vehicle previews may clear a distinct Z/S surface while
        // retaining the canonical backbuffer as RT0. Such a Clear writes no
        // color and must not tear the native full game Draw/Present stream.
        // Color TARGET Clears retain strict RT0/MRT isolation.
        const bool clearsColor = (flags & D3DCLEAR_TARGET) != 0u;
        const bool safe = GameNativeOffscreenPass::isolated_auxiliary_clear(
            seeded, offscreen, true, clearsDepth, true,
            s.frameBatch.stopped, clearsColor);
        if (safe && clearsDepth) s.clearColor.note_auxiliary_depth_clear();
        return safe;
    } catch (...) {
        // No unproved native publication may change the original D3D9 game.
        return false;
    }
}


bool preserve_game_surface_copy(
    IDirect3DDevice9* game, IDirect3DSurface9* destination,
    const RECT* changedArea, HRESULT originalResult,
    bool completingCpuWrite) noexcept {
    // This is invoked AFTER the original D3D9 StretchRect/UpdateSurface has
    // succeeded. The game-visible fallback always keeps its original HRESULT.
    // Only active full-resolution real-game native Draw batches are eligible.
    if (nativeOutputUploadDepth != 0u || !diagnostic_enabled() ||
        !env_full_game_opt_in() || !game || !destination ||
        FAILED(originalResult)) return false;
    try {
        State& s = state();
        std::lock_guard<std::mutex> lock(s.mutex);
        const auto owner = reinterpret_cast<std::uintptr_t>(game);
        if (s.sourceGameDevice != owner || !s.frameBatch.publishable(s.pending) ||
            s.surfaceReplayCount >= 8u || !s.backend.ready() ||
            !s.backend.device() || !s.backend.context() ||
            !s.backend.color_texture()) return false;

        ComPtr<IDirect3DSurface9> backbuffer;
        ComPtr<IUnknown> actualIdentity, backbufferIdentity;
        D3DSURFACE_DESC desc{};
        if (FAILED(game->GetBackBuffer(0u, 0u, D3DBACKBUFFER_TYPE_MONO,
                                      backbuffer.GetAddressOf())) || !backbuffer ||
            FAILED(destination->GetDesc(&desc)) ||
            FAILED(destination->QueryInterface(
                IID_PPV_ARGS(actualIdentity.GetAddressOf()))) ||
            FAILED(backbuffer.As(&backbufferIdentity)) || !actualIdentity ||
            !backbufferIdentity ||
            actualIdentity.Get() != backbufferIdentity.Get() ||
            !s.clearColor.matches(
                owner, reinterpret_cast<std::uintptr_t>(actualIdentity.Get())) ||
            desc.Pool != D3DPOOL_DEFAULT ||
            desc.MultiSampleType != D3DMULTISAMPLE_NONE ||
            (desc.Format != D3DFMT_A8R8G8B8 &&
             desc.Format != D3DFMT_X8R8G8B8) ||
            desc.Width != s.nativeWidth || desc.Height != s.nativeHeight)
            return false;

        const auto region = changedArea
            ? GameNativeSurfaceCopyRegion::destination(
                changedArea->left, changedArea->top,
                changedArea->right, changedArea->bottom,
                desc.Width, desc.Height)
            : GameNativeSurfaceCopyRegion::destination(
                0, 0, desc.Width, desc.Height, desc.Width, desc.Height);
        if (!region.valid) return false;
        // No other D3D9 postpass may consume pixels from an open CPU/GDI
        // write. Only the exact locked surface/rectangle may finish it.
        if (s.cpuSurfaceReplay.active() != completingCpuWrite ||
            (completingCpuWrite && !s.cpuSurfaceReplay.matches(
                owner, reinterpret_cast<std::uintptr_t>(actualIdentity.Get()),
                region.left, region.top, region.right, region.bottom)))
            return false;

        // GetRenderTargetData synchronizes real D3D9 pixels. It is explicitly
        // diagnostic/opt-in, never silently promoted as a performant shared
        // GPU transport. Reuse the staging allocation for sustained gameplay.
        if (!s.surfaceReplayReadback || s.surfaceReplayOwner != owner ||
            s.surfaceReplayWidth != desc.Width ||
            s.surfaceReplayHeight != desc.Height ||
            s.surfaceReplayFormat != desc.Format) {
            s.surfaceReplayReadback.Reset();
            s.surfaceReplayOwner = 0u;
            if (FAILED(game->CreateOffscreenPlainSurface(
                    desc.Width, desc.Height, desc.Format, D3DPOOL_SYSTEMMEM,
                    s.surfaceReplayReadback.GetAddressOf(), nullptr)) ||
                !s.surfaceReplayReadback) return false;
            s.surfaceReplayOwner = owner;
            s.surfaceReplayWidth = desc.Width;
            s.surfaceReplayHeight = desc.Height;
            s.surfaceReplayFormat = desc.Format;
        }
        if (FAILED(game->GetRenderTargetData(
                destination, s.surfaceReplayReadback.Get()))) return false;
        D3DLOCKED_RECT locked{};
        if (FAILED(s.surfaceReplayReadback->LockRect(
                &locked, nullptr, D3DLOCK_READONLY))) return false;
        const std::size_t rowBytes = std::size_t(region.width()) * 4u;
        const bool readable = locked.pBits && locked.Pitch > 0 &&
            std::uint64_t(locked.Pitch) >= std::uint64_t(desc.Width) * 4u;
        bool copied = readable;
        if (readable) {
            // Always unlock D3D9 staging even when vector growth fails.
            // A dangling LockRect would poison later gameplay readbacks.
            try {
                s.surfaceReplayPixels.resize(
                    rowBytes * std::size_t(region.height()));
                const auto* bytes = static_cast<const std::uint8_t*>(locked.pBits);
                for (UINT y = 0u; y < region.height(); ++y) {
                    auto* dst = s.surfaceReplayPixels.data() +
                                std::size_t(y) * rowBytes;
                    const auto* src = bytes +
                        std::size_t(region.top + y) * std::size_t(locked.Pitch) +
                        std::size_t(region.left) * 4u;
                    std::memcpy(dst, src, rowBytes);
                    if (desc.Format == D3DFMT_X8R8G8B8) {
                        // D3D9 X8 has no defined alpha. Never copy its X byte
                        // into a native BGRA8 RTV as visible alpha.
                        for (std::size_t x = 3u; x < rowBytes; x += 4u)
                            dst[x] = 0xffu;
                    }
                }
            } catch (...) { copied = false; }
        }
        const HRESULT unlocked = s.surfaceReplayReadback->UnlockRect();
        if (!copied || FAILED(unlocked)) return false;

        auto* device = s.backend.device();
        auto* context = s.backend.context();
        if (!s.surfaceReplayScratch ||
            s.surfaceReplayScratchDevice.Get() != device ||
            s.surfaceReplayScratchWidth != region.width() ||
            s.surfaceReplayScratchHeight != region.height()) {
            s.surfaceReplayScratch.Reset();
            s.surfaceReplayScratchDevice.Reset();
            D3D11_TEXTURE2D_DESC scratch{};
            scratch.Width = region.width();
            scratch.Height = region.height();
            scratch.MipLevels = 1u;
            scratch.ArraySize = 1u;
            scratch.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
            scratch.SampleDesc.Count = 1u;
            scratch.Usage = D3D11_USAGE_DEFAULT;
            // The transient source is GPU copy-only; never sample it as
            // fictional game geometry, nor allocate a CPU-readable DX11 RT.
            scratch.BindFlags = 0u;
            if (FAILED(device->CreateTexture2D(
                    &scratch, nullptr,
                    s.surfaceReplayScratch.GetAddressOf())) ||
                !s.surfaceReplayScratch) return false;
            s.surfaceReplayScratchDevice = device;
            s.surfaceReplayScratchWidth = region.width();
            s.surfaceReplayScratchHeight = region.height();
        }
        if (FAILED(device->GetDeviceRemovedReason())) return false;
        context->UpdateSubresource(s.surfaceReplayScratch.Get(), 0u,
            nullptr, s.surfaceReplayPixels.data(),
            static_cast<UINT>(rowBytes), 0u);
        // A D3D11 RTV cannot remain a writable output while it is the
        // destination of CopySubresourceRegion. Restore its native Z/OM
        // bindings so the next real game Draw retains depth chronology.
        ID3D11RenderTargetView* oldColor = nullptr;
        ID3D11DepthStencilView* oldDepth = nullptr;
        context->OMGetRenderTargets(1u, &oldColor, &oldDepth);
        context->OMSetRenderTargets(0u, nullptr, nullptr);
        context->CopySubresourceRegion(
            s.backend.color_texture(), 0u, region.left, region.top, 0u,
            s.surfaceReplayScratch.Get(), 0u, nullptr);
        context->OMSetRenderTargets(1u, &oldColor, oldDepth);
        if (oldColor) oldColor->Release();
        if (oldDepth) oldDepth->Release();
        ++s.surfaceReplayCount;
        if (completingCpuWrite) s.cpuSurfaceReplay.reset();
        // Neither a CPU readback nor its D3D11 GPU copy counts as a native
        // Draw/DrawIndexed or supplies invented left/right eye evidence.
        return true;
    } catch (...) {
        return false; // next mutation observer aborts native publication
    }
}


bool begin_game_surface_cpu_write(IDirect3DDevice9* game,
    IDirect3DSurface9* destination, const RECT* rect,
    bool fromGdi) noexcept {
    if (nativeOutputUploadDepth || !diagnostic_enabled() ||
        !env_full_game_opt_in() || !game || !destination) return false;
    try {
        D3DSURFACE_DESC desc{};
        ComPtr<IUnknown> identity, backbufferIdentity;
        ComPtr<IDirect3DSurface9> backbuffer;
        if (FAILED(destination->GetDesc(&desc)) ||
            FAILED(destination->QueryInterface(IID_PPV_ARGS(identity.GetAddressOf()))) ||
            !identity ||
            FAILED(game->GetBackBuffer(0u, 0u, D3DBACKBUFFER_TYPE_MONO,
                backbuffer.GetAddressOf())) || !backbuffer ||
            FAILED(backbuffer.As(&backbufferIdentity)) ||
            identity.Get() != backbufferIdentity.Get() ||
            desc.Pool != D3DPOOL_DEFAULT ||
            desc.MultiSampleType != D3DMULTISAMPLE_NONE ||
            (desc.Format != D3DFMT_A8R8G8B8 &&
             desc.Format != D3DFMT_X8R8G8B8)) return false;
        const auto region = rect
            ? GameNativeSurfaceCopyRegion::destination(
                rect->left, rect->top, rect->right, rect->bottom,
                desc.Width, desc.Height)
            : GameNativeSurfaceCopyRegion::destination(
                0, 0, desc.Width, desc.Height, desc.Width, desc.Height);
        if (!region.valid) return false;
        State& s = state();
        std::lock_guard<std::mutex> lock(s.mutex);
        const auto owner = reinterpret_cast<std::uintptr_t>(game);
        if (s.cpuSurfaceReplay.active()) {
            s.frameBatch.abort();
            s.pending = false;
            return false;
        }
        if (s.sourceGameDevice != owner ||
            !s.clearColor.matches(owner,
                reinterpret_cast<std::uintptr_t>(identity.Get())) ||
            !s.frameBatch.publishable(s.pending) ||
            !s.backend.ready() || !s.backend.color_texture() ||
            s.nativeWidth != desc.Width || s.nativeHeight != desc.Height ||
            s.surfaceReplayCount >= 8u) return false;
        return s.cpuSurfaceReplay.begin(owner,
            reinterpret_cast<std::uintptr_t>(identity.Get()),
            region.left, region.top, region.right, region.bottom,
            desc.Width, desc.Height, fromGdi);
    } catch (...) { return false; }
}

void finish_game_surface_cpu_write(IDirect3DDevice9* game,
    IDirect3DSurface9* destination, HRESULT originalResult,
    bool fromGdi) noexcept {
    if (!game || !destination) return;
    try {
        ComPtr<IUnknown> identity;
        if (FAILED(destination->QueryInterface(IID_PPV_ARGS(
                identity.GetAddressOf()))) || !identity) return;
        RECT r{};
        const auto owner = reinterpret_cast<std::uintptr_t>(game);
        {
            State& s = state();
            std::lock_guard<std::mutex> lock(s.mutex);
            if (!s.cpuSurfaceReplay.permits_finish(fromGdi) ||
                s.cpuSurfaceReplay.owner != owner ||
                s.cpuSurfaceReplay.surface !=
                    reinterpret_cast<std::uintptr_t>(identity.Get()))
                return; // read-only/foreign resource never opened a ticket
            r = {static_cast<LONG>(s.cpuSurfaceReplay.left),
                 static_cast<LONG>(s.cpuSurfaceReplay.top),
                 static_cast<LONG>(s.cpuSurfaceReplay.right),
                 static_cast<LONG>(s.cpuSurfaceReplay.bottom)};
        }
        if (SUCCEEDED(originalResult) &&
            preserve_game_surface_copy(game, destination, &r,
                                       originalResult, true)) return;
        State& s = state();
        std::lock_guard<std::mutex> lock(s.mutex);
        s.cpuSurfaceReplay.reset();
        s.frameBatch.abort();
        s.pending = false;
        s.preDrawFills.discard();
        s.clearColor.discard();
        if (++s.outputGeneration == 0u) ++s.outputGeneration;
    } catch (...) {
        State& s = state();
        std::lock_guard<std::mutex> lock(s.mutex);
        s.cpuSurfaceReplay.reset();
        s.frameBatch.abort();
        s.pending = false;
    }
}

void observe_game_surface_mutation(
    IDirect3DDevice9* game, IDirect3DSurface9* destination,
    HRESULT originalResult) noexcept {
    // Only report a real, successful game-side surface write. This hook
    // observes but never substitutes the D3D9 HRESULT or changes input/FFB.
    // Our own native -> game UpdateSurface occurs under State::mutex; bypass
    // it on the same thread before attempting any COM query or locking.
    if (nativeOutputUploadDepth != 0u || !diagnostic_enabled() ||
        !env_full_game_opt_in() || !game || !destination ||
        FAILED(originalResult)) return;
    try {
        ComPtr<IDirect3DSurface9> surface(destination);
        ComPtr<IUnknown> identity;
        if (FAILED(surface.As(&identity)) || !identity) return;
        State& s = state();
        std::lock_guard<std::mutex> lock(s.mutex);
        const auto owner = reinterpret_cast<std::uintptr_t>(game);
        const bool knownOwner = s.clearColor.valid &&
            s.clearColor.sourceDevice == owner &&
            (s.sourceGameDevice == 0u || s.sourceGameDevice == owner);
        const bool writesGameBackbuffer =
            s.clearColor.backbufferIdentity != 0u &&
            reinterpret_cast<std::uintptr_t>(identity.Get()) ==
                s.clearColor.backbufferIdentity;
        if (!GameNativeSourceMutation::invalidates_full_game_frame(
                env_full_game_opt_in(), SUCCEEDED(originalResult),
                knownOwner, writesGameBackbuffer, false)) return;
        // The D3D9 ColorFill / StretchRect / UpdateSurface bytes survive.
        // Native D3D11 has no equivalent command in this frame, so do not
        // overwrite any part of that original menu/vehicle/race image.
        s.frameBatch.abort();
        s.pending = false;
        s.preDrawFills.discard();
        s.clearColor.discard();
        if (++s.outputGeneration == 0u) ++s.outputGeneration;
    } catch (...) {
        // Observer failures must never change the original D3D9 result.
    }
}



// Validate the actual main depth surface and the native D32 view *before*
// issuing either half of a combined TARGET|Z Clear. The original game D3D9
// Clear always runs first and remains the authoritative fallback.
bool native_game_partial_depth_ready(
    State& s, IDirect3DDevice9* game,
    std::uint32_t width, std::uint32_t height) noexcept {
    if (!s.frameBatch.depthReady || s.frameBatch.depthClearPending ||
        !s.diagnosticDepthView || !s.backend.context() ||
        s.nativeWidth != width || s.nativeHeight != height)
        return false;
    ComPtr<IDirect3DSurface9> depth;
    ComPtr<IUnknown> depthIdentity;
    D3DSURFACE_DESC desc{};
    if (FAILED(game->GetDepthStencilSurface(depth.GetAddressOf())) ||
        !depth || FAILED(depth->GetDesc(&desc)) ||
        FAILED(depth.As(&depthIdentity)) || !depthIdentity ||
        desc.Width != width || desc.Height != height ||
        desc.MultiSampleType != D3DMULTISAMPLE_NONE ||
        !s.clearColor.main_depth_still_bound(
            reinterpret_cast<std::uintptr_t>(depthIdentity.Get())))
        return false;
    D3D11_DEPTH_STENCIL_VIEW_DESC nativeDesc{};
    s.diagnosticDepthView->GetDesc(&nativeDesc);
    return nativeDesc.Format == DXGI_FORMAT_D32_FLOAT;
}

bool preserve_game_partial_target_clear(
    IDirect3DDevice9* game, DWORD count, const D3DRECT* rects,
    DWORD flags, D3DCOLOR color, float z) noexcept {
    // Called only AFTER successful original D3D9 Clear. The same native
    // region may update RTV and the live depth-only DSV; unproved Z writes
    // must not leave half of a combined color/depth Clear applied.
    const bool clearZ = (flags & D3DCLEAR_ZBUFFER) != 0u;
    if (!diagnostic_enabled() || !env_full_game_opt_in() || !game ||
        (flags != D3DCLEAR_TARGET &&
         flags != (D3DCLEAR_TARGET | D3DCLEAR_ZBUFFER)) ||
        (clearZ && !(z >= 0.0f && z <= 1.0f)) ||
        count > GameNativeSourceMutation::kMaxPartialTargetClearRects ||
        (count != 0u && !rects)) return false;
    try {
        State& s = state();
        std::lock_guard<std::mutex> lock(s.mutex);
        const auto owner = reinterpret_cast<std::uintptr_t>(game);
        ComPtr<IDirect3DSurface9> target, backbuffer;
        D3DSURFACE_DESC targetDesc{}, backbufferDesc{};
        D3DVIEWPORT9 vp{};
        if (FAILED(game->GetRenderTarget(0u, target.GetAddressOf())) || !target ||
            FAILED(game->GetBackBuffer(0u, 0u, D3DBACKBUFFER_TYPE_MONO,
                                      backbuffer.GetAddressOf())) || !backbuffer ||
            FAILED(target->GetDesc(&targetDesc)) ||
            FAILED(backbuffer->GetDesc(&backbufferDesc)) ||
            FAILED(game->GetViewport(&vp))) return false;
        ComPtr<IUnknown> rtIdentity, bbIdentity;
        if (FAILED(target.As(&rtIdentity)) ||
            FAILED(backbuffer.As(&bbIdentity)) ||
            !rtIdentity || !bbIdentity) return false;
        const bool sameBackbuffer = rtIdentity.Get() == bbIdentity.Get() &&
            s.clearColor.matches(owner,
                reinterpret_cast<std::uintptr_t>(bbIdentity.Get())) &&
            targetDesc.Width == backbufferDesc.Width &&
            targetDesc.Height == backbufferDesc.Height &&
            targetDesc.MultiSampleType == D3DMULTISAMPLE_NONE &&
            (backbufferDesc.Format == D3DFMT_A8R8G8B8 ||
             backbufferDesc.Format == D3DFMT_X8R8G8B8);
        const bool ready = s.backend.ready() && s.backend.context() &&
            s.backend.color_rtv() &&
            s.nativeWidth == backbufferDesc.Width &&
            s.nativeHeight == backbufferDesc.Height;
        D3DCAPS9 caps{};
        if (FAILED(game->GetDeviceCaps(&caps)) ||
            !GameNativeOffscreenPass::valid_mrt_count(caps.NumSimultaneousRTs))
            return false;
        for (DWORD i = 1u; i < caps.NumSimultaneousRTs; ++i) {
            ComPtr<IDirect3DSurface9> extra;
            // A TARGET Clear with any bound MRT writes unmirrored color.
            if (game->GetRenderTarget(i, extra.GetAddressOf()) != D3DERR_NOTFOUND)
                return false;
        }
        if (!GameNativeSourceMutation::mirrors_partial_target_clear(
                true, true, s.sourceGameDevice == owner, sameBackbuffer,
                s.pending && !s.frameBatch.stopped &&
                    s.frameBatch.submitted != 0u, ready, true))
            return false;

        // Validate and clip the ENTIRE successful game Clear batch before
        // touching the GPU. Fully disjoint rectangles are D3D9 no-ops, not
        // reasons to abandon the native menu/car/race frame. ClearView must
        // receive only populated, nonempty rectangles (never empty extents).
        std::array<D3D11_RECT,
            GameNativeSourceMutation::kMaxPartialTargetClearRects> regions{};
        const std::uint32_t n = count ? count : 1u;
        std::uint32_t nativeRegionCount = 0u;
        for (std::uint32_t i = 0u; i < n; ++i) {
            const std::int64_t l = count ? rects[i].x1 : vp.X;
            const std::int64_t t = count ? rects[i].y1 : vp.Y;
            const std::int64_t r = count ? rects[i].x2 :
                static_cast<std::int64_t>(vp.X) + vp.Width;
            const std::int64_t b = count ? rects[i].y2 :
                static_cast<std::int64_t>(vp.Y) + vp.Height;
            GameNativeSourceMutation::TargetClearRect clipped{};
            const auto coverage = GameNativeSourceMutation::classify_target_clear_rect(
                l,t,r,b,vp.X,vp.Y,vp.Width,vp.Height,
                backbufferDesc.Width,backbufferDesc.Height,clipped);
            if (coverage == GameNativeSourceMutation::TargetClearClip::Invalid)
                return false;
            if (coverage == GameNativeSourceMutation::TargetClearClip::Empty)
                continue;
            regions[nativeRegionCount++] = {
                static_cast<LONG>(clipped.left),
                static_cast<LONG>(clipped.top),
                static_cast<LONG>(clipped.right),
                static_cast<LONG>(clipped.bottom)};
        }
        // Check the D3D9 main Z owner, extents and native D32 attachment
        // before changing even the color RTV of a combined TARGET|Z Clear.
        if (clearZ && !native_game_partial_depth_ready(
                s, game, backbufferDesc.Width, backbufferDesc.Height))
            return false;
        // An entirely off-viewport successful D3D9 Clear wrote neither
        // color nor Z. Retain the native frame and exact Draw ordinals.
        if (nativeRegionCount == 0u) return true;
        ComPtr<ID3D11DeviceContext1> ctx1;
        if (FAILED(s.backend.context()->QueryInterface(
                IID_PPV_ARGS(ctx1.GetAddressOf()))) || !ctx1)
            return false; // D3D11.0: leave original D3D9 and input intact.
        constexpr float scale = 1.0f / 255.0f;
        const float rgba[4] = {
            float((color >> 16) & 255u) * scale,
            float((color >> 8) & 255u) * scale,
            float(color & 255u) * scale,
            backbufferDesc.Format == D3DFMT_X8R8G8B8 ? 1.0f :
                float((color >> 24) & 255u) * scale
        };
        ctx1->ClearView(s.backend.color_rtv(), rgba, regions.data(),
                        nativeRegionCount);
        if (clearZ) {
            // D32_FLOAT has no stencil component, which is required for
            // ClearView's depth-rectangle support. Preserve all other Z.
            const float depthValue[4] = {z, 0.0f, 0.0f, 0.0f};
            ctx1->ClearView(s.diagnosticDepthView.Get(), depthValue,
                            regions.data(), nativeRegionCount);
        }
        // Neither command consumes a game Draw ordinal or alters D3D9 input.
        return true;
    } catch (...) { return false; }
}

bool preserve_game_color_fill(
    IDirect3DDevice9* game, IDirect3DSurface9* destination,
    const RECT* rect, D3DCOLOR color, HRESULT originalResult) noexcept {
    // Observe the successful original D3D9 write; never replace its HRESULT.
    // A whole fill updates the initial native clear or clears the live RTV.
    // A bounded partial fill after native Draw requires D3D11.1 ClearView:
    // unlike ClearRenderTargetView, it preserves the unfilled menu/race pixels.
    if (nativeOutputUploadDepth != 0u || !diagnostic_enabled() ||
        !env_full_game_opt_in() || !game || !destination ||
        FAILED(originalResult)) return false;
    try {
        D3DSURFACE_DESC desc{};
        if (FAILED(destination->GetDesc(&desc)) ||
            desc.Pool != D3DPOOL_DEFAULT || !desc.Width || !desc.Height ||
            (desc.Format != D3DFMT_A8R8G8B8 &&
             desc.Format != D3DFMT_X8R8G8B8)) return false;
        GameNativeSourceMutation::ColorFillRect clipped{};
        const auto coverage = rect
            ? GameNativeSourceMutation::classify_color_fill_rect(
                rect->left, rect->top, rect->right, rect->bottom,
                desc.Width, desc.Height, clipped)
            : GameNativeSourceMutation::ColorFillClip::Pixels;
        if (coverage == GameNativeSourceMutation::ColorFillClip::Invalid)
            return false;
        // A clipped rectangle may cover the whole game backbuffer; use the
        // existing full-RT clear path even without D3D11.1 ClearView.
        const bool wholeSurface = !rect ||
            (coverage == GameNativeSourceMutation::ColorFillClip::Pixels &&
             clipped.left == 0 && clipped.top == 0 &&
             clipped.right == desc.Width && clipped.bottom == desc.Height);
        ComPtr<IUnknown> surfaceIdentity;
        if (FAILED(destination->QueryInterface(
                IID_PPV_ARGS(surfaceIdentity.GetAddressOf()))) ||
            !surfaceIdentity) return false;
        State& s = state();
        std::lock_guard<std::mutex> lock(s.mutex);
        const auto owner = reinterpret_cast<std::uintptr_t>(game);
        const bool sameGameBackbuffer = s.clearColor.matches(
            owner, reinterpret_cast<std::uintptr_t>(surfaceIdentity.Get())) &&
            (s.sourceGameDevice == 0u || s.sourceGameDevice == owner);
        const bool alreadyDrawn = s.frameBatch.submitted != 0u;
        const bool targetReady = s.backend.ready() && s.backend.color_rtv() &&
            s.backend.context() && s.nativeWidth == desc.Width &&
            s.nativeHeight == desc.Height;
        if (rect && coverage == GameNativeSourceMutation::ColorFillClip::Empty)
            return sameGameBackbuffer && s.sourceGameDevice == owner &&
                   !s.frameBatch.stopped; // Successful original D3D9 no-op.
        if (!wholeSurface) {
            // Save successful pre-Draw partial fills so the initial native
            // full-resolution scene includes the same menu/vehicle background.
            // No native GPU command runs until the first actual game Draw.
            if (!alreadyDrawn) {
                return s.sourceGameDevice == owner && !s.frameBatch.stopped &&
                    sameGameBackbuffer && desc.Width <= 0x7fffffffu &&
                    desc.Height <= 0x7fffffffu && rect &&
                    s.preDrawFills.record(owner,
                        reinterpret_cast<std::uintptr_t>(surfaceIdentity.Get()),
                        rect->left, rect->top, rect->right, rect->bottom,
                        desc.Width, desc.Height, color);
            }
            // ClearView is optional on D3D11.0 hardware/runtime. Only mutate
            // the native target when every admission check passes, otherwise
            // retire the batch and leave the original D3D9 pixels untouched.
            if (!rect || !GameNativeSourceMutation::mirrors_partial_color_fill(
                    true, SUCCEEDED(originalResult), sameGameBackbuffer,
                    alreadyDrawn && s.pending && !s.frameBatch.stopped,
                    targetReady,
                    GameNativeSourceMutation::bounded_color_fill_rect(
                        clipped.left, clipped.top, clipped.right, clipped.bottom,
                        desc.Width, desc.Height)))
                return false;
            ComPtr<ID3D11DeviceContext1> context1;
            if (FAILED(s.backend.context()->QueryInterface(
                    IID_PPV_ARGS(context1.GetAddressOf()))) || !context1)
                return false;
            constexpr float scale = 1.0f / 255.0f;
            const float rgba[4] = {
                float((color >> 16) & 255u) * scale,
                float((color >> 8) & 255u) * scale,
                float(color & 255u) * scale,
                desc.Format == D3DFMT_X8R8G8B8 ? 1.0f :
                    float((color >> 24) & 255u) * scale
            };
            const D3D11_RECT nativeRect{
                static_cast<LONG>(clipped.left), static_cast<LONG>(clipped.top),
                static_cast<LONG>(clipped.right), static_cast<LONG>(clipped.bottom)};
            context1->ClearView(s.backend.color_rtv(), rgba, &nativeRect, 1u);
            // A partial ColorFill is not a new whole-frame clear baseline.
            // Keep the original full Clear seed, depth and Draw ordinals.
            return true;
        }
        const bool wholeTargetReady = !alreadyDrawn || targetReady;
        if (!GameNativeSourceMutation::mirrors_full_color_fill(
                true, SUCCEEDED(originalResult), sameGameBackbuffer,
                sameGameBackbuffer, true, !s.frameBatch.stopped,
                wholeTargetReady)) return false;
        s.preDrawFills.discard(); // whole ColorFill supersedes prior tiles
        s.clearColor.argb = color;
        s.clearColor.opaqueDestinationAlpha =
            desc.Format == D3DFMT_X8R8G8B8;
        if (alreadyDrawn) {
            const auto rgba = s.clearColor.native_color(
                owner, reinterpret_cast<std::uintptr_t>(surfaceIdentity.Get()),
                kBackground);
            s.backend.context()->ClearRenderTargetView(
                s.backend.color_rtv(), rgba.data());
        }
        return true;
    } catch (...) {
        return false; // Original D3D9 ColorFill and input always win.
    }
}

void observe_scene_boundary(IDirect3DDevice9* game) noexcept {
    if (!diagnostic_enabled() || !game) return;
    try {
        State& s = state();
        std::lock_guard<std::mutex> lock(s.mutex);
        // Only the device that supplied the game-authored native Draw owns
        // this batch. A menu/vehicle/race clear on a foreign auxiliary device
        // cannot invalidate an unrelated game source.
        const auto owner = reinterpret_cast<std::uintptr_t>(game);
        const bool ownsDraw = s.sourceGameDevice == owner &&
            s.frameBatch.submitted != 0u;
        // Prior to the first Draw, the full game TARGET Clear already owns
        // the scene. An intervening partial/unsupported successful Clear on
        // that device invalidates the seed even if no native Draw ran yet.
        const bool ownsPreDrawColor = env_full_game_opt_in() &&
            s.clearColor.valid && s.clearColor.sourceDevice == owner;
        if (!ownsDraw && !ownsPreDrawColor) return;
        s.frameBatch.scene_boundary();
        s.preDrawFills.discard();
        if (ownsPreDrawColor && s.frameBatch.submitted == 0u)
            s.frameBatch.abort();
        // A GPU Draw may already have run, but its stale color must never be
        // queued to the desktop backbuffer or host transport at Present.
        s.pending = false;
    } catch (...) {
        // Optional diagnostic code cannot interfere with D3D9 game/input.
    }
}

bool observe_game_depth_clear(IDirect3DDevice9* game, DWORD count,
                              const D3DRECT* rects, DWORD flags, float z) noexcept {
    // Stencil-only and combined Z|STENCIL game Clears do not affect native
    // color and need no native stencil translation: all admitted native game
    // Draws explicitly reject D3DRS_STENCILENABLE. Preserve the contiguous
    // main menu/vehicle/race frame only with proved same main Z/S identity.
    // A partial/foreign/unknown Clear still invalidates the native frame.
    constexpr DWORD kDepthStencilFlags = D3DCLEAR_ZBUFFER | D3DCLEAR_STENCIL;
    const bool clearZ = (flags & D3DCLEAR_ZBUFFER) != 0u;
    const bool clearStencil = (flags & D3DCLEAR_STENCIL) != 0u;
    if (!diagnostic_enabled() || !env_full_game_opt_in() || !game ||
        (flags & kDepthStencilFlags) == 0u ||
        (flags & ~kDepthStencilFlags) != 0u ||
        (clearZ && !(z >= 0.0f && z <= 1.0f))) return false;
    try {
        State& s = state();
        std::lock_guard<std::mutex> lock(s.mutex);
        const auto owner = reinterpret_cast<std::uintptr_t>(game);
        // A full original TARGET Clear can precede a separate Z-only Clear
        // before the first game-authored Draw; that is a valid native DSV seed.
        // Keep the existing post-Draw depth-only continuation unchanged.
        if (s.sourceGameDevice != 0u && s.sourceGameDevice != owner) return false;
        const bool continuingFullNativeDraw = s.sourceGameDevice == owner &&
            s.pending && s.frameBatch.submitted != 0u;
        ComPtr<IDirect3DSurface9> target, backbuffer, depth;
        D3DSURFACE_DESC rtDesc{}, bbDesc{}, dsDesc{};
        D3DVIEWPORT9 vp{};
        if (FAILED(game->GetRenderTarget(0, target.GetAddressOf())) || !target ||
            FAILED(game->GetBackBuffer(0, 0, D3DBACKBUFFER_TYPE_MONO,
                                      backbuffer.GetAddressOf())) || !backbuffer ||
            FAILED(game->GetDepthStencilSurface(depth.GetAddressOf())) || !depth ||
            FAILED(target->GetDesc(&rtDesc)) ||
            FAILED(backbuffer->GetDesc(&bbDesc)) ||
            FAILED(depth->GetDesc(&dsDesc)) ||
            FAILED(game->GetViewport(&vp))) return false;
        ComPtr<IUnknown> targetIdentity, backbufferIdentity;
        if (FAILED(target.As(&targetIdentity)) ||
            FAILED(backbuffer.As(&backbufferIdentity)) ||
            !targetIdentity || !backbufferIdentity ||
            targetIdentity.Get() != backbufferIdentity.Get() ||
            rtDesc.Width != bbDesc.Width || rtDesc.Height != bbDesc.Height ||
            dsDesc.Width != bbDesc.Width || dsDesc.Height != bbDesc.Height ||
            bbDesc.MultiSampleType != D3DMULTISAMPLE_NONE ||
            dsDesc.MultiSampleType != D3DMULTISAMPLE_NONE) return false;
        // Original successful D3D9 STENCIL-only Clears cannot affect native
        // color/Z (admitted native game Draws never read stencil). Cropped
        // stencil rectangles may therefore preserve menu-to-race continuity.
        // A Z Clear must still cover the entire native depth surface.
        const bool coversDepth = GameNativeClearCoverage::covers_whole(
            bbDesc.Width, bbDesc.Height, vp.X, vp.Y, vp.Width, vp.Height,
            count, rects);
        const bool compatibleCoverage =
            GameNativeMainStencilClear::preserves_clear_coverage(clearZ, coversDepth);
        // Same RT0 does not imply same Z. Menu/vehicle previews may bind an
        // auxiliary Z surface while restoring the game main backbuffer.
        ComPtr<IUnknown> depthIdentity;
        if (FAILED(depth.As(&depthIdentity)) || !depthIdentity) return false;
        const bool sameMainDepthStencil = s.clearColor.main_depth_still_bound(
            reinterpret_cast<std::uintptr_t>(depthIdentity.Get()));
        const bool partialDepth = clearZ && !coversDepth;
        if (!sameMainDepthStencil ||
            (clearZ && !compatibleCoverage && !partialDepth))
            return false;
        if (clearStencil &&
            !GameNativeMainStencilClear::may_ignore(
                true, s.clearColor.matches(owner,
                    reinterpret_cast<std::uintptr_t>(backbufferIdentity.Get())),
                sameMainDepthStencil, compatibleCoverage,
                !s.frameBatch.stopped))
            return false;
        // D3D9 supports viewport-scissored Z Clears during a live menu/race
        // frame. D3D11 ClearDepthStencilView would erase *all* prior depth:
        // use D3D11.1 ClearView on our D32_FLOAT-only DSV instead. Verify
        // every rectangle before mutating the GPU. No native depth owner or
        // D3D11.0-only context means unchanged DX9Ex and batch retirement.
        if (partialDepth) {
            if (clearStencil || !continuingFullNativeDraw ||
                !GameNativeSourceMutation::mirrors_partial_depth_clear(
                    env_full_game_opt_in(), sameMainDepthStencil,
                    s.pending && !s.frameBatch.stopped &&
                        s.frameBatch.submitted != 0u,
                    s.frameBatch.depthReady,
                    native_game_partial_depth_ready(s, game, bbDesc.Width, bbDesc.Height),
                    s.backend.context() != nullptr) ||
                count > GameNativeSourceMutation::kMaxPartialTargetClearRects ||
                (count != 0u && !rects))
                return false;
            std::array<D3D11_RECT,
                GameNativeSourceMutation::kMaxPartialTargetClearRects> regions{};
            const std::uint32_t n = count ? count : 1u;
            std::uint32_t used = 0u;
            for (std::uint32_t i = 0u; i < n; ++i) {
                const std::int64_t l = count ? rects[i].x1 : vp.X;
                const std::int64_t t = count ? rects[i].y1 : vp.Y;
                const std::int64_t r = count ? rects[i].x2 :
                    static_cast<std::int64_t>(vp.X) + vp.Width;
                const std::int64_t b = count ? rects[i].y2 :
                    static_cast<std::int64_t>(vp.Y) + vp.Height;
                GameNativeSourceMutation::TargetClearRect clipped{};
                const auto kind = GameNativeSourceMutation::classify_target_clear_rect(
                    l, t, r, b, vp.X, vp.Y, vp.Width, vp.Height,
                    bbDesc.Width, bbDesc.Height, clipped);
                if (kind == GameNativeSourceMutation::TargetClearClip::Invalid)
                    return false;
                if (kind == GameNativeSourceMutation::TargetClearClip::Empty)
                    continue;
                regions[used++] = {
                    static_cast<LONG>(clipped.left), static_cast<LONG>(clipped.top),
                    static_cast<LONG>(clipped.right), static_cast<LONG>(clipped.bottom)};
            }
            if (used == 0u) return true;
            ComPtr<ID3D11DeviceContext1> context1;
            if (FAILED(s.backend.context()->QueryInterface(
                    IID_PPV_ARGS(context1.GetAddressOf()))) || !context1)
                return false;
            const float depthValue[4] = {z, 0.0f, 0.0f, 0.0f};
            context1->ClearView(s.diagnosticDepthView.Get(), depthValue,
                                regions.data(), used);
            return true; // Keep RTV, previously drawn Z and source ordinals.
        }
        // Prove the same canonical D3D9 backbuffer/color Clear before
        // admitting a separate full Z Clear with zero native game Draws.
        // This covers menu->vehicle->race startup where TARGET and ZBUFFER
        // are cleared by separate successful game calls.
        const bool beforeFirstGameDraw = !s.pending &&
            s.frameBatch.can_seed_pre_draw_depth(
                s.clearColor.matches(owner, reinterpret_cast<std::uintptr_t>(
                    backbufferIdentity.Get())),
                s.sourceDrawsThisFrame == 0u);
        if ((s.frameBatch.submitted == 0u || s.frameBatch.stopped) &&
            !beforeFirstGameDraw) return false;
        if (s.frameBatch.submitted != 0u && !continuingFullNativeDraw)
            return false;
        // The next real native depth Draw clears the DSV to the exact game
        // Z while keeping the native RTV color; DX9Ex/input are untouched.
        // Stencil-only Clear does not modify the native DSV depth. Combined
        // Z|STENCIL must still seed the native depth with the exact game z.
        if (clearZ) s.frameBatch.note_full_depth_clear(z);
        return true;
    } catch (...) {
        return false; // Never change original game Draw/Present/gamepad.
    }
}

void observe_game_clear(IDirect3DDevice9* game, DWORD count,
                        const D3DRECT* rects, DWORD flags, D3DCOLOR color, float z) noexcept {
    if (!diagnostic_enabled() || !game || !(flags & D3DCLEAR_TARGET)) return;
    // The original successful offscreen TARGET-only Clear cannot erase the
    // canonical game backbuffer. Keep its verified color seed for the next
    // contiguous menu/vehicle/race Draw, including an already active batch.
    // The Clear hook has skipped scene_boundary only for this exact case.
    if (preserve_offscreen_color_only_clear(game, flags)) return;
    try {
        State& s = state();
        std::lock_guard<std::mutex> lock(s.mutex);
        const auto sourceDevice = reinterpret_cast<std::uintptr_t>(game);
        const bool foreignSource = s.sourceGameDevice != 0u &&
            s.sourceGameDevice != sourceDevice;
        if (foreignSource && !env_full_game_opt_in()) return;
        // The previous owner's seed survives an unverified foreign Clear;
        // the real owner still invalidates its own old seed immediately.
        // Only a successful whole-backbuffer Clear may rebind ownership.
        if (!foreignSource) {
            s.clearColor.discard();
            s.preDrawFills.discard();
        }
        ComPtr<IDirect3DSurface9> target, backbuffer;
        D3DSURFACE_DESC targetDesc{}, bbDesc{};
        D3DVIEWPORT9 viewport{};
        if (FAILED(game->GetRenderTarget(0, target.GetAddressOf())) || !target ||
            FAILED(game->GetBackBuffer(0, 0, D3DBACKBUFFER_TYPE_MONO,
                                       backbuffer.GetAddressOf())) || !backbuffer ||
            FAILED(target->GetDesc(&targetDesc)) ||
            FAILED(backbuffer->GetDesc(&bbDesc)) ||
            FAILED(game->GetViewport(&viewport))) return;
        ComPtr<IUnknown> targetIdentity, backbufferIdentity;
        if (FAILED(target.As(&targetIdentity)) ||
            FAILED(backbuffer.As(&backbufferIdentity)) || !targetIdentity ||
            !backbufferIdentity) return;
        const bool wholeBackbuffer = targetIdentity.Get() == backbufferIdentity.Get() &&
            targetDesc.Width == bbDesc.Width && targetDesc.Height == bbDesc.Height &&
            viewport.X == 0u && viewport.Y == 0u &&
            viewport.Width == bbDesc.Width && viewport.Height == bbDesc.Height &&
            GameNativeClearCoverage::covers_whole(
                bbDesc.Width, bbDesc.Height, viewport.X, viewport.Y,
                viewport.Width, viewport.Height, count, rects) &&
            bbDesc.MultiSampleType == D3DMULTISAMPLE_NONE &&
            (bbDesc.Format == D3DFMT_A8R8G8B8 || bbDesc.Format == D3DFMT_X8R8G8B8);
        const bool sourceReacquired = GameNativeFrameBatch::can_reacquire_full_clear(
            sourceDevice, s.sourceGameDevice, env_full_game_opt_in(),
            wholeBackbuffer, s.frameBatch.submitted != 0u, s.pending);
        if (foreignSource && !sourceReacquired) return;
        if (foreignSource) {
            s.clearColor.discard();
            s.preDrawFills.discard();
        }
        std::uintptr_t mainDepthIdentity = 0u;
        if (wholeBackbuffer) {
            ComPtr<IDirect3DSurface9> mainDepth;
            ComPtr<IUnknown> canonicalDepth;
            if (SUCCEEDED(game->GetDepthStencilSurface(mainDepth.GetAddressOf())) &&
                mainDepth && SUCCEEDED(mainDepth.As(&canonicalDepth)) && canonicalDepth)
                mainDepthIdentity = reinterpret_cast<std::uintptr_t>(canonicalDepth.Get());
        }
        s.clearColor.record(sourceDevice,
            reinterpret_cast<std::uintptr_t>(backbufferIdentity.Get()),
            static_cast<std::uint32_t>(color), wholeBackbuffer,
            bbDesc.Format == D3DFMT_X8R8G8B8, mainDepthIdentity);
        if (wholeBackbuffer && env_full_game_opt_in()) {
            if (sourceReacquired || s.sourceGameDevice == 0u) {
                // Genuine full game Clear starts a new native source epoch.
                // Invalidate any readback from an auxiliary/older Present.
                s.sourceGameDevice = sourceDevice;
                if (++s.outputGeneration == 0u) ++s.outputGeneration;
            }
            // Original successful whole Clear makes earlier menu/offscreen
            // Draws invisible. Restart source continuity at the first real
            // post-Clear Draw/DrawIndexed on this SAME game device/Present.
            // Never revive a batch after a partial or foreign Clear.
            s.frameBatch.reset();
            s.cpuSurfaceReplay.reset();
            s.surfaceReplayCount = 0u; // a new verified full Clear starts a new source epoch
            s.pending = false;
            s.sourceDrawsThisFrame = 0u;
    s.sourceModeKnown = false;
            s.eligibleThisFrame = 0u;
            // After a successful full TARGET|ZBUFFER game Clear, initialize
            // the first native Draw's DSV from the game's actual Z value.
            // Without depth COM/extent compatibility, retain DX9Ex fallback.
            if ((flags & (D3DCLEAR_ZBUFFER | D3DCLEAR_STENCIL)) != 0u) {
                ComPtr<IDirect3DSurface9> depth;
                D3DSURFACE_DESC depthDesc{};
                const bool depthMatches =
                    SUCCEEDED(game->GetDepthStencilSurface(depth.GetAddressOf())) &&
                    depth && SUCCEEDED(depth->GetDesc(&depthDesc)) &&
                    depthDesc.Width == bbDesc.Width &&
                    depthDesc.Height == bbDesc.Height &&
                    depthDesc.MultiSampleType == D3DMULTISAMPLE_NONE;
                // TARGET|STENCIL and TARGET|Z|STENCIL can seed the exact
                // menu/race main color frame because the native fixed-function
                // path never admits stencil-tested/writing Draws. Prove the
                // owner, canonical main Z/S identity and matching size first.
                // When Z is not cleared, do not fabricate a native Z Clear.
                const bool clearZ = (flags & D3DCLEAR_ZBUFFER) != 0u;
                const bool clearStencil = (flags & D3DCLEAR_STENCIL) != 0u;
                const bool ignoreStencil = clearStencil &&
                    GameNativeMainStencilClear::may_ignore(
                        env_full_game_opt_in(), wholeBackbuffer,
                        mainDepthIdentity != 0u, depthMatches,
                        !s.frameBatch.stopped);
                if ((clearStencil && !ignoreStencil) ||
                    (clearZ && !GameNativeFullColorDepthClear::can_mirror(
                        true, false, depthMatches, z))) {
                    s.frameBatch.abort(); // failed proof: original D3D9 lives
                } else if (clearZ) {
                    s.frameBatch.note_full_depth_clear(z);
                }
            }
        }
    } catch (...) {
        // D3D9 Clear, input and Present always remain authoritative.
    }
}

void observe_unavailable_game_draw(IDirect3DDevice9* game) noexcept {
    if (!diagnostic_enabled() || !game) return;
    try {
        State& s = state();
        std::lock_guard<std::mutex> lock(s.mutex);
        // Unavailable game draws must obey the same D3D9 device boundary as
        // native-admitted draws; no unrelated source may bridge a scene.
        if (!observe_source_device(s, game)) return;
        // VB/IB Lock shadow miss or an unsupported IndexedUP source must not
        // disappear from the original game's Draw/DrawIndexed ordinal stream.
        if (s.sourceDrawsThisFrame == (std::numeric_limits<std::uint64_t>::max)()) {
            s.frameBatch.abort();
            return;
        }
        const std::uint64_t sourceOrdinal = s.sourceDrawsThisFrame++;
        ++s.observed;
        const bool fullMode = env_full_game_opt_in();
        if (!observe_source_frame_mode(s, fullMode)) return;
        // An unavailable VB/IB shadow still represents a successful game
        // Draw/DrawIndexed. If its enabled scissor excludes the entire game
        // viewport, it cannot change color, Z or stencil. Preserve that exact
        // source ordinal so following native menu/car/race draws can publish;
        // an overlapping or unproved scissor must retain D3D9 fallback.
        if (fullMode) {
            DWORD scissorEnabled = FALSE;
            if (SUCCEEDED(game->GetRenderState(D3DRS_SCISSORTESTENABLE,
                                               &scissorEnabled)) &&
                scissorEnabled == TRUE) {
                D3DVIEWPORT9 sourceViewport{};
                RECT sourceScissor{};
                if (SUCCEEDED(game->GetViewport(&sourceViewport)) &&
                    SUCCEEDED(game->GetScissorRect(&sourceScissor)) &&
                    GameNativeScissorClip::excludes_viewport(
                        sourceViewport.X, sourceViewport.Y,
                        sourceViewport.Width, sourceViewport.Height,
                        sourceScissor.left, sourceScissor.top,
                        sourceScissor.right, sourceScissor.bottom)) {
                    const bool sameSourceFullClear = s.clearColor.valid &&
                        s.clearColor.sourceDevice ==
                            reinterpret_cast<std::uintptr_t>(game);
                    if (!s.frameBatch.absorb_empty_source_draw(
                            sourceOrdinal, sameSourceFullClear))
                        s.frameBatch.abort();
                    return;
                }
            }
        }
        // A VB/IB shadow miss during an isolated offscreen texture pass does
        // not imply an invisible gap in the real backbuffer's Draw stream.
        if (fullMode && isolated_offscreen_game_draw(game, s)) {
            const bool sameSourceFullClear = s.clearColor.valid &&
                s.clearColor.sourceDevice == reinterpret_cast<std::uintptr_t>(game);
            if (!s.frameBatch.absorb_empty_source_draw(
                    sourceOrdinal, sameSourceFullClear))
                s.frameBatch.abort();
            return;
        }
        // Missing VB/IB shadows are not a visual gap when the actual D3D9
        // command cannot write RT0, any MRT, Z or stencil. Preserve this
        // unavailable Draw/DrawIndexed ordinal just like a supported
        // pixel-neutral source call; all unproved writers still abort.
        if (fullMode && proven_game_draw_no_target_writes(game, s)) {
            const bool sameSourceFullClear = s.clearColor.valid &&
                s.clearColor.sourceDevice ==
                    reinterpret_cast<std::uintptr_t>(game);
            if (!s.frameBatch.absorb_empty_source_draw(
                    sourceOrdinal, sameSourceFullClear))
                s.frameBatch.abort();
            return;
        }
        if (s.frameBatch.must_abort_unsupported(fullMode, env_batch_opt_in()))
            s.frameBatch.abort();
    } catch (...) {
        // Diagnostics cannot change the game's render or gamepad behavior.
    }
}

void observe_failed_game_draw(IDirect3DDevice9* game) noexcept {
    if (!diagnostic_enabled() || !game) return;
    try {
        State& s = state();
        std::lock_guard<std::mutex> lock(s.mutex);
        // R30 has already observed this exact source call. A failed native
        // source Draw cannot become a visible successful D3D9 menu/race Draw.
        // Do not increment its ordinal twice or affect a foreign game device.
        if (s.sourceGameDevice != reinterpret_cast<std::uintptr_t>(game)) return;
        s.frameBatch.abort();
        s.pending = false;
    } catch (...) {
        // Original game HRESULT, drawing and controller input win.
    }
}

void before_game_present(IDirect3DDevice9* game,
                         const RECT* sourceRect, const RGNDATA* dirtyRegion) noexcept {
    if (!diagnostic_enabled() || !game) return;
    try {
        State& s = state();
        std::lock_guard<std::mutex> lock(s.mutex);
        const auto presentDevice = reinterpret_cast<std::uintptr_t>(game);
        // The x86 game can Present an auxiliary/menu D3D9 device between
        // game-authored Draw and its owner's Present. Ignore that Present
        // entirely: it must not rotate the game source probe, retire a native
        // readback or replace the owner's output generation.
        if (GameNativeFrameBatch::foreign_present(
                s.sourceGameDevice,
                s.previousOutput.valid() ? s.previousOutput.device : 0u,
                presentDevice)) return;
        ComPtr<IDirect3DSurface9> presentBackbuffer;
        D3DSURFACE_DESC presentDesc{};
        ComPtr<IUnknown> presentBackbufferIdentity;
        const bool backbufferKnown = SUCCEEDED(game->GetBackBuffer(
            0, 0, D3DBACKBUFFER_TYPE_MONO, presentBackbuffer.GetAddressOf())) &&
            presentBackbuffer && SUCCEEDED(presentBackbuffer->GetDesc(&presentDesc)) &&
            SUCCEEDED(presentBackbuffer.As(&presentBackbufferIdentity)) &&
            presentBackbufferIdentity;
        GameOutputSignature outputNow = backbufferKnown
            ? GameOutputSignature{presentDevice, presentDesc.Width, presentDesc.Height,
                                  static_cast<std::uint32_t>(presentDesc.Format),
                                  reinterpret_cast<std::uintptr_t>(
                                      presentBackbufferIdentity.Get())}
            : GameOutputSignature{};
        const bool fullMode = env_full_game_opt_in();
        outputNow.nativeFullFrame = fullMode;
        // D3D9 can crop Present during menu, car selection and race transitions.
        // An UpdateSurface into the backbuffer is not proof of a visible inset
        // unless the *actual source rectangle* includes all native pixels.
        const GameNativePresentRegion presentRegion{
            sourceRect ? static_cast<std::int64_t>(sourceRect->left) : 0,
            sourceRect ? static_cast<std::int64_t>(sourceRect->top) : 0,
            sourceRect ? static_cast<std::int64_t>(sourceRect->right)
                       : static_cast<std::int64_t>(presentDesc.Width),
            sourceRect ? static_cast<std::int64_t>(sourceRect->bottom)
                       : static_cast<std::int64_t>(presentDesc.Height)};
        // Generation tracks the exact crop and dirty-region mode, not only
        // backbuffer identity. A late GPU readback from a prior scene/crop
        // must never be overlaid on the next Present's game output.
        outputNow.sourceLeft = presentRegion.left;
        outputNow.sourceTop = presentRegion.top;
        outputNow.sourceRight = presentRegion.right;
        outputNow.sourceBottom = presentRegion.bottom;
        outputNow.hasDirtyRegion = dirtyRegion != nullptr;
        // Some D3D9 Present calls explicitly mark the *entire* source
        // backbuffer dirty. Preserve full-frame native menu/race output in
        // that supported case, but never overlay a partially dirty D3D9
        // frame or an unbounded/malformed region. Insets remain conservative.
        RECT dirtyRect{};
        const bool oneBoundedDirtyRect = dirtyRegion &&
            dirtyRegion->rdh.dwSize == sizeof(RGNDATAHEADER) &&
            dirtyRegion->rdh.iType == RDH_RECTANGLES &&
            dirtyRegion->rdh.nCount == 1u &&
            dirtyRegion->rdh.nRgnSize >= sizeof(RECT);
        if (oneBoundedDirtyRect)
            std::memcpy(&dirtyRect, dirtyRegion->Buffer, sizeof(dirtyRect));
        // D3D9 can also describe a complete menu/car/race repaint as several
        // disjoint dirty rectangles. Verify exact, nonoverlapping full coverage
        // before native publication, never use a full rcBound as proof by itself.
        // Inspect at most 32 RECTs with verified header/buffer extents.
        GameNativeDirtyRectangle partitionRects[
            GameNativeDirtyRegionCoverage::kMaxPartitionRects]{};
        const bool boundedPartition = fullMode && backbufferKnown && dirtyRegion &&
            dirtyRegion->rdh.dwSize == sizeof(RGNDATAHEADER) &&
            dirtyRegion->rdh.iType == RDH_RECTANGLES &&
            dirtyRegion->rdh.nCount >= 2u &&
            dirtyRegion->rdh.nCount <= GameNativeDirtyRegionCoverage::kMaxPartitionRects &&
            dirtyRegion->rdh.nRgnSize >= dirtyRegion->rdh.nCount * sizeof(RECT);
        if (boundedPartition) {
            for (std::uint32_t i = 0u; i < dirtyRegion->rdh.nCount; ++i) {
                RECT part{};
                std::memcpy(&part, dirtyRegion->Buffer + i * sizeof(RECT), sizeof(part));
                partitionRects[i] = {part.left, part.top, part.right, part.bottom};
            }
        }
        const bool fullDirtyCoverage = fullMode && backbufferKnown && dirtyRegion &&
            ((oneBoundedDirtyRect &&
              GameNativeDirtyRegionCoverage::covers_full_backbuffer(
                  presentDesc.Width, presentDesc.Height,
                  dirtyRegion->rdh.nCount, dirtyRegion->rdh.nRgnSize,
                  dirtyRegion->rdh.rcBound.left, dirtyRegion->rdh.rcBound.top,
                  dirtyRegion->rdh.rcBound.right, dirtyRegion->rdh.rcBound.bottom,
                  dirtyRect.left, dirtyRect.top, dirtyRect.right, dirtyRect.bottom)) ||
             (boundedPartition &&
              (GameNativeDirtyRegionCoverage::covers_partition(
                  presentDesc.Width, presentDesc.Height,
                  dirtyRegion->rdh.nCount, dirtyRegion->rdh.nRgnSize,
                  dirtyRegion->rdh.rcBound.left, dirtyRegion->rdh.rcBound.top,
                  dirtyRegion->rdh.rcBound.right, dirtyRegion->rdh.rcBound.bottom,
                  partitionRects) ||
               GameNativeDirtyRegionCoverage::covers_complete_union(
                   presentDesc.Width, presentDesc.Height,
                   dirtyRegion->rdh.nCount, dirtyRegion->rdh.nRgnSize,
                   0, 0, presentDesc.Width, presentDesc.Height,
                   dirtyRegion->rdh.rcBound.left, dirtyRegion->rdh.rcBound.top,
                   dirtyRegion->rdh.rcBound.right, dirtyRegion->rdh.rcBound.bottom,
                   partitionRects))));
        // A cropped menu/car/race Present may dirty its *entire visible*
        // source RECT without dirtying the rest of the physical backbuffer.
        // Publish only inside that crop; never replace untouched D3D9 pixels.
        const bool cropDirtyCoverage = fullMode && backbufferKnown &&
            oneBoundedDirtyRect &&
            GameNativeDirtyRegionCoverage::covers_present_crop(
                presentDesc.Width, presentDesc.Height,
                dirtyRegion->rdh.nCount, dirtyRegion->rdh.nRgnSize,
                presentRegion.left, presentRegion.top,
                presentRegion.right, presentRegion.bottom,
                dirtyRegion->rdh.rcBound.left, dirtyRegion->rdh.rcBound.top,
                dirtyRegion->rdh.rcBound.right, dirtyRegion->rdh.rcBound.bottom,
                dirtyRect.left, dirtyRect.top, dirtyRect.right, dirtyRect.bottom);
        // A tiled source crop is publishable only when every visible pixel is
        // covered once. Partial menus, overlaps and invalid region metadata
        // continue through untouched D3D9 drawing, Present and input.
        const bool partitionCropCoverage = fullMode && backbufferKnown &&
            boundedPartition &&
            (GameNativeDirtyRegionCoverage::covers_partition_crop(
                presentDesc.Width, presentDesc.Height,
                dirtyRegion->rdh.nCount, dirtyRegion->rdh.nRgnSize,
                presentRegion.left, presentRegion.top,
                presentRegion.right, presentRegion.bottom,
                dirtyRegion->rdh.rcBound.left, dirtyRegion->rdh.rcBound.top,
                dirtyRegion->rdh.rcBound.right, dirtyRegion->rdh.rcBound.bottom,
                partitionRects) ||
             (presentRegion.partial_backbuffer_source(
                  presentDesc.Width, presentDesc.Height) &&
              GameNativeDirtyRegionCoverage::covers_complete_union(
                  presentDesc.Width, presentDesc.Height,
                  dirtyRegion->rdh.nCount, dirtyRegion->rdh.nRgnSize,
                  presentRegion.left, presentRegion.top,
                  presentRegion.right, presentRegion.bottom,
                  dirtyRegion->rdh.rcBound.left, dirtyRegion->rdh.rcBound.top,
                  dirtyRegion->rdh.rcBound.right, dirtyRegion->rdh.rcBound.bottom,
                  partitionRects)));
        // A cropped D3D9 menu/vehicle/race Present only exposes its source
        // rectangle. Native pixels outside it must never replace D3D9 pixels,
        // even when the dirty region is absent or covers the whole backbuffer.
        // An explicitly cropped dirty region still needs complete tile proof.
        const bool provenCroppedDirty =
            (cropDirtyCoverage || partitionCropCoverage) && !fullDirtyCoverage;
        const bool croppedNativeUpload = fullMode && backbufferKnown &&
            presentRegion.partial_backbuffer_source(presentDesc.Width, presentDesc.Height) &&
            (!dirtyRegion || fullDirtyCoverage || provenCroppedDirty);
        // A verified single partial dirty region carries a complete native
        // game frame only into pixels visible in D3D9 Present's source crop.
        const auto partialDirty = GameNativePartialDirtyUpload::select(
            presentDesc.Width, presentDesc.Height, presentRegion,
            oneBoundedDirtyRect ? dirtyRegion->rdh.nCount : 0u,
            oneBoundedDirtyRect ? dirtyRegion->rdh.nRgnSize : 0u,
            oneBoundedDirtyRect ? dirtyRegion->rdh.rcBound.left : 0,
            oneBoundedDirtyRect ? dirtyRegion->rdh.rcBound.top : 0,
            oneBoundedDirtyRect ? dirtyRegion->rdh.rcBound.right : 0,
            oneBoundedDirtyRect ? dirtyRegion->rdh.rcBound.bottom : 0,
            dirtyRect.left, dirtyRect.top, dirtyRect.right, dirtyRect.bottom);
        const bool partialNativeUpload = fullMode && backbufferKnown &&
            oneBoundedDirtyRect && !fullDirtyCoverage && !croppedNativeUpload &&
            partialDirty.valid;
        // Partially dirty game tiles, including overlaps, are copied from one
        // native frame into D3D9-backbuffer-seeded SYSTEMMEM. Their single
        // bounded upload preserves all untouched original D3D9 pixels.
        const auto multiDirty = GameNativeMultiDirtyUpload::select(
            presentDesc.Width, presentDesc.Height, presentRegion,
            boundedPartition ? dirtyRegion->rdh.nCount : 0u,
            boundedPartition ? dirtyRegion->rdh.nRgnSize : 0u,
            boundedPartition ? dirtyRegion->rdh.rcBound.left : 0,
            boundedPartition ? dirtyRegion->rdh.rcBound.top : 0,
            boundedPartition ? dirtyRegion->rdh.rcBound.right : 0,
            boundedPartition ? dirtyRegion->rdh.rcBound.bottom : 0,
            boundedPartition ? partitionRects : nullptr,
            true /* overlapping game dirty tiles are identical native pixels */);
        const bool multiNativeUpload = fullMode && backbufferKnown &&
            !fullDirtyCoverage && !croppedNativeUpload &&
            multiDirty.valid;
        if (!s.previousOutput.same(outputNow)) {
            // Also reject earlier GPU readbacks if the Present backbuffer COM identity
            // changed while the device, dimensions and format stayed identical.
            // Retire the previous upload surface and advance the GPU generation.
            s.previousOutput = outputNow;
            s.sharedDesktop.reset();
            s.cpuUploadRollback.reset();
            s.insetSurface.Reset();
            s.insetFormat = D3DFMT_UNKNOWN;
            s.insetSurfaceDevice = 0u;
    s.insetSurfaceWidth = s.insetSurfaceHeight = 0u;
            if (++s.outputGeneration == 0u) ++s.outputGeneration;
        }
        // Reuse the inspected game backbuffer for bounds proof and D3D9 upload.
        const auto& bb = presentDesc;
        // Place the inset inside the actual Present source, rather than always
        // at the backbuffer's top-right (which cropped menus may not show).
        // Only a full-size native frame can cover a full D3D9 Present.
        const UINT surfaceWidth = fullMode ? s.nativeWidth : kWidth;
        const UINT surfaceHeight = fullMode ? s.nativeHeight : kHeight;
        const bool nativeExtentMatches = !fullMode ||
            (surfaceWidth == bb.Width && surfaceHeight == bb.Height &&
             bb.Width != 0u && bb.Height != 0u);
        const auto insetPlacement = presentRegion.inset_placement(
            bb.Width, bb.Height, surfaceWidth, surfaceHeight, fullMode ? 0u : 8u);
        // A source-RECT crop changes what Present reveals, not where the
        // full-resolution native pixels belong in the original backbuffer.
        // Preserve the inset-only placement for the smaller debug output.
        const auto fullPlacement = presentRegion.full_frame_placement(
            bb.Width, bb.Height, surfaceWidth, surfaceHeight);
        // The native mono color buffer is not the R9 game left eye: the D3D9
        // stereo pipeline writes two distinct cameras AFTER the native mirror
        // sampled the original D3D9 game Draw. A mono full-game upload here
        // overwrote the game's true left view just before R13/R32 captured
        // left/right GPU eyes. Fail closed to the original game-owned stereo
        // backbuffer instead of allowing mismatched VR eyes or fabricated IPD.
        const bool outputWritable = monoNativePublicationAllowed &&
            outputNow.valid() && nativeExtentMatches &&
            (((!outputNow.hasDirtyRegion || fullDirtyCoverage) &&
              (fullMode ? fullPlacement.valid : insetPlacement.valid)) ||
             (croppedNativeUpload && fullPlacement.valid) ||
             (partialNativeUpload && fullPlacement.valid) ||
             (multiNativeUpload && fullPlacement.valid)) &&
            bb.MultiSampleType == D3DMULTISAMPLE_NONE &&
            (bb.Format == D3DFMT_A8R8G8B8 ||
             bb.Format == D3DFMT_X8R8G8B8);
        // A ready asynchronous full-screen GPU copy belongs to an earlier
        // Present. It must not replace today's D3D9 menu, car-selection or
        // race fallback when any *current* game Draw was unsupported, aborted
        // or cleared. Invalidate the entire queued provenance generation,
        // including copies whose GPU fences are not ready yet. Insets may
        // still show their bounded, diagnostic delayed sample.
        if (!GameNativeFramePublication::source_mode_contiguous(
                s.sourceModeKnown, s.sourceWasFullMode, fullMode)) {
            s.frameBatch.abort();
            s.pending = false;
        }
        if (s.cpuSurfaceReplay.active()) {
            s.frameBatch.abort();
            s.pending = false; // original Present stays authoritative
        }
        const bool currentFullFrameComplete =
            s.frameBatch.publishable_full(s.pending, s.sourceDrawsThisFrame) &&
            s.sourceGameDevice == presentDevice;
        if (GameReadbackProvenance::quarantine_full_frame(
                fullMode, currentFullFrameComplete, outputWritable)) {
            if (++s.outputGeneration == 0u) ++s.outputGeneration;
        }
        const bool complete = fullMode
            ? currentFullFrameComplete
            : s.frameBatch.publishable(s.pending);
        if (s.backend.ready() && s.backend.context()) {
            auto* ctx = s.backend.context();
            // Native GPU copy handoff operates on the actual *complete*
            // menu/car/race Draw output before staging to CPU/D3D9. A sink
            // must record any GPU CopyResource synchronously on this same
            // immediate context; original D3D9 Draw/input remain intact.
            bool gpuHandoffQueued = false;
            // This synchronous native D3D11 GPU consumer does not touch the
            // D3D9 backbuffer. Unlike CPU staging / UpdateSurface and the
            // shared-desktop fallback below, it needs no writable D3D9 format,
            // non-MSAA D3D9 surface or CPU dirty-tile upload. It DOES require
            // a real complete native game frame at the current Present,
            // matching output geometry, and an allowed mono publication scope.
            const bool gpuOutputAdmissible = GameNativeGpuHandoff::gpu_frame_output_ready(
                monoNativePublicationAllowed,
                backbufferKnown && outputNow.valid(),
                nativeExtentMatches, fullPlacement.valid);
            if (GameNativeGpuHandoff::may_offer(
                    fullMode, complete, gpuOutputAdmissible,
                    s.sourceGameDevice == presentDevice,
                    s.backend.color_texture() != nullptr,
                    s.gpuFrameSink != nullptr,
                    surfaceWidth, surfaceHeight, s.outputGeneration)) {
                const NativeFullGameGpuFrame frame{
                    ctx, s.backend.color_texture(), surfaceWidth, surfaceHeight,
                    s.presents, s.sourceDrawsThisFrame, s.outputGeneration};
                gpuHandoffQueued = s.gpuFrameSink(s.gpuFrameSinkUser, frame);
            }
            // Optional real GPU-only desktop presentation, without staging
            // D3D11 pixels through system memory. Require an actual D3D9Ex
            // game device and complete source coverage; failed imports, GPU
            // fences or StretchRect keep the original game/CPU path intact.
            // Stereo XR remains separately provenance-gated (never copy mono
            // to both eyes).
            const auto sharedDesktopRegion = NativeSharedDesktopAdmission::select_region(
                presentDesc.Width, presentDesc.Height, presentRegion,
                dirtyRegion != nullptr, oneBoundedDirtyRect, fullDirtyCoverage,
                cropDirtyCoverage, partitionCropCoverage, partialDirty);
            const auto sharedMultiDesktop = NativeSharedDesktopAdmission::select_multi_regions(
                presentDesc.Width, presentDesc.Height, presentRegion,
                dirtyRegion != nullptr, fullDirtyCoverage, cropDirtyCoverage,
                partitionCropCoverage, multiDirty);
            const bool sharedDesktopAllowed = NativeSharedDesktopAdmission::allowed(
                env_shared_desktop_opt_in(), fullMode, complete, outputWritable,
                s.sourceGameDevice == presentDevice,
                sharedDesktopRegion.valid || sharedMultiDesktop.valid,
                sharedDesktopRegion.valid || sharedMultiDesktop.valid,
                NativeSharedDesktopAdmission::destination_compatible(
                    static_cast<std::uint32_t>(bb.Format),
                    static_cast<std::uint32_t>(D3DFMT_A8R8G8B8),
                    static_cast<std::uint32_t>(D3DFMT_X8R8G8B8)),
                // outputWritable already proves non-MSAA on the real
                // game backbuffer; reuse that proof instead of duplicating
                // the legacy safety-test sentinel in an unrelated branch.
                outputWritable,
                surfaceWidth, surfaceHeight, s.outputGeneration);
            if (!gpuHandoffQueued && sharedDesktopAllowed &&
                s.backend.color_texture()) {
                const NativeOutputUploadScope outputUploadScope{};
                if (sharedMultiDesktop.valid) {
                    RECT gpuTiles[GameNativeDirtyRegionCoverage::kMaxPartitionRects]{};
                    for (std::uint32_t i = 0; i < sharedMultiDesktop.count; ++i) {
                        const auto& tile = sharedMultiDesktop.regions[i];
                        gpuTiles[i] = {
                            static_cast<LONG>(tile.left),
                            static_cast<LONG>(tile.top),
                            static_cast<LONG>(tile.right),
                            static_cast<LONG>(tile.bottom)};
                    }
                    gpuHandoffQueued = s.sharedDesktop.try_present_regions(
                        game, presentBackbuffer.Get(), s.backend.device(), ctx,
                        s.backend.color_texture(), surfaceWidth, surfaceHeight,
                        s.outputGeneration, gpuTiles, sharedMultiDesktop.count);
                } else {
                    const auto& region = sharedDesktopRegion.source;
                    const RECT visibleRect{
                        static_cast<LONG>(region.left), static_cast<LONG>(region.top),
                        static_cast<LONG>(region.right), static_cast<LONG>(region.bottom)};
                    gpuHandoffQueued = s.sharedDesktop.try_present(
                        game, presentBackbuffer.Get(), s.backend.device(), ctx,
                        s.backend.color_texture(), surfaceWidth, surfaceHeight,
                        s.outputGeneration, visibleRect);
                }
            }
            // Full-resolution publication must be sampled before THIS D3D9
            // Present, not uploaded one or two frames later. Retire older GPU
            // copies only once their fences complete, never reuse busy memory.
            bool fullQueued = false;
            UINT fullSlot = s.writeSlot;
            if (fullMode) {
                for (auto& prior : s.readbacks) {
                    if (!prior.busy || prior.quarantined ||
                        prior.provenance.capturedAtPresent >= s.presents)
                        continue;
                    const HRESULT done = ctx->GetData(prior.fence.Get(), nullptr, 0,
                        D3D11_ASYNC_GETDATA_DONOTFLUSH);
                    const auto fenceResult = GameNativeFramePublication::classify_fence(
                        static_cast<std::int32_t>(done));
                    if (fenceResult == GameNativeReadbackFence::Complete) {
                        if (prior.mapPending) {
                            // This same-Present frame could not be mapped before
                            // its D3D9 Present. A subsequent completed GPU EVENT
                            // alone is not enough to recycle a previously
                            // WOULD_STILL_DRAW Map: recheck CPU map ownership,
                            // then discard its stale bytes without ever painting
                            // them over the next menu/car/race game frame.
                            D3D11_MAPPED_SUBRESOURCE staleMap{};
                            const HRESULT staleStatus = ctx->Map(
                                prior.staging.Get(), 0, D3D11_MAP_READ,
                                D3D11_MAP_FLAG_DO_NOT_WAIT, &staleMap);
                            const auto staleResult = GameNativeFramePublication::classify_map(
                                static_cast<std::int32_t>(staleStatus),
                                static_cast<std::int32_t>(DXGI_ERROR_WAS_STILL_DRAWING),
                                staleMap.pData != nullptr,
                                prior.completeFullFrame ? s.nativeWidth : kWidth,
                                staleMap.RowPitch);
                            if (staleResult == GameNativeReadbackMap::Ready) {
                                ctx->Unmap(prior.staging.Get(), 0);
                                prior.mapPending = false;
                                prior.busy = false;
                                ++s.staleReadbacks;
                            } else if (staleResult == GameNativeReadbackMap::Failed) {
                                if (staleStatus == S_OK) ctx->Unmap(prior.staging.Get(), 0);
                                prior.quarantined = true;
                                ++s.failed;
                            }
                            // Still drawing: keep busy, never reissue CopyResource.
                        } else {
                            prior.busy = false;
                            ++s.staleReadbacks;
                        }
                    } else if (fenceResult == GameNativeReadbackFence::Failed) {
                        // Device loss/unknown completion is not a free-slot
                        // signal. Original D3D9 Present and gamepad remain live.
                        prior.quarantined = true;
                        ++s.failed;
                    }
                }
                if (!gpuHandoffQueued && complete && outputWritable &&
                    s.sourceGameDevice == presentDevice) {
                    // Stale GPU readbacks can occupy the preferred ring slot
                    // while another staging resource is already free. Prefer the
                    // next free resource rather than dropping a valid full-size
                    // current-Present menu/car/race frame unnecessarily.
                    std::uint32_t occupiedSlots = 0u;
                    for (UINT i = 0u; i < kReadbackSlots; ++i) {
                        if (s.readbacks[i].busy) occupiedSlots |= (1u << i);
                    }
                    const UINT availableSlot =
                        GameNativeFramePublication::select_available_slot(
                            occupiedSlots, kReadbackSlots, s.writeSlot);
                    if (availableSlot < kReadbackSlots) {
                        fullSlot = availableSlot;
                        auto& next = s.readbacks[fullSlot];
                        ctx->CopyResource(next.staging.Get(), s.backend.color_texture());
                        next.provenance = {s.presents, s.sourceDrawsThisFrame};
                        next.mapPending = false;
                        next.completeFullFrame = true;
                        next.provenance.sourceDevice = presentDevice;
                        next.provenance.outputGeneration = s.outputGeneration;
                        ctx->End(next.fence.Get());
                        ctx->Flush(); // one fence submission, never block D3D9
                        next.busy = true;
                        fullQueued = true;
                        s.writeSlot = (fullSlot + 1u) % kReadbackSlots;
                    } else {
                        // All fences are still owned by the GPU: do not wait,
                        // reuse a busy staging resource, or stall gamepad input.
                        ++s.droppedCopies;
                    }
                }
            }
            // Insets retain the bounded asynchronous ring. Full-frame polls
            // ONLY its newly enqueued same-Present fence; if not ready, keep
            // the original D3D9 game frame and gamepad response unmodified.
            auto& oldest = s.readbacks[fullMode ? fullSlot : s.readSlot];
            if (oldest.busy && !oldest.quarantined &&
                (!fullMode || fullQueued)) {
                HRESULT ready = ctx->GetData(
                    oldest.fence.Get(), nullptr, 0, D3D11_ASYNC_GETDATA_DONOTFLUSH);
                // In full-size mode this is the only valid publication slot:
                // previous-Present copies are stale, while a single immediate
                // S_FALSE often races a healthy but unfinished GPU submission.
                // Re-poll the already-flushed *same* fence for at most 0.5 ms
                // and 512 calls. Timeout/errors always keep the original D3D9
                // backbuffer and gamepad path, without a delayed native upload.
                if (fullMode && fullQueued && ready == S_FALSE) {
                    LARGE_INTEGER frequency{}, started{}, now{};
                    if (QueryPerformanceFrequency(&frequency) &&
                        frequency.QuadPart > 0 &&
                        QueryPerformanceCounter(&started)) {
                        std::uint64_t elapsedTicks = 0u;
                        for (std::uint32_t retry = 0u;
                             ready == S_FALSE &&
                             GameNativeFramePublication::retry_same_present_fence(
                                 fullMode, fullQueued, retry, elapsedTicks,
                                 static_cast<std::uint64_t>(frequency.QuadPart));
                             ++retry) {
                            ready = ctx->GetData(oldest.fence.Get(), nullptr, 0,
                                                 D3D11_ASYNC_GETDATA_DONOTFLUSH);
                            if (ready != S_FALSE) break;
                            if (!QueryPerformanceCounter(&now) ||
                                now.QuadPart < started.QuadPart) break;
                            elapsedTicks = static_cast<std::uint64_t>(
                                now.QuadPart - started.QuadPart);
                        }
                    }
                }
                if (ready == S_OK && (!oldest.provenance.may_present(s.presents, fullMode) ||
                                     !oldest.provenance.same_device(presentDevice) ||
                                      oldest.completeFullFrame != fullMode ||
                                     !oldest.provenance.same_output(s.outputGeneration) ||
                                     !outputWritable ||
                                     s.sourceGameDevice != presentDevice)) {
                    // A late native frame cannot overwrite a newer menu/race Present.
                    // Its GPU fence is complete; recycle without blocking D3D9/input.
                    ++s.staleReadbacks;
                    oldest.busy = false;
                    if (!fullMode) s.readSlot = (s.readSlot + 1u) % kReadbackSlots;
                } else if (ready == S_OK) {
                    D3D11_MAPPED_SUBRESOURCE mapped{};
                    HRESULT mapStatus = ctx->Map(oldest.staging.Get(), 0,
                        D3D11_MAP_READ, D3D11_MAP_FLAG_DO_NOT_WAIT, &mapped);
                    auto mapResult = GameNativeFramePublication::classify_map(
                        static_cast<std::int32_t>(mapStatus),
                        static_cast<std::int32_t>(DXGI_ERROR_WAS_STILL_DRAWING),
                        mapped.pData != nullptr, surfaceWidth, mapped.RowPitch);
                    // The same-Present EVENT is complete, yet a nonblocking
                    // CPU staging Map can still return WAS_STILL_DRAWING.
                    // Give ONLY this freshly queued full game frame a bounded
                    // second chance to reach native menu/vehicle/race Present.
                    // Never wait on an older frame, Map a failed result again,
                    // change D3D9 Draw/Present or delay original gamepad input.
                    if (fullMode && fullQueued &&
                        mapResult == GameNativeReadbackMap::Pending) {
                        LARGE_INTEGER mapFrequency{}, startedMap{}, nowMap{};
                        if (QueryPerformanceFrequency(&mapFrequency) &&
                            mapFrequency.QuadPart > 0 &&
                            QueryPerformanceCounter(&startedMap)) {
                            std::uint64_t mapElapsedTicks = 0u;
                            for (std::uint32_t retry = 0u;
                                 GameNativeFramePublication::retry_same_present_map(
                                     fullMode, fullQueued,
                                     mapResult == GameNativeReadbackMap::Pending,
                                     retry, mapElapsedTicks,
                                     static_cast<std::uint64_t>(mapFrequency.QuadPart));
                                 ++retry) {
                                mapped = {};
                                mapStatus = ctx->Map(oldest.staging.Get(), 0,
                                    D3D11_MAP_READ, D3D11_MAP_FLAG_DO_NOT_WAIT, &mapped);
                                mapResult = GameNativeFramePublication::classify_map(
                                    static_cast<std::int32_t>(mapStatus),
                                    static_cast<std::int32_t>(DXGI_ERROR_WAS_STILL_DRAWING),
                                    mapped.pData != nullptr, surfaceWidth, mapped.RowPitch);
                                if (mapResult != GameNativeReadbackMap::Pending) break;
                                if (!QueryPerformanceCounter(&nowMap) ||
                                    nowMap.QuadPart < startedMap.QuadPart) break;
                                mapElapsedTicks = static_cast<std::uint64_t>(
                                    nowMap.QuadPart - startedMap.QuadPart);
                            }
                        }
                    }
                    if (mapResult == GameNativeReadbackMap::Ready) {
                        // A complete same-Present full-resolution frame is
                        // valid even when its pixels match the old debug clear
                        // sentinel (for example a dark menu or fade frame).
                        // Only the delayed diagnostic inset needs a pixel
                        // difference probe; scanning the entire game image
                        // adds unnecessary CPU work to gamepad frame pacing.
                        const bool sourcePitchValid =
                            GameNativeFramePublication::valid_readback_pitch(
                                surfaceWidth, mapped.RowPitch);
                        if (!sourcePitchValid) ++s.failed;
                        UINT changedPixels = 0u;
                        if (sourcePitchValid && !fullMode) {
                            for (UINT y = 0; y < surfaceHeight; ++y) {
                                const auto* row = static_cast<const std::uint8_t*>(mapped.pData) +
                                    static_cast<std::size_t>(y) * mapped.RowPitch;
                                for (UINT x = 0; x < surfaceWidth; ++x) {
                                    const auto* p = row + 4 * x;
                                    if (std::abs(int(p[0])-20) > 3 ||
                                        std::abs(int(p[1])-9) > 3 ||
                                        std::abs(int(p[2])-9) > 3) ++changedPixels;
                                }
                            }
                        }
                        if (sourcePitchValid &&
                            GameNativeFramePublication::should_upload(
                                fullMode, !fullMode || complete, outputWritable,
                                changedPixels)) {
                            if (outputWritable) {
                                auto& back = presentBackbuffer;
                                // Cache CPU upload memory; invalidate on format/Reset.
                                if (!s.insetSurface || s.insetFormat != bb.Format ||
                                    s.insetSurfaceDevice != presentDevice ||
                                    !GameNativeFramePublication::matching_upload_extent(
                                        s.insetSurfaceWidth, s.insetSurfaceHeight,
                                        surfaceWidth, surfaceHeight)) {
                                    s.insetSurface.Reset();
                                    s.insetFormat = D3DFMT_UNKNOWN;
                                    s.insetSurfaceDevice = 0u;
    s.insetSurfaceWidth = s.insetSurfaceHeight = 0u;
                                    if (SUCCEEDED(game->CreateOffscreenPlainSurface(
                                            surfaceWidth, surfaceHeight, bb.Format, D3DPOOL_SYSTEMMEM,
                                            s.insetSurface.GetAddressOf(), nullptr))) {
                                        s.insetFormat = bb.Format;
                                        s.insetSurfaceDevice = presentDevice;
                                        s.insetSurfaceWidth = surfaceWidth;
                                        s.insetSurfaceHeight = surfaceHeight;
                                    }
                                }
                                D3DLOCKED_RECT lockRect{};
                                if (s.insetSurface && s.insetFormat == bb.Format &&
                                    s.insetSurfaceDevice == presentDevice &&
                                    GameNativeFramePublication::matching_upload_extent(
                                        s.insetSurfaceWidth, s.insetSurfaceHeight,
                                        surfaceWidth, surfaceHeight) &&
                                    // A multi-tile UpdateSurface loop can commit early
                                    // tiles before a later failure, leaking a partial native
                                    // frame. Seed every untouched gap from the *current*
                                    // original D3D9 backbuffer, then publish once. If the
                                    // backbuffer cannot be read, keep D3D9/input unchanged.
                                    (!multiNativeUpload || SUCCEEDED(game->GetRenderTargetData(
                                        back.Get(), s.insetSurface.Get()))) &&
                                    SUCCEEDED(s.insetSurface->LockRect(&lockRect, nullptr, 0))) {
                                    // Refuse malformed D3D9 lock pitches
                                    // before copying a full game backbuffer.
                                    // Keep the D3D9 frame/input untouched.
                                    // Transfer native BGRA pixels only while both CPU
                                    // mappings remain valid. A failed UnlockRect must
                                    // never submit partially updated menu/race pixels.
                                    const bool copied =
                                        GameNativeFramePublication::valid_upload_pitch(
                                            surfaceWidth, lockRect.Pitch) &&
                                        (croppedNativeUpload
                                            ? GameNativeFrameUpload::copy_rect(
                                                lockRect.pBits, lockRect.Pitch,
                                                mapped.pData, mapped.RowPitch,
                                                surfaceWidth, surfaceHeight,
                                                static_cast<std::uint32_t>(presentRegion.left),
                                                static_cast<std::uint32_t>(presentRegion.top),
                                                static_cast<std::uint32_t>(presentRegion.right),
                                                static_cast<std::uint32_t>(presentRegion.bottom))
                                            : partialNativeUpload
                                             ? GameNativeFrameUpload::copy_rect(
                                                 lockRect.pBits, lockRect.Pitch,
                                                 mapped.pData, mapped.RowPitch,
                                                 surfaceWidth, surfaceHeight,
                                                 static_cast<std::uint32_t>(partialDirty.source.left),
                                                 static_cast<std::uint32_t>(partialDirty.source.top),
                                                 static_cast<std::uint32_t>(partialDirty.source.right),
                                                 static_cast<std::uint32_t>(partialDirty.source.bottom))
                                             : multiNativeUpload
                                             ? [&]() noexcept {
                                                 for (std::uint32_t i = 0u; i < multiDirty.count; ++i) {
                                                     const auto& tile = multiDirty.regions[i];
                                                     if (!GameNativeFrameUpload::copy_rect(
                                                             lockRect.pBits, lockRect.Pitch,
                                                             mapped.pData, mapped.RowPitch,
                                                             surfaceWidth, surfaceHeight,
                                                             static_cast<std::uint32_t>(tile.left),
                                                             static_cast<std::uint32_t>(tile.top),
                                                             static_cast<std::uint32_t>(tile.right),
                                                             static_cast<std::uint32_t>(tile.bottom)))
                                                         return false;
                                                 }
                                                 return true;
                                             }()
                                             : GameNativeFrameUpload::copy_rows(
                                                lockRect.pBits, lockRect.Pitch,
                                                mapped.pData, mapped.RowPitch,
                                                surfaceWidth, surfaceHeight));
                                    const HRESULT unlockStatus = s.insetSurface->UnlockRect();
                                    if (!copied || FAILED(unlockStatus)) {
                                        ++s.failed;
                                        if (FAILED(unlockStatus)) {
                                            // Drop the invalid D3D9 CPU upload cache.
                                            // Original game Present/input still proceed.
                                            s.insetSurface.Reset();
                                            s.insetFormat = D3DFMT_UNKNOWN;
                                            s.insetSurfaceDevice = 0u;
                                            s.insetSurfaceWidth = s.insetSurfaceHeight = 0u;
                                        }
                                    } else {
                                        POINT destination{
                                            static_cast<LONG>(fullMode ? fullPlacement.left : insetPlacement.left),
                                            static_cast<LONG>(fullMode ? fullPlacement.top : insetPlacement.top)};
                                        const RECT uploadSourceCrop{
                                            static_cast<LONG>(presentRegion.left),
                                            static_cast<LONG>(presentRegion.top),
                                            static_cast<LONG>(presentRegion.right),
                                            static_cast<LONG>(presentRegion.bottom)};
                                        if (croppedNativeUpload) {
                                            destination.x = uploadSourceCrop.left;
                                            destination.y = uploadSourceCrop.top;
                                        }
                                        const RECT partialSourceUpload{
                                             static_cast<LONG>(partialDirty.source.left),
                                             static_cast<LONG>(partialDirty.source.top),
                                             static_cast<LONG>(partialDirty.source.right),
                                             static_cast<LONG>(partialDirty.source.bottom)};
                                         if (partialNativeUpload) {
                                             destination.x = partialSourceUpload.left;
                                             destination.y = partialSourceUpload.top;
                                         }
                                         // Restrict the GPU upload to the exact
                                        // dirty source crop. The other backbuffer
                                        // pixels retain the original D3D9 scene.
                                        bool uploaded = false;
                                        // UpdateSurface goes through the game's
                                        // R30 observer. It is OUR publication,
                                        // not another unmirrored game mutation;
                                        // suppress recursion while State is locked.
                                        const NativeOutputUploadScope outputUploadScope{};
                                        const auto rollbackPlan =
                                            NativeGameCpuUploadPlan::select(
                                                bb.Width, bb.Height,
                                                croppedNativeUpload, partialNativeUpload,
                                                multiNativeUpload, presentRegion,
                                                partialDirty.source, multiDirty.uploadBounds);
                                        // Snapshot calls StretchRect while State is locked:
                                        // NativeOutputUploadScope prevents recursive observation.
                                        const bool originalSaved = !fullMode ||
                                            s.cpuUploadRollback.capture(
                                                game,back.Get(),bb.Width,bb.Height,
                                                bb.Format,s.outputGeneration,rollbackPlan);
                                        if (!originalSaved) {
                                            // Snapshot failed: do not touch game backbuffer.
                                        } else if (!multiNativeUpload) {
                                            uploaded = SUCCEEDED(game->UpdateSurface(
                                                s.insetSurface.Get(),
                                                partialNativeUpload ? &partialSourceUpload :
                                                     (croppedNativeUpload ? &uploadSourceCrop : nullptr),
                                                back.Get(), &destination));
                                        } else {
                                            // The SYSTEMMEM surface contains the original
                                            // D3D9 backbuffer plus only the verified native
                                            // tiles. One bounded UpdateSurface preserves all
                                            // holes and cannot leave a prefix of tiles behind
                                            // when a later upload fails.
                                            const auto& bounds = multiDirty.uploadBounds;
                                            const RECT sourceTiles{
                                                static_cast<LONG>(bounds.left),
                                                static_cast<LONG>(bounds.top),
                                                static_cast<LONG>(bounds.right),
                                                static_cast<LONG>(bounds.bottom)};
                                            const POINT targetTiles{sourceTiles.left, sourceTiles.top};
                                            uploaded = SUCCEEDED(game->UpdateSurface(
                                                s.insetSurface.Get(), &sourceTiles,
                                                back.Get(), &targetTiles));
                                        }
                                        if (uploaded) {
                                            if (fullMode) s.cpuUploadRollback.commit();
                                            ++s.visible;
                                            if (!s.logged) {
                                                spdlog::info("DX11 FIRST_GAME_DRAW_FRAME async game-origin FVF native Draw: {} changed pixels, {}x{} {} output; original D3D9 draw/input untouched; Quest3 UNTESTED",
                                                    changedPixels, surfaceWidth, surfaceHeight,
                                                    fullMode ? "full-frame" : "inset");
                                                s.logged = true;
                                            }
                                        } else {
                                            ++s.failed;
                                            if (fullMode && originalSaved &&
                                                !s.cpuUploadRollback.restore(game,back.Get()))
                                                spdlog::warn("DX11 CPU native upload rollback failed; CPU presentation quarantined until Reset");
                                            // A D3D9 UpdateSurface failure may invalidate
                                            // the CPU upload surface across menu, car or
                                            // race backbuffer transitions. Release it and
                                            // rebuild on a subsequent eligible full frame.
                                            // Never alter the original game Present/input.
                                            if (fullMode) {
                                                s.insetSurface.Reset();
                                                s.insetFormat = D3DFMT_UNKNOWN;
                                                s.insetSurfaceDevice = 0u;
                                                s.insetSurfaceWidth = s.insetSurfaceHeight = 0u;
                                            }
                                        }
                                    }
                                } else ++s.failed;
                            } else ++s.failed;
                        }
                        ctx->Unmap(oldest.staging.Get(), 0);
                        oldest.mapPending = false;
                        oldest.busy = false;
                        if (!fullMode) s.readSlot = (s.readSlot + 1u) % kReadbackSlots;
                    } else if (mapResult == GameNativeReadbackMap::Pending) {
                        // The completed EVENT raced a DO_NOT_WAIT Map. Keep the
                        // staging slot occupied; a future Present must confirm
                        // a successful Map/Unmap before it can be reused.
                        oldest.mapPending = true;
                    } else if (mapResult == GameNativeReadbackMap::Failed) {
                        // Even with a completed EVENT, an unexpected Map status,
                        // invalid row stride or missing pixel pointer cannot be
                        // published. Never recycle the failed staging allocation
                        // into another menu/car/race CopyResource before Reset.
                        if (mapStatus == S_OK) ctx->Unmap(oldest.staging.Get(), 0);
                        oldest.mapPending = false;
                        oldest.quarantined = true;
                        ++s.failed;
                    }
                } else if (GameNativeFramePublication::classify_fence(
                               static_cast<std::int32_t>(ready)) ==
                           GameNativeReadbackFence::Failed) {
                    // Never recycle a staging texture on an unconfirmed GPU
                    // fence failure; wait for a source-device Reset to retire it.
                    oldest.quarantined = true;
                    ++s.failed;
                }
            }
            // Never publish partial GPU compositing from a source draw gap,
            // a failed vertex/index translation or a failed D3D11 submit.
            // Previously s.pending survived abort() and copied corrupt insets.
            // Native full-frame was already enqueued and opportunistically
            // polled for this Present. Never enqueue a second lagged copy.
            if (complete && outputWritable &&
                s.sourceGameDevice == presentDevice && !fullMode) {
                auto& next = s.readbacks[s.writeSlot];
                if (!next.busy) {
                    ctx->CopyResource(next.staging.Get(), s.backend.color_texture());
                    next.provenance = {s.presents, s.sourceDrawsThisFrame};
                    next.mapPending = false;
                    next.completeFullFrame = fullMode;
                    next.provenance.sourceDevice = presentDevice;
                    next.provenance.outputGeneration = s.outputGeneration;
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
        s.frameBatch.reset();
        s.cpuSurfaceReplay.reset();
        s.clearColor.discard();
        s.preDrawFills.discard();
        // Menu/car/race frames often have more than 64 eligible draws. The
        // cursor advances across the actual frame population; shrinking or
        // empty populations reset it without skipping the D3D9 fallback.
        s.probeSlot = GameNativeFrameBatch::next_probe_slot(
            s.probeSlot, s.eligibleThisFrame);
        s.eligibleThisFrame = 0;
        s.sourceDrawsThisFrame = 0u;
    s.sourceModeKnown = false;
        s.sourceGameDevice = 0u;
        s.surfaceReplayCount = 0u;
        // Opt-in-only evidence: a hooked game Draw is not proof that the
        // restricted FVF subset was admitted, nor that GPU pixels became
        // visible in the game's backbuffer. Log both missing links explicitly.
        ++s.presents;
        // This is runtime evidence, not a source-only/CI PASS. Keep a
        // periodic 300-Present heartbeat even AFTER native frames become
        // visible, so a menu->vehicle->race session can be audited.
        if (s.presents % 300u == 0u || (fullMode && s.visible == 1u)) {
            spdlog::info(
                "DX11 FIRST_GAME_DRAW_FRAME progress: game_tri_draws={} native_draws={} desktop_insets={} failed={} presents={} eligible_state_draws={} stale_readbacks={} next_probe_slot={} full_frame_mode={}; unsupported draws stay DX9Ex; HMD UNTESTED",
                s.observed, s.issued, s.visible, s.failed, s.presents,
                s.eligible, s.staleReadbacks, s.probeSlot, fullMode ? 1 : 0);
        }
    } catch (...) {
        // Preserve DX9Ex Present and recover on the next game frame.
        // The diagnostic is best-effort even when logging/readback fails;
        // leave all original D3D9 Present and input behavior untouched.
        State& s = state();
        s.pending = false;
        s.frameBatch.reset();
        s.cpuSurfaceReplay.reset();
        s.eligibleThisFrame = 0;
        s.sourceDrawsThisFrame = 0u;
    s.sourceModeKnown = false;
        s.sourceGameDevice = 0u;
        s.surfaceReplayCount = 0u;
        s.previousOutput = {};
        s.clearColor.discard();
        s.preDrawFills.discard();
        s.insetSurface.Reset();
        s.insetFormat = D3DFMT_UNKNOWN;
        s.insetSurfaceDevice = 0u;
    s.insetSurfaceWidth = s.insetSurfaceHeight = 0u;
        if (++s.outputGeneration == 0u) ++s.outputGeneration;
        s.probeSlot = 0;
    }
}

void before_game_reset(IDirect3DDevice9* game) noexcept {
    if (!diagnostic_enabled() || !game) return;
    State& s = state();
    std::lock_guard<std::mutex> lock(s.mutex);
    // D3D9 Reset is per-device: an auxiliary menu/video device's Reset
    // must not discard the primary game's native Draw/Present GPU batch.
    if (!GameNativeFrameBatch::reset_belongs_to_game_source(
            reinterpret_cast<std::uintptr_t>(game), s.sourceGameDevice,
            s.previousOutput.valid() ? s.previousOutput.device : 0u))
        return;
    s.pending = false;
    s.frameBatch.reset();
    s.cpuSurfaceReplay.reset();
    s.eligibleThisFrame = 0;
    s.sourceDrawsThisFrame = 0u;
    s.sourceModeKnown = false;
    s.sourceGameDevice = 0u;
    s.probeSlot = 0;
    s.sharedDesktop.reset();
    s.cpuUploadRollback.reset();
    for (auto& item : s.readbacks) {
        item.staging.Reset(); item.fence.Reset(); item.busy = false; item.quarantined = false;
        item.mapPending = false;
        item.provenance = {};
    }
    s.readSlot = s.writeSlot = 0;
    s.previousOutput = {};
    s.clearColor.discard();
    s.preDrawFills.discard();
    s.outputGeneration = 0u;
    s.surfaceReplayReadback.Reset();
    s.surfaceReplayOwner = 0u;
    s.surfaceReplayWidth = s.surfaceReplayHeight = 0u;
    s.surfaceReplayFormat = D3DFMT_UNKNOWN;
    s.surfaceReplayScratch.Reset();
    s.surfaceReplayScratchDevice.Reset();
    s.surfaceReplayScratchWidth = s.surfaceReplayScratchHeight = 0u;
    s.surfaceReplayPixels.clear();
    s.surfaceReplayCount = 0u;
    s.insetSurface.Reset(); s.insetFormat = D3DFMT_UNKNOWN;
    s.insetSurfaceDevice = 0u;
    s.insetSurfaceWidth = s.insetSurfaceHeight = 0u;
    s.diagnosticDepthView.Reset(); s.diagnosticDepth.Reset();
    for (auto& depthState : s.diagnosticDepthStates) depthState.Reset();
    for (auto& depthState : s.diagnosticDepthAlwaysStates) depthState.Reset();
    for (auto& depthState : s.diagnosticDepthEqualityStates) depthState.Reset();
    for (auto& depthState : s.diagnosticDepthOrderingStates) depthState.Reset();
    s.raster.Reset(); s.scissorRaster.Reset(); s.layout.Reset();
    for (auto& item : s.diagnosticCullRasters) item.Reset();
    s.alphaBlend.Reset(); s.additiveBlend.Reset(); s.sourceAlphaAddBlend.Reset(); s.premultipliedAlphaBlend.Reset(); s.inverseSourceAlphaBlend.Reset(); s.sourceAlphaCopyBlend.Reset(); s.inverseAlphaCopyBlend.Reset(); s.inverseAlphaAddBlend.Reset(); s.sourceReplaceBlend.Reset(); s.multiplyBlend.Reset(); s.inverseDestMultiplyBlend.Reset(); s.inverseSourceMultiplyBlend.Reset(); s.destAlphaCrossfadeBlend.Reset(); s.reverseDestAlphaCrossfadeBlend.Reset(); s.sourceAlphaSaturateCopyBlend.Reset(); s.sourceAlphaSaturateAddBlend.Reset();
    s.alphaConstants.Reset();
    s.stage1Constants.Reset();
    for (auto& masked : s.maskedBlends) masked.Reset();
    for (auto& masked : s.multiplyMaskedBlends) masked.Reset();
    for (auto& masked : s.inverseDestMultiplyMaskedBlends) masked.Reset();
    for (auto& masked : s.inverseSourceMultiplyMaskedBlends) masked.Reset();
    for (auto& masked : s.destAlphaCrossfadeMaskedBlends) masked.Reset();
    for (auto& masked : s.reverseDestAlphaCrossfadeMaskedBlends) masked.Reset();
    for (auto& masked : s.sourceAlphaSaturateCopyMaskedBlends) masked.Reset();
    for (auto& masked : s.sourceAlphaSaturateAddMaskedBlends) masked.Reset();
    for (auto& masked : s.inverseSourceAlphaMaskedBlends) masked.Reset();
    for (auto& masked : s.sourceAlphaCopyMaskedBlends) masked.Reset();
    for (auto& masked : s.inverseAlphaCopyMaskedBlends) masked.Reset();
    for (auto& masked : s.inverseAlphaAddMaskedBlends) masked.Reset();
    for (auto& masked : s.sourceReplaceMaskedBlends) masked.Reset();
    for (auto& masked : s.subtractiveMaskedBlends) masked.Reset();
    for (auto& masked : s.extremumMaskedBlends) masked.Reset();
    s.ps.Reset(); s.sampledPs.Reset();
    // The four stage-1 pixel shaders must not outlive their native device.
    s.stage1DiffusePs.Reset(); s.stage1ModulatePs.Reset();
    s.stage1TextureOnlyPs.Reset(); s.stage1AddPs.Reset();
    s.textureOnlyPs.Reset(); s.selectTextureDiffuseAlphaPs.Reset(); s.selectTextureModulateAlphaPs.Reset(); s.selectTextureModulate2XAlphaPs.Reset(); s.selectTextureModulate4XAlphaPs.Reset(); s.selectTextureAddAlphaPs.Reset(); s.selectTextureSubtractAlphaPs.Reset(); s.selectDiffuseTextureAlphaPs.Reset(); s.selectDiffuseModulateAlphaPs.Reset(); s.selectDiffuseAddAlphaPs.Reset(); s.selectDiffuseSubtractAlphaPs.Reset(); s.selectDiffuseModulate2XAlphaPs.Reset(); s.selectDiffuseModulate4XAlphaPs.Reset(); s.selectTextureAddSmoothAlphaPs.Reset(); s.selectDiffuseAddSmoothAlphaPs.Reset(); s.selectTextureFactorAlphaPs.Reset(); s.selectTextureTfactorAlphaPs.Reset(); s.selectDiffuseFactorAlphaPs.Reset(); s.selectDiffuseTfactorAlphaPs.Reset(); s.selectTextureBlendTextureAlphaPs.Reset(); s.selectDiffuseBlendTextureAlphaPs.Reset(); s.selectTextureBlendDiffuseAlphaPs.Reset(); s.selectDiffuseBlendDiffuseAlphaPs.Reset(); s.additivePs.Reset(); s.subtractPs.Reset(); s.addSmoothPs.Reset();
    s.subtractTextureAlphaPs.Reset(); s.subtractDiffuseAlphaPs.Reset(); s.subtractModulateAlphaPs.Reset(); s.modulate2xPs.Reset(); s.modulate4xPs.Reset(); s.modulate2xTextureAlphaPs.Reset(); s.modulate2xDiffuseAlphaPs.Reset(); s.modulate4xTextureAlphaPs.Reset(); s.modulate4xDiffuseAlphaPs.Reset(); s.mixedTextureAlphaPs.Reset(); s.mixedDiffuseAlphaPs.Reset(); s.mixedAddTextureAlphaPs.Reset(); s.mixedAddDiffuseAlphaPs.Reset(); s.blendTextureAlphaPs.Reset(); s.blendTextureAlphaPmPs.Reset(); s.blendTextureAlphaPmTextureAlphaPs.Reset(); s.blendTextureAlphaPmInverseTextureAlphaPs.Reset(); s.blendTextureAlphaPmInverseDiffuseAlphaPs.Reset(); s.blendTextureAlphaPmDiffuseAlphaPs.Reset(); s.blendTextureAlphaPmFactorAlphaPs.Reset(); s.blendTextureAlphaPmSignedFactorAlphaPs.Reset(); s.blendTextureAlphaPmSigned2XFactorAlphaPs.Reset(); s.blendTextureAlphaPmModulateFactorAlphaPs.Reset(); s.blendTextureAlphaPmModulateAlphaPs.Reset(); s.blendTextureAlphaPmAddAlphaPs.Reset(); s.blendTextureAlphaPmSubtractAlphaPs.Reset(); s.blendTextureAlphaPmModulate2XAlphaPs.Reset(); s.blendTextureAlphaPmModulate4XAlphaPs.Reset(); s.blendTextureAlphaPmAddSignedAlphaPs.Reset(); s.blendTextureAlphaPmAddSigned2XAlphaPs.Reset(); s.blendTextureAlphaPmBlendTextureAlphaPs.Reset(); s.blendTextureAlphaPmBlendDiffuseAlphaPs.Reset(); s.blendTextureAlphaPmBlendCurrentFactorAlphaPs.Reset(); s.blendTextureAlphaPmBlendFactorAlphaPs.Reset(); s.blendTextureAlphaPmAddSmoothAlphaPs.Reset(); s.blendDiffuseAlphaPs.Reset(); s.blendTextureSelectedTextureAlphaPs.Reset(); s.blendTextureSelectedDiffuseAlphaPs.Reset(); s.blendDiffuseSelectedTextureAlphaPs.Reset(); s.blendDiffuseSelectedDiffuseAlphaPs.Reset(); s.blendTextureModulateAlphaPs.Reset(); s.blendDiffuseModulateAlphaPs.Reset(); s.blendTextureModulate2XAlphaPs.Reset(); s.blendTextureModulate4XAlphaPs.Reset(); s.blendDiffuseModulate2XAlphaPs.Reset(); s.blendDiffuseModulate4XAlphaPs.Reset(); s.blendTextureAddAlphaPs.Reset(); s.blendDiffuseAddAlphaPs.Reset(); s.blendTextureSubtractAlphaPs.Reset(); s.blendDiffuseSubtractAlphaPs.Reset(); s.blendTextureAddSmoothAlphaPs.Reset(); s.blendDiffuseAddSmoothAlphaPs.Reset(); s.blendFactorAlphaPs.Reset(); s.blendFactorTextureAlphaPs.Reset(); s.blendFactorModulateAlphaPs.Reset(); s.blendFactorDiffuseAlphaPs.Reset(); s.blendFactorAddAlphaPs.Reset(); s.blendFactorSubtractAlphaPs.Reset(); s.blendFactorAddSmoothAlphaPs.Reset(); s.blendFactorModulate2XAlphaPs.Reset(); s.blendFactorModulate4XAlphaPs.Reset(); s.addSmoothTextureAlphaPs.Reset(); s.addSmoothDiffuseAlphaPs.Reset(); s.vs.Reset();
    // These buffers are owned by the exact D3D11 device generation.
    s.fullGameVertexUpload.Reset();
    s.fullGameIndexUpload.Reset();
    s.fullGameVertexCapacity = s.fullGameIndexCapacity = 0u;
    s.liveSm3Pipelines.clear();
    s.liveSm3BlendStates.clear();
    s.backend.shutdown();
    s.nativeWidth = s.nativeHeight = 0u;
}
} // namespace outrun::vr::dx11::live_game_frame
