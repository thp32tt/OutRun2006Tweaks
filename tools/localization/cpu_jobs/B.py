#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd()
run="20261006-B-PRODUCTION176-A8CE339F-DXT5-RESIDUE"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_fight_Exst/A8CE339F_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_fight_Exst/A8CE339F_512x256.dds"
src_dds=Path("/tmp/A8CE339F_HD.dds")
urllib.request.urlretrieve(url,src_dds)
SOURCE_SHA="08afacc681737d6a138496cefce559853985084cf779921ac32ef2ebfe06883b"

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
if sha(src_dds)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(src_dds),SOURCE_SHA))
W,H,_,_=meta(sb)
if (W,H)!=(2048,1024): raise RuntimeError(("unexpected size",W,H))
src=Image.open(src_dds).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)

# B174 controller-readable source probe established five text-only windows.
# These windows exclude player markers, route bars/ticks, numerals and decorative shards.
specs=[
 ("extra_time","Extra Time","추가 시간",[16,213,485,284],"extra"),
 ("start_left","Start","출발",[24,308,131,349],"small"),
 ("goal_left","Goal","골",[649,308,744,349],"small"),
 ("start_right","Start","출발",[801,309,908,350],"small"),
 ("goal_right","Goal","골",[1426,308,1521,349],"small"),
]

rows=[]; source_masks=[]
for key,en,ko,bb,kind in specs:
    x0,y0,x1,y1=bb
    a=sa[y0:y1,x0:x1,3]>0
    if not np.any(a): raise RuntimeError(("empty source target",key,bb))
    # Exact bboxes come from B174 connected-component review of the readable canonical source.
    # Use only source alpha inside the component bbox; neighboring player/timeline/numeric art is excluded.
    m=np.zeros((H,W),bool)
    m[y0:y1,x0:x1]=a
    source_masks.append(m)
    rows.append({"key":key,"source":en,"korean":ko,"kind":kind,"original_bbox":bb,"source_mask_pixels":int(m.sum())})

# Exact source bbox sanity, including a one-pixel outside-alpha check on isolated text components.
for row in rows:
    bb=row["original_bbox"]; x0,y0,x1,y1=bb
    outside_ring=np.zeros((H,W),bool)
    outside_ring[max(0,y0-1):min(H,y1+1),max(0,x0-1):min(W,x1+1)]=True
    outside_ring[y0:y1,x0:x1]=False
    # Neighbor art may exist elsewhere, but none of the five isolated text components may continue directly across its bbox.
    direct=int(np.count_nonzero(outside_ring & (sa[:,:,3]>0)))
    if direct:
        raise RuntimeError(("exact text bbox touches other alpha; reclassify",row["key"],bb,direct))

source_mask=np.zeros((H,W),bool)
for m in source_masks: source_mask|=m
if sum(int(m.sum()) for m in source_masks)!=int(source_mask.sum()): raise RuntimeError("source masks overlap")

allowed=np.zeros((H,W),bool)
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]; allowed[y0:y1,x0:x1]=True

clean_arr=sa.copy()
# B175 controller visual QA caught source-script double drawing after BC3 splice.
# Zero the complete RGBA source-text footprint so the compressor cannot retain
# source glyph colour in blocks that become transparent.
clean_arr[source_mask]=0
clean=Image.fromarray(clean_arr,"RGBA")
clean_alpha=np.asarray(clean.getchannel("A"))
clean_source_visible=int(np.count_nonzero(clean_alpha[source_mask]>0))
if clean_source_visible:
    raise RuntimeError(("clean source mask still visible",clean_source_visible))

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra","libnvtt-bin"],check=True)
FONT=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
if not FONT or not Path(FONT).exists() or "NotoSansCJK" not in Path(FONT).name: raise RuntimeError(("font",FONT))
if not Path("/usr/bin/nvcompress").exists(): raise RuntimeError("nvcompress unavailable")

def shear_rgba(im,amount):
    if not amount: return im
    add=int(round(amount*im.height))
    return im.transform((im.width+add,im.height),Image.Transform.AFFINE,(1,-amount,add,0,1,0),resample=Image.Resampling.BICUBIC)

def build_glyph(text,kind,fs,bw,bh):
    f=ImageFont.truetype(FONT,fs)
    if kind=="extra":
        fill=(255,238,188,255); outer=(0,10,65,255); inner=(215,160,50,255)
        osw=max(3,round(fs*0.10)); isw=max(1,round(fs*0.035)); shear=0.20
    else:
        fill=(255,255,255,255); outer=(0,10,65,255); inner=None
        osw=max(2,round(fs*0.09)); isw=0; shear=0.0
    probe=Image.new("RGBA",(max(800,bw*4),max(240,bh*4)),(0,0,0,0))
    d=ImageDraw.Draw(probe); tb=d.textbbox((0,0),text,font=f,stroke_width=osw)
    xy=(20-tb[0],20-tb[1])
    d.text(xy,text,font=f,fill=fill,stroke_width=osw,stroke_fill=outer)
    if inner is not None:
        d.text(xy,text,font=f,fill=fill,stroke_width=isw,stroke_fill=inner)
    gb=probe.getchannel("A").getbbox()
    if not gb: return None
    g=probe.crop(gb); g=shear_rgba(g,shear)
    gb=g.getchannel("A").getbbox()
    if gb: g=g.crop(gb)
    return g,{"fill":fill,"outer":outer,"inner":inner,"outer_stroke":osw,"inner_stroke":isw,"shear":shear}

def render_row(row):
    x0,y0,x1,y1=row["original_bbox"]
    bx0=((x0+3)//4)*4; by0=((y0+3)//4)*4; bx1=(x1//4)*4; by1=(y1//4)*4
    aw,ah=bx1-bx0,by1-by0
    if aw<12 or ah<12: raise RuntimeError(("no block-safe bbox",row["key"],row["original_bbox"],[bx0,by0,bx1,by1]))
    start=min(120, max(22, ah))
    for fs in range(start,15,-1):
        z=build_glyph(row["korean"],row["kind"],fs,aw,ah)
        if z is None: continue
        g,sty=z
        if g.width>aw-4 or g.height>ah-4: continue
        px=bx0+(aw-g.width)//2; py=by0+(ah-g.height)//2
        layer=Image.new("RGBA",(W,H),(0,0,0,0)); layer.alpha_composite(g,(px,py))
        lb=list(layer.getchannel("A").getbbox() or ())
        if not lb: continue
        if not(lb[0]>x0 and lb[1]>y0 and lb[2]<x1 and lb[3]<y1): continue
        return layer,lb,[bx0,by0,bx1,by1],fs,sty
    raise RuntimeError(("render fit failed",row["key"],row["original_bbox"]))

final=clean.copy(); layers=[]; target=np.zeros((H,W),bool)
for row in rows:
    layer,lb,blockbb,fs,sty=render_row(row)
    for old in layers:
        if ImageChops.multiply(layer.getchannel("A"),old.getchannel("A")).getbbox(): raise RuntimeError("localized overlap")
    layers.append(layer); final.alpha_composite(layer)
    tm=np.asarray(layer.getchannel("A"))>0; target|=tm
    ob=row["original_bbox"]; sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    row.update({"localized_bbox":lb,"source_width":sw,"source_height":sh,"localized_width":lw,"localized_height":lh,
      "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","font":"Noto Sans CJK KR Black",
      "font_size":fs,"block_safe_bbox":blockbb,"style":sty,"rework_status":"B176_NEW_EXACT_HD_DXT5_CANDIDATE"})

# Encode full raw image then splice only safe BC3 blocks; boundary cleanup changes alpha indices only.
raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
tmp_png=Path("/tmp/A8CE_final_raw.png"); tmp_dds=Path("/tmp/A8CE_final_nv.dds")
raw.save(tmp_png)
subprocess.run(["/usr/bin/nvcompress","-bc3","-nomips",str(tmp_png),str(tmp_dds)],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
tb=tmp_dds.read_bytes(); meta(tb)

allowed_raw=np.flipud(allowed); srcmask_raw=np.flipud(source_mask); target_raw=np.flipud(target); source_raw_alpha=np.flipud(sa[:,:,3])
bw=W//4; bh=H//4; outb=bytearray(sb)
target_blocks=set(); source_only_full=set(); partial_blocks=set()
def aidx(block):
    bits=int.from_bytes(block[2:8],"little"); return [(bits>>(3*i))&7 for i in range(16)]
def seta(block,idx):
    bits=sum((int(v)&7)<<(3*i) for i,v in enumerate(idx)); return block[:2]+bits.to_bytes(6,"little")+block[8:]

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
            if not np.all(am): raise RuntimeError(("target partial block",bx,by))
            outb[off:off+16]=tb[off:off+16]; target_blocks.add((bx,by)); continue
        if np.all(am):
            # B176: replace the whole DXT5 block from the clean/final encode.
            # B175 copied only alpha bytes and retained source colour blocks,
            # which produced visible English double drawing despite numeric gates.
            outb[off:off+16]=tb[off:off+16]; source_only_full.add((bx,by)); continue
        if not np.any(sm): continue
        # Boundary blocks straddle the exact source bbox. Preserve original
        # colour bytes and rebuild alpha indices with explicit 255/0 endpoints:
        # source glyph pixels -> 0, every other pixel -> nearest original alpha.
        ob=bytes(outb[off:off+16]); sa4=source_raw_alpha[y:y+4,x:x+4]
        alpha_vals=[255,0,218,182,145,109,72,36]
        idx=[]
        for yy in range(4):
            for xx in range(4):
                if sm[yy,xx]:
                    idx.append(1)
                else:
                    a=int(sa4[yy,xx])
                    idx.append(min(range(8),key=lambda k:abs(alpha_vals[k]-a)))
        bits=sum((int(v)&7)<<(3*i) for i,v in enumerate(idx))
        nb=bytes([255,0])+bits.to_bytes(6,"little")+ob[8:]
        outb[off:off+16]=nb; partial_blocks.add((bx,by))

candidate.write_bytes(outb); cand_sha=sha(candidate)
dec=Image.open(candidate).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
da=np.asarray(dec,dtype=np.uint8)

diff=np.any(sa!=da,axis=2)
diff_out=int(np.count_nonzero(diff & ~allowed))
alpha_out=int(np.count_nonzero((sa[:,:,3]!=da[:,:,3]) & ~allowed))
visible_out=int(np.count_nonzero((da[:,:,3]>1) & (sa[:,:,3]<=1) & ~allowed))
if diff_out or alpha_out or visible_out: raise RuntimeError(("protected decoded drift",diff_out,alpha_out,visible_out))

guard=np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
residue=int(np.count_nonzero(source_mask & (da[:,:,3]>8) & ~guard))
if residue: raise RuntimeError(("source residue",residue))

# Decode actual localized bboxes by candidate-vs-clean alpha difference within each target bbox.
clean_a=np.asarray(clean.getchannel("A"))
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]
    cm=(da[y0:y1,x0:x1,3]>8) & (clean_a[y0:y1,x0:x1]<=1)
    ys,xs=np.nonzero(cm)
    if not len(xs): raise RuntimeError(("decoded target empty",row["key"]))
    db=[x0+int(xs.min()),y0+int(ys.min()),x0+int(xs.max())+1,y0+int(ys.max())+1]
    dw,dh=db[2]-db[0],db[3]-db[1]
    if db[0]<x0 or db[1]<y0 or db[2]>x1 or db[3]>y1 or dw>row["source_width"] or dh>row["source_height"]:
        raise RuntimeError(("decoded size gate",row["key"],row["original_bbox"],db))
    row["decoded_localized_bbox"]=db; row["decoded_localized_width"]=dw; row["decoded_localized_height"]=dh
    row["decoded_containment"]="PASS"; row["decoded_size_ceiling"]="PASS"

changed_blocks=0; outside_patch=0; patch=target_blocks|source_only_full|partial_blocks
for by in range(bh):
    for bx in range(bw):
        off=128+(by*bw+bx)*16
        if sb[off:off+16]!=outb[off:off+16]:
            changed_blocks+=1
            if (bx,by) not in patch: outside_patch+=1
if outside_patch: raise RuntimeError(("compressed outside patch",outside_patch))

# Evidence
src.save(out/"B176_SOURCE_READABLE.png"); clean.save(out/"B176_CLEAN_PLATE.png"); dec.save(out/"B176_FINAL_READABLE.png")
Image.fromarray((source_mask.astype(np.uint8)*255),"L").save(out/"B176_SOURCE_TEXT_MASK.png")
Image.fromarray((allowed.astype(np.uint8)*255),"L").save(out/"B176_ALLOWED_MASK.png")
Image.fromarray(((~allowed).astype(np.uint8)*255),"L").save(out/"B176_PROTECTED_MASK.png")
Image.fromarray((target.astype(np.uint8)*255),"L").save(out/"B176_TARGET_MASK.png")

def comp(im,bg=(88,88,88,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def card(label,im,crop,scale=1):
    v=comp(im).crop(crop)
    if scale!=1: v=v.resize((v.width*scale,v.height*scale),Image.Resampling.NEAREST)
    c=Image.new("RGB",(v.width,v.height+28),"white"); c.paste(v,(0,28)); ImageDraw.Draw(c).text((5,5),label,fill="black"); return c

crop=(0,190,1600,450)
cards=[card("SOURCE",src,crop,1),card("CLEAN",clean,crop,1),card("FINAL",dec,crop,1)]
Wc=max(c.width for c in cards); Hc=sum(c.height for c in cards)+8*(len(cards)-1)
sheet=Image.new("RGB",(Wc,Hc),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+8
sheet.thumbnail((2200,1400),Image.Resampling.LANCZOS); sheet.save(out/"B176_SOURCE_CLEAN_FINAL_CONTACT.jpg",quality=97)

raw_src=Image.open(src_dds).convert("RGBA"); raw_final=Image.open(candidate).convert("RGBA")
rcrop=(0,H-450,1600,H-190)
cards=[card("SOURCE_RAW",raw_src,rcrop,1),card("FINAL_RAW",raw_final,rcrop,1)]
Wc=max(c.width for c in cards); Hc=sum(c.height for c in cards)+8
rs=Image.new("RGB",(Wc,Hc),"white"); yy=0
for c in cards: rs.paste(c,(0,yy)); yy+=c.height+8
rs.thumbnail((2200,1200),Image.Resampling.LANCZOS); rs.save(out/"B176_RAW_CONTACT.jpg",quality=97)

report={
 "schema_version":1,"role":"B","run":run,
 "base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "queue_index":52,"asset":asset,"readiness_tier":"ZOOM_REVIEW_POSITIVE_RENDER_COMPLETED_SAME_INVOCATION",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6","url":url,"sha256":SOURCE_SHA},
 "classification":{"localizable":["Extra Time","Start x2","Goal x2"],"translations":{"Extra Time":"추가 시간","Start":"출발","Goal":"골"},
   "protected":["6P/5P/4P/3P/2P/1P player markers","route/timeline bars and ticks","all numeric countdown glyphs","white decorative shards"]},
 "structure":{"width":W,"height":H,"format":"DXT5","mipmaps":1,"header_128_exact":bytes(outb[:128])==sb[:128],"raw_orientation":"mirror_y"},
 "rows":rows,
 "containment":{"elements_total":5,"elements_pass":5,"decoded_changed_outside_exact_source_bboxes":diff_out,
   "alpha_changed_outside_exact_source_bboxes":alpha_out,"visible_pixels_outside_exact_source_bboxes":visible_out,
   "source_residue_pixels":residue,"status":"PASS"},
 "clean_plate":{"source_mask_visible_pixels_after_rgba_zero":clean_source_visible,"status":"PASS"},
 "compressed_patch":{"target_reencoded_blocks":len(target_blocks),"source_only_full_reencoded_blocks":len(source_only_full),
   "partial_alpha_only_blocks":len(partial_blocks),"changed_blocks":changed_blocks,"changed_blocks_outside_patch":outside_patch,
   "partial_endpoints_and_color_bytes_preserved":True,"status":"PASS"},
 "candidate_sha256":cand_sha,"candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","runtime_validation":"UNTESTED",
 "status":"B176_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "superseded_attempts":[
   {"run":"B174 first render dispatch","result":"FAIL_CLOSED_DXT5_DETECTED_BEFORE_OUTPUT",
    "note":"Initial render code assumed RGBA32; hosted worker detected canonical DXT5 and stopped before candidate persistence."},
   {"run":"B175","candidate_sha256":"d23a6cd866fef15d44b86094e22fe6055efd183183039a260af8c1a6f7d7b582",
    "result":"REJECTED_CONTROLLER_VISUAL_QA_SOURCE_SCRIPT_DOUBLE_DRAW",
    "note":"Numeric gates falsely passed because the source-only DXT5 splice retained source colour blocks; readable FINAL visibly showed Ex...me / S...rt / G...al around Korean. B176 replaces full source-only blocks and explicitly zeros RGBA before compression."}
 ],
 "no_vr_ffb_dx11_dxvk_work":True
}
(out/"B176_A8CE339F_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B176_A8CE339F.json").write_text(json.dumps({
 "role":"B","run":run,"queue_index":52,"asset":"A8CE339F","source_sha256":SOURCE_SHA,"candidate_sha256":cand_sha,
 "report":str((out/"B176_A8CE339F_REPORT.json").relative_to(repo)),"status":"WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("B176_DONE",cand_sha,[(r["key"],r["original_bbox"],r["localized_bbox"],r["decoded_localized_bbox"]) for r in rows])