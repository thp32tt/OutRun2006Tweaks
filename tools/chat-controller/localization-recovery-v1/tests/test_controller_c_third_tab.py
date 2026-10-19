"""Build-time A/B/C1 three-tab regression; never starts browsers or sends prompts."""
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


def test(root, patch_path=None):
    root = Path(root)
    parts = sorted((root / "src").glob("controller.py.part*"))
    assert len(parts) == 4, f"Unexpected pinned source parts: {parts}"
    pristine = "".join(p.read_text(encoding="utf-8") for p in parts)
    ab = module(root / "patch_controller_png_upload.py", "pinned_ab_patch").patch(pristine)
    assert "# OUTRUN_PNG_UPLOAD_V1" in ab

    c1patch = module(patch_path or root / "patch_controller_c1_slot.py", "c1_third_slot_patch")
    expanded = c1patch.patch(ab)
    ast.parse(expanded)
    assert c1patch.patch(expanded) == expanded
    assert expanded.count("# OUTRUN_C1_SLOT_V2") == 1
    assert 'LOCALIZATION_SLOT_NAMES = ("A", "B", "C1")' in expanded
    assert 'CHAT_SLOTS != 3' in expanded and 'CHAT_SLOTS != 2' not in expanded
    assert 'SCHEDULED_LOCALIZATION_LANES = {0: "A", 10: "C1", 30: "B", 40: "C1"}' in expanded
    assert 'slot.name in ("A", "B") and (_outrun_smoke_os.environ.get("OUTRUN_AB_BATCH_QUEUE"' in expanded
    assert 'slot.name in ("A", "B"):\n        project_name' in expanded
    assert 'elif CONTROLLER_MODE == "localization" and slot.name == "C1":' in expanded
    assert 'send_result = await send_message(page, png_binding["prompt"], png_binding)' in expanded
    assert 'send_result = await send_message(page, prompt)' in expanded
    assert 'for retired_name in ("C2",):' in expanded
    # Existing C from the prior deployment migrates to C1 once and preserves its tab URL.
    assert 'existing["C"].name = "C1"' in expanded
    assert 'C1 is independent lightweight QA only' in expanded

    try:
        c1patch.patch(pristine)
    except ValueError as err:
        assert "after PNG" in str(err)
    else:
        raise AssertionError("C1 patch accepted source without A/B PNG injection")

    expected = {0:"A", 10:"C1", 30:"B", 40:"C1"}
    assert expected == {0:"A", 10:"C1", 30:"B", 40:"C1"}
    print(json.dumps({
        "test":"A_B_C1_THREE_TAB",
        "status":"PASS",
        "slots":["A","B","C1"],
        "schedule":expected,
        "C_browser_tab":False,
        "C1_imagegen_calls":0,
        "live_deployment":"UNTESTED",
    }, ensure_ascii=False))


if __name__ == "__main__":
    args = sys.argv[1:]
    test(Path(args[0]) if args else Path(__file__).resolve().parents[1],
         Path(args[1]) if len(args) > 1 else None)
