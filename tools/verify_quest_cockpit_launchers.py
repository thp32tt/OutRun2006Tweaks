#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
LAUNCHERS = (
    "RUN-QUEST-COCKPIT-V2.cmd",
    "RUN-QUEST-COCKPIT-V2-F0.cmd",
    "RUN-QUEST-COCKPIT-V2-LOD0.cmd",
    "RUN-QUEST-COCKPIT-V2-INTERP-OFF.cmd",
    "RUN-QUEST-COCKPIT-V2-SKY-DIAG.cmd",
    "RUN-QUEST-COCKPIT-V2-TURN-DIAG.cmd",
)

errors = []
for name in LAUNCHERS:
    path = ROOT / name
    if not path.is_file():
        errors.append(f"missing launcher: {name}")
        continue
    text = path.read_text(encoding="utf-8")
    if r"\n" in text:
        errors.append(f"literal backslash-n found: {name}")
    if "-QuestCockpitV2F0 ON" not in text:
        errors.append(f"F0 ON missing: {name}")
    if r"tools\Run-OutRunVRTest.ps1" not in text:
        errors.append(f"source runner fallback missing: {name}")

runner_path = ROOT / "tools" / "Run-OutRunVRTest.ps1"
if not runner_path.is_file():
    errors.append("missing tools/Run-OutRunVRTest.ps1")
else:
    runner = runner_path.read_text(encoding="utf-8")
    for parameter in (
        "QuestCockpitV2",
        "QuestCockpitV2F0",
        "QuestCockpitV2SkyProbe",
        "QuestCockpitV2Interpolation",
    ):
        if not re.search(r"\$" + re.escape(parameter) + r"\b", runner):
            errors.append(f"runner parameter missing: {parameter}")

if errors:
    for error in errors:
        print(f"FAIL: {error}")
    sys.exit(1)

print("PASS: Quest cockpit launchers keep F0 ON, valid line breaks, and runner fallback.")
