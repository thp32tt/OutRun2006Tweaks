# 5000-cycle DX9Ex HUD static audit — 2026-10-08

- Exact GitHub material SHA is the authority.
- Dedicated `DX9Ex HUD 5000 Static Review` workflow, independent of the previous 1000-cycle workflow.
- **5000** automated passes, each re-running the ten HUD source families, original 71 canonical producer CALL contract, DDS fast-loader source contract, queue semantic ordering and sampled targeted corruption. This is 5000 automated checks, **not** 5000 unique defects or in-headset tests.
- Each **30 cycles** archive `checkpoint-0030.json` through `checkpoint-4980.json`; final `checkpoint-5000.json`. **167 JSON checkpoint files plus summary.json** in run artifact. A checkpoint has exact source digest, SHA, findings and rejected mutation, even on test failure.
- `family_counts` must report **500 per each of 10 families**, and all mutants must be rejected. A source baseline error is FAIL, not success.
- Separate known open gaps: F1 rank 1st–3rd producer's one-tail assumption, F2 ScreenOverlay2D active policy vs header, F3 menu/car replacement DDS loaded pixel evidence; prior 00519 runtime failures remain open.
- Never assert a visually correct Quest 3/VDXR headset frame based on repeated CI; `RUNTIME_VALIDATION=UNTESTED` unless hardware actually tested.
- GitHub Actions artifacts are retained 90 days; important conclusion and SHA should be committed as a small immutable run-result record after the exact run ends, not mistaken for a material source commit.
