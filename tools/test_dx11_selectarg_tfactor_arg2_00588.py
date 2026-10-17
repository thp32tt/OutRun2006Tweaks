#!/usr/bin/env python3
"""00588: live SELECTARG2 alpha factor from D3D9 state into native D3D11 Draw."""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"

def connected(s: str) -> bool:
    try:
        gate = s.split("bool supported_game_state(", 1)[1].split("bool translate_vertices(", 1)[0]
        draw = s.split("bool submit(", 1)[1].split("void observe(", 1)[0]
        pipe = s.split("bool ensure_pipeline(", 1)[1].split("bool supported_game_state(", 1)[0]
    except IndexError:
        return False
    required_gate = (
        "GetTextureStageState(0, D3DTSS_ALPHAARG2, &alphaArg2)",
        "GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)",
        "capture.blendFactorAlphaValue = static_cast<float>((textureFactor >> 24u) & 0xffu) / 255.0f;",
        "selectTextureTfactorArg2Alpha || selectDiffuseTfactorArg2Alpha ||",
        "selectDiffuseTfactorAlpha || selectDiffuseTfactorArg2Alpha ||",
        "nextColorOp != D3DTOP_DISABLE",
        "resultArg != D3DTA_CURRENT",
    )
    if not all(token in gate for token in required_gate):
        return False
    if gate.count("!selectTextureTfactorArg2Alpha && !selectDiffuseTfactorArg2Alpha") != 3:
        return False
    if "(((alphaNeedsDiffuse && !alphaArg2Diffuse) && !alphaArg2UnusedOnSelectArg1) && !selectTextureTfactorArg2Alpha && !selectDiffuseTfactorArg2Alpha &&" not in gate:
        return False
    if not all(token in draw for token in (
        "static_cast<float>(output.alphaFunc), capture.blendFactorAlphaValue",
        "ctx->PSSetConstantBuffers(0, 1, &alphaBuffer);",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )):
        return False
    for mode, colorop in (("Texture", "SELECTARG1"), ("Diffuse", "SELECTARG2")):
        name = "select" + mode + "TfactorArg2Alpha"
        ps = "select" + mode + "TfactorAlphaPs"
        shader = "PSTextureSelect" + mode + "TfactorAlpha"
        predicate = ("const bool " + name + " = op == D3DTOP_" + colorop + " &&\n"
                     "            alphaOp == D3DTOP_SELECTARG2 && alphaArg2 == D3DTA_TFACTOR;")
        if predicate not in gate or "capture." + name + " = " + name + ";" not in gate:
            return False
        if "bool " + name + " = false;" not in s:
            return False
        if "capture." + name + " ? s." + ps + ".Get() :" not in draw:
            return False
        legacy = "selectTextureDiffuseAlpha" if mode == "Texture" else "selectDiffuseDiffuseAlpha"
        if draw.index("capture." + name + " ? s." + ps + ".Get() :") > draw.index("capture." + legacy + " ?"):
            return False
        if 'compile("' + shader + '", "ps_4_0",' not in pipe:
            return False
        if "s." + ps + ".GetAddressOf()" not in pipe:
            return False
    return 'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"' in s

def admitted(colorop: str, alphaop: str, alphaarg1: str, alphaarg2: str) -> bool:
    return colorop in ("SELECTARG1", "SELECTARG2") and alphaop == "SELECTARG2" and alphaarg2 == "TFACTOR"

def main() -> None:
    s = SOURCE.read_text(encoding="utf-8")
    assert connected(s), "live ALPHAARG2/TFACTOR native Draw wiring missing"
    mutations = []
    for mode, colorop in (("Texture", "SELECTARG1"), ("Diffuse", "SELECTARG2")):
        name = "select" + mode + "TfactorArg2Alpha"
        ps = "select" + mode + "TfactorAlphaPs"
        mutations += [
            ("const bool " + name + " = op == D3DTOP_" + colorop + " &&",
             "const bool " + name + " = op == D3DTOP_DISABLE &&"),
            ("capture." + name + " = " + name + ";", "capture." + name + " = false;"),
            ("capture." + name + " ? s." + ps + ".Get() :", "capture." + name + " ? nullptr :"),
            ("bool " + name + " = false;", "bool unused" + mode + " = false;"),
        ]
    mutations += [
        ("alphaOp == D3DTOP_SELECTARG2 && alphaArg2 == D3DTA_TFACTOR;",
         "alphaOp == D3DTOP_SELECTARG2 && alphaArg2 == D3DTA_TEXTURE;"),
        ("selectTextureTfactorArg2Alpha || selectDiffuseTfactorArg2Alpha ||",
         "selectTextureTfactorArg2Alpha || false ||"),
        ("!selectTextureTfactorArg2Alpha && !selectDiffuseTfactorArg2Alpha",
         "!selectTextureTfactorArg2Alpha || !selectDiffuseTfactorArg2Alpha"),
        ("selectDiffuseTfactorAlpha || selectDiffuseTfactorArg2Alpha ||",
         "selectDiffuseTfactorAlpha || false ||"),
        ("GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)",
         "GetRenderState(D3DRS_ALPHAREF, &textureFactor)"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "ctx->DrawIndexed(0, 0, 0);"),
        ("ctx->PSSetConstantBuffers(0, 1, &alphaBuffer);",
         "ctx->PSSetConstantBuffers(0, 0, &alphaBuffer);"),
        ("(((alphaNeedsDiffuse && !alphaArg2Diffuse) && !alphaArg2UnusedOnSelectArg1) && !selectTextureTfactorArg2Alpha && !selectDiffuseTfactorArg2Alpha &&",
         "(alphaNeedsDiffuse && !alphaArg2Diffuse)"),
        ("capture.selectDiffuseTfactorArg2Alpha ? s.selectDiffuseTfactorAlphaPs.Get() :\n                      capture.selectDiffuseDiffuseAlpha",
         "capture.selectDiffuseDiffuseAlpha ? s.ps.Get() :\n                      capture.selectDiffuseTfactorArg2Alpha"),
        ("capture.selectTextureTfactorArg2Alpha ? s.selectTextureTfactorAlphaPs.Get() :\n                      capture.selectTextureDiffuseAlpha",
         "capture.selectTextureDiffuseAlpha ? s.selectTextureDiffuseAlphaPs.Get() :\n                      capture.selectTextureTfactorArg2Alpha"),
    ]
    for old, new in mutations:
        assert old in s, old
        # 00635 added a separate complemented-factor read in this same
        # supported_game_state gate. Sever every active factor source here.
        mutant = s.replace(old, new) if old == "GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)" else s.replace(old, new, 1)
        assert not connected(mutant), old
    for mode in ("SELECTARG1", "SELECTARG2"):
        for alpha_byte in range(256):
            assert (((alpha_byte << 24) & 0xFF000000) >> 24) / 255.0 == alpha_byte / 255.0
            for ignored_arg1 in ("TEXTURE", "DIFFUSE", "TFACTOR"):
                assert admitted(mode, "SELECTARG2", ignored_arg1, "TFACTOR")
                assert not admitted(mode, "SELECTARG1", ignored_arg1, "TFACTOR")
                assert not admitted(mode, "SELECTARG2", ignored_arg1, "TEXTURE")
    print("00588 PASS: 18 negative mutations, 512 factor byte cases, operand+shader-priority regression; runtime UNTESTED")

if __name__ == "__main__":
    main()
