#!/usr/bin/env python3
"""B/C1 ImageGen PNG -> exact CLEAN -> unpromoted RGBA32/BC3 DDS QA.

The native ChatGPT image generator runs in each B or C1 conversation, NOT in GitHub
Actions. This deterministic consumer refuses absent/unverified generator pixels
instead of silently replacing them with fonts/vectors or fabricated "AI" art.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import urllib.request
from urllib.parse import urlparse

import numpy as np
from PIL import Image

SCHEMA = "outrun-b-imagegen-v1"
C1_SCHEMA = "outrun-c1-imagegen-v1"


def validate_role(raw: dict) -> tuple[str, int]:
    role, index = raw.get("role"), raw.get("queue_index")
    schemas = {"B": SCHEMA, "C1": C1_SCHEMA}
    if role not in schemas or raw.get("schema") != schemas.get(role) or type(index) is not int or index < 0:
        raise ValueError("B/C1 actual ImageGen requires exact role, schema and numeric index")
    # Existing B in-flight even index % 4 == 2 remains executable only when
    # explicitly declared, instead of silently reassigned to C1 after cutover.
    if role == "B" and index % 4 == 2 and raw.get("legacy_b_inflight") is not True:
        raise ValueError("B even % 4 == 2 requires explicit pre-cutover in-flight ownership")
    if (role == "B" and index % 2) or (role == "C1" and index % 4 != 2):
        raise ValueError("New B/C1 work must use distinct even shards")

    return role, index
MAX_INPUT_BYTES = 75 * 1024 * 1024
DS = Image.Resampling.LANCZOS


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bound(repo: Path, spec: dict) -> bytes:
    if not isinstance(spec, dict) or not isinstance(spec.get("sha256"), str):
        raise ValueError("Missing exact SHA256-bound source reference")
    target = spec.get("path")
    if not isinstance(target, str) or not target:
        raise ValueError("Missing source path")
    if target.startswith("https://"):
        url = urlparse(target)
        if url.hostname != "raw.githubusercontent.com" or url.username or url.password:
            raise ValueError("Only pinned public raw.githubusercontent.com source URLs supported")
        with urllib.request.urlopen(target, timeout=60) as stream:
            data = stream.read(MAX_INPUT_BYTES + 1)
    else:
        f = (repo / target).resolve()
        if not f.is_relative_to(repo.resolve()) or Path(target).is_absolute():
            raise ValueError("Source path escapes repository")
        data = f.read_bytes()
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("Asset exceeds upload bound")
    if digest(data) != spec["sha256"]:
        raise ValueError("Source SHA256 does not match: " + target)
    return data


def bbox(raw: object, width: int, height: int) -> tuple[int, int, int, int]:
    if not isinstance(raw, list) or len(raw) != 4 or any(type(n) is not int for n in raw):
        raise ValueError("Invalid bounding box")
    x0, y0, x1, y1 = raw
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise ValueError("Bounding box outside source")
    return x0, y0, x1, y1


def dds_format(data: bytes) -> tuple[int, int, str]:
    """Strict single-mip DDS: keep the original header and codec unchanged."""
    if len(data) < 128 or data[:4] != b"DDS ":
        raise ValueError("Not a DDS")
    h, w = struct.unpack_from("<II", data, 12)
    mip = struct.unpack_from("<I", data, 28)[0]
    fourcc = data[84:88]
    if not (w > 0 and h > 0 and w*h <= 16_777_216 and mip in (0, 1)):
        raise ValueError("Unsupported DDS dimensions/mip chain; HOLD")
    if fourcc == b"DXT5":
        if w % 4 or h % 4:
            raise ValueError("Non-block-aligned BC3 dimensions; HOLD")
        if len(data) != 128 + (w//4)*(h//4)*16:
            raise ValueError("BC3 payload/mip mismatch; HOLD")
        return w, h, "BC3_DXT5"
    if fourcc == bytes(4) and struct.unpack_from("<I", data, 88)[0] == 32:
        if len(data) != 128 + w*h*4:
            raise ValueError("RGBA32 payload/mip mismatch; HOLD")
        return w, h, "RGBA32"
    raise ValueError("Only single-mip RGBA32 or BC3/DXT5 supported; HOLD")


def dds_rgba_read(data: bytes) -> np.ndarray:
    w, h, _ = dds_format(data)
    with Image.open(io.BytesIO(data)) as im:
        if im.size != (w, h):
            raise ValueError("Unexpected DDS decoded dimensions")
        return np.asarray(im.convert("RGBA"))[::-1].copy()


def _bc3_block(raw_rgba: np.ndarray) -> bytes:
    """Deterministic BC3 block encoder. Re-encode ONLY touched 4x4 blocks."""
    px = raw_rgba.reshape(16, 4).astype(np.int32)
    alpha = px[:, 3]
    a0, a1 = int(alpha.max()), int(alpha.min())
    if a0 > a1:
        ap = [a0, a1] + [((7-i)*a0+i*a1)//7 for i in range(1, 7)]
    else:
        ap = [a0, a1, 0, 0, 0, 0, 0, 0]
    ai = np.argmin(abs(alpha[:, None]-np.asarray(ap)[None, :]), axis=1)
    alpha_indices = sum(int(v) << (3*i) for i, v in enumerate(ai))
    alpha_payload = bytes((a0, a1)) + alpha_indices.to_bytes(6, "little")

    active = px[alpha > 0, :3]
    if not len(active):
        active = px[:, :3]
    lo, hi = active.min(axis=0), active.max(axis=0)
    def rgb565(v: np.ndarray) -> int:
        return ((int(v[0])*31+127)//255 << 11 |
                (int(v[1])*63+127)//255 << 5 |
                (int(v[2])*31+127)//255)
    c0, c1 = rgb565(hi), rgb565(lo)
    if c0 < c1:
        c0, c1 = c1, c0
    def expand(c: int) -> np.ndarray:
        r = (c >> 11) & 31
        g = (c >> 5) & 63
        b = c & 31
        return np.asarray([(r << 3) | (r >> 2),
                           (g << 2) | (g >> 4),
                           (b << 3) | (b >> 2)], dtype=np.int32)
    p0, p1 = expand(c0), expand(c1)
    pal = np.stack((p0, p1, (2*p0+p1)//3, (p0+2*p1)//3))
    err = np.sum((px[:, None, :3]-pal[None, :, :])**2, axis=2)
    ci = np.argmin(err, axis=1)
    color_indices = sum(int(v) << (2*i) for i, v in enumerate(ci))
    return alpha_payload + struct.pack("<HHI", c0, c1, color_indices)


def dds_rgba_encode(template: bytes, readable: np.ndarray) -> bytes:
    """Preserve exact BC3 blocks outside edits, original masks/codec/header."""
    w, h, fmt = dds_format(template)
    if readable.shape != (h, w, 4) or readable.dtype != np.uint8:
        raise ValueError("Candidate dimensions or pixel type mismatch")
    raw = readable[::-1]
    if fmt == "BC3_DXT5":
        old = dds_rgba_read(template)[::-1]
        payload = bytearray(template[128:])
        blocks_per_row = w // 4
        for y in range(0, h, 4):
            for x in range(0, w, 4):
                new_block = raw[y:y+4, x:x+4]
                if np.array_equal(old[y:y+4, x:x+4], new_block):
                    continue
                at = ((y//4)*blocks_per_row+x//4)*16
                payload[at:at+16] = _bc3_block(new_block)
        return template[:128] + bytes(payload)

    masks = struct.unpack_from("<IIII", template, 92)
    positions = []
    for mask in masks:
        if mask not in (0x000000FF, 0x0000FF00, 0x00FF0000, 0xFF000000):
            raise ValueError("Non-byte-aligned DDS channel mask; HOLD")
        positions.append((mask.bit_length()-8)//8)
    if sorted(positions) != [0, 1, 2, 3]:
        raise ValueError("Missing/duplicate DDS color channels; HOLD")
    payload = np.empty(raw.shape, dtype=np.uint8)
    for component, position in enumerate(positions):
        payload[:, :, position] = raw[:, :, component]
    return template[:128] + payload.tobytes()



def png_rgba(data: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(data)) as im:
        if im.format != "PNG" or im.mode != "RGBA":
            raise ValueError("Generator output must be true transparent RGBA PNG, no JPEG/fake transparency")
        ar = np.asarray(im).copy()
    if np.all(ar[:, :, 3] == 255):
        raise ValueError("Generator output has no transparency")
    return ar


def premul_fit(rgba: np.ndarray, limit_w: int, limit_h: int, mode: str) -> np.ndarray:
    """Native single LANCZOS resize of alpha-premultiplied RGB: no dark halos."""
    mask = rgba[:, :, 3] >= 8
    ys, xs = np.nonzero(mask)
    if len(xs) < 80:
        raise ValueError("Generated image missing visible text")
    crop = rgba[ys.min():ys.max()+1, xs.min():xs.max()+1].copy()
    crop[crop[:, :, 3] < 8] = 0
    ch, cw = crop.shape[:2]
    if mode == "contain":
        ratio = min(limit_w / cw, limit_h / ch)
        new_w, new_h = max(1, round(cw*ratio)), max(1, round(ch*ratio))
    elif mode == "width_priority":
        # Production gate preserves max source bbox but lets source italic width
        # run up to the full safe width without repeated low-res upscaling.
        new_w, new_h = limit_w, limit_h
    else:
        raise ValueError("fit_mode must be contain or width_priority")
    alpha = crop[:, :, 3].astype(np.float32) / 255.0
    pm = np.empty_like(crop)
    pm[:, :, :3] = np.rint(crop[:, :, :3].astype(np.float32)*alpha[:,:,None]).astype(np.uint8)
    pm[:, :, 3] = crop[:, :, 3]
    fitted = np.asarray(Image.fromarray(pm, "RGBA").resize((new_w,new_h), DS)).copy()
    a = fitted[:, :, 3].astype(np.float32)
    out = np.zeros_like(fitted)
    out[:, :, 3] = fitted[:, :, 3]
    nz = a > 0
    out[nz, :3] = np.minimum(255, np.rint(fitted[nz, :3].astype(np.float32)*255/a[nz,None])).astype(np.uint8)
    return out


def save_contact(path: Path, items: list[np.ndarray], rect, gray: int, percent: int, raw: bool) -> None:
    x0,y0,x1,y1=rect
    views=[]
    for ar in items:
        if raw:
            ar=ar[::-1]
            cy0,cy1=ar.shape[0]-y1,ar.shape[0]-y0
        else:
            cy0,cy1=y0,y1
        tile=Image.fromarray(ar[cy0:cy1,x0:x1],"RGBA")
        base=Image.new("RGBA",tile.size,(gray,gray,gray,255))
        base.alpha_composite(tile)
        im=base.convert("RGB")
        if percent != 100:
            im=im.resize((max(1,round(im.width*percent/100)),max(1,round(im.height*percent/100))),DS)
        views.append(im)
    w,h=views[0].size
    canvas=Image.new("RGB",(w*len(views)+16*(len(views)-1),h),(gray,gray,gray))
    for i,im in enumerate(views):
        canvas.paste(im,(i*(w+16),0))
    canvas.save(path)


def run(repo: Path, manifest: Path) -> dict:
    repo=repo.resolve()
    raw=json.loads(manifest.read_text(encoding="utf-8"))
    role, index = validate_role(raw)
    requests_dir = (repo / f"localization/graphics/role_{role}/imagegen_requests").resolve()
    if not manifest.resolve().is_relative_to(requests_dir):
        raise ValueError(f"Manifest must remain under role_{role}/imagegen_requests")
    if not (repo / raw["generated"]["path"]).resolve().is_relative_to(requests_dir):
        raise ValueError(f"Generated PNG must remain under role_{role}/imagegen_requests")
    if raw.get("generator",{}).get("provider") not in ("chatgpt-image-generator","chatgpt-image-plugin"):
        raise ValueError("Only actual B/C1 image-generator output may enter this lane")
    if not raw["generator"].get("generation_id") or not raw["generator"].get("prompt"):
        raise ValueError("No generator invocation/prompt provenance; HOLD")
    if not isinstance(raw.get("target_text"),str) or not raw["target_text"].strip():
        raise ValueError("No exact Korean source-text transcription")
    S0=bound(repo,raw["source"])
    O0=bound(repo,raw["official"])
    C0=bound(repo,raw["clean"])
    M0=bound(repo,raw["removal_mask"])
    P0=bound(repo,raw["generated"])
    S, O=dds_rgba_read(S0),dds_rgba_read(O0)
    if S.shape!=O.shape:
        raise ValueError("Source/candidate dimensions mismatch")
    h,w=S.shape[:2]
    with Image.open(io.BytesIO(C0)) as im:
        if im.format!="PNG" or im.mode!="RGBA" or im.size!=(w,h):
            raise ValueError("CLEAN must be full-native FLIPY readable RGBA PNG")
        C=np.asarray(im).copy()
    with Image.open(io.BytesIO(M0)) as im:
        if im.format!="PNG" or im.size!=(w,h):
            raise ValueError("Mask must be full-native PNG")
        rm=np.asarray(im.convert("L"))>0
    if np.any(np.any(S!=C,axis=2)&~rm) or np.any(C[:,:,3][rm]):
        raise ValueError("Source/CLEAN not independent-removal-equivalent; HOLD")
    r=bbox(raw["source_bbox"],w,h)
    target=bbox(raw["placement_bbox"],w,h)
    allowed=bbox(raw["replace_roi"],w,h)
    if not (allowed[0]<=r[0]<=target[0]<target[2]<=r[2]<=allowed[2] and
            allowed[1]<=r[1]<=target[1]<target[3]<=r[3]<=allowed[3]):
        raise ValueError("Placement/ROI exceeds English source ceiling")
    if not np.any(rm[r[1]:r[3],r[0]:r[2]]):
        raise ValueError("No exact original-removal evidence for region")
    if not raw.get("plate_review",{}).get("status")=="PLATE_PASS":
        raise ValueError("Missing independently approved CLEAN record")
    # A written plate PASS claim alone is not independent verification; bind
    # to exact SHA-backed review file and require its immutable source hashes.
    rev=json.loads(bound(repo,raw["plate_review"]["ref"]))
    if (rev.get("status")!="PLATE_PASS" or rev.get("source_sha256")!=raw["source"]["sha256"]
        or rev.get("clean_sha256")!=raw["clean"]["sha256"]
        or rev.get("removal_sha256")!=raw["removal_mask"]["sha256"]
        or rev.get("reviewer")!="C2"):
        raise ValueError("Independent C2 plate identity mismatch")
    generated=png_rgba(P0)
    dest_w,dest_h=target[2]-target[0],target[3]-target[1]
    fitted=premul_fit(generated,dest_w,dest_h,raw.get("fit_mode","contain"))
    fh,fw=fitted.shape[:2]
    assert fh<=dest_h and fw<=dest_w
    dx=target[0]+(dest_w-fw)//2
    dy=target[1]+(dest_h-fh)//2
    placed=np.zeros_like(C)
    placed[dy:dy+fh,dx:dx+fw]=fitted
    roi=tuple(allowed)
    x0,y0,x1,y1=roi
    N=O.copy()
    bg=Image.fromarray(C[y0:y1,x0:x1],"RGBA")
    fg=Image.fromarray(placed[y0:y1,x0:x1],"RGBA")
    N[y0:y1,x0:x1]=np.asarray(Image.alpha_composite(bg,fg))
    change=np.any(N!=O,axis=2)
    change[y0:y1,x0:x1]=False
    if np.any(change):
        raise ValueError("Modified protected atlas outside declared patch ROI")
    source_effect=bbox(raw["source_bbox"],w,h)
    out_effect=placed[:,:,3]>0
    ys,xs=np.nonzero(out_effect)
    eff=(int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1)
    if not (source_effect[0]<=eff[0]<eff[2]<=source_effect[2]
            and source_effect[1]<=eff[1]<eff[3]<=source_effect[3]):
        raise ValueError("Generated lettering spills one pixel beyond English")
    # No untracked face/sheet residue relative to exact CLEAN in the ROI.
    changed_final=np.any(N!=C,axis=2)
    changed_final[y0:y1,x0:x1]=False
    # Other atlas sprites may be previously localized, so only compare within
    # this ROI and outside the precise generated lettering mask.
    contamination=np.any(N[y0:y1,x0:x1]!=C[y0:y1,x0:x1],axis=2)&~out_effect[y0:y1,x0:x1]
    if np.any(contamination):
        raise ValueError("Clean-to-final changed outside new text alpha")
    dds=dds_rgba_encode(O0,N)
    saved=dds_rgba_read(dds)
    _, _, fmt=dds_format(O0)
    mismatches=int(np.count_nonzero(np.any(saved!=N,axis=2)))
    if fmt=="RGBA32" and mismatches:
        raise ValueError("Persisted DDS RAW/readable mismatch")
    # BC3 is lossy. Inspect SAVED pixels, not just the pre-encode image;
    # even a single compressed 4x4 block contaminating protected art is HOLD.
    changed_saved=np.any(saved!=O,axis=2)
    protected=np.ones((h,w),dtype=bool)
    protected[r[1]:r[3],r[0]:r[2]]=False
    protected_count=int(np.count_nonzero(changed_saved & protected))
    roi_protected=np.ones((h,w),dtype=bool)
    roi_protected[y0:y1,x0:x1]=False
    roi_changed=int(np.count_nonzero(changed_saved & roi_protected))
    if protected_count or roi_changed:
        raise ValueError(f"Saved {fmt} changes protected pixels: source_bbox={protected_count}, outside_roi={roi_changed}; HOLD")
    if digest(dds)==digest(O0):
        raise ValueError("No materially changed DDS")
    outdir=(repo/raw["output_dir"]).resolve()
    if not outdir.is_relative_to((repo/f"localization/graphics/role_{role}").resolve()):
        raise ValueError(f"Output must remain under role_{role}")
    outdir.mkdir(parents=True,exist_ok=True)
    name=f"{role}_IMAGEGEN_"+str(index).zfill(3)
    (outdir/(name+"_UNAPPROVED.dds")).write_bytes(dds)
    Image.fromarray(placed[::-1].copy(),"RGBA").save(outdir/(name+"_LETTERING_RAW.png"))
    evidence=[]
    for orient,gray,percent in [("FLIPY",128,100),("FLIPY",255,75),("FLIPY",0,50),("RAW",128,100)]:
        fn=name+"_SOURCE_CLEAN_OFFICIAL_GENERATED_"+orient+"_"+str(percent)+".png"
        save_contact(outdir/fn,[S,C,O,N],roi,gray,percent,orient=="RAW")
        evidence.append({"path":str((outdir/fn).relative_to(repo)),"sha256":digest((outdir/fn).read_bytes())})
    info={
      "schema":raw["schema"],"queue_index":index,"lane":role,"producer_method":"CHATGPT_IMAGEGEN_ONLY",
      "generation_provenance":raw["generator"],"manifest_sha256":digest(manifest.read_bytes()),
      "official_sha256":digest(O0),"source_sha256":digest(S0),"clean_sha256":digest(C0),
      "generated_sha256":digest(P0),"saved_trial_sha256":digest(dds),
      "dds_format":fmt,"saved_lossy_mismatch_pixels_within_bbox":mismatches,
      "saved_protected_pixels_changed":protected_count,"saved_outside_roi_pixels_changed":roi_changed,
      "fit_mode":raw.get("fit_mode","contain"),"new_effect_bbox":list(eff),
      "source_effect_bbox":list(source_effect),"roi":list(roi),
      "outside_roi_changed_pixels":0,"generated_effect_outside_bbox_pixels":0,
      "clean_to_final_outside_text_changed_pixels":0,"persisted_roundtrip_mismatch":0,
      "new_trial_dds":1,"official_promoted":0,"RUNTIME_VALIDATION":"UNTESTED",
      "P2":"IMAGEGEN_PIXEL_SOURCE_PRESENT_NOT_AUTOMATICALLY_GLYPH_APPROVED",
      "P3":"MACHINE_PASS_VISUAL_PENDING","C2":"NOT_RUN","C3":"NOT_RUN","USER_GAME":"OPEN",
      "qa_evidence":evidence
    }
    (outdir/(name+"_MACHINE.json")).write_text(json.dumps(info,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return info


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",default=".")
    p.add_argument("--manifest",required=True)
    a=p.parse_args()
    try:
        print(json.dumps(run(Path(a.repo),Path(a.manifest)),ensure_ascii=False,indent=2))
    except (KeyError,IndexError,ValueError,OSError,TypeError) as e:
        p.exit(2,"IMAGEGEN_HOLD: "+str(e)+"\n")


if __name__=="__main__":
    main()
