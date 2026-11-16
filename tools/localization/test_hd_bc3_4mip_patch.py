"""Synthetic original-header and four-level protected-source DXT5 regressions."""
import io,struct,unittest
from PIL import Image,ImageDraw
from hd_bc3_native_codec import encode_bc3_block
from hd_bc3_4mip_patch import read_levels,safe_patch,BC3Hold

def fixture():
    w=h=64
    base=Image.new("RGBA",(w,h),(0,0,0,0))
    draw=ImageDraw.Draw(base)
    draw.rectangle((16,16,17,47),fill=(255,255,255,255))
    draw.rectangle((56,56,57,57),fill=(255,255,255,255))
    head=bytearray(128)
    head[:4]=b"DDS "
    for offset,val in ((4,124),(12,h),(16,w),(28,4),
                       (76,32),(80,4),(108,0x1000)):
        struct.pack_into("<I",head,offset,val)
    head[84:88]=b"DXT5"
    out=bytearray(head)
    for level in range(4):
        im=base.resize((w>>level,h>>level),Image.Resampling.BOX)
        for y in range(0,im.height,4):
            for x in range(0,im.width,4):
                pixels=[im.getpixel((x+i%4,y+i//4)) for i in range(16)]
                block=bytearray(encode_bc3_block(pixels))
                if all(p[3]==0 for p in pixels):
                    # Transparent BC3 sprites may retain original white
                    # endpoints; this fixture tests the safe existing
                    # palette path without inventing new RGB endpoints.
                    struct.pack_into("<HH",block,8,0xffff,0)
                    block[12:16]=bytes(4)
                out.extend(block)
    owner=Image.new("L",(w,h),0)
    ImageDraw.Draw(owner).rectangle((16,16,17,47),fill=255)
    korean=Image.new("RGBA",(w,h),(0,0,0,0))
    ImageDraw.Draw(korean).rectangle((24,16,25,47),fill=(255,255,255,255))
    return bytes(out),owner,korean

class FourMips(unittest.TestCase):
    def test_all_four_native_levels_decode_and_header_sha_layout(self):
        raw,owner,korean=fixture()
        levels=read_levels(raw)
        self.assertEqual([x[3].size for x in levels],
                         [(64,64),(32,32),(16,16),(8,8)])
        self.assertEqual(levels[-1][2],len(raw))
        self.assertEqual(len(raw),128+64*64+32*32+16*16+8*8)
    def test_untouched_source_ownership_is_enforced(self):
        raw,owner,text=fixture()
        owner.putpixel((3,3),255)
        with self.assertRaisesRegex(BC3Hold,"OWNER_NOT_NATIVE_SOURCE_ALPHA"):
            safe_patch(raw,owner,text,[(12,12,36,52)])
    def test_unclaimed_art_cannot_be_edited_by_korean(self):
        raw,owner,text=fixture()
        text.putpixel((56,56),(255,255,255,255))
        with self.assertRaisesRegex(BC3Hold,"MIP_KOREAN_TOUCHES_FOREIGN_ART"):
            safe_patch(raw,owner,text,[(12,12,60,60)])
    def test_four_mip_edited_header_bytes_and_protected_foreign_art(self):
        raw,owner,text=fixture()
        try:
            updated,proof=safe_patch(raw,owner,text,[(12,12,36,52)])
        except BC3Hold as e:
            self.fail("Safe 4mip source-owned white index-palette text failed: "+str(e))
        self.assertEqual(updated[:128],raw[:128])
        self.assertEqual(len(updated),len(raw))
        self.assertEqual(len(proof),4)
        self.assertNotEqual(updated,raw)
        before,after=read_levels(raw),read_levels(updated)
        for a,b in zip(before,after):
            scale=64//a[3].width
            pos=(56//scale,56//scale)
            self.assertEqual(a[3].getpixel(pos),b[3].getpixel(pos))

if __name__=="__main__":
    unittest.main()
