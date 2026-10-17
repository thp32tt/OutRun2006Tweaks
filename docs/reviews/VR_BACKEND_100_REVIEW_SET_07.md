# VR Backend 100-Review Campaign — Set 07/10

Derived from Set 06. Set 07 reviews frame transport, synchronization and OpenXR handoff in ten distinct passes.

## Passes

| ID | Direction | Result | Evidence / finding |
|---|---|---|---|
| S07-R01 | Frame/run ABI identity | PASS | Frame ring carries client PID plus per-game run generation; each slot mirrors run generation and RenderFrameRunIdentityMatches rejects stale slots from a previous process. |
| S07-R02 | ACK read consistency | PASS | Game-side ACK reads use a sequence-before/copy/sequence-after pattern and validate magic/version/size plus host PID, client PID, run generation and transport generation. |
| S07-R03 | Producer slot reuse | PASS | Published DirectGPU slots are not reused until producer EVENT completion and the exact host consumer ACK says the frame was GPU-consumed. Unpublished failed copies do not require a host ACK. |
| S07-R04 | Host hold-copy ordering | PASS | main_r23 copies shared producer eyes into host-owned hold textures before the verified projection is considered authoritative. Grace/cached projection samples the host-owned hold texture, not a producer texture that may later be reused. |
| S07-R05 | Consumer EVENT ordering | PASS | R32 arms a D3D11 EVENT after the already-rendered/source-sampling command stream; ACK is published only when GetData reports completion. This preserves copy/render-before-ACK ordering. |
| S07-R06 | ACK publish failure | PASS_FAIL_CLOSED | If publishing the completed frame fails, the pending ACK remains armed and is retried; the producer slot stays blocked instead of being released without a durable ACK. |
| S07-R07 | Generation rollover | PASS | New committed transport generation is observed before polling old EVENTs. Late completion from an older generation is discarded and cannot roll ACK state backwards. |
| S07-R08 | Same-frame XR resubmission | PASS | A repeated submission of the same frame/generation while its EVENT is pending reuses the existing protection instead of falsely treating the slot as an unsafe new producer frame. |
| S07-R09 | Host shutdown/session destruction | PASS_WITH_CAVEAT | DestroySession releases pending host queries and direct caches. Producer-side host freshness/eligibility is responsible for closing the path after host loss; no stale ACK is manufactured during destruction. |
| S07-R10 | DX11 native eye-ring parity | BLOCKER_DX11_ACTIVATION | The proven D3D9Ex transport has run identity, transport generation, producer fence, host hold copy and consumer ACK. NativeSharedEyeRing currently provides shared eyes plus producer EVENT queries only. It must adopt equivalent publication/ACK/generation semantics before native draw activation. |

## Findings carried forward

- The established D3D9Ex DirectGPU transport is accepted as the synchronization reference.
- **F26 BLOCKER DX11 activation:** native eye ring must not invent a simpler synchronization protocol; it needs parity with the proven frame/run/generation/ACK contract.
- No new defect was found in the reviewed R32 asynchronous ACK ordering.
- Set 03 F11 is strengthened by concrete reference behavior rather than duplicated as a new issue.

## Set 08 direction derived from Set 07

Set 08 reviews **hot-path performance and instrumentation cost**. Ten lenses: per-draw census overhead, D3D9 getter cost, mutex/tag-table contention, logging allocations, host EVENT polling, Flush escalation, extra copies, frame pacing, SkyGlow/post effects, and whether diagnostic mode can distort the performance data it is intended to measure.

No production source changes are made by this review commit.
