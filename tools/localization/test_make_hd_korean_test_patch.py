"""Synthetic regression for existing A/B-only TEST_ONLY DDS install package."""
import importlib.util, json, tempfile, unittest, zipfile
from pathlib import Path

here = Path(__file__).parent
spec = importlib.util.spec_from_file_location("test_patch", here / "make_hd_korean_test_patch.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class TestHDPreviewPackaging(unittest.TestCase):
    def materialize(self, root, bad_path=False):
        root = Path(root)
        target = "textures/load/spr_demo/12345678_64x64.dds"
        if bad_path:
            target = "textures/load/../../escape.dds"
        payload = b"DDS " + bytes(124) + b"source-data"
        zpath = root / m.DDS_ZIP
        with zipfile.ZipFile(zpath, "w") as z:
            z.writestr(target, payload)
            z.writestr(m.SOURCE_MANIFEST, json.dumps({
                "release_approved": False, "game_runtime": "UNTESTED",
                "entries": {target: m.sha256(payload)}}))
        qa = {
            "schema":m.QA_SCHEMA,"active_roi_total":954,"imported_roi_total":954,
            "pending_import":0,"release_approved":False,"runtime_validation":"UNTESTED",
            "source_dds_missing_rows":0,"source_sha_conflict_rows":0,
            "translated_roi_generated":1,"hold_roi_reason_counts":{"SOURCE_HELD":953},
            "native_dds_generated":1,"zip_sha256":m.sha256(zpath.read_bytes()),
            "generated":[{
                "target":target,"dds_sha256":m.sha256(payload),"origin_sha256":"a"*64,
                "orientation":"FLIPY","painted":[{"roi_id":"Q012_1234567890abcdef"}],
                "holds":[]
            }]
        }
        qa_path = root / "qa_report.json"
        qa_path.write_text(json.dumps(qa),encoding="utf-8")
        return qa, qa_path, zpath, here / "Install-OutRunKoreanTest.ps1", root/"out"

    def test_valid_preview_is_reproducible_and_never_release(self):
        with tempfile.TemporaryDirectory() as d:
            qa, report, source, installer, out = self.materialize(d)
            r1=m.stage(report,source,installer,out,"42","b"*40)
            r2=m.stage(report,source,installer,out,"42","b"*40)
            self.assertEqual(r1["output_sha256"],r2["output_sha256"])
            self.assertEqual(r1["translated_roi_test_only"],1)
            self.assertEqual(r1["held_roi"],953)
            with zipfile.ZipFile(out/m.OUTPUT_ZIP) as z:
                man=json.loads(z.read(m.STAGED_MANIFEST))
                self.assertEqual(man["status"],"TEST_ONLY_NOT_RELEASE_APPROVED")
                self.assertFalse(man["release_approved"])
                self.assertEqual(man["runtime_validation"],"UNTESTED")
                self.assertIn(b"ConfirmTestOnly",z.read("Install-OutRunKoreanTest.ps1"))

    def test_invalid_qa_source_sha_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            qa, report, source, installer, out = self.materialize(d)
            qa["zip_sha256"]="0"*64
            report.write_text(json.dumps(qa))
            with self.assertRaisesRegex(AssertionError,"QA_ZIP_SHA_MISMATCH"):
                m.stage(report,source,installer,out,"42","b"*40)

    def test_unsafe_path_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            _, report, source, installer, out = self.materialize(d,bad_path=True)
            with self.assertRaisesRegex(AssertionError,"UNSAFE_DDS_PATH"):
                m.stage(report,source,installer,out,"42","b"*40)

    def test_unapproved_extra_file_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            qa, report, source, installer, out = self.materialize(d)
            with zipfile.ZipFile(source,"a") as z:
                z.writestr("not-part-of-source.exe",b"bad")
            qa["zip_sha256"]=m.sha256(source.read_bytes())
            report.write_text(json.dumps(qa))
            with self.assertRaisesRegex(AssertionError,"UNEXPECTED_SOURCE_FILE"):
                m.stage(report,source,installer,out,"42","b"*40)

    def test_unreviewed_can_never_be_marked_release(self):
        with tempfile.TemporaryDirectory() as d:
            qa, report, source, installer, out = self.materialize(d)
            qa["release_approved"]=True
            report.write_text(json.dumps(qa))
            with self.assertRaisesRegex(AssertionError,"INVALID_APPROVAL"):
                m.stage(report,source,installer,out,"42","b"*40)

if __name__=="__main__":
    unittest.main()
