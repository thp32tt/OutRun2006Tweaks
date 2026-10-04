#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B hosted worker only")

repo=Path.cwd()
run="20261005-B-PRODUCTION37"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_selector_cvt_Exst/1A43E9D9_512x64.dds"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_selector_cvt_Exst/1A43E9D9_512x64.dds"
src_dds=Path("/tmp/1A43E9D9_HD.dds")
urllib.request.urlretrieve(url,src_dds)
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def meta(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    mips=struct.unpack_from("<I",b,28)[0]; fourcc=b[84:88]
    need=128+((w+3)//4)*((h+3)//4)*16
    if fourcc!=b"DXT5" or mips not in (0,1) or len(b)!=need:
        raise RuntimeError(("unexpected DDS",w,h,mips,fourcc,len(b),need))
    return w,h,mips,fourcc

sb=src_dds.read_bytes()
W,H,_,_=meta(sb)
if (W,H)!=(2048,256): raise RuntimeError(("unexpected dimensions",W,H))
src=Image.open(src_dds).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
alpha=sa[:,:,3]>0
if np.count_nonzero(alpha)==0: raise RuntimeError("source alpha empty")

# This atlas is a two-line text-only selector label. Derive exact HD source glyph/effect
# bboxes from non-transparent source pixels instead of scaling the historical draft.
row_counts=np.count_nonzero(alpha,axis=1)
active=[i for i,n in enumerate(row_counts) if n>0]
if not active: raise RuntimeError("no_active_rows")
# BC3 alpha fringe bridges the small inter-line gap, so split the two source lines at
# the minimum-alpha valley near the middle instead of requiring a zero-alpha row.
lo,hi=active[0],active[-1]+1
span=hi-lo
ss=lo+max(4,int(span*.30)); ee=lo+min(span-4,int(span*.70))
if ee<=ss: raise RuntimeError(("split_window",lo,hi,ss,ee))
split=ss+int(np.argmin(row_counts[ss:ee]))
groups=[list(range(lo,split+1)),list(range(split+1,hi))]
if min(len(g) for g in groups)<4: raise RuntimeError(("bad_split",lo,hi,split))
texts=["아웃런 모드","15코스 연속"]
sources=["OutRun Mode","15 continuous course"]
rows=[]
source_masks=[]
for n,g in enumerate(groups):
    y0,y1=g[0],g[-1]+1
    ys,xs=np.nonzero(alpha[y0:y1])
    bb=[int(xs.min()),y0,int(xs.max())+1,y1]
    m=np.zeros((H,W),bool); m[y0:y1,:]=alpha[y0:y1,:]
    # Keep only this line's horizontal component footprint.
    m[:,:bb[0]]=False; m[:,bb[2]:]=False
    source_masks.append(m)
    rows.append({"n":n+1,"source":sources[n],"korean":texts[n],"original_bbox":bb})

if np.any(source_masks[0]&source_masks[1]): raise RuntimeError("source line overlap")
source_mask=source_masks[0]|source_masks[1]
# Verify no unrelated source artwork exists outside the two derived line masks.
source_visible_out=int(np.count_nonzero(alpha & ~source_mask))
if source_visible_out: raise RuntimeError(("unexpected_preserved_artwork",source_visible_out))

clean_arr=sa.copy()
clean_arr[source_mask]=(0,0,0,0)
clean=Image.fromarray(clean_arr,"RGBA")

def font_path():
    p=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
    if not p or not Path(p).exists() or "NotoSansCJK" not in Path(p).name:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","libnvtt-bin"],check=True)
        p=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
    if not p: raise RuntimeError("font unavailable")
    return p
FONT=font_path()
if not Path("/usr/bin/nvcompress").exists():
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","libnvtt-bin"],check=True)

# Measure source-family palette from opaque source pixels.
pix=sa[source_mask]
lum=.2126*pix[:,0]+.7152*pix[:,1]+.0722*pix[:,2]
orange_sel=(pix[:,0]>170)&(pix[:,1]>55)&(pix[:,1]<210)&(pix[:,2]<120)&(pix[:,0].astype(int)>pix[:,1].astype(int)+25)
white_sel=(pix[:,0]>180)&(pix[:,1]>180)&(pix[:,2]>180)
dark_sel=lum<105
orange=tuple(int(x) for x in np.median(pix[orange_sel],axis=0)) if np.any(orange_sel) else (255,145,0,255)
white=tuple(int(x) for x in np.median(pix[white_sel],axis=0)) if np.any(white_sel) else (245,245,245,255)
dark=tuple(int(x) for x in np.median(pix[dark_sel],axis=0)) if np.any(dark_sel) else (12,24,48,255)

def shear_rgba(im,s):
    shift=max(0,int(round(s*(im.height-1))))
    o=Image.new("RGBA",(im.width+shift,im.height),(0,0,0,0))
    for y in range(im.height):
        dx=int(round(s*(im.height-1-y)))
        o.alpha_composite(im.crop((0,y,im.width,y+1)),(dx,y))
    return o

def render(text,bb):
    x0,y0,x1,y1=bb
    # Keep the Korean raster in a block-safe interior so DXT5 edge blocks can remain
    # source-color exact while source English alpha is cleared separately.
    bx0=((x0+3)//4)*4; by0=((y0+3)//4)*4
    bx1=(x1//4)*4; by1=(y1//4)*4
    if bx1-bx0<16 or by1-by0<16: raise RuntimeError(("no_block_safe_interior",bb))
    aw,ah=bx1-bx0,by1-by0
    d=ImageDraw.Draw(Image.new("L",(8,8),0))
    slant=.22
    for fs in range(min(180,int(ah*1.05)),9,-1):
        f=ImageFont.truetype(FONT,fs)
        inner=max(1,round(fs*.045)); outer=max(inner+1,round(fs*.075))
        tb=d.textbbox((0,0),text,font=f,stroke_width=outer)
        pad=outer+5
        size=(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad)
        fill=Image.new("L",size,0); mid=Image.new("L",size,0); outm=Image.new("L",size,0)
        pos=(pad-tb[0],pad-tb[1])
        ImageDraw.Draw(fill).text(pos,text,font=f,fill=255)
        ImageDraw.Draw(mid).text(pos,text,font=f,fill=255,stroke_width=inner,stroke_fill=255)
        ImageDraw.Draw(outm).text(pos,text,font=f,fill=255,stroke_width=outer,stroke_fill=255)
        tile=Image.new("RGBA",size,(0,0,0,0))
        tile.paste(white,(0,0),outm)
        tile.paste(dark,(0,0),mid)
        tile.paste(orange,(0,0),fill)
        tile=shear_rgba(tile,slant)
        ab=tile.getchannel("A").getbbox()
        if not ab: continue
        tile=tile.crop(ab)
        if tile.width>aw-4 or tile.height>ah-4: continue
        layer=Image.new("RGBA",(W,H),(0,0,0,0))
        px=bx0+(aw-tile.width)//2; py=by0+(ah-tile.height)//2
        layer.alpha_composite(tile,(px,py))
        lb=layer.getchannel("A").getbbox()
        if lb and lb[0]>x0 and lb[1]>y0 and lb[2]<x1 and lb[3]<y1:
            return layer,fs,inner,outer,list(lb),[bx0,by0,bx1,by1],slant
    raise RuntimeError(("cannot_fit",text,bb))

final=clean.copy()
layers=[]
for row in rows:
    layer,fs,inner,outer,lb,blockbb,slant=render(row["korean"],row["original_bbox"])
    for old in layers:
        if ImageChops.multiply(layer.getchannel("A"),old.getchannel("A")).getbbox():
            raise RuntimeError("localized overlap")
    layers.append(layer); final.alpha_composite(layer)
    ob=row["original_bbox"]; sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    ok=lb[0]>=ob[0] and lb[1]>=ob[1] and lb[2]<=ob[2] and lb[3]<=ob[3] and lw<=sw and lh<=sh
    if not ok: raise RuntimeError(("size gate",row["source"],ob,lb))
    row.update({"localized_bbox":lb,"source_width":sw,"source_height":sh,"localized_width":lw,"localized_height":lh,
                "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
                "containment":"PASS","size_ceiling":"PASS","font_size":fs,"inner_stroke":inner,"outer_stroke":outer,
                "slant":slant,"block_safe_bbox":blockbb})
target=np.zeros((H,W),bool)
for layer in layers: target|=(np.asarray(layer.getchannel("A"))>0)

# Encode a full candidate, then splice only source-bbox-safe DXT5 blocks.
raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
tmp_png=Path("/tmp/1A43_final_raw.png"); tmp_dds=Path("/tmp/1A43_final_nv.dds")
raw.save(tmp_png)
subprocess.run(["/usr/bin/nvcompress","-bc3","-nomips",str(tmp_png),str(tmp_dds)],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
tb=tmp_dds.read_bytes(); meta(tb)
allowed=np.zeros((H,W),bool)
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]; allowed[y0:y1,x0:x1]=True
allowed_raw=np.flipud(allowed); srcmask_raw=np.flipud(source_mask); target_raw=np.flipud(target)
source_raw_alpha=np.flipud(sa[:,:,3])
bw=W//4; bh=H//4; outb=bytearray(sb); full_blocks=set(); partial_blocks=set()

def alpha_idx(block):
    bits=int.from_bytes(block[2:8],"little")
    return [(bits>>(3*i))&7 for i in range(16)]
def set_alpha_idx(block,idx):
    bits=sum((int(v)&7)<<(3*i) for i,v in enumerate(idx))
    return block[:2]+bits.to_bytes(6,"little")+block[8:]

for by in range(bh):
    y=by*4
    if not np.any(allowed_raw[y:y+4]): continue
    for bx in range(bw):
        x=bx*4; am=allowed_raw[y:y+4,x:x+4]
        if not np.any(am): continue
        off=128+(by*bw+bx)*16
        # Full block entirely inside an original source bbox may use freshly compressed Korean.
        if np.all(am):
            outb[off:off+16]=tb[off:off+16]; full_blocks.add((bx,by)); continue
        # Edge block: target is forbidden by block-safe render. Clear only original source
        # glyph alpha indices and preserve source color bytes exactly.
        if np.any(target_raw[y:y+4,x:x+4]): raise RuntimeError(("target_in_partial_block",bx,by))
        sm=srcmask_raw[y:y+4,x:x+4]
        if not np.any(sm): continue
        ob=bytes(outb[off:off+16]); idx=alpha_idx(ob)
        sa4=source_raw_alpha[y:y+4,x:x+4]
        zero=[idx[yy*4+xx] for yy in range(4) for xx in range(4) if sa4[yy,xx]<=1]
        if not zero: raise RuntimeError(("partial_no_transparent_index",bx,by))
        zi=Counter(zero).most_common(1)[0][0]
        for yy in range(4):
            for xx in range(4):
                if sm[yy,xx]: idx[yy*4+xx]=zi
        nb=set_alpha_idx(ob,idx)
        if nb[8:]!=ob[8:]: raise RuntimeError("partial color bytes changed")
        outb[off:off+16]=nb; partial_blocks.add((bx,by))

candidate.write_bytes(outb)
cand_sha=sha(candidate)
dec=Image.open(candidate).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
da=np.asarray(dec,dtype=np.uint8)
diff=np.any(sa!=da,axis=2)
alpha_diff=sa[:,:,3]!=da[:,:,3]
visible_out=int(np.count_nonzero((da[:,:,3]>1)&~allowed))
alpha_out=int(np.count_nonzero(alpha_diff&~allowed))
if visible_out or alpha_out: raise RuntimeError(("outside",visible_out,alpha_out))
# No English source alpha may survive outside the Korean target footprint.
guard=np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
residue=int(np.count_nonzero(source_mask&(da[:,:,3]>8)&~guard))
if residue: raise RuntimeError(("source_residue",residue))
# Re-measure decoded BC3 alpha per source line; compression fringe must still stay
# inside the exact source glyph/effect bbox and source size ceiling.
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]
    cm=(da[y0:y1,x0:x1,3]>1)
    ys,xs=np.nonzero(cm)
    if not len(xs): raise RuntimeError(("decoded_line_empty",row["source"]))
    db=[x0+int(xs.min()),y0+int(ys.min()),x0+int(xs.max())+1,y0+int(ys.max())+1]
    dw,dh=db[2]-db[0],db[3]-db[1]
    if db[0]<x0 or db[1]<y0 or db[2]>x1 or db[3]>y1 or dw>row["source_width"] or dh>row["source_height"]:
        raise RuntimeError(("decoded_size_gate",row["source"],row["original_bbox"],db))
    row["decoded_localized_bbox"]=db
    row["decoded_localized_width"]=dw; row["decoded_localized_height"]=dh
    row["decoded_containment"]="PASS"; row["decoded_size_ceiling"]="PASS"

# Persist masks and validation evidence.
def mask(m): return Image.fromarray((m.astype(np.uint8)*255),"L")
source_mask_png=out/"1A43E9D9_SOURCE_TEXT_MASK.png"; mask(source_mask).save(source_mask_png)
allowed_png=out/"1A43E9D9_ALLOWED_TEXT_REGION_MASK.png"; mask(allowed).save(allowed_png)
protected_png=out/"1A43E9D9_PROTECTED_MASK.png"; mask(~allowed).save(protected_png)
target_png=out/"1A43E9D9_TARGET_TEXT_MASK.png"; mask(target).save(target_png)
clean_png=out/"1A43E9D9_CLEAN_PLATE.png"; clean.save(clean_png)
src_png=Path("/tmp/1A43_source.png"); final_png=Path("/tmp/1A43_final.png")
src.save(src_png); dec.save(final_png)
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(src_png),str(clean_png),str(source_mask_png),"--report",str(out/"B_PRODUCTION37_CLEAN_PLATE_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(src_png),str(final_png),str(allowed_png),"--protected-mask",str(protected_png),"--report",str(out/"B_PRODUCTION37_FINAL_MASK_VALIDATION.json")],check=True)

# Source/clean/final evidence.
def comp(im,bg):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def card(label,im):
    c=Image.new("RGB",(W,H+28),"white"); c.paste(comp(im,(64,64,64,255)),(0,28)); ImageDraw.Draw(c).text((5,5),label,fill="black"); return c
cards=[card("SOURCE",src),card("CLEAN",clean),card("FINAL",dec)]
sheet=Image.new("RGB",(W,H*3+84),"white")
for i,c in enumerate(cards): sheet.paste(c,(0,i*(H+28)))
sheet.save(out/"B_PRODUCTION37_1A43_SOURCE_CLEAN_FINAL.jpg",quality=96)
# 2x row contact.
contacts=[]
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]; p=12; cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[comp(z,(64,64,64,255)).crop(cr) for z in [src,clean,dec]]
    ims=[x.resize((x.width*2,x.height*2),Image.Resampling.NEAREST) for x in ims]
    cw=sum(x.width for x in ims)+12; ch=max(x.height for x in ims)+24
    c=Image.new("RGB",(cw,ch),"white"); xx=0
    for im in ims: c.paste(im,(xx,24)); xx+=im.width+6
    ImageDraw.Draw(c).text((4,4),row["source"]+" -> "+row["korean"],fill="black"); contacts.append(c)
cs=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4),"white"); yy=0
for c in contacts: cs.paste(c,(0,yy)); yy+=c.height+4
cs.save(out/"B_PRODUCTION37_1A43_ROW_CONTACT_2X.jpg",quality=96)

changed_blocks=0; outside_patch=0; patch=full_blocks|partial_blocks
for by in range(bh):
    for bx in range(bw):
        off=128+(by*bw+bx)*16
        if sb[off:off+16]!=outb[off:off+16]:
            changed_blocks+=1
            if (bx,by) not in patch: outside_patch+=1
if outside_patch: raise RuntimeError(("compressed_outside_patch",outside_patch))
report={
 "schema_version":1,"role":"B","run":run,"queue_index":92,"asset":asset,
 "readiness_tier":"RENDER_READY_COMPLETED_SAME_INVOCATION","source_url":url,"source_sha256":sha(src_dds),
 "candidate_sha256":cand_sha,"candidate_path":str(candidate.relative_to(repo)),
 "method":"canonical 2048x256 DXT5 HD source; exact two-line source-alpha bboxes; transparent clean plate; fresh native Hangul with source orange/dark/white palette and right slant; block-safe Korean render; partial edge blocks alpha-only source cleanup; decoded QA",
 "structure":{"width":W,"height":H,"format":"DXT5","mipmaps":1,"header_128_exact":bytes(outb[:128])==sb[:128],"raw_orientation":"mirror_y"},
 "source_visible_pixels_outside_two_text_lines":source_visible_out,
 "palette":{"orange":orange,"dark":dark,"white":white},
 "rows":rows,
 "containment":{"elements_total":2,"elements_pass":2,"localized_overlap_pixels":0,"visible_pixels_outside_original_bboxes":visible_out,"alpha_changed_pixels_outside_original_bboxes":alpha_out,"source_residue_pixels_outside_target":residue,"status":"PASS"},
 "compressed_patch":{"full_blocks":len(full_blocks),"partial_alpha_only_blocks":len(partial_blocks),"changed_blocks":changed_blocks,"changed_blocks_outside_patch":outside_patch,"partial_color_bytes_preserved":True,"status":"PASS"},
 "manual_visual_qa":"PENDING_CONTROLLER_SELF_QA","RUNTIME_VALIDATION":"UNTESTED",
 "status":"B_PRODUCTION37_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
}
(out/"B_PRODUCTION37_1A43_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"1A43E9D9","index":92,"candidate_sha256":cand_sha,"bbox_size_pass":"2/2","visible_outside":visible_out,"alpha_outside":alpha_out,"source_residue":residue,"changed_blocks_outside_patch":outside_patch,"worker_status":report["status"],"runtime_validation":"UNTESTED","report":"localization/graphics/role_B/20261005-B-PRODUCTION37/B_PRODUCTION37_1A43_REPORT.json"}
(wr/"B_PRODUCTION37_1A43E9D9.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
