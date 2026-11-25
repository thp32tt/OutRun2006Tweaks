#!/usr/bin/env python3
"""Conservative per-atlas merge: never sacrifice an already repaired ROI."""
import argparse,hashlib,json,shutil,zipfile
from pathlib import Path
from collections import Counter

def sha(x):return hashlib.sha256(x).hexdigest()

def ids(t):return {r["roi_id"] for r in t["painted"]}

def select(old,new):
    if old["target"]!=new["target"] or old["source_dds_sha256"]!=new["source_dds_sha256"] or old["native_size"]!=new["native_size"] or old["orientation"]!=new["orientation"]:
        raise ValueError("MERGE_SOURCE_MISMATCH")
    allids=lambda t:ids(t)|{r["roi_id"] for r in t["holds"]}
    if allids(old)!=allids(new) or len(allids(old))!=old["roi_count"]:raise ValueError("MERGE_ROI_SET_MISMATCH")
    # Keep old if the new atlas has no strict gain. This also prevents
    # accidental color or layout regression in already accepted PNGs.
    return new if ids(old)<ids(new) else old

def merge(old_build,old_vision,new_root,out):
    ob,ov,nr,out=map(Path,(old_build,old_vision,new_root,out))
    old=json.loads((ob/"qa_report.json").read_text());new=json.loads((nr/"build/qa_report.json").read_text())
    if old["counts"]["atlases"]!=104 or new["counts"]["atlases"]!=104 or old["counts"]["roi"]!=954 or new["counts"]["roi"]!=954:raise ValueError("MERGE_SCOPE")
    if sha((ov/"manifest.json").read_bytes())!="42bc76b14b32e4d1c1b0ef42c283c06acd1d8a54622d6c948f0d746fe354ee73":raise ValueError("MERGE_BASELINE_MANIFEST_SHA")
    if json.loads((ov/"manifest.json").read_bytes())!=old:raise ValueError("MERGE_BASELINE_REPORT")
    (out/"build").mkdir(parents=True,exist_ok=True);(out/"vision").mkdir(parents=True,exist_ok=True)
    old_by={t["target"]:t for t in old["tasks"]};new_by={t["target"]:t for t in new["tasks"]}
    if set(old_by)!=set(new_by):raise ValueError("MERGE_TARGET_SET")
    name="OUTRUN_HD_CLEANPLATE_REPAIR_TEST_ONLY.zip"
    tasks=[];entries={};counts=Counter();gains=[]
    with zipfile.ZipFile(ob/name) as oz,zipfile.ZipFile(nr/"build"/name) as nz,zipfile.ZipFile(out/"build"/name,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=3) as dest:
        for o in old["tasks"]:
            n=new_by[o["target"]];t=select(o,n);fresh=t is n
            base=nr/"vision" if fresh else ov
            if fresh:gains.append({"target":t["target"],"additional_roi":len(ids(t)-ids(o))})
            if not t["source_unchanged"]:
                raw=(nz if fresh else oz).read(t["target"])
                if sha(raw)!=t["candidate_dds_sha256"]:raise ValueError("MERGE_DDS_SHA")
                dest.writestr(t["target"],raw);entries[t["target"]]=sha(raw)
            for item in t["images"].values():
                f=base/item["name"];raw=f.read_bytes()
                if sha(raw)!=item["sha256"]:raise ValueError("MERGE_IMAGE_SHA")
                (out/"vision"/item["name"]).write_bytes(raw)
            counts.update({"atlases":1,"roi":t["roi_count"],"painted":t["painted_count"],"held":t["hold_count"],"changed_dds":int(not t["source_unchanged"])})
            tasks.append(dict(t,retained_baseline=not fresh))
        dest.writestr("TEST_ONLY_MANIFEST.json",json.dumps({"schema":new["schema"],"entries":entries,"release_approved":False,"runtime_validation":"UNTESTED","partial_patch":True},sort_keys=True))
    with zipfile.ZipFile(out/"build"/name) as z:
        if z.testzip() is not None:raise ValueError("MERGE_ZIP_CRC")
    if counts["painted"]<old["counts"]["painted"]:raise ValueError("MERGE_REGRESSION")
    result=dict(new,counts=dict(counts),tasks=tasks,baseline_run_id=45333597142,
                baseline_painted=old["counts"]["painted"],additional_painted=counts["painted"]-old["counts"]["painted"],
                improved_atlases=gains,visual_qa="PENDING",release_approved=False,runtime_validation="UNTESTED")
    for p in (out/"build/qa_report.json",out/"vision/manifest.json"):
        p.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    print("DEADLINE_MERGE",json.dumps({k:v for k,v in result.items() if k!="tasks"},ensure_ascii=False),flush=True)
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--old-build",required=True);p.add_argument("--old-vision",required=True);p.add_argument("--new-root",required=True);p.add_argument("--out",required=True);a=p.parse_args();merge(a.old_build,a.old_vision,a.new_root,a.out)
