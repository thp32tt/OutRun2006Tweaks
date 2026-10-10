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
# 00531-00536 durable work remains grandfathered; 00537+ must ship game-frame progress.
historical = copy.deepcopy(base)
historical['task_id'] = 'CONVERSION-DX11-00536'
assert not validate_task(historical, p), validate_task(historical, p)
frame = copy.deepcopy(base)
frame['task_id'] = 'CONVERSION-DX11-00537'
frame['development_strategy'].update(
    milestone_id='first_live_game_draw',
    gameplay_delivery_target='FIRST_GAME_DRAW_FRAME',
    live_game_draw_path=['LIVE_D3D9_CALLSITE', 'D3D11_NATIVE_DRAW', 'VISIBLE_FRAME_OUTPUT'],
    visible_frame_acceptance='one OutRun authored draw creates a diagnostic native game frame; HMD result untested',
    activation_guard_and_fallback='explicit diagnostic opt-in, NativeDrawPathActive false by default, unsupported paths use DX9Ex',
)
assert not validate_task(frame, p), validate_task(frame, p)
mutations = [
    ('old dormant milestone', lambda t: t['development_strategy'].update(milestone_id='mono_native_draw')),
    ('missing gameplay delivery', lambda t: t['development_strategy'].pop('gameplay_delivery_target')),
    ('missing actual D3D9 callsite', lambda t: t['development_strategy'].update(live_game_draw_path=['D3D11_NATIVE_DRAW','VISIBLE_FRAME_OUTPUT'])),
    ('no visible output', lambda t: t['development_strategy'].update(live_game_draw_path=['LIVE_D3D9_CALLSITE','D3D11_NATIVE_DRAW'])),
    ('reverse-order frame pipeline', lambda t: t['development_strategy'].update(live_game_draw_path=['VISIBLE_FRAME_OUTPUT','D3D11_NATIVE_DRAW','LIVE_D3D9_CALLSITE'])),
    ('no fallback', lambda t: t['development_strategy'].update(activation_guard_and_fallback='')),
    ('no acceptance', lambda t: t['development_strategy'].update(visible_frame_acceptance='')),
    ('test-only claimed complete', lambda t: t.update(status='COMPLETE', changed_files=['tools/test_dx11_probe.py'])),
]
for label, mutate in mutations:
    bad = copy.deepcopy(frame)
    mutate(bad)
    assert validate_task(bad, p), 'gameplay-first negative admitted: '+label
r175_new = copy.deepcopy(frame)
r175_new['development_strategy'].update(
    milestone_id='shader_parity_r175', work_class='blocker_resolution',
    gameplay_delivery_target='R175_CI_UNBLOCK',
    blocking_evidence='R175 mismatch WARP TEXCOORD6 [128,0,16,255] != [224,128,32,255]',
    r175_owner_handoff_evidence='verified fenced handoff from original 00477 owner',
)
assert not validate_task(r175_new, p), validate_task(r175_new, p)
r175_new['development_strategy'].pop('r175_owner_handoff_evidence')
assert validate_task(r175_new, p), 'R175 ownership takeover without evidence must fail'
run = latest_dx11_run()
assert run is not None, "expected durable DX11 run records"
print("DX11 auto-development policy: 11 legacy + 9 gameplay negative mutations, 3 positive classes, pre-policy compatibility PASS")
