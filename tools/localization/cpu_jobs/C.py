#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request,base64,io
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd(); run="20261005-C188-25F697C6"
out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
pd=repo/"localization/graphics/role_A/20261005-A-PRODUCTION47"
pr=json.loads((pd/"A47_25F697C6_REPORT.json").read_text())
asset=pr["asset"]; candidate=repo/pr["candidate_path"]; sp=pr["source_provenance"]
srcurl=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{sp['commit']}/Release/{asset.split('/')[-2]}/{asset.split('/')[-1]}"
tmp=Path("/tmp/c187"); tmp.mkdir(exist_ok=True); srcdds=tmp/"source.dds"
urllib.request.urlretrieve(srcurl,srcdds)

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
def comp(im,bg=(75,75,75,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def saveb64(im,path,q=95):
    b=io.BytesIO(); im.save(b,"JPEG",quality=q,optimize=True); path.write_text(base64.b64encode(b.getvalue()).decode())

sb=srcdds.read_bytes(); cb=candidate.read_bytes()
if sha(sb)!=sp["sha256"]: raise RuntimeError(("source sha drift",sha(sb),sp["sha256"]))
if sha(cb)!=pr["candidate_sha256"]: raise RuntimeError(("candidate sha drift",sha(cb),pr["candidate_sha256"]))
src,raw_src,dims,mips,mode=decode(sb); final,raw_final,dims2,mips2,mode2=decode(cb)
if dims!=[2048,2048] or dims2!=dims or mips2!=mips or cb[:128]!=sb[:128]: raise RuntimeError("structure/header drift")
W,H=dims
sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(final,dtype=np.uint8)

rows=pr["rows"]
# Build union of producer-declared exact source bboxes.
allowed=np.zeros((H,W),bool)
for r in rows:
    x0,y0,x1,y1=map(int,r["source_effect_bbox"]); allowed[y0:y1,x0:x1]=True

# Canonical atlas stores these text sprites on transparent background. Invisible RGB under alpha=0
# is not visible residue, so all residue/render decisions are based on alpha-visible pixels.
bg=np.array([0,0,0,0],dtype=np.uint8)
bg_tuple=[0,0,0,0]
expected=sa.copy()
for r in rows:
    x0,y0,x1,y1=map(int,r["source_effect_bbox"]); expected[y0:y1,x0:x1]=0
expected_clean=Image.fromarray(expected,"RGBA")

# Protected source must be byte/pixel exact outside source bboxes.
machine={
 "final_changed_outside_union_source_bboxes":count(np.any(fa!=sa,axis=2)&~allowed),
 "final_alpha_changed_outside_union_source_bboxes":count((fa[:,:,3]!=sa[:,:,3])&~allowed)
}

rowchecks=[]
render_union=np.zeros((H,W),bool)
for r in rows:
    ob=list(map(int,r["source_effect_bbox"])); declared=list(map(int,r["localized_bbox"]))
    x0,y0,x1,y1=ob
    # Visible candidate alpha defines localized content; alpha=0 RGB is intentionally ignored.
    diff=fa[y0:y1,x0:x1,3]>0
    actual=bbox(diff)
    if actual is not None:
        actual=[actual[0]+x0,actual[1]+y0,actual[2]+x0,actual[3]+y0]
        ax0,ay0,ax1,ay1=actual; render_union[ay0:ay1,ax0:ax1] |= fa[ay0:ay1,ax0:ax1,3]>0
    else:
        actual=None
    # Exact clean-residue gate: outside the declared localized bbox, every target-bbox pixel must be flat background.
    lx0,ly0,lx1,ly1=declared
    local_box=np.zeros((H,W),bool); local_box[ly0:ly1,lx0:lx1]=True
    target=np.zeros((H,W),bool); target[y0:y1,x0:x1]=True
    residue_mask=target & ~local_box & (fa[:,:,3]>0)
    dl=declared[0]-x0; dr=x1-declared[2]; dt=declared[1]-y0; db=y1-declared[3]
    rowchecks.append({
      "idx":r["idx"],"source":r["source"],"korean":r["korean"],
      "source_effect_bbox":ob,"declared_localized_bbox":declared,"independent_actual_localized_bbox":actual,
      "delta_left":dl,"delta_right":dr,"delta_top":dt,"delta_bottom":db,
      "containment":"PASS" if lx0>=x0 and ly0>=y0 and lx1<=x1 and ly1<=y1 else "FAIL",
      "size_ceiling":"PASS" if lx1-lx0<=x1-x0 and ly1-ly0<=y1-y0 else "FAIL",
      "positive_margin":"PASS" if min(dl,dr,dt,db)>0 else "FAIL",
      "flat_background_residue_outside_declared_localized_bbox":count(residue_mask)
    })

# Candidate text may not overlap/touch another localized target.
masks=[]
for rc in rowchecks:
    lx0,ly0,lx1,ly1=rc["declared_localized_bbox"]
    m=np.zeros((H,W),bool); m[ly0:ly1,lx0:lx1]=fa[ly0:ly1,lx0:lx1,3]>0; masks.append(m)
overlap=touch=0
from PIL import ImageFilter
for i,mi in enumerate(masks):
    di=np.asarray(Image.fromarray((mi.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0
    for mj in masks[i+1:]:
        overlap+=count(mi&mj); touch+=count(di&mj)
machine["localized_pair_overlap_pixels"]=overlap
machine["localized_pair_1px_touch_pixels"]=touch
machine["flat_background_residue_pixels_total"]=sum(x["flat_background_residue_outside_declared_localized_bbox"] for x in rowchecks)

rowpass=all(x["containment"]=="PASS" and x["size_ceiling"]=="PASS" and x["positive_margin"]=="PASS" and x["flat_background_residue_outside_declared_localized_bbox"]==0 for x in rowchecks)
status="PASS" if rowpass and all(machine[k]==0 for k in ["final_changed_outside_union_source_bboxes","final_alpha_changed_outside_union_source_bboxes","localized_pair_overlap_pixels","localized_pair_1px_touch_pixels","flat_background_residue_pixels_total"]) else "FAIL"

# Persist exact independent clean plate PNG as C evidence.
expected_clean.save(out/"C188_INDEPENDENT_EXACT_CLEAN_PLATE.png")

font=ImageFont.load_default(); cards=[]
for rc in rowchecks:
    x0,y0,x1,y1=rc["source_effect_bbox"]; pad=20
    crop=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    ims=[comp(z).crop(crop) for z in (src,expected_clean,final)]
    ch=max(i.height for i in ims); cw=max(i.width for i in ims)
    card=Image.new("RGB",(cw*3+18,ch+28),"white"); d=ImageDraw.Draw(card)
    for k,(lab,z) in enumerate(zip(("SOURCE","CLEAN(C)","FINAL"),ims)):
        ox=k*cw+6; card.paste(z,(ox,24)); d.text((ox,4),lab,fill="black",font=font)
    d.text((cw*2+110,4),f"idx {rc['idx']} {rc['source']} -> {rc['korean']}",fill="black",font=font)
    cards.append(card)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+6*(len(cards)-1)),"white")
yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+6
if sheet.width>1800: sheet=sheet.resize((1800,round(sheet.height*1800/sheet.width)),Image.Resampling.LANCZOS)
saveb64(sheet,out/"C188_CONTACTS_B64.txt",95)
rawcard=Image.new("RGB",(1024,2070),"white")
for i,(lab,z) in enumerate((("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_final))):
    zz=comp(z).resize((1024,1024),Image.Resampling.LANCZOS); rawcard.paste(zz,(0,i*1035+22)); ImageDraw.Draw(rawcard).text((5,i*1035+4),lab,fill="black")
saveb64(rawcard,out/"C188_RAW_B64.txt",92)

report={
 "schema_version":1,"role":"C","run":run,"qa_id":"C188","queue_index":pr["index"],"asset":asset,
 "producer_run":pr["run"],"source_sha256":sp["sha256"],"candidate_sha256":pr["candidate_sha256"],
 "structure":{"dimensions":dims,"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"raw_orientation":"mirror_y","header_exact":cb[:128]==sb[:128]},
 "independent_visible_background":"transparent_alpha0",
 "independent_clean_plate":"localization/graphics/role_C/20261005-C188-25F697C6/C188_INDEPENDENT_EXACT_CLEAN_PLATE.png",
 "row_checks":rowchecks,"all_9_bbox_size_positive_margin_and_residue_pass":rowpass,
 "machine_checks":machine,"machine_status":status,
 "policy_checks":{"stage_names":{"ANCIENT RUINS":"에인션트 루인스","ALPINE":"알파인"},"protected_ferrari_model_labels":"outside target bboxes exact by pixel gate"},
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","decision":"PENDING_CONTROLLER_VISUAL_QA" if status=="PASS" else "C188_REWORK_REQUIRED_MACHINE_GATE",
 "runtime_validation":"UNTESTED",
 "preview_b64_files":["localization/graphics/role_C/20261005-C188-25F697C6/C188_CONTACTS_B64.txt","localization/graphics/role_C/20261005-C188-25F697C6/C188_RAW_B64.txt"]
}
(out/"C188_25F697C6_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"C188_25F697C6.json").write_text(json.dumps({"run":run,"qa_id":"C188","index":pr["index"],"asset":"25F697C6","candidate_sha256":pr["candidate_sha256"],"machine_status":status,"machine_checks":machine,"report":f"localization/graphics/role_C/{run}/C188_25F697C6_MACHINE_QA.json","runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"qa_id":"C188","machine_status":status,"background_rgba":bg_tuple,"machine_checks":machine},ensure_ascii=False))
