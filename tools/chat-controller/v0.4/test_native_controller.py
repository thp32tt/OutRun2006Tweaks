"""Behavioral checks without Chrome, credentials, network or production state writes."""
import ast
import asyncio
import hashlib
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
    ns = dict(re=re, datetime=datetime, timedelta=timedelta, TZ=timezone.utc,
              GITHUB_BROKER_ENABLED=False, NATIVE_PLUGIN_PROTOCOL_VERSION=2,
              GITHUB_ASSISTANT_RECOVERY_MAX=2, GITHUB_TOOLING_RETRY_COOLDOWN_SECONDS=300,
              QUEUE_STABLE_SECONDS=30, QUEUE_RESULT_GRACE_SECONDS=180,
              _parse_iso=lambda x: datetime.fromisoformat(x) if x else None,
              stable_hash=lambda x: hashlib.sha256(x.encode()).hexdigest(),
              runtime={}, write_runtime=Mock(), save_queue_state=Mock(),
              github_branch_head=Mock(return_value='a'*40),
              github_find_task_commit=Mock(return_value=None), CONTROLLER_MODE='conversion',
              github_transient_retry_pending=lambda: False,
              native_plugin_instructions=lambda active: 'ALL_TOOLS tool search TOOL_NOT_EXPOSED 404 TARGET_BRANCH',
              queue_send_same_chat_control_message=AsyncMock(return_value=True))
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
            self.assertLessEqual(len(prompt.encode()), 650)

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
        self.assertGreaterEqual(SOURCE.count('await localization_handle_producer_commit('), 4)
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
