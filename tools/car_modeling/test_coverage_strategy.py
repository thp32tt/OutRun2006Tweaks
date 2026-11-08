import copy
import json
import unittest
from pathlib import Path

from coverage_strategy import (
    COMPONENTS, component_for_dispatch, recommended, validate, make_record,
)

ROOT = Path(__file__).resolve().parents[2]


def load():
    q = json.loads((ROOT / "docs/automation/FERRARI16_GEOMETRY_QUEUE.json").read_text(encoding="utf-8"))
    pack = json.loads((ROOT / "docs/automation/FERRARI_COCKPIT_WORKPACK_A_DAYTONA365.json").read_text(encoding="utf-8"))
    return q, pack


class BreadthCoverageTests(unittest.TestCase):
    def test_existing_daytona_does_not_start_wheel_again(self):
        q, pack = load()
        validate(q, pack, "A")
        self.assertEqual(recommended(pack), "center_console")
        self.assertEqual(pack["components"]["steering_wheel"]["status"], "P0_POLISH_HOLD")

    def test_other_slot_f50_is_separate_and_source_derived(self):
        q, _ = load()
        pack = json.loads((ROOT / "docs/automation/FERRARI_COCKPIT_WORKPACK_C_F50.json").read_text(encoding="utf-8"))
        validate(q, pack, "C")
        self.assertEqual(recommended(pack), "center_console")
        self.assertNotEqual(pack["migration_input_blend_sha256"],
                            q["cars"][0]["output_scene_sha256"])

    def test_two_sends_per_component_never_spin_around_wheel(self):
        self.assertEqual([component_for_dispatch(n) for n in range(18)],
                         [x for region in COMPONENTS for x in (region, region)])
        self.assertEqual(component_for_dispatch(500), "cross_cockpit_qa")

    def test_after_covered_console_move_to_controls(self):
        _, pack = load()
        ev = {
            "component": "center_console", "result": "COVERED_PARTIAL_QA",
            "original_game_resource_sha256": pack["original_game_resource_sha256"],
            "input_blend_sha256": "a" * 64,
            "output_blend_sha256": "b" * 64,
            "output_format": "blend", "export_format": None,
            "original_mesh_object_ids_edited": ["ORIGINAL_CONSOLE"],
            "blender_saved_and_reopened": True,
            "source_commit_sha": "c" * 40,
            "report_ref": "private evidence manifest only",
        }
        make_record(pack, ev)
        self.assertEqual(recommended(pack), "driver_controls")
        self.assertEqual(pack["components"]["center_console"]["status"], "COVERED_PARTIAL_QA")
        with self.assertRaisesRegex(ValueError, "order violation"):
            make_record(pack, ev)

    def test_block_missing_region_and_move_on_no_fabrication(self):
        _, pack = load()
        make_record(pack, dict(component="center_console", result="BLOCKED", reason="original source mesh missing"))
        self.assertEqual(recommended(pack), "driver_controls")
        self.assertNotEqual(pack["components"]["center_console"]["status"], "COVERED_PARTIAL_QA")

    def test_reject_fake_mesh_and_ocv(self):
        _, pack = load()
        evidence = {
            "component": "center_console", "result": "COVERED_PARTIAL_QA",
            "original_game_resource_sha256": pack["original_game_resource_sha256"],
            "input_blend_sha256": "a" * 64, "output_blend_sha256": "b" * 64,
            "output_format": "blend", "original_mesh_object_ids_edited": ["ORIGINAL_CONSOLE"],
            "blender_saved_and_reopened": True,
        }
        for extra in ({"export_format": "ovc3"}, {"from_scratch_car": True},
                      {"game_integration_performed": True}, {"blender_saved_and_reopened": False}):
            wrong = copy.deepcopy(pack)
            with self.assertRaises(ValueError):
                make_record(wrong, dict(evidence, **extra))

    def test_p0_not_revisited_until_coveraged_gaps_done(self):
        _, pack = load()
        for name in COMPONENTS[:6]:
            pack["components"][name]["status"] = "COVERED_PARTIAL_QA"
        self.assertEqual(recommended(pack), "cross_cockpit_qa")
        pack["components"]["dashboard"]["status"] = "IN_PROGRESS"
        self.assertEqual(recommended(pack), "dashboard")
        pack["components"]["dashboard"]["status"] = "COVERED_PARTIAL_QA"
        pack["components"]["steering_wheel"]["status"] = "IN_PROGRESS"
        self.assertEqual(recommended(pack), "steering_wheel")


if __name__ == "__main__":
    unittest.main()
