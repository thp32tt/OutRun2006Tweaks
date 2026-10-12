#!/usr/bin/env python3
"""Indexed XYZRHW unique-mask population: source and copy-parity contract.

The 16/32-bit index pass already touches each reference, so count first hits
during the pass instead of recounting a long sparse mask per stereo draw.
These source/model checks do not assert measured Quest3 FPS.
"""
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
CPP = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
WF = ROOT / ".github/workflows/vr-dx9ex-active.yml"


def section(code, begin, end):
    return code.split(begin, 1)[1].split(end, 1)[0]


def valid(code):
    try:
        seed = section(code, "bool R30SeedWorldXyzrhwBuffers(",
                       "bool R30TransformXyzrhwVertices(")
        stereo = section(code, "bool R30TransformXyzrhwStereo(",
                         "template <typename LeftDraw")
        up = section(code, "HRESULT R30TryXyzrhwIndexedPrimitiveUP(",
                     "HRESULT R30TryXyzrhwPrimitiveVB(")
        vb = section(code, "HRESULT R30TryXyzrhwIndexedPrimitiveVB(",
                     "// Called on every eligible FlatPerspectiveEffect draw.")
    except (ValueError, IndexError):
        return False
    for segment in (seed, stereo):
        if not all(x in segment for x in (
                "UINT knownUsedCount = UINT_MAX",
                "knownUsedCount <= vertexCount",
                "static_cast<std::size_t>(knownUsedCount)",
                "std::count_if(", "selectedCount * 4u <= vertexCount")):
            return False
        if segment.index("knownUsedCount <= vertexCount") >= segment.index(
                "std::count_if("):
            return False
    if "usedMask, knownUsedCount))" not in stereo:
        return False
    for name, segment, marker in (
        ("UP", up, "scratch.used[raw] = 1;"),
        ("VB", vb, "scratch.used[static_cast<std::size_t>(local)] = 1;"),
    ):
        if not all(x in segment for x in (
                "UINT knownUsedCount = 0;", "++knownUsedCount;", marker,
                "&scratch.used, knownUsedCount))",
                "scratch.used.assign(vertexCount, 0);")):
            return False
        if not (segment.index("scratch.used.assign(vertexCount, 0);")
                < segment.index("UINT knownUsedCount = 0;")
                < segment.index("++knownUsedCount;")
                < segment.index(marker)
                < segment.index("&scratch.used, knownUsedCount))")):
            return False
        guard = ("if (!scratch.used[raw])" if name == "UP"
                 else "if (!scratch.used[static_cast<std::size_t>(local)])")
        if guard not in segment or segment.index(guard) > segment.index(
                "++knownUsedCount;"):
            return False
    return all(x in up + vb for x in (
        "return E_NOTIMPL;", "R30ConfigureXyzrhwWorldEffect(",
        "R30TransformXyzrhwStereo("))


def old_copy(data, mask, stride, left, right):
    n = len(mask)
    sparse = n >= 64 and sum(mask) * 4 <= n
    if sparse:
        for i, selected in enumerate(mask):
            if selected:
                a, b = i * stride, (i + 1) * stride
                left[a:b] = right[a:b] = data[a:b]
    else:
        left[:] = right[:] = data
    return sparse


def fast_copy(data, indices, n, stride, left, right):
    mask = bytearray(n)
    count = 0
    for idx in indices:
        if idx >= n:
            return None
        if not mask[idx]:
            count += 1
            mask[idx] = 1
    sparse = n >= 64 and count * 4 <= n
    if sparse:
        for i, selected in enumerate(mask):
            if selected:
                a, b = i * stride, (i + 1) * stride
                left[a:b] = right[a:b] = data[a:b]
    else:
        left[:] = right[:] = data
    return mask, count, sparse


def main():
    code = CPP.read_text(encoding="utf-8")
    workflow = WF.read_text(encoding="utf-8")
    assert valid(code), "indexed unique-count / sparse seed routing lost"
    assert workflow.count("tools/verify_vr_r30_sparse_population_fastpath.py") == 2
    mutations = (
        ("UINT knownUsedCount = 0;", "UINT knownUsedCount = vertexCount;"),
        ("++knownUsedCount;", "--knownUsedCount;"),
        ("if (!scratch.used[raw])", "if (scratch.used[raw])"),
        ("if (!scratch.used[static_cast<std::size_t>(local)])",
         "if (scratch.used[static_cast<std::size_t>(local)])"),
        ("&scratch.used, knownUsedCount))", "&scratch.used))"),
        ("knownUsedCount <= vertexCount", "knownUsedCount > vertexCount"),
        ("static_cast<std::size_t>(knownUsedCount)",
         "static_cast<std::size_t>(vertexCount)"),
        ("std::count_if(", "std::count_none("),
        ("selectedCount * 4u <= vertexCount",
         "selectedCount * 2u <= vertexCount"),
        ("usedMask, knownUsedCount))", "usedMask))"),
    )
    for old, new in mutations:
        assert old in code
        assert not valid(code.replace(old, new, 1)), old
    rng = random.Random(694)
    cases = 0
    for stride in (16, 20, 32, 48):
        for n in (1, 2, 63, 64, 65, 256, 1024):
            for density in (0.0, 0.02, 0.25, 0.5, 1.0):
                for _ in range(10):
                    count = rng.randint(1, n * 2)
                    width = max(1, int(n * density))
                    indices = [rng.randrange(width) for __ in range(count)]
                    data = bytearray(rng.randbytes(n * stride))
                    seed = bytearray(rng.randbytes(n * stride))
                    old_l, old_r = seed[:], seed[:]
                    new_l, new_r = seed[:], seed[:]
                    old_mask = bytearray(n)
                    for idx in indices:
                        old_mask[idx] = 1
                    old_sparse = old_copy(data, old_mask, stride, old_l, old_r)
                    result = fast_copy(data, indices, n, stride, new_l, new_r)
                    assert result is not None
                    fast_mask, known, fast_sparse = result
                    assert fast_mask == old_mask
                    assert known == sum(old_mask)
                    assert old_sparse == fast_sparse
                    assert old_l == new_l and old_r == new_r
                    cases += 1
    assert fast_copy(b"\0" * 64, [4], 4, 16,
                     bytearray(64), bytearray(64)) is None
    print(f"PASS R30 indexed unique-mask cardinality: {cases} binary "
          f"stereo-copy cases, {len(mutations)} destructive mutations")


if __name__ == "__main__":
    main()
