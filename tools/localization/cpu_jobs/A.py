#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,shutil
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd(); run="20261005-A-PRODUCTION17"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_sprani_game_cvt_Exst/2EA557B4_512x64.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel; candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"
work=Path("/tmp/outrun_A_prod17"); work.mkdir(parents=True,exist_ok=True)
source=work/"2EA557B4_HD.dds"; atlas=work/"4x_2EA557B4_512x64_atlas.json"
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_SHA="b2d5b03a8e6cc56fcb60c31f32a485854dd7ea41ed10c7b10ba185625d07a685"
BLOB="bbf53949c7d9f1dc4949e661caeeaf19fe667d79"
urllib.request.urlretrieve("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT+"/Release/spr_sprani_game_cvt_Exst/2EA557B4_512x64.dds",source)
urllib.request.urlretrieve("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_game_cvt_Exst/4x_2EA557B4_512x64_atlas.json",atlas)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def count(m): return sum(m.histogram()[1:])
def balpha(im): return im.getchannel("A").point(lambda v:255 if v else 0)
def dmask(a,b):
    d=ImageChops.difference(a,b); z=d.split(); m=z[0]
    for q in z[1:]: m=ImageChops.lighter(m,q)
    return m.point(lambda v:255 if v else 0)

if sha(source)!=SOURCE_SHA: raise RuntimeError(("source SHA",sha(source),SOURCE_SHA))
sb=source.read_bytes()
if sb[:4]!=b"DDS " or sb[84:88]!=b"DXT5": raise RuntimeError("not DXT5")
H,W=struct.unpack_from("<2I",sb,12)
if (W,H)!=(2048,256) or len(sb)!=524416: raise RuntimeError((W,H,len(sb)))
raw=Image.open(source).convert("RGBA"); readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
a=json.loads(atlas.read_text(encoding="utf-8")); rr=a["regions"][0]; x,y,cw,ch=rr["rect"]; cell=[x,y,x+cw,y+ch]
bb=readable.crop(tuple(cell)).getchannel("A").getbbox()
if not bb: raise RuntimeError("empty source text")
ob=[cell[0]+bb[0],cell[1]+bb[1],cell[0]+bb[2],cell[1]+bb[3]]
if ob!=[1,105,1090,248]: raise RuntimeError(("unexpected source bbox",ob))
raw_ob=[ob[0],H-ob[3],ob[2],H-ob[1]]

srcmask=Image.new("L",(W,H),0)
srcmask.paste(readable.crop(tuple(cell)).getchannel("A").point(lambda v:255 if v else 0),(cell[0],cell[1]))
allowed=Image.new("L",(W,H),0); ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
protected=ImageChops.multiply(balpha(readable),ImageOps.invert(allowed))
clean_protected=ImageChops.multiply(balpha(readable),ImageOps.invert(srcmask))
clean=readable.copy(); clean.paste(Image.new("RGBA",(W,H),(0,0,0,0)),(0,0),srcmask)

sp=out/"2EA557B4_HD_SOURCE_READABLE.png"; cp=out/"2EA557B4_HD_CLEAN_PLATE.png"
spm=out/"2EA557B4_HD_SOURCE_TEXT_MASK.png"; ap=out/"2EA557B4_HD_ALLOWED_TEXT_REGION_MASK.png"
pp=out/"2EA557B4_HD_PROTECTED_VISIBLE_MASK.png"; cpp=out/"2EA557B4_HD_CLEAN_PROTECTED_VISIBLE_MASK.png"
readable.save(sp); clean.save(cp); srcmask.save(spm); allowed.save(ap); protected.save(pp); clean_protected.save(cpp)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(spm),"--protected-mask",str(cpp),"--report",str(out/"A_PRODUCTION17_CLEAN_PLATE_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"A_PRODUCTION17_CLEAN_PLATE_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean fail",cleanrep))

def fontpath():
    for pat in ["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]:
        try: p=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        except Exception: p=""
        if p and Path(p).exists() and "NotoSansCJK" in Path(p).name: return p
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    p=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
    if not p: raise RuntimeError("font")
    return p
FONT=fontpath()

def shear(m,s):
    w,h=m.size; k=s/max(1,h-1)
    return m.transform((w+s+4,h),Image.Transform.AFFINE,(1,k,-s,0,1,0),resample=Image.Resampling.BICUBIC)
def grad(size):
    w,h=size; im=Image.new("RGBA",size); px=im.load()
    for yy in range(h):
        t=yy/max(1,h-1)
        if t<.45:
            u=t/.45; c=tuple(int(round(a+(b-a)*u)) for a,b in zip((250,252,255,255),(203,239,255,255)))
        else:
            u=(t-.45)/.55; c=tuple(int(round(a+(b-a)*u)) for a,b in zip((203,239,255,255),(84,181,245,255)))
        for xx in range(w): px[xx,yy]=c
    return im

def render(text):
    aw,ah=ob[2]-ob[0],ob[3]-ob[1]
    for fs in range(min(142,ah-10),30,-1):
        f=ImageFont.truetype(FONT,fs); ow=max(5,fs//14); iw=max(3,fs//24); pad=24
        tb=f.getbbox(text,stroke_width=ow); cw=tb[2]-tb[0]+pad*2; ch=tb[3]-tb[1]+pad*2
        masks={}
        for name,sw in [("outer",ow),("inner",iw),("fill",0)]:
            m=Image.new("L",(cw,ch),0); d=ImageDraw.Draw(m)
            d.text((pad-tb[0],pad-tb[1]),text,font=f,fill=255,stroke_width=sw,stroke_fill=255)
            masks[name]=shear(m,max(8,fs//5))
        union=ImageChops.lighter(masks["outer"],masks["inner"]); union=ImageChops.lighter(union,masks["fill"])
        ub=union.getbbox()
        if not ub: continue
        masks={k:v.crop(ub) for k,v in masks.items()}
        mw=max(v.width for v in masks.values()); mh=max(v.height for v in masks.values())
        sx,sy=max(3,fs//28),max(4,fs//24)
        if mw+sx>aw-16 or mh+sy>ah-16: continue
        layer=Image.new("RGBA",(mw+sx,mh+sy),(0,0,0,0))
        sm=Image.new("L",layer.size,0); sm.paste(masks["outer"],(sx,sy))
        layer.paste(Image.new("RGBA",layer.size,(5,8,18,210)),(0,0),sm)
        mm=Image.new("L",layer.size,0); mm.paste(masks["outer"],(0,0))
        layer.paste(Image.new("RGBA",layer.size,(245,248,252,255)),(0,0),mm)
        mm=Image.new("L",layer.size,0); mm.paste(masks["inner"],(0,0))
        layer.paste(Image.new("RGBA",layer.size,(17,35,82,255)),(0,0),mm)
        fm=Image.new("L",layer.size,0); fm.paste(masks["fill"],(0,0))
        layer.paste(grad(layer.size),(0,0),fm)
        lb=layer.getchannel("A").getbbox(); layer=layer.crop(lb)
        if layer.width<=aw-16 and layer.height<=ah-16:
            tx=ob[0]+(aw-layer.width)//2; ty=ob[1]+(ah-layer.height)//2
            if tx>=ob[0]+4 and ty>=ob[1]+4 and tx+layer.width<=ob[2]-4 and ty+layer.height<=ob[3]-4:
                return layer,(tx,ty),fs
    raise RuntimeError("fit")

layer,(tx,ty),fs=render("다음 라운드")
lm=layer.getchannel("A").point(lambda v:255 if v else 0)
final=clean.copy(); final.paste(layer,(tx,ty),lm)
ideal_loc=[tx,ty,tx+layer.width,ty+layer.height]

# Encode a full target DXT5 image, then splice only blocks fully contained by the exact raw bbox.
# Boundary blocks retain source endpoints/color/index data; only alpha indices for in-bbox pixels
# are changed to an existing source zero-alpha index. This guarantees decoded pixels outside the
# exact bbox remain bit-for-bit identical while erasing edge source glyphs.
exe=shutil.which("convert") or shutil.which("magick")
if not exe:
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","imagemagick"],check=True)
    exe=shutil.which("convert") or shutil.which("magick")
rawfinal=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
png=work/"raw_final.png"; encp=work/"enc_final.dds"; rawfinal.save(png)
cmd=[exe]+(["convert"] if Path(exe).name=="magick" else [])+[str(png),"-define","dds:compression=dxt5","-define","dds:mipmaps=0",str(encp)]
subprocess.run(cmd,check=True); enc=encp.read_bytes()
if len(enc)!=len(sb) or enc[84:88]!=b"DXT5": raise RuntimeError("encode structure")

def get_aidx(block,i):
    bits=int.from_bytes(block[2:8],"little")
    return (bits>>(3*i))&7
def set_aidx(block,i,v):
    bits=int.from_bytes(block[2:8],"little")
    bits=(bits & ~(7<<(3*i))) | ((v&7)<<(3*i))
    block[2:8]=bits.to_bytes(6,"little")

bw=W//4; outb=bytearray(sb); partial_blocks=0; full_blocks=0; boundary_pixels_cleared=0
rx1,ry1,rx2,ry2=raw_ob
for by in range(ry1//4,(ry2+3)//4):
    for bx in range(rx1//4,(rx2+3)//4):
        x0,y0=bx*4,by*4; x4,y4=x0+4,y0+4
        p=128+(by*bw+bx)*16
        fully=(x0>=rx1 and y0>=ry1 and x4<=rx2 and y4<=ry2)
        if fully:
            outb[p:p+16]=enc[p:p+16]; full_blocks+=1
            continue
        partial_blocks+=1
        block=bytearray(sb[p:p+16])
        # Find a source alpha index from any outside-bbox pixel whose decoded alpha is exactly 0.
        zidx=None
        for py in range(4):
            for px in range(4):
                gx,gy=x0+px,y0+py
                outside=not (rx1<=gx<rx2 and ry1<=gy<ry2)
                if outside and raw.getpixel((gx,gy))[3]==0:
                    zidx=get_aidx(block,py*4+px); break
            if zidx is not None: break
        if zidx is None: raise RuntimeError(("no exact-zero source alpha index in partial block",bx,by))
        # Korean render is guaranteed at least 4 px from the exact source bbox, so partial
        # blocks contain cleanup only. Clear every in-bbox alpha sample to the source zero index.
        for py in range(4):
            for px in range(4):
                gx,gy=x0+px,y0+py
                inside=(rx1<=gx<rx2 and ry1<=gy<ry2)
                if inside:
                    # Assert ideal final is transparent at all partial-block in-bbox pixels.
                    if rawfinal.getpixel((gx,gy))[3]!=0:
                        raise RuntimeError(("localized render reached partial DXT block",gx,gy,rawfinal.getpixel((gx,gy))[3]))
                    set_aidx(block,py*4+px,zidx); boundary_pixels_cleared+=1
        outb[p:p+16]=block

candidate.write_bytes(outb); csha=sha(candidate)
if candidate.read_bytes()[:128]!=sb[:128]: raise RuntimeError("header")
dr=Image.open(candidate).convert("RGBA"); dec=dr.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
dp=out/"2EA557B4_HD_FINAL_DECODED_READABLE.png"; dec.save(dp)

subprocess.run(["python3",str(validator),str(sp),str(dp),str(ap),"--protected-mask",str(pp),"--report",str(out/"A_PRODUCTION17_FINAL_MASK_VALIDATION.json")],check=True)
finalrep=json.loads((out/"A_PRODUCTION17_FINAL_MASK_VALIDATION.json").read_text())
diff=dmask(readable,dec)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_out=count(ImageChops.multiply(ImageChops.difference(readable.getchannel("A"),dec.getchannel("A")).point(lambda v:255 if v else 0),ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(diff,protected))

# Decode-localized bbox is the visible candidate within the original cell.
db=dec.crop(tuple(cell)).getchannel("A").getbbox()
if not db: raise RuntimeError("decoded candidate empty")
loc=[cell[0]+db[0],cell[1]+db[1],cell[0]+db[2],cell[1]+db[3]]
contain=loc[0]>=ob[0] and loc[1]>=ob[1] and loc[2]<=ob[2] and loc[3]<=ob[3]
size_ok=(loc[2]-loc[0])<=(ob[2]-ob[0]) and (loc[3]-loc[1])<=(ob[3]-ob[1])
positive=loc[0]>ob[0] and loc[1]>ob[1] and loc[2]<ob[2] and loc[3]<ob[3]

# Residue guard: away from a 4px expansion of the intended Korean render, source-mask pixels
# must decode fully transparent. Compression fringe around intended Korean is excluded.
kguard=Image.new("L",(W,H),0)
ImageDraw.Draw(kguard).rectangle((max(ob[0],ideal_loc[0]-4),max(ob[1],ideal_loc[1]-4),min(ob[2]-1,ideal_loc[2]+3),min(ob[3]-1,ideal_loc[3]+3)),fill=255)
residue_zone=ImageChops.multiply(srcmask,ImageOps.invert(kguard))
decoded_visible=balpha(dec)
residue=count(ImageChops.multiply(decoded_visible,residue_zone))

# Verify all decoded pixels outside exact bbox equal source RGBA exactly.
outside_exact_pixels=outside
raw_bbox=[loc[0],H-loc[3],loc[2],H-loc[1]]
raw_contain=raw_bbox[0]>=raw_ob[0] and raw_bbox[1]>=raw_ob[1] and raw_bbox[2]<=raw_ob[2] and raw_bbox[3]<=raw_ob[3]

def gray(im):
    bg=Image.new("RGBA",im.size,(90,90,90,255)); bg.alpha_composite(im); return bg.convert("RGB")
sheet=Image.new("RGB",(W,H*3),(60,60,60))
sheet.paste(gray(readable),(0,0)); sheet.paste(gray(clean),(0,H)); sheet.paste(gray(dec),(0,H*2))
sheet.save(out/"A_PRODUCTION17_SOURCE_CLEAN_FINAL_GRAY.jpg",quality=95)
gray(dr).save(out/"A_PRODUCTION17_FINAL_RAW_GRAY.jpg",quality=95)
crop=(0,80,1200,256)
cs=Image.new("RGB",(1200,(256-80)*3),(60,60,60))
for i,im in enumerate([readable,clean,dec]): cs.paste(gray(im.crop(crop)),(0,i*(256-80)))
cs.save(out/"A_PRODUCTION17_NEXT_ROUND_DETAIL.jpg",quality=96)

status=(cleanrep["status"]=="PASS" and finalrep["status"]=="PASS" and outside==0 and alpha_out==0 and prot==0 and residue==0 and contain and size_ok and positive and raw_contain)
report={
 "schema_version":1,"role":"A","run":run,"index":55,"asset":asset_rel,"worker":os.environ.get("OUTRUN_CPU_WORKER"),
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":BLOB,"sha256":SOURCE_SHA,"path":"Release/spr_sprani_game_cvt_Exst/2EA557B4_512x64.dds","classification":"authoritative HD source; stale filename suffix, DDS header 2048x256 DXT5"},
 "source_sha256":SOURCE_SHA,"candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),
 "structure":{"dimensions":[W,H],"compression":"DXT5","bytes":len(sb),"header_128_exact":True,"raw_orientation":"mirror_y","exact_source_bbox_block_aligned":False},
 "translation":{"source":"NEXT ROUND","korean":"다음 라운드"},
 "method":"constrained DXT5: full interior blocks from source-faithful target encode; partial boundary blocks keep exact source endpoints/color/index data and rewrite only in-bbox alpha indices to an existing source zero-alpha index",
 "original_bbox":ob,"localized_bbox":loc,"raw_original_bbox":raw_ob,"raw_localized_bbox":raw_bbox,
 "delta_left":loc[0]-ob[0],"delta_right":ob[2]-loc[2],"delta_top":loc[1]-ob[1],"delta_bottom":ob[3]-loc[3],
 "source_size":[ob[2]-ob[0],ob[3]-ob[1]],"localized_size":[loc[2]-loc[0],loc[3]-loc[1]],
 "containment":"PASS" if contain else "FAIL","raw_containment":"PASS" if raw_contain else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL","positive_margin":"PASS" if positive else "FAIL",
 "font":"Noto Sans CJK KR Black","font_size":fs,
 "dxt5":{"full_replaced_blocks":full_blocks,"partial_boundary_blocks":partial_blocks,"boundary_in_bbox_alpha_samples_cleared":boundary_pixels_cleared},
 "clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "decoded_changes":{"changed_pixels_total":count(diff),"changed_pixels_outside_original_bbox":outside_exact_pixels,"alpha_changed_pixels_outside_original_bbox":alpha_out,"protected_visible_pixels_changed":prot,"source_residue_visible_pixels_outside_korean_guard":residue},
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"UNTESTED",
 "status":"A_PRODUCTION17_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status else "A_PRODUCTION17_WORKER_REWORK_REQUIRED"
}
(out/"A_PRODUCTION17_2EA557B4_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"2EA557B4","index":55,"source_sha256":SOURCE_SHA,"candidate_sha256":csha,"source_dimensions":[W,H],"compression":"DXT5","bbox_pass":"1/1" if contain and raw_contain else "FAIL","size_ceiling":"1/1" if size_ok else "FAIL","positive_margin":"1/1" if positive else "FAIL","clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],"changed_pixels_outside_original_bbox":outside,"alpha_changed_pixels_outside_original_bbox":alpha_out,"protected_visible_pixels_changed":prot,"source_residue_visible_pixels_outside_korean_guard":residue,"partial_boundary_blocks":partial_blocks,"worker_status":report["status"],"runtime_validation":"UNTESTED","report":"localization/graphics/role_A/20261005-A-PRODUCTION17/A_PRODUCTION17_2EA557B4_REPORT.json"}
(wr/"A_PRODUCTION17_2EA557B4.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status: raise SystemExit(2)
