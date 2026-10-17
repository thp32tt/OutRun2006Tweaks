#!/usr/bin/env python3
"""Tamper checks for the audited partial game DSV-only GPU clear admission."""
from pathlib import Path
from verify_dx11_activation_boundary import (
    DRAW_DISPATCH, audit_native_partial_depth_clear,
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
# Guard the exact six reviewed GPU dispatch locations: four genuine
# per-eye commands and two non-evidence depth/stretch postpass triangles.
# A new source Draw still requires explicit owner/activation audit.
expected_dispatches = [
    "->Draw(", "->DrawIndexed(",
    "->DrawInstanced(", "->DrawIndexedInstanced(",
    "->Draw(", "->Draw(",
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
print("DX11 native partial DSV draw audit: PASS (positive + negative tamper)")
