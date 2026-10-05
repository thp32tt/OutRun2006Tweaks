#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")
repo=Path.cwd(); run="20261005-A-PRODUCTION53"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/55B57CDE_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel; candidate.parent.mkdir(parents=True,exist_ok=True)
work=Path("/tmp/outrun_A53"); work.mkdir(parents=True,exist_ok=True)
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"; BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
source=work/"55B57CDE_HD.dds"; atlasp=work/"4x_55B57CDE_512x512_atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_sumo_fe_cvt_Exst/55B57CDE_512x512.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_55B57CDE_512x512_atlas.json",atlasp)

def blobsha(data): return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def flatten(im):
    z=Image.new("RGBA",im.size,(72,72,72,255)); z.alpha_composite(im); return z.convert("RGB")
def diffmask(a,b):
    d=ImageChops.difference(a,b); ps=d.split(); m=ps[0]
    for p in ps[1:]: m=ImageChops.lighter(m,p)
    return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])

sb=source.read_bytes(); ab=atlasp.read_bytes()
SOURCE_BLOB_SHA1=blobsha(sb); SOURCE_SHA256=hashlib.sha256(sb).hexdigest()
ATLAS_BLOB_SHA1=blobsha(ab); ATLAS_SHA256=hashlib.sha256(ab).hexdigest()
if SOURCE_BLOB_SHA1!="0b12c672224ce05acb9470af895bbda335cc5543": raise RuntimeError("source drift")
if ATLAS_BLOB_SHA1!="70001b44445f3e10b46eb7e3480abdece8eda790": raise RuntimeError("atlas drift")
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12); pf=struct.unpack_from("<8I",sb,76)
if (W,H,mips)!=(2048,2048,1) or len(sb)!=128+W*H*4 or pf[3]!=32: raise RuntimeError(("structure",W,H,pitch,mips,len(sb),pf))
rgbm=(pf[4],pf[5],pf[6]); RAWMODE="BGRA" if rgbm==(0xff0000,0xff00,0xff) else "RGBA" if rgbm==(0xff,0xff00,0xff0000) else None
if RAWMODE not in ("RGBA","BGRA"): raise RuntimeError(("rawmode",rgbm))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",RAWMODE); src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
atlas=json.loads(ab.decode("utf-8")); regs={int(r["idx"]):r for r in atlas["regions"]}
if len(regs)!=38: raise RuntimeError(("regions",len(regs)))

TARGETS={
0:("VIRGO","처녀자리"),1:("TAURUS","황소자리"),2:("SCORPIO","전갈자리"),3:("SAGITTARIUS","사수자리"),
4:("PISCES","물고기자리"),5:("LIBRA","천칭자리"),6:("LEO","사자자리"),7:("GEMINI","쌍둥이자리"),
8:("CAPRICORN","염소자리"),9:("CANCER","게자리"),10:("ARIES","양자리"),11:("AQUARIUS","물병자리"),
12:("THAILAND","태국"),13:("SWITZERLAND","스위스"),14:("SWEDEN","스웨덴"),15:("SPAIN","스페인"),
16:("SOUTH KOREA","대한민국"),17:("SINGAPORE","싱가포르"),18:("OTHER","기타"),19:("NORWAY","노르웨이"),
20:("NORTH KOREA","북한"),21:("NEW ZEALAND","뉴질랜드"),22:("MEXICO","멕시코"),23:("JAPAN","일본"),
24:("ITALY","이탈리아"),25:("HONG KONG","홍콩"),26:("GERMANY","독일"),27:("FRANCE","프랑스"),
28:("FINLAND","핀란드"),29:("NETHERLANDS","네덜란드"),30:("DENMARK","덴마크"),31:("CHINA","중국"),
32:("CANADA","캐나다"),33:("BRITAIN","영국"),34:("BELGIUM","벨기에"),35:("AUSTRIA","오스트리아"),
36:("AUSTRALIA","호주"),37:("USA","미국")
}

def resolve_font():
    for install in (False,True):
        for pat in ["Noto Sans CJK KR:style=Bold","Noto Sans CJK KR:style=Black","Noto Sans CJK KR"]:
            try: spec=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
            except Exception: spec=""
            if "|" in spec:
                fp,ix=spec.rsplit("|",1)
                if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name: return fp,int(ix or 0),pat
        if not install:
            subprocess.run(["sudo","apt-get","update","-qq"],check=True); subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    raise RuntimeError("font unavailable")
FONT,FONT_INDEX,FONT_PATTERN=resolve_font()

srca=np.asarray(src).copy(); clean_a=srca.copy(); source_mask=Image.new("L",(W,H),0); allowed=Image.new("L",(W,H),0); ad=ImageDraw.Draw(allowed); rows=[]
for idx,(english,korean) in TARGETS.items():
    r=regs[idx]; x,y,w,h=map(int,r["rect"]); crop=src.crop((x,y,x+w,y+h)); aa=np.asarray(crop.getchannel("A")); m=aa>0
    yy,xx=np.where(m)
    if len(xx)==0: raise RuntimeError(("empty",idx))
    eb=[x+int(xx.min()),y+int(yy.min()),x+int(xx.max())+1,y+int(yy.max())+1]
    mf=Image.new("L",(W,H),0); mf.paste(Image.fromarray((m*255).astype(np.uint8)),(x,y)); source_mask=ImageChops.lighter(source_mask,mf)
    ad.rectangle((eb[0],eb[1],eb[2]-1,eb[3]-1),fill=255)
    cy,cx=np.where(m); clean_a[y+cy,x+cx,:]=0
    pix=np.asarray(crop)[m]; med=np.median(pix,axis=0)
    rows.append({"idx":idx,"source":english,"korean":korean,"source_effect_bbox":eb,"source_width":eb[2]-eb[0],"source_height":eb[3]-eb[1],
      "source_visible_pixels":int(m.sum()),"source_rgba_median":[int(v) for v in med]})
clean=Image.fromarray(clean_a,"RGBA"); final=clean.copy()

def render_mask(text,bw,bh):
    font=ImageFont.truetype(FONT,max(20,int(bh*1.25)),index=FONT_INDEX); bb=font.getbbox(text); tw,th=bb[2]-bb[0],bb[3]-bb[1]
    im=Image.new("L",(tw+16,th+16),0); d=ImageDraw.Draw(im); d.text((8-bb[0],8-bb[1]),text,font=font,fill=255); im=im.crop(im.getbbox())
    th2=max(1,int((bh-4)*0.86)); tw2=max(1,int((bw-4)*0.92))
    im=im.resize((max(1,int(round(im.width*(th2/im.height)))),th2),Image.Resampling.LANCZOS)
    im=im.resize((tw2,im.height),Image.Resampling.LANCZOS)
    return im

localized_masks={}
for row in rows:
    idx=row["idx"]; eb=row["source_effect_bbox"]; bw,bh=row["source_width"],row["source_height"]; mask=render_mask(row["korean"],bw,bh)
    tx=eb[0]+(bw-mask.width)//2; ty=eb[1]+(bh-mask.height)//2
    rgba=np.array(row["source_rgba_median"],dtype=np.uint8); ma=np.asarray(mask,dtype=np.float32)/255.0
    layer=np.zeros((mask.height,mask.width,4),dtype=np.uint8); layer[:,:,0:3]=rgba[:3]; layer[:,:,3]=np.clip(np.rint(ma*max(1,int(rgba[3]))),0,255).astype(np.uint8)
    lim=Image.fromarray(layer,"RGBA"); lm=lim.getchannel("A"); final.alpha_composite(lim,(tx,ty))
    full=Image.new("L",(W,H),0); full.paste(lm,(tx,ty)); localized_masks[idx]=full; lb=list(full.getbbox() or ())
    contain=len(lb)==4 and lb[0]>eb[0] and lb[1]>eb[1] and lb[2]<eb[2] and lb[3]<eb[3]
    if not contain: raise RuntimeError(("bbox",idx,eb,lb))
    row.update({"localized_bbox":lb,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
      "delta_left":lb[0]-eb[0],"delta_right":eb[2]-lb[2],"delta_top":lb[1]-eb[1],"delta_bottom":eb[3]-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","font":FONT_PATTERN})

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
candidate.write_bytes(sb[:128]+raw_final.tobytes("raw",RAWMODE)); cb=candidate.read_bytes()
if cb[:128]!=sb[:128] or len(cb)!=len(sb): raise RuntimeError("DDS structure drift")
decoded_raw=Image.frombytes("RGBA",(W,H),cb[128:],"raw",RAWMODE); decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(decoded,final).getbbox() is not None: raise RuntimeError("decode drift")

clean_diff=diffmask(src,clean); clean_out=count(ImageChops.multiply(clean_diff,ImageOps.invert(source_mask)))
final_diff=diffmask(src,decoded); outside=count(ImageChops.multiply(final_diff,ImageOps.invert(allowed)))
alpha_diff=ImageChops.difference(src.getchannel("A"),decoded.getchannel("A")).point(lambda v:255 if v else 0); alpha_out=count(ImageChops.multiply(alpha_diff,ImageOps.invert(allowed)))
same_clean=np.all(np.asarray(clean)==np.asarray(src),axis=2); srcmask_np=np.asarray(source_mask)>0; clean_source_unchanged=int(np.logical_and(srcmask_np,same_clean).sum())
union=Image.new("L",(W,H),0)
for m in localized_masks.values(): union=ImageChops.lighter(union,m)
same_final=np.all(np.asarray(decoded)==np.asarray(src),axis=2); residue=int(np.logical_and(srcmask_np,np.logical_and(same_final,np.asarray(union)==0)).sum())
bbs=[r["localized_bbox"] for r in rows]; overlap=0; touch=0
for i,a in enumerate(bbs):
    for b in bbs[i+1:]:
        if max(a[0],b[0])<min(a[2],b[2]) and max(a[1],b[1])<min(a[3],b[3]): overlap+=1
        if max(a[0]-1,b[0]-1)<min(a[2]+1,b[2]+1) and max(a[1]-1,b[1]-1)<min(a[3]+1,b[3]+1): touch+=1
if any((clean_out,outside,alpha_out,clean_source_unchanged,residue,overlap,touch)): raise RuntimeError(("static",clean_out,outside,alpha_out,clean_source_unchanged,residue,overlap,touch))

cards=[]
for row in rows:
    eb=row["source_effect_bbox"]; box=(max(0,eb[0]-10),max(0,eb[1]-10),min(W,eb[2]+10),min(H,eb[3]+10)); ims=[flatten(z.crop(box)) for z in (src,clean,decoded)]
    scaled=[]
    for q in ims:
        sc=min(1.0,280/max(1,q.width),80/max(1,q.height)); scaled.append(q.resize((max(1,int(q.width*sc)),max(1,int(q.height*sc))),Image.Resampling.LANCZOS) if sc<1 else q)
    cw=sum(q.width for q in scaled)+12; ch=max(q.height for q in scaled)+24; card=Image.new("RGB",(cw,ch),(215,215,215)); d=ImageDraw.Draw(card)
    d.text((4,4),f"idx {row['idx']} {row['source']} -> {row['korean']}  S|C|F",fill=(0,0,0)); xx=0
    for q in scaled: card.paste(q,(xx,24)); xx+=q.width+6
    cards.append(card)
cw=max(c.width for c in cards); ch=sum(c.height+2 for c in cards); sheet=Image.new("RGB",(cw,ch),(195,195,195)); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+2
sheet.save(out/"A53_55B57CDE_SOURCE_CLEAN_FINAL.jpg",quality=94)
flatten(decoded_raw).resize((1024,1024),Image.Resampling.LANCZOS).save(out/"A53_55B57CDE_FINAL_RAW_MIRROR_Y.jpg",quality=93)

report={"schema_version":1,"role":"A","run":run,"index":161,"asset":asset_rel,"worker":"github-actions",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"blob_sha1":SOURCE_BLOB_SHA1,"sha256":SOURCE_SHA256},
 "atlas_provenance":{"blob_sha1":ATLAS_BLOB_SHA1,"sha256":ATLAS_SHA256,"regions":38},
 "candidate_path":str(candidate.relative_to(repo)),"candidate_sha256":sha256(candidate),
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":RAWMODE,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "binding":{"localized_indices":sorted(TARGETS),"semantic_strings":38,"policy":"A52 controller contact fixed physical nationality/zodiac mapping"},
 "rows":rows,"machine_checks":{"clean_changed_outside_source_text_mask":clean_out,"decoded_changed_outside_source_bboxes":outside,
 "alpha_changed_outside_source_bboxes":alpha_out,"clean_source_pixels_unchanged":clean_source_unchanged,"final_source_residue_outside_korean":residue,
 "localized_overlap_pairs":overlap,"localized_1px_touch_pairs":touch},
 "all_38_bbox_size_positive_margin_pass":True,"controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"UNTESTED",
 "status":"A53_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA"}
(out/"A53_55B57CDE_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"index":161,"asset":"55B57CDE","candidate_sha256":report["candidate_sha256"],"bbox_size_positive_margin":"38/38 PASS",
 "changed_outside":outside,"alpha_outside":alpha_out,"clean_source_unchanged":clean_source_unchanged,"source_residue":residue,"overlap":overlap,"touch":touch,
 "worker_status":report["status"],"runtime_validation":"UNTESTED","report":"localization/graphics/role_A/20261005-A-PRODUCTION53/A53_55B57CDE_REPORT.json"}
(wr/"A53_55B57CDE.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False,indent=2))
