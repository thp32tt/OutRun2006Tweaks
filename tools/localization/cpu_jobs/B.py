#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,traceback,zipfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B hosted worker only")

RUN="20261005-B-PRODUCTION45"
ASSET="textures/load/spr_sprani_sumo_fe_cvt_Exst/1762489B_512x128.dds"
INDEX=130
LABELS=[
 ("MIX 1 COURSE","믹스 1 코스"),
 ("MIX 2 COURSE","믹스 2 코스"),
 ("OUTRUN2 COURSE","아웃런2 코스"),
 ("OUTRUN2SP COURSE","아웃런2 SP 코스"),
 ("AVERAGE RANK:","평균 랭크:"),
]

def main():
    repo=Path.cwd(); out=repo/"localization/graphics/role_B"/RUN
    out.mkdir(parents=True,exist_ok=True)
    wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
    for p in (out/"B_PRODUCTION45_FAIL_CLOSED.json",wr/"B_PRODUCTION45_1762489B_FAIL.json"):
        if p.exists(): p.unlink()

    source_zip=repo/"localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip"
    hist_zip=repo/"localization/validation/binary_compare/modified/OutRun2_Korean_GFX_FULL_DRAFT_Test.zip"
    candidate=repo/"localization/graphics/hd_candidates"/ASSET
    candidate.parent.mkdir(parents=True,exist_ok=True)
    source_sha="c64baefa65663bc247c33f2f7a72c4ea49990e2a0edb409f186b090dfd3460ac"
    hist_sha="56ffba4bb666542d1218a1e8d721c6e9129268eae8f2e2b87229c6aa83a6874d"

    def sha(b): return hashlib.sha256(b).hexdigest()
    def meta(b):
        if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
        h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]; m=struct.unpack_from("<I",b,28)[0]
        if len(b)!=128+w*h*4: raise RuntimeError(("unexpected RGBA32 payload",w,h,m,len(b)))
        return w,h,m

    with zipfile.ZipFile(source_zip) as z: sb=z.read(ASSET)
    with zipfile.ZipFile(hist_zip) as z: hb=z.read(ASSET)
    if sha(sb)!=source_sha: raise RuntimeError(("source sha",sha(sb)))
    if sha(hb)!=hist_sha: raise RuntimeError(("historical sha",sha(hb)))
    W,H,mips=meta(sb)
    if (W,H)!=(2048,512): raise RuntimeError(("dimensions",W,H))
    if sb[:128]!=hb[:128]: raise RuntimeError("historical header mismatch")

    # Historical orientation record says this atlas stores the text mirror-X in raw DDS.
    src_raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
    hist_raw=Image.frombytes("RGBA",(W,H),hb[128:],"raw","RGBA")
    src=src_raw.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    hist=hist_raw.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    sa=np.asarray(src,dtype=np.uint8); ha=np.asarray(hist,dtype=np.uint8)
    src_alpha=sa[:,:,3]>0
    base_diff=np.any(sa!=ha,axis=2)
    diff=base_diff & ((sa[:,:,3]>0)|(ha[:,:,3]>0))

    def groups(vals,gap=3):
        vals=[int(v) for v in vals]
        if not vals:return []
        out=[]; g=[vals[0]]
        for v in vals[1:]:
            if v-g[-1]>gap: out.append(g); g=[v]
            else:g.append(v)
        out.append(g); return out

    def discover(mask,k):
        d=np.asarray(Image.fromarray((mask.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(k)))>0
        boxes=[]
        for rg in groups(np.flatnonzero(np.any(d,axis=1)),3):
            y0,y1=rg[0],rg[-1]+1
            for cg in groups(np.flatnonzero(np.any(d[y0:y1],axis=0)),3):
                x0,x1=cg[0],cg[-1]+1
                core=int(np.count_nonzero(mask[y0:y1,x0:x1]))
                if core>=24 and x1-x0>=10 and y1-y0>=6: boxes.append([x0,y0,x1,y1,core])
        boxes.sort(key=lambda b:(b[1],b[0]))
        return boxes

    # Use the k=7 discovery where individual glyph groups are still separated by row.
    # Merge glyph fragments only within the same physical row; do not let dilation bridge
    # vertically adjacent labels. The atlas layout is top-left + top-right, then three
    # right-side rows = five semantic labels.
    raw=discover(diff,7)
    trials={"7":raw}
    bands=[]
    for b in raw:
        placed=False
        for band in bands:
            a=band[0]
            ov=max(0,min(a[3],b[3])-max(a[1],b[1])); mh=min(a[3]-a[1],b[3]-b[1])
            if mh>0 and ov/mh>=0.70:
                band.append(b); placed=True; break
        if not placed: bands.append([b])
    anchors=[]
    for band in bands:
        band=sorted(band,key=lambda x:x[0])
        cur=None
        for b in band:
            if cur is None:
                cur=b[:]
                continue
            gap=b[0]-cur[2]
            if 0<=gap<=120:
                cur=[min(cur[0],b[0]),min(cur[1],b[1]),max(cur[2],b[2]),max(cur[3],b[3]),cur[4]+b[4]]
            else:
                anchors.append(cur); cur=b[:]
        if cur is not None: anchors.append(cur)
    best=sorted(anchors,key=lambda b:(b[1],b[0]))
    if len(best)!=5:
        (out/"B_PRODUCTION45_DISCOVERY_DIAGNOSTIC.json").write_text(json.dumps({"raw_k7":raw,"bands":bands,"post_row_merge":best},indent=2)+"\n")
        raise RuntimeError(("expected 5 target regions after row merge",len(best)))

    # Exact source-effect mask: for each historical-diff anchor, include complete
    # connected source-alpha components that intersect a small diff-neighborhood.
    rows=[]; source_masks=[]; full_source=np.zeros((H,W),bool)
    structure=np.ones((3,3),dtype=np.uint8)
    for n,(anchor,(en,ko)) in enumerate(zip(best,LABELS),1):
        ax0,ay0,ax1,ay1,_=anchor
        pad=28; x0=max(0,ax0-pad); y0=max(0,ay0-pad); x1=min(W,ax1+pad); y1=min(H,ay1+pad)
        la=src_alpha[y0:y1,x0:x1]
        seed=diff[y0:y1,x0:x1]
        seed_near=np.asarray(Image.fromarray((seed.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(11)))>0
        lab,count=ndimage.label(la,structure=structure)
        ids=np.unique(lab[seed_near & la]); ids=ids[ids!=0]
        if not len(ids): raise RuntimeError(("no source components",n,anchor))
        sm_local=np.isin(lab,ids)
        yy,xx=np.nonzero(sm_local)
        bb=[x0+int(xx.min()),y0+int(yy.min()),x0+int(xx.max())+1,y0+int(yy.max())+1]
        # Reject broad artwork capture. Text source components should remain sparse.
        dens=float(np.count_nonzero(sm_local)/max(1,(bb[2]-bb[0])*(bb[3]-bb[1])))
        if dens>0.58 or (bb[2]-bb[0])>min(W,anchor[2]-anchor[0]+100) or (bb[3]-bb[1])>min(H,anchor[3]-anchor[1]+80):
            raise RuntimeError(("source scope ambiguous",n,anchor,bb,dens))
        sm=np.zeros((H,W),bool); sm[y0:y1,x0:x1]=sm_local
        source_masks.append(sm); full_source|=sm
        rows.append({"n":n,"source":en,"korean":ko,"discovery_anchor":anchor[:4],"original_bbox":bb,
                     "source_effect_pixels":int(np.count_nonzero(sm)),"source_mask_density":dens})

    for i in range(5):
        for j in range(i+1,5):
            if np.any(source_masks[i]&source_masks[j]): raise RuntimeError(("source mask overlap",i+1,j+1))

    # Exact clean plate for this transparent/semitransparent text atlas: remove
    # only source text/effect alpha; preserve all source RGB and all non-target pixels.
    clean_arr=sa.copy(); clean_arr[full_source,3]=0
    if np.any(clean_arr[:,:,:3]!=sa[:,:,:3]): raise RuntimeError("clean RGB changed")
    clean=Image.fromarray(clean_arr,"RGBA")

    def font_path():
        p=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Bold"],text=True).strip()
        if not p or not Path(p).exists() or "NotoSansCJK" not in Path(p).name:
            subprocess.run(["sudo","apt-get","update","-qq"],check=True)
            subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
            p=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Bold"],text=True).strip()
        if not p: raise RuntimeError("font unavailable")
        return p
    FONT=font_path()

    def palette(mask):
        p=sa[mask]; p=p[p[:,3]>4]
        if len(p)<8:return (255,255,255,255),(20,30,60,220)
        lum=.2126*p[:,0]+.7152*p[:,1]+.0722*p[:,2]
        hi=lum>=np.percentile(lum,67); lo=lum<=np.percentile(lum,25)
        fill=tuple(int(v) for v in np.median(p[hi],axis=0)) if np.any(hi) else tuple(int(v) for v in p[np.argmax(lum)])
        outline=tuple(int(v) for v in np.median(p[lo],axis=0)) if np.any(lo) else (20,30,60,220)
        return fill,outline

    def slant(mask,bb):
        x0,y0,x1,y1=bb; m=mask[y0:y1,x0:x1]; ys=[]; ls=[]
        for y in range(m.shape[0]):
            xs=np.flatnonzero(m[y])
            if len(xs)>=2: ys.append(y); ls.append(float(np.percentile(xs,15)))
        if len(ys)<7:return 0.0
        s=-float(np.polyfit(np.asarray(ys),np.asarray(ls),1)[0])
        return float(np.clip(s,0,0.32))

    def shear(im,s):
        if s<0.005:return im
        sh=max(0,int(round(s*(im.height-1))))
        o=Image.new("RGBA",(im.width+sh,im.height),(0,0,0,0))
        for y in range(im.height): o.alpha_composite(im.crop((0,y,im.width,y+1)),(int(round(s*(im.height-1-y))),y))
        return o

    def render(row,mask):
        bb=row["original_bbox"]; x0,y0,x1,y1=bb; aw=x1-x0; ah=y1-y0
        fill,outline=palette(mask); ss=slant(mask,bb); d=ImageDraw.Draw(Image.new("L",(8,8),0))
        for fs in range(min(150,max(14,int(ah*.92))),7,-1):
            sw=max(1,round(fs*.05)); f=ImageFont.truetype(FONT,fs)
            tb=d.textbbox((0,0),row["korean"],font=f,stroke_width=sw); pad=sw+4
            sz=(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad)
            st=Image.new("L",sz,0); fi=Image.new("L",sz,0); pos=(pad-tb[0],pad-tb[1])
            ImageDraw.Draw(st).text(pos,row["korean"],font=f,fill=255,stroke_width=sw,stroke_fill=255)
            ImageDraw.Draw(fi).text(pos,row["korean"],font=f,fill=255)
            tile=Image.new("RGBA",sz,(0,0,0,0)); tile.paste(outline,(0,0),st); tile.paste(fill,(0,0),fi); tile=shear(tile,ss)
            ab=tile.getchannel("A").getbbox()
            if not ab:continue
            tile=tile.crop(ab)
            if tile.width>aw-2 or tile.height>ah-2:continue
            px=x0+(aw-tile.width)//2; py=y0+(ah-tile.height)//2
            layer=Image.new("RGBA",(W,H),(0,0,0,0)); layer.alpha_composite(tile,(px,py)); lb=list(layer.getchannel("A").getbbox())
            if lb[0]<=x0 or lb[1]<=y0 or lb[2]>=x1 or lb[3]>=y1:continue
            return layer,fs,sw,ss,lb,fill,outline
        raise RuntimeError(("cannot fit",row["source"],row["korean"],bb))

    final=clean.copy(); target_masks=[]
    for row,sm in zip(rows,source_masks):
        layer,fs,sw,ss,lb,fill,outline=render(row,sm); lm=np.asarray(layer.getchannel("A"))>0
        for old in target_masks:
            if np.any(lm&old): raise RuntimeError(("localized overlap",row["n"]))
        target_masks.append(lm); final.alpha_composite(layer)
        ob=row["original_bbox"]; sw0,sh0=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
        row.update({"localized_bbox":lb,"source_width":sw0,"source_height":sh0,"localized_width":lw,"localized_height":lh,
                    "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
                    "containment":"PASS","size_ceiling":"PASS","edge_touch_high_risk":False,"font_size":fs,"stroke_width":sw,
                    "slant":ss,"fill":fill,"outline":outline,"rework_status":"NEW_EXACT_SOURCE_RGBA_NATIVE_RENDER"})

    target=np.zeros((H,W),bool)
    for m in target_masks: target|=m
    final_raw=final.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    payload=sb[:128]+final_raw.tobytes("raw","RGBA")
    candidate.write_bytes(payload); cand_sha=sha(payload)
    cb=candidate.read_bytes(); _,_,_=meta(cb)
    dec_raw=Image.frombytes("RGBA",(W,H),cb[128:],"raw","RGBA"); dec=dec_raw.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if cb[:128]!=sb[:128] or ImageChops.difference(final,dec).getbbox() is not None: raise RuntimeError("DDS roundtrip/header")
    da=np.asarray(dec,dtype=np.uint8)

    allowed=np.zeros((H,W),bool)
    for row in rows:
        x0,y0,x1,y1=row["original_bbox"]; allowed[y0:y1,x0:x1]=True
    changed=np.any(sa!=da,axis=2); clean_changed=np.any(clean_arr!=sa,axis=2)
    outside=int(np.count_nonzero(changed&~allowed)); alpha_out=int(np.count_nonzero((sa[:,:,3]!=da[:,:,3])&~allowed))
    clean_out=int(np.count_nonzero(clean_changed&~full_source)); clean_residue=int(np.count_nonzero(full_source&(clean_arr[:,:,3]>0)))
    target_out=int(np.count_nonzero(target&~allowed))
    guard=np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
    residue=int(np.count_nonzero(full_source&(da[:,:,3]>0)&~guard))
    touches=[]; overlap=0
    for i in range(5):
        for j in range(i+1,5):
            ov=int(np.count_nonzero(target_masks[i]&target_masks[j])); overlap+=ov
            near=np.asarray(Image.fromarray((target_masks[i].astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0
            npix=int(np.count_nonzero(near&target_masks[j]))
            if ov or npix: touches.append([i+1,j+1,ov,npix])
    ok=not any([outside,alpha_out,clean_out,clean_residue,target_out,residue,overlap,len(touches)])
    if not ok: raise RuntimeError(("static QA",outside,alpha_out,clean_out,clean_residue,target_out,residue,overlap,touches))

    def mimg(m):return Image.fromarray((m.astype(np.uint8)*255),"L")
    mimg(full_source).save(out/"1762489B_SOURCE_TEXT_MASK.png")
    mimg(allowed).save(out/"1762489B_ALLOWED_TEXT_REGION_MASK.png")
    mimg(~allowed).save(out/"1762489B_PROTECTED_MASK.png")
    mimg(target).save(out/"1762489B_TARGET_TEXT_MASK.png")
    clean.save(out/"1762489B_CLEAN_PLATE.png")
    sp=Path("/tmp/176_source.png"); fp=Path("/tmp/176_final.png"); src.save(sp); dec.save(fp)
    validator=repo/"tools/localization/validate_clean_plate.py"
    subprocess.run(["python3",str(validator),str(sp),str(out/"1762489B_CLEAN_PLATE.png"),str(out/"1762489B_SOURCE_TEXT_MASK.png"),"--report",str(out/"B_PRODUCTION45_CLEAN_VALIDATION.json")],check=True)
    subprocess.run(["python3",str(validator),str(sp),str(fp),str(out/"1762489B_ALLOWED_TEXT_REGION_MASK.png"),"--protected-mask",str(out/"1762489B_PROTECTED_MASK.png"),"--report",str(out/"B_PRODUCTION45_FINAL_VALIDATION.json")],check=True)

    def comp(im,bg=(64,64,64,255)):
        z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
    def card(label,im,bg=(64,64,64,255)):
        v=comp(im,bg); c=Image.new("RGB",(W,H+25),"white"); c.paste(v,(0,25)); ImageDraw.Draw(c).text((5,4),label,fill="black"); return c
    cards=[card("SOURCE_READABLE",src),card("CLEAN",clean),card("FINAL",dec),card("FINAL_WHITE",dec,(255,255,255,255))]
    sh=Image.new("RGB",(W*2,(H+25)*2),"white")
    sh.paste(cards[0],(0,0));sh.paste(cards[1],(W,0));sh.paste(cards[2],(0,H+25));sh.paste(cards[3],(W,H+25))
    sh.thumbnail((1900,1200),Image.Resampling.LANCZOS);sh.save(out/"B_PRODUCTION45_176_COMPARE.jpg",quality=96)

    contacts=[]; sr=comp(src); cl=comp(clean); fi=comp(dec)
    for row in rows:
        x0,y0,x1,y1=row["original_bbox"]; p=10; cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
        ims=[z.crop(cr) for z in (sr,cl,fi)]; ims=[z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST) for z in ims]
        c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+25),"white");xx=0
        for z in ims:c.paste(z,(xx,25));xx+=z.width+6
        ImageDraw.Draw(c).text((4,4),f'{row["n"]} {row["source"]} -> {row["korean"]}',fill="black");contacts.append(c)
    rs=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4*(len(contacts)-1)),"white");yy=0
    for c in contacts:rs.paste(c,(0,yy));yy+=c.height+4
    rs.save(out/"B_PRODUCTION45_176_ROW_CONTACT_2X.jpg",quality=96)

    raws=[card("SOURCE_RAW_MIRROR_X",src_raw),card("FINAL_RAW_MIRROR_X",dec_raw)]
    rr=Image.new("RGB",(W,(H+25)*2),"white");rr.paste(raws[0],(0,0));rr.paste(raws[1],(0,H+25));rr.thumbnail((1600,1000),Image.Resampling.LANCZOS);rr.save(out/"B_PRODUCTION45_176_RAW_COMPARE.jpg",quality=96)

    report={"schema_version":1,"role":"B","run":RUN,"queue_index":INDEX,"asset":ASSET,
      "readiness_tier":"RENDER_READY_COMPLETED_SAME_INVOCATION","source_sha256":source_sha,
      "historical_discovery_sha256":hist_sha,"historical_discovery_only":True,"historical_localized_pixels_reused":False,
      "candidate_sha256":cand_sha,"candidate_path":str(candidate.relative_to(repo)),
      "method":"exact 2048x512 RGBA32 source; historical candidate only as target-region hint; exact connected source-alpha/effect component masks; alpha-only clean plate; fresh Hangul render; exact-header mirror-X DDS; decoded static QA",
      "structure":{"width":W,"height":H,"format":"RGBA32","mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_x"},
      "segments_total":5,"preserved_original":["numeric rank marker","unrelated artwork"],"rows":rows,
      "containment":{"elements_total":5,"elements_pass":5,"changed_pixels_outside_original_bboxes":outside,
        "alpha_changed_pixels_outside_original_bboxes":alpha_out,"target_pixels_outside_original_bboxes":target_out,
        "source_residue_pixels_outside_2px_target_guard":residue,"localized_overlap_pixels":overlap,
        "localized_touch_pairs":touches,"status":"PASS"},
      "clean_plate":{"changed_pixels_outside_source_effect":clean_out,"source_effect_alpha_remaining":clean_residue,"rgb_changed_pixels":0,"status":"PASS"},
      "policy":{"stage_names":"not_applicable","song_titles_credits":"not_targeted","multi_line":"not_applicable"},
      "manual_visual_qa":"PENDING_CONTROLLER_SELF_QA","RUNTIME_VALIDATION":"UNTESTED",
      "status":"B_PRODUCTION45_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"}
    (out/"B_PRODUCTION45_176_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary={"run":RUN,"asset":"1762489B","index":INDEX,"candidate_sha256":cand_sha,"bbox_size_pass":"5/5",
      "outside":outside,"alpha_outside":alpha_out,"source_residue":residue,"overlap":overlap,"touch_pairs":len(touches),
      "worker_status":report["status"],"runtime_validation":"UNTESTED","report":f"localization/graphics/role_B/{RUN}/B_PRODUCTION45_176_REPORT.json"}
    (wr/"B_PRODUCTION45_1762489B.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=="__main__":
    try: main()
    except Exception as e:
        repo=Path.cwd(); out=repo/"localization/graphics/role_B"/RUN; out.mkdir(parents=True,exist_ok=True)
        wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
        fail={"run":RUN,"asset":"1762489B","index":INDEX,"status":"FAIL_CLOSED_DIAGNOSTIC","exception":repr(e),"traceback":traceback.format_exc(),"RUNTIME_VALIDATION":"UNTESTED"}
        (out/"B_PRODUCTION45_FAIL_CLOSED.json").write_text(json.dumps(fail,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        (wr/"B_PRODUCTION45_1762489B_FAIL.json").write_text(json.dumps(fail,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(fail,ensure_ascii=False),flush=True)
