from dxvk_decode_window import decode_complete_records, make_window, overlap_prefix


def test_overlap_bytes_are_preserved():
    window = make_window(0x182F7E, "66 0f 54 1d 20 91 61")
    assert overlap_prefix(window, "66 0f 54 1d")
    assert window.end_rva == 0x182F85


def test_window_does_not_claim_outside_bytes():
    window = make_window(0x1000, "90 90")
    assert window.contains(0x1000)
    assert not window.contains(0x1002)


def test_decoder_requires_exact_external_boundaries():
    window = make_window(0x182F7E, "66 0f 54 1d 20 91 61")
    records = decode_complete_records(window, [(0x182F7E, 4)])
    assert records[0].bytes_hex == "66 0f 54 1d"
