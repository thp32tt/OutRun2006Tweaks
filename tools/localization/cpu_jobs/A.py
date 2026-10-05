#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,statistics
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("worker A only")

repo=Path.cwd()
# Retry marker after concurrent worker-output push race.
run="20261006-A-PRODUCTION73-ACF"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/ACF61D7C_1024x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"

commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/a72_acf"); work.mkdir(exist_ok=True)
dds=work/"src.dds"; atlas=work/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/ACF61D7C_1024x512.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_ACF61D7C_1024x512_atlas.json",atlas)
sb=dds.read_bytes(); ab=atlas.read_bytes()

def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b)
    bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

if blob(sb)!="c9417c1b47b1af93d025cdfcdb08bef64de44341": raise RuntimeError(("source drift",blob(sb)))
if blob(ab)!="d41e6e15758c64086e0f6d3e93e6b4add7105951": raise RuntimeError(("atlas drift",blob(ab)))
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
fourcc,bpp,rm,gm,bm,am=pf[2],pf[3],pf[4],pf[5],pf[6],pf[7]
mode="RGBA" if fourcc==0 and bpp==32 and (rm,gm,bm)==(0xff,0xff00,0xff0000) else ("BGRA" if fourcc==0 and bpp==32 and (rm,gm,bm)==(0xff0000,0xff00,0xff) else None)
if not mode or (W,H)!=(4096,2048) or len(sb)!=128+W*H*4:
    raise RuntimeError(("structure",W,H,fourcc,bpp,mode,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regions={r["idx"]:r for r in json.loads(ab.decode())["regions"]}

# Physical binding established by A71 contact-sheet review. Untargeted atlas regions remain pixel-exact.
semantic_segments=[
 ("LOCAL MIXED","로컬 혼합"),("LOCAL MT","로컬 MT"),("LOCAL AT","로컬 AT"),("FRIENDS","친구"),("CANCEL","취소"),
 ("LICENSE DETAILS","라이선스 정보"),("YES","예"),("NO","아니오"),("YOUR POSITION OK","현재 순위 확인"),("REVERSE","반전"),
 ("Exchange OutRun miles for this item?","이 아이템을 OutRun 마일로 교환할까요?"),
 ("Adjust your Game settings","게임 설정 조정"),("View single player and multiplayer rankings","싱글/멀티플레이 랭킹 보기"),
 ("Enjoy the original OutRun2SP","오리지널 OutRun2SP 즐기기"),("OutRun for 1 player!","OutRun 1인 플레이!"),
 ("RANKINGS","랭킹"),("OPTIONS","옵션"),("CONGRATULATIONS!","축하합니다!"),
 ("You got this item","이 아이템을 획득했습니다"),("SORRY! You need more miles!","죄송합니다! 마일이 더 필요합니다!")
]
protected_policy={
  0:"OutRun2SP logo",
  1:"PSP purchase/system message (outside approved transcription scope)",
  6:"Radiation song title",7:"Night Bird song title",
  17:"Tab key/icon",
  18:"ordinal suffix nd",19:"ordinal suffix rd",20:"ordinal suffix st",
  21:"Magical Sound Shower song title",22:"Passing Breeze song title",23:"Life Was A Bore song title",
  24:"Splash Wave song title",25:"Shiny World song title",27:"Night Flight song title",29:"Risky Ride song title",
  30:"Radiation song title duplicate",31:"Night Bird song title duplicate",
  32:"digit 9",33:"digit 6",34:"digit 4",35:"digit 2",36:"digit 0",37:"digit 8",38:"digit 7",39:"digit 5",
  40:"digit 3",41:"digit 1",42:"START artwork",43:"This Item Costs",
  47:"VOICE: ON",49:"NORMAL",50:"orange plate",51:"gray plate",
  52:"TUNED MT",53:"TUNED AT",56:"NORMAL MT",57:"NORMAL AT",58:"NATIONALITY",
  64:"digit 0 small",65:"digit 9 small",66:"digit 8 small",67:"digit 7 small",68:"digit 6 small",69:"digit 4 small",
  70:"digit 3 small",71:"digit 2 small",72:"digit 5 small",73:"digit 1 small",74:"OR artwork"
}

def cell_alpha(idx):
    x,y,w,h=regions[idx]["rect"]
    return bmask(src.crop((x,y,x+w,y+h)).getchannel("A"))

def line_masks(alpha,expected):
    bb=alpha.getbbox()
    if not bb: raise RuntimeError(("empty alpha",expected))
    ys=[]
    for yy in range(bb[1],bb[3]):
        if alpha.crop((bb[0],yy,bb[2],yy+1)).getbbox(): ys.append(yy)
    runs=[]
    if ys:
        s=p=ys[0]
        for y in ys[1:]:
            if y==p+1: p=y
            else: runs.append((s,p+1)); s=p=y
        runs.append((s,p+1))
    if len(runs)!=expected:
        # Merge nearest runs if antialias fragmentation occurs.
        while len(runs)>expected:
            gaps=[(runs[i+1][0]-runs[i][1],i) for i in range(len(runs)-1)]
            _,i=min(gaps)
            runs=runs[:i]+[(runs[i][0],runs[i+1][1])]+runs[i+2:]
    if len(runs)!=expected: raise RuntimeError(("line split",expected,runs,bb))
    out=[]
    for y0,y1 in runs:
        m=Image.new("L",alpha.size,0); m.paste(alpha.crop((0,y0,alpha.width,y1)),(0,y0)); out.append(m)
    return out

def word_groups(mask,expected_words):
    bb=mask.getbbox()
    if not bb: raise RuntimeError(("empty word mask",expected_words))
    cols=[]
    for xx in range(bb[0],bb[2]):
        if mask.crop((xx,bb[1],xx+1,bb[3])).getbbox(): cols.append(xx)
    runs=[]
    s=p=cols[0]
    for x in cols[1:]:
        if x==p+1: p=x
        else: runs.append((s,p+1)); s=p=x
    runs.append((s,p+1))
    # Atlas cells can contain a detached 1-4 px edge strip that is not part of the text.
    # Exclude only such cell-edge strips before word-gap grouping; all interior glyph runs remain eligible.
    runs=[r for r in runs if not ((r[1]-r[0])<=4 and (r[0]<=1 or r[1]>=mask.width-1))]
    if len(runs)<expected_words: raise RuntimeError(("too few runs",expected_words,runs))
    gaps=[(runs[i+1][0]-runs[i][1],i) for i in range(len(runs)-1)]
    cuts=sorted(i for _,i in sorted(gaps,reverse=True)[:expected_words-1])
    groups=[]; start=0
    for cut in cuts+[len(runs)-1]:
        g=runs[start:cut+1]; groups.append((g[0][0],g[-1][1])); start=cut+1
    if len(groups)!=expected_words: raise RuntimeError(("word grouping",expected_words,groups))
    masks=[]
    for x0,x1 in groups:
        m=Image.new("L",mask.size,0); m.paste(mask.crop((x0,0,x1,mask.height)),(x0,0)); masks.append(m)
    return groups,masks,sorted(gaps,reverse=True)

source_mask=Image.new("L",(W,H),0)
allowed=Image.new("L",(W,H),0)
inline_global=Image.new("L",(W,H),0)
rows=[]

def add_row(idx,key,source,korean,local_mask,alignment="left",kind="text",token_mask=None,token_label=None,token_side=None):
    x,y,cw,ch=regions[idx]["rect"]
    bb=local_mask.getbbox()
    if not bb: raise RuntimeError(("row empty",key,idx))
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    gm=Image.new("L",(W,H),0); gm.paste(local_mask,(x,y))
    source_mask.paste(ImageChops.lighter(source_mask.crop((x,y,x+cw,y+ch)),local_mask),(x,y))
    ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
    token_bbox=None
    if token_mask is not None:
        tb=token_mask.getbbox()
        if not tb: raise RuntimeError(("token empty",key))
        token_bbox=[x+tb[0],y+tb[1],x+tb[2],y+tb[3]]
        inline_global.paste(ImageChops.lighter(inline_global.crop((x,y,x+cw,y+ch)),token_mask),(x,y))
        # whole source line is the element size ceiling, including protected inline product token.
        whole=ImageChops.lighter(local_mask,token_mask).getbbox()
        ob=[x+whole[0],y+whole[1],x+whole[2],y+whole[3]]
        ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
    # color median from removable source pixels.
    pix=src.crop((x,y,x+cw,y+ch)); vals=[]
    pp=pix.load()
    for yy in range(ch):
        for xx in range(cw):
            if local_mask.getpixel((xx,yy)):
                r,g,b,a=pp[xx,yy]
                if a>=96: vals.append((r,g,b,a))
    if not vals: raise RuntimeError(("no color samples",key))
    med=[int(round(statistics.median(v[k] for v in vals))) for k in range(4)]
    rows.append({"key":key,"region_idx":idx,"source":source,"korean":korean,"kind":kind,
                 "source_mask":gm,"original_bbox":ob,"source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],
                 "source_median_rgba":med,"alignment":alignment,"preserved_inline_token":token_label,
                 "preserved_inline_token_bbox":token_bbox,"token_side":token_side})

# Messages: exact per-line source masks.
for idx,items in [
    (2,[("sorry_title","SORRY!","죄송합니다!"),("sorry_body","You need more miles!","마일이 더 필요합니다!")]),
    (3,[("congrats_title","CONGRATULATIONS!","축하합니다!"),("congrats_body","You got this item","이 아이템을 획득했습니다")])
]:
    lm=line_masks(cell_alpha(idx),2)
    for m,(key,en,ko) in zip(lm,items): add_row(idx,key,en,ko,m,kind="message")

# Single-region headings.
add_row(4,"options","OPTIONS","옵션",cell_alpha(4),kind="red_heading")
add_row(5,"rankings","RANKINGS","랭킹",cell_alpha(5),kind="red_heading")

# Dark sentence family with product-token preservation where required.
# idx8: OutRun | for | 1 | player!
a8=cell_alpha(8); g8,m8,_=word_groups(a8,4); tok8=m8[0]; rem8=Image.new("L",a8.size,0)
for m in m8[1:]: rem8=ImageChops.lighter(rem8,m)
add_row(8,"out_run_1p","OutRun for 1 player!","1인 플레이!",rem8,kind="dark_sentence",token_mask=tok8,token_label="OutRun",token_side="left")

add_row(9,"view_rankings","View single player and multiplayer rankings","싱글/멀티플레이 랭킹 보기",cell_alpha(9),kind="dark_sentence")

# idx10: Enjoy | the | original | OutRun2SP
a10=cell_alpha(10); g10,m10,_=word_groups(a10,4); tok10=m10[3]; rem10=Image.new("L",a10.size,0)
for m in m10[:3]: rem10=ImageChops.lighter(rem10,m)
add_row(10,"enjoy_original","Enjoy the original OutRun2SP","오리지널 즐기기",rem10,alignment="right",kind="dark_sentence",token_mask=tok10,token_label="OutRun2SP",token_side="right")

add_row(11,"adjust_settings","Adjust your Game settings","게임 설정 조정",cell_alpha(11),kind="dark_sentence")

# idx12 line 1 preserves OutRun in the middle; line 2 is fully replaced.
l12=line_masks(cell_alpha(12),2)
g12,m12,_=word_groups(l12[0],3)
tok12=m12[1]
rem12a=ImageChops.lighter(m12[0],m12[2])
add_row(12,"exchange_line1","Exchange OutRun miles","이 아이템을|마일로",rem12a,kind="dark_sentence_inline_middle",token_mask=tok12,token_label="OutRun",token_side="middle")
add_row(12,"exchange_line2","for this item?","교환할까요?",l12[1],kind="dark_sentence")

# Mid/small UI labels.
add_row(44,"license_details","LICENSE DETAILS","라이선스 정보",cell_alpha(44),kind="mid_ui")
add_row(45,"yes","YES","예",cell_alpha(45),kind="mid_ui")
add_row(46,"no","NO","아니오",cell_alpha(46),kind="mid_ui")
add_row(48,"reverse","REVERSE","반전",cell_alpha(48),alignment="right",kind="small_ui")
add_row(54,"your_position","YOUR POSITION","현재 순위",cell_alpha(54),kind="small_ui")
add_row(55,"ok","OK","확인",cell_alpha(55),kind="small_ui")
add_row(59,"local_mixed","LOCAL MIXED","로컬 혼합",cell_alpha(59),kind="small_ui")
add_row(60,"local_mt","LOCAL MT","로컬 MT",cell_alpha(60),kind="small_ui")
add_row(61,"local_at","LOCAL AT","로컬 AT",cell_alpha(61),kind="small_ui")
add_row(62,"friends","FRIENDS","친구",cell_alpha(62),kind="small_ui")
add_row(63,"cancel","CANCEL","취소",cell_alpha(63),kind="small_ui")

if len(rows)!=23: raise RuntimeError(("physical row count",len(rows)))

# Clean plate is exact transparent removal of approved source glyph pixels only.
clean=src.copy()
ca=clean.getchannel("A"); ca.paste(0,(0,0,W,H),source_mask); clean.putalpha(ca)
sp=out/"A73_ACF_SOURCE_READABLE.png"; cp=out/"A73_ACF_CLEAN_PLATE.png"
smp=out/"A73_ACF_SOURCE_TEXT_MASK.png"; ap=out/"A73_ACF_ALLOWED_BBOX_MASK.png"
src.save(sp); clean.save(cp); source_mask.save(smp); allowed.save(ap)
source_visible=bmask(src.getchannel("A"))
protected=ImageChops.multiply(source_visible,ImageOps.invert(source_mask))
protected=ImageChops.lighter(protected,inline_global)
pp=out/"A73_ACF_PROTECTED_VISIBLE_MASK.png"; protected.save(pp)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(smp),"--protected-mask",str(pp),"--report",str(out/"A73_ACF_CLEAN_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"A73_ACF_CLEAN_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean validator",cleanrep))

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
font_line=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Black"],text=True).strip()
FONT,FI,FSTYLE=font_line.rsplit("|",2); FI=int(FI or 0)

def render_low(text,fs,fill):
    f=ImageFont.truetype(FONT,fs,index=FI)
    dr=ImageDraw.Draw(Image.new("L",(8,8),0))
    bb=dr.textbbox((0,0),text,font=f)
    a=Image.new("L",(max(8,bb[2]-bb[0]+4),max(8,bb[3]-bb[1]+4)),0)
    ImageDraw.Draw(a).text((2-bb[0],2-bb[1]),text,font=f,fill=255)
    ab=a.getbbox()
    if not ab: raise RuntimeError(("render empty",text,fs))
    a=a.crop(ab)
    rgba=Image.new("RGBA",a.size,(fill[0],fill[1],fill[2],255)); rgba.putalpha(a)
    return rgba.resize((rgba.width*4,rgba.height*4),Image.Resampling.NEAREST)

# Shared-size families preserve source-intentional consistency.
family_members={
 "message":["sorry_title","sorry_body","congrats_title","congrats_body"],
 "red_heading":["options","rankings"],
 "dark_sentence":["out_run_1p","view_rankings","enjoy_original","adjust_settings","exchange_line1","exchange_line2"],
 "license_ui":["license_details"],
 "yesno_ui":["yes","no"],
 "reverse_ui":["reverse"],
 "position_ui":["your_position","ok"],
 "local_ui":["local_mixed","local_mt","local_at","friends","cancel"]
}
bykey={r["key"]:r for r in rows}

def fits_row(r,fs):
    ob=r["original_bbox"]; aw=r["source_width"]; ah=r["source_height"]; fill=r["source_median_rgba"]
    if r["kind"]=="dark_sentence_inline_middle":
        left_text,right_text=r["korean"].split("|")
        a=render_low(left_text,fs,fill); b=render_low(right_text,fs,fill); tb=r["preserved_inline_token_bbox"]
        return a.height<=ah-8 and b.height<=ah-8 and a.width<=max(1,tb[0]-ob[0]-12) and b.width<=max(1,ob[2]-tb[2]-12)
    lay=render_low(r["korean"],fs,fill)
    if lay.height>ah-8: return False
    if r["preserved_inline_token_bbox"]:
        tb=r["preserved_inline_token_bbox"]
        if r["token_side"]=="left": return lay.width<=max(1,ob[2]-tb[2]-12)
        if r["token_side"]=="right": return lay.width<=max(1,tb[0]-ob[0]-12)
    return lay.width<=aw-8

family_fs={}
for fam,keys in family_members.items():
    chosen=None
    for fs in range(36,2,-1):
        if all(fits_row(bykey[k],fs) for k in keys):
            chosen=fs; break
    if chosen is None: raise RuntimeError(("family fit",fam))
    family_fs[fam]=chosen

final=clean.copy()
target_union=Image.new("L",(W,H),0)
target_rows=[]
outrows=[]
for r in rows:
    fam=("message" if r["kind"]=="message" else "red_heading" if r["kind"]=="red_heading" else "dark_sentence" if r["kind"].startswith("dark_sentence") else "license_ui" if r["key"]=="license_details" else "yesno_ui" if r["key"] in ("yes","no") else "reverse_ui" if r["key"]=="reverse" else "position_ui" if r["key"] in ("your_position","ok") else "local_ui")
    fs=family_fs[fam]; ob=r["original_bbox"]; ah=r["source_height"]; fill=r["source_median_rgba"]
    rowmask=Image.new("L",(W,H),0)
    placements=[]
    if r["kind"]=="dark_sentence_inline_middle":
        left_text,right_text=r["korean"].split("|"); tb=r["preserved_inline_token_bbox"]
        la=render_low(left_text,fs,fill); rb=render_low(right_text,fs,fill)
        py=ob[1]+(ah-max(la.height,rb.height))//2
        lx=tb[0]-8-la.width; rx=tb[2]+8
        if lx<=ob[0] or rx+rb.width>=ob[2]: raise RuntimeError(("inline middle placement",r["key"],ob,tb,la.size,rb.size))
        final.alpha_composite(la,(lx,py+(max(la.height,rb.height)-la.height)//2))
        final.alpha_composite(rb,(rx,py+(max(la.height,rb.height)-rb.height)//2))
        rowmask.paste(bmask(la.getchannel("A")),(lx,py+(max(la.height,rb.height)-la.height)//2))
        tmp=Image.new("L",(W,H),0); tmp.paste(bmask(rb.getchannel("A")),(rx,py+(max(la.height,rb.height)-rb.height)//2))
        rowmask=ImageChops.lighter(rowmask,tmp)
        placements=[{"text":left_text,"x":lx},{"text":right_text,"x":rx}]
    else:
        lay=render_low(r["korean"],fs,fill)
        py=ob[1]+(ah-lay.height)//2
        if r["preserved_inline_token_bbox"]:
            tb=r["preserved_inline_token_bbox"]
            if r["token_side"]=="left": px=tb[2]+8
            elif r["token_side"]=="right": px=tb[0]-8-lay.width
            else: raise RuntimeError(("token side",r["key"]))
        elif r["alignment"]=="right":
            px=ob[2]-4-lay.width
        else:
            px=ob[0]+4
        if px<=ob[0] or py<=ob[1] or px+lay.width>=ob[2] or py+lay.height>=ob[3]:
            raise RuntimeError(("placement",r["key"],ob,[px,py,px+lay.width,py+lay.height],fs))
        final.alpha_composite(lay,(px,py))
        rowmask.paste(bmask(lay.getchannel("A")),(px,py))
        placements=[{"text":r["korean"],"x":px}]
    lb=rowmask.getbbox()
    if not lb: raise RuntimeError(("localized empty",r["key"]))
    lb=list(lb)
    if not (lb[0]>=ob[0] and lb[1]>=ob[1] and lb[2]<=ob[2] and lb[3]<=ob[3]): raise RuntimeError(("containment",r["key"],ob,lb))
    if lb[2]-lb[0]>r["source_width"] or lb[3]-lb[1]>r["source_height"]: raise RuntimeError(("size ceiling",r["key"],ob,lb))
    if not (lb[0]>ob[0] and lb[1]>ob[1] and lb[2]<ob[2] and lb[3]<ob[3]): raise RuntimeError(("positive margin",r["key"],ob,lb))
    target_rows.append((r["key"],rowmask))
    target_union=ImageChops.lighter(target_union,rowmask)
    outrows.append({k:v for k,v in r.items() if k!="source_mask"} | {
      "localized_bbox":lb,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
      "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","lowres_font_size":fs,"pixel_scale":4,
      "horizontal_scale":1.0,"tracking_px_average":0.0,"font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,
      "fill_rgba":[fill[0],fill[1],fill[2],255],"placements":placements
    })

# Pairwise zero-overlap and positive separation.
overlap=0; touch=[]
for i in range(len(target_rows)):
    for j in range(i+1,len(target_rows)):
        a=target_rows[i][1]; b=target_rows[j][1]
        x=count(ImageChops.multiply(a,b))
        near=count(ImageChops.multiply(a.filter(ImageFilter.MaxFilter(3)),b))
        overlap+=x
        if x or near: touch.append([target_rows[i][0],target_rows[j][0],x,near])
if overlap or touch: raise RuntimeError(("localized overlap/touch",overlap,touch))
target_protected_overlap=count(ImageChops.multiply(target_union,protected))
target_protected_near=count(ImageChops.multiply(target_union.filter(ImageFilter.MaxFilter(3)),protected))
if target_protected_overlap or target_protected_near:
    raise RuntimeError(("target protected conflict",target_protected_overlap,target_protected_near))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",mode)
candidate.write_bytes(payload)
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip")
fp=out/"A73_ACF_FINAL_DECODED_READABLE.png"; dec.save(fp)
target_union.save(out/"A73_ACF_TARGET_TEXT_MASK.png")
subprocess.run(["python3",str(validator),str(sp),str(fp),str(ap),"--protected-mask",str(pp),"--report",str(out/"A73_ACF_FINAL_VALIDATION.json")],check=True)
finalrep=json.loads((out/"A73_ACF_FINAL_VALIDATION.json").read_text())

diff=dmask(src,dec)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alphaout=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(diff,protected))
render_outside=count(ImageChops.multiply(target_union,ImageOps.invert(allowed)))
# Candidate must equal CLEAN everywhere outside the Korean target mask.
clean_final_diff=dmask(clean,dec)
candidate_vs_clean_outside_target=count(ImageChops.multiply(clean_final_diff,ImageOps.invert(target_union)))
# All source-target pixels were cleared before Korean render; preserved source pixels are protected and exact.
preserved_changes=prot
if finalrep["status"]!="PASS" or outside or alphaout or prot or render_outside or candidate_vs_clean_outside_target or overlap or touch or target_protected_overlap or target_protected_near:
    raise RuntimeError(("gates",finalrep["status"],outside,alphaout,prot,render_outside,candidate_vs_clean_outside_target,overlap,touch,target_protected_overlap,target_protected_near))

# Explicit product-token preservation checks.
tokens=[]
for label,tmask in [("OutRun idx8",tok8),("OutRun2SP idx10",tok10),("OutRun idx12",tok12)]:
    idx=8 if "idx8" in label else 10 if "idx10" in label else 12
    x,y,cw,ch=regions[idx]["rect"]
    dd=dmask(src.crop((x,y,x+cw,y+ch)),dec.crop((x,y,x+cw,y+ch)))
    changed=count(ImageChops.multiply(dd,tmask))
    if changed: raise RuntimeError(("token changed",label,changed))
    tokens.append({"label":label,"changed_pixels":changed})

# Visual evidence.
cards=[]
for r in outrows:
    ob=r["original_bbox"]; cr=(max(0,ob[0]-16),max(0,ob[1]-16),min(W,ob[2]+16),min(H,ob[3]+16))
    ims=[comp(z).crop(cr) for z in (src,clean,dec)]
    sc=max(1,min(3,1350//max(1,ims[0].width)))
    ims=[z.resize((z.width*sc,z.height*sc),Image.Resampling.NEAREST) for z in ims]
    c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+34),"white")
    xx=0
    for z in ims: c.paste(z,(xx,34)); xx+=z.width+6
    ImageDraw.Draw(c).text((5,5),f'{r["key"]} idx={r["region_idx"]} {r["source"]} -> {r["korean"]} fs={r["lowres_font_size"]} token={r["preserved_inline_token"]}',fill="black")
    cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+4*(len(cards)-1)),"white")
yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.thumbnail((1900,16000),Image.Resampling.LANCZOS)
sheet.save(out/"A73_ACF_TARGET_CONTACTS.jpg",quality=97)

full=Image.new("RGB",(1024,3*280),"white")
for i,(label,im) in enumerate([("SOURCE",src),("CLEAN",clean),("FINAL",dec)]):
    z=comp(im).resize((1024,512),Image.Resampling.NEAREST)
    z=z.resize((1024,256),Image.Resampling.LANCZOS)
    full.paste(z,(0,i*280+24)); ImageDraw.Draw(full).text((4,i*280+4),label,fill="black")
full.save(out/"A73_ACF_SOURCE_CLEAN_FINAL.jpg",quality=96)

rr=Image.new("RGB",(1024,2*280),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec)]):
    z=comp(im).resize((1024,256),Image.Resampling.LANCZOS)
    rr.paste(z,(0,i*280+24)); ImageDraw.Draw(rr).text((4,i*280+4),label,fill="black")
rr.save(out/"A73_ACF_RAW_COMPARE.jpg",quality=96)

report={
 "schema_version":1,"role":"A","run":run,"index":205,"asset":asset,
 "readiness_tier":"A71_PREFLIGHT_RESOLVED_TO_RENDER_READY_COMPLETED_SAME_INVOCATION_A73_TOKEN_EDGE_FIX",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":commit,"git_blob_sha1":blob(sb),"atlas_git_blob_sha1":blob(ab),"source_sha256":sha(sb)},
 "semantic_binding":{"transcription_segments":len(semantic_segments),"localized_physical_rows":len(outrows),
   "protected_policy_regions":protected_policy,
   "inline_product_tokens":["OutRun idx8","OutRun2SP idx10","OutRun idx12"],
   "notes":["A71 controller contact review mapped the approved transcription to atlas regions 2,3,4,5,8,9,10,11,12,44,45,46,48,54,55,59,60,61,62,63.",
            "YOUR POSITION OK spans atlas regions 54+55; SORRY and Exchange are two-line physical rows; CONGRATULATIONS/You got this item are separate source lines in region 3.",
            "Song titles/music credits, OutRun2SP logo, product tokens and all unapproved atlas labels remain exact original pixels."]},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "font":{"file":Path(FONT).name,"face_index":FI,"style":FSTYLE,"family_sizes_lowres":family_fs,"pixel_scale":4,"horizontal_scale":1.0,"artificial_tracking_px":0.0},
 "rows":outrows,
 "clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "decoded_changes":{"changed_pixels_total":count(diff),"outside":outside,"alpha_outside":alphaout,"protected_changed":prot,
   "render_outside_target":render_outside,"candidate_vs_clean_outside_korean_target":candidate_vs_clean_outside_target,
   "localized_overlap":overlap,"localized_touch_pairs":touch,"target_protected_overlap":target_protected_overlap,"target_protected_1px_near":target_protected_near},
 "preserved_product_tokens":tokens,
 "candidate_sha256":sha(payload),"candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","runtime_validation":"UNTESTED",
 "status":"A73_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
}
(out/"A73_ACF61D7C_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A73_ACF61D7C.json").write_text(json.dumps({
 "run":run,"index":205,"asset":"ACF61D7C","source_sha256":sha(sb),"candidate_sha256":sha(payload),
 "semantic_segments":len(semantic_segments),"localized_physical_rows":len(outrows),
 "bbox_size_positive_margin":f"{len(outrows)}/{len(outrows)} PASS","clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],
 "outside":outside,"alpha_outside":alphaout,"protected_changed":prot,"render_outside_target":render_outside,
 "candidate_vs_clean_outside_target":candidate_vs_clean_outside_target,"overlap":overlap,"touch_pairs":len(touch),
 "target_protected_overlap":target_protected_overlap,"target_protected_1px_near":target_protected_near,
 "worker_status":report["status"],"runtime_validation":"UNTESTED","report":f"localization/graphics/role_A/{run}/A73_ACF61D7C_REPORT.json"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":run,"index":205,"asset":"ACF61D7C","candidate_sha256":sha(payload),"semantic":len(semantic_segments),"physical":len(outrows),"status":report["status"]},ensure_ascii=False))
