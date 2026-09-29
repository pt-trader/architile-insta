"""슬라이드 스펙(JSON) → 이미지.
  - 캐러셀: 1080x1350 (4:5)  → 01.jpg ...
  - 세로 프레임: 1080x1920 (9:16) → 릴스·스토리용 f01.jpg ...
Instagram API는 이미지로 JPEG만 받는다.

스펙의 이미지 경로("img")는 스펙 파일 기준 상대경로 또는 절대경로.
"""
import base64, io, json, os
from pathlib import Path
from PIL import Image, ImageOps

BRAND = "#851B20"
PHONE = "031.306.9630"
MAIL = "facadeworks@naver.com"
HOURS = "평일 09:00~18:00"

# steps 슬라이드용 작은 그림 (나노친수 3단계 등)
_SURF = '<rect x="10" y="118" width="220" height="12" fill="#8FCFE3"/><rect x="10" y="130" width="220" height="40" fill="#C8B4A0"/>'
ICONS = {
    "drop": _SURF + "".join(f'<line x1="{x}" y1="{y}" x2="{x}" y2="112" stroke="#4FA8CC" stroke-width="4"/><circle cx="{x}" cy="{y}" r="{r}" fill="#4FA8CC"/>'
                            for x, y, r in [(45, 60, 11), (95, 40, 9), (140, 78, 8), (185, 50, 11)]),
    "dust": _SURF + "".join(f'<circle cx="{x}" cy="{112 - r}" r="{r}" fill="{c}"/>'
                            for x, r, c in [(40, 13, "#6E6259"), (80, 8, "#9A8F86"), (120, 15, "#6E6259"), (160, 8, "#9A8F86"), (200, 13, "#6E6259")]),
    "rain": _SURF + "".join(f'<line x1="{x}" y1="10" x2="{x - 10}" y2="60" stroke="#4FA8CC" stroke-width="5" stroke-linecap="round"/>' for x in (50, 105, 160, 215))
            + "".join(f'<circle cx="{x}" cy="92" r="11" fill="#6E6259"/><path d="M{x} 103 q -8 8 0 16" stroke="#4FA8CC" stroke-width="4" fill="none"/>' for x in (60, 125, 190)),
}


def resolve_img(p):
    """'@photos/...' → 블로그 사진 폴더(환경변수 ARCHI_PHOTOS, 기본값 저장소 옆 ../_photos)
    '@cases/...'  → 우리 시공 현장 폴더(ARCHI_CASES, 기본값 ../cases)."""
    blog = Path(__file__).resolve().parents[2]
    if p.startswith("@photos/"):
        root = Path(os.environ.get("ARCHI_PHOTOS", blog / "_photos"))
        return str(root / p[len("@photos/"):])
    if p.startswith("@repo/"):
        return str(Path(__file__).resolve().parents[1] / p[len("@repo/"):])
    if p.startswith("@cases/"):
        root = Path(os.environ.get("ARCHI_CASES", blog / "cases"))
        return str(root / p[len("@cases/"):])
    return p


def crop_box(iw, ih, crop, box):
    bw, bh = box
    cx, cy, z = crop or (0.5, 0.5, 1.0)
    r = bw / bh
    if iw / ih > r:
        ch = ih / z; cw = ch * r
    else:
        cw = iw / z; ch = cw / r
    x0 = min(max(cx * iw - cw / 2, 0), iw - cw)
    y0 = min(max(cy * ih - ch / 2, 0), ih - ch)
    return x0, y0, cw, ch


def img_data(path, crop=None, box=(1080, 1350), quality=88, rot=0, fit="cover", bg="#FFFFFF"):
    """crop=[cx, cy, zoom] (중심 0~1, 확대배율). box 비율로 잘라 data URI 반환."""
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    if rot:
        im = im.rotate(rot, expand=True)
    if fit == "contain":   # 도해처럼 잘리면 안 되는 이미지: 여백을 두고 통째로
        bw, bh = box; pad = 0.05
        sc = min(bw * (1 - 2 * pad) / im.width, bh * (1 - 2 * pad) / im.height)
        im2 = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
        can = Image.new("RGB", box, bg); can.paste(im2, ((bw - im2.width) // 2, (bh - im2.height) // 2))
        b = io.BytesIO(); can.save(b, "JPEG", quality=92)
        return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
    x0, y0, cw, ch = crop_box(*im.size, crop, box)
    im = im.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize(box, Image.LANCZOS)
    b = io.BytesIO(); im.save(b, "JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def css(W, H, tall):
    # 9:16 프레임은 인스타 UI(상단 계정명, 하단 캡션·버튼)가 덮는 영역을 비워둔다
    bottom = 420 if tall else 120
    top = 260 if tall else 150
    return f"""
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:{W}px;height:{H}px;font-family:'Noto Sans CJK KR','Noto Sans KR',sans-serif;overflow:hidden;background:#111;color:#fff;letter-spacing:-0.02em}}
.s{{position:relative;width:{W}px;height:{H}px;overflow:hidden}}
.bg{{position:absolute;inset:0;width:100%;height:100%}}
.shade{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.55) 0%,rgba(0,0,0,0) 26%,rgba(0,0,0,0) 42%,rgba(0,0,0,.85) 100%)}}
.shade.top{{background:linear-gradient(180deg,rgba(0,0,0,.9) 0%,rgba(0,0,0,.72) 40%,rgba(0,0,0,0) 66%)}}
.tag{{position:absolute;left:72px;top:{top - 78}px;font-size:26px;font-weight:500;letter-spacing:.08em;opacity:.92}}
.tag b{{display:inline-block;width:14px;height:14px;background:{BRAND};margin-right:12px;vertical-align:1px}}
.pg{{position:absolute;right:72px;top:{top - 78}px;font-size:24px;opacity:.7}}
.txt{{position:absolute;left:72px;right:72px;bottom:{bottom}px}}
.txt.top{{top:{top}px;bottom:auto}}
h1{{font-size:88px;line-height:1.16;font-weight:900}}
h2{{font-size:66px;line-height:1.2;font-weight:800}}
p{{font-size:36px;line-height:1.55;font-weight:400;margin-top:30px;opacity:.93}}
.cap{{position:absolute;left:72px;bottom:{bottom - 68}px;font-size:22px;opacity:.6}}
.swipe{{position:absolute;right:72px;bottom:{bottom - 68}px;font-size:26px;font-weight:500;opacity:.85}}
.solid{{background:#F4F1EC;color:#1d1d1d}}
.brand{{background:{BRAND};color:#fff}}
.big{{font-size:230px;font-weight:900;line-height:1;letter-spacing:-0.05em}}
.unit{{font-size:48px;font-weight:700;margin-left:8px}}
.rule{{width:90px;height:8px;background:{BRAND};margin:44px 0}}
.brand .rule{{background:#fff}}
table{{border-collapse:collapse;width:100%;margin-top:40px;font-size:34px}}
td,th{{padding:18px 10px;border-bottom:2px solid rgba(0,0,0,.12);text-align:left;color:#1d1d1d}}
th{{font-weight:700;font-size:28px;opacity:.6}}
td.a{{color:{BRAND};font-weight:800}}
.inset{{position:absolute;left:72px;right:72px;top:{top + 40}px;height:560px;border-radius:6px;overflow:hidden}}
.inset img{{width:100%;height:100%;object-fit:cover;display:block}}
.contact{{font-size:38px;line-height:1.8;margin-top:36px}}
.contact span{{display:inline-block;width:150px;opacity:.7;font-size:30px}}
.fshade{{position:absolute;left:0;right:0;bottom:0;height:46%;background:linear-gradient(180deg,rgba(0,0,0,0) 0%,rgba(0,0,0,.72) 100%)}}
.tshade{{position:absolute;left:0;right:0;top:0;height:22%;background:linear-gradient(180deg,rgba(0,0,0,.5) 0%,rgba(0,0,0,0) 100%)}}
.ftxt{{position:absolute;left:72px;right:72px;bottom:{bottom}px}}
.ftxt h3{{font-size:58px;line-height:1.22;font-weight:800}}
.ftxt p{{font-size:32px;margin-top:18px}}
.tile{{position:absolute;overflow:hidden;background:#222}}
.tile img{{width:100%;height:100%;object-fit:cover;display:block}}
.chip{{position:absolute;left:24px;bottom:22px;background:rgba(0,0,0,.62);color:#fff;font-size:30px;font-weight:700;padding:10px 20px;border-radius:4px;line-height:1.25}}
.chip small{{display:block;font-size:22px;font-weight:400;opacity:.8}}
.chip.brandc{{background:{BRAND}}}
.band{{position:absolute;left:0;right:0;top:0;background:#111}}
.band h2{{font-size:54px;line-height:1.2}}
.sw .lab{{position:absolute;font-size:30px;font-weight:800;color:#1d1d1d;text-align:center}}
.sw .lab small{{display:block;font-size:22px;font-weight:400;opacity:.6;margin-top:6px}}
.lens{{position:absolute;border-radius:50%;overflow:hidden;border:8px solid #fff;box-shadow:0 12px 40px rgba(0,0,0,.45)}}
.lens img{{width:100%;height:100%;display:block}}
.lensl{{position:absolute;color:#fff;font-size:30px;font-weight:700;text-shadow:0 2px 12px rgba(0,0,0,.7)}}
"""


def slide_html(s, i, n, tag, base, W, H, tall):
    k = s["type"]
    pg = "" if tall else f'<div class="pg">{i}/{n}</div>'
    tg = f'<div class="tag"><b></b>{tag}</div>'
    swipe = '<div class="swipe">넘겨보기 →</div>' if (i == 1 and not tall) else ""
    cap = f'<div class="cap">{s["cap"]}</div>' if s.get("cap") else ""
    P = resolve_img
    inset_top = 300 if tall else 190
    if k in ("photo", "cover"):
        top = s.get("pos") == "top"
        head = f'<h1>{s["h"]}</h1>' if k == "cover" else f'<h2>{s["h"]}</h2>'
        body = f'<p>{s["p"]}</p>' if s.get("p") else ""
        return (f'<div class="s"><img class="bg" src="{img_data(P(s["img"]), s.get("crop"), (W, H))}">'
                f'<div class="shade{" top" if top else ""}"></div>{tg}{pg}'
                f'<div class="txt{" top" if top else ""}">{head}{body}</div>{cap}{swipe}</div>')
    if k == "number":
        cls = s.get("tone", "brand")
        return (f'<div class="s {cls}">{tg}{pg}<div class="txt top" style="top:{520 if tall else 260}px">'
                f'<div style="font-size:40px;font-weight:700;opacity:.85">{s["pre"]}</div>'
                f'<div style="margin-top:20px"><span class="big">{s["num"]}</span><span class="unit">{s["unit"]}</span></div>'
                f'<div class="rule"></div><h2 style="font-size:54px">{s["h"]}</h2><p>{s["p"]}</p></div>{cap}</div>')
    if k == "text":
        cls = s.get("tone", "solid")
        inset = ""
        if s.get("img"):
            inset = (f'<div class="inset" style="top:{inset_top}px"><img src="{img_data(P(s["img"]), s.get("crop"), (936, 560), fit=s.get("fit", "cover"))}"></div>')
        top = (inset_top + 620) if inset else (560 if tall else 380)
        return (f'<div class="s {cls}">{tg}{pg}{inset}<div class="txt top" style="top:{top}px">'
                f'<h2>{s["h"]}</h2><div class="rule" style="margin:34px 0 0"></div><p>{s["p"]}</p></div>{cap}</div>')
    if k == "table":
        rows = "".join(f'<tr><td>{a}</td><td>{b}</td><td class="a">{c}</td></tr>' for a, b, c in s["rows"])
        c = s["cols"]
        return (f'<div class="s solid">{tg}{pg}<div class="txt top" style="top:{420 if tall else 190}px"><h2>{s["h"]}</h2>'
                f'<table><tr><th>{c[0]}</th><th>{c[1]}</th><th>{c[2]}</th></tr>{rows}</table>'
                f'<p style="font-size:28px;opacity:.6">{s.get("p", "")}</p></div>{cap}</div>')
    if k == "cta":
        return (f'<div class="s brand">{tg}{pg}<div class="txt top" style="top:{420 if tall else 230}px"><h2>{s["h"]}</h2>'
                f'<div class="rule"></div><p style="margin-top:0">{s["p"]}</p>'
                f'<div class="contact"><span>상호</span>파사드웍스 Facadeworks<br><span>전화</span>{PHONE}<br>'
                f'<span>메일</span>{MAIL}<br><span>운영</span>{HOURS}</div></div>'
                f'<div class="cap" style="opacity:.8">INAX 아키타일(기능성 외장타일) 공급 및 시공</div></div>')
    if k == "full":
        # 사진이 주인공: 문구는 아래 한두 줄만
        head = f'<h3>{s["h"]}</h3>' if s.get("h") else ""
        body = f'<p>{s["p"]}</p>' if s.get("p") else ""
        shade = '<div class="fshade"></div>' if (head or body) else ""
        return (f'<div class="s"><img class="bg" src="{img_data(P(s["img"]), s.get("crop"), (W, H))}">'
                f'<div class="tshade"></div>{shade}{tg}{pg}<div class="ftxt">{head}{body}</div>{cap}{swipe}</div>')
    if k in ("duo", "grid"):
        items = s["imgs"]
        band = 0
        if s.get("h"):
            band = (470 if tall else 250) + (80 if s.get("p") else 0)
        gap = 8
        x0, y0, w, h = 0, band, W, H - band
        if tall and not band:
            y0 = 0
        cells = []
        if k == "duo":
            vertical = s.get("dir", "v") == "v"
            if vertical:
                hh = (h - gap) // 2
                cells = [(x0, y0, w, hh), (x0, y0 + hh + gap, w, h - hh - gap)]
            else:
                ww = (w - gap) // 2
                cells = [(x0, y0, ww, h), (x0 + ww + gap, y0, w - ww - gap, h)]
        else:
            ww = (w - gap) // 2; hh = (h - gap) // 2
            cells = [(0, y0, ww, hh), (ww + gap, y0, w - ww - gap, hh),
                     (0, y0 + hh + gap, ww, h - hh - gap), (ww + gap, y0 + hh + gap, w - ww - gap, h - hh - gap)]
        tiles = ""
        for it, (cx, cy, cw, ch) in zip(items, cells):
            lab = ""
            if it.get("label"):
                sub = f'<small>{it["sub"]}</small>' if it.get("sub") else ""
                lab = f'<div class="chip{" brandc" if it.get("brand") else ""}">{it["label"]}{sub}</div>'
            tiles += (f'<div class="tile" style="left:{cx}px;top:{cy}px;width:{cw}px;height:{ch}px">'
                      f'<img src="{img_data(P(it["img"]), it.get("crop"), (cw, ch), rot=it.get("rot", 0), fit=it.get("fit", "cover"))}">{lab}</div>')
        bandh = ""
        if band:
            bp = f'<p style="font-size:30px;margin-top:14px;opacity:.85">{s["p"]}</p>' if s.get("p") else ""
            bandh = f'<div class="band" style="height:{band}px"><div style="position:absolute;left:72px;right:72px;bottom:34px"><h2 style="font-size:54px;line-height:1.2">{s["h"]}</h2>{bp}</div></div>'
        capd = f'<div class="cap" style="bottom:auto;top:{band - 40 if band else H - 40}px;left:auto;right:72px">{s["cap"]}</div>' if s.get("cap") else ""
        if band:
            capd = f'<div class="cap" style="bottom:auto;top:{band + 14}px;right:24px;left:auto;background:rgba(0,0,0,.5);padding:4px 10px">{s["cap"]}</div>'
        else:
            capd = f'<div class="cap" style="bottom:auto;top:{H // 2 - 36 if k == "grid" or s.get("dir", "v") == "v" else 20}px;right:24px;left:auto;background:rgba(0,0,0,.5);padding:4px 10px">{s["cap"]}</div>' if s.get("cap") else ""
        return f'<div class="s">{tiles}{bandh}{tg}{pg}{capd}{swipe}</div>'
    if k == "swatch":
        items = s["imgs"]; m = len(items)
        side = 72; gap = 18
        top = (560 if tall else 390)
        tw = (W - side * 2 - gap * (m - 1)) // m
        th = (H - top - (560 if tall else 250))
        tiles = ""
        for j, it in enumerate(items):
            x = side + j * (tw + gap)
            sub = f'<small>{it["sub"]}</small>' if it.get("sub") else ""
            tiles += (f'<div class="tile" style="left:{x}px;top:{top}px;width:{tw}px;height:{th}px;border-radius:4px">'
                      f'<img src="{img_data(P(it["img"]), it.get("crop"), (tw, th))}"></div>'
                      f'<div class="lab" style="left:{x - 10}px;width:{tw + 20}px;top:{top + th + 22}px;{"font-size:24px;" if m >= 5 else ""}">{it["label"]}{sub}</div>')
        body = f'<p style="margin-top:18px;font-size:32px">{s["p"]}</p>' if s.get("p") else ""
        return (f'<div class="s solid sw">{tg}{pg}<div class="txt top" style="top:{top - (240 if s.get("p") else 170)}px">'
                f'<h2 style="font-size:56px">{s["h"]}</h2>{body}</div>{tiles}'
                f'<div class="cap" style="color:#1d1d1d">{s.get("cap", "")}</div></div>')
    if k == "detail":
        # 전체 사진 + 원형 확대경 (같은 사진의 한 부분을 크게)
        lx, ly, z = s.get("lens", [0.5, 0.5, 3.0])
        R = 400 if not tall else 460
        if s.get("lens_at"):
            pos = s["lens_at"]
        else:   # 확대경을 원래 그 자리 위에 올린다
            iw, ih = ImageOps.exif_transpose(Image.open(P(s["img"]))).size
            x0, y0, cw, ch = crop_box(iw, ih, s.get("crop"), (W, H))
            px = (lx * iw - x0) / cw * W; py = (ly * ih - y0) / ch * H
            pos = [int(min(max(px - R / 2, 40), W - R - 40)), int(min(max(py - R / 2, 200), H - R - 420))]
        lens_src = img_data(P(s["img"]), [lx, ly, z], (R, R))
        head = f'<h3>{s["h"]}</h3>' if s.get("h") else ""
        body = f'<p>{s["p"]}</p>' if s.get("p") else ""
        ll = f'<div class="lensl" style="left:{pos[0]}px;top:{pos[1] + R + 18}px;width:{R}px;text-align:center">{s["lens_label"]}</div>' if s.get("lens_label") else ""
        return (f'<div class="s"><img class="bg" src="{img_data(P(s["img"]), s.get("crop"), (W, H))}">'
                f'<div class="tshade"></div><div class="fshade"></div>{tg}{pg}'
                f'<div class="lens" style="left:{pos[0]}px;top:{pos[1]}px;width:{R}px;height:{R}px"><img src="{lens_src}"></div>{ll}'
                f'<div class="ftxt">{head}{body}</div>{cap}{swipe}</div>')
    if k == "steps":
        items = s["items"]; m = len(items)
        top = (470 if tall else 300) + (70 if s.get("p") else 0)
        avail = H - top - (440 if tall else 170)
        rowh = avail // m
        rows = ""
        for j, it in enumerate(items):
            y = top + j * rowh
            if it.get("icon") in ICONS:
                badge = (f'<svg viewBox="0 0 240 180" style="position:absolute;left:72px;top:{y}px;width:240px;height:180px">'
                         f'{ICONS[it["icon"]]}</svg>')
            else:
                badge = (f'<div style="position:absolute;left:72px;top:{y}px;width:120px;height:120px;border-radius:50%;'
                         f'background:{BRAND};color:#fff;font-size:56px;font-weight:900;text-align:center;line-height:120px">{it.get("n", j + 1)}</div>')
            tx = 350 if it.get("icon") in ICONS else 230
            rows += badge + (f'<div style="position:absolute;left:{tx}px;right:72px;top:{y + 6}px">'
                     f'<div style="font-size:26px;font-weight:800;color:{BRAND};letter-spacing:.06em">{it.get("k", "")}</div>'
                     f'<div style="font-size:44px;font-weight:800;margin-top:4px">{it["t"]}</div>'
                     f'<div style="font-size:30px;line-height:1.5;margin-top:10px;opacity:.8">{it.get("d", "")}</div></div>')
        body = f'<p style="margin-top:16px;font-size:32px">{s["p"]}</p>' if s.get("p") else ""
        return (f'<div class="s solid">{tg}{pg}<div class="txt top" style="top:{150 if not tall else 300}px">'
                f'<h2 style="font-size:58px">{s["h"]}</h2>{body}</div>{rows}'
                f'<div class="cap" style="color:#1d1d1d">{s.get("cap", "")}</div></div>')
    raise ValueError(f"unknown slide type: {k}")


def _shoot(pages, out, W, H, quality=88):
    from playwright.sync_api import sync_playwright
    out.mkdir(parents=True, exist_ok=True)
    files = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        for name, html in pages:
            pg.set_content(html)
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(120)
            png = pg.screenshot(type="png")
            f = out / name
            Image.open(io.BytesIO(png)).convert("RGB").save(f, "JPEG", quality=quality, optimize=True)
            files.append(f)
        b.close()
    return files


def render_carousel(spec_path, out):
    spec_path = Path(spec_path); spec = json.load(open(spec_path, encoding="utf-8"))
    W, H = 1080, 1350
    slides = spec["slides"]; n = len(slides)
    assert 2 <= n <= 10, "캐러셀은 2~10장"
    pages = []
    for i, s in enumerate(slides, 1):
        html = (f'<html><head><meta charset="utf-8"><style>{css(W, H, False)}</style></head><body>'
                f'{slide_html(s, i, n, spec["tag"], spec_path.parent, W, H, False)}</body></html>')
        pages.append((f"{i:02d}.jpg", html))
    return _shoot(pages, Path(out), W, H)


def reel_slides(spec):
    """스펙에 'reel' 목록이 있으면 그걸, 없으면 캐러셀에서 자동 추출.
    릴스는 짧아야 하므로: 표지 + 중간 최대 4장(사진·숫자 우선) + 마지막 CTA, 사진 슬라이드는 제목만."""
    if spec.get("reel"):
        return spec["reel"]
    sl = spec["slides"]
    first, last = sl[0], sl[-1]
    PRI = {"full": 0, "photo": 0, "detail": 0, "duo": 1, "grid": 1, "swatch": 1, "number": 2, "steps": 3, "text": 3, "table": 4}
    mid = [s for s in sl[1:-1] if s["type"] in PRI]
    mid.sort(key=lambda s: PRI[s["type"]])
    keep = set(id(s) for s in mid[:4])
    mid = [s for s in sl[1:-1] if id(s) in keep]          # 원래 순서 유지
    out = []
    for s in [first] + mid + [last]:
        s2 = dict(s)
        if s2["type"] in ("photo", "full", "detail"):
            s2.pop("p", None)
        if s2["type"] in ("number", "text", "table", "cta"):
            s2.pop("cap", None)
        out.append(s2)
    return out


def render_frames(spec_path, out):
    """릴스·스토리용 9:16 프레임."""
    spec_path = Path(spec_path); spec = json.load(open(spec_path, encoding="utf-8"))
    W, H = 1080, 1920
    slides = reel_slides(spec); n = len(slides)
    pages = []
    for i, s in enumerate(slides, 1):
        html = (f'<html><head><meta charset="utf-8"><style>{css(W, H, True)}</style></head><body>'
                f'{slide_html(s, i, n, spec["tag"], spec_path.parent, W, H, True)}</body></html>')
        pages.append((f"f{i:02d}.jpg", html))
    return _shoot(pages, Path(out), W, H, quality=92)
