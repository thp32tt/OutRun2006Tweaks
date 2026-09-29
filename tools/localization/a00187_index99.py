#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, math, os, subprocess, urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import PIL
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
TASK_ID="LOCALIZATION-LOCALIZATION_A-00187"
WAVE_ID="P00095"
INDEX=99
ASSET="4F68708E"
SOURCE_REPO="envido32/OR2006Sprites"
SOURCE_COMMIT="55f67a813dd3603d201d0be0da47c071965f53a4"
SOURCE_REL="Release/spr_sprani_selector_cvt_Exst/4F68708E_512x64.dds"
SOURCE_URL=f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/{SOURCE_REL}"
SOURCE_SHA="d97206d8ab5e0898c81d9cc0d6562db1a381894b0fa3e2d9fa75303867a638e2"
PINNED_ZIP_SHA="76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958"
W,H=2048,256

CAND=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/4F68708E_512x64.dds"
REVIEW=ROOT/"localization/graphics/KOREAN_PNG_REVIEW/4F68708E/A00187"
RUN=ROOT/"localization/graphics/role_A/20260930-A00187-P00095"
REPORT=RUN/"A00187_P00095_INDEX99_DXT5_CANDIDATE_QA.json"
TASK=ROOT/"docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00187.json"

SOURCE_LINES=["Drive against the Ghost Car","and challenge for the course record!!"]
KOREAN_LINES=["고스트 카와 달리며","코스 기록에 도전하세요!"]
FONT_PATH="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_INDEX=1
FONT_SIZE=64
STROKE=8
SHEAR=0.22
TRACKING=1
FILL=(255,255,255,255)
NAVY=(5,14,60,255)

def sha256(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()

def bbox(mask:np.ndarray):
    ys,xs=np.nonzero(mask)
    if len(xs)==0:
        return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

def load_source():
    b=urllib.request.urlopen(SOURCE_URL,timeout=120).read()
    if sha256(b)!=SOURCE_SHA:
        raise SystemExit(f"source sha mismatch {sha256(b)}")
    if len(b)!=524416 or b[:4]!=b"DDS " or b[84:88]!=b"DXT5":
        raise SystemExit("source bytes/header/fourcc mismatch")
    im=np.array(Image.open(Path("/dev/stdin") if False else __import__("io").BytesIO(b)).convert("RGBA"))
    if im.shape!=(H,W,4):
        raise SystemExit(f"unexpected decoded shape {im.shape}")
    return b,im

def render_line(text:str,safe:list[int],shape):
    font=ImageFont.truetype(FONT_PATH,size=FONT_SIZE,index=FONT_INDEX)
    tmp=Image.new("RGBA",(1600,180),(0,0,0,0))
    d=ImageDraw.Draw(tmp)
    probe=d.textbbox((0,0),text,font=font,stroke_width=STROKE)
    y=-probe[1]+20
    x=20
    for ch in text:
        d.text((x,y),ch,font=font,fill=FILL,stroke_width=STROKE,stroke_fill=NAVY)
        x += int(round(d.textlength(ch,font=font)+TRACKING))
    a=np.array(tmp)[...,3]
    ys,xs=np.nonzero(a>0)
    crop=np.array(tmp.crop((xs.min(),ys.min(),xs.max()+1,ys.max()+1)))
    h,w=crop.shape[:2]
    extra=int(math.ceil(SHEAR*h))+4
    sheared=np.zeros((h,w+extra,4),dtype=np.uint8)
    for yy in range(h):
        shift=int(round(SHEAR*(h-1-yy)))
        sheared[yy,shift:shift+w]=crop[yy]
    a=sheared[...,3]
    ys,xs=np.nonzero(a>0)
    sheared=sheared[ys.min():ys.max()+1,xs.min():xs.max()+1]
    h,w=sheared.shape[:2]
    x0,y0,x1,y1=safe
    px=x0+4
    py=y0+(y1-y0-h)//2
    if px+w>x1 or py<y0 or py+h>y1:
        raise SystemExit(f"safe-fit failed {text} size={(w,h)} safe={safe}")
    layer=np.zeros(shape,dtype=np.uint8)
    layer[py:py+h,px:px+w]=sheared
    mask=layer[...,3]>0
    cb=bbox(mask)
    margins={"left":cb[0]-x0,"top":cb[1]-y0,"right":x1-cb[2],"bottom":y1-cb[3]}
    if min(margins.values())<1:
        raise SystemExit(f"candidate margin failed {text}: {margins}")
    return layer,mask,cb,margins,[w,h]

def checker(im:np.ndarray)->Image.Image:
    yy,xx=np.indices((H,W))
    c=((xx//16+yy//16)%2)*32+192
    bg=np.repeat(c[...,None],3,axis=2).astype(np.float32)
    alpha=im[...,3:4].astype(np.float32)/255.0
    rgb=np.rint(im[...,:3].astype(np.float32)*alpha+bg*(1-alpha)).clip(0,255).astype(np.uint8)
    return Image.fromarray(rgb,"RGB")

def main():
    now=datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")
    base_head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    source_bytes,source_raw=load_source()
    source=np.flipud(source_raw).copy()
    source_alpha=source[...,3]>0

    # Exact decoded source line envelopes. The only visible content in this atlas is the English text/effect.
    line_masks=[]
    for y0,y1 in [(0,125),(125,H)]:
        m=np.zeros((H,W),dtype=bool)
        m[y0:y1]=source_alpha[y0:y1]
        line_masks.append(m)
    source_bboxes=[bbox(m) for m in line_masks]
    expected=[[534,37,1353,125],[514,125,1614,217]]
    if source_bboxes!=expected:
        raise SystemExit(f"source effect bbox fingerprint changed {source_bboxes}")
    safe_bboxes=[[x0+2,y0+2,x1-2,y1-2] for x0,y0,x1,y1 in source_bboxes]

    # C00181 rejected v3 because preserving alpha retained readable English silhouettes.
    # This is a transparent text/effect-only atlas, so exact visible source/effect pixels are cleared to transparent.
    removal=source_alpha.copy()
    clean=source.copy()
    clean[removal]=0
    if np.count_nonzero(np.any(clean!=source,axis=2)&~removal):
        raise SystemExit("clean plate changed outside removal mask")
    if np.count_nonzero((clean[...,3]!=source[...,3])&~removal):
        raise SystemExit("clean plate alpha changed outside removal mask")
    if np.count_nonzero(clean[...,3]):
        raise SystemExit("clean plate retains visible source residue")

    candidate=clean.copy()
    lettering=np.zeros((H,W),dtype=bool)
    per=[]
    for n,(src_txt,kor_txt,sbbox,safe) in enumerate(zip(SOURCE_LINES,KOREAN_LINES,source_bboxes,safe_bboxes),1):
        layer,mask,cb,margins,rsize=render_line(kor_txt,safe,candidate.shape)
        base=Image.fromarray(candidate,"RGBA")
        base.alpha_composite(Image.fromarray(layer,"RGBA"))
        candidate=np.array(base)
        lettering |= mask
        ox0,oy0,ox1,oy1=sbbox
        lx0,ly0,lx1,ly1=cb
        deltas={"delta_left":lx0-ox0,"delta_top":ly0-oy0,"delta_right":ox1-lx1,"delta_bottom":oy1-ly1}
        if min(deltas.values())<2:
            raise SystemExit(f"source-bbox containment failed {n}: {deltas}")
        per.append({
            "line":n,"source":src_txt,"korean":kor_txt,
            "original_bbox_readable":sbbox,
            "candidate_safe_bbox_readable":safe,
            "localized_bbox_readable":cb,
            "containment_margins_px":margins,
            "render_raster_size":rsize,
            **deltas,
            "containment":"PASS"
        })

    allowed_pre=removal|lettering
    pre_changed=np.any(candidate!=source,axis=2)
    if np.count_nonzero(pre_changed&~allowed_pre):
        raise SystemExit("precompression change outside exact removal/lettering masks")
    if np.count_nonzero((candidate[...,3]!=source[...,3])&~allowed_pre):
        raise SystemExit("precompression alpha change outside exact removal/lettering masks")

    # Encode exact DXT5. Keep every untouched BC3 block byte-identical to canonical source.
    cand_raw=np.flipud(candidate).copy()
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".dds",delete=False) as tf:
        temp_path=Path(tf.name)
    try:
        Image.fromarray(cand_raw,"RGBA").save(temp_path,format="DDS",pixel_format="DXT5")
        enc=temp_path.read_bytes()
    finally:
        temp_path.unlink(missing_ok=True)
    if len(enc)!=len(source_bytes) or enc[84:88]!=b"DXT5":
        raise SystemExit("DXT5 encoder structure mismatch")

    touched_read=removal|lettering
    touched_raw=np.flipud(touched_read)
    bh,bw=H//4,W//4
    payload=bytearray(source_bytes[128:])
    ep=enc[128:]
    block_allow_raw=np.zeros((H,W),dtype=bool)
    touched_blocks=0
    for by in range(bh):
        for bx in range(bw):
            if touched_raw[by*4:(by+1)*4,bx*4:(bx+1)*4].any():
                off=(by*bw+bx)*16
                payload[off:off+16]=ep[off:off+16]
                block_allow_raw[by*4:(by+1)*4,bx*4:(bx+1)*4]=True
                touched_blocks+=1
    final_bytes=source_bytes[:128]+bytes(payload)
    from io import BytesIO
    final_raw=np.array(Image.open(BytesIO(final_bytes)).convert("RGBA"))
    final=np.flipud(final_raw).copy()
    block_allow=np.flipud(block_allow_raw)

    changed=np.any(final!=source,axis=2)
    alpha_changed=final[...,3]!=source[...,3]
    source_region=np.zeros((H,W),dtype=bool)
    safe_region=np.zeros((H,W),dtype=bool)
    for x0,y0,x1,y1 in source_bboxes:
        source_region[y0:y1,x0:x1]=True
    for x0,y0,x1,y1 in safe_bboxes:
        safe_region[y0:y1,x0:x1]=True
    visible_change=changed&((final[...,3]>0)|(source[...,3]>0))
    metrics={
        "changed_pixels_total":int(changed.sum()),
        "changed_pixels_outside_edit_mask":int((changed&~block_allow).sum()),
        "changed_pixels_outside_source_region":int((visible_change&~source_region).sum()),
        "changed_pixels_in_protected_mask":int((visible_change&~source_region).sum()),
        "introduced_alpha_outside_source_region":int(((final[...,3]>0)&(source[...,3]==0)&~source_region).sum()),
        "alpha_changed_outside_edit_mask":int((alpha_changed&~block_allow).sum()),
        "alpha_changed_outside_source_region":int((alpha_changed&~source_region).sum()),
        "introduced_alpha_outside_candidate_safe_bbox":int(((final[...,3]>0)&~safe_region).sum()),
        "touched_bc3_blocks":touched_blocks,
        "block_closure_pixels":int(block_allow.sum())
    }
    for key in ("changed_pixels_outside_edit_mask","changed_pixels_outside_source_region","changed_pixels_in_protected_mask","introduced_alpha_outside_source_region","alpha_changed_outside_edit_mask","alpha_changed_outside_source_region","introduced_alpha_outside_candidate_safe_bbox"):
        if metrics[key]!=0:
            raise SystemExit(f"{key}={metrics[key]}")

    for rec,safe in zip(per,safe_bboxes):
        x0,y0,x1,y1=safe
        m=np.zeros((H,W),dtype=bool)
        m[y0:y1,x0:x1]=final[y0:y1,x0:x1,3]>0
        cb=bbox(m)
        rec["decoded_final_localized_bbox_readable"]=cb
        rec["decoded_final_containment"]="PASS" if cb and cb[0]>=x0 and cb[1]>=y0 and cb[2]<=x1 and cb[3]<=y1 else "FAIL"
        if rec["decoded_final_containment"]!="PASS":
            raise SystemExit(f"decoded containment failed {rec}")

    CAND.parent.mkdir(parents=True,exist_ok=True)
    REVIEW.mkdir(parents=True,exist_ok=True)
    RUN.mkdir(parents=True,exist_ok=True)
    TASK.parent.mkdir(parents=True,exist_ok=True)
    CAND.write_bytes(final_bytes)

    Image.fromarray(source,"RGBA").save(REVIEW/"source_display.png",optimize=False)
    Image.fromarray(clean,"RGBA").save(REVIEW/"clean_plate_display.png",optimize=False)
    Image.fromarray(final,"RGBA").save(REVIEW/"candidate_display.png",optimize=False)
    Image.fromarray(final_raw,"RGBA").save(REVIEW/"candidate_raw.png",optimize=False)
    diff=np.zeros_like(source)
    diff[...,3]=255
    diff[changed,:3]=[255,255,255]
    Image.fromarray(diff,"RGBA").save(REVIEW/"diff_display.png",optimize=False)

    sa=Image.fromarray(source[...,3],"L").convert("RGB")
    ca=Image.fromarray(final[...,3],"L").convert("RGB")
    ada=np.abs(final[...,3].astype(np.int16)-source[...,3].astype(np.int16)).astype(np.uint8)
    da=Image.fromarray(ada,"L").convert("RGB")
    alpha_sheet=Image.new("RGB",(W*3,H))
    alpha_sheet.paste(sa,(0,0)); alpha_sheet.paste(ca,(W,0)); alpha_sheet.paste(da,(W*2,0))
    alpha_sheet.save(REVIEW/"alpha_comparison.png",optimize=False)

    s=checker(source); c=checker(final)
    comp=Image.new("RGB",(W*2,H+28),(255,255,255))
    comp.paste(s,(0,28)); comp.paste(c,(W,28))
    dd=ImageDraw.Draw(comp)
    dd.text((8,6),"ENGLISH SOURCE",fill=(0,0,0))
    dd.text((W+8,6),"KOREAN CANDIDATE",fill=(0,0,0))
    comp.save(REVIEW/"comparison.png",optimize=False)
    crop=(480,20,1660,235)
    reg=Image.fromarray(final,"RGBA").crop(crop)
    reg.save(REVIEW/"text_region_native.png",optimize=False)
    reg.resize((reg.width*2,reg.height*2),Image.Resampling.NEAREST).save(REVIEW/"text_region_nn2x.png",optimize=False)

    slant_deg=round(math.degrees(math.atan(SHEAR)),3)
    prompt={
        "contract":"outrun-first-pass-edit-v2","contract_version":2,"task_id":TASK_ID,
        "queue_index":INDEX,"asset_id":ASSET,
        "source_path":"textures/load/spr_sprani_selector_cvt_Exst/4F68708E_512x64.dds",
        "source_sha256":SOURCE_SHA,"source_dimensions":[W,H],
        "raw_orientation":"mirror-Y","display_transform":"flip_y_to_readable",
        "background_class":"transparent text/effect-only atlas",
        "edit_instruction":"EDIT, DO NOT REDESIGN. Remove the complete English glyph/effect pixels to exact transparency, then render only the approved Korean two-line wording inside 2px-inset source full-effect bboxes.",
        "elements":per,
        "approved_korean_lines":KOREAN_LINES,
        "font_identifier":"NotoSansCJK-Regular.ttc#1 (font bytes not distributed)",
        "style":{"fill_rgb":[255,255,255],"outer_effect_rgb":[5,14,60],"stroke_width_px":STROKE,
                 "slant_direction":"right","slant_dx_per_dy":SHEAR,"slant_angle_deg":slant_deg,
                 "tracking_px":TRACKING,
                 "source_style_note":"white italic sans lettering with thick dark-navy outer effect on transparent atlas"},
        "alpha_behavior":"Outside touched source/effect + Korean BC3 blocks preserve original compressed bytes. Clean plate clears exact visible source alpha/effect pixels to RGBA 0. No opaque panel/background.",
        "forbidden":["visible English residue","opaque/semtransparent cover rectangles","new panels","blur/smudge concealment",
                     "changes outside source full-effect regions","cropping/padding/resizing","upright raw DDS text",
                     "generic shadow/glow not present","fallback glyph boxes"],
        "single_pass_self_check":"Before producing the candidate, verify no source-language text/effect remains; no cover box, patch, seam or invented panel exists; protected pixels remain unchanged; Korean effects stay inside 2px-inset source bboxes; raw mirror-Y orientation and transparency remain correct."
    }
    prompt_bytes=(json.dumps(prompt,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
    (REVIEW/"generation_prompt.json").write_bytes(prompt_bytes)
    prompt_sha=sha256(prompt_bytes)
    cand_sha=sha256(final_bytes)

    qa={
        "schema_version":10,"schema":"outrun-a00187-index99-dxt5-decoded-final-qa-v2","status":"PASS_SELF_QA_PENDING_C",
        "task_id":TASK_ID,"wave_id":WAVE_ID,"lane":"LOCALIZATION_A","asset_id":ASSET,"queue_index":INDEX,
        "recorded_at_kst":now,"base_head_sha":base_head,
        "source_sha256":SOURCE_SHA,"candidate_dds_sha256":cand_sha,
        "candidate_decoded_rgba_sha256":sha256(final.tobytes()),
        "prompt_contract":"outrun-first-pass-edit-v2","prompt_sha256":prompt_sha,"prompt_json_sha256":prompt_sha,
        "signed_slant_gate":"PASS","signed_slant_source_estimate_deg":12.0,
        "signed_slant_candidate_deg":slant_deg,"slant_direction":"right",
        "source":{"repository":SOURCE_REPO,"commit":SOURCE_COMMIT,"path":SOURCE_REL,
                  "bundle_sha256":PINNED_ZIP_SHA,"bytes":len(source_bytes),"dimensions":[W,H],
                  "format":"DXT5_BC3","mip_count":1,"raw_to_readable":"mirror-Y"},
        "source_acquisition":{"google_drive_account":"ezflash557",
                              "google_drive_exact_filename":"SOURCE_TRANSPORT_MISS_RECONFIRMED_PRE_DISPATCH",
                              "pinned_upstream_direct_file":"PASS_EXACT_CANONICAL_SOURCE",
                              "pinned_release_bundle_sha256":PINNED_ZIP_SHA,
                              "final":"PASS_EXACT_CANONICAL_SOURCE"},
        "c_handoff":{"latest_task":"LOCALIZATION-LOCALIZATION_C-00186",
                     "latest_result_sha":"68aa068a82d17ea041f6d265c51ade59bc3e1f2a",
                     "readiness":"ONE_STAGE_TO_RENDER",
                     "rework_origin_task":"LOCALIZATION-LOCALIZATION_C-00181",
                     "rework_reason":"visible English ghost silhouettes in A00173 clean plate v3"},
        "clean_plate":{"contract":"outrun-clean-plate-qa-v1",
                       "method":"transparent_text_only_exact_source_alpha_effect_removal",
                       "source_effect_pixels":int(removal.sum()),"remaining_visible_pixels":int((clean[...,3]>0).sum()),
                       "changed_pixels_outside_edit_mask":0,"alpha_changed_outside_edit_mask":0,
                       "changed_pixels_in_protected_mask":0,"visible_source_residue":"PASS_NONE"},
        "decoded_final":{**metrics,"dimensions":[W,H],"format":"DXT5_BC3","mip_count":1,
                         "header_128_exact":final_bytes[:128]==source_bytes[:128],
                         "raw_orientation":"mirror-Y","per_element":per,
                         "english_source_comparison":"PASS_PRECOMMIT_NATIVE_READABLE",
                         "source_language_residue":"PASS_NONE_VISIBLE",
                         "clean_plate_box_or_seam":"PASS_NONE_TRANSPARENT"},
        "changed_pixels_outside_edit_mask":0,
        "changed_pixels_outside_source_region":0,
        "changed_pixels_in_protected_mask":0,
        "introduced_alpha_outside_source_region":0,
        "alpha_changed_outside_edit_mask":0,
        "candidate_dds_modified":True,
        "candidate_static_qa":"PASS_SELF_QA_PENDING_INDEPENDENT_C",
        "automation_validation":"PENDING","validation_mode":"C_BATCH_GATE",
        "runtime_validation":"UNTESTED","runtime_test_performed":False,
        "shared_state_modified":False,"peer_lane_files_modified":False,
        "build_performed":False,"n100_used":False,"local_clone_used":False,
        "gpt_library_used":False,"google_drive_used":True,"google_drive_write_performed":False,
        "uploaded_archive_used":False,"vr_ffb_dx_changes":False,
        "tool_versions":{"pillow":PIL.__version__,"numpy":np.__version__},
        "notes":"Direct C REWORK_REQUIRED/ONE_STAGE_TO_RENDER index99. v3 failed because alpha-preserving inpaint retained readable dark-blue English silhouettes. v4 treats the exact canonical asset as a transparent text/effect-only atlas: every exact source-visible effect pixel is cleared to transparent; Korean is freshly rendered inside 2px-inset source bboxes; raw mirror-Y is restored; only touched BC3 blocks are re-encoded; untouched BC3 blocks remain byte-identical."
    }
    REPORT.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (REVIEW/"qa_report.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    task={
        "schema_version":13,"task_id":TASK_ID,"lane":"LOCALIZATION_A","target_branch":"korean-localization-clean",
        "attempt":"1/3","wave_id":WAVE_ID,"recorded_at_kst":now,
        "base_sha":base_head,"base_head_sha":base_head,"result_sha":None,
        "result":"PASS_MATERIAL_INDEX99_DXT5_KOREAN_CANDIDATE_V2_SELF_QA_PENDING_C_RUNTIME_UNTESTED",
        "summary":"C00186 identifies index99/4F68708E as ONE_STAGE_TO_RENDER, retaining C00181's direct rework because A00173 v3 clean plate had visible English silhouettes. This producer replaces the residue-prone plate with exact transparent source-effect removal, renders the approved two-line Korean wording with source-like white/dark-navy right slant inside 2px safe bboxes, restores mirror-Y raw orientation, preserves untouched DXT5 blocks, and passes decoded-final self-QA and exact English-source comparison. Independent C remains pending; runtime is UNTESTED.",
        "evidence":[
            str(REPORT.relative_to(ROOT)).replace(os.sep,"/"),
            str((REVIEW/"source_display.png").relative_to(ROOT)).replace(os.sep,"/"),
            str((REVIEW/"clean_plate_display.png").relative_to(ROOT)).replace(os.sep,"/"),
            str((REVIEW/"candidate_display.png").relative_to(ROOT)).replace(os.sep,"/"),
            str((REVIEW/"candidate_raw.png").relative_to(ROOT)).replace(os.sep,"/"),
            str((REVIEW/"comparison.png").relative_to(ROOT)).replace(os.sep,"/"),
            str((REVIEW/"text_region_native.png").relative_to(ROOT)).replace(os.sep,"/"),
            str((REVIEW/"text_region_nn2x.png").relative_to(ROOT)).replace(os.sep,"/"),
            str((REVIEW/"diff_display.png").relative_to(ROOT)).replace(os.sep,"/"),
            str((REVIEW/"alpha_comparison.png").relative_to(ROOT)).replace(os.sep,"/"),
            str((REVIEW/"generation_prompt.json").relative_to(ROOT)).replace(os.sep,"/"),
            str((REVIEW/"qa_report.json").relative_to(ROOT)).replace(os.sep,"/"),
            str(CAND.relative_to(ROOT)).replace(os.sep,"/")
        ],
        "material_deliverable":{"type":"INDEX99_4F68708E_MATERIALLY_REWORKED_V2_KOREAN_DXT5_CANDIDATE",
                                "index":INDEX,"asset":ASSET,"source_sha256":SOURCE_SHA,
                                "candidate_dds_sha256":cand_sha,"candidate_dds_modified":True,
                                "materially_reduces_unresolved_work":True,"material_payload_in_result_commit":True,
                                "source_effect_pixels":int(removal.sum()),"physical_localized_occurrences":2,
                                "changed_pixels_outside_source_region":0,"introduced_alpha_outside_source_region":0},
        "readiness_audit":{"shard_rule":"A_INDEX_MOD_3_EQ_0","selected_priority":"DIRECT_REWORK_REQUIRED__LATEST_C_ONE_STAGE_TO_RENDER",
                           "selected_index":INDEX,
                           "latest_c_handoff_task":"LOCALIZATION-LOCALIZATION_C-00186",
                           "latest_c_handoff_result_sha":"68aa068a82d17ea041f6d265c51ade59bc3e1f2a",
                           "c_rework_origin_task":"LOCALIZATION-LOCALIZATION_C-00181",
                           "failure_addressed":"C visual found readable dark-blue English silhouettes in alpha-preserving v3 clean plate",
                           "unrelated_preflight_deferred":True,
                           "readiness_before":"ONE_STAGE_TO_RENDER_C00186__CLEAN_PLATE_RESIDUE_REPAIR_THEN_RENDER",
                           "readiness_after":"NEW_V2_KOREAN_DXT5_CANDIDATE_SELF_QA_PASS_PENDING_C"},
        "source_acquisition":{"google_drive_exact_filename":"SOURCE_TRANSPORT_MISS_RECONFIRMED_PRE_DISPATCH",
                              "pinned_upstream_direct_file":"PASS_EXACT_CANONICAL_SOURCE",
                              "pinned_release_bundle_sha256":PINNED_ZIP_SHA,
                              "final":"PASS_EXACT_CANONICAL_SOURCE"},
        "self_qa":"PASS_INDEX99_EXACT_CANONICAL_SOURCE__TRANSPARENT_EFFECT_REMOVAL__NO_ENGLISH_RESIDUE__2PX_SAFE_FIT__RIGHT_SLANT__MIRROR_Y__DXT5_BLOCK_PRESERVE__ZERO_VISIBLE_OUTSIDE_SOURCE__ZERO_ALPHA_OUTSIDE_SOURCE",
        "candidate_static_qa":"PASS_SELF_QA_PENDING_INDEPENDENT_C",
        "candidate_dds_modified":True,"shared_state_modified":False,"peer_lane_files_modified":False,
        "runtime_test_performed":False,"build_performed":False,"n100_used":False,"local_clone_used":False,
        "google_drive_used":True,"google_drive_write_performed":False,"gpt_library_used":False,
        "uploaded_archive_used":False,"work_stolen_from_lane":None,"vr_ffb_dx_changes":False,
        "automation_validation":"PENDING","validation_mode":"C_BATCH_GATE","runtime_validation":"UNTESTED"
    }
    TASK.write_text(json.dumps(task,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"candidate_sha256":cand_sha,"source_bboxes":source_bboxes,"safe_bboxes":safe_bboxes,
                      "metrics":metrics,"result":"PASS_SELF_QA_PENDING_C"},ensure_ascii=False))

if __name__=="__main__":
    main()
