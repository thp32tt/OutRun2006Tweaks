#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")
repo=Path.cwd(); run="20261005-A-PRODUCTION54-DXT5"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/55B57CDE_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel; candidate.parent.mkdir(parents=True,exist_ok=True)
tmp=Path("/tmp/outrun_A54"); tmp.mkdir(parents=True,exist_ok=True)
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"; BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
source=tmp/"55B57CDE_HD.dds"; atlasp=tmp/"55B57CDE_atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_sumo_fe_cvt_Exst/55B57CDE_512x512.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_55B57CDE_512x512_atlas.json",atlasp)

def gitblob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def dds_meta(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    H=struct.unpack_from("<I",b,12)[0]; W=struct.unpack_from("<I",b,16)[0]; mips=struct.unpack_from("<I",b,28)[0]; fourcc=b[84:88]
    need=128+((W+3)//4)*((H+3)//4)*16
    if fourcc!=b"DXT5" or mips not in (0,1) or len(b)!=need: raise RuntimeError(("unexpected DDS",W,H,mips,fourcc,len(b),need))
    return W,H,mips
sb=source.read_bytes(); ab=atlasp.read_bytes()
if gitblob(sb)!="0b12c672224ce05acb9470af895bbda335cc5543" or gitblob(ab)!="70001b44445f3e10b46eb7e3480abdece8eda790":
    raise RuntimeError(("pinned drift",gitblob(sb),gitblob(ab)))
W,H,MIPS=dds_meta(sb)
if (W,H)!=(2048,2048): raise RuntimeError(("dimension",W,H))
regs={int(r["idx"]):r for r in json.loads(ab.decode("utf-8"))["regions"]}
raw_src=Image.open(source).convert("RGBA"); src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM); sa=np.asarray(src,dtype=np.uint8)

TARGETS={
0:("VIRGO","처녀자리"),1:("TAURUS","황소자리"),2:("SCORPIO","전갈자리"),3:("SAGITTARIUS","사수자리"),4:("PISCES","물고기자리"),5:("LIBRA","천칭자리"),
6:("LEO","사자자리"),7:("GEMINI","쌍둥이자리"),8:("CAPRICORN","염소자리"),9:("CANCER","게자리"),10:("ARIES","양자리"),11:("AQUARIUS","물병자리"),
12:("THAILAND","태국"),13:("SWITZERLAND","스위스"),14:("SWEDEN","스웨덴"),15:("SPAIN","스페인"),16:("SOUTH KOREA","대한민국"),17:("SINGAPORE","싱가포르"),
18:("OTHER","기타"),19:("NORWAY","노르웨이"),20:("NORTH KOREA","북한"),21:("NEW ZEALAND","뉴질랜드"),22:("MEXICO","멕시코"),23:("JAPAN","일본"),
24:("ITALY","이탈리아"),25:("HONG KONG","홍콩"),26:("GERMANY","독일"),27:("FRANCE","프랑스"),28:("FINLAND","핀란드"),29:("NETHERLANDS","네덜란드"),
30:("DENMARK","덴마크"),31:("CHINA","중국"),32:("CANADA","캐나다"),33:("BRITAIN","영국"),34:("BELGIUM","벨기에"),35:("AUSTRIA","오스트리아"),
36:("AUSTRALIA","호주"),37:("USA","미국")
}
if set(TARGETS)!=set(range(38)): raise RuntimeError("binding incomplete")

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra","libnvtt-bin"],check=True)
FONT=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Bold"],text=True).strip()
if not FONT or not Path(FONT).exists(): raise RuntimeError("font unavailable")
if not Path("/usr/bin/nvcompress").exists(): raise RuntimeError("nvcompress unavailable")

elements=[]; source_union=np.zeros((H,W),bool); allowed=np.zeros((H,W),bool)
for idx,(english,korean) in TARGETS.items():
    x,y,cw,ch=map(int,regs[idx]["rect"]); roi=sa[y:y+ch,x:x+cw]; mask=roi[:,:,3]>1
    ys,xs=np.nonzero(mask)
    if not len(xs): raise RuntimeError(("empty",idx))
    eb=[x+int(xs.min()),y+int(ys.min()),x+int(xs.max())+1,y+int(ys.max())+1]
    gm=np.zeros((H,W),bool); gm[y:y+ch,x:x+cw]=mask
    if np.any(source_union & gm): raise RuntimeError(("source overlap",idx))
    source_union |= gm; allowed[eb[1]:eb[3],eb[0]:eb[2]]=True
    pix=sa[gm]; vis=pix[pix[:,3]>16]; med=vis if len(vis) else pix
    color=tuple(int(np.median(med[:,k])) for k in range(3))+(255,)
    elements.append({"idx":idx,"source":english,"korean":korean,"cell":[x,y,cw,ch],"source_mask":gm,"original_bbox":eb,
                     "source_mask_pixels":int(np.count_nonzero(gm)),"source_rgba_median":list(color)})

clean_arr=sa.copy(); clean_arr[source_union,3]=0; clean=Image.fromarray(clean_arr,"RGBA")
final=clean.copy(); target_union=np.zeros((H,W),bool); layers=[]

def text_alpha(text,maxw,maxh):
    best=None
    for fs in range(max(18,int(maxh*1.15)),11,-1):
        font=ImageFont.truetype(FONT,fs)
        d=ImageDraw.Draw(Image.new("L",(8,8),0)); bb=d.textbbox((0,0),text,font=font)
        im=Image.new("L",(max(8,bb[2]-bb[0]+12),max(8,bb[3]-bb[1]+12)),0)
        ImageDraw.Draw(im).text((6-bb[0],6-bb[1]),text,font=font,fill=255)
        gb=im.getbbox()
        if not gb: continue
        im=im.crop(gb)
        scale=min(1.0,maxw/max(1,im.width),maxh/max(1,im.height))
        if scale<0.35: continue
        if scale<0.999: im=im.resize((max(1,int(im.width*scale)),max(1,int(im.height*scale))),Image.Resampling.LANCZOS)
        if im.width<=maxw and im.height<=maxh: best=(fs,im); break
    if not best: raise RuntimeError(("fit",text,maxw,maxh))
    return best

for e in elements:
    x0,y0,x1,y1=e["original_bbox"]
    bx0=((x0+3)//4)*4; by0=((y0+3)//4)*4; bx1=(x1//4)*4; by1=(y1//4)*4
    maxw=bx1-bx0-8; maxh=by1-by0-8
    if maxw<8 or maxh<8: raise RuntimeError(("no safe interior",e["idx"],e["original_bbox"]))
    fs,a=text_alpha(e["korean"],maxw,maxh)
    px=bx0+4+(maxw-a.width)//2; py=by0+4+(maxh-a.height)//2
    color=tuple(e["source_rgba_median"][:3])+(255,)
    tile=Image.new("RGBA",a.size,color); tile.putalpha(a)
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); layer.alpha_composite(tile,(px,py))
    lm=np.asarray(layer.getchannel("A"))>0
    if np.any(target_union & lm): raise RuntimeError(("target overlap",e["idx"]))
    target_union|=lm; final.alpha_composite(layer); layers.append(layer)
    lb=list(layer.getchannel("A").getbbox() or ())
    if not(lb and lb[0]>x0 and lb[1]>y0 and lb[2]<x1 and lb[3]<y1): raise RuntimeError(("bbox",e["idx"],e["original_bbox"],lb))
    e.update({"localized_bbox_preencode":lb,"font_file":Path(FONT).name,"font_size":fs,"block_safe_bbox":[bx0,by0,bx1,by1]})

# 1px separation
for i,m1 in enumerate([np.asarray(z.getchannel("A"))>0 for z in layers]):
    dil=np.asarray(Image.fromarray((m1.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0
    for j in range(i+1,len(layers)):
        if np.any(dil & (np.asarray(layers[j].getchannel("A"))>0)): raise RuntimeError(("1px touch",i,j))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM); png=tmp/"final_raw.png"; enc=tmp/"final_nv.dds"; raw_final.save(png)
subprocess.run(["/usr/bin/nvcompress","-bc3","-nomips",str(png),str(enc)],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
tb=enc.read_bytes(); dds_meta(tb)

allowed_raw=np.flipud(allowed); source_raw=np.flipud(source_union); target_raw=np.flipud(target_union); source_alpha_raw=np.flipud(sa[:,:,3])
bw=W//4; bh=H//4; outb=bytearray(sb); target_blocks=set(); source_full=set(); source_partial=set()
def alpha_indices(block):
    bits=int.from_bytes(block[2:8],"little"); return [(bits>>(3*i))&7 for i in range(16)]
def set_alpha_indices(block,idx):
    bits=sum((int(v)&7)<<(3*i) for i,v in enumerate(idx)); return block[:2]+bits.to_bytes(6,"little")+block[8:]

for by in range(bh):
    y=by*4
    if not np.any(allowed_raw[y:y+4]): continue
    for bx in range(bw):
        x=bx*4; am=allowed_raw[y:y+4,x:x+4]; sm=source_raw[y:y+4,x:x+4]; tm=target_raw[y:y+4,x:x+4]
        if not np.any(sm) and not np.any(tm): continue
        off=128+(by*bw+bx)*16
        if np.any(tm):
            if not np.all(am): raise RuntimeError(("target block crosses bbox",bx,by))
            outb[off:off+16]=tb[off:off+16]; target_blocks.add((bx,by)); continue
        if np.all(am):
            outb[off:off+16]=tb[off:off+8]+sb[off+8:off+16]; source_full.add((bx,by)); continue
        ob=bytes(outb[off:off+16]); idxs=alpha_indices(ob); a4=source_alpha_raw[y:y+4,x:x+4]
        zeros=[idxs[yy*4+xx] for yy in range(4) for xx in range(4) if not sm[yy,xx] and a4[yy,xx]<=1]
        if not zeros: raise RuntimeError(("partial lacks transparent donor",bx,by))
        zi=Counter(zeros).most_common(1)[0][0]
        for yy in range(4):
            for xx in range(4):
                if sm[yy,xx]: idxs[yy*4+xx]=zi
        nb=set_alpha_indices(ob,idxs)
        if nb[:2]!=ob[:2] or nb[8:]!=ob[8:]: raise RuntimeError(("endpoint/color drift",bx,by))
        outb[off:off+16]=nb; source_partial.add((bx,by))

candidate.write_bytes(outb); dec_raw=Image.open(candidate).convert("RGBA"); dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM); da=np.asarray(dec,dtype=np.uint8)
diff=np.any(sa!=da,axis=2); diff_out=int(np.count_nonzero(diff & ~allowed)); alpha_out=int(np.count_nonzero((sa[:,:,3]!=da[:,:,3]) & ~allowed))
intro=int(np.count_nonzero((sa[:,:,3]<=1)&(da[:,:,3]>1)&~allowed))
if any((diff_out,alpha_out,intro)): raise RuntimeError(("outside drift",diff_out,alpha_out,intro))
guard=np.asarray(Image.fromarray((target_union.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
residue=int(np.count_nonzero(source_union & (da[:,:,3]>8) & ~guard))
if residue: raise RuntimeError(("source residue",residue))

# Exact decoded target bboxes: isolate connected candidate-visible pixels near preencode target, not all source-bbox pixels.
for e,layer in zip(elements,layers):
    x0,y0,x1,y1=e["original_bbox"]; pre=e["localized_bbox_preencode"]; p=4
    rx0=max(x0,pre[0]-p); ry0=max(y0,pre[1]-p); rx1=min(x1,pre[2]+p); ry1=min(y1,pre[3]+p)
    cm=da[ry0:ry1,rx0:rx1,3]>1; ys,xs=np.nonzero(cm)
    if not len(xs): raise RuntimeError(("decoded empty",e["idx"]))
    db=[rx0+int(xs.min()),ry0+int(ys.min()),rx0+int(xs.max())+1,ry0+int(ys.max())+1]
    dw,dh=db[2]-db[0],db[3]-db[1]; sw,sh=x1-x0,y1-y0
    if not(db[0]>=x0 and db[1]>=y0 and db[2]<=x1 and db[3]<=y1 and dw<=sw and dh<=sh and db[0]>x0 and db[1]>y0 and db[2]<x1 and db[3]<y1):
        raise RuntimeError(("decoded bbox",e["idx"],e["original_bbox"],db))
    e.update({"localized_bbox":db,"localized_width":dw,"localized_height":dh,"source_width":sw,"source_height":sh,
      "delta_left":db[0]-x0,"delta_right":x1-db[2],"delta_top":db[1]-y0,"delta_bottom":y1-db[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})
    e.pop("source_mask",None)

changed_blocks=0; changed_outside=0; patch=target_blocks|source_full|source_partial
for by in range(bh):
    for bx in range(bw):
        off=128+(by*bw+bx)*16
        if sb[off:off+16]!=outb[off:off+16]:
            changed_blocks+=1
            if (bx,by) not in patch: changed_outside+=1
if changed_outside: raise RuntimeError(("compressed outside patch",changed_outside))

def comp(im):
    z=Image.new("RGBA",im.size,(65,65,65,255)); z.alpha_composite(im); return z.convert("RGB")
cards=[]
for e in elements:
    x0,y0,x1,y1=e["original_bbox"]; cr=(max(0,x0-8),max(0,y0-8),min(W,x1+8),min(H,y1+8))
    ims=[comp(z).crop(cr) for z in (src,clean,dec)]
    sc=min(1.4,250/max(1,ims[0].width)); ims=[z.resize((max(1,int(z.width*sc)),max(1,int(z.height*sc))),Image.Resampling.NEAREST) for z in ims]
    c=Image.new("RGB",(sum(z.width for z in ims)+8,max(z.height for z in ims)+22),"white"); ImageDraw.Draw(c).text((3,3),f"{e['idx']} {e['source']} -> {e['korean']} S|C|F",fill="black")
    xx=0
    for z in ims: c.paste(z,(xx,22)); xx+=z.width+4
    cards.append(c)
cw=max(c.width for c in cards); sh=sum(c.height+2 for c in cards); sheet=Image.new("RGB",(cw,sh),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+2
sheet.save(out/"A54_55B57CDE_SOURCE_CLEAN_FINAL.jpg",quality=94)
comp(dec_raw).resize((1024,1024),Image.Resampling.LANCZOS).save(out/"A54_55B57CDE_FINAL_RAW_MIRROR_Y.jpg",quality=93)

report={"schema_version":1,"role":"A","run":run,"index":161,"asset":asset_rel,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"blob_sha1":gitblob(sb),"sha256":sha(sb)},
 "atlas_provenance":{"blob_sha1":gitblob(ab),"sha256":sha(ab),"regions":38},
 "structure":{"width":W,"height":H,"format":"DXT5","mipmaps":MIPS,"header_128_exact":bytes(outb[:128])==sb[:128],"raw_orientation":"mirror_y"},
 "binding":{"localized_indices":list(range(38)),"semantic_strings":38,"policy":"A52 controller contact fixed nationality/zodiac physical mapping"},
 "elements":elements,"machine_checks":{"decoded_changed_outside_exact_source_bboxes":diff_out,"alpha_changed_outside_exact_source_bboxes":alpha_out,
 "introduced_visible_outside_exact_source_bboxes":intro,"source_residue_pixels":residue,"localized_overlap_pairs":0,"localized_1px_touch_pairs":0},
 "compressed_patch":{"target_reencoded_blocks":len(target_blocks),"source_only_full_alpha_blocks":len(source_full),
 "boundary_alpha_index_only_blocks":len(source_partial),"changed_blocks":changed_blocks,"changed_blocks_outside_patch":changed_outside,
 "boundary_endpoints_and_color_bytes_preserved":True},
 "candidate_sha256":sha(bytes(outb)),"candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","status":"A54_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA","runtime_validation":"UNTESTED"}
(out/"A54_55B57CDE_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"index":161,"asset":"55B57CDE","candidate_sha256":report["candidate_sha256"],"bbox_size_positive_margin":"38/38 PASS",
 "decoded_changed_outside":diff_out,"alpha_outside":alpha_out,"introduced_visible_outside":intro,"source_residue":residue,
 "boundary_alpha_index_only_blocks":len(source_partial),"worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":"localization/graphics/role_A/20261005-A-PRODUCTION54-DXT5/A54_55B57CDE_REPORT.json"}
(wr/"A54_55B57CDE.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False,indent=2))
