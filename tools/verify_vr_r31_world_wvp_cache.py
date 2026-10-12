#!/usr/bin/env python3
"""DX9Ex R31 exact-WVP repeated world-draw transform cache regression gate."""
from pathlib import Path
import random
import struct

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d9/stereo_renderer_r31.cpp"
WORKFLOW = ROOT / ".github/workflows/vr-dx9ex-active.yml"


def body(code: str, signature: str) -> str:
    start = code.index("{", code.index(signature))
    level = 0
    for pos in range(start, len(code)):
        if code[pos] == "{":
            level += 1
        elif code[pos] == "}":
            level -= 1
            if level == 0:
                return code[start:pos + 1]
    raise AssertionError("unclosed " + signature)


def violations(source: str) -> list[str]:
    errors = []
    cache = body(source, "struct R31WorldWvpCache")
    build = body(source, "bool R31BuildFastWorldConstants(")
    prepare = body(source, "bool R31PrepareEyeTailCache(")
    reset = body(source, "inline void R31ResetFastPathState()")
    blocked = body(source, "void R31BlockCurrentVerifiedGeneration()")
    stateblock = body(source, "void R31MarkStateBlockCachesDirty()")
    def require(ok: bool, label: str) -> None:
        if not ok:
            errors.append(label)
    # Primary fields must exist independently of same-named fields in
    # Recent. Mutating the primary must not pass through the alternate.
    primary = cache.split("struct Recent", 1)[0]
    for marker in ("bool valid = false;", "float originalWvp[16]{};",
                   "float eyeConstants[2][16]{};"):
        require(marker in primary, "primary cache storage " + marker)
    for marker in (
        "GetLastVerifiedWvp(",
        "poseSequence != stereo.poseSequence",
        "R30SupportCurrentShaderEpoch(",
        "R30SupportValidateVerifiedWvp(",
        "R31PrepareEyeTailCache(stereo, projection)",
        "const float* originalWvp = liveValidated ? live : verified;",
        "if (R31WorldCache.valid &&",
        "std::memcmp(R31WorldCache.originalWvp, originalWvp,",
        "sizeof(draw.originalConstants)) == 0)",
        "std::memcpy(draw.eyeConstants, R31WorldCache.eyeConstants,",
        "sizeof(draw.eyeConstants));",
        "const D3DMATRIX eyeWvp = R30SupportMultiplyMatrix(",
        "if (!R30SupportMatrixFinite(eyeWvp))",
        "std::memcpy(R31WorldCache.originalWvp, originalWvp,",
        "std::memcpy(R31WorldCache.eyeConstants, draw.eyeConstants,",
        "R31WorldCache.valid = true;",
    ):
        require(marker in build, "build " + marker)
    # Secondary reuse is legal only after the existing live WVP, shader,
    # eye-tail, and StateBlock gates. A primary invalidation fences every
    # historical entry, and two-eye finite validation precedes publication.
    for marker in (
        "struct Recent",
        "Recent recent[3]{};",
        "unsigned nextRecent = 0;",
        "unsigned hotRecent = 0;",
    ):
        require(marker in cache, "bounded alternate cache " + marker)
    for marker in (
        "if (R31WorldCache.valid)\n            {",
        "for (const auto& previous : R31WorldCache.recent)",
        "const auto& hot = R31WorldCache.recent[R31WorldCache.hotRecent];",
        "if (hot.valid &&",
        "std::memcmp(hot.originalWvp, originalWvp,",
        "std::memcpy(draw.eyeConstants, hot.eyeConstants,",
        "if (&previous == &hot)",
        "R31WorldCache.hotRecent = static_cast<unsigned>(",
        "R31WorldCache.hotRecent = 0;",
        "if (previous.valid &&",
        "std::memcmp(previous.originalWvp, originalWvp,",
        "std::memcpy(draw.eyeConstants, previous.eyeConstants,",
        "if (R31WorldCache.valid)\n            {\n                auto& previous = R31WorldCache.recent[R31WorldCache.nextRecent];",
        "std::memcpy(previous.originalWvp, R31WorldCache.originalWvp,",
        "std::memcpy(previous.eyeConstants, R31WorldCache.eyeConstants,",
        "previous.valid = true;",
        "R31WorldCache.nextRecent = (R31WorldCache.nextRecent + 1) % 3;",
        "for (auto& previous : R31WorldCache.recent)",
        "previous.valid = false;",
        "R31WorldCache.nextRecent = 0;",
    ):
        require(marker in build, "alternate producer " + marker)
    try:
        require(build.index("R31PrepareEyeTailCache(stereo, projection)") <
                build.index("for (const auto& previous : R31WorldCache.recent)"),
                "eye-tail validation precedes alternate hit")
        require(build.index("R30SupportValidateVerifiedWvp(") <
                build.index("for (const auto& previous : R31WorldCache.recent)"),
                "live WVP validation precedes alternate hit")
        require(build.index("if (!R30SupportMatrixFinite(eyeWvp))") <
                build.index("auto& previous = R31WorldCache.recent[R31WorldCache.nextRecent]"),
                "two-eye finite validation precedes alternate publish")
    except ValueError:
        errors.append("alternate guard ordering missing")
    # Destructive mutations deliberately delete individual anchors: record
    # missing-order violations instead of raising ValueError mid-mutation.
    try:
        require(build.index("R30SupportValidateVerifiedWvp(") <
                build.index("if (R31WorldCache.valid &&"), "validation precedes hit")
        require(build.index("R31PrepareEyeTailCache(stereo, projection)") <
                build.index("if (R31WorldCache.valid &&"), "tail validation precedes hit")
        require(build.index("if (!R30SupportMatrixFinite(eyeWvp))") <
                build.index("R31WorldCache.valid = true;"), "two-eye finite before publish")
    except ValueError:
        errors.append("mandatory validation/publish ordering anchor absent")
    require(build.count("draw.poseSequence = stereo.poseSequence;") == 4,
            "all three fast-return paths use the current pose")
    require("R31EyeCache = next;" in prepare and
            "R31WorldCache.valid = false;" in prepare and
            prepare.index("R31EyeCache = next;") <
            prepare.index("R31WorldCache.valid = false;"), "tail miss invalidate")
    require("R31WorldCache = {};" in reset, "Reset/ResetEx invalidate")
    require("R31WorldCache.valid = false;" in blocked, "blocked generation invalidate")
    require("R31WorldCache.valid = false;" in stateblock, "StateBlock invalidate")
    return errors


def f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def matmul(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(f32(sum(f32(a[r * 4 + k] * b[k * 4 + c])
                         for k in range(4))) for r in range(4) for c in range(4))


def numeric_test() -> None:
    randomizer = random.Random(646)
    cached_key = cached_value = None
    hits = misses = 0
    for index in range(1300):
        if index % 5 == 0:
            wvp = tuple(f32(randomizer.uniform(-3, 3)) for _ in range(16))
        if index % 13 == 0:
            tails = tuple(tuple(f32(randomizer.uniform(-3, 3))
                                for _ in range(16)) for _ in range(2))
            cached_key = None
        key = struct.pack("<16f", *wvp)
        products = tuple(matmul(wvp, tail) for tail in tails)
        if cached_key == key:
            hits += 1
            assert cached_value == products
        else:
            misses += 1
            cached_key, cached_value = key, products
    assert hits > 500 and misses > 150
    print(f"PASS exact numeric parity: hits={hits} misses={misses}")



def numeric_interleaved_test() -> None:
    """Four interleaved transforms reuse exact eye products; resets reject old tails."""
    rng = random.Random(653)
    keys = [tuple(f32(rng.uniform(-3, 3)) for _ in range(16))
            for _ in range(4)]
    tails = tuple(tuple(f32(rng.uniform(-2, 2)) for _ in range(16))
                  for _ in range(2))
    primary = None
    recent = [None, None, None]
    slot = 0
    hits = misses = invalidations = 0
    for index in range(2400):
        if index % 137 == 0:
            tails = tuple(tuple(f32(rng.uniform(-2, 2)) for _ in range(16))
                          for _ in range(2))
            primary = None
            invalidations += 1
        wvp = keys[(index * 7 + index // 19) % len(keys)]
        key = struct.pack("<16f", *wvp)
        expected = tuple(matmul(wvp, tail) for tail in tails)
        entry = None
        if primary is not None and primary[0] == key:
            entry = primary
        elif primary is not None:
            entry = next((candidate for candidate in recent
                          if candidate is not None and candidate[0] == key), None)
        if entry is not None:
            assert entry[1] == expected, "stale or non-identical stereo product"
            hits += 1
        else:
            misses += 1
            if primary is None:
                recent = [None, None, None]
                slot = 0
            else:
                recent[slot] = primary
                slot = (slot + 1) % len(recent)
            primary = (key, expected)
    assert hits > 1700 and misses > 50 and invalidations > 10
    print(f"PASS four-way interleaved world WVP: hits={hits}, misses={misses}, tail-invalidations={invalidations}")



def numeric_hot_recent_hint_test() -> None:
    """An interleaved repeated alternate must use exact keys with less search."""
    keys = [struct.pack("<16f", *(float(i * 20 + j) for j in range(16)))
            for i in range(4)]
    primary, recent, hot = keys[0], keys[1:], 0
    baseline_checks = hinted_checks = 0
    for n in range(1800):
        key = keys[3] if n % 12 not in (0, 1) else keys[1 + (n % 2)]
        # Historical primary + sequential three-entry lookup.
        baseline_checks += 1
        baseline_hit = key == primary
        if not baseline_hit:
            for candidate in recent:
                baseline_checks += 1
                if candidate == key:
                    baseline_hit = True
                    break
        hinted_checks += 1
        hinted_hit = key == primary
        if not hinted_hit:
            hinted_checks += 1
            hinted_hit = recent[hot] == key
            if not hinted_hit:
                for i, candidate in enumerate(recent):
                    if i == hot:
                        continue
                    hinted_checks += 1
                    if candidate == key:
                        hot = i
                        hinted_hit = True
                        break
        assert baseline_hit and hinted_hit
    assert hinted_checks * 5 < baseline_checks * 4, (
        hinted_checks, baseline_checks)
    print(f"PASS R31 recent-hot exact WVP hint: {baseline_checks} -> "
          f"{hinted_checks} key comparisons on interleaved world draws")


def zero_copy_bridge_violations(api: str, r32: str, r33: str) -> list[str]:
    """R31 verified eye matrices reach R33 unchanged; the pose is borrowed."""
    errors = []
    if '#include "../core/r31_support_api.hpp"' not in api:
        errors.append("R32 must include the R31 payload ABI")
    if "using R32ReviewFastWorldConstants = R31SupportFastWorldConstants;" not in api:
        errors.append("R32 must reuse R31 world constants storage")
    if "LatchedStereoFrame stereoFrame" in api:
        errors.append("per-draw stereo pose duplication restored")
    bridge = body(r32, "bool R32ReviewBuildFastWorldConstants(")
    if "return R31SupportBuildFastWorldConstants(d, s, out);" not in bridge:
        errors.append("R32 is no longer direct zero-copy forwarding")
    if "std::memcpy(" in bridge or "R31SupportFastWorldConstants draw" in bridge:
        errors.append("second intermediate WVP array was reintroduced")
    world = body(r33, "R32ReviewOwnedResult R33TryFastWorld(")
    # R33 reads the BeginScene-latched stereo frame by immutable view.
    # Keep the forwarding bridge zero-copy and reject lost pose/null fences.
    if "const auto* stereo = OutRunVRRenderer::GetLatchedStereoFrameView();" not in world:
        errors.append("R33 world route no longer borrows the latched pose")
    if "if (!stereo)" not in world or "framePoseSequence != stereo->poseSequence" not in world:
        errors.append("R33 world route lost its borrowed-pose validity fence")
    if "R32ReviewBuildFastWorldConstants(device, *stereo, draw)" not in world:
        errors.append("world constants no longer use verified producer")
    if "draw.poseSequence, *stereo);" not in world or "draw.stereoFrame" in world:
        errors.append("R33 no longer uses its existing latched frame")
    return errors


def zero_copy_bridge_test() -> None:
    api = (ROOT / "src/vr/core/r32_review_api.hpp").read_text(encoding="utf-8")
    r32 = (ROOT / "src/vr/d3d9/stereo_renderer_r32.cpp").read_text(encoding="utf-8")
    r33 = (ROOT / "src/vr/d3d9/stereo_renderer_r33.cpp").read_text(encoding="utf-8")
    assert not zero_copy_bridge_violations(api, r32, r33)
    mutation_cases = (
        (0, '#include "../core/r31_support_api.hpp"'),
        (0, "using R32ReviewFastWorldConstants = R31SupportFastWorldConstants;"),
        (1, "return R31SupportBuildFastWorldConstants(d, s, out);"),
        (2, "const auto* stereo = OutRunVRRenderer::GetLatchedStereoFrameView();"),
        (2, "if (!stereo)"),
        (2, "framePoseSequence != stereo->poseSequence"),
        (2, "R32ReviewBuildFastWorldConstants(device, *stereo, draw)"),
        (2, "draw.poseSequence, *stereo);"),
    )
    for index, marker in mutation_cases:
        sources = [api, r32, r33]
        if index == 2:
            # Both world and HUD routes borrow a pose. Mutate ONLY the
            # world function; identical HUD anchors are valid and protected
            # by their own regression gate.
            world = body(sources[2], "R32ReviewOwnedResult R33TryFastWorld(")
            assert world.count(marker) == 1, marker
            sources[2] = sources[2].replace(
                world, world.replace(marker, "BROKEN", 1), 1)
        else:
            assert sources[index].count(marker) == 1, marker
            sources[index] = sources[index].replace(marker, "BROKEN", 1)
        assert zero_copy_bridge_violations(*sources), marker
    print("PASS zero-copy R31/R32/R33 borrowed pose; eight destructive mutations")

def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert workflow.count("tools/verify_vr_r31_world_wvp_cache.py") == 2
    assert not violations(source), violations(source)
    markers = (
        "float originalWvp[16]{};",
        "float eyeConstants[2][16]{};",
        "if (R31WorldCache.valid &&",
        "std::memcmp(R31WorldCache.originalWvp, originalWvp,",
        "std::memcpy(draw.eyeConstants, R31WorldCache.eyeConstants,",
        "std::memcpy(R31WorldCache.originalWvp, originalWvp,",
        "std::memcpy(R31WorldCache.eyeConstants, draw.eyeConstants,",
        "R31WorldCache.valid = true;",
        "R30SupportValidateVerifiedWvp(",
        "R31PrepareEyeTailCache(stereo, projection)",
    )
    for marker in markers:
        assert marker in source
        assert violations(source.replace(marker, "BROKEN", 1)), marker
    for signature, marker in (
        ("bool R31PrepareEyeTailCache(", "R31WorldCache.valid = false;"),
        ("inline void R31ResetFastPathState()", "R31WorldCache = {};"),
        ("void R31BlockCurrentVerifiedGeneration()", "R31WorldCache.valid = false;"),
        ("void R31MarkStateBlockCachesDirty()", "R31WorldCache.valid = false;"),
    ):
        section = body(source, signature)
        assert marker in section
        assert violations(source.replace(section, section.replace(marker, "BROKEN", 1), 1))
    for marker in (
        "Recent recent[3]{};",
        "unsigned hotRecent = 0;",
        "const auto& hot = R31WorldCache.recent[R31WorldCache.hotRecent];",
        "if (hot.valid &&",
        "std::memcmp(hot.originalWvp, originalWvp,",
        "std::memcpy(draw.eyeConstants, hot.eyeConstants,",
        "if (&previous == &hot)",
        "R31WorldCache.hotRecent = static_cast<unsigned>(",
        "R31WorldCache.hotRecent = 0;",
        "if (previous.valid &&",
        "std::memcmp(previous.originalWvp, originalWvp,",
        "std::memcpy(draw.eyeConstants, previous.eyeConstants,",
        "std::memcpy(previous.originalWvp, R31WorldCache.originalWvp,",
        "std::memcpy(previous.eyeConstants, R31WorldCache.eyeConstants,",
        "R31WorldCache.nextRecent = (R31WorldCache.nextRecent + 1) % 3;",
        "previous.valid = false;",
        "R31WorldCache.nextRecent = 0;",
    ):
        assert source.count(marker) == 1, marker
        assert violations(source.replace(marker, "BROKEN", 1)), marker
    numeric_test()
    numeric_interleaved_test()
    numeric_hot_recent_hint_test()
    zero_copy_bridge_test()
    print(f"PASS R31 WVP hotpath: {len(markers) + 13} negative mutations")


if __name__ == "__main__":
    main()
