"""Regression coverage for 5-source A queue; does not claim ImageGen completion."""
import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("tile_batch_queue", ROOT / "tile_batch_queue.py")
queue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(queue)


def chunk(tag, data):
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))


def tiny_png():
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\x00")) +
            chunk(b"IEND", b""))


class FakePage:
    def __init__(self, seen):
        self.seen = seen

    async def evaluate(self, js, args):
        return {
            "status": "RESULTS_VISIBLE" if self.seen >= args["expected"] else "RESULTS_NOT_YET_VISIBLE",
            "count": self.seen
        }


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.folder = self.root / queue.TILE_DIR
        self.folder.mkdir(parents=True)
        raw = tiny_png()
        sha = hashlib.sha256(raw).hexdigest()
        self.mapping = []
        for i in range(10):
            name = f"asset_{i:03d}_BASE_READABLE_FLIPY.png"
            (self.folder / name).write_bytes(raw)
            self.mapping.append({
                "part_filename": name,
                "part_png_sha256": sha,
                "source_dds_path": "texture/test.dds",
                "queue_indexes": "12",
                "width": "1", "height": "1",
                "orientation": "FLIP_Y_PREVIEW_PER_SPRITE_VERIFY",
            })
        self.sources = {"texture/test.dds": {"dds_sha256": "a" * 64}}
        self.translations = {"12": [("START", "출발", "[]"), ("Tuned", "튜닝", "[]")]}
        self.fake_source = patch.object(queue, "_source_rows", return_value=(
            self.mapping, self.sources, self.translations))
        self.fake_source.start()
        self.addCleanup(self.fake_source.stop)
        self.env = patch.dict(os.environ, {"OUTRUN_A_TILE_BATCH_QUEUE": "true"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_exactly_five_and_idempotent(self):
        first, reason = queue.prepare_next_binding(self.root)
        self.assertIsNone(reason)
        self.assertEqual(first["expected_images"], 5)
        self.assertEqual(len(first["paths"]), 5)
        self.assertIn("START => 출발", first["prompt"])
        self.assertEqual(first["task_id"], "OUTRUN-A-HD5-0001-20261014")
        next_job, error = queue.prepare_next_binding(self.root)
        self.assertIsNone(error)
        self.assertEqual(first["task_id"], next_job["task_id"])
        state = json.loads((self.root / queue.STATE_NAME).read_text())
        self.assertEqual(state["offset"], 0)

    def test_hash_failure_stops_submission(self):
        self.mapping[0]["part_png_sha256"] = "0" * 64
        job, reason = queue.prepare_next_binding(self.root)
        self.assertIsNone(job)
        self.assertIn("PNG_SHA_MISMATCH", reason)

    def test_hold_until_five_assistant_images(self):
        first, reason = queue.prepare_next_binding(self.root)
        self.assertIsNone(reason)
        sent = self.root / "sent" / ("A_" + first["task_id"] + ".json")
        sent.parent.mkdir(exist_ok=True)
        sent.write_text(json.dumps({
            "status": "CHAT_MESSAGE_SENT_ATTACHMENT_UI_VERIFIED_NOT_IMAGEGEN_PASS",
            "submitted_at": queue._now().isoformat(),
            "tiles": [{"filename": t["filename"]} for t in first["tiles"]],
        }))
        binding, msg = queue.prepare_next_binding(self.root)
        self.assertIsNone(binding)
        self.assertEqual(msg, "WAITING_FOR_FIVE_GENERATED_IMAGES")
        check = asyncio.run(queue.confirm_visible_results(FakePage(4), self.root))
        self.assertEqual(check, "WAITING:4/5")
        self.assertEqual(json.loads((self.root / queue.STATE_NAME).read_text())["offset"], 0)
        check = asyncio.run(queue.confirm_visible_results(FakePage(5), self.root))
        self.assertEqual(check, "BATCH_IMAGES_VISIBLE_CONFIRMED")
        assert (self.root / "a_tile_batches" / "visible_results" / (first["task_id"] + ".json")).exists()
        next_job, reason = queue.prepare_next_binding(self.root)
        self.assertIsNone(reason)
        self.assertEqual(next_job["task_id"], "OUTRUN-A-HD5-0002-20261014")
        self.assertEqual(json.loads((self.root / queue.STATE_NAME).read_text())["offset"], 5)

    def test_uncertain_send_never_advances(self):
        first, reason = queue.prepare_next_binding(self.root)
        self.assertIsNone(reason)
        path = self.root / "sent" / ("A_" + first["task_id"] + ".json")
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({"status": "SUBMISSION_UNVERIFIED_DO_NOT_AUTO_RETRY"}))
        check = asyncio.run(queue.confirm_visible_results(FakePage(5), self.root))
        self.assertEqual(check, "UNVERIFIED_SUBMISSION_HOLD")
        self.assertEqual(json.loads((self.root / queue.STATE_NAME).read_text())["offset"], 0)


if __name__ == "__main__":
    unittest.main()