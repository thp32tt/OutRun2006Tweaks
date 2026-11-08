import copy
import datetime as dt
import json
import unittest
from pathlib import Path

from queue_guard import REQUIRED_COCKPIT_VIEWS, advance, check_evidence, validate

UTC = dt.timezone.utc
ROOT = Path(__file__).resolve().parents[2]
SEED = json.loads((ROOT / "docs/automation/FERRARI16_GEOMETRY_QUEUE.json").read_text(encoding="utf-8"))


def ready(now, slot="A"):
    q = copy.deepcopy(SEED)
    car = validate(q)[slot]
    car.update(
        started_at_utc=(now - dt.timedelta(hours=25)).isoformat(),
        geometry_gate="PASS",
        reference_gate="PASS",
        source_scene_sha256="a" * 64,
        output_scene_sha256="b" * 64,
    )
    ev = dict(
        car_id=car["id"], slot=slot, material_commit_count=2,
        verified_blender_run_id="123456", blender_mode="audit",
        independent_reopen_verified=True,
        real_render_views={v: "blender-run-1234/" + v for v in REQUIRED_COCKPIT_VIEWS},
        reference_photo_urls={v: "https://example.org/photos/" + v for v in REQUIRED_COCKPIT_VIEWS},
        correct_car_variant=True, photo_handedness_checked=True,
        dashboard_review="PASS", steering_wheel_review="PASS",
        manual_geometry_review="PASS", outside_cockpit_geometry_edit_count=0,
        texture_work_count=0,
    )
    return q, ev


class TwoLaneCockpitTests(unittest.TestCase):
    def test_seed_owns_two_distinct_cars_and_skips_dino(self):
        active = validate(copy.deepcopy(SEED))
        self.assertEqual(active["A"]["id"], "daytona365")
        self.assertEqual(active["C"]["id"], "f50")
        self.assertEqual(SEED["cars"][1]["status"], "SKIPPED_DONE_BY_USER")
        self.assertEqual(SEED["slots"]["A"]["schedule_minutes"], [0, 30])
        self.assertEqual(SEED["slots"]["C"]["schedule_minutes"], [15, 45])

    def test_reject_early_and_missing_photo_provenance(self):
        now = dt.datetime(2026, 11, 10, tzinfo=UTC)
        q, ev = ready(now)
        c = validate(q)["A"]
        c["started_at_utc"] = (now - dt.timedelta(hours=23)).isoformat()
        with self.assertRaisesRegex(ValueError, "24H"):
            advance(q, ev, now)
        c["started_at_utc"] = (now - dt.timedelta(hours=25)).isoformat()
        ev["reference_photo_urls"].pop("dashboard")
        with self.assertRaisesRegex(ValueError, "cockpit photo"):
            advance(q, ev, now)

    def test_reject_smoke_or_unreviewed_wheel_and_external_parts(self):
        now = dt.datetime(2026, 11, 10, tzinfo=UTC)
        q, ev = ready(now, slot="C")
        ev["blender_mode"] = "smoke"
        with self.assertRaisesRegex(ValueError, "real-scene"):
            advance(q, ev, now, slot="C")
        ev["blender_mode"] = "audit"
        ev["steering_wheel_review"] = "UNTESTED"
        with self.assertRaisesRegex(ValueError, "P0"):
            advance(q, ev, now, slot="C")
        ev["steering_wheel_review"] = "PASS"
        ev["outside_cockpit_geometry_edit_count"] = 1
        with self.assertRaisesRegex(ValueError, "external/body"):
            advance(q, ev, now, slot="C")

    def test_advance_A_then_C_is_separate_and_skips_dino(self):
        now = dt.datetime(2026, 11, 10, tzinfo=UTC)
        q, ev = ready(now, slot="A")
        self.assertEqual(advance(q, ev, now, slot="A"), "360spider")
        self.assertEqual(validate(q)["A"]["id"], "360spider")
        self.assertEqual(validate(q)["C"]["id"], "f50")
        new_c = validate(q)["C"]
        new_c.update(started_at_utc=(now - dt.timedelta(hours=25)).isoformat(),
                     geometry_gate="PASS", reference_gate="PASS",
                     source_scene_sha256="a" * 64, output_scene_sha256="b" * 64)
        ev_c = dict(ev, car_id="f50", slot="C")
        self.assertEqual(advance(q, ev_c, now, slot="C"), "f355spider")
        self.assertEqual(validate(q)["C"]["id"], "f355spider")
        self.assertEqual(q["cars"][1]["status"], "SKIPPED_DONE_BY_USER")

    def test_no_double_assignment_and_no_implicit_skip(self):
        q = copy.deepcopy(SEED)
        q["active_by_slot"]["C"] = "daytona365"
        with self.assertRaisesRegex(ValueError, "one car"):
            validate(q)
        q = copy.deepcopy(SEED)
        q["cars"][1]["status"] = "PENDING"
        with self.assertRaisesRegex(ValueError, "Dino246"):
            validate(q)
        q = copy.deepcopy(SEED)
        q["slots"]["A"]["schedule_minutes"] = [15, 45]
        with self.assertRaisesRegex(ValueError, "00/30"):
            validate(q)

    def test_identical_scene_sha_cannot_complete(self):
        now = dt.datetime(2026, 11, 10, tzinfo=UTC)
        q, ev = ready(now)
        validate(q)["A"]["output_scene_sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "unchanged"):
            advance(q, ev, now)


if __name__ == "__main__":
    unittest.main()
