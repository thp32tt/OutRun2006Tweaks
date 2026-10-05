#!/usr/bin/env python3
import hashlib,json,os,shutil,struct,urllib.request,subprocess
from pathlib import Path

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd()
run="20261006-B-PRODUCTION173-JENN-ALIAS"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)

src_rel="textures/load/spr_sprani_JENN_RANK_Exst/6AB5CEE_1024x1024.dds"
alias_candidate=repo/"localization/graphics/hd_candidates"/src_rel
approved_rel="textures/load/spr_sprani_JENN_RANK_Exst/06AB5CEE_1024x1024.dds"
approved_candidate=repo/"localization/graphics/hd_candidates"/approved_rel
c215_report=repo/"localization/graphics/role_C/20261006-C215-06AB5CEE/C215_06AB5CEE_CONTROLLER_FINAL_QA.json"
inventory=repo/"localization/graphics/inventory.csv"

APPROVED_CANDIDATE_SHA="0b430a505c28b496fa2294326ac9dbc41821e5ddac5b830d348e11d1b67c39e5"
CANONICAL_SOURCE_SHA="cd6f58f1fa187c6ff7813cbb42b5181038712d8142bf575711a30d69e76d2f4a"
RECOVERED_LOWRES_SHA="c45f8592260ad9f1d077b54f17c3d71a9b210081e7ab4c0114aa8368908d109b"
UPSTREAM="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_JENN_RANK_Exst/6AB5CEE_1024x1024.dds"

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def dds_meta(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError(("not_dds",str(p)))
    h=struct.unpack_from("<I",b,12)[0]
    w=struct.unpack_from("<I",b,16)[0]
    pitch=struct.unpack_from("<I",b,20)[0]
    mips=struct.unpack_from("<I",b,28)[0]
    pf_flags=struct.unpack_from("<I",b,80)[0]
    fourcc=b[84:88].hex()
    bpp=struct.unpack_from("<I",b,88)[0]
    masks=[hex(x) for x in struct.unpack_from("<IIII",b,92)]
    return {"width":w,"height":h,"pitch":pitch,"mips":mips,"pf_flags":pf_flags,"fourcc":fourcc,"bpp":bpp,"masks":masks,"bytes":len(b)}

if not approved_candidate.exists() or sha(approved_candidate)!=APPROVED_CANDIDATE_SHA:
    raise RuntimeError(("approved candidate drift",sha(approved_candidate) if approved_candidate.exists() else None))
c215=json.loads(c215_report.read_text(encoding="utf-8"))
if c215.get("candidate_sha256")!=APPROVED_CANDIDATE_SHA or c215.get("source_sha256")!=CANONICAL_SOURCE_SHA:
    raise RuntimeError(("C215 provenance drift",c215.get("candidate_sha256"),c215.get("source_sha256")))
if c215.get("decision")!="C215_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME":
    raise RuntimeError(("C215 approval drift",c215.get("decision")))

inv=inventory.read_text(encoding="utf-8")
expected_low=f"{src_rel},{RECOVERED_LOWRES_SHA},1024,1024,RGBA,language_specific,inspect,unknown,,"
expected_hd=f"{approved_rel},e02db9b4e04747e2a74295e8f5a01e07f0ed88d31832f4169b1e5996bc30f1eb,4096,4096,RGBA,language_specific,inspect,unknown,,"
if expected_low not in inv or expected_hd not in inv:
    raise RuntimeError("inventory alias evidence drift")
if int("06AB5CEE",16)!=int("6AB5CEE",16):
    raise RuntimeError("numeric texture hash alias check failed")

tmp=Path("/tmp/B173_6AB5CEE_HD_SOURCE.dds")
urllib.request.urlretrieve(UPSTREAM,tmp)
if sha(tmp)!=CANONICAL_SOURCE_SHA:
    raise RuntimeError(("canonical source drift",sha(tmp)))
source_meta=dds_meta(tmp)
approved_meta=dds_meta(approved_candidate)
if source_meta!=approved_meta:
    raise RuntimeError(("structure mismatch source vs approved candidate",source_meta,approved_meta))
if source_meta["width"]!=4096 or source_meta["height"]!=4096 or source_meta["mips"]!=1 or source_meta["bpp"]!=32:
    raise RuntimeError(("unexpected canonical structure",source_meta))

alias_candidate.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(approved_candidate,alias_candidate)
alias_sha=sha(alias_candidate)
if alias_sha!=APPROVED_CANDIDATE_SHA:
    raise RuntimeError(("alias copy drift",alias_sha))
if dds_meta(alias_candidate)!=source_meta:
    raise RuntimeError("alias structure mismatch")

report={
  "schema_version":1,
  "role":"B",
  "run":run,
  "base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
  "queue_index":38,
  "asset":src_rel,
  "prior_action":"zoom_review",
  "readiness_tier":"ZOOM_REVIEW_EXACT_CANONICAL_ALIAS_OF_C215_APPROVED_TEXTURE",
  "classification":{
    "result":"LOCALIZABLE_EXACT_ALIAS",
    "source":"Total Rank x3",
    "korean":"종합 랭킹",
    "numeric_texture_hash":"0x06AB5CEE",
    "leading_zero_alias":{"index36":"06AB5CEE","index38":"6AB5CEE","numeric_equal":True},
    "reason":"Index38 recovered source is the 1024x1024 low-resolution form, while the HD baseline resolves to the exact same canonical upstream 6AB5CEE payload already used and independently C-approved for index36."
  },
  "provenance":{
    "recovered_index38_inventory_sha256":RECOVERED_LOWRES_SHA,
    "recovered_index38_dimensions":[1024,1024],
    "canonical_hd_url":UPSTREAM,
    "canonical_hd_sha256":CANONICAL_SOURCE_SHA,
    "canonical_hd_dimensions":[source_meta["width"],source_meta["height"]],
    "approved_index36_candidate":approved_rel,
    "approved_index36_candidate_sha256":APPROVED_CANDIDATE_SHA,
    "c215_report":str(c215_report.relative_to(repo)),
    "c215_decision":c215["decision"]
  },
  "production":{
    "method":"byte-exact deployable alias copy of independently C215-approved canonical-HD candidate; no low-resolution Korean bitmap or recovered 1024x1024 raster is reused/upscaled",
    "candidate_path":str(alias_candidate.relative_to(repo)),
    "candidate_sha256":alias_sha,
    "candidate_byte_exact_to_c215":True,
    "new_rasterization":False,
    "reason_no_rerender":"canonical source SHA and localized candidate bytes are identical to C215-approved index36 texture identity; rerendering would duplicate completed work and risk environment-dependent pixel drift"
  },
  "structure":{**source_meta,"header_and_payload_candidate_byte_exact_to_c215":True,"raw_orientation":"mirror_y"},
  "transferred_static_qa":{
    "basis":"exact canonical source SHA + exact localized candidate SHA + exact DDS structure",
    "bbox_size_positive_margin":"3/3 PASS via C215",
    "decoded_changed_outside_union_source_bboxes":0,
    "alpha_changed_outside_union_source_bboxes":0,
    "introduced_visible_outside_union_source_bboxes":0,
    "unsafe_target_template_variant_pixels":0,
    "localized_bbox_mismatches":0,
    "controller_visual_qa_reference":"C215 PASS SOURCE/CLEAN/FINAL + raw mirror_y"
  },
  "worker_status":"PASS",
  "controller_self_qa":"PENDING_CONTROLLER_EXACT_SHA_REUSE_REVIEW",
  "runtime_validation":"UNTESTED",
  "status":"B173_ALIAS_CANDIDATE_PASS_PENDING_CONTROLLER_RECONCILE",
  "no_vr_ffb_dx11_dxvk_work":True
}
(out/"B173_6AB5CEE_ALIAS_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(repo/"localization/graphics/worker_results/B173_6AB5CEE.json").write_text(json.dumps({
 "role":"B","run":run,"queue_index":38,"asset":"6AB5CEE","candidate_sha256":alias_sha,
 "canonical_source_sha256":CANONICAL_SOURCE_SHA,
 "exact_alias_of_queue_index":36,"exact_alias_candidate_sha256":APPROVED_CANDIDATE_SHA,
 "report":str((out/"B173_6AB5CEE_ALIAS_REPORT.json").relative_to(repo)),
 "status":"WORKER_PASS_PENDING_CONTROLLER_RECONCILE"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("B173_DONE",alias_sha,source_meta)
