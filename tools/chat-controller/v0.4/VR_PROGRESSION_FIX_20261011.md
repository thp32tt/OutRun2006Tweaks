# VR development progression repair — 2026-10-11

Request: stop repeated recovery/review of DX11 00537 and DX9Ex 00591 and advance real development. Controller build identifier: `2026-10-11-progress-v2`.

## Evidence and cause

- GitHub checkpoint `tools/chat-controller/checkpoints/vr/CONVERSION-DX9EX-00591/20261011T1005-periodic.json` records FEATURE_READY, WAIT_CHAT, attempt 2, 17 rollovers, and ACCEPTANCE_ITEM_PENDING:R84-OWNERS. Feature record actually uses PASS_FEATURE_CI. Current repository already understands that R84 label, so the checkpoint is inconsistent with the latest source; deployment must be checked independently.
- DX11 00537 uses explicit source/build/runtime-untested and binary-package PASS labels that the controller rejected. A finite compatibility mapping now accepts those labels only as source acceptance; remote gates/package and runtime separation remain mandatory.
- R84 acceptance steps and ZIP are produced by its dedicated feature workflow. The delivery verifier searched only target Active/Domain runs, so it could never find them. Both target gates and dedicated feature CI now must pass at the same candidate SHA.
- A legacy AUTO marker could bypass feature promotion, and WAIT_ACTIONS could chase later bookkeeping commits. Feature tasks now go through the promotion owner and keep the promoted validation SHA pinned.
- A worker had to write another C6 record after the controller already proved completion. The controller now persists and reads back an exact-SHA result under `tools/chat-controller/results/vr/` without changing the game candidate. Save failure prevents release.
- DX9Ex backlog ended at R84. It now has a dependent OpenXR recommended per-eye extent deliverable and independent bounded frame-pacing diagnostics. No automatic DXVK activation.

## Execution behavior

Reconcile remote progress before rollover. Preserve the requested 30-minute rollover and 40-minute recovery for unfinished work. After an idle, stable worker response, repair actual READY schema/ancestry/failed-CI blockers under bounded attempts; exhaustions become BLOCKED, allowing independent backlog work instead of endless re-review. Running CI does not consume a repair attempt.

Worker prompts prohibit repeated same-SHA PASS audits and READY/status-only commits. FEATURE_CONTRACT remains the finite work scope. Hardware validation remains UNTESTED and is never synthesized from CI.

## Validation

- Fail-before/pass-after tests reproduced DX11 schema rejection, missing next DX9Ex work, legacy-marker promotion bypass, bookkeeping SHA rebinding, and R84 evidence lookup in the wrong workflow.
- New progression tests plus existing feature-pipeline tests: 21 passing locally.
- Complete concatenated controller Python source compiles locally.
- New hosted workflow `VR controller progression regression` checks these two suites and assembled compilation. Hosted result must be inspected separately; local tests do not prove Docker deployment.

## Deployment and observable acceptance

User deployment remains separate. Rebuild/redeploy the existing VR stack from branch `chat-controller-downloads`, Compose path `tools/chat-controller/v0.4/docker-compose.portainer-vr.yml` (same persistent volumes). `/status` runtime and subsequent GitHub checkpoints must identify `2026-10-11-progress-v2`.

After deployment, verify that READY is promoted or gets an exact actionable repair reason, candidate SHA stays stable during final CI, successful delivery creates a controller result, and the lane advances to a different feature. No claim of live Docker, game or HMD PASS is made by this source change.
