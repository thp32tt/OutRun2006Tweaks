#!/usr/bin/env python3
"""GitHub Actions publication/feedback handoff. No browser or N100 compute."""
import argparse,base64,hashlib,json,os,re,subprocess
from pathlib import Path

ROOT="localization/automation_runs/hd_cleanplate_repair"
BRANCH="korean-localization-qa-queue-20261104"
REPO="thp32tt/OutRun2006Tweaks"
H40=re.compile(r"[0-9a-f]{40}\Z")
H64=re.compile(r"[0-9a-f]{64}\Z")

def gh(*args):
    p=subprocess.run(["gh","api",*args],capture_output=True,text=True,check=False)
    if p.returncode:
        if "HTTP 404" in p.stderr:return None
        raise RuntimeError("REPAIR_GITHUB_API_FAILED")
    return json.loads(p.stdout) if p.stdout.strip() else None

def read(rel):
    obj=gh(f"repos/{REPO}/contents/{rel}?ref={BRANCH}")
    if obj is None:return None,None
    return json.loads(base64.b64decode(obj["content"])),obj["sha"]

def write(rel,doc,previous):
    raw=(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode()
    args=["-X","PUT",f"repos/{REPO}/contents/{rel}","-f",f"branch={BRANCH}",
          "-f","message=localization: publish cleanplate repair queue pointer",
          "-f","content="+base64.b64encode(raw).decode()]
    if previous:args+=["-f","sha="+previous]
    gh(*args)
    check,_=read(rel)
    if check!=doc:raise RuntimeError("REPAIR_QUEUE_POINTER_READBACK")

def validate_completed_feedback(state,pointer):
    if (not isinstance(state,dict) or state.get("schema")!="outrun.hd.atlas-vision-state.v1"
        or state.get("run_id")!=pointer["run_id"]
        or state.get("manifest_sha256")!=pointer["manifest_sha256"]):
        return None
    records=state.get("records",{})
    # No feedback generation until the entire 104-atlas batch was reviewed.
    if len(records)!=104 or any(x.get("status") not in ("DONE","HOLD_SEND_UNCERTAIN","HOLD_RESPONSE_TIMEOUT") for x in records.values()):
        return None
    result=[]
    for t,record in records.items():
        d=record.get("decision",{})
        if d.get("task_id")!=t or d.get("decision")!="REWORK_REQUIRED":continue
        for item in d.get("bbox_proposals",[]):
            result.append({"roi_id":item["roi_id"],"bbox_xyxy":item["bbox_xyxy"],
                "target":record["target"],"source_dds_sha256":record["source_dds_sha256"]})
    # One follow-up maximum per input SHA. Repeated visually unproven proposals
    # must not cause a runaway generation loop.
    seen=set();unique=[]
    for item in result:
        if item["roi_id"] not in seen:
            seen.add(item["roi_id"]);unique.append(item)
    return unique

def prepare(asset_sha,out):
    if not H40.fullmatch(asset_sha):raise ValueError("BAD_ASSET_SHA")
    pointer,_=read(ROOT+"/latest.json")
    gen=1;proposals=[]
    if pointer:
        state,_=read(ROOT+"/visual/run-"+str(pointer["run_id"])+".json")
        candidates=validate_completed_feedback(state,pointer)
        # A new source-branch commit must not discard an in-flight 104-DDS
        # review. Keep the active manifest until terminal receipts exist.
        if candidates is None:return "skip",int(pointer.get("generation",1))
        if pointer.get("asset_sha")==asset_sha:
            if pointer.get("generation",1)>=2 or not candidates:return "skip",int(pointer.get("generation",1))
            gen=2;proposals=candidates
    Path(out).write_text(json.dumps({"schema":"outrun.hd.cleanplate-feedback.v1","proposals":proposals}),encoding="utf-8")
    return "build",gen

def publish(asset_sha,run_id,artifact_id,generation,manifest):
    raw=Path(manifest).read_bytes(); doc=json.loads(raw)
    if (doc.get("schema")!="outrun.hd.cleanplate-repair.v1" or doc.get("asset_sha")!=asset_sha
        or doc.get("scope")!="FULL_104" or doc["counts"].get("atlases")!=104
        or doc["counts"].get("roi")!=954 or len(doc["tasks"])!=104
        or doc.get("release_approved") is not False):raise ValueError("BAD_FULL_MANIFEST")
    pointer={"schema":"outrun.hd.cleanplate-queue-pointer.v1","asset_sha":asset_sha,
             "run_id":run_id,"artifact_id":artifact_id,"generation":generation,
             "manifest_sha256":hashlib.sha256(raw).hexdigest(),
             "counts":doc["counts"],"release_approved":False,"runtime_validation":"UNTESTED"}
    prior,etag=read(ROOT+"/latest.json")
    if prior and prior.get("run_id",0)>run_id:raise ValueError("OLDER_RUN_CANNOT_REPLACE_LATEST")
    write(ROOT+"/latest.json",pointer,etag)
    print(json.dumps(pointer,sort_keys=True))

if __name__=="__main__":
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("prepare");a.add_argument("--asset-sha",required=True);a.add_argument("--out",required=True)
    b=sub.add_parser("publish");b.add_argument("--asset-sha",required=True);b.add_argument("--run-id",type=int,required=True);b.add_argument("--artifact-id",type=int,required=True);b.add_argument("--generation",type=int,required=True);b.add_argument("--manifest",required=True)
    args=p.parse_args()
    if args.cmd=="prepare":
        action,generation=prepare(args.asset_sha,args.out)
        with open(os.environ["GITHUB_OUTPUT"],"a") as f:f.write(f"action={action}\ngeneration={generation}\n")
        print("REPAIR_PREFLIGHT",action,generation)
    else:publish(args.asset_sha,args.run_id,args.artifact_id,args.generation,args.manifest)
