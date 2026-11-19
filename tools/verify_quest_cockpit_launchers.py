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

    for required in (
        "'-VR.AutoRenderResolution=false'",
        "'-VR.RenderWidth=2496'",
        "'-VR.RenderHeight=2688'",
    ):
        if required not in runner:
            errors.append(f"release-parity fixed Quest3 eye resolution missing: {required}")
    if "'-VR.AutoRenderResolution=true'" in runner:
        errors.append("release-parity still forces OpenXR auto eye resolution")

release_version_path = ROOT / "VR_RELEASE_VERSION.txt"
if not release_version_path.is_file():
    errors.append("missing release version file: VR_RELEASE_VERSION.txt")
else:
    release_version = release_version_path.read_text(encoding="utf-8")
    if "v0.03" not in release_version:
        errors.append("VR_RELEASE_VERSION.txt is not v0.03")

release_workflow_path = ROOT / ".github" / "workflows" / "vr-github-general-build.yml"
if not release_workflow_path.is_file():
    errors.append("missing release workflow: vr-github-general-build.yml")
else:
    release_workflow = release_workflow_path.read_text(encoding="utf-8")
    if "-notmatch 'v0\\.03'" not in release_workflow:
        errors.append("v0.03 packaging gate does not require v0.03 release version")
    if "-notmatch 'v0\\.02'" in release_workflow:
        errors.append("v0.03 packaging gate still checks stale v0.02 version")

release_path = ROOT / "Start-OutRun.cmd"
if not release_path.is_file():
    errors.append("missing release launcher: Start-OutRun.cmd")
else:
    release = release_path.read_text(encoding="utf-8")
    for required in (
        "-VR.AutoRenderResolution=false",
        "-VR.RenderWidth=2496",
        "-VR.RenderHeight=2688",
    ):
        if required not in release:
            errors.append(f"release launcher fixed Quest3 eye resolution missing: {required}")
    if "-VR.AutoRenderResolution=true" in release:
        errors.append("release launcher still forces OpenXR auto eye resolution")

if errors:
    for error in errors:
        print(f"FAIL: {error}")
    sys.exit(1)

print("PASS: Quest cockpit launchers keep F0 ON, fixed 2496x2688 release eyes, valid line breaks, and runner fallback.")
