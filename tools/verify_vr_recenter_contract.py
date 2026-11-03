#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")

def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise SystemExit(f"FAIL: {label}: missing marker {marker!r}")

def require_before(text: str, first: str, second: str, label: str) -> None:
    a = text.find(first)
    b = text.find(second)
    if a < 0 or b < 0 or a >= b:
        raise SystemExit(
            f"FAIL: {label}: expected {first!r} before {second!r}"
        )

recenter = read("vrhost/src/runtime/r26_recenter_hardening.hpp")
host = read("vrhost/src/main_r23.cpp")
cmake = read("vrhost/CMakeLists.txt")
workflow = read(".github/workflows/vr-openxr.yml")
ipc_smoke = read("vrhost/tests/recenter_ipc_smoke.cpp")
work_queue = json.loads(read("docs/VR_WORK_QUEUE.json"))

require(
    cmake,
    '"/FI${CMAKE_CURRENT_LIST_DIR}/src/runtime/r26_recenter_hardening.hpp"',
    "host forced-include",
)

for marker, label in [
    ("PendingApplicationRecenter.store(true", "pending recenter queue"),
    ("OutRunVrFinalTest::BaseLocalSpace", "immutable runtime LOCAL base"),
    ("::xrLocateSpace(viewSpace, base, displayTime, &location)", "current HMD pose locate"),
    ("create.referenceSpaceType = XR_REFERENCE_SPACE_TYPE_LOCAL", "LOCAL reference-space creation"),
    ("create.poseInReferenceSpace = location.pose", "current-pose application origin"),
    ("localSpace = recentered", "host local-space replacement"),
    ("OutRunVrFinalTest::LocalSpace = recentered", "fallback local-space replacement"),
    ("if (previous != XR_NULL_HANDLE && previous != base)", "immutable base lifetime guard"),
]:
    require(recenter, marker, label)

require_before(
    host,
    "OutRunVrR26RecenterHardening::ApplyPendingApplicationRecenter(",
    "xrLocateSpace(viewSpace, localSpace, fs.predictedDisplayTime, &head)",
    "recenter-before-head-locate",
)
require_before(
    host,
    "OutRunVrR26RecenterHardening::ApplyPendingApplicationRecenter(",
    "vl.space = localSpace",
    "recenter-before-view-locate",
)

for marker, label in [
    ("quad.space = OutRunVrFinalTest::LocalSpace", "LOCAL startup fallback"),
    ("const bool r24ViewFallback =", "R24 VIEW fallback detection"),
    ("XR_SUCCEEDED(result) && !r24ViewFallback", "successful non-VIEW completion gate"),
    ("ApplicationRecenterAppliedForPendingGameRequest()", "generation completion gate"),
    ("PendingGameTargetGeneration.store(0", "generation target clear after completion"),
]:
    require(recenter, marker, label)

for marker, label in [
    ("PendingGameTargetGeneration.store(", "game request target generation"),
    ("QueueApplicationRecenter();", "game request queues application recenter"),
    ("WriteSyntheticLocalChange(eventData, XR_NULL_HANDLE)", "synthetic LOCAL change"),
    ("change->referenceSpaceType = XR_REFERENCE_SPACE_TYPE_LOCAL", "runtime change normalization"),
]:
    require(recenter, marker, label)

for marker, label in [
    ("add_executable(outrun-vr-recenter-ipc-smoke", "recenter IPC smoke build target"),
]:
    require(cmake, marker, label)

for marker, label in [
    ("Run recenter IPC request/ack round-trip", "recenter IPC CI step"),
    ("outrun-vr-recenter-ipc-smoke.exe", "recenter IPC CI executable"),
]:
    require(workflow, marker, label)

for marker, label in [
    ("channel.Publish()", "IPC publish"),
    ("channel.ConsumeEventSignal()", "IPC event signal"),
    ("channel.Pending(", "IPC pending observation"),
    ("channel.MarkReceived(", "IPC receive acknowledgement"),
    ("channel.MarkApplied(", "IPC applied acknowledgement"),
    ("GetCurrentProcessId()", "IPC requester identity"),
]:
    require(ipc_smoke, marker, label)

recenter_items = [item for item in work_queue.get("items", []) if item.get("id") == "L1-RECENTER-001"]
if len(recenter_items) != 1:
    raise SystemExit("FAIL: expected exactly one L1-RECENTER-001 work-queue item")
recenter_item = recenter_items[0]
for key, expected in [
    ("status", "NEED_HMD_TEST"),
    ("automationValidation", "PASS"),
    ("runtimeValidation", "UNTESTED"),
    ("lastAutomationTaskId", "CONVERSION-DXVK-00041"),
    ("lastAutomationResultSha", "9fba9fe1e54f1d2f474820560d42546f00051106"),
]:
    actual = recenter_item.get(key)
    if actual != expected:
        raise SystemExit(
            f"FAIL: recenter queue reconciliation: {key}={actual!r}, expected {expected!r}"
        )
if recenter_item.get("attempts", 0) < 1:
    raise SystemExit("FAIL: recenter queue reconciliation: attempts must record automated coverage")

print("PASS: application-space recenter contract, IPC smoke, and HMD queue gate are wired and fail-closed")
