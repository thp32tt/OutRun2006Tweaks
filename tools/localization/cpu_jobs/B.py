#!/usr/bin/env python3
# B255 actual q172 native DDS repair; C281 source-right-italic C-return.
import os,json,hashlib,struct,tempfile,urllib.request,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageFilter
if os.getenv("OUTRUN_CPU_WORKER")!="github-actions" or os.getenv("OUTRUN_CPU_ROLE")!="B":raise SystemExit("worker B only")
repo=Path.cwd();run="20261008-B255-Q172-EXPLICIT-KOREAN-FONT-SHEAR"
out=repo/"localization/graphics/role_B"/run;out.mkdir(parents=True,exist_ok=True)
file=repo/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/6C9B3611_256x256.dds"
platefile=repo/"localization/graphics/role_B/20261006-B-PRODUCTION191-6C9B3611-START-GOAL/B191_CLEAN_PLATE.png"
SOURCE="d5f4a36d5ef1285555ca8fc045e54d160876d1b3e33c6fbc45668c24566c2cf8"
PRIOR="26381bbba897a303934908a6057d5a7a04ae7e8ff16eee2cdb77780ca43a2110"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/6C9B3611_256x256.dds"
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if sha(file)!=PRIOR:raise RuntimeError(("concurrent DDS changed",sha(file),PRIOR))
with tempfile.TemporaryDirectory(prefix="b254_") as td:
    src=Path(td)/"source.dds";urllib.request.urlretrieve(url,src)
    if sha(src)!=SOURCE:raise RuntimeError("canonical source identity mismatch")
    a=src.read_bytes();b=file.read_bytes()
    if a[:128]!=b[:128]:raise RuntimeError("DDS header drift")
    h,w=struct.unpack_from("<II",a,12)
    masks=struct.unpack_from("<IIII",a,92)
    mode="RGBA" if masks==(0xff,0xff00,0xff0000,0xff000000) else "BGRA" if masks==(0xff0000,0xff00,0xff,0xff000000) else None
    if (w,h)!=(1024,1024) or mode is None or struct.unpack_from("<I",a,28)[0]!=1 or len(a)!=128+4*w*h:raise RuntimeError(("source format drift",w,h,mode))
    def decode(bb):return Image.frombytes("RGBA",(w,h),bb[128:],"raw",mode).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    source=decode(a);previous=decode(b);legacy=Image.open(platefile).convert("RGBA")
    if legacy.size!=(w,h):raise RuntimeError("clean-plate wrong native size")
    specs=[{"key":"START","ko":"출발","box":[55,373,136,396],"textsize":[47,18],"shear":8},
           {"key":"GOAL","ko":"골","box":[595,635,672,659],"textsize":[31,19],"shear":8}]
    allowed=np.zeros((h,w),bool);clean=source.copy()
    for q in specs:
        x0,y0,x1,y1=q["box"];allowed[y0:y1,x0:x1]=True
        clean.paste(legacy.crop((x0,y0,x1,y1)),(x0,y0))
    sourcepixels=np.asarray(source,dtype=np.uint8)
    if np.count_nonzero(np.any(sourcepixels!=np.asarray(clean),axis=2)&allowed)<500:raise RuntimeError("English source-removal plate invalid")
    final=clean.copy()
    # B254 decoded output exposed tofu glyph boxes despite machine QA; install a real
    # Korean family and *probe* actual glyph coverage before any DDS write.
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    subprocess.run(["fc-cache","-f"],check=True)
    res=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{family}","Noto Sans CJK KR:style=Bold"],text=True).strip().split("|")
    fp,idx,fam=res[0],int(res[1] or "0"),res[2]
    if not Path(fp).exists() or "NotoSansCJK" not in Path(fp).name or "Noto Sans CJK KR" not in fam:
        raise RuntimeError(("Korean Noto family unresolved",fp,idx,fam))
    glyph_probe=ImageFont.truetype(fp,108,index=idx)
    missing=bytes(glyph_probe.getmask(chr(0x10ffff)))
    for korean in ["출","발","골"]:
        maskdata=bytes(glyph_probe.getmask(korean))
        if not maskdata or not any(maskdata) or maskdata==missing:
            raise RuntimeError(("Missing Hangul glyph / tofu fallback",korean,fp,idx))
    print("B255_KOREAN_GLYPH_COVERAGE_OK",fp,idx,fam,flush=True)
    for q in specs:
        x0,y0,x1,y1=q["box"];fw,fh=q["textsize"];dx=q["shear"]
        f=ImageFont.truetype(fp,108,index=idx)
        mask=Image.new("L",(900,250),0);d=ImageDraw.Draw(mask)
        bb=d.textbbox((0,0),q["ko"],font=f);d.text((40-bb[0],40-bb[1]),q["ko"],fill=255,font=f)
        mask=mask.crop(mask.getbbox()).resize((fw,fh),Image.Resampling.LANCZOS)
        # Source italic: top of the glyph leans right by 8px versus bottom.
        mask=mask.transform((fw+dx,fh),Image.Transform.AFFINE,(1,dx/(fh-1),-dx,0,1,0),resample=Image.Resampling.BICUBIC)
        mask=mask.crop(mask.getbbox())
        edge=mask.filter(ImageFilter.MaxFilter(3))
        glyph=Image.new("RGBA",(mask.width+2,mask.height+3),(0,0,0,0))
        glyph.paste((188,83,40,255),(1,2),edge)
        glyph.paste((235,145,70,255),(1,1),edge)
        glyph.paste((255,244,199,255),(1,1),mask)
        glyph=glyph.crop(glyph.getchannel("A").getbbox())
        gx=x0+(x1-x0-glyph.width)//2;gy=y0+(y1-y0-glyph.height)//2
        margins=[gx-x0,gy-y0,x1-(gx+glyph.width),y1-(gy+glyph.height)]
        if min(margins)<1:raise RuntimeError(("bbox overflow",q["key"],margins,glyph.size))
        final.alpha_composite(glyph,(gx,gy))
        q.update({"local_bbox":[gx,gy,gx+glyph.width,gy+glyph.height],"margins":margins,
                  "generated_face":list(mask.size),"source_top_vs_bottom_shift_target_px":dx})
        mask.save(out/(q["key"]+"_PRETRANSFORM.png"))
        glyph.save(out/(q["key"]+"_POSTTRANSFORM.png"))
    raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    file.write_bytes(a[:128]+raw.tobytes("raw",mode));hashnow=sha(file)
    decoded=decode(file.read_bytes())
    if ImageChops.difference(decoded,final).getbbox():raise RuntimeError("persisted DDS decode differs")
    delta=np.asarray(decoded,dtype=np.uint8)
    changed=np.any(sourcepixels!=delta,axis=2)
    outside=int(np.count_nonzero(changed&~allowed))
    ao=int(np.count_nonzero((sourcepixels[:,:,3]!=delta[:,:,3])&~allowed))
    if outside or ao:raise RuntimeError(("protected overflow",outside,ao))
    def gray(im):
        p=Image.new("RGBA",im.size,(90,90,90,255));p.alpha_composite(im);return p.convert("RGB")
    # Native SOURCE/CLEAN/OLD/NEW, readable and RAW are required for self-QA.
    for title,im in [("SOURCE",source),("CLEAN",clean),("PREVIOUS",previous),("FINAL",decoded),("FINAL_RAW",raw)]:
        im.save(out/(title+".png"))
    contact=[]
    for q in specs:
        x0,y0,x1,y1=q["box"];rect=(x0-5,y0-5,x1+5,y1+5);items=[]
        for tag,im in [("ORIGINAL",source),("CLEAN",clean),("PREVIOUS",previous),("REWORK",decoded)]:
            crop=gray(im).crop(rect);crop=crop.resize((crop.width*6,crop.height*6),Image.Resampling.NEAREST)
            tile=Image.new("RGB",(crop.width,crop.height+23),(28,28,28));tile.paste(crop,(0,23))
            ImageDraw.Draw(tile).text((4,4),q["key"]+" "+tag,fill="white");items.append(tile)
        panel=Image.new("RGB",(sum(i.width for i in items),max(i.height for i in items)),(28,28,28));x=0
        for img in items:panel.paste(img,(x,0));x+=img.width
        contact.append(panel)
    board=Image.new("RGB",(max(x.width for x in contact),sum(x.height for x in contact)+16),(28,28,28));y=0
    for p in contact:board.paste(p,(0,y));y+=p.height+16
    board.save(out/"B255_SOURCE_CLEAN_PREVIOUS_FINAL_NATIVE6X.png")
    for scale in [1,.75,.5]:
        pr=gray(decoded).resize((int(w*scale),int(h*scale)),Image.Resampling.LANCZOS)
        pr.save(out/("PRACTICAL_"+str(int(scale*100))+".png"))
    report={"role":"B","run":run,"queue_index":172,"source_sha256":SOURCE,
            "prior_sha256":PRIOR,"candidate_sha256":hashnow,"source_url":url,
            "execution_backend":"GITHUB_HOSTED_CPU_INPUT_NOT_MATERIALIZABLE_IN_GPT_LOCAL",
            "format":"RGBA32","native_size":[w,h],"mips":1,"raw_orientation":"mirror_y",
            "regions":specs,"changed_inside":int(np.count_nonzero(changed&allowed)),
            "outside_rgba":outside,"outside_alpha":ao,
            "header_exact":file.read_bytes()[:128]==a[:128],
            "roundtrip":"PASS",
            "controller_visual":"PENDING_HUMAN_REVIEW",
            "status":"B255_MACHINE_PASS_PENDING_CONTROLLER",
            "RUNTIME_VALIDATION":"UNTESTED","forbidden_domains_touched":[]}
    rp=out/"B255_MACHINE_QA.json";rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    wr=repo/"localization/graphics/worker_results/B255_6C9B3611.json"
    wr.write_text(json.dumps({"role":"B","run":run,"candidate_sha256":hashnow,
         "status":"B255_MACHINE_PASS_PENDING_CONTROLLER",
         "qa_path":str(rp.relative_to(repo))},ensure_ascii=False,indent=2)+"\n")
    print("B255_DONE",json.dumps({"candidate_sha":hashnow,"regions":specs,"outside":outside},ensure_ascii=False),flush=True)
