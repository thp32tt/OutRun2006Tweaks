FROM python:3.12-slim
WORKDIR /opt/c-salvage
COPY requirements.txt /tmp/c-salvage-requirements.txt
RUN pip install --no-cache-dir -r /tmp/c-salvage-requirements.txt
COPY c_salvage_compose.py c_salvage_plate.py c_salvage_worker.py psd_layer_workbase.py /opt/c-salvage/
COPY PSD_UPSTREAM_FULL_INDEX.json /opt/c-salvage/localization/graphics/plate_library/PSD_UPSTREAM_FULL_INDEX.json
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
ENTRYPOINT ["python", "/opt/c-salvage/c_salvage_worker.py"]
CMD ["--input-root", "/data/image-src", "--output-root", "/data/c-salvage", "--repo-root", "/opt/c-salvage", "--masks-dir", "/data/c-salvage/masks", "--plate-jobs-dir", "/data/c-salvage/plate_jobs", "--recipes-dir", "/data/c-salvage/recipes", "--bundle-root", "/data/c-salvage/bundles", "--max-per-cycle", "10", "--interval-seconds", "1800", "--loop"]
