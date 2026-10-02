Role: OutRun 2006 {backend} conversion/development lane.

Read AGENTS.md and current backend state/work-queue files that actually exist on this branch. Old controller pipeline schemas and C0-C6 turn rules are non-authoritative.

Select one highest-value unfinished static/development item for {backend}. Complete a meaningful implementation unit: inspect relevant code/evidence, implement or correct source/tool/test/workflow/disassembly artifacts, run available static or CI-oriented validation that does not require the user's gaming PC, and commit the material result.

A review/state-only update is not completion when implementable work remains. If the current item is blocked by unavailable runtime hardware, move to a different source/static/disassembly/test item instead of stopping.

Do not modify the other backend branch or localization files.

If a fresh branch-wide check proves there is no runnable source/static/development work, end the response with exactly:
CONTROLLER_IDLE=NO_RUNNABLE_WORK
Do not create a status-only commit in that case.
