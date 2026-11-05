#!/usr/bin/env python3
"""Regress live game shader and blend cache pressure without changing fallback."""
from pathlib import Path

source = Path("src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = Path("src/vr/d3d11/native_game_live_shader_cache.hpp").read_text()

def assert_integrated(text: str) -> None:
    blend = text.split("const auto blendKey = sm3_live_blend_key", 1)[1].split(
        "rejectionStage = 7u", 1)[0]
    programs = text.split("const auto key = live_sm3_pipeline_identity", 1)[1].split(
        "auto& pipeline = it->second;", 1)[0]
    method = "LiveGameShaderCacheReplacement::retire_oldest_if_full("
    assert method in blend and method in programs, "Both actual D3D11 caches must recover"
    assert blend.index("CreateBlendState(") < blend.index(method) < blend.index(
        "liveSm3BlendStates.emplace("), "Never evict on failed D3D11 blend creation"
    assert programs.index("compile_native_live_sm3_program(") < programs.index(
        method) < programs.index("liveSm3Pipelines.emplace("), "Never evict on shader failure"
    assert "lastUse = ++s.liveSm3UseOrdinal" in text, "Missed game-Draw recency"
    assert text.count("lastUse = ++s.liveSm3UseOrdinal") == 2
    assert "s.liveSm3Pipelines.size() >= 64u) return false" not in text
    assert "s.liveSm3BlendStates.size() >= 64u) return false" not in text

assert "cache.erase(oldest);" in header
assert_integrated(source)
method = "LiveGameShaderCacheReplacement::retire_oldest_if_full("
for anchor in ("const auto blendKey = sm3_live_blend_key",
               "const auto key = live_sm3_pipeline_identity"):
    idx = source.index(anchor)
    call = source.index(method, idx)
    tampered = source[:call] + source[call:].replace(method, "/* removed */ (", 1)
    try:
        assert_integrated(tampered)
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError("Destructive negative regression escaped: " + anchor)
print("01004 live SM3 program/blend cache integration and destructive checks PASS")
