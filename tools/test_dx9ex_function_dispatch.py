#!/usr/bin/env python3
"""Selection contract: never convert a partial fix into a new task or point."""
import copy
import json
from dx9ex_function_dispatch import POLICY, QUEUE, choose

policy=json.loads(POLICY.read_text(encoding="utf-8"))
queue=json.loads(QUEUE.read_text(encoding="utf-8"))
assert queue["policy"]["functionalFeatureDispatch"]["unit"].startswith("ONE_USER_VISIBLE")
ready=[x for x in queue["items"] if x.get("featureId") and x.get("status")=="READY"]
assert any(x["featureId"]=="DX9EX:VIS:HUD_GAMEPLAY" for x in ready)
assert not any(x["featureId"]=="DX9EX-QUEST3-RESPONSIVE-UI-20261013" for x in ready)
no_claim=choose(queue,policy,[],None)
assert no_claim["action"]=="HOLD_OWNER_UNCONFIRMED"
next_job=choose(queue,policy,[],[])
assert next_job["action"]=="PROPOSE_NEW_FUNCTIONAL_FEATURE",next_job
# The queue is mutable authority. Test selection order from *current* priority,
# rather than freezing the former HUD-first value after lens/+TIME were raised.
catalog_ids={f["feature_id"] for f in policy["feature_catalog"]}
ordered=sorted((x for x in queue["items"]
                if x.get("featureId") in catalog_ids
                and x.get("status") in {"READY","NEEDS_VALIDATION","IN_PROGRESS"}),
               key=lambda x:(-int(x.get("priority",0)),x["id"]))
assert len(ordered)>=2
assert next_job["feature_id"]==ordered[0]["featureId"],next_job
assert next_job["symptom_id"]==ordered[0].get("symptomId"),next_job
assert no_claim["candidate"]==ordered[0]["featureId"],no_claim
assert next_job["new_task_allowed"] is False, "selection cannot itself create a task"
rec={"task_id":"CONVERSION-DX9EX-00772",
     "feature_id":"DX9EX:VIS:F11_MENU",
     "symptom_id":"DX9EX:SYMPTOM:F11_MENU",
     "status":"IMPLEMENTING","runtime_validation":"UNTESTED"}
resume=choose(queue,policy,[rec],[])
assert resume["action"]=="RECONCILE_THEN_RESUME" and resume["task_id"]==rec["task_id"]
assert resume["score_delta"]==0 and not resume["new_task_allowed"]
owner={"verified_live":True,"feature_id":rec["feature_id"],"task_id":rec["task_id"],
       "conflict_keys":["DX9EX:SHARED_R30_HUD_RENDERER"]}
attached=choose(queue,policy,[rec],[owner])
assert attached["action"]=="ATTACH_EXISTING_OWNER"
unknown=choose(queue,policy,[],[{"owner_uncertain":True}])
assert unknown["action"]=="HOLD_OWNER_UNCERTAIN"
complete=copy.deepcopy(rec)
complete.update(status="COMPLETE_BUILD_VERIFIED",automation_validation="PASS_EXACT_SHA")
post=choose(queue,policy,[complete],[])
assert post["feature_id"]==ordered[0]["featureId"],post
assert not post["new_task_allowed"]
# BUILD_VERIFIED/HMD-UNTESTED at the top of the queue must advance to the
# next independent visible feature, not stall or reissue the same scored task.
completed_top={"task_id":"CONVERSION-DX9EX-00800",
               "feature_id":ordered[0]["featureId"],
               "symptom_id":ordered[0].get("symptomId"),
               "status":"COMPLETE_BUILD_VERIFIED",
               "runtime_validation":"UNTESTED"}
next_after=choose(queue,policy,[complete,completed_top],[])
assert next_after["feature_id"]==ordered[1]["featureId"],next_after
assert not next_after["new_task_allowed"]
complete["runtime_validation"]="USER_REPORTED_FAIL"
reopen=choose(queue,policy,[complete],[])
assert reopen["action"]=="REOPEN_SAME_SYMPTOM" and reopen["task_id"]==rec["task_id"]
assert reopen["score_delta"]==0
blocked=copy.deepcopy(queue)
for item in blocked["items"]:
    if item.get("featureId","").startswith("DX9EX:VIS:"):
        item["conflictKeys"]=["DX9EX:SHARED_R30_HUD_RENDERER"]
# A live claim for a shared source prevents any new worker on the same paths.
blocked_plan=choose(blocked,policy,[],[{"verified_live":True,"feature_id":"UNRELATED",
                                      "conflict_keys":["DX9EX:SHARED_R30_HUD_RENDERER"]}])
assert blocked_plan["action"]=="HOLD_OVERLAPPING_OWNER_OR_ALL_BUILD_VERIFIED"
print("DX9Ex whole-function dispatch selector PASS: no-claim, pending resume, owner attach, overlap, HMD reopen/no rescore")
