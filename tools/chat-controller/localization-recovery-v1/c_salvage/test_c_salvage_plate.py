"""PSD-first or source-transparent CLEAN fallback: synthetic DDS regression."""
import hashlib
import json
import struct
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import c_salvage_compose as c
import c_salvage_plate as plate


def ref(base, name, blob):
    (base/name).write_bytes(blob)
    return {"path": name, "sha256": hashlib.sha256(blob).hexdigest()}


def png_ref(base, name, im):
    import io
    stream=io.BytesIO()
    im.save(stream, format="PNG")
    return ref(base,name,stream.getvalue())


def encode_dds(im):
    a=np.asarray(im)
    h,w=a.shape[:2]
    head=bytearray(128)
    head[:4]=b"DDS "
    struct.pack_into("<I",head,4,124)
    struct.pack_into("<I",head,8,0x100f)
    struct.pack_into("<I",head,12,h)
    struct.pack_into("<I",head,16,w)
    struct.pack_into("<I",head,20,w*4)
    struct.pack_into("<I",head,28,1)
    struct.pack_into("<I",head,76,32)
    struct.pack_into("<I",head,80,0x41)
    struct.pack_into("<I",head,88,32)
    struct.pack_into("<IIII",head,92,*c.BGRA_MASKS)
    struct.pack_into("<I",head,108,0x1000)
    return bytes(head)+a[:, :, [2,1,0,3]].tobytes()


def trial():
    with tempfile.TemporaryDirectory(prefix="c-plate-test-") as d:
        root=Path(d)
        source=Image.new("RGBA",(64,32))
        z=ImageDraw.Draw(source)
        z.rectangle((8,6,18,16),fill=(240,240,240,255))
        z.rectangle((45,8,54,19),fill=(0,220,60,255))
        rm=np.zeros((32,64),np.uint8);rm[6:17,8:19]=255
        protected=np.zeros((32,64),np.uint8);protected[8:20,45:55]=255
        recipe={"schema":plate.SCHEMA, "orientation":"IDENTITY",
                "source_dds":ref(root,"original.dds",encode_dds(source)),
                "removal_mask":png_ref(root,"remove.png",Image.fromarray(rm,"L")),
                "protected_mask":png_ref(root,"protect.png",Image.fromarray(protected,"L")),
                "source_transparent_under_english_reviewed":True}
        result=plate.prepare_plate(root,recipe,root/"good")
        assert result["psd_attempt"]=="PSD_UNAVAILABLE"
        assert result["status"]=="CLEAN_CANDIDATE_REQUIRES_INDEPENDENT_C1_PLATE_REVIEW"
        clean=np.array(Image.open(root/"good"/"clean_candidate.png"))
        src=np.asarray(source)
        assert np.array_equal(clean[protected!=0],src[protected!=0])
        assert not np.any(clean[rm!=0])
        assert result["outside_removal_changed_rgba_pixels"]==0
        assert result["protected_changed_rgba_pixels"]==0
        bad=dict(recipe,source_transparent_under_english_reviewed=False)
        try:
            plate.prepare_plate(root,bad,root/"rejected")
        except ValueError as err:
            assert "HOLD_SOURCE_BACKGROUND" in str(err)
        else:
            raise AssertionError("Unreviewed CLEAN source was improperly accepted")
        bad=dict(recipe,protected_mask=recipe["removal_mask"])
        try:
            plate.prepare_plate(root,bad,root/"overlap")
        except ValueError as err:
            assert "conflicting" in str(err)
        else:
            raise AssertionError("Protected English overlap bypass")
        import c_salvage_worker as worker
        jobs=root/"plate_jobs"
        jobs.mkdir()
        spec=jobs/"sample.json"
        spec.write_text(json.dumps(recipe,ensure_ascii=False))
        queue=root/"job_queue"
        status,changed=worker.handle_plate_job(spec,root,queue)
        assert status=="CLEAN_CANDIDATE_REQUIRES_INDEPENDENT_C1_PLATE_REVIEW" and changed
        status2,changed2=worker.handle_plate_job(spec,root,queue)
        assert status2=="ALREADY_RECORDED" and not changed2
        assert len(list((queue/"plates").glob("*/receipt.json")))==1
        print(json.dumps({"test":"C_PLATE", "result":"PASS", "cases":3,
                          "psd_missing_fallback":"TEST_ONLY", "unreviewed":"HOLD",
                          "source_pixels_outside_removal_changed":0, "runtime":"UNTESTED"}))

if __name__=="__main__":
    trial()
