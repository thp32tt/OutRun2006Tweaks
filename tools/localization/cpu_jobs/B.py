import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B hosted worker only")

repo=Path.cwd()
run="20261005-B-PRODUCTION43"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_selector_cvt_Exst/D41D0B1_512x64.dds"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_selector_cvt_Exst/D41D0B1_512x64.dds"
src_dds=Path("/tmp/D41D0B1_HD.dds")
urllib.request.urlretrieve(url,src_dds)
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def meta(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    mips=struct.unpack_from("<I",b,28)[0]; fourcc=b[84:88]
    need=128+((w+3)//4)*((h+3)//4)*16
    if fourcc!=b"DXT5" or mips not in (0,1) or len(b)!=need:
        raise RuntimeError(("unexpected DDS",w,h,mips,fourcc,len(b),need))
    return w,h,mips,fourcc

sb=src_dds.read_bytes()
W,H,_,_=meta(sb)
if (W,H)!=(2048,256): raise RuntimeError(("unexpected dimensions",W,H))
src=Image.open(src_dds).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
alpha=sa[:,:,3]>0
if not np.any(alpha): raise RuntimeError("source alpha empty")

# Recover the two source typography rows. Prefer actual transparent separation; if BC3
# fringe bridges the gap, split at the minimum-alpha valley around the vertical middle.
row_counts=np.count_nonzero(alpha,axis=1)
active=np.flatnonzero(row_counts)
groups=[]
if len(active):
    g=[int(active[0])]
    for y in active[1:]:
        if int(y)-g[-1] > 3:
            groups.append(g); g=[int(y)]
        else:
            g.append(int(y))
    groups.append(g)
groups=[g for g in groups if len(g)>=4]
if len(groups)!=2:
    lo,hi=int(active[0]),int(active[-1])+1
    ss=lo+max(4,int((hi-lo)*.36)); ee=lo+min((hi-lo)-4,int((hi-lo)*.64))
    if ee<=ss: raise RuntimeError(("split window",lo,hi,ss,ee))
    split=ss+int(np.argmin(row_counts[ss:ee]))
    groups=[list(range(lo,split+1)),list(range(split+1,hi))]
if len(groups)!=2 or min(len(g) for g in groups)<4:
    raise RuntimeError(("expected two source rows",[(g[0],g[-1],len(g)) for g in groups]))

source_lines=["Try to reach the goal","with your girlfriend."]
korean_lines=["여자친구와 함께","골에 도착하세요."]
rows=[]
source_masks=[]
for i,g in enumerate(groups):
    y0,y1=g[0],g[-1]+1
    yy,xx=np.nonzero(alpha[y0:y1])
    if not len(xx): raise RuntimeError(("empty source row",i))
    bb=[int(xx.min()),y0,int(xx.max())+1,y1]
    m=np.zeros((H,W),bool)
    m[y0:y1,bb[0]:bb[2]]=alpha[y0:y1,bb[0]:bb[2]]
    source_masks.append(m)
    rows.append({"n":i+1,"source":source_lines[i],"korean":korean_lines[i],"original_bbox":bb})
if np.any(source_masks[0]&source_masks[1]): raise RuntimeError("source row overlap")
source_mask=source_masks[0]|source_masks[1]
source_visible_out=int(np.count_nonzero(alpha&~source_mask))
if source_visible_out: raise RuntimeError(("source pixels outside row masks",source_visible_out))

# Exact clean plate: remove full source glyph/effect alpha while retaining source hidden RGB.
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
dark_sel=(lum<120)&(pix[:,2]>pix[:,0])&(pix[:,3]>16)
white_rgb=tuple(int(v) for v in np.median(pix[white_sel,:3],axis=0)) if np.any(white_sel) else (255,255,255)
dark_rgb=tuple(int(v) for v in np.median(pix[dark_sel,:3],axis=0)) if np.any(dark_sel) else (2,13,60)
white=(white_rgb[0],white_rgb[1],white_rgb[2],255)
dark=(dark_rgb[0],dark_rgb[1],dark_rgb[2],255)
slant=.31

def shear_rgba(im,s):
    shift=max(0,int(round(s*(im.height-1))))
    o=Image.new("RGBA",(im.width+shift,im.height),(0,0,0,0))
    for y in range(im.height):
        dx=int(round(s*(im.height-1-y)))
        o.alpha_composite(im.crop((0,y,im.width,y+1)),(dx,y))
    return o

def build_tile(text,fs,stroke):
    f=ImageFont.truetype(FONT,fs)
    d=ImageDraw.Draw(Image.new("L",(8,8),0))
    tb=d.textbbox((0,0),text,font=f,stroke_width=stroke)
    pad=stroke+5
    size=(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad)
    outer=Image.new("L",size,0); fill=Image.new("L",size,0)
    pos=(pad-tb[0],pad-tb[1])
    ImageDraw.Draw(outer).text(pos,text,font=f,fill=255,stroke_width=stroke,stroke_fill=255)
    ImageDraw.Draw(fill).text(pos,text,font=f,fill=255)
    tile=Image.new("RGBA",size,(0,0,0,0))
    tile.paste(dark,(0,0),outer); tile.paste(white,(0,0),fill)
    tile=shear_rgba(tile,slant)
    ab=tile.getchannel("A").getbbox()
    if not ab: return None
    return tile.crop(ab)

# Multi-line style policy: both Korean rows share exactly one font size/stroke/slant,
# matching the two source rows' shared style. Each row is fitted to its own exact bbox.
min_h=min(r["original_bbox"][3]-r["original_bbox"][1] for r in rows)
common=None
for fs in range(min(180,int(min_h*1.08)),11,-1):
    stroke=max(2,round(fs*.10))
    tiles=[]; ok=True
    for row in rows:
        bb=row["original_bbox"]
        bx0=((bb[0]+3)//4)*4; by0=((bb[1]+3)//4)*4; bx1=(bb[2]//4)*4; by1=(bb[3]//4)*4
        aw,ah=bx1-bx0,by1-by0
        tile=build_tile(row["korean"],fs,stroke)
        if tile is None or tile.width>aw-6 or tile.height>ah-6:
            ok=False; break
        tiles.append((tile,[bx0,by0,bx1,by1]))
    if ok:
        common=(fs,stroke,tiles); break
if common is None: raise RuntimeError(("cannot fit shared two-line style",[r["original_bbox"] for r in rows]))
fs,stroke,tiles=common

final=clean.copy()
layers=[]
for row,(tile,blockbb) in zip(rows,tiles):
    bb=row["original_bbox"]; bx0,by0,bx1,by1=blockbb
    layer=Image.new("RGBA",(W,H),(0,0,0,0))
    px=bx0+(bx1-bx0-tile.width)//2
    py=by0+(by1-by0-tile.height)//2
    layer.alpha_composite(tile,(px,py))
    lb=layer.getchannel("A").getbbox()
    if not lb: raise RuntimeError(("empty target row",row["n"]))
    lb=list(lb)
    sw0,sh0=bb[2]-bb[0],bb[3]-bb[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    if lb[0]<=bb[0] or lb[1]<=bb[1] or lb[2]>=bb[2] or lb[3]>=bb[3] or lw>sw0 or lh>sh0:
        raise RuntimeError(("row fit gate",row["n"],bb,lb))
    for old in layers:
        if ImageChops.multiply(layer.getchannel("A"),old.getchannel("A")).getbbox():
            raise RuntimeError(("localized row overlap",row["n"]))
    layers.append(layer); final.alpha_composite(layer)
    row.update({"localized_bbox":lb,"source_width":sw0,"source_height":sh0,
      "localized_width":lw,"localized_height":lh,
      "delta_left":lb[0]-bb[0],"delta_right":bb[2]-lb[2],
      "delta_top":lb[1]-bb[1],"delta_bottom":bb[3]-lb[3],
      "containment":"PASS","size_ceiling":"PASS","font_size":fs,"stroke_width":stroke,
      "slant":slant,"block_safe_bbox":blockbb,
      "multi_line_style_consistency":"PASS_SHARED_FONT_SIZE_STROKE_FILL_OUTLINE_SLANT"})
target=np.zeros((H,W),bool)
for layer in layers: target|=(np.asarray(layer.getchannel("A"))>0)
target_overlap=int(np.count_nonzero((np.asarray(layers[0].getchannel("A"))>0)&(np.asarray(layers[1].getchannel("A"))>0)))
if target_overlap: raise RuntimeError(("target overlap",target_overlap))

# Encode full temporary DXT5, then splice only exact-row-safe blocks into source.
raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
tmp_png=Path("/tmp/D41_final_raw.png"); tmp_dds=Path("/tmp/D41_final_nv.dds")
raw.save(tmp_png)
subprocess.run(["/usr/bin/nvcompress","-bc3","-nomips",str(tmp_png),str(tmp_dds)],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
tb=tmp_dds.read_bytes(); meta(tb)

allowed=np.zeros((H,W),bool)
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]; allowed[y0:y1,x0:x1]=True
allowed_raw=np.flipud(allowed); srcmask_raw=np.flipud(source_mask); target_raw=np.flipud(target); source_raw_alpha=np.flipud(sa[:,:,3])
bw=W//4; bh=H//4
outb=bytearray(sb); target_blocks=set(); source_only_full=set(); partial_blocks=set()

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
        x=bx*4
        am=allowed_raw[y:y+4,x:x+4]
        if not np.any(am): continue
        sm=srcmask_raw[y:y+4,x:x+4]; tm=target_raw[y:y+4,x:x+4]
        if not np.any(sm) and not np.any(tm): continue
        off=128+(by*bw+bx)*16
        if np.any(tm):
            if not np.all(am): raise RuntimeError(("target in partial block",bx,by))
            outb[off:off+16]=tb[off:off+16]; target_blocks.add((bx,by)); continue
        if np.all(am):
            nb=tb[off:off+8]+sb[off+8:off+16]
            if nb[8:]!=sb[off+8:off+16]: raise RuntimeError("source-only color changed")
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

guard=np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
residue=int(np.count_nonzero(source_mask&(da[:,:,3]>16)&~guard))
if residue: raise RuntimeError(("source residue",residue))

# Decoded exact line-wise bbox/size and positive-gap checks.
decoded_masks=[]
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]
    cm=da[y0:y1,x0:x1,3]>1
    yy,xx=np.nonzero(cm)
    if not len(xx): raise RuntimeError(("decoded row empty",row["n"]))
    db=[x0+int(xx.min()),y0+int(yy.min()),x0+int(xx.max())+1,y0+int(yy.max())+1]
    dw,dh=db[2]-db[0],db[3]-db[1]
    if db[0]<x0 or db[1]<y0 or db[2]>x1 or db[3]>y1 or dw>row["source_width"] or dh>row["source_height"]:
        raise RuntimeError(("decoded row gate",row["n"],row["original_bbox"],db))
    row.update({"decoded_localized_bbox":db,"decoded_localized_width":dw,"decoded_localized_height":dh,
                "decoded_containment":"PASS","decoded_size_ceiling":"PASS"})
    dm=np.zeros((H,W),bool); dm[y0:y1,x0:x1]=cm; decoded_masks.append(dm)
decoded_overlap=int(np.count_nonzero(decoded_masks[0]&decoded_masks[1]))
if decoded_overlap: raise RuntimeError(("decoded row overlap",decoded_overlap))
gap=rows[1]["decoded_localized_bbox"][1]-rows[0]["decoded_localized_bbox"][3]
if gap<=0: raise RuntimeError(("decoded nonpositive row gap",gap))

def mask(m): return Image.fromarray((m.astype(np.uint8)*255),"L")
source_mask_png=out/"D41D0B1_SOURCE_TEXT_MASK.png"; mask(source_mask).save(source_mask_png)
allowed_png=out/"D41D0B1_ALLOWED_TEXT_REGION_MASK.png"; mask(allowed).save(allowed_png)
protected_png=out/"D41D0B1_PROTECTED_MASK.png"; mask(~allowed).save(protected_png)
target_png=out/"D41D0B1_TARGET_TEXT_MASK.png"; mask(target).save(target_png)
clean_png=out/"D41D0B1_CLEAN_PLATE.png"; clean.save(clean_png)
src_png=Path("/tmp/D41_source.png"); final_png=Path("/tmp/D41_final.png"); src.save(src_png); dec.save(final_png)
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(src_png),str(clean_png),str(source_mask_png),"--report",str(out/"B_PRODUCTION43_CLEAN_PLATE_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(src_png),str(final_png),str(allowed_png),"--protected-mask",str(protected_png),"--report",str(out/"B_PRODUCTION43_FINAL_MASK_VALIDATION.json")],check=True)

def comp(im,bg=(64,64,64,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def card(label,im,bg=(64,64,64,255)):
    v=comp(im,bg); c=Image.new("RGB",(W,H+28),"white"); c.paste(v,(0,28)); ImageDraw.Draw(c).text((5,5),label,fill="black"); return c
cards=[card("SOURCE",src),card("CLEAN",clean),card("FINAL",dec),card("FINAL_WHITE",dec,(255,255,255,255))]
sheet=Image.new("RGB",(W*2,(H+28)*2),"white")
sheet.paste(cards[0],(0,0)); sheet.paste(cards[1],(W,0)); sheet.paste(cards[2],(0,H+28)); sheet.paste(cards[3],(W,H+28))
sheet.save(out/"B_PRODUCTION43_D41_COMPARE.jpg",quality=96)

contacts=[]
for row in rows:
    bb=row["original_bbox"]; p=12; cr=(max(0,bb[0]-p),max(0,bb[1]-p),min(W,bb[2]+p),min(H,bb[3]+p))
    ims=[comp(z).crop(cr) for z in [src,clean,dec]]
    ims=[x.resize((x.width*2,x.height*2),Image.Resampling.NEAREST) for x in ims]
    c=Image.new("RGB",(sum(x.width for x in ims)+12,max(x.height for x in ims)+28),"white")
    xx=0
    for im in ims: c.paste(im,(xx,28)); xx+=im.width+6
    ImageDraw.Draw(c).text((4,4),row["source"]+" -> "+row["korean"],fill="black")
    contacts.append(c)
cs=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4),"white")
yy=0
for c in contacts: cs.paste(c,(0,yy)); yy+=c.height+4
cs.save(out/"B_PRODUCTION43_D41_ROW_CONTACT_2X.jpg",quality=96)

src_raw=Image.open(src_dds).convert("RGBA"); dec_raw=Image.open(candidate).convert("RGBA")
raw_cards=[card("SOURCE_RAW_MIRROR_Y",src_raw),card("FINAL_RAW_MIRROR_Y",dec_raw)]
raw_sheet=Image.new("RGB",(W,(H+28)*2),"white")
raw_sheet.paste(raw_cards[0],(0,0)); raw_sheet.paste(raw_cards[1],(0,H+28))
raw_sheet.save(out/"B_PRODUCTION43_D41_RAW_COMPARE.jpg",quality=96)

patch=target_blocks|source_only_full|partial_blocks; changed=0; outside_patch=0
for by in range(bh):
    for bx in range(bw):
        off=128+(by*bw+bx)*16
        if sb[off:off+16]!=outb[off:off+16]:
            changed+=1
            if (bx,by) not in patch: outside_patch+=1
if outside_patch: raise RuntimeError(("compressed outside patch",outside_patch))

report={"schema_version":1,"role":"B","run":run,"queue_index":112,"asset":asset,
 "readiness_tier":"RENDER_READY_COMPLETED_SAME_INVOCATION",
 "source_url":url,"source_sha256":sha(src_dds),"candidate_sha256":cand_sha,
 "candidate_path":str(candidate.relative_to(repo)),
 "method":"canonical 2048x256 DXT5 HD source; exact two source-line alpha/effect bboxes; alpha-zero clean plate with hidden RGB retained; two fresh Hangul lines preserving shared source white/navy/right-slanted typography; target color changes only in fully allowed BC3 blocks; source-only cleanup alpha-only; decoded line-wise QA",
 "structure":{"width":W,"height":H,"format":"DXT5","mipmaps":1,"header_128_exact":bytes(outb[:128])==sb[:128],"raw_orientation":"mirror_y"},
 "palette":{"white":white,"dark":dark},"rows":rows,
 "multi_line":{"source_lines":2,"localized_lines":2,"shared_font_size":fs,"shared_stroke_width":stroke,"shared_slant":slant,
               "decoded_row_gap":gap,"localized_overlap_pixels":target_overlap,"decoded_overlap_pixels":decoded_overlap,
               "style_consistency":"PASS_SHARED_SOURCE_FAMILY"},
 "containment":{"elements_total":2,"elements_pass":2,"visible_pixels_outside_original_bboxes":visible_out,
                "alpha_changed_pixels_outside_original_bboxes":alpha_out,
                "source_residue_pixels_alpha_gt16_outside_target_guard":residue,"status":"PASS"},
 "compressed_patch":{"target_reencoded_blocks":len(target_blocks),"source_only_full_alpha_blocks":len(source_only_full),
                     "partial_alpha_only_blocks":len(partial_blocks),"changed_blocks":changed,
                     "changed_blocks_outside_patch":outside_patch,"source_only_color_bytes_preserved":True,
                     "partial_color_bytes_preserved":True,"status":"PASS"},
 "manual_visual_qa":"PENDING_CONTROLLER_SELF_QA","RUNTIME_VALIDATION":"UNTESTED",
 "status":"B_PRODUCTION43_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"}
(out/"B_PRODUCTION43_D41_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"D41D0B1","index":112,"candidate_sha256":cand_sha,"bbox_size_pass":"2/2",
 "visible_outside":visible_out,"alpha_outside":alpha_out,"source_residue":residue,
 "localized_overlap":target_overlap,"decoded_overlap":decoded_overlap,"decoded_row_gap":gap,
 "changed_blocks_outside_patch":outside_patch,"worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":"localization/graphics/role_B/20261005-B-PRODUCTION43/B_PRODUCTION43_D41_REPORT.json"}
(wr/"B_PRODUCTION43_D41D0B1.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
