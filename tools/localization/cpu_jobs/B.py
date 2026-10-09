#!/usr/bin/env python3
"""B339 q214: HAND-DRAWN separated Hangul jamo source-badge BC3 glyphs.

Manual multi-jamo stroke paths replace the resampled-font B325/B326 mask. Original English
metallic material from SHA-pinned DXT5 blocks and reassigns it to a NEW native
Hangul mask (face / beveled edge / warm extrusion), with per-block donor matching.
B339 additionally REBUILDS BC3 ALPHA endpoint/index for the NEW jamo strokes; B338 recycled older alpha masks. A controlled trial only; exact persisted BC3 must visually pass before promotion.
"""
import io,os,sys,json,hashlib,struct,urllib.request,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import binary_dilation,gaussian_filter,distance_transform_edt
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
P=G/"role_B/20261010-B339-Q214-BC3-ALPHA-TOPOLOGY-PILOT"
P.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
srcsha="9a2e428bdb87399a7589338053b49efdcfd103d14f12a33a4bcde7705ab76c6b"
oldsha="ace42cb3d539df7c538c6d93b6c3f001e3d18e4f41aaa29bdab1466fe412fc30"
cleansha="5beb411d1692032d028b747f93083c6b438da1d4ff122f479d3d2f23d08b604b"
rel=Path("textures/load/spr_sprani_sumo_fe_cvt_Exst/BF229CF4_512x512.dds")
current=(G/"hd_candidates"/rel).read_bytes()
assert sha(current)==oldsha, "q214 concurrently changed"
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","214"],capture_output=True,text=True,check=True)
triage_state=json.loads(tri.stdout)["assets"][0]
assert triage_state["index"]==214 and triage_state["next_action"] in ("METHOD_CHANGE_REQUIRED","NORMAL_QUEUE_SELECTION"),tri.stdout
# The current queue label is a direct B338 producer FAIL but lacks the
# exact magic string rework_triage expects. Bind original C rejection and
# new independent production bytes rather than silently trusting the label.
latest_report=G/"role_B/20261010-B338-Q214-MANUAL-JAMO-VECTOR-PILOT/B338_CONTROLLER_VISUAL_REJECT.json"
prior=json.loads(latest_report.read_text())
assert prior["queue_index"]==214 and prior["decision"]=="REWORK_REQUIRED_UNAPPROVED_TRIAL"
assert prior["source_sha256"]==srcsha and prior["unchanged_current_candidate_sha256"]==oldsha
assert prior["new_trial_sha256"]=="b7c0dd8b9f8c4e62cb3b9e2fce88c3d44eb7c2e43d8dae9c3f7bfef84690facd"
guard=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","214","--require-safe-rerender"],capture_output=True,text=True)
assert guard.returncode in (0,2),(guard.returncode,guard.stderr)
if guard.returncode==0:
 assert triage_state["next_action"]=="NORMAL_QUEUE_SELECTION" and prior["producer_visual"]["result"]=="FAIL_OVERRIDE_MECHANICAL_PASS"
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
regions=[dict(name="START",text="출발",bbox=(815,495,899,517),size=(60,19),skew=6),
         dict(name="GOAL",text="골",bbox=(1343,764,1417,787),size=(51,19),skew=6)]
allowed=np.zeros((H,W),bool)
for r in regions:
 l,t,rr,b=r["bbox"];allowed[t:b,l:rr]=True
assert not np.any(np.any(S!=C,axis=2)&~allowed)
# NEW FAMILY METHOD: draw each Hangul jamo manually as vector polylines
# instead of resampling a font raster, shrinking an older Hangul candidate,
# or tuning B325/B326 block-colour/size/shear filters. Every line segment
# is authored at 5x native subpixel resolution and sampled once.
# The 3D material uses source BC3 ORIGINAL palette, but the local topology is
# hand-constructed and separated by open counters.
K=5
GLYPHS={
"출":[([(3,3),(19,3)],1.9), ([(11,2),(11,5)],1.7),
      ([(11,6),(3,9)],2.2), ([(11,6),(19,9)],2.2),
      ([(2,11),(20,11)],2.0), ([(11,11),(11,13)],1.8),
      ([(4,14),(18,14),(18,16),(4,16),(4,18),(19,18)],2.0)],
"발":[ ([(3,3),(3,9),(13,9),(13,3)],2.1), ([(4,6),(13,6)],1.8),
       ([(18,2),(18,12)],2.0), ([(18,6),(22,6)],1.8),
       ([(4,13),(19,13),(19,15.5),(4,15.5),(4,18),(19,18)],2.0)],
"골":[ ([(3,3),(20,3),(20,9)],2.6), ([(11.5,8),(11.5,12)],2.3),
       ([(2,12),(22,12)],2.4),
       ([(4,15),(19,15),(19,17),(4,17),(4,19),(20,19)],2.4)]
}
GLYPH_TILES={}
for char, strokes in GLYPHS.items():
 im=Image.new("L",(24*K,22*K),0); dr=ImageDraw.Draw(im)
 for pts,rad in strokes:
  points=[(round(x*K),round(y*K)) for x,y in pts]
  dr.line(points,fill=255,width=round(rad*K),joint="curve")
  # Explicit rounded terminals reproduce the source sign's rounded,
  # full-weight corners, avoiding split bars on native BC3 decoding.
  rr=round(rad*K/2)
  for px,py in (points[0],points[-1]):
   dr.ellipse((px-rr,py-rr,px+rr,py+rr),fill=255)
 GLYPH_TILES[char]=im.crop((0,0,24*K,21*K))
# Native cap height is source 22/23px, with at least 1px top/bottom
# margin. Hand vector glyphs remain full source-native 19px high.
kind=np.zeros((H,W),np.uint8)
for r in regions:
 if r["name"]=="START":
  pieces=[GLYPH_TILES["출"].resize((28,19),Image.Resampling.LANCZOS),
          GLYPH_TILES["발"].resize((28,19),Image.Resampling.LANCZOS)]
  tile_img=Image.new("L",(64,19),0)
  tile_img.paste(pieces[0],(0,0));tile_img.paste(pieces[1],(36,0))
 else:
  tile_img=GLYPH_TILES["골"].resize((40,19),Image.Resampling.LANCZOS)
  # A one-glyph translation is visibly shorter than the source "GOAL".
  # Any added chrome extension must be separate protected decoration;
  # never invent extra letters or stretch past the source bounds.
 # Shape-preserving direct native italic shift, with x displacement anchored
 # to top and bottom boundaries. No blanket affine fitting of old glyphs.
 aa=np.asarray(tile_img,dtype=np.uint8)
 skew=3
 direct=np.zeros_like(aa)
 for yi in range(aa.shape[0]):
  dx=int(round(skew*(1.0-yi/max(1,aa.shape[0]-1))))
  if dx:direct[yi,dx:]=aa[yi,:-dx]
  else:direct[yi]=aa[yi]
 aa=direct
 face=aa>=130
 from scipy.ndimage import binary_dilation
 # Expose multiple independent jamo strokes with clear counters instead
 # of creating a horizontal solid plate or resized bitmap.
 outer=binary_dilation(aa>=85,iterations=1)
 under=np.zeros_like(face);under[1:,:]=outer[:-1,:]
 under_right=np.zeros_like(face);under_right[1:,1:]=outer[:-1,:-1]
 contour=outer&~face
 tile=np.zeros_like(aa,dtype=np.uint8)
 tile[under|under_right]=1;tile[contour]=2;tile[face]=3
 yx=np.nonzero(tile)
 if not yx[0].size:raise RuntimeError("manual Hangul disappeared")
 ys,xs=yx
 left,top,right,bottom=int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)
 tile=tile[top:bottom,left:right]
 l,t,rr,b=r["bbox"]
 # DXT5 block guard from B324/C289: source-effect bbox remains
 # surrounded by 1+ px and non-4px-complete clipped source blocks untouched.
 cx=(l+rr)//2;cy=(t+b)//2
 xx=cx-tile.shape[1]//2; yy=cy-tile.shape[0]//2
 safe_top=((t+3)//4)*4;safe_bottom=(b//4)*4
 yy=min(yy,safe_bottom-tile.shape[0]);yy=max(yy,max(t+1,safe_top))
 bb=(xx,yy,xx+tile.shape[1],yy+tile.shape[0])
 margins=[xx-l,yy-t,rr-bb[2],b-bb[3]]
 assert min(margins)>=1 and bb[3]<=safe_bottom,(r["name"],bb,margins)
 assert not np.any(kind[yy:bb[3],xx:bb[2]])
 kind[yy:bb[3],xx:bb[2]]=tile
 r["final_bbox"]=list(bb);r["margins"]=margins
 r["core_count"]=int((tile==3).sum())
 r["bevel_count"]=int((tile==2).sum())
 r["manual_glyph_strokes"]={ch:len(GLYPHS[ch]) for ch in r["text"]}
 assert r["core_count"]>110,(r["name"],r["core_count"])
assert not np.any((kind>0)&~allowed)
# Unretouched Hungarian family artwork across these signs must be identical.
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
# DXT5/BC3 alpha block: two endpoints plus sixteen 3-bit indices.
# B338 only wrote COLOR indices and copied old B259 alpha bytes, letting old
# Hangul geometry punch holes through freshly handwritten vertical strokes.
# B339 creates an independent alpha topology for every changed 4x4 block.
def encode_bc3_alpha(a):
 a=np.asarray(a,dtype=np.uint8)
 assert a.shape==(4,4)
 # Use a0>a1 so the 8 levels are 255,0,219,182,146,109,73,36.
 levels=np.array([255,0,219,182,146,109,73,36],dtype=np.int16)
 dist=np.abs(a.reshape(-1,1).astype(np.int16)-levels[None,:])
 inds=np.argmin(dist,axis=1)
 bits=sum(int(inds[i])<<(3*i) for i in range(16))
 return bytes((255,0))+bits.to_bytes(6,"little")
def decode_bc3_alpha(block):
 assert len(block)==16
 a0,a1=block[0],block[1]
 assert a0>a1,"selected alpha palette must be eight levels"
 vals=np.array([a0,a1]+[((7-k)*a0+k*a1)//7 for k in range(1,7)],dtype=np.int16)
 bits=int.from_bytes(block[2:8],"little")
 return np.array([vals[(bits>>(3*i))&7] for i in range(16)],dtype=np.uint8).reshape(4,4)
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
   keyindex=brightorder[2]
   extrindex=brightorder[3]
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
   # The glyph and CLEAN plate now own alpha; old candidate alpha must NOT
   # survive inside a changed BC3 block. Face opacity matters especially for
   # GOAL's 1-2px vertical stroke/counter under compression.
   alpha=Craw[yy:yy+4,xx:xx+4,3].copy()
   alpha[patch==1]=np.maximum(alpha[patch==1],np.uint8(200))
   alpha[patch==2]=np.maximum(alpha[patch==2],np.uint8(230))
   alpha[patch==3]=255
   ablock=encode_bc3_alpha(alpha)
   assert np.count_nonzero(decode_bc3_alpha(ablock)[patch==3]<246)==0
   output=pack_index(ablock+block[8:12]+prior[12:16],ind.reshape(-1))
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
# New B339 saved-DDS checks: the exact decoded alpha must cover nearly
# all hand-authored glyph-core pixels; B338 never enforced this condition.
alpha_core_coverage={}
for r in regions:
 l,t,rr,b=r["bbox"]
 mask=(kind[t:b,l:rr]==3)
 assert int(mask.sum())>110
 observed=D[t:b,l:rr,3]
 coverage=float(np.mean(observed[mask]>=246))
 alpha_core_coverage[r["name"]]=round(coverage,6)
 assert coverage>=0.98,(r["name"],"persisted glyph alpha lost",coverage)
# The non-text region must remain bit-exact as before. Separate diagnostics
# do not imply font/style producer PASS.
# Save trial evidence, no stale candidate can be promoted until controller QA.
trial=P/"B339_UNAPPROVED_MANUAL_JAMO_CHROME_TRIAL.dds"
trial.write_bytes(dst)
assert dec(trial.read_bytes()).shape==(H,W,4)
# Save lossless full clean and actual decoded proof, including game RAW.
Image.fromarray(D,"RGBA").save(P/"B339_PERSISTED_DECODE_READABLE.png")
Image.fromarray(np.flipud(D).copy(),"RGBA").save(P/"B339_PERSISTED_DECODE_RAW.png")
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
    fn=f"{r['name']}_{ori}_{bg_name}_{pc}_SOURCE_CLEAN_OLD_B339.png"
    panel.save(P/fn,optimize=True);views.append(fn)
meta=dict(run="B339",role="B",index=214,method="HAND_DRAWN_JAMO_STROKE_VECTOR_SOURCE_ORIGINAL_DXT5_PALETTE",triage="METHOD_CHANGE_REQUIRED",older_trial_family="B260_B261_FLAT_SDF_PALETTE_REJECTED",source_sha256=srcsha,clean_sha256=cleansha,old_candidate_sha256=oldsha,trial_sha256=sha(dst),manual_vector_paths={k:[{"path":z[0],"stroke":z[1]} for z in v] for k,v in GLYPHS.items()},native=[W,H],dds_format="BC3/DXT5",mips=1,dds_header="EXACT",raw_mirror_y="EXACT",saved_roundtrip="PASS",outside_canonical_source_rgba=outside,outside_canonical_source_alpha=alphaout,outside_prior_candidate_rgba=oldoutside,source_donor_blocks=touched,glyphs=stats,decoded_alpha_core_coverage=alpha_core_coverage,bc3_alpha_method="REBUILT_255_0_EIGHT_LEVEL_3BIT_GLREMOVED_PRIOR_MASK",render_english_source_vs_clean="B324_SOURCE_BOUNDARY_OUTSIDE_ZERO",clean_final_protection="SOURCE_OUTSIDE_ZERO",authored_lossless_contacts=len(views),views=views,output="UNAPPROVED_TRIAL_NOT_PROMOTED",producer_visual="NOT_YET_REVIEWED",fresh_C2="NOT_RUN",C3="NOT_RUN",user_game="UNTESTED",RUNTIME_VALIDATION="UNTESTED",backend="GITHUB_ACTIONS",forbidden_domains_touched=[])
(P/"B339_MACHINE_TRIAL_QA.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n")
print("B339_TRIAL_BUILT",meta["trial_sha256"],"source_donor_blocks",touched,"retention",stats,flush=True)
