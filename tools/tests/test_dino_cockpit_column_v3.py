#!/usr/bin/env python3
"""Source-free v3 Dino driver-column repair acceptance and geometry regression."""
import importlib.util
import math
from pathlib import Path

script=Path(__file__).resolve().parents[1]/"dino_cockpit_hdgeometry_v3.py"
spec=importlib.util.spec_from_file_location("v3",script)
v3=importlib.util.module_from_spec(spec);spec.loader.exec_module(v3)
meshes=v3.build_v3()
d={m.name:m for m in meshes}
assert len(d)==len(meshes)
assert len(meshes)>300 and sum(len(m.faces)//3 for m in meshes)>90000
assert sum("LHD_steering_rim_remodelled"==n for n in d)==1
assert sum("LHD_column_outer_padded_shroud"==n for n in d)==1
assert sum("LHD_column_internal_axle"==n for n in d)==1
for old in ("LHD_column_real_shafts","LHD_column_plastic_shroud",
            "dashboard_driver_instrument_recess","dash_rolled_face",
            "indicator_stalk","wiper_stalk"):
    assert old not in d, "old intersecting geometry not removed: "+old
for required in ("pod_gauges_upper_shell","pod_gauges_lower_left",
                 "pod_gauges_lower_right","dash_front_aperture_left",
                 "dash_front_aperture_right","dash_front_aperture_center_top",
                 "dash_front_aperture_center_bottom",
                 "LHD_column_dash_foot_flange","LHD_column_dash_rubber_inner_seal",
                 "indicator_stalk_v3","wiper_stalk_v3",
                 "column_mouth_top_leather","column_mouth_lower_chrome"):
    assert required in d,required

clear=v3.column_clearance()
assert clear["gauge1"]>=.019
assert clear["notch_clearance_x_m"]>=.047
assert clear["notch_clearance_y_m"]>=.025
assert all(clear[x]>=.012 for x in ("gauge0","gauge1","gauge2"))

# Axis monotonically recedes and remains below the visible main gauge disc:
axis=v3.COLUMN_AXIS
assert all(axis[i][2]>axis[i+1][2] for i in range(len(axis)-1))
assert axis[0][1] > axis[-1][1]
for z in (-.406,-.411,-.417,-.430):
    p=v3.sample_axis_at_z(z)
    x,y,_=p
    for gx,gy,r in v3.POD_GAUGES:
        # Even the thick opaque shroud clears ALL three gauge faces.
        assert math.hypot(x-gx,y-gy)>r+v3.SHROUD_RADIUS+.012
# At the opening the steering can pass without penetrating surrounding fascia.
for z in (-.455,-.466,-.475,-.487):
    x,y,_=v3.sample_axis_at_z(z)
    assert (v3.PANEL_NOTCH_X[0]+v3.SHROUD_RADIUS
            <x<v3.PANEL_NOTCH_X[1]-v3.SHROUD_RADIUS)
    assert (v3.PANEL_NOTCH_Y[0]+v3.SHROUD_RADIUS
            <y<v3.PANEL_NOTCH_Y[1]-v3.SHROUD_RADIUS)

# The 4 front body sub-surfaces leave a real aperture; check triangle vertices
# not one simulated black color/sticker over a solid panel.
for name in list(d):
    if not name.startswith("dash_front_aperture_"):continue
    m=d[name]
    for p in m.vertices:
        in_x=v3.PANEL_NOTCH_X[0]+.00001<p[0]<v3.PANEL_NOTCH_X[1]-.00001
        in_y=v3.PANEL_NOTCH_Y[0]+.00001<p[1]<v3.PANEL_NOTCH_Y[1]-.00001
        assert not(in_x and in_y), ("solid polygon in steering aperture",name,p)
# Validate GLB geometry and source normal/UV/indices in authoring meshes.
zero=0
for m in meshes:
    assert m.vertices and len(m.uvs)==len(m.vertices)==len(m.normals)
    assert len(m.faces)>0 and len(m.faces)%3==0
    for j in range(0,len(m.faces),3):
        a,b,c=[m.vertices[m.faces[j+k]] for k in range(3)]
        u=[b[k]-a[k] for k in range(3)]
        v=[c[k]-a[k] for k in range(3)]
        n=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
        if sum(x*x for x in n)<1e-22:zero+=1
assert zero==0,("degenerate triangles",zero)
batches=v3.v2.merge_meshes_for_runtime(meshes)
assert len(batches)==9 and len(meshes)>len(batches)
assert sum(len(m.faces) for m in meshes)==sum(len(m.faces) for m in batches)
assert sum(len(m.vertices) for m in meshes)==sum(len(m.vertices) for m in batches)
assert max(len(m.vertices) for m in batches)<60000
print("PASS DINO_V3_COCKPIT_COLUMN_CLEARANCE",
      "groups",len(meshes),"batches",len(batches),
      "vertices",sum(len(m.vertices) for m in meshes),
      "triangles",sum(len(m.faces)//3 for m in meshes),
      "zeroArea",zero,"clearance",clear)