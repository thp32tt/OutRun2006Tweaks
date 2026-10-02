import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Pipeline:
    config: dict

    def _queue(self):
        return Path(self.config["queue"])

    def run(self):
        if self.config.get("mode") != "localization":
            raise RuntimeError("non-localization mode rejected")
        if self.config.get("pipeline") != ["A", "B", "C"]:
            raise RuntimeError("Localization pipeline must be A_B_THEN_C_BARRIER")

        with self._queue().open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))

        producers = {
            "A": [r for r in rows if int(r["index"]) % 2 == 0],
            "B": [r for r in rows if int(r["index"]) % 2 == 1],
        }

        return {
            "status": "READY",
            "producer_lanes": {k: len(v) for k, v in producers.items()},
            "barrier": "C",
            "next_wave_locked_until_qa": True,
        }
