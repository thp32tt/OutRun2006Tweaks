#!/usr/bin/env python3
"""Inspect/extract Sumo-style PS2 resource packs used by OutRun 2 SP.

Header:
  0x00: four copies of entry_count (u32 LE)
  0x10: entry_count records of <hash, file_offset, compressed_size, compressed_size>

Most resource entries are zlib streams. SYSTEM.PS2 entries are raw IRX/icon files.
"""
from __future__ import annotations
import argparse, hashlib, json, pathlib, struct, zlib

def pack_hash(name: str, seed: int = 0) -> int:
    h = seed & 0xffffffff
    for ch in reversed(name.encode("ascii")):
        if 0x61 <= ch <= 0x7a:
            ch -= 0x20
        h = (h * 131 + ch) & 0xffffffff
    return h

def parse(path: pathlib.Path):
    data = path.read_bytes()
    if len(data) < 16:
        raise SystemExit("file too small")
    counts = struct.unpack_from("<IIII", data, 0)
    if len(set(counts)) != 1:
        raise SystemExit(f"unsupported header counts: {counts}")
    count = counts[0]
    if 16 + count * 16 > len(data):
        raise SystemExit("entry table exceeds file")
    rows = []
    for i in range(count):
        h, off, size_a, size_b = struct.unpack_from("<IIII", data, 16 + i * 16)
        if size_a != size_b:
            raise SystemExit(f"entry {i}: size fields differ")
        if off + size_a > len(data):
            raise SystemExit(f"entry {i}: payload exceeds file")
        rows.append({"index": i, "hash": h, "offset": off, "size": size_a})
    return data, rows

def load_names(path: pathlib.Path | None):
    if not path:
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key = line if line.startswith("\\") else "\\" + line
        out.setdefault(pack_hash(key), key)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pack", type=pathlib.Path)
    ap.add_argument("--out", type=pathlib.Path)
    ap.add_argument("--names", type=pathlib.Path, help="one relative child path per line")
    args = ap.parse_args()

    data, rows = parse(args.pack)
    names = load_names(args.names)
    manifest = {
        "source": str(args.pack),
        "sha256": hashlib.sha256(data).hexdigest(),
        "entry_count": len(rows),
        "entries": [],
    }
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)

    for row in rows:
        off, size = row["offset"], row["size"]
        blob = data[off:off+size]
        rec = dict(row)
        rec["hash_hex"] = f"0x{row['hash']:08X}"
        rec["name"] = names.get(row["hash"])
        rec["compressed_sha256"] = hashlib.sha256(blob).hexdigest()
        rec["codec"] = "raw"
        payload = blob
        try:
            payload = zlib.decompress(blob)
            rec["codec"] = "zlib"
            rec["decompressed_size"] = len(payload)
            rec["decompressed_sha256"] = hashlib.sha256(payload).hexdigest()
        except zlib.error:
            rec["decompressed_size"] = len(payload)

        if args.out:
            stem = f"{row['index']:03d}_{row['hash']:08X}"
            (args.out / f"{stem}_{rec['codec']}.bin").write_bytes(payload)
        manifest["entries"].append(rec)

    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    if args.out:
        (args.out / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")

if __name__ == "__main__":
    main()
