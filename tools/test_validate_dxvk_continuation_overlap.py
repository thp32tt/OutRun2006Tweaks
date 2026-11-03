import json
import tempfile
from pathlib import Path

from validate_dxvk_continuation_overlap import validate


def test_matching_overlap():
    assert validate({
        "previous_bytes": "aa bb 66 0f 54 1d 20 91 61",
        "overlap_bytes": "66 0f 54 1d 20 91 61",
        "current_bytes": "66 0f 54 1d 20 91 61 cc",
    }) == []


def test_rejects_missing_overlap():
    errors = validate({
        "previous_bytes": "aa bb cc",
        "overlap_bytes": "66 0f",
        "current_bytes": "66 0f cc",
    })
    assert errors


if __name__ == "__main__":
    test_matching_overlap()
    test_rejects_missing_overlap()
    print("DXVK continuation overlap tests: PASS")
