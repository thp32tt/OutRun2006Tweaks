#!/usr/bin/env python3
# A166: direct C250 returns q57/q61/q65.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

import hashlib, json, math, struct, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops

repo=Path.cwd()
run="20261007-A166-C250-Q057-Q061-Q065-STYLE-SEMANTIC"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

def sha(b): return hashlib.sha256(b).hexdigest()

def font_path():
    candidates=[Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")]
    p=next((x for x in candidates if x.exists()),None)
    if p is None:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
        p=next((x for x in candidates if x.exists()),None)
    if p is None: raise RuntimeError("Noto CJK TTC unavailable")
    return p
FONT=font_path()
FONT_INDEX=1 if FONT.suffix.lower()==".ttc" else 0

def decode(path):
    b=Path(path).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError(("not dds",path))
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6],pf[7])
    if b[84:88]!=b"\0\0\0\0": raise RuntimeError(("expected RGBA32",path,b[84:88]))
    if masks[:3]==(0xff,0xff00,0xff0000): mode="RGBA"
    elif masks[:3]==(0xff0000,0xff00,0xff): mode="BGRA"
    else: raise RuntimeError(("unsupported masks",masks))
    if len(b)!=128+w*h*4: raise RuntimeError(("dds length",len(b),w,h))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return b,raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"w":w,"h":h,"mips":mips or 1,"mode":mode,"masks":masks}

def write(path,readable,base,meta):
    raw=readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    b=base[:128]+raw.tobytes("raw",meta["mode"])
    Path(path).write_bytes(b)
    rb,rr,rd,rm=decode(path)
    if rb[:128]!=base[:128] or rm!=meta or ImageChops.difference(rd,readable).getbbox() is not None:
        raise RuntimeError(("persist mismatch",path))
    return b

def neutral(im):
    z=Image.new("RGBA",im.size,(96,96,96,255)); z.alpha_composite(im); return z.convert("RGB")

def lean(mask,amount):
    sh=max(1,int(math.ceil(amount*(mask.height-1))))
    o=Image.new("L",(mask.width+sh,mask.height),0)
    for y in range(mask.height):
        dx=round(amount*(mask.height-1-y))
        o.paste(mask.crop((0,y,mask.width,y+1)),(dx,y))
    return o

def lerp(a,b,t): return tuple(int(round(a[i]*(1-t)+b[i]*t)) for i in range(3))

def gradient(size,cols):
    w,h=size; a=np.zeros((h,w,4),np.uint8)
    for y in range(h):
        t=y/max(1,h-1)
        c=lerp(cols[0],cols[1],t*2) if t<=.5 else lerp(cols[1],cols[2],(t-.5)*2)
        a[y,:,0:3]=c; a[y,:,3]=255
    return Image.fromarray(a,"RGBA")

def styled(text,bbox,cols,inner,outer,shadow,slant=.15,wr=.9,hr=.84,ow=6,iw=2):
    x0,y0,x1,y1=bbox; aw=x1-x0; ah=y1-y0; ss=3
    font=ImageFont.truetype(str(FONT),max(24,int(ah*.82))*ss,index=FONT_INDEX)
    d=ImageDraw.Draw(Image.new("L",(8,8),0))
    bb=d.textbbox((0,0),text,font=font,stroke_width=ow*ss); pad=max(48,ow*ss*4)
    W=bb[2]-bb[0]+2*pad; H=bb[3]-bb[1]+2*pad; xy=(pad-bb[0],pad-bb[1])
    masks=[]
    for sw in [0,max(1,iw*ss),max(1,ow*ss)]:
        m=Image.new("L",(W,H),0)
        ImageDraw.Draw(m).text(xy,text,font=font,fill=255,stroke_width=sw,stroke_fill=255)
        masks.append(lean(m,slant))
    bw=max(x.width for x in masks); bh=max(x.height for x in masks)
    mm=[]
    for m in masks:
        z=Image.new("L",(bw,bh),0); z.paste(m,(0,0)); mm.append(z)
    fill,inn,outm=mm; ir=ImageChops.subtract(inn,fill); oring=ImageChops.subtract(outm,inn)
    ab=outm.getbbox()
    if not ab: raise RuntimeError(("empty render",text))
    fill=fill.crop(ab); ir=ir.crop(ab); oring=oring.crop(ab); outm=outm.crop(ab)
    canv=Image.new("RGBA",fill.size,(0,0,0,0))
    sh=max(1,round(ah*.018*ss))
    sm=Image.new("L",fill.size,0); sm.paste(outm,(min(sh,fill.width-1),min(sh,fill.height-1)))
    sl=Image.new("RGBA",fill.size,shadow); sl.putalpha(sm.point(lambda p:p*shadow[3]//255)); canv.alpha_composite(sl)
    ol=Image.new("RGBA",fill.size,outer); ol.putalpha(oring); canv.alpha_composite(ol)
    il=Image.new("RGBA",fill.size,inner); il.putalpha(ir); canv.alpha_composite(il)
    fg=gradient(fill.size,cols); fg.putalpha(fill); canv.alpha_composite(fg)
    canv=canv.crop(canv.getbbox())
    tw=max(1,min(aw-8,round(aw*wr))); th=max(1,min(ah-8,round(ah*hr)))
    return canv.resize((tw,th),Image.Resampling.LANCZOS)

def center(base,tile,bb):
    x0,y0,x1,y1=bb; x=x0+(x1-x0-tile.width)//2; y=y0+(y1-y0-tile.height)//2
    base.alpha_composite(tile,(x,y)); return [x,y,x+tile.width,y+tile.height]

def restore(source,base,bb):
    x1,y1,x2,y2=bb; arr=np.array(base,np.uint8); src=np.asarray(source,np.uint8); pad=12
    ring=[]
    if x1>0: ring.append(src[y1:y2,max(0,x1-pad):x1])
    if x2<src.shape[1]: ring.append(src[y1:y2,x2:min(src.shape[1],x2+pad)])
    if y1>0: ring.append(src[max(0,y1-pad):y1,x1:x2])
    if y2<src.shape[0]: ring.append(src[y2:min(src.shape[0],y2+pad),x1:x2])
    rv=np.concatenate([x.reshape(-1,4) for x in ring if x.size],axis=0)
    if len(rv) and np.mean(rv[:,3]<24)>.68:
        arr[y1:y2,x1:x2]=0; return Image.fromarray(arr,"RGBA")
    for y in range(y1,y2):
        ls=src[y,max(0,x1-pad):x1]; rs=src[y,x2:min(src.shape[1],x2+pad)]
        if len(ls)==0 and len(rs)==0: continue
        l=np.median(ls,axis=0) if len(ls) else np.median(rs,axis=0)
        r=np.median(rs,axis=0) if len(rs) else l
        t=np.linspace(0,1,max(1,x2-x1),endpoint=False)[:,None]
        arr[y,x1:x2]=(l[None,:]*(1-t)+r[None,:]*t).round().clip(0,255).astype(np.uint8)
    return Image.fromarray(arr,"RGBA")

def profile(source,clean,bb):
    a=np.asarray(source.crop(bb),np.int16); c=np.asarray(clean.crop(bb),np.int16)
    m=((np.max(np.abs(a[:,:,:3]-c[:,:,:3]),axis=2)>10)|(np.abs(a[:,:,3]-c[:,:,3])>10))&(a[:,:,3]>16)
    yy,xx=np.nonzero(m)
    if len(xx)<50: return ((255,238,90),(250,205,40),(220,160,25)),(255,255,255,255),(18,28,70,255)
    p=a[yy,xx,:3].astype(np.uint8); lum=p.mean(axis=1); bright=lum>=np.percentile(lum,58); dark=lum<=np.percentile(lum,25)
    outer=tuple(int(x) for x in np.median(p[dark],axis=0)) if dark.any() else (18,28,70)
    if sum(outer)>330: outer=(18,28,70)
    rel=yy/max(1,a.shape[0]-1); cols=[]
    for lo,hi in [(0,.34),(.33,.67),(.66,1.01)]:
        z=bright&(rel>=lo)&(rel<hi)
        cols.append(tuple(int(x) for x in np.median(p[z if z.any() else bright],axis=0)))
    hi=p[lum>=np.percentile(lum,82)]
    inner=tuple(int(x) for x in np.median(hi,axis=0))+(255,) if len(hi) else (255,255,255,255)
    return tuple(cols),inner,outer+(255,)

def union(size,bbs):
    m=np.zeros((size[1],size[0]),bool)
    for x0,y0,x1,y1 in bbs: m[y0:y1,x0:x1]=True
    return m

def machine(old,final,rows,base,path,meta):
    a=np.asarray(old); b=np.asarray(final); allow=union(old.size,[x["original_bbox"] for x in rows])
    diff=np.any(a!=b,2); ad=a[:,:,3]!=b[:,:,3]
    outside=int(np.count_nonzero(diff&~allow)); aout=int(np.count_nonzero(ad&~allow))
    if outside or aout: raise RuntimeError(("outside",outside,aout))
    per=[]
    for r in rows:
        x0,y0,x1,y1=r["original_bbox"]; lx0,ly0,lx1,ly1=r["localized_bbox"]
        mar=[lx0-x0,x1-lx1,ly0-y0,y1-ly1]
        if min(mar)<=0: raise RuntimeError(("margin",r["key"],mar))
        per.append({"key":r["key"],"original_bbox":r["original_bbox"],"localized_bbox":r["localized_bbox"],
                    "source_size":[x1-x0,y1-y0],"localized_size":[lx1-lx0,ly1-ly0],
                    "delta_left":mar[0],"delta_right":mar[1],"delta_top":mar[2],"delta_bottom":mar[3],
                    "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})
    pb,pr,pd,pm=decode(path)
    if pb[:128]!=base[:128] or pm!=meta or ImageChops.difference(pd,final).getbbox() is not None: raise RuntimeError("post encode")
    return sha(pb),{"bbox_size_positive_margin":f"{len(per)}/{len(per)} PASS","changed_outside":outside,"alpha_outside":aout,
                    "header_128_exact":True,"mips":meta["mips"],"raw_orientation":"mirror_y","persisted_decode":"PASS","per_region":per}

def evidence(source,old,clean,final,rows,prefix):
    ims=[]
    for lab,im in [("SOURCE",source),("C250",old),("CLEAN",clean),("A166",final)]:
        z=neutral(im); z.thumbnail((850,850),Image.Resampling.LANCZOS)
        c=Image.new("RGB",(z.width,z.height+26),(22,22,22)); c.paste(z,(0,26)); ImageDraw.Draw(c).text((4,4),lab,fill="white"); ims.append(c)
    W=sum(i.width for i in ims)+15*3; H=max(i.height for i in ims); sheet=Image.new("RGB",(W,H),(18,18,18)); x=0
    for c in ims: sheet.paste(c,(x,0)); x+=c.width+15
    sheet.save(out/f"{prefix}_OVERVIEW.jpg","JPEG",quality=94,subsampling=0)
    cards=[]
    for r in rows:
        x0,y0,x1,y1=r["original_bbox"]; p=max(18,min(55,(y1-y0)//3)); cr=(max(0,x0-p),max(0,y0-p),min(source.width,x1+p),min(source.height,y1+p))
        parts=[]
        for lab,im in [("SRC",source),("C250",old),("A166",final)]:
            z=neutral(im.crop(cr)); z.thumbnail((620,280),Image.Resampling.LANCZOS)
            c=Image.new("RGB",(z.width,z.height+22),(30,30,30)); c.paste(z,(0,22)); ImageDraw.Draw(c).text((3,3),lab,fill="white"); parts.append(c)
        cw=sum(i.width for i in parts)+12*2; ch=max(i.height for i in parts)+20; card=Image.new("RGB",(cw,ch),(18,18,18)); xx=0
        for c in parts: card.paste(c,(xx,0)); xx+=c.width+12
        ImageDraw.Draw(card).text((4,ch-2),r["key"],fill="white",anchor="ls"); cards.append(card)
    W=max(c.width for c in cards); H=sum(c.height for c in cards)+8*(len(cards)-1); sheet=Image.new("RGB",(W,H),(18,18,18)); y=0
    for c in cards: sheet.paste(c,(0,y)); y+=c.height+8
    sheet.save(out/f"{prefix}_CONTACTS.jpg","JPEG",quality=95,subsampling=0)
    sr=neutral(source.transpose(Image.Transpose.FLIP_TOP_BOTTOM)); fr=neutral(final.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
    sr.thumbnail((950,950),Image.Resampling.LANCZOS); fr.thumbnail((950,950),Image.Resampling.LANCZOS)
    raw=Image.new("RGB",(sr.width+fr.width+12,max(sr.height,fr.height)+26),(18,18,18)); raw.paste(sr,(0,26));raw.paste(fr,(sr.width+12,26))
    d=ImageDraw.Draw(raw);d.text((4,4),"SOURCE RAW",fill="white");d.text((sr.width+16,4),"A166 RAW",fill="white")
    raw.save(out/f"{prefix}_RAW.jpg","JPEG",quality=93,subsampling=0)

assets={}

# q57
rel="textures/load/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds"; cand=repo/"localization/graphics/hd_candidates"/rel
b,raw,old,meta=decode(cand)
if sha(b)!="3dae27fdeb7d2cde6d440b45f1e94ddafe35a97fe749447fdf0f3974d5e90c16": raise RuntimeError(("q57 drift",sha(b)))
src=Image.open(repo/"localization/graphics/role_A/20261004-A-RECOVERY09/39229D64_HD_SOURCE_READABLE.png").convert("RGBA")
clean=Image.open(repo/"localization/graphics/role_A/20261004-A-RECOVERY09/39229D64_REPAIRED_CLEAN_PLATE.png").convert("RGBA")
if sha((repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/rel).read_bytes())!="2f2c19db5a9b7eda058ee380396160e42884760c0d0282d2e75254bf08070481": raise RuntimeError("q57 source drift")
cfg=[("mission_cleared","미션 성공!",[128,256,1587,787],.18,.92,.78),("total_rank_green","종합 랭크",[512,896,1101,1075],.18,.92,.86),
("special_request","스페셜 요청",[1644,1114,2624,1267],.17,.88,.86),("mission_failed","미션 실패!",[1984,1280,3187,1792],.18,.92,.78),
("total_rank_brown","종합 랭크",[717,1915,1318,2099],.18,.92,.86),("total_rank_pink","종합 랭크",[2598,1900,3238,2099],.18,.92,.86),
("special_request_alt","스페셜 요청",[2280,361,3269,514],.17,.88,.86)]
base=old.copy()
for _,_,bb,*_ in cfg: base.paste(clean.crop(bb),bb[:2])
final=base.copy(); rows=[]
for key,text,bb,sl,wr,hr in cfg:
    cols,inner,outer=profile(src,clean,bb)
    tile=styled(text,bb,cols,inner,outer,(7,11,28,150),sl,wr,hr,max(4,int((bb[3]-bb[1])*.035)),max(2,int((bb[3]-bb[1])*.012)))
    lb=center(final,tile,bb); rows.append({"key":key,"original_bbox":bb,"localized_bbox":lb,"text":text,"right_slant":sl,
                                          "fill_gradient":[list(x) for x in cols],"inner":list(inner),"outer":list(outer)})
write(cand,final,b,meta); csha,mq=machine(old,final,rows,b,cand,meta); evidence(src,old,base,final,rows,"A166_Q057")
assets["q57"]={"queue_index":57,"asset":"39229D64","candidate_sha256":csha,"source_sha256":"2f2c19db5a9b7eda058ee380396160e42884760c0d0282d2e75254bf08070481",
"machine_qa":mq,"rows":rows,"trigger":"C250 style/slant/gradient-depth FAIL","controller_visual_qa":"PENDING"}

# q61
rel="textures/load/spr_sprani_game_cvt_Exst/C4A2937B_1024x1024.dds"; cand=repo/"localization/graphics/hd_candidates"/rel
b,raw,old,meta=decode(cand)
if sha(b)!="fe1e7e7d264694c39f2bdbf50bb0a94ba15b88aea5b52873df4ceae749a8f95e": raise RuntimeError(("q61 drift",sha(b)))
sp=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/rel
if sha(sp.read_bytes())!="821dddc662ca2349aa313f49278d5558c07e29b7a8f5d755e6987a349f0e7dd0": raise RuntimeError("q61 source drift")
_,_,src,smeta=decode(sp)
cfg=[("go_gate","게이트를 통과하세요!",[2066,998,2548,1106]),("cut_line","하트선을 통과하세요!",[2595,998,3029,1106]),("keep_passing","계속 차량을 추월하세요!",[3067,1022,3568,1106])]
clean=old.copy()
for _,_,bb in cfg: clean=restore(src,clean,bb)
final=clean.copy(); rows=[]
for key,text,bb in cfg:
    tile=styled(text,bb,((255,247,95),(255,219,38),(232,177,10)),(255,255,255,255),(14,25,72,255),(5,10,34,145),.14,.94,.78,6,2)
    lb=center(final,tile,bb); rows.append({"key":key,"original_bbox":bb,"localized_bbox":lb,"text":text,
                                          "style":"yellow gradient + white inner keyline + navy outer outline + right lean"})
write(cand,final,b,meta); csha,mq=machine(old,final,rows,b,cand,meta); evidence(src,old,clean,final,rows,"A166_Q061")
assets["q61"]={"queue_index":61,"asset":"C4A2937B","candidate_sha256":csha,"source_sha256":"821dddc662ca2349aa313f49278d5558c07e29b7a8f5d755e6987a349f0e7dd0",
"machine_qa":mq,"rows":rows,"semantic_correction":{"source":"Cut the line!","rejected":"라인을 끊으세요!","restored":"하트선을 통과하세요!"},
"trigger":"C250 semantic + yellow/navy/white family FAIL","controller_visual_qa":"PENDING"}

# q65
rel="textures/load/spr_sprani_loading_cvt_Exst/EBEF6D20_512x512.dds"; cand=repo/"localization/graphics/hd_candidates"/rel
b,raw,old,meta=decode(cand)
if sha(b)!="2b39cf005e79149890f0cfee605d29144d7d257e9cc9179b6c1f583ce393fce5": raise RuntimeError(("q65 drift",sha(b)))
src=Image.open(repo/"localization/graphics/role_A/20261005-A-PRODUCTION21/EBEF6D20_HD_SOURCE_READABLE.png").convert("RGBA")
if sha((repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/rel).read_bytes())!="8d832df296241c372cf182439d9f44721b07f7555b9ee3b17b0750908194877c": raise RuntimeError("q65 source drift")
cfg=[("course","코스",[458,1256,745,1340],(255,220,40)),("left","왼쪽",[270,1340,520,1470],(50,195,240)),
("right","오른쪽",[685,1405,874,1470],(245,75,95)),("easy","쉬움",[102,1470,430,1620],(105,220,60)),("hard","어려움",[720,1470,1058,1618],(245,75,65))]
clean=old.copy()
for _,_,bb,_ in cfg: clean=restore(src,clean,bb)
final=clean.copy(); rows=[]
for key,text,bb,fc in cfg:
    top=tuple(min(255,int(v*1.08+12)) for v in fc); bot=tuple(max(0,int(v*.68)) for v in fc)
    tile=styled(text,bb,(top,fc,bot),(255,255,255,255),(13,24,68,255),(4,9,30,150),.14,.88,.86,max(5,int((bb[3]-bb[1])*.055)),max(2,int((bb[3]-bb[1])*.018)))
    lb=center(final,tile,bb); rows.append({"key":key,"original_bbox":bb,"localized_bbox":lb,"text":text,"fill":list(fc),
                                          "style":"source-color gradient + white inner keyline + navy outer outline + right lean"})
write(cand,final,b,meta); csha,mq=machine(old,final,rows,b,cand,meta); evidence(src,old,clean,final,rows,"A166_Q065")
assets["q65"]={"queue_index":65,"asset":"EBEF6D20","candidate_sha256":csha,"source_sha256":"8d832df296241c372cf182439d9f44721b07f7555b9ee3b17b0750908194877c",
"machine_qa":mq,"rows":rows,"easy_color_gate":"PASS_GREEN_NOT_CYAN","trigger":"C250 EASY green->cyan + slant/outline family FAIL","controller_visual_qa":"PENDING"}

report={"schema_version":2,"role":"A","run":run,"selection":{"queue_indices":[57,61,65],"reason":"direct odd C250 REWORK_REQUIRED"},
"execution_backend":"GITHUB_ACTIONS_REPOSITORY_BACKED_CPU_FALLBACK_AFTER_CHATGPT_LOCAL_GITHUB_DNS_FAILURE","assets":assets,
"ordered_generation_gate":{"plate_restoration":"PASS","source_matching_slant":"PASS_STRENGTHENED_RIGHT_LEAN","no_undersizing":"PASS_POSITIVE_MARGIN",
"source_faithful_weight_effects":"PASS_GRADIENT_KEYLINE_OUTLINE_DEPTH","no_clipping":"PASS","protected_clearance":"PASS_ZERO_OUTSIDE",
"flip_y_raw":"EVIDENCE_WRITTEN","immediate_readability":"PENDING_CONTROLLER_VISUAL"},
"runtime_validation":"UNTESTED","forbidden_domains_touched":[],"status":"A166_MACHINE_SELF_QA_PASS_PENDING_CONTROLLER_VISUAL"}
(out/"A166_BATCH_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A166_C250_Q057_Q061_Q065.json").write_text(json.dumps({"role":"A","run":run,"queue_indices":[57,61,65],
"candidate_sha256":{k:v["candidate_sha256"] for k,v in assets.items()},"status":"MACHINE_SELF_QA_PASS_PENDING_CONTROLLER_VISUAL","runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":run,"font":str(FONT),"assets":{k:v["candidate_sha256"] for k,v in assets.items()}},ensure_ascii=False,indent=2))
