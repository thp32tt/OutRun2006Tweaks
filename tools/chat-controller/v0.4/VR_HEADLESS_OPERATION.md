# VR controller: headless single-slot operation

The VR Portainer stack defaults to `VR_BROWSER_MODE=headless` and `CHAT_SLOTS=1`.
It runs the existing Google Chrome Chromium engine in modern headless mode, not a
different browser or a separate login profile. Xvfb, Openbox, x11vnc and websockify
are not launched. The existing Docker data/log volumes and /data/browser-profile
are unchanged; queue, cookies and login/session stores are not intentionally cleared.

Deploy from `chat-controller-downloads` using
`tools/chat-controller/v0.4/docker-compose.portainer-vr.yml`, Pull and redeploy
with image rebuild. Check /status for browser mode and one prepared tab; /healthz
is lightweight HTTP liveness, not evidence of successful dispatch. The runtime
heartbeat watchdog remains active. Port 6080 is reserved for explicit GUI maintenance.

If login expires: stop automatic sending with AUTO_SEND=false and set
VR_BROWSER_MODE=gui in Portainer, redeploy the SAME stack and login using noVNC
(http://192.168.0.48:6080/vnc.html). Then set VR_BROWSER_MODE=headless and
AUTO_SEND=true and redeploy again. Do not launch a separate stack against the same
profile volume. If the login provider requires GUI operation, leave GUI mode on
with a single slot; do not circumvent authentication or account limits.

The deployed browser must be checked on N100 for login compatibility, process
count and CPU load; passing source/CI tests does not establish live operation.
