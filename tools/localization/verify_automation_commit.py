#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, pathlib, struct, subprocess

root = pathlib.Path(__file__).resolve().parents[2]
before = os.environ.get("VERIFY_BEFORE", "").strip() or os.environ.get("GITHUB_EVENT_BEFORE", "").strip()
head = os.environ.get("VERIFY_HEAD", "").strip() or os.environ.get("GITHUB_SHA", "").strip() or "HEAD"
if not before or set(before) == {"0"}:
    before = subprocess.check_output(["git","rev-parse",f"{head}^"], cwd=root, text=True).strip()

changed = subprocess.check_output(["git","diff","--name-only",before,head], cwd=root, text=True).splitlines()
dds = [root / p for p in changed if p.lower().endswith(".dds")]
report_paths = [p for p in changed if p.startswith("localization/graphics/") and p.lower().endswith(".json")]

def git_blob_bytes(revision: str, rel: str) -> bytes:
    try:
        return subprocess.check_output(["git","show",f"{revision}:{rel}"], cwd=root)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"changed file missing from revision {revision}: {rel}") from exc

def dds_info(rel: str, data: bytes):
    if len(data) < 128 or data[:4] != b"DDS ":
        raise SystemExit(f"invalid DDS header: {rel}")
    height = struct.unpack_from("<I", data, 12)[0]
    width = struct.unpack_from("<I", data, 16)[0]
    mipmaps = struct.unpack_from("<I", data, 28)[0] or 1
    fourcc = data[84:88]
    if width <= 0 or height <= 0 or mipmaps < 1:
        raise SystemExit(f"invalid DDS metadata: {rel}")
    return {"width":width,"height":height,"mipmaps":mipmaps,"fourcc":fourcc.hex(),
            "sha256":hashlib.sha256(data).hexdigest()}

def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values(): yield from walk(v)
    elif isinstance(obj, list):
        for v in obj: yield from walk(v)

def qa_pass_records():
    records=[]
    for rel in report_paths:
        try: obj=json.loads(git_blob_bytes(head, rel).decode("utf-8"))
        except Exception: continue
        for d in walk(obj):
            status=str(d.get("status",d.get("result",""))).upper()
            if status in {"PASS","STATIC_PASS","PASS_STRICT","OK"} or "PASS" in status:
                records.append((rel,d))
    return records

for p in dds:
    rel = p.relative_to(root).as_posix()
    dds_info(rel, git_blob_bytes(head, rel))

if dds and not report_paths:
    raise SystemExit("DDS changed without localization/graphics JSON QA report in same commit")

if dds:
    records=qa_pass_records()
    if not records:
        raise SystemExit("DDS changed but no machine-readable PASS record exists in changed QA JSON")
    required_post_reset=("source_sha256","candidate_dds_sha256","runtime_validation","prompt_contract","prompt_sha256","prompt_json_sha256","signed_slant_gate","asset_id")
    zero_keys=("changed_pixels_outside_edit_mask","changed_pixels_outside_source_region",
               "changed_pixels_in_protected_mask","introduced_alpha_outside_source_region",
               "alpha_changed_outside_edit_mask")
    bad=[]
    seen_zero_gate=False
    seen_post_reset=False
    for rel,d in records:
        if all(k in d for k in required_post_reset):
            seen_post_reset=True
            prompt_contract=str(d.get("prompt_contract",""))
            if prompt_contract not in {"outrun-first-pass-edit-v1","outrun-first-pass-edit-v2"}:
                bad.append(f"{rel}:invalid_prompt_contract")
            try:
                schema_version=int(d.get("schema_version",0) or 0)
            except Exception:
                schema_version=0
            if schema_version >= 10 and prompt_contract != "outrun-first-pass-edit-v2":
                bad.append(f"{rel}:schema_v{schema_version}_requires_v2_prompt_contract")
            if len(str(d.get("prompt_sha256","")))!=64 or len(str(d.get("prompt_json_sha256","")))!=64:
                bad.append(f"{rel}:invalid_prompt_hash")
            if d.get("signed_slant_gate")!="PASS":
                bad.append(f"{rel}:signed_slant_gate_invalid")
            rv=str(d.get("runtime_validation","")).upper()
            if rv not in {"UNTESTED","PASS"}:
                bad.append(f"{rel}:runtime_validation={rv}")
        for metric_obj in walk(d):
            for k in zero_keys:
                if k in metric_obj:
                    seen_zero_gate=True
                    try:
                        if int(metric_obj[k]) != 0: bad.append(f"{rel}:{k}={metric_obj[k]}")
                    except Exception: bad.append(f"{rel}:{k}=INVALID")
    if bad:
        raise SystemExit("post-reset zero-pixel QA failed: "+"; ".join(bad))
    if not seen_zero_gate:
        raise SystemExit("DDS changed but PASS reports contain no post-reset zero-pixel/protected-mask metrics")
    if not seen_post_reset:
        raise SystemExit("DDS changed but PASS reports lack post-reset provenance fields (source/candidate SHA and runtime validation)")

print(f"changed_dds={len(dds)} qa_reports={len(report_paths)}")
print("AUTOMATION_VALIDATION strict machine-readable graphics gate PASS; runtime remains UNTESTED unless separately proven")
