# Lens transaction diagnostic completion

TASK_ID=USER-DX9EX-LENS-TRANSACTION-TRACE-20261028; lane=DX9EX;
base=c6b4140f1edfa714c7ef13a1ce261d0c9bd8fb1c; attempt=1.
User requested review and implementation of missing screen-error diagnostics.
RUNTIME_VALIDATION=UNTESTED. No optical repair or score claimed.

## Evidence and design

R30TryScreenSpaceFovDraw currently returns before PHYSICAL EYES when left
WVP upload or left Draw fails. rightHr combines RT/depth/viewport/WVP and
Draw results. Its preScissor describes only the pre-left state; it cannot
prove the actual right-eye raster after SetRenderTarget. Add a separate
read-only transaction receipt, with explicit attempted flags and stage,
and actual per-eye RT/depth/viewport/scissor-enable query HRESULTs.
Keep the existing physical-eye receipt and all rendering decisions intact.
No queue-flush hook, altered draw count, or inferred PMT ownership.

## Implementation plan

- [x] Add failing source-order/mutation regression for each failure exit,
  actual right raster capture and independent draw-attempt/result fields.
- [x] Add bounded VRTelemetry-only transaction diagnostics in compiled R26+HUD.
  Capture actual state immediately before left/right Draw, and after restore.
  Failed queries stay explicitly invalid. Bound normal and failure records
  independently; rearm normal sampling after a stable new Reset epoch.
- [ ] Run changed-area verifiers, review diff independently, publish using
  authenticated GitHub CAS preserving concurrent documentation commits.
- [ ] Validate exact SHA in hosted Active/Official/User/Domain and affected
  Inspector/Full Source gates. Record pre-existing failures separately.
- [ ] Persist exact result, CI and runtime-only next action.

Risk controls: no render-state writes in diagnostic helper; release temporary
COM query references; telemetry-off does no added device queries; no extra
physical Draw; S_OK from setup must never imply an attempted Draw.

## C3 source validation / C4 publication

Changed-area lens physical telemetry, FULL trace including 15 destructive
transaction mutants, desktop Reset coordinates, Reset transport, menu letterbox
and capture-bound client UV verifiers PASS. Independent code review found no
blocking production defects; added missing sample-guard mutations it requested.
Known baseline failures: HUD exact-callsite --self-test reports undetected
GOAL exit admission mutation; visual_composition_p0 expects retired
VR P0 RESULT PROGRESS SOURCE. These are not claimed passing or optical repairs.

Inherited Reset QPC is now explicitly labelled RESET_ENTRY. Separate native
Reset return, snapshot-ready, publish-return and frequency timestamps bracket
publication. C993/CABE source-event QPC and per-eye QPC describe actual event
observations, not opaque queue identity. Existing fields remain compatible.

Recovered 2026-10-28 22:53 KST after interrupted session. GitHub advanced to
006a44cf0185f260df04a25d3e63646a08154707; unrelated reflection/config changes
are preserved. Validation is pending exact result SHA. User requests finishing
only; no further diagnostic or optical scope expansion. No score change.
