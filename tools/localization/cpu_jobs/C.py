#!/usr/bin/env python3
import os, json, hashlib, struct, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C197-55B57CDE"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

producer=repo/"localization/graphics/role_A/20261005-A-PRODUCTION54-DXT5/A54_55B57CDE_REPORT.json"
pr=json.loads(producer.read_text(encoding="utf-8"))
candidate=repo/pr["candidate_path"]
asset=pr["asset"]
sp=pr["source_provenance"]

tmp=Path("/tmp/c197")
tmp.mkdir(exist_ok=True)
srcdds=tmp/"source.dds"
atlasp=tmp/"atlas.json"
folder=asset.split("/")[-2]
name=asset.split("/")[-1]
base=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{sp['commit']}"
urllib.request.urlretrieve(base+f"/Release/{folder}/{name}",srcdds)
urllib.request.urlretrieve(base+f"/Original%20(PC)/Original%20(Tweaks%20dumps)/{folder}/4x_{name[:-4]}_atlas.json",atlasp)

def sha(b): return hashlib.sha256(b).hexdigest()
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

sb=srcdds.read_bytes(); cb=candidate.read_bytes()
if sha(sb)!=sp["sha256"]: raise RuntimeError(("source sha drift",sha(sb),sp["sha256"]))
if sha(cb)!=pr["candidate_sha256"]: raise RuntimeError(("candidate sha drift",sha(cb),pr["candidate_sha256"]))
sm=dds_meta(sb); cm=dds_meta(cb)
if sm!={"width":2048,"height":2048,"mipmaps":1,"format":"DXT5"} or cm!=sm or cb[:128]!=sb[:128]:
    raise RuntimeError(("DDS structure/header drift",sm,cm,cb[:128]==sb[:128]))

raw_src=Image.open(srcdds).convert("RGBA")
raw_fin=Image.open(candidate).convert("RGBA")
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
fin=raw_fin.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(fin,dtype=np.uint8)
H,W=sa.shape[:2]

atlas=json.loads(atlasp.read_text(encoding="utf-8"))
regs={int(r["idx"]):r for r in atlas["regions"]}
rows={int(e["idx"]):e for e in pr["elements"]}
if set(regs)!=set(range(38)) or set(rows)!=set(range(38)):
    raise RuntimeError(("region/row set mismatch",sorted(regs),sorted(rows)))

expected=[
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
semantic_policy_pass=all((rows[i]["source"].upper(),rows[i]["korean"])==expected[i] for i in range(38))

allowed=np.zeros((H,W),dtype=bool)
source_masks=[]
localized_masks=[]
checks=[]
source_bbox_exact_all=True
localized_bbox_exact_all=True
source_residue_outside_localized_bbox=0

for i in range(38):
    reg=regs[i]
    x,y,w,h=map(int,reg["rect"])
    sc=sa[y:y+h,x:x+w]
    smask=sc[:,:,3]>0
    bb0=bbox(smask)
    if bb0 is None: raise RuntimeError(("empty source alpha",i))
    sbb=[bb0[0]+x,bb0[1]+y,bb0[2]+x,bb0[3]+y]
    declared_source=list(map(int,rows[i]["original_bbox"]))
    source_exact=(sbb==declared_source)
    source_bbox_exact_all &= source_exact
    x0,y0,x1,y1=sbb
    allowed[y0:y1,x0:x1]=True

    fc=fa[y0:y1,x0:x1]
    fmask=fc[:,:,3]>0
    fbb0=bbox(fmask)
    fbb=None if fbb0 is None else [fbb0[0]+x0,fbb0[1]+y0,fbb0[2]+x0,fbb0[3]+y0]
    declared_final=list(map(int,rows[i]["localized_bbox"]))
    final_exact=(fbb==declared_final)
    localized_bbox_exact_all &= final_exact
    if fbb is None:
        dl=dr=dt=db=-1; contain=size_ok=positive=False
    else:
        a,b,c,d=fbb
        dl=a-x0; dr=x1-c; dt=b-y0; db=y1-d
        contain=(a>=x0 and b>=y0 and c<=x1 and d<=y1)
        size_ok=((c-a)<=x1-x0 and (d-b)<=y1-y0)
        positive=min(dl,dr,dt,db)>0

        lm=np.zeros((H,W),dtype=bool)
        lm[y0:y1,x0:x1]=fmask
        localized_masks.append(lm)

        # Independent residue audit: exact source-visible pixels surviving outside the
        # final Hangul bbox are unequivocal source residue.
        smfull=np.zeros((H,W),dtype=bool)
        smfull[y:y+h,x:x+w]=smask
        source_masks.append(smfull)
        outside_final=smfull.copy()
        outside_final[b:d,a:c]=False
        equal=np.all(fa==sa,axis=2)
        source_residue_outside_localized_bbox += count(outside_final & equal)

    checks.append({
      "idx":i,"source":expected[i][0],"korean":expected[i][1],
      "atlas_rect":[x,y,w,h],
      "independent_source_bbox":sbb,
      "producer_source_bbox":declared_source,
      "source_bbox_exact_match_producer":source_exact,
      "independent_localized_bbox":fbb,
      "producer_localized_bbox":declared_final,
      "localized_bbox_exact_match_producer":final_exact,
      "delta_left":dl,"delta_right":dr,"delta_top":dt,"delta_bottom":db,
      "containment":"PASS" if contain else "FAIL",
      "size_ceiling":"PASS" if size_ok else "FAIL",
      "positive_margin":"PASS" if positive else "FAIL"
    })

changed=np.any(fa!=sa,axis=2)
alpha_changed=fa[:,:,3]!=sa[:,:,3]
introduced=fa[:,:,3]>sa[:,:,3]
machine={
 "decoded_changed_outside_union_source_bboxes":count(changed&~allowed),
 "alpha_changed_outside_union_source_bboxes":count(alpha_changed&~allowed),
 "introduced_visible_outside_union_source_bboxes":count(introduced&~allowed),
 "source_residue_exact_pixels_outside_localized_bboxes":source_residue_outside_localized_bbox
}
overlap=0; near=0
for i,mi in enumerate(localized_masks):
    yy,xx=np.nonzero(mi)
    dil=np.zeros_like(mi)
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            ys=np.clip(yy+dy,0,H-1); xs=np.clip(xx+dx,0,W-1); dil[ys,xs]=True
    for mj in localized_masks[i+1:]:
        overlap+=count(mi&mj)
        near+=count(dil&mj)
machine["localized_overlap_pixels"]=overlap
machine["localized_1px_touch_pixels"]=near

# DXT5 payload audit in raw mirror_y block coordinates.
payload_src=np.frombuffer(sb[128:],dtype=np.uint8).reshape((-1,16))
payload_fin=np.frombuffer(cb[128:],dtype=np.uint8).reshape((-1,16))
block_changed=np.any(payload_src!=payload_fin,axis=1)
allowed_blocks=np.zeros((H//4,W//4),dtype=bool)
for r in checks:
    x0,y0,x1,y1=r["independent_source_bbox"]
    ry0=H-y1; ry1=H-y0
    allowed_blocks[ry0//4:(ry1+3)//4,x0//4:(x1+3)//4]=True
machine["changed_dxt5_blocks"]=int(np.count_nonzero(block_changed))
machine["changed_dxt5_blocks_wholly_outside_allowed"]=int(np.count_nonzero(block_changed & ~allowed_blocks.reshape(-1)))

row_gate=all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS" for r in checks)
zero_keys=[
 "decoded_changed_outside_union_source_bboxes",
 "alpha_changed_outside_union_source_bboxes",
 "introduced_visible_outside_union_source_bboxes",
 "source_residue_exact_pixels_outside_localized_bboxes",
 "localized_overlap_pixels","localized_1px_touch_pixels",
 "changed_dxt5_blocks_wholly_outside_allowed"
]
machine_status="PASS" if row_gate and source_bbox_exact_all and localized_bbox_exact_all and semantic_policy_pass and all(machine[k]==0 for k in zero_keys) else "FAIL"

# Visual evidence.
cards=[]
for r in checks:
    x0,y0,x1,y1=r["independent_source_bbox"]; pad=8
    crop=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    a=comp(src).crop(crop); b=comp(fin).crop(crop)
    cw=max(a.width,b.width); ch=max(a.height,b.height)
    card=Image.new("RGB",(cw*2+8,ch+24),"white")
    card.paste(a,(0,24)); card.paste(b,(cw+8,24))
    d=ImageDraw.Draw(card); d.text((2,3),f"idx{r['idx']} {r['source']}",fill="black"); d.text((cw+10,3),r["korean"],fill="black")
    cards.append(card)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+3*(len(cards)-1)),"white")
yy=0
for c in cards:
    sheet.paste(c,(0,yy)); yy+=c.height+3
if sheet.width>1800:
    sheet=sheet.resize((1800,round(sheet.height*1800/sheet.width)),Image.Resampling.LANCZOS)
sheet.save(out/"C197_TARGET_CONTACTS.jpg",quality=96)

overview=Image.new("RGB",(2048,1050),"white")
overview.paste(comp(src).resize((1024,1024),Image.Resampling.LANCZOS),(0,24))
overview.paste(comp(fin).resize((1024,1024),Image.Resampling.LANCZOS),(1024,24))
d=ImageDraw.Draw(overview); d.text((4,4),"SOURCE_READABLE",fill="black"); d.text((1028,4),"FINAL_READABLE",fill="black")
overview.save(out/"C197_SOURCE_FINAL_OVERVIEW.jpg",quality=95)

rawcard=Image.new("RGB",(2048,1050),"white")
rawcard.paste(comp(raw_src).resize((1024,1024),Image.Resampling.LANCZOS),(0,24))
rawcard.paste(comp(raw_fin).resize((1024,1024),Image.Resampling.LANCZOS),(1024,24))
d=ImageDraw.Draw(rawcard); d.text((4,4),"SOURCE_RAW_MIRROR_Y",fill="black"); d.text((1028,4),"FINAL_RAW_MIRROR_Y",fill="black")
rawcard.save(out/"C197_RAW_COMPARE.jpg",quality=95)

report={
 "schema_version":1,"role":"C","run":run,"qa_id":"C197","queue_index":161,"asset":asset,
 "producer_run":pr["run"],"source_sha256":sp["sha256"],"candidate_sha256":pr["candidate_sha256"],
 "structure":{**sm,"header_exact":cb[:128]==sb[:128],"raw_orientation":"mirror_y"},
 "semantic_policy_pass":semantic_policy_pass,
 "semantic_expected":{str(i):{"source":expected[i][0],"korean":expected[i][1]} for i in range(38)},
 "source_bbox_exact_match_all":source_bbox_exact_all,
 "candidate_bbox_exact_match_all":localized_bbox_exact_all,
 "row_checks":checks,
 "row_gate":f"{sum(1 for r in checks if r['containment']=='PASS' and r['size_ceiling']=='PASS' and r['positive_margin']=='PASS')}/{len(checks)} PASS",
 "machine_checks":machine,
 "machine_status":machine_status,
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "decision":"PENDING_CONTROLLER_VISUAL_QA" if machine_status=="PASS" else "C197_REWORK_REQUIRED_MACHINE_OR_POLICY_GATE",
 "runtime_validation":"UNTESTED",
 "preview_files":[
  f"localization/graphics/role_C/{run}/C197_TARGET_CONTACTS.jpg",
  f"localization/graphics/role_C/{run}/C197_SOURCE_FINAL_OVERVIEW.jpg",
  f"localization/graphics/role_C/{run}/C197_RAW_COMPARE.jpg"
 ]
}
(out/"C197_55B57CDE_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"C197_55B57CDE.json").write_text(json.dumps({
 "run":run,"qa_id":"C197","index":161,"asset":"55B57CDE",
 "candidate_sha256":pr["candidate_sha256"],"machine_status":machine_status,
 "row_gate":report["row_gate"],"semantic_policy_pass":semantic_policy_pass,
 "source_bbox_exact_match_all":source_bbox_exact_all,"candidate_bbox_exact_match_all":localized_bbox_exact_all,
 "machine_checks":machine,
 "report":f"localization/graphics/role_C/{run}/C197_55B57CDE_MACHINE_QA.json",
 "runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"qa_id":"C197","machine_status":machine_status,"row_gate":report["row_gate"],"semantic_policy_pass":semantic_policy_pass,"machine_checks":machine},ensure_ascii=False),flush=True)
