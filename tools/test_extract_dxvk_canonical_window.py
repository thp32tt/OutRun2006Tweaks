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

    def test_f124_contract_metadata_is_pinned(self):
        self.assertEqual(sut._F124_FRONTIER_CONTINUATION_ID, 95)
        self.assertEqual(sut._F124_START_RVA, 0x00183A0C)
        self.assertEqual(sut._F124_END_RVA, 0x00183A4C)
        self.assertEqual(sut._F124_OVERLAP_BYTES, bytes.fromhex("83"))
        self.assertEqual(len(sut._F124_EXPECTED_BYTES), 64)
        self.assertEqual(
            sut._F124_INHERITED_FORWARD_TARGETS,
            [0x00183A63, 0x00183B6F],
        )

    def test_f124_nonmatching_frontier_is_not_promoted(self):
        result = sut.validate_f124_frontier_contract(
            frontier={"continuation_id": 94, "rva": 0x001839CD},
            payload={},
            exe_path=Path("unused"),
            source_path=Path("unused"),
            length=64,
        )
        self.assertEqual(result, {})


    def test_f126_contract_metadata_is_pinned(self):
        self.assertEqual(sut._F126_FRONTIER_CONTINUATION_ID, 96)
        self.assertEqual(sut._F126_START_RVA, 0x00183A4A)
        self.assertEqual(sut._F126_END_RVA, 0x00183A8A)
        self.assertEqual(sut._F126_OVERLAP_BYTES, bytes.fromhex("8b 4d"))
        self.assertEqual(len(sut._F126_EXPECTED_BYTES), 64)
        self.assertEqual(
            sut._F126_INHERITED_FORWARD_TARGETS,
            [0x00183A50, 0x00183A63, 0x00183B6F],
        )

    def test_f126_nonmatching_frontier_is_not_promoted(self):
        result = sut.validate_f126_frontier_contract(
            frontier={"continuation_id": 95, "rva": 0x00183A0C},
            payload={},
            exe_path=Path("unused"),
            source_path=Path("unused"),
            length=64,
        )
        self.assertEqual(result, {})

    def test_f126_mismatched_payload_fails_closed_before_analyzer_load(self):
        with self.assertRaisesRegex(ValueError, "F126 canonical frontier contract mismatch"):
            sut.validate_f126_frontier_contract(
                frontier={"continuation_id": 96, "rva": 0x00183A4A},
                payload={
                    "rva_start": "0x00183A4A",
                    "rva_end_exclusive": "0x00183A8A",
                    "section": ".text",
                    "bytes_hex": "8b 4d",
                },
                exe_path=Path("unused"),
                source_path=Path("unused"),
                length=64,
            )

    def test_f128_contract_metadata_is_pinned(self):
        self.assertEqual(sut._F128_FRONTIER_CONTINUATION_ID, 97)
        self.assertEqual(sut._F128_START_RVA, 0x00183A8A)
        self.assertEqual(sut._F128_END_RVA, 0x00183ACA)
        self.assertEqual(len(sut._F128_EXPECTED_BYTES), 64)
        self.assertFalse(hasattr(sut, "_F128_OVERLAP_BYTES"))
        self.assertEqual(
            sut._F128_INHERITED_FORWARD_TARGETS,
            [0x00183B60, 0x00183B6E, 0x00183B6F],
        )
        self.assertEqual(
            sut._F128_PREDECESSOR_STATUS,
            "EXACT_183A4A_TO_183A8A_CONTROL_FLOW_BOUNDARY_PROVEN",
        )

    def test_f128_nonmatching_frontier_is_not_promoted(self):
        result = sut.validate_f128_frontier_contract(
            frontier={"continuation_id": 96, "rva": 0x00183A4A},
            payload={},
            exe_path=Path("unused"),
            source_path=Path("unused"),
            length=64,
        )
        self.assertEqual(result, {})

    def test_f128_mismatched_payload_fails_closed_before_analyzer_load(self):
        with self.assertRaisesRegex(ValueError, "F128 canonical frontier contract mismatch"):
            sut.validate_f128_frontier_contract(
                frontier={"continuation_id": 97, "rva": 0x00183A8A},
                payload={
                    "rva_start": "0x00183A8A",
                    "rva_end_exclusive": "0x00183ACA",
                    "section": ".text",
                    "bytes_hex": "8b 35",
                },
                exe_path=Path("unused"),
                source_path=Path("unused"),
                length=64,
            )


    def test_f130_contract_metadata_is_pinned(self):
        self.assertEqual(sut._F130_FRONTIER_CONTINUATION_ID, 98)
        self.assertEqual(sut._F130_START_RVA, 0x00183AC7)
        self.assertEqual(sut._F130_END_RVA, 0x00183B07)
        self.assertEqual(sut._F130_OVERLAP_BYTES, bytes.fromhex("83 a4 88"))
        self.assertEqual(len(sut._F130_EXPECTED_BYTES), 64)
        self.assertEqual(
            sut._F130_INHERITED_FORWARD_TARGETS,
            [0x00183B60, 0x00183B6E, 0x00183B6F],
        )
        self.assertEqual(
            sut._F130_PREDECESSOR_STATUS,
            "EXACT_183A8A_TO_183AC7_CONTROL_FLOW_WITH_183AC7_CUT_EDGE_PROVEN",
        )

    def test_f130_nonmatching_frontier_is_not_promoted(self):
        result = sut.validate_f130_frontier_contract(
            frontier={"continuation_id": 97, "rva": 0x00183A8A},
            payload={},
            exe_path=Path("unused"),
            source_path=Path("unused"),
            length=64,
        )
        self.assertEqual(result, {})

    def test_f130_mismatched_payload_fails_closed_before_analyzer_load(self):
        with self.assertRaisesRegex(ValueError, "F130 canonical frontier contract mismatch"):
            sut.validate_f130_frontier_contract(
                frontier={"continuation_id": 98, "rva": 0x00183AC7},
                payload={
                    "rva_start": "0x00183AC7",
                    "rva_end_exclusive": "0x00183B07",
                    "section": ".text",
                    "bytes_hex": "83 a4 88",
                },
                exe_path=Path("unused"),
                source_path=Path("unused"),
                length=64,
            )

    def test_f130_validator_is_wired_into_frontier_main(self):
        self.assertIn("validate_f130_frontier_contract", sut.main.__code__.co_names)

    def test_f132_contract_metadata_is_pinned(self):
        self.assertEqual(sut._F132_FRONTIER_CONTINUATION_ID, 99)
        self.assertEqual(sut._F132_START_RVA, 0x00183B07)
        self.assertEqual(sut._F132_END_RVA, 0x00183B47)
        self.assertEqual(len(sut._F132_EXPECTED_BYTES), 64)
        self.assertEqual(
            sut._F132_INHERITED_FORWARD_TARGETS,
            [0x00183B60, 0x00183B6E, 0x00183B6F],
        )
        self.assertEqual(
            sut._F132_PREDECESSOR_STATUS,
            "EXACT_183AC7_TO_183B07_CONTROL_FLOW_BOUNDARY_PROVEN",
        )
        self.assertEqual(
            sut._F132_RAW_OUTBOUND_REL32,
            [(0x00183B39, 0x00180340)],
        )
        self.assertEqual(sut._F132_TRAILING_OVERLAP_RVA, 0x00183B44)
        self.assertEqual(
            sut._F132_TRAILING_OVERLAP_BYTES,
            bytes.fromhex("ff 0d 44"),
        )

    def test_f132_nonmatching_frontier_is_not_promoted(self):
        result = sut.validate_f132_frontier_contract(
            frontier={"continuation_id": 98, "rva": 0x00183AC7},
            payload={},
            exe_path=Path("unused"),
            source_path=Path("unused"),
            length=64,
        )
        self.assertEqual(result, {})

    def test_f132_mismatched_payload_fails_closed_before_analyzer_load(self):
        with self.assertRaisesRegex(ValueError, "F132 canonical frontier contract mismatch"):
            sut.validate_f132_frontier_contract(
                frontier={"continuation_id": 99, "rva": 0x00183B07},
                payload={
                    "rva_start": "0x00183B07",
                    "rva_end_exclusive": "0x00183B47",
                    "section": ".text",
                    "bytes_hex": "6a 00",
                },
                exe_path=Path("unused"),
                source_path=Path("unused"),
                length=64,
            )

    def test_f132_positive_contract_preserves_rel32_and_trailing_overlap(self):
        class FakeAnalyzer:
            @staticmethod
            def parse_pe(_data):
                return object()

            @staticmethod
            def collect_guarded_gf_target_c_helper_1_third_callee_continuation_99_prefix_proof(_pe):
                return {
                    "status": "EXACT_183AC7_TO_183B07_CONTROL_FLOW_BOUNDARY_PROVEN",
                    "prefix_end_rva": 0x00183B07,
                    "capture_end_rva": 0x00183B07,
                    "prefix_end_matches": True,
                    "capture_boundary_matches": True,
                    "unresolved_forward_targets": [0x00183B60, 0x00183B6E, 0x00183B6F],
                    "continuation_status": "COMPLETE_INSTRUCTIONS_END_AT_183B07_EXACT_CAPTURE_BOUNDARY_NO_OVERLAP_DEBT",
                }

            @staticmethod
            def collect_raw_inbound_rel32_candidates(_pe, _rva):
                return []

            @staticmethod
            def collect_raw_rel32_call_candidates(_pe, _rva, _length):
                return [{
                    "call_rva": 0x00183B39,
                    "target_rva": 0x00180340,
                    "target_section": ".text",
                    "known_target": "",
                }]

        original_loader = sut._load_frontier_analyzer
        try:
            sut._load_frontier_analyzer = lambda _source_path: FakeAnalyzer
            with tempfile.TemporaryDirectory() as td:
                exe = Path(td) / "canonical.exe"
                exe.write_bytes(b"fixture")
                result = sut.validate_f132_frontier_contract(
                    frontier={"continuation_id": 99, "rva": 0x00183B07},
                    payload={
                        "rva_start": "0x00183B07",
                        "rva_end_exclusive": "0x00183B47",
                        "section": ".text",
                        "bytes_hex": sut._F132_EXPECTED_BYTES.hex(" "),
                    },
                    exe_path=exe,
                    source_path=Path("unused"),
                    length=64,
                )
        finally:
            sut._load_frontier_analyzer = original_loader

        self.assertEqual(
            result["frontier_contract_status"],
            "EXACT_EXE_183B07_TO_183B47_PROVENANCE_CAPTURED",
        )
        self.assertEqual(result["frontier_raw_inbound_rel32_count"], 0)
        self.assertEqual(result["frontier_raw_outbound_rel32_count"], 1)
        self.assertEqual(
            result["frontier_raw_outbound_rel32"],
            [{"call_rva": "0x00183B39", "target_rva": "0x00180340"}],
        )
        self.assertEqual(result["frontier_trailing_overlap_rva"], "0x00183B44")
        self.assertEqual(result["frontier_trailing_overlap_bytes"], "ff 0d 44")
        self.assertTrue(result["frontier_next_overlap_required"])
        self.assertEqual(result["frontier_runtime_validation"], "UNTESTED")

    def test_f132_validator_is_wired_into_frontier_main(self):
        self.assertIn("validate_f132_frontier_contract", sut.main.__code__.co_names)


    def test_f134_contract_metadata_is_pinned(self):
        self.assertEqual(sut._F134_FRONTIER_CONTINUATION_ID, 100)
        self.assertEqual(sut._F134_START_RVA, 0x00183B44)
        self.assertEqual(sut._F134_END_RVA, 0x00183B84)
        self.assertEqual(len(sut._F134_EXPECTED_BYTES), 64)
        self.assertEqual(
            sut._F134_INHERITED_FORWARD_TARGETS,
            [0x00183B60, 0x00183B6E, 0x00183B6F],
        )
        self.assertEqual(
            sut._F134_PREDECESSOR_STATUS,
            "EXACT_183B07_TO_183B44_CONTROL_FLOW_WITH_183B44_CUT_EDGE_PROVEN",
        )
        self.assertEqual(
            sut._F134_REQUIRED_OVERLAP_INSTRUCTION,
            bytes.fromhex("ff 0d 44 bc 98 00"),
        )
        self.assertEqual(sut._F134_TRAILING_OVERLAP_RVA, 0x00183B83)
        self.assertEqual(sut._F134_TRAILING_OVERLAP_BYTES, bytes.fromhex("75"))

    def test_f134_nonmatching_frontier_is_not_promoted(self):
        result = sut.validate_f134_frontier_contract(
            frontier={"continuation_id": 99, "rva": 0x00183B07},
            payload={},
            exe_path=Path("unused"),
            source_path=Path("unused"),
            length=64,
        )
        self.assertEqual(result, {})

    def test_f134_mismatched_payload_fails_closed_before_analyzer_load(self):
        with self.assertRaisesRegex(ValueError, "F134 canonical frontier contract mismatch"):
            sut.validate_f134_frontier_contract(
                frontier={"continuation_id": 100, "rva": 0x00183B44},
                payload={
                    "rva_start": "0x00183B44",
                    "rva_end_exclusive": "0x00183B84",
                    "section": ".text",
                    "bytes_hex": "ff 0d 44",
                },
                exe_path=Path("unused"),
                source_path=Path("unused"),
                length=64,
            )

    def test_f134_positive_contract_consumes_overlap_and_preserves_next_cut(self):
        class FakeAnalyzer:
            @staticmethod
            def parse_pe(_data):
                return object()

            @staticmethod
            def collect_guarded_gf_target_c_helper_1_third_callee_continuation_100_prefix_proof(_pe):
                return {
                    "status": "EXACT_183B07_TO_183B44_CONTROL_FLOW_WITH_183B44_CUT_EDGE_PROVEN",
                    "prefix_end_rva": 0x00183B44,
                    "incomplete_rva": 0x00183B44,
                    "incomplete_bytes": "ff 0d 44",
                    "capture_edge_matches": True,
                    "unresolved_forward_targets": [0x00183B60, 0x00183B6E, 0x00183B6F],
                    "continuation_status": "COMPLETE_INSTRUCTIONS_END_AT_183B44_TRAILING_FF0D44_REQUIRES_OVERLAP",
                }

            @staticmethod
            def collect_raw_inbound_rel32_candidates(_pe, _rva):
                return []

            @staticmethod
            def collect_raw_rel32_call_candidates(_pe, _rva, _length):
                return []

        original_loader = sut._load_frontier_analyzer
        try:
            sut._load_frontier_analyzer = lambda _source_path: FakeAnalyzer
            with tempfile.TemporaryDirectory() as td:
                exe = Path(td) / "canonical.exe"
                exe.write_bytes(b"fixture")
                result = sut.validate_f134_frontier_contract(
                    frontier={"continuation_id": 100, "rva": 0x00183B44},
                    payload={
                        "rva_start": "0x00183B44",
                        "rva_end_exclusive": "0x00183B84",
                        "section": ".text",
                        "bytes_hex": sut._F134_EXPECTED_BYTES.hex(" "),
                    },
                    exe_path=exe,
                    source_path=Path("unused"),
                    length=64,
                )
        finally:
            sut._load_frontier_analyzer = original_loader

        self.assertEqual(
            result["frontier_contract_status"],
            "EXACT_EXE_183B44_TO_183B84_PROVENANCE_CAPTURED",
        )
        self.assertEqual(
            result["frontier_start_boundary_status"],
            "F133_MANDATORY_OVERLAP_FULL_INSTRUCTION_CONSUMED",
        )
        self.assertEqual(
            result["frontier_required_overlap_instruction"],
            "ff 0d 44 bc 98 00",
        )
        self.assertEqual(result["frontier_raw_inbound_rel32_count"], 0)
        self.assertEqual(result["frontier_raw_outbound_rel32_count"], 0)
        self.assertEqual(result["frontier_trailing_overlap_rva"], "0x00183B83")
        self.assertEqual(result["frontier_trailing_overlap_bytes"], "75")
        self.assertTrue(result["frontier_next_overlap_required"])
        self.assertEqual(result["frontier_runtime_validation"], "UNTESTED")

    def test_f134_validator_is_wired_into_frontier_main(self):
        self.assertIn("validate_f134_frontier_contract", sut.main.__code__.co_names)



    def test_f136_contract_metadata_is_pinned(self):
        self.assertEqual(sut._F136_FRONTIER_CONTINUATION_ID, 101)
        self.assertEqual(sut._F136_START_RVA, 0x00183B83)
        self.assertEqual(sut._F136_END_RVA, 0x00183BC3)
        self.assertEqual(len(sut._F136_EXPECTED_BYTES), 64)
        self.assertEqual(sut._F136_INHERITED_FORWARD_TARGETS, [])
        self.assertEqual(
            sut._F136_PREDECESSOR_STATUS,
            "EXACT_183B44_TO_183B83_CONTROL_FLOW_WITH_183B83_CUT_EDGE_PROVEN",
        )
        self.assertEqual(sut._F136_PREDECESSOR_CUT_BYTES, bytes.fromhex("75"))
        self.assertEqual(sut._F136_REQUIRED_OVERLAP_INSTRUCTION, bytes.fromhex("75 34"))
        self.assertEqual(sut._F136_TRAILING_OVERLAP_RVA, 0x00183BC0)
        self.assertEqual(sut._F136_TRAILING_OVERLAP_BYTES, bytes.fromhex("68 c4 41"))

    def test_f136_nonmatching_frontier_is_not_promoted(self):
        result = sut.validate_f136_frontier_contract(
            frontier={"continuation_id": 100, "rva": 0x00183B44},
            payload={},
            exe_path=Path("unused"),
            source_path=Path("unused"),
            length=64,
        )
        self.assertEqual(result, {})

    def test_f136_mismatched_payload_fails_closed_before_analyzer_load(self):
        with self.assertRaisesRegex(ValueError, "F136 canonical frontier contract mismatch"):
            sut.validate_f136_frontier_contract(
                frontier={"continuation_id": 101, "rva": 0x00183B83},
                payload={
                    "rva_start": "0x00183B83",
                    "rva_end_exclusive": "0x00183BC3",
                    "section": ".text",
                    "bytes_hex": "75",
                },
                exe_path=Path("unused"),
                source_path=Path("unused"),
                length=64,
            )

    def test_f136_positive_contract_consumes_overlap_and_preserves_next_cut(self):
        class FakeAnalyzer:
            @staticmethod
            def parse_pe(_data):
                return object()

            @staticmethod
            def collect_guarded_gf_target_c_helper_1_third_callee_continuation_101_prefix_proof(_pe):
                return {
                    "status": "EXACT_183B44_TO_183B83_CONTROL_FLOW_WITH_183B83_CUT_EDGE_PROVEN",
                    "prefix_end_rva": 0x00183B83,
                    "incomplete_rva": 0x00183B83,
                    "incomplete_bytes": "75",
                    "capture_edge_matches": True,
                    "unresolved_forward_targets": [],
                    "remaining_predecessor_external_targets": [],
                    "continuation_status": "COMPLETE_INSTRUCTIONS_END_AT_183B83_TRAILING_75_REQUIRES_OVERLAP",
                }

            @staticmethod
            def collect_raw_inbound_rel32_candidates(_pe, _rva):
                return []

            @staticmethod
            def collect_raw_rel32_call_candidates(_pe, _rva, _length):
                return []

        original_loader = sut._load_frontier_analyzer
        try:
            sut._load_frontier_analyzer = lambda _source_path: FakeAnalyzer
            with tempfile.TemporaryDirectory() as td:
                exe = Path(td) / "canonical.exe"
                exe.write_bytes(b"fixture")
                result = sut.validate_f136_frontier_contract(
                    frontier={"continuation_id": 101, "rva": 0x00183B83},
                    payload={
                        "rva_start": "0x00183B83",
                        "rva_end_exclusive": "0x00183BC3",
                        "section": ".text",
                        "bytes_hex": sut._F136_EXPECTED_BYTES.hex(" "),
                    },
                    exe_path=exe,
                    source_path=Path("unused"),
                    length=64,
                )
        finally:
            sut._load_frontier_analyzer = original_loader

        self.assertEqual(
            result["frontier_contract_status"],
            "EXACT_EXE_183B83_TO_183BC3_PROVENANCE_CAPTURED",
        )
        self.assertEqual(
            result["frontier_start_boundary_status"],
            "F135_MANDATORY_OVERLAP_FULL_INSTRUCTION_CONSUMED",
        )
        self.assertEqual(result["frontier_predecessor_cut_bytes"], "75")
        self.assertEqual(result["frontier_required_overlap_instruction"], "75 34")
        self.assertEqual(result["frontier_inherited_unresolved_forward_targets"], [])
        self.assertEqual(result["frontier_raw_inbound_rel32_count"], 0)
        self.assertEqual(result["frontier_raw_outbound_rel32_count"], 0)
        self.assertEqual(result["frontier_trailing_overlap_rva"], "0x00183BC0")
        self.assertEqual(result["frontier_trailing_overlap_bytes"], "68 c4 41")
        self.assertTrue(result["frontier_next_overlap_required"])
        self.assertEqual(result["frontier_runtime_validation"], "UNTESTED")

    def test_f136_validator_is_wired_into_frontier_main(self):
        self.assertIn("validate_f136_frontier_contract", sut.main.__code__.co_names)


    def test_f138_contract_metadata_is_pinned(self):
        self.assertEqual(sut._F138_FRONTIER_CONTINUATION_ID, 102)
        self.assertEqual(sut._F138_START_RVA, 0x00183BC0)
        self.assertEqual(sut._F138_END_RVA, 0x00183C00)
        self.assertEqual(len(sut._F138_EXPECTED_BYTES), 64)
        self.assertEqual(sut._F138_INHERITED_FORWARD_TARGETS, [])
        self.assertEqual(
            sut._F138_PREDECESSOR_STATUS,
            "EXACT_183B83_TO_183BC0_CONTROL_FLOW_WITH_183BC0_CUT_EDGE_PROVEN",
        )
        self.assertEqual(sut._F138_PREDECESSOR_CUT_BYTES, bytes.fromhex("68 c4 41"))
        self.assertEqual(
            sut._F138_REQUIRED_OVERLAP_INSTRUCTION,
            bytes.fromhex("68 c4 41 00 00"),
        )
        self.assertEqual(sut._F138_TRAILING_OVERLAP_RVA, 0x00183BFE)
        self.assertEqual(sut._F138_TRAILING_OVERLAP_BYTES, bytes.fromhex("ff 76"))

    def test_f138_nonmatching_frontier_is_not_promoted(self):
        result = sut.validate_f138_frontier_contract(
            frontier={"continuation_id": 101, "rva": 0x00183B83},
            payload={},
            exe_path=Path("unused"),
            source_path=Path("unused"),
            length=64,
        )
        self.assertEqual(result, {})

    def test_f138_mismatched_payload_fails_closed_before_analyzer_load(self):
        with self.assertRaisesRegex(ValueError, "F138 canonical frontier contract mismatch"):
            sut.validate_f138_frontier_contract(
                frontier={"continuation_id": 102, "rva": 0x00183BC0},
                payload={
                    "rva_start": "0x00183BC0",
                    "rva_end_exclusive": "0x00183C00",
                    "section": ".text",
                    "bytes_hex": "68 c4 41",
                },
                exe_path=Path("unused"),
                source_path=Path("unused"),
                length=64,
            )

    def test_f138_positive_contract_consumes_push_and_preserves_next_cut(self):
        class FakeAnalyzer:
            @staticmethod
            def parse_pe(_data):
                return object()

            @staticmethod
            def collect_guarded_gf_target_c_helper_1_third_callee_continuation_102_prefix_proof(_pe):
                return {
                    "status": "EXACT_183B83_TO_183BC0_CONTROL_FLOW_WITH_183BC0_CUT_EDGE_PROVEN",
                    "prefix_end_rva": 0x00183BC0,
                    "incomplete_rva": 0x00183BC0,
                    "incomplete_bytes": "68 c4 41",
                    "capture_edge_matches": True,
                    "unresolved_forward_targets": [],
                    "continuation_status": "COMPLETE_INSTRUCTIONS_END_AT_183BC0_TRAILING_68C441_REQUIRES_OVERLAP",
                }

            @staticmethod
            def collect_raw_inbound_rel32_candidates(_pe, _rva):
                return []

            @staticmethod
            def collect_raw_rel32_call_candidates(_pe, _rva, _length):
                return []

        original_loader = sut._load_frontier_analyzer
        try:
            sut._load_frontier_analyzer = lambda _source_path: FakeAnalyzer
            with tempfile.TemporaryDirectory() as td:
                exe = Path(td) / "canonical.exe"
                exe.write_bytes(b"fixture")
                result = sut.validate_f138_frontier_contract(
                    frontier={"continuation_id": 102, "rva": 0x00183BC0},
                    payload={
                        "rva_start": "0x00183BC0",
                        "rva_end_exclusive": "0x00183C00",
                        "section": ".text",
                        "bytes_hex": sut._F138_EXPECTED_BYTES.hex(" "),
                    },
                    exe_path=exe,
                    source_path=Path("unused"),
                    length=64,
                )
        finally:
            sut._load_frontier_analyzer = original_loader

        self.assertEqual(
            result["frontier_contract_status"],
            "EXACT_EXE_183BC0_TO_183C00_PROVENANCE_CAPTURED",
        )
        self.assertEqual(
            result["frontier_start_boundary_status"],
            "F137_MANDATORY_OVERLAP_FULL_INSTRUCTION_CONSUMED",
        )
        self.assertEqual(result["frontier_predecessor_cut_bytes"], "68 c4 41")
        self.assertEqual(
            result["frontier_required_overlap_instruction"],
            "68 c4 41 00 00",
        )
        self.assertEqual(result["frontier_inherited_unresolved_forward_targets"], [])
        self.assertEqual(result["frontier_raw_inbound_rel32_count"], 0)
        self.assertEqual(result["frontier_raw_outbound_rel32_count"], 0)
        self.assertEqual(result["frontier_trailing_overlap_rva"], "0x00183BFE")
        self.assertEqual(result["frontier_trailing_overlap_bytes"], "ff 76")
        self.assertTrue(result["frontier_next_overlap_required"])
        self.assertEqual(result["frontier_call_semantics"], "UNRESOLVED")
        self.assertEqual(result["frontier_runtime_validation"], "UNTESTED")

    def test_f138_validator_is_wired_into_frontier_main(self):
        self.assertIn("validate_f138_frontier_contract", sut.main.__code__.co_names)


    def test_f140_contract_metadata_is_pinned(self):
        self.assertEqual(sut._F140_FRONTIER_CONTINUATION_ID, 103)
        self.assertEqual(sut._F140_START_RVA, 0x00183BFE)
        self.assertEqual(sut._F140_END_RVA, 0x00183C3E)
        self.assertEqual(len(sut._F140_EXPECTED_BYTES), 64)
        self.assertEqual(
            sut._F140_INHERITED_FORWARD_TARGETS,
            [0x00183C10, 0x00183C27],
        )
        self.assertEqual(
            sut._F140_PREDECESSOR_STATUS,
            "EXACT_183BC0_TO_183BFE_CONTROL_FLOW_WITH_183BFE_CUT_EDGE_PROVEN",
        )
        self.assertEqual(sut._F140_PREDECESSOR_CUT_BYTES, bytes.fromhex("ff 76"))
        self.assertEqual(
            sut._F140_REQUIRED_OVERLAP_INSTRUCTION,
            bytes.fromhex("ff 76 10"),
        )
        self.assertEqual(sut._F140_TRAILING_OVERLAP_RVA, 0x00183C3D)
        self.assertEqual(sut._F140_TRAILING_OVERLAP_BYTES, bytes.fromhex("eb"))

    def test_f140_nonmatching_frontier_is_not_promoted(self):
        result = sut.validate_f140_frontier_contract(
            frontier={"continuation_id": 102, "rva": 0x00183BC0},
            payload={},
            exe_path=Path("unused"),
            source_path=Path("unused"),
            length=64,
        )
        self.assertEqual(result, {})

    def test_f140_mismatched_payload_fails_closed_before_analyzer_load(self):
        with self.assertRaisesRegex(ValueError, "F140 canonical frontier contract mismatch"):
            sut.validate_f140_frontier_contract(
                frontier={"continuation_id": 103, "rva": 0x00183BFE},
                payload={
                    "rva_start": "0x00183BFE",
                    "rva_end_exclusive": "0x00183C3E",
                    "section": ".text",
                    "bytes_hex": "ff 76",
                },
                exe_path=Path("unused"),
                source_path=Path("unused"),
                length=64,
            )

    def test_f140_positive_contract_consumes_push_and_preserves_next_cut(self):
        class FakeAnalyzer:
            @staticmethod
            def parse_pe(_data):
                return object()

            @staticmethod
            def collect_guarded_gf_target_c_helper_1_third_callee_continuation_103_prefix_proof(_pe):
                return {
                    "status": "EXACT_183BC0_TO_183BFE_CONTROL_FLOW_WITH_183BFE_CUT_EDGE_PROVEN",
                    "prefix_end_rva": 0x00183BFE,
                    "incomplete_rva": 0x00183BFE,
                    "incomplete_bytes": "ff 76",
                    "capture_edge_matches": True,
                    "unresolved_forward_targets": [0x00183C10, 0x00183C27],
                    "continuation_status": "COMPLETE_INSTRUCTIONS_END_AT_183BFE_TRAILING_FF76_REQUIRES_OVERLAP",
                }

            @staticmethod
            def collect_raw_inbound_rel32_candidates(_pe, _rva):
                return []

            @staticmethod
            def collect_raw_rel32_call_candidates(_pe, _rva, _length):
                return []

        original_loader = sut._load_frontier_analyzer
        try:
            sut._load_frontier_analyzer = lambda _source_path: FakeAnalyzer
            with tempfile.TemporaryDirectory() as td:
                exe = Path(td) / "canonical.exe"
                exe.write_bytes(b"fixture")
                result = sut.validate_f140_frontier_contract(
                    frontier={"continuation_id": 103, "rva": 0x00183BFE},
                    payload={
                        "rva_start": "0x00183BFE",
                        "rva_end_exclusive": "0x00183C3E",
                        "section": ".text",
                        "bytes_hex": sut._F140_EXPECTED_BYTES.hex(" "),
                    },
                    exe_path=exe,
                    source_path=Path("unused"),
                    length=64,
                )
        finally:
            sut._load_frontier_analyzer = original_loader

        self.assertEqual(
            result["frontier_contract_status"],
            "EXACT_EXE_183BFE_TO_183C3E_PROVENANCE_CAPTURED",
        )
        self.assertEqual(
            result["frontier_start_boundary_status"],
            "F139_MANDATORY_OVERLAP_FULL_INSTRUCTION_CONSUMED",
        )
        self.assertEqual(result["frontier_predecessor_cut_bytes"], "ff 76")
        self.assertEqual(result["frontier_required_overlap_instruction"], "ff 76 10")
        self.assertEqual(
            result["frontier_inherited_unresolved_forward_targets"],
            [0x00183C10, 0x00183C27],
        )
        self.assertEqual(result["frontier_raw_inbound_rel32_count"], 0)
        self.assertEqual(result["frontier_raw_outbound_rel32_count"], 0)
        self.assertEqual(result["frontier_trailing_overlap_rva"], "0x00183C3D")
        self.assertEqual(result["frontier_trailing_overlap_bytes"], "eb")
        self.assertTrue(result["frontier_next_overlap_required"])
        self.assertEqual(result["frontier_call_semantics"], "UNRESOLVED")
        self.assertEqual(result["frontier_runtime_validation"], "UNTESTED")

    def test_f140_validator_is_wired_into_frontier_main(self):
        self.assertIn("validate_f140_frontier_contract", sut.main.__code__.co_names)



    def test_f142_contract_metadata_is_pinned(self):
        self.assertEqual(sut._F142_FRONTIER_CONTINUATION_ID, 104)
        self.assertEqual(sut._F142_START_RVA, 0x00183C3D)
        self.assertEqual(sut._F142_END_RVA, 0x00183C7D)
        self.assertEqual(len(sut._F142_EXPECTED_BYTES), 64)
        self.assertEqual(sut._F142_INHERITED_FORWARD_TARGETS, [])
        self.assertEqual(
            sut._F142_PREDECESSOR_STATUS,
            "EXACT_183BFE_TO_183C3D_CONTROL_FLOW_WITH_183C3D_CUT_EDGE_PROVEN",
        )
        self.assertEqual(sut._F142_PREDECESSOR_CUT_BYTES, bytes.fromhex("eb"))
        self.assertEqual(
            sut._F142_REQUIRED_OVERLAP_INSTRUCTION,
            bytes.fromhex("eb 03"),
        )
        self.assertEqual(sut._F142_TRAILING_OVERLAP_RVA, 0x00183C7C)
        self.assertEqual(sut._F142_TRAILING_OVERLAP_BYTES, bytes.fromhex("ff"))

    def test_f142_nonmatching_frontier_is_not_promoted(self):
        result = sut.validate_f142_frontier_contract(
            frontier={"continuation_id": 103, "rva": 0x00183BFE},
            payload={},
            exe_path=Path("unused"),
            source_path=Path("unused"),
            length=64,
        )
        self.assertEqual(result, {})

    def test_f142_mismatched_payload_fails_closed_before_analyzer_load(self):
        with self.assertRaisesRegex(ValueError, "F142 canonical frontier contract mismatch"):
            sut.validate_f142_frontier_contract(
                frontier={"continuation_id": 104, "rva": 0x00183C3D},
                payload={
                    "rva_start": "0x00183C3D",
                    "rva_end_exclusive": "0x00183C7D",
                    "section": ".text",
                    "bytes_hex": "eb",
                },
                exe_path=Path("unused"),
                source_path=Path("unused"),
                length=64,
            )

    def test_f142_positive_contract_consumes_short_jump_and_preserves_next_cut(self):
        class FakeAnalyzer:
            @staticmethod
            def parse_pe(_data):
                return object()

            @staticmethod
            def collect_guarded_gf_target_c_helper_1_third_callee_continuation_104_prefix_proof(_pe):
                return {
                    "status": "EXACT_183BFE_TO_183C3D_CONTROL_FLOW_WITH_183C3D_CUT_EDGE_PROVEN",
                    "prefix_end_rva": 0x00183C3D,
                    "incomplete_rva": 0x00183C3D,
                    "incomplete_bytes": "eb",
                    "capture_edge_matches": True,
                    "unresolved_forward_targets": [],
                    "remaining_predecessor_external_targets": [],
                    "continuation_status": "COMPLETE_INSTRUCTIONS_END_AT_183C3D_TRAILING_EB_REQUIRES_OVERLAP",
                }

            @staticmethod
            def collect_raw_inbound_rel32_candidates(_pe, _rva):
                return []

            @staticmethod
            def collect_raw_rel32_call_candidates(_pe, _rva, _length):
                return []

        original_loader = sut._load_frontier_analyzer
        try:
            sut._load_frontier_analyzer = lambda _source_path: FakeAnalyzer
            with tempfile.TemporaryDirectory() as td:
                exe = Path(td) / "canonical.exe"
                exe.write_bytes(b"fixture")
                result = sut.validate_f142_frontier_contract(
                    frontier={"continuation_id": 104, "rva": 0x00183C3D},
                    payload={
                        "rva_start": "0x00183C3D",
                        "rva_end_exclusive": "0x00183C7D",
                        "section": ".text",
                        "bytes_hex": sut._F142_EXPECTED_BYTES.hex(" "),
                    },
                    exe_path=exe,
                    source_path=Path("unused"),
                    length=64,
                )
        finally:
            sut._load_frontier_analyzer = original_loader

        self.assertEqual(
            result["frontier_contract_status"],
            "EXACT_EXE_183C3D_TO_183C7D_PROVENANCE_CAPTURED",
        )
        self.assertEqual(
            result["frontier_start_boundary_status"],
            "F141_MANDATORY_OVERLAP_FULL_INSTRUCTION_CONSUMED",
        )
        self.assertEqual(result["frontier_predecessor_cut_bytes"], "eb")
        self.assertEqual(result["frontier_required_overlap_instruction"], "eb 03")
        self.assertEqual(result["frontier_inherited_unresolved_forward_targets"], [])
        self.assertEqual(result["frontier_raw_inbound_rel32_count"], 0)
        self.assertEqual(result["frontier_raw_outbound_rel32_count"], 0)
        self.assertEqual(result["frontier_trailing_overlap_rva"], "0x00183C7C")
        self.assertEqual(result["frontier_trailing_overlap_bytes"], "ff")
        self.assertTrue(result["frontier_next_overlap_required"])
        self.assertEqual(result["frontier_call_semantics"], "UNRESOLVED")
        self.assertEqual(result["frontier_runtime_validation"], "UNTESTED")

    def test_f142_validator_is_wired_into_frontier_main(self):
        self.assertIn("validate_f142_frontier_contract", sut.main.__code__.co_names)


    def test_f143_prefix_proof_advances_frontier_to_183c7c(self):
        result = sut.discover_frontier_rva(
            Path(__file__).with_name("analyze_outrun_exe.py")
        )
        self.assertEqual(result["continuation_id"], 105)
        self.assertEqual(result["rva"], 0x00183C7C)
        self.assertEqual(result["basis"], "INCOMPLETE_RVA")


if __name__ == "__main__":
    unittest.main()

