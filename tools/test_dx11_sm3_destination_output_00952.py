#!/usr/bin/env python3
"""Native live SM3 VS/PS destination transform integration and fallback."""
from pathlib import Path
base = Path(__file__).resolve().parents[1]
backend = (base / "src/vr/d3d11/native_backend.cpp").read_text()
header = (base / "src/vr/d3d11/native_sm3_destination_output.hpp").read_text()
workflow = (base / ".github/workflows/dx11-fast-structural.yml").read_text()
for token in ("#include \"native_sm3_destination_output.hpp\"",
              "op.destinationModifier =", "op.destinationShift =",
              "D3DSP_DSTMOD_SHIFT", "D3DSP_DSTSHIFT_SHIFT",
              "native_sm3_destination_modifiers_accepted(",
              "append_native_sm3_destination_postprocess("):
    assert token in backend, token
# Ensure the modifier executes after each actual native arithmetic / texture /
# matrix emission and BEFORE the predication scope closes.
emission = backend.index("} else if (!append_native_sm3_arithmetic(")
post = backend.index("if (!append_native_sm3_destination_postprocess(", emission)
end_predicate = backend.index("append_native_sm3_predicated_end(translated)", emission)
assert emission < post < end_predicate
for token in ("modifier > 1u", "shift == 13u", "shift == 14u",
              "shift == 15u", "saturate(", "mask & ~15u"):
    assert token in header, token
for token in ("dx11_sm3_destination_output_probe_00952.cpp",
              "test_dx11_sm3_destination_output_00952.py"):
    assert token in workflow, token
print("Native SM3 per-lane destination shift/saturate shader path PASS")
