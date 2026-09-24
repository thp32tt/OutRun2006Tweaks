#!/usr/bin/env python3
import argparse
import base64
import hashlib
import json
import struct
from pathlib import Path

MAGIC = b"txet"


def read_txet(path):
    data = Path(path).read_bytes()
    if len(data) < 12 or data[:4] != MAGIC:
        raise ValueError("not a txet file")

    declared = struct.unpack_from("<I", data, 4)[0]
    if declared != len(data):
        raise ValueError(f"size mismatch: header={declared} actual={len(data)}")

    first = struct.unpack_from("<I", data, 8)[0]
    if first < 8 or (first - 8) % 4:
        raise ValueError(f"invalid first string offset: 0x{first:X}")

    count = (first - 8) // 4
    offsets = list(struct.unpack_from(f"<{count}I", data, 8))
    nonzero = [offset for offset in offsets if offset]

    if nonzero != sorted(nonzero) or len(nonzero) != len(set(nonzero)):
        raise ValueError("non-zero offsets are not strictly increasing")

    entries = []
    for index, offset in enumerate(offsets):
        if offset == 0:
            entries.append({"index": index, "null_pointer": True, "raw_b64": ""})
            continue

        next_offset = len(data)
        for candidate in offsets[index + 1 :]:
            if candidate:
                next_offset = candidate
                break

        raw = data[offset:next_offset]
        segments = []
        simple_text = None
        try:
            decoded = raw.decode("utf-16le")
            segments = decoded.split("\x00")
            if segments and segments[-1] == "":
                segments = segments[:-1]
            if len(segments) == 1 and raw.endswith(b"\x00\x00"):
                simple_text = segments[0]
        except UnicodeDecodeError:
            pass

        entries.append(
            {
                "index": index,
                "null_pointer": False,
                "raw_b64": base64.b64encode(raw).decode("ascii"),
                "segments": segments,
                "simple_text": simple_text,
            }
        )

    return {
        "format": "txet",
        "source_size": len(data),
        "entry_count": count,
        "entries": entries,
    }, data


def build_txet(document):
    entries = document["entries"]
    count = len(entries)
    header_size = 8 + 4 * count
    payload = bytearray()
    offsets = []

    for entry in entries:
        if entry.get("null_pointer"):
            offsets.append(0)
            continue

        offsets.append(header_size + len(payload))
        payload += base64.b64decode(entry["raw_b64"])

    total = header_size + len(payload)
    return (
        bytearray(MAGIC)
        + struct.pack("<I", total)
        + struct.pack(f"<{count}I", *offsets)
        + payload
    )


def main():
    parser = argparse.ArgumentParser(
        description="Lossless OutRun 2006 txet BIN utility"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("bin")

    extract_parser = subparsers.add_parser("extract")
    extract_parser.add_argument("bin")
    extract_parser.add_argument("json")

    rebuild_parser = subparsers.add_parser("rebuild")
    rebuild_parser.add_argument("json")
    rebuild_parser.add_argument("bin")

    patch_parser = subparsers.add_parser("patch")
    patch_parser.add_argument("bin")
    patch_parser.add_argument("out")
    patch_parser.add_argument("--index", type=int, required=True)
    patch_parser.add_argument("--text", required=True)

    args = parser.parse_args()

    if args.command == "inspect":
        document, data = read_txet(args.bin)
        simple = sum(
            1 for entry in document["entries"]
            if entry.get("simple_text") is not None
        )
        special = sum(
            1 for entry in document["entries"]
            if entry.get("segments") and entry.get("simple_text") is None
        )
        null = sum(
            1 for entry in document["entries"]
            if entry.get("null_pointer")
        )
        print(
            f"size={len(data)} entries={document['entry_count']} "
            f"simple={simple} multi_or_special={special} null={null}"
        )
        print("sha256=" + hashlib.sha256(data).hexdigest())

    elif args.command == "extract":
        document, data = read_txet(args.bin)
        document["source_sha256"] = hashlib.sha256(data).hexdigest()
        Path(args.json).write_text(
            json.dumps(document, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    elif args.command == "rebuild":
        document = json.loads(Path(args.json).read_text(encoding="utf-8"))
        output = bytes(build_txet(document))
        Path(args.bin).write_bytes(output)
        print("sha256=" + hashlib.sha256(output).hexdigest())

    elif args.command == "patch":
        document, _ = read_txet(args.bin)
        if not 0 <= args.index < len(document["entries"]):
            raise SystemExit("index out of range")

        entry = document["entries"][args.index]
        if entry.get("null_pointer"):
            raise SystemExit("cannot patch null pointer entry")
        if entry.get("simple_text") is None:
            raise SystemExit("refusing to patch multi/special record")

        raw = args.text.encode("utf-16le") + b"\x00\x00"
        entry["raw_b64"] = base64.b64encode(raw).decode("ascii")
        entry["segments"] = [args.text]
        entry["simple_text"] = args.text

        output = bytes(build_txet(document))
        Path(args.out).write_bytes(output)
        print(f"patched index {args.index}: {args.text}")
        print("sha256=" + hashlib.sha256(output).hexdigest())


if __name__ == "__main__":
    main()
