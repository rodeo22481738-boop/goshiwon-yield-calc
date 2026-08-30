# 고시원 수익률 자동 분석기

방개수·보증금·권리금·방별임대료를 넣으면 월 순수익·연 수익률·원금 회수기간을 즉시 계산하는 단일 페이지 웹앱.
주소를 넣으면 주변 고시원 시세, 그리고 **그 위치가 수도권(서울·경기·인천) 재개발·재건축 구역인지**를 지도에서 바로 확인.

- 프레임워크·빌드·백엔드 없음. `index.html` + 정적 데이터 파일 하나.
- 지도·주소검색은 카카오맵 JS SDK (JS 키 1개, 도메인 제한 걸어 공개돼도 안전).
- 매물 여러 개 저장/불러오기는 브라우저 `localStorage` (기기별 로컬, 동기화 아님).
- 계산 로직은 원본 엑셀(`고시원임장보고서`)과 대조 검증됨. `HANDOFF.md` 참고.

## 로컬 실행

```
python -m http.server 8777
# http://localhost:8777/index.html
```

카카오 지도 기능을 쓰려면 카카오 개발자 콘솔 → 앱 → 플랫폼 Web → 사이트 도메인에
`http://localhost:8777` 과 배포 도메인을 등록해야 한다.

## 주변 정보 확인

주소를 입력하면 활성화됨:

| 버튼 | 동작 |
|---|---|
| 주변 고시원·원룸텔 시세 | 카카오맵 `{구 동} 고시원` 을 그 좌표 중심으로 열기 |
| 이 주소가 재개발·재건축 구역인지 지도로 보기 | 앱 안에 카카오 지도 임베드 → 수도권 정비구역 경계를 색으로 표시 + 내 주소 핀. 핀이 색 구역 안이면 그 구역명·유형 표시 |
| 토지이음에서 공식 확인 | 지번을 클립보드에 복사하고 토지이음 열기 (검색창에 Ctrl+V) |
| 서울 정비사업 공식 현황 | 정비사업 정보몽땅 (서울 자치구 직접 선택) |

재개발 지도는 **수도권(서울·경기·인천)** 커버. 그 밖 주소는 토지이음 링크만 뜬다.
경계는 약 3m 단순화됐고 원본도 법적 효력 없는 참고자료 — 확정 판단은 토지이음에서.

## 재개발 구역 데이터 (`data/redev.geojson`)

| 지역 | 출처 | 갱신 |
|---|---|---|
| 서울 | 서울 열린데이터광장 [OA-20957](https://data.seoul.go.kr/dataList/OA-20957/F/1/datasetView.do) 의제처리구역 SHP | **자동** (GitHub Actions 매달 15일) |
| 경기·인천 | 브이월드 "(연속주제)_도시및주거환경정비/정비구역" (dsId 30335, 국토교통부, CC BY-NC-ND) | **수동** (분기, 아래) |

### 서울 — 자동

`.github/workflows/update-redev.yml` 가 매달 15일 GitHub 서버에서 실행 (**내 PC 꺼져 있어도 됨**).
서울 최신 SHP 를 받아 `scripts/build-redev.py --fetch` 로 재빌드 → 커밋된 경기·인천 데이터와 합쳐
`data/redev.geojson` 생성 → 서울 원본이 바뀐 경우에만 커밋 & 푸시 → Cloudflare Pages 자동 재배포.
스크립트가 실패하면 커밋 안 하고 GitHub 이 실패 알림 메일 발송.

수동 실행: GitHub 저장소 → **Actions 탭 → "재개발 구역 데이터 갱신" → Run workflow**

### 경기·인천 — 분기 수동 (약 5분)

브이월드는 다운로드에 로그인이 필요해 자동화하지 않았다. 분기마다:

1. <https://www.vworld.kr> 로그인 (회원가입 무료)
2. <https://www.vworld.kr/dtmk/dtmk_ntads_s002.do?svcCde=MK&dsId=30335> 접속
3. "데이터 리소스"에서 `LSMD_CONT_UD602_5174_경기.zip`, `LSMD_CONT_UD602_5174_인천.zip` 다운로드
4. `data/vendor/` 의 기존 두 파일을 덮어쓰기 (파일명 그대로)
5. `python scripts/build-redev.py` 실행 → `git add data/vendor data/redev.geojson && git commit && git push`

### 로컬 빌드

```
pip install pyshp pyproj shapely
python scripts/build-redev.py            # 서울 캐시 + 경기·인천 vendor zip
python scripts/build-redev.py --fetch    # 서울 최신 SHP 다시 받기
```

`scripts/seoul_gu.json` (서울 자치구 경계, 구역이 어느 구인지 태깅용)과
`data/vendor/*.zip` (경기·인천 원본, 국토교통부 CC BY-NC-ND 출처표시)는 repo 에 포함.

## 배포 (GitHub Pages)

```
git push
```

Settings → Pages → Source `main` / `/ (root)`.
배포 URL을 카카오 콘솔 Web 도메인에 추가하는 것 잊지 말 것.
