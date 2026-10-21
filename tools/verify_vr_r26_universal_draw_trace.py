#!/usr/bin/env python3
"""Static R26+HUD UniversalTrace wiring regression (not runtime VR proof)."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp"
HDR = ROOT / "src/vr/game/universal_draw_trace.hpp"
METHODS = ("DrawPrimitiveDestR30", "DrawIndexedPrimitiveDestR30",
           "DrawPrimitiveUPDestR30", "DrawIndexedPrimitiveUPDestR30")
APIS = ("Primitive", "Indexed", "PrimitiveUP", "IndexedUP")

def valid(src: str, header: str) -> bool:
    if "R26ScreenSpace, R26LowerFallback, R26ExternalImGui, Count" not in header:
        return False
    if "VR R26 DRAW TRACE 5s:" not in src or "DrainWindow()" not in src:
        return False
    if src.count("return R26TraceTopLevelDraw(device,") != 4:
        return False
    if src.count("ScopedDraw::RecordR30EyePair(") < 3:
        return False
    for name, api in zip(METHODS, APIS):
        match = re.search(
            r"HRESULT __stdcall " + name +
            r"\(.*?\{(.*?)(?=\n        HRESULT __stdcall |\n        void R30RollbackHooks)",
            src, re.S)
        if not match:
            return False
        block = match.group(1)
        if not re.search(r"ScopedRenderSemantic drawSemantic\(\s*"
                         r"drawSemanticValue\);\s*return R26TraceTopLevelDraw"
                         r"\(device,\s*OutRunVR::UniversalTrace::DrawApi::"
                         + api + r",", block):
            return False
    for name in ("R30FixedSprite", "R30Xyzrhw", "R26ScreenSpace",
                 "R26LowerFallback", "R26ExternalImGui"):
        if "Route::" + name not in src:
            return False
    if "if (!Settings::VRTelemetry)" not in src:
        return False
    return True

def main():
    src = SRC.read_text(encoding="utf-8")
    hdr = HDR.read_text(encoding="utf-8")
    assert valid(src, hdr), "R26 physical Draw trace contract missing"
    for skill in ("draw-trace", "openxr-debug", "hud-optics",
                  "regression", "texture-debug"):
        p = ROOT / ".github" / "skills" / ("outrun-vr-" + skill) / "SKILL.md"
        data = p.read_text(encoding="utf-8")
        assert data.startswith("---\n"), p
        assert "name: outrun-vr-" + skill in data, p
        assert "description:" in data, p
    assert not valid(src.replace("VR R26 DRAW TRACE 5s:", "TRACE_REMOVED:", 1), hdr)
    for name in METHODS:
        sign = "HRESULT __stdcall " + name
        assert not valid(src.replace(sign, "HRESULT __stdcall MUTATED_" + name, 1), hdr)
    assert not valid(src, hdr.replace("R26LowerFallback", "MissingLowerRoute", 1))
    print("PASS: R26+HUD physical Draw provenance, four API hooks, route and eye telemetry")

if __name__ == "__main__":
    main()
