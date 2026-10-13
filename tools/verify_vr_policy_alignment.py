#!/usr/bin/env python3
"""DX9Ex source-of-truth policy precedence guard, with seven fail-closed mutations."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = "fcd18ddd89f6dd40a8246fcf8591f086811149f1"
STAGES = ["P0_A_USER_REPORTED_RESPONSIVE_HUD_MENU_F11_ISSUE_119", "P0_B_MEASURED_PERFORMANCE_PARALLEL", "P1_OTHER_CONFIRMED_VISUAL_REGRESSIONS", "P2_XR_PER_EYE_RESOLUTION", "P3_MINOR_CLEANUP_DEFERRED"]


def violations(state, queue, docs):
    sa = state["policy"]["executionAuthority"]
    qa = queue["policy"]["executionAuthority"]
    visual = next((item for item in queue.get("items", [])
                   if item.get("id") == "DX9EX-P0-VISUAL-COMPOSITION-20261007"), None)
    p0_ui = next((item for item in queue.get("items", [])
                  if item.get("id") == "DX9EX-QUEST3-RESPONSIVE-UI-20261013"), None)
    v3_gate = next((item for item in queue.get("items", [])
                    if item.get("id") == "ARCH-V3-GATE-001"), None)
    v3_start = next((item for item in queue.get("items", [])
                     if item.get("id") == "ARCH-V3-001"), None)
    # The 2026-10-13 whole-defect override decomposes Issue #119 into
    # four independently owned, dispatchable visual functions. The umbrella
    # remains a tracking-only parent; making it READY creates two writers
    # for the same renderer paths and invalidates the live child claims.
    child_keys = (
        "DX9EX:VIS:HUD_GAMEPLAY", "DX9EX:VIS:F11_MENU",
        "DX9EX:VIS:ESC_MENU", "DX9EX:VIS:MAIN_MENU",
    )
    child_items = [item for item in queue.get("items", [])
                   if item.get("workKey") in child_keys]
    child_dispatch_ok = (
        p0_ui is not None and
        p0_ui.get("status") == "DECOMPOSED_PARENT_TRACKING_ONLY" and
        p0_ui.get("workKey") == "DX9EX-QUEST3-RESPONSIVE-UI-20261013" and
        p0_ui.get("issue") == 119 and
        sorted(p0_ui.get("childFeatureIds", [])) == sorted(child_keys) and
        len(p0_ui.get("childFeatureIds", [])) == len(child_keys) and
        len(child_items) == len(child_keys) and
        all(item.get("featureId") == item.get("workKey") and
            item.get("id") == "DX9EX-FEATURE-" + item["workKey"].rsplit(":", 1)[-1] and
            item.get("status") in ("READY", "IMPLEMENT_NEXT", "NEEDS_VALIDATION", "IN_PROGRESS") and
            item.get("priority", 0) >= 120 and not item.get("blockedBy")
            for item in child_items)
    )
    checks = (
        (sa == qa, "DX9Ex state/queue diverged"),
        (sa["roles"]["A"]["status"] == "ACTIVE" and sa["roles"]["A"]["globalPriority"] == 0, "DX11 A not first-priority ACTIVE"),
        (sa["roles"]["C"]["status"] == "ACTIVE" and sa["roles"]["C"]["effortTargetPercent"] == 50, "DX9Ex C allocation/state changed"),
        (sa["roles"]["B"]["status"] == "FROZEN" and not sa["autoThawDxvk"], "DXVK B thawed"),
        (sa["dx9exPriority"] == STAGES, "2026-10-13 P0-A responsive UI / P0-B performance priority lost"),
        (child_dispatch_ok,
         "P0-A issue 119 must keep a tracking-only parent and four independent dispatchable child work keys"),
        (visual is not None and visual.get("status") == "READY"
         and not visual.get("blockedBy")
         and "non-overlapping active claim" in visual.get("nextAction", ""),
         "independent P0 optics/HUD source work incorrectly blocked or lacks ownership fencing"),
        (v3_gate is not None and v3_gate.get("status") == "NEED_HMD_TEST"
         and v3_start is not None and v3_start.get("status") == "BLOCKED",
         "Architecture v3 live IPC migration HMD gate prematurely opened"),
        (sa["protectedBaseline"] == PIN, "DX9Ex rollback baseline changed"),
        (state["policy"]["parallelBackendDevelopment"]["enabled"] and queue["policy"]["parallelBackendDevelopment"], "A/C parallel source work disabled"),
        (not queue["policy"]["exclusiveFocus"]["enabled"], "historical R84 exclusivity restored"),
        (not any("DX11" in item for item in state["policy"]["blockedBackends"]), "DX11 Native incorrectly frozen"),
        (not any("DX11" in item for item in state["p0VisualComposition"]["blockedUntilStaticGreen"]), "visual P0 blocks DX11 Native"),
        ("Architecture v3" in queue["policy"]["backendReplacementGate"], "Architecture v3 lane-local gate missing"),
        ("## Effective multi-lane dispatch authority" in docs["controller"], "controller precedence missing"),
        ("# Effective backend execution policy" in docs["agents"], "AGENTS precedence missing"),
        (all(phrase in docs["priority"] for phrase in (
            "# DX9Ex VR defect-first execution policy",
            "DX11 Native A remains global conversion priority",
            "DXVK B FROZEN",
            "FFB v0.2 and currently working gamepad/input are FROZEN",
            "R84/structural optimization",
        )), "priority-policy precedence missing"),
    )
    return [message for good, message in checks if not good]


def main():
    state = json.loads((ROOT / "docs/VR_AUTODEV_STATE.json").read_text(encoding="utf-8"))
    queue = json.loads((ROOT / "docs/VR_WORK_QUEUE.json").read_text(encoding="utf-8"))
    docs = {
        "agents": (ROOT / "AGENTS.md").read_text(encoding="utf-8"),
        "priority": (ROOT / "docs/DX9EX_AUTODEV_PRIORITY_20261010.md").read_text(encoding="utf-8"),
        "controller": (ROOT / "docs/automation/QUEUE_CONTROLLER_CONTRACT.md").read_text(encoding="utf-8"),
    }
    errors = violations(state, queue, docs)
    if errors:
        raise SystemExit("VR POLICY FAIL: " + "; ".join(errors))
    negative_cases = (
        lambda s, q: s["policy"]["parallelBackendDevelopment"].update(enabled=False),
        lambda s, q: q["policy"].update(parallelBackendDevelopment=False),
        lambda s, q: q["policy"]["exclusiveFocus"].update(enabled=True),
        lambda s, q: s["policy"]["blockedBackends"].append("DX11_NATIVE_DOWNSTREAM_PORT"),
        lambda s, q: s["policy"]["executionAuthority"]["roles"]["B"].update(status="ACTIVE"),
        lambda s, q: s["policy"]["executionAuthority"]["roles"]["C"].update(effortTargetPercent=10),
        lambda s, q: s["policy"]["executionAuthority"]["dx9exPriority"].reverse(),
        lambda s, q: next(item for item in q["items"] if item["id"] == "DX9EX-QUEST3-RESPONSIVE-UI-20261013").update(status="BLOCKED"),
        lambda s, q: next(item for item in q["items"] if item["id"] == "DX9EX-QUEST3-RESPONSIVE-UI-20261013").update(status="READY"),
        lambda s, q: next(item for item in q["items"] if item["id"] == "DX9EX-FEATURE-MAIN_MENU").update(status="BLOCKED"),
        lambda s, q: next(item for item in q["items"] if item["id"] == "DX9EX-FEATURE-F11_MENU").update(workKey="DX9EX:VIS:MAIN_MENU"),
        lambda s, q: next(item for item in q["items"] if item["id"] == "DX9EX-FEATURE-ESC_MENU").update(blockedBy="HMD"),
        lambda s, q: next(item for item in q["items"] if item["id"] == "DX9EX-QUEST3-RESPONSIVE-UI-20261013").update(childFeatureIds=["DX9EX:VIS:MAIN_MENU"]),
        lambda s, q: next(item for item in q["items"] if item["id"] == "DX9EX-P0-VISUAL-COMPOSITION-20261007").update(status="BLOCKED"),
        lambda s, q: next(item for item in q["items"] if item["id"] == "DX9EX-P0-VISUAL-COMPOSITION-20261007").update(blockedBy="R84"),
        lambda s, q: next(item for item in q["items"] if item["id"] == "ARCH-V3-001").update(status="READY"),
        lambda s, q: next(item for item in q["items"] if item["id"] == "ARCH-V3-GATE-001").update(status="DONE"),
    )
    for index, mutation in enumerate(negative_cases, 1):
        ss, qq = copy.deepcopy(state), copy.deepcopy(queue)
        mutation(ss, qq)
        if not violations(ss, qq, docs):
            raise SystemExit(f"VR POLICY FAIL: negative mutation {index} escaped")
    for phrase in (
        "DX11 Native A remains global conversion priority",
        "DXVK B FROZEN",
        "FFB v0.2 and currently working gamepad/input are FROZEN",
    ):
        mutated_docs = dict(docs)
        mutated_docs["priority"] = docs["priority"].replace(phrase, "RETRACTED_POLICY")
        if not violations(state, queue, mutated_docs):
            raise SystemExit(f"VR POLICY FAIL: priority text mutation escaped: {phrase}")
    print(f"VR POLICY PASS: DX11 A + DX9Ex C ACTIVE / DXVK B FROZEN; {len(negative_cases)} negative cases")


if __name__ == "__main__":
    main()
