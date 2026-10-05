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

def sha256_bytes(b): return hashlib.sha256(b).hexdigest()
def bbox(mask):
    yy,xx=np.nonzero(mask)
    if len(xx)==0: return None
    return [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def count(mask): return int(np.count_nonzero(mask))
def dds_meta(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]
    w=struct.unpack_from("<I",b,16)[0]
    mips=struct.unpack_from("<I",b,28)[0]
    fourcc=b[84:88].decode("ascii","replace")
    return {"width":w,"height":h,"mipmaps":mips,"format":fourcc}
def comp(im,bg=(54,54,54,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def dl(url,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    urllib.request.urlretrieve(url,path)

# ---------------------------------------------------------------------------
# C201: independent A56 55B57CDE DXT5 revalidation
# ---------------------------------------------------------------------------
run1="20261005-C201-55B57CDE"
out1=repo/"localization/graphics/role_C"/run1
out1.mkdir(parents=True,exist_ok=True)
producer1=repo/"localization/graphics/role_A/20261005-A-PRODUCTION56-DXT5/A56_55B57CDE_REPORT.json"
pr1=json.loads(producer1.read_text(encoding="utf-8"))
cand1=repo/pr1["candidate_path"]
asset1=pr1["asset"]
sp1=pr1["source_provenance"]
tmp1=Path("/tmp/c201")
tmp1.mkdir(exist_ok=True)
srcdds1=tmp1/"source.dds"
atlasp1=tmp1/"atlas.json"
folder1=asset1.split("/")[-2]
name1=asset1.split("/")[-1]
base1=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{sp1['commit']}"
dl(base1+f"/Release/{folder1}/{name1}",srcdds1)
dl(base1+f"/Original%20(PC)/Original%20(Tweaks%20dumps)/{folder1}/4x_{name1[:-4]}_atlas.json",atlasp1)

sb1=srcdds1.read_bytes(); cb1=cand1.read_bytes()
if sha256_bytes(sb1)!=sp1["sha256"]: raise RuntimeError(("C201 source sha drift",sha256_bytes(sb1),sp1["sha256"]))
if sha256_bytes(cb1)!=pr1["candidate_sha256"]: raise RuntimeError(("C201 candidate sha drift",sha256_bytes(cb1),pr1["candidate_sha256"]))
meta_s1=dds_meta(sb1); meta_c1=dds_meta(cb1)
if meta_s1!={"width":2048,"height":2048,"mipmaps":1,"format":"DXT5"} or meta_c1!=meta_s1 or cb1[:128]!=sb1[:128]:
    raise RuntimeError(("C201 DDS structure/header drift",meta_s1,meta_c1,cb1[:128]==sb1[:128]))

raw_src1=Image.open(srcdds1).convert("RGBA")
raw_fin1=Image.open(cand1).convert("RGBA")
src1=raw_src1.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
fin1=raw_fin1.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa1=np.asarray(src1,dtype=np.uint8); fa1=np.asarray(fin1,dtype=np.uint8)
H1,W1=sa1.shape[:2]
atlas1=json.loads(atlasp1.read_text(encoding="utf-8"))
regs1={int(r["idx"]):r for r in atlas1["regions"]}
rows1={int(e["idx"]):e for e in pr1["elements"]}
if set(regs1)!=set(range(38)) or set(rows1)!=set(range(38)):
    raise RuntimeError("C201 region/row set mismatch")

expected1=[
("VIRGO","처녀자리"),("TAURUS","황소자리"),("SCORPIO","전갈자리"),("SAGITTARIUS","사수자리"),
("PISCES","물고기자리"),("LIBRA","천칭자리"),("LEO","사자자리"),("GEMINI","쌍둥이자리"),
("CAPRICORN","염소자리"),("CANCER","게자리"),("ARIES","양자리"),("AQUARIUS","물병자리"),
("THAILAND","태국"),("SWITZERLAND","스위스"),("SWEDEN","스웨덴"),("SPAIN","스페인"),
("SOUTH KOREA","대한민국"),("SINGAPORE","싱가포르"),("OTHER","기타"),("NORWAY","노르웨이"),
("NORTH KOREA","북한"),("NEW ZEALAND","뉴질랜드"),("MEXICO","멕시코"),("JAPAN","일본"),
("ITALY","이탈리아"),("HONG KONG","홍콩"),("GERMANY","독일"),("FRANCE","프랑스"),
("FINLAND","핀란드"),("NETHERLANDS","네덜란드"),("DENMARK","덴마크"),("CHINA","중국"),
("CANADA","캐나다"),("BRITAIN","영국"),("BELGIUM","벨기에"),("AUSTRIA","오스트리아"),
("AUSTRALIA","호주"),("USA","미국")
]
semantic1=all((rows1[i]["source"].upper(),rows1[i]["korean"])==expected1[i] for i in range(38))
allowed1=np.zeros((H1,W1),dtype=bool)
lms1=[]; checks1=[]; source_exact1=True; final_exact1=True; residue1=0
for i in range(38):
    r=regs1[i]; x,y,w,h=map(int,r["rect"])
    smask=sa1[y:y+h,x:x+w,3]>0
    bb=bbox(smask)
    if bb is None: raise RuntimeError(("C201 empty source",i))
    sbb=[bb[0]+x,bb[1]+y,bb[2]+x,bb[3]+y]
    declared_s=list(map(int,rows1[i]["original_bbox"]))
    se=(sbb==declared_s); source_exact1 &= se
    x0,y0,x1,y1=sbb
    allowed1[y0:y1,x0:x1]=True
    fmask=fa1[y0:y1,x0:x1,3]>0
    fb=bbox(fmask)
    fbb=None if fb is None else [fb[0]+x0,fb[1]+y0,fb[2]+x0,fb[3]+y0]
    declared_f=list(map(int,rows1[i]["localized_bbox"]))
    fe=(fbb==declared_f); final_exact1 &= fe
    if fbb is None:
        contain=size_ok=positive=False; dlft=drgt=dtop=dbot=-1
    else:
        a,b,c,d=fbb
        dlft=a-x0; drgt=x1-c; dtop=b-y0; dbot=y1-d
        contain=a>=x0 and b>=y0 and c<=x1 and d<=y1
        size_ok=(c-a)<=x1-x0 and (d-b)<=y1-y0
        positive=min(dlft,drgt,dtop,dbot)>0
        lm=np.zeros((H1,W1),dtype=bool); lm[y0:y1,x0:x1]=fmask; lms1.append(lm)
        smfull=np.zeros((H1,W1),dtype=bool); smfull[y:y+h,x:x+w]=smask
        outside_final=smfull.copy(); outside_final[b:d,a:c]=False
        equal=np.all(fa1==sa1,axis=2)
        residue1 += count(outside_final & equal)
    checks1.append({
      "idx":i,"source":expected1[i][0],"korean":expected1[i][1],
      "independent_source_bbox":sbb,"producer_source_bbox":declared_s,"source_bbox_exact_match_producer":se,
      "independent_localized_bbox":fbb,"producer_localized_bbox":declared_f,"localized_bbox_exact_match_producer":fe,
      "delta_left":dlft,"delta_right":drgt,"delta_top":dtop,"delta_bottom":dbot,
      "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL","positive_margin":"PASS" if positive else "FAIL"
    })
changed1=np.any(fa1!=sa1,axis=2); ach1=fa1[:,:,3]!=sa1[:,:,3]; intro1=fa1[:,:,3]>sa1[:,:,3]
machine1={
 "decoded_changed_outside_union_source_bboxes":count(changed1&~allowed1),
 "alpha_changed_outside_union_source_bboxes":count(ach1&~allowed1),
 "introduced_visible_outside_union_source_bboxes":count(intro1&~allowed1),
 "source_residue_exact_pixels_outside_localized_bboxes":residue1
}
over1=0; near1=0
for i,mi in enumerate(lms1):
    yy,xx=np.nonzero(mi); dil=np.zeros_like(mi)
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            ys=np.clip(yy+dy,0,H1-1); xs=np.clip(xx+dx,0,W1-1); dil[ys,xs]=True
    for mj in lms1[i+1:]:
        over1+=count(mi&mj); near1+=count(dil&mj)
machine1["localized_overlap_pixels"]=over1
machine1["localized_1px_touch_pixels"]=near1
ps=np.frombuffer(sb1[128:],dtype=np.uint8).reshape((-1,16)); pf=np.frombuffer(cb1[128:],dtype=np.uint8).reshape((-1,16))
bc=np.any(ps!=pf,axis=1)
ab=np.zeros((H1//4,W1//4),dtype=bool)
for r in checks1:
    x0,y0,x1,y1=r["independent_source_bbox"]; ry0=H1-y1; ry1=H1-y0
    ab[ry0//4:(ry1+3)//4,x0//4:(x1+3)//4]=True
machine1["changed_dxt5_blocks"]=int(np.count_nonzero(bc))
machine1["changed_dxt5_blocks_wholly_outside_allowed"]=int(np.count_nonzero(bc & ~ab.reshape(-1)))
rowpass1=sum(1 for r in checks1 if r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS")
zero1=["decoded_changed_outside_union_source_bboxes","alpha_changed_outside_union_source_bboxes","introduced_visible_outside_union_source_bboxes","source_residue_exact_pixels_outside_localized_bboxes","localized_overlap_pixels","localized_1px_touch_pixels","changed_dxt5_blocks_wholly_outside_allowed"]
status1="PASS" if rowpass1==38 and source_exact1 and final_exact1 and semantic1 and all(machine1[k]==0 for k in zero1) else "FAIL"

cards=[]
for r in checks1:
    x0,y0,x1,y1=r["independent_source_bbox"]; pad=8
    crop=(max(0,x0-pad),max(0,y0-pad),min(W1,x1+pad),min(H1,y1+pad))
    a=comp(src1).crop(crop); b=comp(fin1).crop(crop); cw=max(a.width,b.width); ch=max(a.height,b.height)
    card=Image.new("RGB",(cw*2+8,ch+24),"white"); card.paste(a,(0,24)); card.paste(b,(cw+8,24))
    d=ImageDraw.Draw(card); d.text((2,3),f"idx{r['idx']} {r['source']}",fill="black"); d.text((cw+10,3),r["korean"],fill="black")
    cards.append(card)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+3*(len(cards)-1)),"white")
yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+3
if sheet.width>1800: sheet=sheet.resize((1800,round(sheet.height*1800/sheet.width)),Image.Resampling.LANCZOS)
sheet.save(out1/"C201_TARGET_CONTACTS.jpg",quality=96)
rawcard=Image.new("RGB",(2048,1050),"white")
rawcard.paste(comp(raw_src1).resize((1024,1024),Image.Resampling.LANCZOS),(0,24))
rawcard.paste(comp(raw_fin1).resize((1024,1024),Image.Resampling.LANCZOS),(1024,24))
d=ImageDraw.Draw(rawcard); d.text((4,4),"SOURCE_RAW_MIRROR_Y",fill="black"); d.text((1028,4),"FINAL_RAW_MIRROR_Y",fill="black")
rawcard.save(out1/"C201_RAW_COMPARE.jpg",quality=95)
report1={
 "schema_version":1,"role":"C","run":run1,"qa_id":"C201","queue_index":161,"asset":asset1,
 "producer_run":pr1["run"],"source_sha256":sp1["sha256"],"candidate_sha256":pr1["candidate_sha256"],
 "structure":{**meta_s1,"header_exact":cb1[:128]==sb1[:128],"raw_orientation":"mirror_y"},
 "semantic_policy_pass":semantic1,"source_bbox_exact_match_all":source_exact1,"candidate_bbox_exact_match_all":final_exact1,
 "row_checks":checks1,"row_gate":f"{rowpass1}/38 PASS","machine_checks":machine1,"machine_status":status1,
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","decision":"PENDING_CONTROLLER_VISUAL_QA" if status1=="PASS" else "C201_REWORK_REQUIRED_MACHINE_OR_POLICY_GATE",
 "runtime_validation":"UNTESTED",
 "preview_files":[f"localization/graphics/role_C/{run1}/C201_TARGET_CONTACTS.jpg",f"localization/graphics/role_C/{run1}/C201_RAW_COMPARE.jpg"]
}
(out1/"C201_55B57CDE_MACHINE_QA.json").write_text(json.dumps(report1,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"C201_55B57CDE.json").write_text(json.dumps({
 "run":run1,"qa_id":"C201","index":161,"asset":"55B57CDE","candidate_sha256":pr1["candidate_sha256"],
 "machine_status":status1,"row_gate":report1["row_gate"],"semantic_policy_pass":semantic1,
 "source_bbox_exact_match_all":source_exact1,"candidate_bbox_exact_match_all":final_exact1,
 "machine_checks":machine1,"report":f"localization/graphics/role_C/{run1}/C201_55B57CDE_MACHINE_QA.json","runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

# ---------------------------------------------------------------------------
# C202: independent B148 8215FD25 template-based revalidation
# ---------------------------------------------------------------------------
run2="20261005-C202-8215FD25"
out2=repo/"localization/graphics/role_C"/run2
out2.mkdir(parents=True,exist_ok=True)
producer2=repo/"localization/graphics/role_B/20261005-B-PRODUCTION148-8215-C200-TEMPLATE/B148_8215_REPORT.json"
pr2=json.loads(producer2.read_text(encoding="utf-8"))
cand2=repo/pr2["candidate_path"]
asset2=pr2["asset"]
sp2=pr2["source_provenance"]
tmp2=Path("/tmp/c202"); tmp2.mkdir(exist_ok=True)
srcdds2=tmp2/"source.dds"
folder2=asset2.split("/")[-2]; name2=asset2.split("/")[-1]
base2=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{sp2['commit']}"
dl(base2+f"/Release/{folder2}/{name2}",srcdds2)
sb2=srcdds2.read_bytes(); cb2=cand2.read_bytes()
if sha256_bytes(sb2)!=sp2["source_sha256"]: raise RuntimeError(("C202 source sha drift",sha256_bytes(sb2),sp2["source_sha256"]))
if sha256_bytes(cb2)!=pr2["candidate_sha256"]: raise RuntimeError(("C202 candidate sha drift",sha256_bytes(cb2),pr2["candidate_sha256"]))
meta_s2=dds_meta(sb2); meta_c2=dds_meta(cb2)
if meta_s2["width"]!=4096 or meta_s2["height"]!=2048 or meta_c2!=meta_s2 or cb2[:128]!=sb2[:128]:
    raise RuntimeError(("C202 DDS structure/header drift",meta_s2,meta_c2,cb2[:128]==sb2[:128]))
raw_src2=Image.open(srcdds2).convert("RGBA"); raw_fin2=Image.open(cand2).convert("RGBA")
src2=raw_src2.transpose(Image.Transpose.FLIP_TOP_BOTTOM); fin2=raw_fin2.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa2=np.asarray(src2,dtype=np.uint8); fa2=np.asarray(fin2,dtype=np.uint8)
H2,W2=sa2.shape[:2]
clean2=Image.open(repo/"localization/graphics/role_B/20261005-B-PRODUCTION148-8215-C200-TEMPLATE/B148_CLEAN_PLATE.png").convert("RGBA")
finalpng2=Image.open(repo/"localization/graphics/role_B/20261005-B-PRODUCTION148-8215-C200-TEMPLATE/B148_FINAL_READABLE.png").convert("RGBA")
sourcepng2=Image.open(repo/"localization/graphics/role_B/20261005-B-PRODUCTION148-8215-C200-TEMPLATE/B148_SOURCE_READABLE.png").convert("RGBA")
ca2=np.asarray(clean2,dtype=np.uint8); fpa2=np.asarray(finalpng2,dtype=np.uint8); spa2=np.asarray(sourcepng2,dtype=np.uint8)
decode_source_png_exact=int(np.count_nonzero(np.any(sa2!=spa2,axis=2)))
decode_final_png_exact=int(np.count_nonzero(np.any(fa2!=fpa2,axis=2)))
rows2=pr2["rows"]
allowed2=np.zeros((H2,W2),dtype=bool); lms2=[]; checks2=[]
renderdiff=np.any(fpa2!=ca2,axis=2)
for row in rows2:
    x0,y0,x1,y1=map(int,row["original_bbox"]); allowed2[y0:y1,x0:x1]=True
    rm=renderdiff[y0:y1,x0:x1]
    bb=bbox(rm)
    fbb=None if bb is None else [bb[0]+x0,bb[1]+y0,bb[2]+x0,bb[3]+y0]
    decl=list(map(int,row["localized_bbox"]))
    exact=(fbb==decl)
    if fbb is None:
        contain=size_ok=positive=False; dlft=drgt=dtop=dbot=-1
    else:
        a,b,c,d=fbb; dlft=a-x0; drgt=x1-c; dtop=b-y0; dbot=y1-d
        contain=a>=x0 and b>=y0 and c<=x1 and d<=y1
        size_ok=(c-a)<=x1-x0 and (d-b)<=y1-y0
        positive=min(dlft,drgt,dtop,dbot)>0
        lm=np.zeros((H2,W2),dtype=bool); lm[y0:y1,x0:x1]=rm; lms2.append(lm)
    checks2.append({
      "region_idx":int(row["region_idx"]),"source":row["source"],"korean":row["korean"],
      "original_bbox":list(map(int,row["original_bbox"])),"independent_localized_bbox":fbb,
      "producer_localized_bbox":decl,"localized_bbox_exact_match_producer":exact,
      "delta_left":dlft,"delta_right":drgt,"delta_top":dtop,"delta_bottom":dbot,
      "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL","positive_margin":"PASS" if positive else "FAIL"
    })
changed2=np.any(fa2!=sa2,axis=2); ach2=fa2[:,:,3]!=sa2[:,:,3]
machine2={
 "decoded_source_vs_producer_source_png_diff_pixels":decode_source_png_exact,
 "decoded_final_vs_producer_final_png_diff_pixels":decode_final_png_exact,
 "decoded_changed_outside_union_source_bboxes":count(changed2&~allowed2),
 "alpha_changed_outside_union_source_bboxes":count(ach2&~allowed2),
 "localized_render_outside_union_source_bboxes":count(renderdiff&~allowed2)
}
over2=0; near2=0
for i,mi in enumerate(lms2):
    yy,xx=np.nonzero(mi); dil=np.zeros_like(mi)
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            ys=np.clip(yy+dy,0,H2-1); xs=np.clip(xx+dx,0,W2-1); dil[ys,xs]=True
    for mj in lms2[i+1:]:
        over2+=count(mi&mj); near2+=count(dil&mj)
machine2["localized_overlap_pixels"]=over2; machine2["localized_1px_touch_pixels"]=near2

# Independent exact template-copy check against C193-approved B137 clean starburst.
tmpl=Image.open(repo/"localization/graphics/role_B/20261005-B-PRODUCTION137/63C_CLEAN_PLATE.png").convert("RGBA")
ta=np.asarray(tmpl,dtype=np.uint8)
px0,py0,px1,py1=map(int,pr2["clean_reconstruction"]["idx1_template_patch_bbox"])
sx=int(pr2["clean_reconstruction"]["idx1_template_alignment"]["shift_x"])
sy=int(pr2["clean_reconstruction"]["idx1_template_alignment"]["shift_y"])
refpatch=ta[py0-sy:py1-sy,px0-sx:px1-sx]
curpatch=ca2[py0:py1,px0:px1]
if refpatch.shape!=curpatch.shape: raise RuntimeError(("C202 template patch shape",refpatch.shape,curpatch.shape))
machine2["template_patch_diff_pixels"]=count(np.any(refpatch!=curpatch,axis=2))
machine2["template_patch_max_channel_delta"]=int(np.max(np.abs(refpatch.astype(np.int16)-curpatch.astype(np.int16))))
rowpass2=sum(1 for r in checks2 if r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS" and r["localized_bbox_exact_match_producer"])
zero2=["decoded_source_vs_producer_source_png_diff_pixels","decoded_final_vs_producer_final_png_diff_pixels","decoded_changed_outside_union_source_bboxes","alpha_changed_outside_union_source_bboxes","localized_render_outside_union_source_bboxes","localized_overlap_pixels","localized_1px_touch_pixels","template_patch_diff_pixels","template_patch_max_channel_delta"]
status2="PASS" if rowpass2==2 and all(machine2[k]==0 for k in zero2) else "FAIL"

focus=Image.new("RGB",(1800,650),"white")
for j,(lab,im) in enumerate([("SOURCE",src2),("CLEAN",clean2),("FINAL",fin2)]):
    crop=comp(im).crop((1600,90,2420,340)).resize((600,600),Image.Resampling.LANCZOS)
    focus.paste(crop,(j*600,40)); ImageDraw.Draw(focus).text((j*600+5,5),lab,fill="black")
focus.save(out2/"C202_STARBURST_FOCUS.jpg",quality=96)
report2={
 "schema_version":1,"role":"C","run":run2,"qa_id":"C202","queue_index":30,"asset":asset2,
 "producer_run":pr2["run"],"source_sha256":sp2["source_sha256"],"candidate_sha256":pr2["candidate_sha256"],
 "structure":{**meta_s2,"header_exact":cb2[:128]==sb2[:128],"raw_orientation":"mirror_y"},
 "semantic_binding":"PASS_TOTAL_RANK_X2_TO_종합_랭킹",
 "row_checks":checks2,"row_gate":f"{rowpass2}/2 PASS","machine_checks":machine2,"machine_status":status2,
 "template_provenance":{"source":"C193-approved B137 63C_CLEAN_PLATE.png","shift":[sx,sy],"target_patch":[px0,py0,px1,py1]},
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","decision":"PENDING_CONTROLLER_VISUAL_QA" if status2=="PASS" else "C202_REWORK_REQUIRED_MACHINE_OR_POLICY_GATE",
 "runtime_validation":"UNTESTED","preview_files":[f"localization/graphics/role_C/{run2}/C202_STARBURST_FOCUS.jpg"]
}
(out2/"C202_8215FD25_MACHINE_QA.json").write_text(json.dumps(report2,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"C202_8215FD25.json").write_text(json.dumps({
 "run":run2,"qa_id":"C202","index":30,"asset":"8215FD25","candidate_sha256":pr2["candidate_sha256"],
 "machine_status":status2,"row_gate":report2["row_gate"],"machine_checks":machine2,
 "report":f"localization/graphics/role_C/{run2}/C202_8215FD25_MACHINE_QA.json","runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

print(json.dumps({"C201":{"machine_status":status1,"row_gate":report1["row_gate"],"machine_checks":machine1},"C202":{"machine_status":status2,"row_gate":report2["row_gate"],"machine_checks":machine2}},ensure_ascii=False),flush=True)
