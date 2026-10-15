"""Pure synthetic regression for isolated C automatic salvage; no user assets used."""
from __future__ import annotations
import hashlib
import json
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
import c_salvage_worker as c


def save(im, p):
    p.parent.mkdir(parents=True, exist_ok=True)
    im.save(p, "PNG")


def verify():
    with tempfile.TemporaryDirectory(prefix="c-salvage-worker-test-") as d:
        p = Path(d)
        inp, out, repo = p / "input", p / "output", p / "repo"
        paths = {}
        for role, q, hash_ in [("A", "123", "AAAABBBB"), ("B", "124", "BBBBCCCC"),
                               ("B", "125", "CCCCDDDD")]:
            directory = inp / "ab_batches/candidate_outputs" / role
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / ("Q" + q + "_" + hash_ + "_BASE__r01c01__x0_y0__64x16_k.png")
            image = Image.new("RGBA", (64, 16),
                              (0, 0, 0, 0) if role == "A" else (250, 250, 250, 255))
            from PIL import ImageDraw
            ImageDraw.Draw(image).rectangle((8, 4, 39, 12), fill=(20, 20, 120, 255))
            save(image, path)
            paths[int(q)] = path
        originals = inp / "a_tile_batches/upright_sources"
        originals.mkdir(parents=True)
        name = paths[123].name.replace("_k.png", ".png")
        save(Image.new("RGBA", (64, 16), (0, 0, 0, 0)), originals / name)
        masks = out / "masks"
        masks.mkdir(parents=True)
        mask = np.zeros((16, 64), dtype=np.uint8)
        mask[4:13, 8:40] = 255
        save(Image.fromarray(mask, "L"), masks / (paths[125].stem + ".mask.png"))
        cpath = repo / "localization/graphics/plate_library/PSD_UPSTREAM_FULL_INDEX.json"
        cpath.parent.mkdir(parents=True)
        cpath.write_text(json.dumps({"files": [{
            "texture_hash": "AAAABBBB", "queue_indexes": [123],
            "source_path": "checked.psd", "git_blob_sha": "abc123",
            "copied_into_branch": False
        }], "upstream_commit": "pinnedsha"}))
        class Args:
            input_root = str(inp)
            output_root = str(out)
            repo_root = str(repo)
            recipes_dir = None
            masks_dir = str(masks)
            max_per_cycle = 5
        first = c.run_once(Args)
        assert first["new_processed_items"] == 3, first
        assert first["counts"]["LAYER_PROPOSAL_REVIEW_REQUIRED"] == 2, first
        assert first["counts"]["HOLD_OPAQUE_GENERATED_REQUIRES_EXPLICIT_GLYPH_MASK"] == 1, first
        receipts = [json.loads(x.read_text()) for x in (out / "candidates").glob("*/receipt.json")]
        assert len(receipts) == 3
        for item in receipts:
            assert item["C1"] == "NOT_RUN" and item["official_promoted"] is False
        r123 = next(x for x in receipts if x["queue_index"] == 123)
        assert len(r123["psd_sources"]) == 1
        assert r123["source"]["source_status"] == "SOURCE_TILE_FOUND_NOT_FULL_ATLAS_PROOF"
        r125 = next(x for x in receipts if x["queue_index"] == 125)
        assert r125["generated_text_mask"]["manual_mask_sha256"]
        second = c.run_once(Args)
        assert second["new_processed_items"] == 0, second
        assert len(list((out / "candidates").glob("*/receipt.json"))) == 3
        # Explicit recipe is invalid: fail closed with immutable review evidence.
        recipes = out / "recipes"
        recipes.mkdir()
        (recipes / "bad.json").write_text('{"schema": "outrun-c-salvage-v1", "translation_verified": true}')
        Args.recipes_dir = str(recipes)
        third = c.run_once(Args)
        assert third["new_processed_items"] == 1
        assert third["counts"]["HOLD_RECIPE_FAIL_CLOSED"] == 1
        assert not list((out / "composites").rglob("*.dds"))
        print(json.dumps({"result": "PASS", "new": 3, "rerun_new": 0,
                          "transparent_layer": True, "opaque_hold": True,
                          "manual_mask": True, "psd_catalog_match": True,
                          "invalid_recipe": "HOLD", "runtime": "UNTESTED"}))


if __name__ == "__main__":
    verify()
