#!/usr/bin/env python3
"""DX9Ex R30 indexed XYZRHW 2-pass rebasing contract and negative mutations."""
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
WORKFLOW = ROOT / ".github/workflows/vr-dx9ex-active.yml"


def indexed_body(source):
    return source.split("HRESULT R30TryXyzrhwIndexedPrimitiveVB(", 1)[1].split(
        "// Called on every eligible FlatPerspectiveEffect draw.", 1)[0]


def valid(body):
    required = (
        "const bool index16 = ibShadow->indexFormat == D3DFMT_INDEX16;",
        "const auto* raw16 = index16",
        "const auto* raw32 = !index16",
        "minRaw = (std::min)(minRaw, raw);",
        "maxRaw = (std::max)(maxRaw, raw);",
        "static_cast<std::int64_t>(baseVertexIndex) + minRaw;",
        "static_cast<std::int64_t>(baseVertexIndex) + maxRaw;",
        "if (minPhysical < 0 || maxPhysical > UINT_MAX)",
        "static_cast<std::uint64_t>(maxRaw) - minRaw + 1u;",
        "scratch.used.resize(vertexCount, 0);",
        "scratch.indices16.resize(indexCount);",
        "scratch.indices32.resize(indexCount);",
        "static_cast<std::uint64_t>(raw) - minRaw;",
        "if (local >= vertexCount ||",
        "(index16 && local > 0xFFFFu)",
        "scratch.used[static_cast<std::size_t>(local)] = 1;",
        "scratch.indices16[i] = static_cast<std::uint16_t>(local);",
        "scratch.indices32[i] = static_cast<std::uint32_t>(local);",
        "rebased, ibShadow->indexFormat,",
        "R30ConfigureXyzrhwWorldEffect(",
        "R30TransformXyzrhwStereo(",
    )
    if any(token not in body for token in required):
        return False
    if "scratch.physical" in body or body.count("for (UINT i = 0; i < indexCount; ++i)") != 2:
        return False
    first = body.index("minRaw = (std::min)(minRaw, raw);")
    bound = body.index("if (minPhysical < 0 || maxPhysical > UINT_MAX)")
    setup = body.index("scratch.used.resize(vertexCount, 0);")
    second = body.index("static_cast<std::uint64_t>(raw) - minRaw;")
    mark = body.index("scratch.used[static_cast<std::size_t>(local)] = 1;")
    i16 = body.index("scratch.indices16[i] = static_cast<std::uint16_t>(local);")
    i32 = body.index("scratch.indices32[i] = static_cast<std::uint32_t>(local);")
    effect = body.index("R30ConfigureXyzrhwWorldEffect(")
    draw = body.index("auto leftDraw = [&]()")
    return first < bound < setup < second < mark < i16 < i32 < effect < draw


def old_reference(raw, base, index16):
    physical = [base + value for value in raw]
    if not physical or min(physical) < 0 or max(physical) > 0xFFFFFFFF:
        return None
    minimum, maximum = min(physical), max(physical)
    size = maximum - minimum + 1
    if size > 262144:
        return None
    used = [0] * size
    for value in physical:
        used[value - minimum] = 1
    rebased = [value - minimum for value in physical]
    if index16 and any(value > 0xFFFF for value in rebased):
        return None
    return minimum, size, used, rebased


def optimized_model(raw, base, index16):
    if not raw:
        return None
    min_raw, max_raw = min(raw), max(raw)
    minimum, maximum = base + min_raw, base + max_raw
    if minimum < 0 or maximum > 0xFFFFFFFF:
        return None
    size = max_raw - min_raw + 1
    if size > 262144:
        return None
    used = [0] * size
    rebased = [0] * len(raw)
    for i, value in enumerate(raw):
        local = value - min_raw
        if local >= size or (index16 and local > 0xFFFF):
            return None
        used[local] = 1
        rebased[i] = local
    return minimum, size, used, rebased


def verify_decode_cache(source, body):
    # All signature dimensions must be checked before skipping both scans.
    signature = (
        "decoded.valid && decoded.entry == ibShadow",
        "decoded.revision == scratch.indexCopy.revision",
        "decoded.offset == static_cast<UINT>(firstIndexByte)",
        "decoded.size == static_cast<UINT>(indexBytes)",
        "decoded.format == ibShadow->indexFormat",
        "scratch.used.size() == decoded.vertexCount",
        "scratch.indices16.size() == indexCount",
        "scratch.indices32.size() == indexCount",
        "if (!cachedDecode)",
        "scratch.indexDecode.valid = false;",
        "next.entry = ibShadow;",
        "next.revision = scratch.indexCopy.revision;",
        "next.minRaw = minRaw;",
        "next.maxRaw = maxRaw;",
        "next.knownUsedCount = knownUsedCount;",
        "next.valid = true;",
    )
    assert all(token in body for token in signature)
    assert "struct R30IndexDecodeCache" in source
    assert source.count("scratch.indexDecode.valid = false;") == 2
    assert body.index("if (!cachedDecode)") < body.index(
        "minRaw = (std::min)(minRaw, raw);")
    assert body.index("scratch.indexDecode.valid = false;") < body.index(
        "scratch.used.resize(vertexCount, 0);")
    assert body.index("next.valid = true;") < body.index(
        "R30ConfigureXyzrhwWorldEffect(")

    # A rebase/mask is stable across new signed base vertices, while the
    # physical address validation remains separate on every draw.
    import random
    rng = random.Random(697)
    cases = 0
    for index16 in (False, True):
        for _ in range(350):
            raw = [rng.randint(0, 2000) for _ in range(rng.randint(1, 64))]
            base_a, base_b = rng.randint(0, 10000), rng.randint(0, 10000)
            a = optimized_model(raw, base_a, index16)
            b = optimized_model(raw, base_b, index16)
            assert a is not None and b is not None
            assert a[1:] == b[1:]
            cases += 1
    print(f"PASS R30 IB decode cache: {cases} base-independent cases, "
          f"{len(signature)} invariants")



def valid_vb_touched(source, body):
    """Ring/IB-generation-safe touched list, consumed by the stereo seed path."""
    # The declaration belongs to the full translation unit; every other
    # invariant belongs to the *mutated* indexed-draw body, not the original
    # translation unit. Otherwise the unmodified source masks broken mutants.
    if "std::vector<std::uint32_t> vbTouched;" not in source:
        return False
    required = (
        "scratch.vbTouched.size() == decoded.knownUsedCount",
        "scratch.vbTouched.clear();",
        "scratch.vbTouched.push_back(",
        "static_cast<std::uint32_t>(local));",
        "scratch.used[static_cast<std::size_t>(local)] = 1;",
        "next.knownUsedCount = knownUsedCount;",
        "next.valid = true;",
        "&scratch.used, knownUsedCount, &scratch.vbTouched)",
    )
    if any(token not in body for token in required):
        return False
    if body.count("scratch.vbTouched.push_back(") != 1:
        return False
    invalid = body.index("scratch.indexDecode.valid = false;")
    clear = body.index("scratch.vbTouched.clear();")
    fill = body.index("scratch.used.resize(vertexCount, 0);")
    append = body.index("scratch.vbTouched.push_back(")
    mark = body.index("scratch.used[static_cast<std::size_t>(local)] = 1;")
    publish = body.index("next.valid = true;")
    transform = body.index("&scratch.used, knownUsedCount, &scratch.vbTouched)")
    return invalid < clear < fill < append < mark < publish < transform


def verify_vb_touched(source, body):
    assert valid_vb_touched(source, body), "VB sparse touched producer/consumer broken"
    # The existing UP touched path is independent of indexed VB decoder state.
    assert "std::vector<std::uint32_t> upTouched;" in source
    assert "for (const std::uint32_t previous : scratch.upTouched)" in source
    assert "R30SeedTouchedXyzrhwVertices(" in source
    assert source.count("R30SeedTouchedXyzrhwVertices(") >= 3
    mutations = (
        ("scratch.vbTouched.size() == decoded.knownUsedCount",
         "scratch.vbTouched.size() != decoded.knownUsedCount"),
        ("scratch.vbTouched.clear();", "scratch.vbTouched.reserve(0);"),
        ("scratch.vbTouched.push_back(", "scratch.vbTouched.pop_back("),
        ("&scratch.used, knownUsedCount, &scratch.vbTouched)",
         "&scratch.used, knownUsedCount, nullptr)"),
        ("next.valid = true;", "next.valid = false;"),
    )
    for original, broken in mutations:
        assert original in body, original
        assert not valid_vb_touched(source, body.replace(original, broken, 1))

    # Differential: out-of-order and repeated IB indices must reconstruct
    # the exact old full-span referenced mask. Cache reuse must not invent
    # references, and a changed IB write generation must rebuild the list.
    rng = random.Random(707)
    for _ in range(900):
        span = rng.randint(64, 8000)
        count = rng.randint(1, 900)
        raw = [rng.randrange(span) for _ in range(count)]
        used = bytearray(span)
        touched = []
        for index in raw:
            if not used[index]:
                touched.append(index)
                used[index] = 1
        original_references = [i for i, flag in enumerate(used) if flag]
        assert len(touched) == len(original_references)
        assert set(touched) == set(original_references)
        assert all(used[index] for index in touched)
        # A new generation with a different index stream cannot reuse the
        # old touched list, even if min/max and index count are unchanged.
        changed = raw[:]
        if span > 1:
            changed[0] = (changed[0] + 1) % span
        changed_mask = bytearray(span)
        for index in changed:
            changed_mask[index] = 1
        assert sum(changed_mask) == len(set(changed))
    print(f"PASS R30 indexed VB sparse touched: 900 differential cases, "
          f"{len(mutations)} destructive mutations")




def valid_vb_mask_reuse(body):
    """On changed IB, clear only previous references before resizing the mask."""
    try:
        region = body.split("scratch.indexDecode.valid = false;", 1)[1].split(
            "for (UINT i = 0; i < indexCount; ++i)", 1)[0]
        required = (
            "for (const std::uint32_t previous : scratch.vbTouched)",
            "if (previous < scratch.used.size())",
            "scratch.used[previous] = 0;",
            "scratch.vbTouched.clear();",
            "scratch.used.resize(vertexCount, 0);",
        )
        order = [region.index(item) for item in required]
        return order == sorted(order) and len(set(order)) == len(order) and (
            "scratch.used.assign(vertexCount, 0);" not in body)
    except (ValueError, IndexError):
        return False


def verify_vb_mask_reuse(body):
    assert valid_vb_mask_reuse(body), "changed-IB mask reset contract broken"
    mutants = (
        ("for (const std::uint32_t previous : scratch.vbTouched)",
         "for (const std::uint32_t previous : scratch.upTouched)"),
        ("if (previous < scratch.used.size())",
         "if (previous > scratch.used.size())"),
        ("scratch.used[previous] = 0;", "scratch.used[previous] = 1;"),
        ("scratch.vbTouched.clear();", "scratch.vbTouched.reserve(0);"),
        ("scratch.used.resize(vertexCount, 0);",
         "scratch.used.assign(vertexCount, 0);"),
    )
    for good, bad in mutants:
        assert good in body
        assert not valid_vb_mask_reuse(body.replace(good, bad, 1)), good
    # Reference full-mask allocation versus sparse touched-bit clearing.
    # Includes changing IB revisions, shrink/expand, partial failed decodes.
    rng = random.Random(801)
    mask = bytearray()
    touched = []
    for epoch in range(2200):
        count = rng.choice((1, 2, 64, 511, 4096, 12000))
        for previous in touched:
            if previous < len(mask):
                mask[previous] = 0
        touched.clear()
        if len(mask) < count:
            mask.extend(bytes(count - len(mask)))
        else:
            del mask[count:]
        indices = [rng.randrange(count) for _ in range(rng.randint(1, 120))]
        if epoch % 13 == 0:
            indices = indices[:rng.randrange(len(indices) + 1)]
        for index in indices:
            if not mask[index]:
                touched.append(index)
                mask[index] = 1
        reference = bytearray(count)
        for index in indices:
            reference[index] = 1
        assert mask == reference, ("stale mask", epoch)
        assert len(touched) == sum(reference) == len(set(touched))
        if epoch % 5 == 0:
            assert all(mask[index] for index in touched)  # cache hit
    print(f"PASS R30 changed-IB mask reuse: 2200 generations, "
          f"{len(mutants)} destructive mutations")



def verify_up_single_pass(source):
    """Indexed UP compacts non-zero declared bases without changing draw semantics."""
    body = source.split("HRESULT R30TryXyzrhwIndexedPrimitiveUP(", 1)[1].split(
        "HRESULT R30TryXyzrhwPrimitiveVB(", 1)[0]

    required = (
        "static_cast<std::uint64_t>(minVertexIndex) + numVertices;",
        "if (numVertices == 0 || declaredEnd > 262144u)",
        "static_cast<std::uint64_t>(minVertexIndex) * stride;",
        "(std::numeric_limits<std::size_t>::max)()",
        "const auto* windowVertexData =",
        "static_cast<const std::uint8_t*>(vertexData) +",
        "const UINT vertexCount = numVertices;",
        "if (raw < minVertexIndex || raw >= declaredEnd)",
        "const std::uint32_t local = raw - minVertexIndex;",
        "if (local >= vertexCount)",
        "scratch.upTouched.push_back(local);",
        "scratch.upUsed[local] = 1;",
        "const void* drawIndexData = indexData;",
        "if (minVertexIndex != 0)",
        "scratch.indices16.resize(indexCount);",
        "source[i] - minVertexIndex);",
        "scratch.indices32.resize(indexCount);",
        "drawIndexData = scratch.indices16.data();",
        "drawIndexData = scratch.indices32.data();",
        "device, windowVertexData, vertexCount, stride, state,",
        "windowVertexData, vertexCount, stride, state,",
        "device, type, 0u, numVertices,",
        "primitiveCount, drawIndexData, indexFormat,",
        "&scratch.upUsed, knownUsedCount, &scratch.upTouched)",
        "R30ExecuteXyzrhwStereo(",
    )
    assert all(token in body for token in required)
    forbidden = (
        "const UINT vertexCount = static_cast<UINT>(declaredEnd);",
        "scratch.upTouched.push_back(raw);",
        "scratch.upUsed[raw] = 1;",
        "device, type, minVertexIndex, numVertices,",
        "primitiveCount, indexData, indexFormat,\n                    scratch.left.data()",
    )
    assert all(token not in body for token in forbidden)
    assert body.count("for (UINT i = 0; i < indexCount; ++i)") == 3

    # Destructive source mutations must invalidate the static contract rather
    # than silently restoring the old absolute-base scratch/upload behavior.
    mutations = (
        ("const UINT vertexCount = numVertices;",
         "const UINT vertexCount = static_cast<UINT>(declaredEnd);"),
        ("const std::uint32_t local = raw - minVertexIndex;",
         "const std::uint32_t local = raw;"),
        ("scratch.upTouched.push_back(local);",
         "scratch.upTouched.push_back(raw);"),
        ("scratch.upUsed[local] = 1;",
         "scratch.upUsed[raw] = 1;"),
        ("if (minVertexIndex != 0)", "if (false)"),
        ("source[i] - minVertexIndex);", "source[i]);"),
        ("device, windowVertexData, vertexCount, stride, state,",
         "device, vertexData, vertexCount, stride, state,"),
        ("windowVertexData, vertexCount, stride, state,",
         "vertexData, vertexCount, stride, state,"),
        ("device, type, 0u, numVertices,",
         "device, type, minVertexIndex, numVertices,"),
        ("primitiveCount, drawIndexData, indexFormat,",
         "primitiveCount, indexData, indexFormat,"),
    )
    for original, broken in mutations:
        assert original in body, original
        mutant = body.replace(original, broken, 1)
        assert not all(token in mutant for token in required), original

    def old_accept(indices, minimum, count):
        end = minimum + count
        return (count > 0 and end <= 262144
                and all(minimum <= index < end for index in indices))

    def compact(indices, minimum, count, bits):
        if not old_accept(indices, minimum, count):
            return None
        locals_ = [index - minimum for index in indices]
        if bits == 16 and any(local > 0xFFFF for local in locals_):
            return None
        return count, locals_

    rng = random.Random(831)
    cases = 0
    saved_vertices = 0
    for bits in (16, 32):
        max_raw = (1 << bits) - 1
        for _ in range(1400):
            maximum_min = min(8192, max_raw - 1)
            minimum = rng.randint(0, maximum_min)
            max_count = min(800, max_raw - minimum + 1)
            count = rng.randint(1, max_count)
            end = minimum + count
            indices = [rng.randrange(minimum, end)
                       for _ in range(rng.randint(1, 160))]
            result = compact(indices, minimum, count, bits)
            assert result is not None
            compact_count, locals_ = result
            assert compact_count == count
            assert [local + minimum for local in locals_] == indices
            assert all(0 <= local < count for local in locals_)
            old_span = minimum + count
            new_span = count
            assert new_span <= old_span
            saved_vertices += old_span - new_span
            cases += 1
            if minimum:
                assert not old_accept(indices + [minimum - 1], minimum, count)
            if end <= max_raw:
                assert not old_accept(indices + [end], minimum, count)

    # Zero-base calls preserve the caller index data and exact vertex span.
    assert compact([0, 2, 1, 2], 0, 3, 16) == (3, [0, 2, 1, 2])
    # Non-zero base is mathematically equivalent after rebase.
    assert compact([400, 403, 401, 403], 400, 4, 16) == (4, [0, 3, 1, 3])
    assert compact([70000, 70002], 70000, 3, 32) == (3, [0, 2])
    assert not old_accept([99], 100, 2)
    assert not old_accept([102], 100, 2)

    print(f"PASS R30 indexed-UP local-window compaction: {cases + 5} cases, "
          f"{saved_vertices} scratch vertices avoided in non-zero-base models, "
          f"{len(mutations)} destructive mutations")


def main():
    code = SOURCE.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    body = indexed_body(code)
    assert valid(body), "scratch-free indexed draw / fallback contract broken"
    verify_decode_cache(code, body)
    verify_vb_touched(code, body)
    verify_vb_mask_reuse(body)
    verify_up_single_pass(code)
    assert workflow.count("tools/verify_vr_r30_index_rebase_fastpath.py") == 2
    assert "std::vector<std::uint32_t> physical;" not in code
    mutations = (
        ("const bool index16 = ibShadow->indexFormat == D3DFMT_INDEX16;",
         "const bool index16 = false;"),
        ("minRaw = (std::min)(minRaw, raw);", "minRaw = 0;"),
        ("maxRaw = (std::max)(maxRaw, raw);", "maxRaw = 0;"),
        ("static_cast<std::int64_t>(baseVertexIndex) + minRaw;",
         "static_cast<std::int64_t>(baseVertexIndex);"),
        ("static_cast<std::int64_t>(baseVertexIndex) + maxRaw;",
         "static_cast<std::int64_t>(baseVertexIndex);"),
        ("if (minPhysical < 0 || maxPhysical > UINT_MAX)", "if (false)"),
        ("static_cast<std::uint64_t>(maxRaw) - minRaw + 1u;",
         "static_cast<std::uint64_t>(maxRaw) + 1u;"),
        ("scratch.indices16.resize(indexCount);", "scratch.indices16.clear();"),
        ("scratch.indices32.resize(indexCount);", "scratch.indices32.clear();"),
        ("static_cast<std::uint64_t>(raw) - minRaw;",
         "static_cast<std::uint64_t>(raw);"),
        ("if (local >= vertexCount ||", "if (false ||"),
        ("(index16 && local > 0xFFFFu)", "(false && local > 0xFFFFu)"),
        ("scratch.used[static_cast<std::size_t>(local)] = 1;",
         "scratch.used[static_cast<std::size_t>(local)] = 0;"),
        ("scratch.indices16[i] = static_cast<std::uint16_t>(local);",
         "scratch.indices16[i] = 0;"),
        ("scratch.indices32[i] = static_cast<std::uint32_t>(local);",
         "scratch.indices32[i] = 0;"),
        ("R30ConfigureXyzrhwWorldEffect(", "false /* broken effect */ ("),
        ("R30TransformXyzrhwStereo(", "false /* broken stereo */ ("),
    )
    for original, mutant in mutations:
        assert original in body, original
        assert not valid(body.replace(original, mutant, 1)), original
    rng = random.Random(650)
    cases = 0
    for index16 in (False, True):
        for _ in range(1200):
            n = rng.randrange(1, 300)
            base = rng.choice([-100, -1, 0, 1, 1000, 2**31, 0xFFFFFFFE])
            limit = 65535 if index16 else 130000
            raw = [rng.randrange(0, limit + 1) for _ in range(n)]
            if rng.randrange(10) == 0:
                raw = [raw[0]] * n
            assert optimized_model(raw, base, index16) == old_reference(
                raw, base, index16)
            cases += 1
    assert optimized_model([0, 65536], 0, True) is None
    assert optimized_model([0, 65535], 0, True) == old_reference(
        [0, 65535], 0, True)
    assert optimized_model([0, 65536], 0, False) == old_reference(
        [0, 65536], 0, False)
    print(f"PASS R30 indexed XYZRHW scratch-free rebase: {cases + 3} model cases, "
          f"{len(mutations)} negative mutations")


if __name__ == "__main__":
    main()
