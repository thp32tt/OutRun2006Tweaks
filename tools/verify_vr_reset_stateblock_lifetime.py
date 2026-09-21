from pathlib import Path
import sys

SOURCE = Path("src/vr/d3d9/ex_device_upgrade_r15.cpp")
text = SOURCE.read_text(encoding="utf-8")

forbidden = {
    "persistent all-state pointer": "R15ClassicAllState",
    "D3DSBT_ALL capture": "CreateStateBlock(D3DSBT_ALL",
    "cross-reset all-state restore helper": "R15RestoreClassicAllState",
    "cross-reset health dependency": "allStateHealthy",
}
required = {
    "R13 explicit baseline replay": "OutRunVRD3D9ExUpgrade::RestoreClassicResetState(device)",
    "R15 explicit extra baseline replay": "R15RestoreClassicExtraBaseline(device)",
    "fail-closed health publication": "R15ResetStateHealthy.store(healthy, std::memory_order_release)",
}

failed = []
for name, needle in forbidden.items():
    ok = needle not in text
    print(("PASS" if ok else "FAIL") + ": no " + name)
    if not ok:
        failed.append("forbidden " + name)
for name, needle in required.items():
    ok = needle in text
    print(("PASS" if ok else "FAIL") + ": " + name)
    if not ok:
        failed.append("missing " + name)

if failed:
    print("ResetEx state-block lifetime verifier failed: " + "; ".join(failed), file=sys.stderr)
    raise SystemExit(1)
print("ResetEx replay uses explicit state families without retaining D3D9 state blocks across ResetEx.")
