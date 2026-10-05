#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C162-7CE1CFC5"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_game_cvt_Exst/7CE1CFC5_512x128.dds"
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
CANDIDATE_COMMIT="e5a80269a745140c4928b97c15a20d0532b56ecf"
SOURCE_BLOB_SHA1="8e79a14a4453c7e015144c1c2e25a4aacc633645"
ATLAS_BLOB_SHA1="1a13020899080238d4177800382137f0a3e291a5"
SOURCE_SHA256="9c35216873d617ed68df55be424f35ddf50b1eacc8ee86072068745aea166f9f"
CANDIDATE_SHA256="b75102588dc30ec828fdec765658d2e25cbcee9d972832bb70b527b372008542"

tmp=Path("/tmp/outrun_C162"); tmp.mkdir(parents=True,exist_ok=True)
sp=tmp/"source.dds"; apath=tmp/"atlas.json"; cp=tmp/"candidate.dds"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
urllib.request.urlretrieve(base+"/Release/spr_sprani_game_cvt_Exst/7CE1CFC5_512x128.dds",sp)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_game_cvt_Exst/4x_7CE1CFC5_512x128_atlas.json",apath)
urllib.request.urlretrieve("https://raw.githubusercontent.com/thp32tt/OutRun2006Tweaks/"+CANDIDATE_COMMIT+"/localization/graphics/hd_candidates/"+asset,cp)

def gitblob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def bbox(m):
    yy,xx=np.nonzero(m)
    return None if not len(xx) else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def count(m): return int(np.count_nonzero(m))
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

sb=sp.read_bytes(); ab=apath.read_bytes(); cb=cp.read_bytes()
if gitblob(sb)!=SOURCE_BLOB_SHA1 or gitblob(ab)!=ATLAS_BLOB_SHA1 or sha(sb)!=SOURCE_SHA256 or sha(cb)!=CANDIDATE_SHA256:
    raise RuntimeError(("provenance/hash drift",gitblob(sb),gitblob(ab),sha(sb),sha(cb)))
if sb[:128]!=cb[:128] or len(sb)!=len(cb): raise RuntimeError("DDS header/length drift")
H,W=struct.unpack_from("<II",sb,12); mips=struct.unpack_from("<I",sb,28)[0]; fourcc=sb[84:88]
need=128+((W+3)//4)*((H+3)//4)*16
if (W,H)!=(2048,512) or fourcc!=b"DXT5" or mips not in (0,1) or len(sb)!=need:
    raise RuntimeError(("structure",W,H,mips,fourcc,len(sb),need))

raw_src=Image.open(sp).convert("RGBA")
raw_fin=Image.open(cp).convert("RGBA")
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
fin=raw_fin.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(fin,dtype=np.uint8)
regions={r["idx"]:r for r in json.loads(ab.decode())["regions"]}

specs=[
 (0,"NEXT MISSION","다음 미션",[0,344,1756,168],"big"),
 (1,"Race The Rivals!","라이벌과 레이스!",[0,200,704,144],"small"),
 (2,"Drift To Score!","드리프트 점수 도전!",[0,40,704,136],"small"),
 (8,"Slipstream To Score!","슬립스트림 점수 도전!",[704,200,704,144],"small"),
]

source_mask=np.zeros((H,W),bool); allowed=np.zeros((H,W),bool); rows=[]
for idx,en,ko,roi,family in specs:
    rx,ry,rw,rh=roi
    alpha=sa[ry:ry+rh,rx:rx+rw,3]>1
    bb=bbox(alpha)
    if not bb: raise RuntimeError(("empty source target",idx,en))
    ob=[rx+bb[0],ry+bb[1],rx+bb[2],ry+bb[3]]
    m=np.zeros((H,W),bool); m[ry:ry+rh,rx:rx+rw]=alpha
    source_mask|=m
    allowed[ob[1]:ob[3],ob[0]:ob[2]]=True
    rows.append({"region_idx":idx,"source":en,"korean":ko,"family":family,
                 "cell":regions[idx]["rect"],"text_roi":roi,"original_bbox":ob,"source_mask_pixels":count(m)})

# Independent exact decoded-pixel containment: every RGBA byte outside source bboxes must match.
diff=np.any(sa!=fa,axis=2); adiff=sa[:,:,3]!=fa[:,:,3]
outside=count(diff&~allowed); alpha_out=count(adiff&~allowed)
introduced_visible_out=count((fa[:,:,3]>1)&(sa[:,:,3]<=1)&~allowed)
if outside or alpha_out or introduced_visible_out:
    raise RuntimeError(("outside drift",outside,alpha_out,introduced_visible_out))

# Re-measure localized decoded alpha per exact source bbox.
target=np.zeros((H,W),bool); tms=[]; outrows=[]
for r in rows:
    x0,y0,x1,y1=r["original_bbox"]
    local=fa[y0:y1,x0:x1,3]>1
    bb=bbox(local)
    if not bb: raise RuntimeError(("candidate target empty",r["region_idx"]))
    lb=[x0+bb[0],y0+bb[1],x0+bb[2],y0+bb[3]]
    tm=np.zeros((H,W),bool); tm[y0:y1,x0:x1]=local
    sw,sh=x1-x0,y1-y0; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    d=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
    if lw>sw or lh>sh or min(d)<=0: raise RuntimeError(("bbox/size/margin",r["region_idx"],r["original_bbox"],lb,d))
    target|=tm; tms.append(tm)
    outrows.append({**r,"localized_bbox":lb,"source_size":[sw,sh],"localized_size":[lw,lh],
                    "delta_left":d[0],"delta_right":d[1],"delta_top":d[2],"delta_bottom":d[3],
                    "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

# Residue and localized-label separation.
guard=np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
source_residue=count(source_mask&(fa[:,:,3]>8)&~guard)
if source_residue: raise RuntimeError(("source residue",source_residue))
overlap=0; touch=[]
for i in range(len(tms)):
    grow=np.asarray(Image.fromarray((tms[i].astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0
    for j in range(i+1,len(tms)):
        ov=count(tms[i]&tms[j]); near=count(grow&tms[j]); overlap+=ov
        if ov or near: touch.append([outrows[i]["region_idx"],outrows[j]["region_idx"],ov,near])
if overlap or touch: raise RuntimeError(("localized overlap/touch",overlap,touch))

protected=(sa[:,:,3]>1)&~allowed
target_protected_overlap=count(target&protected)
target_protected_1px_near=count((np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0)&protected)
if target_protected_overlap or target_protected_1px_near:
    raise RuntimeError(("target protected",target_protected_overlap,target_protected_1px_near))

# Explicit protected car/top artwork equality follows from exact outside equality, also summarize non-target atlas cells.
protected_changed=count(diff&protected)

# BC3 patch accounting.
bw=(W+3)//4; bh=(H+3)//4; allowed_raw=np.flipud(allowed)
changed_blocks=0; changed_blocks_wholly_outside=0
for by in range(bh):
    for bx in range(bw):
        off=128+(by*bw+bx)*16
        if sb[off:off+16]!=cb[off:off+16]:
            changed_blocks+=1
            if not np.any(allowed_raw[by*4:min(H,by*4+4),bx*4:min(W,bx*4+4)]):
                changed_blocks_wholly_outside+=1
if changed_blocks_wholly_outside: raise RuntimeError(("BC3 changes wholly outside allowed",changed_blocks_wholly_outside))

for name,m in [("C161_SOURCE_TEXT_MASK.png",source_mask),("C161_ALLOWED_BBOX_MASK.png",allowed),("C161_TARGET_TEXT_MASK.png",target),("C161_PROTECTED_SOURCE_MASK.png",protected)]:
    Image.fromarray((m.astype(np.uint8)*255),"L").save(out/name)

stack=Image.new("RGB",(1024,2*300),"white")
for i,(label,im) in enumerate([("SOURCE",src),("FINAL",fin)]):
    z=comp(im).resize((1024,256),Image.Resampling.NEAREST); stack.paste(z,(0,i*300+28)); ImageDraw.Draw(stack).text((5,i*300+5),label,fill="black")
stack.save(out/"C162_7CE_SOURCE_FINAL.jpg",quality=96)

cards=[]
for r in outrows:
    x0,y0,x1,y1=r["original_bbox"]; p=14
    cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[comp(z).crop(cr) for z in (src,fin)]
    c=Image.new("RGB",(sum(z.width for z in ims)+8,max(z.height for z in ims)+34),"white"); xx=0
    for z in ims: c.paste(z,(xx,34)); xx+=z.width+8
    ImageDraw.Draw(c).text((5,5),f'{r["region_idx"]} {r["source"]} -> {r["korean"]}',fill="black"); cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height+4 for c in cards)),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.save(out/"C162_7CE_ROW_CONTACT.jpg",quality=96)

rr=Image.new("RGB",(1024,2*300),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_fin)]):
    z=comp(im).resize((1024,256),Image.Resampling.NEAREST); rr.paste(z,(0,i*300+28)); ImageDraw.Draw(rr).text((5,i*300+5),label,fill="black")
rr.save(out/"C162_7CE_RAW_COMPARE.jpg",quality=96)

report={"schema_version":1,"role":"C","run":run,"queue_index":59,"asset":asset,"producer_run":"20261005-A-PRODUCTION25",
 "candidate_commit":CANDIDATE_COMMIT,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,"atlas_git_blob_sha1":ATLAS_BLOB_SHA1,"source_sha256":SOURCE_SHA256},
 "candidate_sha256":CANDIDATE_SHA256,"candidate_changed_by_C":False,
 "independent_method":"C re-downloaded pinned canonical DXT5 DDS+atlas and pinned A25 candidate, independently re-derived source alpha masks/exact bboxes from reviewed text ROIs, decoded both images, recomputed exact decoded-pixel containment/alpha/residue/label separation/protected-art and BC3 scope without consuming producer masks.",
 "structure":{"dimensions":[W,H],"format":"DXT5","mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "rows":outrows,
 "machine_checks":{"bbox_size_positive_margin":"4/4 PASS","decoded_changed_outside":outside,"alpha_outside":alpha_out,
   "introduced_visible_outside":introduced_visible_out,"source_residue":source_residue,"localized_overlap":overlap,"touch_pairs":touch,
   "target_protected_overlap":target_protected_overlap,"target_protected_1px_near":target_protected_1px_near,
   "protected_source_changed":protected_changed,"changed_bc3_blocks":changed_blocks,"changed_bc3_blocks_wholly_outside_allowed":changed_blocks_wholly_outside},
 "machine_status":"PASS","controller_visual_qa":"PENDING","decision":"PENDING_CONTROLLER_VISUAL_QA","RUNTIME_VALIDATION":"UNTESTED"}
(out/"C162_7CE_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"asset":"7CE1CFC5","index":59,"source_sha256":SOURCE_SHA256,"candidate_sha256":CANDIDATE_SHA256,
 "machine_status":"PASS","bbox_size_positive_margin":"4/4","decoded_changed_outside":outside,"alpha_outside":alpha_out,
 "introduced_visible_outside":introduced_visible_out,"source_residue":source_residue,"overlap":overlap,"touch_pairs":len(touch),
 "target_protected_overlap":target_protected_overlap,"target_protected_1px_near":target_protected_1px_near,"protected_source_changed":protected_changed,
 "changed_bc3_blocks":changed_blocks,"changed_bc3_blocks_wholly_outside_allowed":changed_blocks_wholly_outside,
 "runtime_validation":"UNTESTED","report":f"localization/graphics/role_C/{run}/C162_7CE_MACHINE_QA.json"}
(wr/"C162_7CE1CFC5.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False),flush=True)
