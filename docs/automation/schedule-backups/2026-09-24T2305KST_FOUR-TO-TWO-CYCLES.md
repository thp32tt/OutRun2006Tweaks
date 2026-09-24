# Automation schedule backup — 2026-09-24 23:05 KST

This snapshot records the active 4-task Chat schedule immediately before consolidation to two full-cycle tasks.

## Active tasks

| Role | Task ID | Title | Schedule |
|---|---|---|---|
| A | 6ab45eaa511c8191ab7d5984495d7e93 | OutRun A R51 Matrix Guard (Chat) | hourly :00 Asia/Seoul |
| B | 6ab45ebf6ba08191a59cb6d49c251637 | OutRun B Parallel VR Matrix Review (Chat) | hourly :20 Asia/Seoul |
| C | 6ab45ed52f548191b94c90af792116fb | OutRun C HMD Matrix Gate (Chat) | hourly :35 Asia/Seoul |
| D | 6ab45eec82dc8191b63632bdad258a7d | OutRun D Parallel HMD Matrix Integrate (Chat) | hourly :45 Asia/Seoul |

## Shared contract at backup

- Protected runtime baseline: R51 17ad376bfdf7939f0851c0c629e4fa094a84f28a.
- Integration branch: vr-d3d9ex-focus.
- Production integration WIP=1.
- Up to six HMD test slots: A_CONTROL DX9Ex, B_HUD, C_FLARE, D_PERF, E_DXVK, F_DX12.
- HUD/flare must not block performance, DXVK or DX12.
- DXVK SAFE precedes multiview optimization; DX12/D3D9On12 resumes from CreateDevice/resource compatibility.
- Self-hosted PC runner disabled unless explicitly authorized.
- A/B/C are review/validation roles; D is the sole production writer/integrator/package writer in this snapshot.

## Reason for replacement

The four-role :00/:20/:35/:45 chain introduces handoff latency and can leave most of an hour idle between discovery, implementation, validation and integration. It is replaced by two independent full development cycles per hour at :00 and :30, with remote GitHub claim/CAS and production WIP=1 preventing writer collisions.
