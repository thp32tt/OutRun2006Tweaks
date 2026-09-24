#!/usr/bin/env python3
import argparse
import hashlib
import struct
from pathlib import Path
from PIL import Image

DDS_MAGIC = b"DDS "
HEADER_SIZE = 128

def source_info(blob):
    if len(blob) < HEADER_SIZE or blob[:4] != DDS_MAGIC:
        raise ValueError("not a DDS file")
    height = struct.unpack_from("<I", blob, 12)[0]
    width = struct.unpack_from("<I", blob, 16)[0]
    pitch = struct.unpack_from("<I", blob, 20)[0]
    mip_count = struct.unpack_from("<I", blob, 28)[0]
    pf_flags = struct.unpack_from("<I", blob, 80)[0]
    fourcc = blob[84:88]
    rgb_bits = struct.unpack_from("<I", blob, 88)[0]
    masks = struct.unpack_from("<IIII", blob, 92)
    return width, height, pitch, mip_count, pf_flags, fourcc, rgb_bits, masks

def main():
    ap = argparse.ArgumentParser(
        description="Replace pixels in a simple uncompressed 32-bit BGRA DDS while preserving its original header byte-for-byte."
    )
    ap.add_argument("source_dds")
    ap.add_argument("replacement_png")
    ap.add_argument("output_dds")
    args = ap.parse_args()

    source = Path(args.source_dds).read_bytes()
    width, height, pitch, mip_count, pf_flags, fourcc, rgb_bits, masks = source_info(source)

    expected_masks = (0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    if fourcc != b"\x00\x00\x00\x00" or rgb_bits != 32 or masks != expected_masks:
        raise SystemExit(
            "unsupported DDS: this proof writer only supports uncompressed 32-bit BGRA with ARGB masks"
        )
    if pitch != width * 4:
        raise SystemExit(f"unexpected pitch {pitch}; expected {width * 4}")
    if len(source) != HEADER_SIZE + width * height * 4:
        raise SystemExit(
            "unsupported DDS payload size (mipmaps or extra data may be present)"
        )

    image = Image.open(args.replacement_png).convert("RGBA")
    if image.size != (width, height):
        raise SystemExit(
            f"replacement size {image.size} does not match source {(width, height)}"
        )

    rgba = image.tobytes()
    bgra = bytearray(len(rgba))
    for i in range(0, len(rgba), 4):
        r, g, b, a = rgba[i:i+4]
        bgra[i:i+4] = bytes((b, g, r, a))

    output = source[:HEADER_SIZE] + bytes(bgra)
    Path(args.output_dds).write_bytes(output)

    if output[:HEADER_SIZE] != source[:HEADER_SIZE]:
        raise SystemExit("internal error: DDS header changed")

    print(f"size={width}x{height}")
    print(f"source_mip_count={mip_count}")
    print("header_preserved=true")
    print("sha256=" + hashlib.sha256(output).hexdigest())

if __name__ == "__main__":
    main()
