#!/usr/bin/env python3
import os, json, hashlib, struct, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C195-4EDA9DE3"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

producer=repo/"localization/graphics/role_A/20261005-A-PRODUCTION51/A51_4EDA9DE3_REPORT.json"
pr=json.loads(producer.read_text(encoding="utf-8"))
candidate=repo/pr["candidate_path"]
asset=pr["asset"]
sp=pr["source_provenance"]

tmp=Path("/tmp/c195")
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
def comp(im,bg=(54,54,54,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def decode_rgba32(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    H,W,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76)
    if (W,H,mips,pf[3])!=(2048,1024,1,32):
        raise RuntimeError(("structure",W,H,mips,pf))
    masks=(pf[4],pf[5],pf[6],pf[7])
    if masks==(0xff0000,0xff00,0xff,0xff000000): mode="BGRA"
    elif masks==(0xff,0xff00,0xff0000,0xff000000): mode="RGBA"
    else: raise RuntimeError(("unsupported masks",masks))
    if len(b)!=128+W*H*4: raise RuntimeError(("length",len(b),128+W*H*4))
    return Image.frombytes("RGBA",(W,H),b[128:],"raw",mode), {"width":W,"height":H,"pitch":pitch,"mipmaps":mips,"raw_mode":mode}

sb=srcdds.read_bytes(); cb=candidate.read_bytes()
if sha(sb)!=sp["sha256"]: raise RuntimeError(("source sha drift",sha(sb),sp["sha256"]))
if sha(cb)!=pr["candidate_sha256"]: raise RuntimeError(("candidate sha drift",sha(cb),pr["candidate_sha256"]))
raw_src,sm=decode_rgba32(sb); raw_fin,cm=decode_rgba32(cb)
if sm!=cm or cb[:128]!=sb[:128]: raise RuntimeError(("header/structure drift",sm,cm,cb[:128]==sb[:128]))
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
fin=raw_fin.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(fin,dtype=np.uint8)
H,W=sa.shape[:2]

atlas=json.loads(atlasp.read_text(encoding="utf-8"))
regs={int(r["idx"]):r for r in atlas["regions"]}
expected={
 0:("WATERFALLS","워터폴스"),
 1:("SUNNY BEACH","서니 비치"),
 2:("SKYSCRAPERS","스카이스크레이퍼스"),
 3:("NATIONAL PARK","내셔널 파크"),
 4:("MILKY WAY","밀키 웨이"),
 5:("LOST CITY","로스트 시티"),
 6:("LEGEND","레전드"),
 7:("JUNGLE","정글"),
 8:("ICE SCAPE","아이스스케이프"),
 9:("GIANT STATUES","자이언트 스태추스"),
 10:("FLORAL VILLAGE","플로럴 빌리지"),
 11:("CASINO TOWN","카지노 타운"),
 12:("CANYON","캐니언"),
 13:("BIG FOREST","빅 포레스트"),
 14:("BAY AREA","베이 에어리어"),
}
rows_by_idx={int(r["idx"]):r for r in pr["rows"]}
if set(regs)!=set(expected): raise RuntimeError(("atlas region set",sorted(regs),sorted(expected)))
semantic_policy_pass=True
source_bbox_exact_all=True
candidate_bbox_exact_all=True
allowed=np.zeros((H,W),dtype=bool)
row_checks=[]
localized_masks=[]

for idx,(english,korean) in expected.items():
    if idx not in rows_by_idx: raise RuntimeError(("missing producer row",idx))
    prow=rows_by_idx[idx]
    if (prow["source"].upper(),prow["korean"])!=(english,korean):
        semantic_policy_pass=False
    x,y,w,h=map(int,regs[idx]["rect"])
    crop_src=sa[y:y+h,x:x+w]
    smask=crop_src[:,:,3]>0
    sbb0=bbox(smask)
    if sbb0 is None: raise RuntimeError(("empty source region",idx))
    sbb=[sbb0[0]+x,sbb0[1]+y,sbb0[2]+x,sbb0[3]+y]
    declared_source=list(map(int,prow["source_effect_bbox"]))
    source_bbox_exact=(sbb==declared_source)
    source_bbox_exact_all &= source_bbox_exact
    x0,y0,x1,y1=sbb
    allowed[y0:y1,x0:x1]=True

    crop_fin=fa[y0:y1,x0:x1]
    fmask=crop_fin[:,:,3]>0
    fbb0=bbox(fmask)
    fbb=None if fbb0 is None else [fbb0[0]+x0,fbb0[1]+y0,fbb0[2]+x0,fbb0[3]+y0]
    declared_final=list(map(int,prow["localized_bbox"]))
    final_exact=(fbb==declared_final)
    candidate_bbox_exact_all &= final_exact
    if fbb:
        a,b,c,d=fbb
        dl=a-x0; dr=x1-c; dt=b-y0; db=y1-d
        containment=(a>=x0 and b>=y0 and c<=x1 and d<=y1)
        size_ok=((c-a)<=x1-x0 and (d-b)<=y1-y0)
        positive=min(dl,dr,dt,db)>0
        full=np.zeros((H,W),dtype=bool); full[y0:y1,x0:x1]=fmask
        localized_masks.append(full)
        spix=crop_src[smask]
        fpix=crop_fin[fmask]
        smed=np.median(spix,axis=0).astype(int).tolist() if len(spix) else None
        fmed=np.median(fpix,axis=0).astype(int).tolist() if len(fpix) else None
    else:
        dl=dr=dt=db=-1; containment=size_ok=positive=False; smed=fmed=None
    row_checks.append({
      "idx":idx,"source":english,"korean":korean,
      "atlas_rect":[x,y,w,h],
      "independent_source_bbox":sbb,
      "producer_source_bbox":declared_source,
      "source_bbox_exact_match_producer":source_bbox_exact,
      "independent_localized_bbox":fbb,
      "producer_localized_bbox":declared_final,
      "localized_bbox_exact_match_producer":final_exact,
      "delta_left":dl,"delta_right":dr,"delta_top":dt,"delta_bottom":db,
      "containment":"PASS" if containment else "FAIL",
      "size_ceiling":"PASS" if size_ok else "FAIL",
      "positive_margin":"PASS" if positive else "FAIL",
      "source_rgba_median":smed,"localized_rgba_median":fmed
    })

changed=np.any(fa!=sa,axis=2)
alpha_changed=fa[:,:,3]!=sa[:,:,3]
introduced=fa[:,:,3]>sa[:,:,3]
candidate_visible=fa[:,:,3]>0
machine={
 "decoded_changed_outside_union_source_bboxes":count(changed&~allowed),
 "alpha_changed_outside_union_source_bboxes":count(alpha_changed&~allowed),
 "introduced_visible_outside_union_source_bboxes":count(introduced&~allowed),
 "candidate_visible_outside_union_source_bboxes":count(candidate_visible&~allowed),
}
overlap=0; touch=0
for i,mi in enumerate(localized_masks):
    for mj in localized_masks[i+1:]:
        overlap+=count(mi&mj)
        # 1px dilation without scipy
        yy,xx=np.nonzero(mi)
        dil=np.zeros_like(mi)
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                ys=np.clip(yy+dy,0,H-1); xs=np.clip(xx+dx,0,W-1)
                dil[ys,xs]=True
        touch+=count(dil & mj)
machine["localized_overlap_pixels"]=overlap
machine["localized_1px_touch_pixels"]=touch

row_gate=all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS" for r in row_checks)
machine_status="PASS" if (
    row_gate and source_bbox_exact_all and candidate_bbox_exact_all and semantic_policy_pass
    and all(machine[k]==0 for k in [
      "decoded_changed_outside_union_source_bboxes","alpha_changed_outside_union_source_bboxes",
      "introduced_visible_outside_union_source_bboxes","candidate_visible_outside_union_source_bboxes",
      "localized_overlap_pixels","localized_1px_touch_pixels"
    ])
) else "FAIL"

# Compact C visual evidence: per-row SOURCE | FINAL, plus readable/raw overviews.
cards=[]
for r in row_checks:
    x0,y0,x1,y1=r["independent_source_bbox"]; pad=8
    crop=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    a=comp(src).crop(crop); b=comp(fin).crop(crop)
    ch=max(a.height,b.height); cw=max(a.width,b.width)
    card=Image.new("RGB",(cw*2+8,ch+24),"white")
    card.paste(a,(0,24)); card.paste(b,(cw+8,24))
    d=ImageDraw.Draw(card); d.text((2,3),f"idx{r['idx']} {r['source']}",fill="black"); d.text((cw+10,3),r["korean"],fill="black")
    cards.append(card)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+4*(len(cards)-1)),"white")
yy=0
for c in cards:
    sheet.paste(c,(0,yy)); yy+=c.height+4
if sheet.width>1800:
    sheet=sheet.resize((1800,round(sheet.height*1800/sheet.width)),Image.Resampling.LANCZOS)
sheet.save(out/"C195_TARGET_CONTACTS.jpg",quality=96)

overview=Image.new("RGB",(2048,1050),"white")
overview.paste(comp(src).resize((1024,512),Image.Resampling.LANCZOS),(0,24))
overview.paste(comp(fin).resize((1024,512),Image.Resampling.LANCZOS),(1024,24))
d=ImageDraw.Draw(overview); d.text((4,4),"SOURCE_READABLE",fill="black"); d.text((1028,4),"FINAL_READABLE",fill="black")
overview.save(out/"C195_SOURCE_FINAL_OVERVIEW.jpg",quality=95)

rawcard=Image.new("RGB",(2048,1050),"white")
rawcard.paste(comp(raw_src).resize((1024,512),Image.Resampling.LANCZOS),(0,24))
rawcard.paste(comp(raw_fin).resize((1024,512),Image.Resampling.LANCZOS),(1024,24))
d=ImageDraw.Draw(rawcard); d.text((4,4),"SOURCE_RAW_MIRROR_Y",fill="black"); d.text((1028,4),"FINAL_RAW_MIRROR_Y",fill="black")
rawcard.save(out/"C195_RAW_COMPARE.jpg",quality=95)

report={
 "schema_version":1,"role":"C","run":run,"qa_id":"C195","queue_index":159,"asset":asset,
 "producer_run":pr["run"],"source_sha256":sp["sha256"],"candidate_sha256":pr["candidate_sha256"],
 "structure":{**sm,"header_exact":cb[:128]==sb[:128],"raw_orientation":"mirror_y"},
 "semantic_expected":{str(k):{"source":v[0],"korean":v[1]} for k,v in expected.items()},
 "semantic_policy_pass":semantic_policy_pass,
 "source_bbox_exact_match_all":source_bbox_exact_all,
 "candidate_bbox_exact_match_all":candidate_bbox_exact_all,
 "row_checks":row_checks,
 "row_gate":f"{sum(1 for r in row_checks if r['containment']=='PASS' and r['size_ceiling']=='PASS' and r['positive_margin']=='PASS')}/{len(row_checks)} PASS",
 "machine_checks":machine,
 "machine_status":machine_status,
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "decision":"PENDING_CONTROLLER_VISUAL_QA" if machine_status=="PASS" else "C195_REWORK_REQUIRED_MACHINE_OR_POLICY_GATE",
 "runtime_validation":"UNTESTED",
 "preview_files":[
  f"localization/graphics/role_C/{run}/C195_TARGET_CONTACTS.jpg",
  f"localization/graphics/role_C/{run}/C195_SOURCE_FINAL_OVERVIEW.jpg",
  f"localization/graphics/role_C/{run}/C195_RAW_COMPARE.jpg"
 ]
}
(out/"C195_4EDA9DE3_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"C195_4EDA9DE3.json").write_text(json.dumps({
 "run":run,"qa_id":"C195","index":159,"asset":"4EDA9DE3",
 "candidate_sha256":pr["candidate_sha256"],"machine_status":machine_status,
 "row_gate":report["row_gate"],"semantic_policy_pass":semantic_policy_pass,
 "source_bbox_exact_match_all":source_bbox_exact_all,"candidate_bbox_exact_match_all":candidate_bbox_exact_all,
 "machine_checks":machine,
 "report":f"localization/graphics/role_C/{run}/C195_4EDA9DE3_MACHINE_QA.json",
 "runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"qa_id":"C195","machine_status":machine_status,"row_gate":report["row_gate"],"semantic_policy_pass":semantic_policy_pass,"machine_checks":machine},ensure_ascii=False),flush=True)
