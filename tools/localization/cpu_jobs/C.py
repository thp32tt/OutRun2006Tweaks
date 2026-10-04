#!/usr/bin/env python3
import hashlib, json, os, struct, subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "C":
    raise SystemExit("Run only in GitHub-hosted localization CPU worker as role C.")

repo=Path.cwd()
run="20261004-1720-C91"
outdir=repo/"localization/graphics/role_C"/run
outdir.mkdir(parents=True,exist_ok=True)

ASSETS=[
 {
  "key":"571E78F3",
  "source":"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/571E78F3_512x64.dds",
  "candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/571E78F3_512x64.dds",
  "source_sha":"17ee051e59d23c741c9df428dccd3ee2f7863c19a038f02db250001f44b6c121",
  "input_sha":"0eb421ac34ec47c6b7ef571b3b17f1e53cb91c65cb89e34bcc7f7c35b5bbdba4",
  "rows":[
   {"key":"571E78F3_1","korean":"타임 어택 모드","sprite_cell":[380,8,1340,140],"original_bbox":[395,15,1330,140],"input_localized_bbox":[541,12,1262,140],"scale":0.94},
   {"key":"571E78F3_2","korean":"15코스 연속","sprite_cell":[500,132,1612,252],"original_bbox":[520,132,1590,245],"input_localized_bbox":[818,136,1293,248],"scale":0.94},
  ]
 },
 {
  "key":"62BEBF33",
  "source":"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/62BEBF33_512x64.dds",
  "candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/62BEBF33_512x64.dds",
  "source_sha":"f0a8491585dd4f225c4707b63bd61ae43869cb9d243d9de881258add023c06e2",
  "input_sha":"def5f018e3effa33d1473dfa0c2c8cab390f88cf76284a81945128f8995ee09d",
  "rows":[
   {"key":"62BEBF33_1","korean":"아웃런 모드","sprite_cell":[380,44,1372,208],"original_bbox":[392,52,1357,201],"input_localized_bbox":[565,51,1186,199],"scale":0.96},
  ]
 },
 {
  "key":"E3FD08BE",
  "source":"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/E3FD08BE_512x64.dds",
  "candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/E3FD08BE_512x64.dds",
  "source_sha":"ebc2d866597955c6e802de65eff2d07e048f66b4ae2770fffd86b81b61fd5845",
  "input_sha":"12f5593406a5a3c8d3cd1c025c7ff4dd1e97e265e31ba997fb0f4b89d80eb4bc",
  "rows":[
   {"key":"E3FD08BE_1","korean":"하트 어택 모드","sprite_cell":[380,44,1640,208],"original_bbox":[393,54,1628,200],"input_localized_bbox":[632,53,1388,198],"scale":0.96},
  ]
 },
]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def dds_meta(p):
 b=Path(p).read_bytes()
 if b[:4]!=b"DDS ": raise RuntimeError("not DDS "+str(p))
 h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
 mips=struct.unpack_from("<I",b,28)[0]; fourcc=b[84:88]
 if fourcc!=b"DXT5": raise RuntimeError(("expected DXT5",p,fourcc))
 need=128+((w+3)//4)*((h+3)//4)*16
 if mips!=1 or len(b)!=need: raise RuntimeError(("unexpected DXT5 layout",p,w,h,mips,len(b),need))
 return b,{"width":w,"height":h,"mips":mips,"fourcc":"DXT5","bytes":len(b)}

def decode_readable(p):
 raw=Image.open(p).convert("RGBA")
 return raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

def rectmask(size,boxes):
 m=Image.new("L",size,0); d=ImageDraw.Draw(m)
 for x0,y0,x1,y1 in boxes: d.rectangle((x0,y0,x1-1,y1-1),fill=255)
 return m

def bool_bbox(mask):
 ys,xs=np.nonzero(mask)
 if not len(xs): return None
 return [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]

def count_visible_diff(a,b,allowed):
 aa=np.asarray(a,dtype=np.uint8); bb=np.asarray(b,dtype=np.uint8)
 diff=np.any(aa!=bb,axis=2)
 visible=(aa[:,:,3]>0)|(bb[:,:,3]>0)
 outside=np.logical_and(np.logical_and(diff,visible),np.logical_not(allowed))
 alpha=np.logical_and(aa[:,:,3]!=bb[:,:,3],np.logical_not(allowed))
 return int(np.count_nonzero(diff)),int(np.count_nonzero(outside)),int(np.count_nonzero(alpha)),bool_bbox(diff)

def card(label,im,bg=(64,64,64,255),max_w=900,max_h=420):
 q=Image.new("RGBA",im.size,bg); q.alpha_composite(im); v=q.convert("RGB")
 v.thumbnail((max_w,max_h),Image.Resampling.LANCZOS)
 c=Image.new("RGB",(v.width,v.height+28),"white"); c.paste(v,(0,28))
 ImageDraw.Draw(c).text((5,5),label,fill="black",font=ImageFont.load_default())
 return c

def save_compare(key,src,clean,before,final):
 cards=[card("SOURCE_READABLE",src),card("CLEAN_READABLE",clean),card("BEFORE_READABLE",before),card("FINAL_READABLE",final),
        card("SOURCE_RAW",src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)),card("FINAL_RAW",final.transpose(Image.Transpose.FLIP_TOP_BOTTOM))]
 gap=8; cols=2
 widths=[max(cards[i].width for i in range(c,len(cards),cols)) for c in range(cols)]
 rowhs=[]
 for r in range((len(cards)+cols-1)//cols): rowhs.append(max(cards[i].height for i in range(r*cols,min((r+1)*cols,len(cards)))))
 sheet=Image.new("RGB",(sum(widths)+gap,max(sum(rowhs)+gap*(len(rowhs)-1),1)),"white")
 y=0
 for r,rh in enumerate(rowhs):
  x=0
  for c in range(cols):
   i=r*cols+c
   if i<len(cards): sheet.paste(cards[i],(x,y))
   x+=widths[c]+gap
  y+=rh+gap
 sheet.save(outdir/f"C91_{key}_FULL_COMPARE.jpg",quality=94)

def save_rows(key,src,before,final,rows):
 strips=[]
 font=ImageFont.load_default()
 for row in rows:
  x0,y0,x1,y1=row["sprite_cell"]; pad=8
  cr=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad))
  cs=[]
  for tag,im in (("SRC",src),("BEFORE",before),("FINAL",final)):
   q=Image.new("RGBA",im.size,(64,64,64,255)); q.alpha_composite(im)
   v=q.convert("RGB").crop(cr); v.thumbnail((700,220),Image.Resampling.LANCZOS)
   c=Image.new("RGB",(720,250),"white"); c.paste(v,((720-v.width)//2,25+(220-v.height)//2))
   ImageDraw.Draw(c).text((5,5),f'{row["key"]} {tag}',fill="black",font=font); cs.append(c)
  strip=Image.new("RGB",(720*3+12,250),"white")
  for i,c in enumerate(cs): strip.paste(c,(i*(720+6),0))
  strips.append(strip)
 sheet=Image.new("RGB",(strips[0].width,sum(x.height for x in strips)),"white")
 y=0
 for s in strips: sheet.paste(s,(0,y)); y+=s.height
 sheet.save(outdir/f"C91_{key}_ROW_CONTACT.jpg",quality=95)

# nvcompress is used only for the touched DXT5 blocks; current candidate header and all untouched blocks remain byte-exact.
if not Path("/usr/bin/nvcompress").exists():
 subprocess.run(["sudo","apt-get","update","-qq"],check=True)
 subprocess.run(["sudo","apt-get","install","-y","-qq","libnvtt-bin"],check=True)
nvcompress=Path("/usr/bin/nvcompress")
if not nvcompress.exists(): raise RuntimeError("nvcompress unavailable")

all_results=[]
for spec in ASSETS:
 key=spec["key"]; source=repo/spec["source"]; cand=repo/spec["candidate"]
 if sha(source)!=spec["source_sha"]: raise RuntimeError(key+" source SHA mismatch")
 if sha(cand)!=spec["input_sha"]: raise RuntimeError(key+" input candidate SHA mismatch")
 sb,smeta=dds_meta(source); cb,cmeta=dds_meta(cand)
 if sb[:128]!=cb[:128] or smeta!=cmeta: raise RuntimeError(key+" current candidate structure/header drift")
 src=decode_readable(source); before=decode_readable(cand)
 if src.size!=(smeta["width"],smeta["height"]): raise RuntimeError(key+" decode size mismatch")
 W,H=src.size

 allowed_boxes=[r["original_bbox"] for r in spec["rows"]]
 allowed_img=rectmask(src.size,allowed_boxes); allowed=np.asarray(allowed_img)>0
 protected_img=ImageChops.invert(allowed_img)

 # Exact transparent clean plate for these standalone text atlases: remove only canonical source-alpha pixels inside exact source bboxes.
 src_arr=np.asarray(src,dtype=np.uint8).copy(); clean_arr=src_arr.copy()
 source_text=np.zeros((H,W),dtype=bool)
 for row in spec["rows"]:
  x0,y0,x1,y1=row["original_bbox"]
  source_text[y0:y1,x0:x1]=src_arr[y0:y1,x0:x1,3]>0
 clean_arr[source_text]=0
 clean=Image.fromarray(clean_arr,"RGBA")
 source_mask=Image.fromarray((source_text.astype(np.uint8)*255),"L")
 clean_total,clean_out,clean_alpha_out,clean_bbox=count_visible_diff(src,clean,source_text)
 if clean_out or clean_alpha_out: raise RuntimeError((key,"clean gate",clean_out,clean_alpha_out))
 
 # Small C corrective rework: downscale accepted localized raster (never upscale), center with margin inside exact C85 source bbox.
 final=before.copy()
 final_arr=np.asarray(final,dtype=np.uint8).copy()
 transformed=[]
 for row in spec["rows"]:
  cx0,cy0,cx1,cy1=row["sprite_cell"]
  # Clear the full isolated cell; these assets are standalone label atlases and the C81 visual evidence confirms no protected non-text art in these cells.
  final_arr[cy0:cy1,cx0:cx1]=0
 final=Image.fromarray(final_arr,"RGBA")
 for row in spec["rows"]:
  ib=row["input_localized_bbox"]; ob=row["original_bbox"]
  crop=before.crop(tuple(ib))
  ab=crop.getchannel("A").getbbox()
  if not ab: raise RuntimeError((key,row["key"],"empty input Korean crop"))
  crop=crop.crop(ab)
  avail_w=max(1,(ob[2]-ob[0])-8); avail_h=max(1,(ob[3]-ob[1])-8)
  scale=min(float(row["scale"]),avail_w/crop.width,avail_h/crop.height)
  if not (0<scale<=1): raise RuntimeError((key,row["key"],"bad scale",scale))
  nw=max(1,round(crop.width*scale)); nh=max(1,round(crop.height*scale))
  glyph=crop.resize((nw,nh),Image.Resampling.LANCZOS)
  gab=glyph.getchannel("A").getbbox()
  if not gab: raise RuntimeError((key,row["key"],"empty scaled glyph"))
  glyph=glyph.crop(gab); nw,nh=glyph.size
  px=ob[0]+((ob[2]-ob[0])-nw)//2; py=ob[1]+((ob[3]-ob[1])-nh)//2
  if px<ob[0] or py<ob[1] or px+nw>ob[2] or py+nh>ob[3]: raise RuntimeError((key,row["key"],"fit fail"))
  final.alpha_composite(glyph,(px,py))
  transformed.append({"key":row["key"],"scale":scale,"precompress_bbox":[px,py,px+nw,py+nh]})

 # Compress a full raw-orientation scratch image with nvcompress; only selected blocks will be taken.
 raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
 tmp_png=Path("/tmp")/f"C91_{key}_raw.png"; tmp_dds=Path("/tmp")/f"C91_{key}_nv.dds"
 raw_final.save(tmp_png)
 subprocess.run([str(nvcompress),"-bc3","-nomips",str(tmp_png),str(tmp_dds)],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 tb,tmeta=dds_meta(tmp_dds)
 tmp_dec=Image.open(tmp_dds).convert("RGBA")
 arr_target=np.asarray(raw_final,dtype=np.int16); arr_dec=np.asarray(tmp_dec,dtype=np.int16)
 mae=float(np.mean(np.abs(arr_target-arr_dec)))
 mae_flip=float(np.mean(np.abs(arr_target-np.flipud(arr_dec))))
 if mae_flip+0.5<mae: raise RuntimeError((key,"nvcompress orientation flip suspected",mae,mae_flip))

 out=bytearray(cb); bw=(W+3)//4; bh=(H+3)//4
 patch_blocks=set()
 for row in spec["rows"]:
  # Patch all BC3 blocks intersecting old or exact source bbox; conversion to raw mirror-y coordinates is explicit.
  ib=row["input_localized_bbox"]; ob=row["original_bbox"]
  ux0=min(ib[0],ob[0]); uy0=min(ib[1],ob[1]); ux1=max(ib[2],ob[2]); uy1=max(ib[3],ob[3])
  ry0=H-uy1; ry1=H-uy0
  bx0=max(0,ux0//4); bx1=min(bw,(ux1+3)//4); by0=max(0,ry0//4); by1=min(bh,(ry1+3)//4)
  for by in range(by0,by1):
   for bx in range(bx0,bx1): patch_blocks.add((bx,by))
 for bx,by in patch_blocks:
  i=128+(by*bw+bx)*16
  out[i:i+16]=tb[i:i+16]
 cand.write_bytes(out)
 output_sha=sha(cand)
 fb,fmeta=dds_meta(cand)
 if fb[:128]!=sb[:128] or fmeta!=smeta: raise RuntimeError(key+" output header/structure mismatch")
 final_dec=decode_readable(cand)

 # C91 exact decoded gates.
 final_total,final_out,final_alpha_out,final_bbox=count_visible_diff(src,final_dec,allowed)
 if final_out or final_alpha_out: raise RuntimeError((key,"final outside gate",final_out,final_alpha_out,final_bbox))
 changed_blocks=0; outside_patch_blocks=0
 for by in range(bh):
  for bx in range(bw):
   i=128+(by*bw+bx)*16
   if cb[i:i+16]!=fb[i:i+16]:
    changed_blocks+=1
    if (bx,by) not in patch_blocks: outside_patch_blocks+=1
 if outside_patch_blocks: raise RuntimeError((key,"compressed collateral",outside_patch_blocks))

 row_reports=[]
 target=np.zeros((H,W),dtype=bool)
 for row,tmeta_row in zip(spec["rows"],transformed):
  cx0,cy0,cx1,cy1=row["sprite_cell"]; ob=row["original_bbox"]
  alpha=np.asarray(final_dec.getchannel("A"))>0
  local=np.zeros_like(alpha); local[cy0:cy1,cx0:cx1]=alpha[cy0:cy1,cx0:cx1]
  lb=bool_bbox(local)
  if not lb: raise RuntimeError((key,row["key"],"no final alpha"))
  ok=lb[0]>=ob[0] and lb[1]>=ob[1] and lb[2]<=ob[2] and lb[3]<=ob[3]
  if not ok: raise RuntimeError((key,row["key"],"post-BC3 containment fail",ob,lb))
  target[lb[1]:lb[3],lb[0]:lb[2]] |= alpha[lb[1]:lb[3],lb[0]:lb[2]]
  row_reports.append({
   "key":row["key"],"korean":row["korean"],"sprite_cell":row["sprite_cell"],
   "original_bbox":ob,"input_localized_bbox":row["input_localized_bbox"],"localized_bbox":lb,
   "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
   "containment":"PASS","rework_status":"C91_SMALL_CORRECTIVE_DOWNSCALE_CENTER",
   "requested_scale":row["scale"],"actual_precompress_scale":tmeta_row["scale"],
   "precompress_bbox":tmeta_row["precompress_bbox"]
  })

 source_mask.save(outdir/f"C91_{key}_SOURCE_TEXT_MASK.png")
 allowed_img.save(outdir/f"C91_{key}_ALLOWED_TEXT_REGION_MASK.png")
 protected_img.save(outdir/f"C91_{key}_PROTECTED_MASK.png")
 clean.save(outdir/f"C91_{key}_CLEAN_PLATE.png")
 Image.fromarray((target.astype(np.uint8)*255),"L").save(outdir/f"C91_{key}_TARGET_TEXT_MASK.png")
 save_compare(key,src,clean,before,final_dec)
 save_rows(key,src,before,final_dec,spec["rows"])

 result={
  "asset":key,"source_path":spec["source"],"candidate_path":spec["candidate"],
  "source_sha256":spec["source_sha"],"input_candidate_sha256":spec["input_sha"],"candidate_sha256":output_sha,
  "method":"C91 small corrective rework: exact canonical DXT5 source -> source-alpha clean plate evidence -> accepted current Korean raster downscale (no upscale) + recenter inside exact C85 source bbox -> nvcompress BC3 scratch -> patch only affected BC3 blocks into current exact-header candidate -> decoded strict QA",
  "structure":{**smeta,"header_128_exact_canonical":True,"raw_orientation":"mirror_y"},
  "clean_plate_gate":{"changed_pixels":clean_total,"changed_bbox":clean_bbox,"visible_changed_pixels_outside_source_text_mask":clean_out,"alpha_changed_pixels_outside_source_text_mask":clean_alpha_out,"status":"PASS"},
  "final_gate":{"changed_pixels":final_total,"changed_bbox":final_bbox,"visible_changed_pixels_outside_allowed_bboxes":final_out,"alpha_changed_pixels_outside_allowed_bboxes":final_alpha_out,"status":"PASS"},
  "compressed_patch_gate":{"patched_blocks":len(patch_blocks),"changed_blocks_vs_input_candidate":changed_blocks,"changed_blocks_outside_patch_set":outside_patch_blocks,"status":"PASS"},
  "bbox_gate":{"elements":len(row_reports),"pass":len(row_reports),"fail":0,"rows":row_reports,"status":"PASS"},
  "nvcompress_mae_raw_rgba":mae,"nvcompress_mae_if_flipped":mae_flip,
  "manual_visual_qa":"PENDING_CONTROLLER_VISUAL_QA",
  "runtime_validation":"UNTESTED",
  "status":"C91_WORKER_CORRECTIVE_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA_AND_INGAME"
 }
 (outdir/f"C91_{key}_REPORT.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 all_results.append(result)

summary={
 "schema_version":1,"role":"C","run":run,"base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "scope":"C small corrective rework of the three remaining C85 DXT5 exact-bbox failures; completed C90 assets not repeated; FD90AA9 large rework intentionally left for A/B producer lane",
 "assets":all_results,
 "summary":{"assets_reworked":3,"elements_reworked":4,"static_pass":3,"static_fail":0,"runtime_validation":"UNTESTED","vr_ffb_dx11_dxvk_changes":False},
 "RUNTIME_VALIDATION":"UNTESTED"
}
(outdir/"C91_DXT5_CORRECTIVE_STATIC_QA.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("C91_DXT5_CORRECTIVE_DONE",[(x["asset"],x["candidate_sha256"]) for x in all_results])
