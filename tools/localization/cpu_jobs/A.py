#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,statistics
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A": raise SystemExit("worker A only")
repo=Path.cwd(); run="20261005-A-PRODUCTION69"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/A9ABD877_512x512.dds"; candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"; base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/a69"); work.mkdir(exist_ok=True); dds=work/"src.dds"; atlas=work/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/A9ABD877_512x512.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_A9ABD877_512x512_atlas.json",atlas)
sb=dds.read_bytes(); ab=atlas.read_bytes()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
 d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
 for z in bands[1:]: m=ImageChops.lighter(m,z)
 return bmask(m)
def comp(im,bg=(72,72,72,255)):
 z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
if blob(sb)!="8d4c508477442b5278c3bda3ba4fc5efcbdc1027": raise RuntimeError(("source drift",blob(sb)))
if blob(ab)!="805d46d27b32d09f8eecb553095e3f3fc65d7167": raise RuntimeError(("atlas drift",blob(ab)))
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12); pf=struct.unpack_from("<8I",sb,76); fourcc,bpp,rm,gm,bm,am=pf[2],pf[3],pf[4],pf[5],pf[6],pf[7]
mode="RGBA" if fourcc==0 and bpp==32 and (rm,gm,bm)==(0xff,0xff00,0xff0000) else ("BGRA" if fourcc==0 and bpp==32 and (rm,gm,bm)==(0xff0000,0xff00,0xff) else None)
if not mode or (W,H)!=(2048,2048) or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,fourcc,bpp,mode,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode); src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regions={r["idx"]:r for r in json.loads(ab.decode())["regions"]}
specs=[
(0,"CONIFEROUS FOREST","코니퍼러스 포레스트","stage"),(1,"ICE SCAPE","아이스스케이프","stage"),
(2,"GIANT STATUES","자이언트 스태추스","stage"),(3,"GHOST FOREST","고스트 포레스트","stage"),
(4,"FLORAL VILLAGE","플로럴 빌리지","stage"),(5,"DESERT","데저트","stage"),(6,"DEEP LAKE","딥 레이크","stage"),
(7,"CLOUDY HIGHLAND","클라우디 하이랜드","stage"),(8,"CASTLE WALL","캐슬 월","stage"),(9,"CASINO TOWN","카지노 타운","stage"),
(10,"CAPE WAY","케이프 웨이","stage"),(11,"CANYON","캐니언","stage"),(12,"BIG FOREST","빅 포레스트","stage"),(13,"BAY AREA","베이 에어리어","stage"),
(14,"Special","스페셜","ui"),(15,"STAGES","스테이지","ui"),(16,"GOALS","골","ui")]
protected_ids={17:"Night Bird song title",18:"Radiation song title"}
source_mask=Image.new("L",(W,H),0); allowed=Image.new("L",(W,H),0); rows=[]
for idx,en,ko,kind in specs:
 x,y,cw,ch=regions[idx]["rect"]; cell=src.crop((x,y,x+cw,y+ch)); lm=bmask(cell.getchannel("A")); bb=lm.getbbox()
 if not bb: raise RuntimeError(("empty",idx,en))
 ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
 source_mask.paste(ImageChops.lighter(source_mask.crop((x,y,x+cw,y+ch)),lm),(x,y))
 ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
 vals=[]; p=cell.load()
 for yy in range(ch):
  for xx in range(cw):
   rr,gg,bbv,aa=p[xx,yy]
   if aa>=96: vals.append((rr,gg,bbv,aa))
 med=[int(round(statistics.median(v[k] for v in vals))) for k in range(4)]
 rows.append({"region_idx":idx,"source":en,"korean":ko,"kind":kind,"cell":[x,y,cw,ch],"original_bbox":ob,
              "source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],"source_median_rgba":med})
clean=src.copy(); ca=clean.getchannel("A"); ca.paste(0,(0,0,W,H),source_mask); clean.putalpha(ca)
sp=out/"A69_SOURCE_READABLE.png"; cp=out/"A69_CLEAN_PLATE.png"; smp=out/"A69_SOURCE_TEXT_MASK.png"; ap=out/"A69_ALLOWED_BBOX_MASK.png"
src.save(sp); clean.save(cp); source_mask.save(smp); allowed.save(ap)
protected=ImageChops.multiply(bmask(src.getchannel("A")),ImageOps.invert(allowed)); pp=out/"A69_PROTECTED_VISIBLE_MASK.png"; protected.save(pp)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(smp),"--protected-mask",str(pp),"--report",str(out/"A69_CLEAN_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"A69_CLEAN_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean",cleanrep))
subprocess.run(["sudo","apt-get","update","-qq"],check=True); subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
font_line=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Black"],text=True).strip(); FONT,FI,FSTYLE=font_line.rsplit("|",2); FI=int(FI or 0)
def render_low(text,fs,fill):
 f=ImageFont.truetype(FONT,fs,index=FI); bb=ImageDraw.Draw(Image.new("L",(8,8),0)).textbbox((0,0),text,font=f)
 a=Image.new("L",(max(8,bb[2]-bb[0]+4),max(8,bb[3]-bb[1]+4)),0); ImageDraw.Draw(a).text((2-bb[0],2-bb[1]),text,font=f,fill=255)
 ab=a.getbbox(); a=a.crop(ab); rgba=Image.new("RGBA",a.size,(fill[0],fill[1],fill[2],255)); rgba.putalpha(a)
 return rgba.resize((rgba.width*4,rgba.height*4),Image.Resampling.NEAREST)
MX=6; MY=2
stage_rows=[r for r in rows if r["kind"]=="stage"]; shared_fs=None
for fs in range(28,6,-1):
 ok=True
 for r in stage_rows:
  lay=render_low(r["korean"],fs,r["source_median_rgba"])
  if lay.height>r["source_height"]-2*MY or lay.width>r["source_width"]-2*MX: ok=False; break
 if ok: shared_fs=fs; break
if shared_fs is None: raise RuntimeError("stage family fit")
final=clean.copy(); targets=[]; outrows=[]
for r in rows:
 ob=r["original_bbox"]; aw=r["source_width"]; ah=r["source_height"]; fill=r["source_median_rgba"]
 if r["kind"]=="stage":
  fs=shared_fs; align="right"
 else:
  fs=None
  for z in range(24,5,-1):
   lay0=render_low(r["korean"],z,fill)
   if lay0.height<=ah-2*MY and lay0.width<=aw-2*MX: fs=z; break
  if fs is None: raise RuntimeError(("ui fit",r["region_idx"],r["korean"],aw,ah))
  align="left"
 lay=render_low(r["korean"],fs,fill)
 if align=="right": px=ob[2]-MX-lay.width
 else: px=ob[0]+MX
 py=ob[1]+(ah-lay.height)//2
 if not(px>ob[0] and py>ob[1] and px+lay.width<ob[2] and py+lay.height<ob[3]): raise RuntimeError(("placement",r["region_idx"],ob,[px,py,px+lay.width,py+lay.height],fs))
 final.alpha_composite(lay,(px,py)); lm=Image.new("L",(W,H),0); lm.paste(bmask(lay.getchannel("A")),(px,py)); lb=list(lm.getbbox()); targets.append((r["region_idx"],lm))
 outrows.append({**r,"localized_bbox":lb,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
  "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
  "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","lowres_font_size":fs,"pixel_scale":4,"horizontal_scale":1.0,
  "alignment":align,"font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,"fill_rgba":[fill[0],fill[1],fill[2],255]})
ov=0; touch=[]
for i in range(len(targets)):
 for j in range(i+1,len(targets)):
  aa=targets[i][1]; bbm=targets[j][1]; x=count(ImageChops.multiply(aa,bbm)); n=count(ImageChops.multiply(aa.filter(ImageFilter.MaxFilter(3)),bbm)); ov+=x
  if x or n: touch.append([targets[i][0],targets[j][0],x,n])
if ov or touch: raise RuntimeError(("overlap/touch",ov,touch))
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM); payload=sb[:128]+raw_final.tobytes("raw",mode); candidate.write_bytes(payload)
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode); dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip")
fp=out/"A69_FINAL_DECODED_READABLE.png"; dec.save(fp)
subprocess.run(["python3",str(validator),str(sp),str(fp),str(ap),"--protected-mask",str(pp),"--report",str(out/"A69_FINAL_VALIDATION.json")],check=True)
finalrep=json.loads((out/"A69_FINAL_VALIDATION.json").read_text())
diff=dmask(src,dec); outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed))); alphaout=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),ImageOps.invert(allowed))); prot=count(ImageChops.multiply(diff,protected))
target=Image.new("L",(W,H),0)
for _,m in targets: target=ImageChops.lighter(target,m)
residue=count(ImageChops.multiply(ImageChops.multiply(source_mask,ImageOps.invert(target)),bmask(dec.getchannel("A")))); render_outside=count(ImageChops.multiply(target,ImageOps.invert(allowed)))
preserved={}
for idx,label in protected_ids.items():
 x,y,cw,ch=regions[idx]["rect"]; preserved[str(idx)]={"label":label,"changed_pixels":count(dmask(src.crop((x,y,x+cw,y+ch)),dec.crop((x,y,x+cw,y+ch))))}
if finalrep["status"]!="PASS" or outside or alphaout or prot or residue or render_outside or ov or touch or any(v["changed_pixels"] for v in preserved.values()):
 raise RuntimeError(("gates",finalrep["status"],outside,alphaout,prot,residue,render_outside,ov,touch,preserved))
target.save(out/"A69_TARGET_TEXT_MASK.png")
cards=[]
for r in outrows:
 ob=r["original_bbox"]; cr=(max(0,ob[0]-10),max(0,ob[1]-10),min(W,ob[2]+10),min(H,ob[3]+10)); ims=[comp(z).crop(cr) for z in (src,clean,dec)]; sc=max(1,min(2,1400//max(1,ims[0].width))); ims=[z.resize((z.width*sc,z.height*sc),Image.Resampling.NEAREST) for z in ims]
 c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+30),"white"); xx=0
 for z in ims: c.paste(z,(xx,30)); xx+=z.width+6
 ImageDraw.Draw(c).text((5,5),f'{r["region_idx"]} {r["source"]} -> {r["korean"]} fs={r["lowres_font_size"]} {r["alignment"]}',fill="black"); cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+4*(len(cards)-1)),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.thumbnail((1900,12000),Image.Resampling.LANCZOS); sheet.save(out/"A69_ROW_CONTACTS.jpg",quality=97)
raw_final_img=dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM); rr=Image.new("RGB",(1024,2*1048),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_final_img)]):
 z=comp(im).resize((1024,1024),Image.Resampling.NEAREST); rr.paste(z,(0,i*1048+24)); ImageDraw.Draw(rr).text((4,i*1048+4),label,fill="black")
rr.save(out/"A69_RAW_COMPARE.jpg",quality=96)
rep={"schema_version":1,"role":"A","run":run,"index":201,"asset":asset,"readiness_tier":"A68_ONE_STAGE_TO_RENDER_COMPLETED_SAME_INVOCATION",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":commit,"git_blob_sha1":blob(sb),"atlas_git_blob_sha1":blob(ab),"source_sha256":sha(sb)},
 "semantic_binding":{"source_contact":"localization/graphics/role_A/20261005-A-PRODUCTION68-PREFLIGHT/A68_A9ABD877_SOURCE_ROWS.jpg","translations":{str(i):{"source":en,"korean":ko,"kind":kind} for i,en,ko,kind in specs},"protected":{"17":"Night Bird song title","18":"Radiation song title"}},
 "stage_name_policy":"PASS_CANONICAL_PHONETIC_TRANSLITERATION","song_title_policy":"PASS_NIGHT_BIRD_RADIATION_PIXEL_EXACT",
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "source_style":{"stage_family":"dark-gray/blue-gray bold condensed all-caps; right aligned","stage_shared_lowres_font_size":shared_fs,"ui_family":"dark-gray bold labels; left aligned","font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,"pixel_scale":4},
 "rows":outrows,"preserved_regions":preserved,"clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "decoded_changes":{"changed_pixels_total":count(diff),"outside":outside,"alpha_outside":alphaout,"protected_changed":prot,"exact_source_residue":residue,"render_outside_target":render_outside,"overlap":ov,"touch_pairs":touch},
 "candidate_sha256":sha(payload),"candidate_path":str(candidate.relative_to(repo)),"controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","runtime_validation":"UNTESTED","status":"A69_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"}
(out/"A69_A9ABD877_REPORT.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n")
(wr/"A69_A9ABD877.json").write_text(json.dumps({"run":run,"index":201,"asset":"A9ABD877","source_sha256":sha(sb),"candidate_sha256":sha(payload),"localized_physical_elements":17,"protected_song_regions":2,"bbox_size_positive_margin":"17/17 PASS","clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],"source_residue":residue,"outside":outside,"alpha_outside":alphaout,"protected_changed":prot,"render_outside_target":render_outside,"preserved_song_changes":sum(v["changed_pixels"] for v in preserved.values()),"overlap":ov,"touch_pairs":len(touch),"worker_status":rep["status"],"runtime_validation":"UNTESTED","report":f"localization/graphics/role_A/{run}/A69_A9ABD877_REPORT.json"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":run,"asset":"A9ABD877","candidate_sha256":sha(payload),"stage_shared_fs":shared_fs,"status":rep["status"]},ensure_ascii=False))
