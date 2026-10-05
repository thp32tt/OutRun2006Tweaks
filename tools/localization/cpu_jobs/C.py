#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd(); run="20261005-C143-E3F4BA07"
out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/E3F4BA07_512x128.dds"
cand=repo/"localization/graphics/hd_candidates"/asset
bdir=repo/"localization/graphics/role_B/20261005-B-PRODUCTION67"

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="0ac26331b6c2765b9c46b867ff1f2151fd7a15b1"
ATLAS_BLOB_SHA1="50256e8d4d5af1335249993d44abc5d18a4c5672"
SOURCE_SHA256="fb31e9f62e0d46c4554646be2f32d70cb015e8fdbc269189bf9d76a26eab5b72"
CANDIDATE_SHA256="1042102e5f298628ce874fe86a5562211f8a02c87fdd4de55324679f84d8f12c"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
tmp=Path("/tmp/outrun_C143"); tmp.mkdir(parents=True,exist_ok=True)
sp=tmp/"source.dds"; ap=tmp/"atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_sumo_fe_cvt_Exst/E3F4BA07_512x128.dds",sp)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_E3F4BA07_512x128_atlas.json",ap)

def gitblob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def bbox(m):
    yy,xx=np.nonzero(m)
    return None if not len(xx) else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def rect(shape,b):
    h,w=shape; x0,y0,x1,y1=map(int,b); m=np.zeros((h,w),bool); m[y0:y1,x0:x1]=1; return m
def dil(m,p=1):
    return np.asarray(Image.fromarray((m.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(p*2+1)))>0
def comp(im,bg=(64,64,64,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

sb=sp.read_bytes(); ab=ap.read_bytes(); cb=cand.read_bytes()
if gitblob(sb)!=SOURCE_BLOB_SHA1 or gitblob(ab)!=ATLAS_BLOB_SHA1: raise RuntimeError(("pinned blob drift",gitblob(sb),gitblob(ab)))
if sha(sb)!=SOURCE_SHA256 or sha(cb)!=CANDIDATE_SHA256: raise RuntimeError(("sha mismatch",sha(sb),sha(cb)))
if sb[:128]!=cb[:128]: raise RuntimeError("DDS header mismatch")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12); pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,mips)!=(2048,512,8192,1) or len(sb)!=128+W*H*4 or len(cb)!=len(sb): raise RuntimeError(("structure",W,H,pitch,mips,len(sb),len(cb)))
masks=(pf[4],pf[5],pf[6]); rawmode="BGRA" if masks==(0xff0000,0xff00,0xff) else "RGBA" if masks==(0xff,0xff00,0xff0000) else None
if not rawmode: raise RuntimeError(("rawmode",masks))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",rawmode)
raw_fin=Image.frombytes("RGBA",(W,H),cb[128:],"raw",rawmode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
fin=raw_fin.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(fin,dtype=np.uint8)

regions={int(r["idx"]):r["rect"] for r in json.loads(ab.decode("utf-8"))["regions"]}
expected={
0:[0,424,980,88],1:[980,424,980,88],2:[0,336,980,88],3:[980,336,980,88],
4:[0,248,980,88],5:[980,248,980,88],6:[0,160,980,88],7:[980,160,980,88],
8:[0,72,980,88],9:[980,72,980,88]
}
if regions!=expected: raise RuntimeError(("atlas drift",regions))
specs=[
 (0,"STAGE","스테이지"),(3,"GOAL E","골 E"),(4,"GOAL D","골 D"),(5,"GOAL C","골 C"),
 (6,"GOAL B","골 B"),(7,"GOAL A","골 A"),(8,"GOAL","골"),(9,"15 STAGE CONTINUOUS","15코스 연속")
]
protected_regions={1:"OUTRUN2SP",2:"OUTRUN2"}

source_masks=[]; allowed_masks=[]; rows=[]
for idx,en,ko in specs:
    x,y,cw,ch=regions[idx]; local=sa[y:y+ch,x:x+cw,3]>0; b=bbox(local)
    if not b: raise RuntimeError(("empty source",idx))
    ob=[x+b[0],y+b[1],x+b[2],y+b[3]]
    sm=np.zeros((H,W),bool); sm[y:y+ch,x:x+cw]=local
    source_masks.append(sm); allowed_masks.append(rect((H,W),ob))
    rows.append({"region_idx":idx,"source":en,"korean":ko,"cell":[x,y,cw,ch],"original_bbox":ob})
source_mask=np.logical_or.reduce(source_masks); allowed=np.logical_or.reduce(allowed_masks)

protected_mask=np.zeros((H,W),bool)
protected_bboxes={}
for idx,name in protected_regions.items():
    x,y,cw,ch=regions[idx]; local=sa[y:y+ch,x:x+cw,3]>0; b=bbox(local)
    if not b: raise RuntimeError(("empty protected",idx))
    protected_mask[y:y+ch,x:x+cw]|=local
    protected_bboxes[str(idx)]={"name":name,"bbox":[x+b[0],y+b[1],x+b[2],y+b[3]],"pixels":int(np.count_nonzero(local))}
# There must be no visible canonical alpha outside localized or protected regions.
unclassified=(sa[:,:,3]>0)&~source_mask&~protected_mask
if np.count_nonzero(unclassified): raise RuntimeError(("unclassified visible",int(np.count_nonzero(unclassified)),bbox(unclassified)))

expected_clean=sa.copy(); expected_clean[source_mask]=0
bclean=np.asarray(Image.open(bdir/"E3F4_CLEAN_PLATE.png").convert("RGBA"),dtype=np.uint8)
clean_diff=np.any(expected_clean!=bclean,axis=2)
if np.count_nonzero(clean_diff): raise RuntimeError(("producer clean differs",int(np.count_nonzero(clean_diff)),bbox(clean_diff)))

target_masks=[]; row_results=[]
for r,am in zip(rows,allowed_masks):
    tm=am&(fa[:,:,3]>0); lb=bbox(tm)
    if not lb: raise RuntimeError(("missing target",r["region_idx"]))
    ob=r["original_bbox"]; sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    d=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    if lw>sw or lh>sh or min(d)<=0: raise RuntimeError(("bbox/size/margin",r["region_idx"],ob,lb,d))
    target_masks.append(tm)
    row_results.append({**r,"localized_bbox":lb,"source_size":[sw,sh],"localized_size":[lw,lh],
      "delta_left":d[0],"delta_right":d[1],"delta_top":d[2],"delta_bottom":d[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})
target=np.logical_or.reduce(target_masks)

final_diff=np.any(fa!=sa,axis=2); alpha_diff=fa[:,:,3]!=sa[:,:,3]
outside=int(np.count_nonzero(final_diff&~allowed&~protected_mask))
alpha_out=int(np.count_nonzero(alpha_diff&~allowed&~protected_mask))
protected_changed=int(np.count_nonzero(final_diff&protected_mask))
render_diff=np.any(fa!=expected_clean,axis=2)
render_out=int(np.count_nonzero(render_diff&~target&~protected_mask))
source_residue=int(np.count_nonzero(source_mask&~target&render_diff))
overlap=0; touch=[]
for i in range(len(target_masks)):
  for j in range(i+1,len(target_masks)):
    ov=int(np.count_nonzero(target_masks[i]&target_masks[j])); near=int(np.count_nonzero(dil(target_masks[i],1)&target_masks[j]))
    overlap+=ov
    if ov or near: touch.append([rows[i]["region_idx"],rows[j]["region_idx"],ov,near])
target_protected_overlap=int(np.count_nonzero(target&protected_mask))
target_protected_near=int(np.count_nonzero(dil(target,1)&protected_mask))

# All localized labels share the same gray-blue source typography family.
style={}
for i,r in enumerate(row_results):
    px=fa[target_masks[i]]
    good=(np.abs(px[:,0].astype(int)-px[:,1].astype(int))<=45)&(px[:,2].astype(int)>=px[:,1].astype(int)-25)&(px[:,0]>=30)&(px[:,0]<=180)
    frac=float(np.mean(good)); style[str(r["region_idx"])]={"target_pixels":int(len(px)),"gray_blue_family_fraction":frac}
    if frac<0.90: raise RuntimeError(("style",r["region_idx"],frac))

if any([outside,alpha_out,protected_changed,render_out,source_residue,overlap,target_protected_overlap,target_protected_near]) or touch:
    raise RuntimeError(("gates",outside,alpha_out,protected_changed,render_out,source_residue,overlap,target_protected_overlap,target_protected_near,touch))

for name,m in [("C143_SOURCE_TEXT_MASK.png",source_mask),("C143_ALLOWED_BBOX_MASK.png",allowed),
               ("C143_TARGET_TEXT_MASK.png",target),("C143_PROTECTED_OUTRUN_MASK.png",protected_mask)]:
    Image.fromarray((m.astype(np.uint8)*255),"L").save(out/name)
clean_img=Image.fromarray(expected_clean,"RGBA"); clean_img.save(out/"C143_EXACT_CLEAN_PLATE.png")

cards=[]
for label,im in [("SOURCE",src),("CLEAN",clean_img),("FINAL",fin)]:
    z=comp(im).resize((1024,256),Image.Resampling.LANCZOS); c=Image.new("RGB",(1024,284),"white"); c.paste(z,(0,28)); ImageDraw.Draw(c).text((5,5),label,fill="black"); cards.append(c)
sheet=Image.new("RGB",(1024,852),"white")
for i,c in enumerate(cards): sheet.paste(c,(0,i*284))
sheet.save(out/"C143_E3F4_COMPARE.jpg",quality=96)

contacts=[]
for r in row_results:
    x0,y0,x1,y1=r["original_bbox"]; p=8; cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[comp(z).crop(cr) for z in (src,clean_img,fin)]
    outims=[]
    for z in ims:
      if z.width>600:
        sc=600/z.width; z=z.resize((600,max(1,int(z.height*sc))),Image.Resampling.NEAREST)
      outims.append(z)
    c=Image.new("RGB",(sum(z.width for z in outims)+12,max(z.height for z in outims)+28),"white"); xx=0
    for z in outims: c.paste(z,(xx,28)); xx+=z.width+6
    ImageDraw.Draw(c).text((5,5),f'{r["region_idx"]} {r["source"]} -> {r["korean"]}',fill="black"); contacts.append(c)
rw=max(c.width for c in contacts); rh=sum(c.height for c in contacts)+4*(len(contacts)-1)
rs=Image.new("RGB",(rw,rh),"white"); yy=0
for c in contacts: rs.paste(c,(0,yy)); yy+=c.height+4
rs.save(out/"C143_E3F4_ROW_CONTACT.jpg",quality=96)

rr=Image.new("RGB",(1024,568),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_fin)]):
    z=comp(im).resize((1024,256),Image.Resampling.LANCZOS); rr.paste(z,(0,i*284+28)); ImageDraw.Draw(rr).text((5,i*284+5),label,fill="black")
rr.save(out/"C143_E3F4_RAW_COMPARE.jpg",quality=96)

report={"schema_version":1,"role":"C","run":run,"queue_index":226,"asset":asset,"producer_run":"20261005-B-PRODUCTION67",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,"atlas_git_blob_sha1":ATLAS_BLOB_SHA1,"source_sha256":SOURCE_SHA256},
 "candidate_sha256":CANDIDATE_SHA256,"candidate_changed_by_C":False,
 "independent_method":"pinned canonical source+atlas; exact source alpha for 8 localized regions and 2 protected OutRun marks; exact transparent clean reconstruction; independent DDS/header/bbox/protected/overlap/style validation",
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":rawmode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "protected_regions":protected_bboxes,"rows":row_results,
 "machine_checks":{"unclassified_visible_source_pixels":int(np.count_nonzero(unclassified)),"producer_clean_exact_diff_pixels":int(np.count_nonzero(clean_diff)),
   "bbox_size_positive_margin":"8/8 PASS","final_outside":outside,"alpha_outside":alpha_out,"protected_changed":protected_changed,
   "render_outside_target":render_out,"source_residue":source_residue,"overlap":overlap,"touch_pairs":touch,
   "target_protected_overlap":target_protected_overlap,"target_protected_1px_near":target_protected_near,"style":style},
 "machine_status":"PASS","controller_visual_qa":"PENDING","decision":"PENDING_CONTROLLER_VISUAL_QA","RUNTIME_VALIDATION":"UNTESTED"}
(out/"C143_E3F4_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"E3F4BA07","index":226,"source_sha256":SOURCE_SHA256,"candidate_sha256":CANDIDATE_SHA256,
 "machine_status":"PASS","bbox_size_positive_margin":"8/8","clean_exact_diff_pixels":int(np.count_nonzero(clean_diff)),
 "outside":outside,"alpha_outside":alpha_out,"protected_changed":protected_changed,"render_outside_target":render_out,
 "source_residue":source_residue,"overlap":overlap,"touch_pairs":len(touch),"target_protected_overlap":target_protected_overlap,
 "runtime_validation":"UNTESTED","report":f"localization/graphics/role_C/{run}/C143_E3F4_MACHINE_QA.json"}
(wr/"C143_E3F4BA07.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False),flush=True)
