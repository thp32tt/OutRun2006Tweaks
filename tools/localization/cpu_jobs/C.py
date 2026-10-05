#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C158-BA0147DA"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds"
cand=repo/"localization/graphics/hd_candidates"/asset
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="4a0ffb723e48313e3bdd7106dfadacd36cb212e8"
ATLAS_BLOB_SHA1="7f7432f469c86362670c8e2ca7a2f0473b64f694"
SOURCE_SHA256="f83f58483aab7a99ffe230c86eaa0527d9b7323be36808bdf69f2817e29c9f61"
CANDIDATE_SHA256="869cf1bea8b27dcc89f5b2ab68f9dd163e4bf41fa6de4b53c7b3f19b3b1c74ad"

tmp=Path("/tmp/outrun_C158"); tmp.mkdir(parents=True,exist_ok=True)
sp=tmp/"source.dds"; apath=tmp/"atlas.json"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds",sp)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_BA0147DA_512x512_atlas.json",apath)

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
if atlas.get("regions_count")!=60: raise RuntimeError(("atlas drift",atlas.get("regions_count")))
regions={r["idx"]:r for r in atlas["regions"]}
specs=[
 (14,"HEART ATTACK","하트 어택","red_big","left"),
 (15,"SHOWROOM","쇼룸","red_big","left"),
 (16,"COAST 2 COAST","코스트 2 코스트","red_big","left"),
 (17,"OUTRUN","아웃런","red_big","left"),
 (25,"SELECT STAR SIGN","별자리 선택","dark_menu","left"),
 (26,"SELECT PHOTO","사진 선택","dark_menu","left"),
 (27,"SELECT NATIONALITY","국적 선택","dark_menu","left"),
 (28,"ENTER NAME","이름 입력","dark_menu","left"),
 (30,"DONE","완료","dark_done_large","left"),
 (43,"PROFESSIONAL","프로","orange_prof","right"),
 (44,"OUTRUN","아웃런","red_small","right"),
 (53,"DONE","완료","dark_done_small","left"),
]
protected_semantics={"character_names":["CLARISSA","JENNIFER","WOLF","ALBERTO","HOLLY","SAM"],"car_color":["VERDE MUGELLO"],"zodiac_icons":"preserve","logos_icons":"preserve"}

source_mask=np.zeros((H,W),bool)
allowed=np.zeros((H,W),bool)
rows=[]; group_source={}
for idx,en,ko,group,align in specs:
    x,y,cw,ch=regions[idx]["rect"]
    alpha=sa[y:y+ch,x:x+cw,3]
    lm=alpha>0
    bb=bbox(lm)
    if not bb: raise RuntimeError(("empty canonical alpha",idx,en))
    pix=count(lm)
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    source_mask[y:y+ch,x:x+cw] |= lm
    allowed[ob[1]:ob[3],ob[0]:ob[2]]=True
    hi=alpha>=192
    vals=sa[y:y+ch,x:x+cw,:3][hi]
    if len(vals): group_source.setdefault(group,[]).append(vals)
    rows.append({"region_idx":idx,"source":en,"korean":ko,"group":group,"alignment":align,
                 "cell":[x,y,cw,ch],"original_bbox":ob,"source_mask_pixels":pix})

protected=(sa[:,:,3]>0)&~allowed
clean=sa.copy(); clean[source_mask,3]=0
clean_diff=np.any(clean!=sa,axis=2)
clean_outside=count(clean_diff & ~source_mask)
clean_unchanged_inside=count(source_mask & ~clean_diff)
clean_protected=count(clean_diff & protected)
clean_alpha_outside=count((clean[:,:,3]!=sa[:,:,3]) & ~source_mask)
if any([clean_outside,clean_unchanged_inside,clean_protected,clean_alpha_outside]):
    raise RuntimeError(("clean gates",clean_outside,clean_unchanged_inside,clean_protected,clean_alpha_outside))

render_diff=np.any(fa!=clean,axis=2)
row_results=[]; target_masks=[]; group_candidate={}
alignment_fail=[]
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
    if r["alignment"]=="left" and d[0]>8: alignment_fail.append([r["region_idx"],"left",d[0]])
    if r["alignment"]=="right" and d[1]>8: alignment_fail.append([r["region_idx"],"right",d[1]])
    target_masks.append(tm)
    cvals=fa[:,:,:3][tm & (fa[:,:,3]>=192)]
    if len(cvals): group_candidate.setdefault(r["group"],[]).append(cvals)
    row_results.append({**r,"localized_bbox":lb,"source_size":[sw,sh],"localized_size":[lw,lh],
        "delta_left":d[0],"delta_right":d[1],"delta_top":d[2],"delta_bottom":d[3],
        "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
        "source_alignment_anchor":"PASS" if not ((r["alignment"]=="left" and d[0]>8) or (r["alignment"]=="right" and d[1]>8)) else "FAIL"})
if alignment_fail: raise RuntimeError(("alignment anchor drift",alignment_fail))

target=np.logical_or.reduce(target_masks)
final_diff=np.any(fa!=sa,axis=2); alpha_diff=fa[:,:,3]!=sa[:,:,3]
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

style_checks={}
for g in sorted(group_source):
    svals=np.concatenate(group_source[g],axis=0)
    cvals=np.concatenate(group_candidate.get(g,[]),axis=0) if group_candidate.get(g) else np.empty((0,3),dtype=np.uint8)
    if len(svals)<30 or len(cvals)<30: raise RuntimeError(("style sample small",g,len(svals),len(cvals)))
    sm=[int(np.median(svals[:,k])) for k in range(3)]
    cm=[int(np.median(cvals[:,k])) for k in range(3)]
    delta=[abs(cm[k]-sm[k]) for k in range(3)]
    if max(delta)>3: raise RuntimeError(("fill style drift",g,sm,cm,delta))
    style_checks[g]={"source_fill_median_rgb":sm,"localized_fill_median_rgb":cm,"fill_median_abs_delta":delta,"status":"PASS"}

for name,m in [
    ("C158_SOURCE_TEXT_MASK.png",source_mask),
    ("C158_ALLOWED_BBOX_MASK.png",allowed),
    ("C158_TARGET_TEXT_MASK.png",target),
    ("C158_PROTECTED_MASK.png",protected)
]:
    Image.fromarray((m.astype(np.uint8)*255),"L").save(out/name)
clean_img=Image.fromarray(clean,"RGBA"); clean_img.save(out/"C158_VERIFIED_CLEAN_PLATE.png")

stack=Image.new("RGB",(1024,3*1050),"white")
for i,(label,im) in enumerate([("SOURCE",src),("CLEAN",clean_img),("FINAL",fin)]):
    z=comp(im).resize((1024,1024),Image.Resampling.NEAREST); stack.paste(z,(0,i*1050+26)); ImageDraw.Draw(stack).text((5,i*1050+5),label,fill="black")
stack.save(out/"C158_BA_COMPARE.jpg",quality=96)

cards=[]
for r in row_results:
    x0,y0,x1,y1=r["original_bbox"]; p=14
    cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[comp(z).crop(cr) for z in (src,clean_img,fin)]
    maxw=max(z.width for z in ims); sc=min(2.0,650/max(1,maxw))
    ims=[z.resize((max(1,int(z.width*sc)),max(1,int(z.height*sc))),Image.Resampling.NEAREST) for z in ims]
    c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+34),"white"); xx=0
    for z in ims: c.paste(z,(xx,34)); xx+=z.width+6
    ImageDraw.Draw(c).text((5,5),f'{r["region_idx"]} {r["source"]} -> {r["korean"]} [{r["alignment"]}]',fill="black"); cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+4*(len(cards)-1)),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.thumbnail((2200,16000),Image.Resampling.LANCZOS); sheet.save(out/"C158_BA_ROW_CONTACT.jpg",quality=96)

rr=Image.new("RGB",(1024,2*1050),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_fin)]):
    z=comp(im).resize((1024,1024),Image.Resampling.NEAREST); rr.paste(z,(0,i*1050+26)); ImageDraw.Draw(rr).text((5,i*1050+5),label,fill="black")
rr.save(out/"C158_BA_RAW_COMPARE.jpg",quality=96)

report={"schema_version":1,"role":"C","run":run,"queue_index":212,"asset":asset,"producer_run":"20261005-B-PRODUCTION85",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,"atlas_git_blob_sha1":ATLAS_BLOB_SHA1,"source_sha256":SOURCE_SHA256},
 "candidate_sha256":CANDIDATE_SHA256,"candidate_changed_by_C":False,
 "independent_method":"C re-downloaded pinned canonical DDS+atlas, used only the controller-reviewed semantic region IDs, independently rebuilt canonical alpha source masks/exact bboxes/transparent clean plate and protected artwork from source pixels, decoded the committed candidate, and recomputed containment/protected/overlap/alignment/style gates without producer masks.",
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "semantic_binding":{"rows":[{"region_idx":i,"source":en,"korean":ko,"group":g,"alignment":al} for i,en,ko,g,al in specs],"protected":protected_semantics},
 "rows":row_results,"style_checks":style_checks,
 "machine_checks":{"clean_changed_outside_source_mask":clean_outside,"clean_unchanged_inside_source_mask":clean_unchanged_inside,
   "clean_protected_changed":clean_protected,"clean_alpha_changed_outside_source_mask":clean_alpha_outside,
   "bbox_size_positive_margin":"12/12 PASS","source_alignment_anchor":"12/12 PASS",
   "final_outside":outside,"alpha_outside":alpha_out,"protected_changed":protected_changed,"render_outside_target":render_out,
   "source_residue":source_residue,"target_protected_overlap":target_protected_overlap,"target_protected_1px_near":target_protected_near,
   "overlap":overlap,"touch_pairs":touch},
 "machine_status":"PASS","controller_visual_qa":"PENDING","decision":"PENDING_CONTROLLER_VISUAL_QA","RUNTIME_VALIDATION":"UNTESTED"}
(out/"C158_BA_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"BA0147DA","index":212,"source_sha256":SOURCE_SHA256,"candidate_sha256":CANDIDATE_SHA256,
 "machine_status":"PASS","bbox_size_positive_margin":"12/12","source_alignment_anchor":"12/12",
 "clean_outside":clean_outside,"clean_unchanged_inside":clean_unchanged_inside,"clean_protected":clean_protected,
 "outside":outside,"alpha_outside":alpha_out,"protected_changed":protected_changed,"render_outside_target":render_out,"source_residue":source_residue,
 "target_protected_overlap":target_protected_overlap,"target_protected_1px_near":target_protected_near,"overlap":overlap,"touch_pairs":len(touch),
 "style_checks":style_checks,"runtime_validation":"UNTESTED","report":f"localization/graphics/role_C/{run}/C158_BA_MACHINE_QA.json"}
(wr/"C158_BA0147DA.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False),flush=True)
