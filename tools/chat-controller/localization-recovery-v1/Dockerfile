FROM mcr.microsoft.com/playwright/python:v1.63.0-noble

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    DISPLAY=:99 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120

RUN apt-get update && apt-get install -y --no-install-recommends xvfb x11vnc openbox novnc websockify tini curl ca-certificates gnupg wget tesseract-ocr tesseract-ocr-eng python3-numpy python3-pil && rm -rf /var/lib/apt/lists/*
RUN wget -qO- https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] https://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && apt-get update && apt-get install -y --no-install-recommends google-chrome-stable && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/outrun

COPY requirements.txt /opt/outrun/requirements.txt
RUN python -m pip install \
      --no-cache-dir \
      --prefer-binary \
      --retries 5 \
      --timeout 120 \
      --index-url https://pypi.org/simple \
      -r /opt/outrun/requirements.txt

RUN mkdir -p /opt/outrun/app /opt/outrun/prompts /tmp/controller-parts && touch /opt/outrun/app/__init__.py
COPY src/controller.py.part* /tmp/controller-parts/
COPY chrome_maintenance.py /opt/outrun/app/chrome_maintenance.py
RUN mkdir -p /opt/outrun/c_english_crop
COPY c_english_crop/*.py /opt/outrun/c_english_crop/
RUN python -m py_compile /opt/outrun/c_english_crop/*.py && tesseract --list-langs 2>&1 | grep -q eng
COPY chrome-cache-clean.sh /opt/outrun/chrome-cache-clean.sh
RUN cat /tmp/controller-parts/controller.py.part* > /opt/outrun/app/controller.py && python -m py_compile /opt/outrun/app/controller.py && rm -rf /tmp/controller-parts

# Exact pinned controller source is patched at build time; never alter a live container.
# Build fails closed if upstream Python anchors change.
COPY controller_png_attach.py /opt/outrun/app/controller_png_attach.py
COPY tile_batch_queue.py /opt/outrun/app/tile_batch_queue.py
COPY tile_orientation_policy.py /opt/outrun/app/tile_orientation_policy.py
COPY ab_batch_queue.py /opt/outrun/app/ab_batch_queue.py
COPY text_roi_queue.py /opt/outrun/app/text_roi_queue.py
COPY project_library_gate.py /opt/outrun/app/project_library_gate.py
COPY patch_controller_png_upload.py /tmp/patch_controller_png_upload.py
RUN python /tmp/patch_controller_png_upload.py /opt/outrun/app/controller.py \
 && python -m py_compile /opt/outrun/app/controller.py /opt/outrun/app/controller_png_attach.py /opt/outrun/app/ab_batch_queue.py /opt/outrun/app/text_roi_queue.py /opt/outrun/app/tile_orientation_policy.py /opt/outrun/app/project_library_gate.py \
 && rm -f /tmp/patch_controller_png_upload.py

# Add the third logical C tab to the SAME controller after A/B native PNG wiring.
# This does not spawn a second service; runtime deployment remains operator-manual.
COPY patch_controller_c_slot.py /tmp/patch_controller_c_slot.py
RUN python /tmp/patch_controller_c_slot.py /opt/outrun/app/controller.py \
 && python -m py_compile /opt/outrun/app/controller.py \
 && rm -f /tmp/patch_controller_c_slot.py

COPY v2_automation_policy.py /opt/outrun/app/v2_automation_policy.py
COPY v2_docker_policy.json /opt/outrun/v2_docker_policy.json
RUN python -m py_compile /opt/outrun/app/v2_automation_policy.py
COPY entrypoint.sh /opt/outrun/entrypoint.sh
COPY prompts/localization_A.md /opt/outrun/prompts/localization_A.md
COPY prompts/localization_B.md /opt/outrun/prompts/localization_B.md
COPY prompts/localization_C.md /opt/outrun/prompts/localization_C.md
COPY prompts/localization_C1.md /opt/outrun/prompts/localization_C1.md
COPY prompts/localization_C2.md /opt/outrun/prompts/localization_C2.md

RUN chmod +x /opt/outrun/entrypoint.sh /opt/outrun/chrome-cache-clean.sh
ENTRYPOINT ["/usr/bin/tini","-g","--","/opt/outrun/entrypoint.sh"]