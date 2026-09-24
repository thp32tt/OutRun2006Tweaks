#!/usr/bin/env python3
import argparse
import csv
import hashlib
import struct
from pathlib import Path

def dds_size(path: Path):
    data = path.read_bytes()[:128]
    if len(data) < 20 or data[:4] != b"DDS ":
        return None, None
    height = struct.unpack_from("<I", data, 12)[0]
    width = struct.unpack_from("<I", data, 16)[0]
    return width, height

def classify(rel: str):
    s = rel.lower()
    if "font" in s:
        return "font"
    if "name_entry" in s or "name5" in s or "name_cmn" in s:
        return "name_entry"
    if "selector" in s or "select" in s:
        return "selector"
    if "ranking" in s or "_rank" in s:
        return "ranking"
    if "route" in s:
        return "route"
    if "loading" in s:
        return "loading"
    if "game_cvt" in s:
        return "game_ui"
    if "sumo_fe" in s:
        return "front_end"
    if "etc" in s:
        return "common_ui"
    return "other"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("csv")
    args = ap.parse_args()
    root = Path(args.root)
    files = sorted(root.rglob("*.dds"))
    with open(args.csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["path", "category", "width", "height", "bytes", "sha256", "status"])
        for p in files:
            rel = p.relative_to(root).as_posix()
            width, height = dds_size(p)
            blob = p.read_bytes()
            w.writerow([
                rel, classify(rel), width or "", height or "",
                len(blob), hashlib.sha256(blob).hexdigest(), "TODO_VISUAL_REVIEW"
            ])
    print(f"wrote {len(files)} DDS entries -> {args.csv}")

if __name__ == "__main__":
    main()
