#!/usr/bin/env python3
"""A215 q121 P0: lossless source-derived atlas change-region evidence, NOT DDS production.

Unlike A212's three-title-only gate, this measures the larger existing translation
footprint and creates independent SOURCE / CLEAN / exact persisted FINAL crops.
The A213 change-component boxes are *inspection aids*, not preapproved text
masks or protected-art exclusion masks. No C approval is inferred from this run.
"""
import hashlib, json, os, struct, tempfile, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

assert os.environ.get("OUTRUN_CPU_WORKER") == "github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE") == "A"
ROOT = Path.cwd()
BASE = ROOT / "localization/graphics/role_A/20261010-A213-Q121-SOURCE-PROTECTION-ROOT-CAUSE"
OUT = ROOT / "localization/graphics/role_A/20261010-A215-Q121-P0-SOURCE-COMPONENT-LOSSLESS"
CANDIDATE = ROOT / "localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
CLEAN = ROOT / "localization/graphics/role_A/20261008-A176-Q121-TRANSPARENT-PLATE/A176_Q121_CLEAN.png"
SOURCE_URL = "https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
SOURCE_SHA = "f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e"
CANDIDATE_SHA = "38d5c2c30ea813202051b191dc01de9d7804e52c1cbab0f46c5372b59ed6c844"
CLEAN_SHA = "88e85995d90b5f590f6ae8da2307cecc90e243da4731850e525ba2c6bbc2eb80"
RUN_KEY = "OUTRUN-KOR-A215-Q121-30-REGION-SOURCE-CLEAN-PERSISTED-20261010-0300"

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def dds_read(path):
    data = Path(path).read_bytes()
    if data[:4] != b"DDS " or len(data) != 128 + 4096*4096*4:
        raise ValueError("q121 DDS native header/data length mismatch")
    h,w = struct.unpack_from("<II",data,12)
    pitch = struct.unpack_from("<I",data,20)[0]
    mip = struct.unpack_from("<I",data,28)[0]
    if (w,h,pitch,mip) != (4096,4096,16384,1):
        raise ValueError(f"unexpected header {w}x{h}, pitch={pitch}, mips={mip}")
    im = Image.frombytes("RGBA",(w,h),data[128:],"raw","RGBA")
    return data[:128], im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

def comp(im, rgb):
    bg=Image.new("RGBA",im.size,(*rgb,255))
    bg.alpha_composite(im)
    return bg.convert("RGB")

def main():
    if sha(CANDIDATE) != CANDIDATE_SHA or sha(CLEAN) != CLEAN_SHA:
        raise ValueError("q121 exact persisted candidate or clean plate changed; abort instead of overwriting")
    old=json.loads((BASE/"A213_P0_ROOT_CAUSE.json").read_text(encoding="utf8"))
    items=old["ranked_components"]
    if len(items) != 30 or old["changed_components_count"] != 179:
        raise ValueError("A213 ranked source component evidence changed")
    with tempfile.TemporaryDirectory(prefix="outrun_a215_q121_") as tmp:
        original=Path(tmp)/"pinned_english.dds"
        urllib.request.urlretrieve(SOURCE_URL, original)
        if sha(original) != SOURCE_SHA:
            raise ValueError("canonical English source SHA mismatch")
        hd, source = dds_read(original)
        hd2, final = dds_read(CANDIDATE)
        if hd != hd2:
            raise ValueError("English DDS and current DDS have mismatched header")
        clean=Image.open(CLEAN).convert("RGBA")
        if clean.size != source.size:
            raise ValueError("CLEAN native size mismatch")
        s,c,f=np.asarray(source),np.asarray(clean),np.asarray(final)
        diff_sc=np.any(s!=c,axis=2)
        diff_sf=np.any(s!=f,axis=2)
        diff_cf=np.any(c!=f,axis=2)
        alpha_sc=s[:,:,3]!=c[:,:,3]
        # A212 title boxes are deliberately not assumed to cover other translated texts.
        report=[]
        OUT.mkdir(parents=True,exist_ok=True)
        for x in items:
            rank=int(x["rank"])
            xa,ya,xb,yb=map(int,x["bbox_readable"])
            # Record the observed region with 12px contextual margin. DO NOT infer text-vs-art
            # purely from spatial connected components; source markup remains a manual requirement.
            box=(max(0,xa-12),max(0,ya-12),min(4096,xb+12),min(4096,yb+12))
            name=f"A215_component_{rank:02d}"
            r0,r1,r2=[im.crop(box) for im in (source,clean,final)]
            for label,im in (("SOURCE",r0),("CLEAN",r1),("FINAL",r2)):
                im.save(OUT/f"{name}_{label}_NATIVE_RGBA.png",compress_level=7)
            # A native composited comparison and two practical-scale checks.
            tiles=[comp(im,(105,105,105)) for im in (r0,r1,r2)]
            gap=8
            contact=Image.new("RGB",(tiles[0].width*3+gap*2,tiles[0].height),(105,105,105))
            for i,t in enumerate(tiles):
                contact.paste(t,(i*(t.width+gap),0))
            contact.save(OUT/f"{name}_SOURCE_CLEAN_FINAL_GRAY_100.jpg",quality=88,optimize=True)
            contact.resize((max(1,contact.width//2),max(1,contact.height//2)),
                           Image.Resampling.LANCZOS).save(
                OUT/f"{name}_SOURCE_CLEAN_FINAL_GRAY_50.jpg",quality=90,optimize=True)
            if rank <= 12:
                # Separate black/white backdrops catch halo/box artifacts hidden by gray.
                for bgcolor,rgb in (("BLACK",(0,0,0)),("WHITE",(255,255,255))):
                    t=[comp(im,rgb) for im in (r0,r1,r2)]
                    view=Image.new("RGB",(t[0].width*3+16,t[0].height),rgb)
                    for i,tile in enumerate(t):view.paste(tile,(i*(tile.width+8),0))
                    view.resize((max(1,view.width//2),max(1,view.height//2)),
                                Image.Resampling.LANCZOS).save(
                        OUT/f"{name}_SOURCE_CLEAN_FINAL_{bgcolor}_50.jpg",
                        quality=88,optimize=True)
            yy0,yy1=4096-box[3],4096-box[1]
            if rank <= 12:
                for label,im in (("SOURCE",source),("CLEAN",clean),("FINAL",final)):
                    im.transpose(Image.Transpose.FLIP_TOP_BOTTOM).crop(
                        (box[0],yy0,box[2],yy1)).save(
                        OUT/f"{name}_{label}_RAW_NATIVE_RGBA.png",compress_level=7)
            sl=np.s_[ya:yb,xa:xb]
            machine={
                "rank":rank,"bbox_readable":list(x["bbox_readable"]),
                "expanded_crop_readable":list(box),
                "A213_component_changed_pixels":int(x["changed_pixels"]),
                "source_clean_RGBA_changes_in_bbox":int(np.count_nonzero(diff_sc[sl])),
                "source_final_RGBA_changes_in_bbox":int(np.count_nonzero(diff_sf[sl])),
                "clean_final_RGBA_changes_in_bbox":int(np.count_nonzero(diff_cf[sl])),
                "source_clean_alpha_changes_in_bbox":int(np.count_nonzero(alpha_sc[sl])),
                "source_alpha_disappeared_in_bbox":int(np.count_nonzero((s[:,:,3][sl]>0)&(f[:,:,3][sl]==0))),
                "source_alpha_appeared_in_bbox":int(np.count_nonzero((s[:,:,3][sl]==0)&(f[:,:,3][sl]>0))),
                "semantic_classification":"UNCLASSIFIED_NEEDS_INDEPENDENT_SOURCE_TEXT_VS_ART_REVIEW",
                "lossless":["SOURCE_NATIVE_RGBA.png","CLEAN_NATIVE_RGBA.png","FINAL_NATIVE_RGBA.png"],
                "gray100":f"{name}_SOURCE_CLEAN_FINAL_GRAY_100.jpg",
                "gray50":f"{name}_SOURCE_CLEAN_FINAL_GRAY_50.jpg",
                "raw_native":rank<=12
            }
            report.append(machine)
        result={
            "run":"A215","run_key":RUN_KEY,"role":"A","priority":"P0","queue_index":121,
            "ingame_reports":["IGR-030","IGR-031","IGR-040"],
            "source_sha256":SOURCE_SHA,"candidate_sha256":CANDIDATE_SHA,"clean_sha256":CLEAN_SHA,
            "source_url":SOURCE_URL,"native":"4096x4096 RGBA32 mip1; persisted FLIP-Y and RAW",
            "A213_components_total":179,"ranked_components_lossless_new":len(report),
            "new_promoted_dds":0,"new_trial_dds":0,"candidate_changed":False,
            "all_atlas_source_clean_RGBA_changed_pixels":int(np.count_nonzero(diff_sc)),
            "all_atlas_source_final_RGBA_changed_pixels":int(np.count_nonzero(diff_sf)),
            "all_atlas_clean_final_RGBA_changed_pixels":int(np.count_nonzero(diff_cf)),
            "all_atlas_source_clean_alpha_changed_pixels":int(np.count_nonzero(alpha_sc)),
            "regions":report,
            "interpretation":"Components are measured from canonical source and CLEAN diff; actual localized segments and protected artwork MUST still be identified manually. Diff-derived boxes do not authorize an edit mask or imply original artwork is protected. This is a producer-native evidence handoff, not material DDS production.",
            "visual_status":"CONTROLLER_NATIVE_REVIEW_PENDING",
            "C1":"C335_HOLD_STRICT_RECHECK_UNCHANGED",
            "C3":"NOT_RUN","approval":"NOT_ISSUED",
            "real_game":"OPEN_USER_INGAME_FAIL",
            "RUNTIME_VALIDATION":"UNTESTED",
            "VR_FFB_DX11_DXVK":"EXCLUDED"
        }
        (OUT/"A215_COMPONENT_QA.json").write_text(
            json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
        print("A215_SOURCE_PROTECTION_HOLD", json.dumps({
            "new_lossless_component_regions":len(report),"current_DDS_changed":False,
            "source_clean_changed":result["all_atlas_source_clean_RGBA_changed_pixels"],
            "clean_final_changed":result["all_atlas_clean_final_RGBA_changed_pixels"]}),flush=True)
if __name__=="__main__":
    main()
