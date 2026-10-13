"""Regression checks for upright English references and reversible source pixel mapping."""
import hashlib
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("orientation", ROOT / "tile_orientation_policy.py")
orientation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(orientation)


def make_rgba():
    im = Image.new("RGBA", (5, 3))
    for y in range(3):
        for x in range(5):
            im.putpixel((x,y), (x*23, 50+y*47, 120-y*31, 0 if (x+y)%4==0 else 255))
    buf=BytesIO()
    im.save(buf,format="PNG")
    return im,buf.getvalue()


class OrientationTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.source = self.root / "inputs" / "A" / "HD_EN_TILES_20261014"
        self.source.mkdir(parents=True)
        self.image,self.raw=make_rgba()
        self.sha=hashlib.sha256(self.raw).hexdigest()

    def test_normal_q012_requires_y_flip_to_upright_and_inverts_exactly(self):
        name=orientation.OVERRIDE_Q012
        path=self.source/name
        path.write_bytes(self.raw)
        mapping={"part_filename":name,"part_png_sha256":self.sha,"orientation":"NORMAL"}
        with patch.object(orientation,"ORIGINAL_Q012_SHA",self.sha):
            normalized=orientation.resolve_upright_source(self.root,mapping,path)
            same=orientation.resolve_upright_source(self.root,mapping,path)
        self.assertEqual(normalized["sha256"],same["sha256"])
        self.assertNotEqual(normalized["sha256"],self.sha)
        self.assertEqual(normalized["source_to_upright"],"FLIP_Y")
        self.assertEqual(normalized["upright_to_source"],"FLIP_Y")
        self.assertEqual(path.read_bytes(),self.raw)
        with Image.open(normalized["path"]) as flipped:
            flipped.load()
            self.assertEqual(flipped.size,self.image.size)
            self.assertEqual(flipped.mode,"RGBA")
            self.assertEqual(flipped.tobytes(),ImageOps.flip(self.image).tobytes())
            restored=orientation.restore_source_orientation(flipped,normalized)
        self.assertEqual(restored.tobytes(),self.image.tobytes())
        manifest=Path(normalized["path"]).with_suffix(".orientation.json")
        self.assertEqual(json.loads(manifest.read_text())["source_sha256"],self.sha)

    def test_flipy_named_readable_source_is_not_flipped(self):
        name="example_BASE_READABLE_FLIPY.png"
        path=self.source/name
        path.write_bytes(self.raw)
        mapping={"part_filename":name,"part_png_sha256":self.sha,
                 "orientation":"FLIP_Y_PREVIEW_PER_SPRITE_VERIFY"}
        result=orientation.resolve_upright_source(self.root,mapping,path)
        self.assertEqual(result["path"],str(path.resolve()))
        self.assertEqual(result["sha256"],self.sha)
        self.assertEqual(result["source_to_upright"],"IDENTITY")
        self.assertEqual(result["upright_to_source"],"IDENTITY")
        self.assertEqual(orientation.restore_source_orientation(self.image,result).tobytes(),self.image.tobytes())
        self.assertFalse((self.root / orientation.DERIVED_DIR).exists())

    def test_unknown_normal_not_guessed(self):
        name="unknown_NORMAL.png"
        path=self.source/name
        path.write_bytes(self.raw)
        with self.assertRaisesRegex(ValueError,"ORIENTATION_UNREVIEWED"):
            orientation.resolve_upright_source(self.root,{
                "part_filename":name,"part_png_sha256":self.sha,"orientation":"NORMAL"},path)

    def test_existing_derived_modification_blocks_reuse(self):
        name=orientation.OVERRIDE_Q012
        path=self.source/name
        path.write_bytes(self.raw)
        row={"part_filename":name,"part_png_sha256":self.sha,"orientation":"NORMAL"}
        with patch.object(orientation,"ORIGINAL_Q012_SHA",self.sha):
            normalized=orientation.resolve_upright_source(self.root,row,path)
            Path(normalized["path"]).write_bytes(self.raw)
            with self.assertRaisesRegex(ValueError,"UPRIGHT_DERIVATIVE_SHA_MISMATCH"):
                orientation.resolve_upright_source(self.root,row,path)


if __name__=="__main__":
    unittest.main()