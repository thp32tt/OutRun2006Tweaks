"""Static regression for the one-stack/one-container localization deployment."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

def test():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    assert list(services) == ["outrun-chat-controller-localization-recovery"], services.keys()
    svc = services["outrun-chat-controller-localization-recovery"]
    env = svc["environment"]
    assert env["CHAT_SLOTS"] == "3"
    assert env["AUTO_SEND"] == "true"
    assert env["OUTRUN_CROP_ENABLED"] == "true"
    assert env["OUTRUN_ROI_BRIDGE_ENABLED"] == "true"
    assert env["OUTRUN_AB_TEXT_ROI_QUEUE"] == "true"
    assert env["SCHEDULE_MINUTES"] == "0,10,30,40"
    assert env["OUTRUN_KR_V2_AUTO_COMPOSE"] == "false"
    assert env["OUTRUN_KR_V2_AUTO_DEPLOY"] == "false"
    assert svc["ports"] == ["6083:6080", "8788:8787"]
    mounts = [v for v in svc["volumes"] if isinstance(v, dict)]
    sources = {v.get("source") for v in mounts}
    assert "/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only" in sources
    assert "/home/chatgpt-runner2/work/c_salvage_text_roi/source_full_20261012" in sources
    assert any("MASTER_CROP_MANIFEST_255.json" in str(x) for x in sources)

    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "tesseract-ocr-eng" in dockerfile
    assert "COPY c_english_crop/*.py /opt/outrun/c_english_crop/" in dockerfile
    assert 'ENTRYPOINT ["/usr/bin/tini","-g","--","/opt/outrun/entrypoint.sh"]' in dockerfile

    req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "playwright==1.63.0" in req
    assert "Pillow==" not in req and "numpy==" not in req
    assert "python3-numpy" in dockerfile and "python3-pil" in dockerfile
    entry = (ROOT / "entrypoint.sh").read_text(encoding="utf-8")
    assert "/opt/outrun/c_english_crop/loop.py" in entry
    assert "/opt/outrun/app/crop_to_imagegen_queue.py" in entry
    assert "OUTRUN_CROP_ENABLED" in entry
    print("SINGLE_PORTAINER_CONTAINER_PASS")

if __name__ == "__main__":
    test()
