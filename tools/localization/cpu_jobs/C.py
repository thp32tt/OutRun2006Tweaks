#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request,base64,io
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd(); run="20261005-C179-560FA536"
out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
pd=repo/"localization/graphics/role_A/20261005-A-PRODUCTION36"
pr=json.loads((pd/"A36_560FA536_REPORT.json").read_text())
asset=pr["asset"]; candidate=repo/pr["candidate_path"]
commit=pr["source_provenance"]["commit"]; expected_source_sha=pr["source_provenance"]["sha256"]
expected_candidate_sha=pr["candidate_sha256"]
folder=asset.split("/")[-2]; name=asset.split("/")[-1]
srcurl=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{commit}/Release/{folder}/{name}"
tmp=Path("/tmp/c179"); tmp.mkdir(exist_ok=True)
srcdds=tmp/"source.dds"; urllib.request.urlretrieve(srcurl,srcdds)

def sha(b): return hashlib.sha256(b).hexdigest()
def count(m): return int(np.count_nonzero(m))
def bm(im): return np.asarray(im.convert("L"))>0
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

sb=srcdds.read_bytes(); cb=candidate.read_bytes()
if sha(sb)!=expected_source_sha: raise RuntimeError(("source sha",sha(sb),expected_source_sha))
if sha(cb)!=expected_candidate_sha: raise RuntimeError(("candidate sha",sha(cb),expected_candidate_sha))
src,raw_src,dims,mips,mode=decode(sb); final,raw_final,dims2,mips2,mode2=decode(cb)
if dims!=[4096,4096] or dims2!=dims or mips2!=mips or cb[:128]!=sb[:128]: raise RuntimeError("structure drift")
W,H=dims
prodsrc=Image.open(pd/"560FA536_HD_SOURCE_READABLE.png").convert("RGBA")
if ImageChops.difference(src,prodsrc).getbbox(): raise RuntimeError("producer source mismatch")
clean=Image.open(pd/"560FA536_HD_CLEAN_PLATE.png").convert("RGBA")
sa=np.asarray(src,dtype=np.uint8); ca=np.asarray(clean,dtype=np.uint8); fa=np.asarray(final,dtype=np.uint8)
source_core=bm(Image.open(pd/"560FA536_HD_SOURCE_CORE_MASK.png"))
protected=bm(Image.open(pd/"560FA536_HD_PROTECTED_VISIBLE_MASK.png"))

rows=pr["rows"]; allowed=np.zeros((H,W),bool); rowchecks=[]
for r in rows:
    ob=[int(v) for v in r["source_effect_bbox"]]; lb=[int(v) for v in r["localized_bbox"]]
    x0,y0,x1,y1=ob; a,b,c,d=lb; allowed[y0:y1,x0:x1]=True
    dl,dr,dt,db=a-x0,x1-c,b-y0,y1-d
    rowchecks.append({"idx":r["idx"],"kind":r.get("kind"),"korean_lines":r.get("korean_lines"),
      "original_bbox":ob,"localized_bbox":lb,"delta_left":dl,"delta_right":dr,"delta_top":dt,"delta_bottom":db,
      "containment":"PASS" if a>=x0 and b>=y0 and c<=x1 and d<=y1 else "FAIL",
      "size_ceiling":"PASS" if c-a<=x1-x0 and d-b<=y1-y0 else "FAIL",
      "positive_margin":"PASS" if min(dl,dr,dt,db)>0 else "FAIL"})
if len(rowchecks)!=13: raise RuntimeError("row count")

cdiff=np.any(ca!=sa,axis=2); fdiff=np.any(fa!=sa,axis=2); render=np.any(fa!=ca,axis=2)
guard=np.asarray(Image.fromarray((render.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
machine={
 "clean_changed_outside_union_source_bboxes":count(cdiff&~allowed),
 "final_changed_outside_union_source_bboxes":count(fdiff&~allowed),
 "clean_alpha_outside_union_source_bboxes":count((ca[:,:,3]!=sa[:,:,3])&~allowed),
 "final_alpha_outside_union_source_bboxes":count((fa[:,:,3]!=sa[:,:,3])&~allowed),
 "protected_clean_changed":count(cdiff&protected),
 "protected_final_changed":count(fdiff&protected),
 "clean_source_core_unchanged":count(source_core & np.all(ca==sa,axis=2)),
 "source_core_residue_pixels":count(source_core & np.all(fa==sa,axis=2) & ~guard),
 "render_outside_union_source_bboxes":count(render&~allowed),
 "localized_render_on_protected_pixels":count(render&protected)
}
# pairwise separation within producer-declared target boxes
masks=[]
for rc in rowchecks:
    x0,y0,x1,y1=rc["original_bbox"]; m=np.zeros((H,W),bool); m[y0:y1,x0:x1]=render[y0:y1,x0:x1]; masks.append(m)
ov=touch=0
for i,mi in enumerate(masks):
    di=np.asarray(Image.fromarray((mi.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0
    for mj in masks[i+1:]:
        ov+=count(mi&mj); touch+=count(di&mj)
machine["localized_pair_overlap_pixels"]=ov; machine["localized_pair_1px_touch_pixels"]=touch
status="PASS" if all(v==0 for v in machine.values()) and all(x["containment"]=="PASS" and x["size_ceiling"]=="PASS" and x["positive_margin"]=="PASS" for x in rowchecks) else "FAIL"

# controller evidence: SOURCE | CLEAN | FINAL contacts, grouped.
font=ImageFont.load_default(); previews=[]
for gi,grp in enumerate((rowchecks[:7],rowchecks[7:]),1):
    cards=[]
    for rc in grp:
        x0,y0,x1,y1=rc["original_bbox"]; pad=24; crop=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
        ims=[comp(z).crop(crop) for z in (src,clean,final)]
        th=min(230,max(100,max(z.height for z in ims))); rr=[]
        for z in ims:
            if z.height>th: z=z.resize((max(1,round(z.width*th/z.height)),th),Image.Resampling.LANCZOS)
            rr.append(z)
        pw=max(330,max(z.width for z in rr)); card=Image.new("RGB",(pw*3+24,th+34),"white"); d=ImageDraw.Draw(card)
        for ci,(lab,z) in enumerate(zip(("SOURCE","CLEAN","FINAL"),rr)):
            ox=ci*pw+8; card.paste(z,(ox,28)); d.text((ox,6),lab,fill="black",font=font)
        d.text((pw*2+120,6),f"idx {rc['idx']} {rc.get('kind','')}",fill="black",font=font); cards.append(card)
    sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+8*(len(cards)-1)),"white"); yy=0
    for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+8
    if sheet.width>1800: sheet=sheet.resize((1800,round(sheet.height*1800/sheet.width)),Image.Resampling.LANCZOS)
    bio=io.BytesIO(); sheet.save(bio,"JPEG",quality=93,optimize=True)
    fn=out/f"C179_CONTACTS_{gi}_B64.txt"; fn.write_text(base64.b64encode(bio.getvalue()).decode()); previews.append(str(fn.relative_to(repo)))
# raw overview
rawcard=Image.new("RGB",(1024,2070),"white")
for i,(lab,z) in enumerate((("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_final))):
    zz=comp(z).resize((1024,1024),Image.Resampling.LANCZOS); rawcard.paste(zz,(0,i*1035+22)); ImageDraw.Draw(rawcard).text((5,i*1035+4),lab,fill="black")
bio=io.BytesIO(); rawcard.save(bio,"JPEG",quality=90,optimize=True)
rf=out/"C179_RAW_B64.txt"; rf.write_text(base64.b64encode(bio.getvalue()).decode()); previews.append(str(rf.relative_to(repo)))

report={"schema_version":1,"role":"C","run":run,"qa_id":"C179","queue_index":pr["index"],"asset":asset,
 "producer_run":pr["run"],"source_sha256":expected_source_sha,"candidate_sha256":expected_candidate_sha,
 "independent_source_decode_matches_producer_png":True,
 "structure":{"dimensions":dims,"format":"RGBA32","mipmaps":mips,"raw_orientation":"mirror_y","header_exact":cb[:128]==sb[:128]},
 "row_checks":rowchecks,"machine_checks":machine,"machine_status":status,
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","decision":"PENDING_CONTROLLER_VISUAL_QA" if status=="PASS" else "C179_REWORK_REQUIRED_MACHINE_GATE",
 "runtime_validation":"UNTESTED","preview_b64_files":previews}
(out/"C179_560FA536_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"C179_560FA536.json").write_text(json.dumps({"run":run,"qa_id":"C179","index":pr["index"],"asset":"560FA536","candidate_sha256":expected_candidate_sha,"machine_status":status,"machine_checks":machine,"report":f"localization/graphics/role_C/{run}/C179_560FA536_MACHINE_QA.json","runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"qa_id":"C179","machine_status":status,"machine_checks":machine,"previews":previews},ensure_ascii=False))
