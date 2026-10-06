#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,shutil
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd(); run="20261007-A-MANUALQA148-2EA557B4"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_sprani_game_cvt_Exst/2EA557B4_512x64.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel; candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"
work=Path("/tmp/outrun_A148_q055"); work.mkdir(parents=True,exist_ok=True)
source=work/"2EA557B4_HD.dds"; atlas=work/"4x_2EA557B4_512x64_atlas.json"
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_SHA="b2d5b03a8e6cc56fcb60c31f32a485854dd7ea41ed10c7b10ba185625d07a685"
EXPECTED_BEFORE="b0cf1dbdd1c73801f3023e9c45af245b4f655f1d4c6f6b0a08e1c1bdae16d7fc"
SOURCE_WIDTH_RESTORE=1.65
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
if not candidate.exists() or sha(candidate)!=EXPECTED_BEFORE: raise RuntimeError(("candidate drift before A148",sha(candidate) if candidate.exists() else None,EXPECTED_BEFORE))
old_raw=Image.open(candidate).convert("RGBA"); old_readable=old_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
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
subprocess.run(["python3",str(validator),str(sp),str(cp),str(spm),"--protected-mask",str(cpp),"--report",str(out/"A148_CLEAN_PLATE_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"A148_CLEAN_PLATE_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean fail",cleanrep))

def fontpath():
    specs=[
        ("Noto Sans CJK KR:style=Bold","Bold"),
        ("Noto Sans CJK KR:style=Black","Black"),
        ("Noto Sans CJK KR",""),
    ]
    def pick():
        for pat,want in specs:
            try:
                spec=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
            except Exception:
                spec=""
            if "|" not in spec: continue
            fp,idx=spec.rsplit("|",1)
            try: idx=int(idx or "0")
            except Exception: idx=0
            name=Path(fp).name
            if fp and Path(fp).exists() and "NotoSansCJK" in name and (not want or want in name):
                return fp,idx,pat
        return None
    got=pick()
    if got: return got
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    got=pick()
    if not got: raise RuntimeError("actual Noto CJK Bold/Black face unavailable")
    return got

FONT,FONT_INDEX,FONT_PATTERN=fontpath()

# Derive the source title's actual vertical fill profile from the eroded glyph core.
# This deliberately avoids the white/navy edging and uses canonical pixels rather than
# a hand-authored approximation.
scrop=readable.crop(tuple(ob))
sa=scrop.getchannel("A").point(lambda v:255 if v>=160 else 0)
core=sa.filter(ImageFilter.MinFilter(11))
spix=scrop.load(); cpix=core.load()
profile=[]
for yy in range(scrop.height):
    vals=[]
    for xx in range(scrop.width):
        if cpix[xx,yy]:
            r,g,b,a=spix[xx,yy]
            if a>=160 and max(r,g,b)>=90:
                vals.append((r,g,b))
    if vals:
        profile.append(tuple(int(round(sorted(v[k] for v in vals)[len(vals)//2])) for k in range(3)))
    else:
        profile.append(None)
valid=[i for i,v in enumerate(profile) if v is not None]
if len(valid)<20:
    raise RuntimeError(("insufficient source fill profile",len(valid)))
for i in range(len(profile)):
    if profile[i] is None:
        j=min(valid,key=lambda z:abs(z-i))
        profile[i]=profile[j]

visible=[]
for yy in range(scrop.height):
    for xx in range(scrop.width):
        r,g,b,a=spix[xx,yy]
        if a>=80:
            visible.append((r,g,b,a))
navy_samples=[p for p in visible if max(p[:3])<125 and p[2]>=p[0]]
white_samples=[p for p in visible if min(p[:3])>=220]
if len(navy_samples)<100 or len(white_samples)<100:
    raise RuntimeError(("source edge samples",len(navy_samples),len(white_samples)))
def med4(vals):
    return tuple(int(round(sorted(v[k] for v in vals)[len(vals)//2])) for k in range(4))
navy=med4(navy_samples)
white=med4(white_samples)

def shear(m,s):
    w,h=m.size; k=s/max(1,h-1)
    return m.transform((w+s+6,h),Image.Transform.AFFINE,(1,k,-s,0,1,0),resample=Image.Resampling.BICUBIC)

def grad(size):
    w,h=size
    im=Image.new("RGBA",size,(0,0,0,0)); px=im.load()
    n=len(profile)
    for yy in range(h):
        sy=int(round((yy/max(1,h-1))*(n-1)))
        r,g,b=profile[sy]
        for xx in range(w):
            px[xx,yy]=(r,g,b,255)
    return im

def render(text):
    aw,ah=ob[2]-ob[0],ob[3]-ob[1]
    for fs in range(min(138,ah-8),40,-1):
        f=ImageFont.truetype(FONT,fs,index=FONT_INDEX)
        outer=max(8,fs//12)
        white_stroke=max(5,fs//20)
        body_extra=max(3,fs//34)
        pad=outer+20
        tb=f.getbbox(text,stroke_width=outer)
        cw=tb[2]-tb[0]+pad*2
        ch=tb[3]-tb[1]+pad*2
        masks={}
        for name,sw in [("outer",outer),("white",white_stroke),("body",body_extra)]:
            m=Image.new("L",(cw,ch),0); d=ImageDraw.Draw(m)
            d.text((pad-tb[0],pad-tb[1]),text,font=f,fill=255,stroke_width=sw,stroke_fill=255)
            masks[name]=shear(m,max(12,int(round(fs*0.20))))
        union=masks["outer"]
        ub=union.getbbox()
        if not ub: continue
        masks={k:v.crop(ub) for k,v in masks.items()}
        mw=max(v.width for v in masks.values()); mh=max(v.height for v in masks.values())
        sx=max(5,fs//22); sy=max(6,fs//20)
        if mw+sx>aw-16 or mh+sy>ah-16: continue
        layer=Image.new("RGBA",(mw+sx,mh+sy),(0,0,0,0))
        # Lower-right depth/shadow.
        sm=Image.new("L",layer.size,0); sm.paste(masks["outer"],(sx,sy))
        layer.paste(Image.new("RGBA",layer.size,(navy[0],navy[1],navy[2],220)),(0,0),sm)
        # Source order: dark navy outer edge -> white middle edge -> filled gradient body.
        om=Image.new("L",layer.size,0); om.paste(masks["outer"],(0,0))
        layer.paste(Image.new("RGBA",layer.size,(navy[0],navy[1],navy[2],255)),(0,0),om)
        wm=Image.new("L",layer.size,0); wm.paste(masks["white"],(0,0))
        layer.paste(Image.new("RGBA",layer.size,(white[0],white[1],white[2],255)),(0,0),wm)
        bm=Image.new("L",layer.size,0); bm.paste(masks["body"],(0,0))
        layer.paste(grad(layer.size),(0,0),bm)
        lb=layer.getchannel("A").getbbox()
        if not lb: continue
        layer=layer.crop(lb)
        target_w=min(aw-16,int(round(layer.width*SOURCE_WIDTH_RESTORE)))
        if target_w>layer.width:
            layer=layer.resize((target_w,layer.height),Image.Resampling.LANCZOS)
            rb=layer.getchannel("A").getbbox()
            if rb: layer=layer.crop(rb)
        if layer.width<=aw-16 and layer.height<=ah-16:
            tx=ob[0]+(aw-layer.width)//2; ty=ob[1]+(ah-layer.height)//2
            if tx>=ob[0]+4 and ty>=ob[1]+4 and tx+layer.width<=ob[2]-4 and ty+layer.height<=ob[3]-4:
                return layer,(tx,ty),fs,outer,white_stroke,body_extra
    raise RuntimeError("filled-gradient fit failed")

layer,(tx,ty),fs,OUTER_STROKE,WHITE_STROKE,BODY_EXTRA=render("다음 라운드")

layer.save(out/"A148_KOREAN_LAYER_FILLED_GRADIENT.png")
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

subprocess.run(["python3",str(validator),str(sp),str(dp),str(ap),"--protected-mask",str(pp),"--report",str(out/"A148_FINAL_MASK_VALIDATION.json")],check=True)
finalrep=json.loads((out/"A148_FINAL_MASK_VALIDATION.json").read_text())
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
old_db=old_readable.crop(tuple(cell)).getchannel("A").getbbox()
if not old_db: raise RuntimeError("prior C164 candidate empty")
old_loc=[cell[0]+old_db[0],cell[1]+old_db[1],cell[0]+old_db[2],cell[1]+old_db[3]]
old_w=old_loc[2]-old_loc[0]; old_h=old_loc[3]-old_loc[1]
new_w=loc[2]-loc[0]; new_h=loc[3]-loc[1]
if new_w < int(round(old_w*1.50)): raise RuntimeError(("insufficient width restoration",old_w,new_w))
if new_h < old_h-2: raise RuntimeError(("height regression",old_h,new_h))

def gray(im):
    bg=Image.new("RGBA",im.size,(90,90,90,255)); bg.alpha_composite(im); return bg.convert("RGB")
sheet=Image.new("RGB",(W*2,H*2),(60,60,60))
sheet.paste(gray(readable),(0,0)); sheet.paste(gray(old_readable),(W,0))
sheet.paste(gray(clean),(0,H)); sheet.paste(gray(dec),(W,H))
sheet.thumbnail((1800,500),Image.Resampling.LANCZOS)
sheet.save(out/"A148_SOURCE_C164_CLEAN_NEW_READABLE.jpg",quality=96)
rawsheet=Image.new("RGB",(W*3,H),(60,60,60))
rawsheet.paste(gray(raw),(0,0)); rawsheet.paste(gray(old_raw),(W,0)); rawsheet.paste(gray(dr),(W*2,0))
rawsheet.thumbnail((2100,320),Image.Resampling.LANCZOS)
rawsheet.save(out/"A148_SOURCE_C164_NEW_RAW.jpg",quality=96)
crop=(0,80,1200,256)
cs=Image.new("RGB",(1200,(256-80)*3),(60,60,60))
for i,im in enumerate([readable,old_readable,dec]): cs.paste(gray(im.crop(crop)),(0,i*(256-80)))
cs.save(out/"A148_NEXT_ROUND_SOURCE_C164_NEW_DETAIL.jpg",quality=96)

status=(cleanrep["status"]=="PASS" and finalrep["status"]=="PASS" and outside==0 and alpha_out==0 and prot==0 and residue==0 and contain and size_ok and positive and raw_contain)
report={
 "schema_version":1,"role":"A","run":run,"index":55,"asset":asset_rel,"worker":os.environ.get("OUTRUN_CPU_WORKER"),
 "trigger":"MANUAL_PRE_INGAME_TEXT_SCALE_HIERARCHY_FALSE_NEGATIVE","review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/017_q055_2EA557B4.jpg","prior_c_status":"C164_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME","prior_candidate_sha256":EXPECTED_BEFORE,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":BLOB,"sha256":SOURCE_SHA,"path":"Release/spr_sprani_game_cvt_Exst/2EA557B4_512x64.dds","classification":"authoritative HD source; stale filename suffix, DDS header 2048x256 DXT5"},
 "source_sha256":SOURCE_SHA,"candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),
 "structure":{"dimensions":[W,H],"compression":"DXT5","bytes":len(sb),"header_128_exact":True,"raw_orientation":"mirror_y","exact_source_bbox_block_aligned":False},
 "translation":{"source":"NEXT ROUND","korean":"다음 라운드"},
 "method":"constrained DXT5: full interior blocks from source-faithful target encode; partial boundary blocks keep exact source endpoints/color/index data and rewrite only in-bbox alpha indices to an existing source zero-alpha index",
 "original_bbox":ob,"localized_bbox":loc,"raw_original_bbox":raw_ob,"raw_localized_bbox":raw_bbox,
 "delta_left":loc[0]-ob[0],"delta_right":ob[2]-loc[2],"delta_top":loc[1]-ob[1],"delta_bottom":ob[3]-loc[3],
 "source_size":[ob[2]-ob[0],ob[3]-ob[1]],"localized_size":[loc[2]-loc[0],loc[3]-loc[1]],
 "containment":"PASS" if contain else "FAIL","raw_containment":"PASS" if raw_contain else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL","positive_margin":"PASS" if positive else "FAIL",
 "font":"Noto Sans CJK KR Bold","font_file":FONT,"font_face_index":FONT_INDEX,"font_pattern":FONT_PATTERN,"font_size":fs,"horizontal_source_hierarchy_scale":SOURCE_WIDTH_RESTORE,"prior_localized_bbox":old_loc,"prior_localized_size":[old_w,old_h],"width_gain_px":new_w-old_w,"width_ratio_vs_c164":round(new_w/old_w,4),"style_geometry":{"outer_navy_stroke":OUTER_STROKE,"white_mid_stroke":WHITE_STROKE,"gradient_body_extra":BODY_EXTRA,"slant_px":max(12,int(round(fs*0.20))),"shadow_offset":[max(5,fs//22),max(6,fs//20)],"source_profile_samples":[profile[0],profile[len(profile)//4],profile[len(profile)//2],profile[(3*len(profile))//4],profile[-1]],"source_navy":navy,"source_white":white},
 "dxt5":{"full_replaced_blocks":full_blocks,"partial_boundary_blocks":partial_blocks,"boundary_in_bbox_alpha_samples_cleared":boundary_pixels_cleared},
 "clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "decoded_changes":{"changed_pixels_total":count(diff),"changed_pixels_outside_original_bbox":outside_exact_pixels,"alpha_changed_pixels_outside_original_bbox":alpha_out,"protected_visible_pixels_changed":prot,"source_residue_visible_pixels_outside_korean_guard":residue},
 "ordered_generation_gate":{"plate_restoration":"PASS_EXACT_SOURCE_MASK","source_matching_slant_direction":"PASS_RIGHT_LEAN_PRESERVED","no_unnecessary_undersizing":"REWORKED_1_65X_WIDTH_PENDING_CONTROLLER","source_faithful_weight_outline_shadow":"PASS_SOURCE_DERIVED","clipping":"PASS_POSITIVE_MARGIN","protected_art_clearance":"PASS_ZERO_OUTSIDE","flip_y_and_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER","immediate_readability":"PENDING_CONTROLLER"},"controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"UNTESTED","status":"A148_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status else "A148_WORKER_REWORK_REQUIRED","no_vr_ffb_dx11_dxvk_work":True
}
(out/"A148_2EA557B4_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"2EA557B4","index":55,"trigger":"MANUAL_PRE_INGAME_TEXT_SCALE_HIERARCHY_FALSE_NEGATIVE","prior_candidate_sha256":EXPECTED_BEFORE,"source_sha256":SOURCE_SHA,"candidate_sha256":csha,"source_dimensions":[W,H],"compression":"DXT5","bbox_pass":"1/1" if contain and raw_contain else "FAIL","size_ceiling":"1/1" if size_ok else "FAIL","positive_margin":"1/1" if positive else "FAIL","clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],"changed_pixels_outside_original_bbox":outside,"alpha_changed_pixels_outside_original_bbox":alpha_out,"protected_visible_pixels_changed":prot,"source_residue_visible_pixels_outside_korean_guard":residue,"partial_boundary_blocks":partial_blocks,"prior_width":old_w,"new_width":new_w,"width_gain_px":new_w-old_w,"width_ratio_vs_c164":round(new_w/old_w,4),"worker_status":report["status"],"runtime_validation":"UNTESTED","report":"localization/graphics/role_A/20261005-A-PRODUCTION26/A148_2EA557B4_REPORT.json"}
(wr/"A148_2EA557B4.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status: raise SystemExit(2)
