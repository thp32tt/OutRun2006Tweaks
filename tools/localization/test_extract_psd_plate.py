import tempfile
import unittest
from pathlib import Path
from PIL import Image
from psd_tools import PSDImage
from psd_tools.api.layers import PixelLayer
from extract_psd_plate import extract
from plate_library import digest


class PsdTests(unittest.TestCase):
    def test_native_layer_and_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = Path(tmp); psd = PSDImage.new('RGB', (16, 12))
            PixelLayer.frompil(Image.new('RGBA', (4, 3), (12, 24, 36, 255)), psd, name='background', top=2, left=3)
            source = b / 'source.psd'; psd.save(source)
            report = extract(source, digest(source.read_bytes()), [0], b / 'layer.png')
            self.assertEqual(report['status'], 'EXTRACTED_UNVERIFIED')
            with Image.open(b / 'layer.png') as im:
                self.assertEqual(im.size, (16, 12)); self.assertEqual(im.getpixel((3, 2)), (12, 24, 36, 255))
            with self.assertRaises(ValueError): extract(source, '0' * 64, [0], b / 'bad.png')
            with self.assertRaises(ValueError): extract(source, digest(source.read_bytes()), [], b / 'bad.png')
            with self.assertRaises(ValueError): extract(source, digest(source.read_bytes()), [9], b / 'bad.png')


if __name__ == '__main__':
    unittest.main()
