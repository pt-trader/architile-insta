"""인스타 장기 토큰 갱신 (60일 만료 → 매주 갱신). 새 토큰을 stdout 마지막 줄에 출력한다.
GitHub Actions(refresh-token.yml)가 이 값을 IG_TOKEN 시크릿에 다시 저장한다."""
import json, os, sys, urllib.parse, urllib.request

tok = os.environ["IG_TOKEN"]
url = "https://graph.instagram.com/refresh_access_token?" + urllib.parse.urlencode(
    {"grant_type": "ig_refresh_token", "access_token": tok})
with urllib.request.urlopen(url, timeout=60) as r:
    d = json.loads(r.read())
new = d["access_token"]
days = int(d.get("expires_in", 0)) // 86400
print(f"::add-mask::{new}")
print(f"토큰 갱신 완료 — 남은 유효기간 {days}일", file=sys.stderr)
out = os.environ.get("GITHUB_OUTPUT")
if out:
    with open(out, "a") as f:
        f.write(f"token={new}\n")
