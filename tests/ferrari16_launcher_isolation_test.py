#!/usr/bin/env python3
"""Ferrari16 isolated launch gates: actual scripts and negative fixtures."""
from pathlib import Path
import unittest
import os
import re
import subprocess
import tempfile

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

def choice_dispatch(source):
    """Extract the actual launcher's post-CHOICE branch, not a copied policy."""
    lines = source.splitlines()
    start = lines.index('choice /C 12 /N /M "Select 1 or 2: "')
    end = lines.index(":MODE_2D")
    return [line.strip() for line in lines[start + 1:end]
            if line.strip() and not line.strip().lower().startswith("rem ")]


def simulate_choice(source, status):
    """Model the exact CMD IF ERRORLEVEL >= dispatch; reject unknown syntax."""
    for line in choice_dispatch(source):
        match = re.fullmatch(r"if errorlevel (\d+) (.+)", line, re.I)
        if match:
            if status < int(match[1]):
                continue
            line = match[2]
        if line in ("goto MODE_VR", "goto MODE_2D", "exit /b 89"):
            return line
        raise AssertionError("unknown dispatch: " + line)
    raise AssertionError("fell through without explicit launch selection")


def probe_flags(source, mode, inherited):
    """Read actual SET statements before the game start in the chosen mode."""
    block = source.split(":" + mode + "\n", 1)[1]
    block = block.split('start "" "%~dp0OR2006C2C.exe"', 1)[0]
    flags = dict(inherited)
    for key, value in re.findall(
        r'^set "(OUTRUN_VR_EXTERNAL_(?:FIXED_FUNCTION|PBR_STEREO)_TEST)=([01])"$',
        block, re.M):
        flags[key] = int(value)
    return (flags["OUTRUN_VR_EXTERNAL_FIXED_FUNCTION_TEST"],
            flags["OUTRUN_VR_EXTERNAL_PBR_STEREO_TEST"])


class LauncherIsolationTest(unittest.TestCase):
    def test_choice_routes_and_negative(self):
        for name in LAUNCHERS:
            source = (ROOT / name).read_text(encoding="utf-8")
            for code, expected in ((1, "goto MODE_2D"), (2, "goto MODE_VR"),
                                   (0, "exit /b 89"), (3, "exit /b 89"),
                                   (255, "exit /b 89"), (9009, "exit /b 89")):
                with self.subTest(launcher=name, code=code):
                    self.assertEqual(simulate_choice(source, code), expected)
            old = source.replace("if errorlevel 3 exit /b 89\n", "").replace(
                "if errorlevel 1 goto MODE_2D\nexit /b 89", "goto MODE_2D")
            self.assertEqual(simulate_choice(old, 0), "goto MODE_2D")
            self.assertEqual(simulate_choice(old, 255), "goto MODE_VR")

    @unittest.skipUnless(os.name == "nt", "actual CMD dispatch requires Windows")
    def test_native_cmd_choice_dispatch(self):
        # Execute the real dispatch lines with injected CHOICE return codes.
        # No game/host launch, interactive prompt or test installation needed.
        with tempfile.TemporaryDirectory() as temp:
            fixture = Path(temp) / "choice.cmd"
            for name in LAUNCHERS:
                source = (ROOT / name).read_text(encoding="utf-8")
                body = "\n".join(choice_dispatch(source))
                for code, expected in ((0, 89), (1, 41), (2, 42),
                                       (3, 89), (255, 89), (9009, 89)):
                    fixture.write_text(
                        "@echo off\ncall :inject\n" + body +
                        "\n:MODE_2D\nexit /b 41\n:MODE_VR\nexit /b 42\n" +
                        ":inject\nexit /b " + str(code) + "\n",
                        encoding="ascii")
                    with self.subTest(launcher=name, code=code):
                        result = subprocess.run(
                            ["cmd.exe", "/d", "/c", str(fixture)],
                            capture_output=True, timeout=10)
                        self.assertEqual(result.returncode, expected)

    def test_probe_modes_ignore_inherited_environment(self):
        fixed = "OUTRUN_VR_EXTERNAL_FIXED_FUNCTION_TEST"
        pbr = "OUTRUN_VR_EXTERNAL_PBR_STEREO_TEST"
        expected = ((1, 0), (1, 0), (0, 0), (0, 1))
        for name, vr_expected in zip(LAUNCHERS, expected):
            source = (ROOT / name).read_text(encoding="utf-8")
            for f in (0, 1):
                for p in (0, 1):
                    inherited = {fixed: f, pbr: p}
                    with self.subTest(launcher=name, inherited=inherited):
                        self.assertEqual(probe_flags(source, "MODE_2D", inherited),
                                         (0, 0))
                        self.assertEqual(probe_flags(source, "MODE_VR", inherited),
                                         vr_expected)
            # A removed explicit PBR reset must reproduce the inherited leak.
            if vr_expected[1] == 0:
                broken = source.replace('set "' + pbr + '=0"\n', "")
                self.assertNotEqual(probe_flags(broken, "MODE_VR",
                                               {fixed: 1, pbr: 1}), vr_expected)

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
