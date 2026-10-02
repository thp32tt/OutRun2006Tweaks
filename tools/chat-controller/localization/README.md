# Standalone Korean Localization Controller

This directory is the independent Korean-localization runtime.

- hard-locked to localization mode;
- exactly three slots: A, B, C;
- image contains only localization A/B/C prompts;
- no VR/DX11/DXVK prompt is packaged;
- VR keeps its own existing controller/compose;
- stale D/E runtime records from an older shared controller are archived, not executed;
- persistent Generic Retry and missing-composer WAIT_CHAT states roll over to a fresh localization-project chat under the same TASK_ID.

Portainer:
- branch: `chat-controller-downloads`
- compose: `tools/chat-controller/localization/docker-compose.portainer.yml`

Execution environment:
- N100 connected execution environment is supported for controller operation, Docker/Portainer management, and validation.
- GitHub remains the source of truth for code and state records.
- Approved Google Drive canonical HD source transport may be used for original DDS acquisition when required by localization tasks.
- Original assets, DDS outputs, QA records, and Git history must be preserved.

Set `LOCALIZATION_PROJECT_URL`, `VNC_PASSWORD`, and optionally `GITHUB_TOKEN`. This stack defaults `AUTO_SEND=true`.
# Execution evidence and recovery (2026-10-02)

Producer completion now reads the exact task JSON and changed files at the result
commit. A BLOCKED record or bookkeeping-only commit stays resumable and is never
counted as a produced DDS. Material prerequisite changes are ADVANCED; only DDS
candidates enter C validation. External candidates must declare candidate_artifacts
with role=korean_candidate, path ending in .dds, sha256, and drive_file_id, with
changed self-QA evidence. C still verifies their bytes and all acceptance gates.

Stable answers without durable work resume the same TASK_ID with bounded backoff
(up to 15 minutes), preserving ATTEMPT and CHAT_ROLLOVER. Dispatch, repair and
rollover prompts require connected GitHub tool discovery and actual error evidence;
rollovers retain their real cause and C batch inputs. Legacy ineligible C inputs
are retained in qa_ineligible, not deleted or counted as completed artwork.

Both localization and v0.4 build contexts include this fix. Rebuild/redeploy the
Localization Portainer stack from chat-controller-downloads to activate it; a Git
commit alone does not replace an already running image. Keep the existing data and
log volumes. No queue reset or deletion of DDS, translations, QA or history is needed.

Regression check: `python tests/test_localization_execution.py` at repository root.
Browser dispatch and Docker deployment require separate live verification.

