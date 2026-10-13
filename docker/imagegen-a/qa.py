"""Mechanical checks are separate from model visual self-QA and game approval."""
import hashlib
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def inspect(source, candidate, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as a, Image.open(candidate) as b:
        a.load(); b.load()
        reasons = []
        if b.format != "PNG": reasons.append("OUTPUT_NOT_PNG")
        if a.size != b.size: reasons.append("DIMENSION_MISMATCH")
        if "A" not in b.getbands(): reasons.append("ALPHA_CHANNEL_MISSING")
        aa, bb = a.convert("RGBA"), b.convert("RGBA")
        if aa.getchannel("A").getextrema()[0] < 255 and bb.getchannel("A").getextrema()[0] == 255:
            reasons.append("TRANSPARENCY_LOST")
        if a.size == b.size and not ImageChops.difference(aa, bb).convert("RGB").getbbox() and aa.getchannel("A").tobytes() == bb.getchannel("A").tobytes():
            reasons.append("UNCHANGED_SOURCE")
        for scale in (1, .75, .5):
            # Scaling only for labeled review; candidate bytes are never altered.
            w, h = int(a.width * scale), int(a.height * scale)
            board = Image.new("RGB", (w * 2, h + 40), "#606060")
            for x, im, label in ((0, aa, "ENGLISH SOURCE"), (w, bb, "GENERATED CANDIDATE")):
                display = im.copy(); display.thumbnail((w, h))
                board.paste(display, (x, 40), display)
                ImageDraw.Draw(board).text((x+10, 12), label, fill="white")
            board.save(output / f"compare_{int(scale*100)}.jpg", quality=93)
        return {"source_sha256": sha(source), "candidate_sha256": sha(candidate),
                "source_size": list(a.size), "candidate_size": list(b.size),
                "mechanical": "FAIL" if reasons else "PASS", "failures": reasons,
                "protected_pixels": "UNVERIFIED_NO_APPROVED_MASK",
                "independent_qa": "NOT_RUN", "DDS": "NOT_BUILT",
                "RUNTIME_VALIDATION": "UNTESTED", "official_promotion": False}
