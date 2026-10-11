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
                "if (rhwPerspectiveFastPath)" in full_body and
                full_body.count("/ rhwDet;") == 2 and
                "std::isfinite(viewZ)" in full_body and
                "std::isfinite(rhsX)" in full_body and
                "std::isfinite(rhsY)" in full_body and
                "if (!restored)" in full_body and
                "state.inverseBaseProjection.m[row][col]" in full_body and
                "if (fullDrawOk && selectedVertices != 0)" in code and
                "std::memcpy(out.data(), source, bytes);" in code and
                "bool ignored = false;" not in full_body and
                code.count("for (UINT i = 0; i < vertexCount; ++i)") >= 2)
    except ValueError:
        return False


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert workflow.count("tools/verify_vr_r30_rhw_perspective_fastpath.py") == 2
    code = transform_body(source)
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
        ("(rhsX * bp._22 -\n                                 bp._21 * rhsY) / rhwDet;",
         "(rhsX * bp._22 -\n                                 bp._21 * rhsY) / 1.0f;"),
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
    for keep in ("if (leftFull != rightFull)", "state, 0, left, usedMask, false, ignored)",
                 "state, 1, right, usedMask, false, ignored)"):
        assert keep in stereo, "bilateral fallback altered"
    print("PASS R30 per-draw RHW perspective hotpath; 12 destructive mutations")


if __name__ == "__main__":
    main()
