"""Regression tests for ChatGPT 2026 composer attachment DOM variants."""
import asyncio
import importlib.util
from pathlib import Path
import sys
import unittest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
spec = importlib.util.spec_from_file_location("controller_png_attach", BASE / "controller_png_attach.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Locator:
    def __init__(self, page, kind, selector=""):
        self.page = page
        self.kind = kind
        self.selector = selector

    @property
    def first(self):
        return self

    def nth(self, i):
        return self

    def locator(self, selector):
        if selector.startswith("xpath=ancestor::form"):
            return Locator(self.page, "form", selector)
        return Locator(self.page, "remove", selector)

    async def count(self):
        if self.kind == "input":
            return int(self.selector == self.page.available_input)
        if self.kind == "form":
            return 1
        if self.kind == "remove":
            return 0
        return 1

    async def wait_for(self, **kwargs):
        return None

    async def set_input_files(self, paths, **kwargs):
        self.page.uploaded = paths

    async def is_visible(self):
        return True


class Page:
    url = "https://chatgpt.com/g/g-p-test/project"

    def __init__(self, available_input):
        self.available_input = available_input
        self.uploaded = None
        self.wait_script = ""
        self.wait_arg = None

    def locator(self, selector):
        if selector == '[role="textbox"][contenteditable="true"]':
            return Locator(self, "textbox", selector)
        if selector.startswith('input[type="file"]'):
            return Locator(self, "input", selector)
        raise AssertionError(selector)

    async def wait_for_timeout(self, ms):
        return None

    async def wait_for_function(self, script, arg=None, timeout=None):
        self.wait_script = script
        self.wait_arg = arg
        self.timeout = timeout


class AttachmentDomTests(unittest.TestCase):
    def test_single_photo_input_variant_is_supported(self):
        selector = 'input[type="file"][aria-label="Attach photos"]'
        page = Page(selector)
        result = asyncio.run(m.attach_png(page, {"path": "/tmp/roi.png", "paths": ["/tmp/roi.png"]}))
        self.assertEqual(result, "ATTACHMENT_UPLOAD_COMPLETED")
        self.assertEqual(page.uploaded, "/tmp/roi.png")
        self.assertEqual(page.wait_arg, {"names": ["roi.png"]})
        self.assertIn('data-testid*="attachment"', page.wait_script)
        self.assertIn("selectedFiles", page.wait_script)

    def test_batch_photos_or_videos_input_variant_is_supported(self):
        selector = 'input[type="file"][aria-label="Attach photos or videos"]'
        page = Page(selector)
        paths = ["/tmp/a.png", "/tmp/b.png"]
        result = asyncio.run(m.attach_batch_pngs(page, {"paths": paths}))
        self.assertEqual(result, "ATTACHMENT_UPLOAD_COMPLETED")
        self.assertEqual(page.uploaded, paths)
        self.assertEqual(page.wait_arg, {"names": ["a.png", "b.png"]})

    def test_missing_file_input_is_fail_closed(self):
        page = Page("none")
        result = asyncio.run(m.attach_png(page, {"path": "/tmp/roi.png", "paths": ["/tmp/roi.png"]}))
        self.assertEqual(result, "ATTACH_FILES_INPUT_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()