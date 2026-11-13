"""Regression: edit-before-regenerate and never erase protected native art."""
import io
import unittest

from PIL import Image, ImageDraw
from hd_hold_retry_pipeline import safe_fit_existing, make_task, assert_safe_mask


def fixture(protected_x=(62,66)):
    source=Image.new("RGBA",(140,52),(0,0,0,0))
    draw=ImageDraw.Draw(source)
    draw.rectangle((10,10,59,30),fill=(255,255,255,255))
    draw.rectangle((protected_x[0],10,protected_x[1],30),fill=(0,128,255,255))
    owner=Image.new("L",source.size,0)
    protect=Image.new("L",source.size,0)
    ImageDraw.Draw(owner).rectangle((10,10,59,30),fill=255)
    ImageDraw.Draw(protect).rectangle((protected_x[0],10,protected_x[1],30),fill=255)
    ambiguous=Image.new("L",source.size,0)
    text=Image.new("RGBA",source.size,(0,0,0,0))
    ImageDraw.Draw(text).rectangle((26,12,75,28),fill=(235,220,30,255))
    lines=[{"source":[10,10,100,31],"translated":[26,12,76,29]}]
    return source,owner,protect,ambiguous,text,lines


class HoldRetrySafety(unittest.TestCase):
    def test_collision_attempt_rescues_without_foreign_pixel_change(self):
        source,owner,protect,uncertain,text,lines=fixture()
        output,status,ops=safe_fit_existing(source,owner,protect,uncertain,text,lines)
        self.assertIsNotNone(output)
        self.assertEqual(status,"REVIEW_REQUIRED_PARTIAL_OWNER")
        self.assertEqual(len(ops),1)
        glyph,clean,composite=output
        self.assertIsNone(Image.Image.getbbox(Image.new("L",(1,1),0)))
        self.assertEqual(composite.getpixel((63,20)),source.getpixel((63,20)))
        self.assertEqual(clean.getpixel((30,20))[3],0)
        self.assertIsNotNone(glyph.getchannel("A").getbbox())

    def test_unfixable_collision_stays_hold(self):
        source,owner,protect,uncertain,text,lines=fixture((62,129))
        lines=[{"source":[62,10,129,31],"translated":[26,12,76,29]}]
        output,status,_=safe_fit_existing(source,owner,protect,uncertain,text,lines)
        self.assertIsNone(output)
        self.assertEqual(status,"NO_NONCOLLIDING_NATIVE_FIT")

    def test_mask_partition_rejects_invented_owner(self):
        source,owner,protect,uncertain,text,lines=fixture()
        owner.putpixel((75,1),255)
        with self.assertRaisesRegex(ValueError,"NOT_EXACT_SOURCE_CORE_PARTITION"):
            assert_safe_mask(source,owner,protect,uncertain)

    def test_regen_task_text_only_is_source_and_sha_bound(self):
        source,*_=fixture()
        record={"roi_id":"Q043_0123456789abcdef",
           "source_native_bbox_xyxy":[0,0,140,52],
           "candidate_sha256":"a"*64,
           "hold_reason":"QA_ORIGINAL_LINE_COUNT_NOT_PRESERVED"}
        ticket={"source_dds_path":"textures/load/a/b.dds",
                 "english":"CONTINUE","korean":"계속하기"}
        task,png,error=make_task(record,ticket,source,"A","b"*64)
        self.assertIsNone(error)
        self.assertIn("ONLY_KOREAN_TEXT",task["generation_mode"])
        self.assertEqual(task["reference"]["sha256"],__import__("hashlib").sha256(png).hexdigest())
        self.assertEqual(task["release_approved"] if "release_approved" in task else False,False)


if __name__=="__main__":
    unittest.main()
