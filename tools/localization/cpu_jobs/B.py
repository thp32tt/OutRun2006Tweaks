#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,statistics
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B": raise SystemExit("worker B only")
repo=Path.cwd(); run="20261005-B-PRODUCTION65"; out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/D657C2EB_512x128.dds"; index=220
cand=repo/"localization/graphics/hd_candidates"/asset; cand.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"; base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/b65"); work.mkdir(exist_ok=True); dds=work/"src.dds"; atlas=work/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/D657C2EB_512x128.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_D657C2EB_512x128_atlas.json",atlas)
sb=dds.read_bytes(); ab=atlas.read_bytes()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
 d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
 for z in bands[1:]: m=ImageChops.lighter(m,z)
 return bmask(m)
def comp(im,bg=(64,64,64,255)):
 z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
if blob(sb)!="0b3bdc37870e75da3290f2d5587cebd9cd73655c" or blob(ab)!="4c6af70c683fb6c298e32c289d762a1f7e6a56b5": raise RuntimeError("input drift")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12); pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6])
RAWMODE="RGBA" if masks==(0xff,0xff00,0xff0000) else "BGRA"
if (W,H,pitch,mips)!=(2048,512,8192,1) or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,pitch,mips,len(sb),pf))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",RAWMODE); src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regions={r["idx"]:r for r in json.loads(ab.decode("utf-8"))["regions"]}
# B64 canonical source visual binding. Duplicate TIME ATTACK is a second physical occurrence.
specs=[
 (0,"TIME ATTACK","타임 어택","red"),
 (1,"COAST 2 COAST","코스트 2 코스트","gray"),
 (2,"HEART ATTACK","하트 어택","gray"),
 (3,"TIME ATTACK","타임 어택","gray"),
 (4,"OUTRUN","아웃런","gray"),
 (5,"SEND GAME INVITE","게임 초대 보내기","small"),
 (6,"REMOVE FRIEND","친구 삭제","small"),
]
source_union=Image.new("L",(W,H),0); allowed=Image.new("L",(W,H),0); rows=[]; samples={"red":[],"gray":[],"small":[]}
for idx,en,ko,group in specs:
 x,y,cw,ch=regions[idx]["rect"]; cell=src.crop((x,y,x+cw,y+ch)); a=bmask(cell.getchannel("A")); bb=a.getbbox()
 if not bb: raise RuntimeError(("empty",idx))
 ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]; source_union.paste(ImageChops.lighter(source_union.crop((x,y,x+cw,y+ch)),a),(x,y)); ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
 px=cell.load()
 for yy in range(ch):
  for xx in range(cw):
   r,g,b,aa=px[xx,yy]
   if aa>64: samples[group].append((r,g,b,aa))
 rows.append({"region_idx":idx,"source":en,"korean":ko,"style_group":group,"cell":[x,y,cw,ch],"original_bbox":ob,"source_pixels":count(a)})
COLORS={g:tuple(int(statistics.median(v[i] for v in samples[g])) for i in range(4)) for g in samples}
# transparent source text atlas: exact clean plate is zero only on source glyph/effect pixels.
clean=src.copy(); clean.paste(Image.new("RGBA",(W,H),(0,0,0,0)),(0,0),source_union)
sp=out/"D657_SOURCE_READABLE.png"; cp=out/"D657_CLEAN_PLATE.png"; smp=out/"D657_SOURCE_TEXT_MASK.png"; ap=out/"D657_ALLOWED_BBOX_MASK.png"
src.save(sp);clean.save(cp);source_union.save(smp);allowed.save(ap)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(smp),"--report",str(out/"B65_CLEAN_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"B65_CLEAN_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean",cleanrep))
residue_clean=count(ImageChops.multiply(source_union,ImageOps.invert(dmask(src,clean))))
if residue_clean: raise RuntimeError(("clean residue",residue_clean))

def font():
 def pick():
  for p in ["Noto Sans CJK KR:style=Bold","Noto Sans CJK KR:style=Black"]:
   try:s=subprocess.check_output(["fc-match","-f","%{file}|%{index}",p],text=True).strip()
   except:s=""
   if "|" in s:
    fp,ix=s.rsplit("|",1)
    if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name:return fp,int(ix or 0),p
  return None
 g=pick()
 if g:return g
 subprocess.run(["sudo","apt-get","update","-qq"],check=True);subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
 g=pick()
 if not g:raise RuntimeError("font")
 return g
FONT,FIDX,FPAT=font(); WEIGHT=2
# group-shared sizes preserve source family differences.
def findfs(group,start):
 rr=[r for r in rows if r["style_group"]==group]
 for fs in range(start,12,-1):
  f=ImageFont.truetype(FONT,fs,index=FIDX);ok=True
  for r in rr:
   ob=r["original_bbox"];aw,ah=ob[2]-ob[0],ob[3]-ob[1];tb=ImageDraw.Draw(Image.new("L",(8,8))).textbbox((0,0),r["korean"],font=f,stroke_width=WEIGHT)
   if tb[2]-tb[0]>aw-4 or tb[3]-tb[1]>ah-4:ok=False;break
  if ok:return fs
 raise RuntimeError(("fit",group))
FS={"red":findfs("red",144),"gray":findfs("gray",62),"small":findfs("small",38)}
final=clean.copy();target=Image.new("L",(W,H),0);targets=[];outrows=[]
for r in rows:
 ob=r["original_bbox"];aw,ah=ob[2]-ob[0],ob[3]-ob[1];f=ImageFont.truetype(FONT,FS[r["style_group"]],index=FIDX);d=ImageDraw.Draw(Image.new("L",(8,8)));tb=d.textbbox((0,0),r["korean"],font=f,stroke_width=WEIGHT);pad=WEIGHT+4
 lay=Image.new("RGBA",(tb[2]-tb[0]+pad*2,tb[3]-tb[1]+pad*2),(0,0,0,0));ImageDraw.Draw(lay).text((pad-tb[0],pad-tb[1]),r["korean"],font=f,fill=COLORS[r["style_group"]],stroke_width=WEIGHT,stroke_fill=COLORS[r["style_group"]]);bb=lay.getchannel("A").getbbox();lay=lay.crop(bb)
 if lay.width>aw-4 or lay.height>ah-4:raise RuntimeError(("fit2",r["region_idx"],lay.size,[aw,ah]))
 pos=(ob[0]+2,ob[1]+(ah-lay.height)//2);final.alpha_composite(lay,pos);lm=Image.new("L",(W,H),0);lm.paste(bmask(lay.getchannel("A")),pos);lb=list(lm.getbbox())
 if not(lb[0]>ob[0] and lb[1]>ob[1] and lb[2]<ob[2] and lb[3]<ob[3]):raise RuntimeError(("margin",r["region_idx"],ob,lb))
 target=ImageChops.lighter(target,lm);targets.append((r["region_idx"],lm));outrows.append({**r,"localized_bbox":lb,"source_width":aw,"source_height":ah,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],"delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],"containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","font_size":FS[r["style_group"]],"font_file":Path(FONT).name,"font_face_index":FIDX,"font_pattern":FPAT,"fill_rgba":COLORS[r["style_group"]],"same_color_weight_stroke":WEIGHT})
overlap=0;touch=[]
for i in range(len(targets)):
 for j in range(i+1,len(targets)):
  ov=count(ImageChops.multiply(targets[i][1],targets[j][1]));near=count(ImageChops.multiply(targets[i][1].filter(ImageFilter.MaxFilter(3)),targets[j][1]));overlap+=ov
  if ov or near:touch.append([targets[i][0],targets[j][0],ov,near])
if overlap or touch:raise RuntimeError(("overlap",overlap,touch))
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM);payload=sb[:128]+raw_final.tobytes("raw",RAWMODE);cand.write_bytes(payload);csha=sha(payload)
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",RAWMODE);dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox() or payload[:128]!=sb[:128]:raise RuntimeError("roundtrip/header")
fp=out/"D657_FINAL_DECODED.png";dec.save(fp);target.save(out/"D657_TARGET_TEXT_MASK.png")
subprocess.run(["python3",str(validator),str(sp),str(fp),str(ap),"--report",str(out/"B65_FINAL_VALIDATION.json")],check=True)
finalrep=json.loads((out/"B65_FINAL_VALIDATION.json").read_text());diff=dmask(src,dec);outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)));alpha_out=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),ImageOps.invert(allowed)));exact_residue=count(ImageChops.multiply(ImageChops.multiply(source_union,ImageOps.invert(target)),ImageOps.invert(diff)))
if finalrep["status"]!="PASS" or outside or alpha_out or exact_residue:raise RuntimeError(("final",finalrep,outside,alpha_out,exact_residue))
# evidence
cards=[]
for label,im in [("SOURCE",src),("CLEAN",clean),("FINAL",dec)]:
 z=comp(im).resize((1024,256),Image.Resampling.LANCZOS);c=Image.new("RGB",(1024,284),"white");c.paste(z,(0,28));ImageDraw.Draw(c).text((5,5),label,fill="black");cards.append(c)
sheet=Image.new("RGB",(1024,852),"white")
for i,c in enumerate(cards):sheet.paste(c,(0,i*284))
sheet.save(out/"B65_D657_SOURCE_CLEAN_FINAL.jpg",quality=96)
contacts=[]
for r in outrows:
 ob=r["original_bbox"];p=8;cr=(max(0,ob[0]-p),max(0,ob[1]-p),min(W,ob[2]+p),min(H,ob[3]+p));ims=[comp(z).crop(cr) for z in (src,clean,dec)];ims=[z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST) for z in ims];c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+28),"white");xx=0
 for z in ims:c.paste(z,(xx,28));xx+=z.width+6
 ImageDraw.Draw(c).text((5,5),f'{r["region_idx"]} {r["source"]} -> {r["korean"]}',fill="black");contacts.append(c)
rs=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4*(len(contacts)-1)),"white");yy=0
for c in contacts:rs.paste(c,(0,yy));yy+=c.height+4
rs.save(out/"B65_D657_ROW_CONTACT_2X.jpg",quality=96)
rr=Image.new("RGB",(1024,568),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec)]):
 z=comp(im).resize((1024,256),Image.Resampling.LANCZOS);rr.paste(z,(0,i*284+28));ImageDraw.Draw(rr).text((5,i*284+5),label,fill="black")
rr.save(out/"B65_D657_RAW_COMPARE.jpg",quality=96)
report={"schema_version":1,"role":"B","run":run,"index":index,"asset":asset,"readiness_tier":"ONE_STAGE_TO_RENDER_COMPLETED_SAME_INVOCATION","source_sha256":sha(sb),"candidate_sha256":csha,"structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":RAWMODE,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},"semantic_binding":{"B64_regions":{"0":"TIME ATTACK","1":"COAST 2 COAST","2":"HEART ATTACK","3":"TIME ATTACK","4":"OUTRUN","5":"SEND GAME INVITE","6":"REMOVE FRIEND"},"stale_transcription_correction":"TIME ATTACK has two physical occurrences"},"source_style":{"group_font_sizes":FS,"fill_rgba":COLORS,"same_color_weight_stroke":WEIGHT},"rows":outrows,"clean_plate_validator":cleanrep,"final_mask_validator":finalrep,"decoded_changes":{"outside":outside,"alpha_outside":alpha_out,"exact_source_residue":exact_residue,"overlap":overlap,"touch_pairs":touch},"controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","status":"B_PRODUCTION65_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C","RUNTIME_VALIDATION":"UNTESTED"}
(out/"B65_D657_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n");(wr/"B65_D657C2EB.json").write_text(json.dumps({"run":run,"index":index,"source_sha256":sha(sb),"candidate_sha256":csha,"bbox_size_positive_margin":"7/7","outside":outside,"alpha_outside":alpha_out,"source_residue":exact_residue,"overlap":overlap,"touch_pairs":len(touch),"worker_status":report["status"],"runtime_validation":"UNTESTED","report":f"localization/graphics/role_B/{run}/B65_D657_REPORT.json"},ensure_ascii=False,indent=2)+"\n");print(json.dumps({"status":report["status"],"candidate_sha256":csha}))
