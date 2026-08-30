# 고시원 수익률 자동 분석기

방개수·보증금·권리금·방별임대료를 넣으면 월 순수익·연 수익률·원금 회수기간을 즉시 계산하는 단일 페이지 웹앱.
주소를 넣으면 주변 고시원 시세, 그리고 **그 위치가 서울시 재개발·재건축 구역인지**를 지도에서 바로 확인.

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
| 이 주소가 재개발·재건축 구역인지 지도로 보기 | 앱 안에 카카오 지도 임베드 → 서울시 정비구역 경계를 색으로 표시 + 내 주소 핀. 핀이 색 구역 안이면 그 구역명·유형 표시 |
| 토지이음에서 공식 확인 | 지번을 클립보드에 복사하고 토지이음 열기 (검색창에 Ctrl+V) |
| 서울 정비사업 공식 현황 | 정비사업 정보몽땅 (자치구 직접 선택) |

재개발 지도는 **서울시만** 커버(데이터 출처가 서울 전용). 서울 밖 주소는 토지이음 링크만 뜬다.
경계는 약 3m 단순화됐고 원본도 법적 효력 없는 참고자료 — 확정 판단은 토지이음에서.

## 재개발 구역 데이터 갱신 — 자동

`data/redev-seoul.geojson` 은 **GitHub Actions 가 매달 15일** 자동으로 갱신한다
(`.github/workflows/update-redev.yml`). 동작:

1. GitHub 서버에서 실행 — **내 PC 안 켜져 있어도 됨**
2. 서울 열린데이터광장 [OA-20957](https://data.seoul.go.kr/dataList/OA-20957/F/1/datasetView.do)
   최신 SHP 를 받아 `scripts/build-redev-seoul.py --fetch` 실행
3. 서울시 원본이 바뀌었을 때만 커밋 & 푸시 → Cloudflare Pages 자동 재배포
4. 원본 포맷이 바뀌어 스크립트가 실패하면 커밋 안 하고 GitHub 이 실패 알림 메일 발송

수동 실행: GitHub 저장소 → **Actions 탭 → "재개발 구역 데이터 갱신" → Run workflow**

로컬에서 직접 돌리려면:
```
pip install pyshp pyproj shapely
python scripts/build-redev-seoul.py --fetch
```

`scripts/seoul_gu.json` (자치구 경계, 구역이 어느 구인지 태깅용)은 repo에 포함.

## 배포 (GitHub Pages)

```
git push
```

Settings → Pages → Source `main` / `/ (root)`.
배포 URL을 카카오 콘솔 Web 도메인에 추가하는 것 잊지 말 것.
