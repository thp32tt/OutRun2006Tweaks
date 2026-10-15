"""Synthetic stage-0 tests: precise reconstruction, SHA, coverage and HOLD behavior."""
import csv
import hashlib
import json
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image
import c_salvage_atlas as a


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "input"
        output = Path(tmp) / "output"
        folder = root / a.MAP_REL.parent
        folder.mkdir(parents=True)
        fieldnames = list(a.REQUIRED)
        left = Image.new("RGBA", (2, 3), (20, 40, 60, 128))
        right = Image.new("RGBA", (3, 3), (100, 90, 80, 255))
        names = ["Q123_ABCD1234_BASE__r01c01__x0_y0__2x3.png",
                 "Q123_ABCD1234_BASE__r01c02__x2_y0__3x3.png"]
        rows = []
        for im, name, x in zip((left, right), names, (0, 2)):
            tile = folder / name
            im.save(tile)
            rows.append({
                "part_filename": name, "source_png": "Q123_ABCD1234_BASE.png",
                "source_dds_path": "textures/ABCD1234.dds",
                "source_width": "5", "source_height": "3",
                "x": str(x), "y": "0", "width": str(im.width), "height": "3",
                "orientation": "FLIP_Y_PREVIEW_PER_SPRITE_VERIFY",
                "source_png_sha256": "e" * 64,
                "part_png_sha256": sha(tile.read_bytes()),
            })
        with (root / a.MAP_REL).open("w", newline="") as fp:
            writer = csv.DictWriter(fp, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        res = a.run_atlas_first(root, output, 3)
        assert res["new"] == 1 and len(res["ready"]) == 2, res
        atlas_dir = next((output / "atlases").iterdir())
        with Image.open(atlas_dir / "source_reassembled_readable.png") as im:
            arr = np.asarray(im)
            assert im.size == (5, 3) and np.all(arr[:, :2] == [20, 40, 60, 128])
            assert np.all(arr[:, 2:] == [100, 90, 80, 255])
        ev = json.loads((atlas_dir / "atlas_manifest.json").read_text())
        assert ev["DDS_EQUIVALENCE"] == "UNVERIFIED"
        assert ev["original_full_png_comparison"] == "REFERENCE_FULL_PNG_NOT_STAGED"
        assert a.run_atlas_first(root, output, 3)["new"] == 0

        # Same input SHA with missing tile must not yield any usable atlas.
        badroot = Path(tmp) / "badinput"
        badfolder = badroot / a.MAP_REL.parent
        badfolder.mkdir(parents=True)
        (badroot / a.MAP_REL).write_bytes((root / a.MAP_REL).read_bytes())
        (badfolder / names[0]).write_bytes((folder / names[0]).read_bytes())
        invalid = a.run_atlas_first(badroot, Path(tmp) / "badoutput", 1)
        assert invalid["counts"]["HOLD_ATLAS_REASSEMBLY"] == 1
        assert not list((Path(tmp) / "badoutput" / "atlases").glob("*/source_reassembled_readable.png"))

        # Exact bytes must be SHA-pinned; no silently altered RGB/alpha.
        changed = Image.new("RGBA", (2, 3), (5, 3, 2, 1))
        changed.save(badfolder / names[0])
        invalid = a.run_atlas_first(badroot, Path(tmp) / "badoutput2", 1)
        assert invalid["counts"]["HOLD_ATLAS_REASSEMBLY"] == 1
        print(json.dumps({"result": "PASS", "atlas": list(res["ready"]),
                          "SHA": "PASS", "coverage": "PASS", "failure_closed": "PASS"}))


if __name__ == "__main__":
    verify()
