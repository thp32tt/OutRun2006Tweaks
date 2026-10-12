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
        "bool R30TransformXyzrhwStereo(", 1)[0]
    stereo = source.split("bool R30TransformXyzrhwStereo(", 1)[1].split(
        "template <typename LeftDraw,", 1)[0]
    return state, configure, vertices, stereo


def verify(source: str):
    state, configure, vertices, stereo = sections(source)
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
        "std::memcpy(out.data(), source, bytes);",
        "state.parallaxPerRhwX[eye] * rhw",
    ):
        assert required in vertices, f"world particle or fallback guard lost: {required}"
    # CPU-projected smoke/skid/decal geometry is constant within a latched
    # pose/projection/scale, while depth evidence and viewport stay per draw.
    assert "thread_local R30XyzrhwWorldGeometryCache R30XyzrhwWorldGeometry{};" in state
    assert "R30XyzrhwWorldGeometry = {};" in source.split(
        "HRESULT __stdcall ResetDestR30", 1)[1].split("float R30HudScaleValue", 1)[0]
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
    assert vertices.count("state.eyeTail[eye].m[row][col];") == 1
    full = vertices.split(
        "if (state.worldEffect && state.fullWorldReprojection &&", 1)[1].split(
        "if (fullDrawOk && selectedVertices != 0)", 1)[0]
    assert "state.eyeTail[eye].m[row][col];" in full
    assert full.index("float clipEye[4]{};") < full.index(
        "clipEye[3] <= 1.0e-6f")
    for required in (
        "if (leftFull != rightFull)",
        "state, 0, left, usedMask, false, ignored)",
        "state, 1, right, usedMask, false, ignored)",
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


def main():
    source = SOURCE.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert workflow.count("tools/verify_vr_r30_eye_tail_hotpath.py") == 2
    verify(source)
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
    )
    for i, (before, after) in enumerate(mutations, 1):
        assert before in source, f"mutation {i} is ineffective"
        altered = source.replace(before, after, 1)
        try:
            verify(altered)
        except (AssertionError, ValueError, IndexError):
            continue
        raise AssertionError(f"destructive mutation {i} escaped")
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
    math_parity()
    print(f"PASS R30 particle stereo composed eye-tail/geometry cache: {len(mutations) + len(geometry_mutations)} destructive mutations and 300 matrix parity cases")


if __name__ == "__main__":
    main()
