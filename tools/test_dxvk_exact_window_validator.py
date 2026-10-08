import unittest

from dxvk_exact_window_validator import validate_window


class TestDXVKExactWindowValidator(unittest.TestCase):
    def test_overlap_must_match(self):
        result = validate_window(
            bytes.fromhex("66 0f 54 1d 20 91 61 aa"),
            bytes.fromhex("66 0f 54 1d 20 91 61"),
            "0x182f7e",
            "0x182fbe",
        )
        self.assertFalse(result["semantic_promotion"])

    def test_overlap_mismatch_fails_closed(self):
        with self.assertRaises(ValueError):
            validate_window(
                bytes.fromhex("90 90"),
                bytes.fromhex("66 0f"),
                "0x1",
                "0x2",
            )


if __name__ == "__main__":
    unittest.main()
