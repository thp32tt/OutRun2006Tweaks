#!/usr/bin/env python3
"""00600: game-authored D3D9 alpha-test state through live native DX11 Draw."""
from pathlib import Path
import operator
import re

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"

# D3DCMPFUNC numeric values: NEVER=1, LESS=2, EQUAL=3, LESSEQUAL=4,
# GREATER=5, NOTEQUAL=6, GREATEREQUAL=7, ALWAYS=8.
HLSL_CASES = (
    "alphaParams.z == 2.0f && value < alphaParams.y",
    "alphaParams.z == 3.0f && value == alphaParams.y",
    "alphaParams.z == 4.0f && value <= alphaParams.y",
    "alphaParams.z == 5.0f && value > alphaParams.y",
    "alphaParams.z == 6.0f && value != alphaParams.y",
    "alphaParams.z == 7.0f && value >= alphaParams.y",
    "alphaParams.z == 8.0f",
)
GUARDS = (
    "func != D3DCMP_NEVER", "func != D3DCMP_LESS",
    "func != D3DCMP_EQUAL", "func != D3DCMP_LESSEQUAL",
    "func != D3DCMP_GREATER", "func != D3DCMP_NOTEQUAL",
    "func != D3DCMP_GREATEREQUAL", "func != D3DCMP_ALWAYS",
)

def section(s, start, end):
    a = s.find(start)
    b = s.find(end, a + len(start))
    return s[a:b] if a >= 0 and b > a else ""

def linked(s):
    shader = section(s, 'constexpr char kShader[] = R"(', ')";')
    producer = section(s, "bool supported_game_state(", "bool translate_vertices(")
    consumer = section(s, "bool submit(", "void observe(")
    observer = section(s, "void observe(", "} // namespace")
    return (
        len(shader.encode("utf-8")) < 16380  # MSVC C2026 raw string limit
        and all(shader.count(case) == 1 for case in HLSL_CASES)
        and 'float value = floor(saturate(alpha) * 255.0f + 0.5f);' in shader
        and "clip(pass ? 1.0f : -1.0f);" in shader
        and "alphaParams.x > 0.5f" in shader
        and "alphaParams.z == 1.0f" not in shader  # NEVER never passes
        and all(len(re.findall(re.escape(case) + r"\b", producer)) == 1 for case in GUARDS)
        and "GetRenderState(D3DRS_ALPHAFUNC, &func)" in producer
        and "GetRenderState(D3DRS_ALPHAREF, &reference)" in producer
        and "reference > 255u" in producer
        and "output.alphaFunc = static_cast<D3DCMPFUNC>(func);" in producer
        and "output.alphaRef = reference;" in producer
        and "output.alphaTest = true;" in producer
        and "static_cast<float>(output.alphaRef)" in consumer
        and "static_cast<float>(output.alphaFunc)" in consumer
        and "ctx->PSSetConstantBuffers(0, 1, &alphaBuffer);" in consumer
        and "ctx->DrawIndexed(indexCount, 0, 0);" in consumer
        and "ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in consumer
        and "D3DPRIMITIVETYPE topology," in producer
        and "supported_game_state(game, type, vp, layout, transforms, capture, output)" in observer
        and "nativeSubmitted = submit(s, vertices, fanTriangles.data()," in observer
        and "D3DPT_TRIANGLELIST, capture, output);" in observer
        and "nativeSubmitted = submit(s, vertices, indices, indexCount," in observer
        and "type, capture, output);" in observer
        and "if (nativeSubmitted)" in observer
        and "s.frameBatch.succeeded(output.nativeDepthTest," in observer
        and "return optedIn;" in s
    )

def main():
    s = SOURCE.read_text(encoding="utf-8")
    assert linked(s), "Game ALPHAFUNC -> quantized HLSL AlphaGate -> Draw disconnected"

    cases = [(case, case.replace(" && ", " || ", 1)) for case in HLSL_CASES[:6]]
    cases += [(HLSL_CASES[6], "alphaParams.z == 1.0f")]
    cases += [(case, case.replace("func !=", "func ==", 1)) for case in GUARDS]
    cases += [
        ("floor(saturate(alpha) * 255.0f + 0.5f)", "saturate(alpha) * 255.0f"),
        ("clip(pass ? 1.0f : -1.0f);", "clip(1.0f);"),
        ("output.alphaFunc = static_cast<D3DCMPFUNC>(func);", "output.alphaFunc = D3DCMP_ALWAYS;"),
        ("output.alphaRef = reference;", "output.alphaRef = 0u;"),
        ("static_cast<float>(output.alphaFunc)", "8.0f"),
        ("static_cast<float>(output.alphaRef)", "0.0f"),
        ("supported_game_state(game, type, vp, layout, transforms, capture, output)",
         "supported_game_state(game, D3DPT_TRIANGLELIST, vp, layout, transforms, capture, output)"),
        ("D3DPRIMITIVETYPE topology,", "D3DPRIMITIVETYPE unusedTopology,"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "/* indexed draw dropped */"),
        ("ctx->Draw(static_cast<UINT>(vertices.size()), 0);", "/* linear draw dropped */"),
        ("nativeSubmitted = submit(s, vertices, fanTriangles.data(),",
         "nativeSubmitted = false /* fan submit removed */;"),
        ("nativeSubmitted = submit(s, vertices, indices, indexCount,",
         "nativeSubmitted = false /* indexed submit removed */;"),
        ("s.frameBatch.succeeded(output.nativeDepthTest,",
         "s.frameBatch.abort(); /* success path removed */"),
    ]
    for good, bad in cases:
        assert s.count(good) >= 1, good
        assert not linked(s.replace(good, bad, 1)), "undetected destructive mutation: " + good

    comparisons = {
        1: lambda a, b: False,
        2: operator.lt,
        3: operator.eq,
        4: operator.le,
        5: operator.gt,
        6: operator.ne,
        7: operator.ge,
        8: lambda a, b: True,
    }
    checks = 0
    for alpha in range(256):
        # Texture/vertex alpha has already saturated into an 8-bit compare.
        quantized = int((alpha / 255.) * 255. + 0.5)
        assert quantized == alpha
        for ref in range(256):
            expected = (
                False, alpha < ref, alpha == ref, alpha <= ref,
                alpha > ref, alpha != ref, alpha >= ref, True
            )
            for func in range(1, 9):
                assert comparisons[func](quantized, ref) == expected[func-1]
                checks += 1
    assert checks == 8 * 256 * 256
    print(f"00600 native menu/race alpha-test: {len(cases)} destructive mutations, {checks} 8-bit comparisons PASS")

if __name__ == "__main__":
    main()
