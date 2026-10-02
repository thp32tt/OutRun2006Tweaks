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
