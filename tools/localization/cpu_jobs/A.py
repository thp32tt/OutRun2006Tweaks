#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd(); run="20261005-A-RECOVERY11"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_sprani_etc_cvt_Exst/BF3EE5C6_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
input_sha="30cc2167b1650ab0a7b1c579c7d29118065007f0474f7207ce993ab1b19e45fa"
source_sha="b5c0a868add94395745af1827c21ddddd178439b5b4614fbadd8f0e4135a9887"
validator=repo/"tools/localization/validate_clean_plate.py"
a14=repo/"localization/graphics/role_A/20261004-A-PRODUCTION14/A_PRODUCTION14_BF3EE5C6_REPORT.json"
work=Path("/tmp/outrun_A_recovery11"); work.mkdir(parents=True,exist_ok=True)
source=work/"BF3EE5C6_HD.dds"
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
BLOB="d6cde0c83a157e66e089867ccd616c289eb29c6e"
urllib.request.urlretrieve("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT+"/Release/spr_sprani_etc_cvt_Exst/BF3EE5C6_512x512.dds",source)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def count(m): return sum(m.histogram()[1:])
def balpha(im): return im.getchannel("A").point(lambda v:255 if v else 0)
def dmask(a,b):
    d=ImageChops.difference(a,b); z=d.split(); m=z[0]
    for q in z[1:]: m=ImageChops.lighter(m,q)
    return m.point(lambda v:255 if v else 0)

if sha(source)!=source_sha: raise RuntimeError(("source SHA",sha(source),source_sha))
if sha(candidate)!=input_sha: raise RuntimeError(("input candidate SHA",sha(candidate),input_sha))
sb=source.read_bytes(); cb0=candidate.read_bytes()
if sb[:4]!=b"DDS " or cb0[:128]!=sb[:128]: raise RuntimeError("header mismatch")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
if (W,H,pitch,depth,mips)!=(2048,2048,8192,1,1): raise RuntimeError((W,H,pitch,depth,mips))
src_raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
cur_raw=Image.frombytes("RGBA",(W,H),cb0[128:],"raw","RGBA")
cur=cur_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

old=json.loads(a14.read_text(encoding="utf-8"))
rows0=old["rows"]
if len(rows0)!=13: raise RuntimeError(("row count",len(rows0)))
failed={"rank_stage","normal","tuned_a","tuned_b","double","strike","spare","shift_up","rank","turkey","go"}
preserve={"top_ghost","goal"}
if {r["key"] for r in rows0} != failed|preserve: raise RuntimeError("unexpected key set")

# Rebuild exact clean plate from canonical source, then preserve the two C109 style-accepted rows byte-exact.
source_text_mask=Image.new("L",(W,H),0)
allowed=Image.new("L",(W,H),0); ad=ImageDraw.Draw(allowed)
failed_allowed=Image.new("L",(W,H),0); fad=ImageDraw.Draw(failed_allowed)
clean=src.copy()
for r in rows0:
    cell=tuple(r["cell_rect"]); ob=tuple(r["original_bbox"])
    ca=src.crop(cell).getchannel("A").point(lambda v:255 if v else 0)
    source_text_mask.paste(ImageChops.lighter(source_text_mask.crop(cell),ca),(cell[0],cell[1]))
    ad.rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
    if r["key"] in failed: fad.rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
clean.paste(Image.new("RGBA",(W,H),(0,0,0,0)),(0,0),source_text_mask)

src_visible=balpha(src)
protected=ImageChops.multiply(src_visible,ImageOps.invert(allowed))
clean_protected=ImageChops.multiply(src_visible,ImageOps.invert(source_text_mask))
sp=out/"BF3EE5C6_HD_SOURCE_READABLE.png"; cp=out/"BF3EE5C6_HD_CLEAN_PLATE.png"
src.save(sp); clean.save(cp); source_text_mask.save(out/"BF3EE5C6_HD_SOURCE_TEXT_MASK.png")
allowed.save(out/"BF3EE5C6_HD_ALLOWED_TEXT_REGION_MASK.png"); failed_allowed.save(out/"BF3EE5C6_C109_FAILED_REGION_MASK.png")
protected.save(out/"BF3EE5C6_HD_PROTECTED_VISIBLE_MASK.png"); clean_protected.save(out/"BF3EE5C6_HD_CLEAN_PROTECTED_VISIBLE_MASK.png")
subprocess.run(["python3",str(validator),str(sp),str(cp),str(out/"BF3EE5C6_HD_SOURCE_TEXT_MASK.png"),"--protected-mask",str(out/"BF3EE5C6_HD_CLEAN_PROTECTED_VISIBLE_MASK.png"),"--report",str(out/"A_RECOVERY11_CLEAN_PLATE_VALIDATION.json")],check=True)
clean_rep=json.loads((out/"A_RECOVERY11_CLEAN_PLATE_VALIDATION.json").read_text())
if clean_rep["status"]!="PASS": raise RuntimeError(("clean validator",clean_rep))

def fontpath():
    for pat in ["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]:
        try: p=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        except Exception: p=""
        if p and Path(p).exists() and "NotoSansCJK" in Path(p).name: return p
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    p=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
    if not p: raise RuntimeError("font")
    return p
FONT=fontpath()

styles={
 "gold_navy":{"top":(255,248,207,255),"bottom":(218,171,76,255),"inner":(245,225,169,255),"outer":(16,28,72,255),"shadow":(7,13,35,210),"inner_ratio":.030,"outer_ratio":.065,"shadow_ratio":.070,"shear":.36,"glow":None},
 "yellow_white_navy":{"top":(255,239,76,255),"bottom":(255,176,19,255),"inner":(252,252,246,255),"outer":(27,42,91,255),"shadow":(11,17,39,210),"inner_ratio":.025,"outer_ratio":.060,"shadow_ratio":.060,"shear":.34,"glow":None},
 "yellow_navy":{"top":(255,244,72,255),"bottom":(255,199,22,255),"inner":(255,255,255,255),"outer":(13,26,75,255),"shadow":(7,12,34,220),"inner_ratio":.025,"outer_ratio":.070,"shadow_ratio":.060,"shear":.34,"glow":None},
 "green_navy":{"top":(205,255,205,255),"bottom":(43,179,78,255),"inner":None,"outer":(11,25,71,255),"shadow":(7,12,31,210),"inner_ratio":0.0,"outer_ratio":.085,"shadow_ratio":.055,"shear":.36,"glow":None},
 "red_navy":{"top":(255,237,237,255),"bottom":(214,52,69,255),"inner":None,"outer":(12,25,72,255),"shadow":(8,12,30,220),"inner_ratio":0.0,"outer_ratio":.085,"shadow_ratio":.055,"shear":.36,"glow":None},
 "white_red_glow":{"top":(255,255,255,255),"bottom":(255,255,255,255),"inner":(200,28,35,255),"outer":(255,255,255,255),"shadow":(191,21,28,240),"inner_ratio":.060,"outer_ratio":.095,"shadow_ratio":0.0,"shear":.12,"glow":(205,24,31,170)},
 "goal_multicolor":{"top":(255,224,82,255),"bottom":(151,15,65,255),"inner":(255,252,232,255),"outer":(21,29,73,255),"shadow":(7,11,30,220),"inner_ratio":.030,"outer_ratio":.075,"shadow_ratio":.065,"shear":.15,"glow":None},
 "white_lavender":{"top":(255,255,255,255),"bottom":(223,215,242,255),"inner":(70,69,82,255),"outer":(244,244,246,255),"shadow":(16,17,22,220),"inner_ratio":.030,"outer_ratio":.070,"shadow_ratio":.085,"shear":.36,"glow":None},
 "go_peach":{"top":(255,255,255,255),"bottom":(255,184,123,255),"inner":(179,168,193,255),"outer":(242,238,246,255),"shadow":(21,20,28,230),"inner_ratio":.025,"outer_ratio":.065,"shadow_ratio":.065,"shear":.32,"glow":None},
}
def grad(size,top,bottom):
    w,h=size; im=Image.new("RGBA",size); px=im.load()
    for y in range(h):
        t=y/max(1,h-1); c=tuple(round(top[i]*(1-t)+bottom[i]*t) for i in range(4))
        for x in range(w): px[x,y]=c
    return im
def shear_mask(mask,s):
    if not s:return mask
    extra=max(1,int(abs(s)*mask.height)+6)
    c=Image.new("L",(mask.width+extra*2,mask.height),0); c.paste(mask,(extra,0))
    o=c.transform(c.size,Image.Transform.AFFINE,(1,-s,s*c.height,0,1,0),resample=Image.Resampling.BICUBIC)
    bb=o.getbbox(); return o.crop(bb) if bb else o
def offset(m,dx,dy):
    o=Image.new("L",m.size,0)
    sx1=max(0,-dx); sy1=max(0,-dy); sx2=m.width-max(0,dx); sy2=m.height-max(0,dy)
    if sx2>sx1 and sy2>sy1:o.paste(m.crop((sx1,sy1,sx2,sy2)),(max(0,dx),max(0,dy)))
    return o
def render(text,sty,aw,ah):
    st=styles[sty]
    for fs in range(max(18,int(ah*1.18)),13,-1):
        f=ImageFont.truetype(FONT,fs); outer=max(1,round(fs*st["outer_ratio"])); inner=max(0,round(fs*st["inner_ratio"])); shadow=max(0,round(fs*st["shadow_ratio"]))
        d=ImageDraw.Draw(Image.new("L",(8,8),0)); bb=d.textbbox((0,0),text,font=f,stroke_width=max(outer,inner)); pad=max(outer,inner)+shadow+12
        cw=bb[2]-bb[0]+pad*2; ch=bb[3]-bb[1]+pad*2
        def dm(sw):
            m=Image.new("L",(cw,ch),0); ImageDraw.Draw(m).text((pad-bb[0],pad-bb[1]),text,font=f,fill=255,stroke_width=sw,stroke_fill=255); return shear_mask(m,st["shear"])
        fill,inn,outm=dm(0),dm(inner),dm(outer)
        mw=max(fill.width,inn.width,outm.width); mh=max(fill.height,inn.height,outm.height)
        def center(m):
            c=Image.new("L",(mw,mh),0); c.paste(m,((mw-m.width)//2,(mh-m.height)//2)); return c
        fill,inn,outm=center(fill),center(inn),center(outm)
        ex=max(8,shadow+12)
        def padm(m):
            c=Image.new("L",(mw+ex*2,mh+ex*2),0); c.paste(m,(ex,ex)); return c
        fill,inn,outm=padm(fill),padm(inn),padm(outm)
        rgba=Image.new("RGBA",outm.size,(0,0,0,0))
        if st["glow"]:
            gm=outm.filter(ImageFilter.GaussianBlur(max(2,round(fs*.10))))
            rgba.alpha_composite(Image.composite(Image.new("RGBA",rgba.size,st["glow"]),Image.new("RGBA",rgba.size,(0,0,0,0)),gm))
        if shadow:
            sm=offset(outm,shadow,shadow); rgba.alpha_composite(Image.composite(Image.new("RGBA",rgba.size,st["shadow"]),Image.new("RGBA",rgba.size,(0,0,0,0)),sm))
        rgba.alpha_composite(Image.composite(Image.new("RGBA",rgba.size,st["outer"]),Image.new("RGBA",rgba.size,(0,0,0,0)),outm))
        if inner: rgba.alpha_composite(Image.composite(Image.new("RGBA",rgba.size,st["inner"]),Image.new("RGBA",rgba.size,(0,0,0,0)),inn))
        rgba.alpha_composite(Image.composite(grad(rgba.size,st["top"],st["bottom"]),Image.new("RGBA",rgba.size,(0,0,0,0)),fill))
        box=rgba.getchannel("A").getbbox()
        if not box:continue
        rgba=rgba.crop(box)
        if rgba.width<=aw-6 and rgba.height<=ah-6:return rgba,fs,outer,inner,shadow,st["shear"]
    raise RuntimeError(("fit",text,sty,aw,ah))

final=clean.copy()
# Preserve C109 style-accepted rows exactly from the existing candidate.
for r in rows0:
    if r["key"] in preserve:
        ob=tuple(r["original_bbox"]); final.paste(cur.crop(ob),(ob[0],ob[1]))

meta={}
for r in rows0:
    if r["key"] not in failed: continue
    ob=r["original_bbox"]; aw,ah=ob[2]-ob[0],ob[3]-ob[1]
    glyph,fs,outer,inner,shadow,shear=render(r["korean"],r["style"],aw,ah)
    tx=ob[0]+(aw-glyph.width)//2; ty=ob[1]+(ah-glyph.height)//2
    if tx<=ob[0]:tx=ob[0]+1
    if ty<=ob[1]:ty=ob[1]+1
    if tx+glyph.width>=ob[2]:tx=ob[2]-glyph.width-1
    if ty+glyph.height>=ob[3]:ty=ob[3]-glyph.height-1
    final.alpha_composite(glyph,(tx,ty))
    meta[r["key"]]={"font_size":fs,"stroke_outer":outer,"stroke_inner":inner,"shadow_px":shadow,"shear":shear,"preencode_bbox":[tx,ty,tx+glyph.width,ty+glyph.height]}

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
outb=sb[:128]+raw_final.tobytes("raw","RGBA"); candidate.write_bytes(outb); csha=sha(candidate)
decoded_raw=Image.frombytes("RGBA",(W,H),outb[128:],"raw","RGBA"); decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(decoded,final).getbbox() is not None:raise RuntimeError("roundtrip")
dp=out/"BF3EE5C6_HD_FINAL_DECODED_READABLE.png"; decoded.save(dp)
subprocess.run(["python3",str(validator),str(sp),str(dp),str(out/"BF3EE5C6_HD_ALLOWED_TEXT_REGION_MASK.png"),"--protected-mask",str(out/"BF3EE5C6_HD_PROTECTED_VISIBLE_MASK.png"),"--report",str(out/"A_RECOVERY11_FINAL_MASK_VALIDATION.json")],check=True)
final_rep=json.loads((out/"A_RECOVERY11_FINAL_MASK_VALIDATION.json").read_text())
if final_rep["status"]!="PASS":raise RuntimeError(("final validator",final_rep))

diff=dmask(src,decoded); outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_out=count(ImageChops.multiply(ImageChops.difference(src.getchannel("A"),decoded.getchannel("A")).point(lambda v:255 if v else 0),ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(diff,protected)); residue=count(ImageChops.multiply(balpha(clean),source_text_mask))
vs_input=dmask(cur,decoded); changed_vs_input_out_failed=count(ImageChops.multiply(vs_input,ImageOps.invert(failed_allowed)))
preserved_diffs={}
for r in rows0:
    if r["key"] in preserve:
        ob=tuple(r["original_bbox"]); preserved_diffs[r["key"]]=count(dmask(cur.crop(ob),decoded.crop(ob)))

rows=[]
for r in rows0:
    ob=r["original_bbox"]; bb=decoded.crop(tuple(ob)).getchannel("A").getbbox()
    loc=[ob[0]+bb[0],ob[1]+bb[1],ob[0]+bb[2],ob[1]+bb[3]] if bb else None
    ok=loc and loc[0]>=ob[0] and loc[1]>=ob[1] and loc[2]<=ob[2] and loc[3]<=ob[3]
    sz=loc and loc[2]-loc[0]<=ob[2]-ob[0] and loc[3]-loc[1]<=ob[3]-ob[1]
    pos=loc and loc[0]>ob[0] and loc[1]>ob[1] and loc[2]<ob[2] and loc[3]<ob[3]
    md=meta.get(r["key"],{})
    rows.append({"key":r["key"],"source":r["source"],"korean":r["korean"],"style":r["style"],"original_bbox":ob,"localized_bbox":loc,
      "delta_left":loc[0]-ob[0],"delta_right":ob[2]-loc[2],"delta_top":loc[1]-ob[1],"delta_bottom":ob[3]-loc[3],
      "source_size":[ob[2]-ob[0],ob[3]-ob[1]],"localized_size":[loc[2]-loc[0],loc[3]-loc[1]],
      "containment":"PASS" if ok else "FAIL","size_ceiling":"PASS" if sz else "FAIL","positive_margin":"PASS" if pos else "FAIL",
      "raw_original_bbox":[ob[0],H-ob[3],ob[2],H-ob[1]],"raw_localized_bbox":[loc[0],H-loc[3],loc[2],H-loc[1]],"raw_containment":"PASS" if ok else "FAIL",
      "font":"Noto Sans CJK KR Black/Bold","font_size":md.get("font_size",r.get("font_size")),"shear":md.get("shear","PRESERVED_A14"),
      "rework_status":"A_RECOVERY11_SLANT_RERENDER" if r["key"] in failed else "A14_PRESERVED_EXACT_C109_STYLE_ACCEPTED"})

all_bbox=all(r["containment"]=="PASS" and r["raw_containment"]=="PASS" for r in rows)
all_size=all(r["size_ceiling"]=="PASS" for r in rows); all_pos=all(r["positive_margin"]=="PASS" for r in rows)

def gray(im):
    bg=Image.new("RGBA",im.size,(92,92,92,255)); bg.alpha_composite(im); return bg.convert("RGB")
thumb=(1024,1024); sh=Image.new("RGB",(1024,3072),(70,70,70))
for i,im in enumerate([src,cur,decoded]): sh.paste(gray(im).resize(thumb,Image.Resampling.LANCZOS),(0,i*1024))
sh.save(out/"A_RECOVERY11_SOURCE_OLD_FINAL_GRAY.jpg",quality=95)
gray(decoded_raw).resize(thumb,Image.Resampling.LANCZOS).save(out/"A_RECOVERY11_FINAL_RAW_GRAY.jpg",quality=95)

# SOURCE | OLD | NEW per row, with failed rows first.
contact=[]
lab=ImageFont.truetype(FONT,20)
order=sorted(rows0,key=lambda r:(r["key"] not in failed,r["key"]))
for r in order:
    ob=r["original_bbox"]; m=12; box=(max(0,ob[0]-m),max(0,ob[1]-m),min(W,ob[2]+m),min(H,ob[3]+m))
    ims=[gray(z.crop(box)) for z in [src,cur,decoded]]
    total=sum(i.width for i in ims)+24
    if total>1350:
        sc=(1350-24)/sum(i.width for i in ims); ims=[i.resize((max(1,int(i.width*sc)),max(1,int(i.height*sc))),Image.Resampling.LANCZOS) for i in ims]
    row=Image.new("RGB",(sum(i.width for i in ims)+24,max(i.height for i in ims)+28),(225,225,225)); x=0
    for im in ims: row.paste(im,(x,28)); x+=im.width+12
    ImageDraw.Draw(row).text((3,3),r["key"]+" SOURCE | OLD | NEW",font=lab,fill=(0,0,0)); contact.append(row)
cw=max(x.width for x in contact); ch=sum(x.height for x in contact)+4*(len(contact)-1); cs=Image.new("RGB",(cw,ch),(235,235,235)); y=0
for x in contact: cs.paste(x,(0,y)); y+=x.height+4
cs.save(out/"A_RECOVERY11_ROW_CONTACT_SOURCE_OLD_NEW.jpg",quality=95)

status=(clean_rep["status"]=="PASS" and final_rep["status"]=="PASS" and all_bbox and all_size and all_pos and outside==0 and alpha_out==0 and prot==0 and residue==0 and changed_vs_input_out_failed==0 and all(v==0 for v in preserved_diffs.values()))
report={"schema_version":1,"role":"A","run":run,"index":49,"asset":asset_rel,"worker":os.environ.get("OUTRUN_CPU_WORKER"),"source_sha256":source_sha,"input_candidate_sha256":input_sha,"candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":BLOB,"sha256":source_sha},
 "structure":{"dimensions":[W,H],"format":"RGBA32","pitch":pitch,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "c109_return_reason":"source style slant/italic mismatch on 11 rows","reworked_keys":sorted(failed),"preserved_c109_style_accepted_keys":sorted(preserve),"preserved_input_pixel_diffs":preserved_diffs,
 "method":"reconstruct canonical clean plate; preserve C109-style-accepted top_ghost/goal exact; rerender only 11 returned rows with materially stronger source-family right shear 0.32-0.36 while retaining A14 fill/outline/shadow families",
 "clean_plate_validator":clean_rep,"final_mask_validator":final_rep,"rows":rows,
 "all_13_readable_and_raw_bbox_pass":all_bbox,"all_13_size_ceiling_pass":all_size,"all_13_positive_margin":all_pos,
 "decoded_changes":{"changed_pixels_outside_original_bboxes":outside,"alpha_changed_pixels_outside_original_bboxes":alpha_out,"protected_visible_pixels_changed":prot,"clean_plate_source_text_residue_pixels":residue,"changes_vs_input_outside_11_failed_bboxes":changed_vs_input_out_failed},
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"UNTESTED","status":"A_RECOVERY11_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status else "A_RECOVERY11_WORKER_REWORK_REQUIRED"}
(out/"A_RECOVERY11_BF3EE5C6_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"BF3EE5C6","index":49,"input_candidate_sha256":input_sha,"candidate_sha256":csha,"reworked_rows":11,"preserved_rows":2,"bbox_pass":"13/13" if all_bbox else "FAIL","size_ceiling":"13/13" if all_size else "FAIL","positive_margin":"13/13" if all_pos else "FAIL","clean_plate_validator":clean_rep["status"],"final_mask_validator":final_rep["status"],"changed_pixels_outside_original_bboxes":outside,"alpha_changed_pixels_outside_original_bboxes":alpha_out,"protected_visible_pixels_changed":prot,"source_residue_pixels":residue,"changes_vs_input_outside_11_failed_bboxes":changed_vs_input_out_failed,"preserved_input_pixel_diffs":preserved_diffs,"worker_status":report["status"],"runtime_validation":"UNTESTED","report":"localization/graphics/role_A/20261005-A-RECOVERY11/A_RECOVERY11_BF3EE5C6_REPORT.json"}
(wr/"A_RECOVERY11_BF3EE5C6.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status: raise SystemExit(2)
