"""Exercise immutable fallback, retry rollover and actual wave scheduling."""
import ast
import asyncio
import base64
import io
import json
import re
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ''.join(p.read_text() for p in sorted((ROOT/'tools/chat-controller/v0.4/src').glob('controller.py.part*')))

def env():
    nodes = [n for n in ast.parse(SOURCE).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    module = ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]+nodes,type_ignores=[])
    e = dict(json=json,base64=base64,re=re,urllib=urllib,time=time,datetime=datetime,TZ=timezone.utc,
             PREFERRED_THINKING_LEVEL='High',GITHUB_REPO='owner/repo',GITHUB_TOKEN='test',log=Mock(),write_runtime=Mock(),
             save_queue_state=Mock(),save_registry=Mock(),_github_rest_block_until_epoch=0,
             _producer_result_evidence_cache={})
    exec(compile(ast.fix_missing_locations(module),'controller','exec'),e)
    e.update(write_runtime=Mock(),save_queue_state=Mock(),save_registry=Mock())
    return e

def encoded(record):
    return {'content':base64.b64encode(json.dumps(record).encode()).decode()}

def missing():
    return urllib.error.HTTPError('url',404,'missing',{},None)

class ControllerV2(unittest.TestCase):
    def test_fallback_all_tiers_and_identity(self):
        tid='LOCALIZATION-LOCALIZATION_A-00487'
        for name in [tid+'.rollover.json','dispatch-log.json','reconcile-log.json','rollover-log.json','LOCALIZATION_A-other-00487.json','other-00487.json']:
            with self.subTest(name=name):
                e=env();path='docs/automation/runs/'+name
                def api(url):
                    if '/git/trees/' in url:
                        return {'tree':[{'path':path,'type':'blob'}]}
                    if '/'+tid+'.json?' in url:
                        raise missing()
                    return encoded({'entries':[{'TASK_ID':'other'},{'TASK_ID':tid,'ATTEMPT':2,'CHAT_ROLLOVER':7}]})
                e['github_api_json']=Mock(side_effect=api)
                record=e['github_task_record']('exact-sha',tid)
                self.assertEqual(record['CHAT_ROLLOVER'],7)
                active={'task_id':tid,'attempt':2,'chat_rollovers':5}
                e['restore_task_counters'](active,record)
                self.assertEqual(active,{'task_id':tid,'attempt':2,'chat_rollovers':7})
                self.assertTrue(all('exact-sha' in x.args[0] for x in e['github_api_json'].call_args_list))
                e['github_api_json']=Mock(side_effect=lambda url: {'tree':[{'path':path,'type':'blob'}]} if '/git/trees/' in url else encoded({'TASK_ID':'wrong'}))
                self.assertIsNone(e['github_task_record']('exact-sha',tid))

    def test_exact_precedence_and_auth(self):
        e=env();e['github_api_json']=Mock(return_value=encoded({'TASK_ID':'T'}))
        self.assertEqual(e['github_task_record']('sha','T'),{'TASK_ID':'T'})
        self.assertEqual(e['github_api_json'].call_count,1)
        for code in (401,403,429):
            e['github_api_json']=Mock(side_effect=urllib.error.HTTPError('url',code,'error',{},None))
            with self.assertRaises(urllib.error.HTTPError): e['github_task_record']('sha','T')
            self.assertEqual(e['github_api_json'].call_count,1)

    def test_http_error_classification(self):
        for code,headers,blocked in [(404,{},False),(401,{},False),(403,{},False),(403,{'X-RateLimit-Remaining':'0'},True),(429,{},True)]:
            e=env()
            with patch.object(urllib.request,'urlopen',side_effect=urllib.error.HTTPError('url',code,'error',headers,io.BytesIO())):
                with self.assertRaises(urllib.error.HTTPError): e['github_api_json']('/test')
            self.assertEqual(e['_github_rest_block_until_epoch']>0,blocked)
            if code in (401,403) and not blocked:
                self.assertEqual(e['write_runtime'].call_args.kwargs['github_blocker'],'GITHUB_AUTHORIZATION_REQUIRED')

    def test_retry_once_then_rollover(self):
        e=env();e.update(first_visible=AsyncMock(return_value=object()),RETRY_SELECTORS=[],retry_surface_text=AsyncMock(return_value='error'),RATE_LIMIT_PATTERNS=[],RETRY_BUTTON_COOLDOWN_SECONDS=10,send_guard_reason=Mock(return_value=None),click_retry_generation=AsyncMock(return_value=True),note_successful_request=Mock(),queue_rollover_chat=AsyncMock(return_value=True))
        active={'task_id':'T','attempt':2,'chat_rollovers':4};slot=SimpleNamespace(name='A')
        asyncio.run(e['queue_handle_retry_surface'](None,None,slot,active,{},object(),{}))
        active['last_retry_click_at']='2000-01-01T00:00:00+00:00'
        asyncio.run(e['queue_handle_retry_surface'](None,None,slot,active,{},object(),{}))
        self.assertEqual(e['click_retry_generation'].await_count,1)
        self.assertEqual(e['queue_rollover_chat'].await_count,1)
        self.assertEqual(active['attempt'],2)

    def test_rollover_preserves_identity(self):
        e=env();slot=SimpleNamespace(name='A',url='old');reg=SimpleNamespace(slots=[slot])
        e.update(CONVERSATION_ROLLOVER_ENABLED=True,MAX_CHAT_ROLLOVERS_PER_TASK=0,load_registry=Mock(return_value=reg),send_guard_reason=Mock(return_value=None),replace_with_fresh_slot_page=AsyncMock(return_value=object()),ensure_logged_in=AsyncMock(return_value=True),first_visible=AsyncMock(return_value=object()),INPUT_SELECTORS=[],runtime={},ensure_thinking_level=AsyncMock(return_value=True),STRICT_THINKING_LEVEL=True,send_message=AsyncMock(return_value='sent'),queue_rollover_prompt=Mock(return_value='resume'),wait_for_chat_url=AsyncMock(return_value='new'),note_successful_request=Mock())
        active={'task_id':'T','lane':'LOCALIZATION_A','branch':'branch','slot':'A','attempt':2,'chat_rollovers':7}
        self.assertTrue(asyncio.run(e['queue_rollover_chat'](None,{},active,'error')))
        self.assertEqual((active['task_id'],active['attempt'],active['chat_rollovers']),('T',2,8))

    def test_wave_barrier(self):
        e=env();q={'active_by_lane':{},'qa_pending':[]}
        e.update(load_queue_state=Mock(return_value=q),load_registry=Mock(return_value=None),rate_limit_active=Mock(return_value=False),localization_process_lane=AsyncMock(),LOCALIZATION_QA_BATCH_SIZE=2,LOCALIZATION_QA_COALESCE_SECONDS=0,select_verified_qa_batch=lambda q:q['qa_pending'],finalize_c_qa_batch=Mock(side_effect=lambda q,t:q.update(qa_pending=[])))
        async def send(ctx,pages,q,lane,wave,qa_batch=None):
            q['active_by_lane'][lane]={'task_id':lane,'result_sha':lane+'sha','phase':'WAIT_CHAT','qa_batch':qa_batch,'terminal':None}
            return True
        e['localization_send_lane_task']=AsyncMock(side_effect=send)
        cycle=lambda:asyncio.run(e['localization_parallel_cycle'](None,{}))
        cycle();self.assertEqual(set(q['active_by_lane']),{'A','B'})
        q['active_by_lane']['A'].update(phase='DONE',terminal='PRODUCED')
        cycle();self.assertEqual(set(q['active_by_lane']),{'B'})
        cycle();self.assertEqual(e['localization_send_lane_task'].await_count,2)
        q['active_by_lane']['B'].update(phase='DONE',terminal='PRODUCED')
        cycle();self.assertEqual(set(q['active_by_lane']),{'C'})
        cycle();self.assertEqual(e['localization_send_lane_task'].await_count,3)
        q['active_by_lane']['C'].update(phase='DONE',terminal='PASS')
        cycle();self.assertEqual(set(q['active_by_lane']),{'A','B'})

    def test_retired_lane_rejected(self):
        e=env();e['CONTROLLER_MODE']='localization'
        for lane in ('D','E'):
            with self.assertRaises(ValueError): e['queue_target_for_slot'](lane)
            with self.assertRaises(ValueError): e['prompt_for_slot'](SimpleNamespace(name=lane),'parallel')
        self.assertEqual(e['queue_target_for_slot']('C')['lane'],'LOCALIZATION_C')

    def test_incomplete_c_evidence_holds(self):
        e=env();item={'task_id':'A','result_sha':'sha'};q={'qa_pending':[item]}
        e['github_task_record']=Mock(return_value={'qa_dispositions':[]})
        e['finalize_c_qa_batch'](q,{'task_id':'C','result_sha':'csha','qa_batch':[item],'terminal':'PASS'})
        self.assertIn('qa_hold',q);self.assertEqual(q['qa_pending'],[item])

if __name__=='__main__': unittest.main()
