import unittest

from dxvk_continuation_target_guard import validate_targets


class TestDXVKContinuationTargetGuard(unittest.TestCase):
    def test_target_inside_window(self):
        result = validate_targets(0x182f7e, 0x182fbe, [0x182f8a])
        self.assertFalse(result["semantic_promotion"])

    def test_target_outside_window_fails(self):
        with self.assertRaises(ValueError):
            validate_targets(0x182f7e, 0x182fbe, [0x190000])


if __name__ == "__main__":
    unittest.main()
