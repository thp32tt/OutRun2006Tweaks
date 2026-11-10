"""Import six manually generated Korean HD ROI PNGs into a TEST_ONLY GitHub runner.

No C1/C3 PASS is forged. No source asset or prior A/B PNG is overwritten.
Only an exact SHA-bound user ZIP on the separate QA branch is accepted.
"""
from __future__ import annotations
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from PIL import Image

INPUT_ZIP = ("hd-qa-queue-state/localization/automation_inputs/manual_user_20261110/"
             "OUTRUN_HD_MANUAL_SUBMISSION_QA_TEST_ONLY_20261110.zip")
INPUT_ZIP_SHA256 = "67522bd1ef6195362355b9e2c489a6418a823d1efe116a6f010f653e80001102"
SCHEMA = "outrun-uploaded-manual-images-independent-qa-v1"
EXPECTED = {
    "Q193_53d6085638ec9c80": (
        "e6df419c9300829cca7b10d4c1bf19686bed2ab958f437c968ef9ab5d8fbb8d3",
        (405, 137), "OUTRUN SHOWROOM", "아웃런 쇼룸"),
    "Q205_bf0d812a762a295e": (
        "9a7d7f71bccde056898167b340a9d4c19807e098d9d62181b127a4031b74ebac",
        (677, 187), "SORRY! You need more miles!", "죄송합니다! 마일이 더 필요합니다!"),
    "Q205_0e672581cf837a7d": (
        "9a7d7f71bccde056898167b340a9d4c19807e098d9d62181b127a4031b74ebac",
        (677, 187), "SORRY! You need more miles!", "죄송합니다! 마일이 더 필요합니다!"),
    "Q226_17d32be0f1ec1624": (
        "c837654b9639842edfeaee749c4ae3586ca500d4d3fa1fd3e061f6d70da5ac07",
        (435, 201), "STAGE", "스테이지"),
    "Q046_1c32c8310a619ea2": (
        "4a0d17f50377cd336b9afaca3e6cae2a7cd7f9268cf62a62b1fe83cf1589fb26",
        (265, 147), "PAUSE MENU", "일시정지 / 메뉴"),
    "Q101_ce6fc95e42c9cdff": (
        "40e219c656bbb984b8785e93aa84a76fdd1c157b1b69ffb3da74f9ef2b389992",
        (487, 145), "Steering Wheel :", "스티어링 휠:"),
}
STAGE_ROI = "Q226_17d32be0f1ec1624"
STAGE_ORIGINAL_BBOX = [0, 319, 427, 512]
# The SHA-bound original crop contains three labels GOALS, OUTRUN2 and STAGE.
# Source STAGE spans local y=125:189 of crop origin y=311. Never erase the
# upper two source labels. This child is only a TEST_ONLY owner *candidate*.
STAGE_CHILD_BBOX = [0, 436, 343, 500]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def apply_user_manual_candidates(root, groups):
    """Mutate only in-memory row candidate paths on the GitHub CPU runner."""
    root = Path(root)
    archive = root / INPUT_ZIP
    if not archive.is_file():
        return 0
    if archive.is_symlink() or archive.stat().st_size > 2_000_000:
        raise ValueError("MANUAL_QA_ZIP_FILE_UNSAFE")
    if sha(archive.read_bytes()) != INPUT_ZIP_SHA256:
        raise ValueError("MANUAL_QA_ZIP_SHA_MISMATCH")
    by_id = {r["roi_id"]: r for group in groups.values() for r in group}
    if any(rid not in by_id for rid in EXPECTED):
        raise ValueError("MANUAL_QA_ROI_ID_NOT_IN_SOURCE")
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError("MANUAL_QA_ZIP_CRC")
        names = set(z.namelist())
        raw = z.read("QA_MANIFEST.json")
        if len(raw) > 200_000:
            raise ValueError("MANUAL_QA_MANIFEST_TOO_LARGE")
        manifest = json.loads(raw)
        if (manifest.get("schema") != SCHEMA
                or manifest.get("release_approved") is not False
                or manifest.get("runtime_validation") != "UNTESTED"):
            raise ValueError("MANUAL_QA_MANIFEST_NOT_STAGING")
        targets = manifest.get("targets")
        if not isinstance(targets, list) or len(targets) != len(EXPECTED):
            raise ValueError("MANUAL_QA_TARGET_LIST_INVALID")
        mapped = {}
        for t in targets:
            rid = t.get("id")
            if rid not in EXPECTED or rid in mapped:
                raise ValueError("MANUAL_QA_TARGET_DUPLICATE")
            mapped[rid] = t
        destroot = root / "localization/automation_inputs/manual_user_20261110/output"
        destroot.mkdir(parents=True, exist_ok=True)
        verified = []
        for rid, (digest, dim, english, korean) in EXPECTED.items():
            item = mapped[rid]
            row = by_id[rid]
            output_name = item.get("output_file", "")
            if (item.get("output_sha256") != digest
                    or item.get("output_size") != list(dim)
                    or not re.fullmatch(r"Q\d{3}_[0-9a-f]{16}_MANUAL_KO_RGBA_TEST_ONLY\.png",
                                        output_name)
                    or item.get("status", "").startswith("PASS")
                    or row["english"] != english or row["korean"] != korean):
                raise ValueError("MANUAL_QA_TARGET_SHA_GEOMETRY_OR_TRANSLATION_CHANGED")
            member = "candidate_png_test_only/" + output_name
            if member not in names or z.getinfo(member).file_size > 4_194_304:
                raise ValueError("MANUAL_QA_TARGET_BYTES_MISSING")
            data = z.read(member)
            if sha(data) != digest:
                raise ValueError("MANUAL_QA_TARGET_PNG_SHA_MISMATCH")
            with Image.open(io.BytesIO(data)) as image:
                image.load()
                if image.format != "PNG" or image.mode != "RGBA" or image.size != dim:
                    raise ValueError("MANUAL_QA_TARGET_PNG_NOT_NATIVE_RGBA")
                if not image.getchannel("A").getbbox():
                    raise ValueError("MANUAL_QA_TARGET_EMPTY")
            verified.append((rid, output_name, data))
        # Only after ALL six are verified may in-memory rows change.
        for rid, output_name, data in verified:
            row = by_id[rid]
            dest = destroot / output_name
            dest.write_bytes(data)
            row["_candidate_rel"] = str(dest.relative_to(root))
            row["_manual_user_sha256"] = sha(data)
            row["_candidate_import_mode"] = "MANUAL_USER_COSMETIC_TOLERANCE_TEST_ONLY"
            if rid == STAGE_ROI:
                if row["_bbox"] != STAGE_ORIGINAL_BBOX:
                    raise ValueError("MANUAL_QA_STAGE_ORIGINAL_BBOX_CHANGED")
                row["_manual_source_bbox_original"] = list(row["_bbox"])
                row["_bbox"] = STAGE_CHILD_BBOX.copy()
                row["_manual_source_child_text"] = "STAGE_ONLY_NOT_GOALS_OR_OUTRUN2"
    return len(verified)
