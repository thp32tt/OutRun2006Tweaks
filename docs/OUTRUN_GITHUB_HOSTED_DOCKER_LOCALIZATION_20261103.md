# Historical GitHub-hosted Docker experiment (retired 2026-11-03 KST)

This document described an earlier design where a GitHub Actions runner built a
Docker image and performed Korean localization QA. The user clarified that this
was **not** the intended architecture. Do not deploy it.

## Current design
- Existing user's Portainer Docker is the low-impact GitHub control/status
  monitor only: see [controller runbook](../tools/chat-controller/localization-recovery-v1/GITHUB_GITOPS_RUNBOOK_20261103.md) on branch
  localization-controller-recovery-20260928.
- Heavy localization QA and TEST_ONLY DDS packaging run as **normal Python
  processes directly on a GitHub-hosted runner**, NOT inside Docker.
- GitHub compute workflow (default master + asset branch):
  .github/workflows/outrun-korean-github-compute.yml.
- First verified GitHub Python-only run: 41544581244 SUCCESS; native Q012,
  Q089, Q104 DDS TEST_ONLY, with source/visual/game release unapproved.
- Legacy .github/workflows/outrun-korean-docker-auto.yml is retired
  (no cron/push run; dispatch only displays a notice).
- A/B source candidates 954/954 are **not yet present as GitHub job input**.
  This setup is functioning as a 3-DDS static QA/test package pipeline only.
  Full automatic localization remains gated on the missing inputs.
- To achieve ZERO N100 usage, stop the original Portainer container; GitHub's
  existing daily schedule and asset push triggers will still run independently.
  Leaving the existing Docker running uses a little RAM/CPU for GitHub API
  polling, now capped by Compose at 96 MiB/0.1 CPU; no local DDS/image work.

## Non-negotiable
Never treat static DDS QA as visual C1/C3 or in-game approval; the package
remains TEST_ONLY. Do not erase old N100 image assets or named Portainer volumes.
