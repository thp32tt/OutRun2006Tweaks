#!/usr/bin/env python3
"""00616 stage0 CURRENT-alpha native Draw linkage and failure mutations."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp"
HEADER = ROOT / "src/vr/d3d11/live_game_stage0_blend.hpp"
PROBE = ROOT / "tools/dx11_stage0_current_alpha_probe.cpp"


def linked(bridge: str, header: str, probe: str) -> bool:
    required_bridge = (
        '#include "live_game_stage0_blend.hpp"',
        "kGameStage0BlendCurrentAlpha == D3DTOP_BLENDCURRENTALPHA",
        "kGameStage0BlendDiffuseAlpha == D3DTOP_BLENDDIFFUSEALPHA",
        "layout.hasDiffuse && resultArg == D3DTA_CURRENT;",
        "stage1Result != D3DTA_CURRENT || stage2Op != D3DTOP_DISABLE",
        "resultArg == D3DTA_CURRENT;",
        "op = canonical_game_stage0_blend_alpha_op(op, stage0CurrentIsDiffuse);",
        "alphaOp = canonical_game_stage0_pm_alpha_op(\n            op, alphaOp, stage0CurrentIsDiffuse);",
        "const bool blendDiffuseAlpha = op == D3DTOP_BLENDDIFFUSEALPHA",
        "capture.blendDiffuseAlpha ? s.blendDiffuseAlphaPs.Get()",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )
    required_header = (
        "kGameStage0BlendDiffuseAlpha = 12u;",
        "kGameStage0BlendCurrentAlpha = 16u;",
        "return currentIsVertexDiffuse && op == kGameStage0BlendCurrentAlpha",
    )
    required_probe = (
        "#include <initializer_list>",
        "static_assert(canonical_game_stage0_blend_alpha_op(16u, true) == 12u);",
        "static_assert(canonical_game_stage0_blend_alpha_op(16u, false) == 16u);",
        "assert(canonical_game_stage0_blend_alpha_op(rgb, false) == rgb);",
        "assert(canonical_game_stage0_blend_alpha_op(alpha, false) == alpha);",
    )
    return (all(x in bridge for x in required_bridge) and
            all(x in header for x in required_header) and
            all(x in probe for x in required_probe) and
            bridge.index("op = canonical_game_stage0_blend_alpha_op") <
            bridge.index("const bool blendDiffuseAlpha = op =="))


def main() -> None:
    bridge = BRIDGE.read_text(encoding="utf-8")
    header = HEADER.read_text(encoding="utf-8")
    probe = PROBE.read_text(encoding="utf-8")
    assert linked(bridge, header, probe)
    for src, old, wrong in (
        ("bridge",
         "op = canonical_game_stage0_blend_alpha_op(op, stage0CurrentIsDiffuse);",
         "op = canonical_game_stage0_blend_alpha_op(op, false);"),
        ("bridge",
         "alphaOp = canonical_game_stage0_pm_alpha_op(\n            op, alphaOp, stage0CurrentIsDiffuse);",
         "alphaOp = canonical_game_stage0_pm_alpha_op(\n            op, alphaOp, false);"),
        ("bridge",
         "layout.hasDiffuse && resultArg == D3DTA_CURRENT;",
         "resultArg == D3DTA_CURRENT;"),
        ("bridge",
         "stage1Result != D3DTA_CURRENT || stage2Op != D3DTOP_DISABLE",
         "stage1Result != D3DTA_CURRENT"),
        ("header",
         "return currentIsVertexDiffuse && op == kGameStage0BlendCurrentAlpha",
         "return op == kGameStage0BlendCurrentAlpha"),
        ("probe",
         "static_assert(canonical_game_stage0_blend_alpha_op(16u, false) == 16u);",
         "static_assert(canonical_game_stage0_blend_alpha_op(16u, false) == 12u);"),
    ):
        originals = {"bridge": bridge, "header": header, "probe": probe}
        mutant = originals[src].replace(old, wrong, 1)
        assert mutant != originals[src], f"missing mutation anchor: {old}"
        originals[src] = mutant
        assert not linked(originals["bridge"], originals["header"], originals["probe"]), (
            f"mutation escaped stage0 native safety: {old}"
        )
    for op in (12, 13, 16, 4):
        for current_is_diffuse in (True, False):
            canonical = 12 if op == 16 and current_is_diffuse else op
            if op == 16:
                assert (canonical == 12) is current_is_diffuse
            else:
                assert canonical == op
    print("DX11 live stage0 CURRENT-alpha -> DIFFUSE-alpha native Draw regression PASS (static only)")


if __name__ == "__main__":
    main()
