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
        "scratch.used.assign(vertexCount, 0);",
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
    setup = body.index("scratch.used.assign(vertexCount, 0);")
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
        "scratch.used.assign(vertexCount, 0);")
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
    fill = body.index("scratch.used.assign(vertexCount, 0);")
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



def verify_up_single_pass(source):
    """Full UP 16/32-bit sparse stereo, legal window, negative mutations."""
    body = source.split("HRESULT R30TryXyzrhwIndexedPrimitiveUP(", 1)[1].split(
        "HRESULT R30TryXyzrhwPrimitiveVB(", 1)[0]
    required = (
        "static_cast<std::uint64_t>(minVertexIndex) + numVertices;",
        "if (numVertices == 0 || declaredEnd > 262144u)",
        "if (raw < minVertexIndex || raw >= vertexCount)",
        "scratch.upTouched.push_back(raw);",
        "scratch.upUsed[raw] = 1;",
        "&scratch.upUsed, knownUsedCount, &scratch.upTouched)",
        "R30ExecuteXyzrhwStereo(",
    )
    assert all(token in body for token in required)
    assert "UINT maxIndex = 0;" not in body
    assert body.count("for (UINT i = 0; i < indexCount; ++i)") == 1
    for original, wrong in (
        ("numVertices == 0", "numVertices != 0"),
        ("declaredEnd > 262144u", "declaredEnd < 262144u"),
        ("raw < minVertexIndex", "false"),
        ("raw >= vertexCount", "false"),
        ("scratch.upTouched.push_back(raw);", "scratch.upTouched.clear();"),
        ("scratch.upUsed[raw] = 1;", "scratch.upUsed[raw] = 0;"),
    ):
        assert original in body
        mutant = body.replace(original, wrong, 1)
        assert not all(token in mutant for token in required), original

    def accepted(indices, minimum, count):
        end = minimum + count
        return (count > 0 and end <= 262144
                and all(minimum <= index < end for index in indices))

    rng = random.Random(792)
    for bits in (16, 32):
        max_raw = (1 << bits) - 1
        for _ in range(1000):
            low = rng.randint(0, 4096)
            count = rng.randint(1, 400)
            end = low + count
            indices = [rng.randrange(low, end)
                       for _ in range(rng.randint(1, 120))]
            # In-range original max-index scan and one-pass upper bound agree.
            old_end = max(end, max(indices) + 1)
            assert old_end == end and accepted(indices, low, count)
            assert set(indices) == set(indices)  # repeated index semantics
            if low:
                assert not accepted(indices + [low - 1], low, count)
            if end <= max_raw:
                assert not accepted(indices + [end], low, count)
    assert not accepted([0], 0, 0)
    assert not accepted([262144], 0, 262144)
    assert not accepted([0xFFFFFFFF], 0xFFFFFFFE, 4)
    assert accepted([0, 1, 0], 0, 2)
    print("PASS R30 indexed-UP one-pass: 2000 randomized 16/32-bit windows, "
          "invalid range/fallback and six destructive mutations")


def main():
    code = SOURCE.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    body = indexed_body(code)
    assert valid(body), "scratch-free indexed draw / fallback contract broken"
    verify_decode_cache(code, body)
    verify_vb_touched(code, body)
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
