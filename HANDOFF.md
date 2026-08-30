# 고시원 수익률 자동계산기 — 인수인계 문서

최종 갱신: 2026-08-30

## 현재 상태 (한 줄)

단일 파일 웹앱 `index.html`. 배포 라이브. 직전 작업 **재개발 지도 수도권(서울·경기·인천) 확장** 완료·푸시·배포 검증까지 끝남. 미결 작업 없음.

## 프로젝트 개요

- 원본: `고시원임장보고서 (본인판단) 최종.xlsx` 의 매물 수익률 계산 로직을 브라우저 단일 페이지로 재구현.
- 스택: 프레임워크·빌드·백엔드 없음. `index.html` + 정적 데이터 파일(`data/redev.geojson`).
- 지도/주소검색: 카카오맵 JS SDK. JS 키 `a66749202196f535a2d455027bf172ca` (도메인 제한, 공개돼도 안전).
- 매물 저장: 브라우저 `localStorage` (`goshiwon_properties_v2`, 기기별 로컬).
- 계산 로직은 엑셀과 대조 검증 완료 — **이번 세션에서 안 건드림**.

### 배포

- GitHub repo: `https://github.com/rodeo22481738-boop/goshiwon-yield-calc.git` (branch `main`)
- Cloudflare Pages: `https://goshiwon-yield-calc.pages.dev` — `main` 에 푸시하면 자동 재배포
- `/index.html` → `/` 로 308 리다이렉트 (정상)

## 이번 세션에서 한 일 — 재개발 지도 수도권 확장

**배경**: 재개발 구역 지도가 서울만 커버했음. 경기·인천(수도권)까지 확장 요청.

**확정한 방향** (AskUserQuestion 로 사용자가 선택):
- 전국 폴리곤 지도 방식 (O/X 판정 폴백 아님)
- 데이터 갱신: **서울=자동, 경기·인천=분기 수동**. VWorld 로그인 자격증명은 CI 에 저장 안 함.

**핵심 발견**:
- 국가공간정보포털(nsdi.go.kr)은 **서비스 종료·폐기됨**. 공간정보는 전부 **브이월드(vworld.kr)** 로 이관.
- 정비구역 폴리곤 데이터 = 브이월드 공간정보 다운로드 **dsId 30335** "(연속주제)_도시및주거환경정비/정비구역" (국토교통부, SHP, 시도별 분할, EPSG:5174, CC BY-NC-ND, ~분기 갱신).
- 브이월드는 **다운로드에 로그인 필요** → 자동화 불가 → 분기 수동.
- 서울은 기존대로 서울 열린데이터광장 OA-20957 (로그인 불필요, 자동화 유지).

**만든/바꾼 파일**:

| 파일 | 상태 | 내용 |
|---|---|---|
| `scripts/build-redev.py` | 신규 (구 `build-redev-seoul.py` 대체) | 서울(자동 다운로드) + 경기·인천(vendor zip) → `data/redev.geojson`. `--fetch` 로 서울 최신 SHP 재다운로드. |
| `data/redev.geojson` | 신규 (구 `redev-seoul.geojson` 대체) | 1970개 구역 `{name, cat, gu}`. 서울 1547 + 경기·인천 423. ~1.2MB (gzip ~260KB). |
| `data/vendor/LSMD_CONT_UD602_5174_경기.zip` | 신규 커밋 | 브이월드 원본 zip 그대로 (CC BY-NC-ND, 비영리 원본 재배포 허용). |
| `data/vendor/LSMD_CONT_UD602_5174_인천.zip` | 신규 커밋 | 〃 |
| `data/vendor/SOURCE.md` | 신규 | 출처·라이선스 표기 |
| `index.html` | 수정 (5군데, 계산 로직 무변경) | fetch 경로 `redev-seoul.geojson`→`redev.geojson`, 경계박스 서울→수도권(`lat 36.8~38.35`, `lng 125.9~127.95`), 안내 문구 "서울"→"수도권(서울·경기·인천)" |
| `.github/workflows/update-redev.yml` | 수정 | 스크립트/산출물 파일명을 `build-redev.py` / `redev.geojson` 로 |
| `README.md` | 수정 | "서울"→"수도권", 경기·인천 분기 수동 갱신 5단계 절차 추가 |
| `scripts/build-redev-seoul.py`, `data/redev-seoul.geojson` | `git rm` | |

**커밋**: `a6ebcc8` "재개발 지도 수도권(서울·경기·인천) 확장" — 푸시 완료, Cloudflare 배포 라이브 검증됨.

**데이터 품질 처리** (브이월드 원본이 지저분함):
- `MNUM` 에 `UDT1` 포함된 것만 = 실제 정비구역 (`UDT999` = 행위제한지역, 제외)
- 구역명은 `ALIAS` + `REMARK` 자유텍스트에서 파싱, 없으면 `(구역명 미상)` (경기 ~96/309건)
- `gu` = 시도명 (index.html 렌더링에서 안 쓰는 필드라 행정구역 개편 코드 추적 안 함)

## 갱신 방법 (README 에도 있음)

- **서울**: `.github/workflows/update-redev.yml` 이 매달 15일 GitHub 서버에서 자동. 수동 실행은 Actions 탭 → "재개발 구역 데이터 갱신" → Run workflow.
- **경기·인천 (분기, ~5분)**:
  1. vworld.kr 로그인
  2. `https://www.vworld.kr/dtmk/dtmk_ntads_s002.do?svcCde=MK&dsId=30335`
  3. `LSMD_CONT_UD602_5174_경기.zip`, `_인천.zip` 다운로드
  4. `data/vendor/` 의 기존 파일 덮어쓰기 (파일명 그대로)
  5. `python scripts/build-redev.py` → `git add data/vendor data/redev.geojson && git commit && git push`
- 로컬 빌드: `pip install pyshp pyproj shapely` 후 `python scripts/build-redev.py`

## 다음에 할 일

**미결 없음.** 사용자 지시 대기.

- (사용자 확인 필요) 배포된 사이트에서 경기·인천 주소로 지도가 뜨는지 최종 확인 — 강력 새로고침(Ctrl+Shift+R) 후 테스트. 이전에 사용자가 옛 캐시 화면 보고 "안 뜬다"고 했던 건이라 재확인 필요.
- (선택) 다른 시도 확장이 필요하면 같은 방식으로 `data/vendor/` 에 zip 추가 + `build-redev.py` 의 `VWORLD_ZIPS` dict 에 항목 추가.
- (선택) 브이월드 로그인 다운로드가 API 화되면 경기·인천도 자동화 검토.

## 회귀 검증 기준값

숫자만 입력 (원룸 27 / 방별 390 / 보증금 30000 / 권리금 145000 / 임차료 4070 / 관리비 1000 / 입실률 90%)
→ 월 순수익 279만 / 연수익률 18.6% / 회수기간 53개월 (이번 세션에서 확인됨)
