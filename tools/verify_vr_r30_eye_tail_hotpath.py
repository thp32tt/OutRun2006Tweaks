#!/usr/bin/env python3
"""DX9Ex R30 CPU-projected particles: one composed eye tail, not two per-vertex matrices.

Source-contract and destructive-mutation gate; exact Windows x86 game compilation
runs separately in the DX9Ex Active workflow. HMD frame-time is not asserted.
"""
from pathlib import Path
import math
import random

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
WORKFLOW = ROOT / ".github/workflows/vr-dx9ex-active.yml"


def sections(source: str):
    state = source.split("struct R30XyzrhwState", 1)[1].split(
        "bool R30PrepareXyzrhwState", 1)[0]
    configure = source.split("bool R30ConfigureXyzrhwWorldEffect(", 1)[1].split(
        "UINT R30PrimitiveElementCount(", 1)[0]
    vertices = source.split("bool R30TransformXyzrhwVertices(", 1)[1].split(
        "bool R30TryFusedWorldXyzrhwProjection(", 1)[0]
    stereo = source.split("bool R30TransformXyzrhwStereo(", 1)[1].split(
        "template <typename LeftDraw,", 1)[0]
    return state, configure, vertices, stereo


def verify(source: str):
    state, configure, vertices, stereo = sections(source)
    seed = source.split("bool R30SeedWorldXyzrhwBuffers(", 1)[1].split(
        "bool R30TransformXyzrhwVertices(", 1)[0]
    assert "D3DMATRIX eyeTail[2]{};" in state
    for required in (
        "state.eyeInverse[eye] = R29OwnerInverseRigid(eyePose);",
        "state.eyeProjection[eye] =",
        "state.eyeTail[eye] = R29OwnerMultiplyMatrix(\n"
        "                    state.eyeInverse[eye], state.eyeProjection[eye]);",
        "!R29OwnerMatrixFinite(state.eyeTail[eye])",
    ):
        assert required in configure, f"composed eye-tail initialization lost: {required}"
    assert configure.index("state.eyeProjection[eye] =") < configure.index(
        "state.eyeTail[eye] =") < configure.index(
        "!R29OwnerMatrixFinite(state.eyeTail[eye])")
    for required in (
        "if (state.worldEffect && state.fullWorldReprojection &&",
        "if (rhwPerspectiveFastPath)",
        "if (!restored)",
        "state.inverseBaseProjection.m[row][col]",
        "float clipEye[4]{};",
        "clipEye[col] += restoredView[row] *",
        "state.eyeTail[eye].m[row][col];",
        "clipEye[3] <= 1.0e-6f",
        "const float invEyeW = 1.0f / clipEye[3];",
        "dst[2] = transformedZ;",
        "dst[3] = invEyeW;",
        "else if (!R30SeedWorldXyzrhwBuffers(",
        "state.parallaxPerRhwX[eye] * rhw",
    ):
        assert required in vertices, f"world particle or fallback guard lost: {required}"
    # Dense and unindexed draws must preserve the original full source,
    # while sparse indexed draws copy only referenced contiguous runs before
    # either full or affine per-eye transform. A failed full projection now
    # restores only the previously modified XYZRHW headers; copying the full
    # span a second time would defeat this hot-path optimization.
    for required in (
        "if (usedMask && vertexCount >= 64u)",
        "usedMask->begin() + vertexCount",
        "static_cast<std::size_t>(selectedCount) * 4u <= vertexCount",
        "while (cursor < vertexCount && !(*usedMask)[cursor])",
        "while (cursor < vertexCount && (*usedMask)[cursor])",
        "static_cast<std::size_t>(cursor - begin) * stride",
        "std::memcpy(left.data() + offset,",
        "std::memcpy(right->data() + offset,",
        "if (!sparseCopied)",
        "std::memcpy(left.data(), source, bytes);",
        "std::memcpy(right->data(), source, bytes);",
    ):
        assert required in seed, f"sparse indexed two-eye seed guard lost: {required}"
    assert seed.index("if (!sparseCopied)") < seed.index("return true;")
    assert vertices.index("if (preseeded)") < vertices.index("const float x0")
    assert vertices.index("const float x0") < vertices.index(
        "if (state.worldEffect && state.fullWorldReprojection &&")
    assert vertices.count("else if (!R30SeedWorldXyzrhwBuffers(") == 1
    # A late full-reprojection failure must roll back ALL already-written
    # referenced XYZRHW values before the affine pass reads them. Preserve
    # untouched UV/color bytes and sparse unused gaps, not a second full copy.
    for required in (
        "UINT modifiedVertexEnd = 0;",
        "modifiedVertexEnd = i + 1u;",
        "for (UINT i = 0; i < modifiedVertexEnd; ++i)",
        "if (selected(i))\n                        std::memcpy(outputVertex(i), sourceVertex(i),",
        "4u * sizeof(float));",
    ):
        assert required in vertices, f"reprojection partial rollback lost: {required}"
    assert vertices.index("modifiedVertexEnd = i + 1u;") < vertices.index(
        "if (fullDrawOk && selectedVertices != 0)") < vertices.index(
        "for (UINT i = 0; i < modifiedVertexEnd; ++i)") < vertices.index(
        "const float ndcX = (x - x0)", vertices.index(
            "for (UINT i = 0; i < modifiedVertexEnd; ++i)"))
    assert "if (leftFull &&" in stereo and "if (rightFull &&" in stereo
    assert stereo.index("if (leftFull &&") < stereo.index(
        "state, 0, left, usedMask, false, ignored, false)")
    assert stereo.index("if (rightFull &&") < stereo.index(
        "state, 1, right, usedMask, false, ignored, false)")
    # CPU-projected smoke/skid/decal geometry is constant within a latched
    # pose/projection/scale, while depth evidence and viewport stay per draw.
    assert "thread_local R30XyzrhwWorldGeometryCache R30XyzrhwWorldGeometry{};" in state
    assert "R30InvalidateXyzrhwWorldGeometry();" in source.split(
        "HRESULT __stdcall ResetDestR30", 1)[1].split("float R30HudScaleValue", 1)[0]
    assert "void R30InvalidateXyzrhwWorldGeometry() noexcept" in state
    assert "R30XyzrhwWorldGeometry = {};" in state
    for key in (
        "geometryCache.valid &&",
        "geometryCache.worldScale == worldScale",
        "geometryCache.geometry.stereo.poseSequence == state.stereo.poseSequence",
        "std::memcmp(&geometryCache.geometry.baseProjection,",
        "std::memcmp(geometryCache.geometry.stereo.eyeOffset,",
        "std::memcmp(geometryCache.geometry.stereo.eyeFov,",
        "geometryCache.valid = false;",
        "geometryCache.geometry = state;",
        "geometryCache.valid = true;",
        "state.inverseBaseProjection = previous.inverseBaseProjection;",
        "std::memcpy(state.eyeTail, previous.eyeTail,",
        "std::memcpy(state.parallaxPerRhwX, previous.parallaxPerRhwX,",
        "std::memcpy(state.parallaxPerRhwY, previous.parallaxPerRhwY,",
    ):
        assert key in configure, f"XYZRHW geometry cache guard lost: {key}"
    # A rejected world signature must not reuse cached world geometry.
    assert configure.index("state.rhwDepthEvidence =") < configure.index(
        "if (!state.worldEffect)") < configure.index("geometryCacheHit")
    assert configure.index("geometryCache.valid = false;") < configure.index(
        "R29OwnerInvertMatrix(baseProjection, state.inverseBaseProjection)")
    assert configure.index("!R29OwnerMatrixFinite(state.eyeTail[eye])") < configure.index(
        "geometryCache.valid = true;")
    # No second 4x4 multiplication may remain inside the particle loop.
    assert "float eyeView[4]{};" not in vertices
    assert "state.eyeInverse[eye].m[row][col]" not in vertices
    assert "state.eyeProjection[eye].m[row][col]" not in vertices
    # 00684 adds a separate fused binocular world route in addition to the
    # original independent-eye safety fallback. Each route must retain its
    # own composed eye-tail multiplication; neither may use a raw projection.
    fused = source.split("bool R30TryFusedWorldXyzrhwProjection(", 1)[1].split(
        "bool R30TransformXyzrhwStereo(", 1)[0]
    full = vertices.split(
        "if (state.worldEffect && state.fullWorldReprojection &&", 1)[1].split(
        "if (fullDrawOk && selectedVertices != 0)", 1)[0]
    eye_tail = "state.eyeTail[eye].m[row][col];"
    assert vertices.count(eye_tail) == 1
    assert full.count(eye_tail) == 1
    assert fused.count(eye_tail) == 1
    assert "for (int eye = 0; eye < 2; ++eye)" in fused
    assert "clipEye[3] <= 1.0e-6f" in fused
    assert "if (allValid && referenced != 0)" in fused
    assert "for (UINT i = 0; i < modifiedVertexEnd; ++i)" in fused
    assert full.index("float clipEye[4]{};") < full.index(
        "clipEye[3] <= 1.0e-6f")
    for required in (
        "if (leftFull != rightFull)",
        "state, 0, left, usedMask, false, ignored, false)",
        "state, 1, right, usedMask, false, ignored, false)",
    ):
        assert required in stereo, "bilateral fallback must not be removed"


def multiply_matrix(a, b):
    return [[sum(a[row][k] * b[k][col] for k in range(4))
             for col in range(4)] for row in range(4)]


def multiply_vector(v, m):
    return [sum(v[row] * m[row][col] for row in range(4))
            for col in range(4)]


def math_parity():
    rng = random.Random(644)
    for _ in range(300):
        translation = [rng.uniform(-0.06, 0.06) for _ in range(3)]
        inverse_eye = [
            [1., 0., 0., 0.], [0., 1., 0., 0.],
            [0., 0., 1., 0.], [*translation, 1.]]
        projection = [
            [rng.uniform(0.5, 1.8), 0., 0., 0.],
            [0., rng.uniform(0.5, 1.8), 0., 0.],
            [rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2),
             rng.uniform(0.1, 1.5), rng.choice((-1., 1.))],
            [0., 0., rng.uniform(-0.1, 0.2), 0.]]
        view = [rng.uniform(-8., 8.), rng.uniform(-8., 8.),
                rng.uniform(0.1, 80.), 1.]
        old = multiply_vector(multiply_vector(view, inverse_eye), projection)
        composed = multiply_vector(view, multiply_matrix(inverse_eye, projection))
        for a, b in zip(old, composed):
            assert math.isclose(a, b, rel_tol=1e-11, abs_tol=1e-11), (
                "eye inverse/projection order or floating-point parity changed", a, b)


def sparse_copy_parity():
    """Model indexed-up copy semantics for dense/sparse/empty selections."""
    rng = random.Random(662)
    cases = 0
    for vertices in (1, 63, 64, 65, 128, 1024):
        for stride in (16, 24, 32, 64):
            for coverage in (0., .05, .25, .5, 1.):
                source = bytes(rng.randrange(256) for _ in range(vertices * stride))
                mask = [int(rng.random() < coverage) for _ in range(vertices)]
                sentinel = 173
                out = bytearray([sentinel] * len(source))
                sparse = vertices >= 64 and sum(mask) * 4 <= vertices
                if sparse:
                    cursor = 0
                    while cursor < vertices:
                        while cursor < vertices and not mask[cursor]:
                            cursor += 1
                        begin = cursor
                        while cursor < vertices and mask[cursor]:
                            cursor += 1
                        if begin != cursor:
                            out[begin * stride:cursor * stride] = source[
                                begin * stride:cursor * stride]
                else:
                    out[:] = source
                for i, selected in enumerate(mask):
                    a = out[i * stride:(i + 1) * stride]
                    b = source[i * stride:(i + 1) * stride]
                    assert a == b if selected or not sparse else a == bytes(
                        [sentinel] * stride)
                # Only referenced XYZRHW headers are written by the full
                # reprojector. Model a rejection after 0, half, or all of
                # those writes; selective rollback must equal the legacy
                # re-copy for the affine reader, including sparse gaps.
                selected = [i for i, v in enumerate(mask) if v]
                original_copy = out[:]
                for success_count in (0, len(selected) // 2, len(selected)):
                    changed = out[:]
                    for i in selected[:success_count]:
                        start = i * stride
                        changed[start:start + 16] = bytes([0xA5] * 16)
                    modified_end = selected[success_count - 1] + 1 if success_count else 0
                    for i in range(modified_end):
                        if mask[i]:
                            start = i * stride
                            changed[start:start + 16] = source[start:start + 16]
                    assert changed == original_copy
                cases += 1
    return cases



def verify_fused_origin_hotpath(source: str) -> None:
    """R30 fused per-eye constant terms must be hoisted without altering parity."""
    import struct
    block = source.split("bool R30TryFusedWorldXyzrhwProjection(", 1)[1].split(
        "bool R30TransformXyzrhwStereo(", 1)[0]

    requirements = (
        "const float halfWidth = width * 0.5f;",
        "const float halfHeight = height * 0.5f;",
        "float eyeTailOrigin[2][4]{};",
        "eyeTailOrigin[eye][col] = state.eyeTail[eye].m[3][col];",
        "for (int row = 0; row < 3; ++row)",
        "clipEye[col] += restoredView[row] *",
        "state.eyeTail[eye].m[row][col];",
        "clipEye[col] += eyeTailOrigin[eye][col];",
        "projected[eye][0] = x0 + (fullX + 1.0f) * halfWidth;",
        "projected[eye][1] = y0 + (1.0f - fullY) * halfHeight;",
        "clipEye[3] <= 1.0e-6f",
        "if (allValid && referenced != 0)",
        "for (UINT i = 0; i < modifiedVertexEnd; ++i)",
    )

    def valid(part):
        # The fused path now walks a bounded list of referenced indices when
        # sparse; the origin hoist must precede the visit loop, not the
        # retired full-span vertex loop.
        return (all(term in part for term in requirements)
                and part.index("float eyeTailOrigin[2][4]{};")
                < part.index("for (UINT visit = 0; visit < visitCount; ++visit)")
                and part.index("const float halfWidth = width * 0.5f;")
                < part.index("for (UINT visit = 0; visit < visitCount; ++visit)")
                and part.index("clipEye[col] += eyeTailOrigin[eye][col];")
                < part.index("clipEye[3] <= 1.0e-6f"))
    assert valid(block), "fused binocular constant-term fastpath missing"
    mutants = (
        ("m[3]", "m[2]"),
        ("row < 3", "row < 4"),
        ("clipEye[col] += eyeTailOrigin", "clipEye[col] -= eyeTailOrigin"),
        ("halfWidth = width * 0.5f", "halfWidth = width * 1.0f"),
        ("halfHeight = height * 0.5f", "halfHeight = height * 1.0f"),
        ("(fullX + 1.0f) * halfWidth", "(fullZ + 1.0f) * halfWidth"),
        ("(1.0f - fullY) * halfHeight", "(1.0f - fullZ) * halfHeight"),
    )
    for good, bad in mutants:
        assert good in block, f"mutation fixture missing: {good}"
        assert not valid(block.replace(good, bad, 1)), (
            f"destructive fastpath mutation escaped: {good}")

    f32 = lambda v: struct.unpack("<f", struct.pack("<f", v))[0]
    rng = random.Random(695)
    for _ in range(16000):
        restored = [f32(rng.uniform(-120., 120.)) for _ in range(3)] + [1.0]
        tails = [[[f32(rng.uniform(-4., 4.)) for _ in range(4)]
                  for _ in range(4)] for eye in range(2)]
        for eye in range(2):
            for col in range(4):
                original = f32(0.0)
                for row in range(4):
                    original = f32(original + f32(
                        restored[row] * tails[eye][row][col]))
                optimized = f32(0.0)
                for row in range(3):
                    optimized = f32(optimized + f32(
                        restored[row] * tails[eye][row][col]))
                optimized = f32(optimized + tails[eye][3][col])
                assert original == optimized, "eye-tail float32 parity changed"
        width = f32(rng.choice((320, 640, 1280, 1920, 3440, 4096)))
        height = f32(rng.choice((240, 480, 720, 1080, 1440, 2160)))
        x0 = f32(rng.randint(0, 200))
        y0 = f32(rng.randint(0, 200))
        full_x, full_y = f32(rng.uniform(-1.5, 1.5)), f32(rng.uniform(-1.5, 1.5))
        old_x = f32(x0 + f32(f32(f32(full_x + 1.0) * 0.5) * width))
        new_x = f32(x0 + f32(f32(full_x + 1.0) * f32(width * 0.5)))
        old_y = f32(y0 + f32(f32(f32(1.0 - full_y) * 0.5) * height))
        new_y = f32(y0 + f32(f32(1.0 - full_y) * f32(height * 0.5)))
        assert abs(old_x - new_x) <= .002
        assert abs(old_y - new_y) <= .002
    print(f"PASS fused XYZRHW per-eye origin: {len(mutants)} negative mutations, 16000 float32 two-eye/viewport cases")


def main():
    source = SOURCE.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert workflow.count("tools/verify_vr_r30_eye_tail_hotpath.py") == 2
    verify(source)
    verify_fused_origin_hotpath(source)
    mutations = (
        ("D3DMATRIX eyeTail[2]{};", "D3DMATRIX omitted[2]{};"),
        ("state.eyeInverse[eye], state.eyeProjection[eye]);",
         "state.eyeProjection[eye], state.eyeInverse[eye]);"),
        ("!R29OwnerMatrixFinite(state.eyeTail[eye])", "false"),
        ("clipEye[col] += restoredView[row] *",
         "clipEye[col] += 1.0f *"),
        ("state.eyeTail[eye].m[row][col];", "state.eyeProjection[eye].m[row][col];"),
        ("clipEye[3] <= 1.0e-6f", "false"),
        ("if (!restored)", "if (false)"),
        ("state.inverseBaseProjection.m[row][col]", "0.0f"),
        ("if (leftFull != rightFull)", "if (false)"),
        ("state.parallaxPerRhwX[eye] * rhw", "0.0f"),
        ("modifiedVertexEnd = i + 1u;", "modifiedVertexEnd = 0;"),
        ("for (UINT i = 0; i < modifiedVertexEnd; ++i)",
         "for (UINT i = 0; i < 0; ++i)"),
        ("if (selected(i))\n                        std::memcpy(outputVertex(i), sourceVertex(i),",
         "if (!selected(i))\n                        std::memcpy(outputVertex(i), sourceVertex(i),"),
        ("4u * sizeof(float));", "2u * sizeof(float));"),
        ("if (leftFull &&", "if (false &&"),
        ("if (rightFull &&", "if (false &&"),
    )
    for i, (before, after) in enumerate(mutations, 1):
        assert before in source, f"mutation {i} is ineffective"
        # 00686 introduces a separate affine-only helper with the same
        # parallax expression. Mutate the legacy independent-eye fallback
        # inside R30TransformXyzrhwVertices, not that earlier new helper.
        if before == "state.parallaxPerRhwX[eye] * rhw":
            begin = source.index("bool R30TransformXyzrhwVertices(")
            at = source.index(before, begin)
            altered = source[:at] + after + source[at + len(before):]
        else:
            altered = source.replace(before, after, 1)
        try:
            verify(altered)
        except (AssertionError, ValueError, IndexError):
            continue
        raise AssertionError(f"destructive mutation {i} escaped")
    # Target the second eye-tail multiplication explicitly: replacing only
    # the first site above tests the independent-eye fallback, not the fused
    # world implementation. Guard both routes against independent regression.
    fused_start = source.index("bool R30TryFusedWorldXyzrhwProjection(")
    eye_tail = "state.eyeTail[eye].m[row][col];"
    fused_site = source.index(eye_tail, fused_start)
    for damaged_eye_tail in (
        "state.eyeProjection[eye].m[row][col];",
        "state.eyeInverse[eye].m[row][col];",
    ):
        mutated = (source[:fused_site] + damaged_eye_tail +
                   source[fused_site + len(eye_tail):])
        try:
            verify(mutated)
        except (AssertionError, ValueError, IndexError):
            continue
        raise AssertionError("fused world eye-tail mutation escaped")
    # The fused route must also reject clip-W behind the eye.
    fused_guard = "clipEye[3] <= 1.0e-6f"
    fused_guard_site = source.index(fused_guard, fused_start)
    mutated_guard = (source[:fused_guard_site] + "false" +
                     source[fused_guard_site + len(fused_guard):])
    try:
        verify(mutated_guard)
    except (AssertionError, ValueError, IndexError):
        pass
    else:
        raise AssertionError("fused world clip-W mutation escaped")
    # The Reset callsite precedes the later TLS geometry declaration. Fail
    # any change that drops its correctly forward-declared invalidator.
    reset_bad = source.replace(
        "            R30InvalidateXyzrhwWorldGeometry();",
        "            /* reset invalidation removed */", 1)
    try:
        verify(reset_bad)
    except AssertionError:
        pass
    else:
        raise AssertionError("Reset invalidation mutation escaped")
    geometry_mutations = (
        ("geometryCache.worldScale == worldScale", "true"),
        ("geometryCache.geometry.stereo.poseSequence == state.stereo.poseSequence", "true"),
        ("std::memcmp(&geometryCache.geometry.baseProjection,", "std::memcmp(&state.baseProjection,"),
        ("std::memcmp(geometryCache.geometry.stereo.eyeOffset,", "std::memcmp(state.stereo.eyeOffset,"),
        ("std::memcmp(geometryCache.geometry.stereo.eyeFov,", "std::memcmp(state.stereo.eyeFov,"),
        ("geometryCache.valid = false;", "/* stale geometry allowed */"),
        ("geometryCache.geometry = state;", "/* missing geometry publication */"),
        ("geometryCache.valid = true;", "/* never publish validated geometry */"),
        ("state.inverseBaseProjection = previous.inverseBaseProjection;", "/* stale inverse */"),
        ("std::memcpy(state.eyeTail, previous.eyeTail,", "std::memcpy(state.eyeTail, state.eyeTail,"),
        ("std::memcpy(state.parallaxPerRhwY, previous.parallaxPerRhwY,", "std::memcpy(state.parallaxPerRhwY, state.parallaxPerRhwY,"),
    )
    for i, (before, after) in enumerate(geometry_mutations, 1):
        scope = source.index("bool R30ConfigureXyzrhwWorldEffect(")
        position = source.find(before, scope)
        assert position >= 0, f"geometry mutation {i} missing"
        changed = source[:position] + after + source[position + len(before):]
        try:
            verify(changed)
        except (AssertionError, ValueError, IndexError):
            continue
        raise AssertionError(f"XYZRHW cache destructive mutation {i} escaped")
    assert sparse_copy_parity() == 120
    math_parity()
    print(f"PASS R30 particle stereo eye-tail/geometry cache + partial rollback: {len(mutations) + len(geometry_mutations) + 1} destructive mutations, 120 sparse rollback models, and 300 matrix parity cases")


if __name__ == "__main__":
    main()
