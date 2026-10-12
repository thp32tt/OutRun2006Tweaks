#!/usr/bin/env python3
"""R30 classification-only projection accessor: source and negative regression."""
import math
import pathlib
import random

ROOT = pathlib.Path(__file__).resolve().parents[1]
HEADER = (ROOT / "src/vr/ipc/protocol.hpp").read_text(encoding="utf-8")
RENDERER = (ROOT / "src/vr/game/outrun_renderer.cpp").read_text(encoding="utf-8")
R30 = (ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def source_contract(renderer=RENDERER, r30=R30):
    signature = renderer.split(
        "bool GetRendererProjectionSignature(float& m34, float& m44) noexcept", 1
    )
    require(len(signature) == 2, "missing renderer signature accessor")
    body = signature[1].split("bool GetLastVerifiedWvp(", 1)[0]
    for invariant in (
        "ValidateRendererGlobals()", "RendererProjection",
        "CullingProjectionOverridden", "CullingProjectionSaved",
        "std::memcpy(&projection, RendererProjection, sizeof(projection))",
        "MatrixFinite(projection)", "m34 = projection._34;",
        "m44 = projection._44;", "return true;",
    ):
        require(invariant in body, "projection accessor contract missing: " + invariant)
    require("bool GetRendererProjectionSignature(float& m34, float& m44) noexcept;" in HEADER,
            "declaration must match independent translation units")
    cls = r30.split("R30ScreenSpaceKind R30ClassifyScreenSpacePass(", 1)
    require(len(cls) == 2, "missing classifier")
    cls = cls[1].split("// Only the OpenXR pose/FOV", 1)[0]
    require("R29OwnerTargetIsBackBuffer()" in cls, "main backbuffer identity lost")
    require("GetRendererProjectionSignature(m34, m44)" in cls, "full-matrix classifier not optimized")
    require("ClassifyProjectionSignature(m34, m44)" in cls, "signature elements reversed")
    require("GetRendererBaseProjection(" not in cls, "full matrix copied on hot Draw route")
    for guard in ("ProjectionClass::Orthographic2D", "ProjectionClass::Perspective3D",
                  "R29OwnerTryGetEffectTelemetrySnapshot(effect)", "GetRenderState(",
                  "D3DRS_ZENABLE", "D3DRS_ALPHABLENDENABLE",
                  "D3DRS_ALPHATESTENABLE"):
        require(guard in cls, "HUD / fragile effect fallback lost: " + guard)


def classify(m34, m44):
    near = lambda v, ref: abs(v - ref) <= 0.05
    if near(abs(m34), 1.0) and near(m44, 0.0):
        return "perspective"
    if near(m34, 0.0) and near(abs(m44), 1.0):
        return "orthographic"
    return "unknown"


def model_cases():
    rng = random.Random(681)
    cases = [
        (-1.0, 0.0), (1.0, 0.0), (0.0, 1.0), (0.0, -1.0),
        (0.75, 0.0), (0.0, 0.75), (1.0, 1.0),
        (float("nan"), 0.0), (float("inf"), 0.0),
    ]
    cases.extend((rng.uniform(-1.2, 1.2), rng.uniform(-1.2, 1.2))
                 for _ in range(4000))
    for m34, m44 in cases:
        projection = [rng.uniform(-9, 9) for _ in range(16)]
        projection[11], projection[15] = m34, m44
        finite = all(math.isfinite(v) for v in projection)
        old = classify(projection[11], projection[15]) if finite else "invalid"
        new = classify(m34, m44) if finite else "invalid"
        require(old == new, "projection classification changed")
        # Fail closed even when unrelated matrix elements become nonfinite.
        projection[3] = math.nan
        require(not all(math.isfinite(v) for v in projection),
                "full matrix validation cannot be replaced by pair-only finiteness")


def negative_mutations():
    marker = "m34 = projection._34;"
    for altered in (
        RENDERER.replace(marker, "m34 = projection._44;", 1),
        RENDERER.replace("m44 = projection._44;", "m44 = projection._34;", 1),
        RENDERER.replace("MatrixFinite(projection)", "true", 1),
        RENDERER.replace("CullingProjectionSaved", "projection", 1),
    ):
        try:
            source_contract(renderer=altered)
        except AssertionError:
            pass
        else:
            raise AssertionError("invalid projection fastpath mutation survived")
    try:
        source_contract(r30=R30.replace(
            "ClassifyProjectionSignature(m34, m44)",
            "ClassifyProjectionSignature(m44, m34)", 1))
    except AssertionError:
        pass
    else:
        raise AssertionError("swapped projection classification survived")


if __name__ == "__main__":
    source_contract()
    model_cases()
    negative_mutations()
    print("PASS: R30 projection signature, 4009 matrix cases, 5 negative mutations")
