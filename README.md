# 고시원 수익률 자동 분석기

방개수·보증금·권리금·방별임대료를 넣으면 월 순수익·연 수익률·원금 회수기간을 즉시 계산하는 단일 페이지 웹앱.
주소를 넣으면 반경 2km 지도에 **내 위치 핀 + 주변 고시원·원룸텔 + 서울 재개발·재건축 구역**을 표시.

- 프레임워크·빌드 없음. `index.html` 하나 + 정적 데이터.
- 매물 여러 개 저장/불러오기는 브라우저 `localStorage` (기기별 로컬, 동기화 아님).
- 서버·DB·회원 없음. 지도만 카카오맵 JS SDK 사용.

## 로컬 실행

```
python -m http.server 8777
# http://localhost:8777/index.html
```

`file://` 로 열면 카카오맵 도메인 제한과 `fetch` 때문에 안 됨. 반드시 http 서버로.

## 카카오맵 키 설정 (지도 기능에 필수)

1. https://developers.kakao.com 로그인 → **내 애플리케이션** → 애플리케이션 추가
2. **앱 키** 탭에서 **JavaScript 키**, **REST API 키** 복사
3. **플랫폼** → Web → 사이트 도메인 등록:
   - `http://localhost:8777` (로컬 테스트)
   - `https://<github-id>.github.io` (배포)
4. **카카오맵** → 활성화 설정 ON
5. `index.html` 상단의 `window.KAKAO_JS_KEY = "REPLACE_WITH_KAKAO_JS_KEY"` 를 JavaScript 키로 교체

무료 한도 일 30만 건(지도/지오코딩/키워드검색 각각). 카드/비즈월렛을 직접 등록하지 않으면 초과해도
429 에러가 날 뿐 **과금 없음**. 개인/커뮤니티 규모에선 한도 근처도 안 감.

## 재개발·재건축 데이터 갱신 (분기별, 선택)

지도의 재개발 구역은 `data/redevelopment.json` (서울시만). 갱신 방법:

1. https://www.data.go.kr/data/15097425/fileData.do 에서 CSV 다운로드 → `data/seoul_jeongbi_raw.csv` 로 저장
2. `KAKAO_REST_KEY=<REST 키> node scripts/build-redev.mjs`
3. 바뀐 `data/redevelopment.json` 커밋 & 푸시

서울 외 지역은 데이터가 없어 지도에 안 뜸(전국 통합 공개 API 없음). 앱이 재재맵·정비사업 정보몽땅 링크로 안내함.

## 배포 (GitHub Pages)

```
git push
```

Settings → Pages → Source: `main` / `/ (root)` 활성화되어 있으면 푸시만으로 반영.
배포 URL을 카카오 개발자 콘솔 Web 플랫폼 도메인에 등록해야 지도가 뜸.

## 알려진 한계

- 고시원 **방값(월세)은 지도에 안 뜸** — 카카오 장소 데이터에 없음. 마커의 카카오맵 링크로 확인.
- 재개발 데이터는 서울시, 분기별 수동 갱신.
- 계산 로직은 원본 엑셀(`고시원임장보고서`)과 대조 검증됨. `HANDOFF.md` 참고.
