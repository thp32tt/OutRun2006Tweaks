# Localization v2 migration

## Controller rules

A producer:
- owns even shard assets
- creates material commits only

B producer:
- owns odd shard assets
- creates material commits only

C QA:
- validates A/B material commits
- blocks next wave until PASS/REWORK/HOLD

## State lookup fallback

TASK_ID resolution order:

exact TASK_ID
TASK_ID.*
dispatch
reconcile
rollover
LANE + number
number

Lookup errors:
- 404/path miss: continue fallback
- permission/auth error: report separately

This migration does not remove existing controller or localization output.
