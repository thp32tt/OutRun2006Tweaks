#!/usr/bin/env python3
"""Strict texture-only preservation gate for the native PMT exporter layout."""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def snapshot(path):
    data = path.read_bytes()
    if len(data) < 28 or struct.unpack_from("<4sII", data) != (b"glTF", 2, len(data)):
        raise ValueError("invalid GLB header")
    size, kind = struct.unpack_from("<I4s", data, 12)
    end = 20 + size
    if kind != b"JSON" or size % 4 or end + 8 > len(data):
        raise ValueError("invalid JSON chunk")
    doc = json.loads(data[20:end])
    size, kind = struct.unpack_from("<I4s", data, end)
    if kind != b"BIN\0" or size % 4 or end + 8 + size != len(data):
        raise ValueError("invalid BIN chunk")
    blob = memoryview(data)[end + 8:]
    buffers = doc.pop("buffers")
    if len(buffers) != 1 or "uri" in buffers[0]:
        raise ValueError("expected one embedded buffer")
    length = buffers[0]["byteLength"]
    if not 0 <= size - length <= 3 or doc["asset"]["version"] != "2.0":
        raise ValueError("invalid embedded buffer")
    if any(doc.get(key) for key in ("extensionsUsed", "extensionsRequired")):
        raise ValueError("extensions are outside the PMT texture-only profile")

    images = doc.get("images", [])
    image_views = {image["bufferView"] for image in images}
    views = doc["bufferViews"]
    if any("uri" in image for image in images) or any(
        not 0 <= index < len(views) for index in image_views
    ):
        raise ValueError("invalid embedded image reference")
    for accessor in doc["accessors"]:
        index = accessor["bufferView"]
        if "sparse" in accessor or not 0 <= index < len(views) or index in image_views:
            raise ValueError("unsupported or aliased accessor")

    intervals = []
    digests = {}
    for index, view in enumerate(views):
        start = view.pop("byteOffset", 0)
        count = view["byteLength"]
        stop = start + count
        if view["buffer"] != 0 or start % 4 or not 0 <= start < stop <= length:
            raise ValueError(f"invalid bufferView {index}")
        intervals.append((start, stop))
        digest = hashlib.sha256(blob[start:stop]).hexdigest()
        if index in image_views:
            view.pop("byteLength")
            digests[index] = digest
        else:
            view["payload_sha256"] = digest
    previous_end = 0
    for start, stop in sorted(intervals):
        if start < previous_end:
            raise ValueError("overlapping bufferViews")
        previous_end = stop
    return doc, [digests[image["bufferView"]] for image in images]


def audit(before, after):
    before_doc, before_images = snapshot(before)
    after_doc, after_images = snapshot(after)
    changed = [key for key in sorted(before_doc.keys() | after_doc.keys())
               if before_doc.get(key) != after_doc.get(key)]
    if changed:
        raise ValueError("texture-only contract changed: " + ", ".join(changed))
    return {"preserved": True, "profile": "native PMT exporter texture-only",
            "changed_images": [i for i, (a, b) in enumerate(zip(before_images, after_images))
                               if a != b]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(audit(args.before, args.after), indent=2))
    except (OSError, ValueError, KeyError, TypeError, struct.error) as error:
        parser.exit(2, f"FAIL: {error}\n")


if __name__ == "__main__":
    main()
