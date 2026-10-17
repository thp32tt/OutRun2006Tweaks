"""Regression tests for the 00537/00591 review-only controller loop.

Run with python3 -m unittest discover -s tools/chat-controller/v0.4/tests.
Load real controller functions without starting Chrome or reading credentials.
"""
import ast
import asyncio
import base64
import copy
import json
from pathlib import Path
import re
import unittest
import urllib.parse
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ''.join(p.read_text() for p in sorted((ROOT / 'src-vr-v2').glob('controller.py.part*')))


def functions():
    tree = ast.parse(SOURCE)
    tree.body = [ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)] + [
        x for x in tree.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) and (x.name.startswith(('vr_', 'github_feature_', 'conversion_')) or x.name in {'refresh_wait_actions_task_binding', '_parse_iso'})]
    ns = dict(re=re, json=json, datetime=datetime, TZ=timezone.utc, base64=base64, urllib=urllib)
    exec(compile(ast.fix_missing_locations(tree), '<controller>', 'exec'), ns)
    return ns


class Progression(unittest.TestCase):
    def setUp(self):
        self.ns = functions()
        self.sha = 'a' * 40
        self.backlog = json.loads((ROOT / 'feature_backlog.json').read_text())
        self.contract = copy.deepcopy(self.backlog['features'][2])

    def test_40m_busy_chat_must_not_block_resume(self):
        verdict = self.ns['vr_rollover_must_wait_for_owner']
        self.assertTrue(verdict(True, False))   # 30m: keep existing owner
        self.assertFalse(verdict(True, True))   # 40m: force new chat
        self.assertFalse(verdict(False, False)) # idle: safe to rotate
        self.assertIn(
            'if vr_rollover_must_wait_for_owner(owner_busy_or_missing, hard_40m):',
            SOURCE,
        )

    def test_dx9ex_ai_promoted_c6_recovers_changed_paths_from_ancestry(self):
        ns = self.ns
        contract = copy.deepcopy(self.backlog['features'][3])
        base, candidate = 'a'*40, 'b'*40
        source = ['src/vr/ipc/xr_eye_extent.hpp',
                  'src/vr/d3d9/stereo_renderer_r7.inc',
                  'tools/Collect-OutRunVREyeExtent.ps1']
        ns['GITHUB_REPO'] = 'example/repo'
        ns['log'] = __import__('logging').getLogger('vr-progression-test')
        ns['github_api_json'] = lambda url: {
            'behind_by': 0, 'ahead_by': 2,
            'files': [{'filename': p} for p in source]
        }
        active = dict(task_id='DX9EX-TEST', branch='vr-d3d9ex-focus',
                      feature_contract=contract, feature_base_sha=base,
                      delivery_evidence={'sha': candidate})
        record = dict(task_id='DX9EX-TEST', target_branch='vr-d3d9ex-focus',
                      feature_id=contract['feature_id'], work_key=contract['work_key'],
                      checkpoint='C6_STATE', status='COMPLETE_BUILD_VERIFIED',
                      automation_validation='PASS_EXACT_SHA',
                      validation_bearing_result_sha=candidate,
                      acceptance_results=[
                          {'id': item['id'], 'status': 'PASS_FEATURE_CI',
                           'evidence_paths': [source[0] if item['id'] == 'XR-EYE-SIZING'
                                              else source[1] if item['id'] == 'XR-EYE-RESET'
                                              else source[2]],
                           'validation_command': 'CI on exact candidate'}
                          for item in contract['acceptance_items']
                      ])
        gate = dict(head_sha=candidate, status='completed', conclusion='success')
        self.assertEqual(ns['conversion_terminal_verdict'](record, active, gate),
                         (True, 'C6_EXACT_SHA_VERIFIED'))
        self.assertEqual(active['feature_changed_paths'], source)
        # Reject a divergent or unverifiable material ancestry.
        active.pop('feature_changed_paths')
        ns['github_api_json'] = lambda _: {
            'behind_by': 1, 'ahead_by': 1,
            'files': [{'filename': p} for p in source]
        }
        self.assertEqual(ns['conversion_terminal_verdict'](record, active, gate)[0], False)

    def test_durable_dx11_c6_repairs_historical_blocked_dependency_only_after_ci(self):
        ns = self.ns
        contract = copy.deepcopy(self.backlog['features'][0])
        head, candidate, base = 'c'*40, 'b'*40, 'a'*40
        task_id = 'CONVERSION-DX11-00537'
        feature_id = contract['feature_id']
        q = dict(
            active_by_lane={},
            completed=[],
            blocked=[dict(task_id=task_id, feature_id=feature_id,
                          branch='vr-dx11-native-r71', feature_base_sha=base,
                          failure_context='OLD_FAILED_CI', phase='DONE')],
            feature_outcomes={feature_id: {'terminal': 'BLOCKED', 'task_id': task_id}})
        ns['GITHUB_REPO'] = 'example/repo'
        ns['log'] = __import__('logging').getLogger('vr-progression-test')
        ns['github_branch_head'] = lambda _: head
        evidence = ['src/vr/d3d11/live_game_frame_bridge.cpp',
                    'tools/package_dx11_first_game_frame.py']
        ns['github_api_json'] = lambda url: ({
            'behind_by': 0, 'ahead_by': 1,
            'files': [{'filename': p} for p in evidence],
        } if '/compare/' in url else {})
        ns['github_task_record'] = lambda h, ident: dict(
            task_id=ident, target_branch='vr-dx11-native-r71',
            feature_id=feature_id, work_key=contract['work_key'],
            status='COMPLETE_DX11_FIRST_GAME_FRAME_DIAGNOSTIC_CI_RUNTIME_UNTESTED',
            checkpoint='C6_RESULT', automation_validation='PASS_EXACT_SHA',
            validation_bearing_result_sha=candidate,
            acceptance_results=[
                dict(id=item['id'], status='PASS_FEATURE_CI',
                     evidence_paths=[evidence[1] if item['id'] == 'DX11-TEST-BUNDLE'
                                     else evidence[0]],
                     validation_command='exact-SHA tested')
                for item in contract['acceptance_items']])
        ns['github_gate_run'] = lambda *a, **kw: dict(
            head_sha=candidate, status='completed', conclusion='success')
        ns['save_queue_state'] = lambda _: None
        def delivered(active, sha):
            active['delivery_evidence'] = {'sha': sha}
            return True, 'PASS'
        ns['github_feature_delivery_evidence'] = delivered
        self.assertTrue(ns['vr_reconcile_durable_blocked_outcomes'](self.backlog, 'DX11', q))
        self.assertEqual(q['feature_outcomes'][feature_id]['terminal'], 'PASS')
        self.assertEqual(q['completed'][-1]['task_id'], task_id)
        self.assertFalse(q['blocked'])
        self.assertEqual(ns['vr_select_feature'](self.backlog, 'DX11', q)['feature_id'],
                         'DX11:MENU_TO_RACE_FRAME')
        # CI failures may never silently repair a historical BLOCKED task.
        q['feature_outcomes'][feature_id]['terminal'] = 'BLOCKED'
        q['blocked'] = [dict(task_id=task_id, feature_id=feature_id,
                             branch='vr-dx11-native-r71', feature_base_sha=base)]
        q['completed'] = []
        q['vr_blocked_outcome_recheck_at'] = {}
        ns['github_feature_delivery_evidence'] = lambda active, sha: (False, 'NO_CI')
        self.assertFalse(ns['vr_reconcile_durable_blocked_outcomes'](self.backlog, 'DX11', q))
        self.assertEqual(q['feature_outcomes'][feature_id]['terminal'], 'BLOCKED')

    def test_continuous_cadence_keeps_live_owner_until_terminal(self):
        ns = self.ns
        now = datetime(2026, 10, 11, 12, 30, tzinfo=timezone.utc)
        q = {"active_by_lane": {
            "A": {"task_id": "CONVERSION-DX11-00538", "phase": "WAIT_CHAT"},
            "C": {"task_id": "CONVERSION-DX9EX-00593", "phase": "WAIT_ACTIONS"}}}
        due = ns["vr_continuous_dispatch_due"]
        self.assertFalse(due(q, "A", now))
        self.assertFalse(due(q, "C", now))
        self.assertFalse(due(q, "B", now))
        q["active_by_lane"]["A"]["phase"] = "DONE"
        self.assertTrue(due(q, "A", now))
        del q["active_by_lane"]["C"]
        self.assertTrue(due(q, "C", now))

    def test_continuous_processing_never_replaces_live_production(self):
        from unittest.mock import AsyncMock, Mock
        ns = self.ns
        ns.update(CONVERSION_DX11_ENABLED=True, CONVERSION_DX9EX_ENABLED=True,
                  CONVERSION_ONLY_SLOT="", TZ=timezone.utc)
        ns["save_queue_state"] = Mock()
        ns["write_runtime"] = Mock()
        ns["log"] = __import__("logging").getLogger("vr-continuous-test")
        ns["conversion_process_lane"] = AsyncMock()
        ns["vr_checkpoint_and_rollover"] = AsyncMock(return_value=False)
        calls = []
        async def sender(_context, _pages, q, lane, *, force_fresh_chat=False):
            calls.append((lane, force_fresh_chat))
            q["active_by_lane"][lane] = {"task_id": "NEW-" + lane, "phase": "WAIT_CHAT",
                                          "sent_at": datetime.now(timezone.utc).isoformat()}
            return True
        ns["conversion_send_lane_task"] = sender
        q = {"active_by_lane": {
            "A": {"task_id": "OLD-A", "phase": "WAIT_ACTIONS"},
            "C": {"task_id": "OLD-C", "phase": "WAIT_CHAT"}}}
        asyncio.run(ns["vr_continuous_conversion_cycle"](None, {}, q, datetime.now(timezone.utc)))
        self.assertEqual(calls, [])
        self.assertEqual(q["active_by_lane"]["A"]["task_id"], "OLD-A")
        self.assertEqual(q["active_by_lane"]["C"]["task_id"], "OLD-C")
        ns["vr_checkpoint_and_rollover"].assert_awaited_once()
        self.assertNotIn("vr_continuous_superseded", q)
        q["active_by_lane"]["A"]["phase"] = "DONE"
        asyncio.run(ns["vr_continuous_conversion_cycle"](None, {}, q, datetime.now(timezone.utc)))
        self.assertEqual(calls, [("A", True)])
        self.assertEqual(q["active_by_lane"]["A"]["task_id"], "NEW-A")
        self.assertEqual(q["active_by_lane"]["C"]["task_id"], "OLD-C")

    def test_dx11_existing_runtime_untested_acceptance_schema(self):
        contract = copy.deepcopy(self.backlog['features'][0])
        results = []
        paths = []
        for item in contract['acceptance_items']:
            path = 'CMakeLists.txt' if item['id'].endswith('BUNDLE') else 'src/vr/d3d11/live_game_frame_bridge.cpp'
            paths.append(path)
            results.append(dict(id=item['id'], status='PASS_EXACT_SHA_BINARY_PACKAGE' if item['id'].endswith('BUNDLE') else 'PASS_EXACT_SHA_STATIC_SOURCE_AND_BUILD__RUNTIME_UNTESTED', evidence_paths=[path], validation_command='remote exact build'))
        record = dict(feature_id=contract['feature_id'], work_key=contract['work_key'], acceptance_results=results)
        self.assertTrue(self.ns['vr_acceptance_verdict']({'feature_contract': contract}, record, paths)[0])
        results[0]['status'] = 'PASS_MADE_UP'
        self.assertFalse(self.ns['vr_acceptance_verdict']({'feature_contract': contract}, record, paths)[0])

    def delivery_fixture(self, fail_target=False, bad_artifact=False):
        active = dict(branch='target', feature_branch='feature', feature_contract=self.contract)
        def run(branch, sha, name, **kw):
            return dict(id=3 if name.startswith('R84 feature') else (2 if name == 'Domain Isolation Guard' else 1), name=name, head_sha=sha, status='completed', conclusion='failure' if fail_target and name == 'Domain Isolation Guard' else 'success')
        def api(endpoint):
            if '/3/jobs?' in endpoint:
                return {'jobs': [dict(name=n, status='completed', conclusion='success', steps=[dict(name=i['ci_step'] + ' - actual test', status='completed', conclusion='success') for i in self.contract['acceptance_items']]) for n in ['r84-local','r84-win32','r84-host','r84-baseline-game','r84-bundle']]}
            if '/1/jobs?' in endpoint or '/2/jobs?' in endpoint:
                names = ['domain-isolation'] if '/2/' in endpoint else self.contract['required_gates'][0]['jobs']
                return {'jobs': [dict(name=n,status='completed',conclusion='success',steps=[]) for n in names]}
            if '/3/artifacts?' in endpoint:
                return {'artifacts':[dict(id=42, name=self.contract['artifact_prefix'] + self.sha, expired=False, size_in_bytes=100, workflow_run={'head_sha': 'b'*40 if bad_artifact else self.sha})]}
            return {'artifacts':[]}
        self.ns.update(github_gate_run=run, github_api_json=api, GITHUB_REPO='owner/repo')
        return active

    def test_r84_feature_evidence_joins_target_gates_at_same_sha(self):
        active = self.delivery_fixture()
        ok, why = self.ns['github_feature_delivery_evidence'](active, self.sha)
        self.assertTrue(ok, why)
        self.assertEqual(active['delivery_evidence']['artifact_id'], 42)

    def test_target_failure_cannot_be_replaced_by_feature_success(self):
        active = self.delivery_fixture(fail_target=True)
        self.assertFalse(self.ns['github_feature_delivery_evidence'](active, self.sha)[0])

    def test_artifact_from_other_sha_is_rejected(self):
        active = self.delivery_fixture(bad_artifact=True)
        self.assertFalse(self.ns['github_feature_delivery_evidence'](active, self.sha)[0])

    def test_promoted_sha_does_not_chase_bookkeeping(self):
        active = dict(phase='WAIT_ACTIONS',branch='target',task_id='task',feature_branch='feature',feature_promoted_at='now',result_sha=self.sha)
        self.ns.update(github_branch_head=lambda _: 'b'*40, github_task_record=lambda *_: None, github_find_task_commit=lambda *_: {'sha':'b'*40}, _github_commit_list_cache={})
        self.assertIsNone(self.ns['refresh_wait_actions_task_binding'](active))
        self.assertEqual(active['result_sha'], self.sha)

    def test_dx9ex_has_next_independent_development_after_r84(self):
        q = {'feature_outcomes': {self.contract['feature_id']: {'terminal':'PASS'}}}
        item = self.ns['vr_select_feature'](self.backlog, 'DX9EX', q)
        self.assertIsNotNone(item)
        self.assertNotEqual(item['feature_id'], self.contract['feature_id'])

    def test_feature_marker_cannot_skip_promotion(self):
        fn = next(n for n in ast.parse(SOURCE).body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'conversion_process_lane')
        # Execute WAIT_CHAT until remote promotion succeeds. Old marker must not
        # divert this branch to WAIT_ACTIONS without acceptance verification.
        active = dict(phase='WAIT_CHAT',slot='C',branch='target',task_id='task',feature_branch='feature')
        q = {'active_by_lane':{'C':active}}
        class Slot: name = 'C'
        class Registry: slots = [Slot()]
        async def page(*_): return object()
        seen = []
        def promote(a, now):
            seen.append('promote')
            a.update(phase='WAIT_ACTIONS', result_sha=self.sha)
            return True
        self.ns.update(asyncio=asyncio, load_registry=lambda _:Registry(), slot_page=page, github_branch_head=lambda _:self.sha,
                       github_task_record=lambda *_:None, github_find_task_commit=lambda *_:{'sha':'b'*40,'message':'old task marker'},
                       github_feature_promote_ready=promote, VR_FEATURE_PROMOTION_MODE='controller',
                       save_queue_state=lambda _:None, write_runtime=lambda **_:None)
        asyncio.run(self.ns['conversion_process_lane'](None, {}, q, 'C'))
        self.assertEqual(seen, ['promote'])
        self.assertEqual(active['result_sha'], self.sha)

    def test_ai_self_promoted_target_enters_actions_without_controller_push(self):
        active = dict(phase='WAIT_CHAT', slot='C', branch='target',
                      task_id='task', feature_branch='feature')
        q = {'active_by_lane': {'C': active}}
        class Slot: name = 'C'
        class Registry: slots = [Slot()]
        async def page(*_): return object()
        self.ns.update(
            asyncio=asyncio, VR_FEATURE_PROMOTION_MODE='ai',
            load_registry=lambda _: Registry(), slot_page=page,
            github_branch_head=lambda _: self.sha,
            github_task_record=lambda *_: None,
            github_find_task_commit=lambda *_: {'sha': self.sha,
                                                  'message': '[AUTO:task] implemented'},
            github_feature_promote_ready=lambda *args: self.fail("controller must not promote"),
            save_queue_state=lambda _: None,
            write_runtime=lambda **_: None,
        )
        asyncio.run(self.ns['conversion_process_lane'](None, {}, q, 'C'))
        self.assertEqual(active['phase'], 'WAIT_ACTIONS')
        self.assertEqual(active['result_sha'], self.sha)

    def test_c6_is_persisted_without_another_review_chat(self):
        active = self.delivery_fixture()
        active.update(task_id='task',feature_id=self.contract['feature_id'],result_sha=self.sha)
        record = dict(task_id='task',target_branch='target',feature_id=self.contract['feature_id'],work_key=self.contract['work_key'],
                      feature_status='FEATURE_READY', feature_acceptance={'implementation_complete':True}, material_result_sha=self.sha,
                      acceptance_results=[dict(id=i['id'],status='PASS_FEATURE_CI',evidence_paths=[i['paths'][0]+'test.cpp' if i['paths'][0].endswith('/') else i['paths'][0]],validation_command='executed') for i in self.contract['acceptance_items']])
        active['feature_changed_paths'] = [r['evidence_paths'][0] for r in record['acceptance_results']]
        active['delivery_evidence'] = {'sha':self.sha,'gates':[{'run_id':1}], 'artifact_id':42}
        run = dict(head_sha=self.sha,status='completed',conclusion='success')
        written = []
        def mutate(method, path, payload):
            written.append(json.loads(base64.b64decode(payload['content'])))
            return {'commit':{'sha':'b'*40}}
        self.ns.update(VR_CHECKPOINT_BRANCH='controller',github_feature_mutate=mutate,
                       github_api_json=lambda _: {'content':base64.b64encode(json.dumps(written[-1]).encode()).decode()})
        fn = self.ns.get('vr_finalize_verified_feature')
        self.assertIsNotNone(fn, 'controller must own durable completion after verified feature delivery')
        done = fn(active, record, run)
        self.assertEqual(done['status'], 'COMPLETE_BUILD_VERIFIED')
        self.assertEqual(done['runtime_validation'], 'UNTESTED')
        self.assertEqual(written[0]['validation_bearing_result_sha'], self.sha)
        self.assertTrue(active['controller_result_path'].startswith('tools/chat-controller/results/vr/'))
        run['conclusion'] = 'failure'
        self.assertIsNone(fn(active, record, run))
        self.assertEqual(len(written), 1)

    def test_ready_schema_blocker_has_bounded_repair(self):
        fn = self.ns.get('conversion_repair_ready_blocker')
        self.assertIsNotNone(fn)
        active = dict(feature_branch='feature',feature_stage='FEATURE_READY',feature_blocker='ACCEPTANCE_ITEM_PENDING:X',attempt=3)
        self.ns['MAX_TASK_ATTEMPTS'] = 3
        asyncio.run(fn(None, {}, active))
        self.assertEqual(active['phase'], 'BLOCKED')
        self.assertIn('ACCEPTANCE_ITEM_PENDING:X', active['failure_context'])

    def test_no_new_chat_while_feature_ci_runs(self):
        fn = self.ns.get('conversion_repair_ready_blocker')
        self.assertIsNotNone(fn)
        active = dict(feature_branch='feature',feature_stage='FEATURE_READY',feature_blocker='FEATURE_CI_EXACT_SHA_NOT_SUCCESS',attempt=1)
        async def retry(*_):
            raise AssertionError('running CI is not a schema repair')
        self.ns.update(queue_send_retry=retry,MAX_TASK_ATTEMPTS=3)
        self.assertFalse(asyncio.run(fn(None, {}, active)))


if __name__ == '__main__':
    unittest.main()
