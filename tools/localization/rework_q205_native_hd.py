#!/usr/bin/env python3
from __future__ import annotations
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import hashlib, json
import numpy as np

# Runner font package: full Noto CJK including Medium/Serif.
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/ACF61D7C_1024x512.dds"
CLEAN = ROOT / "localization/graphics/role_A/20261006-A-PRODUCTION76-ACF/A76_ACF_CLEAN_PLATE.png"
SOURCE_READABLE = ROOT / "localization/graphics/role_A/20261006-A-PRODUCTION76-ACF/A76_ACF_SOURCE_READABLE.png"
OUTDIR = ROOT / "localization/graphics/role_B/20261008-B240-Q205-NATIVE-HD"
OUTDIR.mkdir(parents=True, exist_ok=True)

EXPECTED_PRIOR = "7598af3375cfd96fa83f2ac7610ac1a97dd0fcebd7aa95f3e33a641dbcfbba9e"
actual_prior = hashlib.sha256(CANDIDATE.read_bytes()).hexdigest()
if actual_prior != EXPECTED_PRIOR:
    raise SystemExit(f"q205 base drift: expected {EXPECTED_PRIOR}, got {actual_prior}")

current_raw = Image.open(CANDIDATE).convert("RGBA")
current = current_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
clean = Image.open(CLEAN).convert("RGBA")
source = Image.open(SOURCE_READABLE).convert("RGBA")
if current.size != (4096, 2048) or clean.size != current.size or source.size != current.size:
    raise SystemExit(f"unexpected q205 dimensions: {current.size}, {clean.size}, {source.size}")
new = current.copy()

sans = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
serif = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Medium.ttc"
for p in (sans, serif):
    if not Path(p).is_file():
        raise SystemExit(f"required native-HD font missing: {p}")

rows = [
    dict(key="options", text="옵션", bbox=(1591,1423,2316,1568), font=serif, fs=142, color=(186,0,0,255), align="left"),
    dict(key="rankings", text="랭킹", bbox=(33,1245,930,1388), font=serif, fs=140, color=(186,0,0,255), align="left"),
    dict(key="out_run_1p", text="1인 플레이!", bbox=(1959,1066,2569,1132), font=sans, fs=60, color=(63,71,74,255), align="after_token", token=(1959,1066,2184,1121)),
    dict(key="view_rankings", text="싱글/멀티플레이 랭킹 보기", bbox=(3,911,1334,977), font=sans, fs=60, color=(63,71,74,255), align="left"),
    dict(key="enjoy_original", text="오리지널", bbox=(1807,909,2696,975), font=sans, fs=60, color=(63,71,74,255), align="before_token", token=(2356,909,2696,964), gap=24),
    dict(key="adjust_settings", text="게임 설정 조정", bbox=(1,748,1800,814), font=sans, fs=60, color=(63,71,74,255), align="left"),
]

# Remove only the screenshot-visible old low-resolution Korean rows, using the
# independently validated A76 clean plate. Inline OutRun product tokens remain
# present in that clean plate and are verified byte/pixel exact below.
for r in rows:
    x0,y0,x1,y1 = r["bbox"]
    new.paste(clean.crop((x0,y0,x1,y1)), (x0,y0))

def render_native(text: str, font_path: str, size: int, color):
    font = ImageFont.truetype(font_path, size, index=1)
    bb = font.getbbox(text)
    im = Image.new("RGBA", (bb[2]-bb[0]+8, bb[3]-bb[1]+8), (0,0,0,0))
    d = ImageDraw.Draw(im)
    d.text((4-bb[0], 4-bb[1]), text, font=font, fill=color)
    crop = im.getchannel("A").getbbox()
    return im.crop(crop)

report_rows = []
for r in rows:
    x0,y0,x1,y1 = r["bbox"]
    glyph = render_native(r["text"], r["font"], r["fs"], r["color"])
    maxw, maxh = x1-x0-8, y1-y0-8
    if glyph.width > maxw or glyph.height > maxh:
        ratio = min(maxw/glyph.width, maxh/glyph.height)
        glyph = glyph.resize((max(1,int(glyph.width*ratio)), max(1,int(glyph.height*ratio))), Image.Resampling.LANCZOS)

    if r["align"] == "left":
        x = x0 + 4
    elif r["align"] == "after_token":
        x = r["token"][2] + r.get("gap", 16)
    elif r["align"] == "before_token":
        x = r["token"][0] - r.get("gap", 16) - glyph.width
    else:
        raise RuntimeError(r["align"])

    y = y0 + ((y1-y0) - glyph.height)//2
    if x < x0+4 or x+glyph.width > x1-4:
        raise SystemExit(f"{r['key']} placement escaped source bbox")
    new.alpha_composite(glyph, (x,y))
    report_rows.append({
        "key": r["key"],
        "text": r["text"],
        "source_bbox": list(r["bbox"]),
        "localized_bbox": [x,y,x+glyph.width,y+glyph.height],
        "localized_size": [glyph.width,glyph.height],
        "margins": [x-x0, x1-(x+glyph.width), y-y0, y1-(y+glyph.height)],
        "font": Path(r["font"]).name,
        "font_size": r["fs"],
        "pixel_scale": 1,
        "stroke_width": 0,
        "alignment": r["align"],
    })

a = np.array(current)
b = np.array(new)
changed = np.any(a != b, axis=2)
allowed = np.zeros(changed.shape, dtype=bool)
for r in rows:
    x0,y0,x1,y1 = r["bbox"]
    allowed[y0:y1,x0:x1] = True
outside = int(np.count_nonzero(changed & ~allowed))
if outside:
    raise SystemExit(f"q205 blast radius failure: {outside} changed pixels outside exact six bboxes")

token_checks = {}
for name,box in [("OutRun", rows[2]["token"]), ("OutRun2SP", rows[4]["token"])]:
    x0,y0,x1,y1 = box
    token_checks[name] = int(np.count_nonzero(np.any(a[y0:y1,x0:x1] != b[y0:y1,x0:x1], axis=2)))
if any(token_checks.values()):
    raise SystemExit(f"protected product token changed: {token_checks}")

# Persist exact DDS header/format and canonical raw mirror-Y orientation.
raw = new.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
header = CANDIDATE.read_bytes()[:128]
CANDIDATE.write_bytes(header + raw.tobytes("raw", "RGBA"))
candidate_sha = hashlib.sha256(CANDIDATE.read_bytes()).hexdigest()

# 25% full-atlas comparison and native 1x contacts for the six user-visible rows.
def thumb(im):
    return im.resize((1024,512), Image.Resampling.LANCZOS).convert("RGB")

proof = Image.new("RGB", (1024, 512*3+72), "white")
for i,(label,im) in enumerate([
    ("SOURCE", source),
    ("C217/A76 CURRENT (quarter-size raster x4)", current),
    ("B240 NATIVE-HD", new),
]):
    proof.paste(thumb(im), (0, i*536+24))
    ImageDraw.Draw(proof).text((8, i*536+4), label, fill="black")
proof.save(OUTDIR / "B240_Q205_SOURCE_CURRENT_NEW.jpg", quality=95)

contacts = []
for r in rows:
    x0,y0,x1,y1 = r["bbox"]
    pad=20
    box=(max(0,x0-pad),max(0,y0-pad),min(new.width,x1+pad),min(new.height,y1+pad))
    ss,cc,nn = source.crop(box), current.crop(box), new.crop(box)
    w,h = ss.width, ss.height
    sheet=Image.new("RGB",(w*3,h+28),"white")
    sheet.paste(ss.convert("RGB"),(0,28))
    sheet.paste(cc.convert("RGB"),(w,28))
    sheet.paste(nn.convert("RGB"),(w*2,28))
    d=ImageDraw.Draw(sheet)
    d.text((4,4),"SOURCE",fill="black")
    d.text((w+4,4),"CURRENT",fill="black")
    d.text((w*2+4,4),"B240 NATIVE",fill="black")
    name=f"B240_Q205_{r['key']}_1X.jpg"
    sheet.save(OUTDIR / name, quality=95)
    contacts.append(name)

report = {
    "schema_version": 1,
    "role": "B",
    "run": "B240",
    "queue_index": 205,
    "asset": "textures/load/spr_sprani_sumo_fe_cvt_Exst/ACF61D7C_1024x512.dds",
    "trigger": "USER_INGAME_SCREENSHOTS_159_162_LOW_RES_DIRTY_HEAVY_KOREAN",
    "source_sha256": "58a75fe75b5672169dcc2ed1f9993d462d80b700d4e12dad453b70f2ab701a5f",
    "prior_candidate_sha256": EXPECTED_PRIOR,
    "candidate_sha256": candidate_sha,
    "method": "replace only six screenshot-visible rows from A76 exact clean plate; render Korean directly at final 4096x2048 with native Noto CJK Medium/Regular; no 33px/12px quarter-size raster and no x4 bitmap upscale; no artificial stroke; B240R visual correction shortens the constrained protected-token row to 오리지널 + 24px gap + original OutRun2SP",
    "pixel_scale": 1,
    "changed_pixels": int(changed.sum()),
    "changed_outside_rework_bboxes": outside,
    "protected_token_changed_pixels": token_checks,
    "rows": report_rows,
    "contacts": contacts,
    "controller_visual_qa": "PENDING_FRESH_CONTROLLER_AFTER_WORKER",
    "fresh_c_required": True,
    "runtime_validation": "UNTESTED",
    "no_vr_ffb_dx11_dxvk_work": True,
}
(OUTDIR / "B240_Q205_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n", encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))
