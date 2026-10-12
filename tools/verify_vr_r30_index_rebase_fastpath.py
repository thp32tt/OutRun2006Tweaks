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
        "scratch.physical[i] = static_cast<std::uint32_t>(p);",
        "scratch.used.assign(vertexCount, 0);",
        "scratch.indices16.resize(indexCount);",
        "scratch.indices32.resize(indexCount);",
        "scratch.physical[i] -",
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
    if body.count("for (UINT i = 0; i < indexCount; ++i)") != 2:
        return False
    first = body.index("scratch.physical[i] =")
    prepare = body.index("scratch.used.assign(vertexCount, 0);")
    second = body.index("scratch.physical[i] -")
    mark = body.index("scratch.used[static_cast<std::size_t>(local)] = 1;")
    output16 = body.index("scratch.indices16[i] = static_cast<std::uint16_t>(local);")
    output32 = body.index("scratch.indices32[i] = static_cast<std::uint32_t>(local);")
    transform = body.index("R30ConfigureXyzrhwWorldEffect(")
    leftdraw = body.index("auto leftDraw = [&]()")
    return (
        first < prepare < second < mark < output16 < output32 < transform < leftdraw
        and body.index("if (p < 0 || p > UINT_MAX)") < first
        and body.index("const UINT vertexCount = static_cast<UINT>(vertexCount64);") < prepare
        and "if (vertexCount64 > 65535u)" not in body
        and "scratch.indices16[i] = static_cast<std::uint16_t>(scratch.physical[i]);" not in body
    )


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
    physical = []
    minimum, maximum = (1 << 63) - 1, -(1 << 63)
    for value in raw:
        p = base + value
        if p < 0 or p > 0xFFFFFFFF:
            return None
        physical.append(p)
        minimum, maximum = min(minimum, p), max(maximum, p)
    if not physical:
        return None
    size = maximum - minimum + 1
    if size > 262144:
        return None
    used = [0] * size
    rebased = [0] * len(raw)
    for i, p in enumerate(physical):
        local = p - minimum
        if local >= size or (index16 and local > 0xFFFF):
            return None
        used[local] = 1
        rebased[i] = local
    return minimum, size, used, rebased


def main():
    code = SOURCE.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    body = indexed_body(code)
    assert valid(body), "two-pass indexed draw / fallback contract broken"
    assert workflow.count("tools/verify_vr_r30_index_rebase_fastpath.py") == 2
    mutations = (
        ("const bool index16 = ibShadow->indexFormat == D3DFMT_INDEX16;",
         "const bool index16 = false;"),
        ("scratch.physical[i] = static_cast<std::uint32_t>(p);",
         "scratch.physical[i] = 0;"),
        ("scratch.indices16.resize(indexCount);", "scratch.indices16.clear();"),
        ("scratch.indices32.resize(indexCount);", "scratch.indices32.clear();"),
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
        ("if (p < 0 || p > UINT_MAX)", "if (false)"),
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
    print(f"PASS R30 indexed XYZRHW two-pass rebase: {cases + 3} model cases, "
          f"{len(mutations)} negative mutations")


if __name__ == "__main__":
    main()
