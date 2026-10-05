#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,statistics
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B": raise SystemExit("worker B only")
repo=Path.cwd(); run="20261005-B-PRODUCTION67"; out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/E3F4BA07_512x128.dds"; index=226
candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"; base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/b67"); work.mkdir(exist_ok=True); dds=work/"a.dds"; atlas=work/"a.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/E3F4BA07_512x128.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_E3F4BA07_512x128_atlas.json",atlas)
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
if blob(sb)!="0ac26331b6c2765b9c46b867ff1f2151fd7a15b1" or blob(ab)!="50256e8d4d5af1335249993d44abc5d18a4c5672": raise RuntimeError("blob drift")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12); pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6])
if (W,H,pitch,mips)!=(2048,512,8192,1) or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,pitch,mips,len(sb)))
mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
if not mode: raise RuntimeError(("rawmode",masks))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode); src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regions={r["idx"]:r for r in json.loads(ab.decode())["regions"]}
specs=[
 (0,"STAGE","스테이지"),(3,"GOAL E","골 E"),(4,"GOAL D","골 D"),(5,"GOAL C","골 C"),
 (6,"GOAL B","골 B"),(7,"GOAL A","골 A"),(8,"GOAL","골"),(9,"15 STAGE CONTINUOUS","15코스 연속")
]
source_mask=Image.new("L",(W,H),0); allowed=Image.new("L",(W,H),0); rows=[]; samples=[]
for idx,en,ko in specs:
 x,y,cw,ch=regions[idx]["rect"]; cell=src.crop((x,y,x+cw,y+ch)); a=bmask(cell.getchannel("A")); bb=a.getbbox()
 if not bb: raise RuntimeError(("empty",idx))
 ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
 source_mask.paste(ImageChops.lighter(source_mask.crop((x,y,x+cw,y+ch)),a),(x,y))
 ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
 px=cell.load()
 for yy in range(ch):
  for xx in range(cw):
   r,g,b,aa=px[xx,yy]
   if aa and abs(r-g)<=35 and abs(g-b)<=45 and 35<=r<=170: samples.append((r,g,b,aa))
 rows.append({"region_idx":idx,"source":en,"korean":ko,"cell":[x,y,cw,ch],"original_bbox":ob})
if len(samples)<200: raise RuntimeError(("style samples",len(samples)))
FILL=tuple(int(round(statistics.median([v[i] for v in samples]))) for i in range(4))
source_visible=bmask(src.getchannel("A"))
protected=ImageChops.multiply(source_visible,ImageOps.invert(allowed))
# Region 1/2 are protected OutRun2SP / OutRun2 marks.
prot12=Image.new("L",(W,H),0)
for idx in (1,2):
 x,y,cw,ch=regions[idx]["rect"]; prot12.paste(bmask(src.crop((x,y,x+cw,y+ch)).getchannel("A")),(x,y))
if count(prot12)<10000: raise RuntimeError(("protected marks too small",count(prot12)))
clean=src.copy(); clean.paste(Image.new("RGBA",(W,H),(0,0,0,0)),(0,0),source_mask)
cleanprot=ImageChops.multiply(source_visible,ImageOps.invert(source_mask))
sp=out/"E3F4_SOURCE_READABLE.png"; cp=out/"E3F4_CLEAN_PLATE.png"; smp=out/"E3F4_SOURCE_TEXT_MASK.png"; ap=out/"E3F4_ALLOWED_BBOX_MASK.png"; pp=out/"E3F4_PROTECTED_VISIBLE_MASK.png"; cpp=out/"E3F4_CLEAN_PROTECTED_VISIBLE_MASK.png"
src.save(sp); clean.save(cp); source_mask.save(smp); allowed.save(ap); protected.save(pp); cleanprot.save(cpp)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(smp),"--protected-mask",str(cpp),"--report",str(out/"B67_CLEAN_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"B67_CLEAN_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean",cleanrep))
def getfont():
 def pick():
  for pat in ["Noto Sans CJK KR:style=Bold","Noto Sans CJK KR:style=Black"]:
   try:s=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
   except:s=""
   if "|" in s:
    fp,ix=s.rsplit("|",1)
    if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name and "Bold" in Path(fp).name:return fp,int(ix or 0),pat
  return None
 g=pick()
 if g:return g
 subprocess.run(["sudo","apt-get","update","-qq"],check=True); subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
 g=pick()
 if not g:raise RuntimeError("font")
 return g
FONT,FI,FPAT=getfont(); STROKE=2
# One shared size because all eight source labels share one 64px-high typography family.
for fs in range(60,15,-1):
 f=ImageFont.truetype(FONT,fs,index=FI); ok=True
 for r in rows:
  ob=r["original_bbox"]; aw=ob[2]-ob[0]; ah=ob[3]-ob[1]; tb=ImageDraw.Draw(Image.new("L",(8,8))).textbbox((0,0),r["korean"],font=f,stroke_width=STROKE)
  if tb[2]-tb[0]>aw-4 or tb[3]-tb[1]>ah-4:ok=False;break
 if ok:FS=fs;break
else:raise RuntimeError("shared fit")
final=clean.copy(); targets=[]; outrows=[]
for r in rows:
 ob=r["original_bbox"]; aw=ob[2]-ob[0]; ah=ob[3]-ob[1]; f=ImageFont.truetype(FONT,FS,index=FI)
 tb=ImageDraw.Draw(Image.new("L",(8,8))).textbbox((0,0),r["korean"],font=f,stroke_width=STROKE); pad=STROKE+4
 lay=Image.new("RGBA",(tb[2]-tb[0]+pad*2,tb[3]-tb[1]+pad*2),(0,0,0,0))
 ImageDraw.Draw(lay).text((pad-tb[0],pad-tb[1]),r["korean"],font=f,fill=FILL,stroke_width=STROKE,stroke_fill=FILL)
 bb=lay.getchannel("A").getbbox(); lay=lay.crop(bb); pos=(ob[0]+2,ob[1]+(ah-lay.height)//2)
 if lay.width>aw-4 or lay.height>ah-4:raise RuntimeError(("fit",r["region_idx"]))
 final.alpha_composite(lay,pos); lm=Image.new("L",(W,H),0); lm.paste(bmask(lay.getchannel("A")),pos); lb=list(lm.getbbox())
 if not(lb[0]>ob[0] and lb[1]>ob[1] and lb[2]<ob[2] and lb[3]<ob[3]):raise RuntimeError(("margin",r["region_idx"],ob,lb))
 if count(ImageChops.multiply(lm,protected)):raise RuntimeError(("protected overlap",r["region_idx"]))
 targets.append((r["region_idx"],lm)); outrows.append({**r,"localized_bbox":lb,"source_width":aw,"source_height":ah,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],"delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],"containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","font_file":Path(FONT).name,"font_face_index":FI,"font_size":FS,"stroke_width":STROKE,"fill_rgba":FILL,"rework_status":"B67_NEW_EXACT_HD_CANDIDATE"})
ov=0; touch=[]
for i in range(len(targets)):
 for j in range(i+1,len(targets)):
  a=targets[i][1]; b=targets[j][1]; x=count(ImageChops.multiply(a,b)); n=count(ImageChops.multiply(a.filter(ImageFilter.MaxFilter(3)),b)); ov+=x
  if x or n:touch.append([targets[i][0],targets[j][0],x,n])
if ov or touch:raise RuntimeError(("overlap",ov,touch))
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM); payload=sb[:128]+raw_final.tobytes("raw",mode); candidate.write_bytes(payload); csha=sha(payload)
if payload[:128]!=sb[:128]:raise RuntimeError("header")
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode); dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox():raise RuntimeError("roundtrip")
fp=out/"E3F4_FINAL_DECODED_READABLE.png"; dec.save(fp)
subprocess.run(["python3",str(validator),str(sp),str(fp),str(ap),"--protected-mask",str(pp),"--report",str(out/"B67_FINAL_VALIDATION.json")],check=True)
finalrep=json.loads((out/"B67_FINAL_VALIDATION.json").read_text())
diff=dmask(src,dec); outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed))); alphaout=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),ImageOps.invert(allowed))); prot=count(ImageChops.multiply(diff,protected)); p12=count(ImageChops.multiply(diff,prot12))
target=Image.new("L",(W,H),0)
for _,m in targets:target=ImageChops.lighter(target,m)
same=ImageOps.invert(diff); residue=count(ImageChops.multiply(ImageChops.multiply(source_mask,ImageOps.invert(target)),same))
if finalrep["status"]!="PASS" or outside or alphaout or prot or p12 or residue or ov or touch:raise RuntimeError(("gates",finalrep["status"],outside,alphaout,prot,p12,residue,ov,touch))
target.save(out/"E3F4_TARGET_TEXT_MASK.png")
cards=[]
for label,im in [("SOURCE",src),("CLEAN",clean),("FINAL",dec)]:
 z=comp(im).resize((1024,256),Image.Resampling.NEAREST); c=Image.new("RGB",(1024,284),"white"); c.paste(z,(0,28)); ImageDraw.Draw(c).text((5,5),label,fill="black"); cards.append(c)
sheet=Image.new("RGB",(1024,852),"white")
for i,c in enumerate(cards):sheet.paste(c,(0,i*284))
sheet.save(out/"B67_E3F4_SOURCE_CLEAN_FINAL.jpg",quality=96)
contacts=[]
for r in outrows:
 ob=r["original_bbox"]; p=6; cr=(max(0,ob[0]-p),max(0,ob[1]-p),min(W,ob[2]+p),min(H,ob[3]+p)); ims=[comp(z).crop(cr) for z in (src,clean,dec)]; ims=[z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST) for z in ims]
 c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+28),"white"); xx=0
 for z in ims:c.paste(z,(xx,28));xx+=z.width+6
 ImageDraw.Draw(c).text((5,5),f'{r["region_idx"]} {r["source"]} -> {r["korean"]}',fill="black");contacts.append(c)
rs=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4*(len(contacts)-1)),"white");yy=0
for c in contacts:rs.paste(c,(0,yy));yy+=c.height+4
rs.save(out/"B67_E3F4_ROW_CONTACT_2X.jpg",quality=96)
rr=Image.new("RGB",(1024,568),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec)]):
 z=comp(im).resize((1024,256),Image.Resampling.NEAREST);rr.paste(z,(0,i*284+28));ImageDraw.Draw(rr).text((5,i*284+5),label,fill="black")
rr.save(out/"B67_E3F4_RAW_COMPARE.jpg",quality=96)
report={"schema_version":1,"role":"B","run":run,"index":index,"asset":asset,"readiness_tier":"ONE_STAGE_TO_RENDER_COMPLETED_SAME_INVOCATION","source_sha256":sha(sb),"semantic_binding":{"localized":{"0":"STAGE","3":"GOAL E","4":"GOAL D","5":"GOAL C","6":"GOAL B","7":"GOAL A","8":"GOAL","9":"15 STAGE CONTINUOUS"},"protected":{"1":"OUTRUN2SP","2":"OUTRUN2"}},"structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},"shared_source_style":{"font_file":Path(FONT).name,"font_size":FS,"fill_rgba":FILL,"same_color_weight_stroke":STROKE},"rows":outrows,"clean_plate_validator":cleanrep,"final_mask_validator":finalrep,"decoded_changes":{"changed_pixels_total":count(diff),"outside":outside,"alpha_outside":alphaout,"protected_changed":prot,"protected_outrun_marks_changed":p12,"exact_source_residue":residue,"overlap":ov,"touch_pairs":touch},"candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),"controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","RUNTIME_VALIDATION":"UNTESTED","status":"B_PRODUCTION67_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"}
(out/"B67_E3F4_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"index":index,"asset":"E3F4BA07","source_sha256":sha(sb),"candidate_sha256":csha,"bbox_size_positive_margin":"8/8","clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],"source_residue":residue,"outside":outside,"alpha_outside":alphaout,"protected_changed":prot,"protected_marks_changed":p12,"overlap":ov,"touch_pairs":len(touch),"worker_status":report["status"],"runtime_validation":"UNTESTED","report":f"localization/graphics/role_B/{run}/B67_E3F4_REPORT.json"}
(wr/"B67_E3F4BA07.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False))
