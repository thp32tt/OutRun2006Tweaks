# Localization recovery baseline

This branch restores the controller runtime to the exact state immediately before producer E was introduced.

- Controller baseline: `42e3410d9582b85d74a51435188905c5bbd27feb`
- First E controller commit: `e34492f6024c3ef20c65dcfa2a14bcdee73776db`
- Localization governance baseline: `a7bbbdbbbb77825fc077e577a574325119032364`
- First three-producer localization governance commit: `b93a0df64c6bc8619c66c59913789f15212e3c0b`

## Exact pre-E behavior

- Active localization lanes are A, B and C only.
- A uses the odd-index primary shard in `localization/graphics/asset_queue.csv`.
- B uses the even-index primary shard in `localization/graphics/asset_queue.csv`.
- C is an independent batched QA consumer and shared-state merger.
- A and B continue after their own durable commits; C does not act as a wave barrier in this baseline.
- Producer commits leave `automation_validation=PENDING` with `validation_mode=C_BATCH_GATE`; C owns final automation validation.
- GitHub `korean-localization-clean` HEAD is the state/progress/QA SSOT.
- N100/local clones and remembered chat progress are not authoritative.
- Runtime validation stays `UNTESTED` unless actually performed.
- No producer E prompt, route or modulo-3 shard is active in this controller baseline.

## Preservation

The restore changes governance/controller files forward in history. Existing translation data, DDS outputs, QA records, WORKLOG entries and historical run records are not reset or deleted.
