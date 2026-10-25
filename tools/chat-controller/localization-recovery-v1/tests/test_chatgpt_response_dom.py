"""Static regression for current ChatGPT 2026 assistant-turn DOM selectors."""
from __future__ import annotations
import importlib.util
from pathlib import Path

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def test(root):
    root=Path(root)
    pristine="".join(p.read_text(encoding="utf-8") for p in sorted((root/"src").glob("controller.py.part*")))
    assert "[data-chatgpt-search-unit-key$=':assistant']" in pristine
    assert "[data-content-search-unit-key$=':assistant']" in pristine
    ab=module(root/"patch_controller_png_upload.py","ab").patch(pristine)
    c1=module(root/"patch_controller_c1_slot.py","c1").patch(ab)
    out=module(root/"patch_controller_gpt_chat_ocr.py","gpt").patch(c1)
    assert "data-markdown-text-style=\"assistant-message\"" in out
    assert "UPLOAD_TASK_ID=" in out
    assert "role(units[i]) !== 'assistant'" in out
    assert "Never consume an unrelated prior assistant turn." in out
    print("CHATGPT_RESPONSE_DOM_PASS")

if __name__=="__main__":
    import sys
    test(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1])