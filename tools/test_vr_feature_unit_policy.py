#!/usr/bin/env python3
"""Negative regressions for 00772+ integrated feature acceptance."""
import copy
import json
from verify_vr_feature_unit_policy import POLICY, validate

policy = json.loads(POLICY.read_text(encoding="utf-8"))
baseline = {
    "task_id": "CONVERSION-DX9EX-00772",
    "feature_id": "DX9EX-QUEST3-RESPONSIVE-UI-20261013",
    "status": "IMPLEMENTING",
    "runtime_validation": "UNTESTED",
    "feature_contract": {
        "feature_id": "DX9EX-QUEST3-RESPONSIVE-UI-20261013",
        "goal": "Complete source/FOV responsive Quest3 HUD, menu, ESC, F11 and integrated acceptance",
        "acceptance_items": [
            {"id": "hud", "category": "end_to_end_behavior", "behavior_area": "gameplay_hud", "expected_behavior": "HUD anchors follow source aspect and real XR FOV"},
            {"id": "fallback", "category": "fallback_regression", "behavior_area": "menu_overlay", "expected_behavior": "Non-VR and unsupported eye aspect preserve native fallback"},
            {"id": "full", "category": "integrated_validation", "behavior_area": "gameplay_hud", "expected_behavior": "Exact SHA DX9Ex Active Win32 and Domain success"},
        ],
    },
}
assert not validate(baseline, policy), validate(baseline, policy)
for label, mutation in (
    ("no feature", lambda r: r.pop("feature_contract")),
    ("one widget", lambda r: r["feature_contract"].update(acceptance_items=r["feature_contract"]["acceptance_items"][:1])),
    ("missing fallback", lambda r: r["feature_contract"]["acceptance_items"][1].update(category="end_to_end_behavior")),
    ("same behavior area", lambda r: [x.update(behavior_area="same") for x in r["feature_contract"]["acceptance_items"]]),
    ("wrong ownership", lambda r: r["feature_contract"].update(feature_id="different")),
    ("false terminal", lambda r: r.update(status="COMPLETE_BUILD_VERIFIED", automation_validation="PASS_EXACT_SHA", validation_bearing_result_sha="a"*40, acceptance_results={"hud": "PASS"})),
):
    bad = copy.deepcopy(baseline)
    mutation(bad)
    assert validate(bad, policy), "micro-feature passed: " + label
done = copy.deepcopy(baseline)
done.update(status="COMPLETE_BUILD_VERIFIED", automation_validation="PASS_EXACT_SHA", validation_bearing_result_sha="a"*40, acceptance_results={"hud":"PASS", "fallback":"PASS", "full":"PASS_EXACT_SHA"})
assert not validate(done, policy), validate(done, policy)
legacy = copy.deepcopy(baseline)
legacy["task_id"] = "CONVERSION-DX9EX-00771"
legacy.pop("feature_contract")
assert not validate(legacy, policy), "00771 and prior must be grandfathered"
print("DX9Ex functional feature-sized dispatch acceptance: PASS")
