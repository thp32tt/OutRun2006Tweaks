"""Regression for actual single-mip DXT5 native source-owned Korean reuse."""
import unittest
from PIL import Image,ImageChops
from hd_bc3_index_patch import BC3Hold
from hd_bc3_native_owner_mip1 import apply
from hd_bc3_4mip_patch import read_levels
from test_hd_bc3_4mip_patch import fixture

class MipOneOwnerTest(unittest.TestCase):
    def inputs(self):
        raw,owner,text=fixture()
        single=read_levels(raw)[0][0]
        size=(12,12,36,52)
        with Image.open(__import__("io").BytesIO(single)) as im:
            orig=im.convert("RGBA")
        amb=Image.new("L",(24,40),0)
        return single,orig.crop(size),owner.crop(size),amb,text.crop(size),size
    def test_one_mip_native_source_header_and_foreign_art_survive(self):
        original,crop,owner,amb,text,bbox=self.inputs()
        result,proof=apply(original,crop,owner,amb,text,bbox)
        self.assertEqual(result[:128],original[:128])
        self.assertEqual(len(result),len(original))
        self.assertGreater(proof["bc3_pixels_modified"],0)
        with Image.open(__import__("io").BytesIO(original)) as im:
            src=im.convert("RGBA")
        with Image.open(__import__("io").BytesIO(result)) as im:
            got=im.convert("RGBA")
        self.assertEqual(got.getpixel((56,56)),src.getpixel((56,56)))
        self.assertGreater(got.getpixel((24,20))[3],15)
        self.assertLess(got.getpixel((16,20))[3],16)
    def test_original_source_pixels_cannot_be_substituted(self):
        original,crop,owner,amb,text,bbox=self.inputs()
        crop.putpixel((4,4),(0,0,0,255))
        with self.assertRaisesRegex(BC3Hold,"SHA_CROP_MISMATCH"):
            apply(original,crop,owner,amb,text,bbox)
    def test_ambiguous_owner_is_not_erased(self):
        original,crop,owner,amb,text,bbox=self.inputs()
        amb.putpixel((4,4),255)
        with self.assertRaisesRegex(BC3Hold,"AMBIGUOUS"):
            apply(original,crop,owner,amb,text,bbox)
    def test_non_mip1_is_not_accidentally_downconverted(self):
        multi,_,_=fixture()
        original,crop,owner,amb,text,bbox=self.inputs()
        with self.assertRaisesRegex(BC3Hold,"MIP_CHAIN"):
            apply(multi,crop,owner,amb,text,bbox)

if __name__=="__main__":
    unittest.main()
