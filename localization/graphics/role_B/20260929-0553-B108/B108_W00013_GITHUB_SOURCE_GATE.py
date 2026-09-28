#!/usr/bin/env python3
"""Deterministic GitHub-only source identity gate for W00013 lane B indices 38 and 238."""
import base64
import json
import urllib.parse
import urllib.request

TARGET_REPO = "thp32tt/OutRun2006Tweaks"
TARGET_BRANCH = "korean-localization-clean"
REFERENCE_REPO = "Sonic-TV/OR2006Sprites"
REFERENCE_COMMIT = "a95efe01d1f136514cef94b0d9e9fd61df021754"
EXPECTED_QUEUE_BLOB = "c88bb65e2fbfc99a5741c9135bf5c0052896ff0a"

EXPECTED = {
    38: {
        "queue_fragment": "38,textures/load/spr_sprani_JENN_RANK_Exst/6AB5CEE_1024x1024.dds,zoom_review,blocked_review,needs_zoom_review,",
        "blobs": {
            "Original (PC)/Original (Tweaks dumps)/spr_sprani_JENN_RANK_Exst/06AB5CEE_1024x1024.png": "ffe7d0366a8c71986e3e96c3b1214373295705d7",
            "Original (PC)/Original (Tweaks dumps)/spr_sprani_JENN_RANK_Exst/4x_06AB5CEE_1024x1024_atlas.json": "b777ed9ee87333ec4617a2b283136cdc5189517d",
            "Release/spr_sprani_JENN_RANK_Exst/6AB5CEE_1024x1024.dds": "2302d1218646d51f3d23ce7b93ce9c941ceaaf93",
        },
        "classification": "LOCALIZABLE_TEXT_CONFIRMED",
    },
    238: {
        "queue_fragment": "238,textures/load/spr_sprani_sumo_loading_Exst/132A1B1F_512x512.dds,zoom_review,blocked_review,needs_zoom_review,",
        "blobs": {
            "Original (PC)/Original (Tweaks dumps)/spr_sprani_sumo_loading_Exst/132A1B1F_512x512.png": "0fb60cad692f022fa4ea6f9734d3d7716735661f",
            "Original (PC)/Original (Tweaks dumps)/spr_sprani_sumo_loading_Exst/4x_132A1B1F_512x512_atlas.json": "2b424f07960d73ad6895dc6e526283bf68640399",
            "Release/spr_sprani_sumo_loading_Exst/132A1B1F_512x512.dds": "5a4f2443a6207d2465b60c17272eaf07c7d9a394",
        },
        "classification": "PRESERVE_ORIGINAL",
    },
}

def get_json(url):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "or2006-localization-b108",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

def contents(repo, path, ref):
    qpath = urllib.parse.quote(path, safe="/")
    qref = urllib.parse.quote(ref, safe="")
    return get_json(f"https://api.github.com/repos/{repo}/contents/{qpath}?ref={qref}")

def main():
    queue = contents(TARGET_REPO, "localization/graphics/asset_queue.csv", TARGET_BRANCH)
    assert queue["sha"] == EXPECTED_QUEUE_BLOB, (queue["sha"], EXPECTED_QUEUE_BLOB)
    queue_text = base64.b64decode(queue["content"]).decode("utf-8")

    for idx, spec in EXPECTED.items():
        assert spec["queue_fragment"] in queue_text, idx
        for path, sha in spec["blobs"].items():
            metadata = contents(REFERENCE_REPO, path, REFERENCE_COMMIT)
            assert metadata["sha"] == sha, (idx, path, metadata["sha"], sha)

    print(json.dumps({
        "result": "PASS",
        "queue_blob": queue["sha"],
        "resolved": {
            "38": "LOCALIZABLE_TEXT_CONFIRMED",
            "238": "PRESERVE_ORIGINAL",
        },
        "runtime_validation": "UNTESTED",
    }, ensure_ascii=False, sort_keys=True))

if __name__ == "__main__":
    main()
