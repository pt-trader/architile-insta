"""예약 게시 실행기 — GitHub Actions가 매시간 돌린다.

docs/p/*/post.json 을 훑어서, 게시 시각(at, KST)이 지났고 아직 안 올라간 항목을 올린다.
main 브랜치에 들어와 있는 것 = 브로가 검수(PR 머지)한 것 = 올려도 되는 것.

환경변수
  IG_TOKEN      인스타 장기 토큰 (GitHub Secret)
  IG_USER_ID    인스타 계정 ID (없으면 토큰으로 조회)
  PAGES_BASE    이미지 공개 주소 루트. 예: https://<아이디>.github.io/architile-insta
  PAUSED        "true"면 아무것도 안 올림 (긴급 정지 스위치)
  DRY_RUN       "true"면 API 호출 없이 무엇을 올릴지만 출력
  MAX_FEED      한 번 실행에 올릴 피드(캐러셀·릴스) 최대 개수. 기본 1 — 밀린 게 몰려서 폭주하지 않게
"""
import json, os, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "state" / "published.json"
KST = ZoneInfo("Asia/Seoul")
API = os.environ.get("IG_API", "https://graph.instagram.com/v25.0")   # 테스트 때만 바꿈
MAX_ATTEMPTS = 3
MEDIA_EXT = (".jpg", ".mp4")

env = os.environ.get
DRY = env("DRY_RUN", "").lower() == "true"


# ─────────────── HTTP ───────────────
def call(method, path, **params):
    params["access_token"] = env("IG_TOKEN")
    url = f"{API}/{path}"
    data = None
    if method == "GET":
        url += "?" + urllib.parse.urlencode(params)
    else:
        data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"{method} {path} → {e.code}: {body}") from None


def url_ok(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, method="HEAD"), timeout=30) as r:
            return r.status == 200
    except Exception:
        return False


def wait_ready(cid, timeout=600, every=10):
    t0 = time.time()
    while True:
        st = call("GET", cid, fields="status_code,status")
        code = st.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"컨테이너 {cid} 실패: {st}")
        if time.time() - t0 > timeout:
            raise RuntimeError(f"컨테이너 {cid} 처리 시간 초과: {st}")
        time.sleep(every)


def publish_container(ig, cid):
    r = call("POST", f"{ig}/media_publish", creation_id=cid)
    mid = r["id"]
    try:
        link = call("GET", mid, fields="permalink").get("permalink")
    except Exception:
        link = None
    return mid, link


# ─────────────── 게시 종류별 ───────────────
def do_carousel(ig, base, it):
    kids = []
    for name, alt in zip(it["images"], it.get("alt", [""] * len(it["images"]))):
        p = dict(image_url=f"{base}/{name}", is_carousel_item="true")
        if alt:
            p["alt_text"] = alt[:1000]
        try:
            kids.append(call("POST", f"{ig}/media", **p)["id"])
        except RuntimeError as e:
            if "alt_text" in str(e):                      # alt_text 미지원 응답이면 빼고 재시도
                p.pop("alt_text"); kids.append(call("POST", f"{ig}/media", **p)["id"])
            else:
                raise
    for k in kids:
        wait_ready(k, timeout=120, every=3)
    cid = call("POST", f"{ig}/media", media_type="CAROUSEL", children=",".join(kids),
               caption=it["caption"])["id"]
    wait_ready(cid, timeout=180, every=5)
    return publish_container(ig, cid)


def do_story(ig, base, it):
    cid = call("POST", f"{ig}/media", media_type="STORIES", image_url=f"{base}/{it['image']}")["id"]
    wait_ready(cid, timeout=120, every=3)
    return publish_container(ig, cid)


def do_reel(ig, base, it):
    cid = call("POST", f"{ig}/media", media_type="REELS", video_url=f"{base}/{it['video']}",
               cover_url=f"{base}/{it['cover']}", caption=it["caption"], share_to_feed="true")["id"]
    wait_ready(cid, timeout=900, every=15)
    return publish_container(ig, cid)


DO = {"carousel": do_carousel, "story": do_story, "reel": do_reel}


# ─────────────── 상태 ───────────────
def load_state():
    return json.load(open(STATE, encoding="utf-8")) if STATE.exists() else {}


def save_state(s):
    STATE.parent.mkdir(exist_ok=True)
    json.dump(s, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)


def due_items(state, now):
    out = []
    for pj in sorted((ROOT / "docs" / "p").glob("*/post.json")):
        post = json.load(open(pj, encoding="utf-8"))
        for it in post["items"]:
            key = f"{post['id']}#{it['kind']}"
            rec = state.get(key, {})
            if rec.get("media_id") or rec.get("attempts", 0) >= MAX_ATTEMPTS:
                continue
            at = datetime.fromisoformat(it["at"]).replace(tzinfo=KST)
            if at <= now:
                out.append((at, key, post, it))
    out.sort(key=lambda x: (x[0], x[2]["id"], 0 if x[3]["kind"] != "story" else 1))
    return out


def cleanup(state, now, keep_days=3):
    """모든 항목이 올라간 지 keep_days 지난 게시물은 이미지·영상 삭제(post.json만 남김). 저장소 용량 관리."""
    removed = 0
    for pj in (ROOT / "docs" / "p").glob("*/post.json"):
        post = json.load(open(pj, encoding="utf-8"))
        recs = [state.get(f"{post['id']}#{it['kind']}", {}) for it in post["items"]]
        if recs and all(r.get("media_id") for r in recs):
            last = max(datetime.fromisoformat(r["published_at"]) for r in recs)
            if now - last > timedelta(days=keep_days):
                for f in pj.parent.iterdir():
                    if f.suffix in MEDIA_EXT:
                        f.unlink(); removed += 1
    if removed:
        print(f"🧹 게시 완료 미디어 {removed}개 정리")


def main():
    now = datetime.now(KST)
    if env("FAKE_NOW"):                      # 테스트 전용
        now = datetime.fromisoformat(env("FAKE_NOW")).replace(tzinfo=KST)
    if env("PAUSED", "").lower() == "true":
        print("⏸ PAUSED=true — 게시 중단 상태"); return
    state = load_state()
    todo = due_items(state, now)
    if not todo:
        print(f"{now:%Y-%m-%d %H:%M} 올릴 것 없음"); cleanup(state, now); save_state(state); return

    pages = env("PAGES_BASE", "").rstrip("/")
    if not pages:
        sys.exit("PAGES_BASE 가 비어 있음")
    ig = env("IG_USER_ID")
    if not DRY:
        if not ig:
            ig = call("GET", "me", fields="user_id,username")["user_id"]
        lim = call("GET", f"{ig}/content_publishing_limit", fields="quota_usage,config")
        print("게시 한도:", lim.get("data"))

    max_feed = int(env("MAX_FEED", "1"))
    fed = 0; failed = False
    for at, key, post, it in todo:
        if it["kind"] != "story":
            if fed >= max_feed:
                print(f"⏭ {key} 다음 실행으로 미룸 (MAX_FEED={max_feed})"); continue
        else:
            feed_key = f"{post['id']}#carousel"
            if feed_key in [k for _, k, _, _ in todo] and not state.get(feed_key, {}).get("media_id"):
                print(f"⏭ {key} 피드 게시 후에 올림"); continue
        base = f"{pages}/p/{post['id']}"
        files = it.get("images") or [it.get("image") or it.get("video")] + ([it["cover"]] if it.get("cover") else [])
        print(f"▶ {key}  (예정 {at:%m-%d %H:%M}, {len(files)}개 파일)")
        if DRY:
            if it["kind"] != "story": fed += 1
            state.setdefault(key, {})["dry_run_ok"] = now.isoformat(timespec="minutes")
            continue
        missing = [f for f in files if not url_ok(f"{base}/{f}")]
        if missing:
            print(f"  ⚠ 공개 주소에 아직 없음(Pages 배포 대기?): {missing}"); continue
        rec = state.setdefault(key, {})
        try:
            mid, link = DO[it["kind"]](ig, base, it)
            rec.update(media_id=mid, permalink=link, published_at=now.isoformat(timespec="minutes"))
            rec.pop("error", None)
            print(f"  ✅ 게시 완료 {link or mid}")
            if it["kind"] != "story": fed += 1
        except Exception as e:
            rec["attempts"] = rec.get("attempts", 0) + 1
            rec["error"] = str(e)[:500]
            failed = True
            print(f"  ❌ 실패 ({rec['attempts']}/{MAX_ATTEMPTS}): {e}")
        save_state(state)
    cleanup(state, now)
    save_state(state)
    if failed:
        sys.exit(1)   # 실패하면 GitHub가 브로 메일로 알림


if __name__ == "__main__":
    main()
