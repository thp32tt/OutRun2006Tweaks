#!/usr/bin/env python3
"""C2 q154 independent RED-five persisted-DDS/source/authored-clean review evidence.
Evidence-only worker. Never write an approval or touch candidate bytes.
"""
from pathlib import Path
from io import BytesIO
import hashlib, json, os, subprocess, urllib.request
import numpy as np
from PIL import Image, ImageDraw

assert os.getenv("OUTRUN_CPU_WORKER") == "github-actions"
assert os.getenv("OUTRUN_CPU_ROLE") == "C"
R=Path(".")
O=R/"localization/graphics/role_C/20261008-C292-C2-Q154-RED-FIVE-INDEPENDENT"
O.mkdir(parents=True,exist_ok=True)
triage_run=subprocess.run(["python","tools/localization/rework_triage.py","--index","154"],
                         text=True,capture_output=True,check=True)
triage_info=json.loads(triage_run.stdout)
assert len(triage_info["assets"])==1, triage_info
assert triage_info["assets"][0]["next_action"]=="EVIDENCE_ONLY_HOLD",triage_info
(O/"C292_TRIAGE.json").write_text(json.dumps(triage_info,ensure_ascii=False,indent=2)+"\n")

source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"
with urllib.request.urlopen(source_url,timeout=180) as f: source_bytes=f.read()
candidate_path=R/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"
candidate_bytes=candidate_path.read_bytes()
clean_path=R/"localization/graphics/role_B/20261005-B-PRODUCTION60/4D38_HD_CLEAN_PLATE.png"
historical_independent_clean=R/"localization/graphics/role_C/20261005-C141-4D38BBB0/C141_EXACT_CLEAN_PLATE.png"
H=lambda b:hashlib.sha256(b).hexdigest()
source_sha="15a10e6b44ca5f1267fdf24eebbe902bb18a77b3903896370e183fea8a401bcf"
candidate_sha="94678124f6cddaeb44520c6419f4b475d1452866c052ff301a4859dddf38cb1f"
clean_sha="a4d707fa4376a7db4cc04fd1de51d9dc23b1874eac9a8b4988dc44c7f4c23380"
assert H(source_bytes)==source_sha, "source changed"
assert H(candidate_bytes)==candidate_sha, "candidate changed"
assert H(clean_path.read_bytes())==clean_sha, "authored clean changed"
assert H(historical_independent_clean.read_bytes())==clean_sha, "independent clean changed"
assert source_bytes[:128]==candidate_bytes[:128], "DDS header mismatch"
def decode(b):return np.asarray(Image.open(BytesIO(b)).convert("RGBA")).copy()
raw_s=decode(source_bytes);raw_f=decode(candidate_bytes)
source=np.flipud(raw_s).copy();current=np.flipud(raw_f).copy()
clean=np.asarray(Image.open(clean_path).convert("RGBA")).copy()
assert source.shape==current.shape==clean.shape==(1024,4096,4)
def changed(a,b):return np.any(a!=b,axis=2)
def comp(a,bg):
    alpha=a[...,3:4].astype(np.uint16)
    return ((a[...,:3].astype(np.uint16)*alpha+bg*(255-alpha)+127)//255).astype(np.uint8)
def bbox(m):
    yy,xx=np.where(m)
    return None if not len(xx) else [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
rows=[
("01_create_new_license","CREATE NEW LICENSE","새 라이선스 만들기",[13,548,1954,696]),
("02_select_license","SELECT LICENSE","라이선스 선택",[2007,541,3468,689]),
("03_single_player","SINGLE PLAYER","싱글 플레이",[12,374,1388,522]),
("04_default_license","DEFAULT LICENSE","기본 라이선스",[1772,374,3316,522]),
("05_multiplayer","MULTIPLAYER","멀티플레이",[15,203,1235,347])]
all_eight=[
[13,548,1954,696],[2007,541,3468,689],[12,374,1388,522],[1772,374,3316,522],[15,203,1235,347],
[1610,286,2197,350],[2674,288,3094,350],[2566,952,3086,1014]]
mask=np.zeros((1024,4096),dtype=bool)
for l,t,r,b in all_eight:mask[t:b,l:r]=True
rgba_out=int(np.count_nonzero(changed(source,current)&~mask))
alpha_out=int(np.count_nonzero((source[:,:,3]!=current[:,:,3])&~mask))
clean_out=int(np.count_nonzero(changed(source,clean)&~mask))
details=[]
for name,en,ko,box in rows:
    l,t,r,b=box
    sl=source[t:b,l:r];cl=clean[t:b,l:r];fl=current[t:b,l:r]
    sm=sl[:,:,3]>0;fm=fl[:,:,3]>0
    ab=bbox(sm);bb=bbox(fm)
    absbb=None if ab is None else [ab[0]+l,ab[1]+t,ab[2]+l,ab[3]+t]
    absfb=None if bb is None else [bb[0]+l,bb[1]+t,bb[2]+l,bb[3]+t]
    margins=None if absfb is None else [absfb[0]-l,r-absfb[2],absfb[1]-t,b-absfb[3]]
    preserved_art=not np.any(changed(source,current)[t:b,l:r]&~sm&~fm)
    pad=12;crop_l=max(0,l-pad);crop_t=max(0,t-pad);crop_r=min(4096,r+pad);crop_b=min(1024,b+pad)
    crops=[a[crop_t:crop_b,crop_l:crop_r] for a in (source,clean,current)]
    for typ,a in zip(("ORIGINAL_SOURCE","B60_AUTHORED_CLEAN","CURRENT_PERSISTED_DDS"),crops):
        Image.fromarray(a,"RGBA").save(O/f"{name}_{typ}.png")
    for bg,background in ((0,"BLACK"),(128,"GRAY"),(255,"WHITE")):
        images=[Image.fromarray(comp(a,bg),"RGB") for a in crops]
        w,h=images[0].size
        panel=Image.new("RGB",(3*w,h+24),(46,46,46));draw=ImageDraw.Draw(panel)
        for n,(im,label) in enumerate(zip(images,("ENGLISH","B60 CLEAN","KOREAN PERSISTED"))):
            panel.paste(im,(n*w,24))
            draw.text((n*w+4,4),label,fill="white")
        panel.save(O/f"{name}_{background}_CONTACT_NATIVE.png")
        if background=="GRAY":
            panel.resize((round(w*3*.5),round((h+24)*.5)),Image.Resampling.LANCZOS).save(O/f"{name}_SOURCE_CLEAN_FINAL_50.png")
            panel.resize((round(w*3*.75),round((h+24)*.75)),Image.Resampling.LANCZOS).save(O/f"{name}_SOURCE_CLEAN_FINAL_75.png")
            # First 440 native px are enough for inspecting local glyph strokes without a giant image
            half=min(w,440)
            focus=panel.crop((0,0,half,h+24))
            focus2=panel.crop((w,0,w+half,h+24))
            focus3=panel.crop((2*w,0,2*w+half,h+24))
            narrow=Image.new("RGB",(3*half,h+24),(30,30,30))
            for n,im in enumerate((focus,focus2,focus3)):narrow.paste(im,(n*half,0))
            narrow.resize((narrow.width*2,narrow.height*2),Image.Resampling.NEAREST).save(O/f"{name}_NATIVE_LEFT_FOCUS_2X.png")
    # For raw mirror-y, reversible coordinate transformation.
    raw_t,raw_b=1024-crop_b,1024-crop_t
    Image.fromarray(raw_s[raw_t:raw_b,crop_l:crop_r],"RGBA").save(O/f"{name}_SOURCE_RAW.png")
    Image.fromarray(raw_f[raw_t:raw_b,crop_l:crop_r],"RGBA").save(O/f"{name}_FINAL_RAW.png")
    assert np.array_equal(np.flipud(raw_s[raw_t:raw_b,crop_l:crop_r]),crops[0])
    assert np.array_equal(np.flipud(raw_f[raw_t:raw_b,crop_l:crop_r]),crops[2])
    details.append({
        "id":name,"source_text":en,"localized_text":ko,
        "source_bbox":box,"source_alpha_bbox":absbb,"candidate_alpha_bbox":absfb,
        "candidate_positive_margins_lrtb":margins,
        "source_alpha_count":int(np.count_nonzero(sm)),
        "candidate_alpha_count":int(np.count_nonzero(fm)),
        "source_clean_residual_alpha_inside_bbox":int(np.count_nonzero(cl[:,:,3])),
        "changed_source_to_candidate_inside_source_bbox":int(np.count_nonzero(changed(sl,fl))),
        "changed_clean_to_candidate_inside_bbox":int(np.count_nonzero(changed(cl,fl))),
        "outside_original_glyph_effect_pixels_fully_proven":"NO: exact glyph-only and protected plate mask not independently obtained",
        "native_raw_orientation_byte_exact":True,
        "contact_native":f"{name}_GRAY_CONTACT_NATIVE.png",
        "practical50":f"{name}_SOURCE_CLEAN_FINAL_50.png",
        "focus2x":f"{name}_NATIVE_LEFT_FOCUS_2X.png"
    })
machine={"run":"C292","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",
         "policy_version":"visual-evidence-v1-20261008","queue_index":154,
         "source_sha256":source_sha,"candidate_sha256":candidate_sha,"clean_sha256":clean_sha,
         "source_url":source_url,"native_size":[4096,1024],"format":"BGRA32_DDS","raw_orientation":"mirror_y",
         "source_candidate_header_128_equal":True,
         "source_current_changed_outside_8_source_boxes":rgba_out,
         "source_current_alpha_outside_8_source_boxes":alpha_out,
         "source_clean_changed_outside_8_source_boxes":clean_out,
         "five_red_regions":details,"triage":triage_info["assets"][0],
         "visual_C":"PENDING_CONTROLLER","C3":"BLOCKED_PENDING_CALIBRATED_C",
         "RUNTIME_VALIDATION":"UNTESTED"}
(O/"C292_Q154_RED_FIVE_MACHINE.json").write_text(json.dumps(machine,ensure_ascii=False,indent=2)+"\n")
print("C292_RED_FIVE",candidate_sha,"OUTSIDE",rgba_out,alpha_out,
      "SOURCE_CLEAN_OUTSIDE",clean_out,"CROPS",len(details))
