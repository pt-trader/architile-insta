# 파사드웍스 인스타 자동 게시

블로그 원고(`architile_blog`)를 잘게 쪼갠 캐러셀·릴스·스토리를 **검수 후 예약 게시**하는 저장소.

```
Claude가 만든다 ─▶ PR(검수 요청) ─▶ 브로가 확인·머지 ─▶ 예약 시각에 자동 게시 ─▶ 현황판 갱신
 specs/*.json       썸네일·캡션 확인      = 승인             GitHub Actions 매시 17분     docs/index.html
```

- **main 브랜치에 들어온 것 = 승인된 것.** 머지 안 하면 절대 안 올라감
- 급하게 멈추려면: Settings → Secrets and variables → Actions → **Variables** 에서 `PAUSED` = `true`
- 현황판: `https://<깃허브아이디>.github.io/architile-insta/` (휴대폰으로 보면 됨)

---

## 처음 1회 설정 (브로가 할 일, 약 40분)

순서대로. 막히면 그 화면 캡처해서 Claude한테 보내면 된다.

### A. 인스타그램 계정 (10분)

1. 인스타 앱에서 새 계정 만들기 (예: `facadeworks`)
2. **설정 → 계정 유형 및 도구 → 프로페셔널 계정으로 전환 → 비즈니스**
   - 카테고리: 건축 자재 / 건설 관련 중 하나
   - 연락처: `031.306.9630`, `facadeworks@naver.com`
3. 프로필 사진·소개·링크(네이버 블로그) 채우기
4. **처음 1~2주는 앱에서 직접도 조금씩 써주기** (프로필 편집, 다른 계정 몇 개 팔로우 등).
   새 계정이 첫날부터 API로만 올리면 스팸 의심을 받을 수 있다

### B. Meta 개발자 앱 (15분)

> Meta 화면 문구는 자주 바뀐다. 이름이 조금 달라도 같은 위치의 메뉴를 찾으면 됨.

1. <https://developers.facebook.com> → 페이스북 계정으로 로그인 → 개발자 등록 (처음이면)
2. **내 앱 → 앱 만들기**
   - 앱 이름: `facadeworks-publisher` (이름에 Instagram/Facebook 넣으면 거절됨)
   - 사용 사례: **"Instagram에서 메시지 및 콘텐츠 관리"** (없으면 "기타 → 비즈니스")
   - 비즈니스 포트폴리오: 연결 안 함으로 진행해도 됨
3. 앱 대시보드 → **앱 역할(App roles) → 역할 → 사람 추가 → Instagram 테스터** → A에서 만든 인스타 아이디 입력
4. **인스타에서 초대 수락** ← 가장 많이 빠뜨리는 단계
   - 웹: <https://www.instagram.com/accounts/manage_access/> → **테스터 초대** 탭 → 수락
   - 앱: 설정 → 웹사이트 권한 → 앱 및 웹사이트 → 테스터 초대
5. 앱 대시보드 → **Instagram → Instagram 로그인을 사용한 API 설정**
   - 권한에 `instagram_business_basic`, `instagram_business_content_publish` 가 있는지 확인
   - **1. 액세스 토큰 생성 → 계정 추가** → 인스타 로그인·허용 → **토큰 생성** → 나온 긴 문자열 복사 (메모장에 잠깐)
6. 같은 화면 또는 **앱 설정 → 기본 설정**에서 **Instagram 앱 시크릿** 복사 (메모장에 잠깐)

앱은 **개발 모드 그대로** 둔다. 브로 계정 하나에만 올리는 용도라 앱 검수(App Review)는 필요 없다.

### C. GitHub (15분)

1. <https://github.com> 가입 (이미 있으면 로그인)
2. 오른쪽 위 **+ → New repository**
   - 이름: `architile-insta` / **Public** / 나머지 체크 없이 **Create**
   - Public이어야 GitHub Pages(이미지 공개 주소)와 Actions가 무료다. 올라갈 이미지는 어차피 인스타에 공개될 것들이고, 토큰 같은 비밀값은 저장소가 아니라 Secrets에 들어가서 안 보인다
3. **Claude가 이 저장소에 코드를 올릴 수 있게 연결**
   - claude.ai → 설정 → 커넥터 → **GitHub 연결** → `architile-insta` 접근 허용
   - 연결되면 Claude한테 "올려"라고 하면 Claude가 코드를 push 한다
4. **개인 토큰(PAT) 만들기** — Actions가 인스타 토큰을 스스로 갱신하는 데 씀
   - 오른쪽 위 프로필 → Settings → Developer settings → **Personal access tokens → Fine-grained tokens → Generate new token**
   - 이름 `insta-bot`, 만료: 가장 긴 기간, Repository access: **Only select repositories → architile-insta**
   - Permissions → Repository permissions: **Secrets: Read and write**, **Variables: Read and write**
   - Generate → 나온 값 복사
5. 저장소 → **Settings → Secrets and variables → Actions → New repository secret** 3개

   | Name | Value |
   |---|---|
   | `IG_TOKEN` | B-5에서 복사한 인스타 토큰 |
   | `IG_APP_SECRET` | B-6에서 복사한 앱 시크릿 |
   | `GH_PAT` | C-4에서 만든 개인 토큰 |

6. (Claude가 코드를 올린 뒤) 저장소 → **Settings → Pages** → Source: **Deploy from a branch** → Branch: `main` / 폴더 `/docs` → Save
7. 저장소 → **Actions** 탭 → 워크플로 사용 허용 → 왼쪽 **"처음 1회 - 인스타 연결 확인"** → **Run workflow**
   - 초록 체크 + 로그에 `연결된 계정: @facadeworks` 나오면 끝
8. 같은 Actions 탭 → **"인스타 예약 게시" → Run workflow → dry_run: true** 로 한 번 돌려서 올릴 목록이 제대로 잡히는지 확인

---

## 매주 운영 (첫 한 달 = 검수 후 업로드)

1. 브로 → Claude: "다음 주 거 만들어"
2. Claude가 다음 주 분량(캐러셀 5~6개 + 릴스 2개 + 스토리)을 만들어 **PR** 로 올림
   - PR 본문에 날짜·시간·썸네일·캡션이 다 보임
   - 자동 **게시물 검사**(금지 표기, 해시태그 5개, 연락처 표기, 이미지 규격, 피드 간격)가 돌고 초록 체크가 떠야 정상
3. 브로가 휴대폰으로 PR 확인
   - 고칠 게 있으면 PR에 댓글 → Claude가 수정해서 다시 올림
   - 괜찮으면 **Merge pull request** = 승인
4. 예약 시각이 되면 매시 17분 실행에서 자동 게시. 결과는 현황판·Actions 탭에서 확인
5. 게시가 3번 연속 실패하면 GitHub가 메일로 알려주고 그 항목은 멈춘다

## 기본 게시 시간

| 요일 | 피드 | 릴스 |
|---|---|---|
| 월~금 | 12:10 캐러셀 (+같은 시각 스토리) | 수 20:10 |
| 토 | — | 토 11:10 |

GitHub 예약 실행은 몇 분~수십 분 늦어질 수 있다. 12:10 예정이면 보통 12:17~12:40 사이에 올라간다.

---

## 폴더

```
specs/        게시물 설계 (슬라이드 문구·사진·캡션·예약 시각)  ← Claude가 작성
docs/p/<id>/  렌더 결과 (01.jpg… story.jpg reel.mp4 post.json)  ← 인스타가 여기서 이미지를 가져감
docs/index.html  현황판
state/published.json  게시 기록 (미디어 ID·링크)
tools/        render(캐러셀) · reel(릴스) · build(패키지) · rules(표기 규칙) · check(검사) · publish(게시) · board(현황판)
assets/music/ mp3를 넣으면 릴스 배경음으로 랜덤 사용 (저작권 없는 음원만). 비어 있으면 무음
```

## 규칙 (architile_blog/_data/용어_표기규칙.md 따름)

- 연락처 `031.306.9630` 통일
- 금지: 진흥인터내셔날, architile.co.kr, 공식 취급점, 대리점, 세라믹 타일, 저가/고가 …
- BLUE·RED·BLACK 제품은 가격·유지비·LCC 언급 금지 (GREEN만 LCC)
- 제조사 이미지엔 `(제조사 제품 이미지)`, INAX 일본 현장은 `일본 적용 사례(제조사 자료)` 표기
- 파사드웍스가 시공하지 않은 현장을 우리 사례처럼 쓰지 않는다
- 해시태그 최대 5개 (인스타 2026 정책)

## 알아둘 것

- 인스타 토큰은 60일짜리. 매주 월요일 자동 갱신된다. **60일 넘게 갱신이 끊기면 B-5부터 다시** 해야 한다
- 공개 저장소의 예약 실행은 저장소에 60일간 변화가 없으면 GitHub가 멈춘다. 게시할 때마다 기록이 커밋되니 운영 중엔 문제없음
- 게시 끝난 지 3일 지난 이미지·영상은 자동 삭제(인스타에 이미 올라가 있음). 저장소 용량 관리용
- 자동으로 하는 건 **우리 계정 안의 게시·기록뿐**. 남의 게시물 자동 좋아요·댓글·팔로우는 인스타 금지 사항이라 넣지 않았다
