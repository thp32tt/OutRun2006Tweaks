#!/usr/bin/env python3
"""Deterministic v2 3D topology/fit regression without proprietary assets."""
import importlib.util,math
from pathlib import Path

source=Path(__file__).resolve().parents[1]/"dino_cockpit_hdgeometry_v2.py"
spec=importlib.util.spec_from_file_location("dinohd",source)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
meshes=mod.build_v2()
prev=mod.v1.generate_cockpit()
by_name={m.name:m for m in meshes}
assert len(by_name)==len(meshes)
assert len(meshes)>len(prev)
assert sum(len(m.faces)//3 for m in meshes)>sum(len(m.faces)//3 for m in prev)*2
assert all(len(m.vertices)==len(m.uvs)==len(m.normals) for m in meshes)
for mesh in meshes:
    assert mesh.faces and len(mesh.faces)%3==0
    assert not any(i>=len(mesh.vertices) or i<0 for i in mesh.faces)
    assert all(math.isfinite(c) for p in mesh.vertices for c in p)
    assert all(math.isfinite(c) for p in mesh.normals for c in p)
    assert all(.9<math.sqrt(sum(c*c for c in n))<1.1 for n in mesh.normals)
assert sum("steering_rim" in name and "stitch" not in name for name in by_name)==1
assert sum("column_real_shafts" in name for name in by_name)==1
assert sum("perforated_stamped" in name for name in by_name)==3
assert not any(name.startswith("steering_spoke_") for name in by_name)
assert sum("window_crank" in name for name in by_name)>=6
assert sum("door_panel" in name for name in by_name)>=2
assert sum("backrest_thick_shell" in name for name in by_name)==2
assert sum("cushion_thick_shell" in name for name in by_name)==2
assert sum("tick" in name for name in by_name)>=60

def inside_triangle(p,tri):
    (x,y),((ax,ay),(bx,by),(cx,cy))=p,tri
    det=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
    if abs(det)<1e-12:return False
    a=((by-cy)*(x-cx)+(cx-bx)*(y-cy))/det
    b=((cy-ay)*(x-cx)+(ax-cx)*(y-cy))/det
    c=1-a-b
    return min(a,b,c)>1e-6

def intersects(mesh, p):
    for i in range(0,len(mesh.faces),3):
        tri=[mesh.vertices[mesh.faces[i+j]][:2] for j in range(3)]
        if inside_triangle(p,tri):
            return True
    return False

for no,angle in enumerate((math.pi/2,math.pi*7/6,math.pi*11/6)):
    spoke=by_name["wheel_spoke_%d_perforated_stamped_metal"%no]
    for t in (.36,.69):
        r=.046+(.170-.046)*t
        center=(-.320+r*math.cos(angle), .708+r*math.sin(angle))
        assert not intersects(spoke,center),("wheel perforation filled",no,t)
    for t in (.17,.52,.88):
        r=.046+(.170-.046)*t
        center=(-.320+r*math.cos(angle)-.005*math.sin(angle), .708+r*math.sin(angle)+.005*math.cos(angle))
        assert intersects(spoke,center),("wheel solid spoke missing",no,t)

bbox=[
    [min(v[i] for mesh in meshes for v in mesh.vertices),
     max(v[i] for mesh in meshes for v in mesh.vertices)]
    for i in range(3)
]
assert -.80<=bbox[0][0]<-.6 and .6<bbox[0][1]<=.80, bbox
assert bbox[1][0]>=.12 and bbox[1][1]<=1.18,bbox
assert bbox[2][0]>=-1.25 and bbox[2][1]<1.28,bbox
print("PASS HD_V2_TOPOLOGY_VALID, authentic wheel perforation cutouts = 6",
      "meshes",len(meshes),
      "vertices",sum(len(m.vertices) for m in meshes),
      "triangles",sum(len(m.faces)//3 for m in meshes),
      "bounds",bbox)

# R26/OVC must not issue hundreds of per-eye D3D9 Draw calls.
merged=mod.merge_meshes_for_runtime(meshes)
assert 1<=len(merged)<=16,("excessive R26 Draw groups",len(merged))
assert len(set(m.material for m in merged))==len(set(m.material for m in meshes))
assert sum(len(m.faces) for m in merged)==sum(len(m.faces) for m in meshes)
assert sum(len(m.vertices) for m in merged)==sum(len(m.vertices) for m in meshes)
assert max(len(m.vertices) for m in merged)<=60000
assert all(len(m.faces)//3>0 for m in merged)
# No zero-area triangle is allowed, particularly inside wheel perforations.
for mesh in meshes:
    for j in range(0,len(mesh.faces),3):
        a,b,c=[mesh.vertices[mesh.faces[j+k]] for k in range(3)]
        ab=[b[k]-a[k] for k in range(3)]
        ac=[c[k]-a[k] for k in range(3)]
        cross=(ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0])
        assert sum(x*x for x in cross)>=1e-22,mesh.name
print("PASS R26_MATERIAL_BATCHES",len(merged),"no zero-area triangles")

# External artwork substitution must be exact/complete, never silently partial.
from tempfile import TemporaryDirectory
from PIL import Image
with TemporaryDirectory() as tmp:
    folder=Path(tmp)
    names=("leather","vinyl","plastic","metal","carpet","seat")
    for j,name in enumerate(names):
        Image.new("RGB",(256,256),(24+j*7,33+j*4,47+j*3)).save(folder/(name+".png"))
    maps=mod.material_maps_v2(512,folder)
    assert all(maps[name].size==(512,512) for name in names)
    (folder/"seat.png").unlink()
    try:
        mod.material_maps_v2(512,folder)
        raise AssertionError("missing optional external texture unexpectedly accepted")
    except ValueError:
        pass
print("PASS EXTERNAL_PNG_OVERRIDE complete-six-material contract")