import hashlib
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from car_importer.cli import StageError, validate_ovc2


def fixture():
    # 3 vertices, 1 triangle, single 16x16 ARGB32 DDS, correct C++ OVRCABH2 contract.
    vertex = struct.pack("<8f", 0, 0, 0, 0, 1, 0, 0, 0)
    group = (struct.pack("<HHIII", 3, 0, 3, 3, 4) + b"F50" +
             vertex * 3 + struct.pack("<III", 0, 1, 2))
    tex = bytearray(128)
    tex[:4] = b"DDS "
    struct.pack_into("<I", tex, 4, 124)
    struct.pack_into("<I", tex, 12, 16)
    struct.pack_into("<I", tex, 16, 16)
    struct.pack_into("<I", tex, 28, 1)
    struct.pack_into("<I", tex, 76, 32)
    struct.pack_into("<I", tex, 88, 32)
    pixels = bytes((100, 50, 200, 255)) * (16 * 16)
    payload = group + struct.pack("<I", len(tex)+len(pixels)) + tex + pixels
    return b"OVRCABH2" + struct.pack("<7I", 2, 1, 1, 3, 1, len(payload),
                                       zlib.crc32(payload)) + payload


class Ovc2SafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = Path(self.tmp.name) / "F50_External_Test.ovc"

    def test_valid_ovc2(self):
        self.p.write_bytes(fixture())
        got = validate_ovc2(self.p)
        self.assertEqual((got["groups"], got["materials"], got["triangles"]), (1, 1, 1))
        self.assertEqual(got["sha256"], hashlib.sha256(self.p.read_bytes()).hexdigest())

    def test_rejects_crc(self):
        b = bytearray(fixture())
        b[44] ^= 4
        self.p.write_bytes(b)
        with self.assertRaisesRegex(StageError, "CRC"):
            validate_ovc2(self.p)

    def test_rejects_bad_vertex_index(self):
        b = bytearray(fixture())
        offset = 36 + 16 + 3 + 3 * 32
        struct.pack_into("<I", b, offset + 8, 99)
        struct.pack_into("<I", b, 32, zlib.crc32(b[36:]))
        self.p.write_bytes(b)
        with self.assertRaisesRegex(StageError, "Index range"):
            validate_ovc2(self.p)

    def test_rejects_wrong_format(self):
        self.p.write_bytes(b"OVRCABH3" + fixture()[8:])
        with self.assertRaisesRegex(StageError, "OVRCABH2"):
            validate_ovc2(self.p)


if __name__ == "__main__":
    unittest.main()
