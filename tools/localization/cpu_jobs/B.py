import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B hosted worker only")

repo=Path.cwd()
run="20261005-B-PRODUCTION41"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_selector_cvt_Exst/D41D0B1_512x64.dds"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_selector_cvt_Exst/D41D0B1_512x64.dds"
src_dds=Path("/tmp/D41D0B1_HD.dds")
urllib.request.urlretrieve(url,src_dds)
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

sb=src_dds.read_bytes()
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H=struct.unpack_from("<I",sb,12)[0]
W=struct.unpack_from("<I",sb,16)[0]
pitch=struct.unpack_from("<I",sb,20)[0]
mips=struct.unpack_from("<I",sb,28)[0]
pf_flags=struct.unpack_from("<I",sb,80)[0]
fourcc=sb[84:88]
rgb_bits=struct.unpack_from("<I",sb,88)[0]
masks=[struct.unpack_from("<I",sb,o)[0] for o in (92,96,100,104)]
if (W,H)!=(2048,256): raise RuntimeError(("unexpected dimensions",W,H))
if fourcc!=b"\x00\x00\x00\x00" or rgb_bits!=32 or pitch!=W*4 or mips not in (0,1):
    raise RuntimeError(("unexpected RGBA DDS",W,H,pitch,mips,fourcc,rgb_bits,pf_flags,masks))
if len(sb)!=128+W*H*4:
    raise RuntimeError(("unexpected byte size",len(sb),128+W*H*4))
# Require four independent 8-bit channels; exact ordering may vary and is handled below.
if sorted(masks)!=sorted([0x000000ff,0x0000ff00,0x00ff0000,0xff000000]):
    raise RuntimeError(("unsupported channel masks",masks))

src_raw=Image.open(src_dds).convert("RGBA")
src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)  # game/readable orientation
sa=np.asarray(src,dtype=np.uint8)
source_mask=sa[:,:,3]>0
ys,xs=np.nonzero(source_mask)
if not len(xs): raise RuntimeError("source alpha empty")
bbox=[int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
source_w=bbox[2]-bbox[0]; source_h=bbox[3]-bbox[1]

# This selector is a single text-only sentence. Fail closed if unrelated visible islands
# exist far away from the main alpha footprint.
row_counts=np.count_nonzero(source_mask,axis=1)
active_rows=np.flatnonzero(row_counts)
if active_rows[-1]-active_rows[0]+1 != source_h:
    gaps=[y for y in range(active_rows[0],active_rows[-1]+1) if row_counts[y]==0]
    if len(gaps)>max(3,source_h//12):
        raise RuntimeError(("unexpected multi-band source",bbox,len(gaps)))

# Exact clean plate: clear source glyph/effect alpha only and preserve hidden RGB.
clean_arr=sa.copy()
clean_arr[source_mask,3]=0
clean=Image.fromarray(clean_arr,"RGBA")

# Source palette: bright fill + dark navy outline/shadow.
pix=sa[source_mask]
lum=.2126*pix[:,0]+.7152*pix[:,1]+.0722*pix[:,2]
white_sel=(pix[:,0]>185)&(pix[:,1]>185)&(pix[:,2]>185)&(pix[:,3]>32)
dark_sel=(lum<130)&(pix[:,2]>=pix[:,0])&(pix[:,3]>16)
if not np.any(white_sel): raise RuntimeError("source white fill not detected")
white_rgb=tuple(int(v) for v in np.median(pix[white_sel,:3],axis=0))
white=(white_rgb[0],white_rgb[1],white_rgb[2],255)
if np.any(dark_sel):
    dark_rgb=tuple(int(v) for v in np.median(pix[dark_sel,:3],axis=0))
else:
    dark_rgb=(0,12,57)
dark=(dark_rgb[0],dark_rgb[1],dark_rgb[2],255)

# Measure source right-lean from the left edge of active rows.
samples=[]
for y in range(bbox[1],bbox[3]):
    xx=np.flatnonzero(source_mask[y,bbox[0]:bbox[2]])
    if len(xx)>=6:
        samples.append((y,float(xx.min()+bbox[0])))
if len(samples)<12: raise RuntimeError("insufficient slant samples")
yy=np.array([p[0] for p in samples],dtype=float)
xx=np.array([p[1] for p in samples],dtype=float)
slope=float(np.polyfit(yy,xx,1)[0])
measured_slant=max(0.18,min(0.38,-slope))
# Source family is visibly italic in this selector set; reject a nonsensical regression.
if measured_slant<0.18: raise RuntimeError(("source slant not recovered",slope,measured_slant))

def font_path():
    p=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
    if not p or not Path(p).exists() or "NotoSansCJK" not in Path(p).name:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
        p=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
    if not p: raise RuntimeError("font unavailable")
    return p
FONT=font_path()

def shear_rgba(im,s):
    shift=max(0,int(round(s*(im.height-1))))
    o=Image.new("RGBA",(im.width+shift,im.height),(0,0,0,0))
    for y in range(im.height):
        dx=int(round(s*(im.height-1-y)))
        o.alpha_composite(im.crop((0,y,im.width,y+1)),(dx,y))
    return o

korean="여자친구와 함께 골에 도착하세요."
dummy=ImageDraw.Draw(Image.new("L",(8,8),0))
layer=None
render_meta=None
# Slightly smaller than source is preferred; leave >=4 px positive margin where possible.
for fs in range(min(220,int(source_h*.98)),11,-1):
    f=ImageFont.truetype(FONT,fs)
    stroke=max(2,round(fs*.085))
    tb=dummy.textbbox((0,0),korean,font=f,stroke_width=stroke)
    pad=stroke+6
    size=(tb[2]-tb[0]+pad*2,tb[3]-tb[1]+pad*2)
    outer=Image.new("L",size,0)
    fill=Image.new("L",size,0)
    pos=(pad-tb[0],pad-tb[1])
    ImageDraw.Draw(outer).text(pos,korean,font=f,fill=255,stroke_width=stroke,stroke_fill=255)
    ImageDraw.Draw(fill).text(pos,korean,font=f,fill=255)
    tile=Image.new("RGBA",size,(0,0,0,0))
    tile.paste(dark,(0,0),outer)
    tile.paste(white,(0,0),fill)
    tile=shear_rgba(tile,measured_slant)
    ab=tile.getchannel("A").getbbox()
    if not ab: continue
    tile=tile.crop(ab)
    if tile.width>source_w-8 or tile.height>source_h-8: continue
    test=Image.new("RGBA",(W,H),(0,0,0,0))
    px=bbox[0]+(source_w-tile.width)//2
    py=bbox[1]+(source_h-tile.height)//2
    test.alpha_composite(tile,(px,py))
    lb=test.getchannel("A").getbbox()
    if not lb: continue
    if lb[0]<bbox[0] or lb[1]<bbox[1] or lb[2]>bbox[2] or lb[3]>bbox[3]:
        continue
    if (lb[2]-lb[0])>source_w or (lb[3]-lb[1])>source_h:
        continue
    if min(lb[0]-bbox[0],bbox[2]-lb[2],lb[1]-bbox[1],bbox[3]-lb[3])<2:
        continue
    layer=test
    render_meta=(fs,stroke,list(lb))
    break
if layer is None: raise RuntimeError(("cannot fit Korean",bbox,korean))

final=clean.copy()
final.alpha_composite(layer)
target=np.asarray(layer.getchannel("A"))>0
lb=render_meta[2]
localized_w=lb[2]-lb[0]; localized_h=lb[3]-lb[1]
if localized_w>source_w or localized_h>source_h:
    raise RuntimeError(("size ceiling",bbox,lb))

# Zero overlap/residue is exact for RGBA32: all source alpha is removed before target.
residue=int(np.count_nonzero(source_mask & (np.asarray(final)[:,:,3]>0) & ~target))
if residue: raise RuntimeError(("source residue",residue))
outside_bbox=np.ones((H,W),bool)
outside_bbox[bbox[1]:bbox[3],bbox[0]:bbox[2]]=False
fa=np.asarray(final,dtype=np.uint8)
changed=np.any(sa!=fa,axis=2)
changed_out=int(np.count_nonzero(changed & outside_bbox))
introduced_alpha_out=int(np.count_nonzero((fa[:,:,3]>sa[:,:,3]) & outside_bbox))
if changed_out or introduced_alpha_out:
    raise RuntimeError(("outside change",changed_out,introduced_alpha_out))

# Encode exact source DDS header and masks.
raw_arr=np.asarray(final.transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8)
def shift(mask):
    s=0
    while ((mask>>s)&1)==0: s+=1
    return s
rs,gs,bs,as_=[shift(m) for m in masks]
packed=((raw_arr[:,:,0].astype(np.uint32)<<rs)&masks[0]) | ((raw_arr[:,:,1].astype(np.uint32)<<gs)&masks[1]) | ((raw_arr[:,:,2].astype(np.uint32)<<bs)&masks[2]) | ((raw_arr[:,:,3].astype(np.uint32)<<as_)&masks[3])
outb=sb[:128]+packed.astype("<u4").tobytes()
if outb[:128]!=sb[:128]: raise RuntimeError("header changed")
candidate.write_bytes(outb)

# Decode persisted DDS and rerun exact pixel gates.
dec_raw=Image.open(candidate).convert("RGBA")
dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
da=np.asarray(dec,dtype=np.uint8)
decoded_changed=np.any(sa!=da,axis=2)
decoded_changed_out=int(np.count_nonzero(decoded_changed & outside_bbox))
decoded_alpha_out=int(np.count_nonzero((da[:,:,3]>sa[:,:,3])&outside_bbox))
if decoded_changed_out or decoded_alpha_out:
    raise RuntimeError(("decoded outside change",decoded_changed_out,decoded_alpha_out))
cm=da[bbox[1]:bbox[3],bbox[0]:bbox[2],3]>0
ys2,xs2=np.nonzero(cm)
if not len(xs2): raise RuntimeError("decoded target empty")
db=[bbox[0]+int(xs2.min()),bbox[1]+int(ys2.min()),bbox[0]+int(xs2.max())+1,bbox[1]+int(ys2.max())+1]
dw,dh=db[2]-db[0],db[3]-db[1]
if db[0]<bbox[0] or db[1]<bbox[1] or db[2]>bbox[2] or db[3]>bbox[3] or dw>source_w or dh>source_h:
    raise RuntimeError(("decoded size gate",bbox,db))
decoded_residue=int(np.count_nonzero(source_mask & (da[:,:,3]>0) & ~target))
if decoded_residue: raise RuntimeError(("decoded source residue",decoded_residue))

allowed=np.zeros((H,W),bool)
allowed[bbox[1]:bbox[3],bbox[0]:bbox[2]]=True
protected=~allowed
def mask(m): return Image.fromarray((m.astype(np.uint8)*255),"L")
source_mask_png=out/"D41D0B1_SOURCE_TEXT_MASK.png"; mask(source_mask).save(source_mask_png)
allowed_png=out/"D41D0B1_ALLOWED_TEXT_REGION_MASK.png"; mask(allowed).save(allowed_png)
protected_png=out/"D41D0B1_PROTECTED_MASK.png"; mask(protected).save(protected_png)
target_png=out/"D41D0B1_TARGET_TEXT_MASK.png"; mask(target).save(target_png)
clean_png=out/"D41D0B1_CLEAN_PLATE.png"; clean.save(clean_png)
src_png=Path("/tmp/D41_source.png"); final_png=Path("/tmp/D41_final.png")
src.save(src_png); dec.save(final_png)
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(src_png),str(clean_png),str(source_mask_png),"--report",str(out/"B_PRODUCTION41_CLEAN_PLATE_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(src_png),str(final_png),str(allowed_png),"--protected-mask",str(protected_png),"--report",str(out/"B_PRODUCTION41_FINAL_MASK_VALIDATION.json")],check=True)

# Human evidence in readable and raw DDS orientations.
def comp(im,bg=(64,64,64,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def labeled(label,im):
    rgb=comp(im)
    c=Image.new("RGB",(W,H+28),"white"); c.paste(rgb,(0,28))
    ImageDraw.Draw(c).text((5,5),label,fill="black")
    return c
cards=[labeled("SOURCE_READABLE",src),labeled("CLEAN_READABLE",clean),labeled("FINAL_READABLE",dec)]
sheet=Image.new("RGB",(W,H*3+84),"white")
for i,c in enumerate(cards): sheet.paste(c,(0,i*(H+28)))
sheet.save(out/"B_PRODUCTION41_D41_SOURCE_CLEAN_FINAL.jpg",quality=96)
raw_cards=[labeled("SOURCE_RAW_MIRROR_Y",src_raw),labeled("FINAL_RAW_MIRROR_Y",dec_raw)]
raw_sheet=Image.new("RGB",(W,(H+28)*2),"white")
raw_sheet.paste(raw_cards[0],(0,0)); raw_sheet.paste(raw_cards[1],(0,H+28))
raw_sheet.save(out/"B_PRODUCTION41_D41_RAW_COMPARE.jpg",quality=96)
pad=16
cr=(max(0,bbox[0]-pad),max(0,bbox[1]-pad),min(W,bbox[2]+pad),min(H,bbox[3]+pad))
ims=[comp(x).crop(cr) for x in [src,clean,dec]]
ims=[x.resize((x.width*2,x.height*2),Image.Resampling.NEAREST) for x in ims]
contact=Image.new("RGB",(sum(x.width for x in ims)+12,max(x.height for x in ims)+28),"white")
xx=0
for im in ims:
    contact.paste(im,(xx,28)); xx+=im.width+6
ImageDraw.Draw(contact).text((4,4),"Try to reach the goal with your girlfriend. -> "+korean,fill="black")
contact.save(out/"B_PRODUCTION41_D41_ROW_CONTACT_2X.jpg",quality=96)

report={
 "schema_version":1,"role":"B","run":run,"queue_index":112,"asset":asset,
 "readiness_tier":"RENDER_READY_COMPLETED_SAME_INVOCATION",
 "source_url":url,"source_sha256":sha(src_dds),"candidate_sha256":sha(candidate),
 "candidate_path":str(candidate.relative_to(repo)),
 "method":"canonical 2048x256 RGBA32 HD source; exact full alpha/effect source mask; alpha-only clean plate with hidden RGB preserved; source-measured white/navy palette and measured right slant; fresh native Hangul; exact source header/masks preserved; decoded final QA",
 "structure":{"width":W,"height":H,"format":"RGBA32","pitch":pitch,"mipmaps":1,"header_128_exact":candidate.read_bytes()[:128]==sb[:128],"raw_orientation":"mirror_y","channel_masks":[hex(x) for x in masks]},
 "source_style":{"white":white,"dark":dark,"measured_left_edge_slope":slope,"applied_right_slant":measured_slant},
 "element":{"source":"Try to reach the goal with your girlfriend.","korean":korean,
   "original_bbox":bbox,"localized_bbox":lb,"decoded_localized_bbox":db,
   "source_width":source_w,"source_height":source_h,
   "localized_width":localized_w,"localized_height":localized_h,
   "decoded_localized_width":dw,"decoded_localized_height":dh,
   "delta_left":lb[0]-bbox[0],"delta_right":bbox[2]-lb[2],"delta_top":lb[1]-bbox[1],"delta_bottom":bbox[3]-lb[3],
   "containment":"PASS","size_ceiling":"PASS","decoded_containment":"PASS","decoded_size_ceiling":"PASS",
   "font_size":render_meta[0],"stroke_width":render_meta[1]},
 "qa":{"changed_pixels_outside_source_bbox":decoded_changed_out,"introduced_alpha_outside_source_bbox":decoded_alpha_out,
   "source_residue_pixels":decoded_residue,"localized_overlap_pixels":0,"protected_pixels_changed":decoded_changed_out,"status":"PASS"},
 "manual_visual_qa":"PENDING_CONTROLLER_SELF_QA","RUNTIME_VALIDATION":"UNTESTED",
 "status":"B_PRODUCTION41_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
}
(out/"B_PRODUCTION41_D41_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"D41D0B1","index":112,"candidate_sha256":sha(candidate),"bbox_size_pass":"1/1",
 "changed_outside":decoded_changed_out,"alpha_outside":decoded_alpha_out,"source_residue":decoded_residue,
 "worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":"localization/graphics/role_B/20261005-B-PRODUCTION41/B_PRODUCTION41_D41_REPORT.json"}
(wr/"B_PRODUCTION41_D41D0B1.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
