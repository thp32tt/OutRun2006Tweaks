#!/usr/bin/env python3
"""R30 projected-depth sparse bounded visit contract (build-only; Quest3 UNTESTED).

The UP and shadowed VB/IB indexed producers publish unique touched indices
and a matching mask. For <=512 references the classifier visits only those
indices; 513..2048 sparse references use a bounded ascending sort to retain
the original first-512 sample, while dense/untrusted hints scan as before.
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
        "fastTouched = false;",
        "const UINT visitCount = fastTouched",
        "const UINT i = fastTouched ? (*touched)[visit] :",
        "sortedTouched.empty() ? visit : sortedTouched[visit]",
        "visit < visitCount && sampled < 512u",
        "const UINT remaining = sampleLimit - sampled;",
        "const float projectionDepthScale =",
        "if (!projectionDepthFast || !std::isfinite(depthDelta) ||",
        "return sampled >= 3u && valid >= 3u",
        "touched->size() > 512u && touched->size() <= 2048u",
        "vertexCount / touched->size() >= 8u",
        "sortedTouched.assign(touched->begin(), touched->end());",
        "std::sort(sortedTouched.begin(), sortedTouched.end());",
        "sortedTouched[n - 1u] == index",
        "sortedTouched.clear(); // original dense fallback",
    ):
        assert token in c, ("classifier", token)
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
    assert workflow.count("tools/verify_vr_r30_sparse_depth_classifier.py") == 2


def negative_mutations(src, workflow):
    for old, new in (
        ("touched->size() <= 512u", "touched->size() <= 2048u"),
        ("touched->size() <= vertexCount", "touched->size() > vertexCount"),
        ("usedMask->size() >= vertexCount", "usedMask->size() < vertexCount"),
        ("index >= vertexCount || (*usedMask)[index] == 0", "false"),
        ("fastTouched = false;", "fastTouched = true;"),
        ("sortedTouched.empty() ? visit : sortedTouched[visit]",
         "sortedTouched.empty() ? visit : visit"),
        ("std::sort(sortedTouched.begin(), sortedTouched.end());",
         "std::reverse(sortedTouched.begin(), sortedTouched.end());"),
        ("sortedTouched[n - 1u] == index",
         "sortedTouched[n - 1u] != index"),
        ("vertexCount / touched->size() >= 8u",
         "vertexCount / touched->size() >= 0u"),
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


def simulate(mask, touched, quality, fast):
    n = len(mask)
    use_touched = bool(fast and touched and len(touched) <= 512 and
                       len(touched) <= n and
                       all(0 <= i < n and mask[i] for i in touched))
    use_sorted = bool(fast and not use_touched and touched and
                      512 < len(touched) <= 2048 and len(touched) <= n and
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
                # Bad bounds or mask membership reject the hint, then use dense.
                bad = selected[:-1] + [n]
                assert simulate(mask, bad, quality, True) == simulate(
                    mask, bad, quality, False)
                missing = next((i for i in range(n) if not mask[i]), None)
                if missing is not None:
                    bad = selected[:-1] + [missing]
                    assert simulate(mask, bad, quality, True) == simulate(
                        mask, bad, quality, False)


if __name__ == "__main__":
    source = CPP.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    static_contract(source, workflow)
    negative_mutations(source, workflow)
    parity()
    print("R30 sparse depth classifier: contract, 10 mutations, parity PASS; runtime UNTESTED")
