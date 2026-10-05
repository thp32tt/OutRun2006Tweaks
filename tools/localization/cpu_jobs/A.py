#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,statistics
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageFilter,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd(); run="20261005-A-PRODUCTION24"
out=repo/"localization/graphics/role_A"/run; wr=repo/"localization/graphics/worker_results"
out.mkdir(parents=True,exist_ok=True); wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_game_cvt_Exst/7CE1CFC5_512x128.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"; base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
srcp=Path("/tmp/7CE1CFC5_HD.dds"); atp=Path("/tmp/7CE1CFC5_atlas.json")
urllib.request.urlretrieve(base+"/Release/spr_sprani_game_cvt_Exst/7CE1CFC5_512x128.dds",srcp)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_game_cvt_Exst/4x_7CE1CFC5_512x128_atlas.json",atp)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def count(im): return sum(im.histogram()[1:])
def bmask(im): return im.point(lambda v:255 if v else 0)
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def diffmask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for q in bands[1:]: m=ImageChops.lighter(m,q)
    return bmask(m)

sb=srcp.read_bytes(); ab=atp.read_bytes()
if blob(sb)!="8e79a14a4453c7e015144c1c2e25a4aacc633645": raise RuntimeError(("source drift",blob(sb)))
if blob(ab)!="1a13020899080238d4177800382137f0a3e291a5": raise RuntimeError(("atlas drift",blob(ab)))
if sb[:4]!=b"DDS " or sb[84:88]!=b"DXT5": raise RuntimeError(("not DXT5",sb[84:88]))
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
need=128+((W+3)//4)*((H+3)//4)*16
if (W,H)!=(2048,512) or mips not in (0,1) or len(sb)!=need: raise RuntimeError(("unexpected DDS",W,H,mips,len(sb),need))
raw_src=Image.open(srcp).convert("RGBA"); src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM); sa=np.asarray(src,dtype=np.uint8)
regs={r["idx"]:r for r in json.loads(ab.decode("utf-8"))["regions"]}

# Controller-confirmed from 4x atlas + original contact: indices 0/1/2/8 are the four text labels.
# Regions 2 and 8 overlap unrelated line/car artwork at their top edge; strict y floors protect it.
specs=[
 (0,"NEXT MISSION","다음 미션",344,"big"),
 (1,"Race The Rivals!","라이벌과 레이스!",200,"small"),
 (2,"Drift To Score!","드리프트 점수 도전!",40,"small"),
 (8,"Slipstream To Score!","슬립스트림 점수 도전!",200,"small"),
]
rows=[]; source_masks=[]
for idx,en,ko,yfloor,family in specs:
    x,y,cw,ch=regs[idx]["rect"]; y0=max(y,yfloor); y1=y+ch
    alpha=sa[y0:y1,x:x+cw,3]>0
    ys,xs=np.nonzero(alpha)
    if not len(xs): raise RuntimeError(("empty text",idx,en))
    bb=[x+int(xs.min()),y0+int(ys.min()),x+int(xs.max())+1,y0+int(ys.max())+1]
    m=np.zeros((H,W),bool); m[y0:y1,x:x+cw]=alpha
    # Keep only pixels inside the exact text bbox.
    m[:,:bb[0]]=False; m[:,bb[2]:]=False; m[:bb[1],:]=False; m[bb[3]:,:]=False
    source_masks.append(m)
    rows.append({"region_idx":idx,"source":en,"korean":ko,"family":family,"cell":[x,y,cw,ch],"text_roi":[x,y0,cw,y1-y0],
                 "original_bbox":bb,"source_width":bb[2]-bb[0],"source_height":bb[3]-bb[1],"source_mask_pixels":int(np.count_nonzero(m))})
source_mask=np.zeros((H,W),bool)
for m in source_masks: source_mask|=m
if sum(np.count_nonzero(m) for m in source_masks)!=np.count_nonzero(source_mask): raise RuntimeError("source masks overlap")

allowed=np.zeros((H,W),bool)
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]; allowed[y0:y1,x0:x1]=True

# Clean plate: transparent source text/effects only. Preserve hidden RGB and every protected pixel.
clean_arr=sa.copy(); clean_arr[source_mask,3]=0
clean=Image.fromarray(clean_arr,"RGBA")

# Source-derived style colors.
allpix=sa[source_mask]
warm=allpix[(allpix[:,3]>100)&(allpix[:,0]>170)&(allpix[:,1]>80)&(allpix[:,2]<190)]
whitep=allpix[(allpix[:,3]>100)&(allpix[:,:3].min(axis=1)>205)]
navyp=allpix[(allpix[:,3]>100)&(allpix[:,2]>allpix[:,0]+15)&(allpix[:,2]>allpix[:,1]+8)&(allpix[:,0]<90)&(allpix[:,1]<90)&(allpix[:,2]<160)]
if len(warm)<100 or len(whitep)<100 or len(navyp)<100: raise RuntimeError(("style samples",len(warm),len(whitep),len(navyp)))
yellow=tuple(int(round(float(np.median(warm[:,k])))) for k in range(3))+(255,)
white=tuple(int(round(float(np.median(whitep[:,k])))) for k in range(3))+(255,)
navy=tuple(int(round(float(np.median(navyp[:,k])))) for k in range(3))+(255,)

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra","libnvtt-bin"],check=True)
FONT=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Black"],text=True).strip()
fp,fi,fstyle=FONT.rsplit("|",2); fi=int(fi or 0)
if not Path(fp).exists() or not Path("/usr/bin/nvcompress").exists(): raise RuntimeError(("dependency",FONT))

def shear_rgba(im,s):
    shift=max(0,int(round(s*(im.height-1))))
    o=Image.new("RGBA",(im.width+shift,im.height),(0,0,0,0))
    for yy in range(im.height):
        o.alpha_composite(im.crop((0,yy,im.width,yy+1)),(int(round(s*(im.height-1-yy))),yy))
    return o

def text_mask(text,fs,stroke):
    f=ImageFont.truetype(fp,fs,index=fi)
    d=ImageDraw.Draw(Image.new("L",(4,4),0)); bb=d.textbbox((0,0),text,font=f,stroke_width=stroke)
    pad=stroke+8; m=Image.new("L",(bb[2]-bb[0]+2*pad,bb[3]-bb[1]+2*pad),0)
    ImageDraw.Draw(m).text((pad-bb[0],pad-bb[1]),text,font=f,fill=255,stroke_width=stroke,stroke_fill=255)
    b=m.getbbox(); return m.crop(b) if b else None

def make_small(text,fs):
    inner=max(3,round(fs*.055)); outer=max(inner+4,round(fs*.13))
    f=ImageFont.truetype(fp,fs,index=fi)
    d=ImageDraw.Draw(Image.new("L",(4,4),0)); bb=d.textbbox((0,0),text,font=f,stroke_width=outer)
    pad=outer+8; size=(bb[2]-bb[0]+2*pad,bb[3]-bb[1]+2*pad); pos=(pad-bb[0],pad-bb[1])
    om=Image.new("L",size,0); nm=Image.new("L",size,0); fm=Image.new("L",size,0)
    ImageDraw.Draw(om).text(pos,text,font=f,fill=255,stroke_width=outer,stroke_fill=255)
    ImageDraw.Draw(nm).text(pos,text,font=f,fill=255,stroke_width=inner,stroke_fill=255)
    ImageDraw.Draw(fm).text(pos,text,font=f,fill=255)
    # Source has a soft white halo outside the navy outline.
    halo=om.filter(ImageFilter.GaussianBlur(max(1.2,fs*.018)))
    tile=Image.new("RGBA",size,(0,0,0,0)); tile.paste(white,(0,0),halo); tile.paste(navy,(0,0),om); tile.paste(yellow,(0,0),fm)
    b=tile.getchannel("A").getbbox(); return tile.crop(b) if b else None,{"inner":inner,"outer":outer}

def big_gradient(size):
    w,h=size; im=Image.new("RGBA",size); p=im.load()
    for yy in range(h):
        t=yy/max(1,h-1)
        if t<.38:
            u=t/.38; c=(255,int(round(158+(246-158)*u)),int(round(5+(220-5)*u)),255)
        elif t<.62:
            u=(t-.38)/.24; c=(255,int(round(246+(248-246)*u)),int(round(220+(232-220)*u)),255)
        else:
            u=(t-.62)/.38; c=(255,int(round(248+(181-248)*u)),int(round(232+(16-232)*u)),255)
        for xx in range(w): p[xx,yy]=c
    return im

def make_big(text,fs):
    outer=max(7,round(fs*.075)); inner=max(3,round(fs*.03)); shadow=max(5,round(fs*.055))
    f=ImageFont.truetype(fp,fs,index=fi)
    d=ImageDraw.Draw(Image.new("L",(4,4),0)); bb=d.textbbox((0,0),text,font=f,stroke_width=outer)
    pad=outer+shadow+10; size=(bb[2]-bb[0]+2*pad,bb[3]-bb[1]+2*pad); pos=(pad-bb[0],pad-bb[1])
    om=Image.new("L",size,0); wm=Image.new("L",size,0); fm=Image.new("L",size,0)
    ImageDraw.Draw(om).text(pos,text,font=f,fill=255,stroke_width=outer,stroke_fill=255)
    ImageDraw.Draw(wm).text(pos,text,font=f,fill=255,stroke_width=inner,stroke_fill=255)
    ImageDraw.Draw(fm).text(pos,text,font=f,fill=255)
    tile=Image.new("RGBA",(size[0]+shadow,size[1]+shadow),(0,0,0,0))
    sm=Image.new("L",tile.size,0); sm.paste(om,(shadow,shadow)); tile.paste((7,15,57,220),(0,0,tile.width,tile.height),sm)
    z=Image.new("L",tile.size,0); z.paste(om,(0,0)); tile.paste(navy,(0,0),z)
    z=Image.new("L",tile.size,0); z.paste(wm,(0,0)); tile.paste(white,(0,0),z)
    z=Image.new("L",tile.size,0); z.paste(fm,(0,0)); tile.paste(big_gradient(tile.size),(0,0),z)
    tile=shear_rgba(tile,.20)
    b=tile.getchannel("A").getbbox(); return tile.crop(b) if b else None,{"outer":outer,"inner":inner,"shadow":shadow,"slant":.20}

# Fit big independently; small labels share one size/style family.
bigrow=rows[0]; bx0,by0,bx1,by1=bigrow["original_bbox"]
big_tile=big_meta=big_fs=None
for fs in range(142,48,-1):
    tile,meta=make_big(bigrow["korean"],fs)
    if tile and tile.width<=(bx1-bx0)-10 and tile.height<=(by1-by0)-10:
        big_tile,big_meta,big_fs=tile,meta,fs; break
if big_tile is None: raise RuntimeError("big fit failed")

small_fs=None; small_tiles={}
for fs in range(94,24,-1):
    trial={}; ok=True
    for row in rows[1:]:
        tile,meta=make_small(row["korean"],fs); x0,y0,x1,y1=row["original_bbox"]
        if tile is None or tile.width>(x1-x0)-8 or tile.height>(y1-y0)-8: ok=False; break
        trial[row["region_idx"]]=(tile,meta)
    if ok: small_fs=fs; small_tiles=trial; break
if small_fs is None: raise RuntimeError("small shared fit failed")

final=clean.copy(); target_masks=[]; outrows=[]
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]
    if row["family"]=="big":
        tile,fs,meta=big_tile,big_fs,big_meta
    else:
        tile,meta=small_tiles[row["region_idx"]]; fs=small_fs
    px=x0+(x1-x0-tile.width)//2; py=y0+(y1-y0-tile.height)//2
    if px<=x0+3 or py<=y0+3 or px+tile.width>=x1-3 or py+tile.height>=y1-3:
        raise RuntimeError(("insufficient DXT5 margin",row["region_idx"],[x0,y0,x1,y1],[px,py,tile.width,tile.height]))
    final.alpha_composite(tile,(px,py))
    lm=Image.new("L",(W,H),0); lm.paste(bmask(tile.getchannel("A")),(px,py)); lb=list(lm.getbbox())
    sw,sh=x1-x0,y1-y0; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    if not(lb[0]>x0 and lb[1]>y0 and lb[2]<x1 and lb[3]<y1 and lw<=sw and lh<=sh): raise RuntimeError(("bbox gate",row["region_idx"],lb,row["original_bbox"]))
    target_masks.append(lm)
    outrows.append({**row,"localized_bbox":lb,"localized_width":lw,"localized_height":lh,
      "delta_left":lb[0]-x0,"delta_right":x1-lb[2],"delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","font_file":Path(fp).name,"font_style":fstyle,
      "font_size":fs,"style_effects":meta,"alignment":"center"})

# Zero pair overlap/touch.
overlap=touch=0
for i in range(len(target_masks)):
    for j in range(i+1,len(target_masks)):
        overlap+=count(ImageChops.multiply(target_masks[i],target_masks[j]))
        touch+=count(ImageChops.multiply(target_masks[i].filter(ImageFilter.MaxFilter(3)),target_masks[j]))
if overlap or touch: raise RuntimeError(("localized overlap/touch",overlap,touch))
target=np.zeros((H,W),bool)
for m in target_masks: target|=(np.asarray(m)>0)

# Encode ideal raw-mirror-y final to BC3, then splice with exact boundary preservation.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM); png=Path("/tmp/7CE_final_raw.png"); encp=Path("/tmp/7CE_final_nv.dds"); raw_final.save(png)
subprocess.run(["/usr/bin/nvcompress","-bc3","-nomips",str(png),str(encp)],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
tb=encp.read_bytes()
if tb[84:88]!=b"DXT5" or len(tb)!=len(sb): raise RuntimeError(("encode structure",tb[84:88],len(tb),len(sb)))

allowed_raw=np.flipud(allowed); srcmask_raw=np.flipud(source_mask); target_raw=np.flipud(target); srcalpha_raw=np.flipud(sa[:,:,3])
bw=(W+3)//4; bh=(H+3)//4; outb=bytearray(sb); target_blocks=set(); source_full=set(); partial=set()
def aidx(block):
    bits=int.from_bytes(block[2:8],"little"); return [(bits>>(3*i))&7 for i in range(16)]
def seta(block,idx):
    bits=sum((int(v)&7)<<(3*i) for i,v in enumerate(idx)); return block[:2]+bits.to_bytes(6,"little")+block[8:]
for by in range(bh):
    y=by*4
    for bx in range(bw):
        x=bx*4; am=allowed_raw[y:y+4,x:x+4]; sm=srcmask_raw[y:y+4,x:x+4]; tm=target_raw[y:y+4,x:x+4]
        if not np.any(sm) and not np.any(tm): continue
        off=128+(by*bw+bx)*16
        if np.any(tm):
            if not np.all(am): raise RuntimeError(("target reaches partial BC3 block",bx,by))
            outb[off:off+16]=tb[off:off+16]; target_blocks.add((bx,by)); continue
        if np.all(am):
            outb[off:off+16]=tb[off:off+8]+sb[off+8:off+16]; source_full.add((bx,by)); continue
        if not np.any(sm): continue
        ob=bytes(outb[off:off+16]); idx=aidx(ob); a4=srcalpha_raw[y:y+4,x:x+4]
        zero=[idx[yy*4+xx] for yy in range(4) for xx in range(4) if a4[yy,xx]<=1 and not am[yy,xx]]
        if not zero: zero=[idx[yy*4+xx] for yy in range(4) for xx in range(4) if a4[yy,xx]<=1]
        if not zero: raise RuntimeError(("no transparent alpha index",bx,by))
        zi=Counter(zero).most_common(1)[0][0]
        for yy in range(4):
            for xx in range(4):
                if sm[yy,xx]: idx[yy*4+xx]=zi
        nb=seta(ob,idx)
        if nb[:2]!=ob[:2] or nb[8:]!=ob[8:]: raise RuntimeError("boundary endpoint/color drift")
        outb[off:off+16]=nb; partial.add((bx,by))

candidate.write_bytes(outb); cand_sha=sha(candidate)
if bytes(outb[:128])!=sb[:128]: raise RuntimeError("header drift")
raw_dec=Image.open(candidate).convert("RGBA"); dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM); da=np.asarray(dec,dtype=np.uint8)
diff=np.any(sa!=da,axis=2)
outside=int(np.count_nonzero(diff & ~allowed)); alphaout=int(np.count_nonzero((sa[:,:,3]!=da[:,:,3])&~allowed)); visout=int(np.count_nonzero((da[:,:,3]>1)&(sa[:,:,3]<=1)&~allowed))
if outside or alphaout or visout: raise RuntimeError(("decoded outside drift",outside,alphaout,visout))
guard=np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(7)))>0
residue=int(np.count_nonzero(source_mask&(da[:,:,3]>8)&~guard))
if residue: raise RuntimeError(("source residue",residue))

# Protected source artwork at top-edge overlaps of regions 2/8 must remain byte-identical decoded.
protected_top=((np.indices((H,W))[0]<40)&(np.indices((H,W))[1]<704)) | ((np.indices((H,W))[0]<200)&(np.indices((H,W))[0]>=176)&(np.indices((H,W))[1]>=704)&(np.indices((H,W))[1]<1408))
protected_top_changed=int(np.count_nonzero(diff&protected_top))
if protected_top_changed: raise RuntimeError(("protected top art changed",protected_top_changed))

changed_blocks=outside_patch=0; patch=target_blocks|source_full|partial
for by in range(bh):
    for bx in range(bw):
        off=128+(by*bw+bx)*16
        if sb[off:off+16]!=outb[off:off+16]:
            changed_blocks+=1
            if (bx,by) not in patch: outside_patch+=1
if outside_patch: raise RuntimeError(("compressed outside patch",outside_patch))

# Validation/evidence.
source_png=out/"7CE_SOURCE_READABLE.png"; clean_png=out/"7CE_CLEAN_PLATE.png"; final_png=out/"7CE_FINAL_DECODED_READABLE.png"
src.save(source_png); clean.save(clean_png); dec.save(final_png)
smimg=Image.fromarray((source_mask.astype(np.uint8)*255),"L"); alimg=Image.fromarray((allowed.astype(np.uint8)*255),"L"); protimg=ImageOps.invert(alimg)
smimg.save(out/"7CE_SOURCE_TEXT_MASK.png"); alimg.save(out/"7CE_ALLOWED_BBOX_MASK.png"); protimg.save(out/"7CE_PROTECTED_MASK.png")
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(source_png),str(clean_png),str(out/"7CE_SOURCE_TEXT_MASK.png"),"--report",str(out/"A24_CLEAN_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(source_png),str(final_png),str(out/"7CE_ALLOWED_BBOX_MASK.png"),"--protected-mask",str(out/"7CE_PROTECTED_MASK.png"),"--report",str(out/"A24_FINAL_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"A24_CLEAN_VALIDATION.json").read_text()); finalrep=json.loads((out/"A24_FINAL_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS" or finalrep["status"]!="PASS": raise RuntimeError(("validator",cleanrep["status"],finalrep["status"]))

stack=Image.new("RGB",(1024,3*282),"white")
for i,(label,im) in enumerate([("SOURCE",src),("CLEAN",clean),("FINAL",dec)]):
    z=comp(im).resize((1024,256),Image.Resampling.LANCZOS); stack.paste(z,(0,i*282+24)); ImageDraw.Draw(stack).text((5,i*282+5),label,fill="black")
stack.save(out/"A24_7CE_SOURCE_CLEAN_FINAL.jpg",quality=97)
cards=[]
for row in outrows:
    x0,y0,x1,y1=row["original_bbox"]; p=16; cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[comp(z).crop(cr) for z in (src,clean,dec)]; sc=max(1,min(2,1000//max(1,ims[0].width)))
    ims=[z.resize((z.width*sc,z.height*sc),Image.Resampling.NEAREST) for z in ims]
    c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+34),"white"); xx=0
    for z in ims: c.paste(z,(xx,34)); xx+=z.width+6
    ImageDraw.Draw(c).text((5,5),f'{row["region_idx"]} {row["source"]} -> {row["korean"]}',fill="black"); cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height+4 for c in cards)),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.save(out/"A24_7CE_ROW_CONTACT.jpg",quality=97)
rr=Image.new("RGB",(1024,2*282),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec)]):
    z=comp(im).resize((1024,256),Image.Resampling.LANCZOS); rr.paste(z,(0,i*282+24)); ImageDraw.Draw(rr).text((5,i*282+5),label,fill="black")
rr.save(out/"A24_7CE_RAW_COMPARE.jpg",quality=97)

report={"schema_version":1,"role":"A","run":run,"queue_index":59,"asset":asset,"readiness_tier":"ONE_STAGE_TO_RENDER_COMPLETED_SAME_INVOCATION",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":commit,"source_git_blob_sha1":blob(sb),"atlas_git_blob_sha1":blob(ab),"source_sha256":sha(srcp)},
 "semantic_binding":{"0":"NEXT MISSION -> 다음 미션","1":"Race The Rivals! -> 라이벌과 레이스!","2":"Drift To Score! -> 드리프트 점수 도전!","8":"Slipstream To Score! -> 슬립스트림 점수 도전!"},
 "structure":{"dimensions":[W,H],"format":"DXT5","mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "source_style":{"big":"italic orange-white-yellow gradient, white keyline, navy outline + lower-right shadow","small":"yellow heavy upright fill, navy outline, soft white halo","sampled_yellow_rgba":yellow,"sampled_white_rgba":white,"sampled_navy_rgba":navy,"small_shared_font_size":small_fs,"big_font_size":big_fs},
 "rows":outrows,"clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "decoded_changes":{"changed_pixels_outside_exact_source_bboxes":outside,"alpha_outside":alphaout,"introduced_visible_outside":visout,"source_residue":residue,"protected_top_art_changed":protected_top_changed,"localized_overlap":overlap,"localized_touch":touch},
 "compressed_patch":{"target_reencoded_blocks":len(target_blocks),"source_only_full_alpha_blocks":len(source_full),"partial_alpha_only_blocks":len(partial),"changed_blocks":changed_blocks,"changed_blocks_outside_patch":outside_patch,"partial_endpoints_and_color_bytes_preserved":True},
 "candidate_sha256":cand_sha,"candidate_path":str(candidate.relative_to(repo)),"controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","RUNTIME_VALIDATION":"UNTESTED",
 "status":"A24_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"}
(out/"A24_7CE_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"index":59,"asset":"7CE1CFC5","source_sha256":sha(srcp),"candidate_sha256":cand_sha,"localized_physical_elements":4,
 "bbox_size_positive_margin":"4/4","clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],"source_residue":residue,
 "decoded_changed_outside":outside,"alpha_outside":alphaout,"protected_top_art_changed":protected_top_changed,"overlap":overlap,"touch":touch,
 "changed_blocks_outside_patch":outside_patch,"worker_status":report["status"],"runtime_validation":"UNTESTED","report":str((out/"A24_7CE_REPORT.json").relative_to(repo))}
(wr/"A24_7CE1CFC5.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False))
