#!/usr/bin/env python3
"""Sparse ScreenHud XYZRHW two-eye visit contract; no HMD FPS assertion.

The indexed-UP or generation-fenced VB/IB producer supplies unique touched
indices and exactly matching mask bits. The fast route must visit only those
indices, preserve pixel transforms and all other vertex payload bytes, and
fail closed on a corrupted producer. Dense/unindexed retains the full walk.
"""
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
CPP = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
WORKFLOW = ROOT / ".github/workflows/vr-dx9ex-active.yml"


def hud_section(source):
    start = source.index("bool R30TransformXyzrhwStereo(")
    stop = source.index("// This is the high-frequency indexed smoke/sand/decal path:", start)
    return source[start:stop]


def verify_source(source, workflow):
    hud = hud_section(source)
    required = (
        "if (!state.worldEffect)",
        "knownUsedCount > 0u",
        "knownUsedCount == touched->size()",
        "knownUsedCount <= vertexCount / 8u",
        "const bool sparseHudTouched = usedMask && touched &&",
        "sparseHudTouched ? knownUsedCount : vertexCount",
        "for (UINT visit = 0; visit < hudVisitCount; ++visit)",
        "const UINT i = sparseHudTouched ? (*touched)[visit] : visit;",
        "if (i >= vertexCount ||",
        "(sparseHudTouched && !(*usedMask)[i]))",
        "if (usedMask && !(*usedMask)[i])",
        "!std::isfinite(src[0]) || !std::isfinite(src[1])",
        "!std::isfinite(src[2]) || !std::isfinite(src[3])",
        "const float transformedY = hudScaleY * src[1] + hudBiasY;",
        "eyeScaleX[0] * src[0] + eyeBiasX[0];",
        "eyeScaleX[1] * src[0] + eyeBiasX[1];",
        "leftDst[0] = transformedLeftX;",
        "leftDst[1] = transformedY;",
        "rightDst[0] = transformedRightX;",
        "rightDst[1] = transformedY;",
    )
    for token in required:
        assert token in hud, "missing ScreenHud invariant: " + token
    # The sparse route requires bounds and mask checks before any indexed read.
    assert hud.index("const UINT i = sparseHudTouched") < hud.index(
        "if (i >= vertexCount ||") < hud.index(
        "const auto* src = reinterpret_cast<const float*")
    assert hud.count("for (UINT visit = 0; visit < hudVisitCount; ++visit)") == 1
    assert "for (UINT i = 0; i < vertexCount; ++i)" not in hud
    assert "R30SeedTouchedXyzrhwVertices(" in hud
    assert "if (!sparseCopied)" in hud
    assert "std::memcpy(left.data(), source, bytes);" in hud
    assert "std::memcpy(right.data(), source, bytes);" in hud
    assert "if (!R30SeedWorldXyzrhwBuffers(" in source
    assert workflow.count("tools/verify_vr_r30_hud_sparse_visit.py") == 2


def destructive_mutations(source, workflow):
    hud = hud_section(source)
    mutants = (
        ("knownUsedCount == touched->size()", "knownUsedCount != touched->size()"),
        ("knownUsedCount <= vertexCount / 8u", "knownUsedCount <= vertexCount"),
        ("sparseHudTouched ? knownUsedCount : vertexCount", "vertexCount"),
        ("sparseHudTouched ? (*touched)[visit] : visit;", "visit;"),
        ("if (i >= vertexCount ||", "if (false ||"),
        ("(sparseHudTouched && !(*usedMask)[i]))", "false)"),
        ("if (usedMask && !(*usedMask)[i])", "if (false)"),
        ("leftDst[0] = transformedLeftX;", "leftDst[0] = src[0];"),
        ("rightDst[0] = transformedRightX;", "rightDst[0] = src[0];"),
    )
    start = source.index("bool R30TransformXyzrhwStereo(")
    end = source.index("// This is the high-frequency indexed smoke/sand/decal path:", start)
    for n, (old, new) in enumerate(mutants, 1):
        assert hud.count(old) == 1, ("mutation anchor", n)
        changed = source[:start] + hud.replace(old, new, 1) + source[end:]
        try:
            verify_source(changed, workflow)
        except (AssertionError, ValueError):
            continue
        raise AssertionError(f"HUD sparse mutation {n} escaped")


def visit_indices(mask, touched, known_count):
    n = len(mask)
    sparse = (touched is not None and known_count > 0 and
              known_count == len(touched) and known_count <= n // 8)
    if not sparse:
        return [i for i in range(n) if mask[i]], False
    indices = []
    for i in touched:
        if i < 0 or i >= n or not mask[i]:
            return None, True
        indices.append(i)
    return indices, True


def numeric_parity():
    rng = random.Random(713)
    for n in (1, 9, 63, 64, 128, 513, 8192):
        for cardinality in (0, 1, max(1, n // 16), max(1, n // 4), n):
            count = min(n, cardinality)
            touched = rng.sample(range(n), count)
            mask = [False] * n
            for i in touched:
                mask[i] = True
            data = [(rng.uniform(-900, 900), rng.uniform(-400, 400),
                     rng.uniform(0, 1), rng.uniform(0.01, 3),
                     rng.getrandbits(32), rng.getrandbits(32))
                    for _ in range(n)]
            selected, sparse = visit_indices(mask, touched, count)
            assert selected is not None and set(selected) == set(touched)
            assert sparse == (count > 0 and count <= n // 8)
            # Both eye transforms change only X; Y is shared, remaining
            # Z/RHW/color/UV payload must remain bit-for-bit identical.
            for scale, bias in ((0.91, -2.5), (1.08, 7.0)):
                dense = list(data)
                fast = list(data)
                for i in range(n):
                    if mask[i]:
                        x, y, z, rhw, color, uv = dense[i]
                        dense[i] = (scale * x + bias, 1.05 * y + 2.0,
                                    z, rhw, color, uv)
                for i in selected:
                    x, y, z, rhw, color, uv = fast[i]
                    fast[i] = (scale * x + bias, 1.05 * y + 2.0,
                               z, rhw, color, uv)
                assert dense == fast, ("sparse/dense parity", n, count)
            if sparse:
                if count < n:
                    bad = next(i for i in range(n) if not mask[i])
                    assert visit_indices(mask, touched[:-1] + [bad], count)[0] is None
                assert visit_indices(mask, touched[:-1] + [n], count)[0] is None
            # A mismatched list size must select safe dense fallback.
            assert visit_indices(mask, touched[:-1], count)[0] is not None


if __name__ == "__main__":
    src, wf = CPP.read_text(encoding="utf-8"), WORKFLOW.read_text(encoding="utf-8")
    verify_source(src, wf)
    destructive_mutations(src, wf)
    numeric_parity()
    print("R30 ScreenHud sparse touched-index visit: source, mutations and parity PASS (runtime UNTESTED)")
