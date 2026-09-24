#!/usr/bin/env python3
"""Read-only shared game-data analyzer for OutRun 2006 C2C.

Emits metadata/hashes/offsets only. It does not copy game payloads into output.
Supported: zlib .sz, XST, Sprani, Scripts/bin, COLI0200, Text/*.bin txet,
and canonical OR2006C2C.EXE localization anchors.
"""
from __future__ import annotations
import argparse, collections, gzip, hashlib, json, re, struct, zlib
from pathlib import Path

CANONICAL_EXE_SHA256 = "68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3"
MAX_INFLATED = 256 * 1024 * 1024
LANG_SUFFIXES = "EFGIS"

STAGE_FOLDERS = [
    ("PALM", "Palm Beach"), ("LAKE", "Deep Lake"), ("INDU", "Industrial Complex"),
    ("ALPI", "Alpine"), ("SNOW", "Snowy Mountain"), ("CLOU", "Cloudy Highland"),
    ("CAST", "Castle Wall"), ("GHOS", "Ghost Forest"), ("FORE", "Coniferous Forest"),
    ("DESE", "Desert"), ("TULI", "Tulip Garden"), ("METR", "Metropolis"),
    ("RUIN", "Ancient Ruins"), ("CAPE", "Cape Way"), ("IMPE", "Imperial Avenue"),
    ("BEAC", "Sunny Beach"), ("SEQU", "Big Forest"), ("NIAG", "Waterfalls"),
    ("LASV", "Casino Town"), ("ALAS", "Ice Scape"), ("GRAN", "Canyon"),
    ("SANF", "Bay Area"), ("AMAZ", "Jungle"), ("MACH", "Lost City"),
    ("YOSE", "National Park"), ("MAYA", "Legend"), ("NEWY", "Skyscrapers"),
    ("PRIN", "Floral Village"), ("FLOR", "Milky Way"), ("EAST", "Giant Statues"),
]
STAGE_FOLDER_ID = {name: i for i, (name, _) in enumerate(STAGE_FOLDERS)}
STAGE_FOLDER_ID.update({name + "_R": i + 30 for i, (name, _) in enumerate(STAGE_FOLDERS)})
STAGE_FOLDER_ID.update({
    "PALM_T": 60, "BEAC_T": 61, "PALM_BT": 62,
    "BEAC_BT": 63, "PALM_BR": 64, "BEAC_BR": 65,
})
STAGE_DISPLAY = {name: display for name, display in STAGE_FOLDERS}
STAGE_DISPLAY.update({name + "_R": "(R) " + display for name, display in STAGE_FOLDERS})
STAGE_DISPLAY.update({
    "PALM_T": "(T) Palm Beach", "BEAC_T": "(T) Sunny Beach",
    "PALM_BT": "(Night) Palm Beach", "BEAC_BT": "(Night) Sunny Beach",
    "PALM_BR": "(R-Night) Palm Beach", "BEAC_BR": "(R-Night) Sunny Beach",
})

def stage_identity_from_path(relative_path: str) -> dict | None:
    parts = Path(relative_path).parts
    try:
        idx = next(i for i, part in enumerate(parts) if part.lower() == "stage")
    except StopIteration:
        return None
    if idx + 1 >= len(parts):
        return None
    folder = parts[idx + 1].upper()
    if folder not in STAGE_FOLDER_ID:
        return {"folder": folder, "stageId": None, "displayName": None}
    return {
        "folder": folder,
        "stageId": STAGE_FOLDER_ID[folder],
        "displayName": STAGE_DISPLAY[folder],
    }

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def u32(data: bytes, off: int) -> int:
    if off < 0 or off + 4 > len(data):
        raise ValueError(f"u32 OOB @{off:#x}")
    return struct.unpack_from("<I", data, off)[0]

def inflate_sz(raw: bytes) -> bytes:
    obj = zlib.decompressobj()
    out = obj.decompress(raw, MAX_INFLATED + 1) + obj.flush()
    if len(out) > MAX_INFLATED:
        raise ValueError("inflated SZ exceeds safety limit")
    if obj.unused_data:
        raise ValueError("SZ has trailing/concatenated data")
    return out

def read_payload(path: Path) -> tuple[bytes, str]:
    raw = path.read_bytes()
    if path.suffix.lower() == ".sz":
        return inflate_sz(raw), "zlib-sz"
    if raw[:2] == b"\x1f\x8b":
        return gzip.decompress(raw), "gzip"
    return raw, "raw"

def parse_xst(data: bytes) -> dict:
    base = 0
    sysmem = vidmem = None
    if len(data) >= 8:
        s, v = struct.unpack_from("<II", data, 0)
        if s + v + 8 == len(data):
            base, sysmem, vidmem = 8, s, v
    if base + 32 > len(data):
        raise ValueError("XST header too small")
    head = struct.unpack_from("<8I", data, base)
    flag, tex_ofs, nb_tex, dummy, nb_dsptbl, dsptbl, nb_scrtbl, scrtbl = head
    if max(nb_tex, nb_dsptbl, nb_scrtbl) > 1_000_000:
        raise ValueError("unreasonable XST count")
    displays = []
    if base + dsptbl + nb_dsptbl * 8 <= len(data):
        for i in range(nb_dsptbl):
            displays.append(list(struct.unpack_from("<II", data, base + dsptbl + i * 8)))
    sprites = []
    if base + scrtbl + nb_scrtbl * 28 <= len(data):
        for i in range(nb_scrtbl):
            sprites.append(list(struct.unpack_from("<IffffHHHH", data, base + scrtbl + i * 28)))
    structural = json.dumps(
        {"header": list(head), "display": displays, "sprites": sprites},
        separators=(",", ":"), sort_keys=True).encode()
    prefix_len = (8 + sysmem) if sysmem is not None else min(len(data), max(base + 32, base + tex_ofs))
    return {
        "format": "XST", "size": len(data), "memHeader": sysmem is not None,
        "sysmem": sysmem, "vidmem": vidmem, "textureCount": nb_tex,
        "displayTableCount": nb_dsptbl, "spriteCount": nb_scrtbl,
        "structureSha256": sha256(structural),
        "systemPrefixSha256": sha256(data[:prefix_len]),
        "videoPayloadSha256": sha256(data[prefix_len:]) if prefix_len < len(data) else None,
    }

def parse_sprani(data: bytes) -> dict:
    if len(data) < 12:
        raise ValueError("Sprani too small")
    payload_size, first = struct.unpack_from("<II", data, 0)
    if payload_size + 4 != len(data):
        raise ValueError("Sprani payload-size mismatch")
    if first < 8 or first % 4:
        raise ValueError("Sprani first-record offset invalid")
    count = first // 4 - 1
    offsets = [u32(data, 4 + 4 * i) for i in range(count)]
    monotonic = all(a <= b for a, b in zip(offsets, offsets[1:]))
    valid = all(first <= x < len(data) for x in offsets)
    sizes = []
    if monotonic and valid:
        sizes = [b - a for a, b in zip(offsets, offsets[1:] + [len(data)])]
    return {
        "format": "SPRANI", "size": len(data), "payloadSizeField": payload_size,
        "recordCount": count, "firstRecordOffset": first,
        "offsetsMonotonic": monotonic, "offsetsInBounds": valid,
        "recordSizeMin": min(sizes) if sizes else None,
        "recordSizeMax": max(sizes) if sizes else None,
        "offsetTableSha256": sha256(data[4:first]),
    }

def parse_script_bin(data: bytes) -> dict:
    if len(data) < 8:
        raise ValueError("script bin too small")
    desc_count, fix_count = struct.unpack_from("<II", data, 0)
    if desc_count > 10000 or fix_count > 100000:
        raise ValueError("script counts unreasonable")
    fix_start = 8
    desc_start = fix_start + fix_count * 8
    if desc_start + desc_count * 12 > len(data):
        raise ValueError("script tables OOB")
    fixups = []
    for i in range(fix_count):
        field, target = struct.unpack_from("<II", data, fix_start + i * 8)
        fixups.append({
            "fieldOffset": field, "targetOffset": target,
            "fieldInBounds": field + 4 <= len(data), "targetInBounds": target < len(data)})
    descs = []
    for i in range(desc_count):
        type_id, count, off = struct.unpack_from("<III", data, desc_start + i * 12)
        descs.append({"typeId": f"0x{type_id:08X}", "count": count, "offset": off})
    distinct = sorted(set(d["offset"] for d in descs if d["offset"] < len(data)))
    for d in descs:
        off = d["offset"]
        if off >= len(data):
            d["dataInBounds"] = False
            continue
        d["dataInBounds"] = True
        next_off = next((x for x in distinct if x > off), len(data))
        span = max(0, next_off - off)
        d["spanToNextRegion"] = span
        d["inferredStride"] = span // d["count"] if d["count"] and span % d["count"] == 0 else None
    return {
        "format": "SCRIPT_BIN", "size": len(data),
        "descriptorCount": desc_count, "fixupCount": fix_count,
        "fixups": fixups, "descriptors": descs,
        "allFixupsInBounds": all(x["fieldInBounds"] and x["targetInBounds"] for x in fixups),
    }

def parse_coli(data: bytes) -> dict:
    if len(data) < 64 or data[4:12] != b"COLI0200":
        raise ValueError("not COLI0200")
    words = list(struct.unpack_from("<16I", data, 0))
    return {
        "format": "COLI0200", "size": len(data), "payloadSizeField": words[0],
        "payloadSizeMatches": words[0] + 4 == len(data),
        "headerU32": [f"0x{x:08X}" for x in words], "sha256": sha256(data),
    }

def parse_txet(data: bytes) -> dict:
    """Lossless txet structure parser shared with Korean-localization research."""
    if len(data) < 12 or data[:4] != b"txet":
        raise ValueError("not txet")
    declared = u32(data, 4)
    if declared != len(data):
        raise ValueError(f"txet size mismatch header={declared} actual={len(data)}")
    first = u32(data, 8)
    if first < 8 or (first - 8) % 4:
        raise ValueError(f"invalid first txet payload offset {first:#x}")
    count = (first - 8) // 4
    if 8 + count * 4 > len(data):
        raise ValueError("txet offset table OOB")
    offsets = list(struct.unpack_from(f"<{count}I", data, 8))
    nonzero = [x for x in offsets if x]
    if nonzero != sorted(nonzero) or len(nonzero) != len(set(nonzero)):
        raise ValueError("txet non-zero offsets not strictly increasing")

    entries, chars = [], collections.Counter()
    simple = multi = nulls = 0
    for i, off in enumerate(offsets):
        if off == 0:
            nulls += 1
            entries.append({"index": i, "nullPointer": True})
            continue
        next_off = len(data)
        for candidate in offsets[i + 1:]:
            if candidate:
                next_off = candidate
                break
        if not (first <= off <= next_off <= len(data)):
            raise ValueError(f"txet record bounds invalid index={i}")
        raw = data[off:next_off]
        segments, simple_text = [], None
        try:
            decoded = raw.decode("utf-16le")
            segments = decoded.split("\x00")
            if segments and segments[-1] == "":
                segments = segments[:-1]
            if len(segments) == 1 and raw.endswith(b"\x00\x00"):
                simple_text = segments[0]
                simple += 1
            elif segments:
                multi += 1
            for segment in segments:
                chars.update(segment)
        except UnicodeDecodeError:
            multi += 1
        entries.append({
            "index": i, "nullPointer": False, "offset": off, "size": len(raw),
            "segmentCount": len(segments), "simpleText": simple_text})

    return {
        "format": "TXET", "size": len(data), "sha256": sha256(data),
        "entryCount": count, "simpleRecordCount": simple,
        "multiOrSpecialRecordCount": multi, "nullPointerCount": nulls,
        "firstPayloadOffset": first, "uniqueCharacters": len(chars),
        "nonAsciiCharacterCount": sum(ord(ch) > 0x7F for ch in chars),
        "uniqueHangulSyllables": sum(0xAC00 <= ord(ch) <= 0xD7A3 for ch in chars),
        "entries": entries,
    }


def analyze_exe(path: Path) -> dict:
    data = path.read_bytes()
    digest = sha256(data)
    out = {"path": path.name, "size": len(data), "sha256": digest,
           "canonical": digest == CANONICAL_EXE_SHA256}
    if not out["canonical"]:
        out["note"] = "Non-canonical EXE: fixed RVA semantic anchors omitted."
        return out
    out["anchors"] = {
        "textLoaderRva": "0x00065DF0", "stringGetterRva": "0x00065EB0",
        "textPathTableVa": "0x0064B91C", "fontGlyphDrawRva": "0x0002B720",
        "setPrintFontRva": "0x0002BA60", "putSpriteExRva": "0x0002CFE0",
        "lensFlareLoaderRva": "0x0004A630", "lensFlareSelectorRva": "0x0004A690",
        "drawObjectAlphaRva": "0x000056D0",
    }
    out["localizationFacts"] = {
        "textPointerTableOffset": 8, "textPointersAreRelative": True,
        "stockLoaderInputEncoding": "UTF-16LE",
        "stockLoaderRuntimeConversion": "low byte of each UTF-16 code unit",
        "stockGlyphAcceptedByteRange": "0x00..0x7F excluding control/space cases",
        "fontDescriptorSearchCount": 10,
        "glyphAtlasAddressing": "16x16 cells from low/high nibble of one-byte glyph index",
        "stockUnicodeHangulSupported": False,
    }
    out["textPaths"] = [
        "\\text\\english_us.bin", "\\text\\french.bin", "\\text\\german.bin",
        "\\text\\italian.bin", "\\text\\spanish.bin", "\\text\\english.bin"]
    return out

def parse_manifest(path: Path) -> dict:
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "|" not in line:
            continue
        name, size = line.rsplit("|", 1)
        try:
            n = int(size)
        except ValueError:
            continue
        rows.append({"path": name.removeprefix("./"), "size": n})
    return {
        "fileCount": len(rows),
        "textFiles": [r for r in rows if r["path"].lower().startswith("text/")],
        "stageCollisionFiles": [
            r for r in rows
            if r["path"].lower().startswith("stage/") and "/coli_" in r["path"].lower()],
    }

def scan(root: Path, exe: Path | None = None, manifest: Path | None = None) -> dict:
    report = {
        "schema": "outrun-shared-reverse-kb-v1",
        "policy": {"payloadsCommitted": False, "evidence": "metadata/hashes/offsets/counts only"},
        "sz": {}, "xst": {}, "sprani": {}, "scripts": {}, "collision": {},
        "localization": {}, "manifest": None, "exe": None,
    }
    sz_ok, sz_fail, total_c, total_d = 0, [], 0, 0
    xst, sprani, scripts, collision, textbins = {}, {}, {}, {}, {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rp = p.relative_to(root).as_posix()
        try:
            data, _ = read_payload(p)
            if p.suffix.lower() == ".sz":
                sz_ok += 1
                total_c += p.stat().st_size
                total_d += len(data)
            low = p.name.lower()
            if low.endswith("xst.sz") or p.suffix.lower() == ".xst":
                xst[rp] = parse_xst(data)
            elif low.startswith("ani_") and low.endswith(".sz"):
                try:
                    sprani[rp] = parse_sprani(data)
                except ValueError:
                    pass
            if "/scripts/bin/" in ("/" + rp.lower()):
                scripts[rp] = parse_script_bin(data)
            if low.startswith("coli_") and low.endswith("_bin.sz") and len(data) >= 12 and data[4:12] == b"COLI0200":
                coli_meta = parse_coli(data)
                coli_meta["compressedSize"] = p.stat().st_size
                coli_meta["stage"] = stage_identity_from_path(rp)
                coli_meta["collisionClass"] = (
                    "course-surface" if low.startswith("coli_cs_")
                    else "background" if low.startswith("coli_bk_")
                    else "other"
                )
                collision[rp] = coli_meta
            if p.parent.name.lower() == "text" and p.suffix.lower() == ".bin":
                try:
                    textbins[rp] = parse_txet(data)
                except ValueError as e:
                    textbins[rp] = {"status": "PARSE_REJECTED", "reason": str(e), "size": len(data)}
        except Exception as e:
            if p.suffix.lower() == ".sz":
                sz_fail.append({"path": rp, "error": str(e)})

    report["sz"] = {
        "filesAttempted": sz_ok + len(sz_fail), "success": sz_ok, "failures": sz_fail,
        "compressedBytes": total_c, "inflatedBytes": total_d,
        "ratio": total_d / total_c if total_c else None}
    report["xst"]["files"] = xst
    report["sprani"]["files"] = sprani
    report["scripts"]["files"] = scripts
    report["collision"]["files"] = collision
    report["localization"]["textFiles"] = textbins

    groups = collections.defaultdict(dict)
    rx = re.compile(r"^(.*)_([EFGIS])xst\.sz$", re.I)
    for rp, meta in xst.items():
        m = rx.match(Path(rp).name)
        if m:
            groups[m.group(1).lower()][m.group(2).upper()] = (rp, meta)
    families = []
    for base, members in sorted(groups.items()):
        if set(members) == set(LANG_SUFFIXES):
            families.append({
                "base": base, "languages": sorted(members),
                "sameStructure": len({x[1]["structureSha256"] for x in members.values()}) == 1,
                "sameSystemPrefix": len({x[1]["systemPrefixSha256"] for x in members.values()}) == 1,
                "textureCount": next(iter(members.values()))[1]["textureCount"],
                "spriteCount": next(iter(members.values()))[1]["spriteCount"],
                "files": {k: v[0] for k, v in sorted(members.items())}})
    report["localization"]["languageXstFamilies"] = families
    report["localization"]["fontAssets"] = {
        rp: meta for rp, meta in xst.items() if "font" in Path(rp).name.lower()}

    stride_counts, type_counts = collections.Counter(), collections.Counter()
    for meta in scripts.values():
        for d in meta["descriptors"]:
            type_counts[d["typeId"]] += 1
            if d.get("inferredStride") is not None:
                stride_counts[d["inferredStride"]] += 1
    report["scripts"]["summary"] = {
        "fileCount": len(scripts), "descriptorTypeIdCount": len(type_counts),
        "mostCommonInferredStrides": [
            {"stride": k, "descriptorOccurrences": v} for k, v in stride_counts.most_common(30)],
        "mostCommonDescriptorTypeIds": [
            {"typeId": k, "occurrences": v} for k, v in type_counts.most_common(30)]}

    hashes = collections.defaultdict(list)
    for rp, meta in collision.items():
        hashes[meta["sha256"]].append(rp)
    stage_coli = [
        {"path": rp, **meta["stage"], "collisionClass": meta["collisionClass"],
         "compressedSize": meta["compressedSize"], "inflatedSize": meta["size"],
         "sha256": meta["sha256"]}
        for rp, meta in collision.items() if meta.get("stage")
    ]
    report["collision"]["summary"] = {
        "fileCount": len(collision), "uniquePayloads": len(hashes),
        "stageCollisionCount": len(stage_coli),
        "stageCollisionInventory": sorted(
            stage_coli,
            key=lambda x: (999 if x["stageId"] is None else x["stageId"], x["path"])),
        "duplicateGroups": [
            {"sha256": h, "paths": paths} for h, paths in hashes.items() if len(paths) > 1]}

    if manifest:
        report["manifest"] = parse_manifest(manifest)
    if exe:
        report["exe"] = analyze_exe(exe)
    return report

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, type=Path)
    ap.add_argument("--exe", type=Path)
    ap.add_argument("--manifest", type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args(argv)
    report = scan(args.root, args.exe, args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"wrote {args.output}: SZ {report['sz']['success']}/{report['sz']['filesAttempted']}; "
        f"XST={len(report['xst']['files'])}; Sprani={len(report['sprani']['files'])}; "
        f"Scripts={len(report['scripts']['files'])}; COLI={len(report['collision']['files'])}")
    return 0 if not report["sz"]["failures"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
