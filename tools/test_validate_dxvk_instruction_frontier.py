import unittest

from pathlib import Path
import importlib.util


spec = importlib.util.spec_from_file_location("frontier", "tools/validate_dxvk_instruction_frontier.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FrontierValidationTests(unittest.TestCase):
    def test_overlap_is_required(self):
        self.assertEqual([], module.validate_window(b"aa" + bytes.fromhex(module.DEFAULT_OVERLAP), 0, 9, module.DEFAULT_OVERLAP))

    def test_missing_overlap_fails_closed(self):
        self.assertIn("overlap_not_present", module.validate_window(b"aa", 0, 2, module.DEFAULT_OVERLAP))


if __name__ == "__main__":
    unittest.main()
