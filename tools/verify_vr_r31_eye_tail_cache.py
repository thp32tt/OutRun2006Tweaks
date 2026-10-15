#!/usr/bin/env python3
"""R31 exact OpenXR eye cache and Reset telemetry-epoch verifier: nine mutations."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d9/stereo_renderer_r31.cpp"


def body(source: str, name: str) -> str:
    start = source.index(name)
    brace = source.index("{", start)
    depth = 0
    for pos in range(brace, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[brace:pos + 1]
    raise AssertionError("unclosed body: " + name)


def violations(source: str) -> list[str]:
    errors = []
    cache = body(source, "struct R31EyeTailCache")
    prepare = body(source, "bool R31PrepareEyeTailCache(")
    key = prepare.split("return true;", 1)[0]
    fill = prepare.split("R31EyeTailCache next{};", 1)[1].split("for (int eye", 1)[0]
    for member in ("eyeOrientation", "eyeOffset", "eyeFov"):
        if f"decltype(OutRunVRRenderer::LatchedStereoFrame::{member}) {member}" not in cache:
            errors.append(member + ": missing cache field")
        if f"std::memcmp(R31EyeCache.{member}, stereo.{member}," not in key:
            errors.append(member + ": missing cache-hit comparison")
        if f"sizeof(stereo.{member})) == 0" not in key:
            errors.append(member + ": invalid comparison extent")
        if f"std::memcpy(next.{member}, stereo.{member}," not in fill:
            errors.append(member + ": missing cache-miss capture")
    # Inversion is now cache-miss-only; projection equality is the key.
    # The old inverse equality check required a needless inversion per draw.
    if "R31ProjectionMatches(R31EyeCache.projection, projection)" not in key:
        errors.append("projection: missing exact cache-hit comparison")
    if "R30SupportGetInverseProjection(" in key:
        errors.append("inverseProjection: recomputed before cache-hit return")
    if "R30SupportGetInverseProjection(projection, inverseProjection)" not in fill:
        errors.append("inverseProjection: missing cache-miss inverse calculation")
    if "next.inverseProjection = inverseProjection;" not in fill:
        errors.append("inverseProjection: missing cache-miss snapshot")
    if "D3DMATRIX composedEyeTail[2]{};" not in cache:
        errors.append("composedEyeTail: cache storage missing")
    if "next.composedEyeTail[eye] = R30SupportMultiplyMatrix(\n                    inverseProjection, next.eyeTail[eye]);" not in prepare:
        errors.append("composedEyeTail: cache-miss composition missing")
    if "if (!R30SupportMatrixFinite(next.composedEyeTail[eye]))" not in prepare:
        errors.append("composedEyeTail: nonfinite cache publish possible")
    caller = body(source, "bool R31BuildFastWorldConstants(")
    if "R30SupportGetInverseProjection(" in caller:
        errors.append("inverseProjection: caller performs per-draw inversion")
    if "R31PrepareEyeTailCache(stereo, projection)" not in caller:
        errors.append("inverseProjection: caller does not use cached inverse")
    # Busy-stage world draws still fetch the verified projection to bind the
    # generation, but their unchanged key must not rescan 16 floats for NaN
    # after R31PrepareEyeTailCache proved that exact projection finite.
    if "R30SupportMatrixFinite(projection)" in caller:
        errors.append("projection: redundant finite scan on every world draw")
    finite_guard = "if (!R30SupportMatrixFinite(projection))"
    if prepare.count(finite_guard) != 1:
        errors.append("projection: missing/duplicated cache-miss finite gate")
    else:
        try:
            if not (prepare.index("return true;") <
                    prepare.index(finite_guard) <
                    prepare.index("R30SupportGetInverseProjection(") <
                    prepare.index("R31EyeCache = next;")):
                errors.append("projection: finite check must precede inversion/publish on cache miss")
        except ValueError:
            errors.append("projection: miss-only finite ordering anchor lost")
    if "currentWvp, R31EyeCache.composedEyeTail[eye]);" not in caller:
        errors.append("composedEyeTail: per-draw path still runs a third multiply")
    if "correctedWorldView" in caller:
        errors.append("composedEyeTail: legacy per-draw inverse multiplication remains")
    if "R31EyeCache = next;" not in prepare or "if (!R30SupportMatrixFinite(next.eyeTail[eye]))" not in prepare:
        errors.append("transactional finite validation/publish lost")
    reset = body(source, "inline void R31ResetFastPathState()")
    if "R31EyeCache = {};" not in reset:
        errors.append("Reset cache invalidation lost")
    if "R31TelemetryResetFrameWindow();" not in reset or "R31Window = {};" not in reset:
        errors.append("Reset/ResetEx must clear frame and performance windows")
    return errors


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    errors = violations(source)
    if errors:
        raise SystemExit("R31 EYE CACHE FAIL: " + "; ".join(errors))
    negative_markers = (
        "std::memcmp(R31EyeCache.eyeOrientation, stereo.eyeOrientation,",
        "std::memcmp(R31EyeCache.eyeOffset, stereo.eyeOffset,",
        "std::memcmp(R31EyeCache.eyeFov, stereo.eyeFov,",
        "std::memcpy(next.eyeOrientation, stereo.eyeOrientation,",
        "std::memcpy(next.eyeOffset, stereo.eyeOffset,",
        "std::memcpy(next.eyeFov, stereo.eyeFov,",
        "R31ProjectionMatches(R31EyeCache.projection, projection)",
        "R30SupportGetInverseProjection(projection, inverseProjection)",
        "if (!R30SupportMatrixFinite(projection))",
        "next.inverseProjection = inverseProjection;",
        "next.composedEyeTail[eye] = R30SupportMultiplyMatrix(",
        "if (!R30SupportMatrixFinite(next.composedEyeTail[eye]))",
        "currentWvp, R31EyeCache.composedEyeTail[eye]);",
    )
    for marker in negative_markers:
        if source.count(marker) != 1 or not violations(source.replace(marker, "MUTATED", 1)):
            raise SystemExit("R31 EYE CACHE mutation not rejected: " + marker)
    reset = body(source, "inline void R31ResetFastPathState()")
    reset_markers = ("R31EyeCache = {};", "R31Window = {};")
    for marker in reset_markers:
        if reset.count(marker) != 1:
            raise SystemExit("R31 RESET marker not unique: " + marker)
        mutated_reset = reset.replace(marker, "MUTATED", 1)
        if not violations(source.replace(reset, mutated_reset, 1)):
            raise SystemExit("R31 RESET negative mutation survived: " + marker)
    print(f"R31 EYE CACHE PASS: exact pose/FOV/projection and reset-epoch guards; {len(negative_markers) + len(reset_markers)} negative mutations")


if __name__ == "__main__":
    main()
