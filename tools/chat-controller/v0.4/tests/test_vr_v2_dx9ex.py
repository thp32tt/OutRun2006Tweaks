"""Regression coverage for the isolated VR Controller v2 DX11/DXVK/DX9Ex queue."""
import ast
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ''.join(p.read_text() for p in sorted((ROOT / 'src-vr-v2').glob('controller.py.part*')))


def load_queue_target():
    tree = ast.parse(SOURCE)
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'queue_target_for_slot')
    module = ast.Module(body=[fn], type_ignores=[])
    ns = {'CONTROLLER_MODE': 'conversion'}
    exec(compile(module, '<queue-target>', 'exec'), ns)
    return ns['queue_target_for_slot']



def load_dispatch_plan():
    tree = ast.parse(SOURCE)
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'conversion_dispatch_plan')
    ns = {}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), '<dispatch-plan>', 'exec'), ns)
    return ns['conversion_dispatch_plan']


def load_liveness_helpers():
    tree = ast.parse(SOURCE)
    names = {'rollover_has_confirmed_ui_failure', 'hold_unconfirmed_chat'}
    fns = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in fns} == names
    module = ast.Module(body=fns, type_ignores=[])
    ns = {
        'datetime': datetime,
        'TZ': timezone.utc,
        'save_queue_state': Mock(),
        'write_runtime': Mock(),
    }
    exec(compile(module, '<liveness-guard>', 'exec'), ns)
    return ns


class VRV2DX9ExTests(unittest.TestCase):
    def test_source_compiles_and_keeps_event_model(self):
        compile(SOURCE, 'controller-vr-v2.py', 'exec')
        self.assertIn('TASK_EVENT_MODEL', SOURCE)
        self.assertIn('PRODUCTION_COUNTER_MODE', SOURCE)
        self.assertIn('production_id', SOURCE)
        self.assertIn('event_id', SOURCE)
        self.assertIn('conversation_rollover', SOURCE)

    def test_three_conversion_targets(self):
        target = load_queue_target()
        self.assertEqual(target('A'), {
            'lane': 'DX11', 'branch': 'vr-dx11-native-r71', 'workflow': 'Backend Conversion Gate'})
        self.assertEqual(target('B'), {
            'lane': 'DXVK', 'branch': 'vr-dxvk-r71-disasm', 'workflow': 'Backend Conversion Gate'})
        self.assertEqual(target('C'), {
            'lane': 'DX9EX', 'branch': 'vr-d3d9ex-focus', 'workflow': 'DX9Ex Active Validation'})

    def test_dx9ex_prompt_and_slot_resize_are_wired(self):
        self.assertIn('"C": "conversion_dx9ex.md"', SOURCE)
        self.assertIn('resized chat slots from %s to %s while preserving state', SOURCE)
        self.assertTrue((ROOT / 'conversion_dx9ex.md').stat().st_size > 0)

    def test_dx9ex_is_opt_in_maintenance_only(self):
        prompt = (ROOT / 'conversion_dx9ex.md').read_text()
        self.assertIn('보호된 DX9Ex 기준 유지보수 전용', prompt)
        self.assertIn('NEED_HMD_TEST', prompt)
        self.assertNotIn('0순위는 현재 진행 중인 DX9Ex 구조 개선/리팩터링 작업이다', prompt)

    def test_conversion_lanes_are_independent(self):
        self.assertIn('async def conversion_parallel_cycle', SOURCE)
        self.assertIn('async def conversion_process_lane', SOURCE)
        self.assertIn('async def conversion_send_lane_task', SOURCE)
        self.assertIn('CONTROLLER_MODE == "conversion" and CONVERSION_PARALLEL', SOURCE)
        self.assertIn('q.setdefault("active_by_lane", {})', SOURCE)
        self.assertIn('conversion_parallel_schema_version', SOURCE)
        self.assertIn('stale pre-independent-conversion active_by_lane state', SOURCE)
        self.assertIn('for lane_key in ("A", "B", "C")', SOURCE)

    def test_dx11_dxvk_primary_dx9ex_opt_in_and_capacity_safe(self):
        plan = load_dispatch_plan()
        self.assertEqual(plan({}, 2, True, True, False), ('A', 'B'))
        self.assertEqual(plan({}, 2, True, True, True), ('A', 'B'))
        self.assertEqual(plan({'A': {'phase': 'WAIT_ACTIONS'}}, 2, True, True, True), ('B',))
        self.assertEqual(plan({'C': {'phase': 'WAIT_CHAT'}}, 2, True, True, True), ('A',))
        self.assertEqual(plan({'A': {'phase': 'WAIT_CHAT'}, 'C': {'phase': 'WAIT_ACTIONS'}}, 2, True, True, True), ())
        self.assertEqual(plan({'A': {'phase': 'DONE'}}, 2, True, True, False), ('B',))
        self.assertEqual(plan({'A': {'phase': 'HOLD_OWNER_UNCERTAIN'}}, 2, True, True, False), ('B',))
        self.assertEqual(plan({}, 1, False, False, True), ('C',))
        self.assertEqual(plan({}, 0, True, True, True), ())
        self.assertIn('for lane_key in conversion_dispatch_plan(', SOURCE)
        self.assertNotIn('CONVERSION_DXVK_DEFERRED', SOURCE)

    def test_single_lane_policy_freezes_non_dx9ex(self):
        self.assertIn('CONVERSION_ONLY_SLOT', SOURCE)
        self.assertIn('frozen_lane_tasks', SOURCE)
        self.assertIn('conversion_single_lane_running', SOURCE)
        self.assertIn('await conversion_send_lane_task(context, pages, q, CONVERSION_ONLY_SLOT)', SOURCE)

    def test_preventive_recycle_policy(self):
        self.assertIn('RECYCLE_ENABLED', SOURCE)
        self.assertIn('RECYCLE_INTERVAL_MINUTES', SOURCE)
        self.assertIn('RECYCLE_MEMORY_PERCENT', SOURCE)
        self.assertIn('RECYCLE_MIN_IDLE_SECONDS', SOURCE)
        self.assertIn('RECYCLE_MIN_NEXT_SLOT_SECONDS', SOURCE)
        self.assertIn('async def maybe_request_controller_recycle', SOURCE)
        self.assertIn('async def recycle_block_reason', SOURCE)
        self.assertIn('def fatal_browser_disconnect', SOURCE)
        self.assertIn('raise SystemExit(75)', SOURCE)
        self.assertIn('browser_fatal_disconnect', SOURCE)

    def test_failed_gate_repair_is_not_dropped_as_stale(self):
        self.assertIn('repair_send = trigger.startswith("retry-send:")', SOURCE)
        self.assertIn('and not repair_send', SOURCE)
        self.assertIn('A failed GitHub validation needs a repair prompt', SOURCE)
        self.assertIn('page = await replace_with_fresh_slot_page(context, pages, slot)', SOURCE)
        self.assertIn('repair fresh-chat login required', SOURCE)

    def test_exact_sha_actions_lookup_recovers_from_stale_bound_run(self):
        self.assertIn('bound = github_action_run_by_id(int(run_id), sha, workflow_name)', SOURCE)
        self.assertIn('if bound is not None:', SOURCE)
        self.assertIn('falling back to exact-SHA discovery', SOURCE)
        self.assertIn('{"head_sha": sha, "per_page": 100}', SOURCE)
        self.assertIn('exact_matches', SOURCE)
        self.assertIn('{"branch": branch, "per_page": 100}', SOURCE)
        self.assertNotIn('{"branch": branch, "per_page": 30}', SOURCE)

    def test_rollover_throttle_policy(self):
        self.assertIn('CONVERSATION_ROLLOVER_MIN_SECONDS', SOURCE)
        self.assertIn('conversation_rollover_cooldown', SOURCE)
        self.assertIn('hard_length_limit', SOURCE)
        self.assertIn('rollover_anchor = last_rollover or _parse_iso(active.get("sent_at"))', SOURCE)
        self.assertIn('github_stale_event_guard', SOURCE)
        self.assertIn('status="stale_event_drop"', SOURCE)
        self.assertIn('terminal"] = "STALE_DROPPED"', SOURCE)
        self.assertIn('completed_tasks_in_chat', SOURCE)
        self.assertIn('CHAT_ROTATE_COMPLETED_TASKS', SOURCE)

    def test_rollover_requires_confirmed_ui_failure(self):
        policy = load_liveness_helpers()['rollover_has_confirmed_ui_failure']
        for reason in (
            'No assistant response was detected before grace period',
            'Chat response stabilized but there is no [AUTO:TASK_ID] commit',
            'Active conversion lane chat URL is missing or outside project',
            '60 minutes have passed',
            'Failed to observe GitHub changes',
        ):
            with self.subTest(reason=reason):
                self.assertFalse(policy(reason))
        self.assertTrue(policy('ChatGPT reported that conversation reached its length limit.'))
        self.assertTrue(policy('Retry persisted after one recovery attempt'))
        self.assertFalse(policy(''))

    def test_uncertain_chat_retains_task_and_does_not_fake_progress(self):
        ns = load_liveness_helpers()
        active = {'task_id': 'CONVERSION-DX11-00454', 'phase': 'WAIT_CHAT',
                  'attempt': 1, 'chat_rollovers': 0}
        queue = {'active_by_lane': {'A': active}}
        hold = ns['hold_unconfirmed_chat']
        hold(queue, active, 'No reply detected')
        self.assertEqual(active['phase'], 'WAIT_CHAT')
        self.assertEqual(active['attempt'], 1)
        self.assertEqual(active['chat_rollovers'], 0)
        self.assertEqual(active['chat_liveness'], 'STALE_UNCONFIRMED')
        self.assertIn('liveness_first_uncertain_at', active)
        ns['save_queue_state'].assert_called_once_with(queue)
        ns['write_runtime'].assert_called_once()
        stamp = active['liveness_first_uncertain_at']
        hold(queue, active, 'No reply detected')
        self.assertEqual(active['liveness_first_uncertain_at'], stamp)
        ns['save_queue_state'].assert_called_once_with(queue)
        hold(queue, active, 'Stable interim text, no commit')
        self.assertEqual(ns['save_queue_state'].call_count, 2)
        self.assertEqual(active['attempt'], 1)

    def test_serial_and_parallel_chat_grace_fail_closed(self):
        tree = ast.parse(SOURCE)
        for fn_name in ('queue_cycle', 'conversion_process_lane'):
            node = next(n for n in tree.body
                        if isinstance(n, ast.AsyncFunctionDef) and n.name == fn_name)
            body = ast.get_source_segment(SOURCE, node)
            with self.subTest(function=fn_name):
                self.assertGreaterEqual(body.count('hold_unconfirmed_chat('), 2)
                self.assertIn('QUEUE_RESULT_GRACE_SECONDS', body)
                self.assertNotIn('No assistant response was detected before', body)
                self.assertNotIn('Chat response stabilized but no durable commit', body)
        rollover = next(n for n in tree.body
                        if isinstance(n, ast.AsyncFunctionDef) and n.name == 'queue_rollover_chat')
        body = ast.get_source_segment(SOURCE, rollover)
        self.assertIn('if not rollover_has_confirmed_ui_failure(reason):', body)
        self.assertIn('status="conversation_rollover_held"', body)

    def test_c6_terminal_verdict_guards_release_and_sha(self):
        tree = ast.parse(SOURCE)
        fn = next(n for n in tree.body
                  if isinstance(n, ast.FunctionDef) and n.name == 'conversion_terminal_verdict')
        ns = {}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), '<terminal-verdict>', 'exec'), ns)
        verdict = ns['conversion_terminal_verdict']
        sha = 'a' * 40
        active = {'task_id': 'CONVERSION-DX11-00454', 'branch': 'vr-dx11-native-r71'}
        run = {'head_sha': sha, 'status': 'completed', 'conclusion': 'success'}
        record = {'task_id': active['task_id'], 'target_branch': active['branch'],
                  'status': 'COMPLETE', 'checkpoint': 'C6_STATE',
                  'automation_validation': 'PASS', 'validation_bearing_result_sha': sha}
        self.assertEqual(verdict(record, active, run), (True, 'C6_EXACT_SHA_VERIFIED'))
        uncompleted = dict(record, status='IN_PROGRESS')
        self.assertEqual(verdict(uncompleted, active, run)[1], 'C6_NOT_COMPLETE')
        failed = dict(record, automation_validation='PENDING')
        self.assertEqual(verdict(failed, active, run)[1], 'AUTOMATION_VALIDATION_NOT_PASS')
        mismatch = dict(record, validation_bearing_result_sha='b' * 40)
        self.assertEqual(verdict(mismatch, active, run)[1], 'EXACT_SHA_MISMATCH')
        self.assertEqual(verdict(None, active, run)[1], 'RUN_RECORD_NOT_FOUND')
        dxvk = dict(record, status='COMPLETE', checkpoint='C6_STATE')
        dxvk.pop('automation_validation')
        dxvk['validation'] = {'automation_validation': 'PASS'}
        self.assertTrue(verdict(dxvk, active, run)[0])
        dx9 = dict(record, status='COMPLETE_BUILD_VERIFIED', controller_terminal=True)
        dx9.pop('checkpoint')
        self.assertTrue(verdict(dx9, active, run)[0])

    def test_conversion_success_waits_for_terminal_c6(self):
        tree = ast.parse(SOURCE)
        fn = next(n for n in tree.body
                  if isinstance(n, ast.AsyncFunctionDef) and n.name == 'conversion_process_lane')
        body = ast.get_source_segment(SOURCE, fn)
        self.assertIn('verified, reason = conversion_terminal_verdict(record, active, run)', body)
        self.assertIn('status="conversion_wait_c6"', body)
        self.assertIn('if not verified:', body)
        self.assertIn('active["terminal_verification"] = reason', body)

    def test_vr_compose_pins_v2_and_three_slots(self):
        compose = (ROOT / 'docker-compose.portainer-vr.yml').read_text()
        self.assertIn('dockerfile: Dockerfile.portainer-vr', compose)
        self.assertIn('CHAT_SLOTS: "3"', compose)
        self.assertIn('RECYCLE_ENABLED: "true"', compose)
        self.assertIn('RECYCLE_INTERVAL_MINUTES: "180"', compose)
        self.assertIn('RECYCLE_MEMORY_PERCENT: "70"', compose)
        self.assertIn('RECYCLE_CHECK_SECONDS: "30"', compose)
        self.assertIn('RECYCLE_MIN_IDLE_SECONDS: "300"', compose)
        self.assertIn('RECYCLE_MIN_NEXT_SLOT_SECONDS: "120"', compose)
        self.assertIn('PROFILE_CACHE_PRUNE_ON_START: "true"', compose)
        self.assertIn('mem_limit: 4g', compose)
        self.assertIn('CONVERSION_PARALLEL: "true"', compose)
        self.assertIn('CONVERSION_ACTIVE_LIMIT: "2"', compose)
        self.assertIn('CONVERSION_DX11_ENABLED: "true"', compose)
        self.assertIn('CONVERSION_DXVK_ENABLED: "true"', compose)
        self.assertIn('CONVERSION_DX9EX_ENABLED: "false"', compose)
        self.assertIn('CONVERSION_ONLY_SLOT: ""', compose)
        self.assertNotIn("CONVERSION_DXVK_DEFERRED", compose)
        self.assertIn('QUEUE_RESULT_GRACE_SECONDS: "600"', compose)
        self.assertIn('QUEUE_NEXT_TASK_DELAY_SECONDS: "180"', compose)
        self.assertIn("실기 HMD/게임 화면 테스트가 없다는 이유로", SOURCE)
        self.assertIn("1000/5000회 반복", SOURCE)
        self.assertIn("실기 테스트가 필요한 항목은", (ROOT / "conversion_dx11.md").read_text())
        self.assertIn('CONVERSATION_ROLLOVER_MIN_SECONDS: "3600"', compose)
        self.assertIn('MAX_CHAT_ROLLOVERS_PER_TASK: "1"', compose)
        self.assertIn('CHAT_ROTATE_COMPLETED_TASKS: "5"', compose)
        self.assertIn('TASK_EVENT_MODEL: "v2"', compose)
        self.assertIn('PRODUCTION_COUNTER_MODE: "lane"', compose)
        dockerfile = (ROOT / 'Dockerfile.portainer-vr').read_text()
        self.assertIn('COPY src-vr-v2/controller.py.part*', dockerfile)
        self.assertIn('COPY entrypoint.vr.sh /opt/outrun/entrypoint.sh', dockerfile)
        self.assertIn('COPY conversion_dx9ex.md', dockerfile)
        entrypoint = (ROOT / 'entrypoint.vr.sh').read_text()
        self.assertIn('PROFILE_CACHE_PRUNE_ON_START', entrypoint)
        self.assertIn('Chrome DevTools lost after controller attach; recycling container', entrypoint)
        self.assertIn('Default/Service Worker/CacheStorage', entrypoint)
        self.assertNotIn('Default/Cookies', entrypoint)
        self.assertNotIn('Default/Local Storage', entrypoint)
        self.assertNotIn('Default/IndexedDB', entrypoint)


if __name__ == '__main__':
    unittest.main()
