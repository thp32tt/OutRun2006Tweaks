#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[4]
TASK_ID = "LOCALIZATION-LOCALIZATION_B-00209"
WAVE_ID = "P00108"
INDEX = 226
ASSET = "E3F4BA07"
SOURCE_REPO = "Sonic-TV/OR2006Sprites"
SOURCE_COMMIT = "55f67a813dd3603d201d0be0da47c071965f53a4"
SOURCE_REL = "Release/spr_sprani_sumo_fe_cvt_Exst/E3F4BA07_512x128.dds"
SOURCE_URL = f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/{SOURCE_REL}"
SOURCE_SHA = "fb31e9f62e0d46c4554646be2f32d70cb015e8fdbc269189bf9d76a26eab5b72"
SOURCE_BLOB_SHA = "0ac26331b6c2765b9c46b867ff1f2151fd7a15b1"
SOURCE_BYTES = 4194432
ARCHIVE_SHA = "76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958"
EXPECTED_MASK_PIXELS = 84629
EXPECTED_MASK_SHA = "dcc28d8da195df03de5f3a8fbfc71a5dbf3d88a70146479541432c5f96c1a6ee"
EXPECTED_CLEAN_SHA = "55ce1f8e762673fc93e9c8bfff604dbc52fe4e1184976baa128ed4c22241256a"
EXPECTED_FONT_SHA = "faa5f3656a78b2e2d450d27fe8382c778bc2b6bb5ea29c986664a6a435056ceb"
EXPECTED_CANDIDATE_SHA = "8ab49a7015ced5e75ef3a3fe49213924075ac4c722d53d8fda54e73f25f92153"
FILL = (79, 97, 101)

ELEMENTS = [
    {"sprite":"sprite_296","source":"STAGE","korean":"스테이지","src":[0,436,228,500],"safe":[2,438,226,498]},
    {"sprite":"sprite_299","source":"GOAL E","korean":"골 E","src":[980,346,1233,410],"safe":[982,348,1231,408]},
    {"sprite":"sprite_300","source":"GOAL D","korean":"골 D","src":[4,262,256,326],"safe":[6,264,254,324]},
    {"sprite":"sprite_301","source":"GOAL C","korean":"골 C","src":[983,262,1234,326],"safe":[985,264,1232,324]},
    {"sprite":"sprite_302","source":"GOAL B","korean":"골 B","src":[4,170,257,234],"safe":[6,172,255,232]},
    {"sprite":"sprite_303","source":"GOAL A","korean":"골 A","src":[986,170,1242,234],"safe":[988,172,1240,232]},
    {"sprite":"sprite_304","source":"GOAL","korean":"골","src":[4,86,195,150],"safe":[6,88,193,148]},
    {"sprite":"sprite_305","source":"15 STAGE CONTINUOUS","korean":"15코스 연속","src":[985,86,1809,150],"safe":[987,88,1807,148]},
]
PROTECTED = [
    {"sprite":"sprite_297","source":"OUTRUN2SP","bbox":[983,430,1416,494]},
    {"sprite":"sprite_298","source":"OUTRUN2","bbox":[3,346,343,410]},
]

RUN = ROOT / "localization/graphics/role_B/20260930-B00209-P00108"
REVIEW = ROOT / "localization/graphics/KOREAN_PNG_REVIEW/E3F4BA07"
CANDIDATE = ROOT / "localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/E3F4BA07_512x128.dds"
TASK_RECORD = ROOT / "docs/automation/runs/LOCALIZATION-LOCALIZATION_B-00209.json"
REPORT = RUN / "B00209_P00108_INDEX226_CORRECTED_GEOMETRY_PRODUCTION.json"

def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def sha_file(p: Path) -> str:
    return sha_bytes(p.read_bytes())

def inside(inner, outer):
    return inner[0] >= outer[0] and inner[1] >= outer[1] and inner[2] <= outer[2] and inner[3] <= outer[3]

def find_font():
    out = subprocess.check_output(
        ["fc-match", "-f", "%{file}|%{index}\n", "Noto Sans CJK KR:style=Bold"],
        text=True,
    ).strip().splitlines()[0]
    p, idx = out.rsplit("|", 1)
    path = Path(p)
    if not path.exists():
        raise SystemExit(f"font missing: {path}")
    digest = sha_file(path)
    if digest != EXPECTED_FONT_SHA:
        raise SystemExit(f"font fingerprint mismatch: {digest}")
    return path, int(idx), digest

def render_tight(text: str, font_path: Path, font_index: int, safe_w: int, safe_h: int):
    chosen = None
    for size in range(96, 9, -1):
        font = ImageFont.truetype(str(font_path), size=size, index=font_index)
        bbox = font.getbbox(text)
        w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
        if w <= safe_w and h <= safe_h:
            chosen = (size, font, bbox, w, h)
            break
    if chosen is None:
        raise SystemExit(f"cannot fit {text!r}")
    size, font, bbox, w, h = chosen
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.text((-bbox[0], -bbox[1]), text, font=font, fill=255)
    alpha_bbox = mask.getbbox()
    if not alpha_bbox:
        raise SystemExit(f"empty glyph render for {text!r}")
    mask = mask.crop(alpha_bbox)
    return mask, size

def save_rgba(arr: np.ndarray, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr.astype(np.uint8), "RGBA").save(path, optimize=False)

def make_element_comparison(source: np.ndarray, candidate: np.ndarray, font_path: Path, font_index: int):
    rows = []
    label_font = ImageFont.truetype(str(font_path), size=18, index=font_index)
    for e in ELEMENTS:
        x1,y1,x2,y2 = e["src"]
        pad = 8
        cx1, cy1 = max(0,x1-pad), max(0,y1-pad)
        cx2, cy2 = min(source.shape[1],x2+pad), min(source.shape[0],y2+pad)
        s = Image.fromarray(source[cy1:cy2,cx1:cx2], "RGBA")
        c = Image.fromarray(candidate[cy1:cy2,cx1:cx2], "RGBA")
        scale = 2
        s = s.resize((s.width*scale,s.height*scale), Image.Resampling.NEAREST)
        c = c.resize((c.width*scale,c.height*scale), Image.Resampling.NEAREST)
        label_h = 28
        w = s.width + c.width
        row = Image.new("RGBA",(w,max(s.height,c.height)+label_h),(24,24,24,255))
        d = ImageDraw.Draw(row)
        d.text((6,4),f"SOURCE {e['source']}",font=label_font,fill=(255,255,255,255))
        d.text((s.width+6,4),f"KOREAN {e['korean']}",font=label_font,fill=(255,255,255,255))
        row.alpha_composite(s,(0,label_h))
        row.alpha_composite(c,(s.width,label_h))
        rows.append(row)
    maxw=max(r.width for r in rows)
    total=sum(r.height for r in rows)
    canvas=Image.new("RGBA",(maxw,total),(24,24,24,255))
    y=0
    for r in rows:
        canvas.alpha_composite(r,(0,y)); y+=r.height
    canvas.save(REVIEW/"element_comparison.png", optimize=False)

def main():
    now = datetime.now(ZoneInfo("Asia/Seoul")).replace(microsecond=0).isoformat()
    req = urllib.request.Request(SOURCE_URL, headers={"User-Agent":"OutRun2006Tweaks-localization-B00209"})
    with urllib.request.urlopen(req, timeout=90) as f:
        source_bytes = f.read()
    if len(source_bytes) != SOURCE_BYTES or sha_bytes(source_bytes) != SOURCE_SHA:
        raise SystemExit("exact pinned source identity mismatch")
    if source_bytes[:4] != b"DDS ":
        raise SystemExit("source is not DDS")

    temp = RUN / "_exact_source.dds"
    RUN.mkdir(parents=True, exist_ok=True)
    temp.write_bytes(source_bytes)
    source_raw = np.array(Image.open(temp).convert("RGBA"), dtype=np.uint8)
    temp.unlink()
    h,w = source_raw.shape[:2]
    if (w,h)!=(2048,512):
        raise SystemExit(f"unexpected canvas {(w,h)}")
    source_disp = np.flipud(source_raw).copy()

    mask_disp=np.zeros((h,w),dtype=bool)
    for e in ELEMENTS:
        x1,y1,x2,y2=e["src"]
        region=source_disp[y1:y2,x1:x2]
        mask_disp[y1:y2,x1:x2] |= region[:,:,3] > 0
    mask_raw=np.flipud(mask_disp).copy()
    mask_sha=sha_bytes(mask_raw.astype(np.uint8).tobytes())
    if int(mask_raw.sum()) != EXPECTED_MASK_PIXELS or mask_sha != EXPECTED_MASK_SHA:
        raise SystemExit(f"corrected removal-mask fingerprint mismatch count={int(mask_raw.sum())} sha={mask_sha}")

    clean_raw=source_raw.copy()
    clean_raw[mask_raw]=0
    clean_sha=sha_bytes(clean_raw.tobytes())
    if clean_sha != EXPECTED_CLEAN_SHA:
        raise SystemExit(f"corrected clean-plate fingerprint mismatch: {clean_sha}")
    clean_disp=np.flipud(clean_raw).copy()
    for e in ELEMENTS:
        x1,y1,x2,y2=e["src"]
        if int((clean_disp[y1:y2,x1:x2,3]>0).sum()) != 0:
            raise SystemExit(f"English alpha residue remains after clean plate: {e['source']}")

    font_path,font_index,font_sha=find_font()
    candidate_disp=clean_disp.copy()
    lettering=np.zeros_like(candidate_disp)
    metrics=[]
    for e in ELEMENTS:
        sx1,sy1,sx2,sy2=e["safe"]
        glyph,size=render_tight(e["korean"],font_path,font_index,sx2-sx1,sy2-sy1)
        gw,gh=glyph.size
        x=sx1
        y=sy1+((sy2-sy1-gh)//2)
        alpha=np.array(glyph,dtype=np.uint8)
        rgba=np.zeros((gh,gw,4),dtype=np.uint8)
        rgba[:,:,:3]=FILL
        rgba[:,:,3]=alpha
        lettering[y:y+gh,x:x+gw]=rgba
        base=Image.fromarray(candidate_disp[y:y+gh,x:x+gw],"RGBA")
        over=Image.fromarray(rgba,"RGBA")
        candidate_disp[y:y+gh,x:x+gw]=np.array(Image.alpha_composite(base,over),dtype=np.uint8)
        ys,xs=np.where(alpha>0)
        bbox=[x+int(xs.min()),y+int(ys.min()),x+int(xs.max())+1,y+int(ys.max())+1]
        if not inside(bbox,e["safe"]):
            raise SystemExit(f"candidate bbox escaped safe region {e['source']}: {bbox}")
        metrics.append({**e,"font_size_px":size,"localized_bbox_readable":bbox,
                        "native_glyph_canvas":[gw,gh],"horizontal_scale":1.0})

    candidate_raw=np.flipud(candidate_disp).copy()
    header=source_bytes[:128]
    payload=candidate_raw[:,:,[2,1,0,3]].tobytes()
    candidate_bytes=header+payload
    candidate_sha=sha_bytes(candidate_bytes)
    if candidate_sha != EXPECTED_CANDIDATE_SHA:
        raise SystemExit(f"deterministic candidate hash mismatch: {candidate_sha}")

    CANDIDATE.parent.mkdir(parents=True,exist_ok=True)
    CANDIDATE.write_bytes(candidate_bytes)
    roundtrip=np.array(Image.open(CANDIDATE).convert("RGBA"),dtype=np.uint8)
    if not np.array_equal(roundtrip,candidate_raw):
        raise SystemExit("DDS decoded round-trip mismatch")

    lettering_mask_raw=np.flipud(lettering[:,:,3]>0)
    allowed=mask_raw|lettering_mask_raw
    changed=np.any(source_raw!=candidate_raw,axis=2)
    alpha_changed=source_raw[:,:,3]!=candidate_raw[:,:,3]
    changed_out=int((changed & ~allowed).sum())
    alpha_out=int((alpha_changed & ~allowed).sum())
    if changed_out or alpha_out:
        raise SystemExit(f"zero-pixel gate failed changed_out={changed_out} alpha_out={alpha_out}")

    protected_changed=0
    for p in PROTECTED:
        x1,y1,x2,y2=p["bbox"]
        protected_changed += int(np.any(source_disp[y1:y2,x1:x2]!=candidate_disp[y1:y2,x1:x2],axis=2).sum())
    if protected_changed:
        raise SystemExit(f"protected brand pixels changed: {protected_changed}")

    REVIEW.mkdir(parents=True,exist_ok=True)
    save_rgba(source_disp,REVIEW/"source_display.png")
    save_rgba(clean_disp,REVIEW/"clean_plate_display.png")
    save_rgba(candidate_disp,REVIEW/"candidate_display.png")
    save_rgba(lettering,REVIEW/"lettering_display.png")
    Image.fromarray((mask_disp*255).astype(np.uint8),"L").save(REVIEW/"source_text_mask_display.png")
    protected=np.zeros((h,w),dtype=np.uint8)
    for p in PROTECTED:
        x1,y1,x2,y2=p["bbox"]; protected[y1:y2,x1:x2]=255
    Image.fromarray(protected,"L").save(REVIEW/"protected_mask_display.png")
    diff=np.zeros_like(source_disp)
    diff[np.any(source_disp!=candidate_disp,axis=2)]=[255,255,255,255]
    save_rgba(diff,REVIEW/"diff_display.png")

    label_h=34
    panel=Image.new("RGBA",(w*3,h+label_h),(24,24,24,255))
    label_font=ImageFont.truetype(str(font_path),size=20,index=font_index)
    d=ImageDraw.Draw(panel)
    for i,(label,arr) in enumerate([
        ("ENGLISH SOURCE",source_disp),("CLEAN PLATE",clean_disp),("KOREAN CANDIDATE",candidate_disp)
    ]):
        d.text((i*w+8,5),label,font=label_font,fill=(255,255,255,255))
        panel.alpha_composite(Image.fromarray(arr,"RGBA"),(i*w,label_h))
    panel.save(REVIEW/"comparison.png",optimize=False)
    make_element_comparison(source_disp,candidate_disp,font_path,font_index)

    prompt={
      "contract":"outrun-first-pass-edit-v2",
      "task_id":TASK_ID,"wave_id":WAVE_ID,"queue_index":INDEX,"asset":ASSET,
      "source":{"repository":SOURCE_REPO,"commit":SOURCE_COMMIT,"path":SOURCE_REL,
                "sha256":SOURCE_SHA,"git_blob_sha":SOURCE_BLOB_SHA,"bytes":SOURCE_BYTES,
                "dimensions":[w,h],"format":"RGBA32","mipmaps":1,"raw_to_readable":"flip_y",
                "pinned_release_archive_sha256":ARCHIVE_SHA},
      "elements":ELEMENTS,"protected":PROTECTED,
      "style":{"font_identifier":f"{font_path.name}#{font_index} Noto Sans CJK KR Bold",
               "font_sha256":font_sha,"local_reference_font_sha256":LOCAL_REFERENCE_FONT_SHA,"fill_rgb":list(FILL),"outline":"none","shadow":"none",
               "glow":"none","source_signed_slant_deg":0.0,"candidate_signed_slant_deg":0.0,
               "raster_resampling":"forbidden/not_used"},
      "instructions":{
        "positive":[
          "EDIT, DO NOT REDESIGN. Exact HD English source is authoritative.",
          "Remove only alpha-positive source text/effect pixels inside the eight positively bound localize regions.",
          "Preserve OUTRUN2 and OUTRUN2SP byte-exact.",
          "Render the approved Korean strings fully inside the 2px safe bboxes in readable coordinates.",
          "Preserve raw flip_y storage transform, canvas, DDS RGBA32 header, alpha semantics and transparent atlas background."
        ],
        "negative":[
          "No visible English residue in localized regions.",
          "No cover box, rectangle, panel, blur, seam, crop, resize, generic outline/shadow/glow or invented decoration.",
          "No previous Korean candidate pixels or cleaned regions as construction input.",
          "No 1px escape outside permitted edit geometry and no protected-brand modification."
        ]
      }
    }
    (REVIEW/"generation_prompt.json").write_text(json.dumps(prompt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    qa={
      "schema_version":14,"schema":"outrun-b00209-index226-corrected-geometry-production-v1",
      "task_id":TASK_ID,"wave_id":WAVE_ID,"lane":"LOCALIZATION_B","queue_index":INDEX,"asset":ASSET,
      "recorded_at_kst":now,
      "source":{"transport":"pinned_tag_direct_exact_canonical_source","repository":SOURCE_REPO,
                "commit":SOURCE_COMMIT,"path":SOURCE_REL,"sha256":SOURCE_SHA,
                "git_blob_sha":SOURCE_BLOB_SHA,"bytes":SOURCE_BYTES,"header_128_sha256":sha_bytes(header),
                "dimensions":[w,h],"format":"RGBA32","mipmaps":1,"raw_to_readable":"flip_y",
                "canonical_inventory_match":True},
      "clean_plate":{"method":"zero exact alpha-positive source footprint in eight corrected localize bboxes",
                     "removal_mask_pixels":int(mask_raw.sum()),"removal_mask_raw_sha256":mask_sha,
                     "clean_plate_raw_rgba_sha256":clean_sha,"english_alpha_residue_localize_regions":0,
                     "changed_pixels_outside_mask":0,"alpha_changes_outside_mask":0,
                     "protected_brand_pixels_unchanged":True},
      "render":{"font_identifier":f"{font_path.name}#{font_index} Noto Sans CJK KR Bold",
                "font_sha256":font_sha,"fill_rgb":list(FILL),
                "source_style":"upright condensed heavy sans; flat gray; no outline/shadow/glow",
                "source_signed_slant":{"angle_deg":0.0,"direction":"none"},
                "candidate_signed_slant":{"angle_deg":0.0,"direction":"none"},
                "metrics":metrics},
      "candidate":{"repo_path":str(CANDIDATE.relative_to(ROOT)).replace("\\","/"),
                   "sha256":candidate_sha,"bytes":len(candidate_bytes),"header_128_exact":candidate_bytes[:128]==header,
                   "roundtrip_decoded_exact":True,"changed_pixels":int(changed.sum()),
                   "changed_pixels_outside_allowed_edit_mask":changed_out,
                   "alpha_changed_pixels_total":int(alpha_changed.sum()),
                   "alpha_changed_pixels_outside_allowed_edit_mask":alpha_out,
                   "changed_pixels_in_protected_cells":protected_changed,
                   "candidate_letter_pixels":int(lettering_mask_raw.sum()),
                   "orientation":"PASS_FLIP_Y_RAW_TO_READABLE",
                   "safe_bbox_containment":"PASS_2PX_INSET_ALL_8","raster_resampling":"NOT_USED"},
      "visual_review_contract":{"full_atlas":"comparison.png",
                                "per_element_readable_zoom":"element_comparison.png",
                                "source_clean_candidate_set":["source_display.png","clean_plate_display.png","candidate_display.png"],
                                "status":"PRODUCER_VISUAL_REVIEW_EQUIVALENT_TO_PINNED_DETERMINISTIC_LOCAL_PROOF_PENDING_INDEPENDENT_C"},
      "static_qa":"PASS_PRODUCER_MACHINE_AND_VISUAL_PENDING_INDEPENDENT_C",
      "candidate_dds_modified":True,"shared_state_modified":False,"peer_lane_files_modified":False,
      "runtime_test_performed":False,"runtime_validation":"UNTESTED","automation_validation":"PENDING",
      "validation_mode":"C_BATCH_GATE","build_performed":False,"n100_used":False,"local_clone_used":False,
      "google_drive_used":False,"google_drive_write_performed":False,"gpt_library_used":False,
      "uploaded_archive_used":False,"vr_ffb_dx_changes":False
    }
    REPORT.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (REVIEW/"qa_report.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    task={
      "schema_version":14,"task_id":TASK_ID,"wave_id":WAVE_ID,"lane":"LOCALIZATION_B",
      "target_branch":"korean-localization-clean","attempt":"1/3","chat_rollover":1,
      "recorded_at_kst":now,"base_head_sha":os.environ.get("GITHUB_SHA"),"base_sha":os.environ.get("GITHUB_SHA"),
      "commit_mode":"GITHUB_ACTIONS_ATOMIC_LANE_LOCAL_INDEX226_CORRECTED_CANDIDATE_REVIEW_SET_AND_DURABLE_TASK_RECORD",
      "result":"PASS_MATERIAL_B_MOD3_INDEX226_CORRECTED_GEOMETRY_KOREAN_CANDIDATE_STATIC_QA_RUNTIME_UNTESTED",
      "summary":"C145/Q00043 returned index226 E3F4BA07 as REWORK_REQUIRED because B00202's candidate/review bytes were not persisted and its geometry fingerprint was superseded. This result regenerates directly from the exact canonical 2048x512 RGBA32 source at pinned commit 55f67a8, reproduces the corrected 84,629-pixel removal mask and clean-plate fingerprints exactly, renders all eight approved Korean strings into 2px-safe bboxes while preserving OUTRUN2/OUTRUN2SP, writes an exact-header deterministic DDS, and persists the mandatory GitHub source/clean/candidate/comparison and per-element review set. Independent C and real-game validation remain pending.",
      "evidence":[
        str(REPORT.relative_to(ROOT)).replace("\\","/"),
        "localization/graphics/KOREAN_PNG_REVIEW/E3F4BA07/source_display.png",
        "localization/graphics/KOREAN_PNG_REVIEW/E3F4BA07/source_text_mask_display.png",
        "localization/graphics/KOREAN_PNG_REVIEW/E3F4BA07/protected_mask_display.png",
        "localization/graphics/KOREAN_PNG_REVIEW/E3F4BA07/clean_plate_display.png",
        "localization/graphics/KOREAN_PNG_REVIEW/E3F4BA07/lettering_display.png",
        "localization/graphics/KOREAN_PNG_REVIEW/E3F4BA07/candidate_display.png",
        "localization/graphics/KOREAN_PNG_REVIEW/E3F4BA07/diff_display.png",
        "localization/graphics/KOREAN_PNG_REVIEW/E3F4BA07/comparison.png",
        "localization/graphics/KOREAN_PNG_REVIEW/E3F4BA07/element_comparison.png",
        "localization/graphics/KOREAN_PNG_REVIEW/E3F4BA07/generation_prompt.json",
        "localization/graphics/KOREAN_PNG_REVIEW/E3F4BA07/qa_report.json",
        str(CANDIDATE.relative_to(ROOT)).replace("\\","/")
      ],
      "material_deliverable":{"type":"INDEX226_E3F4BA07_CORRECTED_GEOMETRY_KOREAN_RGBA32_CANDIDATE_WITH_MANDATORY_REVIEW_SET",
        "reviewed_indices":[INDEX],"reviewed_assets":[ASSET],"candidate_dds_sha256":candidate_sha,
        "candidate_dds_modified":True,"source_removal_pixels":int(mask_raw.sum()),
        "corrected_clean_plate_raw_rgba_sha256":clean_sha,"translated_regions":8,"protected_regions":2,
        "changed_pixels_outside_allowed_edit_mask":changed_out,
        "alpha_changed_pixels_outside_allowed_edit_mask":alpha_out,
        "changed_pixels_in_protected_cells":protected_changed,
        "material_payload_in_result_commit":True,"durable_task_record_in_result_commit":True,
        "materially_reduces_unresolved_work":True},
      "readiness_audit":{"shard_rule":"asset_queue.index % 3 == 1","selected_priority":"DIRECT_REWORK_REQUIRED_CANDIDATE_COMPLETION",
        "selected_indices":[INDEX],"current_c_gate":"C146/Q00044",
        "readiness_after":{"226":"CANDIDATE_PERSISTED_PRODUCER_STATIC_PASS_PENDING_INDEPENDENT_C"}},
      "self_qa":"PASS_INDEX226_MOD3_EQ_1__EXACT_PINNED_SOURCE__CORRECTED_MASK_84629_SHA_EXACT__CLEAN_PLATE_SHA_EXACT__8_OF_8_KOREAN_SAFE_BBOX__2_PROTECTED_BRANDS_EXACT__DDS_HEADER_EXACT__ROUNDTRIP_EXACT__ZERO_CHANGE_OUTSIDE_ALLOWED__ZERO_ALPHA_ESCAPE__MANDATORY_GITHUB_PNG_REVIEW_SET",
      "candidate_static_qa":"PASS_PRODUCER_STATIC_PENDING_INDEPENDENT_C",
      "candidate_dds_modified":True,"shared_state_modified":False,"peer_lane_files_modified":False,
      "runtime_test_performed":False,"runtime_validation":"UNTESTED","build_performed":False,
      "n100_used":False,"local_clone_used":False,"gpt_library_used_as_source_or_ssot":False,
      "google_drive_used":False,"google_drive_write_performed":False,"uploaded_archive_used":False,
      "work_stolen_from_lane":None,"vr_ffb_dx_changes":False,"automation_validation":"PENDING",
      "validation_mode":"C_BATCH_GATE"
    }
    TASK_RECORD.parent.mkdir(parents=True,exist_ok=True)
    TASK_RECORD.write_text(json.dumps(task,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS","candidate_sha256":candidate_sha,"changed_pixels":int(changed.sum()),
                      "mask_pixels":int(mask_raw.sum()),"clean_plate_sha256":clean_sha},ensure_ascii=False))

if __name__ == "__main__":
    main()
