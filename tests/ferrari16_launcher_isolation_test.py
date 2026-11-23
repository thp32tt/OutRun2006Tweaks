#!/usr/bin/env python3
"""Ferrari16 isolated launch gates: actual scripts and negative fixtures."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "tools/ferrari16"
LAUNCHERS = (
    "RUN-FERRARI16-V003-ALL-CARS.cmd",
    "RUN-FERRARI16-V003-ALL-CARS-TRACE.cmd",
    "RUN-FERRARI16-V003-MODEL-OFF.cmd",
    "RUN-FERRARI16-V003-PBR-TRACE.cmd",
)
MARKER = 'if not exist "%~dp0.ferrari16-isolated.json"'
EXPECTED = {
    "RUN-FERRARI16-V003-ALL-CARS.cmd": "-VR.ExternalFerrariTest=true",
    "RUN-FERRARI16-V003-ALL-CARS-TRACE.cmd": "-VR.ExternalFerrariTest=true",
    "RUN-FERRARI16-V003-MODEL-OFF.cmd": "-VR.ExternalFerrariTest=false",
    "RUN-FERRARI16-V003-PBR-TRACE.cmd": "OUTRUN_VR_EXTERNAL_PBR_STEREO_TEST=1",
}

def is_isolated_launcher(source):
    low = source.lower()
    marker_at = low.find(MARKER.lower())
    launch_at = low.find('start "" "%~dp0or2006c2c.exe"')
    return (marker_at >= 0 and launch_at > marker_at
            and 'taskkill /im outrun-vr-host.exe' not in low
            and low.count('tasklist /fi "imagename eq outrun-vr-host.exe"') == 2
            and low.count("if not errorlevel 1 (") >= 2
            and 'exit /b 87' in low and 'exit /b 88' in low)

class LauncherIsolationTest(unittest.TestCase):
    def test_all_real_launchers_positive(self):
        for name in LAUNCHERS:
            with self.subTest(launcher=name):
                source = (ROOT / name).read_text(encoding="utf-8")
                self.assertTrue(is_isolated_launcher(source))
                self.assertIn(EXPECTED[name], source)
                self.assertIn("-VR.PreferD3D9Ex=true", source)
                self.assertIn("-VR.DirectGpuOnly=true", source)

    def test_negative_global_host_kill(self):
        source = (ROOT / LAUNCHERS[0]).read_text(encoding="utf-8")
        self.assertFalse(is_isolated_launcher(source + "\ntaskkill /IM outrun-vr-host.exe /F"))

    def test_negative_no_test_marker(self):
        source = (ROOT / LAUNCHERS[0]).read_text(encoding="utf-8")
        self.assertFalse(is_isolated_launcher(source.replace(MARKER, "rem marker removed")))

    def test_negative_no_host_conflict_guard(self):
        source = (ROOT / LAUNCHERS[0]).read_text(encoding="utf-8")
        self.assertFalse(is_isolated_launcher(source.replace(
            'tasklist /FI "IMAGENAME eq outrun-vr-host.exe"', 'echo removed')))

if __name__ == "__main__":
    unittest.main(verbosity=2)
