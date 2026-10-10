#!/usr/bin/env python3
"""DX9Ex source-of-truth policy precedence guard, with seven fail-closed mutations."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = "fcd18ddd89f6dd40a8246fcf8591f086811149f1"
STAGES = ["P0_FFB_V0_2_INTEGRATION", "P1_R84_STRUCTURAL",
          "P2_XR_PER_EYE_RESOLUTION", "P3_NATIVE_120FPS"]


def violations(state, queue, docs):
    sa = state["policy"]["executionAuthority"]
    qa = queue["policy"]["executionAuthority"]
    checks = (
        (sa == qa, "DX9Ex state/queue diverged"),
        (sa["roles"]["A"]["status"] == "ACTIVE" and sa["roles"]["A"]["globalPriority"] == 0, "DX11 A not first-priority ACTIVE"),
        (sa["roles"]["C"]["status"] == "ACTIVE" and sa["roles"]["C"]["effortTargetPercent"] == 50, "DX9Ex C allocation/state changed"),
        (sa["roles"]["B"]["status"] == "FROZEN" and not sa["autoThawDxvk"], "DXVK B thawed"),
        (sa["dx9exPriority"] == STAGES, "P0-P3 stage order lost"),
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
