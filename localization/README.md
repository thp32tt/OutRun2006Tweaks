# Localization data

This directory is the resumable state for the Korean localization prototype.

- `progress.json`: canonical machine-readable progress counters and next pointers.
- `resume_state.json`: exact continuation instructions and source archive hash.
- `WORKLOG.md`: append-only checkpoint log.
- `text/korean_*.tsv`: translated ID chunks bound to source hashes.
- `text/config_text_ko.tsv`: launcher/configurator translation.
- `graphics/*.csv`: DDS inventory/classification chunks.

Statuses: `todo`, `draft`, `reviewed`, `blocked_special`, `blocked_null`, `inspect`, `localized`, `deferred_nonlocalized`.
