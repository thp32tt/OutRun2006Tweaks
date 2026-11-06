"""Fail-closed DXT5 4x4 index patch tests. Source endpoints are immutable."""
import importlib.util
import struct
import unittest
from pathlib import Path

from PIL import Image

here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("bc3", here / "hd_bc3_index_patch.py")
bc3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc3)


def dxt5_blank(width=64, height=32, mipmaps=1):
    header = bytearray(128)
    header[:4] = b"DDS "
    for offset, value in ((4,124),(12,height),(16,width),(28,mipmaps),
                          (76,32),(80,4),(88,0)):
        struct.pack_into("<I",header,offset,value)
    header[84:88] = b"DXT5"
    # Alpha 1=0, alpha 0=255, all 16 pixel alpha-indices=1.
    alpha_indexes = sum(1 << (i * 3) for i in range(16)).to_bytes(6,"little")
    block = bytes([255,0]) + alpha_indexes + struct.pack("<HHI",0xffff,0x0000,0)
    return bytes(header) + block * ((width // 4) * (height // 4))


class DXT5SafeIndexTests(unittest.TestCase):
    def test_existing_palette_white_pixels_can_be_placed_without_neighbor_damage(self):
        original=dxt5_blank()
        source=bc3._decode_bc3(original)
        desired=source.copy()
        desired.paste((255,255,255,255),(8,8,23,17))
        altered, receipt=bc3.patch_mip1(original,desired,[(8,8,23,17)],source)
        self.assertEqual(len(altered),len(original))
        self.assertEqual(altered[:128],original[:128])
        self.assertEqual(receipt["bc3_method"],"SOURCE_RGB_ENDPOINTS_FIXED_INDEX_ONLY_WITH_PROVEN_FULLY_TRANSPARENT_ALPHA_REBASE")
        got=bc3._decode_bc3(altered)
        self.assertEqual(got.getpixel((10,10)),(255,255,255,255))
        for y in range(source.height):
            for x in range(source.width):
                if not (8<=x<23 and 8<=y<17):
                    self.assertEqual(got.getpixel((x,y)),source.getpixel((x,y)))
        for by in range(32//4):
            for bx in range(64//4):
                off=128+(by*16+bx)*16
                self.assertEqual(original[off:off+2],altered[off:off+2])
                self.assertEqual(original[off+8:off+12],altered[off+8:off+12])
                if not (2<=bx<=5 and 2<=by<=4):
                    self.assertEqual(original[off:off+16],altered[off:off+16])

    def test_alpha_zero_block_may_rebase_only_with_bit_exact_unmodified_pixels(self):
        original=bytearray(dxt5_blank())
        for by in range(32//4):
            for bx in range(64//4):
                off=128+(by*16+bx)*16
                original[off:off+2]=bytes((3,0))
                # Original alpha indices already all point to endpoint1=0.
        original=bytes(original)
        source=bc3._decode_bc3(original)
        self.assertEqual(source.getpixel((10,10))[3],0)
        desired=source.copy()
        desired.paste((255,255,255,255),(8,8,23,17))
        after,receipt=bc3.patch_mip1(original,desired,[(8,8,23,17)],source)
        self.assertGreater(receipt["bc3_alpha_rebased_from_zero_blocks"],0)
        self.assertEqual(after[:128],original[:128])
        saved=bc3._decode_bc3(after)
        for y in range(32):
            for x in range(64):
                if 8<=x<23 and 8<=y<17:
                    self.assertEqual(saved.getpixel((x,y))[3],255)
                else:
                    self.assertEqual(saved.getpixel((x,y)),source.getpixel((x,y)))
        # RGB565 endpoints NEVER change, including alpha-rebased blocks.
        for i in range((64//4)*(32//4)):
            off=128+i*16
            self.assertEqual(after[off+8:off+12],original[off+8:off+12])

    def test_nonzero_source_alpha_block_refuses_endpoint_rebase(self):
        original=bytearray(dxt5_blank())
        # One whole block contains protected alpha=50. We cannot change
        # original endpoints, because old alpha 50 must remain unchanged.
        off=128+(2*(64//4)+2)*16
        original[off:off+2]=bytes((50,0))
        original[off+2:off+8]=bytes(6)
        original=bytes(original)
        desired=bc3._decode_bc3(original)
        desired.putpixel((8,8),(255,255,255,255))
        with self.assertRaisesRegex(bc3.BC3Hold,"ALPHA_PALETTE_INSUFFICIENT"):
            bc3.patch_mip1(original,desired,[(8,8,12,12)])

    def test_different_candidate_color_cannot_be_faked_with_original_palette(self):
        original=dxt5_blank()
        im=bc3._decode_bc3(original)
        im.putpixel((8,8),(240,10,10,255))
        with self.assertRaisesRegex(bc3.BC3Hold,"RGB_PALETTE_INSUFFICIENT"):
            bc3.patch_mip1(original,im,[(8,8,12,12)])

    def test_edits_outside_declared_roi_are_denied(self):
        original=dxt5_blank()
        im=bc3._decode_bc3(original)
        im.putpixel((2,2),(255,255,255,255))
        with self.assertRaisesRegex(bc3.BC3Hold,"NO_GLYPH_CHANGE|PROTECTED_PIXEL_CHANGED"):
            bc3.patch_mip1(original,im,[(8,8,12,12)])

    def test_mip_chain_is_held_even_if_base_level_can_be_decoded(self):
        original=dxt5_blank(mipmaps=13)
        im=bc3._decode_bc3(dxt5_blank())
        im.putpixel((8,8),(255,255,255,255))
        with self.assertRaisesRegex(bc3.BC3Hold,"MIP_CHAIN_REQUIRES"):
            bc3.patch_mip1(original,im,[(8,8,12,12)])

    def test_wrong_fourcc_or_malformed_length_held(self):
        original=dxt5_blank()
        with self.assertRaisesRegex(bc3.BC3Hold,"PAYLOAD_LENGTH"):
            bc3.bc3_shape(original[:-1])
        corrupt=bytearray(original)
        corrupt[84:88]=b"DXT1"
        with self.assertRaisesRegex(bc3.BC3Hold,"FOURCC"):
            bc3.bc3_shape(bytes(corrupt))


if __name__=="__main__":
    unittest.main()
