#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
from PIL import Image, ImageDraw, ImageFont

TASK_ID="LOCALIZATION-LOCALIZATION_A-00351"
WAVE_ID="P00221"
INDEX=222
ASSET="DDF0392A"
ROOT=Path(os.environ["REPO_ROOT"])
SRC=Path(os.environ["SOURCE_DDS"])
RUN=ROOT/"localization/graphics/role_A/20261001-A00351-P00221"
REVIEW=ROOT/"localization/graphics/KOREAN_PNG_REVIEW/DDF0392A"
CAND_REL="localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/DDF0392A_256x512.dds"
CAND=ROOT/CAND_REL
REPORT=RUN/"A00351_P00221_INDEX222_V19_SONG_TITLE_REWORK.json"
TASK=ROOT/"docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00351.json"
SOURCE_SHA="bcfad5a1a71ab66c841134b0f3f3aa8fa5571b806bd3945dabeca3722d18fb72"
ARCHIVE_SHA="76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958"
FONT_SHA="faa5f3656a78b2e2d450d27fe8382c778bc2b6bb5ea29c986664a6a435056ceb"
EXPECTED_CANDIDATE_SHA="e8dadfb5a976a9addafa08fe7a9dd1d94d4979ac387c496c98983e2d01e68b83"
W,H=1024,2048
LOCALIZED=[
 (0,"sprite_401","OutRun Mode / 15 C.","아웃런 모드 / 15코스",[0,1972,960,76],[6,14,548,66],[8,16,546,64],[46,53,57],45),
 (1,"sprite_402","OutRun 1986","아웃런 1986",[0,1896,960,76],[4,17,333,61],[6,19,331,59],[57,61,65],40),
 (2,"sprite_403","Journey Mode / Random","저니 모드 / 무작위",[0,1820,960,76],[2,10,627,68],[4,12,625,66],[46,53,57],50),
]
SONG_TITLES=[
 (3,"sprite_404","Who Are You?",[0,1744,960,76],[2,17,342,60]),
 (6,"sprite_407","Shake The Street",[0,1516,960,76],[3,17,419,60]),
 (7,"sprite_408","Rush A Difficulty",[0,1440,960,76],[6,17,421,70]),
]
MASK_SHA={
 0:"2ce842e4548201e2c50e088f709f14b5ac2a35e80ea8fbdb5f2784056858f1f7",
 1:"349ff963d0aebf0ae1fe6909cd4d9ce18d7909dde19be119220e81660c4a78d5",
 2:"b8f773f47536dfa3917eece034fed358323d2f15a87cbfbb09f34bade3bf4dbe",
}
def sha(b): return hashlib.sha256(b).hexdigest()
def fsha(p): return sha(Path(p).read_bytes())
def inside(a,b): return a[0]>=b[0] and a[1]>=b[1] and a[2]<=b[2] and a[3]<=b[3]
def githead(): return subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
def font_info():
    out=subprocess.check_output(["fc-match","-f","%{file}|%{index}\\n","Noto Sans CJK KR:style=Bold"],text=True).splitlines()[0]
    p,i=out.rsplit("|",1); p=Path(p)
    if fsha(p)!=FONT_SHA: raise SystemExit("font fingerprint mismatch")
    return p,int(i)
def save_rgba(a,p): p.parent.mkdir(parents=True,exist_ok=True); Image.fromarray(a.astype(np.uint8),"RGBA").save(p,optimize=False)
def dark(a):
    im=Image.fromarray(a.astype(np.uint8),"RGBA")
    bg=Image.new("RGBA",im.size,(28,28,28,255)); bg.alpha_composite(im); return bg

def main():
    now=datetime.now(ZoneInfo("Asia/Seoul")).replace(microsecond=0).isoformat()
    base=githead()
    sb=SRC.read_bytes()
    if len(sb)!=2097280 or sha(sb)!=SOURCE_SHA or sb[:4]!=b"DDS ": raise SystemExit("source identity mismatch")
    header=sb[:128]
    src=np.array(Image.open(SRC).convert("RGBA"),dtype=np.uint8)
    if src.shape!=(H,W,4): raise SystemExit(f"bad canvas {src.shape}")
    src_display=np.flipud(src).copy()
    fp,fi=font_info()
    clean=src.copy(); lettering=np.zeros_like(src); removal=np.zeros((H,W),bool); metrics=[]
    for idx,sprite,en,ko,rect,srcbb,safe,fill,expected_fs in LOCALIZED:
        x,yb,w,h=rect; y=H-(yb+h)
        disp=src[y:y+h,x:x+w][::-1].copy(); mask=disp[:,:,3]>0
        if sha(mask.astype(np.uint8).tobytes())!=MASK_SHA[idx]: raise SystemExit(f"mask mismatch {idx}")
        rawmask=mask[::-1]; removal[y:y+h,x:x+w]|=rawmask
        clean[y:y+h,x:x+w][rawmask]=[0,0,0,0]
        sx0,sy0,sx1,sy1=safe
        rx0,ry0,rx1,ry1=sx0+1,sy0+1,sx1-1,sy1-1
        rw,rh=rx1-rx0+1,ry1-ry0+1
        chosen=None
        for fs in range(12,90):
            f=ImageFont.truetype(str(fp),fs,index=fi); bb=f.getbbox(ko)
            tw,th=bb[2]-bb[0],bb[3]-bb[1]
            if tw<=rw and th<=rh: chosen=(fs,f,bb,tw,th)
        if not chosen: raise SystemExit(f"no fit {idx}")
        fs,f,bb,tw,th=chosen
        if fs!=expected_fs: raise SystemExit(f"font-size drift {idx}: {fs}")
        glyph=Image.new("RGBA",(tw+8,th+8),(0,0,0,0))
        d=ImageDraw.Draw(glyph)
        d.text((4-bb[0],4-bb[1]),ko,font=f,fill=tuple(fill)+(255,))
        glyph=glyph.crop(glyph.getbbox())
        px=rx0; py=ry0+(rh-glyph.height)//2
        layer=Image.new("RGBA",(960,76),(0,0,0,0)); layer.alpha_composite(glyph,(px,py))
        ab=layer.getbbox(); loc=[ab[0],ab[1],ab[2]-1,ab[3]-1]
        if not inside(loc,safe): raise SystemExit(f"preencode containment {idx}: {loc}")
        lr=np.array(layer)[::-1]
        lettering[y:y+h,x:x+w]=np.maximum(lettering[y:y+h,x:x+w],lr)
        metrics.append({
            "region_index":idx,"sprite":sprite,"source":en,"approved_korean":ko,
            "semantic_role":"LOCALIZE_UI_LABEL","atlas_rect_bl":rect,
            "source_effect_bbox_readable_local":srcbb,
            "candidate_safe_bbox_readable_local":safe,
            "render_box_readable_local":[rx0,ry0,rx1,ry1],
            "localized_bbox_readable_local_preencode":loc,
            "safe_margins_ltrb_preencode":[loc[0]-sx0,loc[1]-sy0,sx1-loc[2],sy1-loc[3]],
            "font_size_px":fs,
            "font_identifier":"NotoSansCJK-Bold.ttc#1 Noto Sans CJK KR Bold",
            "font_sha256":FONT_SHA,
            "candidate_fill_rgb":fill,
            "flattened_raster_resize":False,
            "containment_preencode":"PASS"
        })
    target=np.array(Image.alpha_composite(Image.fromarray(clean,"RGBA"),Image.fromarray(lettering,"RGBA")),dtype=np.uint8)
    RUN.mkdir(parents=True,exist_ok=True)
    tmpc=RUN/"_clean_tmp.dds"; tmpt=RUN/"_target_tmp.dds"
    Image.fromarray(clean,"RGBA").save(tmpc,format="DDS",pixel_format="DXT5")
    Image.fromarray(target,"RGBA").save(tmpt,format="DDS",pixel_format="DXT5")
    cb=tmpc.read_bytes(); tb=tmpt.read_bytes(); tmpc.unlink(); tmpt.unlink()
    bx=(W+3)//4; by=(H+3)//4; BLOCK=16
    clean_diff=np.any(clean!=src,axis=2); target_diff=np.any(target!=src,axis=2)
    def touched(diff):
        t=np.zeros((by,bx),bool); ys,xs=np.where(diff); t[ys//4,xs//4]=True; return t
    cbt=touched(clean_diff); tbt=touched(target_diff)
    cpay=bytearray(sb[128:]); tpay=bytearray(sb[128:])
    for yy,xx in zip(*np.where(cbt)):
        off=(yy*bx+xx)*BLOCK; cpay[off:off+BLOCK]=cb[128+off:128+off+BLOCK]
    for yy,xx in zip(*np.where(tbt)):
        off=(yy*bx+xx)*BLOCK; tpay[off:off+BLOCK]=tb[128+off:128+off+BLOCK]
    clean_dds=header+bytes(cpay); candidate=header+bytes(tpay)
    if sha(candidate)!=EXPECTED_CANDIDATE_SHA: raise SystemExit(f"candidate fingerprint drift {sha(candidate)}")
    rt=RUN/"_clean_roundtrip.dds"; rt.write_bytes(clean_dds)
    clean_dec=np.array(Image.open(rt).convert("RGBA"),dtype=np.uint8); rt.unlink()
    CAND.parent.mkdir(parents=True,exist_ok=True); CAND.write_bytes(candidate)
    cand=np.array(Image.open(CAND).convert("RGBA"),dtype=np.uint8)
    allowed=np.zeros((H,W),bool)
    for yy,xx in zip(*np.where(tbt)): allowed[yy*4:min(H,yy*4+4),xx*4:min(W,xx*4+4)]=True
    protected=np.ones((H,W),bool)
    for _,_,_,_,rect,_,_,_,_ in LOCALIZED:
        x,yb,w,h=rect; y=H-(yb+h); protected[y:y+h,x:x+w]=False
    changed=np.any(cand!=src,axis=2); ach=cand[:,:,3]!=src[:,:,3]
    if changed[~allowed].any() or ach[~allowed].any() or changed[protected].any():
        raise SystemExit("decoded zero-pixel/protected gate fail")
    for m,r in zip(metrics,LOCALIZED):
        idx,_,_,_,rect,_,safe,_,_=r; x,yb,w,h=rect; y=H-(yb+h)
        disp=cand[y:y+h,x:x+w][::-1]; ys,xs=np.where(disp[:,:,3]>0)
        bb=[int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())]
        m["localized_bbox_readable_local_decoded_final"]=bb
        m["safe_margins_ltrb_decoded_final"]=[bb[0]-safe[0],bb[1]-safe[1],safe[2]-bb[2],safe[3]-bb[3]]
        m["containment_decoded_final"]="PASS" if inside(bb,safe) else "FAIL"
        m["decoded_final_alpha_pixels"]=int((disp[:,:,3]>0).sum())
        if m["containment_decoded_final"]!="PASS": raise SystemExit(f"decoded containment {idx}")
        if int((clean_dec[y:y+h,x:x+w,3]>0).sum())!=0: raise SystemExit(f"clean alpha residue {idx}")
    title_metrics=[]
    for idx,sprite,title,rect,srcbb in SONG_TITLES:
        x,yb,w,h=rect; y=H-(yb+h)
        sreg=src[y:y+h,x:x+w]; creg=cand[y:y+h,x:x+w]
        if not np.array_equal(sreg,creg): raise SystemExit(f"song title changed {idx}")
        disp=sreg[::-1]; alpha=disp[:,:,3]>0
        yy,xx=np.where(alpha); rows=np.where(np.any(alpha,axis=1))[0]
        if int(rows.min())!=17: raise SystemExit(f"title top drift {idx}")
        desc=max(0,int(rows.max())-59)
        title_metrics.append({
            "region_index":idx,"sprite":sprite,"source_title":title,"canonical_output":title,
            "semantic_role":"SONG_TITLE_PRESERVE_ORIGINAL",
            "typography_family_id":"DDF0392A_SONG_TITLE_SOURCE_NATIVE_V19",
            "family_target_font_size_px":43,"actual_font_size_px":43,
            "font_size_measurement_basis":"SOURCE_NATIVE_COMMON_ALPHA_BODY_ROWS_17_TO_59_INCLUSIVE",
            "source_alpha_bbox_readable_local":[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())],
            "common_body_height_px":43,"descender_extension_px":desc,
            "source_pixels_preserved_exact":True,"candidate_pixels_equal_source":True,
            "artwork_effects_preserved_exact":True
        })
    if len({x["actual_font_size_px"] for x in title_metrics})!=1: raise SystemExit("title family nonuniform")
    REVIEW.mkdir(parents=True,exist_ok=True)
    cand_display=np.flipud(cand).copy(); clean_display=np.flipud(clean_dec).copy()
    letter_display=np.flipud(lettering).copy(); removal_display=np.flipud(removal).copy(); allowed_display=np.flipud(allowed).copy()
    save_rgba(src_display,REVIEW/"source_display.png")
    save_rgba(clean_display,REVIEW/"clean_plate_display.png")
    save_rgba(cand_display,REVIEW/"candidate_display.png")
    save_rgba(letter_display,REVIEW/"lettering_display.png")
    Image.fromarray((removal_display*255).astype(np.uint8),"L").save(REVIEW/"source_text_mask_display.png",optimize=False)
    Image.fromarray((~allowed_display*255).astype(np.uint8),"L").save(REVIEW/"protected_mask_display.png",optimize=False)
    diff=np.zeros_like(src_display); diff[np.any(src_display!=cand_display,axis=2)]=[255,255,255,255]
    save_rgba(diff,REVIEW/"diff_display.png")
    label=ImageFont.truetype(str(fp),20,index=fi)
    panel=Image.new("RGBA",(W*3,H+34),(24,24,24,255)); pd=ImageDraw.Draw(panel)
    for i,(name,a) in enumerate([("ENGLISH SOURCE",src_display),("CLEAN PLATE",clean_display),("CURRENT CANDIDATE",cand_display)]):
        pd.text((i*W+8,5),name,font=label,fill=(255,255,255,255)); panel.alpha_composite(Image.fromarray(a,"RGBA"),(i*W,34))
    panel.save(REVIEW/"comparison.png",optimize=False)
    rows=[]; lfont=ImageFont.truetype(str(fp),18,index=fi)
    for idx,sprite,en,ko,rect,srcbb,safe,fill,fs in LOCALIZED:
        x,yb,w,h=rect; x1,y1,x2,y2=srcbb; pad=8
        xa=max(0,x+x1-pad); ya=max(0,yb+y1-pad); xb=min(W,x+x2+pad+1); yb2=min(H,yb+y2+pad+1)
        s=dark(src_display[ya:yb2,xa:xb]).resize(((xb-xa)*2,(yb2-ya)*2),Image.Resampling.NEAREST)
        d=dark(cand_display[ya:yb2,xa:xb]).resize(((xb-xa)*2,(yb2-ya)*2),Image.Resampling.NEAREST)
        row=Image.new("RGBA",(s.width+d.width,max(s.height,d.height)+30),(20,20,20,255)); dr=ImageDraw.Draw(row)
        dr.text((6,4),f"SOURCE {en}",font=lfont,fill="white"); dr.text((s.width+6,4),f"KOREAN {ko}",font=lfont,fill="white")
        row.alpha_composite(s,(0,30)); row.alpha_composite(d,(s.width,30)); rows.append(row)
    for idx,sprite,title,rect,srcbb in SONG_TITLES:
        x,yb,w,h=rect; x1,y1,x2,y2=srcbb; pad=8
        xa=max(0,x+x1-pad); ya=max(0,yb+y1-pad); xb=min(W,x+x2+pad+1); yb2=min(H,yb+y2+pad+1)
        s=dark(src_display[ya:yb2,xa:xb]).resize(((xb-xa)*2,(yb2-ya)*2),Image.Resampling.NEAREST)
        d=dark(cand_display[ya:yb2,xa:xb]).resize(((xb-xa)*2,(yb2-ya)*2),Image.Resampling.NEAREST)
        row=Image.new("RGBA",(s.width+d.width,max(s.height,d.height)+30),(20,20,20,255)); dr=ImageDraw.Draw(row)
        dr.text((6,4),f"SOURCE SONG {title}",font=lfont,fill="white"); dr.text((s.width+6,4),f"PRESERVED {title}",font=lfont,fill="white")
        row.alpha_composite(s,(0,30)); row.alpha_composite(d,(s.width,30)); rows.append(row)
    ec=Image.new("RGBA",(max(r.width for r in rows),sum(r.height for r in rows)),(20,20,20,255)); yoff=0
    for r in rows: ec.alpha_composite(r,(0,yoff)); yoff+=r.height
    ec.save(REVIEW/"element_comparison.png",optimize=False)
    prompt={
      "contract":"outrun-first-pass-edit-v2","controller_schema_version":21,"task_id":TASK_ID,"wave_id":WAVE_ID,
      "queue_index":INDEX,"asset":ASSET,
      "source":{"archive":"OR2-HD-GUI-v0.25.10a.zip","archive_sha256":ARCHIVE_SHA,
                "member":"textures/load/spr_sprani_sumo_fe_cvt_Exst/DDF0392A_256x512.dds",
                "sha256":SOURCE_SHA,"dimensions":[W,H],"format":"DXT5","mipmaps":1,"raw_to_readable":"flip_y"},
      "localized_elements":[{"region_index":m["region_index"],"source":m["source"],"approved_korean":m["approved_korean"],
                             "candidate_safe_bbox_readable_local":m["candidate_safe_bbox_readable_local"],
                             "font_size_px":m["font_size_px"]} for m in metrics],
      "preserve_original_song_titles":title_metrics,
      "typography_family_policy":{"title_family":"DDF0392A_SONG_TITLE_SOURCE_NATIVE_V19",
                                  "family_target_font_size_px":43,
                                  "measurement_basis":"common source-native alpha body rows y=17..59; Rush A Difficulty has a glyph descender at y=60..69",
                                  "per_string_font_size_override":False,"source_title_pixels_preserved_exact":True},
      "instructions":[
        "EDIT, DO NOT REDESIGN. The exact supplied HD source is authoritative.",
        "Localize only OutRun Mode / 15 C., OutRun 1986, and Journey Mode / Random.",
        "Preserve Who Are You?, Shake The Street, and Rush A Difficulty exactly from source pixels; do not translate, transliterate, redraw, resize, recolor, or alter their effects.",
        "Treat the three song titles as one source-native typography family with a common 43px body size.",
        "Preserve every pixel outside the three localized source-text/effect masks.",
        "No cover rectangles, panels, blur, residue, clipping, scaling, padding, cropping, or flattened-raster resizing.",
        "Render Korean natively inside the accepted 2px-safe boxes in the measured source style.",
        "Keep DXT5 mip1 and the exact source 128-byte header; patch only touched BC3 blocks.",
        "Before producing the candidate, verify no source-language text remains in the three localized regions, protected song titles are exact source pixels, protected artwork is unchanged, Korean text is fully contained and unclipped, and canvas/orientation/transparency are unchanged. If not, do not produce a production candidate."
      ]
    }
    pb=(json.dumps(prompt,ensure_ascii=False,indent=2)+"\n").encode()
    (REVIEW/"generation_prompt.json").write_bytes(pb)
    qa={
      "schema_version":21,"schema":"outrun-a00351-index222-v19-song-title-source-restore-v1",
      "task_id":TASK_ID,"wave_id":WAVE_ID,"lane":"LOCALIZATION_A","queue_index":INDEX,"asset":ASSET,
      "recorded_at_kst":now,"base_head_sha":base,
      "source":{"transport":"pinned_release_exact_canonical_source","archive":"OR2-HD-GUI-v0.25.10a.zip",
                "archive_sha256":ARCHIVE_SHA,"member":"textures/load/spr_sprani_sumo_fe_cvt_Exst/DDF0392A_256x512.dds",
                "sha256":SOURCE_SHA,"bytes":len(sb),"header_128_sha256":sha(header),
                "dimensions":[W,H],"format":"DXT5","mipmaps":1,"raw_to_readable":"flip_y","canonical_inventory_match":True},
      "policy_rework":{"reason":"V20_RETROSPECTIVE_REWORK_TRANSLATED_SONG_TITLES",
                       "prior_candidate_sha256":"c2938974e9dbde92b05eab319f85e9dd226b7f89b037d24b67b463b312a92878",
                       "canonical_song_titles":["Who Are You?","Shake The Street","Rush A Difficulty"],
                       "title_family":"DDF0392A_SONG_TITLE_SOURCE_NATIVE_V19","family_target_font_size_px":43},
      "localized_render":{"contract":"outrun-first-pass-edit-v2",
                          "font_identifier":"NotoSansCJK-Bold.ttc#1 Noto Sans CJK KR Bold","font_sha256":FONT_SHA,
                          "metrics":metrics},
      "song_title_family":{"status":"PASS_SOURCE_NATIVE_EXACT_PRESERVATION_UNIFORM_FAMILY_BODY_SIZE",
                           "typography_family_id":"DDF0392A_SONG_TITLE_SOURCE_NATIVE_V19",
                           "family_target_font_size_px":43,
                           "font_size_measurement_basis":"SOURCE_NATIVE_COMMON_ALPHA_BODY_ROWS_17_TO_59_INCLUSIVE",
                           "members":title_metrics,"all_actual_font_sizes_equal":True,
                           "per_string_font_size_override":False,"candidate_song_title_pixels_equal_source":True},
      "clean_plate":{"removal_mask_pixels":int(removal.sum()),"changed_pixels_outside_removal_block_mask":0,
                     "alpha_changed_pixels_outside_removal_block_mask":0,"protected_regions_unchanged":True},
      "candidate":{"repo_path":CAND_REL,"sha256":sha(candidate),"bytes":len(candidate),
                   "header_128_exact":candidate[:128]==sb[:128],"format":"DXT5","mipmaps":1,
                   "changed_bc3_blocks":int(tbt.sum()),"total_bc3_blocks":int(bx*by),
                   "changed_pixels":int(changed.sum()),"changed_pixels_outside_allowed_edit_mask":int(changed[~allowed].sum()),
                   "alpha_changed_pixels_total":int(ach.sum()),"alpha_changed_pixels_outside_allowed_edit_mask":int(ach[~allowed].sum()),
                   "changed_pixels_in_protected_regions":int(changed[protected].sum()),
                   "decoded_raw_rgba_sha256":sha(cand.tobytes()),"decoded_display_rgba_sha256":sha(cand_display.tobytes()),
                   "orientation":"PASS_FLIP_Y_RAW_TO_READABLE","safe_bbox_containment":"PASS_2PX_INSET_ALL_3_LOCALIZED",
                   "one_pixel_overflow":0,"song_title_regions_changed_pixels":0,"raster_resampling":"NOT_USED"},
      "visual_review_contract":{"full_atlas":"comparison.png","per_element_readable_zoom":"element_comparison.png",
                                "source_clean_candidate_set":["source_display.png","clean_plate_display.png","candidate_display.png"],
                                "source_mask":"source_text_mask_display.png","protected_mask":"protected_mask_display.png",
                                "lettering":"lettering_display.png","diff":"diff_display.png",
                                "status":"PRODUCER_VISUAL_REVIEW_PASS_PENDING_INDEPENDENT_C",
                                "manual_review_findings":{"localized_source_english_residue":"NONE_OBSERVED",
                                                          "broken_hangul":"NONE_OBSERVED","clipping_or_overlap":"NONE_OBSERVED",
                                                          "protected_song_titles":"PASS_EXACT_SOURCE_PRESERVED",
                                                          "wrong_image_replacement":"NONE_OBSERVED","resolution_loss":"NONE_OBSERVED",
                                                          "raw_orientation":"PASS_VERTICAL_FLIP_MATCHES_SOURCE_STORAGE",
                                                          "style":"PASS_SOURCE_FAITHFUL"}},
      "static_qa":"PASS_PRODUCER_MACHINE_AND_VISUAL_PENDING_INDEPENDENT_C",
      "candidate_dds_modified":True,"shared_state_modified":False,"peer_lane_files_modified":False,
      "runtime_test_performed":False,"runtime_validation":"UNTESTED","automation_validation":"PENDING",
      "validation_mode":"C_BATCH_GATE","build_performed":False,"n100_used":False,"local_clone_used":False,
      "google_drive_used":False,"google_drive_write_performed":False,"gpt_library_used":False,
      "uploaded_archive_used":False,"pinned_release_used":True,"vr_ffb_dx_changes":False,
      "status":"PASS","asset_id":ASSET,"source_sha256":SOURCE_SHA,"candidate_dds_sha256":sha(candidate),
      "prompt_contract":"outrun-first-pass-edit-v2","prompt_sha256":sha(pb),"prompt_json_sha256":sha(pb),
      "signed_slant_gate":"PASS_SOURCE_NONE","changed_pixels_outside_edit_mask":0,
      "changed_pixels_in_protected_mask":0,"introduced_alpha_outside_source_region":0,"alpha_changed_outside_edit_mask":0
    }
    (REVIEW/"qa_report.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    report={
      "schema_version":21,"schema":"outrun-a00351-p00221-index222-v19-song-title-rework-v1",
      "task_id":TASK_ID,"wave_id":WAVE_ID,"lane":"LOCALIZATION_A","role":"CONTINUOUS_PRODUCTION_LANE_A_SELF_QA",
      "target_branch":"korean-localization-clean","attempt":"1/3","chat_rollover":4,"recorded_at_kst":now,
      "base_head_sha":base,
      "result":"PARTIAL_BATCH_PASS_MATERIAL_A_MOD3_INDEX222_V19_SONG_TITLE_SOURCE_RESTORE_V2_CANDIDATE_SELF_QA_RUNTIME_UNTESTED",
      "summary":"Direct REWORK_REQUIRED index222/DDF0392A repaired under v18/v19 naming and typography policy. Who Are You?, Shake The Street, and Rush A Difficulty are exact source pixels/artwork/effects again; all share the measured 43px source-native body y=17..59, with only the y descender extending below it. The remaining three UI labels retain canonical Korean rendering. Exact DXT5 mip1 header/orientation are preserved, only touched BC3 blocks are patched, localized 3/3 safe-bbox checks pass, and decoded-final changes outside allowed edit/protected/song-title regions are zero. Runtime remains UNTESTED.",
      "readiness_audit":{"shard_rule":"asset_queue.index % 3 == 0","selected_priority":"DIRECT_REWORK_REQUIRED_RUNNABLE",
                         "selected_index":222,"selected_asset":ASSET,"readiness_before":"V19_SONG_TITLE_REWORK_REQUIRED",
                         "readiness_after":"V19_REWORKED_V2_CANDIDATE_SELF_QA_PASS_PENDING_C_BATCH",
                         "candidate_attempted":True,"candidate_dds_modified":True,"batch_status":"PARTIAL_BATCH",
                         "partial_batch_reason":"Fresh A-shard completion-tier scan has no second already-runnable direct candidate: index51 is HOLD_STRICT_RECHECK measurement work, indices159/198/201 are candidate QA-pending, and unchanged source/dependency blockers are skipped."},
      "source":qa["source"],
      "generation":{"prompt_path":"localization/graphics/KOREAN_PNG_REVIEW/DDF0392A/generation_prompt.json",
                    "prompt_sha256":sha(pb),"title_family":"DDF0392A_SONG_TITLE_SOURCE_NATIVE_V19",
                    "family_target_font_size_px":43,"song_title_mode":"SOURCE_PIXELS_PRESERVED_EXACT",
                    "localized_font_identifier":"NotoSansCJK-Bold.ttc#1 Noto Sans CJK KR Bold",
                    "native_resolution_render":True,"flattened_raster_resize":False},
      "candidate":qa["candidate"],
      "self_qa":{"status":"PASS","qa_report":"localization/graphics/KOREAN_PNG_REVIEW/DDF0392A/qa_report.json",
                 "candidate_sha256":sha(candidate),"changed_pixels_outside_edit_mask":0,
                 "alpha_changed_outside_edit_mask":0,"changed_pixels_in_protected_mask":0,
                 "one_pixel_overflow_total":0,
                 "song_title_family_policy":"PASS_SOURCE_NATIVE_EXACT_PRESERVATION_UNIFORM_43PX_BODY",
                 "source_comparison_gate":"PASS_3_LOCALIZED_PLUS_3_PRESERVED_TITLES"},
      "review_set":{"base":"localization/graphics/KOREAN_PNG_REVIEW/DDF0392A",
                    "mandatory":["source_display.png","clean_plate_display.png","candidate_display.png","comparison.png","generation_prompt.json","qa_report.json"],
                    "additional":["element_comparison.png","source_text_mask_display.png","protected_mask_display.png","lettering_display.png","diff_display.png"]},
      "material_deliverable":{"type":"INDEX222_MATERIALLY_REWORKED_V2_DDS_WITH_SOURCE_PRESERVED_SONG_TITLES_AND_V19_FAMILY_EVIDENCE",
                              "candidate_dds_modified":True,"candidate_binary_persisted":True,"materially_reduces_unresolved_work":True},
      "shared_state_modified":False,"peer_lane_files_modified":False,"runtime_test_performed":False,
      "runtime_validation":"UNTESTED","build_performed":False,"n100_used":False,"local_clone_used":False,
      "gpt_library_used_as_source_or_ssot":False,"google_drive_used":False,"google_drive_write_performed":False,
      "uploaded_archive_used":False,"pinned_release_used":True,"work_stolen_from_lane":None,"vr_ffb_dx_changes":False,
      "automation_validation":"PENDING","validation_mode":"C_BATCH_GATE","result_sha":None,"authoritative_result_sha":None
    }
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    evidence=[
      "localization/graphics/role_A/20261001-A00351-P00221/A00351_P00221_INDEX222_V19_SONG_TITLE_REWORK.json",
      CAND_REL,
      "localization/graphics/KOREAN_PNG_REVIEW/DDF0392A/source_display.png",
      "localization/graphics/KOREAN_PNG_REVIEW/DDF0392A/clean_plate_display.png",
      "localization/graphics/KOREAN_PNG_REVIEW/DDF0392A/candidate_display.png",
      "localization/graphics/KOREAN_PNG_REVIEW/DDF0392A/comparison.png",
      "localization/graphics/KOREAN_PNG_REVIEW/DDF0392A/element_comparison.png",
      "localization/graphics/KOREAN_PNG_REVIEW/DDF0392A/generation_prompt.json",
      "localization/graphics/KOREAN_PNG_REVIEW/DDF0392A/qa_report.json",
      "localization/graphics/role_A/20261001-A00351-P00221/generate_index222_v19_song_title_rework.py"
    ]
    task={
      "schema_version":21,"task_id":TASK_ID,"wave_id":WAVE_ID,"lane":"LOCALIZATION_A",
      "target_branch":"korean-localization-clean","attempt":"1/3","chat_rollover":4,"recorded_at_kst":now,
      "base_head_sha":base,
      "commit_mode":"GITHUB_ACTIONS_ATOMIC_LANE_LOCAL_INDEX222_V19_SONG_TITLE_REWORK_CANDIDATE_REVIEW_SET_AND_DURABLE_TASK_RECORD",
      "result":"PARTIAL_BATCH_PASS_MATERIAL_A_MOD3_INDEX222_V19_SONG_TITLE_SOURCE_RESTORE_V2_CANDIDATE_STATIC_QA_RUNTIME_UNTESTED",
      "summary":report["summary"],"evidence":evidence,"material_deliverable":report["material_deliverable"],
      "readiness_audit":report["readiness_audit"],"self_qa":report["self_qa"],
      "candidate_static_qa":"PASS_PRODUCER_MACHINE_AND_VISUAL_PENDING_INDEPENDENT_C",
      "candidate_dds_modified":True,"shared_state_modified":False,"peer_lane_files_modified":False,
      "runtime_test_performed":False,"runtime_validation":"UNTESTED","build_performed":False,
      "n100_used":False,"local_clone_used":False,"gpt_library_used_as_source_or_ssot":False,
      "google_drive_used":False,"google_drive_write_performed":False,"uploaded_archive_used":False,"pinned_release_used":True,
      "work_stolen_from_lane":None,"vr_ffb_dx_changes":False,"automation_validation":"PENDING",
      "validation_mode":"C_BATCH_GATE","result_sha":None,"authoritative_result_sha":None
    }
    TASK.parent.mkdir(parents=True,exist_ok=True)
    TASK.write_text(json.dumps(task,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"candidate_sha256":sha(candidate),"changed_bc3_blocks":int(tbt.sum()),
                      "changed_pixels":int(changed.sum()),"alpha_changed_pixels":int(ach.sum()),
                      "removal_mask_pixels":int(removal.sum()),"song_title_regions_changed_pixels":0,
                      "prompt_sha256":sha(pb)},indent=2))

if __name__=="__main__":
    main()
