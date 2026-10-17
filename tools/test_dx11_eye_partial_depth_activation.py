#!/usr/bin/env python3
"""Tamper checks for the audited partial game DSV-only GPU clear admission."""
from pathlib import Path
from verify_dx11_activation_boundary import (
    DRAW_DISPATCH, audit_native_partial_depth_clear,
    audit_native_partial_color_clear,
)

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/vr/d3d11/native_game_stereo_submission.cpp").read_text(
    encoding="utf-8")
probe = (ROOT / "tools/dx11_native_transport_probe.cpp").read_text(
    encoding="utf-8")

assert not audit_native_partial_depth_clear(source, probe), "valid DSV audit failed"
# The timeline's valid bounded Clear must replay through GPU Draw, while its
# negative companion must actually lie outside the eye (not an old valid box).
assert "invalidPartialDepth.entries[1][0].rect = {-1, 1, 4, 4};" in probe
assert "zRect.kind = SourceClear::Kind::FullDepthStencil;" in probe
# Guard the exact seven reviewed GPU dispatch locations: four genuine
# per-eye commands and three non-evidence color/depth/stretch GPU triangles.
# A new source Draw still requires explicit owner/activation audit.
expected_dispatches = [
    "->Draw(", "->DrawIndexed(",
    "->DrawInstanced(", "->DrawIndexedInstanced(",
    "->Draw(", "->Draw(", "->Draw(",
]
assert DRAW_DISPATCH.findall(source) == expected_dispatches, (
    "unexpected native Draw dispatch")
# Removing the OM0 unbind would let a helper write a color RTV instead of
# replacing only depth/stencil under exactly scoped per-eye provenance.
assert audit_native_partial_depth_clear(
    source.replace(
        "context->OMSetRenderTargets(0u, nullptr, depthView);",
        "context->OMSetRenderTargets(1u, &target, depthView);", 1),
    probe), "color RTV tamper slipped through"
# A helper which does not preserve full MRT/IA/shader state after the GPU fill
# could corrupt the next game's eye Draw and the original D3D9 fallback.
assert audit_native_partial_depth_clear(
    source.replace("if (!saved.valid()) return false;", "", 1), probe
), "state guard tamper slipped through"
# Source coverage cannot silently lose the negative real-game RECT regression.
assert audit_native_partial_depth_clear(
    source, probe.replace(
        "!encoder.clear_depth_stencil(0.5f, 0u, true, true, &badRect)", ""
    )), "bad-RECT regression removal slipped through"
# Reject a real partial HUD/menu Clear being widened into a whole-eye
# DSV operation, and reject deleting the malformed two-eye preflight.
assert audit_native_partial_depth_clear(
    source.replace(
        "route == live_game_stereo::NativeDepthClearRoute::PartialRaster",
        "route == live_game_stereo::NativeDepthClearRoute::FullDsv", 1),
    probe), "cropped depth-region widening slipped through"
assert audit_native_partial_depth_clear(
    source.replace(
        "route == live_game_stereo::NativeDepthClearRoute::Reject",
        "route == live_game_stereo::NativeDepthClearRoute::FullDsv", 1),
    probe), "invalid depth-region admission slipped through"
# The caller still owns the boundary: a fifth unauthorized Draw is not made
# legitimate by the narrowly reviewed depth-only callback.
assert DRAW_DISPATCH.findall(source + "\ncontext->Draw(8u, 0u);") != expected_dispatches

# A D3D11.0 source TARGET Clear uses one strictly cropped GPU shader Draw,
# never authorizes unrelated game draws or an unbounded full-eye color Clear.
assert not audit_native_partial_color_clear(source), "valid color audit failed"
assert audit_native_partial_color_clear(
    source.replace(
        "context->OMSetRenderTargets(1u, &target, nullptr);",
        "context->OMSetRenderTargets(0u, nullptr, nullptr);", 1),
), "missing owned eye RTV slipped through"
assert audit_native_partial_color_clear(
    source.replace(
        "context->RSSetState(nullptr); // game Clear ignores saved scissor/cull",
        "", 1),
), "inherited scissor/cull tamper slipped through"
assert audit_native_partial_color_clear(
    source.replace(
        "ds.DepthEnable = FALSE;", "ds.DepthEnable = TRUE;", 1),
), "inherited depth test tamper slipped through"
assert audit_native_partial_color_clear(
    source.replace(
        "case live_game_stereo::NativeColorClearRoute::ShaderRaster:",
        "case live_game_stereo::NativeColorClearRoute::FullRtv:", 1),
), "cropped TARGET clear widened into full-eye Clear"
assert audit_native_partial_color_clear(
    source.replace(
        'GetProcAddress(compiler, "D3DCompile")', "nullptr", 1),
), "missing D3D11.0 preflight slipped through"
print("DX11 native partial DSV/TARGET GPU draw audit: PASS (positive + negative tamper)")
