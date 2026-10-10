#!/usr/bin/env python3
"""R31 exact OpenXR eye-tail cache-key verifier: one pass + seven mutations."""
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
    if "R31ProjectionMatches(R31EyeCache.inverseProjection, inverseProjection)" not in key:
        errors.append("inverseProjection: missing cache-hit comparison")
    if "R31EyeCache = next;" not in prepare or "if (!R30SupportMatrixFinite(next.eyeTail[eye]))" not in prepare:
        errors.append("transactional finite validation/publish lost")
    if "R31EyeCache = {};" not in source:
        errors.append("Reset cache invalidation lost")
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
        "R31ProjectionMatches(R31EyeCache.inverseProjection, inverseProjection)",
    )
    for marker in negative_markers:
        if source.count(marker) != 1 or not violations(source.replace(marker, "MUTATED", 1)):
            raise SystemExit("R31 EYE CACHE mutation not rejected: " + marker)
    print(f"R31 EYE CACHE PASS: exact pose/FOV/projection key and {len(negative_markers)} negative mutations")


if __name__ == "__main__":
    main()
