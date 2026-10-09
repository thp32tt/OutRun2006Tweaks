FROM python:3.12-slim-bookworm
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 DISPLAY=:99
RUN apt-get update && apt-get install -y --no-install-recommends xvfb x11vnc openbox novnc websockify tini curl ca-certificates gnupg wget procps && rm -rf /var/lib/apt/lists/*
RUN wget -qO- https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] https://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && apt-get update && apt-get install -y --no-install-recommends google-chrome-stable && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir playwright==1.55.0
WORKDIR /opt/outrun
RUN mkdir -p app prompts && touch app/__init__.py
COPY src/controller.py.part* /tmp/controller-parts/
RUN cat /tmp/controller-parts/controller.py.part* > app/controller.py && python -m py_compile app/controller.py && rm -rf /tmp/controller-parts
COPY localization_A.md localization_B.md localization_C.md /opt/outrun/prompts/
COPY entrypoint.direct.sh /opt/outrun/entrypoint.sh
RUN chmod +x /opt/outrun/entrypoint.sh && printf '%s\n' '#!/bin/sh' 'set -eu' '[ "${CONTROLLER_MODE:-localization}" = localization ] || { echo "Localization-only image" >&2; exit 64; }' 'export CONTROLLER_MODE=localization QUEUE_MODE=true LOCALIZATION_PARALLEL=true CHAT_SLOTS=4' 'exec /opt/outrun/entrypoint.sh' > /opt/outrun/localization-only.sh && chmod +x /opt/outrun/localization-only.sh
ENTRYPOINT ["/usr/bin/tini", "--", "/opt/outrun/localization-only.sh"]
