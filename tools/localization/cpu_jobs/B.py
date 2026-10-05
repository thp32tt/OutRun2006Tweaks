#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,statistics
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter
import numpy as np
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("worker B only")

repo=Path.cwd()
run="20261005-B-PRODUCTION77"
out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/9FC88069_1024x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"

commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/b77"); work.mkdir(exist_ok=True)
dds=work/"src.dds"; atlas=work/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/9FC88069_1024x512.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_9FC88069_1024x512_atlas.json",atlas)
sb=dds.read_bytes(); ab=atlas.read_bytes()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def comp(im,bg=(48,48,48,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

if blob(sb)!="e97d852a905aa8a219b786b843089e0998037f52": raise RuntimeError(("source blob drift",blob(sb)))
if blob(ab)!="77904226ad9347044c4c091575efbe0aba72717a": raise RuntimeError(("atlas blob drift",blob(ab)))
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6])
mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
if not mode or (W,H)!=(4096,2048) or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,mips,masks,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regions={r["idx"]:r for r in json.loads(ab.decode())["regions"]}

# Exact semantic binding from B76 region contact.
specs=[
 (0,"RANDOM","무작위","card_white"),
 (1,"= RANDOM PLAY =","- 무작위 재생 -","cyan_pixel"),
 (2,"(GUITAR MIX)","(기타 믹스)","cyan_pixel"),
 (10,"(INSTRUMENTAL)","(연주곡)","cyan_pixel"),
 (39,"(PROTOTYPE)","(프로토타입)","cyan_pixel"),
 (40,"INTERMEDIATE B","중급 B","cyan_block"),
 (41,"INTERMEDIATE A","중급 A","cyan_block"),
]
target_ids={x[0] for x in specs}
preserved_ids=[i for i in regions if i not in target_ids]

# Determine source masks/bboxes.
source_mask=Image.new("L",(W,H),0)
allowed=Image.new("L",(W,H),0)
rows=[]
card_bg=None
for idx,en,ko,group in specs:
    x,y,cw,ch=regions[idx]["rect"]
    cell=src.crop((x,y,x+cw,y+ch))
    if idx!=0:
        lm=bmask(cell.getchannel("A"))
    else:
        arr=np.asarray(cell)
        alpha=arr[:,:,3]
        white=(alpha>80)&(arr[:,:,0]>150)&(arr[:,:,1]>150)&(arr[:,:,2]>150)
        # RANDOM is the lower white word; question mark/frame are protected.
        white[:int(ch*0.68),:]=False
        lbl,n=ndimage.label(white)
        seed=np.zeros_like(white,dtype=bool)
        for lab in range(1,n+1):
            ys,xs=np.where(lbl==lab)
            if len(xs)==0: continue
            bw=xs.max()-xs.min()+1; bh=ys.max()-ys.min()+1; area=len(xs)
            if 8<=bw<=120 and 18<=bh<=90 and 80<=area<=4500:
                seed[lbl==lab]=True
        if not seed.any(): raise RuntimeError("RANDOM glyph components not found")
        sy,sx=np.where(seed)
        tx0=max(0,int(sx.min())-5); tx1=min(cw,int(sx.max())+6)
        ty0=max(0,int(sy.min())-5); ty1=min(ch,int(sy.max())+6)
        # Estimate flat blue interior from opaque blue pixels.
        blue=((alpha>240)&(arr[:,:,2]>arr[:,:,0]+20)&(arr[:,:,2]>arr[:,:,1]))
        vals=arr[:,:,:4][blue]
        if len(vals)<100: raise RuntimeError("card blue background sample missing")
        card_bg=tuple(int(round(statistics.median(vals[:,k].tolist()))) for k in range(4))
        dist=np.max(np.abs(arr[:,:,:3].astype(np.int16)-np.array(card_bg[:3],dtype=np.int16)),axis=2)
        effect=(alpha>20)&(dist>12)
        mask=np.zeros_like(effect)
        mask[ty0:ty1,tx0:tx1]=effect[ty0:ty1,tx0:tx1]
        # keep only pixels near seed, avoiding the frame
        near=ndimage.binary_dilation(seed,iterations=3)
        mask &= near
        lm=Image.fromarray((mask.astype(np.uint8)*255),"L")
    bb=lm.getbbox()
    if not bb: raise RuntimeError(("empty source mask",idx,en))
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    smcrop=source_mask.crop((x,y,x+cw,y+ch))
    source_mask.paste(ImageChops.lighter(smcrop,lm),(x,y))
    ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
    rows.append({"region_idx":idx,"source":en,"korean":ko,"group":group,"cell":[x,y,cw,ch],"original_bbox":ob,"source_mask_pixels":count(lm)})

# Clean plate: transparent text-only regions; reconstruct card text with exact blue interior.
clean=src.copy(); cpix=clean.load(); sm=source_mask.load()
for r in rows:
    idx=r["region_idx"]; x,y,cw,ch=r["cell"]
    if idx==0:
        for yy in range(y,y+ch):
            for xx in range(x,x+cw):
                if sm[xx,yy]: cpix[xx,yy]=card_bg
    else:
        for yy in range(y,y+ch):
            for xx in range(x,x+cw):
                if sm[xx,yy]: cpix[xx,yy]=(0,0,0,0)

sp=out/"9FC_SOURCE_READABLE.png"; cp=out/"9FC_CLEAN_PLATE.png"; smp=out/"9FC_SOURCE_TEXT_MASK.png"; ap=out/"9FC_ALLOWED_BBOX_MASK.png"
src.save(sp); clean.save(cp); source_mask.save(smp); allowed.save(ap)
protected=ImageChops.multiply(bmask(src.getchannel("A")),ImageOps.invert(allowed))
pp=out/"9FC_PROTECTED_VISIBLE_MASK.png"; protected.save(pp)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(smp),"--protected-mask",str(pp),"--report",str(out/"B77_CLEAN_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"B77_CLEAN_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean validator",cleanrep))

# Verified heavy CJK face.
subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
font_line=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Black"],text=True).strip()
FONT,FI,FSTYLE=font_line.rsplit("|",2); FI=int(FI or 0)
if "Black" not in Path(FONT).name and "Black" not in FSTYLE: raise RuntimeError(("heavy CJK face missing",font_line))

def source_color(idx):
    r=next(z for z in rows if z["region_idx"]==idx); ob=r["original_bbox"]
    vals=[]
    for yy in range(ob[1],ob[3]):
        for xx in range(ob[0],ob[2]):
            if sm[xx,yy]:
                rr,gg,bb,aa=src.getpixel((xx,yy))
                if aa>64: vals.append((rr,gg,bb,aa))
    if not vals: return (65,185,235,255)
    vals.sort(key=lambda v:0.2126*v[0]+0.7152*v[1]+0.0722*v[2])
    top=vals[int(len(vals)*0.55):]
    return tuple(int(round(statistics.median([v[k] for v in top]))) for k in range(4))

cyan=source_color(39)
cyan_block=source_color(40)
white=(248,248,248,255)

def render_pixel(text,max_w,max_h,color,shadow=True):
    # Source artwork is native low-resolution pixel type scaled 4x in the HD atlas.
    low_w=max(8,max_w//4); low_h=max(8,max_h//4)
    best=None
    for fs in range(max(6,low_h+4),5,-1):
        font=ImageFont.truetype(FONT,fs,index=FI)
        probe=Image.new("L",(8,8),0); bb=ImageDraw.Draw(probe).textbbox((0,0),text,font=font)
        pad=3
        tw=max(1,bb[2]-bb[0]); th=max(1,bb[3]-bb[1])
        canvas=Image.new("RGBA",(tw+pad*2+2,th+pad*2+2),(0,0,0,0))
        d=ImageDraw.Draw(canvas)
        if shadow:
            sh=(max(0,color[0]//3),max(0,color[1]//3),max(0,color[2]//3),220)
            d.text((pad-bb[0]+1,pad-bb[1]+1),text,font=font,fill=sh)
        d.text((pad-bb[0],pad-bb[1]),text,font=font,fill=color)
        ab=canvas.getchannel("A").getbbox()
        if not ab: continue
        canvas=canvas.crop(ab)
        up=canvas.resize((canvas.width*4,canvas.height*4),Image.Resampling.NEAREST)
        if up.width<=max_w-8 and up.height<=max_h-8:
            best=(up,fs); break
    if best is None: raise RuntimeError(("pixel text fit failed",text,max_w,max_h))
    return best

final=clean.copy(); targets=[]; outrows=[]
for r in rows:
    idx=r["region_idx"]; ob=r["original_bbox"]; aw=ob[2]-ob[0]; ah=ob[3]-ob[1]
    color=white if idx==0 else (cyan_block if r["group"]=="cyan_block" else cyan)
    lay,fs=render_pixel(r["korean"],aw,ah,color,shadow=(idx!=0))
    if idx==0:
        px=ob[0]+(aw-lay.width)//2
    else:
        px=ob[0]+4
    py=ob[1]+(ah-lay.height)//2
    px=max(ob[0]+4,min(px,ob[2]-4-lay.width)); py=max(ob[1]+4,min(py,ob[3]-4-lay.height))
    final.alpha_composite(lay,(px,py))
    lm=Image.new("L",(W,H),0); lm.paste(bmask(lay.getchannel("A")),(px,py))
    lb=list(lm.getbbox())
    if not(lb[0]>ob[0] and lb[1]>ob[1] and lb[2]<ob[2] and lb[3]<ob[3]): raise RuntimeError(("positive margin",idx,ob,lb))
    if lb[2]-lb[0]>aw or lb[3]-lb[1]>ah: raise RuntimeError(("size ceiling",idx,ob,lb))
    targets.append((idx,lm))
    outrows.append({**r,"localized_bbox":lb,"source_width":aw,"source_height":ah,
      "localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
      "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
      "font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,"lowres_font_size":fs,
      "pixel_scale":4,"fill_rgba":color,"alignment":"center" if idx==0 else "left","rework_status":"B77_NEW_EXACT_HD_CANDIDATE"})

# Pairwise overlap/touch.
ov=0; touch=[]
for i in range(len(targets)):
    for j in range(i+1,len(targets)):
        a=targets[i][1]; b=targets[j][1]
        x=count(ImageChops.multiply(a,b)); n=count(ImageChops.multiply(a.filter(ImageFilter.MaxFilter(3)),b))
        ov+=x
        if x or n: touch.append([targets[i][0],targets[j][0],x,n])
if ov or touch: raise RuntimeError(("label overlap/touch",ov,touch))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",mode)
if payload[:128]!=sb[:128]: raise RuntimeError("header mismatch")
candidate.write_bytes(payload); csha=sha(payload)
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("raw roundtrip mismatch")
fp=out/"9FC_FINAL_DECODED_READABLE.png"; dec.save(fp)
subprocess.run(["python3",str(validator),str(sp),str(fp),str(ap),"--protected-mask",str(pp),"--report",str(out/"B77_FINAL_VALIDATION.json")],check=True)
finalrep=json.loads((out/"B77_FINAL_VALIDATION.json").read_text())

diff=dmask(src,dec)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alphaout=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(diff,protected))
target=Image.new("L",(W,H),0)
for _,m in targets: target=ImageChops.lighter(target,m)
clean_change=dmask(src,clean)
residue=count(ImageChops.multiply(ImageChops.multiply(clean_change,ImageOps.invert(target)),ImageOps.invert(diff)))
if finalrep["status"]!="PASS" or outside or alphaout or prot or residue or ov or touch:
    raise RuntimeError(("gates",finalrep["status"],outside,alphaout,prot,residue,ov,touch))
target.save(out/"9FC_TARGET_TEXT_MASK.png")

# All non-target atlas regions must remain pixel exact.
preserved_changed={}
for idx in preserved_ids:
    x,y,w,h=regions[idx]["rect"]
    preserved_changed[str(idx)]=count(dmask(src.crop((x,y,x+w,y+h)),dec.crop((x,y,x+w,y+h))))
# Target card artwork outside its exact text bbox must also be exact.
ob0=next(r["original_bbox"] for r in rows if r["region_idx"]==0)
cardx,cardy,cardw,cardh=regions[0]["rect"]
cardprot=Image.new("L",(W,H),0); ImageDraw.Draw(cardprot).rectangle((cardx,cardy,cardx+cardw-1,cardy+cardh-1),fill=255)
ImageDraw.Draw(cardprot).rectangle((ob0[0],ob0[1],ob0[2]-1,ob0[3]-1),fill=0)
card_art_changed=count(ImageChops.multiply(diff,cardprot))
if any(preserved_changed.values()) or card_art_changed:
    raise RuntimeError(("preservation",card_art_changed,{k:v for k,v in preserved_changed.items() if v}))

# Evidence images.
full=Image.new("RGB",(1024,3*536),"white")
for i,(label,im) in enumerate([("SOURCE",src),("CLEAN",clean),("FINAL",dec)]):
    z=comp(im).resize((1024,512),Image.Resampling.LANCZOS); full.paste(z,(0,i*536+24))
    ImageDraw.Draw(full).text((5,i*536+4),label,fill="black")
full.save(out/"B77_9FC_SOURCE_CLEAN_FINAL.jpg",quality=95)

cards=[]
for r in outrows:
    ob=r["original_bbox"]; p=12
    cr=(max(0,ob[0]-p),max(0,ob[1]-p),min(W,ob[2]+p),min(H,ob[3]+p))
    ims=[comp(z).crop(cr) for z in (src,clean,dec)]
    scale=max(1,min(2,900//max(1,ims[0].width)))
    ims=[z.resize((z.width*scale,z.height*scale),Image.Resampling.NEAREST) for z in ims]
    c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+30),"white")
    xx=0
    for z in ims: c.paste(z,(xx,30)); xx+=z.width+6
    ImageDraw.Draw(c).text((5,5),f'{r["region_idx"]} {r["source"]} -> {r["korean"]}',fill="black")
    cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+4*(len(cards)-1)),"white")
yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.thumbnail((1800,10000),Image.Resampling.LANCZOS)
sheet.save(out/"B77_9FC_ROW_CONTACT.jpg",quality=96)

rr=Image.new("RGB",(1024,2*536),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec)]):
    z=comp(im).resize((1024,512),Image.Resampling.LANCZOS); rr.paste(z,(0,i*536+24))
    ImageDraw.Draw(rr).text((5,i*536+4),label,fill="black")
rr.save(out/"B77_9FC_RAW_COMPARE.jpg",quality=95)

report={"schema_version":1,"role":"B","run":run,"index":198,"asset":asset,
 "readiness_tier":"ONE_STAGE_TO_RENDER_COMPLETED_SAME_INVOCATION",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":commit,"git_blob_sha1":blob(sb),"atlas_git_blob_sha1":blob(ab),"source_sha256":sha(sb)},
 "semantic_binding":{"localized":{str(i):s for i,s,_,_ in specs},"protected":"all non-target atlas regions including song titles and TBD labels"},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "style":{"font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,"pixel_scale":4,"cyan_rgba":cyan,"cyan_block_rgba":cyan_block,"card_white_rgba":white,"source_style":"native low-resolution pixel lettering upscaled 4x nearest with dark cyan shadow where present"},
 "rows":outrows,"card_blue_background_rgba":card_bg,"card_art_changed_outside_text_bbox":card_art_changed,
 "preserved_regions_changed_pixels":preserved_changed,
 "clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "decoded_changes":{"changed_pixels_total":count(diff),"outside":outside,"alpha_outside":alphaout,"protected_changed":prot,"exact_source_residue":residue,"overlap":ov,"touch_pairs":touch},
 "candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","RUNTIME_VALIDATION":"UNTESTED",
 "status":"B_PRODUCTION77_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"}
(out/"B77_9FC_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"index":198,"asset":"9FC88069","source_sha256":sha(sb),"candidate_sha256":csha,
 "localized_physical_elements":len(specs),"preserved_regions":len(preserved_ids),
 "bbox_size_positive_margin":f"{len(specs)}/{len(specs)}","clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],
 "source_residue":residue,"outside":outside,"alpha_outside":alphaout,"protected_changed":prot,
 "preserved_regions_changed":sum(preserved_changed.values()),"card_art_changed":card_art_changed,"overlap":ov,"touch_pairs":len(touch),
 "worker_status":report["status"],"runtime_validation":"UNTESTED","report":f"localization/graphics/role_B/{run}/B77_9FC_REPORT.json"}
(wr/"B77_9FC88069.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False))
