import ast
import re
import unittest
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "\n".join(
    (ROOT / "src" / f"controller.py.part{i:02d}").read_text(encoding="utf-8")
    for i in range(4)
)
TREE = ast.parse(SOURCE)

NAMES = {
    "Slot",
    "TaskEvent",
    "Registry",
    "allocate_lane_production_id",
    "production_id_from_identifier",
    "next_task_event_id",
    "append_task_event",
    "_task_records",
}
selected = [node for node in TREE.body if getattr(node, "name", None) in NAMES]
module = ast.Module(body=selected, type_ignores=[])
ast.fix_missing_locations(module)

ns = {
    "dataclass": dataclass,
    "asdict": asdict,
    "field": field,
    "datetime": datetime,
    "Optional": Optional,
    "ZoneInfo": ZoneInfo,
    "TZ": ZoneInfo("Asia/Seoul"),
    "re": re,
    "PRODUCTION_COUNTER_MODE": "lane",
}
exec(compile(module, "<controller-v2-subset>", "exec"), ns)


class ControllerV2EventModelTests(unittest.TestCase):
    def setUp(self):
        Registry = ns["Registry"]
        self.reg = Registry(
            logical_date="2026-10-03",
            next_slot=0,
            slots=[],
            next_production_id={"LOCALIZATION_B": 491},
            task_events=[],
        )

    def test_rollover_retry_do_not_consume_production_number(self):
        allocate = ns["allocate_lane_production_id"]
        append = ns["append_task_event"]

        production_id = allocate(self.reg, "LOCALIZATION_B", "LOCALIZATION", 491)
        active = {
            "task_id": production_id,
            "production_id": production_id,
            "attempt": 1,
            "retry_count": 0,
            "rollover_count": 0,
            "chat_rollovers": 0,
        }

        append(self.reg, active, "dispatch")
        active["rollover_count"] = 1
        active["chat_rollovers"] = 1
        append(self.reg, active, "rollover")
        append(self.reg, active, "continue")
        active["rollover_count"] = 2
        active["chat_rollovers"] = 2
        append(self.reg, active, "rollover")
        active["retry_count"] = 1
        append(self.reg, active, "retry")
        active["retry_count"] = 2
        append(self.reg, active, "retry")

        self.assertEqual(production_id, "LOCALIZATION-LOCALIZATION_B-00491")
        self.assertEqual(
            [e.event_id for e in self.reg.task_events],
            [f"{production_id}-E{i:03d}" for i in range(1, 7)],
        )
        self.assertEqual(self.reg.next_production_id["LOCALIZATION_B"], 492)

    def test_next_new_dispatch_is_next_production_number(self):
        allocate = ns["allocate_lane_production_id"]
        first = allocate(self.reg, "LOCALIZATION_B", "LOCALIZATION", 491)
        second = allocate(self.reg, "LOCALIZATION_B", "LOCALIZATION", 491)
        self.assertTrue(first.endswith("-00491"))
        self.assertTrue(second.endswith("-00492"))

    def test_event_identifier_resolves_to_same_production_record(self):
        production_from = ns["production_id_from_identifier"]
        records = ns["_task_records"]
        production_id = "LOCALIZATION-LOCALIZATION_B-00491"
        event_id = production_id + "-E002"
        payload = {
            "production_id": production_id,
            "event_id": event_id,
            "event_type": "rollover",
        }
        self.assertEqual(production_from(event_id), production_id)
        self.assertEqual(list(records(payload, event_id)), [payload])


if __name__ == "__main__":
    unittest.main()
