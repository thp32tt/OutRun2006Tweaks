FROM python:3.12-slim
WORKDIR /repo
COPY docker/localization-production/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY tools/localization /repo/tools/localization
ENV PYTHONDONTWRITEBYTECODE=1
ENTRYPOINT ["python", "tools/localization/plate_library.py"]
CMD ["audit"]
