# Korean localization HD coverage audit — 2026-10-21

This audit distinguishes the current A/B ImageGen production queue from total reviewed HD localization coverage.

## Verified source scope

- Verified native HD PNG sources: 108 files.
- Unique Q groups represented by those 108 files: 88.
- Reviewed translatable transcript segments in those Q groups: 745 segment occurrences.
- Unique reviewed Q + English translation pairs: 744.

## Crop / ROI coverage

- Readable native crop manifests: 242.
- Unique reviewed Q + English pairs with at least one crop: 178.
- Unique reviewed Q + English pairs with no crop yet: 566.
- Unique currently known crop occurrences by source SHA + English + bbox: 229.
  - clean non-edge occurrences: 158.
  - edge-review occurrences: 71.
- A/B production queue has 160 unique approved source keys:
  - 158 clean occurrences;
  - 2 rescued replacements for edge-review occurrences.
- Therefore unresolved edge-review occurrences are approximately 69 after accounting for the two rescued replacements.

## Production interpretation

The 160-row A/B queue is NOT the total Korean localization inventory. It is only the currently auto-approved native ROI subset.

A conservative lower bound for this 108-HD-source localization workload is:

- 229 already-located crop occurrences
- + 566 reviewed translation pairs that still have no crop
- = at least 795 ROI occurrences.

The true occurrence count can be higher because a reviewed phrase can appear more than once in the same source/variant.

At the time of this audit, A/B had completed 155 of the 160 currently approved ROI rows. The remaining five were blocked only by an inconsistent 2048px ROI validation cap; one valid native reference is 2142x219 RGBA. The controller validation was corrected to the same 8192px bound used by the attachment layer.

## Required next phase

1. Finish the last five current approved ROI rows.
2. Rework the ~69 unresolved edge-review occurrences into safe native crops where possible.
3. Create native-source crops for the 566 reviewed Q+English pairs that currently have no crop.
4. Feed each newly SHA-verified crop into A/B automatically.
5. Keep C1 independent QA and DDS/game approval separate.

An empty A/B queue or `EDGE_REVIEW_COMPLETE pending_after=0` must not be reported as total localization completion while the coverage backlog above remains.


## Source-variant occurrence recount — 2026-10-21

The earlier 795 figure was a conservative lower bound based on unique Q+English pairs plus already-located crop instances. A source-variant-aware recount against all 108 verified HD PNG rows gives the operational crop target used by the new C worker:

- reviewed phrase occurrences across the 108 actual source variants: **992**
- occurrences with an existing HD108 crop manifest at recount time: **225**
- occurrences still without a crop: **767**
- source PNGs still containing at least one uncovered reviewed phrase: **103 / 108**

This source-variant occurrence count is the production coverage denominator for C. Repeated Q groups across BASE/Keyboard/PlayStation/Switch/Xbox are separate source occurrences and must each reach crop coverage. C must continue cycling until `pending_phrases=0` and edge backlog is also zero. A one-time source `SCANNED` receipt is not completion.
