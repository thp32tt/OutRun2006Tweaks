#!/usr/bin/env python3
"""DX9Ex review105 TEST-only source guard for F11 frustum and shader identity.

This gate is not a claim of headset optical correctness. The Windows build
runs the constexpr C++ F11 tests; these checks reject accidental source drift.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
F11 = ROOT / "src/vr/d3d9/f11_screen_2d.hpp"
SHADER = ROOT / "src/vr/d3d9/shader_fingerprint_gpl.hpp"


def check_f11(source: str) -> None:
    header = source.split("constexpr bool Build(", 1)[1].split(
        "constexpr bool TestEqualEyes()", 1
    )[0]
    for token in (
        "fov[0].left > fov[1].left",
        "fov[0].right < fov[1].right",
        "fov[0].down > fov[1].down",
        "fov[0].up < fov[1].up",
        "commonWidth <= 0.05f",
        "commonHeight <= 0.05f",
        "out[0] = candidate[0];",
        "out[1] = candidate[1];",
    ):
        assert token in header, token
    assert "0.5f * (fov[0].left + fov[1].left)" not in header
    assert "TestIntersectionInsideBothEyes()" in source
    assert "TestDisjointEyesKeepBoth()" in source
    assert "static_assert(TestIntersectionInsideBothEyes())" in source
    assert "static_assert(TestDisjointEyesKeepBoth())" in source


def check_shader(source: str) -> None:
    body = source.split("inline ShaderPair CaptureCurrent(", 1)[1].split(
        "inline bool RememberPair(", 1
    )[0]
    assert "result.vertex = HashBytecode(vertex);" in body
    assert "result.pixel = HashBytecode(pixel);" in body
    assert "if (vertex) vertex->Release();" in body
    assert "if (pixel) pixel->Release();" in body
    assert "HashBytecodeCached(" not in source
    assert "vsCache" not in source and "psCache" not in source
    assert "std::array<Seen, 256> seen{};" in source


def main() -> None:
    f11 = F11.read_text(encoding="utf-8")
    shader = SHADER.read_text(encoding="utf-8")
    check_f11(f11)
    check_shader(shader)
    f11_mutations = (
        ("fov[0].left > fov[1].left", "fov[0].left < fov[1].left"),
        ("fov[0].right < fov[1].right", "fov[0].right > fov[1].right"),
        ("commonHeight <= 0.05f", "commonHeight < -1.0f"),
    )
    for old, new in f11_mutations:
        assert old in f11
        try:
            check_f11(f11.replace(old, new, 1))
        except AssertionError:
            continue
        raise AssertionError("F11 source mutation escaped: " + old)
    for old, new in (
        ("result.vertex = HashBytecode(vertex);", "result.vertex = {};"),
        ("result.pixel = HashBytecode(pixel);", "result.pixel = {};"),
    ):
        assert old in shader
        try:
            check_shader(shader.replace(old, new, 1))
        except AssertionError:
            continue
        raise AssertionError("shader identity mutation escaped: " + old)
    print("PASS DX9Ex review105 F11 binocular containment, shader lifetime, 5 negative mutations; HMD UNTESTED")


if __name__ == "__main__":
    main()
