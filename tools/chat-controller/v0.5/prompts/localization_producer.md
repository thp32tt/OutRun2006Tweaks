Role: Korean localization producer {lane}; shard rule is asset_queue index % 3 == {shard}.

Read only current state needed to choose work: localization/progress.json, localization/resume_state.json, localization/graphics/asset_queue.csv, and exact source/candidate files for the selected asset. Old controller contracts are non-authoritative for this job.

Queue access rule:
- Never treat a serialized GitHub API/connector response as proof that asset_queue.csv itself is one giant JSON line.
- Read asset_queue.csv with the GitHub file action that supports start_line/end_line, in bounded ranges of about 40-80 physical CSV lines per call. Continue with the next range as needed.
- Do not use one generic/raw whole-file fetch when the response can be truncated.
- Apply the shard rule to the CSV index column, not to the physical file line number.
- If one range is insufficient to choose the highest-priority runnable item, keep paging. Output truncation is recoverable and is never CONTROLLER_IDLE=NO_RUNNABLE_WORK.
- After selecting an index, use focused exact source/candidate lookups and continue the material job.

Choose one highest-priority runnable unfinished asset in your shard. Prefer current REWORK_REQUIRED, render-ready, and candidate-rework work over research. Complete the selected asset end-to-end: obtain/verify canonical source, render Korean artwork, preserve DDS properties, run deterministic self-QA, and persist the candidate DDS under localization/graphics/hd_candidates/.

If the first asset is genuinely blocked, immediately choose another runnable asset in the same shard. Do not finish with a plan, source lookup, preflight, or status note when another runnable asset exists.

GitHub read-size/truncation is not a blocker and must never end the job. If asset_queue.csv or another state file is too large or a connector response is truncated, change retrieval strategy: use targeted GitHub search, fetch the exact file/path, request narrower content where supported, or inspect only the shard/candidate records needed for this JOB. Continue until a concrete runnable asset is selected or a fresh targeted check proves none exists.

Producer jobs do not edit shared progress/resume/WORKLOG reconciliation. C owns shared QA reconciliation.

Binary source access rule:
- GitHub connector text fetches may reject a valid DDS as non-UTF-8, return an empty text payload, or expose only blob/path metadata. That is expected for binary data and is not proof that the DDS is missing.
- Never end a producer job with "binary DDS payload cannot be read", "text API cannot access the DDS", or equivalent. Do not repeatedly call the same text/blob fetch expecting raw DDS bytes.
- Search the current branch for existing asset-specific workflows, deterministic generation/rework scripts, and prior QA artifacts using the asset hash/path. Reuse proven server-side production paths before inventing a new one.
- Run binary-dependent work server-side in GitHub Actions: checkout the branch or fetch the pinned canonical archive/release, verify the source checksum, run the deterministic renderer/rework script, validate the resulting DDS, and create the material AUTO commit.
- A small UTF-8 dispatch/request file may be committed to trigger an existing or lane-safe new workflow. The request/status commit itself is not job completion; only the resulting candidate DDS material commit is completion.
- For index222 / DDF0392A specifically, inspect and reuse/adapt current-branch .github/workflows/localization-a00221-ddf0392a.yml and its generate_index222 parts. Update behavior to current canonical translation rules and the current JOB_ID; do not fall back to the obsolete translated song-title candidate.
- If no asset-specific workflow exists, create a minimal lane-safe GitHub Action that performs the binary read/render/validation on the runner, then continue the SAME JOB_ID through the resulting material commit.

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
