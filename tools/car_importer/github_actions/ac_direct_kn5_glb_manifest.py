#!/usr/bin/env python3
from __future__ import annotations
import argparse, configparser, hashlib, json, math, shutil, subprocess, sys
from pathlib import Path

import numpy as np

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def select_kn5(root:Path)->tuple[Path,str]:
    ini=root/"data"/"lods.ini"
    if ini.is_file():
        cp=configparser.ConfigParser(interpolation=None,strict=False)
        try: cp.read(ini,encoding="utf-8-sig")
        except UnicodeError: cp.read(ini,encoding="cp1252")
        sections=sorted((s for s in cp.sections() if s.upper().startswith("LOD_")),
                        key=lambda s:int(s.split("_")[-1]) if s.split("_")[-1].isdigit() else 999)
        for s in sections:
            name=cp.get(s,"FILE",fallback="").strip().strip('"').replace("\\","/")
            p=(root/name).resolve()
            if p.is_file() and p.suffix.lower()==".kn5":
                return p,"lods_ini_highest"
    files=[p for p in root.glob("*.kn5") if p.is_file() and p.stem.lower() not in ("collider","collision")
           and "collider" not in p.stem.lower() and "_lod_b" not in p.stem.lower()
           and "_lod_c" not in p.stem.lower() and "_lod_d" not in p.stem.lower()]
    if not files: files=[p for p in root.glob("*.kn5") if p.is_file() and "collider" not in p.stem.lower()]
    if not files: raise RuntimeError("No visual KN5 found")
    files.sort(key=lambda p:p.stat().st_size,reverse=True)
    return files[0],"largest_primary_kn5"

def pick_skin(root:Path)->str|None:
    skins=root/"skins"
    if not skins.is_dir(): return None
    dirs=sorted([p for p in skins.iterdir() if p.is_dir()],key=lambda p:p.name.lower())
    for preferred in ("rosso_corsa","rosso_scuderia","rosso_dino","red","default"):
        for p in dirs:
            if p.name.lower()==preferred: return p.name
    return dirs[0].name if dirs else None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-audit",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--car-id",required=True)
    ap.add_argument("--vehicle-name",required=True)
    ap.add_argument("--fbc-tools",type=Path,required=True)
    ns=ap.parse_args()

    audit=json.loads(ns.source_audit.read_text(encoding="utf-8"))
    if not audit["rights"].get("private_conversion_allowed"):
        raise RuntimeError("rights audit blocked conversion")
    root=Path(audit["car_root"]).resolve()
    out=ns.output.resolve();out.mkdir(parents=True,exist_ok=True)
    kn5,method=select_kn5(root)
    skin=pick_skin(root)
    exe=shutil.which("kn5-to-gltf")
    if not exe: raise RuntimeError("kn5-to-gltf executable missing")
    cmd=[exe,str(kn5),str(out),"--name","source","--glb"]
    if skin: cmd += ["--skin",skin]
    print("DIRECT_CONVERT",json.dumps({"kn5":str(kn5),"skin":skin,"method":method}))
    subprocess.run(cmd,check=True)
    glb=out/"source.glb"
    if not glb.is_file(): raise RuntimeError("direct converter did not create source.glb")

    sys.path.insert(0,str(ns.fbc_tools.resolve()))
    import ferrari_batch_converter as fbc
    g,binary=fbc.load_glb(glb)
    lo=np.full(3,np.inf); hi=np.full(3,-np.inf)
    ident=np.eye(4,dtype=float).reshape(-1).tolist()
    triangles=0; source_vertices=0
    for _node,mesh,matrix in fbc.ordered_mesh_nodes(g,ident):
        for prim in mesh.get("primitives",[]):
            pos=fbc.accessor(g,binary,prim["attributes"]["POSITION"],components=3).astype(np.float64)
            xyz=pos @ matrix[:3,:3].T + matrix[:3,3]
            lo=np.minimum(lo,xyz.min(axis=0)); hi=np.maximum(hi,xyz.max(axis=0))
            source_vertices += len(pos)
            idx=fbc.accessor(g,binary,prim["indices"],components=1)
            triangles += len(idx)//3
    dims=hi-lo
    # Direct converter output is glTF: +X right, +Y up, -Z forward.
    width,height,length=float(dims[0]),float(dims[1]),float(dims[2])
    if not (1.2 <= width <= 2.6): raise RuntimeError(f"direct GLB width invalid {width:.3f}")
    if not (0.7 <= height <= 2.2): raise RuntimeError(f"direct GLB height invalid {height:.3f}")
    if not (3.0 <= length <= 6.0): raise RuntimeError(f"direct GLB length invalid {length:.3f}")
    cx=float((lo[0]+hi[0])*0.5); ground=float(lo[1]); cz=float((lo[2]+hi[2])*0.5)
    # OutRun sidecars are +X right, +Y up, +Z forward. Mirror Z and let the
    # OVC converter reverse triangle winding when determinant is negative.
    matrix=[
        1,0,0,-cx,
        0,1,0,-ground,
        0,0,-1,cz,
        0,0,0,1,
    ]
    manifest={
      "schema":1,"car_id":ns.car_id,"vehicle_name":ns.vehicle_name,
      "source_sha256":sha256(glb),"geometry_space":"outrun_local_y_up_meters",
      "alignment_verified":True,"model_scope":"full_car","origin_type":"external_mod",
      "external_to_game_matrix":matrix,
      "rights_note":audit["rights"].get("rights_note","PRIVATE_TEST_ONLY"),
      "redistribution_verified":False,
      "selected_kn5":str(kn5.relative_to(root)) if kn5.is_relative_to(root) else kn5.name,
      "selected_kn5_sha256":sha256(kn5),"lod_selection_method":method,"skin":skin,
      "normalization":{
        "source_gltf_bounds":[lo.tolist(),hi.tolist()],
        "source_gltf_dimensions_width_height_length_m":[width,height,length],
        "source_axes":{"right":"+X","up":"+Y","forward":"-Z"},
        "game_axes":{"right":"+X","up":"+Y","forward":"+Z"},
        "center_x":cx,"center_z":cz,"ground_y":ground,
        "policy":"center_xz_ground_y0_mirror_z_with_winding_fix"
      },
      "mesh_stats":{"meshes":len(g.get("meshes",[])),"materials":len(g.get("materials",[])),
                    "images":len(g.get("images",[])),"source_vertices":source_vertices,"triangles":triangles},
      "converter":"semiloker/assetto-corsa-gltf@9ab1438113c0a1c655ba44f99ace1b048a2d3bb5"
    }
    (out/"source.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("DIRECT_GLB_MANIFEST",json.dumps(manifest,ensure_ascii=False))

if __name__=="__main__": main()
