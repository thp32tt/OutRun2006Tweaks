#!/usr/bin/env python3
from __future__ import annotations
import os, pathlib, struct, subprocess, sys

root = pathlib.Path(__file__).resolve().parents[2]
before = os.environ.get("GITHUB_EVENT_BEFORE", "").strip()
head = os.environ.get("GITHUB_SHA", "").strip() or "HEAD"
if not before or set(before) == {"0"}:
    before = subprocess.check_output(["git","rev-parse",f"{head}^"], cwd=root, text=True).strip()

changed = subprocess.check_output(["git","diff","--name-only",before,head], cwd=root, text=True).splitlines()
dds = [root / p for p in changed if p.lower().endswith(".dds")]
reports = [p for p in changed if p.startswith("localization/graphics/") and p.lower().endswith(".json")]

def check_dds(path: pathlib.Path):
    data = path.read_bytes()
    if len(data) < 128 or data[:4] != b"DDS ":
        raise SystemExit(f"invalid DDS header: {path}")
    height, width, mipmaps = struct.unpack_from("<III", data, 12)
    if width <= 0 or height <= 0:
        raise SystemExit(f"invalid DDS dimensions: {path}")
    if mipmaps == 0:
        mipmaps = 1
    if mipmaps < 1:
        raise SystemExit(f"invalid DDS mip count: {path}")

for p in dds:
    if not p.exists():
        raise SystemExit(f"changed DDS missing from checkout: {p}")
    check_dds(p)

if dds and not reports:
    raise SystemExit("DDS changed without a localization/graphics JSON QA report in the same commit")

print(f"changed_dds={len(dds)} qa_reports={len(reports)}")
print("AUTOMATION_VALIDATION structural DDS gate PASS; runtime remains UNTESTED unless separately proven")
