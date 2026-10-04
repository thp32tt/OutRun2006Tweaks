#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,statistics,traceback
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B": raise SystemExit("worker B only")
repo=Path.cwd(); run="20261005-B-PRODUCTION63"; out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/49BB5FE5_128x32.dds"; index=152
cand=repo/"localization/graphics/hd_candidates"/asset; cand.parent.mkdir(parents=True,exist_ok=True)
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"; base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/b63"); work.mkdir(exist_ok=True); dds=work/"src.dds"; atlas=work/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/49BB5FE5_128x32.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_49BB5FE5_128x32_atlas.json",atlas)
sb=dds.read_bytes(); ab=atlas.read_bytes()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
 d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
 for z in bands[1:]: m=ImageChops.lighter(m,z)
 return bmask(m)
if blob(sb)!="0288babbb9c70e8f092bdd15561db4cadc19dcb3" or blob(ab)!="ca611e5b613c7fe73eee1b66d4fe89465b52b709": raise RuntimeError("input drift")
H,W,mips=struct.unpack_from("<III",sb,12)[0],struct.unpack_from("<I",sb,16)[0],struct.unpack_from("<I",sb,28)[0]
pf=struct.unpack_from("<8I",sb,76)
if (W,H)!=(512,128) or struct.pack("<I",pf[2])!=b"DXT5" or len(sb)!=65664: raise RuntimeError(("structure",W,H,mips,pf,len(sb)))
raw_src=Image.open(dds).convert("RGBA"); src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regions={r["idx"]:r for r in json.loads(ab.decode("utf-8"))["regions"]}
specs=[(0,"PRO.","프로"),(1,"INS.","연주"),(2,"G.M.","기타"),(3,"E.R.","유로")]
preserve=[4,5]

def resolve_font():
 def pick():
  for p in ["Noto Sans CJK KR:style=Bold","Noto Sans CJK KR:style=Black"]:
   try:s=subprocess.check_output(["fc-match","-f","%{file}|%{index}",p],text=True).strip()
   except:s=""
   if "|" in s:
    fp,idx=s.rsplit("|",1)
    if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name: return fp,int(idx or 0),p
  return None
 g=pick()
 if g:return g
 subprocess.run(["sudo","apt-get","update","-qq"],check=True); subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
 g=pick()
 if not g:raise RuntimeError("font unavailable")
 return g
FONT,FIDX,FPAT=resolve_font()

source_masks=[]; rows=[]; clean=src.copy(); allowed=Image.new("L",(W,H),0); source_union=Image.new("L",(W,H),0)
for idx,en,ko in specs:
 x,y,cw,ch=regions[idx]["rect"]; cell=src.crop((x,y,x+cw,y+ch)); pix=cell.load()
 bgvals=[]
 for yy in range(5,ch-5):
  for xx in range(5,cw-5):
   r,g,b,a=pix[xx,yy]
   if a>180 and max(r,g,b)<220: bgvals.append((r,g,b,a))
 if len(bgvals)<100: raise RuntimeError(("bg samples",idx,len(bgvals)))
 bg=tuple(int(statistics.median(v[i] for v in bgvals)) for i in range(4))
 mask=Image.new("L",(cw,ch),0); mp=mask.load()
 for yy in range(3,ch-3):
  for xx in range(3,cw-3):
   r,g,b,a=pix[xx,yy]
   mean=(r+g+b)/3; bgmean=sum(bg[:3])/3
   dist=((r-bg[0])**2+(g-bg[1])**2+(b-bg[2])**2)**0.5
   chrom=max(r,g,b)-min(r,g,b); bgchrom=max(bg[:3])-min(bg[:3])
   if a>100 and mean>bgmean+15 and dist>25 and chrom<max(40,bgchrom*0.75):
    mp[xx,yy]=255
 # absorb 1px antialias fringe only around detected text, excluding plate edge
 grown=mask.filter(ImageFilter.MaxFilter(3)); gp=grown.load()
 for yy in range(3,ch-3):
  for xx in range(3,cw-3):
   if mp[xx,yy] or not gp[xx,yy]: continue
   r,g,b,a=pix[xx,yy]; mean=(r+g+b)/3; bgmean=sum(bg[:3])/3
   if a>80 and mean>bgmean+8: mp[xx,yy]=255
 bb=mask.getbbox()
 if not bb: raise RuntimeError(("mask empty",idx,bg))
 ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
 globalm=Image.new("L",(W,H),0); globalm.paste(mask,(x,y)); source_masks.append((idx,globalm))
 source_union=ImageChops.lighter(source_union,globalm); ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
 # reconstruct source text to dominant pill color but preserve original per-pixel alpha
 ca=cell.getchannel("A"); fill=Image.new("RGBA",cell.size,bg); fill.putalpha(ca); cc=cell.copy(); cc.paste(fill,(0,0),mask); clean.paste(cc,(x,y))
 rows.append({"region_idx":idx,"source":en,"korean":ko,"cell":regions[idx]["rect"],"source_text_bbox":ob,"pill_bg_rgba":bg,"source_text_pixels":count(mask)})

# verify preserved '89/'86 cells are untouched in clean
for idx in preserve:
 x,y,cw,ch=regions[idx]["rect"]
 if ImageChops.difference(src.crop((x,y,x+cw,y+ch)),clean.crop((x,y,x+cw,y+ch))).getbbox(): raise RuntimeError(("preserve changed",idx))

# render shared Korean badge style in white, fit each exact glyph bbox with positive margins
final=clean.copy(); target_union=Image.new("L",(W,H),0); target_masks=[]
common=None
for fs in range(44,10,-1):
 f=ImageFont.truetype(FONT,fs,index=FIDX); ok=True; tiles=[]
 for r in rows:
  ob=r["source_text_bbox"]; aw,ah=ob[2]-ob[0],ob[3]-ob[1]; d=ImageDraw.Draw(Image.new("L",(8,8),0)); tb=d.textbbox((0,0),r["korean"],font=f,stroke_width=1)
  lay=Image.new("RGBA",(tb[2]-tb[0]+8,tb[3]-tb[1]+8),(0,0,0,0)); ImageDraw.Draw(lay).text((4-tb[0],4-tb[1]),r["korean"],font=f,fill=(255,255,255,255),stroke_width=1,stroke_fill=(255,255,255,255))
  bb=lay.getchannel("A").getbbox(); lay=lay.crop(bb)
  if lay.width>aw-4 or lay.height>ah-4: ok=False; break
  tiles.append(lay)
 if ok: common=(fs,tiles); break
if common is None: raise RuntimeError("no shared fit")
fs,tiles=common
for r,lay in zip(rows,tiles):
 ob=r["source_text_bbox"]; aw,ah=ob[2]-ob[0],ob[3]-ob[1]; pos=(ob[0]+(aw-lay.width)//2,ob[1]+(ah-lay.height)//2); final.alpha_composite(lay,pos)
 lm=Image.new("L",(W,H),0); lm.paste(bmask(lay.getchannel("A")),pos); lb=list(lm.getbbox())
 if not(lb[0]>ob[0] and lb[1]>ob[1] and lb[2]<ob[2] and lb[3]<ob[3]): raise RuntimeError(("margin",r["region_idx"],ob,lb))
 target_union=ImageChops.lighter(target_union,lm); target_masks.append((r["region_idx"],lm)); r.update({"localized_bbox":lb,"source_width":aw,"source_height":ah,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],"delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],"containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","font_size":fs,"font_file":Path(FONT).name,"font_face_index":FIDX,"font_pattern":FPAT})

# encode DXT5 then splice only 4x4 blocks intersecting the exact source-text masks/bboxes.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM); encp=work/"enc.dds"; raw_final.save(encp,pixel_format="DXT5")
eb=encp.read_bytes()
if len(eb)!=len(sb) or eb[84:88]!=b"DXT5": raise RuntimeError(("Pillow DXT5 encoding structure",len(eb),eb[84:88]))
# source/current and encoded DXT5 data are 16-byte blocks, 128 blocks/row, 32 block rows
outb=bytearray(sb); blocks=set()
# convert readable allowed bboxes to raw Y then mark intersecting blocks
for r in rows:
 x0,y0,x1,y1=r["source_text_bbox"]; ry0=H-y1; ry1=H-y0
 for by in range(ry0//4,(ry1-1)//4+1):
  for bx in range(x0//4,(x1-1)//4+1): blocks.add((bx,by))
for bx,by in blocks:
 off=128+(by*(W//4)+bx)*16; outb[off:off+16]=eb[off:off+16]
payload=bytes(outb)
tmp=work/"candidate.dds"; tmp.write_bytes(payload)
raw_dec=Image.open(tmp).convert("RGBA"); dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
diff=dmask(src,dec); outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_out=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),ImageOps.invert(allowed)))
exact_residue=count(ImageChops.multiply(ImageChops.multiply(source_union,ImageOps.invert(target_union)),ImageOps.invert(diff)))
overlap=0; touch=[]
for i in range(len(target_masks)):
 for j in range(i+1,len(target_masks)):
  ov=count(ImageChops.multiply(target_masks[i][1],target_masks[j][1])); near=count(ImageChops.multiply(target_masks[i][1].filter(ImageFilter.MaxFilter(3)),target_masks[j][1])); overlap+=ov
  if ov or near: touch.append([target_masks[i][0],target_masks[j][0],ov,near])
# preserve year badges decoded pixels exactly
preserve_diff=0
for idx in preserve:
 x,y,cw,ch=regions[idx]["rect"]; preserve_diff+=count(dmask(src.crop((x,y,x+cw,y+ch)),dec.crop((x,y,x+cw,y+ch))))
diagnostic={"outside":outside,"alpha_outside":alpha_out,"exact_source_residue":exact_residue,"preserve_year_badge_changed_pixels":preserve_diff,"overlap":overlap,"touch_pairs":touch,"edited_dxt5_blocks":len(blocks)}
if outside or alpha_out or exact_residue or preserve_diff or overlap or touch:
 (out/"B63_DXT5_FAIL_CLOSED.json").write_text(json.dumps({"schema_version":1,"role":"B","run":run,"index":index,"asset":asset,"source_sha256":sha(sb),"status":"HOLD_STRICT_RECHECK_DXT5_DECODED_PIXEL_GATE","diagnostic":diagnostic,"reason":"DXT5 re-encoding/splice cannot satisfy exact decoded-pixel containment/residue gate without altering pixels outside exact source text bbox; candidate not persisted","RUNTIME_VALIDATION":"UNTESTED"},ensure_ascii=False,indent=2)+"\n")
 (wr/"B63_49BB5FE5_FAIL.json").write_text(json.dumps({"run":run,"index":index,"status":"HOLD_STRICT_RECHECK_DXT5_DECODED_PIXEL_GATE","diagnostic":diagnostic,"candidate_written":False,"RUNTIME_VALIDATION":"UNTESTED"},indent=2)+"\n")
 print(json.dumps({"status":"HOLD_STRICT_RECHECK_DXT5_DECODED_PIXEL_GATE","diagnostic":diagnostic})); raise SystemExit(0)

cand.write_bytes(payload); csha=sha(payload)
# evidence only on full pass
src.save(out/"49BB_SOURCE_READABLE.png"); clean.save(out/"49BB_CLEAN_PLATE.png"); dec.save(out/"49BB_FINAL_DECODED.png"); source_union.save(out/"49BB_SOURCE_TEXT_MASK.png"); allowed.save(out/"49BB_ALLOWED_BBOX_MASK.png"); target_union.save(out/"49BB_TARGET_TEXT_MASK.png")
report={"schema_version":1,"role":"B","run":run,"index":index,"asset":asset,"source_sha256":sha(sb),"candidate_sha256":csha,"structure":{"dimensions":[W,H],"format":"DXT5","mipmaps":mips,"raw_orientation":"mirror_y","source_header_128_exact":payload[:128]==sb[:128]},"rows":rows,"preserved_regions":{"4":"'89","5":"'86"},"decoded_pixel_qa":diagnostic,"controller_visual_qa":"PENDING","status":"B_PRODUCTION63_WORKER_STATIC_PASS_PENDING_CONTROLLER_AND_C","RUNTIME_VALIDATION":"UNTESTED"}
(out/"B63_49BB_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n"); (wr/"B63_49BB5FE5.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"status":report["status"],"candidate_sha256":csha,"diagnostic":diagnostic}))
