# OutRun2006 Korean Localization Controller v2

Dedicated localization controller migration target.

Rules:
- Localization only
- A/B production lanes
- C QA barrier
- No VR/conversion runtime
- Existing v0.4 is preserved during migration

Migration changes:
- TASK lookup fallback chain:
  1. exact TASK_ID
  2. TASK_ID.* rollover variants
  3. dispatch records
  4. reconcile records
  5. rollover records
  6. lane + numeric id
  7. numeric id
- 404 lookup misses continue fallback search
- permission failures are treated separately
