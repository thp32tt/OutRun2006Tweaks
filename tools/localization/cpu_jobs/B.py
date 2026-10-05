#!/usr/bin/env python3
import base64, hashlib, json, os, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B hosted worker only")

repo=Path.cwd()
run="20261006-B-PRODUCTION159-A8CE"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_fight_Exst/A8CE339F_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
A8_SOURCE_SHA="08afacc681737d6a138496cefce559853985084cf779921ac32ef2ebfe06883b"
FF_SOURCE_SHA="5b029de75fa10ed00e547ef2c5d9df9691e8e5d8b9f2622fee62bc4972c7ae67"
FF_CAND_SHA="9e6f0247e54302b0c81d84f24f02ec255af4c027916e3bdfe4726f0839f2de08"

tmp=Path("/tmp/outrun_B159"); tmp.mkdir(parents=True,exist_ok=True)
a8dds=tmp/"A8CE.dds"
ffdds=tmp/"FF2462BB.dds"
atlasp=tmp/"A8CE_atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_fight_Exst/A8CE339F_512x256.dds",a8dds)
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds",ffdds)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_fight_Exst/4x_A8CE339F_512x256_atlas.json",atlasp)

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return sha_bytes(p.read_bytes())
def mask_count(im): return int(np.count_nonzero(np.asarray(im)>0))
def diff_mask(a,b):
    d=ImageChops.difference(a,b)
    bands=d.split()
    m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)
def composite(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def save_jpg_b64(im,name,quality=94):
    p=out/name
    im.convert("RGB").save(p,quality=quality,optimize=True)
    (out/(name+".b64.txt")).write_text(base64.b64encode(p.read_bytes()).decode("ascii"))

sb=a8dds.read_bytes()
if sha_bytes(sb)!=A8_SOURCE_SHA: raise RuntimeError(("A8 source drift",sha_bytes(sb)))
if sha_file(ffdds)!=FF_SOURCE_SHA: raise RuntimeError(("FF source drift",sha_file(ffdds)))
if sb[:4]!=b"DDS ": raise RuntimeError("A8 not DDS")
H=struct.unpack_from("<I",sb,12)[0]; W=struct.unpack_from("<I",sb,16)[0]; mips=struct.unpack_from("<I",sb,28)[0]
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6],pf[7])
mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
if mode is None or (W,H)!=(2048,1024) or len(sb)!=128+W*H*4:
    raise RuntimeError(("A8 structure",W,H,mips,masks,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
regs={int(r["idx"]):list(map(int,r["rect"])) for r in json.loads(atlasp.read_text())["regions"]}
for idx in (24,25,26,27,28,29,30,31,32,33):
    if idx not in regs: raise RuntimeError(("atlas missing",idx))

# Read the C86-approved FF candidate and clean plate to reuse Start/Goal only when
# its exact English source patch is byte/pixel-identical to A8CE.
ff_candidate_path=repo/"localization/graphics/hd_candidates/textures/load/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds"
ff_clean_path=repo/"localization/graphics/role_A/20261004-A-RECOVERY01/FF2462BB_CLEAN_PLATE.png"
if sha_file(ff_candidate_path)!=FF_CAND_SHA: raise RuntimeError(("FF candidate drift",sha_file(ff_candidate_path)))
ff_src=Image.open(ffdds).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
ff_cand=Image.open(ff_candidate_path).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
ff_clean=Image.open(ff_clean_path).convert("RGBA")
if ff_src.size!=(4096,2048) or ff_cand.size!=ff_src.size or ff_clean.size!=ff_src.size:
    raise RuntimeError(("FF dimensions",ff_src.size,ff_cand.size,ff_clean.size))

ff_templates={
 "Start":[
   [1335,737,1449,785],[2111,737,2225,785],[2887,737,3001,785]
 ],
 "Goal":[
   [1965,737,2068,785],[2741,737,2844,785],[3517,737,3620,785]
 ]
}

# Font: use the same family documented by approved recovery jobs where available.
font_candidates=[
 "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
 "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
 "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]
font_path=next((p for p in font_candidates if Path(p).exists()),None)
if font_path is None:
    try:
        q=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
        if q and Path(q).exists(): font_path=q
    except Exception:
        pass
if font_path is None: raise RuntimeError("Noto CJK font unavailable")

def bbox_from_mask(m):
    ys,xs=np.nonzero(m)
    if not len(xs): return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

def detect_start_goal(cell):
    arr=np.asarray(cell,dtype=np.uint8)
    alpha=arr[:,:,3]>0
    h,w=alpha.shape
    # Source labels occupy the upper portion of each 776x104 bar sprite in readable orientation.
    top=alpha[:min(68,h),:]
    dil=ndimage.binary_dilation(top,structure=np.ones((3,9),dtype=bool),iterations=1)
    labs,n=ndimage.label(dil)
    comps=[]
    for k in range(1,n+1):
        m=(labs==k)
        ys,xs=np.nonzero(m)
        if not len(xs): continue
        x0,x1=int(xs.min()),int(xs.max()+1); y0,y1=int(ys.min()),int(ys.max()+1)
        # Refine with original visible source alpha under the dilated component.
        orig=top & m
        bb=bbox_from_mask(orig)
        if bb is None: continue
        ox0,oy0,ox1,oy1=bb; ww=ox1-ox0; hh=oy1-oy0
        if 70<=ww<=150 and 35<=hh<=60 and oy0<55:
            comps.append([ox0,oy0,ox1,oy1])
    # Exact source family dimensions are known from the C86-approved FF source.
    starts=[b for b in comps if (b[2]-b[0],b[3]-b[1])==(114,48)]
    goals=[b for b in comps if (b[2]-b[0],b[3]-b[1])==(103,48)]
    if len(starts)==1 and len(goals)==1:
        return {"Start":starts[0],"Goal":goals[0],"components":comps}
    # Fallback grouping by word-sized source-alpha columns, still fail closed unless two words are obvious.
    col=np.any(top,axis=0)
    # bridge letter gaps <= 10 px but not the large Start-to-Goal gap
    bridged=ndimage.binary_closing(col,structure=np.ones(11,dtype=bool))
    lab1,n1=ndimage.label(bridged)
    words=[]
    for k in range(1,n1+1):
        xs=np.nonzero(lab1==k)[0]
        if not len(xs): continue
        x0,x1=int(xs.min()),int(xs.max()+1)
        sub=top[:,x0:x1]
        bb=bbox_from_mask(sub)
        if bb:
            words.append([x0+bb[0],bb[1],x0+bb[2],bb[3]])
    words=[b for b in words if 70<=b[2]-b[0]<=150 and 35<=b[3]-b[1]<=60]
    words=sorted(words,key=lambda b:b[0])
    if len(words)==2:
        # Start is wider than Goal in this exact source family.
        a,b=words
        if (a[2]-a[0])>(b[2]-b[0]):
            return {"Start":a,"Goal":b,"components":comps}
    raise RuntimeError(("ambiguous Start/Goal detection",comps,words))

def globalize(cell_rect,local_bbox):
    x,y,w,h=cell_rect; a,b,c,d=local_bbox
    return [x+a,y+b,x+c,y+d]

pair_rows=[]
for idx in (24,25):
    x,y,w,h=regs[idx]
    cell=src.crop((x,y,x+w,y+h))
    det=detect_start_goal(cell)
    for word in ("Start","Goal"):
        pair_rows.append({"region_idx":idx,"source":word,"korean":"시작" if word=="Start" else "골",
                          "source_bbox":globalize(regs[idx],det[word])})

# Extra Time is its own atlas sprite (idx26); derive exact visible source-effect bbox.
x,y,w,h=regs[26]
cell26=np.asarray(src.crop((x,y,x+w,y+h)),dtype=np.uint8)
ebb=bbox_from_mask(cell26[:,:,3]>0)
if ebb is None: raise RuntimeError("Extra Time alpha absent")
extra_bbox=globalize(regs[26],ebb)
# Sanity: this label should occupy a substantial part of the 504x104 sprite but leave positive room.
ew,eh=extra_bbox[2]-extra_bbox[0],extra_bbox[3]-extra_bbox[1]
if not (250<=ew<=504 and 50<=eh<=104):
    raise RuntimeError(("Extra Time bbox unexpected",extra_bbox,ew,eh))

clean_arr=sa.copy()
final_arr=sa.copy()
allowed=np.zeros((H,W),dtype=np.uint8)
source_text=np.zeros((H,W),dtype=np.uint8)
render_union=np.zeros((H,W),dtype=np.uint8)
rows=[]
template_notes=[]

def exact_source_mask(bbox):
    x0,y0,x1,y1=bbox
    m=sa[y0:y1,x0:x1,3]>0
    return m

# Apply the four Start/Goal labels. Exact FF source-patch match is required for approved-template copy.
ff_src_np=np.asarray(ff_src,dtype=np.uint8)
ff_clean_np=np.asarray(ff_clean,dtype=np.uint8)
ff_cand_np=np.asarray(ff_cand,dtype=np.uint8)
for rr in pair_rows:
    b=rr["source_bbox"]; x0,y0,x1,y1=b
    patch=sa[y0:y1,x0:x1]
    word=rr["source"]
    matched=None
    for tb in ff_templates[word]:
        tx0,ty0,tx1,ty1=tb
        tsp=ff_src_np[ty0:ty1,tx0:tx1]
        if tsp.shape==patch.shape and np.array_equal(tsp,patch):
            matched=tb; break
    if matched is None:
        raise RuntimeError(("C86 source-family template mismatch",rr))
    tx0,ty0,tx1,ty1=matched
    cp=ff_clean_np[ty0:ty1,tx0:tx1]
    fp=ff_cand_np[ty0:ty1,tx0:tx1]
    clean_arr[y0:y1,x0:x1]=cp
    final_arr[y0:y1,x0:x1]=fp
    allowed[y0:y1,x0:x1]=255
    source_text[y0:y1,x0:x1][patch[:,:,3]>0]=255
    rend=np.any(cp!=fp,axis=2)
    render_union[y0:y1,x0:x1][rend]=255
    lb=bbox_from_mask(rend)
    if lb is None: raise RuntimeError(("empty template render",rr))
    lbg=globalize([x0,y0,x1-x0,y1-y0],lb)
    sw,sh=x1-x0,y1-y0; lw,lh=lbg[2]-lbg[0],lbg[3]-lbg[1]
    if not(lbg[0]>x0 and lbg[1]>y0 and lbg[2]<x1 and lbg[3]<y1 and lw<=sw and lh<=sh):
        raise RuntimeError(("template bbox gate",rr,lbg))
    rr.update({"localized_bbox":lbg,"source_width":sw,"source_height":sh,
               "localized_width":lw,"localized_height":lh,
               "delta_left":lbg[0]-x0,"delta_right":x1-lbg[2],
               "delta_top":lbg[1]-y0,"delta_bottom":y1-lbg[3],
               "template_source_bbox":matched,
               "template_approval":"C86_PIXEL_VISUAL_PASS_PENDING_INGAME",
               "source_patch_exact_to_template":True,
               "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})
    rows.append(rr)
    template_notes.append({"region_idx":rr["region_idx"],"source":word,
                           "target_source_bbox":b,"ff_template_bbox":matched,
                           "source_patch_diff_pixels":0,
                           "approval":"C86_PIXEL_VISUAL_PASS_PENDING_INGAME"})

# Remove Extra Time source glyph/effect footprint on transparent background.
ex0,ey0,ex1,ey1=extra_bbox
em=sa[ey0:ey1,ex0:ex1,3]>0
clean_arr[ey0:ey1,ex0:ex1][em]=0
final_arr[ey0:ey1,ex0:ex1][em]=0
allowed[ey0:ey1,ex0:ex1]=255
source_text[ey0:ey1,ex0:ex1][em]=255

# Source-style color sampling for Extra Time.
sp=sa[ey0:ey1,ex0:ex1]
vis=sp[:,:,3]>=96
rgb=sp[:,:,:3].astype(np.float32)
lum=0.2126*rgb[:,:,0]+0.7152*rgb[:,:,1]+0.0722*rgb[:,:,2]
vals=lum[vis]
if vals.size<100: raise RuntimeError("Extra Time sampling insufficient")
q65=float(np.quantile(vals,0.65)); q25=float(np.quantile(vals,0.25))
bright=vis & (lum>=q65)
dark=vis & (lum<=q25)
mid=(ey1-ey0)//2
def medcolor(mask,fallback):
    pts=rgb[mask]
    if len(pts)<20: return fallback
    return tuple(int(v) for v in np.median(pts,axis=0).round())
top_fill=medcolor(bright & (np.indices(bright.shape)[0]<mid),(255,245,205))
bottom_fill=medcolor(bright & (np.indices(bright.shape)[0]>=mid),(228,187,80))
outline=medcolor(dark,(9,16,55))
# Prevent a bad quantile sample from turning the fill into the dark outline.
if sum(top_fill)<420: top_fill=(255,245,205)
if sum(bottom_fill)<330: bottom_fill=(228,187,80)
if sum(outline)>300: outline=(9,16,55)

def build_slanted_masks(text,maxw,maxh):
    # Source family is heavy, outlined, right-italic. Fit strictly inside source bbox with >=2px margin.
    target_h=maxh-4
    best=None
    for size in range(18,100):
        f=ImageFont.truetype(font_path,size)
        sw=max(2,int(round(maxh*0.055)))
        probe=Image.new("L",(1200,260),0)
        d=ImageDraw.Draw(probe)
        bb=d.textbbox((0,0),text,font=f,stroke_width=sw)
        ox=-bb[0]+12; oy=-bb[1]+12
        outer=Image.new("L",probe.size,0); fill=Image.new("L",probe.size,0)
        ImageDraw.Draw(outer).text((ox,oy),text,font=f,fill=255,stroke_width=sw,stroke_fill=255)
        ImageDraw.Draw(fill).text((ox,oy),text,font=f,fill=255,stroke_width=0)
        bb2=outer.getbbox()
        if not bb2: continue
        outer=outer.crop(bb2); fill=fill.crop(bb2)
        s=0.20
        add=int(np.ceil(s*outer.height))+2
        coeff=(1,s,-s*outer.height,0,1,0)
        outer=outer.transform((outer.width+add,outer.height),Image.Transform.AFFINE,coeff,resample=Image.Resampling.BICUBIC)
        fill=fill.transform((fill.width+add,fill.height),Image.Transform.AFFINE,coeff,resample=Image.Resampling.BICUBIC)
        bb3=outer.getbbox()
        if not bb3: continue
        outer=outer.crop(bb3); fill=fill.crop(bb3)
        # source has a dark down-right depth/shadow; include it in fit.
        off=max(1,int(round(maxh*0.045)))
        fw=max(outer.width+off,1); fh=max(outer.height+off,1)
        eff=Image.new("L",(fw,fh),0)
        eff.paste(outer,(off,off),outer)
        eff=ImageChops.lighter(eff,ImageOps.pad(outer,(fw,fh),method=Image.Resampling.NEAREST,centering=(0,0)))
        if eff.width<=maxw-4 and eff.height<=target_h:
            best=(size,sw,outer,fill,off,eff)
        else:
            if best: break
    if best is None: raise RuntimeError(("Extra Time font fit failed",maxw,maxh))
    return best

size,stroke,outer_m,fill_m,shadow_off,effect_m=build_slanted_masks("추가 시간",ew,eh)
ow,oh=effect_m.size
# left anchor is semantically important here; use +2px safety and vertically center.
px=ex0+2
py=ey0+(eh-oh)//2
if px+ow>=ex1 or py<=ey0 or py+oh>=ey1:
    raise RuntimeError(("Extra Time placement",extra_bbox,(px,py,ow,oh)))

# Build dark shadow, dark outline, then sampled source gradient fill.
overlay=Image.new("RGBA",(ow,oh),(0,0,0,0))
shadow=Image.new("RGBA",(ow,oh),outline+(0,))
shadow_alpha=Image.new("L",(ow,oh),0)
shadow_alpha.paste(outer_m,(shadow_off,shadow_off))
shadow.putalpha(shadow_alpha)
overlay.alpha_composite(shadow)
outline_layer=Image.new("RGBA",(ow,oh),outline+(0,))
outline_canvas=Image.new("L",(ow,oh),0); outline_canvas.paste(outer_m,(0,0))
outline_layer.putalpha(outline_canvas)
overlay.alpha_composite(outline_layer)
grad=np.zeros((oh,ow,4),dtype=np.uint8)
for yy in range(oh):
    t=yy/max(1,oh-1)
    c=[int(round(top_fill[i]*(1-t)+bottom_fill[i]*t)) for i in range(3)]
    grad[yy,:,0]=c[0]; grad[yy,:,1]=c[1]; grad[yy,:,2]=c[2]
fill_canvas=Image.new("L",(ow,oh),0); fill_canvas.paste(fill_m,(0,0))
grad[:,:,3]=np.asarray(fill_canvas)
overlay.alpha_composite(Image.fromarray(grad,"RGBA"))

# Composite onto transparent clean plate.
final_im_tmp=Image.fromarray(final_arr,"RGBA")
final_im_tmp.alpha_composite(overlay,(px,py))
final_arr=np.asarray(final_im_tmp,dtype=np.uint8).copy()
render_extra=np.asarray(overlay.getchannel("A"))>0
render_union[py:py+oh,px:px+ow][render_extra]=255
extra_loc=bbox_from_mask(render_extra)
extra_loc_g=globalize([px,py,ow,oh],extra_loc)
lw,lh=extra_loc_g[2]-extra_loc_g[0],extra_loc_g[3]-extra_loc_g[1]
if not(extra_loc_g[0]>ex0 and extra_loc_g[1]>ey0 and extra_loc_g[2]<ex1 and extra_loc_g[3]<ey1 and lw<=ew and lh<=eh):
    raise RuntimeError(("Extra Time bbox gate",extra_bbox,extra_loc_g))
rows.append({
 "region_idx":26,"source":"Extra Time","korean":"추가 시간",
 "source_bbox":extra_bbox,"localized_bbox":extra_loc_g,
 "source_width":ew,"source_height":eh,"localized_width":lw,"localized_height":lh,
 "delta_left":extra_loc_g[0]-ex0,"delta_right":ex1-extra_loc_g[2],
 "delta_top":extra_loc_g[1]-ey0,"delta_bottom":ey1-extra_loc_g[3],
 "font_file":Path(font_path).name,"font_size":size,"stroke_width":stroke,"slant":0.20,
 "shadow_offset":shadow_off,"fill_top_rgb":top_fill,"fill_bottom_rgb":bottom_fill,
 "outline_rgb":outline,"alignment":"left",
 "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"
})

clean=Image.fromarray(clean_arr,"RGBA")
final=Image.fromarray(final_arr,"RGBA")
allowed_im=Image.fromarray(allowed,"L")
protected_im=ImageOps.invert(allowed_im)
source_text_im=Image.fromarray(source_text,"L")
render_im=Image.fromarray(render_union,"L")

# Zero-overlap among five localized label effect bboxes and preserved 1P..6P sprites.
for i,a in enumerate(rows):
    ax0,ay0,ax1,ay1=a["localized_bbox"]
    for b in rows[i+1:]:
        bx0,by0,bx1,by1=b["localized_bbox"]
        if not(ax1<bx0-1 or bx1<ax0-1 or ay1<by0-1 or by1<ay0-1):
            raise RuntimeError(("localized overlap/touch",a["source"],a["region_idx"],b["source"],b["region_idx"]))

# Exact-source residue outside the new localized render masks must be zero.
st=np.asarray(source_text_im)>0; rm=np.asarray(render_im)>0
clean_a=np.asarray(clean)[:,:,3]; final_a=np.asarray(final)[:,:,3]
residue=int(np.count_nonzero(st & (~rm) & (final_a>0)))
if residue: raise RuntimeError(("source residue",residue))

# Exact DDS roundtrip preserving 128-byte header and mirror_y raw orientation.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",mode)
candidate.write_bytes(payload)
csha=sha_bytes(payload)
dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip mismatch")

dm=diff_mask(src,dec)
outside=mask_count(ImageChops.multiply(dm,protected_im))
ad=ImageChops.difference(src.getchannel("A"),dec.getchannel("A")).point(lambda v:255 if v else 0)
alpha_out=mask_count(ImageChops.multiply(ad,protected_im))
if outside or alpha_out: raise RuntimeError(("outside gate",outside,alpha_out))

source_png=out/"B159_SOURCE_READABLE.png"; clean_png=out/"B159_CLEAN_PLATE.png"; final_png=out/"B159_FINAL_READABLE.png"
source_png.parent.mkdir(parents=True,exist_ok=True)
src.save(source_png); clean.save(clean_png); dec.save(final_png)
allowed_im.save(out/"B159_ALLOWED_BBOX_MASK.png"); protected_im.save(out/"B159_PROTECTED_MASK.png")
source_text_im.save(out/"B159_SOURCE_TEXT_MASK.png"); render_im.save(out/"B159_LOCALIZED_RENDER_MASK.png")
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(source_png),str(clean_png),str(out/"B159_ALLOWED_BBOX_MASK.png"),
                "--protected-mask",str(out/"B159_PROTECTED_MASK.png"),"--report",str(out/"B159_CLEAN_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(source_png),str(final_png),str(out/"B159_ALLOWED_BBOX_MASK.png"),
                "--protected-mask",str(out/"B159_PROTECTED_MASK.png"),"--report",str(out/"B159_FINAL_VALIDATION.json")],check=True)
cr=json.loads((out/"B159_CLEAN_VALIDATION.json").read_text()); fr=json.loads((out/"B159_FINAL_VALIDATION.json").read_text())
if cr.get("status")!="PASS" or fr.get("status")!="PASS": raise RuntimeError(("validator",cr.get("status"),fr.get("status")))

# Focus visual evidence for each atlas sprite: SOURCE | CLEAN | FINAL.
for idx in (24,25,26):
    x,y,w,h=regs[idx]; pad=24
    box=(max(0,x-pad),max(0,y-pad),min(W,x+w+pad),min(H,y+h+pad))
    ims=[composite(z.crop(box)) for z in (src,clean,dec)]
    scale=min(3.0,1900/max(1,ims[0].width))
    ims=[z.resize((int(z.width*scale),int(z.height*scale)),Image.Resampling.NEAREST) for z in ims]
    card=Image.new("RGB",(sum(z.width for z in ims)+20,max(z.height for z in ims)+48),"white")
    xx=0; dd=ImageDraw.Draw(card)
    for lab,z in zip(("SOURCE","CLEAN","FINAL"),ims):
        card.paste(z,(xx,48)); dd.text((xx+6,12),lab,fill="black"); xx+=z.width+10
    save_jpg_b64(card,f"B159_IDX{idx}_FOCUS.jpg",96)

# Full readable and raw comparisons.
overview=Image.new("RGB",(1600,3*840),"white")
for i,(lab,im) in enumerate((("SOURCE",src),("CLEAN",clean),("FINAL",dec))):
    z=composite(im); z.thumbnail((1580,800),Image.Resampling.LANCZOS)
    overview.paste(z,(0,i*840+32)); ImageDraw.Draw(overview).text((8,i*840+8),lab,fill="black")
save_jpg_b64(overview,"B159_A8CE_SOURCE_CLEAN_FINAL.jpg",93)
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
rawsheet=Image.new("RGB",(1600,2*840),"white")
for i,(lab,im) in enumerate((("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec))):
    z=composite(im); z.thumbnail((1580,800),Image.Resampling.LANCZOS)
    rawsheet.paste(z,(0,i*840+32)); ImageDraw.Draw(rawsheet).text((8,i*840+8),lab,fill="black")
save_jpg_b64(rawsheet,"B159_A8CE_RAW_COMPARE.jpg",93)

report={
 "schema_version":1,"role":"B","run":run,"queue_index":52,"asset":asset,
 "readiness_tier":"ZOOM_REVIEW_POSITIVELY_CLASSIFIED_AND_RENDERED_SAME_INVOCATION",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"source_sha256":A8_SOURCE_SHA},
 "classification":{"prior_action":"zoom_review","localizable":["Extra Time","Start x2","Goal x2"],
                   "translations":{"Extra Time":"추가 시간","Start":"시작","Goal":"골"},
                   "protected":["0-9 number sprites","1P-6P player identifiers","progress bars/ticks/arrows","track fragments"]},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,
              "header_128_exact":payload[:128]==sb[:128],"raw_orientation":"mirror_y"},
 "approved_template_reuse":{"source_asset":"FF2462BB","source_candidate_sha256":FF_CAND_SHA,
                             "approval":"C86_PIXEL_VISUAL_PASS_PENDING_INGAME","rows":template_notes},
 "extra_time_source_style":{"font":Path(font_path).name,"font_size":size,"stroke_width":stroke,
                            "slant":0.20,"shadow_offset":shadow_off,
                            "fill_top_rgb":top_fill,"fill_bottom_rgb":bottom_fill,"outline_rgb":outline},
 "rows":rows,
 "clean_plate_validator":cr,"final_mask_validator":fr,
 "decoded_changes":{"outside_allowed_bboxes":outside,"alpha_outside":alpha_out,
                    "source_script_residue_outside_render_mask":residue,
                    "localized_overlap":0,"localized_1px_touch":0},
 "candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),
 "worker_static_qa":"PASS","controller_visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "status":"B159_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "runtime_validation":"UNTESTED"
}
(out/"B159_A8CE_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"B159_A8CE339F.json").write_text(json.dumps({
 "run":"B159","index":52,"asset":"A8CE339F","candidate_sha256":csha,
 "localized_physical_elements":5,"bbox_size_positive_margin":"5/5",
 "outside":outside,"alpha_outside":alpha_out,"source_script_residue":residue,
 "worker_status":report["status"],"report":f"localization/graphics/role_B/{run}/B159_A8CE_REPORT.json",
 "runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"B159","candidate_sha256":csha,"elements":5,"bbox":"5/5 PASS",
                  "outside":outside,"alpha_outside":alpha_out,"source_residue":residue},ensure_ascii=False),flush=True)
