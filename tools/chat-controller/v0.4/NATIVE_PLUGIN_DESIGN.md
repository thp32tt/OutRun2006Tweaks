# Native plugin controller design — 2026-10-02

## Requested outcome

Remove the text GitHub broker, including image/file transport through chat. ChatGPT uses connected GitHub/Drive and native image/file tools directly. The controller schedules work and observes durable GitHub results. Deployment remains user-operated.

## Evidence and boundary

Base: `cd63979869be7781e266f288d899b12011d8e7ba`, branch `chat-controller-downloads`, read through the connected GitHub plugin. N100 status at 06:44 KST showed DXVK-00267 in WAIT_CHAT, attempt 1, two rollovers and generic Retry activity, without a result SHA. This confirms a stalled queue, not a GitHub service outage.

Controller GitHub reads cannot prove the browser chat has a GitHub plugin. Model prose cannot prove a tool ran, a connection failed or a task succeeded. Final success continues to require the repository task commit and the existing exact-SHA workflow/producer-QA policy. Runtime validation remains UNTESTED unless independently performed.

## Selected structure

1. ChatGPT worker: discover and call connected plugins; edit source and native images/files directly. Report actual request target/result when a call fails; distinguish unavailable tool interface from remote connection failure. No public-web or N100 clone fallback.
2. Controller: read GitHub HEAD/commits/Actions using its own credential; preserve TASK_ID, current chat, High policy and lane contracts; no Git mutation API or broker parser.
3. Same-chat recovery: stable idle response without a durable commit gets a concise action request. Every such response follows one recovery path regardless of wording. Rate limits, send spacing and cooldown remain enforced. No attempt increment, terminal failure or rollover solely from model claims. Recovery is bounded per cooldown and resumes automatically.
4. One-time migration: existing tasks receive a short native-plugin instruction in the same chat. Preserve tasks, results, QA inputs and archived pending files. Never execute old broker tags.

## Options considered

- Broker hardening: rejected by user because it complicates image/file workflows.
- Prompt-only correction: insufficient; controller must independently verify outcomes.
- Native plugins plus read-only controller evidence: selected; reduces code and retains objective result gates.

## Verification / limitations

Regression tests exercise stalled/deferred recovery, repeated responses, Retry plus active generation, native migration, compact native prompts and absence of broker execution. Existing controller selftests remain required. Browser plugin availability and image editing cannot be guaranteed by prompt text; redeployed live execution must still be observed.
