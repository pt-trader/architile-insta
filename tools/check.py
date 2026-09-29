"""게시물 검사 — PR마다 GitHub가 자동 실행. 문제 있으면 빨간 X로 표시된다.

검사 항목
  - 스펙: 금지 표기·등급별 금지어·해시태그 5개·캡션 길이 (build.py의 lint 재사용)
  - 파일: 존재, JPEG, 캐러셀 4:5(1080x1350), 스토리·릴스 표지 9:16, 8MB 이하
  - 릴스: 3~90초, 300MB 이하 (ffprobe 있을 때)
  - 일정: 피드(캐러셀·릴스) 간격 최소 3시간, 같은 날 피드 2개 초과 금지
"""
import json, shutil, subprocess, sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from PIL import Image  # noqa: E402

errs, warns = [], []
state = json.load(open(ROOT / "state" / "published.json", encoding="utf-8")) if (ROOT / "state" / "published.json").exists() else {}

from rules import lint  # noqa: E402
for sp in sorted((ROOT / "specs").glob("*.json")):
    for e in lint(json.load(open(sp, encoding="utf-8"))):
        errs.append(f"{sp.name}: {e}")


def img_check(p, want, label):
    if not p.exists():
        errs.append(f"{label}: 파일 없음 {p.name}"); return
    if p.stat().st_size > 8 * 1024 * 1024:
        errs.append(f"{label}: 8MB 초과 {p.name}")
    with Image.open(p) as im:
        if im.format != "JPEG":
            errs.append(f"{label}: JPEG 아님 {p.name}")
        if im.size != want:
            errs.append(f"{label}: 크기 {im.size} ≠ {want} ({p.name})")


feeds = []
for pj in sorted((ROOT / "docs" / "p").glob("*/post.json")):
    post = json.load(open(pj, encoding="utf-8")); d = pj.parent; pid = post["id"]
    for it in post["items"]:
        key = f"{pid}#{it['kind']}"
        if state.get(key, {}).get("media_id"):
            continue                                   # 이미 올라간 건 검사 안 함
        at = datetime.fromisoformat(it["at"])
        if it["kind"] == "carousel":
            if not 2 <= len(it["images"]) <= 10:
                errs.append(f"{key}: 캐러셀 {len(it['images'])}장")
            for f in it["images"]:
                img_check(d / f, (1080, 1350), key)
            feeds.append((at, key))
        elif it["kind"] == "story":
            img_check(d / it["image"], (1080, 1920), key)
        elif it["kind"] == "reel":
            img_check(d / it["cover"], (1080, 1920), key)
            v = d / it["video"]
            if not v.exists():
                errs.append(f"{key}: 영상 없음")
            else:
                if v.stat().st_size > 300 * 1024 * 1024:
                    errs.append(f"{key}: 300MB 초과")
                if shutil.which("ffprobe"):
                    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                                "-of", "csv=p=0", str(v)], capture_output=True, text=True).stdout or 0)
                    if not 3 <= dur <= 90:
                        errs.append(f"{key}: 길이 {dur:.1f}초 (3~90초)")
            feeds.append((at, key))
        if "caption" in it and len(it["caption"]) > 2200:
            errs.append(f"{key}: 캡션 2200자 초과")
        if at < datetime.now() - timedelta(hours=1):
            warns.append(f"{key}: 예정 시각 {it['at']} 이 이미 지남 → 머지하면 바로 올라감")

feeds.sort()
for (a, ka), (b, kb) in zip(feeds, feeds[1:]):
    if b - a < timedelta(hours=3):
        errs.append(f"피드 간격 3시간 미만: {ka} {a:%m-%d %H:%M} / {kb} {b:%m-%d %H:%M}")
per_day = {}
for a, k in feeds:
    per_day.setdefault(a.date(), []).append(k)
for day, ks in per_day.items():
    if len(ks) > 2:
        errs.append(f"{day} 피드 {len(ks)}개 (하루 최대 2개)")

for w in warns:
    print("⚠", w)
for e in errs:
    print("❌", e)
print(f"검사 끝 — 오류 {len(errs)} / 경고 {len(warns)} / 대기 피드 {len(feeds)}개")
sys.exit(1 if errs else 0)
