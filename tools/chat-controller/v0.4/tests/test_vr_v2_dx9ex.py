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

    def test_vr_compose_pins_v2_and_three_slots(self):
        compose = (ROOT / 'docker-compose.portainer-vr.yml').read_text()
        self.assertIn('dockerfile: Dockerfile.portainer-vr', compose)
        self.assertIn('CHAT_SLOTS: "3"', compose)
        self.assertIn('TASK_EVENT_MODEL: "v2"', compose)
        self.assertIn('PRODUCTION_COUNTER_MODE: "lane"', compose)
        dockerfile = (ROOT / 'Dockerfile.portainer-vr').read_text()
        self.assertIn('COPY src-vr-v2/controller.py.part*', dockerfile)
        self.assertIn('COPY conversion_dx9ex.md', dockerfile)


if __name__ == '__main__':
    unittest.main()
