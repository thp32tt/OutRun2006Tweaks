"""Local HTML fixture tests real file input/send/download; NOT live ChatGPT."""
import asyncio
import base64
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from playwright.async_api import async_playwright
from . import controller as c

class BrowserFixture(unittest.TestCase):
    def test_upload_send_download(self):
        async def scenario():
            source=Path(os.getenv('FIXTURE_PNG','source/english_png/Q217_D1039D6F_BASE_READABLE_FLIPY.png')).resolve()
            async with async_playwright() as p:
                browser=await p.chromium.launch()
                page=await browser.new_page(accept_downloads=True)
                encoded=base64.b64encode(source.read_bytes()).decode()
                await page.set_content('''<form onsubmit="return false"><input type=file multiple>
                <textarea id=prompt-textarea></textarea><button data-testid=send-button>Send</button></form>
                <script>
                document.querySelector('input').onchange=e=>{
                  document.querySelectorAll('[data-testid=attachment]').forEach(n=>n.remove());
                  for(const f of e.target.files){let n=document.createElement('button');n.type='button';n.dataset.testid='attachment';n.textContent=f.name;document.querySelector('form').append(n);}
                };
                document.querySelector('[data-testid=send-button]').onclick=()=>{
                  const n=document.createElement('div');n.dataset.messageAuthorRole='user';n.textContent=document.querySelector('textarea').value;document.body.append(n);document.querySelector('textarea').value='';
                  const a=document.createElement('div');a.dataset.messageAuthorRole='assistant';
                  const b=document.createElement('button');b.setAttribute('aria-label','Download image');b.textContent='Download';
                  b.onclick=()=>{const link=document.createElement('a');link.href='data:image/png;base64,SOURCE_BYTES';link.download='generated.png';link.click();};a.append(b);document.body.append(a);
                };</script>'''.replace('SOURCE_BYTES',encoded))
                with tempfile.TemporaryDirectory() as temp:
                    out=Path(temp)
                    with patch.object(c,'OUT',out),patch.object(c,'STATE',out/'state.json'):
                        await c.upload(page,[source])
                        await c.submit(page,'generate','fixture-task','GENERATION')
                        self.assertEqual(c.read_state()['phase'],'GENERATION_SENT')
                        candidate=await c.capture(page,0)
                        self.assertEqual(candidate.read_bytes(),source.read_bytes())
                        await c.upload(page,[source,candidate])
                        self.assertEqual(await page.locator('[data-testid=attachment]').count(),2)
                await browser.close()
        asyncio.run(scenario())

if __name__=='__main__': unittest.main()
