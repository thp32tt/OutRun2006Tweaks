import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
import plate_library as p


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        s = Image.new('RGBA', (4, 4), (0, 0, 0, 0)); s.putpixel((1, 1), (255, 255, 255, 255))
        self.source = self.root / 'source.dds'; s.save(self.source)
        clean = Image.new('RGBA', (4, 4), (0, 0, 0, 0))
        mask = Image.new('L', (4, 4)); mask.putpixel((1, 1), 255)
        def ref(im):
            b = io.BytesIO(); im.save(b, format='PNG'); return p.put(self.root, b.getvalue(), '.png')
        self.m = dict(schema=p.VERSION, queue_index=60, region_id='title',
                      source_sha256=p.digest(self.source.read_bytes()), orientation='native_raw',
                      size=[4, 4], background='transparent', clean=ref(clean), removal=ref(mask),
                      producer_evidence=p.put(self.root, b'{"fixture":true}', '.json'))
        self.path = self.save(self.m)

    def save(self, m):
        path = self.root / p.LIB / 'entries' / (p.digest(p.canonical(m)) + '.json')
        p.immutable(path, json.dumps(m).encode()); return path

    def test_integrity_and_real_dds_pixels(self):
        self.assertEqual(p.verify_source(self.root, p.load(self.root, self.path), self.source)['outside_removal_rgba'], 0)

    def test_corruption(self):
        (self.root / self.m['clean']['path']).write_bytes(b'corrupt')
        with self.assertRaises(ValueError): p.load(self.root, self.path)

    def test_no_self_approval(self):
        with self.assertRaises(ValueError): p.review(self.root, self.path, self.m)

    def test_wrong_identity(self):
        with self.assertRaises(ValueError): p.resolve(self.root, 60, 'f' * 64, 'title', 'native_raw')

    def test_wrong_orientation(self):
        with self.assertRaises(ValueError): p.resolve(self.root, 60, self.m['source_sha256'], 'title', 'readable_flip_y')

    def test_wrong_region(self):
        with self.assertRaises(ValueError): p.resolve(self.root, 60, self.m['source_sha256'], 'other', 'native_raw')

    def test_ambiguity(self):
        m = copy.deepcopy(self.m); m['note'] = 'another revision'; self.save(m)
        with self.assertRaises(ValueError): p.resolve(self.root, 60, self.m['source_sha256'], 'title', 'native_raw')

    def test_immutable(self):
        p.immutable(self.path, self.path.read_bytes())
        with self.assertRaises(ValueError): p.immutable(self.path, b'changed')

    def test_path_escape(self):
        with self.assertRaises(ValueError): p.checked(self.root, {'path': '../escape', 'sha256': 'f' * 64})

    def test_source_substitution(self):
        self.source.write_bytes(b'DDS bad')
        with self.assertRaises(ValueError): p.verify_source(self.root, self.m, self.source)

    def test_protected_art_loss(self):
        im = Image.new('RGBA', (4, 4), (0, 0, 0, 0)); im.putpixel((3, 3), (1, 1, 1, 255))
        b = io.BytesIO(); im.save(b, format='PNG'); self.m['clean'] = p.put(self.root, b.getvalue(), '.png')
        with self.assertRaises(ValueError): p.verify_source(self.root, self.m, self.source)

    def test_alpha_residue(self):
        im = Image.open(self.source).convert('RGBA'); b = io.BytesIO(); im.save(b, format='PNG')
        self.m['clean'] = p.put(self.root, b.getvalue(), '.png')
        with self.assertRaises(ValueError): p.verify_source(self.root, self.m, self.source)

    def test_revocation_and_wrong_shard(self):
        r = {'manifest_sha256': self.path.stem, 'reviewer': 'C2', 'status': 'PLATE_PASS',
             'observations': ['TEST FIXTURE ONLY'], 'evidence': [self.m['producer_evidence']]}
        path = self.root / p.LIB / 'reviews' / (self.path.stem + '.json'); path.parent.mkdir()
        path.write_text(json.dumps(r)); p.review(self.root, self.path, self.m)
        for key, value in [('reviewer', 'B'), ('reviewer', 'C1'), ('status', 'REVOKED'), ('manifest_sha256', 'a' * 64), ('evidence', [])]:
            bad = dict(r); bad[key] = value; path.write_text(json.dumps(bad))
            with self.assertRaises(ValueError): p.review(self.root, self.path, self.m)


if __name__ == '__main__':
    unittest.main()
