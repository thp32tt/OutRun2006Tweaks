"""Synthetic bridge tests: prove the same on-disk English PNG bytes reach edit(image=...)."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from PIL import Image
import imagegen_source_edit_bridge as bridge


class FakeAPIReply:
    headers = {"x-request-id": "req-fixture-verified"}
    def __init__(self, data):
        self._data = data
    def parse(self):
        class Result: pass
        class Item: pass
        x, obj = Result(), Item()
        obj.b64_json = base64.b64encode(self._data).decode("ascii")
        x.data = [obj]
        return x


class FakeImageEdit:
    def __init__(self, source_sha, result):
        self.source_sha = source_sha
        self.result = result
        self.calls = []
    def edit(self, **kwargs):
        handle = kwargs.get("image")
        self.calls.append({
            "input_sha256": hashlib.sha256(handle.read()).hexdigest(),
            "input_name": handle.name,
            "model": kwargs.get("model"),
            "size": kwargs.get("size"),
            "background": kwargs.get("background"),
            "prompt": kwargs.get("prompt"),
        })
        if self.calls[-1]["input_sha256"] != self.source_sha:
            raise AssertionError("fake service did not receive the actual source file bytes")
        return FakeAPIReply(self.result)


class FakeClient:
    class Images:
        def __init__(self, edit):
            self.with_raw_response = edit
    def __init__(self, edit):
        self.images = self.Images(edit)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        def png():
            img = Image.new("RGBA", (76, 34))
            for y in range(5, 25):
                for x in range(8, 55):
                    img.putpixel((x, y), (230, 110, 20, 255))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        self.original = png()
        self.output = png()
        self.source = self.root / "english.png"
        self.source.write_bytes(self.original)
        self.req = {
            "schema": bridge.SCHEMA,
            "role": "C1",
            "queue_index": 102,
            "model": bridge.MODEL,
            "english_reference": {"path": "english.png", "sha256": bridge.digest(self.original)},
            "target_text": "타임 어택 모드",
            "prompt": "Create only transparent Korean lettering: 타임 어택 모드",
            "output_dir": "localization/graphics/role_C1/imagegen_requests",
            "request_key": "q102_C1_BIND_FIXTURE_ONLY",
        }

    def test_binary_multipart_file_is_actually_passed_and_receipted(self):
        mock_image = FakeImageEdit(bridge.digest(self.original), self.output)
        result = bridge.run(self.root, self.req, api_client=FakeClient(mock_image))
        self.assertEqual("REMOTE_MULTIPART_EDIT_RESPONSE_RECEIVED_RAW_UNREVIEWED", result["status"])
        self.assertEqual(1, len(mock_image.calls))
        self.assertEqual(bridge.digest(self.original), mock_image.calls[0]["input_sha256"])
        self.assertEqual(str(self.source), mock_image.calls[0]["input_name"])
        self.assertEqual("transparent", mock_image.calls[0]["background"])
        out = self.root / self.req["output_dir"]
        receipt = json.loads((out / "q102_C1_BIND_FIXTURE_ONLY_TOOL_INPUT_RECEIPT.json").read_text())
        manifest = json.loads((out / "q102_C1_BIND_FIXTURE_ONLY_OUTPUT_MANIFEST.json").read_text())
        self.assertEqual("openai.images.edit", receipt["tool"])
        self.assertEqual("multipart_image", receipt["image_input_field"])
        self.assertEqual("req-fixture-verified", receipt["openai_request_id"])
        self.assertEqual(bridge.digest(self.output), receipt["result_sha256"])
        self.assertEqual("openai-images-edit", manifest["generator"]["provider"])
        self.assertEqual("NOT_RUN", manifest["C2"])
        self.assertEqual(0, result["new_trial_dds"])

    def test_sha_preflight_must_match_real_bytes(self):
        self.req["english_reference"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SOURCE_REFERENCE_NOT_BOUND"):
            bridge.preflight(self.root, self.req)

    def test_protected_role_and_target(self):
        self.req["queue_index"] = 92
        with self.assertRaisesRegex(ValueError, "C1 shard"):
            bridge.preflight(self.root, self.req)
        self.req["queue_index"] = 102
        self.req["prompt"] = "Wrong phrase"
        with self.assertRaisesRegex(ValueError, "exact target"):
            bridge.preflight(self.root, self.req)

    def test_b_mod4_48_source_bytes_and_credential_gate(self):
        self.req.update({
            "role": "B",
            "queue_index": 48,
            "target_text": "슬립스트림",
            "prompt": "Create one transparent Korean glyph layer: 슬립스트림",
            "output_dir": "localization/graphics/role_B/imagegen_requests",
            "request_key": "q048_B_SLIPSTREAM_UNIT_ONLY",
        })
        path, binary_source, proof = bridge.preflight(self.root, self.req)
        self.assertEqual(self.source, path)
        self.assertEqual(bridge.digest(binary_source), proof["source_sha256"])
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "SOURCE_ATTACHMENT_API_CREDENTIAL_MISSING"):
                bridge.run(self.root, self.req)
        self.assertFalse((self.root / self.req["output_dir"]).exists())
        self.req["queue_index"] = 50
        with self.assertRaisesRegex(ValueError, "B shard"):
            bridge.preflight(self.root, self.req)

    def test_no_api_key_means_zero_calls_and_zero_output(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "SOURCE_ATTACHMENT_API_CREDENTIAL_MISSING"):
                bridge.run(self.root, self.req)
        self.assertFalse((self.root / self.req["output_dir"]).exists())

    def test_repeat_same_key_never_overwrites_bytes(self):
        fake = FakeClient(FakeImageEdit(bridge.digest(self.original), self.output))
        bridge.run(self.root, self.req, api_client=fake)
        with self.assertRaisesRegex(FileExistsError, "request_key"):
            bridge.run(self.root, self.req, api_client=fake)


if __name__ == "__main__":
    unittest.main()
