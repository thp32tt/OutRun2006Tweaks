"""Regression tests for exact ChatGPT project navigation on fresh A/B tabs.

The initial tab is chatgpt.com/, not a project home. Requiring a
'New chat in PROJECT' button on that root incorrectly blocked both slots.
"""
import asyncio
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
spec = importlib.util.spec_from_file_location("controller_png_attach", BASE / "controller_png_attach.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
NAME = "아웃런 한글화 신규"
PROJECT = "https://chatgpt.com/g/g-p-correct/project"


class FakeLocator:
    def __init__(self, page, kind, item=None):
        self.page, self.kind, self.item = page, kind, item

    @property
    def first(self):
        return self

    def nth(self, i):
        if self.kind == "rows":
            return FakeLocator(self.page, "row", self.page.rows[i])
        return FakeLocator(self.page, "link", self.page.links[i])

    async def count(self):
        if self.kind == "links":
            return len(self.page.links)
        if self.kind == "rows":
            return len(self.page.rows)
        if self.kind == "button":
            return int(self.item in self.page.buttons)
        if self.kind == "text":
            return int(self.page.text_present)
        return 1

    async def is_visible(self):
        return await self.count() == 1

    async def inner_text(self):
        return self.item["title"]

    async def get_attribute(self, attr):
        return self.item.get({"href": "href", "aria-label": "aria",
                              "data-app-action-sidebar-project-id": "id",
                              "data-app-action-sidebar-project-label": "label"}.get(attr))

    async def wait_for(self, **kwargs):
        if self.kind == "text" and not self.page.text_present:
            raise TimeoutError("project text not visible")
        if self.kind == "heading" and (not self.page.identity or self.page.url != PROJECT):
            raise TimeoutError("wrong project identity")
        if self.kind == "textbox" and self.page.url != PROJECT:
            raise TimeoutError("composer outside project")

    async def click(self, **kwargs):
        self.page.clicked.append(self.kind + ":" + str(self.item))
        if self.kind == "button" or self.kind == "text":
            self.page.url = PROJECT


class FakePage:
    def __init__(self, links=None, buttons=None, text_present=True, identity=True, rows=None):
        self.url = "https://chatgpt.com/"
        self.links = links or []
        self.rows = rows or []
        self.buttons = set(buttons or [])
        self.text_present = text_present
        self.identity = identity
        self.clicked = []
        self.navigation = []

    def get_by_text(self, name, exact=False):
        assert name == NAME and exact
        return FakeLocator(self, "text")

    def get_by_role(self, role, name=None, exact=False):
        if role == "button":
            return FakeLocator(self, "button", name)
        assert role == "heading" and name == NAME and exact
        return FakeLocator(self, "heading")

    def locator(self, css):
        if css.startswith('[data-app-action-sidebar-project-id]'):
            return FakeLocator(self, "rows")
        if css.startswith("a[href"):
            return FakeLocator(self, "links")
        assert css == '[role="textbox"][contenteditable="true"]'
        return FakeLocator(self, "textbox")

    async def goto(self, url, **kwargs):
        self.navigation.append(url)
        self.url = url

    async def wait_for_url(self, glob, **kwargs):
        if self.url != PROJECT:
            raise TimeoutError("not project home")


class ProjectNavigationTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"CHATGPT_PROJECT_URL": "", "LOCALIZATION_PROJECT_URL": ""})
        self.env.start()
        self.addCleanup(self.env.stop)

    def execute(self, page):
        return asyncio.run(module.prepare_a_project_target(page, NAME, allow_saved_chat=False))

    def test_actual_chatgpt_div_project_row_direct_route(self):
        # Observed in the authorized 2026-10-14 N100 Chrome DOM:
        # project row is a DIV; clicking expands but never navigates.
        page = FakePage(rows=[
            {"id": "g-p-other", "label": "다른 프로젝트"},
            {"id": "g-p-correct", "label": NAME},
        ], text_present=True)
        self.assertEqual(self.execute(page), "A_PROJECT_COMPOSER_READY")
        self.assertEqual(page.navigation, [PROJECT])
        self.assertEqual(page.clicked, [])

    def test_duplicate_same_name_project_rows_are_blocked(self):
        page = FakePage(rows=[
            {"id": "g-p-correct", "label": NAME},
            {"id": "g-p-other", "label": NAME},
        ])
        self.assertEqual(self.execute(page), "A_PROJECT_LINK_AMBIGUOUS")
        self.assertEqual(page.navigation, [])

    def test_untrusted_project_row_id_is_blocked(self):
        page = FakePage(rows=[
            {"id": "../../outside", "label": NAME},
        ])
        self.assertEqual(self.execute(page), "A_PROJECT_ID_INVALID")
        self.assertEqual(page.navigation, [])

    def test_fresh_root_exact_sidebar_link(self):
        page = FakePage(links=[
            {"title": "다른 프로젝트", "aria": "", "href": "/g/g-p-other/project"},
            {"title": NAME, "aria": "", "href": "/g/g-p-correct/project"},
        ])
        self.assertEqual(self.execute(page), "A_PROJECT_COMPOSER_READY")
        self.assertEqual(page.navigation, [PROJECT])
        self.assertEqual(page.clicked, [])  # never click global New Chat

    def test_fresh_root_button_sidebar_variant(self):
        page = FakePage(buttons=[NAME])
        self.assertEqual(self.execute(page), "A_PROJECT_COMPOSER_READY")
        self.assertEqual(page.url, PROJECT)
        self.assertEqual(len(page.clicked), 1)

    def test_configured_project_url_when_sidebar_hidden(self):
        with patch.dict(os.environ, {"CHATGPT_PROJECT_URL": PROJECT}):
            page = FakePage(text_present=False)
            self.assertEqual(self.execute(page), "A_PROJECT_COMPOSER_READY")
            self.assertEqual(page.navigation, [PROJECT])

    def test_wrong_heading_blocks(self):
        page = FakePage(links=[{"title": NAME, "aria": "", "href": "/g/g-p-correct/project"}],
                        identity=False)
        self.assertEqual(self.execute(page), "A_PROJECT_IDENTITY_NOT_VERIFIED")

    def test_missing_project_blocks_without_global_chat(self):
        page = FakePage(text_present=False)
        self.assertEqual(self.execute(page), "A_PROJECT_LINK_NOT_FOUND")
        self.assertEqual(page.navigation, [])
        self.assertEqual(page.clicked, [])

    def test_disguised_external_link_is_rejected(self):
        page = FakePage(links=[
            {"title": NAME, "aria": "", "href": "https://example.net/g/foo/project"}
        ])
        self.assertEqual(self.execute(page), "A_PROJECT_LINK_UNTRUSTED")
        self.assertEqual(page.navigation, [])
        self.assertEqual(page.clicked, [])

    def test_invalid_explicit_url_blocks(self):
        with patch.dict(os.environ, {"CHATGPT_PROJECT_URL": "https://example.net/g/foo/project"}):
            page = FakePage()
            self.assertEqual(self.execute(page), "A_PROJECT_URL_INVALID")

if __name__ == "__main__":
    unittest.main()
