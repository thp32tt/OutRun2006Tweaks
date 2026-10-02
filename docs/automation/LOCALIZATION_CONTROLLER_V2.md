# Localization Controller V2

This is the only controller contract for the Korean-localization Docker stack.

## Domain isolation
This controller may work only on Korean localization. VR, FFB, DX9Ex, DX11, DXVK and OpenXR work belongs to a different controller/container and must never enter this queue, runtime state, task IDs or prompts.

## Scheduler
One wave is strictly:

1. Refresh `korean-localization-clean` HEAD.
2. Select one runnable even-index item for A and one runnable odd-index item for B from `localization/graphics/asset_queue_v2.csv`.
3. Dispatch A and B. They may run concurrently.
4. A/B are complete only when a real material commit containing their exact `[AUTO:TASK_ID]` exists. Assistant prose is never completion.
5. Do not start another production wave.
6. When both producer slots are terminal (material result or typed no-runnable-slot), dispatch C with the exact immutable producer TASK_ID@RESULT_SHA inputs.
7. C performs strict independent QA and is the only role that reconciles shared queue/progress/resume/worklog state.
8. PASS -> PRODUCTION_COMPLETE. Defect -> REWORK_REQUIRED returned to the owning A/B shard. Missing prerequisite -> HOLD.
9. Only after C commits the wave reconciliation may the next A/B wave start.

No E producer exists in v2.

## Producer rules
A owns even queue indices; B owns odd queue indices. No work stealing while both lanes are enabled. Producers modify candidate/localization artifacts and lane-local evidence only; they do not rewrite shared state. A producer that stops without a material commit remains the same task and is retried. After two failed same-chat attempts, open a fresh chat with the same TASK_ID and current Git HEAD.

## C rules
C receives only immutable results from the current wave. It must verify source identity, dimensions, 1-pixel containment, clipping, resolution, DDS format/mipmaps, alpha/transparency, orientation, background preservation, wrong-source replacement, Korean integrity and English residue as applicable. Runtime/in-game validation remains UNTESTED unless actually performed.

## Queue v2
`asset_queue_v2.csv` is operational state, not history. Never append old task narratives to it. Historical evidence stays in Git history, WORKLOG and `docs/automation/runs/`.

Required operational fields:
`index,path,action,state,owner,current_candidate_sha,current_qa_sha,blocker_code`.

Legacy `asset_queue.csv` is read-only migration evidence after v2 cutover.

## Docker boundary
The localization stack has its own persistent volume and browser/session registry. It must not mount or read VR controller runtime state. Restarting or rebuilding the localization stack must not affect the VR stack, and vice versa.
