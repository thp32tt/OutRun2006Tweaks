#!/usr/bin/env python3
import json,csv,hashlib,io
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
root=Path.cwd()
out=root/"localization/graphics/role_C/20261011-C2-Q193-A243-FIRST-PIXEL-INDEPENDENT"
machine=json.loads((out/"C2_Q193_A243_MECHANICAL.json").read_text())
at=datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M KST")
uri="localization/graphics/role_C/20261011-C2-Q193-A243-FIRST-PIXEL-INDEPENDENT/"
sha=lambda file:hashlib.sha256((root/file).read_bytes()).hexdigest()
evidence=[{"path":p,"sha256":sha(p)} for p in machine["independent_evidence"]]
source=machine["files"]["source"]; trial=machine["files"]["trial"];official=machine["files"]["official"]
checks={
"slant":{"result":"PASS_SCOPED","observation":"Upright English source label and upright Hangul in native readable views; no opposite lean in this single ROI"},
"clean_plate":{"result":"PASS_SCOPED","observation":"Clean alpha exactly zero in ROI; official-to-CLEAN changed 5839 RGBA pixels inside ROI and zero outside; English source letters fully removed in visible area"},
"style":{"result":"HOLD_FAMILY_CALIBRATION","observation":"New bold Hangul similar dark heavy hierarchy to English 15 Cont.; native family blind calibration and all remaining q193 regions not accepted"},
"readability":{"result":"PASS_SCOPED","observation":"15 연속전 individually readable on gray100/white75/white50/black100; shorter translation width permitted by 2026-10-11 per-glyph policy"},
"glyph_integrity":{"result":"PASS_SCOPED","observation":"Native view shows separate visible Hangul syllables, preserved counters/strokes and no evident spurious fragments; not a user game validation"},
"protected_art":{"result":"PASS_SCOPED","observation":"Official-to-trial 6938 RGBA pixel changes all within English source ROI, zero outside; neighboring atlas cells unchanged"},
"placement":{"result":"PASS_SCOPED","observation":"Native trial alpha bbox [1416,224,1592,265] within exact English source bbox [1413,221,1622,268], positive margins"},
"orientation":{"result":"PASS_SCOPED","observation":"Persisted native BGRA32 DDS 2048x1024 mip1 saved RAW -> FLIPY exactly; separately rendered readable crop matches"}
}
result={
"schema_version":2,"review_id":"C2-20261011-1950-Q193-A243-FIRST-INDEPENDENT",
"run_key":"OUTRUN-KOR-C2-Q193-A243-PIXEL-PLATE-20261011-1950",
"reviewed_at_kst":at,"role":"C2","reviewer":"ChatGPT AI1 C2 independent inspection",
"queue_index":193,"producer_role":"A","producer_run":"A243","queue_status_before":"c1_20261011_q193_six_inherited_native_style_rework_goal_a_hold",
"queue_status_after":"UNCHANGED_HOLD_STRICT_RECHECK",
"official_candidate_unchanged":True,"trial_status":"UNPROMOTED",
"source_sha256":source["sha256"],"official_sha256":official["sha256"],"trial_sha256":trial["sha256"],
"source_english":"15 Cont.","korean_trial":"15 연속전",
"calibration":{"blind_review_completed":False,"reason":"No independently recorded normal and four negative-control visual calibration cases; cannot claim machine-evidence current-policy C2 PASS"},
"policy_20261011":{"text_length_difference_ignored":True,"whole_sentence_width_ratio":"diagnostic_only","source_bbox_containment":"PASS","per_glyph_size_and_readability":"PASS_SCOPED"},
"scope":{"region_bbox":[1413,221,1622,268],"raw_flipy":True,"native_100_75_50":True,"mip_count":1,
"additional_regions":"NOT_REVIEWED_CURRENT_RUN","C3":"NOT_RUN","user_game":"OPEN_IGR003_IGR019_IGR033",
"RUNTIME_VALIDATION":"UNTESTED"},
"machine_evidence":uri+"C2_Q193_A243_MECHANICAL.json",
"measured":{"candidate_rgba_changed_inside":6938,"candidate_rgba_changed_outside":0,"candidate_alpha_changed_outside":0,
"official_to_clean_inside":5839,"official_to_clean_outside":0,
"clean_alpha_target_roi":0,"clean_to_trial_outside":0,"lettering_alpha_outside":0,
"clean_plus_glyph_composited_vs_persisted_diff":0},
"visual_findings":checks,
"evidence":evidence,
"assessment":"SCOPED_C2_PIXEL_PLATE_GLYPH_OK_ATLAS_HOLD_STRICT_RECHECK",
"independent_c2_final_PASS":False,
"reason":"This is independent first-hand *single-cell* evidence for a genuinely new trial DDS SHA, not full q193 C2 approval. Other inherited q193 cells, source-family blind calibration and stage C3/game are incomplete. No old-SHA reapproval, DDS production, approval manifest or in-game closure.",
"candidate_SHA_repeated_approval":False,
"backend":"N100 MCP minimal native-pixel fallback (local direct GitHub bytes unavailable), GitHub SSOT"}
qa=out/"C2_Q193_A243_INDEPENDENT_SCOPED_HOLD.json"
qa.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
queuefile=root/"localization/graphics/asset_queue.csv"
with queuefile.open("r",encoding="utf-8-sig",newline="") as f:
 reader=csv.DictReader(f);headers=reader.fieldnames;rows=list(reader)
idx=[x for x in rows if x.get("index")=="193"]
if len(idx)!=1:raise ValueError(f"q193 duplicate/missing: {len(idx)}")
note=f"C2 {at} q193 A243 NEW SHA {trial['sha256']} independently native-source/official/CLEAN/glyph/saved-DDS scoped pixel QA. Trial vs official 6938 RGBA inside source ROI [1413,221,1622,268], outside0; official->CLEAN outside0 / alpha ROI0; CLEAN+GLYPH DDS pixel exact; RAW/FLIPY 100/75/50 native clear. SCOPED_C2_PIXEL_PLATE_GLYPH_OK_ATLAS_HOLD_STRICT_RECHECK because other five inherited cells, blind calibration/C3/current-policy approval and user IGR003/019/033 retest unresolved. Official DDS unchanged, C2 FULL PASS0/C3 NOT_RUN/USER_GAME_OPEN/RUNTIME_VALIDATION=UNTESTED. QA {uri}C2_Q193_A243_INDEPENDENT_SCOPED_HOLD.json RUN_KEY={result['run_key']}."
if result["run_key"] not in idx[0]["notes"]:
 idx[0]["notes"]+=" "+note
 lines=queuefile.read_text(encoding="utf-8-sig").splitlines(keepends=True)
 hits=[i for i,line in enumerate(lines) if line.startswith("193,")]
 if len(hits)!=1: raise RuntimeError("q193 physical row nonunique; do not rewrite")
 i=hits[0]
 row=next(csv.reader([lines[i]]))
 if len(row)!=len(headers): raise RuntimeError("q193 row malformed")
 row[headers.index("notes")]+= " "+note
 buf=io.StringIO(newline="")
 csv.writer(buf,lineterminator="\n").writerow(row)
 lines[i]=buf.getvalue()
 queuefile.write_text("".join(lines),encoding="utf-8")
worklog=root/"localization/WORKLOG.md"
wl=f"\n- {at} C2 independent q193 A243 first new trial SHA `{trial['sha256']}`: source/official/clean/glyph/native persisted DDS cross-check inside changed6938/outside0, correct PLATE removal and no protected-art change, RAW/FLIP-Y and BGW native/75/50 visually inspected. SCOPED CELL pixel/plate/glyph OK; atlas remains HOLD, full C2 PASS0, C3/game UNTESTED, IGR003/019/033 OPEN. Evidence `{uri}C2_Q193_A243_INDEPENDENT_SCOPED_HOLD.json`; `RUN_KEY={result['run_key']}`.\n"
if result["run_key"] not in worklog.read_text(encoding="utf-8"): 
 with worklog.open("a",encoding="utf-8") as f:f.write(wl)
resume=root/"localization/resume_state.json"
state=json.loads(resume.read_text(encoding="utf-8"))
act=f"C2 {at} q193 A243 fresh trial {trial['sha256']} first independent native-source/CLEAN/lettering/persisted DDS cell-level PASS_SCOPED, whole atlas HOLD, existing official unchanged, five inherited/source-family calibration/C3/user game OPEN. {uri}C2_Q193_A243_INDEPENDENT_SCOPED_HOLD.json; RUN_KEY={result['run_key']}"
if not any(result["run_key"] in str(x) for x in state.get("next_actions",[])):state["next_actions"].insert(0,act)
resume.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"evidence_files":len(evidence),"qa":str(qa.relative_to(root)),"time":at,"result":result["assessment"]}))
