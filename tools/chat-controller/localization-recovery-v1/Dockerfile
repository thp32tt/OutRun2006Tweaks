FROM mcr.microsoft.com/playwright/python:v1.63.0-noble

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    DISPLAY=:99

RUN apt-get update && apt-get install -y --no-install-recommends xvfb x11vnc openbox novnc websockify tini curl ca-certificates gnupg wget && rm -rf /var/lib/apt/lists/*
RUN wget -qO- https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] https://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && apt-get update && apt-get install -y --no-install-recommends google-chrome-stable && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/outrun

COPY requirements.txt /opt/outrun/requirements.txt
RUN python -m pip install --upgrade pip --index-url https://pypi.org/simple && python -m pip install --no-cache-dir --prefer-binary --index-url https://pypi.org/simple -r /opt/outrun/requirements.txt

RUN mkdir -p /opt/outrun/app /opt/outrun/prompts /tmp/controller-parts && touch /opt/outrun/app/__init__.py
COPY src/controller.py.part* /tmp/controller-parts/
COPY chrome_maintenance.py /opt/outrun/app/chrome_maintenance.py
COPY chrome-cache-clean.sh /opt/outrun/chrome-cache-clean.sh
RUN cat /tmp/controller-parts/controller.py.part* > /opt/outrun/app/controller.py && python -m py_compile /opt/outrun/app/controller.py && rm -rf /tmp/controller-parts

COPY entrypoint.sh /opt/outrun/entrypoint.sh
COPY prompts/localization_A.md /opt/outrun/prompts/localization_A.md
COPY prompts/localization_B.md /opt/outrun/prompts/localization_B.md
COPY prompts/localization_C.md /opt/outrun/prompts/localization_C.md
COPY prompts/localization_C1.md /opt/outrun/prompts/localization_C1.md
COPY prompts/localization_C2.md /opt/outrun/prompts/localization_C2.md

RUN chmod +x /opt/outrun/entrypoint.sh /opt/outrun/chrome-cache-clean.sh
ENTRYPOINT ["/usr/bin/tini","--","/opt/outrun/entrypoint.sh"]
