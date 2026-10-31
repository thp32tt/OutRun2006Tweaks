#include "live_game_sm3_table_fog.hpp"
#include "native_game_raw_fvf_fog_visual.hpp"
#include <cassert>
#include <cmath>
#include <string>
using namespace outrun::vr::dx11;
int main() {
    NativeSm3TableFog fog{};
    // D3D9 equation NONE/NONE is shared across fixed-function and SM3
    // game-authored draws. Any active equation still requires exact coverage.
    assert(native_game_inert_fog_modes(0u, 0u));
    assert(!native_game_inert_fog_modes(1u, 0u));
    assert(!native_game_inert_fog_modes(0u, 1u));
    assert(!native_game_inert_fog_modes(3u, 3u));
    // Mode-only NONE/NONE must not require inactive payload/caps reads;
    // active shader/table/vertex fog still requires all of them.
    assert(!native_sm3_fog_needs_parameters(false, 3u, 3u));
    assert(!native_sm3_fog_needs_parameters(true, 0u, 0u));
    assert(native_sm3_fog_needs_parameters(true, 1u, 0u));
    assert(native_sm3_fog_needs_parameters(true, 0u, 2u));
    assert(native_sm3_fog_needs_parameters(true, 3u, 3u));
    // Source-authentic EXP/EXP2 density=0 is pixel-inert even if the
    // driver advertises W fog or reports no Z fog. Range/vertex fog are
    // inherited but overridden by the active table equation; no synthetic
    // color or full-frame claim is permitted.
    for (unsigned mode : {1u, 2u}) {
        assert(native_sm3_exponential_table_density_probe(mode, 3u));
        assert(native_sm3_inert_exponential_table_fog(mode, 3u, -0.0f));
        NativeSm3FogReject reason = NativeSm3FogReject::SourceQuery;
        assert(native_sm3_table_zfog_admission(
            true, mode, 3u, true, true, false, true,
            0u, std::nanf(""), std::nanf(""), -0.0f, fog, &reason));
        assert(!fog.enabled && reason == NativeSm3FogReject::None);
        assert(!native_sm3_table_zfog_admission(
            true, mode, 3u, true, true, false, true,
            0u, 0.0f, 1.0f, 0.1f, fog, &reason));
        assert(!fog.enabled && reason == NativeSm3FogReject::Srgb);
        assert(!native_sm3_inert_exponential_table_fog(
            mode, 3u, std::nanf("")));
    }
    assert(!native_sm3_exponential_table_density_probe(3u, 3u));
    assert(!native_sm3_exponential_table_density_probe(1u, 4u));
    assert(!native_sm3_inert_exponential_table_fog(0u, 0u, 0.0f));
    // Genuine exponential, squared-exponential and linear game fog inputs.
    for (unsigned mode : {1u, 2u, 3u}) {
        assert(native_sm3_table_zfog_admission(
            true, mode, 0u, false, false, true, false,
            0xff204080u, 0.2f, 0.8f, 1.0f, fog));
        assert(fog.enabled && fog.controls[3] == float(mode));
        assert(std::fabs(fog.rgba[0] - 32.0f/255.0f) < 0.0001f);
    }
    assert(std::fabs(native_sm3_table_zfog_factor(3u, 0.5f, 0.2f, 0.8f, 1.0f)
                     - 0.5f) < 0.0001f);
    assert(std::fabs(native_sm3_table_zfog_factor(1u, 1.0f, 0.0f, 1.0f, 1.0f)
                     - std::exp(-1.0f)) < 0.0001f);
    assert(std::fabs(native_sm3_table_zfog_factor(2u, 1.0f, 0.0f, 1.0f, 1.0f)
                     - std::exp(-1.0f)) < 0.0001f);
    // The D3D9 rasterizer chooses real Z/W fog by the actual projection
    // fourth column, not by the mere presence of a WFOG device capability.
    assert(native_sm3_projection_fog_depth(0.f,0.f,0.f,1.f,true)
           == NativeSm3FogDepth::Z);
    assert(native_sm3_projection_fog_depth(0.f,0.f,1.f,0.f,true)
           == NativeSm3FogDepth::W);
    assert(native_sm3_projection_fog_depth(0.f,0.f,0.2f,0.f,true)
           == NativeSm3FogDepth::Unknown);
    assert(native_sm3_projection_fog_depth(0.f,1.f,1.f,0.f,true)
           == NativeSm3FogDepth::Unknown);
    assert(native_sm3_projection_fog_depth(
               std::nanf(""),0.f,1.f,0.f,true)
           == NativeSm3FogDepth::Unknown);
    assert(native_sm3_projection_fog_depth(0.f,0.f,1.f,0.f,false)
           == NativeSm3FogDepth::Z);
    // Source-authentic active EXP/EXP2/LINEAR table fog now travels through
    // the same native PS and live cbuffer with either certified coordinate.
    // A W-only device must not require the unrelated ZFOG capability.
    for (unsigned mode : {1u, 2u, 3u}) {
        NativeSm3FogReject why = NativeSm3FogReject::SourceQuery;
        assert(native_sm3_table_zfog_admission(
            true, mode, 2u, true, false, false, true,
            0xffaabbccu, 0.1f, 0.9f, 0.5f, fog, &why,
            NativeSm3FogDepth::W));
        assert(fog.enabled && fog.rgba[3] == 1.0f &&
               fog.controls[3] == float(mode) && why == NativeSm3FogReject::None);
        assert(native_sm3_table_zfog_admission(
            true, mode, 2u, false, false, true, true,
            0xffaabbccu, 0.1f, 0.9f, 0.5f, fog, &why,
            NativeSm3FogDepth::Z));
        assert(fog.enabled && fog.rgba[3] == 0.0f);
        assert(!native_sm3_table_zfog_admission(
            true, mode, 2u, false, false, true, true,
            0u, 0.1f, 0.9f, 0.5f, fog, &why,
            NativeSm3FogDepth::Unknown));
        assert(why == NativeSm3FogReject::WCapability && !fog.enabled);
        assert(!native_sm3_table_zfog_admission(
            true, mode, 2u, false, false, false, false,
            0u, 0.1f, 0.9f, 0.5f, fog, &why,
            NativeSm3FogDepth::W));
        assert(why == NativeSm3FogReject::WCapability && !fog.enabled);
        assert(!native_sm3_table_zfog_admission(
            true, mode, 2u, false, false, false, true,
            0u, 0.1f, 0.9f, 0.5f, fog, &why,
            NativeSm3FogDepth::Z));
        assert(why == NativeSm3FogReject::MissingZCapability);
    }
    // A live D3D9 TABLE mode wins over inherited VERTEX and RANGE modes.
    // These are real game-state combinations, not relaxed safety checks.
    for (unsigned mode : {1u, 2u, 3u}) {
        for (unsigned vertex : {0u, 1u, 2u, 3u}) {
            for (bool range : {false, true}) {
                NativeSm3FogReject reason = NativeSm3FogReject::SourceQuery;
                assert(native_sm3_table_zfog_admission(
                    true, mode, vertex, range, false, true, false,
                    0xff204080u, 0.2f, 0.8f, 1.0f, fog, &reason));
                assert(fog.enabled && fog.controls[3] == float(mode));
                assert(reason == NativeSm3FogReject::None);
            }
        }
        // Only the five genuinely unsupported live table-source cases fail.
        for (unsigned problem=0; problem<5; ++problem) {
            const bool badSrgb = problem == 0;
            const bool missingZ = problem == 1;
            const bool badW = problem == 2;
            const bool badVertexIdentity = problem == 3;
            const bool badTableIdentity = problem == 4;
            const bool ok = native_sm3_table_zfog_admission(
                true, badTableIdentity ? 4u : mode,
                badVertexIdentity ? 4u : 2u, true, badSrgb,
                !missingZ, badW, 0u, 0.2f, 0.8f, 1.0f, fog);
            assert(!ok && !fog.enabled);
        }
    }
    // Vertex-only fog still has no native VS fog coordinate transport:
    // it must stay on original D3D9, regardless of range or Z capability.
    NativeSm3FogReject ignoredVertex = NativeSm3FogReject::None;
    assert(!native_sm3_table_zfog_admission(
        true, 0u, 3u, false, false, true, false,
        0u, 0.2f, 0.8f, 1.0f, fog, &ignoredVertex));
    assert(ignoredVertex == NativeSm3FogReject::VertexFog);
    assert(!native_sm3_table_zfog_admission(
        true, 3u, 0u, false, false, true, false,
        0u, 0.9f, 0.3f, 1.0f, fog));
    assert(!native_sm3_table_zfog_admission(
        true, 2u, 0u, false, false, true, false,
        0u, 0.0f, 1.0f, -1.0f, fog));
    assert(native_sm3_table_zfog_admission(
        true, 0u, 0u, false, false, true, false,
        0u, 0.0f, 1.0f, 1.0f, fog) && !fog.enabled);
    assert(native_sm3_table_zfog_admission(
        false, 3u, 1u, true, true, false, true,
        0u, 0.0f, 1.0f, -1.0f, fog) && !fog.enabled);
    // Live FVF production Draws must admit EXP/EXP2 table fog only with
    // an authentic zero-density DWORD; vertex/range inherit no contribution.
    assert(native_sm3_exponential_table_density_probe(1u, 3u));
    assert(native_sm3_inert_exponential_table_fog(1u, 3u, -0.0f));
    assert(native_sm3_inert_exponential_table_fog(2u, 0u, 0.0f));
    assert(!native_sm3_inert_exponential_table_fog(1u, 3u, 0.1f));
    assert(!native_sm3_inert_exponential_table_fog(1u, 3u, std::nanf("")));
    // An unavailable W projection cannot certify production fog, but RAW
    // deliberately omits its appearance after verified SOURCE float reads.
    // LINEAR and EXP consume different source registers, including vertex-
    // only fallback. A failed getter/invalid consumed equation never enters.
    assert(native_sm3_raw_visual_fog_omission(
        true, true, 3u, 1u, 0.2f, 0.8f, std::nanf("")));
    assert(native_sm3_raw_visual_fog_omission(
        true, true, 1u, 3u, std::nanf(""), std::nanf(""), 0.25f));
    assert(native_sm3_raw_visual_fog_omission(
        true, true, 0u, 3u, 0.2f, 0.8f, std::nanf("")));
    assert(native_sm3_raw_visual_fog_omission(
        true, true, 0u, 2u, std::nanf(""), std::nanf(""), 0.25f));
    assert(!native_sm3_raw_visual_fog_omission(
        false, true, 1u, 0u, 0.f, 1.f, 0.25f));
    assert(!native_sm3_raw_visual_fog_omission(
        true, false, 1u, 0u, 0.f, 1.f, 0.25f));
    assert(!native_sm3_raw_visual_fog_omission(
        true, true, 0u, 0u, 0.f, 1.f, 0.25f));
    assert(!native_sm3_raw_visual_fog_omission(
        true, true, 0u, 3u, 1.f, 0.f, 0.25f));
    assert(!native_sm3_raw_visual_fog_omission(
        true, true, 0u, 1u, 0.f, 1.f, std::nanf("")));
    assert(!native_sm3_raw_visual_fog_omission(
        true, true, 4u, 0u, 0.f, 1.f, 0.25f));
    // Source-matched FVF RAW GPU preview: the table equation overrides
    // inherited vertex mode. An unused live register can be NaN or its COM
    // getter can be intentionally skipped, without inventing source pixels.
    // The RAW tile remains incomplete and never marks full-frame parity.
    assert(native_raw_fvf_fog_visual_admission(
        true, true, 1u, 3u, 1u, std::nanf(""), std::nanf(""), 0.25f));
    assert(native_raw_fvf_fog_visual_admission(
        true, true, 2u, 3u, 0u, std::nanf(""), std::nanf(""), 0.25f));
    assert(native_raw_fvf_fog_visual_admission(
        true, true, 3u, 2u, 0u, 0.2f, 0.8f, std::nanf("")));
    assert(native_raw_fvf_fog_visual_admission(
        true, true, 0u, 3u, 1u, 0.2f, 0.8f, std::nanf("")));
    assert(native_raw_fvf_fog_visual_admission(
        true, true, 0u, 2u, 0u, std::nanf(""), std::nanf(""), 0.5f));
    assert(!native_raw_fvf_fog_visual_admission(
        false, true, 1u, 0u, 0u, 0.f, 1.f, 0.1f));
    assert(!native_raw_fvf_fog_visual_admission(
        true, false, 1u, 0u, 0u, 0.f, 1.f, 0.1f));
    assert(!native_raw_fvf_fog_visual_admission(
        true, true, 1u, 0u, 3u, 0.f, 1.f, 0.1f));
    assert(!native_raw_fvf_fog_visual_admission(
        true, true, 0u, 0u, 0u, 0.f, 1.f, 0.1f));
    assert(!native_raw_fvf_fog_visual_admission(
        true, true, 4u, 0u, 0u, 0.f, 1.f, 0.1f));
    assert(!native_raw_fvf_fog_visual_admission(
        true, true, 3u, 1u, 0u, 0.9f, 0.2f, std::nanf("")));
    assert(!native_raw_fvf_fog_visual_admission(
        true, true, 2u, 0u, 0u, std::nanf(""), std::nanf(""), std::nanf("")));
    assert(!native_raw_fvf_fog_visual_admission(
        true, true, 1u, 0u, 0u, 0.f, 1.f, -0.25f));
    // Source FOGENABLE=TRUE with no active TABLE or VERTEX equation is
    // pixel-equivalent to no fog, even if RANGEFOG/sRGB/caps are inherited.
    // This is NOT permission to ignore an active vertex or W table fog.
    NativeSm3FogReject cause = NativeSm3FogReject::SourceQuery;
    assert(native_sm3_table_zfog_admission(
        true, 0u, 0u, true, true, false, true,
        0u, std::nanf(""), std::nanf(""), -1.0f, fog, &cause));
    assert(!fog.enabled && cause == NativeSm3FogReject::None);
    assert(!native_sm3_table_zfog_admission(
        true, 0u, 2u, true, true, false, true,
        0u, 0.0f, 1.0f, 1.0f, fog, &cause));
    assert(!fog.enabled && cause == NativeSm3FogReject::VertexFog);
    assert(!native_sm3_table_zfog_admission(
        true, 3u, 0u, false, false, true, true,
        0u, 0.0f, 1.0f, 1.0f, fog, &cause));
    assert(!fog.enabled && cause == NativeSm3FogReject::WCapability);
    assert(!native_sm3_table_zfog_admission(
        true, 3u, 0u, false, false, true, false,
        0u, 0.9f, 0.3f, 1.0f, fog, &cause));
    assert(!fog.enabled && cause == NativeSm3FogReject::LinearRange);
    // Live shader-bound table fog must not depend on unused COM float
    // registers. Non-finite *consumed* operands still reject the native Draw.
    assert(native_sm3_table_fog_requires_density(1u));
    assert(native_sm3_table_fog_requires_density(2u));
    assert(!native_sm3_table_fog_requires_density(3u));
    assert(native_sm3_table_fog_requires_linear_bounds(3u));
    assert(!native_sm3_table_fog_requires_linear_bounds(1u));
    for (unsigned mode : {1u, 2u}) {
        NativeSm3FogReject why = NativeSm3FogReject::SourceQuery;
        assert(native_sm3_table_zfog_admission(
            true, mode, 0u, true, false, true, false,
            0xff123456u, std::nanf(""), std::nanf(""), 0.25f,
            fog, &why));
        assert(fog.enabled && why == NativeSm3FogReject::None);
        assert(std::fabs(native_sm3_table_zfog_factor(
            mode, 0.5f, std::nanf(""), std::nanf(""), 0.25f) -
            (mode == 1u ? std::exp(-0.125f) : std::exp(-0.015625f))) < 0.0001f);
        assert(!native_sm3_table_zfog_admission(
            true, mode, 0u, false, false, true, false,
            0u, 0.0f, 1.0f, std::nanf(""), fog, &why));
        assert(why == NativeSm3FogReject::DensityNotFinite && !fog.enabled);
    }
    NativeSm3FogReject linearWhy = NativeSm3FogReject::SourceQuery;
    assert(native_sm3_table_zfog_admission(
        true, 3u, 2u, true, false, true, false,
        0xff567890u, 0.1f, 0.9f, std::nanf(""), fog, &linearWhy));
    assert(fog.enabled && linearWhy == NativeSm3FogReject::None);
    assert(std::fabs(native_sm3_table_zfog_factor(
        3u, 0.5f, 0.1f, 0.9f, std::nanf("")) - 0.5f) < 0.0001f);
    assert(!native_sm3_table_zfog_admission(
        true, 3u, 0u, false, false, true, false,
        0u, std::nanf(""), 1.0f, 0.0f, fog, &linearWhy));
    assert(linearWhy == NativeSm3FogReject::StartNotFinite && !fog.enabled);
    // Live game FVF diffuse, modulate and texture-only now use the shared
    // actual D3D9 table fog equation. Native shader must keep alpha unchanged.
    NativeSm3FogReject fixedWhy = NativeSm3FogReject::SourceQuery;
    assert(native_sm3_table_zfog_admission(
        true, 3u, 2u, true, false, true, false,
        0xff204060u, 0.25f, 0.75f, std::nanf(""), fog, &fixedWhy));
    assert(fog.enabled && fog.rgba[3] == 0.0f &&
           std::fabs(native_sm3_table_zfog_factor(
               3u, 0.5f, 0.25f, 0.75f, std::nanf("")) - 0.5f) < 0.0001f);
    assert(native_sm3_table_zfog_admission(
        true, 1u, 3u, false, false, true, true,
        0xff204060u, std::nanf(""), std::nanf(""), 0.5f,
        fog, &fixedWhy, NativeSm3FogDepth::W));
    assert(fog.enabled && fog.rgba[3] == 1.0f);
    // Vertex-only fog or SRGB output cannot borrow the exact table shader.
    assert(!native_sm3_table_zfog_admission(
        true, 0u, 3u, false, false, true, false,
        0xff204060u, 0.2f, 0.8f, 0.0f, fog, &fixedWhy));
    assert(!fog.enabled && fixedWhy == NativeSm3FogReject::VertexFog);
    assert(!native_sm3_table_zfog_admission(
        true, 3u, 0u, false, true, true, false,
        0xff204060u, 0.2f, 0.8f, 0.0f, fog, &fixedWhy));
    assert(!fog.enabled && fixedWhy == NativeSm3FogReject::Srgb);
    // Native GPU shader and output stays protected: no bypass of Z/W,
    // source shader identity, render target, poison or publication guards.
    std::string ps = "float4 main(R283Input input) : SV_Target0 {\n"
                     "    float4 r283_color = float4(0,0,0,0);\n"
                     "    return r283_color;\n}\n";
    assert(append_native_sm3_table_zfog(ps, true));
    assert(ps.find("register(b4)") != std::string::npos);
    assert(ps.find("r283_fogPosition : SV_Position") != std::string::npos);
    assert(ps.find("rcp(r283_fogPosition.w)") != std::string::npos);
    assert(ps.find("r283_fogColor.a == 1.0f") != std::string::npos);
    assert(ps.find("r283_color.rgb = lerp(") != std::string::npos);
    assert(ps.find("return r283_color;") != std::string::npos);
    assert(!append_native_sm3_table_zfog(ps, true)); // no duplicate injection
    return 0;
}
