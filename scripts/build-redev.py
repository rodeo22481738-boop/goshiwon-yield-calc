"""
수도권(서울·경기·인천) 정비구역 경계 GeoJSON 생성 스크립트.

입력:
  서울   : 서울 열린데이터광장 "서울시 의제처리구역 위치정보"(OA-20957) SHP zip
           https://data.seoul.go.kr/dataList/OA-20957/F/1/datasetView.do  (자동 다운로드, 반기 갱신)
  경기·인천: 브이월드 "(연속주제)_도시및주거환경정비/정비구역" SHP (dsId 30335, 국토교통부)
           로그인이 필요해 자동 다운로드가 안 되므로 data/vendor/ 에 넣어둔 zip 을 사용 (분기 갱신)
  scripts/seoul_gu.json  — 서울 자치구 경계 (구역이 어느 구인지 공간조인용, repo 에 포함)
출력:
  data/redev.geojson  — index.html 이 fetch 해서 지도에 그림

  python scripts/build-redev.py           # 서울은 scratch_redev/uq181.zip, 경기·인천은 vendor zip
  python scripts/build-redev.py --fetch   # 서울 최신 zip 을 다시 받아서 빌드

브이월드 파일 갱신법(분기): www.vworld.kr 로그인 → dsId 30335 →
  LSMD_CONT_UD602_5174_경기.zip / _인천.zip 받아 data/vendor/ 에 덮어쓰고 commit.
  라이선스 CC BY-NC-ND (비상업 이용 · 출처 국토교통부 표시).

GitHub Actions(.github/workflows/update-redev.yml)가 매달 --fetch 로 돌려서(서울만 최신화)
변경 있으면 자동 커밋 → Cloudflare Pages 자동 배포. (사용자 PC 안 켜져 있어도 됨)
필요 패키지: pip install pyshp pyproj shapely
"""
import io, json, sys, re, zipfile, pathlib, collections, urllib.request
import shapefile  # pyshp
from pyproj import Transformer
from shapely.geometry import shape, mapping
from shapely.ops import unary_union, transform as shp_transform
from shapely.strtree import STRtree

DATASET_PAGE = "https://data.seoul.go.kr/dataList/OA-20957/F/1/datasetView.do"
DOWNLOAD_API = "https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do"

HERE = pathlib.Path(__file__).resolve().parent
SHP_ZIP = HERE.parent / "scratch_redev" / "uq181.zip"
GU_JSON = HERE / "seoul_gu.json"
VENDOR = HERE.parent / "data" / "vendor"
VWORLD_ZIPS = {
    "경기": VENDOR / "LSMD_CONT_UD602_5174_경기.zip",
    "인천": VENDOR / "LSMD_CONT_UD602_5174_인천.zip",
}
OUT = HERE.parent / "data" / "redev.geojson"

# 서울 SHP: 포함할 분류(MLSFC_CL 또는 ATRB_SE) → 표시 라벨. UQ1206(정비해제)·소규모정비는 제외.
CAT = {
    "UQ1210": "주거환경개선",
    "UQ1220": "재개발",
    "UQ1230": "재건축",
    "UQ1240": "정비예정구역",
    "UQ1250": "정비구역",
    "UQ1200": "정비구역",
    "UQ5110": "재정비촉진지구",
    "UQ5120": "재정비촉진지구",
    "UQ5130": "재정비촉진지구",
}
EXCLUDE = {"UQ1206"}

SIMPLIFY_DEG = 0.00003   # 약 3m (필지 경계 수준). "핀이 구역 안인가" 판정용.
COORD_NDIGITS = 5


# ── 서울: 열린데이터광장 의제처리구역 ────────────────────────────
def download_zip(dest):
    """OA-20957 데이터셋 페이지에서 최신 파일 seq 를 찾아 zip 다운로드."""
    def get(url, data=None):
        req = urllib.request.Request(url, data=data,
                                     headers={"User-Agent": "Mozilla/5.0"})
        return urllib.request.urlopen(req, timeout=60).read()

    html = get(DATASET_PAGE).decode("utf-8", "replace")
    seqs = [int(m) for m in re.findall(r"downloadFile\('(\d+)'\)", html)]
    if not seqs:
        sys.exit("데이터셋 페이지에서 다운로드 링크를 못 찾음 — 사이트 구조가 바뀐 듯")
    seq = max(seqs)
    body = f"infId=OA-20957&seq={seq}&infSeq=1&useCache=false".encode()
    blob = get(DOWNLOAD_API, body)
    if blob[:2] != b"PK":
        sys.exit(f"받은 파일이 zip 이 아님 (seq={seq}, {len(blob)} bytes)")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(blob)
    print(f"서울 다운로드 완료: seq={seq}, {len(blob)/1024:.0f} KB → {dest}")


def load_seoul_reader(zip_path):
    zf = zipfile.ZipFile(zip_path)
    names = {p.rsplit("/", 1)[-1].lower(): p for p in zf.namelist()}
    b = "upis_c_uq181"
    parts = {e: zf.read(names[f"{b}.{e}"]) for e in ("shp", "dbf", "shx", "prj")}
    r = shapefile.Reader(shp=io.BytesIO(parts["shp"]), dbf=io.BytesIO(parts["dbf"]),
                         shx=io.BytesIO(parts["shx"]), encoding="cp949")
    return r, parts["prj"].decode("utf-8")


def load_gu():
    d = json.loads(GU_JSON.read_text(encoding="utf-8"))
    polys, names = [], []
    for f in d["features"]:
        polys.append(shape(f["geometry"]))
        names.append(f["properties"]["name"])
    return STRtree(polys), polys, names


def gu_of(pt, tree, polys, names):
    for i in tree.query(pt):
        if polys[i].contains(pt):
            return names[i]
    return "서울시"


def build_seoul():
    if "--fetch" in sys.argv or not SHP_ZIP.exists():
        download_zip(SHP_ZIP)
    r, prj_wkt = load_seoul_reader(SHP_ZIP)
    flds = [f[0] for f in r.fields[1:]]
    to_wgs = Transformer.from_crs(prj_wkt, "EPSG:4326", always_xy=True).transform
    gu_tree = load_gu()

    # 같은 고시번호(NTFC_SN)+구역명 = 한 구역. 필지별로 쪼개진 폴리곤을 합침.
    groups = collections.OrderedDict()
    for sh, rec in zip(r.iterShapes(), r.iterRecords()):
        d = dict(zip(flds, rec))
        mls, atrb = d["MLSFC_CL"], d["ATRB_SE"]
        if atrb in EXCLUDE or mls in EXCLUDE:
            continue
        cat = CAT.get(mls) or CAT.get(atrb)
        if not cat or not sh.points:
            continue
        geom = shape(sh.__geo_interface__).buffer(0)
        if geom.is_empty:
            continue
        name = (d["DGM_NM"] or "").strip() or "(구역명 없음)"
        key = (d["NTFC_SN"] or d["PRESENT_SN"], name)
        g = groups.get(key)
        if g is None:
            groups[key] = {"cat": cat, "name": name, "geoms": [geom]}
        else:
            g["geoms"].append(geom)

    feats = []
    for g in groups.values():
        m = unary_union(g["geoms"]) if len(g["geoms"]) > 1 else g["geoms"][0]
        m = shp_transform(to_wgs, m).simplify(SIMPLIFY_DEG, preserve_topology=True)
        if m.is_empty:
            continue
        gu = gu_of(m.representative_point(), *gu_tree)
        feats.append({
            "type": "Feature",
            "properties": {"name": g["name"], "cat": g["cat"], "gu": gu},
            "geometry": _round(mapping(m), COORD_NDIGITS),
        })
    return feats


# ── 경기·인천: 브이월드 도시및주거환경정비/정비구역 ─────────────────
def vworld_cat(text):
    if "재정비촉진" in text: return "재정비촉진지구"
    if "재건축" in text: return "재건축"
    if "재개발" in text: return "재개발"
    if "주거환경개선" in text or "주거환경관리" in text: return "주거환경개선"
    if "정비예정" in text: return "정비예정구역"
    return "정비구역"


def vworld_name(alias, remark):
    for s in (alias, remark):
        s = re.sub(r"\s+", " ", (s or "").strip())
        if not s:
            continue
        if re.match(r"^\d{4}[.\-/]", s):        # 날짜만 들어간 칸
            continue
        if s.endswith("용지") or "행위제한" in s:  # 세부용지·행위제한 설명
            continue
        return s
    return "(구역명 미상)"


def build_vworld():
    feats, by_sido = [], collections.Counter()
    for sido, zp in VWORLD_ZIPS.items():
        if not zp.exists():
            print(f"  ! {zp.name} 없음 — {sido} 건너뜀 (www.vworld.kr dsId 30335 에서 받아 data/vendor/ 에)")
            continue
        z = zipfile.ZipFile(zp)
        base = next(n[:-4] for n in z.namelist() if n.lower().endswith(".shp"))
        prj = z.read(base + ".prj").decode("utf-8", "replace")
        to_wgs = Transformer.from_crs(prj, "EPSG:4326", always_xy=True).transform
        r = shapefile.Reader(shp=io.BytesIO(z.read(base + ".shp")), dbf=io.BytesIO(z.read(base + ".dbf")),
                             shx=io.BytesIO(z.read(base + ".shx")), encoding="cp949")
        flds = [f[0] for f in r.fields[1:]]
        for sh, rec in zip(r.iterShapes(), r.iterRecords()):
            d = dict(zip(flds, rec))
            if "UDT1" not in (d.get("MNUM") or ""):   # UDT999… = 행위제한지역, 제외
                continue
            if not sh.points:
                continue
            g = shape(sh.__geo_interface__).buffer(0)
            if g.is_empty:
                continue
            g = shp_transform(to_wgs, g).simplify(SIMPLIFY_DEG, preserve_topology=True)
            if g.is_empty:
                continue
            txt = f"{d.get('ALIAS', '')} {d.get('REMARK', '')}"
            feats.append({
                "type": "Feature",
                "properties": {"name": vworld_name(d.get("ALIAS"), d.get("REMARK")),
                               "cat": vworld_cat(txt), "gu": sido},
                "geometry": _round(mapping(g), COORD_NDIGITS),
            })
            by_sido[sido] += 1
    for s, n in by_sido.items():
        print(f"  {s}: {n}")
    return feats


def main():
    seoul = build_seoul()
    vworld = build_vworld()
    _check(seoul, vworld)
    feats = seoul + vworld

    OUT.parent.mkdir(exist_ok=True)
    fc = {"type": "FeatureCollection",
          "meta": {"source": "서울: 열린데이터광장 OA-20957 / 경기·인천: 브이월드 30335 (국토교통부)",
                   "zones": len(feats)},
          "features": feats}
    OUT.write_text(json.dumps(fc, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    by_cat = collections.Counter(f["properties"]["cat"] for f in feats)
    print(f"wrote {OUT.name}  {OUT.stat().st_size/1024:.0f} KB  {len(feats)} zones "
          f"(서울 {len(seoul)} + 경기·인천 {len(vworld)})")
    for c, n in by_cat.most_common():
        print(f"  {c}: {n}")


def _check(seoul, vworld):
    """재투영·필터가 깨지면 실패하는 최소 확인."""
    from shapely.geometry import Point, shape
    # 서울: 성북구 장위동 68-2 부근은 정비구역 안, 광화문 한복판은 밖.
    inside = Point(127.0518, 37.6128)
    outside = Point(126.9769, 37.5759)
    assert any(shape(f["geometry"]).contains(inside) for f in seoul), \
        "장위동 68-2 가 어떤 정비구역에도 안 들어감 — 서울 좌표/필터 확인"
    assert not any(shape(f["geometry"]).contains(outside) for f in seoul + vworld), \
        "광화문이 정비구역으로 잡힘 — 재투영 확인"
    # 경기·인천: vendor zip 이 실제로 반영됐고 좌표가 수도권 범위인지.
    assert len(vworld) > 200, \
        f"경기·인천 구역이 너무 적음 ({len(vworld)}) — data/vendor zip 확인"
    for f in vworld[::20]:
        c = shape(f["geometry"]).representative_point()
        assert 36.8 < c.y < 38.4 and 125.9 < c.x < 127.7, \
            f"경기·인천 좌표가 수도권 밖: {c.y:.3f},{c.x:.3f} — 재투영 확인"
    print("self-check OK")


def _round(o, nd):
    if isinstance(o, float):
        return round(o, nd)
    if isinstance(o, (list, tuple)):
        return [_round(x, nd) for x in o]
    if isinstance(o, dict):
        return {k: _round(v, nd) for k, v in o.items()}
    return o


if __name__ == "__main__":
    main()
