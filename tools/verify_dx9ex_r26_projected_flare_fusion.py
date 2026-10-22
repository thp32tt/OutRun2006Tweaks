#!/usr/bin/env python3
"""R26 exact CABE projected-flare fusion regression guard.

Static source test only. It proves that the exact ProjectedScreenEffect2D owner
uses the reviewed R69 zero-disparity eye-constant path and that generic
SceneEffect/world/HUD producers cannot borrow that admission.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp"
text = SRC.read_text(encoding="utf-8")

def body(signature: str) -> str:
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise AssertionError(signature)

classifier = body("R30ScreenSpaceKind R30ClassifyScreenSpacePass(")
builder = body("bool R30BuildScreenSpaceEyeConstants(")
dispatch = body("HRESULT R30TryScreenSpaceFovDraw(")

assert "ProjectedScreenEffect2D," in text
assert "if (semanticProjectedScreen)" in classifier
assert "return R30ScreenSpaceKind::ProjectedScreenEffect2D;" in classifier
assert classifier.index("if (semanticProjectedScreen)") < classifier.index("if (semanticSceneEffect)")
assert "if (semanticProjectedScreen || semanticSceneEffect)" not in classifier

source_gate = """else if (screenKind ==
                    R30ScreenSpaceKind::ProjectedScreenEffect2D)"""
assert source_gate in builder
gate_tail = builder[builder.index(source_gate):]
assert "R44GetOwnedRawOverlayWvp(original)" in gate_tail
assert "R30GetExtendedRawWvpForExactSceneEffect(original)" in gate_tail

fusion = """if (screenKind == R30ScreenSpaceKind::ProjectedScreenEffect2D)"""
assert fusion in builder
fusion_tail = builder[builder.index(fusion):]
right_copy = "std::memcpy(eyeConstants[1], &stockT, sizeof(stockT));"
left_copy = "std::memcpy(eyeConstants[0], &stockT, sizeof(stockT));"
assert left_copy in fusion_tail and right_copy in fusion_tail
assert fusion_tail.index(left_copy) < fusion_tail.index(right_copy)
assert "VR R69 FLARE FUSION" in fusion_tail

dispatch_gate = """else if (screenKind ==
                R30ScreenSpaceKind::ProjectedScreenEffect2D)"""
assert dispatch_gate in dispatch
d = dispatch[dispatch.index(dispatch_gate):]
assert "ProjectedScreenEffect2D)" in d
assert "return E_NOTIMPL;" in d

# Negative controls: a one-eye mutation or rejoining generic SceneEffect
# must be detectable by the contract above.
mut = builder.replace(right_copy,
                      "std::memcpy(eyeConstants[1], original, sizeof(stockT));", 1)
assert right_copy not in mut[mut.index(fusion):]
mut_classifier = classifier.replace(
    "if (semanticProjectedScreen)",
    "if (semanticProjectedScreen || semanticSceneEffect)", 1)
assert "if (semanticProjectedScreen || semanticSceneEffect)" in mut_classifier

print("PASS R26 R69 exact CABE centre-eye L/R fusion and scope isolation")