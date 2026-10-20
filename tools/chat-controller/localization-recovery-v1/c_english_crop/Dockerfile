# GitOps C slot: native, unmodified English text crops from the 108
# manifest-verified unsplit original HD PNGs and existing verified DDS set.
# No ChatGPT tabs, generative images, DDS writes or A/B task access.
FROM python:3.12-slim
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    TZ=Asia/Seoul
RUN apt-get update \
 && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng tesseract-ocr-jpn \
 && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --no-cache-dir "Pillow==12.3.0" "numpy==2.3.5"
WORKDIR /app
COPY c_english_crop/*.py /app/
RUN python3 -m py_compile /app/*.py \
 && tesseract --list-langs 2>&1 | grep -q eng \
 && tesseract --list-langs 2>&1 | grep -q jpn
USER 1002:1002
ENTRYPOINT ["python3", "/app/loop.py"]
CMD ["--interval-seconds", "60", "--max-per-cycle", "10"]
