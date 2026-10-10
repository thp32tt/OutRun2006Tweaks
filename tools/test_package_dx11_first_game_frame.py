#!/usr/bin/env python3
"""Synthetic packaging negatives, not a live GPU test."""
import io
import json
import struct
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from package_dx11_first_game_frame import MARKER, construct, pack, verify


def fake_pe(machine, size, marker=b""):
    data = bytearray(size)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3c, 128)
    data[128:132] = b"PE\x00\x00"
    struct.pack_into("<H", data, 132, machine)
    data[512:512+len(marker)] = marker
    return bytes(data)


def must_fail(f, label):
    try:
        f()
    except (ValueError, KeyError):
        return
    raise AssertionError("unsafe package accepted: " + label)


def main():
    a = "a" * 40
    game = fake_pe(0x14c, 1000500, MARKER)
    host = fake_pe(0x8664, 12000)
    args = (game, host, b"PreferD3D9Ex=true", b"LOD", b"runner", a, a)
    payload = construct(*args)
    data = pack(payload)
    verify(data)
    must_fail(lambda: construct(host, game, *args[2:]), "reversed architectures")
    must_fail(lambda: construct(game.replace(MARKER, b"x"*len(MARKER)), *args[1:]), "marker absent")
    must_fail(lambda: construct(*args[:-1], "bad"), "invalid identity")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        content = {name:z.read(name) for name in z.namelist()}
    content["DX9EX_VARIANT.txt"] += b"tamper"
    result = io.BytesIO()
    with zipfile.ZipFile(result, "w") as z:
        for name, value in content.items():
            z.writestr(name, value)
    must_fail(lambda: verify(result.getvalue()), "tampered payload")
    assert json.loads(payload["BUILD_IDENTITY.json"])["runtime_validation"] == "UNTESTED"
    assert b"OUTRUN_DX11_FIRST_GAME_FRAME=1" in payload["RUN_DX11_FIRST_GAME_FRAME.cmd"]
    assert b'OUTRUN_DX11_FIRST_GAME_FRAME="' in payload["RUN_DX9EX_CONTROL.cmd"]
    print("DX11 first-game-frame packaging PE/SHA/tamper/opt-in tests: PASS (synthetic)")


if __name__ == "__main__":
    main()
