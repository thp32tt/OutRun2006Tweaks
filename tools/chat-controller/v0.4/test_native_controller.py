"""Behavioral checks without Chrome, credentials, network or production state writes."""
import ast
import asyncio
import hashlib
import json
import re
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import AsyncMock, Mock

ROOT = Path(__file__).parent
SOURCE = ''.join(p.read_text() for p in sorted((ROOT / 'src').glob('controller.py.part*')))
TREE = ast.parse(SOURCE)
FUNCTIONS = {n.name: n for n in TREE.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def load_function(name, **overrides):
    ns = dict(re=re, json=json, datetime=datetime, timedelta=timedelta, TZ=timezone.utc,
              GITHUB_BROKER_ENABLED=False, NATIVE_PLUGIN_PROTOCOL_VERSION=2,
              GITHUB_ASSISTANT_RECOVERY_MAX=2, GITHUB_TOOLING_RETRY_COOLDOWN_SECONDS=300,
              SAME_TASK_CONTROL_GAP_SECONDS=15,
              PREMATURE_STOP_ROLLOVER_THRESHOLD=3,
              PRODUCER_PREMATURE_STOP_ROLLOVER_THRESHOLD=2,
              PRODUCER_CONTINUATION_COOLDOWN_SECONDS=15,
              LOCALIZATION_PRODUCER_TARGET_CANDIDATES=2,
              LOCALIZATION_PRODUCER_MAX_MATERIAL_COMMITS=8,
              LOCALIZATION_QA_BATCH_SIZE=4,
              QUEUE_STABLE_SECONDS=30, QUEUE_RESULT_GRACE_SECONDS=180,
              _parse_iso=lambda x: datetime.fromisoformat(x) if x else None,
              stable_hash=lambda x: hashlib.sha256(x.encode()).hexdigest(),
              runtime={}, write_runtime=Mock(), save_queue_state=Mock(),
              github_branch_head=Mock(return_value='a'*40),
              github_find_task_commit=Mock(return_value=None), CONTROLLER_MODE='conversion',
              github_transient_retry_pending=lambda: False,
              native_plugin_instructions=lambda active: 'ALL_TOOLS tool search TOOL_NOT_EXPOSED 404 TARGET_BRANCH',
              _is_localization_producer=lambda active: False,
              _is_latched_execution_task=lambda active: False,
              queue_send_producer_execution_continuation=AsyncMock(return_value=False),
              queue_send_conversion_execution_continuation=AsyncMock(return_value=False),
              queue_send_same_chat_control_message=AsyncMock(return_value=True),
              queue_rollover_chat=AsyncMock(return_value=True),
              collect_retry_diagnostic=AsyncMock(return_value={
                  'at': datetime.now(timezone.utc).isoformat(),
                  'classification': 'GENERIC_RETRY_COMPOSER_PRESENT',
                  'composer_visible': True,
                  'retry_surface': 'retry',
              }),
              persist_retry_diagnostic=Mock(),
              localization_material_target_prompt=lambda active: 'CONTROLLER_SELECTED_MATERIAL_TARGETS=T1:index=94;asset=2DA43E41;status=rework_required_zero_pixel_or_artifact;path=x',
              localization_producer_seen_result=lambda active, sha: False,
              localization_c_result_seen=lambda active, sha: False,
              queue_send_c_execution_continuation=AsyncMock(return_value=True))
    ns.update(overrides)
    node = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), FUNCTIONS[name]], type_ignores=[])
    exec(compile(ast.fix_missing_locations(node), '<controller>', 'exec'), ns)
    return ns[name], ns


class NativeControllerTests(unittest.TestCase):
    def active(self):
        return dict(task_id='TASK-1', branch='feature', slot='A', phase='WAIT_CHAT', attempt=1, chat_rollovers=2)

    def test_broker_execution_and_mutation_are_removed(self):
        for name in ('github_api_mutation_json', 'github_broker_apply_changeset', 'queue_handle_broker_response'):
            self.assertNotIn(name, list(FUNCTIONS))
        self.assertFalse((ROOT / 'src/broker_protocol.py').exists())

    def test_prompts_use_native_plugins_without_broker_tags(self):
        for name in ('conversion_dx11', 'conversion_dxvk', 'localization_A', 'localization_B', 'localization_C', 'localization_E'):
            prompt = (ROOT / (name + '.md')).read_text()
            self.assertNotIn('BROKER_', prompt)
            self.assertIn('플러그인', prompt)
            if name in ('localization_A', 'localization_B', 'localization_E'):
                self.assertIn('qa_pending/candidate_awaiting_C', prompt)
                self.assertIn('producer 종료 조건이 아니다', prompt)
                self.assertIn('RESULT_SHA=NOT_CREATED', prompt)
                self.assertIn('같은 응답에서 실제 material 작업', prompt)
                self.assertIn('FINAL_ARTWORK_FIRST', prompt)
                self.assertLessEqual(len(prompt.encode()), 1700)
            else:
                self.assertLessEqual(len(prompt.encode()), 650)
            self.assertIn('Skill', prompt)
            self.assertIn('blocker', prompt)

    def test_preflight_does_not_claim_browser_plugin_connected(self):
        f, ns = load_function('queue_send_github_recovery')
        asyncio.run(f(None, {}, self.active()))
        prompt = ns['queue_send_same_chat_control_message'].call_args.args[3]
        self.assertNotIn('GitHub 연결돼 있어', prompt)
        self.assertIn('ALL_TOOLS', prompt)
        self.assertIn('tool search', prompt)
        self.assertIn('TOOL_NOT_EXPOSED', prompt)

    def test_native_instructions_search_tools_before_blocking(self):
        f, _ = load_function('native_plugin_instructions')
        prompt = f(self.active())
        self.assertIn('ALL_TOOLS', prompt)
        self.assertIn('tool search', prompt)
        self.assertIn('탐색 후', prompt)
        self.assertIn('404', prompt)
        self.assertIn('TARGET_BRANCH/ref', prompt)
        self.assertIn('TOOL_NOT_EXPOSED', prompt)
        self.assertIn('NATIVE_PLUGIN_PROTOCOL_VERSION = 2', SOURCE)

    def test_dynamic_prefix_stays_compact(self):
        native, _ = load_function('native_plugin_instructions')
        f, _ = load_function(
            'queue_dynamic_prefix',
            runtime=dict(
                queue_task_id='CONVERSION-DX11-12345',
                queue_lane='DX11',
                queue_branch='vr-dx11-native-r71',
                queue_base_sha='a' * 40,
                queue_attempt=1,
                queue_failure_context='',
                queue_wave_id='',
                queue_qa_batch=[],
            ),
            MAX_TASK_ATTEMPTS=3,
            native_plugin_instructions=native,
        )
        prefix = f()
        self.assertLessEqual(len(prefix.encode()), 1800)
        self.assertIn('FIRST_ACTION=CALL_CONNECTED_GITHUB_PLUGIN', prefix)
        self.assertIn('ALL_TOOLS', prefix)
        self.assertNotIn('bookkeeping/checkpoint', prefix)

    def test_c_qa_backlog_never_throttles_producers(self):
        self.assertIn('C QA backlog is consumer-only state. It must never pause A/B/E producer dispatch.', SOURCE)
        self.assertNotIn('pending_count >= LOCALIZATION_E_QA_PAUSE_THRESHOLD', SOURCE)
        self.assertNotIn('lane_key == "D" and e_throttled', SOURCE)

    def test_runtime_only_manifest_is_not_producer_completion(self):
        f, _ = load_function('producer_result_claims_no_work')
        self.assertTrue(f({
            'candidate_dds_modified': False,
            'material_deliverable': {
                'type': 'INDEX102_CURRENT_WORKFLOW_CONSUMABLE_SINGLE_DDS_MANIFEST',
                'candidate_dds_modified': False,
                'materially_reduces_unresolved_work': True,
            },
        }))
        self.assertFalse(f({
            'candidate_dds_modified': False,
            'material_deliverable': {
                'type': 'INDEX111_SOURCE_ONLY_PANEL_INTERIOR_RECONSTRUCTION_ADVANCE',
                'candidate_dds_modified': False,
                'materially_reduces_unresolved_work': True,
            },
        }))

    def test_final_artwork_progress_hint_is_runtime_independent(self):
        f, _ = load_function(
            'localization_final_artwork_progress_hint',
            github_json_file_at_ref=lambda path, ref: {
                'graphics_checkpoint': {
                    'final_artwork_completed': 0,
                    'final_artwork_total': 95,
                    'final_artwork_percent': 0,
                }
            },
        )
        hint = f('korean-localization-clean')
        self.assertIn('FINAL_ARTWORK_PROGRESS=0/95', hint)
        self.assertIn('MODE=FINAL_ARTWORK_CONVERGENCE', hint)
        self.assertIn('runtime UNTESTED', hint)

    def test_localization_prefix_injects_final_artwork_convergence(self):
        native, _ = load_function('native_plugin_instructions')
        f, _ = load_function(
            'queue_dynamic_prefix',
            runtime=dict(
                queue_task_id='LOCALIZATION-LOCALIZATION_E-00479',
                queue_lane='LOCALIZATION_E',
                queue_branch='korean-localization-clean',
                queue_base_sha='a' * 40,
                queue_attempt=1,
                queue_failure_context='',
                queue_wave_id='P00313',
                queue_qa_batch=[],
            ),
            CONTROLLER_MODE='localization',
            MAX_TASK_ATTEMPTS=3,
            localization_controller_contract_fingerprint=lambda: ('38', 'b' * 40),
            localization_final_artwork_progress_hint=lambda branch: 'FINAL_ARTWORK_PROGRESS=0/95 (0%); MODE=FINAL_ARTWORK_CONVERGENCE',
            native_plugin_instructions=native,
        )
        prefix = f()
        self.assertIn('FINAL_ARTWORK_PROGRESS=0/95', prefix)
        self.assertIn('FINAL_ARTWORK_FIRST', prefix)
        self.assertIn('runtime-only/DDS_ONLY', prefix)

    def test_no_work_guard_blocks_incomplete_authoritative_state(self):
        status_fn, _ = load_function('_collect_current_status_blockers')
        pending_fn, _ = load_function('_collect_pending_array_blockers')
        f, _ = load_function(
            'localization_no_work_blockers_from_state',
            _collect_current_status_blockers=status_fn,
            _collect_pending_array_blockers=pending_fn,
        )
        state = {
            'graphics_checkpoint': {
                'final_artwork_completed': 0,
                'final_artwork_total': 95,
                'final_artwork_percent': 0,
                'pending_dxt5_assets': ['x.dds'],
                'strict_qa_current': {},
                'next_hd_rework': {'status': 'ZERO_PIXEL_BBOX_REWORK_REQUIRED'},
            },
            'latest_qa_batch': {
                'qa_dispositions': [{'status': 'REWORK_REQUIRED'}],
            },
            'typography_v19_reaudit': {
                'pending_not_completed_apply_on_production': [46],
            },
            'packaging': {'status': 'pending'},
        }
        blockers = f(state)
        self.assertTrue(any(x.startswith('FINAL_ARTWORK_INCOMPLETE:') for x in blockers))
        self.assertTrue(any(x.startswith('FINAL_ARTWORK_PERCENT_LT_100:') for x in blockers))
        self.assertTrue(any('REWORK_REQUIRED' in x for x in blockers))
        self.assertTrue(any('pending_dxt5_assets' in x for x in blockers))
        self.assertTrue(any('pending_not_completed_apply_on_production' in x for x in blockers))
        self.assertIn('PACKAGING_NOT_DONE:pending', blockers)

    def test_no_work_guard_allows_only_complete_clear_state(self):
        status_fn, _ = load_function('_collect_current_status_blockers')
        pending_fn, _ = load_function('_collect_pending_array_blockers')
        f, _ = load_function(
            'localization_no_work_blockers_from_state',
            _collect_current_status_blockers=status_fn,
            _collect_pending_array_blockers=pending_fn,
        )
        state = {
            'graphics_checkpoint': {
                'final_artwork_completed': 95,
                'final_artwork_total': 95,
                'final_artwork_percent': 100,
                'pending_dxt5_assets': [],
                'strict_qa_current': {},
                'next_hd_rework': {'status': 'DONE'},
            },
            'latest_qa_batch': {'qa_dispositions': [{'status': 'PASS'}]},
            'typography_v19_reaudit': {'pending_not_completed_apply_on_production': []},
            'packaging': {'status': 'done'},
        }
        self.assertEqual(f(state), [])

    def test_review_only_zero_material_result_is_no_work_claim(self):
        f, _ = load_function('producer_result_claims_no_work')
        record = {
            'result': 'PASS_REVIEW_NO_RUNNABLE',
            'selection': {'selected_action': 'NO_NEW_PRODUCER_WORK_UNTIL_C'},
            'material_change': False,
            'candidate_dds_modified': False,
            'review_record_only': True,
            'material_deliverable': {
                'type': 'FRESH_SHARD_NO_ACTION_REVIEW',
                'materially_reduces_unresolved_work': False,
            },
        }
        self.assertTrue(f(record))
        self.assertFalse(f({
            'result': 'PASS_MATERIAL_PREFLIGHT',
            'material_change': True,
            'candidate_dds_modified': False,
            'review_record_only': False,
            'material_deliverable': {
                'type': 'NEW_RECONSTRUCTION_INPUT',
                'materially_reduces_unresolved_work': True,
            },
        }))

    def test_missing_task_result_is_work_required_not_no_work(self):
        f, _ = load_function(
            'localization_validate_producer_result_commit',
            github_json_file_at_ref=lambda path, ref: None,
            producer_result_claims_no_work=lambda record: True,
            localization_no_work_blockers_from_state=lambda state: ['BLOCKED'],
        )
        valid, reasons, record = f('TASK-1', 'a' * 40)
        self.assertFalse(valid)
        self.assertEqual(reasons, ['TASK_RESULT_FILE_MISSING'])
        self.assertIsNone(record)

    def test_no_work_result_is_rejected_while_global_work_remains(self):
        def fetch(path, ref):
            if path.endswith('TASK-1.json'):
                return {
                    'task_id': 'TASK-1',
                    'review_record_only': True,
                    'material_change': False,
                    'candidate_dds_modified': False,
                    'material_deliverable': {'materially_reduces_unresolved_work': False},
                }
            return {'state': 'unfinished'}
        f, _ = load_function(
            'localization_validate_producer_result_commit',
            github_json_file_at_ref=fetch,
            producer_result_claims_no_work=lambda record: True,
            localization_no_work_blockers_from_state=lambda state: ['FINAL_ARTWORK_INCOMPLETE:0/95'],
        )
        valid, reasons, _ = f('TASK-1', 'b' * 40)
        self.assertFalse(valid)
        self.assertEqual(reasons, ['FINAL_ARTWORK_INCOMPLETE:0/95'])

    def test_producer_release_paths_use_no_work_guard(self):
        self.assertGreaterEqual(SOURCE.count('localization_handle_producer_commit('), 3)
        self.assertIn('localization_handle_discovered_commit', SOURCE)
        self.assertIn('localization_record_producer_checkpoint', SOURCE)
        self.assertIn('NO_WORK_GUARD_REJECTED', SOURCE)
        self.assertIn('TASK_RESULT_FILE_MISSING', SOURCE)
        self.assertIn("'커밋할 변경 없음'은 종료 사유가 아니다", SOURCE)

    def test_startup_and_watchdog_recovery_use_no_work_guard(self):
        self.assertIn('def localization_reconcile_producer_commit_without_ui(', SOURCE)
        self.assertGreaterEqual(
            SOURCE.count('localization_reconcile_producer_commit_without_ui('), 3
        )
        self.assertIn('producer-no-work-rearmed:', SOURCE)
        self.assertIn('NO_WORK_GUARD_REARMED_STARTUP', SOURCE.replace('f"NO_WORK_GUARD_REARMED_{source}"', 'NO_WORK_GUARD_REARMED_STARTUP'))

    def test_sync_reconcile_keeps_same_task_when_no_work_is_rejected(self):
        finalize = Mock()
        invalidate = Mock()
        f, _ = load_function(
            'localization_reconcile_producer_commit_without_ui',
            localization_validate_producer_result_commit=Mock(
                return_value=(False, ['FINAL_ARTWORK_INCOMPLETE:0/95'], {})
            ),
            finalize_localization_producer_commit=finalize,
            invalidate_task_commit_cache=invalidate,
        )
        active = dict(
            task_id='TASK-1',
            branch='korean-localization-clean',
            slot='A',
            lane='LOCALIZATION_A',
            phase='WAIT_ACTIONS',
            attempt=1,
            terminal=None,
            result_sha='old',
            completed_at='old',
            batch_validation_pending=True,
            wait_actions_started_at='old',
        )
        accepted = f(
            {'completed': []},
            active,
            {'sha': 'b' * 40, 'message': 'review only'},
            datetime.now(timezone.utc),
            'STARTUP',
        )
        self.assertFalse(accepted)
        self.assertEqual(active['task_id'], 'TASK-1')
        self.assertEqual(active['attempt'], 1)
        self.assertEqual(active['phase'], 'WAIT_CHAT')
        self.assertIsNone(active['result_sha'])
        self.assertIn('FINAL_ARTWORK_INCOMPLETE:0/95', active['producer_no_work_guard_reasons'])
        self.assertEqual(active['failure_context'], 'NO_WORK_GUARD_REARMED_STARTUP')
        self.assertNotIn('completed_at', active)
        finalize.assert_not_called()
        invalidate.assert_called_once()

    def test_localization_producer_identity(self):
        f, _ = load_function('_is_localization_producer', CONTROLLER_MODE='localization')
        self.assertTrue(f({'slot': 'A', 'lane': 'LOCALIZATION_A'}))
        self.assertTrue(f({'slot': 'D', 'lane': 'LOCALIZATION_E'}))
        self.assertFalse(f({'slot': 'C', 'lane': 'LOCALIZATION_C'}))
        f2, _ = load_function('_is_localization_producer', CONTROLLER_MODE='conversion')
        self.assertFalse(f2({'slot': 'A', 'lane': 'LOCALIZATION_A'}))

    def test_exact_e00479_planning_only_response_is_not_terminal(self):
        continuation = AsyncMock(return_value=True)
        recovery = AsyncMock(return_value=True)
        f, _ = load_function(
            'queue_handle_native_response',
            _is_localization_producer=lambda active: True,
            queue_send_producer_execution_continuation=continuation,
            queue_send_github_recovery=recovery,
        )
        active = self.active()
        active.update(slot='D', lane='LOCALIZATION_E', task_id='LOCALIZATION-LOCALIZATION_E-00479')
        text_value = (
            'TASK_ID=LOCALIZATION-LOCALIZATION_E-00479 작업 재개. '
            '현재까지는 상태 재구성 단계이며, 아직 이 TASK_ID 결과 커밋은 생성하지 않았다. '
            '다음 단계: E shard 미완료 material 후보 스캔, C qa_pending 제외, DDS 후보 제작. '
            'TASK_ID=LOCALIZATION-LOCALIZATION_E-00479 '
            'RESULT_SHA=NOT_CREATED AUTOMATION_VALIDATION=PENDING RUNTIME_VALIDATION=UNTESTED'
        )
        self.assertTrue(asyncio.run(f(None, {}, active, text_value)))
        continuation.assert_awaited_once()
        recovery.assert_not_awaited()
        self.assertEqual(active['task_id'], 'LOCALIZATION-LOCALIZATION_E-00479')
        self.assertEqual(active['attempt'], 1)
        self.assertEqual(active['phase'], 'WAIT_CHAT')
        self.assertNotIn('result_sha', active)

    def test_producer_no_commit_response_forces_execution_continuation(self):
        continuation = AsyncMock(return_value=True)
        recovery = AsyncMock(return_value=True)
        f, ns = load_function(
            'queue_handle_native_response',
            _is_localization_producer=lambda active: True,
            queue_send_producer_execution_continuation=continuation,
            queue_send_github_recovery=recovery,
        )
        active = self.active()
        text_value = (
            '현재까지는 상태 재구성 단계이며 아직 결과 커밋은 생성하지 않았다. '
            '다음 단계: E shard 스캔. RESULT_SHA=NOT_CREATED'
        )
        self.assertTrue(asyncio.run(f(None, {}, active, text_value)))
        continuation.assert_awaited_once()
        recovery.assert_not_awaited()
        self.assertEqual(active['attempt'], 1)
        self.assertEqual(active['phase'], 'WAIT_CHAT')

    def test_producer_execution_continuation_prompt_forbids_plan_only_stop(self):
        f, ns = load_function(
            'queue_send_producer_execution_continuation',
            CONTROLLER_MODE='localization',
        )
        active = self.active()
        active.update(branch='korean-localization-clean', lane='LOCALIZATION_A')
        sent = asyncio.run(f(None, {}, active, 'h1'))
        self.assertTrue(sent)
        prompt = ns['queue_send_same_chat_control_message'].call_args.args[3]
        self.assertIn('INTERMEDIATE_STATUS_NOT_TERMINAL', prompt)
        self.assertIn('RESULT_SHA=NOT_CREATED', prompt)
        self.assertIn('실제 material 작업', prompt)
        self.assertIn('사용자 확인을 기다리지 말고', prompt)
        self.assertIn('[AUTO:TASK_ID]', prompt)
        self.assertIn('첫 출력은 설명이 아니라', prompt)
        self.assertIn('CONTROLLER_SELECTED_MATERIAL_TARGETS=', prompt)
        self.assertIn('실제 변경부터 수행', prompt)

    def test_producer_candidate_count_and_two_candidate_batch_release(self):
        count_fn, _ = load_function('producer_result_candidate_count')
        indices_fn, _ = load_function(
            'producer_result_candidate_indices',
            producer_result_candidate_count=count_fn,
        )
        paths_fn, _ = load_function(
            'producer_result_candidate_paths',
            producer_result_candidate_count=count_fn,
        )
        enqueue = Mock(return_value=True)
        checkpoint, _ = load_function(
            'localization_record_producer_checkpoint',
            localization_producer_seen_result=lambda active, sha: False,
            producer_result_candidate_count=count_fn,
            producer_result_candidate_indices=indices_fn,
            producer_result_candidate_paths=paths_fn,
            enqueue_producer_result_for_qa=enqueue,
            localization_qa_inflight_candidate_indices=lambda q: [],
            _localization_material_target_cache={},
            localization_remaining_material_targets=lambda active: [{'index':163}],
            producer_result_claims_no_work=lambda record: False,
            LOCALIZATION_PRODUCER_TARGET_CANDIDATES=2,
            LOCALIZATION_PRODUCER_MAX_MATERIAL_COMMITS=8,
        )
        q={'qa_pending':[]}
        active=dict(
            task_id='LOCALIZATION-LOCALIZATION_B-00477',
            lane='LOCALIZATION_B',
            branch='korean-localization-clean',
            pipeline_result_shas=[],
            pipeline_candidate_indices=[],
        )
        record1={
            'task_id':active['task_id'],
            'candidate_dds_modified':True,
            'selection':{'index':94},
            'material_deliverable':{'candidate_dds_modified':True},
        }
        release, reason=checkpoint(q,active,{'sha':'1'*40,'message':'m1'},record1,datetime.now(timezone.utc))
        self.assertFalse(release)
        self.assertIn('CONTINUE_PIPELINE', reason)
        self.assertEqual(active['pipeline_candidate_count'],1)
        self.assertEqual(active['pipeline_candidate_indices'],[94])
        self.assertEqual(enqueue.call_count,1)

        checkpoint2, _ = load_function(
            'localization_record_producer_checkpoint',
            localization_producer_seen_result=lambda active, sha: sha in active.get('pipeline_result_shas',[]),
            producer_result_candidate_count=count_fn,
            producer_result_candidate_indices=indices_fn,
            producer_result_candidate_paths=paths_fn,
            enqueue_producer_result_for_qa=enqueue,
            localization_qa_inflight_candidate_indices=lambda q: [],
            _localization_material_target_cache={},
            localization_remaining_material_targets=lambda active: [{'index':205}],
            producer_result_claims_no_work=lambda record: False,
            LOCALIZATION_PRODUCER_TARGET_CANDIDATES=2,
            LOCALIZATION_PRODUCER_MAX_MATERIAL_COMMITS=8,
        )
        record2={
            'task_id':active['task_id'],
            'candidate_dds_modified':True,
            'selection':{'index':163},
            'material_deliverable':{'candidate_dds_modified':True},
        }
        release2, reason2=checkpoint2(q,active,{'sha':'2'*40,'message':'m2'},record2,datetime.now(timezone.utc))
        self.assertTrue(release2)
        self.assertIn('TARGET_REACHED:2/2', reason2)
        self.assertEqual(active['pipeline_candidate_count'],2)
        self.assertEqual(enqueue.call_count,2)

    def test_intermediate_producer_commit_keeps_same_task_latched(self):
        finalize=Mock()
        continuation=AsyncMock(return_value=True)
        f, _ = load_function(
            'localization_handle_producer_commit',
            localization_producer_seen_result=lambda active, sha: False,
            localization_validate_producer_result_commit=Mock(return_value=(True,[],{'candidate_dds_modified':True})),
            localization_record_producer_checkpoint=Mock(return_value=(False,'CONTINUE_PIPELINE:candidates=1/2')),
            invalidate_task_commit_cache=Mock(),
            finalize_localization_producer_commit=finalize,
            queue_send_producer_pipeline_continuation=continuation,
        )
        active=self.active()
        active.update(
            task_id='LOCALIZATION-LOCALIZATION_B-00477',
            branch='korean-localization-clean',
            lane='LOCALIZATION_B',
            task_latched=True,
        )
        accepted=asyncio.run(f(None,{}, {}, active, {'sha':'a'*40,'message':'material'}, datetime.now(timezone.utc)))
        self.assertFalse(accepted)
        self.assertEqual(active['phase'],'WAIT_CHAT')
        self.assertTrue(active['task_latched'])
        self.assertEqual(active['controller_stage'],'CONTINUE_PIPELINE')
        self.assertTrue(continuation.await_count)
        finalize.assert_not_called()

    def test_c_result_requires_every_immutable_batch_input(self):
        batch=[
            {'task_id':'A-1','result_sha':'a'*40},
            {'task_id':'B-2','result_sha':'b'*40},
        ]
        def missing_fetch(path, ref):
            return {'task_id':'C-1','inputs':['A-1@'+'a'*40]}
        f, _ = load_function(
            'localization_validate_c_result_commit',
            github_json_file_at_ref=missing_fetch,
        )
        valid,reasons,_=f('C-1','c'*40,batch)
        self.assertFalse(valid)
        self.assertIn('C_BATCH_INPUTS_MISSING',reasons[0])

        def full_fetch(path, ref):
            return {'task_id':'C-1','inputs':['A-1@'+'a'*40,'B-2@'+'b'*40]}
        f2, _ = load_function(
            'localization_validate_c_result_commit',
            github_json_file_at_ref=full_fetch,
        )
        valid2,reasons2,_=f2('C-1','d'*40,batch)
        self.assertTrue(valid2)
        self.assertEqual(reasons2,[])

    def test_c_incomplete_commit_is_rejected_before_actions(self):
        continuation=AsyncMock(return_value=True)
        invalidate=Mock()
        f, _ = load_function(
            'localization_bind_c_commit',
            localization_c_result_seen=lambda active, sha: False,
            localization_validate_c_result_commit=Mock(return_value=(False,['C_BATCH_INPUTS_MISSING:B-2'],{})),
            invalidate_task_commit_cache=invalidate,
            queue_send_c_execution_continuation=continuation,
        )
        active=self.active()
        active.update(
            task_id='LOCALIZATION-LOCALIZATION_C-00476',
            branch='korean-localization-clean',
            lane='LOCALIZATION_C',
            qa_batch=[{'task_id':'B-2','result_sha':'b'*40}],
            task_latched=True,
        )
        handled=asyncio.run(f(None,{},active,{'sha':'c'*40,'message':'partial'},datetime.now(timezone.utc)))
        self.assertTrue(handled)
        self.assertEqual(active['phase'],'WAIT_CHAT')
        self.assertEqual(active['controller_stage'],'WAIT_QA_RESULT')
        self.assertIsNone(active['result_sha'])
        continuation.assert_awaited_once()
        invalidate.assert_called_once()

    def test_c_valid_commit_binds_exact_sha_to_actions(self):
        f, _ = load_function(
            'localization_bind_c_commit',
            localization_c_result_seen=lambda active, sha: False,
            localization_validate_c_result_commit=Mock(return_value=(True,[],{})),
        )
        active=self.active()
        active.update(
            task_id='LOCALIZATION-LOCALIZATION_C-00476',
            branch='korean-localization-clean',
            lane='LOCALIZATION_C',
            qa_batch=[{'task_id':'B-2','result_sha':'b'*40}],
        )
        handled=asyncio.run(f(None,{},active,{'sha':'c'*40,'message':'complete'},datetime.now(timezone.utc)))
        self.assertTrue(handled)
        self.assertEqual(active['phase'],'WAIT_ACTIONS')
        self.assertEqual(active['result_sha'],'c'*40)
        self.assertEqual(active['controller_stage'],'WAIT_ACTIONS')

    def test_c_success_path_continues_drain_in_same_task(self):
        source=ast.get_source_segment(SOURCE, FUNCTIONS['localization_process_lane']) or ''
        self.assertIn('finalize_c_qa_batch(q, active)',source)
        self.assertIn('localization_prepare_c_next_batch(active, next_batch, now)',source)
        self.assertIn('qa_batches_completed_in_task',source)
        self.assertIn('c_drain_waiting',source)
        self.assertIn('PREVIOUS_BATCH_PASS_CONTINUE_DRAIN',source)

    def test_localization_dispatch_initializes_pipeline_latches(self):
        source=ast.get_source_segment(SOURCE, FUNCTIONS['localization_send_lane_task']) or ''
        self.assertIn('"pipeline_candidate_count"',source)
        self.assertIn('"qa_batches_completed_in_task"',source)
        self.assertIn('"c_consumed_result_shas"',source)
        self.assertIn('True if CONTROLLER_MODE in {"conversion", "localization"}',source)

    def test_localization_compose_tunes_continuous_pipeline(self):
        compose=(ROOT/'docker-compose.portainer-localization.yml').read_text()
        self.assertIn('LOCALIZATION_PRODUCER_TARGET_CANDIDATES: "2"',compose)
        self.assertIn('LOCALIZATION_PRODUCER_MAX_MATERIAL_COMMITS: "8"',compose)
        self.assertIn('GITHUB_TASK_COMMIT_CACHE_SECONDS: "15"',compose)
        self.assertIn('PREVIOUS_TASK_UI_SETTLE_SECONDS: "45"',compose)

    def test_c_plan_only_response_continues_same_batch(self):
        continuation=AsyncMock(return_value=True)
        rollover=AsyncMock(return_value=False)
        f, _ = load_function(
            'queue_handle_native_response',
            CONTROLLER_MODE='localization',
            _is_localization_producer=lambda active:False,
            queue_send_c_execution_continuation=continuation,
            queue_rollover_chat=rollover,
        )
        active=self.active()
        active.update(
            task_id='LOCALIZATION-LOCALIZATION_C-00476',
            lane='LOCALIZATION_C',
            qa_batch=[{'task_id':'B-1','result_sha':'b'*40}],
            sent_at='2026-10-02T00:00:00+00:00',
        )
        self.assertTrue(asyncio.run(f(None,{},active,'상태 확인 완료. 다음 단계에서 QA를 수행하겠습니다.')))
        continuation.assert_awaited_once()
        self.assertEqual(active['c_premature_stop_count'],1)
        self.assertEqual(active['task_id'],'LOCALIZATION-LOCALIZATION_C-00476')

    def test_c_second_plan_only_turn_rolls_same_task(self):
        continuation=AsyncMock(return_value=True)
        rollover=AsyncMock(return_value=True)
        f, _ = load_function(
            'queue_handle_native_response',
            CONTROLLER_MODE='localization',
            _is_localization_producer=lambda active:False,
            queue_send_c_execution_continuation=continuation,
            queue_rollover_chat=rollover,
        )
        active=self.active()
        active.update(
            task_id='LOCALIZATION-LOCALIZATION_C-00476',
            lane='LOCALIZATION_C',
            qa_batch=[{'task_id':'B-1','result_sha':'b'*40}],
            sent_at='2026-10-02T00:00:00+00:00',
            c_premature_stop_count=1,
            c_premature_stop_total=1,
            c_premature_stop_counted_for_send_at='older',
        )
        self.assertTrue(asyncio.run(f(None,{},active,'또 계획만 출력')))
        rollover.assert_awaited_once()
        self.assertEqual(active['c_premature_stop_count'],0)

    def test_c_rollover_carries_current_qa_batch(self):
        f, _ = load_function(
            'queue_rollover_prompt',
            CONTROLLER_MODE='localization',
            MAX_TASK_ATTEMPTS=3,
            localization_controller_contract_fingerprint=lambda:('43','f'*40),
            localization_final_artwork_progress_hint=lambda branch:'FINAL_ARTWORK_PROGRESS=0/95 (0%); MODE=FINAL_ARTWORK_CONVERGENCE',
            _is_localization_producer=lambda active:False,
        )
        active=self.active()
        active.update(
            task_id='LOCALIZATION-LOCALIZATION_C-00476',
            lane='LOCALIZATION_C',
            branch='korean-localization-clean',
            task_latched=True,
            controller_stage='WAIT_QA_RESULT',
            qa_batch=[{'task_id':'B-1','result_sha':'b'*40}],
            qa_batches_completed_in_task=3,
        )
        prompt=f(active)
        self.assertIn('ACTIVE_TASK_LATCH=ON',prompt)
        self.assertIn('QA_BATCHES_COMPLETED=3',prompt)
        self.assertIn('QA_BATCH_INPUTS=',prompt)
        self.assertIn('B-1',prompt)
        self.assertIn('FIRST_EXECUTION_ACTION=CALL_CONNECTED_TOOL',prompt)

    def test_blocked_producer_recovery_cannot_bypass_batch_gate(self):
        source=ast.get_source_segment(SOURCE, FUNCTIONS['reconcile_localization_blocked_producer_commits']) or ''
        self.assertIn('localization_record_producer_checkpoint',source)
        self.assertIn('pipeline_release_decision',source)
        self.assertIn('CONTINUE_PIPELINE',source)
        self.assertIn('pipeline_continuation_pending',source)

    def test_c_retirement_does_not_double_finalize_already_drained_batch(self):
        source=ast.get_source_segment(SOURCE, FUNCTIONS['localization_parallel_cycle']) or ''
        self.assertIn('if not ctask.get("qa_batch_finalized")',source)
        self.assertIn('finalize_c_qa_batch(q, ctask)',source)

    def test_conversion_no_commit_response_forces_execution_continuation(self):
        continuation = AsyncMock(return_value=True)
        recovery = AsyncMock(return_value=True)
        f, _ = load_function(
            'queue_handle_native_response',
            CONTROLLER_MODE='conversion',
            _is_localization_producer=lambda active: False,
            queue_send_conversion_execution_continuation=continuation,
            queue_send_github_recovery=recovery,
        )
        active = self.active()
        active.update(lane='DX11', branch='vr-dx11-native-r71')
        text_value = 'HEAD 확인 완료. 다음 단계에서 구현하겠습니다. RESULT_SHA=NOT_CREATED'
        self.assertTrue(asyncio.run(f(None, {}, active, text_value)))
        continuation.assert_awaited_once()
        recovery.assert_not_awaited()
        self.assertEqual(active['task_id'], 'TASK-1')
        self.assertEqual(active['attempt'], 1)
        self.assertEqual(active['phase'], 'WAIT_CHAT')

    def test_conversion_premature_stop_rolls_same_task_on_third_turn(self):
        same_chat = AsyncMock(return_value=True)
        rollover = AsyncMock(return_value=True)
        f, _ = load_function(
            'queue_send_conversion_execution_continuation',
            CONTROLLER_MODE='conversion',
            queue_send_same_chat_control_message=same_chat,
            queue_rollover_chat=rollover,
        )
        active = self.active()
        active.update(
            lane='DX11',
            branch='vr-dx11-native-r71',
            sent_at='2026-10-02T00:00:00+00:00',
            chat_rollovers=0,
            task_latched=True,
        )
        self.assertTrue(asyncio.run(f(None, {}, active, 'h1')))
        self.assertEqual(active['premature_stop_count'], 1)
        active['sent_at'] = '2026-10-02T00:01:00+00:00'
        self.assertTrue(asyncio.run(f(None, {}, active, 'h2')))
        self.assertEqual(active['premature_stop_count'], 2)
        active['sent_at'] = '2026-10-02T00:02:00+00:00'
        self.assertTrue(asyncio.run(f(None, {}, active, 'h3')))
        rollover.assert_awaited_once()
        self.assertEqual(active['premature_stop_count'], 0)
        self.assertEqual(active['premature_stop_total'], 3)
        self.assertTrue(active['task_latched'])
        self.assertEqual(active['phase'], 'WAIT_CHAT')

    def test_conversion_continuation_is_github_only_and_skill_optional(self):
        f, ns = load_function(
            'queue_send_conversion_execution_continuation',
            CONTROLLER_MODE='conversion',
        )
        active = self.active()
        active.update(branch='vr-dxvk-r71-disasm', lane='DXVK')
        self.assertTrue(asyncio.run(f(None, {}, active, 'h1')))
        prompt = ns['queue_send_same_chat_control_message'].call_args.args[3]
        self.assertIn('GITHUB_ONLY_DEVELOPMENT=true', prompt)
        self.assertIn('로컬 개발 PC', prompt)
        self.assertIn('Skill', prompt)
        self.assertIn('[AUTO:TASK_ID]', prompt)
        self.assertIn('RESULT_SHA=NOT_CREATED', prompt)

    def test_latched_execution_identity_includes_conversion(self):
        loc = lambda active: active.get('lane') == 'LOCALIZATION_A'
        f, _ = load_function(
            '_is_latched_execution_task',
            CONTROLLER_MODE='conversion',
            _is_localization_producer=loc,
        )
        self.assertTrue(f({'lane':'DX11'}))
        f2, _ = load_function(
            '_is_latched_execution_task',
            CONTROLLER_MODE='localization',
            _is_localization_producer=loc,
        )
        self.assertTrue(f2({'lane':'LOCALIZATION_A'}))
        self.assertTrue(f2({'lane':'LOCALIZATION_C', 'slot':'C'}))

    def test_conversion_parallel_migrates_legacy_b_and_dispatches_missing_dx11(self):
        q = {
            'counter': 269,
            'active': {
                'task_id':'CONVERSION-DXVK-00269',
                'slot':'B',
                'lane':'DXVK',
                'branch':'vr-dxvk-r71-disasm',
                'workflow':'Backend Conversion Gate',
                'phase':'WAIT_ACTIONS',
                'attempt':1,
                'sent_at':'2026-10-02T02:00:00+00:00',
                'result_sha':'a'*40,
            },
            'active_by_lane': {},
            'completed': [],
            'blocked': [],
        }
        reg = SimpleNamespace(
            slots=[
                SimpleNamespace(name='A', last_sent_at='2026-10-02T00:30:00+00:00', last_task_completed_at=None),
                SimpleNamespace(name='B', last_sent_at='2026-10-02T02:00:00+00:00', last_task_completed_at=None),
            ]
        )
        send = AsyncMock(return_value=True)
        process = AsyncMock(return_value=None)
        f, ns = load_function(
            'conversion_parallel_cycle',
            CONTROLLER_MODE='conversion',
            load_queue_state=lambda:q,
            load_registry=lambda now:reg,
            reconcile_legacy_conversion_blocked=Mock(),
            queue_upgrade_native_context=AsyncMock(return_value=False),
            rate_limit_active=lambda *args:False,
            localization_process_lane_isolated=process,
            localization_safe_send_lane_task=send,
            save_registry=Mock(),
        )
        asyncio.run(f(None,{}))
        self.assertIsNone(q['active'])
        self.assertEqual(q['active_by_lane']['B']['task_id'],'CONVERSION-DXVK-00269')
        self.assertTrue(q['active_by_lane']['B']['task_latched'])
        self.assertEqual(q['active_by_lane']['B']['controller_stage'],'WAIT_ACTIONS')
        process.assert_awaited()
        self.assertEqual(send.await_args.args[3], 'A')

    def test_conversion_parallel_scheduler_is_selected(self):
        source = ast.get_source_segment(SOURCE, FUNCTIONS['scheduler_loop']) or ''
        self.assertIn('CONTROLLER_MODE == "conversion"', source)
        self.assertIn('await conversion_parallel_cycle(context, pages)', source)

    def test_conversion_parallel_dispatch_uses_conversion_task_prefix(self):
        source = ast.get_source_segment(SOURCE, FUNCTIONS['localization_send_lane_task']) or ''
        self.assertIn('"CONVERSION" if CONTROLLER_MODE == "conversion"', source)
        self.assertIn('"WAIT_DURABLE_RESULT" if CONTROLLER_MODE == "conversion"', source)

    def test_no_progress_is_handled_even_when_send_deferred(self):
        self.assertTrue('queue_handle_native_response' in FUNCTIONS)
        f, ns = load_function('queue_handle_native_response', queue_send_github_recovery=AsyncMock(return_value=False))
        active = self.active()
        self.assertTrue(asyncio.run(f(None, {}, active, 'GitHub 연결 오류, 작업 불가')))
        self.assertEqual(active['attempt'], 1)
        self.assertEqual(active['phase'], 'WAIT_CHAT')
        self.assertEqual(active['chat_rollovers'], 2)

    def test_success_prose_without_commit_is_not_success(self):
        self.assertTrue('queue_handle_native_response' in FUNCTIONS)
        f, ns = load_function('queue_handle_native_response', queue_send_github_recovery=AsyncMock(return_value=True))
        active = self.active()
        self.assertTrue(asyncio.run(f(None, {}, active, '수정 완료. RESULT_SHA=' + 'f'*40)))
        self.assertNotIn('result_sha', active)
        self.assertEqual(active['phase'], 'WAIT_CHAT')

    def test_recovery_cap_keeps_same_task_in_cooldown(self):
        f, ns = load_function('queue_send_github_recovery')
        active = self.active(); active['github_recovery_prompts'] = 2
        self.assertTrue(asyncio.run(f(None, {}, active)))
        ns['queue_send_same_chat_control_message'].assert_not_called()
        self.assertEqual(active['attempt'], 1)
        self.assertGreater(datetime.fromisoformat(active['github_tooling_retry_until']), datetime.now(timezone.utc))

    def test_duplicate_response_does_not_resend(self):
        self.assertTrue('queue_handle_native_response' in FUNCTIONS)
        f, ns = load_function('queue_handle_native_response', queue_send_github_recovery=AsyncMock(return_value=True))
        active=self.active()
        for _ in range(3): self.assertTrue(asyncio.run(f(None, {}, active, '작업 불가')))
        self.assertEqual(ns['queue_send_github_recovery'].call_count, 1)

    def test_migration_preserves_task_and_pending_file(self):
        self.assertTrue('queue_upgrade_native_context' in FUNCTIONS)
        f, ns=load_function('queue_upgrade_native_context', native_plugin_instructions=lambda active: 'native')
        active=self.active(); active.update(broker_mode=True, broker_pending_file='/data/state/broker_pending/TASK-1.json')
        self.assertTrue(asyncio.run(f(None, {}, {'active':active}, active)))
        self.assertEqual(active['task_id'],'TASK-1')
        self.assertEqual(active['attempt'],1)
        self.assertEqual(active['chat_rollovers'],2)
        self.assertEqual(active['legacy_broker_pending_file'],'/data/state/broker_pending/TASK-1.json')
        self.assertEqual(active['native_plugin_protocol_version'],2)
        self.assertFalse(asyncio.run(f(None, {}, {'active':active}, active)))
        self.assertEqual(ns['queue_send_same_chat_control_message'].call_count,1)

    def test_same_task_control_guard_uses_short_gap_not_new_task_gap(self):
        f, _ = load_function(
            'same_task_control_send_guard_reason',
            rate_limit_active=lambda *args: False,
            rate_limit_seconds_remaining=lambda *args: 0,
        )
        now = datetime.now(timezone.utc)
        reg = SimpleNamespace(last_global_send_at=(now - timedelta(seconds=20)).isoformat())
        slot = SimpleNamespace(last_sent_at=(now - timedelta(seconds=20)).isoformat())
        self.assertIsNone(f(reg, slot, now))
        reg.last_global_send_at = (now - timedelta(seconds=5)).isoformat()
        self.assertTrue(f(reg, slot, now).startswith('same_task_control_gap:'))

    def test_same_chat_control_message_uses_same_task_guard(self):
        node_source = ast.get_source_segment(SOURCE, FUNCTIONS['queue_send_same_chat_control_message']) or ''
        self.assertIn('same_task_control_send_guard_reason', node_source)
        self.assertNotIn('guard = send_guard_reason(', node_source)

    def test_producer_premature_stop_escalates_to_rollover_on_second_turn(self):
        same_chat = AsyncMock(return_value=True)
        rollover = AsyncMock(return_value=True)
        f, _ = load_function(
            'queue_send_producer_execution_continuation',
            _is_localization_producer=lambda active: True,
            queue_send_same_chat_control_message=same_chat,
            queue_rollover_chat=rollover,
        )
        active = self.active()
        active.update(
            lane='LOCALIZATION_E',
            branch='korean-localization-clean',
            sent_at='2026-10-02T00:00:00+00:00',
            task_latched=True,
            chat_rollovers=0,
        )
        self.assertTrue(asyncio.run(f(None, {}, active, 'h1')))
        self.assertEqual(active['premature_stop_count'], 1)
        self.assertTrue(active['task_latched'])
        self.assertEqual(active['controller_stage'], 'WAIT_MATERIAL_COMMIT')
        self.assertEqual(same_chat.call_count, 1)
        rollover.assert_not_awaited()

        active['sent_at'] = '2026-10-02T00:01:00+00:00'
        self.assertTrue(asyncio.run(f(None, {}, active, 'h2')))
        rollover.assert_awaited_once()
        self.assertEqual(active['premature_stop_count'], 0)
        self.assertEqual(active['premature_stop_total'], 2)
        self.assertEqual(same_chat.call_count, 1)
        self.assertEqual(active['phase'], 'WAIT_CHAT')
        self.assertTrue(active['task_latched'])

    def test_same_premature_turn_is_counted_only_once_until_controller_sends_again(self):
        same_chat = AsyncMock(return_value=False)
        rollover = AsyncMock(return_value=False)
        f, _ = load_function(
            'queue_send_producer_execution_continuation',
            _is_localization_producer=lambda active: True,
            queue_send_same_chat_control_message=same_chat,
            queue_rollover_chat=rollover,
        )
        active = self.active()
        active.update(
            lane='LOCALIZATION_A',
            branch='korean-localization-clean',
            sent_at='2026-10-02T00:00:00+00:00',
            task_latched=True,
            chat_rollovers=0,
        )
        asyncio.run(f(None, {}, active, 'same'))
        asyncio.run(f(None, {}, active, 'same'))
        asyncio.run(f(None, {}, active, 'same'))
        self.assertEqual(active['premature_stop_count'], 1)
        self.assertEqual(active['premature_stop_total'], 1)
        rollover.assert_not_awaited()

    def test_rollover_prompt_carries_persistent_task_checkpoint(self):
        f, _ = load_function(
            'queue_rollover_prompt',
            CONTROLLER_MODE='localization',
            MAX_TASK_ATTEMPTS=3,
            localization_controller_contract_fingerprint=lambda: ('38', 'b' * 40),
            localization_final_artwork_progress_hint=lambda branch: 'FINAL_ARTWORK_PROGRESS=0/95 (0%); MODE=FINAL_ARTWORK_CONVERGENCE',
            _is_localization_producer=lambda active: True,
        )
        active = self.active()
        active.update(
            lane='LOCALIZATION_E',
            branch='korean-localization-clean',
            task_id='LOCALIZATION-LOCALIZATION_E-00479',
            task_latched=True,
            controller_stage='WAIT_MATERIAL_COMMIT',
            last_checkpoint_head='c' * 40,
            premature_stop_total=3,
        )
        prompt = f(active)
        self.assertIn('ACTIVE_TASK_LATCH=ON', prompt)
        self.assertIn('CONTROLLER_STAGE=WAIT_MATERIAL_COMMIT', prompt)
        self.assertIn('LAST_CHECKPOINT_HEAD=' + 'c' * 40, prompt)
        self.assertIn('FIRST_EXECUTION_ACTION=CALL_CONNECTED_TOOL', prompt)
        self.assertIn('CONTROLLER_SELECTED_MATERIAL_TARGETS=', prompt)
        self.assertIn('FINAL_ARTWORK_PROGRESS=0/95', prompt)

    def test_localization_producer_dispatch_injects_concrete_material_target(self):
        send_source = ast.get_source_segment(SOURCE, FUNCTIONS['localization_send_lane_task']) or ''
        cont_source = ast.get_source_segment(SOURCE, FUNCTIONS['queue_send_producer_execution_continuation']) or ''
        roll_source = ast.get_source_segment(SOURCE, FUNCTIONS['queue_rollover_prompt']) or ''
        helper_source = ast.get_source_segment(SOURCE, FUNCTIONS['localization_material_target_hints']) or ''
        self.assertIn('localization_material_target_prompt', send_source)
        self.assertIn('localization_material_target_prompt', cont_source)
        self.assertIn('localization_material_target_prompt', roll_source)
        self.assertIn('rework_required', helper_source)
        self.assertIn('candidate_qa_pending', helper_source)
        self.assertIn('source_identity_mismatch', helper_source)
        self.assertIn('idx % 3', helper_source)

    def test_latched_localization_producer_rollover_budget_is_soft(self):
        node_source = ast.get_source_segment(SOURCE, FUNCTIONS['queue_rollover_chat']) or ''
        self.assertIn('rollover_soft_limit_exceeded', node_source)
        self.assertIn('task_latched', node_source)
        self.assertIn('_is_latched_execution_task', node_source)

    def test_latched_producer_controller_failure_restarts_instead_of_done(self):
        node_source = ast.get_source_segment(SOURCE, FUNCTIONS['localization_process_lane_isolated']) or ''
        self.assertIn('lane_exception_restart', node_source)
        self.assertIn('raise ControllerRestartRequested', node_source)
        self.assertIn('active["phase"] = "WAIT_CHAT"', node_source)
        self.assertIn('active["terminal"] = None', node_source)
        self.assertIn('active["task_latched"] = True', node_source)

    def test_valid_producer_commit_releases_active_task_latch(self):
        node_source = ast.get_source_segment(SOURCE, FUNCTIONS['finalize_localization_producer_commit']) or ''
        self.assertIn('active["task_latched"] = False', node_source)
        self.assertIn('active["controller_stage"] = "DONE"', node_source)
        self.assertIn('last_material_progress_at', node_source)

    def test_retry_diagnostic_classifies_missing_composer_without_chat_dump(self):
        f, ns = load_function(
            'collect_retry_diagnostic',
            CONTROLLER_MODE='conversion',
            first_visible=AsyncMock(return_value=None),
            INPUT_SELECTORS=[],
            composer_diagnostics=AsyncMock(return_value=[{
                'tag':'DIV','role':'textbox','visible':False,'frame_url':'https://chatgpt.com/'
            }]),
            current_assistant_text=AsyncMock(return_value=''),
            RATE_LIMIT_PATTERNS=[r'too many requests'],
            CONVERSATION_LIMIT_PATTERNS=[r'conversation.{0,20}limit'],
            LIMIT_PATTERNS=[r'usage limit'],
        )
        page=SimpleNamespace(url='https://chatgpt.com/g/project/c/chat', title=AsyncMock(return_value='ChatGPT'))
        slot=SimpleNamespace(name='B')
        active=self.active()
        active.update(lane='DXVK', branch='vr-dxvk-r71-disasm', generic_retry_clicks=2, chat_rollovers=1)
        d=asyncio.run(f(page,slot,active,'Something went wrong. Retry',busy=False))
        self.assertEqual(d['classification'],'GENERIC_RETRY_COMPOSER_MISSING')
        self.assertFalse(d['composer_visible'])
        self.assertEqual(d['task_id'],'TASK-1')
        self.assertEqual(d['generic_retry_clicks'],2)
        self.assertIn('Retry',d['retry_surface'])
        self.assertNotIn('assistant_text',d)

    def test_retry_diagnostic_classifies_rate_limit(self):
        f, _ = load_function(
            'collect_retry_diagnostic',
            CONTROLLER_MODE='localization',
            first_visible=AsyncMock(return_value=object()),
            INPUT_SELECTORS=[],
            composer_diagnostics=AsyncMock(return_value=[]),
            current_assistant_text=AsyncMock(return_value=''),
            RATE_LIMIT_PATTERNS=[r'too many requests'],
            CONVERSATION_LIMIT_PATTERNS=[],
            LIMIT_PATTERNS=[],
        )
        page=SimpleNamespace(url='https://chatgpt.com/', title=AsyncMock(return_value='ChatGPT'))
        d=asyncio.run(f(page,SimpleNamespace(name='A'),self.active(),'Too many requests. Retry',busy=False))
        self.assertEqual(d['classification'],'RATE_LIMIT')
        self.assertTrue(d['composer_visible'])
        self.assertIsNotNone(d['rate_limit_match'])

    def test_retry_handler_persists_structured_diagnostic(self):
        diag={
            'at': datetime.now(timezone.utc).isoformat(),
            'classification':'GENERIC_RETRY_COMPOSER_MISSING',
            'composer_visible':False,
            'retry_surface':'Something went wrong. Retry',
        }
        persist=Mock()
        f, _ = load_function(
            'queue_handle_retry_surface',
            first_visible=AsyncMock(return_value=object()), RETRY_SELECTORS=[],
            detect_busy=AsyncMock(return_value=False),
            retry_surface_text=AsyncMock(return_value='Something went wrong. Retry'),
            collect_retry_diagnostic=AsyncMock(return_value=diag),
            persist_retry_diagnostic=persist,
            RATE_LIMIT_PATTERNS=[],
            current_assistant_text=AsyncMock(return_value=''),
            GENERIC_RETRY_ROLLOVER_CLICKS=2, RETRY_BUTTON_COOLDOWN_SECONDS=45,
            send_guard_reason=lambda *args:None, click_retry_generation=AsyncMock(return_value=True),
            note_successful_request=Mock(), save_registry=Mock(),
        )
        active=self.active(); slot=SimpleNamespace(name='A')
        self.assertTrue(asyncio.run(f(None,{},None,None,slot,active,{'active':active})))
        persist.assert_called_once_with(diag)
        self.assertEqual(active['last_retry_classification'],'GENERIC_RETRY_COMPOSER_MISSING')
        self.assertFalse(active['last_retry_composer_visible'])
        self.assertEqual(active['last_retry_recovery_action'],'CONTROLLED_RETRY_CLICK')

    def test_persistent_generic_retry_rolls_same_task_to_fresh_chat(self):
        rollover = AsyncMock(return_value=True)
        f, ns = load_function(
            'queue_handle_retry_surface',
            CONTROLLER_MODE='conversion',
            first_visible=AsyncMock(return_value=object()),
            RETRY_SELECTORS=[],
            detect_busy=AsyncMock(return_value=False),
            retry_surface_text=AsyncMock(return_value='Something went wrong. Retry'),
            RATE_LIMIT_PATTERNS=[],
            current_assistant_text=AsyncMock(return_value=''),
            GENERIC_RETRY_ROLLOVER_CLICKS=2,
            RETRY_BUTTON_COOLDOWN_SECONDS=45,
            rate_limit_active=lambda *args: False,
            send_guard_reason=lambda *args: None,
            click_retry_generation=AsyncMock(return_value=False),
            queue_rollover_chat=rollover,
            save_registry=Mock(),
        )
        active = self.active()
        active.update(
            lane='DXVK',
            branch='vr-dxvk-r71-disasm',
            generic_retry_clicks=2,
            generic_retry_cooldown_until=(datetime.now(timezone.utc)+timedelta(seconds=300)).isoformat(),
        )
        slot=SimpleNamespace(name='B')
        q={'active':active}
        self.assertTrue(asyncio.run(f(None,{},None,None,slot,active,q)))
        rollover.assert_awaited_once()
        self.assertEqual(active['task_id'], 'TASK-1')
        self.assertTrue(active['task_latched'])
        self.assertEqual(active['controller_stage'], 'WAIT_DURABLE_RESULT')
        self.assertEqual(active['generic_retry_clicks'], 0)
        self.assertNotIn('generic_retry_cooldown_until', active)

    def test_startup_migrates_persisted_active_task_latch_fields(self):
        node_source = ast.get_source_segment(SOURCE, FUNCTIONS['startup_reconcile_queue_state']) or ''
        self.assertIn('task["task_latched"] = True', node_source)
        self.assertIn('WAIT_DURABLE_RESULT', node_source)
        self.assertIn('WAIT_MATERIAL_COMMIT', node_source)
        self.assertIn('WAIT_QA_RESULT', node_source)
        self.assertIn('generic_retry_cooldown_until', node_source)

    def test_retry_surface_stable_response_preempts_generic_retry_cooldown(self):
        native = AsyncMock(return_value=True)
        f, ns = load_function(
            'queue_handle_retry_surface',
            first_visible=AsyncMock(return_value=object()),
            RETRY_SELECTORS=[],
            detect_busy=AsyncMock(return_value=False),
            retry_surface_text=AsyncMock(return_value='Retry'),
            RATE_LIMIT_PATTERNS=[],
            current_assistant_text=AsyncMock(return_value='상태 재구성 완료. 다음 단계 진행. RESULT_SHA=NOT_CREATED'),
            queue_handle_native_response=native,
            GENERIC_RETRY_ROLLOVER_CLICKS=2,
            GENERIC_RETRY_COOLDOWN_SECONDS=300,
            RETRY_BUTTON_COOLDOWN_SECONDS=45,
            rate_limit_active=lambda *args: False,
            send_guard_reason=lambda *args: None,
            click_retry_generation=AsyncMock(return_value=False),
            save_registry=Mock(),
        )
        active = self.active()
        text_value = '상태 재구성 완료. 다음 단계 진행. RESULT_SHA=NOT_CREATED'
        active['last_hash'] = ns['stable_hash'](text_value)
        active['last_hash_changed_at'] = (
            datetime.now(timezone.utc) - timedelta(seconds=60)
        ).isoformat()
        active['generic_retry_clicks'] = 2
        slot = SimpleNamespace(name='A')
        self.assertTrue(asyncio.run(f(None, {}, None, None, slot, active, {'active': active})))
        native.assert_awaited_once()
        self.assertNotIn('generic_retry_cooldown_until', active)

    def test_retry_surface_does_not_interrupt_busy_generation(self):
        f, ns=load_function('queue_handle_retry_surface',
            first_visible=AsyncMock(return_value=object()), RETRY_SELECTORS=[],
            detect_busy=AsyncMock(return_value=True), retry_surface_text=AsyncMock(return_value='Retry'),
            RATE_LIMIT_PATTERNS=[], last_assistant_text=AsyncMock(return_value='작업 불가'),
            queue_handle_native_response=AsyncMock(return_value=True),
            queue_handle_broker_response=AsyncMock(return_value=False),
            assistant_claims_github_tooling_absent=lambda _:True,
            assistant_claims_github_unavailable=lambda _:False,
            queue_send_github_recovery=AsyncMock(return_value=True))
        active=self.active()
        self.assertTrue(asyncio.run(f(None,{},None,None,None,active,{'active':active})))
        ns['queue_send_github_recovery'].assert_not_called()
        ns['last_assistant_text'].assert_not_called()

    def test_old_assistant_text_before_latest_user_is_not_current_response(self):
        self.assertTrue('current_assistant_text' in FUNCTIONS)
        f, ns=load_function('current_assistant_text')
        item=SimpleNamespace(get_attribute=AsyncMock(return_value='user'), inner_text=AsyncMock(return_value='new task'))
        loc=SimpleNamespace(count=AsyncMock(return_value=3), nth=Mock(return_value=item))
        page=SimpleNamespace(locator=Mock(return_value=loc))
        self.assertEqual(asyncio.run(f(page)), '')
        item.get_attribute.return_value='assistant'; item.inner_text.return_value='current result'
        self.assertEqual(asyncio.run(f(page)), 'current result')

    def test_migration_checks_durable_commit_before_sending(self):
        f, ns=load_function('queue_upgrade_native_context', native_plugin_instructions=lambda _: 'native',
                            github_find_task_commit=Mock(return_value={'sha':'b'*40}))
        active=self.active(); active['broker_mode']=True
        self.assertFalse(asyncio.run(f(None,{}, {'active':active},active)))
        ns['queue_send_same_chat_control_message'].assert_not_called()

    def test_generic_retry_works_when_current_generation_has_no_reply(self):
        f, ns=load_function('queue_handle_retry_surface',
            first_visible=AsyncMock(return_value=object()), RETRY_SELECTORS=[],
            detect_busy=AsyncMock(return_value=False), retry_surface_text=AsyncMock(return_value='Something went wrong. Retry'),
            RATE_LIMIT_PATTERNS=[], last_assistant_text=AsyncMock(return_value='old reply'),
            current_assistant_text=AsyncMock(return_value=''),
            queue_handle_native_response=AsyncMock(return_value=True),
            GENERIC_RETRY_ROLLOVER_CLICKS=2, RETRY_BUTTON_COOLDOWN_SECONDS=45,
            send_guard_reason=lambda *args:None, click_retry_generation=AsyncMock(return_value=True),
            note_successful_request=Mock(), save_registry=Mock())
        active=self.active(); active['last_hash']=ns['stable_hash']('old reply')
        active['last_hash_changed_at']=(datetime.now(timezone.utc)-timedelta(seconds=60)).isoformat()
        slot=SimpleNamespace(name='A')
        self.assertTrue(asyncio.run(f(None,{},None,None,slot,active,{'active':active})))
        self.assertEqual(ns['click_retry_generation'].call_count,1)
        ns['queue_handle_native_response'].assert_not_called()


if __name__ == '__main__':
    unittest.main()
