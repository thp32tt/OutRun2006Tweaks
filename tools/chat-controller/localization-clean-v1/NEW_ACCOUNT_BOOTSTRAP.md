# New-account bootstrap — Korean localization clean-v1

Use a new ChatGPT Project. Do not import the old project's memory, chat history, controller prompts, or accumulated exception rules.

## Project instruction

Keep the project instruction short:

> Work only on thp32tt/OutRun2006Tweaks branch korean-localization-20260928-clean-v1. GitHub is the durable source of truth. For localization tasks, read docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md first and follow the repository state. Do actual work when executable work exists; do not stop at planning or inspection. Do not touch VR/FFB.

Do not add controller state-machine rules to the ChatGPT Project instruction. Those belong in the repository/controller.

## Account setup

1. Connect GitHub read/write access for thp32tt/OutRun2006Tweaks.
2. Create the new ChatGPT Project and apply only the short instruction above.
3. Deploy the Portainer stack from this branch.
4. Set LOCALIZATION_PROJECT_URL to the new project's full URL.
5. Start with AUTO_SEND=false.
6. Open noVNC on port 6081 and log in with the new ChatGPT account.
7. Manually send OutRun 한글화 A 실행 once and confirm the account can read/write the target branch.
8. Set AUTO_SEND=true and redeploy.

The controller deliberately has no C0-C6 schema, EVENT_ID, rollover event model, per-stage gate, or production-latch policy.
