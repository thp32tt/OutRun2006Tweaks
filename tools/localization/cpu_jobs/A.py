#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont
from scipy import ndimage
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")
repo=Path.cwd(); run="20261006-A-REWORK96R-E596B7AC"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
base_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load_dds(p):
 b=Path(p).read_bytes()
 if b[:4]!=b"DDS ": raise RuntimeError("not dds")
 h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]; pitch=struct.unpack_from("<I",b,20)[0]; mips=struct.unpack_from("<I",b,28)[0]
 fourcc=b[84:88]; bpp=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
 if bpp!=32 or fourcc!=b"\0\0\0\0" or mips!=1 or len(b)!=128+w*h*4: raise RuntimeError(("unsupported",w,h,mips,fourcc,bpp,len(b)))
 mode="BGRA" if masks==(0xff0000,0xff00,0xff,0xff000000) else "RGBA" if masks==(0xff,0xff00,0xff0000,0xff000000) else None
 if not mode: raise RuntimeError(("masks",masks))
 raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
 return b[:128],raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"width":w,"height":h,"pitch":pitch,"mips":mips,"bpp":bpp,"masks":[hex(x) for x in masks],"raw_mode":mode}
def write_dds(h,im,p,mode):
 payload=h+im.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw",mode); Path(p).write_bytes(payload); return hashlib.sha256(payload).hexdigest()
def bbox_mask(m):
 ys,xs=np.nonzero(m); return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
q=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
if not q or not Path(q).exists() or "NotoSansCJK" not in Path(q).name:
 subprocess.run(["sudo","apt-get","update","-qq"],check=True); subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
 q=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
FONT=q
def comp(im):
 bg=Image.new("RGBA",im.size,(240,240,240,255)); bg.alpha_composite(im); return bg.convert("RGB")
def component_rows(src,rowdefs,cap):
 a=np.asarray(src.getchannel("A"))>0; lab,n=ndimage.label(a); objs=ndimage.find_objects(lab); infos=[]
 for i,sl in enumerate(objs,1):
  if sl is None: continue
  y,x=sl; area=int((lab[sl]==i).sum()); infos.append((i,area,(.5*(x.start+x.stop),.5*(y.start+y.stop))))
 rows=[]
 for r in rowdefs:
  x0,y0,x1,y1=r["window"]; ids=[i for i,area,(cx,cy) in infos if area<=cap and x0<=cx<x1 and y0<=cy<y1]
  m=np.isin(lab,ids); bb=bbox_mask(m)
  if not bb: raise RuntimeError(("no components",r["key"],r["window"]))
  z=dict(r); z["source_mask"]=m; z["original_bbox"]=bb; z["component_ids"]=ids; rows.append(z)
 return rows
def color(sa,m):
 px=sa[m]; px=px[px[:,3]>160]
 if len(px)<10: px=sa[m]
 v=np.median(px[:,:3],axis=0).astype(int); return (int(v[0]),int(v[1]),int(v[2]),255)
def render(text,size,fill):
 f=ImageFont.truetype(FONT,size,index=1); pad=max(16,size//3); im=Image.new("RGBA",(2700,440),(0,0,0,0)); d=ImageDraw.Draw(im); d.text((pad,pad),text,font=f,fill=fill)
 bb=im.getchannel("A").getbbox()
 if not bb: raise RuntimeError(("empty",text))
 return im.crop(bb)
def process(s):
 p=Path("/tmp")/s["file"]; urllib.request.urlretrieve(base_url+s["file"],p)
 if sha(p)!=s["source_sha"]: raise RuntimeError(("source drift",s["file"],sha(p)))
 header,src,meta=load_dds(p)
 if [meta["width"],meta["height"]]!=s["size"]: raise RuntimeError(("size",s["file"],meta))
 sa=np.asarray(src); alpha=sa[:,:,3]>0; rows=component_rows(src,[dict(r) for r in s["rows"]],s["cap"])
 sm=np.zeros_like(alpha)
 for r in rows: sm|=r["source_mask"]
 protected=alpha&~sm; ca=sa.copy(); ca[sm]=0; clean=Image.fromarray(ca,"RGBA")
 fam_size={}
 for fam in sorted({r["family"] for r in rows}):
  grp=[r for r in rows if r["family"]==fam]; start=min(170,max(18,min(r["original_bbox"][3]-r["original_bbox"][1] for r in grp)-3)); chosen=None
  for size in range(start,15,-1):
   ok=True
   for r in grp:
    g=render(r["korean"],size,color(sa,r["source_mask"])); x0,y0,x1,y1=r["original_bbox"]
    if g.width>x1-x0-4 or g.height>y1-y0-4: ok=False; break
   if ok: chosen=size; break
  if chosen is None: raise RuntimeError(("no family fit",s["file"],fam))
  fam_size[fam]=chosen
 final=clean.copy(); allowed=np.zeros_like(alpha); rms=[]; ro=[]
 for r in rows:
  x0,y0,x1,y1=r["original_bbox"]; sw=x1-x0; sh=y1-y0; allowed[y0:y1,x0:x1]=1; fill=color(sa,r["source_mask"]); size=fam_size[r["family"]]; g=render(r["korean"],size,fill)
  px=x0+2; py=y0+(sh-g.height)//2
  if px+g.width>=x1 or py<=y0 or py+g.height>=y1: raise RuntimeError(("margin",s["file"],r["key"],g.size,r["original_bbox"],(px,py)))
  layer=Image.new("RGBA",src.size,(0,0,0,0)); layer.alpha_composite(g,(px,py)); gm=np.asarray(layer.getchannel("A"))>0
  if int((gm&protected).sum()): raise RuntimeError(("protected overlap",s["file"],r["key"]))
  final.alpha_composite(layer); rms.append(gm); lb=bbox_mask(gm)
  ro.append({"key":r["key"],"source":r["source"],"korean":r["korean"],"family":r["family"],"original_bbox":r["original_bbox"],"localized_bbox":lb,"component_count":len(r["component_ids"]),
   "source_width":sw,"source_height":sh,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
   "delta_left":lb[0]-x0,"delta_right":x1-lb[2],"delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
   "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","font":"Noto Sans CJK KR Black","font_size":size,"fill_rgba":list(fill),"alignment":"source-left+2 / vertical-center","render_resolution":f"native_{src.width}x{src.height}"})
 fa=np.asarray(final); changed=np.any(sa!=fa,axis=2); outside=int((changed&~allowed).sum()); alpha_out=int(((sa[:,:,3]!=fa[:,:,3])&~allowed).sum()); protected_changed=int((changed&protected).sum())
 ru=np.zeros_like(alpha)
 for m in rms: ru|=m
 render_protected=int((ru&protected).sum()); residue=int((sm&np.all(fa==sa,axis=2)&~ru).sum()); clean_res=0
 for r,m in zip(ro,rms):
  x0,y0,x1,y1=r["original_bbox"]; diff=np.any(fa[y0:y1,x0:x1]!=ca[y0:y1,x0:x1],axis=2); clean_res+=int((diff&~m[y0:y1,x0:x1]).sum())
 overlaps=[]; touches=[]
 for i in range(len(rms)):
  for j in range(i+1,len(rms)):
   ov=int((rms[i]&rms[j]).sum())
   if ov: overlaps.append([i,j,ov])
   t=int((ndimage.binary_dilation(rms[i],structure=np.ones((3,3),bool))&rms[j]).sum())
   if t: touches.append([i,j,t])
 if any([outside,alpha_out,protected_changed,render_protected,residue,clean_res]) or overlaps or touches: raise RuntimeError(("QA",s["file"],outside,alpha_out,protected_changed,render_protected,residue,clean_res,overlaps,touches))
 cand=repo/"localization/graphics/hd_candidates"/s["asset_rel"]; cand.parent.mkdir(parents=True,exist_ok=True); new_sha=write_dds(header,final,cand,meta["raw_mode"]); dh,decoded,dmeta=load_dds(cand)
 if dh!=header or dmeta!=meta or ImageChops.difference(decoded,final).getbbox(): raise RuntimeError(("roundtrip",s["file"]))
 pre=s["prefix"]; src.save(out/f"{pre}_SOURCE_READABLE.png"); clean.save(out/f"{pre}_CLEAN_PLATE.png"); decoded.save(out/f"{pre}_FINAL_READABLE.png")
 Image.fromarray((sm*255).astype(np.uint8),"L").save(out/f"{pre}_SOURCE_TEXT_MASK.png"); Image.fromarray((protected*255).astype(np.uint8),"L").save(out/f"{pre}_PROTECTED_MASK.png")
 cards=[]
 for r in ro:
  x0,y0,x1,y1=r["original_bbox"]; pad=8; crop=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad)); ps=[comp(x).crop(crop) for x in (src,clean,decoded)]; W=max(p.width for p in ps); H=max(p.height for p in ps)
  c=Image.new("RGB",(W*3+16,H+26),"white"); d=ImageDraw.Draw(c); d.text((4,3),r["key"]+" | SOURCE | CLEAN | FINAL",fill="black")
  for k,panel in enumerate(ps): c.paste(panel,(k*(W+8),26))
  cards.append(c)
 cw=max(c.width for c in cards); ch=sum(c.height for c in cards)+4*(len(cards)-1); sheet=Image.new("RGB",(cw,ch),"white"); yy=0
 for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
 sheet.thumbnail((3400,7000),Image.Resampling.LANCZOS); sheet.save(out/f"{pre}_SOURCE_CLEAN_FINAL_CONTACTS.jpg",quality=97)
 aa=comp(src); bb=comp(decoded); full=Image.new("RGB",(aa.width+bb.width+8,max(aa.height,bb.height)+28),"white"); ImageDraw.Draw(full).text((4,4),"SOURCE | FINAL",fill="black"); full.paste(aa,(0,28)); full.paste(bb,(aa.width+8,28)); full.thumbnail((3000,3000),Image.Resampling.LANCZOS); full.save(out/f"{pre}_READABLE_SOURCE_FINAL.jpg",quality=95)
 rr1=comp(src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)); rr2=comp(decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM)); raw=Image.new("RGB",(rr1.width+rr2.width+8,max(rr1.height,rr2.height)+28),"white"); ImageDraw.Draw(raw).text((4,4),"SOURCE | FINAL RAW",fill="black"); raw.paste(rr1,(0,28)); raw.paste(rr2,(rr1.width+8,28)); raw.thumbnail((3000,3000),Image.Resampling.LANCZOS); raw.save(out/f"{pre}_RAW_SOURCE_FINAL.jpg",quality=95)
 qa={"bbox_size_positive_margin":f"{len(ro)}/{len(ro)} PASS","changed_pixels":int(changed.sum()),"changed_outside_source_bboxes":outside,"alpha_changed_outside_source_bboxes":alpha_out,"protected_changed_pixels":protected_changed,"render_protected_overlap_pixels":render_protected,"source_exact_residue_pixels":residue,"clean_plate_residue_outside_korean_glyphs":clean_res,"localized_overlap_pairs":overlaps,"localized_1px_touch_pairs":touches,"dds_roundtrip":"PASS"}
 rep={"schema_version":1,"role":"A","run":run,"queue_index":s["index"],"asset":s["asset_rel"],"source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6","source_sha256":s["source_sha"],"source_url":base_url+s["file"]},"structure":{**meta,"header_128_exact":True,"raw_orientation":"mirror_y"},"transcription_correction":s.get("correction"),"candidate_sha256":new_sha,"candidate_path":str(cand.relative_to(repo)),"conceptual_segments":s["segments"],"localized_physical_rows":len(ro),"shared_family_font_sizes":fam_size,"rows":ro,"machine_qa":qa,"visual_qa":"PENDING_CONTROLLER_SELF_QA","runtime_validation":"UNTESTED","status":f"{pre}_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"}
 (out/f"{pre}_{s['stem']}_REPORT.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); (wr/f"{pre}_{s['stem']}.json").write_text(json.dumps({"run":run,"queue_index":s["index"],"asset":s["stem"],"candidate_sha256":new_sha,"localized_physical_rows":len(ro),"machine_qa":qa,"worker_status":rep["status"],"runtime_validation":"UNTESTED","report":str((out/f"{pre}_{s['stem']}_REPORT.json").relative_to(repo))},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 return {"index":s["index"],"stem":s["stem"],"candidate_sha256":new_sha,"rows":len(ro)}
specs=[
{"index":225,"prefix":"A95","stem":"E3C455FA","file":"E3C455FA_512x256.dds","source_sha":"a0c8c67f88dfdc93385b821452f0175a6a951c238f5f3d8b012afa113ef37fc9","asset_rel":"textures/load/spr_sprani_sumo_fe_cvt_Exst/E3C455FA_512x256.dds","size":[2048,1024],"cap":5000,"segments":9,"rows":[
{"key":"game_lobby","source":"GAME LOBBY","korean":"게임 로비","family":"dark_big","window":[0,0,600,100]},{"key":"game_list","source":"GAME LIST","korean":"게임 목록","family":"dark_big","window":[930,100,1420,230]},{"key":"setup","source":"SETUP","korean":"설정","family":"white_big","window":[940,490,1260,580]},{"key":"course_type","source":"COURSE TYPE","korean":"코스 유형","family":"dark_small","window":[950,690,1320,755]},{"key":"course","source":"COURSE","korean":"코스","family":"dark_small","window":[950,755,1200,810]},{"key":"car_type","source":"CAR TYPE","korean":"차량 유형","family":"dark_small","window":[950,805,1230,860]},{"key":"catch_up","source":"CATCH-UP","korean":"추격 보정","family":"dark_small","window":[950,860,1250,915]},{"key":"collision","source":"COLLISION","korean":"충돌","family":"dark_small","window":[950,915,1250,965]},{"key":"players","source":"PLAYERS","korean":"플레이어","family":"dark_small","window":[950,965,1200,1020]}]},
{"index":227,"prefix":"A96R","stem":"E596B7AC","file":"E596B7AC_512x512.dds","source_sha":"769308121df7229766b50eea1d43c68703e1720df4147ec8f34b735e2a9527f3","asset_rel":"textures/load/spr_sprani_sumo_fe_cvt_Exst/E596B7AC_512x512.dds","size":[2048,2048],"cap":20000,"segments":16,"correction":{"prior_segment_count":14,"corrected_segment_count":16,"added_source_lines":["CAPE WAY","BAY AREA"]},"rows":[
{"key":"intermediate","source":"INTERMEDIATE","korean":"중급","family":"gray_main","window":[0,390,760,505]},{"key":"outrun","source":"OUTRUN","korean":"아웃런","family":"gray_main","window":[0,500,440,600]},{"key":"professional","source":"PROFESSIONAL","korean":"프로","family":"gray_main","window":[0,600,760,695]},{"key":"alpine","source":"ALPINE","korean":"알파인","family":"gray_main","window":[0,690,430,785]},{"key":"ancient_ruins","source":"ANCIENT RUINS","korean":"에인션트 루인스","family":"gray_main","window":[0,785,820,885]},{"key":"cape_way","source":"CAPE WAY","korean":"케이프 웨이","family":"gray_main","window":[0,885,590,980]},{"key":"castle_wall","source":"CASTLE WALL","korean":"캐슬 월","family":"gray_main","window":[0,980,730,1075]},{"key":"cloudy_highland","source":"CLOUDY HIGHLAND","korean":"클라우디 하이랜드","family":"gray_main","window":[0,1075,920,1170]},{"key":"coniferous_forest","source":"CONIFEROUS FOREST","korean":"코니퍼러스 포레스트","family":"gray_main","window":[0,1170,980,1270]},{"key":"deep_lake","source":"DEEP LAKE","korean":"딥 레이크","family":"gray_main","window":[0,1270,620,1360]},{"key":"desert","source":"DESERT","korean":"데저트","family":"gray_main","window":[0,1360,450,1460]},{"key":"bay_area","source":"BAY AREA","korean":"베이 에어리어","family":"gray_main","window":[0,1460,560,1555]},{"key":"flagman1","source":"FLAGMAN 1","korean":"플래그맨 1","family":"red_flag","window":[0,1555,1020,1725]},{"key":"flagman2","source":"FLAGMAN 2","korean":"플래그맨 2","family":"red_flag","window":[0,1720,1020,1890]},{"key":"flagman3","source":"FLAGMAN 3","korean":"플래그맨 3","family":"red_flag","window":[0,1885,1020,2048]},{"key":"novice","source":"NOVICE","korean":"초급","family":"gray_novice","window":[1000,1600,1400,1740]}]}
]
results=[process(specs[1])]
(wr/"A96R_E596B7AC_BATCH.json").write_text(json.dumps({"run":run,"results":results,"status":"WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("A96R_DONE",results)
