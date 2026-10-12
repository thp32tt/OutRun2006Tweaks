#!/usr/bin/env python3
"""R30 XYZRHW immutable VB/IB descriptor hot-path contract and negative tests."""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d9/stereo_renderer_r30.cpp"


def body(text, signature):
    begin = text.index("{", text.index(signature))
    depth = 0
    for pos in range(begin, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[begin:pos + 1]
    raise AssertionError("unclosed function " + signature)


def validate(source):
    ensure_vb = body(source, "R30ShadowPtr R30EnsureVertexShadow(")
    ensure_ib = body(source, "R30ShadowPtr R30EnsureIndexShadow(")
    copy_vb = body(source, "bool R30CopyVertexShadow(")
    copy_ib = body(source, "bool R30CopyIndexShadow(")
    draw_vb = body(source, "HRESULT R30TryXyzrhwPrimitiveVB(")
    draw_ib = body(source, "HRESULT R30TryXyzrhwIndexedPrimitiveVB(")
    assert "buffer->GetDesc(&desc)" in ensure_vb
    assert "buffer->GetDesc(&desc)" in ensure_ib
    assert "entry->size = desc.Size;" in ensure_vb
    assert "entry->size = desc.Size;" in ensure_ib
    assert "entry->indexFormat = desc.Format;" in ensure_ib
    assert "R30VertexShadows.erase(buffer);" in source
    assert "R30IndexShadows.erase(buffer);" in source
    assert "R30VertexShadows.clear();" in source
    assert "R30IndexShadows.clear();" in source
    for copy, signature in ((copy_vb, "const R30ShadowPtr& entry,"),
                            (copy_ib, "const R30ShadowPtr& entry,")):
        assert signature in source
        assert "if (!entry)" in copy
        assert "offset > entry->size || size > entry->size - offset" in copy
        assert "R30RangeValid(entry->valid, offset, offset + size)" in copy
        assert "std::lock_guard<std::mutex> lock(entry->mutex)" in copy
        assert "R30FindVertexShadow(" not in copy
        assert "R30FindIndexShadow(" not in copy
    for draw in (draw_vb, draw_ib):
        assert "GetDesc(" not in draw
        assert "R30EnsureVertexShadow(vb)" in draw
        assert "firstByte > desc.Size" not in draw
        assert "R30CopyVertexShadow(vbShadow," in draw
        assert "return E_NOTIMPL;" in draw
    assert "if (!vbShadow)" in draw_vb
    assert "firstByte > vbShadow->size" in draw_vb
    assert "byteCount > vbShadow->size - firstByte" in draw_vb
    assert "firstByte > UINT_MAX || byteCount > UINT_MAX" in draw_vb
    assert "R30EnsureIndexShadow(ib)" in draw_ib
    assert "if (!vbShadow || !ibShadow ||" in draw_ib
    assert "ibShadow->indexFormat != D3DFMT_INDEX16" in draw_ib
    assert "ibShadow->indexFormat != D3DFMT_INDEX32" in draw_ib
    assert "firstIndexByte > ibShadow->size" in draw_ib
    assert "indexBytes > ibShadow->size - firstIndexByte" in draw_ib
    assert "firstIndexByte > UINT_MAX || indexBytes > UINT_MAX" in draw_ib
    assert "firstVertexByte > vbShadow->size" in draw_ib
    assert "vertexBytes > vbShadow->size - firstVertexByte" in draw_ib
    assert "firstVertexByte > UINT_MAX || vertexBytes > UINT_MAX" in draw_ib
    assert "R30CopyIndexShadow(ibShadow," in draw_ib
    assert "rebased, ibShadow->indexFormat," in draw_ib



def validate_range_fastpath(source):
    merge = body(source, "void R30MergeValidRange(")
    read = body(source, "bool R30RangeValid(")
    assert "std::lower_bound(ranges.begin(), ranges.end(), begin," in merge
    assert "std::lower_bound(ranges.begin(), ranges.end(), begin," in read
    for part in (merge, read):
        assert "return range.end < position;" in part
    for part in (
        "if (begin >= end)",
        "if (first == ranges.end() || first->begin > end)",
        "ranges.insert(first, { begin, end });",
        "first->begin = (std::min)(first->begin, begin);",
        "first->end = (std::max)(first->end, end);",
        "while (last != ranges.end() && last->begin <= first->end)",
        "first->end = (std::max)(first->end, last->end);",
        "ranges.erase(first + 1, last);",
    ):
        assert part in merge, part
    assert "return first != ranges.end() &&" in read
    assert "first->begin <= begin && first->end >= end;" in read
    assert "ranges.erase(it)" not in merge
    assert "for (const auto& range : ranges)" not in read


def exercise_range_model():
    # Differential, deterministic interval coverage model including adjacency,
    # duplicate writes, reverse writes and a wide bridging write.
    def add(ranges, begin, end):
        if begin >= end:
            return
        first = next((i for i, (a, b) in enumerate(ranges) if b >= begin), len(ranges))
        if first == len(ranges) or ranges[first][0] > end:
            ranges.insert(first, [begin, end])
            return
        ranges[first][0] = min(ranges[first][0], begin)
        ranges[first][1] = max(ranges[first][1], end)
        last = first + 1
        while last < len(ranges) and ranges[last][0] <= ranges[first][1]:
            ranges[first][1] = max(ranges[first][1], ranges[last][1])
            last += 1
        del ranges[first + 1:last]

    for seed in range(96):
        ranges = []
        covered = set()
        for i in range(90):
            begin = (seed * 211 + i * 71 + (i * i * 13)) % 1024
            end = min(1024, begin + ((seed * 19 + i * 31) % 80))
            add(ranges, begin, end)
            covered.update(range(begin, end))
            assert all(0 <= a < b <= 1024 for a, b in ranges)
            assert all(ranges[j][1] < ranges[j + 1][0]
                       for j in range(len(ranges) - 1))
            for check_begin in range(0, 1024, 13):
                check_end = min(1024, check_begin + 1 + (seed + i) % 21)
                found = any(a <= check_begin and b >= check_end for a, b in ranges)
                expected = all(x in covered for x in range(check_begin, check_end))
                assert found == expected, (seed, i, check_begin)
        add(ranges, 0, 1024)
        assert ranges == [[0, 1024]]


def test_range_mutations(source):
    mutations = (
        ("return range.end < position;", "return range.end <= position;"),
        ("first->begin > end", "first->begin >= end"),
        ("ranges.insert(first, { begin, end });", "ranges.insert(first, { begin, begin });"),
        ("first->begin = (std::min)(first->begin, begin);", "first->begin = begin;"),
        ("first->end = (std::max)(first->end, end);", "first->end = end;"),
        ("last->begin <= first->end", "last->begin < first->end"),
        ("ranges.erase(first + 1, last);", "ranges.erase(first + 1, first + 1);"),
        ("first->end >= end", "first->end < end"),
    )
    for needle, replacement in mutations:
        assert needle in source, needle
        mutant = source.replace(needle, replacement, 1)
        try:
            validate_range_fastpath(mutant)
        except AssertionError:
            pass
        else:
            raise AssertionError("range mutation survived: " + needle)



def validate_shadow_copy_cache(source):
    """Same-entry/same-generation byte-range reuse; writes must invalidate."""
    begin = body(source, "void R30BeginObservedLock(")
    finish = body(source, "void R30FinishObservedLock(")
    vb_unlock = body(source, "HRESULT __stdcall R30VertexBufferUnlockDest(")
    ib_unlock = body(source, "HRESULT __stdcall R30IndexBufferUnlockDest(")
    vb_copy = body(source, "bool R30CopyVertexShadow(")
    ib_copy = body(source, "bool R30CopyIndexShadow(")
    primitive = body(source, "HRESULT R30TryXyzrhwPrimitiveVB(")
    indexed = body(source, "HRESULT R30TryXyzrhwIndexedPrimitiveVB(")

    assert "std::uint64_t revision = 1;" in source
    assert "R30ShadowCopyCache vertexCopy;" in source
    assert "R30ShadowCopyCache indexCopy;" in source
    assert "R30ShadowPtr entry;" in source
    assert source.count("R30ShadowCopyCache& cache)") == 2
    for fn in (begin, finish, vb_unlock, ib_unlock):
        assert "++entry->revision;" in fn
    assert "entry->valid.clear();" in begin
    assert "entry->valid.clear();" in vb_unlock
    assert "entry->valid.clear();" in ib_unlock
    assert finish.count("++entry->revision;") >= 3  # success, exception, failure
    for fn in (vb_copy, ib_copy):
        for required in (
            "std::lock_guard<std::mutex> lock(entry->mutex)",
            "!R30RangeValid(entry->valid, offset, offset + size)",
            "cache.entry == entry",
            "cache.offset == offset",
            "cache.size == size",
            "cache.revision == entry->revision",
            "out.size() == size",
            "std::memcpy(out.data(), entry->bytes.data() + offset, size)",
            "cache.entry = entry;",
            "cache.offset = offset;",
            "cache.size = size;",
            "cache.revision = entry->revision;",
            "cache.entry.reset();",
        ):
            assert required in fn, required
        assert fn.count("cache.entry.reset();") >= 3
        # A stable (entry, offset, size, revision) copy was already range-
        # validated under this mutex; only misses run the interval binary search.
        assert fn.index("std::lock_guard<std::mutex> lock(entry->mutex)") < fn.index("cache.entry == entry")
        assert fn.index("cache.entry == entry") < fn.index("!R30RangeValid")
        assert fn.index("cache.revision == entry->revision") < fn.index("!R30RangeValid")
        assert fn.index("cache.revision == entry->revision") < fn.index("std::memcpy")
        assert fn.index("std::memcpy") < fn.index("cache.revision = entry->revision;")
    assert "scratch.source,\n                    scratch.vertexCopy))" in primitive
    assert "scratch.source,\n                    scratch.vertexCopy))" in indexed
    assert "scratch.indexSource,\n                    scratch.indexCopy))" in indexed


def test_shadow_copy_cache_mutations(source):
    changes = (
        ("cache.entry == entry", "cache.entry != entry"),
        ("!R30RangeValid(entry->valid, offset, offset + size)", "false"),
        ("cache.offset == offset", "cache.offset != offset"),
        ("cache.size == size", "cache.size != size"),
        ("cache.revision == entry->revision", "cache.revision == cache.revision"),
        ("out.size() == size", "out.size() != size"),
        ("cache.entry = entry;", "cache.entry.reset();"),
        ("cache.revision = entry->revision;", "cache.revision = 0;"),
        ("std::memcpy(out.data(), entry->bytes.data() + offset, size)", "// missing CPU shadow refresh"),
        ("++entry->revision;\n                ++R30ShadowDiscardInvalidations;", "++R30ShadowDiscardInvalidations;"),
        ("++entry->revision;\n                    ++R30ShadowWrites;", "++R30ShadowWrites;"),
        ("entry->valid.clear();\n                ++entry->revision;\n            }\n            return hr;", "entry->valid.clear();\n            }\n            return hr;"),
        ("static_cast<UINT>(indexBytes), scratch.indexSource,\n                    scratch.indexCopy))",
         "static_cast<UINT>(indexBytes), scratch.indexSource,\n                    scratch.vertexCopy))"),
        ("cache.entry.reset();\n                ++R30ShadowReadMisses;",
         "++R30ShadowReadMisses;"),
    )
    for index, (needle, changed) in enumerate(changes, 1):
        assert needle in source, (index, needle)
        altered = source.replace(needle, changed, 1)
        try:
            validate_shadow_copy_cache(altered)
        except AssertionError:
            pass
        else:
            raise AssertionError("copy-cache mutation survived: " + str(index))


def main():
    source = SOURCE.read_text(encoding="utf-8")
    validate(source)
    validate_range_fastpath(source)
    exercise_range_model()
    test_range_mutations(source)
    validate_shadow_copy_cache(source)
    test_shadow_copy_cache_mutations(source)
    mutations = (
        ("if (!vbShadow)", "if (false)"),
        ("firstByte > vbShadow->size", "false"),
        ("byteCount > vbShadow->size - firstByte", "false"),
        ("if (!vbShadow || !ibShadow ||", "if (false ||"),
        ("ibShadow->indexFormat != D3DFMT_INDEX32", "false"),
        ("firstIndexByte > ibShadow->size", "false"),
        ("indexBytes > ibShadow->size - firstIndexByte", "false"),
        ("firstVertexByte > vbShadow->size", "false"),
        ("vertexBytes > vbShadow->size - firstVertexByte", "false"),
        ("R30CopyIndexShadow(ibShadow,", "R30CopyIndexShadow(ib,"),
        ("R30CopyVertexShadow(vbShadow,", "R30CopyVertexShadow(vb,"),
    )
    for needle, bad in mutations:
        assert needle in source, needle
        mutant = source.replace(needle, bad, 1)
        try:
            validate(mutant)
        except AssertionError:
            pass
        else:
            raise AssertionError("mutation survived: " + needle)
    print("PASS R30 VB/IB descriptor, range and revision-keyed shadow copy cache; 11 descriptor + 8 range + 13 cache negative mutations")


if __name__ == "__main__":
    main()
