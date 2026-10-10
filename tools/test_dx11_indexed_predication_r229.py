#!/usr/bin/env python3
"""R229: reject conditional DrawIndexed predication, preserve R219 OM fence."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
source = (root / "src/vr/d3d11/native_indexed_uav_eye_guard.hpp").read_text(encoding="utf-8")
probe = (root / "tools/dx11_indexed_draw_probe_r186.cpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
r229 = source.split("// R229: R219 proves sole-eye OM ownership", 1)[1]
guards = (
    "verified_indexed_unpredicated_eye_ready(",
    "!verified_indexed_uav_isolated_eye_ready(",
    "context->GetPredication(livePredicate.GetAddressOf(), &predicatePolarity);",
    "return !livePredicate;",
)
assert all(x in r229 for x in guards), "missing R229 predicate fence"
for x in guards:
    assert not all(g in r229.replace(x, "", 1) for g in guards), (
        "R229 negative mutant escaped: " + x
    )
assert "->Draw(" not in source and "->DrawIndexed(" not in source
for x in (
    "R229 initial unpredicated indexed eye",
    "R229 create same-device occlusion predicate",
    "R229 predecessor accepts active predicate",
    "R229 reject false-polarity predication",
    "R229 reject true-polarity predication",
    "R229 restore unpredicated indexed eye",
    "R229 unpredicated WARP DrawIndexed restores green pixel",
    "context->SetPredication(r229Predicate.Get(),FALSE);",
    "context->SetPredication(r229Predicate.Get(),TRUE);",
    "context->SetPredication(nullptr,FALSE);",
    "context->DrawIndexed(3u,0u,0);",
):
    assert x in probe, "R229 WARP missing: " + x
step = "python tools/test_dx11_indexed_predication_r229.py"
assert workflow.count(step) == 1
assert workflow.index("Verify R219 indexed OM UAV isolation") < workflow.index(step)
assert workflow.index(step) < workflow.index("Build R186 owned indexed Draw WARP probe")
print("R229 indexed predication: four guard mutants + same-device TRUE/FALSE + WARP restore wired PASS")
