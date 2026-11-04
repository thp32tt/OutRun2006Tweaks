"""Idempotent GitHub-only HD ImageGen rework queue refill, no N100 compute."""
import argparse
import json
import os
from pathlib import Path
import hd_rework_queue
import publish_hd_rework_queue

def refill(source,queue,state,output):
    qfile=Path(queue)/"latest.json"
    reportfile=Path(queue)/"last_report.json"
    if not reportfile.is_file():
        print("HOLD_STRICT_REPORT_NOT_AVAILABLE")
        return "HOLD_STRICT_REPORT_NOT_AVAILABLE"
    prior=json.loads(qfile.read_text(encoding="utf-8")) if qfile.is_file() else {}
    if prior.get("schema")!="outrun-hd-qa-chat-workqueue-v1":
        raise ValueError("INVALID_PRIOR_QUEUE_SCHEMA")
    waiting=[]
    for task in prior.get("tasks",[]):
        task_id=task.get("task_id","")
        if not hd_rework_queue.re.fullmatch(r"HDRW-[AB]-[0-9a-f]{20}",task_id):
            raise ValueError("INVALID_PRIOR_TASK_ID")
        if not (Path(state)/(task_id+".json")).is_file():
            waiting.append(task_id)
    if waiting:
        print("QUEUE_HAS_UNCLAIMED_TASKS="+str(len(waiting)))
        return "WAIT_UNCLAIMED_TASKS"
    report=json.loads(reportfile.read_text(encoding="utf-8"))
    if report.get("schema")!="outrun.ab-imagegen-hd-strict.v2":
        raise ValueError("NOT_STRICT_QA_SOURCE")
    q=hd_rework_queue.build_queue(source,report,output,state)
    publish_hd_rework_queue.publish(output,os.environ.get("GH_TOKEN",""),reportfile)
    print("REFILLED_CHAT_QUEUE="+str(len(q["tasks"])))
    return "REFILLED"

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",required=True)
    ap.add_argument("--queue-root",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    root=Path(args.queue_root)
    refill(args.source,root,root/"state",args.out)
