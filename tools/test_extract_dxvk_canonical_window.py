#!/usr/bin/env python3
import hashlib
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import extract_dxvk_canonical_window as sut


def build_fixture(path: Path) -> tuple[bytes, str]:
    data = bytearray(0x400)
    data[0:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<H", data, 0x84, 0x014C)
    struct.pack_into("<H", data, 0x86, 1)
    struct.pack_into("<H", data, 0x94, 0xE0)
    struct.pack_into("<H", data, 0x98, 0x10B)
    struct.pack_into("<I", data, 0x98 + 60, 0x200)
    section = 0x98 + 0xE0
    data[section:section + 8] = b".text\0\0\0"
    struct.pack_into("<I", data, section + 8, 0x180)
    struct.pack_into("<I", data, section + 12, 0x1000)
    struct.pack_into("<I", data, section + 16, 0x200)
    struct.pack_into("<I", data, section + 20, 0x200)
    payload = bytes(range(256)) + bytes(range(256))
    data[0x200:0x400] = payload
    raw = bytes(data)
    path.write_bytes(raw)
    return raw, hashlib.sha256(raw).hexdigest()


class CanonicalWindowTests(unittest.TestCase):
    def test_extracts_exact_rva_window_from_pe_section(self):
        with tempfile.TemporaryDirectory() as td:
            exe = Path(td) / "fixture.exe"
            raw, sha = build_fixture(exe)
            result = sut.extract_window(
                exe_path=exe,
                rva=0x1010,
                length=6,
                expected_sha256=sha,
                source_sha="deadbeef",
            )
            self.assertEqual(result["rva_start"], "0x00001010")
            self.assertEqual(result["rva_end_exclusive"], "0x00001016")
            self.assertEqual(result["length"], 6)
            self.assertEqual(result["section"], ".text")
            self.assertEqual(result["file_offset"], "0x00000210")
            self.assertEqual(result["bytes_hex"], raw[0x210:0x216].hex(" "))
            self.assertEqual(result["canonical_exe_sha256"], sha)
            self.assertEqual(result["source_sha"], "deadbeef")

    def test_rejects_sha256_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            exe = Path(td) / "fixture.exe"
            build_fixture(exe)
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                sut.extract_window(
                    exe_path=exe,
                    rva=0x1000,
                    length=4,
                    expected_sha256="0" * 64,
                )

    def test_rejects_window_past_section_raw_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            exe = Path(td) / "fixture.exe"
            _raw, sha = build_fixture(exe)
            with self.assertRaisesRegex(ValueError, "raw section bytes"):
                sut.extract_window(
                    exe_path=exe,
                    rva=0x11FF,
                    length=2,
                    expected_sha256=sha,
                )

    def test_writes_stable_json_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            exe = root / "fixture.exe"
            _raw, sha = build_fixture(exe)
            out = root / "out" / "window.json"
            rc = sut.main([
                "--exe", str(exe),
                "--rva", "0x1010",
                "--length", "4",
                "--expected-sha256", sha,
                "--source-sha", "abc123",
                "--out", str(out),
            ])
            self.assertEqual(rc, 0)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["rva_start"], "0x00001010")
            self.assertEqual(payload["length"], 4)
            self.assertEqual(payload["source_sha"], "abc123")


class FrontierDiscoveryTests(unittest.TestCase):
    def test_discovers_latest_incomplete_overlap_frontier(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "analyzer.py"
            source.write_text(
                "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_70_PREFIX_END_RVA = 0x1833EA\n"
                "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_70_INCOMPLETE_RVA = 0x1833EA\n"
                "def collect_guarded_gf_target_c_helper_1_third_callee_continuation_70_prefix_proof(pe):\n"
                "    return {}\n"
                "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_71_PREFIX_END_RVA = 0x18342A\n"
                "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_71_INCOMPLETE_RVA = 0x183429\n"
                "def collect_guarded_gf_target_c_helper_1_third_callee_continuation_71_prefix_proof(pe):\n"
                "    return {}\n",
                encoding="utf-8",
            )
            result = sut.discover_frontier_rva(source)
            self.assertEqual(result["continuation_id"], 71)
            self.assertEqual(result["rva"], 0x183429)
            self.assertEqual(result["basis"], "INCOMPLETE_RVA")

    def test_discovers_exact_boundary_when_latest_proof_has_no_incomplete_rva(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "analyzer.py"
            source.write_text(
                "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PREFIX_END_RVA = 0x2000\n"
                "def collect_guarded_gf_target_c_helper_1_third_callee_continuation_9_prefix_proof(pe):\n"
                "    return {}\n",
                encoding="utf-8",
            )
            result = sut.discover_frontier_rva(source)
            self.assertEqual(result["continuation_id"], 9)
            self.assertEqual(result["rva"], 0x2000)
            self.assertEqual(result["basis"], "PREFIX_END_RVA")


if __name__ == "__main__":
    unittest.main()
