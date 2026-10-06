#!/usr/bin/env python3
import hashlib,json,math,os,struct,subprocess,urllib.parse,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

subprocess.run(["python","-m","pip","install","--disable-pip-version-check","-q","psd-tools==1.10.8","opencv-python-headless==4.10.0.84"],check=True)
from psd_tools import PSDImage
import cv2

repo=Path.cwd()
run="20261006-A-WORKSTEAL128-33491F83-TELEA-INPAINT"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

queue_index=62
asset="textures/load/spr_sprani_loading_cvt_Exst/33491F83_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)

src_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_loading_cvt_Exst/33491F83_512x256.dds"
SOURCE_SHA="796531b06a159745d799f66f1476b9f78c5a14fd670468f58ce5404e6ced0551"
psd_commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
psd_rel="PSDs, XCFs, SVGs, and other Working Source Assets/OutRun2SP Mode UI/spr_sprani_loading_cvt_Exst/33491F83_512x256.psd"
psd_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+psd_commit+"/"+urllib.parse.quote(psd_rel,safe="/")

srcp=Path("/tmp/A128_33491F83.dds")
psdp=Path("/tmp/A128_33491F83.psd")
urllib.request.urlretrieve(src_url,srcp)
urllib.request.urlretrieve(psd_url,psdp)

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
raw=srcp.read_bytes()
if sha_bytes(raw)!=SOURCE_SHA: raise RuntimeError(("source drift",sha_bytes(raw)))
if raw[:4]!=b"DDS ": raise RuntimeError("not DDS")
H=struct.unpack_from("<I",raw,12)[0]
W=struct.unpack_from("<I",raw,16)[0]
MIPS=struct.unpack_from("<I",raw,28)[0]
FOURCC=raw[84:88]
BPP=struct.unpack_from("<I",raw,88)[0]
MASKS=struct.unpack_from("<IIII",raw,92)
if (W,H,MIPS,FOURCC,BPP)!=(2048,1024,1,b"\0\0\0\0",32):
    raise RuntimeError(("source structure",W,H,MIPS,FOURCC,BPP))
if MASKS!=(0xff,0xff00,0xff0000,0xff000000):
    raise RuntimeError(("source masks",MASKS))

src_raw=Image.open(srcp).convert("RGBA")
src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)

# Parse layered authoring source and locate the nine visible rasterized English labels.
psd=PSDImage.open(psdp)
if (psd.width,psd.height)!=(W,H): raise RuntimeError(("PSD canvas",psd.width,psd.height))

layers=[]
def walk(group,parent=""):
    for layer in group:
        path=(parent+"/"+layer.name).strip("/")
        layers.append((path,layer))
        if layer.is_group(): walk(layer,path)
walk(psd)

label_layers=[]
for path,layer in layers:
    if "/Text/" in path and layer.name.endswith("[Rasterized]") and getattr(layer,"kind",None)=="pixel":
        label_layers.append((path,layer))
if len(label_layers)!=9:
    raise RuntimeError(("expected 9 rasterized text layers",len(label_layers),[p for p,_ in label_layers]))

# Stable path -> translation/style binding.
bindings={}
for path,layer in label_layers:
    if "Bunki - Remastered/Text/Diverge/" in path:
        key="diverge_main"; ko="분기"; family="yellow"; style_group="diverge"; shear=0.0; cell="main"
    elif "Bunki - Remastered/Text/Left-Easy/EASY" in path:
        key="easy_main"; ko="쉬움"; family="green"; style_group="main_diff"; shear=0.0; cell="main"
    elif "Bunki - Remastered/Text/Left-Easy/Left" in path:
        key="left_main"; ko="좌측"; family="green"; style_group="main_lr"; shear=0.0; cell="main"
    elif "Bunki - Remastered/Text/Right-Hard/HARD" in path:
        key="hard_main"; ko="어려움"; family="red"; style_group="main_diff"; shear=0.0; cell="main"
    elif "Bunki - Remastered/Text/Right-Hard/Right" in path:
        key="right_main"; ko="우측"; family="red"; style_group="main_lr"; shear=0.0; cell="main"
    elif "Manual Work/Text/Regular/EASY" in path:
        key="easy_alone"; ko="쉬움"; family="green"; style_group="regular_diff"; shear=0.0; cell="detached"
    elif "Manual Work/Text/Regular/HARD" in path:
        key="hard_alone"; ko="어려움"; family="red"; style_group="regular_diff"; shear=0.0; cell="detached"
    elif "Oblique - 27 degrees shear/Up-EASY/EASY" in path:
        key="easy_arrow"; ko="쉬움"; family="green"; style_group="oblique_diff"; shear=math.tan(math.radians(27)); cell="detached"
    elif "Oblique - 27 degrees shear/Down-HARD/HARD" in path:
        key="hard_arrow"; ko="어려움"; family="red"; style_group="oblique_diff"; shear=math.tan(math.radians(27)); cell="detached"
    else:
        raise RuntimeError(("unbound PSD text layer",path))
    bindings[key]={"key":key,"path":path,"layer":layer,"ko":ko,"family":family,
                   "style_group":style_group,"shear":shear,"cell":cell}

if set(bindings)!=set(["diverge_main","left_main","right_main","easy_main","hard_main",
                       "hard_arrow","easy_arrow","hard_alone","easy_alone"]):
    raise RuntimeError(("binding keys",sorted(bindings)))

# Exact source-text/effect masks come from the authoring PSD's visible rasterized
# label layers, not OCR/threshold rectangles. This solves the prior under/over-mask problem.
source_mask=np.zeros((H,W),bool)
rows=[]
exclude_keys=set()
for key in ["diverge_main","left_main","right_main","easy_main","hard_main",
            "hard_arrow","easy_arrow","hard_alone","easy_alone"]:
    b=bindings[key]; layer=b["layer"]
    exclude_keys.add((layer.name,int(layer.left),int(layer.top),int(layer.right),int(layer.bottom)))
    im=layer.topil()
    if im is None: raise RuntimeError(("no pixel image",key))
    im=im.convert("RGBA")
    if im.size!=(layer.width,layer.height):
        raise RuntimeError(("layer image size",key,im.size,(layer.width,layer.height)))
    a=np.asarray(im)[:,:,3]>0
    if not a.any(): raise RuntimeError(("empty rasterized alpha",key))
    ys,xs=np.nonzero(a)
    x0=int(layer.left+xs.min()); y0=int(layer.top+ys.min())
    x1=int(layer.left+xs.max()+1); y1=int(layer.top+ys.max()+1)
    m=np.zeros((H,W),bool)
    m[int(layer.top):int(layer.bottom),int(layer.left):int(layer.right)]=a
    if np.any(source_mask&m): raise RuntimeError(("text masks overlap",key))
    source_mask|=m
    yy,xx=np.nonzero(m)
    rows.append({
      "key":key,"source":layer.name.replace(" [Rasterized]",""),"korean":b["ko"],
      "psd_layer_path":b["path"],"source_bbox":[x0,y0,x1,y1],
      "source_mask_pixels":int(m.sum()),"source_centroid":[float(xx.mean()),float(yy.mean())],
      "family":b["family"],"style_group":b["style_group"],"shear":b["shear"],"cell":b["cell"],
      "_mask":m
    })

# Build exact manual clean artwork from the authoring PSD components that were
# created specifically to erase the AI/upscaled typography:
#   Layer 43: full main-route art with EASY/HARD already removed.
#   Erase Left and Right and Diverge: clean patches for the remaining 3 labels.
# Composite those authoring layers, then splice ONLY through exact label alpha masks.
layer43_path="objects/**Put any graphic and text art inside this folder**/Manual Work/Bunki - Remastered/Bunki graphic/Erase AI Typography/4xHDcube3/Layer 43"
erase_path="objects/**Put any graphic and text art inside this folder**/Manual Work/Bunki - Remastered/Bunki graphic/Erase AI Typography/Erase Left and Right and Diverge"
by_path={p:l for p,l in layers}
if layer43_path not in by_path or erase_path not in by_path:
    raise RuntimeError("manual clean PSD layers missing")
layer43=by_path[layer43_path]; erase=by_path[erase_path]
base_im=layer43.topil()
erase_im=erase.topil()
if base_im is None or erase_im is None:
    raise RuntimeError("manual clean PSD pixel image missing")
manual_clean=Image.new("RGBA",(W,H),(0,0,0,0))
manual_clean.alpha_composite(base_im.convert("RGBA"),(int(layer43.left),int(layer43.top)))
manual_clean.alpha_composite(erase_im.convert("RGBA"),(int(erase.left),int(erase.top)))
mca=np.asarray(manual_clean,dtype=np.uint8)

# Build authoritative clean plate with component-specific authoring layers.
# Layer 43 is the verified clean source for EASY/HARD. The erase patch layer is
# ONLY valid for Diverge/Left/Right; applying it globally creates the white
# patch-box defect caught by controller visual QA in A125.
layer43_canvas=Image.new("RGBA",(W,H),(0,0,0,0))
layer43_canvas.alpha_composite(base_im.convert("RGBA"),(int(layer43.left),int(layer43.top)))
erase_canvas=layer43_canvas.copy()
erase_canvas.alpha_composite(erase_im.convert("RGBA"),(int(erase.left),int(erase.top)))
l43a=np.asarray(layer43_canvas,dtype=np.uint8)
era=np.asarray(erase_canvas,dtype=np.uint8)

clean_arr=sa.copy()
manual_missing={}
clean_component_by_key={}
for row in rows:
    m=row["_mask"]
    if row["cell"]=="main":
        if row["key"] in {"easy_main","hard_main"}:
            # The PSD erase layer leaves a broad white plate here. Use
            # edge-aware Telea inpainting on a padded authoritative-source crop
            # and copy back ONLY exact source-text pixels. This preserves the
            # curved road/green border continuity while keeping zero drift
            # outside the declared text mask.
            y0=max(0,row["source_bbox"][1]-48); y1=min(H,row["source_bbox"][3]+48)
            x0=max(0,row["source_bbox"][0]-48); x1=min(W,row["source_bbox"][2]+48)
            cm=m[y0:y1,x0:x1]
            ca=sa[y0:y1,x0:x1]
            if not cm.any() or np.all(cm):
                raise RuntimeError(("invalid inpaint mask",row["key"]))
            # OpenCV works in BGRA/BGR. Preserve source alpha separately.
            bgr=cv2.cvtColor(ca[:,:,:3],cv2.COLOR_RGB2BGR)
            mask8=(cm.astype(np.uint8)*255)
            inp=cv2.inpaint(bgr,mask8,7.0,cv2.INPAINT_TELEA)
            rgb=cv2.cvtColor(inp,cv2.COLOR_BGR2RGB)
            patch=clean_arr[y0:y1,x0:x1].copy()
            patch[cm,:3]=rgb[cm]
            patch[cm,3]=ca[cm,3]
            clean_arr[y0:y1,x0:x1]=patch
            clean_component_by_key[row["key"]]="OpenCV Telea r7 exact-mask inpaint"
            manual_missing[row["key"]]=0
            continue
        else:
            component=era
            clean_component_by_key[row["key"]]="Erase Left and Right and Diverge"
        missing=int(np.count_nonzero(m & (component[:,:,3]==0)))
        manual_missing[row["key"]]=missing
        if missing:
            raise RuntimeError(("manual clean alpha missing",row["key"],missing))
        clean_arr[m]=component[m]
    else:
        clean_arr[m]=0
clean=Image.fromarray(clean_arr,"RGBA")

# Deterministic regression guards for the A125/A126 visual false-negatives:
# inpaint may change ONLY exact source-text pixels and must not reproduce the
# Layer-43 broad white erasure plate byte-for-byte.
for row in rows:
    if row["key"] in {"easy_main","hard_main"}:
        m=row["_mask"]
        if np.array_equal(clean_arr[m],l43a[m]):
            raise RuntimeError(("easy/hard fell back to Layer 43 patch",row["key"]))
clean_changed=np.any(clean_arr!=sa,axis=2)
clean_outside=int(np.count_nonzero(clean_changed & ~source_mask))
if clean_outside: raise RuntimeError(("clean outside source mask",clean_outside))
manual_clean.save(out/"A128_MANUAL_PSD_CLEAN_COMPONENT.png")

# Source-family colors sampled from the authoritative release inside each exact PSD mask.
def sample_style(row):
    m=row["_mask"]; px=sa[m]
    rgb=px[:,:3].astype(np.int16)
    r,g,b=rgb[:,0],rgb[:,1],rgb[:,2]
    if row["family"]=="green":
        sel=(g>110)&(g>r+35)&(g>b+20)
    elif row["family"]=="red":
        sel=(r>125)&(r>g+45)&(r>b+25)
    else:
        sel=(r>155)&(g>145)&(b<125)&(r>g-50)
    fill=tuple(int(v) for v in np.median(rgb[sel],axis=0))+(255,) if sel.any() else {
      "green":(0,179,96,255),"red":(199,50,50,255),"yellow":(230,230,0,255)}[row["family"]]
    nsel=(r<95)&(g<105)&(b<145)&(b>r+18)&(b>g+8)
    navy=tuple(int(v) for v in np.median(rgb[nsel],axis=0))+(255,) if nsel.any() else (0,10,57,255)
    wsel=(r>240)&(g>240)&(b>240)
    white=tuple(int(v) for v in np.median(rgb[wsel],axis=0))+(255,) if wsel.any() else (255,255,255,255)
    row["fill_rgba"]=fill; row["navy_rgba"]=navy; row["white_rgba"]=white
for row in rows: sample_style(row)

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
FONT=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
if not FONT or not Path(FONT).exists(): raise RuntimeError(("font",FONT))

def shear_image(im,k):
    if abs(k)<1e-6:return im
    add=max(1,int(math.ceil(abs(k)*im.height)))
    # Right-lean: x' = x + k*(h-y), matching source oblique label direction.
    return im.transform((im.width+add,im.height),Image.Transform.AFFINE,
                        (1,-k,add,0,1,0),resample=Image.Resampling.BICUBIC)

def make_glyph(row,fs):
    outer=max(3,round(fs*0.10)); inner=max(2,round(fs*0.065))
    font=ImageFont.truetype(FONT,fs)
    probe=Image.new("RGBA",(1200,360),(0,0,0,0))
    d=ImageDraw.Draw(probe)
    tb=d.textbbox((0,0),row["korean"],font=font,stroke_width=outer)
    xy=(40-tb[0],40-tb[1])
    if row["key"]=="diverge_main":
        d.text(xy,row["korean"],font=font,fill=row["fill_rgba"],stroke_width=outer,stroke_fill=row["navy_rgba"])
    else:
        d.text(xy,row["korean"],font=font,fill=row["fill_rgba"],stroke_width=outer,stroke_fill=row["white_rgba"])
        d.text(xy,row["korean"],font=font,fill=row["fill_rgba"],stroke_width=inner,stroke_fill=row["navy_rgba"])
    gb=probe.getchannel("A").getbbox()
    if not gb:return None
    g=probe.crop(gb)
    g=shear_image(g,row["shear"])
    gb=g.getchannel("A").getbbox()
    if gb:g=g.crop(gb)
    return g,outer,inner

# Shared source family => shared Korean point size within each corresponding label family.
groups={}
for row in rows: groups.setdefault(row["style_group"],[]).append(row)
for group,grows in groups.items():
    chosen=None
    for fs in range(110,15,-1):
        built=[]
        good=True
        for row in grows:
            got=make_glyph(row,fs)
            if got is None: good=False;break
            glyph,outer,inner=got
            x0,y0,x1,y1=row["source_bbox"]
            if glyph.width>(x1-x0)-2 or glyph.height>(y1-y0)-2:
                good=False;break
            built.append((row,glyph,outer,inner))
        if good:
            chosen=(fs,built);break
    if chosen is None: raise RuntimeError(("no shared-style fit",group))
    fs,built=chosen
    for row,glyph,outer,inner in built:
        row["_glyph"]=glyph; row["font_size"]=fs; row["outer_stroke_px"]=outer; row["navy_stroke_px"]=inner

# Place each glyph nearest the source-label centroid, with mandatory 1px positive bbox margin.
final=clean.copy()
target=np.zeros((H,W),bool)
for row in rows:
    g=row["_glyph"]; x0,y0,x1,y1=row["source_bbox"]
    cx,cy=row["source_centroid"]
    px=int(round(cx-g.width/2)); py=int(round(cy-g.height/2))
    px=max(x0+1,min(px,x1-g.width-1))
    py=max(y0+1,min(py,y1-g.height-1))
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); layer.alpha_composite(g,(px,py))
    lm=np.asarray(layer.getchannel("A"))>0
    ys,xs=np.nonzero(lm)
    lb=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
    if not(lb[0]>x0 and lb[1]>y0 and lb[2]<x1 and lb[3]<y1):
        raise RuntimeError(("target containment",row["key"],row["source_bbox"],lb))
    if np.any(target&lm): raise RuntimeError(("localized overlap",row["key"]))
    final.alpha_composite(layer); target|=lm
    row["localized_bbox"]=lb
    row["font"]="Noto Sans CJK KR Black"
    row["anchor"]=[px,py]
    row["source_width"]=x1-x0; row["source_height"]=y1-y0
    row["localized_width"]=lb[2]-lb[0]; row["localized_height"]=lb[3]-lb[1]
    row["delta_left"]=lb[0]-x0; row["delta_right"]=x1-lb[2]
    row["delta_top"]=lb[1]-y0; row["delta_bottom"]=y1-lb[3]
    row["containment"]="PASS";row["size_ceiling"]="PASS";row["positive_margin"]="PASS"

# Hard allowed region is union of exact source-effect bboxes.
allowed=np.zeros((H,W),bool)
for row in rows:
    x0,y0,x1,y1=row["source_bbox"];allowed[y0:y1,x0:x1]=True
if int(np.count_nonzero(target&~allowed)): raise RuntimeError("target outside source bboxes")

# Encode exact RGBA32 preserving original header and raw mirror-Y.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=raw[:128]+raw_final.tobytes("raw","RGBA")
if payload[:128]!=raw[:128] or len(payload)!=len(raw): raise RuntimeError("DDS structure drift")
candidate.write_bytes(payload)
cand_sha=sha_bytes(payload)
dec=Image.open(candidate).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("DDS roundtrip mismatch")
da=np.asarray(dec,dtype=np.uint8)

changed=np.any(da!=sa,axis=2)
outside=int(np.count_nonzero(changed&~allowed))
alpha_out=int(np.count_nonzero((da[:,:,3]!=sa[:,:,3])&~allowed))
target_out=int(np.count_nonzero(target&~allowed))
if outside or alpha_out or target_out:
    raise RuntimeError(("zero-pixel gate",outside,alpha_out,target_out))
rows_pass=sum(1 for r in rows if min(r["delta_left"],r["delta_right"],r["delta_top"],r["delta_bottom"])>0)
if rows_pass!=9: raise RuntimeError(("row gate",rows_pass))

# Strip private helper objects from report.
for row in rows:
    row.pop("_mask",None); row.pop("_glyph",None)

# Evidence.
src.save(out/"A128_SOURCE_READABLE.png")
clean.save(out/"A128_CLEAN_PLATE.png")
dec.save(out/"A128_FINAL_READABLE.png")
src_raw.save(out/"A128_SOURCE_RAW.png")
dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(out/"A128_FINAL_RAW.png")
Image.fromarray((source_mask.astype(np.uint8)*255),"L").save(out/"A128_SOURCE_TEXT_MASK.png")
Image.fromarray((target.astype(np.uint8)*255),"L").save(out/"A128_TARGET_MASK.png")
manual_clean.save(out/"A128_MANUAL_PSD_CLEAN_COMPOSITE.png")

def white(im):
    z=Image.new("RGBA",im.size,(235,235,235,255));z.alpha_composite(im);return z.convert("RGB")
def card(label,im,crop,scale=1):
    v=white(im).crop(crop)
    if scale!=1:v=v.resize((v.width*scale,v.height*scale),Image.Resampling.NEAREST)
    c=Image.new("RGB",(v.width,v.height+30),"white");c.paste(v,(0,30));ImageDraw.Draw(c).text((6,7),label,fill="black");return c
def contact(cards,path,maxsize=None):
    mw=max(c.width for c in cards);mh=sum(c.height+8 for c in cards)
    s=Image.new("RGB",(mw,mh),"white");y=0
    for c in cards:s.paste(c,(0,y));y+=c.height+8
    if maxsize:s.thumbnail(maxsize,Image.Resampling.LANCZOS)
    s.save(path,quality=97)

contact([card("SOURCE",src,(0,0,1200,820)),card("CLEAN PSD-LAYER",clean,(0,0,1200,820)),card("FINAL",dec,(0,0,1200,820))],
        out/"A128_MAIN_SOURCE_CLEAN_FINAL.jpg",(1800,2400))
contact([card("SOURCE RIGHT",src,(1260,0,2048,270)),card("CLEAN RIGHT",clean,(1260,0,2048,270)),card("FINAL RIGHT",dec,(1260,0,2048,270))],
        out/"A128_RIGHT_SOURCE_CLEAN_FINAL.jpg",(1800,1400))
contact([card("SOURCE RAW mirror_y",src_raw,(0,0,W,H)),card("FINAL RAW mirror_y",dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM),(0,0,W,H))],
        out/"A128_RAW_COMPARE.jpg",(1300,1200))
zoomcards=[]
for row in rows:
    x0,y0,x1,y1=row["source_bbox"];p=8;crop=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    zoomcards += [card(row["key"]+" SOURCE",src,crop,2),card(row["key"]+" CLEAN",clean,crop,2),card(row["key"]+" FINAL",dec,crop,2)]
contact(zoomcards,out/"A128_LABEL_ZOOM_CONTACT.jpg",(2800,6000))

report={
 "schema_version":1,"role":"A","run":run,"queue_index":queue_index,"asset":asset,
 "work_stolen_from_lane":"B",
 "work_steal_reason":"A odd shard exhausted; index62 was the oldest actionable manual reconstruction while B continued later even zoom-review production.",
 "source_provenance":{"dds_url":src_url,"dds_sha256":SOURCE_SHA,
   "psd_repo":"Sonic-TV/OR2006Sprites","psd_commit":psd_commit,"psd_path":psd_rel,
   "psd_bytes":psdp.stat().st_size,"psd_canvas":[psd.width,psd.height]},
 "translation":{"Diverge":"분기","Left":"좌측","Right":"우측","EASY":"쉬움","HARD":"어려움","physical_elements":9},
 "construction":{
   "source_text_mask":"exact alpha masks from nine visible PSD rasterized English label layers",
   "clean_plate":"exact-mask reconstruction: EASY/HARD OpenCV Telea r7 authoritative-source inpaint, Diverge/Left/Right PSD erase component, detached labels transparent; no pixel outside exact source masks changes",
   "render":"native 2048x1024 Noto Sans CJK KR Black; family colors sampled from source; shared Korean font size within Left/Right, main EASY/HARD, regular EASY/HARD and oblique EASY/HARD pairs",
   "oblique_transform":"27-degree source PSD shear reproduced as tan(27deg)"
 },
 "structure":{"width":W,"height":H,"format":"RGBA32","mipmaps":MIPS,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "rows":rows,
 "static_qa":{"elements_total":9,"bbox_size_positive_margin":"9/9 PASS",
   "clean_changed_outside_source_text_mask":clean_outside,"manual_clean_missing_alpha_by_main_label":manual_missing,"clean_component_by_key":clean_component_by_key,
   "changed_pixels_outside_exact_source_bboxes":outside,
   "alpha_changed_outside_exact_source_bboxes":alpha_out,
   "localized_pixels_outside_exact_source_bboxes":target_out,
   "localized_overlap_pixels":0,"dds_roundtrip":"PASS","status":"PASS"},
 "candidate_path":str(candidate.relative_to(repo)),"candidate_sha256":cand_sha,
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","runtime_validation":"UNTESTED",
 "status":"A128_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"A128_33491F83_REPORT.json"
rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A128_33491F83.json").write_text(json.dumps({
 "role":"A","run":run,"queue_index":queue_index,"asset":"33491F83","work_stolen_from_lane":"B",
 "source_sha256":SOURCE_SHA,"candidate_sha256":cand_sha,"psd_layered_source":True,
 "elements":9,"bbox_size_positive_margin":"9/9 PASS","changed_outside":outside,"alpha_outside":alpha_out,
 "report":str(rp.relative_to(repo)),"status":"WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({
 "run":run,"candidate_sha256":cand_sha,
 "rows":[{"key":r["key"],"source_bbox":r["source_bbox"],"localized_bbox":r["localized_bbox"],
          "font_size":r["font_size"],"shear":r["shear"],
          "margins":[r["delta_left"],r["delta_right"],r["delta_top"],r["delta_bottom"]]} for r in rows],
 "status":"A128_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
},ensure_ascii=False),flush=True)
