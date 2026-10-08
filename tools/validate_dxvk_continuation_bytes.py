#!/usr/bin/env python3
"""Validate bounded DXVK disassembly continuation byte windows.

This is a static evidence guard. It deliberately does not infer runtime
semantics from bytes; it only verifies that a continuation window preserves the
required overlap bytes at its boundary before a later decoder consumes it.
"""

EXPECTED = {
    "start_rva": 0x00182F7E,
    "end_rva": 0x00182FBE,
    "overlap": bytes.fromhex("66 0f 54 1d 20 91 61"),
}


def validate_window(start_rva: int, end_rva: int, data: bytes) -> None:
    if start_rva != EXPECTED["start_rva"]:
        raise ValueError("unexpected continuation start RVA")
    if end_rva != EXPECTED["end_rva"]:
        raise ValueError("unexpected continuation probe end RVA")
    if len(data) < len(EXPECTED["overlap"]):
        raise ValueError("continuation window is shorter than required overlap")
    if data[: len(EXPECTED["overlap"])] != EXPECTED["overlap"]:
        raise ValueError("continuation overlap bytes changed")


def main() -> None:
    validate_window(
        EXPECTED["start_rva"],
        EXPECTED["end_rva"],
        EXPECTED["overlap"] + b"\x90",
    )
    print("DXVK continuation byte window validator: PASS")


if __name__ == "__main__":
    main()
