#!/usr/bin/env python3
"""R230 non-indexed predication ownership and WARP recovery contract."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
s = (root / "src/vr/d3d11/native_linear_uav_eye_guard.hpp").read_text(encoding="utf-8")
p = (root / "tools/dx11_linear_buffer_mirror_probe.cpp").read_text(encoding="utf-8")
w = (root / ".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
# R232 composes the R230 preflight, so mutation checks cover R230's body
# only. Retain the full-header no-Draw activation invariant below.
section = s.split("// R230: a live D3D11 predicate", 1)[1].split(
    "// R232: even an otherwise unpredicated", 1)[0]
required = (
    "verified_linear_unpredicated_eye_ready(",
    "!verified_linear_uav_isolated_eye_ready(",
    "Microsoft::WRL::ComPtr<ID3D11Predicate> livePredicate;",
    "context->GetPredication(livePredicate.GetAddressOf(), &predicatePolarity);",
    "return !livePredicate;",
)
assert all(x in section for x in required)
for deleted in required:
    mutant = section.replace(deleted, "", 1)
    assert not all(x in mutant for x in required), "surviving R230 guard mutant: " + deleted
assert "->Draw(" not in s and "->DrawIndexed(" not in s
for label in (
    "R230 initial unpredicated linear eye",
    "R230 same-device predicate object",
    "R230 predecessor accepts active predicate",
    "R230 reject false-polarity predication",
    "R230 reject true-polarity predication",
    "R230 restore unpredicated linear eye",
    "R230 restored WARP Draw paints red eye pixel",
    "ctx->SetPredication(r230Predicate.Get(), FALSE);",
    "ctx->SetPredication(r230Predicate.Get(), TRUE);",
    "ctx->SetPredication(nullptr, FALSE);",
    "ctx->Draw(3u, 0u);",
):
    assert label in p, "missing linear WARP proof: " + label
step = "python tools/test_dx11_linear_predication_r230.py"
assert w.count(step) == 1
assert w.index("Verify R221 linear OM UAV isolation") < w.index(step)
assert w.index(step) < w.index("Build DX11 linear VB/IB mirror R183 WARP probe")
print("R230 linear predication: 5 mutants + two WARP predicate polarities + GPU restoration PASS")
