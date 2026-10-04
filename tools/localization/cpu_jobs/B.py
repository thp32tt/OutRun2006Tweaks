#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,traceback,zipfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B hosted worker only")

RUN="20261005-B-PRODUCTION50"
ASSET="textures/load/spr_sprani_sumo_fe_cvt_Exst/EBFC709F_512x256.dds"
INDEX=232
# Direct exact-source readable cells established by B48 controller visual evidence.
# Order is semantic/physical: small JOIN, small CREATE, large CREATE, large JOIN.
TARGETS=[
 ("join_small","JOIN GAME","게임 참가",(0,275,300,360),"small"),
 ("create_small","CREATE GAME","게임 만들기",(870,275,1480,360),"small"),
 ("create_large","CREATE GAME","게임 만들기",(0,690,1350,875),"large_blue"),
 ("join_large","JOIN GAME","게임 참가",(0,875,1120,1024),"large_blue"),
]

def main():
    repo=Path.cwd();out=repo/"localization/graphics/role_B"/RUN;out.mkdir(parents=True,exist_ok=True)
    wr=repo/"localization/graphics/worker_results";wr.mkdir(parents=True,exist_ok=True)
    srczip=repo/"localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip"
    cand=repo/"localization/graphics/hd_candidates"/ASSET;cand.parent.mkdir(parents=True,exist_ok=True)
    expected="ad7a1c21be17d1fa93463201a26a85a21899dbe1162d5c2748ddeb6136a4f9a0"
    with zipfile.ZipFile(srczip) as z:sb=z.read(ASSET)
    if hashlib.sha256(sb).hexdigest()!=expected:raise RuntimeError("source hash mismatch")
    if sb[:4]!=b"DDS ":raise RuntimeError("not DDS")
    H=struct.unpack_from("<I",sb,12)[0];W=struct.unpack_from("<I",sb,16)[0];mips=struct.unpack_from("<I",sb,28)[0]
    if (W,H)!=(2048,1024) or len(sb)!=128+W*H*4:raise RuntimeError(("structure",W,H,mips,len(sb)))
    raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
    src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM);sa=np.asarray(src,dtype=np.uint8)

    rows=[];sms=[];full=np.zeros((H,W),bool)
    for n,(key,en,ko,cell,family) in enumerate(TARGETS,1):
        x0,y0,x1,y1=cell
        alpha=sa[y0:y1,x0:x1,3]>0
        yy,xx=np.nonzero(alpha)
        if not len(xx):raise RuntimeError(("empty cell",key))
        bb=[x0+int(xx.min()),y0+int(yy.min()),x0+int(xx.max())+1,y0+int(yy.max())+1]
        # Fail closed if the visual cell captured an unexpected neighboring sentence/artwork.
        if bb[0]<=x0 and x0>0 or bb[2]>=x1 and x1<W:
            raise RuntimeError(("cell x edge ambiguous",key,cell,bb))
        if bb[1]<=y0 or (bb[3]>=y1 and y1<H):
            raise RuntimeError(("cell y edge ambiguous",key,cell,bb))
        sm=np.zeros((H,W),bool);sm[y0:y1,x0:x1]=alpha;sms.append(sm);full|=sm
        rows.append({"n":n,"key":key,"source":en,"korean":ko,"style_family":family,"measurement_cell":list(cell),
                     "original_bbox":bb,"source_effect_pixels":int(np.count_nonzero(sm))})
    for i in range(len(sms)):
        for j in range(i+1,len(sms)):
            if np.any(sms[i]&sms[j]):raise RuntimeError(("source overlap",i+1,j+1))

    clean_a=sa.copy();clean_a[full,3]=0
    if np.any(clean_a[:,:,:3]!=sa[:,:,:3]):raise RuntimeError("clean RGB changed")
    clean=Image.fromarray(clean_a,"RGBA")
    p=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
    if (not p) or (not Path(p).exists()) or ("NotoSansCJK" not in Path(p).name):
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
        p=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
    if "NotoSansCJK" not in Path(p).name:raise RuntimeError(("verified Korean font unavailable",p))
    FONT=p
    def palette(m):
        px=sa[m];px=px[px[:,3]>8];lum=.2126*px[:,0]+.7152*px[:,1]+.0722*px[:,2]
        hi=lum>=np.percentile(lum,65);lo=lum<=np.percentile(lum,25)
        fill=tuple(int(v) for v in np.median(px[hi],axis=0)) if np.any(hi) else tuple(int(v) for v in px[np.argmax(lum)])
        outline=tuple(int(v) for v in np.median(px[lo],axis=0)) if np.any(lo) else fill
        return fill,outline
    def render(row,m):
        x0,y0,x1,y1=row["original_bbox"];aw=x1-x0;ah=y1-y0;fill,outline=palette(m)
        d=ImageDraw.Draw(Image.new("L",(8,8),0))
        for fs in range(min(260,max(16,int(ah*.94))),8,-1):
            sw=max(1,round(fs*(.035 if row["style_family"]=="small" else .025)))
            f=ImageFont.truetype(FONT,fs);tb=d.textbbox((0,0),row["korean"],font=f,stroke_width=sw);pad=sw+4
            st=Image.new("L",(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad),0);fi=Image.new("L",st.size,0);pos=(pad-tb[0],pad-tb[1])
            ImageDraw.Draw(st).text(pos,row["korean"],font=f,fill=255,stroke_width=sw,stroke_fill=255)
            ImageDraw.Draw(fi).text(pos,row["korean"],font=f,fill=255)
            tile=Image.new("RGBA",st.size,(0,0,0,0));tile.paste(outline,(0,0),st);tile.paste(fill,(0,0),fi);ab=tile.getchannel("A").getbbox()
            if not ab:continue
            tile=tile.crop(ab)
            if tile.width>aw-4 or tile.height>ah-4:continue
            layer=Image.new("RGBA",(W,H),(0,0,0,0));layer.alpha_composite(tile,(x0+(aw-tile.width)//2,y0+(ah-tile.height)//2));lb=list(layer.getchannel("A").getbbox())
            if lb[0]<=x0 or lb[1]<=y0 or lb[2]>=x1 or lb[3]>=y1:continue
            return layer,fs,sw,lb,fill,outline
        raise RuntimeError(("cannot fit",row["key"],row["original_bbox"]))
    final=clean.copy();tms=[];target=np.zeros((H,W),bool)
    for row,sm in zip(rows,sms):
        layer,fs,sw,lb,fill,outline=render(row,sm);lm=np.asarray(layer.getchannel("A"))>0
        for old in tms:
            if np.any(lm&old):raise RuntimeError(("localized overlap",row["key"]))
        tms.append(lm);target|=lm;final.alpha_composite(layer)
        ob=row["original_bbox"];row.update({"localized_bbox":lb,"source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],
          "localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],"delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],
          "delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],"containment":"PASS","size_ceiling":"PASS","font_size":fs,
          "stroke_width":sw,"fill":fill,"outline":outline,"font_path_basename":Path(FONT).name,"rework_status":"B49_FULL_PHYSICAL_OCCURRENCE_RENDER"})
    raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM);payload=sb[:128]+raw_final.tobytes("raw","RGBA");cand.write_bytes(payload);csha=hashlib.sha256(payload).hexdigest()
    raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw","RGBA");dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    if payload[:128]!=sb[:128] or ImageChops.difference(dec,final).getbbox():raise RuntimeError("roundtrip")
    da=np.asarray(dec,dtype=np.uint8);allowed=np.zeros((H,W),bool)
    for r in rows:x0,y0,x1,y1=r["original_bbox"];allowed[y0:y1,x0:x1]=True
    changed=np.any(sa!=da,axis=2);outside=int(np.count_nonzero(changed&~allowed));alpha_out=int(np.count_nonzero((sa[:,:,3]!=da[:,:,3])&~allowed))
    guard=np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
    residue=int(np.count_nonzero(full&(da[:,:,3]>0)&~guard));target_out=int(np.count_nonzero(target&~allowed))
    overlap=0;touch=[]
    for i in range(4):
        for j in range(i+1,4):
            ov=int(np.count_nonzero(tms[i]&tms[j]));near=np.asarray(Image.fromarray((tms[i].astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0;npix=int(np.count_nonzero(near&tms[j]));overlap+=ov
            if ov or npix:touch.append([i+1,j+1,ov,npix])
    if outside or alpha_out or residue or target_out or overlap or touch:raise RuntimeError(("QA",outside,alpha_out,residue,target_out,overlap,touch))
    def mi(m):return Image.fromarray((m.astype(np.uint8)*255),"L")
    mi(full).save(out/"EBFC709F_SOURCE_TEXT_MASK.png");mi(allowed).save(out/"EBFC709F_ALLOWED_TEXT_REGION_MASK.png");mi(~allowed).save(out/"EBFC709F_PROTECTED_MASK.png");mi(target).save(out/"EBFC709F_TARGET_TEXT_MASK.png");clean.save(out/"EBFC709F_CLEAN_PLATE.png")
    sp=Path("/tmp/b49src.png");fp=Path("/tmp/b49fin.png");src.save(sp);dec.save(fp);v=repo/"tools/localization/validate_clean_plate.py"
    subprocess.run(["python3",str(v),str(sp),str(out/"EBFC709F_CLEAN_PLATE.png"),str(out/"EBFC709F_SOURCE_TEXT_MASK.png"),"--report",str(out/"B_PRODUCTION50_CLEAN_VALIDATION.json")],check=True)
    subprocess.run(["python3",str(v),str(sp),str(fp),str(out/"EBFC709F_ALLOWED_TEXT_REGION_MASK.png"),"--protected-mask",str(out/"EBFC709F_PROTECTED_MASK.png"),"--report",str(out/"B_PRODUCTION50_FINAL_VALIDATION.json")],check=True)
    def comp(im,bg=(64,64,64,255)):z=Image.new("RGBA",im.size,bg);z.alpha_composite(im);return z.convert("RGB")
    def card(lbl,im,bg=(64,64,64,255)):z=comp(im,bg);c=Image.new("RGB",(W,H+25),"white");c.paste(z,(0,25));ImageDraw.Draw(c).text((5,4),lbl,fill="black");return c
    cs=[card("SOURCE_READABLE",src),card("CLEAN",clean),card("FINAL",dec),card("FINAL_WHITE",dec,(255,255,255,255))]
    sh=Image.new("RGB",(W*2,(H+25)*2),"white");sh.paste(cs[0],(0,0));sh.paste(cs[1],(W,0));sh.paste(cs[2],(0,H+25));sh.paste(cs[3],(W,H+25));sh.thumbnail((1900,1500),Image.Resampling.LANCZOS);sh.save(out/"B_PRODUCTION50_EBFC_COMPARE.jpg",quality=96)
    contacts=[];sr=comp(src);cl=comp(clean);fi=comp(dec)
    for r in rows:
        x0,y0,x1,y1=r["original_bbox"];p=12;cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p));ims=[z.crop(cr) for z in (sr,cl,fi)];ims=[z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST) for z in ims]
        c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+25),"white");xx=0
        for z in ims:c.paste(z,(xx,25));xx+=z.width+6
        ImageDraw.Draw(c).text((4,4),f'{r["n"]} {r["key"]}: {r["source"]} -> {r["korean"]}',fill="black");contacts.append(c)
    rs=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4*(len(contacts)-1)),"white");yy=0
    for c in contacts:rs.paste(c,(0,yy));yy+=c.height+4
    rs.save(out/"B_PRODUCTION50_EBFC_ROW_CONTACT_2X.jpg",quality=96)
    rr=Image.new("RGB",(W,(H+25)*2),"white");rr.paste(card("SOURCE_RAW_MIRROR_Y",raw_src),(0,0));rr.paste(card("FINAL_RAW_MIRROR_Y",raw_dec),(0,H+25));rr.thumbnail((1600,1400),Image.Resampling.LANCZOS);rr.save(out/"B_PRODUCTION50_EBFC_RAW_COMPARE.jpg",quality=96)
    report={"schema_version":1,"role":"B","run":RUN,"queue_index":INDEX,"asset":ASSET,"readiness_tier":"REWORK_REQUIRED_FIXED_SAME_INVOCATION",
      "source_sha256":expected,"candidate_sha256":csha,"candidate_path":str(cand.relative_to(repo)),"structure":{"width":W,"height":H,"format":"RGBA32","mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
      "physical_occurrences":4,"semantic_labels":2,"rows":rows,"font_coverage":"PASS_VERIFIED_NOTO_CJK",
      "containment":{"elements_total":4,"elements_pass":4,"outside":outside,"alpha_outside":alpha_out,"target_out":target_out,"source_residue":residue,"overlap":overlap,"touch_pairs":touch,"status":"PASS"},
      "clean_plate":{"rgb_changed_pixels":0,"source_effect_alpha_remaining":0,"status":"PASS"},"manual_visual_qa":"PENDING_CONTROLLER_SELF_QA","RUNTIME_VALIDATION":"UNTESTED","status":"B_PRODUCTION50_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"}
    (out/"B_PRODUCTION50_EBFC_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    summary={"run":RUN,"asset":"EBFC709F","index":INDEX,"candidate_sha256":csha,"physical_occurrences":"4/4","bbox_size_pass":"4/4","outside":outside,"alpha_outside":alpha_out,"source_residue":residue,"overlap":overlap,"touch_pairs":len(touch),"worker_status":report["status"],"runtime_validation":"UNTESTED","report":f"localization/graphics/role_B/{RUN}/B_PRODUCTION50_EBFC_REPORT.json"}
    (wr/"B_PRODUCTION50_EBFC709F.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n");print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=="__main__":
    try:main()
    except Exception as e:
        repo=Path.cwd();out=repo/"localization/graphics/role_B"/RUN;out.mkdir(parents=True,exist_ok=True);wr=repo/"localization/graphics/worker_results";wr.mkdir(parents=True,exist_ok=True)
        fail={"run":RUN,"asset":"EBFC709F","index":INDEX,"status":"FAIL_CLOSED_DIAGNOSTIC","exception":repr(e),"traceback":traceback.format_exc(),"RUNTIME_VALIDATION":"UNTESTED"}
        (out/"B_PRODUCTION50_FAIL_CLOSED.json").write_text(json.dumps(fail,ensure_ascii=False,indent=2)+"\n");(wr/"B_PRODUCTION50_EBFC709F_FAIL.json").write_text(json.dumps(fail,ensure_ascii=False,indent=2)+"\n");print(json.dumps(fail,ensure_ascii=False),flush=True)
