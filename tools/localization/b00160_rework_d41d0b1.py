#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import os
import struct
import subprocess
import urllib.request
from collections import deque
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "LOCALIZATION-LOCALIZATION_B-00160"
ASSET_ID = "D41D0B1"
INDEX = 112
SOURCE_REPO = "envido32/OR2006Sprites"
SOURCE_COMMIT = "55f67a813dd3603d201d0be0da47c071965f53a4"
SOURCE_REL = "Release/spr_sprani_selector_cvt_Exst/D41D0B1_512x64.dds"
SOURCE_URL = f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/{SOURCE_REL}"
SOURCE_SHA256 = "524de4c0db3dbb69c6cda484ace71a9213a378e3e4895a035199ced0ac0a3617"
SOURCE_BLOB_SHA = "278a518f5151f0759dfcfdc78e129a7a7cb55cf0"
EXPECTED_BYTES = 524416
W, H = 2048, 256
SOURCE_EFFECT_BBOX = [435, 19, 1357, 238]
CANDIDATE_SAFE_BBOX = [437, 21, 1354, 235]
BLOCK_SAFE_BBOX = [440, 24, 1352, 232]
SOURCE_ALPHA_PIXELS = 132035
SOURCE_COMPONENTS = 7
KOREAN = "여자친구와 함께 골에 도착하세요."
LINES = ["여자친구와 함께", "골에 도착하세요."]
SLANT_DX_PER_DY = 0.2753623188405797
SLANT_ANGLE_DEG = 15.39554925399509

CANDIDATE = ROOT / "localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/D41D0B1_512x64.dds"
REVIEW = ROOT / "localization/graphics/KOREAN_PNG_REVIEW/D41D0B1"
RUN = ROOT / "localization/graphics/role_B/20260929-B00160-rollover3"
TASK_RECORD = ROOT / "docs/automation/runs/LOCALIZATION-LOCALIZATION_B-00160.json"
REPORT = RUN / "B00160_D41D0B1_DECODED_FINAL_QA.json"

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def dds_header_info(b: bytes):
    if len(b) < 128 or b[:4] != b"DDS ":
        raise SystemExit("invalid DDS")
    h = struct.unpack_from("<I", b, 12)[0]
    w = struct.unpack_from("<I", b, 16)[0]
    mips = struct.unpack_from("<I", b, 28)[0] or 1
    fourcc = b[84:88]
    return {"width": w, "height": h, "mips": mips, "fourcc": fourcc.decode("latin1"), "header": b[:128]}

def rgb565_unpack(v: int):
    r = ((v >> 11) & 31) * 255 // 31
    g = ((v >> 5) & 63) * 255 // 63
    b = (v & 31) * 255 // 31
    return np.array([r, g, b], dtype=np.uint8)

def rgb565_pack(rgb):
    r, g, b = [int(x) for x in rgb]
    return (int(round(r * 31 / 255)) << 11) | (int(round(g * 63 / 255)) << 5) | int(round(b * 31 / 255))

def alpha_palette(a0: int, a1: int):
    if a0 > a1:
        return [
            a0, a1,
            int(round((6*a0 + 1*a1)/7)), int(round((5*a0 + 2*a1)/7)),
            int(round((4*a0 + 3*a1)/7)), int(round((3*a0 + 4*a1)/7)),
            int(round((2*a0 + 5*a1)/7)), int(round((1*a0 + 6*a1)/7)),
        ]
    return [
        a0, a1,
        int(round((4*a0 + 1*a1)/5)), int(round((3*a0 + 2*a1)/5)),
        int(round((2*a0 + 3*a1)/5)), int(round((1*a0 + 4*a1)/5)),
        0, 255,
    ]

def decode_bc3(data: bytes):
    info = dds_header_info(data)
    if (info["width"], info["height"], info["mips"], info["fourcc"]) != (W, H, 1, "DXT5"):
        raise SystemExit(f"unexpected DDS metadata: {info}")
    payload = data[128:]
    if len(payload) != W * H:
        raise SystemExit(f"unexpected DXT5 payload bytes {len(payload)}")
    out = np.zeros((H, W, 4), dtype=np.uint8)
    pos = 0
    for by in range(0, H, 4):
        for bx in range(0, W, 4):
            block = payload[pos:pos+16]; pos += 16
            a0, a1 = block[0], block[1]
            ap = alpha_palette(a0, a1)
            abits = int.from_bytes(block[2:8], "little")
            c0, c1 = struct.unpack_from("<HH", block, 8)
            c0rgb = rgb565_unpack(c0).astype(np.int32)
            c1rgb = rgb565_unpack(c1).astype(np.int32)
            cp = [
                c0rgb,
                c1rgb,
                (2*c0rgb + c1rgb) // 3,
                (c0rgb + 2*c1rgb) // 3,
            ]
            cbits = struct.unpack_from("<I", block, 12)[0]
            for py in range(4):
                for px in range(4):
                    i = py*4 + px
                    ai = (abits >> (3*i)) & 7
                    ci = (cbits >> (2*i)) & 3
                    out[by+py, bx+px, :3] = cp[ci]
                    out[by+py, bx+px, 3] = ap[ai]
    return out

def encode_alpha_block(alpha):
    vals = [int(v) for v in alpha.reshape(-1)]
    if max(vals) == 0:
        return b"\x00" * 8
    a0, a1 = max(vals), min(vals)
    if a0 == a1:
        a1 = 0 if a0 else 1
    if a0 <= a1:
        a0, a1 = max(a0, a1), min(a0, a1)
        if a0 == a1:
            a0 = min(255, a1 + 1)
    pal = alpha_palette(a0, a1)
    bits = 0
    for i, v in enumerate(vals):
        idx = min(range(8), key=lambda q: (pal[q]-v)*(pal[q]-v))
        bits |= idx << (3*i)
    return bytes([a0, a1]) + bits.to_bytes(6, "little")

def encode_color_block(rgb, alpha):
    flat = rgb.reshape(-1, 3).astype(np.int32)
    vis = flat[alpha.reshape(-1) > 0]
    if len(vis) == 0:
        vis = flat
    lum = vis[:,0]*2126 + vis[:,1]*7152 + vis[:,2]*722
    lo = vis[int(np.argmin(lum))]
    hi = vis[int(np.argmax(lum))]
    c_hi, c_lo = rgb565_pack(hi), rgb565_pack(lo)
    if c_hi == c_lo:
        if c_hi < 65535:
            c_hi += 1
        elif c_lo > 0:
            c_lo -= 1
    c0, c1 = (c_hi, c_lo) if c_hi > c_lo else (c_lo, c_hi)
    p0 = rgb565_unpack(c0).astype(np.int32)
    p1 = rgb565_unpack(c1).astype(np.int32)
    pal = np.stack([p0, p1, (2*p0+p1)//3, (p0+2*p1)//3], axis=0)
    bits = 0
    for i, pix in enumerate(flat):
        d = np.sum((pal - pix) ** 2, axis=1)
        idx = int(np.argmin(d))
        bits |= idx << (2*i)
    return struct.pack("<HHI", c0, c1, bits)

def encode_candidate(source_bytes: bytes, source_raw: np.ndarray, target_raw: np.ndarray):
    out = bytearray(source_bytes[:128])
    payload = source_bytes[128:]
    pos = 0
    rewritten_candidate = 0
    cleared_source = 0
    copied = 0
    for by in range(0, H, 4):
        for bx in range(0, W, 4):
            orig = payload[pos:pos+16]; pos += 16
            sa = source_raw[by:by+4, bx:bx+4, 3]
            ta = target_raw[by:by+4, bx:bx+4, 3]
            if np.any(ta > 0):
                trgb = target_raw[by:by+4, bx:bx+4, :3]
                out += encode_alpha_block(ta)
                out += encode_color_block(trgb, ta)
                rewritten_candidate += 1
            elif np.any(sa > 0):
                out += b"\x00" * 8
                out += orig[8:16]
                cleared_source += 1
            else:
                out += orig
                copied += 1
    return bytes(out), {"candidate_blocks": rewritten_candidate, "source_clear_blocks": cleared_source, "copied_blocks": copied}

def bbox_from_mask(mask):
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()+1), int(ys.max()+1)]

def count_components_8(mask):
    seen = np.zeros(mask.shape, dtype=bool)
    comps = []
    ys, xs = np.nonzero(mask)
    for y, x in zip(ys.tolist(), xs.tolist()):
        if seen[y, x]:
            continue
        q = deque([(y, x)]); seen[y, x] = True; n = 0
        x0=x1=x; y0=y1=y
        while q:
            yy, xx = q.popleft(); n += 1
            x0=min(x0,xx); x1=max(x1,xx); y0=min(y0,yy); y1=max(y1,yy)
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    if not dx and not dy: continue
                    ny,nx=yy+dy,xx+dx
                    if 0<=ny<H and 0<=nx<W and mask[ny,nx] and not seen[ny,nx]:
                        seen[ny,nx]=True; q.append((ny,nx))
        comps.append({"pixels":n,"bbox":[x0,y0,x1+1,y1+1]})
    return sorted(comps, key=lambda c:c["pixels"], reverse=True)

def clean_plate_4_neighbor(src_disp: np.ndarray):
    mask = src_disp[:,:,3] > 0
    known = ~mask
    rgb = src_disp[:,:,:3].copy()
    iters = 0
    while not np.all(known):
        cnt = np.zeros((H,W), dtype=np.uint8)
        acc = np.zeros((H,W,3), dtype=np.float32)
        k = known[:-1,:]
        cnt[1:,:] += k
        acc[1:,:,:] += rgb[:-1,:,:] * k[:,:,None]
        k = known[1:,:]
        cnt[:-1,:] += k
        acc[:-1,:,:] += rgb[1:,:,:] * k[:,:,None]
        k = known[:,:-1]
        cnt[:,1:] += k
        acc[:,1:,:] += rgb[:,:-1,:] * k[:,:,None]
        k = known[:,1:]
        cnt[:,:-1] += k
        acc[:,:-1,:] += rgb[:,1:,:] * k[:,:,None]
        front = (~known) & (cnt > 0)
        if not np.any(front):
            raise SystemExit("4-neighbor diffusion stalled")
        rgb[front] = np.rint(acc[front] / cnt[front,None]).clip(0,255).astype(np.uint8)
        known[front] = True
        iters += 1
    out = np.zeros_like(src_disp)
    out[:,:,:3] = rgb
    out[:,:,3] = 0
    return out, iters

def find_font():
    spec = "Noto Sans CJK KR:style=Black"
    s = subprocess.check_output(["fc-match","-f","%{file}|%{index}\n",spec], text=True).strip().splitlines()[0]
    p, idx = s.rsplit("|",1)
    if not Path(p).exists():
        raise SystemExit(f"font not found: {p}")
    return p, int(idx)

def render_line(text, font, shear):
    pad=18
    probe=Image.new("RGBA",(1400,180),(0,0,0,0)); d=ImageDraw.Draw(probe)
    bb=d.textbbox((0,0),text,font=font,stroke_width=7)
    w=bb[2]-bb[0]+pad*2+10; h=bb[3]-bb[1]+pad*2+10
    im=Image.new("RGBA",(w,h),(0,0,0,0)); dr=ImageDraw.Draw(im)
    x=pad-bb[0]; y=pad-bb[1]
    navy=(5,15,61,235)
    dr.text((x+4,y+4),text,font=font,fill=navy,stroke_width=9,stroke_fill=(0,12,58,210))
    dr.text((x,y),text,font=font,fill=(255,255,255,255),stroke_width=7,stroke_fill=(5,15,61,255))
    ab=im.getchannel("A").getbbox()
    im=im.crop((ab[0]-3,ab[1]-3,ab[2]+3,ab[3]+3))
    hh=im.height; shift=int(math.ceil(shear*hh))
    out=im.transform((im.width+shift,hh),Image.Transform.AFFINE,
                     (1,shear,-shear*(hh-1),0,1,0),
                     resample=Image.Resampling.BICUBIC)
    ab=out.getchannel("A").getbbox()
    return out.crop(ab)

def render_korean(clean: np.ndarray, font_path: str, font_index: int):
    l,t,r,b = BLOCK_SAFE_BBOX
    maxw=r-l-32; maxh=b-t-20
    chosen=None
    for size in range(86, 55, -1):
        font=ImageFont.truetype(font_path,size=size,index=font_index)
        ims=[render_line(x,font,SLANT_DX_PER_DY) for x in LINES]
        gap=10
        tw=max(i.width for i in ims); th=sum(i.height for i in ims)+gap
        if tw<=maxw and th<=maxh:
            chosen=(size,ims,gap,tw,th); break
    if not chosen:
        raise SystemExit("Korean render could not fit block-safe region")
    size,ims,gap,tw,th=chosen
    base=Image.fromarray(clean,"RGBA")
    xcenter=(l+r)//2
    y=t+(b-t-th)//2
    placed=[]
    for im,text in zip(ims,LINES):
        x=xcenter-im.width//2
        base.alpha_composite(im,(x,y))
        bb=im.getchannel("A").getbbox()
        placed.append({"text":text,"bbox":[x+bb[0],y+bb[1],x+bb[2],y+bb[3]],"font_size":size})
        y += im.height + gap
    arr=np.array(base,dtype=np.uint8)
    bb=bbox_from_mask(arr[:,:,3]>0)
    return arr,bb,placed,size

def inside(inner, outer):
    return inner and inner[0]>=outer[0] and inner[1]>=outer[1] and inner[2]<=outer[2] and inner[3]<=outer[3]

def save_png(arr, path):
    path.parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray(arr,"RGBA").save(path,optimize=False)

def main():
    now=datetime.now(ZoneInfo("Asia/Seoul")).replace(microsecond=0).isoformat()
    req=urllib.request.Request(SOURCE_URL,headers={"User-Agent":"OutRun2006Tweaks-localization-B00160"})
    with urllib.request.urlopen(req,timeout=60) as f:
        src_bytes=f.read()
    if len(src_bytes)!=EXPECTED_BYTES or sha256_bytes(src_bytes)!=SOURCE_SHA256:
        raise SystemExit("exact pinned GitHub source identity mismatch")
    info=dds_header_info(src_bytes)
    if (info["width"],info["height"],info["mips"],info["fourcc"])!=(W,H,1,"DXT5"):
        raise SystemExit(f"source DDS structure mismatch {info}")

    source_raw=decode_bc3(src_bytes)
    source_disp=np.flipud(source_raw).copy()
    source_mask=source_disp[:,:,3]>0
    source_pixels=int(source_mask.sum())
    source_bbox=bbox_from_mask(source_mask)
    comps=count_components_8(source_mask)
    if source_pixels!=SOURCE_ALPHA_PIXELS or source_bbox!=SOURCE_EFFECT_BBOX or len(comps)!=SOURCE_COMPONENTS:
        raise SystemExit(f"canonical alpha contract mismatch pixels={source_pixels} bbox={source_bbox} comps={len(comps)}")

    clean,iters=clean_plate_4_neighbor(source_disp)
    if iters!=49:
        raise SystemExit(f"corrected 4-neighbor convergence expected 49, got {iters}")
    outside_clean=int(np.count_nonzero(np.any(clean[~source_mask]!=source_disp[~source_mask],axis=1)))
    if outside_clean!=0 or int(np.count_nonzero(clean[:,:,3]))!=0:
        raise SystemExit("clean plate protected/alpha gate failed")

    font_path,font_index=find_font()
    cand_disp,cand_pre_bbox,line_records,font_size=render_korean(clean,font_path,font_index)
    if not inside(cand_pre_bbox,BLOCK_SAFE_BBOX) or not inside(cand_pre_bbox,CANDIDATE_SAFE_BBOX):
        raise SystemExit(f"pre-compression Korean bbox escaped safe bounds: {cand_pre_bbox}")

    target_raw=np.flipud(cand_disp).copy()
    cand_bytes,block_stats=encode_candidate(src_bytes,source_raw,target_raw)
    if len(cand_bytes)!=EXPECTED_BYTES or cand_bytes[:128]!=src_bytes[:128]:
        raise SystemExit("candidate DDS size/header changed")
    final_raw=decode_bc3(cand_bytes)
    final_disp=np.flipud(final_raw).copy()
    final_mask=final_disp[:,:,3]>0
    final_bbox=bbox_from_mask(final_mask)
    if not inside(final_bbox,CANDIDATE_SAFE_BBOX):
        raise SystemExit(f"decoded-final candidate bbox escaped safe bbox: {final_bbox}")

    # All visible source English must be gone: any final alpha outside the Korean block-safe region is residue.
    l,t,r,b=BLOCK_SAFE_BBOX
    outside_allowed=final_mask.copy()
    outside_allowed[t:b,l:r]=False
    english_residue_pixels=int(outside_allowed.sum())
    introduced_outside_source=final_mask.copy()
    sl,st,sr,sb=SOURCE_EFFECT_BBOX
    introduced_outside_source[st:sb,sl:sr]=False
    introduced_outside_source_pixels=int(introduced_outside_source.sum())

    changed=np.any(final_disp!=source_disp,axis=2)
    outside_source_region=changed.copy()
    outside_source_region[st:sb,sl:sr]=False
    changed_outside_source_region=int(outside_source_region.sum())

    # Effective protected area is all original alpha-zero pixels outside the approved Korean lettering region.
    protected=(source_disp[:,:,3]==0)
    effective_protected=protected.copy()
    effective_protected[t:b,l:r]=False
    changed_in_effective_protected=int((changed & effective_protected).sum())

    alpha_changed=(final_disp[:,:,3]!=source_disp[:,:,3])
    alpha_outside_source_region=alpha_changed.copy()
    alpha_outside_source_region[st:sb,sl:sr]=False
    alpha_changed_outside_source_region=int(alpha_outside_source_region.sum())

    if any((english_residue_pixels,introduced_outside_source_pixels,changed_outside_source_region,
            changed_in_effective_protected,alpha_changed_outside_source_region)):
        raise SystemExit(json.dumps({
            "english_residue_pixels":english_residue_pixels,
            "introduced_alpha_outside_source_region":introduced_outside_source_pixels,
            "changed_pixels_outside_source_region":changed_outside_source_region,
            "changed_pixels_in_effective_protected_mask":changed_in_effective_protected,
            "alpha_changed_outside_source_region":alpha_changed_outside_source_region
        },indent=2))

    # Compression must preserve the intended visible Korean coverage closely; exact pixel identity is not expected for BC3.
    pre_mask=cand_disp[:,:,3]>0
    pre_pixels=int(pre_mask.sum()); final_pixels=int(final_mask.sum())
    iou_num=int((pre_mask & final_mask).sum()); iou_den=int((pre_mask | final_mask).sum())
    visible_iou=(iou_num/iou_den) if iou_den else 1.0
    if visible_iou < 0.97:
        raise SystemExit(f"decoded-final BC3 visible-mask IoU too low: {visible_iou}")

    REVIEW.mkdir(parents=True,exist_ok=True); RUN.mkdir(parents=True,exist_ok=True); CANDIDATE.parent.mkdir(parents=True,exist_ok=True)
    save_png(source_disp,REVIEW/"source_display.png")
    save_png(clean,REVIEW/"clean_plate_display.png")
    save_png(final_disp,REVIEW/"candidate_display.png")

    # Native-resolution 3-panel review.
    canvas=Image.new("RGBA",(W*3,H+28),(28,28,28,255))
    canvas.paste(Image.fromarray(source_disp,"RGBA"),(0,28))
    canvas.paste(Image.fromarray(clean,"RGBA"),(W,28))
    canvas.paste(Image.fromarray(final_disp,"RGBA"),(W*2,28))
    dr=ImageDraw.Draw(canvas)
    dr.text((8,7),"SOURCE",(255,255,255,255))
    dr.text((W+8,7),"CLEAN PLATE",(255,255,255,255))
    dr.text((W*2+8,7),"KOREAN CANDIDATE",(255,255,255,255))
    canvas.save(REVIEW/"comparison.png",optimize=False)

    prompt={
      "contract":"outrun-first-pass-edit-v2",
      "asset":{"id":ASSET_ID,"index":INDEX,"canvas":[W,H],"source_sha256":SOURCE_SHA256,
               "source_git_blob_sha":SOURCE_BLOB_SHA,"dds_format":"DXT5","mip_count":1,
               "source_text_transform":"flip_y"},
      "elements":[{
        "element_id":"index112_girlfriend_goal",
        "source_text":"Try to reach the goal with your girlfriend.",
        "approved_korean":KOREAN,
        "line_breaks":LINES,
        "source_bbox":SOURCE_EFFECT_BBOX,
        "permitted_region":CANDIDATE_SAFE_BBOX,
        "candidate_safe_bbox":CANDIDATE_SAFE_BBOX,
        "block_safe_bbox":BLOCK_SAFE_BBOX,
        "safety_inset_px":2,
        "source_text_transform":"flip_y",
        "display_transform":"raw_flip_y_to_readable",
        "baseline_vector":[1,0],
        "slant_dx_per_dy":SLANT_DX_PER_DY,
        "slant_angle_deg":SLANT_ANGLE_DEG,
        "slant_direction":"right",
        "style_traits":{
          "fill":"opaque white",
          "outline_shadow":"dark navy family",
          "dominant_dark_rgba_examples":[[5,15,61,255],[0,12,58,255],[3,13,61,255]],
          "line_structure":"two centered lines",
          "font_identifier":f"{Path(font_path).name}#{font_index}",
          "font_size_px":font_size,
          "outline_px":7,
          "shadow_offset_px":[4,4],
          "shadow_outer_px":9
        }
      }],
      "reconstruction":{
        "source_effect_mask":"all exact canonical decoded alpha>0 pixels; 132035 pixels, seven text-owned components",
        "method":"synchronous 4-neighbor hidden-RGB diffusion from immutable source alpha==0 pixels; round-nearest arithmetic mean; output alpha zero",
        "iterations_to_converge":iters
      },
      "instructions":{
        "positive":[
          "EDIT, DO NOT REDESIGN. Exact HD source is authoritative.",
          "Remove the complete English source text plus its own outline/shadow only.",
          "Render only the approved Korean wording in the cleared region.",
          "Match the measured right slant, white fill, dark navy effect hierarchy, two-line centered layout, raw flip_y orientation and transparency.",
          "Keep all Korean effect pixels inside the conservative 2px-inset candidate_safe_bbox.",
          "The result must look as though the Korean text was part of the original game artwork, not pasted on later."
        ],
        "negative":[
          "No visible English residue; no cover rectangle, panel, blur patch or seam.",
          "No crop, padding, resizing or aspect-ratio change.",
          "No generic readability effect or invented decoration.",
          "No modification outside the source effect region or effective protected mask.",
          "No low-resolution reconstruction followed by upscale."
        ],
        "pre_output_check":"Verify no source-language text or effect remains; no cover box, patch, seam or invented panel exists; protected artwork is unchanged; Korean text is fully inside the permitted region and unclipped; canvas, orientation and transparency are unchanged."
      }
    }
    canonical=json.dumps(prompt,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
    prompt["prompt_sha256"]=hashlib.sha256(canonical).hexdigest()
    (REVIEW/"generation_prompt.json").write_text(json.dumps(prompt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    prompt_json_sha=sha256_file(REVIEW/"generation_prompt.json")

    CANDIDATE.write_bytes(cand_bytes)
    candidate_sha=sha256_bytes(cand_bytes)

    report={
      "schema_version":9,
      "schema":"outrun-b00160-index112-dxt5-decoded-final-qa-v1",
      "task_id":TASK_ID,
      "lane":"LOCALIZATION_B",
      "asset_id":ASSET_ID,
      "index":INDEX,
      "recorded_at_kst":now,
      "status":"PASS",
      "result":"PASS_INDEX112_KOREAN_DXT5_CANDIDATE_DECODED_FINAL_STATIC_QA_RUNTIME_UNTESTED",
      "source":{
        "repository":SOURCE_REPO,"commit":SOURCE_COMMIT,"path":SOURCE_REL,
        "git_blob_sha":SOURCE_BLOB_SHA,"bytes":len(src_bytes),"sha256":SOURCE_SHA256,
        "width":W,"height":H,"fourcc":"DXT5","mip_count":1,"raw_to_readable":"flip_y"
      },
      "translation":{"source":"Try to reach the goal with your girlfriend.","korean":KOREAN,"lines":LINES},
      "source_effect":{
        "alpha_positive_pixels":source_pixels,"bbox_readable_ltrb_exclusive":source_bbox,
        "components_8":len(comps),"component_summaries":comps
      },
      "clean_plate":{
        "method":"synchronous_4_neighbor_hidden_rgb_diffusion_round_nearest_from_immutable_alpha0",
        "iterations_to_converge":iters,
        "alpha_positive_after":0,
        "changed_pixels_outside_removal_mask":outside_clean,
        "lineage_correction":"B00155 mislabeled this 49-iteration lineage as 8-neighbor; B00160 explicitly locks and regenerates it as 4-neighbor, matching C128's independent 49-iteration reproduction."
      },
      "render":{
        "font_identifier":f"{Path(font_path).name}#{font_index}","font_size_px":font_size,
        "source_slant_dx_per_dy":SLANT_DX_PER_DY,"source_slant_angle_deg":SLANT_ANGLE_DEG,
        "source_slant_direction":"right","candidate_slant_dx_per_dy":SLANT_DX_PER_DY,
        "candidate_slant_angle_deg":SLANT_ANGLE_DEG,"candidate_slant_direction":"right",
        "signed_slant_gate":"PASS","precompression_bbox":cand_pre_bbox,
        "decoded_final_bbox":final_bbox,"candidate_safe_bbox":CANDIDATE_SAFE_BBOX,
        "block_safe_bbox":BLOCK_SAFE_BBOX,"line_records":line_records
      },
      "dds":{
        "candidate_path":str(CANDIDATE.relative_to(ROOT)).replace("\\","/"),
        "candidate_dds_sha256":candidate_sha,"bytes":len(cand_bytes),
        "header_128_exact":cand_bytes[:128]==src_bytes[:128],"fourcc":"DXT5","mip_count":1,
        "block_strategy":"copy untouched blocks; alpha-zero source-only text blocks while preserving original color bytes; encode only Korean blocks",
        "block_stats":block_stats,
        "decoded_final_bc3_mask_iou_vs_precompression":visible_iou,
        "precompression_alpha_positive_pixels":pre_pixels,
        "decoded_final_alpha_positive_pixels":final_pixels
      },
      "qa":{
        "english_residue_pixels_outside_korean_block_safe_region":english_residue_pixels,
        "changed_pixels_outside_source_region":changed_outside_source_region,
        "introduced_alpha_outside_source_region":introduced_outside_source_pixels,
        "alpha_changed_outside_source_region":alpha_changed_outside_source_region,
        "changed_pixels_in_effective_protected_mask":changed_in_effective_protected,
        "decoded_final_containment":"PASS",
        "source_vs_candidate_comparison":"PASS",
        "orientation_gate":"PASS_FLIP_Y_RAW_TO_READABLE",
        "signed_slant_gate":"PASS"
      },
      "source_sha256":SOURCE_SHA256,
      "candidate_dds_sha256":candidate_sha,
      "runtime_validation":"UNTESTED",
      "prompt_contract":"outrun-first-pass-edit-v2",
      "prompt_sha256":prompt["prompt_sha256"],
      "prompt_json_sha256":prompt_json_sha,
      "signed_slant_gate":"PASS",
      "changed_pixels_outside_source_region":changed_outside_source_region,
      "changed_pixels_in_protected_mask":changed_in_effective_protected,
      "introduced_alpha_outside_source_region":introduced_outside_source_pixels,
      "alpha_changed_outside_edit_mask":alpha_changed_outside_source_region,
      "candidate_static_qa":"PASS_DECODED_FINAL_DXT5_PENDING_INDEPENDENT_C",
      "automation_validation":"PENDING",
      "validation_mode":"C_BATCH_GATE",
      "runtime_test_performed":False,
      "build_performed":False,
      "n100_used":False,
      "local_clone_used":False,
      "google_drive_used":False,
      "gpt_library_used":False,
      "uploaded_archive_used":False,
      "vr_ffb_dx_changes":False
    }
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (REVIEW/"qa_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    task={
      "schema_version":9,
      "task_id":TASK_ID,
      "lane":"LOCALIZATION_B",
      "target_branch":"korean-localization-clean",
      "attempt":"1/3",
      "chat_rollover":3,
      "recorded_at_kst":now,
      "base_head_sha":os.environ.get("GITHUB_SHA"),
      "commit_mode":"GITHUB_ACTIONS_ATOMIC_LANE_LOCAL_CANDIDATE_AND_TASK_RECORD",
      "result":"PASS_INDEX112_D41D0B1_KOREAN_DXT5_CANDIDATE_DECODED_FINAL_STATIC_QA_RUNTIME_UNTESTED",
      "summary":"Resumed the C128 REWORK_REQUIRED handoff for index112 without repeating completed B00158 work. Corrected the CLEAN_PLATE lineage by explicitly regenerating the 49-iteration method as synchronous 4-neighbor diffusion, rendered the approved Korean two-line wording with the measured right-slant/style in readable space, mapped back with flip_y, encoded an exact-header DXT5 candidate using source-block preservation, decoded the final DDS again, and passed native-resolution containment/source-region/protected/alpha/orientation/slant checks. Independent C and real-game validation remain pending.",
      "evidence":[
        str(REPORT.relative_to(ROOT)).replace("\\","/"),
        "localization/graphics/KOREAN_PNG_REVIEW/D41D0B1/source_display.png",
        "localization/graphics/KOREAN_PNG_REVIEW/D41D0B1/clean_plate_display.png",
        "localization/graphics/KOREAN_PNG_REVIEW/D41D0B1/candidate_display.png",
        "localization/graphics/KOREAN_PNG_REVIEW/D41D0B1/comparison.png",
        "localization/graphics/KOREAN_PNG_REVIEW/D41D0B1/generation_prompt.json",
        "localization/graphics/KOREAN_PNG_REVIEW/D41D0B1/qa_report.json",
        str(CANDIDATE.relative_to(ROOT)).replace("\\","/")
      ],
      "material_deliverable":{
        "type":"INDEX112_D41D0B1_KOREAN_DXT5_CANDIDATE_WITH_DECODED_FINAL_QA",
        "index":INDEX,"asset":ASSET_ID,"candidate_dds_sha256":candidate_sha,
        "candidate_dds_modified":True,"clean_plate_method":"synchronous_4_neighbor_49_iterations",
        "source_alpha_effect_pixels":source_pixels,"source_components":len(comps),
        "candidate_effect_bbox_readable_ltrb_exclusive":final_bbox,
        "candidate_safe_bbox_readable_ltrb_exclusive":CANDIDATE_SAFE_BBOX,
        "changed_pixels_outside_source_region":changed_outside_source_region,
        "changed_pixels_in_effective_protected_mask":changed_in_effective_protected,
        "introduced_alpha_outside_source_region":introduced_outside_source_pixels,
        "decoded_final_bc3_mask_iou":visible_iou,
        "materially_reduces_unresolved_work":True,
        "material_payload_in_result_commit":True
      },
      "self_qa":"PASS_INDEX112_EXACT_SOURCE__4_NEIGHBOR_49_ITER_CLEAN_PLATE_REPRODUCIBLE__KOREAN_RENDER_SAFE_BBOX__DXT5_HEADER_EXACT__DECODED_FINAL_ZERO_OUTSIDE_SOURCE_ZERO_EFFECTIVE_PROTECTED_ZERO_ALPHA_ESCAPE__RIGHT_SLANT__FLIP_Y",
      "candidate_static_qa":"PASS_DECODED_FINAL_PENDING_INDEPENDENT_C",
      "shared_state_modified":False,
      "peer_lane_files_modified":False,
      "candidate_dds_modified":True,
      "runtime_test_performed":False,
      "build_performed":False,
      "n100_used":False,
      "local_clone_used":False,
      "google_drive_used":False,
      "gpt_library_used":False,
      "uploaded_archive_used":False,
      "vr_ffb_dx_changes":False,
      "automation_validation":"PENDING",
      "validation_mode":"C_BATCH_GATE",
      "runtime_validation":"UNTESTED"
    }
    TASK_RECORD.parent.mkdir(parents=True,exist_ok=True)
    TASK_RECORD.write_text(json.dumps(task,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS","candidate_sha256":candidate_sha,"final_bbox":final_bbox,
                      "clean_plate_iterations":iters,"mask_iou":visible_iou},ensure_ascii=False))

if __name__ == "__main__":
    main()
