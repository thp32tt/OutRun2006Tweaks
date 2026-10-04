#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,zipfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd(); run="20261005-C138-1F5FE6E9"
out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/1F5FE6E9_1024x512.dds"
srczip=repo/"localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip"
with zipfile.ZipFile(srczip) as z: sb=z.read(asset)
source_sha=hashlib.sha256(sb).hexdigest()
if source_sha!="3656adbd699b7852cb5fcf4bb01fc4f1f65bbd9d7d39e12e7a1c2ac5a49fef1d":
    raise RuntimeError(("source_sha",source_sha))
H=struct.unpack_from("<I",sb,12)[0]; W=struct.unpack_from("<I",sb,16)[0]; mips=struct.unpack_from("<I",sb,28)[0]
if (W,H)!=(1024,512) or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,mips,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)

labels=[("REQUEST","요청"),("SPECIAL REQUEST 1","스페셜 요청 1"),("SPECIAL REQUEST 2","스페셜 요청 2"),("SPECIAL REQUEST 3","스페셜 요청 3")]

# B51/C136/C137 established mirror_y and the menu text band. The source glyphs
# share panel hidden RGB, with visibility/effect carried mainly in alpha.
# Restrict to the dark panel interior to exclude the x~638 border and the y>=232
# colored selector panel. Then split rows at local minima in alpha population.
X0,X1=645,900
YT,YB=132,232
alpha=sa[YT:YB,X0:X1,3]
active=alpha>0
counts=np.count_nonzero(active,axis=1)
expected_boundaries=[172,196,219]
cuts=[]
for b in expected_boundaries:
    lo=max(YT+1,b-7); hi=min(YB-1,b+7)
    vals=counts[lo-YT:hi-YT+1]
    if len(vals)==0: raise RuntimeError(("empty boundary window",b))
    rel=int(np.argmin(vals)); y=lo+rel
    # Prefer true zero-alpha separators; otherwise a very sparse separator.
    if counts[y-YT] > max(3,int(0.04*(X1-X0))):
        raise RuntimeError(("no clean row separator",b,y,int(counts[y-YT])))
    cuts.append(y)
if not (YT<cuts[0]<cuts[1]<cuts[2]<YB):
    raise RuntimeError(("bad cuts",cuts))
bands=[(YT,cuts[0]),(cuts[0]+1,cuts[1]),(cuts[1]+1,cuts[2]),(cuts[2]+1,YB)]

def bbox(mask):
    yy,xx=np.nonzero(mask)
    if not len(xx): return None
    return [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]

def rect(shape,b):
    h,w=shape; x0,y0,x1,y1=map(int,b); m=np.zeros((h,w),bool); m[y0:y1,x0:x1]=1; return m

def dil(mask,px):
    return np.asarray(Image.fromarray((mask.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(px*2+1)))>0

rows=[]; source_masks=[]; full=np.zeros((H,W),bool); allowed=np.zeros((H,W),bool)
for n,((en,ko),(y0,y1)) in enumerate(zip(labels,bands),1):
    local=sa[y0:y1,X0:X1,3]>0
    # Reject broad panel lines; keep glyph/effect components. Small glyph fragments
    # are retained because the row band already isolates semantics.
    from scipy import ndimage
    lab,num=ndimage.label(local,np.ones((3,3),dtype=np.uint8))
    kept=np.zeros_like(local)
    comps=[]
    for i in range(1,num+1):
        yy,xx=np.nonzero(lab==i)
        if len(xx)<2: continue
        bw=int(xx.max()-xx.min()+1); bh=int(yy.max()-yy.min()+1)
        if bw>int(0.90*(X1-X0)) and bh<=4: continue
        if bh>int(0.85*(y1-y0)) and bw<=3: continue
        if len(xx)>0.70*local.size: continue
        kept[yy,xx]=1
        comps.append([int(len(xx)),[X0+int(xx.min()),y0+int(yy.min()),X0+int(xx.max())+1,y0+int(yy.max())+1]])
    if not comps: raise RuntimeError(("no glyph components",n,en,[y0,y1]))
    # Recover the full source alpha/effect fringe only within this semantic band.
    near=dil(kept,2)
    fringe=near & (sa[y0:y1,X0:X1,3]>0)
    yy,xx=np.nonzero(fringe)
    if len(xx)<10: raise RuntimeError(("tiny source effect",n,en,int(len(xx))))
    bb=[X0+int(xx.min()),y0+int(yy.min()),X0+int(xx.max())+1,y0+int(yy.max())+1]
    # Positive room must exist around exact source effect; if bbox hits scan limits,
    # fail rather than assuming the source extent.
    if bb[0]<=X0 or bb[2]>=X1 or bb[1]<=y0 or bb[3]>=y1:
        raise RuntimeError(("source bbox touches row scan boundary",n,bb,[X0,y0,X1,y1],comps))
    sm=np.zeros((H,W),bool); sm[y0:y1,X0:X1]=fringe
    source_masks.append(sm); full|=sm; allowed|=rect((H,W),bb)
    px=sa[sm]
    hi=px[:,3]>=np.percentile(px[:,3],60)
    core=px[hi] if np.any(hi) else px
    fill=tuple(int(v) for v in np.median(core,axis=0))
    rows.append({"n":n,"source":en,"korean":ko,"row_band":[y0,y1],"source_components":comps,
                 "original_bbox":bb,"source_effect_pixels":int(np.count_nonzero(sm)),
                 "source_alpha_min":int(px[:,3].min()),"source_alpha_max":int(px[:,3].max()),
                 "source_alpha_median":float(np.median(px[:,3])),"source_core_fill_rgba":fill})

for i in range(4):
    for j in range(i+1,4):
        if np.any(source_masks[i]&source_masks[j]): raise RuntimeError(("source mask overlap",i+1,j+1))

# Reconstruct exact source effects from a local ring. RGB and alpha are fit
# independently to preserve the panel's subtle gradient/hidden-RGB behavior.
clean=sa.astype(np.float32).copy()
for row,sm in zip(rows,source_masks):
    ring=dil(sm,5)&~sm
    # Keep ring inside a modest neighborhood of the source bbox and dark-panel y<232.
    x0,y0,x1,y1=row["original_bbox"]
    neigh=rect((H,W),[max(0,x0-8),max(YT,y0-8),min(W,x1+8),min(YB,y1+8)])
    ring&=neigh
    yy,xx=np.nonzero(ring)
    if len(xx)<40: raise RuntimeError(("insufficient clean ring",row["n"],len(xx)))
    A=np.column_stack([np.ones(len(xx)),xx.astype(float),yy.astype(float)])
    vals=sa[yy,xx].astype(float)
    coefs=[]; pred=np.zeros_like(vals)
    for c in range(4):
        coef=np.linalg.lstsq(A,vals[:,c],rcond=None)[0]; coefs.append(coef); pred[:,c]=A@coef
    mae=float(np.mean(np.abs(pred-vals)))
    if mae>18: raise RuntimeError(("background ring not smooth",row["n"],mae))
    my,mx=np.nonzero(sm); M=np.column_stack([np.ones(len(mx)),mx.astype(float),my.astype(float)])
    for c in range(4): clean[my,mx,c]=np.clip(M@coefs[c],0,255)
    row["clean_ring_rgba_mae"]=mae
clean_a=np.rint(clean).astype(np.uint8)
clean_img=Image.fromarray(clean_a,"RGBA")

# Verified Korean font; all four rows share source family/weight/size.
font_path=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Bold"],text=True).strip()
if not font_path or not Path(font_path).exists() or "NotoSansCJK" not in Path(font_path).name:
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    font_path=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Bold"],text=True).strip()
if not font_path or "NotoSansCJK" not in Path(font_path).name: raise RuntimeError(("font unavailable",font_path))

# Shared source fill/effect core. Preserve low-opacity source character.
allpx=sa[full]
cut=np.percentile(allpx[:,3],60)
core=allpx[allpx[:,3]>=cut]
shared_fill=tuple(int(v) for v in np.median(core,axis=0)) if len(core) else tuple(int(v) for v in np.median(allpx,axis=0))
# Never invent opacity above source maximum.
shared_fill=(shared_fill[0],shared_fill[1],shared_fill[2],min(shared_fill[3],int(allpx[:,3].max())))

def make_tile(text,fs,fill):
    f=ImageFont.truetype(font_path,fs)
    for ch in set(text.replace(" ","")):
        if f.getbbox(ch) is None: raise RuntimeError(("missing glyph",ch,Path(font_path).name))
    d=ImageDraw.Draw(Image.new("L",(8,8),0)); tb=d.textbbox((0,0),text,font=f)
    pad=3; im=Image.new("RGBA",(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad),(0,0,0,0))
    ImageDraw.Draw(im).text((pad-tb[0],pad-tb[1]),text,font=f,fill=fill)
    ab=im.getchannel("A").getbbox()
    return im.crop(ab) if ab else None

min_h=min(r["original_bbox"][3]-r["original_bbox"][1] for r in rows)
common=None
for fs in range(max(8,int(min_h*.92)),7,-1):
    tiles=[make_tile(r["korean"],fs,shared_fill) for r in rows]
    ok=True
    for r,t in zip(rows,tiles):
        if t is None: ok=False; break
        ob=r["original_bbox"]; aw=ob[2]-ob[0]; ah=ob[3]-ob[1]
        if t.width>aw-2 or t.height>ah-2: ok=False; break
    if ok: common=(fs,tiles); break
if common is None: raise RuntimeError("cannot fit shared typography")
fs,tiles=common

final=clean_img.copy(); target_masks=[]; target=np.zeros((H,W),bool)
for row,t in zip(rows,tiles):
    x0,y0,x1,y1=row["original_bbox"]; aw=x1-x0; ah=y1-y0
    px=x0+1; py=y0+(ah-t.height)//2
    if px+t.width>=x1 or py<=y0 or py+t.height>=y1:
        raise RuntimeError(("fit",row["n"],row["original_bbox"],t.size,[px,py]))
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); layer.alpha_composite(t,(px,py))
    lm=np.asarray(layer.getchannel("A"))>0
    for old in target_masks:
        if np.any(lm&old): raise RuntimeError(("localized overlap",row["n"]))
    target_masks.append(lm); target|=lm; final.alpha_composite(layer)
    lb=list(layer.getchannel("A").getbbox()); ob=row["original_bbox"]
    row.update({"localized_bbox":lb,"source_size":[ob[2]-ob[0],ob[3]-ob[1]],
                "localized_size":[lb[2]-lb[0],lb[3]-lb[1]],
                "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],
                "delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
                "containment":"PASS","size_ceiling":"PASS","edge_touch_high_risk":False,
                "font_size":fs,"font_basename":Path(font_path).name,
                "shared_fill_rgba":shared_fill,"shared_source_style":"PASS",
                "rework_status":"C138_ALPHA_ROW_PARTITION_RENDER"})

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw","RGBA")
cand=repo/"localization/graphics/hd_candidates"/asset; cand.parent.mkdir(parents=True,exist_ok=True); cand.write_bytes(payload)
candidate_sha=hashlib.sha256(payload).hexdigest()
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw","RGBA")
dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if payload[:128]!=sb[:128] or ImageChops.difference(final,dec).getbbox() is not None: raise RuntimeError("roundtrip/header")
da=np.asarray(dec,dtype=np.uint8)

changed=np.any(sa!=da,axis=2)
outside=int(np.count_nonzero(changed&~allowed))
alpha_out=int(np.count_nonzero((sa[:,:,3]!=da[:,:,3])&~allowed))
target_out=int(np.count_nonzero(target&~allowed))
target_invisible=int(np.count_nonzero(target&(da[:,:,3]==0)))
protected_changed=outside
guard=dil(target,2)
# Any source-effect pixel still differing from reconstructed clean plate outside the
# Korean target guard is residual source effect.
clean_diff=np.any(sa!=clean_a,axis=2)
residual_mask=full & (np.any(da!=clean_a,axis=2)) & ~guard
source_residue=int(np.count_nonzero(residual_mask))
overlap=0; touch=[]
for i in range(4):
    for j in range(i+1,4):
        ov=int(np.count_nonzero(target_masks[i]&target_masks[j]))
        near=int(np.count_nonzero(dil(target_masks[i],1)&target_masks[j]))
        overlap+=ov
        if ov or near: touch.append([i+1,j+1,ov,near])
positive=all(r["delta_left"]>0 and r["delta_right"]>0 and r["delta_top"]>0 and r["delta_bottom"]>0 for r in rows)
ok=(outside==0 and alpha_out==0 and target_out==0 and target_invisible==0 and protected_changed==0 and
    source_residue==0 and overlap==0 and not touch and positive)
if not ok: raise RuntimeError(("C138_QA_FAIL",outside,alpha_out,target_out,target_invisible,source_residue,overlap,touch,rows))

def mi(m): return Image.fromarray((m.astype(np.uint8)*255),"L")
mi(full).save(out/"1F5_SOURCE_TEXT_MASK.png"); mi(allowed).save(out/"1F5_ALLOWED_TEXT_REGION_MASK.png")
mi(~allowed).save(out/"1F5_PROTECTED_MASK.png"); mi(target).save(out/"1F5_TARGET_TEXT_MASK.png")
clean_img.save(out/"1F5_CLEAN_PLATE.png"); dec.save(out/"C138_1F5_FINAL_READABLE.png")

def comp(im,bg=(64,64,64,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def card(lbl,im,bg=(64,64,64,255)):
    v=comp(im,bg); c=Image.new("RGB",(W,H+25),"white"); c.paste(v,(0,25)); ImageDraw.Draw(c).text((5,4),lbl,fill="black"); return c
cards=[card("SOURCE_READABLE",src),card("CLEAN",clean_img),card("C138_FINAL",dec),card("C138_FINAL_WHITE",dec,(255,255,255,255))]
sheet=Image.new("RGB",(W*2,(H+25)*2),"white");sheet.paste(cards[0],(0,0));sheet.paste(cards[1],(W,0));sheet.paste(cards[2],(0,H+25));sheet.paste(cards[3],(W,H+25));sheet.save(out/"C138_1F5_COMPARE.jpg",quality=96)
contacts=[]; sr=comp(src); cl=comp(clean_img); fi=comp(dec)
for r in rows:
    x0,y0,x1,y1=r["original_bbox"]; p=10; cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[z.crop(cr) for z in (sr,cl,fi)]; ims=[z.resize((z.width*3,z.height*3),Image.Resampling.NEAREST) for z in ims]
    c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+25),"white"); xx=0
    for z in ims: c.paste(z,(xx,25)); xx+=z.width+6
    ImageDraw.Draw(c).text((4,4),f'{r["n"]} {r["source"]} -> {r["korean"]}',fill="black"); contacts.append(c)
rowsheet=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4*(len(contacts)-1)),"white"); yy=0
for c in contacts: rowsheet.paste(c,(0,yy)); yy+=c.height+4
rowsheet.save(out/"C138_1F5_ROW_CONTACT_3X.jpg",quality=96)
rawsheet=Image.new("RGB",(W,(H+25)*2),"white");rawsheet.paste(card("SOURCE_RAW_MIRROR_Y",raw_src),(0,0));rawsheet.paste(card("C138_FINAL_RAW_MIRROR_Y",raw_dec),(0,H+25));rawsheet.save(out/"C138_1F5_RAW_COMPARE.jpg",quality=96)

report={"schema_version":1,"role":"C","run":run,"asset":"1F5FE6E9","queue_index":132,
 "source_sha256":source_sha,"candidate_sha256":candidate_sha,"candidate_changed_by_C":True,
 "corrective_scope":"resolve B51 fail-closed adjacent-row source-mask ambiguity by alpha-population row partition on the verified mirror_y dark panel",
 "structure":{"width":W,"height":H,"format":"RGBA32","mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "row_separators":cuts,"rows":rows,"shared_typography":{"font_size":fs,"fill_rgba":shared_fill,"status":"PASS_SHARED_SOURCE_STYLE"},
 "machine_checks":{"bbox_and_size":"4/4 PASS with positive margins","outside":outside,"alpha_outside":alpha_out,
   "protected_changed":protected_changed,"target_out":target_out,"target_invisible":target_invisible,
   "source_residue":source_residue,"overlap":overlap,"touch_pairs":touch},
 "machine_status":"PASS","controller_visual_qa":"PENDING","runtime_validation":"UNTESTED"}
(out/"C138_1F5_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"1F5FE6E9","index":132,"candidate_sha256":candidate_sha,"machine_status":"PASS",
 "bbox_size_pass":"4/4","positive_margin_pass":"4/4","outside":outside,"alpha_outside":alpha_out,
 "source_residue":source_residue,"overlap":overlap,"touch_pairs":len(touch),"runtime_validation":"UNTESTED",
 "report":f"localization/graphics/role_C/{run}/C138_1F5_MACHINE_QA.json"}
(wr/"C138_1F5FE6E9.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False),flush=True)
