FROM python:3.12-slim
RUN python -m pip install --no-cache-dir "Pillow==11.3.0"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /workspace
ENTRYPOINT ["python", "/workspace/tools/localization/github_docker_qa.py"]
