"""Coverage-first 104-DDS package: exact input, hash and reversible install checks."""
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from make_hd_korean_coverage_first_package import package, digest


class CoverageFirstPackagingTests(unittest.TestCase):
    def fixture(self, root: Path):
        inp = root / "in"
        inp.mkdir()
        files = {}
        atlases = []
        for i in range(104):
            name = f"textures/load/spr_test/{i:08X}_16x16.dds"
            raw = b"DDS " + bytes(124) + bytes([i % 256]) * 24
            files[name] = raw
            atlases.append({
                "target": name, "source_sha256": "a" * 64,
                "output_dds_sha256": digest(raw), "orientation": "NORMAL",
                "fallback_painted": 1, "ab_candidates_applied": 1,
            })
        hybrid_manifest = {
            "status": "TEST_ONLY_NOT_RUNTIME_APPROVED",
            "dds_count": 104,
            "translation_coverage_complete": True,
            "translation_coverage_accounted": 954,
            "entries": {name: digest(raw) for name, raw in files.items()},
        }
        zfile = inp / "OUTRUN_HD_KOREAN_HYBRID_TEST_ONLY.zip"
        with zipfile.ZipFile(zfile, "w") as z:
            for name, raw in files.items():
                z.writestr(name, raw)
            z.writestr("TEST_ONLY_MANIFEST.json", json.dumps(hybrid_manifest))
        report = {
            "schema": "outrun.github-hd-korean-hybrid-completion.v1",
            "release_approved": False, "runtime_validation": "UNTESTED",
            "active_roi_total": 954, "active_dds_total": 104,
            "source_dds_verified": 104, "output_dds_count": 104,
            "translation_coverage_accounted": 954, "translation_coverage_complete": True,
            "fallback_hold_count": 0, "ab_candidate_applied_count": 104,
            "duplicate_translation_represented_count": 0,
            "atlases": atlases, "zip_sha256": digest(zfile.read_bytes()),
        }
        report_file = inp / "qa_report.json"
        report_file.write_text(json.dumps(report), encoding="utf-8")
        installer = inp / "Install-OutRunKoreanTest.ps1"
        installer.write_text("Backup Rollback ConfirmTestOnly ApplyAll", encoding="utf-8")
        return report, report_file, zfile, installer

    def test_104_shas_954_coverage_reversible_package(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            report, qa, z, installer = self.fixture(root)
            result = package(str(qa), str(z), str(installer), str(root / "out"))
            self.assertEqual(result["coverage_accounted"], 954)
            self.assertEqual(result["dds_count"], 104)
            self.assertFalse(result["release_approved"])
            with zipfile.ZipFile(root / "out" / result["archive"]) as final:
                manifest = json.loads(final.read("TEST_ONLY_INSTALL_MANIFEST.json"))
                self.assertEqual(len(manifest["files"]), 104)
                self.assertTrue(manifest["needs_actual_game_test"])
                self.assertEqual(manifest["visual_qa"], "BEST_EFFORT_NOT_INDEPENDENTLY_APPROVED")

    def test_incomplete_coverage_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            report,qa,z,installer=self.fixture(root)
            report["fallback_hold_count"]=1
            qa.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError,"COVERAGE_FIRST_INCOMPLETE"):
                package(str(qa),str(z),str(installer),str(root/"out"))

    def test_source_zip_sha_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            report,qa,z,installer=self.fixture(root)
            report["zip_sha256"]="f"*64
            qa.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError,"SOURCE_OUTPUT_ZIP_SHA"):
                package(str(qa),str(z),str(installer),str(root/"out"))

    def test_wrong_dds_digest_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            report,qa,z,installer=self.fixture(root)
            report["atlases"][0]["output_dds_sha256"]="f"*64
            qa.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError,"SOURCE_HYBRID_MANIFEST"):
                package(str(qa),str(z),str(installer),str(root/"out"))


if __name__ == "__main__":
    unittest.main()
