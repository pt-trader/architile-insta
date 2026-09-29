"""게시 현황판 docs/index.html 생성 — https://<아이디>.github.io/<저장소>/ 에서 휴대폰으로 확인.
예정/완료/실패를 날짜순으로 보여준다. publish 워크플로가 매시간 다시 만든다."""
import html, json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo("Asia/Seoul")
KIND = {"carousel": "캐러셀", "reel": "릴스", "story": "스토리"}

state = json.load(open(ROOT / "state" / "published.json", encoding="utf-8")) if (ROOT / "state" / "published.json").exists() else {}
rows = []
for pj in sorted((ROOT / "docs" / "p").glob("*/post.json")):
    post = json.load(open(pj, encoding="utf-8"))
    for it in post["items"]:
        if it["kind"] == "story":
            continue
        key = f"{post['id']}#{it['kind']}"
        rec = state.get(key, {})
        st = "done" if rec.get("media_id") else ("fail" if rec.get("attempts", 0) >= 3 else ("retry" if rec.get("error") else "wait"))
        thumb = it.get("images", [None])[0] if it["kind"] == "carousel" else it.get("cover")
        has = thumb and (pj.parent / thumb).exists()
        rows.append((it["at"], post, it, rec, st, f"p/{post['id']}/{thumb}" if has else None))
rows.sort(key=lambda r: r[0])

LABEL = {"done": "게시 완료", "wait": "예정", "retry": "재시도 중", "fail": "실패 — 확인 필요"}
cards = []
for at, post, it, rec, st, thumb in rows:
    t = datetime.fromisoformat(at)
    cap = html.escape(it.get("caption", "").split("\n")[0])
    img = f'<img src="{thumb}" alt="" loading="lazy">' if thumb else '<div class="noimg">미디어 정리됨</div>'
    link = f'<a href="{html.escape(rec["permalink"])}">인스타에서 보기 →</a>' if rec.get("permalink") else ""
    err = f'<div class="err">{html.escape(rec.get("error", ""))[:200]}</div>' if st in ("retry", "fail") else ""
    cards.append(f'''<li class="card {st}">{img}<div class="meta">
<div class="when">{t:%m/%d} ({"월화수목금토일"[t.weekday()]}) {t:%H:%M} · {KIND[it["kind"]]}</div>
<div class="cap">{cap}</div><div class="tag">{html.escape(post["tag"])}</div>
<span class="st">{LABEL[st]}</span> {link}{err}</div></li>''')

n = {k: sum(1 for r in rows if r[4] == k) for k in LABEL}
now = datetime.now(KST)
page = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>파사드웍스 인스타 현황</title><style>
:root{{--bg:#f6f4f1;--card:#fff;--ink:#1d1d1d;--mute:#6b6661;--line:#e4dfd9;--brand:#851B20;--ok:#2f6b3a;--warn:#9a6a00;--bad:#b3261e}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#161413;--card:#211e1c;--ink:#eee9e4;--mute:#a39c95;--line:#35302c;--brand:#d0676d;--ok:#7cc48a;--warn:#e0b44c;--bad:#f08a82}}}}
:root[data-theme="dark"]{{--bg:#161413;--card:#211e1c;--ink:#eee9e4;--mute:#a39c95;--line:#35302c;--brand:#d0676d;--ok:#7cc48a;--warn:#e0b44c;--bad:#f08a82}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif}}
main{{max-width:760px;margin:0 auto;padding:24px 16px 60px}}h1{{font-size:20px;margin:0 0 4px}}
.sub{{color:var(--mute);font-size:13px;margin-bottom:18px}}.sum{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:18px}}
.sum span{{background:var(--card);border:1px solid var(--line);border-radius:999px;padding:4px 12px;font-size:13px}}
ul{{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:minmax(0,1fr);gap:10px}}
.card{{display:flex;gap:12px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px}}
.card img,.noimg{{width:84px;height:105px;object-fit:cover;border-radius:6px;flex:none;background:var(--line)}}
.noimg{{display:flex;align-items:center;justify-content:center;font-size:11px;color:var(--mute);text-align:center}}
.meta{{min-width:0;flex:1}}.when{{font-weight:700}}.cap{{margin:2px 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.tag{{color:var(--mute);font-size:12px}}.st{{display:inline-block;margin-top:4px;font-size:12px;font-weight:700;color:var(--mute)}}
.done .st{{color:var(--ok)}}.retry .st{{color:var(--warn)}}.fail .st{{color:var(--bad)}}.fail{{border-color:var(--bad)}}
a{{color:var(--brand);font-size:13px;margin-left:6px}}.err{{font-size:12px;color:var(--bad);margin-top:4px;word-break:break-all}}
</style></head><body><main><h1>파사드웍스 인스타 현황</h1>
<div class="sub">갱신 {now:%Y-%m-%d %H:%M} KST · 매시 17분 자동 확인</div>
<div class="sum"><span>예정 {n["wait"]}</span><span>완료 {n["done"]}</span><span>재시도 {n["retry"]}</span><span>실패 {n["fail"]}</span></div>
<ul>{"".join(cards) or "<li>대기 중인 게시물이 없어요</li>"}</ul></main></body></html>'''
(ROOT / "docs" / "index.html").write_text(page, encoding="utf-8")
(ROOT / "docs" / ".nojekyll").write_text("")
print(f"현황판 갱신: 예정 {n['wait']} / 완료 {n['done']}")
