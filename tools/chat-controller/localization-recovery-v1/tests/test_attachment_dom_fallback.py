import importlib.util
import pathlib
import unittest

MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "controller_png_attach.py"
SPEC = importlib.util.spec_from_file_location("controller_png_attach", MODULE_PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class FakeLocator:
    def __init__(self, kind, page, count=0):
        self.kind = kind
        self.page = page
        self._count = count
        self.first = self
        self.last = self

    async def count(self):
        return self._count

    async def wait_for(self, **kwargs):
        return None

    async def dispatch_event(self, name):
        self.page.events.append(("dispatch", self.kind, name))

    async def set_input_files(self, paths, **kwargs):
        self.page.events.append(("files", self.kind, paths))


class FakePage:
    def __init__(self, accepted_selector):
        self.url = "https://chatgpt.com/g/g-p-test/project"
        self.accepted_selector = accepted_selector
        self.events = []
        self.wait_expression = ""

    def locator(self, selector):
        if selector == '[role="textbox"][contenteditable="true"]':
            return FakeLocator("textbox", self, 1)
        if selector.startswith('button[aria-label^="Remove '):
            return FakeLocator("previous", self, 0)
        return FakeLocator(selector, self, 1 if selector == self.accepted_selector else 0)

    async def evaluate(self, expression):
        self.events.append(("snapshot",))
        return {"ready": 0, "loading": 0}

    async def wait_for_function(self, expression, **kwargs):
        self.wait_expression = expression
        self.events.append(("wait", kwargs.get("arg")))
        return None

    async def wait_for_timeout(self, ms):
        return None


class AttachmentDomFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_single_png_accepts_modern_attach_photos_input(self):
        page = FakePage('input[type="file"][aria-label="Attach photos"]')
        result = await MOD.attach_png(page, {"path": "/tmp/roi.png"})
        self.assertEqual(result, "ATTACHMENT_UPLOAD_COMPLETED")
        self.assertIn(("files", 'input[type="file"][aria-label="Attach photos"]', "/tmp/roi.png"), page.events)
        self.assertIn('img[alt="User attachment"]', page.wait_expression)
        self.assertIn('[role="progressbar"]', page.wait_expression)

    async def test_batch_accepts_photos_or_videos_input(self):
        selector = 'input[type="file"][aria-label="Attach photos or videos"]'
        page = FakePage(selector)
        result = await MOD.attach_batch_pngs(page, {
            "paths": ["/tmp/a.png", "/tmp/b.png"]
        })
        self.assertEqual(result, "ATTACHMENT_UPLOAD_COMPLETED")
        self.assertIn(("files", selector, ["/tmp/a.png", "/tmp/b.png"]), page.events)
        wait_args = [e[1] for e in page.events if e[0] == "wait"][0]
        self.assertEqual(wait_args["files"], ["a.png", "b.png"])
        self.assertEqual(wait_args["baseline"], 0)


if __name__ == "__main__":
    unittest.main()