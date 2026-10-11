#!/usr/bin/env python3
"""C1 lane: consume ChatGPT-generated PNG inputs only; NEVER generate font/vector glyphs.

The ChatGPT project C1 invocation calls ImageGen and commits a real PNG + manifest
under imagegen_requests. GitHub Actions automatically runs this deterministic
consumer when a request arrives. No request = transparent no-op, not a QA PASS.
"""
import hashlib
import json
import os
from pathlib import Path
import sys

assert os.getenv("OUTRUN_CPU_WORKER") == "github-actions"
assert os.getenv("OUTRUN_CPU_ROLE") == "C1"
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path("tools/localization").resolve()))
from imagegen_b_pipeline import run

base = Path("localization/graphics/role_C1/imagegen_requests")
if not base.exists():
    print("C1_IMAGEGEN_INPUT_REQUIRED: no genuine ImageGen PNG/manifest staged; no fallback.")
    sys.exit(0)
manifests = sorted(base.glob("*.json"))
if not manifests:
    print("C1_IMAGEGEN_INPUT_REQUIRED: no JSON requests; no font/vector fallback.")
    sys.exit(0)
new = []
for mf in manifests:
    rec = json.loads(mf.read_text(encoding="utf-8"))
    path = Path(rec.get("output_dir", ""))
    if not path.as_posix().startswith("localization/graphics/role_C1/imagegen_trials/"):
        raise ValueError("ImageGen output_dir must be a scoped role_C1 imagegen_trials dir")
    report = path / ("C1_IMAGEGEN_" + str(rec["queue_index"]).zfill(3) + "_MACHINE.json")
    mh = hashlib.sha256(mf.read_bytes()).hexdigest()
    if report.is_file():
        done = json.loads(report.read_text(encoding="utf-8"))
        if done.get("manifest_sha256") == mh:
            print("C1_IMAGEGEN_SKIP_SAME_MANIFEST_SHA", str(mf))
            continue
        raise ValueError("Existing output directory has different ImageGen manifest SHA: " + str(report))
    new.append(mf)
if not new:
    print("C1_IMAGEGEN_NO_NEW_INPUTS: previously processed SHA only, 0 new candidates")
    sys.exit(0)
# One new unqualified family pilot per run; agent/queue controls priority.
chosen = new[0]
print("C1_IMAGEGEN_CONSUME_REAL_GENERATED_INPUT:", str(chosen), flush=True)
output = run(Path("."), chosen)
print(json.dumps({"result": "C1_IMAGEGEN_SAVED_TRIAL_VISUAL_PENDING",
                  "queue_index": output["queue_index"],
                  "candidate_sha256": output["saved_trial_sha256"],
                  "pending_requests": len(new)-1}, ensure_ascii=False), flush=True)
