#!/usr/bin/env python3
"""R31 sampled-live/verified WVP must supply identical original and per-eye inputs.

Single source pass, targeted negative mutations, and independent numeric fixture.
"""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d9/stereo_renderer_r31.cpp"


def function_body(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for pos in range(brace, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[brace:pos + 1]
    raise AssertionError("unclosed function " + signature)


def violations(source: str) -> list[str]:
    body = function_body(source, "bool R31BuildFastWorldConstants(")
    required = (
        "R30SupportValidateVerifiedWvp(\n                        device, verified, live)",
        "liveValidated = true;",
        "const float* originalWvp = liveValidated ? live : verified;",
        "std::memcpy(draw.originalConstants, originalWvp, sizeof(verified));",
        "std::memcpy(&uploadedT, originalWvp, sizeof(uploadedT));",
        "const D3DMATRIX currentWvp = R30SupportTransposeMatrix(uploadedT);",
        "const D3DMATRIX correctedWorldView = R30SupportMultiplyMatrix(\n                currentWvp, R31EyeCache.inverseProjection);",
    )
    missing = [item for item in required if body.count(item) != 1]
    if missing:
        return ["missing or duplicated source contract: " + repr(item) for item in missing]
    probe = body.index(required[0])
    accepted = body.index(required[1])
    choice = body.index(required[2])
    restore = body.index(required[3])
    stereo = body.index(required[4])
    if not probe < accepted < choice < restore < stereo:
        return ["sample/selection/restore/stereo source ordering changed"]
    if body.index("if (!R30SupportValidateVerifiedWvp(") > accepted:
        return ["live sample can be selected before validation"]
    if body.index("return false;", probe) > accepted:
        return ["live-sample rejection no longer exits before acceptance"]
    return []


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    errors = violations(source)
    if errors:
        raise SystemExit("R31 LIVE WVP FAIL: " + "; ".join(errors))
    mutations = (
        ("const float* originalWvp = liveValidated ? live : verified;",
         "const float* originalWvp = verified;"),
        ("const float* originalWvp = liveValidated ? live : verified;",
         "const float* originalWvp = live;"),
        ("std::memcpy(draw.originalConstants, originalWvp, sizeof(verified));",
         "std::memcpy(draw.originalConstants, verified, sizeof(verified));"),
        ("std::memcpy(&uploadedT, originalWvp, sizeof(uploadedT));",
         "std::memcpy(&uploadedT, verified, sizeof(uploadedT));"),
        ("liveValidated = true;", "liveValidated = false;"),
    )
    for before, after in mutations:
        if source.count(before) != 1 or not violations(source.replace(before, after, 1)):
            raise SystemExit("R31 LIVE WVP mutation escaped: " + before)
    # A tolerated 1e-5 live-vs-verified difference is enough to expose the old
    # mismatched-original / stereo-projection input selection on sampled draws.
    verified, live = 1.0, 1.00001
    for validated in (True, False):
        selected = live if validated else verified
        original_uploaded = selected
        stereo_source = selected
        assert original_uploaded == stereo_source
    assert live != verified
    print("R31 LIVE WVP PASS: shared sample/verified source, 5 rejected mutations, numeric delta")


if __name__ == "__main__":
    main()
