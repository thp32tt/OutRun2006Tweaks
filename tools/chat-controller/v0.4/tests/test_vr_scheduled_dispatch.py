"""VR Docker lane schedule regression tests: DX11 :00/:20/:40, DX9Ex :00 KST."""
import ast
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "".join(p.read_text(encoding="utf-8") for p in sorted((ROOT / "src-vr-v2").glob("controller.py.part*")))
TZ = ZoneInfo("Asia/Seoul")


def due(enabled=True, mode="conversion"):
    tree = ast.parse(SOURCE)
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)
             and n.name in {"vr_lane_schedule_window_due", "vr_scheduled_dispatch_due"}]
    assert len(funcs) == 2
    ns = {"VR_SCHEDULED_DISPATCH_ENABLED": enabled,
          "SCHEDULE_MINUTES": [0, 20, 40],
          "DX9EX_SCHEDULE_MINUTES": [0],
          "CONTROLLER_MODE": mode,
          "datetime": datetime}
    exec(compile(ast.Module(body=funcs, type_ignores=[]), "<schedule>", "exec"), ns)
    return ns["vr_scheduled_dispatch_due"], ns["vr_lane_schedule_window_due"]


class ScheduledDispatchTests(unittest.TestCase):
    def test_dx9ex_only_top_of_hour(self):
        dispatch, window = due()
        for minute in range(60):
            now = datetime(2026, 10, 22, 8, minute, 15, tzinfo=TZ)
            with self.subTest(minute=minute):
                self.assertEqual(dispatch({}, "C", now), minute == 0)
                self.assertEqual(window("C", now), minute == 0)

    def test_dx11_shared_schedule_unchanged(self):
        dispatch, window = due()
        for minute in range(60):
            now = datetime(2026, 10, 22, 8, minute, 15, tzinfo=TZ)
            with self.subTest(minute=minute):
                self.assertEqual(dispatch({}, "A", now), minute in {0, 20, 40})
                self.assertEqual(window("A", now), minute in {0, 20, 40})

    def test_dx9ex_deduplicates_and_rearms_next_hour(self):
        dispatch, _ = due()
        q = {"vr_scheduled_dispatch_windows": {"C": "2026-10-22T08:00"}}
        self.assertFalse(dispatch(q, "C", datetime(2026, 10, 22, 8, 0, 55, tzinfo=TZ)))
        self.assertFalse(dispatch(q, "C", datetime(2026, 10, 22, 8, 20, tzinfo=TZ)))
        self.assertFalse(dispatch(q, "C", datetime(2026, 10, 22, 8, 40, tzinfo=TZ)))
        self.assertTrue(dispatch(q, "C", datetime(2026, 10, 22, 9, 0, tzinfo=TZ)))
        self.assertTrue(dispatch(q, "A", datetime(2026, 10, 22, 8, 20, tzinfo=TZ)))

    def test_dx9ex_hourly_even_global_schedule_disabled(self):
        dispatch, _ = due(False)
        self.assertFalse(dispatch({}, "C", datetime(2026, 10, 22, 8, 20, tzinfo=TZ)))
        self.assertTrue(dispatch({}, "C", datetime(2026, 10, 22, 8, 0, tzinfo=TZ)))
        q = {"vr_scheduled_dispatch_windows": {"C": "2026-10-22T08:00"}}
        self.assertFalse(dispatch(q, "C", datetime(2026, 10, 22, 8, 0, tzinfo=TZ)))
        self.assertTrue(dispatch({}, "A", datetime(2026, 10, 22, 8, 7, tzinfo=TZ)))

    def test_localization_unaffected(self):
        dispatch, _ = due(False, "localization")
        self.assertTrue(dispatch({}, "C", datetime(2026, 10, 22, 8, 7, tzinfo=TZ)))

    def test_integrated_send_rollover_and_compose(self):
        tree = ast.parse(SOURCE)
        send = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)
                    and n.name == "conversion_send_lane_task")
        code = ast.get_source_segment(SOURCE, send)
        self.assertGreaterEqual(code.count("vr_scheduled_dispatch_due(q, slot_name,"), 2)
        self.assertIn("vr_scheduled_dispatch_windows", code)
        self.assertIn('CONTROLLER_MODE == "conversion" and slot_name == "C"', code)
        rollover = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)
                        and n.name == "vr_checkpoint_and_rollover")
        self.assertIn("vr_lane_schedule_window_due", ast.get_source_segment(SOURCE, rollover))
        yml = (ROOT / "docker-compose.portainer-vr.yml").read_text(encoding="utf-8")
        for snippet in ('VR_SCHEDULED_DISPATCH_ENABLED: "true"',
                        'SCHEDULE_MINUTES: "0,20,40"',
                        'DX9EX_SCHEDULE_MINUTES: "0"',
                        'DX9EX_REVIEW_ONLY: "true"'):
            self.assertIn(snippet, yml)


if __name__ == "__main__":
    unittest.main()
