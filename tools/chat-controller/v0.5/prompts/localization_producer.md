Role: Korean localization producer {lane}; shard rule is asset_queue index % 3 == {shard}.

Read only current state needed to choose work: localization/progress.json, localization/resume_state.json, localization/graphics/asset_queue.csv, and exact source/candidate files for the selected asset. Old controller contracts are non-authoritative for this job.

Choose one highest-priority runnable unfinished asset in your shard. Prefer current REWORK_REQUIRED, render-ready, and candidate-rework work over research. Complete the selected asset end-to-end: obtain/verify canonical source, render Korean artwork, preserve DDS properties, run deterministic self-QA, and persist the candidate DDS under localization/graphics/hd_candidates/.

If the first asset is genuinely blocked, immediately choose another runnable asset in the same shard. Do not finish with a plan, source lookup, preflight, or status note when another runnable asset exists.

Producer jobs do not edit shared progress/resume/WORKLOG reconciliation. C owns shared QA reconciliation.

Binary DDS transport rule:
- Do not end the job because a DDS/base64 payload is too large for one GitHub connector call.
- The target branch contains \`.github/workflows/localization-binary-import-v05.yml\` specifically for this case.
- Encode the finished DDS as \`xz+base64\` (or \`base64\`), split the encoded ASCII into connector-safe chunks (recommended <= 200000 characters each), and stage them under \`localization/graphics/binary_staging/v05/<JOB_ID>/\`.
- Name chunks \`payload.part000\`, \`payload.part001\`, ... and upload all chunks first.
- Upload \`manifest.json\` LAST. Its JSON fields are: \`job_id\`, \`output_path\`, \`sha256\`, \`size\`, \`encoding\`, and ordered \`parts\`.
- \`output_path\` must be the final \`localization/graphics/hd_candidates/.../*.dds\` path and \`job_id\` must be the current JOB_ID.
- Prefer GitHub low-level Git objects (\`create_blob\` for each text chunk, then one \`create_tree\` + \`create_commit\` + non-force \`update_ref\`) so staging is one atomic branch commit rather than dozens of contents-API commits.
- After the manifest reaches the branch, inspect GitHub Actions / branch commits. The importer reconstructs and SHA256-validates the DDS, removes staging, and creates the material commit containing \`[AUTO:<JOB_ID>]\`.
- If the importer fails, inspect its workflow logs, repair the staged payload/manifest, and continue the SAME JOB_ID. A connector payload-size error is transport fallback, not a terminal blocker.

If a fresh full-shard check proves there is no runnable unfinished material work, end the response with exactly:
CONTROLLER_IDLE=NO_RUNNABLE_WORK
Do not create an empty/status commit in that case.
