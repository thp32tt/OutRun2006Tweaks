#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps, ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "A":
    raise SystemExit("GitHub-hosted role A required")

repo = Path.cwd()
run = "20261004-A-PRODUCTION14"
out = repo / "localization/graphics/role_A" / run
out.mkdir(parents=True, exist_ok=True)
worker_out = repo / "localization/graphics/worker_results"
worker_out.mkdir(parents=True, exist_ok=True)

asset_rel = "textures/load/spr_sprani_etc_cvt_Exst/BF3EE5C6_512x512.dds"
candidate = repo / "localization/graphics/hd_candidates" / asset_rel
candidate.parent.mkdir(parents=True, exist_ok=True)
validator = repo / "tools/localization/validate_clean_plate.py"

work = Path("/tmp/outrun_A_prod14")
work.mkdir(parents=True, exist_ok=True)
source = work / "BF3EE5C6_HD.dds"
atlas = work / "4x_BF3EE5C6_512x512_atlas.json"

COMMIT = "3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
BLOB = "d6cde0c83a157e66e089867ccd616c289eb29c6e"
SOURCE_SHA = "b5c0a868add94395745af1827c21ddddd178439b5b4614fbadd8f0e4135a9887"

base = "https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/" + COMMIT
urllib.request.urlretrieve(base + "/Release/spr_sprani_etc_cvt_Exst/BF3EE5C6_512x512.dds", source)
urllib.request.urlretrieve(base + "/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_etc_cvt_Exst/4x_BF3EE5C6_512x512_atlas.json", atlas)

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

if sha(source) != SOURCE_SHA:
    raise RuntimeError(("source SHA", sha(source), SOURCE_SHA))

sb = source.read_bytes()
if sb[:4] != b"DDS ":
    raise RuntimeError("not DDS")
H, W, pitch, depth, mips = struct.unpack_from("<5I", sb, 12)
pf = struct.unpack_from("<8I", sb, 76)
if (W,H,pitch,depth,mips) != (2048,2048,8192,1,1):
    raise RuntimeError((W,H,pitch,depth,mips))
if pf[1:] != (65,0,32,0xff,0xff00,0xff0000,0xff000000):
    raise RuntimeError(("pixel format", pf))
if len(sb) != 128 + W*H*4:
    raise RuntimeError(("byte size", len(sb)))

raw_source = Image.frombytes("RGBA", (W,H), sb[128:], "raw", "RGBA")
source_readable = raw_source.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
aj = json.loads(atlas.read_text(encoding="utf-8"))
regions = {r["idx"]:r for r in aj["regions"]}
if len(regions) != 61:
    raise RuntimeError(("unexpected atlas region count", len(regions)))

# Exact localized target sprites. TUNED occurs twice, so 12 translated concepts = 13 sprite occurrences.
target_specs = [
    (7,  "rank_stage", "Rank for this stage", "이 스테이지 랭크", "yellow_navy"),
    (18, "normal",     "NORMAL",              "일반",             "green_navy"),
    (19, "tuned_a",    "TUNED",               "튜닝",             "red_navy"),
    (20, "tuned_b",    "TUNED",               "튜닝",             "red_navy"),
    (26, "top_ghost",  "TOP Ghost Car!!",     "최고 고스트 카!!", "white_red_glow"),
    (5,  "double",     "Double!",              "더블!",            "gold_navy"),
    (30, "strike",     "Strike!",              "스트라이크!",      "gold_navy"),
    (36, "goal",       "GOAL!",                "골!",              "goal_multicolor"),
    (37, "spare",      "Spare!",               "스페어!",          "gold_navy"),
    (3,  "shift_up",   "Shift up!!",           "시프트 업!!",      "yellow_white_navy"),
    (41, "rank",       "Rank",                 "랭크",             "white_lavender"),
    (50, "turkey",     "Turkey!",              "터키!",            "gold_navy"),
    (1,  "go",         "Go!",                  "출발!",            "go_peach"),
]

def count(mask):
    return sum(mask.histogram()[1:])

def binary_alpha(im):
    return im.getchannel("A").point(lambda v:255 if v else 0)

def changed_mask(a,b):
    d = ImageChops.difference(a,b)
    bands = d.split()
    m = bands[0]
    for z in bands[1:]:
        m = ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)

# Every selected sprite is text-only/effect-only. Determine the exact HD source effect bbox from its own cell.
targets=[]
for idx,key,src,kor,style in target_specs:
    rr=regions[idx]
    x,y,w,h=rr["rect"]
    cell=source_readable.crop((x,y,x+w,y+h))
    bb=cell.getchannel("A").getbbox()
    if not bb:
        raise RuntimeError(("empty target sprite",idx,key))
    gb=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    targets.append({
        "region_idx":idx,"key":key,"source":src,"korean":kor,"style":style,
        "cell_rect":[x,y,x+w,y+h],"original_bbox":gb
    })

# Sanity: target sprite cells must not overlap one another.
for i,a in enumerate(targets):
    ax1,ay1,ax2,ay2=a["cell_rect"]
    for b in targets[i+1:]:
        bx1,by1,bx2,by2=b["cell_rect"]
        if max(ax1,bx1)<min(ax2,bx2) and max(ay1,by1)<min(ay2,by2):
            raise RuntimeError(("target cells overlap",a["key"],b["key"]))

source_text_mask=Image.new("L",(W,H),0)
allowed_bbox=Image.new("L",(W,H),0)
abd=ImageDraw.Draw(allowed_bbox)
for t in targets:
    x1,y1,x2,y2=t["cell_rect"]
    cell_alpha=source_readable.crop((x1,y1,x2,y2)).getchannel("A").point(lambda v:255 if v else 0)
    source_text_mask.paste(ImageChops.lighter(source_text_mask.crop((x1,y1,x2,y2)),cell_alpha),(x1,y1))
    ox1,oy1,ox2,oy2=t["original_bbox"]
    abd.rectangle((ox1,oy1,ox2-1,oy2-1),fill=255)

source_visible=binary_alpha(source_readable)
protected_visible=ImageChops.multiply(source_visible,ImageOps.invert(allowed_bbox))
clean_protected=ImageChops.multiply(source_visible,ImageOps.invert(source_text_mask))
clean=source_readable.copy()
clean.paste(Image.new("RGBA",(W,H),(0,0,0,0)),(0,0),source_text_mask)

source_png=out/"BF3EE5C6_HD_SOURCE_READABLE.png"
clean_png=out/"BF3EE5C6_HD_CLEAN_PLATE.png"
source_readable.save(source_png)
clean.save(clean_png)
source_text_mask.save(out/"BF3EE5C6_HD_SOURCE_TEXT_MASK.png")
allowed_bbox.save(out/"BF3EE5C6_HD_ALLOWED_TEXT_REGION_MASK.png")
protected_visible.save(out/"BF3EE5C6_HD_PROTECTED_VISIBLE_MASK.png")
clean_protected.save(out/"BF3EE5C6_HD_CLEAN_PROTECTED_VISIBLE_MASK.png")

subprocess.run([
    "python3",str(validator),str(source_png),str(clean_png),
    str(out/"BF3EE5C6_HD_SOURCE_TEXT_MASK.png"),
    "--protected-mask",str(out/"BF3EE5C6_HD_CLEAN_PROTECTED_VISIBLE_MASK.png"),
    "--report",str(out/"A_PRODUCTION14_CLEAN_PLATE_VALIDATION.json")
],check=True)
clean_rep=json.loads((out/"A_PRODUCTION14_CLEAN_PLATE_VALIDATION.json").read_text())
if clean_rep["status"]!="PASS":
    raise RuntimeError("clean validator failed")

def resolve_font():
    pats=["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]
    for pat in pats:
        try:
            fp=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        except Exception:
            fp=""
        if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name:
            return fp
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    for pat in pats:
        fp=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        if fp and Path(fp).exists():
            return fp
    raise RuntimeError("Noto CJK Korean unavailable")
FONT=resolve_font()

styles = {
    "gold_navy": {
        "top":(255,248,207,255),"bottom":(218,171,76,255),
        "inner":(245,225,169,255),"outer":(16,28,72,255),"shadow":(7,13,35,210),
        "inner_ratio":0.030,"outer_ratio":0.065,"shadow_ratio":0.070,"shear":0.20,"glow":None
    },
    "yellow_white_navy": {
        "top":(255,239,76,255),"bottom":(255,176,19,255),
        "inner":(252,252,246,255),"outer":(27,42,91,255),"shadow":(11,17,39,210),
        "inner_ratio":0.025,"outer_ratio":0.060,"shadow_ratio":0.060,"shear":0.18,"glow":None
    },
    "yellow_navy": {
        "top":(255,244,72,255),"bottom":(255,199,22,255),
        "inner":(255,255,255,255),"outer":(13,26,75,255),"shadow":(7,12,34,220),
        "inner_ratio":0.025,"outer_ratio":0.070,"shadow_ratio":0.060,"shear":0.14,"glow":None
    },
    "green_navy": {
        "top":(205,255,205,255),"bottom":(43,179,78,255),
        "inner":None,"outer":(11,25,71,255),"shadow":(7,12,31,210),
        "inner_ratio":0.0,"outer_ratio":0.085,"shadow_ratio":0.055,"shear":0.15,"glow":None
    },
    "red_navy": {
        "top":(255,237,237,255),"bottom":(214,52,69,255),
        "inner":None,"outer":(12,25,72,255),"shadow":(8,12,30,220),
        "inner_ratio":0.0,"outer_ratio":0.085,"shadow_ratio":0.055,"shear":0.15,"glow":None
    },
    "white_red_glow": {
        "top":(255,255,255,255),"bottom":(255,255,255,255),
        "inner":(200,28,35,255),"outer":(255,255,255,255),"shadow":(191,21,28,240),
        "inner_ratio":0.060,"outer_ratio":0.095,"shadow_ratio":0.0,"shear":0.12,"glow":(205,24,31,170)
    },
    "goal_multicolor": {
        "top":(255,224,82,255),"bottom":(151,15,65,255),
        "inner":(255,252,232,255),"outer":(21,29,73,255),"shadow":(7,11,30,220),
        "inner_ratio":0.030,"outer_ratio":0.075,"shadow_ratio":0.065,"shear":0.15,"glow":None
    },
    "white_lavender": {
        "top":(255,255,255,255),"bottom":(223,215,242,255),
        "inner":(70,69,82,255),"outer":(244,244,246,255),"shadow":(16,17,22,220),
        "inner_ratio":0.030,"outer_ratio":0.070,"shadow_ratio":0.085,"shear":0.16,"glow":None
    },
    "go_peach": {
        "top":(255,255,255,255),"bottom":(255,184,123,255),
        "inner":(179,168,193,255),"outer":(242,238,246,255),"shadow":(21,20,28,230),
        "inner_ratio":0.025,"outer_ratio":0.065,"shadow_ratio":0.065,"shear":0.14,"glow":None
    },
}

def make_gradient(size, top, bottom):
    w,h=size
    im=Image.new("RGBA",size)
    pix=im.load()
    for yy in range(h):
        f=0 if h<=1 else yy/(h-1)
        col=tuple(round(top[i]*(1-f)+bottom[i]*f) for i in range(4))
        for xx in range(w):
            pix[xx,yy]=col
    return im

def text_mask(text,font,stroke=0):
    d=ImageDraw.Draw(Image.new("L",(8,8),0))
    bb=d.textbbox((0,0),text,font=font,stroke_width=stroke)
    pad=stroke+8
    w=max(1,bb[2]-bb[0]+pad*2); h=max(1,bb[3]-bb[1]+pad*2)
    m=Image.new("L",(w,h),0)
    md=ImageDraw.Draw(m)
    md.text((pad-bb[0],pad-bb[1]),text,font=font,fill=255,stroke_width=stroke,stroke_fill=255)
    box=m.getbbox()
    return m.crop(box) if box else m

def shear_mask(mask,shear):
    if not shear:
        return mask
    extra=max(1,int(abs(shear)*mask.height)+4)
    canvas=Image.new("L",(mask.width+extra*2,mask.height),0)
    canvas.paste(mask,(extra,0))
    # x_out = x_in + shear*(h-y), making a right-leaning italic.
    coeff=(1,-shear,shear*canvas.height,0,1,0)
    outm=canvas.transform(canvas.size,Image.Transform.AFFINE,coeff,resample=Image.Resampling.BICUBIC)
    bb=outm.getbbox()
    return outm.crop(bb) if bb else outm

def offset_mask(mask,dx,dy):
    outm=Image.new("L",mask.size,0)
    x=max(0,dx); y=max(0,dy)
    src=(max(0,-dx),max(0,-dy),mask.width-max(0,dx),mask.height-max(0,dy))
    if src[2]>src[0] and src[3]>src[1]:
        outm.paste(mask.crop(src),(x,y))
    return outm

def render_style(text, style_name, box_w, box_h):
    st=styles[style_name]
    max_fs=max(18,int(box_h*1.20))
    for fs in range(max_fs,13,-1):
        font=ImageFont.truetype(FONT,fs)
        outer=max(1,round(fs*st["outer_ratio"]))
        inner=max(0,round(fs*st["inner_ratio"]))
        shadow=max(0,round(fs*st["shadow_ratio"]))
        base=text_mask(text,font,0)
        inner_m=text_mask(text,font,inner) if inner else base.copy()
        outer_m=text_mask(text,font,outer)
        # Normalize canvases by rendering again into one sufficiently large canvas.
        d=ImageDraw.Draw(Image.new("L",(8,8),0))
        bb=d.textbbox((0,0),text,font=font,stroke_width=max(outer,inner))
        pad=max(outer,inner)+shadow+12
        cw=max(1,bb[2]-bb[0]+pad*2)
        ch=max(1,bb[3]-bb[1]+pad*2)
        def drawm(sw):
            m=Image.new("L",(cw,ch),0); md=ImageDraw.Draw(m)
            md.text((pad-bb[0],pad-bb[1]),text,font=font,fill=255,stroke_width=sw,stroke_fill=255)
            return m
        fill_m=drawm(0); inner_m=drawm(inner); outer_m=drawm(outer)
        if st["shear"]:
            fill_m=shear_mask(fill_m,st["shear"])
            inner_m=shear_mask(inner_m,st["shear"])
            outer_m=shear_mask(outer_m,st["shear"])
            maxw=max(fill_m.width,inner_m.width,outer_m.width); maxh=max(fill_m.height,inner_m.height,outer_m.height)
            def center(m):
                c=Image.new("L",(maxw,maxh),0); c.paste(m,((maxw-m.width)//2,(maxh-m.height)//2)); return c
            fill_m,inner_m,outer_m=center(fill_m),center(inner_m),center(outer_m)
        cw,ch=outer_m.size
        # Extra canvas for shadow/glow.
        extra=max(8,shadow+12)
        def padmask(m):
            c=Image.new("L",(cw+extra*2,ch+extra*2),0); c.paste(m,(extra,extra)); return c
        fill_m,inner_m,outer_m=padmask(fill_m),padmask(inner_m),padmask(outer_m)
        rgba=Image.new("RGBA",outer_m.size,(0,0,0,0))
        if st["glow"]:
            glow=outer_m.filter(ImageFilter.GaussianBlur(max(2,round(fs*0.10))))
            gcol=Image.new("RGBA",rgba.size,st["glow"]); rgba.alpha_composite(Image.composite(gcol,Image.new("RGBA",rgba.size,(0,0,0,0)),glow))
        if shadow:
            sh=offset_mask(outer_m,shadow,shadow)
            scol=Image.new("RGBA",rgba.size,st["shadow"]); rgba.alpha_composite(Image.composite(scol,Image.new("RGBA",rgba.size,(0,0,0,0)),sh))
        ocol=Image.new("RGBA",rgba.size,st["outer"]); rgba.alpha_composite(Image.composite(ocol,Image.new("RGBA",rgba.size,(0,0,0,0)),outer_m))
        if inner:
            icol=Image.new("RGBA",rgba.size,st["inner"]); rgba.alpha_composite(Image.composite(icol,Image.new("RGBA",rgba.size,(0,0,0,0)),inner_m))
        grad=make_gradient(rgba.size,st["top"],st["bottom"]); rgba.alpha_composite(Image.composite(grad,Image.new("RGBA",rgba.size,(0,0,0,0)),fill_m))
        bbox=rgba.getchannel("A").getbbox()
        if not bbox:
            continue
        rgba=rgba.crop(bbox)
        # strict positive margins; reduce if even one edge would touch.
        if rgba.width<=box_w-4 and rgba.height<=box_h-4:
            return rgba,fs,outer,inner,shadow
    raise RuntimeError(("fit failed",text,style_name,box_w,box_h))

final=clean.copy()
for t in targets:
    ox1,oy1,ox2,oy2=t["original_bbox"]
    aw,ah=ox2-ox1,oy2-oy1
    glyph,fs,outer,inner,shadow=render_style(t["korean"],t["style"],aw,ah)
    tx=ox1+(aw-glyph.width)//2
    ty=oy1+(ah-glyph.height)//2
    if tx<=ox1: tx=ox1+1
    if ty<=oy1: ty=oy1+1
    if tx+glyph.width>=ox2: tx=ox2-glyph.width-1
    if ty+glyph.height>=oy2: ty=oy2-glyph.height-1
    final.alpha_composite(glyph,(tx,ty))
    t["font_size"]=fs
    t["stroke_outer"]=outer
    t["stroke_inner"]=inner
    t["shadow_px"]=shadow
    t["preencode_bbox"]=[tx,ty,tx+glyph.width,ty+glyph.height]

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
cb=sb[:128]+raw_final.tobytes("raw","RGBA")
candidate.write_bytes(cb)
candidate_sha=sha(candidate)
if cb[:128]!=sb[:128]:
    raise RuntimeError("header changed")

decoded_raw=Image.frombytes("RGBA",(W,H),cb[128:],"raw","RGBA")
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
decoded_png=out/"BF3EE5C6_HD_FINAL_DECODED_READABLE.png"
decoded.save(decoded_png)
if ImageChops.difference(decoded,final).getbbox() is not None:
    raise RuntimeError("RGBA roundtrip mismatch")

subprocess.run([
    "python3",str(validator),str(source_png),str(decoded_png),
    str(out/"BF3EE5C6_HD_ALLOWED_TEXT_REGION_MASK.png"),
    "--protected-mask",str(out/"BF3EE5C6_HD_PROTECTED_VISIBLE_MASK.png"),
    "--report",str(out/"A_PRODUCTION14_FINAL_MASK_VALIDATION.json")
],check=True)
final_rep=json.loads((out/"A_PRODUCTION14_FINAL_MASK_VALIDATION.json").read_text())
if final_rep["status"]!="PASS":
    raise RuntimeError("final validator failed")

diff=changed_mask(source_readable,decoded)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed_bbox)))
alpha_delta=ImageChops.difference(source_readable.getchannel("A"),decoded.getchannel("A")).point(lambda v:255 if v else 0)
alpha_outside=count(ImageChops.multiply(alpha_delta,ImageOps.invert(allowed_bbox)))
protected_changed=count(ImageChops.multiply(diff,protected_visible))
clean_residue=count(ImageChops.multiply(binary_alpha(clean),source_text_mask))

rows=[]
for t in targets:
    ob=t["original_bbox"]
    cell=t["cell_rect"]
    # localized bbox is exact nonzero candidate alpha within the original permitted bbox
    bb=decoded.crop(tuple(ob)).getchannel("A").getbbox()
    loc=[ob[0]+bb[0],ob[1]+bb[1],ob[0]+bb[2],ob[1]+bb[3]] if bb else None
    ok=loc is not None and loc[0]>=ob[0] and loc[1]>=ob[1] and loc[2]<=ob[2] and loc[3]<=ob[3]
    size_ok=loc is not None and (loc[2]-loc[0])<=(ob[2]-ob[0]) and (loc[3]-loc[1])<=(ob[3]-ob[1])
    positive=loc is not None and loc[0]>ob[0] and loc[1]>ob[1] and loc[2]<ob[2] and loc[3]<ob[3]
    raw_ob=[ob[0],H-ob[3],ob[2],H-ob[1]]
    raw_loc=[loc[0],H-loc[3],loc[2],H-loc[1]] if loc else None
    rows.append({
        "key":t["key"],"region_idx":t["region_idx"],"source":t["source"],"korean":t["korean"],"style":t["style"],
        "cell_rect":cell,"original_bbox":ob,"localized_bbox":loc,
        "source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],
        "localized_width":loc[2]-loc[0] if loc else None,"localized_height":loc[3]-loc[1] if loc else None,
        "delta_left":loc[0]-ob[0] if loc else None,"delta_right":ob[2]-loc[2] if loc else None,
        "delta_top":loc[1]-ob[1] if loc else None,"delta_bottom":ob[3]-loc[3] if loc else None,
        "containment":"PASS" if ok else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL",
        "positive_margin":"PASS" if positive else "EDGE_TOUCH_OR_FAIL",
        "raw_original_bbox":raw_ob,"raw_localized_bbox":raw_loc,
        "raw_containment":"PASS" if ok else "FAIL",
        "font":"Noto Sans CJK KR Black/Bold","font_size":t["font_size"],
        "stroke_outer":t["stroke_outer"],"stroke_inner":t["stroke_inner"],"shadow_px":t["shadow_px"],
        "rework_status":"A_PRODUCTION14_NEW_HD_CANDIDATE"
    })

all_bbox=all(r["containment"]=="PASS" and r["raw_containment"]=="PASS" for r in rows)
all_size=all(r["size_ceiling"]=="PASS" for r in rows)
all_positive=all(r["positive_margin"]=="PASS" for r in rows)

def gray(im):
    bg=Image.new("RGBA",im.size,(96,96,96,255))
    bg.alpha_composite(im)
    return bg.convert("RGB")

thumb=(1024,1024)
sheet=Image.new("RGB",(thumb[0],thumb[1]*3),(80,80,80))
sheet.paste(gray(source_readable).resize(thumb,Image.Resampling.LANCZOS),(0,0))
sheet.paste(gray(clean).resize(thumb,Image.Resampling.LANCZOS),(0,thumb[1]))
sheet.paste(gray(decoded).resize(thumb,Image.Resampling.LANCZOS),(0,thumb[1]*2))
sheet.save(out/"A_PRODUCTION14_SOURCE_CLEAN_FINAL_GRAY.jpg",quality=94)
gray(decoded_raw).resize(thumb,Image.Resampling.LANCZOS).save(out/"A_PRODUCTION14_FINAL_RAW_GRAY.jpg",quality=94)

contact=[]
label_font=ImageFont.truetype(FONT,20)
for t in targets:
    ob=t["original_bbox"]; m=12
    x1=max(0,ob[0]-m);y1=max(0,ob[1]-m);x2=min(W,ob[2]+m);y2=min(H,ob[3]+m)
    a=gray(source_readable.crop((x1,y1,x2,y2)))
    b=gray(decoded.crop((x1,y1,x2,y2)))
    maxw=900
    if a.width+b.width+16>maxw:
        scale=(maxw-16)/(a.width+b.width)
        a=a.resize((max(1,int(a.width*scale)),max(1,int(a.height*scale))),Image.Resampling.LANCZOS)
        b=b.resize((max(1,int(b.width*scale)),max(1,int(b.height*scale))),Image.Resampling.LANCZOS)
    row=Image.new("RGB",(a.width+b.width+16,max(a.height,b.height)+28),(225,225,225))
    row.paste(a,(0,28)); row.paste(b,(a.width+16,28))
    ImageDraw.Draw(row).text((3,3),t["key"]+" SOURCE | FINAL",font=label_font,fill=(0,0,0))
    contact.append(row)
cw=max(x.width for x in contact); ch=sum(x.height for x in contact)+4*(len(contact)-1)
cs=Image.new("RGB",(cw,ch),(235,235,235)); yy=0
for x in contact:
    cs.paste(x,(0,yy)); yy+=x.height+4
cs.save(out/"A_PRODUCTION14_ROW_CONTACT.jpg",quality=94)

status_ok=(
    clean_rep["status"]=="PASS" and final_rep["status"]=="PASS"
    and all_bbox and all_size and all_positive
    and outside==0 and alpha_outside==0 and protected_changed==0 and clean_residue==0
)
report={
    "schema_version":1,"role":"A","run":run,"worker":os.environ.get("OUTRUN_CPU_WORKER"),
    "base_head":os.environ.get("GITHUB_SHA"),"index":49,"asset":asset_rel,
    "source_provenance":{
        "repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":BLOB,
        "sha256":SOURCE_SHA,"path":"Release/spr_sprani_etc_cvt_Exst/BF3EE5C6_512x512.dds",
        "classification":"authoritative high-resolution source; stale filename suffix, DDS header 2048x2048 RGBA32"
    },
    "source_sha256":SOURCE_SHA,"candidate_sha256":candidate_sha,
    "candidate_path":str(candidate.relative_to(repo)),
    "structure":{"dimensions":[W,H],"format":"RGBA32","pitch":pitch,"mipmaps":mips,"bytes":len(sb),"header_128_exact":True,"raw_orientation":"mirror_y"},
    "translation_policy":{
        "translated_concepts":12,"localized_sprite_occurrences":13,
        "translations":[{"source":s,"korean":k} for _,_,s,k,_ in target_specs],
        "protected_non_target_artwork":"all non-target sprite cells preserved pixel-identical"
    },
    "clean_plate_validator":clean_rep,"final_mask_validator":final_rep,
    "decoded_changes":{
        "changed_pixels_total":count(diff),"changed_pixels_outside_original_bboxes":outside,
        "alpha_changed_pixels_outside_original_bboxes":alpha_outside,
        "protected_visible_pixels_changed":protected_changed,"clean_plate_source_text_residue_pixels":clean_residue
    },
    "rows":rows,"all_13_readable_and_raw_bbox_pass":all_bbox,"all_13_size_ceiling_pass":all_size,"all_13_positive_margin":all_positive,
    "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"UNTESTED",
    "status":"A_PRODUCTION14_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status_ok else "A_PRODUCTION14_WORKER_REWORK_REQUIRED"
}
(out/"A_PRODUCTION14_BF3EE5C6_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={
    "run":run,"asset":"BF3EE5C6","index":49,"source_sha256":SOURCE_SHA,"candidate_sha256":candidate_sha,
    "source_dimensions":[W,H],"format":"RGBA32","target_occurrences":13,"translated_concepts":12,
    "bbox_pass":"13/13" if all_bbox else "FAIL","size_ceiling":"13/13" if all_size else "FAIL",
    "positive_margin":"13/13" if all_positive else "FAIL",
    "clean_plate_validator":clean_rep["status"],"final_mask_validator":final_rep["status"],
    "changed_pixels_outside_original_bboxes":outside,"alpha_changed_pixels_outside_original_bboxes":alpha_outside,
    "protected_visible_pixels_changed":protected_changed,"clean_plate_source_text_residue_pixels":clean_residue,
    "worker_status":report["status"],"runtime_validation":"UNTESTED",
    "report":"localization/graphics/role_A/20261004-A-PRODUCTION14/A_PRODUCTION14_BF3EE5C6_REPORT.json"
}
(worker_out/"A_PRODUCTION14_BF3EE5C6.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status_ok:
    raise SystemExit(2)
