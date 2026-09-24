#!/usr/bin/env python3
"""Analyze a decompressed OutRun 2 SP JSPRANI entry.

Verified fields only:
- u32 at physical +0: payload length, equal to file_size - 4
- logical base = physical +4
- zero-terminated root-offset array at logical base
- root: <group_count, group_ptr, track_count, track_ptr>
- group stride 0x24: +0x1c child count, +0x20 child pointer
- node stride 0x4c
- track stride 0x18: +0 x, +4 y, +0xc frame_count, +0x10 frame_ptr
- frame stride 0x14: first word low16 = sprite index before relocation
"""
from __future__ import annotations
import argparse, json, pathlib, struct

def u32(b, o):
    if o < 0 or o + 4 > len(b):
        raise ValueError(f"u32 out of range: 0x{o:X}")
    return struct.unpack_from("<I", b, o)[0]

def i32(b, o):
    if o < 0 or o + 4 > len(b):
        raise ValueError(f"i32 out of range: 0x{o:X}")
    return struct.unpack_from("<i", b, o)[0]

def phys(logical_off):
    return 4 + logical_off

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=pathlib.Path)
    ap.add_argument("--resource-id", type=lambda x:int(x,0))
    args = ap.parse_args()
    b = args.file.read_bytes()
    if len(b) < 8:
        raise SystemExit("file too small")
    declared = u32(b, 0)
    if declared != len(b) - 4:
        raise SystemExit(f"length mismatch: declared={declared} actual={len(b)-4}")

    roots = []
    pos = 4
    while pos + 4 <= len(b):
        off = u32(b, pos)
        if off == 0:
            break
        if phys(off) + 16 > len(b):
            raise SystemExit(f"invalid root offset 0x{off:X}")
        roots.append(off)
        pos += 4

    groups = nodes = tracks = frames = 0
    xs, ys, sprite_indices = [], [], []

    for roff in roots:
        rp = phys(roff)
        gcount, gptr, tcount, tptr = struct.unpack_from("<IIII", b, rp)
        groups += gcount
        tracks += tcount

        for i in range(gcount):
            gp = phys(gptr + i * 0x24)
            child_count = u32(b, gp + 0x1c)
            child_ptr = u32(b, gp + 0x20)
            if child_count and phys(child_ptr + child_count * 0x4c - 1) >= len(b):
                raise SystemExit(f"invalid node span from root 0x{roff:X}")
            nodes += child_count

        for i in range(tcount):
            tp = phys(tptr + i * 0x18)
            x, y = i32(b, tp), i32(b, tp + 4)
            fcount, fptr = u32(b, tp + 0x0c), u32(b, tp + 0x10)
            xs.append(x); ys.append(y)
            frames += fcount
            for j in range(fcount):
                fp = phys(fptr + j * 0x14)
                word = u32(b, fp)
                sprite_indices.append(word & 0xffff)

    out = {
        "file": str(args.file),
        "declared_payload_length": declared,
        "roots": len(roots),
        "groups": groups,
        "nodes": nodes,
        "tracks": tracks,
        "frames": frames,
        "x_min": min(xs) if xs else None,
        "x_max": max(xs) if xs else None,
        "y_min": min(ys) if ys else None,
        "y_max": max(ys) if ys else None,
        "unique_sprite_indices": len(set(sprite_indices)),
        "max_sprite_index": max(sprite_indices) if sprite_indices else None,
    }
    if args.resource_id is not None:
        out["resource_id"] = f"0x{args.resource_id:04X}"
        out["full_sprite_id_min"] = f"0x{args.resource_id << 16:08X}"
        if sprite_indices:
            out["full_sprite_id_max_observed"] = f"0x{((args.resource_id << 16) | max(sprite_indices)):08X}"
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
