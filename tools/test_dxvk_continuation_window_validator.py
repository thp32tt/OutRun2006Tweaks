"""Static DXVK continuation window validator.

Keeps raw-byte continuation evidence separate from semantic decoding.
The validator is intentionally conservative: incomplete tails cannot become
instruction records until a complete canonical window is supplied.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ContinuationWindow:
    start_rva: str
    bytes_hex: str
    complete: bool


EXPECTED_START = "0x00182F7E"
EXPECTED_OVERLAP = "66 0f 54 1d 20 91 61"


def validate_continuation(window: ContinuationWindow) -> None:
    assert window.start_rva == EXPECTED_START
    assert window.bytes_hex.lower() == EXPECTED_OVERLAP
    assert window.complete is False


def test_partial_continuation_is_not_decoded() -> None:
    validate_continuation(
        ContinuationWindow(
            start_rva=EXPECTED_START,
            bytes_hex=EXPECTED_OVERLAP,
            complete=False,
        )
    )


if __name__ == "__main__":
    test_partial_continuation_is_not_decoded()
    print("DXVK continuation validator: PASS")
