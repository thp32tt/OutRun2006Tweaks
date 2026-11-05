#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "automation" / "QUEUE_CONTROLLER_CONTRACT.md"
WORKFLOW = ROOT / ".github" / "workflows" / "backend-conversion-gate.yml"

REQUIRED = (
    "validation_bearing_result_sha",
    "Missing-run recovery is mandatory before timeout failure",
    "query repository workflow runs for the exact candidate SHA",
    "Do not rely only on helpers that return pull-request-associated runs",
    "head_sha exactly equal to the candidate SHA is authoritative evidence",
    "MUST NOT silently replace an already recorded validation_bearing_result_sha",
    "exact-SHA fallback search finds no matching Gate",
)

def main():
    contract = CONTRACT.read_text(encoding="utf-8")
    missing = [token for token in REQUIRED if token not in contract]
    if missing:
        raise SystemExit("queue controller contract missing exact-SHA Gate recovery rules: " + ", ".join(missing))
    policy = ROOT / "docs" / "automation" / "DX11_AUTODEV_EXECUTION_POLICY.json"
    if not policy.exists() or "DX11 auto-work selection and batching gate" not in contract:
        raise SystemExit("DX11 task allocation/acceptance policy missing")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    if "python tools/verify_queue_controller_contract.py" not in workflow:
        raise SystemExit("Backend Conversion Gate does not invoke queue controller contract verifier")
    if "python tools/dx11_autodev_policy.py --check-latest" not in workflow:
        raise SystemExit("DX11 full Gate does not enforce next-task structural acceptance")
    print("Queue controller contract: PASS (exact-SHA missing-run recovery + validation-bearing identity sealed)")

if __name__ == "__main__":
    main()