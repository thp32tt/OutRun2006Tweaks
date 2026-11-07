#!/usr/bin/env python3
import os,sys,json,subprocess,tempfile
from pathlib import Path
from PIL import Image
script=Path(__file__).with_name("generate_daytona365_v7_materials.py")
with tempfile.TemporaryDirectory(prefix="daytona_v7_test_") as d:
 root=Path(d)
 refs=root/"reference_v7";refs.mkdir()
 for name,color in (("tan",(165,98,58)),("black",(36,32,30)),("wood",(101,58,37))):
  im=Image.new("RGB",(48,48))
  px=im.load()
  for y in range(48):
   for x in range(48):
    z=(x*7+y*11)%17-8
    px[x,y]=tuple(max(0,min(255,c+z)) for c in color)
  im.save(refs/(name+"_reference.jpg"))
 env=dict(os.environ);env["DAYTONA_V7_ROOT"]=str(root)
 r=subprocess.run([sys.executable,str(script)],env=env,text=True,capture_output=True,timeout=60)
 assert r.returncode==0,r.stderr
 out=root/"blender_v7/textures"
 j=json.loads((out/"V7_MATERIAL_MANIFEST.json").read_text())
 assert len(j)==3
 for name in ("TanLeather","BlackLeather","WalnutRim"):
  for suffix in ("BaseColor","Normal","ORM","HeightOffline"):
   q=out/(name+"_"+suffix+".png")
   assert q.is_file()
   img=Image.open(q);img.load()
   assert img.size==(512,512)
   if suffix=="Normal":
    assert min(v[2] for v in img.convert("RGB").getdata())>=127
   if suffix=="ORM":
    assert all(v[2]==0 for v in img.convert("RGB").getdata())
 print("DAYTONA_V7_PBR_SYNTHETIC_PASS: 3 materials, 12 texture maps")