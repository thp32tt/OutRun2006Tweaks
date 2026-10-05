#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request,statistics
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C149-E95DA5"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/E95DA5_512x256.dds"
cand=repo/"localization/graphics/hd_candidates"/asset
bdir=repo/"localization/graphics/role_B/20261005-B-PRODUCTION73"

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="ee939d33fd363be135e681b076021c92cddcb489"
ATLAS_BLOB_SHA1="d1cbe695add81e599424c29aa40539bb6875ef5a"
SOURCE_SHA256="33077919771f580491b8ea1011401dc22df640f87b5b0e6f602b112dbdb07b81"
CANDIDATE_SHA256="d039f8d01ea744224caff7bb6c4f5d72233cd9bde48555dcb642008df91ac92b"

BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
tmp=Path("/tmp/outrun_C147")
tmp.mkdir(parents=True,exist_ok=True)
sp=tmp/"source.dds"
ap=tmp/"atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_sumo_fe_cvt_Exst/E95DA5_512x256.dds",sp)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_00E95DA5_512x256_atlas.json",ap)

def gitblob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def bbox(m):
    yy,xx=np.nonzero(m)
    return None if not len(xx) else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def rect(shape,b):
    h,w=shape
    x0,y0,x1,y1=map(int,b)
    m=np.zeros((h,w),bool)
    m[y0:y1,x0:x1]=1
    return m
def dil(m,p=1):
    return np.asarray(Image.fromarray((m.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(p*2+1)))>0
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg)
    z.alpha_composite(im)
    return z.convert("RGB")
def count(m): return int(np.count_nonzero(m))

sb=sp.read_bytes()
ab=ap.read_bytes()
cb=cand.read_bytes()
if gitblob(sb)!=SOURCE_BLOB_SHA1 or gitblob(ab)!=ATLAS_BLOB_SHA1:
    raise RuntimeError(("pinned blob drift",gitblob(sb),gitblob(ab)))
if sha(sb)!=SOURCE_SHA256 or sha(cb)!=CANDIDATE_SHA256:
    raise RuntimeError(("sha mismatch",sha(sb),sha(cb)))
if sb[:128]!=cb[:128]:
    raise RuntimeError("DDS header mismatch")

H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,mips)!=(2048,1024,8192,1) or len(sb)!=128+W*H*4 or len(cb)!=len(sb):
    raise RuntimeError(("structure",W,H,pitch,mips,len(sb),len(cb)))
masks=(pf[4],pf[5],pf[6])
rawmode="RGBA" if masks==(0xff,0xff00,0xff0000) else "BGRA" if masks==(0xff0000,0xff00,0xff) else None
if not rawmode:
    raise RuntimeError(("rawmode",masks))

raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",rawmode)
raw_fin=Image.frombytes("RGBA",(W,H),cb[128:],"raw",rawmode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
fin=raw_fin.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
fa=np.asarray(fin,dtype=np.uint8)

regions={int(r["idx"]):r for r in json.loads(ab.decode("utf-8"))["regions"]}
if sorted(regions)!=list(range(27)):
    raise RuntimeError(("atlas region drift",sorted(regions)))

specs=[
    (5,"FERRARI CARS","페라리 차량","dark"),
    (6,"CAR COLORS","차량 색상","dark"),
    (13,"SHOWROOM ITEMS","쇼룸 아이템","white"),
    (14,"GAME MODES","게임 모드","white"),
    (15,"FERRARI'S","페라리","white"),
    (16,"COURSES","코스","white"),
    (17,"CAR COLOURS","차량 색상","white"),
    (18,"BONUS MATERIAL","보너스 자료","white"),
    (19,"BGMUSIC","BGM","white"),
    (24,"UNAVAILABLE","이용 불가","pill"),
    (25,"SOLD","판매 완료","pill"),
]
preserved={
    0:"decorative panel",
    1:"Night Flight (song title)",2:"Magical Sound Shower (song title)",3:"Life Was A Bore (song title)",4:"Keep Your Heart (song title)",
    7:"BGM (translation unchanged)",
    8:"Alberto's Antics Vol.5",9:"Alberto's Antics Vol.4",10:"Alberto's Antics Vol.3",11:"Alberto's Antics Vol.2",12:"Alberto's Antics Vol.1",
    20:"You cannot buy this item yet",21:"You already own this item",
    22:"yellow bar artwork",23:"gray bar artwork",26:"separator artwork"
}

def strengthened_pill_source_mask(arr):
    h,w,_=arr.shape
    m=np.zeros((h,w),bool)
    row_bg={}
    for y in range(h):
        vals=[]
        for x in range(4,max(4,w-4)):
            r,g,b,a=[int(v) for v in arr[y,x]]
            if a>=245 and not (g>105 and b>105 and max(r,g,b)-min(r,g,b)<95):
                vals.append((r,g,b,a))
        if vals:
            row_bg[y]=tuple(int(round(statistics.median(v[k] for v in vals))) for k in range(4))
    for y,bg in row_bg.items():
        br,bg_g,bb,ba=bg
        for x in range(w):
            r,g,b,a=[int(v) for v in arr[y,x]]
            if a<16:
                continue
            if (g-bg_g)>=18 and (b-bb)>=18 and r>=br-28 and max(r,g,b)-min(r,g,b)<=115:
                m[y,x]=True
    tight=bbox(m)
    if tight:
        x0,y0,x1,y1=tight
        for y in range(y0,y1):
            bg=row_bg.get(y)
            if not bg:
                continue
            br,bg_g,bb,ba=bg
            for x in range(x0,x1):
                r,g,b,a=[int(v) for v in arr[y,x]]
                if a<16:
                    continue
                if max(abs(r-br),abs(g-bg_g),abs(b-bb))>6:
                    m[y,x]=True
        grown=dil(m,1)
        clipped=np.zeros_like(m)
        clipped[y0:y1,x0:x1]=grown[y0:y1,x0:x1]
        m=clipped
    return m,row_bg

source_masks=[]
allowed_masks=[]
rows=[]
pill_bg={}
for idx,en,ko,group in specs:
    x,y,cw,ch=regions[idx]["rect"]
    cell=sa[y:y+ch,x:x+cw,:]
    if group=="pill":
        local,rb=strengthened_pill_source_mask(cell)
        pill_bg[idx]=rb
    else:
        local=cell[:,:,3]>0
    b=bbox(local)
    if not b:
        raise RuntimeError(("empty source text",idx,en))
    ob=[x+b[0],y+b[1],x+b[2],y+b[3]]
    sm=np.zeros((H,W),bool)
    sm[y:y+ch,x:x+cw]=local
    source_masks.append(sm)
    allowed_masks.append(rect((H,W),ob))
    rows.append({"region_idx":idx,"source":en,"korean":ko,"group":group,"cell":[x,y,cw,ch],"original_bbox":ob,"source_mask_pixels":count(local)})

source_mask=np.logical_or.reduce(source_masks)
allowed=np.logical_or.reduce(allowed_masks)

# Independent exact clean reconstruction.
expected_clean=sa.copy()
for r,sm in zip(rows,source_masks):
    idx=r["region_idx"]
    if r["group"]!="pill":
        expected_clean[sm]=0
    else:
        x,y,cw,ch=r["cell"]
        local=sm[y:y+ch,x:x+cw]
        for yy,bg in pill_bg[idx].items():
            xs=np.nonzero(local[yy])[0]
            if len(xs):
                expected_clean[y+yy,x+xs,:]=np.asarray(bg,dtype=np.uint8)

bclean=np.asarray(Image.open(bdir/"E95_CLEAN_PLATE.png").convert("RGBA"),dtype=np.uint8)
clean_diff=np.any(expected_clean!=bclean,axis=2)
if count(clean_diff):
    raise RuntimeError(("producer clean differs",count(clean_diff),bbox(clean_diff)))

# Producer target is exact rendered Korean mask; C independently re-checks every bbox and relation.
target=np.asarray(Image.open(bdir/"E95_TARGET_TEXT_MASK.png").convert("L"),dtype=np.uint8)>0
target_outside_allowed=count(target&~allowed)
if target_outside_allowed:
    raise RuntimeError(("producer target outside allowed",target_outside_allowed,bbox(target&~allowed)))

preserved_changed={}
preserved_mask=np.zeros((H,W),bool)
for idx,name in preserved.items():
    x,y,cw,ch=regions[idx]["rect"]
    local=np.any(sa[y:y+ch,x:x+cw,:]!=fa[y:y+ch,x:x+cw,:],axis=2)
    preserved_changed[str(idx)]=count(local)
    preserved_mask[y:y+ch,x:x+cw]=True
if any(preserved_changed.values()):
    raise RuntimeError(("preserved cell changed",preserved_changed))

target_masks=[]
row_results=[]
style={}
for r,am in zip(rows,allowed_masks):
    tm=target&am
    lb=bbox(tm)
    if not lb:
        raise RuntimeError(("missing target",r["region_idx"]))
    ob=r["original_bbox"]
    sw,sh=ob[2]-ob[0],ob[3]-ob[1]
    lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    d=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    if lw>sw or lh>sh or min(d)<=0:
        raise RuntimeError(("bbox/size/margin",r["region_idx"],ob,lb,d))
    target_masks.append(tm)
    sm=source_masks[len(target_masks)-1]
    spx=sa[sm]
    tpx=fa[tm]
    slum=float(np.median(0.2126*spx[:,0]+0.7152*spx[:,1]+0.0722*spx[:,2]))
    tlum=float(np.median(0.2126*tpx[:,0]+0.7152*tpx[:,1]+0.0722*tpx[:,2]))
    style[str(r["region_idx"])]={"source_median_luminance":slum,"localized_median_luminance":tlum}
    row_results.append({**r,"localized_bbox":lb,"source_size":[sw,sh],"localized_size":[lw,lh],
        "delta_left":d[0],"delta_right":d[1],"delta_top":d[2],"delta_bottom":d[3],
        "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

final_diff=np.any(fa!=sa,axis=2)
alpha_diff=fa[:,:,3]!=sa[:,:,3]
render_diff=np.any(fa!=expected_clean,axis=2)
outside=count(final_diff&~allowed&~preserved_mask)
alpha_out=count(alpha_diff&~allowed&~preserved_mask)
protected_changed=count(final_diff&preserved_mask)
render_out=count(render_diff&~target&~preserved_mask)
equal_source=np.all(fa==sa,axis=2)
clean_change=np.any(sa!=expected_clean,axis=2)
source_residue=count(clean_change&~target&equal_source)

overlap=0
touch=[]
for i in range(len(target_masks)):
    for j in range(i+1,len(target_masks)):
        ov=count(target_masks[i]&target_masks[j])
        near=count(dil(target_masks[i],1)&target_masks[j])
        overlap+=ov
        if ov or near:
            touch.append([rows[i]["region_idx"],rows[j]["region_idx"],ov,near])

target_preserved_overlap=count(target&preserved_mask)
target_preserved_near=count(dil(target,1)&preserved_mask)

if any([outside,alpha_out,protected_changed,render_out,source_residue,overlap,target_preserved_overlap,target_preserved_near]) or touch:
    raise RuntimeError(("gates",outside,alpha_out,protected_changed,render_out,source_residue,overlap,target_preserved_overlap,target_preserved_near,touch))

for name,m in [
    ("C149_SOURCE_TEXT_MASK.png",source_mask),
    ("C149_ALLOWED_BBOX_MASK.png",allowed),
    ("C149_TARGET_TEXT_MASK.png",target),
    ("C149_PRESERVED_REGION_MASK.png",preserved_mask),
]:
    Image.fromarray((m.astype(np.uint8)*255),"L").save(out/name)
clean_img=Image.fromarray(expected_clean,"RGBA")
clean_img.save(out/"C149_EXACT_CLEAN_PLATE.png")

cards=[]
for label,im in [("SOURCE",src),("CLEAN",clean_img),("FINAL",fin)]:
    z=comp(im).resize((1024,512),Image.Resampling.NEAREST)
    c=Image.new("RGB",(1024,540),"white")
    c.paste(z,(0,24))
    ImageDraw.Draw(c).text((5,4),label,fill="black")
    cards.append(c)
sheet=Image.new("RGB",(1024,1620),"white")
for i,c in enumerate(cards):
    sheet.paste(c,(0,i*540))
sheet.save(out/"C149_E95_COMPARE.jpg",quality=96)

contacts=[]
for r in row_results:
    x0,y0,x1,y1=r["original_bbox"]
    p=12
    cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[comp(z).crop(cr) for z in (src,clean_img,fin)]
    c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+30),"white")
    xx=0
    for z in ims:
        c.paste(z,(xx,30))
        xx+=z.width+6
    ImageDraw.Draw(c).text((5,5),f'{r["region_idx"]} {r["source"]} -> {r["korean"]}',fill="black")
    contacts.append(c)
rw=max(c.width for c in contacts)
rh=sum(c.height for c in contacts)+4*(len(contacts)-1)
rs=Image.new("RGB",(rw,rh),"white")
yy=0
for c in contacts:
    rs.paste(c,(0,yy))
    yy+=c.height+4
rs.save(out/"C149_E95_ROW_CONTACT.jpg",quality=96)

rr=Image.new("RGB",(1024,1080),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_fin)]):
    z=comp(im).resize((1024,512),Image.Resampling.NEAREST)
    rr.paste(z,(0,i*540+24))
    ImageDraw.Draw(rr).text((5,i*540+4),label,fill="black")
rr.save(out/"C149_E95_RAW_COMPARE.jpg",quality=96)

report={
    "schema_version":1,"role":"C","run":run,"queue_index":230,"asset":asset,
    "producer_run":"20261005-B-PRODUCTION73",
    "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,"atlas_git_blob_sha1":ATLAS_BLOB_SHA1,"source_sha256":SOURCE_SHA256},
    "candidate_sha256":CANDIDATE_SHA256,"candidate_changed_by_C":False,
    "semantic_binding":{"localized":{str(i):en for i,en,ko,g in specs},"translations":{str(i):ko for i,en,ko,g in specs},"preserved":{str(k):v for k,v in preserved.items()}},
    "independent_method":"pinned canonical source+atlas; exact alpha masks for transparent rows; strengthened pill source/effect separation and independent row-background clean reconstruction; exact preserved-cell comparison; producer Korean target rechecked for bbox/size/positive margin/overlap/protected relation; decoded DDS/header/raw orientation validation",
    "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":rawmode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
    "rows":row_results,
    "machine_checks":{"producer_clean_exact_diff_pixels":count(clean_diff),"target_outside_allowed":target_outside_allowed,"bbox_size_positive_margin":"11/11 PASS","final_outside":outside,"alpha_outside":alpha_out,"protected_changed":protected_changed,"render_outside_target":render_out,"source_residue":source_residue,"source_residue_basis":"source_to_independent_clean_changed_pixels","overlap":overlap,"touch_pairs":touch,"target_preserved_overlap":target_preserved_overlap,"target_preserved_1px_near":target_preserved_near,"preserved_regions_changed_pixels":preserved_changed,"style":style},
    "machine_status":"PASS","controller_visual_qa":"PENDING","decision":"PENDING_CONTROLLER_VISUAL_QA","RUNTIME_VALIDATION":"UNTESTED"
}
(out/"C149_E95_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"E95DA5","index":230,"source_sha256":SOURCE_SHA256,"candidate_sha256":CANDIDATE_SHA256,"machine_status":"PASS","bbox_size_positive_margin":"11/11","clean_exact_diff_pixels":count(clean_diff),"outside":outside,"alpha_outside":alpha_out,"protected_changed":protected_changed,"render_outside_target":render_out,"source_residue":source_residue,"source_residue_basis":"source_to_independent_clean_changed_pixels","overlap":overlap,"touch_pairs":len(touch),"target_preserved_overlap":target_preserved_overlap,"target_preserved_1px_near":target_preserved_near,"preserved_regions_changed":sum(preserved_changed.values()),"runtime_validation":"UNTESTED","report":f"localization/graphics/role_C/{run}/C149_E95_MACHINE_QA.json"}
(wr/"C149_E95DA5.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False),flush=True)