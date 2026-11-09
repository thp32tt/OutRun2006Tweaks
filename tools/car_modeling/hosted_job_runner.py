#!/usr/bin/env python3
"""GitHub public Ubuntu runner orchestration; encrypted native source in/out.

Does NOT run Blender on N100. Missing key/source -> fail closed. A probe is not
a modeling achievement; edit requires a separately reviewed native-mesh script.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda:f.read(1048576),b""):
            h.update(part)
    return h.hexdigest()


def inside(root, rel):
    candidate=(root / rel).resolve()
    if not candidate.is_relative_to(root) or candidate == root:
        raise RuntimeError("BLOCKED_PATH: outside private runner root")
    return candidate


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--slot",choices=("A","C"),required=True)
    parser.add_argument("--mode",choices=("spec","probe","edit"),default="spec")
    parser.add_argument("--root",required=True)
    parser.add_argument("--blender",required=True)
    parser.add_argument("--spec",required=True)
    parser.add_argument("--queue",required=True)
    parser.add_argument("--workpack",required=True)
    parser.add_argument("--encrypted-output",required=True)
    a=parser.parse_args()
    root=Path(a.root).resolve()
    repo=Path(__file__).resolve().parents[2]
    spec_path=Path(a.spec).resolve()
    spec=json.loads(spec_path.read_text(encoding="utf-8"))
    queue=json.loads(Path(a.queue).read_text(encoding="utf-8"))
    workpack=json.loads(Path(a.workpack).read_text(encoding="utf-8"))
    target=queue.get("active_by_slot",{}).get(a.slot)
    if spec.get("schema_version")!=1 or target!=spec.get("car_id") or workpack.get("car_id")!=target:
        raise RuntimeError("BLOCKED_SLOT: inconsistent car assignment")
    if spec.get("component")!=workpack.get("current_component"):
        raise RuntimeError("BLOCKED_PART: stale component; no infinite wheel redo")
    car=next(c for c in queue["cars"] if c["id"]==target)
    if car.get("output_scene_sha256")!=spec.get("source_sha256"):
        raise RuntimeError("BLOCKED_INPUT: latest private .blend SHA changed; refresh encrypted input before model edit")
    if car["source_provenance"]["original_game_resource_sha256"]!=spec.get("original_sha256"):
        raise RuntimeError("BLOCKED_ORIGINAL: wrong native PMT")
    mode=spec["mode"] if a.mode=="spec" else a.mode
    if mode not in ("probe","edit"):
        raise RuntimeError("BLOCKED_MODE: only source probe or scoped native edit")
    blender=Path(a.blender).resolve(strict=True)
    source=inside(root,spec["source_blend_rel"])
    result=inside(root,spec["output_blend_rel"])
    receipt=inside(root,spec["receipt_rel"])
    if not source.is_file() or sha(source)!=spec["source_sha256"]:
        raise RuntimeError("BLOCKED_SOURCE_SHA: changed source .blend")
    stage=repo/"tools/car_modeling/hosted_scene_stage.py"
    def invoke(stage_name,scene):
        cmd=[str(blender),"--background",str(scene),"--threads","2",
             "--python",str(stage),"--","--stage",stage_name,"--slot",a.slot,
             "--spec",str(spec_path),"--root",str(root)]
        subprocess.run(cmd,cwd=repo,check=True,timeout=1800)
    invoke(mode,source)
    if mode=="edit":
        if not result.is_file() or not receipt.is_file():
            raise RuntimeError("BLOCKED_EDIT: no saved source-derived .blend or receipt")
        invoke("verify",result)
    if not receipt.is_file():
        raise RuntimeError("BLOCKED_PROBE: missing private scene inventory")
    secure=repo/"tools/car_modeling/secure_bundle.py"
    paths=[spec["receipt_rel"]]+([spec["output_blend_rel"]] if mode=="edit" else [])
    encrypted=Path(a.encrypted_output).resolve()
    pack=[sys.executable,str(secure),"pack","--slot",a.slot,
          "--root",str(root),"--out",str(encrypted)]
    for item in paths:
        pack.extend(["--include",item])
    subprocess.run(pack,cwd=repo,check=True,timeout=180)
    if not encrypted.is_file():
        raise RuntimeError("BLOCKED_OUTPUT: encrypted artifact missing")
    print(json.dumps({"status":"PUBLIC_GITHUB_VM_PROBE_NOT_MODEL_COMPLETE" if mode=="probe"
                      else "PUBLIC_GITHUB_VM_SOURCE_GEOMETRY_EDIT_ENCRYPTED",
                      "slot":a.slot,"part":spec["component"],
                      "ciphertext_bytes":encrypted.stat().st_size,
                      "ciphertext_sha256":sha(encrypted),
                      "private_source_publicly_uploaded":False},ensure_ascii=False))


if __name__=="__main__":
    main()
