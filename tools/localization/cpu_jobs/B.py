#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request,math
from pathlib import Path
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("worker B only")
repo=Path.cwd()
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def alpha_count(a): return sum(a.histogram()[1:])
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

# B78: C151-returned DXT5 REWORK first. Prove whether ordinary exact-bbox block-splice can remove all source effect pixels.
run78="20261005-B-PRODUCTION78-C598-REWORK"
out78=repo/"localization/graphics/role_B"/run78; out78.mkdir(parents=True,exist_ok=True)
w=Path("/tmp/b78"); w.mkdir(exist_ok=True)
d=w/"c598.dds"; a=w/"c598_atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_ranking_cvt_Exst/C598919A_1024x1024.dds",d)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_ranking_cvt_Exst/4x_C598919A_1024x1024_atlas.json",a)
sb=d.read_bytes(); ab=a.read_bytes()
if blob(sb)!="3ab34d5fcd66b5b8cb3d59e02d0d199e2e6b5456": raise RuntimeError(("C598 source drift",blob(sb)))
if blob(ab)!="c2d82b14396fc89ca08affcb8ff9c615d644bc82": raise RuntimeError(("C598 atlas drift",blob(ab)))
im=Image.open(d).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regions={r["idx"]:r for r in json.loads(ab.decode())["regions"]}
stage_ids=list(range(77,87))
stage_names=["Cape Way","Imperial Avenue","Ancient Ruins","Metropolis","Tulip Garden","Skyscrapers","Milky Way","Floral Village","Legend","Giant Statues"]
checks=[]
total_boundary_alpha=0
for idx,name in zip(stage_ids,stage_names):
    x,y,cw,ch=regions[idx]["rect"]
    cell=im.crop((x,y,x+cw,y+ch))
    aa=cell.getchannel("A")
    bb=aa.getbbox()
    if not bb: raise RuntimeError(("empty stage alpha",idx,name))
    gx0,gy0,gx1,gy1=x+bb[0],y+bb[1],x+bb[2],y+bb[3]
    pix=im.getchannel("A").load()
    boundary=0; boundary_blocks=set()
    bx0=(gx0//4)*4; by0=(gy0//4)*4; bx1=((gx1+3)//4)*4; by1=((gy1+3)//4)*4
    for by in range(by0,by1,4):
      for bx in range(bx0,bx1,4):
        fully=(bx>=gx0 and by>=gy0 and bx+4<=gx1 and by+4<=gy1)
        if fully: continue
        n=0
        for yy in range(by,min(by+4,4096)):
          for xx in range(bx,min(bx+4,4096)):
            if gx0<=xx<gx1 and gy0<=yy<gy1 and pix[xx,yy]>0: n+=1
        if n:
          boundary+=n; boundary_blocks.add((bx,by))
    total_boundary_alpha+=boundary
    checks.append({"region_idx":idx,"source":name,"cell":[x,y,cw,ch],"exact_alpha_bbox":[gx0,gy0,gx1,gy1],
      "bbox_mod4":[gx0%4,gy0%4,gx1%4,gy1%4],"source_alpha_pixels":alpha_count(aa),
      "source_alpha_pixels_in_bbox_crossing_blocks":boundary,"bbox_crossing_blocks_with_source_alpha":len(boundary_blocks),
      "ordinary_full_block_splice_exact_safe":"PASS" if boundary==0 else "FAIL"})
hold78={
 "schema_version":1,"role":"B","run":run78,"index":86,
 "asset":"textures/load/spr_sprani_ranking_cvt_Exst/C598919A_1024x1024.dds",
 "reworks":"C151_REWORK_REQUIRED_DXT5_EXACT_MASK_AND_RENDER",
 "source_sha256":sha(sb),"source_blob_sha1":blob(sb),"atlas_blob_sha1":blob(ab),
 "structure":{"dimensions":[4096,4096],"format":"DXT5","raw_orientation":"mirror_y"},
 "stage_boundary_checks":checks,
 "total_source_alpha_pixels_in_bbox_crossing_blocks":total_boundary_alpha,
 "finding":"FAIL_CLOSED_ORDINARY_DXT5_BLOCK_SPLICE_CANNOT_BE_EXACT_DECODED_PIXEL_SAFE" if total_boundary_alpha else "BLOCK_SPLICE_STAGE_BOUNDARIES_SAFE",
 "reason":"At least one mandatory source glyph/effect pixel lies in a 4x4 DXT5 block crossing the exact source bbox. Replacing that whole block can alter decoded pixels outside the permitted exact bbox; retaining it leaves source residue. An endpoint/index-constrained DXT5 solver that preserves every outside decoded pixel is required before safe candidate construction.",
 "candidate_persisted":False,
 "decision":"REWORK_REQUIRED_DXT5_CONSTRAINED_ENDPOINT_INDEX_SOLVER",
 "RUNTIME_VALIDATION":"UNTESTED"
}
(out78/"B78_C598_DXT5_BOUNDARY_BLOCKER.json").write_text(json.dumps(hold78,ensure_ascii=False,indent=2)+"\n")
(wr/"B78_C598_REWORK.json").write_text(json.dumps({"run":run78,"index":86,"decision":hold78["decision"],"boundary_alpha_pixels":total_boundary_alpha,"candidate_persisted":False},indent=2)+"\n")

# B79 preflight for next renderable even shard item 236 FEF70E85.
run79="20261005-B-PRODUCTION79-FEF-PREFLIGHT"
out79=repo/"localization/graphics/role_B"/run79; out79.mkdir(parents=True,exist_ok=True)
w79=Path("/tmp/b79"); w79.mkdir(exist_ok=True)
d2=w79/"fef.dds"; a2=w79/"fef_atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/FEF70E85_512x512.dds",d2)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_FEF70E85_512x512_atlas.json",a2)
sb2=d2.read_bytes(); ab2=a2.read_bytes()
if blob(sb2)!="48fd896aaa8ff2f269b659771f2618ea6a8426d5": raise RuntimeError(("FEF source drift",blob(sb2)))
if blob(ab2)!="750c9f48f00508161f195a1a2515321cbebdab88": raise RuntimeError(("FEF atlas drift",blob(ab2)))
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb2,12)
pf=struct.unpack_from("<8I",sb2,76); masks=(pf[4],pf[5],pf[6])
mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
if not mode or (W,H)!=(2048,2048) or len(sb2)!=128+W*H*4: raise RuntimeError(("FEF structure",W,H,mips,masks,len(sb2)))
raw2=Image.frombytes("RGBA",(W,H),sb2[128:],"raw",mode)
src2=raw2.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regs2=json.loads(ab2.decode())["regions"]
cards=[]; meta=[]
for r in regs2:
    idx=r["idx"]; x,y,cw,ch=r["rect"]; cr=src2.crop((x,y,x+cw,y+ch)); aa=cr.getchannel("A"); bb=aa.getbbox()
    gb=None if not bb else [x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    show=comp(cr)
    sc=max(1,min(3,900//max(1,cw)))
    show=show.resize((cw*sc,ch*sc),Image.Resampling.NEAREST)
    c=Image.new("RGB",(show.width,show.height+34),"white"); c.paste(show,(0,34))
    ImageDraw.Draw(c).text((4,5),f"idx={idx} {r['name']} cell={x},{y},{cw},{ch}",fill="black")
    cards.append(c)
    meta.append({"idx":idx,"name":r["name"],"cell":[x,y,cw,ch],"alpha_bbox":gb,"alpha_pixels":alpha_count(aa)})
cw=max(c.width for c in cards); sheet=Image.new("RGB",(cw,max(1,sum(c.height+6 for c in cards))),"white")
yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+6
sheet.thumbnail((1600,12000),Image.Resampling.LANCZOS)
sheet.save(out79/"B79_FEF_REGION_CONTACT.jpg",quality=96)
src2.save(out79/"B79_FEF_SOURCE_READABLE.png")
raw2.save(out79/"B79_FEF_SOURCE_RAW.png")
pre79={"schema_version":1,"role":"B","run":run79,"index":236,
 "asset":"textures/load/spr_sprani_sumo_fe_cvt_Exst/FEF70E85_512x512.dds",
 "source_sha256":sha(sb2),"source_blob_sha1":blob(sb2),"atlas_blob_sha1":blob(ab2),
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"raw_orientation":"mirror_y"},
 "regions":meta,
 "expected_stage_names":["IMPERIAL AVENUE","JUNGLE","LEGEND","LOST CITY","METROPOLIS","MILKY WAY","NATIONAL PARK","PALM BEACH","SKYSCRAPERS","SNOW MOUNTAIN","SUNNY BEACH","TULIP GARDEN","WATERFALLS","INDUSTRIAL COMPLEX"],
 "status":"B79_CANONICAL_REGION_ORDER_VISUAL_BINDING_REQUIRED_SAME_INVOCATION",
 "RUNTIME_VALIDATION":"UNTESTED"}
(out79/"B79_FEF_PREFLIGHT.json").write_text(json.dumps(pre79,ensure_ascii=False,indent=2)+"\n")
(wr/"B79_FEF_PREFLIGHT.json").write_text(json.dumps({"run":run79,"index":236,"source_sha256":sha(sb2),"region_count":len(meta),"status":pre79["status"]},indent=2)+"\n")
print(json.dumps({"B78_boundary_alpha_pixels":total_boundary_alpha,"B78_decision":hold78["decision"],"B79_regions":len(meta),"B79_source_sha256":sha(sb2)}))
