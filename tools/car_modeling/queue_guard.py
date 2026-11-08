"""Cockpit-only Ferrari queue, 2 independent 24h owners. No time-only advancement."""
import argparse
import datetime as dt
import json
import re
from pathlib import Path

UTC = dt.timezone.utc
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SLOTS = ("A", "C")
REQUIRED_COCKPIT_VIEWS = frozenset((
    "driver_eye", "dashboard", "steering_wheel", "instrument_cluster",
    "center_console", "door_trim", "windshield_frame",
))
WORK_PROHIBITED = frozenset((
    "car exterior body panels", "exterior wheels", "tires", "suspension",
    "textures", "PBR", "normal maps",
))


def iso_utc(value):
    result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() is None:
        raise ValueError("timestamp must carry UTC offset")
    return result.astimezone(UTC)


def validate(queue):
    cars = queue.get("cars", ())
    if len(cars) != 16 or [c.get("order") for c in cars] != list(range(1, 17)):
        raise ValueError("expected original 16-entry Ferrari inventory in immutable order")
    if len({c["id"] for c in cars}) != 16:
        raise ValueError("duplicate vehicle IDs")
    if queue.get("schema_version") != 2:
        raise ValueError("expected dual-slot schema v2")
    if queue.get("policy") != "cockpit_visible_geometry_only_no_texture":
        raise ValueError("cockpit-only policy drift")
    budget = queue.get("budget", {})
    if budget.get("per_car_wall_clock_hours") != 24:
        raise ValueError("24h policy drift")
    if set(budget.get("required_views", ())) != REQUIRED_COCKPIT_VIEWS:
        raise ValueError("cockpit photo and render acceptance must match")
    if not WORK_PROHIBITED.issubset(set(budget.get("exclude", ()))):
        raise ValueError("external wheel/body or texture work reactivated")
    slots = queue.get("slots", {})
    if slots.get("A", {}).get("schedule_minutes") != [0, 30]:
        raise ValueError("A dispatch should be at 00/30")
    if slots.get("C", {}).get("schedule_minutes") != [15, 45]:
        raise ValueError("C dispatch should be at 15/45")
    active_by_slot = queue.get("active_by_slot")
    if set(active_by_slot or {}) != set(SLOTS):
        raise ValueError("A/C must have separate ownership entries")
    car_map = {c["id"]: c for c in cars}
    owners = {}
    for slot, car_id in active_by_slot.items():
        if car_id is None:
            continue
        if car_id in owners:
            raise ValueError("one car owned by multiple slots")
        if car_id not in car_map or car_map[car_id].get("slot") != slot or car_map[car_id].get("status") != "ACTIVE":
            raise ValueError("slot-to-car assignment mismatch")
        owners[car_id] = slot
    active = [c for c in cars if c["status"] == "ACTIVE"]
    if len(active) > 2:
        raise ValueError("more than two active vehicles")
    if {c["id"] for c in active} != set(owners):
        raise ValueError("ACTIVE entries must have unique assigned slot")
    if cars[1]["id"] != "dino246gts" or cars[1]["status"] != "SKIPPED_DONE_BY_USER":
        raise ValueError("finished Dino246 is excluded, not recreated")
    for c in cars:
        if c["status"] not in {"ACTIVE", "PENDING", "COMPLETE", "SKIPPED_DONE_BY_USER"}:
            raise ValueError("unknown car status")
        if c["id"] != "dino246gts" and c["status"] == "SKIPPED_DONE_BY_USER":
            raise ValueError("unexpected skip without operator override")
        if c["status"] == "PENDING" and (c.get("slot") or c.get("completed_at_utc")):
            raise ValueError("pending car has an owner or completion timestamp")
        if c["status"] == "ACTIVE" and c.get("completed_at_utc"):
            raise ValueError("active car already completed")
        if c["status"] == "COMPLETE" and not c.get("completed_at_utc"):
            raise ValueError("complete car has no completion timestamp")
        if c["status"] in ("PENDING", "ACTIVE") and c.get("geometry_gate") == "PASS" and c.get("reference_gate") != "PASS":
            raise ValueError("unreviewed photo evidence")
    if any(c["status"] == "PENDING" for c in cars) and any(x is None for x in active_by_slot.values()):
        raise ValueError("available slot left empty while pending vehicles remain")
    return {slot: car_map.get(car_id) for slot, car_id in active_by_slot.items()}


def check_evidence(car, evidence, now):
    if not car.get("started_at_utc"):
        raise ValueError("NO_START: record first new source geometry commit timestamp")
    started = iso_utc(car["started_at_utc"])
    if now < started or now - started < dt.timedelta(hours=24):
        raise ValueError("LESS_THAN_24H: do not advance before full vehicle work window")
    if car.get("geometry_gate") != "PASS" or car.get("reference_gate") != "PASS":
        raise ValueError("NO_GATE: both geometry and photos must PASS")
    for key in ("source_scene_sha256", "output_scene_sha256"):
        if not isinstance(car.get(key), str) or not HEX64.fullmatch(car[key]):
            raise ValueError("missing real original and edited Blender scene SHA256")
    if car["source_scene_sha256"] == car["output_scene_sha256"]:
        raise ValueError("unchanged Blender scene does not count")
    if evidence.get("car_id") != car["id"] or evidence.get("slot") != car.get("slot"):
        raise ValueError("evidence belongs to another car or slot")
    if evidence.get("material_commit_count", 0) < 2:
        raise ValueError("missing multiple independently committed geometry improvements")
    if not evidence.get("verified_blender_run_id") or evidence.get("blender_mode") != "audit":
        raise ValueError("missing real-scene Blender audit; smoke does not count")
    if not evidence.get("independent_reopen_verified"):
        raise ValueError("Blender scene must be saved and reopened independently")
    renders = evidence.get("real_render_views", {})
    if not REQUIRED_COCKPIT_VIEWS.issubset(renders) or not all(renders.get(v) for v in REQUIRED_COCKPIT_VIEWS):
        raise ValueError("missing seven cockpit-only render views")
    photos = evidence.get("reference_photo_urls", {})
    if not REQUIRED_COCKPIT_VIEWS.issubset(photos) or not all(
        isinstance(photos.get(v), str) and photos[v].startswith("https://")
        for v in REQUIRED_COCKPIT_VIEWS
    ):
        raise ValueError("missing seven source-proven real-car cockpit photo views")
    if evidence.get("correct_car_variant") is not True or evidence.get("photo_handedness_checked") is not True:
        raise ValueError("real vehicle trim and LHD/RHD photos must be verified")
    if evidence.get("dashboard_review") != "PASS" or evidence.get("steering_wheel_review") != "PASS":
        raise ValueError("P0 dashboard and wheel must both PASS first")
    if evidence.get("manual_geometry_review") != "PASS":
        raise ValueError("manual geometry review missing")
    if evidence.get("outside_cockpit_geometry_edit_count", 0) or evidence.get("texture_work_count", 0):
        raise ValueError("external/body/wheel geometry or new texture/PBR work prohibited")


def advance(queue, evidence, now, slot="A"):
    active = validate(queue)
    if slot not in SLOTS:
        raise ValueError("unknown modeling slot")
    current = active[slot]
    if current is None:
        raise ValueError("slot has no current vehicle")
    check_evidence(current, evidence, now)
    current["status"] = "COMPLETE"
    current["completed_at_utc"] = now.astimezone(UTC).isoformat()
    current["slot"] = None
    candidate = next((c for c in queue["cars"] if c["status"] == "PENDING"), None)
    if candidate:
        candidate["status"] = "ACTIVE"
        candidate["slot"] = slot
        queue["active_by_slot"][slot] = candidate["id"]
    else:
        queue["active_by_slot"][slot] = None
    validate(queue)
    return candidate["id"] if candidate else None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--queue", required=True)
    p.add_argument("--slot", choices=SLOTS, default="A")
    p.add_argument("--evidence")
    p.add_argument("--advance", action="store_true")
    args = p.parse_args()
    path = Path(args.queue)
    queue = json.loads(path.read_text(encoding="utf-8"))
    active = validate(queue)
    if not args.advance:
        print("QUEUE_OK " + " ".join(f"{s}={active[s]['id'] if active[s] else 'IDLE'}" for s in SLOTS))
        return
    if not args.evidence:
        raise SystemExit("evidence file is required for promotion")
    next_car = advance(
        queue, json.loads(Path(args.evidence).read_text(encoding="utf-8")),
        dt.datetime.now(UTC), slot=args.slot,
    )
    path.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"GATE_PASS slot={args.slot} next_car={next_car or 'DONE'}")


if __name__ == "__main__":
    main()
