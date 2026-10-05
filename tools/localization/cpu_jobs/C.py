#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C157-8C259C68"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/8C259C68_512x512.dds"
cand=repo/"localization/graphics/hd_candidates"/asset
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="4a95a48c9c34f2ddd786340e4323d6779b7a103b"
ATLAS_BLOB_SHA1="6061128430caeb04773ac8caa7918629eeef8ba8"
SOURCE_SHA256="dfc72a0d66c30257066d56c2b325dca00832ceeda0d07d46443c27b396e0cb38"
CANDIDATE_SHA256="03f52892acd091496c53c19a0a48c2f9c2d1acf9b05d9f96801ff4032e756b03"

tmp=Path("/tmp/outrun_C157"); tmp.mkdir(parents=True,exist_ok=True)
sp=tmp/"source.dds"; apath=tmp/"atlas.json"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/8C259C68_512x512.dds",sp)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_8C259C68_512x512_atlas.json",apath)

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
    raise RuntimeError("DDS structure/header mismatch")
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

atlas=json.loads(ab.decode())
if atlas.get("regions_count")!=6: raise RuntimeError(("atlas drift",atlas.get("regions_count")))
regions={r["idx"]:r for r in atlas["regions"]}
specs=[
 (0,"Drive against the Ghost Cars and go for the course records!","고스트 카와 달리며 코스 기록에 도전하세요!"),
 (1,"Buy your OutRun items here!","여기서 아웃런 아이템을 구매하세요!"),
 (2,"Try to reach the goal with your girlfriend!","여자친구와 함께 골에 도착하세요!"),
 (3,"Try to win Hearts by meeting your girlfriend's demands!","여자친구의 요구를 들어주고 하트를 획득하세요!"),
 (4,"Complete Race and Heart Attack missions to win OR Miles!","레이스와 하트 어택 미션을 완료해 OR 마일을 획득하세요!"),
 (5,"Online and LAN OutRun for up to 6 players","온라인/LAN 아웃런 최대 6인 플레이"),
]

source_mask=np.zeros((H,W),bool)
allowed=np.zeros((H,W),bool)
rows=[]
style_samples=[]
for idx,en,ko in specs:
    x,y,cw,ch=regions[idx]["rect"]
    alpha=sa[y:y+ch,x:x+cw,3]
    lm=alpha>0
    bb=bbox(lm)
    if not bb: raise RuntimeError(("empty canonical alpha",idx))
    pix=count(lm); frac=pix/(cw*ch)
    if frac>0.30 or (bb[3]-bb[1])>ch*0.85:
        raise RuntimeError(("ambiguous non-text alpha",idx,frac,bb,[x,y,cw,ch]))
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    source_mask[y:y+ch,x:x+cw] |= lm
    allowed[ob[1]:ob[3],ob[0]:ob[2]]=True
    hi=(alpha>=192)
    vals=sa[y:y+ch,x:x+cw,:3][hi]
    if len(vals): style_samples.append(vals)
    rows.append({"region_idx":idx,"source":en,"korean":ko,"cell":[x,y,cw,ch],
                 "original_bbox":ob,"source_mask_pixels":pix,"alpha_fraction":frac})

protected=(sa[:,:,3]>0)&~allowed
clean=sa.copy()
clean[source_mask,3]=0
clean_diff=np.any(clean!=sa,axis=2)
clean_outside=count(clean_diff & ~source_mask)
clean_unchanged_inside=count(source_mask & ~clean_diff)
clean_protected=count(clean_diff & protected)
clean_alpha_outside=count((clean[:,:,3]!=sa[:,:,3]) & ~source_mask)
if any([clean_outside,clean_unchanged_inside,clean_protected,clean_alpha_outside]):
    raise RuntimeError(("clean gates",clean_outside,clean_unchanged_inside,clean_protected,clean_alpha_outside))

render_diff=np.any(fa!=clean,axis=2)
row_results=[]; target_masks=[]
for r in rows:
    x0,y0,x1,y1=r["original_bbox"]
    am=np.zeros((H,W),bool); am[y0:y1,x0:x1]=True
    tm=render_diff & am
    lb=bbox(tm)
    if not lb: raise RuntimeError(("missing target",r["region_idx"]))
    sw,sh=x1-x0,y1-y0; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    d=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
    if lw>sw or lh>sh or min(d)<=0:
        raise RuntimeError(("bbox/size/margin",r["region_idx"],r["original_bbox"],lb,d))
    target_masks.append(tm)
    row_results.append({**r,"localized_bbox":lb,"source_size":[sw,sh],"localized_size":[lw,lh],
        "delta_left":d[0],"delta_right":d[1],"delta_top":d[2],"delta_bottom":d[3],
        "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

target=np.logical_or.reduce(target_masks)
final_diff=np.any(fa!=sa,axis=2)
alpha_diff=fa[:,:,3]!=sa[:,:,3]
outside=count(final_diff & ~allowed)
alpha_out=count(alpha_diff & ~allowed)
protected_changed=count(final_diff & protected)
render_out=count(render_diff & ~target)
source_residue=count(source_mask & (fa[:,:,3]>0) & ~target)
target_protected_overlap=count(target & protected)
target_protected_near=count((np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0)&protected)

overlap=0; touch=[]
for i in range(len(target_masks)):
    ag=np.asarray(Image.fromarray((target_masks[i].astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0
    for j in range(i+1,len(target_masks)):
        ov=count(target_masks[i]&target_masks[j]); near=count(ag&target_masks[j]); overlap+=ov
        if ov or near: touch.append([row_results[i]["region_idx"],row_results[j]["region_idx"],ov,near])

if any([outside,alpha_out,protected_changed,render_out,source_residue,target_protected_overlap,target_protected_near,overlap]) or touch:
    raise RuntimeError(("final gates",outside,alpha_out,protected_changed,render_out,source_residue,target_protected_overlap,target_protected_near,overlap,touch))

# Source-family style diagnostics: canonical high-alpha fill vs localized high-alpha fill.
src_samples=np.concatenate(style_samples,axis=0) if style_samples else np.empty((0,3),dtype=np.uint8)
cand_hi=target & (fa[:,:,3]>=192)
cand_samples=fa[:,:,:3][cand_hi]
if len(src_samples)<100 or len(cand_samples)<100: raise RuntimeError(("style sample small",len(src_samples),len(cand_samples)))
src_median=[int(np.median(src_samples[:,k])) for k in range(3)]
cand_median=[int(np.median(cand_samples[:,k])) for k in range(3)]
style_delta=[abs(cand_median[k]-src_median[k]) for k in range(3)]
if max(style_delta)>3: raise RuntimeError(("fill style drift",src_median,cand_median,style_delta))

for name,m in [
    ("C157_SOURCE_TEXT_MASK.png",source_mask),
    ("C157_ALLOWED_BBOX_MASK.png",allowed),
    ("C157_TARGET_TEXT_MASK.png",target),
    ("C157_PROTECTED_MASK.png",protected)
]:
    Image.fromarray((m.astype(np.uint8)*255),"L").save(out/name)
clean_img=Image.fromarray(clean,"RGBA"); clean_img.save(out/"C157_VERIFIED_CLEAN_PLATE.png")

cards=[]
for label,im in [("SOURCE",src),("CLEAN",clean_img),("FINAL",fin)]:
    z=comp(im).resize((1024,1024),Image.Resampling.NEAREST)
    c=Image.new("RGB",(1024,1050),"white"); c.paste(z,(0,26)); ImageDraw.Draw(c).text((5,5),label,fill="black"); cards.append(c)
sheet=Image.new("RGB",(1024,3150),"white")
for i,c in enumerate(cards): sheet.paste(c,(0,i*1050))
sheet.save(out/"C157_8C_COMPARE.jpg",quality=96)

contacts=[]
for r in row_results:
    x0,y0,x1,y1=r["original_bbox"]; p=16
    cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[comp(z).crop(cr) for z in (src,clean_img,fin)]
    outims=[]
    for z in ims:
        if z.width>700:
            sc=700/z.width; z=z.resize((700,max(1,int(z.height*sc))),Image.Resampling.NEAREST)
        outims.append(z)
    c=Image.new("RGB",(sum(z.width for z in outims)+12,max(z.height for z in outims)+34),"white"); xx=0
    for z in outims: c.paste(z,(xx,34)); xx+=z.width+6
    ImageDraw.Draw(c).text((5,5),f'{r["region_idx"]} {r["source"]} -> {r["korean"]}',fill="black")
    contacts.append(c)
rw=max(c.width for c in contacts); rh=sum(c.height for c in contacts)+4*(len(contacts)-1)
rs=Image.new("RGB",(rw,rh),"white"); yy=0
for c in contacts: rs.paste(c,(0,yy)); yy+=c.height+4
rs.thumbnail((2200,12000),Image.Resampling.LANCZOS)
rs.save(out/"C157_8C_ROW_CONTACT.jpg",quality=96)

rr=Image.new("RGB",(1024,2100),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_fin)]):
    z=comp(im).resize((1024,1024),Image.Resampling.NEAREST); rr.paste(z,(0,i*1050+26)); ImageDraw.Draw(rr).text((5,i*1050+5),label,fill="black")
rr.save(out/"C157_8C_RAW_COMPARE.jpg",quality=96)

report={"schema_version":1,"role":"C","run":run,"queue_index":188,"asset":asset,"producer_run":"20261005-B-PRODUCTION81",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,
                      "atlas_git_blob_sha1":ATLAS_BLOB_SHA1,"source_sha256":SOURCE_SHA256},
 "candidate_sha256":CANDIDATE_SHA256,"candidate_changed_by_C":False,
 "independent_method":"C re-downloaded pinned canonical DDS+atlas, independently reconstructed each row alpha source mask and exact bbox, rebuilt the transparent clean plate, decoded the committed candidate, and recomputed containment/protected/overlap/style gates without consuming producer masks.",
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "semantic_binding":{"readable_mirror_y_order":True,"rows":[{"region_idx":i,"source":en,"korean":ko} for i,en,ko in specs]},
 "rows":row_results,
 "machine_checks":{"clean_changed_outside_source_mask":clean_outside,"clean_unchanged_inside_source_mask":clean_unchanged_inside,
   "clean_protected_changed":clean_protected,"clean_alpha_changed_outside_source_mask":clean_alpha_outside,
   "bbox_size_positive_margin":"6/6 PASS","final_outside":outside,"alpha_outside":alpha_out,
   "protected_changed":protected_changed,"render_outside_target":render_out,"source_residue":source_residue,
   "target_protected_overlap":target_protected_overlap,"target_protected_1px_near":target_protected_near,
   "overlap":overlap,"touch_pairs":touch,
   "source_fill_median_rgb":src_median,"localized_fill_median_rgb":cand_median,"fill_median_abs_delta":style_delta},
 "machine_status":"PASS","controller_visual_qa":"PENDING","decision":"PENDING_CONTROLLER_VISUAL_QA","RUNTIME_VALIDATION":"UNTESTED"}
(out/"C157_8C_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"8C259C68","index":188,"source_sha256":SOURCE_SHA256,"candidate_sha256":CANDIDATE_SHA256,
 "machine_status":"PASS","bbox_size_positive_margin":"6/6","clean_outside":clean_outside,"clean_unchanged_inside":clean_unchanged_inside,
 "clean_protected":clean_protected,"outside":outside,"alpha_outside":alpha_out,"protected_changed":protected_changed,
 "render_outside_target":render_out,"source_residue":source_residue,"target_protected_overlap":target_protected_overlap,
 "target_protected_1px_near":target_protected_near,"overlap":overlap,"touch_pairs":len(touch),
 "source_fill_median_rgb":src_median,"localized_fill_median_rgb":cand_median,"fill_median_abs_delta":style_delta,
 "runtime_validation":"UNTESTED","report":f"localization/graphics/role_C/{run}/C157_8C_MACHINE_QA.json"}
(wr/"C157_8C259C68.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False),flush=True)
