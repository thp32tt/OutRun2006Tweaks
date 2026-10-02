# OutRun Chat Controller v0.5

v0.5 is a clean controller. It does not load or interpret v0.4 scheduler contracts.

## Single source of truth

The controller owns scheduling state. Git owns work products. ChatGPT performs one atomic job at a time.

An assistant response ending is not job completion. A job completes only when the target branch contains a material commit with the exact AUTO JOB_ID marker.

## State machine

READY -> SENT -> WAIT_RESPONSE -> VERIFY_GIT -> DONE

If a response ends without a valid commit, the controller returns the same JOB_ID to READY. This is normal continuation, not failure and not chat rollover.

A new chat is created only when the current chat is unusable, a conversation-length limit is detected, or a completed chat exceeds the configured reuse budget.

## Localization

A, B and E are independent modulo-3 producers. One producer job takes one runnable asset through candidate DDS creation and self-QA. A producer completes only when its marked commit changes a DDS under localization/graphics/hd_candidates/.

Every completed producer commit is appended to the controller QA queue. C consumes up to four immutable producer JOB_ID@SHA inputs per job. Producers never wait for C.

## Conversion

DX11 and DXVK run independently. One job selects one unfinished static/development item, implements it, validates it, and commits a material result. Bookkeeping-only commits do not complete jobs.

Runtime validation is separate. Missing gaming-PC runtime does not block source, static, disassembly, test, workflow, or material analysis work.

## Removed v0.4 concepts

v0.5 has no schema-number negotiation, wave barrier, WAIT_ACTIONS, PREMATURE_STOP, rollover budget, multi-commit same-task batch target, controller_roles policy loading, or assistant-prose completion authority.

## Mandatory GitHub connection first line

Every controller-generated ChatGPT input is decorated at the final send boundary. Its first line is always:

`깃허브 연결은되어 있다 오류가 난다면 정상연결될때까지 무제한 다시 연결 상태를 확인한다`

This applies to new jobs and same-JOB continuation/recovery turns. Individual prompt files cannot bypass it.

GitHub tool-unavailable replies are retried in the SAME chat and SAME JOB_ID by sending only '진행해' after the mandatory first line. This repeats without an attempt limit. A new chat is reserved for actual platform/conversation failure.

GitHub read/output truncation replies (for example an oversized asset_queue response) use the same retry path; truncation is never accepted as a terminal no-work result.


## Large localization binary transport

Localization producers must not treat connector payload-size limits as material blockers. Large DDS candidates are transported as connector-safe ASCII chunks under \`localization/graphics/binary_staging/v05/<JOB_ID>/\`; \`manifest.json\` is written last. The branch workflow \`.github/workflows/localization-binary-import-v05.yml\` reconstructs, validates SHA256/size/DDS signature, removes staging, and publishes the final \`hd_candidates\` DDS in a material commit containing the same \`[AUTO:<JOB_ID>]\` marker.

## Connector-unavailable recovery

If an assistant response explicitly reports that the authenticated GitHub connector/tool is unavailable or not exposed, that response is never accepted as progress or completion. The controller preserves the exact JOB_ID, opens a fresh chat in the configured project, and retries without a finite attempt cap.

Visible Retry/Try again controls alone are not failure evidence. They are actionable only when the current visible surface also contains an actual ChatGPT generation/network error, preventing stale history controls from causing chat churn.


Queue-read recovery is same-chat first. If a localization producer claims asset_queue.csv is unreadable because a generic GitHub response is large or truncated, the controller keeps the same JOB_ID and sends a bounded start_line/end_line paging instruction instead of accepting the turn as blocked.
