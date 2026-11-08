"""Sequential Ferrari geometry rework queue. Never advance merely due to elapsed time."""
import argparse
import datetime as dt
import json
import re
from pathlib import Path

UTC = dt.timezone.utc
HEX64 = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_VIEWS = {
    "front", "rear", "left", "right", "top", "cockpit"
}


def iso_utc(value):
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("expected timezone-aware timestamp")
    return parsed.astimezone(UTC)


def validate(queue):
    cars = queue.get("cars", [])
    if not cars or len(cars) != 16:
        raise ValueError("16 distinct vehicle entries required")
    if [x.get("order") for x in cars] != list(range(1, 17)):
        raise ValueError("vehicle order must remain 1..16")
    if len({x["id"] for x in cars}) != 16:
        raise ValueError("duplicate car id")
    if queue.get("policy") != "geometry_only_no_texture":
        raise ValueError("texture policy drift")
    active = [c for c in cars if c.get("status") == "ACTIVE"]
    if len(active) > 1:
        raise ValueError("parallel car modeling disallowed")
    if len(active) == 0 and not all(c.get("status") == "COMPLETE" for c in cars):
        raise ValueError("unfinished queue has no active car")
    if active and active[0]["id"] != queue.get("active_car_id"):
        raise ValueError("active pointer does not match car state")
    for idx, item in enumerate(cars):
        if item.get("status") not in {"ACTIVE", "PENDING", "COMPLETE"}:
            raise ValueError("unknown car status")
        if item.get("status") == "COMPLETE" and idx > 0:
            if cars[idx - 1].get("status") != "COMPLETE":
                raise ValueError("completion violates sequential order")
        if item.get("status") == "PENDING" and item.get("completed_at_utc"):
            raise ValueError("pending entry has completed timestamp")
    if queue["budget"]["per_car_wall_clock_hours"] != 24:
        raise ValueError("24h work policy changed")
    return active[0] if active else None


def check_evidence(car, evidence, clock):
    if not car.get("started_at_utc"):
        raise ValueError("NO_START: first new material geometry commit must establish start")
    started = iso_utc(car["started_at_utc"])
    if clock - started < dt.timedelta(hours=24):
        raise ValueError("LESS_THAN_24H: car still owns development")
    if clock < started:
        raise ValueError("clock precedes start")
    if car.get("geometry_gate") != "PASS" or car.get("reference_gate") != "PASS":
        raise ValueError("NO_GATE: independent geometry/photo acceptance is required")
    for key in ("source_scene_sha256", "output_scene_sha256"):
        if not isinstance(car.get(key), str) or not HEX64.fullmatch(car[key]):
            raise ValueError("NO_SHA: source/result scene hashes required")
    if evidence.get("car_id") != car["id"]:
        raise ValueError("wrong evidence car")
    if evidence.get("material_commit_count", 0) < 2:
        raise ValueError("at least two distinct physical geometry commits required")
    if not evidence.get("verified_blender_run_id"):
        raise ValueError("missing real-scene Blender run")
    if evidence.get("blender_mode") != "audit":
        raise ValueError("smoke mode can never promote a car")
    views = evidence.get("real_render_views", {})
    if not REQUIRED_VIEWS.issubset(set(views)) or not all(views.get(v) for v in REQUIRED_VIEWS):
        raise ValueError("six real geometry views required")
    photos = evidence.get("reference_photo_urls", {})
    if not REQUIRED_VIEWS.issubset(set(photos)) or not all(
        isinstance(photos.get(v), str) and photos[v].startswith("https://")
        for v in REQUIRED_VIEWS
    ):
        raise ValueError("six authentic original-car photo view URLs required")
    if evidence.get("manual_geometry_review") != "PASS":
        raise ValueError("reviewer must independently accept geometry")
    if evidence.get("texture_work_count", 0) != 0:
        raise ValueError("texture processing prohibited")
    return True


def advance(queue, evidence, clock):
    current = validate(queue)
    if current is None:
        raise ValueError("all cars already complete")
    check_evidence(current, evidence, clock)
    current["status"] = "COMPLETE"
    current["completed_at_utc"] = clock.isoformat()
    remaining = next((c for c in queue["cars"] if c["status"] == "PENDING"), None)
    if remaining:
        remaining["status"] = "ACTIVE"
        queue["active_car_id"] = remaining["id"]
    else:
        queue["active_car_id"] = None
    validate(queue)
    return remaining["id"] if remaining else None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--queue", required=True)
    p.add_argument("--evidence")
    p.add_argument("--advance", action="store_true")
    args = p.parse_args()
    path = Path(args.queue)
    queue = json.loads(path.read_text(encoding="utf-8"))
    active = validate(queue)
    if not args.advance:
        print("QUEUE_OK active=" + (active["id"] if active else "NONE"))
        return
    if not args.evidence:
        raise SystemExit("Refuse advance: evidence file required")
    next_car = advance(
        queue, json.loads(Path(args.evidence).read_text(encoding="utf-8")),
        dt.datetime.now(UTC),
    )
    path.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("GATE_PASS next_car=" + (next_car or "DONE"))


if __name__ == "__main__":
    main()
