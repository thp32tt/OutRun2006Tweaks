#!/usr/bin/env python3
"""Verify canonical PE32 x86 player wrapper CALL chain without publishing EXE.

EXT16-008 deliberately proves only two caller edges, NOT body-only ownership
of 0x46BD30 or undocumented duties of 0x49A650.
"""
import argparse
import hashlib
import struct
from pathlib import Path

IMAGE_BASE = 0x400000
CALLER = 0x49F3E0
FIRST = 0x46BD30
FOLLOWUP = 0x49A650
EXE_SHA256 = "68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3"
PREFIX = bytes.fromhex(
    "568b74240856e845c9fcff68f0e7820056e85ab2ffff83c40c5ec3"
)


def rel_target(blob: bytes, start: int, va: int = CALLER) -> int:
    if start < 0 or start + 5 > len(blob) or blob[start] != 0xE8:
        raise ValueError("no bounded near CALL at requested offset")
    return (va + start + 5 + struct.unpack_from("<i", blob, start + 1)[0]) & 0xFFFFFFFF


def verify(prefix: bytes) -> None:
    if prefix != PREFIX:
        raise ValueError("retail 49F3E0 signature differs")
    if rel_target(prefix, 6) != FIRST or rel_target(prefix, 17) != FOLLOWUP:
        raise ValueError("retail two-call chain is not the attested ABI")
    if prefix[11:17] != bytes.fromhex("68f0e7820056"):
        raise ValueError("missing push 82E7F0 / push ESI follow-up arguments")


def verify_followup(code: bytes) -> None:
    if code != b"\xc3":
        raise ValueError("49A650 is not a bare RET in this canonical EXE")


def extract_canonical_exe(path: Path, va: int = CALLER, count_bytes: int = len(PREFIX)) -> bytes:
    binary = path.read_bytes()
    digest = hashlib.sha256(binary).hexdigest()
    if digest != EXE_SHA256:
        raise ValueError("unknown EXE SHA256: " + digest)
    if binary[:2] != b"MZ":
        raise ValueError("invalid DOS header")
    pe = struct.unpack_from("<I", binary, 0x3C)[0]
    if binary[pe:pe + 4] != bytes.fromhex("50450000"):
        raise ValueError("invalid PE signature")
    if struct.unpack_from("<H", binary, pe + 24)[0] != 0x10B:
        raise ValueError("not canonical PE32 x86")
    if struct.unpack_from("<I", binary, pe + 24 + 28)[0] != IMAGE_BASE:
        raise ValueError("unexpected image base")
    count = struct.unpack_from("<H", binary, pe + 6)[0]
    section = pe + 24 + struct.unpack_from("<H", binary, pe + 20)[0]
    rva = va - IMAGE_BASE
    for i in range(count):
        h = section + i * 40
        start, raw_len, offset = struct.unpack_from("<III", binary, h + 12)
        if start <= rva and rva + count_bytes <= start + raw_len:
            pos = offset + rva - start
            if pos + count_bytes > len(binary):
                raise ValueError("truncated section")
            return binary[pos:pos + count_bytes]
    raise ValueError("49F3E0 is unmapped in canonical EXE")


def self_test() -> None:
    verify(PREFIX)
    verify_followup(bytes.fromhex("c3"))
    for bad in (b"", bytes.fromhex("90"), bytes.fromhex("c2"), bytes.fromhex("c300")):
        try:
            verify_followup(bad)
        except ValueError:
            continue
        raise AssertionError("invalid follow-up accepted")
    for offset in (0, 6, 7, 11, 17, 18, 22, 24, 25, 26):
        damaged = bytearray(PREFIX)
        damaged[offset] ^= 1
        try:
            verify(bytes(damaged))
        except ValueError:
            continue
        raise AssertionError(f"corruption at {offset} was accepted")
    for damaged in (PREFIX[:24], PREFIX[:-1], b"", PREFIX + bytes.fromhex("00")):
        try:
            verify(damaged)
        except ValueError:
            continue
        raise AssertionError("wrong-size wrapper accepted")
    for offset in (5, 16, len(PREFIX)):
        try:
            rel_target(PREFIX, offset)
        except ValueError:
            continue
        raise AssertionError("non-CALL accepted")
    print("EXT16_008_ORIGINAL_WRAPPER_CALL_EDGES_SELF_TEST_PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--exe", type=Path)
    options = parser.parse_args()
    if options.self_test:
        self_test()
    if options.exe:
        verify(extract_canonical_exe(options.exe))
        # The decompiled PC x86 build identifies 49A650 as a bare RET.
        # Its identity does not turn 46BD30/469600 into a body-only leaf.
        verify_followup(extract_canonical_exe(options.exe, FOLLOWUP, 1))
        print("EXT16_008_EXACT_SHA_PE32_WRAPPER_TWO_CALL_EDGES_PASS",
              hex(CALLER), hex(FIRST), hex(FOLLOWUP))
    if not options.self_test and options.exe is None:
        parser.error("specify --self-test and/or --exe canonical_file")


if __name__ == "__main__":
    main()
