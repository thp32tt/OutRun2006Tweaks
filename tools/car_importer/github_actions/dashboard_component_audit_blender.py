#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector

EPS=1.0e-5

def qkey(v):
    return (round(v.x/EPS),round(v.y/EPS),round(v.z/EPS))

def analyze_object(obj):
    mesh=obj.data
    world=obj.matrix_world
    pos=[world @ v.co for v in mesh.vertices]
    tris=[]
    mesh.calc_loop_triangles()
    for tri in mesh.loop_triangles:
        tris.append((tri.material_index,tuple(tri.vertices)))
    bymat={}
    for ti,(mi,vs) in enumerate(tris):
        bymat.setdefault(mi,[]).append((ti,vs))
    rows=[]
    for mi,items in bymat.items():
        parent=list(range(len(items)))
        def find(x):
            while parent[x]!=x:
                parent[x]=parent[parent[x]]
                x=parent[x]
            return x
        def join(a,b):
            a,b=find(a),find(b)
            if a!=b: parent[b]=a
        owners={}
        for local,(_ti,vs) in enumerate(items):
            for vi in vs:
                k=qkey(pos[vi])
                if k in owners: join(local,owners[k])
                else: owners[k]=local
        groups={}
        for local,(_ti,vs) in enumerate(items):
            r=find(local)
            g=groups.setdefault(r,{"triangles":0,"vertices":set()})
            g["triangles"]+=1
            g["vertices"].update(vs)
        mat=mesh.materials[mi].name if mi < len(mesh.materials) and mesh.materials[mi] else ""
        for g in groups.values():
            pts=[pos[v] for v in g["vertices"]]
            lo=[min(p[i] for p in pts) for i in range(3)]
            hi=[max(p[i] for p in pts) for i in range(3)]
            size=[hi[i]-lo[i] for i in range(3)]
            center=[(lo[i]+hi[i])*0.5 for i in range(3)]
            dims=sorted(size)
            # F40 needle reference is about 4.3 x 2.4 x 0.1 cm. Keep this
            # deliberately broad: audit candidates only, never auto-bind.
            maxd=max(size)
            mind=min(size)
            flat=(dims[0] <= 0.012)
            compact=(0.012 <= maxd <= 0.18)
            smalltop=(g["triangles"] <= 600)
            aspect=(maxd/(dims[1]+1e-9)) if dims[1]>0 else 999.0
            score=(3 if flat else 0)+(3 if compact else 0)+(2 if smalltop else 0)+(1 if aspect>=1.3 else 0)
            rows.append({
                "object":obj.name,"material":mat,
                "vertices":len(g["vertices"]),"triangles":g["triangles"],
                "bounds_world":[lo,hi],"center_world":center,"size_world":size,
                "needle_audit_score":score,
                "needle_like":bool(score>=7),
            })
    return rows

def main():
    raw=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    ap=argparse.ArgumentParser()
    ap.add_argument("--glb",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ns=ap.parse_args(raw)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ns.glb))
    all_rows=[]
    for obj in bpy.context.scene.objects:
        if obj.type!="MESH": continue
        # cockpit/interior objects are the only target; keep all materials inside them.
        text=(obj.name+" "+obj.data.name).lower()
        if "cockpit" not in text and "interior" not in text:
            continue
        all_rows.extend(analyze_object(obj))
    all_rows.sort(key=lambda r:(-r["needle_audit_score"],r["triangles"],r["object"],r["material"]))
    result={
        "schema":1,"source_glb":str(ns.glb),
        "component_count":len(all_rows),
        "needle_like_count":sum(r["needle_like"] for r in all_rows),
        "needle_like_candidates":[r for r in all_rows if r["needle_like"]][:120],
        "top_components":all_rows[:250]
    }
    ns.out.parent.mkdir(parents=True,exist_ok=True)
    ns.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("COMPONENT_AUDIT_SUMMARY",json.dumps({
        "component_count":result["component_count"],
        "needle_like_count":result["needle_like_count"],
        "needle_like_candidates":result["needle_like_candidates"][:30]
    },ensure_ascii=False))

if __name__=="__main__":
    main()
