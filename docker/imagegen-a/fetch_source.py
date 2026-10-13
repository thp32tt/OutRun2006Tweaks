"""Download a pinned public GitHub PNG, atomically cache after SHA/decode checks."""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse
from urllib.request import urlopen
from PIL import Image

def fetch(manifest, directory):
    spec = json.loads(Path(manifest).read_text())
    url = spec["url"]
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "raw.githubusercontent.com":
        raise ValueError("SOURCE_HOST_NOT_ALLOWED")
    if not re.fullmatch(r"[0-9a-f]{40}", parsed.path.split("/")[3]):
        raise ValueError("SOURCE_COMMIT_NOT_PINNED")
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    name = spec["filename"]
    if Path(name).name != name: raise ValueError("SOURCE_PATH_INVALID")
    target = directory / name
    expected = spec["sha256"]
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
        return target
    temporary = target.with_suffix(".download")
    try:
        with urlopen(url, timeout=60) as response, temporary.open("wb") as handle:
            total = 0
            while chunk := response.read(65536):
                total += len(chunk)
                if total > 32 * 1024 * 1024: raise ValueError("SOURCE_TOO_LARGE")
                handle.write(chunk)
        if hashlib.sha256(temporary.read_bytes()).hexdigest() != expected:
            raise ValueError("SOURCE_SHA_MISMATCH")
        with Image.open(temporary) as im:
            im.load()
            if im.format != "PNG" or list(im.size) != spec["size"] or im.mode != "RGBA":
                raise ValueError("SOURCE_PNG_INVALID")
        temporary.replace(target)
        return target
    finally:
        temporary.unlink(missing_ok=True)
