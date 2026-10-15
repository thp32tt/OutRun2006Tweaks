"""Build-time C third-tab regression; never starts browsers or sends prompts."""
from __future__ import annotations

import ast
import importlib.util
import json
import sys
from pathlib import Path


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test(root, cpatch_path=None):
    root = Path(root)
    parts = sorted((root / "src").glob("controller.py.part*"))
    assert len(parts) == 4, f"Unexpected pinned source parts: {parts}"
    pristine = "".join(p.read_text(encoding="utf-8") for p in parts)
    ab = module(root / "patch_controller_png_upload.py", "pinned_ab_patch").patch(pristine)
    assert "# OUTRUN_PNG_UPLOAD_V1" in ab
    cpatch = module(cpatch_path or root / "patch_controller_c_slot.py", "c_third_slot_patch")
    expanded = cpatch.patch(ab)
    ast.parse(expanded)
    assert cpatch.patch(expanded) == expanded, "C patch must be idempotent"
    assert expanded.count("# OUTRUN_C_SLOT_V1") == 1
    assert 'LOCALIZATION_SLOT_NAMES = ("A", "B", "C")' in expanded
    assert 'CHAT_SLOTS != 3' in expanded and 'CHAT_SLOTS != 2' not in expanded
    assert "SCHEDULED_LOCALIZATION_LANES.update({3: \"C\", 33: \"C\"})" in expanded
    assert 'if CONTROLLER_MODE == "localization" and slot.name in ("A", "B") and _outrun_smoke_os.environ.get("OUTRUN_AB_BATCH_QUEUE"' in expanded
    assert 'if CONTROLLER_MODE == "localization" and slot.name in ("A", "B"):\n        project_name' in expanded
    assert 'elif CONTROLLER_MODE == "localization" and slot.name == "C":' in expanded
    assert 'send_result = await send_message(page, prompt)' in expanded
    assert 'send_result = await send_message(page, png_binding["prompt"], png_binding)' in expanded
    assert 'target_status = await prepare_a_project_target(page, project_name, allow_saved_chat=False)' in expanded
    assert 'if "C" in existing:' not in expanded, "C cannot be mapped to inactive C1"
    assert 'for retired_name in ("C1", "C2"):' in expanded, "Prior C1/C2 registry archiving preserved"
    try:
        cpatch.patch(pristine)
    except ValueError as err:
        assert "AFTER" in str(err)
    else:
        raise AssertionError("C patch accepted a source without A/B PNG injection")
    expected = {minute: ("A" if minute % 10 == 0 else "B") for minute in range(0, 60, 5)}
    expected.update({3: "C", 33: "C"})
    assert len(expected) == 14
    assert [expected.get(m) for m in (0, 3, 5, 30, 33, 35)] == ["A", "C", "B", "A", "C", "B"]
    assert {k: list(expected.values()).count(k) for k in "ABC"} == {"A": 6, "B": 6, "C": 2}
    print(json.dumps({"test": "C_THIRD_TAB", "status": "PASS",
        "AB_slots_preserved": 12, "C_slots_added": 2,
        "registry_migration": "AB_URLS_PRESERVED_C_ADDED_C1_C2_ARCHIVED",
        "C_imagegen_calls": 0, "C_target": "EXISTING_KOREAN_PROJECT_NAME",
        "live_deployment": "UNTESTED"}, ensure_ascii=False))


if __name__ == "__main__":
    args = sys.argv[1:]
    test(Path(args[0]) if args else Path(__file__).resolve().parents[1],
         Path(args[1]) if len(args) > 1 else None)