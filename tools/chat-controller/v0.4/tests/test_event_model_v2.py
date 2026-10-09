"""Lane/asset regression coverage; historical filename retained for existing runners."""
import asyncio
import base64
import json
import os
import re
import sys
import tempfile
import types
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ''.join(p.read_text() for p in sorted((ROOT / 'src').glob('controller.py.part*')))
TMP = tempfile.TemporaryDirectory()
api = types.ModuleType('playwright.async_api')
api.async_playwright = Mock()
api.BrowserContext = api.Page = object
api.TimeoutError = TimeoutError
m = types.ModuleType('controller_under_test')
sys.modules[m.__name__] = m
source = SOURCE.replace('Path("/logs/controller.log")', repr(TMP.name + '/controller.log'))
source = source.replace('LOG_FILE = ' + repr(TMP.name + '/controller.log'),
                        'LOG_FILE = Path(' + repr(TMP.name + '/controller.log') + ')')
with patch.dict(sys.modules, {'playwright': types.ModuleType('playwright'), 'playwright.async_api': api}), patch.dict(os.environ, {'CONTROLLER_MODE': 'localization', 'AUTO_SEND': 'false'}):
    exec(compile(source, 'controller.py', 'exec'), m.__dict__)

SHA = 'a' * 40
HEAD = 'b' * 40
BLOB = 'c' * 40
PATH = 'textures/load/test/x.dds'


class LaneAssetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        m.STATE_DIR = Path(self.tmp.name)
        m.REGISTRY_FILE = m.STATE_DIR / 'registry.json'
        m.RUNTIME_FILE = m.STATE_DIR / 'runtime.json'
        m.PROMPTS_DIR = ROOT
        self.reg = m.new_registry(m.datetime.now(m.TZ))
        # Unit tests execute mocked I/O inline, independent of thread wakeups.
        async def inline_io(fn, *args, **kwargs):
            return fn(*args, **kwargs)
        worker = patch.object(m.asyncio, 'to_thread', side_effect=inline_io)
        worker.start()
        self.addCleanup(worker.stop)

    def candidate(self, **kw):
        return dict(lane='A', asset_path=PATH, artifact_sha=BLOB,
                    candidate_sha=SHA, result_sha=SHA, state='QA_PENDING', **kw)

    def test_source_has_no_old_execution_engine(self):
        self.assertIsNone(re.search(r'TASK_ID|TaskEvent|task_id|production_id|event_id|rollover|retry_count|chat_rollovers', SOURCE))
        compile(SOURCE, 'controller.py', 'exec')

    def test_parity_uses_csv_index_not_row_position(self):
        rows = [dict(index='53', path='b.dds', action='localize_text', artwork_status='pending_artwork'),
                dict(index='26', path='a.dds', action='localize_text', artwork_status='pending_artwork')]
        self.assertEqual(m.choose_asset(rows, 'A', self.reg)['path'], 'a.dds')
        self.assertEqual(m.choose_asset(rows, 'B', self.reg)['path'], 'b.dds')

    def test_no_duplicate_producer_or_completed_asset(self):
        rows = [dict(index='26', path=PATH, action='localize_text', artwork_status='pending_artwork')]
        for state in ('PASS', 'QA_PENDING', 'WAIT_GATE'):
            self.reg.artifact_records[PATH] = dict(state=state)
            self.assertIsNone(m.choose_asset(rows, 'A', self.reg))
        self.reg.artifact_records.clear()
        self.reg.active_lanes['C1'] = {'asset_path': PATH}
        self.assertIsNone(m.choose_asset(rows, 'A', self.reg))

    def test_rework_priority_and_preserve_exclusion(self):
        rows = [dict(index='26', path=PATH, action='localize_text', artwork_status='pending_artwork'),
                dict(index='28', path='rework.dds', action='localize_text', artwork_status='rework_required'),
                dict(index='30', path='brand.dds', action='localize_text', artwork_status='preserve_original')]
        self.assertEqual(m.choose_asset(rows, 'A', self.reg)['path'], 'rework.dds')

    def test_queue_dedup_is_asset_plus_sha(self):
        c = self.candidate()
        m.enqueue_candidate(self.reg, c)
        m.enqueue_candidate(self.reg, c)
        self.assertEqual(len(self.reg.qa_queue), 1)
        m.enqueue_candidate(self.reg, {**c, 'candidate_sha': HEAD})
        self.assertEqual(len(self.reg.qa_queue), 2)

    def test_checkpoint_survives_restart_and_midnight(self):
        self.reg.logical_date = '2020-01-01'
        self.reg.artifact_records[PATH] = self.candidate()
        self.reg.active_lanes['A'] = dict(lane='A', asset_path=PATH, state='PRODUCING', base_sha=SHA)
        m.enqueue_candidate(self.reg, self.candidate())
        m.save_registry(self.reg)
        loaded = m.load_registry(m.datetime.now(m.TZ))
        self.assertEqual(loaded.active_lanes, self.reg.active_lanes)
        self.assertEqual(loaded.qa_queue, self.reg.qa_queue)
        self.assertEqual(loaded.artifact_records, self.reg.artifact_records)

    def test_old_checkpoint_archived_not_deleted(self):
        old = {'logical_date':'2020-01-01', 'slots':[{'name':'A', 'url':'https://chatgpt.com/c/abc'}],
               'task_events':[{'event_id':'old'}], 'next_production_id':{'A':99}}
        raw = json.dumps(old)
        m.REGISTRY_FILE.write_text(raw)
        reg = m.load_registry(m.datetime.now(m.TZ))
        self.assertEqual(m.REGISTRY_FILE.read_text(), raw)
        self.assertEqual(m.REGISTRY_FILE.with_suffix('.before-lane-asset.json').read_text(), raw)
        self.assertEqual(reg.slots[0].url, old['slots'][0]['url'])
        self.assertEqual(reg.active_lanes, {})
        m.save_registry(reg)
        self.assertNotIn('task_events', json.loads(m.REGISTRY_FILE.read_text()))

    def test_invalid_checkpoint_not_reset(self):
        m.REGISTRY_FILE.write_text('{bad')
        with self.assertRaises(json.JSONDecodeError):
            m.load_registry(m.datetime.now(m.TZ))
        self.assertEqual(m.REGISTRY_FILE.read_text(), '{bad')

    def test_path_and_exact_sha_validation(self):
        with self.assertRaises(ValueError): m.asset_key('../escape')
        with self.assertRaises(ValueError): m.qa_record_path(PATH, 'abc')
        self.assertNotEqual(m.qa_record_path(PATH, SHA), m.qa_record_path(PATH, HEAD))

    def manifest(self, **kw):
        return dict(asset_path=PATH, lane='A', state='PRODUCED', artifact_path='candidates/x.dds',
                    artifact_sha=BLOB, self_qa_path='evidence/x.json', runtime_validation='UNTESTED', **kw)

    def verify(self, manifest, file_effect):
        with patch.object(m, 'github_json_file', return_value=manifest), \
             patch.object(m, 'github_api_json', return_value={'parents':[{'sha':HEAD}]}), \
             patch.object(m, 'github_file', side_effect=file_effect):
            return m.verify_candidate(PATH, SHA, 'A')

    def test_real_dds_change_and_self_qa_accepted(self):
        result = self.verify(self.manifest(), [{'sha':'proof'}, None, {'sha':BLOB}, {'sha':'old'}])
        self.assertEqual(result['candidate_sha'], SHA)
        self.assertEqual(result['state'], 'QA_PENDING')

    def test_unchanged_dds_is_not_production(self):
        with self.assertRaisesRegex(ValueError, 'Unchanged DDS'):
            self.verify(self.manifest(), [{'sha':'proof'}, None, {'sha':BLOB}, {'sha':BLOB}])

    def test_wrong_blob_rejected(self):
        with self.assertRaisesRegex(ValueError, 'blob SHA mismatch'):
            self.verify(self.manifest(), [{'sha':'proof'}, None, {'sha':'wrong'}, None])

    def test_unchanged_self_qa_rejected(self):
        with self.assertRaisesRegex(ValueError, 'self-QA'):
            self.verify(self.manifest(), [{'sha':'proof'}, {'sha':'proof'}])

    def test_wrong_asset_or_lane_rejected(self):
        for key, value in [('lane', 'B'), ('asset_path', 'other.dds'), ('state', 'ADVANCED')]:
            with self.assertRaises(ValueError): self.verify({**self.manifest(), key:value}, [])

    def test_external_candidate_requires_hash_and_file(self):
        with self.assertRaisesRegex(ValueError, 'Drive candidate'):
            self.verify(self.manifest(transport='drive'), [{'sha':'proof'}, None])

    def test_external_material_candidate_accepted(self):
        manifest = {**self.manifest(transport='drive', drive_file_id='file'), 'artifact_sha':'d'*64}
        with patch.object(m, 'github_json_file', side_effect=[manifest, None]), \
             patch.object(m, 'github_api_json', return_value={'parents':[{'sha':HEAD}]}), \
             patch.object(m, 'github_file', side_effect=[{'sha':'proof'}, None]):
            self.assertEqual(m.verify_candidate(PATH, SHA, 'A')['state'], 'QA_PENDING')

    def test_qa_wrong_candidate_sha_rejected(self):
        payload = dict(asset_path=PATH, candidate_sha=HEAD, artifact_sha=BLOB, status='PASS')
        with patch.object(m, 'github_json_file', return_value=payload), self.assertRaisesRegex(ValueError, 'identity'):
            m.read_qa_result(self.candidate(), HEAD)

    def test_qa_requires_independent_commit_and_evidence(self):
        payload = dict(asset_path=PATH, candidate_sha=SHA, artifact_sha=BLOB, status='PASS', evidence_path='qa/proof.json')
        with patch.object(m, 'github_json_file', return_value=payload), patch.object(m, 'latest_path_commit', return_value=SHA), self.assertRaisesRegex(ValueError, 'independent commit'):
            m.read_qa_result(self.candidate(), HEAD)
        with patch.object(m, 'github_json_file', return_value=payload), patch.object(m, 'latest_path_commit', return_value=HEAD), patch.object(m, 'github_file', return_value=None), self.assertRaisesRegex(ValueError, 'independent QA evidence'):
            m.read_qa_result(self.candidate(), HEAD)

    def test_gate_success_releases_only_exact_candidate(self):
        self.reg.artifact_records[PATH] = self.candidate()
        m.enqueue_candidate(self.reg, self.candidate())
        active = {**self.candidate(), 'lane':'C1', 'disposition':'PASS', 'result_sha':HEAD}
        self.reg.active_lanes['C1'] = active
        m.finish_qa(self.reg, active)
        self.assertEqual(self.reg.artifact_records[PATH]['state'], 'PASS')
        self.assertEqual(self.reg.qa_queue, [])

    def test_late_pass_cannot_approve_newer_candidate(self):
        self.reg.artifact_records[PATH] = {**self.candidate(), 'candidate_sha':HEAD}
        active = {**self.candidate(), 'lane':'C1', 'disposition':'PASS', 'result_sha':HEAD}
        m.finish_qa(self.reg, active)
        self.assertEqual(self.reg.artifact_records[PATH]['state'], 'QA_PENDING')

    def test_rework_returns_to_correct_shard(self):
        self.reg.artifact_records[PATH] = self.candidate()
        m.enqueue_candidate(self.reg, self.candidate())
        m.finish_qa(self.reg, {**self.candidate(), 'lane':'C1', 'disposition':'REWORK_REQUIRED', 'result_sha':HEAD})
        rows = [dict(index='26', path=PATH, action='localize_text', artwork_status='pending_artwork')]
        self.assertIsNotNone(m.choose_asset(rows, 'A', self.reg))
        self.assertIsNone(m.choose_asset(rows, 'B', self.reg))

    def test_network_error_is_not_missing_file(self):
        for code in (401,403,429,500):
            err = urllib.error.HTTPError('url', code, 'error', {}, None)
            with patch.object(m, 'github_api_json', side_effect=err), self.assertRaises(urllib.error.HTTPError):
                m.github_file('a.json', SHA)
        with patch.object(m, 'github_api_json', side_effect=urllib.error.HTTPError('url',404,'error',{},None)):
            self.assertIsNone(m.github_file('a.json', SHA))

    def test_generated_prompts_use_only_asset_contract(self):
        a = m.new_producer([{'index':26,'asset_path':PATH}], 'A', HEAD, self.reg)
        for text in (m.producer_prompt(a), m.qa_prompt(self.candidate())):
            self.assertIsNone(re.search(r'TASK_ID|PRODUCTION_ID|EVENT_ID|ATTEMPT=|CHAT_ROLLOVER', text))
            self.assertIn(PATH, text)
        self.assertNotIn('\nASSET=', m.producer_prompt(a))
        self.assertIn('ASSET_SELECTION=AUTONOMOUS_WITHIN_SHARD', m.producer_prompt(a))

    def test_manual_mode_never_dispatches(self):
        with patch.object(m, 'github_branch_head', return_value=HEAD), \
             patch.object(m, 'reconcile_assets'), patch.object(m, 'dispatch_lane', new_callable=AsyncMock) as send:
            asyncio.run(m.localization_cycle(None, {}, self.reg))
            send.assert_not_awaited()

    def test_c_gets_next_slot_without_waiting_for_both_producers(self):
        self.reg.artifact_records[PATH] = self.candidate()
        m.enqueue_candidate(self.reg, self.candidate())
        async def send(context, pages, reg, active):
            reg.active_lanes[active['lane']] = active
            return True
        with patch.object(m,'AUTO_SEND',True), patch.object(m,'github_branch_head',return_value=HEAD), \
             patch.object(m,'reconcile_assets'), patch.object(m,'read_qa_result',return_value=None), \
             patch.object(m,'load_asset_rows',return_value=[]), patch.object(m,'dispatch_lane',side_effect=send) as dispatch:
            asyncio.run(m.localization_cycle(None, {}, self.reg))
            self.assertEqual(dispatch.call_args.args[3]['lane'], 'C1')

    def test_all_three_available_lanes_start_without_two_worker_cap(self):
        self.reg.artifact_records[PATH] = self.candidate()
        m.enqueue_candidate(self.reg, self.candidate())
        rows = [dict(index=str(i),path=f'{i}.dds',action='localize_text',artwork_status='pending_artwork') for i in (26,27)]
        async def send(context, pages, reg, active):
            reg.active_lanes[active['lane']] = active
            return True
        with patch.object(m,'AUTO_SEND',True), patch.object(m,'github_branch_head',return_value=HEAD), \
             patch.object(m,'reconcile_assets'), patch.object(m,'read_qa_result',return_value=None), \
             patch.object(m,'load_asset_rows',return_value=rows), patch.object(m,'dispatch_lane',side_effect=send):
            asyncio.run(m.localization_cycle(None, {}, self.reg))
            self.assertEqual(set(self.reg.active_lanes), {'A','B','C1'})

    def test_four_logical_worker_slots_and_distinct_qa_assignments(self):
        self.assertEqual([slot.name for slot in self.reg.slots], ["A", "B", "C1", "C2"])
        self.assertEqual(m.MAX_ACTIVE_LANES, 4)
        second_path = "textures/load/test/y.dds"
        second = {**self.candidate(), "asset_path": second_path,
                  "candidate_sha": HEAD, "artifact_sha": "d" * 40}
        self.reg.artifact_records[PATH] = self.candidate()
        self.reg.artifact_records[second_path] = second
        m.enqueue_candidate(self.reg, self.candidate())
        m.enqueue_candidate(self.reg, second)
        rows = [dict(index=str(i),path=f"{i}.dds",
                     action="localize_text",artwork_status="pending_artwork")
                for i in (26, 27)]
        async def send(context, pages, reg, active):
            reg.active_lanes[active["lane"]] = active
            return True
        with patch.object(m,"AUTO_SEND",True), \
             patch.object(m,"github_branch_head",return_value=HEAD), \
             patch.object(m,"reconcile_assets"), \
             patch.object(m,"read_qa_result",return_value=None), \
             patch.object(m,"load_asset_rows",return_value=rows), \
             patch.object(m,"dispatch_lane",side_effect=send) as dispatch:
            asyncio.run(m.localization_cycle(None, {}, self.reg))
        self.assertEqual(set(self.reg.active_lanes), {"A", "B", "C1", "C2"})
        self.assertEqual(self.reg.active_lanes["C1"]["asset_path"], PATH)
        self.assertEqual(self.reg.active_lanes["C2"]["asset_path"], second_path)
        self.assertEqual(dispatch.call_count, 4)

    def test_qa_two_workers_do_not_claim_single_candidate_twice(self):
        self.reg.artifact_records[PATH] = self.candidate()
        m.enqueue_candidate(self.reg, self.candidate())
        async def send(context, pages, reg, active):
            reg.active_lanes[active["lane"]] = active
            return True
        with patch.object(m,"AUTO_SEND",True), \
             patch.object(m,"github_branch_head",return_value=HEAD), \
             patch.object(m,"reconcile_assets"), \
             patch.object(m,"read_qa_result",return_value=None), \
             patch.object(m,"load_asset_rows",return_value=[]), \
             patch.object(m,"dispatch_lane",side_effect=send) as dispatch:
            asyncio.run(m.localization_cycle(None, {}, self.reg))
        self.assertEqual(set(self.reg.active_lanes), {"C1"})
        self.assertEqual(dispatch.call_count, 1)

    def test_legacy_c_progress_and_chat_url_migrate_to_c1(self):
        previous_url = "https://chatgpt.com/g/g-p-test/c/old"
        old = m.new_registry(m.datetime.now(m.TZ))
        old.slots = [m.Slot(name="A"), m.Slot(name="B"),
                     m.Slot(name="C", url=previous_url, runs=17)]
        old.active_lanes["C"] = {**self.candidate(), "lane":"C", "state":"VERIFYING",
                                 "chat_url":previous_url, "base_sha":HEAD}
        m.save_registry(old)
        migrated = m.load_registry(m.datetime.now(m.TZ))
        self.assertEqual([slot.name for slot in migrated.slots], ["A", "B", "C1", "C2"])
        self.assertEqual(migrated.slots[2].url, previous_url)
        self.assertEqual(migrated.slots[2].runs, 17)
        self.assertEqual(migrated.active_lanes["C1"]["chat_url"], previous_url)
        self.assertEqual(migrated.active_lanes["C1"]["lane"], "C1")
        self.assertNotIn("C", migrated.active_lanes)
        persisted = m.load_registry(m.datetime.now(m.TZ))
        self.assertEqual(persisted.active_lanes, migrated.active_lanes)

    def test_c2_qa_result_releases_only_owned_candidate(self):
        second_path = "textures/load/test/y.dds"
        one = self.candidate()
        two = {**self.candidate(), "asset_path":second_path,
               "candidate_sha":HEAD, "artifact_sha":"d" * 40}
        self.reg.artifact_records[PATH] = one
        self.reg.artifact_records[second_path] = two
        m.enqueue_candidate(self.reg, one)
        m.enqueue_candidate(self.reg, two)
        self.reg.active_lanes["C1"] = {**one, "lane":"C1", "state":"VERIFYING"}
        worker_two = {**two, "lane":"C2", "state":"WAIT_GATE",
                      "disposition":"PASS", "result_sha":HEAD}
        self.reg.active_lanes["C2"] = worker_two
        m.finish_qa(self.reg, worker_two)
        self.assertEqual(self.reg.artifact_records[second_path]["state"], "PASS")
        self.assertEqual(self.reg.artifact_records[PATH]["state"], "QA_PENDING")
        self.assertEqual(set(self.reg.active_lanes), {"C1"})
        self.assertEqual([item["asset_path"] for item in self.reg.qa_queue], [PATH])

    def test_restart_adopts_existing_qa_before_sending(self):
        self.reg.artifact_records[PATH] = self.candidate()
        m.enqueue_candidate(self.reg, self.candidate())
        with patch.object(m,'AUTO_SEND',True), patch.object(m,'github_branch_head',return_value=HEAD), \
             patch.object(m,'reconcile_assets'), patch.object(m,'read_qa_result',return_value={'status':'PASS','result_sha':HEAD}), \
             patch.object(m,'github_commit_message',return_value='QA'), patch.object(m,'load_asset_rows',return_value=[]), \
             patch.object(m,'dispatch_lane',new_callable=AsyncMock) as send:
            asyncio.run(m.localization_cycle(None, {}, self.reg))
            send.assert_not_awaited()
            self.assertEqual(self.reg.active_lanes['C1']['state'], 'WAIT_GATE')

    def test_failed_or_absent_gate_never_passes(self):
        self.reg.artifact_records[PATH] = self.candidate()
        now = m.datetime.now(m.TZ).isoformat()
        active = {**self.candidate(), 'lane':'C1', 'state':'WAIT_GATE', 'disposition':'PASS',
                  'branch':m.LOCALIZATION_BRANCH, 'workflow':'Localization Automation Gate','gate_started_at':now}
        with patch.object(m,'github_gate_run',return_value={'id':1,'status':'completed','conclusion':'failure'}):
            asyncio.run(m.poll_gate(self.reg, active))
            self.assertEqual(self.reg.artifact_records[PATH]['state'], 'BLOCKED')

    def test_blocked_source_remains_an_option_after_ready_candidates(self):
        rows = [dict(index='26',path=PATH,action='localize_text',artwork_status='pending_artwork'),
                dict(index='28',path='next.dds',action='localize_text',artwork_status='pending_artwork')]
        self.reg.artifact_records[PATH] = dict(state='BLOCKED',reason='source 404')
        options = m.producer_options(rows, 'A', self.reg)
        self.assertEqual([o['asset_path'] for o in options], ['next.dds', PATH])
        self.assertEqual(options[1]['previous_blocker'], 'source 404')

    def test_autonomous_completion_accepts_second_option_not_missing_first(self):
        options = [{'index':26,'asset_path':'missing.dds'}, {'index':28,'asset_path':PATH}]
        active = m.new_producer(options, 'A', HEAD, self.reg)
        self.reg.active_lanes['A'] = active
        self.reg.artifact_records[PATH] = self.candidate()
        with patch.object(m, 'github_api_json', return_value={'status':'ahead'}):
            self.assertTrue(asyncio.run(m.reconcile_active(self.reg, active, HEAD)))
        self.assertEqual(active['asset_path'], PATH)
        self.assertNotIn('A', self.reg.active_lanes)
        self.assertEqual(self.reg.qa_queue[0]['asset_path'], PATH)

    def test_autonomous_completion_rejects_old_commit_and_other_lane(self):
        options = [{'index':26,'asset_path':PATH}]
        active = m.new_producer(options, 'A', HEAD, self.reg)
        self.reg.artifact_records[PATH] = self.candidate()
        with patch.object(m, 'github_api_json', return_value={'status':'behind'}):
            self.assertFalse(asyncio.run(m.reconcile_active(self.reg, active, HEAD)))
        self.reg.artifact_records[PATH]['lane'] = 'B'
        with patch.object(m, 'github_api_json') as api:
            self.assertFalse(asyncio.run(m.reconcile_active(self.reg, active, HEAD)))
            api.assert_not_called()
        self.assertEqual(self.reg.qa_queue, [])

    def test_autonomous_no_result_does_not_block_a_fake_asset(self):
        active = m.new_producer([{'index':26,'asset_path':PATH}], 'A', HEAD, self.reg)
        self.reg.active_lanes['A'] = active
        m.block_lane(self.reg, active, 'No runnable source in this pass')
        self.assertEqual(self.reg.artifact_records, {})
        self.assertIn('A', self.reg.producer_cooldowns)
        m.save_registry(self.reg)
        self.assertEqual(m.load_registry(m.datetime.now(m.TZ)).producer_cooldowns, self.reg.producer_cooldowns)


if __name__ == '__main__':
    unittest.main()

