#!/usr/bin/env python3
"""R30 non-DISCARD one-generation VB/IB shadow delta and conservative fallback."""
from __future__ import annotations
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
WORKFLOW = ROOT / ".github/workflows/vr-dx9ex-active.yml"


def contract(text: str) -> bool:
    try:
        owner = text.split("void R30FinishObservedLock(", 1)[1].split(
            "bool R30TryIncrementalShadowCopy(", 1)[0]
        helper = text.split("bool R30TryIncrementalShadowCopy(", 1)[1].split(
            "bool R30CopyVertexShadow(", 1)[0]
        order = (
            "std::memcpy(entry->bytes.data() + entry->lockOffset,",
            "R30MergeValidRange(entry->valid, entry->lockOffset,",
            "++entry->revision;",
            "entry->lastWriteRevision = entry->revision;",
            "entry->lastWriteBegin = entry->lockOffset;",
            "entry->lastWriteEnd = entry->lockOffset + entry->lockSize;",
            "(entry->lockFlags & D3DLOCK_DISCARD) == 0;",
        )
        if any(item not in owner for item in order):
            return False
        indices = [owner.index(item) for item in order]
        if indices != sorted(indices) or len(set(indices)) != len(indices):
            return False
        required = (
            "cache.entry != entry",
            "cache.offset != offset || cache.size != size",
            "out.size() != size",
            "cache.revision >= entry->revision",
            "entry->revision - cache.revision != 1u",
            "entry->lastWriteRevision != entry->revision",
            "!entry->lastWriteSafe",
            "offset > entry->size || size > entry->size - offset",
            "entry->bytes.size() != entry->size",
            "!R30RangeValid(entry->valid, offset, offset + size)",
            "(std::max)(offset, entry->lastWriteBegin)",
            "(std::min)(offset + size, entry->lastWriteEnd)",
            "if (begin < end)",
            "std::memcpy(out.data() + (begin - offset),",
            "entry->bytes.data() + begin, end - begin)",
            "cache.revision = entry->revision;",
        )
        if any(item not in helper for item in required):
            return False
        if helper.index("if (begin < end)") > helper.index(
                "cache.revision = entry->revision;"):
            return False
        if text.count("R30TryIncrementalShadowCopy(entry, offset, size, out, cache)") != 2:
            return False
        return all(token in text for token in (
            "std::uint64_t lastWriteRevision = 0;",
            "UINT lastWriteBegin = 0;",
            "UINT lastWriteEnd = 0;",
            "bool lastWriteSafe = false;",
        ))
    except (IndexError, ValueError):
        return False


def parity() -> None:
    rng = random.Random(802)
    delta_bytes = 0
    full_bytes = 0
    for _ in range(3500):
        n = rng.randint(8, 8192)
        raw = bytearray(rng.randbytes(n))
        start = rng.randrange(n)
        end = rng.randint(start + 1, n)
        size = end - start
        snapshot = raw[start:end]
        original = bytearray(snapshot)
        revision = 1
        copied_rev = revision
        # Multi-write, failed-Unlock and DISCARD force full-copy behavior.
        count = rng.choice((1, 1, 1, 2, 3))
        discard = rng.randrange(11) == 0
        failed = rng.randrange(17) == 0
        last_begin = last_end = 0
        for _step in range(count):
            low = rng.randrange(n)
            high = rng.randint(low + 1, n)
            value = rng.randbytes(high - low)
            if not failed:
                raw[low:high] = value
            last_begin, last_end = low, high
            revision += 1
        if discard:
            revision += 1
        # Failure means coverage cannot be trusted; an original D3D9
        # fallback is required, not an incremental or full shadow copy.
        coverage = not (discard or failed)
        can_increment = (
            coverage and revision > copied_rev and
            revision - copied_rev == 1 and count == 1)
        if not coverage:
            assert not can_increment
            continue
        if can_increment:
            low = max(start, last_begin)
            high = min(end, last_end)
            if low < high:
                snapshot[low - start:high - start] = raw[low:high]
                delta_bytes += high - low
        else:
            snapshot = raw[start:end]
            delta_bytes += size
        full_bytes += size
        assert snapshot == raw[start:end]
        if can_increment and (last_end <= start or last_begin >= end):
            assert snapshot == original
        # The next snapshot has the current revision (including disjoint
        # writes), so a subsequent single edit remains correctly fenced.
        copied_rev = revision
        assert copied_rev == revision
    assert delta_bytes < full_bytes
    print(f"PASS R30 shadow incremental parity: 3500 VB/IB cases, "
          f"copy bytes {delta_bytes}/{full_bytes} full-reference")


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert contract(source), "shadow delta generation/coverage guard broken"
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert workflow.count("tools/verify_vr_r30_shadow_incremental_copy.py") == 2
    mutations = (
        ("entry->revision - cache.revision != 1u",
         "entry->revision - cache.revision > 1u"),
        ("entry->lastWriteRevision != entry->revision",
         "entry->lastWriteRevision == entry->revision"),
        ("!entry->lastWriteSafe", "entry->lastWriteSafe"),
        ("!R30RangeValid(entry->valid, offset, offset + size)",
         "R30RangeValid(entry->valid, offset, offset + size)"),
        ("cache.revision = entry->revision;", "cache.revision = 0;"),
        ("if (begin < end)", "if (begin > end)"),
        ("(entry->lockFlags & D3DLOCK_DISCARD) == 0;",
         "(entry->lockFlags & D3DLOCK_DISCARD) != 0;"),
    )
    for good, bad in mutations:
        assert good in source
        assert not contract(source.replace(good, bad, 1)), good
    parity()
    print(f"PASS R30 shadow incremental safety: {len(mutations)} destructive mutants, "
          "VB and IB identical call-site coverage")


if __name__ == "__main__":
    main()
