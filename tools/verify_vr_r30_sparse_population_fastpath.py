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
    # Both the original world-seed path and the new fused projection path
    # must consume the validated touched-count contract. A mutation of the
    # first matching callsite may no longer pass by matching the second one.
    if stereo.count("usedMask, knownUsedCount, touched))") != 2:
        return False
    # Live C++ touched-copy branch must be behind sparse cardinality and
    # preserve the historical contiguous-mask scan as a safe fallback.
    helper = section(code, "bool R30SeedTouchedXyzrhwVertices(",
                     "bool R30SeedWorldXyzrhwBuffers(")
    for token in ("touched->size() != selectedCount",
                  "selectedCount * 4u > vertexCount",
                  "index >= vertexCount || !usedMask[index]",
                  "std::memcpy(left.data() + offset,",
                  "std::memcpy(right->data() + offset,"):
        if token not in helper:
            return False
    if seed.count("R30SeedTouchedXyzrhwVertices(") != 1 or (
            "src, vertexCount, stride, left, right," not in seed or
            "*usedMask, touched, selectedCount" not in seed):
        return False
    if stereo.count("R30SeedTouchedXyzrhwVertices(") != 1 or (
            "srcBytes, vertexCount, stride, left, &right," not in stereo):
        return False
    if "&scratch.upUsed, knownUsedCount, &scratch.upTouched))" not in up:
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
        "if (raw < minVertexIndex || raw >= vertexCount)",
        "if (!scratch.upUsed[raw])",
        "scratch.upTouched.push_back(raw);",
        "scratch.upUsed[raw] = 1;",
        "++knownUsedCount;",
        "&scratch.upUsed, knownUsedCount, &scratch.upTouched))",
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
        "scratch.vbTouched.size() == decoded.knownUsedCount",
        "scratch.indexDecode.valid = false;",
        "for (const std::uint32_t previous : scratch.vbTouched)",
        "if (previous < scratch.used.size())",
        "scratch.used[previous] = 0;",
        "scratch.vbTouched.clear();",
        "scratch.used.resize(vertexCount, 0);",
        "scratch.vbTouched.push_back(",
        "if (!scratch.used[static_cast<std::size_t>(local)])",
        "++knownUsedCount;",
        "scratch.used[static_cast<std::size_t>(local)] = 1;",
        "next.knownUsedCount = knownUsedCount;",
        "next.valid = true;",
        "&scratch.used, knownUsedCount, &scratch.vbTouched))",
    )
    if not all(t in vb for t in vb_contract):
        return False
    if ("if (!cachedDecode)" not in vb or
            "decoded.revision == scratch.indexCopy.revision" not in vb or
            "scratch.upUsed" in vb or "scratch.upTouched" in vb):
        return False
    # The new sparse reset must run after invalidating the IB cache but
    # before resizing and before any newly marked index. Full-span assign
    # would retain parity but undo the actual performance correction.
    mask_order = (
        "scratch.indexDecode.valid = false;",
        "for (const std::uint32_t previous : scratch.vbTouched)",
        "if (previous < scratch.used.size())",
        "scratch.used[previous] = 0;",
        "scratch.vbTouched.clear();",
        "scratch.used.resize(vertexCount, 0);",
        "scratch.vbTouched.push_back(",
        "scratch.used[static_cast<std::size_t>(local)] = 1;",
    )
    if "scratch.used.assign(vertexCount, 0);" in vb or (
            any(vb.index(a) >= vb.index(b) for a, b in
                zip(mask_order, mask_order[1:]))):
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



def touched_copy(data, mask, touched, stride, left, right):
    n = len(mask)
    count = sum(mask)
    if (n < 64 or count * 4 > n or len(touched) != count or
            count * 4 > n or any(i >= n or not mask[i] for i in touched)):
        return old_copy(data, mask, stride, left, right), False
    for i in touched:
        a, b = i * stride, (i + 1) * stride
        left[a:b] = right[a:b] = data[a:b]
    return True, True


def main():
    code = CPP.read_text(encoding="utf-8")
    workflow = WF.read_text(encoding="utf-8")
    assert valid(code), "indexed unique-count / sparse seed routing lost"
    assert workflow.count("tools/verify_vr_r30_sparse_population_fastpath.py") == 2
    mutations = (
        ("UINT knownUsedCount = 0;", "UINT knownUsedCount = vertexCount;"),
        ("++knownUsedCount;", "--knownUsedCount;"),
        ("if (!scratch.upUsed[raw])", "if (scratch.upUsed[raw])"),
        ("if (raw < minVertexIndex || raw >= vertexCount)",
         "if (raw >= vertexCount)"),
        ("scratch.upTouched.push_back(raw);", "/* lost UP dirty entry */"),
        ("scratch.upUsed[previous] = 0;", "/* stale UP dirty bit */"),
        ("scratch.upTouched.clear();", "/* old offsets accumulate */"),
        ("scratch.upUsed.resize(vertexCount, 0);", "/* missing grow */"),
        ("if (!scratch.used[static_cast<std::size_t>(local)])",
         "if (scratch.used[static_cast<std::size_t>(local)])"),
        ("&scratch.upUsed, knownUsedCount, &scratch.upTouched))", "&scratch.upUsed))"),
        ("scratch.vbTouched.size() == decoded.knownUsedCount",
         "scratch.vbTouched.size() != decoded.knownUsedCount"),
        ("for (const std::uint32_t previous : scratch.vbTouched)",
         "for (const std::uint32_t previous : scratch.upTouched)"),
        ("if (previous < scratch.used.size())",
         "if (previous > scratch.used.size())"),
        ("scratch.used[previous] = 0;", "scratch.used[previous] = 1;"),
        ("scratch.used.resize(vertexCount, 0);",
         "scratch.used.assign(vertexCount, 0);"),
        ("scratch.vbTouched.clear();", "scratch.vbTouched.reserve(0);"),
        ("scratch.vbTouched.push_back(", "scratch.vbTouched.pop_back("),
        ("&scratch.used, knownUsedCount, &scratch.vbTouched))",
         "&scratch.used, knownUsedCount, nullptr))"),
        ("knownUsedCount <= vertexCount", "knownUsedCount > vertexCount"),
        ("static_cast<std::size_t>(knownUsedCount)",
         "static_cast<std::size_t>(vertexCount)"),
        ("std::count_if(", "std::count_none("),
        ("static_cast<std::size_t>(selectedCount) * 4u <= vertexCount",
         "static_cast<std::size_t>(selectedCount) * 2u <= vertexCount"),
        ("usedMask, knownUsedCount, touched))", "usedMask))"),
        ("selectedCount * 4u > vertexCount", "selectedCount * 80u > vertexCount"),
        ("index >= vertexCount || !usedMask[index]", "index >= vertexCount"),
        ("touched->size() != selectedCount", "touched->size() < selectedCount"),
        ("*usedMask, touched, selectedCount", "*usedMask, nullptr, selectedCount"),
        ("&scratch.upUsed, knownUsedCount, &scratch.upTouched))",
         "&scratch.upUsed, knownUsedCount, nullptr))"),
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
        elif old == "knownUsedCount <= vertexCount":
            # The affine projection now also has a touched-count density
            # guard before the seed helper. Damage the seed's authoritative
            # population check, not an unrelated earlier affine guard.
            start = code.index("bool R30SeedWorldXyzrhwBuffers(")
            end = code.index("bool R30TransformXyzrhwVertices(", start)
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
                    touched = list(set(indices))
                    rng.shuffle(touched)
                    touch_l, touch_r = seed[:], seed[:]
                    touch_sparse, touched_selected = touched_copy(
                        data, old_mask, touched, stride, touch_l, touch_r)
                    assert touch_sparse == old_sparse
                    assert touch_l == old_l and touch_r == old_r
                    assert touched_selected == (
                        n >= 64 and known * 4 <= n)
                    cases += 1

    # Intermediate sparse spans (12.5-25%): use the validated touched
    # list for both eyes rather than scanning every source vertex.
    for n, used in ((80, 10), (80, 11), (80, 16), (80, 20), (80, 21)):
        stride = 32
        data = bytearray(rng.randbytes(n * stride))
        initial = bytearray(rng.randbytes(n * stride))
        mask = bytearray([1] * used + [0] * (n - used))
        touched = list(range(used))
        rng.shuffle(touched)
        old_left, old_right = initial[:], initial[:]
        new_left, new_right = initial[:], initial[:]
        expected_sparse = old_copy(data, mask, stride, old_left, old_right)
        sparse, used_touched = touched_copy(
            data, mask, touched, stride, new_left, new_right)
        assert sparse == expected_sparse
        assert used_touched == (used * 4 <= n)
        assert (new_left, new_right) == (old_left, old_right)
        if used:
            corrupt = touched[:]
            corrupt[0] = n
            fallback_left, fallback_right = initial[:], initial[:]
            sparse, used_touched = touched_copy(
                data, mask, corrupt, stride, fallback_left, fallback_right)
            assert sparse == expected_sparse and not used_touched
            assert (fallback_left, fallback_right) == (old_left, old_right)

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
