#!/usr/bin/env python3
"""Read-only A/B ImageGen candidate inventory for the 954 active original-HD ROI."""
import argparse,csv,json
from collections import Counter,defaultdict
from pathlib import Path

def run(root,out):
 root=Path(root).resolve(); out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
 m=json.loads((root/"production_manifest.json").read_text(encoding="utf8"))
 active=[r for r in m["items"] if r.get("status")=="ROI_APPROVED_FOR_IMAGEGEN"]
 rebalance=[r for r in m["items"] if r.get("status")=="ROI_REBALANCED_TO_B"]
 index=defaultdict(list);allfiles=[]
 for role in ("A","B"):
  for f in sorted((root/"candidate_outputs"/role).glob("*.png")):
   allfiles.append(f)
   name=f.name
   if name.endswith("_source_k.png"): stem=name[:-13]
   elif name.endswith("_k.png"):stem=name[:-6]
   else:continue
   index[stem].append((role,f))
 records=[];used=set()
 for r in active:
  rid=r["id"];items=index.get(rid,[])
  if not items and rid.endswith("_RB_B"):items=index.get(rid[:-5],[])
  for _,p in items:used.add(str(p))
  state=("MISSING" if not items else "AMBIGUOUS" if len(items)>1 else "CANDIDATE_ONLY_QA_UNVERIFIED")
  records.append({
   "roi_id":rid,"candidate_status":state,"candidate_count":len(items),
   "candidate_paths":";".join(str(p) for _,p in items),"roles":";".join(role for role,_ in items),
   "source_dds_path":r.get("source_dds_path",""),"source_dds_sha256":r.get("source_dds_sha256",""),
   "source_hd_sha256":r.get("source_png_sha256",""),"native_crop_sha256":r.get("native_crop_sha256",""),
   "bbox_xyxy":json.dumps(r.get("bbox_xyxy",[])),"english":r.get("english",""),"korean":r.get("korean",""),
   "qa_status":"UNVERIFIED","runtime_status":"UNTESTED","final_dds_status":"NOT_BUILT"})
 with (out/"ab_roi_crosswalk.csv").open("w",newline="",encoding="utf-8-sig") as f:
  w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
 summary={"status":"READ_ONLY_NOT_RUNTIME_APPROVED","manifest_total":len(m["items"]),"active_roi":len(active),
  "retired_rebalance":len(rebalance),"A_B_png_files":len(allfiles),"matched_png_files":len(used),
  "unmatched_png_files":len(allfiles)-len(used),"crosswalk_status":dict(Counter(r["candidate_status"] for r in records)),
  "unmatched_samples":[str(f) for f in allfiles if str(f) not in used][:20]}
 (out/"ab_audit_summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
 print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":
 a=argparse.ArgumentParser()
 a.add_argument("--root",default="/home/chatgpt-runner2/work/image-src/text_roi_batches")
 a.add_argument("--output",default="/home/chatgpt-runner2/work/image-src/text_roi_batches/ab_dds_integration_prep_20261102")
 v=a.parse_args();run(v.root,v.output)
