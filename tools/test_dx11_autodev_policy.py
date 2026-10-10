#!/usr/bin/env python3
"""Executable negative controls for DX11 task allocation and Gate protection."""
import copy
import json

from dx11_autodev_policy import POLICY_FILE, validate_policy, validate_task, latest_dx11_run

p = json.loads(POLICY_FILE.read_text(encoding="utf-8"))
assert not validate_policy(p), validate_policy(p)
base = {
    "task_id": "CONVERSION-DX11-00531",
    "target_branch": "vr-dx11-native-r71",
    "runtime_validation": "UNTESTED",
    "automation_validation": "PENDING",
    "development_strategy": {
        "work_class": "vertical_slice",
        "milestone_id": "mono_native_draw",
        "integration_path": ["D3D9 draw source snapshot", "owned D3D11 resources", "real WARP Draw pixel"],
        "batch_components": ["source translator", "GPU integration probe"],
        "acceptance_proof": {
            "positive_probe": "same-device native Draw paints expected pixel",
            "negative_regression": "stale resource generation rejected",
            "component_integration": "D3D9 source lineage reaches bound DX11 target",
        },
        "conflict_keys": ["DX11:MONO_NATIVE_DRAW"],
        "full_gate_plan": "one_validation_bearing_sha",
    },
}
assert not validate_task(base, p), validate_task(base, p)
cases = [
    ("guard-only", lambda t: t["development_strategy"].update(work_class="readiness_guard")),
    ("missing bridge", lambda t: t["development_strategy"].update(integration_path=["one guard"])),
    ("single component", lambda t: t["development_strategy"].update(batch_components=["source guard"])),
    ("missing positive", lambda t: t["development_strategy"]["acceptance_proof"].update(positive_probe="")),
    ("missing negative", lambda t: t["development_strategy"]["acceptance_proof"].update(negative_regression="")),
    ("missing integration", lambda t: t["development_strategy"]["acceptance_proof"].update(component_integration="")),
    ("wrong milestone", lambda t: t["development_strategy"].update(milestone_id="legacy_small_fence")),
    ("no exact gate", lambda t: t["development_strategy"].update(full_gate_plan="skip_full_gate")),
    ("runtime fake", lambda t: t.update(runtime_validation="PASS")),
    ("full gate fake", lambda t: t.update(automation_validation="PASS", evidence={"backend_gate_conclusion": "failure"})),
    ("unsafe DXVK scope", lambda t: t.update(target_branch="vr-dxvk-r71-disasm")),
]
for label, mutate in cases:
    bad = copy.deepcopy(base)
    mutate(bad)
    assert validate_task(bad, p), f"negative task admitted: {label}"
blocked = copy.deepcopy(base)
blocked["development_strategy"].update(
    work_class="blocker_resolution", milestone_id="shader_parity_r175",
    blocking_evidence="R175 VS/PS TEXCOORD6 output mismatch [128,0,16,255] vs expected [224,128,32,255]",
)
assert not validate_task(blocked, p), validate_task(blocked, p)
blocked["development_strategy"].pop("blocking_evidence")
assert validate_task(blocked, p)
legacy = copy.deepcopy(base)
legacy["task_id"] = "CONVERSION-DX11-00530"
legacy.pop("development_strategy")
assert not validate_task(legacy, p), "live 00530 must not be retroactively invalidated"
run = latest_dx11_run()
assert run is not None, "expected durable DX11 run records"
print("DX11 auto-development policy: 11 negative mutations, 2 positive classes, pre-policy compatibility PASS")
