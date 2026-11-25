"""Bounded PE image envelope checks for the Ferrari16 test package.

This is not a Windows loader, signature check, or proof of runtime behavior.
"""
import struct


def assert_pe_image(data, machine, is_dll, label):
    def reject(reason):
        raise ValueError(f"{label}: {reason}")

    if len(data) < 64 or data[:2] != b"MZ":
        reject("not a PE file")
    offset = struct.unpack_from("<I", data, 0x3c)[0]
    if (offset < 64 or offset > len(data) - 24 or
            data[offset:offset + 4] != b"PE\x00\x00"):
        reject("invalid PE/COFF header")
    actual, sections, _, _, _, opt_size, flags = struct.unpack_from(
        "<HHIIIHH", data, offset + 4)
    if actual != machine:
        reject("wrong machine")
    if not flags & 0x0002 or bool(flags & 0x2000) != is_dll:
        reject("wrong executable/DLL role")
    if not 1 <= sections <= 96:
        reject("invalid section count")
    opt = offset + 24
    fixed_size, magic = (96, 0x10b) if machine == 0x14c else (112, 0x20b)
    if opt_size < fixed_size or opt + opt_size > len(data):
        reject("truncated optional header")
    if struct.unpack_from("<H", data, opt)[0] != magic:
        reject("wrong optional header magic")
    directories = struct.unpack_from("<I", data, opt + fixed_size - 4)[0]
    if directories > (opt_size - fixed_size) // 8:
        reject("truncated data directories")
    entry = struct.unpack_from("<I", data, opt + 16)[0]
    image_size, headers_size = struct.unpack_from("<II", data, opt + 56)
    table = opt + opt_size
    if not table + sections * 40 <= headers_size <= len(data):
        reject("truncated section table or invalid SizeOfHeaders")
    if image_size < headers_size:
        reject("invalid SizeOfImage")
    executable_bytes = False
    entry_backed = False
    raw_ranges = []
    virtual_ranges = []
    for i in range(sections):
        section = table + i * 40
        virtual_size, rva, raw_size, raw = struct.unpack_from(
            "<IIII", data, section + 8)
        characteristics = struct.unpack_from("<I", data, section + 36)[0]
        if raw_size and (raw < headers_size or raw + raw_size > len(data)):
            reject("section raw data outside image file")
        if max(virtual_size, raw_size) and (
                rva < headers_size or rva + max(virtual_size, raw_size) > image_size):
            reject("section outside virtual image")
        # Individually bounded sections can still alias each other. A PE
        # image must not map competing section contents to the same RVA
        # or describe the same file bytes as separate section payloads.
        if raw_size:
            raw_ranges.append((raw, raw + raw_size))
        if max(virtual_size, raw_size):
            virtual_ranges.append((rva, rva + max(virtual_size, raw_size)))
        if raw_size and characteristics & 0x20000000:
            executable_bytes = True
            if rva <= entry < rva + raw_size:
                entry_backed = True
    for ranges, kind in ((raw_ranges, "raw"), (virtual_ranges, "virtual")):
        ranges.sort()
        if any(left[1] > right[0] for left, right in zip(ranges, ranges[1:])):
            reject(f"overlapping {kind} sections")
    if not executable_bytes:
        reject("no file-backed executable section")
    if (entry == 0 and not is_dll) or (entry != 0 and not entry_backed):
        reject("invalid executable entry point")
