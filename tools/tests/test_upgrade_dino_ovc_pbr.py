import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from tools.upgrade_dino_ovc_pbr import upgrade, validate_base_ovc2, validate_dds


def dds4():
    b = bytearray(128 + 4 * 4 * 4)
    b[:4] = b"DDS "
    for off,v in ((4,124),(12,4),(16,4),(28,1),(76,32),(80,0x41),
                  (88,32),(92,0x00ff0000),(96,0x0000ff00),(100,0x000000ff),
                  (104,0xff000000)):
        struct.pack_into("<I",b,off,v)
    return bytes(b)


def ovc2():
    b = bytearray(36)
    b[:8] = b"OVRCABH2"
    for off,v in ((8,2),(12,1),(16,1),(20,3),(24,1)):
        struct.pack_into("<I",b,off,v)
    b.extend(struct.pack("<HHIII",3,0,3,3,2))
    b.extend(b"PBR")
    b.extend(struct.pack("<8f",0,0,0,0,1,0,0,0)*3)
    b.extend(struct.pack("<3H",0,1,2))
    tex=dds4()
    b.extend(struct.pack("<I",len(tex)))
    b.extend(tex)
    struct.pack_into("<I",b,28,len(b)-36)
    struct.pack_into("<I",b,32,zlib.crc32(b[36:]))
    return bytes(b)


class Ovc3UpgradeTests(unittest.TestCase):
    def test_pbr_extension_preserves_original_payload_and_crc(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            old=ovc2()
            (root/"normal.dds").write_bytes(dds4())
            (root/"orm.dds").write_bytes(dds4())
            manifest={"materials":[{"index":0,"roughness":0.55,
                                    "metallic":0.8,"normalScale":1.25,
                                    "normal":"normal.dds","orm":"orm.dds"}]}
            new=upgrade(old,manifest,root)
            self.assertEqual(new[:8],b"OVRCABH3")
            self.assertEqual(struct.unpack_from("<I",new,8)[0],3)
            self.assertEqual(new[36:len(old)],old[36:])
            self.assertEqual(new[len(old):len(old)+8],b"OVCPBR3!")
            self.assertEqual(zlib.crc32(new[36:]),struct.unpack_from("<I",new,32)[0])
            self.assertEqual(validate_base_ovc2(old)[0],1)

    def test_packed_orm_defaults_preserve_metallic_and_roughness(self):
        # A metallic 100%-white ORM pixel must remain metallic; the previous
        # default 0.04 multiplier silently discarded ~96% of map metalness.
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            (root/"orm.dds").write_bytes(dds4())
            base=ovc2()
            metal=upgrade(base,{"materials":[{"index":0,"orm":"orm.dds"}]},root)
            roughness, metallic, strength=struct.unpack_from("<3f",metal,len(base)+8)
            self.assertEqual((roughness,metallic,strength),(1.0,1.0,1.0))
            no_map=upgrade(base,{"materials":[]},root)
            roughness, metallic, strength=struct.unpack_from("<3f",no_map,len(base)+8)
            self.assertEqual((roughness,metallic,strength),(0.75,0.0,1.0))
            with_factors=upgrade(base,{"materials":[
                {"index":0,"orm":"orm.dds","roughness":0.6,"metallic":0.8}
            ]},root)
            self.assertAlmostEqual(
                struct.unpack_from("<f",with_factors,len(base)+8)[0],0.6)
            self.assertAlmostEqual(
                struct.unpack_from("<f",with_factors,len(base)+12)[0],0.8)

    def test_reject_corrupt_input_and_unsafe_materials(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            old=ovc2()
            tampered=bytearray(old)
            tampered[40]^=1
            with self.assertRaises(ValueError):
                upgrade(bytes(tampered),{"materials":[]},root)
            for entry in ({"index":0,"roughness":float("nan")},
                          {"index":0,"metallic":2.0},
                          {"index":0,"normalScale":-1.0},
                          {"index":3},
                          {"index":0,"normal":"../outside.dds"}):
                with self.subTest(entry=entry):
                    with self.assertRaises(ValueError):
                        upgrade(old,{"materials":[entry]},root)
            with self.assertRaises(ValueError):
                upgrade(old,{"materials":[{"index":0},{"index":0}]},root)
            with self.assertRaises(ValueError):
                validate_dds(b"DDS "+bytes(200))

    def test_empty_maps_allow_factor_only_pbr(self):
        with tempfile.TemporaryDirectory() as t:
            new=upgrade(ovc2(),{"materials":[]},Path(t))
            self.assertEqual(len(new)-len(ovc2()),8+12+8)
            self.assertEqual(new[-8:],bytes(8))


if __name__ == "__main__":
    unittest.main()
