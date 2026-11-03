from tools.validate_dxvk_instruction_window import validate_window


def test_overlap_window_is_checked():
    result = validate_window(bytes.fromhex("660f541d20916190"), "0x182f7e", "0x182f86", bytes.fromhex("660f541d209161"))
    assert result["overlap_verified"] is True
    assert result["semantic_promotion"] is False


def test_empty_window_is_rejected():
    try:
        validate_window(b"", "0x0", "0x0", None)
    except ValueError:
        return
    raise AssertionError("empty windows must fail closed")
