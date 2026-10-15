#!/usr/bin/env python3
"""World XYZRHW indexed stereo seed: one sparse span walk for both eyes.

Models original independent eye seeding against fused scratch pre-seeding,
including sparse holes and the single-eye affine fallback. No Quest3 claim.
"""
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(
    encoding="utf-8")


def contract(source):
    begin = source.find("bool R30SeedWorldXyzrhwBuffers(")
    end = source.find("bool R30TransformXyzrhwVertices(", begin)
    stereo = source.find("bool R30TransformXyzrhwStereo(")
    fallback = source.find("if (leftFull != rightFull)", stereo)
    final = source.find("return true;", fallback)
    if min(begin, end, stereo, fallback, final) < 0:
        return False
    seed = source[begin:end]
    body = source[end:stereo]
    caller = source[stereo:final]
    required_seed = (
        "left.resize(bytes);",
        "if (right)",
        "right->resize(bytes);",
        "usedMask->size() < vertexCount",
        "vertexCount >= 64u",
        "std::count_if(",
        "UINT knownUsedCount = UINT_MAX",
        "knownUsedCount <= vertexCount",
        "static_cast<std::size_t>(knownUsedCount)",
        "selectedCount) * 4u <= vertexCount",
        "std::memcpy(left.data() + offset,",
        "std::memcpy(right->data() + offset,",
        "std::memcpy(left.data(), source, bytes);",
        "std::memcpy(right->data(), source, bytes);",
    )
    required_caller = (
        "left, &right,\n                    usedMask, knownUsedCount, touched))",
        "state, 0, left, usedMask, true, leftFull, true)",
        "state, 1, right, usedMask, true, rightFull, true)",
        "state, 0, left, usedMask, false, ignored, false)",
        "state, 1, right, usedMask, false, ignored, false)",
    )
    return (all(x in seed for x in required_seed)
            and all(x in caller for x in required_caller)
            and "if (preseeded)" in body
            and "if (out.size() != bytes)" in body
            and "out, nullptr, usedMask)" in body
            and "std::count_if(" not in body
            and caller.index("left, &right,\n                    usedMask, knownUsedCount, touched))")
            < caller.index("bool leftFull = false;")
            and caller.index("bool leftFull = false;") < fallback)


assert contract(SOURCE), "world indexed two-eye seed + fallback contract lost"
mutations = [
    ("no shared seed", "left, &right,\n                    usedMask, knownUsedCount, touched))",
     "left, nullptr,\n                    usedMask, knownUsedCount, touched))"),
    ("no right sparse copy", "std::memcpy(right->data() + offset,",
     "std::memcpy(left.data() + offset,"),
    ("no right dense copy", "std::memcpy(right->data(), source, bytes);",
     "std::memcpy(left.data(), source, bytes);"),
    ("no sparse guard", "selectedCount) * 4u <= vertexCount", "false"),
    ("no fallback re-seed", "state, 0, left, usedMask, false, ignored, false)",
     "state, 0, left, usedMask, false, ignored, true)"),
    ("no right fallback", "state, 1, right, usedMask, false, ignored, false)",
     "state, 1, right, usedMask, false, ignored, true)"),
    ("invalid buffer protection", "if (out.size() != bytes)", "if (false)"),
    ("no bounds", "usedMask && usedMask->size() < vertexCount))",
     "usedMask && usedMask->size() < 0))"),
]
for name, before, after in mutations:
    # The sparse density rule is also used by the separate ScreenHud path.
    # Mutate this feature's producer, not the unrelated HUD implementation.
    if name in ("no shared seed", "no fallback re-seed",
                "no right fallback", "invalid buffer protection"):
        assert SOURCE.count(before) == 1, (name, "fixture")
        damaged = SOURCE.replace(before, after, 1)
    else:
        start = SOURCE.index("bool R30SeedWorldXyzrhwBuffers(")
        end = SOURCE.index("bool R30TransformXyzrhwVertices(", start)
        section = SOURCE[start:end]
        assert section.count(before) == 1, (name, "seed fixture")
        damaged = (SOURCE[:start] + section.replace(before, after, 1)
                   + SOURCE[end:])
    assert not contract(damaged), (name, "escaped destructive mutation")


def seed(src, stride, mask, left, right):
    count = len(src) // stride
    sparse = mask is not None and count >= 64 and sum(mask) * 4 <= count
    if sparse:
        for i in range(count):
            if mask[i]:
                a, b = i * stride, (i + 1) * stride
                left[a:b] = src[a:b]
                if right is not None:
                    right[a:b] = src[a:b]
    else:
        left[:] = src
        if right is not None:
            right[:] = src


rng = random.Random(674)
cases = 0
for count in (1, 2, 8, 63, 64, 65, 127, 512, 4096):
    for density in (0, 1, 2, 24, 25, 26, 50, 75, 100):
        for _ in range(25):
            stride = rng.choice((16, 20, 32, 44, 64))
            src = bytearray(rng.randbytes(count * stride))
            mask = ([rng.randrange(100) < density for i in range(count)]
                    if rng.randrange(2) else None)
            poison = rng.randbytes(count * stride)
            old_left, old_right = bytearray(poison), bytearray(poison)
            new_left, new_right = bytearray(poison), bytearray(poison)
            seed(src, stride, mask, old_left, None)
            seed(src, stride, mask, old_right, None)
            seed(src, stride, mask, new_left, new_right)
            assert (old_left, old_right) == (new_left, new_right)
            # Simulate one successful full-reprojection eye requiring
            # source restoration; the other eye remains on affine fallback.
            # Full reprojection writes only XYZRHW (16 bytes) for
            # referenced vertices. Unreferenced sparse holes are not read
            # by indexed UP draws and must retain their previous bytes.
            for i in range(count):
                if mask is None or mask[i]:
                    a = i * stride
                    new_left[a:a + 16] = bytes([0xA5]) * 16
            seed(src, stride, mask, new_left, None)
            assert new_left == old_left and new_right == old_right
            cases += 1
print(f"PASS world indexed XYZRHW dual-eye seed: {cases} "
      f"sparse/dense/fallback model cases and {len(mutations)} negative mutations")
