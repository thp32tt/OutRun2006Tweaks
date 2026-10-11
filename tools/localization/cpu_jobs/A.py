#!/usr/bin/env python3
"""A246 q193: independently source-bounded Goal B/C/D/E Korean re-lettering,
composed with byte-pinned C2-scoped A243 15 Cont / A245 Online trials.
Never promotes official until final independent C2+C3. No width-ratio gate.
"""
import csv, hashlib, json, os, struct, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont

assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="A"
R=Path.cwd()
OUT=R/"localization/graphics/role_A/20261011-A246-Q193-FOUR-GOALS-INTEGRATED-CLEAN"
OUT.mkdir(parents=True,exist_ok=True)
BASE="localization/graphics/"
SRC=R/(BASE+"role_A/20261009-A208-Q193-GOAL-A-FLAT-UI-PILOT/A208_SOURCE_CANONICAL_RGBA32.dds")
OFF=R/(BASE+"hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/97E863AD_512x256.dds")
A243=R/(BASE+"role_A/20261011-A243-Q193-15CONT-SOURCE-CLEAN-PILOT/A243_Q193_15CONT_TRUE_CLEAN_NATIVE_TRIAL_UNPROMOTED.dds")
A245=R/(BASE+"role_A/20261011-A245-Q193-ONLINE-CLEAN-REAL-GLYPH/A245_Q193_ONLINE_TRUE_CLEAN_NATIVE_TRIAL_UNPROMOTED.dds")
SHA_SOURCE="d308bf0558ed46ab531c869c65260e37a02f125ceaf7efd0f12524c3d0266451"
SHA_OFF="9ea15d130693dd99bcd0ffa445b4799132665c5c93728c1c11783c94ba25b0f3"
SHA_A243="79a831d6d6d9351a442e766e16617d79720f32085640bbf874bcc11d1928799f"
SHA_A245="107648ca5628048ea4813a2c65385ad72ab002815ed25a8dda236e66eb1dd9e7"
RUN="OUTRUN-KOR-A246-Q193-GOAL-BCDE-SIX-CELL-INTEGRATION-20261011-2200"
F=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
REGIONS=[
 dict(name="goal_b",source="Goal B",korean="목표 B",box=(492,221,648,268)),
 dict(name="goal_c",source="Goal C",korean="목표 C",box=(30,221,188,268)),
 dict(name="goal_d",source="Goal D",korean="목표 D",box=(1473,308,1629,355)),
 dict(name="goal_e",source="Goal E",korean="목표 E",box=(1011,308,1171,355))]
INHERITED=[
 ("15_cont",(1413,221,1622,268),A243,SHA_A243),
 ("online",(1660,156,1832,194),A245,SHA_A245)]
W,H=2048,1024
def sha(b):return hashlib.sha256(b).hexdigest()
def file_sha(p):return sha(p.read_bytes())
def ref(p):return {"path":str(p.relative_to(R)),"sha256":file_sha(p)}
def save_json(name,obj):
 p=OUT/name;p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return ref(p)
def save_png(name,im):
 p=OUT/name;im.save(p,"PNG");return ref(p)
def check(v,message):
 if not v:raise RuntimeError(message)
def decode(blob):
 check(blob[:4]==b"DDS " and len(blob)==128+W*H*4,"DDS unexpected length")
 check(struct.unpack_from("<II",blob,12)==(H,W),"dimensions incorrect")
 check(struct.unpack_from("<I",blob,28)[0]==1 and struct.unpack_from("<I",blob,88)[0]==32,"mip/bitcount drift")
 check(struct.unpack_from("<IIII",blob,92)==(255,65280,16711680,4278190080),"not q193 native RGBA masks")
 return Image.frombytes("RGBA",(W,H),blob[128:],"raw","RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def bbox_alpha(a):
 ys,xs=np.nonzero(a)
 check(len(xs)>50,"empty source alpha")
 return (int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1))
def flat(im,bg):
 return Image.alpha_composite(Image.new("RGBA",im.size,(*bg,255)),im).convert("RGB")
with (R/"localization/graphics/asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
 queue=next(x for x in csv.DictReader(f) if x["index"].lstrip("\ufeff")=="193")
check(queue["action"]=="localize_text" and "rework" in queue["artwork_status"].lower(),"q193 rework owner/status changed")
check("OUTRUN-KOR-A245-Q193-ONLINE-SOURCE-NATIVE-20261011-2100" in queue["notes"],"A245 state not saved; stop")
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","193"],capture_output=True,text=True,check=True)
save_json("A246_TRIAGE.json",{"output":tri.stdout,"decision":"MATERIAL_REWORK_4_C1_VERIFIED_GLITCHED_GOAL_CELLS; integration of independent prior 15 Cont and Online per C2 scoped checks","run_key":RUN})
srcbytes=SRC.read_bytes();offbytes=OFF.read_bytes()
check(sha(srcbytes)==SHA_SOURCE and sha(offbytes)==SHA_OFF,"source/official SHA drift")
check(srcbytes[:128]==offbytes[:128],"source HD format differs official")
S=np.asarray(decode(srcbytes)).copy();B=np.asarray(decode(offbytes)).copy()
result=B.copy()
clean=B.copy()
letters=np.zeros_like(B)
# Exact sha-bound prior trials are *integrated*, never synthetically called completed
# without preserving each previous source ROI. New four regions kept independent.
rows=[]
used=np.zeros((H,W),bool)
for region_id,cell,p,expected in INHERITED:
 b=p.read_bytes()
 check(sha(b)==expected,"prior C2-scoped candidate SHA drift "+region_id)
 prior=np.asarray(decode(b))
 x0,y0,x1,y1=cell
 dif=np.any(prior!=B,axis=2)
 allowed=np.zeros((H,W),bool);allowed[y0:y1,x0:x1]=True
 check(int(np.count_nonzero(dif&~allowed))==0,"prior trial has unrelated atlas changes: "+region_id)
 check(not np.any(used&allowed),"integration regions overlap")
 used|=allowed
 result[y0:y1,x0:x1]=prior[y0:y1,x0:x1]
 rows.append({"id":region_id,"method":"prior C2-scoped real saved trial byte-verified, ROI integrated","trial_sha256":expected,
              "source_roi":list(cell),"official_to_prior_changed":int(np.count_nonzero(dif)),
              "outside":int(np.count_nonzero(dif&~allowed))})
check(F.is_file(),"Noto native Hangul font unavailable")
font_sha=file_sha(F)
source=Image.fromarray(S,"RGBA")
original=Image.fromarray(B,"RGBA")
for reg in REGIONS:
 name=reg["name"];x0,y0,x1,y1=reg["box"]
 check(not np.any(used[y0:y1,x0:x1]),"Four Goal regions overlap trial cells")
 cell_s=S[y0:y1,x0:x1,:]
 source_measure=bbox_alpha(cell_s[:,:,3]>0)
 check(source_measure==(0,0,x1-x0,y1-y0) or
       (source_measure[0]>=0 and source_measure[1]>=0 and
        source_measure[2]<=x1-x0 and source_measure[3]<=y1-y0),"Goal source glyph bbox outside declared C2 ROI")
 check(np.count_nonzero(cell_s[:,:,3]>0)>500,"source cell unexpectedly empty")
 # Zero ONLY original glyph+effect source rectangle (old Korean is entirely inside).
 check(np.count_nonzero(B[y0:y1,x0:x1,3])>200,"existing Korean glyph unexpected")
 clean[y0:y1,x0:x1]=0
 check(np.count_nonzero(clean[y0:y1,x0:x1,3])==0,"Goal CLEAN retained alpha")
 # Truly native outlined AA text; never force phrase width, preserving condensed family by
 # source height selection only. Every syllable and Latin goal-letter must be visible.
 AA=4
 glyph=None
 chosen=0
 for size in range(54,27,-1):
    f=ImageFont.truetype(str(F),size*AA,index=1)
    canvas=Image.new("L",(450*AA,100*AA))
    ImageDraw.Draw(canvas).text((4*AA,0),reg["korean"],font=f,fill=255)
    cb=canvas.getbbox()
    if cb is None:continue
    crop=canvas.crop(cb)
    g=crop.resize((round(crop.width/AA),round(crop.height/AA)),Image.Resampling.LANCZOS)
    if g.width<=x1-x0-6 and g.height<=y1-y0-4 and g.height>=int((y1-y0)*0.73):
        glyph=g;chosen=size;break
 check(glyph is not None,"no native readable font fits "+name)
 gx=x0+3
 gy=y0+((y1-y0)-glyph.height)//2
 check(gx>=x0+1 and gx+glyph.width<=x1-1 and
       gy>=y0+1 and gy+glyph.height<=y1-1,"1px bounded source glyph FAIL "+name)
 mask=np.asarray(glyph,dtype=np.uint8)
 actual=bbox_alpha(mask>0)
 face_pixels=cell_s[:,:,:3][cell_s[:,:,3]>=220]
 check(len(face_pixels)>100,"no original source color samples")
 color=tuple(int(v) for v in np.median(face_pixels,axis=0))
 # SOURCE original upright dark-flat title, no invented bevel or shadow.
 layer=Image.new("RGBA",glyph.size,(*color,0));layer.putalpha(glyph)
 isolated=Image.new("RGBA",(x1-x0,y1-y0))
 isolated.alpha_composite(layer,(gx-x0,gy-y0))
 # Written into the isolated CLEAN only, not blend over source.
 cell_a=np.asarray(isolated)
 letters[y0:y1,x0:x1]=cell_a
 result[y0:y1,x0:x1]=cell_a
 allowed=np.zeros((H,W),bool);allowed[y0:y1,x0:x1]=True
 used|=allowed
 rows.append({"id":name,"source_english":reg["source"],"new_korean":reg["korean"],
       "source_bbox":list(reg["box"]),"new_bbox":[gx,gy,gx+glyph.width,gy+glyph.height],
       "font_size":chosen,"font_sha256":font_sha,"native_glyph_size":list(glyph.size),
       "source_median_rgb":color,"source_shorter_korean_width":"NOT_A_QA_FAILURE_20261011_POLICY",
       "margin_lr_tb":[gx-x0,x1-(gx+glyph.width),gy-y0,y1-(gy+glyph.height)],
       "clean_alpha_pixels":0,
       "changed_vs_official":int(np.count_nonzero(np.any(cell_a!=B[y0:y1,x0:x1],axis=2)))})
 # 5-stage native proofs for each region (source/official/CLEAN/glyph/SAVED)
 plate_crop=Image.fromarray(clean[y0:y1,x0:x1],"RGBA")
 glyph_crop=Image.fromarray(letters[y0:y1,x0:x1],"RGBA")
 persist_crop=Image.fromarray(result[y0:y1,x0:x1],"RGBA")
 save_png("A246_"+name+"_SOURCE_NATIVE.png",source.crop(reg["box"]))
 save_png("A246_"+name+"_CLEAN_NATIVE.png",plate_crop)
 save_png("A246_"+name+"_GLYPH_NATIVE.png",glyph_crop)
 for cname,bg in [("GRAY",(105,105,105)),("BLACK",(0,0,0)),("WHITE",(255,255,255))]:
    parts=[flat(im,bg) for im in [source.crop(reg["box"]),original.crop(reg["box"]),plate_crop,glyph_crop,persist_crop]]
    for pct in (100,75,50):
       width=round((x1-x0)*pct/100)
       height=round((y1-y0)*pct/100)
       card=Image.new("RGB",(5*width,height),bg)
       for k,v in enumerate(parts):
           card.paste(v.resize((width,height),Image.Resampling.LANCZOS),(k*width,0))
       save_png("A246_"+name+"_"+cname+"_"+str(pct)+".png",card)
# Preserve ALL other atlas pixels exactly; no promotion until C2/C3.
check(np.all(result[~used]==B[~used]),"official protected art changed")
changed=np.any(result!=B,axis=2)
changed_outside=int(np.count_nonzero(changed&~used))
check(changed_outside==0,"changed outside all six allowed source bboxes")
check(all(np.any(result[r["source_bbox"][1]:r["source_bbox"][3],r["source_bbox"][0]:r["source_bbox"][2],3]) for r in rows if r["id"].startswith("goal_")),"saved glyph missing")
out=OUT/"A246_Q193_SIX_LEGACY_SOURCE_CLEAN_INTEGRATED_TRIAL_UNPROMOTED.dds"
actual_im=Image.fromarray(result,"RGBA")
out.write_bytes(srcbytes[:128]+actual_im.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw","RGBA"))
decoded=np.asarray(decode(out.read_bytes()))
check(np.array_equal(decoded,result),"save/redecode mismatch")
save_png("A246_PERSISTED_FLIPY_NATIVE.png",Image.fromarray(decoded,"RGBA"))
save_png("A246_PERSISTED_RAW.png",Image.fromarray(decoded,"RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
save_png("A246_CLEAN_RAW.png",Image.fromarray(clean,"RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
save_png("A246_NEW_GOALS_GLYPH_RAW.png",Image.fromarray(letters,"RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
save_json("A246_SOURCE_FAMILY_RECIPE.json",{"version":"a246-goal-source-native-v1","run_key":RUN,
 "canonical_source_sha256":SHA_SOURCE,"official_sha256":SHA_OFF,
 "inherited_scoped_prior_trials":{"15_cont":SHA_A243,"online":SHA_A245},
 "font_file":str(F),"font_sha256":font_sha,"ttc_index":1,"font_license":"SIL OFL",
 "source_clean_scope":"true clear 4 exact original source bbox; A243/A245 source CLEAN previously independently C2 checked",
 "source_coords":"native readable; persisted native RAW mirror-Y",
 "approvals":"A producer only; independent C2/C3 and user in-game not run",
 "per_glyph_policy":"native 100/75/50 readability not per-sentence stretch"})
machine={"schema_version":2,"run":"A246","run_key":RUN,"role":"A","queue_index":193,
 "priority":"P1","source_sha256":SHA_SOURCE,"official_sha256":SHA_OFF,
 "new_six_cell_persisted_trial_sha256":file_sha(out),
 "new_dds_saved":1,"official_dds_changed":0,
 "native_size":[W,H],"mips":1,"format":"RGBA32","raw_mirror_y":True,
 "saved_dds_roundtrip_exact":True,"changed_vs_official":int(np.count_nonzero(changed)),
 "changed_outside_six_source_bboxes":changed_outside,
 "new_native_rendered_goals":4,"integrated_prior_C2_scoped_cells":2,
 "preserved_other_atlas_pixels":True,"rows":rows,
 "producer_visual":"PENDING_ACTUAL_NATIVE_BGW_100_75_50_RAW",
 "independent_C2":"PENDING_NEW_INTEGRATED_SHA","C3":"NOT_RUN",
 "PJR_IGR":"IGR003_IGR019_IGR033_OPEN","RUNTIME_VALIDATION":"UNTESTED",
 "exclusions":["VR","FFB","DX11","DXVK"]}
save_json("A246_MACHINE_AND_HANDOFF.json",machine)
print(json.dumps({"run":"A246","trial_sha":machine["new_six_cell_persisted_trial_sha256"],
                  "changed":machine["changed_vs_official"],"outside":changed_outside,
                  "goal_count":4,"integrated":2,"promoted":0},ensure_ascii=False),flush=True)
