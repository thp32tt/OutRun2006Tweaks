#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C159-DDF0392A"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/DDF0392A_256x512.dds"
cand=repo/"localization/graphics/hd_candidates"/asset
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="1ff7680eb71750d884b0e69fe058aef3a5cf5fa2"
ATLAS_BLOB_SHA1="819d31b1cd9c59fb6d011f3f0361d6ed7114c286"
SOURCE_SHA256="bcfad5a1a71ab66c841134b0f3f3aa8fa5571b806bd3945dabeca3722d18fb72"
CANDIDATE_SHA256="e0d04c144aec92aad090dd2d5f7895f956a1001cafca319d1b0f4681fd7e0fea"

tmp=Path("/tmp/outrun_C159"); tmp.mkdir(parents=True,exist_ok=True)
sp=tmp/"source.dds"; apath=tmp/"atlas.json"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/DDF0392A_256x512.dds",sp)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_DDF0392A_256x512_atlas.json",apath)

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
if sb[:128]!=cb[:128] or len(sb)!=len(cb):
    raise RuntimeError("DDS header/length drift")
H,W=struct.unpack_from("<II",sb,12)
mips=struct.unpack_from("<I",sb,28)[0]; fourcc=sb[84:88]
need=128+((W+3)//4)*((H+3)//4)*16
if (W,H)!=(1024,2048) or fourcc!=b"DXT5" or mips not in (0,1) or len(sb)!=need:
    raise RuntimeError(("structure",W,H,mips,fourcc,len(sb),need))

raw_src=Image.open(sp).convert("RGBA")
raw_fin=Image.open(cand).convert("RGBA")
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
fin=raw_fin.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(fin,dtype=np.uint8)

atlas=json.loads(ab.decode())
regions={r["idx"]:r for r in atlas["regions"]}
specs=[
 (0,"OutRun Mode / 15 C.","아웃런 모드 / 15코스"),
 (1,"OutRun 1986","아웃런 1986"),
 (2,"Journey Mode / Random","저니 모드 / 무작위"),
]
songs={3:"Who Are You?",4:"Splash Wave",5:"Shiny World",6:"Shake The Street",7:"Rush A Difficulty",8:"Risky Ride",9:"Passing Breeze"}

source_mask=np.zeros((H,W),bool)
allowed=np.zeros((H,W),bool)
rows=[]
for idx,en,ko in specs:
    x,y,cw,ch=regions[idx]["rect"]
    lm=sa[y:y+ch,x:x+cw,3]>0
    bb=bbox(lm)
    if not bb: raise RuntimeError(("empty source target",idx,en))
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    source_mask[y:y+ch,x:x+cw] |= lm
    allowed[ob[1]:ob[3],ob[0]:ob[2]]=True
    rows.append({"region_idx":idx,"source":en,"korean":ko,"cell":[x,y,cw,ch],"original_bbox":ob,"source_mask_pixels":count(lm)})

# Exact decoded protection: every RGBA pixel outside exact source bboxes must be byte-identical.
diff=np.any(sa!=fa,axis=2)
alpha_diff=sa[:,:,3]!=fa[:,:,3]
outside=count(diff & ~allowed)
alpha_out=count(alpha_diff & ~allowed)
introduced_visible_out=count((fa[:,:,3]>1)&(sa[:,:,3]<=1)&~allowed)
if outside or alpha_out or introduced_visible_out:
    raise RuntimeError(("decoded outside drift",outside,alpha_out,introduced_visible_out))

# Explicit song-title/Ferrari region equality independent of producer masks.
preserved={}
for idx in range(3,25):
    x,y,cw,ch=regions[idx]["rect"]
    changed=count(np.any(sa[y:y+ch,x:x+cw]!=fa[y:y+ch,x:x+cw],axis=2))
    preserved[str(idx)]=changed
if any(preserved.values()): raise RuntimeError(("protected row changed",preserved))

# Reconstruct a source-alpha clean plate and independently measure decoded localized pixels.
clean=sa.copy(); clean[source_mask,3]=0
clean_diff=np.any(clean!=sa,axis=2)
clean_outside=count(clean_diff & ~source_mask)
clean_unchanged_inside=count(source_mask & ~clean_diff)
if clean_outside or clean_unchanged_inside:
    raise RuntimeError(("clean reconstruction",clean_outside,clean_unchanged_inside))

target=np.zeros((H,W),bool); target_masks=[]; row_results=[]
for r in rows:
    x0,y0,x1,y1=r["original_bbox"]
    tm=np.zeros((H,W),bool)
    tm[y0:y1,x0:x1]=(fa[y0:y1,x0:x1,3]>1)
    lb=bbox(tm)
    if not lb: raise RuntimeError(("decoded localized target empty",r["region_idx"]))
    sw,sh=x1-x0,y1-y0; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    d=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
    if lw>sw or lh>sh or min(d)<=0:
        raise RuntimeError(("bbox/size/margin",r["region_idx"],r["original_bbox"],lb,d))
    target|=tm; target_masks.append(tm)
    row_results.append({**r,"localized_bbox":lb,"source_size":[sw,sh],"localized_size":[lw,lh],
      "delta_left":d[0],"delta_right":d[1],"delta_top":d[2],"delta_bottom":d[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

# Source residue: source alpha footprint must not remain away from localized target with a 2px guard.
guard=np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
source_residue=count(source_mask & (fa[:,:,3]>8) & ~guard)
if source_residue: raise RuntimeError(("source residue",source_residue))

# Localized labels must not overlap or touch each other, and must stay separated from protected source pixels.
overlap=0; touch=[]
for i in range(len(target_masks)):
    ag=np.asarray(Image.fromarray((target_masks[i].astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0
    for j in range(i+1,len(target_masks)):
        ov=count(target_masks[i]&target_masks[j]); near=count(ag&target_masks[j]); overlap+=ov
        if ov or near: touch.append([row_results[i]["region_idx"],row_results[j]["region_idx"],ov,near])
protected_source=(sa[:,:,3]>0)&~allowed
target_protected_overlap=count(target&protected_source)
target_protected_1px_near=count((np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0)&protected_source)
if overlap or touch or target_protected_overlap or target_protected_1px_near:
    raise RuntimeError(("overlap/protected-near",overlap,touch,target_protected_overlap,target_protected_1px_near))

# Source family color diagnostic on high-alpha glyph pixels.
sv=sa[source_mask & (sa[:,:,3]>=128),:3]
cv=fa[target & (fa[:,:,3]>=128),:3]
if len(sv)<30 or len(cv)<30: raise RuntimeError(("style samples",len(sv),len(cv)))
sm=[int(np.median(sv[:,k])) for k in range(3)]
cm=[int(np.median(cv[:,k])) for k in range(3)]
delta=[abs(cm[k]-sm[k]) for k in range(3)]
if max(delta)>8: raise RuntimeError(("fill style drift",sm,cm,delta))

# Compressed byte-change accounting: no changed BC3 block may be wholly outside exact bbox-derived patch coverage.
bw=(W+3)//4; bh=(H+3)//4
allowed_raw=np.flipud(allowed)
changed_blocks=0; changed_blocks_wholly_outside=0
for by in range(bh):
    for bx in range(bw):
        off=128+(by*bw+bx)*16
        if sb[off:off+16]!=cb[off:off+16]:
            changed_blocks+=1
            if not np.any(allowed_raw[by*4:min(H,by*4+4),bx*4:min(W,bx*4+4)]):
                changed_blocks_wholly_outside+=1
if changed_blocks_wholly_outside:
    raise RuntimeError(("changed BC3 blocks wholly outside allowed",changed_blocks_wholly_outside))

for name,m in [
 ("C159_SOURCE_TEXT_MASK.png",source_mask),
 ("C159_ALLOWED_BBOX_MASK.png",allowed),
 ("C159_TARGET_TEXT_MASK.png",target),
 ("C159_PROTECTED_SOURCE_MASK.png",protected_source)
]:
    Image.fromarray((m.astype(np.uint8)*255),"L").save(out/name)
clean_img=Image.fromarray(clean,"RGBA"); clean_img.save(out/"C159_VERIFIED_CLEAN_PLATE.png")

stack=Image.new("RGB",(512,3*1050),"white")
for i,(label,im) in enumerate([("SOURCE",src),("CLEAN",clean_img),("FINAL",fin)]):
    z=comp(im).resize((512,1024),Image.Resampling.NEAREST); stack.paste(z,(0,i*1050+26)); ImageDraw.Draw(stack).text((5,i*1050+5),label,fill="black")
stack.save(out/"C159_DDF_COMPARE.jpg",quality=96)

cards=[]
for r in row_results:
    x0,y0,x1,y1=r["original_bbox"]; p=12
    cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[comp(z).crop(cr) for z in (src,clean_img,fin)]
    sc=min(2.0,1000/max(1,ims[0].width))
    ims=[z.resize((max(1,int(z.width*sc)),max(1,int(z.height*sc))),Image.Resampling.NEAREST) for z in ims]
    c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+34),"white"); xx=0
    for z in ims: c.paste(z,(xx,34)); xx+=z.width+6
    ImageDraw.Draw(c).text((5,5),r["source"]+" -> "+r["korean"],fill="black"); cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+4*(len(cards)-1)),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.save(out/"C159_DDF_ROW_CONTACT.jpg",quality=96)

rr=Image.new("RGB",(512,2*1050),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_fin)]):
    z=comp(im).resize((512,1024),Image.Resampling.NEAREST); rr.paste(z,(0,i*1050+26)); ImageDraw.Draw(rr).text((5,i*1050+5),label,fill="black")
rr.save(out/"C159_DDF_RAW_COMPARE.jpg",quality=96)

report={"schema_version":1,"role":"C","run":run,"queue_index":222,"asset":asset,"producer_run":"20261005-B-PRODUCTION89",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,"atlas_git_blob_sha1":ATLAS_BLOB_SHA1,"source_sha256":SOURCE_SHA256},
 "candidate_sha256":CANDIDATE_SHA256,"candidate_changed_by_C":False,
 "independent_method":"C re-downloaded pinned canonical DXT5 DDS+atlas, independently decoded source/candidate, re-derived the three exact source-alpha bboxes from canonical regions, required byte-identical decoded RGBA outside their union, explicitly compared protected song-title/Ferrari regions 3..24, rebuilt the transparent-alpha clean plate, remeasured decoded localized bboxes/residue/overlap/protected separation, and independently audited BC3 changed-block scope.",
 "structure":{"dimensions":[W,H],"format":"DXT5","mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "semantic_binding":{"localized":[{"region_idx":i,"source":en,"korean":ko} for i,en,ko in specs],"protected_song_titles":songs,"protected_rows_10_24":"Ferrari model names"},
 "rows":row_results,
 "machine_checks":{"decoded_pixels_changed_outside_exact_source_bboxes":outside,"alpha_changed_outside_exact_source_bboxes":alpha_out,
   "introduced_visible_outside_exact_source_bboxes":introduced_visible_out,"protected_rows_3_24_changed_pixels":preserved,
   "clean_changed_outside_source_mask":clean_outside,"clean_unchanged_inside_source_mask":clean_unchanged_inside,
   "bbox_size_positive_margin":"3/3 PASS","source_residue":source_residue,"overlap":overlap,"touch_pairs":touch,
   "target_protected_overlap":target_protected_overlap,"target_protected_1px_near":target_protected_1px_near,
   "source_fill_median_rgb":sm,"localized_fill_median_rgb":cm,"fill_median_abs_delta":delta,
   "changed_bc3_blocks":changed_blocks,"changed_bc3_blocks_wholly_outside_allowed":changed_blocks_wholly_outside},
 "song_title_policy":"PASS_PRESERVE_ORIGINAL_ENGLISH_PIXEL_EXACT",
 "machine_status":"PASS","controller_visual_qa":"PENDING","decision":"PENDING_CONTROLLER_VISUAL_QA","RUNTIME_VALIDATION":"UNTESTED"}
(out/"C159_DDF_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"asset":"DDF0392A","index":222,"source_sha256":SOURCE_SHA256,"candidate_sha256":CANDIDATE_SHA256,
 "machine_status":"PASS","bbox_size_positive_margin":"3/3","decoded_changed_outside":outside,"alpha_outside":alpha_out,
 "introduced_visible_outside":introduced_visible_out,"protected_rows_changed":sum(preserved.values()),"source_residue":source_residue,
 "overlap":overlap,"touch_pairs":len(touch),"target_protected_overlap":target_protected_overlap,"target_protected_1px_near":target_protected_1px_near,
 "source_fill_median_rgb":sm,"localized_fill_median_rgb":cm,"fill_median_abs_delta":delta,
 "changed_bc3_blocks":changed_blocks,"changed_bc3_blocks_wholly_outside_allowed":changed_blocks_wholly_outside,
 "runtime_validation":"UNTESTED","report":f"localization/graphics/role_C/{run}/C159_DDF_MACHINE_QA.json"}
(wr/"C159_DDF0392A.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False),flush=True)
