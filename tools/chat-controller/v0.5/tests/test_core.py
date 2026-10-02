import json
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core import (
    consume_qa_inputs,
    enqueue_qa,
    initial_state,
    make_job,
    material_commit_ok,
    GITHUB_CONNECTION_FIRST_LINE,
    GITHUB_TOOL_RECOVERY_MESSAGE,
    LOCALIZATION_QUEUE_RECOVERY_MESSAGE,
    LOCALIZATION_BINARY_RECOVERY_MESSAGE,
    prepare_outgoing_message,
    github_tool_unavailable_response,
    github_read_limit_response,
    localization_binary_blocker_response,
    retry_surface_has_platform_error,
    reconcile_state,
    select_qa_batch,
)


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.specs = [
            {"name": "A", "role": "localization_producer", "branch": "korean-localization-clean", "shard": 0},
            {"name": "B", "role": "localization_producer", "branch": "korean-localization-clean", "shard": 1},
            {"name": "E", "role": "localization_producer", "branch": "korean-localization-clean", "shard": 2},
            {"name": "C", "role": "localization_qa", "branch": "korean-localization-clean", "qa_batch_size": 4},
        ]

    def test_reconcile_preserves_runtime_state(self):
        state = initial_state("localization", self.specs)
        state["lanes"]["A"]["chat_url"] = "https://chatgpt.com/g/g-p-x/c/1"
        state["lanes"]["A"]["chat_jobs"] = 3
        result = reconcile_state(state, "localization", self.specs)
        self.assertEqual(result["lanes"]["A"]["chat_jobs"], 3)
        self.assertEqual(result["lanes"]["A"]["shard"], 0)

    def test_each_job_has_unique_id(self):
        state = initial_state("localization", self.specs)
        a = state["lanes"]["A"]
        j1 = make_job(state, a, "a" * 40)
        j2 = make_job(state, a, "b" * 40)
        self.assertNotEqual(j1["job_id"], j2["job_id"])
        self.assertTrue(j1["job_id"].startswith("LOC-A-"))

    def test_producer_requires_real_candidate_dds(self):
        self.assertFalse(material_commit_ok("localization_producer", ["docs/automation/run.json"]))
        self.assertFalse(material_commit_ok("localization_producer", ["localization/resume_state.json"]))
        self.assertTrue(
            material_commit_ok(
                "localization_producer",
                ["localization/graphics/hd_candidates/textures/load/foo.dds"],
            )
        )

    def test_conversion_rejects_bookkeeping_only(self):
        self.assertFalse(
            material_commit_ok(
                "conversion",
                ["docs/automation/runs/x.json", "docs/CONVERSION_LANE_STATE.json", "AGENTS.md"],
            )
        )
        self.assertTrue(material_commit_ok("conversion", ["vr/src/vr/runtime/foo.cpp"]))
        self.assertTrue(material_commit_ok("conversion", ["tools/verify_dx11_source_graph.py"]))


    def test_qa_accepts_only_shared_state_or_v05_qa_record(self):
        self.assertFalse(material_commit_ok("localization_qa", ["docs/automation/runs/old.json"]))
        self.assertTrue(material_commit_ok("localization_qa", ["docs/automation/v05/LOC-C-000001.json"]))
        self.assertTrue(material_commit_ok("localization_qa", ["localization/resume_state.json"]))

    def test_qa_queue_exact_identity(self):
        state = initial_state("localization", self.specs)
        self.assertTrue(
            enqueue_qa(
                state,
                producer_job_id="LOC-A-000001",
                sha="1" * 40,
                lane="A",
                branch="korean-localization-clean",
            )
        )
        self.assertFalse(
            enqueue_qa(
                state,
                producer_job_id="LOC-A-000001",
                sha="1" * 40,
                lane="A",
                branch="korean-localization-clean",
            )
        )
        batch = select_qa_batch(state, 4)
        self.assertEqual(len(batch), 1)
        self.assertEqual(consume_qa_inputs(state, batch), 1)
        self.assertEqual(state["qa_pending"], [])

    def test_every_outgoing_message_gets_github_instruction_first(self):
        body = "Repository work rules for this job:\n- Repository: x"
        rendered = prepare_outgoing_message(body)
        self.assertEqual(rendered.splitlines()[0], GITHUB_CONNECTION_FIRST_LINE)
        self.assertEqual(rendered.count(GITHUB_CONNECTION_FIRST_LINE), 1)
        self.assertEqual(
            prepare_outgoing_message(rendered),
            rendered,
        )

    def test_detects_github_tool_unavailable_response(self):
        self.assertTrue(
            github_tool_unavailable_response(
                "현재 이 실행에서는 인증된 GitHub 커넥터 작업 도구 호출까지 연결하지 못해 최신 HEAD를 확인할 수 없습니다."
            )
        )
        self.assertTrue(
            github_tool_unavailable_response(
                "The GitHub connector tool is not available in this chat."
            )
        )
        self.assertFalse(
            github_tool_unavailable_response(
                "GitHub HEAD 확인 완료. 파일 수정과 커밋을 계속 진행합니다."
            )
        )

    def test_detects_github_read_limit_response(self):
        self.assertTrue(
            github_read_limit_response(
                "asset_queue.csv가 GitHub API 응답에서 단일 대형 JSON 라인으로 반환되어 필요한 후반부 queue 항목과 후보 DDS 경로를 끝까지 확인할 수 없는 상태입니다."
            )
        )
        self.assertTrue(
            github_read_limit_response(
                "GitHub API output was truncated because the file is too large, so I cannot inspect the remaining candidates."
            )
        )
        self.assertFalse(
            github_read_limit_response(
                "asset_queue.csv 전체를 확인했고 runnable asset 222를 선택했습니다."
            )
        )


    def test_detects_localization_binary_source_blocker(self):
        sample = (
            "GitHub 연결: OK. 현재 GitHub 텍스트 API 범위에서는 해당 바이너리 DDS payload를 "
            "직접 읽어 생성·검증할 수 있는 입력이 확보되지 않았습니다."
        )
        self.assertTrue(localization_binary_blocker_response(sample))
        self.assertTrue(
            localization_binary_blocker_response(
                "원본 DDS binary payload를 읽을 수 없어 작업을 진행할 수 없습니다."
            )
        )
        self.assertFalse(
            localization_binary_blocker_response(
                "GitHub Actions에서 DDS를 생성했고 material commit까지 완료했습니다."
            )
        )

    def test_detects_real_missing_branch_dds_responses(self):
        samples = [
            "현재 branch에서 실제 원본 DDS 파일을 확인할 수 없었다. canonical source/candidate를 확보할 수 없었다.",
            "현재 선택 가능한 B shard REWORK 항목 중 실제 DDS binary source를 GitHub branch에서 읽을 수 있는 대상이 확인되지 않았다.",
            "이번 응답 내에서는 DDS 원본/후보 바이너리 확보와 렌더링·SHA 검증·Git 커밋까지 완료할 수 있는 상태까지 도달하지 못했습니다.",
            "GitHub에서 해당 DDS 경로를 직접 조회했으나 파일 객체가 존재하지 않아 canonical source를 확보할 수 없었다.",
        ]
        for sample in samples:
            self.assertTrue(localization_binary_blocker_response(sample), sample)

    def test_binary_recovery_message_forces_server_side_action(self):
        rendered = prepare_outgoing_message(LOCALIZATION_BINARY_RECOVERY_MESSAGE)
        self.assertEqual(rendered.splitlines()[0], GITHUB_CONNECTION_FIRST_LINE)
        self.assertIn("GitHub Actions", rendered)
        self.assertIn("DDF0392A", rendered)
        self.assertIn("같은 JOB", rendered)

    def test_retry_button_requires_real_platform_error(self):
        self.assertFalse(retry_surface_has_platform_error("Retry this task when GitHub is ready"))
        self.assertTrue(retry_surface_has_platform_error("Something went wrong. Try again."))
        self.assertTrue(retry_surface_has_platform_error("응답 생성 중 오류가 발생했습니다. 다시 시도"))

    def test_same_chat_github_recovery_message_is_minimal(self):
        rendered = prepare_outgoing_message(GITHUB_TOOL_RECOVERY_MESSAGE)
        self.assertEqual(rendered.splitlines(), [GITHUB_CONNECTION_FIRST_LINE, "진행해"])

    def test_localization_queue_recovery_message_uses_ranged_reads(self):
        rendered = prepare_outgoing_message(LOCALIZATION_QUEUE_RECOVERY_MESSAGE)
        self.assertEqual(rendered.splitlines()[0], GITHUB_CONNECTION_FIRST_LINE)
        self.assertIn("start_line/end_line", rendered)
        self.assertIn("같은 JOB_ID", rendered)
        prompt = (ROOT / "prompts" / "localization_producer.md").read_text(encoding="utf-8")
        self.assertIn("40-80 physical CSV lines", prompt)
        self.assertIn("CSV index column", prompt)

    def test_localization_prompt_has_chunked_binary_fallback(self):
        prompt = (ROOT / "prompts" / "localization_producer.md").read_text(encoding="utf-8")
        self.assertIn("localization-binary-import-v05.yml", prompt)
        self.assertIn("binary_staging/v05/<JOB_ID>/", prompt)
        self.assertIn("manifest.json", prompt)
        self.assertIn("GitHub read-size/truncation is not a blocker", prompt)

    def test_config_has_expected_current_branches(self):
        config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        loc = config["modes"]["localization"]["lanes"]
        conv = config["modes"]["conversion"]["lanes"]
        self.assertEqual({x["name"] for x in loc}, {"A", "B", "C", "E"})
        self.assertEqual({x["branch"] for x in conv}, {"vr-dx11-native-r71", "vr-dxvk-r71-disasm"})


if __name__ == "__main__":
    unittest.main()
