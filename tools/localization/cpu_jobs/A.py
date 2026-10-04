#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "A":
    raise SystemExit("This deterministic job must run in the GitHub-hosted localization CPU worker as role A.")

repo=Path.cwd()
run="20261004-A-PRODUCTION10"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
worker_out=repo/"localization/graphics/worker_results"
worker_out.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_congrats_cvt_Exst/455717B2_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"

work=Path("/tmp/outrun_A_production10")
work.mkdir(parents=True,exist_ok=True)
source=work/"455717B2_RELEASE_HD.dds"
atlas_json=work/"4x_455717B2_512x512_atlas.json"

UPSTREAM_REPO="Sonic-TV/OR2006Sprites"
UPSTREAM_COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
UPSTREAM_BLOB="92a3cb717afb6ea10aa76df23941353fd0a04148"
SOURCE_SHA="ce5d3610eac8945d76a559bb7f7201f9b1efb409c965bd20ed0a26164ed7f356"

urllib.request.urlretrieve(
 "https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+UPSTREAM_COMMIT+
 "/Release/spr_sprani_congrats_cvt_Exst/455717B2_512x512.dds",source)
urllib.request.urlretrieve(
 "https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+UPSTREAM_COMMIT+
 "/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_congrats_cvt_Exst/4x_455717B2_512x512_atlas.json",atlas_json)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if sha(source)!=SOURCE_SHA: raise RuntimeError(("HD source SHA mismatch",sha(source),SOURCE_SHA))

src_bytes=source.read_bytes()
if src_bytes[:4]!=b"DDS ": raise RuntimeError("not DDS")
h,w,pitch,depth,mips=struct.unpack_from("<5I",src_bytes,12)
pf=struct.unpack_from("<8I",src_bytes,76)
if (w,h,pitch,depth,mips)!=(2048,2048,8192,1,1):
    raise RuntimeError(("structure",(w,h,pitch,depth,mips)))
if pf[1:]!=(65,0,32,0xff,0xff00,0xff0000,0xff000000):
    raise RuntimeError(("pixel format",pf))
if len(src_bytes)!=128+w*h*4: raise RuntimeError(("bytes",len(src_bytes)))

raw_source=Image.frombytes("RGBA",(w,h),src_bytes[128:],"raw","RGBA")
source_readable=raw_source.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
W,H=w,h

atlas=json.loads(atlas_json.read_text(encoding="utf-8"))
regions={r["idx"]:r for r in atlas["regions"]}
bindings=[
 {"key":"continue","source":"CONTINUE","korean":"계속하기","idx":6,"style":"continue"},
 {"key":"perfect","source":"PERFECT!","korean":"완벽!","idx":5,"style":"green"},
 {"key":"congratulations","source":"CONGRATULATIONS!","korean":"축하합니다!","idx":4,"style":"gold"},
 {"key":"passed","source":"PASSED!","korean":"통과!","idx":1,"style":"green"},
]
for item in bindings:
    r=regions[item["idx"]]
    x,y,cw,ch=r["rect"]
    item["cell"]=[x,y,x+cw,y+ch]
    x1,y1,x2,y2=item["cell"]
    bb=source_readable.crop((x1,y1,x2,y2)).getchannel("A").getbbox()
    if not bb: raise RuntimeError(("empty source cell",item["key"]))
    item["original_bbox"]=[x1+bb[0],y1+bb[1],x1+bb[2],y1+bb[3]]

def count(m): return sum(m.histogram()[1:])
def binary_alpha(im): return im.getchannel("A").point(lambda v:255 if v else 0)
def changed_mask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)

source_text_mask=Image.new("L",(W,H),0)
for item in bindings:
    x1,y1,x2,y2=item["cell"]
    local=source_readable.crop((x1,y1,x2,y2)).getchannel("A").point(lambda v:255 if v else 0)
    prior=source_text_mask.crop((x1,y1,x2,y2))
    source_text_mask.paste(ImageChops.lighter(prior,local),(x1,y1))

allowed_bbox=Image.new("L",(W,H),0)
ad=ImageDraw.Draw(allowed_bbox)
for item in bindings:
    x1,y1,x2,y2=item["original_bbox"]
    ad.rectangle((x1,y1,x2-1,y2-1),fill=255)

source_visible=binary_alpha(source_readable)
protected_visible=ImageChops.multiply(source_visible,ImageOps.invert(allowed_bbox))
clean_protected=ImageChops.multiply(source_visible,ImageOps.invert(source_text_mask))

clean=source_readable.copy()
clean.paste(Image.new("RGBA",(W,H),(0,0,0,0)),(0,0),source_text_mask)

source_png=out/"455717B2_HD_SOURCE_READABLE.png"
clean_png=out/"455717B2_HD_CLEAN_PLATE.png"
source_readable.save(source_png)
clean.save(clean_png)
source_text_mask.save(out/"455717B2_HD_SOURCE_TEXT_MASK.png")
allowed_bbox.save(out/"455717B2_HD_ALLOWED_TEXT_REGION_MASK.png")
protected_visible.save(out/"455717B2_HD_PROTECTED_VISIBLE_MASK.png")
clean_protected.save(out/"455717B2_HD_CLEAN_PROTECTED_VISIBLE_MASK.png")

subprocess.run([
 "python3",str(validator),str(source_png),str(clean_png),
 str(out/"455717B2_HD_SOURCE_TEXT_MASK.png"),
 "--protected-mask",str(out/"455717B2_HD_CLEAN_PROTECTED_VISIBLE_MASK.png"),
 "--report",str(out/"A_PRODUCTION10_CLEAN_PLATE_VALIDATION.json")
],check=True)
clean_rep=json.loads((out/"A_PRODUCTION10_CLEAN_PLATE_VALIDATION.json").read_text())
if clean_rep["status"]!="PASS": raise RuntimeError("clean plate fail")

def resolve_font():
    for pat in ["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]:
        try: fp=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        except Exception: fp=""
        if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name: return fp
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    for pat in ["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]:
        fp=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        if fp and Path(fp).exists(): return fp
    raise RuntimeError("font unavailable")
fontpath=resolve_font()

def shear_mask(mask,shear_px):
    w,h=mask.size; s=max(0,int(round(shear_px)))
    if not s: return mask
    k=s/max(1,h-1)
    return mask.transform((w+s+4,h),Image.Transform.AFFINE,(1,k,-s,0,1,0),resample=Image.Resampling.BICUBIC)

def gradient(size,stops):
    w,h=size; im=Image.new("RGBA",size); px=im.load(); stops=sorted(stops)
    for y in range(h):
        t=0 if h<=1 else y/(h-1); i=0
        while i+1<len(stops) and t>stops[i+1][0]: i+=1
        if i+1>=len(stops): c=stops[-1][1]
        else:
            t0,c0=stops[i]; t1,c1=stops[i+1]; u=0 if t1==t0 else (t-t0)/(t1-t0)
            c=tuple(int(round(c0[k]+(c1[k]-c0[k])*u)) for k in range(4))
        for x in range(w): px[x,y]=c
    return im

styles={
 "continue":{"max_font":78,"outer":7,"inner":4,"shear":18,"shadow":(4,5),
             "outer_color":(250,250,246,255),"inner_color":(10,20,58,255),"shadow_color":(8,8,14,205),
             "stops":[(0,(255,250,205,255)),(.42,(255,229,95,255)),(1,(239,169,25,255))]},
 "green":{"max_font":176,"outer":12,"inner":7,"shear":34,"shadow":(7,9),
          "outer_color":(250,250,247,255),"inner_color":(17,23,29,255),"shadow_color":(10,10,14,215),
          "stops":[(0,(240,255,225,255)),(.25,(183,255,125,255)),(.58,(98,238,48,255)),(1,(41,170,8,255))]},
 "gold":{"max_font":168,"outer":12,"inner":7,"shear":34,"shadow":(7,9),
         "outer_color":(250,250,247,255),"inner_color":(28,28,34,255),"shadow_color":(10,10,14,215),
         "stops":[(0,(255,251,215,255)),(.24,(255,227,96,255)),(.58,(255,183,34,255)),(1,(222,126,10,255))]},
}

def render_style(text,ob,style):
    cfg=styles[style]; ox1,oy1,ox2,oy2=ob; aw,ah=ox2-ox1,oy2-oy1
    for fs in range(cfg["max_font"],35,-1):
        font=ImageFont.truetype(fontpath,fs); pad=28
        tb=font.getbbox(text,stroke_width=cfg["outer"])
        cw=(tb[2]-tb[0])+pad*2; ch=(tb[3]-tb[1])+pad*2
        masks={}
        for name,sw in [("outer",cfg["outer"]),("inner",cfg["inner"]),("fill",0)]:
            m=Image.new("L",(cw,ch),0); d=ImageDraw.Draw(m)
            d.text((pad-tb[0],pad-tb[1]),text,font=font,fill=255,stroke_width=sw,stroke_fill=255)
            masks[name]=shear_mask(m,cfg["shear"]*fs/max(1,cfg["max_font"]))
        union=ImageChops.lighter(masks["outer"],masks["inner"]); union=ImageChops.lighter(union,masks["fill"])
        bb=union.getbbox()
        if not bb: continue
        masks={k:v.crop(bb) for k,v in masks.items()}
        mw=max(v.width for v in masks.values()); mh=max(v.height for v in masks.values())
        sx,sy=cfg["shadow"]
        if mw+sx>aw-8 or mh+sy>ah-8: continue
        layer=Image.new("RGBA",(mw+sx,mh+sy),(0,0,0,0))
        sm=Image.new("L",layer.size,0); sm.paste(masks["outer"],(sx,sy))
        layer.paste(Image.new("RGBA",layer.size,cfg["shadow_color"]),(0,0),sm)
        for name,color in [("outer",cfg["outer_color"]),("inner",cfg["inner_color"])]:
            mm=Image.new("L",layer.size,0); mm.paste(masks[name],(0,0))
            layer.paste(Image.new("RGBA",layer.size,color),(0,0),mm)
        fm=Image.new("L",layer.size,0); fm.paste(masks["fill"],(0,0))
        layer.paste(gradient(layer.size,cfg["stops"]),(0,0),fm)
        abb=layer.getchannel("A").getbbox()
        if not abb: continue
        layer=layer.crop(abb)
        if layer.width>aw-8 or layer.height>ah-8: continue
        tx=ox1+(aw-layer.width)//2; ty=oy1+(ah-layer.height)//2
        if tx<=ox1+2: tx=ox1+3
        if ty<=oy1+2: ty=oy1+3
        if tx+layer.width>=ox2-2: tx=ox2-layer.width-3
        if ty+layer.height>=oy2-2: ty=oy2-layer.height-3
        return layer,(tx,ty),fs
    raise RuntimeError(("fit",text,ob,style))

final=clean.copy()
for item in bindings:
    layer,(tx,ty),fs=render_style(item["korean"],item["original_bbox"],item["style"])
    am=layer.getchannel("A").point(lambda v:255 if v else 0)
    final.paste(layer,(tx,ty),am)
    item["font_size"]=fs
    item["preencode_bbox"]=[tx,ty,tx+layer.width,ty+layer.height]

# Exact RGBA32 encode with canonical source header and raw mirror-Y orientation.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
cand_bytes=src_bytes[:128]+raw_final.tobytes("raw","RGBA")
candidate.write_bytes(cand_bytes)
candidate_sha=sha(candidate)
if candidate.read_bytes()[:128]!=src_bytes[:128]: raise RuntimeError("header changed")

cb=candidate.read_bytes()
decoded_raw=Image.frombytes("RGBA",(W,H),cb[128:],"raw","RGBA")
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
decoded_png=out/"455717B2_HD_FINAL_DECODED_READABLE.png"
decoded.save(decoded_png)
if ImageChops.difference(decoded,final).getbbox() is not None: raise RuntimeError("RGBA roundtrip mismatch")

subprocess.run([
 "python3",str(validator),str(source_png),str(decoded_png),
 str(out/"455717B2_HD_ALLOWED_TEXT_REGION_MASK.png"),
 "--protected-mask",str(out/"455717B2_HD_PROTECTED_VISIBLE_MASK.png"),
 "--report",str(out/"A_PRODUCTION10_FINAL_MASK_VALIDATION.json")
],check=True)
final_rep=json.loads((out/"A_PRODUCTION10_FINAL_MASK_VALIDATION.json").read_text())
if final_rep["status"]!="PASS": raise RuntimeError("final mask fail")

diff=changed_mask(source_readable,decoded)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed_bbox)))
alpha_delta=ImageChops.difference(source_readable.getchannel("A"),decoded.getchannel("A")).point(lambda v:255 if v else 0)
alpha_outside=count(ImageChops.multiply(alpha_delta,ImageOps.invert(allowed_bbox)))
protected_changed=count(ImageChops.multiply(diff,protected_visible))
clean_residue=count(ImageChops.multiply(binary_alpha(clean),source_text_mask))

rows=[]
for item in bindings:
    x1,y1,x2,y2=item["cell"]
    bb=decoded.crop((x1,y1,x2,y2)).getchannel("A").getbbox()
    loc=[x1+bb[0],y1+bb[1],x1+bb[2],y1+bb[3]] if bb else None
    ob=item["original_bbox"]
    ok=loc is not None and loc[0]>=ob[0] and loc[1]>=ob[1] and loc[2]<=ob[2] and loc[3]<=ob[3]
    positive=loc is not None and loc[0]>ob[0] and loc[1]>ob[1] and loc[2]<ob[2] and loc[3]<ob[3]
    raw_ob=[ob[0],H-ob[3],ob[2],H-ob[1]]
    raw_loc=[loc[0],H-loc[3],loc[2],H-loc[1]] if loc else None
    rows.append({
      "key":item["key"],"source":item["source"],"korean":item["korean"],"sprite_cell":item["cell"],
      "original_bbox":ob,"localized_bbox":loc,
      "delta_left":loc[0]-ob[0] if loc else None,"delta_right":ob[2]-loc[2] if loc else None,
      "delta_top":loc[1]-ob[1] if loc else None,"delta_bottom":ob[3]-loc[3] if loc else None,
      "containment":"PASS" if ok else "FAIL","positive_margin":"PASS" if positive else "EDGE_TOUCH_OR_FAIL",
      "raw_original_bbox":raw_ob,"raw_localized_bbox":raw_loc,
      "raw_delta_left":raw_loc[0]-raw_ob[0] if raw_loc else None,"raw_delta_right":raw_ob[2]-raw_loc[2] if raw_loc else None,
      "raw_delta_top":raw_loc[1]-raw_ob[1] if raw_loc else None,"raw_delta_bottom":raw_ob[3]-raw_loc[3] if raw_loc else None,
      "raw_containment":"PASS" if ok else "FAIL",
      "font":"Noto Sans CJK KR Black/Bold","font_size":item["font_size"],"style":item["style"],
      "rework_status":"A_PRODUCTION10_HD_REBUILD"
    })
all_bbox=all(x["containment"]=="PASS" and x["raw_containment"]=="PASS" for x in rows)
all_positive=all(x["positive_margin"]=="PASS" for x in rows)

def gray(im):
    bg=Image.new("RGBA",im.size,(100,100,100,255)); bg.alpha_composite(im); return bg.convert("RGB")

# Downsampled full evidence only; contact evidence retains 1:1 source pixels.
thumb=1024
sheet=Image.new("RGB",(thumb*3,thumb),(70,70,70))
sheet.paste(gray(source_readable).resize((thumb,thumb),Image.Resampling.LANCZOS),(0,0))
sheet.paste(gray(clean).resize((thumb,thumb),Image.Resampling.LANCZOS),(thumb,0))
sheet.paste(gray(decoded).resize((thumb,thumb),Image.Resampling.LANCZOS),(thumb*2,0))
sheet.save(out/"A_PRODUCTION10_HD_SOURCE_CLEAN_FINAL_GRAY.jpg",quality=94)
gray(decoded_raw).resize((1024,1024),Image.Resampling.LANCZOS).save(out/"A_PRODUCTION10_HD_FINAL_RAW_GRAY.jpg",quality=94)

contact=[]
label_font=ImageFont.truetype(fontpath,24)
for item in bindings:
    ob=item["original_bbox"]; margin=24
    x1=max(0,ob[0]-margin); y1=max(0,ob[1]-margin); x2=min(W,ob[2]+margin); y2=min(H,ob[3]+margin)
    a=gray(source_readable.crop((x1,y1,x2,y2))); b=gray(decoded.crop((x1,y1,x2,y2)))
    row=Image.new("RGB",(a.width+b.width+20,max(a.height,b.height)+34),(225,225,225))
    row.paste(a,(0,34)); row.paste(b,(a.width+20,34))
    ImageDraw.Draw(row).text((4,4),item["key"]+" SOURCE | FINAL",font=label_font,fill=(0,0,0))
    contact.append(row)
cw=max(x.width for x in contact); ch=sum(x.height for x in contact)+10*(len(contact)-1)
cs=Image.new("RGB",(cw,ch),(235,235,235)); yy=0
for x in contact: cs.paste(x,(0,yy)); yy+=x.height+10
cs.save(out/"A_PRODUCTION10_HD_ROW_CONTACT.jpg",quality=94)

status_ok=all_bbox and all_positive and clean_rep["status"]=="PASS" and final_rep["status"]=="PASS" and outside==0 and alpha_outside==0 and protected_changed==0 and clean_residue==0
report={
 "schema_version":1,"role":"A","run":run,"worker":os.environ.get("OUTRUN_CPU_WORKER","unknown"),
 "base_head":os.environ.get("GITHUB_SHA"),"index":43,"asset":asset_rel,
 "supersedes":{"run":"20261004-A-PRODUCTION09","candidate_sha256":"9dadee3c300bd0500940fcfe304bb640e7b458329210ce2b134c8ce06c65eac4","reason":"wrong stock-resolution fallback; C97 preflight exposed authoritative 2048x2048 Release DDS source"},
 "source_provenance":{"repository":UPSTREAM_REPO,"commit":UPSTREAM_COMMIT,"git_blob_sha1":UPSTREAM_BLOB,"sha256":SOURCE_SHA,"path":"Release/spr_sprani_congrats_cvt_Exst/455717B2_512x512.dds","classification":"authoritative available high-resolution source; filename suffix is stale, DDS header is 2048x2048 RGBA32"},
 "method":"exact 2048x2048 HD RGBA32 source -> 4x atlas text regions -> exact source-alpha text mask -> transparent clean plate -> native-HD source-family Korean render -> exact source-header RGBA32 raw mirror_y encode -> decoded static QA",
 "translations":[{"source":x["source"],"korean":x["korean"]} for x in bindings],
 "structure":{"dimensions":[W,H],"format":"RGBA32","pitch":pitch,"mipmaps":mips,"source_bytes":len(src_bytes),"candidate_bytes":len(cb),"header_128_exact":cb[:128]==src_bytes[:128],"raw_orientation":"mirror_y"},
 "source_sha256":SOURCE_SHA,"candidate_sha256":candidate_sha,"candidate_path":str(candidate.relative_to(repo)),
 "clean_plate_validator":clean_rep,"final_mask_validator":final_rep,
 "decoded_changes":{"changed_pixels_total":count(diff),"changed_pixels_outside_original_bboxes":outside,"alpha_changed_pixels_outside_original_bboxes":alpha_outside,"protected_visible_pixels_changed":protected_changed,"clean_plate_source_text_residue_pixels":clean_residue},
 "rows":rows,"all_4_readable_and_raw_bbox_pass":all_bbox,"all_4_positive_margin":all_positive,
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"UNTESTED",
 "status":"A_PRODUCTION10_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status_ok else "A_PRODUCTION10_WORKER_REWORK_REQUIRED"
}
(out/"A_PRODUCTION10_455717B2_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={
 "run":run,"asset":"455717B2","index":43,"source_sha256":SOURCE_SHA,"candidate_sha256":candidate_sha,
 "source_dimensions":[W,H],"format":"RGBA32","bbox_pass":"4/4" if all_bbox else "FAIL","positive_margin":"4/4" if all_positive else "FAIL",
 "clean_plate_validator":clean_rep["status"],"final_mask_validator":final_rep["status"],
 "changed_pixels_outside_original_bboxes":outside,"alpha_changed_pixels_outside_original_bboxes":alpha_outside,
 "protected_visible_pixels_changed":protected_changed,"clean_plate_source_text_residue_pixels":clean_residue,
 "worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":"localization/graphics/role_A/20261004-A-PRODUCTION10/A_PRODUCTION10_455717B2_REPORT.json"
}
(worker_out/"A_PRODUCTION10_455717B2.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status_ok: raise SystemExit(2)
