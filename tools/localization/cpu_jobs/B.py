import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B hosted worker only")

repo=Path.cwd()
run="20261005-B-PRODUCTION42"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_selector_cvt_Exst/D41D0B1_512x64.dds"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_selector_cvt_Exst/D41D0B1_512x64.dds"
src_dds=Path("/tmp/D41D0B1_HD.dds"); urllib.request.urlretrieve(url,src_dds)
candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def meta(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    mips=struct.unpack_from("<I",b,28)[0]; fourcc=b[84:88]
    need=128+((w+3)//4)*((h+3)//4)*16
    if fourcc!=b"DXT5" or mips not in (0,1) or len(b)!=need:
        raise RuntimeError(("unexpected DDS",w,h,mips,fourcc,len(b),need))
    return w,h,mips,fourcc

sb=src_dds.read_bytes(); W,H,_,_=meta(sb)
if (W,H)!=(2048,256): raise RuntimeError(("unexpected dimensions",W,H))
src=Image.open(src_dds).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
source_mask=sa[:,:,3]>0
ys,xs=np.nonzero(source_mask)
if not len(xs): raise RuntimeError("source alpha empty")
bbox=[int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
source_visible_out=int(np.count_nonzero((sa[:,:,3]>0)&~source_mask))
clean_arr=sa.copy(); clean_arr[source_mask,3]=0
clean=Image.fromarray(clean_arr,"RGBA")

def font_path():
    p=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
    if not p or not Path(p).exists() or "NotoSansCJK" not in Path(p).name:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","libnvtt-bin"],check=True)
        p=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
    if not p: raise RuntimeError("font unavailable")
    return p
FONT=font_path()
if not Path("/usr/bin/nvcompress").exists():
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","libnvtt-bin"],check=True)

pix=sa[source_mask]
lum=.2126*pix[:,0]+.7152*pix[:,1]+.0722*pix[:,2]
white_sel=(pix[:,0]>185)&(pix[:,1]>185)&(pix[:,2]>185)&(pix[:,3]>32)
dark_sel=(lum<115)&(pix[:,2]>pix[:,0])&(pix[:,3]>16)
white_rgb=tuple(int(v) for v in np.median(pix[white_sel,:3],axis=0)) if np.any(white_sel) else (250,250,250)
white=(white_rgb[0],white_rgb[1],white_rgb[2],255)
dark_rgb=tuple(int(v) for v in np.median(pix[dark_sel,:3],axis=0)) if np.any(dark_sel) else (8,18,70)
dark=(dark_rgb[0],dark_rgb[1],dark_rgb[2],255)

def shear_rgba(im,s):
    shift=max(0,int(round(s*(im.height-1))))
    o=Image.new("RGBA",(im.width+shift,im.height),(0,0,0,0))
    for y in range(im.height):
        o.alpha_composite(im.crop((0,y,im.width,y+1)),(int(round(s*(im.height-1-y))),y))
    return o

def render(text,bb):
    x0,y0,x1,y1=bb
    bx0=((x0+3)//4)*4; by0=((y0+3)//4)*4; bx1=(x1//4)*4; by1=(y1//4)*4
    aw,ah=bx1-bx0,by1-by0
    if aw<32 or ah<32: raise RuntimeError(("no block-safe bbox",bb,[bx0,by0,bx1,by1]))
    dummy=ImageDraw.Draw(Image.new("L",(8,8),0)); slant=.31
    for fs in range(min(180,int(ah*1.05)),11,-1):
        f=ImageFont.truetype(FONT,fs)
        sw=max(2,round(fs*.10))
        tb=dummy.textbbox((0,0),text,font=f,stroke_width=sw)
        pad=sw+5
        m=Image.new("L",(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad),0)
        ImageDraw.Draw(m).text((pad-tb[0],pad-tb[1]),text,font=f,fill=255,stroke_width=sw,stroke_fill=255)
        fill=Image.new("L",m.size,0)
        ImageDraw.Draw(fill).text((pad-tb[0],pad-tb[1]),text,font=f,fill=255)
        tile=Image.new("RGBA",m.size,(0,0,0,0))
        tile.paste(dark,(0,0),m); tile.paste(white,(0,0),fill)
        tile=shear_rgba(tile,slant)
        ab=tile.getchannel("A").getbbox()
        if not ab: continue
        tile=tile.crop(ab)
        if tile.width>aw-6 or tile.height>ah-6: continue
        layer=Image.new("RGBA",(W,H),(0,0,0,0))
        px=bx0+(aw-tile.width)//2; py=by0+(ah-tile.height)//2
        layer.alpha_composite(tile,(px,py))
        lb=layer.getchannel("A").getbbox()
        if lb and lb[0]>x0 and lb[1]>y0 and lb[2]<x1 and lb[3]<y1:
            return layer,fs,sw,list(lb),[bx0,by0,bx1,by1],slant
    raise RuntimeError(("cannot fit",text,bb))

korean="여자친구와 함께 골에 도착하세요."
layer,fs,sw,lb,blockbb,slant=render(korean,bbox)
final=clean.copy(); final.alpha_composite(layer)
target=np.asarray(layer.getchannel("A"))>0
sw0,sh0=bbox[2]-bbox[0],bbox[3]-bbox[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
if not(lb[0]>=bbox[0] and lb[1]>=bbox[1] and lb[2]<=bbox[2] and lb[3]<=bbox[3] and lw<=sw0 and lh<=sh0):
    raise RuntimeError(("size gate",bbox,lb))

raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
tmp_png=Path("/tmp/D41_final_raw.png"); tmp_dds=Path("/tmp/D41_final_nv.dds")
raw.save(tmp_png)
subprocess.run(["/usr/bin/nvcompress","-bc3","-nomips",str(tmp_png),str(tmp_dds)],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
tb=tmp_dds.read_bytes(); meta(tb)
allowed=np.zeros((H,W),bool); allowed[bbox[1]:bbox[3],bbox[0]:bbox[2]]=True
allowed_raw=np.flipud(allowed); srcmask_raw=np.flipud(source_mask); target_raw=np.flipud(target); source_raw_alpha=np.flipud(sa[:,:,3])
bw=W//4; bh=H//4; outb=bytearray(sb); target_blocks=set(); source_only_full=set(); partial_blocks=set()

def aidx(block):
    bits=int.from_bytes(block[2:8],"little")
    return [(bits>>(3*i))&7 for i in range(16)]
def seta(block,idx):
    bits=sum((int(v)&7)<<(3*i) for i,v in enumerate(idx))
    return block[:2]+bits.to_bytes(6,"little")+block[8:]

for by in range(bh):
    y=by*4
    if not np.any(allowed_raw[y:y+4]): continue
    for bx in range(bw):
        x=bx*4; am=allowed_raw[y:y+4,x:x+4]
        if not np.any(am): continue
        sm=srcmask_raw[y:y+4,x:x+4]; tm=target_raw[y:y+4,x:x+4]
        if not np.any(sm) and not np.any(tm): continue
        off=128+(by*bw+bx)*16
        if np.any(tm):
            if not np.all(am): raise RuntimeError(("target in partial block",bx,by))
            outb[off:off+16]=tb[off:off+16]; target_blocks.add((bx,by)); continue
        if np.all(am):
            nb=tb[off:off+8]+sb[off+8:off+16]
            outb[off:off+16]=nb; source_only_full.add((bx,by)); continue
        if not np.any(sm): continue
        ob=bytes(outb[off:off+16]); idx=aidx(ob); sa4=source_raw_alpha[y:y+4,x:x+4]
        zero=[idx[yy*4+xx] for yy in range(4) for xx in range(4) if sa4[yy,xx]==0]
        if not zero: raise RuntimeError(("partial no transparent alpha",bx,by))
        zi=Counter(zero).most_common(1)[0][0]
        for yy in range(4):
            for xx in range(4):
                if sm[yy,xx]: idx[yy*4+xx]=zi
        nb=seta(ob,idx)
        if nb[8:]!=ob[8:]: raise RuntimeError("partial color changed")
        outb[off:off+16]=nb; partial_blocks.add((bx,by))

candidate.write_bytes(outb)
cand_sha=sha(candidate)
dec=Image.open(candidate).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
da=np.asarray(dec,dtype=np.uint8)
alpha_out=int(np.count_nonzero((sa[:,:,3]!=da[:,:,3])&~allowed))
visible_out=int(np.count_nonzero((da[:,:,3]>1)&~allowed))
if alpha_out or visible_out: raise RuntimeError(("outside",alpha_out,visible_out))
# Detect surviving source pixels outside a 2px expansion of Korean target. Low-alpha BC3 fringe is ignored below alpha 16.
guard=np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
residue=int(np.count_nonzero(source_mask&(da[:,:,3]>16)&~guard))
if residue: raise RuntimeError(("source residue",residue))

cm=da[bbox[1]:bbox[3],bbox[0]:bbox[2],3]>1
ys,xs=np.nonzero(cm)
db=[bbox[0]+int(xs.min()),bbox[1]+int(ys.min()),bbox[0]+int(xs.max())+1,bbox[1]+int(ys.max())+1]
dw,dh=db[2]-db[0],db[3]-db[1]
if db[0]<bbox[0] or db[1]<bbox[1] or db[2]>bbox[2] or db[3]>bbox[3] or dw>sw0 or dh>sh0:
    raise RuntimeError(("decoded size gate",bbox,db))

def mask(m): return Image.fromarray((m.astype(np.uint8)*255),"L")
source_mask_png=out/"D41D0B1_SOURCE_TEXT_MASK.png"; mask(source_mask).save(source_mask_png)
allowed_png=out/"D41D0B1_ALLOWED_TEXT_REGION_MASK.png"; mask(allowed).save(allowed_png)
protected_png=out/"D41D0B1_PROTECTED_MASK.png"; mask(~allowed).save(protected_png)
target_png=out/"D41D0B1_TARGET_TEXT_MASK.png"; mask(target).save(target_png)
clean_png=out/"D41D0B1_CLEAN_PLATE.png"; clean.save(clean_png)
src_png=Path("/tmp/D41_source.png"); final_png=Path("/tmp/D41_final.png"); src.save(src_png); dec.save(final_png)
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(src_png),str(clean_png),str(source_mask_png),"--report",str(out/"B_PRODUCTION42_CLEAN_PLATE_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(src_png),str(final_png),str(allowed_png),"--protected-mask",str(protected_png),"--report",str(out/"B_PRODUCTION42_FINAL_MASK_VALIDATION.json")],check=True)

def comp(im,bg):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def card(label,im,bg):
    v=comp(im,bg); c=Image.new("RGB",(W,H+28),"white"); c.paste(v,(0,28)); ImageDraw.Draw(c).text((5,5),label,fill="black"); return c
cards=[card("SOURCE",src,(64,64,64,255)),card("CLEAN",clean,(64,64,64,255)),card("FINAL",dec,(64,64,64,255)),card("FINAL_WHITE",dec,(255,255,255,255))]
sheet=Image.new("RGB",(W*2,(H+28)*2),"white")
sheet.paste(cards[0],(0,0));sheet.paste(cards[1],(W,0));sheet.paste(cards[2],(0,H+28));sheet.paste(cards[3],(W,H+28))
sheet.save(out/"B_PRODUCTION42_D41_COMPARE.jpg",quality=96)
cr=(max(0,bbox[0]-20),max(0,bbox[1]-6),min(W,bbox[2]+20),min(H,bbox[3]+6))
ims=[comp(z,(64,64,64,255)).crop(cr) for z in [src,clean,dec]]
ims=[x.resize((x.width*2,x.height*2),Image.Resampling.NEAREST) for x in ims]
contact=Image.new("RGB",(sum(x.width for x in ims)+12,max(x.height for x in ims)+28),"white");xx=0
for im in ims: contact.paste(im,(xx,28));xx+=im.width+6
ImageDraw.Draw(contact).text((4,4),"Try to reach the goal with your girlfriend. -> "+korean,fill="black")
contact.save(out/"B_PRODUCTION42_D41_ROW_CONTACT_2X.jpg",quality=96)

# Explicit raw DDS mirror-Y proof for orientation policy.
src_raw=Image.open(src_dds).convert("RGBA")
dec_raw=Image.open(candidate).convert("RGBA")
raw_cards=[card("SOURCE_RAW_MIRROR_Y",src_raw,(64,64,64,255)),card("FINAL_RAW_MIRROR_Y",dec_raw,(64,64,64,255))]
raw_sheet=Image.new("RGB",(W,(H+28)*2),"white")
raw_sheet.paste(raw_cards[0],(0,0)); raw_sheet.paste(raw_cards[1],(0,H+28))
raw_sheet.save(out/"B_PRODUCTION42_D41_RAW_COMPARE.jpg",quality=96)

patch=target_blocks|source_only_full|partial_blocks; changed=0; outside_patch=0
for by in range(bh):
    for bx in range(bw):
        off=128+(by*bw+bx)*16
        if sb[off:off+16]!=outb[off:off+16]:
            changed+=1
            if (bx,by) not in patch: outside_patch+=1
if outside_patch: raise RuntimeError(("compressed outside patch",outside_patch))

row={"source":"Try to reach the goal with your girlfriend.","korean":korean,"original_bbox":bbox,"localized_bbox":lb,
     "decoded_localized_bbox":db,"source_width":sw0,"source_height":sh0,"localized_width":lw,"localized_height":lh,
     "decoded_localized_width":dw,"decoded_localized_height":dh,"delta_left":lb[0]-bbox[0],"delta_right":bbox[2]-lb[2],
     "delta_top":lb[1]-bbox[1],"delta_bottom":bbox[3]-lb[3],"containment":"PASS","size_ceiling":"PASS",
     "decoded_containment":"PASS","decoded_size_ceiling":"PASS","font_size":fs,"stroke_width":sw,"slant":slant,"block_safe_bbox":blockbb}
report={"schema_version":1,"role":"B","run":run,"queue_index":112,"asset":asset,"readiness_tier":"RENDER_READY_COMPLETED_SAME_INVOCATION",
"source_url":url,"source_sha256":sha(src_dds),"candidate_sha256":cand_sha,"candidate_path":str(candidate.relative_to(repo)),
"method":"canonical 2048x256 DXT5 HD source; exact source alpha bbox/effect mask; alpha-zero clean plate with hidden RGB preserved; source-measured white fill/navy outline; fresh right-slanted native Hangul; target color changes only in fully allowed BC3 blocks; source-only cleanup alpha-only; decoded static QA",
"structure":{"width":W,"height":H,"format":"DXT5","mipmaps":1,"header_128_exact":bytes(outb[:128])==sb[:128],"raw_orientation":"mirror_y"},
"palette":{"white":white,"dark":dark},"rows":[row],
"containment":{"elements_total":1,"elements_pass":1,"visible_pixels_outside_original_bbox":visible_out,"alpha_changed_pixels_outside_original_bbox":alpha_out,"source_residue_pixels_alpha_gt16_outside_target_guard":residue,"status":"PASS"},
"compressed_patch":{"target_reencoded_blocks":len(target_blocks),"source_only_full_alpha_blocks":len(source_only_full),"partial_alpha_only_blocks":len(partial_blocks),"changed_blocks":changed,"changed_blocks_outside_patch":outside_patch,"source_only_color_bytes_preserved":True,"partial_color_bytes_preserved":True,"status":"PASS"},
"manual_visual_qa":"PENDING_CONTROLLER_SELF_QA","RUNTIME_VALIDATION":"UNTESTED","status":"B_PRODUCTION42_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"}
(out/"B_PRODUCTION42_D41_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"D41D0B1","index":112,"candidate_sha256":cand_sha,"bbox_size_pass":"1/1","visible_outside":visible_out,"alpha_outside":alpha_out,"source_residue":residue,"changed_blocks_outside_patch":outside_patch,"worker_status":report["status"],"runtime_validation":"UNTESTED","report":"localization/graphics/role_B/20261005-B-PRODUCTION42/B_PRODUCTION42_D41_REPORT.json"}
(wr/"B_PRODUCTION42_D41D0B1.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
