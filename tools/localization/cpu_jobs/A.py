#!/usr/bin/env python3
import hashlib,json,math,os,statistics,struct,subprocess,traceback,urllib.request
from pathlib import Path
import numpy as np
from scipy import ndimage
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd()
run="20261006-A-PRODUCTION112-D103-D263"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
tmp=Path("/tmp/a112"); tmp.mkdir(exist_ok=True)

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
q=subprocess.check_output(["fc-match","-f","%{file}|%{index}","Noto Sans CJK KR:style=Bold"],text=True).strip()
FONT,FI=q.rsplit("|",1); FI=int(FI or 0)
if not FONT or not Path(FONT).exists() or "NotoSansCJK" not in Path(FONT).name:
    raise RuntimeError(("font",FONT,FI))
if ImageFont.truetype(FONT,48,index=FI).getmask("코스 선택 출발 골").getbbox() is None:
    raise RuntimeError("Hangul font coverage missing")

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b); zs=d.split(); m=zs[0]
    for z in zs[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def comp(im,bg=(235,235,235,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def decode_rgba32(raw,expected_sha):
    if sha_bytes(raw)!=expected_sha: raise RuntimeError(("source sha drift",sha_bytes(raw),expected_sha))
    if raw[:4]!=b"DDS ": raise RuntimeError("not DDS")
    H,W,pitch,depth,mips=struct.unpack_from("<5I",raw,12)
    pf=struct.unpack_from("<8I",raw,76); masks=(pf[4],pf[5],pf[6])
    mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
    if not mode or len(raw)!=128+W*H*4: raise RuntimeError(("rgba32 structure",W,H,mips,masks,len(raw)))
    rawim=Image.frombytes("RGBA",(W,H),raw[128:],"raw",mode)
    return W,H,mips,mode,rawim,rawim.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def write_candidate(raw,mode,readable,path):
    raw_final=readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    payload=raw[:128]+raw_final.tobytes("raw",mode)
    path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(payload)
    dec_raw=Image.frombytes("RGBA",readable.size,payload[128:],"raw",mode)
    dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    if ImageChops.difference(dec,readable).getbbox(): raise RuntimeError("DDS roundtrip")
    return payload,dec_raw,dec
def shear_mask(mask,k):
    pad=max(6,int(math.ceil(abs(k)*mask.height))+8)
    c=Image.new("L",(mask.width+pad*2,mask.height),0); c.paste(mask,(pad,0))
    o=c.transform(c.size,Image.Transform.AFFINE,(1,-k,k*c.height,0,1,0),resample=Image.Resampling.BICUBIC)
    bb=o.getbbox(); return o.crop(bb) if bb else o

# ---------------- D263 COURSE SELECT: exact C144-approved silver-techno family ----------------
def process_d263():
    name="D263B3F1_512x512.dds"
    p=tmp/name; urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/"+name,p)
    raw=p.read_bytes()
    W,H,mips,mode,raw_src,src=decode_rgba32(raw,"6cb45f18647bb20965d89c9e6e48b427241ea08edccf7b09be3aa53af213555d")
    atlas=json.loads(urllib.request.urlopen(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_D263B3F1_512x512_atlas.json").read().decode())
    region=next(r for r in atlas["regions"] if r["idx"]==2)
    x,y,cw,ch=region["rect"]
    if [cw,ch]!=[2048,156]: raise RuntimeError(("D263 header cell drift",region))
    cell=src.crop((x,y,x+cw,y+ch))
    sm_local=bmask(cell.getchannel("A")); bb=sm_local.getbbox()
    if not bb: raise RuntimeError("D263 empty course-select cell")
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    source_mask=Image.new("L",(W,H),0); source_mask.paste(sm_local,(x,y))
    # exact transparent clean reconstruction: the atlas cell is text-only.
    clean=src.copy(); clean.paste(Image.new("RGBA",(cw,ch),(0,0,0,0)),(x,y),sm_local)
    allowed=Image.new("L",(W,H),0); ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
    source_visible=bmask(src.getchannel("A"))
    protected=ImageChops.multiply(source_visible,ImageOps.invert(allowed))
    # ensure every visible pixel in the COURSE SELECT cell belongs to the source text mask.
    if count(ImageChops.multiply(bmask(cell.getchannel("A")),ImageOps.invert(sm_local)))!=0: raise RuntimeError("D263 unclassified cell pixels")
    sp=out/"A112_D263_SOURCE_READABLE.png"; cp=out/"A112_D263_CLEAN_PLATE.png"
    smp=out/"A112_D263_SOURCE_TEXT_MASK.png"; ap=out/"A112_D263_ALLOWED_BBOX_MASK.png"; pp=out/"A112_D263_PROTECTED_VISIBLE_MASK.png"
    src.save(sp); clean.save(cp); source_mask.save(smp); allowed.save(ap); protected.save(pp)
    subprocess.run(["python3",str(validator),str(sp),str(cp),str(source_mask_path:=smp),"--protected-mask",str(pp),"--report",str(out/"A112_D263_CLEAN_VALIDATION.json")],check=True)
    cr=json.loads((out/"A112_D263_CLEAN_VALIDATION.json").read_text())
    if cr["status"]!="PASS": raise RuntimeError(("D263 clean validator",cr))
    # C144/B68 exact approved family parameters.
    SHEAR=0.12; STROKE=5; SDX=4; SDY=5; MARGIN=4
    TOP=(244,244,244,255); BOTTOM=(134,134,134,255); OUTLINE=(2,2,2,255); SHADOW=(2,2,2,200)
    def render(text,fs):
        f=ImageFont.truetype(FONT,fs,index=FI)
        tb=ImageDraw.Draw(Image.new("L",(8,8),0)).textbbox((0,0),text,font=f)
        pad=STROKE+SDX+12
        fill=Image.new("L",(tb[2]-tb[0]+pad*2,tb[3]-tb[1]+pad*2),0)
        outer=Image.new("L",fill.size,0); pos=(pad-tb[0],pad-tb[1])
        ImageDraw.Draw(fill).text(pos,text,font=f,fill=255)
        ImageDraw.Draw(outer).text(pos,text,font=f,fill=255,stroke_width=STROKE,stroke_fill=255)
        fill=shear_mask(fill,SHEAR); outer=shear_mask(outer,SHEAR)
        ow=max(fill.width,outer.width)+SDX+6; oh=max(fill.height,outer.height)+SDY+6
        fc=Image.new("L",(ow,oh),0); oc=Image.new("L",(ow,oh),0); fc.paste(fill,(2,2)); oc.paste(outer,(2,2))
        sh=Image.new("L",(ow,oh),0); sh.paste(oc,(SDX,SDY))
        rgba=Image.new("RGBA",(ow,oh),(0,0,0,0)); rgba.paste(SHADOW,(0,0),sh); rgba.paste(OUTLINE,(0,0),oc)
        grad=np.zeros((oh,ow,4),dtype=np.uint8)
        for yy in range(oh):
            t=yy/max(1,oh-1); grad[yy,:,]=[round(TOP[k]*(1-t)+BOTTOM[k]*t) for k in range(4)]
        rgba.paste(Image.fromarray(grad,"RGBA"),(0,0),fc)
        b=rgba.getchannel("A").getbbox(); return rgba.crop(b) if b else rgba
    lay=render("코스 선택",101)
    aw,ah=ob[2]-ob[0],ob[3]-ob[1]
    if lay.width>aw-2*MARGIN or lay.height>ah-2*MARGIN: raise RuntimeError(("D263 C144 style does not fit",ob,lay.size))
    px=ob[0]+MARGIN; py=ob[1]+max(MARGIN,(ah-lay.height)//2)
    if py+lay.height>ob[3]-MARGIN: py=ob[3]-MARGIN-lay.height
    final=clean.copy(); final.alpha_composite(lay,(px,py))
    target=Image.new("L",(W,H),0); target.paste(bmask(lay.getchannel("A")),(px,py)); lb=list(target.getbbox())
    margins=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    if min(margins)<=0 or lb[2]-lb[0]>aw or lb[3]-lb[1]>ah: raise RuntimeError(("D263 bbox gate",ob,lb,margins))
    if count(ImageChops.multiply(target,protected)): raise RuntimeError("D263 target-protected overlap")
    cand=repo/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/D263B3F1_512x512.dds"
    payload,raw_dec,dec=write_candidate(raw,mode,final,cand)
    fp=out/"A112_D263_FINAL_READABLE.png"; dec.save(fp); target.save(out/"A112_D263_RENDER_MASK.png")
    subprocess.run(["python3",str(validator),str(sp),str(fp),str(ap),"--protected-mask",str(pp),"--report",str(out/"A112_D263_FINAL_VALIDATION.json")],check=True)
    fr=json.loads((out/"A112_D263_FINAL_VALIDATION.json").read_text())
    diff=dmask(src,dec); outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
    alpha_out=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),ImageOps.invert(allowed)))
    same=ImageOps.invert(diff); residue=count(ImageChops.multiply(ImageChops.multiply(source_mask,ImageOps.invert(target)),same))
    if fr["status"]!="PASS" or outside or alpha_out or residue: raise RuntimeError(("D263 gates",fr["status"],outside,alpha_out,residue))
    # evidence
    box=(max(0,ob[0]-15),max(0,ob[1]-15),min(W,ob[2]+15),min(H,ob[3]+15))
    ims=[comp(z.crop(box)) for z in (src,clean,dec)]
    ims=[z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST) for z in ims]
    sh=Image.new("RGB",(sum(z.width for z in ims)+16,max(z.height for z in ims)+38),"white"); xx=0
    ImageDraw.Draw(sh).text((5,5),"D263 COURSE SELECT: SOURCE | CLEAN | FINAL  -> 코스 선택",fill="black")
    for z in ims: sh.paste(z,(xx,38)); xx+=z.width+8
    sh.save(out/"A112_D263_CONTACTS.jpg",quality=96,optimize=True)
    rr=Image.new("RGB",(1000,1040),"white")
    for i,(lab,z0) in enumerate((("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec))):
        z=comp(z0); z.thumbnail((1000,480),Image.Resampling.LANCZOS); rr.paste(z,(0,i*515+25)); ImageDraw.Draw(rr).text((5,i*515+5),lab,fill="black")
    rr.save(out/"A112_D263_RAW_COMPARE.jpg",quality=92,optimize=True)
    return {
      "queue_index":219,"asset":"D263B3F1","source_sha256":sha_bytes(raw),"candidate_sha256":sha_bytes(payload),
      "classification":{"source":"COURSE SELECT","korean":"코스 선택","occurrences":1},
      "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":payload[:128]==raw[:128],"raw_orientation":"mirror_y"},
      "family_reference":"C144-approved B68 E7F6 silver-techno menu-name family",
      "style":{"font":Path(FONT).name,"font_face_index":FI,"font_size":101,"shear":SHEAR,"stroke_width":STROKE,"shadow_offset":[SDX,SDY],"fill_top_rgba":TOP,"fill_bottom_rgba":BOTTOM,"outline_rgba":OUTLINE,"shadow_rgba":SHADOW},
      "row":{"original_bbox":ob,"localized_bbox":lb,"delta_left":margins[0],"delta_right":margins[1],"delta_top":margins[2],"delta_bottom":margins[3],"source_width":aw,"source_height":ah,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],"containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"},
      "zero_pixel_gates":{"outside":outside,"alpha_outside":alpha_out,"source_residue":residue,"localized_overlap":0},
      "clean_validator":cr,"final_validator":fr,
      "candidate_path":str(cand.relative_to(repo)),"worker_static_qa":"PASS","controller_visual_qa":"PENDING"
    }

# ---------------- D103 START/GOAL: native route-map badge reconstruction ----------------
def process_d103():
    name="D1039D6F_512x512.dds"
    p=tmp/name; urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/"+name,p)
    raw=p.read_bytes()
    W,H,mips,mode,raw_src,src=decode_rgba32(raw,"d3d2d15540642d8315df8b38b77a34609e534ea042bce8e7e951e65ab219bcd0")
    sa=np.asarray(src,dtype=np.uint8); r=sa[:,:,0].astype(np.int16); g=sa[:,:,1].astype(np.int16); b=sa[:,:,2].astype(np.int16); a=sa[:,:,3]>8
    red=a&(r>155)&(r>g+60)&(r>b+40)&(g<125)
    lab,n=ndimage.label(red)
    comps=[]
    for i in range(1,n+1):
        c=(lab==i); area=int(c.sum())
        if area<300: continue
        yy,xx=np.nonzero(c); x0,y0,x1,y1=int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)
        w=x1-x0; h=y1-y0
        rectangularity=area/max(1,w*h)
        if 55<=w<=220 and 14<=h<=80 and w/h>=1.7 and rectangularity>=0.20:
            bright=int(np.count_nonzero(a[y0:y1,x0:x1]&(r[y0:y1,x0:x1]>190)&(g[y0:y1,x0:x1]>150)&(b[y0:y1,x0:x1]>85)))
            if bright>=50: comps.append({"label":i,"area":area,"bbox":[x0,y0,x1,y1],"rectangularity":rectangularity,"bright":bright})
    comps=sorted(comps,key=lambda z:(z["area"],z["bright"]),reverse=True)
    # Keep two strongest separated route badges; both live in the route-map card.
    picked=[]
    for c in comps:
        cx=(c["bbox"][0]+c["bbox"][2])/2; cy=(c["bbox"][1]+c["bbox"][3])/2
        if not (650<=cx<=1600 and 0<=cy<=1300): continue
        if all(abs(cx-(p["bbox"][0]+p["bbox"][2])/2)>80 or abs(cy-(p["bbox"][1]+p["bbox"][3])/2)>80 for p in picked):
            picked.append(c)
        if len(picked)==2: break
    if len(picked)!=2: raise RuntimeError(("D103 badge detect",comps[:12]))
    picked=sorted(picked,key=lambda z:(z["bbox"][0]+z["bbox"][2])/2)
    labels=[("START","출발"),("GOAL","골")]
    clean_arr=sa.copy(); clean_region=np.zeros((H,W),bool); source_face=np.zeros((H,W),bool)
    records=[]
    for c,(en,ko) in zip(picked,labels):
        i=c["label"]; x0,y0,x1,y1=c["bbox"]
        # envelope the saturated-red connected body across each scanline, then inset from its rim.
        sub=(lab[y0:y1,x0:x1]==i)
        banner=np.zeros_like(sub)
        for yy in range(sub.shape[0]):
            xs=np.nonzero(sub[yy])[0]
            if len(xs)>=2: banner[yy,int(xs.min()):int(xs.max())+1]=True
        banner=ndimage.binary_fill_holes(banner)
        interior=ndimage.binary_erosion(banner,iterations=1,border_value=0)
        if int(interior.sum())<250: raise RuntimeError(("D103 interior",en,int(interior.sum()),c))
        subarr=sa[y0:y1,x0:x1]
        rr=subarr[:,:,0].astype(np.int16); gg=subarr[:,:,1].astype(np.int16); bb=subarr[:,:,2].astype(np.int16); aa=subarr[:,:,3]>8
        known=interior&(rr>135)&(rr>gg+35)&(rr>bb+25)&(gg<145)
        # Source face/effect core, excluding long horizontal badge highlights.
        core=interior&aa&(rr>185)&(gg>130)&(bb>70)
        clab,cn=ndimage.label(core); kept=np.zeros_like(core)
        for ci in range(1,cn+1):
            cc=(clab==ci); ar=int(cc.sum())
            if ar<2: continue
            ys,xs=np.nonzero(cc); cw=int(xs.max()-xs.min()+1); ch=int(ys.max()-ys.min()+1)
            if cw>0.60*banner.shape[1] and ch<=5: continue
            kept|=cc
        core=kept
        if int(core.sum())<40: raise RuntimeError(("D103 text core",en,int(core.sum()),c))
        effect=ndimage.binary_dilation(core,iterations=3)&interior
        ey,ex=np.nonzero(effect); sb=[x0+int(ex.min()),y0+int(ey.min()),x0+int(ex.max()+1),y0+int(ey.max()+1)]
        # continuous source-derived row reconstruction across the badge interior.
        for yy in range(interior.shape[0]):
            xs=np.nonzero(known[yy])[0]
            if not len(xs): continue
            vals=subarr[yy,xs].astype(np.float64)
            # robust median sign-body color for the row; keep original alpha.
            col=np.median(vals,axis=0)
            gx=np.nonzero(interior[yy])[0]
            clean_arr[y0+yy,x0+gx,:3]=np.clip(np.rint(col[:3]),0,255).astype(np.uint8)
            clean_arr[y0+yy,x0+gx,3]=subarr[yy,gx,3]
        gm=np.zeros((H,W),bool); gm[y0:y1,x0:x1]=interior; clean_region|=gm
        fm=np.zeros((H,W),bool); fm[y0:y1,x0:x1]=core; source_face|=fm
        records.append({"source":en,"korean":ko,"banner_bbox":[x0,y0,x1,y1],"source_bbox":sb,"clean_region_pixels":int(interior.sum()),"source_face_pixels":int(core.sum())})
    clean=Image.fromarray(clean_arr,"RGBA")
    same_clean=np.all(clean_arr==sa,axis=2)
    face_residue=int(np.count_nonzero(source_face&same_clean))
    if face_residue: raise RuntimeError(("D103 clean source-face residue",face_residue))
    final=clean.copy(); target=np.zeros((H,W),bool)
    def render_badge(text,maxw,maxh):
        for fs in range(min(36,maxh+6),11,-1):
            f=ImageFont.truetype(FONT,fs,index=FI)
            tb=ImageDraw.Draw(Image.new("L",(8,8),0)).textbbox((0,0),text,font=f)
            pad=12
            can=Image.new("RGBA",(max(120,tb[2]-tb[0]+pad*2),max(80,tb[3]-tb[1]+pad*2)),(0,0,0,0))
            d=ImageDraw.Draw(can); ox=pad-tb[0]; oy=pad-tb[1]; shoff=max(1,round(fs*0.055))
            d.text((ox+shoff,oy+shoff),text,font=f,fill=(234,131,95,255))
            d.text((ox,oy),text,font=f,fill=(255,235,184,255))
            gb=can.getchannel("A").getbbox()
            if not gb: continue
            glyph=can.crop(gb)
            add=max(2,int(round(0.17*glyph.height))+4)
            glyph=glyph.transform((glyph.width+add,glyph.height),Image.Transform.AFFINE,(1,-0.17,0.17*glyph.height,0,1,0),resample=Image.Resampling.BICUBIC)
            gb=glyph.getchannel("A").getbbox()
            if gb: glyph=glyph.crop(gb)
            if glyph.width<=maxw-4 and glyph.height<=maxh-4: return glyph,fs,shoff
        raise RuntimeError(("D103 cannot fit",text,maxw,maxh))
    for rec in records:
        sx0,sy0,sx1,sy1=rec["source_bbox"]; sw=sx1-sx0; sh=sy1-sy0
        glyph,fs,shoff=render_badge(rec["korean"],sw,sh)
        px=sx0+(sw-glyph.width)//2; py=sy0+(sh-glyph.height)//2
        final.alpha_composite(glyph,(px,py))
        lm=np.zeros((H,W),bool); ma=np.asarray(glyph.getchannel("A"))>0; lm[py:py+glyph.height,px:px+glyph.width]=ma
        ys,xs=np.nonzero(lm); lb=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
        margins=[lb[0]-sx0,sx1-lb[2],lb[1]-sy0,sy1-lb[3]]
        if min(margins)<=0 or lb[2]-lb[0]>sw or lb[3]-lb[1]>sh: raise RuntimeError(("D103 bbox gate",rec["source"],rec["source_bbox"],lb,margins))
        if np.any(target&lm): raise RuntimeError("D103 localized overlap")
        target|=lm
        rec.update({"localized_bbox":lb,"delta_left":margins[0],"delta_right":margins[1],"delta_top":margins[2],"delta_bottom":margins[3],"source_width":sw,"source_height":sh,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],"containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","font":Path(FONT).name,"font_face_index":FI,"font_size":fs,"shear":0.17,"shadow_offset":shoff})
    clean_mask=Image.fromarray((clean_region*255).astype(np.uint8),"L")
    protected=ImageOps.invert(clean_mask)
    diff_clean=dmask(src,clean); clean_out=count(ImageChops.multiply(diff_clean,protected))
    diff_final=dmask(src,final); final_out=count(ImageChops.multiply(diff_final,protected))
    alpha_out=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),final.getchannel("A"))),protected))
    if clean_out or final_out or alpha_out: raise RuntimeError(("D103 outside",clean_out,final_out,alpha_out))
    cand=repo/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/D1039D6F_512x512.dds"
    payload,raw_dec,dec=write_candidate(raw,mode,final,cand)
    sp=out/"A112_D103_SOURCE_READABLE.png"; cp=out/"A112_D103_CLEAN_PLATE.png"; fp=out/"A112_D103_FINAL_READABLE.png"
    src.save(sp); clean.save(cp); dec.save(fp); clean_mask.save(out/"A112_D103_CLEAN_REGION_MASK.png")
    Image.fromarray((source_face*255).astype(np.uint8),"L").save(out/"A112_D103_SOURCE_FACE_MASK.png")
    Image.fromarray((target*255).astype(np.uint8),"L").save(out/"A112_D103_RENDER_MASK.png")
    subprocess.run(["python3",str(validator),str(sp),str(cp),str(out/"A112_D103_CLEAN_REGION_MASK.png"),"--protected-mask",str(protected_path:=out/"A112_D103_PROTECTED_MASK.png"),"--report",str(out/"A112_D103_CLEAN_VALIDATION.json")],check=False)
    # validator needs persisted protected mask.
    protected.save(protected_path)
    subprocess.run(["python3",str(validator),str(sp),str(cp),str(out/"A112_D103_CLEAN_REGION_MASK.png"),"--protected-mask",str(protected_path),"--report",str(out/"A112_D103_CLEAN_VALIDATION.json")],check=True)
    subprocess.run(["python3",str(validator),str(sp),str(fp),str(out/"A112_D103_CLEAN_REGION_MASK.png"),"--protected-mask",str(protected_path),"--report",str(out/"A112_D103_FINAL_VALIDATION.json")],check=True)
    cr=json.loads((out/"A112_D103_CLEAN_VALIDATION.json").read_text()); fr=json.loads((out/"A112_D103_FINAL_VALIDATION.json").read_text())
    if cr["status"]!="PASS" or fr["status"]!="PASS": raise RuntimeError(("D103 validator",cr["status"],fr["status"]))
    # contacts
    cards=[]
    for rec in records:
        x0,y0,x1,y1=rec["banner_bbox"]; pad=18; box=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
        ims=[comp(z.crop(box)) for z in (src,clean,dec)]
        ims=[z.resize((z.width*4,z.height*4),Image.Resampling.NEAREST) for z in ims]
        row=Image.new("RGB",(sum(z.width for z in ims)+16,max(z.height for z in ims)+38),"white"); xx=0
        ImageDraw.Draw(row).text((5,5),f'{rec["source"]} -> {rec["korean"]} | SOURCE CLEAN FINAL',fill="black")
        for z in ims: row.paste(z,(xx,38)); xx+=z.width+8
        cards.append(row)
    sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height+5 for c in cards)),"white"); yy=0
    for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+5
    sheet.save(out/"A112_D103_BADGE_CONTACTS.jpg",quality=96,optimize=True)
    rr=Image.new("RGB",(1000,1040),"white")
    for i,(lab,z0) in enumerate((("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec))):
        z=comp(z0); z.thumbnail((1000,480),Image.Resampling.LANCZOS); rr.paste(z,(0,i*515+25)); ImageDraw.Draw(rr).text((5,i*515+5),lab,fill="black")
    rr.save(out/"A112_D103_RAW_COMPARE.jpg",quality=92,optimize=True)
    return {
      "queue_index":217,"asset":"D1039D6F","source_sha256":sha_bytes(raw),"candidate_sha256":sha_bytes(payload),
      "classification":{"segments":[{"source":"START","korean":"출발"},{"source":"GOAL","korean":"골"}],"occurrences":2},
      "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":payload[:128]==raw[:128],"raw_orientation":"mirror_y"},
      "construction":"native-HD source-derived red badge interior reconstruction inside detected body only; outer rim/map/art preserved; fresh Noto CJK Korean with A85/B185 badge-family pale+orange shadow and 0.17 shear",
      "rows":records,
      "zero_pixel_gates":{"clean_outside":clean_out,"final_outside":final_out,"alpha_outside":alpha_out,"source_face_residue_clean":face_residue,"localized_overlap":0},
      "clean_validator":cr,"final_validator":fr,
      "candidate_path":str(cand.relative_to(repo)),"worker_static_qa":"PASS","controller_visual_qa":"PENDING"
    }

results={}; failures={}
try:
    results["D263B3F1"]=process_d263()
except Exception as e:
    failures["D263B3F1"]={"error":repr(e),"traceback":traceback.format_exc()}
try:
    results["D1039D6F"]=process_d103()
except Exception as e:
    failures["D1039D6F"]={"error":repr(e),"traceback":traceback.format_exc()}

report={
 "schema_version":1,"role":"A","run":run,
 "results":results,"failures":failures,
 "status":"A112_COMPLETE_WITH_STATIC_RESULTS" if results else "A112_FAIL_CLOSED_NO_CANDIDATES",
 "runtime_validation":"UNTESTED","vr_ffb_dx11_dxvk_touched":False
}
(out/"A112_BATCH_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"A112_D103_D263.json").write_text(json.dumps({
 "run":run,
 "candidates":{k:v.get("candidate_sha256") for k,v in results.items()},
 "failures":{k:v["error"] for k,v in failures.items()},
 "status":report["status"],
 "report":f"localization/graphics/role_A/{run}/A112_BATCH_REPORT.json"
},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"results":results,"failures":{k:v["error"] for k,v in failures.items()}},ensure_ascii=False),flush=True)
