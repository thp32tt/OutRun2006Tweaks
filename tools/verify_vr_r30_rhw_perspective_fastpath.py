#!/usr/bin/env python3
"""Guard actual R30 XYZRHW per-draw RHW basis hoisting and fallback."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
WORKFLOW = ROOT / ".github/workflows/vr-dx9ex-active.yml"


def transform_body(source: str) -> str:
    begin = source.index("        bool R30TransformXyzrhwVertices(")
    end = source.index("        bool R30TransformXyzrhwStereo(", begin)
    return source[begin:end]


def valid(code: str) -> bool:
    try:
        loop = code.index("                for (UINT i = 0; i < vertexCount; ++i)")
        hoist = code.index("            const D3DMATRIX& rhwBase = state.baseProjection;")
        det = code.index("            const float rhwDet =")
        gate = code.index("            const bool rhwPerspectiveFastPath =")
        full = code.index("            if (state.worldEffect && state.fullWorldReprojection &&")
        predicate = code[gate:code.index("            auto selected =", gate)]
        basis = code[det:gate]
        full_body = code[full:code.index("                if (fullDrawOk && selectedVertices != 0)", full)]
        ratios = code[gate:code.index("            auto selected =", gate)]
        return (hoist < det < gate < loop and
                "rhwBase._11 * rhwBase._22 - rhwBase._21 * rhwBase._12" in basis and
                all(x in predicate for x in (
                    "state.worldEffect && state.fullWorldReprojection &&",
                    "allowFullReprojection &&",
                    "std::fabs(rhwBase._14) <= 1.0e-5f",
                    "std::fabs(rhwBase._24) <= 1.0e-5f",
                    "std::fabs(rhwBase._34) > 1.0e-5f",
                    "std::isfinite(rhwDet)",
                    "std::fabs(rhwDet) > 1.0e-6f")) and
                "const float invRhw34 = rhwPerspectiveFastPath" in ratios and
                "? 1.0f / rhwBase._34 : 0.0f;" in ratios and
                "const float invRhwDet = rhwPerspectiveFastPath" in ratios and
                "? 1.0f / rhwDet : 0.0f;" in ratios and
                "const float invDepthSpan = 1.0f / depthSpan;" in ratios and
                "if (rhwPerspectiveFastPath)" in full_body and
                "(clipW - bp._44) * invRhw34;" in full_body and
                full_body.count("* invRhwDet;") == 2 and
                "(screenZ - minZ) * invDepthSpan;" in full_body and
                "std::isfinite(viewZ)" in full_body and
                "std::isfinite(rhsX)" in full_body and
                "std::isfinite(rhsY)" in full_body and
                "if (!restored)" in full_body and
                "state.inverseBaseProjection.m[row][col]" in full_body and
                "if (fullDrawOk && selectedVertices != 0)" in code and
                "else if (!R30SeedWorldXyzrhwBuffers(" in code and
                "if (preseeded)" in code and
                "if (out.size() != bytes)" in code and
                "bool ignored = false;" not in full_body and
                code.count("for (UINT i = 0; i < vertexCount; ++i)") >= 2)
    except ValueError:
        return False



def projected_depth_signature_contract(source: str) -> None:
    """No per-particle divides on the common path; preserve HUD/world guards."""
    import math
    import random
    import struct

    code = source.split("bool R30XyzrhwHasProjectedDepthSignature(", 1)[1].split(
        "bool R30ConfigureXyzrhwWorldEffect(", 1)[0]
    def valid(s: str) -> bool:
        start = s.index("const float projectionDepthScale =")
        loop = s.index("for (UINT i = 0; i < vertexCount && sampled < 512u; ++i)")
        slow = s.index("if (!projectionDepthFast || !std::isfinite(depthDelta) ||")
        return (start < loop < slow
            and "projection._33 / projection._34;" in s[:loop]
            and "projection._43 - projection._44 * projectionDepthScale;" in s[:loop]
            and "const float inverseDepthSpan = 1.0f / depthSpan;" in s[:loop]
            and "std::isfinite(projectionDepthScale)" in s[:loop]
            and "std::isfinite(projectionDepthOffset)" in s[:loop]
            and "std::isfinite(inverseDepthSpan)" in s[:loop]
            and "projectionDepthOffset * rhw;" in s[loop:slow]
            and "(z - state.viewport.MinZ) * inverseDepthSpan;" in s[loop:slow]
            and "std::fabs(depthDelta - 0.10f) <= 0.0005f" in s[slow:]
            and "const float clipW = 1.0f / rhw;" in s[slow:]
            and "expectedNdcZ = clipZ / clipW;" in s[slow:]
            and "(z - state.viewport.MinZ) / depthSpan;" in s[slow:]
            and "std::fabs(rhw - 1.0f) > 0.02f && depthDelta <= 0.10f" in s
            and "sampled >= 3u && valid >= 3u && valid * 2u >= sampled" in s
            and "projected * 4u >= valid * 3u" in s
            and "if (usedMask &&" in s)
    assert valid(code), "R30 projected world/particle depth fastpath contract lost"
    mutations = (
        ("projection._33 / projection._34;", "projection._33 / projection._44;"),
        ("projection._43 - projection._44 * projectionDepthScale;",
         "projection._43 + projection._44 * projectionDepthScale;"),
        ("projectionDepthOffset * rhw;", "projectionDepthOffset / rhw;"),
        ("(z - state.viewport.MinZ) * inverseDepthSpan;",
         "(z - state.viewport.MinZ) / inverseDepthSpan;"),
        ("std::isfinite(projectionDepthScale)", "true"),
        ("std::isfinite(projectionDepthOffset)", "true"),
        ("std::isfinite(inverseDepthSpan)", "true"),
        ("std::fabs(depthDelta - 0.10f) <= 0.0005f", "false"),
        ("expectedNdcZ = clipZ / clipW;", "expectedNdcZ = clipZ;"),
        ("std::fabs(rhw - 1.0f) > 0.02f && depthDelta <= 0.10f",
         "depthDelta <= 0.10f"),
        ("projected * 4u >= valid * 3u", "projected >= 0u"),
    )
    for number, (needle, replacement) in enumerate(mutations, 1):
        assert needle in code, f"depth signature mutation {number} absent"
        assert not valid(code.replace(needle, replacement, 1)), (
            f"depth signature mutation {number} escaped")
    f32 = lambda x: struct.unpack("<f", struct.pack("<f", x))[0]
    rng = random.Random(669)
    for _ in range(12000):
        p34 = f32(rng.choice((-1.0, 1.0)))
        p33 = f32(rng.uniform(0.8, 1.2))
        p43 = f32(rng.uniform(-2.0, 2.0))
        p44 = f32(rng.uniform(-0.15, 0.15))
        rhw = f32(rng.uniform(0.001, 10.0))
        clip_w = f32(1.0 / rhw)
        view_z = f32(f32(clip_w - p44) / p34)
        clip_z = f32(f32(view_z * p33) + p43)
        old_expected = f32(clip_z / clip_w)
        coeff = f32(p33 / p34)
        slope = f32(p43 - f32(p44 * coeff))
        fast_expected = f32(coeff + f32(slope * rhw))
        assert math.isfinite(old_expected) and math.isfinite(fast_expected)
        assert abs(old_expected - fast_expected) <= (
            0.00005 * max(1.0, abs(old_expected)))
    print(f"PASS R30 projected-depth hotpath, {len(mutations)} destructive mutations, 12000 float32 cases")


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert workflow.count("tools/verify_vr_r30_rhw_perspective_fastpath.py") == 2
    code = transform_body(source)
    projected_depth_signature_contract(source)
    assert valid(code), "R30 RHW basis must be computed once before vertex loops"
    mutations = (
        ("state.worldEffect && state.fullWorldReprojection &&",
         "true &&"),
        ("allowFullReprojection &&", "true &&"),
        ("std::fabs(rhwBase._14) <= 1.0e-5f", "true"),
        ("std::fabs(rhwBase._24) <= 1.0e-5f", "true"),
        ("std::fabs(rhwBase._34) > 1.0e-5f", "true"),
        ("std::isfinite(rhwDet)", "true"),
        ("std::fabs(rhwDet) > 1.0e-6f", "true"),
        ("if (rhwPerspectiveFastPath)", "if (true)"),
        ("(rhsX * bp._22 -\n                                 bp._21 * rhsY) * invRhwDet;",
         "(rhsX * bp._22 -\n                                 bp._21 * rhsY) / 1.0f;"),
        ("(clipW - bp._44) * invRhw34;",
         "(clipW - bp._44) / bp._34;"),
        ("(screenZ - minZ) * invDepthSpan;",
         "(screenZ - minZ) / depthSpan;"),
        ("? 1.0f / rhwBase._34 : 0.0f;", "? 1.0f;"),
        ("? 1.0f / rhwDet : 0.0f;", "? 1.0f;"),
        ("const float invDepthSpan = 1.0f / depthSpan;",
         "const float invDepthSpan = 1.0f;"),
        ("state.inverseBaseProjection.m[row][col]", "0.0f"),
        ("if (!restored)", "if (false)"),
        ("const D3DMATRIX& rhwBase = state.baseProjection;", "// removed"),
    )
    for i, (before, after) in enumerate(mutations, 1):
        assert before in code, f"mutation {i} target absent"
        damaged = code.replace(before, after, 1)
        assert damaged != code and not valid(damaged), f"mutation {i} escaped"
    # The full-matrix eye projection and affine bilateral fallback remain intact.
    stereo = source[source.index("        bool R30TransformXyzrhwStereo("):
                    source.index("        template <typename LeftDraw,", source.index(
                        "        bool R30TransformXyzrhwStereo("))]
    for keep in ("if (leftFull != rightFull)", "state, 0, left, usedMask, false, ignored, false)",
                 "state, 1, right, usedMask, false, ignored, false)"):
        assert keep in stereo, "bilateral fallback altered"
    print("PASS R30 per-draw RHW perspective hotpath; 17 destructive mutations")


if __name__ == "__main__":
    main()
