import copy
import datetime as dt
import json
import unittest
from pathlib import Path

from queue_guard import advance, check_evidence, validate

UTC = dt.timezone.utc
ROOT = Path(__file__).resolve().parents[2]
SEED = json.loads(
    (ROOT / "docs/automation/FERRARI16_GEOMETRY_QUEUE.json").read_text(encoding="utf-8")
)


class GeometryQueueTests(unittest.TestCase):
    def test_seed(self):
        self.assertEqual(validate(copy.deepcopy(SEED))["id"], "daytona365")

    def test_reject_early_and_missing_photos(self):
        q = copy.deepcopy(SEED)
        now = dt.datetime(2026, 11, 9, tzinfo=UTC)
        active = q["cars"][0]
        active["started_at_utc"] = (now - dt.timedelta(hours=23)).isoformat()
        active["geometry_gate"] = "PASS"
        active["reference_gate"] = "PASS"
        active["source_scene_sha256"] = "a" * 64
        active["output_scene_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "24H"):
            advance(q, {}, now)
        active["started_at_utc"] = (now - dt.timedelta(hours=25)).isoformat()
        with self.assertRaisesRegex(ValueError, "physical geometry"):
            advance(q, {"car_id": "daytona365"}, now)

    def test_advance_requires_genuine_audit_and_six_views(self):
        q = copy.deepcopy(SEED)
        now = dt.datetime(2026, 11, 10, tzinfo=UTC)
        car = q["cars"][0]
        car.update(started_at_utc=(now - dt.timedelta(hours=25)).isoformat(),
                   geometry_gate="PASS", reference_gate="PASS",
                   source_scene_sha256="a" * 64, output_scene_sha256="b" * 64)
        ev = dict(car_id="daytona365", material_commit_count=2,
                  verified_blender_run_id="12345", blender_mode="smoke",
                  real_render_views={v: "artifact" for v in ("front","rear","left","right","top","cockpit")},
                  reference_photo_urls={v: "https://example.org/real-photo" for v in
                                        ("front","rear","left","right","top","cockpit")},
                  manual_geometry_review="PASS", texture_work_count=0)
        with self.assertRaisesRegex(ValueError, "smoke"):
            advance(q, ev, now)
        ev["blender_mode"] = "audit"
        ev["reference_photo_urls"].pop("top")
        with self.assertRaisesRegex(ValueError, "photo"):
            advance(q, ev, now)
        ev["reference_photo_urls"]["top"] = "https://example.org/real-photo"
        self.assertEqual(advance(q, ev, now), "dino246gts")
        self.assertEqual(validate(q)["id"], "dino246gts")
        self.assertEqual(q["cars"][0]["status"], "COMPLETE")
        self.assertIsNone(q["cars"][1]["started_at_utc"])

    def test_no_parallel_and_no_reordered_complete(self):
        q = copy.deepcopy(SEED)
        q["cars"][2]["status"] = "ACTIVE"
        with self.assertRaisesRegex(ValueError, "parallel"):
            validate(q)
        q = copy.deepcopy(SEED)
        q["cars"][2]["status"] = "COMPLETE"
        with self.assertRaisesRegex(ValueError, "sequential"):
            validate(q)


if __name__ == "__main__":
    unittest.main()
