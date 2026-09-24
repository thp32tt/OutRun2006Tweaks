#!/usr/bin/env python3
import argparse
import csv
import hashlib
import struct
from pathlib import Path

def read_txet(path: Path):
    data = path.read_bytes()
    if len(data) < 12 or data[:4] != b"txet":
        raise ValueError("not a txet file")
    declared = struct.unpack_from("<I", data, 4)[0]
    if declared != len(data):
        raise ValueError(f"size mismatch: header={declared} actual={len(data)}")
    first = struct.unpack_from("<I", data, 8)[0]
    if first < 8 or (first - 8) % 4:
        raise ValueError("invalid offset table")
    count = (first - 8) // 4
    offsets = list(struct.unpack_from(f"<{count}I", data, 8))
    rows = []
    for i, off in enumerate(offsets):
        if not off:
            rows.append([i, "", "NULL", "", ""])
            continue
        end = next((x for x in offsets[i + 1:] if x), len(data))
        raw = data[off:end]
        rec_hash = hashlib.sha256(raw).hexdigest()
        try:
            decoded = raw.decode("utf-16le")
            parts = decoded.split("\x00")
            if parts and parts[-1] == "":
                parts.pop()
            kind = "SIMPLE" if len(parts) == 1 and raw.endswith(b"\x00\x00") else "SPECIAL"
            source = parts[0] if parts else ""
        except UnicodeDecodeError:
            kind = "BINARY"
            source = ""
        rows.append([i, source, kind, len(raw), rec_hash])
    return rows, hashlib.sha256(data).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bin")
    ap.add_argument("csv")
    args = ap.parse_args()
    rows, source_hash = read_txet(Path(args.bin))
    with open(args.csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["# source_sha256", source_hash])
        w.writerow(["id", "source", "record_type", "raw_bytes", "record_sha256"])
        w.writerows(rows)
    print(f"wrote {len(rows)} entries -> {args.csv}")
    print(f"source_sha256={source_hash}")

if __name__ == "__main__":
    main()
