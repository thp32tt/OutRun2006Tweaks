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
    # Final Release now erases only live entries, advancing the generation so
    # thread-local VB/IB lookup caches cannot reuse a recycled COM address.
    release_vb = body(source, "ULONG __stdcall R30VertexBufferReleaseDest(")
    release_ib = body(source, "ULONG __stdcall R30IndexBufferReleaseDest(")
    assert "if (R30VertexShadows.erase(buffer))" in release_vb
    assert "if (R30IndexShadows.erase(buffer))" in release_ib
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
    for token in ("if (!ranges.empty())", "auto& tail = ranges.back();",
                  "if (begin >= tail.begin)", "if (begin <= tail.end)",
                  "tail.end = (std::max)(tail.end, end);",
                  "ranges.push_back({begin, end});"):
        assert token in merge, token
    assert merge.index("if (!ranges.empty())") < merge.index("std::lower_bound(")
    assert "if (!ranges.empty() && begin >= ranges.back().begin)" in read
    assert "return end <= ranges.back().end;" in read
    assert read.index("return end <= ranges.back().end;") < read.index("std::lower_bound(")
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
        if ranges and begin >= ranges[-1][0]:
            if begin <= ranges[-1][1]:
                ranges[-1][1] = max(ranges[-1][1], end)
            else:
                ranges.append([begin, end])
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

    # 4,096 monotonically streamed partial writes exercise both O(1)
    # append (disjoint) and tail extension (adjacent/overlapping) paths.
    for stride, expected_len in ((16, 1), (24, 4096)):
        ranges = []
        for index in range(4096):
            begin = index * stride
            add(ranges, begin, begin + 16)
        assert len(ranges) == expected_len, (stride, ranges[:4])
        assert ranges[0] == [0, 16 if stride > 16 else 65536]
        if stride > 16:
            assert ranges[-1] == [4095 * stride, 4095 * stride + 16]
        # Writing within the newest tail never shrinks coverage.
        tail = list(ranges[-1])
        add(ranges, tail[0] + 2, tail[1] - 2)
        assert ranges[-1] == tail


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
        ("if (begin >= tail.begin)", "if (begin > tail.begin)"),
        ("if (begin <= tail.end)", "if (begin < tail.end)"),
        ("tail.end = (std::max)(tail.end, end);", "tail.end = end;"),
        ("ranges.push_back({begin, end});", "ranges.push_back({begin, begin});"),
        ("if (!ranges.empty() && begin >= ranges.back().begin)",
         "if (!ranges.empty() && begin <= ranges.back().begin)"),
        ("return end <= ranges.back().end;", "return end < ranges.back().end;"),
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
    # The incremental-copy helper has its own cache parameter; verify the two
    # original VB/IB readers independently instead of counting every helper.
    for reader in ("R30CopyVertexShadow", "R30CopyIndexShadow"):
        signature = source.split(f"bool {reader}(", 1)[1].split("{", 1)[0]
        assert "R30ShadowCopyCache& cache)" in signature
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
        assert fn.index("R30TryIncrementalShadowCopy(entry, offset, size, out, cache)") < fn.index("std::memcpy")
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
        ("++entry->revision;\n                R30RecordTelemetryCounter(R30ShadowDiscardInvalidations);",
         "R30RecordTelemetryCounter(R30ShadowDiscardInvalidations);"),
        ("++entry->revision;\n                    entry->lastWriteRevision = entry->revision;",
         "entry->lastWriteRevision = entry->revision;"),
        ("entry->valid.clear();\n                ++entry->revision;\n            }\n            return hr;", "entry->valid.clear();\n            }\n            return hr;"),
        ("static_cast<UINT>(indexBytes), scratch.indexSource,\n                    scratch.indexCopy))",
         "static_cast<UINT>(indexBytes), scratch.indexSource,\n                    scratch.vertexCopy))"),
        ("cache.entry.reset();\n                R30RecordTelemetryCounter(R30ShadowReadMisses);",
         "R30RecordTelemetryCounter(R30ShadowReadMisses);"),
    )
    for index, (needle, changed) in enumerate(changes, 1):
        assert needle in source, (index, needle)
        # A new incremental helper may contain the same tokens as the reader.
        # Target the vertex reader so a mutation cannot accidentally touch the
        # helper and leave both original VB/IB cache paths untested.
        vb_begin = source.index("bool R30CopyVertexShadow(")
        vb_end = source.index("bool R30CopyIndexShadow(", vb_begin)
        vb_reader = source[vb_begin:vb_end]
        if needle in vb_reader:
            altered = (source[:vb_begin] + vb_reader.replace(needle, changed, 1)
                       + source[vb_end:])
        else:
            altered = source.replace(needle, changed, 1)
        try:
            validate_shadow_copy_cache(altered)
        except AssertionError:
            pass
        else:
            raise AssertionError("copy-cache mutation survived: " + str(index))



def validate_shadow_registry_lookup(source):
    """Validate the epoch-fenced four-way VB/IB lookup shared by both wrappers."""
    find_v = body(source, "R30ShadowPtr R30FindVertexShadow(")
    find_i = body(source, "R30ShadowPtr R30FindIndexShadow(")
    common = body(source, "R30ShadowPtr R30FindShadow(")
    assert "std::atomic<std::uint64_t> R30ShadowRegistryEpoch{1};" in source
    assert "Slot slots[4]{};" in source
    assert "unsigned next = 0;" in source
    assert "return R30FindShadow(buffer, R30VertexShadows, R30VertexLookup);" in find_v
    assert "return R30FindShadow(buffer, R30IndexShadows, R30IndexLookup);" in find_i

    for token in (
        "R30ShadowRegistryEpoch.load(std::memory_order_acquire)",
        "if (cached.epoch == epoch)",
        "for (const auto& slot : cached.slots)",
        "if (slot.buffer == buffer)",
        "return slot.entry;",
        "std::lock_guard<std::mutex> lock(R30ShadowRegistryMutex);",
        "R30ShadowRegistryEpoch.load(std::memory_order_relaxed)",
        "if (cached.epoch != lockedEpoch)",
        "for (auto& slot : cached.slots)",
        "slot = {};",
        "cached.epoch = lockedEpoch;",
        "cached.next = 0;",
        "registry.find(buffer)",
        "auto& slot = cached.slots[cached.next];",
        "cached.next = (cached.next + 1u) % 4u;",
        "slot.buffer = buffer;",
        "slot.entry = it == registry.end() ? nullptr : it->second;",
    ):
        assert token in common, token

    # A positive or negative hit avoids the registry lock. Every miss
    # captures the current membership generation while holding that lock;
    # a concurrent Reset/Release cannot fill a slot with an older epoch.
    assert common.index("if (cached.epoch == epoch)") < common.index(
        "std::lock_guard<std::mutex> lock(R30ShadowRegistryMutex);")
    assert common.index("std::lock_guard<std::mutex> lock(R30ShadowRegistryMutex);") < (
        common.index("R30ShadowRegistryEpoch.load(std::memory_order_relaxed)"))
    assert common.index("if (cached.epoch != lockedEpoch)") < common.index(
        "registry.find(buffer)")
    assert common.index("registry.find(buffer)") < common.index(
        "slot.entry = it == registry.end() ? nullptr : it->second;")
    assert "if (slot.buffer == buffer && slot.entry)" not in common

    for type in ("Vertex", "Index"):
        ensure = body(source, f"R30ShadowPtr R30Ensure{type}Shadow(")
        release = body(source, f"ULONG __stdcall R30{type}BufferReleaseDest(")
        assert "if (inserted)" in ensure
        assert "R30ShadowRegistryEpoch.fetch_add(1, std::memory_order_release);" in ensure
        assert f"if (R30{type}Shadows.erase(buffer))" in release
        assert "R30ShadowRegistryEpoch.fetch_add(" in release
    rollback = body(source, "void R30RollbackBufferShadowHooks(")
    assert rollback.index("R30VertexShadows.clear();") < rollback.index(
        "R30ShadowRegistryEpoch.fetch_add(")
    assert rollback.index("R30IndexShadows.clear();") < rollback.index(
        "R30ShadowRegistryEpoch.fetch_add(")


def exercise_shadow_negative_lookup_model():
    """Alternating positive/negative entries survive hits; lifetime epochs do not."""
    membership = {}
    caches = {kind: {"epoch": 0, "slots": [(None, None)] * 4, "next": 0}
              for kind in ("VB", "IB")}
    epoch = 1
    lock_lookups = 0

    def find(kind, pointer):
        nonlocal lock_lookups
        cache = caches[kind]
        if cache["epoch"] == epoch:
            for key, value in cache["slots"]:
                if key == pointer:
                    return value
        lock_lookups += 1
        if cache["epoch"] != epoch:
            cache["slots"] = [(None, None)] * 4
            cache["epoch"] = epoch
            cache["next"] = 0
        value = membership.get((kind, pointer))
        cache["slots"][cache["next"]] = (pointer, value)
        cache["next"] = (cache["next"] + 1) % 4
        return value

    def register(kind, pointer, value):
        nonlocal epoch
        if find(kind, pointer) is not None:
            return
        if (kind, pointer) not in membership:
            membership[(kind, pointer)] = value
            epoch += 1

    def release(kind, pointer):
        nonlocal epoch
        if membership.pop((kind, pointer), None) is not None:
            epoch += 1

    for kind in ("VB", "IB"):
        # Four alternating untracked addresses should incur only four misses.
        first = lock_lookups
        for i in range(512):
            assert find(kind, (0x1234, 0x2345, 0x3456, 0x4567)[i % 4]) is None
        assert lock_lookups == first + 4, (kind, "negative-cache thrash")
        register(kind, 0x1234, "old")
        first = lock_lookups
        for i in range(512):
            assert find(kind, (0x1234, 0x2345, 0x3456, 0x4567)[i % 4]) == (
                "old" if i % 4 == 0 else None)
        assert lock_lookups == first + 4, (kind, "mixed-cache thrash")
        release(kind, 0x1234)
        assert find(kind, 0x1234) is None
        register(kind, 0x1234, "recycled")
        assert find(kind, 0x1234) == "recycled"
        release(kind, 0x1234)
        assert find(kind, 0x1234) is None

    # A membership change in either registry invalidates both lookup families.
    assert find("VB", 0xFEED) is None
    register("IB", 0xBEEF, "indexed")
    before = lock_lookups
    assert find("VB", 0xFEED) is None
    assert lock_lookups == before + 1
    release("IB", 0xBEEF)


def test_shadow_registry_lookup_mutations(source):
    # Keep the legacy descriptor gate's independent lifecycle coverage after
    # the single-slot lookup was replaced by a shared two-way helper.
    edits = (
        ("Slot slots[4]{};", "Slot slots[1]{};"),
        ("if (cached.epoch == epoch)", "if (cached.epoch != epoch)"),
        ("if (slot.buffer == buffer)", "if (slot.buffer == buffer && slot.entry)"),
        ("R30ShadowRegistryEpoch.load(std::memory_order_acquire)",
         "R30ShadowRegistryEpoch.load(std::memory_order_relaxed)"),
        ("std::lock_guard<std::mutex> lock(R30ShadowRegistryMutex);\n            const auto lockedEpoch",
         "const auto lockedEpoch"),
        ("if (cached.epoch != lockedEpoch)", "if (cached.epoch == lockedEpoch)"),
        ("slot = {};", "/* retain stale slot */"),
        ("cached.epoch = lockedEpoch;", "cached.epoch = epoch;"),
        ("cached.next = (cached.next + 1u) % 4u;", "cached.next = 0u;"),
        ("slot.entry = it == registry.end() ? nullptr : it->second;",
         "slot.entry = nullptr;"),
        ("if (inserted)\n                R30ShadowRegistryEpoch.fetch_add(1, std::memory_order_release);",
         "if (inserted) {}"),
        ("if (R30VertexShadows.erase(buffer))", "if (false)"),
        ("if (R30IndexShadows.erase(buffer))", "if (false)"),
        ("R30IndexShadows.clear();\n                R30VertexShadows.clear();\n                R30ShadowRegistryEpoch.fetch_add(",
         "R30IndexShadows.clear();\n                R30VertexShadows.clear();\n                ("),
        ("return R30FindShadow(buffer, R30IndexShadows, R30IndexLookup);",
         "return R30FindShadow(buffer, R30IndexShadows, R30VertexLookup);"),
    )
    for i, (needle, replacement) in enumerate(edits, 1):
        assert needle in source, (i, needle)
        mutated = source.replace(needle, replacement, 1)
        try:
            validate_shadow_registry_lookup(mutated)
        except (AssertionError, ValueError):
            continue
        raise AssertionError(f"R30 registry negative mutation {i} escaped")


def main():
    source = SOURCE.read_text(encoding="utf-8")
    validate(source)
    validate_range_fastpath(source)
    exercise_range_model()
    test_range_mutations(source)
    validate_shadow_copy_cache(source)
    test_shadow_copy_cache_mutations(source)
    validate_shadow_registry_lookup(source)
    exercise_shadow_negative_lookup_model()
    test_shadow_registry_lookup_mutations(source)
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
    print("PASS R30 VB/IB tail-streamed shadow range append/merge/read, descriptor, range and revision-keyed shadow copy cache; 11 descriptor + 8 range + 13 copy + 15 registry negative mutations; VB/IB negative-cache/recycle model")


if __name__ == "__main__":
    main()
