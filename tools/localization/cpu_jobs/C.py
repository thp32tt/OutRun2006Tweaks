#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,zipfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C135-EBFC709F"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/EBFC709F_512x256.dds"
srczip=repo/"localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip"
diag=json.loads((repo/"localization/graphics/role_C/20261005-C134-EBFC709F-DIAG/C134_EBFC_SOURCE_LINE_DIAGNOSTIC.json").read_text(encoding="utf-8"))
with zipfile.ZipFile(srczip) as z: sb=z.read(asset)
source_sha=hashlib.sha256(sb).hexdigest()
if source_sha!="ad7a1c21be17d1fa93463201a26a85a21899dbe1162d5c2748ddeb6136a4f9a0":
    raise RuntimeError(("source_sha",source_sha))
H=struct.unpack_from("<I",sb,12)[0]; W=struct.unpack_from("<I",sb,16)[0]; mips=struct.unpack_from("<I",sb,28)[0]
if (W,H)!=(2048,1024) or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,mips,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
alpha=sa[:,:,3]>0

def union_bbox(groups):
    return [min(g["bbox"][0] for g in groups),min(g["bbox"][1] for g in groups),max(g["bbox"][2] for g in groups),max(g["bbox"][3] for g in groups)]

small_line=diag["zones"]["small_zone"][0]
sg=small_line["xgroups"]
join_groups=[g for g in sg if g["bbox"][2] < 500]
create_groups=[g for g in sg if g["bbox"][0] > 800]
if len(join_groups)!=5 or len(create_groups)!=4:
    raise RuntimeError(("small_heading_group_count",len(join_groups),len(create_groups)))
small_join=union_bbox(join_groups)
small_create=union_bbox(create_groups)
large_create=union_bbox(diag["zones"]["large_zone"][0]["xgroups"])
large_join=union_bbox(diag["zones"]["large_zone"][1]["xgroups"])
expected_boxes={
 "join_small":[14,287,418,354],
 "create_small":[898,287,1420,354],
 "create_large":[24,695,1245,840],
 "join_large":[9,874,979,1019],
}
measured={"join_small":small_join,"create_small":small_create,"create_large":large_create,"join_large":large_join}
if measured!=expected_boxes:
    raise RuntimeError(("diagnostic_drift",measured,expected_boxes))

targets=[
 ("join_small","JOIN GAME","게임 참가",small_join,"small"),
 ("create_small","CREATE GAME","게임 만들기",small_create,"small"),
 ("create_large","CREATE GAME","게임 만들기",large_create,"large_blue"),
 ("join_large","JOIN GAME","게임 참가",large_join,"large_blue"),
]

def rect(shape,b):
    h,w=shape; x0,y0,x1,y1=map(int,b)
    m=np.zeros((h,w),bool); m[y0:y1,x0:x1]=True
    return m

def bbox(m):
    yy,xx=np.nonzero(m)
    if not len(xx): return None
    return [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]

def dil(m,px=1):
    return np.asarray(Image.fromarray((m.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(px*2+1)))>0

rows=[]; source_masks=[]; full_source=np.zeros((H,W),bool); allowed=np.zeros((H,W),bool)
for n,(key,en,ko,region_hint,family) in enumerate(targets,1):
    # C134 line diagnostics provide a coarse per-heading region. Recompute the
    # exact non-transparent glyph/effect bbox inside that region and use that
    # smaller bbox as the hard C containment/size ceiling.
    region=rect((H,W),region_hint)
    sm=region & alpha
    actual=bbox(sm)
    if actual is None:
        raise RuntimeError(("empty_source_heading",key,region_hint))
    # The exact bbox may be smaller than the line-scan y envelope because another
    # heading on the same scan line can have a deeper glyph. It may never escape.
    if not (actual[0]>=region_hint[0] and actual[1]>=region_hint[1] and actual[2]<=region_hint[2] and actual[3]<=region_hint[3]):
        raise RuntimeError(("source_bbox_escape",key,actual,region_hint))
    exact_region=rect((H,W),actual)
    sm=exact_region & alpha
    source_masks.append(sm); full_source|=sm; allowed|=exact_region
    px=sa[sm]
    med=[int(v) for v in np.median(px,axis=0)]
    rows.append({"n":n,"key":key,"source":en,"korean":ko,"style_family":family,
                 "diagnostic_region":region_hint,"original_bbox":actual,
                 "source_effect_pixels":int(np.count_nonzero(sm)),"source_median_rgba":med})

# Protected source sentences/artwork must remain outside exact target bboxes.
for i in range(len(source_masks)):
    for j in range(i+1,len(source_masks)):
        if np.any(source_masks[i]&source_masks[j]): raise RuntimeError(("source_overlap",i+1,j+1))

clean_a=sa.copy(); clean_a[full_source,3]=0
if np.any(clean_a[:,:,:3]!=sa[:,:,:3]): raise RuntimeError("clean RGB changed")
clean=Image.fromarray(clean_a,"RGBA")

font_path=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
if not font_path or not Path(font_path).exists() or "NotoSansCJK" not in Path(font_path).name:
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    font_path=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
if not font_path or "NotoSansCJK" not in Path(font_path).name:
    raise RuntimeError(("verified_korean_font_unavailable",font_path))

def render(row,sm):
    x0,y0,x1,y1=row["original_bbox"]; aw=x1-x0; ah=y1-y0
    px=sa[sm]; px=px[px[:,3]>0]
    med=np.median(px,axis=0)
    fill=tuple(int(v) for v in med)
    outline=fill
    d=ImageDraw.Draw(Image.new("L",(8,8),0))
    # Source headings are upright flat-color heavy sans. Preserve family by using
    # Noto CJK Black, same-color stroke, zero slant, centered within exact source bbox.
    start=min(260,max(18,int(ah*.94)))
    step=6 if row["style_family"]=="small" else 8
    for fs in range(start,9,-step):
        sw=max(1,round(fs*(0.035 if row["style_family"]=="small" else 0.025)))
        f=ImageFont.truetype(font_path,fs)
        # Font-coverage sanity: every non-space Korean character must have a non-empty glyph.
        for ch in set(row["korean"].replace(" ","")):
            if f.getbbox(ch) is None: raise RuntimeError(("missing_glyph",ch,Path(font_path).name))
        tb=d.textbbox((0,0),row["korean"],font=f,stroke_width=sw)
        pad=sw+4
        st=Image.new("L",(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad),0)
        fi=Image.new("L",st.size,0)
        pos=(pad-tb[0],pad-tb[1])
        ImageDraw.Draw(st).text(pos,row["korean"],font=f,fill=255,stroke_width=sw,stroke_fill=255)
        ImageDraw.Draw(fi).text(pos,row["korean"],font=f,fill=255)
        tile=Image.new("RGBA",st.size,(0,0,0,0))
        tile.paste(outline,(0,0),st); tile.paste(fill,(0,0),fi)
        ab=tile.getchannel("A").getbbox()
        if not ab: continue
        tile=tile.crop(ab)
        if tile.width>aw-4 or tile.height>ah-4: continue
        px0=x0+(aw-tile.width)//2; py0=y0+(ah-tile.height)//2
        layer=Image.new("RGBA",(W,H),(0,0,0,0)); layer.alpha_composite(tile,(px0,py0))
        lb=list(layer.getchannel("A").getbbox())
        if lb[0]<=x0 or lb[1]<=y0 or lb[2]>=x1 or lb[3]>=y1: continue
        return layer,fs,sw,lb,fill
    raise RuntimeError(("cannot_fit",row["key"],row["original_bbox"]))

final=clean.copy(); target_masks=[]; target=np.zeros((H,W),bool)
for row,sm in zip(rows,source_masks):
    layer,fs,sw,lb,fill=render(row,sm)
    lm=np.asarray(layer.getchannel("A"))>0
    for old in target_masks:
        if np.any(lm&old): raise RuntimeError(("localized_overlap",row["key"]))
    target_masks.append(lm); target|=lm; final.alpha_composite(layer)
    ob=row["original_bbox"]; sw0,sh0=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    row.update({"localized_bbox":lb,"source_size":[sw0,sh0],"localized_size":[lw,lh],
                "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],
                "delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
                "containment":"PASS","size_ceiling":"PASS","edge_touch_high_risk":False,
                "font_size":fs,"stroke_width":sw,"font_path_basename":Path(font_path).name,
                "fill":fill,"slant":0.0,"rework_status":"C135_EXACT_SOURCE_LINE_RENDER"})

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw","RGBA")
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)
candidate.write_bytes(payload)
candidate_sha=hashlib.sha256(payload).hexdigest()
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw","RGBA")
dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if payload[:128]!=sb[:128] or ImageChops.difference(dec,final).getbbox() is not None:
    raise RuntimeError("roundtrip/header")
da=np.asarray(dec,dtype=np.uint8)

changed=np.any(sa!=da,axis=2)
outside=int(np.count_nonzero(changed&~allowed))
alpha_out=int(np.count_nonzero((sa[:,:,3]!=da[:,:,3])&~allowed))
protected_changed=outside
target_out=int(np.count_nonzero(target&~allowed))
target_invisible=int(np.count_nonzero(target&(da[:,:,3]==0)))
guard=dil(target,2)
residue=int(np.count_nonzero(full_source&(da[:,:,3]>0)&~guard))
clean_out=int(np.count_nonzero(np.any(clean_a!=sa,axis=2)&~full_source))
clean_residue=int(np.count_nonzero(full_source&(clean_a[:,:,3]>0)))
overlap=0;touch=[]
for i in range(len(target_masks)):
    for j in range(i+1,len(target_masks)):
        ov=int(np.count_nonzero(target_masks[i]&target_masks[j]))
        near=int(np.count_nonzero(dil(target_masks[i],1)&target_masks[j]))
        overlap+=ov
        if ov or near: touch.append([i+1,j+1,ov,near])
positive=all(r["delta_left"]>0 and r["delta_right"]>0 and r["delta_top"]>0 and r["delta_bottom"]>0 for r in rows)
ok=(outside==0 and alpha_out==0 and protected_changed==0 and target_out==0 and target_invisible==0 and
    residue==0 and clean_out==0 and clean_residue==0 and overlap==0 and not touch and positive)
if not ok:
    raise RuntimeError(("C135_QA_FAIL",outside,alpha_out,target_out,target_invisible,residue,clean_out,clean_residue,overlap,touch,rows))

def mi(m): return Image.fromarray((m.astype(np.uint8)*255),"L")
mi(full_source).save(out/"EBFC709F_SOURCE_TEXT_MASK.png")
mi(allowed).save(out/"EBFC709F_ALLOWED_TEXT_REGION_MASK.png")
mi(~allowed).save(out/"EBFC709F_PROTECTED_MASK.png")
mi(target).save(out/"EBFC709F_TARGET_TEXT_MASK.png")
clean.save(out/"EBFC709F_CLEAN_PLATE.png")
dec.save(out/"C135_EBFC_FINAL_READABLE.png")

def comp(im,bg=(64,64,64,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def card(lbl,im,bg=(64,64,64,255)):
    z=comp(im,bg); c=Image.new("RGB",(W,H+25),"white"); c.paste(z,(0,25)); ImageDraw.Draw(c).text((5,4),lbl,fill="black"); return c

cs=[card("SOURCE_READABLE",src),card("CLEAN",clean),card("C135_FINAL",dec),card("C135_FINAL_WHITE",dec,(255,255,255,255))]
sh=Image.new("RGB",(W*2,(H+25)*2),"white")
sh.paste(cs[0],(0,0));sh.paste(cs[1],(W,0));sh.paste(cs[2],(0,H+25));sh.paste(cs[3],(W,H+25))
sh.thumbnail((1900,1500),Image.Resampling.LANCZOS);sh.save(out/"C135_EBFC_COMPARE.jpg",quality=96)

contacts=[];sr=comp(src);cl=comp(clean);fi=comp(dec)
for r in rows:
    x0,y0,x1,y1=r["original_bbox"];p=12;cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[z.crop(cr) for z in (sr,cl,fi)];ims=[z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST) for z in ims]
    c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+25),"white");xx=0
    for z in ims:c.paste(z,(xx,25));xx+=z.width+6
    ImageDraw.Draw(c).text((4,4),f'{r["n"]} {r["key"]}: {r["source"]} -> {r["korean"]}',fill="black");contacts.append(c)
rs=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4*(len(contacts)-1)),"white");yy=0
for c in contacts:rs.paste(c,(0,yy));yy+=c.height+4
rs.save(out/"C135_EBFC_ROW_CONTACT_2X.jpg",quality=96)

rr=Image.new("RGB",(W,(H+25)*2),"white")
rr.paste(card("SOURCE_RAW_MIRROR_Y",raw_src),(0,0));rr.paste(card("C135_FINAL_RAW_MIRROR_Y",raw_dec),(0,H+25))
rr.thumbnail((1600,1400),Image.Resampling.LANCZOS);rr.save(out/"C135_EBFC_RAW_COMPARE.jpg",quality=96)

report={
 "schema_version":1,"role":"C","run":run,"asset":"EBFC709F","queue_index":232,
 "source_sha256":source_sha,"candidate_sha256":candidate_sha,"candidate_changed_by_C":True,
 "corrective_scope":"replace B48/B49/B50 failed discovery with C134 exact-source line measurement; render all four physical JOIN/CREATE occurrences with verified Noto CJK font",
 "structure":{"width":W,"height":H,"format":"RGBA32","mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "physical_occurrences":4,"semantic_labels":2,"font_coverage":"PASS_VERIFIED_NOTO_CJK",
 "rows":rows,
 "machine_checks":{"bbox_and_size":"4/4 PASS with positive margins","outside":outside,"alpha_outside":alpha_out,
   "protected_changed":protected_changed,"target_out":target_out,"target_invisible":target_invisible,
   "source_residue":residue,"clean_outside_source":clean_out,"clean_source_alpha_remaining":clean_residue,
   "overlap":overlap,"touch_pairs":touch},
 "machine_status":"PASS","controller_visual_qa":"PENDING","runtime_validation":"UNTESTED"
}
(out/"C135_EBFC_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"EBFC709F","index":232,"candidate_sha256":candidate_sha,"machine_status":"PASS",
 "physical_occurrences":"4/4","bbox_size_pass":"4/4","positive_margin_pass":"4/4","outside":outside,"alpha_outside":alpha_out,
 "source_residue":residue,"overlap":overlap,"touch_pairs":len(touch),"runtime_validation":"UNTESTED",
 "report":f"localization/graphics/role_C/{run}/C135_EBFC_MACHINE_QA.json"}
(wr/"C135_EBFC709F.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False),flush=True)
