#!/usr/bin/env python3
"""00595: live stage0 D3D9 COUNT2 texture UV matrix to D3D11 Draw."""
from pathlib import Path
import math

FILE = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"

def linked(s):
    try:
        capture = s.split("struct TextureCapture {",1)[1].split("struct OutputCapture {",1)[0]
        gate = s.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
        vertex = s.split("bool translate_vertices(",1)[1].split("bool mirror_texture(",1)[0]
        draw = s.split("bool submit(",1)[1].split("void observe(",1)[0]
    except IndexError:
        return False
    return all(x in capture for x in ("bool transformUv = false;", "D3DMATRIX uvTransform{};")) and all(x in gate for x in (
        "transformFlags == D3DTTFF_COUNT2",
        "FAILED(game->GetTransform(D3DTS_TEXTURE0, &uvTransform))",
        "transformFlags != D3DTTFF_DISABLE && transformFlags != D3DTTFF_COUNT2",
        "coordIndex >= layout.texcoordCount",
        "capture.transformUv = transformUv;",
        "if (transformUv) capture.uvTransform = uvTransform;",
    )) and all(x in vertex for x in (
        "game_fvf_select_uv(decoded, layout, capture.coordIndex, output[i].uv)",
        "if (capture.enabled && capture.transformUv)",
        "const float u = output[i].uv[0], v = output[i].uv[1];",
        "const auto& m = capture.uvTransform;",
        "const float texU = u * m._11 + v * m._21 + m._31;",
        "const float texV = u * m._12 + v * m._22 + m._32;",
        "if (!std::isfinite(texU) || !std::isfinite(texV)) return false;",
        "output[i].uv[0] = texU;", "output[i].uv[1] = texV;",
    )) and all(x in draw for x in (
        "mirror_texture(dev, capture, sampledView, sampledSampler)",
        "ctx->PSSetSamplers(0, 1, &boundSampler);",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )) and "return optedIn;" in s and "void before_game_present(" in s

def uv(u, v, m):
    return u*m[0]+v*m[2]+m[4], u*m[1]+v*m[3]+m[5]

def main():
    s = FILE.read_text(encoding="utf8")
    assert linked(s), "live texture matrix missing from native Draw"
    mutants = [
        ("bool transformUv = false;", "bool badUv = false;"),
        ("D3DMATRIX uvTransform{};", "D3DMATRIX wrongMatrix{};"),
        ("transformFlags == D3DTTFF_COUNT2", "transformFlags == D3DTTFF_COUNT3"),
        ("FAILED(game->GetTransform(D3DTS_TEXTURE0, &uvTransform))", "FAILED(game->GetTransform(D3DTS_WORLD, &uvTransform))"),
        ("transformFlags != D3DTTFF_DISABLE && transformFlags != D3DTTFF_COUNT2", "transformFlags != D3DTTFF_DISABLE && transformFlags != D3DTTFF_COUNT3"),
        ("coordIndex >= layout.texcoordCount", "coordIndex > layout.texcoordCount"),
        ("capture.transformUv = transformUv;", "capture.transformUv = false;"),
        ("if (transformUv) capture.uvTransform = uvTransform;", "if (false) capture.uvTransform = uvTransform;"),
        ("if (capture.enabled && capture.transformUv)", "if (false && capture.transformUv)"),
        ("const float texU = u * m._11 + v * m._21 + m._31;", "const float texU = u * m._11 + v * m._21 + m._41;"),
        ("const float texV = u * m._12 + v * m._22 + m._32;", "const float texV = u * m._12 + v * m._22 + m._42;"),
        ("if (!std::isfinite(texU) || !std::isfinite(texV)) return false;", "if (false) return false;"),
        ("output[i].uv[0] = texU;", "output[i].uv[0] = u;"),
        ("output[i].uv[1] = texV;", "output[i].uv[1] = v;"),
        ("ctx->PSSetSamplers(0, 1, &boundSampler);", "ctx->PSSetSamplers(0, 0, &boundSampler);"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "ctx->DrawIndexed(0, 0, 0);"),
        ("ctx->Draw(static_cast<UINT>(vertices.size()), 0);", "ctx->Draw(0, 0);"),
    ]
    for before, after in mutants:
        assert before in s, before
        assert not linked(s.replace(before, after, 1)), before
    n = 0
    for u in (-2,-.25,0,.5,1,2.25,4):
        for v in (-3,0,.125,1,5):
            for sc in (0,.5,1,2):
                for tx in (-2,0,1.25):
                    for ty in (-.75,0,3):
                        a,b=uv(u,v,(sc,0,0,sc,tx,ty))
                        assert math.isclose(a, u*sc+tx, abs_tol=1e-12)
                        assert math.isclose(b, v*sc+ty, abs_tol=1e-12)
                        n += 1
    assert uv(2,3,(0,-1,1,0,7,8)) == (10,6)
    assert math.isnan(uv(1,1,(math.nan,0,0,1,0,0))[0])
    print(f"00595 PASS: {len(mutants)} negative mutations, {n} matrix UV cases; HMD UNTESTED")

if __name__ == "__main__":
    main()
