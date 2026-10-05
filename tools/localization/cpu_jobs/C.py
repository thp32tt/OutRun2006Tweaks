#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C160-B99-63C91067"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_CLAR_RANK_Exst/63C91067_512x512.dds"
cand=Path("/tmp/outrun_C160/b99_candidate.dds")
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="9f41fe44ecb17a4daba096ddbb9d2c73fa28e8f9"
ATLAS_BLOB_SHA1="7f118326e34794e2ae5bf3f3b6d82b6ce566c64a"
SOURCE_SHA256="d44868cbb37f8412901fa6252638250fcaebfed87e23a65772f61e710e3273ab"
CANDIDATE_SHA256="55829559f2111526dd789e30d66c30c384755ef956fadd8e9d9ca9b36dd19660"\nCANDIDATE_COMMIT="4703bfb4b6fb7a1c5fb3712d1db0927bafccfb0f"

tmp=Path("/tmp/outrun_C160"); tmp.mkdir(parents=True,exist_ok=True)
sp=tmp/"source.dds"; apath=tmp/"atlas.json"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
urllib.request.urlretrieve(base+"/Release/spr_sprani_CLAR_RANK_Exst/63C91067_512x512.dds",sp)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_CLAR_RANK_Exst/4x_63C91067_512x512_atlas.json",apath)
urllib.request.urlretrieve("https://raw.githubusercontent.com/thp32tt/OutRun2006Tweaks/"+CANDIDATE_COMMIT+"/localization/graphics/hd_candidates/"+asset,cand)

def gitblob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def bbox(m):
    yy,xx=np.nonzero(m)
    return None if not len(xx) else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def count(m): return int(np.count_nonzero(m))
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

sb=sp.read_bytes(); ab=apath.read_bytes(); cb=cand.read_bytes()
if gitblob(sb)!=SOURCE_BLOB_SHA1 or gitblob(ab)!=ATLAS_BLOB_SHA1 or sha(sb)!=SOURCE_SHA256 or sha(cb)!=CANDIDATE_SHA256:
    raise RuntimeError(("provenance/hash drift",gitblob(sb),gitblob(ab),sha(sb),sha(cb)))
if sb[:128]!=cb[:128] or len(sb)!=len(cb): raise RuntimeError("DDS header/length drift")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6])
mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
if (W,H,pitch,mips)!=(2048,2048,8192,1) or mode!="RGBA":
    raise RuntimeError(("structure",W,H,pitch,mips,masks))

raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
raw_fin=Image.frombytes("RGBA",(W,H),cb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
fin=raw_fin.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(fin,dtype=np.uint8)
regions={r["idx"]:r for r in json.loads(ab.decode())["regions"]}

rows=[]; source_core=np.zeros((H,W),bool); source_mask=np.zeros((H,W),bool); allowed=np.zeros((H,W),bool)
for idx in (0,1):
    x,y,cw,ch=regions[idx]["rect"]
    rx0=x+int(cw*.20); rx1=x+int(cw*.80); ry0=y+int(ch*.02); ry1=y+min(int(ch*.28),300)
    roi=sa[ry0:ry1,rx0:rx1]
    rr=roi[:,:,0].astype(np.int16); gg=roi[:,:,1].astype(np.int16); bb=roi[:,:,2].astype(np.int16); aa=roi[:,:,3]
    white=(aa>32)&(rr>165)&(gg>165)&(bb>165)&((np.maximum.reduce([rr,gg,bb])-np.minimum.reduce([rr,gg,bb]))<65)
    navy=(aa>32)&(bb>rr+10)&(bb>gg+5)&(rr<100)&(gg<100)&(bb<170)
    nys,nxs=np.nonzero(navy)
    if len(nxs)<100: raise RuntimeError(("source navy core too small",idx,len(nxs)))
    nx0=max(0,int(nxs.min())-10); ny0=max(0,int(nys.min())-10); nx1=min(navy.shape[1],int(nxs.max())+11); ny1=min(navy.shape[0],int(nys.max())+11)
    core=np.zeros_like(navy); core[ny0:ny1,nx0:nx1]=(white|navy)[ny0:ny1,nx0:nx1]
    m=np.zeros((H,W),bool); m[ry0:ry1,rx0:rx1]=core
    source_core|=m
    dil=np.asarray(Image.fromarray((m.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(41)))>0
    ob=bbox(dil)
    if not ob: raise RuntimeError(("source effect bbox empty",idx))
    source_mask|=dil
    allowed[ob[1]:ob[3],ob[0]:ob[2]]=True
    rows.append({"region_idx":idx,"source":"Total Rank","korean":"종합 랭킹","cell":[x,y,cw,ch],
                 "core_bbox":bbox(m),"original_bbox":ob,"source_core_pixels":count(m),"source_mask_pixels":count(dil)})

# Exact protection outside independently derived source bboxes.
diff=np.any(sa!=fa,axis=2); alpha_diff=sa[:,:,3]!=fa[:,:,3]
outside=count(diff & ~allowed); alpha_out=count(alpha_diff & ~allowed)
if outside or alpha_out: raise RuntimeError(("outside drift",outside,alpha_out))

# Independently identify final Korean white/navy title footprint inside each bbox using navy as anchor.
target=np.zeros((H,W),bool); target_masks=[]; outrows=[]
for r in rows:
    x0,y0,x1,y1=r["original_bbox"]
    roi=fa[y0:y1,x0:x1]
    cr=roi[:,:,0].astype(np.int16); cg=roi[:,:,1].astype(np.int16); cb2=roi[:,:,2].astype(np.int16); ca=roi[:,:,3]
    white=(ca>32)&(cr>200)&(cg>200)&(cb2>200)&((np.maximum.reduce([cr,cg,cb2])-np.minimum.reduce([cr,cg,cb2]))<55)
    navy=(ca>32)&(cb2>cr+10)&(cb2>cg+5)&(cr<100)&(cg<100)&(cb2<170)
    nys,nxs=np.nonzero(navy)
    if len(nxs)<100: raise RuntimeError(("candidate navy core too small",r["region_idx"],len(nxs)))
    bx0=max(0,int(nxs.min())-8); by0=max(0,int(nys.min())-8); bx1=min(navy.shape[1],int(nxs.max())+9); by1=min(navy.shape[0],int(nys.max())+9)
    local=np.zeros_like(navy); local[by0:by1,bx0:bx1]=(white|navy)[by0:by1,bx0:bx1]
    tm=np.zeros((H,W),bool); tm[y0:y1,x0:x1]=local
    lb=bbox(tm)
    if not lb: raise RuntimeError(("target empty",r["region_idx"]))
    sw,sh=x1-x0,y1-y0; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    d=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
    if lw>sw or lh>sh or min(d)<=0: raise RuntimeError(("bbox/size/margin",r["region_idx"],r["original_bbox"],lb,d))
    target|=tm; target_masks.append(tm)
    outrows.append({**r,"localized_bbox":lb,"source_size":[sw,sh],"localized_size":[lw,lh],
      "delta_left":d[0],"delta_right":d[1],"delta_top":d[2],"delta_bottom":d[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

overlap=count(target_masks[0]&target_masks[1])
touch=count((np.asarray(Image.fromarray((target_masks[0].astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0)&target_masks[1])
protected=(sa[:,:,3]>0)&~allowed
target_protected_overlap=count(target&protected)
target_protected_1px_near=count((np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0)&protected)
if overlap or touch or target_protected_overlap or target_protected_1px_near:
    raise RuntimeError(("overlap/protected",overlap,touch,target_protected_overlap,target_protected_1px_near))

# Structural residue diagnostic only: source-title core locations not covered by Korean are
# compared to a strongly blurred candidate background. High counts require controller visual review.
guard=np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(9)))>0
blur=np.asarray(fin.filter(ImageFilter.GaussianBlur(12)),dtype=np.int16)
resid_scope=source_core & ~guard
resid_delta=np.max(np.abs(fa[:,:,:3].astype(np.int16)-blur[:,:,:3]),axis=2)
resid_structural_pixels=count(resid_scope & (resid_delta>=18))
resid_scope_pixels=count(resid_scope)

for name,m in [("C160_B99_SOURCE_CORE_MASK.png",source_core),("C160_SOURCE_EFFECT_MASK.png",source_mask),("C160_ALLOWED_BBOX_MASK.png",allowed),("C160_TARGET_TEXT_MASK.png",target),("C160_PROTECTED_MASK.png",protected)]:
    Image.fromarray((m.astype(np.uint8)*255),"L").save(out/name)

# Independent source/final evidence, plus row contacts; no producer clean/masks consumed.
stack=Image.new("RGB",(1024,2*1050),"white")
for i,(label,im) in enumerate([("SOURCE",src),("FINAL",fin)]):
    z=comp(im).resize((1024,1024),Image.Resampling.NEAREST); stack.paste(z,(0,i*1050+26)); ImageDraw.Draw(stack).text((5,i*1050+5),label,fill="black")
stack.save(out/"C160_B99_63C_SOURCE_FINAL.jpg",quality=96)
cards=[]
for r in outrows:
    x0,y0,x1,y1=r["original_bbox"]; p=24; cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[comp(z).crop(cr) for z in (src,fin)]
    c=Image.new("RGB",(sum(z.width for z in ims)+8,max(z.height for z in ims)+34),"white"); xx=0
    for z in ims: c.paste(z,(xx,34)); xx+=z.width+8
    ImageDraw.Draw(c).text((5,5),f'{r["region_idx"]} Total Rank -> 종합 랭킹',fill="black"); cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height+4 for c in cards)),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.save(out/"C160_B99_63C_ROW_CONTACT.jpg",quality=96)
rr=Image.new("RGB",(1024,2*1050),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_fin)]):
    z=comp(im).resize((1024,1024),Image.Resampling.NEAREST); rr.paste(z,(0,i*1050+26)); ImageDraw.Draw(rr).text((5,i*1050+5),label,fill="black")
rr.save(out/"C160_B99_63C_RAW_COMPARE.jpg",quality=96)

report={"schema_version":1,"role":"C","run":run,"queue_index":26,"asset":asset,"producer_run":"20261005-B-PRODUCTION99","candidate_commit":CANDIDATE_COMMIT,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,"atlas_git_blob_sha1":ATLAS_BLOB_SHA1,"source_sha256":SOURCE_SHA256},
 "candidate_sha256":CANDIDATE_SHA256,"candidate_changed_by_C":False,
 "independent_method":"C re-downloaded pinned canonical RGBA DDS+atlas, independently re-derived the two Total Rank source cores/effect bboxes from canonical white+navy title pixels, decoded the pinned B99 candidate, independently anchored Korean masks from candidate navy+white pixels, recomputed exact-bbox/protected/overlap gates, and generated source/final visual evidence without consuming producer masks or clean plate.",
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "rows":outrows,
 "machine_checks":{"final_outside":outside,"alpha_outside":alpha_out,"bbox_size_positive_margin":"2/2 PASS",
   "localized_overlap":overlap,"localized_touch":touch,"target_protected_overlap":target_protected_overlap,"target_protected_1px_near":target_protected_1px_near,
   "source_core_residue_diagnostic_scope_pixels":resid_scope_pixels,"source_core_residue_structural_pixels_ge18":resid_structural_pixels,
   "residue_diagnostic_note":"diagnostic only; patterned plates require mandatory controller visual residue decision"},
 "machine_status":"PASS_CONTAINMENT_VISUAL_RESIDUE_REVIEW_REQUIRED","controller_visual_qa":"PENDING",
 "decision":"PENDING_CONTROLLER_VISUAL_QA","RUNTIME_VALIDATION":"UNTESTED"}
(out/"C160_B99_63C_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"asset":"63C91067","index":26,"source_sha256":SOURCE_SHA256,"candidate_sha256":CANDIDATE_SHA256,
 "machine_status":report["machine_status"],"bbox_size_positive_margin":"2/2","outside":outside,"alpha_outside":alpha_out,
 "overlap":overlap,"touch":touch,"target_protected_overlap":target_protected_overlap,"target_protected_1px_near":target_protected_1px_near,
 "residue_diagnostic_scope_pixels":resid_scope_pixels,"residue_structural_pixels_ge18":resid_structural_pixels,
 "runtime_validation":"UNTESTED","report":f"localization/graphics/role_C/{run}/C160_63C_MACHINE_QA.json"}
(wr/"C160_B99_63C91067.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False),flush=True)
