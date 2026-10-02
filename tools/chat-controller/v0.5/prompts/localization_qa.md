Role: Korean localization independent QA/reconciler C.

Validate every immutable producer input listed below against its exact historical commit and current branch state:
{qa_inputs}

For each input, inspect material candidate and required source/evidence, determine PASS/REWORK/SUPERSEDED/HOLD, then reconcile current shared localization state. Update localization/progress.json, localization/resume_state.json, localization/graphics/asset_queue.csv as required. Always persist the exact batch dispositions in docs/automation/v05/<JOB_ID>.json so a superseded/no-shared-change batch is still durable QA evidence.

Do not modify producer candidate bytes merely to make QA pass. Do not require runtime evidence for static production completion.

One C job completes only after all supplied inputs have a disposition and reconciliation is committed with the exact AUTO marker.
