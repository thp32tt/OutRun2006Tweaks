# Ferrari SLOT A Daytona — hosted BLOCKED gate (2026-11-09 KST)

- Scope/owner: `active_by_slot.A=daytona365`, original 24-hour start `2026-11-08T04:13:41Z`; SLOT C/Dino untouched.
- User target `inner_door`: already R45 `COVERED_PARTIAL_QA` (one source-backed checkpoint), not full-car QA; existing original-derived `V5_L_LEATHER_SCULPTED_DOOR` source `object00_group01_material005_a0`. Do not repeat this first-pass edit or touch wheel/dashboard.
- Original native PMT read-only SHA256: `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe`. Original imported Blender SHA256: `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`. Latest accepted private R45 editable Blender SHA256: `224131c7adc928d5d6f0377d030d5a350c59b8664c13303a2731d6dfc6e9a722` (see R45 report).
- GitHub-hosted public run [42540030991](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/42540030991), job SLOT A: ciphertext reassembly PASS; `FERRARI_BUNDLE_KEY_B64` empty, `BLOCKED_KEY_OR_UNSELECTED`; decrypt, Blender save/reopen/render, artifact upload skipped. The run's overall green status **does not certify geometry**.
- Public slot A AES-GCM ciphertext manifest SHA256 `502cf59b193ad45345ca50e6dd093eb88c92248ae044a99d9860991d6fffd520`; originally committed 2026-11-09 00:10:44 UTC, before R45 geometry source commit 2026-11-09 00:39:56 UTC. It cannot certify the latest R45 .blend as input. Do not assume encrypted contents.
- Windshield-frame work is `BLOCKED` by hosted key/current encrypted input, **not** proven absent in original PMT; no windshield mesh fabricated or edited. Per breadth-first skip policy the next candidate is `visible_seat`. Underlying hosted prerequisites must be resolved before any real geometry edit.
- No Blender executed on N100, no PMT/OVC/OVC3/game conversion/export, no exterior/wheel, new model, textures/PBR, Model2, Dino, or other slots.
- This checkpoint has **no material modeling achievement**; `vehicle QA PASS=false`, score delta `+0`. No geometry script committed as an unverified edit.

## Correction after newer public VM runs — 2026-11-09 10:36 KST

- The earlier key-missing observation applied to run 42540030991 only, **not the later status**. In [run 42543904654](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/42543904654), SLOT A had a configured AES Secret (masked in logs), decrypted **six private inputs**, installed Blender 4.5.15, but stopped with `RuntimeError: BLOCKED_SOURCE_SHA: changed source .blend` before any model edit. Never reveal the Secret.
- [Run 42546429232](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/42546429232) selected SLOT C; A's decrypt, Blender and edit steps were skipped. Its success/green A job is **not** Daytona geometry proof.
- Correct A blocker: `BLOCKED_HOSTED_INPUT_STALE`, **not missing key**. Bundle SHA256 `502cf59b193ad45345ca50e6dd093eb88c92248ae044a99d9860991d6fffd520` predates current accepted R45 .blend SHA256 `224131c7adc928d5d6f0377d030d5a350c59b8664c13303a2731d6dfc6e9a722`.
- Keep `inner_door=COVERED_PARTIAL_QA` from R45; no repeat dashboard/wheel/door edit. `visible_seat=NOT_STARTED` until current authenticated encrypted R45 scene and native seat identity are available. The entire car input is blocked, so do not mislabel each unexplored component as absent. No N100 Blender/render, new script, plaintext upload or synthetic source.
- Documentation-only correction; no hosted modeling/QA PASS, no duplicated competition points. `tools/car_modeling/hosted_jobs/slot_A.json` is **not** rewritten merely to trigger another stale public Actions run.
