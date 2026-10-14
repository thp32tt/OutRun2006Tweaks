#!/usr/bin/env python3
"""Fail closed if live-game diagnostic pixel shaders escape Reset/readiness checks."""
from pathlib import Path
import re

source = Path("src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
ready = source.split("bool ensure_pipeline(State& s) noexcept {", 1)[1].split("return true;", 1)[0]
reset = source.split("void before_game_reset() noexcept {", 1)[1].split("s.backend.shutdown();", 1)[0]
reinit = source.split("bool ensure_pipeline(State& s) noexcept {", 1)[1].split("s.backend.shutdown();", 1)[0]
checks = {
    "blendTextureAlphaPmInverseTextureAlphaPs": True,
    "blendTextureAlphaPmAddFactorAlphaPs": True,
    "blendTextureAlphaPmAddSmoothFactorAlphaPs": True,
}
for name in checks:
    assert re.search(r"\\bs\\." + name + r"\\b", ready), f"{name}: missing from ready gate"
    assert f"s.{name}.Reset();" in reset, f"{name}: missing from before_game_reset"
    assert f"s.{name}.Reset();" in reinit, f"{name}: missing from ensure_pipeline rebuild"
print("DX11 live-game shader readiness and Reset parity: PASS")
