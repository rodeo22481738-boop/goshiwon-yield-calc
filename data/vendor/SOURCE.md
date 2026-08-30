# 경기·인천 정비구역 원본 데이터

- **출처**: 국토교통부 "(연속주제)_도시및주거환경정비/정비구역"
- **배포**: 브이월드(V-World) 공간정보 다운로드, dsId 30335
  <https://www.vworld.kr/dtmk/dtmk_ntads_s002.do?svcCde=MK&dsId=30335>
- **라이선스**: CC BY-NC-ND (저작자표시-비영리-변경금지)
- **좌표계**: EPSG:5174 (Korean 1985 / Modified Central Belt)

이 폴더의 `LSMD_CONT_UD602_5174_경기.zip`, `LSMD_CONT_UD602_5174_인천.zip` 은
브이월드에서 받은 원본 zip 을 그대로 둔 것이다. `scripts/build-redev.py` 가 읽어
서울 데이터와 합쳐 `data/redev.geojson` 을 만든다.

갱신 방법은 저장소 루트 `README.md` 참고.
