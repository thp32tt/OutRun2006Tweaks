#!/usr/bin/env python3
"""00980 native SM3 live shader trig/sign opcode source integration."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPE = ROOT / "src/vr/d3d11/pipeline_translation.cpp"
NATIVE = ROOT / "src/vr/d3d11/native_backend.cpp"
HELPER = ROOT / "src/vr/d3d11/native_sm3_trig_sign_opcode.hpp"


def connected(pipeline: str, backend: str, helper: str) -> bool:
    # Both game shader stages must decode exact source arity before emitting
    # native HLSL. SM2 trig and pixel SGN stay outside the live SM3 contract.
    semantic = pipeline.split("const auto plan_for =", 1)[-1].split(
        "std::uint64_t semanticHash =", 1
    )[0]
    live = backend.split("NativeSm3ArithmeticOpcode opcode{}", 1)[-1].split(
        "// Predication, co-issue", 1
    )[0]
    return all(s in semantic for s in [
        "case D3DSIO_SINCOS:", "case D3DSIO_SGN:",
        "shaderMajor, vertexStage", "operands.sourceCount",
        "NativeSm3TrigSignOpcode::SineCosine",
        "NativeSm3TrigSignOpcode::Sign",
    ]) and all(s in pipeline for s in [
        # Scratch-register parsing executes after semanticHash initialization,
        # not inside plan_for's opcode table. Check the full decode function.
        "ProgrammableShaderRegisterOperandRole::ScratchDestination",
        "++out.scratchDestinationOperandCount",
        "scratch0.registerIndex == scratch1.registerIndex",
    ]) and all(s in live for s in [
        "case D3DSIO_SINCOS:", "case D3DSIO_SGN:",
        "NativeSm3TrigSignOpcode::SineCosine, 3u, vertexStage",
        "NativeSm3TrigSignOpcode::Sign, 3u, vertexStage",
        "operands.scratchDestinations", "sourceCount = operands.sourceCount"
    ]) and all(s in helper for s in [
        "shaderMajor == 3u", "shaderMajor == 2u",
        "return {1u, false, true};", "return {3u, true, true};"
    ])


def main() -> None:
    p = PIPE.read_text(encoding="utf-8")
    n = NATIVE.read_text(encoding="utf-8")
    h = HELPER.read_text(encoding="utf-8")
    assert connected(p, n, h), "trig/sign decoder to live native shader disconnected"
    assert not connected(p.replace("case D3DSIO_SINCOS:", "case D3DSIO_NOP:", 1), n, h)
    assert not connected(p.replace("case D3DSIO_SGN:", "case D3DSIO_NOP:", 1), n, h)
    assert not connected(p, n.replace("operands.scratchDestinations", "false", 1), h)
    assert not connected(p, n, h.replace("return {3u, true, true};", "return {};"))
    assert not connected(p.replace(
        "++out.scratchDestinationOperandCount", "++out.sourceOperandCount", 1
    ), n, h)
    print("DX11 00980 live SM3 trig/sign source integration: PASS")


if __name__ == "__main__":
    main()
