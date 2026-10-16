#!/usr/bin/env python3
"""R26 HMD-backed source-owned generic SpriteQueue HUD finite-plane regression."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=(root/"src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8-sig")
sem=(root/"src/vr/game/render_semantics.hpp").read_text(encoding="utf-8-sig")
safe=(root/"src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp").read_text(encoding="utf-8-sig")
policy="QueueOverlayNeedsFiniteHudPlane("
def verify(src,pol):
    block=src.split("bool R30ConfigureXyzrhwWorldEffect(",1)[1].split(
        "// Smoke/sand can redraw a static VB/IB span",1)[0]
    queue=block.split("// R26_SAFE HMD baseline:",1)[1]
    for token in ("CapturePhysicalDrawCommand()",policy,
                  "physical.scope, physical.queued",
                  "ExternalOverlaySemanticDepth != 0",
                  "R30BuildStageExtensionXyzrhwEyePlane(state, baseProjection)",
                  "return valid;"):
        assert token in queue, f"missing queued-HUD proof: {token}"
    assert block.index("CanReprojectFiniteResultHudPlane(") < block.index(
        "CorroboratesHud(") < block.index(
        "QueueOverlayNeedsFiniteHudPlane(")
    assert "RenderScope::ScreenOverlay2D && queued && !external" in pol
    assert "static_assert(!QueueOverlayNeedsFiniteHudPlane(" in pol
    assert "RenderScope::WorldParticle, true, false" in pol
    assert "RenderScope::ScreenOverlay2D, true, true" in pol

assert "state.screenOverlay2D = semanticOverlay2D;" in safe
assert "state.hudWorldLockValid = true;" in safe
verify(source,sem)
for tok in ("CapturePhysicalDrawCommand()",
             "ExternalOverlaySemanticDepth != 0",
             "R30BuildStageExtensionXyzrhwEyePlane(state, baseProjection)",
             "QueueOverlayNeedsFiniteHudPlane("):
    anchor=source.index("// R26_SAFE HMD baseline:")
    mutated=source[:anchor]+source[anchor:].replace(tok,"REMOVED_FOR_NEGATIVE_TEST",1)
    try: verify(mutated,sem)
    except AssertionError: pass
    else: raise AssertionError(f"negative mutation failed: {tok}")
bad=sem.replace("RenderScope::ScreenOverlay2D && queued && !external",
                "RenderScope::ScreenOverlay2D && queued",1)
try: verify(source,bad)
except AssertionError: pass
else: raise AssertionError("F11 bypass mutation escaped")
print("PASS R84 generic queue-owned HUD finite bilateral plane; R26 source proof; F11/world veto; Quest HMD UNTESTED")
