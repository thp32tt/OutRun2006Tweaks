import importlib.util
from pathlib import Path


MODULE = Path(__file__).parents[1] / "tools" / "validate_dxvk_continuation_evidence.py"


spec = importlib.util.spec_from_file_location("dxvk_validator", MODULE)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def test_accepts_valid_continuation_window():
    record = {
        "start_rva": "0x182F7E",
        "end_rva": "0x182FBE",
        "bytes": "66 0f 54 1d 20 91 61",
        "branch_targets": [],
    }
    assert validator.validate(record) == []


def test_rejects_invalid_range_and_hex():
    record = {
        "start_rva": "0x20",
        "end_rva": "0x10",
        "bytes": "not-hex",
        "branch_targets": [],
    }
    errors = validator.validate(record)
    assert "end_rva must be greater than start_rva" in errors
    assert "byte window is not valid hex" in errors


def test_rejects_missing_overlap_provenance_bytes():
    record = {
        "start_rva": "0x182F7E",
        "end_rva": "0x182FBE",
        "bytes": "90 90 90 90",
        "branch_targets": [],
    }
    errors = validator.validate(record)
    assert "byte window must preserve canonical overlap bytes" in errors
