#!/usr/bin/env python3
import os,json,hashlib,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd(); run="20261005-C208-97E863AD"
out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
pr=json.loads((repo/"localization/graphics/role_A/20261005-A-PRODUCTION65/A65_97E863AD_REPORT.json").read_text(encoding="utf-8"))
asset=pr["asset"]; sp=pr["source_provenance"]; cand=repo/pr["candidate_path"]
tmp=Path("/tmp/c208"); tmp.mkdir(exist_ok=True)
srcdds=tmp/"source.dds"; atlasp=tmp/"atlas.json"
folder=asset.split("/")[-2]; name=asset.split("/")[-1]
base=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{sp['commit']}"
urllib.request.urlretrieve(base+f"/Release/{folder}/{name}",srcdds)
urllib.request.urlretrieve(base+f"/Original%20(PC)/Original%20(Tweaks%20dumps)/{folder}/4x_{name[:-4]}_atlas.json",atlasp)

def sha(b): return hashlib.sha256(b).hexdigest()
def bbox(m):
    yy,xx=np.nonzero(m)
    return None if len(xx)==0 else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def count(m): return int(np.count_nonzero(m))
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def x_groups(mask, expected_words):
    bb=bbox(mask)
    if bb is None: raise RuntimeError("empty word mask")
    cols=[x for x in range(bb[0],bb[2]) if mask[:,x].any()]
    runs=[]
    if cols:
        s=p=cols[0]
        for x in cols[1:]:
            if x==p+1: p=x
            else: runs.append((s,p+1)); s=p=x
        runs.append((s,p+1))
    gaps=[(runs[i+1][0]-runs[i][1],i) for i in range(len(runs)-1)]
    cuts=sorted(i for _,i in sorted(gaps,reverse=True)[:expected_words-1])
    groups=[]; start=0
    for cut in cuts+[len(runs)-1]:
        g=runs[start:cut+1]; groups.append((g[0][0],g[-1][1])); start=cut+1
    if len(groups)!=expected_words: raise RuntimeError(("word grouping",expected_words,groups))
    return groups

sb=srcdds.read_bytes(); cb=cand.read_bytes()
if sha(sb)!=sp["source_sha256"] or sha(cb)!=pr["candidate_sha256"] or cb[:128]!=sb[:128]:
    raise RuntimeError(("identity/header",sha(sb),sha(cb),cb[:128]==sb[:128]))

raws=Image.open(srcdds).convert("RGBA")
rawf=Image.open(cand).convert("RGBA")
src=raws.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
fin=rawf.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(fin,dtype=np.uint8); H,W=sa.shape[:2]
if (W,H)!=(2048,1024): raise RuntimeError((W,H))
atlas=json.loads(atlasp.read_text(encoding="utf-8")); regs={int(r["idx"]):r for r in atlas["regions"]}
rows={int(r["region_idx"]):r for r in pr["rows"]}
expected_ids=set(pr["semantic_binding"]["localized_indices"])
if set(rows)!=expected_ids: raise RuntimeError(("row ids",sorted(rows),sorted(expected_ids)))

source_mask=np.zeros((H,W),bool)
allowed=np.zeros((H,W),bool)
preserved_masks=[]
source_bboxes={}
for idx,r in regs.items():
    x,y,w,h=map(int,r["rect"])
    a=sa[y:y+h,x:x+w,3]>0
    if idx not in expected_ids:
        pm=np.zeros((H,W),bool); pm[y:y+h,x:x+w]=a; preserved_masks.append((f"region_{idx}",pm))
        continue
    lm=a.copy()
    if idx in (1,2):
        groups=x_groups(a,5 if idx==1 else 4)
        tx0,tx1=groups[1]
        token=np.zeros_like(a); token[:,tx0:tx1]=a[:,tx0:tx1]
        lm &= ~token
        pm=np.zeros((H,W),bool); pm[y:y+h,x:x+w]=token; preserved_masks.append((f"inline_token_{idx}",pm))
    elif idx==4:
        ys=[yy for yy in range(h) if a[yy,:].any()]
        yruns=[]
        if ys:
            s=p=ys[0]
            for yy in ys[1:]:
                if yy==p+1: p=yy
                else: yruns.append((s,p+1)); s=p=yy
            yruns.append((s,p+1))
        if len(yruns)<2: raise RuntimeError(("idx4 line split",yruns))
        bottom=yruns[-1]
        keep=np.zeros_like(a); keep[bottom[0]:bottom[1],:]=a[bottom[0]:bottom[1],:]
        top=a & ~keep
        lm=keep
        pm=np.zeros((H,W),bool); pm[y:y+h,x:x+w]=top; preserved_masks.append(("idx4_OUTRUN_top",pm))
    sm=np.zeros((H,W),bool); sm[y:y+h,x:x+w]=lm
    source_mask |= sm
    bb=bbox(sm)
    if bb is None: raise RuntimeError(("empty local source",idx))
    source_bboxes[idx]=bb
    x0,y0,x1,y1=bb; allowed[y0:y1,x0:x1]=True

# Independent clean alpha: exact source localizable alpha removed; protected source pixels remain.
clean_alpha=sa[:,:,3].copy()
clean_alpha[source_mask]=0
final_alpha=fa[:,:,3]>0
row_checks=[]; targets=[]; source_exact=True; target_exact=True
for idx in sorted(expected_ids):
    r=rows[idx]; ob=source_bboxes[idx]; pob=list(map(int,r["original_bbox"]))
    se=(ob==pob); source_exact &= se
    x0,y0,x1,y1=ob
    tm=np.zeros((H,W),bool)
    tm[y0:y1,x0:x1]=final_alpha[y0:y1,x0:x1] & (clean_alpha[y0:y1,x0:x1]==0)
    tbb=bbox(tm); pt=list(map(int,r["localized_bbox"]))
    te=(tbb==pt); target_exact &= te
    if tbb is None:
        dl=dr=dt=db=-1; contain=sizeok=positive=False; wratio=hratio=0.0
    else:
        a,b,c,d=tbb
        dl=a-x0; dr=x1-c; dt=b-y0; db=y1-d
        contain=a>=x0 and b>=y0 and c<=x1 and d<=y1
        sizeok=(c-a)<=x1-x0 and (d-b)<=y1-y0
        positive=min(dl,dr,dt,db)>0
        wratio=(c-a)/(x1-x0); hratio=(d-b)/(y1-y0)
    targets.append((idx,tm))
    row_checks.append({
        "region_idx":idx,"source":r["source"],"korean":r["korean"],
        "independent_source_bbox":ob,"producer_source_bbox":pob,"source_bbox_exact_match_producer":se,
        "independent_localized_bbox":tbb,"producer_localized_bbox":pt,"localized_bbox_exact_match_producer":te,
        "delta_left":dl,"delta_right":dr,"delta_top":dt,"delta_bottom":db,
        "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if sizeok else "FAIL","positive_margin":"PASS" if positive else "FAIL",
        "localized_to_source_width_ratio":round(wratio,4),"localized_to_source_height_ratio":round(hratio,4)
    })

chg=np.any(fa!=sa,axis=2); ach=fa[:,:,3]!=sa[:,:,3]; intro=fa[:,:,3]>sa[:,:,3]
preserved={}
for label,pm in preserved_masks:
    preserved[label]=count(chg & pm)
# Any exact source pixel retained inside localizable source glyph masks is source-script residue.
exact=np.all(fa==sa,axis=2)
residue=count(source_mask & exact & (sa[:,:,3]>0))
ov=0; touch=0
for i,(ii,mi) in enumerate(targets):
    yy,xx=np.nonzero(mi); dil=np.zeros_like(mi)
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            ys=np.clip(yy+dy,0,H-1); xs=np.clip(xx+dx,0,W-1); dil[ys,xs]=True
    for jj,mj in targets[i+1:]:
        ov += count(mi & mj); touch += count(dil & mj)

machine={
 "decoded_changed_outside_union_source_bboxes":count(chg & ~allowed),
 "alpha_changed_outside_union_source_bboxes":count(ach & ~allowed),
 "introduced_visible_outside_union_source_bboxes":count(intro & ~allowed),
 "source_script_exact_residue_pixels":residue,
 "localized_overlap_pixels":ov,
 "localized_1px_touch_pixels":touch,
 "protected_changed_pixels":sum(preserved.values())
}
rp=sum(1 for r in row_checks if r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS")
status="PASS" if rp==len(row_checks) and source_exact and target_exact and all(v==0 for v in machine.values()) else "FAIL"

cards=[]
for r in row_checks:
    x0,y0,x1,y1=r["independent_source_bbox"]; pad=12
    crop=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    a=comp(src).crop(crop); b=comp(fin).crop(crop); cw=max(a.width,b.width); ch=max(a.height,b.height)
    card=Image.new("RGB",(cw*2+8,ch+24),"white"); card.paste(a,(0,24)); card.paste(b,(cw+8,24))
    d=ImageDraw.Draw(card); d.text((2,3),f"{r['region_idx']} {r['source']}",fill="black"); d.text((cw+10,3),r["korean"],fill="black")
    cards.append(card)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+3*(len(cards)-1)),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+3
if sheet.width>1800: sheet=sheet.resize((1800,round(sheet.height*1800/sheet.width)),Image.Resampling.LANCZOS)
sheet.save(out/"C208_TARGET_CONTACTS.jpg",quality=96)
rawsheet=Image.new("RGB",(1024,536*2),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raws),("FINAL_RAW_MIRROR_Y",rawf)]):
    z=comp(im).resize((1024,512),Image.Resampling.NEAREST); rawsheet.paste(z,(0,i*536+24)); ImageDraw.Draw(rawsheet).text((4,i*536+4),label,fill="black")
rawsheet.save(out/"C208_RAW_COMPARE.jpg",quality=96)

rep={
 "schema_version":1,"role":"C","run":run,"qa_id":"C208","queue_index":193,"asset":asset,
 "producer_run":pr["run"],"source_sha256":sp["source_sha256"],"candidate_sha256":pr["candidate_sha256"],
 "structure":{"dimensions":[W,H],"header_exact":True,"raw_orientation":"mirror_y","format":pr["structure"]["format"]},
 "source_bbox_exact_match_all":source_exact,"candidate_bbox_exact_match_all":target_exact,
 "row_checks":row_checks,"row_gate":f"{rp}/{len(row_checks)} PASS","machine_checks":machine,
 "protected_pixel_changes":preserved,"machine_status":status,
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "decision":"PENDING_CONTROLLER_VISUAL_QA" if status=="PASS" else "C208_REWORK_REQUIRED_MACHINE_GATE",
 "runtime_validation":"UNTESTED",
 "preview_files":[f"localization/graphics/role_C/{run}/C208_TARGET_CONTACTS.jpg",f"localization/graphics/role_C/{run}/C208_RAW_COMPARE.jpg"]
}
(out/"C208_97E863AD_MACHINE_QA.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"C208_97E863AD.json").write_text(json.dumps({
 "run":run,"qa_id":"C208","index":193,"asset":"97E863AD","candidate_sha256":pr["candidate_sha256"],
 "machine_status":status,"row_gate":rep["row_gate"],"source_bbox_exact_match_all":source_exact,
 "candidate_bbox_exact_match_all":target_exact,"machine_checks":machine,
 "report":f"localization/graphics/role_C/{run}/C208_97E863AD_MACHINE_QA.json","runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"C208":{"machine_status":status,"row_gate":rep["row_gate"],"machine_checks":machine}},ensure_ascii=False),flush=True)
