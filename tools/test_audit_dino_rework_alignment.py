import json
import struct
import tempfile
import unittest
from pathlib import Path

from audit_dino_rework_alignment import audit


def fixture(path, image=b"abcd", vertex=1.0, uv=0.0, translation=0.0):
    blob = struct.pack("<5f", vertex, 0, 0, uv, 0) + image
    doc = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": len(blob)}],
        "bufferViews": [{"buffer": 0, "byteLength": 12},
                        {"buffer": 0, "byteOffset": 12, "byteLength": 8},
                        {"buffer": 0, "byteOffset": 20, "byteLength": len(image)}],
        "accessors": [{"bufferView": 0, "componentType": 5126, "count": 1, "type": "VEC3"},
                      {"bufferView": 1, "componentType": 5126, "count": 1, "type": "VEC2"}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "TEXCOORD_0": 1}}]}],
        "nodes": [{"mesh": 0, "translation": [translation, 0, 0]}],
        "scenes": [{"nodes": [0]}],
        "images": [{"bufferView": 2, "mimeType": "image/png"}],
    }
    metadata = json.dumps(doc).encode()
    metadata += b" " * (-len(metadata) % 4)
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, 28 + len(metadata) + len(blob))
                     + struct.pack("<I4s", len(metadata), b"JSON") + metadata
                     + struct.pack("<I4s", len(blob), b"BIN\0") + blob)


class PreservationTests(unittest.TestCase):
    def test_texture_change(self):
        with tempfile.TemporaryDirectory() as directory:
            before, after = (Path(directory) / name for name in ("before.glb", "after.glb"))
            fixture(before)
            fixture(after, image=b"abcdefgh")
            self.assertEqual(audit(before, after)["changed_images"], [0])

    def test_model_change(self):
        for change in ({"vertex": 2}, {"uv": 0.5}, {"translation": 1}):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                before, after = (Path(directory) / name for name in ("before.glb", "after.glb"))
                fixture(before)
                fixture(after, **change)
                with self.assertRaises(ValueError):
                    audit(before, after)

    def test_truncated_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.glb"
            fixture(path)
            path.write_bytes(path.read_bytes()[:-4])
            with self.assertRaises(ValueError):
                audit(path, path)
