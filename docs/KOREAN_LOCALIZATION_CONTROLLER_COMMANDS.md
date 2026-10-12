# OutRun localization controller — current commands (2026-10-12)

Authoritative policy: docs/KOREAN_LOCALIZATION_HD_PNG_IMAGEGEN_AND_FAST_QA_20261012.md; read latest docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md FIRST.

| ACTIVE tab | Schedule | Role |
| --- | --- | --- |
| A | :00 | Odd HD DDS→READABLE PNG uploaded as real ChatGPT image input→native ImageGen→ROI fit→trial DDS |
| B | :30 | Even HD DDS→READABLE PNG uploaded as real ChatGPT image input→native ImageGen→ROI fit→trial DDS |
| C1 | :10/:40 | Batch QA of 4–8 new A/B saved DDS candidates in one run; no image generation |

Allowed messages: OutRun 한글화 A 실행 / OutRun 한글화 B 실행 / OutRun 한글화 C1 실행.

**C2 tab, schedule, command and prompt removed.** Historic C2 evidence remains readable, but no new C2 PASS may be issued. No C1 self-approval of its historical own production; preserve C3 and user game revalidation. Preserve old owner assignments/P0/P1. The controller MUST use original HD DDS dimensions, format, orientation and source UI cells; a generated larger PNG is fitted by proportional resize and XY translation into original cells. Fail readable-letter damage, UI cell overflow/collision/clipping, original protected art change or broken stored DDS. Minor optical variance is accepted. Never claim that only displaying a GitHub image meant the image was actually attached to native ChatGPT ImageGen. Verification receipt/thumbnail required. Old C2-dependent export gates must not be bypassed. New UI tab deletion requires controlled Portainer redeploy; policy updates alone do not close live tabs. Backup branch: backup/korean-controller-policy-pre-hd-imagegen-20261012.
