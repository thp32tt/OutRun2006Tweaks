#!/usr/bin/env python3
import os, json, hashlib, struct, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

def sha(b): return hashlib.sha256(b).hexdigest()
def bbox(mask):
    yy,xx=np.nonzero(mask)
    if len(xx)==0: return None
    return [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def count(mask): return int(np.count_nonzero(mask))
def dl(url,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    urllib.request.urlretrieve(url,path)
def comp(im,bg=(70,70,70,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def dds_basic(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    return {
      "width":struct.unpack_from("<I",b,16)[0],
      "height":struct.unpack_from("<I",b,12)[0],
      "mipmaps":struct.unpack_from("<I",b,28)[0],
      "fourcc":b[84:88].decode("latin1")
    }

# ---------------- C203 / A60 59A79158 ----------------
run1="20261005-C203-59A79158"
out1=repo/"localization/graphics/role_C"/run1
out1.mkdir(parents=True,exist_ok=True)
pr1=json.loads((repo/"localization/graphics/role_A/20261005-A-PRODUCTION60/A60_59A79158_REPORT.json").read_text(encoding="utf-8"))
cand1=repo/pr1["candidate_path"]
sp1=pr1["source_provenance"]
asset1=pr1["asset"]
tmp1=Path("/tmp/c203"); tmp1.mkdir(exist_ok=True)
srcdds1=tmp1/"source.dds"; atlasp1=tmp1/"atlas.json"
folder1=asset1.split("/")[-2]; name1=asset1.split("/")[-1]
base1=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{sp1['commit']}"
dl(base1+f"/Release/{folder1}/{name1}",srcdds1)
dl(base1+f"/Original%20(PC)/Original%20(Tweaks%20dumps)/{folder1}/4x_{name1[:-4]}_atlas.json",atlasp1)

sb1=srcdds1.read_bytes(); cb1=cand1.read_bytes()
if sha(sb1)!=sp1["source_sha256"]: raise RuntimeError(("C203 source SHA",sha(sb1),sp1["source_sha256"]))
if sha(cb1)!=pr1["candidate_sha256"]: raise RuntimeError(("C203 candidate SHA",sha(cb1),pr1["candidate_sha256"]))
if cb1[:128]!=sb1[:128]: raise RuntimeError("C203 header mismatch")
raws1=Image.open(srcdds1).convert("RGBA"); rawf1=Image.open(cand1).convert("RGBA")
src1=raws1.transpose(Image.Transpose.FLIP_TOP_BOTTOM); fin1=rawf1.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa1=np.asarray(src1,dtype=np.uint8); fa1=np.asarray(fin1,dtype=np.uint8)
H1,W1=sa1.shape[:2]
if (W1,H1)!=(1024,2048): raise RuntimeError(("C203 size",W1,H1))
atlas1=json.loads(atlasp1.read_text(encoding="utf-8"))
regs1={int(r["idx"]):r for r in atlas1["regions"]}
rows1={int(r["region_idx"]):r for r in pr1["rows"]}
if set(regs1)!=set(range(24)) or set(rows1)!=set(range(24)): raise RuntimeError("C203 region set")
expected1=[
("Waterfalls","워터폴스"),("Tulip Garden","튤립 가든"),("Sunny Beach","서니 비치"),
("Snow Mountain","스노 마운틴"),("Skyscrapers","스카이스크레이퍼스"),("Palm Beach","팜 비치"),
("National Park","내셔널 파크"),("Milky Way","밀키 웨이"),("Metropolis","메트로폴리스"),
("Lost City","로스트 시티"),("Legend","레전드"),("Jungle","정글"),
("Industrial Complex","인더스트리얼 컴플렉스"),("Imperial Avenue","임페리얼 애비뉴"),
("Ice Scape","아이스스케이프"),("Giant Statues","자이언트 스태추스"),
("Ghost Forest","고스트 포레스트"),("Floral Village","플로럴 빌리지"),("Desert","데저트"),
("Deep Lake","딥 레이크"),("Coniferous Forest","코니퍼러스 포레스트"),
("Cloudy Highland","클라우디 하이랜드"),("Casino Town","카지노 타운"),("Castle Wall","캐슬 월")
]
semantic1=all((rows1[i]["source"],rows1[i]["korean"])==expected1[i] for i in range(24))
allowed1=np.zeros((H1,W1),dtype=bool); lms=[]; checks1=[]; source_exact=True; final_exact=True; residue=0
equal1=np.all(fa1==sa1,axis=2)
for i in range(24):
    x,y,w,h=map(int,regs1[i]["rect"])
    sm=sa1[y:y+h,x:x+w,3]>0
    bb=bbox(sm)
    if bb is None: raise RuntimeError(("C203 empty source row",i))
    sbb=[bb[0]+x,bb[1]+y,bb[2]+x,bb[3]+y]
    ds=list(map(int,rows1[i]["original_bbox"]))
    se=(sbb==ds); source_exact &= se
    x0,y0,x1,y1=sbb; allowed1[y0:y1,x0:x1]=True
    fm=fa1[y0:y1,x0:x1,3]>0
    fb=bbox(fm); fbb=None if fb is None else [fb[0]+x0,fb[1]+y0,fb[2]+x0,fb[3]+y0]
    df=list(map(int,rows1[i]["localized_bbox"]))
    fe=(fbb==df); final_exact &= fe
    if fbb is None:
        dlft=drgt=dtop=dbot=-1; contain=size_ok=positive=False
    else:
        a,b,c,d=fbb; dlft=a-x0; drgt=x1-c; dtop=b-y0; dbot=y1-d
        contain=a>=x0 and b>=y0 and c<=x1 and d<=y1
        size_ok=(c-a)<=x1-x0 and (d-b)<=y1-y0
        positive=min(dlft,drgt,dtop,dbot)>0
        lm=np.zeros((H1,W1),dtype=bool); lm[y0:y1,x0:x1]=fm; lms.append(lm)
        smf=np.zeros((H1,W1),dtype=bool); smf[y:y+h,x:x+w]=sm
        outside_final=smf.copy(); outside_final[b:d,a:c]=False
        residue += count(outside_final & equal1)
    checks1.append({
      "region_idx":i,"source":expected1[i][0],"korean":expected1[i][1],
      "independent_source_bbox":sbb,"producer_source_bbox":ds,"source_bbox_exact_match_producer":se,
      "independent_localized_bbox":fbb,"producer_localized_bbox":df,"localized_bbox_exact_match_producer":fe,
      "delta_left":dlft,"delta_right":drgt,"delta_top":dtop,"delta_bottom":dbot,
      "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL","positive_margin":"PASS" if positive else "FAIL"
    })
chg1=np.any(fa1!=sa1,axis=2); ach1=fa1[:,:,3]!=sa1[:,:,3]; intro1=fa1[:,:,3]>sa1[:,:,3]
m1={
 "decoded_changed_outside_union_source_bboxes":count(chg1&~allowed1),
 "alpha_changed_outside_union_source_bboxes":count(ach1&~allowed1),
 "introduced_visible_outside_union_source_bboxes":count(intro1&~allowed1),
 "source_residue_exact_pixels_outside_localized_bboxes":residue
}
ov=0; touch=0
for i,mi in enumerate(lms):
    yy,xx=np.nonzero(mi); dil=np.zeros_like(mi)
    for dy in (-1,0,1):
      for dx in (-1,0,1):
        ys=np.clip(yy+dy,0,H1-1); xs=np.clip(xx+dx,0,W1-1); dil[ys,xs]=True
    for mj in lms[i+1:]:
      ov+=count(mi&mj); touch+=count(dil&mj)
m1["localized_overlap_pixels"]=ov; m1["localized_1px_touch_pixels"]=touch
rowpass1=sum(1 for r in checks1 if r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS")
status1="PASS" if rowpass1==24 and source_exact and final_exact and semantic1 and all(v==0 for v in m1.values()) else "FAIL"

cards=[]
for r in checks1:
    x0,y0,x1,y1=r["independent_source_bbox"]; pad=8
    crop=(max(0,x0-pad),max(0,y0-pad),min(W1,x1+pad),min(H1,y1+pad))
    a=comp(src1).crop(crop); b=comp(fin1).crop(crop); cw=max(a.width,b.width); ch=max(a.height,b.height)
    card=Image.new("RGB",(cw*2+8,ch+22),"white"); card.paste(a,(0,22)); card.paste(b,(cw+8,22))
    d=ImageDraw.Draw(card); d.text((2,3),f"{r['region_idx']} {r['source']}",fill="black"); d.text((cw+10,3),r["korean"],fill="black")
    cards.append(card)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+3*(len(cards)-1)),"white")
yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+3
if sheet.width>1800: sheet=sheet.resize((1800,round(sheet.height*1800/sheet.width)),Image.Resampling.LANCZOS)
sheet.save(out1/"C203_TARGET_CONTACTS.jpg",quality=96)
rawcard=Image.new("RGB",(1024,2070),"white")
rawcard.paste(comp(raws1).resize((512,1024),Image.Resampling.LANCZOS),(0,22))
rawcard.paste(comp(rawf1).resize((512,1024),Image.Resampling.LANCZOS),(512,22))
d=ImageDraw.Draw(rawcard); d.text((4,3),"SOURCE_RAW_MIRROR_Y",fill="black"); d.text((516,3),"FINAL_RAW_MIRROR_Y",fill="black")
rawcard.save(out1/"C203_RAW_COMPARE.jpg",quality=95)
rep1={
 "schema_version":1,"role":"C","run":run1,"qa_id":"C203","queue_index":163,"asset":asset1,
 "producer_run":pr1["run"],"source_sha256":sp1["source_sha256"],"candidate_sha256":pr1["candidate_sha256"],
 "structure":{"dimensions":[W1,H1],"header_exact":True,"raw_orientation":"mirror_y","producer_format":pr1["structure"]["format"]},
 "semantic_policy_pass":semantic1,"source_bbox_exact_match_all":source_exact,"candidate_bbox_exact_match_all":final_exact,
 "row_checks":checks1,"row_gate":f"{rowpass1}/24 PASS","machine_checks":m1,"machine_status":status1,
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","decision":"PENDING_CONTROLLER_VISUAL_QA" if status1=="PASS" else "C203_REWORK_REQUIRED_MACHINE_OR_POLICY_GATE",
 "runtime_validation":"UNTESTED","preview_files":[f"localization/graphics/role_C/{run1}/C203_TARGET_CONTACTS.jpg",f"localization/graphics/role_C/{run1}/C203_RAW_COMPARE.jpg"]
}
(out1/"C203_59A79158_MACHINE_QA.json").write_text(json.dumps(rep1,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"C203_59A79158.json").write_text(json.dumps({
 "run":run1,"qa_id":"C203","index":163,"asset":"59A79158","candidate_sha256":pr1["candidate_sha256"],
 "machine_status":status1,"row_gate":rep1["row_gate"],"semantic_policy_pass":semantic1,
 "source_bbox_exact_match_all":source_exact,"candidate_bbox_exact_match_all":final_exact,
 "machine_checks":m1,"report":f"localization/graphics/role_C/{run1}/C203_59A79158_MACHINE_QA.json","runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

# ---------------- C204 / B151 DCC7B488 ----------------
run2="20261005-C204-DCC7B488"
out2=repo/"localization/graphics/role_C"/run2
out2.mkdir(parents=True,exist_ok=True)
pr2=json.loads((repo/"localization/graphics/role_B/20261005-B-PRODUCTION151-DCC7/B151_DCC7_REPORT.json").read_text(encoding="utf-8"))
cand2=repo/pr2["candidate_path"]; sp2=pr2["source_provenance"]; asset2=pr2["asset"]
tmp2=Path("/tmp/c204"); tmp2.mkdir(exist_ok=True); srcdds2=tmp2/"source.dds"
folder2=asset2.split("/")[-2]; name2=asset2.split("/")[-1]
base2=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{sp2['commit']}"
dl(base2+f"/Release/{folder2}/{name2}",srcdds2)
sb2=srcdds2.read_bytes(); cb2=cand2.read_bytes()
if sha(sb2)!=sp2["source_sha256"]: raise RuntimeError(("C204 source SHA",sha(sb2),sp2["source_sha256"]))
if sha(cb2)!=pr2["candidate_sha256"]: raise RuntimeError(("C204 candidate SHA",sha(cb2),pr2["candidate_sha256"]))
if cb2[:128]!=sb2[:128]: raise RuntimeError("C204 header mismatch")
raws2=Image.open(srcdds2).convert("RGBA"); rawf2=Image.open(cand2).convert("RGBA")
src2=raws2.transpose(Image.Transpose.FLIP_TOP_BOTTOM); fin2=rawf2.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa2=np.asarray(src2,dtype=np.uint8); fa2=np.asarray(fin2,dtype=np.uint8)
H2,W2=sa2.shape[:2]
if (W2,H2)!=(2048,1024): raise RuntimeError(("C204 size",W2,H2))
basep=repo/"localization/graphics/role_B/20261005-B-PRODUCTION151-DCC7"
sourcepng=Image.open(basep/"B151_SOURCE_READABLE.png").convert("RGBA")
clean=Image.open(basep/"B151_CLEAN_PLATE.png").convert("RGBA")
finalpng=Image.open(basep/"B151_FINAL_READABLE.png").convert("RGBA")
stm=Image.open(basep/"B151_SOURCE_TEXT_MASK.png").convert("L")
prot=Image.open(basep/"B151_PROTECTED_MASK.png").convert("L")
allow=Image.open(basep/"B151_ALLOWED_EFFECT_BBOX_MASK.png").convert("L")
spa=np.asarray(sourcepng,dtype=np.uint8); ca=np.asarray(clean,dtype=np.uint8); fpa=np.asarray(finalpng,dtype=np.uint8)
st=np.asarray(stm)>0; pm=np.asarray(prot)>0; am=np.asarray(allow)>0
if count(np.any(spa!=sa2,axis=2))!=0: raise RuntimeError("C204 producer source PNG decode mismatch")
if count(np.any(fpa!=fa2,axis=2))!=0: raise RuntimeError("C204 producer final PNG decode mismatch")
row=pr2["rows"][0]
orig=list(map(int,row["original_bbox"]))
maskbb=bbox(st)
allowbb=bbox(am)
render=np.any(fpa!=ca,axis=2); renderbb=bbox(render)
x0,y0,x1,y1=orig
if renderbb is None:
    dlft=drgt=dtop=dbot=-1; contain=size_ok=positive=False
else:
    a,b,c,d=renderbb; dlft=a-x0; drgt=x1-c; dtop=b-y0; dbot=y1-d
    contain=a>=x0 and b>=y0 and c<=x1 and d<=y1
    size_ok=(c-a)<=x1-x0 and (d-b)<=y1-y0
    positive=min(dlft,drgt,dtop,dbot)>0
changed=np.any(fa2!=sa2,axis=2); ach=fa2[:,:,3]!=sa2[:,:,3]
clean_changed=np.any(ca!=spa,axis=2)
m2={
 "decoded_source_vs_evidence_diff_pixels":count(np.any(sa2!=spa,axis=2)),
 "decoded_final_vs_evidence_diff_pixels":count(np.any(fa2!=fpa,axis=2)),
 "source_text_mask_bbox_matches_original_bbox":bool(maskbb==orig),
 "allowed_mask_bbox_matches_original_bbox":bool(allowbb==orig),
 "localized_bbox_exact_match_producer":bool(renderbb==list(map(int,row["localized_bbox"]))),
 "decoded_changed_outside_allowed_effect_bbox":count(changed&~am),
 "alpha_changed_outside_allowed_effect_bbox":count(ach&~am),
 "localized_render_outside_allowed_effect_bbox":count(render&~am),
 "protected_region_changed_pixels":count(changed&pm),
 "clean_exact_source_residue_pixels_in_source_text_mask":count(st & np.all(ca==spa,axis=2)),
 "localized_overlap_pixels":0
}
# Boundary continuity: producer B151 specifically claims source-boundary blending.
# The outer 1px ring of the exact effect bbox should remain source-exact where not source-text mask.
ring=np.zeros((H2,W2),dtype=bool)
ring[y0:y0+1,x0:x1]=True; ring[y1-1:y1,x0:x1]=True; ring[y0:y1,x0:x0+1]=True; ring[y0:y1,x1-1:x1]=True
ring_safe=ring & ~st
m2["clean_boundary_safe_ring_changed_pixels"]=count(ring_safe & clean_changed)
status2="PASS" if all([
 contain,size_ok,positive,
 m2["source_text_mask_bbox_matches_original_bbox"],
 m2["allowed_mask_bbox_matches_original_bbox"],
 m2["localized_bbox_exact_match_producer"],
 m2["decoded_changed_outside_allowed_effect_bbox"]==0,
 m2["alpha_changed_outside_allowed_effect_bbox"]==0,
 m2["localized_render_outside_allowed_effect_bbox"]==0,
 m2["protected_region_changed_pixels"]==0,
 m2["clean_exact_source_residue_pixels_in_source_text_mask"]==0,
 m2["clean_boundary_safe_ring_changed_pixels"]==0
]) else "FAIL"
focus=Image.new("RGB",(1800,600),"white")
cropbox=(430,100,1180,330)
for j,(lab,im) in enumerate([("SOURCE",src2),("CLEAN",clean),("FINAL",fin2)]):
    crop=comp(im).crop(cropbox).resize((600,550),Image.Resampling.LANCZOS)
    focus.paste(crop,(j*600,30)); ImageDraw.Draw(focus).text((j*600+5,5),lab,fill="black")
focus.save(out2/"C204_DCC7_FOCUS.jpg",quality=96)
rawcard=Image.new("RGB",(2048,1060),"white")
rawcard.paste(comp(raws2).resize((1024,512),Image.Resampling.LANCZOS),(0,24))
rawcard.paste(comp(rawf2).resize((1024,512),Image.Resampling.LANCZOS),(1024,24))
d=ImageDraw.Draw(rawcard); d.text((4,4),"SOURCE_RAW_MIRROR_Y",fill="black"); d.text((1028,4),"FINAL_RAW_MIRROR_Y",fill="black")
rawcard.save(out2/"C204_RAW_COMPARE.jpg",quality=95)
rep2={
 "schema_version":1,"role":"C","run":run2,"qa_id":"C204","queue_index":32,"asset":asset2,
 "producer_run":pr2["run"],"source_sha256":sp2["source_sha256"],"candidate_sha256":pr2["candidate_sha256"],
 "structure":{"dimensions":[W2,H2],"header_exact":True,"raw_orientation":"mirror_y","producer_format":pr2["structure"]["format"]},
 "classification":{"source":"Total Rank","korean":"종합 랭킹","prior_queue_action":"zoom_review","positive_localize_text":True},
 "independent_source_text_mask_bbox":maskbb,"independent_allowed_mask_bbox":allowbb,
 "row_checks":[{
   "original_bbox":orig,"independent_localized_bbox":renderbb,"producer_localized_bbox":list(map(int,row["localized_bbox"])),
   "delta_left":dlft,"delta_right":drgt,"delta_top":dtop,"delta_bottom":dbot,
   "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL","positive_margin":"PASS" if positive else "FAIL"
 }],
 "row_gate":"1/1 PASS" if contain and size_ok and positive else "0/1 FAIL",
 "machine_checks":m2,"machine_status":status2,
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","decision":"PENDING_CONTROLLER_VISUAL_QA" if status2=="PASS" else "C204_REWORK_REQUIRED_MACHINE_OR_POLICY_GATE",
 "runtime_validation":"UNTESTED","preview_files":[f"localization/graphics/role_C/{run2}/C204_DCC7_FOCUS.jpg",f"localization/graphics/role_C/{run2}/C204_RAW_COMPARE.jpg"]
}
(out2/"C204_DCC7B488_MACHINE_QA.json").write_text(json.dumps(rep2,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"C204_DCC7B488.json").write_text(json.dumps({
 "run":run2,"qa_id":"C204","index":32,"asset":"DCC7B488","candidate_sha256":pr2["candidate_sha256"],
 "machine_status":status2,"row_gate":rep2["row_gate"],"machine_checks":m2,
 "report":f"localization/graphics/role_C/{run2}/C204_DCC7B488_MACHINE_QA.json","runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

print(json.dumps({"C203":{"machine_status":status1,"row_gate":rep1["row_gate"],"machine_checks":m1},"C204":{"machine_status":status2,"row_gate":rep2["row_gate"],"machine_checks":m2}},ensure_ascii=False),flush=True)
