#!/usr/bin/env python3
"""Summarize R84 on-device visual provenance counters and original HUD callsites.

This analysis never equates GPU success with Quest3 optical success. Five-second
aggregates cannot demonstrate a 1:1 source->Draw pairing; UNKNOWN is preserved.
Standard library only; accepts unzipped OutRun2_VR_ANALYZE directory or log file.
"""
from __future__ import annotations
import argparse
import collections
import csv
import json
import re
from pathlib import Path

FAMILIES = (
    "CENTRE_C993", "OUTER_CABE_CANDIDATE", "OTHER_PROJECTED_EFFECT", "SKYGLOW",
    "HUD", "PROJECTED_RANK", "SCREEN_OVERLAY", "WORLD", "UNKNOWN",
    "STAGE_PLUS_TIME", "RANK_6TH_OF_6", "GOAL_RESULT_TIMER",
    "HUD_TEXT_DIGITS", "PAUSE_OPTION_ARROW", "PLAYER_CAR_SHADOW",
    "WORLD_PARTICLES", "REFLECTIONS", "SCENE_FX", "WORLD_BILLBOARD",
    "LENS_CENTRE_UNPROVEN",
)
FIELD_NAMES = ("total","ok","fail","both","failed","unverified",
               "queued","unknown","badQueue","none","r30Fvf","r30Xyz",
               "r33Hud","r33World","r29","raw","sbRaw","dp","dip","dpup","dipup",
               "r30Both","r30Failed")
CHECKED_SOURCE_FAMILIES = {
    "STAGE_PLUS_TIME","RANK_6TH_OF_6","GOAL_RESULT_TIMER",
    "HUD_TEXT_DIGITS","PROJECTED_RANK","PAUSE_OPTION_ARROW","PLAYER_CAR_SHADOW",
}
RVA_GROUPS = {
    "STAGE_PLUS_TIME": {0x9898E, 0x98A36, 0x98AC6, 0x989AD, 0x98A10, 0x98A89},
    "RANK_6TH_OF_6": {0xB9DA6},
    "PROJECTED_RANK": {0xBB0FB,0xBB133,0xBB16C,0xBB1A5,
                       0xBB21F,0xBB241,0xBB271,0xBB2BC,0xBB2D0},
}

def collect_files(root: Path):
    if root.is_file():
        logs = [root] if root.suffix.lower()==".log" else []
        csvs = [root] if root.suffix.lower()==".csv" else []
    else:
        logs = sorted(p for p in root.rglob("OutRun2006Tweaks*.log") if p.is_file())
        csvs = sorted(p for p in root.rglob("OutRun2006Tweaks-hudtrace*.csv")
                      if p.is_file())
    return logs, csvs

def extract_fields(line: str):
    if "VR R84 DRAW TRACE 5s:" not in line:
        return None
    # fmt/spdlog prints bracketed sections; use safe named-value parsing.
    pairs = dict(re.findall(r"\b([A-Za-z][A-Za-z0-9]*)=([^\s,\[\]]+)",line))
    family = pairs.get("family")
    if family not in FAMILIES:
        return None
    numbers = {}
    for name in FIELD_NAMES:
        try: numbers[name] = max(0,int(pairs.get(name, "0")))
        except ValueError: numbers[name] = 0
    return family,pairs,numbers

def parse_logs(logs):
    counters=collections.defaultdict(collections.Counter)
    meta={}
    windows=collections.Counter()
    for path in logs:
        with path.open("r",encoding="utf-8-sig",errors="replace") as f:
            for line in f:
                record=extract_fields(line)
                if record is None:continue
                family, fields,nums=record
                windows[family]+=1
                counters[family].update(nums)
                meta[family]={key:fields.get(key) for key in
                              ("scope","producer","qEpoch","lastDraw","centreCallEpoch")}
    return counters,windows,meta

def parse_original_hud(csvs):
    result=collections.defaultdict(collections.Counter)
    samples=collections.defaultdict(list)
    invalid=0
    observed_sites=collections.defaultdict(set)
    for path in csvs:
        with path.open("r",encoding="utf-8-sig",errors="replace",newline="") as f:
            for row in csv.DictReader(f):
                txt=str(row.get("call_rva") or "").strip().lower()
                if not txt:continue
                try:
                    value=int(txt, 16) if txt.startswith("0x") or re.search(r"[a-f]",txt) else int(txt,16)
                except ValueError:
                    invalid+=1
                    continue
                labels=[name for name,rv in RVA_GROUPS.items() if value in rv]
                if not labels:
                    semantic=str(row.get("semantic") or "").upper()
                    if "RESULT" in semantic or "GOAL" in semantic:labels=["GOAL_RESULT_TIMER"]
                    elif "HUD" in semantic:labels=["HUD_TEXT_DIGITS"]
                    elif "RANK" in semantic:labels=["PROJECTED_RANK"]
                    else:labels=["OTHER_CALLS"]
                for label in labels:
                    result[label]["observed_rows"]+=1
                    if label in RVA_GROUPS:
                        observed_sites[label].add(value)
                    if len(samples[label])<12:
                        samples[label].append({"call_rva":row.get("call_rva"),
                            "event":row.get("event"),"semantic":row.get("semantic"),
                            "mode":row.get("mode"),"stage":row.get("stage"),
                            "arg0":row.get("arg0")})
    return result,samples,invalid,observed_sites

def analyze(root: Path):
    logs,csvs=collect_files(root)
    counters,windows,meta=parse_logs(logs)
    hud,hud_samples,invalid,observed_sites=parse_original_hud(csvs)
    families={}
    for family in FAMILIES:
        nums=dict(counters[family])
        count=windows[family]
        flags=[]
        if nums.get("fail",0):flags.append("NATIVE_DRAW_FAILED")
        if nums.get("failed",0):flags.append("R33_EYE_OR_RESTORE_FAILED")
        if nums.get("r30Failed",0):flags.append("R30_EYE_OR_RESTORE_FAILED")
        if nums.get("badQueue",0):flags.append("QUEUE_IDENTITY_INCOMPLETE")
        if nums.get("none",0):flags.append("DRAW_ROUTE_UNCLASSIFIED")
        if nums.get("unverified",0):flags.append("STEREO_OUTCOME_UNVERIFIED_NOT_MONO_PROOF")
        if nums.get("r29",0)+nums.get("raw",0) and family in CHECKED_SOURCE_FAMILIES:
            flags.append("ORIGINAL_OR_FALLBACK_REVIEW_NOT_AUTOMATIC_BUG")
        if nums.get("unknown",0):flags.append("SOURCE_TOKEN_NOT_PROVEN")
        if count==0:
            status=("SOURCE_ONLY_GPU_NOT_ATTRIBUTED" if hud[family]["observed_rows"]
                    else "NOT_OBSERVED")
        elif any(x in flags for x in ("NATIVE_DRAW_FAILED",
                                     "R30_EYE_OR_RESTORE_FAILED",
                                     "R33_EYE_OR_RESTORE_FAILED",
                                     "QUEUE_IDENTITY_INCOMPLETE")):
            status="INVESTIGATE"
        else:
            status="OBSERVED_NEEDS_QUEST3_OPTICAL_VALIDATION"
        # A source callsite observed in a HUD CSV is not proof that the
        # physical R84 family routed to both eyes. A missing callsite may
        # simply mean the player did not visit that stage/animation branch.
        expected=RVA_GROUPS.get(family,set())
        seen=observed_sites.get(family,set())
        coverage={"status":("NOT_CAPTURED" if not seen else
                             "ALL_KNOWN_SITES_CAPTURED" if expected <= seen else
                             "PARTIAL_CAPTURE_NOT_RUNTIME_FAILURE"),
                  "expected_call_rvas":[f"0x{r:X}" for r in sorted(expected)],
                  "observed_call_rvas":[f"0x{r:X}" for r in sorted(seen)],
                  "not_captured_call_rvas":[f"0x{r:X}" for r in sorted(expected-seen)]}
        families[family]={"status":status,"windows":count,"counters":nums,
                          "source_site_coverage":coverage,
                          "last_owner":meta.get(family,{}),
                          "hud_source_rows":hud[family]["observed_rows"],
                          "example_callers":hud_samples.get(family,[]),
                          "flags":flags}
    investigations=[{"family":k,"flags":v["flags"]} for k,v in families.items()
                    if v["flags"]]
    return {
        "schema":1,
        "interpretation":"static producer CSV and 5s GPU counters are not a one-to-one per-draw chain",
        "mixed_log_warning":("MULTIPLE_LOG_FILES_NOT_A_SINGLE_PROVEN_SESSION" if len(logs)>1 else None),
        "runtime_validation":"UNTESTED unless matching Quest3/HMD evidence is provided",
        "input_logs":[str(p) for p in logs],"input_hud_csv":[str(p) for p in csvs],
        "invalid_hud_call_rows":invalid,
        "families":families,
        "review_queue":investigations,
        "known_gaps":{
           "main_menu_and_car_selector":"Generic SCREEN_OVERLAY may contain these; exact UI event not identified by R33 family alone",
           "f11":"Separate host/ImGui UI; in-game D3D9 Draw capture cannot prove host overlay",
           "lens_outer":"CABE PROJECTED_SCREEN_EFFECT is still a candidate, not an exact source",
           "openxr":"Compositor eye visibility needs host matching-frame evidence",
           "unvisited_scenes":"NOT_OBSERVED/NOT_CAPTURED is never a PASS or failure",
           "source_only":"CSV caller does not prove a GPU family or left/right submission",
           "identity":"5s aggregate not exact source_serial->GPU draw lifetime, requires detailed bounded events",
        },
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("session",type=Path,help="session log file or extracted collector directory")
    ap.add_argument("--output",type=Path,default=None)
    opt=ap.parse_args()
    result=analyze(opt.session)
    data=json.dumps(result,ensure_ascii=False,indent=2)
    if opt.output:
        opt.output.parent.mkdir(parents=True,exist_ok=True)
        opt.output.write_text(data+"\n",encoding="utf-8")
        print(str(opt.output))
    else:print(data)

if __name__=="__main__":main()