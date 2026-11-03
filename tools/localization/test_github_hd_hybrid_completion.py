import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw

SOURCE = Path(__file__).with_name("github_hd_hybrid_completion.py")
spec = importlib.util.spec_from_file_location("hd_hybrid", SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def row(rid, box, korean="한글"):
    return {
        "roi_id": rid,
        "english": "EN",
        "korean": korean,
        "_bbox": list(box),
        "_candidate_rel": "localization/automation_inputs/candidate_outputs/A/" + rid + "_source_k.png",
    }


class HybridCompletionTest(unittest.TestCase):
    def setUp(self):
        self.font = m.font_path()

    def test_overlap_is_relocated_not_dropped(self):
        source = Image.new("RGBA", (256, 128), (0, 0, 0, 0))
        rows = [
            row("Q001_1111111111111111", (20, 20, 100, 60), "작게"),
            row("Q001_2222222222222222", (10, 10, 190, 105), "큰영역"),
        ]
        out, accepted, held, represented, changed = m.fallback_compose(source, rows, self.font)
        self.assertEqual(len(accepted) + len(represented), 2)
        self.assertEqual(held, [])
        self.assertGreater(changed, 0)
        self.assertIsNotNone(out.getchannel("A").getbbox())

    def test_near_duplicate_is_accounted_once(self):
        source = Image.new("RGBA", (256, 128), (0, 0, 0, 0))
        rows = [
            row("Q001_3333333333333333", (20, 20, 120, 70), "동일"),
            row("Q001_4444444444444444", (18, 18, 122, 72), "동일"),
        ]
        _, accepted, held, represented, _ = m.fallback_compose(source, rows, self.font)
        self.assertEqual(len(accepted), 1)
        self.assertEqual(len(represented), 1)
        self.assertEqual(held, [])

    def test_ab_replacement_cannot_escape_fallback_ink_box(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rel = "localization/automation_inputs/candidate_outputs/A/Q001_5555555555555555_source_k.png"
            p = root / rel
            p.parent.mkdir(parents=True)
            candidate = Image.new("RGBA", (100, 50), (0, 0, 0, 0))
            ImageDraw.Draw(candidate).rectangle((10, 10, 89, 39), fill=(255, 255, 255, 255))
            candidate.save(p)

            base = Image.new("RGBA", (200, 100), (0, 0, 0, 0))
            ImageDraw.Draw(base).rectangle((50, 30, 119, 59), fill=(20, 20, 20, 255))
            accepted = [{
                "roi_id": "Q001_5555555555555555",
                "bbox": [40, 20, 140, 80],
                "placement_bbox": [40, 20, 140, 80],
                "ink_box": [50, 30, 120, 60],
                "resolution": "FALLBACK_PRIMARY",
                "_row": row("Q001_5555555555555555", (40, 20, 140, 80), "교체"),
            }]
            out, applied, holds = m.apply_ab_candidates(root, base, accepted)
            self.assertEqual(len(applied), 1)
            self.assertEqual(holds, [])
            diff = ImageChops.difference(base, out)
            outside = np.asarray(diff)
            mask = np.zeros((100, 200), dtype=bool)
            mask[30:60, 50:120] = True
            changed = np.any(outside != 0, axis=2)
            self.assertEqual(int(np.count_nonzero(changed & ~mask)), 0)

    def test_output_dds_roundtrip_normal_and_flipy(self):
        im = Image.new("RGBA", (64, 32), (12, 34, 56, 200))
        for orientation in ("NORMAL", "FLIPY"):
            raw = m.encode_rgba_dds(im, orientation)
            self.assertTrue(raw.startswith(b"DDS "))
            with Image.open(io.BytesIO(raw)) as decoded:
                native = decoded.convert("RGBA")
            expected = im if orientation == "NORMAL" else im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            self.assertIsNone(ImageChops.difference(native, expected).getbbox())


if __name__ == "__main__":
    unittest.main()
