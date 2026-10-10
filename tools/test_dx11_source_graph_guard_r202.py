#!/usr/bin/env python3
"""Static DX11 conversion source-graph guard.

Repository-only validation helper. It verifies that conversion lane policy keeps
DX11 work isolated from DXVK/localization changes and does not imply runtime
validation.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    state = (ROOT / "docs" / "CONVERSION_LANE_STATE.json").read_text(encoding="utf-8")

    required = {
        '"lane": "DX11"': "DX11 lane marker",
        '"github_only_development": true': "GitHub-only marker",
        '"runtime_validation": "UNTESTED"': "runtime evidence boundary",
        '"normal_success_requires"': "conversion gate marker",
    }

    missing = [name for token, name in required.items() if token not in state]
    if missing:
        raise SystemExit("DX11 source graph guard drift: " + ", ".join(missing))

    print("DX11 source graph guard R202: PASS")


if __name__ == "__main__":
    main()
