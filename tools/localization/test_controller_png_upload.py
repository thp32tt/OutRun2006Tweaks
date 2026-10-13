"""Offline unit tests only: no ChatGPT messages, Docker redeploy or external API."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch as mock_patch
import zlib

from controller_png_attach import load_binding, mark_sent, attach_png
from patch_controller_png_upload import patch
from stage_controller_policy import configure, A_SMOKE_TASK_ID, NAME as CONTROLLER_NAME


def small_png():
    def chunk(k, data):
        return struct.pack(">I", len(data)) + k + data + struct.pack(">I", zlib.crc32(k + data))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00\xff"))
            + chunk(b"IEND", b""))


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "inputs").mkdir()
        data = small_png()
        (self.root / "inputs" / "hd.png").write_bytes(data)
        self.manifest = {
            "role": "A", "task_id": "OUTRUN-TEST-Q001",
            "png": "hd.png", "png_sha256": hashlib.sha256(data).hexdigest(),
            "source_dds_sha256": "b" * 64,
            "prompt": "첨부된 영문 HD 원본의 SELECT CAR만 차량 선택으로 변경하세요.",
        }
        self.write_manifest()

    def write_manifest(self):
        (self.root / "pending_A.json").write_text(
            json.dumps(self.manifest, ensure_ascii=False), encoding="utf-8"
        )

    def test_exact_sha_and_dedup(self):
        binding, reason = load_binding("A", self.root)
        self.assertIsNone(reason)
        self.assertEqual(binding["dimensions"], [1, 1])
        self.assertEqual(binding["path"], str(self.root / "inputs" / "hd.png"))
        mark_sent(binding, self.root)
        self.assertEqual(load_binding("A", self.root)[1], "ALREADY_SENT")
        self.assertEqual(load_binding("B", self.root)[1], "SOURCE_REFERENCE_NOT_BOUND")

    def test_mismatched_sha_fails_closed(self):
        self.manifest["png_sha256"] = "a" * 64
        self.write_manifest()
        self.assertEqual(load_binding("A", self.root)[1], "PNG_SHA_MISMATCH")

    def test_corrupted_png_crc_is_rejected(self):
        bad = bytearray((self.root / "inputs" / "hd.png").read_bytes())
        bad[24] ^= 1
        (self.root / "inputs" / "hd.png").write_bytes(bad)
        self.manifest["png_sha256"] = hashlib.sha256(bad).hexdigest()
        self.write_manifest()
        self.assertEqual(load_binding("A", self.root)[1], "INVALID_PNG_CRC")

    def test_invalid_role_and_path_fails_closed(self):
        self.manifest["role"] = "B"
        self.write_manifest()
        self.assertEqual(load_binding("A", self.root)[1], "ROLE_MISMATCH")
        self.manifest["role"] = "A"
        self.manifest["png"] = "../hd.png"
        self.write_manifest()
        self.assertEqual(load_binding("A", self.root)[1], "INVALID_PNG_PATH")

    def test_missing_approved_prompt_rejected(self):
        self.manifest["prompt"] = ""
        self.write_manifest()
        self.assertEqual(load_binding("A", self.root)[1], "MISSING_APPROVED_PROMPT")

    def test_single_a_pilot_allows_only_exact_task_and_role(self):
        with mock_patch.dict(os.environ, {"OUTRUN_A_SINGLE_SMOKE_TASK_ID": A_SMOKE_TASK_ID}):
            self.assertEqual(load_binding("A", self.root)[1], "PILOT_TASK_ID_MISMATCH")
            self.assertEqual(load_binding("B", self.root)[1], "PILOT_ROLE_BLOCKED")
            self.manifest["task_id"] = A_SMOKE_TASK_ID
            self.write_manifest()
            binding, reason = load_binding("A", self.root)
            self.assertIsNone(reason)
            self.assertEqual(binding["task_id"], A_SMOKE_TASK_ID)
            mark_sent(binding, self.root)
            self.assertEqual(load_binding("A", self.root)[1], "ALREADY_SENT")

    def test_invalid_pilot_id_fails_closed(self):
        with mock_patch.dict(os.environ, {"OUTRUN_A_SINGLE_SMOKE_TASK_ID": "../../bad"}):
            self.assertEqual(load_binding("A", self.root)[1], "INVALID_PILOT_TASK_ID")


FIXTURE = '''LOCALIZATION_SLOT_NAMES = ("A", "B", "C1", "C2")
if CONTROLLER_MODE == "localization" and CHAT_SLOTS != 4:
    raise ValueError("Recovery localization requires CHAT_SLOTS=4 (A/B/C1/C2)")
SCHEDULED_LOCALIZATION_LANES = {0: "A", 10: "C1", 20: "C2",
                                30: "B", 40: "C1", 50: "C2"}
def load_registry():
        unexpected = set(existing) - set(LOCALIZATION_SLOT_NAMES)
async def send_message(page: Page, message: str) -> str:
    """Insert and send a prompt, returning the exact stage result for diagnostics."""
    box = await first_visible(page, INPUT_SELECTORS)
    if True:
        await page.wait_for_timeout(1500)
        return "sent"
async def watchdog():
        prompt = prompt_for_slot(slot, "watchdog")
        send_result = await send_message(page, prompt)
async def scheduled():
    send_result = await send_message(page, prompt)
    if send_result != "sent":
        pass
'''


class PatchTests(unittest.TestCase):
    def test_idempotent_patch_and_three_lanes(self):
        result = patch(FIXTURE)
        self.assertEqual(patch(result), result)
        self.assertIn('LOCALIZATION_SLOT_NAMES = ("A", "B", "C1")', result)
        self.assertIn('30: "B", 40: "C1"', result)
        self.assertIn('SOURCE_REFERENCE_NOT_BOUND', result)
        self.assertIn('png_binding["prompt"]', result)
        self.assertIn('retired_C2_slot_before_png_upload_v1.json', result)
        self.assertIn('OUTRUN_SINGLE_A_SMOKE_V1', result)
        self.assertIn('SCHEDULED_LOCALIZATION_LANES = {0: "A"}', result)
        self.assertIn('OUTRUN_A_SINGLE_SMOKE_TASK_ID and slot.name != "A"', result)

    def test_unknown_base_fails_without_modification(self):
        with self.assertRaises(ValueError):
            patch("async def send_message(page, message): pass")


class ComposeSmokeTests(unittest.TestCase):
    def setUp(self):
        self.revision = "a" * 40
        self.base = {"services": {CONTROLLER_NAME: {
            "environment": {"CHATGPT_PROJECT_URL": "https://chatgpt.com/g/example"},
            "volumes": ["volume:/data"],
        }}}

    def test_single_a_compose_preserves_volumes_and_true_autosend(self):
        cfg = configure(self.base, self.revision, single_a_smoke=True)
        service = cfg["services"][CONTROLLER_NAME]
        self.assertEqual(service["environment"]["CHAT_SLOTS"], "3")
        self.assertEqual(service["environment"]["SCHEDULE_MINUTES"], "0")
        self.assertEqual(service["environment"]["AUTO_SEND"], "true")
        self.assertEqual(service["environment"]["OUTRUN_A_SINGLE_SMOKE_TASK_ID"], A_SMOKE_TASK_ID)
        self.assertEqual(service["volumes"], ["volume:/data"])
        self.assertNotIn("OUTRUN_A_SINGLE_SMOKE_TASK_ID", self.base["services"][CONTROLLER_NAME]["environment"])

    def test_normal_compose_clears_pilot_lock(self):
        staged = configure(self.base, self.revision, single_a_smoke=True)
        normal = configure(staged, self.revision, single_a_smoke=False)
        env = normal["services"][CONTROLLER_NAME]["environment"]
        self.assertEqual(env["SCHEDULE_MINUTES"], "0,10,30,40")
        self.assertNotIn("OUTRUN_A_SINGLE_SMOKE_TASK_ID", env)
        self.assertEqual(env["AUTO_SEND"], "true")


class DummyLocator:
    def __init__(self, count=1, fail=False):
        self.number = count
        self.fail = fail
        self.uploads = []

    async def count(self):
        return self.number

    async def evaluate_all(self, expression):
        return self.number

    @property
    def last(self):
        return self

    async def set_input_files(self, path, timeout=None):
        if self.fail:
            raise RuntimeError("upload rejected")
        self.uploads.append(path)


class DummyPage:
    def __init__(self, fail=False):
        self.files = DummyLocator(fail=fail)
        self.preview = DummyLocator(count=0)
        self.waited = False

    def locator(self, selector):
        if "input[type='file']" in selector:
            return self.files
        return self.preview

    async def wait_for_function(self, expression, arg, timeout=None):
        if self.files.fail:
            raise RuntimeError("no preview")
        self.waited = True


class BrowserContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_file_input_and_preview_confirmation(self):
        page = DummyPage()
        result = await attach_png(page, {"path": "/tmp/hd.png"})
        self.assertEqual(result, "ATTACHED_PREVIEW_CONFIRMED")
        self.assertEqual(page.files.uploads, ["/tmp/hd.png"])
        self.assertTrue(page.waited)

    async def test_attachment_failure_does_not_claim_success(self):
        page = DummyPage(fail=True)
        self.assertEqual(
            await attach_png(page, {"path": "/tmp/hd.png"}),
            "ATTACHMENT_NOT_VERIFIED",
        )


if __name__ == "__main__":
    unittest.main()
