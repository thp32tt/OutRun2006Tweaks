# DX9Ex R84 interrupted-session recovery — 2026-10-09 KST

Task context: `DX9EX-R84-PORT-SEAMS-001`; source authority `thp32tt/OutRun2006Tweaks` / `vr-d3d9ex-focus`. The external Docker worker remains separately authoritative for unattended execution; this file describes only directly observed GitHub work in this chat. Existing five-minute **active development checkpoints** are retained, not replaced by repeat-verification loops.

## 18:20–18:25 C0/C1: recover stalled terminal task
- GitHub source HEAD before restart: `77e8a45ea8ea4f05580a78871a8d9931c72a7b76`, committed at 15:35:39 KST. No newer DX9Ex commit was found at inspection.
- Exact matching **DX9Ex Active Validation** 37894349126 and **Domain Isolation Guard** 37894349056: both SUCCESS. Hosted policy, x86 game, x64 host, full-chain, package all SUCCESS. Package artifact 11598654704, sha256:19159c1b26f9d43898fc1ac8c06d4737dd7b1bdc51971190aa4cbf9e42fbb80f.
- Completed missing C6 run record `docs/automation/runs/DX9EX-R84-R32-R9-RIGHT-SYNC-OWNER-20261009.json` (commit `53de6fc3292bb54792535223366b9beacd43feaa`). This is **not** a new material or score item.
- Remaining queue `DX9EX-R84-PORT-SEAMS-001` READY, R32/R31 split/CMake cleanup pending; Gate0 and R84 inventory DONE. HMD and actual Docker running state not asserted.

## 18:25–18:30 C2: resume a single bounded new owner seam
- Work item `DX9EX-R84-R32-R9-DEPTH-WRITE-OWNER-20261009`: exact R9 main depth-content write notification `R9NoteMainDepthContentWrite` remains the lower side effect. R32 review only delegates through an R30 support API so later independent-TU separation will not reach the private lower R9 symbol.
- Four paths: `src/vr/core/r30_support_api.hpp`, `src/vr/d3d9/stereo_renderer_r30.cpp`, `src/vr/d3d9/stereo_renderer_r32.cpp`, `tools/verify_vr_refactor_contract.py`. One full direct R9 call is replaced by one forwarding call, without new policy, duplicating notification, adding epochs, changing HUD or adjusting resource/pose lifetime.
- Fail-closed verifier requires exact forwarding and detects both erased lower notification and R32 bypass. C3 hosted DX9Ex/Domain results **PENDING** until exact material SHA workflows finish. `RUNTIME_VALIDATION=UNTESTED`; no Quest 3/VDXR inference.
- Next checkpoint: log only actual CI results or source repair, not fabricated time intervals or a repeated unchanged-source verifier run.
