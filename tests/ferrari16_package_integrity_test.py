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

def make_pe(machine, is_dll=None):
    if is_dll is None:
        is_dll = machine == 0x14c
    offset = 0x80
    opt_size = 0xe0 if machine == 0x14c else 0xf0
    opt = offset + 24
    data = bytearray(0x400)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3c, offset)
    data[offset:offset + 4] = b"PE\x00\x00"
    struct.pack_into("<HHIIIHH", data, offset + 4, machine, 1, 0, 0, 0,
                     opt_size, 0x0002 | (0x2000 if is_dll else 0))
    struct.pack_into("<H", data, opt, 0x10b if machine == 0x14c else 0x20b)
    struct.pack_into("<I", data, opt + 16, 0x1000)
    struct.pack_into("<II", data, opt + 56, 0x2000, 0x200)
    struct.pack_into("<I", data, opt + (92 if machine == 0x14c else 108), 16)
    table = opt + opt_size
    data[table:table + 8] = b".text\x00\x00\x00"
    struct.pack_into("<IIII", data, table + 8, 0x100, 0x1000, 0x200, 0x200)
    struct.pack_into("<I", data, table + 36, 0x60000020)
    data[0x200] = 0xc3
    return bytes(data)


def make_two_section_pe(machine, overlap=None):
    data = bytearray(make_pe(machine))
    data.extend(bytes(0x200))
    table = 0x98 + (0xe0 if machine == 0x14c else 0xf0)
    struct.pack_into("<H", data, 0x86, 2)
    struct.pack_into("<I", data, 0x98 + 56, 0x3000)
    second = table + 40
    data[second:second + 8] = b".data\x00\x00\x00"
    # Adjacent raw intervals, distinct RVAs in the positive control.
    rva = 0x1000 if overlap == "virtual" else 0x2000
    raw = 0x200 if overlap == "raw" else 0x400
    struct.pack_into("<IIII", data, second + 8, 0x100, rva, 0x200, raw)
    struct.pack_into("<I", data, second + 36, 0xc0000040)
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

    def test_pe_envelope_positive_negative(self):
        for machine, dll in ((0x14c, True), (0x8664, False)):
            good = make_pe(machine, dll)
            pkg.assert_pe_image(good, machine, dll, "test")
            table = 0x98 + (0xe0 if dll else 0xf0)
            cases = (
                ("bad-offset", 0x3c, "I", 4),
                ("wrong-machine", 0x84, "H", 0xaa64),
                ("zero-sections", 0x86, "H", 0),
                ("too-many-sections", 0x86, "H", 97),
                ("short-opt", 0x94, "H", 2),
                ("wrong-role", 0x96, "H", 0x2 if dll else 0x2002),
                ("non-executable", 0x96, "H", 0x2000 if dll else 0),
                ("wrong-magic", 0x98, "H", 0x20b if dll else 0x10b),
                ("too-many-directories", 0x98 + (92 if dll else 108), "I", 17),
                ("small-headers", 0x98 + 60, "I", 0x100),
                ("small-image", 0x98 + 56, "I", 0x100),
                ("raw-overrun", table + 16, "I", 0x201),
                ("raw-overlap-headers", table + 20, "I", 0x100),
                ("virtual-overrun", table + 12, "I", 0x2000),
                ("no-exec", table + 36, "I", 0x40000040),
                ("bad-entry", 0x98 + 16, "I", 0x3000),
            )
            for name, offset, fmt, value in cases:
                with self.subTest(machine=machine, case=name):
                    bad = bytearray(good)
                    struct.pack_into("<" + fmt, bad, offset, value)
                    with self.assertRaises(ValueError):
                        pkg.assert_pe_image(bad, machine, dll, "test")
            with self.assertRaises(ValueError):
                pkg.assert_pe_image(good[:0x90], machine, dll, "test")
            no_entry = bytearray(good)
            struct.pack_into("<I", no_entry, 0x98 + 16, 0)
            if dll:
                pkg.assert_pe_image(no_entry, machine, dll, "test")
            else:
                with self.assertRaises(ValueError):
                    pkg.assert_pe_image(no_entry, machine, dll, "test")

    def test_section_overlap_build_and_rehashed_zip(self):
        root = self.path / "root"
        for index, machine in enumerate((0x14c, 0x8664)):
            target = (self.dll, self.host)[index]
            original = target.read_bytes()
            good = make_two_section_pe(machine)
            target.write_bytes(good)
            pkg.build_package(root, self.dll, self.host, SHA, self.zip_path)
            pkg.verify_package(self.zip_path, SHA)
            for kind in ("raw", "virtual"):
                with self.subTest(payload=pkg.PAYLOAD[index], overlap=kind):
                    bad = make_two_section_pe(machine, kind)
                    target.write_bytes(bad)
                    with self.assertRaisesRegex(ValueError, f"overlapping {kind}"):
                        pkg.build_package(root, self.dll, self.host, SHA, self.zip_path)
                    target.write_bytes(good)
                    def change(entries):
                        entries[pkg.PAYLOAD[index]] = bad
                        hashed = {name: data for name, data in entries.items()
                                  if name not in ("QA.json", "SHA256SUMS.txt")}
                        qa = json.loads(entries["QA.json"])
                        qa["ContentSha256"] = {name: pkg.digest(data)
                                               for name, data in hashed.items()}
                        entries["QA.json"] = json.dumps(qa).encode()
                        entries["SHA256SUMS.txt"] = pkg.contents_sha(hashed)
                    self.rewrite(change)
                    with self.assertRaisesRegex(ValueError, f"overlapping {kind}"):
                        pkg.verify_package(self.zip_path, SHA)
                    pkg.build_package(root, self.dll, self.host, SHA, self.zip_path)
            target.write_bytes(original)
            pkg.build_package(root, self.dll, self.host, SHA, self.zip_path)

    def test_negative_wrong_role_build_and_rehashed_zip(self):
        # Same machine, but DLL role reversed. Recomputed SHA/CRC cannot
        # substitute for the PE structural check at either package boundary.
        root = self.path / "root"
        for index, machine in enumerate((0x14c, 0x8664)):
            with self.subTest(payload=pkg.PAYLOAD[index]):
                bad = make_pe(machine, is_dll=(index != 0))
                target = (self.dll, self.host)[index]
                original = target.read_bytes()
                target.write_bytes(bad)
                with self.assertRaisesRegex(ValueError, "role"):
                    pkg.build_package(root, self.dll, self.host, SHA, self.zip_path)
                target.write_bytes(original)
                def change(entries):
                    entries[pkg.PAYLOAD[index]] = bad
                    hashed = {name: data for name, data in entries.items()
                              if name not in ("QA.json", "SHA256SUMS.txt")}
                    qa = json.loads(entries["QA.json"])
                    qa["ContentSha256"] = {name: pkg.digest(data)
                                           for name, data in hashed.items()}
                    entries["QA.json"] = json.dumps(qa).encode()
                    entries["SHA256SUMS.txt"] = pkg.contents_sha(hashed)
                self.rewrite(change)
                with self.assertRaisesRegex(ValueError, "role"):
                    pkg.verify_package(self.zip_path, SHA)
                pkg.build_package(root, self.dll, self.host, SHA, self.zip_path)

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
