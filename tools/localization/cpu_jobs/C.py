#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request,base64,io
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd(); run="20261005-C192-39BCA907"
out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
pd=repo/"localization/graphics/role_A/20261005-A-PRODUCTION49"
pr=json.loads((pd/"A49_39BCA907_REPORT.json").read_text())
asset=pr["asset"]; candidate=repo/pr["candidate_path"]; sp=pr["source_provenance"]

tmp=Path("/tmp/c192"); tmp.mkdir(exist_ok=True); srcdds=tmp/"source.dds"
url=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{sp['commit']}/Release/{asset.split('/')[-2]}/{asset.split('/')[-1]}"
urllib.request.urlretrieve(url,srcdds)

def sha(b): return hashlib.sha256(b).hexdigest()
def count(m): return int(np.count_nonzero(m))
def bbox(m):
    yy,xx=np.nonzero(m)
    return None if len(xx)==0 else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def decode(data):
    if data[:4]!=b"DDS ": raise RuntimeError("not dds")
    H,W,pitch,depth,mips=struct.unpack_from("<5I",data,12)
    pf=struct.unpack_from("<8I",data,76); masks=(pf[4],pf[5],pf[6],pf[7])
    mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
    if mode is None or len(data)!=128+W*H*4: raise RuntimeError(("structure",W,H,mips,masks,len(data)))
    raw=Image.frombytes("RGBA",(W,H),data[128:],"raw",mode)
    return raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),raw,[W,H],mips,mode
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def saveb64(im,path,q=96):
    b=io.BytesIO(); im.save(b,"JPEG",quality=q,optimize=True); path.write_text(base64.b64encode(b.getvalue()).decode())

sb=srcdds.read_bytes(); cb=candidate.read_bytes()
if sha(sb)!=sp["sha256"]: raise RuntimeError(("source sha drift",sha(sb),sp["sha256"]))
if sha(cb)!=pr["candidate_sha256"]: raise RuntimeError(("candidate sha drift",sha(cb),pr["candidate_sha256"]))
src,raw_src,dims,mips,mode=decode(sb); final,raw_final,dims2,mips2,mode2=decode(cb)
if dims!=[2048,1024] or dims2!=dims or mips2!=mips or cb[:128]!=sb[:128]: raise RuntimeError("structure/header drift")
W,H=dims
sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(final,dtype=np.uint8)

rows=pr["rows"]
allowed=np.zeros((H,W),bool)
for r in rows:
    x0,y0,x1,y1=map(int,r["source_effect_bbox"]); allowed[y0:y1,x0:x1]=True

changed=np.any(fa!=sa,axis=2)
alpha_changed=fa[:,:,3]!=sa[:,:,3]
machine={
 "final_changed_outside_union_source_bboxes":count(changed&~allowed),
 "final_alpha_changed_outside_union_source_bboxes":count(alpha_changed&~allowed)
}
# Outside all 15 target bboxes is protected by exact canonical pixel equality.
machine["protected_pixels_changed"]=machine["final_changed_outside_union_source_bboxes"]

rowchecks=[]; masks=[]
for r in rows:
    x0,y0,x1,y1=map(int,r["source_effect_bbox"])
    # Transparent text atlas: localized visible alpha inside each exact source bbox is the text footprint.
    vis=fa[y0:y1,x0:x1,3]>0
    bb=bbox(vis)
    actual=None if bb is None else [bb[0]+x0,bb[1]+y0,bb[2]+x0,bb[3]+y0]
    declared=list(map(int,r["localized_bbox"]))
    if actual:
        a,b,c,d=actual; dl=a-x0; dr=x1-c; dt=b-y0; db=y1-d
        contain=a>=x0 and b>=y0 and c<=x1 and d<=y1
        size=(c-a)<=x1-x0 and (d-b)<=y1-y0
        positive=min(dl,dr,dt,db)>0
    else:
        dl=dr=dt=db=-1; contain=size=positive=False
    local=np.zeros((H,W),bool); local[y0:y1,x0:x1]=vis
    masks.append(local)
    guard=np.asarray(Image.fromarray((local.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
    source_visible=(sa[:,:,3]>0)
    residue=allowed & source_visible & np.all(fa==sa,axis=2) & ~guard
    # scope this residue to the current row only
    rowmask=np.zeros((H,W),bool); rowmask[y0:y1,x0:x1]=True
    rc={
      "idx":r["idx"],"source":r["source"],"korean":r["korean"],
      "source_effect_bbox":[x0,y0,x1,y1],
      "producer_localized_bbox":declared,
      "independent_localized_bbox":actual,
      "bbox_exact_match_producer":actual==declared,
      "delta_left":dl,"delta_right":dr,"delta_top":dt,"delta_bottom":db,
      "containment":"PASS" if contain else "FAIL",
      "size_ceiling":"PASS" if size else "FAIL",
      "positive_margin":"PASS" if positive else "FAIL",
      "visible_source_residue_outside_korean_guard":count(residue&rowmask)
    }
    rowchecks.append(rc)

overlap=touch=0
for i,mi in enumerate(masks):
    di=np.asarray(Image.fromarray((mi.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0
    for mj in masks[i+1:]:
        overlap+=count(mi&mj)
        touch+=count(di&mj)
machine["localized_pair_overlap_pixels"]=overlap
machine["localized_pair_1px_touch_pixels"]=touch
machine["visible_source_residue_outside_korean_guard_total"]=sum(x["visible_source_residue_outside_korean_guard"] for x in rowchecks)

canonical={
 "TULIP GARDEN":"튤립 가든","SNOW MOUNTAIN":"스노 마운틴","PALM BEACH":"팜 비치",
 "METROPOLIS":"메트로폴리스","INDUSTRIAL COMPLEX":"인더스트리얼 컴플렉스","IMPERIAL AVENUE":"임페리얼 애비뉴",
 "GHOST FOREST":"고스트 포레스트","DESERT":"데저트","DEEP LAKE":"딥 레이크",
 "CONIFEROUS FOREST":"코니퍼러스 포레스트","CLOUDY HIGHLAND":"클라우디 하이랜드","CASTLE WALL":"캐슬 월",
 "CAPE WAY":"케이프 웨이","ANCIENT RUINS":"에인션트 루인스","ALPINE":"알파인"
}
semantic_pass=all(canonical.get(r["source"])==r["korean"] for r in rows) and len(rows)==15
rows_pass=all(x["containment"]=="PASS" and x["size_ceiling"]=="PASS" and x["positive_margin"]=="PASS" and x["bbox_exact_match_producer"] and x["visible_source_residue_outside_korean_guard"]==0 for x in rowchecks)
hard_zero=["final_changed_outside_union_source_bboxes","final_alpha_changed_outside_union_source_bboxes","protected_pixels_changed","localized_pair_overlap_pixels","localized_pair_1px_touch_pixels","visible_source_residue_outside_korean_guard_total"]
status="PASS" if semantic_pass and rows_pass and all(machine[k]==0 for k in hard_zero) else "FAIL"

# C-owned exact clean plate for visual proof: clear only the 15 exact source text bboxes.
clean_arr=sa.copy()
for r in rows:
    x0,y0,x1,y1=map(int,r["source_effect_bbox"]); clean_arr[y0:y1,x0:x1]=0
clean=Image.fromarray(clean_arr,"RGBA")
clean.save(out/"C192_INDEPENDENT_CLEAN_PLATE.png")

font=ImageFont.load_default(); cards=[]
for rc in rowchecks:
    x0,y0,x1,y1=rc["source_effect_bbox"]; pad=10
    crop=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    ims=[comp(z).crop(crop) for z in (src,clean,final)]
    cw=max(i.width for i in ims); ch=max(i.height for i in ims)
    card=Image.new("RGB",(cw*3+12,ch+28),"white"); d=ImageDraw.Draw(card)
    for k,(lab,z) in enumerate(zip(("SOURCE","CLEAN(C)","FINAL"),ims)):
        ox=k*cw+4; card.paste(z,(ox,24)); d.text((ox,4),lab,fill="black",font=font)
    d.text((cw*2+110,4),f"idx {rc['idx']} {rc['source']} -> {rc['korean']}",fill="black",font=font)
    cards.append(card)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+4*(len(cards)-1)),"white")
y=0
for c in cards: sheet.paste(c,(0,y)); y+=c.height+4
if sheet.width>1800: sheet=sheet.resize((1800,round(sheet.height*1800/sheet.width)),Image.Resampling.LANCZOS)
saveb64(sheet,out/"C192_CONTACTS_B64.txt",96)

rawcard=Image.new("RGB",(1024,1050),"white")
raw=comp(final).resize((1024,512),Image.Resampling.LANCZOS)
srcraw=comp(src).resize((1024,512),Image.Resampling.LANCZOS)
rawcard.paste(srcraw,(0,18)); rawcard.paste(raw,(0,538))
rd=ImageDraw.Draw(rawcard); rd.text((5,2),"SOURCE_READABLE",fill="black"); rd.text((5,522),"FINAL_READABLE",fill="black")
saveb64(rawcard,out/"C192_READABLE_OVERVIEW_B64.txt",94)

rawmirror=Image.new("RGB",(1024,2070),"white")
for i,(lab,z) in enumerate((("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_final))):
    zz=comp(z).resize((1024,512),Image.Resampling.LANCZOS)
    yy=i*520+22; rawmirror.paste(zz,(0,yy)); ImageDraw.Draw(rawmirror).text((5,yy-18),lab,fill="black")
# crop unused lower canvas
rawmirror=rawmirror.crop((0,0,1024,1060))
saveb64(rawmirror,out/"C192_RAW_B64.txt",94)

report={
 "schema_version":1,"role":"C","run":run,"qa_id":"C192","queue_index":pr["index"],"asset":asset,
 "producer_run":pr["run"],"source_sha256":sp["sha256"],"candidate_sha256":pr["candidate_sha256"],
 "structure":{"dimensions":dims,"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"raw_orientation":"mirror_y","header_exact":cb[:128]==sb[:128]},
 "row_checks":rowchecks,"all_15_bbox_size_positive_margin_exact_match_pass":rows_pass,
 "canonical_stage_mapping":canonical,"semantic_policy_pass":semantic_pass,
 "machine_checks":machine,"machine_status":status,
 "a48_semantic_binding_defect":"superseded by A49 before C finalization",
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "decision":"PENDING_CONTROLLER_VISUAL_QA" if status=="PASS" else "C192_REWORK_REQUIRED_MACHINE_OR_SEMANTIC_GATE",
 "runtime_validation":"UNTESTED",
 "preview_b64_files":[
  "localization/graphics/role_C/20261005-C192-39BCA907/C192_CONTACTS_B64.txt",
  "localization/graphics/role_C/20261005-C192-39BCA907/C192_READABLE_OVERVIEW_B64.txt",
  "localization/graphics/role_C/20261005-C192-39BCA907/C192_RAW_B64.txt"
 ]
}
(out/"C192_39BCA907_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"C192_39BCA907.json").write_text(json.dumps({
 "run":run,"qa_id":"C192","index":pr["index"],"asset":"39BCA907","candidate_sha256":pr["candidate_sha256"],
 "machine_status":status,"semantic_policy_pass":semantic_pass,"machine_checks":machine,
 "report":f"localization/graphics/role_C/{run}/C192_39BCA907_MACHINE_QA.json","runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"qa_id":"C192","machine_status":status,"semantic_policy_pass":semantic_pass,"machine_checks":machine},ensure_ascii=False))
