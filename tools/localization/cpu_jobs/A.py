#!/usr/bin/env python3
"""A latest-policy q217: SHA-verified HD original READABLE source input (not generation)."""
from pathlib import Path
from PIL import Image, ImageDraw
import hashlib, io, json, os, struct, urllib.request
R=Path.cwd()
OUT=R/"localization/graphics/role_A/imagegen_inputs/q217_20261012"
RUN="OUTRUN-KOR-A-Q217-HD-READABLE-TWO-SPRITES-20261012-1600"
URL=("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"
"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/"
"Release/spr_sprani_sumo_fe_cvt_Exst/D1039D6F_512x512.dds")
SHA="d3d2d15540642d8315df8b38b77a34609e534ea042bce8e7e951e65ab219bcd0"
TEXTS=[
    {"id":"START","source":"START","korean":"출발","original_effect_bbox_readable":[803,509,884,532],"roi":[787,493,900,548]},
    {"id":"GOAL","source":"GOAL","korean":"골","original_effect_bbox_readable":[1343,771,1420,795],"roi":[1327,755,1436,811]}
]
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="A"
def sha(b):return hashlib.sha256(b).hexdigest()
def write_png(name,im):
    path=OUT/name
    im.save(path,format="PNG",optimize=True)
    with Image.open(path) as reloaded:
        reloaded.load()
        assert reloaded.size==im.size
        assert reloaded.convert("RGBA").tobytes()==im.convert("RGBA").tobytes(), "PNG_PERSISTED_PIXEL_MISMATCH"
    data=path.read_bytes()
    return {"path":str(path.relative_to(R)),"sha256":sha(data),"bytes":len(data),
            "dimensions":list(im.size),"mode":im.mode}
def write_json(name,data):
    (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
OUT.mkdir(parents=True,exist_ok=True)
assert not (OUT/"q217_INPUT_AND_GENERATION_STATE.json").exists(),"ALREADY_PREPARED_NO_DUPLICATE"
with urllib.request.urlopen(urllib.request.Request(URL,headers={"User-Agent":"OutRun-A-HD-Source"}),timeout=90) as response:
    b=response.read()
assert sha(b)==SHA,(len(b),sha(b),"CANONICAL_DDS_SHA_MISMATCH")
assert b[:4]==b"DDS "
h,w=struct.unpack_from("<II",b,12)
mips=struct.unpack_from("<I",b,28)[0]
bits=struct.unpack_from("<I",b,88)[0]
assert (w,h,mips,bits)==(2048,2048,1,32),(w,h,mips,bits)
raw=Image.open(io.BytesIO(b))
raw.load()
readable=raw.convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
atlas=write_png("q217_CANONICAL_HD_FULL_READABLE_2048x2048.png",readable)
sources=[]
for info in TEXTS:
    x0,y0,x1,y1=info["roi"]
    tx0,ty0,tx1,ty1=info["original_effect_bbox_readable"]
    assert (x0<tx0<x1 and y0<ty0<y1 and x0<tx1<x1 and y0<ty1<y1)
    roi=readable.crop((x0,y0,x1,y1))
    persist=write_png("q217_"+info["id"]+"_SOURCE_READABLE_NATIVE.png",roi)
    compare=Image.new("RGB",(roi.width*4,roi.height*4),(125,125,125))
    large=roi.resize((roi.width*4,roi.height*4),Image.Resampling.NEAREST)
    compare.paste(large,mask=large.getchannel("A"))
    illustration=write_png("q217_"+info["id"]+"_SOURCE_VISUAL_ZOOM4_NOT_FOR_IMAGEGEN.png",compare)
    assert roi.tobytes()==readable.crop(info["roi"]).tobytes()
    sources.append({**info,"source_native":persist,"source_reference_zoom_only":illustration,
                    "readable_transform":"flip_y","local_text_bbox": [tx0-x0,ty0-y0,tx1-x0,ty1-y0]})
translations=[{"source":x["source"],"korean":x["korean"]} for x in TEXTS]
prompt=(
    "첨부 파일은 SHA 검증된 OutRun 2006 HD 원본 DDS에서 정방향으로 변환한 원본 PNG입니다. "
    "이 실제 이미지 첨부를 기준으로 번역할 글자만 바꾸세요.\n"
    "START → 출발\nGOAL → 골\n"
    "각각 빨간색 배지·원본 문구의 크림색/주황색 입체 표면·남색 음영과 "
    "오른쪽으로 기울어진 방향을 최대한 유지하세요. 원본 배지 아트·하이라이트·테두리·"
    "텍스트 외 모든 부분을 보존하고, 한글 획·받침·내부 공간을 정확히 생성하세요.\n"
    "번역이 짧아도 전체 폭을 강제 확대하지 않습니다. 원래 영문 글자+효과 bbox를 "
    "한 픽셀도 넘지 않게 하고 원본 UI 칸이나 이웃 아트가 훼손되지 않도록 하세요. "
    "원본 PNG 해상도·방향·투명 픽셀을 보존하고 부가 문구·워터마크를 만들지 마세요.\n"
    "실제 원본 이미지가 첨부되지 않았으면 편집을 수행했다고 주장하지 마세요."
)
(OUT/"q217_A_IMAGEGEN_EDIT_PROMPT.txt").write_text(prompt+"\n",encoding="utf-8")
evidence={
    "schema":"a-hd-source-imagegen-input-v2","role":"A","run_key":RUN,
    "asset_queue_index":217,"status":"SOURCE_REFERENCE_NOT_BOUND__UPLOAD_TO_CHATGPT_REQUIRED",
    "canonical_source_url":URL,"canonical_source_sha256":SHA,
    "dds_header":{"width":w,"height":h,"format":"BGRA32","mip_count":mips},
    "atlas":atlas,"sprites":sources,
    "translations":translations,
    "raw_to_readable":"flip_y","readable_to_raw":"flip_y",
    "full_atlas_has_mixed_transforms":"NOT_REVIEWED_PER_SPRITE; the two relevant sprites are verified from C1 readable bounding boxes",
    "input_connection_receipt":None,"imagegen_generation_id":None,
    "imagegen_output_png_sha256":None,"actual_imagegen_calls":0,
    "new_Korean_image_png":0,"new_trial_dds":0,"official_promoted":0,
    "A_per_glyph_size_qa":"NOT_RUN_ON_NEW_KOREAN_BYTES",
    "strict_source_effect_bbox_check":"PENDING_NEW_IMAGE",
    "independent_C1":"NOT_RUN","C3":"NOT_RUN",
    "RUNTIME_VALIDATION":"UNTESTED","excluded":["VR","FFB","DX11","DXVK"],
    "producer_decision":"SOURCE_ONLY_INPUT_READY_NOT_LOCALIZATION_PASS"
}
write_json("q217_INPUT_AND_GENERATION_STATE.json",evidence)
print(json.dumps({"run":RUN,"source_sha256":SHA,"atlas_sha256":atlas["sha256"],
"regions":{x["id"]:x["source_native"]["sha256"] for x in sources},"new_dds":0,"status":evidence["status"]},
ensure_ascii=False),flush=True)
