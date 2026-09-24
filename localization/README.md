# Localization data

This directory is the canonical resumable state for the Korean localization prototype.

- `progress.json`: machine-readable counters, gates and current resume pointer.
- `resume_state.json`: exact continuation order, source archive identity and next actions.
- `WORKLOG.md`: append-only human-readable checkpoint history.
- `text/korean_all.jsonl`: canonical 1,356-row translation state. Source game text is not redistributed; each row contains an ID, source-record hash, Korean text and review status.
- `text/special_records.json`: translations for multi-segment records whose opaque tail bytes must be preserved.
- `text/config_text_ko.tsv`: configurator strings.
- `graphics/inventory.csv`: all 243 DDS identities, dimensions and hashes.
- `graphics/visual_review.csv`: all 243 DDS localization decisions.
- `graphics/asset_queue.csv`: 141 actionable graphics/font rows with resumable artwork/transcription status.
- `tools/localization/build_korean_bin.py`: rebuilds a Korean draft BIN only when source hashes match.
- `tools/localization/verify_state.py`: validates text IDs/statuses, special records, DDS hashes/actions and progress counters.
- `.github/workflows/localization-state.yml`: automatically runs the state validator when localization data changes.

Text statuses: `reviewed`, `reviewed_special`, `draft`, `blocked_null`.
Graphics actions: `localize_text`, `preserve_brand_song_credit`, `font_pipeline`, `hangul_name_entry`, `zoom_review`, `no_localization`.

The generated Korean BIN is a data-validation artifact until the runtime Unicode/glyph path is implemented. Do not replace a playable game's text BIN with it yet.
