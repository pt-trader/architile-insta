"""스펙 1개 → 게시 패키지 docs/p/<id>/ 생성.

  python tools/build.py specs/2026-10-06_case01_corner.json

생성물
  docs/p/<id>/01.jpg ...      캐러셀 (1080x1350)
  docs/p/<id>/story.jpg       스토리 (1080x1920)
  docs/p/<id>/reel.mp4        릴스 (spec에 reel_at이 있을 때)
  docs/p/<id>/reel_cover.jpg
  docs/p/<id>/post.json       게시 일정·캡션 (publish.py가 읽음)

스펙 필수 필드: id, tag, tier(GREEN/BLUE/RED/BLACK/CASE/BRAND), slides, caption, hashtags,
               feed_at("YYYY-MM-DDTHH:MM", KST)
선택: story(기본 true), reel_at, reel_caption, reel(릴스 전용 슬라이드 목록), alt
"""
import json, re, shutil, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from render import render_carousel, render_frames, reel_slides  # noqa: E402
from reel import build_reel  # noqa: E402
from rules import lint, full_caption  # noqa: E402

def build(spec_path):
    spec_path = Path(spec_path).resolve()
    spec = json.load(open(spec_path, encoding="utf-8"))
    errs = lint(spec)
    if errs:
        raise SystemExit("❌ 규칙 위반\n  - " + "\n  - ".join(errs))
    pid = spec["id"]
    out = ROOT / "docs" / "p" / pid
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    imgs = render_carousel(spec_path, out)
    def alt_of(s):
        t = " ".join(str(s.get(k, "")) for k in ("pre", "num", "unit", "h", "p"))
        t += " " + " ".join(f'{it.get("label", "")} {it.get("sub", "")}' for it in s.get("imgs", []))
        t += " " + " ".join(f'{it.get("t", "")} {it.get("d", "")}' for it in s.get("items", []))
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)).strip()[:300]
    alts = spec.get("alt") or [alt_of(s) for s in spec["slides"]]
    items = [{"kind": "carousel", "at": spec["feed_at"], "images": [f.name for f in imgs],
              "alt": alts, "caption": full_caption(spec)}]

    need_frames = spec.get("story", True) or spec.get("reel_at")
    if need_frames:
        with tempfile.TemporaryDirectory() as td:
            frames = render_frames(spec_path, td)
            if spec.get("story", True):
                shutil.copy(frames[0], out / "story.jpg")
                items.append({"kind": "story", "at": spec["feed_at"], "image": "story.jpg"})
            if spec.get("reel_at"):
                dur = build_reel(frames, reel_slides(spec), out / "reel.mp4",
                                 music_dir=ROOT / "assets" / "music", seed=pid)
                shutil.copy(frames[0], out / "reel_cover.jpg")
                items.append({"kind": "reel", "at": spec["reel_at"], "video": "reel.mp4",
                              "cover": "reel_cover.jpg", "duration": round(dur, 1),
                              "caption": full_caption(spec, "reel_caption")})
    post = {"id": pid, "tier": spec["tier"], "tag": spec["tag"], "items": items}
    json.dump(post, open(out / "post.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"✅ {pid}: " + ", ".join(f"{i['kind']}@{i['at']}" for i in items))
    return out


if __name__ == "__main__":
    for p in sys.argv[1:]:
        build(p)
