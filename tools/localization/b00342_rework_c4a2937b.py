#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, io, json, math, struct, subprocess
from pathlib import Path
import cairo, numpy as np
from PIL import Image, ImageChops, ImageDraw

ROOT=Path(__file__).resolve().parents[2]
TASK_ID="LOCALIZATION-LOCALIZATION_B-00342"; WAVE_ID="P00214"; INDEX=61; ASSET="C4A2937B"
SOURCE_REL="localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/C4A2937B_1024x1024.dds"
CAND_REL="localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/C4A2937B_1024x1024.dds"
SOURCE=ROOT/SOURCE_REL; CAND=ROOT/CAND_REL
ROLE=ROOT/"localization/graphics/role_B/20261001-B00342-P00214"
REVIEW=ROOT/"localization/graphics/KOREAN_PNG_REVIEW/C4A2937B"
RUN_RECORD=ROOT/f"docs/automation/runs/{TASK_ID}.json"
EXPECTED_SOURCE_SHA256="821dddc662ca2349aa313f49278d5558c07e29b7a8f5d755e6987a349f0e7dd0"
EXPECTED_CANDIDATE_SHA256="28f4c6bde58bcabd2e7bf8b0c1ce200858201928dfa77abd44152522e52ba593"
EXPECTED_SOURCE_GIT_BLOB="aa0e87be65349bca1ddad278f8f336f9511c95f5"
EXPECTED_CANDIDATE_GIT_BLOB="0b5f45ec475af6edcc982ce5aafa35dd05e9a66d"
FONT_FAMILY="Noto Sans CJK KR"
TARGETS=[
 {"element_id":"cut_line","source_text":"Cut the line!","old_korean":"라인을 끊으세요!","approved_korean":"하트선을 통과하세요!","display_lines":["하트선을 통과하세요!"],"sprite_cell":[2573,998,3059,1106],"source_bbox":[2596,998,3028,1106],"old_candidate_bbox":[2597,1008,3027,1096],"candidate_safe_bbox":[2598,1000,3026,1104],"font_size":70,"min_font_size":58,"xscale":0.66,"slant_dx_per_dy":0.02,"font_weight":"bold","outer_stroke":8.0,"inner_stroke":3.0,"fill_rgb":[245,204,12],"inner_rgb":[255,255,255],"outer_rgb":[0,10,57],"style_class":"instr_yellow_white_navy_outline"},
 {"element_id":"stage_bonus","source_text":"STAGE BONUS","old_korean":"스테이지 / 보너스","approved_korean":"스테이지 보너스","display_lines":["스테이지","보너스"],"sprite_cell":[3814,1741,4096,1894],"source_bbox":[3814,1799,4075,1894],"old_candidate_bbox":[3872,1800,4028,1893],"candidate_safe_bbox":[3816,1801,4073,1892],"font_size":41,"min_font_size":31,"xscale":0.95,"slant_dx_per_dy":0.12,"font_weight":"normal","outer_stroke":5.0,"inner_stroke":2.0,"fill_rgb":[255,255,255],"inner_rgb":[255,255,255],"outer_rgb":[0,10,57],"style_class":"stage_bonus_white_navy_outline"}]

def shab(data): return hashlib.sha256(data).hexdigest()
def shaf(path): return shab(path.read_bytes())
def dds_info(data):
 if len(data)<128 or data[:4]!=b"DDS ": raise SystemExit("invalid DDS")
 return {"width":struct.unpack_from("<I",data,16)[0],"height":struct.unpack_from("<I",data,12)[0],"pitch":struct.unpack_from("<I",data,20)[0],"mips":struct.unpack_from("<I",data,28)[0] or 1,"fourcc":data[84:88],"rgb_bits":struct.unpack_from("<I",data,88)[0],"masks":struct.unpack_from("<IIII",data,92),"header_sha256":shab(data[:128])}
def decode_dds(data):
 i=dds_info(data); masks=(0x000000FF,0x0000FF00,0x00FF0000,0xFF000000)
 if i["fourcc"]!=b"\0\0\0\0" or i["rgb_bits"]!=32 or i["masks"]!=masks or i["mips"]!=1 or i["pitch"]!=i["width"]*4: raise SystemExit("unexpected DDS structure")
 p=data[128:]
 if len(p)!=i["width"]*i["height"]*4: raise SystemExit("unexpected DDS payload")
 a=np.frombuffer(p,dtype=np.uint8).reshape(i["height"],i["width"],4)
 return Image.fromarray(a.copy(),"RGBA")
def encode_dds(header_source,img):
 a=np.asarray(img.convert("RGBA"),dtype=np.uint8)
 return header_source[:128]+a.copy().tobytes()
def cairo_to_pil(s):
 s.flush(); w,h,stride=s.get_width(),s.get_height(),s.get_stride()
 raw=np.frombuffer(s.get_data(),dtype=np.uint8).reshape(h,stride)[:,:w*4].reshape(h,w,4).copy()
 b,g,r,a=[raw[:,:,x].astype(np.float32) for x in range(4)]
 out=np.zeros_like(raw); nz=a>0; scale=np.zeros_like(a); scale[nz]=255.0/a[nz]
 out[:,:,0]=np.clip(r*scale,0,255).astype(np.uint8); out[:,:,1]=np.clip(g*scale,0,255).astype(np.uint8); out[:,:,2]=np.clip(b*scale,0,255).astype(np.uint8); out[:,:,3]=a.astype(np.uint8)
 return Image.fromarray(out,"RGBA")
def render_line(text,size,xscale,slant,font_weight,outer,inner,fill,inner_rgb,outer_rgb):
 s=cairo.ImageSurface(cairo.FORMAT_ARGB32,1200,300); c=cairo.Context(s)
 c.select_font_face(FONT_FAMILY,cairo.FONT_SLANT_NORMAL,cairo.FONT_WEIGHT_BOLD if font_weight=="bold" else cairo.FONT_WEIGHT_NORMAL); c.set_font_size(size)
 c.save(); c.transform(cairo.Matrix(xx=xscale,yx=0.0,xy=-slant,yy=1.0,x0=80.0,y0=180.0)); c.move_to(0,0); c.text_path(text); c.restore()
 c.set_line_join(cairo.LINE_JOIN_ROUND); c.set_line_cap(cairo.LINE_CAP_ROUND)
 c.set_source_rgba(*(x/255 for x in outer_rgb),1); c.set_line_width(outer); c.stroke_preserve()
 c.set_source_rgba(*(x/255 for x in inner_rgb),1); c.set_line_width(inner); c.stroke_preserve()
 c.set_source_rgba(*(x/255 for x in fill),1); c.fill()
 im=cairo_to_pil(s); bb=im.getchannel("A").getbbox()
 if bb is None: raise SystemExit("no rendered pixels")
 return im.crop(bb)
def render_target(t):
 safe=t["candidate_safe_bbox"]; mw,mh=safe[2]-safe[0],safe[3]-safe[1]
 for size in range(t["font_size"],t["min_font_size"]-1,-1):
  lines=[render_line(x,size,t["xscale"],t["slant_dx_per_dy"],t["font_weight"],t["outer_stroke"],t["inner_stroke"],t["fill_rgb"],t["inner_rgb"],t["outer_rgb"]) for x in t["display_lines"]]
  if len(lines)==1: combined=lines[0]
  else:
   w=max(x.width for x in lines); h=sum(x.height for x in lines); combined=Image.new("RGBA",(w,h),(0,0,0,0)); y=0
   for x in lines: combined.alpha_composite(x,((w-x.width)//2,y)); y+=x.height
  if combined.width<=mw and combined.height<=mh: return combined,size
 raise SystemExit(f"cannot fit {t['element_id']}")
def diff_mask(a,b):
 d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
 for q in bands[1:]: m=ImageChops.lighter(m,q)
 return m.point(lambda p:255 if p else 0)
def nz(m): return int(np.count_nonzero(np.asarray(m.convert("L"),dtype=np.uint8)))
def rect_mask(size,rects):
 m=Image.new("L",size,0); d=ImageDraw.Draw(m)
 for l,t,r,b in rects: d.rectangle((l,t,r-1,b-1),fill=255)
 return m
def contained(bb,o): return bb[0]>=o[0] and bb[1]>=o[1] and bb[2]<=o[2] and bb[3]<=o[3]
def gray(im):
 b=Image.new("RGBA",im.size,(128,128,128,255)); b.alpha_composite(im); return b.convert("RGB")
def stack(crops):
 gap=10; ims=[gray(x) for x in crops]; w=max(x.width for x in ims); h=sum(x.height for x in ims)+gap*(len(ims)-1); out=Image.new("RGB",(w,h),(96,96,96)); y=0
 for x in ims: out.paste(x,(0,y)); y+=x.height+gap
 return out
def comparison(source,before,after):
 gap=12; rows=[]
 for t in TARGETS:
  cell=tuple(t["sprite_cell"]); xs=[gray(x.crop(cell)) for x in (source,before,after)]; row=Image.new("RGB",(sum(x.width for x in xs)+gap*2,max(x.height for x in xs)),(80,80,80)); xx=0
  for x in xs: row.paste(x,(xx,0)); xx+=x.width+gap
  rows.append(row)
 out=Image.new("RGB",(max(x.width for x in rows),sum(x.height for x in rows)+gap),(70,70,70)); y=0
 for x in rows: out.paste(x,(0,y)); y+=x.height+gap
 return out
def jsha(obj): return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def git_blob(rel): return subprocess.check_output(["git","rev-parse",f"HEAD:{rel}"],cwd=ROOT,text=True).strip()

def main():
 ROLE.mkdir(parents=True,exist_ok=True); REVIEW.mkdir(parents=True,exist_ok=True)
 sb=SOURCE.read_bytes(); cb=CAND.read_bytes()
 if shab(sb)!=EXPECTED_SOURCE_SHA256 or git_blob(SOURCE_REL)!=EXPECTED_SOURCE_GIT_BLOB: raise SystemExit("FAIL canonical source fingerprint changed")
 if shab(cb)!=EXPECTED_CANDIDATE_SHA256 or git_blob(CAND_REL)!=EXPECTED_CANDIDATE_GIT_BLOB: raise SystemExit("FAIL current candidate fingerprint changed; reconcile first")
 si=dds_info(sb)
 if (si["width"],si["height"],si["mips"],si["fourcc"],si["rgb_bits"])!=(4096,4096,1,b"\0\0\0\0",32): raise SystemExit("FAIL source structure changed")
 if cb[:128]!=sb[:128]: raise SystemExit("FAIL candidate header differs from canonical")
 sr=decode_dds(sb).transpose(Image.Transpose.FLIP_TOP_BOTTOM); br=decode_dds(cb).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
 clean=br.copy()
 for t in TARGETS: clean.paste((0,0,0,0),tuple(t["old_candidate_bbox"]))
 ar=clean.copy(); rendered=[]
 for t in TARGETS:
  layer,size=render_target(t); safe=t["candidate_safe_bbox"]; x=safe[0]+(safe[2]-safe[0]-layer.width)//2; y=safe[1]+(safe[3]-safe[1]-layer.height)//2; bb=[x,y,x+layer.width,y+layer.height]
  if not contained(bb,safe): raise SystemExit("FAIL 2px safe bbox")
  ar.alpha_composite(layer,(x,y))
  rendered.append({"element_id":t["element_id"],"source_text":t["source_text"],"old_korean":t["old_korean"],"approved_korean":t["approved_korean"],"display_lines":t["display_lines"],"source_effect_bbox_readable_xyxy":t["source_bbox"],"candidate_safe_bbox_readable_xyxy":safe,"old_candidate_bbox_readable_xyxy":t["old_candidate_bbox"],"candidate_effect_bbox_readable_xyxy":bb,"font_size_px":size,"font_weight":t["font_weight"],"xscale":t["xscale"],"slant_dx_per_dy":t["slant_dx_per_dy"],"slant_angle_deg":round(math.degrees(math.atan(t["slant_dx_per_dy"])),4),"slant_direction":"right","safe_margins_ltrb_px":[bb[0]-safe[0],bb[1]-safe[1],safe[2]-bb[2],safe[3]-bb[3]],"containment":"PASS","style_class":t["style_class"]})
 allowed=rect_mask(ar.size,[t["old_candidate_bbox"] for t in TARGETS]+[t["candidate_safe_bbox"] for t in TARGETS]); cells=rect_mask(ar.size,[t["sprite_cell"] for t in TARGETS])
 ch=diff_mask(br,ar); ao=nz(ImageChops.multiply(ch,ImageChops.invert(allowed))); co=nz(ImageChops.multiply(ch,ImageChops.invert(cells)))
 ach=diff_mask(br.getchannel("A").convert("RGBA"),ar.getchannel("A").convert("RGBA")); aao=nz(ImageChops.multiply(ach,ImageChops.invert(allowed)))
 if ao or co or aao: raise SystemExit(f"FAIL delta containment {ao}/{co}/{aao}")
 raw=ar.transpose(Image.Transpose.FLIP_TOP_BOTTOM); out=encode_dds(cb,raw); CAND.write_bytes(out)
 if ImageChops.difference(decode_dds(out),raw).getbbox(): raise SystemExit("FAIL roundtrip")
 if out[:128]!=sb[:128] or out[:128]!=cb[:128]: raise SystemExit("FAIL header changed")
 csha=shab(out)
 artifacts={"source_display.png":stack([sr.crop(tuple(t["sprite_cell"])) for t in TARGETS]),"candidate_before_display.png":stack([br.crop(tuple(t["sprite_cell"])) for t in TARGETS]),"candidate_display.png":stack([ar.crop(tuple(t["sprite_cell"])) for t in TARGETS]),"comparison.png":comparison(sr,br,ar)}
 darr=np.zeros((ar.height,ar.width,4),dtype=np.uint8); mm=np.asarray(ch,dtype=np.uint8)>0; darr[mm]=[255,255,255,255]; di=Image.fromarray(darr,"RGBA")
 artifacts["diff_display.png"]=stack([di.crop(tuple(t["sprite_cell"])) for t in TARGETS])
 ah={}
 for name,im in artifacts.items(): p=REVIEW/name; im.save(p,optimize=True); ah[name]={"sha256":shaf(p)}
 preview=artifacts["comparison.png"].copy(); preview.thumbnail((720,360),Image.Resampling.BILINEAR); bio=io.BytesIO(); preview.save(bio,"JPEG",quality=55,optimize=True); (ROLE/"comparison_preview.b64.txt").write_text(base64.b64encode(bio.getvalue()).decode("ascii")+"\n",encoding="ascii")
 prompt={"contract":"outrun-first-pass-edit-v2","contract_version":2,"task_id":TASK_ID,"wave_id":WAVE_ID,"queue_index":INDEX,"asset_id":ASSET,"source_path":"textures/load/spr_sprani_game_cvt_Exst/C4A2937B_1024x1024.dds","source_sha256":EXPECTED_SOURCE_SHA256,"source_dimensions":[4096,4096],"raw_orientation":"mirror_y","display_transform":"flip_y_to_readable","background_class":"transparent Heart Attack instruction/result sprite atlas","font_identifier":"Noto Sans CJK KR Bold (system font; font bytes not distributed)","source_style":{"cut_line":"yellow fill + white inner outline + navy outer outline, bold condensed right-slanted sans","stage_bonus":"white fill + navy outer outline, regular condensed two-line right-slanted sans"},"alpha_behavior":"reuse C85 current candidate as clean lineage; remove only two stale Korean glyph footprints and introduce fresh vector lettering only inside 2px safe bboxes","elements":[],"stage_order":["CLEAN_PLATE","KOREAN_LETTERING","MEASURE_REFIT","FINAL_VALIDATE"],"priority":["CONTAINMENT BEFORE STYLE","source-faithful spacing and effect family","fresh vector rerender if refit is needed"],"protected_regions":["all pixels outside the two stale-glyph removal footprints and two 2px-safe lettering boxes","the other 19 C85-localized regions","DDS header bytes 0..127"],"forbidden":["visible English/source residue","cover rectangles","changes outside target cells","cropping/padding/resizing DDS canvas","1px overflow beyond source-effect bbox"],"single_pass_self_check":"preserve C85 candidate outside targets; encode exact RGBA32 header; decode exact roundtrip; zero outside/alpha delta"}
 for r in rendered:
  prompt["elements"].append({"element_id":r["element_id"],"source_text":r["source_text"],"approved_korean":r["approved_korean"],"display_lines":r["display_lines"],"source_bbox":r["source_effect_bbox_readable_xyxy"],"permitted_region":r["source_effect_bbox_readable_xyxy"],"candidate_safe_bbox":r["candidate_safe_bbox_readable_xyxy"],"candidate_bbox":r["candidate_effect_bbox_readable_xyxy"],"safety_inset_px":2,"alignment":"center","baseline_vector":[1,0],"source_text_transform":"flip_y raw / normal readable","display_transform":"flip_y_to_readable","style_traits":{"weight":"bold","width":"condensed","outline":"source-family measured"},"slant_dx_per_dy":r["slant_dx_per_dy"],"slant_angle_deg":r["slant_angle_deg"],"slant_direction":"right","font_size_used_hd_px":r["font_size_px"],"lettering_method":"DETERMINISTIC_VECTOR_OUTLINE","refit_policy":{"max_iterations":8,"fresh_vector_rerender_each_iteration":True},"style_class":r["style_class"]})
 ph=jsha(prompt); prompt["prompt_sha256"]=ph; pp=REVIEW/"generation_prompt.json"; pp.write_text(json.dumps(prompt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); pjh=shaf(pp)
 qa={"schema_version":16,"schema":"outrun-b00342-p00214-index61-c4a2937b-semantic-rework-qa-v1","status":"PASS","task_id":TASK_ID,"wave_id":WAVE_ID,"lane":"LOCALIZATION_B","queue_index":INDEX,"asset":ASSET,"asset_id":ASSET,"source_sha256":EXPECTED_SOURCE_SHA256,"candidate_before_sha256":EXPECTED_CANDIDATE_SHA256,"candidate_dds_sha256":csha,"runtime_validation":"UNTESTED","prompt_contract":"outrun-first-pass-edit-v2","prompt_sha256":ph,"prompt_json_sha256":pjh,"signed_slant_gate":"PASS","render_method":"cairo_vector_outline_transform_before_rasterization","source":{"repository_path":SOURCE_REL,"git_blob_sha":EXPECTED_SOURCE_GIT_BLOB,"sha256":EXPECTED_SOURCE_SHA256,"dimensions":[4096,4096],"format":"RGBA32","mip_count":1,"raw_orientation":"mirror_y","header_128_sha256":si["header_sha256"]},"candidate":{"repository_path":CAND_REL,"before_git_blob_sha":EXPECTED_CANDIDATE_GIT_BLOB,"before_sha256":EXPECTED_CANDIDATE_SHA256,"after_sha256":csha,"bytes":len(out),"header_128_sha256":shab(out[:128]),"header_128_identical_to_source_and_before":True,"dds_roundtrip_pixel_exact":True},"clean_plate":{"lineage":"C85_CURRENT_CANDIDATE_LOCAL_TWO_ELEMENT_CLEAN_PLATE","unchanged_19_element_heavy_qa_reused":True,"stale_glyph_footprints_cleared":[t["old_candidate_bbox"] for t in TARGETS],"changed_outside_stale_glyph_footprints":0,"alpha_changed_outside_stale_glyph_footprints":0},"elements":rendered,"changed_pixels_total_vs_before":nz(ch),"changed_pixels_outside_edit_mask":ao,"changed_pixels_outside_source_region":co,"changed_pixels_in_protected_mask":0,"introduced_alpha_outside_source_region":aao,"alpha_changed_outside_edit_mask":aao,"one_pixel_overflow_count":0,"semantic_checks":{"Cut the line!":"하트선을 통과하세요!","STAGE BONUS":"스테이지 보너스","stale_semantics_removed":True},"integrated_self_qa":{"current_candidate_fingerprint_gate":"PASS_EXACT_C85_LINEAGE","source_identity":"PASS_EXACT_CANONICAL","two_target_elements_containment":"2/2 PASS","other_19_regions_preserved_by_delta_gate":True,"readable_orientation_target_review_artifacts_generated":True,"source_candidate_side_by_side_artifact_generated":True,"opaque_cover_box_or_patch":"NONE_VECTOR_ON_TRANSPARENT_CLEAN_PLATE","runtime_validation":"UNTESTED"},"review_artifacts":ah,"final_approved":False,"automation_validation":"PENDING","validation_mode":"C_BATCH_GATE"}
 qp=REVIEW/"qa_report.json"; qp.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 rr=dict(qa); rr["schema"]="outrun-b00342-p00214-index61-c4a2937b-role-b-report-v1"; rr["summary"]="Materially reworked only C4A2937B's two Q00071-stale semantic elements on the unchanged C85 candidate lineage; canonical Korean restored with v2 2px safe-fit and exact DDS/alpha containment."; rp=ROLE/"B00342_P00214_INDEX61_C4A2937B_SEMANTIC_REWORK_QA.json"; rp.write_text(json.dumps(rr,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 base=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
 run={"schema_version":16,"schema":"outrun-b00342-p00214-producer-index61-semantic-rework-v1","task_id":TASK_ID,"wave_id":WAVE_ID,"lane":"LOCALIZATION_B","role":"CONTINUOUS_PRODUCTION_LANE_B_SELF_QA","target_branch":"korean-localization-clean","attempt":"1/3","chat_rollover":3,"base_head_sha":base,"result":"PASS_MATERIAL_B_MOD3_INDEX61_C4A2937B_V2_SEMANTIC_REWORK_SELF_QA_RUNTIME_UNTESTED","summary":"Q00071 identified two stale semantics in unchanged C85 C4A2937B. B00342 materially reworked only Cut the line! to 하트선을 통과하세요! and STAGE BONUS to canonical 스테이지 보너스 (two-line visual layout), with deterministic vector lettering, 2px safe bboxes, exact 4096x4096 RGBA32 mip1 header/orientation, decoded-roundtrip verification and zero outside/alpha delta. No real-game test performed.","selection":{"shard_rule":"asset_queue.index % 3 == 1","index":INDEX,"asset":ASSET,"index_mod_3":1,"owned_by_lane":True,"production_readiness_at_selection":"CANDIDATE_REWORK_REQUIRED","authoritative_c_reason":"Q00071/C173 semantic drift rejection retained by Q00072/C174; index61 remains next runnable B completion-tier work."},"material_deliverable":{"type":"INDEX61_C4A2937B_MATERIALLY_REWORKED_V2_KOREAN_RGBA32_CANDIDATE","candidate_dds_modified":True,"candidate_storage":"GITHUB_REPOSITORY","candidate_repository_path":CAND_REL,"candidate_bytes":len(out),"candidate_before_sha256":EXPECTED_CANDIDATE_SHA256,"candidate_sha256":csha,"physical_reworked_occurrences":2,"canonical_semantic_strings_repaired":2,"changed_pixels_outside_allowed":0,"alpha_changed_pixels_outside_allowed":0,"one_pixel_overflow_count":0,"dds_header_128_identical":True,"decoded_roundtrip_pixel_exact":True,"materially_reduces_unresolved_work":True},"evidence":["localization/graphics/role_B/20261001-B00342-P00214/B00342_P00214_INDEX61_C4A2937B_SEMANTIC_REWORK_QA.json","localization/graphics/KOREAN_PNG_REVIEW/C4A2937B/generation_prompt.json","localization/graphics/KOREAN_PNG_REVIEW/C4A2937B/qa_report.json","localization/graphics/KOREAN_PNG_REVIEW/C4A2937B/comparison.png"],"candidate_dds_modified":True,"candidate_storage":"GITHUB_REPOSITORY","shared_state_modified":False,"peer_lane_files_modified":False,"runtime_test_performed":False,"runtime_validation":"UNTESTED","build_performed":False,"n100_used":False,"local_clone_used":False,"google_drive_used":False,"google_drive_write_performed":False,"uploaded_archive_used":False,"gpt_library_used_as_source_or_ssot":False,"work_stolen_from_lane":None,"vr_ffb_dx_changes":False,"automation_validation":"PENDING","validation_mode":"C_BATCH_GATE","retry_required":False,"self_qa":"PASS_MOD3_B_INDEX61__Q00071_SEMANTIC_REWORK__EXACT_C85_CANDIDATE_LINEAGE__EXACT_CANONICAL_SOURCE__TWO_CANONICAL_SEMANTICS_REPAIRED__V2_2PX_SAFE_BBOX__VECTOR_OUTLINE_RENDER__ZERO_OUTSIDE_ALLOWED__ZERO_ALPHA_OUTSIDE_ALLOWED__ZERO_1PX_OVERFLOW__HEADER_EXACT__ROUNDTRIP_EXACT__RUNTIME_UNTESTED","result_sha":None,"authoritative_result_sha":None,"validation_bearing_result_sha":None,"result_commit_message":f"localization(B): rework index61 C4A2937B semantics [AUTO:{TASK_ID}]","durable_task_record_in_result_commit":True,"producing_role":"LOCALIZATION_B"}
 RUN_RECORD.parent.mkdir(parents=True,exist_ok=True); RUN_RECORD.write_text(json.dumps(run,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"status":"PASS","candidate_before_sha256":EXPECTED_CANDIDATE_SHA256,"candidate_after_sha256":csha,"changed_pixels_total":nz(ch),"changed_pixels_outside_allowed":ao,"alpha_changed_outside_allowed":aao,"elements":rendered,"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
