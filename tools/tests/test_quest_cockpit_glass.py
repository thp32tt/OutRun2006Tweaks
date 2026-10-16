#!/usr/bin/env python3
"""No proprietary PMTs required: synthetic regression for player-car glass patch."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
import zlib
p=Path(__file__).resolve().parents[1]/"quest_cockpit_glass.py"
spec=importlib.util.spec_from_file_location("questglass",p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def fixture():
    raw=bytearray(760)
    struct.pack_into("<4I",raw,0,1,3,704,0)
    struct.pack_into("<6I",raw,16,0,1,3,0,0,0)
    o=[0]*15;o[6]=84;o[13]=144;o[14]=408
    struct.pack_into("<15I",raw,40,*o)
    h=[0]*13;h[9:13]=[1,3,3,3]
    struct.pack_into("<13I",raw,100,*h)
    for j in range(3):
        struct.pack_into("<II",raw,160+j*88,j,0x08005107 if j==2 else 0x5400)
        struct.pack_into("<4f",raw,424+j*72,
                         *([.3,.3,.3,.55] if j==2 else [1.,1.,1.,1.]))
    return bytes(raw)

class GlassTests(unittest.TestCase):
    def test_strict_match_and_raw_unmodified(self):
        orig=fixture()
        encoded,hit=m.patch_bytes(zlib.compress(orig),"obj_plcar_360sp_pmt.sz",.3)
        after,packed=m.unpack(encoded)
        self.assertTrue(packed)
        self.assertEqual(len(hit),1)
        offset=424+2*72+12
        self.assertAlmostEqual(struct.unpack_from("<f",after,offset)[0],.3,places=6)
        self.assertEqual(orig[:offset]+orig[offset+4:],
                         after[:offset]+after[offset+4:])
    def test_unknown_model_material_and_aliased_body_rejected(self):
        orig=fixture()
        with self.assertRaises(ValueError):
            m.patch_bytes(orig,"obj_stage_pmt.sz",.3)
        corrupted=bytearray(orig)
        struct.pack_into("<I",corrupted,160+2*88+4,0x1400)
        with self.assertRaises(ValueError):
            m.patch_bytes(corrupted,"obj_plcar_360sp_pmt.sz",.3)
        shared=bytearray(orig)
        struct.pack_into("<I",shared,160,2)
        with self.assertRaises(ValueError):
            m.patch_bytes(shared,"obj_plcar_360sp_pmt.sz",.3)
    def test_opacity_and_corruption_negative(self):
        orig=fixture()
        for opacity in (float("nan"),float("inf"),0.,.95):
            with self.assertRaises(ValueError):
                m.patch_bytes(orig,"obj_plcar_360sp_pmt.sz",opacity)
        with self.assertRaises((ValueError,zlib.error)):
            m.patch_bytes(b"\x78\x9c","obj_plcar_360sp_pmt.sz",.3)
    def test_selection_and_recovery(self):
        orig=fixture()
        name="obj_plcar_360sp_pmt.sz"
        out,hit=m.patch_bytes(orig,name,.2,{(0,2)})
        self.assertEqual(len(hit),1)
        self.assertEqual(len(out),len(orig))
        with self.assertRaises(ValueError):
            m.patch_bytes(orig,name,.3,{(0,1)})
        valid,hit=m.patch_bytes(orig,name,.3)
        self.assertEqual(len(hit),1)
        self.assertNotEqual(valid,orig)
if __name__=="__main__":
    unittest.main()
