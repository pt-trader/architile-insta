"""처음 1회: 브로가 IG_TOKEN 시크릿에 넣은 토큰을 확인하고 60일짜리로 바꿔 저장한다.
  1) 토큰으로 계정 조회 → 계정명 출력 (맞는 계정인지 로그로 확인)
  2) IG_APP_SECRET 이 있으면 단기 토큰 → 장기(60일) 토큰 교환 시도. 이미 장기면 그대로 둔다.
  3) GITHUB_OUTPUT 으로 token, user_id, username 전달 → 워크플로가 시크릿·변수에 저장
토큰 값은 로그에 절대 찍히지 않게 마스킹한다."""
import json, os, sys, urllib.error, urllib.parse, urllib.request

G = "https://graph.instagram.com"


def get(url, **q):
    try:
        with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(q), timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"_error": e.read().decode(errors="replace")[:300]}


tok = os.environ.get("IG_TOKEN", "").strip()
if not tok:
    sys.exit("❌ IG_TOKEN 시크릿이 비어 있어요. Settings → Secrets and variables → Actions 에 넣어주세요.")
print(f"::add-mask::{tok}")

me = get(f"{G}/v25.0/me", fields="user_id,username,account_type", access_token=tok)
if "_error" in me:
    sys.exit(f"❌ 토큰으로 계정 조회 실패 — 토큰을 다시 복사해 넣어주세요.\n{me['_error']}")
print(f"✅ 연결된 계정: @{me.get('username')} ({me.get('account_type')}) / user_id {me.get('user_id')}")

new, days = tok, None
secret = os.environ.get("IG_APP_SECRET", "").strip()
if secret:
    ex = get(f"{G}/access_token", grant_type="ig_exchange_token", client_secret=secret, access_token=tok)
    if "access_token" in ex:
        new = ex["access_token"]; days = int(ex.get("expires_in", 0)) // 86400
        print(f"::add-mask::{new}")
        print(f"✅ 장기 토큰으로 교환 완료 — 유효기간 {days}일")
    else:
        print("ℹ 교환 생략 (이미 장기 토큰이거나 앱 시크릿 불일치). 그대로 사용합니다.")
else:
    print("ℹ IG_APP_SECRET 없음 → 교환 생략. 대시보드에서 만든 토큰은 보통 60일짜리입니다.")

out = os.environ.get("GITHUB_OUTPUT")
if out:
    with open(out, "a") as f:
        f.write(f"token={new}\nuser_id={me.get('user_id')}\nusername={me.get('username')}\n")
