#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, struct, subprocess, urllib.request
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
TASK_ID="LOCALIZATION-LOCALIZATION_B-00176"
WAVE_ID="P00088"
INDEX=130
ASSET="1762489B"
SOURCE_REPO="envido32/OR2006Sprites"
SOURCE_COMMIT="55f67a813dd3603d201d0be0da47c071965f53a4"
SOURCE_REL="Release/spr_sprani_sumo_fe_cvt_Exst/1762489B_512x128.dds"
SOURCE_URL=f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/{SOURCE_REL}"
SOURCE_GIT_BLOB="ce5158f8f3e78dc328227e4e76c7c71789b53060"
SOURCE_SHA="c64baefa65663bc247c33f2f7a72c4ea49990e2a0edb409f186b090dfd3460ac"
ZIP_SHA="76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958"
W,H=2048,512
CAND=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/1762489B_512x128.dds"
REVIEW=ROOT/"localization/graphics/KOREAN_PNG_REVIEW/1762489B"
RUN=ROOT/"localization/graphics/role_B/20260930-B00176-P00088"
REPORT=RUN/"B00176_P00088_INDEX130_RGBA32_CANDIDATE_QA.json"
TASK=ROOT/"docs/automation/runs/LOCALIZATION-LOCALIZATION_B-00176.json"

REGIONS=[
 {"sprite":"sprite_1080","raw_cell":[0,0,1264,96],"source":"OUTRUN2SP COURSE","korean":"아웃런2 SP 코스","fill":[79,97,101]},
 {"sprite":"sprite_1081","raw_cell":[0,96,1264,96],"source":"OUTRUN2 COURSE","korean":"아웃런2 코스","fill":[79,97,101]},
 {"sprite":"sprite_1082","raw_cell":[0,192,1264,96],"source":"MIX 2 COURSE","korean":"믹스 2 코스","fill":[79,97,101]},
 {"sprite":"sprite_1083","raw_cell":[0,288,1264,96],"source":"MIX 1 COURSE","korean":"믹스 1 코스","fill":[79,97,101]},
 {"sprite":"sprite_1084","raw_cell":[1264,0,600,64],"source":"AVERAGE RANK:","korean":"평균 랭크:","fill":[63,71,74],"align":"right"},
]
PRESERVE=[1864,0,128,56]

def sha256(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def bbox(mask):
    ys,xs=np.nonzero(mask)
    if len(xs)==0:return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def font_info():
    row=subprocess.check_output(["fc-match","-f","%{file}|%{index}\n","Noto Sans Mono CJK KR:style=Bold"],text=True).splitlines()[0]
    p,idx=row.rsplit("|",1)
    return p,int(idx)
def load_source():
    b=urllib.request.urlopen(SOURCE_URL,timeout=60).read()
    if sha256(b)!=SOURCE_SHA: raise SystemExit("source sha mismatch")
    if len(b)!=4194432 or b[:4]!=b"DDS ": raise SystemExit("source bytes/magic mismatch")
    width=struct.unpack_from("<I",b,16)[0]; height=struct.unpack_from("<I",b,12)[0]
    mips=struct.unpack_from("<I",b,28)[0] or 1
    fourcc=b[84:88]; rgbbits=struct.unpack_from("<I",b,88)[0]
    masks=struct.unpack_from("<IIII",b,92)
    if (width,height,mips,fourcc,rgbbits,masks)!=(2048,512,1,b"\0\0\0\0",32,(16711680,65280,255,4278190080)):
        raise SystemExit(f"unexpected DDS metadata {(width,height,mips,fourcc,rgbbits,masks)}")
    store=np.frombuffer(b[128:],dtype=np.uint8).reshape(H,W,4).copy()
    rgba=store[..., [2,1,0,3]].copy()
    return b,rgba
def save_rgba(a,p): Image.fromarray(a.astype(np.uint8),"RGBA").save(p,optimize=False)

def main():
    now=datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")
    base_head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    src_bytes,src=load_source()
    src_disp=np.flipud(src).copy()
    removal=np.zeros((H,W),bool)
    elems=[]
    for spec in REGIONS:
        x,y,w,h=spec["raw_cell"]; sub=src[y:y+h,x:x+w]
        full=np.any(sub!=0,axis=2)
        ys,xs=np.nonzero(full)
        if len(xs)==0: raise SystemExit(spec["sprite"]+" empty source")
        rb=[x+int(xs.min()),y+int(ys.min()),x+int(xs.max()+1),y+int(ys.max()+1)]
        db=[rb[0],H-rb[3],rb[2],H-rb[1]]
        removal[y:y+h,x:x+w]|=full
        elems.append({
          **spec,
          "source_effect_bbox_raw":rb,
          "source_effect_bbox_readable":db,
          "source_effect_pixels":int(full.sum()),
          "source_alpha_positive_pixels":int((sub[:,:,3]>0).sum()),
          "hidden_rgb_effect_pixels_at_alpha0":int((full&(sub[:,:,3]==0)).sum()),
        })
    clean=src.copy(); clean[removal]=0
    clean_changed=np.any(clean!=src,axis=2)
    if int((clean_changed&~removal).sum())!=0: raise SystemExit("clean changed outside removal")
    for e in elems:
        x,y,w,h=e["raw_cell"]
        if np.any(clean[y:y+h,x:x+w]!=0): raise SystemExit("clean localize cell residue")
    clean_disp=np.flipud(clean).copy()

    fp,fi=font_info()
    cand_disp=clean_disp.copy()
    lettering=np.zeros((H,W),bool)
    placements=[]
    for e in elems:
        sb=e["source_effect_bbox_readable"]
        safe=[sb[0]+2,sb[1]+2,sb[2]-2,sb[3]-2]
        if safe[2]<=safe[0] or safe[3]<=safe[1]: raise SystemExit("empty safe bbox")
        e["candidate_safe_bbox_readable"]=safe
        maxw,maxh=safe[2]-safe[0],safe[3]-safe[1]
        chosen=None
        for size in range(90,10,-1):
            font=ImageFont.truetype(fp,size=size,index=fi)
            d=ImageDraw.Draw(Image.new("L",(2000,200),0))
            bb=d.textbbox((0,0),e["korean"],font=font)
            tw,th=bb[2]-bb[0],bb[3]-bb[1]
            if tw<=maxw and th<=maxh:
                chosen=(font,size,bb,tw,th); break
        if chosen is None: raise SystemExit("cannot fit "+e["korean"])
        font,size,bb,tw,th=chosen
        xx=safe[2]-tw if e.get("align")=="right" else safe[0]
        yy=safe[1]+(maxh-th)//2
        m=Image.new("L",(tw,th),0); md=ImageDraw.Draw(m)
        md.text((-bb[0],-bb[1]),e["korean"],font=font,fill=255)
        ma=np.array(m,dtype=np.uint8); nz=ma>0
        sub=cand_disp[yy:yy+th,xx:xx+tw]
        sub[nz,0]=e["fill"][0]; sub[nz,1]=e["fill"][1]; sub[nz,2]=e["fill"][2]; sub[nz,3]=ma[nz]
        cand_disp[yy:yy+th,xx:xx+tw]=sub
        cur=np.zeros((H,W),bool); cur[yy:yy+th,xx:xx+tw]=nz
        lettering|=cur
        placements.append({"sprite":e["sprite"],"font_size_px":size,"text_bbox_readable":bbox(cur),"alignment":e.get("align","left")})

    cand=np.flipud(cand_disp).copy()
    lettering_raw=np.flipud(lettering).copy()
    allowed=removal.copy()
    per=[]
    for e,p in zip(elems,placements):
        x0,y0,x1,y1=e["candidate_safe_bbox_readable"]
        rr=[x0,H-y1,x1,H-y0]; e["candidate_safe_bbox_raw"]=rr
        allowed[rr[1]:rr[3],rr[0]:rr[2]]=True
        lm=lettering_raw[rr[1]:rr[3],rr[0]:rr[2]]
        lb=bbox(lm)
        if lb is None: raise SystemExit("empty Korean lettering")
        la=[rr[0]+lb[0],rr[1]+lb[1],rr[0]+lb[2],rr[1]+lb[3]]
        sb=e["source_effect_bbox_raw"]
        ok=la[0]>=rr[0] and la[1]>=rr[1] and la[2]<=rr[2] and la[3]<=rr[3]
        if not ok: raise SystemExit("containment fail "+e["sprite"])
        per.append({
          "sprite":e["sprite"],"source":e["source"],"korean":e["korean"],
          "source_effect_bbox_raw":sb,"source_effect_bbox_readable":e["source_effect_bbox_readable"],
          "source_effect_pixels":e["source_effect_pixels"],"source_alpha_positive_pixels":e["source_alpha_positive_pixels"],
          "hidden_rgb_effect_pixels_at_alpha0":e["hidden_rgb_effect_pixels_at_alpha0"],
          "candidate_safe_bbox_raw":rr,"candidate_safe_bbox_readable":e["candidate_safe_bbox_readable"],
          "localized_bbox_raw":la,"localized_bbox_readable":p["text_bbox_readable"],
          "delta_left":la[0]-sb[0],"delta_right":sb[2]-la[2],"delta_top":la[1]-sb[1],"delta_bottom":sb[3]-la[3],
          "containment":"PASS","font_size_px":p["font_size_px"],"alignment":p["alignment"],
        })

    store=cand[..., [2,1,0,3]].copy()
    cand_bytes=src_bytes[:128]+store.tobytes()
    changed=np.any(cand!=src,axis=2)
    outside=int((changed&~allowed).sum())
    alpha_changed=(cand[:,:,3]!=src[:,:,3])
    alpha_out=int((alpha_changed&~allowed).sum())
    px,py,pw,ph=PRESERVE
    preserve_exact=np.array_equal(cand[py:py+ph,px:px+pw],src[py:py+ph,px:px+pw])
    if outside or alpha_out or not preserve_exact or cand_bytes[:128]!=src_bytes[:128] or len(cand_bytes)!=len(src_bytes):
        raise SystemExit(f"final gate outside={outside} alpha_out={alpha_out} preserve={preserve_exact}")
    cand_sha=sha256(cand_bytes)
    clean_sha=sha256(clean.tobytes())

    CAND.parent.mkdir(parents=True,exist_ok=True); REVIEW.mkdir(parents=True,exist_ok=True); RUN.mkdir(parents=True,exist_ok=True); TASK.parent.mkdir(parents=True,exist_ok=True)
    CAND.write_bytes(cand_bytes)
    save_rgba(src_disp,REVIEW/"source_display.png")
    save_rgba(clean_disp,REVIEW/"clean_plate_display.png")
    save_rgba(cand_disp,REVIEW/"candidate_display.png")

    margin=34
    comp=Image.new("RGBA",(W*3,H+margin),(24,24,24,255))
    for i,a in enumerate([src_disp,clean_disp,cand_disp]): comp.paste(Image.fromarray(a,"RGBA"),(i*W,margin))
    d=ImageDraw.Draw(comp); lf=ImageFont.truetype(fp,size=22,index=fi)
    for i,t in enumerate(["ENGLISH SOURCE","CLEAN PLATE","KOREAN CANDIDATE"]): d.text((i*W+10,6),t,font=lf,fill=(255,255,255,255))
    comp.save(REVIEW/"comparison.png",optimize=False)

    vm=np.any(src_disp!=clean_disp,axis=2)|np.any(cand_disp!=clean_disp,axis=2)
    ys,xs=np.nonzero(vm); crop=[max(0,int(xs.min())-8),max(0,int(ys.min())-8),min(W,int(xs.max())+9),min(H,int(ys.max())+9)]
    x0,y0,x1,y1=crop
    native=Image.new("RGBA",((x1-x0)*2,y1-y0),(0,0,0,255))
    native.paste(Image.fromarray(src_disp[y0:y1,x0:x1],"RGBA"),(0,0)); native.paste(Image.fromarray(cand_disp[y0:y1,x0:x1],"RGBA"),(x1-x0,0))
    native.save(REVIEW/"text_region_native.png",optimize=False)
    native.resize((native.width*2,native.height*2),Image.Resampling.NEAREST).save(REVIEW/"text_region_nn2x.png",optimize=False)
    diff=np.abs(cand_disp.astype(np.int16)-src_disp.astype(np.int16)).astype(np.uint8); save_rgba(diff,REVIEW/"diff_display.png")
    ac=np.zeros((H,W*2,4),dtype=np.uint8)
    for i,a in enumerate([src_disp[:,:,3],cand_disp[:,:,3]]):
        ac[:,i*W:(i+1)*W,:3]=a[:,:,None]; ac[:,i*W:(i+1)*W,3]=255
    save_rgba(ac,REVIEW/"alpha_comparison.png")

    prompt={
      "schema":"outrun-first-pass-edit-v2","task_id":TASK_ID,"queue_index":INDEX,"asset":ASSET,
      "source_dimensions":[W,H],"raw_orientation":"flip_y_to_readable",
      "elements":[{"sprite":e["sprite"],"source":e["source"],"korean":e["korean"],"source_effect_bbox_readable":e["source_effect_bbox_readable"],"candidate_safe_bbox_readable":e["candidate_safe_bbox_readable"]} for e in elems],
      "protected_regions":[{"sprite":"sprite_1085","description":"numeric rank marker ???; preserve exact RGBA"}],
      "source_style":{"course_fill_rgb":[79,97,101],"average_fill_rgb":[63,71,74],"outline":"none","shadow":"none","glow":"none","slant_direction":"none","slant_angle_deg":0.0,"stroke_weight":"bold","width_character":"monospaced/condensed block sans"},
      "render":{"font_identifier":Path(fp).name+f"#{fi} Noto Sans Mono CJK KR Bold","alignment":"course left; average rank right","background":"transparent text-only; clear exact source full-effect footprint including alpha-zero hidden RGB fringe","safe_inset_px":2},
      "negative":["no source text or hidden RGB fringe","no cover rectangle","no neighboring sprite changes","no resize/crop","no invented outline/shadow/glow","no font fallback boxes"],
      "self_check":"Verify no source-language text/effect remains; protected numeric marker is unchanged; Korean is fully inside 2px safe regions and unclipped; canvas, orientation and transparency contract remain unchanged."
    }
    (REVIEW/"generation_prompt.json").write_text(json.dumps(prompt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    qa={
      "schema_version":9,"schema":"outrun-b00176-index130-rgba32-decoded-final-qa-v2",
      "task_id":TASK_ID,"wave_id":WAVE_ID,"lane":"LOCALIZATION_B","queue_index":INDEX,"asset":ASSET,"recorded_at_kst":now,"status":"PASS",
      "source":{"repository":SOURCE_REPO,"commit":SOURCE_COMMIT,"path":SOURCE_REL,"git_blob_sha":SOURCE_GIT_BLOB,"sha256":SOURCE_SHA,"bytes":len(src_bytes),"width":W,"height":H,"format":"RGBA32","mip_count":1,"raw_to_readable":"flip_y","canonical_inventory_match":True},
      "source_acquisition":{"drive_exact_filename_probe":"SOURCE_TRANSPORT_MISS","pinned_direct":"PASS_EXACT_CANONICAL_SOURCE","pinned_release_bundle_sha256":ZIP_SHA,"release_cache_crosscheck_performed_before_dispatch":True},
      "translation":[{"source":e["source"],"korean":e["korean"],"sprite":e["sprite"]} for e in elems],
      "source_removal_mask":{"method":"any nonzero RGBA inside C111/C113-accepted LOCALIZE cells; includes alpha-zero hidden RGB fringe; preserve sprite_1085","pixels":int(removal.sum()),"hidden_rgb_alpha0_pixels":int(sum(e["hidden_rgb_effect_pixels_at_alpha0"] for e in elems)),"clean_changed_outside_mask":0,"clean_plate_rgba_sha256":clean_sha,"clean_localize_cells_all_zero_rgba":True},
      "style":{"font_identifier":Path(fp).name+f"#{fi}","signed_slant_deg":0.0,"slant_direction":"none","course_fill_rgb":[79,97,101],"average_fill_rgb":[63,71,74],"outline_shadow_glow":"none"},
      "decoded_final":{"candidate_path":str(CAND.relative_to(ROOT)).replace("\\","/"),"candidate_sha256":cand_sha,"bytes":len(cand_bytes),"header_128_exact":True,"changed_pixels":int(changed.sum()),"changed_pixels_outside_allowed_region":outside,"alpha_changed_pixels_total":int(alpha_changed.sum()),"alpha_changed_pixels_outside_allowed":alpha_out,"protected_numeric_marker_exact":preserve_exact,"per_element":per,"orientation":"PASS_FLIP_Y_RAW_TO_READABLE","containment":"PASS_ZERO_CHANGE_OUTSIDE_REMOVAL_OR_SAFE_BBOX"},
      "comparison_evidence":[str((REVIEW/x).relative_to(ROOT)).replace("\\","/") for x in ["source_display.png","clean_plate_display.png","candidate_display.png","comparison.png","text_region_native.png","text_region_nn2x.png","diff_display.png","alpha_comparison.png"]],
      "visual_validation":"PENDING_EXACT_GITHUB_RESULT_VISUAL_REVIEW","candidate_static_qa":"PASS_MACHINE_DECODED_FINAL_PENDING_B_GITHUB_VISUAL_AND_INDEPENDENT_C",
      "automation_validation":"PENDING","validation_mode":"C_BATCH_GATE","runtime_validation":"UNTESTED","runtime_test_performed":False,
      "build_performed":False,"n100_used":False,"local_clone_used":False,"gpt_library_used":False,"google_drive_used":True,"google_drive_write_performed":False,"vr_ffb_dx_changes":False
    }
    REPORT.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (REVIEW/"qa_report.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    task={
      "schema_version":12,"task_id":TASK_ID,"lane":"LOCALIZATION_B","target_branch":"korean-localization-clean","attempt":"1/3","wave_id":WAVE_ID,"recorded_at_kst":now,
      "base_head_sha":base_head,"commit_mode":"GITHUB_ACTIONS_ATOMIC_LANE_LOCAL_INDEX130_CANDIDATE_AND_TASK_RECORD",
      "result":"PASS_MATERIAL_INDEX130_1762489B_RGBA32_KOREAN_CANDIDATE_MACHINE_QA_PENDING_C_RUNTIME_UNTESTED",
      "summary":"Fresh B-even candidate-completion scan skipped QA/runtime-pending assets and found no C-accepted runnable direct rework. During the single legal preflight batch, index130/1762489B resolved to an exact canonical v0.25.10a pinned source (SHA-256 c64baefa..., 2048x512 RGBA32), while C111/C113 already supplied accepted semantics/cell work-order lineage. This task therefore continued in the same invocation through source-effect removal, transparent CLEAN_PLATE, style/orientation measurement, 2px safe-fit Korean rendering, exact RGBA32 DDS write and decoded-final self-QA. Five localizable text elements are replaced; sprite_1085 numeric rank marker remains exact. Final machine QA has zero changed pixels outside the removal-or-safe region, zero alpha changes outside it, exact 128-byte header, exact dimensions/mips, flip_y readable orientation and per-element positive containment margins. Exact Git PNG visual review and independent C batch QA remain pending; runtime is UNTESTED.",
      "evidence":[str(REPORT.relative_to(ROOT)).replace("\\","/")]+qa["comparison_evidence"]+[str((REVIEW/"generation_prompt.json").relative_to(ROOT)).replace("\\","/"),str((REVIEW/"qa_report.json").relative_to(ROOT)).replace("\\","/"),str(CAND.relative_to(ROOT)).replace("\\","/")],
      "material_deliverable":{"type":"INDEX130_1762489B_NEW_V2_KOREAN_RGBA32_CANDIDATE","index":INDEX,"asset":ASSET,"source_sha256":SOURCE_SHA,"candidate_dds_sha256":cand_sha,"candidate_dds_modified":True,"localized_elements":5,"source_effect_removal_pixels":int(removal.sum()),"hidden_rgb_fringe_pixels_removed":int(sum(e["hidden_rgb_effect_pixels_at_alpha0"] for e in elems)),"changed_pixels_outside_allowed_region":outside,"alpha_changed_pixels_outside_allowed":alpha_out,"protected_numeric_marker_exact":preserve_exact,"materially_reduces_unresolved_work":True,"material_payload_in_result_commit":True},
      "readiness_audit":{"selected_priority":"ONE_STAGE_TO_RENDER_DISCOVERED_DURING_SINGLE_PREFLIGHT_BATCH","selected_index":INDEX,"readiness_before":"PREFLIGHT_ONLY_EXACT_CANONICAL_SOURCE_REQUIRED","source_acquisition_after":"PASS_EXACT_CANONICAL_SOURCE","c_accepted_lineage":["C111/Q00009 exact payload/cell mapping","C113/Q00011 v2 work-order"],"readiness_transition":"EXACT_SOURCE_FOUND -> ONE_STAGE_TO_RENDER -> CANDIDATE_COMPLETED_SAME_INVOCATION","unrelated_preflight_stopped_after_ready_discovery":True},
      "self_qa":"PASS_EVEN_INDEX130__EXACT_CANONICAL_SOURCE__FULL_RGBA_EFFECT_MASK_INCLUDING_HIDDEN_RGB__TRANSPARENT_CLEAN_PLATE__2PX_SAFE_BBOX__FIVE_KOREAN_ELEMENTS__ZERO_OUTSIDE_ALLOWED__ZERO_ALPHA_OUTSIDE_ALLOWED__HEADER_EXACT__NUMERIC_MARKER_EXACT__FLIP_Y",
      "candidate_static_qa":"PASS_MACHINE_DECODED_FINAL_PENDING_EXACT_GITHUB_VISUAL_AND_INDEPENDENT_C",
      "shared_state_modified":False,"peer_lane_files_modified":False,"candidate_dds_modified":True,"runtime_test_performed":False,"build_performed":False,"n100_used":False,"local_clone_used":False,"google_drive_used":True,"google_drive_write_performed":False,"gpt_library_used":False,"uploaded_archive_used":True,"uploaded_archive_role":"READ_ONLY_PINNED_V0.25.10A_DIGEST_CROSSCHECK_BEFORE_DISPATCH","work_stolen_from_lane":None,"vr_ffb_dx_changes":False,
      "automation_validation":"PENDING","validation_mode":"C_BATCH_GATE","runtime_validation":"UNTESTED"
    }
    TASK.write_text(json.dumps(task,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS","source_sha256":SOURCE_SHA,"candidate_sha256":cand_sha,"outside":outside,"alpha_outside":alpha_out,"preserve_exact":preserve_exact,"removal_pixels":int(removal.sum())},ensure_ascii=False))

if __name__=="__main__": main()
