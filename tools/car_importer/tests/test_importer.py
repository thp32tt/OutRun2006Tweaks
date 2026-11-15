from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock

# Standalone test invocation without package installation.
sys.path.insert(0, str(Path(__file__).parents[2]))
from car_importer.glb import inspect_glb, InvalidModel
from car_importer.game import GameSafetyError, verify_game, make_backup, restore_backup, install_model
from car_importer.profiles import Profile, PROFILES
from car_importer.cli import stage_model, StageError


def sample_glb(*, bad_stride=False, license_text="CC-BY-4.0", draco=False, no_indices=False):
    vertex_data = struct.pack("<9f", 0, 0, 0, 1, 0, 0, 0, 0, 1)
    index_data = struct.pack("<3H", 0, 1, 2)
    binary = vertex_data + index_data + b"\x00\x00"
    primitive = {"attributes": {"POSITION": 0}, "mode": 4}
    if not no_indices:
        primitive["indices"] = 1
    if draco:
        primitive["extensions"] = {"KHR_draco_mesh_compression": {"bufferView": 0, "attributes": {"POSITION": 0}}}
    payload = {
        "asset": {"version": "2.0", "extras": {"license": license_text, "author": "Test artist"}},
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": 36, **({"byteStride": 8} if bad_stride else {})},
            {"buffer": 0, "byteOffset": 36, "byteLength": 6},
        ],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "type": "VEC3", "count": 3,
             "min": [0, 0, 0], "max": [1, 0, 1]},
            {"bufferView": 1, "componentType": 5123, "type": "SCALAR", "count": 3},
        ],
        "meshes": [{"name": "Original_Test_Model", "primitives": [primitive]}],
        "nodes": [{"mesh": 0}],
        "scenes": [{"nodes": [0]}],
        "scene": 0,
    }
    j = json.dumps(payload, separators=(",", ":")).encode()
    j += b" " * (-len(j) % 4)
    body = struct.pack("<II", len(j), 0x4E4F534A) + j + struct.pack("<II", len(binary), 0x004E4942) + binary
    return struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body


class GLBTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "source.glb"

    def test_valid_glb(self):
        self.path.write_bytes(sample_glb())
        data = inspect_glb(self.path)
        self.assertEqual(data["status"], "PREFLIGHT_PASS_NOT_GAME_READY")
        self.assertEqual(data["triangles"], 1)
        self.assertEqual(data["vertices"], 3)
        self.assertEqual(data["sha256"], hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertFalse(data["game_installable"])
        self.assertIn("CC-BY-4.0", data["license_claim_unverified"])

    def test_truncated_glb(self):
        self.path.write_bytes(sample_glb()[:-4])
        with self.assertRaises(InvalidModel):
            inspect_glb(self.path)

    def test_wrong_stride(self):
        self.path.write_bytes(sample_glb(bad_stride=True))
        with self.assertRaises(InvalidModel):
            inspect_glb(self.path)

    def test_draco_rejected_without_geometry_validation(self):
        self.path.write_bytes(sample_glb(draco=True))
        with self.assertRaises(InvalidModel):
            inspect_glb(self.path)

    def test_no_indices_rejected(self):
        self.path.write_bytes(sample_glb(no_indices=True))
        with self.assertRaises(InvalidModel):
            inspect_glb(self.path)

    def test_disallows_non_glb(self):
        p = self.path.with_suffix(".obj")
        p.write_bytes(sample_glb())
        with self.assertRaises(InvalidModel):
            inspect_glb(p)

    def test_stage_refuses_to_write_inside_game_tree(self):
        self.path.write_bytes(sample_glb())
        game = Path(self.temp.name) / "game"
        (game / "Cars").mkdir(parents=True)
        (game / "OR2006C2C.exe").write_bytes(b"game")
        with self.assertRaisesRegex(StageError, "OUTSIDE"):
            stage_model(self.path, sys.executable, game / "Cars" / "stage", rights_confirmed=True)
        self.assertFalse((game / "Cars" / "stage").exists())

    def test_stage_rejects_nonempty_existing_folder(self):
        self.path.write_bytes(sample_glb())
        folder = Path(self.temp.name) / "staging"
        folder.mkdir()
        (folder / "keep.txt").write_text("do not touch")
        with self.assertRaisesRegex(StageError, "empty"):
            stage_model(self.path, sys.executable, folder, rights_confirmed=True)
        self.assertEqual((folder / "keep.txt").read_text(), "do not touch")

    def test_uses_external_rights_gate(self):
        self.path.write_bytes(sample_glb())
        with self.assertRaises(StageError):
            stage_model(self.path, "not_a_blender", Path(self.temp.name) / "output")


class GameSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.tmp = Path(self.temp.name)
        self.game = self.tmp / "game"
        (self.game / "Cars").mkdir(parents=True)
        (self.game / "OR2006C2C.exe").write_bytes(b"fake exe for path check")
        self.src = self.game / "Cars" / "obj_plcar_f50_pmt.sz"
        self.src.write_bytes(b"test original fixture")
        sha = hashlib.sha256(self.src.read_bytes()).hexdigest()
        self.test_profile = Profile("f50", "Test F50", "obj_plcar_f50_pmt.sz", sha,
                                    (2, 1, 4), (0, .5, 0), 0)
        patcher = mock.patch.dict(PROFILES, {"f50": self.test_profile})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_verified_original_backup_and_noop_restore(self):
        info = verify_game(self.game)
        self.assertEqual(info["status"], "SOURCE_VERIFIED_NO_GAME_FILES_CHANGED")
        original = self.src.read_bytes()
        receipt = make_backup(self.game, self.tmp / "backup")
        receipt_file = Path(receipt["backup_directory"]) / "receipt.json"
        self.assertTrue(receipt_file.exists())
        self.assertEqual((receipt_file.parent / "original_pmt.sz").read_bytes(), original)
        status = restore_backup(self.game, receipt_file)
        self.assertEqual(status["status"], "ALREADY_ORIGINAL_NO_RESTORE_REQUIRED")
        self.assertEqual(self.src.read_bytes(), original)

    def test_modified_game_never_overwritten(self):
        receipt = make_backup(self.game, self.tmp / "backups")
        self.src.write_bytes(b"a user mod in place")
        with self.assertRaises(GameSafetyError):
            restore_backup(self.game, Path(receipt["backup_directory"]) / "receipt.json")
        self.assertEqual(self.src.read_bytes(), b"a user mod in place")

    def test_unknown_game_sha_blocks(self):
        self.src.write_bytes(b"modified")
        with self.assertRaises(GameSafetyError):
            verify_game(self.game)
        with self.assertRaises(GameSafetyError):
            make_backup(self.game, self.tmp / "backups")

    def test_backup_in_game_directory_rejected(self):
        with self.assertRaises(GameSafetyError):
            make_backup(self.game, self.game / "backups")

    def test_different_game_root_rejected(self):
        receipt = make_backup(self.game, self.tmp / "backups")
        alt = self.tmp / "other"
        alt.mkdir()
        with self.assertRaises(GameSafetyError):
            restore_backup(alt, Path(receipt["backup_directory"]) / "receipt.json")

    def test_game_install_explicitly_disabled(self):
        with self.assertRaises(GameSafetyError) as cm:
            install_model(self.game, self.tmp / "staged_car.glb")
        self.assertIn("GAME_INSTALL_BLOCKED", str(cm.exception))


if __name__ == "__main__":
    unittest.main()