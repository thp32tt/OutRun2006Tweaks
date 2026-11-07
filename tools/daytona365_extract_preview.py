#!/usr/bin/env python3
from pathlib import Path
import json
from PIL import Image
try:
    from pmt_export_base import open_pmt,decode_dds,decode_object
except ModuleNotFoundError:
    from dino_original_pmt_to_glb import open_pmt,decode_dds,decode_object
root=Path(__file__).parent
p=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
a=open_pmt(p)
out=root/"original_preview";out.mkdir(exist_ok=True)
failed=[]
for i in range(a["tex_count"]):
 try:
  png, orig,after=decode_dds(a,i,1)
  (out/("tex_%02d.png"%i)).write_bytes(png)
 except Exception as e:failed.append([i,str(e)])
parts=decode_object(a,0)
ref={}
for q in parts:
 ti=q["tex_index"]
 if ti is None:continue
 v=q["vertices"]
 z=[(min(v[i][k] for i in range(len(v))),max(v[i][k] for i in range(len(v)))) for k in range(3)]
 ref.setdefault(ti,[]).append({"name":q["name"],"verts":len(v),"triangles":len(q["indices"])//3,"bounds":z})
(root/"texture_usage.json").write_text(json.dumps(ref,indent=2))
print(json.dumps({"extracted":len(list(out.glob("*.png"))),"failed":failed,"object0_textures":list(ref)},indent=2))