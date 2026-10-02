#!/usr/bin/env python3
import csv, json
from pathlib import Path

root=Path(__file__).resolve().parents[2]
cfg=json.loads((root/"localization/controller_roles.json").read_text(encoding="utf-8"))
errors=[]
def req(ok,msg):
    if not ok: errors.append(msg)

req(cfg.get("schema_version")==50,"schema_version must be 50")
ex=cfg.get("execution",{})
req(ex.get("mode")=="two_producers_then_c_barrier","execution mode")
req(ex.get("producer_lanes")==["A","B"],"producer lanes must be A/B only")
req(ex.get("qa_lane")=="C","C must be QA lane")
req(ex.get("max_parallel_production")==2,"max production must be 2")
req(ex.get("c_gates_next_wave") is True,"C must gate next wave")
req("E" not in cfg.get("lanes",{}),"E lane must not exist")
req(cfg.get("queue_source")=="localization/graphics/asset_queue_v2.csv","v2 queue source")
iso=cfg.get("isolation",{})
req(iso.get("domain")=="LOCALIZATION_ONLY","localization-only domain")
for k in ("share_runtime_state_with_vr","share_queue_with_vr","share_task_ids_with_vr","share_browser_slots_with_vr"):
    req(iso.get(k) is False,k+" must be false")
sm=cfg.get("state_machine",{})
req(sm.get("assistant_text_never_completes_task") is True,"prose cannot complete task")
req(sm.get("next_wave_requires_c_terminal") is True,"C barrier required")
with (root/"localization/graphics/asset_queue_v2.csv").open(encoding="utf-8",newline="") as f:
    rows=list(csv.DictReader(f))
req(len(rows)==137,f"v2 queue row count {len(rows)} != 137")
req(len({r["index"] for r in rows})==137,"duplicate v2 queue index")
allowed={"READY","CLAIMED_A","CLAIMED_B","QA_PENDING","REWORK_REQUIRED","PRODUCTION_COMPLETE","HOLD","PRESERVE"}
for r in rows:
    req(r["state"] in allowed,f'bad state {r["index"]}')
    req(r["owner"]==("A" if int(r["index"])%2==0 else "B"),f'bad owner {r["index"]}')
if errors:
    raise SystemExit("LOCALIZATION_CONTROLLER_V2_FAIL: "+"; ".join(errors))
print("LOCALIZATION_CONTROLLER_V2_PASS")
print("A/B production -> C barrier -> next wave")
print("VR controller state/queue/task/browser isolation enforced")
