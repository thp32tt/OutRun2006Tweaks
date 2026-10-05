#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C152-FEF70E85"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/FEF70E85_512x512.dds"
cand=repo/"localization/graphics/hd_candidates"/asset
bdir=repo/"localization/graphics/role_B/20261005-B-PRODUCTION80"

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="48fd896aaa8ff2f269b659771f2618ea6a8426d5"
ATLAS_BLOB_SHA1="750c9f48f00508161f195a1a2515321cbebdab88"
SOURCE_SHA256="a1c7f7d6ca5d2440076e49477cefecbf5084b4188072f3427ff13e5da24bc518"
CANDIDATE_SHA256="e6d12ebf9b48192067c3f31bad0ffcb81f5f77c7370f7d43dfd9a4d04df5d086"

BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
tmp=Path("/tmp/outrun_C152"); tmp.mkdir(parents=True,exist_ok=True)
sp=tmp/"source.dds"; ap=tmp/"atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_sumo_fe_cvt_Exst/FEF70E85_512x512.dds",sp)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_FEF70E85_512x512_atlas.json",ap)

def gitblob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def bbox(m):
    yy,xx=np.nonzero(m)
    return None if not len(xx) else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def count(m): return int(np.count_nonzero(m))
def rect(shape,b):
    h,w=shape; x0,y0,x1,y1=map(int,b)
    m=np.zeros((h,w),bool); m[y0:y1,x0:x1]=1; return m
def comp(im,bg=(76,76,76,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

sb=sp.read_bytes(); ab=ap.read_bytes(); cb=cand.read_bytes()
if gitblob(sb)!=SOURCE_BLOB_SHA1 or gitblob(ab)!=ATLAS_BLOB_SHA1:
    raise RuntimeError(("pinned blob drift",gitblob(sb),gitblob(ab)))
if sha(sb)!=SOURCE_SHA256 or sha(cb)!=CANDIDATE_SHA256:
    raise RuntimeError(("sha mismatch",sha(sb),sha(cb)))
if sb[:128]!=cb[:128] or len(sb)!=len(cb):
    raise RuntimeError("DDS structure/header mismatch")

H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6])
mode="BGRA" if masks==(0xff0000,0xff00,0xff) else ("RGBA" if masks==(0xff,0xff00,0xff0000) else None)
if (W,H,pitch,mips)!=(2048,2048,8192,1) or mode!="BGRA" or len(sb)!=128+W*H*4:
    raise RuntimeError(("structure",W,H,pitch,mips,masks,len(sb)))

raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
raw_fin=Image.frombytes("RGBA",(W,H),cb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
fin=raw_fin.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(fin,dtype=np.uint8)

regions={int(r["idx"]):r for r in json.loads(ab.decode("utf-8"))["regions"]}
if sorted(regions)!=list(range(15)):
    raise RuntimeError(("atlas region drift",sorted(regions)))

translations={
0:("INDUSTRIAL COMPLEX","인더스트리얼 컴플렉스"),
1:("WATERFALLS","워터폴스"),
2:("TULIP GARDEN","튤립 가든"),
3:("SUNNY BEACH","서니 비치"),
4:("SNOW MOUNTAIN","스노 마운틴"),
5:("SKYSCRAPERS","스카이스크레이퍼스"),
6:("PALM BEACH","팜 비치"),
7:("NATIONAL PARK","내셔널 파크"),
8:("MILKY WAY","밀키 웨이"),
9:("METROPOLIS","메트로폴리스"),
10:("LOST CITY","로스트 시티"),
11:("LEGEND","레전드"),
12:("JUNGLE","정글"),
13:("IMPERIAL AVENUE","임페리얼 애비뉴"),
}
protected={14:"REVERSED"}

source_masks=[]; allowed_masks=[]; rows=[]
expected_source_bboxes={
0:[54,1937,1161,2024],1:[321,1804,1038,1899],2:[263,1694,1056,1788],
3:[283,1580,1063,1675],4:[106,1464,1034,1559],5:[255,1356,1056,1451],
6:[351,1241,1057,1335],7:[191,1134,1056,1227],8:[423,1023,1051,1112],
9:[347,908,1057,1003],10:[516,795,1050,890],11:[632,681,1055,775],
12:[623,573,1043,667],13:[36,467,1046,559]
}
for idx,(en,ko) in translations.items():
    x,y,cw,ch=map(int,regions[idx]["rect"])
    local=sa[y:y+ch,x:x+cw,3]>0
    bb=bbox(local)
    if not bb: raise RuntimeError(("empty source",idx))
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    if ob!=expected_source_bboxes[idx]:
        raise RuntimeError(("source bbox drift",idx,ob,expected_source_bboxes[idx]))
    sm=np.zeros((H,W),bool); sm[y:y+ch,x:x+cw]=local
    source_masks.append(sm); allowed_masks.append(rect((H,W),ob))
    rows.append({"region_idx":idx,"source":en,"korean":ko,"cell":[x,y,cw,ch],"original_bbox":ob})

source_mask=np.logical_or.reduce(source_masks)
allowed=np.logical_or.reduce(allowed_masks)

# Independent clean plate: localized source regions are transparent; protected REVERSED remains untouched.
expected_clean=sa.copy()
expected_clean[source_mask]=0
producer_clean=np.asarray(Image.open(bdir/"FEF_CLEAN_PLATE.png").convert("RGBA"),dtype=np.uint8)
clean_diff=np.any(expected_clean!=producer_clean,axis=2)
if count(clean_diff):
    raise RuntimeError(("producer clean differs",count(clean_diff),bbox(clean_diff)))

# Protected cell exact preservation.
protected_mask=np.zeros((H,W),bool)
protected_changed={}
for idx,name in protected.items():
    x,y,cw,ch=map(int,regions[idx]["rect"])
    protected_mask[y:y+ch,x:x+cw]=True
    d=np.any(sa[y:y+ch,x:x+cw]!=fa[y:y+ch,x:x+cw],axis=2)
    protected_changed[str(idx)]=count(d)
if any(protected_changed.values()):
    raise RuntimeError(("protected changed",protected_changed))

# Derive Korean target strictly as final pixels differing from independent clean inside each exact source bbox.
row_results=[]; target_masks=[]
for i,r in enumerate(rows):
    ob=r["original_bbox"]; am=allowed_masks[i]
    diff_clean=np.any(fa!=expected_clean,axis=2)
    tm=diff_clean & am
    lb=bbox(tm)
    if not lb: raise RuntimeError(("missing localized target",r["region_idx"]))
    sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    d=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    if lw>sw or lh>sh or min(d)<=0:
        raise RuntimeError(("bbox/size/margin",r["region_idx"],ob,lb,d))
    target_masks.append(tm)
    row_results.append({**r,"localized_bbox":lb,"source_size":[sw,sh],"localized_size":[lw,lh],
        "delta_left":d[0],"delta_right":d[1],"delta_top":d[2],"delta_bottom":d[3],
        "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

target=np.logical_or.reduce(target_masks)
final_diff=np.any(fa!=sa,axis=2)
alpha_diff=fa[:,:,3]!=sa[:,:,3]
render_diff=np.any(fa!=expected_clean,axis=2)
outside=count(final_diff & ~allowed & ~protected_mask)
alpha_out=count(alpha_diff & ~allowed & ~protected_mask)
protected_out=count(final_diff & protected_mask)
render_out=count(render_diff & ~target & ~protected_mask)
equal_source=np.all(fa==sa,axis=2)
source_residue=count(source_mask & ~target & equal_source)

overlap=0; touch=[]
from PIL import ImageFilter
for i in range(len(target_masks)):
    a=Image.fromarray((target_masks[i].astype(np.uint8)*255),"L")
    ag=np.asarray(a.filter(ImageFilter.MaxFilter(3)))>0
    for j in range(i+1,len(target_masks)):
        ov=count(target_masks[i]&target_masks[j]); near=count(ag&target_masks[j])
        overlap+=ov
        if ov or near: touch.append([rows[i]["region_idx"],rows[j]["region_idx"],ov,near])

target_protected_overlap=count(target&protected_mask)
target_protected_near=count((np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0)&protected_mask)

if any([outside,alpha_out,protected_out,render_out,source_residue,overlap,target_protected_overlap,target_protected_near]) or touch:
    raise RuntimeError(("gates",outside,alpha_out,protected_out,render_out,source_residue,overlap,target_protected_overlap,target_protected_near,touch))

for name,m in [
 ("C152_SOURCE_TEXT_MASK.png",source_mask),("C152_ALLOWED_BBOX_MASK.png",allowed),
 ("C152_TARGET_TEXT_MASK.png",target),("C152_PROTECTED_MASK.png",protected_mask)
]:
    Image.fromarray((m.astype(np.uint8)*255),"L").save(out/name)
clean_img=Image.fromarray(expected_clean,"RGBA"); clean_img.save(out/"C152_EXACT_CLEAN_PLATE.png")

cards=[]
for label,im in [("SOURCE",src),("CLEAN",clean_img),("FINAL",fin)]:
    z=comp(im).resize((768,768),Image.Resampling.NEAREST)
    c=Image.new("RGB",(768,794),"white"); c.paste(z,(0,26)); ImageDraw.Draw(c).text((5,5),label,fill="black"); cards.append(c)
sheet=Image.new("RGB",(768,2382),"white")
for i,c in enumerate(cards): sheet.paste(c,(0,i*794))
sheet.save(out/"C152_FEF_COMPARE.jpg",quality=96)

contacts=[]
for r in row_results:
    x0,y0,x1,y1=r["original_bbox"]; p=8
    cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[comp(z).crop(cr) for z in (src,clean_img,fin)]
    outims=[]
    for z in ims:
        if z.width>560:
            sc=560/z.width; z=z.resize((560,max(1,int(z.height*sc))),Image.Resampling.NEAREST)
        outims.append(z)
    c=Image.new("RGB",(sum(z.width for z in outims)+12,max(z.height for z in outims)+28),"white")
    xx=0
    for z in outims: c.paste(z,(xx,28)); xx+=z.width+6
    ImageDraw.Draw(c).text((5,5),f'{r["region_idx"]} {r["source"]} -> {r["korean"]}',fill="black")
    contacts.append(c)
rw=max(c.width for c in contacts); rh=sum(c.height for c in contacts)+4*(len(contacts)-1)
rs=Image.new("RGB",(rw,rh),"white"); yy=0
for c in contacts: rs.paste(c,(0,yy)); yy+=c.height+4
rs.save(out/"C152_FEF_ROW_CONTACT.jpg",quality=96)

rr=Image.new("RGB",(768,1588),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_fin)]):
    z=comp(im).resize((768,768),Image.Resampling.NEAREST); rr.paste(z,(0,i*794+26)); ImageDraw.Draw(rr).text((5,i*794+5),label,fill="black")
rr.save(out/"C152_FEF_RAW_COMPARE.jpg",quality=96)

report={
 "schema_version":1,"role":"C","run":run,"queue_index":236,"asset":asset,"producer_run":"20261005-B-PRODUCTION80",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,"atlas_git_blob_sha1":ATLAS_BLOB_SHA1,"source_sha256":SOURCE_SHA256},
 "candidate_sha256":CANDIDATE_SHA256,"candidate_changed_by_C":False,
 "semantic_binding":{"localized":{str(k):v[0] for k,v in translations.items()},"translations":{str(k):v[1] for k,v in translations.items()},"protected":{"14":"REVERSED"}},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "rows":row_results,
 "machine_checks":{"producer_clean_exact_diff_pixels":count(clean_diff),"bbox_size_positive_margin":"14/14 PASS",
    "final_outside":outside,"alpha_outside":alpha_out,"protected_changed":protected_out,"render_outside_target":render_out,
    "source_residue":source_residue,"overlap":overlap,"touch_pairs":touch,
    "target_protected_overlap":target_protected_overlap,"target_protected_1px_near":target_protected_near,
    "protected_regions_changed_pixels":protected_changed},
 "machine_status":"PASS","controller_visual_qa":"PENDING","decision":"PENDING_CONTROLLER_VISUAL_QA","RUNTIME_VALIDATION":"UNTESTED"
}
(out/"C152_FEF_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"FEF70E85","index":236,"source_sha256":SOURCE_SHA256,"candidate_sha256":CANDIDATE_SHA256,
 "machine_status":"PASS","bbox_size_positive_margin":"14/14","clean_exact_diff_pixels":count(clean_diff),"outside":outside,"alpha_outside":alpha_out,
 "protected_changed":protected_out,"render_outside_target":render_out,"source_residue":source_residue,"overlap":overlap,"touch_pairs":len(touch),
 "target_protected_overlap":target_protected_overlap,"target_protected_1px_near":target_protected_near,
 "runtime_validation":"UNTESTED","report":f"localization/graphics/role_C/{run}/C152_FEF_MACHINE_QA.json"}
(wr/"C152_FEF70E85.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False),flush=True)
