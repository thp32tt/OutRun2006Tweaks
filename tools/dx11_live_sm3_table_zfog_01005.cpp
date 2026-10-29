#include "live_game_sm3_table_fog.hpp"
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
    std::string ps = "float4 main(R283Input input) : SV_Target0 {\n"
                     "    float4 r283_color = float4(0,0,0,0);\n"
                     "    return r283_color;\n}\n";
    assert(append_native_sm3_table_zfog(ps, true));
    assert(ps.find("register(b4)") != std::string::npos);
    assert(ps.find("r283_fogPosition : SV_Position") != std::string::npos);
    assert(ps.find("r283_color.rgb = lerp(") != std::string::npos);
    assert(ps.find("return r283_color;") != std::string::npos);
    assert(!append_native_sm3_table_zfog(ps, true)); // no duplicate injection
    return 0;
}
