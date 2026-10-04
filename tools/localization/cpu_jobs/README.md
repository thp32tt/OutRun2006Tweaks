# Localization CPU job slots

These role files are execution slots for CPU-heavy localization work that should not run on the N100 controller.

- `A.py`, `B.py`, `C.py`: deterministic role-specific scripts. Creating or replacing one triggers `.github/workflows/localization-cpu-worker.yml`.
- The hosted worker supplies Python 3.12, Pillow and NumPy.
- Scripts may read any repository localization source required for the role, but writes are restricted by the workflow to:
  - `localization/graphics/hd_candidates/`
  - `localization/graphics/role_A/`
  - `localization/graphics/role_B/`
  - `localization/graphics/role_C/`
  - `localization/graphics/worker_results/`
- Do not update `asset_queue.csv`, `resume_state.json`, `progress/`, `WORKLOG.md`, runtime/source code, or controller state from a CPU slot. The role fetches the worker result and performs those small shared-state updates separately.
- A slot is compute transport, not an authoritative work queue. `localization/graphics/asset_queue.csv` remains the only graphics work queue.
- N100 heavy Python is fallback-only when the required data is local-only/runtime-only or the hosted worker is unavailable.
