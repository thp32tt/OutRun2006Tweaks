#!/usr/bin/env python3
"""DX11 00766 native OpenXR eye ACK replay and slot lifetime integration."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ring = (ROOT / "src/vr/d3d11/native_shared_eye_ring.cpp").read_text()
header = (ROOT / "src/vr/d3d11/native_shared_eye_ring.hpp").read_text()
source = (ROOT / "src/vr/d3d11/native_game_eye_pair_sources.hpp").read_text()
probe = (ROOT / "tools/dx11_native_transport_probe.cpp").read_text()

def linked(ring, header, source, probe):
    try:
        acquire = ring.split("bool NativeSharedEyeRing::try_acquire_slot(", 1)[1].split(
            "bool NativeSharedEyeRing::cancel_acquired_slot(", 1)[0]
        retire = ring.split("bool NativeSharedEyeRing::retire_acknowledged(", 1)[1].split(
            "SharedEyeSlotState NativeSharedEyeRing::slot_state(", 1)[0]
        bind = ring.split("bool NativeSharedEyeRing::bind_lifetime(", 1)[1].split(
            "void NativeSharedEyeRing::invalidate_lifetime(", 1)[0]
    except IndexError:
        return False
    return all((
        "frame_id_high_watermark_ = 0u;" in header,
        "next > highWatermark && next > sameLifetimeAck" in source,
        "OutRunVR::Core::TransportAckIdentityMatches(*ack, identity_)" in acquire,
        "native_game_eye_frame_id_admitted(" in acquire,
        0 <= acquire.find("native_game_eye_frame_id_admitted(") <
            acquire.find("if (slot.state == SharedEyeSlotState::Published)"),
        acquire.count("frame_id_high_watermark_ = native_game_eye_frame_high_watermark(") == 2,
        "frame_id_high_watermark_ = native_game_eye_frame_high_watermark(" in retire,
        "frame_id_high_watermark_ = 0u;" in bind,
        "retired frame ID cannot be replayed" in probe,
        "future cumulative ACK cannot retire a new eye pair" in probe,
        "cumulative ACK high watermark rejects old or already ACKed frame" in probe,
    ))

assert linked(ring, header, source, probe), "ring/frame/ACK source graph disconnected"
for needle in ("native_game_eye_frame_id_admitted(",
               "OutRunVR::Core::TransportAckIdentityMatches(*ack, identity_)",
               "frame_id_high_watermark_ = native_game_eye_frame_high_watermark("):
    mutated = ring.replace(needle, "/* dropped replay protection */")
    assert mutated != ring and not linked(mutated, header, source, probe)
assert not linked(ring, header, source.replace(
    "next > highWatermark && next > sameLifetimeAck", "true"), probe)

code = r"""
#include "native_game_eye_pair_sources.hpp"
#include <cassert>
using namespace outrun::vr::dx11;
constexpr bool valid() {
    return native_game_eye_frame_id_admitted(1, 0, 0) &&
           native_game_eye_frame_id_admitted(6, 5, 0) &&
           native_game_eye_frame_id_admitted(12, 9, 10) &&
           !native_game_eye_frame_id_admitted(0, 0, 0) &&
           !native_game_eye_frame_id_admitted(5, 5, 0) &&
           !native_game_eye_frame_id_admitted(4, 5, 0) &&
           !native_game_eye_frame_id_admitted(6, 5, 6) &&
           !native_game_eye_frame_id_admitted(9, 5, 10) &&
           native_game_eye_frame_high_watermark(5, 10) == 10 &&
           native_game_eye_frame_high_watermark(12, 10) == 12;
}
static_assert(valid(), "cumulative ACK must not retire a reused native eye");
int main() { assert(valid()); }
"""
compiler = shutil.which("g++") or shutil.which("clang++")
assert compiler, "DX11 Fast requires a portable C++ compiler"
with TemporaryDirectory(prefix="dx11-00766-") as tmp:
    src = Path(tmp) / "test.cpp"
    out = Path(tmp) / "test"
    src.write_text(code)
    subprocess.run([compiler, "-std=c++17", "-O2", "-Wall", "-Wextra",
                    "-Werror", "-pedantic", "-I", str(ROOT / "src/vr/d3d11"),
                    str(src), "-o", str(out)], check=True)
    subprocess.run([str(out)], check=True)
print("PASS: 00766 native eye ACK replay/slot continuity; Quest3 UNTESTED")
