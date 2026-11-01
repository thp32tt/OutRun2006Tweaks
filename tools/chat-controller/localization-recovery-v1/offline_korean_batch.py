#!/usr/bin/env python3
"""Bounded all-source OutRun Korean fallback. TEST_ONLY, no OCR/API or DDS overwrite.

Each cycle operates on SHA-verified original HD PNG + existing approved Korean ROI
metadata. It emits isolated DDS candidates; original DDS may be absent or DXT.
In that case emits a valid UNCOMPRESSED DDS, explicitly not a source-format clone.
"""
from __future__ import annotations
import argparse, collections, datetime as dt, hashlib, importlib.util, json, os, re, struct, tempfile, time
from pathlib import Path, PurePosixPath
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
SP = importlib.util.spec_from_file_location("offline_sprite", HERE / "offline_korean_sprite_fallback.py")
sprite = importlib.util.module_from_spec(SP)
SP.loader.exec_module(sprite)
HOST = Path("/home/chatgpt-runner2/work")
IMAGE_ROOT = Path("/data/imagegen") if Path("/data/imagegen/text_roi_batches/production_manifest.json").is_file() else HOST / "image-src"
SOURCE_ROOT = HOST / "c_salvage_text_roi/c_original_hd_crop_only/hd_original_108_verified"
DDS_ROOT = HOST / "c_salvage_text_roi/source_full_20261012"
DEFAULT_OUTPUT = IMAGE_ROOT / "text_roi_batches/offline_bulk_test_only"
REGION_STATUS = {"ROI_APPROVED_FOR_IMAGEGEN", "ROI_REBALANCED_TO_B"}
SAFE_SOURCE = re.compile(r"^Q\d{3}_[A-Z0-9_]+\.png$")
ORIENT = {"_FLIPY": "FLIPY", "_NORMAL": "NORMAL"}
LAST_RUN_SCHEMA = "outrun.offline-korean-all-sources.test-only.v1"

def checksum(path):
    return sprite.sha(path)

def atomic_json(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as f:
        json.dump(row, f, indent=2, ensure_ascii=False)
        f.write("\n")
        tmp = Path(f.name)
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)

def verify_path(value):
    p = PurePosixPath(str(value))
    if p.is_absolute() or not str(p).startswith("textures/load/") or ".." in p.parts or not str(p).endswith(".dds"):
        raise ValueError("UNSAFE_TEXTURE_TARGET")
    return p

def source_orientation(name):
    found = [direction for mark, direction in ORIENT.items() if mark in name]
    if len(found) != 1:
        raise ValueError("SOURCE_ORIENTATION_UNKNOWN")
    return found[0]

def source_variation(name):
    for v in ("Keyboard", "PlayStation", "Switch", "Xbox"):
        if "_" + v.upper() + "_READABLE" in name:
            return v
    return None

def variant_path(row, name):
    path = verify_path(row["source_dds_path"])
    variant = source_variation(name)
    parts = path.parts
    consoles = {"Keyboard", "PlayStation", "Switch", "Xbox"}
    found = next((x for x in parts if x in consoles), None)
    if variant != found:
        return False
    return True

def read_sources(manifest, source_root, hash_cache=None):
    cache = hash_cache if hash_cache is not None else {}
    by_hash = collections.defaultdict(list)
    for row in manifest["items"]:
        if not isinstance(row, dict) or row.get("status") not in REGION_STATUS:
            continue
        if not all(row.get(k) for k in ("english","korean","source_png_sha256","source_dds_path","source_dds_sha256")):
            continue
        if len(row["source_png_sha256"]) != 64 or len(row["source_dds_sha256"]) != 64:
            continue
        by_hash[row["source_png_sha256"]].append(row)
    # File names are pinned against their actual bytes, not from a guessed Q index.
    results = []
    for src in sorted(source_root.glob("*.png")):
        if src.is_symlink() or not SAFE_SOURCE.fullmatch(src.name):
            continue
        stat = src.stat()
        sig = [stat.st_size, stat.st_mtime_ns]
        memo = cache.get(src.name)
        if isinstance(memo, dict) and memo.get("stat") == sig and isinstance(memo.get("sha"), str):
            actual_sha = memo["sha"]
        else:
            actual_sha = checksum(src)
            cache[src.name] = {"stat":sig,"sha":actual_sha}
        matching = by_hash.get(actual_sha, [])
        matching = [r for r in matching if variant_path(r, src.name)]
        results.append({"source": src, "sha": actual_sha, "rows": matching})
    return results

def canonical_dds(source_name, wanted_sha, root):
    # Rare canonical DDS files in N100 are named by original full SHA prefix.
    # They MUST be byte checked. Never silently use a similarly named DDS.
    candidates = [p for p in root.glob(source_name[:4] + "_*.dds")
                  if wanted_sha[:12].lower() in p.name.lower()]
    matched = [p for p in candidates if not p.is_symlink() and checksum(p) == wanted_sha]
    if len(matched) > 1:
        raise ValueError("AMBIGUOUS_CANONICAL_DDS")
    return matched[0] if matched else None

def inspect_dds(source_path, source_png, flip):
    with Image.open(source_path) as im:
        if im.format != "DDS":
            raise ValueError("DDS_IMAGE_FORMAT_INVALID")
        dds = im.convert("RGBA")
    if dds.size != source_png.size:
        raise ValueError("DDS_DIMENSIONS_MISMATCH")
    reference = source_png if flip == "NORMAL" else source_png.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    if not np.array_equal(np.asarray(dds), np.asarray(reference)):
        # DXT5 decode can be nonexact by a few colors; full pixel equality
        # does not hold for every DDS source decoder. Fail closed: no guessing.
        raise ValueError("CANONICAL_DDS_DECODE_NOT_EXACT_SOURCE_PNG")
    return True

def render(source, rows, *, max_opaque_fraction=1.0):
    before = np.asarray(source)
    w,h = source.size
    # Keep bounded non-overlapping regions; huge/overlapping atlas groups are HOLD.
    boxes = {}
    rejected = []
    for item in rows:
        b = item.get("bbox_xyxy")
        if not isinstance(b, list) or len(b) != 4 or any(type(x) != int for x in b):
            rejected.append({"id":item.get("id"),"reason":"BAD_BBOX"});continue
        x0,y0,x1,y1 = b
        if not (0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h):
            rejected.append({"id":item.get("id"),"reason":"OUT_OF_BOUNDS"});continue
        key=tuple(b)
        if key in boxes:
            if boxes[key]["korean"] != item["korean"]:
                raise ValueError("CONFLICTING_TRANSLATIONS_SAME_ROI")
            continue
        boxes[key]=item
    ordered = sorted(boxes.values(),
                     key=lambda x:((x["bbox_xyxy"][2]-x["bbox_xyxy"][0])*
                                   (x["bbox_xyxy"][3]-x["bbox_xyxy"][1]),x["bbox_xyxy"][1]))
    out=source.copy()
    painted=[]
    region_boxes=[]
    font=sprite.font_path()
    for item in ordered:
        b=item["bbox_xyxy"]
        x0,y0,x1,y1=b
        if any(x0<a[2] and a[0]<x1 and y0<a[3] and a[1]<y1 for a in region_boxes):
            rejected.append({"id":item.get("id"),"reason":"OVERLAPPING_ROI"})
            continue
        piece=before[y0:y1,x0:x1]
        alpha=float(np.count_nonzero(piece[:,:,3]>=16))/piece[:,:,3].size
        if alpha>max_opaque_fraction:
            rejected.append({"id":item.get("id"),"reason":"OPAQUE_REGION"})
            continue
        try:
            glyph=sprite.make_glyph(item["korean"],x1-x0,y1-y0,font,piece)
        except (ValueError, OSError, OverflowError):
            rejected.append({"id":item.get("id"),"reason":"GLYPH_CANNOT_FIT"})
            continue
        region_boxes.append(b)
        out.paste((0,0,0,0),(x0,y0,x1,y1))
        out.alpha_composite(glyph,(x0,y0))
        painted.append({"id":item.get("id"),"english":item["english"],
                        "korean":item["korean"],"bbox":b,"opaque":round(alpha,5)})
    if not painted:
        raise ValueError("NO_DRAWABLE_NONOVERLAPPING_ROI")
    after=np.asarray(out)
    mask=np.zeros((h,w),dtype=bool)
    for x0,y0,x1,y1 in region_boxes:mask[y0:y1,x0:x1]=True
    changed=np.any(before!=after,axis=2)
    outside=int(np.count_nonzero(changed&~mask))
    if outside:
        raise AssertionError("OUTSIDE_APPROVED_ROI_CHANGED")
    return out,painted,rejected,int(np.count_nonzero(changed)),outside

def encode_rgba_dds(readable, orientation, mip_count):
    # Standard D3D9 DDS: 128 byte header, RGBA32 (R mask 0x000000ff),
    # full-size 32-bit pixels. Supports 1 or a complete mip chain. This is
    # intentionally NOT a claim to have recompressed original DXT5 bytes.
    raw=readable if orientation=="NORMAL" else readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    w,h=raw.size
    nmax=max(w,h).bit_length()
    mips=max(1,min(mip_count,nmax))
    data=bytearray(128)
    data[:4]=b"DDS "
    struct.pack_into("<I",data,4,124)
    flags=0x1|0x2|0x4|0x8|0x1000
    if mips>1:flags|=0x20000
    struct.pack_into("<I",data,8,flags)
    struct.pack_into("<I",data,12,h)
    struct.pack_into("<I",data,16,w)
    struct.pack_into("<I",data,20,w*4)
    struct.pack_into("<I",data,28,mips)
    struct.pack_into("<I",data,76,32)
    struct.pack_into("<I",data,80,0x41)
    struct.pack_into("<I",data,88,32)
    struct.pack_into("<IIII",data,92,255,65280,16711680,4278190080)
    struct.pack_into("<I",data,108,0x1000|(0x8|0x400000 if mips>1 else 0))
    out=bytearray(data)
    current=raw
    for i in range(mips):
        out.extend(current.tobytes())
        if i<mips-1:
            current=current.resize((max(1,current.width//2),max(1,current.height//2)),Image.Resampling.BOX)
    return bytes(out)

def run_source(entry, output_root, dds_root, *, max_opaque_fraction, execute, mips):
    source_path=entry["source"]
    rows=entry["rows"]
    if not rows:
        return {"source":source_path.name,"status":"NO_APPROVED_ROI","ready_count":0}
    dds_paths=sorted(set(r["source_dds_path"] for r in rows))
    dds_shas=sorted(set(r["source_dds_sha256"] for r in rows))
    if len(dds_paths)!=1 or len(dds_shas)!=1:
        raise ValueError("CONFLICTING_CANONICAL_DDS_FOR_VARIANT")
    target=verify_path(dds_paths[0])
    expected_dds_sha=dds_shas[0]
    orientation=source_orientation(source_path.name)
    candidate_dir=output_root/"sources"/(source_path.stem+"_"+entry["sha"][:12])
    report_path=candidate_dir/"report.json"
    if report_path.is_file():
        previous=json.loads(report_path.read_text(encoding="utf-8"))
        d=candidate_dir/"KOREAN_TEST_ONLY.dds"
        if previous.get("source_sha256")!=entry["sha"] or previous.get("target_path")!=str(target):
            raise ValueError("EXISTING_REPORT_MISMATCH")
        if not d.is_file():raise ValueError("EXISTING_OUTPUT_MISSING")
        st=d.stat()
        if (st.st_size != previous.get("output_dds_bytes") or
            st.st_mtime_ns != previous.get("output_dds_mtime_ns")):
            if checksum(d)!=previous.get("output_dds_sha256"):
                raise ValueError("EXISTING_OUTPUT_SHA_MISMATCH")
        return {"source":source_path.name,"status":"ALREADY_VERIFIED",
                "ready_count":previous.get("painted_count",0)}
    with Image.open(source_path) as im:
        if im.format!="PNG" or im.mode!="RGBA":
            raise ValueError("SOURCE_NOT_RGBA_PNG")
        original=im.copy()
    if checksum(source_path)!=entry["sha"]:
        raise ValueError("SOURCE_CHANGED_DURING_READ")
    dds=canonical_dds(source_path.name, expected_dds_sha, dds_root)
    # A known DXT original can differ numerically from decoded source-PNG
    # due to its decompress provenance. Record that distinction in receipt.
    if dds:
        with Image.open(dds) as im:
            if im.size!=original.size:
                raise ValueError("DDS_SOURCE_DIMENSIONS_MISMATCH")
            native=original if orientation=="NORMAL" else original.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            exact=np.array_equal(np.asarray(im.convert("RGBA")),np.asarray(native))
        canonical_status="MATCHED_CANONICAL_DDS_EXACT_PIXELS" if exact else "MATCHED_DDS_SHA_NONEXACT_PNG_PIXELS"
    else:
        exact=False
        canonical_status="MISSING_CANONICAL_DDS_RECONSTRUCT_FROM_VERIFIED_PNG"
    # Reported names may point at other variants; never clobber live texture.
    output,painted,held,pixels,wrong=render(original,rows,max_opaque_fraction=max_opaque_fraction)
    dds_bytes=encode_rgba_dds(output,orientation,mips)
    if not execute:
        return {"source":source_path.name,"status":"DRY_RUN","ready_count":len(painted),
                "held_count":len(held),"dds_source":canonical_status,"target_path":str(target)}
    candidate_dir.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".offline-test-",dir=candidate_dir.parent) as temp:
        root=Path(temp)
        d=root/"KOREAN_TEST_ONLY.dds"
        p=root/"KOREAN_READABLE_TEST_ONLY.png"
        d.write_bytes(dds_bytes)
        output.save(p)
        with Image.open(d) as check:
            expect=output if orientation=="NORMAL" else output.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            if check.size!=expect.size or not np.array_equal(np.asarray(check.convert("RGBA")),np.asarray(expect)):
                raise ValueError("OUTPUT_DDS_ROUNDTRIP_FAILED")
        report={
            "schema":LAST_RUN_SCHEMA,"status":"TEST_ONLY_NOT_RUNTIME_APPROVED",
            "source":source_path.name,"source_sha256":entry["sha"],
            "canonical_dds_expected_sha256":expected_dds_sha,"canonical_dds_available":dds is not None,
            "canonical_dds_verification":canonical_status,
            "target_path":str(target),"source_orientation":orientation,
            "output_encoding":"DDS_RGBA32_UNCOMPRESSED","mip_levels":mips,
            "painted_count":len(painted),"held_count":len(held),"painted":painted,"held":held,
            "pixels_changed":pixels,"outside_roi_changed_pixels":wrong,
            "output_dds_sha256":checksum(d),"output_png_sha256":checksum(p),
            "output_dds_bytes":d.stat().st_size,"output_dds_mtime_ns":d.stat().st_mtime_ns,
            "dds_roundtrip_exact":True,"original_source_modified":False,
            "A_B_C1_unchanged":True,"requires_C1_C3_and_ingame_qa":True,
            "RUNTIME_VALIDATION":"UNTESTED"}
        (root/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        os.replace(root,candidate_dir)
    return {"source":source_path.name,"status":"TEST_ONLY_SAVED","ready_count":len(painted),
            "held_count":len(held),"target_path":str(target),"canonical":canonical_status}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--execute",action="store_true",help="Generate TEST_ONLY candidates; default is dry-run")
    p.add_argument("--max-sources",type=int,default=1)
    p.add_argument("--only-source",default="",help="Only the literal basename Q...png for an isolated test")
    p.add_argument("--retry-holds",action="store_true",help="Retry failed sources after changing the code or source")
    p.add_argument("--inventory-only",action="store_true",help="Summarize readiness without rendering or modifying any file")
    p.add_argument("--mips",type=int,default=1)
    p.add_argument("--max-opaque-fraction",type=float,default=1.0)
    p.add_argument("--manifest",default=str(IMAGE_ROOT/"text_roi_batches/production_manifest.json"))
    p.add_argument("--source-root",default=str(SOURCE_ROOT))
    p.add_argument("--dds-root",default=str(DDS_ROOT))
    p.add_argument("--output-root",default=str(DEFAULT_OUTPUT))
    args=p.parse_args()
    if args.max_sources<1 or args.max_sources>108 or args.mips<1 or args.mips>16:
        p.error("max-sources 1..108; mips 1..16")
    if not 0<=args.max_opaque_fraction<=1:p.error("invalid opacity fraction")
    output_root=Path(args.output_root)
    manifest=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    if not isinstance(manifest.get("items"),list):raise ValueError("INVALID_PRODUCTION_MANIFEST")
    cache_path=output_root/"source_digest_cache.json"
    try:
        cache=json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.is_file() else {}
    except (ValueError,OSError):
        cache={}
    if not isinstance(cache,dict):cache={}
    entries=read_sources(manifest,Path(args.source_root),cache)
    if args.only_source:
        if not SAFE_SOURCE.fullmatch(args.only_source):p.error("unsafe --only-source")
        entries=[e for e in entries if e["source"].name==args.only_source]
        if not entries:raise ValueError("SOURCE_NAME_NOT_FOUND")
    if args.inventory_only:
        stats=collections.Counter()
        source_rows=0
        for e in entries:
            key=e["source"].stem+"_"+e["sha"][:12]
            source_rows+=len(e["rows"])
            status=("NO_APPROVED_ROI" if not e["rows"] else
                    "ALREADY_GENERATED" if (output_root/"sources"/key/"report.json").is_file() else
                    "HELD" if (output_root/"holds"/(key+".json")).is_file() else "PENDING")
            stats[status]+=1
        print(json.dumps({"status":"INVENTORY_ONLY","total_source_png":len(entries),
           "approved_source_rows_including_rebalances":source_rows,
           "counts":dict(stats),"RUNTIME_VALIDATION":"UNTESTED"},ensure_ascii=False))
        return
    if args.execute:atomic_json(cache_path,cache)
    results=[];attempted=0
    # Bound actual new builds. Previously verified sources do not consume slots.
    for e in entries:
        key=e["source"].stem+"_"+e["sha"][:12]
        hold_file=output_root/"holds"/(key+".json")
        if hold_file.is_file() and not args.retry_holds:
            results.append({"source":e["source"].name,"status":"HELD_PREVIOUSLY"})
            continue
        if e["rows"] and not (output_root/"sources"/key/"report.json").exists():
            if attempted>=args.max_sources:break
            attempted+=1
        try:
            r=run_source(e,output_root,Path(args.dds_root),
                         max_opaque_fraction=args.max_opaque_fraction,
                         execute=args.execute,mips=args.mips)
            results.append(r)
        except Exception as exc:
            hold={"source":e["source"].name,"sha":e["sha"],"status":"HOLD_ERROR",
                  "error":type(exc).__name__+":"+str(exc)[:180],
                  "time_utc":dt.datetime.now(dt.timezone.utc).isoformat()}
            if args.execute:atomic_json(hold_file,hold)
            results.append(hold)
    counted=collections.Counter(r["status"] for r in results)
    summary={"schema":LAST_RUN_SCHEMA,"time_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
             "dry_run":not args.execute,"total_sources":len(entries),
             "source_entries_inspected":len(results),"new_attempts":attempted,
             "counts":dict(counted),
             "painted_this_run":sum(r.get("ready_count",0) for r in results if r["status"]=="TEST_ONLY_SAVED"),
             "results":results,
             "next_step":"Repeat --execute --max-sources 1; already saved files are hash-checked and skipped",
             "runtime_validation":"UNTESTED"}
    if args.execute: atomic_json(output_root/"last_run.json",summary)
    print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":main()