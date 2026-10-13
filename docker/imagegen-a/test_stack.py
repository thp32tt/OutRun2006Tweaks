import asyncio
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, AsyncMock
from PIL import Image
from . import controller as c
from .fetch_source import fetch
from .qa import inspect, sha

class StackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.source = self.root / 'source.png'
        im = Image.new('RGBA', (32,32), (0,0,0,0)); im.putpixel((1,1),(255,0,0,255)); im.save(self.source)
        self.candidate = self.root / 'candidate.png'
        im.putpixel((2,2),(0,255,0,255)); im.save(self.candidate)
        self.spec = self.root / 'source.json'
        self.data = {'filename':'source.png','url':'https://raw.githubusercontent.com/u/r/'+'a'*40+'/source.png', 'sha256':sha(self.source),'size':[32,32]}
        self.spec.write_text(json.dumps(self.data))
    def tearDown(self): self.tmp.cleanup()
    def test_download_hash_and_cache(self):
        with patch('stack.fetch_source.urlopen', return_value=io.BytesIO(self.source.read_bytes())) as get:
            target=fetch(self.spec,self.root/'cache')
            self.assertEqual(sha(target),sha(self.source))
            fetch(self.spec,self.root/'cache'); self.assertEqual(get.call_count,1)
    def test_bad_download_never_replaces(self):
        with patch('stack.fetch_source.urlopen', return_value=io.BytesIO(b'bad')):
            with self.assertRaisesRegex(ValueError,'SHA'): fetch(self.spec,self.root/'cache')
        self.assertFalse((self.root/'cache/source.png').exists())
    def test_branch_url_rejected(self):
        self.data['url']=self.data['url'].replace('a'*40,'main'); self.spec.write_text(json.dumps(self.data))
        with self.assertRaisesRegex(ValueError,'PINNED'): fetch(self.spec,self.root/'cache')
    def test_arbitrary_host_rejected(self):
        self.data['url']=self.data['url'].replace('raw.githubusercontent.com','example.org'); self.spec.write_text(json.dumps(self.data))
        with self.assertRaisesRegex(ValueError,'HOST'): fetch(self.spec,self.root/'cache')
    def test_unchanged_image_fails(self):
        r=inspect(self.source,self.source,self.root/'qa'); self.assertIn('UNCHANGED_SOURCE',r['failures'])
    def test_size_mismatch_fails(self):
        Image.new('RGBA',(16,16)).save(self.candidate)
        self.assertIn('DIMENSION_MISMATCH',inspect(self.source,self.candidate,self.root/'qa')['failures'])
    def test_alpha_missing_fails(self):
        Image.new('RGB',(32,32)).save(self.candidate)
        self.assertIn('ALPHA_CHANNEL_MISSING',inspect(self.source,self.candidate,self.root/'qa')['failures'])
    def test_mechanical_pass_is_not_game_or_visual_pass(self):
        r=inspect(self.source,self.candidate,self.root/'qa')
        self.assertEqual(r['mechanical'],'PASS'); self.assertFalse(r['official_promotion'])
        self.assertEqual(r['independent_qa'],'NOT_RUN'); self.assertEqual(r['RUNTIME_VALIDATION'],'UNTESTED')
        self.assertEqual(len(list((self.root/'qa').glob('compare_*.jpg'))),3)
    def test_checkpoint_atomic_preserves_task(self):
        with patch.object(c,'OUT',self.root),patch.object(c,'STATE',self.root/'state.json'):
            c.save('GENERATION_SUBMITTING',marker='test'); c.save('HOLD')
            self.assertEqual(c.read_state()['marker'],'test')
            self.assertFalse((self.root/'state.tmp').exists())
    def test_send_intent_recorded_before_ambiguous_click(self):
        async def scenario():
            box=AsyncMock(); send=AsyncMock(); send.click.side_effect=RuntimeError('connection lost')
            page=AsyncMock(); page.url='https://chatgpt.com/c/test'
            page.locator=lambda s: box if s==c.BOX else send
            with patch.object(c,'OUT',self.root),patch.object(c,'STATE',self.root/'state.json'):
                with self.assertRaises(RuntimeError): await c.submit(page,'prompt','marker','GENERATION')
                self.assertEqual(c.read_state()['phase'],'GENERATION_SUBMITTING')
        asyncio.run(scenario())

if __name__=='__main__': unittest.main()
