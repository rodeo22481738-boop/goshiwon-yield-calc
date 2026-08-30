"""
서울시 정비구역(재개발·재건축·재정비촉진 등) 경계 GeoJSON 생성 스크립트.

입력:
  scratch_redev/uq181.zip  — 서울 열린데이터광장 "서울시 의제처리구역 위치정보"(OA-20957) SHP zip
     https://data.seoul.go.kr/dataList/OA-20957/F/1/datasetView.do  →  파일내려받기 최신 zip
  scripts/seoul_gu.json    — 서울 자치구 경계 (구역이 어느 구인지 공간조인용, repo 에 포함)
출력:
  data/redev-seoul.geojson — index.html 이 fetch 해서 지도에 그림

새 zip 을 받으면 scratch_redev/uq181.zip 을 교체하고 다시 실행. (반기 갱신)
필요 패키지: pip install pyshp pyproj shapely
"""
import io, json, sys, zipfile, pathlib, collections
import shapefile  # pyshp
from pyproj import Transformer
from shapely.geometry import shape, mapping
from shapely.ops import unary_union, transform as shp_transform
from shapely.prepared import prep
from shapely.strtree import STRtree

HERE = pathlib.Path(__file__).resolve().parent
SHP_ZIP = HERE.parent / "scratch_redev" / "uq181.zip"
GU_JSON = HERE / "seoul_gu.json"
OUT = HERE.parent / "data" / "redev-seoul.geojson"

# 포함할 분류(MLSFC_CL 또는 ATRB_SE) → 표시 라벨. UQ1206(정비해제)·소규모정비는 제외.
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

SIMPLIFY_DEG = 0.00012   # 약 12m. "핀이 구역 안인가" 판정엔 충분.
COORD_NDIGITS = 5


def load_reader(zip_path):
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


def main():
    if not SHP_ZIP.exists():
        sys.exit(f"SHP zip 없음: {SHP_ZIP}")
    r, prj_wkt = load_reader(SHP_ZIP)
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

    OUT.parent.mkdir(exist_ok=True)
    fc = {"type": "FeatureCollection",
          "meta": {"source": "서울 열린데이터광장 OA-20957 의제처리구역",
                   "zones": len(feats)},
          "features": feats}
    OUT.write_text(json.dumps(fc, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    by_cat = collections.Counter(f["properties"]["cat"] for f in feats)
    by_gu = collections.Counter(f["properties"]["gu"] for f in feats)
    print(f"wrote {OUT.name}  {OUT.stat().st_size/1024:.0f} KB  {len(feats)} zones")
    for c, n in by_cat.most_common():
        print(f"  {c}: {n}")
    print("구 미상:", by_gu.get("서울시", 0))
    _check(feats)


def _check(feats):
    """재투영·필터가 깨지면 실패하는 최소 확인."""
    from shapely.geometry import Point, shape
    # 성북구 장위동 68-2 부근(토지이음상 정비구역) 은 구역 안, 광화문 한복판은 밖.
    inside = Point(127.0518, 37.6128)
    outside = Point(126.9769, 37.5759)
    hit = any(shape(f["geometry"]).contains(inside) for f in feats)
    miss = any(shape(f["geometry"]).contains(outside) for f in feats)
    assert hit, "장위동 68-2 가 어떤 정비구역에도 안 들어감 — 좌표/필터 확인"
    assert not miss, "광화문이 정비구역으로 잡힘 — 재투영 확인"
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
