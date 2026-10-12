#include "live_game_frame_bridge.hpp"
#include "live_game_primitive_span.hpp"
#include "live_game_fvf_layout.hpp"
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
#include <string>
#include <vector>
#include <spdlog/spdlog.h>

namespace outrun::vr::dx11::live_game_frame {
namespace {
using Microsoft::WRL::ComPtr;
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
              kGameFvfPositionMask == D3DFVF_POSITION_MASK,
              "Portable FVF constants must match the D3D9 SDK");
constexpr UINT kWidth = 256;
constexpr UINT kHeight = 144;
constexpr UINT kMaxVertices = 1536;
constexpr UINT kMaxIndices = 1536;
// Rotate among eligible game Draws so an off-screen first Draw cannot starve
// later visible candidates. Exactly one native submission is allowed per Present.
constexpr UINT kProbeSlots = 64;
constexpr UINT kReadbackSlots = 3; // GPU event-fenced frame copies
// D3D11 sampler range: reject rather than clamp unsupported D3D9 LOD offsets.
constexpr float kMinMipLodBias = -16.0f;
constexpr float kMaxMipLodBias = 15.99f;

constexpr std::array<float, 4> kBackground{0.035f, 0.035f, 0.08f, 1.0f};
constexpr char kShader[] = R"(
struct VIn { float4 clip : POSITION; float4 diffuse : COLOR0; float2 uv : TEXCOORD0; };
struct VOut { float4 clip : SV_Position; float4 diffuse : COLOR0; float2 uv : TEXCOORD0; };
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
VOut VS(VIn v) { VOut o; o.clip = v.clip; o.diffuse = v.diffuse; o.uv = v.uv; return o; }
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
};

// Narrow fixed-function stage-0 textured subset for real game menu/vehicle/race
// draws. Any unmirrored texture, sampler, alpha or stage state fails closed.
struct TextureCapture {
    bool enabled = false;
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
    D3D11_BLEND_OP blendOp = D3D11_BLEND_OP_ADD; // Captured D3D9 RGB and alpha operation.
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
    static const std::string shaderSource = std::string(kShader) + kScaledAlphaShader;
    return SUCCEEDED(D3DCompile(shaderSource.data(), shaderSource.size(), "live_game_frame",
        nullptr, nullptr, entry, profile, D3DCOMPILE_ENABLE_STRICTNESS,
        0, blob.GetAddressOf(), errors.GetAddressOf())) && blob;
}

bool ensure_pipeline(State& s) noexcept {
    const bool readbackReady = std::all_of(s.readbacks.begin(), s.readbacks.end(),
        [](const ReadbackSlot& item) { return item.staging && item.fence; });
    if (s.backend.ready() && s.vs && s.ps && s.sampledPs && s.textureOnlyPs && s.selectDiffuseTextureAlphaPs && s.selectDiffuseModulateAlphaPs && s.selectDiffuseAddAlphaPs && s.selectDiffuseSubtractAlphaPs && s.selectDiffuseModulate2XAlphaPs && s.selectDiffuseModulate4XAlphaPs && s.additivePs && s.subtractPs && s.selectTextureAddSmoothAlphaPs && s.selectDiffuseAddSmoothAlphaPs && s.selectTextureFactorAlphaPs && s.selectTextureTfactorAlphaPs && s.selectDiffuseFactorAlphaPs && s.selectDiffuseTfactorAlphaPs && s.selectTextureBlendTextureAlphaPs && s.selectDiffuseBlendTextureAlphaPs && s.selectTextureBlendDiffuseAlphaPs && s.selectDiffuseBlendDiffuseAlphaPs && s.selectTextureModulate2XAlphaPs && s.selectTextureModulate4XAlphaPs && s.selectTextureDiffuseAlphaPs && s.selectTextureModulateAlphaPs && s.selectTextureAddAlphaPs && s.selectTextureSubtractAlphaPs &&
        s.subtractTextureAlphaPs && s.subtractDiffuseAlphaPs && s.subtractModulateAlphaPs && s.addSmoothPs && s.modulate2xPs && s.modulate4xPs &&
        s.modulate2xTextureAlphaPs &&
        s.modulate2xDiffuseAlphaPs &&
        s.modulate4xTextureAlphaPs &&
        s.modulate4xDiffuseAlphaPs && s.mixedTextureAlphaPs && s.mixedDiffuseAlphaPs &&
        s.mixedAddTextureAlphaPs && s.mixedAddDiffuseAlphaPs &&
        s.blendTextureAlphaPs && s.blendDiffuseAlphaPs && s.blendTextureSelectedTextureAlphaPs && s.blendTextureSelectedDiffuseAlphaPs && s.blendDiffuseSelectedTextureAlphaPs && s.blendDiffuseSelectedDiffuseAlphaPs && s.blendTextureModulateAlphaPs && s.blendDiffuseModulateAlphaPs && s.blendTextureModulate2XAlphaPs && s.blendTextureModulate4XAlphaPs && s.blendDiffuseModulate2XAlphaPs && s.blendDiffuseModulate4XAlphaPs && s.blendTextureAddAlphaPs && s.blendDiffuseAddAlphaPs &&
        s.blendTextureSubtractAlphaPs && s.blendDiffuseSubtractAlphaPs &&
        s.blendTextureAddSmoothAlphaPs && s.blendDiffuseAddSmoothAlphaPs && s.blendFactorAlphaPs &&
        s.blendFactorTextureAlphaPs && s.blendFactorModulateAlphaPs &&
        s.blendFactorDiffuseAlphaPs && s.blendFactorAddAlphaPs &&
        s.blendFactorSubtractAlphaPs && s.blendFactorAddSmoothAlphaPs &&
        s.blendFactorModulate2XAlphaPs && s.blendFactorModulate4XAlphaPs &&
        s.addSmoothTextureAlphaPs && s.addSmoothDiffuseAlphaPs &&
        s.layout && s.raster && s.scissorRaster && s.alphaBlend &&
         s.additiveBlend && s.sourceAlphaAddBlend && s.premultipliedAlphaBlend &&
        s.inverseSourceAlphaBlend && s.multiplyBlend &&
         s.inverseDestMultiplyBlend && s.inverseSourceMultiplyBlend &&
         s.destAlphaCrossfadeBlend && s.reverseDestAlphaCrossfadeBlend &&
         s.sourceAlphaSaturateCopyBlend && s.sourceAlphaSaturateAddBlend &&
        s.sourceAlphaCopyBlend && s.inverseAlphaCopyBlend &&
        s.inverseAlphaAddBlend && s.sourceReplaceBlend &&
        s.alphaConstants && readbackReady)
        return true;
    s.backend.shutdown();
    s.vs.Reset(); s.ps.Reset(); s.sampledPs.Reset(); s.textureOnlyPs.Reset(); s.selectTextureDiffuseAlphaPs.Reset(); s.selectTextureModulateAlphaPs.Reset(); s.selectTextureModulate2XAlphaPs.Reset(); s.selectTextureModulate4XAlphaPs.Reset(); s.selectTextureAddAlphaPs.Reset(); s.selectTextureSubtractAlphaPs.Reset(); s.selectDiffuseTextureAlphaPs.Reset(); s.selectDiffuseModulateAlphaPs.Reset(); s.selectDiffuseAddAlphaPs.Reset(); s.selectDiffuseSubtractAlphaPs.Reset(); s.selectDiffuseModulate2XAlphaPs.Reset(); s.selectDiffuseModulate4XAlphaPs.Reset(); s.selectTextureAddSmoothAlphaPs.Reset(); s.selectDiffuseAddSmoothAlphaPs.Reset(); s.selectTextureFactorAlphaPs.Reset(); s.selectTextureTfactorAlphaPs.Reset(); s.selectDiffuseFactorAlphaPs.Reset(); s.selectDiffuseTfactorAlphaPs.Reset(); s.selectTextureBlendTextureAlphaPs.Reset(); s.selectDiffuseBlendTextureAlphaPs.Reset(); s.selectTextureBlendDiffuseAlphaPs.Reset(); s.selectDiffuseBlendDiffuseAlphaPs.Reset(); s.additivePs.Reset(); s.subtractPs.Reset(); s.addSmoothPs.Reset();
    s.subtractTextureAlphaPs.Reset(); s.subtractDiffuseAlphaPs.Reset(); s.subtractModulateAlphaPs.Reset(); s.modulate2xPs.Reset(); s.modulate4xPs.Reset(); s.modulate2xTextureAlphaPs.Reset(); s.modulate2xDiffuseAlphaPs.Reset(); s.modulate4xTextureAlphaPs.Reset(); s.modulate4xDiffuseAlphaPs.Reset(); s.mixedTextureAlphaPs.Reset(); s.mixedDiffuseAlphaPs.Reset(); s.mixedAddTextureAlphaPs.Reset(); s.mixedAddDiffuseAlphaPs.Reset(); s.blendTextureAlphaPs.Reset(); s.blendDiffuseAlphaPs.Reset(); s.blendTextureSelectedTextureAlphaPs.Reset(); s.blendTextureSelectedDiffuseAlphaPs.Reset(); s.blendDiffuseSelectedTextureAlphaPs.Reset(); s.blendDiffuseSelectedDiffuseAlphaPs.Reset(); s.blendTextureModulateAlphaPs.Reset(); s.blendDiffuseModulateAlphaPs.Reset(); s.blendTextureModulate2XAlphaPs.Reset(); s.blendTextureModulate4XAlphaPs.Reset(); s.blendDiffuseModulate2XAlphaPs.Reset(); s.blendDiffuseModulate4XAlphaPs.Reset(); s.blendTextureAddAlphaPs.Reset(); s.blendDiffuseAddAlphaPs.Reset(); s.blendTextureSubtractAlphaPs.Reset(); s.blendDiffuseSubtractAlphaPs.Reset(); s.blendTextureAddSmoothAlphaPs.Reset(); s.blendDiffuseAddSmoothAlphaPs.Reset(); s.blendFactorAlphaPs.Reset(); s.blendFactorTextureAlphaPs.Reset(); s.blendFactorModulateAlphaPs.Reset();
    s.blendFactorDiffuseAlphaPs.Reset(); s.blendFactorAddAlphaPs.Reset(); s.blendFactorSubtractAlphaPs.Reset(); s.blendFactorAddSmoothAlphaPs.Reset();
    s.blendFactorModulate2XAlphaPs.Reset(); s.blendFactorModulate4XAlphaPs.Reset();
    s.addSmoothTextureAlphaPs.Reset(); s.addSmoothDiffuseAlphaPs.Reset();
    s.layout.Reset(); s.raster.Reset(); s.scissorRaster.Reset();
    s.alphaBlend.Reset(); s.additiveBlend.Reset(); s.sourceAlphaAddBlend.Reset(); s.premultipliedAlphaBlend.Reset(); s.inverseSourceAlphaBlend.Reset(); s.sourceAlphaCopyBlend.Reset(); s.inverseAlphaCopyBlend.Reset(); s.inverseAlphaAddBlend.Reset(); s.sourceReplaceBlend.Reset(); s.multiplyBlend.Reset(); s.inverseDestMultiplyBlend.Reset(); s.inverseSourceMultiplyBlend.Reset(); s.destAlphaCrossfadeBlend.Reset(); s.reverseDestAlphaCrossfadeBlend.Reset(); s.sourceAlphaSaturateCopyBlend.Reset(); s.sourceAlphaSaturateAddBlend.Reset();
    s.alphaConstants.Reset();
    for (auto& item : s.readbacks) {
        item.staging.Reset(); item.fence.Reset(); item.busy = false;
    }
    s.readSlot = s.writeSlot = 0;
    s.insetSurface.Reset(); s.insetFormat = D3DFMT_UNKNOWN;
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
    NativeBackendConfig cfg{};
    cfg.width = kWidth;
    cfg.height = kHeight;
    cfg.color_format = DXGI_FORMAT_B8G8R8A8_UNORM;
    if (!s.backend.initialize(cfg)) return false;
    auto* dev = s.backend.device();
    ComPtr<ID3DBlob> vcode, pcode, sampledCode, textureOnlyCode, additiveCode, subtractCode, addSmoothCode, modulate2xCode, modulate4xCode, modulate2xTextureCode, modulate2xDiffuseCode, modulate4xTextureCode, modulate4xDiffuseCode, subtractTextureCode, subtractDiffuseCode, subtractModulateCode, mixedTextureCode, mixedDiffuseCode, mixedAddTextureCode, mixedAddDiffuseCode, blendTextureCode, blendDiffuseCode, blendTextureSelectedTextureAlphaCode, blendTextureSelectedDiffuseAlphaCode, blendDiffuseSelectedTextureAlphaCode, blendDiffuseSelectedDiffuseAlphaCode, blendTextureModulate2XCode, blendTextureModulate4XCode, blendDiffuseModulate2XCode, blendDiffuseModulate4XCode, blendTextureModulateCode, blendDiffuseModulateCode, blendTextureAddCode, blendDiffuseAddCode, blendTextureSubtractCode, blendDiffuseSubtractCode, blendTextureAddSmoothCode, blendDiffuseAddSmoothCode, blendFactorCode, blendFactorTextureCode, blendFactorModulateCode, blendFactorDiffuseCode, blendFactorAddCode, blendFactorSubtractCode, blendFactorAddSmoothCode, blendFactorModulate2XCode, blendFactorModulate4XCode, smoothTextureCode, smoothDiffuseCode, selectDiffuseTextureCode, selectDiffuseModulateCode, selectTextureDiffuseCode, selectTextureModulateCode, selectTextureModulate2XCode, selectTextureModulate4XCode, selectTextureAddCode, selectTextureSubtractCode, selectDiffuseAddCode, selectDiffuseSubtractCode, selectDiffuseModulate2XCode, selectDiffuseModulate4XCode, selectTextureAddSmoothCode, selectDiffuseAddSmoothCode, selectTextureFactorCode, selectDiffuseFactorCode, selectTextureBlendTextureCode, selectDiffuseBlendTextureCode; ComPtr<ID3DBlob> selectTextureBlendDiffuseCode, selectDiffuseBlendDiffuseCode, selectTextureTfactorCode, selectDiffuseTfactorCode;
    if (!compile("VS", "vs_4_0", vcode) ||
        !compile("PS", "ps_4_0", pcode) ||
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
                          GameFvfLayout& layout,
                          std::array<D3DMATRIX, 3>& transforms,
                          TextureCapture& capture, OutputCapture& output) noexcept {
    if (!game || FAILED(game->GetViewport(&viewport)) ||
        viewport.Width == 0 || viewport.Height == 0)
        return false;
    DWORD fvf = 0;
    if (FAILED(game->GetFVF(&fvf))) return false;
    // Use the live game's exact FVF byte layout; avoid reading UV as
    // diffuse when a menu/sprite TEX1 vertex omits D3DFVF_DIFFUSE.
    if (!game_fvf_layout(fvf, layout)) return false;
    // observe() admits triangle lists/strips/fans only: FVF PSIZE cannot
    // affect triangle rasterization, but offsets for live COLOR/UV must skip it.
    capture.enabled = layout.textured;
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
    // D3D9 sprite/menu draw states. Mirror the complete 8-bit alpha compare
    // family, but continue to reject unsupported blend factors/separate alpha.
    if (blend) {
        DWORD src = 0, dst = 0, blendOp = 0, separate = TRUE;
        if (FAILED(game->GetRenderState(D3DRS_SRCBLEND, &src)) ||
            FAILED(game->GetRenderState(D3DRS_DESTBLEND, &dst)) ||
            FAILED(game->GetRenderState(D3DRS_BLENDOP, &blendOp)) ||
            FAILED(game->GetRenderState(D3DRS_SEPARATEALPHABLENDENABLE, &separate)) ||
            separate)
            return false;
        // Do not enable separate-alpha blending: both native OM operations
        // always apply to RGB and alpha, matching a single D3D9 BLENDOP.
        if (blendOp != D3DBLENDOP_ADD || separate) {
            if (blendOp != D3DBLENDOP_SUBTRACT &&
                blendOp != D3DBLENDOP_REVSUBTRACT) return false;
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
        nextColorOp != D3DTOP_DISABLE || resultArg != D3DTA_CURRENT)
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
        const bool rgbDiffuse =
            (op == D3DTOP_SELECTARG1 &&
             (arg == D3DTA_DIFFUSE || arg == D3DTA_CURRENT)) ||
            (op == D3DTOP_SELECTARG2 &&
             (arg2 == D3DTA_DIFFUSE || arg2 == D3DTA_CURRENT));
        const bool alphaDiffuse =
            (alphaOp == D3DTOP_SELECTARG1 &&
             (alphaArg1 == D3DTA_DIFFUSE || alphaArg1 == D3DTA_CURRENT)) ||
            (alphaOp == D3DTOP_SELECTARG2 &&
             (alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT));
        if (!rgbDiffuse || !alphaDiffuse) return false;
    }
    if (capture.enabled) {
        DWORD arg2=0, alphaOp=0, alphaArg1=0, alphaArg2=0;
        DWORD coordIndex=~0u, transformFlags=~0u;
        DWORD addressU=0, addressV=0, mag=0, min=0, mip=0, srgb=1;
        DWORD borderColor = 0u;
        DWORD maxMip=~0u, mipBias=~0u;
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
            FAILED(game->GetSamplerState(0, D3DSAMP_SRGBTEXTURE, &srgb)))
            return false;
        // Sampled BORDER U or V needs game-authored ARGB rather than D3D11 zero.
        // Failure stays on original D3D9 Draw, with no native submission.
        if ((addressU == D3DTADDRESS_BORDER || addressV == D3DTADDRESS_BORDER) &&
            FAILED(game->GetSamplerState(0, D3DSAMP_BORDERCOLOR, &borderColor)))
            return false;
        // D3D9 COUNT2 takes (u,v,1,0); projective and other counts fail closed.
        const bool transformUv = transformFlags == D3DTTFF_COUNT2;
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
        // Capture the factor only after the SELECTARG predicates exist;
        // unsupported D3D9 states keep the original DX9Ex draw/input.
        DWORD textureFactor = 0;
        if ((blendFactorAlpha || blendFactorTextureAlpha || blendFactorModulateAlpha ||
             selectTextureTfactorAlpha || selectDiffuseTfactorAlpha ||
             selectTextureTfactorArg2Alpha || selectDiffuseTfactorArg2Alpha ||
             blendFactorDiffuseAlpha || blendFactorAddAlpha ||
             blendFactorSubtractAlpha || blendFactorAddSmoothAlpha ||
             blendFactorModulate2XAlpha || blendFactorModulate4XAlpha ||
              selectTextureFactorAlpha || selectDiffuseFactorAlpha) &&
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
        const bool blendDiffuseAlpha = op == D3DTOP_BLENDDIFFUSEALPHA && alphaOp == D3DTOP_BLENDDIFFUSEALPHA;
        const bool blendTextureSelectedTextureAlpha = op == D3DTOP_BLENDTEXTUREALPHA && alphaOp == D3DTOP_SELECTARG1;
        const bool blendTextureSelectedDiffuseAlpha = op == D3DTOP_BLENDTEXTUREALPHA && alphaOp == D3DTOP_SELECTARG2;
        const bool blendDiffuseSelectedTextureAlpha = op == D3DTOP_BLENDDIFFUSEALPHA && alphaOp == D3DTOP_SELECTARG1;
        const bool blendDiffuseSelectedDiffuseAlpha = op == D3DTOP_BLENDDIFFUSEALPHA && alphaOp == D3DTOP_SELECTARG2;
        // On D3D9 fixed-function stage 0, CURRENT resolves to vertex DIFFUSE.
        // Reject operand modifiers; later stages are disabled by the gate.
        const bool arg2Diffuse = arg2 == D3DTA_DIFFUSE || arg2 == D3DTA_CURRENT;
        const bool alphaArg2Diffuse = alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT;
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
                                     blendTextureAlpha || blendDiffuseAlpha || blendFactorAlpha;
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
                                       blendTextureAlpha || blendDiffuseAlpha || blendFactorAlpha;
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
             !blendTextureAlpha && !blendDiffuseAlpha && !blendFactorAlpha) || arg != D3DTA_TEXTURE ||
            (!selectTextureDiffuseAlpha && (!blendFactorDiffuseAlpha && !addSmoothDiffuseAlpha &&
              !subtractDiffuseAlpha &&
              !modulate2xDiffuseAlpha && !modulate4xDiffuseAlpha &&
              (!subtractDiffuseAlpha && !blendTextureSelectedDiffuseAlpha && !blendDiffuseSelectedDiffuseAlpha &&
               ((!selectDiffuseDiffuseAlpha && !mixedDiffuseAlpha && !mixedAddDiffuseAlpha && alphaArg1 != D3DTA_TEXTURE) && !selectTextureTfactorAlpha && !selectDiffuseTfactorAlpha &&
               !selectTextureTfactorArg2Alpha && !selectDiffuseTfactorArg2Alpha)))) ||
            (rgbNeedsDiffuse && !arg2Diffuse) ||
            ((alphaNeedsDiffuse && !alphaArg2Diffuse) && !selectTextureTfactorArg2Alpha && !selectDiffuseTfactorArg2Alpha) ||
            coordIndex >= layout.texcoordCount ||
            (transformFlags != D3DTTFF_DISABLE && transformFlags != D3DTTFF_COUNT2) || srgb ||
            ((addressU != D3DTADDRESS_WRAP && addressU != D3DTADDRESS_CLAMP &&
             addressU != D3DTADDRESS_MIRROR && addressU != D3DTADDRESS_MIRRORONCE) &&
             addressU != D3DTADDRESS_BORDER) ||
            ((addressV != D3DTADDRESS_WRAP && addressV != D3DTADDRESS_CLAMP &&
             addressV != D3DTADDRESS_MIRROR && addressV != D3DTADDRESS_MIRRORONCE) &&
             addressV != D3DTADDRESS_BORDER) ||
            (mag != D3DTEXF_POINT && mag != D3DTEXF_LINEAR) ||
            (min != D3DTEXF_POINT && min != D3DTEXF_LINEAR) ||
            ((mip != D3DTEXF_NONE && mip != D3DTEXF_POINT) && mip != D3DTEXF_LINEAR) ||
            (mip == D3DTEXF_NONE && (maxMip != 0u || decodedMipBias != 0.0f)) || !validMipBias)
            return false;
        capture.mipFilter = static_cast<D3DTEXTUREFILTERTYPE>(mip);
        capture.maxMipLevel = maxMip;
        capture.mipLodBias = decodedMipBias;
        capture.addressU = static_cast<D3DTEXTUREADDRESS>(addressU);
        capture.addressV = static_cast<D3DTEXTUREADDRESS>(addressV);
        capture.borderColor = borderColor;
        capture.minFilter = static_cast<D3DTEXTUREFILTERTYPE>(min);
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
        capture.coordIndex = coordIndex;
        capture.transformUv = transformUv;
        if (transformUv) capture.uvTransform = uvTransform;
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
    return true;
}

bool translate_vertices(const void* input, UINT count, UINT stride,
                        const D3DVIEWPORT9& vp, const GameFvfLayout& layout,
                        const std::array<D3DMATRIX, 3>& transforms,
                        const TextureCapture& capture,
                        std::vector<NativeVertex>& output) {
    if (!input || stride < layout.minStride || stride > 512u ||
        count == 0 || count > kMaxVertices ||
        capture.enabled != layout.textured)
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
        // TEX2..8 select UV1..7 from game bytes; absent slots fail closed.
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

// Snapshot a live game texture into a D3D11 sampleable resource. When the
// source asks for MIP_POINT or MIP_LINEAR, upload every readable mip rather than binding
// level 0 and silently changing the game's minification result. All error
// paths preserve the original D3D9 Draw/Present/gamepad behavior.
bool mirror_texture(ID3D11Device* dev, const TextureCapture& capture,
                    ComPtr<ID3D11ShaderResourceView>& view,
                    ComPtr<ID3D11SamplerState>& sampler) noexcept {
    if (!dev || !capture.enabled || !capture.texture) return false;
    const UINT sourceLevels = capture.texture->GetLevelCount();
    if (sourceLevels == 0 || sourceLevels > 11u) return false;
    D3DSURFACE_DESC base{};
    if (FAILED(capture.texture->GetLevelDesc(0, &base)) ||
        base.Width == 0 || base.Height == 0 ||
        base.Width > 1024 || base.Height > 1024) return false;
    const bool gpuRenderTarget = base.Pool == D3DPOOL_DEFAULT &&
        (base.Usage & D3DUSAGE_RENDERTARGET) != 0u &&
        (base.Format == D3DFMT_A8R8G8B8 ||
         base.Format == D3DFMT_X8R8G8B8);
    if (base.Pool == D3DPOOL_DEFAULT && !gpuRenderTarget) return false;
    const bool usesMips = capture.mipFilter == D3DTEXF_POINT ||
                          capture.mipFilter == D3DTEXF_LINEAR;
    // AUTOGENMIPMAP exposes one level to LockRect even though the D3D9
    // sampler consumes generated levels. Never claim those mips were copied.
    if (usesMips && (base.Usage & D3DUSAGE_AUTOGENMIPMAP)) return false;
    if (usesMips && capture.texture->GetLOD() != 0u) return false;
    // Reject invalid game mip requests rather than silently clamping a native sampler.
    if (usesMips && capture.maxMipLevel >= sourceLevels) return false;
    const UINT levels = usesMips ? sourceLevels : 1u;
    if (gpuRenderTarget && levels != 1u) return false;
    const bool compressed = base.Format == D3DFMT_DXT1 ||
                            base.Format == D3DFMT_DXT3 ||
                            base.Format == D3DFMT_DXT5;
    const bool packed16 = base.Format == D3DFMT_R5G6B5 ||
                          base.Format == D3DFMT_A1R5G5B5 ||
                          base.Format == D3DFMT_A4R4G4B4;
    DXGI_FORMAT nativeFormat = DXGI_FORMAT_UNKNOWN;
    if (compressed) {
        // A full-sized BC base level is required, but its final mips may
        // legally be 2x2 or 1x1, each occupying one compressed 4x4 block.
        if ((base.Width & 3u) || (base.Height & 3u)) return false;
        nativeFormat = base.Format == D3DFMT_DXT1 ? DXGI_FORMAT_BC1_UNORM :
                       base.Format == D3DFMT_DXT3 ? DXGI_FORMAT_BC2_UNORM :
                                                     DXGI_FORMAT_BC3_UNORM;
    } else if (base.Format == D3DFMT_A8R8G8B8 ||
               base.Format == D3DFMT_X8R8G8B8 || packed16) {
        nativeFormat = DXGI_FORMAT_B8G8R8A8_UNORM;
    } else return false;

    ComPtr<IDirect3DSurface9> readbackSurface;
    if (gpuRenderTarget) {
        ComPtr<IDirect3DSurface9> sourceSurface;
        ComPtr<IDirect3DDevice9> gameDevice;
        D3DSURFACE_DESC sourceDesc{};
        if (FAILED(capture.texture->GetSurfaceLevel(0, sourceSurface.GetAddressOf())) ||
            FAILED(sourceSurface->GetDesc(&sourceDesc)) ||
            sourceDesc.MultiSampleType != D3DMULTISAMPLE_NONE ||
            sourceDesc.Width != base.Width || sourceDesc.Height != base.Height ||
            sourceDesc.Format != base.Format ||
            !(sourceDesc.Usage & D3DUSAGE_RENDERTARGET) ||
            FAILED(capture.texture->GetDevice(gameDevice.GetAddressOf())) ||
            FAILED(gameDevice->CreateOffscreenPlainSurface(
                base.Width, base.Height, base.Format, D3DPOOL_SYSTEMMEM,
                readbackSurface.GetAddressOf(), nullptr)) ||
            FAILED(gameDevice->GetRenderTargetData(sourceSurface.Get(), readbackSurface.Get())))
            return false;
    }

    std::vector<std::vector<std::uint8_t>> copied(levels);
    std::vector<UINT> pitches(levels);
    for (UINT level = 0; level < levels; ++level) {
        D3DSURFACE_DESC desc{};
        if (FAILED(capture.texture->GetLevelDesc(level, &desc)) ||
            desc.Format != base.Format || desc.Pool != base.Pool ||
            desc.Width != (std::max)(1u, base.Width >> level) ||
            desc.Height != (std::max)(1u, base.Height >> level))
            return false;
        const UINT rows = compressed ? (std::max)(1u, (desc.Height + 3u) / 4u) : desc.Height;
        const UINT rowBytes = compressed ?
            (std::max)(1u, (desc.Width + 3u) / 4u) *
                (base.Format == D3DFMT_DXT1 ? 8u : 16u) :
            desc.Width * (packed16 ? 2u : 4u);
        const UINT uploadPitch = packed16 ? desc.Width * 4u : rowBytes;
        D3DLOCKED_RECT lock{};
        const HRESULT lockResult = gpuRenderTarget ?
            readbackSurface->LockRect(&lock, nullptr, D3DLOCK_READONLY) :
            capture.texture->LockRect(level, &lock, nullptr, D3DLOCK_READONLY);
        if (FAILED(lockResult)) return false;
        const bool readable = lock.pBits && lock.Pitch > 0 &&
                              static_cast<UINT>(lock.Pitch) >= rowBytes;
        if (readable) {
            auto& pixels = copied[level];
            pixels.resize(static_cast<std::size_t>(uploadPitch) * rows);
            const auto packing = base.Format == D3DFMT_R5G6B5 ?
                packed_texture16::Layout::rgb565 :
                base.Format == D3DFMT_A1R5G5B5 ?
                packed_texture16::Layout::argb1555 :
                packed_texture16::Layout::argb4444;
            for (UINT y = 0; y < rows; ++y) {
                const auto* source = static_cast<const std::uint8_t*>(lock.pBits) +
                                     static_cast<std::size_t>(y) * lock.Pitch;
                auto* destination = pixels.data() + static_cast<std::size_t>(y) * uploadPitch;
                if (packed16)
                    packed_texture16::unpack_row(source, destination, desc.Width, packing);
                else
                    std::memcpy(destination, source, rowBytes);
            }
            // X8R8G8B8 has no usable alpha; every mip must sample opaque.
            if (base.Format == D3DFMT_X8R8G8B8)
                for (std::size_t p = 3; p < pixels.size(); p += 4)
                    pixels[p] = 0xffu;
            pitches[level] = uploadPitch;
        }
        if (gpuRenderTarget) readbackSurface->UnlockRect();
        else capture.texture->UnlockRect(level);
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
    state.MaxAnisotropy = 1;
    state.ComparisonFunc = D3D11_COMPARISON_NEVER;
    return SUCCEEDED(dev->CreateSamplerState(&state, sampler.GetAddressOf()));
}

bool submit(State& s, const std::vector<NativeVertex>& vertices,
            const std::uint32_t* indices, UINT indexCount,
            D3DPRIMITIVETYPE topology, const TextureCapture& capture,
            const OutputCapture& output) noexcept {
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
        static_cast<float>(output.alphaFunc), capture.blendFactorAlphaValue
    };
    // D3D11 default OM state writes all channels. Even when blending is off,
    // a partial D3D9 COLORWRITEENABLE requires a real blend-state object.
    // Copy the validated alpha blend descriptor rather than approximating
    // its RGB/alpha factors in a second path.
    ComPtr<ID3D11BlendState>* maskedBlend = nullptr;
    if (output.blendOp != D3D11_BLEND_OP_ADD) {
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
    ctx->UpdateSubresource(s.alphaConstants.Get(), 0, nullptr, alphaParams, 0, 0);
    s.backend.begin_frame(kBackground);
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
    const UINT stride = sizeof(NativeVertex), offset = 0;
    ID3D11Buffer* boundVB = vb.Get();
    ctx->IASetInputLayout(s.layout.Get());
    ctx->IASetPrimitiveTopology(topology == D3DPT_TRIANGLESTRIP ?
        D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP :
        D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    ctx->IASetVertexBuffers(0, 1, &boundVB, &stride, &offset);
    if (ib) ctx->IASetIndexBuffer(ib.Get(), DXGI_FORMAT_R32_UINT, 0);
    const D3D11_RECT fullScissor{0, 0, static_cast<LONG>(kWidth),
                                  static_cast<LONG>(kHeight)};
    const D3D11_RECT& rect = output.scissor ? output.nativeScissor : fullScissor;
    ctx->RSSetScissorRects(1, &rect);
    ctx->RSSetState(output.scissor ? s.scissorRaster.Get() : s.raster.Get());
    ctx->VSSetShader(s.vs.Get(), nullptr, 0);
    ctx->PSSetShader(capture.selectDiffuseTextureAlpha ? s.selectDiffuseTextureAlphaPs.Get() :
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
    UINT expectedElements = 0;
    if (!diagnostic_enabled() || !game ||
        (type != D3DPT_TRIANGLELIST && type != D3DPT_TRIANGLESTRIP &&
         type != D3DPT_TRIANGLEFAN) ||
        !game_primitive_element_count(type == D3DPT_TRIANGLESTRIP ||
                                       type == D3DPT_TRIANGLEFAN,
                                      primitives, expectedElements))
        return;
    try {
        State& s = state();
        std::lock_guard<std::mutex> lock(s.mutex);
        ++s.observed;
        D3DVIEWPORT9 vp{};
        GameFvfLayout layout{};
        std::array<D3DMATRIX, 3> transforms{};
        TextureCapture capture{};
        OutputCapture output{};
        if (!supported_game_state(game, vp, layout, transforms, capture, output)) return;
        // Count every admitted state, including calls after this frame's one
        // native draw. Use that bounded population to rotate the next frame's
        // probe rather than sampling its same first triangle indefinitely.
        const UINT candidateOrdinal = s.eligibleThisFrame++;
        ++s.eligible;
        if (s.attempted || candidateOrdinal != s.probeSlot) return;
        if (indexCount && (!indices || indexCount != expectedElements ||
                           vertexCount > kMaxVertices))
            return;
        if (!indexCount && vertexCount != expectedElements) return;
        std::vector<NativeVertex> vertices;
        if (!translate_vertices(bytes, vertexCount, stride, vp,
                                layout, transforms, capture, vertices))
            return;
        if (indices) {
            for (UINT i=0; i<indexCount; ++i)
                if (indices[i] >= vertexCount) return;
        }
        if (type == D3DPT_TRIANGLEFAN) {
            // Real game VB/IB/UP data, rebased by R30. No fixture substitution.
            std::vector<std::uint32_t> fanTriangles;
            if (!game_fan_to_triangle_list(primitives, indices, indexCount,
                                           vertexCount, fanTriangles))
                return;
            s.attempted = true;
            if (!submit(s, vertices, fanTriangles.data(),
                        static_cast<UINT>(fanTriangles.size()),
                        D3DPT_TRIANGLELIST, capture, output))
                ++s.failed;
        } else {
            s.attempted = true;
            if (!submit(s, vertices, indices, indexCount, type, capture, output))
                ++s.failed;
        }
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
    UINT nativeElements = 0;
    if ((type != D3DPT_TRIANGLELIST && type != D3DPT_TRIANGLESTRIP &&
         type != D3DPT_TRIANGLEFAN) ||
        !game_primitive_element_count(type == D3DPT_TRIANGLESTRIP ||
                                       type == D3DPT_TRIANGLEFAN,
                                      primitives, nativeElements)) return;
    observe(game, type, primitives, vertices, stride, nativeElements, nullptr, 0);
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
    s.alphaBlend.Reset(); s.additiveBlend.Reset(); s.sourceAlphaAddBlend.Reset(); s.premultipliedAlphaBlend.Reset(); s.inverseSourceAlphaBlend.Reset(); s.sourceAlphaCopyBlend.Reset(); s.inverseAlphaCopyBlend.Reset(); s.inverseAlphaAddBlend.Reset(); s.sourceReplaceBlend.Reset(); s.multiplyBlend.Reset(); s.inverseDestMultiplyBlend.Reset(); s.inverseSourceMultiplyBlend.Reset(); s.destAlphaCrossfadeBlend.Reset(); s.reverseDestAlphaCrossfadeBlend.Reset(); s.sourceAlphaSaturateCopyBlend.Reset(); s.sourceAlphaSaturateAddBlend.Reset();
    s.alphaConstants.Reset();
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
    s.ps.Reset(); s.sampledPs.Reset(); s.textureOnlyPs.Reset(); s.selectTextureDiffuseAlphaPs.Reset(); s.selectTextureModulateAlphaPs.Reset(); s.selectTextureModulate2XAlphaPs.Reset(); s.selectTextureModulate4XAlphaPs.Reset(); s.selectTextureAddAlphaPs.Reset(); s.selectTextureSubtractAlphaPs.Reset(); s.selectDiffuseTextureAlphaPs.Reset(); s.selectDiffuseModulateAlphaPs.Reset(); s.selectDiffuseAddAlphaPs.Reset(); s.selectDiffuseSubtractAlphaPs.Reset(); s.selectDiffuseModulate2XAlphaPs.Reset(); s.selectDiffuseModulate4XAlphaPs.Reset(); s.selectTextureAddSmoothAlphaPs.Reset(); s.selectDiffuseAddSmoothAlphaPs.Reset(); s.selectTextureFactorAlphaPs.Reset(); s.selectTextureTfactorAlphaPs.Reset(); s.selectDiffuseFactorAlphaPs.Reset(); s.selectDiffuseTfactorAlphaPs.Reset(); s.selectTextureBlendTextureAlphaPs.Reset(); s.selectDiffuseBlendTextureAlphaPs.Reset(); s.selectTextureBlendDiffuseAlphaPs.Reset(); s.selectDiffuseBlendDiffuseAlphaPs.Reset(); s.additivePs.Reset(); s.subtractPs.Reset(); s.addSmoothPs.Reset();
    s.subtractTextureAlphaPs.Reset(); s.subtractDiffuseAlphaPs.Reset(); s.subtractModulateAlphaPs.Reset(); s.modulate2xPs.Reset(); s.modulate4xPs.Reset(); s.modulate2xTextureAlphaPs.Reset(); s.modulate2xDiffuseAlphaPs.Reset(); s.modulate4xTextureAlphaPs.Reset(); s.modulate4xDiffuseAlphaPs.Reset(); s.mixedTextureAlphaPs.Reset(); s.mixedDiffuseAlphaPs.Reset(); s.mixedAddTextureAlphaPs.Reset(); s.mixedAddDiffuseAlphaPs.Reset(); s.blendTextureAlphaPs.Reset(); s.blendDiffuseAlphaPs.Reset(); s.blendTextureSelectedTextureAlphaPs.Reset(); s.blendTextureSelectedDiffuseAlphaPs.Reset(); s.blendDiffuseSelectedTextureAlphaPs.Reset(); s.blendDiffuseSelectedDiffuseAlphaPs.Reset(); s.blendTextureModulateAlphaPs.Reset(); s.blendDiffuseModulateAlphaPs.Reset(); s.blendTextureModulate2XAlphaPs.Reset(); s.blendTextureModulate4XAlphaPs.Reset(); s.blendDiffuseModulate2XAlphaPs.Reset(); s.blendDiffuseModulate4XAlphaPs.Reset(); s.blendTextureAddAlphaPs.Reset(); s.blendDiffuseAddAlphaPs.Reset(); s.blendTextureSubtractAlphaPs.Reset(); s.blendDiffuseSubtractAlphaPs.Reset(); s.blendTextureAddSmoothAlphaPs.Reset(); s.blendDiffuseAddSmoothAlphaPs.Reset(); s.blendFactorAlphaPs.Reset(); s.blendFactorTextureAlphaPs.Reset(); s.blendFactorModulateAlphaPs.Reset(); s.blendFactorDiffuseAlphaPs.Reset(); s.blendFactorAddAlphaPs.Reset(); s.blendFactorSubtractAlphaPs.Reset(); s.blendFactorAddSmoothAlphaPs.Reset(); s.blendFactorModulate2XAlphaPs.Reset(); s.blendFactorModulate4XAlphaPs.Reset(); s.addSmoothTextureAlphaPs.Reset(); s.addSmoothDiffuseAlphaPs.Reset(); s.vs.Reset();
    s.backend.shutdown();
}
} // namespace outrun::vr::dx11::live_game_frame
