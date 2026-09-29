#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HEAD = os.environ.get("GITHUB_SHA", "").strip() or "HEAD"
message = subprocess.check_output(["git", "log", "-1", "--pretty=%B", HEAD], cwd=ROOT, text=True)

m = re.search(r"\[AUTO:(LOCALIZATION-LOCALIZATION_C-\d+)\]", message)
if not m:
    print("C_BATCH_GATE: current commit is not a C automation task; no producer batch verification required")
    raise SystemExit(0)

task_id = m.group(1)
before = subprocess.check_output(["git", "rev-parse", f"{HEAD}^"], cwd=ROOT, text=True).strip()
changed = subprocess.check_output(["git", "diff", "--name-only", before, HEAD], cwd=ROOT, text=True).splitlines()
expected_record = f"docs/automation/runs/{task_id}.json"
if expected_record not in changed:
    raise SystemExit(f"C_BATCH_GATE: missing changed task record {expected_record}")

record = json.loads(subprocess.check_output(["git", "show", f"{HEAD}:{expected_record}"], cwd=ROOT, text=True))
inputs = record.get("qa_batch_inputs") or []
dispositions = record.get("qa_dispositions") or []
if not inputs:
    raise SystemExit("C_BATCH_GATE: qa_batch_inputs must be non-empty")
if not dispositions:
    raise SystemExit("C_BATCH_GATE: qa_dispositions must be non-empty")

allowed = {"PASS", "REWORK_REQUIRED", "HOLD_STRICT_RECHECK", "SUPERSEDED"}
disp_by_key = {}
for d in dispositions:
    key = (str(d.get("task_id") or ""), str(d.get("result_sha") or ""))
    status = str(d.get("status") or "").upper()
    if not all(key) or status not in allowed:
        raise SystemExit(f"C_BATCH_GATE: invalid disposition {d!r}")
    if key in disp_by_key:
        raise SystemExit(f"C_BATCH_GATE: duplicate disposition for {key}")
    disp_by_key[key] = status

input_keys = {(str(i.get("task_id") or ""), str(i.get("result_sha") or "")) for i in inputs}
if input_keys != set(disp_by_key):
    missing = sorted(input_keys - set(disp_by_key))
    extra = sorted(set(disp_by_key) - input_keys)
    raise SystemExit(f"C_BATCH_GATE: disposition identity mismatch missing={missing} extra={extra}")

failures = []
validated = 0
nonpass = 0
for item in inputs:
    producer_task = str(item.get("task_id") or "")
    sha = str(item.get("result_sha") or "")
    key = (producer_task, sha)
    status = disp_by_key[key]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        failures.append(f"{producer_task}: invalid result_sha {sha!r}")
        continue
    try:
        producer_message = subprocess.check_output(["git", "log", "-1", "--pretty=%B", sha], cwd=ROOT, text=True)
    except subprocess.CalledProcessError:
        failures.append(f"{producer_task}: result SHA {sha} not present in checkout")
        continue
    if f"[AUTO:{producer_task}]" not in producer_message:
        failures.append(f"{producer_task}: SHA {sha} does not carry exact AUTO marker")
        continue
    anc = subprocess.run(["git", "merge-base", "--is-ancestor", sha, HEAD], cwd=ROOT)
    if anc.returncode != 0:
        failures.append(f"{producer_task}: SHA {sha} is not an ancestor of C result {HEAD}")
        continue

    if status != "PASS":
        nonpass += 1
        print(f"C_BATCH_INPUT_NONPASS task={producer_task} sha={sha} disposition={status}")
        continue

    parent = subprocess.check_output(["git", "rev-parse", f"{sha}^"], cwd=ROOT, text=True).strip()
    env = dict(os.environ)
    env["VERIFY_HEAD"] = sha
    env["VERIFY_BEFORE"] = parent

    checks = [
        [sys.executable, "tools/verify_domain_isolation.py", "--base", parent, "--head", sha, "--branch", "korean-localization-clean"],
        [sys.executable, "tools/localization/verify_automation_commit.py"],
        [sys.executable, "tools/localization/verify_parallel_lane_commit.py"],
    ]
    ok = True
    for cmd in checks:
        proc = subprocess.run(cmd, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(f"$ {' '.join(cmd)}\n{proc.stdout}")
        if proc.returncode != 0:
            failures.append(f"{producer_task}@{sha}: {' '.join(cmd)} failed")
            ok = False
            break
    if ok:
        validated += 1
        print(f"C_BATCH_INPUT_PASS task={producer_task} sha={sha}")

if failures:
    raise SystemExit("C_BATCH_GATE failed:\n- " + "\n- ".join(failures))

print(f"C_BATCH_GATE PASS inputs={len(inputs)} strict_pass={validated} nonpass_dispositions={nonpass}")
print("One C Actions Gate validated the immutable producer batch; runtime remains separately UNTESTED unless proven.")
