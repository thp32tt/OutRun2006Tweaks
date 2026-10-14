#!/usr/bin/env python3
"""Destructive unit tests: each visual defect stays whole, not a tiny patch or umbrella."""
import copy
import json
from verify_vr_feature_unit_policy import POLICY, validate, printable_diagnostic, validate_source_first_override

p = json.loads(POLICY.read_text(encoding="utf-8"))
assert p["schema_version"] == 2
assert not validate_source_first_override(p)
for label, change in (
    ("review-first", lambda q: q["user_override_20261014"].update(dispatch_order="REVIEW_FIRST")),
    ("skip-final-gate", lambda q: q["validation_cadence_20261014"].update(final_full_exact_sha_preserved=False)),
    ("allow-micro-builds", lambda q: q["validation_cadence_20261014"].update(no_repeated_full_build_per_microedit=False)),
):
    bad = copy.deepcopy(p)
    change(bad)
    assert validate_source_first_override(bad), "DX9Ex source-first guard failed: " + label
features = {x["id"]: x for x in p["feature_catalog"]}
assert {"HUD_GAMEPLAY", "F11_MENU", "ESC_MENU", "MAIN_MENU",
        "LENS_FLARE_CENTRE", "EXTENDED_TIME", "GOAL_PROGRESS"}.issubset(features)

def fresh(f):
    return {
        "task_id": "CONVERSION-DX9EX-00772",
        "feature_id": f["feature_id"],
        "symptom_id": f["symptom_id"],
        "feature_class": "USER_VISIBLE_VISUAL_DEFECT",
        "status": "IMPLEMENTING",
        "runtime_validation": "UNTESTED",
        "feature_contract": {
            "feature_id": f["feature_id"],
            "symptom_id": f["symptom_id"],
            "goal": f["goal"],
            "scope_boundary": "Only this user-visible error and its source layer; other features unchanged.",
            "trace_stages": f["trace_stages"],
            "subcomponents": ["producer-side defect and complete semantics",
                              "stereo/per-eye visual correction and fallback"],
            "acceptance_items": [
                {"id": "all_producers", "category": "end_to_end_behavior",
                 "behavior_area": "producer", "expected_behavior": "Every component of visible symptom corrected"},
                {"id": "fallback", "category": "fallback_regression",
                 "behavior_area": "eye_composition", "expected_behavior": "Protected stereo/fallback behavior remains correct"},
                {"id": "integrated", "category": "integrated_validation",
                 "behavior_area": "producer", "expected_behavior": "Exact SHA Win32 game host package and guards PASS"},
            ],
        },
    }

for f in features.values():
    record = fresh(f)
    assert not validate(record, p), (f["id"], validate(record, p))

f = features["LENS_FLARE_CENTRE"]
baseline = fresh(f)
for label, corrupt in (
    ("umbrella", lambda r: r.update(feature_id="DX9EX-QUEST3-RESPONSIVE-UI-20261013")),
    ("subcontrol-only", lambda r: r["feature_contract"].update(subcomponents=["one offset"])),
    ("no trace", lambda r: r["feature_contract"].update(trace_stages=[])),
    ("wrong symptom", lambda r: r.update(symptom_id="DX9EX:SYMPTOM:EXTENDED_TIME")),
    ("wrong contract symptom", lambda r: r["feature_contract"].update(symptom_id="DX9EX:SYMPTOM:HUD_GAMEPLAY")),
    ("only one assertion", lambda r: r["feature_contract"].update(acceptance_items=r["feature_contract"]["acceptance_items"][:1])),
    ("skip fallback", lambda r: r["feature_contract"]["acceptance_items"][1].update(category="end_to_end_behavior")),
    ("same layer", lambda r: [i.update(behavior_area="one") for i in r["feature_contract"]["acceptance_items"]]),
    ("no scope", lambda r: r["feature_contract"].update(scope_boundary="")),
    ("no diagnosis terminal", lambda r: r.update(status="COMPLETE_BUILD_VERIFIED")),
):
    bad = copy.deepcopy(baseline)
    corrupt(bad)
    assert validate(bad, p), "bad feature incorrectly accepted: " + label

def finished(record):
    good = copy.deepcopy(record)
    good.update(
        status="COMPLETE_BUILD_VERIFIED",
        automation_validation="PASS_EXACT_SHA",
        validation_bearing_result_sha="a"*40,
        material_result_sha="b"*40,
        changed_files=["src/vr/d3d9/stereo_renderer_r30.cpp", "tools/test_flare.py"],
        acceptance_results={"all_producers":"PASS", "fallback":"PASS", "integrated":"PASS_EXACT_SHA"},
        ci_evidence={"exact_sha": "a"*40, "dx9ex_active": "SUCCESS",
                     "domain_isolation":"SUCCESS", "win32_game_host_package":"SUCCESS"},
        diagnosis={
            "original_evidence":"Canonical EXE effect caller and protected outer ring identity inspected",
            "source_trace":["original producer origin and sprite semantic mapped",
                            "queue/c64 effect submission ownership mapped",
                            "eye-specific transform and host composition mapped"],
            "root_cause":"Confirmed duplicate centre effect owner at the original producer-to-stereo boundary.",
            "alternatives_rejected":["Outer ring and SkyGlow producer disproved by independent callsite and test"],
            "fix_evidence":"C++ whole-feature source change with pre/post visual source-trace evidence",
            "negative_test_evidence":"Fail-before/pass-after mutated wrong-producer and eye scope tests",
            "eye_ownership":"Left/right centre depth owner is scene projected, not head-fixed.",
        },
    )
    return good

good = finished(baseline)
assert not validate(good, p), validate(good, p)
bad=copy.deepcopy(good)
bad["diagnosis"]["source_trace"]=bad["diagnosis"]["source_trace"][:1]
assert validate(bad,p), "shallow analysis cannot complete feature"
bad=copy.deepcopy(good)
bad["diagnosis"]["eye_ownership"]=""
assert validate(bad,p), "headlock cause must be described"
bad=copy.deepcopy(good)
bad["changed_files"]=["docs/automation/runs/foo.json"]
assert validate(bad,p), "bookkeeping must not complete visual fix"
bad=copy.deepcopy(good)
bad["acceptance_results"]["fallback"]="PENDING"
assert validate(bad,p), "one positive test is not complete feature"
bad=copy.deepcopy(good)
bad["runtime_validation"]="PASS"
assert validate(bad,p), "no invented headset PASS"
legacy=copy.deepcopy(baseline)
legacy["task_id"]="CONVERSION-DX9EX-00771"
legacy.pop("feature_contract")
assert not validate(legacy,p), "historical C6 must be grandfathered"
# A distinct performance feature is allowed with specific measured evidence.
perf=fresh(features["HUD_GAMEPLAY"])
perf.update(feature_id="DX9EX:PERF:FRAME_PACING",symptom_id="NA",feature_class="MEASURED_PERFORMANCE")
perf["feature_contract"].update(feature_id="DX9EX:PERF:FRAME_PACING",
    special_work_evidence="Measured R23/GPU p95 frame time exceeds XR 72 Hz budget")
assert not validate(perf,p),validate(perf,p)
# Reproduce the failing Windows-2022 PowerShell runner's cp1252 stdout.
# The actual validation errors must survive even when the JSON contains
# a non-ASCII original-to-Draw-to-eye trace.
diagnostic = "original\u2192Draw\u2192eye"
assert printable_diagnostic(diagnostic, "cp1252") == r"original\u2192Draw\u2192eye"
assert printable_diagnostic(diagnostic, "utf-8") == diagnostic
assert printable_diagnostic(diagnostic, None) == diagnostic
# Regression for CONVERSION-DX9EX-00820: the original material commit
# failed before Windows compile because the rank feature omitted its explicit
# neighbor-exclusion boundary. Verify the actual record and remove the field
# destructively: the same policy error must be observable, not silently skipped.
rank_run_path = POLICY.parent / "runs" / "CONVERSION-DX9EX-00820.json"
if rank_run_path.is_file():
    rank_run = json.loads(rank_run_path.read_text(encoding="utf-8"))
    assert rank_run["feature_id"] == features["RANK_MARKERS"]["feature_id"]
    assert not validate(rank_run, p), validate(rank_run, p)
    rank_without_boundary = copy.deepcopy(rank_run)
    rank_without_boundary["feature_contract"].pop("scope_boundary", None)
    rank_errors = validate(rank_without_boundary, p)
    assert "scope_boundary must exclude adjacent unrelated features" in rank_errors, rank_errors

# The Windows pwsh job must fail-closed on every Python verifier. PowerShell
# does not automatically propagate a failing *intermediate* python process:
# a later successful check previously hid "run record missing" at exact HEAD.
workflow = (POLICY.parents[2] / ".github/workflows/vr-dx9ex-active.yml").read_text(encoding="utf-8")
step = workflow.split("- name: Enforce feature-sized DX9Ex autonomous completion", 1)[1].split("- name:", 1)[0]
for command in (
    "python tools/test_vr_feature_unit_policy.py",
    "python tools/test_dx9ex_function_dispatch.py",
    "python tools/verify_vr_feature_unit_policy.py --check-head",
    "python tools/verify_vr_hud_edge_transition.py",
    "python tools/verify_vr_r30_positiont_decl.py",
    "python tools/verify_vr_stage_extension_d3dx_batch_owner.py",
):
    pos = step.index(command)
    rest = step[pos + len(command):].split("\n", 2)
    assert len(rest) > 1 and "if ($LASTEXITCODE -ne 0)" in rest[1], command
# Keep the expected guard count tied to the enumerated commands. A new
# verifier must be guarded too, without making this mutation test stale.
guard_count = step.count("if ($LASTEXITCODE -ne 0)")
assert guard_count == 6, "all six policy verifiers must fail closed"
mutant = step.replace("if ($LASTEXITCODE -ne 0)", "# swallow verifier errors", 1)
assert mutant.count("if ($LASTEXITCODE -ne 0)") == guard_count - 1
print(f"DX9Ex full-function/visual-defect policy PASS: {len(features)} feature classes, 10+ negative cases, terminal root-cause gate, legacy and performance")
