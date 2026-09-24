# Localization data

This directory is the canonical resumable state for the Korean localization prototype.

- `progress.json`: machine-readable counters, gates and current resume pointer.
- `resume_state.json`: exact continuation order, source archive identity and next actions.
- `WORKLOG.md`: append-only human-readable checkpoint history.
- `text/korean_*.jsonl`: translation chunks. Source game text is not redistributed; each row contains an ID, source-record hash, Korean text and review status.
- `text/special_records.json`: translations for multi-segment records whose opaque tail bytes must be preserved.
- `text/config_text_ko.tsv`: configurator strings.
- `graphics/inventory.csv`: DDS identity, dimensions and hashes.
- `graphics/visual_review.csv`: all 243 DDS assets and localization action.
- `tools/localization/build_korean_bin.py`: rebuilds a Korean draft BIN only when source hashes match.

Text statuses: `reviewed`, `reviewed_special`, `draft`, `blocked_null`.
Graphics actions: `localize_text`, `preserve_brand_song_credit`, `font_pipeline`, `hangul_name_entry`, `zoom_review`, `no_localization`.

The generated Korean BIN is a data-validation artifact until the runtime Unicode/glyph path is implemented. Do not replace a playable game's text BIN with it yet.
