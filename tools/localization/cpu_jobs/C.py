#!/usr/bin/env python3
"""C2 q154 exact historical producer-clean provenance recheck; evidence only."""
import io, hashlib, json, os, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="C"
root=Path(".")
p=root/"localization/graphics/role_C/20261008-C287-C2-Q154-AUTHORED-CLEAN-CROSSCHECK"
p.mkdir(parents=True,exist_ok=True)
b60=root/"localization/graphics/role_B/20261005-B-PRODUCTION60/4D38_HD_CLEAN_PLATE.png"
c141=root/"localization/graphics/role_C/20261005-C141-4D38BBB0/C141_EXACT_CLEAN_PLATE.png"
c284=root/"localization/graphics/role_C/20261008-C284-C2-Q154-INFERRED-CLEAN-ATLAS-AUDIT/C284_INFERRED_CLEAN_WHOLE_ATLAS_FLIPY.png"
candidate=root/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"
with urllib.request.urlopen(url,timeout=180) as f:sb=f.read()
cb=candidate.read_bytes()
hash=lambda b:hashlib.sha256(b).hexdigest()
source_sha="15a10e6b44ca5f1267fdf24eebbe902bb18a77b3903896370e183fea8a401bcf"
candidate_sha="94678124f6cddaeb44520c6419f4b475d1452866c052ff301a4859dddf38cb1f"
assert hash(sb)==source_sha and hash(cb)==candidate_sha, "source/candidate SHA drift"
assert sb[:128]==cb[:128], "DDS header drift"
def png(x):return np.asarray(Image.open(x).convert("RGBA")).copy()
rawsrc=np.asarray(Image.open(io.BytesIO(sb)).convert("RGBA")).copy()
rawfin=np.asarray(Image.open(io.BytesIO(cb)).convert("RGBA")).copy()
src=np.flipud(rawsrc).copy(); final=np.flipud(rawfin).copy()
clean=png(b60); cclean=png(c141); inferred=png(c284)
assert all(x.shape==(1024,4096,4) for x in (src,final,clean,cclean,inferred))
rows=[
("create_new_license_red","CREATE NEW LICENSE","새 라이선스 만들기",(13,548,1954,696)),
("select_license_red","SELECT LICENSE","라이선스 선택",(2007,541,3468,689)),
("single_player_red","SINGLE PLAYER","싱글 플레이",(12,374,1388,522)),
("default_license_red","DEFAULT LICENSE","기본 라이선스",(1772,374,3316,522)),
("multiplayer_red","MULTIPLAYER","멀티플레이",(15,203,1235,347)),
("single_player_gray","SINGLE PLAYER","싱글 플레이",(1610,286,2197,350)),
("showroom_gray","SHOWROOM","쇼룸",(2674,288,3094,350)),
("multiplayer_gray","MULTIPLAYER","멀티플레이",(2566,952,3086,1014))]
allowed=np.zeros((1024,4096),bool)
for _,_,_,(x0,y0,x1,y1) in rows:allowed[y0:y1,x0:x1]=True
diff=lambda x,y:np.any(x!=y,axis=2)
def bbox(mask):
    ys,xs=np.where(mask)
    return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def neutral(a,bg):
    rgb=a[:,:,:3].astype(np.uint16);alpha=a[:,:,3:4].astype(np.uint16)
    return ((rgb*alpha+bg*(255-alpha)+127)//255).astype(np.uint8)
observed=[]
for rid,en,ko,box in rows:
    x0,y0,x1,y1=box
    source_alpha=src[y0:y1,x0:x1,3]>0
    local_alpha=final[y0:y1,x0:x1,3]>0
    candbbox=bbox(local_alpha)
    if candbbox: candbbox=[candbbox[0]+x0,candbbox[1]+y0,candbbox[2]+x0,candbbox[3]+y0]
    margins=None if candbbox is None else [candbbox[0]-x0,x1-candbbox[2],candbbox[1]-y0,y1-candbbox[3]]
    r={"id":rid,"source_text":en,"korean_text":ko,"source_bbox":list(box),
       "final_alpha_bbox":candbbox,"source_region_opaque_count":int(source_alpha.sum()),
       "final_region_opaque_count":int(local_alpha.sum()),"final_alpha_positive_margins_LRTB":margins,
       "b60_clean_nonzero_alpha_in_source_region":int(np.count_nonzero(clean[y0:y1,x0:x1,3])),
       "b60_clean_vs_c141_changed":int(np.count_nonzero(diff(clean[y0:y1,x0:x1],cclean[y0:y1,x0:x1]))),
       "b60_clean_vs_c284_inferred_changed":int(np.count_nonzero(diff(clean[y0:y1,x0:x1],inferred[y0:y1,x0:x1]))),
       "final_equals_original_visible_pixels_inside_box":int(np.count_nonzero(np.all(src[y0:y1,x0:x1]==final[y0:y1,x0:x1],axis=2)&local_alpha)),
       "alpha_containment":"PASS" if margins is not None and all(v>0 for v in margins) else "FAIL"}
    observed.append(r)
    if rid.endswith("gray"):
        pad=12;l=max(0,x0-pad);t=max(0,y0-pad);rr=min(4096,x1+pad);bb=min(1024,y1+pad)
        images=[Image.fromarray(neutral(a[t:bb,l:rr],128),"RGB") for a in (src,clean,final)]
        w,h=images[0].size
        base=Image.new("RGB",(3*w,h+22),(42,42,42));d=ImageDraw.Draw(base)
        for j,(im,label) in enumerate(zip(images,("SOURCE ENGLISH","B60 AUTHORED CLEAN","CURRENT KOREAN DDS"))):
            base.paste(im,(j*w,22));d.text((j*w+3,4),label,fill="white")
        for kind,im in (("NATIVE",base),("ZOOM2X",base.resize((base.width*2,base.height*2),Image.Resampling.NEAREST)),("PRACTICAL50",base.resize((base.width//2,base.height//2),Image.Resampling.LANCZOS))):
            im.save(p/f"{rid}_{kind}.png")
        Image.fromarray(rawsrc[1024-bb:1024-t,l:rr]).save(p/f"{rid}_SOURCE_RAW.png")
        Image.fromarray(rawfin[1024-bb:1024-t,l:rr]).save(p/f"{rid}_FINAL_RAW.png")
machine={
"run":"C287","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","queue_index":154,
"policy_version":"visual-evidence-v1-20261008","source_sha256":source_sha,"candidate_sha256":candidate_sha,
"source_url":url,"dds_header_identical":True,"native_size":[4096,1024],"raw_orientation":"mirror_y",
"clean_sources":{"authored_B60":{"path":str(b60),"sha256":hash(b60.read_bytes())},
"independent_C141":{"path":str(c141),"sha256":hash(c141.read_bytes())},
"inferred_C284":{"path":str(c284),"sha256":hash(c284.read_bytes())}},
"b60_vs_c141_rgba_differing_pixels":int(np.count_nonzero(diff(clean,cclean))),
"b60_vs_c284_rgba_differing_pixels":int(np.count_nonzero(diff(clean,inferred))),
"clean_vs_source_changed_outside_eight_bboxes":int(np.count_nonzero(diff(src,clean)&~allowed)),
"current_vs_source_changed_outside_eight_bboxes":int(np.count_nonzero(diff(src,final)&~allowed)),
"current_vs_source_alpha_changed_outside_eight_bboxes":int(np.count_nonzero((src[:,:,3]!=final[:,:,3])&~allowed)),
"b60_alpha_nonzero_inside_source_eight_bboxes":int(np.count_nonzero(clean[:,:,3]&allowed)),
"rows":observed,
"machine_status":"EXACT_CLEAN_PROVENANCE_CHECKED",
"visual_C":"PENDING_CONTROLLER_REVIEW","C3":"NOT_PERFORMED","RUNTIME_VALIDATION":"UNTESTED"}
(p/"C287_Q154_AUTHORED_CLEAN_MACHINE.json").write_text(json.dumps(machine,ensure_ascii=False,indent=2)+"\n")
print("C287_clean_diff_C141",machine["b60_vs_c141_rgba_differing_pixels"],
      "C284",machine["b60_vs_c284_rgba_differing_pixels"],
      "clean_outside",machine["clean_vs_source_changed_outside_eight_bboxes"],
      "candidate_outside",machine["current_vs_source_changed_outside_eight_bboxes"])
