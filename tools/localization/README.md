# OutRun 2006 localization tools

## Inspect

```bash
python tools/localization/txet_tool.py inspect "Text/English_Korean.bin"
```

## Lossless extraction and rebuild

```bash
python tools/localization/txet_tool.py extract "Text/English_Korean.bin" english_korean.json
python tools/localization/txet_tool.py rebuild english_korean.json rebuilt.bin
cmp "Text/English_Korean.bin" rebuilt.bin
```

A successful unchanged round trip must be byte-identical.

## Patch one simple string

```bash
python tools/localization/txet_tool.py patch \
  "Text/English_Korean.bin" \
  English_Korean.test.bin \
  --index 0 \
  --text "화면 위치"
```

The tool intentionally refuses records that contain multiple/special payload segments.

## Important

Creating a BIN with Korean text does not make the game display Hangul. The stock executable reduces UTF-16LE characters to one byte before the existing glyph renderer, and the stock font atlas does not contain Hangul. Runtime/font work is tracked in `docs/KOREAN_LOCALIZATION.md`.

## Runtime trace analysis

After a K1/K2/K3 test, analyze the game log with:

```bash
python tools/localization/analyze_korean_trace.py OutRun2006Tweaks.log \
  --json localization_work/trace.json \
  --markdown localization_work/trace.md
```

The analyzer extracts:
- observed text IDs and K2 proof override,
- context-sensitive IDs 96/97/279/280,
- K3 width strings and high-bit detection,
- observed glyph bytes,
- active font handle/texture/cell/scale/spacing state.

This is the preferred input to K3-A implementation decisions.


## Rework blast-radius QA

When repairing only part of an existing localized candidate, validate both normal source containment and collateral changes against the previous candidate:

```bash
python tools/localization/validate_clean_plate.py \
  source.png new_candidate.png edit_mask.png \
  --protected-mask protected.png \
  --baseline-candidate previous_candidate.png \
  --rework-mask intended_rework_mask.png \
  --report qa.json
```

The command fails when the new candidate changes any pixel outside `intended_rework_mask.png` relative to the previous candidate. This catches collateral regressions that ordinary source-vs-candidate edit containment cannot detect.

## Task lifecycle cleanup

To avoid filling persistent N100 storage with short-lived A/B/C jobs, use
`post_task_cleanup.py` for **N100 fallback tasks only**:

```bash
python3 ~/n100-mcp/post_task_cleanup.py run --task-id A181 -- python3 /path/to/producer.py
```

`run` provides a uniquely marked task scratch directory as
`$OUTRUN_TASK_SCRATCH`/`$TMPDIR`, then deletes only that directory after a
**successful** command. Failed commands retain scratch for investigation.

When a new short-lived Git worktree is necessary, register it immediately:

```bash
python3 ~/n100-mcp/post_task_cleanup.py register-worktree \
  --base ~/work/outrun-a-next --path ~/work/outrun-temporary-role-C --task-id C299
# Produce + QA + commit + push + verify remote HEAD *before* cleanup.
python3 ~/n100-mcp/post_task_cleanup.py finish-worktree \
  --path ~/work/outrun-temporary-role-C
```

The non-force worktree finalizer requires explicit registration, clean Git
status including untracked files, no process using the worktree, and a HEAD
reachable from an `origin/*` remote-tracking branch. Otherwise it skips
removal. To preview potential stale registered worktrees:

```bash
python3 ~/n100-mcp/post_task_cleanup.py prune --dry-run
```

The current account's `outrun-task-cleanup.timer` is configured to recheck
registered worktrees every hour, no earlier than 24 hours after registration.
It never removes unknown folders, active worktrees, unpushed work, Git
evidence, or failed scratch by default. Successful GitHub-hosted jobs use
ephemeral runners; GPT-local jobs should clean their own local
`TemporaryDirectory` in `finally`.
