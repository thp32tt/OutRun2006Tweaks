#!/usr/bin/env python3
"""B325 q214: BC3 source-block material transfer, native vector Korean glyphs.

Unlike B260/B261 SDF categorical recolor, this takes actual original English
metallic material from SHA-pinned DXT5 blocks and reassigns it to a NEW native
Hangul mask (face / beveled edge / warm extrusion), with per-block donor matching.
A controlled trial only; exact persisted BC3 is visually judged before promotion.
"""
import io,os,sys,json,hashlib,struct,urllib.request,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import binary_dilation,gaussian_filter,distance_transform_edt
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
P=G/"role_B/20261009-B325-Q214-SOURCE-BLOCK-METALLIC-TRANSFER"
P.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
srcsha="9a2e428bdb87399a7589338053b49efdcfd103d14f12a33a4bcde7705ab76c6b"
oldsha="ace42cb3d539df7c538c6d93b6c3f001e3d18e4f41aaa29bdab1466fe412fc30"
cleansha="5beb411d1692032d028b747f93083c6b438da1d4ff122f479d3d2f23d08b604b"
rel=Path("textures/load/spr_sprani_sumo_fe_cvt_Exst/BF229CF4_512x512.dds")
current=(G/"hd_candidates"/rel).read_bytes()
assert sha(current)==oldsha, "q214 concurrently changed"
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","214"],capture_output=True,text=True,check=True)
assert json.loads(tri.stdout)["assets"][0]["next_action"]=="METHOD_CHANGE_REQUIRED",tri.stdout
guard=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","214","--require-safe-rerender"],capture_output=True,text=True)
assert guard.returncode==2,("same method retry unexpectedly allowed",guard.returncode)
url=("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"
    "3da79726739ac631d8e2703a65330dbb0c310770/"
    "Release/spr_sprani_sumo_fe_cvt_Exst/BF229CF4_512x512.dds")
with urllib.request.urlopen(url,timeout=120) as f: raw=f.read()
assert sha(raw)==srcsha and raw[:128]==current[:128]
W,H=struct.unpack_from("<II",raw,16)[0],struct.unpack_from("<I",raw,12)[0]
assert (W,H,len(raw),raw[84:88])==(2048,2048,128+2048*2048,b"DXT5")
def dec(buf):
 return np.array(Image.open(io.BytesIO(buf)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8)
S=dec(raw);O=dec(current)
cleanfile=G/"role_B/20261009-B324-Q214-CANONICAL-PLATE-BOUNDARY/B324_CANONICAL_BOUNDARY_CLEAN_PLATE_LOSSLESS.png"
assert sha(cleanfile.read_bytes())==cleansha
C=np.array(Image.open(cleanfile).convert("RGBA"),dtype=np.uint8)
assert S.shape==O.shape==C.shape==(2048,2048,4)
regions=[dict(name="START",text="출발",bbox=(815,495,899,517),size=(57,18),skew=5),
         dict(name="GOAL",text="골",bbox=(1343,764,1417,787),size=(43,18),skew=4)]
allowed=np.zeros((H,W),bool)
for r in regions:
 l,t,rr,b=r["bbox"];allowed[t:b,l:rr]=True
assert not np.any(np.any(S!=C,axis=2)&~allowed)
# Install source-independent Korean outline only. All color/effect data comes
# from the original English's DXT5 blocks, NOT a flat color fill / recolor.
subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
fontinfo=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{family}","Noto Sans CJK KR:style=Black"],text=True).strip().split("|")
fp,fi,fam=fontinfo[0],int(fontinfo[1] or 0),fontinfo[2]
assert "NotoSansCJK" in Path(fp).name and "Noto Sans CJK KR" in fam,(fp,fi,fam)
font=ImageFont.truetype(fp,120,index=fi)
tofu=bytes(font.getmask(chr(0x10ffff)))
for ch in "출발골":
 assert any(bytes(font.getmask(ch))) and bytes(font.getmask(ch))!=tofu,"missing glyph"
kind=np.zeros((H,W),np.uint8)
# EXPLICIT native mask with separately modeled extrusion, bevel and face.
for r in regions:
 w,h=r["size"]
 tmp=Image.new("L",(600,230),0)
 d=ImageDraw.Draw(tmp)
 bb=d.textbbox((0,0),r["text"],font=font)
 d.text((30-bb[0],30-bb[1]),r["text"],font=font,fill=255)
 ink=tmp.getbbox()
 assert ink,("tofu",r["name"])
 # 120px vector glyph is direct font outline oversampling, not previous low-res
 # candidate raster scaling; material and positioning remain native source 2048.
 cov=np.asarray(tmp.crop(ink).resize((w-r["skew"],h),Image.Resampling.LANCZOS),dtype=np.uint8)
 glyph=Image.fromarray(cov,"L").transform((w,h),Image.Transform.AFFINE,
  (1,r["skew"]/max(1,h-1),-r["skew"],0,1,0),resample=Image.Resampling.BICUBIC)
 aa=np.array(glyph,dtype=np.uint8);face=aa>=155
 # Keep counters open; one-pixel warm undercut but no giant SDF pale rim.
 outer=binary_dilation(aa>=60,iterations=1)
 under=np.zeros_like(face);under[1:,:]=outer[:-1,:]
 contour=outer&~face
 # in source's right italic direction: oriented downward/right warm extrusion
 under_right=np.zeros_like(face);under_right[1:,1:]=outer[:-1,:-1]
 tile=np.zeros_like(aa,dtype=np.uint8)
 tile[under|under_right]=1
 tile[contour]=2
 tile[face]=3
 # Real English source family has cream top and gold lower edges; do not turn
 # solid syllable interiors into alternating horizontal strips.
 lh,lw=tile.shape
 ys,xs=np.nonzero(tile)
 assert len(xs)>110,(r["name"],"too few native glyph pixels")
 left,top,right,bottom=int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)
 tile=tile[top:bottom,left:right]
 l,t,rr,b=r["bbox"]
 cx=(l+rr)//2; cy=(t+b)//2
 x=cx-tile.shape[1]//2; y=cy-tile.shape[0]//2
 safe_top=((t+3)//4)*4
 safe_bottom=(b//4)*4
 y=min(y,safe_bottom-tile.shape[0]);y=max(y,max(t+1,safe_top))
 bbox=(x,y,x+tile.shape[1],y+tile.shape[0])
 margins=[x-l,y-t,rr-bbox[2],b-bbox[3]]
 assert min(margins)>=1 and bbox[3]<=safe_bottom,("unsafe glyph source box",r["name"],bbox,margins)
 assert not np.any(kind[y:bbox[3],x:bbox[2]])
 kind[y:bbox[3],x:bbox[2]]=tile
 r["final_bbox"]=list(bbox)
 r["margins"]=margins
 r["core_count"]=int((tile==3).sum())
 r["bevel_count"]=int((tile==2).sum())
assert not np.any((kind>0)&~allowed)
# DDS block color endpoints and indices in RAW vertically mirrored orientation.
def rgb565_decode(n):return np.array([(n>>11&31)*255/31,(n>>5&63)*255/63,(n&31)*255/31])
def pal(block):
 hi=int.from_bytes(block[8:10],"little");lo=int.from_bytes(block[10:12],"little")
 p0=rgb565_decode(hi);p1=rgb565_decode(lo)
 return np.stack([p0,p1,(2*p0+p1)/3,(p0+2*p1)/3])
def bc_indices(block):
 z=int.from_bytes(block[12:16],"little")
 return [(z>>(2*i))&3 for i in range(16)]
def pack_index(block,ind):
 z=sum((int(ind[i])&3)<<(2*i) for i in range(16))
 return block[:12]+z.to_bytes(4,"little")
bw=W//4;bh=H//4
# A donor is a truly encoded *original English* BC3 block with cream-white
# source face plus red badge backing. Select using English material, block
# occupancy and source-row geometry; copy original endpoint colors verbatim.
donors={}
for r in regions:
 l,t,rr,b=r["bbox"];pool=[]
 for fy in range((t+3)//4,b//4):
  by=bh-1-fy
  for bx in range((l+3)//4,rr//4):
   off=128+(by*bw+bx)*16; block=raw[off:off+16]
   pp=pal(block)
   source_patch=S[H-(by+1)*4:H-by*4,bx*4:bx*4+4]
   is_face=(source_patch[:,:,0]>207)&(source_patch[:,:,1]>141)&(source_patch[:,:,2]>82)&(source_patch[:,:,1]>source_patch[:,:,2]-20)
   n=int(is_face.sum())
   warm=int(np.count_nonzero((pp[:,0]>205)&(pp[:,1]>125)&(pp[:,2]>65)))
   has_red=bool(np.any((pp[:,0]>pp[:,1]+46)&(pp[:,0]>pp[:,2]+45)))
   if warm and has_red and 1<=n<=15:
    pool.append((bx,by,n,block,pp))
 assert len(pool)>=5,(r["name"],len(pool))
 donors[r["name"]]=pool
 r["donor_count"]=len(pool)
encoded=bytearray(current)
kindraw=np.flipud(kind)
allowedraw=np.flipud(allowed)
Craw=np.flipud(C)
Sraw=np.flipud(S)
touched=0;donorchoices=[]
for r in regions:
 l,t,rr,b=r["bbox"]
 for by in range(bh-1-(b-1)//4,bh-1-t//4+1):
  yy=by*4
  for bx in range(l//4,(rr+3)//4):
   xx=bx*4
   m=allowedraw[yy:yy+4,xx:xx+4]
   if not np.any(m):continue
   patch=kindraw[yy:yy+4,xx:xx+4]
   if not np.all(m):
    assert not np.any(patch),("glyph entered partial source effect block",r["name"],bx,by)
    continue
   off=128+(by*bw+bx)*16; prior=bytes(encoded[off:off+16])
   if not np.any(patch):
    # preserve original B259 rest of plate; no whole region RGB wash
    continue
   # Use original donor most similar to desired Korean glyph density at same
   # vertical source row, and nearest to adjacent original texture encoding.
   coverage=int(np.count_nonzero(patch==3))
   pool=donors[r["name"]]
   bx0,by0,non,block,pp=min(pool,key=lambda d:(
     abs(d[2]-coverage)*3+abs(d[1]-by)*0.7+abs(d[0]-bx)*0.015,
     abs(d[1]-by),d[0]))
   # Palette is exact source-block original; no manually fabricated cream or
   # red endpoints. Select source native white/gold with warm orange bevel.
   lum=pp[:,0]*.25+pp[:,1]*.55+pp[:,2]*.20
   brightest=int(np.argmax(lum))
   ranked=list(np.argsort(lum))
   brightorder=[int(x) for x in ranked[::-1]]
   # Surface: highest source cream, bevel: second warm, shadow: third dark.
   faceindex=brightorder[0]
   keyindex=brightorder[1]
   extrindex=brightorder[2]
   # Native red badge must stay near original CLEAN plate appearance.
   ind=np.array(bc_indices(prior),dtype=np.uint8).reshape((4,4))
   for ky in range(4):
    for kx in range(4):
     role=int(patch[ky,kx])
     if role:
      ind[ky,kx]=[0,extrindex,keyindex,faceindex][role]
     else:
      bg=Craw[yy+ky,xx+kx,:3].astype(float)
      red_idxs=[int(i) for i,v in enumerate(pp) if v[0]>v[1]+30 and v[0]>v[2]+25]
      if not red_idxs:red_idxs=list(range(4))
      ind[ky,kx]=min(red_idxs,key=lambda i:float(np.sum((pp[i]-bg)**2)))
   output=pack_index(prior[:8]+block[8:12]+prior[12:16],ind.reshape(-1))
   encoded[off:off+16]=output
   touched+=1
   donorchoices.append([r["name"],bx,by,bx0,by0,coverage,non])
assert touched>15,(touched,donors)
dst=bytes(encoded)
D=dec(dst)
outside=int(np.count_nonzero(np.any(D!=S,axis=2)&~allowed))
alphaout=int(np.count_nonzero((D[:,:,3]!=S[:,:,3])&~allowed))
oldoutside=int(np.count_nonzero(np.any(D!=O,axis=2)&~allowed))
assert (outside,alphaout,oldoutside)==(0,0,0),("source/old changed protected",outside,alphaout,oldoutside)
assert dst[:128]==raw[:128]
stats=[]
for r in regions:
 l,t,rr,b=r["bbox"]
 # Make no machine PASS claim for whether chromatic metallic source style
 # survives BC3; controller direct inspect + independent C review are needed.
 roi=D[t:b,l:rr]
 ink=(kind[t:b,l:rr]==3)
 bright=(roi[:,:,0]>200)&(roi[:,:,1]>120)&(roi[:,:,2]>60)
 ratio=float(np.count_nonzero(ink&bright)/max(1,np.count_nonzero(ink)))
 assert ratio>=0.85,(r["name"],"source-donor bright face lost",ratio)
 stats.append(dict(id=r["name"],source_bbox=r["bbox"],new_bbox=r["final_bbox"],
    margins=r["margins"],new_source_native_core=r["core_count"],
    BC3_source_donor_face_bright_retention=round(ratio,5),material_donor_blocks=r["donor_count"]))
# Save trial evidence, no stale candidate can be promoted until controller QA.
trial=P/"B325_UNAPPROVED_SOURCE_BLOCK_METALLIC_TRIAL.dds"
trial.write_bytes(dst)
assert dec(trial.read_bytes()).shape==(H,W,4)
# Save lossless full clean and actual decoded proof, including game RAW.
Image.fromarray(D,"RGBA").save(P/"B325_PERSISTED_DECODE_READABLE.png")
Image.fromarray(np.flipud(D).copy(),"RGBA").save(P/"B325_PERSISTED_DECODE_RAW.png")
def flatten(z,bg):
 canvas=Image.new("RGBA",(z.shape[1],z.shape[0]),(*bg,255))
 canvas.alpha_composite(Image.fromarray(z,"RGBA"))
 return canvas.convert("RGB")
views=[]
for r in regions:
 l,t,rr,b=r["bbox"];xl,yt,xr,yb=l-22,t-12,rr+22,b+12
 for ori in ("FLIPY","RAW"):
  imgs0=[z[yt:yb,xl:xr].copy() for z in (S,C,O,D)]
  if ori=="RAW":imgs0=[np.flipud(x).copy() for x in imgs0]
  for bg_name,bg in (("GRAY",(128,128,128)),("WHITE",(255,255,255)),("BLACK",(0,0,0))):
   for pc in (100,75,50):
    ims=[flatten(x,bg) for x in imgs0]
    if pc!=100:ims=[x.resize((max(1,round(x.width*pc/100)),max(1,round(x.height*pc/100))),Image.Resampling.LANCZOS) for x in ims]
    panel=Image.new("RGB",(sum(x.width for x in ims)+12,max(x.height for x in ims)),bg)
    x=0
    for im in ims:panel.paste(im,(x,0));x+=im.width+4
    fn=f"{r['name']}_{ori}_{bg_name}_{pc}_SOURCE_CLEAN_OLD_B325.png"
    panel.save(P/fn,optimize=True);views.append(fn)
meta=dict(run="B325",role="B",index=214,method="NATIVE_HANGUL_VECTOR_SOURCE_ORIGINAL_DXT5_BLOCK_CHROMATIC_MATERIAL_DONOR_TRANSFER",triage="METHOD_CHANGE_REQUIRED",older_trial_family="B260_B261_FLAT_SDF_PALETTE_REJECTED",source_sha256=srcsha,clean_sha256=cleansha,old_candidate_sha256=oldsha,trial_sha256=sha(dst),native=[W,H],dds_format="BC3/DXT5",mips=1,dds_header="EXACT",raw_mirror_y="EXACT",saved_roundtrip="PASS",outside_canonical_source_rgba=outside,outside_canonical_source_alpha=alphaout,outside_prior_candidate_rgba=oldoutside,source_donor_blocks=touched,glyphs=stats,render_english_source_vs_clean="B324_SOURCE_BOUNDARY_OUTSIDE_ZERO",clean_final_protection="SOURCE_OUTSIDE_ZERO",authored_lossless_contacts=len(views),views=views,output="UNAPPROVED_TRIAL_NOT_PROMOTED",producer_visual="NOT_YET_REVIEWED",fresh_C2="NOT_RUN",C3="NOT_RUN",user_game="UNTESTED",RUNTIME_VALIDATION="UNTESTED",backend="GITHUB_ACTIONS",forbidden_domains_touched=[])
(P/"B325_MACHINE_TRIAL_QA.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n")
print("B325_TRIAL_BUILT",meta["trial_sha256"],"source_donor_blocks",touched,"retention",stats,flush=True)
