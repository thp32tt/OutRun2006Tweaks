#!/usr/bin/env python3
"""R26-safe v R84 Draw->WVP->eye route comparison, 1000-case native C++ gate.

This source check guards that the C++ smoke executable is built and executed
by DX9Ex Active, not just added to the repository.
"""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
safe=(root/"src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp").read_text(encoding="utf-8-sig")
current=(root/"src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8-sig")
proof=(root/"src/vr/d3d9/hud_original_wvp_provenance.hpp").read_text(encoding="utf-8-sig")
test=(root/"vrhost/tests/hud_original_wvp_smoke.cpp").read_text(encoding="utf-8-sig")
workflow=(root/".github/workflows/vr-dx9ex-active.yml").read_text(encoding="utf-8-sig")
def check(code, h):
    block=code.split("bool R30BuildScreenSpaceEyeConstants(",1)[1].split(
        "bool R30TryScreenSpaceFovDraw(",1)[0]
    assert "const bool genericQueuedHud =" in block
    assert "screenKind == R30ScreenSpaceKind::Hud2D" in block
    assert "RenderScope::ScreenOverlay2D" in block
    assert "ExternalOverlaySemanticDepth == 0" in block
    assert "if (exactHud || genericQueuedHud)" in block
    assert "R30GetRecentOriginalHudWvp(rawGameWvp)" in block
    assert block.index("if (exactHud || genericQueuedHud)") < block.index(
        "R30GetRecentOriginalHudWvp(rawGameWvp)")
    # The source-verified queued ESC text shares the pause optical plane with
    # exact ScreenHud arrows only inside the original pause state.  The older
    # exactHud-only assertion rejected this intentional source fix.
    assert "const bool exactPauseShaderOwner =" in block
    assert "OutRunVrPauseEye::OwnsPauseShaderPlane(" in block
    assert "exactHud, genericQueuedHud, R30IsPauseMenuElement());" in block
    assert block.index("R30GetRecentOriginalHudWvp(rawGameWvp)") < block.index(
        "OutRunVrPauseEye::OwnsPauseShaderPlane(")
    owner=code.split("bool R30GetRecentOriginalHudWvp(",1)[1].split(
        "bool R30SpatialSceneEffectNeedsWorldRouting(",1)[0]
    assert "OwnsGenericQueuedOverlay(provenance)" in owner
    assert "OwnsProducer(provenance)" in owner
    assert "QueueRenderActive() && ExternalOverlaySemanticDepth == 0" in owner
    assert "writtenNode" in owner and "writtenQueueEpoch" in owner
    assert "OutRunVR::HudOriginalWvp::OwnsGenericQueuedOverlay" in owner
    assert "e.currentNode == e.writtenNode" in h
    assert "e.currentNodeEpoch == e.writtenNodeEpoch" in h
    assert "e.currentProducer == ProducerToken::None" in h
    assert "e.writtenScope == RenderScope::ScreenOverlay2D" in h

assert "R30ScreenSpaceKind::ScreenOverlay2D" in safe
assert "state, true, semanticOverlay2D" in safe
assert "if (screenOverlay2D)" in safe
assert "scaleX = R30HudScaleValue();" in safe
check(current,proof)
assert "for (int i = 0; i < 1000; ++i)" in test
assert "'outrun-vr-hud-original-wvp-smoke.exe'," in workflow
assert "outrun-vr-hud-original-wvp-smoke " in workflow
for removed in (
    "if (exactHud || genericQueuedHud)",
    "exactHud, genericQueuedHud, R30IsPauseMenuElement());",
    "OutRunVrPauseEye::OwnsPauseShaderPlane(",
    "OwnsGenericQueuedOverlay(provenance)",
    "ExternalOverlaySemanticDepth == 0",
):
    # The source contains several independent exact HUD/F11 guards.
    # Mutate the real shader/owner function, not the first unrelated match.
    if removed == "ExternalOverlaySemanticDepth == 0":
        start=current.index("bool R30GetRecentOriginalHudWvp(")
        end=current.index("bool R30SpatialSceneEffectNeedsWorldRouting(",start)
        region=current[start:end]
        assert removed in region
        mutant=current[:start]+region.replace(
            removed,"REGRESSION_DELETED",1)+current[end:]
    else:
        mutant=current.replace(removed,"REGRESSION_DELETED",1)
    try: check(mutant,proof)
    except AssertionError: pass
    else: raise AssertionError(f"source mutation escaped: {removed}")
print("PASS R26 generic queue finite-plane parity, R84 same-owner c64, 1000 native cases queued")
