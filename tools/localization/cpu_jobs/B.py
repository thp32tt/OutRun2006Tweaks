#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,zipfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B hosted worker only")

def main():
    repo=Path.cwd()
    run="20261005-B-PRODUCTION44"
    out=repo/"localization/graphics/role_B"/run
    out.mkdir(parents=True,exist_ok=True)
    wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
    for stale in [out/"B_PRODUCTION44_DISCOVERY_FAIL.json", out/"B_PRODUCTION44_FAIL_CLOSED.json", wr/"B_PRODUCTION44_12519155_FAIL.json"]:
        if stale.exists(): stale.unlink()

    asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/12519155_256x256.dds"
    source_zip=repo/"localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip"
    hist_zip=repo/"localization/validation/binary_compare/modified/OutRun2_Korean_GFX_FULL_DRAFT_Test.zip"
    candidate=repo/"localization/graphics/hd_candidates"/asset
    candidate.parent.mkdir(parents=True,exist_ok=True)
    source_sha_expected="ad88efc25b705be8960f373f8a06ea88ce39f086857e68c851595f7c867c14c3"
    hist_sha_expected="c66b8a0b1294a5ada7f28ebb0023bb461c26aac4b99da4c5da60894dce8a3f83"
    labels=[
     ("Time Attack Mode / 15 C.","타임 어택 모드 / 15코스",False),
     ("Alpine","알파인",True),
     ("Ancient Ruins","에인션트 루인스",True),
     ("Bay Area","베이 에어리어",True),
     ("Big Forest","빅 포레스트",True),
     ("Canyon","캐니언",True),
     ("Cape Way","케이프 웨이",True),
    ]

    def sha_bytes(b): return hashlib.sha256(b).hexdigest()
    def rgba_meta(b):
        if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
        h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
        mips=struct.unpack_from("<I",b,28)[0]
        if len(b)!=128+w*h*4: raise RuntimeError(("unexpected_rgba_size",w,h,mips,len(b),128+w*h*4))
        return w,h,mips

    with zipfile.ZipFile(source_zip) as z: sb=z.read(asset)
    with zipfile.ZipFile(hist_zip) as z: hb=z.read(asset)
    if sha_bytes(sb)!=source_sha_expected: raise RuntimeError(("source_sha",sha_bytes(sb)))
    if sha_bytes(hb)!=hist_sha_expected: raise RuntimeError(("historical_sha",sha_bytes(hb)))
    W,H,mips=rgba_meta(sb)
    if (W,H)!=(1024,1024): raise RuntimeError(("dimensions",W,H))
    if hb[:128]!=sb[:128]: raise RuntimeError("historical header differs")
    # Direct raw-element inspection shows all seven source rows are mirror-Y (top/bottom flipped).
    # FLIP_TOP_BOTTOM restores both glyph orientation and the semantic row order recorded by transcription.
    src_raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
    hist_raw=Image.frombytes("RGBA",(W,H),hb[128:],"raw","RGBA")
    src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    hist=hist_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    sa=np.asarray(src,dtype=np.uint8); ha=np.asarray(hist,dtype=np.uint8)

    # Historical candidate is discovery-only. It supplies no final pixels.
    base_diff=np.any(sa!=ha,axis=2)
    visible=(sa[:,:,3]>0)|(ha[:,:,3]>0)
    diff=base_diff & visible

    def groups(active,max_gap=2):
        active=[int(x) for x in active]
        if not active: return []
        out=[]; g=[active[0]]
        for v in active[1:]:
            if v-g[-1] > max_gap:
                out.append(g); g=[v]
            else: g.append(v)
        out.append(g); return out

    def discover_components(mask,k):
        d=np.asarray(Image.fromarray((mask.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(k)))>0
        rgs=groups(np.flatnonzero(np.count_nonzero(d,axis=1)>0),2)
        boxes=[]
        for rg in rgs:
            y0,y1=rg[0],rg[-1]+1
            cgs=groups(np.flatnonzero(np.count_nonzero(d[y0:y1],axis=0)>0),2)
            for cg in cgs:
                x0,x1=cg[0],cg[-1]+1
                core=int(np.count_nonzero(mask[y0:y1,x0:x1]))
                if core<20 or (x1-x0)<8 or (y1-y0)<6: continue
                boxes.append([x0,y0,x1,y1,core])
        boxes.sort(key=lambda b:(b[1],b[0]))
        return boxes

    tries={}
    best=None
    for k in (5,7,9,11,13,15,17,21,25):
        b=discover_components(diff,k); tries[str(k)]=b
        if best is None or abs(len(b)-7)<abs(len(best)-7): best=b
        if len(b)==7: best=b; break
    # A single long bottom label can split into two diff components at a narrow glyph gap.
    # Merge only components that are on the same physical row, have strong vertical overlap,
    # and are separated by <= 16 px. This preserves all independent stacked labels.
    if len(best)>7:
        merged=[]
        for b in best:
            if merged:
                a=merged[-1]
                ov=max(0,min(a[3],b[3])-max(a[1],b[1]))
                minh=min(a[3]-a[1],b[3]-b[1])
                gap=b[0]-a[2]
                if minh>0 and ov/minh>=0.80 and 0<=gap<=16:
                    merged[-1]=[min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3]),a[4]+b[4]]
                    continue
            merged.append(b)
        best=merged
    merge_note=None
    if len(best)==8:
        # C128 small corrective rework: one long bottom label can split into
        # two horizontally adjacent discovery components. Merge only one
        # unambiguous same-band pair with a small horizontal gap.
        pairs=[]
        for i in range(len(best)-1):
            a=best[i]
            for j in range(i+1,len(best)):
                bb=best[j]
                ov=max(0,min(a[3],bb[3])-max(a[1],bb[1]))
                mh=min(a[3]-a[1],bb[3]-bb[1])
                if mh<=0 or ov/mh < 0.80:
                    continue
                left,right=(a,bb) if a[0] <= bb[0] else (bb,a)
                gap=right[0]-left[2]
                if 0 <= gap <= 12:
                    pairs.append((gap,i,j))
        if len(pairs)==1:
            gap,i,j=pairs[0]
            a,bb=best[i],best[j]
            merged=[min(a[0],bb[0]),min(a[1],bb[1]),max(a[2],bb[2]),max(a[3],bb[3]),a[4]+bb[4]]
            best=[x for n,x in enumerate(best) if n not in (i,j)] + [merged]
            best.sort(key=lambda x:(x[1],x[0]))
            merge_note={"pair":[i,j],"gap":gap,"merged_bbox":merged}
    if len(best)!=7:
        (out/"B_PRODUCTION44_DISCOVERY_FAIL.json").write_text(json.dumps({"counts":{k:len(v) for k,v in tries.items()},"boxes":tries,"post_row_merge":best},indent=2)+"\n")
        raise RuntimeError(("expected_7_regions",len(best)))

    # Slightly expand each discovery region only for measuring source effect pixels.
    regions=[]
    all_source_mask=np.zeros((H,W),bool)
    rows=[]
    for i,(box,lab) in enumerate(zip(best,labels),1):
        x0,y0,x1,y1,_=box; pad=6
        x0=max(0,x0-pad); y0=max(0,y0-pad); x1=min(W,x1+pad); y1=min(H,y1+pad)
        local_diff=diff[y0:y1,x0:x1]
        hint=np.asarray(Image.fromarray((local_diff.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
        local_alpha=sa[y0:y1,x0:x1,3]>0
        sm=hint & local_alpha
        yy,xx=np.nonzero(sm)
        if not len(xx): raise RuntimeError(("empty_source_mask",i,box))
        # Keep source-connected effect pixels inside the discovered region.
        bx=[x0+int(xx.min()),y0+int(yy.min()),x0+int(xx.max())+1,y0+int(yy.max())+1]
        # Tighten to source pixels near the actual change while retaining AA/outline fringe.
        sub=sm[bx[1]-y0:bx[3]-y0,bx[0]-x0:bx[2]-x0]
        density=float(np.count_nonzero(sub)/max(1,(bx[2]-bx[0])*(bx[3]-bx[1])))
        src_alpha_density=float(np.count_nonzero(sa[bx[1]:bx[3],bx[0]:bx[2],3]>0)/max(1,(bx[2]-bx[0])*(bx[3]-bx[1])))
        if src_alpha_density>0.62:
            raise RuntimeError(("opaque_or_art_dense_region_requires_manual_clean_plate",i,bx,src_alpha_density))
        full=np.zeros((H,W),bool); full[y0:y1,x0:x1]=sm
        all_source_mask|=full
        regions.append((full,bx))
        rows.append({"n":i,"source":lab[0],"korean":lab[1],"stage_name":lab[2],
                     "discovery_bbox":[x0,y0,x1,y1],"original_bbox":bx,
                     "source_mask_density":density,"source_alpha_density":src_alpha_density})

    # Ensure regions are disjoint.
    for i in range(len(regions)):
        for j in range(i+1,len(regions)):
            if np.any(regions[i][0]&regions[j][0]): raise RuntimeError(("source_mask_overlap",i+1,j+1))

    # Transparent/semitransparent text atlas clean plate: erase source effect alpha only; hidden RGB is preserved.
    clean_arr=sa.copy(); clean_arr[all_source_mask,3]=0
    clean=Image.fromarray(clean_arr,"RGBA")
    if np.count_nonzero(clean_arr[:,:,:3]!=sa[:,:,:3]): raise RuntimeError("clean_rgb_changed")

    def font_path():
        p=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Bold"],text=True).strip()
        if not p or not Path(p).exists() or "NotoSansCJK" not in Path(p).name:
            subprocess.run(["sudo","apt-get","update","-qq"],check=True)
            subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
            p=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Bold"],text=True).strip()
        if not p: raise RuntimeError("font unavailable")
        return p
    FONT=font_path()

    def measure_palette(mask):
        p=sa[mask]
        p=p[p[:,3]>4]
        if len(p)<8: return (255,255,255,255),(255,255,255,255),(20,30,70,230)
        lum=.2126*p[:,0]+.7152*p[:,1]+.0722*p[:,2]
        hi=lum>=np.percentile(lum,68); lo=lum<=np.percentile(lum,25)
        top=tuple(int(v) for v in np.median(p[hi],axis=0)) if np.any(hi) else tuple(int(v) for v in p[np.argmax(lum)])
        bot=top
        outline=tuple(int(v) for v in np.median(p[lo],axis=0)) if np.any(lo) else (20,30,70,220)
        return top,bot,outline

    def source_slant(mask,bb):
        x0,y0,x1,y1=bb
        m=mask[y0:y1,x0:x1]
        ys=[]; left=[]
        for yy in range(m.shape[0]):
            xs=np.flatnonzero(m[yy])
            if len(xs)>=2:
                ys.append(yy); left.append(float(np.percentile(xs,15)))
        if len(ys)<8: return 0.0
        slope=float(np.polyfit(np.asarray(ys),np.asarray(left),1)[0])
        # right-leaning top corresponds to negative left-edge slope
        return float(np.clip(-slope,0.0,0.32))

    def shear(im,s):
        if s<=0.005: return im
        shift=max(0,int(round(s*(im.height-1))))
        o=Image.new("RGBA",(im.width+shift,im.height),(0,0,0,0))
        for y in range(im.height):
            dx=int(round(s*(im.height-1-y)))
            o.alpha_composite(im.crop((0,y,im.width,y+1)),(dx,y))
        return o

    def render_text(text,bb,mask):
        x0,y0,x1,y1=bb; aw=x1-x0; ah=y1-y0
        top,bot,outline=measure_palette(mask); sl=source_slant(mask,bb)
        dummy=ImageDraw.Draw(Image.new("L",(8,8),0))
        for fs in range(min(180,max(16,int(ah*.95))),7,-1):
            sw=max(1,round(fs*.055))
            f=ImageFont.truetype(FONT,fs)
            tb=dummy.textbbox((0,0),text,font=f,stroke_width=sw)
            pad=sw+4
            size=(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad)
            stroke=Image.new("L",size,0); fill=Image.new("L",size,0)
            pos=(pad-tb[0],pad-tb[1])
            ImageDraw.Draw(stroke).text(pos,text,font=f,fill=255,stroke_width=sw,stroke_fill=255)
            ImageDraw.Draw(fill).text(pos,text,font=f,fill=255)
            tile=Image.new("RGBA",size,(0,0,0,0))
            tile.paste(outline,(0,0),stroke)
            grad=np.zeros((size[1],size[0],4),dtype=np.uint8)
            for yy in range(size[1]):
                t=yy/max(1,size[1]-1)
                for c in range(3): grad[yy,:,c]=round(top[c]*(1-t)+bot[c]*t)
                grad[yy,:,3]=255
            tile.paste(Image.fromarray(grad,"RGBA"),(0,0),fill)
            tile=shear(tile,sl)
            ab=tile.getchannel("A").getbbox()
            if not ab: continue
            tile=tile.crop(ab)
            if tile.width>aw-2 or tile.height>ah-2: continue
            px=x0+(aw-tile.width)//2; py=y0+(ah-tile.height)//2
            layer=Image.new("RGBA",(W,H),(0,0,0,0)); layer.alpha_composite(tile,(px,py))
            lb=list(layer.getchannel("A").getbbox())
            if lb[0]<=x0 or lb[1]<=y0 or lb[2]>=x1 or lb[3]>=y1: continue
            return layer,fs,sw,sl,lb,{"fill_top":top,"fill_bottom":bot,"outline":outline}
        raise RuntimeError(("cannot_fit",text,bb))

    final=clean.copy(); layers=[]; target=np.zeros((H,W),bool)
    for row,(sm,bb) in zip(rows,regions):
        layer,fs,sw,sl,lb,pal=render_text(row["korean"],bb,sm)
        lm=np.asarray(layer.getchannel("A"))>0
        for old in layers:
            if np.any(lm & old): raise RuntimeError(("localized_overlap",row["n"]))
        layers.append(lm); target|=lm; final.alpha_composite(layer)
        sw0,sh0=bb[2]-bb[0],bb[3]-bb[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
        if lw>sw0 or lh>sh0: raise RuntimeError(("size_ceiling",row["n"],bb,lb))
        row.update({"localized_bbox":lb,"source_width":sw0,"source_height":sh0,
                    "localized_width":lw,"localized_height":lh,
                    "delta_left":lb[0]-bb[0],"delta_right":bb[2]-lb[2],
                    "delta_top":lb[1]-bb[1],"delta_bottom":bb[3]-lb[3],
                    "containment":"PASS","size_ceiling":"PASS","font_size":fs,
                    "stroke_width":sw,"slant":sl,"palette":pal,
                    "rework_status":"NEW_EXACT_SOURCE_RGBA_NATIVE_RENDER"})

    # Exact-header raw mirror-Y write matching the exact source element transform.
    final_raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    payload=sb[:128]+final_raw.tobytes("raw","RGBA")
    candidate.write_bytes(payload)
    cand_sha=sha_bytes(payload)
    cb=candidate.read_bytes()
    if cb[:128]!=sb[:128] or len(cb)!=len(sb): raise RuntimeError("structure mismatch")
    decoded_raw=Image.frombytes("RGBA",(W,H),cb[128:],"raw","RGBA")
    decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    if ImageChops.difference(final,decoded).getbbox() is not None: raise RuntimeError("roundtrip mismatch")
    da=np.asarray(decoded,dtype=np.uint8)

    allowed=np.zeros((H,W),bool)
    for row in rows:
        x0,y0,x1,y1=row["original_bbox"]; allowed[y0:y1,x0:x1]=True
    changed=np.any(sa!=da,axis=2)
    outside=int(np.count_nonzero(changed&~allowed))
    alpha_out=int(np.count_nonzero((sa[:,:,3]!=da[:,:,3])&~allowed))
    protected=int(np.count_nonzero(changed&~allowed))
    guard=np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
    residue=int(np.count_nonzero(all_source_mask&(da[:,:,3]>0)&~guard))
    overlap_pairs=0
    for i in range(len(layers)):
        for j in range(i+1,len(layers)):
            if np.any(layers[i]&layers[j]): overlap_pairs+=1
    if outside or alpha_out or protected or residue or overlap_pairs:
        raise RuntimeError(("qa",outside,alpha_out,protected,residue,overlap_pairs))

    def mask_img(m): return Image.fromarray((m.astype(np.uint8)*255),"L")
    source_mask_png=out/"12519155_SOURCE_TEXT_MASK.png"; mask_img(all_source_mask).save(source_mask_png)
    allowed_png=out/"12519155_ALLOWED_TEXT_REGION_MASK.png"; mask_img(allowed).save(allowed_png)
    protected_png=out/"12519155_PROTECTED_MASK.png"; mask_img(~allowed).save(protected_png)
    target_png=out/"12519155_TARGET_TEXT_MASK.png"; mask_img(target).save(target_png)
    clean_png=out/"12519155_CLEAN_PLATE.png"; clean.save(clean_png)
    src_png=Path("/tmp/125_src.png"); final_png=Path("/tmp/125_final.png"); src.save(src_png); decoded.save(final_png)
    validator=repo/"tools/localization/validate_clean_plate.py"
    subprocess.run(["python3",str(validator),str(src_png),str(clean_png),str(source_mask_png),"--report",str(out/"B_PRODUCTION44_CLEAN_PLATE_VALIDATION.json")],check=True)
    subprocess.run(["python3",str(validator),str(src_png),str(final_png),str(allowed_png),"--protected-mask",str(protected_png),"--report",str(out/"B_PRODUCTION44_FINAL_MASK_VALIDATION.json")],check=True)

    def comp(im,bg=(64,64,64,255)):
        z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
    def card(label,im,bg=(64,64,64,255)):
        v=comp(im,bg); c=Image.new("RGB",(W,H+26),"white"); c.paste(v,(0,26)); ImageDraw.Draw(c).text((5,5),label,fill="black"); return c
    cards=[card("SOURCE_READABLE",src),card("CLEAN",clean),card("FINAL",decoded),card("FINAL_WHITE",decoded,(255,255,255,255))]
    sheet=Image.new("RGB",(W*2,(H+26)*2),"white")
    sheet.paste(cards[0],(0,0)); sheet.paste(cards[1],(W,0)); sheet.paste(cards[2],(0,H+26)); sheet.paste(cards[3],(W,H+26))
    sheet.thumbnail((1800,1800),Image.Resampling.LANCZOS)
    sheet.save(out/"B_PRODUCTION44_125_COMPARE.jpg",quality=96)

    contacts=[]
    src_rgb=comp(src); clean_rgb=comp(clean); fin_rgb=comp(decoded)
    for row in rows:
        bb=row["original_bbox"]; p=10; cr=(max(0,bb[0]-p),max(0,bb[1]-p),min(W,bb[2]+p),min(H,bb[3]+p))
        ims=[src_rgb.crop(cr),clean_rgb.crop(cr),fin_rgb.crop(cr)]
        ims=[x.resize((x.width*2,x.height*2),Image.Resampling.NEAREST) for x in ims]
        c=Image.new("RGB",(sum(x.width for x in ims)+12,max(x.height for x in ims)+26),"white")
        xx=0
        for im in ims: c.paste(im,(xx,26)); xx+=im.width+6
        ImageDraw.Draw(c).text((4,4),f'{row["n"]} {row["source"]} -> {row["korean"]}',fill="black")
        contacts.append(c)
    cs=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4*(len(contacts)-1)),"white")
    yy=0
    for c in contacts: cs.paste(c,(0,yy)); yy+=c.height+4
    cs.save(out/"B_PRODUCTION44_125_ROW_CONTACT_2X.jpg",quality=96)

    raws=[card("SOURCE_RAW_MIRROR_Y",src_raw),card("FINAL_RAW_MIRROR_Y",decoded_raw)]
    rs=Image.new("RGB",(W,(H+26)*2),"white"); rs.paste(raws[0],(0,0)); rs.paste(raws[1],(0,H+26))
    rs.thumbnail((1200,1800),Image.Resampling.LANCZOS); rs.save(out/"B_PRODUCTION44_125_RAW_COMPARE.jpg",quality=96)

    report={"schema_version":1,"role":"B","run":run,"queue_index":128,"asset":asset,
     "readiness_tier":"RENDER_READY_COMPLETED_SAME_INVOCATION",
     "source_sha256":source_sha_expected,"historical_discovery_sha256":hist_sha_expected,
     "historical_discovery_only":True,"historical_localized_pixels_reused":False,
     "candidate_sha256":cand_sha,"candidate_path":str(candidate.relative_to(repo)),
     "method":"exact original 1024x1024 RGBA32 source -> historical candidate only as region-discovery hint -> source-alpha/effect mask -> alpha-only transparent clean plate with hidden RGB preserved -> fresh native Hangul render -> exact-header raw mirror-Y DDS -> decoded static QA",
     "structure":{"width":W,"height":H,"format":"RGBA32","mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
     "segments_total":7,"rows":rows,
     "policy":{"stage_names":"canonical_phonetic_hangul","song_credit_preserved":"not_applicable","multi_line":"not_applicable"},
     "containment":{"elements_total":7,"elements_pass":7,"changed_pixels_outside_exact_source_bboxes":outside,
                    "alpha_changed_pixels_outside_exact_source_bboxes":alpha_out,"protected_changed_pixels":protected,
                    "source_residue_pixels":residue,"localized_overlap_pairs":overlap_pairs,"status":"PASS"},
     "clean_plate":{"rgb_changed_pixels":0,"source_effect_alpha_cleared":int(np.count_nonzero(all_source_mask)),"status":"PASS"},
     "manual_visual_qa":"PENDING_CONTROLLER_SELF_QA","RUNTIME_VALIDATION":"UNTESTED",
     "status":"B_PRODUCTION44_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"}
    (out/"B_PRODUCTION44_125_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary={"run":run,"asset":"12519155","index":128,"candidate_sha256":cand_sha,"bbox_size_pass":"7/7",
     "outside":outside,"alpha_outside":alpha_out,"protected_changed":protected,"source_residue":residue,
     "localized_overlap_pairs":overlap_pairs,"worker_status":report["status"],"runtime_validation":"UNTESTED",
     "report":"localization/graphics/role_B/20261005-B-PRODUCTION44/B_PRODUCTION44_125_REPORT.json"}
    (wr/"B_PRODUCTION44_12519155.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))

if __name__=="__main__":
    try:
        main()
    except Exception as e:
        import traceback
        repo=Path.cwd()
        run="20261005-B-PRODUCTION44"
        out=repo/"localization/graphics/role_B"/run
        out.mkdir(parents=True,exist_ok=True)
        wr=repo/"localization/graphics/worker_results"
        wr.mkdir(parents=True,exist_ok=True)
        fail={"run":run,"asset":"12519155","index":128,"status":"FAIL_CLOSED_DIAGNOSTIC","exception":repr(e),"traceback":traceback.format_exc(),"RUNTIME_VALIDATION":"UNTESTED"}
        (out/"B_PRODUCTION44_FAIL_CLOSED.json").write_text(json.dumps(fail,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        (wr/"B_PRODUCTION44_12519155_FAIL.json").write_text(json.dumps(fail,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(fail,ensure_ascii=False))
