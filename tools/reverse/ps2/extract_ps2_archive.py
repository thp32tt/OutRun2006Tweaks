#!/usr/bin/env python3
"""Extract the PS2 container layout observed in SYSTEM/JSPRITE/JSPRANI/COMMON/BK/DRIVER."""
import argparse
import json
import pathlib
import struct
import zlib

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("archive", type=pathlib.Path)
    ap.add_argument("out", type=pathlib.Path)
    args = ap.parse_args()

    blob = args.archive.read_bytes()
    if len(blob) < 16:
        raise SystemExit("archive too small")

    header = struct.unpack_from("<4I", blob, 0)
    count = header[0]
    if not (0 < count < 100000) or any(x != count for x in header):
        raise SystemExit("unrecognized PS2 container header")

    args.out.mkdir(parents=True, exist_ok=True)
    rows = []
    for index in range(count):
        entry_hash, offset, stored_size, size2 = struct.unpack_from("<4I", blob, 16 + index * 16)
        if offset + stored_size > len(blob):
            raise SystemExit(f"entry {index} is out of range")

        raw = blob[offset:offset + stored_size]
        decoded = raw
        mode = "raw"
        if len(raw) >= 2 and raw[0] == 0x78:
            try:
                decoded = zlib.decompress(raw)
                mode = "zlib"
            except zlib.error:
                pass

        suffix = ".bin"
        if decoded.startswith(b"\x7fELF"):
            suffix = ".elf"
        elif decoded.startswith(b"COLI"):
            suffix = ".coli"
        elif decoded.startswith(b"SOV"):
            suffix = ".sov"

        filename = f"{index:03d}_{entry_hash:08x}{suffix}"
        (args.out / filename).write_bytes(decoded)
        rows.append({
            "index": index,
            "hash": f"{entry_hash:08x}",
            "offset": offset,
            "stored": stored_size,
            "size2": size2,
            "decoded": len(decoded),
            "mode": mode,
            "magic": decoded[:16].hex(),
            "file": filename,
        })

    (args.out / "manifest.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "archive": str(args.archive),
        "entries": count,
        "zlib_entries": sum(x["mode"] == "zlib" for x in rows),
        "decoded_total": sum(x["decoded"] for x in rows),
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
