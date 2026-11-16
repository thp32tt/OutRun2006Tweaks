#!/usr/bin/env python3
"""Run native strict DDS QA on only exact 8 staged source-owner A/B test edits.

This checks the real multi-ROI atlas assembler; isolated canaries are not a
substitute for other labels in the same source DDS. Does NOT issue C1/C3 PASS.
"""
import argparse,hashlib,json,zipfile
from collections import Counter,defaultdict
from pathlib import Path
from github_ab_imagegen_atlas_batch import (
    CROSS,ORIGINAL,SOURCE_PLAN,load_cross,load_pinned_orientations,
    apply_c1_preliminary_overrides,process_strict_with_bc3_quarantine,sha)
from hd_bc3_source_owner_import import BASE,apply_test_only_source_owner_overrides

def run(root,out):
    root,out=Path(root),Path(out)
    out.mkdir(parents=True,exist_ok=True)
    groups=load_cross(root/CROSS)
    orientation=load_pinned_orientations(root,groups)
    expected={}
    for file in sorted((root/BASE).glob("Q*.json")):
        r=json.loads(file.read_text(encoding="utf-8"))
        expected[r["roi_id"]]=r["source_dds_path"]
    if len(expected)!=8:
        raise ValueError("EIGHT_SOURCE_PINNED_TEST_ONLY_ROIS_REQUIRED")
    imported=apply_test_only_source_owner_overrides(root,groups)
    if imported!=8:
        raise ValueError("EXPECTED_EIGHT_SHA_PINNED_A_B_OVERRIDES")
    targets=defaultdict(list)
    for rid,target in expected.items():
        targets[target].append(rid)
    reports=[]
    for target,ids in sorted(targets.items()):
        path=root/ORIGINAL/target
        if path.is_symlink() or not path.is_file():
            raise ValueError("PINNED_SOURCE_DDS_NOT_AVAILABLE:"+target)
        rows=groups[target]
        raw=path.read_bytes()
        if len({r["source_dds_sha256"] for r in rows})!=1 or sha(raw)!=rows[0]["source_dds_sha256"]:
            raise ValueError("PINNED_SOURCE_DDS_SHA_CHANGED:"+target)
        report={"source_dds_path":target,
                "source_dds_sha256":sha(raw),
                "source_orientation":orientation[target],
                "targeted_source_owner_roi_ids":sorted(ids)}
        try:
            native,readable,clean,painted,holds=process_strict_with_bc3_quarantine(
                raw,rows,root,orientation[target])
            pids={item["roi_id"] for item in painted}
            by_hold={item["roi_id"]:item["reason"] for item in holds}
            report["atlas_native_test_dds_created"]=native is not None
            if native is not None:
                if native[:128]!=raw[:128] or len(native)!=len(raw) or native==raw:
                    raise ValueError("TEST_ONLY_DDS_HEADER_OR_SOURCE_NOOP")
                save=out/"native_dds_TEST_ONLY"/target
                save.parent.mkdir(parents=True,exist_ok=True)
                save.write_bytes(native)
                report["native_test_dds_sha256"]=sha(native)
                report["native_test_dds_artifact_path"]=str(save.relative_to(out))
            report["all_other_rows"]=len(rows)-len(ids)
            report["all_painted_on_atlas"]=len(painted)
            report["all_holds_on_atlas"]=len(holds)
            report["tested_original_owner_results"]=[
                {"roi_id":rid,"result":"NATIVE_DDS_TEST_ONLY_PAINTED"
                 if rid in pids else "HOLD_"+by_hold.get(rid,"UNKNOWN")}
                for rid in sorted(ids)]
            report["remaining_atlas_holds_sample"]=[
                {"roi_id":x["roi_id"],"reason":x["reason"]}
                for x in holds[:12]]
        except (ValueError,OSError,OverflowError) as exc:
            report["atlas_error"]=str(exc).split(":",1)[0][:140]
            report["tested_original_owner_results"]=[
                {"roi_id":rid,"result":"HOLD_ATLAS_"+report["atlas_error"]}
                for rid in sorted(ids)]
        reports.append(report)
        print(json.dumps({"dds":target,"outcomes":report["tested_original_owner_results"]},ensure_ascii=False))
    statuses=Counter(
        z["result"] for a in reports for z in a["tested_original_owner_results"])
    result={"schema":"outrun-hd-eight-native-source-owner-strict-qa-v1",
            "source_roi":954,"source_holds_previous":640,
            "source_owner_test_png_imported":imported,
            "targeted_roi_count":len(expected),
            "test_dds_roi_painted":statuses["NATIVE_DDS_TEST_ONLY_PAINTED"],
            "targeted_result_counts":dict(sorted(statuses.items())),
            "source_atlas_count":len(targets),
            "release_approved":False,
            "independent_c1_c3":"UNTESTED",
            "game_test":"UNTESTED",
            "machine_only_no_final_hold_change":True,
            "atlases":reports}
    result["native_dds_test_only_files"]=sum(
        "native_test_dds_artifact_path" in a for a in reports)
    (out/"native_8_targeted_results.json").write_text(
       json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    pack=out/"OUTRUN_HD_EIGHT_SOURCE_OWNER_NATIVE_QA_TEST_ONLY.zip"
    with zipfile.ZipFile(pack,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=4) as archive:
        manifest=out/"native_8_targeted_results.json"
        archive.write(manifest,arcname=manifest.name)
        for a in reports:
            rel=a.get("native_test_dds_artifact_path")
            if rel:
                archive.write(out/rel,arcname=rel)
    print(json.dumps({k:v for k,v in result.items() if k!="atlases"},ensure_ascii=False,sort_keys=True))
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--repo-root",default=".")
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    run(args.repo_root,args.out)
