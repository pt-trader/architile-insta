"""표기·등급 규칙 검사 (architile_blog/_data/용어_표기규칙.md 기준). build.py와 check.py가 같이 쓴다."""
import json, re

PHONE = "031.306.9630"

# ── 표기 규칙 (architile_blog/_data/용어_표기규칙.md 기준) ──
BANNED = ["진흥인터내셔날", "architile.co.kr", "공식 취급점", "대리점", "세라믹 타일", "세라믹타일",
          "청수", "자기질", "CE 인증", "의장 의도", "휘도차", "세라비오 G", "세라비오G", "세라비오 U", "세라비오U",   # 단종 예정
          "저가", "고가",
          "리즈믹", "RYC-"]   # 리즈믹Ⅱ 국내 미판매(2026-09-29 확정)
PREMIUM_BANNED = ["유지비", "LCC", "가격", "만원", "견적서", "30년", "비싸", "저렴"]   # BLUE·RED·BLACK은 가격·LCC 언급 금지
# 카탈로그 사진 중 스타벅스 매장 (로고·매장 노출) — 사용 금지 (2026-09-29 브로 지시)
BLOCKED_IMAGES = ["p01_646", "p31_415", "p33_431", "p34_439", "p34_441", "p35_445", "p36_455", "p37_465", "p39_486",
                  # 세라비오R 폴더 DSC0393x·K10023: 출처 미확인(엔화 가격표 노출 컷 포함) — 브로 확인 전 사용 금지
                  "DSC0393", "DSC0394", "K10023_",
                  # 국내 미수입 색(세키하 SKH-2·3) — 국내 색으로 오인될 수 있어 사용 금지
                  "2020_SKH-2", "2020_SKH-3", "re_a02_", "STS-14",
                  "2020_1000361475", "YUKAGE-", "2020_Ramdom-HB-3", "2020_Romdom-HB-5", "p18_244"]   # 국내 미수입 색·타 제품
MAX_TAGS = 5
MAX_CAPTION = 2200


def lint(spec):
    errs = []
    blob = json.dumps(spec, ensure_ascii=False)
    for w in BANNED:
        hit = re.search(r"(?<![재층])고가", blob) if w == "고가" else (w in blob)   # '재고가·층고가'는 가격 표현 아님
        if hit:
            errs.append(f"금지 표기: {w}")
    if spec.get("tier") in ("BLUE", "RED", "BLACK"):
        for w in PREMIUM_BANNED:
            if w in blob:
                errs.append(f"{spec['tier']} 등급 금지어: {w}")
    if re.search(r"031-306-9630|031 306 9630", blob):
        errs.append(f"연락처는 {PHONE} 표기로 통일")
    tags = spec.get("hashtags", [])
    if len(tags) > MAX_TAGS:
        errs.append(f"해시태그 {len(tags)}개 → 최대 {MAX_TAGS}개")
    cap = full_caption(spec)
    if len(cap) > MAX_CAPTION:
        errs.append(f"캡션 {len(cap)}자 → 최대 {MAX_CAPTION}자")
    n = len(spec["slides"])
    if not 2 <= n <= 10:
        errs.append(f"캐러셀 {n}장 → 2~10장")
    pairs = []   # (이미지 경로, 그 이미지에 붙는 캡션)
    for s in spec["slides"] + spec.get("reel", []):
        if s.get("img"):
            pairs.append((s["img"], s.get("cap", "")))
        for it in s.get("imgs", []):
            pairs.append((it["img"], s.get("cap", "") + " " + it.get("cap", "")))
    for img, cap in pairs:
        catalog_case = "/catalog/사례_" in img
        mfr = ("INAX_official" in img or "architile.co.kr" in img or "-list-img-ori" in img
               or ("/architile/" in img and not catalog_case))
        if "/architile/" in img and not cap.strip():
            errs.append(f"사진 출처 캡션 필요: {img}")
        if mfr and "제조사" not in cap:
            errs.append(f"제조사 이미지 캡션에 '(제조사 제품 이미지)' 필요: {img}")
        if any(b in img for b in BLOCKED_IMAGES):
            errs.append(f"사용 금지 사진: {img}")
        if catalog_case and ("적용 사례" not in cap or "파사드웍스" in cap or "카탈로그" in cap):
            errs.append(f"카탈로그 시공사례는 캡션 '아키타일 적용 사례'만 (파사드웍스·카탈로그 표기 금지): {img}")
        if "INAX_official/projects" in img and "일본" not in cap:
            errs.append(f"일본 현장 사진은 '일본 적용 사례(제조사 자료)' 명시: {img}")
        if "@cases/" in img and "파사드웍스" not in cap:
            errs.append(f"우리 현장 사진은 '파사드웍스 시공 현장' 명시: {img}")
    for k in ("id", "tag", "tier", "caption", "feed_at"):
        if not spec.get(k):
            errs.append(f"필수 필드 없음: {k}")
    return errs


def full_caption(spec, key="caption"):
    return spec.get(key, spec["caption"]).rstrip() + "\n\n" + " ".join(spec.get("hashtags", []))


