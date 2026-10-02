# v0.4 compatibility notice

v0.4 controller logic is retired. This directory is retained only because existing Portainer stacks may still reference its compose path.

The v0.4 localization and VR compose files now build ../v0.5. Do not deploy the old v0.4 Dockerfile or copy old prompt/state rules into the new controller.

Canonical deployment documentation: ../v0.5/DEPLOY_PORTAINER.md
