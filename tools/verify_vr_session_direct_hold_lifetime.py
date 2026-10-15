#!/usr/bin/env python3
"""Regression gate: XR session restart must not retain DirectGPU hold ownership."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "vrhost/src/main_r23.cpp").read_text(encoding="utf-8")


def body(text: str, marker: str) -> str:
    at = text.find(marker)
    if at < 0:
        raise ValueError(f"missing source block: {marker}")
    left = text.find("{", at)
    if left < 0:
        raise ValueError(f"missing opening brace: {marker}")
    depth = 0
    for i in range(left, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[left:i + 1]
    raise ValueError(f"unterminated source block: {marker}")


def ordered(text: str, *markers: str) -> None:
    offsets = [text.find(marker) for marker in markers]
    if any(at < 0 for at in offsets) or offsets != sorted(offsets):
        raise ValueError(f"missing/reordered lifecycle steps: {markers}")


def verify(text: str) -> None:
    retire = body(text, "void R23RetireSessionDirectGpu(")
    ordered(retire, "R23InvalidateDirect(c);",
            "R23ReleaseDirectHoldResources();")
    stop = body(text, "else if (state == XR_SESSION_STATE_STOPPING && running)")
    ordered(stop, "xrEndSession(session)", "cadence.SetRunning(false)",
            "compositor.ReferenceSpaceChanged();",
            "R23RetireSessionDirectGpu(compositor);",
            "OutRunVrR23VerifiedBundle::Invalidate();")
    classic = body(text, "bool R23CommitClassicAfterValidation(")
    ordered(classic, "c.CommitStereoSource()", "R23InvalidateDirectHold();",
            "c.stereoSourceValid_ = true;")
    projection = body(text, "bool R23RenderProjection(")
    if "c.directFrameValid_ && R23DirectHold.valid" not in projection:
        raise ValueError("direct projection must require a valid hold epoch")


verify(source)
# Negative regression: deleting any one critical retirement must fail.
mutants = (
    source.replace("R23RetireSessionDirectGpu(compositor);", "", 1),
    source.replace("R23ReleaseDirectHoldResources();\n    }\n\n    bool R23CommitDirectAfterValidation",
                   "}\n\n    bool R23CommitDirectAfterValidation", 1),
    source.replace("R23InvalidateDirectHold();\n        c.stereoSourceValid_ = true;",
                   "c.stereoSourceValid_ = true;", 1),
)
for i, mutation in enumerate(mutants):
    if mutation == source:
        raise ValueError(f"negative mutation {i} could not be constructed")
    try:
        verify(mutation)
    except ValueError:
        continue
    raise ValueError(f"negative mutation {i} escaped the lifetime verifier")
print("XR session DirectGPU hold-lifetime PASS (including negative mutations)")
