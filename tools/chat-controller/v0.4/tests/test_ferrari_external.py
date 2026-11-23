"""Pure admission/dispatch regressions for external Ferrari16 automation."""
import importlib.util
from pathlib import Path
import unittest

_SOURCE = Path(__file__).resolve().parents[1] / "ferrari_external.py"
_spec = importlib.util.spec_from_file_location("ferrari_external_under_test", _SOURCE)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

REPO = "thp32tt/OutRun2006Tweaks"
BRANCH = "automation/ferrari16-external-20261123"


def fixture():
    return {
        "schema_version": 1,
        "repository": REPO,
        "target_branch": BRANCH,
        "one_owner_slot": "A",
        "cadence_kst_minutes": [0, 30],
        "active_work_id": "EXT16-001",
        "work": [{"id": "EXT16-001", "stage": "source_fix", "status": "ACTIVE",
                  "title": "both-eye stereo", "acceptance": ["left+right exact-SHA"]}],
    }


class ExternalModelQueueTests(unittest.TestCase):
    def test_active_model_is_selected(self):
        self.assertEqual(_module.choose_external_work(fixture(), REPO, BRANCH)["id"], "EXT16-001")

    def test_old_cockpit_repo_rejected(self):
        with self.assertRaises(ValueError):
            _module.choose_external_work(fixture(), "thp32tt/imsi1", "main")

    def test_wrong_branch_rejected(self):
        with self.assertRaises(ValueError):
            _module.choose_external_work(fixture(), REPO, "vr-d3d9ex-focus")

    def test_duplicate_work_id_rejected(self):
        queue = fixture()
        queue["work"].append(dict(queue["work"][0]))
        with self.assertRaises(ValueError):
            _module.choose_external_work(queue, REPO, BRANCH)

    def test_no_completed_work_dispatch(self):
        queue = fixture()
        queue["work"][0]["status"] = "COMPLETE_STATIC"
        self.assertIsNone(_module.choose_external_work(queue, REPO, BRANCH))

    def test_no_quest_hmd_auto_pass(self):
        queue = fixture()
        queue["work"][0]["requires_user_headset"] = True
        self.assertIsNone(_module.choose_external_work(queue, REPO, BRANCH))

    def test_no_cross_project_car_owner(self):
        queue = fixture()
        queue["one_owner_slot"] = "C"
        with self.assertRaises(ValueError):
            _module.choose_external_work(queue, REPO, BRANCH)

    def test_prompt_keeps_same_id_and_hardware_untested(self):
        queue = fixture()
        work = _module.choose_external_work(queue, REPO, BRANCH)
        text = _module.make_external_prompt(work, queue, "f" * 40, True)
        self.assertIn("TASK_ID=EXT16-001", text)
        self.assertIn("CONTINUATION=1", text)
        self.assertIn("RUNTIME_VALIDATION=UNTESTED", text)
        self.assertIn("left+right exact-SHA", text)


if __name__ == "__main__":
    unittest.main()
