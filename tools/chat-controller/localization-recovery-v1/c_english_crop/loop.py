#!/usr/bin/env python3
"""OutRun C native English crop worker. Offline, queue-only, no generators."""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time
import traceback

BASE = Path("/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only")
SOURCE = Path("/home/chatgpt-runner2/work/c_salvage_text_roi/source_full_20261012")
MANIFEST = Path("/home/chatgpt-runner2/work/c_salvage_text_roi/original_hd_phrase_crops_20261016/MASTER_255_V2_20261016/MASTER_CROP_MANIFEST_255.json")
sys.path.insert(0, "/app")
sys.path.append(str(BASE))
import c_crop_only_runner as verified_runner
import c_original_hd_crop_only_checked_20261016 as crop_helper
import discover
import ocr_recognize
import ocr_hd108

STOP = False

def shutdown(_signal, _frame):
    global STOP
    STOP = True

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

def sha(path):
    d = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            d.update(b)
    return d.hexdigest()

def archive_keys():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data.get("total_native_crop_png") != 255 or len(data.get("items", [])) != 255:
        raise ValueError("MASTER_255_ARCHIVE_INVALID")
    keys = set()
    for item in data["items"]:
        q = str(item.get("id","")).split("-")[0].upper()
        box = item.get("bbox_xyxy")
        if q and isinstance(box,list) and len(box)==4:
            keys.add((q,tuple(box)))
    return keys

def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def write_audit(row):
    row = {"time_utc":stamp(),"worker":"docker-c-original-english-v1",**row}
    with (BASE/"docker_run_audit.jsonl").open("a",encoding="utf-8") as f:
        f.write(json.dumps(row,ensure_ascii=False)+"\n")
    tmp = BASE/"docker_last_run.json.tmp"
    tmp.write_text(json.dumps(row,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    os.replace(tmp,BASE/"docker_last_run.json")
    print(json.dumps(row,ensure_ascii=False),flush=True)

def process_batch(limit):
    known = archive_keys()
    completed = 0
    held = 0
    skipped = 0
    queued = sorted((BASE/"queue_specs").glob("*.json"))
    for spec in queued:
        if completed >= limit or STOP: break
        try:
            if spec.is_symlink(): raise ValueError("SYMLINK_SPEC_REJECTED")
            obj = json.loads(spec.read_text(encoding="utf-8"))
            regions = obj.get("regions",[])
            if len(regions)!=1: raise ValueError("ONE_PHRASE_ONLY")
            region = regions[0]
            q = obj["queue_id"].upper()
            label = region["id"]
            outname = q+"-"+label
            if not q.startswith("Q") or not all(c.isalnum() or c in "_-" for c in label):
                raise ValueError("INVALID_QUEUE_ID")
            if (q,tuple(region["bbox_xyxy"])) in known:
                skipped += 1
                continue  # Already archived: NEVER export again
            output = BASE/"outputs"/outname
            if output.exists():
                skipped += 1
                continue  # Already exported: never overwrite
            # Fail closed. Only SHA/DDS-pixel-verified sources in the live allowlist.
            verified_runner.check_original(obj)
            result = crop_helper.run(spec,SOURCE,BASE/"outputs")
            if result.get("hold") or len(result.get("ready",[]))!=1:
                raise ValueError("CROP_HELPER_HOLD:"+json.dumps(result.get("hold"),ensure_ascii=False))
            manifest = json.loads((output/"crop_manifest.json").read_text(encoding="utf-8"))
            if sha(output/"english_original_native_crop.png") != manifest["crop_png_sha256"]:
                raise ValueError("OUTPUT_SHA_MISMATCH")
            write_audit({"status":"NEW_CROP_TEST_ONLY","spec":spec.name,"id":outname,
                         "crop_sha256":manifest["crop_png_sha256"],
                         "source_sha256":manifest["source_full_png_sha256"],
                         "RUNTIME_VALIDATION":"UNTESTED","A_B":"STOPPED_UNTOUCHED"})
            completed += 1
        except Exception as e:
            held += 1
            reason = type(e).__name__+":"+str(e)
            # Deduplicate identical holds; preserve queue specs and existing output.
            holds = BASE/"docker_holds"
            holds.mkdir(exist_ok=True)
            target = holds/(spec.stem+".json")
            row = {"status":"HOLD","spec":spec.name,"reason":reason,"at":stamp()}
            if not target.exists() or json.loads(target.read_text(encoding="utf-8")).get("reason")!=reason:
                target.write_text(json.dumps(row,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
                write_audit(row)
    return {"status":"BATCH","completed":completed,"held":held,"skipped_existing":skipped,"queued":len(queued)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval-seconds",type=int,default=60)
    ap.add_argument("--max-per-cycle",type=int,default=10)
    ap.add_argument("--once",action="store_true")
    args = ap.parse_args()
    if args.interval_seconds < 20 or args.max_per_cycle not in range(1,21):
        raise SystemExit("INVALID_CROP_LIMITS")
    BASE.mkdir(parents=True,exist_ok=True)
    (BASE/"queue_specs").mkdir(exist_ok=True)
    (BASE/"outputs").mkdir(exist_ok=True)
    lockfile = BASE/".docker.run.lock"
    with lockfile.open("a+") as f:
        fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        print(json.dumps({"status":"STARTED","interval_seconds":args.interval_seconds,
                          "max_per_cycle":args.max_per_cycle,"mode":"C_NATIVE_ENGLISH_CROP_ONLY",
                          "RUNTIME_VALIDATION":"UNTESTED"}),flush=True)
        last_summary = None
        last_hd108_status = None
        last_edge_status = None
        last_coverage_status = None
        heartbeat = 0.0
        last_discovery = -1000000.0
        while not STOP:
            try:
                now=time.monotonic()
                if now-last_discovery >= 60:
                    last_discovery=now
                    try:
                        # Coverage-driven scan: a source is revisited until every
                        # reviewed phrase has a crop. OCR strategy rotates by attempt.
                        original108=ocr_hd108.scan(max_sources=4, max_new=1000)
                        hd_sig=(original108.get("status"),
                                original108.get("pending_sources_after"),
                                original108.get("pending_phrases_after"))
                        if original108.get("new_crops") or hd_sig!=last_hd108_status:
                            write_audit(original108)
                        last_hd108_status=hd_sig

                        # Edge warnings are progressively expanded and only stop
                        # blocking after a safe or max-context/C1-required crop exists.
                        edge_review=ocr_hd108.review_edge_warnings(max_items=args.max_per_cycle)
                        edge_sig=(edge_review.get("status"),edge_review.get("pending_after"),
                                  edge_review.get("rescued"),edge_review.get("held"))
                        if edge_review.get("reviewed") or edge_sig!=last_edge_status:
                            write_audit(edge_review)
                        last_edge_status=edge_sig

                        phrase_pending=int(original108.get("pending_phrases_after",
                                                           original108.get("pending_phrases_before",0)) or 0)
                        edge_pending=int(edge_review.get("pending_after",0) or 0)
                        coverage_status={
                            "status":("C_CROP_COVERAGE_COMPLETE"
                                      if phrase_pending==0 and edge_pending==0
                                      else "C_CROP_COVERAGE_RUNNING"),
                            "reviewed_phrase_total":original108.get("reviewed_phrase_total"),
                            "located_phrase_count":original108.get("located_phrase_count"),
                            "pending_sources":original108.get("pending_sources_after",
                                                              original108.get("pending_sources_before")),
                            "pending_phrases":phrase_pending,
                            "edge_pending":edge_pending,
                            "new_crops_this_cycle":original108.get("new_crops",0),
                            "edge_rescued_this_cycle":edge_review.get("rescued",0),
                            "RUNTIME_VALIDATION":"UNTESTED",
                        }
                        coverage_sig=(coverage_status["status"],coverage_status["pending_sources"],
                                      coverage_status["pending_phrases"],coverage_status["edge_pending"])
                        if (coverage_status["new_crops_this_cycle"] or
                            coverage_status["edge_rescued_this_cycle"] or
                            coverage_sig!=last_coverage_status):
                            write_audit(coverage_status)
                        last_coverage_status=coverage_sig
                    except Exception as e:
                        write_audit({"status":"DISCOVERY_HOLD","reason":type(e).__name__+":"+str(e)})
                summary = process_batch(args.max_per_cycle)
                if summary != last_summary or summary["completed"] or time.monotonic()-heartbeat>1800:
                    print(json.dumps({"timestamp":stamp(),**summary}),flush=True)
                    last_summary = summary
                    heartbeat = time.monotonic()
            except Exception as e:
                write_audit({"status":"WORKER_HOLD","error":str(e)})
            if args.once: break
            for _ in range(args.interval_seconds):
                if STOP: break
                time.sleep(1)

if __name__=="__main__":
    main()