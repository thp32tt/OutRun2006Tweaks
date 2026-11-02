"""Isolated regression tests for repository-hosted Korean DDS QA."""
import io
import importlib.util
import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

SRC = Path(__file__).with_name("github_docker_qa.py")
spec = importlib.util.spec_from_file_location("localization_github_qa", SRC)
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)


def bgra_dds(w=16, h=8):
    blob = bytearray(128)
    blob[:4] = b"DDS "
    struct.pack_into("<I", blob, 4, 124)
    struct.pack_into("<I", blob, 12, h)
    struct.pack_into("<I", blob, 16, w)
    struct.pack_into("<I", blob, 28, 1)
    struct.pack_into("<I", blob, 76, 32)
    struct.pack_into("<I", blob, 80, 65)
    struct.pack_into("<I", blob, 88, 32)
    struct.pack_into("<IIII", blob, 92, *qa.NATIVE_MASKS)
    return bytes(blob) + bytes((13,45,178,255)) * (w*h)


class GithubDockerLocalizationQATests(unittest.TestCase):
    def test_native_dds_roundtrip(self):
        img, dims = qa.inspect_native(bgra_dds())
        self.assertEqual((16,8), dims)
        self.assertEqual((178,45,13,255), img.getpixel((0,0)))

    def test_reject_wrong_mask_and_mip(self):
        data=bytearray(bgra_dds())
        struct.pack_into("<I",data,92,0xff)
        with self.assertRaisesRegex(ValueError,"DDS_NOT_SOURCE_NATIVE"):
            qa.inspect_native(data)
        data=bytearray(bgra_dds())
        struct.pack_into("<I",data,28,2)
        with self.assertRaisesRegex(ValueError,"DDS_NOT_SOURCE_NATIVE"):
            qa.inspect_native(data)

    def test_reject_traversal_and_double_entry(self):
        self.assertFalse(qa.safe_name("../textures/load/x.dds"))
        self.assertFalse(qa.safe_name("/textures/load/x.dds"))
        self.assertFalse(qa.safe_name("textures\\load\\x.dds"))
        self.assertTrue(qa.safe_name("textures/load/x.dds"))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"dupe.zip"
            with zipfile.ZipFile(p,"w") as z:
                z.writestr("textures/load/x.dds",b"abcd")
                z.writestr("textures/load/x.dds",b"abcde")
            with zipfile.ZipFile(p) as z:
                with self.assertRaisesRegex(ValueError,"DUPLICATE_ARCHIVE_MEMBER"):
                    qa.zip_members(z)

    def test_deterministic_zip(self):
        def make_zip():
            buf=io.BytesIO()
            with zipfile.ZipFile(buf,"w") as z:
                qa.deterministic_write(z,"textures/load/x.dds",bgra_dds())
                qa.deterministic_write(z,"TEST_ONLY_MANIFEST.json",qa.stable_json({"runtime_validation":"UNTESTED"}))
            return buf.getvalue()
        self.assertEqual(qa.sha(make_zip()),qa.sha(make_zip()))

    def test_reject_missing_crosswalk_without_fabricating_success(self):
        with tempfile.TemporaryDirectory() as d:
            result=qa.audit_candidate_inventory(Path(d))
            self.assertEqual("INPUT_CROSSWALK_MISSING",result["status"])
            self.assertEqual(0,result["on_github"])

    def test_huge_member_rejected_without_extract(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"large.zip"
            with zipfile.ZipFile(p,"w",compression=zipfile.ZIP_DEFLATED) as z:
                z.writestr("textures/load/oversize.dds",b"a"*(qa.MAX_MEMBER+1))
            with zipfile.ZipFile(p) as z:
                with self.assertRaisesRegex(ValueError,"OVERSIZED_MEMBER"):
                    qa.zip_members(z)


if __name__ == "__main__":
    unittest.main()
