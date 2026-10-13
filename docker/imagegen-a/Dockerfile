FROM mcr.microsoft.com/playwright/python:v1.63.0-noble

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    DISPLAY=:99

RUN apt-get update && apt-get install -y --no-install-recommends xvfb x11-utils x11vnc openbox novnc websockify tini curl ca-certificates gnupg wget && rm -rf /var/lib/apt/lists/*
RUN wget -qO- https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] https://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && apt-get update && apt-get install -y --no-install-recommends google-chrome-stable && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/outrun

COPY requirements.txt /opt/outrun/requirements.txt
RUN python -m pip install --upgrade pip --index-url https://pypi.org/simple && python -m pip install --no-cache-dir --prefer-binary --index-url https://pypi.org/simple -r /opt/outrun/requirements.txt

RUN mkdir -p /opt/outrun/app && touch /opt/outrun/app/__init__.py
COPY controller.py qa.py fetch_source.py /opt/outrun/app/
COPY input/prompt.txt input/source.json /opt/outrun/input/
COPY entrypoint.sh /opt/outrun/entrypoint.sh
RUN chmod +x /opt/outrun/entrypoint.sh
ENTRYPOINT ["/usr/bin/tini","--","/opt/outrun/entrypoint.sh"]

