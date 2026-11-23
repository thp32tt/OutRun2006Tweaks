#!/usr/bin/env python3
"""Positive/negative ZIP, SHA and PE contract; synthetic binaries, not real game."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools/ferrari16"))
import private_test_package as pkg

SHA = "a" * 40

def make_pe(machine):
    data = bytearray(0x100)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3c, 0x80)
    data[0x80:0x84] = b"PE\x00\x00"
    struct.pack_into("<H", data, 0x84, machine)
    return bytes(data)

class PackageIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        root = self.path / "root"
        (root / "tools/ferrari16").mkdir(parents=True)
        for name in pkg.LAUNCHERS + pkg.SCRIPTS:
            (root / "tools/ferrari16" / name).write_text("fixture\n")
        for name in pkg.LICENSES:
            (root / name).write_text("license\n")
        self.dll = self.path / "dinput8.dll"
        self.host = self.path / "outrun-vr-host.exe"
        self.dll.write_bytes(make_pe(0x14c))
        self.host.write_bytes(make_pe(0x8664))
        self.zip_path = self.path / "qa.zip"
        pkg.build_package(root, self.dll, self.host, SHA, self.zip_path)

    def rewrite(self, change):
        with zipfile.ZipFile(self.zip_path) as original:
            entries = {name: original.read(name) for name in original.namelist()}
        change(entries)
        with zipfile.ZipFile(self.zip_path, "w") as archive:
            for name, data in entries.items():
                archive.writestr(name, data)

    def test_positive_source_arch_hashes(self):
        qa = pkg.verify_package(self.zip_path, SHA)
        self.assertEqual(qa["RuntimeValidation"], "UNTESTED")
        self.assertFalse(qa["Real16ModelAssetsValidated"])
        self.assertTrue(self.zip_path.with_suffix(".zip.sha256").exists())

    def test_negative_wrong_source_sha(self):
        with self.assertRaises(ValueError):
            pkg.verify_package(self.zip_path, "b" * 40)

    def test_negative_modified_dll_even_with_valid_zip_crc(self):
        self.rewrite(lambda entries: entries.__setitem__(
            "PAYLOAD/dinput8.dll", make_pe(0x14c) + b"tampered"))
        with self.assertRaisesRegex(ValueError, "SHA256"):
            pkg.verify_package(self.zip_path, SHA)

    def test_negative_missing_host(self):
        self.rewrite(lambda entries: entries.pop("PAYLOAD/outrun-vr-host.exe"))
        with self.assertRaisesRegex(ValueError, "unauthorized"):
            pkg.verify_package(self.zip_path, SHA)

    def test_negative_extra_private_model(self):
        self.rewrite(lambda entries: entries.__setitem__(
            "ExternalCars/car_id_05.ovc", b"not licensed for redistribution"))
        with self.assertRaisesRegex(ValueError, "unauthorized"):
            pkg.verify_package(self.zip_path, SHA)

    def test_negative_architectures(self):
        with self.assertRaisesRegex(ValueError, "x86"):
            pkg.assert_binaries({pkg.PAYLOAD[0]: make_pe(0x8664),
                                 pkg.PAYLOAD[1]: make_pe(0x8664)})
        with self.assertRaisesRegex(ValueError, "x64"):
            pkg.assert_binaries({pkg.PAYLOAD[0]: make_pe(0x14c),
                                 pkg.PAYLOAD[1]: make_pe(0x14c)})

    def test_negative_tampered_manifest_or_untested_claim(self):
        def change(entries):
            qa = json.loads(entries["QA.json"])
            qa["Quest3HardwarePass"] = True
            entries["QA.json"] = json.dumps(qa).encode()
        self.rewrite(change)
        with self.assertRaisesRegex(ValueError, "unsafe"):
            pkg.verify_package(self.zip_path, SHA)

    def test_negative_modified_launcher(self):
        self.rewrite(lambda entries: entries.__setitem__(
            f"LAUNCHERS/{pkg.LAUNCHERS[0]}", b"unverified launcher"))
        with self.assertRaisesRegex(ValueError, "SHA256"):
            pkg.verify_package(self.zip_path, SHA)

if __name__ == "__main__":
    unittest.main(verbosity=2)
