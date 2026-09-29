#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import struct
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "LOCALIZATION-LOCALIZATION_A-00173"
WAVE_ID = "P00086"
INDEX = 99
ASSET_ID = "4F68708E"
SOURCE_REPO = "envido32/OR2006Sprites"
SOURCE_COMMIT = "55f67a813dd3603d201d0be0da47c071965f53a4"
SOURCE_REL = "Release/spr_sprani_selector_cvt_Exst/4F68708E_512x64.dds"
SOURCE_URL = f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/{SOURCE_REL}"
SOURCE_BLOB_SHA = "eb8c2ddacf4075ff2c7c1dd7a025ca791008fbc8"
SOURCE_SHA256 = "d97206d8ab5e0898c81d9cc0d6562db1a381894b0fa3e2d9fa75303867a638e2"
W, H = 2048, 256
EXPECTED_BYTES = 128 + W * H

A00157_TASK = ROOT / "docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00157.json"
C131_TASK = ROOT / "docs/automation/runs/LOCALIZATION-LOCALIZATION_C-00169.json"
QUEUE = ROOT / "localization/graphics/asset_queue.csv"
RUN = ROOT / "localization/graphics/role_A/20260930-A00173-P00086"
REVIEW = ROOT / "localization/graphics/KOREAN_PNG_REVIEW/4F68708E/A00173"
REPORT = RUN / "A00173_P00086_INDEX99_TRANSPARENT_CLEAN_PLATE_V3.json"
MASK_RLE = RUN / "A00173_P00086_INDEX99_EFFECT_MASK_RLE.json"
TASK_RECORD = ROOT / "docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00173.json"

# C131 returned the prior rectangular reconstruction. These are source-space
# half-open line envelopes derived from the accepted threshold-18 line bboxes
# with the same six-pixel effect search allowance, but the edit mask below is
# pixel-shaped and can never become the whole rectangle.
LINE_BOXES = [
    (521, 46, 1608, 127),
    (536, 130, 1347, 215),
]
PANEL_ROI = (514, 39, 1614, 219)

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

def dds_info(b: bytes):
    if len(b) < 128 or b[:4] != b"DDS ":
        raise SystemExit("invalid DDS")
    return {
        "height": struct.unpack_from("<I", b, 12)[0],
        "width": struct.unpack_from("<I", b, 16)[0],
        "mips": struct.unpack_from("<I", b, 28)[0] or 1,
        "fourcc": b[84:88].decode("latin1"),
        "header": b[:128],
    }

def rgb565(v: int):
    return np.array([
        ((v >> 11) & 31) * 255 // 31,
        ((v >> 5) & 63) * 255 // 63,
        (v & 31) * 255 // 31,
    ], dtype=np.uint8)

def alpha_palette(a0: int, a1: int):
    if a0 > a1:
        return [
            a0, a1,
            int(round((6*a0 + a1)/7)), int(round((5*a0 + 2*a1)/7)),
            int(round((4*a0 + 3*a1)/7)), int(round((3*a0 + 4*a1)/7)),
            int(round((2*a0 + 5*a1)/7)), int(round((a0 + 6*a1)/7)),
        ]
    return [
        a0, a1,
        int(round((4*a0 + a1)/5)), int(round((3*a0 + 2*a1)/5)),
        int(round((2*a0 + 3*a1)/5)), int(round((a0 + 4*a1)/5)),
        0, 255,
    ]

def color_palette(c0: int, c1: int):
    p0 = rgb565(c0).astype(np.int32)
    p1 = rgb565(c1).astype(np.int32)
    p2 = np.rint((2.0*p0 + p1) / 3.0).astype(np.int32)
    p3 = np.rint((p0 + 2.0*p1) / 3.0).astype(np.int32)
    return np.stack([p0, p1, p2, p3], axis=0)

def decode_bc3(data: bytes):
    info = dds_info(data)
    if (info["width"], info["height"], info["mips"], info["fourcc"]) != (W, H, 1, "DXT5"):
        raise SystemExit(f"unexpected DDS metadata: {info}")
    payload = data[128:]
    if len(payload) != W * H:
        raise SystemExit(f"unexpected DXT5 payload bytes: {len(payload)}")
    out = np.zeros((H, W, 4), dtype=np.uint8)
    pos = 0
    for by in range(0, H, 4):
        for bx in range(0, W, 4):
            block = payload[pos:pos+16]
            pos += 16
            a0, a1 = block[0], block[1]
            ap = alpha_palette(a0, a1)
            abits = int.from_bytes(block[2:8], "little")
            c0, c1 = struct.unpack_from("<HH", block, 8)
            cp = color_palette(c0, c1)
            cbits = struct.unpack_from("<I", block, 12)[0]
            for py in range(4):
                for px in range(4):
                    i = py*4 + px
                    out[by+py, bx+px, :3] = cp[(cbits >> (2*i)) & 3]
                    out[by+py, bx+px, 3] = ap[(abits >> (3*i)) & 7]
    return out

def rect_mask(box):
    x0,y0,x1,y1 = box
    m = np.zeros((H,W), dtype=bool)
    m[y0:y1,x0:x1] = True
    return m

def disk_dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    out = np.zeros_like(mask)
    for dy in range(-radius, radius+1):
        for dx in range(-radius, radius+1):
            if dx*dx + dy*dy > radius*radius:
                continue
            sy0 = max(0, -dy); sy1 = min(H, H-dy)
            sx0 = max(0, -dx); sx1 = min(W, W-dx)
            dy0 = sy0 + dy; dy1 = sy1 + dy
            dx0 = sx0 + dx; dx1 = sx1 + dx
            out[dy0:dy1, dx0:dx1] |= mask[sy0:sy1, sx0:sx1]
    return out

def rec601(rgb: np.ndarray) -> np.ndarray:
    f = rgb.astype(np.float32)
    return 0.299*f[:,:,0] + 0.587*f[:,:,1] + 0.114*f[:,:,2]

def fit_background_plane(src: np.ndarray, sample: np.ndarray, box):
    y0, y1 = box[1], box[3]
    x0, x1 = box[0], box[2]
    ys, xs = np.nonzero(sample)
    if len(xs) < 1000:
        raise SystemExit(f"insufficient protected background samples: {len(xs)}")
    cx = (x0+x1-1)/2.0
    cy = (y0+y1-1)/2.0
    sx = max(1.0, (x1-x0-1)/2.0)
    sy = max(1.0, (y1-y0-1)/2.0)
    nx = (xs-cx)/sx
    ny = (ys-cy)/sy
    X = np.stack([np.ones_like(nx), nx, ny, nx*nx, ny*ny, nx*ny], axis=1)
    vals = src[ys,xs,:3].astype(np.float64)
    keep = np.ones(len(xs), dtype=bool)
    coeff = None
    for _ in range(5):
        coeff = np.linalg.lstsq(X[keep], vals[keep], rcond=None)[0]
        pred = X @ coeff
        resid = np.linalg.norm(vals-pred, axis=1)
        med = float(np.median(resid[keep]))
        mad = float(np.median(np.abs(resid[keep]-med))) + 1e-6
        cut = max(2.0, med + 3.5*1.4826*mad)
        new_keep = resid <= cut
        if int(new_keep.sum()) < 750 or np.array_equal(new_keep, keep):
            break
        keep = new_keep
    yy, xx = np.mgrid[y0:y1, x0:x1]
    gx = (xx-cx)/sx
    gy = (yy-cy)/sy
    G = np.stack([np.ones_like(gx),gx,gy,gx*gx,gy*gy,gx*gy], axis=-1)
    pred_box = np.tensordot(G, coeff, axes=([2],[0]))
    pred_box = np.clip(pred_box, 0, 255)
    sample_pred = X @ coeff
    sample_resid = np.linalg.norm(vals-sample_pred,axis=1)
    return pred_box, {
        "samples_total": int(len(xs)),
        "samples_robust_kept": int(keep.sum()),
        "sample_residual_median": float(np.median(sample_resid[keep])),
        "sample_residual_p995": float(np.quantile(sample_resid[keep],0.995)),
        "coefficients_rgb": coeff.tolist(),
    }

def mask_to_rle(mask: np.ndarray):
    runs=[]
    for y in range(H):
        row=mask[y]
        x=0
        while x<W:
            if not row[x]:
                x+=1
                continue
            x0=x
            x+=1
            while x<W and row[x]:
                x+=1
            runs.append([y,x0,x])
    return runs

def inpaint_harmonic(src: np.ndarray, mask: np.ndarray, init_rgb: np.ndarray):
    work = src[:,:,:3].astype(np.float32).copy()
    work[mask] = init_rgb[mask]
    visible = src[:,:,3] > 0
    for iteration in range(320):
        total = np.zeros_like(work)
        count = np.zeros((H,W), dtype=np.float32)

        v = np.zeros_like(visible); v[1:,:] = visible[:-1,:]
        total[1:,:,:] += work[:-1,:,:] * v[1:,:,None]
        count[1:,:] += v[1:,:]

        v = np.zeros_like(visible); v[:-1,:] = visible[1:,:]
        total[:-1,:,:] += work[1:,:,:] * v[:-1,:,None]
        count[:-1,:] += v[:-1,:]

        v = np.zeros_like(visible); v[:,1:] = visible[:,:-1]
        total[:,1:,:] += work[:,:-1,:] * v[:,1:,None]
        count[:,1:] += v[:,1:]

        v = np.zeros_like(visible); v[:,:-1] = visible[:,1:]
        total[:,:-1,:] += work[:,1:,:] * v[:,:-1,None]
        count[:,:-1] += v[:,:-1]

        upd = total / np.maximum(count[:,:,None],1.0)
        delta = float(np.max(np.abs(upd[mask]-work[mask]))) if np.any(mask) else 0.0
        work[mask] = upd[mask]
        if iteration >= 48 and delta < 0.025:
            return np.clip(np.rint(work),0,255).astype(np.uint8), iteration+1, delta
    return np.clip(np.rint(work),0,255).astype(np.uint8), 320, delta

def save_rgba(a: np.ndarray, p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(a, "RGBA").save(p, optimize=False)

def save_mask(mask: np.ndarray, p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)
    a=np.zeros((H,W,4),dtype=np.uint8)
    a[mask] = np.array([255,255,255,255],dtype=np.uint8)
    Image.fromarray(a,"RGBA").save(p,optimize=False)

def make_comparison(src_read: np.ndarray, clean_read: np.ndarray):
    label_h=26
    canvas=Image.new("RGBA",(W*2,H+label_h),(20,20,20,255))
    canvas.paste(Image.fromarray(src_read,"RGBA"),(0,label_h))
    canvas.paste(Image.fromarray(clean_read,"RGBA"),(W,label_h))
    d=ImageDraw.Draw(canvas)
    d.text((8,6),"ENGLISH SOURCE",fill=(255,255,255,255))
    d.text((W+8,6),"CLEAN PLATE V3",fill=(255,255,255,255))
    return canvas

def main():
    now=datetime.now(ZoneInfo("Asia/Seoul")).replace(microsecond=0).isoformat()
    base_head=git("rev-parse","HEAD")

    # Lane/parity and current C return are fail-closed inputs.
    with QUEUE.open("r",encoding="utf-8",newline="") as f:
        rows=list(csv.DictReader(f))
    qrow=next((r for r in rows if int(r["index"])==INDEX),None)
    if not qrow or INDEX % 2 != 1 or ASSET_ID not in qrow["path"]:
        raise SystemExit("A-shard queue identity/parity mismatch")

    ctask=json.loads(C131_TASK.read_text(encoding="utf-8"))
    cdisp=next((d for d in ctask.get("qa_dispositions",[]) if d.get("task_id")=="LOCALIZATION-LOCALIZATION_A-00164"),None)
    if not cdisp or cdisp.get("status")!="REWORK_REQUIRED":
        raise SystemExit("current C131 direct rework disposition not present")

    prior=json.loads(A00157_TASK.read_text(encoding="utf-8"))
    em=prior["embedded_material"]
    rm=em["removal_mask"]
    if int(rm["pixels"]) != 42774 or len(rm["rle_runs"]) != 3450:
        raise SystemExit("A00157 accepted threshold-mask fingerprint mismatch")

    req=urllib.request.Request(SOURCE_URL,headers={"User-Agent":"OutRun2006Tweaks-localization-A00173"})
    with urllib.request.urlopen(req,timeout=60) as f:
        source_bytes=f.read()
    if len(source_bytes)!=EXPECTED_BYTES or sha256_bytes(source_bytes)!=SOURCE_SHA256:
        raise SystemExit(f"canonical source identity mismatch bytes={len(source_bytes)} sha={sha256_bytes(source_bytes)}")
    info=dds_info(source_bytes)
    src=decode_bc3(source_bytes)

    seed=np.zeros((H,W),dtype=bool)
    for y,x0,x1 in rm["rle_runs"]:
        if not (0<=y<H and 0<=x0<x1<=W):
            raise SystemExit("invalid accepted seed RLE")
        seed[y,x0:x1]=True
    if int(seed.sum())!=42774:
        raise SystemExit("accepted seed materialization mismatch")

    alpha=src[:,:,3]
    lum=rec601(src[:,:,:3])
    line_union=np.zeros((H,W),dtype=bool)
    for b in LINE_BOXES:
        line_union |= rect_mask(b)
    if int((seed & ~line_union).sum()) != 0:
        raise SystemExit("accepted seed escaped line envelopes")

    final_mask=np.zeros((H,W),dtype=bool)
    prediction=np.zeros((H,W,3),dtype=np.float32)
    line_reports=[]
    for line_no,box in enumerate(LINE_BOXES,1):
        rect=rect_mask(box)
        line_seed=seed & rect
        near6=disk_dilate(line_seed,6) & rect
        near10=disk_dilate(line_seed,10) & rect
        near12=disk_dilate(line_seed,12) & rect

        # The accepted seed is luminance>=18. Protected source pixels outside
        # a twelve-pixel effect corridor form a robust local background prior.
        sample=rect & (alpha>0) & ~near12 & (lum<18.0)
        if int(sample.sum())<1000:
            sample=rect & (alpha>0) & ~near10 & ~line_seed
        pred_box,fit=fit_background_plane(src,sample,box)
        x0,y0,x1,y1=box
        prediction[y0:y1,x0:x1,:]=pred_box

        src_box=src[y0:y1,x0:x1,:3].astype(np.float32)
        residual=np.linalg.norm(src_box-pred_box.astype(np.float32),axis=2)
        pred_lum=0.299*pred_box[:,:,0]+0.587*pred_box[:,:,1]+0.114*pred_box[:,:,2]
        src_lum=lum[y0:y1,x0:x1]
        robust_thr=min(6.0,max(2.5,fit["sample_residual_p995"]+0.75))
        closure_local=(residual>=robust_thr) | (np.abs(src_lum-pred_lum)>=2.25)
        closure=np.zeros((H,W),dtype=bool)
        closure[y0:y1,x0:x1]=closure_local
        closure &= near10 & (alpha>0)

        mask_line=(near6 | closure) & rect & (alpha>0)
        final_mask |= mask_line
        line_reports.append({
            "line":line_no,
            "box_half_open":list(box),
            "accepted_seed_pixels":int(line_seed.sum()),
            "near6_visible_pixels":int((near6 & (alpha>0)).sum()),
            "model_residual_closure_pixels":int((closure & ~near6).sum()),
            "final_effect_pixels":int(mask_line.sum()),
            "robust_residual_threshold":float(robust_thr),
            "background_fit":fit,
        })

    if int((final_mask & (alpha==0)).sum()) != 0:
        raise SystemExit("source-transparent pixels entered effect mask")
    if int((seed & ~final_mask).sum()) != 0:
        raise SystemExit("accepted seed not fully included in effect mask")

    mask_pixels=int(final_mask.sum())
    if mask_pixels <= int(seed.sum()):
        raise SystemExit("rework mask failed to expand beyond rejected threshold seed")
    expanded_area=sum((x1-x0)*(y1-y0) for x0,y0,x1,y1 in LINE_BOXES)
    coverage=mask_pixels/expanded_area
    if coverage >= 0.88:
        raise SystemExit(f"effect mask became rectangle-like coverage={coverage:.4f}")

    # Initialize from the robust local model, then harmonic-inpaint only the
    # pixel-shaped true-effect mask. Alpha is immutable across the whole image.
    init=src[:,:,:3].astype(np.float32).copy()
    init[final_mask]=prediction[final_mask]
    inpaint_rgb,iters,last_delta=inpaint_harmonic(src,final_mask,init)
    clean=src.copy()
    clean[final_mask,:3]=inpaint_rgb[final_mask]
    clean[:,:,3]=src[:,:,3]

    changed=np.any(clean!=src,axis=2)
    changed_outside=int((changed & ~final_mask).sum())
    alpha_changed=int(np.count_nonzero(clean[:,:,3]!=src[:,:,3]))
    source_transparent_changed=int((changed & (src[:,:,3]==0)).sum())
    if changed_outside or alpha_changed or source_transparent_changed:
        raise SystemExit(f"containment/alpha failure outside={changed_outside} alpha={alpha_changed} transparent={source_transparent_changed}")

    runs=mask_to_rle(final_mask)
    full_width_rows=0
    max_run_fraction=0.0
    for y,x0,x1 in runs:
        width=None
        for bx0,by0,bx1,by1 in LINE_BOXES:
            if by0<=y<by1:
                width=bx1-bx0
                if x0<=bx0 and x1>=bx1:
                    full_width_rows+=1
                max_run_fraction=max(max_run_fraction,(x1-x0)/width)
    if full_width_rows != 0 or max_run_fraction >= 0.95:
        raise SystemExit(f"rectangle/no-box gate failed rows={full_width_rows} max_run_fraction={max_run_fraction:.4f}")

    # Self-supervised effect-removal metric: distance to the independently fit
    # local background is measured on the immutable accepted bright seed.
    reduction=[]
    for line_no,box in enumerate(LINE_BOXES,1):
        x0,y0,x1,y1=box
        line_seed=seed[y0:y1,x0:x1]
        pred=prediction[y0:y1,x0:x1]
        s=src[y0:y1,x0:x1,:3].astype(np.float32)
        c=clean[y0:y1,x0:x1,:3].astype(np.float32)
        before=np.linalg.norm(s-pred,axis=2)[line_seed]
        after=np.linalg.norm(c-pred,axis=2)[line_seed]
        record={
            "line":line_no,
            "seed_pixels":int(line_seed.sum()),
            "mean_distance_to_background_before":float(before.mean()),
            "mean_distance_to_background_after":float(after.mean()),
            "p95_after":float(np.quantile(after,0.95)),
            "reduction_ratio":float(after.mean()/max(before.mean(),1e-6)),
        }
        reduction.append(record)
        if record["reduction_ratio"] >= 0.70:
            raise SystemExit("clean-plate effect contrast reduction insufficient: "+json.dumps(record))

    RUN.mkdir(parents=True,exist_ok=True)
    REVIEW.mkdir(parents=True,exist_ok=True)
    save_rgba(src,REVIEW/"source_native.png")
    save_rgba(clean,REVIEW/"clean_plate_native.png")
    save_rgba(np.flipud(src).copy(),REVIEW/"source_readable.png")
    save_rgba(np.flipud(clean).copy(),REVIEW/"clean_plate_readable.png")
    save_mask(np.flipud(final_mask).copy(),REVIEW/"effect_mask_readable.png")
    make_comparison(np.flipud(src).copy(),np.flipud(clean).copy()).save(REVIEW/"comparison_readable.png",optimize=False)

    mask_doc={
        "schema":"outrun-schema9-index99-source-effect-mask-v3",
        "task_id":TASK_ID,
        "index":INDEX,
        "asset":ASSET_ID,
        "source_sha256":SOURCE_SHA256,
        "source_git_blob_sha":SOURCE_BLOB_SHA,
        "seed_authority":"A00157/C127 accepted threshold18 42774px seed",
        "mask_derivation":"disk-radius6 accepted-seed growth plus robust-local-background residual closure through radius10, intersect source alpha>0 and fixed line envelopes",
        "pixels":mask_pixels,
        "rle_encoding":"[y,x_start,x_end_exclusive]",
        "rle_runs":runs,
        "source_alpha_zero_pixels_in_mask":int((final_mask & (alpha==0)).sum()),
        "rectangle_gate":{"coverage_of_two_search_envelopes":coverage,"full_width_rows":full_width_rows,"max_run_fraction":max_run_fraction},
    }
    MASK_RLE.write_text(json.dumps(mask_doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    clean_raw_sha=sha256_bytes(clean.tobytes())
    report={
        "schema_version":9,
        "schema":"outrun-schema9-index99-transparent-cleanplate-v3",
        "task_id":TASK_ID,
        "wave_id":WAVE_ID,
        "lane":"LOCALIZATION_A",
        "role":"CONTINUOUS_PRODUCTION_LANE_A_SELF_QA",
        "target_branch":"korean-localization-clean",
        "recorded_at_kst":now,
        "base_head_sha":base_head,
        "selection":{
            "priority_tier":"DIRECT_C_REWORK_REQUIRED",
            "selected_index":INDEX,
            "selected_asset":ASSET_ID,
            "c_return_task":"LOCALIZATION-LOCALIZATION_C-00169",
            "c_batch":"Q00029",
            "c_disposition":"REWORK_REQUIRED",
            "failure_addressed":"A00164 opaque rectangular clean plate introduced alpha into 33373 source-transparent pixels and produced two dark-blue cover strips",
            "unrelated_preflight_deferred":True,
        },
        "source_lineage":{
            "repository":SOURCE_REPO,
            "pinned_commit":SOURCE_COMMIT,
            "path":SOURCE_REL,
            "git_blob_sha":SOURCE_BLOB_SHA,
            "bytes":len(source_bytes),
            "sha256":SOURCE_SHA256,
            "width":W,"height":H,"format":"DXT5_BC3","mip_count":1,
            "identity_authority":"REUSED_C127_Q00025_EXACT_CANONICAL_PASS_FINGERPRINT_AND_RECHECKED_BYTES_SHA_HEADER",
            "drive_exact_name_probe_this_invocation":"SOURCE_TRANSPORT_MISS",
            "fallback":"PINNED_UPSTREAM_DIRECT_FILE_AFTER_DRIVE_MISS",
        },
        "orientation":{"raw_to_readable":"mirror-Y","authority":"UNCHANGED_C127_ACCEPTED_LINEAGE"},
        "mask":{
            "accepted_seed_pixels":int(seed.sum()),
            "v3_effect_pixels":mask_pixels,
            "growth_pixels":mask_pixels-int(seed.sum()),
            "rle_runs":len(runs),
            "source_alpha_zero_pixels_in_mask":int((final_mask & (alpha==0)).sum()),
            "coverage_of_search_envelopes":coverage,
            "full_width_rows":full_width_rows,
            "max_run_fraction":max_run_fraction,
            "line_reports":line_reports,
            "artifact":str(MASK_RLE.relative_to(ROOT)).replace("\\","/"),
        },
        "clean_plate":{
            "algorithm":"SOURCE_ALPHA_IMMUTABLE_PIXEL_MASK_HARMONIC_RGB_INPAINT_WITH_ROBUST_LOCAL_BACKGROUND_INITIALIZATION",
            "decoded_rgba_sha256":clean_raw_sha,
            "source_decoded_rgba_sha256":sha256_bytes(src.tobytes()),
            "changed_pixels":int(changed.sum()),
            "changed_pixels_outside_effect_mask":changed_outside,
            "alpha_changed_pixels_global":alpha_changed,
            "source_transparent_pixels_changed":source_transparent_changed,
            "source_transparent_pixels_introduced_alpha":0,
            "hidden_rgb_changes_at_source_alpha_zero":0,
            "harmonic_iterations":iters,
            "harmonic_last_max_delta":last_delta,
            "seed_effect_contrast_reduction":reduction,
            "rectangle_or_opaque_strip_gate":"PASS_ZERO_FULL_WIDTH_ROWS_ALPHA_IMMUTABLE",
            "visual_acceptance":"HOLD_C_INDEPENDENT_NATIVE_READABLE_REVIEW_REQUIRED",
        },
        "layout":{
            "source":"Drive against the Ghost Car and challenge for the course record!!",
            "korean_full":"고스트 카와 달리며 코스 기록에 도전하세요!",
            "line1":"고스트 카와 달리며",
            "line2":"코스 기록에 도전하세요!",
        },
        "safe_fit_reused_as_nonfinal_measurement":{
            "line1_candidate_safe_bbox_ltrb":[529,54,1599,118],
            "line2_candidate_safe_bbox_ltrb":[544,138,1338,206],
            "safety_inset_px":2,
            "status":"MEASURED_PRIOR_ONLY_NOT_PROMOTED_UNTIL_C_ACCEPTS_V3_CLEAN_PLATE",
        },
        "self_qa":{
            "parity":"PASS_ODD_INDEX_99_ONLY",
            "source_identity":"PASS_RECHECKED_ACCEPTED_C127_FINGERPRINT",
            "accepted_seed_inclusion":"PASS_ZERO_OMITTED",
            "one_pixel_containment":"PASS_CHANGED_PIXELS_ONLY_INSIDE_PIXEL_EFFECT_MASK",
            "source_transparency":"PASS_ZERO_SOURCE_ALPHA_ZERO_CHANGES",
            "alpha_preservation":"PASS_ZERO_ALPHA_CHANGES_GLOBAL",
            "no_cover_rectangle":"PASS_ZERO_FULL_WIDTH_ROWS_MAX_RUN_FRACTION_LT_0_95",
            "protected_rgba_outside_mask":"PASS_EXACT",
            "source_effect_reduction":"PASS_LT_0_70_RATIO_BOTH_LINES",
            "candidate_false_promotion":"PASS_NONE",
            "runtime_test_performed":False,
            "runtime_validation":"UNTESTED",
        },
        "readiness_after":"DIRECT_REWORK_CLEAN_PLATE_V3_MATERIAL_READY_FOR_C_INDEPENDENT_NATIVE_VISUAL__NOT_RENDER_READY_BY_PRODUCER",
        "candidate_dds_modified":False,
        "candidate_static_qa":"HOLD_NO_NEW_V2_KOREAN_CANDIDATE__C131_REQUIRES_INDEPENDENT_CLEAN_PLATE_ACCEPTANCE_FIRST",
        "automation_validation":"PENDING",
        "validation_mode":"C_BATCH_GATE",
        "runtime_validation":"UNTESTED",
        "shared_state_modified":False,
        "peer_lane_files_modified":False,
        "runtime_test_performed":False,
        "build_performed":False,
        "n100_used":False,
        "local_clone_used":False,
        "google_drive_used":True,
        "google_drive_write_performed":False,
        "gpt_library_used":False,
        "uploaded_archive_used":False,
        "work_stolen_from_lane":None,
        "vr_ffb_dx_changes":False,
        "fingerprints":{
            "automation_contract_blob_sha":git("hash-object","docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md"),
            "controller_roles_blob_sha":git("hash-object","localization/controller_roles.json"),
            "queue_blob_sha":git("hash-object","localization/graphics/asset_queue.csv"),
            "a00157_task_blob_sha":git("hash-object","docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00157.json"),
            "c131_task_blob_sha":git("hash-object","docs/automation/runs/LOCALIZATION-LOCALIZATION_C-00169.json"),
            "source_git_blob_sha":SOURCE_BLOB_SHA,
            "source_sha256":SOURCE_SHA256,
        },
        "evidence":[
            str(MASK_RLE.relative_to(ROOT)).replace("\\","/"),
            str(REVIEW.relative_to(ROOT)/"source_native.png").replace("\\","/"),
            str(REVIEW.relative_to(ROOT)/"clean_plate_native.png").replace("\\","/"),
            str(REVIEW.relative_to(ROOT)/"source_readable.png").replace("\\","/"),
            str(REVIEW.relative_to(ROOT)/"clean_plate_readable.png").replace("\\","/"),
            str(REVIEW.relative_to(ROOT)/"effect_mask_readable.png").replace("\\","/"),
            str(REVIEW.relative_to(ROOT)/"comparison_readable.png").replace("\\","/"),
        ],
    }
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    task={
        "schema_version":9,
        "task_id":TASK_ID,
        "lane":"LOCALIZATION_A",
        "target_branch":"korean-localization-clean",
        "attempt":"1/3",
        "wave_id":WAVE_ID,
        "recorded_at_kst":now,
        "commit_mode":"GITHUB_ACTIONS_ATOMIC_LANE_LOCAL_MATERIAL_AND_TASK_RECORD",
        "base_head_sha":base_head,
        "result":"PASS_MATERIAL_DIRECT_REWORK_INDEX99_SOURCE_EFFECT_AWARE_TRANSPARENT_CLEAN_PLATE_V3_RUNTIME_UNTESTED",
        "summary":"C131/Q00029 directly returned odd index99/4F68708E because A00164 used two opaque rectangular clean-plate strips. This producer reuses and rechecks the unchanged C127 canonical DXT5 fingerprint, grows only the accepted 42,774-pixel source-effect seed in pixel topology, adds local-model residual closure, excludes every source-alpha-zero pixel, and harmonic-inpaints RGB while preserving source alpha globally. The clean plate therefore changes zero pixels outside the effect mask, changes zero source-transparent pixels and zero alpha values, and has no full-width rectangular mask rows. Latest C has not yet independently accepted this new plate, so producer does not self-promote it to RENDER_READY or emit a speculative Korean DXT5 candidate. No unrelated preflight, shared state, peer lane, runtime/build, N100/local clone, Library, or VR/FFB/DX work is performed.",
        "evidence":[str(REPORT.relative_to(ROOT)).replace("\\","/")]+report["evidence"],
        "material_deliverable":{
            "type":"INDEX99_SOURCE_EFFECT_AWARE_TRANSPARENT_CLEAN_PLATE_V3",
            "indices":[INDEX],"assets":[ASSET_ID],
            "source_git_blob_sha":SOURCE_BLOB_SHA,
            "source_sha256":SOURCE_SHA256,
            "accepted_seed_pixels":int(seed.sum()),
            "effect_mask_pixels":mask_pixels,
            "effect_mask_rle_runs":len(runs),
            "clean_plate_decoded_rgba_sha256":clean_raw_sha,
            "changed_pixels_outside_mask":changed_outside,
            "alpha_changed_pixels":alpha_changed,
            "source_transparent_pixels_changed":source_transparent_changed,
            "full_width_mask_rows":full_width_rows,
            "candidate_dds_modified":False,
            "materially_reduces_unresolved_work":True,
            "material_payload_in_result_commit":True,
            "report_path":str(REPORT.relative_to(ROOT)).replace("\\","/"),
        },
        "readiness_audit":{
            "selected_priority":"DIRECT_REWORK_REQUIRED",
            "selected_index":INDEX,
            "c_return_task":"LOCALIZATION-LOCALIZATION_C-00169",
            "c_disposition":"REWORK_REQUIRED",
            "explicit_render_ready_count_from_latest_C":0,
            "explicit_one_stage_to_render_count_from_latest_C":0,
            "unrelated_preflight_deferred":True,
            "readiness_before":"C131_REWORK_REQUIRED_OPAQUE_RECTANGULAR_CLEAN_PLATE",
            "readiness_after":"DIRECT_REWORK_CLEAN_PLATE_V3_READY_FOR_C_INDEPENDENT_NATIVE_VISUAL__NOT_RENDER_READY_BY_PRODUCER",
            "candidate_completion_rule":"CHECKED__LATEST_C_REQUIRES_INDEPENDENT_CLEAN_PLATE_ACCEPTANCE_BEFORE_RENDER__NO_FALSE_READY_PROMOTION",
        },
        "fingerprints":report["fingerprints"],
        "self_qa":"PASS_ODD_99_DIRECT_C_REWORK__PIXEL_EFFECT_MASK__SOURCE_ALPHA_ZERO_EXCLUDED__ZERO_ALPHA_CHANGE__ZERO_OUTSIDE_MASK_CHANGE__NO_FULL_WIDTH_MASK_ROWS__CONTRAST_REDUCED__NO_SHARED_STATE",
        "candidate_static_qa":"HOLD_NO_NEW_V2_KOREAN_CANDIDATE__V3_CLEAN_PLATE_PENDING_C_INDEPENDENT_NATIVE_VISUAL",
        "shared_state_modified":False,
        "peer_lane_files_modified":False,
        "candidate_dds_modified":False,
        "runtime_test_performed":False,
        "build_performed":False,
        "n100_used":False,
        "local_clone_used":False,
        "google_drive_used":True,
        "google_drive_write_performed":False,
        "gpt_library_used":False,
        "uploaded_archive_used":False,
        "work_stolen_from_lane":None,
        "vr_ffb_dx_changes":False,
        "automation_validation":"PENDING",
        "validation_mode":"C_BATCH_GATE",
        "runtime_validation":"UNTESTED",
    }
    TASK_RECORD.write_text(json.dumps(task,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":"PASS",
        "effect_mask_pixels":mask_pixels,
        "rle_runs":len(runs),
        "coverage":coverage,
        "alpha_changed":alpha_changed,
        "source_transparent_changed":source_transparent_changed,
        "changed_outside":changed_outside,
        "contrast_reduction":reduction,
        "clean_rgba_sha256":clean_raw_sha,
    },ensure_ascii=False))

if __name__ == "__main__":
    main()
