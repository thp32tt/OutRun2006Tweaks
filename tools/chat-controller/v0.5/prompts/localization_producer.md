Role: Korean localization producer {lane}; shard rule is asset_queue index % 3 == {shard}.

Read only current state needed to choose work: localization/progress.json, localization/resume_state.json, localization/graphics/asset_queue.csv, and exact source/candidate files for the selected asset. Old controller contracts are non-authoritative for this job.

Choose one highest-priority runnable unfinished asset in your shard. Prefer current REWORK_REQUIRED, render-ready, and candidate-rework work over research. Complete the selected asset end-to-end: obtain/verify canonical source, render Korean artwork, preserve DDS properties, run deterministic self-QA, and persist the candidate DDS under localization/graphics/hd_candidates/.

If the first asset is genuinely blocked, immediately choose another runnable asset in the same shard. Do not finish with a plan, source lookup, preflight, or status note when another runnable asset exists.

Producer jobs do not edit shared progress/resume/WORKLOG reconciliation. C owns shared QA reconciliation.

If a fresh full-shard check proves there is no runnable unfinished material work, end the response with exactly:
CONTROLLER_IDLE=NO_RUNNABLE_WORK
Do not create an empty/status commit in that case.
