import hashlib
import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.package_dino_pbr_copyrun import (
    BACKEND_FILES, DEFAULT_FILES, ROOT_FILES, SCRIPT_FILES,
    PBR_NAME, VARIANT, prepare_payload, write_zip,
)
from tools.tests.test_upgrade_dino_ovc_pbr import ovc2
from tools.upgrade_dino_ovc_pbr import upgrade


SHA="0123456789abcdef0123456789abcdef01234567"


def make_pe(path: Path, machine: int):
    data=bytearray(256)
    data[:2]=b"MZ"
    struct.pack_into("<I",data,0x3C,128)
    data[128:132]=b"PE\x00\x00"
    struct.pack_into("<H",data,132,machine)
    path.write_bytes(data)


def fixture(root: Path):
    artifact=root/"artifact"
    artifact.mkdir()
    for directory in ("scripts","defaults"):
        (artifact/directory).mkdir()
    for filename in ROOT_FILES:
        (artifact/filename).write_text("test launcher\n",encoding="ascii")
    for filename in SCRIPT_FILES:
        (artifact/"scripts"/filename).write_text("test script\n",encoding="ascii")
    for filename in DEFAULT_FILES:
        (artifact/"defaults"/filename).write_text("test INI\n",encoding="ascii")
    for filename in BACKEND_FILES:
        (artifact/filename).write_bytes(b"")
    make_pe(artifact/"dinput8.dll",0x14C)
    make_pe(artifact/"outrun-vr-host.exe",0x8664)
    (artifact/"SOURCE_SHA.txt").write_text(SHA+"\n",encoding="ascii")
    (artifact/"HOST_BUILD_SOURCE_SHA.txt").write_text(SHA+"\n",encoding="ascii")
    (artifact/"VARIANT_ID.txt").write_text(VARIANT+"\n",encoding="ascii")
    model=root/"model.ovc"
    model.write_bytes(upgrade(ovc2(),{"materials":[]},root))
    return artifact,model


class DinoPbrPackageTests(unittest.TestCase):
    def test_exact_sha_complete_zip_and_no_top_level_dll(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            artifact,model=fixture(root)
            contents=prepare_payload(artifact,model)
            identity=json.loads(contents["QUEST_APK_COPYRUN_PAYLOAD/IDENTITY.json"])
            self.assertEqual(identity["SourceSha"],SHA)
            self.assertEqual(identity["HostSourceSha"],SHA)
            self.assertEqual(identity["VariantId"],VARIANT)
            self.assertEqual(identity["DinoPbrModelSha256"],hashlib.sha256(model.read_bytes()).hexdigest())
            self.assertIn(f"QUEST_APK_COPYRUN_PAYLOAD/model/{PBR_NAME}",contents)
            self.assertNotIn("dinput8.dll",contents)
            self.assertNotIn("outrun-vr-host.exe",contents)
            self.assertNotIn("OR2006C2C.EXE",contents)
            dest=root/"out.zip"
            write_zip(contents,dest)
            with zipfile.ZipFile(dest) as z:
                self.assertIsNone(z.testzip())
                self.assertEqual(sorted(z.namelist()),sorted(contents))
                self.assertEqual(z.read("QUEST_APK_COPYRUN_PAYLOAD/IDENTITY.json"),contents["QUEST_APK_COPYRUN_PAYLOAD/IDENTITY.json"])
                self.assertEqual(z.read(f"QUEST_APK_COPYRUN_PAYLOAD/model/{PBR_NAME}"),model.read_bytes())
            with self.assertRaises(FileExistsError):
                write_zip(contents,dest)
            self.assertTrue(dest.exists())

    def test_reject_mixed_host_sha_wrong_arch_corrupt_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            artifact,model=fixture(root)
            marker=artifact/"HOST_BUILD_SOURCE_SHA.txt"
            marker.write_text("f"*40,encoding="ascii")
            with self.assertRaisesRegex(ValueError,"SHA or variant"):
                prepare_payload(artifact,model)
            marker.write_text(SHA,encoding="ascii")
            make_pe(artifact/"dinput8.dll",0x8664)
            with self.assertRaisesRegex(ValueError,"architecture"):
                prepare_payload(artifact,model)
            make_pe(artifact/"dinput8.dll",0x14C)
            broken=bytearray(model.read_bytes())
            broken[-1]^=1
            model.write_bytes(broken)
            with self.assertRaisesRegex(ValueError,"CRC32"):
                prepare_payload(artifact,model)
            model.write_bytes(b"OVRCABH2"+bytes(28))
            with self.assertRaisesRegex(ValueError,"not an OVC3"):
                prepare_payload(artifact,model)

    def test_reject_incomplete_artifact_without_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            artifact,model=fixture(root)
            (artifact/"scripts/Run-OutRunVRTest.ps1").unlink()
            with self.assertRaisesRegex(ValueError,"missing or unsafe"):
                prepare_payload(artifact,model)
            self.assertEqual(list(root.glob("*.zip")),[])


if __name__=="__main__":
    unittest.main()
