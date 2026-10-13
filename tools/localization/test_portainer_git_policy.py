"""Read-only regression checks for Git-based Portainer one-A smoke overlays.

These tests never connect to Portainer, launch containers, or edit a running stack.
"""
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
TARGET = "outrun-chat-controller-localization-recovery"
DIR = ROOT / "docker/localization-production"
SMOKE = DIR / "portainer-git-q217-a-smoke.override.yml"
NORMAL = DIR / "portainer-git-normal.override.yml"
TASK = "OUTRUN-A-Q217-IMG-SMOKE-20261013"


class PortainerGitPolicyTests(unittest.TestCase):
    def read(self, path):
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertEqual(set(value), {"services"})
        self.assertEqual(set(value["services"]), {TARGET})
        service = value["services"][TARGET]
        self.assertEqual(set(service), {"environment"})
        env = service["environment"]
        self.assertEqual(set(env), {"AUTO_SEND", "CHAT_SLOTS", "SCHEDULE_MINUTES", "OUTRUN_A_SINGLE_SMOKE_TASK_ID"})
        self.assertEqual(env["AUTO_SEND"], "true")
        self.assertEqual(env["CHAT_SLOTS"], "3")
        return env

    def test_one_a_smoke_only(self):
        env = self.read(SMOKE)
        self.assertEqual(env["SCHEDULE_MINUTES"], "0")
        self.assertEqual(env["OUTRUN_A_SINGLE_SMOKE_TASK_ID"], TASK)

    def test_normal_restore(self):
        env = self.read(NORMAL)
        self.assertEqual(env["SCHEDULE_MINUTES"], "0,10,30,40")
        self.assertEqual(env["OUTRUN_A_SINGLE_SMOKE_TASK_ID"], "")

    def test_no_build_or_lifecycle_mutation_in_overlays(self):
        for path in (SMOKE, NORMAL):
            with self.subTest(path=str(path)):
                text = path.read_text(encoding="utf-8")
                # Explicitly disallow structural Compose changes to a pre-existing Portainer stack.
                keys = set(yaml.safe_load(text)["services"][TARGET])
                self.assertNotIn("image", keys)
                self.assertNotIn("build", keys)
                self.assertNotIn("volumes", keys)
                self.assertNotIn("container_name", keys)
                self.assertNotIn("ports", keys)


if __name__ == "__main__":
    unittest.main()
