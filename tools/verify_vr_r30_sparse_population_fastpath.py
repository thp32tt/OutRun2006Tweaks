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
    for block in (seed, stereo):
        if not all(t in block for t in (
            "UINT knownUsedCount = UINT_MAX",
            "knownUsedCount <= vertexCount",
            "static_cast<std::size_t>(knownUsedCount)",
            "std::count_if(",
            "static_cast<std::size_t>(selectedCount) * 4u <= vertexCount")):
            return False
    if "usedMask, knownUsedCount))" not in stereo:
        return False
    if not all(t in code for t in (
            "std::vector<std::uint8_t> upUsed;",
            "std::vector<std::uint32_t> upTouched;")):
        return False
    up_contract = (
        "scratch.indexDecode.valid = false;",
        "for (const std::uint32_t previous : scratch.upTouched)",
        "scratch.upUsed[previous] = 0;",
        "scratch.upTouched.clear();",
        "if (scratch.upUsed.size() < vertexCount)",
        "scratch.upUsed.resize(vertexCount, 0);",
        "UINT knownUsedCount = 0;",
        "if (raw >= vertexCount)",
        "if (!scratch.upUsed[raw])",
        "scratch.upTouched.push_back(raw);",
        "scratch.upUsed[raw] = 1;",
        "++knownUsedCount;",
        "&scratch.upUsed, knownUsedCount))",
    )
    if not all(t in up for t in up_contract):
        return False
    if any(up.index(a) >= up.index(b) for a, b in
           zip(up_contract, up_contract[1:])):
        return False
    if up.count("&scratch.upUsed") != 2 or "scratch.used.assign(" in up:
        return False
    vb_contract = (
        "UINT knownUsedCount = cachedDecode ? decoded.knownUsedCount : 0;",
        "scratch.used.assign(vertexCount, 0);",
        "if (!scratch.used[static_cast<std::size_t>(local)])",
        "++knownUsedCount;",
        "scratch.used[static_cast<std::size_t>(local)] = 1;",
        "next.knownUsedCount = knownUsedCount;",
        "next.valid = true;",
        "&scratch.used, knownUsedCount))",
    )
    if not all(t in vb for t in vb_contract):
        return False
    if ("if (!cachedDecode)" not in vb or
            "decoded.revision == scratch.indexCopy.revision" not in vb or
            "scratch.upUsed" in vb or "scratch.upTouched" in vb):
        return False
    return all(t in up + vb for t in (
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
        ("if (!scratch.upUsed[raw])", "if (scratch.upUsed[raw])"),
        ("scratch.upTouched.push_back(raw);", "/* lost UP dirty entry */"),
        ("scratch.upUsed[previous] = 0;", "/* stale UP dirty bit */"),
        ("scratch.upTouched.clear();", "/* old offsets accumulate */"),
        ("scratch.upUsed.resize(vertexCount, 0);", "/* missing grow */"),
        ("if (!scratch.used[static_cast<std::size_t>(local)])",
         "if (scratch.used[static_cast<std::size_t>(local)])"),
        ("&scratch.upUsed, knownUsedCount))", "&scratch.upUsed))"),
        ("&scratch.used, knownUsedCount))", "&scratch.used))"),
        ("knownUsedCount <= vertexCount", "knownUsedCount > vertexCount"),
        ("static_cast<std::size_t>(knownUsedCount)",
         "static_cast<std::size_t>(vertexCount)"),
        ("std::count_if(", "std::count_none("),
        ("static_cast<std::size_t>(selectedCount) * 4u <= vertexCount",
         "static_cast<std::size_t>(selectedCount) * 2u <= vertexCount"),
        ("usedMask, knownUsedCount))", "usedMask))"),
    )
    for old, new in mutations:
        assert old in code
        if old == "UINT knownUsedCount = 0;":
            # The decode-cache structure also contains a field with this
            # initializer. Mutate the UP draw's live counter, not metadata.
            start = code.index("HRESULT R30TryXyzrhwIndexedPrimitiveUP(")
            end = code.index("HRESULT R30TryXyzrhwPrimitiveVB(", start)
            assert old in code[start:end]
            mutant = code[:start] + code[start:end].replace(old, new, 1) + code[end:]
        else:
            mutant = code.replace(old, new, 1)
        assert not valid(mutant), old
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
    # Successive UP draws, shrinking/growing masks and failed index bounds
    # reproduce the persistent scratch rather than a fresh allocation.
    up_mask = bytearray()
    previous_touched = []
    for n, refs in ((131072, (0, 99999, 99999)),
                    (8, (7, 7, 0)), (128, (2, 3, 90)),
                    (4, (0, 7)), (4, (3, 3)),
                    (131072, (99999, 0)), (1, (0,))):
        for i in previous_touched:
            up_mask[i] = 0
        previous_touched.clear()
        up_mask.extend(bytes(max(0, n - len(up_mask))))
        expected = bytearray(n)
        for index in refs:
            if index >= n:
                break
            expected[index] = 1
            if not up_mask[index]:
                previous_touched.append(index)
                up_mask[index] = 1
        assert up_mask[:n] == expected
        assert len(previous_touched) == sum(expected)
    print(f"PASS R30 indexed unique-mask cardinality: {cases} binary "
          f"stereo-copy cases, {len(mutations)} destructive mutations")


if __name__ == "__main__":
    main()
