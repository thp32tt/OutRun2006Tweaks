#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,statistics
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A": raise SystemExit("worker A only")
repo=Path.cwd(); run="20261005-A-PRODUCTION65"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/97E863AD_512x256.dds"; candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"; base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/a65"); work.mkdir(exist_ok=True); dds=work/"src.dds"; atlas=work/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/97E863AD_512x256.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_97E863AD_512x256_atlas.json",atlas)
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
if blob(sb)!="71c9961992b6718cd3da0222c83a88bd9cd22d7f": raise RuntimeError(("source drift",blob(sb)))
if blob(ab)!="2c826a5eadf4784ec50c26f4a6e269f86209be71": raise RuntimeError(("atlas drift",blob(ab)))
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12); pf=struct.unpack_from("<8I",sb,76); fourcc,bpp,rm,gm,bm,am=pf[2],pf[3],pf[4],pf[5],pf[6],pf[7]
mode="RGBA" if fourcc==0 and bpp==32 and (rm,gm,bm)==(0xff,0xff00,0xff0000) else ("BGRA" if fourcc==0 and bpp==32 and (rm,gm,bm)==(0xff0000,0xff00,0xff) else None)
if not mode or (W,H)!=(2048,1024) or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,fourcc,bpp,mode,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode); src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regions={r["idx"]:r for r in json.loads(ab.decode())["regions"]}
# A63 controller binding. Product tokens remain original Latin per C151 policy; protected product/model/logo regions are untouched.
specs={
 1:("View OutRun single player rankings!","OutRun 싱글 플레이 랭킹 보기","sentence_token","싱글 플레이 랭킹 보기"),
 2:("View OutRun2SP arcade rankings!","OutRun2SP 아케이드 랭킹 보기","sentence_token","아케이드 랭킹 보기"),
 3:("View the online multiplayer rankings!","온라인 멀티플레이 랭킹 보기","sentence","온라인 멀티플레이 랭킹 보기"),
 4:("SHOWROOM (OUTRUN line preserved)","쇼룸","showroom_bottom","쇼룸"),
 5:("MULTIPLAYER","멀티플레이","multiplayer","멀티플레이"),
 6:("Goal E","골 E","goal","골 E"),7:("Goal D","골 D","goal","골 D"),8:("Goal C","골 C","goal","골 C"),9:("Goal B","골 B","goal","골 B"),10:("Goal A","골 A","goal","골 A"),
 11:("15 Cont.","15코스","goal","15코스"),14:("WELCOME TO THE","환영합니다","welcome","환영합니다"),16:("ONLINE","온라인","online","온라인")
}
protected_regions={0:"OUTRUN2SP logo",12:"SP product fragment",13:"OR product fragment",15:"TESTAROSSA model name",17:"non-text black artwork"}

def word_spans(mask, expected_words):
    bb=mask.getbbox()
    if not bb: raise RuntimeError("empty word mask")
    cols=[]
    for xx in range(bb[0],bb[2]):
        if mask.crop((xx,bb[1],xx+1,bb[3])).getbbox(): cols.append(xx)
    runs=[]
    if cols:
        s=p=cols[0]
        for x in cols[1:]:
            if x==p+1: p=x
            else: runs.append((s,p+1)); s=p=x
        runs.append((s,p+1))
    if len(runs)<expected_words: raise RuntimeError(("too few x-runs",expected_words,runs))
    gaps=[(runs[i+1][0]-runs[i][1],i) for i in range(len(runs)-1)]
    cuts=sorted(i for _,i in sorted(gaps,reverse=True)[:expected_words-1])
    groups=[]; start=0
    for cut in cuts+[len(runs)-1]:
        g=runs[start:cut+1]
        groups.append((g[0][0],g[-1][1]))
        start=cut+1
    if len(groups)!=expected_words: raise RuntimeError(("word grouping",expected_words,groups,runs,gaps))
    return groups,sorted(gaps,reverse=True)

source_mask=Image.new("L",(W,H),0); allowed=Image.new("L",(W,H),0); rows=[]; preserve_masks={}; inline_tokens={}
inline_global=Image.new("L",(W,H),0)
for idx in range(18):
 x,y,cw,ch=regions[idx]["rect"]; cell=src.crop((x,y,x+cw,y+ch)); a=bmask(cell.getchannel("A")); bb=a.getbbox()
 if idx in protected_regions:
  preserve_masks[idx]=a; continue
 if idx not in specs: continue
 en,ko,kind,render_text=specs[idx]
 lm=a; localbb=bb; token_bbox_abs=None; token_label=None; token_gap_evidence=None
 if idx in (1,2):
  expected_words=5 if idx==1 else 4
  groups,gaps=word_spans(a,expected_words)
  tx0,tx1=groups[1]
  token=Image.new("L",(cw,ch),0); token.paste(a.crop((tx0,0,tx1,ch)),(tx0,0))
  tokenbb=token.getbbox()
  if not tokenbb: raise RuntimeError(("inline token empty",idx,groups))
  token_label="OutRun" if idx==1 else "OutRun2SP"
  token_bbox_abs=[x+tokenbb[0],y+tokenbb[1],x+tokenbb[2],y+tokenbb[3]]
  token_gap_evidence={"word_spans":groups,"largest_gaps":gaps[:expected_words+2]}
  inline_tokens[idx]=token
  inline_global.paste(ImageChops.lighter(inline_global.crop((x,y,x+cw,y+ch)),token),(x,y))
  lm=ImageChops.subtract(a,token)
  localbb=bb  # whole sentence remains the exact permitted element bbox
 if idx==4:
  if not bb: raise RuntimeError("idx4 empty")
  y0,y1=bb[1],bb[3]; occ=[]
  for yy in range(y0,y1):
   occ.append((yy,sum(1 for v in a.crop((bb[0],yy,bb[2],yy+1)).getdata() if v)))
  zeros=[yy for yy,n in occ if n==0 and y0+(y1-y0)//3 <= yy <= y0+2*(y1-y0)//3]
  if not zeros: raise RuntimeError(("idx4 no interline gap",bb))
  split=max(zeros)
  topmask=Image.new("L",(cw,ch),0); topmask.paste(a.crop((0,0,cw,split+1)),(0,0))
  bottom=Image.new("L",(cw,ch),0); bottom.paste(a.crop((0,split+1,cw,ch)),(0,split+1)); lm=bottom; localbb=lm.getbbox()
  if not localbb: raise RuntimeError(("idx4 bottom empty",split))
  preserve_masks[idx]=topmask
 if not localbb: raise RuntimeError(("target empty",idx))
 ob=[x+localbb[0],y+localbb[1],x+localbb[2],y+localbb[3]]
 source_mask.paste(ImageChops.lighter(source_mask.crop((x,y,x+cw,y+ch)),lm),(x,y)); ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
 vals=[]; p=cell.load()
 for yy in range(localbb[1],localbb[3]):
  for xx in range(localbb[0],localbb[2]):
   r,g,b,aa=p[xx,yy]
   if aa>=96 and lm.getpixel((xx,yy)): vals.append((r,g,b,aa))
 med=[int(round(statistics.median(v[k] for v in vals))) for k in range(4)]
 rows.append({"region_idx":idx,"source":en,"korean":ko,"render_text":render_text,"kind":kind,"cell":[x,y,cw,ch],"original_bbox":ob,"source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],"source_median_rgba":med,
              "preserved_inline_token":token_label,"preserved_inline_token_bbox":token_bbox_abs,"token_detection":token_gap_evidence})
clean=src.copy(); ca=clean.getchannel("A"); ca.paste(0,(0,0,W,H),source_mask); clean.putalpha(ca)
sp=out/"A65_SOURCE_READABLE.png"; cp=out/"A65_CLEAN_PLATE.png"; smp=out/"A65_SOURCE_TEXT_MASK.png"; ap=out/"A65_ALLOWED_BBOX_MASK.png"
src.save(sp); clean.save(cp); source_mask.save(smp); allowed.save(ap)
protected=ImageChops.lighter(ImageChops.multiply(bmask(src.getchannel("A")),ImageOps.invert(allowed)),inline_global); pp=out/"A65_PROTECTED_VISIBLE_MASK.png"; protected.save(pp)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(smp),"--protected-mask",str(pp),"--report",str(out/"A65_CLEAN_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"A65_CLEAN_VALIDATION.json").read_text()); 
if cleanrep["status"]!="PASS": raise RuntimeError(("clean",cleanrep))
subprocess.run(["sudo","apt-get","update","-qq"],check=True); subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
font_line=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Bold"],text=True).strip(); FONT,FI,FSTYLE=font_line.rsplit("|",2); FI=int(FI or 0)
def render_low(text,fs,fill):
 f=ImageFont.truetype(FONT,fs,index=FI); bb=ImageDraw.Draw(Image.new("L",(8,8),0)).textbbox((0,0),text,font=f)
 a=Image.new("L",(max(8,bb[2]-bb[0]+4),max(8,bb[3]-bb[1]+4)),0); ImageDraw.Draw(a).text((2-bb[0],2-bb[1]),text,font=f,fill=255)
 ab=a.getbbox(); a=a.crop(ab); rgba=Image.new("RGBA",a.size,(fill[0],fill[1],fill[2],255)); rgba.putalpha(a); return rgba.resize((rgba.width*4,rgba.height*4),Image.Resampling.NEAREST)
# Shared sizes only within matching source families. Inline product tokens stay source-pixel exact.
groups={"sentence":[1,2,3],"goal":[6,7,8,9,10,11]}
fs_group={}
for name,ids in groups.items():
 fs_group[name]=None
 for fs in range(24,5,-1):
  ok=True
  for r in rows:
   if r["region_idx"] not in ids: continue
   lay=render_low(r["render_text"],fs,r["source_median_rgba"])
   maxw=r["source_width"]-8
   if r["region_idx"] in (1,2):
    maxw=r["original_bbox"][2]-4-(r["preserved_inline_token_bbox"][2]+12)
   if lay.height>r["source_height"]-4 or lay.width>maxw: ok=False; break
  if ok: fs_group[name]=fs; break
 if fs_group[name] is None: raise RuntimeError(("group fit",name))
final=clean.copy(); targets=[]; outrows=[]
for r in rows:
 ob=r["original_bbox"]; aw=r["source_width"]; ah=r["source_height"]; fill=r["source_median_rgba"]; kind=r["kind"]
 if kind in ("sentence","sentence_token"): fs=fs_group["sentence"]
 elif kind=="goal": fs=fs_group["goal"]
 else:
  fs=None
  for z in range(30,5,-1):
   lay0=render_low(r["render_text"],z,fill)
   if lay0.height<=ah-4 and lay0.width<=aw-8: fs=z; break
  if fs is None: raise RuntimeError(("row fit",r["region_idx"],r["render_text"],aw,ah))
 lay=render_low(r["render_text"],fs,fill); sx=1.0
 if r["region_idx"] in (1,2):
  px=r["preserved_inline_token_bbox"][2]+12
  maxw=ob[2]-4-px
 else:
  px=ob[0]+4
  maxw=aw-8
 if lay.width>maxw:
  sx=maxw/lay.width; lay=lay.resize((int(maxw),lay.height),Image.Resampling.NEAREST)
 py=ob[1]+(ah-lay.height)//2
 if px+lay.width>=ob[2]: px=ob[2]-4-lay.width
 if not(px>ob[0] and py>ob[1] and px+lay.width<ob[2] and py+lay.height<ob[3]): raise RuntimeError(("placement",r["region_idx"],ob,[px,py,px+lay.width,py+lay.height]))
 final.alpha_composite(lay,(px,py)); lm=Image.new("L",(W,H),0); lm.paste(bmask(lay.getchannel("A")),(px,py)); lb=list(lm.getbbox()); targets.append((r["region_idx"],lm))
 outrows.append({**r,"localized_bbox":lb,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],"delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],"containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","lowres_font_size":fs,"pixel_scale":4,"horizontal_scale":round(sx,4),"alignment":"after_preserved_token" if r["region_idx"] in (1,2) else "left","font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,"fill_rgba":[fill[0],fill[1],fill[2],255]})
ov=0; touch=[]
for i in range(len(targets)):
 for j in range(i+1,len(targets)):
  aa=targets[i][1]; bb=targets[j][1]; x=count(ImageChops.multiply(aa,bb)); n=count(ImageChops.multiply(aa.filter(ImageFilter.MaxFilter(3)),bb)); ov+=x
  if x or n: touch.append([targets[i][0],targets[j][0],x,n])
if ov or touch: raise RuntimeError(("overlap/touch",ov,touch))
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM); payload=sb[:128]+raw_final.tobytes("raw",mode); candidate.write_bytes(payload)
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode); dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip")
fp=out/"A65_FINAL_DECODED_READABLE.png"; dec.save(fp)
subprocess.run(["python3",str(validator),str(sp),str(fp),str(ap),"--protected-mask",str(pp),"--report",str(out/"A65_FINAL_VALIDATION.json")],check=True)
finalrep=json.loads((out/"A65_FINAL_VALIDATION.json").read_text())
diff=dmask(src,dec); outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed))); alphaout=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),ImageOps.invert(allowed))); prot=count(ImageChops.multiply(diff,protected))
target=Image.new("L",(W,H),0)
for _,m in targets: target=ImageChops.lighter(target,m)
residue=count(ImageChops.multiply(ImageChops.multiply(source_mask,ImageOps.invert(target)),bmask(dec.getchannel("A")))); render_outside=count(ImageChops.multiply(target,ImageOps.invert(allowed)))
preserved={}
for idx,label in protected_regions.items():
 x,y,cw,ch=regions[idx]["rect"]; preserved[str(idx)]={"label":label,"changed_pixels":count(dmask(src.crop((x,y,x+cw,y+ch)),dec.crop((x,y,x+cw,y+ch))))}
x,y,cw,ch=regions[4]["rect"]; pm=preserve_masks[4]; idx4diff=dmask(src.crop((x,y,x+cw,y+ch)),dec.crop((x,y,x+cw,y+ch))); preserved["4_OUTRUN_TOP"]={"label":"OUTRUN product token line","changed_pixels":count(ImageChops.multiply(idx4diff,pm))}
for idx,label in ((1,"OutRun inline token"),(2,"OutRun2SP inline token")):
 x,y,cw,ch=regions[idx]["rect"]; tok=inline_tokens[idx]; dd=dmask(src.crop((x,y,x+cw,y+ch)),dec.crop((x,y,x+cw,y+ch)))
 preserved[f"{idx}_INLINE_TOKEN"]={"label":label,"bbox":next(r["preserved_inline_token_bbox"] for r in rows if r["region_idx"]==idx),"changed_pixels":count(ImageChops.multiply(dd,tok))}
token_overlap=count(ImageChops.multiply(target,inline_global))
if finalrep["status"]!="PASS" or outside or alphaout or prot or residue or render_outside or ov or touch or token_overlap or any(v["changed_pixels"] for v in preserved.values()): raise RuntimeError(("gates",finalrep["status"],outside,alphaout,prot,residue,render_outside,ov,touch,token_overlap,preserved))
target.save(out/"A65_TARGET_TEXT_MASK.png")
cards=[]
for r in outrows:
 ob=r["original_bbox"]; cr=(max(0,ob[0]-12),max(0,ob[1]-12),min(W,ob[2]+12),min(H,ob[3]+12)); ims=[comp(z).crop(cr) for z in (src,clean,dec)]; sc=max(1,min(2,1200//max(1,ims[0].width))); ims=[z.resize((z.width*sc,z.height*sc),Image.Resampling.NEAREST) for z in ims]
 c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+30),"white"); xx=0
 for z in ims: c.paste(z,(xx,30)); xx+=z.width+6
 ImageDraw.Draw(c).text((5,5),f'{r["region_idx"]} {r["source"]} -> {r["korean"]} fs={r["lowres_font_size"]} token={r["preserved_inline_token"]}',fill="black"); cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+4*(len(cards)-1)),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.thumbnail((1800,12000),Image.Resampling.LANCZOS); sheet.save(out/"A65_TARGET_CONTACTS.jpg",quality=97)
full=Image.new("RGB",(1024,3*536),"white")
for i,(label,im) in enumerate([("SOURCE",src),("CLEAN",clean),("FINAL",dec)]):
 z=comp(im).resize((1024,512),Image.Resampling.NEAREST); full.paste(z,(0,i*536+24)); ImageDraw.Draw(full).text((4,i*536+4),label,fill="black")
full.save(out/"A65_SOURCE_CLEAN_FINAL.jpg",quality=96)
raw_final_img=dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM); rr=Image.new("RGB",(1024,2*536),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_final_img)]):
 z=comp(im).resize((1024,512),Image.Resampling.NEAREST); rr.paste(z,(0,i*536+24)); ImageDraw.Draw(rr).text((4,i*536+4),label,fill="black")
rr.save(out/"A65_RAW_COMPARE.jpg",quality=96)
rep={"schema_version":1,"role":"A","run":run,"index":193,"asset":asset,"readiness_tier":"A63_ONE_STAGE_TO_RENDER_COMPLETED_SAME_INVOCATION",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":commit,"git_blob_sha1":blob(sb),"atlas_git_blob_sha1":blob(ab),"source_sha256":sha(sb)},
 "semantic_binding":{"localized_indices":sorted(specs),"protected_regions":protected_regions,"product_token_policy":{"idx1":"OutRun original word pixels preserved exact; only descriptor -> 싱글 플레이 랭킹 보기","idx2":"OutRun2SP original word pixels preserved exact; only descriptor -> 아케이드 랭킹 보기","idx4":"OUTRUN top line preserved pixel-exact; only SHOWROOM -> 쇼룸"}},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},"rows":outrows,"preserved_regions":preserved,
 "clean_plate_validator":cleanrep,"final_mask_validator":finalrep,"decoded_changes":{"changed_pixels_total":count(diff),"outside":outside,"alpha_outside":alphaout,"protected_changed":prot,"exact_source_residue":residue,"render_outside_target":render_outside,"overlap":ov,"touch_pairs":touch,"inline_token_overlap":token_overlap},
 "candidate_sha256":sha(payload),"candidate_path":str(candidate.relative_to(repo)),"controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","runtime_validation":"UNTESTED","status":"A65_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"}
(out/"A65_97E863AD_REPORT.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n")
(wr/"A65_97E863AD.json").write_text(json.dumps({"run":run,"index":193,"asset":"97E863AD","source_sha256":sha(sb),"candidate_sha256":sha(payload),"localized_physical_elements":len(specs),"protected_regions":len(protected_regions)+1,"bbox_size_positive_margin":f"{len(specs)}/{len(specs)} PASS","clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],"source_residue":residue,"outside":outside,"alpha_outside":alphaout,"protected_changed":prot,"render_outside_target":render_outside,"preserved_changes":sum(v["changed_pixels"] for v in preserved.values()),"inline_token_overlap":token_overlap,"overlap":ov,"touch_pairs":len(touch),"worker_status":rep["status"],"runtime_validation":"UNTESTED","report":f"localization/graphics/role_A/{run}/A65_97E863AD_REPORT.json"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":run,"asset":"97E863AD","candidate_sha256":sha(payload),"localized":len(specs),"preserved_changed":sum(v["changed_pixels"] for v in preserved.values()),"status":rep["status"]},ensure_ascii=False))
