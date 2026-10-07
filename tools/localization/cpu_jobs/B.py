#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request,statistics
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B hosted worker only")

repo=Path.cwd()
run="20261007-B-MANUALQA227-DDF0392A"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/DDF0392A_256x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
src_dds=Path("/tmp/DDF0392A_HD.dds")
atlas_path=Path("/tmp/DDF0392A_atlas.json")
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/DDF0392A_256x512.dds",src_dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_DDF0392A_256x512_atlas.json",atlas_path)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def meta(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    mips=struct.unpack_from("<I",b,28)[0]; fourcc=b[84:88]
    need=128+((w+3)//4)*((h+3)//4)*16
    if fourcc!=b"DXT5" or mips not in (0,1) or len(b)!=need:
        raise RuntimeError(("unexpected DDS",w,h,mips,fourcc,len(b),need))
    return w,h,mips,fourcc

sb=src_dds.read_bytes(); ab=atlas_path.read_bytes()
EXPECTED_BEFORE="e0d04c144aec92aad090dd2d5f7895f956a1001cafca319d1b0f4681fd7e0fea"
if not candidate.exists():
    raise RuntimeError("current q222 candidate missing")
before_bytes=candidate.read_bytes()
if hashlib.sha256(before_bytes).hexdigest()!=EXPECTED_BEFORE:
    raise RuntimeError(("q222 candidate drift",hashlib.sha256(before_bytes).hexdigest(),EXPECTED_BEFORE))
W,H,_,_=meta(sb)
if (W,H)!=(1024,2048): raise RuntimeError(("unexpected dimensions",W,H))
src=Image.open(src_dds).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
regs={r["idx"]:r for r in json.loads(ab.decode())["regions"]}

# B86 controller-reviewed readable-order semantic binding.
specs=[
 (0,"OutRun Mode / 15 C.","아웃런 모드 / 15코스"),
 (1,"OutRun 1986","아웃런 1986"),
 (2,"Journey Mode / Random","저니 모드 / 무작위"),
]
protected_rows={3:"Who Are You?",4:"Splash Wave",5:"Shiny World",6:"Shake The Street",7:"Rush A Difficulty",8:"Risky Ride",9:"Passing Breeze"}
protected_policy="Song-title rows 3..9 remain pixel-exact original English; Ferrari model rows 10..24 remain pixel-exact original."

rows=[]; source_masks=[]; rgb_samples=[]
for idx,en,ko in specs:
    x,y,cw,ch=regs[idx]["rect"]
    cell_alpha=sa[y:y+ch,x:x+cw,3]>0
    ys,xs=np.nonzero(cell_alpha)
    if not len(xs): raise RuntimeError(("empty source target",idx,en))
    bb=[x+int(xs.min()),y+int(ys.min()),x+int(xs.max())+1,y+int(ys.max())+1]
    m=np.zeros((H,W),bool); m[y:y+ch,x:x+cw]=cell_alpha
    # Keep only the exact alpha footprint within its exact source bbox.
    m[:,:bb[0]]=False; m[:,bb[2]:]=False; m[:bb[1],:]=False; m[bb[3]:,:]=False
    source_masks.append(m)
    pix=sa[m]
    sel=pix[pix[:,3]>=128]
    if len(sel): rgb_samples.extend(sel[:,:3].tolist())
    rows.append({"region_idx":idx,"source":en,"korean":ko,"cell":[x,y,cw,ch],"original_bbox":bb,"source_mask_pixels":int(np.count_nonzero(m))})

source_mask=np.zeros((H,W),bool)
for m in source_masks: source_mask|=m
if sum(int(np.count_nonzero(m)) for m in source_masks)!=int(np.count_nonzero(source_mask)):
    raise RuntimeError("source target masks overlap")

# All non-target canonical rows are protected by decoded pixel equality.
allowed=np.zeros((H,W),bool)
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]; allowed[y0:y1,x0:x1]=True

clean_arr=sa.copy()
clean_arr[source_mask,3]=0
clean=Image.fromarray(clean_arr,"RGBA")

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra","libnvtt-bin"],check=True)
FONT=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
if not FONT or not Path(FONT).exists() or "NotoSansCJK" not in Path(FONT).name:
    raise RuntimeError(("CJK black unavailable",FONT))
if not Path("/usr/bin/nvcompress").exists(): raise RuntimeError("nvcompress unavailable")

if not rgb_samples: raise RuntimeError("source style sample empty")
fill_rgb=tuple(int(round(statistics.median(v[k] for v in rgb_samples))) for k in range(3))
fill=(fill_rgb[0],fill_rgb[1],fill_rgb[2],255)

def render(text,bb,fs):
    x0,y0,x1,y1=bb
    bx0=((x0+3)//4)*4; by0=((y0+3)//4)*4; bx1=(x1//4)*4; by1=(y1//4)*4
    aw,ah=bx1-bx0,by1-by0
    if aw<16 or ah<16: raise RuntimeError(("no block-safe bbox",bb,[bx0,by0,bx1,by1]))
    f=ImageFont.truetype(FONT,fs)
    d=ImageDraw.Draw(Image.new("L",(8,8),0))
    tb=d.textbbox((0,0),text,font=f)
    pad=4
    a=Image.new("L",(max(8,tb[2]-tb[0]+2*pad),max(8,tb[3]-tb[1]+2*pad)),0)
    ImageDraw.Draw(a).text((pad-tb[0],pad-tb[1]),text,font=f,fill=255)
    ab=a.getbbox()
    if not ab: return None
    a=a.crop(ab)
    tile=Image.new("RGBA",a.size,fill); tile.putalpha(a)
    if tile.width>aw-4 or tile.height>ah-4: return None
    layer=Image.new("RGBA",(W,H),(0,0,0,0))
    px=bx0+2
    py=by0+(ah-tile.height)//2
    layer.alpha_composite(tile,(px,py))
    lb=layer.getchannel("A").getbbox()
    if not lb: return None
    if not(lb[0]>x0 and lb[1]>y0 and lb[2]<x1 and lb[3]<y1): return None
    return layer,list(lb),[bx0,by0,bx1,by1]

# Current strict visual policy supersedes C159/B227's historical "one shared size"
# assumption: the English source intentionally uses different per-row heights (52/44/58px).
# Fit each Korean row independently to the largest native font size that remains inside the
# exact block-safe source bbox. This restores source-relative hierarchy without upscaling an
# old Korean bitmap or allowing a single short row to force every row undersized.
rendered=[]
for row in rows:
    chosen=None
    for fs in range(64,15,-1):
        z=render(row["korean"],row["original_bbox"],fs)
        if z is not None:
            chosen=(z,fs)
            break
    if chosen is None:
        raise RuntimeError(("per-row native fit failed",row["source"]))
    (layer,lb,blockbb),row_fs=chosen
    rendered.append((layer,lb,blockbb,row_fs))

final=clean.copy(); layers=[]; target=np.zeros((H,W),bool)
for row,(layer,lb,blockbb,row_fs) in zip(rows,rendered):
    for old in layers:
        if ImageChops.multiply(layer.getchannel("A"),old.getchannel("A")).getbbox():
            raise RuntimeError("localized overlap")
    layers.append(layer); final.alpha_composite(layer)
    tm=np.asarray(layer.getchannel("A"))>0; target|=tm
    ob=row["original_bbox"]; sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    if not(lb[0]>=ob[0] and lb[1]>=ob[1] and lb[2]<=ob[2] and lb[3]<=ob[3] and lw<=sw and lh<=sh):
        raise RuntimeError(("size gate",row["source"],ob,lb))
    row.update({"localized_bbox":lb,"source_width":sw,"source_height":sh,"localized_width":lw,"localized_height":lh,
      "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","font_file":Path(FONT).name,
      "font_size":row_fs,"fill_rgba":fill,"alignment":"left","block_safe_bbox":blockbb,"rework_status":"B227_NEW_EXACT_HD_DXT5_CANDIDATE"})

# Encode full raw mirror-y image, then splice only exact-safe BC3 blocks.
raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
tmp_png=Path("/tmp/DDF_final_raw.png"); tmp_dds=Path("/tmp/DDF_final_nv.dds")
raw.save(tmp_png)
subprocess.run(["/usr/bin/nvcompress","-bc3","-nomips",str(tmp_png),str(tmp_dds)],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
tb=tmp_dds.read_bytes(); meta(tb)

allowed_raw=np.flipud(allowed); srcmask_raw=np.flipud(source_mask); target_raw=np.flipud(target); source_raw_alpha=np.flipud(sa[:,:,3])
bw=W//4; bh=H//4; outb=bytearray(sb)
target_blocks=set(); source_only_full=set(); partial_blocks=set()

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
            # Source-only cleanup: take encoded clean alpha, preserve source color bytes exactly.
            outb[off:off+16]=tb[off:off+8]+sb[off+8:off+16]; source_only_full.add((bx,by)); continue
        if not np.any(sm): continue
        # Boundary source cleanup: preserve endpoints/color bytes; only remap source alpha indices to the existing transparent index.
        ob=bytes(outb[off:off+16]); idx=aidx(ob); sa4=source_raw_alpha[y:y+4,x:x+4]
        zero=[idx[yy*4+xx] for yy in range(4) for xx in range(4) if sa4[yy,xx]<=1]
        if not zero: raise RuntimeError(("partial block has no transparent alpha index",bx,by))
        zi=Counter(zero).most_common(1)[0][0]
        for yy in range(4):
            for xx in range(4):
                if sm[yy,xx]: idx[yy*4+xx]=zi
        nb=seta(ob,idx)
        if nb[8:]!=ob[8:] or nb[:2]!=ob[:2]: raise RuntimeError("partial endpoint/color drift")
        outb[off:off+16]=nb; partial_blocks.add((bx,by))

candidate.write_bytes(outb); cand_sha=sha(candidate)
dec=Image.open(candidate).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
da=np.asarray(dec,dtype=np.uint8)

# Exact protected-pixel gate: every pixel outside the union of exact source bboxes must decode byte-identically.
diff=np.any(sa!=da,axis=2)
diff_out=int(np.count_nonzero(diff & ~allowed))
alpha_out=int(np.count_nonzero((sa[:,:,3]!=da[:,:,3]) & ~allowed))
visible_out=int(np.count_nonzero((da[:,:,3]>1) & (sa[:,:,3]<=1) & ~allowed))
if diff_out or alpha_out or visible_out:
    raise RuntimeError(("protected decoded drift",diff_out,alpha_out,visible_out))

# No source English alpha may survive outside a 2px target guard inside target bboxes.
guard=np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
residue=int(np.count_nonzero(source_mask & (da[:,:,3]>8) & ~guard))
if residue: raise RuntimeError(("source residue",residue))

# Decode remeasure each row, excluding protected rows entirely.
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]
    cm=da[y0:y1,x0:x1,3]>1
    ys,xs=np.nonzero(cm)
    if not len(xs): raise RuntimeError(("decoded target empty",row["source"]))
    db=[x0+int(xs.min()),y0+int(ys.min()),x0+int(xs.max())+1,y0+int(ys.max())+1]
    dw,dh=db[2]-db[0],db[3]-db[1]
    if db[0]<x0 or db[1]<y0 or db[2]>x1 or db[3]>y1 or dw>row["source_width"] or dh>row["source_height"]:
        raise RuntimeError(("decoded size gate",row["source"],row["original_bbox"],db))
    row["decoded_localized_bbox"]=db; row["decoded_localized_width"]=dw; row["decoded_localized_height"]=dh
    row["decoded_containment"]="PASS"; row["decoded_size_ceiling"]="PASS"

# Explicit protected song/Ferrari cells decoded equality.
preserved={}
for idx in range(3,25):
    x,y,cw,ch=regs[idx]["rect"]
    preserved[str(idx)]=int(np.count_nonzero(np.any(sa[y:y+ch,x:x+cw]!=da[y:y+ch,x:x+cw],axis=2)))
if any(preserved.values()): raise RuntimeError(("protected row changed",preserved))

# Compressed patch accounting.
changed_blocks=0; outside_patch=0; patch=target_blocks|source_only_full|partial_blocks
for by in range(bh):
    for bx in range(bw):
        off=128+(by*bw+bx)*16
        if sb[off:off+16]!=outb[off:off+16]:
            changed_blocks+=1
            if (bx,by) not in patch: outside_patch+=1
if outside_patch: raise RuntimeError(("compressed outside patch",outside_patch))

def mask(m): return Image.fromarray((m.astype(np.uint8)*255),"L")
source_mask_png=out/"DDF_SOURCE_TEXT_MASK.png"; mask(source_mask).save(source_mask_png)
allowed_png=out/"DDF_ALLOWED_TEXT_REGION_MASK.png"; mask(allowed).save(allowed_png)
protected_png=out/"DDF_PROTECTED_MASK.png"; mask(~allowed).save(protected_png)
target_png=out/"DDF_TARGET_TEXT_MASK.png"; mask(target).save(target_png)
clean_png=out/"DDF_CLEAN_PLATE.png"; clean.save(clean_png)
src_png=Path("/tmp/DDF_source.png"); final_png=Path("/tmp/DDF_final.png"); src.save(src_png); dec.save(final_png)
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(src_png),str(clean_png),str(source_mask_png),"--report",str(out/"B227_CLEAN_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(src_png),str(final_png),str(allowed_png),"--protected-mask",str(protected_png),"--report",str(out/"B227_FINAL_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"B227_CLEAN_VALIDATION.json").read_text()); finalrep=json.loads((out/"B227_FINAL_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS" or finalrep["status"]!="PASS": raise RuntimeError(("validator",cleanrep["status"],finalrep["status"]))

def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
# Full readable proof.
stack=Image.new("RGB",(512,3*1050),"white")
for i,(label,im) in enumerate([("SOURCE",src),("CLEAN",clean),("FINAL",dec)]):
    z=comp(im).resize((512,1024),Image.Resampling.NEAREST); stack.paste(z,(0,i*1050+26)); ImageDraw.Draw(stack).text((5,i*1050+5),label,fill="black")
stack.save(out/"B227_DDF_SOURCE_CLEAN_FINAL.jpg",quality=96)
# Row contacts.
cards=[]
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]; p=12; cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[comp(z).crop(cr) for z in (src,clean,dec)]
    sc=min(2.0,1000/max(1,ims[0].width))
    ims=[z.resize((max(1,int(z.width*sc)),max(1,int(z.height*sc))),Image.Resampling.NEAREST) for z in ims]
    c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+34),"white"); xx=0
    for z in ims: c.paste(z,(xx,34)); xx+=z.width+6
    ImageDraw.Draw(c).text((5,5),row["source"]+" -> "+row["korean"],fill="black"); cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+4*(len(cards)-1)),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.save(out/"B227_DDF_ROW_CONTACT.jpg",quality=96)
# Raw mirror-Y proof.
src_raw=Image.open(src_dds).convert("RGBA"); dec_raw=Image.open(candidate).convert("RGBA")
rr=Image.new("RGB",(512,2*1050),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",src_raw),("FINAL_RAW_MIRROR_Y",dec_raw)]):
    z=comp(im).resize((512,1024),Image.Resampling.NEAREST); rr.paste(z,(0,i*1050+26)); ImageDraw.Draw(rr).text((5,i*1050+5),label,fill="black")
rr.save(out/"B227_DDF_RAW_COMPARE.jpg",quality=96)

report={
 "schema_version":1,"role":"B","run":run,"queue_index":222,"asset":asset,
 "readiness_tier":"EXISTING_CANDIDATE_MATERIAL_REWORK_CURRENT_POLICY_FALSE_NEGATIVE",
 "trigger":"PRE_INGAME_JPG_023_SOURCE_RELATIVE_SCALE_HIERARCHY_FALSE_NEGATIVE",
 "before_candidate_sha256":EXPECTED_BEFORE,
 "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/023_q222_DDF0392A.jpg",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":commit,"git_blob_sha1":blob(sb),"atlas_git_blob_sha1":blob(ab),"source_sha256":sha(src_dds)},
 "semantic_binding":{"localized":{"0":"OutRun Mode / 15 C.","1":"OutRun 1986","2":"Journey Mode / Random"},"translations":{"0":"아웃런 모드 / 15코스","1":"아웃런 1986","2":"저니 모드 / 무작위"},"protected_song_rows":protected_rows,"protected_rows_10_24":"Ferrari model names"},
 "song_title_policy":"PASS_PRESERVE_ORIGINAL_ENGLISH",
 "structure":{"width":W,"height":H,"format":"DXT5","mipmaps":1,"header_128_exact":bytes(outb[:128])==sb[:128],"raw_orientation":"mirror_y"},
 "source_style":{"family":"dark condensed upright mode labels","font_file":Path(FONT).name,"font_size_policy":"largest_native_per_row_inside_exact_block_safe_source_bbox","font_size_by_row":[r["font_size"] for r in rows],"fill_rgba":fill,"alignment":"left"},
 "rows":rows,"protected_region_changed_pixels":preserved,
 "clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "containment":{"elements_total":3,"elements_pass":3,"decoded_pixels_changed_outside_exact_source_bboxes":diff_out,"alpha_changed_pixels_outside_exact_source_bboxes":alpha_out,"visible_pixels_outside_exact_source_bboxes":visible_out,"source_residue_pixels":residue,"status":"PASS"},
 "compressed_patch":{"target_reencoded_blocks":len(target_blocks),"source_only_full_alpha_blocks":len(source_only_full),"partial_alpha_only_blocks":len(partial_blocks),"changed_blocks":changed_blocks,"changed_blocks_outside_patch":outside_patch,"partial_endpoints_and_color_bytes_preserved":True,"status":"PASS"},
 "candidate_sha256":cand_sha,"candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","ordered_generation_gate":{"plate_restoration":"PASS_EXACT_TRANSPARENT_CLEAN_REBUILT","slant_direction":"PASS_SOURCE_UPRIGHT","scale_hierarchy":"PENDING_CONTROLLER_MAX_NATIVE_PER_ROW","weight_effects":"PASS_SOURCE_DARK_PLAIN_FAMILY","clipping":"PASS_POSITIVE_MARGIN","protected_art":"PASS_ROWS_3_24_PIXEL_EXACT","flip_y_raw":"EVIDENCE_WRITTEN","immediate_readability":"PENDING_CONTROLLER"},"RUNTIME_VALIDATION":"UNTESTED",
 "status":"B227_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
}
(out/"B227_DDF_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"index":222,"asset":"DDF0392A","source_sha256":sha(src_dds),"candidate_sha256":cand_sha,"localized_physical_elements":3,
 "bbox_size_positive_margin":"3/3","clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],
 "source_residue":residue,"decoded_changed_outside":diff_out,"alpha_outside":alpha_out,"visible_outside":visible_out,
 "protected_rows_changed":sum(preserved.values()),"changed_blocks_outside_patch":outside_patch,
 "worker_status":report["status"],"runtime_validation":"UNTESTED","before_candidate_sha256":EXPECTED_BEFORE,"report":f"localization/graphics/role_B/{run}/B227_DDF_REPORT.json"}
(wr/"B227_DDF0392A.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False))
