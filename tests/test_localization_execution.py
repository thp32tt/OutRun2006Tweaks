"""Regression tests load pure/controller functions without launching browser or network."""
import ast
import asyncio
import base64
import json
import re
import unittest
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock


ROOT = Path(__file__).resolve().parents[1]


def load_functions(variant):
    src = ''.join(p.read_text() for p in sorted((ROOT / 'tools/chat-controller' / variant / 'src').glob('controller.py.part*')))
    compile(src, variant, 'exec')
    names = {'_task_records', 'github_task_record', 'classify_localization_result', 'github_localization_result_evidence',
             'finalize_localization_producer_commit', 'resume_incomplete_localization',
             'queue_rollover_prompt', 'queue_dynamic_prefix', 'enqueue_producer_result_for_qa',
             'localization_process_lane', 'select_verified_qa_batch'}
    nodes = [n for n in ast.parse(src).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    env = dict(re=re, json=json, base64=base64, datetime=datetime, TZ=timezone.utc,
               _producer_result_evidence_cache={}, GITHUB_REPO='owner/repo',
               urllib=urllib, log=Mock(),
               LOCALIZATION_EXECUTION_POLICY='discover GitHub tools', MAX_TASK_ATTEMPTS=3,
               CONTROLLER_MODE='localization', GAME_MOD_CONTEXT='authorized game mod', LOCALIZATION_QA_BATCH_SIZE=4,
               _parse_iso=lambda x: datetime.fromisoformat(x) if x else None,
               save_queue_state=Mock(), queue_send_retry=AsyncMock(return_value=True))
    module = ast.fix_missing_locations(ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)] + nodes, type_ignores=[]))
    exec(compile(module, variant, 'exec'), env)
    return env


class ExecutionTests(unittest.TestCase):
    def test_variants(self):
        for variant in ('localization',):
            with self.subTest(variant=variant):
                e = load_functions(variant)
                classify = e['classify_localization_result']
                tid = 'LOCALIZATION-LOCALIZATION_A-00484'
                record = {'TASK_ID': tid}
                task_file = {'filename': f'docs/automation/runs/{tid}.json', 'status': 'added'}
                dds = {'filename': 'localization/graphics/candidates/test.dds', 'status': 'modified'}
                self.assertEqual(classify({**record, 'result':'BLOCKED', 'blocker':'not ready'}, [task_file], tid)[0], 'REJECTED')
                self.assertEqual(classify(record, [task_file], tid)[0], 'REJECTED')
                self.assertEqual(classify(record, [dds, task_file], tid)[0], 'PRODUCED')
                self.assertEqual(classify(record, [{**dds, 'status':'removed'}], tid)[0], 'REJECTED')
                self.assertEqual(classify({'TASK_ID':'other'}, [dds], tid)[0], 'REJECTED')
                self.assertEqual(classify(record, [{'filename':'localization/graphics/masks/x.json'}], tid)[0], 'ADVANCED')
                external = {**record, 'candidate_artifacts':[{'role':'korean_candidate','path':'x.dds','sha256':'a'*64,'drive_file_id':'drive1'}]}
                self.assertEqual(classify(external, [task_file], tid)[0], 'REJECTED')
                self.assertEqual(classify(external, [{'filename':'localization/graphics/qa/x.json'}], tid)[0], 'PRODUCED')

                # Immutable record and changed files must both be queried at the result SHA.
                e['github_api_json'] = Mock(side_effect=[{'content':base64.b64encode(json.dumps(record).encode()).decode()}, {'files':[dds]}])
                self.assertEqual(e['github_localization_result_evidence']({'sha':'abc'}, tid)[0], 'PRODUCED')
                self.assertIn('ref=abc', e['github_api_json'].call_args_list[0].args[0])
                self.assertIn('/commits/abc?', e['github_api_json'].call_args_list[1].args[0])
                e['github_api_json'] = Mock(side_effect=RuntimeError('temporary'))
                self.assertEqual(e['github_localization_result_evidence']({'sha':'def'}, tid)[0], 'RETRY')
                self.assertNotIn(('def', tid), e['_producer_result_evidence_cache'])
                e['github_api_json'] = Mock(side_effect=urllib.error.HTTPError('test',404,'missing',{},None))
                self.assertEqual(e['github_localization_result_evidence']({'sha':'missing'}, tid)[0], 'REJECTED')
                e['github_api_json'] = Mock(side_effect=urllib.error.HTTPError('test',403,'forbidden',{},None))
                self.assertEqual(e['github_localization_result_evidence']({'sha':'denied'}, tid), ('RETRY','RESULT_EVIDENCE_HTTP_403'))

                now = datetime.now(timezone.utc)
                active = {'task_id':tid, 'attempt':1, 'phase':'WAIT_CHAT'}
                q = {}
                e['github_localization_result_evidence'] = Mock(return_value=('REJECTED','BOOKKEEPING_ONLY_NO_ARTIFACT'))
                e['finalize_localization_producer_commit'](q, active, {'sha':'bad'}, now)
                self.assertEqual(active['phase'], 'WAIT_CHAT')
                self.assertIsNone(active['result_sha'])
                self.assertNotIn('completed', q)
                self.assertFalse(e['enqueue_producer_result_for_qa'](q, active))
                e['github_localization_result_evidence'] = Mock(return_value=('ADVANCED','PREREQUISITE_CHANGE_ONLY'))
                e['finalize_localization_producer_commit'](q, active, {'sha':'prep'}, now)
                self.assertEqual(active['terminal'], 'ADVANCED')
                self.assertFalse(e['enqueue_producer_result_for_qa'](q, active))
                e['github_localization_result_evidence'] = Mock(return_value=('PRODUCED','DDS_CHANGED'))
                e['finalize_localization_producer_commit'](q, active, {'sha':'good'}, now)
                self.assertEqual(active['terminal'], 'PRODUCED')
                self.assertEqual(active['automation_validation'], 'PENDING')

                legacy = {'task_id':tid, 'result_sha':'bad'}
                pending = {'qa_pending':[legacy]}
                e['github_localization_result_evidence'] = Mock(return_value=('RETRY','read failure'))
                self.assertEqual(e['select_verified_qa_batch'](pending), [])
                self.assertEqual(pending['qa_pending'], [legacy])
                e['github_localization_result_evidence'] = Mock(return_value=('REJECTED','blocker only'))
                self.assertEqual(e['select_verified_qa_batch'](pending), [])
                self.assertEqual(pending['qa_pending'], [])
                self.assertEqual(pending['qa_ineligible'][0]['result_sha'], 'bad')

                # Same-task recovery is throttled and never consumes CI attempts or rollovers.
                active = {'task_id':tid,'attempt':1,'chat_rollovers':2,'execution_resume_reason':'missing work'}
                asyncio.run(e['resume_incomplete_localization'](None, {}, q, active, 'missing work'))
                self.assertEqual(active['attempt'], 1)
                self.assertEqual(active['chat_rollovers'], 2)
                self.assertEqual(active['execution_resumes'], 1)
                asyncio.run(e['resume_incomplete_localization'](None, {}, q, active, 'missing work'))
                e['queue_send_retry'].assert_awaited_once()

                active.update(lane='LOCALIZATION_C', branch='korean-localization-clean', last_rollover_reason='composer unavailable', qa_batch=[{'task_id':tid,'result_sha':'good'}])
                prompt = e['queue_rollover_prompt'](active)
                self.assertIn('composer unavailable', prompt)
                self.assertIn('QA_BATCH_INPUTS=', prompt)
                self.assertIn('discover GitHub tools', prompt)


if __name__ == '__main__':
    unittest.main()


