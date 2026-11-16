#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
import bpy
from mathutils import Vector

TOKENS = re.compile(r"(needle|speed|speedo|tach|rpm|gauge|meter|cluster|instrument|dash|cockpit|interior|gear)", re.I)

def bounds(obj):
    pts=[obj.matrix_world @ Vector(c) for c in obj.bound_box]
    lo=[min(p[i] for p in pts) for i in range(3)]
    hi=[max(p[i] for p in pts) for i in range(3)]
    return lo,hi,[hi[i]-lo[i] for i in range(3)]

def main():
    raw=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    ap=argparse.ArgumentParser()
    ap.add_argument("--glb",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ns=ap.parse_args(raw)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ns.glb))
    rows=[]
    for obj in bpy.context.scene.objects:
        if obj.type!="MESH":
            continue
        mats=[m.name for m in obj.data.materials if m]
        name=obj.name
        mesh=obj.data.name
        lo,hi,size=bounds(obj)
        obj.data.calc_loop_triangles()
        text=" ".join([name,mesh,*mats])
        rows.append({
            "node":name,"mesh":mesh,"materials":mats,
            "vertices":len(obj.data.vertices),
            "triangles":len(obj.data.loop_triangles),
            "bounds_world":[lo,hi],"size_world":size,
            "token_candidate":bool(TOKENS.search(text)),
        })
    rows.sort(key=lambda r:(not r["token_candidate"],r["node"]))
    result={
        "schema":1,
        "source_glb":str(ns.glb),
        "mesh_count":len(rows),
        "candidate_count":sum(r["token_candidate"] for r in rows),
        "candidates":[r for r in rows if r["token_candidate"]],
        "all_meshes":rows,
    }
    ns.out.parent.mkdir(parents=True,exist_ok=True)
    ns.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("DASHBOARD_AUDIT_BEGIN")
    print(json.dumps({"mesh_count":result["mesh_count"],"candidate_count":result["candidate_count"],
                      "candidates":result["candidates"]},ensure_ascii=False))
    print("DASHBOARD_AUDIT_END")

if __name__=="__main__":
    main()
