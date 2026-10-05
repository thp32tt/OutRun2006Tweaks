"""Regression coverage for the isolated VR Controller v2 DX11/DXVK/DX9Ex queue."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ''.join(p.read_text() for p in sorted((ROOT / 'src-vr-v2').glob('controller.py.part*')))


def load_queue_target():
    tree = ast.parse(SOURCE)
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'queue_target_for_slot')
    module = ast.Module(body=[fn], type_ignores=[])
    ns = {'CONTROLLER_MODE': 'conversion'}
    exec(compile(module, '<queue-target>', 'exec'), ns)
    return ns['queue_target_for_slot']


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

    def test_dx9ex_structural_refactor_is_priority_zero(self):
        prompt = (ROOT / 'conversion_dx9ex.md').read_text()
        self.assertIn('0순위는 현재 진행 중인 DX9Ex 구조 개선/리팩터링 작업이다', prompt)
        self.assertIn('docs/VR_REFACTOR_STATE.json', prompt)
        self.assertIn('R33 final dispatcher', prompt)
        self.assertIn('구조 개선이 현재 Git 상태에서 명시적으로 완료되었거나', prompt)

    def test_conversion_lanes_are_independent(self):
        self.assertIn('async def conversion_parallel_cycle', SOURCE)
        self.assertIn('async def conversion_process_lane', SOURCE)
        self.assertIn('async def conversion_send_lane_task', SOURCE)
        self.assertIn('CONTROLLER_MODE == "conversion" and CONVERSION_PARALLEL', SOURCE)
        self.assertIn('q.setdefault("active_by_lane", {})', SOURCE)
        self.assertIn('conversion_parallel_schema_version', SOURCE)
        self.assertIn('stale pre-independent-conversion active_by_lane state', SOURCE)
        self.assertIn('for lane_key in ("C", "A", "B")', SOURCE)

    def test_priority_policy_defers_dxvk(self):
        self.assertIn('high_priority = ("C", "A")', SOURCE)
        self.assertIn('CONVERSION_DXVK_DEFERRED', SOURCE)
        self.assertIn('high_active == 0', SOURCE)
        self.assertIn('Priority C(DX9Ex refactor) > A(DX11) > B(DXVK deferred)', SOURCE)

    def test_rollover_throttle_policy(self):
        self.assertIn('CONVERSATION_ROLLOVER_MIN_SECONDS', SOURCE)
        self.assertIn('conversation_rollover_cooldown', SOURCE)
        self.assertIn('hard_length_limit', SOURCE)

    def test_vr_compose_pins_v2_and_three_slots(self):
        compose = (ROOT / 'docker-compose.portainer-vr.yml').read_text()
        self.assertIn('dockerfile: Dockerfile.portainer-vr', compose)
        self.assertIn('CHAT_SLOTS: "3"', compose)
        self.assertIn('CONVERSION_PARALLEL: "true"', compose)
        self.assertIn('CONVERSION_ACTIVE_LIMIT: "2"', compose)
        self.assertIn('CONVERSION_DXVK_DEFERRED: "true"', compose)
        self.assertIn('QUEUE_RESULT_GRACE_SECONDS: "600"', compose)
        self.assertIn('CONVERSATION_ROLLOVER_MIN_SECONDS: "900"', compose)
        self.assertIn('MAX_CHAT_ROLLOVERS_PER_TASK: "3"', compose)
        self.assertIn('TASK_EVENT_MODEL: "v2"', compose)
        self.assertIn('PRODUCTION_COUNTER_MODE: "lane"', compose)
        dockerfile = (ROOT / 'Dockerfile.portainer-vr').read_text()
        self.assertIn('COPY src-vr-v2/controller.py.part*', dockerfile)
        self.assertIn('COPY conversion_dx9ex.md', dockerfile)


if __name__ == '__main__':
    unittest.main()
