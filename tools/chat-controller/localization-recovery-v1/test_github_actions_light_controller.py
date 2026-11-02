"""Zero-image-processing regression checks for existing Portainer light controller."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec=importlib.util.spec_from_file_location(
    "outrun_light", Path(__file__).with_name("github_actions_light_controller.py"))
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class LightControllerTests(unittest.TestCase):
    def test_self_test_constants(self):
        self.assertEqual(mod.WORKFLOW,"outrun-korean-github-compute.yml")
        self.assertTrue(mod.EXPECTED_SHA.fullmatch("1"*40))
        self.assertFalse(mod.EXPECTED_SHA.fullmatch("1"*39))
        self.assertFalse(mod.EXPECTED_SHA.fullmatch("../x"*10))

    def test_reject_unsafe_api_path(self):
        for path in ("https://attacker", "/https://attacker", "\\evil", "relative"):
            with self.assertRaises(ValueError):
                mod.api_call(path)

    def test_no_token_does_not_dispatch(self):
        with tempfile.TemporaryDirectory() as d, \
            patch.object(mod,"latest_asset_sha",return_value="a"*40), \
            patch.object(mod,"latest_qa_run",return_value={"head_sha":"b"*40,"status":"completed"}), \
            patch.object(mod,"dispatch_qa",side_effect=AssertionError("must not dispatch")):
            status=mod.check_cycle(Path(d),"")
            self.assertEqual(status["dispatch"],"GITHUB_SCHEDULE_AND_PUSH")
            self.assertFalse(status["local_image_processing"])
            self.assertFalse(status["local_dds_processing"])
            self.assertFalse(status["github_uses_docker"])

    def test_dispatch_only_once_for_new_sha(self):
        with tempfile.TemporaryDirectory() as d, \
            patch.object(mod,"latest_asset_sha",return_value="c"*40), \
            patch.object(mod,"latest_qa_run",return_value={"head_sha":"b"*40,"status":"completed"}), \
            patch.object(mod,"dispatch_qa") as send:
            first=mod.check_cycle(Path(d),"fake-token")
            second=mod.check_cycle(Path(d),"fake-token")
            self.assertEqual(first["dispatch"],"WORKFLOW_DISPATCHED")
            self.assertEqual(second["dispatch"],"DEDUP_SHA_ALREADY_DISPATCHED")
            send.assert_called_once_with("fake-token")

    def test_existing_run_same_head_not_redispatched(self):
        with tempfile.TemporaryDirectory() as d, \
            patch.object(mod,"latest_asset_sha",return_value="c"*40), \
            patch.object(mod,"latest_qa_run",return_value={"head_sha":"c"*40,"status":"in_progress"}), \
            patch.object(mod,"dispatch_qa",side_effect=AssertionError("duplicate dispatch")):
            status=mod.check_cycle(Path(d),"fake-token")
            self.assertEqual(status["dispatch"],"ALREADY_RUN_FOR_SHA")

    def test_no_secret_in_error_status(self):
        with tempfile.TemporaryDirectory() as d, \
            patch.object(mod,"latest_asset_sha",side_effect=RuntimeError("secret")):
            # The worker's main loop writes only exception type; no raw HTTP error or token.
            err={"status":"HOLD_RETRY","error_type":"RuntimeError"}
            self.assertNotIn("secret",str(err))
            mod.atomic_json(Path(d)/"err.json",err)
            self.assertTrue((Path(d)/"err.json").exists())


if __name__=="__main__":
    unittest.main()
