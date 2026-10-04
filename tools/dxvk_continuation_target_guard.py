#!/usr/bin/env python3
"""Validate DXVK continuation control-flow evidence without semantic promotion.

Checks that recorded branch targets are inside the captured raw window and that
no target is silently accepted without an explicit hexadecimal RVA.
"""

import argparse
import json


def validate_targets(start_rva: int, end_rva: int, targets):
    if start_rva >= end_rva:
        raise ValueError("invalid window range")
    normalized = []
    for target in targets:
        if target < start_rva or target >= end_rva:
            raise ValueError("branch target escapes evidence window")
        normalized.append(hex(target))
    return {
        "window": [hex(start_rva), hex(end_rva)],
        "branch_targets": normalized,
        "semantic_promotion": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("targets", nargs="*")
    args = parser.parse_args()
    print(json.dumps(validate_targets(
        int(args.start, 16),
        int(args.end, 16),
        [int(x, 16) for x in args.targets],
    ), indent=2))


if __name__ == "__main__":
    main()
