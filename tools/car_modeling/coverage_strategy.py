"""Breadth-first Ferrari cockpit priorities. Does not edit game assets or scenes.

Recommends the next component from independently saved per-vehicle workpacks.
Real edits must be done in Blender on original imported PMT-based meshes.
"""
import argparse
import json
from pathlib import Path

COMPONENTS = (
    "center_console", "driver_controls", "inner_door", "windshield_frame",
    "visible_seat", "instrument_cluster", "dashboard", "steering_wheel",
    "cross_cockpit_qa",
)
EDIT_LIMIT_PER_COMPONENT = 2
BANNED_DELIVERABLES = {"ovc3", "ovc", "pmt", "glb", "fbx"}


def validate(queue, workpack, slot):
    if slot not in ("A", "C"):
        raise ValueError("only Ferrari slot A or C")
    if workpack.get("schema_version") != 1 or workpack.get("strategy") != "breadth_first_cockpit_v3":
        raise ValueError("strategy V3 workpack required")
    if queue.get("active_by_slot", {}).get(slot) != workpack.get("car_id"):
        raise ValueError("BLOCKED: workpack car ownership differs from Ferrari16 queue")
    if workpack.get("slot") != slot or tuple(workpack.get("component_order", ())) != COMPONENTS:
        raise ValueError("workpack slot or cockpit component order drift")
    car = next((x for x in queue["cars"] if x["id"] == workpack["car_id"]), None)
    if not car or car["status"] != "ACTIVE" or car["slot"] != slot:
        raise ValueError("target is not active in this slot")
    provenance = car.get("source_provenance") or {}
    if not provenance.get("original_game_resource_sha256") or not provenance.get("original_import_blend_sha256"):
        raise ValueError("BLOCKED_INPUT: original PMT and native import missing")
    if len(workpack.get("migration_input_blend_sha256", "")) != 64:
        raise ValueError("BLOCKED_INPUT: latest source-backed private scene unknown")
    if not workpack.get("cannot_promote_from_interim_coverage"):
        raise ValueError("interim geometry coverage cannot promote a finished car")
    cards = workpack.get("components", {})
    if set(cards) != set(COMPONENTS):
        raise ValueError("missing component coverage cards")
    for key, c in cards.items():
        if c.get("status") not in {"NOT_STARTED", "P0_POLISH_HOLD", "IN_PROGRESS",
                                   "COVERED_PARTIAL_QA", "BLOCKED", "OUT_OF_VIEW"}:
            raise ValueError(f"invalid coverage card {key}")
        if not isinstance(c.get("source_edits_this_phase"), int) or c["source_edits_this_phase"] < 0:
            raise ValueError("invalid edit attempt count")
    return car


def recommended(workpack):
    """Never endlessly revisit P0 until other original cockpit components covered."""
    cards = workpack["components"]
    for component in COMPONENTS[:6]:
        if cards[component]["status"] in {"NOT_STARTED", "IN_PROGRESS"}:
            if cards[component]["source_edits_this_phase"] >= EDIT_LIMIT_PER_COMPONENT:
                continue
            return component
    for component in ("dashboard", "steering_wheel"):
        if cards[component]["status"] in {"NOT_STARTED", "IN_PROGRESS"}:
            if cards[component]["source_edits_this_phase"] < EDIT_LIMIT_PER_COMPONENT:
                return component
    return "cross_cockpit_qa"


def component_for_dispatch(n):
    """Two ACTUALLY SENT 30-minute commands per region; no rollover reset."""
    if not isinstance(n, int) or n < 0:
        raise ValueError("dispatch count must be non-negative")
    return COMPONENTS[min(n // EDIT_LIMIT_PER_COMPONENT, len(COMPONENTS)-1)]


def make_record(workpack, evidence):
    """Only a genuine source-backed Blender checkpoint counts as covered."""
    component = evidence.get("component")
    if component not in workpack["components"]:
        raise ValueError("invalid targeted component")
    if component != recommended(workpack):
        raise ValueError("component order violation: switch from repetitive P0 to unfinished cockpit region")
    card = workpack["components"][component]
    mode = evidence.get("result")
    if mode == "BLOCKED" or mode == "OUT_OF_VIEW":
        if not str(evidence.get("reason") or "").strip():
            raise ValueError("missing blocker / visibility explanation")
        card["status"] = mode
        card["blocking_reason"] = evidence["reason"]
        return workpack
    if mode != "COVERED_PARTIAL_QA":
        raise ValueError("interim pass is not final QA; use COVERED_PARTIAL_QA")
    original_sha = evidence.get("original_game_resource_sha256")
    if original_sha != workpack["original_game_resource_sha256"]:
        raise ValueError("original native game resource mismatch")
    input_sha = evidence.get("input_blend_sha256")
    output_sha = evidence.get("output_blend_sha256")
    if not all(isinstance(x, str) and len(x) == 64 for x in (input_sha, output_sha)) or input_sha == output_sha:
        raise ValueError("real different private .blend SHA256 required")
    if not evidence.get("original_mesh_object_ids_edited"):
        raise ValueError("source-native mesh object evidence required")
    if evidence.get("output_format") != "blend" or evidence.get("export_format") in BANNED_DELIVERABLES:
        raise ValueError("new car/export/OVC3 output forbidden")
    if evidence.get("from_scratch_car") or evidence.get("game_integration_performed"):
        raise ValueError("from-scratch car and runtime export forbidden")
    if not evidence.get("blender_saved_and_reopened"):
        raise ValueError("independent Blender save/reopen must be evidenced")
    card["status"] = "COVERED_PARTIAL_QA"
    card["source_edits_this_phase"] += 1
    card["last_saved_blend_sha256"] = output_sha
    card["evidence_refs"] = (card.get("evidence_refs", []) + [str(evidence.get("report_ref", ""))])[-5:]
    workpack["last_material_commit"] = evidence.get("source_commit_sha")
    return workpack


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--queue", required=True)
    p.add_argument("--state", required=True)
    p.add_argument("--slot", required=True, choices=("A", "C"))
    p.add_argument("--evidence", help="optional JSON geometry record to apply to workpack")
    args = p.parse_args()
    queue = json.loads(Path(args.queue).read_text(encoding="utf-8"))
    path = Path(args.state)
    pack = json.loads(path.read_text(encoding="utf-8"))
    validate(queue, pack, args.slot)
    if args.evidence:
        make_record(pack, json.loads(Path(args.evidence).read_text(encoding="utf-8")))
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "slot": args.slot,
        "car": pack["car_id"],
        "next_component": recommended(pack),
        "max_edits_before_switch": EDIT_LIMIT_PER_COMPONENT,
        "p0_revisit_blocked_until_breadth": recommended(pack) not in ("dashboard", "steering_wheel", "cross_cockpit_qa"),
        "interim_coverage_is_not_qa_pass": True,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
