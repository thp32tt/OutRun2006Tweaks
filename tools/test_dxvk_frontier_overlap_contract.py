#!/usr/bin/env python3
"""Static guard for the DXVK disassembly continuation frontier.

This intentionally validates only repository evidence contracts. It does not
promote runtime/render semantics from disassembly data.
"""

EXPECTED = {
    "start_rva": "0x00182F7E",
    "probe_end_rva": "0x00182FBE",
    "overlap_bytes": "66 0f 54 1d 20 91 61",
}


def validate_frontier(record):
    for key, value in EXPECTED.items():
        if record.get(key) != value:
            raise AssertionError(f"DXVK frontier contract mismatch: {key}")
    if not record.get("capture_edge_matches", False):
        raise AssertionError("DXVK overlap capture edge must be proven")
    return True


if __name__ == "__main__":
    sample = {
        **EXPECTED,
        "capture_edge_matches": True,
    }
    assert validate_frontier(sample)
    print("DXVK frontier overlap contract: PASS")
