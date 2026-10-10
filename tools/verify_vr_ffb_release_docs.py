#!/usr/bin/env python3
"""Ensure DX9Ex imported FFB reverse maps exactly match released v0.2 blobs."""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINNED = {
    "docs/reverse/LINDBERGH_FFB_MAP.md": "89078dcd26115beb9e32349f651ac036cdd63eda",
    "docs/reverse/C2C_STAGE_FFB_MAP.md": "74ab37bc8a992148f016f8ef7904070578aefd1a",
    "docs/reverse/FFB_MODEL_MODES.md": "8781d0927e7bff410e3845f1ccf61d31727d7809",
}


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def main() -> None:
    for name, expected in PINNED.items():
        path = ROOT / name
        if not path.is_file():
            raise SystemExit("VR FFB v0.2 MAP FAIL: missing " + name)
        payload = path.read_bytes()
        if blob_sha(payload) != expected:
            raise SystemExit("VR FFB v0.2 MAP FAIL: release provenance mismatch for " + name)
        # Negative fixture: even a single byte added must invalidate the pin.
        if blob_sha(payload + b"!") == expected:
            raise SystemExit("VR FFB v0.2 MAP FAIL: mutation escaped for " + name)
    print(f"VR FFB v0.2 MAP PASS: {len(PINNED)} exact release SHA pins; 3 negative byte mutations")


if __name__ == "__main__":
    main()
