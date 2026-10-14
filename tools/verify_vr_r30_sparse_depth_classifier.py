#!/usr/bin/env python3
"""R30 projected-depth sparse bounded visit contract (build-only; Quest3 UNTESTED).

The UP and shadowed VB/IB indexed producers publish unique touched indices
and a matching mask. For <=512 references the classifier visits only those
indices; 513..2048 sparse references use a bounded ascending sort to retain
the original first-512 sample. Leased 2049..16384 references quick-select
 the same first 512; dense/untrusted hints scan as before.
This tests both the classification result and fail-closed hint rejection.
"""
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
CPP = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
WORKFLOW = ROOT / ".github/workflows/vr-dx9ex-active.yml"


def sections(src):
    a = src.split("bool R30XyzrhwHasProjectedDepthSignature(", 1)[1]
    classifier = a.split("bool R30ConfigureXyzrhwWorldEffect(", 1)[0]
    setup = src.split("bool R30ConfigureXyzrhwWorldEffect(", 1)[1].split(
        "// OutRun can disable Z", 1)[0]
    up = src.split("HRESULT R30TryXyzrhwIndexedPrimitiveUP(", 1)[1].split(
        "HRESULT R30TryXyzrhwPrimitiveVB(", 1)[0]
    vb = src.split("HRESULT R30TryXyzrhwIndexedPrimitiveVB(", 1)[1].split(
        "// Called on every eligible FlatPerspectiveEffect draw.", 1)[0]
    return classifier, setup, up, vb


def static_contract(src, workflow):
    c, setup, up, vb = sections(src)
    for token in (
        "const std::vector<std::uint32_t>* touched) noexcept",
        "touched->size() <= 512u",
        "touched->size() <= vertexCount",
        "usedMask->size() >= vertexCount",
        "for (const std::uint32_t index : *touched)",
        "if (index >= vertexCount || (*usedMask)[index] == 0)",
        "const bool directHintOwnedByProducer = R30Scratch.busy &&",
        "fastTouched = fastTouched && directHintOwnedByProducer;",
        "R30Scratch.indexDecode.knownUsedCount == touched->size()",
        "fastTouched = false;",
        "const UINT visitCount = fastTouched",
        "const UINT i = fastTouched ? (*touched)[visit] :",
        "sortedTouched.empty() ? visit : sortedTouched[visit]",
        "visit < visitCount && sampled < 512u",
        "const UINT remaining = sampleLimit - sampled;",
        "const float projectionDepthScale =",
        "if (!projectionDepthFast || !std::isfinite(depthDelta) ||",
        "return sampled >= 3u && valid >= 3u",
        "touched->size() > 512u &&",
        "touched->size() <= 2048u",
        "touched->size() <= 16384u",
        "const bool largeSparseSample = sortedCandidate &&",
        "touched->size() > 2048u;",
        "largeSparseSample ? 512u : touched->size()",
        "if (largeSparseSample)",
        "for (const std::uint32_t index : sortedTouched)",
        "if (!membershipValid)",
        "std::nth_element(",
        "sortedTouched.begin() + 512u,",
        "sortedTouched.resize(512u);",
        "vertexCount / touched->size() >= 8u",
        "sortedTouched.assign(touched->begin(), touched->end());",
        "std::sort(sortedTouched.begin(), sortedTouched.end());",
        "sortedTouched[n - 1u] == index",
        "sortedTouched.clear(); // original dense fallback",
    ):
        assert token in c, ("classifier", token)
    # Two independent guarded consumers share these exact predicates:
    # <=512 direct reference list and 513..2048 sorted reference list.
    # A mutation removing either boundary must be rejected even when the
    # other path still retains the same token.
    assert c.count("touched->size() <= vertexCount") == 2
    assert c.count("usedMask->size() >= vertexCount") == 2
    direct_owner = c.split(
        "const bool directHintOwnedByProducer = R30Scratch.busy &&", 1)[1].split(
        "fastTouched = fastTouched && directHintOwnedByProducer;", 1)[0]
    for required in (
        "usedMask == &R30Scratch.upUsed",
        "touched == &R30Scratch.upTouched",
        "usedMask == &R30Scratch.used",
        "touched == &R30Scratch.vbTouched",
        "R30Scratch.indexDecode.valid &&",
        "R30Scratch.indexDecode.vertexCount == vertexCount",
        "R30Scratch.indexDecode.knownUsedCount == touched->size()",
    ):
        assert required in direct_owner, ("direct-owner", required)
    assert c.index("fastTouched = fastTouched && directHintOwnedByProducer;") < c.index(
        "for (const std::uint32_t index : *touched)")
    assert c.index("for (const std::uint32_t index : *touched)") < c.index(
        "for (UINT visit = 0; visit < visitCount")
    assert "for (UINT i = 0; i < vertexCount && sampled < 512u; ++i)" not in c
    assert "baseProjection, usedMask, touched);" in setup
    assert "const std::vector<std::uint32_t>* touched = nullptr" in setup
    assert ("&scratch.upUsed, nullptr, nullptr, nullptr,\n"
            "                    &scratch.upTouched))") in up
    assert "scratch.upTouched.push_back(raw);" in up
    assert "scratch.upUsed[raw] = 1;" in up
    assert "&scratch.indexCopy, &scratch.depthSignature," in vb
    assert "&scratch.vbTouched) ||" in vb
    assert "scratch.vbTouched.push_back(" in vb
    assert "scratch.used[static_cast<std::size_t>(local)] = 1;" in vb
    assert "scratch.indexDecode.valid = true;" not in vb  # published through next.valid
    assert "next.valid = true;" in vb
    # Same IB mask generation may be sorted once for multiple VB updates;
    # UP reuses capacity but never inherits the VB ordering. Unknown callers
    # retain the original allocation/sort/dense fallback contract.
    for token in (
        "R30Scratch.busy &&",
        "usedMask == &R30Scratch.used",
        "touched == &R30Scratch.vbTouched",
        "R30Scratch.indexDecode.valid",
        "R30Scratch.indexDecode.vertexCount == vertexCount",
        "R30Scratch.indexDecode.knownUsedCount == touched->size()",
        "usedMask == &R30Scratch.upUsed",
        "touched == &R30Scratch.upTouched",
        "const bool sortedCacheHit = sortedCandidate && trustedVbHint &&",
        "R30Scratch.vbDepthSortedGeneration ==",
        "largeSparseSample ? 512u : touched->size()",
        "if (!sortedCacheHit)",
        "sortedTouched.clear();",
        "sortedTouched.size() ==\n                    (largeSparseSample ? 512u : touched->size());",
        "if (!sortedTouched.empty() && trustedVbHint)",
    ):
        assert token in c, ("sort lifecycle", token)
    assert c.index("if (!sortedCacheHit)") < c.index(
        "sortedTouched.assign(touched->begin(), touched->end());")
    # Equality (==) in the cache-hit predicate is not the eventual
    # assignment; compare against the exact multiline success publication.
    assert c.index("std::sort(sortedTouched.begin(), sortedTouched.end());") < c.index(
        "R30Scratch.vbDepthSortedGeneration =\n")
    assert "std::vector<std::uint32_t> vbSortedDepthTouched;" in src
    assert "std::vector<std::uint32_t> upSortedDepthTouched;" in src
    assert "std::uint64_t vbTouchGeneration = 1;" in src
    assert "std::uint64_t vbDepthSortedGeneration = 0;" in src
    decoder = vb.split("if (!cachedDecode)", 2)[-1]
    assert "if (++scratch.vbTouchGeneration == 0)" in decoder
    assert decoder.index("if (++scratch.vbTouchGeneration == 0)") < decoder.index(
        "for (const std::uint32_t previous : scratch.vbTouched)")
    assert workflow.count("tools/verify_vr_r30_sparse_depth_classifier.py") == 2


def negative_mutations(src, workflow):
    for old, new in (
        ("touched->size() <= 512u", "touched->size() <= 2048u"),
        ("touched->size() <= vertexCount", "touched->size() > vertexCount"),
        ("usedMask->size() >= vertexCount", "usedMask->size() < vertexCount"),
        ("index >= vertexCount || (*usedMask)[index] == 0", "false"),
        ("fastTouched = false;", "fastTouched = true;"),
        ("fastTouched = fastTouched && directHintOwnedByProducer;",
         "fastTouched = true;"),
        ("const bool directHintOwnedByProducer = R30Scratch.busy &&",
         "const bool directHintOwnedByProducer = true &&"),
        ("sortedTouched.empty() ? visit : sortedTouched[visit]",
         "sortedTouched.empty() ? visit : visit"),
        ("std::sort(sortedTouched.begin(), sortedTouched.end());",
         "std::reverse(sortedTouched.begin(), sortedTouched.end());"),
        ("sortedTouched[n - 1u] == index",
         "sortedTouched[n - 1u] != index"),
        ("vertexCount / touched->size() >= 8u",
         "vertexCount / touched->size() >= 0u"),
        ("touched->size() <= 16384u", "touched->size() <= 65536u"),
        ("largeSparseSample ? 512u : touched->size()",
         "largeSparseSample ? 0u : touched->size()"),
        ("std::nth_element(", "std::reverse("),
        ("sortedTouched.resize(512u);", "sortedTouched.clear();"),
        ("if (!membershipValid)", "if (false)"),
        ("const bool sortedCacheHit = sortedCandidate && trustedVbHint &&",
         "const bool sortedCacheHit = sortedCandidate &&"),
        ("R30Scratch.vbDepthSortedGeneration ==",
         "R30Scratch.vbDepthSortedGeneration !="),
        ("usedMask == &R30Scratch.used",
         "usedMask == &R30Scratch.upUsed"),
        ("R30Scratch.indexDecode.valid &&",
         "true &&"),
        ("if (++scratch.vbTouchGeneration == 0)",
         "if (scratch.vbTouchGeneration == 0)"),
        ("visit < visitCount && sampled < 512u", "visit < vertexCount"),
        ("baseProjection, usedMask, touched);", "baseProjection, usedMask, nullptr);"),
        ("&scratch.upUsed, nullptr, nullptr, nullptr,\n"
         "                    &scratch.upTouched))",
         "&scratch.upUsed, nullptr, nullptr, nullptr,\n"
         "                    nullptr))"),
        ("&scratch.vbTouched) ||", "nullptr) ||"),
    ):
        assert src.count(old) >= 1, old
        candidate = src.replace(old, new, 1)
        try:
            static_contract(candidate, workflow)
        except (AssertionError, ValueError):
            continue
        raise AssertionError("destructive source mutation escaped: " + old)


def simulate(mask, touched, quality, fast, trusted=True):
    n = len(mask)
    use_touched = bool(fast and trusted and touched and len(touched) <= 512 and
                       len(touched) <= n and
                       all(0 <= i < n and mask[i] for i in touched))
    use_sorted = bool(fast and not use_touched and touched and
                      512 < len(touched) <= 16384 and len(touched) <= n and
                      (len(touched) <= 2048 or trusted) and
                      n // len(touched) >= 8 and
                      len(set(touched)) == len(touched) and
                      all(0 <= i < n and mask[i] for i in touched))
    visits = (touched if use_touched else
              sorted(touched) if use_sorted else range(n))
    sampled = valid = projected = 0
    limit = min(n, 512)
    for i in visits:
        if sampled >= 512:
            break
        if not mask[i]:
            continue
        sampled += 1
        v, p = quality[i]
        if v:
            valid += 1
            projected += bool(p)
        if sampled % 16 == 0:
            remaining = limit - sampled
            if (valid >= 3 and valid * 2 >= sampled + remaining and
                    projected * 4 >= (valid + remaining) * 3):
                return True
            if ((valid + remaining) * 2 < sampled + remaining or
                    (projected + remaining) * 4 <
                    (valid + remaining) * 3):
                return False
    return (sampled >= 3 and valid >= 3 and
            valid * 2 >= sampled and projected * 4 >= valid * 3)


def parity():
    rng = random.Random(714)
    for n in (3, 47, 512, 513, 4096, 65536):
        for count in (0, 1, 2, 3, 16, 127, 511, 512, 513, 700):
            count = min(count, n)
            selected = rng.sample(range(n), count)
            mask = bytearray(n)
            for i in selected:
                mask[i] = 1
            for kind in ("hud", "world", "mixed", "invalid"):
                quality = [(rng.random() > (0.1 if kind != "invalid" else 0.9),
                            (rng.random() < (0.94 if kind == "world" else
                                            0.03 if kind == "hud" else 0.72)))
                           for _ in range(n)]
                base = simulate(mask, selected, quality, False)
                fast = simulate(mask, selected, quality, True)
                assert base == fast, (n, count, kind)
            if count >= 513 and n // count >= 8:
                # Ascending first-512 identity is critical for World/HUD
                # projected-depth decisions on sparse indexed buffers.
                assert sorted(selected)[:512] == [
                    i for i in range(n) if mask[i]][:512]
                assert simulate(mask, selected[::-1], quality, True) == base
                bad = selected[:-1] + [selected[0]]
                assert simulate(mask, bad, quality, True) == base
            if count and count <= 512:
                # Unknown/corrupt lists may repeat a good vertex. The leased
                # unique-index producer contract is mandatory for the fast
                # path even if all mask members and bounds appear valid.
                duplicate = selected[:-1] + [selected[0]]
                assert simulate(mask, duplicate, quality, True,
                                trusted=False) == simulate(mask, duplicate,
                                                           quality, False)
                # Bad bounds or mask membership reject the hint, then use dense.
                bad = selected[:-1] + [n]
                assert simulate(mask, bad, quality, True) == simulate(
                    mask, bad, quality, False)
                missing = next((i for i in range(n) if not mask[i]), None)
                if missing is not None:
                    bad = selected[:-1] + [missing]
                    assert simulate(mask, bad, quality, True) == simulate(
                        mask, bad, quality, False)


def large_sparse_parity():
    # Sand/particle-like sparse spans previously fell back to a full 64K+
    # mask traversal above 2048 touched vertices. The first 512 referenced
    # vertices must remain EXACTLY those from the old ascending dense walk.
    rng = random.Random(822)
    for n, count in ((32768, 2500), (65536, 4096),
                     (131072, 8192), (262144, 16384)):
        touched = rng.sample(range(n), count)
        mask = bytearray(n)
        for index in touched:
            mask[index] = 1
        first512 = sorted(touched)[:512]
        assert first512 == [i for i in range(n) if mask[i]][:512]
        quality = [(True, bool((i * 13) % 5)) for i in range(n)]
        assert simulate(mask, touched, quality, True) == simulate(
            mask, touched, quality, False)
        assert simulate(mask, touched[::-1], quality, True) == simulate(
            mask, touched, quality, False)
        # A list not owned by the UP/VB decoder may not take the new path.
        assert simulate(mask, touched, quality, True, trusted=False) == (
            simulate(mask, touched, quality, False))
        damaged = touched[:]
        damaged[-1] = n
        assert simulate(mask, damaged, quality, True) == simulate(
            mask, damaged, quality, False)


def cached_mask_lifecycle():
    # Deterministic model: decoding generation changes must force a new
    # exact ascending first-512 order; new VBs/projections with unchanged
    # decoded IB reuse it. UP never inherits a different producer's hint.
    rng = random.Random(805)
    vb_sort_cache = None
    cached_generation = 0
    gen = 1
    sort_count = 0

    def classify_order(mask, touched, generation, source):
        nonlocal vb_sort_cache, cached_generation, sort_count
        stable = source == "vb"
        if (stable and vb_sort_cache is not None and
                cached_generation == generation and
                len(vb_sort_cache) == (512 if len(touched) > 2048 else
                                        len(touched))):
            order = vb_sort_cache
        else:
            order = sorted(touched)
            if len(touched) > 2048:
                # nth_element + sort stores only the first 512 values.
                # Model the same observable cache payload/order.
                order = order[:512]
            sort_count += 1
            if stable:
                vb_sort_cache, cached_generation = order, generation
        return order[:512]

    for generation_index, (n, count) in enumerate(
            ((8192, 700), (65536, 4096), (131072, 8192))):
        # Each new vertex span comes from a different decoded IB mask;
        # invalidate the previous generation across full and 512-entry
        # quick-select cache payloads.
        gen += 1
        selected = rng.sample(range(n), count)
        mask = bytearray(n)
        for i in selected:
            mask[i] = 1
        base = [i for i in range(n) if mask[i]][:512]
        assert classify_order(mask, selected, gen, "vb") == base
        for _ in range(15):
            assert classify_order(mask, selected, gen, "vb") == base
        assert sort_count == 3 * generation_index + 1
        if count > 2048:
            assert len(vb_sort_cache) == 512
        else:
            assert len(vb_sort_cache) == count
        # UP is independent and always builds its own ascending order.
        other = rng.sample(range(n), count)
        assert classify_order(mask, other, gen, "up") == sorted(other)[:512]
        gen += 1  # decoded IB revision, span or mask changed
        assert classify_order(mask, selected[::-1], gen, "vb") == base
        assert sort_count == 3 * (generation_index + 1)
    assert sort_count == 9  # 3 VB misses + 3 UP + 3 decode invalidations


if __name__ == "__main__":
    source = CPP.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    static_contract(source, workflow)
    negative_mutations(source, workflow)
    parity()
    large_sparse_parity()
    cached_mask_lifecycle()
    print("R30 sparse depth classifier: sort cache, generation invalidation, UP isolation, parity and mutations PASS; runtime UNTESTED")
