"""VR Docker dispatch cadence regression tests (00/20/40 KST)."""
import ast
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "".join(p.read_text(encoding="utf-8") for p in sorted((ROOT / "src-vr-v2").glob("controller.py.part*")))
TZ = ZoneInfo("Asia/Seoul")


def due(enabled=True):
    tree = ast.parse(SOURCE)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
              and n.name == "vr_scheduled_dispatch_due")
    ns = {"VR_SCHEDULED_DISPATCH_ENABLED": enabled, "SCHEDULE_MINUTES": [0, 20, 40], "datetime": datetime}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "<schedule>", "exec"), ns)
    return ns["vr_scheduled_dispatch_due"]


class ScheduledDispatchTests(unittest.TestCase):
    def test_only_three_start_minutes(self):
        for minute in range(60):
            with self.subTest(minute=minute):
                self.assertEqual(due()({}, "C", datetime(2026, 10, 22, 8, minute, 15, tzinfo=TZ)),
                                 minute in {0, 20, 40})

    def test_no_same_window_repeat_even_if_task_finishes(self):
        q = {"vr_scheduled_dispatch_windows": {"C": "2026-10-22T08:20"}}
        self.assertFalse(due()(q, "C", datetime(2026, 10, 22, 8, 20, 55, tzinfo=TZ)))
        self.assertFalse(due()(q, "C", datetime(2026, 10, 22, 8, 21, tzinfo=TZ)))
        self.assertTrue(due()(q, "C", datetime(2026, 10, 22, 8, 40, tzinfo=TZ)))
        self.assertTrue(due()(q, "A", datetime(2026, 10, 22, 8, 20, tzinfo=TZ)))
        self.assertTrue(due()(q, "C", datetime(2026, 10, 22, 9, 20, tzinfo=TZ)))

    def test_opt_out_preserves_other_controller_modes(self):
        self.assertTrue(due(False)({}, "C", datetime(2026, 10, 22, 8, 7, tzinfo=TZ)))

    def test_integrated_send_and_rollover_gates(self):
        tree = ast.parse(SOURCE)
        send = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)
                    and n.name == "conversion_send_lane_task")
        s = ast.get_source_segment(SOURCE, send)
        self.assertGreaterEqual(s.count("vr_scheduled_dispatch_due(q, slot_name,"), 2)
        self.assertIn("vr_scheduled_dispatch_windows", s)
        rollover = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)
                        and n.name == "vr_checkpoint_and_rollover")
        self.assertIn("now.minute in SCHEDULE_MINUTES", ast.get_source_segment(SOURCE, rollover))
        yml = (ROOT / "docker-compose.portainer-vr.yml").read_text(encoding="utf-8")
        for snippet in ('VR_SCHEDULED_DISPATCH_ENABLED: "true"',
                        'SCHEDULE_MINUTES: "0,20,40"', 'DX9EX_REVIEW_ONLY: "true"'):
            self.assertIn(snippet, yml)


if __name__ == "__main__":
    unittest.main()
