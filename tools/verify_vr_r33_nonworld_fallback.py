#!/usr/bin/env python3
"""R84 source scope: screen/SkyGlow cannot inherit road WVP on ANY R33 fallback.

Quest3 verification is separate; this is a compiled-source positive/negative
guard for a concrete classification-to-dispatch failure path.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sem = (root / "src/vr/game/render_semantics.hpp").read_text(encoding="utf-8-sig")
src = (root / "src/vr/d3d9/stereo_renderer_r33.cpp").read_text(encoding="utf-8-sig")
r29 = (root / "src/vr/d3d9/stereo_renderer_r29.cpp").read_text(encoding="utf-8-sig")
r30 = (root / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8-sig")
r31 = (root / "src/vr/d3d9/stereo_renderer_r31.cpp").read_text(encoding="utf-8-sig")

def check_sem(code: str) -> None:
    scope = code.split("constexpr bool DeniesGenericWorldFallback()", 1)[1].split(
        "\n        }", 1)[0]
    for name in ("ScreenHud", "ScreenOverlay2D", "ProjectedWorldMarker2D",
                 "ProjectedScreenEffect2D", "SkyGlow"):
        assert "scope == RenderScope::" + name in scope, name
    for name in ("WorldParticle", "WorldBillboard", "SceneEffect"):
        assert "scope == RenderScope::" + name not in scope, name
    assert "static_assert(PhysicalDrawCommand{RenderScope::SkyGlow," in code
    assert "static_assert(!PhysicalDrawCommand{RenderScope::WorldParticle," in code

def check_dispatch(code: str) -> None:
    block = code.split("HRESULT R33Dispatch(", 1)[1].split(
        "HRESULT __stdcall DrawPrimitiveDestR33(", 1)[0]
    assert "const auto drawCommand =" in block
    assert "CapturePhysicalDrawCommand();" in block
    assert block.count("drawCommand.DeniesGenericWorldFallback()") == 3, (
        "must protect failed resync, unclassified fast world, and lower fallback")
    a = block.index("if (!resyncAlreadyFlushed)")
    b = block.index("// Classify exactly once", a)
    assert "drawCommand.DeniesGenericWorldFallback()" in block[a:b]
    c = block.index("else\n            {\n                // Screen pass classified as None")
    d = block.index("const auto fast = R33TryFastWorld(device,", c)
    assert "drawCommand.DeniesGenericWorldFallback()" in block[c:d]
    e = block.index("// Preserve the same lower R29 fail-closed policy", d)
    assert "drawCommand.DeniesGenericWorldFallback()" in block[d:e]
    assert block.index("const bool directCarShadow =") < a
    assert "R33TryHud(device, screenKind" in block
    assert "return fallbackToR29();" in block
    assert "return actualDraw();" in block[c:d]

check_sem(sem)
check_dispatch(src)
assert "R28CanRebindVerifiedWorld(" in r29
assert "if (allowVerifiedWorldRebind &&" in r29
assert "R30ClassifyScreenSpacePass(" in r30
assert "if (ownedOverlay)" in r30 and "return R30ScreenSpaceKind::None;" in r30
assert "R31BuildFastWorldConstants(" in r31
for needle in ("ScreenHud","ScreenOverlay2D","ProjectedWorldMarker2D",
               "ProjectedScreenEffect2D","SkyGlow"):
    # Mutate this method only: other independent semantic helpers also
    # contain ScreenHud / ScreenOverlay2D checks and must remain unchanged.
    marker = "constexpr bool DeniesGenericWorldFallback() const noexcept"
    before, owner = sem.split(marker, 1)
    owner_start, owner_tail = owner.split("\n        }", 1)
    source_token = "scope == RenderScope::" + needle
    assert source_token in owner_start
    mutant = before + marker + owner_start.replace(
        source_token, "false /* mutation */", 1) + "\n        }" + owner_tail
    try: check_sem(mutant)
    except AssertionError: pass
    else: raise AssertionError(f"semantic veto removal escaped: {needle}")
for occurrence in range(3):
    needle = "drawCommand.DeniesGenericWorldFallback()"
    pos = -1
    for _ in range(occurrence + 1):
        pos = src.find(needle, pos + 1)
    assert pos >= 0
    mutant = src[:pos] + "false /* mutation */" + src[pos + len(needle):]
    try: check_dispatch(mutant)
    except AssertionError: pass
    else: raise AssertionError(f"R33 exit {occurrence} mutation escaped")
print("PASS R33 scope veto: 5 screen sources/3 dispatch exits; world unaffected; negative mutations; Quest3 UNTESTED")
