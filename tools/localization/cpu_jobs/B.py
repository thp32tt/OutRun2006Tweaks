#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,statistics
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd(); run="20261005-B-PRODUCTION60"
out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"; index=154
candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="d06a7ea1d9e9c940788be244963fcb0146fe2498"
ATLAS_BLOB_SHA1="11f58c46008eb6ca355cd9b0d64f1fe268695838"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
work=Path("/tmp/outrun_B60"); work.mkdir(parents=True,exist_ok=True)
source=work/"4D38BBB0_HD.dds"; atlas=work/"4x_4D38BBB0_1024x256_atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_4D38BBB0_1024x256_atlas.json",atlas)

def gitblob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def med(vals):
    return tuple(int(round(statistics.median([v[i] for v in vals]))) for i in range(4))
def comp(im,bg=(64,64,64,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

sb=source.read_bytes(); ab=atlas.read_bytes()
if gitblob(sb)!=SOURCE_BLOB_SHA1: raise RuntimeError(("source blob",gitblob(sb)))
if gitblob(ab)!=ATLAS_BLOB_SHA1: raise RuntimeError(("atlas blob",gitblob(ab)))
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12); pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,mips)!=(4096,1024,16384,1) or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,pitch,depth,mips,len(sb)))
masks=(pf[4],pf[5],pf[6])
if masks==(0xff,0xff00,0xff0000): RAWMODE="RGBA"
elif masks==(0xff0000,0xff00,0xff): RAWMODE="BGRA"
else: raise RuntimeError(("rawmode",masks))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",RAWMODE); src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regions={r["idx"]:r for r in json.loads(ab.decode("utf-8"))["regions"]}

# B59 controller-readable binding: regions 0/1 are Ferrari artwork and fully protected.
# Text regions 2..9 are physical occurrences. Region 8 SHOWROOM was missing from stale
# transcription and is corrected here from the canonical HD source.
specs=[
 (2,"CREATE NEW LICENSE","새 라이선스 만들기","red"),
 (3,"SELECT LICENSE","라이선스 선택","red"),
 (4,"SINGLE PLAYER","싱글 플레이","red"),
 (5,"DEFAULT LICENSE","기본 라이선스","red"),
 (6,"MULTIPLAYER","멀티플레이","red"),
 (7,"SINGLE PLAYER","싱글 플레이","gray"),
 (8,"SHOWROOM","쇼룸","gray"),
 (9,"MULTIPLAYER","멀티플레이","gray"),
]
source_mask=Image.new("L",(W,H),0); allowed=Image.new("L",(W,H),0)
rows=[]; color_samples={"red":[],"gray":[]}
for idx,en,ko,group in specs:
    x,y,cw,ch=regions[idx]["rect"]; cell=src.crop((x,y,x+cw,y+ch)); a=bmask(cell.getchannel("A")); bb=a.getbbox()
    if not bb: raise RuntimeError(("empty text region",idx))
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    source_mask.paste(ImageChops.lighter(source_mask.crop((x,y,x+cw,y+ch)),a),(x,y))
    ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
    px=cell.load()
    for yy in range(ch):
      for xx in range(cw):
        r,g,b,aa=px[xx,yy]
        if not aa: continue
        if group=="red" and r>=90 and r>g*1.5 and r>b*1.5: color_samples[group].append((r,g,b,aa))
        if group=="gray" and abs(r-g)<=35 and b>=g-15 and 40<=r<=160: color_samples[group].append((r,g,b,aa))
    rows.append({"region_idx":idx,"source":en,"korean":ko,"style_group":group,"cell":[x,y,cw,ch],"original_bbox":ob})
if min(len(color_samples["red"]),len(color_samples["gray"]))<200:
    raise RuntimeError(("style samples",len(color_samples["red"]),len(color_samples["gray"])))
COLORS={k:med(v) for k,v in color_samples.items()}

source_visible=bmask(src.getchannel("A"))
protected=ImageChops.multiply(source_visible,ImageOps.invert(allowed))
# Artwork regions 0/1 must be in protected and never edited.
artmask=Image.new("L",(W,H),0)
for idx in (0,1):
    x,y,cw,ch=regions[idx]["rect"]; ImageDraw.Draw(artmask).rectangle((x,y,x+cw-1,y+ch-1),fill=255)
if count(ImageChops.multiply(source_visible,artmask))<800000: raise RuntimeError("artwork protection evidence too small")

clean=src.copy(); clean.paste(Image.new("RGBA",(W,H),(0,0,0,0)),(0,0),source_mask)
clean_protected=ImageChops.multiply(source_visible,ImageOps.invert(source_mask))
sp=out/"4D38_HD_SOURCE_READABLE.png"; cp=out/"4D38_HD_CLEAN_PLATE.png"; smp=out/"4D38_SOURCE_TEXT_MASK.png"
ap=out/"4D38_ALLOWED_BBOX_MASK.png"; pp=out/"4D38_PROTECTED_VISIBLE_MASK.png"; cpp=out/"4D38_CLEAN_PROTECTED_VISIBLE_MASK.png"
src.save(sp); clean.save(cp); source_mask.save(smp); allowed.save(ap); protected.save(pp); clean_protected.save(cpp)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(smp),"--protected-mask",str(cpp),"--report",str(out/"B60_CLEAN_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"B60_CLEAN_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean",cleanrep))
residue_clean=count(ImageChops.multiply(source_mask,ImageOps.invert(dmask(src,clean))))
if residue_clean: raise RuntimeError(("clean residue",residue_clean))

def font():
  def pick():
    for pat in ["Noto Sans CJK KR:style=Bold","Noto Sans CJK KR:style=Black"]:
      try: spec=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
      except: spec=""
      if "|" in spec:
        fp,idx=spec.rsplit("|",1)
        if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name and "Bold" in Path(fp).name: return fp,int(idx or 0),pat
    return None
  g=pick()
  if g:return g
  subprocess.run(["sudo","apt-get","update","-qq"],check=True); subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
  g=pick()
  if not g: raise RuntimeError("Noto CJK Bold unavailable")
  return g
FONT,FONT_INDEX,FONT_PATTERN=font()

# Shared source style per group. Red rows share ~144-148px exact source height;
# gray rows share ~62-64px. Use one font size per group and refit all members together.
def find_group_size(group):
    rr=[r for r in rows if r["style_group"]==group]
    maxh=min(r["original_bbox"][3]-r["original_bbox"][1] for r in rr)-4
    start=170 if group=="red" else 82
    for fs in range(start,15,-1):
      f=ImageFont.truetype(FONT,fs,index=FONT_INDEX)
      ok=True
      for r in rr:
        ob=r["original_bbox"]; aw=ob[2]-ob[0]; ah=ob[3]-ob[1]
        bb=ImageDraw.Draw(Image.new("L",(8,8))).textbbox((0,0),r["korean"],font=f,stroke_width=2)
        if bb[2]-bb[0]>aw-4 or bb[3]-bb[1]>min(ah-4,maxh): ok=False; break
      if ok:return fs
    raise RuntimeError(("group fit",group))
GROUP_FS={g:find_group_size(g) for g in ("red","gray")}
WEIGHT=2

final=clean.copy(); target_masks=[]; outrows=[]
for r in rows:
    ob=r["original_bbox"]; aw,ah=ob[2]-ob[0],ob[3]-ob[1]; fs=GROUP_FS[r["style_group"]]
    f=ImageFont.truetype(FONT,fs,index=FONT_INDEX); d=ImageDraw.Draw(Image.new("L",(8,8)))
    tb=d.textbbox((0,0),r["korean"],font=f,stroke_width=WEIGHT); pad=WEIGHT+4
    lay=Image.new("RGBA",(tb[2]-tb[0]+pad*2,tb[3]-tb[1]+pad*2),(0,0,0,0))
    ImageDraw.Draw(lay).text((pad-tb[0],pad-tb[1]),r["korean"],font=f,fill=COLORS[r["style_group"]],stroke_width=WEIGHT,stroke_fill=COLORS[r["style_group"]])
    bb=lay.getchannel("A").getbbox(); lay=lay.crop(bb)
    if lay.width>aw-4 or lay.height>ah-4: raise RuntimeError(("render fit",r["region_idx"],lay.size,[aw,ah]))
    pos=(ob[0]+2,ob[1]+(ah-lay.height)//2)
    final.alpha_composite(lay,pos)
    lm=Image.new("L",(W,H),0); lm.paste(bmask(lay.getchannel("A")),pos); lb=list(lm.getbbox() or ())
    contain=lb[0]>=ob[0] and lb[1]>=ob[1] and lb[2]<=ob[2] and lb[3]<=ob[3]
    sizeok=(lb[2]-lb[0])<=aw and (lb[3]-lb[1])<=ah
    positive=lb[0]>ob[0] and lb[1]>ob[1] and lb[2]<ob[2] and lb[3]<ob[3]
    if not(contain and sizeok and positive): raise RuntimeError(("bbox",r["region_idx"],ob,lb))
    target_masks.append((r["region_idx"],lm))
    outrows.append({**r,"localized_bbox":lb,"source_width":aw,"source_height":ah,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
      "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","font_file":Path(FONT).name,"font_face_index":FONT_INDEX,
      "font_pattern":FONT_PATTERN,"font_size":fs,"same_color_weight_stroke":WEIGHT,"fill_rgba":COLORS[r["style_group"]],"rework_status":"B60_NEW_EXACT_HD_CANDIDATE"})

# zero overlap/touch
ov=0; touch=[]
for i in range(len(target_masks)):
 for j in range(i+1,len(target_masks)):
  a=target_masks[i][1]; b=target_masks[j][1]; x=count(ImageChops.multiply(a,b)); n=count(ImageChops.multiply(a.filter(ImageFilter.MaxFilter(3)),b))
  ov+=x
  if x or n: touch.append([target_masks[i][0],target_masks[j][0],x,n])
if ov or touch: raise RuntimeError(("target overlap/touch",ov,touch))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM); payload=sb[:128]+raw_final.tobytes("raw",RAWMODE)
candidate.write_bytes(payload); csha=sha(payload)
if payload[:128]!=sb[:128]: raise RuntimeError("header changed")
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",RAWMODE); dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip")
fp=out/"4D38_HD_FINAL_DECODED_READABLE.png"; dec.save(fp)
subprocess.run(["python3",str(validator),str(sp),str(fp),str(ap),"--protected-mask",str(pp),"--report",str(out/"B60_FINAL_VALIDATION.json")],check=True)
finalrep=json.loads((out/"B60_FINAL_VALIDATION.json").read_text())
if finalrep["status"]!="PASS": raise RuntimeError(("final",finalrep))
diff=dmask(src,dec); outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_out=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(diff,protected)); art_changed=count(ImageChops.multiply(diff,artmask))
# residue: any exact original source text-effect pixel that survives outside new Korean target
target=Image.new("L",(W,H),0)
for _,m in target_masks: target=ImageChops.lighter(target,m)
source_residue=count(ImageChops.multiply(source_mask,ImageOps.invert(target)).point(lambda p:p))
# exact surviving pixel residue, not just source mask geometry
same=ImageOps.invert(dmask(src,dec)); exact_residue=count(ImageChops.multiply(ImageChops.multiply(source_mask,ImageOps.invert(target)),same))
if outside or alpha_out or prot or art_changed or exact_residue or ov or touch:
    raise RuntimeError(("final gates",outside,alpha_out,prot,art_changed,exact_residue,ov,touch))
target.save(out/"4D38_TARGET_TEXT_MASK.png")

# Evidence sheets
cards=[]
for label,im in [("SOURCE",src),("CLEAN",clean),("FINAL",dec)]:
 z=comp(im).resize((1024,256),Image.Resampling.LANCZOS); c=Image.new("RGB",(1024,284),"white"); c.paste(z,(0,28)); ImageDraw.Draw(c).text((5,5),label,fill="black"); cards.append(c)
sheet=Image.new("RGB",(1024,852),"white")
for i,c in enumerate(cards):sheet.paste(c,(0,i*284))
sheet.save(out/"B60_4D38_SOURCE_CLEAN_FINAL.jpg",quality=96)
contacts=[]
for r in outrows:
 ob=r["original_bbox"]; p=8; cr=(max(0,ob[0]-p),max(0,ob[1]-p),min(W,ob[2]+p),min(H,ob[3]+p))
 ims=[comp(z).crop(cr) for z in (src,clean,dec)]
 scale=2; ims=[z.resize((z.width*scale,z.height*scale),Image.Resampling.NEAREST) for z in ims]
 c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+28),"white"); xx=0
 for z in ims: c.paste(z,(xx,28)); xx+=z.width+6
 ImageDraw.Draw(c).text((5,5),f'{r["region_idx"]} {r["source"]} -> {r["korean"]}',fill="black"); contacts.append(c)
rs=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4*(len(contacts)-1)),"white"); yy=0
for c in contacts: rs.paste(c,(0,yy)); yy+=c.height+4
rs.save(out/"B60_4D38_ROW_CONTACT_2X.jpg",quality=96)
rr=Image.new("RGB",(1024,568),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec)]):
 z=comp(im).resize((1024,256),Image.Resampling.LANCZOS); rr.paste(z,(0,i*284+28)); ImageDraw.Draw(rr).text((5,i*284+5),label,fill="black")
rr.save(out/"B60_4D38_RAW_COMPARE.jpg",quality=96)

report={"schema_version":1,"role":"B","run":run,"index":index,"asset":asset,"readiness_tier":"ONE_STAGE_TO_RENDER_COMPLETED_SAME_INVOCATION",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,"sha256":sha(sb),"path":"Release/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"},
 "semantic_binding":{"B59_regions":{"2":"CREATE NEW LICENSE","3":"SELECT LICENSE","4":"SINGLE PLAYER","5":"DEFAULT LICENSE","6":"MULTIPLAYER","7":"SINGLE PLAYER","8":"SHOWROOM","9":"MULTIPLAYER"},
   "stale_transcription_correction":"added canonical source SHOWROOM region 8 and duplicate SINGLE PLAYER/MULTIPLAYER physical occurrences","protected_regions":[0,1]},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":RAWMODE,"mipmaps":mips,"bytes":len(sb),"header_128_exact":True,"raw_orientation":"mirror_y"},
 "source_style":{"group_font_sizes":GROUP_FS,"fill_rgba":COLORS,"same_color_weight_stroke":WEIGHT,"font_file":Path(FONT).name},
 "rows":outrows,"clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "source_mask_pixels_unchanged_in_clean":residue_clean,"localized_overlap_pixels":ov,"localized_touch_pairs":touch,
 "decoded_changes":{"changed_pixels_total":count(diff),"changed_pixels_outside_source_bboxes":outside,"alpha_changed_pixels_outside_source_bboxes":alpha_out,
   "protected_visible_pixels_changed":prot,"protected_artwork_pixels_changed":art_changed,"exact_source_residue_pixels":exact_residue},
 "candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","RUNTIME_VALIDATION":"UNTESTED",
 "status":"B_PRODUCTION60_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"}
(out/"B60_4D38_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"4D38BBB0","index":index,"source_sha256":sha(sb),"candidate_sha256":csha,"bbox_size_positive_margin":"8/8",
 "clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],"source_mask_residue":exact_residue,"outside":outside,"alpha_outside":alpha_out,
 "protected_changed":prot,"artwork_changed":art_changed,"overlap":ov,"touch_pairs":len(touch),"worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":f"localization/graphics/role_B/{run}/B60_4D38_REPORT.json"}
(wr/"B60_4D38BBB0.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
