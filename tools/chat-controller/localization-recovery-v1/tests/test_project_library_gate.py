"""Offline test for exact generated PNG <-> existing project Library matching.

The real B batch and its five library items were also SHA256-matched
using N100 Playwright on 2026-10-14, without modifying controller state.
"""
import asyncio
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import os

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))
sp=importlib.util.spec_from_file_location("project_library_gate",BASE/"project_library_gate.py")
gate=importlib.util.module_from_spec(sp)
sp.loader.exec_module(gate)

SHAS=[str(i)*64 for i in range(1,6)]
ACTIVE={"task_id":"OUTRUN-AB-B-0001-20261014","role":"B","count":5}

class Locator:
    def __init__(self,folder,role=None,index=None):
        self.folder=folder
        self.role=role
        self.index=index
    @property
    def first(self):
        return Locator(self.folder,self.role,0)
    @property
    def last(self):
        return self
    async def wait_for(self,**kwargs):return None
    async def click(self,**kwargs):
        if self.role=="project":
            self.folder.url="https://chatgpt.com/library/d/abcdef123456?tab=folders"
    async def count(self):
        if self.role=="cards":
            return len(self.folder.rows) if self.folder.expanded else 2
        return 1
    def nth(self,i):
        return Locator(self.folder,"card",i)
    async def get_attribute(self,name):
        return self.folder.rows[self.index]["name"] if name=="aria-label" else None
    async def scroll_into_view_if_needed(self,**kwargs):return None
    def locator(self,selector):
        return Locator(self.folder,"image",self.index)
    async def evaluate(self,source,*args):
        if self.role=="image":
            return None # img.decode()
        if self.role=="card":
            return self.folder.rows[self.index].copy()
        return None

class Mouse:
    def __init__(self,page):self.page=page
    async def move(self,*args):pass
    async def wheel(self,*args):self.page.expanded=True

class FakeFolder:
    url="https://chatgpt.com/library?tab=folders"
    def __init__(self,rows):
        self.rows=rows
        self.expanded=False
        self.closed=False
        self.mouse=Mouse(self)
    async def goto(self,url,**kw):self.url=url
    def get_by_role(self,role,name=None,exact=False):
        return Locator(self,"project" if role=="button" else "tab")
    def locator(self,selector):
        return Locator(self,"cards")
    async def evaluate(self,js,arg):
        return 1 # one project Library folder card with exact name
    async def wait_for_url(self,*args,**kwargs):
        assert "/library/d/" in self.url
    async def close(self):
        self.closed=True

class FakeContext:
    def __init__(self,folder):self.folder=folder
    async def new_page(self):return self.folder

class FakeChat:
    def __init__(self,folder,shas):
        self.context=FakeContext(folder)
        self.shas=shas
    async def evaluate(self,js,args):
        return {"images":[{"index":i+1,"sha256":h,"bytes":2048}
                         for i,h in enumerate(self.shas)],"error":None}


class ProjectLibraryTests(unittest.TestCase):
    def setUp(self):
        rows=[{"id":"libfile_ABCX"+str(i).zfill(5),
               "name":"image-gen-"+str(i)+"(3).png","sha256":"a"*64,"bytes":800}
              for i in range(2)]
        for i,sha in enumerate(SHAS):
            rows.append({"id":"libfile_012345"+str(i).zfill(6),
                         "name":f"image-gen-{i+1}(2).png","sha256":sha,"bytes":1400})
        self.folder=FakeFolder(rows)
        self.chat=FakeChat(self.folder,SHAS)
        self.env=patch.dict(os.environ,{
            "OUTRUN_AB_PROJECT_LIBRARY_NAME":"아웃런 한글화 신규",
            "OUTRUN_AB_PROJECT_NAME":"아웃런 한글화 신규",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_five_sha_matched_even_with_other_images_and_lazy_pages(self):
        proof,error=asyncio.run(gate.verify_project_library_images(self.chat,ACTIVE,max_scan=12))
        self.assertIsNone(error)
        self.assertEqual(proof["verification_method"],"browser_content_sha256_match")
        self.assertEqual(proof["generated_image_sha256"],SHAS)
        self.assertEqual(proof["library_content_sha256"],SHAS)
        self.assertEqual(len(set(proof["library_item_ids"])),5)
        self.assertTrue(self.folder.expanded)
        self.assertTrue(self.folder.closed)
        self.assertEqual(proof["folder"],"아웃런 한글화 신규")
        self.assertEqual(proof["match_status"],"EXACT_GENERATED_LIBRARY_PNG_SHA256_MATCH")

    def test_one_missing_library_png_must_not_pass(self):
        self.folder.rows[-1]["sha256"]="b"*64
        proof,error=asyncio.run(gate.verify_project_library_images(self.chat,ACTIVE,max_scan=12))
        self.assertIsNone(proof)
        self.assertIn("PROJECT_LIBRARY_HASH_MATCH_INCOMPLETE:4/5",error)
        self.assertTrue(self.folder.closed)

    def test_wrong_project_is_failed_closed(self):
        with patch.dict(os.environ,{"OUTRUN_AB_PROJECT_NAME":"다른 프로젝트"}):
            proof,error=asyncio.run(gate.verify_project_library_images(self.chat,ACTIVE))
        self.assertIsNone(proof)
        self.assertIn("PROJECT_LIBRARY_PROJECT_NAME_MISMATCH",error)
        self.assertFalse(self.folder.closed)

    def test_distinct_generated_sources_required(self):
        self.chat.shas=[SHAS[0]]*5
        proof,error=asyncio.run(gate.verify_project_library_images(self.chat,ACTIVE))
        self.assertIsNone(proof)
        self.assertEqual(error,"INVALID_SOURCE_IMAGE_HASHES")
        self.assertFalse(self.folder.closed)

if __name__=="__main__":
    unittest.main()