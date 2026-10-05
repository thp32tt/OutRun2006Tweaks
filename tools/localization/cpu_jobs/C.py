#!/usr/bin/env python3
import os, json, hashlib, struct, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C194-C598919A"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

producer=repo/"localization/graphics/role_B/20261005-B-PRODUCTION139-C598-SOLVER-FIX/B139_C598_REPORT.json"
pr=json.loads(producer.read_text(encoding="utf-8"))
candidate=repo/pr["candidate_path"]
sp=pr["source_provenance"]
asset=pr["asset"]

tmp=Path("/tmp/c194")
tmp.mkdir(exist_ok=True)
srcdds=tmp/"source.dds"
atlas=tmp/"atlas.json"
base=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{sp['commit']}"
folder=asset.split("/")[-2]
name=asset.split("/")[-1]
urllib.request.urlretrieve(base+f"/Release/{folder}/{name}",srcdds)
urllib.request.urlretrieve(base+f"/Original%20(PC)/Original%20(Tweaks%20dumps)/{folder}/4x_{name[:-4]}_atlas.json",atlas)

def sha(b): return hashlib.sha256(b).hexdigest()
def count(m): return int(np.count_nonzero(m))
def bbox(m):
    yy,xx=np.nonzero(m)
    return None if len(xx)==0 else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def dds_meta(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]
    w=struct.unpack_from("<I",b,16)[0]
    mips=struct.unpack_from("<I",b,28)[0]
    fourcc=b[84:88]
    return w,h,mips,fourcc.decode("ascii","replace")
def comp(im,bg=(54,54,54,255)):
    z=Image.new("RGBA",im.size,bg)
    z.alpha_composite(im)
    return z.convert("RGB")

sb=srcdds.read_bytes()
cb=candidate.read_bytes()
if sha(sb)!=sp["source_sha256"]: raise RuntimeError(("source sha drift",sha(sb),sp["source_sha256"]))
if sha(cb)!=pr["candidate_sha256"]: raise RuntimeError(("candidate sha drift",sha(cb),pr["candidate_sha256"]))
sm=dds_meta(sb); cm=dds_meta(cb)
if sm!=(4096,4096,1,"DXT5") or cm!=sm or cb[:128]!=sb[:128]:
    raise RuntimeError(("DDS structure/header drift",sm,cm,cb[:128]==sb[:128]))

raw_src=Image.open(srcdds).convert("RGBA")
raw_final=Image.open(candidate).convert("RGBA")
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
final=raw_final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
fa=np.asarray(final,dtype=np.uint8)
H,W=sa.shape[:2]

atlas_obj=json.loads(atlas.read_text(encoding="utf-8"))
atlas_regs={int(r["idx"]):r for r in atlas_obj["regions"]}
expected_stage={
 79:("Cape Way","케이프 웨이"),
 80:("Imperial Avenue","임페리얼 애비뉴"),
 81:("Ancient Ruins","에인션트 루인스"),
 82:("Metropolis","메트로폴리스"),
 83:("Tulip Garden","튤립 가든"),
 84:("Skyscrapers","스카이스크레이퍼스"),
 85:("Milky Way","밀키 웨이"),
 86:("Floral Village","플로럴 빌리지"),
 87:("Legend","레전드"),
 88:("Giant Statues","자이언트 스태추스"),
}
stage_rows={int(e["region_idx"]):(e["source"],e["korean"]) for e in pr["elements"] if e["kind"]=="stage"}
semantic_policy_pass=(stage_rows==expected_stage)

allowed=np.zeros((H,W),dtype=bool)
row_checks=[]
localized_masks=[]
all_declared=True
for e in pr["elements"]:
    x0,y0,x1,y1=map(int,e["original_bbox"])
    if not (0<=x0<x1<=W and 0<=y0<y1<=H): raise RuntimeError(("bad source bbox",e["region_idx"],e["original_bbox"]))
    allowed[y0:y1,x0:x1]=True
    vis=fa[y0:y1,x0:x1,3]>1
    bb=bbox(vis)
    actual=None if bb is None else [bb[0]+x0,bb[1]+y0,bb[2]+x0,bb[3]+y0]
    if actual:
        a,b,c,d=actual
        dl=a-x0; dr=x1-c; dt=b-y0; db=y1-d
        contain=(a>=x0 and b>=y0 and c<=x1 and d<=y1)
        size=((c-a)<=x1-x0 and (d-b)<=y1-y0)
        positive=min(dl,dr,dt,db)>0
    else:
        dl=dr=dt=db=-1; contain=size=positive=False
    declared=list(map(int,e["localized_bbox"]))
    exact=(actual==declared)
    all_declared=all_declared and exact
    lm=np.zeros((H,W),dtype=bool); lm[y0:y1,x0:x1]=vis
    localized_masks.append(lm)
    row_checks.append({
      "region_idx":int(e["region_idx"]),"source":e["source"],"korean":e["korean"],"kind":e["kind"],
      "original_bbox":[x0,y0,x1,y1],"producer_localized_bbox":declared,
      "independent_localized_bbox":actual,"bbox_exact_match_producer":exact,
      "delta_left":dl,"delta_right":dr,"delta_top":dt,"delta_bottom":db,
      "containment":"PASS" if contain else "FAIL",
      "size_ceiling":"PASS" if size else "FAIL",
      "positive_margin":"PASS" if positive else "FAIL"
    })

changed=np.any(fa!=sa,axis=2)
alpha_changed=fa[:,:,3]!=sa[:,:,3]
introduced=(fa[:,:,3]>sa[:,:,3])
machine={
 "decoded_changed_outside_union_source_bboxes":count(changed&~allowed),
 "alpha_changed_outside_union_source_bboxes":count(alpha_changed&~allowed),
 "introduced_visible_outside_union_source_bboxes":count(introduced&~allowed),
}
overlap=0
for i,mi in enumerate(localized_masks):
    for mj in localized_masks[i+1:]:
        overlap+=count(mi&mj)
machine["localized_pair_overlap_pixels"]=overlap

# Independent DXT5 block audit: every modified 4x4 block must intersect an allowed exact source bbox.
payload_src=np.frombuffer(sb[128:],dtype=np.uint8).reshape((-1,16))
payload_fin=np.frombuffer(cb[128:],dtype=np.uint8).reshape((-1,16))
block_changed=np.any(payload_src!=payload_fin,axis=1)
bw=W//4
allowed_blocks=np.zeros((H//4,W//4),dtype=bool)
for e in pr["elements"]:
    x0,y0,x1,y1=map(int,e["original_bbox"])
    # DDS payload is raw mirror_y while producer bboxes are readable orientation.
    # Convert readable Y bounds to raw block-row bounds before compressed-block audit.
    ry0=H-y1
    ry1=H-y0
    allowed_blocks[ry0//4:(ry1+3)//4,x0//4:(x1+3)//4]=True
machine["changed_dxt5_blocks"]=int(np.count_nonzero(block_changed))
machine["changed_dxt5_blocks_wholly_outside_allowed"]=int(np.count_nonzero(block_changed & ~allowed_blocks.reshape(-1)))

row_gate=all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS" for r in row_checks)
hard_zero=[
 "decoded_changed_outside_union_source_bboxes",
 "alpha_changed_outside_union_source_bboxes",
 "introduced_visible_outside_union_source_bboxes",
 "localized_pair_overlap_pixels",
 "changed_dxt5_blocks_wholly_outside_allowed"
]
machine_status="PASS" if row_gate and all(machine[k]==0 for k in hard_zero) else "FAIL"

# Verify protected atlas regions from the producer policy are outside exact target bboxes.
target_indices={int(e["region_idx"]) for e in pr["elements"]}
protected_indices=[i for i in list(range(31,40))+list(range(50,64))+list(range(66,79))+list(range(89,106)) if i in atlas_regs]
protected_overlap={}
for idx in protected_indices:
    x,y,w,h=map(int,atlas_regs[idx]["rect"])
    protected_overlap[str(idx)]=count(allowed[y:y+h,x:x+w])
protected_geometry_pass=all(v==0 for v in protected_overlap.values())

# Visual evidence: full readable overview, raw mirror orientation, and per-element contacts.
overview=Image.new("RGB",(2048,2076),"white")
for i,(lab,im) in enumerate((("SOURCE_READABLE",src),("FINAL_READABLE",final))):
    z=comp(im).resize((2048,2048),Image.Resampling.LANCZOS)
    yy=i*0
# store side-by-side instead to keep evidence compact
overview=Image.new("RGB",(2048,1055),"white")
sd=comp(src).resize((1024,1024),Image.Resampling.LANCZOS)
fd=comp(final).resize((1024,1024),Image.Resampling.LANCZOS)
overview.paste(sd,(0,28)); overview.paste(fd,(1024,28))
od=ImageDraw.Draw(overview); od.text((5,5),"SOURCE_READABLE",fill="black"); od.text((1029,5),"FINAL_READABLE",fill="black")
overview.save(out/"C194_SOURCE_FINAL_OVERVIEW.jpg",quality=95)

rawcard=Image.new("RGB",(2048,1055),"white")
rs=comp(raw_src).resize((1024,1024),Image.Resampling.LANCZOS)
rf=comp(raw_final).resize((1024,1024),Image.Resampling.LANCZOS)
rawcard.paste(rs,(0,28)); rawcard.paste(rf,(1024,28))
rd=ImageDraw.Draw(rawcard); rd.text((5,5),"SOURCE_RAW_MIRROR_Y",fill="black"); rd.text((1029,5),"FINAL_RAW_MIRROR_Y",fill="black")
rawcard.save(out/"C194_RAW_COMPARE.jpg",quality=95)

cards=[]
font=ImageFont.load_default()
for r in row_checks:
    x0,y0,x1,y1=r["original_bbox"]; pad=12
    crop=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    a=comp(src).crop(crop); b=comp(final).crop(crop)
    cw=max(a.width,b.width); ch=max(a.height,b.height)
    card=Image.new("RGB",(cw*2+8,ch+30),"white")
    card.paste(a,(2,28)); card.paste(b,(cw+6,28))
    d=ImageDraw.Draw(card)
    d.text((3,3),f"SRC idx{r['region_idx']} {r['source']}",fill="black",font=font)
    d.text((cw+7,3),f"FINAL {r['korean']}",fill="black",font=font)
    cards.append(card)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+4*(len(cards)-1)),"white")
yy=0
for c in cards:
    sheet.paste(c,(0,yy)); yy+=c.height+4
if sheet.width>1800:
    sheet=sheet.resize((1800,round(sheet.height*1800/sheet.width)),Image.Resampling.LANCZOS)
sheet.save(out/"C194_TARGET_CONTACTS.jpg",quality=96)

report={
 "schema_version":1,"role":"C","run":run,"qa_id":"C194","queue_index":86,"asset":asset,
 "producer_run":pr["run"],"source_sha256":sp["source_sha256"],"candidate_sha256":pr["candidate_sha256"],
 "structure":{"dimensions":[W,H],"format":"DXT5","mipmaps":sm[2],"raw_orientation":"mirror_y","header_exact":cb[:128]==sb[:128]},
 "semantic_stage_mapping_expected":{str(k):{"source":v[0],"korean":v[1]} for k,v in expected_stage.items()},
 "semantic_stage_mapping_seen":{str(k):{"source":v[0],"korean":v[1]} for k,v in stage_rows.items()},
 "semantic_policy_pass":semantic_policy_pass,
 "row_checks":row_checks,"row_gate":f"{sum(1 for r in row_checks if r['containment']=='PASS' and r['size_ceiling']=='PASS' and r['positive_margin']=='PASS')}/{len(row_checks)} containment/size/positive-margin PASS",
 "producer_bbox_exact_match_all":all_declared,
 "machine_checks":machine,"protected_region_allowed_overlap_pixels":protected_overlap,
 "protected_geometry_pass":protected_geometry_pass,
 "machine_status":machine_status,
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "decision":"PENDING_CONTROLLER_VISUAL_QA" if machine_status=="PASS" and semantic_policy_pass and protected_geometry_pass else "C194_REWORK_REQUIRED_MACHINE_OR_POLICY_GATE",
 "runtime_validation":"UNTESTED",
 "preview_files":[
  f"localization/graphics/role_C/{run}/C194_SOURCE_FINAL_OVERVIEW.jpg",
  f"localization/graphics/role_C/{run}/C194_TARGET_CONTACTS.jpg",
  f"localization/graphics/role_C/{run}/C194_RAW_COMPARE.jpg"
 ]
}
(out/"C194_C598919A_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"C194_C598919A.json").write_text(json.dumps({
 "run":run,"qa_id":"C194","index":86,"asset":"C598919A","candidate_sha256":pr["candidate_sha256"],
 "machine_status":machine_status,"semantic_policy_pass":semantic_policy_pass,"protected_geometry_pass":protected_geometry_pass,
 "machine_checks":machine,"report":f"localization/graphics/role_C/{run}/C194_C598919A_MACHINE_QA.json","runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"qa_id":"C194","machine_status":machine_status,"semantic_policy_pass":semantic_policy_pass,"protected_geometry_pass":protected_geometry_pass,"machine_checks":machine},ensure_ascii=False),flush=True)
