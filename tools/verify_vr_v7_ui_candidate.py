#!/usr/bin/env python3
"""Fail-closed static guard for the R69 V7 OutRun UI candidate."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")

errors = []

renderer = read("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp")
ui = read("src/hooks_uiscaling.cpp")
runner = read("tools/Run-OutRunVRTest.ps1")
selector = read("tools/Select-OutRunVRBackend.ps1")
start = read("tools/START_HERE_VR_TEST.cmd")

required_renderer = [
    "R30SkyGlowAppliedEpoch",
    "R30ApplyStereoSkyGlowOnce",
    "if (R30CaptureSkyGlowSceneBeforeHud(device))",
    "R30ApplyStereoSkyGlowOnce(device);",
    "Settings::SkyGlowFactor.get(), 1, 16",
    "VR V7 SKY GLOW: requested factor honored + pre-HUD composite",
]
for item in required_renderer:
    if item not in renderer:
        errors.append("renderer missing: " + item)

if "constexpr int factor = 2;" in renderer:
    errors.append("renderer still forces SkyGlow factor=2")

for rva in ("0x460F1", "0x463D6", "0x46410"):
    if rva not in ui:
        errors.append("runtime-proven option-arrow RVA missing: " + rva)

for asset in ("0x3004A", "0x3004B", "0x2C0251", "0x2C0254"):
    if asset not in ui:
        errors.append("option-arrow asset guard missing: " + asset)

if "'R69_V7_UIFIX' { $semanticMode='0'; $hudExperimentMode='4' }" not in runner:
    errors.append("V7 mode4 runtime mapping missing")
if '"R69_V7_UIFIX"' not in selector:
    errors.append("V7 selector variant missing")
if "-VariantId R69_V7_UIFIX" not in start:
    errors.append("one-click launcher does not select V7")

# Preserve exact-owner priority: mode4 may widen only generic ScreenOverlay2D;
# exact sticky queue scopes still resolve first in render_semantics.hpp.
sem = read("src/vr/game/render_semantics.hpp")
exact = "if (mode >= 3 && IsExactHudScope(CurrentQueueExactScope))"
generic = "if (mode >= 4 && CurrentScope == RenderScope::ScreenOverlay2D)"
if exact not in sem or generic not in sem or sem.index(exact) > sem.index(generic):
    errors.append("mode4 no longer preserves exact-owner priority")

if errors:
    for e in errors:
        print("V7_UI_CANDIDATE_ERROR:", e, file=sys.stderr)
    raise SystemExit(2)

print("V7 UI candidate static guard passed.")
