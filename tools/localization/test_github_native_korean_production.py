"""Native Korean Github producer: no N100, no game files changed, synthetic-only tests."""
import importlib.util, io, struct, tempfile, unittest
from pathlib import Path
from PIL import Image
P=Path(__file__).with_name("github_native_korean_production.py")
spec=importlib.util.spec_from_file_location("outrun_gh_native_production",P)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def fake_dds(w=256,h=64):
 header=bytearray(128)
 header[:4]=b"DDS "
 for off,num in ((4,124),(12,h),(16,w),(28,1),(76,32),(80,65),(88,32)):
  struct.pack_into("<I",header,off,num)
 struct.pack_into("<IIII",header,92,*m.BGRA)
 pixels=Image.new("RGBA",(w,h))
 for x in range(100,115):pixels.putpixel((x,20),(246,246,246,255))
 return bytes(header)+pixels.tobytes("raw","BGRA")

class SourceGates(unittest.TestCase):
 def test_good_dds(self):
  b=fake_dds()
  self.assertEqual(m.inspect_dds(b),(256,64,"BGRA"))
  with self.assertRaisesRegex(ValueError,"DDS_LENGTH_INVALID"):m.inspect_dds(b[:-8])
 def test_safe_targets(self):
  self.assertTrue(m.safe_texture("textures/load/spr_etc_xst/D6DC1380_256x64.dds"))
  for s in ("../x.dds","textures/load/a/../x.dds","textures/load/a/file.png","textures/load/a/evil\\file.dds"):
   self.assertFalse(m.safe_texture(s))
 def test_korean_render(self):
  data,png,painted,held=m.produce(fake_dds(),
   [{"id":"Q012_test","box":[0,0,200,64],"korean":"계속?","english":"Continue?"}],
   "NORMAL",m.font_file())
  self.assertTrue(data and data!=fake_dds())
  self.assertEqual(len(painted),1)
  self.assertEqual(png.getpixel((250,50)),(0,0,0,0))
  self.assertFalse(held)
 def test_two_line_hold(self):
  data,png,painted,held=m.produce(fake_dds(),
   [{"id":"x","box":[0,0,200,64],"korean":"한줄","english":"Two / Lines"}],
   "NORMAL",m.font_file())
  self.assertIsNone(data)
  self.assertEqual(held[0][1],"TWO_LINE_LAYOUT_HOLD")
 def test_opaque_protected_hold(self):
  b=bytearray(fake_dds())
  b[128:]=bytes((255,255,255,255))* (256*64)
  _,_,painted,held=m.produce(bytes(b),
   [{"id":"x","box":[0,0,256,64],"korean":"계속?","english":"Continue?"}],
   "NORMAL",m.font_file())
  self.assertFalse(painted)
  self.assertEqual(held[0][1],"OPAQUE_PROTECTED_ART_HOLD")
 def test_orientation_roundtrip(self):
  b=fake_dds()
  out,_,painted,held=m.produce(b,
   [{"id":"x","box":[0,0,200,64],"korean":"계속?","english":"Continue?"}],
   "FLIPY",m.font_file())
  self.assertEqual(len(out),len(b))
  self.assertEqual(len(painted),1)
  self.assertFalse(held)
if __name__=="__main__":unittest.main()
